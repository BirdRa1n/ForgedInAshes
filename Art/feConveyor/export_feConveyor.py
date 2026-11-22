"""Saves feConveyor.blend and exports feConveyor.fbx and feConveyorCorner.fbx.

Each FBX holds one piece with its root (<P>_Frame) at the origin; the corner is
moved back from its display offset only for the export. FBX settings aim at Unity
(Y up, -Z forward baked into the meshes); the import result is NOT verified yet.
"""
import bpy

DIR = r"E:\ModGameDev\ForgedInAshes\Art\feConveyor"
bpy.ops.wm.save_as_mainfile(filepath=DIR + r"\feConveyor.blend")

for prefix in ("feConveyor", "feConveyorCorner"):
    root = bpy.data.objects[prefix + "_Frame"]
    saved = root.location.copy()
    root.location = (0, 0, 0)
    bpy.context.view_layer.update()
    objs = [o for o in bpy.data.objects if o.name.startswith(prefix + "_")]
    for o in bpy.context.view_layer.objects:
        o.select_set(o in objs)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.fbx(
        filepath=f"{DIR}\\{prefix}.fbx",
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
    root.location = saved
    print("exported", prefix, sorted(o.name for o in objs))
bpy.context.view_layer.update()
