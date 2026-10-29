"""
main.py - Entry Point for iRacing HUD Overlay Suite v3.0 Supreme
=================================================================
Author: vevi (VEVIkils556@gmail.com)
Version: 3.0 Supreme (RaceLab + Trophi.ai + SimHub + 2026 TV Broadcast)

Usage:
  python main.py                     -> Opens the Control Center GUI (Launcher)
  python main.py --overlay tv2026    -> 2026 F1 TV Broadcast Dashboard & Tower
  python main.py --overlay trophi    -> Trophi.ai Neural Coach & Reference Trace
  python main.py --overlay trackmap  -> RaceLab Live GPS Track Map & Pit Predictor
  python main.py --overlay tires     -> SimHub 4-Tire Thermals, Brakes & Weather
  python main.py --overlay standings -> RaceLab Multiclass Standings & iRating
  python main.py --overlay gear      -> Gear, RPM & Speedometer
  python main.py --overlay inputs    -> Pedal Telemetry, Trace & Steering Wheel
  python main.py --overlay delta     -> Lap Delta & Sector Splits
  python main.py --overlay relative  -> Relative Leaderboard Box
  python main.py --overlay radar     -> 2D Spatial Proximity Radar
  python main.py --overlay fuel      -> Fuel & Pit Strategy Calculator
"""

import sys
import argparse
from PyQt5.QtWidgets import QApplication


def run_single_overlay(overlay_type: str):
    app = QApplication(sys.argv)
    window = None

    if overlay_type == "gear":
        from overlay1 import IRacingOverlay
        window = IRacingOverlay()
    elif overlay_type == "inputs":
        from inputs_overlay import InputsOverlay
        window = InputsOverlay()
    elif overlay_type == "delta":
        from delta_overlay import DeltaOverlay
        window = DeltaOverlay()
    elif overlay_type == "relative":
        from relative_overlay import RelativeOverlay
        window = RelativeOverlay()
    elif overlay_type == "radar":
        from radar_overlay import RadarOverlay
        window = RadarOverlay()
    elif overlay_type == "fuel":
        from fuel_overlay import FuelOverlay
        window = FuelOverlay()
    elif overlay_type == "tv2026":
        from tv_2026_overlay import TV2026BroadcastOverlay
        window = TV2026BroadcastOverlay()
    elif overlay_type == "trophi":
        from trophiai_overlay import TrophiAIOverlay
        window = TrophiAIOverlay()
    elif overlay_type == "trackmap":
        from trackmap_overlay import TrackMapOverlay
        window = TrackMapOverlay()
    elif overlay_type == "tires":
        from tires_weather_overlay import TiresWeatherOverlay
        window = TiresWeatherOverlay()
    elif overlay_type == "standings":
        from standings_overlay import StandingsOverlay
        window = StandingsOverlay()
    else:
        print(f"Unknown overlay type: {overlay_type}")
        sys.exit(1)

    window.show()
    sys.exit(app.exec_())


def run_launcher(autostart: bool = False):
    app = QApplication(sys.argv)
    from launcher_gui import LauncherWindow
    launcher = LauncherWindow(autostart_tv2026=autostart)
    launcher.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="iRacing HUD Overlay Suite v3.0 Supreme by vevi")
    parser.add_argument(
        "--overlay",
        type=str,
        help="Overlay key: tv2026, trophi, trackmap, tires, standings, gear, inputs, delta, relative, radar, fuel"
    )
    parser.add_argument(
        "--autostart",
        action="store_true",
        help="Automatically launch the 2026 TV Broadcast + Trophi.ai + RaceLab + SimHub preset"
    )
    args = parser.parse_args()

    if args.overlay:
        run_single_overlay(args.overlay.lower())
    else:
        run_launcher(autostart=args.autostart)
