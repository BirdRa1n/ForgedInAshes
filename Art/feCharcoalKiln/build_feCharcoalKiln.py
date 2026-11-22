"""Builds the Charcoal Kiln (E02, block feCharcoalKiln) in the open Blender scene.

Run inside Blender (Scripting tab, or through the Blender MCP server).
Units: 1 Blender unit = 1 m = 1 game block. Footprint 2 (X) x 1 (Y) x 2 (Z) blocks,
origin at the floor center of the footprint. The front faces -Y.

Layout: a stone barrel-vault kiln (vault axis along Y) on a stone plinth, with an
arched iron door and glowing air vents on the front, a brick chimney at the back,
iron tie rods, and a woodpile on the right (what goes in: Wood -> Charcoal).

Objects:
  feKiln_Base        everything (nothing moves)
  feKiln_SmokePoint  empty at the chimney mouth, for a smoke particle effect

The scene is cleared of other objects first (except the default Camera/Light and
the fePreview* helpers): save the previous model before running this.
"""
import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

KX = -0.35                 # kiln center X
R_OUT, R_IN = 0.58, 0.46   # vault radii
Z0, SPRING = 0.12, 0.40    # plinth top, vault springline
Y_FRONT, Y_BACK = -0.32, 0.32
WALL = 0.08               # end wall thickness
CHIMNEY = Vector((KX, 0.24))
rng = random.Random(7)

# ---------------------------------------------------------------- materials
MATS = {
    "feKiln_Stone":     ((0.42, 0.40, 0.37), 0.90, 0.0, 0.0),
    "feKiln_StoneDark": ((0.30, 0.29, 0.27), 0.90, 0.0, 0.0),
    "feKiln_Clay":      ((0.52, 0.29, 0.17), 0.90, 0.0, 0.0),
    "feKiln_Iron":      ((0.15, 0.15, 0.16), 0.55, 0.85, 0.0),
    "feKiln_Soot":      ((0.04, 0.04, 0.04), 0.90, 0.20, 0.0),
    "feKiln_Glow":      ((1.00, 0.35, 0.05), 0.50, 0.00, 6.0),
    "feKiln_Bark":      ((0.22, 0.14, 0.08), 0.90, 0.00, 0.0),
    "feKiln_WoodCut":   ((0.62, 0.45, 0.28), 0.80, 0.00, 0.0),
}
MI = {name: i for i, name in enumerate(MATS)}
STONE, STONE2, CLAY, IRON, SOOT, GLOW, BARK, WOODCUT = (MI[n] for n in MATS)


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


def box(bm, size, loc, mat, rot=Matrix.Identity(4)):
    r = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)
    _finish(bm, mat, Matrix.Translation(loc) @ rot @ Matrix.Diagonal((*size, 1.0)), r["verts"])


def box_m(bm, size, matrix, mat):
    """Unit cube scaled by size, then placed by a full 4x4 matrix."""
    r = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)
    _finish(bm, mat, matrix @ Matrix.Diagonal((*size, 1.0)), r["verts"])


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


def arch_slab(bm, half_w, rect_h, thick, x, y0, z0, mat, segs=12):
    """Rectangle with a semicircular top, in the XZ plane, extruded from y0 to y0+thick."""
    outline = [(-half_w, 0.0)]
    for i in range(segs + 1):
        a = math.pi - math.pi * i / segs
        outline.append((half_w * math.cos(a), rect_h + half_w * math.sin(a)))
    outline.append((half_w, 0.0))
    front = [bm.verts.new((x + px, y0, z0 + pz)) for px, pz in outline]
    back = [bm.verts.new((x + px, y0 + thick, z0 + pz)) for px, pz in outline]
    faces = [bm.faces.new(front), bm.faces.new(list(reversed(back)))]
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((front[i], back[i], back[j], front[j])))
    for f in faces:
        f.material_index = mat


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


def stone_mat():
    return STONE if rng.random() < 0.65 else STONE2


# ---------------------------------------------------------------- parts
def build_base():
    bm = bmesh.new()
    # Plinth.
    box(bm, (1.24, 0.94, Z0), (KX, 0, Z0 / 2), STONE2)

    # Side walls: two courses of stone blocks up to the springline.
    course_h = (SPRING - Z0) / 2
    n_along = 5
    seg = (Y_BACK - Y_FRONT) / n_along
    for side in (-1, 1):
        xc = KX + side * (R_IN + R_OUT) / 2
        for c in range(2):
            off = seg / 2 if c % 2 else 0.0
            ys = [Y_FRONT + off + seg * (i + 0.5) for i in range(n_along)]
            for y in ys:
                if y + seg / 2 > Y_BACK + 1e-6:
                    y = Y_BACK - seg / 4
                    length = seg / 2
                else:
                    length = seg
                box(bm, (R_OUT - R_IN + rng.uniform(-0.01, 0.01), length - 0.008, course_h - 0.008),
                    (xc + rng.uniform(-0.006, 0.006), y, Z0 + course_h * (c + 0.5)), stone_mat())

    # Barrel vault: rings of voussoirs along Y, staggered bond.
    n_rings, n_stones = 6, 9
    ring_d = (Y_BACK - Y_FRONT) / n_rings
    thick = R_OUT - R_IN
    for k in range(n_rings):
        y = Y_FRONT + ring_d * (k + 0.5)
        stagger = 0.5 if k % 2 else 0.0
        for i in range(n_stones + (1 if stagger else 0)):
            a0 = (i - stagger) * math.pi / n_stones
            a1 = a0 + math.pi / n_stones
            a0, a1 = max(a0, 0.0), min(a1, math.pi)
            if a1 - a0 < 1e-3:
                continue
            a = (a0 + a1) / 2
            span = (a1 - a0) * (R_IN + R_OUT) / 2
            rad = (R_IN + R_OUT) / 2 + rng.uniform(-0.008, 0.012)
            m = (Matrix.Translation((KX, y, SPRING))
                 @ Matrix.Rotation(-a, 4, "Y")
                 @ Matrix.Translation((rad, 0, 0)))
            box_m(bm, (thick, ring_d - 0.008, span - 0.008), m, stone_mat())
    # Clay plaster along the crest.
    box(bm, (0.22, Y_BACK - Y_FRONT + 0.02, 0.035), (KX, 0, SPRING + R_OUT + 0.005), CLAY)

    # End walls (front with door, back with chimney), clay-plastered.
    arch_slab(bm, R_OUT + 0.02, SPRING - Z0, WALL, KX, Y_FRONT - WALL, Z0, CLAY, segs=16)
    arch_slab(bm, R_OUT + 0.02, SPRING - Z0, WALL, KX, Y_BACK, Z0, CLAY, segs=16)
    # Stone arch ring framing each end wall.
    for y in (Y_FRONT - WALL / 2, Y_BACK + WALL / 2):
        for i in range(11):
            a = math.pi * (i + 0.5) / 11
            m = (Matrix.Translation((KX, y, SPRING)) @ Matrix.Rotation(-a, 4, "Y")
                 @ Matrix.Translation((R_OUT + 0.02, 0, 0)))
            box_m(bm, (0.07, WALL + 0.015, 0.15), m, stone_mat())

    # Front: soot frame, arched iron door with rivets and handle, glow under the door.
    yf = Y_FRONT - WALL
    arch_slab(bm, 0.24, 0.26, 0.02, KX, yf - 0.02, Z0 + 0.02, SOOT, segs=12)
    arch_slab(bm, 0.20, 0.24, 0.03, KX, yf - 0.05, Z0 + 0.05, IRON, segs=12)
    for s in (-1, 1):
        for z in (Z0 + 0.12, Z0 + 0.30):
            cyl(bm, 0.022, 0.06, (KX + s * 0.20, yf - 0.035, z), "Z", IRON, segs=8)   # hinges/latch
        for z in (Z0 + 0.10, Z0 + 0.20, Z0 + 0.30):
            cyl(bm, 0.011, 0.012, (KX + s * 0.16, yf - 0.056, z), "Y", IRON, segs=6)
    box(bm, (0.14, 0.02, 0.02), (KX, yf - 0.07, Z0 + 0.27), IRON)
    cyl(bm, 0.03, 0.02, (KX, yf - 0.06, Z0 + 0.45), "Y", IRON, segs=10)            # peephole
    cyl(bm, 0.02, 0.01, (KX, yf - 0.072, Z0 + 0.45), "Y", GLOW, segs=10)
    box(bm, (0.34, 0.012, 0.016), (KX, yf - 0.055, Z0 + 0.04), GLOW)                # under the door
    for s in (-1, 1):                                                                # air vents
        box(bm, (0.09, 0.02, 0.07), (KX + s * 0.42, yf - 0.005, Z0 + 0.10), SOOT)
        box(bm, (0.06, 0.01, 0.04), (KX + s * 0.42, yf - 0.012, Z0 + 0.10), GLOW)

    # Iron tie rods across the front and back with anchor plates.
    for y in (Y_FRONT - WALL - 0.025, Y_BACK + WALL + 0.025):
        cyl(bm, 0.012, 1.26, (KX, y, SPRING), "X", IRON, segs=8)
        for s in (-1, 1):
            box(bm, (0.02, 0.05, 0.12), (KX + s * 0.62, y, SPRING), IRON)
    for s in (-1, 1):
        cyl(bm, 0.012, Y_BACK - Y_FRONT + 2 * WALL + 0.05, (KX + s * 0.62, 0, SPRING), "Y", IRON, segs=8)

    # Brick chimney at the back of the crest, with iron cap.
    z = SPRING + R_OUT - 0.08
    course = 0
    while z < 1.70:
        h = 0.095
        rot = Matrix.Rotation(math.radians(rng.uniform(-2, 2)), 4, "Z")
        box(bm, (0.24 + rng.uniform(-0.006, 0.006), 0.24, h - 0.008),
            (CHIMNEY.x, CHIMNEY.y, z + h / 2), CLAY if course % 3 else STONE2, rot)
        z += h
        course += 1
    for s in (-1, 1):   # open iron collar around the mouth
        box(bm, (0.30, 0.04, 0.03), (CHIMNEY.x, CHIMNEY.y + s * 0.13, z + 0.015), IRON)
        box(bm, (0.04, 0.22, 0.03), (CHIMNEY.x + s * 0.13, CHIMNEY.y, z + 0.015), IRON)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(bm, (0.02, 0.02, 0.09), (CHIMNEY.x + sx * 0.12, CHIMNEY.y + sy * 0.12, z + 0.075), IRON)
    cyl(bm, 0.24, 0.07, (CHIMNEY.x, CHIMNEY.y, z + 0.155), "Z", SOOT, segs=4, r2=0.03)
    box(bm, (0.16, 0.16, 0.012), (CHIMNEY.x, CHIMNEY.y, z + 0.035), SOOT)        # soot in the mouth
    top = z

    # Woodpile on the right, held by two stakes.
    logs = [(0.41, 0.075), (0.56, 0.075), (0.71, 0.075), (0.86, 0.075),
            (0.485, 0.205), (0.635, 0.205), (0.785, 0.205),
            (0.56, 0.335), (0.71, 0.335), (0.635, 0.465)]
    for x, zc in logs:
        r = 0.068 + rng.uniform(-0.006, 0.006)
        length = 0.80 + rng.uniform(-0.05, 0.03)
        yc = rng.uniform(-0.03, 0.03)
        cyl(bm, r, length, (x, yc, zc), "Y", BARK, segs=8)
        for s in (-1, 1):
            cyl(bm, r - 0.008, 0.008, (x, yc + s * (length / 2 + 0.002), zc), "Y", WOODCUT, segs=8)
    for x in (0.31, 0.95):
        beam(bm, (x, 0.0, 0.01), (x + (0.03 if x < 0.5 else -0.03), 0.0, 0.52), 0.04, 0.04, BARK)
    return to_object(bm, "feKiln_Base", bevel=0.004), top


# ---------------------------------------------------------------- scene
def main():
    keep = {"Camera", "Light"}
    for ob in list(bpy.data.objects):
        if ob.name not in keep and not ob.name.startswith("fePreview"):
            bpy.data.objects.remove(ob, do_unlink=True)
    for coll in list(bpy.data.collections):
        if coll.name != "feCharcoalKiln" and not coll.objects and not coll.children:
            bpy.data.collections.remove(coll)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    for m in list(bpy.data.materials):
        if m.users == 0:
            bpy.data.materials.remove(m)
    make_materials()

    col = bpy.data.collections.get("feCharcoalKiln")
    if not col:
        col = bpy.data.collections.new("feCharcoalKiln")
        bpy.context.scene.collection.children.link(col)

    base, chimney_top = build_base()
    col.objects.link(base)
    smoke = bpy.data.objects.new("feKiln_SmokePoint", None)
    smoke.empty_display_type = "SINGLE_ARROW"
    smoke.empty_display_size = 0.2
    smoke.location = (CHIMNEY.x, CHIMNEY.y, chimney_top + 0.05)
    col.objects.link(smoke)
    smoke.parent = base

    bpy.context.view_layer.update()
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for v in base.data.vertices:
        w = base.matrix_world @ v.co
        lo, hi = Vector(map(min, lo, w)), Vector(map(max, hi, w))
    print("bbox min", tuple(round(c, 3) for c in lo), "max", tuple(round(c, 3) for c in hi))
    print("triangles (before bevel):", sum(len(p.vertices) - 2 for p in base.data.polygons))
    print("smoke point", tuple(round(c, 3) for c in smoke.location))


main()
