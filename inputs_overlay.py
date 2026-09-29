import sys
import time
import ctypes
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QLinearGradient, QFont, QPainterPath, QBrush
import os
import json

# Import shared utilities
import overlay_utils

class TelemetryDataThread(QThread):
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
                time.sleep(1/60) # 60 FPS for ultra-smooth graphs
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
                if not self.ir.startup():
                    time.sleep(1)
                    continue

            try:
                self.ir.freeze_var_buffer_latest()
                
                t = self.ir['Throttle']
                b = self.ir['Brake']
                c = self.ir['Clutch']
                
                data = {
                    'Throttle': float(t) if t is not None else 0.0,
                    'Brake': float(b) if b is not None else 0.0,
                    'Clutch': float(c) if c is not None else 0.0,
                }
                self.data_updated.emit(data)
            except Exception as e:
                pass
                
            time.sleep(1/60)

    def stop(self):
        self.running = False
        self.wait()

class TelemetryHistoryWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.history_throttle = [0.0] * 120
        self.history_brake = [0.0] * 120
        self.theme_colors = None
        self.setFixedHeight(100)
        self.setMinimumWidth(320)

    def set_theme_colors(self, colors):
        self.theme_colors = colors
        self.update()

    def update_history(self, throttle, brake):
        self.history_throttle.pop(0)
        self.history_throttle.append(throttle)
        self.history_brake.pop(0)
        self.history_brake.append(brake)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Fondo oscuro del gráfico
        painter.fillRect(self.rect(), QColor(5, 5, 5, 120))
        
        width = self.width()
        height = self.height()
        points = len(self.history_throttle)
        dx = width / (points - 1)

        # 1. Dibujar líneas de rejilla (Grid)
        pen_grid = QPen(QColor(255, 255, 255, 15), 1, Qt.DotLine)
        painter.setPen(pen_grid)
        
        # Grid horizontal (25%, 50%, 75%)
        for y_pct in [0.25, 0.50, 0.75]:
            y_pos = int(height * y_pct)
            painter.drawLine(0, y_pos, width, y_pos)
            
        # Grid vertical (divisiones temporales)
        for i in range(1, 4):
            x_pos = int(width * (i / 4.0))
            painter.drawLine(x_pos, 0, x_pos, height)

        # Colores por defecto si no se han establecido
        throttle_color = QColor(overlay_utils.get_theme_colors("classic_red")["chart_throttle"])
        brake_color = QColor(overlay_utils.get_theme_colors("classic_red")["chart_brake"])
        
        if self.theme_colors:
            throttle_color = QColor(self.theme_colors["chart_throttle"])
            brake_color = QColor(self.theme_colors["chart_brake"])

        # 2. Dibujar áreas rellenas con degradado
        # Relleno del Freno (Rojo)
        path_brake_fill = QPainterPath()
        path_brake_fill.moveTo(0, height)
        for i in range(points):
            x = i * dx
            y = height - (self.history_brake[i] * height * 0.96) # 0.96 para evitar recortes arriba
            path_brake_fill.lineTo(x, y)
        path_brake_fill.lineTo(width, height)
        path_brake_fill.closeSubpath()
        
        grad_brake = QLinearGradient(0, 0, 0, height)
        grad_brake.setColorAt(0, QColor(brake_color.red(), brake_color.green(), brake_color.blue(), 60))
        grad_brake.setColorAt(1, QColor(brake_color.red(), brake_color.green(), brake_color.blue(), 0))
        painter.fillPath(path_brake_fill, QBrush(grad_brake))

        # Relleno del Acelerador (Verde)
        path_throttle_fill = QPainterPath()
        path_throttle_fill.moveTo(0, height)
        for i in range(points):
            x = i * dx
            y = height - (self.history_throttle[i] * height * 0.96)
            path_throttle_fill.lineTo(x, y)
        path_throttle_fill.lineTo(width, height)
        path_throttle_fill.closeSubpath()
        
        grad_throttle = QLinearGradient(0, 0, 0, height)
        grad_throttle.setColorAt(0, QColor(throttle_color.red(), throttle_color.green(), throttle_color.blue(), 60))
        grad_throttle.setColorAt(1, QColor(throttle_color.red(), throttle_color.green(), throttle_color.blue(), 0))
        painter.fillPath(path_throttle_fill, QBrush(grad_throttle))

        # 3. Dibujar las líneas de contorno gruesas
        # Línea de Freno
        pen_brake_line = QPen(brake_color, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen_brake_line)
        path_brake = QPainterPath()
        path_brake.moveTo(0, height - (self.history_brake[0] * height * 0.96))
        for i in range(1, points):
            path_brake.lineTo(i * dx, height - (self.history_brake[i] * height * 0.96))
        painter.drawPath(path_brake)

        # Línea de Acelerador
        pen_throttle_line = QPen(throttle_color, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen_throttle_line)
        path_throttle = QPainterPath()
        path_throttle.moveTo(0, height - (self.history_throttle[0] * height * 0.96))
        for i in range(1, points):
            path_throttle.lineTo(i * dx, height - (self.history_throttle[i] * height * 0.96))
        painter.drawPath(path_throttle)

class InputOverlay(QWidget):
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
        
        self.data_thread = TelemetryDataThread()
        self.data_thread.data_updated.connect(self.update_view)
        self.data_thread.start()
        
        # Timer para recargar configuración dinámicamente
        self.config_timer = QTimer(self)
        self.config_timer.timeout.connect(self.reload_settings)
        self.config_timer.start(500)
        
        self.drag_pos = None

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.main_layout = QHBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)

        # Contenedor Principal
        self.container = QFrame()
        self.container.setObjectName("mainContainer")
        self.main_layout.addWidget(self.container)
        
        container_layout = QHBoxLayout(self.container)
        container_layout.setContentsMargins(12, 10, 12, 10)
        container_layout.setSpacing(12)
        
        # Historial Gráfico
        self.history_chart = TelemetryHistoryWidget()
        container_layout.addWidget(self.history_chart)
        
        # Barras Verticales de Inputs (Acelerador, Freno, Embrague)
        self.bars_layout = QHBoxLayout()
        self.bars_layout.setSpacing(8)
        
        # Embrague (Clutch) - Barra Gris/Azul
        self.clutch_bar_bg, self.clutch_bar_fill = self.create_bar("#8e8e93")
        # Freno (Brake) - Barra Roja
        self.brake_bar_bg, self.brake_bar_fill = self.create_bar("#ff3b30")
        # Acelerador (Throttle) - Barra Verde
        self.throttle_bar_bg, self.throttle_bar_fill = self.create_bar("#34c759")
        
        self.bars_layout.addWidget(self.clutch_bar_bg)
        self.bars_layout.addWidget(self.brake_bar_bg)
        self.bars_layout.addWidget(self.throttle_bar_bg)
        
        container_layout.addLayout(self.bars_layout)
        
        self.setGeometry(100, 600, 480, 120)

    def create_bar(self, color):
        # El contenedor (fondo de la barra) con estilo premium de cápsula
        bg = QFrame()
        bg.setFixedWidth(16)
        bg.setFixedHeight(100)
        bg.setStyleSheet("background: rgba(255, 255, 255, 0.06); border-radius: 8px;")
        
        # La barra que se llena (hija del contenedor)
        fill = QFrame(bg)
        fill.setFixedWidth(16)
        fill.setStyleSheet(f"background: {color}; border-radius: 8px;")
        fill.move(0, 100)
        fill.setFixedHeight(0)
        
        return bg, fill

    def reload_settings(self):
        config = overlay_utils.load_config()
        
        # 1. Opacidad
        opacity = config.get("opacity", 0.90)
        if opacity != self.current_opacity:
            self.setWindowOpacity(opacity)
            self.current_opacity = opacity

        # 2. Bloqueo (Click-through)
        locked = config.get("locked", False)
        if locked != self.current_locked:
            self.setAttribute(Qt.WA_TransparentForMouseEvents, locked)
            self.current_locked = locked

        # 4. Comprobar si el lanzador restableció la posición
        pos = config.get('inputs_overlay')
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
            
            # Actualizar contenedor
            self.container.setStyleSheet(f"""
                #mainContainer {{
                    background: {colors["bg_gradient"]};
                    border: 1.5px solid {colors["border"]};
                    border-radius: 10px;
                }}
            """)
            
            # Pasar colores al widget de gráfico
            self.history_chart.set_theme_colors(colors)
            
            # Actualizar colores de las barras de inputs
            self.throttle_bar_fill.setStyleSheet(f"background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {colors['chart_throttle']}, stop:1 rgba(48, 209, 88, 120)); border-radius: 8px;")
            self.brake_bar_fill.setStyleSheet(f"background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {colors['chart_brake']}, stop:1 rgba(255, 69, 58, 120)); border-radius: 8px;")
            self.clutch_bar_fill.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8e8e93, stop:1 rgba(142, 142, 147, 120)); border-radius: 8px;")

    def update_view(self, data):
        t = data.get('Throttle', 0.0)
        b = data.get('Brake', 0.0)
        c = data.get('Clutch', 0.0)
        
        # Actualizar Barras (0.0 a 1.0)
        t_height = int(t * 100)
        self.throttle_bar_fill.setFixedHeight(t_height)
        self.throttle_bar_fill.move(0, 100 - t_height)
        
        b_height = int(b * 100)
        self.brake_bar_fill.setFixedHeight(b_height)
        self.brake_bar_fill.move(0, 100 - b_height)
        
        c_height = int(c * 100)
        self.clutch_bar_fill.setFixedHeight(c_height)
        self.clutch_bar_fill.move(0, 100 - c_height)
        
        # Actualizar Historial
        self.history_chart.update_history(t, b)

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
        config['inputs_overlay'] = {
            'x': self.x(),
            'y': self.y()
        }
        self.last_saved_x = self.x()
        self.last_saved_y = self.y()
        overlay_utils.save_config(config)

    def load_position(self):
        config = overlay_utils.load_config()
        pos = config.get('inputs_overlay')
        if pos:
            self.move(pos['x'], pos['y'])
            self.last_saved_x = pos['x']
            self.last_saved_y = pos['y']

    def closeEvent(self, event):
        self.data_thread.stop()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    overlay = InputOverlay()
    overlay.show()
    sys.exit(app.exec_())
