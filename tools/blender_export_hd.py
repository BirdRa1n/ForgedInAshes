"""Re-exports Art/<model>/hd/<model>_HD.fbx from the textured <model>_HD.blend, after it was edited by hand in Blender.

Same FBX settings as F:\\IA\\fe_blender\\texturizar_pbr.py (Unity: Y up, -Z forward, transform baked). Only meshes
and empties are exported (cameras / lights of the scene are left out), like the texturizer does.

    blender -b <model>_HD.blend --python tools/blender_export_hd.py -- <output.fbx>
(tools/fe.ps1 calls it.)
"""
import sys

import bpy

out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else None
if not out:
    raise SystemExit("pass the output .fbx after --")
objs = [o for o in bpy.context.scene.objects if o.type in ("MESH", "EMPTY")]
if not objs:
    raise SystemExit("no meshes in " + bpy.data.filepath)
if bpy.context.object and bpy.context.object.mode != "OBJECT":
    bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.object.select_all(action="DESELECT")
for o in objs:
    o.hide_set(False)
    o.select_set(True)
bpy.context.view_layer.objects.active = objs[0]
bpy.ops.export_scene.fbx(
    filepath=out, use_selection=True, object_types={"MESH", "EMPTY"},
    apply_unit_scale=True, apply_scale_options="FBX_SCALE_ALL",
    axis_forward="-Z", axis_up="Y", bake_space_transform=True,
    use_mesh_modifiers=True, mesh_smooth_type="FACE", use_tspace=True,
    add_leaf_bones=False, bake_anim=False, path_mode="STRIP",
)
print("[fe] exported", len(objs), "objects ->", out, flush=True)
