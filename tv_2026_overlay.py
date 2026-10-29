"""
tv_2026_overlay.py - Official 2026 F1 & Motorsport TV Broadcast Dashboard HUD (3D Edition)
==========================================================================================
Author: vevi (VEVIkils556@gmail.com)
Version: 3.5 Supreme (Blender 3D PBR + Resizable & Lockable + Clean Typography)
"""

import sys
import math
import time
import irsdk
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt5.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QLinearGradient,
    QRadialGradient, QPainterPath
)
from overlay_utils import (
    load_config, get_theme, get_sim_telemetry,
    get_3d_asset, draw_3d_card_bezel, draw_elided_text,
    ResizableLockableOverlay
)

OVERLAY_KEY = "tv2026_overlay"
BASE_W, BASE_H = 1160, 560


class TV2026BroadcastOverlay(ResizableLockableOverlay):
    def __init__(self):
        super().__init__(OVERLAY_KEY, BASE_W, BASE_H, default_x=20, default_y=30)
        self.ir = irsdk.IRSDK()
        self.is_connected = False
        self._sim = get_sim_telemetry(time.time())
        self._peak_g = 0.0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_telemetry)
        self.timer.start(16)  # 60 FPS Broadcast Smoothness

    def update_telemetry(self):
        self.sync_window_from_config()
        sim_data = get_sim_telemetry(time.time())

        curr_g = math.hypot(sim_data["lat_g"], sim_data["long_g"])
        self._peak_g = max(curr_g, self._peak_g * 0.995)
        self._sim = sim_data
        self.update()

    def paintEvent(self, event):
        p = self.begin_overlay_painter()
        self._draw_timing_tower(p, 12, 12, 315, 536)
        self._draw_center_halo_pod(p, 348, 22, 796, 516)
        self.end_overlay_painter(p)

    def _draw_timing_tower(self, p: QPainter, x: int, y: int, w: int, h: int):
        d = self._sim
        if not draw_3d_card_bezel(p, x, y, w, h, "timing_tower_chassis_3d.png"):
            bg_path = QPainterPath()
            bg_path.addRoundedRect(QRectF(x, y, w, h), 10, 10)
            p.fillPath(bg_path, QColor(10, 12, 18, 244))

        p.setPen(QColor(255, 255, 255))
        p.setFont(QFont("Segoe UI", 11, QFont.Black))
        p.drawText(QRectF(x + 14, y + 5, 160, 20), Qt.AlignLeft | Qt.AlignVCenter, "F1 2026 TV 3D")

        p.setFont(QFont("Consolas", 11, QFont.Bold))
        lap_str = f"LAP {d['current_lap']}/{d['total_laps']}"
        p.drawText(QRectF(x + w - 128, y + 5, 114, 20), Qt.AlignRight | Qt.AlignVCenter, lap_str)

        # Sub-header Flag & Track Status bar
        sub_rect = QRectF(x + 8, y + 26, w - 16, 18)
        p.fillRect(sub_rect, QColor(10, 13, 20, 215))
        p.setPen(QColor("#00F5D4"))
        p.setFont(QFont("Segoe UI", 7, QFont.Bold))
        p.drawText(QRectF(x + 14, y + 26, 195, 18), Qt.AlignLeft | Qt.AlignVCenter, "GREEN FLAG | MOM & X-MODE")
        p.setPen(QColor("#A0AAB8"))
        p.drawText(QRectF(x + w - 108, y + 26, 94, 18), Qt.AlignRight | Qt.AlignVCenter, "INT / TIRE")

        # 13 Broadcast Driver Rows
        row_y = y + 48
        row_h = 34
        standings = d.get("standings", [])
        for idx, drv in enumerate(standings[:13]):
            ry = row_y + idx * row_h
            is_player = drv.get("is_player", False)
            has_fl = bool(drv.get("has_fastest_lap", False))

            row_rect = QRectF(x + 9, ry, w - 18, row_h - 3)
            if is_player:
                r_grad = QLinearGradient(x + 9, ry, x + w - 9, ry)
                r_grad.setColorAt(0.0, QColor(0, 245, 212, 85))
                r_grad.setColorAt(1.0, QColor(18, 25, 38, 195))
                p.fillRect(row_rect, QBrush(r_grad))
                p.setPen(QPen(QColor("#00F5D4"), 1.4))
                p.drawRoundedRect(row_rect, 4, 4)
            else:
                bg_alpha = 155 if idx % 2 == 0 else 115
                p.fillRect(row_rect, QColor(14, 18, 28, bg_alpha))

            # Position Badge (x+13 .. x+37)
            pos_rect = QRectF(x + 13, ry + 4, 24, row_h - 11)
            p.setBrush(QColor("#E10600") if idx == 0 else (QColor("#00F5D4") if is_player else QColor(34, 40, 54, 230)))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(pos_rect, 3, 3)

            p.setPen(QColor(10, 12, 18) if is_player else QColor(255, 255, 255))
            p.setFont(QFont("Segoe UI", 8, QFont.Black))
            p.drawText(pos_rect, Qt.AlignCenter, str(drv["pos"]))

            # Team Color Vertical Bar (x+40 .. x+44)
            p.setBrush(QColor(drv["color"]))
            p.drawRoundedRect(QRectF(x + 40, ry + 4, 4, row_h - 11), 2, 2)

            # Driver TLA (x+48 .. x+82)
            p.setPen(QColor("#00F5D4") if is_player else QColor(255, 255, 255))
            p.setFont(QFont("Segoe UI", 8, QFont.Black))
            p.drawText(QRectF(x + 48, ry + 2, 34, row_h - 6), Qt.AlignLeft | Qt.AlignVCenter, drv["tla"])

            # Driver Name strictly bounded so it never touches FL pill or Interval
            name_max_w = 92 if has_fl else 114
            p.setPen(QColor("#00F5D4") if is_player else QColor("#CBD5E1"))
            p.setFont(QFont("Segoe UI", 7, QFont.Bold))
            raw_drv_name = drv.get("full_name", drv["name"]).replace(" [TU]", "").replace(" (TÚ)", "")
            draw_elided_text(p, QRectF(x + 84, ry + 2, name_max_w, row_h - 6), Qt.AlignLeft | Qt.AlignVCenter, raw_drv_name)

            # Fastest Lap Purple Pill (x+178 .. x+198)
            if has_fl:
                fl_rect = QRectF(x + 178, ry + 6, 20, row_h - 15)
                p.setBrush(QColor("#A855F7"))
                p.setPen(Qt.NoPen)
                p.drawRoundedRect(fl_rect, 3, 3)
                p.setPen(QColor(255, 255, 255))
                p.setFont(QFont("Segoe UI", 6, QFont.Black))
                p.drawText(fl_rect, Qt.AlignCenter, "FL")

            # Interval / Leader / Pit Status (x+200 .. x+262)
            p.setFont(QFont("Consolas", 8, QFont.Bold))
            if drv.get("in_pit"):
                p.setPen(QColor("#FFCC00"))
                gap_txt = "IN PIT"
            elif idx == 0:
                p.setPen(QColor("#E10600"))
                gap_txt = "LEADER"
            else:
                p.setPen(QColor("#FFFFFF") if is_player else QColor("#D0D7E2"))
                gap_txt = f"+{drv['interval']:.3f}"
            p.drawText(QRectF(x + 200, ry + 2, 62, row_h - 6), Qt.AlignRight | Qt.AlignVCenter, gap_txt)

            # Pirelli Tire Compound Circle (center at x+w-26)
            tire_c = drv.get("tire", "S")
            tire_col = {"S": "#FF2A2A", "M": "#FFD700", "H": "#FFFFFF", "I": "#22C55E", "W": "#38BDF8"}.get(tire_c, "#FF2A2A")
            t_cx = x + w - 26
            t_cy = ry + (row_h - 3) / 2.0
            p.setPen(QPen(QColor(tire_col), 2.0))
            p.setBrush(QColor(14, 16, 22))
            p.drawEllipse(QPointF(t_cx, t_cy), 8.5, 8.5)
            p.setPen(QColor(255, 255, 255))
            p.setFont(QFont("Segoe UI", 7, QFont.Black))
            p.drawText(QRectF(t_cx - 8, t_cy - 8, 16, 16), Qt.AlignCenter, tire_c)

        # Bottom Tower Footer (3D Anodized Purple Pod) - Strictly non-overlapping boxes
        foot_y = y + h - 43
        p.setPen(QColor(255, 255, 255))
        p.setFont(QFont("Segoe UI", 8, QFont.Black))
        p_num = d.get("player_num", "23")
        p_name = d.get("player_name", "Diego Garcia Fernandez")
        bst_m = int(d["best_lap"] // 60)
        bst_s = d["best_lap"] % 60
        draw_elided_text(p, QRectF(x + 14, foot_y + 2, 184, 16), Qt.AlignLeft | Qt.AlignVCenter, f"SESION: #{p_num} {p_name}")

        p.setFont(QFont("Consolas", 9, QFont.Bold))
        p.drawText(QRectF(x + w - 112, foot_y + 2, 98, 16), Qt.AlignRight | Qt.AlignVCenter, f"{bst_m}:{bst_s:06.3f}")

        p.setPen(QColor("#E9D5FF"))
        p.setFont(QFont("Segoe UI", 7, QFont.DemiBold))
        tot_drv = d.get("total_drivers", len(standings))
        t_short = d.get("track_name", "Autodromo Nazionale Monza")
        draw_elided_text(p, QRectF(x + 14, foot_y + 17, w - 28, 14), Qt.AlignLeft | Qt.AlignVCenter, f"SOF {d['sof']} | {tot_drv} PILOTOS | {t_short}")

    def _draw_center_halo_pod(self, p: QPainter, x: int, y: int, w: int, h: int):
        d = self._sim
        if not draw_3d_card_bezel(p, x, y, w, h, "halo_telemetry_chassis_3d.png"):
            pod_rect = QRectF(x, y, w, h)
            path = QPainterPath()
            path.addRoundedRect(pod_rect, 18, 18)
            p.fillPath(path, QColor(12, 15, 23, 242))

        # Header Bar inside Halo Pod
        top_bar = QRectF(x + 22, y + 14, w - 44, 30)
        p.setBrush(QColor(14, 18, 28, 150))
        p.setPen(QPen(QColor(0, 245, 212, 75), 1.0))
        p.drawRoundedRect(top_bar, 7, 7)

        # Active Corner / Track Zone Badge (Left: x+32 .. x+312)
        p.setPen(QColor("#00F5D4"))
        p.setFont(QFont("Segoe UI", 9, QFont.Black))
        draw_elided_text(p, QRectF(x + 32, y + 14, 280, 30), Qt.AlignLeft | Qt.AlignVCenter, f"ZONA: {d['active_corner_name']}")

        # Live Lap Delta Pill in Header (Center: x+w/2-72 .. x+w/2+72)
        delta_val = d["delta"]
        delta_col = QColor("#10B981") if delta_val <= 0 else QColor("#EF4444")
        p.setBrush(delta_col)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(x + w / 2 - 72, y + 17, 144, 24), 6, 6)
        p.setPen(QColor(10, 12, 18) if delta_val <= 0 else QColor(255, 255, 255))
        p.setFont(QFont("Consolas", 10, QFont.Black))
        sign = "+" if delta_val > 0 else ""
        p.drawText(QRectF(x + w / 2 - 72, y + 17, 144, 24), Qt.AlignCenter, f"DELTA {sign}{delta_val:.3f}s")

        # 2026 F1 Broadcast Watermark (Right: x+w-260 .. x+w-32)
        p.setPen(QColor("#FFFFFF"))
        p.setFont(QFont("Segoe UI", 8, QFont.Black))
        p.drawText(QRectF(x + w - 260, y + 14, 228, 30), Qt.AlignRight | Qt.AlignVCenter, "F1 2026 TELEMETRY HALO | VEVI")

        # ==================================================================
        # 1. LEFT CLUSTER: THROTTLE & BRAKE CURVED ARCS + G-FORCE SPHERE
        # ==================================================================
        arc_cx = x + 150
        arc_cy = y + 198

        thr_rect = QRectF(arc_cx - 102, arc_cy - 102, 204, 204)
        p.setPen(QPen(QColor(35, 42, 58, 220), 13, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(thr_rect, 225 * 16, -270 * 16)

        thr_span = int(-270 * 16 * max(0.0, min(1.0, d["throttle"])))
        p.setPen(QPen(QColor("#00F58A"), 13, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(thr_rect, 225 * 16, thr_span)

        brk_rect = QRectF(arc_cx - 79, arc_cy - 79, 158, 158)
        p.setPen(QPen(QColor(35, 42, 58, 220), 13, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(brk_rect, 225 * 16, -270 * 16)

        brk_span = int(-270 * 16 * max(0.0, min(1.0, d["brake"])))
        p.setPen(QPen(QColor("#FF1E38"), 13, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(brk_rect, 225 * 16, brk_span)

        # 2D G-Force Accelerometer Sphere
        g_rad = 54
        g_grad = QRadialGradient(arc_cx, arc_cy, g_rad)
        g_grad.setColorAt(0.0, QColor(24, 30, 44, 240))
        g_grad.setColorAt(1.0, QColor(10, 13, 20, 250))
        p.setBrush(QBrush(g_grad))
        p.setPen(QPen(QColor(100, 116, 139, 140), 1.2))
        p.drawEllipse(QPointF(arc_cx, arc_cy), g_rad, g_rad)
        p.drawEllipse(QPointF(arc_cx, arc_cy), g_rad * 0.5, g_rad * 0.5)
        p.drawLine(int(arc_cx - g_rad), int(arc_cy), int(arc_cx + g_rad), int(arc_cy))
        p.drawLine(int(arc_cx), int(arc_cy - g_rad), int(arc_cx), int(arc_cy + g_rad))

        gx = arc_cx + (d["lat_g"] / 5.0) * (g_rad - 8)
        gy = arc_cy - (d["long_g"] / 5.0) * (g_rad - 8)
        p.setBrush(QColor("#00F5D4"))
        p.setPen(QPen(QColor(255, 255, 255), 1.5))
        p.drawEllipse(QPointF(gx, gy), 6.5, 6.5)

        total_g = math.hypot(d["lat_g"], d["long_g"])
        p.setPen(QColor(255, 255, 255))
        p.setFont(QFont("Consolas", 9, QFont.Bold))
        p.drawText(QRectF(arc_cx - 45, arc_cy + g_rad - 20, 90, 18), Qt.AlignCenter, f"{total_g:.1f}G")

        # Numeric Readouts below Left Cluster
        p.setFont(QFont("Segoe UI", 8, QFont.Black))
        p.setPen(QColor("#00F58A"))
        p.drawText(QRectF(arc_cx - 102, arc_cy + 94, 98, 20), Qt.AlignLeft | Qt.AlignVCenter, f"THR {int(d['throttle']*100):3d}%")
        p.setPen(QColor("#FF1E38"))
        p.drawText(QRectF(arc_cx + 4, arc_cy + 94, 98, 20), Qt.AlignRight | Qt.AlignVCenter, f"BRK {int(d['brake']*100):3d}%")

        # G-Force directional box
        g_box = QRectF(x + 28, y + 340, 244, 92)
        p.setBrush(QColor(18, 22, 32, 230))
        p.setPen(QPen(QColor(255, 255, 255, 35), 1.0))
        p.drawRoundedRect(g_box, 8, 8)
        p.setPen(QColor("#8E96AA"))
        p.setFont(QFont("Segoe UI", 7, QFont.Bold))
        p.drawText(QRectF(x + 38, y + 347, 224, 16), Qt.AlignLeft, "G-FORCE TELEMETRY (2026 SENSOR POD)")
        p.setPen(QColor("#FFFFFF"))
        p.setFont(QFont("Consolas", 9, QFont.Bold))
        p.drawText(QRectF(x + 38, y + 369, 110, 20), Qt.AlignLeft, f"LAT:  {abs(d['lat_g']):.2f} G")
        p.drawText(QRectF(x + 152, y + 369, 110, 20), Qt.AlignLeft, f"LONG: {abs(d['long_g']):.2f} G")
        p.setPen(QColor("#00F5D4"))
        p.drawText(QRectF(x + 38, y + 397, 224, 20), Qt.AlignLeft, f"PEAK: {self._peak_g:.2f}G | STEER: {d['steer_deg']:+.1f} deg")

        # ==================================================================
        # 2. CENTER HALO DIAL: 15-LED RPM ARC + SPEED + GEAR + 3D WHEEL BAY
        # ==================================================================
        c_cx = x + 405
        c_cy = y + 192

        halo_rect = QRectF(c_cx - 115, c_cy - 115, 230, 230)
        p.setPen(QPen(QColor(35, 42, 60, 230), 10, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(halo_rect, 215 * 16, -250 * 16)

        num_leds = 15
        lit_leds = int(round(d["shift_pct"] * num_leds))
        for i in range(num_leds):
            ang_deg = 205.0 - (i / (num_leds - 1)) * 230.0
            ang_rad = math.radians(ang_deg)
            lx = c_cx + 115.0 * math.cos(ang_rad)
            ly = c_cy - 115.0 * math.sin(ang_rad)

            if i < lit_leds:
                led_col = QColor("#00F58A") if i < 5 else (QColor("#FF2A2A") if i < 10 else QColor("#A855F7"))
                p.setBrush(led_col)
                p.setPen(QPen(QColor(255, 255, 255, 200), 1.2))
            else:
                p.setBrush(QColor(28, 34, 48, 220))
                p.setPen(QPen(QColor(60, 70, 90, 120), 1.0))
            p.drawEllipse(QPointF(lx, ly), 5.8, 5.8)

        # Speedometer Readout
        p.setPen(QColor(255, 255, 255))
        p.setFont(QFont("Segoe UI", 34, QFont.Black))
        p.drawText(QRectF(c_cx - 90, c_cy - 88, 180, 46), Qt.AlignCenter, f"{d['speed_kmh']}")

        p.setPen(QColor("#00F5D4"))
        p.setFont(QFont("Segoe UI", 8, QFont.Black))
        p.drawText(QRectF(c_cx - 90, c_cy - 42, 180, 18), Qt.AlignCenter, f"KM/H  |  {d['speed_mph']} MPH")

        # Central Gear Badge + RPM
        gear_box = QRectF(c_cx - 32, c_cy - 20, 64, 52)
        p.setBrush(QColor(225, 6, 0, 235) if d["shift_pct"] > 0.88 else QColor(24, 30, 46, 245))
        p.setPen(QPen(QColor("#E10600") if d["shift_pct"] > 0.88 else QColor("#00F5D4"), 1.8))
        p.drawRoundedRect(gear_box, 10, 10)

        gear_str = "R" if d["gear"] == -1 else ("N" if d["gear"] == 0 else str(d["gear"]))
        p.setPen(QColor(255, 255, 255))
        p.setFont(QFont("Segoe UI", 24, QFont.Black))
        p.drawText(gear_box, Qt.AlignCenter, gear_str)

        p.setPen(QColor("#CBD5E1"))
        p.setFont(QFont("Consolas", 10, QFont.Bold))
        p.drawText(QRectF(c_cx - 80, c_cy + 36, 160, 20), Qt.AlignCenter, f"{d['rpm']:,} RPM")

        # Dedicated 3D Steering Wheel Cockpit Bay (y+332 .. y+432, below the RPM ring)
        sw_bay = QRectF(c_cx - 115, y + 332, 230, 100)
        p.setBrush(QColor(16, 20, 30, 230))
        p.setPen(QPen(QColor(0, 245, 212, 65), 1.0))
        p.drawRoundedRect(sw_bay, 9, 9)

        p.setPen(QColor("#8E96AA"))
        p.setFont(QFont("Segoe UI", 7, QFont.Bold))
        p.drawText(QRectF(c_cx - 105, y + 338, 110, 16), Qt.AlignLeft, "VOLANTE F1 2026 3D")
        p.setPen(QColor("#00F5D4"))
        p.setFont(QFont("Consolas", 9, QFont.Black))
        p.drawText(QRectF(c_cx - 105, y + 358, 95, 20), Qt.AlignLeft, f"ANG: {d['steer_deg']:+.1f} deg")
        p.setPen(QColor("#CBD5E1"))
        p.setFont(QFont("Consolas", 8, QFont.Bold))
        p.drawText(QRectF(c_cx - 105, y + 380, 95, 18), Qt.AlignLeft, f"MARCHA: G{gear_str}")
        p.drawText(QRectF(c_cx - 105, y + 398, 95, 18), Qt.AlignLeft, f"VEL: {d['speed_kmh']} KM/H")

        # Rotating 3D F1 2026 Steering Wheel on the right side of the bay (c_cx + 52, y + 382)
        self._draw_f1_steering_wheel(p, c_cx + 52, y + 382, 36, d["steer_deg"], d["gear"], d["speed_kmh"])

        # ==================================================================
        # 3. RIGHT CLUSTER: 2026 ACTIVE AERO (X/Z MODE) + MOM + DRS + ERS SOC
        # ==================================================================
        rx = x + 545
        ry = y + 62
        rw = 232

        is_xmode = "X-MODE" in d["active_aero_mode"]
        aero_rect = QRectF(rx, ry, rw, 54)
        aero_col = QColor("#00F5D4") if is_xmode else QColor("#F59E0B")
        p.setBrush(QColor(0, 245, 212, 35) if is_xmode else QColor(245, 158, 11, 35))
        p.setPen(QPen(aero_col, 1.8))
        p.drawRoundedRect(aero_rect, 9, 9)

        p.setPen(QColor("#8E96AA"))
        p.setFont(QFont("Segoe UI", 7, QFont.Bold))
        p.drawText(QRectF(rx + 12, ry + 6, rw - 24, 15), Qt.AlignLeft, "2026 FIA ACTIVE AERODYNAMICS")
        p.setPen(aero_col)
        p.setFont(QFont("Segoe UI", 9, QFont.Black))
        p.drawText(QRectF(rx + 12, ry + 23, rw - 20, 24), Qt.AlignLeft | Qt.AlignVCenter, d["active_aero_mode"])

        # DRS & 2026 MOM Pills
        drs_rect = QRectF(rx, ry + 66, 110, 42)
        mom_rect = QRectF(rx + 122, ry + 66, 110, 42)

        drs_on = d["drs_active"]
        p.setBrush(QColor(16, 185, 129, 220) if drs_on else QColor(22, 26, 38, 220))
        p.setPen(QPen(QColor("#10B981") if drs_on else QColor(70, 80, 100), 1.5))
        p.drawRoundedRect(drs_rect, 8, 8)
        p.setPen(QColor(10, 12, 18) if drs_on else QColor("#64748B"))
        p.setFont(QFont("Segoe UI", 9, QFont.Black))
        p.drawText(drs_rect, Qt.AlignCenter, "DRS OPEN" if drs_on else "DRS CLOSED")

        mom_on = d["mom_override"]
        p.setBrush(QColor(168, 85, 247, 230) if mom_on else QColor(22, 26, 38, 220))
        p.setPen(QPen(QColor("#C084FC") if mom_on else QColor(70, 80, 100), 1.5))
        p.drawRoundedRect(mom_rect, 8, 8)
        p.setPen(QColor(255, 255, 255) if mom_on else QColor("#64748B"))
        p.setFont(QFont("Segoe UI", 9, QFont.Black))
        p.drawText(mom_rect, Qt.AlignCenter, "MOM 350kW" if mom_on else "MOM READY")

        # ERS Battery State of Charge (SOC %)
        ers_box = QRectF(rx, ry + 120, rw, 98)
        p.setBrush(QColor(18, 22, 32, 235))
        p.setPen(QPen(QColor(255, 255, 255, 40), 1.2))
        p.drawRoundedRect(ers_box, 9, 9)

        p.setPen(QColor("#8E96AA"))
        p.setFont(QFont("Segoe UI", 7, QFont.Bold))
        p.drawText(QRectF(rx + 12, ry + 127, 150, 16), Qt.AlignLeft, "ERS MGU-K BATTERY SOC")

        ers_pct = d["ers_battery_pct"]
        p.setPen(QColor("#00F5D4"))
        p.setFont(QFont("Consolas", 12, QFont.Black))
        p.drawText(QRectF(rx + rw - 85, ry + 124, 73, 22), Qt.AlignRight, f"{int(ers_pct)}%")

        num_cells = 12
        lit_cells = int(round((ers_pct / 100.0) * num_cells))
        cell_w = (rw - 28 - (num_cells - 1) * 3) / num_cells
        for c_i in range(num_cells):
            cx_i = rx + 14 + c_i * (cell_w + 3)
            c_rect = QRectF(cx_i, ry + 150, cell_w, 22)
            if c_i < lit_cells:
                c_col = QColor("#EF4444") if ers_pct < 20 else (QColor("#FACC15") if ers_pct < 45 else QColor("#00F5D4"))
                p.setBrush(c_col)
            else:
                p.setBrush(QColor(32, 38, 52, 200))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(c_rect, 2, 2)

        status_col = "#10B981" if d["ers_status"] == "HARVESTING" else ("#C084FC" if "MOM" in d["ers_status"] else "#38BDF8")
        p.setPen(QColor(status_col))
        p.setFont(QFont("Segoe UI", 8, QFont.Black))
        p.drawText(QRectF(rx + 12, ry + 182, rw - 24, 20), Qt.AlignLeft | Qt.AlignVCenter, f"MODE: {d['ers_status']}")

        # Sector 1 / S2 / S3 Broadcast Mini-Sector Boxes
        sec_box = QRectF(rx, ry + 230, rw, 140)
        p.setBrush(QColor(18, 22, 32, 235))
        p.setPen(QPen(QColor(255, 255, 255, 40), 1.2))
        p.drawRoundedRect(sec_box, 9, 9)

        p.setPen(QColor("#8E96AA"))
        p.setFont(QFont("Segoe UI", 7, QFont.Bold))
        p.drawText(QRectF(rx + 12, ry + 238, rw - 24, 16), Qt.AlignLeft, "BROADCAST SECTOR SPLITS & PACE")

        sectors = [
            ("S1", d["s1_delta"], "#A855F7"),
            ("S2", d["s2_delta"], "#10B981"),
            ("S3", d["s3_delta"], "#A855F7"),
        ]
        sw_box = (rw - 32) / 3.0
        for s_i, (s_name, s_val, s_hex) in enumerate(sectors):
            sx = rx + 12 + s_i * (sw_box + 4)
            s_rect = QRectF(sx, ry + 258, sw_box, 42)
            p.setBrush(QColor(s_hex))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(s_rect, 5, 5)
            p.setPen(QColor(255, 255, 255))
            p.setFont(QFont("Segoe UI", 8, QFont.Black))
            p.drawText(QRectF(sx, ry + 261, sw_box, 16), Qt.AlignCenter, s_name)
            p.setFont(QFont("Consolas", 8, QFont.Bold))
            p.drawText(QRectF(sx, ry + 277, sw_box, 18), Qt.AlignCenter, f"{s_val:+.2f}s")

        cur_m = int(d["lap_time"] // 60)
        cur_s = d["lap_time"] % 60
        bst_m = int(d["best_lap"] // 60)
        bst_s = d["best_lap"] % 60
        p.setPen(QColor("#FFFFFF"))
        p.setFont(QFont("Consolas", 9, QFont.Bold))
        p.drawText(QRectF(rx + 12, ry + 310, rw - 24, 20), Qt.AlignLeft, f"CURRENT:  {cur_m}:{cur_s:06.3f}")
        p.setPen(QColor("#C084FC"))
        p.drawText(QRectF(rx + 12, ry + 332, rw - 24, 20), Qt.AlignLeft, f"BEST LAP: {bst_m}:{bst_s:06.3f} (PURPLE)")

        # ==================================================================
        # 4. BOTTOM TV LOWER-THIRD DRIVER BANNER (Strict Non-Overlapping Columns)
        # ==================================================================
        p_num = d.get("player_num", "23")
        p_name = d.get("player_name", "Diego Garcia Fernandez")
        p_car = d.get("player_car", "FIA F4")
        t_name = d.get("track_name", "Autodromo Nazionale Monza")
        ac = d.get("active_corner", {})

        p.setPen(QColor(255, 255, 255))
        p.setFont(QFont("Segoe UI", 16, QFont.Black))
        p.drawText(QRectF(x + 28, y + h - 60, 62, 44), Qt.AlignLeft | Qt.AlignVCenter, f"#{p_num}")

        # Left column: x+92 .. x+362 (width 270px)
        p.setFont(QFont("Segoe UI", 10, QFont.Black))
        draw_elided_text(p, QRectF(x + 92, y + h - 59, 270, 24), Qt.AlignLeft | Qt.AlignVCenter, f"{p_name.upper()} | VEVI WORKS")
        p.setPen(QColor("#00F5D4"))
        p.setFont(QFont("Segoe UI", 8, QFont.Bold))
        draw_elided_text(p, QRectF(x + 92, y + h - 37, 270, 18), Qt.AlignLeft | Qt.AlignVCenter, f"{p_car} | {t_name.upper()}")

        # Right column: x+372 .. x+w-28 (width 396px) -> 10px guaranteed gap from left column
        p.setPen(QColor("#FFFFFF"))
        p.setFont(QFont("Consolas", 8, QFont.Bold))
        w_info = d["weather"]
        draw_elided_text(
            p,
            QRectF(x + 372, y + h - 58, w - 400, 22),
            Qt.AlignRight | Qt.AlignVCenter,
            f"PISTA {w_info['track_temp']}C | AIRE {w_info['air_temp']}C | VIENTO {w_info['wind_speed_kmh']} KM/H"
        )
        p.setPen(QColor("#10B981"))
        p.setFont(QFont("Segoe UI", 8, QFont.Black))
        c_brk_str = f"IA C{ac.get('id',1)}: FRENAR m.{ac.get('ref_brake_m',679)} AL {ac.get('ref_peak_brake_pct',96)}% ({ac.get('ref_brake_dist_m',138)}m) -> APICE {ac.get('ref_apex_speed_kmh',76)} KM/H"
        draw_elided_text(
            p,
            QRectF(x + 372, y + h - 37, w - 400, 18),
            Qt.AlignRight | Qt.AlignVCenter,
            c_brk_str
        )

    def _draw_f1_steering_wheel(self, p: QPainter, cx: float, cy: float, radius: float, steer_deg: float, gear: int, speed: int):
        p.save()
        p.translate(cx, cy)
        p.rotate(steer_deg)

        sw_pix = get_3d_asset("f1_2026_steering_wheel_3d.png")
        if not sw_pix.isNull():
            r_draw = radius * 1.28
            p.drawPixmap(
                QRectF(-r_draw, -r_draw, r_draw * 2.0, r_draw * 2.0),
                sw_pix,
                QRectF(0, 0, sw_pix.width(), sw_pix.height())
            )
            p.setPen(QColor("#00F5D4"))
            p.setFont(QFont("Consolas", 7, QFont.Black))
            p.drawText(
                QRectF(-radius * 0.56, -radius * 0.24, radius * 1.12, radius * 0.50),
                Qt.AlignCenter,
                f"G{gear}|{speed}"
            )
        else:
            p.setPen(QPen(QColor("#00F5D4"), 2.0))
            p.drawRoundedRect(QRectF(-radius, -radius * 0.68, radius * 2, radius * 1.36), 14, 14)

        p.restore()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TV2026BroadcastOverlay()
    win.show()
    sys.exit(app.exec_())
