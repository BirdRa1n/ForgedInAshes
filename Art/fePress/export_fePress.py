"""Saves fePress.blend and exports fePress.fbx (fePress_* objects only).

FBX settings aim at Unity (Y up, -Z forward baked into the meshes). The exact
import result in the game's Unity 2022.3.62f2 project is NOT verified yet.
"""
import bpy

DIR = r"E:\ModGameDev\ForgedInAshes\Art\fePress"
objs = [o for o in bpy.data.objects if o.name.startswith("fePress_")]

bpy.ops.wm.save_as_mainfile(filepath=DIR + r"\fePress.blend")

for o in bpy.context.view_layer.objects:
    o.select_set(o in objs)
bpy.context.view_layer.objects.active = bpy.data.objects["fePress_Base"]
bpy.ops.export_scene.fbx(
    filepath=DIR + r"\fePress.fbx",
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
print("saved", bpy.data.filepath, "exported", [o.name for o in objs])
