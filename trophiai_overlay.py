"""
trophiai_overlay.py - Trophi.ai Real-Time All-Corners Braking AI & Telemetry Coach
===================================================================================
Author: vevi (VEVIkils556@gmail.com)
Version: 3.5 Supreme (Blender 3D PBR + Resizable & Lockable + Clean Typography)
"""

import sys
import time
from collections import deque
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer, QRectF
from PyQt5.QtGui import (
    QPainter, QColor, QFont, QPen, QPainterPath
)
from overlay_utils import (
    get_sim_telemetry, draw_3d_card_bezel, draw_elided_text,
    ResizableLockableOverlay
)

OVERLAY_KEY = "trophi_overlay"
BASE_W, BASE_H = 590, 435
HISTORY_LEN = 180


class TrophiAIOverlay(ResizableLockableOverlay):
    def __init__(self):
        super().__init__(OVERLAY_KEY, BASE_W, BASE_H, default_x=360, default_y=580)

        self.live_thr = deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN)
        self.live_brk = deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN)
        self.opt_thr = deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN)
        self.opt_brk = deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN)

        now = time.time()
        for i in range(HISTORY_LEN):
            s = get_sim_telemetry(now - (HISTORY_LEN - i) * 0.032)
            self.live_thr.append(s["throttle"])
            self.live_brk.append(s["brake"])
            self.opt_thr.append(s["opt_throttle"])
            self.opt_brk.append(s["opt_brake"])

        self._sim = get_sim_telemetry(now)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_telemetry)
        self.timer.start(16)

    def update_telemetry(self):
        self.sync_window_from_config()
        sim_data = get_sim_telemetry(time.time())

        self.live_thr.append(sim_data["throttle"])
        self.live_brk.append(sim_data["brake"])
        self.opt_thr.append(sim_data["opt_throttle"])
        self.opt_brk.append(sim_data["opt_brake"])
        self._sim = sim_data
        self.update()

    def paintEvent(self, event):
        p = self.begin_overlay_painter()

        d = self._sim
        ac = d.get("active_corner", {})
        corners_db = d.get("corners_db", [])

        # Outer 3D Blender Machined Titanium & Carbon Neural Chassis (1180x870 RGBA)
        if not draw_3d_card_bezel(p, 6, 6, BASE_W - 12, BASE_H - 12, "trophi_neural_chassis_3d.png"):
            bg_path = QPainterPath()
            bg_path.addRoundedRect(QRectF(6, 6, BASE_W - 12, BASE_H - 12), 12, 12)
            p.fillPath(bg_path, QColor(12, 11, 24, 245))

        # 1. Header Bar: Track Name + Active Corner + ABS/TC Pills
        hdr_rect = QRectF(14, 12, BASE_W - 28, 28)
        p.setBrush(QColor(139, 92, 246, 55))
        p.setPen(QPen(QColor(139, 92, 246, 150), 1.0))
        p.drawRoundedRect(hdr_rect, 7, 7)

        p.setPen(QColor("#C4B5FD"))
        p.setFont(QFont("Segoe UI", 8, QFont.Black))
        track_title = d.get("track_name", "Autodromo Nazionale Monza")
        draw_elided_text(p, QRectF(22, 12, 235, 28), Qt.AlignLeft | Qt.AlignVCenter, f"TROPHI.AI | {track_title.upper()}")

        p.setPen(QColor("#00F5D4"))
        p.setFont(QFont("Consolas", 8, QFont.Bold))
        draw_elided_text(p, QRectF(262, 12, 195, 28), Qt.AlignCenter, d.get("active_corner_name", "C1"))

        abs_rect = QRectF(BASE_W - 112, 15, 45, 22)
        tc_rect = QRectF(BASE_W - 63, 15, 43, 22)
        p.setBrush(QColor("#EF4444") if d["abs_active"] else QColor(28, 32, 46))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(abs_rect, 4, 4)
        p.setPen(QColor("#FFFFFF") if d["abs_active"] else QColor("#64748B"))
        p.setFont(QFont("Segoe UI", 7, QFont.Black))
        p.drawText(abs_rect, Qt.AlignCenter, "ABS/LK")

        p.setBrush(QColor("#F59E0B") if d["tc_active"] else QColor(28, 32, 46))
        p.drawRoundedRect(tc_rect, 4, 4)
        p.setPen(QColor("#101218") if d["tc_active"] else QColor("#64748B"))
        p.drawText(tc_rect, Qt.AlignCenter, "TC/SLIP")

        # 2. Live AI Braking Coaching Banner
        tip_rect = QRectF(14, 44, BASE_W - 28, 26)
        p.setBrush(QColor(16, 185, 129, 38))
        p.setPen(QPen(QColor("#10B981"), 1.2))
        p.drawRoundedRect(tip_rect, 6, 6)
        p.setPen(QColor("#10B981"))
        p.setFont(QFont("Segoe UI", 7, QFont.Black))
        draw_elided_text(p, QRectF(22, 44, BASE_W - 44, 26), Qt.AlignLeft | Qt.AlignVCenter, f">> {d['coach_tip']}")

        # 3. Upper Left: Dual-Layer Braking & Throttle Trace (Live vs Optimal Reference)
        gx, gy, gw, gh = 14, 75, 355, 118
        p.setBrush(QColor(10, 12, 20, 238))
        p.setPen(QPen(QColor(255, 255, 255, 35), 1.0))
        p.drawRoundedRect(QRectF(gx, gy, gw, gh), 8, 8)

        # Dedicated Legend Strip at top of Graph (gy .. gy+18) so traces never collide with text
        p.fillRect(QRectF(gx + 2, gy + 2, gw - 4, 17), QColor(16, 20, 32, 220))
        p.setFont(QFont("Segoe UI", 6, QFont.Black))
        legend_items = [
            (gx + 8,   "#FF1E38", Qt.SolidLine, "FRENO VIVO"),
            (gx + 92,  "#F472B6", Qt.DashLine,  "FRENO REF IA"),
            (gx + 184, "#10B981", Qt.SolidLine, "GAS VIVO"),
            (gx + 262, "#38BDF8", Qt.DashLine,  "GAS REF IA"),
        ]
        for lx, col_hex, pen_style, lbl in legend_items:
            p.setPen(QPen(QColor(col_hex), 2.0, pen_style))
            p.drawLine(int(lx), int(gy + 10), int(lx + 12), int(gy + 10))
            p.setPen(QColor(col_hex))
            p.drawText(QRectF(lx + 15, gy + 3, 72, 14), Qt.AlignLeft | Qt.AlignVCenter, lbl)

        plot_top = gy + 22
        plot_h = gh - 28
        p.setPen(QPen(QColor(255, 255, 255, 18), 1.0, Qt.DashLine))
        for frac in (0.25, 0.5, 0.75):
            ly = plot_top + plot_h * frac
            p.drawLine(int(gx + 4), int(ly), int(gx + gw - 4), int(ly))

        def make_path(arr):
            path = QPainterPath()
            n = len(arr)
            for idx, val in enumerate(arr):
                px = gx + 6 + (idx / max(1, n - 1)) * (gw - 12)
                py = plot_top + plot_h - max(0.0, min(1.0, val)) * plot_h
                if idx == 0:
                    path.moveTo(px, py)
                else:
                    path.lineTo(px, py)
            return path

        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(56, 189, 248, 155), 1.5, Qt.DashLine))
        p.drawPath(make_path(self.opt_thr))
        p.setPen(QPen(QColor(244, 114, 182, 165), 1.6, Qt.DashLine))
        p.drawPath(make_path(self.opt_brk))
        p.setPen(QPen(QColor("#10B981"), 2.2))
        p.drawPath(make_path(self.live_thr))
        p.setPen(QPen(QColor("#FF1E38"), 2.5))
        p.drawPath(make_path(self.live_brk))

        # 4. Upper Right: Active Corner Real Braking Metrics Pod
        rx = gx + gw + 8
        rw = BASE_W - rx - 14
        pod_r = QRectF(rx, gy, rw, gh)
        p.setBrush(QColor(18, 22, 34, 240))
        p.setPen(QPen(QColor("#00F5D4"), 1.3))
        p.drawRoundedRect(pod_r, 8, 8)

        p.setPen(QColor("#00F5D4"))
        p.setFont(QFont("Segoe UI", 7, QFont.Black))
        c_title = f"DATOS REALES C{ac.get('id', 1)}: {ac.get('name', '')}"
        draw_elided_text(p, QRectF(rx + 8, gy + 5, rw - 16, 15), Qt.AlignLeft | Qt.AlignVCenter, c_title)

        p.setFont(QFont("Consolas", 8, QFont.Bold))
        p.setPen(QColor("#FFFFFF"))
        brk_m = ac.get("last_brake_m", 679)
        d_m = ac.get("delta_brake_m", 0)
        draw_elided_text(p, QRectF(rx + 8, gy + 24, rw - 16, 16), Qt.AlignLeft | Qt.AlignVCenter, f"FRENADA: m.{brk_m} ({d_m:+d}m)")

        pk_b = ac.get("peak_brake_pct", 92)
        ref_b = ac.get("ref_peak_brake_pct", 94)
        p.setPen(QColor("#FF1E38") if pk_b > 95 else QColor("#FBBF24"))
        draw_elided_text(p, QRectF(rx + 8, gy + 42, rw - 16, 16), Qt.AlignLeft | Qt.AlignVCenter, f"PICO FRENO: {pk_b}% (OBJ {ref_b}%)")

        b_dist = ac.get("brake_dist_m", 110)
        r_dist = ac.get("ref_brake_dist_m", 110)
        p.setPen(QColor("#CBD5E1"))
        draw_elided_text(p, QRectF(rx + 8, gy + 60, rw - 16, 16), Qt.AlignLeft | Qt.AlignVCenter, f"DISTANCIA:  {b_dist}m (OBJ {r_dist}m)")

        ent_s = ac.get("entry_speed_kmh", 242)
        apx_s = ac.get("apex_speed_kmh", 82)
        p.setPen(QColor("#10B981"))
        draw_elided_text(p, QRectF(rx + 8, gy + 78, rw - 16, 16), Qt.AlignLeft | Qt.AlignVCenter, f"VEL CURVA:  {ent_s} -> {apx_s} km/h")

        tb_s = ac.get("trail_score", 92)
        cs_s = ac.get("corner_score", 94)
        p.setPen(QColor("#C4B5FD"))
        draw_elided_text(p, QRectF(rx + 8, gy + 96, rw - 16, 16), Qt.AlignLeft | Qt.AlignVCenter, f"TRAIL: {tb_s}% | IA: {cs_s}%")

        # ==================================================================
        # 5. LOWER SECTION: ALL CORNERS REAL BRAKING TELEMETRY TABLE
        # ==================================================================
        ty = gy + gh + 8
        th = BASE_H - ty - 12
        t_rect = QRectF(14, ty, BASE_W - 28, th)
        p.setBrush(QColor(12, 15, 24, 242))
        p.setPen(QPen(QColor(139, 92, 246, 110), 1.2))
        p.drawRoundedRect(t_rect, 8, 8)

        # Table Column Headers (Strict non-overlapping X positions)
        p.setPen(QColor("#8E96AA"))
        p.setFont(QFont("Segoe UI", 7, QFont.Black))
        hy = ty + 5
        p.drawText(QRectF(22,  hy, 148, 16), Qt.AlignLeft,   "CURVA DEL CIRCUITO")
        p.drawText(QRectF(172, hy, 74,  16), Qt.AlignCenter, "PUNTO (dm)")
        p.drawText(QRectF(248, hy, 72,  16), Qt.AlignCenter, "PICO / OBJ")
        p.drawText(QRectF(322, hy, 46,  16), Qt.AlignCenter, "DIST.")
        p.drawText(QRectF(370, hy, 82,  16), Qt.AlignCenter, "ENT -> APICE")
        p.drawText(QRectF(454, hy, 42,  16), Qt.AlignCenter, "TRAIL")
        p.drawText(QRectF(498, hy, 70,  16), Qt.AlignCenter, "ESTADO IA")

        row_start_y = ty + 24
        max_rows = min(7, len(corners_db))
        row_h = 28
        active_id = ac.get("id", 1)

        for idx, c in enumerate(corners_db[:max_rows]):
            ry = row_start_y + idx * row_h
            is_act = (c["id"] == active_id)
            r_box = QRectF(18, ry, BASE_W - 36, row_h - 3)

            if is_act:
                p.setBrush(QColor(0, 245, 212, 42))
                p.setPen(QPen(QColor("#00F5D4"), 1.3))
                p.drawRoundedRect(r_box, 4, 4)
            else:
                p.setBrush(QColor(20, 24, 36, 195 if idx % 2 == 0 else 155))
                p.setPen(Qt.NoPen)
                p.drawRoundedRect(r_box, 4, 4)

            # Corner ID & Name
            prefix = "> " if is_act else ""
            p.setPen(QColor("#00F5D4") if is_act else QColor("#FFFFFF"))
            p.setFont(QFont("Segoe UI", 7, QFont.Black if is_act else QFont.Bold))
            draw_elided_text(p, QRectF(22, ry, 148, row_h - 3), Qt.AlignLeft | Qt.AlignVCenter, f"{prefix}C{c['id']} {c['name']}")

            # Brake Point & Delta m
            dm = c.get("delta_brake_m", 0)
            p.setPen(QColor("#10B981") if abs(dm) <= 5 else QColor("#F59E0B"))
            p.setFont(QFont("Consolas", 7, QFont.Bold))
            p.drawText(QRectF(172, ry, 74, row_h - 3), Qt.AlignCenter, f"m.{c['last_brake_m']}({dm:+d})")

            # Peak Brake % vs Ref %
            pk = c["peak_brake_pct"]
            rf = c["ref_peak_brake_pct"]
            p.setPen(QColor("#FF1E38") if pk > 95 else (QColor("#10B981") if abs(pk - rf) <= 8 else QColor("#FBBF24")))
            p.drawText(QRectF(248, ry, 72, row_h - 3), Qt.AlignCenter, f"{pk}% / {rf}%")

            # Brake Distance (m)
            p.setPen(QColor("#CBD5E1"))
            p.drawText(QRectF(322, ry, 46, row_h - 3), Qt.AlignCenter, f"{c['brake_dist_m']}m")

            # Entry -> Apex Speed (km/h)
            p.setPen(QColor("#38BDF8"))
            p.drawText(QRectF(370, ry, 82, row_h - 3), Qt.AlignCenter, f"{c['entry_speed_kmh']}->{c['apex_speed_kmh']}")

            # Trail-Brake Score %
            tb = c["trail_score"]
            p.setPen(QColor("#10B981") if tb >= 85 else QColor("#F59E0B"))
            p.drawText(QRectF(454, ry, 42, row_h - 3), Qt.AlignCenter, f"{tb}%")

            # Status Badge
            cs = c["corner_score"]
            badge_r = QRectF(500, ry + 3, 66, row_h - 9)
            p.setBrush(QColor(16, 185, 129, 55) if cs >= 88 else QColor(245, 158, 11, 55))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(badge_r, 3, 3)
            p.setPen(QColor("#10B981") if cs >= 88 else QColor("#FBBF24"))
            p.setFont(QFont("Segoe UI", 7, QFont.Black))
            p.drawText(badge_r, Qt.AlignCenter, f"IA {cs}% OK" if cs >= 88 else f"REV {cs}%")

        self.end_overlay_painter(p)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TrophiAIOverlay()
    win.show()
    sys.exit(app.exec_())
