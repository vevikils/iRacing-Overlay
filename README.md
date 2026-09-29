# iRacing HUD Overlay Suite v2.0

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![PyQt5](https://img.shields.io/badge/PyQt-5.15%2B-green.svg)](https://pypi.org/project/PyQt5/)
[![iRacing SDK](https://img.shields.io/badge/pyirsdk-1.3.5-orange.svg)](https://pypi.org/project/pyirsdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-2.0.0-purple.svg)]()

> **Autor:** vevi (VEVIkils556@gmail.com)

Una suite completa de **Overlays de Telemetria en Tiempo Real** para **iRacing**, desarrollada en Python y PyQt5.  
Disenada para simracers que buscan widgets de telemetria premium, con temas visuales glassmorphism y bajo impacto en rendimiento.

---

## Novedades en v2.0

- **UI completamente rediseada** - glassmorphism premium con 7 temas visuales
- **Launcher reescrito** - 5 paginas (Dashboard, Overlays, Themes, Settings, About)
- **Shift lights dibujadas con QPainter** - render nativo sin artefactos visuales
- **Arquitectura modular limpia** - cada overlay es independiente y recargable
- **Demo mode mejorado** - telemetria sintetica de 60s con 6 etapas de circuito realistas

---

## Overlays incluidos

| Overlay | Descripcion |
|---------|-------------|
| ⚙ Gear & Speed | Marcha gigante, velocimetro KM/H y barra de shift lights F1 |
| 🚦 Inputs | Acelerador, freno, embrague y trazado historico en grafico |
| ⏱ Delta | Barra bidireccional de diferencia de tiempo respecto a la mejor vuelta |
| 📊 Relative | Pilotos cercanos con gaps, iRating, licencia y Safety Rating |
| 🛰 Radar | Spotter car left / car right / 3-wide con alertas visuales |
| ⛽ Fuel | Combustible restante, consumo por vuelta y temperaturas |

---

## Instalacion rapida

```bash
git clone https://github.com/vevikils/iRacing-Overlay.git
cd iRacing-Overlay/overlay-v2
pip install -r requirements.txt
python main.py
```

O con doble clic en **lanzar_overlay.bat**.

---

## Uso por CLI

```bash
# Lanzar panel de control
python main.py

# Lanzar un overlay individual
python main.py --overlay gear
python main.py --overlay inputs
python main.py --overlay delta
python main.py --overlay relative
python main.py --overlay radar
python main.py --overlay fuel
```

---

## Configuracion (config.json)

```json
{
    "locked": false,
    "theme": "racelab_pro",
    "opacity": 0.93,
    "sim_mode": false,
    "gear_overlay":     {"x": 100, "y": 350},
    "inputs_overlay":   {"x": 100, "y": 200},
    "delta_overlay":    {"x": 100, "y": 100},
    "relative_overlay": {"x": 100, "y": 500},
    "radar_overlay":    {"x": 400, "y": 100},
    "fuel_overlay":     {"x": 400, "y": 250}
}
```

---

## Temas visuales

| Key | Nombre |
|-----|--------|
| `classic_red` | Classic Red |
| `cyberpunk` | Cyberpunk Neon |
| `electric_blue` | Electric Blue |
| `toxic_green` | Toxic Green |
| `racelab_pro` | RaceLab Purple |
| `dark_carbon` | Stealth Carbon |
| `alpine_luxury` | Alpine Luxury |

---

## Compilar a .exe

```bash
pyinstaller launcher_gui.py --noconsole --icon=iRacingOverlay.ico --name="iRacingOverlay_v2"
```

---

## Licencia

MIT License - vevi (VEVIkils556@gmail.com)
