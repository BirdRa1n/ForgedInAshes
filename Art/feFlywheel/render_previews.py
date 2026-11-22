"""Renders preview PNGs of the flywheel item into this folder.

The floor is placed just under the wheel (radius ~0.21 m) so the item reads as
standing on its rim; the model itself is not moved.
"""
import math
import os

import bpy
from mathutils import Vector

OUT = r"E:\ModGameDev\ForgedInAshes\Art\feFlywheel"
FLOOR_Z = -0.218
TARGET = Vector((0, 0, 0))
VIEWS = {
    "preview_front": (-0.55, -0.85, 0.30),
    "preview_side": (0.95, -0.25, 0.12),
}

scene = bpy.context.scene
for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scene.render.engine = engine
        break
    except TypeError:
        continue
scene.render.resolution_x = scene.render.resolution_y = 900
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
    bpy.ops.mesh.primitive_plane_add(size=10)
    floor = bpy.context.active_object
    floor.name = "fePreviewFloor"
    m = bpy.data.materials.get("fePreviewFloor") or bpy.data.materials.new("fePreviewFloor")
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.25, 0.25, 0.24, 1)
    floor.data.materials.append(m)
floor.location.z = FLOOR_Z

for name, pos in VIEWS.items():
    cam.location = pos
    cam.rotation_euler = (TARGET - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("wrote", scene.render.filepath)
floor.location.z = 0.0
