"""Exports the mod's HD models (Art/<model>/hd/<model>_HD.blend) as small GLB files for the tutorial site.

    blender -b --factory-startup --python tools/blender_export_glb.py -- <out_dir> [model ...]

Textures are scaled down to SIZE px and written as JPEG inside the GLB (a model is ~0.3-0.8 MB). Optional parts the
game shows only in some states (pour streams, particle empties, duct joints...) are left out, like the icons do.
Only the mod's own models are exported (no game assets).
"""
import os
import sys

import bpy

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIZE = 512
HIDE = ("fePreview", "FePour", "FeFx", "FeDuctSide", "FeDuctHatch", "FeDuctBoot", "FeDuctRamp", "FeDuctCapF", "FeCurve",
        "FeJunction", "FeMerge", "FeBeltChute", "FeFunnelSpoutDuct", "FeLevelGas", "FeReach", "FeSplit", "FeFill")
HIDE_EXACT = ("FeFunnelSpout",)

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if not args:
    raise SystemExit("pass the output dir after --")
out_dir = os.path.abspath(args[0])
os.makedirs(out_dir, exist_ok=True)
art = os.path.join(REPO, "Art")
models = args[1:] or sorted(d for d in os.listdir(art) if os.path.exists(os.path.join(art, d, "hd", d + "_HD.blend")))

ok = 0
for m in models:
    path = os.path.join(art, m, "hd", m + "_HD.blend")
    if not os.path.exists(path):
        print("[glb] no HD model:", m, flush=True)
        continue
    bpy.ops.wm.open_mainfile(filepath=path)
    sc = bpy.context.scene
    keep = []
    for o in list(sc.objects):
        if o.type in ("CAMERA", "LIGHT"):
            bpy.data.objects.remove(o)
            continue
        hidden = o.name.startswith(HIDE) or o.name in HIDE_EXACT
        if o.type == "MESH" and not hidden:
            keep.append(o)
        if o.type == "EMPTY":
            keep.append(o)
    for img in bpy.data.images:
        try:
            if img.size[0] > SIZE or img.size[1] > SIZE:
                img.scale(min(SIZE, img.size[0]), min(SIZE, img.size[1]))
        except Exception as e:
            print("[glb] image", img.name, e, flush=True)
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    for o in keep:
        try:
            o.hide_set(False)
            o.select_set(True)
        except Exception:
            pass
    out = os.path.join(out_dir, m + ".glb")
    try:
        bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", use_selection=True, export_apply=True,
                                  export_image_format="JPEG", export_jpeg_quality=80, export_yup=True,
                                  export_animations=False, export_cameras=False, export_lights=False)
        ok += 1
        print("[glb]", m, round(os.path.getsize(out) / 1024), "KB", flush=True)
    except Exception as e:
        print("[glb] FAILED", m, e, flush=True)
print("[glb] done", ok, "of", len(models), flush=True)
