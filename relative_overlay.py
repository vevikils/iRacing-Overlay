import sys
import time
import os
import json
import ctypes
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPalette

# Import shared utilities
import overlay_utils

def format_lap_time(sec):
    if sec is None or sec <= 0:
        return "--"
    minutes = int(sec // 60)
    seconds = sec % 60
    if minutes > 0:
        return f"{minutes}:{seconds:05.2f}"
    else:
        return f"{seconds:.2f}"

class RelativeDataThread(QThread):
    data_updated = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        try:
            import irsdk
            self.ir = irsdk.IRSDK()
        except:
            self.ir = None
        self.running = True
        self.starting_irating = {}

    def run(self):
        while self.running:
            config = overlay_utils.load_config()
            sim_mode = config.get("sim_mode", False)

            if sim_mode:
                data = overlay_utils.get_sim_telemetry(time.time())
                self.data_updated.emit(data)
                time.sleep(0.1) # 10Hz is plenty for relative lists
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
                
                player_idx = self.ir['PlayerCarIdx']
                if player_idx is None:
                    time.sleep(1)
                    continue

                driver_info = self.ir['DriverInfo']
                drivers = driver_info.get('Drivers', [])
                
                # Mapear datos de conductores
                driver_map = {}
                total_irating = 0
                count_irating = 0
                
                for d in drivers:
                    idx = d['CarIdx']
                    ir = d['IRating']
                    
                    # Guardar iR inicial para el delta
                    if idx not in self.starting_irating and ir > 0:
                        self.starting_irating[idx] = ir
                    
                    ir_gain = ir - self.starting_irating.get(idx, ir)
                    
                    if ir > 0:
                        total_irating += ir
                        count_irating += 1
                    
                    driver_map[idx] = {
                        'Name': d['UserName'],
                        'IRating': ir,
                        'IRGain': ir_gain,
                        'LicString': d['LicString'],
                        'LicColor': d['LicColor'],
                        'CarNumber': d['CarNumber'],
                        'LicShort': d['LicString'][0] if d['LicString'] else '?',
                        'Class': d.get('CarClassShortName', '')
                    }

                sof = total_irating // count_irating if count_irating > 0 else 0
                
                gaps = self.ir['CarIdxF2Time']
                dist_pct = self.ir['CarIdxLapDistPct']
                positions = self.ir['CarIdxPosition']
                
                rel_list = []
                if gaps and dist_pct:
                    for i in range(len(gaps)):
                        if dist_pct[i] < 0: continue
                        
                        rel_list.append({
                            'CarIdx': i,
                            'Gap': gaps[i],
                            'Dist': dist_pct[i],
                            'Position': positions[i] if positions else 0
                        })

                player_dist = dist_pct[player_idx] if player_idx < len(dist_pct) else 0
                for item in rel_list:
                    d = item['Dist'] - player_dist
                    if d > 0.5: d -= 1.0
                    if d < -0.5: d += 1.0
                    item['RelDist'] = d

                rel_list.sort(key=lambda x: x['RelDist'], reverse=True)
                
                player_pos_in_list = -1
                for i, item in enumerate(rel_list):
                    if item['CarIdx'] == player_idx:
                        player_pos_in_list = i
                        break
                
                if player_pos_in_list != -1:
                    start = max(0, player_pos_in_list - 4)
                    end = min(len(rel_list), player_pos_in_list + 5)
                    final_relatives = rel_list[start:end]
                else:
                    final_relatives = rel_list[:9]

                incidents = self.ir['PlayerCarMyIncidents']
                max_incidents = self.ir['PlayerCarDriverIncidentLimit']
                if max_incidents == 255: max_incidents = "∞"
                
                last_laps = self.ir['CarIdxLastLapTime'] or []
                
                # RaceLab Pro Fuel & Spotter telemetry
                fuel_level = self.ir['FuelLevel'] if self.ir['FuelLevel'] is not None else 0.0
                fuel_per_lap = self.ir['FuelLevelPct']
                car_left_right = self.ir['CarLeftRight'] or 0
                # CarLeftRight flags in iRacing:
                # 0 = clear, 1 = car left, 2 = car right, 3 = car left and right, 4 = 2 cars left, 5 = 2 cars right
                spotter_l = (car_left_right in [1, 3, 4])
                spotter_r = (car_left_right in [2, 3, 5])
                
                data = {
                    'SOF': sof,
                    'Incidents': f"{incidents if incidents is not None else 0}/{max_incidents}",
                    'Relatives': [],
                    'PlayerIdx': player_idx,
                    'SessionTimeRemain': self.ir['SessionTimeRemain'],
                    'Lap': self.ir['Lap'],
                    'FuelLevel': fuel_level,
                    'SpotterLeft': spotter_l,
                    'SpotterRight': spotter_r
                }

                for item in final_relatives:
                    idx = item['CarIdx']
                    d_info = driver_map.get(idx, {})
                    
                    lic_str = d_info.get('LicString', '')
                    sr_val = lic_str.split(' ')[1] if (lic_str and ' ' in lic_str) else ''
                    
                    last_lap_sec = last_laps[idx] if idx < len(last_laps) else -1
                    last_lap_formatted = format_lap_time(last_lap_sec)
                    
                    data['Relatives'].append({
                        'CarIdx': idx,
                        'Position': item['Position'],
                        'Name': d_info.get('Name', 'Unknown'),
                        'Number': d_info.get('CarNumber', '--'),
                        'IRating': d_info.get('IRating', 0),
                        'IRGain': d_info.get('IRGain', 0),
                        'LicShort': d_info.get('LicShort', 'R'),
                        'LicColor': d_info.get('LicColor', 0xFFFFFF),
                        'Gap': item['Gap'],
                        'SR': sr_val,
                        'Class': d_info.get('Class', ''),
                        'LastLap': last_lap_formatted
                    })

                self.data_updated.emit(data)
            except Exception as e:
                pass
            time.sleep(0.1)

    def stop(self):
        self.running = False
        self.wait()

class RelativeRow(QFrame):
    def __init__(self, is_player=False):
        super().__init__()
        self.is_player = is_player
        self.current_theme = "classic_red"
        self.init_ui()

    def init_ui(self):
        self.setFixedHeight(39)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 0, 13, 0)
        self.layout.setSpacing(8)
        
        self.setObjectName("rowContainer")

        # Posición (P1, P2...)
        self.pos_label = QLabel("P-")
        self.pos_label.setFixedWidth(31)
        self.pos_label.setAlignment(Qt.AlignCenter)
        self.pos_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        
        # Car Number
        self.num_label = QLabel("00")
        self.num_label.setFixedWidth(31)
        self.num_label.setAlignment(Qt.AlignCenter)
        self.num_label.setStyleSheet("font-size: 14px; font-family: monospace; font-weight: bold;")
        
        # Name
        self.name_label = QLabel("Unknown")
        self.name_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        # Lic Badge (Official look)
        self.lic_tag = QLabel("R")
        self.lic_tag.setFixedSize(21, 21)
        self.lic_tag.setAlignment(Qt.AlignCenter)
        self.lic_tag.setStyleSheet("background: #ef233c; color: white; border-radius: 3px; font-size: 12px; font-weight: 900; font-family: monospace;")
        
        # Safety Rating Label
        self.sr_label = QLabel("2.50")
        self.sr_label.setFixedWidth(35)
        self.sr_label.setAlignment(Qt.AlignCenter)
        
        # IRating
        self.ir_label = QLabel("1.5k")
        self.ir_label.setFixedWidth(42)
        self.ir_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.ir_label.setStyleSheet("font-size: 14px; font-family: monospace; font-weight: bold;")
        
        # IRating Gain
        self.ir_gain_label = QLabel("")
        self.ir_gain_label.setFixedWidth(35)
        self.ir_gain_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.ir_gain_label.setStyleSheet("font-size: 12px; font-family: monospace;")
        
        # Class Label
        self.class_label = QLabel("GT3")
        self.class_label.setFixedWidth(50)
        self.class_label.setAlignment(Qt.AlignCenter)
        
        # Last Lap Label
        self.last_lap_label = QLabel("--")
        self.last_lap_label.setFixedWidth(65)
        self.last_lap_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        # Gap
        self.gap_label = QLabel("0.0")
        self.gap_label.setFixedWidth(65)
        self.gap_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.gap_label.setStyleSheet("font-size: 17px; font-weight: 900; font-family: 'Consolas', monospace;")

        self.layout.addWidget(self.pos_label)
        self.layout.addWidget(self.num_label)
        self.layout.addWidget(self.name_label)
        self.layout.addStretch()
        self.layout.addWidget(self.lic_tag)
        self.layout.addWidget(self.sr_label)
        self.layout.addWidget(self.ir_label)
        self.layout.addWidget(self.ir_gain_label)
        self.layout.addWidget(self.class_label)
        self.layout.addWidget(self.last_lap_label)
        self.layout.addWidget(self.gap_label)

        self.update_row_style()

    def update_row_style(self, theme="classic_red"):
        self.current_theme = theme
        colors = overlay_utils.get_theme_colors(theme)
        
        if self.is_player:
            # Player Highlight: Glowing golden/amber design
            bg_style = "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(252, 191, 73, 230), stop:1 rgba(247, 127, 0, 210)); border: 1px solid #fcbf49;"
            text_color = "#000000"
            self.setStyleSheet(f"""
                #rowContainer {{
                    {bg_style}
                    border-radius: 4px;
                }}
                QLabel {{
                    color: {text_color};
                    font-family: 'Segoe UI', sans-serif;
                }}
            """)
            self.class_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #000000;")
            self.sr_label.setStyleSheet("font-size: 13px; font-family: monospace; font-weight: bold; color: #000000;")
            self.last_lap_label.setStyleSheet("font-size: 14px; font-family: monospace; font-weight: bold; color: #000000;")
        else:
            # Other Drivers: Sleek transparent dark row
            bg_style = "background: rgba(255, 255, 255, 0.03);"
            text_color = "#ffffff"
            self.setStyleSheet(f"""
                #rowContainer {{
                    {bg_style}
                    border-radius: 4px;
                    border: 1px solid rgba(255, 255, 255, 0.03);
                }}
                #rowContainer:hover {{
                    background: rgba(255, 255, 255, 0.07);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                }}
                QLabel {{
                    color: {text_color};
                    font-family: 'Segoe UI', sans-serif;
                }}
            """)
            self.class_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #8e8e93;")
            self.sr_label.setStyleSheet("font-size: 13px; font-family: monospace; font-weight: bold; color: #ffffff;")
            self.last_lap_label.setStyleSheet("font-size: 14px; font-family: monospace; font-weight: bold; color: #ffffff;")

    def update_data(self, data):
        self.pos_label.setText(f"P{data['Position']}" if data['Position'] > 0 else "P-")
        self.num_label.setText(str(data['Number']))
        
        # Elide long names
        raw_name = data['Name']
        if len(raw_name) > 24:
            raw_name = raw_name[:22] + "..."
        self.name_label.setText(raw_name)
        
        # SR formatting
        self.sr_label.setText(str(data.get('SR', '')))
        
        # Class formatting
        self.class_label.setText(str(data.get('Class', '')))
        
        # Last Lap formatting
        self.last_lap_label.setText(str(data.get('LastLap', '--')))
        
        # iRating formatting
        ir = data['IRating']
        if ir >= 1000:
            self.ir_label.setText(f"{ir/1000:.1f}k")
        else:
            self.ir_label.setText(str(ir) if ir > 0 else "--")
            
        # iRating Gain formatting
        gain = data['IRGain']
        if gain > 0:
            self.ir_gain_label.setText(f"+{gain}")
            self.ir_gain_label.setStyleSheet("color: #34c759; font-size: 9px; font-family: monospace; font-weight: bold;" if not self.is_player else "color: #000000; font-size: 9px; font-family: monospace; font-weight: bold;")
        elif gain < 0:
            self.ir_gain_label.setText(f"{gain}")
            self.ir_gain_label.setStyleSheet("color: #ff3b30; font-size: 9px; font-family: monospace; font-weight: bold;" if not self.is_player else "color: #000000; font-size: 9px; font-family: monospace; font-weight: bold;")
        else:
            self.ir_gain_label.setText("")

        # License Badge
        lic_short = data['LicShort']
        colors = overlay_utils.get_theme_colors(self.current_theme)
        lic_bg = colors["lic_colors"].get(lic_short, '#555555')
        self.lic_tag.setText(lic_short)
        self.lic_tag.setStyleSheet(f"background: {lic_bg}; color: white; border-radius: 3px; font-size: 9px; font-weight: 900; font-family: monospace;")

        # Gap formatting (Cyan/Green for ahead, Red/Pink for behind)
        gap = data['Gap']
        if self.is_player:
            self.gap_label.setText("SELF")
            self.gap_label.setStyleSheet("font-size: 12px; font-weight: 900; color: #000000; font-family: 'Consolas', monospace;")
        else:
            if gap > 0:
                # Driver ahead
                self.gap_label.setText(f"+{gap:.1f}" if gap < 99 else "LAP")
                # Cyan/Emerald
                col = colors["accent_secondary"] if self.current_theme in ["cyberpunk", "toxic_green"] else "#30d158"
                self.gap_label.setStyleSheet(f"font-size: 13px; font-weight: 900; color: {col}; font-family: 'Consolas', monospace;")
            elif gap < 0:
                # Driver behind
                self.gap_label.setText(f"{gap:.1f}")
                # Orange/Red
                col = colors["accent"] if self.current_theme in ["cyberpunk", "classic_red"] else "#ff453a"
                self.gap_label.setStyleSheet(f"font-size: 13px; font-weight: 900; color: {col}; font-family: 'Consolas', monospace;")
            else:
                self.gap_label.setText("0.0")
                self.gap_label.setStyleSheet("font-size: 13px; font-weight: 900; color: #ffffff; font-family: 'Consolas', monospace;")

class RelativeOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.script_dir = overlay_utils.get_base_path()
        self.config_file = os.path.join(self.script_dir, "config.json")
        self.drag_pos = None
        
        self.current_theme = ""
        self.current_opacity = 0.0
        self.current_locked = False
        self.last_saved_x = -9999
        self.last_saved_y = -9999
        
        self.init_ui()
        QTimer.singleShot(100, self.load_position)
        
        self.data_thread = RelativeDataThread()
        self.data_thread.data_updated.connect(self.update_view)
        self.data_thread.start()

        # Timer para recargar configuración dinámicamente
        self.config_timer = QTimer(self)
        self.config_timer.timeout.connect(self.reload_settings)
        self.config_timer.start(500)

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(580)
        
        self.main_container = QFrame(self)
        self.main_container.setObjectName("mainContainer")
        
        self.main_layout = QVBoxLayout(self.main_container)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(6)

        # Header: SOF e Incidentes
        header = QHBoxLayout()
        header.setContentsMargins(4, 2, 4, 2)
        
        self.sof_label = QLabel("SOF --")
        self.sof_label.setStyleSheet("color: #8e8e93; font-weight: 900; font-size: 11px; letter-spacing: 0.5px;")
        
        title_label = QLabel("RELATIVE")
        title_label.setObjectName("titleLabel")
        title_label.setStyleSheet("font-weight: 900; font-size: 11px; letter-spacing: 1.5px;")
        
        self.inc_label = QLabel("× 0/--")
        self.inc_label.setStyleSheet("color: #ff3b30; font-weight: 900; font-size: 11px;")
        
        # Spotter Radar indicators (Car Left / Car Right RaceLab Pro style)
        self.radar_left = QLabel("◄ CAR LEFT")
        self.radar_left.setFixedHeight(18)
        self.radar_left.setStyleSheet("background: rgba(255, 59, 48, 0.2); color: #ff3b30; font-size: 9px; font-weight: 900; padding: 2px 6px; border-radius: 3px; border: 1px solid #ff3b30;")
        self.radar_left.setVisible(False)
        
        self.radar_right = QLabel("CAR RIGHT ►")
        self.radar_right.setFixedHeight(18)
        self.radar_right.setStyleSheet("background: rgba(255, 59, 48, 0.2); color: #ff3b30; font-size: 9px; font-weight: 900; padding: 2px 6px; border-radius: 3px; border: 1px solid #ff3b30;")
        self.radar_right.setVisible(False)
        
        header.addWidget(self.sof_label)
        header.addWidget(self.radar_left)
        header.addStretch()
        header.addWidget(title_label)
        header.addStretch()
        header.addWidget(self.radar_right)
        header.addWidget(self.inc_label)
        self.main_layout.addLayout(header)

        # Separador superior
        line_top = QFrame()
        line_top.setFixedHeight(1)
        line_top.setStyleSheet("background-color: rgba(255, 255, 255, 0.06);")
        self.main_layout.addWidget(line_top)

        # Columna de cabeceras (Headers)
        headers_layout = QHBoxLayout()
        headers_layout.setContentsMargins(11, 2, 14, 2)
        headers_layout.setSpacing(8)
        
        lbl_h_pos = QLabel("POS")
        lbl_h_pos.setFixedWidth(31)
        lbl_h_pos.setAlignment(Qt.AlignCenter)
        
        lbl_h_num = QLabel("#")
        lbl_h_num.setFixedWidth(31)
        lbl_h_num.setAlignment(Qt.AlignCenter)
        
        lbl_h_name = QLabel("DRIVER")
        lbl_h_name.setFixedWidth(140)
        lbl_h_name.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        lbl_h_lic = QLabel("LIC")
        lbl_h_lic.setFixedWidth(21)
        lbl_h_lic.setAlignment(Qt.AlignCenter)
        
        lbl_h_sr = QLabel("SR")
        lbl_h_sr.setFixedWidth(35)
        lbl_h_sr.setAlignment(Qt.AlignCenter)
        
        lbl_h_ir = QLabel("iR")
        lbl_h_ir.setFixedWidth(42)
        lbl_h_ir.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        lbl_h_irgain = QLabel("+/-")
        lbl_h_irgain.setFixedWidth(35)
        lbl_h_irgain.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        lbl_h_class = QLabel("CLASS")
        lbl_h_class.setFixedWidth(50)
        lbl_h_class.setAlignment(Qt.AlignCenter)
        
        lbl_h_last = QLabel("LAST LAP")
        lbl_h_last.setFixedWidth(65)
        lbl_h_last.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        lbl_h_gap = QLabel("GAP")
        lbl_h_gap.setFixedWidth(65)
        lbl_h_gap.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        for lbl in [lbl_h_pos, lbl_h_num, lbl_h_name, lbl_h_lic, lbl_h_sr, lbl_h_ir, lbl_h_irgain, lbl_h_class, lbl_h_last, lbl_h_gap]:
            lbl.setStyleSheet("color: #636366; font-size: 9px; font-weight: 800; font-family: 'Segoe UI', sans-serif;")
            
        headers_layout.addWidget(lbl_h_pos)
        headers_layout.addWidget(lbl_h_num)
        headers_layout.addWidget(lbl_h_name)
        headers_layout.addStretch()
        headers_layout.addWidget(lbl_h_lic)
        headers_layout.addWidget(lbl_h_sr)
        headers_layout.addWidget(lbl_h_ir)
        headers_layout.addWidget(lbl_h_irgain)
        headers_layout.addWidget(lbl_h_class)
        headers_layout.addWidget(lbl_h_last)
        headers_layout.addWidget(lbl_h_gap)
        
        self.main_layout.addLayout(headers_layout)

        # Contenedor de filas
        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(4)
        self.main_layout.addLayout(self.rows_layout)
        
        self.rows = []
        
        # Separador decorativo
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: rgba(255, 255, 255, 0.06);")
        self.main_layout.addWidget(line)

        # Footer: Tiempo de sesión, combustible inteligente RaceLab Pro y vueltas
        footer = QHBoxLayout()
        footer.setContentsMargins(4, 2, 4, 2)
        
        self.time_label = QLabel("REMAINING --:--:--")
        self.time_label.setStyleSheet("color: #8e8e93; font-weight: bold; font-size: 9px; font-family: monospace;")
        
        self.fuel_label = QLabel("⛽ FUEL: -- L (0.0 L/lap)")
        self.fuel_label.setStyleSheet("color: #00f5d4; font-weight: bold; font-size: 9px; font-family: monospace;")
        
        self.lap_label = QLabel("LAP --")
        self.lap_label.setStyleSheet("color: #8e8e93; font-weight: bold; font-size: 9px; font-family: monospace;")
        
        footer.addWidget(self.time_label)
        footer.addStretch()
        footer.addWidget(self.fuel_label)
        footer.addStretch()
        footer.addWidget(self.lap_label)
        self.main_layout.addLayout(footer)

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.main_container)
        self.layout().setContentsMargins(0,0,0,0)
        
        self.reload_settings()

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
        pos = config.get('relative_overlay')
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
            
            self.main_container.setStyleSheet(f"""
                #mainContainer {{
                    background: {colors["bg_gradient"]};
                    border: 1.5px solid {colors["border"]};
                    border-radius: 10px;
                }}
                #titleLabel {{
                    color: {colors["accent"]};
                }}
            """)
            
            # Actualizar filas
            for row in self.rows:
                row.update_row_style(theme)

    def update_view(self, data):
        # SOF e Incidencias
        sof = data.get('SOF', 0)
        if sof > 0:
            self.sof_label.setText(f"SOF {sof/1000:.1f}k")
        else:
            self.sof_label.setText("SOF --")
            
        self.inc_label.setText(f"× {data.get('Incidents', '0/--')}")
        
        # Session Footer
        t_rem = data.get('SessionTimeRemain', 0.0)
        if t_rem > 0 and t_rem < 604800: # Evitar tiempos infinitos antes de la carrera
            h = int(t_rem // 3600)
            m = int((t_rem % 3600) // 60)
            s = int(t_rem % 60)
            self.time_label.setText(f"REMAINING {h:02d}:{m:02d}:{s:02d}")
        else:
            self.time_label.setText("REMAINING --:--:--")
        
        lap = data.get('Lap', 0)
        self.lap_label.setText(f"LAP {lap}" if lap > 0 else "LAP --")

        # Spotter Proximity Radar (RaceLab Pro)
        spot_l = data.get('SpotterLeft', False)
        spot_r = data.get('SpotterRight', False)
        self.radar_left.setVisible(spot_l)
        self.radar_right.setVisible(spot_r)

        # Smart Fuel Calculation
        fuel_lvl = data.get('FuelLevel', 0.0)
        fuel_per_lap = data.get('FuelPerLap', 0.0)
        laps_left = data.get('FuelLapsRemaining', 0.0)
        if fuel_lvl > 0:
            if laps_left > 0:
                self.fuel_label.setText(f"⛽ {fuel_lvl:.1f}L (~{laps_left:.1f} laps)")
            else:
                self.fuel_label.setText(f"⛽ {fuel_lvl:.1f}L")
        else:
            self.fuel_label.setText("⛽ FUEL --")

        # Actualizar Relativos
        relatives = data.get('Relatives', [])
        player_idx = data.get('PlayerIdx', -1)
        
        # Crear nuevas filas si es necesario
        while len(self.rows) < len(relatives):
            row = RelativeRow()
            self.rows.append(row)
            self.rows_layout.addWidget(row)
            row.update_row_style(self.current_theme)
        
        for i, rel in enumerate(relatives):
            is_player = (rel['CarIdx'] == player_idx)
            
            # Recrear la fila si cambia su estado de jugador
            if self.rows[i].is_player != is_player:
                self.rows_layout.removeWidget(self.rows[i])
                self.rows[i].deleteLater()
                self.rows[i] = RelativeRow(is_player=is_player)
                self.rows_layout.insertWidget(i, self.rows[i])
                self.rows[i].update_row_style(self.current_theme)
            
            self.rows[i].update_data(rel)
            self.rows[i].show()
            
        # Ocultar filas sobrantes
        for i in range(len(relatives), len(self.rows)):
            self.rows[i].hide()

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
        config['relative_overlay'] = {'x': self.x(), 'y': self.y()}
        self.last_saved_x = self.x()
        self.last_saved_y = self.y()
        overlay_utils.save_config(config)

    def load_position(self):
        config = overlay_utils.load_config()
        pos = config.get('relative_overlay')
        if pos:
            self.move(pos['x'], pos['y'])
            self.last_saved_x = pos['x']
            self.last_saved_y = pos['y']

    def closeEvent(self, event):
        self.data_thread.stop()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    overlay = RelativeOverlay()
    overlay.show()
    sys.exit(app.exec_())
