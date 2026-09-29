"""
main.py  -  iRacing HUD Overlay Suite v2.0
Punto de entrada principal.

Autor: vevi (VEVIkils556@gmail.com)
Version: 2.0.0
"""
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

def main():
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import Qt

    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app.setStyle("Fusion")

    if len(sys.argv) > 2 and sys.argv[1] == "--overlay":
        overlay_name = sys.argv[2]
        overlay_map = {
            "gear":     ("overlay1",    "OverlayWindow"),
            "inputs":   ("inputs_overlay", "InputOverlay"),
            "delta":    ("delta_overlay",  "DeltaOverlay"),
            "relative": ("relative_overlay", "RelativeOverlay"),
            "radar":    ("radar_overlay",  "RadarOverlay"),
            "fuel":     ("fuel_overlay",   "FuelOverlay"),
        }
        if overlay_name not in overlay_map:
            print(f"Overlay desconocido: {overlay_name}")
            sys.exit(1)
        mod_name, cls_name = overlay_map[overlay_name]
        mod = __import__(mod_name)
        cls = getattr(mod, cls_name)
        window = cls()
        window.show()
        sys.exit(app.exec_())
    else:
        import launcher_gui
        launcher = launcher_gui.LauncherWindow()
        launcher.show()
        sys.exit(app.exec_())

if __name__ == "__main__":
    main()
