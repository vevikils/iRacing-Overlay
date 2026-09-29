"""
overlay1.py  -  Gear & Speed Overlay v2.0
Marcha gigante, velocimetro, RPM y shift lights premium.

Autor: vevi (VEVIkils556@gmail.com)
Version: 2.0.0
"""
import sys, time, os
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout,
                              QHBoxLayout, QFrame, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPainter, QBrush, QLinearGradient, QPen
import overlay_utils


class IRacingDataThread(QThread):
    data_updated            = pyqtSignal(dict)
    connection_status_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.ir = None
        self.running = True
        self.last_status = False
        try:
            import irsdk
            self.ir = irsdk.IRSDK()
        except Exception:
            pass

    def run(self):
        while self.running:
            cfg = overlay_utils.load_config()
            if cfg.get("sim_mode", False):
                if not self.last_status:
                    self.connection_status_changed.emit(True)
                    self.last_status = True
                self.data_updated.emit(overlay_utils.get_sim_telemetry(time.time()))
                time.sleep(1 / 30)
                continue
            if not self.ir:
                try:
                    import irsdk
                    self.ir = irsdk.IRSDK()
                except Exception:
                    time.sleep(1); continue
            connected = self.ir.is_initialized and self.ir.is_connected
            if not connected:
                if self.last_status:
                    self.connection_status_changed.emit(False)
                self.last_status = False
                if not self.ir.startup():
                    time.sleep(1); continue
            if not self.last_status:
                self.connection_status_changed.emit(True)
                self.last_status = True
            try:
                self.ir.freeze_var_buffer_latest()
                speed = self.ir["Speed"] or 0.0
                rpm   = self.ir["RPM"] or 0.0
                gear  = self.ir["Gear"] or 0
                pct   = self.ir["ShiftIndicatorPct"] or 0.0
                self.data_updated.emit({"Speed": speed, "RPM": rpm, "Gear": gear, "ShiftIndicatorPct": pct})
            except Exception:
                pass
            time.sleep(1 / 30)
        if self.ir and self.ir.is_initialized:
            self.ir.shutdown()

    def stop(self):
        self.running = False
        self.wait()


class ShiftLightStrip(QWidget):
    """Barra de shift lights dibujada con QPainter - 10 LEDs premium."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(10)
        self.pct = 0.0
        self.accent_color = QColor("#9d4edd")
        self.flash_state  = False

    def set_pct(self, pct: float, accent: QColor):
        self.pct = pct
        self.accent_color = accent
        self.update()

    def set_flash(self, state: bool):
        self.flash_state = state
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        n = 10
        gap = 4
        led_w = (w - gap * (n - 1)) / n

        if self.pct >= 0.96:
            # Todos parpadean en acento
            for i in range(n):
                x = i * (led_w + gap)
                c = self.accent_color if self.flash_state else QColor(255, 255, 255, 15)
                p.setBrush(QBrush(c))
                p.setPen(Qt.NoPen)
                p.drawRoundedRect(int(x), 0, int(led_w), self.height(), 3, 3)
        else:
            num_on = int(self.pct * n)
            for i in range(n):
                x = i * (led_w + gap)
                if i < num_on:
                    if i < 4:   c = QColor("#38b000")
                    elif i < 7: c = QColor("#fcbf49")
                    else:       c = QColor("#ef233c")
                else:
                    c = QColor(255, 255, 255, 15)
                p.setBrush(QBrush(c))
                p.setPen(Qt.NoPen)
                p.drawRoundedRect(int(x), 0, int(led_w), self.height(), 3, 3)
        p.end()


class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.script_dir = overlay_utils.get_base_path()
        self.current_theme   = ""
        self.current_opacity = 0.0
        self.current_locked  = False
        self.last_x = self.last_y = -9999
        self.drag_pos = None

        self._init_ui()
        QTimer.singleShot(120, self._load_position)

        self.data_thread = IRacingDataThread()
        self.data_thread.data_updated.connect(self._on_data)
        self.data_thread.connection_status_changed.connect(self._on_connection)
        self.data_thread.start()

        self.cfg_timer = QTimer(self)
        self.cfg_timer.timeout.connect(self._reload_settings)
        self.cfg_timer.start(500)

        self.flash_timer = QTimer(self)
        self.flash_timer.timeout.connect(self._toggle_flash)
        self.flash_timer.start(100)
        self._flash = False

    # ── UI ──────────────────────────────────────
    def _init_ui(self):
        self.setWindowTitle("iRacing Gear v2")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.container = QWidget()
        self.container.setObjectName("gearContainer")
        root.addWidget(self.container)

        lay = QVBoxLayout(self.container)
        lay.setContentsMargins(16, 12, 16, 14)
        lay.setSpacing(4)

        # Header row
        hdr = QHBoxLayout()
        self.dot = QFrame()
        self.dot.setFixedSize(7, 7)
        self.dot.setStyleSheet("border-radius:3px; background:#ff3b30;")
        self.lbl_status = QLabel("OFFLINE")
        self.lbl_status.setStyleSheet("font-size:8px; font-weight:900; letter-spacing:1.5px; color:#8e8e93; font-family:'Segoe UI';")
        hdr.addWidget(self.dot, 0, Qt.AlignVCenter)
        hdr.addSpacing(5)
        hdr.addWidget(self.lbl_status, 0, Qt.AlignVCenter)
        hdr.addStretch()
        lay.addLayout(hdr)

        # Shift lights
        self.shift_strip = ShiftLightStrip()
        lay.addWidget(self.shift_strip)
        lay.addSpacing(2)

        # Gear number
        self.lbl_gear = QLabel("N")
        self.lbl_gear.setAlignment(Qt.AlignCenter)
        self.lbl_gear.setStyleSheet(
            "font-size:90px; font-weight:900; color:#ffffff; "
            "font-family:'Segoe UI', Arial; margin:-8px 0;"
        )
        self.gear_glow = QGraphicsDropShadowEffect(self)
        self.gear_glow.setBlurRadius(24)
        self.gear_glow.setOffset(0, 0)
        self.gear_glow.setColor(QColor(157, 78, 221, 160))
        self.lbl_gear.setGraphicsEffect(self.gear_glow)
        lay.addWidget(self.lbl_gear)

        # Speed row
        spd_row = QHBoxLayout()
        spd_row.setAlignment(Qt.AlignCenter)
        spd_row.setSpacing(3)
        self.lbl_speed = QLabel("0")
        self.lbl_speed.setStyleSheet(
            "font-size:28px; font-weight:800; color:#ffffff; "
            "font-family:'Segoe UI', monospace;"
        )
        self.lbl_unit = QLabel("KM/H")
        self.lbl_unit.setStyleSheet(
            "font-size:9px; font-weight:bold; color:#8e8e93; "
            "margin-top:12px; font-family:'Segoe UI';"
        )
        spd_row.addWidget(self.lbl_speed)
        spd_row.addWidget(self.lbl_unit)
        lay.addLayout(spd_row)

        # RPM label
        self.lbl_rpm = QLabel("0 RPM")
        self.lbl_rpm.setAlignment(Qt.AlignCenter)
        self.lbl_rpm.setStyleSheet(
            "font-size:9px; font-weight:bold; color:#8e8e93; "
            "font-family:'Segoe UI', monospace;"
        )
        lay.addWidget(self.lbl_rpm)

        self.setGeometry(100, 100, 190, 240)
        self._reload_settings()

    # ── Ajustes dinamicos ───────────────────────
    def _reload_settings(self):
        cfg = overlay_utils.load_config()

        op = cfg.get("opacity", 0.93)
        if op != self.current_opacity:
            self.setWindowOpacity(op)
            self.current_opacity = op

        lk = cfg.get("locked", False)
        if lk != self.current_locked:
            self.setAttribute(Qt.WA_TransparentForMouseEvents, lk)
            self.current_locked = lk

        pos = cfg.get("gear_overlay", {})
        if pos.get("x") != self.last_x or pos.get("y") != self.last_y:
            self.move(pos["x"], pos["y"])
            self.last_x = pos["x"]
            self.last_y = pos["y"]

        theme = cfg.get("theme", "racelab_pro")
        if theme != self.current_theme:
            self.current_theme = theme
            c = overlay_utils.get_theme_colors(theme)
            self.container.setStyleSheet(f"""
                #gearContainer {{
                    background: {c['bg_gradient']};
                    border: 1.5px solid {c['border']};
                    border-radius: 12px;
                }}
            """)
            ar = c["accent_rgb"]
            self.gear_glow.setColor(QColor(ar[0], ar[1], ar[2], 170))
            self.lbl_speed.setStyleSheet(
                f"font-size:28px; font-weight:800; color:{c['text']}; "
                "font-family:'Segoe UI', monospace;"
            )

    def _toggle_flash(self):
        self._flash = not self._flash

    # ── Slots de datos ──────────────────────────
    def _on_connection(self, connected: bool):
        c = overlay_utils.get_theme_colors(self.current_theme)
        if connected:
            self.lbl_status.setText("LIVE")
            self.dot.setStyleSheet(f"border-radius:3px; background:{c['accent']};")
        else:
            self.lbl_status.setText("OFFLINE")
            self.dot.setStyleSheet("border-radius:3px; background:#ff3b30;")
            self.lbl_gear.setText("N")
            self.lbl_speed.setText("0")
            self.lbl_rpm.setText("0 RPM")
            self.shift_strip.set_pct(0.0, QColor(c["accent"]))

    def _on_data(self, data: dict):
        c = overlay_utils.get_theme_colors(self.current_theme)
        g = data.get("Gear", 0)
        if g == 0:
            self.lbl_gear.setText("N")
            self.lbl_gear.setStyleSheet("font-size:90px; font-weight:900; color:#ffffff; font-family:'Segoe UI'; margin:-8px 0;")
        elif g == -1:
            self.lbl_gear.setText("R")
            self.lbl_gear.setStyleSheet("font-size:90px; font-weight:900; color:#ef233c; font-family:'Segoe UI'; margin:-8px 0;")
        else:
            self.lbl_gear.setText(str(g))
            self.lbl_gear.setStyleSheet(f"font-size:90px; font-weight:900; color:{c['text']}; font-family:'Segoe UI'; margin:-8px 0;")

        spd_kmh = data.get("Speed", 0.0) * 3.6
        self.lbl_speed.setText(f"{spd_kmh:.0f}")
        rpm = data.get("RPM", 0.0)
        self.lbl_rpm.setText(f"{rpm:,.0f} RPM")

        pct = data.get("ShiftIndicatorPct", 0.0)
        ar  = c["accent_rgb"]
        self.shift_strip.set_pct(pct, QColor(ar[0], ar[1], ar[2]))
        if pct >= 0.96:
            self.shift_strip.set_flash(self._flash)

    # ── Drag ────────────────────────────────────
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and not self.testAttribute(Qt.WA_TransparentForMouseEvents):
            self.drag_pos = e.globalPos() - self.frameGeometry().topLeft()
        elif e.button() == Qt.RightButton:
            lk = not self.testAttribute(Qt.WA_TransparentForMouseEvents)
            self.setAttribute(Qt.WA_TransparentForMouseEvents, lk)
            self.current_locked = lk
            cfg = overlay_utils.load_config()
            cfg["locked"] = lk
            overlay_utils.save_config(cfg)

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and self.drag_pos and not self.testAttribute(Qt.WA_TransparentForMouseEvents):
            self.move(e.globalPos() - self.drag_pos)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.drag_pos = None
            cfg = overlay_utils.load_config()
            cfg["gear_overlay"] = {"x": self.x(), "y": self.y()}
            self.last_x = self.x(); self.last_y = self.y()
            overlay_utils.save_config(cfg)

    def _load_position(self):
        cfg = overlay_utils.load_config()
        pos = cfg.get("gear_overlay", {})
        if pos:
            self.move(pos["x"], pos["y"])
            self.last_x = pos["x"]; self.last_y = pos["y"]

    def closeEvent(self, e):
        self.data_thread.stop()
        e.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = OverlayWindow()
    w.show()
    sys.exit(app.exec_())
