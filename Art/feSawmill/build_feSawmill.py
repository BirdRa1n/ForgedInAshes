"""Builds the Sawmill (M16, block feSawmill) in the open Blender scene.

Run inside Blender (Scripting tab, or through the Blender MCP server).
Units: 1 Blender unit = 1 m = 1 game block. Proposed size 2 wide (X) x 1 deep (Y) x
2 tall (Z), i.e. MultiBlockDim="2,2,1" like the other big stations (the block does not
exist yet: phase 3). Origin at the floor center of the footprint; the front faces -Y.

A heavy timber saw bench: big circular saw with guard and riving knife, a log carriage
running on rails behind the blade (the log overhangs the blade), a Carga motor under
the table driving the saw arbor by belt, sawdust falling under the blade, logs waiting
on the left, planks and beams stacked on the right; input/output bins under the table.

Objects:
  feSawmill_Base         static (root)
  feSawmill_Blade        saw blade + arbor + pulley; spins around local Y
  feSawmill_MotorPulley  motor pulley; spins around local Y (same direction as the blade)
  feSawmill_Carriage     log carriage + log + dogs; slides along local X (towards +X when cutting)
  feSawmill_PortIn_1     conveyor input: wood/logs (left side)
  feSawmill_PortIn_2     conveyor input: Carga (back of the left cell)
  feSawmill_PortOut_1    conveyor output: planks/beams (right side)

The scene is cleared of other objects first (except the default Camera/Light and
the fePreview* helpers): save the previous model before running this.
"""
import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

TOP = 0.80                                  # table top
BLADE = Vector((0.10, 0.0, 0.70))           # arbor center (axis along Y)
BLADE_R = 0.34
PULLEY_Y = 0.24
MOTOR = Vector((0.10, 0.10, 0.22))          # motor body center (axis along Y)
CARRIAGE = Vector((-0.15, 0.19, TOP + 0.02))
LOG_R = 0.11
rng = random.Random(9)

MATS = {
    "feSawmill_Wood":    ((0.30, 0.18, 0.09), 0.85, 0.00, 0.0),
    "feSawmill_Bark":    ((0.22, 0.14, 0.08), 0.90, 0.00, 0.0),
    "feSawmill_WoodCut": ((0.66, 0.50, 0.32), 0.80, 0.00, 0.0),
    "feSawmill_Sawdust": ((0.74, 0.60, 0.40), 0.95, 0.00, 0.0),
    "feSawmill_Iron":    ((0.15, 0.15, 0.16), 0.55, 0.85, 0.0),
    "feSawmill_Rust":    ((0.30, 0.13, 0.06), 0.80, 0.35, 0.0),
    "feSawmill_Steel":   ((0.60, 0.60, 0.62), 0.25, 1.00, 0.0),
    "feSawmill_Copper":  ((0.72, 0.36, 0.20), 0.35, 1.00, 0.0),
    "feSawmill_Rubber":  ((0.06, 0.06, 0.06), 0.85, 0.00, 0.0),
    "feSawmill_Paint":   ((0.80, 0.60, 0.10), 0.60, 0.20, 0.0),
    "feSawmill_Soot":    ((0.04, 0.04, 0.04), 0.90, 0.20, 0.0),
    "feSawmill_Dial":    ((0.80, 0.74, 0.58), 0.60, 0.00, 0.0),
    "feSawmill_PortIn":  ((0.16, 0.48, 0.16), 0.60, 0.20, 0.0),
    "feSawmill_PortOut": ((0.85, 0.45, 0.06), 0.60, 0.20, 0.0),
}
MI = {name: i for i, name in enumerate(MATS)}
(WOOD, BARK, WOODCUT, SAWDUST, IRON, RUST, STEEL, COPPER, RUBBER, PAINT, SOOT, DIAL,
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
# Wood in on the left, Carga in at the back of the left cell, planks/beams out on the right.
PORTS = [("In", (-1.0, 0.0, PORT_Z), (-1, 0, 0), 0.14),
         ("In", (-0.5, 0.5, PORT_Z), (0, 1, 0), 0.22),
         ("Out", (1.0, 0.0, PORT_Z), (1, 0, 0), 0.14)]

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
def arc_band(bm, ro, ri, depth, center, a0, a1, mat, segs=16):
    """Part of a ring in the XZ plane (axis Y), from angle a0 to a1 (radians, 0 = +X, CCW toward +Z)."""
    c = Vector(center)
    loops = []
    for i in range(segs + 1):
        a = a0 + (a1 - a0) * i / segs
        dx, dz = math.cos(a), math.sin(a)
        loops.append([bm.verts.new(c + Vector((r * dx, y, r * dz)))
                      for r, y in ((ro, -depth / 2), (ro, depth / 2), (ri, depth / 2), (ri, -depth / 2))])
    faces = []
    for i in range(segs):
        for k in range(4):
            k2 = (k + 1) % 4
            faces.append(bm.faces.new((loops[i][k], loops[i][k2], loops[i + 1][k2], loops[i + 1][k])))
    faces.append(bm.faces.new(loops[0]))
    faces.append(bm.faces.new(list(reversed(loops[-1]))))
    for f in faces:
        f.material_index = mat


def build_base():
    bm = bmesh.new()
    # Table: plank top with a slot for the blade, aprons, legs, stretchers.
    for y in (-0.22, -0.075):
        box(bm, (1.90, 0.14, 0.06), (0, y, TOP - 0.03), WOOD)
    box(bm, (1.90, 0.185, 0.06), (0, 0.0975, TOP - 0.03), WOOD)      # 1 cm slot for the blade at y 0
    box(bm, (1.90, 0.10, 0.06), (0, 0.24, TOP - 0.03), WOOD)
    for y in (-0.29, 0.29):
        box(bm, (1.84, 0.04, 0.12), (0, y, TOP - 0.12), WOOD)
    for x in (-0.90, -0.20, 0.40, 0.90):       # middle legs clear of the Carga duct and bins
        for y in (-0.26, 0.26):
            box(bm, (0.09, 0.09, TOP - 0.06), (x, y, (TOP - 0.06) / 2), WOOD)
            box(bm, (0.11, 0.11, 0.012), (x, y, 0.006), IRON)
    for x in (-0.90, 0.90):
        box(bm, (0.05, 0.48, 0.06), (x, 0, 0.10), WOOD)
    for y in (-0.26, 0.26):
        box(bm, (1.70, 0.05, 0.05), (0, y, 0.10), WOOD)
    # Iron throat plate around the blade slot.
    box(bm, (0.80, 0.10, 0.008), (BLADE.x, -0.035, TOP + 0.004), IRON)
    box(bm, (0.74, 0.012, 0.009), (BLADE.x, 0.0, TOP + 0.0045), SOOT)          # the slot

    # Carriage rails behind the blade.
    for y in (0.12, 0.26):
        box(bm, (1.86, 0.03, 0.02), (0, y, TOP + 0.01), STEEL)
        for x in (-0.80, -0.30, 0.30, 0.80):
            cyl(bm, 0.008, 0.006, (x, y, TOP + 0.022), "Z", IRON, segs=6)
    for x in (-0.94, 0.94):
        box(bm, (0.02, 0.20, 0.05), (x, 0.19, TOP + 0.025), RUST)              # end stops

    # Blade guard: arched hood on an arm from the back, riving knife, yellow edge.
    arc_band(bm, BLADE_R + 0.05, BLADE_R + 0.02, 0.07, (BLADE.x, -0.005, BLADE.z),
             math.radians(55), math.radians(125), IRON, segs=10)
    for s in (-1, 1):
        arc_band(bm, BLADE_R + 0.05, BLADE_R - 0.04, 0.006, (BLADE.x, -0.005 + s * 0.036, BLADE.z),
                 math.radians(55), math.radians(125), PAINT if s < 0 else IRON, segs=10)
    top_z = BLADE.z + BLADE_R + 0.05
    beam(bm, (BLADE.x, 0.0, top_z), (BLADE.x, 0.31, top_z + 0.02), 0.03, 0.03, IRON)
    beam(bm, (BLADE.x, 0.31, top_z + 0.02), (BLADE.x, 0.31, TOP - 0.06), 0.04, 0.04, IRON)
    box(bm, (0.08, 0.05, 0.03), (BLADE.x, 0.31, TOP - 0.05), IRON)
    knife_x = BLADE.x + BLADE_R + 0.02
    box(bm, (0.10, 0.006, 0.16), (knife_x, 0.0, TOP + 0.07), STEEL)            # riving knife

    # Arbor bearings under the table, belt to the motor, motor, sawdust chute and heap.
    for y in (-0.05, 0.17):
        box(bm, (0.10, 0.05, 0.10), (BLADE.x, y, BLADE.z - 0.02), IRON)
    box(bm, (0.12, 0.06, TOP - 0.10 - BLADE.z + 0.06), (BLADE.x, 0.17, (TOP - 0.10 + BLADE.z - 0.06) / 2), IRON)
    big_r, small_r = 0.075, 0.045
    a, b = Vector((BLADE.x, PULLEY_Y, BLADE.z)), Vector((MOTOR.x, PULLEY_Y, MOTOR.z))
    ring(bm, big_r + 0.008, big_r, 0.028, a, "Y", RUBBER, segs=20)
    ring(bm, small_r + 0.008, small_r, 0.028, b, "Y", RUBBER, segs=16)
    for s in (-1, 1):
        beam(bm, a + Vector((s * (big_r + 0.004), 0, 0)), b + Vector((s * (small_r + 0.004), 0, 0)),
             0.008, 0.028, RUBBER)
    cyl(bm, 0.09, 0.22, (MOTOR.x, MOTOR.y, MOTOR.z), "Y", IRON, segs=18)
    for dy in (-0.06, 0.0, 0.06):
        ring(bm, 0.093, 0.085, 0.03, (MOTOR.x, MOTOR.y + dy, MOTOR.z), "Y", COPPER, segs=18)
    box(bm, (0.20, 0.16, 0.10), (MOTOR.x, MOTOR.y, 0.05), IRON)               # motor base
    box(bm, (0.06, 0.05, 0.05), (MOTOR.x + 0.10, MOTOR.y + 0.02, MOTOR.z + 0.06), IRON)  # terminal
    beam(bm, (MOTOR.x + 0.13, MOTOR.y + 0.03, MOTOR.z + 0.06), (-0.40, 0.24, 0.30), 0.02, 0.02, RUBBER)
    # Sawdust: heap under the blade on the front side, a few on the table.
    cyl(bm, 0.22, 0.14, (BLADE.x - 0.02, -0.15, 0.07), "Z", SAWDUST, segs=14, r2=0.04)
    cyl(bm, 0.12, 0.05, (BLADE.x + 0.18, -0.08, 0.025), "Z", SAWDUST, segs=12, r2=0.03)
    box(bm, (0.12, 0.08, 0.004), (BLADE.x - 0.18, -0.06, TOP + 0.002), SAWDUST)

    # Front controls: start lever and Carga dial on the apron.
    dial = Vector((-0.40, -0.315, TOP - 0.12))
    cyl(bm, 0.05, 0.02, dial, "Y", IRON, segs=16)
    cyl(bm, 0.042, 0.008, dial + Vector((0, -0.012, 0)), "Y", DIAL, segs=16)
    box(bm, (0.005, 0.005, 0.035), dial + Vector((0.008, -0.018, 0.01)), SOOT,
        Matrix.Rotation(math.radians(30), 4, "Y"))
    box(bm, (0.06, 0.03, 0.08), (-0.25, -0.32, TOP - 0.12), IRON)
    beam(bm, (-0.25, -0.33, TOP - 0.10), (-0.22, -0.40, TOP + 0.02), 0.018, 0.018, IRON)
    cyl(bm, 0.02, 0.06, (-0.22, -0.40, TOP + 0.04), "Z", WOOD, segs=8)

    # Logs waiting on the left (front), planks and beams stacked on the right.
    for i, (x, y, z) in enumerate(((-0.75, -0.17, TOP + 0.07), (-0.75, -0.02, TOP + 0.07))):
        cyl(bm, 0.07, 0.36, (x, y, z), "X", BARK, segs=10)
        for s in (-1, 1):
            cyl(bm, 0.062, 0.006, (x + s * 0.182, y, z), "X", WOODCUT, segs=10)
    for i in range(5):
        box(bm, (0.48, 0.12, 0.025), (0.66 + rng.uniform(-0.01, 0.01), -0.20, TOP + 0.0125 + i * 0.026),
            WOODCUT, Matrix.Rotation(math.radians(rng.uniform(-2, 2)), 4, "Z"))
    for i in range(2):
        box(bm, (0.48, 0.07, 0.07), (0.66, -0.07, TOP + 0.035 + i * 0.07), WOODCUT)   # beams, clear of the knife

    # Bins under the table: input (left, with Carga junction box behind), output (right).
    box(bm, (0.40, 0.36, 0.36), (-0.66, -0.06, 0.25), IRON)
    box(bm, (0.41, 0.37, 0.02), (-0.66, -0.06, 0.44), RUST)
    box(bm, (0.30, 0.14, 0.30), (-0.50, 0.21, 0.25), IRON)                    # Carga junction box
    box(bm, (0.06, 0.02, 0.06), (-0.40, 0.14, 0.33), COPPER)
    box(bm, (0.40, 0.48, 0.36), (0.66, 0.0, 0.25), IRON)
    box(bm, (0.41, 0.49, 0.02), (0.66, 0.0, 0.44), RUST)

    for kind, pt, nrm, depth in PORTS:
        port(bm, pt, nrm, kind, depth)
    return to_object(bm, "feSawmill_Base", bevel=0.003)


def build_blade():
    """Local coords: origin on the arbor; spins around local Y."""
    bm = bmesh.new()
    cyl(bm, BLADE_R - 0.02, 0.004, (0, 0, 0), "Y", STEEL, segs=40)
    teeth = 36
    for k in range(teeth):
        a = 2 * math.pi * k / teeth
        m = Matrix.Rotation(a, 4, "Y") @ Matrix.Translation((BLADE_R - 0.01, 0, 0)) @ \
            Matrix.Rotation(math.radians(20), 4, "Y")
        box_m(bm, (0.03, 0.007, 0.02), m, STEEL)
    for s in (-1, 1):
        cyl(bm, 0.06, 0.01, (0, s * 0.007, 0), "Y", IRON, segs=14)            # collars
    cyl(bm, 0.02, PULLEY_Y + 0.08, (0, (PULLEY_Y - 0.08) / 2, 0), "Y", STEEL, segs=10)  # arbor
    cyl(bm, 0.075, 0.03, (0, PULLEY_Y, 0), "Y", IRON, segs=20)
    for dy in (-0.018, 0.018):
        cyl(bm, 0.084, 0.006, (0, PULLEY_Y + dy, 0), "Y", IRON, segs=20)
    return to_object(bm, "feSawmill_Blade", location=BLADE, bevel=0.0)


def build_motor_pulley():
    bm = bmesh.new()
    cyl(bm, 0.012, 0.06, (0, -0.03, 0), "Y", STEEL, segs=8)
    cyl(bm, 0.045, 0.03, (0, 0, 0), "Y", IRON, segs=14)
    for dy in (-0.018, 0.018):
        cyl(bm, 0.053, 0.006, (0, dy, 0), "Y", IRON, segs=14)
    return to_object(bm, "feSawmill_MotorPulley", location=(MOTOR.x, PULLEY_Y, MOTOR.z), bevel=0.002)


def build_carriage():
    """Local coords: origin at CARRIAGE (on the rails); slides along local X."""
    bm = bmesh.new()
    box(bm, (0.62, 0.20, 0.04), (0, 0, 0.02), IRON)
    for x in (-0.24, 0.24):
        for y in (-0.07, 0.07):
            cyl(bm, 0.02, 0.02, (x, y, -0.005), "X", STEEL, segs=10)          # wheels
        box(bm, (0.05, 0.04, 0.26), (x, 0.08, 0.17), IRON)                    # knee
        beam(bm, (x, 0.06, 0.24), (x, -0.02, 0.20), 0.025, 0.025, RUST)       # dog
    box(bm, (0.05, 0.03, 0.03), (-0.30, -0.08, 0.06), IRON)                   # ratchet
    beam(bm, (-0.30, -0.09, 0.07), (-0.36, -0.14, 0.20), 0.016, 0.016, IRON)
    # The log (overhangs the blade toward -Y), with its sawn face.
    ly = 0.10 - (CARRIAGE.y - 0.0)            # log center at world Y 0.10
    lz = 0.04 + LOG_R
    cyl(bm, LOG_R, 0.80, (0.05, ly, lz), "X", BARK, segs=14)
    for s in (-1, 1):
        cyl(bm, LOG_R - 0.008, 0.006, (0.05 + s * 0.403, ly, lz), "X", WOODCUT, segs=14)
    box(bm, (0.40, 0.006, 0.12), (-0.15, ly - LOG_R + 0.012, lz), WOODCUT)   # flat sawn face
    return to_object(bm, "feSawmill_Carriage", location=CARRIAGE, bevel=0.002)


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

    col = bpy.data.collections.get("feSawmill") or bpy.data.collections.new("feSawmill")
    if col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(col)

    base = build_base()
    parts = [build_blade(), build_motor_pulley(), build_carriage()]
    for ob in [base] + parts:
        col.objects.link(ob)
    bpy.context.view_layer.update()
    for child in parts:            # direct children only (FBX export misplaces grandchildren)
        mw = child.matrix_world.copy()
        child.parent = base
        child.matrix_world = mw
    add_port_empties("feSawmill", base, col)

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
