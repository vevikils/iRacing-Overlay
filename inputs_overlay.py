"""
inputs_overlay.py - RaceLab / SimHub Pro Pedal Telemetry, Trace & 3D Steering Wheel
===================================================================================
Author: vevi (VEVIkils556@gmail.com)
Version: 3.5 Supreme (Blender 3D PBR + Resizable & Lockable + Clean Typography)
"""

import sys
import math
import time
from collections import deque
import irsdk
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt5.QtGui import (
    QPainter, QColor, QFont, QPen, QPainterPath
)
from overlay_utils import (
    get_sim_telemetry, get_3d_asset, draw_3d_card_bezel, draw_elided_text,
    ResizableLockableOverlay
)

OVERLAY_KEY = "inputs_overlay"
BASE_W, BASE_H = 510, 175
HISTORY_LEN = 160


class InputsOverlay(ResizableLockableOverlay):
    def __init__(self):
        super().__init__(OVERLAY_KEY, BASE_W, BASE_H, default_x=380, default_y=800)
        self.ir = irsdk.IRSDK()
        self.is_connected = False

        self.thr_hist = deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN)
        self.brk_hist = deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN)
        now = time.time()
        for i in range(HISTORY_LEN):
            s = get_sim_telemetry(now - (HISTORY_LEN - i) * 0.032)
            self.thr_hist.append(s["throttle"])
            self.brk_hist.append(s["brake"])

        self._sim = get_sim_telemetry(now)

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
                    sim_data["throttle"] = float(self.ir["Throttle"] or 0.0)
                    sim_data["brake"] = float(self.ir["Brake"] or 0.0)
                    sim_data["clutch"] = 1.0 - float(self.ir["Clutch"] or 1.0)
                    sim_data["steer_deg"] = -math.degrees(float(self.ir["SteeringWheelAngle"] or 0.0))
                except Exception:
                    pass

        self.thr_hist.append(sim_data["throttle"])
        self.brk_hist.append(sim_data["brake"])
        self._sim = sim_data
        self.update()

    def paintEvent(self, event):
        p = self.begin_overlay_painter()

        d = self._sim
        if not draw_3d_card_bezel(p, 4, 4, BASE_W - 8, BASE_H - 8):
            bg_path = QPainterPath()
            bg_path.addRoundedRect(QRectF(6, 6, BASE_W - 12, BASE_H - 12), 12, 12)
            p.fillPath(bg_path, QColor(12, 15, 22, 240))

        # 1. Scrolling Telemetry Trace Area (Left)
        gx, gy, gw, gh = 16, 16, 285, BASE_H - 32
        p.setBrush(QColor(18, 22, 32, 230))
        p.setPen(QPen(QColor(255, 255, 255, 30), 1.0))
        p.drawRoundedRect(QRectF(gx, gy, gw, gh), 8, 8)

        # Dedicated Header Strip inside plot so traces never touch the title text
        p.fillRect(QRectF(gx + 2, gy + 2, gw - 4, 16), QColor(14, 18, 28, 220))
        p.setPen(QColor("#8E96AA"))
        p.setFont(QFont("Segoe UI", 7, QFont.Bold))
        draw_elided_text(p, QRectF(gx + 8, gy + 3, 180, 14), Qt.AlignLeft | Qt.AlignVCenter, "INPUT TELEMETRY | 60Hz")

        plot_y = gy + 20
        plot_h = gh - 26
        p.setPen(QPen(QColor(255, 255, 255, 20), 1.0, Qt.DashLine))
        for f in (0.25, 0.5, 0.75):
            p.drawLine(int(gx + 4), int(plot_y + plot_h * f), int(gx + gw - 4), int(plot_y + plot_h * f))

        def build_curve(arr):
            path = QPainterPath()
            n = len(arr)
            for idx, v in enumerate(arr):
                px = gx + 6 + (idx / max(1, n - 1)) * (gw - 12)
                py = plot_y + plot_h - max(0.0, min(1.0, v)) * plot_h
                if idx == 0:
                    path.moveTo(px, py)
                else:
                    path.lineTo(px, py)
            return path

        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor("#00F58A"), 2.3))
        p.drawPath(build_curve(self.thr_hist))
        p.setPen(QPen(QColor("#FF1E38"), 2.5))
        p.drawPath(build_curve(self.brk_hist))

        # 2. Vertical Pedal Bars (C, B, T)
        bx_start = gx + gw + 12
        bars = [
            ("C", d["clutch"], "#38BDF8"),
            ("B", d["brake"], "#FF1E38"),
            ("T", d["throttle"], "#00F58A"),
        ]
        bw = 22
        bh = gh - 22
        for idx, (lbl, val, col) in enumerate(bars):
            bx = bx_start + idx * (bw + 8)
            p.setBrush(QColor(24, 28, 40, 230))
            p.setPen(QPen(QColor(255, 255, 255, 35), 1.0))
            p.drawRoundedRect(QRectF(bx, gy, bw, bh), 4, 4)

            fill_h = max(0.0, min(1.0, val)) * bh
            p.setBrush(QColor(col))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(bx, gy + bh - fill_h, bw, fill_h), 4, 4)

            p.setPen(QColor("#FFFFFF"))
            p.setFont(QFont("Consolas", 7, QFont.Black))
            p.drawText(QRectF(bx - 4, gy + bh + 4, bw + 8, 16), Qt.AlignCenter, f"{int(val*100)}")

        # 3. Rotating 3D F1 2026 Steering Wheel (Right)
        sw_cx = BASE_W - 56
        sw_cy = BASE_H / 2.0 - 8
        r = 38

        p.save()
        p.translate(sw_cx, sw_cy)
        p.rotate(d["steer_deg"])
        sw_pix = get_3d_asset("f1_2026_steering_wheel_3d.png")
        if not sw_pix.isNull():
            p.drawPixmap(QRectF(-r, -r, r * 2, r * 2), sw_pix, QRectF(0, 0, sw_pix.width(), sw_pix.height()))
        else:
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor("#00F5D4"), 2.0))
            p.drawEllipse(QPointF(0, 0), r, r)
        p.restore()

        p.setPen(QColor("#00F5D4"))
        p.setFont(QFont("Consolas", 8, QFont.Bold))
        p.drawText(QRectF(sw_cx - 44, sw_cy + r + 4, 88, 16), Qt.AlignCenter, f"{d['steer_deg']:+.1f} deg")

        self.end_overlay_painter(p)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = InputsOverlay()
    win.show()
    sys.exit(app.exec_())
