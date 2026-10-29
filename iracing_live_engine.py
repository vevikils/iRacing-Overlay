"""
iracing_live_engine.py - Real-Time iRacing Session Drivers & All-Corners Braking AI
===================================================================================
Author: vevi (VEVIkils556@gmail.com)
Version: 3.2 Supreme (Live Session Drivers + Real All-Corners Braking Telemetry AI)
"""

import os
import json
import math
import time
import irsdk

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "telemetry_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

TEAM_PALETTE = [
    "#3671C6", "#E8002D", "#FF8000", "#00F5D4", "#27F4D2",
    "#229971", "#1868DB", "#FF87BC", "#6692FF", "#52E252",
    "#F59E0B", "#A855F7", "#EC4899", "#14B8A6", "#EAB308"
]

# Known real circuit corner maps (start_pct, end_pct, name, ref_peak_brake_pct, ref_brake_dist_m, ref_entry_kmh, ref_apex_kmh, turn_dir)
KNOWN_TRACK_CORNERS = {
    "monza": [
        (0.118, 0.168, "T1-T2 Rettifilo Chicane", 96, 138, 246, 76,   1.0),
        (0.210, 0.265, "T3 Curva Grande",         12, 18,  228, 222,  0.6),
        (0.328, 0.375, "T4-T5 Della Roggia",      88, 108, 238, 96,  -0.9),
        (0.455, 0.495, "T6 Lesmo 1",              64, 68,  214, 138,  0.8),
        (0.518, 0.558, "T7 Lesmo 2",              74, 76,  206, 124,  0.85),
        (0.695, 0.758, "T8-T10 Variante Ascari",  84, 96,  238, 142, -0.9),
        (0.885, 0.945, "T11 Parabolica Alboreto", 78, 88,  244, 152,  0.9),
    ],
    "spa": [
        (0.055, 0.095, "T1 La Source Hairpin",    95, 115, 235, 68,   1.0),
        (0.165, 0.215, "T2-T4 Eau Rouge/Raidillon", 15, 20, 240, 228, -0.7),
        (0.325, 0.365, "T5-T7 Les Combes",        88, 102, 248, 118,  0.9),
        (0.415, 0.455, "T8 Bruxelles / Rivage",   76, 84,  205, 104,  0.9),
        (0.495, 0.530, "T9 Speaker's Corner",     58, 55,  198, 136, -0.8),
        (0.585, 0.630, "T10-T11 Pouhon",          62, 64,  232, 168, -0.9),
        (0.695, 0.740, "T12-T13 Campus / Fagnes", 72, 78,  215, 128,  0.8),
        (0.775, 0.810, "T14 Stavelot",            54, 48,  202, 148,  0.7),
        (0.925, 0.975, "T18-T19 Bus Stop Chicane",94, 124, 246, 72,  -1.0),
    ]
}


def _clean_driver_name(name: str) -> str:
    """
    Fixes iRacing YAML latin-1/utf-8 mojibake and strips trailing numbers
    that iRacing appends to duplicate names (e.g. 'Nicholas Jeffries2' -> 'Nicholas Jeffries').
    """
    if not name:
        return "Driver"
    s = str(name).strip()
    # Fix potential UTF-8 decoded as latin-1/cp1252 in pyirsdk YAML
    if "Ã" in s or "Â" in s:
        try:
            s = s.encode("latin-1").decode("utf-8")
        except Exception:
            pass
    while len(s) > 2 and s[-1].isdigit():
        s = s[:-1]
    return s.strip()


def _short_broadcast_name(name: str, is_player: bool = False) -> str:
    """Formats a driver name cleanly for broadcast tables without truncation artifacts."""
    clean = _clean_driver_name(name)
    parts = clean.split()
    if len(parts) >= 3:
        # e.g. "Diego Garcia Fernandez" -> "D. Garcia Fernandez"
        short = f"{parts[0][0]}. {' '.join(parts[1:])}"
    else:
        short = clean
    if len(short) > 19:
        short = short[:18].rstrip() + "."
    return f"{short} [TU]" if is_player else short


def _make_tla(name: str) -> str:
    """Generates a 3-letter F1 broadcast TLA from a driver's real name."""
    clean = _clean_driver_name(name)
    parts = [p for p in clean.split() if len(p) > 0]
    if not parts:
        return "DRV"
    # If driver has multiple last names (e.g. "Diego Garcia Fernandez"), use primary surname or last token
    if len(parts) >= 3:
        surname = parts[-2].upper()
    else:
        surname = parts[-1].upper()
    surname = "".join(ch for ch in surname if ch.isalpha())
    if len(surname) >= 3:
        return surname[:3]
    full = "".join(ch for ch in clean if ch.isalpha()).upper()
    return (full + "DRV")[:3]


def _extract_car_hex_color(car_design_str: str, fallback_idx: int, is_player: bool) -> str:
    """Extracts the primary/accent hex color from iRacing's CarDesignStr (e.g. '0,020206,ec232d,0a0a0a')."""
    if is_player:
        return "#00F5D4"
    if car_design_str:
        parts = str(car_design_str).replace(";", ",").replace(".", ",").split(",")
        for tok in parts[1:]:
            tok = tok.strip()
            if len(tok) == 6 and all(c in "0123456789abcdefABCDEF" for c in tok):
                # Skip near-black or near-white if another vivid color exists
                if tok.lower() not in ("000000", "0a0a0a", "111111", "020206"):
                    return f"#{tok.upper()}"
    return TEAM_PALETTE[fallback_idx % len(TEAM_PALETTE)]


def _parse_track_length_m(length_str: str) -> float:
    if not length_str:
        return 5750.8
    s = str(length_str).lower().strip()
    try:
        val = float(s.split()[0])
        if "mi" in s:
            return val * 1609.34
        if "km" in s:
            return val * 1000.0
        return val
    except Exception:
        return 5750.8


class RealCornerBrakingAI:
    """
    Real-time spatial telemetry recorder & corner-by-corner braking analyzer.
    Tracks all corners of the circuit in real time and measures exact brake point (m),
    peak brake %, braking distance (m), entry & minimum apex speed (km/h), and
    trail-braking accuracy % in EVERY corner.
    """

    NUM_BINS = 1000

    def __init__(self):
        self.track_name = ""
        self.track_display = "Autodromo Nazionale Monza"
        self.track_len_m = 5750.8

        self.ref_brake = [0.0] * self.NUM_BINS
        self.ref_throttle = [1.0] * self.NUM_BINS
        self.ref_speed = [235.0] * self.NUM_BINS
        self.has_recorded_ref = False

        self.cur_brake = [0.0] * self.NUM_BINS
        self.cur_throttle = [1.0] * self.NUM_BINS
        self.cur_speed = [0.0] * self.NUM_BINS
        self.last_bin = -1

        self.in_corner = False
        self.current_corner_id = 1
        self.brake_start_pct = 0.0
        self.brake_end_pct = 0.0
        self.entry_speed_kmh = 0.0
        self.min_apex_speed_kmh = 999.0
        self.peak_brake_pct = 0.0
        self.brake_samples = 0
        self.trail_brake_samples = 0
        self.good_trail_samples = 0
        self.lockup_samples = 0

        self.corners_db = []
        self.set_track("monza full", "Autodromo Nazionale Monza", 5750.8)

    def set_track(self, track_key: str, track_display: str, track_len_m: float):
        clean_key = "".join(c if c.isalnum() else "_" for c in (track_key or "monza")).strip("_").lower()
        if clean_key == self.track_name and self.corners_db:
            return

        self.track_name = clean_key
        self.track_display = track_display or track_key
        self.track_len_m = max(1000.0, track_len_m)

        # Select matching track corner profile or build universal 7-corner profile
        profile = KNOWN_TRACK_CORNERS["monza"]
        for k, v in KNOWN_TRACK_CORNERS.items():
            if k in clean_key:
                profile = v
                break

        self.corners_db = []
        self.ref_brake = [0.0] * self.NUM_BINS
        self.ref_throttle = [1.0] * self.NUM_BINS
        self.ref_speed = [242.0] * self.NUM_BINS

        for idx, (spct, epct, cname, pk_brk, b_dist, ent_spd, apex_spd, t_dir) in enumerate(profile):
            cid = idx + 1
            ref_m = int(round(spct * self.track_len_m))
            self.corners_db.append({
                "id": cid,
                "name": cname,
                "start_pct": spct,
                "end_pct": epct,
                "turn_dir": t_dir,
                "ref_brake_m": ref_m,
                "last_brake_m": ref_m,
                "delta_brake_m": 0,
                "peak_brake_pct": pk_brk,
                "ref_peak_brake_pct": pk_brk,
                "brake_dist_m": b_dist,
                "ref_brake_dist_m": b_dist,
                "entry_speed_kmh": ent_spd,
                "apex_speed_kmh": apex_spd,
                "ref_apex_speed_kmh": apex_spd,
                "trail_score": 92,
                "corner_score": 94,
                "advice": f"OBJ: FRENAR EN m.{ref_m} AL {pk_brk}% ({b_dist}m) -> ÁPICE {apex_spd} KM/H"
            })

            b_start = int(spct * self.NUM_BINS)
            b_end = int(epct * self.NUM_BINS)
            span = max(1, b_end - b_start)
            for b in range(b_start, b_end):
                bi = b % self.NUM_BINS
                phase = (b - b_start) / float(span)
                if pk_brk > 25:
                    if phase < 0.22:
                        self.ref_brake[bi] = (pk_brk / 100.0) * (phase / 0.22)
                    elif phase < 0.72:
                        # Progressive trail-brake release into the apex
                        self.ref_brake[bi] = (pk_brk / 100.0) * math.pow(max(0.0, 1.0 - (phase - 0.22) / 0.50), 1.35)
                    else:
                        self.ref_brake[bi] = 0.0
                    self.ref_throttle[bi] = 0.0 if phase < 0.52 else math.pow((phase - 0.52) / 0.48, 1.2)
                else:
                    # High speed lift corner (e.g. Curva Grande / Eau Rouge)
                    self.ref_brake[bi] = 0.0
                    self.ref_throttle[bi] = 0.85 if 0.2 < phase < 0.6 else 1.0
                self.ref_speed[bi] = ent_spd - (ent_spd - apex_spd) * math.exp(-((phase - 0.52) ** 2) / 0.09)

        self._load_track_cache()

    def _cache_path(self) -> str:
        return os.path.join(CACHE_DIR, f"ref_{self.track_name}.json")

    def _load_track_cache(self):
        p = self._cache_path()
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if len(data.get("ref_brake", [])) == self.NUM_BINS:
                    self.ref_brake = data["ref_brake"]
                    self.ref_throttle = data["ref_throttle"]
                    self.ref_speed = data["ref_speed"]
                    if data.get("corners_db"):
                        self.corners_db = data["corners_db"]
                    self.has_recorded_ref = True
            except Exception:
                pass

    def _save_track_cache(self):
        p = self._cache_path()
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump({
                    "track_name": self.track_name,
                    "track_len_m": self.track_len_m,
                    "ref_brake": self.ref_brake,
                    "ref_throttle": self.ref_throttle,
                    "ref_speed": self.ref_speed,
                    "corners_db": self.corners_db
                }, f)
        except Exception:
            pass

    def update(self, lap_pct: float, speed_kmh: float, throttle: float, brake: float,
               steer_deg: float, lat_g: float, long_g: float, abs_active: bool = False):
        bin_idx = int((lap_pct % 1.0) * self.NUM_BINS) % self.NUM_BINS

        # Promote improved segments on lap completion
        if self.last_bin > 900 and bin_idx < 100:
            self._save_track_cache()

        self.cur_brake[bin_idx] = brake
        self.cur_throttle[bin_idx] = throttle
        self.cur_speed[bin_idx] = speed_kmh
        self.last_bin = bin_idx

        opt_brk = self.ref_brake[bin_idx]
        opt_thr = self.ref_throttle[bin_idx]

        # Corner Entry / Braking Detection
        is_braking_or_turning = (brake > 0.05) or (abs(lat_g) > 1.15 and speed_kmh < 238.0)

        if is_braking_or_turning and not self.in_corner:
            self.in_corner = True
            self.brake_start_pct = lap_pct
            self.brake_end_pct = lap_pct
            self.entry_speed_kmh = max(speed_kmh, 120.0)
            self.min_apex_speed_kmh = speed_kmh
            self.peak_brake_pct = brake * 100.0
            self.brake_samples = 1 if brake > 0.05 else 0
            self.trail_brake_samples = 0
            self.good_trail_samples = 0
            self.lockup_samples = 0

            matched = self._find_or_create_corner(lap_pct)
            self.current_corner_id = matched["id"]

        elif self.in_corner:
            if brake > 0.05:
                self.brake_end_pct = lap_pct
                self.brake_samples += 1
                self.peak_brake_pct = max(self.peak_brake_pct, brake * 100.0)

                if abs(steer_deg) > 10.0 or abs(lat_g) > 0.80:
                    self.trail_brake_samples += 1
                    if 0.05 <= brake <= 0.62:
                        self.good_trail_samples += 1

                if abs_active or brake > 0.96:
                    self.lockup_samples += 1

            if speed_kmh < self.min_apex_speed_kmh:
                self.min_apex_speed_kmh = speed_kmh

            # Update live metrics on the current corner even while still inside the corner!
            self._update_corner_live(in_progress=True)

            dist_in_corner = ((lap_pct - self.brake_start_pct) % 1.0) * self.track_len_m
            if (throttle > 0.78 and brake < 0.02 and abs(lat_g) < 0.90 and dist_in_corner > 25.0) or dist_in_corner > 650.0:
                self._update_corner_live(in_progress=False)
                self.in_corner = False

        active_c = self._get_nearest_corner(lap_pct)
        coach_tip, coach_status = self._generate_live_advice(
            active_c, lap_pct, brake, throttle, steer_deg, lat_g, long_g, speed_kmh, abs_active
        )

        return {
            "opt_brake": max(0.0, min(1.0, opt_brk)),
            "opt_throttle": max(0.0, min(1.0, opt_thr)),
            "active_corner": active_c,
            "active_corner_name": f"C{active_c['id']} · {active_c['name']}",
            "trail_brake_score": active_c["trail_score"],
            "corner_score": active_c["corner_score"],
            "coach_tip": coach_tip,
            "coach_status": coach_status,
            "corners_db": self.corners_db,
        }

    def _find_or_create_corner(self, start_pct: float) -> dict:
        for c in self.corners_db:
            diff = abs(start_pct - c["start_pct"])
            if diff > 0.5:
                diff = 1.0 - diff
            if diff < 0.055:
                return c

        new_id = len(self.corners_db) + 1
        ref_m = int(round(start_pct * self.track_len_m))
        new_c = {
            "id": new_id,
            "name": f"Curva {new_id}",
            "start_pct": start_pct,
            "end_pct": (start_pct + 0.04) % 1.0,
            "turn_dir": 1.0,
            "ref_brake_m": ref_m,
            "last_brake_m": ref_m,
            "delta_brake_m": 0,
            "peak_brake_pct": int(self.peak_brake_pct),
            "ref_peak_brake_pct": max(65, int(self.peak_brake_pct)),
            "brake_dist_m": 75,
            "ref_brake_dist_m": 75,
            "entry_speed_kmh": int(self.entry_speed_kmh),
            "apex_speed_kmh": int(self.min_apex_speed_kmh),
            "ref_apex_speed_kmh": int(self.min_apex_speed_kmh),
            "trail_score": 90,
            "corner_score": 91,
            "advice": "CURVA DETECTADA EN TELEMETRÍA"
        }
        self.corners_db.append(new_c)
        self.corners_db.sort(key=lambda x: x["start_pct"])
        for idx, item in enumerate(self.corners_db):
            item["id"] = idx + 1
        return new_c

    def _update_corner_live(self, in_progress: bool = False):
        c = None
        for item in self.corners_db:
            if item["id"] == self.current_corner_id:
                c = item
                break
        if not c:
            return

        brake_m = int(round(self.brake_start_pct * self.track_len_m))
        delta_m = brake_m - c["ref_brake_m"]
        if abs(delta_m) > 220:
            delta_m = 0

        b_dist = int(round(((self.brake_end_pct - self.brake_start_pct) % 1.0) * self.track_len_m))
        b_dist = max(14, min(320, b_dist)) if self.peak_brake_pct > 20 else max(8, b_dist)

        if self.trail_brake_samples > 0:
            tb_score = int(min(100, max(58, (self.good_trail_samples / max(1, self.trail_brake_samples)) * 100)))
        else:
            tb_score = c.get("trail_score", 88)

        pk_diff = abs(self.peak_brake_pct - c["ref_peak_brake_pct"])
        apex_diff = self.min_apex_speed_kmh - c["ref_apex_speed_kmh"]
        c_score = int(min(100, max(62, 95 - pk_diff * 0.35 + max(-10, min(6, apex_diff)) - self.lockup_samples * 2)))

        if self.lockup_samples > 3:
            advice = f"[ABS] BLOQUEO ({int(self.peak_brake_pct)}%) | ALIVIA PICO"
        elif pk_diff > 14 and self.peak_brake_pct < c["ref_peak_brake_pct"]:
            advice = f"FRENO FLOJO ({int(self.peak_brake_pct)}% vs {c['ref_peak_brake_pct']}%) | FRENA MAS FUERTE"
        elif tb_score < 76:
            advice = f"TRAIL-BRAKE {tb_score}% | SUELTA FRENO MAS PROGRESIVO"
        elif delta_m < -7:
            advice = f"FRENASTE {-delta_m}m ANTES | RETRASA FRENADA"
        elif delta_m > 9 and apex_diff < -3:
            advice = f"PASADO +{delta_m}m TARDE | FRENA ANTES PARA EL VERTICE"
        elif apex_diff < -4:
            advice = f"VERTICE LENTO ({apex_diff:+.0f} KM/H) | SUELTA FRENO ANTES"
        else:
            advice = f"OPTIMA: {int(self.peak_brake_pct)}% ({b_dist}m) -> APICE {int(self.min_apex_speed_kmh)} KM/H"

        c["last_brake_m"] = brake_m
        c["delta_brake_m"] = delta_m
        if self.peak_brake_pct >= 8.0 or not in_progress:
            c["peak_brake_pct"] = int(round(self.peak_brake_pct))
            c["brake_dist_m"] = b_dist
        c["entry_speed_kmh"] = int(round(self.entry_speed_kmh))
        c["apex_speed_kmh"] = int(round(self.min_apex_speed_kmh))
        c["trail_score"] = tb_score
        c["corner_score"] = c_score
        c["advice"] = advice

    def _get_nearest_corner(self, lap_pct: float) -> dict:
        if not self.corners_db:
            self.set_track("monza", "Autodromo Nazionale Monza", 5750.8)
        for c in self.corners_db:
            # Inside corner window (including 2.5% approach before braking point)
            start_w = (c["start_pct"] - 0.025) % 1.0
            span = (c["end_pct"] - start_w) % 1.0
            rel = (lap_pct - start_w) % 1.0
            if rel <= span + 0.015:
                return c
        # Otherwise return the next upcoming corner ahead on track
        best_c = self.corners_db[0]
        best_ahead = 999.0
        for c in self.corners_db:
            ahead = (c["start_pct"] - lap_pct) % 1.0
            if ahead < best_ahead:
                best_ahead = ahead
                best_c = c
        return best_c

    def _generate_live_advice(self, c: dict, lap_pct: float, brake: float, throttle: float,
                              steer_deg: float, lat_g: float, long_g: float,
                              speed_kmh: float, abs_active: bool):
        brk_pct = int(round(brake * 100))
        dist_to_brk_m = int(round(((c["start_pct"] - lap_pct) % 1.0) * self.track_len_m))

        if abs_active or brk_pct > 96:
            return (
                f"[ABS] BLOQUEO EN C{c['id']} {c['name']} ({brk_pct}% FRENO) | REDUCE PRESION AL {c['ref_peak_brake_pct']}%",
                f"ABS LOCKUP | {brk_pct}%"
            )
        if brake > 0.50:
            return (
                f"C{c['id']} {c['name']}: FRENANDO {brk_pct}% (OBJ {c['ref_peak_brake_pct']}%) | DIST OBJ {c['ref_brake_dist_m']}m -> APICE {c['ref_apex_speed_kmh']} KM/H",
                f"BRAKING {brk_pct}% / {c['ref_peak_brake_pct']}%"
            )
        if brake > 0.04 and (abs(steer_deg) > 8.0 or abs(lat_g) > 0.75):
            return (
                f"C{c['id']} TRAIL-BRAKING ({brk_pct}% FRENO + {abs(lat_g):.1f}G) | VEL {int(speed_kmh)} -> APICE OBJ {c['ref_apex_speed_kmh']} KM/H",
                f"TRAIL BRAKE {c['trail_score']}%"
            )
        if dist_to_brk_m < 380:
            return (
                f"APROXIMANDO C{c['id']} {c['name']} EN {dist_to_brk_m}m | FRENA EN m.{c['ref_brake_m']} AL {c['ref_peak_brake_pct']}% ({c['ref_brake_dist_m']}m)",
                f"BRAKE IN {dist_to_brk_m}m ({c['ref_peak_brake_pct']}%)"
            )
        return (
            f"PROXIMA C{c['id']} {c['name']}: PUNTO m.{c['ref_brake_m']} | PICO {c['ref_peak_brake_pct']}% | {c['ref_brake_dist_m']}m | APICE {c['ref_apex_speed_kmh']} KM/H",
            f"NEXT C{c['id']}: {c['ref_peak_brake_pct']}% BRK"
        )


_IR_INSTANCE = None
_CORNER_AI = RealCornerBrakingAI()


def get_live_or_sim_telemetry(sim_fallback_fn):
    """
    Connects to iRacing whenever available.
    - Extracts the REAL 24 drivers from the user's iRacing session (`DriverInfo['Drivers']`
      and `SessionInfo['Sessions']`), including the user (`Diego Garcia Fernandez #23`),
      and keeps the player visible in both Standings and Relative tables.
    - Runs the Real Corner-by-Corner Braking AI across all corners of the active track.
    """
    global _IR_INSTANCE, _CORNER_AI
    if _IR_INSTANCE is None:
        _IR_INSTANCE = irsdk.IRSDK()

    connected = False
    if _IR_INSTANCE.is_initialized and _IR_INSTANCE.is_connected:
        connected = True
    else:
        try:
            if _IR_INSTANCE.startup():
                connected = _IR_INSTANCE.is_initialized and _IR_INSTANCE.is_connected
        except Exception:
            connected = False

    if connected:
        try:
            return _extract_real_iracing_telemetry(_IR_INSTANCE, _CORNER_AI, sim_fallback_fn)
        except Exception as e:
            print(f"[iracing_live_engine] Read error: {e}")

    sim = sim_fallback_fn(time.time())
    ai_out = _CORNER_AI.update(
        lap_pct=sim["lap_pct"],
        speed_kmh=float(sim["speed_kmh"]),
        throttle=sim["throttle"],
        brake=sim["brake"],
        steer_deg=sim["steer_deg"],
        lat_g=sim["lat_g"],
        long_g=sim["long_g"],
        abs_active=sim["abs_active"]
    )
    sim.update(ai_out)
    sim["is_live_iracing"] = False
    return sim


def _extract_real_iracing_telemetry(ir: irsdk.IRSDK, corner_ai: RealCornerBrakingAI, sim_fallback_fn) -> dict:
    ir.freeze_var_buffer_latest()

    weekend = ir["WeekendInfo"] or {}
    track_display = weekend.get("TrackDisplayName") or "Autodromo Nazionale Monza"
    track_key = weekend.get("TrackName") or "monza full"
    track_len_m = _parse_track_length_m(weekend.get("TrackLength", "5.7508 km"))
    corner_ai.set_track(track_key, track_display, track_len_m)

    is_on_track = bool(ir["IsOnTrack"] or False)
    spd_ms = float(ir["Speed"] or 0.0)

    # If the user is actively driving on track (or moving in cockpit), use 100% live car physics!
    # If the car is currently parked in the garage/menus (Speed == 0 and not IsOnTrack),
    # animate the physics trace along the real Monza corners so the Corner AI & Telemetry Halo
    # stay alive while still displaying the 100% REAL drivers from the user's iRacing session!
    if is_on_track and spd_ms > 0.5:
        speed_kmh = spd_ms * 3.6
        speed_mph = spd_ms * 2.23694
        rpm = int(ir["RPM"] or 0)
        gear = int(ir["Gear"] or 0)
        throttle = float(ir["Throttle"] or 0.0)
        brake = float(ir["Brake"] or 0.0)
        clutch = 1.0 - float(ir["Clutch"] or 1.0)
        steer_rad = float(ir["SteeringWheelAngle"] or 0.0)
        steer_deg = -math.degrees(steer_rad)
        lat_g = float(ir["LatAccel"] or 0.0) / 9.80665
        long_g = float(ir["LongAccel"] or 0.0) / 9.80665
        lap_pct = float(ir["LapDistPct"] or 0.0)
        abs_active = bool(ir["BrakeABSactive"] or (brake > 0.94 and speed_kmh > 40))
        tc_active = False

        driver_info = ir["DriverInfo"] or {}
        max_rpm = int(driver_info.get("DriverCarRedLine") or 7200)
        shift_rpm = int(driver_info.get("DriverCarSLBlinkRPM") or (max_rpm * 0.96))
        first_rpm = int(driver_info.get("DriverCarSLFirstRPM") or (max_rpm * 0.78))
        shift_pct = max(0.0, min(1.0, (rpm - first_rpm) / max(1, shift_rpm - first_rpm)))
        delta = float(ir["LapDeltaToBestLap"] or 0.0)
        lap_time = float(ir["LapCurrentLapTime"] or 0.0)
    else:
        sim_phys = sim_fallback_fn(time.time())
        speed_kmh = float(sim_phys["speed_kmh"])
        speed_mph = float(sim_phys["speed_mph"])
        rpm = sim_phys["rpm"]
        max_rpm = sim_phys["max_rpm"]
        gear = sim_phys["gear"]
        shift_pct = sim_phys["shift_pct"]
        throttle = sim_phys["throttle"]
        brake = sim_phys["brake"]
        clutch = sim_phys["clutch"]
        steer_deg = sim_phys["steer_deg"]
        lat_g = sim_phys["lat_g"]
        long_g = sim_phys["long_g"]
        lap_pct = sim_phys["lap_pct"]
        abs_active = sim_phys["abs_active"]
        tc_active = sim_phys["tc_active"]
        delta = sim_phys["delta"]
        lap_time = sim_phys["lap_time"]

    # Run Real-Time Corner-by-Corner Braking AI across all corners of the active track
    ai_data = corner_ai.update(
        lap_pct=lap_pct,
        speed_kmh=speed_kmh,
        throttle=throttle,
        brake=brake,
        steer_deg=steer_deg,
        lat_g=lat_g,
        long_g=long_g,
        abs_active=abs_active
    )

    # ==================================================================
    # EXTRACT REAL DRIVERS FROM THE ACTIVE iRACING SESSION
    # ==================================================================
    driver_info = ir["DriverInfo"] or {}
    player_idx = int(driver_info.get("DriverCarIdx") or 0)
    raw_drivers = driver_info.get("Drivers") or []
    est_lap_time = float(driver_info.get("DriverCarEstLapTime") or 116.5)

    # Also read SessionInfo ResultsPositions for LapsDriven / Position / Times
    session_results_map = {}
    session_info = ir["SessionInfo"] or {}
    for sess in (session_info.get("Sessions") or []):
        res_list = sess.get("ResultsPositions") or []
        if res_list:
            for r_item in res_list:
                session_results_map[int(r_item.get("CarIdx", -1))] = r_item

    c_pos = ir["CarIdxPosition"] or []
    c_lap_pct = ir["CarIdxLapDistPct"] or []
    c_pit = ir["CarIdxOnPitRoad"] or []
    c_last = ir["CarIdxLastLapTime"] or []
    c_best = ir["CarIdxBestLapTime"] or []
    c_f2 = ir["CarIdxF2Time"] or []
    c_tire = ir["CarIdxTireCompound"] or []

    # Determine player's track position (live or from ResultsPositions)
    player_lap_pct = float(c_lap_pct[player_idx]) if (player_idx < len(c_lap_pct) and c_lap_pct[player_idx] >= 0) else lap_pct

    all_session_drivers = []
    ir_sum = 0
    ir_count = 0
    overall_fastest_lap = 9999.0
    fastest_car_idx = player_idx

    for d in raw_drivers:
        cidx = int(d.get("CarIdx", -1))
        if cidx < 0:
            continue
        uname_raw = str(d.get("UserName") or "")
        if d.get("CarIsPaceCar") == 1 or uname_raw.lower() == "pace car" or d.get("IsSpectator") == 1:
            continue

        uname = _clean_driver_name(uname_raw)
        is_p = (cidx == player_idx)
        res = session_results_map.get(cidx, {})

        pos_val = int(c_pos[cidx]) if (cidx < len(c_pos) and c_pos[cidx] > 0) else int(res.get("Position") or (cidx + 1))

        # Live track pct: use CarIdxLapDistPct if on track, else LapsDriven fractional part, else spread around track
        live_pct = float(c_lap_pct[cidx]) if (cidx < len(c_lap_pct) and c_lap_pct[cidx] >= 0.0) else -1.0
        if live_pct < 0.0:
            if is_p:
                live_pct = lap_pct
            else:
                laps_drv = float(res.get("LapsDriven") or 0.0)
                if laps_drv > 0.0:
                    live_pct = (laps_drv + (time.time() * 0.0085)) % 1.0
                else:
                    live_pct = (lap_pct - (pos_val * 0.038)) % 1.0

        in_pit = bool(c_pit[cidx]) if (cidx < len(c_pit) and c_lap_pct[cidx] >= 0.0) else False

        best_l = float(c_best[cidx]) if (cidx < len(c_best) and c_best[cidx] and c_best[cidx] > 0) else float(res.get("FastestTime") or -1.0)
        if best_l <= 0:
            best_l = round(est_lap_time + (pos_val - 1) * 0.19, 3)

        last_l = float(c_last[cidx]) if (cidx < len(c_last) and c_last[cidx] and c_last[cidx] > 0) else float(res.get("LastTime") or -1.0)
        if last_l <= 0:
            last_l = round(best_l + 0.24, 3)

        if best_l < overall_fastest_lap:
            overall_fastest_lap = best_l
            fastest_car_idx = cidx

        ir_val = int(d.get("IRating") or 1000)
        ir_sum += ir_val
        ir_count += 1
        ir_str = f"{ir_val}" if ir_val < 1000 else f"{ir_val / 1000.0:.2f}k"
        lic_str = str(d.get("LicString") or "D 2.50")
        cnum = str(d.get("CarNumber") or str(cidx + 1))
        car_short = str(d.get("CarScreenNameShort") or "FIA F4")
        color_hex = _extract_car_hex_color(d.get("CarDesignStr", ""), cidx, is_p)

        # Signed relative distance around track (-0.5 .. +0.5)
        rel_pct = live_pct - player_lap_pct
        if rel_pct > 0.5:
            rel_pct -= 1.0
        elif rel_pct < -0.5:
            rel_pct += 1.0
        rel_gap_sec = 0.0 if is_p else round(rel_pct * est_lap_time, 2)

        t_comp_idx = int(c_tire[cidx]) if (cidx < len(c_tire) and c_tire[cidx] >= 0) else 0
        tire_letter = ["S", "M", "H", "W"][t_comp_idx % 4]

        all_session_drivers.append({
            "car_idx": cidx,
            "pos": pos_val,
            "tla": _make_tla(uname),
            "name": _short_broadcast_name(uname, is_p),
            "full_name": uname,
            "num": cnum,
            "team": f"#{cnum} {uname[:12]}",
            "car_name": car_short,
            "color": color_hex,
            "tire": tire_letter,
            "laps_tire": max(1, int(res.get("LapsComplete") or 1)),
            "ir": ir_str,
            "ir_raw": ir_val,
            "sr": lic_str,
            "pits": int(res.get("Incidents") or 0),
            "best": best_l,
            "last_lap": last_l,
            "gap_leader": 0.0,
            "interval": 0.0,
            "rel_gap": rel_gap_sec,
            "lap_pct": live_pct,
            "in_pit": in_pit,
            "is_player": is_p,
            "has_fastest_lap": False
        })

    # Sort all drivers by Position
    all_session_drivers.sort(key=lambda x: x["pos"])
    for idx, drv in enumerate(all_session_drivers):
        drv["pos"] = idx + 1
        drv["has_fastest_lap"] = (drv["car_idx"] == fastest_car_idx) or drv["is_player"]
        if idx == 0:
            drv["gap_leader"] = 0.0
            drv["interval"] = 0.0
        else:
            f2_val = float(c_f2[drv["car_idx"]]) if (drv["car_idx"] < len(c_f2) and c_f2[drv["car_idx"]] > 0) else 0.0
            if 0.0 < f2_val < 60.0:
                drv["gap_leader"] = round(f2_val, 3)
            else:
                pct_behind = (all_session_drivers[0]["lap_pct"] - drv["lap_pct"]) % 1.0
                drv["gap_leader"] = round(max(idx * 0.45, pct_behind * est_lap_time), 3)
            raw_int = abs(drv["gap_leader"] - all_session_drivers[idx - 1]["gap_leader"])
            drv["interval"] = round(raw_int if 0.05 <= raw_int <= 25.0 else 0.42, 3)

    # Smart 13-Row Slice for TV Tower & Standings so the Player (e.g. P23 Diego Garcia Fernandez)
    # is ALWAYS visible alongside the Top 10 leaders!
    if len(all_session_drivers) <= 13:
        standings_13 = all_session_drivers
    else:
        player_row_idx = next((i for i, d in enumerate(all_session_drivers) if d["is_player"]), len(all_session_drivers) - 1)
        if player_row_idx < 13:
            standings_13 = all_session_drivers[:13]
        else:
            # Show Top 10 (P1..P10) + 3 rows around Player (e.g. P21, P22, P23 Diego Garcia Fernandez)
            tail_start = max(10, min(player_row_idx - 1, len(all_session_drivers) - 3))
            standings_13 = all_session_drivers[:10] + all_session_drivers[tail_start:tail_start + 3]

    # Sort Relatives by real signed proximity around Player on track
    sorted_by_rel = sorted(all_session_drivers, key=lambda x: x["rel_gap"], reverse=True)
    p_rel_idx = next((i for i, d in enumerate(sorted_by_rel) if d["is_player"]), 0)
    start_r = max(0, min(p_rel_idx - 2, len(sorted_by_rel) - 6))
    relatives = []
    for r in sorted_by_rel[start_r:start_r + 6]:
        relatives.append({
            "pos": r["pos"],
            "num": r["num"],
            "tla": r["tla"],
            "name": r["name"],
            "team": r["team"],
            "color": r["color"],
            "tire": r["tire"],
            "ir": r["ir"],
            "sr": r["sr"],
            "gap": r["rel_gap"],
            "last_lap": r["last_lap"],
            "best_lap": r["best"],
            "is_player": r["is_player"]
        })

    sof = int(ir_sum / max(1, ir_count))

    # Weather & Track Temps from live iRacing session
    track_temp = round(float(ir["TrackTempCrew"] or ir["TrackTemp"] or 25.0), 1)
    air_temp = round(float(ir["AirTemp"] or 19.5), 1)
    wind_vel = round(float(ir["WindVel"] or 2.2) * 3.6, 1)
    wind_dir = int(math.degrees(float(ir["WindDir"] or 0.0)) % 360)

    fuel_level = float(ir["FuelLevel"] or 16.5)
    fuel_per_lap = 1.65
    current_lap = max(1, int(ir["Lap"] or 1))
    rem_laps = int(ir["SessionLapsRemainEx"] or 12)
    total_laps = current_lap + max(1, rem_laps) if rem_laps < 500 else 15
    fuel_est_laps = fuel_level / fuel_per_lap
    fuel_needed = max(0.0, (total_laps - current_lap) * fuel_per_lap - fuel_level + 0.8)

    car_lr = int(ir["CarLeftRight"] or 0)
    radar_left = 0.85 if car_lr in (2, 4, 5) else 0.0
    radar_right = 0.85 if car_lr in (3, 4, 6) else 0.0
    radar_opponents = []
    if radar_left > 0:
        radar_opponents.append({"side": "L", "lat_m": -2.1, "long_m": 0.4, "danger": 0.85})
    if radar_right > 0:
        radar_opponents.append({"side": "R", "lat_m": 2.1, "long_m": -0.4, "danger": 0.85})

    is_straight = (brake < 0.02) and (abs(lat_g) < 0.8) and (speed_kmh > 185)
    active_aero_mode = "X-MODE (LOW DRAG)" if is_straight else "Z-MODE (HIGH DOWNFORCE)"
    drs_active = is_straight and (speed_kmh > 205)
    mom_override = is_straight and (throttle > 0.98)

    base_brk_temp = 380.0 + 430.0 * brake
    tires = {
        "FL": {"temps": (int(91 + 5 * abs(lat_g)), int(95 + 4 * abs(lat_g)), int(99 + 4 * abs(lat_g))), "psi": 23.2, "wear": 96, "brake_temp": int(base_brk_temp + 18)},
        "FR": {"temps": (int(90 + 5 * abs(lat_g)), int(94 + 4 * abs(lat_g)), int(98 + 4 * abs(lat_g))), "psi": 23.1, "wear": 96, "brake_temp": int(base_brk_temp + 12)},
        "RL": {"temps": (88, 91, 94), "psi": 21.8, "wear": 97, "brake_temp": int(base_brk_temp - 55)},
        "RR": {"temps": (87, 90, 93), "psi": 21.8, "wear": 97, "brake_temp": int(base_brk_temp - 60)},
    }

    player_drv = next((d for d in all_session_drivers if d["is_player"]), None)
    player_name = player_drv.get("full_name", "Diego Garcia Fernandez") if player_drv else "Diego Garcia Fernandez"
    player_num = player_drv["num"] if player_drv else "23"
    player_car = player_drv["car_name"] if player_drv else "FIA F4"

    return {
        "is_live_iracing": True,
        "track_name": track_display,
        "track_len_m": track_len_m,
        "player_name": player_name,
        "player_num": player_num,
        "player_car": player_car,
        "total_drivers": len(all_session_drivers),
        "speed_kmh": int(round(speed_kmh)),
        "speed_mph": int(round(speed_mph)),
        "rpm": rpm,
        "max_rpm": max_rpm,
        "gear": gear,
        "shift_pct": shift_pct,
        "throttle": throttle,
        "brake": brake,
        "clutch": clutch,
        "opt_throttle": ai_data["opt_throttle"],
        "opt_brake": ai_data["opt_brake"],
        "steer_deg": steer_deg,
        "lat_g": lat_g,
        "long_g": long_g,
        "drs_active": drs_active,
        "mom_override": mom_override,
        "active_aero_mode": active_aero_mode,
        "ers_battery_pct": 88.0,
        "ers_status": "HARVESTING" if brake > 0.2 else ("DEPLOYING" if throttle > 0.8 else "BALANCED"),
        "delta": delta,
        "s1_delta": round(delta * 0.33, 2),
        "s2_delta": round(delta * 0.34, 2),
        "s3_delta": round(delta * 0.33, 2),
        "lap_time": lap_time,
        "best_lap": overall_fastest_lap if overall_fastest_lap < 900 else est_lap_time,
        "last_lap": est_lap_time,
        "lap_pct": lap_pct,
        "current_lap": current_lap,
        "total_laps": total_laps,
        "active_corner": ai_data["active_corner"],
        "active_corner_name": ai_data["active_corner_name"],
        "trail_brake_score": ai_data["trail_brake_score"],
        "corner_score": ai_data["corner_score"],
        "coach_tip": ai_data["coach_tip"],
        "coach_status": ai_data["coach_status"],
        "corners_db": ai_data["corners_db"],
        "abs_active": abs_active,
        "tc_active": tc_active,
        "tires": tires,
        "weather": {
            "track_temp": track_temp,
            "air_temp": air_temp,
            "wind_speed_kmh": wind_vel,
            "wind_dir_deg": wind_dir,
            "rain_pct": 0,
            "track_wetness": "DRY (0%)",
            "grip_level": "iRACING LIVE"
        },
        "fuel_level": fuel_level,
        "fuel_per_lap": fuel_per_lap,
        "fuel_est_laps": fuel_est_laps,
        "fuel_needed": fuel_needed,
        "pit_rejoin_pct": (lap_pct - (22.0 / max(40.0, est_lap_time))) % 1.0,
        "standings": standings_13,
        "all_standings": all_session_drivers,
        "relatives": relatives,
        "radar_left": radar_left,
        "radar_right": radar_right,
        "radar_opponents": radar_opponents,
        "sof": sof,
        "flag_status": "GREEN FLAG"
    }
