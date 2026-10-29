"""
standings_overlay.py - RaceLab Pro Full Standings, iRating Gain/Loss & Pit Tracker
===================================================================================
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

OVERLAY_KEY = "standings_overlay"
BASE_W, BASE_H = 620, 445


def _fmt_lap(sec: float) -> str:
    m = int(sec // 60)
    s = sec % 60
    return f"{m}:{s:06.3f}"


class StandingsOverlay(ResizableLockableOverlay):
    def __init__(self):
        super().__init__(OVERLAY_KEY, BASE_W, BASE_H, default_x=40, default_y=60)
        self._sim = get_sim_telemetry(time.time())

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_telemetry)
        self.timer.start(100)

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

        # Header
        hdr = QRectF(12, 12, BASE_W - 24, 32)
        p.setBrush(QColor(255, 85, 0, 225))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(hdr, 7, 7)

        p.setPen(QColor("#FFFFFF"))
        p.setFont(QFont("Segoe UI", 9, QFont.Black))
        draw_elided_text(p, QRectF(20, 12, 275, 32), Qt.AlignLeft | Qt.AlignVCenter, "RACELAB PRO MULTICLASS STANDINGS")

        p.setFont(QFont("Consolas", 8, QFont.Bold))
        draw_elided_text(
            p,
            QRectF(300, 12, BASE_W - 318, 32),
            Qt.AlignRight | Qt.AlignVCenter,
            f"SOF {d['sof']} | LAP {d['current_lap']}/{d['total_laps']} | PISTA {d['weather']['track_temp']}C"
        )

        # Column Headers
        col_y = 48
        p.setPen(QColor("#8E96AA"))
        p.setFont(QFont("Segoe UI", 7, QFont.Bold))
        p.drawText(QRectF(18, col_y, 28, 16), Qt.AlignCenter, "POS")
        p.drawText(QRectF(48, col_y, 32, 16), Qt.AlignCenter, "#")
        p.drawText(QRectF(84, col_y, 138, 16), Qt.AlignLeft, "DRIVER / TEAM")
        p.drawText(QRectF(224, col_y, 76, 16), Qt.AlignCenter, "iRATING (+/-)")
        p.drawText(QRectF(302, col_y, 48, 16), Qt.AlignCenter, "LIC/SR")
        p.drawText(QRectF(354, col_y, 46, 16), Qt.AlignCenter, "TIRE")
        p.drawText(QRectF(402, col_y, 36, 16), Qt.AlignCenter, "INC")
        p.drawText(QRectF(442, col_y, 72, 16), Qt.AlignRight, "BEST")
        p.drawText(QRectF(518, col_y, 82, 16), Qt.AlignRight, "GAP")

        row_y = 68
        row_h = 28
        for idx, drv in enumerate(d["standings"][:13]):
            ry = row_y + idx * row_h
            is_p = drv.get("is_player", False)
            r_rect = QRectF(12, ry, BASE_W - 24, row_h - 3)
            if is_p:
                p.setBrush(QColor(0, 245, 212, 48))
                p.setPen(QPen(QColor("#00F5D4"), 1.2))
                p.drawRoundedRect(r_rect, 4, 4)
            else:
                p.setBrush(QColor(20, 24, 34, 195 if idx % 2 == 0 else 155))
                p.setPen(Qt.NoPen)
                p.drawRoundedRect(r_rect, 4, 4)

            # POS
            p.setPen(QColor("#00F5D4") if is_p else QColor("#FFFFFF"))
            p.setFont(QFont("Consolas", 8, QFont.Black))
            p.drawText(QRectF(18, ry, 28, row_h - 3), Qt.AlignCenter, f"P{drv['pos']}")

            # Car # with Team Color pill
            num_rect = QRectF(49, ry + 3, 30, row_h - 9)
            p.setBrush(QColor(drv["color"]))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(num_rect, 3, 3)
            p.setPen(QColor("#101218") if drv["color"] in ("#00F5D4", "#27F4D2", "#52E252") else QColor("#FFFFFF"))
            p.setFont(QFont("Segoe UI", 7, QFont.Black))
            p.drawText(num_rect, Qt.AlignCenter, f"#{drv['num']}")

            # Driver Name (Elided cleanly so it never overflows or clips parentheses)
            p.setPen(QColor("#00F5D4") if is_p else QColor("#FFFFFF"))
            p.setFont(QFont("Segoe UI", 8, QFont.Bold))
            draw_elided_text(p, QRectF(84, ry, 136, row_h - 3), Qt.AlignLeft | Qt.AlignVCenter, drv["name"])

            # iRating + Gain/Loss
            ir_delta = +42 - idx * 7
            ir_str = f"{drv['ir']} ({ir_delta:+d})"
            p.setPen(QColor("#10B981") if ir_delta >= 0 else QColor("#EF4444"))
            p.setFont(QFont("Consolas", 8, QFont.Bold))
            p.drawText(QRectF(224, ry, 76, row_h - 3), Qt.AlignCenter, ir_str)

            # Safety Rating
            p.setPen(QColor("#38BDF8"))
            p.drawText(QRectF(302, ry, 48, row_h - 3), Qt.AlignCenter, drv["sr"])

            # Tire + Laps
            p.setPen(QColor("#FBBF24"))
            p.drawText(QRectF(354, ry, 46, row_h - 3), Qt.AlignCenter, f"{drv['tire']}({drv['laps_tire']}L)")

            # Incidents / Pits
            p.setPen(QColor("#CBD5E1"))
            p.drawText(QRectF(402, ry, 36, row_h - 3), Qt.AlignCenter, f"{drv['pits']}x")

            # Best Lap
            p.setPen(QColor("#C084FC") if drv.get("has_fastest_lap") else QColor("#E2E8F0"))
            p.drawText(QRectF(442, ry, 72, row_h - 3), Qt.AlignRight | Qt.AlignVCenter, _fmt_lap(drv["best"]))

            # Gap to Leader
            gap_str = "LEADER" if idx == 0 else f"+{drv['gap_leader']:.2f}s"
            p.setPen(QColor("#FF5500") if idx == 0 else QColor("#FFFFFF"))
            p.drawText(QRectF(518, ry, 82, row_h - 3), Qt.AlignRight | Qt.AlignVCenter, gap_str)

        self.end_overlay_painter(p)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = StandingsOverlay()
    win.show()
    sys.exit(app.exec_())
