"""
overlay_utils.py - Shared Configuration, Themes & Live iRacing Telemetry Bridge
===============================================================================
Author: vevi (VEVIkils556@gmail.com)
Version: 3.2 Supreme (Live iRacing Session Drivers + All-Corners Braking AI)
"""

import json
import os
import math
import time
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPixmap, QPainter, QColor, QFont, QPen, QPolygonF, QFontMetrics
from PyQt5.QtCore import Qt, QRectF, QPoint, QPointF
from iracing_live_engine import get_live_or_sim_telemetry

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
ASSETS_3D_DIR = os.path.join(BASE_DIR, "assets_3d")

_ASSET_3D_CACHE = {}


def get_3d_asset(filename: str) -> QPixmap:
    """
    Loads and caches a Blender 4.2 3D PBR rendered RGBA UI component from assets_3d/.
    """
    if filename in _ASSET_3D_CACHE:
        return _ASSET_3D_CACHE[filename]
    full_path = os.path.join(ASSETS_3D_DIR, filename)
    pix = QPixmap(full_path) if os.path.exists(full_path) else QPixmap()
    _ASSET_3D_CACHE[filename] = pix
    return pix


def draw_3d_card_bezel(p, x: float, y: float, w: float, h: float, asset_name: str = "card_carbon_bezel_3d.png"):
    """
    Draws a Blender 3D machined titanium + carbon fiber weave card bezel into (x, y, w, h).
    """
    pix = get_3d_asset(asset_name)
    if not pix.isNull():
        p.drawPixmap(QRectF(x, y, w, h), pix, QRectF(0, 0, pix.width(), pix.height()))
        return True
    return False


_CHAR_REPLACEMENTS = {
    "━": "-",
    "┅": "--",
    "▸": ">",
    "▶": ">",
    "◀": "<",
    "●": "*",
    "⏱": "",
    "📍": "",
    "🧠": "",
    "🗺️": "",
    "🗺": "",
    "🛞": "",
    "🌦️": "",
    "🌦": "",
    "🏆": "",
    "📡": "",
    "⛽": "",
    "🌡️": "",
    "🌡": "",
    "⚠️": "[!]",
    "⚠": "[!]",
    "✔": "[OK]",
    "⚡": "",
    "→": "->",
    "·": "|",
}


def sanitize_hud_text(text: str) -> str:
    """Replaces special Unicode/emoji glyphs that cause boxes or misalignment in Windows HUD fonts."""
    if not text:
        return ""
    s = str(text)
    for k, v in _CHAR_REPLACEMENTS.items():
        if k in s:
            s = s.replace(k, v)
    return " ".join(s.split()) if "  " in s else s.strip()


def draw_elided_text(p: QPainter, rect: QRectF, flags: int, text: str):
    """Sanitizes text and elides it to fit strictly inside rect without ever overflowing."""
    clean = sanitize_hud_text(text)
    fm = QFontMetrics(p.font())
    elided = fm.elidedText(clean, Qt.ElideRight, max(10, int(rect.width())))
    p.drawText(rect, flags, elided)


class ResizableLockableOverlay(QWidget):
    """
    Universal base class for all 11 iRacing HUD Overlays:
    - Freely movable by dragging anywhere inside the window (when unlocked)
    - Freely resizable by dragging the bottom-right grip or edges, or using Mouse Wheel / [+] [-] buttons
    - Lockable / Pinnable ("Fijable") per window or globally so it cannot be accidentally moved while racing
    - Automatically syncs scale, custom width/height, opacity, and lock state with config.json
    """
    RESIZE_MARGIN = 18

    def __init__(self, overlay_key: str, base_w: int, base_h: int, default_x: int = 100, default_y: int = 100):
        super().__init__()
        self.overlay_key = overlay_key
        self.base_w = base_w
        self.base_h = base_h
        self._default_x = default_x
        self._default_y = default_y

        self._cfg = load_config()
        self._theme = get_theme(self._cfg)
        self._opacity = float(self._cfg.get("opacity", 0.96))

        ov = self._cfg.get("overlays", {}).get(self.overlay_key, {})
        global_scale = float(self._cfg.get("scale", 1.0))
        self._scale_x = float(ov.get("scale_x", ov.get("scale", global_scale)))
        self._scale_y = float(ov.get("scale_y", ov.get("scale", global_scale)))
        self._scale = self._scale_x
        self._locked = bool(ov.get("locked", False) or self._cfg.get("locked_all", False))

        self._dragging = False
        self._resizing = False
        self._resize_mode = ""  # "br", "r", "b"
        self._drag_pos = QPoint()
        self._resize_start_pos = QPoint()
        self._resize_start_size = (0, 0)
        self._hovered = False
        self._preview_mode = False

        # Hit rects in widget coordinates for the top-right mini toolbar
        self._btn_minus_rect = QRectF()
        self._btn_plus_rect = QRectF()
        self._btn_reset_rect = QRectF()
        self._btn_lock_rect = QRectF()

        self.setMouseTracking(True)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(self._opacity)

        win_w = max(int(self.base_w * 0.5), int(round(self.base_w * self._scale_x)))
        win_h = max(int(self.base_h * 0.5), int(round(self.base_h * self._scale_y)))
        self.setGeometry(
            int(ov.get("x", default_x)),
            int(ov.get("y", default_y)),
            win_w,
            win_h
        )
        self._last_saved_global_scale = global_scale

    def sync_window_from_config(self):
        """Called during telemetry ticks to react live to Launcher changes (scale, opacity, lock)."""
        if self._dragging or self._resizing or self._preview_mode:
            return
        self._cfg = load_config()
        self._theme = get_theme(self._cfg)

        new_op = float(self._cfg.get("opacity", 0.96))
        if abs(new_op - self._opacity) > 0.01:
            self._opacity = new_op
            self.setWindowOpacity(self._opacity)

        ov = self._cfg.get("overlays", {}).get(self.overlay_key, {})
        self._locked = bool(ov.get("locked", False) or self._cfg.get("locked_all", False))

        global_scale = float(self._cfg.get("scale", 1.0))
        if abs(global_scale - self._last_saved_global_scale) > 0.01 and "scale_x" not in ov:
            self._last_saved_global_scale = global_scale
            self._scale_x = global_scale
            self._scale_y = global_scale
            self._scale = global_scale
            self.resize(int(round(self.base_w * self._scale_x)), int(round(self.base_h * self._scale_y)))
        elif "scale_x" in ov or "scale" in ov:
            sx = float(ov.get("scale_x", ov.get("scale", self._scale_x)))
            sy = float(ov.get("scale_y", ov.get("scale", self._scale_y)))
            if abs(sx - self._scale_x) > 0.01 or abs(sy - self._scale_y) > 0.01:
                self._scale_x = sx
                self._scale_y = sy
                self._scale = sx
                self.resize(int(round(self.base_w * self._scale_x)), int(round(self.base_h * self._scale_y)))

    def _save_geometry_to_config(self):
        cfg = load_config()
        ov = cfg.setdefault("overlays", {}).setdefault(self.overlay_key, {})
        ov["x"] = self.x()
        ov["y"] = self.y()
        ov["scale"] = round(self._scale_x, 3)
        ov["scale_x"] = round(self._scale_x, 3)
        ov["scale_y"] = round(self._scale_y, 3)
        ov["locked"] = bool(self._locked)
        save_config(cfg)

    def set_overlay_scale(self, new_sx: float, new_sy: float = None):
        sx = max(0.50, min(2.50, new_sx))
        sy = max(0.50, min(2.50, new_sy if new_sy is not None else sx))
        self._scale_x = sx
        self._scale_y = sy
        self._scale = sx
        self.resize(int(round(self.base_w * sx)), int(round(self.base_h * sy)))
        self._save_geometry_to_config()
        self.update()

    def toggle_lock(self):
        self._locked = not self._locked
        cfg = load_config()
        if not self._locked:
            cfg["locked_all"] = False
        ov = cfg.setdefault("overlays", {}).setdefault(self.overlay_key, {})
        ov["locked"] = self._locked
        save_config(cfg)
        self.update()

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.setCursor(Qt.ArrowCursor)
        self.update()

    def _detect_resize_zone(self, pos: QPoint) -> str:
        if self._locked:
            return ""
        w, h = self.width(), self.height()
        m = self.RESIZE_MARGIN
        on_r = (w - m <= pos.x() <= w)
        on_b = (h - m <= pos.y() <= h)
        if on_r and on_b:
            return "br"
        if on_r:
            return "r"
        if on_b:
            return "b"
        return ""

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            p = QPointF(event.pos())
            # 1. Check Lock/Pin button (always clickable even when locked!)
            if self._btn_lock_rect.contains(p):
                self.toggle_lock()
                event.accept()
                return

            if self._locked:
                event.ignore()
                return

            # 2. Check [-], [+], [1:1] size buttons
            if self._btn_minus_rect.contains(p):
                self.set_overlay_scale(self._scale_x - 0.10, self._scale_y - 0.10)
                event.accept()
                return
            if self._btn_plus_rect.contains(p):
                self.set_overlay_scale(self._scale_x + 0.10, self._scale_y + 0.10)
                event.accept()
                return
            if self._btn_reset_rect.contains(p):
                self.set_overlay_scale(1.0, 1.0)
                event.accept()
                return

            # 3. Check Resize Grip / Borders
            zone = self._detect_resize_zone(event.pos())
            if zone:
                self._resizing = True
                self._resize_mode = zone
                self._resize_start_pos = event.globalPos()
                self._resize_start_size = (self.width(), self.height())
                event.accept()
                return

            # 4. Otherwise start window move drag
            self._dragging = True
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            self.setCursor(Qt.SizeAllCursor)
            event.accept()

    def mouseMoveEvent(self, event):
        if self._resizing and (event.buttons() & Qt.LeftButton):
            delta = event.globalPos() - self._resize_start_pos
            start_w, start_h = self._resize_start_size
            new_w = start_w + (delta.x() if "r" in self._resize_mode else 0)
            new_h = start_h + (delta.y() if "b" in self._resize_mode else 0)

            # Hold Shift for independent X/Y aspect ratio, otherwise uniform proportional scaling
            if not (event.modifiers() & Qt.ShiftModifier) and self._resize_mode == "br":
                ratio = max(0.50, min(2.50, new_w / float(self.base_w)))
                self._scale_x = ratio
                self._scale_y = ratio
            else:
                self._scale_x = max(0.50, min(2.50, new_w / float(self.base_w)))
                self._scale_y = max(0.50, min(2.50, new_h / float(self.base_h)))
            self._scale = self._scale_x
            self.resize(int(round(self.base_w * self._scale_x)), int(round(self.base_h * self._scale_y)))
            self.update()
            event.accept()
            return

        if self._dragging and (event.buttons() & Qt.LeftButton):
            if not self._locked:
                self.move(event.globalPos() - self._drag_pos)
            event.accept()
            return

        # Update hover cursor
        p = QPointF(event.pos())
        if (
            self._btn_lock_rect.contains(p)
            or (not self._locked and (self._btn_minus_rect.contains(p) or self._btn_plus_rect.contains(p) or self._btn_reset_rect.contains(p)))
        ):
            self.setCursor(Qt.PointingHandCursor)
            return

        zone = self._detect_resize_zone(event.pos())
        if zone == "br":
            self.setCursor(Qt.SizeFDiagCursor)
        elif zone == "r":
            self.setCursor(Qt.SizeHorCursor)
        elif zone == "b":
            self.setCursor(Qt.SizeVerCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._dragging or self._resizing:
                self._dragging = False
                self._resizing = False
                self.setCursor(Qt.ArrowCursor)
                self._save_geometry_to_config()
            event.accept()

    def wheelEvent(self, event):
        """Allows resizing any unlocked overlay smoothly with the mouse wheel."""
        if self._locked:
            return
        step = 0.06 if event.angleDelta().y() > 0 else -0.06
        self.set_overlay_scale(self._scale_x + step, self._scale_y + step)
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_L:
            self.toggle_lock()

    def begin_overlay_painter(self) -> QPainter:
        """Initializes QPainter with smooth scaling across both X and Y dimensions."""
        p = QPainter(self)
        p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        sx = self.width() / float(self.base_w)
        sy = self.height() / float(self.base_h)
        p.scale(sx, sy)
        return p

    def end_overlay_painter(self, p: QPainter):
        """Draws the interactive Lock/Pin & Resize mini-controls in screen coordinates and ends painting."""
        if self._preview_mode:
            p.end()
            return

        p.resetTransform()
        w, h = self.width(), self.height()

        # Draw bottom-right 3D resize grip when unlocked
        if not self._locked:
            p.setPen(QPen(QColor("#00F5D4"), 1.6))
            for offset in (4, 8, 12):
                p.drawLine(w - offset, h - 3, w - 3, h - offset)

        # Draw top-right interactive Lock & Scale mini-toolbar when hovered
        if self._hovered:
            alpha = 240
            bar_h = 18
            if self._locked:
                self._btn_minus_rect = QRectF()
                self._btn_plus_rect = QRectF()
                self._btn_reset_rect = QRectF()
                self._btn_lock_rect = QRectF(w - 64, 4, 58, bar_h)

                p.setBrush(QColor(225, 6, 0, alpha))
                p.setPen(QPen(QColor("#FFFFFF"), 1.0))
                p.drawRoundedRect(self._btn_lock_rect, 4, 4)
                p.setFont(QFont("Segoe UI", 7, QFont.Black))
                p.setPen(QColor("#FFFFFF"))
                p.drawText(self._btn_lock_rect, Qt.AlignCenter, "FIJADO")
            else:
                self._btn_minus_rect = QRectF(w - 134, 4, 20, bar_h)
                self._btn_plus_rect = QRectF(w - 112, 4, 20, bar_h)
                self._btn_reset_rect = QRectF(w - 90, 4, 26, bar_h)
                self._btn_lock_rect = QRectF(w - 62, 4, 56, bar_h)

                for r_btn, txt, bg_c in [
                    (self._btn_minus_rect, "-", QColor(16, 22, 34, alpha)),
                    (self._btn_plus_rect, "+", QColor(16, 22, 34, alpha)),
                    (self._btn_reset_rect, f"{int(round(self._scale_x*100))}%", QColor(16, 22, 34, alpha)),
                    (self._btn_lock_rect, "FIJAR", QColor(0, 165, 145, alpha)),
                ]:
                    p.setBrush(bg_c)
                    p.setPen(QPen(QColor("#00F5D4"), 1.0))
                    p.drawRoundedRect(r_btn, 4, 4)
                    p.setFont(QFont("Segoe UI", 6 if "%" in txt else 7, QFont.Black))
                    p.setPen(QColor("#FFFFFF"))
                    p.drawText(r_btn, Qt.AlignCenter, txt)

        p.end()

_DEFAULT_CONFIG = {
    "opacity": 0.96,
    "scale": 1.0,
    "theme": "f1_2026_tv",
    "sim_mode": False,
    "overlays": {
        "gear_overlay": {"x": 810, "y": 780, "enabled": True},
        "inputs_overlay": {"x": 380, "y": 800, "enabled": True},
        "delta_overlay": {"x": 790, "y": 40, "enabled": True},
        "relative_overlay": {"x": 1490, "y": 530, "enabled": True},
        "radar_overlay": {"x": 850, "y": 460, "enabled": True},
        "fuel_overlay": {"x": 1520, "y": 830, "enabled": True},
        "tv2026_overlay": {"x": 20, "y": 30, "enabled": True},
        "trophi_overlay": {"x": 380, "y": 510, "enabled": True},
        "trackmap_overlay": {"x": 1500, "y": 40, "enabled": True},
        "tires_overlay": {"x": 40, "y": 730, "enabled": True},
        "standings_overlay": {"x": 40, "y": 60, "enabled": False}
    }
}

THEMES = {
    "f1_2026_tv": {
        "name": "F1 2026 TV Broadcast (Official)",
        "primary": "#E10600",
        "secondary": "#00F5D4",
        "bg": (10, 12, 18, 242),
        "panel": (18, 22, 32, 235),
        "border": (225, 6, 0, 210),
        "text_dim": "#8E96AA",
        "accent": "#FFD700"
    },
    "racelab_pro": {
        "name": "RaceLab Pro Telemetry",
        "primary": "#FF5500",
        "secondary": "#00E5FF",
        "bg": (13, 15, 20, 240),
        "panel": (22, 25, 34, 230),
        "border": (255, 85, 0, 190),
        "text_dim": "#8A92A6",
        "accent": "#A855F7"
    },
    "trophi_ai": {
        "name": "Trophi.ai Coach Neural",
        "primary": "#8B5CF6",
        "secondary": "#10B981",
        "bg": (12, 10, 22, 242),
        "panel": (21, 18, 38, 232),
        "border": (139, 92, 246, 200),
        "text_dim": "#94A3B8",
        "accent": "#38BDF8"
    },
    "simhub_gt": {
        "name": "SimHub GT3 Bosch DDU",
        "primary": "#00D4FF",
        "secondary": "#FFCC00",
        "bg": (8, 10, 14, 245),
        "panel": (16, 20, 28, 235),
        "border": (0, 212, 255, 190),
        "text_dim": "#7E8B9B",
        "accent": "#22C55E"
    },
    "classic_red": {
        "name": "Apex Crimson",
        "primary": "#FF1E1E",
        "secondary": "#00FF88",
        "bg": (12, 12, 16, 235),
        "panel": (22, 22, 30, 220),
        "border": (255, 30, 30, 180),
        "text_dim": "#888899",
        "accent": "#FFAA00"
    },
    "cyberpunk": {
        "name": "Night City Neon",
        "primary": "#FCEE09",
        "secondary": "#00F0FF",
        "bg": (15, 10, 25, 235),
        "panel": (28, 18, 45, 220),
        "border": (252, 238, 9, 190),
        "text_dim": "#A388EE",
        "accent": "#FF0055"
    },
    "dark_carbon": {
        "name": "Stealth Carbon",
        "primary": "#FFFFFF",
        "secondary": "#FF3366",
        "bg": (8, 8, 10, 245),
        "panel": (16, 16, 20, 235),
        "border": (90, 90, 105, 180),
        "text_dim": "#666675",
        "accent": "#00E5FF"
    }
}

# Fallback Driver Roster matching the user's real FIA F4 Monza iRacing session
FALLBACK_SESSION_DRIVERS = [
    {"pos": 1,  "tla": "JEF", "name": "Nicholas Jeffries",     "num": "1",  "team": "#1 N. Jeffries",    "color": "#EC232D", "tire": "S", "laps_tire": 5, "ir": "1.04k", "sr": "C 2.01", "pits": 0, "best": 116.412},
    {"pos": 2,  "tla": "LUM", "name": "Nicholas Lumma",        "num": "2",  "team": "#2 N. Lumma",       "color": "#0038FF", "tire": "S", "laps_tire": 5, "ir": "1.04k", "sr": "D 2.88", "pits": 0, "best": 116.584},
    {"pos": 3,  "tla": "SOM", "name": "Joshua Somers",         "num": "3",  "team": "#3 J. Somers",      "color": "#D90FFA", "tire": "S", "laps_tire": 5, "ir": "1.03k", "sr": "C 1.53", "pits": 0, "best": 116.710},
    {"pos": 4,  "tla": "RUS", "name": "Tomas Rusinol",         "num": "4",  "team": "#4 T. Rusinol",     "color": "#2E358F", "tire": "S", "laps_tire": 5, "ir": "1.01k", "sr": "D 2.32", "pits": 0, "best": 116.845},
    {"pos": 5,  "tla": "MON", "name": "Samuel Mongare",        "num": "5",  "team": "#5 S. Mongare",     "color": "#8500FA", "tire": "S", "laps_tire": 5, "ir": "993",   "sr": "D 1.99", "pits": 0, "best": 116.990},
    {"pos": 6,  "tla": "GAR", "name": "Nate Garcia",           "num": "6",  "team": "#6 N. Garcia",      "color": "#FF0000", "tire": "S", "laps_tire": 5, "ir": "989",   "sr": "D 0.98", "pits": 0, "best": 117.120},
    {"pos": 7,  "tla": "FAS", "name": "Lenar Fasakhiev",       "num": "7",  "team": "#7 L. Fasakhiev",   "color": "#52FF00", "tire": "S", "laps_tire": 5, "ir": "988",   "sr": "D 2.08", "pits": 0, "best": 117.260},
    {"pos": 8,  "tla": "CUN", "name": "Bertolino Cunha",       "num": "8",  "team": "#8 B. Cunha",       "color": "#005EFF", "tire": "S", "laps_tire": 5, "ir": "979",   "sr": "D 2.36", "pits": 0, "best": 117.410},
    {"pos": 9,  "tla": "LEV", "name": "Mark Levant",           "num": "9",  "team": "#9 M. Levant",      "color": "#F25306", "tire": "S", "laps_tire": 5, "ir": "970",   "sr": "D 2.70", "pits": 0, "best": 117.550},
    {"pos": 10, "tla": "ROD", "name": "Bruno Rodriguez",       "num": "10", "team": "#10 B. Rodriguez",  "color": "#EC232D", "tire": "S", "laps_tire": 5, "ir": "967",   "sr": "D 1.69", "pits": 0, "best": 117.690},
    {"pos": 21, "tla": "ARR", "name": "Jaime Arroyo",          "num": "21", "team": "#21 J. Arroyo",     "color": "#EFD600", "tire": "S", "laps_tire": 5, "ir": "437",   "sr": "D 0.99", "pits": 0, "best": 118.420},
    {"pos": 22, "tla": "ROD", "name": "Bruno Rodrigues",       "num": "22", "team": "#22 B. Rodrigues",  "color": "#09ED5E", "tire": "S", "laps_tire": 5, "ir": "342",   "sr": "D 1.67", "pits": 0, "best": 118.590},
    {"pos": 23, "tla": "GAR", "name": "D. Garcia Fernandez [TU]", "full_name": "Diego Garcia Fernandez", "num": "23", "team": "#23 D. Garcia", "color": "#00F5D4", "tire": "S", "laps_tire": 5, "ir": "240", "sr": "D 0.25", "pits": 0, "best": 116.355, "is_player": True},
]


def load_config():
    if not os.path.exists(CONFIG_PATH):
        save_config(_DEFAULT_CONFIG)
        return json.loads(json.dumps(_DEFAULT_CONFIG))
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k, v in _DEFAULT_CONFIG.items():
            if k not in data:
                data[k] = v
        for ok, ov in _DEFAULT_CONFIG["overlays"].items():
            if ok not in data["overlays"]:
                data["overlays"][ok] = ov
        return data
    except Exception:
        return json.loads(json.dumps(_DEFAULT_CONFIG))


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
    except Exception as e:
        print(f"[overlay_utils] Error saving config: {e}")


def get_theme(cfg=None):
    if cfg is None:
        cfg = load_config()
    t_name = cfg.get("theme", "f1_2026_tv")
    return THEMES.get(t_name, THEMES["f1_2026_tv"])


def _generate_synthetic_telemetry(t=None):
    """
    Generates realistic FIA F4 @ Autodromo Nazionale Monza 60Hz telemetry
    across all 7 Monza corners when the car is in the garage or iRacing is closed.
    """
    if t is None:
        t = time.time()

    lap_duration = 116.355  # 1:56.355 F4 Monza lap
    lap_time = t % lap_duration
    lap_pct = lap_time / lap_duration
    current_lap = 5 + int((t // lap_duration) % 10)
    total_laps = 15

    # Exact Monza 7 corner zones: (center_pct, half_width, min_speed_kmh, brake_peak, turn_dir, name)
    corners = [
        (0.142, 0.032, 76,  0.96,  1.0,  "T1-T2 Rettifilo Chicane"),
        (0.235, 0.028, 222, 0.08,  0.55, "T3 Curva Grande"),
        (0.350, 0.030, 96,  0.88, -0.90, "T4-T5 Della Roggia"),
        (0.475, 0.025, 138, 0.64,  0.80, "T6 Lesmo 1"),
        (0.538, 0.026, 124, 0.74,  0.85, "T7 Lesmo 2"),
        (0.726, 0.034, 142, 0.84, -0.92, "T8-T10 Variante Ascari"),
        (0.915, 0.032, 152, 0.78,  0.88, "T11 Parabolica Alboreto"),
    ]

    opt_throttle = 1.0
    opt_brake = 0.0
    steer_deg = 0.0
    lat_g = 0.0
    long_g = 0.35
    target_speed = 246.0
    active_corner_name = "RECTA PRINCIPAL MONZA"
    in_corner_zone = False

    for c_pct, c_w, c_min_spd, c_brk, c_dir, c_name in corners:
        dist = lap_pct - c_pct
        if dist > 0.5:
            dist -= 1.0
        elif dist < -0.5:
            dist += 1.0

        if -c_w * 1.4 <= dist <= c_w * 1.3:
            in_corner_zone = True
            active_corner_name = c_name
            norm = dist / c_w

            if c_brk > 0.15 and -1.35 <= norm <= 0.18:
                b_phase = (norm + 1.35) / 1.53
                if b_phase < 0.24:
                    opt_brake = c_brk * (b_phase / 0.24)
                else:
                    opt_brake = c_brk * math.pow(max(0.0, 1.0 - (b_phase - 0.24) / 0.76), 1.40)
                opt_throttle = 0.0
            if norm > -0.08:
                t_phase = min(1.0, max(0.0, (norm + 0.08) / 1.15))
                opt_throttle = math.pow(t_phase, 1.2)

            apex_factor = math.exp(-(norm * norm) / 0.52)
            target_speed = 244.0 - (244.0 - c_min_spd) * apex_factor
            steer_factor = math.exp(-((norm - 0.05) ** 2) / 0.36)
            steer_deg = c_dir * (145.0 * (c_brk ** 0.65)) * steer_factor
            lat_g = c_dir * (3.2 * (c_brk ** 0.5)) * steer_factor
            break

    if not in_corner_zone:
        straight_wave = 0.5 + 0.5 * math.sin(lap_pct * math.pi * 6.0)
        target_speed = 215.0 + 33.0 * straight_wave
        steer_deg = 2.5 * math.sin(t * 2.1)
        lat_g = 0.18 * math.sin(t * 2.1)

    human_err = 0.035 * math.sin(t * 3.8)
    live_brake = max(0.0, min(1.0, opt_brake + (human_err if opt_brake > 0.05 else 0.0)))
    live_throttle = max(0.0, min(1.0, opt_throttle - (abs(human_err) * 0.6 if opt_throttle < 0.95 else 0.0)))
    clutch = 0.0

    if live_brake > 0.05:
        long_g = -3.6 * live_brake
    else:
        long_g = 0.95 * live_throttle * (1.0 - (target_speed / 280.0))

    speed_kmh = max(62.0, target_speed + 1.8 * math.sin(t * 4.5))
    speed_mph = speed_kmh * 0.621371

    # 6-Speed FIA F4 Gearbox mapping
    gear_thresholds = [0, 88, 126, 158, 188, 216, 260]
    gear = 1
    for g_idx in range(1, 7):
        if speed_kmh >= gear_thresholds[g_idx - 1]:
            gear = g_idx
    g_low = gear_thresholds[gear - 1]
    g_high = gear_thresholds[gear]
    rpm_norm = (speed_kmh - g_low) / max(1.0, g_high - g_low)
    rpm = int(5200 + max(0.0, min(1.04, rpm_norm)) * 1950)
    max_rpm = 7200
    shift_pct = max(0.0, min(1.0, (rpm - 5600) / (max_rpm - 5600)))

    is_straight = (not in_corner_zone) and (speed_kmh > 195.0)
    active_aero_mode = "X-MODE (LOW DRAG)" if is_straight else "Z-MODE (HIGH DOWNFORCE)"
    drs_active = is_straight and (speed_kmh > 210.0)
    mom_override = is_straight and (0.0 <= (lap_pct % 0.5) <= 0.28)
    ers_battery_pct = max(15.0, min(100.0, 74.0 + 22.0 * math.cos(lap_pct * math.pi * 2.0)))
    ers_status = "HARVESTING" if live_brake > 0.20 else ("MOM 350kW BOOST" if mom_override else "DEPLOYING")

    delta = -0.18 - 0.11 * math.sin(lap_pct * math.pi * 4.0)
    abs_active = (live_brake > 0.91) and (math.sin(t * 32.0) > 0.25)
    tc_active = (live_throttle > 0.86) and in_corner_zone and (math.sin(t * 28.0) > 0.35)

    base_brk_temp = 390.0 + (410.0 * live_brake)
    tires = {
        "FL": {"temps": (92, 96, 100), "psi": 23.2, "wear": 95, "brake_temp": int(base_brk_temp + 20)},
        "FR": {"temps": (91, 95, 98),  "psi": 23.1, "wear": 95, "brake_temp": int(base_brk_temp + 10)},
        "RL": {"temps": (88, 91, 94),  "psi": 21.8, "wear": 96, "brake_temp": int(base_brk_temp - 55)},
        "RR": {"temps": (87, 90, 93),  "psi": 21.7, "wear": 96, "brake_temp": int(base_brk_temp - 65)},
    }

    standings = []
    for idx, d in enumerate(FALLBACK_SESSION_DRIVERS):
        gap_leader = 0.0 if idx == 0 else round(idx * 0.92 + 0.15 * math.sin(t * 0.7 + idx), 3)
        prev_gap = 0.0 if idx <= 1 else round((idx - 1) * 0.92 + 0.15 * math.sin(t * 0.7 + idx - 1), 3)
        interval = 0.0 if idx == 0 else round(max(0.10, gap_leader - prev_gap), 3)
        rel_gap = 0.0 if d.get("is_player") else round((12 - idx) * 0.85, 2)
        car_lap_pct = (lap_pct + (rel_gap / lap_duration)) % 1.0
        standings.append({
            **d,
            "gap_leader": gap_leader,
            "interval": interval,
            "rel_gap": rel_gap,
            "lap_pct": car_lap_pct,
            "last_lap": round(d["best"] + 0.21, 3),
            "in_pit": False,
            "has_fastest_lap": d.get("is_player", False)
        })

    relatives = [
        {
            "pos": s["pos"], "num": s["num"], "tla": s["tla"], "name": s["name"],
            "team": s["team"], "color": s["color"], "tire": s["tire"],
            "ir": s["ir"], "sr": s["sr"], "gap": s["rel_gap"],
            "last_lap": s["last_lap"], "best_lap": s["best"], "is_player": s.get("is_player", False)
        }
        for s in standings[-6:]
    ]

    radar_cycle = math.sin(t * 0.95)
    radar_left = max(0.0, min(1.0, (radar_cycle - 0.15) * 1.4))
    radar_right = max(0.0, min(1.0, (-radar_cycle - 0.35) * 1.5))
    radar_opponents = []
    if radar_left > 0.05:
        radar_opponents.append({"side": "L", "lat_m": -1.9, "long_m": 2.4 * math.cos(t * 1.2), "danger": radar_left})
    if radar_right > 0.05:
        radar_opponents.append({"side": "R", "lat_m": 1.9, "long_m": -2.0 * math.sin(t * 1.1), "danger": radar_right})

    return {
        "track_name": "Autodromo Nazionale Monza",
        "track_len_m": 5750.8,
        "player_name": "Diego Garcia Fernandez",
        "player_num": "23",
        "player_car": "FIA F4",
        "total_drivers": 23,
        "speed_kmh": int(round(speed_kmh)),
        "speed_mph": int(round(speed_mph)),
        "rpm": rpm,
        "max_rpm": max_rpm,
        "gear": gear,
        "shift_pct": shift_pct,
        "throttle": live_throttle,
        "brake": live_brake,
        "clutch": clutch,
        "opt_throttle": opt_throttle,
        "opt_brake": opt_brake,
        "steer_deg": steer_deg,
        "lat_g": lat_g,
        "long_g": long_g,
        "drs_active": drs_active,
        "mom_override": mom_override,
        "active_aero_mode": active_aero_mode,
        "ers_battery_pct": ers_battery_pct,
        "ers_status": ers_status,
        "delta": delta,
        "s1_delta": -0.06,
        "s2_delta": -0.08,
        "s3_delta": -0.04,
        "lap_time": lap_time,
        "best_lap": 116.355,
        "last_lap": 116.590,
        "lap_pct": lap_pct,
        "current_lap": current_lap,
        "total_laps": total_laps,
        "active_corner_name": active_corner_name,
        "trail_brake_score": 92,
        "corner_score": 94,
        "coach_tip": "FRENADA MONITORIZADA EN TODAS LAS CURVAS",
        "coach_status": "ALL CORNERS AI",
        "abs_active": abs_active,
        "tc_active": tc_active,
        "tires": tires,
        "weather": {
            "track_temp": 25.4,
            "air_temp": 19.8,
            "wind_speed_kmh": 7.9,
            "wind_dir_deg": 145,
            "rain_pct": 0,
            "track_wetness": "DRY (0%)",
            "grip_level": "MONZA LIVE"
        },
        "fuel_level": 16.4,
        "fuel_per_lap": 1.65,
        "fuel_est_laps": 9.9,
        "fuel_needed": 0.0,
        "pit_rejoin_pct": (lap_pct - 0.19) % 1.0,
        "standings": standings,
        "all_standings": standings,
        "relatives": relatives,
        "radar_left": radar_left,
        "radar_right": radar_right,
        "radar_opponents": radar_opponents,
        "sof": 812,
        "flag_status": "GREEN FLAG"
    }


def get_sim_telemetry(t=None):
    """
    Unified telemetry entrypoint called by all 11 overlays.
    Automatically reads live iRacing session drivers & real-time corner braking AI
    whenever iRacing is open!
    """
    return get_live_or_sim_telemetry(_generate_synthetic_telemetry)
