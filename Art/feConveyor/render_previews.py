"""Renders preview PNGs of the conveyor pieces built by build_feConveyor.py into Art/feConveyor.

preview_line.png: a small line laid out the way BeltShape (Belt.cs) shows the parts in game: a shaft-driven
straight (drive on its right), a straight, a left curve, a straight, a ramp up, a straight on top with its end
stop, and a 3-way junction beside it. preview_modes.png: the flat piece in each look side by side, plus both
ramps. Linked copies are made for the layout and removed afterwards; the model itself is not changed (do not
save the .blend after running this).
"""
import math
import os

import bpy
from mathutils import Matrix, Vector

OUT = r"E:\ModGameDev\ForgedInAshes\Art\feConveyor"
PIECES = {"feConveyor": 0.0, "feConveyorRamp": 1.6, "feConveyorDown": 3.2, "feConveyorStand": 4.8}

STRAIGHT = ["FeBeltBed", "FeBeltSlats", "FeSpin_BeltRollerFront", "FeSpin_BeltRollerBack"]
RAILS = ["FeRail_L", "FeRail_R"]


def base_name(n):
    return n.split(".")[0]


def place(col_name, parts, at, rot_deg=0.0, layout=None):
    """Linked copies of the named parts of a piece, moved to `at` and turned about Z."""
    dx = PIECES[col_name]
    m = Matrix.Translation(at) @ Matrix.Rotation(math.radians(rot_deg), 4, "Z") @ Matrix.Translation((-dx, 0, 0))
    for ob in bpy.data.collections[col_name].objects:
        if parts is not None and base_name(ob.name) not in parts:
            continue
        c = ob.copy()
        c.matrix_world = m @ ob.matrix_world
        layout.objects.link(c)


def setup_scene():
    scene = bpy.context.scene
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    scene.render.resolution_x, scene.render.resolution_y = 1200, 800
    scene.render.image_settings.file_format = "PNG"
    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.42, 0.44, 0.47, 1)
    bg.inputs["Strength"].default_value = 0.9
    for name in ("Camera", "Light"):
        ob = bpy.data.objects.get(name)
        if ob:
            ob.hide_render = True
    cam = bpy.data.objects.get("fePreviewCam")
    if not cam:
        cam = bpy.data.objects.new("fePreviewCam", bpy.data.cameras.new("fePreviewCam"))
        scene.collection.objects.link(cam)
    cam.data.lens = 35
    scene.camera = cam
    sun = bpy.data.objects.get("fePreviewSun")
    if not sun:
        sun = bpy.data.objects.new("fePreviewSun", bpy.data.lights.new("fePreviewSun", "SUN"))
        scene.collection.objects.link(sun)
    sun.data.energy = 3.5
    sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(-35))
    floor = bpy.data.objects.get("fePreviewFloor")
    if not floor:
        me = bpy.data.meshes.new("fePreviewFloor")
        me.from_pydata([(-20, -20, -0.001), (20, -20, -0.001), (20, 20, -0.001), (-20, 20, -0.001)], [],
                       [(0, 1, 2, 3)])
        floor = bpy.data.objects.new("fePreviewFloor", me)
        scene.collection.objects.link(floor)
        m = bpy.data.materials.new("fePreviewFloor")
        m.use_nodes = True
        m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.25, 0.25, 0.24, 1)
        me.materials.append(m)
    return scene, cam


def shoot(scene, cam, name, pos, target):
    cam.location = pos
    cam.rotation_euler = (Vector(target) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("wrote", scene.render.filepath)


def render(scene, cam, name, build, pos, target):
    for cname in PIECES:
        bpy.data.collections[cname].hide_render = True
    layout = bpy.data.collections.new("fePreviewLayout")
    scene.collection.children.link(layout)
    build(layout)
    shoot(scene, cam, name, pos, target)
    for ob in list(layout.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.collections.remove(layout)


def line(layout):
    # blocks are 1 m; "at" is the block's floor centre. Travel of an unturned piece = -Y.
    place("feConveyor", STRAIGHT + RAILS + ["FeBeltDrive_R", "FeSpin_BeltDrive_R"], (0, 0, 0), layout=layout)
    shaft = bpy.data.meshes.get("fePreviewShaft")
    if shaft is None:
        import bmesh
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.08, radius2=0.08, depth=1.0)
        bm.to_mesh(shaft := bpy.data.meshes.new("fePreviewShaft"))
        bm.free()
        shaft.materials.append(bpy.data.materials["feConveyor_Steel"])
    s = bpy.data.objects.new("fePreviewShaftObj", shaft)
    s.location = (-1.0, 0, 0.5)
    s.rotation_euler = (0, math.radians(90), 0)
    layout.objects.link(s)
    place("feConveyor", STRAIGHT + RAILS, (0, -1, 0), layout=layout)
    place("feConveyor", ["FeCurveSet_L", "FeCurveSlats_L"], (0, -2, 0), layout=layout)
    place("feConveyor", STRAIGHT + RAILS, (1, -2, 0), 90, layout=layout)
    place("feConveyorRamp", ["feConveyorRamp_Base", "FeBeltSlats", "FeSpin_BeltRollerFront",
                             "FeSpin_BeltRollerBack"], (2, -2, 0), 90, layout=layout)
    place("feConveyor", STRAIGHT + RAILS + ["FeBeltEnd"], (3, -2, 1), 90, layout=layout)
    # a junction splitting to the front and both sides, with belts on its three outputs
    place("feConveyor", STRAIGHT + RAILS, (-2, 0, 0), layout=layout)
    place("feConveyor", ["FeJunction", "FeJunctionPosts"], (-2, -1, 0), layout=layout)
    place("feConveyor", STRAIGHT + RAILS + ["FeBeltEnd"], (-2, -2, 0), layout=layout)
    place("feConveyor", STRAIGHT + RAILS + ["FeBeltEnd"], (-1, -1, 0), 90, layout=layout)
    place("feConveyor", STRAIGHT + RAILS + ["FeBeltEnd"], (-3, -1, 0), -90, layout=layout)


def modes(layout):
    place("feConveyor", STRAIGHT + RAILS + ["FeBeltEnd", "FeBeltDrive_L", "FeSpin_BeltDrive_L"], (0, 0, 0),
          layout=layout)
    place("feConveyor", ["FeCurveSet_L", "FeCurveSlats_L"], (1.4, 0, 0), layout=layout)
    place("feConveyor", ["FeCurveSet_R", "FeCurveSlats_R"], (2.8, 0, 0), layout=layout)
    place("feConveyor", ["FeJunction", "FeJunctionPosts", "FeJunctionWedge", "FeBeltEnd"], (4.2, 0, 0),
          layout=layout)
    place("feConveyorRamp", None, (5.8, 0, 0), layout=layout)
    place("feConveyorDown", None, (7.4, 0, 0), layout=layout)


def stands(layout):
    """A raised line on Conveyor Stands (straight, curve, straight, junction) and two belts side by side."""
    def stand(at, rot, part):
        place("feConveyorStand", [part], at, rot, layout=layout)
    place("feConveyor", STRAIGHT + RAILS, (0, 0, 1), layout=layout)
    stand((0, 0, 0), 0, "FeStand_Straight")
    place("feConveyor", ["FeCurveSet_L", "FeCurveSlats_L"], (0, -1, 1), layout=layout)
    stand((0, -1, 0), 0, "FeStand_Curve_L")
    place("feConveyor", STRAIGHT + ["FeRail_L", "FeRail_R", "FeBeltEnd"], (1, -1, 1), 90, layout=layout)
    stand((1, -1, 0), 90, "FeStand_Straight")
    for x in (-2.0, -3.0):                       # side by side, same way: one wide belt
        side = ["FeBeltFill_L", "FeBeltFillSlats_L", "FeRail_R"] if x == -3.0 else ["FeBeltFill_R", "FeBeltFillSlats_R", "FeRail_L"]
        for y in (0, -1):
            place("feConveyor", STRAIGHT + side + (["FeBeltEnd"] if y == -1 else []), (x, y, 0), layout=layout)


scene, cam = setup_scene()
render(scene, cam, "preview_line", line, (-3.2, -6.6, 4.2), (0.2, -1.3, 0.3))
render(scene, cam, "preview_modes", modes, (3.7, -9.5, 4.2), (3.7, 0, 0.4))
render(scene, cam, "preview_front", lambda l: place(
    "feConveyor", STRAIGHT + RAILS + ["FeBeltEnd", "FeBeltDrive_L", "FeSpin_BeltDrive_L"], (0, 0, 0), layout=l),
    (1.5, -1.6, 1.1), (0, 0, 0.2))
render(scene, cam, "preview_stands", stands, (-3.0, -5.2, 3.6), (-0.8, -0.6, 0.6))
for cname in PIECES:
    bpy.data.collections[cname].hide_render = False
