"""Builds the Crank (E01, block feCrank) in the open Blender scene.

Run inside Blender (Scripting tab, or through the Blender MCP server).
Units: 1 Blender unit = 1 m = 1 game block. Footprint 1x1x1, origin at the
floor center. The front (where the player stands to turn the crank) faces -Y.

Objects:
  feCrank_Base          static frame, deck, bearings, dynamo body, belt
  feCrank_Rotor         axle + flywheel + pulley + crank; pivot on the axle (Y axis)
  feCrank_DynamoPulley  dynamo shaft + small pulley; pivot on its shaft (Y axis)
Both rotating parts are children of feCrank_Base and spin around local Y.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

AXLE_Z = 0.62          # crank axle height
BAT_POS = Vector((0.35, 0.0, 0.0))         # battery compartment center (x, y)
INS_POS = Vector((0.35, -0.10, 0.64))      # insulator tip; WireOffset (wire anchor) sits just above
DYN = Vector((0.0, 0.42, 0.17))   # dynamo pulley center
FRONT_Y, BACK_Y = -0.30, 0.30     # A-frames

# ---------------------------------------------------------------- materials
MATS = {
    "feCrank_Wood":    ((0.30, 0.18, 0.09), 0.85, 0.0),
    "feCrank_Iron":    ((0.16, 0.16, 0.17), 0.55, 0.85),
    "feCrank_Rust":    ((0.32, 0.14, 0.06), 0.80, 0.35),
    "feCrank_Copper":  ((0.72, 0.36, 0.20), 0.35, 1.0),
    "feCrank_Leather": ((0.10, 0.06, 0.04), 0.70, 0.0),
    "feCrank_PortIn":  ((0.16, 0.48, 0.16), 0.60, 0.20),
    "feCrank_PortOut": ((0.85, 0.45, 0.06), 0.60, 0.20),
    "feCrank_Battery": ((0.05, 0.05, 0.06), 0.50, 0.00),
    "feCrank_Porcelain": ((0.88, 0.87, 0.82), 0.25, 0.00),
    "feCrank_Red": ((0.65, 0.06, 0.05), 0.50, 0.00),
}
MI = {name: i for i, name in enumerate(MATS)}
WOOD, IRON, RUST, COPPER, LEATHER, PORT_IN, PORT_OUT, BATTERY, PORCELAIN, RED = (MI[n] for n in MATS)


def make_materials():
    for name, (rgb, rough, metal) in MATS.items():
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
    """Square beam from point a to point b (w across X-ish, t across the other side)."""
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
    verts = [v for lp in loops for v in lp]
    _finish(bm, n, mat, Matrix.Translation(loc) @ AXIS[axis], verts)


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
    # Deck: three planks plus two iron straps with bolts.
    for x in (-0.30, 0.0, 0.30):
        box(bm, (0.285, 0.92, 0.06), (x, 0, 0.03), WOOD)
    for y in (-0.40, 0.40):
        box(bm, (0.94, 0.05, 0.008), (0, y, 0.064), RUST)
        for x in (-0.40, -0.30, 0.0, 0.30, 0.40):
            cyl(bm, 0.011, 0.012, (x, y, 0.072), "Z", IRON, segs=6)
    # A-frames with cross bar and bearing block.
    for y in (FRONT_Y, BACK_Y):
        for s in (-1, 1):
            beam(bm, (s * 0.36, y, 0.06), (s * 0.05, y, 0.60), 0.07, 0.07, WOOD)
        out = -0.055 if y < 0 else 0.055
        box(bm, (0.50, 0.04, 0.06), (0, y + out, 0.30), WOOD)
        for s in (-1, 1):
            cyl(bm, 0.013, 0.02, (s * 0.21, y + out * 1.45, 0.30), "Y", IRON, segs=6)
        box(bm, (0.17, 0.10, 0.10), (0, y, AXLE_Z), IRON)
        box(bm, (0.19, 0.11, 0.015), (0, y, AXLE_Z + 0.055), RUST)
        for s in (-1, 1):
            cyl(bm, 0.012, 0.02, (s * 0.065, y, AXLE_Z + 0.07), "Z", IRON, segs=6)
        # Iron brackets where the legs meet the deck.
        for s in (-1, 1):
            box(bm, (0.10, 0.09, 0.012), (s * 0.34, y, 0.066), IRON)
    # Dynamo under the flywheel (its shaft and pulley spin: separate object).
    dy = 0.13
    cyl(bm, 0.085, 0.20, (0, dy, DYN.z), "Y", IRON, segs=20)
    for y in (dy - 0.105, dy + 0.105):
        cyl(bm, 0.092, 0.02, (0, y, DYN.z), "Y", RUST, segs=20)
    ring(bm, 0.090, 0.080, 0.035, (0, dy, DYN.z), "Y", COPPER, segs=20)
    box(bm, (0.17, 0.17, 0.045), (0, dy, 0.083), IRON)
    box(bm, (0.08, 0.06, 0.05), (0, dy, DYN.z + 0.105), IRON)
    for x in (-0.02, 0.02):
        cyl(bm, 0.008, 0.025, (x, dy, DYN.z + 0.14), "Z", COPPER, segs=6)
    box(bm, (0.06, 0.06, 0.05), (0, 0.33, DYN.z), RUST)          # rear shaft bearing
    box(bm, (0.08, 0.08, 0.10), (0, 0.33, 0.11), RUST)           # its stand
    # Leather belt between the big pulley and the dynamo pulley.
    big_r, small_r = 0.10, 0.045
    ring(bm, big_r + 0.01, big_r, 0.03, (0, DYN.y, AXLE_Z), "Y", LEATHER, segs=24)
    ring(bm, small_r + 0.01, small_r, 0.03, DYN, "Y", LEATHER, segs=16)
    for s in (-1, 1):
        beam(bm, (s * (small_r + 0.005), DYN.y, DYN.z),
             (s * (big_r + 0.005), DYN.y, AXLE_Z), 0.01, 0.03, LEATHER)
    # Battery compartment on the right side (D7: the crank charges car batteries, user 2026-11-22).
    bx, by = BAT_POS.x, BAT_POS.y
    box(bm, (0.24, 0.30, 0.02), (bx, by, 0.07), RUST)                       # floor plate
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(bm, (0.02, 0.02, 0.30), (bx + sx * 0.11, by + sy * 0.14, 0.22), IRON)   # corner posts
    for z in (0.20, 0.36):
        for sy in (-1, 1):
            box(bm, (0.24, 0.015, 0.02), (bx, by + sy * 0.14, z), IRON)
        for sx in (-1, 1):
            box(bm, (0.015, 0.30, 0.02), (bx + sx * 0.11, by, z), IRON)
    box(bm, (0.18, 0.24, 0.16), (bx, by, 0.16), BATTERY)                    # the car battery
    box(bm, (0.17, 0.23, 0.01), (bx, by, 0.245), RUST)                      # label band
    for sy, mat in ((-0.08, RED), (0.08, BATTERY)):
        cyl(bm, 0.015, 0.03, (bx, by + sy, 0.255), "Z", mat, segs=8)       # terminals
        cyl(bm, 0.011, 0.012, (bx, by + sy, 0.276), "Z", COPPER, segs=8)
    # Cables: dynamo -> battery (+), battery (-) -> frame.
    beam(bm, (0.0, 0.13, 0.255), (0.0, 0.13, 0.30), 0.02, 0.02, LEATHER)
    beam(bm, (0.0, 0.13, 0.30), (bx, by + 0.08, 0.29), 0.018, 0.018, RED)
    beam(bm, (bx, by - 0.08, 0.28), (bx - 0.11, by - 0.14, 0.36), 0.016, 0.016, LEATHER)
    # Transmitter: insulator post on the compartment's top frame; the wire attaches at its tip.
    tx, ty = INS_POS.x, INS_POS.y
    box(bm, (0.10, 0.06, 0.02), (tx, ty, 0.37), IRON)                       # bracket
    cyl(bm, 0.012, INS_POS.z - 0.37, (tx, ty, (INS_POS.z + 0.37) / 2), "Z", IRON, segs=8)
    for k in range(3):
        cyl(bm, 0.038, 0.02, (tx, ty, 0.45 + k * 0.05), "Z", PORCELAIN, segs=14, r2=0.026)
    cyl(bm, 0.022, 0.03, (tx, ty, INS_POS.z - 0.01), "Z", PORCELAIN, segs=12)
    cyl(bm, 0.014, 0.02, (tx, ty, INS_POS.z + 0.012), "Z", COPPER, segs=8)   # wire clamp
    beam(bm, (bx, by + 0.08, 0.28), (tx, ty, 0.40), 0.014, 0.014, RED)        # battery (+) -> insulator
    for kind, pt, nrm, depth in PORTS:
        port(bm, pt, nrm, kind, depth)
    return to_object(bm, "feCrank_Base", bevel=0.004)


def build_rotor():
    """Local coords: origin on the axle; spins around local Y."""
    bm = bmesh.new()
    cyl(bm, 0.025, 0.86, (0, 0.03, 0), "Y", IRON)                        # axle -0.40..0.46
    cyl(bm, 0.035, 0.02, (0, -0.40, 0), "Y", IRON, segs=6)               # front nut
    # Flywheel.
    ring(bm, 0.28, 0.235, 0.06, (0, 0, 0), "Y", IRON, segs=32)
    ring(bm, 0.285, 0.275, 0.064, (0, 0, 0), "Y", RUST, segs=32)
    cyl(bm, 0.06, 0.09, (0, 0, 0), "Y", IRON)
    for k in range(6):
        a = k * math.pi / 3
        m = Matrix.Rotation(a, 4, "Y") @ Matrix.Translation((0.15, 0, 0))
        n = len(bm.faces)
        r = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)
        _finish(bm, n, IRON, m @ Matrix.Diagonal((0.19, 0.03, 0.035, 1.0)), r["verts"])
    # Pulley behind the back frame.
    cyl(bm, 0.10, 0.05, (0, DYN.y, 0), "Y", IRON, segs=24)
    for y in (DYN.y - 0.03, DYN.y + 0.03):
        cyl(bm, 0.115, 0.01, (0, y, 0), "Y", IRON, segs=24)
    # Crank arm and handle at the front.
    arm_y, throw = -0.38, 0.20
    box(bm, (0.05, 0.03, throw), (0, arm_y, -throw / 2), RUST)
    cyl(bm, 0.03, 0.03, (0, arm_y, 0), "Y", RUST)
    cyl(bm, 0.03, 0.03, (0, arm_y, -throw), "Y", RUST)
    cyl(bm, 0.012, 0.11, (0, -0.44, -throw), "Y", IRON, segs=8)          # pin
    cyl(bm, 0.022, 0.08, (0, -0.45, -throw), "Y", WOOD, segs=12)         # grip
    cyl(bm, 0.026, 0.01, (0, -0.495, -throw), "Y", IRON, segs=12)        # end cap
    return to_object(bm, "feCrank_Rotor", location=(0, 0, AXLE_Z), bevel=0.003)


def build_dynamo_pulley():
    bm = bmesh.new()
    cyl(bm, 0.015, 0.20, (0, -0.09, 0), "Y", IRON, segs=10)
    cyl(bm, 0.045, 0.045, (0, 0, 0), "Y", IRON, segs=16)
    for y in (-0.026, 0.026):
        cyl(bm, 0.058, 0.008, (0, y, 0), "Y", IRON, segs=16)
    return to_object(bm, "feCrank_DynamoPulley", location=DYN, bevel=0.002)


# ---------------------------------------------------------------- conveyor ports
# Standard (Art/CONVEYOR_PORTS.md): opening 0.36 x 0.22 m centered 0.25 m above the
# floor, on the outer face of one block cell, flush with the block boundary; iron
# frame with the top bar painted green (input) or orange (output); a duct joins
# the face to the machine body. Each port also gets an empty <prefix>_Port{In|Out}_<n>
# on the face, its +Z pointing outward.
PORT_W, PORT_H, PORT_Z, PORT_FRAME = 0.36, 0.22, 0.25, 0.045


def box_m(bm, size, matrix, mat):
    """Unit cube scaled by size, then placed by a full 4x4 matrix."""
    r = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)
    _finish(bm, 0, mat, matrix @ Matrix.Diagonal((*size, 1.0)), r["verts"])


def _port_frame(pt, normal):
    """Local frame on the block face: X' along the face, Y' outward, Z' up."""
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
    for s in (-1, 1):   # duct from the face back to the machine body
        box_m(bm, (0.02, d, PORT_H + 0.04), m @ T((s * (hw + 0.01), -d / 2, 0)), IRON)
        box_m(bm, (PORT_W + 0.04, d, 0.02), m @ T((0, -d / 2, s * (hh + 0.01))), IRON)
    box_m(bm, (PORT_W, 0.02, PORT_H), m @ T((0, -d + 0.01, 0)), PORT_DARK)
    for s in (-1, 1):   # frame flush with the block face
        box_m(bm, (fw, 0.04, PORT_H + 2 * fw), m @ T((s * (hw + fw / 2), -0.02, 0)), IRON)
    box_m(bm, (PORT_W + 2 * fw, 0.04, fw), m @ T((0, -0.02, -(hh + fw / 2))), IRON)
    box_m(bm, (PORT_W + 2 * fw, 0.04, fw), m @ T((0, -0.02, hh + fw / 2)),
          PORT_IN if kind == "In" else PORT_OUT)
    if kind == "In":    # chute floor sloping down into the machine
        c = min(d, 0.12)
        box_m(bm, (PORT_W - 0.01, c, 0.012),
              m @ T((0, -c / 2, -hh + 0.03)) @ Matrix.Rotation(math.radians(12), 4, "X"), IRON)
    else:               # hinged flap over the upper part of the opening
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

# Output only: Carga (feCharge) leaves through a collector box on the right side.
# No conveyor port: the crank's output is electricity (wire from the insulator), not items.
PORTS = []
PORT_DARK = LEATHER


# ---------------------------------------------------------------- scene
def main():
    for ob in list(bpy.data.objects):
        if ob.name.startswith("feCrank") or ob.name.startswith("WireOffset") or ob.name == "Cube":
            bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    make_materials()

    col = bpy.data.collections.get("feCrank")
    if not col:
        col = bpy.data.collections.new("feCrank")
        bpy.context.scene.collection.children.link(col)

    base = build_base()
    rotor = build_rotor()
    pulley = build_dynamo_pulley()
    for ob in (base, rotor, pulley):
        col.objects.link(ob)
    for child in (rotor, pulley):
        child.parent = base
        child.matrix_parent_inverse = base.matrix_world.inverted()

    add_port_empties("feCrank", base, col)
    wire = bpy.data.objects.new("WireOffset", None)   # name read by TileEntityPowered.set_BlockTransform
    wire.empty_display_type = "SPHERE"
    wire.empty_display_size = 0.03
    wire.location = INS_POS + Vector((0, 0, 0.03))
    col.objects.link(wire)
    wire.parent = base

    bpy.context.view_layer.update()
    lo = Vector((1e9,) * 3)
    hi = Vector((-1e9,) * 3)
    tris = 0
    for ob in (base, rotor, pulley):
        for v in ob.data.vertices:
            w = ob.matrix_world @ v.co
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
        tris += sum(len(p.vertices) - 2 for p in ob.data.polygons)
    print("bbox min", tuple(round(c, 3) for c in lo), "max", tuple(round(c, 3) for c in hi))
    print("triangles (before bevel):", tris)


main()
