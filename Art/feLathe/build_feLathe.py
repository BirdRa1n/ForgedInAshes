"""Builds the Lathe (M03, block feLathe) in the open Blender scene.

Run inside Blender (Scripting tab, or through the Blender MCP server).
Units: 1 Blender unit = 1 m = 1 game block. Block feLathe is 1x1x1 (Config/blocks.xml,
ART_BRIEF.md). Origin at the floor center of the block; the front faces -Y.

A small bench lathe on an iron cabinet: bed with rails, headstock with a 3-jaw chuck
holding a workpiece, tailstock with handwheel, carriage with tool post and a side
crank ("manivela lateral"), and a Carga motor behind the headstock driving the
spindle by belt. Carga dial and doors on the cabinet, chips on the tray.

Objects:
  feLathe_Base           static (root)
  feLathe_Spindle        chuck + workpiece + spindle pulley; spins around local X
  feLathe_MotorPulley    motor pulley; spins around local X (same direction as the spindle)
  feLathe_Carriage       saddle + cross slide + tool post + apron; slides along local X
  feLathe_CarriageWheel  apron crank; spins around local Y and moves with the carriage
  feLathe_TailWheel      tailstock handwheel; spins around local X
  feLathe_PortIn_1       conveyor input: raw material (left side)
  feLathe_PortIn_2       conveyor input: Carga (back)
  feLathe_PortOut_1      conveyor output: finished parts (right side)

The scene is cleared of other objects first (except the default Camera/Light and
the fePreview* helpers): save the previous model before running this.
"""
import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

TRAY_Z = 0.72                 # top of the cabinet tray
BED_Z = 0.80                  # top of the rails
AXIS_Y, AXIS_Z = -0.01, 0.90  # spindle center line (along X)
SPINDLE = Vector((-0.18, AXIS_Y, AXIS_Z))
MOTOR = Vector((-0.30, 0.19, 0.80))
PULLEY_X = -0.445
TAIL_WHEEL = Vector((0.40, AXIS_Y, AXIS_Z))
CARRIAGE = Vector((0.02, 0.0, BED_Z))
rng = random.Random(5)

MATS = {
    "feLathe_Wood":    ((0.30, 0.18, 0.09), 0.85, 0.00, 0.0),
    "feLathe_Iron":    ((0.15, 0.15, 0.16), 0.55, 0.85, 0.0),
    "feLathe_Rust":    ((0.30, 0.13, 0.06), 0.80, 0.35, 0.0),
    "feLathe_Steel":   ((0.55, 0.55, 0.57), 0.30, 1.00, 0.0),
    "feLathe_Brass":   ((0.70, 0.55, 0.22), 0.35, 1.00, 0.0),
    "feLathe_Copper":  ((0.72, 0.36, 0.20), 0.35, 1.00, 0.0),
    "feLathe_Soot":    ((0.04, 0.04, 0.04), 0.90, 0.20, 0.0),
    "feLathe_Dial":    ((0.80, 0.74, 0.58), 0.60, 0.00, 0.0),
    "feLathe_Rubber":  ((0.06, 0.06, 0.06), 0.85, 0.00, 0.0),
    "feLathe_Paint":   ((0.20, 0.30, 0.26), 0.70, 0.30, 0.0),
    "feLathe_PortIn":  ((0.16, 0.48, 0.16), 0.60, 0.20, 0.0),
    "feLathe_PortOut": ((0.85, 0.45, 0.06), 0.60, 0.20, 0.0),
}
MI = {name: i for i, name in enumerate(MATS)}
(WOOD, IRON, RUST, STEEL, BRASS, COPPER, SOOT, DIAL, RUBBER, PAINT,
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


def handwheel(bm, r, axis, mat, spokes=3, handle=True):
    """Handwheel at the local origin, axis X or Y; rim, hub, spokes and a handle pin."""
    ring(bm, r, r - 0.012, 0.014, (0, 0, 0), axis, mat, segs=20)
    cyl(bm, 0.016, 0.03, (0, 0, 0), axis, mat, segs=10)
    rot_axis = "X" if axis == "X" else "Y"
    for k in range(spokes):
        a = 2 * math.pi * k / spokes
        m = Matrix.Rotation(a, 4, rot_axis)
        d = Vector((0, 0, (r - 0.006) / 2))
        box_m(bm, (0.008, 0.008, r - 0.02) if axis == "X" else (0.008, 0.008, r - 0.02),
              Matrix.Translation(m @ d) @ m, mat)
    if handle:
        tip = Vector((0, 0, r - 0.006))
        off = Vector((0.04, 0, 0)) if axis == "X" else Vector((0, -0.04, 0))   # outward
        cyl(bm, 0.009, 0.045, tip + off / 2, axis, WOOD, segs=8)


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
# Raw material in on the left, Carga in at the back, finished parts out on the right.
PORTS = [("In", (-0.5, 0.0, PORT_Z), (-1, 0, 0), 0.08),
         ("In", (0.0, 0.5, PORT_Z), (0, 1, 0), 0.24),
         ("Out", (0.5, 0.0, PORT_Z), (1, 0, 0), 0.08)]


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
    # Cabinet on a plinth, two doors, drawer, Carga dial and switch.
    box(bm, (0.88, 0.60, 0.06), (0, -0.02, 0.03), IRON)
    box(bm, (0.84, 0.56, TRAY_Z - 0.08), (0, -0.02, 0.06 + (TRAY_Z - 0.08) / 2), PAINT)
    for z in (0.10, TRAY_Z - 0.05):
        box(bm, (0.85, 0.57, 0.02), (0, -0.02, z), IRON)
    for x in (-0.20, 0.20):
        box(bm, (0.36, 0.012, 0.36), (x, -0.306, 0.33), PAINT)
        box(bm, (0.02, 0.02, 0.10), (x + (0.14 if x < 0 else -0.14), -0.318, 0.36), STEEL)
    box(bm, (0.76, 0.012, 0.10), (0, -0.306, 0.58), PAINT)                  # drawer
    box(bm, (0.12, 0.02, 0.02), (0, -0.318, 0.58), STEEL)
    dial = Vector((0.30, -0.31, 0.58))
    cyl(bm, 0.055, 0.02, dial, "Y", IRON, segs=18)
    cyl(bm, 0.046, 0.008, dial + Vector((0, -0.012, 0)), "Y", DIAL, segs=18)
    box(bm, (0.006, 0.005, 0.04), dial + Vector((0.01, -0.018, 0.012)), SOOT,
        Matrix.Rotation(math.radians(30), 4, "Y"))
    box(bm, (0.05, 0.02, 0.07), (-0.30, -0.315, 0.58), SOOT)                # power switch
    beam(bm, (-0.30, -0.325, 0.58), (-0.30, -0.36, 0.62), 0.012, 0.012, STEEL)
    # Chip tray on top, with a lip and a few chips.
    box(bm, (0.92, 0.64, 0.02), (0, -0.02, TRAY_Z - 0.01), RUST)
    for x, w in ((-0.455, 0.01), (0.455, 0.01)):
        box(bm, (w, 0.64, 0.04), (x, -0.02, TRAY_Z + 0.01), RUST)
    for y in (-0.335, 0.295):
        box(bm, (0.92, 0.01, 0.04), (0, y, TRAY_Z + 0.01), RUST)
    for _ in range(9):
        x, y = rng.uniform(-0.1, 0.2), rng.uniform(-0.25, -0.15)
        box(bm, (0.03, 0.006, 0.01), (x, y, TRAY_Z + 0.005), STEEL,
            Matrix.Rotation(math.radians(rng.uniform(0, 180)), 4, "Z"))

    # Bed: base casting, two rails, leadscrew along the front.
    box(bm, (0.80, 0.20, 0.04), (0, -0.01, TRAY_Z + 0.02), IRON)
    for y in (-0.065, 0.045):
        box(bm, (0.80, 0.05, BED_Z - TRAY_Z - 0.04), (0, y, (TRAY_Z + 0.04 + BED_Z) / 2), STEEL)
    cyl(bm, 0.008, 0.80, (0, -0.115, 0.755), "X", STEEL, segs=8)
    for x in (-0.39, 0.39):
        box(bm, (0.03, 0.03, 0.04), (x, -0.115, 0.755), IRON)

    # Headstock with spindle bearings and gear cover.
    box(bm, (0.22, 0.22, AXIS_Z + 0.08 - BED_Z), (-0.29, AXIS_Y, (BED_Z + AXIS_Z + 0.08) / 2), PAINT)
    box(bm, (0.23, 0.23, 0.02), (-0.29, AXIS_Y, AXIS_Z + 0.08), IRON)
    cyl(bm, 0.045, 0.03, (-0.17, AXIS_Y, AXIS_Z), "X", IRON, segs=16)       # front bearing
    cyl(bm, 0.04, 0.03, (-0.41, AXIS_Y, AXIS_Z), "X", IRON, segs=16)        # rear bearing
    for z in (BED_Z + 0.03, AXIS_Z + 0.05):
        cyl(bm, 0.01, 0.012, (-0.36, -0.125, z), "Y", STEEL, segs=6)
        cyl(bm, 0.01, 0.012, (-0.22, -0.125, z), "Y", STEEL, segs=6)
    box(bm, (0.05, 0.02, 0.05), (-0.29, -0.13, BED_Z + 0.06), BRASS)        # speed plate

    # Tailstock with quill and live center.
    box(bm, (0.12, 0.18, AXIS_Z + 0.04 - BED_Z), (0.28, AXIS_Y, (BED_Z + AXIS_Z + 0.04) / 2), PAINT)
    cyl(bm, 0.024, 0.14, (0.20, AXIS_Y, AXIS_Z), "X", STEEL, segs=12)
    cyl(bm, 0.018, 0.03, (0.115, AXIS_Y, AXIS_Z), "X", STEEL, segs=12, r2=0.002)
    cyl(bm, 0.03, 0.08, (0.36, AXIS_Y, AXIS_Z), "X", IRON, segs=12)
    beam(bm, (0.30, -0.10, AXIS_Z + 0.02), (0.30, -0.15, AXIS_Z + 0.06), 0.01, 0.01, STEEL)  # lock lever

    # Carga motor behind the headstock, belt to the spindle pulley, cable down.
    cyl(bm, 0.065, 0.20, (MOTOR.x + 0.02, MOTOR.y, MOTOR.z), "X", IRON, segs=16)
    for dx in (-0.05, 0.02, 0.09):
        ring(bm, 0.068, 0.06, 0.025, (MOTOR.x + dx, MOTOR.y, MOTOR.z), "X", COPPER, segs=16)
    box(bm, (0.16, 0.12, 0.02), (MOTOR.x + 0.02, MOTOR.y, TRAY_Z + 0.005), IRON)
    box(bm, (0.05, 0.05, 0.05), (MOTOR.x + 0.04, MOTOR.y + 0.07, MOTOR.z + 0.02), IRON)
    beam(bm, (MOTOR.x + 0.04, MOTOR.y + 0.09, MOTOR.z + 0.02), (MOTOR.x + 0.04, 0.27, TRAY_Z), 0.015, 0.015, RUBBER)
    big_r, small_r = 0.06, 0.035
    ring(bm, big_r + 0.008, big_r, 0.025, (PULLEY_X, AXIS_Y, AXIS_Z), "X", RUBBER, segs=20)
    ring(bm, small_r + 0.008, small_r, 0.025, (PULLEY_X, MOTOR.y, MOTOR.z), "X", RUBBER, segs=16)
    a, b = Vector((PULLEY_X, AXIS_Y, AXIS_Z)), Vector((PULLEY_X, MOTOR.y, MOTOR.z))
    d = (b - a).normalized()
    nrm = Vector((0, -d.z, d.y))
    for s in (-1, 1):
        beam(bm, a + nrm * s * (big_r + 0.004), b + nrm * s * (small_r + 0.004), 0.025, 0.008, RUBBER)

    for kind, pt, nrm_, depth in PORTS:
        port(bm, pt, nrm_, kind, depth)
    return to_object(bm, "feLathe_Base", bevel=0.003)


def build_spindle():
    """Local coords: origin on the spindle axis at SPINDLE; spins around local X."""
    bm = bmesh.new()
    cyl(bm, 0.022, 0.30, (-0.13, 0, 0), "X", STEEL, segs=12)                # spindle shaft
    cyl(bm, 0.07, 0.05, (0.035, 0, 0), "X", IRON, segs=20)                  # chuck body
    ring(bm, 0.072, 0.06, 0.01, (0.06, 0, 0), "X", STEEL, segs=20)
    for k in range(3):                                                      # 3 jaws
        m = Matrix.Rotation(2 * math.pi * k / 3, 4, "X")
        box_m(bm, (0.04, 0.022, 0.035), Matrix.Translation(m @ Vector((0.075, 0, 0.045))) @ m, STEEL)
    # Workpiece: a stepped shaft being turned (looks like the "Eixo" being made).
    cyl(bm, 0.022, 0.12, (0.13, 0, 0), "X", STEEL, segs=14)
    cyl(bm, 0.016, 0.10, (0.24, 0, 0), "X", STEEL, segs=14)
    cyl(bm, 0.020, 0.02, (0.20, 0, 0), "X", RUST, segs=14)                  # rough, uncut band
    # Spindle pulley at the left end.
    cyl(bm, 0.06, 0.03, (PULLEY_X - SPINDLE.x, 0, 0), "X", IRON, segs=20)
    for dx in (-0.018, 0.018):
        cyl(bm, 0.068, 0.006, (PULLEY_X - SPINDLE.x + dx, 0, 0), "X", IRON, segs=20)
    return to_object(bm, "feLathe_Spindle", location=SPINDLE, bevel=0.002)


def build_motor_pulley():
    bm = bmesh.new()
    pos = Vector((PULLEY_X, MOTOR.y, MOTOR.z))
    cyl(bm, 0.012, 0.11, (0.06, 0, 0), "X", STEEL, segs=8)
    cyl(bm, 0.035, 0.03, (0, 0, 0), "X", IRON, segs=14)
    for dx in (-0.018, 0.018):
        cyl(bm, 0.043, 0.006, (dx, 0, 0), "X", IRON, segs=14)
    return to_object(bm, "feLathe_MotorPulley", location=pos, bevel=0.002)


def build_carriage():
    """Local coords: origin at CARRIAGE (on the rails); slides along local X."""
    bm = bmesh.new()
    box(bm, (0.15, 0.24, 0.03), (0, -0.01, 0.015), IRON)                    # saddle
    box(bm, (0.10, 0.16, 0.04), (0, -0.01, 0.05), PAINT)                    # cross slide
    box(bm, (0.05, 0.05, 0.05), (0, -0.07, 0.095), IRON)                    # tool post
    box(bm, (0.012, 0.05, 0.012), (0, -0.045, AXIS_Z - BED_Z - 0.006), STEEL)  # tool bit
    cyl(bm, 0.012, 0.03, (0, -0.07, 0.135), "Z", STEEL, segs=6)             # clamp bolt
    box(bm, (0.17, 0.04, 0.10), (0, -0.15, -0.015), PAINT)                  # apron (clears the tray)
    cyl(bm, 0.012, 0.04, (-0.03, -0.17, -0.03), "Y", STEEL, segs=8)         # crank shaft
    box(bm, (0.03, 0.02, 0.03), (0.05, -0.175, 0.0), BRASS)                 # feed lever
    return to_object(bm, "feLathe_Carriage", location=CARRIAGE, bevel=0.002)


def build_carriage_wheel(carriage):
    bm = bmesh.new()
    handwheel(bm, 0.045, "Y", STEEL)
    ob = to_object(bm, "feLathe_CarriageWheel")
    ob.location = CARRIAGE + Vector((-0.03, -0.195, -0.03))
    return ob


def build_tail_wheel():
    bm = bmesh.new()
    cyl(bm, 0.01, 0.04, (-0.02, 0, 0), "X", STEEL, segs=8)
    handwheel(bm, 0.05, "X", STEEL)
    return to_object(bm, "feLathe_TailWheel", location=TAIL_WHEEL)


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

    col = bpy.data.collections.get("feLathe") or bpy.data.collections.new("feLathe")
    if col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(col)

    base = build_base()
    carriage = build_carriage()
    cwheel = build_carriage_wheel(carriage)
    parts = [build_spindle(), build_motor_pulley(), carriage, build_tail_wheel()]
    for ob in [base] + parts + [cwheel]:
        col.objects.link(ob)
    bpy.context.view_layer.update()
    for child in parts:
        mw = child.matrix_world.copy()
        child.parent = base
        child.matrix_world = mw
    # Flat hierarchy on purpose: the FBX export (bake_space_transform) misplaces
    # grandchildren, so the crank is a child of the base and must follow the carriage.
    mw = cwheel.matrix_world.copy()
    cwheel.parent = base
    cwheel.matrix_world = mw
    add_port_empties("feLathe", base, col)

    bpy.context.view_layer.update()
    lo, hi, tris = Vector((1e9,) * 3), Vector((-1e9,) * 3), 0
    for ob in [base] + parts + [cwheel]:
        for v in ob.data.vertices:
            w = ob.matrix_world @ v.co
            lo, hi = Vector(map(min, lo, w)), Vector(map(max, hi, w))
        tris += sum(len(p.vertices) - 2 for p in ob.data.polygons)
    print("bbox min", tuple(round(c, 3) for c in lo), "max", tuple(round(c, 3) for c in hi))
    print("triangles (before bevel):", tris)


main()
