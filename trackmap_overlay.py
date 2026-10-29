"""
trackmap_overlay.py - RaceLab / SimHub Live GPS Track Map & Pit Rejoin Predictor
=================================================================================
Author: vevi (VEVIkils556@gmail.com)
Version: 3.5 Supreme (Blender 3D PBR + Resizable & Lockable + Anti-Overlap Layout)
"""

import sys
import math
import time
import irsdk
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt5.QtGui import (
    QPainter, QColor, QFont, QPen, QPainterPath
)
from overlay_utils import (
    get_sim_telemetry, draw_3d_card_bezel, draw_elided_text,
    ResizableLockableOverlay
)

OVERLAY_KEY = "trackmap_overlay"
BASE_W, BASE_H = 380, 290


class TrackMapOverlay(ResizableLockableOverlay):
    def __init__(self):
        super().__init__(OVERLAY_KEY, BASE_W, BASE_H, default_x=1500, default_y=40)

        self.ir = irsdk.IRSDK()
        self.is_connected = False
        self._sim = get_sim_telemetry(time.time())
        self._track_pts = self._build_circuit_spline(300)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_telemetry)
        self.timer.start(16)

    def _build_circuit_spline(self, n_pts: int):
        pts = []
        cx, cy = BASE_W / 2.0, BASE_H / 2.0 + 6
        rx, ry = 122.0, 72.0
        for i in range(n_pts):
            pct = i / float(n_pts)
            ang = pct * math.pi * 2.0
            r_mod = (
                1.0
                + 0.14 * math.sin(ang * 2.0 + 0.4)
                - 0.10 * math.cos(ang * 3.0 - 0.8)
                + 0.06 * math.sin(ang * 5.0 + 1.1)
            )
            px = cx + rx * r_mod * math.cos(ang)
            py = cy + ry * r_mod * math.sin(ang)
            pts.append(QPointF(px, py))
        return pts

    def _point_at_pct(self, pct: float) -> QPointF:
        idx = int((pct % 1.0) * len(self._track_pts)) % len(self._track_pts)
        return self._track_pts[idx]

    def _offset_from_center(self, pt: QPointF, dist_px: float) -> QPointF:
        """Offsets a point outward (+dist_px) or inward (-dist_px) radially from track center."""
        cx, cy = BASE_W / 2.0, BASE_H / 2.0 + 6
        dx, dy = pt.x() - cx, pt.y() - cy
        length = max(1.0, math.hypot(dx, dy))
        return QPointF(pt.x() + (dx / length) * dist_px, pt.y() + (dy / length) * dist_px)

    def update_telemetry(self):
        self.sync_window_from_config()
        sim_data = get_sim_telemetry(time.time())

        if not self._cfg.get("sim_mode", False):
            if not self.is_connected:
                if self.ir.startup():
                    self.is_connected = True
            elif not self.ir.is_initialized:
                self.is_connected = False
            if self.is_connected:
                try:
                    self.ir.freeze_var_buffer_latest()
                    lap_dist = float(self.ir["LapDistPct"] or 0.0)
                    sim_data["lap_pct"] = lap_dist
                    sim_data["pit_rejoin_pct"] = (lap_dist - 0.265) % 1.0
                except Exception:
                    pass

        self._sim = sim_data
        self.update()

    def paintEvent(self, event):
        p = self.begin_overlay_painter()

        d = self._sim
        if not draw_3d_card_bezel(p, 4, 4, BASE_W - 8, BASE_H - 8):
            bg_path = QPainterPath()
            bg_path.addRoundedRect(QRectF(6, 6, BASE_W - 12, BASE_H - 12), 12, 12)
            p.fillPath(bg_path, QColor(12, 15, 22, 238))

        # Top Header (Strictly separated Left & Right boxes)
        p.setPen(QColor("#FFFFFF"))
        p.setFont(QFont("Segoe UI", 8, QFont.Black))
        draw_elided_text(p, QRectF(16, 12, 240, 20), Qt.AlignLeft | Qt.AlignVCenter, "GPS TRACK MAP | PIT PREDICTOR")

        p.setPen(QColor("#00F5D4"))
        p.setFont(QFont("Consolas", 8, QFont.Bold))
        p.drawText(QRectF(BASE_W - 116, 12, 100, 20), Qt.AlignRight | Qt.AlignVCenter, f"LAP {d['current_lap']}/{d['total_laps']}")

        # Draw Track Asphalt Shadow
        track_path = QPainterPath()
        for i, pt in enumerate(self._track_pts):
            if i == 0:
                track_path.moveTo(pt)
            else:
                track_path.lineTo(pt)
        track_path.closeSubpath()

        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(35, 42, 58, 240), 10, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(track_path)

        # Draw Sector-Colored Centerline (S1 Red, S2 Cyan, S3 Purple)
        n = len(self._track_pts)
        sector_cols = [(0, n // 3, "#E10600"), (n // 3, (2 * n) // 3, "#00F5D4"), ((2 * n) // 3, n, "#A855F7")]
        for i_start, i_end, hex_c in sector_cols:
            s_path = QPainterPath()
            for idx in range(i_start, i_end + 1):
                pt = self._track_pts[idx % n]
                if idx == i_start:
                    s_path.moveTo(pt)
                else:
                    s_path.lineTo(pt)
            p.setPen(QPen(QColor(hex_c), 3.0, Qt.SolidLine, Qt.RoundCap))
            p.drawPath(s_path)

        # Start / Finish Line Marker
        sf_pt = self._point_at_pct(0.0)
        p.setBrush(QColor("#FFFFFF"))
        p.setPen(QPen(QColor("#E10600"), 1.5))
        p.drawRect(QRectF(sf_pt.x() - 3.5, sf_pt.y() - 8, 7, 16))

        # 1. Corner Braking Badges (C1..C7) Offset OUTWARD so they never touch cars on track
        active_cid = d.get("active_corner", {}).get("id", 1)
        for c_item in d.get("corners_db", []):
            cpt = self._point_at_pct(c_item["start_pct"])
            lbl_pt = self._offset_from_center(cpt, 19.0)
            is_act_c = (c_item["id"] == active_cid)

            p.setPen(QPen(QColor("#00F5D4" if is_act_c else "#E10600"), 1.0))
            p.drawLine(cpt, lbl_pt)

            p.setBrush(QColor("#00F5D4") if is_act_c else QColor(24, 28, 40, 235))
            p.setPen(QPen(QColor("#FFFFFF" if is_act_c else "#E10600"), 1.1))
            c_box = QRectF(lbl_pt.x() - 9, lbl_pt.y() - 6.5, 18, 13)
            p.drawRoundedRect(c_box, 3, 3)

            p.setPen(QColor(10, 12, 18) if is_act_c else QColor("#FFFFFF"))
            p.setFont(QFont("Segoe UI", 6, QFont.Black))
            p.drawText(c_box, Qt.AlignCenter, f"C{c_item['id']}")

        # 2. Predicted Pit Exit Ghost Marker Offset INWARD
        rejoin_pt = self._point_at_pct(d["pit_rejoin_pct"])
        in_pt = self._offset_from_center(rejoin_pt, -20.0)
        p.setPen(QPen(QColor("#F59E0B"), 1.2, Qt.DashLine))
        p.drawLine(rejoin_pt, in_pt)

        p.setBrush(QColor(245, 158, 11, 225))
        p.setPen(QPen(QColor("#FFFFFF"), 1.4))
        p.drawEllipse(rejoin_pt, 5.5, 5.5)

        pit_pill = QRectF(in_pt.x() - 25, in_pt.y() - 7, 50, 14)
        p.setBrush(QColor(20, 24, 34, 235))
        p.setPen(QPen(QColor("#F59E0B"), 1.0))
        p.drawRoundedRect(pit_pill, 3, 3)
        p.setPen(QColor("#FBBF24"))
        p.setFont(QFont("Segoe UI", 6, QFont.Black))
        p.drawText(pit_pill, Qt.AlignCenter, "PIT EXIT")

        # 3. Opponent Cars on Track (De-cluttered dots)
        standings = d.get("all_standings") or d.get("standings", [])
        player_drv = None
        placed_label_pcts = []
        for drv in standings:
            if drv.get("is_player"):
                player_drv = drv
                placed_label_pcts.append(drv["lap_pct"])
                break

        for drv in reversed(standings):
            if drv.get("is_player"):
                continue
            lp = drv["lap_pct"]
            pt = self._point_at_pct(lp)

            # Check if far enough from other labeled cars to show position number
            can_label = (drv["pos"] <= 3) and all(
                min(abs(lp - pp), 1.0 - abs(lp - pp)) > 0.055 for pp in placed_label_pcts
            )
            if can_label:
                placed_label_pcts.append(lp)
                p.setBrush(QColor(14, 18, 26, 245))
                p.setPen(QPen(QColor(drv["color"]), 2.0))
                p.drawEllipse(pt, 6.8, 6.8)
                p.setPen(QColor("#FFFFFF"))
                p.setFont(QFont("Segoe UI", 6, QFont.Black))
                p.drawText(QRectF(pt.x() - 7, pt.y() - 7, 14, 14), Qt.AlignCenter, str(drv["pos"]))
            else:
                p.setBrush(QColor(drv["color"]))
                p.setPen(QPen(QColor(10, 12, 18, 220), 1.0))
                p.drawEllipse(pt, 4.2, 4.2)

        # 4. Player Car on Top + Central Telemetry Info Pill (Zero overlap!)
        if player_drv:
            ppt = self._point_at_pct(player_drv["lap_pct"])
            p.setBrush(QColor(0, 245, 212, 75))
            p.setPen(Qt.NoPen)
            p.drawEllipse(ppt, 12.5, 12.5)

            p.setBrush(QColor("#00F5D4"))
            p.setPen(QPen(QColor("#FFFFFF"), 1.8))
            p.drawEllipse(ppt, 7.5, 7.5)

            p.setPen(QColor(10, 12, 18))
            p.setFont(QFont("Segoe UI", 6, QFont.Black))
            p.drawText(QRectF(ppt.x() - 8, ppt.y() - 8, 16, 16), Qt.AlignCenter, str(player_drv["pos"]))

        # Center Loop Status Badge (Inside the circuit hole where no cars/corners exist)
        cx, cy = BASE_W / 2.0, BASE_H / 2.0 + 6
        center_box = QRectF(cx - 70, cy - 17, 140, 34)
        p.setBrush(QColor(12, 16, 26, 225))
        p.setPen(QPen(QColor(0, 245, 212, 95), 1.0))
        p.drawRoundedRect(center_box, 6, 6)
        p.setPen(QColor("#00F5D4"))
        p.setFont(QFont("Segoe UI", 7, QFont.Black))
        p_pos = player_drv["pos"] if player_drv else 23
        p_num = player_drv["num"] if player_drv else "23"
        draw_elided_text(p, QRectF(cx - 66, cy - 15, 132, 15), Qt.AlignCenter, f"TU COCHE: #{p_num} (P{p_pos})")
        p.setPen(QColor("#CBD5E1"))
        p.setFont(QFont("Consolas", 7, QFont.Bold))
        draw_elided_text(p, QRectF(cx - 66, cy + 1, 132, 14), Qt.AlignCenter, d.get("active_corner_name", "C1"))

        # Bottom Legend
        p.setPen(QColor("#94A3B8"))
        p.setFont(QFont("Segoe UI", 7, QFont.Bold))
        draw_elided_text(
            p,
            QRectF(16, BASE_H - 26, BASE_W - 32, 16),
            Qt.AlignCenter,
            "CYAN: TU (#23)  |  AMBAR: PIT EXIT (-21s)  |  S1 / S2 / S3"
        )
        self.end_overlay_painter(p)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TrackMapOverlay()
    win.show()
    sys.exit(app.exec_())
