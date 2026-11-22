"""Builds the Foundry (M01, block feFoundry) in the open Blender scene.

Run inside Blender (Scripting tab, or through the Blender MCP server).
Units: 1 Blender unit = 1 m = 1 game block. Block feFoundry has MultiBlockDim="2,2,1"
(Config/blocks.xml): 2 wide (X) x 2 tall (Z) x 1 deep (Y). Origin at the floor center
of the footprint; the front faces -Y.

ART_BRIEF: "fornalha de tijolo + cadinho, chaminé curta". Left cell: brick furnace
bound with iron bands and corner angles, firebox door with glowing grate, clay crucible
of molten metal sunk in the top, short brick chimney. Right cell: casting table with
an ingot mold (two ingots still glowing, two cooled), ladle, tongs and finished ingots;
under it a leather bellows blowing into the furnace and an output bin.

Objects:
  feFoundry_Base        static (root)
  feFoundry_BellowsTop  bellows top board + handle; rotates around local Y (hinge at the nozzle)
  feFoundry_PortIn_1    conveyor input: ore/scrap (back of the furnace)
  feFoundry_PortIn_2    conveyor input: fuel (left side)
  feFoundry_PortOut_1   conveyor output: forged iron etc. (right side)

The scene is cleared of other objects first (except the default Camera/Light and
the fePreview* helpers): save the previous model before running this.
"""
import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

FX0, FX1 = -0.95, 0.02         # furnace X range
FY0, FY1 = -0.43, 0.43         # furnace Y range
FZ1 = 1.08                     # furnace top
FCX = (FX0 + FX1) / 2
CRUCIBLE = Vector((FCX + 0.06, -0.06, FZ1))
CHIMNEY = Vector((FX0 + 0.20, 0.24))
TABLE_Z = 0.74                 # casting table top
BELLOWS_HINGE = Vector((0.10, -0.12, 0.17))
rng = random.Random(3)

MATS = {
    "feFoundry_Brick":     ((0.45, 0.17, 0.10), 0.90, 0.00, 0.0),
    "feFoundry_BrickDark": ((0.33, 0.12, 0.08), 0.90, 0.00, 0.0),
    "feFoundry_Mortar":    ((0.55, 0.50, 0.44), 0.95, 0.00, 0.0),
    "feFoundry_Clay":      ((0.52, 0.29, 0.17), 0.90, 0.00, 0.0),
    "feFoundry_Iron":      ((0.15, 0.15, 0.16), 0.55, 0.85, 0.0),
    "feFoundry_Rust":      ((0.30, 0.13, 0.06), 0.80, 0.35, 0.0),
    "feFoundry_Steel":     ((0.55, 0.55, 0.57), 0.30, 1.00, 0.0),
    "feFoundry_Soot":      ((0.04, 0.04, 0.04), 0.90, 0.20, 0.0),
    "feFoundry_Wood":      ((0.30, 0.18, 0.09), 0.85, 0.00, 0.0),
    "feFoundry_Leather":   ((0.20, 0.11, 0.06), 0.75, 0.00, 0.0),
    "feFoundry_Glow":      ((1.00, 0.35, 0.05), 0.50, 0.00, 6.0),
    "feFoundry_Molten":    ((1.00, 0.55, 0.12), 0.30, 0.00, 12.0),
    "feFoundry_PortIn":    ((0.16, 0.48, 0.16), 0.60, 0.20, 0.0),
    "feFoundry_PortOut":   ((0.85, 0.45, 0.06), 0.60, 0.20, 0.0),
}
MI = {name: i for i, name in enumerate(MATS)}
(BRICK, BRICK2, MORTAR, CLAY, IRON, RUST, STEEL, SOOT, WOOD, LEATHER, GLOW, MOLTEN,
 PORT_IN, PORT_OUT) = (MI[n] for n in MATS)


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
# Ore/scrap in at the back of the furnace, fuel in on the left, products out on the right.
PORTS = [("In", (-0.5, 0.5, PORT_Z), (0, 1, 0), 0.07),
         ("In", (-1.0, 0.0, PORT_Z), (-1, 0, 0), 0.05),
         ("Out", (1.0, 0.0, PORT_Z), (1, 0, 0), 0.06)]

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
def brick_face(bm, origin, u, v, nrm, width, height, holes=(), bw=0.24, bh=0.08, depth=0.025):
    """Staggered brick courses on a face. origin = lower-left corner on the face; u, v = unit
    vectors along width/height; nrm = outward normal. holes = [(u0, u1, v0, v1)] left empty."""
    origin, u, v, nrm = Vector(origin), Vector(u), Vector(v), Vector(nrm)
    rot = Matrix((u, v, nrm)).transposed().to_4x4()
    rows = int(round(height / bh))
    rh = height / rows
    for r in range(rows):
        v0 = r * rh
        x = -bw / 2 if r % 2 else 0.0
        while x < width - 1e-6:
            a, b = max(x, 0.0), min(x + bw, width)
            x += bw
            if b - a < 0.02:
                continue
            cu, cv = (a + b) / 2, v0 + rh / 2
            if any(h0 <= cu <= h1 and g0 <= cv <= g1 for h0, h1, g0, g1 in holes):
                continue
            c = origin + u * cu + v * cv + nrm * (depth / 2 + rng.uniform(-0.002, 0.003))
            box_m(bm, (b - a - 0.008, rh - 0.008, depth), Matrix.Translation(c) @ rot,
                  BRICK if rng.random() < 0.7 else BRICK2)


def build_base():
    bm = bmesh.new()
    w, d = FX1 - FX0, FY1 - FY0
    # Furnace core (mortar shows in the brick joints) and brick skin on front, back and sides.
    box(bm, (w - 0.05, d - 0.05, FZ1 - 0.06), (FCX, 0, 0.06 + (FZ1 - 0.06) / 2), MORTAR)
    box(bm, (w + 0.02, d + 0.02, 0.06), (FCX, 0, 0.03), IRON)                       # plinth
    door_u = (0.30, w - 0.30)
    brick_face(bm, (FX0 + 0.025, FY0 + 0.025, 0.06), (1, 0, 0), (0, 0, 1), (0, -1, 0), w - 0.05,
               FZ1 - 0.06, holes=[(door_u[0] - 0.02, door_u[1] + 0.02, 0.0, 0.40)])
    brick_face(bm, (FX1 - 0.025, FY1 - 0.025, 0.06), (-1, 0, 0), (0, 0, 1), (0, 1, 0), w - 0.05,
               FZ1 - 0.06, holes=[(0.24, 0.73, 0.0, 0.32)])                          # port at the back
    brick_face(bm, (FX0 + 0.025, FY1 - 0.025, 0.06), (0, -1, 0), (0, 0, 1), (-1, 0, 0), d - 0.05,
               FZ1 - 0.06, holes=[(0.18, 0.67, 0.0, 0.32)])                          # port on the left
    brick_face(bm, (FX1 - 0.025, FY0 + 0.025, 0.06), (0, 1, 0), (0, 0, 1), (1, 0, 0), d - 0.05,
               FZ1 - 0.06)
    # Iron corner angles, bands and top plate.
    for x in (FX0, FX1):
        for y in (FY0, FY1):
            box(bm, (0.05, 0.05, FZ1), (x, y, FZ1 / 2), IRON)
    for z in (0.45, FZ1 - 0.04):
        for y in (FY0 - 0.003, FY1 + 0.003):
            box(bm, (w + 0.05, 0.012, 0.04), (FCX, y, z), RUST)
        for x in (FX0 - 0.003, FX1 + 0.003):
            box(bm, (0.012, d + 0.05, 0.04), (x, 0, z), RUST)
    box(bm, (w + 0.06, d + 0.06, 0.04), (FCX, 0, FZ1 + 0.02), IRON)
    # Firebox door with glowing grate, ash slot below.
    dx = FX0 + (door_u[0] + door_u[1]) / 2
    box(bm, (door_u[1] - door_u[0] + 0.06, 0.03, 0.34), (dx, FY0 - 0.01, 0.27), IRON)
    box(bm, (door_u[1] - door_u[0] - 0.06, 0.02, 0.18), (dx, FY0 - 0.025, 0.30), SOOT)
    for i in range(5):
        box(bm, (door_u[1] - door_u[0] - 0.10, 0.012, 0.012), (dx, FY0 - 0.035, 0.23 + i * 0.035), GLOW)
    for z in (0.16, 0.40):
        cyl(bm, 0.018, 0.05, (dx - 0.22, FY0 - 0.03, z), "Z", IRON, segs=8)
    box(bm, (0.09, 0.025, 0.025), (dx + 0.17, FY0 - 0.045, 0.30), STEEL)
    box(bm, (0.30, 0.02, 0.05), (dx, FY0 - 0.012, 0.10), SOOT)
    # Peep hole glowing on the front, higher up.
    cyl(bm, 0.035, 0.03, (dx + 0.20, FY0 - 0.01, 0.78), "Y", IRON, segs=12)
    cyl(bm, 0.022, 0.01, (dx + 0.20, FY0 - 0.026, 0.78), "Y", GLOW, segs=12)

    # Crucible sunk in the top: glowing ring, clay pot, molten metal, lid leaning beside.
    c = CRUCIBLE
    ring(bm, 0.20, 0.16, 0.012, (c.x, c.y, FZ1 + 0.041), "Z", GLOW, segs=24)
    cyl(bm, 0.155, 0.22, (c.x, c.y, FZ1 + 0.10), "Z", CLAY, segs=20, r2=0.13)
    ring(bm, 0.135, 0.115, 0.02, (c.x, c.y, FZ1 + 0.21), "Z", CLAY, segs=20)
    cyl(bm, 0.112, 0.01, (c.x, c.y, FZ1 + 0.214), "Z", MOLTEN, segs=20)   # above the pot's top cap
    box(bm, (0.035, 0.03, 0.02), (c.x + 0.14, c.y, FZ1 + 0.21), CLAY)        # pour lip
    cyl(bm, 0.15, 0.02, (c.x - 0.02, c.y + 0.24, FZ1 + 0.15), "Y", IRON, segs=20)  # lid on edge
    box(bm, (0.04, 0.03, 0.03), (c.x - 0.02, c.y + 0.235, FZ1 + 0.31), IRON)

    # Short brick chimney at the back-left with iron cap.
    z = FZ1 + 0.04
    course = 0
    while z < 1.60:
        h = 0.08
        box(bm, (0.26 + rng.uniform(-0.006, 0.006), 0.26, h - 0.008), (CHIMNEY.x, CHIMNEY.y, z + h / 2),
            BRICK if course % 3 else BRICK2, Matrix.Rotation(math.radians(rng.uniform(-2, 2)), 4, "Z"))
        z += h
        course += 1
    for sx in (-1, 1):
        box(bm, (0.30, 0.03, 0.03), (CHIMNEY.x, CHIMNEY.y + sx * 0.135, z + 0.015), IRON)
        box(bm, (0.03, 0.24, 0.03), (CHIMNEY.x + sx * 0.135, CHIMNEY.y, z + 0.015), IRON)
    box(bm, (0.18, 0.18, 0.012), (CHIMNEY.x, CHIMNEY.y, z + 0.03), SOOT)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(bm, (0.02, 0.02, 0.08), (CHIMNEY.x + sx * 0.11, CHIMNEY.y + sy * 0.11, z + 0.07), IRON)
    cyl(bm, 0.22, 0.06, (CHIMNEY.x, CHIMNEY.y, z + 0.14), "Z", SOOT, segs=4, r2=0.03)
    smoke_z = z + 0.06

    # Casting table (right cell) with ingot mold, ladle, tongs and finished ingots.
    tx0, tx1 = 0.12, 0.95
    tcx = (tx0 + tx1) / 2
    box(bm, (tx1 - tx0, 0.70, 0.04), (tcx, -0.04, TABLE_Z - 0.02), IRON)
    for x in (tx0 + 0.03, tx1 - 0.03):
        for y in (-0.36, 0.28):
            box(bm, (0.04, 0.04, TABLE_Z - 0.04), (x, y, (TABLE_Z - 0.04) / 2), IRON)
    box(bm, (tx1 - tx0 - 0.04, 0.03, 0.03), (tcx, 0.28, 0.12), IRON)
    mold_x, mold_y = 0.42, -0.10
    box(bm, (0.40, 0.30, 0.06), (mold_x, mold_y, TABLE_Z + 0.03), IRON)
    for i, kind in enumerate((MOLTEN, MOLTEN, SOOT, SOOT)):
        y = mold_y - 0.105 + i * 0.07
        box(bm, (0.30, 0.05, 0.006), (mold_x, y, TABLE_Z + 0.058), SOOT)     # cavity
        box(bm, (0.28, 0.045, 0.010), (mold_x, y, TABLE_Z + 0.058), kind)    # ingot, proud of the mold
    for i in range(6):                                                       # finished ingots
        layer, k = divmod(i, 3)
        box(bm, (0.24, 0.06, 0.04), (0.78, -0.24 + k * 0.08 + layer * 0.04, TABLE_Z + 0.02 + layer * 0.04),
            STEEL if (i % 2) else IRON, Matrix.Rotation(math.radians(90 * layer), 4, "Z"))
    # Ladle (bowl + long handle) and tongs.
    cyl(bm, 0.07, 0.07, (0.70, 0.14, TABLE_Z + 0.035), "Z", IRON, segs=14, r2=0.08)
    cyl(bm, 0.07, 0.005, (0.70, 0.14, TABLE_Z + 0.065), "Z", SOOT, segs=14)
    beam(bm, (0.63, 0.14, TABLE_Z + 0.05), (0.20, 0.20, TABLE_Z + 0.03), 0.02, 0.02, IRON)
    cyl(bm, 0.016, 0.10, (0.17, 0.205, TABLE_Z + 0.03), "X", WOOD, segs=8)
    for dy in (-0.012, 0.012):
        beam(bm, (0.30, 0.24 + dy, TABLE_Z + 0.008), (0.62, 0.25 + dy * 3, TABLE_Z + 0.008), 0.012, 0.012, IRON)

    # Bellows body (bottom board + leather) under the table, nozzle into the furnace side.
    hb = BELLOWS_HINGE
    box(bm, (0.42, 0.26, 0.025), (hb.x + 0.21, hb.y, hb.z - 0.11), WOOD)     # bottom board
    box(bm, (0.40, 0.24, 0.07), (hb.x + 0.20, hb.y, hb.z - 0.065), LEATHER)  # leather folds
    for z in (hb.z - 0.08, hb.z - 0.05):
        box(bm, (0.41, 0.25, 0.008), (hb.x + 0.205, hb.y, z), RUST)
    box(bm, (0.04, 0.04, 0.048), (hb.x + 0.38, hb.y, 0.024), WOOD)               # feet
    box(bm, (0.04, 0.04, 0.048), (hb.x + 0.03, hb.y, 0.024), WOOD)
    cyl(bm, 0.025, 0.12, (FX1 + 0.04, hb.y, hb.z - 0.06), "X", IRON, segs=10, r2=0.016)   # nozzle
    cyl(bm, 0.035, 0.02, (FX1 + 0.105, hb.y, hb.z - 0.06), "X", IRON, segs=10)

    # Output bin under the right end of the table.
    box(bm, (0.36, 0.48, 0.38), (0.76, 0.0, 0.25), IRON)
    box(bm, (0.37, 0.49, 0.02), (0.76, 0.0, 0.44), RUST)

    for kind, pt, nrm, depth in PORTS:
        port(bm, pt, nrm, kind, depth)
    # No bevel: with ~300 bricks it would triple the triangle count (~15k).
    return to_object(bm, "feFoundry_Base"), smoke_z


def build_bellows_top():
    """Local coords: origin on the hinge (local Y axis); the board opens upward at +X."""
    bm = bmesh.new()
    box(bm, (0.42, 0.26, 0.025), (0.21, 0, 0.0), WOOD)
    for x in (0.08, 0.20, 0.32):
        box(bm, (0.02, 0.27, 0.03), (x, 0, 0.004), RUST)
    beam(bm, (0.36, 0, 0.012), (0.44, -0.08, 0.32), 0.03, 0.03, WOOD)        # handle
    cyl(bm, 0.022, 0.12, (0.44, -0.08, 0.33), "Y", WOOD, segs=8)
    return to_object(bm, "feFoundry_BellowsTop", location=BELLOWS_HINGE, bevel=0.002)


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

    col = bpy.data.collections.get("feFoundry") or bpy.data.collections.new("feFoundry")
    if col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(col)

    base, smoke_z = build_base()
    bellows = build_bellows_top()
    for ob in (base, bellows):
        col.objects.link(ob)
    bpy.context.view_layer.update()
    mw = bellows.matrix_world.copy()
    bellows.parent = base
    bellows.matrix_world = mw
    add_port_empties("feFoundry", base, col)
    smoke = bpy.data.objects.new("feFoundry_SmokePoint", None)
    smoke.empty_display_type = "SINGLE_ARROW"
    smoke.empty_display_size = 0.2
    smoke.location = (CHIMNEY.x, CHIMNEY.y, smoke_z)
    col.objects.link(smoke)
    smoke.parent = base

    bpy.context.view_layer.update()
    lo, hi, tris = Vector((1e9,) * 3), Vector((-1e9,) * 3), 0
    for ob in (base, bellows):
        for v in ob.data.vertices:
            w = ob.matrix_world @ v.co
            lo, hi = Vector(map(min, lo, w)), Vector(map(max, hi, w))
        tris += sum(len(p.vertices) - 2 for p in ob.data.polygons)
    print("bbox min", tuple(round(c, 3) for c in lo), "max", tuple(round(c, 3) for c in hi))
    print("triangles (before bevel):", tris)
    print("smoke point", tuple(round(c, 3) for c in smoke.location))


main()
