"""
render_overlay_previews.py - Renders High-Res Previews of All v3.0 Overlays
============================================================================
Author: vevi (VEVIkils556@gmail.com)
"""

import os
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap, QPainter, QColor, QFont, QLinearGradient
from PyQt5.QtCore import Qt, QRectF

from tv_2026_overlay import TV2026BroadcastOverlay
from trophiai_overlay import TrophiAIOverlay
from trackmap_overlay import TrackMapOverlay
from tires_weather_overlay import TiresWeatherOverlay
from standings_overlay import StandingsOverlay
from radar_overlay import RadarOverlay
from inputs_overlay import InputsOverlay
from fuel_overlay import FuelOverlay
from relative_overlay import RelativeOverlay
from delta_overlay import DeltaOverlay
from overlay1 import IRacingOverlay
from launcher_gui import LauncherWindow

ARTIFACT_DIR = r"C:\Users\alfaswz\.gemini\antigravity\brain\42498b41-1c8a-42cd-a1d2-dfcc666e8b2f"


def grab_widget_with_dark_bg(widget, out_path: str, base_w: int = None, base_h: int = None):
    widget._preview_mode = True
    if hasattr(widget, "update_telemetry"):
        widget.update_telemetry()
    widget._scale = 1.0
    widget._scale_x = 1.0
    widget._scale_y = 1.0
    if base_w and base_h:
        widget.resize(base_w, base_h)
    widget.repaint()
    w, h = widget.width(), widget.height()
    canvas = QPixmap(w, h)
    canvas.fill(QColor(8, 10, 15))
    p = QPainter(canvas)
    widget.render(p)
    p.end()
    canvas.save(out_path, "PNG")
    print(f"[OK] Saved {out_path} ({w}x{h})")
    return canvas


def main():
    app = QApplication(sys.argv)

    tv = TV2026BroadcastOverlay()
    trophi = TrophiAIOverlay()
    tmap = TrackMapOverlay()
    tires = TiresWeatherOverlay()
    standings = StandingsOverlay()
    radar = RadarOverlay()
    inputs = InputsOverlay()
    fuel = FuelOverlay()
    rel = RelativeOverlay()
    delta = DeltaOverlay()
    gear = IRacingOverlay()
    launcher = LauncherWindow()

    # 1. Save individual high-res captures at 1:1 native base resolution
    p_tv = grab_widget_with_dark_bg(tv, os.path.join(ARTIFACT_DIR, "preview_tv2026_broadcast_dashboard.png"), 1160, 560)
    p_trophi = grab_widget_with_dark_bg(trophi, os.path.join(ARTIFACT_DIR, "preview_trophiai_neural_coach.png"), 590, 435)
    p_tmap = grab_widget_with_dark_bg(tmap, os.path.join(ARTIFACT_DIR, "preview_racelab_trackmap_pit.png"), 380, 290)
    p_tires = grab_widget_with_dark_bg(tires, os.path.join(ARTIFACT_DIR, "preview_simhub_tires_weather.png"), 335, 315)
    p_stand = grab_widget_with_dark_bg(standings, os.path.join(ARTIFACT_DIR, "preview_racelab_standings.png"), 620, 445)
    p_radar = grab_widget_with_dark_bg(radar, os.path.join(ARTIFACT_DIR, "preview_radar_inputs_fuel.png"), 260, 260)
    for w_obj, bw, bh in [(inputs, 510, 175), (fuel, 340, 175), (rel, 385, 245), (delta, 380, 105), (gear, 260, 175)]:
        w_obj._preview_mode = True
        w_obj._scale = 1.0
        w_obj._scale_x = 1.0
        w_obj._scale_y = 1.0
        w_obj.resize(bw, bh)

    launcher.repaint()
    launcher.grab().save(os.path.join(ARTIFACT_DIR, "preview_launcher_v3_supreme.png"), "PNG")
    print("[OK] Saved Launcher v3.0 Supreme preview")

    # 2. Build a Full 1920x1080 Master Cockpit Showcase combining TV 2026 + RaceLab + Trophi.ai + SimHub
    master = QPixmap(1920, 1080)
    mp = QPainter(master)
    mp.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)

    # Simulated Onboard Cockpit / Track Horizon Background
    bg_grad = QLinearGradient(0, 0, 0, 1080)
    bg_grad.setColorAt(0.0, QColor(12, 17, 28))
    bg_grad.setColorAt(0.45, QColor(22, 30, 46))
    bg_grad.setColorAt(0.48, QColor(16, 20, 28))
    bg_grad.setColorAt(1.0, QColor(8, 10, 14))
    mp.fillRect(0, 0, 1920, 1080, bg_grad)

    # Title Banner at Top Center
    mp.setPen(QColor("#00F5D4"))
    mp.setFont(QFont("Segoe UI", 14, QFont.Black))
    mp.drawText(QRectF(0, 8, 1920, 28), Qt.AlignCenter, "iRACING HUD OVERLAY SUITE v3.0 SUPREME · TV 2026 + RACELAB + TROPHI.AI + SIMHUB (BY VEVI)")

    # Render Overlays onto 1920x1080 canvas with zero overlap
    tv.move(10, 36)
    tv.render(mp, tv.pos())
    tmap.move(1525, 36)
    tmap.render(mp, tmap.pos())
    rel.move(1520, 336)
    rel.render(mp, rel.pos())
    tires.move(16, 602)
    tires.render(mp, tires.pos())
    trophi.move(362, 602)
    trophi.render(mp, trophi.pos())
    radar.move(962, 602)
    radar.render(mp, radar.pos())
    fuel.move(955, 875)
    fuel.render(mp, fuel.pos())
    standings.move(1285, 602)
    standings.render(mp, standings.pos())

    mp.end()
    master_path = os.path.join(ARTIFACT_DIR, "preview_full_1080p_hud_suite_v3.png")
    master.save(master_path, "PNG")
    print(f"[OK] Saved Full 1080p Master HUD Showcase: {master_path}")


if __name__ == "__main__":
    main()
