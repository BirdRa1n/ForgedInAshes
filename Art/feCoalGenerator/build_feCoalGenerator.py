"""Builds the Coal Generator (E03, block feCoalGenerator) in the open Blender scene.

Run inside Blender (Scripting tab, or through the Blender MCP server).
Units: 1 Blender unit = 1 m = 1 game block. Footprint 2 (X) x 1 (Y) x 2 (Z) blocks,
origin at the floor center of the footprint. The front faces -Y.

Layout (front view, left to right): iron firebox with door and chimney, finned
heat exchanger feeding a hot-air engine, crankshaft with rear flywheel and front
gear, pinion driving the dynamo (with charge dial), coal crate.

Objects:
  feCoalGen_Base         static: skid, deck, firebox, chimney, exchanger, engine,
                         pedestals, dynamo body, dial, coal crate
  feCoalGen_Crank        crankshaft + flywheel + big gear (16 teeth); spins on local Y
  feCoalGen_DynamoRotor  dynamo shaft + pinion (8 teeth); spins on local Y, 2x faster,
                         opposite direction
Both rotating parts are children of feCoalGen_Base.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

CRANK = Vector((0.12, 0.0, 0.95))       # crankshaft axis point (axis along Y)
GEAR_BIG_R, GEAR_SMALL_R = 0.20, 0.10   # pitch radii, ratio 2:1
DYNAMO = Vector((CRANK.x + GEAR_BIG_R + GEAR_SMALL_R, 0.0, CRANK.z))
GEAR_Y = -0.36                           # gears' plane (front)
FLY_Y, FLY_R = 0.30, 0.44                # flywheel plane and radius

# ---------------------------------------------------------------- materials
MATS = {
    "feCoalGen_Iron":   ((0.15, 0.15, 0.16), 0.55, 0.85, 0.0),
    "feCoalGen_Rust":   ((0.30, 0.13, 0.06), 0.80, 0.35, 0.0),
    "feCoalGen_Copper": ((0.72, 0.36, 0.20), 0.35, 1.00, 0.0),
    "feCoalGen_Soot":   ((0.04, 0.04, 0.04), 0.90, 0.20, 0.0),
    "feCoalGen_Dial":   ((0.80, 0.74, 0.58), 0.60, 0.00, 0.0),
    "feCoalGen_Glow":   ((1.00, 0.35, 0.05), 0.50, 0.00, 6.0),
    "feCoalGen_Wood":   ((0.28, 0.17, 0.09), 0.85, 0.00, 0.0),
}
MI = {name: i for i, name in enumerate(MATS)}
IRON, RUST, COPPER, SOOT, DIAL, GLOW, WOOD = (MI[n] for n in MATS)


def make_materials():
    for name, (rgb, rough, metal, emit) in MATS.items():
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = m.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metal
        if emit:
            bsdf.inputs["Emission Color"].default_value = (*rgb, 1.0)
            bsdf.inputs["Emission Strength"].default_value = emit
        m.diffuse_color = (*rgb, 1.0)


# ---------------------------------------------------------------- bmesh helpers
AXIS = {
    "Z": Matrix.Identity(4),
    "Y": Matrix.Rotation(math.pi / 2, 4, "X"),
    "X": Matrix.Rotation(math.pi / 2, 4, "Y"),
}


def _finish(bm, n_faces, mat, matrix, verts):
    # Material goes on the faces of the new verts: bm.faces order is not creation order.
    bmesh.ops.transform(bm, matrix=matrix, verts=verts)
    for f in {f for v in verts for f in v.link_faces}:
        f.material_index = mat


def box(bm, size, loc, mat, rot=Matrix.Identity(4)):
    n = len(bm.faces)
    r = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)
    m = Matrix.Translation(loc) @ rot @ Matrix.Diagonal((*size, 1.0))
    _finish(bm, n, mat, m, r["verts"])


def beam(bm, a, b, w, t, mat):
    a, b = Vector(a), Vector(b)
    d = b - a
    rot = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    box(bm, (w, t, d.length), (a + b) / 2, mat, rot)


def cyl(bm, r, depth, loc, axis, mat, segs=16, r2=None):
    n = len(bm.faces)
    res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                                radius1=r, radius2=r if r2 is None else r2,
                                depth=depth, calc_uvs=True)
    _finish(bm, n, mat, Matrix.Translation(loc) @ AXIS[axis], res["verts"])


def ring(bm, ro, ri, depth, loc, axis, mat, segs=24):
    n = len(bm.faces)
    loops = []
    for rad, z in ((ro, -depth / 2), (ro, depth / 2), (ri, depth / 2), (ri, -depth / 2)):
        loops.append([bm.verts.new((rad * math.cos(2 * math.pi * i / segs),
                                    rad * math.sin(2 * math.pi * i / segs), z))
                      for i in range(segs)])
    for k in range(4):
        la, lb = loops[k], loops[(k + 1) % 4]
        for i in range(segs):
            j = (i + 1) % segs
            bm.faces.new((la[i], la[j], lb[j], lb[i]))
    _finish(bm, n, mat, Matrix.Translation(loc) @ AXIS[axis], [v for lp in loops for v in lp])


def gear(bm, pitch_r, teeth, width, y, mat, phase=0.0, hub_r=None):
    """Spur gear in the XZ plane at local (0, y, 0), axis along Y."""
    tooth_h = 0.03   # same on every gear so meshing gears touch exactly
    root = pitch_r - tooth_h / 2
    cyl(bm, root, width, (0, y, 0), "Y", mat, segs=teeth * 2)
    tw = 2 * math.pi * pitch_r / teeth * 0.5
    for k in range(teeth):
        a = phase + 2 * math.pi * k / teeth
        m = Matrix.Rotation(a, 4, "Y") @ Matrix.Translation((root + tooth_h / 2, y, 0))
        n = len(bm.faces)
        r = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)
        _finish(bm, n, mat, m @ Matrix.Diagonal((tooth_h, width, tw, 1.0)), r["verts"])
    cyl(bm, hub_r or pitch_r * 0.3, width * 1.6, (0, y, 0), "Y", mat, segs=12)


def to_object(bm, name, location=(0, 0, 0), bevel=0.0):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mname in MATS:
        me.materials.append(bpy.data.materials[mname])
    for p in me.polygons:
        p.use_smooth = True
    try:
        me.set_sharp_from_angle(angle=math.radians(35))
    except (AttributeError, TypeError):
        pass
    ob = bpy.data.objects.new(name, me)
    ob.location = location
    if bevel:
        mod = ob.modifiers.new("Bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 1
        mod.limit_method = "ANGLE"
    return ob


# ---------------------------------------------------------------- parts
def build_base():
    bm = bmesh.new()
    # Skid rails and deck plate with rivets.
    for y in (-0.38, 0.38):
        box(bm, (1.98, 0.10, 0.06), (0, y, 0.03), IRON)
    box(bm, (1.96, 0.92, 0.04), (0, 0, 0.08), RUST)
    for y in (-0.43, 0.43):
        for i in range(9):
            cyl(bm, 0.012, 0.012, (-0.88 + i * 0.22, y, 0.103), "Z", IRON, segs=6)

    # Firebox.
    fx0, fx1 = -0.96, -0.30
    fcx = (fx0 + fx1) / 2
    box(bm, (fx1 - fx0, 0.80, 0.70), (fcx, -0.02, 0.45), IRON)
    for z in (0.16, 0.74):
        box(bm, (fx1 - fx0 + 0.02, 0.82, 0.04), (fcx, -0.02, z), RUST)
    for x in (fx0 + 0.02, fx1 - 0.02):
        for z in (0.25, 0.45, 0.65):
            cyl(bm, 0.012, 0.012, (x, -0.427, z), "Y", IRON, segs=6)
    # Door with glowing slits, hinges and handle.
    box(bm, (0.36, 0.025, 0.28), (fcx, -0.433, 0.47), SOOT)
    for z in (0.41, 0.46, 0.51):
        box(bm, (0.24, 0.01, 0.014), (fcx, -0.447, z), GLOW)
    for z in (0.37, 0.57):
        cyl(bm, 0.016, 0.05, (fcx - 0.19, -0.44, z), "Z", IRON, segs=8)
    box(bm, (0.08, 0.02, 0.02), (fcx + 0.13, -0.46, 0.47), IRON)
    # Ash drawer.
    box(bm, (0.40, 0.02, 0.09), (fcx, -0.433, 0.23), SOOT)
    box(bm, (0.10, 0.02, 0.016), (fcx, -0.448, 0.23), IRON)

    # Chimney (rear-left) with bands and cap.
    chx, chy = -0.80, 0.20
    cyl(bm, 0.085, 1.10, (chx, chy, 0.80 + 0.55), "Z", IRON, segs=14)
    for z in (0.95, 1.35, 1.75):
        cyl(bm, 0.095, 0.03, (chx, chy, z), "Z", RUST, segs=14)
    cyl(bm, 0.15, 0.08, (chx, chy, 1.92), "Z", SOOT, segs=14, r2=0.05)
    for s in (-1, 1):
        box(bm, (0.012, 0.012, 0.06), (chx + s * 0.10, chy, 1.89), IRON)

    # Finned heat exchanger on top of the firebox, feeding the engine cylinder.
    ex_y = -0.06
    box(bm, (0.08, 0.30, 0.08), (fx0 + 0.15, ex_y, 0.82), IRON)   # saddles
    box(bm, (0.08, 0.30, 0.08), (fx1 - 0.10, ex_y, 0.82), IRON)
    cyl(bm, 0.12, 0.66, ((fx0 + 0.06 + fx1 + 0.10) / 2, ex_y, CRANK.z), "X", IRON, segs=16)
    for i in range(8):
        ring(bm, 0.175, 0.12, 0.014, (fx0 + 0.14 + i * 0.075, ex_y, CRANK.z), "X", RUST, segs=16)
    # Engine cylinder and crank housing.
    cyl(bm, 0.115, 0.26, (-0.15, ex_y, CRANK.z), "X", IRON, segs=16)
    for x in (-0.28, -0.02):
        cyl(bm, 0.135, 0.025, (x, ex_y, CRANK.z), "X", RUST, segs=16)
    box(bm, (0.26, 0.30, 0.32), (CRANK.x, -0.04, CRANK.z), IRON)
    box(bm, (0.20, 0.26, CRANK.z - 0.16 - 0.10), (CRANK.x, -0.04, (CRANK.z - 0.16 + 0.10) / 2), RUST)
    # Exhaust pipe from the exchanger into the chimney.
    beam(bm, (-0.42, ex_y, CRANK.z + 0.10), (-0.42, ex_y, 1.28), 0.06, 0.06, IRON)
    beam(bm, (-0.42, ex_y, 1.28), (chx + 0.07, chy, 1.28), 0.06, 0.06, IRON)
    cyl(bm, 0.045, 0.03, (-0.42, ex_y, 1.28), "Z", RUST, segs=10)

    # Rear pedestal holding the crankshaft next to the flywheel.
    py = 0.19
    for s in (-1, 1):
        beam(bm, (CRANK.x + s * 0.20, py, 0.10), (CRANK.x + s * 0.05, py, CRANK.z - 0.05), 0.06, 0.06, IRON)
    box(bm, (0.16, 0.08, 0.10), (CRANK.x, py, CRANK.z), RUST)

    # Dynamo body on its stand (pinion and shaft are a separate object).
    dx = DYNAMO.x
    box(bm, (0.24, 0.30, CRANK.z - 0.14 - 0.10), (dx, -0.06, (CRANK.z - 0.14 + 0.10) / 2), IRON)
    cyl(bm, 0.15, 0.40, (dx, -0.03, DYNAMO.z), "Y", IRON, segs=20)
    for y in (-0.235, 0.175):
        cyl(bm, 0.158, 0.03, (dx, y, DYNAMO.z), "Y", RUST, segs=20)
    for y in (-0.10, 0.0, 0.10):
        ring(bm, 0.156, 0.14, 0.04, (dx, y, DYNAMO.z), "Y", COPPER, segs=20)
    box(bm, (0.12, 0.10, 0.07), (dx, -0.03, DYNAMO.z + 0.18), IRON)
    for x in (dx - 0.03, dx + 0.03):
        cyl(bm, 0.01, 0.035, (x, -0.03, DYNAMO.z + 0.23), "Z", COPPER, segs=6)
    beam(bm, (dx + 0.06, 0.02, DYNAMO.z + 0.18), (dx + 0.17, 0.02, 0.10), 0.03, 0.03, SOOT)  # cable
    # Charge dial on the stand front.
    dial = Vector((dx, -0.22, 0.50))
    cyl(bm, 0.085, 0.03, dial, "Y", IRON, segs=20)
    cyl(bm, 0.072, 0.01, dial + Vector((0, -0.017, 0)), "Y", DIAL, segs=20)
    box(bm, (0.008, 0.006, 0.06), dial + Vector((0.015, -0.024, 0.02)), SOOT,
        Matrix.Rotation(math.radians(-30), 4, "Y"))
    cyl(bm, 0.01, 0.012, dial + Vector((0, -0.026, 0)), "Y", IRON, segs=8)

    # Coal crate at the right end.
    cx = 0.84
    box(bm, (0.24, 0.50, 0.03), (cx, 0.0, 0.115), WOOD)
    for s in (-1, 1):
        box(bm, (0.24, 0.03, 0.22), (cx, s * 0.235, 0.24), WOOD)
        box(bm, (0.03, 0.50, 0.22), (cx + s * 0.105, 0.0, 0.24), WOOD)
    lumps = [(-0.05, -0.15, 0.30, 20), (0.04, -0.05, 0.31, 55), (-0.03, 0.08, 0.30, 10),
             (0.05, 0.15, 0.29, 75), (0.00, -0.01, 0.34, 35), (-0.06, 0.18, 0.31, 60),
             (0.06, -0.17, 0.30, 40)]
    for lx, ly, lz, ang in lumps:
        box(bm, (0.08, 0.07, 0.06), (cx + lx, ly, lz), SOOT,
            Matrix.Rotation(math.radians(ang), 4, Vector((1, 1, 0.5)).normalized()))
    box(bm, (0.20, 0.44, 0.12), (cx, 0.0, 0.22), SOOT)   # coal bed
    return to_object(bm, "feCoalGen_Base", bevel=0.004)


def build_crank():
    """Local coords: origin on the crankshaft axis; spins around local Y."""
    bm = bmesh.new()
    cyl(bm, 0.03, 0.78, (0, -0.02, 0), "Y", IRON, segs=12)          # shaft y -0.41..0.37
    gear(bm, GEAR_BIG_R, 16, 0.05, GEAR_Y, IRON, hub_r=0.05)
    cyl(bm, 0.035, 0.025, (0, GEAR_Y - 0.05, 0), "Y", RUST, segs=6)  # nut
    # Flywheel with 5 spokes.
    ring(bm, FLY_R, FLY_R - 0.06, 0.07, (0, FLY_Y, 0), "Y", IRON, segs=36)
    ring(bm, FLY_R + 0.006, FLY_R - 0.012, 0.074, (0, FLY_Y, 0), "Y", RUST, segs=36)
    cyl(bm, 0.07, 0.10, (0, FLY_Y, 0), "Y", IRON, segs=12)
    for k in range(5):
        m = Matrix.Rotation(k * 2 * math.pi / 5, 4, "Y") @ Matrix.Translation(((FLY_R - 0.03) / 2 + 0.03, FLY_Y, 0))
        n = len(bm.faces)
        r = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)
        _finish(bm, n, IRON, m @ Matrix.Diagonal((FLY_R - 0.09, 0.035, 0.045, 1.0)), r["verts"])
    return to_object(bm, "feCoalGen_Crank", location=CRANK, bevel=0.003)


def build_dynamo_rotor():
    bm = bmesh.new()
    cyl(bm, 0.025, 0.20, (0, -0.30, 0), "Y", IRON, segs=10)
    # Half-tooth phase so the pinion teeth sit between the big gear's teeth.
    gear(bm, GEAR_SMALL_R, 8, 0.05, GEAR_Y, IRON, phase=math.pi + math.pi / 8, hub_r=0.04)
    cyl(bm, 0.03, 0.025, (0, GEAR_Y - 0.05, 0), "Y", RUST, segs=6)
    return to_object(bm, "feCoalGen_DynamoRotor", location=DYNAMO, bevel=0.002)


# ---------------------------------------------------------------- scene
def main():
    for ob in list(bpy.data.objects):
        if ob.name.startswith("feCoalGen") or ob.name == "Cube":
            bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    make_materials()

    col = bpy.data.collections.get("feCoalGenerator")
    if not col:
        col = bpy.data.collections.new("feCoalGenerator")
        bpy.context.scene.collection.children.link(col)

    base = build_base()
    crank = build_crank()
    rotor = build_dynamo_rotor()
    for ob in (base, crank, rotor):
        col.objects.link(ob)
    for child in (crank, rotor):
        child.parent = base
        child.matrix_parent_inverse = base.matrix_world.inverted()

    bpy.context.view_layer.update()
    lo, hi, tris = Vector((1e9,) * 3), Vector((-1e9,) * 3), 0
    for ob in (base, crank, rotor):
        for v in ob.data.vertices:
            w = ob.matrix_world @ v.co
            lo, hi = Vector(map(min, lo, w)), Vector(map(max, hi, w))
        tris += sum(len(p.vertices) - 2 for p in ob.data.polygons)
    print("bbox min", tuple(round(c, 3) for c in lo), "max", tuple(round(c, 3) for c in hi))
    print("triangles (before bevel):", tris)


main()
