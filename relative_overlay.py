"""
relative_overlay.py - RaceLab Pro Relative Box (On-Track Gap, Tire, iR & SR)
=============================================================================
Author: vevi (VEVIkils556@gmail.com)
Version: 3.5 Supreme (Blender 3D PBR + Resizable & Lockable + Clean Typography)
"""

import sys
import time
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer, QRectF
from PyQt5.QtGui import (
    QPainter, QColor, QFont, QPen, QPainterPath
)
from overlay_utils import (
    get_sim_telemetry, draw_3d_card_bezel, draw_elided_text,
    ResizableLockableOverlay
)

OVERLAY_KEY = "relative_overlay"
BASE_W, BASE_H = 385, 245


class RelativeOverlay(ResizableLockableOverlay):
    def __init__(self):
        super().__init__(OVERLAY_KEY, BASE_W, BASE_H, default_x=1490, default_y=530)
        self._sim = get_sim_telemetry(time.time())

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_telemetry)
        self.timer.start(80)

    def update_telemetry(self):
        self.sync_window_from_config()
        self._sim = get_sim_telemetry(time.time())
        self.update()

    def paintEvent(self, event):
        p = self.begin_overlay_painter()

        d = self._sim
        if not draw_3d_card_bezel(p, 4, 4, BASE_W - 8, BASE_H - 8):
            bg_path = QPainterPath()
            bg_path.addRoundedRect(QRectF(6, 6, BASE_W - 12, BASE_H - 12), 12, 12)
            p.fillPath(bg_path, QColor(12, 15, 22, 242))

        # Header (Non-overlapping Left & Right boxes)
        p.setPen(QColor("#FFFFFF"))
        p.setFont(QFont("Segoe UI", 8, QFont.Black))
        draw_elided_text(p, QRectF(16, 12, 195, 22), Qt.AlignLeft | Qt.AlignVCenter, "RACELAB RELATIVE BOX")
        p.setPen(QColor("#00F5D4"))
        p.setFont(QFont("Consolas", 8, QFont.Bold))
        draw_elided_text(p, QRectF(BASE_W - 165, 12, 148, 22), Qt.AlignRight | Qt.AlignVCenter, f"SOF {d['sof']} | {d['weather']['track_temp']}C")

        row_y = 40
        row_h = 31
        for idx, r in enumerate(d.get("relatives", [])):
            ry = row_y + idx * row_h
            is_p = r.get("is_player", False)
            rect = QRectF(12, ry, BASE_W - 24, row_h - 3)
            if is_p:
                p.setBrush(QColor(0, 245, 212, 48))
                p.setPen(QPen(QColor("#00F5D4"), 1.3))
                p.drawRoundedRect(rect, 5, 5)
            else:
                p.setBrush(QColor(20, 24, 34, 200 if idx % 2 == 0 else 160))
                p.setPen(Qt.NoPen)
                p.drawRoundedRect(rect, 5, 5)

            # POS
            p.setPen(QColor("#00F5D4") if is_p else QColor("#FFFFFF"))
            p.setFont(QFont("Consolas", 8, QFont.Black))
            p.drawText(QRectF(16, ry, 26, row_h - 3), Qt.AlignCenter, f"P{r['pos']}")

            # Car # badge
            num_r = QRectF(44, ry + 4, 28, row_h - 11)
            p.setBrush(QColor(r.get("color", "#E10600")))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(num_r, 3, 3)
            p.setPen(QColor("#101218") if r.get("color") == "#00F5D4" else QColor("#FFFFFF"))
            p.setFont(QFont("Segoe UI", 7, QFont.Black))
            p.drawText(num_r, Qt.AlignCenter, f"#{r['num']}")

            # Driver Name (Elided cleanly inside 118px)
            p.setPen(QColor("#00F5D4") if is_p else QColor("#FFFFFF"))
            p.setFont(QFont("Segoe UI", 8, QFont.Bold))
            draw_elided_text(p, QRectF(76, ry, 118, row_h - 3), Qt.AlignLeft | Qt.AlignVCenter, r["name"])

            # License & iRating
            sr_r = QRectF(198, ry + 5, 86, row_h - 13)
            p.setBrush(QColor(30, 38, 54))
            p.drawRoundedRect(sr_r, 3, 3)
            p.setPen(QColor("#38BDF8"))
            p.setFont(QFont("Consolas", 7, QFont.Bold))
            p.drawText(sr_r, Qt.AlignCenter, f"{r['sr']} | {r['ir']}")

            # Tire compound
            p.setPen(QColor("#FBBF24"))
            p.setFont(QFont("Segoe UI", 8, QFont.Black))
            p.drawText(QRectF(288, ry, 22, row_h - 3), Qt.AlignCenter, r.get("tire", "S"))

            # Relative Gap
            gap = r["gap"]
            gap_str = "0.00s" if is_p else f"{gap:+.2f}s"
            p.setPen(QColor("#00F5D4") if is_p else (QColor("#10B981") if gap > 0 else QColor("#F59E0B")))
            p.setFont(QFont("Consolas", 9, QFont.Black))
            p.drawText(QRectF(312, ry, 54, row_h - 3), Qt.AlignRight | Qt.AlignVCenter, gap_str)

        self.end_overlay_painter(p)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = RelativeOverlay()
    win.show()
    sys.exit(app.exec_())
