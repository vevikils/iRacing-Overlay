"""
tires_weather_overlay.py - SimHub / RaceLab 4-Tire Thermals, Brakes & Weather HUD
==================================================================================
Author: vevi (VEVIkils556@gmail.com)
Version: 3.5 Supreme (Blender 3D PBR + Resizable & Lockable + Clean Typography)
"""

import sys
import time
import irsdk
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer, QRectF
from PyQt5.QtGui import (
    QPainter, QColor, QFont, QPen, QPainterPath
)
from overlay_utils import (
    get_sim_telemetry, draw_3d_card_bezel, draw_elided_text,
    ResizableLockableOverlay
)

OVERLAY_KEY = "tires_overlay"
BASE_W, BASE_H = 335, 315


def _temp_to_color(temp_c: int) -> QColor:
    if temp_c < 75:
        return QColor("#38BDF8")
    if temp_c <= 98:
        return QColor("#10B981")
    if temp_c <= 106:
        return QColor("#F59E0B")
    return QColor("#EF4444")


def _brake_to_color(temp_c: int) -> QColor:
    if temp_c < 350:
        return QColor("#38BDF8")
    if temp_c <= 650:
        return QColor("#10B981")
    if temp_c <= 800:
        return QColor("#F97316")
    return QColor("#EF4444")


class TiresWeatherOverlay(ResizableLockableOverlay):
    def __init__(self):
        super().__init__(OVERLAY_KEY, BASE_W, BASE_H, default_x=40, default_y=730)
        self.ir = irsdk.IRSDK()
        self.is_connected = False
        self._sim = get_sim_telemetry(time.time())

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_telemetry)
        self.timer.start(50)

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
                    tt = self.ir["TrackTempCrew"] or self.ir["TrackTemp"]
                    at = self.ir["AirTemp"]
                    if tt:
                        sim_data["weather"]["track_temp"] = round(float(tt), 1)
                    if at:
                        sim_data["weather"]["air_temp"] = round(float(at), 1)
                except Exception:
                    pass

        self._sim = sim_data
        self.update()

    def paintEvent(self, event):
        p = self.begin_overlay_painter()

        d = self._sim
        tires = d["tires"]
        w = d["weather"]

        if not draw_3d_card_bezel(p, 4, 4, BASE_W - 8, BASE_H - 8):
            bg_path = QPainterPath()
            bg_path.addRoundedRect(QRectF(6, 6, BASE_W - 12, BASE_H - 12), 12, 12)
            p.fillPath(bg_path, QColor(12, 15, 22, 242))

        # Header (Non-overlapping Left & Right boxes)
        p.setPen(QColor("#FFFFFF"))
        p.setFont(QFont("Segoe UI", 8, QFont.Black))
        draw_elided_text(p, QRectF(16, 12, 225, 20), Qt.AlignLeft | Qt.AlignVCenter, "SIMHUB TIRE THERMALS & WEATHER")
        p.setPen(QColor("#FF2A2A"))
        p.setFont(QFont("Segoe UI", 8, QFont.Black))
        p.drawText(QRectF(BASE_W - 85, 12, 68, 20), Qt.AlignRight | Qt.AlignVCenter, "SOFT C5")

        # 4 Tire Pods: FL, FR, RL, RR
        pods = [
            ("FL", tires["FL"], 16, 38, True),
            ("FR", tires["FR"], 174, 38, False),
            ("RL", tires["RL"], 16, 136, True),
            ("RR", tires["RR"], 174, 136, False),
        ]
        for label, td, px, py, is_left in pods:
            self._draw_tire_pod(p, label, td, px, py, 145, 90, is_left)

        # Weather & Surface Radar Box at Bottom
        wy = 234
        w_rect = QRectF(14, wy, BASE_W - 28, 68)
        p.setBrush(QColor(18, 22, 34, 235))
        p.setPen(QPen(QColor(255, 255, 255, 35), 1.0))
        p.drawRoundedRect(w_rect, 8, 8)

        p.setPen(QColor("#00F5D4"))
        p.setFont(QFont("Segoe UI", 7, QFont.Black))
        draw_elided_text(p, QRectF(22, wy + 5, BASE_W - 44, 14), Qt.AlignLeft | Qt.AlignVCenter, f"TRACK METEO STATION | GRIP: {w['grip_level']}")

        p.setPen(QColor("#FFFFFF"))
        p.setFont(QFont("Consolas", 8, QFont.Bold))
        draw_elided_text(p, QRectF(22, wy + 24, 145, 18), Qt.AlignLeft | Qt.AlignVCenter, f"TRACK: {w['track_temp']} C")
        draw_elided_text(p, QRectF(175, wy + 24, 140, 18), Qt.AlignLeft | Qt.AlignVCenter, f"AIR:   {w['air_temp']} C")

        p.setPen(QColor("#38BDF8"))
        draw_elided_text(p, QRectF(22, wy + 44, 145, 18), Qt.AlignLeft | Qt.AlignVCenter, f"RAIN:  {w['rain_pct']}% ({w['track_wetness']})")
        p.setPen(QColor("#CBD5E1"))
        draw_elided_text(p, QRectF(175, wy + 44, 140, 18), Qt.AlignLeft | Qt.AlignVCenter, f"WIND:  {w['wind_speed_kmh']} km/h ({w['wind_dir_deg']} deg)")

        self.end_overlay_painter(p)

    def _draw_tire_pod(self, p: QPainter, label: str, td: dict, x: int, y: int, w: int, h: int, is_left: bool):
        p.setBrush(QColor(18, 22, 34, 235))
        p.setPen(QPen(QColor(255, 255, 255, 35), 1.0))
        p.drawRoundedRect(QRectF(x, y, w, h), 8, 8)

        p.setPen(QColor("#00F5D4"))
        p.setFont(QFont("Segoe UI", 8, QFont.Black))
        p.drawText(QRectF(x + 8, y + 4, 28, 16), Qt.AlignLeft | Qt.AlignVCenter, label)

        p.setPen(QColor("#FFFFFF"))
        p.setFont(QFont("Consolas", 8, QFont.Bold))
        p.drawText(QRectF(x + 34, y + 4, 62, 16), Qt.AlignCenter, f"{td['psi']} PSI")

        p.setPen(QColor("#10B981"))
        p.drawText(QRectF(x + w - 48, y + 4, 40, 16), Qt.AlignRight | Qt.AlignVCenter, f"{td['wear']}%")

        t_o, t_m, t_i = td["temps"]
        zones = [t_o, t_m, t_i] if is_left else [t_i, t_m, t_o]
        zw = 30
        zh = 40
        zx_start = x + 10
        for idx, temp_val in enumerate(zones):
            zr = QRectF(zx_start + idx * (zw + 3), y + 24, zw, zh)
            p.setBrush(_temp_to_color(temp_val))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(zr, 4, 4)
            p.setPen(QColor(10, 12, 18))
            p.setFont(QFont("Consolas", 8, QFont.Black))
            p.drawText(zr, Qt.AlignCenter, f"{temp_val}C")

        brk_t = td["brake_temp"]
        bx = x + w - 32
        b_rect = QRectF(bx, y + 24, 22, 40)
        p.setBrush(_brake_to_color(brk_t))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(b_rect, 4, 4)
        p.setPen(QColor(10, 12, 18))
        p.setFont(QFont("Consolas", 6, QFont.Black))
        p.drawText(b_rect, Qt.AlignCenter, f"BRK\n{brk_t}")

        p.setBrush(QColor(32, 38, 52))
        p.drawRoundedRect(QRectF(x + 8, y + h - 14, w - 16, 7), 3, 3)
        p.setBrush(QColor("#10B981") if td["wear"] > 70 else QColor("#F59E0B"))
        p.drawRoundedRect(QRectF(x + 8, y + h - 14, (w - 16) * (td["wear"] / 100.0), 7), 3, 3)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TiresWeatherOverlay()
    win.show()
    sys.exit(app.exec_())
