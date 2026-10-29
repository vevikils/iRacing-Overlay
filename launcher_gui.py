"""
launcher_gui.py - Control Center for iRacing HUD Overlay Suite v3.5 Supreme (3D Edition)
========================================================================================
Author: vevi (VEVIkils556@gmail.com)
Version: 3.5 Supreme (Blender 3D PBR + Individual Resize & Lock/Pin Controls)
"""

import sys
import os
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QFrame, QComboBox, QCheckBox,
    QGridLayout, QScrollArea, QSizeGrip
)
from PyQt5.QtCore import Qt, QTimer, QRectF
from PyQt5.QtGui import QFont, QPainter, QColor
from overlay_utils import load_config, save_config, THEMES, get_3d_asset, draw_3d_card_bezel


class Blender3DHeroFrame(QFrame):
    """Renders the Blender 4.2 3D PBR Hero Banner + 3D F1 2026 Steering Wheel emblem."""
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        pix = get_3d_asset("launcher_hero_banner_3d.png")
        if not pix.isNull():
            p.drawPixmap(QRectF(0, 0, self.width(), self.height()), pix, QRectF(0, 0, pix.width(), pix.height()))
        else:
            p.fillRect(self.rect(), QColor("#151B2B"))
        sw_pix = get_3d_asset("f1_2026_steering_wheel_3d.png")
        if not sw_pix.isNull():
            sz = self.height() - 12
            p.drawPixmap(QRectF(self.width() - sz - 18, 6, sz, sz), sw_pix, QRectF(0, 0, sw_pix.width(), sw_pix.height()))
        p.end()


class Blender3DCardFrame(QFrame):
    """Renders the Blender 4.2 3D Machined Titanium & Carbon Weave Card Bezel."""
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        if not draw_3d_card_bezel(p, 0, 0, self.width(), self.height(), "card_carbon_bezel_3d.png"):
            p.fillRect(self.rect(), QColor("#131824"))
        p.end()


OVERLAYS_META = [
    ("tv2026",    "tv2026_overlay",    "[TV 2026] Broadcast HUD 3D",   "F1 2026 Timing Tower + Telemetry Halo + X/Z Aero + MOM + ERS"),
    ("trophi",    "trophi_overlay",    "[IA] Trophi.ai Neural Coach",  "Frenada Real en Todas las Curvas + Gráfica Vivo vs Ref IA"),
    ("trackmap",  "trackmap_overlay",  "[GPS] Track Map + Pit Exit",   "Circuito 2D + Pilotos de tu Sesión + Predicción Pit Exit"),
    ("tires",     "tires_overlay",     "[SIMHUB] Tires & Weather",     "Termografía 4 Ruedas O/M/I + Discos de Freno + Estación Meteo"),
    ("standings", "standings_overlay", "[RACELAB] Pro Standings",      "Parrilla Completa + Ganancia iRating + SR + Compuesto + Gaps"),
    ("radar",     "radar_overlay",     "[RADAR] 3D Spatial Spotter",   "Radar Helicorsa 3D con Monoplazas FIA F4 + Alertas Laterales"),
    ("inputs",    "inputs_overlay",    "[INPUTS] Pedals & 3D Wheel",   "Telemetría 60Hz de Pedales + Barras + Volante F1 2026 3D"),
    ("relative",  "relative_overlay",  "[RELATIVE] On-Track Box",      "Rivales Cercanos en Pista + Licencia/iR + Neumático + Gap"),
    ("fuel",      "fuel_overlay",      "[FUEL] Pit Strategy Calc",     "Litros Restantes + Media L/Vuelta + Litros a Repostar en Pit"),
    ("gear",      "gear_overlay",      "[DDU] Shift RPM & Gear Pod",   "Arco de 12 LEDs de Cambio + Indicador de Marcha + Velocímetro"),
    ("delta",     "delta_overlay",     "[DELTA] Session Best Split",   "Barra Dinámica Verde/Roja contra Mejor Vuelta + Sectores S1-S3"),
]

F4_SKINS_LIST = [
    ("VEVI Factory Works #69 (Oficial)", "F4_VEVI_Factory_Works_69"),
    ("Oracle Red Bull Racing RB21 (#1 Verstappen)", "F4_F1_01_RedBull_Oracle_RB21"),
    ("Scuderia Ferrari HP SF-25 (#16 Leclerc)", "F4_F1_02_Ferrari_Scuderia_HP_SF25"),
    ("McLaren Formula 1 Team MCL39 (#4 Norris)", "F4_F1_03_McLaren_Papaya_MCL39"),
    ("Mercedes-AMG Petronas W16 (#63 Russell)", "F4_F1_04_Mercedes_AMG_Petronas_W16"),
    ("Aston Martin Aramco AMR25 (#14 Alonso)", "F4_F1_05_AstonMartin_Aramco_AMR25"),
    ("BWT Alpine F1 Team A525 (#10 Gasly)", "F4_F1_06_Alpine_BWT_A525"),
    ("Atlassian Williams Racing FW47 (#55 Sainz)", "F4_F1_07_Williams_Atlassian_FW47"),
    ("Visa Cash App Racing Bulls VCARB 02 (#22)", "F4_F1_08_RacingBulls_VCARB_02"),
    ("MoneyGram Haas F1 Team VF-25 (#31 Ocon)", "F4_F1_09_Haas_MoneyGram_VF25"),
    ("Stake F1 Team Kick Sauber / Audi C45 (#27)", "F4_F1_10_KickSauber_Stake_Audi_C45"),
]


class LauncherWindow(QMainWindow):
    def __init__(self, autostart_tv2026: bool = False):
        super().__init__()
        self.setWindowTitle("iRacing HUD Overlay Suite v3.5 · Blender 3D Edition — by vevi")
        self.setMinimumSize(860, 680)
        self.resize(980, 900)

        self.processes = {}
        self.status_labels = {}
        self.toggle_btns = {}
        self.lock_btns = {}
        self.scale_labels = {}

        self._cfg = load_config()
        self._pinned = False
        self._init_ui()

        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self._check_processes)
        self.monitor_timer.start(700)

        if autostart_tv2026:
            QTimer.singleShot(300, self.launch_tv2026_preset)

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(18, 14, 18, 12)
        main_layout.setSpacing(9)

        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #0B0E14;
                color: #F1F5F9;
                font-family: 'Segoe UI', sans-serif;
            }
            QFrame#Card {
                background-color: #131824;
                border: 1px solid #263044;
                border-radius: 10px;
            }
            QPushButton {
                background-color: #1E2638;
                color: #FFFFFF;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #2D3850;
                border-color: #00F5D4;
            }
            QPushButton#BtnSmallScale {
                background-color: #161E2E;
                border: 1px solid #38BDF8;
                border-radius: 5px;
                padding: 2px 0px;
                font-size: 12px;
                font-weight: bold;
                color: #FFFFFF;
            }
            QPushButton#BtnSmallScale:hover {
                background-color: #25334D;
                border-color: #00F5D4;
            }
            QPushButton#BtnTV2026 {
                background-color: #E10600;
                border: 1px solid #FF4D4D;
                font-size: 11px;
                padding: 9px 12px;
            }
            QPushButton#BtnTV2026:hover {
                background-color: #FF1E1E;
            }
            QPushButton#BtnProSuite {
                background-color: #6D28D9;
                border: 1px solid #A78BFA;
                font-size: 11px;
                padding: 9px 12px;
            }
            QPushButton#BtnProSuite:hover {
                background-color: #7C3AED;
            }
            QPushButton#BtnLockAll {
                background-color: #0F766E;
                border: 1px solid #00F5D4;
                font-size: 11px;
                padding: 9px 12px;
            }
            QPushButton#BtnSkin {
                background-color: #0D9488;
                border: 1px solid #00F5D4;
                color: #FFFFFF;
            }
            QPushButton#BtnStop {
                background-color: #331820;
                border: 1px solid #EF4444;
                color: #FCA5A5;
            }
            QComboBox {
                background-color: #1E2638;
                border: 1px solid #38BDF8;
                border-radius: 6px;
                padding: 5px 10px;
                color: #FFFFFF;
                font-weight: bold;
            }
            QCheckBox {
                font-weight: bold;
                color: #00F5D4;
                spacing: 8px;
            }
        """)

        # 1. Hero Header Banner (Rendered with Blender 4.2 3D PBR Assets)
        hero = Blender3DHeroFrame()
        hero.setFixedHeight(92)
        h_lay = QVBoxLayout(hero)
        h_lay.setContentsMargins(20, 12, 110, 12)

        title_row = QHBoxLayout()
        title_lbl = QLabel("iRACING SUITE v3.5 | BLENDER 3D EDITION")
        title_lbl.setFont(QFont("Segoe UI", 13, QFont.Black))
        title_lbl.setStyleSheet("color: #FFFFFF; background: transparent;")
        badge_lbl = QLabel("REDIMENSIONABLE Y FIJABLE | BY VEVI")
        badge_lbl.setFont(QFont("Segoe UI", 8, QFont.Black))
        badge_lbl.setStyleSheet("color: #00F5D4; background-color: rgba(10, 14, 24, 225); padding: 4px 8px; border-radius: 5px; border: 1px solid #00F5D4;")
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        title_row.addWidget(badge_lbl)
        h_lay.addLayout(title_row)

        sub_lbl = QLabel(
            "Todas las ventanas son ajustables de tamaño (arrastrando su esquina inferior derecha, con la rueda del ratón o con [-]/[+]) "
            "y fijables individualmente o en bloque para que no se muevan mientras conduces."
        )
        sub_lbl.setWordWrap(True)
        sub_lbl.setStyleSheet("color: #CBD5E1; font-size: 10px; background: transparent;")
        h_lay.addWidget(sub_lbl)
        main_layout.addWidget(hero)

        # 2. Quick Preset Launchers & Global Lock Row
        preset_row = QHBoxLayout()
        btn_tv = QPushButton("LANZAR TV 2026 BROADCAST 3D")
        btn_tv.setObjectName("BtnTV2026")
        btn_tv.clicked.connect(self.launch_tv2026_preset)

        btn_pro = QPushButton("SUITE PRO (RACELAB + TROPHI.AI)")
        btn_pro.setObjectName("BtnProSuite")
        btn_pro.clicked.connect(self.launch_pro_suite_preset)

        self.btn_lock_all = QPushButton("FIJAR TODAS LAS VENTANAS")
        self.btn_lock_all.setObjectName("BtnLockAll")
        self.btn_lock_all.clicked.connect(self.toggle_lock_all_overlays)

        btn_all = QPushButton("TODOS (11)")
        btn_all.clicked.connect(self.start_all)

        btn_stop = QPushButton("DETENER")
        btn_stop.setObjectName("BtnStop")
        btn_stop.clicked.connect(self.stop_all)

        preset_row.addWidget(btn_tv, 2)
        preset_row.addWidget(btn_pro, 2)
        preset_row.addWidget(self.btn_lock_all, 2)
        preset_row.addWidget(btn_all, 1)
        preset_row.addWidget(btn_stop, 1)
        main_layout.addLayout(preset_row)

        # 3. 1-Click F1 / VEVI Skin Installer Card for iRacing (Customer ID 948371)
        skin_card = QFrame()
        skin_card.setObjectName("Card")
        sk_lay = QHBoxLayout(skin_card)
        sk_lay.setContentsMargins(14, 7, 14, 7)
        sk_lbl = QLabel("Skin Activa F4 (ID 948371):")
        sk_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.skin_combo = QComboBox()
        for label, s_key in F4_SKINS_LIST:
            self.skin_combo.addItem(label, s_key)
        btn_apply_skin = QPushButton("Activar Skin en iRacing")
        btn_apply_skin.setObjectName("BtnSkin")
        btn_apply_skin.clicked.connect(self.apply_selected_f4_skin)
        self.skin_status = QLabel("13 Skins Pro Instaladas")
        self.skin_status.setStyleSheet("color: #10B981; font-weight: bold; font-size: 10px;")

        sk_lay.addWidget(sk_lbl)
        sk_lay.addWidget(self.skin_combo, 1)
        sk_lay.addWidget(btn_apply_skin)
        sk_lay.addWidget(self.skin_status)
        main_layout.addWidget(skin_card)

        # 4. Global Settings Bar (Theme, Pin Control Center, Sim Mode, Opacity, Scale)
        settings_card = QFrame()
        settings_card.setObjectName("Card")
        s_lay = QGridLayout(settings_card)
        s_lay.setContentsMargins(14, 8, 14, 8)
        s_lay.setHorizontalSpacing(16)
        s_lay.setVerticalSpacing(6)

        s_lay.addWidget(QLabel("Tema Visual:"), 0, 0)
        self.theme_combo = QComboBox()
        for t_key, t_val in THEMES.items():
            self.theme_combo.addItem(t_val["name"], t_key)
        cur_theme = self._cfg.get("theme", "f1_2026_tv")
        idx = self.theme_combo.findData(cur_theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        self.theme_combo.currentIndexChanged.connect(self._on_settings_changed)
        s_lay.addWidget(self.theme_combo, 0, 1)

        self.sim_chk = QCheckBox("Modo Demo 60Hz (Sin iRacing)")
        self.sim_chk.setChecked(bool(self._cfg.get("sim_mode", False)))
        self.sim_chk.stateChanged.connect(self._on_settings_changed)
        s_lay.addWidget(self.sim_chk, 0, 2)

        self.pin_launcher_chk = QCheckBox("Fijar Este Panel Siempre Visible")
        self.pin_launcher_chk.setChecked(False)
        self.pin_launcher_chk.stateChanged.connect(self._toggle_pin_launcher)
        s_lay.addWidget(self.pin_launcher_chk, 0, 3)

        self.op_lbl = QLabel(f"Opacidad: {int(self._cfg.get('opacity', 0.96)*100)}%")
        s_lay.addWidget(self.op_lbl, 1, 0)
        self.op_slider = QSlider(Qt.Horizontal)
        self.op_slider.setRange(40, 100)
        self.op_slider.setValue(int(self._cfg.get("opacity", 0.96) * 100))
        self.op_slider.valueChanged.connect(self._on_settings_changed)
        s_lay.addWidget(self.op_slider, 1, 1)

        self.sc_lbl = QLabel(f"Escala Global: {int(self._cfg.get('scale', 1.0)*100)}%")
        s_lay.addWidget(self.sc_lbl, 1, 2)
        self.sc_slider = QSlider(Qt.Horizontal)
        self.sc_slider.setRange(55, 200)
        self.sc_slider.setValue(int(self._cfg.get("scale", 1.0) * 100))
        self.sc_slider.valueChanged.connect(self._on_global_scale_changed)
        s_lay.addWidget(self.sc_slider, 1, 3)

        main_layout.addWidget(settings_card)

        # 5. Scrollable Grid of 11 Overlays with Individual Size [-][+] & Lock [Fijar] Controls
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        grid_container = QWidget()
        grid = QGridLayout(grid_container)
        grid.setContentsMargins(2, 2, 2, 2)
        grid.setSpacing(8)

        for idx, (short_key, cfg_key, title, desc) in enumerate(OVERLAYS_META):
            card = Blender3DCardFrame()
            c_lay = QHBoxLayout(card)
            c_lay.setContentsMargins(12, 8, 12, 8)
            c_lay.setSpacing(5)

            info_lay = QVBoxLayout()
            t_lbl = QLabel(title)
            t_lbl.setFont(QFont("Segoe UI", 9, QFont.Black))
            t_lbl.setStyleSheet("color: #FFFFFF; background: transparent;")
            d_lbl = QLabel(desc)
            d_lbl.setStyleSheet("color: #CBD5E1; font-size: 9px; background: transparent;")
            d_lbl.setWordWrap(True)
            info_lay.addWidget(t_lbl)
            info_lay.addWidget(d_lbl)

            # Individual scale [-] [100%] [+] controls
            ov_cfg = self._cfg.get("overlays", {}).get(cfg_key, {})
            cur_ov_scale = float(ov_cfg.get("scale", self._cfg.get("scale", 1.0)))
            btn_minus = QPushButton("-")
            btn_minus.setObjectName("BtnSmallScale")
            btn_minus.setFixedSize(24, 26)
            btn_minus.setToolTip("Reducir tamaño de esta ventana (-10%)")
            btn_minus.clicked.connect(lambda checked, ck=cfg_key: self.adjust_single_overlay_scale(ck, -0.10))

            sc_val_lbl = QLabel(f"{int(round(cur_ov_scale * 100))}%")
            sc_val_lbl.setFont(QFont("Consolas", 8, QFont.Bold))
            sc_val_lbl.setAlignment(Qt.AlignCenter)
            sc_val_lbl.setFixedWidth(36)
            sc_val_lbl.setStyleSheet("color: #00F5D4; background: transparent;")
            self.scale_labels[cfg_key] = sc_val_lbl

            btn_plus = QPushButton("+")
            btn_plus.setObjectName("BtnSmallScale")
            btn_plus.setFixedSize(24, 26)
            btn_plus.setToolTip("Aumentar tamaño de esta ventana (+10%)")
            btn_plus.clicked.connect(lambda checked, ck=cfg_key: self.adjust_single_overlay_scale(ck, +0.10))

            # Individual Lock / Pin Button
            btn_lock = QPushButton("Fijar")
            btn_lock.setFixedWidth(52)
            btn_lock.setToolTip("Fijar o desbloquear la posición y tamaño de esta ventana")
            btn_lock.clicked.connect(lambda checked, ck=cfg_key: self.toggle_single_overlay_lock(ck))
            self.lock_btns[cfg_key] = btn_lock

            st_lbl = QLabel("OFF")
            st_lbl.setFont(QFont("Consolas", 8, QFont.Bold))
            st_lbl.setFixedWidth(30)
            st_lbl.setAlignment(Qt.AlignCenter)
            st_lbl.setStyleSheet("color: #64748B; background: transparent;")
            self.status_labels[short_key] = st_lbl

            btn = QPushButton("Iniciar")
            btn.setFixedWidth(62)
            btn.clicked.connect(lambda checked, k=short_key: self.toggle_overlay(k))
            self.toggle_btns[short_key] = btn

            c_lay.addLayout(info_lay, 1)
            c_lay.addWidget(btn_minus)
            c_lay.addWidget(sc_val_lbl)
            c_lay.addWidget(btn_plus)
            c_lay.addWidget(btn_lock)
            c_lay.addWidget(st_lbl)
            c_lay.addWidget(btn)

            row = idx // 2
            col = idx % 2
            grid.addWidget(card, row, col)

        scroll.setWidget(grid_container)
        main_layout.addWidget(scroll, 1)

        # Bottom Footer with Resize Grip
        foot_row = QHBoxLayout()
        foot = QLabel(
            "Arrastra la esquina inferior derecha de cualquier overlay (o usa la rueda del raton / botones - +) para redimensionarlo, "
            "y pulsa 'FIJAR' para bloquearlo | Creado por vevi (VEVIkils556@gmail.com)"
        )
        foot.setAlignment(Qt.AlignCenter)
        foot.setStyleSheet("color: #94A3B8; font-size: 9px;")
        foot_row.addWidget(foot, 1)
        grip = QSizeGrip(self)
        foot_row.addWidget(grip, 0, Qt.AlignBottom | Qt.AlignRight)
        main_layout.addLayout(foot_row)

        self._refresh_lock_and_scale_ui()

    def _toggle_pin_launcher(self):
        self._pinned = self.pin_launcher_chk.isChecked()
        flags = self.windowFlags()
        if self._pinned:
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
        self.show()

    def adjust_single_overlay_scale(self, cfg_key: str, delta: float):
        self._cfg = load_config()
        ov = self._cfg.setdefault("overlays", {}).setdefault(cfg_key, {})
        cur = float(ov.get("scale", self._cfg.get("scale", 1.0)))
        new_sc = round(max(0.50, min(2.50, cur + delta)), 2)
        ov["scale"] = new_sc
        ov["scale_x"] = new_sc
        ov["scale_y"] = new_sc
        save_config(self._cfg)
        self._refresh_lock_and_scale_ui()

    def toggle_single_overlay_lock(self, cfg_key: str):
        self._cfg = load_config()
        ov = self._cfg.setdefault("overlays", {}).setdefault(cfg_key, {})
        cur_locked = bool(ov.get("locked", False) or self._cfg.get("locked_all", False))
        new_locked = not cur_locked
        if not new_locked:
            self._cfg["locked_all"] = False
        ov["locked"] = new_locked
        save_config(self._cfg)
        self._refresh_lock_and_scale_ui()

    def toggle_lock_all_overlays(self):
        self._cfg = load_config()
        cur_all = bool(self._cfg.get("locked_all", False))
        new_all = not cur_all
        self._cfg["locked_all"] = new_all
        for _, cfg_key, _, _ in OVERLAYS_META:
            self._cfg.setdefault("overlays", {}).setdefault(cfg_key, {})["locked"] = new_all
        save_config(self._cfg)
        self._refresh_lock_and_scale_ui()

    def _refresh_lock_and_scale_ui(self):
        self._cfg = load_config()
        locked_all = bool(self._cfg.get("locked_all", False))
        if locked_all:
            self.btn_lock_all.setText("DESBLOQUEAR TODAS LAS VENTANAS")
            self.btn_lock_all.setStyleSheet("background-color: #B91C1C; border: 1px solid #FCA5A5;")
        else:
            self.btn_lock_all.setText("FIJAR TODAS LAS VENTANAS")
            self.btn_lock_all.setStyleSheet("background-color: #0F766E; border: 1px solid #00F5D4;")

        for _, cfg_key, _, _ in OVERLAYS_META:
            ov = self._cfg.get("overlays", {}).get(cfg_key, {})
            is_lk = bool(ov.get("locked", False) or locked_all)
            sc = float(ov.get("scale", self._cfg.get("scale", 1.0)))
            if cfg_key in self.scale_labels:
                self.scale_labels[cfg_key].setText(f"{int(round(sc * 100))}%")
            if cfg_key in self.lock_btns:
                btn = self.lock_btns[cfg_key]
                if is_lk:
                    btn.setText("Fijado")
                    btn.setStyleSheet("background-color: #991B1B; border: 1px solid #F87171; color: #FFFFFF;")
                else:
                    btn.setText("Fijar")
                    btn.setStyleSheet("background-color: #1E2638; border: 1px solid #334155; color: #00F5D4;")

    def apply_selected_f4_skin(self):
        skin_key = self.skin_combo.currentData()
        installer = r"C:\Users\alfaswz\Desktop\paints iracings\install_all_skins_to_iracing.py"
        if os.path.exists(installer):
            subprocess.Popen([sys.executable, installer, skin_key])
            self.skin_status.setText(f"OK: {skin_key[:18]} Activa")
            self.skin_status.setStyleSheet("color: #00F5D4; font-weight: bold; font-size: 10px;")

    def _on_settings_changed(self):
        self._cfg = load_config()
        self._cfg["theme"] = self.theme_combo.currentData()
        self._cfg["sim_mode"] = self.sim_chk.isChecked()
        self._cfg["opacity"] = round(self.op_slider.value() / 100.0, 2)
        self.op_lbl.setText(f"Opacidad: {self.op_slider.value()}%")
        save_config(self._cfg)

    def _on_global_scale_changed(self):
        self._cfg = load_config()
        new_sc = round(self.sc_slider.value() / 100.0, 2)
        self._cfg["scale"] = new_sc
        for _, cfg_key, _, _ in OVERLAYS_META:
            ov = self._cfg.setdefault("overlays", {}).setdefault(cfg_key, {})
            ov["scale"] = new_sc
            ov["scale_x"] = new_sc
            ov["scale_y"] = new_sc
        self.sc_lbl.setText(f"Escala Global: {self.sc_slider.value()}%")
        save_config(self._cfg)
        self._refresh_lock_and_scale_ui()

    def toggle_overlay(self, key: str):
        proc = self.processes.get(key)
        if proc and proc.poll() is None:
            proc.terminate()
            self.processes.pop(key, None)
        else:
            main_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
            p = subprocess.Popen([sys.executable, main_script, "--overlay", key])
            self.processes[key] = p
        self._check_processes()

    def launch_tv2026_preset(self):
        self.stop_all()
        self._cfg = load_config()
        self._cfg["theme"] = "f1_2026_tv"
        save_config(self._cfg)
        for k in ("tv2026", "trophi", "trackmap", "tires", "radar"):
            self.toggle_overlay(k)

    def launch_pro_suite_preset(self):
        self.stop_all()
        for k in ("trophi", "trackmap", "tires", "standings", "relative", "radar", "inputs", "fuel", "delta", "gear"):
            self.toggle_overlay(k)

    def start_all(self):
        for short_key, _, _, _ in OVERLAYS_META:
            proc = self.processes.get(short_key)
            if not proc or proc.poll() is not None:
                self.toggle_overlay(short_key)

    def stop_all(self):
        for k, proc in list(self.processes.items()):
            if proc and proc.poll() is None:
                proc.terminate()
        self.processes.clear()
        self._check_processes()

    def _check_processes(self):
        self._refresh_lock_and_scale_ui()
        for short_key, _, _, _ in OVERLAYS_META:
            proc = self.processes.get(short_key)
            running = proc is not None and proc.poll() is None
            lbl = self.status_labels.get(short_key)
            btn = self.toggle_btns.get(short_key)
            if lbl and btn:
                if running:
                    lbl.setText("LIVE")
                    lbl.setStyleSheet("color: #00F5D4; background: transparent;")
                    btn.setText("Detener")
                else:
                    lbl.setText("OFF")
                    lbl.setStyleSheet("color: #64748B; background: transparent;")
                    btn.setText("Iniciar")

    def closeEvent(self, event):
        self.stop_all()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    autostart = "--autostart" in sys.argv
    win = LauncherWindow(autostart_tv2026=autostart)
    win.show()
    sys.exit(app.exec_())
