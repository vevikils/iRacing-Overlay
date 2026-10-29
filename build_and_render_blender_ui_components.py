"""
build_and_render_blender_ui_components.py
=========================================
Builds & renders ultra-modern 3D PBR UI components in Blender 4.2 LTS for the
iRacing HUD Overlay Suite v3.5 Supreme (by vevi).

Outputs in `overlay-v2/assets_3d/`:
  1. f1_2026_steering_wheel_3d.png  (512x512 RGBA - 3D Sculpted F1 Butterfly Wheel)
  2. halo_telemetry_chassis_3d.png  (1592x1032 RGBA - 3D Carbon/Titanium TV 2026 Halo Pod)
  3. timing_tower_chassis_3d.png    (630x1072 RGBA - 3D F1 2026 Broadcast Tower Frame)
  4. trophi_neural_chassis_3d.png   (1180x870 RGBA - 3D Trophi.ai Neural Coach Frame)
  5. radar_scope_3d.png             (520x520 RGBA - 3D Spatial Radar Bezel & Grid)
  6. radar_3d_f4_player_car.png     (256x256 RGBA - Top-Down 3D Formula Car Cyan)
  7. radar_3d_f4_opponent_car.png   (256x256 RGBA - Top-Down 3D Formula Car Red/Orange)
  8. gforce_sphere_3d.png           (260x260 RGBA - 3D Glass & Titanium G-Force Gyro)
  9. card_carbon_bezel_3d.png       (800x600 RGBA - Universal 3D Carbon/Titanium Panel Frame)
 10. launcher_hero_banner_3d.png    (1520x240 RGBA - 3D Hero Showcase Banner for Launcher GUI)
"""

import bpy
import bmesh
import math
import os

OUT_DIR = r"c:\Users\alfaswz\.gemini\antigravity-ide\scratch\agentes-personalizados\overlay-v2\assets_3d"
os.makedirs(OUT_DIR, exist_ok=True)
BLEND_PATH = os.path.join(OUT_DIR, "iRacing_Overlay_3D_UI_Components.blend")


# ==============================================================================
# MATERIAL LIBRARY (PBR Carbon Fiber, Brushed Titanium, Anodized Metal, Neon)
# ==============================================================================
def create_pbr_materials():
    mats = {}

    def new_bsdf(name, base_col, metallic=0.0, roughness=0.4, emission_col=None, emission_str=0.0, alpha=1.0):
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        if alpha < 1.0:
            mat.blend_method = 'BLEND'
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()

        out = nodes.new("ShaderNodeOutputMaterial")
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.inputs["Base Color"].default_value = (*base_col, 1.0)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        if "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = alpha

        if emission_col and emission_str > 0.0:
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = (*emission_col, 1.0)
                bsdf.inputs["Emission Strength"].default_value = emission_str
            elif "Emission" in bsdf.inputs:
                bsdf.inputs["Emission"].default_value = (*emission_col, 1.0)

        links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
        return mat, nodes, links, bsdf

    # 1. Procedural 3D Carbon Fiber Weave
    m_carb, nodes, links, bsdf = new_bsdf("Carbon_Fiber_3D", (0.035, 0.042, 0.060), metallic=0.35, roughness=0.22)
    tex_coord = nodes.new("ShaderNodeTexCoord")
    checker = nodes.new("ShaderNodeTexChecker")
    checker.inputs["Scale"].default_value = 85.0
    checker.inputs["Color1"].default_value = (0.02, 0.025, 0.038, 1.0)
    checker.inputs["Color2"].default_value = (0.055, 0.068, 0.095, 1.0)
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.18
    bump.inputs["Distance"].default_value = 0.01
    links.new(tex_coord.outputs["Object"], checker.inputs["Vector"])
    links.new(checker.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(checker.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    mats["carbon"] = m_carb

    # 2. Dark Gunmetal Brushed Titanium
    m_tit, _, _, _ = new_bsdf("Brushed_Titanium", (0.09, 0.11, 0.15), metallic=0.92, roughness=0.20)
    mats["titanium"] = m_tit

    # 3. Chrome / Silver Machined Alloy
    m_chr, _, _, _ = new_bsdf("Machined_Chrome", (0.65, 0.72, 0.80), metallic=0.98, roughness=0.12)
    mats["chrome"] = m_chr

    # 4. Dark Glass Panel (Translucent Deep Slate)
    m_gls, _, _, _ = new_bsdf("Dark_Glass_Panel", (0.018, 0.024, 0.038), metallic=0.45, roughness=0.08, alpha=0.90)
    mats["glass"] = m_gls

    # 5. Alcantara / Matte Grip Rubber
    m_alc, _, _, _ = new_bsdf("Alcantara_Grip", (0.025, 0.028, 0.035), metallic=0.05, roughness=0.82)
    mats["alcantara"] = m_alc

    # 6. Emissive Neon Cyan (#00F5D4) for thin laser pipes
    m_cyan, _, _, _ = new_bsdf("Neon_Cyan", (0.0, 0.92, 0.80), metallic=0.3, roughness=0.15, emission_col=(0.0, 0.92, 0.80), emission_str=2.6)
    mats["cyan"] = m_cyan

    # 6b. Rich Anodized Metallic Cyan for car bodies & caps
    m_cyan_metal, _, _, _ = new_bsdf("Anodized_Cyan", (0.0, 0.68, 0.62), metallic=0.85, roughness=0.20, emission_col=(0.0, 0.68, 0.62), emission_str=0.35)
    mats["cyan_metal"] = m_cyan_metal

    # 7. Emissive F1 Crimson Red (#E10600) for thin laser pipes
    m_red, _, _, _ = new_bsdf("Neon_Red", (0.88, 0.015, 0.015), metallic=0.4, roughness=0.18, emission_col=(0.90, 0.02, 0.01), emission_str=2.4)
    mats["red"] = m_red

    # 7b. Rich Anodized F1 Crimson Metallic for headers & car bodies
    m_red_metal, _, _, _ = new_bsdf("Anodized_Red", (0.68, 0.01, 0.015), metallic=0.85, roughness=0.20, emission_col=(0.68, 0.01, 0.015), emission_str=0.30)
    mats["red_metal"] = m_red_metal

    # 8. Emissive Trophi Neural Violet (#8B5CF6)
    m_vio, _, _, _ = new_bsdf("Neon_Violet", (0.48, 0.22, 0.92), metallic=0.5, roughness=0.18, emission_col=(0.48, 0.22, 0.92), emission_str=1.8)
    mats["violet"] = m_vio

    # 8b. Deep Anodized Violet for Fastest Lap pod
    m_vio_metal, _, _, _ = new_bsdf("Anodized_Violet", (0.28, 0.08, 0.58), metallic=0.85, roughness=0.22, emission_col=(0.28, 0.08, 0.58), emission_str=0.25)
    mats["violet_metal"] = m_vio_metal

    # 9. Emissive Gold / Amber (#F59E0B)
    m_gld, _, _, _ = new_bsdf("Anodized_Gold", (0.96, 0.62, 0.04), metallic=0.88, roughness=0.18, emission_col=(0.96, 0.62, 0.04), emission_str=1.5)
    mats["gold"] = m_gld

    # 10. Emerald Green (#10B981)
    m_grn, _, _, _ = new_bsdf("Neon_Green", (0.06, 0.73, 0.51), metallic=0.3, roughness=0.18, emission_col=(0.06, 0.73, 0.51), emission_str=3.8)
    mats["green"] = m_grn

    # 11. Tire Rubber
    m_tire, _, _, _ = new_bsdf("Slick_Tire", (0.02, 0.02, 0.022), metallic=0.1, roughness=0.55)
    mats["tire"] = m_tire

    return mats


def clear_scene_objects():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def setup_studio_lighting_and_camera(ortho_scale=10.0, res_x=1024, res_y=1024, is_ortho=True):
    scene = bpy.context.scene
    # Use BLENDER_EEVEE_NEXT in Blender 4.2 or BLENDER_EEVEE fallback
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
        try:
            scene.render.engine = eng
            break
        except Exception:
            continue

    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.resolution_percentage = 100

    # Camera looking straight down -Z from (0, 0, 12)
    cam_data = bpy.data.cameras.new("StudioCam")
    if is_ortho:
        cam_data.type = 'ORTHO'
        cam_data.ortho_scale = ortho_scale
    else:
        cam_data.type = 'PERSP'
        cam_data.lens = 50.0
    cam_obj = bpy.data.objects.new("StudioCam", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    cam_obj.location = (0.0, 0.0, 12.0)
    cam_obj.rotation_euler = (0.0, 0.0, 0.0)
    scene.camera = cam_obj

    # 3-Point Studio Area Lighting for Metallic Bevels & Carbon Specular Highlights
    lights_spec = [
        ("KeyLight_TopLeft",  (-6.0,  6.0, 8.0), (0.35, -0.35, 0.0), 450.0, (0.90, 0.96, 1.0)),
        ("FillLight_Right",   ( 7.0, -5.0, 7.0), (-0.30, 0.35, 0.0), 320.0, (1.0,  0.92, 0.95)),
        ("RimLight_Cyan",     ( 0.0,  8.0, 5.0), (0.45,  0.0,  0.0), 280.0, (0.2,  0.95, 0.90)),
    ]
    for lname, loc, rot, energy, col in lights_spec:
        ldata = bpy.data.lights.new(name=lname, type='AREA')
        ldata.energy = energy
        ldata.color = col
        ldata.size = 8.0
        lobj = bpy.data.objects.new(name=lname, object_data=ldata)
        bpy.context.collection.objects.link(lobj)
        lobj.location = loc
        lobj.rotation_euler = rot

    return cam_obj


def add_beveled_box(name, loc, scale, mat, bevel_width=0.08, segments=4):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    bev = obj.modifiers.new(name="Bevel", type='BEVEL')
    bev.width = bevel_width
    bev.segments = segments
    bev.limit_method = 'ANGLE'
    bpy.ops.object.shade_smooth()
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    return obj


def add_cylinder(name, loc, radius, depth, mat, vertices=64, rot=(0, 0, 0), bevel_w=0.02):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc, rotation=rot)
    obj = bpy.context.active_object
    obj.name = name
    if bevel_w > 0:
        bev = obj.modifiers.new(name="Bevel", type='BEVEL')
        bev.width = bevel_w
        bev.segments = 3
    bpy.ops.object.shade_smooth()
    obj.data.materials.append(mat)
    return obj


def add_torus(name, loc, major_r, minor_r, mat, major_seg=96, minor_seg=24, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_r, minor_radius=minor_r,
        major_segments=major_seg, minor_segments=minor_seg,
        location=loc
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.shade_smooth()
    obj.data.materials.append(mat)
    return obj


# ==============================================================================
# 1. RENDER 3D F1 2026 BUTTERFLY STEERING WHEEL (`f1_2026_steering_wheel_3d.png`)
# ==============================================================================
def render_f1_steering_wheel(mats):
    clear_scene_objects()
    setup_studio_lighting_and_camera(ortho_scale=4.6, res_x=512, res_y=512, is_ortho=True)

    # Rear Gold Shift Paddles (Left & Right)
    add_beveled_box("Paddle_L", (-1.45, 0.25, -0.22), (0.55, 1.35, 0.08), mats["gold"], bevel_width=0.04)
    add_beveled_box("Paddle_R", ( 1.45, 0.25, -0.22), (0.55, 1.35, 0.08), mats["gold"], bevel_width=0.04)

    # Main Carbon Fiber Butterfly Central Chassis Plate
    plate = add_beveled_box("Carbon_Chassis", (0.0, -0.05, 0.0), (3.10, 2.05, 0.22), mats["carbon"], bevel_width=0.18, segments=6)

    # Cutout / Recessed Lower Window Effect & Side Grips
    add_torus("Grip_Rim_Outer", (0.0, -0.04, 0.06), 1.62, 0.21, mats["alcantara"], scale=(1.08, 0.72, 0.85))

    # Top Carbon Brow Bridge + 12 Shift LEDs Housing
    add_beveled_box("Top_Carbon_Brow", (0.0, 0.98, 0.14), (2.35, 0.36, 0.18), mats["carbon"], bevel_width=0.06)

    # Top Center Crimson Red Stripe Marker
    add_beveled_box("Top_Red_Stripe", (0.0, 1.12, 0.20), (0.20, 0.24, 0.16), mats["red"], bevel_width=0.02)

    # 10 3D Shift LED Lenses along Top Brow
    for i in range(10):
        lx = -0.90 + i * 0.20
        led_mat = mats["green"] if i < 3 else (mats["red"] if i < 7 else mats["violet"])
        add_cylinder(f"Wheel_LED_{i}", (lx, 0.98, 0.24), 0.055, 0.08, led_mat, vertices=24)

    # Central Sunken DDU Display Bezel (Titanium + Dark Glass)
    add_beveled_box("DDU_Titanium_Frame", (0.0, 0.18, 0.16), (1.75, 1.05, 0.14), mats["titanium"], bevel_width=0.05)
    add_beveled_box("DDU_Glass_Screen", (0.0, 0.18, 0.20), (1.56, 0.88, 0.10), mats["glass"], bevel_width=0.02)
    add_beveled_box("DDU_Cyan_Trim", (0.0, 0.62, 0.23), (1.45, 0.04, 0.06), mats["cyan"], bevel_width=0.01)

    # 4 Rotary Encoders (Knobs) with Chrome Rings & Colored Caps
    knobs = [
        (-1.18,  0.42, mats["red"]),
        ( 1.18,  0.42, mats["cyan"]),
        (-1.18, -0.25, mats["gold"]),
        ( 1.18, -0.25, mats["violet"]),
        (-0.52, -0.62, mats["green"]),
        ( 0.52, -0.62, mats["red"]),
    ]
    for idx, (kx, ky, kmat) in enumerate(knobs):
        add_cylinder(f"Knob_Base_{idx}", (kx, ky, 0.16), 0.19, 0.14, mats["chrome"], vertices=32)
        add_cylinder(f"Knob_Cap_{idx}",  (kx, ky, 0.24), 0.14, 0.12, kmat, vertices=24)
        add_beveled_box(f"Knob_Ptr_{idx}", (kx, ky + 0.05, 0.30), (0.04, 0.12, 0.05), mats["titanium"], bevel_width=0.01)

    # Center Quick-Release Hub Ring at bottom
    add_cylinder("QR_Hub", (0.0, -0.62, 0.16), 0.28, 0.14, mats["titanium"], vertices=36)
    add_cylinder("QR_Center", (0.0, -0.62, 0.22), 0.16, 0.12, mats["cyan"], vertices=36)

    out_path = os.path.join(OUT_DIR, "f1_2026_steering_wheel_3d.png")
    bpy.context.scene.render.filepath = out_path
    bpy.ops.render.render(write_still=True)
    print(f"[BLENDER 3D] Rendered {out_path}")


# ==============================================================================
# 2. RENDER 3D HALO TELEMETRY CHASSIS (`halo_telemetry_chassis_3d.png`)
# ==============================================================================
def render_halo_telemetry_chassis(mats):
    clear_scene_objects()
    # Aspect ratio matches BASE_W=796, BASE_H=516 -> 15.92 x 10.32 ortho units
    W, H = 15.92, 10.32
    setup_studio_lighting_and_camera(ortho_scale=W, res_x=1592, res_y=1032, is_ortho=True)

    # Outer Titanium Exoskeleton Frame
    add_beveled_box("Outer_Titanium_Shell", (0, 0, -0.35), (W - 0.15, H - 0.15, 0.32), mats["titanium"], bevel_width=0.22, segments=6)

    # Inner Carbon Fiber Weave Deck
    add_beveled_box("Inner_Carbon_Deck", (0, 0, -0.18), (W - 0.42, H - 0.42, 0.28), mats["carbon"], bevel_width=0.18, segments=5)

    # Glowing F1 2026 Red & Cyan Top/Bottom Laser Light Pipes
    add_beveled_box("Top_Laser_Red", (0, H/2 - 0.14, 0.05), (W - 1.2, 0.08, 0.08), mats["red"], bevel_width=0.02)
    add_beveled_box("Bot_Laser_Cyan", (0, -H/2 + 0.14, 0.05), (W - 1.2, 0.08, 0.08), mats["cyan"], bevel_width=0.02)

    # Top Header Bar 3D Bezel
    # Mapped from Qt (x+18, y+12, w-36, 32) -> center Y = H/2 - 0.56
    add_beveled_box("Header_Bezel", (0, H/2 - 0.56, 0.02), (W - 0.72, 0.66, 0.16), mats["titanium"], bevel_width=0.05)
    add_beveled_box("Header_Glass", (0, H/2 - 0.56, 0.08), (W - 0.84, 0.56, 0.12), mats["glass"], bevel_width=0.03)

    # Left Gauge Turbine Ring (Center in Qt: x=150, y=205 out of 796x516)
    # In Ortho coords: X = (150 - 398) * 0.02 = -4.96, Y = (258 - 205) * 0.02 = +1.06
    lx, ly = -4.96, 1.06
    add_torus("Left_Turbine_Bezel", (lx, ly, 0.06), 2.28, 0.11, mats["titanium"])
    add_torus("Left_Cyan_Accent", (lx, ly, 0.12), 2.34, 0.025, mats["cyan"])
    add_cylinder("Left_G_Well", (lx, ly, -0.02), 1.16, 0.18, mats["glass"], vertices=64)

    # Left G-Force Telemetry Pod at bottom-left: Qt (28, 345, 244, 86) -> center (150, 388)
    gb_x, gb_y = -4.96, (258 - 388) * 0.02
    add_beveled_box("G_Box_Titanium", (gb_x, gb_y, 0.02), (4.92, 1.74, 0.16), mats["titanium"], bevel_width=0.06)
    add_beveled_box("G_Box_Glass", (gb_x, gb_y, 0.08), (4.78, 1.60, 0.12), mats["glass"], bevel_width=0.04)

    # Center Main Halo Ring (Center in Qt: x=405, y=205) -> X = (405-398)*0.02 = +0.14, Y = +1.06
    cx, cy = 0.14, 1.06
    add_torus("Center_Halo_Arch", (cx, cy, 0.08), 2.62, 0.14, mats["titanium"])
    add_torus("Center_Halo_RedRim", (cx, cy, 0.16), 2.68, 0.03, mats["red"])
    add_cylinder("Center_Dial_Well", (cx, cy, -0.04), 2.42, 0.16, mats["glass"], vertices=72)

    # Right 3D Module Bays (Qt rx=545, rw=232 -> center X = 661 -> (661-398)*0.02 = +5.26)
    rx = 5.26
    right_bays = [
        ("Aero_Bay",   (258 - (62 + 27)) * 0.02,  4.68, 1.12, mats["titanium"]),
        ("ERS_Bay",    (258 - (182 + 49)) * 0.02, 4.68, 1.98, mats["titanium"]),
        ("Sector_Bay", (258 - (292 + 69)) * 0.02, 4.68, 2.78, mats["titanium"]),
    ]
    for bname, by, bw, bh, rim_mat in right_bays:
        add_beveled_box(bname, (rx, by, 0.02), (bw, bh, 0.16), rim_mat, bevel_width=0.06)
        add_beveled_box(bname + "_Glass", (rx, by, 0.08), (bw - 0.14, bh - 0.14, 0.12), mats["glass"], bevel_width=0.04)

    # Bottom Broadcast Lower-Third Wing Bar (Qt y = 516 - 62 = 454, h = 48 -> center Y = 478 -> (258-478)*0.02 = -4.40)
    add_beveled_box("Lower_Third_Frame", (0, -4.40, 0.04), (W - 0.72, 0.98, 0.18), mats["titanium"], bevel_width=0.06)
    add_beveled_box("Lower_Third_RedWing", (-W/2 + 1.85, -4.40, 0.10), (2.90, 0.88, 0.14), mats["red_metal"], bevel_width=0.05)
    add_beveled_box("Lower_Third_Glass", (1.40, -4.40, 0.09), (W - 3.65, 0.88, 0.12), mats["glass"], bevel_width=0.04)

    # Corner Hex Bolts
    for bx in (-W/2 + 0.35, W/2 - 0.35):
        for by in (-H/2 + 0.35, H/2 - 0.35):
            add_cylinder("HexBolt", (bx, by, 0.06), 0.11, 0.12, mats["chrome"], vertices=6)

    out_path = os.path.join(OUT_DIR, "halo_telemetry_chassis_3d.png")
    bpy.context.scene.render.filepath = out_path
    bpy.ops.render.render(write_still=True)
    print(f"[BLENDER 3D] Rendered {out_path}")


# ==============================================================================
# 3. RENDER 3D TIMING TOWER CHASSIS (`timing_tower_chassis_3d.png`)
# ==============================================================================
def render_timing_tower_chassis(mats):
    clear_scene_objects()
    # Aspect ratio matches 315 x 536 -> 6.30 x 10.72 ortho units
    W, H = 6.30, 10.72
    setup_studio_lighting_and_camera(ortho_scale=H, res_x=630, res_y=1072, is_ortho=True)
    # Note: in Blender, when res_y > res_x, ortho_scale controls the largest dimension (height)!

    add_beveled_box("Tower_Titanium_Shell", (0, 0, -0.30), (W - 0.12, H - 0.12, 0.30), mats["titanium"], bevel_width=0.16, segments=5)
    add_beveled_box("Tower_Carbon_Core", (0, 0, -0.14), (W - 0.34, H - 0.34, 0.24), mats["carbon"], bevel_width=0.12, segments=4)

    # Top F1 Crimson 3D Hood
    add_beveled_box("Tower_Red_Header", (0, H/2 - 0.46, 0.06), (W - 0.24, 0.82, 0.22), mats["red_metal"], bevel_width=0.08)
    add_beveled_box("Tower_SubHeader", (0, H/2 - 1.02, 0.08), (W - 0.32, 0.38, 0.16), mats["glass"], bevel_width=0.03)

    # Side Neon Strips
    add_beveled_box("Tower_Left_Laser", (-W/2 + 0.09, -0.2, 0.06), (0.05, H - 2.2, 0.10), mats["red"], bevel_width=0.01)
    add_beveled_box("Tower_Right_Laser", ( W/2 - 0.09, -0.2, 0.06), (0.05, H - 2.2, 0.10), mats["cyan"], bevel_width=0.01)

    # Bottom Fastest Lap 3D Violet Pod
    add_beveled_box("Tower_Fastest_Pod", (0, -H/2 + 0.52, 0.06), (W - 0.34, 0.72, 0.20), mats["violet_metal"], bevel_width=0.06)

    out_path = os.path.join(OUT_DIR, "timing_tower_chassis_3d.png")
    bpy.context.scene.render.filepath = out_path
    bpy.ops.render.render(write_still=True)
    print(f"[BLENDER 3D] Rendered {out_path}")


# ==============================================================================
# 4. RENDER 3D TROPHI.AI NEURAL COACH CHASSIS (`trophi_neural_chassis_3d.png`)
# ==============================================================================
def render_trophi_neural_chassis(mats):
    clear_scene_objects()
    # Matches BASE_W=590, BASE_H=435 -> 11.80 x 8.70 ortho units
    W, H = 11.80, 8.70
    setup_studio_lighting_and_camera(ortho_scale=W, res_x=1180, res_y=870, is_ortho=True)

    add_beveled_box("Trophi_Titanium", (0, 0, -0.30), (W - 0.16, H - 0.16, 0.30), mats["titanium"], bevel_width=0.18, segments=5)
    add_beveled_box("Trophi_Carbon", (0, 0, -0.14), (W - 0.38, H - 0.38, 0.24), mats["carbon"], bevel_width=0.14, segments=4)

    # Top Neural Violet Laser Pipe & Bottom Cyan Pipe
    add_beveled_box("Trophi_Top_Violet", (0, H/2 - 0.12, 0.06), (W - 1.0, 0.07, 0.10), mats["violet"], bevel_width=0.02)
    add_beveled_box("Trophi_Bot_Cyan", (0, -H/2 + 0.12, 0.06), (W - 1.0, 0.07, 0.10), mats["cyan"], bevel_width=0.02)

    # Graph Oscilloscope Recessed Bay (Qt gx=14, gy=75, gw=355, gh=118 out of 590x435)
    gx = ((14 + 355/2.0) - 295.0) * 0.02
    gy = (217.5 - (75 + 118/2.0)) * 0.02
    add_beveled_box("Trophi_Graph_Bezel", (gx, gy, 0.03), (355 * 0.02, 118 * 0.02, 0.16), mats["titanium"], bevel_width=0.05)
    add_beveled_box("Trophi_Graph_Well", (gx, gy, 0.08), (347 * 0.02, 110 * 0.02, 0.12), mats["glass"], bevel_width=0.03)

    # Right Active Corner Pod (Qt rx=377, rw=199, gy=75, gh=118)
    rx = ((377 + 199/2.0) - 295.0) * 0.02
    add_beveled_box("Trophi_Right_Pod", (rx, gy, 0.03), (199 * 0.02, 118 * 0.02, 0.16), mats["titanium"], bevel_width=0.05)
    add_beveled_box("Trophi_Right_Well", (rx, gy, 0.08), (191 * 0.02, 110 * 0.02, 0.12), mats["glass"], bevel_width=0.03)

    # Bottom All-Corners Matrix Bay (Qt x=14, y=201, w=562, h=222)
    ty = (217.5 - (201 + 222/2.0)) * 0.02
    add_beveled_box("Trophi_Table_Bezel", (0, ty, 0.02), (562 * 0.02, 222 * 0.02, 0.15), mats["titanium"], bevel_width=0.06)
    add_beveled_box("Trophi_Table_Glass", (0, ty, 0.07), (552 * 0.02, 212 * 0.02, 0.12), mats["glass"], bevel_width=0.04)

    out_path = os.path.join(OUT_DIR, "trophi_neural_chassis_3d.png")
    bpy.context.scene.render.filepath = out_path
    bpy.ops.render.render(write_still=True)
    print(f"[BLENDER 3D] Rendered {out_path}")


# ==============================================================================
# 5. RENDER 3D RADAR SCOPE & 3D FORMULA CARS (`radar_*.png`)
# ==============================================================================
def render_radar_3d_assets(mats):
    # 5A. 3D Radar Scope Dish (`radar_scope_3d.png`)
    clear_scene_objects()
    setup_studio_lighting_and_camera(ortho_scale=5.2, res_x=520, res_y=520, is_ortho=True)

    add_torus("Radar_Outer_Bezel", (0, 0, 0.08), 2.32, 0.14, mats["titanium"])
    add_torus("Radar_Cyan_Ring", (0, 0, 0.18), 2.36, 0.03, mats["cyan"])
    add_cylinder("Radar_Glass_Dish", (0, 0, -0.06), 2.26, 0.12, mats["glass"], vertices=96)
    add_torus("Radar_Mid_Ring", (0, 0, 0.04), 1.54, 0.018, mats["titanium"])
    add_torus("Radar_Inner_Ring", (0, 0, 0.04), 0.80, 0.018, mats["titanium"])

    out_scope = os.path.join(OUT_DIR, "radar_scope_3d.png")
    bpy.context.scene.render.filepath = out_scope
    bpy.ops.render.render(write_still=True)
    print(f"[BLENDER 3D] Rendered {out_scope}")

    # 5B & 5C. Top-Down 3D Formula Car (Player Cyan & Opponent Crimson)
    for fname, body_mat, accent_mat in [
        ("radar_3d_f4_player_car.png", mats["cyan_metal"], mats["cyan"]),
        ("radar_3d_f4_opponent_car.png", mats["red_metal"], mats["gold"]),
    ]:
        clear_scene_objects()
        setup_studio_lighting_and_camera(ortho_scale=4.2, res_x=256, res_y=256, is_ortho=True)

        # Nose & Monocoque Fuselage
        add_beveled_box("Monocoque", (0, 0.15, 0.15), (0.52, 2.65, 0.35), body_mat, bevel_width=0.12)
        # Sidepods
        add_beveled_box("Sidepod_L", (-0.42, -0.15, 0.10), (0.48, 1.35, 0.28), body_mat, bevel_width=0.10)
        add_beveled_box("Sidepod_R", ( 0.42, -0.15, 0.10), (0.48, 1.35, 0.28), body_mat, bevel_width=0.10)
        # Front Wing
        add_beveled_box("Front_Wing", (0, 1.55, 0.05), (1.72, 0.34, 0.10), mats["carbon"], bevel_width=0.04)
        add_beveled_box("Front_Flap", (0, 1.52, 0.11), (1.66, 0.14, 0.06), accent_mat, bevel_width=0.02)
        # Rear Wing
        add_beveled_box("Rear_Wing", (0, -1.52, 0.28), (1.36, 0.36, 0.14), mats["carbon"], bevel_width=0.04)
        add_beveled_box("Rear_Flap", (0, -1.48, 0.35), (1.30, 0.12, 0.08), body_mat, bevel_width=0.02)
        # 4 Slick Tires
        for tx, ty in [(-0.78, 0.98), (0.78, 0.98), (-0.78, -1.05), (0.78, -1.05)]:
            add_beveled_box("Tire", (tx, ty, 0.12), (0.36, 0.64, 0.34), mats["tire"], bevel_width=0.08)
        # Cockpit & Halo
        add_cylinder("Cockpit", (0, 0.05, 0.28), 0.22, 0.20, mats["alcantara"], vertices=24)
        add_torus("Halo_Ring", (0, 0.12, 0.36), 0.24, 0.04, mats["titanium"], scale=(0.85, 1.25, 1.0))

        out_car = os.path.join(OUT_DIR, fname)
        bpy.context.scene.render.filepath = out_car
        bpy.ops.render.render(write_still=True)
        print(f"[BLENDER 3D] Rendered {out_car}")


# ==============================================================================
# 6. RENDER UNIVERSAL 3D CARBON/TITANIUM CARD BEZEL & HERO BANNER
# ==============================================================================
def render_universal_card_and_hero(mats):
    # 6A. Universal 3D Carbon/Titanium Card (`card_carbon_bezel_3d.png`)
    clear_scene_objects()
    W, H = 8.0, 6.0
    setup_studio_lighting_and_camera(ortho_scale=W, res_x=800, res_y=600, is_ortho=True)

    add_beveled_box("Card_Titanium", (0, 0, -0.25), (W - 0.14, H - 0.14, 0.28), mats["titanium"], bevel_width=0.16, segments=5)
    add_beveled_box("Card_Carbon", (0, 0, -0.10), (W - 0.36, H - 0.36, 0.22), mats["carbon"], bevel_width=0.12, segments=4)
    add_beveled_box("Card_Top_Cyan", (0, H/2 - 0.11, 0.06), (W - 0.9, 0.06, 0.08), mats["cyan"], bevel_width=0.01)
    add_beveled_box("Card_Bot_Red", (0, -H/2 + 0.11, 0.06), (W - 0.9, 0.06, 0.08), mats["red"], bevel_width=0.01)

    for bx in (-W/2 + 0.28, W/2 - 0.28):
        for by in (-H/2 + 0.28, H/2 - 0.28):
            add_cylinder("Bolt", (bx, by, 0.05), 0.08, 0.10, mats["chrome"], vertices=6)

    out_card = os.path.join(OUT_DIR, "card_carbon_bezel_3d.png")
    bpy.context.scene.render.filepath = out_card
    bpy.ops.render.render(write_still=True)
    print(f"[BLENDER 3D] Rendered {out_card}")

    # 6B. Launcher Hero 3D Banner (`launcher_hero_banner_3d.png` - 1520x220)
    clear_scene_objects()
    BW, BH = 15.20, 2.20
    setup_studio_lighting_and_camera(ortho_scale=BW, res_x=1520, res_y=220, is_ortho=True)

    add_beveled_box("Hero_Shell", (0, 0, -0.30), (BW - 0.10, BH - 0.10, 0.28), mats["titanium"], bevel_width=0.14)
    add_beveled_box("Hero_Carbon", (0, 0, -0.14), (BW - 0.28, BH - 0.28, 0.22), mats["carbon"], bevel_width=0.10)
    add_beveled_box("Hero_Top_Laser", (0, BH/2 - 0.09, 0.05), (BW - 0.8, 0.06, 0.08), mats["red"], bevel_width=0.01)
    add_beveled_box("Hero_Bot_Laser", (0, -BH/2 + 0.09, 0.05), (BW - 0.8, 0.06, 0.08), mats["cyan"], bevel_width=0.01)

    # Decorative 3D Turbine & Speed Chevrons on right side of Hero Banner
    for i in range(5):
        cx = 3.2 + i * 0.55
        mat_c = mats["red"] if i % 2 == 0 else mats["cyan"]
        obj = add_beveled_box(f"Chevron_{i}", (cx, 0, 0.02), (0.18, 1.45, 0.12), mat_c, bevel_width=0.03)
        obj.rotation_euler = (0, 0, -0.42)

    out_hero = os.path.join(OUT_DIR, "launcher_hero_banner_3d.png")
    bpy.context.scene.render.filepath = out_hero
    bpy.ops.render.render(write_still=True)
    print(f"[BLENDER 3D] Rendered {out_hero}")


def main():
    mats = create_pbr_materials()
    render_halo_telemetry_chassis(mats)
    render_timing_tower_chassis(mats)
    render_trophi_neural_chassis(mats)
    render_radar_3d_assets(mats)
    render_universal_card_and_hero(mats)
    # Render F1 2026 Steering Wheel last so it stays in the saved .blend scene!
    render_f1_steering_wheel(mats)

    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
    print(f"[BLENDER 3D] Saved Blender project -> {BLEND_PATH}")


if __name__ == "__main__":
    main()
