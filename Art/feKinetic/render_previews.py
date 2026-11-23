"""Renders preview PNGs of the torque network models (build_feKinetic.py) into each block's Art folder and a
line-up of all of them into Art/feKinetic/preview_lineup.png. Moves the model roots temporarily (restored after).
"""
import math
import os

import bpy
from mathutils import Vector

ART = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if "__file__" in globals() else \
    r"F:\Github\FerroEngrenagem\Art"
NAMES = ["feTorqueCrank", "feShaft", "feSpeedBox", "feGearbox", "feSpinInverter", "feTorqueRegulator"]

scene = bpy.context.scene
for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scene.render.engine = engine
        break
    except TypeError:
        continue
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
cam.data.lens = 50
scene.camera = cam
sun = bpy.data.objects.get("fePreviewSun")
if not sun:
    sun = bpy.data.objects.new("fePreviewSun", bpy.data.lights.new("fePreviewSun", "SUN"))
    scene.collection.objects.link(sun)
sun.data.energy = 3.5
sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(-35))
floor = bpy.data.objects.get("fePreviewFloor")
if not floor:
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, -0.001))
    floor = bpy.context.active_object
    floor.name = "fePreviewFloor"
    mat = bpy.data.materials.get("fePreviewFloorMat") or bpy.data.materials.new("fePreviewFloorMat")
    mat.diffuse_color = (0.25, 0.25, 0.25, 1)
    floor.data.materials.append(mat)


def roots():
    out = {}
    for n in NAMES:
        col = bpy.data.collections.get(n)
        if col:
            out[n] = [o for o in col.objects if o.parent is None][0]
    return out


def look(target, eye):
    cam.location = eye
    cam.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()


def render(path):
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


R = roots()
saved = {n: r.location.copy() for n, r in R.items()}
written = []
# each model alone (others hidden), two views
for n, r in R.items():
    for m, rr in R.items():
        for o in bpy.data.collections[m].objects:
            o.hide_render = m != n
    scene.render.resolution_x = scene.render.resolution_y = 700
    d = os.path.join(ART, n)
    os.makedirs(d, exist_ok=True)
    look((0, 0, 0.45), (1.7, -2.1, 1.35))
    render(os.path.join(d, "preview_front.png"))
    look((0, 0, 0.45), (-1.9, 1.9, 1.25))
    render(os.path.join(d, "preview_back.png"))
    written += [os.path.join(d, "preview_front.png"), os.path.join(d, "preview_back.png")]
# line-up
for m in R:
    for o in bpy.data.collections[m].objects:
        o.hide_render = False
for i, (n, r) in enumerate(R.items()):
    r.location = saved[n] + Vector((i * 1.4 - 3.5, 0, 0))
scene.render.resolution_x, scene.render.resolution_y = 1600, 600
cam.data.lens = 26
look((0, 0, 0.45), (0.0, -7.0, 2.6))
p = os.path.join(ART, "feKinetic", "preview_lineup.png")
render(p)
written.append(p)
for n, r in R.items():
    r.location = saved[n]
print(written)
