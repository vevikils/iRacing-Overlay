"""
fuel_overlay.py - RaceLab / SimHub Pro Fuel & Pit Strategy Calculator
======================================================================
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

OVERLAY_KEY = "fuel_overlay"
BASE_W, BASE_H = 340, 175


class FuelOverlay(ResizableLockableOverlay):
    def __init__(self):
        super().__init__(OVERLAY_KEY, BASE_W, BASE_H, default_x=1520, default_y=830)
        self.ir = irsdk.IRSDK()
        self.is_connected = False
        self._sim = get_sim_telemetry(time.time())

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_telemetry)
        self.timer.start(100)

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
                    fl = float(self.ir["FuelLevel"] or 0.0)
                    sim_data["fuel_level"] = fl
                    sim_data["fuel_est_laps"] = fl / max(0.5, sim_data["fuel_per_lap"])
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
            p.fillPath(bg_path, QColor(12, 15, 22, 242))

        # Header (Strictly separated from PIT WINDOW OK badge)
        p.setPen(QColor("#FFFFFF"))
        p.setFont(QFont("Segoe UI", 8, QFont.Black))
        draw_elided_text(p, QRectF(18, 12, 205, 22), Qt.AlignLeft | Qt.AlignVCenter, "FUEL & PIT STRATEGY")

        pw_rect = QRectF(BASE_W - 104, 12, 86, 22)
        p.setBrush(QColor(16, 185, 129, 45))
        p.setPen(QPen(QColor("#10B981"), 1.2))
        p.drawRoundedRect(pw_rect, 5, 5)
        p.setPen(QColor("#10B981"))
        p.setFont(QFont("Segoe UI", 7, QFont.Black))
        p.drawText(pw_rect, Qt.AlignCenter, "PIT WINDOW OK")

        # 4 Telemetry Metric Cards
        cards = [
            ("REMAINING", f"{d['fuel_level']:.1f} L", "#00F5D4"),
            ("EST. LAPS", f"{d['fuel_est_laps']:.1f} L", "#10B981" if d['fuel_est_laps'] > 4 else "#EF4444"),
            ("AVG / LAP", f"{d['fuel_per_lap']:.2f} L", "#FFFFFF"),
            ("ADD AT PIT", f"+{d['fuel_needed']:.1f} L", "#F59E0B"),
        ]
        cw = (BASE_W - 36 - 18) / 4.0
        for idx, (lbl, val, col) in enumerate(cards):
            cx = 18 + idx * (cw + 6)
            c_rect = QRectF(cx, 44, cw, 64)
            p.setBrush(QColor(18, 22, 34, 235))
            p.setPen(QPen(QColor(255, 255, 255, 35), 1.0))
            p.drawRoundedRect(c_rect, 7, 7)

            p.setPen(QColor("#8E96AA"))
            p.setFont(QFont("Segoe UI", 6, QFont.Bold))
            p.drawText(QRectF(cx + 2, 50, cw - 4, 14), Qt.AlignCenter, lbl)

            p.setPen(QColor(col))
            p.setFont(QFont("Consolas", 10, QFont.Black))
            p.drawText(QRectF(cx + 2, 68, cw - 4, 30), Qt.AlignCenter, val)

        # Fuel Tank Progress Bar
        bar_bg = QRectF(18, 120, BASE_W - 36, 16)
        p.setBrush(QColor(24, 28, 40))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(bar_bg, 5, 5)

        pct = max(0.0, min(1.0, d["fuel_level"] / 30.0))
        fill_col = QColor("#10B981") if pct > 0.25 else QColor("#EF4444")
        p.setBrush(fill_col)
        p.drawRoundedRect(QRectF(18, 120, (BASE_W - 36) * pct, 16), 5, 5)

        p.setPen(QColor("#94A3B8"))
        p.setFont(QFont("Segoe UI", 7, QFont.Bold))
        draw_elided_text(
            p,
            QRectF(18, 142, BASE_W - 36, 18),
            Qt.AlignCenter,
            f"SAFE TARGET: {d['fuel_per_lap']*0.96:.2f} L/LAP (LIFT & COAST) | BY VEVI"
        )
        self.end_overlay_painter(p)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = FuelOverlay()
    win.show()
    sys.exit(app.exec_())
