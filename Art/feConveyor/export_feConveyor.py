"""Saves Art/feConveyor/feConveyor.blend and exports one FBX per piece built by build_feConveyor.py:
Art/feConveyor/feConveyor.fbx, Art/feConveyorRamp/feConveyorRamp.fbx, Art/feConveyorDown/feConveyorDown.fbx.

Each piece is moved back from its display offset for the export. Same FBX settings as every other model of the
mod (Unity: Y up, -Z forward, transform baked); Art/UnityProject/Assets/Editor/FeBuild.cs picks them up.
"""
import os

import bpy

ART = r"E:\ModGameDev\ForgedInAshes\Art"
PIECES = (("feConveyor", 0.0), ("feConveyorRamp", 1.6), ("feConveyorDown", 3.2), ("feConveyorStand", 4.8))

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART, "feConveyor", "feConveyor.blend"))
for name, dx in PIECES:
    objs = list(bpy.data.collections[name].objects)
    for o in objs:
        o.location.x -= dx
    bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects:
        o.select_set(o in objs)
    bpy.context.view_layer.objects.active = objs[0]
    d = os.path.join(ART, name)
    os.makedirs(d, exist_ok=True)
    bpy.ops.export_scene.fbx(
        filepath=os.path.join(d, name + ".fbx"),
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
    for o in objs:
        o.location.x += dx
    print("exported", name, sorted(o.name for o in objs))
bpy.context.view_layer.update()
