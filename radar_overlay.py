import sys
import time
import os
import ctypes
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont

import overlay_utils

class RadarDataThread(QThread):
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
                t = time.time()
                data = overlay_utils.get_sim_telemetry(t)
                self.data_updated.emit(data)
                time.sleep(1/30)
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
                car_lr = self.ir['CarLeftRight'] or 0
                # 0=clear, 1=left, 2=right, 3=both, 4=2 cars left, 5=2 cars right
                spot_l = car_lr in [1, 3, 4]
                spot_r = car_lr in [2, 3, 5]

                self.data_updated.emit({
                    'SpotterLeft': spot_l,
                    'SpotterRight': spot_r,
                    'CarLeftRight': car_lr
                })
            except:
                pass
            time.sleep(1/30)

    def stop(self):
        self.running = False
        self.wait()

class RadarOverlay(QWidget):
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

        self.data_thread = RadarDataThread()
        self.data_thread.data_updated.connect(self.update_view)
        self.data_thread.start()

        self.config_timer = QTimer(self)
        self.config_timer.timeout.connect(self.reload_settings)
        self.config_timer.start(500)

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(360, 100)

        self.container = QFrame(self)
        self.container.setGeometry(0, 0, 360, 100)
        self.container.setObjectName("radarContainer")

        layout = QHBoxLayout(self.container)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # Left Radar indicator
        self.left_indicator = QFrame()
        self.left_indicator.setFixedWidth(100)
        left_lay = QVBoxLayout(self.left_indicator)
        left_lay.setAlignment(Qt.AlignCenter)
        self.lbl_left = QLabel("◄ CAR LEFT")
        self.lbl_left.setAlignment(Qt.AlignCenter)
        self.lbl_left.setStyleSheet("font-size: 11px; font-weight: 900; color: #666666;")
        left_lay.addWidget(self.lbl_left)
        layout.addWidget(self.left_indicator)

        # Center Car Representation
        center_box = QFrame()
        center_box.setFixedWidth(110)
        center_lay = QVBoxLayout(center_box)
        center_lay.setAlignment(Qt.AlignCenter)
        center_lay.setSpacing(2)
        
        lbl_title = QLabel("PROXIMITY RADAR")
        lbl_title.setStyleSheet("font-size: 8px; font-weight: 900; color: #888888; letter-spacing: 1px;")
        lbl_title.setAlignment(Qt.AlignCenter)
        
        self.car_icon = QLabel("🏎️")
        self.car_icon.setAlignment(Qt.AlignCenter)
        self.car_icon.setStyleSheet("font-size: 24px;")

        self.lbl_status = QLabel("CLEAR")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet("font-size: 10px; font-weight: 900; color: #34c759;")

        center_lay.addWidget(lbl_title)
        center_lay.addWidget(self.car_icon)
        center_lay.addWidget(self.lbl_status)
        layout.addWidget(center_box)

        # Right Radar indicator
        self.right_indicator = QFrame()
        self.right_indicator.setFixedWidth(100)
        right_lay = QVBoxLayout(self.right_indicator)
        right_lay.setAlignment(Qt.AlignCenter)
        self.lbl_right = QLabel("CAR RIGHT ►")
        self.lbl_right.setAlignment(Qt.AlignCenter)
        self.lbl_right.setStyleSheet("font-size: 11px; font-weight: 900; color: #666666;")
        right_lay.addWidget(self.lbl_right)
        layout.addWidget(self.right_indicator)

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

        pos = config.get('radar_overlay')
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
                #radarContainer {{
                    background: {colors["bg_gradient"]};
                    border: 1.5px solid {colors["border"]};
                    border-radius: 10px;
                }}
            """)

    def update_view(self, data):
        spot_l = data.get('SpotterLeft', False)
        spot_r = data.get('SpotterRight', False)

        if spot_l:
            self.left_indicator.setStyleSheet("background: rgba(255, 59, 48, 0.35); border: 1.5px solid #ff3b30; border-radius: 6px;")
            self.lbl_left.setStyleSheet("font-size: 11px; font-weight: 900; color: #ffffff;")
        else:
            self.left_indicator.setStyleSheet("background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 6px;")
            self.lbl_left.setStyleSheet("font-size: 11px; font-weight: 900; color: #444444;")

        if spot_r:
            self.right_indicator.setStyleSheet("background: rgba(255, 59, 48, 0.35); border: 1.5px solid #ff3b30; border-radius: 6px;")
            self.lbl_right.setStyleSheet("font-size: 11px; font-weight: 900; color: #ffffff;")
        else:
            self.right_indicator.setStyleSheet("background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 6px;")
            self.lbl_right.setStyleSheet("font-size: 11px; font-weight: 900; color: #444444;")

        if spot_l and spot_r:
            self.lbl_status.setText("3 WIDE!")
            self.lbl_status.setStyleSheet("font-size: 10px; font-weight: 900; color: #ff0054;")
        elif spot_l:
            self.lbl_status.setText("HOLD RIGHT")
            self.lbl_status.setStyleSheet("font-size: 10px; font-weight: 900; color: #ff9f1c;")
        elif spot_r:
            self.lbl_status.setText("HOLD LEFT")
            self.lbl_status.setStyleSheet("font-size: 10px; font-weight: 900; color: #ff9f1c;")
        else:
            self.lbl_status.setText("CLEAR")
            self.lbl_status.setStyleSheet("font-size: 10px; font-weight: 900; color: #2ec4b6;")

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
        config['radar_overlay'] = {'x': self.x(), 'y': self.y()}
        self.last_saved_x = self.x()
        self.last_saved_y = self.y()
        overlay_utils.save_config(config)

    def load_position(self):
        config = overlay_utils.load_config()
        pos = config.get('radar_overlay')
        if pos:
            self.move(pos['x'], pos['y'])
            self.last_saved_x = pos['x']
            self.last_saved_y = pos['y']

    def closeEvent(self, event):
        self.data_thread.stop()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    overlay = RadarOverlay()
    overlay.show()
    sys.exit(app.exec_())
