"""Splits feConveyor.blend (Harrison's build_feConveyor.py) into one source .blend per block for the HD texture
pass (F:\IA\texturizar.bat): Art/<block>/hd/<block>_src.blend with only that collection's objects, names kept
(Belt.cs / ConveyorStand.cs find the parts by name, ".001" suffixes included).

    blender -b Art/feConveyor/feConveyor.blend --python Art/feConveyor/split_for_hd.py
"""
import os

import bpy

ART = os.path.dirname(os.path.dirname(os.path.abspath(bpy.data.filepath)))
SRC = bpy.data.filepath
for name in ("feConveyor", "feConveyorRamp", "feConveyorDown", "feConveyorStand"):
    bpy.ops.wm.open_mainfile(filepath=SRC)
    keep = {o.name for o in bpy.data.collections[name].objects}
    for o in list(bpy.data.objects):
        if o.name not in keep:
            bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections):
        if c.name != name:
            bpy.data.collections.remove(c)
    d = os.path.join(ART, name, "hd")
    os.makedirs(d, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(d, name + "_src.blend"))
    print("[split]", name, len(keep), "objects")
