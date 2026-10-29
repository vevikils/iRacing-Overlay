"""
radar_overlay.py - SimHub / RaceLab / Helicorsa 3D Spatial Proximity Radar
==========================================================================
Author: vevi (VEVIkils556@gmail.com)
Version: 3.5 Supreme (Blender 3D PBR + Resizable & Lockable + Clean Typography)
"""

import sys
import time
import irsdk
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt5.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QRadialGradient
)
from overlay_utils import (
    get_sim_telemetry, get_3d_asset, draw_elided_text,
    ResizableLockableOverlay
)

OVERLAY_KEY = "radar_overlay"
BASE_W, BASE_H = 260, 260


class RadarOverlay(ResizableLockableOverlay):
    def __init__(self):
        super().__init__(OVERLAY_KEY, BASE_W, BASE_H, default_x=850, default_y=460)
        self.ir = irsdk.IRSDK()
        self.is_connected = False
        self._sim = get_sim_telemetry(time.time())

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_telemetry)
        self.timer.start(16)

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
                    car_lr = int(self.ir["CarLeftRight"] or 0)
                    sim_data["radar_left"] = 0.85 if car_lr in (2, 4, 5) else 0.0
                    sim_data["radar_right"] = 0.85 if car_lr in (3, 4, 6) else 0.0
                except Exception:
                    pass

        self._sim = sim_data
        self.update()

    def paintEvent(self, event):
        p = self.begin_overlay_painter()

        d = self._sim
        cx, cy = BASE_W / 2.0, BASE_H / 2.0
        max_r = 114.0

        # 1. Blender 3D Machined Titanium & Dark Glass Radar Scope (520x520 RGBA)
        scope_pix = get_3d_asset("radar_scope_3d.png")
        if not scope_pix.isNull():
            p.drawPixmap(QRectF(4, 4, BASE_W - 8, BASE_H - 8), scope_pix, QRectF(0, 0, scope_pix.width(), scope_pix.height()))
        else:
            rad_grad = QRadialGradient(cx, cy, max_r)
            rad_grad.setColorAt(0.0, QColor(14, 18, 28, 215))
            rad_grad.setColorAt(1.0, QColor(0, 245, 212, 80))
            p.setBrush(QBrush(rad_grad))
            p.setPen(QPen(QColor(255, 255, 255, 45), 1.5))
            p.drawEllipse(QPointF(cx, cy), max_r, max_r)

        # Left & Right Proximity Warning Arcs
        rl = d["radar_left"]
        rr = d["radar_right"]
        arc_rect = QRectF(cx - max_r + 12, cy - max_r + 12, (max_r - 12) * 2, (max_r - 12) * 2)

        if rl > 0.05:
            col_l = QColor("#EF4444") if rl > 0.55 else QColor("#F59E0B")
            p.setPen(QPen(col_l, 9, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(arc_rect, 135 * 16, 90 * 16)

        if rr > 0.05:
            col_r = QColor("#EF4444") if rr > 0.55 else QColor("#F59E0B")
            p.setPen(QPen(col_r, 9, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(arc_rect, -45 * 16, 90 * 16)

        # 2. Center Player Car: 3D Blender Rendered FIA F4 Top-Down Single-Seater
        player_car_pix = get_3d_asset("radar_3d_f4_player_car.png")
        if not player_car_pix.isNull():
            pw, ph = 56, 56
            p.drawPixmap(
                QRectF(cx - pw / 2.0, cy - ph / 2.0, pw, ph),
                player_car_pix,
                QRectF(0, 0, player_car_pix.width(), player_car_pix.height())
            )
        else:
            car_w, car_h = 24, 48
            car_rect = QRectF(cx - car_w / 2.0, cy - car_h / 2.0, car_w, car_h)
            p.setBrush(QColor("#00F5D4"))
            p.setPen(QPen(QColor("#FFFFFF"), 1.6))
            p.drawRoundedRect(car_rect, 6, 6)

        # 3. Opponent Spatial 3D FIA F4 Cars
        opp_car_pix = get_3d_asset("radar_3d_f4_opponent_car.png")
        for opp in d.get("radar_opponents", []):
            ox = cx + opp["lat_m"] * 18.0
            oy = cy - opp["long_m"] * 12.0
            if not opp_car_pix.isNull():
                ow, oh = 52, 52
                p.drawPixmap(
                    QRectF(ox - ow / 2.0, oy - oh / 2.0, ow, oh),
                    opp_car_pix,
                    QRectF(0, 0, opp_car_pix.width(), opp_car_pix.height())
                )
            else:
                o_rect = QRectF(ox - 12, oy - 24, 24, 48)
                danger_col = QColor("#EF4444") if opp["danger"] > 0.55 else QColor("#F59E0B")
                p.setBrush(danger_col)
                p.setPen(QPen(QColor("#FFFFFF"), 1.4))
                p.drawRoundedRect(o_rect, 5, 5)

        # Spotter Callout Pill at Top (Clean ASCII/Latin, zero strange arrow symbols)
        if rl > 0.2 and rr > 0.2:
            spot_txt, spot_col = "[!] 3-WIDE ALERT [!]", "#EF4444"
        elif rl > 0.1:
            spot_txt, spot_col = "<< CAR LEFT", "#EF4444" if rl > 0.55 else "#F59E0B"
        elif rr > 0.1:
            spot_txt, spot_col = "CAR RIGHT >>", "#EF4444" if rr > 0.55 else "#F59E0B"
        else:
            spot_txt, spot_col = "CLEAR ALL AROUND", "#10B981"

        pill = QRectF(cx - 72, 22, 144, 22)
        p.setBrush(QColor(12, 15, 22, 235))
        p.setPen(QPen(QColor(spot_col), 1.4))
        p.drawRoundedRect(pill, 6, 6)
        p.setPen(QColor(spot_col))
        p.setFont(QFont("Segoe UI", 7, QFont.Black))
        draw_elided_text(p, pill, Qt.AlignCenter, spot_txt)

        self.end_overlay_painter(p)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = RadarOverlay()
    win.show()
    sys.exit(app.exec_())
