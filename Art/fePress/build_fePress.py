"""Builds the Parts Press (M02, block fePress) in the open Blender scene.

Run inside Blender (Scripting tab, or through the Blender MCP server).
Units: 1 Blender unit = 1 m = 1 game block. Block fePress has MultiBlockDim="2,2,1"
(Config/blocks.xml): 2 wide (X) x 2 tall (Z) x 1 deep (Y). Origin at the floor center
of the footprint; the front faces -Y.

A friction screw press on a heavy workbench: two columns and a crosshead, a vertical
screw ("fuso") with a horizontal flywheel ("volante") on top, a ram with a punch over a
plate die ("matriz de chapa"). A small Carga motor drives the flywheel through a
friction wheel on its rim. Raw forged iron on the left of the bench, finished plates
on the right; input/output cabinets under the bench, cast-iron pedestal in the middle.

Objects:
  fePress_Base        static (root)
  fePress_Screw       screw + flywheel; spins around local Z
  fePress_Ram         ram + punch; moves along local Z (down when pressing)
  fePress_DriveWheel  motor friction wheel; spins around local Z (opposite to the flywheel)
  fePress_PortIn_1    conveyor input: Forged Iron (left side)
  fePress_PortIn_2    conveyor input: Carga (back of the right cell)
  fePress_PortOut_1   conveyor output: Iron Plate (right side)

The scene is cleared of other objects first (except the default Camera/Light and
the fePreview* helpers): save the previous model before running this.
"""
import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

TOP = 0.88                        # bench top surface
BOLSTER_Z = TOP + 0.06
COL_X, COL_R = 0.26, 0.045
CROSS_Z0, CROSS_Z1 = 1.64, 1.80
SCREW_AXIS_Z = 1.60               # Screw object origin (on the axis)
WHEEL_Z, WHEEL_RO, WHEEL_RI = 1.90, 0.34, 0.29
RAM_Z = 1.26                      # Ram object origin (its center)
DRIVE = Vector((0.415, 0.0, WHEEL_Z))
rng = random.Random(11)

MATS = {
    "fePress_Wood":    ((0.30, 0.18, 0.09), 0.85, 0.00, 0.0),
    "fePress_Iron":    ((0.15, 0.15, 0.16), 0.55, 0.85, 0.0),
    "fePress_Rust":    ((0.30, 0.13, 0.06), 0.80, 0.35, 0.0),
    "fePress_Steel":   ((0.55, 0.55, 0.57), 0.30, 1.00, 0.0),
    "fePress_Brass":   ((0.70, 0.55, 0.22), 0.35, 1.00, 0.0),
    "fePress_Copper":  ((0.72, 0.36, 0.20), 0.35, 1.00, 0.0),
    "fePress_Soot":    ((0.04, 0.04, 0.04), 0.90, 0.20, 0.0),
    "fePress_Dial":    ((0.80, 0.74, 0.58), 0.60, 0.00, 0.0),
    "fePress_Rubber":  ((0.06, 0.06, 0.06), 0.85, 0.00, 0.0),
    "fePress_PortIn":  ((0.16, 0.48, 0.16), 0.60, 0.20, 0.0),
    "fePress_PortOut": ((0.85, 0.45, 0.06), 0.60, 0.20, 0.0),
}
MI = {name: i for i, name in enumerate(MATS)}
(WOOD, IRON, RUST, STEEL, BRASS, COPPER, SOOT, DIAL, RUBBER,
 PORT_IN, PORT_OUT) = (MI[n] for n in MATS)


def make_materials():
    for name, (rgb, rough, metal, emit) in MATS.items():
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = m.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metal
        m.diffuse_color = (*rgb, 1.0)


# ---------------------------------------------------------------- bmesh helpers
AXIS = {
    "Z": Matrix.Identity(4),
    "Y": Matrix.Rotation(math.pi / 2, 4, "X"),
    "X": Matrix.Rotation(math.pi / 2, 4, "Y"),
}


def _finish(bm, mat, matrix, verts):
    # Material goes on the faces of the new verts: bm.faces order is not creation order.
    bmesh.ops.transform(bm, matrix=matrix, verts=verts)
    for f in {f for v in verts for f in v.link_faces}:
        f.material_index = mat


def box_m(bm, size, matrix, mat):
    r = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)
    _finish(bm, mat, matrix @ Matrix.Diagonal((*size, 1.0)), r["verts"])


def box(bm, size, loc, mat, rot=Matrix.Identity(4)):
    box_m(bm, size, Matrix.Translation(loc) @ rot, mat)


def beam(bm, a, b, w, t, mat):
    a, b = Vector(a), Vector(b)
    d = b - a
    rot = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    box(bm, (w, t, d.length), (a + b) / 2, mat, rot)


def cyl(bm, r, depth, loc, axis, mat, segs=16, r2=None):
    res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                                radius1=r, radius2=r if r2 is None else r2,
                                depth=depth, calc_uvs=True)
    _finish(bm, mat, Matrix.Translation(loc) @ AXIS[axis], res["verts"])


def ring(bm, ro, ri, depth, loc, axis, mat, segs=24):
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
    _finish(bm, mat, Matrix.Translation(loc) @ AXIS[axis], [v for lp in loops for v in lp])


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


# ---------------------------------------------------------------- conveyor ports
# Standard (Art/CONVEYOR_PORTS.md): opening 0.36 x 0.22 m centered 0.25 m above the
# floor, on the outer face of one block cell, flush with the block boundary; iron
# frame with the top bar painted green (input) or orange (output); a duct joins
# the face to the machine body. Each port also gets an empty <prefix>_Port{In|Out}_<n>
# on the face, its +Z pointing outward.
PORT_W, PORT_H, PORT_Z, PORT_FRAME = 0.36, 0.22, 0.25, 0.045
PORT_DARK = SOOT
# Forged Iron in on the left, Carga in at the back of the right cell, plates out on the right.
PORTS = [("In", (-1.0, 0.0, PORT_Z), (-1, 0, 0), 0.07),
         ("In", (0.5, 0.5, PORT_Z), (0, 1, 0), 0.14),
         ("Out", (1.0, 0.0, PORT_Z), (1, 0, 0), 0.07)]


def _port_frame(pt, normal):
    n = Vector(normal).normalized()
    up = Vector((0, 0, 1))
    m = Matrix((n.cross(up), n, up)).transposed().to_4x4()
    m.translation = Vector(pt)
    return m


def port(bm, pt, normal, kind, depth):
    m = _port_frame(pt, normal)
    T = Matrix.Translation
    fw, hw, hh = PORT_FRAME, PORT_W / 2, PORT_H / 2
    d = max(depth, 0.05)
    for s in (-1, 1):
        box_m(bm, (0.02, d, PORT_H + 0.04), m @ T((s * (hw + 0.01), -d / 2, 0)), IRON)
        box_m(bm, (PORT_W + 0.04, d, 0.02), m @ T((0, -d / 2, s * (hh + 0.01))), IRON)
    box_m(bm, (PORT_W, 0.02, PORT_H), m @ T((0, -d + 0.01, 0)), PORT_DARK)
    for s in (-1, 1):
        box_m(bm, (fw, 0.04, PORT_H + 2 * fw), m @ T((s * (hw + fw / 2), -0.02, 0)), IRON)
    box_m(bm, (PORT_W + 2 * fw, 0.04, fw), m @ T((0, -0.02, -(hh + fw / 2))), IRON)
    box_m(bm, (PORT_W + 2 * fw, 0.04, fw), m @ T((0, -0.02, hh + fw / 2)),
          PORT_IN if kind == "In" else PORT_OUT)
    if kind == "In":
        c = min(d, 0.12)
        box_m(bm, (PORT_W - 0.01, c, 0.012),
              m @ T((0, -c / 2, -hh + 0.03)) @ Matrix.Rotation(math.radians(12), 4, "X"), IRON)
    else:
        box_m(bm, (PORT_W - 0.02, 0.01, 0.09), m @ T((0, -0.05, hh - 0.05)), IRON)
        box_m(bm, (PORT_W - 0.02, 0.016, 0.016), m @ T((0, -0.05, hh - 0.005)), IRON)


def add_port_empties(prefix, base, col):
    count = {"In": 0, "Out": 0}
    for kind, pt, nrm, _depth in PORTS:
        count[kind] += 1
        e = bpy.data.objects.new(f"{prefix}_Port{kind}_{count[kind]}", None)
        e.empty_display_type = "SINGLE_ARROW"
        e.empty_display_size = 0.25
        e.location = pt
        e.rotation_euler = Vector(nrm).to_track_quat("Z", "Y").to_euler()
        col.objects.link(e)
        e.parent = base


# ---------------------------------------------------------------- parts
def build_base():
    bm = bmesh.new()
    # Bench: plank top with iron edge bands, four legs, stretchers.
    for i, y in enumerate((-0.28, 0.0, 0.28)):
        box(bm, (1.90, 0.275, 0.06), (0, y, TOP - 0.03), WOOD)
    for y in (-0.42, 0.42):
        box(bm, (1.92, 0.012, 0.07), (0, y, TOP - 0.035), RUST)
    for x in (-0.90, 0.90):
        box(bm, (0.012, 0.86, 0.07), (x + (0.006 if x > 0 else -0.006), 0, TOP - 0.035), RUST)
    for x in (-0.86, 0.86):
        for y in (-0.36, 0.36):
            box(bm, (0.08, 0.08, TOP - 0.06), (x, y, (TOP - 0.06) / 2), WOOD)
            box(bm, (0.10, 0.10, 0.012), (x, y, 0.006), IRON)
        box(bm, (0.05, 0.64, 0.06), (x, 0, 0.12), WOOD)
    for y in (-0.36, 0.36):
        box(bm, (1.64, 0.05, 0.06), (0, y, TOP - 0.12), WOOD)

    # Cabinets under the bench: input (left) and output (right), riveted iron.
    for side in (-1, 1):
        cx = side * 0.66
        box(bm, (0.42, 0.66, 0.66), (cx, 0, 0.39), IRON)
        for z in (0.10, 0.68):
            box(bm, (0.43, 0.67, 0.025), (cx, 0, z), RUST)
        box(bm, (0.30, 0.012, 0.36), (cx, -0.336, 0.40), RUST)          # front hatch
        box(bm, (0.08, 0.02, 0.02), (cx, -0.35, 0.48), STEEL)           # handle
        for x in (cx - 0.17, cx + 0.17):
            for z in (0.20, 0.40, 0.60):
                cyl(bm, 0.01, 0.01, (x, -0.333, z), "Y", STEEL, segs=6)

    # Cast-iron pedestal under the press, with a Carga dial on the front.
    box(bm, (0.60, 0.56, 0.08), (0, 0, 0.04), IRON)
    box(bm, (0.50, 0.46, TOP - 0.14), (0, 0, 0.08 + (TOP - 0.14) / 2), IRON)
    box(bm, (0.54, 0.50, 0.04), (0, 0, TOP - 0.08), RUST)
    dial = Vector((0, -0.24, 0.55))
    cyl(bm, 0.085, 0.03, dial, "Y", IRON, segs=20)
    cyl(bm, 0.072, 0.01, dial + Vector((0, -0.017, 0)), "Y", DIAL, segs=20)
    box(bm, (0.008, 0.006, 0.06), dial + Vector((-0.015, -0.024, 0.02)), SOOT,
        Matrix.Rotation(math.radians(25), 4, "Y"))
    cyl(bm, 0.01, 0.012, dial + Vector((0, -0.026, 0)), "Y", IRON, segs=8)

    # Press: bolster, plate die, columns, crosshead with brass nut.
    box(bm, (0.70, 0.46, 0.06), (0, 0, TOP + 0.03), IRON)
    box(bm, (0.32, 0.28, 0.06), (0, 0, BOLSTER_Z + 0.03), STEEL)
    box(bm, (0.22, 0.17, 0.006), (0, 0, BOLSTER_Z + 0.061), SOOT)          # die cavity
    box(bm, (0.20, 0.15, 0.006), (0, 0, BOLSTER_Z + 0.064), STEEL)         # blank in the die
    for x in (-COL_X, COL_X):
        cyl(bm, COL_R, CROSS_Z1 - BOLSTER_Z, (x, 0, (BOLSTER_Z + CROSS_Z1) / 2), "Z", STEEL, segs=16)
        cyl(bm, 0.07, 0.04, (x, 0, BOLSTER_Z + 0.02), "Z", IRON, segs=6)   # bottom nuts
        cyl(bm, 0.07, 0.05, (x, 0, CROSS_Z1 + 0.025), "Z", IRON, segs=6)   # top nuts
    box(bm, (0.78, 0.24, CROSS_Z1 - CROSS_Z0), (0, 0, (CROSS_Z0 + CROSS_Z1) / 2), IRON)
    for x in (-0.37, 0.37):
        box(bm, (0.04, 0.25, CROSS_Z1 - CROSS_Z0 + 0.01), (x, 0, (CROSS_Z0 + CROSS_Z1) / 2), RUST)
    cyl(bm, 0.08, 0.06, (0, 0, CROSS_Z1 + 0.03), "Z", BRASS, segs=16)       # screw nut

    # Carga motor on a bracket off the crosshead's right end, cable down to the bench.
    box(bm, (0.16, 0.14, 0.03), (0.44, 0, CROSS_Z0 - 0.015), IRON)
    beam(bm, (0.38, 0, CROSS_Z0 - 0.03), (0.30, 0, CROSS_Z0 - 0.25), 0.03, 0.06, IRON)
    cyl(bm, 0.065, 0.20, (DRIVE.x, 0, CROSS_Z0 + 0.10), "Z", IRON, segs=16)
    for z in (CROSS_Z0 + 0.05, CROSS_Z0 + 0.10, CROSS_Z0 + 0.15):
        ring(bm, 0.068, 0.06, 0.025, (DRIVE.x, 0, z), "Z", COPPER, segs=16)
    cyl(bm, 0.07, 0.02, (DRIVE.x, 0, CROSS_Z0 + 0.21), "Z", RUST, segs=16)
    box(bm, (0.06, 0.05, 0.05), (DRIVE.x + 0.07, 0, CROSS_Z0 + 0.12), IRON)  # terminal box
    # Cable: out of the terminal box, then straight down to the bench, with two clips.
    cx, cy = DRIVE.x + 0.10, 0.06
    beam(bm, (DRIVE.x + 0.09, 0.0, CROSS_Z0 + 0.10), (cx, cy, CROSS_Z0 + 0.06), 0.018, 0.018, RUBBER)
    beam(bm, (cx, cy, CROSS_Z0 + 0.06), (cx, cy, TOP + 0.005), 0.018, 0.018, RUBBER)
    box(bm, (0.04, 0.04, 0.02), (cx, cy, TOP + 0.01), IRON)
    box(bm, (0.03, 0.03, 0.03), (cx, cy, 1.25), IRON)

    # Clutch lever on the front of the right column.
    box(bm, (0.06, 0.06, 0.08), (COL_X, -0.07, 1.10), IRON)
    beam(bm, (COL_X, -0.09, 1.10), (COL_X + 0.10, -0.30, 1.42), 0.025, 0.025, IRON)
    cyl(bm, 0.03, 0.08, (COL_X + 0.10, -0.30, 1.45), "Z", WOOD, segs=10)

    # Raw forged iron (left) and finished plates (right) on the bench.
    for i in range(5):
        x, y = -0.66 + rng.uniform(-0.05, 0.05), -0.12 + i * 0.06
        box(bm, (0.30, 0.05, 0.04), (x, y, TOP + 0.02), SOOT,
            Matrix.Rotation(math.radians(rng.uniform(-6, 6)), 4, "Z"))
    for i in range(2):
        box(bm, (0.30, 0.05, 0.04), (-0.66, -0.09 + i * 0.12, TOP + 0.06), SOOT)
    for i in range(7):
        box(bm, (0.28, 0.22, 0.008), (0.66 + rng.uniform(-0.01, 0.01), -0.05 + rng.uniform(-0.01, 0.01),
                                      TOP + 0.004 + i * 0.0085), STEEL,
            Matrix.Rotation(math.radians(rng.uniform(-4, 4)), 4, "Z"))

    for kind, pt, nrm, depth in PORTS:
        port(bm, pt, nrm, kind, depth)
    return to_object(bm, "fePress_Base", bevel=0.004)


def build_ram():
    """Local coords: origin at the ram's center; moves along local Z."""
    bm = bmesh.new()
    box(bm, (0.36, 0.20, 0.14), (0, 0, 0), IRON)
    for x in (-COL_X, COL_X):
        cyl(bm, 0.07, 0.16, (x, 0, 0), "Z", RUST, segs=16)                  # guide sleeves
    box(bm, (0.20, 0.15, 0.05), (0, 0, -0.095), STEEL)                      # punch
    cyl(bm, 0.06, 0.03, (0, 0, 0.085), "Z", IRON, segs=12)                  # screw socket
    return to_object(bm, "fePress_Ram", location=(0, 0, RAM_Z), bevel=0.003)


def build_screw():
    """Local coords: origin on the screw axis at SCREW_AXIS_Z; spins around local Z."""
    bm = bmesh.new()
    z0, z1 = RAM_Z + 0.07 - SCREW_AXIS_Z, WHEEL_Z + 0.03 - SCREW_AXIS_Z
    cyl(bm, 0.04, z1 - z0, (0, 0, (z0 + z1) / 2), "Z", STEEL, segs=16)
    z = RAM_Z + 0.10 - SCREW_AXIS_Z
    while z < CROSS_Z0 - 0.01 - SCREW_AXIS_Z:                             # visible thread
        ring(bm, 0.052, 0.039, 0.012, (0, 0, z), "Z", STEEL, segs=16)
        z += 0.03
    wz = WHEEL_Z - SCREW_AXIS_Z
    ring(bm, WHEEL_RO, WHEEL_RI, 0.05, (0, 0, wz), "Z", IRON, segs=40)
    ring(bm, WHEEL_RO + 0.004, WHEEL_RO - 0.012, 0.03, (0, 0, wz), "Z", RUST, segs=40)
    cyl(bm, 0.07, 0.07, (0, 0, wz), "Z", IRON, segs=12)
    for k in range(4):
        m = (Matrix.Translation((0, 0, wz)) @ Matrix.Rotation(k * math.pi / 2 + math.pi / 4, 4, "Z")
             @ Matrix.Translation(((WHEEL_RI + 0.07) / 2, 0, 0)))
        box_m(bm, (WHEEL_RI - 0.06, 0.035, 0.035), m, IRON)
    cyl(bm, 0.018, 0.07, (WHEEL_RI - 0.03, 0, wz + 0.05), "Z", WOOD, segs=8)   # hand peg
    return to_object(bm, "fePress_Screw", location=(0, 0, SCREW_AXIS_Z), bevel=0.003)


def build_drive_wheel():
    bm = bmesh.new()
    cyl(bm, 0.015, 0.08, (0, 0, -0.03), "Z", STEEL, segs=8)
    r = DRIVE.x - WHEEL_RO - 0.004            # touches the flywheel rim
    cyl(bm, r, 0.04, (0, 0, 0), "Z", RUBBER, segs=16)
    cyl(bm, r * 0.55, 0.046, (0, 0, 0), "Z", IRON, segs=12)
    return to_object(bm, "fePress_DriveWheel", location=DRIVE, bevel=0.002)


# ---------------------------------------------------------------- scene
def main():
    keep = {"Camera", "Light"}
    for ob in list(bpy.data.objects):
        if ob.name not in keep and not ob.name.startswith("fePreview"):
            bpy.data.objects.remove(ob, do_unlink=True)
    for coll in list(bpy.data.collections):
        if not coll.objects and not coll.children:
            bpy.data.collections.remove(coll)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    for m in list(bpy.data.materials):
        if m.users == 0:
            bpy.data.materials.remove(m)
    make_materials()

    col = bpy.data.collections.get("fePress") or bpy.data.collections.new("fePress")
    if col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(col)

    base = build_base()
    parts = [build_screw(), build_ram(), build_drive_wheel()]
    for ob in [base] + parts:
        col.objects.link(ob)
    for child in parts:
        child.parent = base
        child.matrix_parent_inverse = base.matrix_world.inverted()
    add_port_empties("fePress", base, col)

    bpy.context.view_layer.update()
    lo, hi, tris = Vector((1e9,) * 3), Vector((-1e9,) * 3), 0
    for ob in [base] + parts:
        for v in ob.data.vertices:
            w = ob.matrix_world @ v.co
            lo, hi = Vector(map(min, lo, w)), Vector(map(max, hi, w))
        tris += sum(len(p.vertices) - 2 for p in ob.data.polygons)
    print("bbox min", tuple(round(c, 3) for c in lo), "max", tuple(round(c, 3) for c in hi))
    print("triangles (before bevel):", tris)


main()
