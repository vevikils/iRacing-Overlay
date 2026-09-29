"""
overlay_utils.py  -  iRacing HUD Overlay Suite v2.0
Utilidades compartidas: config, temas y telemetria simulada.

Autor: vevi (VEVIkils556@gmail.com)
Version: 2.0.0
"""

import os
import json
import time
import math
import sys

def get_base_path():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

_DEFAULT_CONFIG = {
    "locked": False,
    "theme": "racelab_pro",
    "opacity": 0.93,
    "sim_mode": False,
    "gear_overlay":     {"x": 100, "y": 350},
    "inputs_overlay":   {"x": 100, "y": 200},
    "delta_overlay":    {"x": 100, "y": 100},
    "relative_overlay": {"x": 100, "y": 500},
    "radar_overlay":    {"x": 400, "y": 100},
    "fuel_overlay":     {"x": 400, "y": 250},
}

def load_config():
    cfg = json.loads(json.dumps(_DEFAULT_CONFIG))
    path = os.path.join(get_base_path(), "config.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            for k, v in loaded.items():
                if isinstance(v, dict) and k in cfg and isinstance(cfg[k], dict):
                    cfg[k].update(v)
                else:
                    cfg[k] = v
        except Exception as exc:
            print(f"[overlay_utils] Error cargando config: {exc}")
    return cfg

def save_config(config):
    path = os.path.join(get_base_path(), "config.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as exc:
        print(f"[overlay_utils] Error guardando config: {exc}")

LIC_COLORS = {"R":"#ef233c","D":"#f77f00","C":"#fcbf49","B":"#38b000","A":"#0077b6","P":"#7209b7"}

_THEMES = {
    "classic_red":    {"name":"Classic Red",      "accent":"#ff3b30","accent_rgb":(255,59,48),   "accent_secondary":"#ff6b6b","bg_gradient":"qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 rgba(20,10,10,245),stop:1 rgba(8,8,8,252))","border":"rgba(255,59,48,0.45)","border_soft":"rgba(255,255,255,0.06)","text":"#ffffff","text_secondary":"#8e8e93","text_dark":"#1c1c1e","glow":"rgba(255,59,48,0.65)","chart_throttle":"#34c759","chart_brake":"#ff3b30"},
    "cyberpunk":      {"name":"Cyberpunk Neon",   "accent":"#ff007f","accent_rgb":(255,0,127),   "accent_secondary":"#00f0ff","bg_gradient":"qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 rgba(12,8,20,245),stop:1 rgba(4,4,10,252))","border":"rgba(255,0,127,0.55)","border_soft":"rgba(0,240,255,0.15)","text":"#00f0ff","text_secondary":"#ff007f","text_dark":"#080810","glow":"rgba(255,0,127,0.70)","chart_throttle":"#00f0ff","chart_brake":"#ff007f"},
    "electric_blue":  {"name":"Electric Blue",    "accent":"#007aff","accent_rgb":(0,122,255),   "accent_secondary":"#0a84ff","bg_gradient":"qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 rgba(10,20,40,245),stop:1 rgba(4,8,18,252))","border":"rgba(0,122,255,0.50)","border_soft":"rgba(255,255,255,0.05)","text":"#ffffff","text_secondary":"#0a84ff","text_dark":"#0a0c14","glow":"rgba(0,122,255,0.65)","chart_throttle":"#30d158","chart_brake":"#ff453a"},
    "toxic_green":    {"name":"Toxic Green",       "accent":"#39ff14","accent_rgb":(57,255,20),   "accent_secondary":"#ccff00","bg_gradient":"qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 rgba(8,18,8,245),stop:1 rgba(4,8,4,252))","border":"rgba(57,255,20,0.50)","border_soft":"rgba(255,255,255,0.04)","text":"#39ff14","text_secondary":"#ccff00","text_dark":"#0a120a","glow":"rgba(57,255,20,0.70)","chart_throttle":"#39ff14","chart_brake":"#ff3b30"},
    "racelab_pro":    {"name":"RaceLab Purple",   "accent":"#9d4edd","accent_rgb":(157,78,221),  "accent_secondary":"#00f5d4","bg_gradient":"qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 rgba(14,10,28,248),stop:1 rgba(6,4,12,255))","border":"rgba(157,78,221,0.60)","border_soft":"rgba(0,245,212,0.14)","text":"#ffffff","text_secondary":"#c77dff","text_dark":"#060410","glow":"rgba(157,78,221,0.80)","chart_throttle":"#00f5d4","chart_brake":"#ff0054"},
    "dark_carbon":    {"name":"Stealth Carbon",   "accent":"#e0e1dd","accent_rgb":(224,225,221), "accent_secondary":"#00b4d8","bg_gradient":"qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 rgba(20,22,26,248),stop:1 rgba(8,9,11,255))","border":"rgba(255,255,255,0.18)","border_soft":"rgba(255,255,255,0.07)","text":"#ffffff","text_secondary":"#9ca3af","text_dark":"#0f111a","glow":"rgba(255,255,255,0.38)","chart_throttle":"#10b981","chart_brake":"#ef4444"},
    "alpine_luxury":  {"name":"Alpine Luxury",    "accent":"#0090ff","accent_rgb":(0,144,255),   "accent_secondary":"#d4af37","bg_gradient":"qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 rgba(10,22,46,248),stop:1 rgba(4,8,18,255))","border":"rgba(0,144,255,0.60)","border_soft":"rgba(212,175,55,0.18)","text":"#ffffff","text_secondary":"#70b5ff","text_dark":"#030810","glow":"rgba(0,144,255,0.80)","chart_throttle":"#00e5ff","chart_brake":"#ff3366"},
}

def get_theme_colors(theme_name):
    colors = _THEMES.get(theme_name, _THEMES["racelab_pro"]).copy()
    colors["lic_colors"] = LIC_COLORS
    return colors

def get_all_themes():
    return [(k, v["name"]) for k, v in _THEMES.items()]

def get_sim_telemetry(t):
    lap_len = 60.0
    tl = t % lap_len
    throttle = brake = clutch = 0.0
    gear = 1; speed_kmh = 0.0; rpm = 1000.0; delta = 0.0
    if tl < 18.0:
        p = tl / 18.0; throttle = 1.0; speed_kmh = 60 + p * 200
        if speed_kmh < 90:    gear,rpm = 1, 3000+(speed_kmh-60)*80
        elif speed_kmh < 130: gear,rpm = 2, 4500+(speed_kmh-90)*80
        elif speed_kmh < 170: gear,rpm = 3, 5000+(speed_kmh-130)*75
        elif speed_kmh < 210: gear,rpm = 4, 5200+(speed_kmh-170)*70
        else:                 gear,rpm = 5, 5500+(speed_kmh-210)*60
        for sp in [90,130,170,210]:
            if abs(speed_kmh-sp)<4: throttle=0.0; clutch=0.6*(1-abs(speed_kmh-sp)/4); rpm=4000; break
        delta = -0.15-p*0.25
    elif tl < 24.0:
        p=(tl-18)/6; brake=0.85 if p<0.2 else 0.85-(p-0.2)*0.8; speed_kmh=260-p*185
        if speed_kmh>200: gear,rpm=5,6500
        elif speed_kmh>160: gear,rpm=4,7200
        elif speed_kmh>120: gear,rpm=3,7100
        else: gear,rpm=2,6800
        delta=-0.40+p*0.15
    elif tl < 32.0:
        p=(tl-24)/8; throttle=min(1.0,p*1.5); speed_kmh=75+p*85
        if speed_kmh<110: gear,rpm=2,4000+(speed_kmh-75)*80
        elif speed_kmh<150: gear,rpm=3,4800+(speed_kmh-110)*80
        else: gear,rpm=4,5200+(speed_kmh-150)*70
        delta=-0.25-p*0.10
    elif tl < 42.0:
        p=(tl-32)/10
        if p<0.2: brake=0.60;speed_kmh=160-p/0.2*70;gear=2;rpm=5500-(160-speed_kmh)*20
        elif p<0.5: throttle=0.80;speed_kmh=90+(p-0.2)/0.3*40;gear=3;rpm=4500+(speed_kmh-90)*60
        elif p<0.8: brake=0.50;speed_kmh=130-(p-0.5)/0.3*45;gear=2;rpm=6000-(130-speed_kmh)*30
        else: throttle=0.40;speed_kmh=85+(p-0.8)/0.2*15;gear=2;rpm=4500+(speed_kmh-85)*60
        delta=-0.35+math.sin(p*math.pi*3)*0.12
    elif tl < 52.0:
        p=(tl-42)/10
        if p<0.6: throttle=0.70;speed_kmh=100+p/0.6*50;gear=3;rpm=5000+(speed_kmh-100)*50
        else: p2=(p-0.6)/0.4;brake=0.70-p2*0.5;speed_kmh=150-p2*65;gear=2;rpm=6500-(150-speed_kmh)*30
        delta=-0.30+p*0.15
    else:
        p=(tl-52)/8; throttle=1.0; speed_kmh=85+p*135
        if speed_kmh<120: gear,rpm=2,4000+(speed_kmh-85)*80
        elif speed_kmh<165: gear,rpm=3,5000+(speed_kmh-120)*75
        else: gear,rpm=4,5500+(speed_kmh-165)*65
        delta=-0.15-p*0.30
    speed_ms=speed_kmh/3.6; shift_pct=min(1.0,max(0.0,(rpm-3500)/4500.0))
    fuel_level=max(2.5,45.0-(t/60.0)*2.8); fuel_per_lap=2.78
    car_left=(t%30)>22 and (t%30)<27; car_right=(t%45)>38 and (t%45)<42
    drivers=[
        {"CarIdx":0,"Position":1,"Name":"Lucas Perez","Number":"14","IRating":3450,"IRGain":45,"LicShort":"A","LicColor":0x0077B6,"Gap":8.5+math.sin(t*0.05)*0.5,"SR":"4.99","Class":"GT3","LastLap":"1:23.45"},
        {"CarIdx":1,"Position":2,"Name":"Jane Smith","Number":"7","IRating":2980,"IRGain":12,"LicShort":"B","LicColor":0x38B000,"Gap":4.2+math.sin(t*0.10)*0.2,"SR":"3.20","Class":"GT3","LastLap":"1:24.12"},
        {"CarIdx":6,"Position":3,"Name":"Lewis Hamilton","Number":"44","IRating":5400,"IRGain":-15,"LicShort":"A","LicColor":0x0077B6,"Gap":2.1+math.sin(t*0.06)*0.3,"SR":"4.80","Class":"GT3","LastLap":"1:23.20"},
        {"CarIdx":2,"Position":4,"Name":"ALFA SWZ","Number":"88","IRating":2500,"IRGain":25,"LicShort":"C","LicColor":0xFCBF49,"Gap":0.0,"SR":"2.85","Class":"GT3","LastLap":"1:23.95"},
        {"CarIdx":3,"Position":5,"Name":"M. Verstappen","Number":"33","IRating":8200,"IRGain":-5,"LicShort":"P","LicColor":0x7209B7,"Gap":-1.8-(t%15)*0.08,"SR":"4.99","Class":"GT3","LastLap":"1:22.10"},
        {"CarIdx":4,"Position":6,"Name":"Carlos Sainz","Number":"55","IRating":4120,"IRGain":65,"LicShort":"A","LicColor":0x0077B6,"Gap":-4.4+math.cos(t*0.04)*0.3,"SR":"4.21","Class":"GT3","LastLap":"1:23.18"},
        {"CarIdx":7,"Position":7,"Name":"F. Alonso","Number":"14","IRating":5800,"IRGain":10,"LicShort":"A","LicColor":0x0077B6,"Gap":-6.5+math.sin(t*0.04)*0.4,"SR":"4.95","Class":"GT3","LastLap":"1:22.90"},
        {"CarIdx":8,"Position":8,"Name":"Ch. Leclerc","Number":"16","IRating":4700,"IRGain":-20,"LicShort":"B","LicColor":0x38B000,"Gap":-8.9+math.cos(t*0.05)*0.3,"SR":"3.90","Class":"GT3","LastLap":"1:23.35"},
        {"CarIdx":9,"Position":9,"Name":"Lando Norris","Number":"4","IRating":4900,"IRGain":35,"LicShort":"A","LicColor":0x0077B6,"Gap":-11.2+math.sin(t*0.07)*0.2,"SR":"4.10","Class":"GT3","LastLap":"1:23.10"},
        {"CarIdx":5,"Position":10,"Name":"Rookie Driver","Number":"99","IRating":1150,"IRGain":-40,"LicShort":"R","LicColor":0xEF233C,"Gap":-18.4+math.sin(t*0.02)*0.8,"SR":"1.50","Class":"GT3","LastLap":"1:27.40"},
    ]
    drivers.sort(key=lambda x: x["Gap"], reverse=True)
    return {"Speed":speed_ms,"RPM":rpm,"Gear":gear,"ShiftIndicatorPct":shift_pct,"Throttle":throttle,"Brake":brake,"Clutch":clutch,"LapDeltaToBestLap":delta,"LapDeltaToSessionBest":delta,"Delta":delta,"PlayerCarIdx":2,"PlayerIdx":2,"SOF":2850,"Incidents":f"{int((t//10)%9)}/17","SessionTimeRemain":max(0.0,1800.0-t),"Lap":int(t//60)+1,"Relatives":drivers,"FuelLevel":fuel_level,"FuelPerLap":fuel_per_lap,"FuelLapsRemaining":fuel_level/fuel_per_lap if fuel_per_lap>0 else 0,"SpotterLeft":car_left,"SpotterRight":car_right,"WaterTemp":85.0+math.sin(t*0.02)*2.0,"OilTemp":92.0+math.sin(t*0.015)*3.0}
