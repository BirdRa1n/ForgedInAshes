"""Inventory icons (160 x 160, transparent) from the HD models: one per block, written to
Mods/FerroEngrenagem/UIAtlases/ItemIconAtlas/<block>.png (then run tools/apply_icons.py).

    blender -b --factory-startup --python Art/feHD/render_icons_hd.py [-- feCaster feFunnel ...]

Optional parts (shown by the mod's code in the game) are hidden so the icon shows the plain block.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "Mods", "FerroEngrenagem", "UIAtlases", "ItemIconAtlas")
# model (Art/<model>/hd) -> block names that use it
BLOCKS = {
    "feM_Foundry": ["feFoundry"], "feM_Lathe": ["feLathe"], "feM_Ammo": ["feAmmoPress"],
}
HIDE = ("FePour", "FeFx", "FeDuctSide", "FeDuctHatch", "FeDuctBoot", "FeDuctRamp", "FeDuctCapF", "FeCurve",
        "FeJunction", "FeBeltChute", "FeFunnelSpoutDuct", "FeLevelGas")
HIDE_EXACT = ("FeFunnelSpout",)


def render(model):
    path = os.path.join(REPO, "Art", model, "hd", model + "_HD.blend")
    if not os.path.exists(path):
        print("[icons] no HD model:", model)
        return
    bpy.ops.wm.open_mainfile(filepath=path)
    sc = bpy.context.scene
    for o in list(sc.objects):
        if o.type in ("CAMERA", "LIGHT"):
            bpy.data.objects.remove(o)
            continue
        if o.type == "MESH":
            o.hide_render = o.name.startswith(HIDE) or o.name in HIDE_EXACT
    meshes = [o for o in sc.objects if o.type == "MESH" and not o.hide_render]
    pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    centre, size = (lo + hi) / 2, (hi - lo).length
    cam = bpy.data.objects.new("IconCam", bpy.data.cameras.new("IconCam"))
    sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = size * 0.92
    d = Vector((0.75, -1.25, 0.85)).normalized()            # 3/4 view from the front right, a bit from above
    cam.location = centre + d * size * 3
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    sun = bpy.data.objects.new("IconSun", bpy.data.lights.new("IconSun", "SUN"))
    sun.data.energy = 4.0
    sun.rotation_euler = (math.radians(40), math.radians(10), math.radians(30))
    sc.collection.objects.link(sun)
    w = bpy.data.worlds.new("IconWorld")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.57, 0.6, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.2
    sc.world = w
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 32
    sc.cycles.use_denoising = True
    sc.render.film_transparent = True
    sc.render.resolution_x = sc.render.resolution_y = 160
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"
    for block in BLOCKS.get(model, [model]):
        sc.render.filepath = os.path.join(OUT, block + ".png")
        bpy.ops.render.render(write_still=True)
        print("[icons]", block, flush=True)


args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
models = args or sorted(d for d in os.listdir(os.path.join(REPO, "Art"))
                        if os.path.exists(os.path.join(REPO, "Art", d, "hd", d + "_HD.blend")))
for m in models:
    render(m)
