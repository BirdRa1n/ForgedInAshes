"""Inventory icons (user request 2026-11-24: "ta ficando dificil de identificar os itens").

Run inside Blender AFTER build_feKinetic.py, in the same namespace (it uses its helpers: box, cyl, ring, gear,
to_object, the material indices...). bg_icons.py in the scratchpad does:
    exec(build_feKinetic.py, ns); exec(render_icons.py, ns)

Writes 160x160 transparent PNGs to Mods/ForgedInAshes/UIAtlases/ItemIconAtlas/<name>.png:
  - every mod block with a model in feKinetic.blend (orthographic, 3/4 view from the front right);
  - every mod item, from small item models built here (molds show their cavity in glowing metal).
tools/apply_icons.py then points CustomIcon of each block/item at its own icon.
"""
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

REPO = r"F:\Github\ForgedInAshes"
OUT_DIR = os.path.join(REPO, "Mods", "ForgedInAshes", "UIAtlases", "ItemIconAtlas")
SIZE = 160
os.makedirs(OUT_DIR, exist_ok=True)

# block name -> collection in feKinetic.blend (the workstations' models are feM_*)
BLOCK_COLS = {n: n for n in MODELS if not n.startswith("feM_")}
BLOCK_COLS.update({
    "feFoundry": "feM_Foundry", "fePress": "feM_Press", "feLathe": "feM_Lathe", "feCharcoalKiln": "feM_Kiln",
    "feAmmoPress": "feM_Ammo", "feAssembler": "feM_Assembler", "feModBench": "feM_ModBench", "feLoom": "feM_Loom",
    "feRefinery": "feM_Refinery", "feLab": "feM_Lab", "feKitchen": "feM_Kitchen", "feElectronics": "feM_Electronics",
    "feMetalShop": "feM_MetalShop", "feSawmill": "feM_Sawmill", "feMixer": "feM_Mixer", "feGarage": "feM_Garage",
    "feRobotics": "feM_Robotics",
})

# our low belt renders its own icons (Art/feConveyor/render_icons.py), filter conveyor included
for _n in ("feConveyor", "feConveyorRamp", "feConveyorDown"):
    BLOCK_COLS.pop(_n, None)

# ---------------------------------------------------------------- extra materials (icons only)
EXTRA = {
    "feIco_Char":    ((0.035, 0.035, 0.04), 0.95, 0.0),
    "feIco_White":   ((0.92, 0.92, 0.88), 0.85, 0.0),
    "feIco_Earth":   ((0.36, 0.22, 0.11), 0.95, 0.0),
    "feIco_Mash":    ((0.30, 0.33, 0.08), 0.70, 0.0),
    "feIco_Cloth":   ((0.78, 0.74, 0.62), 0.90, 0.0),
    "feIco_Green":   ((0.16, 0.55, 0.12), 0.45, 0.1),
    "feIco_Copper":  ((0.78, 0.38, 0.16), 0.35, 1.0),
    "feIco_Paste":   ((0.24, 0.26, 0.30), 0.40, 0.0),
    "feIco_LightWood": ((0.62, 0.42, 0.22), 0.80, 0.0),
}
XI = {n: len(MATS) + i for i, n in enumerate(EXTRA)}
CHAR, WHITE, EARTH, MASH, CLOTH, GREEN, COPPER, PASTE, LWOOD = (XI[n] for n in EXTRA)
for name, (rgb, rough, metal) in EXTRA.items():
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*rgb, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal


def obj(bm, name):
    o = to_object(bm, name, bevel=0.004)
    for n in EXTRA:
        o.data.materials.append(bpy.data.materials[n])
    return o


def heap(bm, r, h, mat, loc=(0, 0, 0), lumps=6, seed=1):
    cyl(bm, r, h, (loc[0], loc[1], loc[2] + h / 2), "Z", mat, segs=24, r2=r * 0.18)
    for k in range(lumps):
        a = 2.3 * k + seed
        d = r * (0.55 + 0.35 * ((k * 37 + seed) % 7) / 7)
        box(bm, (r * 0.22,) * 3, (loc[0] + d * math.cos(a), loc[1] + d * math.sin(a), loc[2] + r * 0.08), mat,
            Matrix.Rotation(a, 4, "Z") @ Matrix.Rotation(0.6, 4, "X"))


# ---------------------------------------------------------------- item models
def it_plate():
    bm = bmesh.new()
    for k in range(3):
        box(bm, (0.9, 0.6, 0.05), (0.04 * k, -0.03 * k, 0.03 + 0.06 * k), STEEL, Matrix.Rotation(0.08 * k, 4, "Z"))
    return [obj(bm, "ico_plate")]


def it_shaft():
    bm = bmesh.new()
    cyl(bm, 0.07, 1.1, (0, 0, 0), "X", STEEL, segs=20)
    for x in (-0.5, 0.5):
        ring(bm, 0.09, 0.07, 0.05, (x, 0, 0), "X", IRON, segs=20)
    box(bm, (0.30, 0.03, 0.02), (0.15, 0, 0.07), IRON)
    o = obj(bm, "ico_shaft")
    o.rotation_euler = (0, 0, math.radians(-25))
    return [o]


def it_gear():
    bm = bmesh.new()
    gear(bm, 0.36, 0.12, 16, (0, 0, 0), "Y", BRASS, tooth=0.08)
    cyl(bm, 0.11, 0.18, (0, 0, 0), "Y", STEEL, segs=20)
    ring(bm, 0.25, 0.20, 0.13, (0, 0, 0), "Y", IRON, segs=28)
    o = obj(bm, "ico_gear")
    o.rotation_euler = (math.radians(-20), 0, math.radians(39))
    return [o]


def it_piston():
    bm = bmesh.new()
    cyl(bm, 0.17, 0.55, (-0.15, 0, 0), "X", STEEL, segs=24)
    for x in (-0.42, 0.12):
        cyl(bm, 0.21, 0.05, (x, 0, 0), "X", IRON, segs=24)
    cyl(bm, 0.045, 0.6, (0.42, 0, 0), "X", STEEL, segs=12)
    ring(bm, 0.09, 0.05, 0.08, (0.75, 0, 0), "Y", BRASS, segs=16)
    o = obj(bm, "ico_piston")
    o.rotation_euler = (0, 0, math.radians(-25))
    return [o]


def it_flywheel():
    bm = bmesh.new()
    ring(bm, 0.48, 0.38, 0.14, (0, 0, 0), "Y", IRON, segs=36)
    cyl(bm, 0.10, 0.20, (0, 0, 0), "Y", STEEL, segs=16)
    for k in range(6):
        a = k * math.pi / 3
        beam(bm, (0.08 * math.cos(a), 0, 0.08 * math.sin(a)), (0.4 * math.cos(a), 0, 0.4 * math.sin(a)), 0.06, 0.06, IRON)
    o = obj(bm, "ico_flywheel")
    o.rotation_euler = (math.radians(-20), 0, math.radians(39))
    return [o]


def it_battery():
    bm = bmesh.new()
    box(bm, (0.70, 0.42, 0.42), (0, 0, 0.21), PAINT)
    box(bm, (0.72, 0.44, 0.06), (0, 0, 0.44), IRON)
    box(bm, (0.72, 0.01, 0.12), (0, -0.215, 0.22), OUT)
    cyl(bm, 0.05, 0.08, (-0.22, 0, 0.50), "Z", RED, segs=12)
    cyl(bm, 0.05, 0.08, (0.22, 0, 0.50), "Z", IRON, segs=12)
    return [obj(bm, "ico_battery")]


def it_charcoal():
    bm = bmesh.new()
    for k in range(9):
        a = 1.7 * k
        d = 0.08 + 0.05 * (k % 4)
        box(bm, (0.22, 0.14, 0.12), (d * math.cos(a), d * math.sin(a), 0.06 + 0.07 * (k % 3)), CHAR,
            Matrix.Rotation(a, 4, "Z") @ Matrix.Rotation(0.4 * k, 4, "X"))
    return [obj(bm, "ico_charcoal")]


def it_brasswire():
    bm = bmesh.new()
    for y in (-0.22, 0.22):
        cyl(bm, 0.32, 0.04, (0, y, 0), "Y", LWOOD, segs=28)
    cyl(bm, 0.08, 0.48, (0, 0, 0), "Y", LWOOD, segs=16)
    for k in range(7):
        ring(bm, 0.26, 0.08, 0.05, (0, -0.17 + k * 0.057, 0), "Y", BRASS, segs=28)
    o = obj(bm, "ico_wire")
    o.rotation_euler = (0, 0, math.radians(-35))
    return [o]


def it_coil():
    bm = bmesh.new()
    box(bm, (0.75, 0.16, 0.16), (0, 0, 0), IRON)
    for k in range(9):
        ring(bm, 0.17, 0.08, 0.05, (-0.24 + k * 0.06, 0, 0), "X", COPPER, segs=20)
    beam(bm, (0.30, 0, 0.1), (0.42, 0, 0.28), 0.02, 0.02, COPPER)
    o = obj(bm, "ico_coil")
    o.rotation_euler = (0, 0, math.radians(-25))
    return [o]


def it_lubricant():
    bm = bmesh.new()
    cyl(bm, 0.22, 0.45, (0, 0, 0.225), "Z", STEEL, segs=24)
    cyl(bm, 0.225, 0.18, (0, 0, 0.22), "Z", IN, segs=24)
    cyl(bm, 0.22, 0.10, (0, 0, 0.50), "Z", STEEL, segs=24, r2=0.06)
    beam(bm, (0.0, 0, 0.55), (0.30, 0, 0.78), 0.035, 0.035, BRASS)
    return [obj(bm, "ico_lube")]


def it_plank():
    bm = bmesh.new()
    for k in range(3):
        box(bm, (1.0, 0.24, 0.06), (0, -0.26 + 0.26 * k, 0.03), LWOOD)
    box(bm, (1.0, 0.24, 0.06), (0.02, 0.0, 0.09), LWOOD, Matrix.Rotation(0.15, 4, "Z"))
    return [obj(bm, "ico_plank")]


def it_beam():
    bm = bmesh.new()
    box(bm, (1.1, 0.24, 0.24), (0, 0, 0.12), WOOD)
    box(bm, (1.1, 0.24, 0.24), (0.05, 0.27, 0.12), WOOD)
    o = obj(bm, "ico_beam")
    o.rotation_euler = (0, 0, math.radians(-20))
    return [o]


def it_clothroll():
    bm = bmesh.new()
    cyl(bm, 0.24, 0.85, (0, 0, 0), "X", CLOTH, segs=28)
    cyl(bm, 0.06, 0.88, (0, 0, 0), "X", WOOD, segs=12)
    box(bm, (0.80, 0.02, 0.35), (0, -0.24, -0.16), CLOTH, Matrix.Rotation(0.3, 4, "X"))
    o = obj(bm, "ico_cloth")
    o.rotation_euler = (0, 0, math.radians(-25))
    return [o]


def it_barrel():
    bm = bmesh.new()
    ring(bm, 0.06, 0.035, 1.1, (0, 0, 0), "X", STEEL, segs=20)
    ring(bm, 0.08, 0.035, 0.08, (0.53, 0, 0), "X", IRON, segs=20)
    box(bm, (0.22, 0.16, 0.16), (-0.6, 0, 0), IRON)
    o = obj(bm, "ico_barrel")
    o.rotation_euler = (0, 0, math.radians(-25))
    return [o]


def it_mechanism():
    bm = bmesh.new()
    box(bm, (0.60, 0.14, 0.24), (0, 0, 0.12), IRON)
    ring(bm, 0.12, 0.09, 0.05, (0.05, 0, -0.06), "Y", STEEL, segs=20)
    box(bm, (0.03, 0.04, 0.12), (0.05, 0, -0.04), STEEL, Matrix.Rotation(0.3, 4, "Y"))
    box(bm, (0.08, 0.06, 0.12), (-0.26, 0, 0.28), STEEL, Matrix.Rotation(-0.4, 4, "Y"))
    cyl(bm, 0.03, 0.24, (0.15, 0, 0.30), "X", BRASS, segs=10)
    o = obj(bm, "ico_mech")
    o.rotation_euler = (0, 0, math.radians(-25))
    return [o]


def it_stock():
    bm = bmesh.new()
    box(bm, (0.60, 0.12, 0.26), (0, 0, 0), WOOD, Matrix.Rotation(-0.15, 4, "Y"))
    box(bm, (0.18, 0.12, 0.40), (-0.36, 0, -0.08), WOOD, Matrix.Rotation(-0.15, 4, "Y"))
    box(bm, (0.04, 0.13, 0.42), (-0.46, 0, -0.08), CHAR, Matrix.Rotation(-0.15, 4, "Y"))
    o = obj(bm, "ico_stock")
    o.rotation_euler = (0, 0, math.radians(-25))
    return [o]


def mold(cavity):
    def build():
        bm = bmesh.new()
        box(bm, (0.9, 0.65, 0.22), (0, 0, 0.11), IRON)
        for x in (-0.5, 0.5):
            box(bm, (0.10, 0.18, 0.06), (x, 0, 0.16), STEEL)
        cavity(bm, 0.225)
        return [obj(bm, "ico_mold")]
    return build


def cav_casing(bm, z):
    for i in range(3):
        for j in range(2):
            cyl(bm, 0.075, 0.02, (-0.24 + 0.24 * i, -0.13 + 0.26 * j, z), "Z", MOLTEN, segs=16)


def cav_tip(bm, z):
    for i in range(3):
        for j in range(2):
            cyl(bm, 0.07, 0.10, (-0.24 + 0.24 * i, -0.13 + 0.26 * j, z + 0.04), "Z", MOLTEN, segs=16, r2=0.01)


def cav_ingot(bm, z):
    cyl(bm, 0.30, 0.03, (0, 0, z), "Z", MOLTEN, segs=4, r2=0.24)


def cav_plate(bm, z):
    box(bm, (0.68, 0.46, 0.02), (0, 0, z), MOLTEN)


def cav_pipe(bm, z):
    cyl(bm, 0.10, 0.75, (0, 0, z - 0.06), "X", MOLTEN, segs=20)


def cav_gear(bm, z):
    gear(bm, 0.20, 0.02, 12, (0, 0, z), "Z", MOLTEN, tooth=0.06)


def it_casing_raw():
    bm = bmesh.new()
    for k, (x, y) in enumerate(((0, 0), (0.18, 0.05), (-0.1, 0.17))):
        cyl(bm, 0.075, 0.34, (x, y, 0.17), "Z", COPPER, segs=16)
        ring(bm, 0.08, 0.06, 0.03, (x, y, 0.015), "Z", RUST, segs=16)
    cyl(bm, 0.075, 0.34, (0.05, -0.25, 0.075), "X", COPPER, segs=16)
    return [obj(bm, "ico_casing_raw")]


def it_heap(mat, extra=None):
    def build():
        bm = bmesh.new()
        heap(bm, 0.42, 0.30, mat)
        if extra:
            extra(bm)
        return [obj(bm, "ico_heap")]
    return build


def drops(bm):
    for x, y in ((0.18, -0.2), (-0.15, -0.25), (0.3, 0.05)):
        cyl(bm, 0.045, 0.09, (x, y, 0.30), "Z", WATERC, segs=12, r2=0.005)
        cyl(bm, 0.045, 0.02, (x, y, 0.25), "Z", WATERC, segs=12)


def specks(bm):
    for k in range(10):
        a = 1.9 * k
        d = 0.08 + 0.025 * k
        box(bm, (0.04,) * 3, (d * math.cos(a), d * math.sin(a), 0.29 - d * 0.55), WHITE)


def it_biomash():
    bm = bmesh.new()
    ring(bm, 0.34, 0.31, 0.42, (0, 0, 0.21), "Z", STEEL, segs=28)
    cyl(bm, 0.32, 0.02, (0, 0, 0.01), "Z", STEEL, segs=28)
    cyl(bm, 0.31, 0.30, (0, 0, 0.20), "Z", MASH, segs=28)
    for k in range(5):
        a = 1.3 * k
        box(bm, (0.08,) * 3, (0.15 * math.cos(a), 0.15 * math.sin(a), 0.36), EARTH, Matrix.Rotation(a, 4, "X"))
    beam(bm, (-0.33, 0, 0.40), (0.33, 0, 0.40), 0.02, 0.02, IRON)
    return [obj(bm, "ico_mash")]


def it_biofuel():
    bm = bmesh.new()
    box(bm, (0.55, 0.24, 0.70), (0, 0, 0.35), GREEN)
    for x in (-0.12, 0.12):
        box(bm, (0.04, 0.10, 0.12), (x, 0, 0.75), GREEN)
    box(bm, (0.30, 0.10, 0.04), (0, 0, 0.81), GREEN)
    cyl(bm, 0.06, 0.10, (0.22, 0, 0.75), "Z", IRON, segs=12)
    box(bm, (0.40, 0.01, 0.30), (0, -0.125, 0.35), GASC)
    box(bm, (0.12, 0.012, 0.12), (0, -0.13, 0.38), IN, Matrix.Rotation(math.pi / 4, 4, "Y"))
    o = obj(bm, "ico_biofuel")
    o.rotation_euler = (0, 0, math.radians(-15))
    return [o]


ITEMS = {
    "feResourceIronPlate": it_plate, "feResourceIronShaft": it_shaft, "feResourceGear": it_gear,
    "feSteamPiston": it_piston, "feFlywheel": it_flywheel, "feBatteryModule": it_battery,
    "feResourceCharcoal": it_charcoal, "feResourceBrassWire": it_brasswire, "feResourceCoil": it_coil,
    "feResourceLubricant": it_lubricant, "feResourcePlank": it_plank, "feResourceBeam": it_beam,
    "feResourceClothRoll": it_clothroll, "feGunBarrel": it_barrel, "feGunMechanism": it_mechanism,
    "feGunStock": it_stock,
    "feMoldCasing": mold(cav_casing), "feMoldBulletTip": mold(cav_tip), "feMoldIngot": mold(cav_ingot),
    "feMoldPlate": mold(cav_plate), "feMoldPipe": mold(cav_pipe), "feMoldGear": mold(cav_gear),
    "feCasingRaw": it_casing_raw, "feCoalDust": it_heap(CHAR), "feNitratePure": it_heap(WHITE),
    "feGunPowderWet": it_heap(PASTE, drops), "feNitreEarth": it_heap(EARTH, specks),
    "feBioMash": it_biomash, "feBiofuel": it_biofuel,
}

# ---------------------------------------------------------------- render setup
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


def fit_and_render(objs, path):
    for o in bpy.data.objects:
        if o.type in ("MESH", "CURVE", "EMPTY"):
            o.hide_render = True
    keep = set()
    for o in objs:
        keep.add(o)
        keep.update(o.children_recursive)
    for o in keep:
        o.hide_render = False
    bpy.context.view_layer.update()
    rot = (-VIEW).to_track_quat("-Z", "Y")
    right, up = rot @ Vector((1, 0, 0)), rot @ Vector((0, 1, 0))
    pts = [o.matrix_world @ Vector(c) for o in keep if o.type == "MESH" for c in o.bound_box]
    center = sum(pts, Vector()) / len(pts)
    xs = [(p - center).dot(right) for p in pts]
    ys = [(p - center).dot(up) for p in pts]
    mid = center + right * (max(xs) + min(xs)) / 2 + up * (max(ys) + min(ys)) / 2
    cam.data.ortho_scale = max(max(xs) - min(xs), max(ys) - min(ys)) * 1.08
    cam.location = mid + VIEW * 20
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


ICONS = []
for name, col_name in BLOCK_COLS.items():
    col = bpy.data.collections.get(col_name)
    if not col:
        continue
    roots = [o for o in col.objects if o.parent is None]
    p = os.path.join(OUT_DIR, name + ".png")
    fit_and_render(roots, p)
    ICONS.append(name)

# the filter conveyor: the conveyor with a blue filter frame on top
col = None   # feConveyorFilter: Art/feConveyor/render_icons.py
if col:
    bm = bmesh.new()
    for x in (-0.3, 0.3):
        box(bm, (0.05, 0.9, 0.05), (x, 0, 0.62), WATERC)
    for y in (-0.42, 0.42):
        box(bm, (0.65, 0.05, 0.05), (0, y, 0.62), WATERC)
    box(bm, (0.04, 0.85, 0.30), (0, 0, 0.47), WATERC)
    frame = obj(bm, "ico_filter")
    scene.collection.objects.link(frame)
    fit_and_render([o for o in col.objects if o.parent is None] + [frame], os.path.join(OUT_DIR, "feConveyorFilter.png"))
    ICONS.append("feConveyorFilter")
    bpy.data.objects.remove(frame, do_unlink=True)

icol = bpy.data.collections.get("feIcons") or bpy.data.collections.new("feIcons")
if icol.name not in scene.collection.children:
    scene.collection.children.link(icol)
for name, fn in ITEMS.items():
    objs = fn()
    for o in objs:
        icol.objects.link(o)
    fit_and_render(objs, os.path.join(OUT_DIR, name + ".png"))
    ICONS.append(name)
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
print("ICONS", len(ICONS), ICONS)
