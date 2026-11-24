"""Inventory icons of our conveyor pieces: feConveyor, feConveyorRamp, feConveyorDown and feConveyorFilter
(the straight belt with a blue filter frame). Same look as Art/feKinetic/render_icons.py (160x160 transparent,
orthographic, 3/4 view from the front right), which no longer renders these four.

Run after build_feConveyor.py in the same Blender session (do not save the .blend afterwards).
"""
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

OUT_DIR = r"E:\ModGameDev\ForgedInAshes\Mods\FerroEngrenagem\UIAtlases\ItemIconAtlas"
SIZE = 160
PIECES = {"feConveyor": 0.0, "feConveyorRamp": 1.6, "feConveyorDown": 3.2, "feConveyorStand": 4.8}
SHOW = {"feConveyor": {"FeBeltBed", "FeBeltSlats", "FeSpin_BeltRollerFront", "FeSpin_BeltRollerBack",
                       "FeRail_L", "FeRail_R", "FeBeltEnd"},
        "feConveyorRamp": None, "feConveyorDown": None, "feConveyorStand": {"FeStand_Straight"}}
DRIVE = ("FeBeltDrive", "FeSpin_BeltDrive")

scene = bpy.context.scene
for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scene.render.engine = engine
        break
    except TypeError:
        continue
scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.resolution_x = scene.render.resolution_y = SIZE * 2
scene.render.resolution_percentage = 100
try:
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.exposure = -0.2
except TypeError:
    pass
world = scene.world or bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
bg.inputs["Color"].default_value = (0.75, 0.78, 0.82, 1)
bg.inputs["Strength"].default_value = 0.55
cam = bpy.data.objects.get("feIconCam")
if not cam:
    cam = bpy.data.objects.new("feIconCam", bpy.data.cameras.new("feIconCam"))
    scene.collection.objects.link(cam)
cam.data.type = "ORTHO"
scene.camera = cam
sun = bpy.data.objects.get("feIconSun")
if not sun:
    sun = bpy.data.objects.new("feIconSun", bpy.data.lights.new("feIconSun", "SUN"))
    scene.collection.objects.link(sun)
sun.data.energy = 3.2
sun.rotation_euler = (math.radians(40), math.radians(15), math.radians(-30))
VIEW = Vector((1.0, -1.25, 0.95)).normalized()      # from the front right, above


def fit_and_render(keep, path, view=None):
    view = VIEW if view is None else view
    for o in bpy.data.objects:
        o.hide_render = o not in keep and o.type != "LIGHT"
    bpy.context.view_layer.update()
    rot = (-view).to_track_quat("-Z", "Y")
    right, up = rot @ Vector((1, 0, 0)), rot @ Vector((0, 1, 0))
    pts = [o.matrix_world @ Vector(c) for o in keep if o.type == "MESH" for c in o.bound_box]
    center = sum(pts, Vector()) / len(pts)
    xs = [(p - center).dot(right) for p in pts]
    ys = [(p - center).dot(up) for p in pts]
    mid = center + right * (max(xs) + min(xs)) / 2 + up * (max(ys) + min(ys)) / 2
    cam.data.ortho_scale = max(max(xs) - min(xs), max(ys) - min(ys)) * 1.08
    cam.location = mid + view * 20
    cam.rotation_euler = rot.to_euler()
    cam.data.clip_end = 100
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path, check_existing=False)
    img.scale(SIZE, SIZE)
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    print("icon", path)


def parts(name):
    want = SHOW[name]
    return [o for o in bpy.data.collections[name].objects
            if not o.name.startswith(DRIVE) and (want is None or o.name.split(".")[0] in want)]


for name in PIECES:
    # the up ramp rises toward its front: seen from behind so its belt shows, not its underside
    v = Vector((1.0, 1.25, 0.95)).normalized() if name == "feConveyorRamp" else None
    fit_and_render(parts(name), os.path.join(OUT_DIR, name + ".png"), v)

# the filter conveyor: our straight belt with a blue filter frame over it
blue = bpy.data.materials.get("feIco_Filter") or bpy.data.materials.new("feIco_Filter")
blue.use_nodes = True
blue.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.10, 0.35, 0.85, 1.0)
bm = bmesh.new()
for x, y, sx, sy in ((-0.24, 0, 0.04, 0.9), (0.24, 0, 0.04, 0.9), (0, -0.43, 0.52, 0.04), (0, 0.43, 0.52, 0.04)):
    r = bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.transform(bm, matrix=Matrix.Translation((x, y, 0.33)) @ Matrix.Diagonal((sx, sy, 0.04, 1)),
                        verts=r["verts"])
for x in (-0.24, 0.24):
    for y in (-0.43, 0.43):
        r = bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.transform(bm, matrix=Matrix.Translation((x, y, 0.27)) @ Matrix.Diagonal((0.03, 0.03, 0.12, 1)),
                            verts=r["verts"])
me = bpy.data.meshes.new("ico_filter")
bm.to_mesh(me)
bm.free()
me.materials.append(blue)
frame = bpy.data.objects.new("ico_filter", me)
scene.collection.objects.link(frame)
fit_and_render(parts("feConveyor") + [frame], os.path.join(OUT_DIR, "feConveyorFilter.png"))
bpy.data.objects.remove(frame, do_unlink=True)
