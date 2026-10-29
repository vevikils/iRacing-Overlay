"""
overlay1.py - SimHub / RaceLab Pro Standalone Gear, RPM Shift LED & Speed Pod
==============================================================================
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

OVERLAY_KEY = "gear_overlay"
BASE_W, BASE_H = 260, 175


class IRacingOverlay(ResizableLockableOverlay):
    def __init__(self):
        super().__init__(OVERLAY_KEY, BASE_W, BASE_H, default_x=810, default_y=780)
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
                    spd = float(self.ir["Speed"] or 0.0)
                    sim_data["speed_kmh"] = int(round(spd * 3.6))
                    sim_data["speed_mph"] = int(round(spd * 2.23694))
                    sim_data["rpm"] = int(self.ir["RPM"] or 0)
                    sim_data["gear"] = int(self.ir["Gear"] or 0)
                except Exception:
                    pass

        self._sim = sim_data
        self.update()

    def paintEvent(self, event):
        p = self.begin_overlay_painter()

        d = self._sim
        if not draw_3d_card_bezel(p, 4, 4, BASE_W - 8, BASE_H - 8):
            bg_path = QPainterPath()
            bg_path.addRoundedRect(QRectF(6, 6, BASE_W - 12, BASE_H - 12), 14, 14)
            p.fillPath(bg_path, QColor(12, 15, 22, 242))

        # 12 Shift LEDs across top
        n_leds = 12
        lit = int(round(d["shift_pct"] * n_leds))
        lw = (BASE_W - 36 - (n_leds - 1) * 4) / n_leds
        for i in range(n_leds):
            lx = 18 + i * (lw + 4)
            lr = QRectF(lx, 16, lw, 12)
            if i < lit:
                c = QColor("#00F58A") if i < 4 else (QColor("#FF1E38") if i < 8 else QColor("#A855F7"))
                p.setBrush(c)
            else:
                p.setBrush(QColor(28, 34, 48))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(lr, 3, 3)

        # Giant Gear Readout Left
        g_box = QRectF(18, 38, 86, 102)
        p.setBrush(QColor(225, 6, 0, 230) if d["shift_pct"] > 0.88 else QColor(20, 25, 38, 240))
        p.setPen(QPen(QColor("#00F5D4"), 1.5))
        p.drawRoundedRect(g_box, 10, 10)

        g_str = "R" if d["gear"] == -1 else ("N" if d["gear"] == 0 else str(d["gear"]))
        p.setPen(QColor("#FFFFFF"))
        p.setFont(QFont("Segoe UI", 44, QFont.Black))
        p.drawText(g_box, Qt.AlignCenter, g_str)

        # Speed & RPM Right
        p.setPen(QColor("#FFFFFF"))
        p.setFont(QFont("Segoe UI", 30, QFont.Black))
        p.drawText(QRectF(114, 36, 126, 48), Qt.AlignRight | Qt.AlignVCenter, f"{d['speed_kmh']}")

        p.setPen(QColor("#00F5D4"))
        p.setFont(QFont("Segoe UI", 8, QFont.Black))
        p.drawText(QRectF(114, 82, 126, 18), Qt.AlignRight, f"KM/H | {d['speed_mph']} MPH")

        p.setPen(QColor("#CBD5E1"))
        p.setFont(QFont("Consolas", 11, QFont.Bold))
        p.drawText(QRectF(114, 106, 126, 24), Qt.AlignRight, f"{d['rpm']:,} RPM")

        p.setPen(QColor("#64748B"))
        p.setFont(QFont("Segoe UI", 7, QFont.Bold))
        draw_elided_text(p, QRectF(18, BASE_H - 24, BASE_W - 36, 14), Qt.AlignCenter, "DDU TELEMETRY POD | BY VEVI")
        self.end_overlay_painter(p)


GearOverlay = IRacingOverlay

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = IRacingOverlay()
    win.show()
    sys.exit(app.exec_())
