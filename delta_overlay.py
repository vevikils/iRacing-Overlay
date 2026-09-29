import sys
import time
import ctypes
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QLinearGradient, QFont
import os
import json

# Import shared utilities
import overlay_utils

class DeltaDataThread(QThread):
    data_updated = pyqtSignal(dict)
    connection_status = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        try:
            import irsdk
            self.ir = irsdk.IRSDK()
        except:
            self.ir = None
        self.running = True
        self.last_connected = False

    def run(self):
        while self.running:
            config = overlay_utils.load_config()
            sim_mode = config.get("sim_mode", False)

            if sim_mode:
                if not self.last_connected:
                    self.connection_status.emit(True)
                    self.last_connected = True
                data = overlay_utils.get_sim_telemetry(time.time())
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

            is_connected = self.ir.is_initialized and self.ir.is_connected
            
            if not is_connected:
                if self.last_connected:
                    self.connection_status.emit(False)
                    self.last_connected = False
                
                if not self.ir.startup():
                    time.sleep(1)
                    continue
                else:
                    self.connection_status.emit(True)
                    self.last_connected = True
            
            try:
                self.ir.freeze_var_buffer_latest()
                
                delta = self.ir['LapDeltaToBestLap']
                if delta is None or delta == 0:
                    delta = self.ir['LapDeltaToSessionBest']
                
                data = {
                    'Delta': delta if delta is not None else 0.0
                }
                self.data_updated.emit(data)
            except Exception as e:
                pass
            
            time.sleep(1/30)

    def stop(self):
        self.running = False
        self.wait()

class DeltaOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.script_dir = overlay_utils.get_base_path()
        self.config_file = os.path.join(self.script_dir, "config.json")
        
        self.current_theme = ""
        self.current_opacity = 0.0
        self.current_locked = False
        self.last_saved_x = -9999
        self.last_saved_y = -9999
        
        self.init_ui()
        QTimer.singleShot(100, self.load_position)
        
        self.data_thread = DeltaDataThread()
        self.data_thread.data_updated.connect(self.update_view)
        self.data_thread.connection_status.connect(self.handle_connection)
        self.data_thread.start()
        
        # Timer para recargar configuración dinámicamente
        self.config_timer = QTimer(self)
        self.config_timer.timeout.connect(self.reload_settings)
        self.config_timer.start(500)
        
        self.drag_pos = None

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 60)
        
        # Contenedor principal
        self.container = QFrame(self)
        self.container.setGeometry(0, 0, 400, 60)
        self.container.setObjectName("deltaContainer")

        layout = QHBoxLayout(self.container)
        layout.setContentsMargins(15, 0, 15, 0)
        layout.setSpacing(15)
        
        # Etiqueta del Delta (Monospaced, muy legible y grande)
        self.delta_label = QLabel("0.00")
        self.delta_label.setAlignment(Qt.AlignCenter)
        self.delta_label.setFixedWidth(130)
        self.delta_label.setStyleSheet("font-size: 30px; font-weight: 900; color: #8e8e93; font-family: 'Consolas', monospace;")
        layout.addWidget(self.delta_label)

        # Contenedor de la Barra de Delta
        self.bar_container = QFrame()
        self.bar_container.setFixedHeight(16)
        self.bar_container.setStyleSheet("background: rgba(255, 255, 255, 0.05); border-radius: 8px;")
        
        # Barra de llenado (se ajusta dinámicamente de forma bidireccional)
        self.bar_fill = QFrame(self.bar_container)
        self.bar_fill.setFixedHeight(16)
        self.bar_fill.setGeometry(110, 0, 0, 16)
        
        # Línea central del Delta cero
        self.center_line = QFrame(self.bar_container)
        self.center_line.setFixedWidth(2)
        self.center_line.setFixedHeight(16)
        self.center_line.setStyleSheet("background-color: rgba(255, 255, 255, 0.25);")
        
        layout.addWidget(self.bar_container)
        
        self.reload_settings()

    def resizeEvent(self, event):
        # Reposicionar la línea central cuando se redimensione
        center_x = self.bar_container.width() // 2
        self.center_line.setGeometry(center_x, 0, 2, 16)
        super().resizeEvent(event)

    def reload_settings(self):
        config = overlay_utils.load_config()
        
        # 1. Opacidad
        opacity = config.get("opacity", 0.90)
        if opacity != self.current_opacity:
            self.setWindowOpacity(opacity)
            self.current_opacity = opacity

        # 2. Bloqueo
        locked = config.get("locked", False)
        if locked != self.current_locked:
            self.setAttribute(Qt.WA_TransparentForMouseEvents, locked)
            self.current_locked = locked

        # 4. Comprobar si el lanzador restableció la posición
        pos = config.get('delta_overlay')
        if pos:
            if pos['x'] != self.last_saved_x or pos['y'] != self.last_saved_y:
                self.move(pos['x'], pos['y'])
                self.last_saved_x = pos['x']
                self.last_saved_y = pos['y']

        # 3. Aplicar Estilos del Tema
        theme = config.get("theme", "classic_red")
        if theme != self.current_theme:
            self.current_theme = theme
            colors = overlay_utils.get_theme_colors(theme)
            
            self.container.setStyleSheet(f"""
                #deltaContainer {{
                    background: {colors["bg_gradient"]};
                    border: 1.5px solid {colors["border"]};
                    border-radius: 10px;
                }}
            """)
            
            # Forzar recolocación de línea central
            QTimer.singleShot(10, self.align_center_line)

    def align_center_line(self):
        center_x = self.bar_container.width() // 2
        self.center_line.setGeometry(center_x, 0, 2, 16)

    def handle_connection(self, connected):
        if not connected:
            self.delta_label.setText("OFF")
            self.delta_label.setStyleSheet("font-size: 24px; font-weight: 900; color: #8e8e93; font-family: 'Consolas', monospace;")
            self.bar_fill.setFixedWidth(0)

    def update_view(self, data):
        delta = data.get('Delta', 0.0)
        
        if delta == 0:
            self.delta_label.setText("0.00")
            self.delta_label.setStyleSheet("font-size: 30px; font-weight: 900; color: #ffffff; font-family: 'Consolas', monospace;")
            self.bar_fill.setGeometry(0, 0, 0, 0)
            return

        # Formatear el delta con signo y dos decimales
        prefix = "+" if delta > 0 else "-"
        abs_delta = abs(delta)
        self.delta_label.setText(f"{prefix}{abs_delta:.2f}")
        
        # Cargar colores de tema
        colors = overlay_utils.get_theme_colors(self.current_theme)
        
        # Color del texto y la barra según el tema y el signo del delta
        # Negativo = Gana tiempo (Verde/Cyan), Positivo = Pierde tiempo (Rojo/Rosa)
        gaining_color1 = ""
        gaining_color2 = ""
        losing_color1 = ""
        losing_color2 = ""
        
        if self.current_theme == "alpine_luxury":
            gaining_color1 = "#00e5ff"  # Electric Cyan
            gaining_color2 = "#0090ff"  # Alpine Blue
            losing_color1 = "#d4af37"   # Champagne Gold
            losing_color2 = "#aa8820"
            text_gaining = "#00e5ff"
            text_losing = "#d4af37"
        elif self.current_theme == "racelab_pro":
            gaining_color1 = "#00f5d4"  # Teal
            gaining_color2 = "#9d4edd"  # Purple
            losing_color1 = "#ff0054"   # Rose
            losing_color2 = "#a00030"
            text_gaining = "#00f5d4"
            text_losing = "#ff0054"
        elif self.current_theme == "cyberpunk":
            gaining_color1 = "#00f0ff"  # Cyan
            gaining_color2 = "#0088b3"
            losing_color1 = "#ff007f"   # Pink
            losing_color2 = "#b30059"
            text_gaining = "#00f0ff"
            text_losing = "#ff007f"
        elif self.current_theme == "toxic_green":
            gaining_color1 = "#39ff14"  # Neon Green
            gaining_color2 = "#1fa30a"
            losing_color1 = "#ccff00"   # Lime Yellow
            losing_color2 = "#8cae00"
            text_gaining = "#39ff14"
            text_losing = "#ccff00"
        elif self.current_theme == "electric_blue":
            gaining_color1 = "#30d158"  # Green
            gaining_color2 = "#1c9c3a"
            losing_color1 = "#ff453a"   # Red
            losing_color2 = "#b82b23"
            text_gaining = "#30d158"
            text_losing = "#ff453a"
        else: # classic_red
            gaining_color1 = "#34c759"  # Green
            gaining_color2 = "#1c9c3a"
            losing_color1 = "#ff3b30"   # Red
            losing_color2 = "#b82b23"
            text_gaining = "#34c759"
            text_losing = "#ff3b30"

        # Aplicar color de texto
        if delta < 0:
            self.delta_label.setStyleSheet(f"font-size: 30px; font-weight: 900; color: {text_gaining}; font-family: 'Consolas', monospace;")
        else:
            self.delta_label.setStyleSheet(f"font-size: 30px; font-weight: 900; color: {text_losing}; font-family: 'Consolas', monospace;")

        # Lógica de la barra (máximo delta representable en barra es 1.5 segundos)
        max_delta_scale = 1.5
        fill_fraction = min(abs_delta / max_delta_scale, 1.0)
        
        container_width = self.bar_container.width()
        center_x = container_width // 2
        
        # Ancho máximo de la barra es la mitad del contenedor
        max_bar_width = center_x
        bar_width = int(fill_fraction * max_bar_width)
        
        if delta < 0:
            # Gana tiempo: Se desplaza hacia la izquierda desde el centro
            self.bar_fill.setGeometry(center_x - bar_width, 0, bar_width, 16)
            self.bar_fill.setStyleSheet(f"""
                background: qlineargradient(x1:1, y1:0, x2:0, y2:0, stop:0 {gaining_color2}, stop:1 {gaining_color1});
                border-radius: 8px;
            """)
        else:
            # Pierde tiempo: Se desplaza hacia la derecha desde el centro
            self.bar_fill.setGeometry(center_x, 0, bar_width, 16)
            self.bar_fill.setStyleSheet(f"""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {losing_color2}, stop:1 {losing_color1});
                border-radius: 8px;
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.testAttribute(Qt.WA_TransparentForMouseEvents):
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.RightButton:
            is_transparent = self.testAttribute(Qt.WA_TransparentForMouseEvents)
            self.setAttribute(Qt.WA_TransparentForMouseEvents, not is_transparent)
            self.current_locked = not is_transparent
            config = overlay_utils.load_config()
            config["locked"] = not is_transparent
            overlay_utils.save_config(config)
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
        config['delta_overlay'] = {
            'x': self.x(),
            'y': self.y()
        }
        self.last_saved_x = self.x()
        self.last_saved_y = self.y()
        overlay_utils.save_config(config)

    def load_position(self):
        config = overlay_utils.load_config()
        pos = config.get('delta_overlay')
        if pos:
            self.move(pos['x'], pos['y'])
            self.last_saved_x = pos['x']
            self.last_saved_y = pos['y']

    def closeEvent(self, event):
        self.data_thread.stop()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    overlay = DeltaOverlay()
    overlay.show()
    sys.exit(app.exec_())
