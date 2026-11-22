"""Preview only: conveyor pieces hooked to the Coal Generator's ports.

Run in a background Blender on feConveyor.blend (it does not save):
  blender --background feConveyor.blend --python render_line_preview.py
Appends the generator from ../feCoalGenerator/feCoalGenerator.blend and places
conveyor collection instances so their port empties meet the generator's.
"""
import math
import os

import bpy
from mathutils import Vector

HERE = r"E:\ModGameDev\ForgedInAshes\Art\feConveyor"
GEN = os.path.join(os.path.dirname(HERE), "feCoalGenerator", "feCoalGenerator.blend")

for root in ("feConveyor_Frame", "feConveyorCorner_Frame"):
    bpy.data.objects[root].location = (0, 0, 0)
for name in ("feConveyor", "feConveyorCorner"):
    bpy.context.view_layer.layer_collection.children[name].exclude = True

with bpy.data.libraries.load(GEN) as (src, dst):
    dst.collections = ["feCoalGenerator"]
gen = dst.collections[0]
bpy.context.scene.collection.children.link(gen)


def place(col_name, loc, rot_deg):
    inst = bpy.data.objects.new(f"inst_{col_name}_{loc}", None)
    inst.instance_type = "COLLECTION"
    inst.instance_collection = bpy.data.collections[col_name]
    inst.location = loc
    inst.rotation_euler = (0, 0, math.radians(rot_deg))
    bpy.context.scene.collection.objects.link(inst)


# Feed line into the generator's charcoal input (-1, 0, 0.25), facing +X:
place("feConveyor", (-1.5, 0, 0), -90)
place("feConveyor", (-2.5, 0, 0), -90)
place("feConveyorCorner", (-3.5, 0, 0), 0)
place("feConveyor", (-3.5, -1, 0), 0)
# Output line from the generator's Carga output (0.5, -0.5, 0.25), going -Y:
place("feConveyor", (0.5, -1.0, 0), 180)
place("feConveyor", (0.5, -2.0, 0), 180)

scene = bpy.context.scene
cam = bpy.data.objects["fePreviewCam"]
cam.data.lens = 35
target = Vector((-1.4, -0.9, 0.4))
cam.location = (-3.6, -5.6, 3.6)
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
floor = bpy.data.objects.get("fePreviewFloor")
if floor:
    floor.scale = (3, 3, 1)
scene.render.filepath = os.path.join(HERE, "preview_line.png")
bpy.ops.render.render(write_still=True)
print("wrote", scene.render.filepath)
