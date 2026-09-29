"""
launcher_gui.py  -  iRacing HUD Overlay Suite v2.0
Panel de control principal con UI premium glassmorphism.

Autor: vevi (VEVIkils556@gmail.com)
Version: 2.0.0
"""
import sys, os, subprocess, time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QFrame, QStackedWidget, QSlider, QCheckBox,
    QGraphicsDropShadowEffect, QGridLayout, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QColor, QFont, QIcon, QPainter, QBrush, QLinearGradient, QPen, QPixmap
import overlay_utils


# ─────────────────────────────────────────────────────────────────
#  MONITOR THREAD
# ─────────────────────────────────────────────────────────────────
class IRacingMonitorThread(QThread):
    status_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.running = True
        self.last_status = None

    def run(self):
        ir = None
        try:
            import irsdk
            ir = irsdk.IRSDK()
        except Exception:
            pass
        while self.running:
            cfg = overlay_utils.load_config()
            if cfg.get("sim_mode", False):
                connected = True
            elif ir:
                connected = ir.startup() and ir.is_connected
            else:
                connected = False
            if connected != self.last_status:
                self.status_changed.emit(connected)
                self.last_status = connected
            time.sleep(1.5)

    def stop(self):
        self.running = False
        self.wait()


# ─────────────────────────────────────────────────────────────────
#  HELPERS DE ESTILO
# ─────────────────────────────────────────────────────────────────
def _sidebar_btn_style(accent: str, active: bool) -> str:
    if active:
        return f"""
            QPushButton {{
                background: {accent};
                color: #ffffff;
                font-size: 11px; font-weight: 900;
                letter-spacing: 1px;
                border: none; border-radius: 8px;
                padding: 0 10px;
                text-align: left;
            }}
        """
    return """
        QPushButton {
            background: rgba(255,255,255,0.04);
            color: #8e8e93;
            font-size: 11px; font-weight: 700;
            letter-spacing: 1px;
            border: none; border-radius: 8px;
            padding: 0 10px;
            text-align: left;
        }
        QPushButton:hover {
            background: rgba(255,255,255,0.10);
            color: #ffffff;
        }
    """


def _action_btn_style(accent: str) -> str:
    return f"""
        QPushButton {{
            background: {accent};
            color: #ffffff;
            font-size: 9px; font-weight: 900;
            letter-spacing: 0.5px;
            border: none; border-radius: 5px;
        }}
        QPushButton:hover {{ opacity: 0.85; }}
        QPushButton:pressed {{ padding-top: 1px; }}
    """


def _stop_btn_style() -> str:
    return """
        QPushButton {
            background: rgba(239,35,60,0.25);
            color: #ef233c;
            font-size: 9px; font-weight: 900;
            border: 1px solid rgba(239,35,60,0.4);
            border-radius: 5px;
        }
        QPushButton:hover { background: rgba(239,35,60,0.45); }
    """


# ─────────────────────────────────────────────────────────────────
#  LAUNCHER WINDOW
# ─────────────────────────────────────────────────────────────────
class LauncherWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.script_dir = overlay_utils.get_base_path()
        self.processes: dict[str, subprocess.Popen] = {}
        self.current_theme = ""
        self.current_page  = 0
        self.drag_pos      = None
        self._overlay_btns: dict[str, QPushButton] = {}

        self._init_ui()

        self.monitor = IRacingMonitorThread()
        self.monitor.status_changed.connect(self._on_connection)
        self.monitor.start()

        self.proc_timer = QTimer(self)
        self.proc_timer.timeout.connect(self._check_processes)
        self.proc_timer.start(1000)

        self._apply_theme()

    # ── Build UI ────────────────────────────────────────────────
    def _init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(780, 550)

        icon_path = os.path.join(self.script_dir, "iRacingOverlay.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)

        self.root_frame = QFrame()
        self.root_frame.setObjectName("rootFrame")
        root_lay.addWidget(self.root_frame)

        rf_lay = QVBoxLayout(self.root_frame)
        rf_lay.setContentsMargins(0, 0, 0, 0)
        rf_lay.setSpacing(0)

        # ── Title Bar ──────────────────────────────────────────
        tbar = QFrame()
        tbar.setObjectName("titleBar")
        tbar.setFixedHeight(44)
        tb_lay = QHBoxLayout(tbar)
        tb_lay.setContentsMargins(18, 0, 14, 0)

        dot_r = QFrame(); dot_r.setFixedSize(9, 9)
        dot_r.setStyleSheet("border-radius:4px; background:rgba(255,59,48,0.8);")
        dot_y = QFrame(); dot_y.setFixedSize(9, 9)
        dot_y.setStyleSheet("border-radius:4px; background:rgba(252,191,73,0.8);")
        dot_g = QFrame(); dot_g.setFixedSize(9, 9)
        dot_g.setStyleSheet("border-radius:4px; background:rgba(52,199,89,0.8);")

        self.lbl_title = QLabel("iRACING HUD OVERLAY  ·  v2.0  ·  by vevi")
        self.lbl_title.setStyleSheet(
            "font-size:10px; font-weight:900; letter-spacing:2px; color:#8e8e93; font-family:'Segoe UI';"
        )

        btn_min = QPushButton("—")
        btn_min.setFixedSize(22, 22)
        btn_min.setStyleSheet("""
            QPushButton { background:rgba(255,255,255,0.06); border:none; border-radius:11px;
                          color:#8e8e93; font-size:11px; font-weight:bold; }
            QPushButton:hover { background:rgba(252,191,73,0.3); color:#fcbf49; }
        """)
        btn_min.clicked.connect(self.showMinimized)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(22, 22)
        btn_close.setStyleSheet("""
            QPushButton { background:rgba(255,255,255,0.06); border:none; border-radius:11px;
                          color:#8e8e93; font-size:10px; font-weight:bold; }
            QPushButton:hover { background:rgba(239,35,60,0.35); color:#ef233c; }
        """)
        btn_close.clicked.connect(self.close)

        for w in [dot_r, dot_y, dot_g]:
            tb_lay.addWidget(w, 0, Qt.AlignVCenter)
            tb_lay.addSpacing(5)
        tb_lay.addSpacing(10)
        tb_lay.addWidget(self.lbl_title, 0, Qt.AlignVCenter)
        tb_lay.addStretch()
        tb_lay.addWidget(btn_min)
        tb_lay.addSpacing(6)
        tb_lay.addWidget(btn_close)
        rf_lay.addWidget(tbar)

        # ── Content ────────────────────────────────────────────
        content = QFrame()
        c_lay   = QHBoxLayout(content)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(0)

        # Sidebar
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(170)
        sb_lay = QVBoxLayout(self.sidebar)
        sb_lay.setContentsMargins(12, 18, 12, 18)
        sb_lay.setSpacing(6)

        logo = QLabel("OVERLAY")
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("font-size:22px; font-weight:900; letter-spacing:4px; color:#ffffff; font-family:'Segoe UI';")
        sub  = QLabel("HUD SUITE  v2.0")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("font-size:8px; font-weight:900; letter-spacing:2px; color:#9d4edd; margin-top:-8px; margin-bottom:14px; font-family:'Segoe UI';")
        sb_lay.addWidget(logo)
        sb_lay.addWidget(sub)

        # Nav buttons
        NAV = [("  ◈  DASHBOARD", 0), ("  ◉  OVERLAYS", 1), ("  ◐  THEMES", 2), ("  ◌  SETTINGS", 3), ("  ?  ABOUT", 4)]
        self.nav_btns: list[QPushButton] = []
        for txt, idx in NAV:
            b = QPushButton(txt)
            b.setFixedHeight(36)
            b.clicked.connect(lambda _, i=idx: self._switch_page(i))
            self.nav_btns.append(b)
            sb_lay.addWidget(b)

        sb_lay.addStretch()

        # iRSDK status
        status_box = QFrame()
        status_box.setStyleSheet(
            "background:rgba(0,0,0,0.18); border-radius:8px; border:1px solid rgba(255,255,255,0.04);"
        )
        st_lay = QVBoxLayout(status_box)
        st_lay.setContentsMargins(10, 10, 10, 10)
        QLabel("iRSDK STATUS").setParent(status_box)
        hdr_st = QLabel("iRSDK STATUS")
        hdr_st.setStyleSheet("font-size:8px; font-weight:900; letter-spacing:1px; color:#8e8e93; font-family:'Segoe UI';")
        si_row = QHBoxLayout()
        si_row.setSpacing(6)
        self.status_dot = QFrame(); self.status_dot.setFixedSize(7,7)
        self.status_dot.setStyleSheet("border-radius:3px; background:#ff3b30;")
        self.status_lbl = QLabel("SEARCHING...")
        self.status_lbl.setStyleSheet("font-size:9px; font-weight:900; color:#8e8e93; font-family:'Segoe UI';")
        si_row.addWidget(self.status_dot, 0, Qt.AlignVCenter)
        si_row.addWidget(self.status_lbl, 0, Qt.AlignVCenter)
        si_row.addStretch()
        st_lay.addWidget(hdr_st)
        st_lay.addLayout(si_row)
        sb_lay.addWidget(status_box)

        c_lay.addWidget(self.sidebar)

        # Pages
        self.pages = QStackedWidget()
        c_lay.addWidget(self.pages)
        rf_lay.addWidget(content)

        # Build all pages
        self._build_page_dashboard()
        self._build_page_overlays()
        self._build_page_themes()
        self._build_page_settings()
        self._build_page_about()

        self._switch_page(0)

    # ── Pages ───────────────────────────────────────────────────
    def _page_base(self, title: str) -> tuple:
        pg  = QFrame()
        lay = QVBoxLayout(pg)
        lay.setContentsMargins(28, 22, 28, 22)
        lay.setSpacing(14)
        lbl = QLabel(title)
        lbl.setStyleSheet("font-size:22px; font-weight:900; letter-spacing:2px; color:#ffffff; font-family:'Segoe UI';")
        lay.addWidget(lbl)
        return pg, lay

    # Page 0 - Dashboard
    def _build_page_dashboard(self):
        pg, lay = self._page_base("DASHBOARD")

        # Big launch button
        self.btn_launch = QPushButton("▶  LAUNCH ALL OVERLAYS")
        self.btn_launch.setFixedHeight(72)
        self.btn_launch.setStyleSheet("""
            QPushButton {
                font-size:15px; font-weight:900; letter-spacing:2px;
                border-radius:10px; border:none; color:#ffffff;
            }
        """)
        self.btn_launch.clicked.connect(self._toggle_all)
        glow = QGraphicsDropShadowEffect(self.btn_launch)
        glow.setBlurRadius(22); glow.setOffset(0,0)
        self.launch_glow = glow
        self.btn_launch.setGraphicsEffect(glow)
        lay.addWidget(self.btn_launch)

        # Info cards
        grid = QGridLayout(); grid.setSpacing(12)

        def card(label_top, attr_name):
            f = QFrame(); f.setObjectName("infoCard")
            fl = QVBoxLayout(f); fl.setContentsMargins(14,12,14,12); fl.setSpacing(4)
            lt = QLabel(label_top)
            lt.setStyleSheet("font-size:8px; font-weight:900; letter-spacing:1.5px; color:#8e8e93; font-family:'Segoe UI';")
            lv = QLabel("—")
            lv.setStyleSheet("font-size:15px; font-weight:900; color:#ffffff; font-family:'Segoe UI';")
            fl.addWidget(lt); fl.addWidget(lv)
            setattr(self, attr_name, lv)
            return f

        grid.addWidget(card("ACTIVE THEME",       "lbl_d_theme"),   0, 0)
        grid.addWidget(card("CLICK-THROUGH",       "lbl_d_lock"),    0, 1)
        grid.addWidget(card("TELEMETRY MODE",      "lbl_d_sim"),     1, 0)
        grid.addWidget(card("RUNNING OVERLAYS",    "lbl_d_count"),   1, 1)
        lay.addLayout(grid)
        lay.addStretch()
        self.pages.addWidget(pg)

    # Page 1 - Overlays
    def _build_page_overlays(self):
        pg, lay = self._page_base("OVERLAYS MANAGER")
        sub = QLabel("Toggle each overlay independently. Use CENTER to reset position if off-screen.")
        sub.setStyleSheet("font-size:9px; color:#8e8e93; margin-top:-10px; font-family:'Segoe UI';")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;} QScrollBar{width:4px;}")
        inner = QWidget(); inner.setStyleSheet("background:transparent;")
        il = QVBoxLayout(inner); il.setSpacing(8); il.setContentsMargins(0,0,4,0)

        OVERLAYS = [
            ("gear",     "⚙  GEAR & SHIFT LIGHTS",      "overlay1.py",          "Marcha gigante, velocimetro y barra de shift lights F1."),
            ("inputs",   "🚦  PEDAL INPUT TELEMETRY",    "inputs_overlay.py",    "Acelerador, freno, embrague y trazado grafico historico."),
            ("delta",    "⏱  LAP TIME DELTA",            "delta_overlay.py",     "Barra bidireccional de diferencia de tiempo respecto a la mejor vuelta."),
            ("relative", "📊  RELATIVE LEADERBOARD",     "relative_overlay.py",  "Pilotos cercanos con gaps, iRating, licencia y Safety Rating."),
            ("radar",    "🛰  PROXIMITY RADAR",           "radar_overlay.py",     "Spotter de puntos ciegos - alerta car left / car right / 3-wide."),
            ("fuel",     "⛽  FUEL & STINT CALCULATOR",  "fuel_overlay.py",      "Combustible restante, consumo por vuelta y temperaturas de fluidos."),
        ]

        for key, name, script, desc in OVERLAYS:
            card = QFrame(); card.setObjectName("overlayCard")
            card.setStyleSheet("background:rgba(255,255,255,0.03); border-radius:10px; border:1px solid rgba(255,255,255,0.06);")
            cl = QHBoxLayout(card); cl.setContentsMargins(14,12,14,12)

            info = QVBoxLayout(); info.setSpacing(3)
            ln = QLabel(name); ln.setStyleSheet("font-weight:bold; font-size:11px; color:#ffffff; font-family:'Segoe UI';")
            ld = QLabel(desc); ld.setStyleSheet("font-size:9px; color:#8e8e93; font-family:'Segoe UI';")
            ld.setWordWrap(True)
            info.addWidget(ln); info.addWidget(ld)
            cl.addLayout(info, 7)

            acts = QHBoxLayout(); acts.setSpacing(6)
            btn_t = QPushButton("START"); btn_t.setFixedSize(68, 28)
            btn_r = QPushButton("CENTER"); btn_r.setFixedSize(68, 28)
            btn_r.setStyleSheet("font-size:9px; font-weight:bold; background:rgba(255,255,255,0.06); color:#8e8e93; border-radius:5px; border:none;")

            btn_t.clicked.connect(lambda _, k=key, s=script: self._toggle_overlay(k, s))
            btn_r.clicked.connect(lambda _, k=key: self._center_overlay(k))

            acts.addWidget(btn_t); acts.addWidget(btn_r)
            cl.addLayout(acts, 3)
            il.addWidget(card)
            self._overlay_btns[key] = btn_t

        il.addStretch()
        scroll.setWidget(inner)
        lay.addWidget(scroll)
        self.pages.addWidget(pg)

    # Page 2 - Themes
    def _build_page_themes(self):
        pg, lay = self._page_base("VISUAL THEMES")
        sub = QLabel("Selecciona el tema de color que se aplicara a todos los overlays en tiempo real.")
        sub.setStyleSheet("font-size:9px; color:#8e8e93; margin-top:-10px; font-family:'Segoe UI';")
        lay.addWidget(sub)

        grid = QGridLayout(); grid.setSpacing(10)
        themes = overlay_utils.get_all_themes()

        self.theme_btns: dict[str, QPushButton] = {}
        ACCENT_MAP = {
            "classic_red": "#ff3b30", "cyberpunk": "#ff007f", "electric_blue": "#007aff",
            "toxic_green": "#39ff14", "racelab_pro": "#9d4edd", "dark_carbon": "#e0e1dd",
            "alpine_luxury": "#0090ff",
        }
        for i, (key, name) in enumerate(themes):
            ac = ACCENT_MAP.get(key, "#9d4edd")
            btn = QPushButton(f"  {name}")
            btn.setFixedHeight(44)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(255,255,255,0.04);
                    border: 2px solid {ac};
                    border-radius: 8px;
                    color: #ffffff;
                    font-size: 11px; font-weight: 700;
                    text-align: left; padding-left: 6px;
                    font-family: 'Segoe UI';
                }}
                QPushButton:hover {{ background: rgba(255,255,255,0.10); }}
                QPushButton:checked {{ background: {ac}33; }}
            """)
            btn.clicked.connect(lambda _, k=key: self._apply_theme_key(k))
            self.theme_btns[key] = btn
            grid.addWidget(btn, i // 2, i % 2)

        lay.addLayout(grid)
        lay.addStretch()
        self.pages.addWidget(pg)

    # Page 3 - Settings
    def _build_page_settings(self):
        pg, lay = self._page_base("SETTINGS")

        # Opacity
        def section(txt):
            l = QLabel(txt)
            l.setStyleSheet("font-size:9px; font-weight:900; letter-spacing:1px; color:#8e8e93; font-family:'Segoe UI';")
            return l

        lay.addWidget(section("OPACITY"))
        slid = QSlider(Qt.Horizontal); slid.setRange(30, 100); slid.setValue(93)
        slid.setStyleSheet("QSlider::handle:horizontal{background:#9d4edd;width:14px;height:14px;border-radius:7px;margin:-5px 0;} QSlider::groove:horizontal{height:4px;background:rgba(255,255,255,0.10);border-radius:2px;} QSlider::sub-page:horizontal{background:#9d4edd;border-radius:2px;}")
        self.lbl_opacity = QLabel("93%")
        self.lbl_opacity.setStyleSheet("font-size:11px; font-weight:bold; color:#ffffff; font-family:'Segoe UI';")
        op_row = QHBoxLayout(); op_row.addWidget(slid, 1); op_row.addWidget(self.lbl_opacity)
        lay.addLayout(op_row)

        def _on_opacity(v):
            self.lbl_opacity.setText(f"{v}%")
            cfg = overlay_utils.load_config()
            cfg["opacity"] = v / 100
            overlay_utils.save_config(cfg)
        slid.valueChanged.connect(_on_opacity)
        self.slid_opacity = slid

        lay.addSpacing(10)
        lay.addWidget(section("MOUSE CLICK-THROUGH (lock all overlays)"))
        chk_lock = QCheckBox("Enable click-through on all overlays")
        chk_lock.setStyleSheet("color:#ffffff; font-size:11px; font-family:'Segoe UI';")
        def _on_lock(s):
            cfg = overlay_utils.load_config()
            cfg["locked"] = bool(s)
            overlay_utils.save_config(cfg)
        chk_lock.stateChanged.connect(_on_lock)
        lay.addWidget(chk_lock)
        self.chk_lock = chk_lock

        lay.addSpacing(10)
        lay.addWidget(section("TELEMETRY SOURCE"))
        chk_sim = QCheckBox("Demo / Simulation mode (no iRacing needed)")
        chk_sim.setStyleSheet("color:#ffffff; font-size:11px; font-family:'Segoe UI';")
        def _on_sim(s):
            cfg = overlay_utils.load_config()
            cfg["sim_mode"] = bool(s)
            overlay_utils.save_config(cfg)
            self.lbl_d_sim.setText("Simulation" if s else "Real iRacing")
        chk_sim.stateChanged.connect(_on_sim)
        lay.addWidget(chk_sim)
        self.chk_sim = chk_sim

        # Load current values
        cfg = overlay_utils.load_config()
        slid.setValue(int(cfg.get("opacity", 0.93) * 100))
        chk_lock.setChecked(cfg.get("locked", False))
        chk_sim.setChecked(cfg.get("sim_mode", False))

        lay.addStretch()
        self.pages.addWidget(pg)

    # Page 4 - About
    def _build_page_about(self):
        pg, lay = self._page_base("ABOUT")

        lines = [
            ("iRacing HUD Overlay Suite", "font-size:22px; font-weight:900; color:#ffffff; font-family:'Segoe UI';"),
            ("Version 2.0.0", "font-size:13px; font-weight:700; color:#9d4edd; font-family:'Segoe UI';"),
            ("", ""),
            ("Autor: vevi", "font-size:11px; color:#8e8e93; font-family:'Segoe UI';"),
            ("Email: VEVIkils556@gmail.com", "font-size:11px; color:#8e8e93; font-family:'Segoe UI';"),
            ("", ""),
            ("Suite de overlays de telemetria en tiempo real para iRacing.", "font-size:10px; color:#8e8e93; font-family:'Segoe UI';"),
            ("Desarrollada en Python + PyQt5 con arquitectura modular.", "font-size:10px; color:#8e8e93; font-family:'Segoe UI';"),
            ("", ""),
            ("Modulos incluidos:", "font-size:10px; font-weight:700; color:#c77dff; font-family:'Segoe UI';"),
            ("  Gear & Speed  •  Inputs  •  Delta  •  Relative  •  Radar  •  Fuel", "font-size:10px; color:#ffffff; font-family:'Segoe UI';"),
        ]
        for txt, style in lines:
            if not txt and not style:
                lay.addSpacing(8)
                continue
            l = QLabel(txt); l.setStyleSheet(style); l.setWordWrap(True)
            lay.addWidget(l)

        lay.addStretch()
        self.pages.addWidget(pg)

    # ── Navigation ──────────────────────────────────────────────
    def _switch_page(self, idx: int):
        self.current_page = idx
        self.pages.setCurrentIndex(idx)
        self._apply_theme()

    # ── Theme ───────────────────────────────────────────────────
    def _apply_theme_key(self, key: str):
        cfg = overlay_utils.load_config()
        cfg["theme"] = key
        overlay_utils.save_config(cfg)
        self.current_theme = key
        self._apply_theme()

    def _apply_theme(self):
        cfg = overlay_utils.load_config()
        theme = cfg.get("theme", "racelab_pro")
        if theme != self.current_theme:
            self.current_theme = theme
        c = overlay_utils.get_theme_colors(theme)
        acc = c["accent"]
        ar  = c["accent_rgb"]

        self.root_frame.setStyleSheet(f"""
            #rootFrame {{
                {c['bg_gradient'].replace('qlineargradient', 'background: qlineargradient')}
                border: 1.5px solid {c['border']};
                border-radius: 14px;
            }}
            #titleBar {{ background: rgba(0,0,0,0.25); border-top-left-radius:14px; border-top-right-radius:14px; }}
            #sidebar  {{ background: rgba(0,0,0,0.18); }}
            #infoCard {{
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.07);
                border-radius: 10px;
            }}
        """)

        # Nav buttons
        for i, b in enumerate(self.nav_btns):
            b.setStyleSheet(_sidebar_btn_style(acc, i == self.current_page))
            b.setFixedHeight(36)

        # Launch button
        self.btn_launch.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {acc}, stop:1 {c['accent_secondary']});
                font-size:15px; font-weight:900; letter-spacing:2px;
                border-radius:10px; border:none; color:#ffffff;
            }}
            QPushButton:hover {{ opacity:0.88; }}
        """)
        self.launch_glow.setColor(QColor(ar[0], ar[1], ar[2], 120))

        # Update overlay action buttons with current accent
        for key, btn in self._overlay_btns.items():
            running = key in self.processes and self.processes[key].poll() is None
            if running:
                btn.setText("STOP")
                btn.setStyleSheet(_stop_btn_style())
            else:
                btn.setText("START")
                btn.setStyleSheet(_action_btn_style(acc))

        # Theme selector highlight
        for k, b in getattr(self, "theme_btns", {}).items():
            if k == theme:
                b.setStyleSheet(b.styleSheet().replace("rgba(255,255,255,0.04)", f"rgba({ar[0]},{ar[1]},{ar[2]},0.20)"))

        # Dashboard cards
        c_map = {
            "lbl_d_theme": overlay_utils.get_theme_colors(theme)["name"],
            "lbl_d_lock":  "Locked" if cfg.get("locked") else "Unlocked",
            "lbl_d_sim":   "Simulation" if cfg.get("sim_mode") else "Real iRacing",
        }
        for attr, val in c_map.items():
            if hasattr(self, attr):
                getattr(self, attr).setText(val)
        running_count = sum(1 for p in self.processes.values() if p.poll() is None)
        if hasattr(self, "lbl_d_count"):
            self.lbl_d_count.setText(f"{running_count} / 6 Active")

    # ── Overlay control ─────────────────────────────────────────
    def _toggle_overlay(self, key: str, script: str):
        if key in self.processes and self.processes[key].poll() is None:
            self.processes[key].terminate()
            del self.processes[key]
        else:
            py = sys.executable
            script_path = os.path.join(self.script_dir, script)
            self.processes[key] = subprocess.Popen([py, "main.py", "--overlay", key],
                                                   cwd=self.script_dir)
        self._apply_theme()

    def _toggle_all(self):
        any_running = any(p.poll() is None for p in self.processes.values())
        if any_running:
            for p in self.processes.values():
                if p.poll() is None:
                    p.terminate()
            self.processes.clear()
        else:
            SCRIPTS = {
                "gear": "overlay1.py", "inputs": "inputs_overlay.py",
                "delta": "delta_overlay.py", "relative": "relative_overlay.py",
                "radar": "radar_overlay.py", "fuel": "fuel_overlay.py",
            }
            for key, script in SCRIPTS.items():
                self.processes[key] = subprocess.Popen(
                    [sys.executable, "main.py", "--overlay", key],
                    cwd=self.script_dir
                )
        self._apply_theme()

    def _center_overlay(self, key: str):
        cfg = overlay_utils.load_config()
        defaults = overlay_utils.load_config()
        cfg[f"{key}_overlay"] = {"x": 100, "y": 100}
        overlay_utils.save_config(cfg)

    def _check_processes(self):
        dead = [k for k, p in self.processes.items() if p.poll() is not None]
        for k in dead:
            del self.processes[k]
        if dead:
            self._apply_theme()

    # ── Connection status ───────────────────────────────────────
    def _on_connection(self, connected: bool):
        c = overlay_utils.get_theme_colors(self.current_theme)
        if connected:
            self.status_dot.setStyleSheet(f"border-radius:3px; background:{c['accent']};")
            self.status_lbl.setText("CONNECTED")
            self.status_lbl.setStyleSheet(f"font-size:9px; font-weight:900; color:{c['accent']}; font-family:'Segoe UI';")
        else:
            self.status_dot.setStyleSheet("border-radius:3px; background:#ff3b30;")
            self.status_lbl.setText("OFFLINE")
            self.status_lbl.setStyleSheet("font-size:9px; font-weight:900; color:#8e8e93; font-family:'Segoe UI';")

    # ── Drag ────────────────────────────────────────────────────
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.drag_pos = e.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and self.drag_pos:
            self.move(e.globalPos() - self.drag_pos)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.drag_pos = None

    def closeEvent(self, e):
        for p in self.processes.values():
            if p.poll() is None:
                p.terminate()
        self.monitor.stop()
        e.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setStyle("Fusion")
    w = LauncherWindow()
    w.show()
    sys.exit(app.exec_())
