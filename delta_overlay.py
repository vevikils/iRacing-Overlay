"""
delta_overlay.py - RaceLab / SimHub Dynamic Lap Delta & Sector Splits Bar
==========================================================================
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

OVERLAY_KEY = "delta_overlay"
BASE_W, BASE_H = 380, 105


class DeltaOverlay(ResizableLockableOverlay):
    def __init__(self):
        super().__init__(OVERLAY_KEY, BASE_W, BASE_H, default_x=790, default_y=40)
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
                    sim_data["delta"] = float(self.ir["LapDeltaToBestLap"] or 0.0)
                except Exception:
                    pass

        self._sim = sim_data
        self.update()

    def paintEvent(self, event):
        p = self.begin_overlay_painter()

        d = self._sim
        delta = d["delta"]
        if not draw_3d_card_bezel(p, 4, 4, BASE_W - 8, BASE_H - 8):
            bg_path = QPainterPath()
            bg_path.addRoundedRect(QRectF(6, 6, BASE_W - 12, BASE_H - 12), 12, 12)
            p.fillPath(bg_path, QColor(12, 15, 22, 240))

        # Horizontal Center-Zero Split Bar
        bar_rect = QRectF(18, 16, BASE_W - 36, 20)
        p.setBrush(QColor(24, 30, 44))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(bar_rect, 6, 6)

        mid_x = BASE_W / 2.0
        max_w = (BASE_W - 36) / 2.0
        norm = max(-1.0, min(1.0, delta / 1.0))
        if norm <= 0:
            w_fill = abs(norm) * max_w
            p.setBrush(QColor("#10B981"))
            p.drawRoundedRect(QRectF(mid_x - w_fill, 16, w_fill, 20), 5, 5)
        else:
            w_fill = norm * max_w
            p.setBrush(QColor("#EF4444"))
            p.drawRoundedRect(QRectF(mid_x, 16, w_fill, 20), 5, 5)

        p.setPen(QPen(QColor("#FFFFFF"), 2.0))
        p.drawLine(int(mid_x), 14, int(mid_x), 38)

        # Delta Number + Best & Last Lap
        sign = "+" if delta > 0 else ""
        p.setPen(QColor("#10B981") if delta <= 0 else QColor("#EF4444"))
        p.setFont(QFont("Consolas", 19, QFont.Black))
        p.drawText(QRectF(18, 42, 145, 36), Qt.AlignLeft | Qt.AlignVCenter, f"{sign}{delta:.3f}s")

        bst_m = int(d["best_lap"] // 60)
        bst_s = d["best_lap"] % 60
        p.setPen(QColor("#C084FC"))
        p.setFont(QFont("Consolas", 8, QFont.Bold))
        draw_elided_text(p, QRectF(165, 44, 195, 16), Qt.AlignRight | Qt.AlignVCenter, f"BEST: {bst_m}:{bst_s:06.3f} (PURPLE)")
        p.setPen(QColor("#94A3B8"))
        draw_elided_text(p, QRectF(165, 62, 195, 16), Qt.AlignRight | Qt.AlignVCenter, f"S1 {d['s1_delta']:+.2f} | S2 {d['s2_delta']:+.2f} | S3 {d['s3_delta']:+.2f}")

        self.end_overlay_painter(p)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DeltaOverlay()
    win.show()
    sys.exit(app.exec_())
