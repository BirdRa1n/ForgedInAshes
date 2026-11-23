"""Saves Art/feKinetic/feKinetic.blend and exports one FBX per torque block into Art/<block>/<block>.fbx (only the
objects of that block's collection), with the same settings as Art/feCrank/export_feCrank.py (Unity: Y up,
-Z forward, transform baked). The FBX are picked up by Art/UnityProject/Assets/Editor/FeBuild.cs.
"""
import os

import bpy

ART = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if "__file__" in globals() else \
    r"F:\Github\FerroEngrenagem\Art"
NAMES = ["feTorqueCrank", "feShaft", "feSpeedBox", "feGearbox", "feSpinInverter", "feTorqueRegulator",
         "feClutch", "feTorqueGauge"]

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART, "feKinetic", "feKinetic.blend"))
exported = {}
for n in NAMES:
    col = bpy.data.collections[n]
    objs = list(col.objects)
    for o in bpy.context.view_layer.objects:
        o.select_set(o in objs)
    root = [o for o in objs if o.parent is None][0]
    bpy.context.view_layer.objects.active = root
    d = os.path.join(ART, n)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, n + ".fbx")
    bpy.ops.export_scene.fbx(
        filepath=path,
        use_selection=True,
        object_types={"MESH", "EMPTY"},
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_ALL",
        axis_forward="-Z",
        axis_up="Y",
        bake_space_transform=True,
        use_mesh_modifiers=True,
        mesh_smooth_type="FACE",
        add_leaf_bones=False,
        bake_anim=False,
    )
    exported[n] = [o.name for o in objs]
print(exported)
