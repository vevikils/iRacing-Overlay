import sys
import time
import os
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QProgressBar
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont

import overlay_utils

class FuelDataThread(QThread):
    data_updated = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        try:
            import irsdk
            self.ir = irsdk.IRSDK()
        except:
            self.ir = None
        self.running = True

    def run(self):
        while self.running:
            config = overlay_utils.load_config()
            sim_mode = config.get("sim_mode", False)

            if sim_mode:
                data = overlay_utils.get_sim_telemetry(time.time())
                self.data_updated.emit(data)
                time.sleep(1/10)
                continue

            if not self.ir:
                try:
                    import irsdk
                    self.ir = irsdk.IRSDK()
                except:
                    time.sleep(1)
                    continue

            if not (self.ir.is_initialized and self.ir.is_connected):
                if not self.ir.startup():
                    time.sleep(1)
                    continue

            try:
                self.ir.freeze_var_buffer_latest()
                fuel_level = self.ir['FuelLevel'] or 0.0
                fuel_pct = self.ir['FuelLevelPct'] or 0.0
                water_temp = self.ir['WaterTemp'] or 85.0
                oil_temp = self.ir['OilTemp'] or 90.0

                # Estimated 2.8L per lap if not calculated yet
                fuel_per_lap = 2.80
                laps_rem = fuel_level / fuel_per_lap if fuel_per_lap > 0 else 0

                self.data_updated.emit({
                    'FuelLevel': fuel_level,
                    'FuelPerLap': fuel_per_lap,
                    'FuelLapsRemaining': laps_rem,
                    'WaterTemp': water_temp,
                    'OilTemp': oil_temp
                })
            except:
                pass
            time.sleep(1/10)

    def stop(self):
        self.running = False
        self.wait()

class FuelOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.script_dir = overlay_utils.get_base_path()
        self.current_theme = ""
        self.current_opacity = 0.0
        self.current_locked = False
        self.last_saved_x = -9999
        self.last_saved_y = -9999
        self.drag_pos = None

        self.init_ui()
        QTimer.singleShot(100, self.load_position)

        self.data_thread = FuelDataThread()
        self.data_thread.data_updated.connect(self.update_view)
        self.data_thread.start()

        self.config_timer = QTimer(self)
        self.config_timer.timeout.connect(self.reload_settings)
        self.config_timer.start(500)

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(320, 110)

        self.container = QFrame(self)
        self.container.setGeometry(0, 0, 320, 110)
        self.container.setObjectName("fuelContainer")

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        # Header
        header = QHBoxLayout()
        lbl_title = QLabel("FUEL & STINT CALCULATOR")
        lbl_title.setStyleSheet("font-size: 9px; font-weight: 900; letter-spacing: 1.5px; color: #8e8e93;")
        self.lbl_laps_rem = QLabel("~0.0 LAPS")
        self.lbl_laps_rem.setStyleSheet("font-size: 11px; font-weight: 900; color: #00f5d4;")
        header.addWidget(lbl_title)
        header.addStretch()
        header.addWidget(self.lbl_laps_rem)
        layout.addLayout(header)

        # Main Fuel Remaining
        mid = QHBoxLayout()
        self.lbl_fuel_main = QLabel("45.0")
        self.lbl_fuel_main.setStyleSheet("font-size: 32px; font-weight: 900; font-family: monospace; color: #ffffff;")
        lbl_unit = QLabel("LITERS")
        lbl_unit.setStyleSheet("font-size: 10px; font-weight: 900; color: #8e8e93; margin-top: 14px;")

        mid.addWidget(self.lbl_fuel_main)
        mid.addWidget(lbl_unit)
        mid.addStretch()

        # Stats on right
        stats_col = QVBoxLayout()
        stats_col.setSpacing(2)
        self.lbl_per_lap = QLabel("AVG: 2.78 L/LAP")
        self.lbl_per_lap.setStyleSheet("font-size: 10px; font-weight: bold; color: #cccccc;")
        self.lbl_temp = QLabel("H2O: 85°C | OIL: 92°C")
        self.lbl_temp.setStyleSheet("font-size: 9px; font-weight: bold; color: #8e8e93;")
        stats_col.addWidget(self.lbl_per_lap)
        stats_col.addWidget(self.lbl_temp)
        mid.addLayout(stats_col)
        layout.addLayout(mid)

        # Fuel Level Bar
        self.fuel_bar = QProgressBar()
        self.fuel_bar.setFixedHeight(8)
        self.fuel_bar.setTextVisible(False)
        self.fuel_bar.setRange(0, 100)
        self.fuel_bar.setValue(80)
        self.fuel_bar.setStyleSheet("""
            QProgressBar {
                background: rgba(255, 255, 255, 0.08);
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00f5d4, stop:1 #9d4edd);
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.fuel_bar)

        self.reload_settings()

    def reload_settings(self):
        config = overlay_utils.load_config()
        opacity = config.get("opacity", 0.92)
        if opacity != self.current_opacity:
            self.setWindowOpacity(opacity)
            self.current_opacity = opacity

        locked = config.get("locked", False)
        if locked != self.current_locked:
            self.setAttribute(Qt.WA_TransparentForMouseEvents, locked)
            self.current_locked = locked

        pos = config.get('fuel_overlay')
        if pos:
            if pos['x'] != self.last_saved_x or pos['y'] != self.last_saved_y:
                self.move(pos['x'], pos['y'])
                self.last_saved_x = pos['x']
                self.last_saved_y = pos['y']

        theme = config.get("theme", "racelab_pro")
        if theme != self.current_theme:
            self.current_theme = theme
            colors = overlay_utils.get_theme_colors(theme)
            self.container.setStyleSheet(f"""
                #fuelContainer {{
                    background: {colors["bg_gradient"]};
                    border: 1.5px solid {colors["border"]};
                    border-radius: 10px;
                }}
            """)

    def update_view(self, data):
        fuel = data.get('FuelLevel', 0.0)
        laps_rem = data.get('FuelLapsRemaining', 0.0)
        per_lap = data.get('FuelPerLap', 0.0)
        w_temp = data.get('WaterTemp', 85.0)
        o_temp = data.get('OilTemp', 92.0)

        self.lbl_fuel_main.setText(f"{fuel:.1f}")
        self.lbl_laps_rem.setText(f"~{laps_rem:.1f} LAPS")
        self.lbl_per_lap.setText(f"AVG: {per_lap:.2f} L/LAP")
        self.lbl_temp.setText(f"H2O: {w_temp:.0f}°C | OIL: {o_temp:.0f}°C")

        # Assume max capacity ~ 60L or scale
        pct = min(100, max(0, int((fuel / 60.0) * 100)))
        self.fuel_bar.setValue(pct)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.testAttribute(Qt.WA_TransparentForMouseEvents):
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos and not self.testAttribute(Qt.WA_TransparentForMouseEvents):
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = None
            self.save_position()
            event.accept()

    def save_position(self):
        config = overlay_utils.load_config()
        config['fuel_overlay'] = {'x': self.x(), 'y': self.y()}
        self.last_saved_x = self.x()
        self.last_saved_y = self.y()
        overlay_utils.save_config(config)

    def load_position(self):
        config = overlay_utils.load_config()
        pos = config.get('fuel_overlay')
        if pos:
            self.move(pos['x'], pos['y'])
            self.last_saved_x = pos['x']
            self.last_saved_y = pos['y']

    def closeEvent(self, event):
        self.data_thread.stop()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    overlay = FuelOverlay()
    overlay.show()
    sys.exit(app.exec_())
