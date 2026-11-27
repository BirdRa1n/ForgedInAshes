"""HD remake of seven blocks in a 7 Days to Die look (scrap-industrial: riveted plate, firebrick, cast iron, rust).

Run headless, one model per call (saves Art/<block>/hd/<block>_src.blend, then F:\\IA texturizar bakes it):
    blender -b --factory-startup --python Art/feHD/build_feHD.py -- <block>
    blocks: feM_Foundry feMetalChute feCaster feShaft feCondenser fePipe feMechPump

Every contract of the original models (Art/feKinetic/build_feKinetic.py) is kept: object names, pivots, axes,
port heights and flange sizes (FeArm_*, FeSpin_*, FeCastMetal, FeCastReady, FeLevelGas, FeLevelLiquid, FeFan_*,
WireOffset). Units: 1 m = 1 block, origin at the floor centre, front = Blender -Y.

New effect contract (read by Art/UnityProject/Assets/Editor/FeBuild.cs and src/ForgedInAshes/FxVisual.cs):
  materials  feHD_Molten  glowing metal (emission = metal colour, scrolls while it flows, dark crust when cold)
             feHD_Liquid  fluid seen through sight glasses (colour = the fluid in it)
             feHD_Gas     translucent steam chamber
             feHD_Glow    fire glow (on while the machine burns / works)
  objects    FePour_<n>   falling stream of molten metal (shown while metal flows there)
             FeFx_Steam_<n>, FeFx_Smoke_<n>, FeFx_Sparks_<n>  empties: particle emitters (+Z local = Blender +Z up)
Faces with an effect material are not baked into the atlas (F:\\IA\\fe_blender\\texturizar_pbr.py keeps them).
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

ART = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = 0.5
SHAFT_R, FLANGE_R, PIPE_R = 0.06, 0.10, 0.085

# name: (rgb, roughness, metallic, emission)
MATS = {
    "feHD_Iron":      ((0.13, 0.13, 0.14), 0.55, 0.80, 0),
    "feHD_CastIron":  ((0.18, 0.18, 0.18), 0.70, 0.70, 0),
    "feHD_Steel":     ((0.45, 0.46, 0.48), 0.35, 0.95, 0),
    "feHD_Rust":      ((0.32, 0.15, 0.07), 0.85, 0.30, 0),
    "feHD_Paint":     ((0.26, 0.31, 0.20), 0.70, 0.20, 0),    # faded olive (7DTD industrial)
    "feHD_Hazard":    ((0.75, 0.55, 0.08), 0.65, 0.10, 0),    # worn safety yellow
    "feHD_Brick":     ((0.45, 0.20, 0.12), 0.90, 0.00, 0),
    "feHD_Soot":      ((0.05, 0.05, 0.05), 0.90, 0.10, 0),
    "feHD_Sand":      ((0.20, 0.19, 0.17), 0.95, 0.00, 0),
    "feHD_Brass":     ((0.70, 0.52, 0.22), 0.35, 1.00, 0),
    "feHD_Copper":    ((0.70, 0.36, 0.20), 0.35, 1.00, 0),
    "feHD_Wood":      ((0.30, 0.19, 0.10), 0.85, 0.00, 0),
    "feHD_Glass":     ((0.06, 0.07, 0.07), 0.08, 0.00, 0),
    "feHD_In":        ((0.16, 0.48, 0.16), 0.60, 0.20, 0),
    "feHD_Out":       ((0.85, 0.45, 0.06), 0.60, 0.20, 0),
    "feHD_Molten":    ((1.00, 0.42, 0.08), 0.40, 0.00, 8.0),
    "feHD_Liquid":    ((0.10, 0.30, 0.45), 0.03, 0.00, 0),
    "feHD_Gas":       ((0.90, 0.92, 0.95), 0.60, 0.00, 0),
    "feHD_Glow":      ((1.00, 0.35, 0.05), 0.50, 0.00, 6.0),
    "feHD_Red":       ((0.45, 0.07, 0.05), 0.65, 0.20, 0),    # handwheels, gas bottles, pressure bands
    "feHD_Leather":   ((0.36, 0.22, 0.12), 0.85, 0.00, 0),    # hides
    "feHD_Leaf":      ((0.22, 0.48, 0.12), 0.60, 0.00, 0),    # plants (Hydroponic Tower)
    "feHD_Concrete":  ((0.42, 0.41, 0.38), 0.90, 0.00, 0),    # platforms, pads, foundations (D14)
    "feHD_Ballast":   ((0.30, 0.28, 0.25), 0.95, 0.00, 0),    # track ballast (D14)
}
MI = {n: i for i, n in enumerate(MATS)}
(IRON, CAST, STEEL, RUST, PAINT, HAZ, BRICK, SOOT, SAND, BRASS, COPPER, WOOD, GLASS, IN, OUT,
 MOLTEN, LIQUID, GAS, GLOW, RED, LEATHER, LEAF, CONCRETE, BALLAST) = range(len(MATS))

AXIS = {"Z": Matrix.Identity(4), "Y": Matrix.Rotation(math.pi / 2, 4, "X"), "X": Matrix.Rotation(math.pi / 2, 4, "Y")}


def make_materials():
    for name, (rgb, rough, metal, emit) in MATS.items():
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.use_nodes = True
        b = m.node_tree.nodes.get("Principled BSDF")
        b.inputs["Base Color"].default_value = (*rgb, 1)
        b.inputs["Roughness"].default_value = rough
        b.inputs["Metallic"].default_value = metal
        if emit:
            b.inputs["Emission Color"].default_value = (*rgb, 1)
            b.inputs["Emission Strength"].default_value = emit
        m.diffuse_color = (*rgb, 1)


# ---------------------------------------------------------------- bmesh helpers
def _fin(bm, mat, mtx, verts):
    bmesh.ops.transform(bm, matrix=mtx, verts=verts)
    for f in {f for v in verts for f in v.link_faces}:
        f.material_index = mat


# Anti z-fighting (2026-11-24, user: "parts flicker as I move"): primitives built flush with each other had faces in
# exactly the same plane (crossing ribs, plates on plates, strips on walls). Every primitive now grows by a small
# amount that differs from its neighbours' (0 .. 4.8 mm, never more than a quarter of its thinnest side), so no two
# faces coincide any more. Deterministic: the counter restarts for every model (build()).
_JIT = [0]


def _j(smallest):
    _JIT[0] += 1
    return min(0.0012 * (_JIT[0] % 5), 0.25 * max(smallest, 0.0))


def box(bm, size, loc, mat, rot=None):
    j = _j(min(size))
    size = (size[0] + j, size[1] + j, size[2] + j)
    r = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)
    _fin(bm, mat, Matrix.Translation(loc) @ (rot or Matrix.Identity(4)) @ Matrix.Diagonal((*size, 1)), r["verts"])


def beam(bm, a, b, w, t, mat):
    a, b = Vector(a), Vector(b)
    d = b - a
    box(bm, (w, t, d.length), (a + b) / 2, mat, d.to_track_quat("Z", "Y").to_matrix().to_4x4())


def cyl(bm, r, depth, loc, axis, mat, segs=16, r2=None, rot=None):
    j = _j(min(r, depth))
    r += j / 2
    r2 = None if r2 is None else r2 + j / 2
    depth += j
    res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r,
                                radius2=r if r2 is None else r2, depth=depth, calc_uvs=True)
    _fin(bm, mat, Matrix.Translation(loc) @ (rot or Matrix.Identity(4)) @ AXIS[axis], res["verts"])


def ring(bm, ro, ri, depth, loc, axis, mat, segs=24):
    j = _j(min(ro - ri, depth))
    ro += j / 2
    ri -= j / 2
    depth += j
    loops = []
    for rad, z in ((ro, -depth / 2), (ro, depth / 2), (ri, depth / 2), (ri, -depth / 2)):
        loops.append([bm.verts.new((rad * math.cos(2 * math.pi * i / segs), rad * math.sin(2 * math.pi * i / segs), z))
                      for i in range(segs)])
    for k in range(4):
        la, lb = loops[k], loops[(k + 1) % 4]
        for i in range(segs):
            j = (i + 1) % segs
            bm.faces.new((la[i], la[j], lb[j], lb[i]))
    _fin(bm, mat, Matrix.Translation(loc) @ AXIS[axis], [v for lp in loops for v in lp])


def gear(bm, r, depth, teeth, loc, axis, mat, tooth=0.025):
    cyl(bm, r, depth, loc, axis, mat, segs=max(12, teeth))
    for k in range(teeth):
        a = 2 * math.pi * k / teeth
        m = Matrix.Translation(loc) @ AXIS[axis] @ Matrix.Rotation(a, 4, "Z") @ Matrix.Translation((r + tooth / 2, 0, 0))
        rr = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)
        _fin(bm, mat, m @ Matrix.Diagonal((tooth, tooth * 1.1, depth * 0.9, 1)), rr["verts"])


def rivets(bm, a, b, n, mat=IRON, r=0.011, axis="Y", segs=6):
    """n rivet heads on the line a..b; axis = the normal of the plate they sit on."""
    a, b = Vector(a), Vector(b)
    for k in range(n):
        p = a.lerp(b, (k + 0.5) / n)
        cyl(bm, r, 0.012, p, axis, mat, segs=segs)


def bolt_circle(bm, n, rad, center, axis, mat=IRON, r=0.011, d=0.018):
    c = Vector(center)
    for k in range(n):
        a = 2 * math.pi * k / n + math.pi / n
        if axis == "Y":
            off = Vector((rad * math.cos(a), 0, rad * math.sin(a)))
        elif axis == "X":
            off = Vector((0, rad * math.cos(a), rad * math.sin(a)))
        else:
            off = Vector((rad * math.cos(a), rad * math.sin(a), 0))
        cyl(bm, r, d, c + off, axis, mat, segs=6)


def flange(bm, center, axis, ring_mat=None, r=PIPE_R + 0.03, bolts=6):
    """Pipe flange with bolts; flush with the block face at `center`."""
    cyl(bm, r, 0.03, center, axis, IRON, segs=18)
    bolt_circle(bm, bolts, r - 0.018, center, axis, STEEL, r=0.008, d=0.04)
    if ring_mat is not None:
        ring(bm, r + 0.006, r - 0.012, 0.034, center, axis, ring_mat, segs=18)


def plate(bm, size, loc, mat, rivet_axis, n=4, rot=None):
    """A riveted plate: box plus rivets along its two long edges on the outward face."""
    box(bm, size, loc, mat, rot)
    sx, sy, sz = size
    L = Vector(loc)
    if rivet_axis == "-Y":
        y = L.y - sy / 2 - 0.004
        for z in (L.z - sz / 2 + 0.03, L.z + sz / 2 - 0.03):
            rivets(bm, (L.x - sx / 2 + 0.02, y, z), (L.x + sx / 2 - 0.02, y, z), n)
    elif rivet_axis == "+Y":
        y = L.y + sy / 2 + 0.004
        for z in (L.z - sz / 2 + 0.03, L.z + sz / 2 - 0.03):
            rivets(bm, (L.x - sx / 2 + 0.02, y, z), (L.x + sx / 2 - 0.02, y, z), n)
    elif rivet_axis in ("-X", "+X"):
        x = L.x + (sx / 2 + 0.004) * (1 if rivet_axis == "+X" else -1)
        for z in (L.z - sz / 2 + 0.03, L.z + sz / 2 - 0.03):
            rivets(bm, (x, L.y - sy / 2 + 0.02, z), (x, L.y + sy / 2 - 0.02, z), n, axis="X")


def hazard(bm, length, loc, along="X", h=0.05, n=8, t=0.012):
    """Yellow/black hazard stripe band made of alternating blocks."""
    L = Vector(loc)
    step = length / n
    for k in range(n):
        off = -length / 2 + step * (k + 0.5)
        p = L + (Vector((off, 0, 0)) if along == "X" else Vector((0, off, 0)))
        size = (step, t, h) if along == "X" else (t, step, h)
        box(bm, size, p, HAZ if k % 2 == 0 else SOOT)


def stream(p0, p1, drop_curve=2.0, r0=0.020, r1=0.011, rings=16, segs=10, wobble=0.004, lead=0.0):
    """A falling stream of molten metal as a tapered tube, in coordinates relative to its object's origin.
    p0 = the lip, p1 = where it lands. Horizontal motion is linear, the fall goes with s^drop_curve (a ballistic
    arc: it leaves the lip almost level and bends down). It thins as it speeds up (r0 -> r1) and wobbles a bit.
    UV: u around, v DEcreasing along the length, so FxVisual's growing offset makes the texture run downward.
    `lead` > 0 adds a short bulge at the lip (the metal curling over the edge)."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()
    p0, p1 = Vector(p0), Vector(p1)
    pts = []
    for i in range(rings + 1):
        s = i / rings
        p = Vector((p0.x + (p1.x - p0.x) * s, p0.y + (p1.y - p0.y) * s, p0.z + (p1.z - p0.z) * (s ** drop_curve)))
        p.x += wobble * math.sin(s * 9.0) * s
        pts.append(p)
    length = [0.0]
    for i in range(1, len(pts)):
        length.append(length[-1] + (pts[i] - pts[i - 1]).length)
    total = length[-1]
    rings_v = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, rings)] - pts[max(i - 1, 0)]).normalized()
        side = Vector((1, 0, 0)) if abs(t.x) < 0.9 else Vector((0, 1, 0))
        n1 = t.cross(side).normalized()
        n2 = t.cross(n1).normalized()
        s = i / rings
        r = r0 + (r1 - r0) * s ** 0.7 + (lead * (1 - s) ** 6)
        ring_ = []
        for j in range(segs):
            a = 2 * math.pi * j / segs
            ring_.append(bm.verts.new(p + (n1 * math.cos(a) + n2 * math.sin(a)) * r))
        rings_v.append(ring_)
    for i in range(rings):
        for j in range(segs):
            jn = (j + 1) % segs
            f = bm.faces.new((rings_v[i][j], rings_v[i][jn], rings_v[i + 1][jn], rings_v[i + 1][j]))
            f.material_index = MOLTEN
            for lp, (ii, jj) in zip(f.loops, ((i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j))):
                lp[uvl].uv = (jj / segs, (total - length[ii]) * 4.0)
    cap = bm.faces.new(list(reversed(rings_v[0])))
    cap.material_index = MOLTEN
    return bm


def to_object(bm, name, location=(0, 0, 0), rotation=None, bevel=0.0):
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
    if rotation is not None:
        ob.rotation_euler = rotation
    if bevel:
        mod = ob.modifiers.new("Bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 1
        mod.limit_method = "ANGLE"
    return ob


def empty(name, loc, size=0.1, rot=None):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "SINGLE_ARROW"
    e.empty_display_size = size
    e.location = loc
    if rot:
        e.rotation_euler = rot
    return e


def conveyor_port(bm, face_pt, normal):
    """Conveyor input frame (Art/CONVEYOR_PORTS.md): 0.36 x 0.22 opening centred 0.25 high, iron frame,
    green top bar, a dark duct going in."""
    n = Vector(normal).normalized()
    up = Vector((0, 0, 1))
    m = Matrix((n.cross(up), n, up)).transposed().to_4x4()
    m.translation = Vector(face_pt)
    T = Matrix.Translation
    w, h, f = 0.36, 0.22, 0.045

    def bx(size, mat_, tm):
        r = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)
        _fin(bm, mat_, m @ tm @ Matrix.Diagonal((*size, 1)), r["verts"])
    for sx in (-1, 1):
        bx((f, 0.05, h + 2 * f), IRON, T((sx * (w / 2 + f / 2), -0.025, 0)))
    bx((w + 2 * f, 0.05, f), IRON, T((0, -0.025, -(h / 2 + f / 2))))
    bx((w + 2 * f, 0.05, f), IN, T((0, -0.025, h / 2 + f / 2)))
    bx((w, 0.02, h), SOOT, T((0, -0.22, 0)))
    for sx in (-1, 1):
        bx((0.02, 0.22, h + 0.04), IRON, T((sx * (w / 2 + 0.01), -0.11, 0)))
    # rubber flap strips
    for k in range(4):
        bx((w / 4 - 0.01, 0.008, h * 0.7), SOOT, T((-w / 2 + w / 8 + k * w / 4, -0.03, h * 0.12)))


# ---------------------------------------------------------------- Shaft (1x1x1, axis = Blender Y at C)
def shaft_end(bm, y_from, y_to, mat_ring=None):
    length = abs(y_to - y_from)
    cyl(bm, SHAFT_R, length, (0, (y_from + y_to) / 2, 0), "Y", STEEL, segs=18)
    s = 1 if y_to > y_from else -1
    cyl(bm, FLANGE_R, 0.035, (0, y_to - s * 0.0175, 0), "Y", CAST, segs=20)          # coupling flange
    cyl(bm, SHAFT_R + 0.018, 0.05, (0, y_to - s * 0.06, 0), "Y", CAST, segs=18)        # hub
    bolt_circle(bm, 4, 0.072, (0, y_to - s * 0.038, 0), "Y", STEEL, r=0.010, d=0.02)
    box(bm, (0.02, length * 0.55, 0.014), (0, (y_from + y_to) / 2, SHAFT_R + 0.004), RUST)  # key: spin visible
    if mat_ring is not None:
        ring(bm, FLANGE_R + 0.004, FLANGE_R - 0.018, 0.036, (0, y_to - s * 0.0175, 0), "Y", mat_ring, segs=20)


def model_shaft():
    bm = bmesh.new()
    shaft_end(bm, 0.0, -0.5)
    shaft_end(bm, 0.0, 0.5)
    for y in (-0.16, 0.16):                                         # grease collars
        cyl(bm, SHAFT_R + 0.010, 0.03, (0, y, 0), "Y", BRASS, segs=18)
    root = bpy.data.objects.new("feShaft_Base", None)
    root.empty_display_type = "PLAIN_AXES"
    # static bearing block in the middle (rides around the shaft, does not spin)
    br = bmesh.new()
    box(br, (0.20, 0.16, 0.20), (0, 0, C), PAINT)
    cyl(br, 0.085, 0.17, (0, 0, C), "Y", CAST, segs=20)
    for sx in (-1, 1):
        for sz in (-1, 1):
            cyl(br, 0.012, 0.17, (sx * 0.075, 0, C + sz * 0.075), "Y", STEEL, segs=6)
    cyl(br, 0.015, 0.04, (0, 0, C + 0.12), "Z", BRASS, segs=8)        # grease nipple
    return [root, to_object(bm, "FeSpin_Shaft", location=(0, 0, C), bevel=0.003),
            to_object(br, "feShaft_Bearing", bevel=0.004)]


# ---------------------------------------------------------------- Pipe (arms named after Unity axes)
ARM_DIRS = {"FeArm_PX": (-1, 0, 0), "FeArm_NX": (1, 0, 0), "FeArm_PY": (0, 0, 1), "FeArm_NY": (0, 0, -1),
            "FeArm_PZ": (0, -1, 0), "FeArm_NZ": (0, 1, 0)}


def _axname(v):
    return "X" if v[0] else ("Y" if v[1] else "Z")


def model_pipe():
    core = bmesh.new()
    # cast-iron cross fitting: a chunky body with a bolted sight glass on top
    box(core, (0.26, 0.26, 0.26), (0, 0, 0), CAST)
    for v in ARM_DIRS.values():
        ax = _axname(v)
        cyl(core, PIPE_R + 0.012, 0.03, Vector(v) * 0.13, ax, CAST, segs=16)
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                cyl(core, 0.010, 0.012, (sx * 0.10, sy * 0.10, sz * 0.134), "Z", STEEL, segs=6)
    # sight glass window on the front (-Y): the fluid shows through it
    box(core, (0.12, 0.012, 0.12), (0, -0.131, 0), IRON)
    box(core, (0.09, 0.014, 0.09), (0, -0.133, 0), LIQUID)
    root = bpy.data.objects.new("fePipe_Base", None)
    out = [root, to_object(core, "fePipe_Core", location=(0, 0, C), bevel=0.004)]
    for n, v in ARM_DIRS.items():
        bm = bmesh.new()
        vv = Vector(v)
        ax = _axname(v)
        cyl(bm, PIPE_R, 0.36, vv * 0.31, ax, STEEL, segs=16)
        cyl(bm, PIPE_R + 0.008, 0.02, vv * 0.30, ax, RUST, segs=16)          # weld seam
        flange(bm, vv * 0.485, ax)
        out.append(to_object(bm, n, location=(0, 0, C), bevel=0.002))
    return out


# ---------------------------------------------------------------- Mechanical Pump (1x1x1)
def model_mech_pump():
    b = bmesh.new()
    box(b, (0.62, 0.50, 0.04), (0, 0, 0.02), IRON)                              # base plate
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(b, 0.014, 0.03, (sx * 0.27, sy * 0.21, 0.05), "Z", STEEL, segs=6)  # anchor bolts
    # cast-iron volute: drum + a tangential outlet neck
    cyl(b, 0.21, 0.22, (0, 0, C), "Y", CAST, segs=28)
    for y in (-0.115, 0.115):
        cyl(b, 0.225, 0.03, (0, y, C), "Y", PAINT, segs=28)
        bolt_circle(b, 10, 0.205, (0, y * 1.1, C), "Y", STEEL, r=0.009, d=0.02)
    beam(b, (0.0, 0.0, 0.04), (0.0, 0.0, C - 0.18), 0.30, 0.18, CAST)          # pedestal
    # inlet (+Y, green) and outlet (-Y, orange) pipes, flush flanges like fePipe
    cyl(b, PIPE_R, 0.38, (0, 0.31, C), "Y", STEEL, segs=16)
    flange(b, (0, 0.485, C), "Y", IN)
    cyl(b, PIPE_R, 0.38, (0, -0.31, C), "Y", STEEL, segs=16)
    flange(b, (0, -0.485, C), "Y", OUT)
    # priming cup + sight glass on top of the casing (fluid colour shows here)
    cyl(b, 0.03, 0.10, (0, 0, C + 0.25), "Z", BRASS, segs=10)
    cyl(b, 0.05, 0.04, (0, 0, C + 0.31), "Z", BRASS, segs=12)
    box(b, (0.08, 0.03, 0.11), (0.12, -0.11, C + 0.12), IRON)
    box(b, (0.05, 0.034, 0.08), (0.12, -0.11, C + 0.12), LIQUID)
    # bearing pedestals for the cross shaft (Blender X)
    for sx in (-0.33, 0.33):
        box(b, (0.09, 0.16, C - 0.06), (sx, 0, (C - 0.06) / 2 + 0.04), PAINT)
        cyl(b, 0.075, 0.10, (sx, 0, C), "X", CAST, segs=18)
        cyl(b, 0.012, 0.03, (sx, 0, C + 0.085), "Z", BRASS, segs=6)
    hazard(b, 0.60, (0, -0.253, 0.07), "X", h=0.05, n=10)
    out = [to_object(b, "feMechPump_Base", bevel=0.004)]
    sh = bmesh.new()
    shaft_end(sh, 0.0, -0.5)
    shaft_end(sh, 0.0, 0.5)
    gear(sh, 0.12, 0.04, 16, (0, 0.20, 0), "Y", BRASS)
    out.append(to_object(sh, "FeSpin_PumpShaft", location=(0, 0, C), rotation=(0, 0, -math.pi / 2), bevel=0.002))
    return out


# ---------------------------------------------------------------- Condenser (2 wide x 2 high, centred on x)

def chute_arm(bm, v):
    """Arm from the core to the face: a riveted steel U-trough lined with firebrick, molten metal running in it.
    Up/down: a closed square duct with a brick lining (the metal falls through)."""
    v = Vector(v)
    mid = v * 0.31
    L = 0.38
    if v.z:
        box(bm, (0.22, 0.22, L), (0, 0, C + mid.z), IRON)
        for k in (-1, 1):
            box(bm, (0.235, 0.235, 0.03), (0, 0, C + mid.z + k * 0.12), RUST)
        box(bm, (0.26, 0.26, 0.04), (0, 0, C + v.z * 0.48), STEEL)
        return
    ax = bool(v.x)
    def sz(a, b_, c):
        return (a, b_, c) if ax else (b_, a, c)
    def off(o):
        return (mid.x, mid.y + o, 0) if ax else (mid.x + o, mid.y, 0)
    box(bm, sz(L, 0.24, 0.035), (mid.x, mid.y, C - 0.085), IRON)                    # floor plate
    box(bm, sz(L, 0.17, 0.02), (mid.x, mid.y, C - 0.06), BRICK)                     # brick lining
    for sgn in (-1, 1):
        o = off(sgn * 0.115)
        box(bm, sz(L, 0.03, 0.15), (o[0], o[1], C - 0.02), IRON)                    # walls
        o2 = off(sgn * 0.09)
        box(bm, sz(L, 0.02, 0.10), (o2[0], o2[1], C - 0.03), BRICK)
        o3 = off(sgn * 0.132)
        a_ = Vector((o3[0], o3[1], C - 0.06)) - (Vector((0.15, 0, 0)) if ax else Vector((0, 0.15, 0)))
        b_ = Vector((o3[0], o3[1], C - 0.06)) + (Vector((0.15, 0, 0)) if ax else Vector((0, 0.15, 0)))
        rivets(bm, a_, b_, 4, axis="Y" if ax else "X")
    box(bm, sz(L, 0.15, 0.015), (mid.x, mid.y, C - 0.045), MOLTEN)                   # the metal
    lip = sz(0.03, 0.28, 0.19)
    box(bm, lip, (v.x * 0.485, v.y * 0.485, C - 0.025), STEEL)                       # flange at the face
    # support strap under the trough, down to the floor half way
    box(bm, sz(0.04, 0.26, 0.03), (mid.x, mid.y, C - 0.115), RUST)


def model_metal_chute():
    core = bmesh.new()
    box(core, (0.28, 0.28, 0.035), (0, 0, -0.085), IRON)
    for sx in (-1, 1):
        box(core, (0.03, 0.28, 0.15), (sx * 0.135, 0, -0.02), IRON)
        box(core, (0.28, 0.03, 0.15), (0, sx * 0.135, -0.02), IRON)
    box(core, (0.22, 0.22, 0.02), (0, 0, -0.06), BRICK)
    box(core, (0.20, 0.20, 0.015), (0, 0, -0.045), MOLTEN)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(core, (0.04, 0.04, 0.40), (sx * 0.12, sy * 0.12, -0.30), RUST)        # legs to the floor
    root = bpy.data.objects.new("feMetalChute_Base", None)
    out = [root, to_object(core, "feMetalChute_Core", location=(0, 0, C), bevel=0.003)]
    for n, v in ARM_DIRS.items():
        bm = bmesh.new()
        chute_arm(bm, v)
        out.append(to_object(bm, n, bevel=0.002))
    return out


# ---------------------------------------------------------------- Casting Table (1x1x1)
def model_caster():
    """Casting Table as a low foundry floor bench, so the metal really runs DOWN: it arrives from the Metal Chute at
    the back at chute height (metal ~0.455), fills a pouring cup, runs down a lined channel and falls in an arc into
    the sand mold (cavity bottom 0.22). FeCastMetal (pivot = cavity bottom, height scaled by the fill), FeCastReady
    (finished casts on the ejector shelf in front, belt height), FePour_Caster (the falling stream),
    FeFx_Splash_1 (sparks where it lands), FeFx_Steam_1 (the cast steaming while it cools)."""
    b = bmesh.new()
    TOP = 0.19                                                                        # bench top
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(b, (0.08, 0.08, TOP - 0.03), (sx * 0.38, sy * 0.30, (TOP - 0.03) / 2), IRON)
            box(b, (0.12, 0.12, 0.015), (sx * 0.38, sy * 0.30, 0.0075), IRON)
    plate(b, (0.88, 0.72, 0.05), (0, -0.02, TOP - 0.025), CAST, "-Y", n=8)
    hazard(b, 0.86, (0, -0.385, TOP - 0.025), "X", h=0.04, n=12)
    # sand flask (mold box): cavity 0.40 x 0.30 x 0.10, bottom at 0.22
    CB = 0.22
    for y in (0.185, -0.185):
        plate(b, (0.54, 0.07, 0.13), (0, y, TOP + 0.065), RUST, "-Y" if y < 0 else "+Y", n=4)
    for x in (0.235, -0.235):
        box(b, (0.07, 0.30, 0.13), (x, 0, TOP + 0.065), RUST)
    box(b, (0.40, 0.30, CB - TOP), (0, 0, (CB + TOP) / 2), SAND)                    # sand floor of the cavity
    for x in (-0.20, 0.20):
        box(b, (0.035, 0.012, 0.012), (x, -0.20, TOP + 0.12), STEEL)                # clamps
        box(b, (0.012, 0.012, 0.13), (x, -0.226, TOP + 0.065), STEEL)
    for x in (-0.29, 0.29):                                                          # flask handles
        box(b, (0.05, 0.10, 0.025), (x, 0, TOP + 0.10), STEEL)
    # pouring cup at the back: receives the chute (lip flush with the back face at chute height)
    CUP_Y, CUP_F = 0.42, 0.405                                                        # centre, floor
    box(b, (0.28, 0.16, 0.03), (0, CUP_Y, CUP_F - 0.015), IRON)
    box(b, (0.22, 0.12, 0.012), (0, CUP_Y, CUP_F + 0.006), BRICK)
    for sx in (-1, 1):
        box(b, (0.03, 0.16, 0.13), (sx * 0.125, CUP_Y, CUP_F + 0.05), IRON)
    box(b, (0.28, 0.03, 0.05), (0, CUP_Y + 0.065, CUP_F + 0.10), IN)                 # green: metal comes in here
    box(b, (0.20, 0.10, 0.012), (0, CUP_Y, CUP_F + 0.02), MOLTEN)                    # metal in the cup
    for sx in (-1, 1):                                                               # cup stand down to the bench
        box(b, (0.04, 0.04, CUP_F - TOP), (sx * 0.11, CUP_Y + 0.03, (CUP_F + TOP) / 2), IRON)
    # sloped channel from the cup to the lip over the mold (U section, brick lined, metal running in it)
    y0, z0, y1, z1 = CUP_Y - 0.08, CUP_F + 0.005, 0.20, 0.375
    mid = Vector((0, (y0 + y1) / 2, (z0 + z1) / 2))
    L = math.hypot(y0 - y1, z0 - z1)
    tilt = Matrix.Rotation(math.atan2(z0 - z1, y0 - y1), 4, "X")
    T = Matrix.Translation
    for (size, off, mat) in (((0.11, L, 0.02), (0, 0, 0), IRON), ((0.075, L, 0.01), (0, 0, 0.012), BRICK),
                             ((0.05, L, 0.008), (0, 0, 0.021), MOLTEN)):
        r = bmesh.ops.create_cube(b, size=1.0, calc_uvs=True)
        _fin(b, mat, T(mid) @ tilt @ T(off) @ Matrix.Diagonal((*size, 1)), r["verts"])
    for sx in (-1, 1):
        r = bmesh.ops.create_cube(b, size=1.0, calc_uvs=True)
        _fin(b, IRON, T(mid) @ tilt @ T((sx * 0.05, 0, 0.03)) @ Matrix.Diagonal((0.012, L, 0.06, 1)), r["verts"])
    box(b, (0.08, 0.03, 0.02), (0, y1 - 0.005, z1 - 0.005), STEEL)                  # lip
    # quench water trough (right) with tongs; ejector shelf (front) up to belt height for the finished casts
    box(b, (0.14, 0.50, 0.14), (0.38, 0.02, TOP + 0.07), STEEL)
    box(b, (0.11, 0.46, 0.012), (0.38, 0.02, TOP + 0.12), LIQUID)
    beam(b, (0.36, -0.20, TOP + 0.15), (0.37, 0.16, TOP + 0.17), 0.012, 0.012, STEEL)   # tongs on the trough rim
    beam(b, (0.40, -0.20, TOP + 0.15), (0.385, 0.16, TOP + 0.17), 0.012, 0.012, STEEL)
    for sx in (-1, 1):
        box(b, (0.04, 0.04, 0.60 - TOP), (-0.22 + sx * 0.14, -0.43, (0.60 + TOP) / 2), IRON)
    box(b, (0.34, 0.14, 0.03), (-0.22, -0.43, 0.585), STEEL)
    box(b, (0.36, 0.03, 0.03), (-0.22, -0.495, 0.62), OUT)
    out = [to_object(b, "feCaster_Base", bevel=0.003)]
    metal = bmesh.new()
    box(metal, (0.40, 0.30, 0.10), (0, 0, 0.05), MOLTEN)
    out.append(to_object(metal, "FeCastMetal", location=(0, 0, CB + 0.004)))   # never flush with the sand
    ready = bmesh.new()
    for k, (x, y) in enumerate(((-0.07, -0.025), (0.07, -0.025), (0.0, 0.025))):
        box(ready, (0.13, 0.06, 0.04), (x, y, 0.02 + (0.04 if k == 2 else 0)), CAST)
    out.append(to_object(ready, "FeCastReady", location=(-0.22, -0.43, 0.60)))
    # the stream: leaves the lip still moving forward (-Y) and falls into the mold
    lip = Vector((0, y1 - 0.02, z1 + 0.012))
    out.append(to_object(stream((0, 0, 0), (0, -0.10, CB + 0.01 - lip.z), drop_curve=2.0, r0=0.012, r1=0.0065,
                                rings=20, lead=0.007), "FePour_Caster", location=lip))
    out.append(empty("FeFx_Splash_1", (0, lip.y - 0.10, CB + 0.05)))
    out.append(empty("FeFx_Steam_1", (0, 0, CB + 0.11)))
    return out


# ---------------------------------------------------------------- Foundry (2 wide x 2 high, centred on x)
def model_m_foundry():
    """Firebrick blast furnace on a steel skid. Molten metal collects in a launder (channel) that runs around the
    bottom layer and leaves at any outer face into a Metal Chute (MetalWorks: any outer side of the bottom layer).
    Belt inlets on the back and both ends (the Foundry takes items from a belt on any side). Crucible on top,
    chimney on the left end, fire door in front."""
    b = bmesh.new()
    X0, X1 = -1.0, 1.0
    # skid
    for y in (-0.42, 0.42):
        box(b, (1.96, 0.08, 0.08), (0, y, 0.04), IRON)
    box(b, (1.80, 0.80, 0.04), (0, 0, 0.10), IRON)
    # furnace body (firebrick) z 0.12..1.30, inset so the launder fits around it
    box(b, (1.56, 0.62, 1.18), (0, 0.0, 0.71), BRICK)
    for z in (0.30, 0.62, 0.94, 1.26):                                              # steel bands
        box(b, (1.60, 0.66, 0.05), (0, 0, z), IRON)
        rivets(b, (-0.76, -0.335, z), (0.76, -0.335, z), 10)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(b, (0.07, 0.07, 1.22), (sx * 0.78, sy * 0.31, 0.71), IRON)          # corner angles
    # launder: channel around the bottom layer at chute height (floor 0.43, metal 0.455)
    def launder(a, b_, along_x):
        a, b_ = Vector(a), Vector(b_)
        mid, L = (a + b_) / 2, (b_ - a).length
        def S(l, w_, h):
            return (l, w_, h) if along_x else (w_, l, h)
        box(b, S(L, 0.20, 0.03), (mid.x, mid.y, 0.42), IRON)
        box(b, S(L, 0.15, 0.02), (mid.x, mid.y, 0.44), BRICK)
        box(b, S(L, 0.14, 0.012), (mid.x, mid.y, 0.455), MOLTEN)
        o = Vector((0, 0.095, 0)) if along_x else Vector((0.095, 0, 0))
        for s_ in (-1, 1):
            box(b, S(L, 0.025, 0.10), (mid.x + s_ * o.x, mid.y + s_ * o.y, 0.465), IRON)
    launder((-0.92, -0.41, 0), (0.92, -0.41, 0), True)       # front
    launder((-0.92, 0.41, 0), (0.92, 0.41, 0), True)         # back
    launder((-0.90, -0.30, 0), (-0.90, 0.30, 0), False)      # right end (Blender -X = Unity +X)
    launder((0.90, -0.30, 0), (0.90, 0.30, 0), False)        # left end
    # spouts at every outer face of both bottom cells, lip flush with the block face
    for (px, py, nx, ny) in ((-0.5, -0.5, 0, -1), (0.5, -0.5, 0, -1), (-0.5, 0.5, 0, 1), (0.5, 0.5, 0, 1),
                             (-1.0, 0.0, -1, 0), (1.0, 0.0, 1, 0)):
        along_x = ny == 0
        c = Vector((px - nx * 0.045, py - ny * 0.045, 0.45))
        box(b, (0.09, 0.16, 0.04) if along_x else (0.16, 0.09, 0.04), (c.x, c.y, 0.425), STEEL)
        box(b, (0.09, 0.10, 0.012) if along_x else (0.10, 0.09, 0.012), (c.x, c.y, 0.452), MOLTEN)
    # open firebox (front, LEFT cell, away from the crucible pour): a cast-iron mouth standing out of the brick,
    # deep enough that the flames (FeFx_Fire, own particles; the vanilla forge particle is gone from blocks.xml)
    # stay inside it. Back wall and sides sooty, a grate with a glowing coal bed, the door swung open on its hinge.
    FX, FZ0, FZ1 = 0.40, 0.58, 1.00                                                  # mouth centre x, bottom, top
    MY0, MY1 = -0.31, -0.45                                                          # from the brick face out
    box(b, (0.50, 0.02, FZ1 - FZ0), (FX, -0.35, (FZ0 + FZ1) / 2), SOOT)           # back wall (covers the bands)
    for sx in (-1, 1):
        box(b, (0.05, MY0 - MY1, FZ1 - FZ0 + 0.06), (FX + sx * 0.255, (MY0 + MY1) / 2, (FZ0 + FZ1) / 2), CAST)
        box(b, (0.012, MY0 - MY1 - 0.02, FZ1 - FZ0 - 0.04), (FX + sx * 0.226, (MY0 + MY1) / 2, (FZ0 + FZ1) / 2), SOOT)
    box(b, (0.56, MY0 - MY1, 0.06), (FX, (MY0 + MY1) / 2, FZ1 + 0.03), CAST)       # lintel (roof over the flames)
    box(b, (0.50, MY0 - MY1 - 0.02, 0.012), (FX, (MY0 + MY1) / 2, FZ1 - 0.006), SOOT)
    box(b, (0.60, 0.04, 0.05), (FX, MY1 + 0.02, FZ1 + 0.035), STEEL)                # front lip of the lintel
    box(b, (0.56, MY0 - MY1, 0.06), (FX, (MY0 + MY1) / 2, FZ0 - 0.03), CAST)       # sill
    for k in range(6):                                                               # grate bars
        box(b, (0.42, 0.02, 0.02), (FX, MY0 - 0.02 - k * 0.022, FZ0 + 0.05), IRON)
    box(b, (0.40, 0.10, 0.035), (FX, (MY0 + MY1) / 2 + 0.01, FZ0 + 0.075), GLOW)    # coal bed
    for k in range(7):                                                               # coal lumps on top of it
        box(b, (0.06, 0.05, 0.03), (FX - 0.16 + k * 0.053, (MY0 + MY1) / 2 + 0.01 + 0.02 * ((k % 3) - 1),
                                     FZ0 + 0.10 + 0.008 * (k % 2)), SOOT, Matrix.Rotation(0.3 * k, 4, "Z"))
    # the door, swung fully open (180 deg) and lying against the brick beside the mouth (stays inside the block)
    plate(b, (0.34, 0.035, 0.38), (FX - 0.455, -0.365, (FZ0 + FZ1) / 2), CAST, "-Y", n=4)
    for z in (FZ0 + 0.09, FZ1 - 0.09):
        cyl(b, 0.02, 0.06, (FX - 0.285, -0.40, z), "Z", STEEL, segs=8)                # hinges
    box(b, (0.03, 0.03, 0.08), (FX - 0.58, -0.395, (FZ0 + FZ1) / 2), STEEL)         # handle
    # ash door under the firebox
    plate(b, (0.40, 0.04, 0.12), (FX, -0.33, 0.48 + 0.05), CAST, "-Y", n=3)
    # pressure gauge between the two cells
    cyl(b, 0.07, 0.03, (-0.02, -0.34, 1.05), "Y", BRASS, segs=18)
    cyl(b, 0.058, 0.032, (-0.02, -0.345, 1.05), "Y", GLASS, segs=18)
    hazard(b, 1.50, (0, -0.33, 1.20), "X", h=0.05, n=18)
    # crucible on top (right part): steel pot in a tilting yoke, molten surface inside
    # an OPEN pot (walls only: the old capped cylinder hid the melt under a grey lid): thick refractory walls,
    # dark inside, the glowing melt a little under the rim, the lid swung back on its hinge
    CRX, CRY = -0.40, 0.0
    cyl(b, 0.30, 0.04, (CRX, CRY, 1.32), "Z", IRON, segs=24)                         # stand plate
    cyl(b, 0.27, 0.06, (CRX, CRY, 1.37), "Z", CAST, segs=24)                         # bottom
    ring(b, 0.285, 0.235, 0.36, (CRX, CRY, 1.55), "Z", CAST, segs=28)                # pot wall
    ring(b, 0.236, 0.22, 0.30, (CRX, CRY, 1.56), "Z", BRICK, segs=28)                # refractory lining
    ring(b, 0.30, 0.235, 0.04, (CRX, CRY, 1.74), "Z", STEEL, segs=28)                # rim band
    cyl(b, 0.222, 0.02, (CRX, CRY, 1.66), "Z", MOLTEN, segs=28)                      # the melt
    for k in range(5):                                                                  # slag crusts floating
        a_ = 2 * math.pi * k / 5 + 0.3
        cyl(b, 0.03 + 0.01 * (k % 2), 0.012, (CRX + 0.12 * math.cos(a_), CRY + 0.12 * math.sin(a_), 1.675), "Z", SOOT, segs=7)
    # lid on a swing arm: a post at the back-right corner holds it raised and turned half aside
    PX_, PY_ = CRX - 0.32, CRY + 0.30
    cyl(b, 0.025, 0.62, (PX_, PY_, 1.32 + 0.31), "Z", STEEL, segs=10)                 # post
    cyl(b, 0.04, 0.05, (PX_, PY_, 1.92), "Z", CAST, segs=10)
    LX_, LY_ = CRX - 0.20, CRY + 0.16                                                  # lid centre (off the pot)
    beam(b, (PX_, PY_, 1.92), (LX_, LY_, 1.92), 0.03, 0.03, STEEL)                   # arm
    cyl(b, 0.26, 0.035, (LX_, LY_, 1.89), "Z", CAST, segs=24)                        # the lid, held up
    cyl(b, 0.27, 0.012, (LX_, LY_, 1.866), "Z", SOOT, segs=24)                       # sooty underside
    cyl(b, 0.04, 0.05, (LX_, LY_, 1.93), "Z", STEEL, segs=10)                        # handle
    box(b, (0.10, 0.10, 0.04), (-0.40, -0.29, 1.72), STEEL, Matrix.Rotation(0.4, 4, "X"))   # pour lip
    for sx in (-1, 1):
        box(b, (0.05, 0.05, 0.42), (-0.40 + sx * 0.36, 0, 1.53), IRON)
        cyl(b, 0.04, 0.08, (-0.40 + sx * 0.33, 0, 1.58), "X", STEEL, segs=10)
    # chimney (left end): brick stack + steel cap, to z = 2.0
    box(b, (0.42, 0.42, 0.62), (0.52, 0.06, 1.61), BRICK)
    for z in (1.40, 1.70):
        box(b, (0.46, 0.46, 0.04), (0.52, 0.06, z), IRON)
    cyl(b, 0.15, 0.12, (0.52, 0.06, 1.96), "Z", SOOT, segs=16)
    cyl(b, 0.22, 0.02, (0.52, 0.06, 1.99), "Z", IRON, segs=16)
    # bellows pipe from the blower to the furnace (back)
    cyl(b, 0.06, 0.70, (-0.10, 0.36, 1.10), "X", RUST, segs=12)
    # belt inlets: back of both cells, both ends (bottom layer, 0.25 high)
    for p, n in (((-0.5, 0.5, 0.25), (0, 1, 0)), ((0.5, 0.5, 0.25), (0, 1, 0)),
                 ((-1.0, 0.0, 0.25), (-1, 0, 0)), ((1.0, 0.0, 0.25), (1, 0, 0))):
        conveyor_port(b, p, n)
    objs = [to_object(b, "feM_Foundry_Base", bevel=0.004)]
    # blower fan on the back (spins while it burns: MachineVisual FeSpin_*)
    bl = bmesh.new()
    ring(bl, 0.16, 0.14, 0.06, (0, 0, 0), "Y", IRON, segs=20)
    cyl(bl, 0.04, 0.07, (0, 0, 0), "Y", CAST, segs=10)
    for k in range(6):
        a_ = k * math.pi / 3
        box(bl, (0.13, 0.04, 0.02), (math.cos(a_) * 0.075, 0, math.sin(a_) * 0.075), STEEL, Matrix.Rotation(-a_, 4, "Y"))
    objs.append(to_object(bl, "FeSpin_x3_Blower", location=(-0.60, 0.40, 1.10), rotation=(0, 0, math.pi)))
    # pour: from the crucible lip (front, -Y) an arc out and down into the front launder (metal at 0.455)
    lip = Vector((-0.40, -0.33, 1.715))
    objs.append(to_object(stream((0, 0, 0), (0, -0.085, 0.455 - lip.z), drop_curve=2.2, r0=0.018, r1=0.009,
                                 rings=24, lead=0.008), "FePour_Foundry", location=lip))
    objs.append(empty("FeFx_Splash_1", (-0.40, -0.415, 0.47)))                    # where it lands
    objs.append(empty("FeFx_Smoke_1", (0.52, 0.06, 2.0)))
    objs.append(empty("FeFx_Sparks_1", (-0.33, -0.08, 1.70)))
    objs.append(empty("FeFx_Fire_1", (0.40, -0.39, 0.66)))                         # flames inside the mouth
    return objs


# ================================================================ round 2: torque blocks, engine, machines, belt
AX_X = (0, 0, math.pi / 2)
AX_UP = (-math.pi / 2, 0, 0)


def cast_housing(bm, w, d, h, mat=CAST, ribs=3):
    """Cast-iron box centred on the torque axis: ribbed walls, bolted lid, feet down to the floor."""
    box(bm, (w, d, h), (0, 0, C), mat)
    for k in range(ribs):                                       # vertical ribs on the X walls
        y = -d / 2 + d * (k + 1) / (ribs + 1)
        for sx in (-1, 1):
            box(bm, (0.02, 0.025, h - 0.04), (sx * (w / 2 + 0.01), y, C), mat)
    box(bm, (w + 0.03, d + 0.03, 0.03), (0, 0, C + h / 2 + 0.005), mat)            # lid flange
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(bm, 0.011, 0.02, (sx * (w / 2 - 0.01), sy * (d / 2 - 0.01), C + h / 2 + 0.025), "Z", STEEL, segs=6)
    box(bm, (0.012, d * 0.5, 0.08), (w / 2 + 0.016, 0, C - h * 0.2), BRASS)        # name plate
    for sx in (-1, 1):                                                              # feet
        box(bm, (0.10, d * 0.8, C - h / 2), (sx * (w / 2 - 0.06), 0, (C - h / 2) / 2), mat)
        box(bm, (0.16, d * 0.9, 0.025), (sx * (w / 2 - 0.06), 0, 0.0125), IRON)
        for sy in (-1, 1):
            cyl(bm, 0.012, 0.03, (sx * (w / 2 - 0.06), sy * d * 0.35, 0.03), "Z", STEEL, segs=6)


def boss(bm, y, ring_mat=None, r=0.12):
    """Bearing boss on the Y faces of a housing, with a coloured ring (green in / orange out)."""
    cyl(bm, r, 0.05, (0, y, C), "Y", CAST, segs=22)
    bolt_circle(bm, 6, r - 0.02, (0, y + (0.026 if y > 0 else -0.026), C), "Y", STEEL, r=0.008, d=0.015)
    if ring_mat is not None:
        ring(bm, r + 0.008, r - 0.008, 0.052, (0, y, C), "Y", ring_mat, segs=22)


def bevel_gear(bm, r, depth, teeth, loc, mat, facing=1):
    """Bevel gear along Y: a cone with radial teeth on its slope (facing = which way the small end points)."""
    y = loc[1]
    cyl(bm, r, depth, loc, "Y", mat, segs=teeth, r2=r * 0.6)
    if facing < 0:
        pass
    for k in range(teeth):
        a = 2 * math.pi * k / teeth
        m = Matrix.Translation(loc) @ AXIS["Y"] @ Matrix.Rotation(a, 4, "Z") @ Matrix.Translation((r * 0.85, 0, 0)) \
            @ Matrix.Rotation(0.6 * facing, 4, "Y")
        rr = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)
        _fin(bm, mat, m @ Matrix.Diagonal((0.03, 0.022, depth * 0.9, 1)), rr["verts"])


def model_gearbox():
    w = 0.56
    b = bmesh.new()
    box(b, (w, w, w), (0, 0, C), CAST)
    for ax in range(3):                                          # cast ribs around the cube on every axis
        for k in (-1, 1):
            size = [w + 0.02] * 3
            size[ax] = 0.03
            loc = [0, 0, C]
            loc[ax] += k * w * 0.28
            box(b, tuple(size), tuple(loc), CAST)
    for axis, sign in (("X", 1), ("X", -1), ("Y", 1), ("Y", -1), ("Z", 1), ("Z", -1)):
        loc = Vector((0, 0, C))
        loc["XYZ".index(axis)] += sign * (w / 2 + 0.012)
        cyl(b, 0.13, 0.03, loc, axis, CAST, segs=22)
        bolt_circle(b, 6, 0.11, loc + Vector([0.016 * sign if a == axis else 0 for a in "XYZ"]), axis, STEEL,
                    r=0.009, d=0.012)
    cyl(b, 0.03, 0.04, (0.18, 0.18, C + w / 2 + 0.02), "Z", BRASS, segs=10)          # oil filler
    cyl(b, 0.015, 0.03, (0.18, -0.20, C - w / 2 + 0.05), "X", STEEL, segs=6)
    box(b, (0.012, 0.18, 0.08), (w / 2 + 0.02, -0.12, C + 0.16), BRASS)              # plate
    out = [to_object(b, "feGearbox_Base", bevel=0.004)]
    rots = {"+Y": (0, 0, 0), "-Y": (0, 0, math.pi), "+X": (0, 0, -math.pi / 2), "-X": (0, 0, math.pi / 2),
            "+Z": (math.pi / 2, 0, 0), "-Z": (-math.pi / 2, 0, 0)}
    for k, (n, rot) in enumerate(rots.items()):
        bm = bmesh.new()
        shaft_end(bm, w / 2 - 0.03, 0.5)
        out.append(to_object(bm, "FeSpin_Gearbox" + str(k + 1), location=(0, 0, C), rotation=rot, bevel=0.002))
    return out


def model_speedbox():
    b = bmesh.new()
    cast_housing(b, 0.56, 0.42, 0.50, PAINT)
    boss(b, 0.235, IN)
    boss(b, -0.235, OUT)
    # open top with a guard grid: the two gears show through
    box(b, (0.40, 0.30, 0.02), (0, 0, C + 0.26), SOOT)
    for k in range(5):
        box(b, (0.018, 0.30, 0.02), (-0.16 + k * 0.08, 0, C + 0.285), STEEL)
    box(b, (0.42, 0.32, 0.02), (0, 0, C + 0.275), IRON)
    # ratio selector: notched quadrant and a lever (+X side)
    box(b, (0.012, 0.20, 0.12), (0.30, 0.05, C + 0.08), BRASS)
    for k in range(3):
        box(b, (0.014, 0.012, 0.03), (0.307, -0.03 + k * 0.08, C + 0.13), SOOT)
    beam(b, (0.31, 0.05, C + 0.02), (0.31, 0.13, C + 0.20), 0.02, 0.02, STEEL)
    cyl(b, 0.025, 0.04, (0.31, 0.13, C + 0.21), "X", WOOD, segs=10)
    out = [to_object(b, "feSpeedBox_Base", bevel=0.004)]
    sin = bmesh.new()
    shaft_end(sin, -0.02, 0.5, IN)
    gear(sin, 0.16, 0.05, 24, (0, 0.06, 0), "Y", BRASS)
    cyl(sin, 0.05, 0.07, (0, 0.06, 0), "Y", STEEL, segs=12)
    out.append(to_object(sin, "FeSpinIn_SpeedBox", location=(0, 0, C), bevel=0.002))
    sout = bmesh.new()
    shaft_end(sout, 0.02, -0.5, OUT)
    gear(sout, 0.08, 0.05, 12, (0, -0.06, 0), "Y", STEEL)
    out.append(to_object(sout, "FeSpinOut_SpeedBox", location=(0, 0, C), bevel=0.002))
    return out


def model_inverter():
    b = bmesh.new()
    cyl(b, 0.23, 0.34, (0, 0, C), "Y", CAST, segs=28)                               # drum
    cyl(b, 0.14, 0.52, (0, 0, C), "X", CAST, segs=20)                               # cross housing (idler)
    for sx in (-1, 1):
        cyl(b, 0.16, 0.03, (sx * 0.26, 0, C), "X", CAST, segs=20)
        bolt_circle(b, 6, 0.135, (sx * 0.276, 0, C), "X", STEEL, r=0.008, d=0.012)
    for y in (-0.19, 0.19):
        cyl(b, 0.25, 0.03, (0, y, C), "Y", IRON, segs=28)
        bolt_circle(b, 10, 0.225, (0, y + (0.016 if y > 0 else -0.016), C), "Y", STEEL, r=0.008, d=0.012)
    ring(b, 0.258, 0.242, 0.034, (0, 0.19, C), "Y", IN, segs=28)
    ring(b, 0.258, 0.242, 0.034, (0, -0.19, C), "Y", OUT, segs=28)
    # window on top (open, with bars) and a red reversing arrow
    box(b, (0.16, 0.20, 0.02), (0, 0, C + 0.225), SOOT)
    for k in range(3):
        box(b, (0.016, 0.20, 0.016), (-0.05 + k * 0.05, 0, C + 0.24), STEEL)
    for k in range(6):
        a = math.radians(-75 + k * 30)
        box(b, (0.035, 0.03, 0.012), (0.0, 0.17 * math.sin(a), C + 0.17 * math.cos(a) + 0.08), HAZ,
            Matrix.Rotation(-a, 4, "X"))
    for sy in (-0.12, 0.12):                                                         # stand
        beam(b, (-0.20, sy, 0.0), (-0.10, sy, C - 0.20), 0.05, 0.05, IRON)
        beam(b, (0.20, sy, 0.0), (0.10, sy, C - 0.20), 0.05, 0.05, IRON)
    box(b, (0.50, 0.38, 0.025), (0, 0, 0.0125), IRON)
    out = [to_object(b, "feSpinInverter_Base", bevel=0.004)]
    sin = bmesh.new()
    shaft_end(sin, 0.0, 0.5, IN)
    bevel_gear(sin, 0.11, 0.05, 16, (0, 0.08, 0), BRASS, 1)
    out.append(to_object(sin, "FeSpinIn_Inverter", location=(0, 0, C), bevel=0.002))
    sout = bmesh.new()
    shaft_end(sout, 0.0, -0.5, OUT)
    bevel_gear(sout, 0.11, 0.05, 16, (0, -0.08, 0), STEEL, -1)
    out.append(to_object(sout, "FeSpinOut_Inverter", location=(0, 0, C), bevel=0.002))
    idl = bmesh.new()                                                                # idler bevel across (X)
    bevel_gear(idl, 0.07, 0.04, 12, (0, 0.10, 0), BRASS, 1)
    cyl(idl, 0.02, 0.22, (0, 0.11, 0), "Y", STEEL, segs=8)
    out.append(to_object(idl, "FeSpin_InverterIdler", location=(0, 0, C), rotation=(0, 0, -math.pi / 2), bevel=0.002))
    return out


def model_clutch():
    """Clutch: bell housing between the shafts; a lever on top (FeLever_Clutch, pivot on its axle) that FxVisual
    throws to one side when the clutch is engaged and to the other when released (BlockFeKinetic.Engaged)."""
    b = bmesh.new()
    cyl(b, 0.21, 0.30, (0, 0, C), "Y", PAINT, segs=28)
    for k in range(8):                                                               # cooling slots
        a = 2 * math.pi * k / 8
        box(b, (0.05, 0.12, 0.012), (0.212 * math.cos(a), 0, C + 0.212 * math.sin(a)), SOOT,
            Matrix.Rotation(-a + math.pi / 2, 4, "Y"))
    for y in (-0.16, 0.16):
        cyl(b, 0.225, 0.03, (0, y, C), "Y", CAST, segs=28)
        bolt_circle(b, 8, 0.20, (0, y + (0.016 if y > 0 else -0.016), C), "Y", STEEL, r=0.009, d=0.012)
    ring(b, 0.232, 0.216, 0.034, (0, 0.16, C), "Y", IN, segs=28)
    ring(b, 0.232, 0.216, 0.034, (0, -0.16, C), "Y", OUT, segs=28)
    for sy in (-0.10, 0.10):                                                         # cradle
        beam(b, (-0.17, sy, 0.0), (-0.09, sy, C - 0.17), 0.05, 0.05, IRON)
        beam(b, (0.17, sy, 0.0), (0.09, sy, C - 0.17), 0.05, 0.05, IRON)
    box(b, (0.42, 0.30, 0.025), (0, 0, 0.0125), IRON)
    # lever bracket on top: two cheeks, an axle along Y; ON / OFF marks (green / red) on the quadrant
    for sx in (-1, 1):
        box(b, (0.015, 0.10, 0.08), (sx * 0.035, 0, C + 0.235), IRON)
    cyl(b, 0.012, 0.10, (0, 0, C + 0.25), "X", STEEL, segs=8)
    box(b, (0.10, 0.012, 0.03), (-0.07, -0.055, C + 0.235), IN)
    box(b, (0.10, 0.012, 0.03), (0.07, -0.055, C + 0.235), OUT)
    out = [to_object(b, "feClutch_Base", bevel=0.004)]
    lv = bmesh.new()                                                                 # built upright, pivot at origin
    box(lv, (0.03, 0.03, 0.04), (0, 0, 0), STEEL)
    beam(lv, (0, 0, 0.0), (0, 0, 0.20), 0.025, 0.025, HAZ)
    cyl(lv, 0.03, 0.06, (0, 0, 0.215), "Y", WOOD, segs=12)
    out.append(to_object(lv, "FeLever_Clutch", location=(0, 0, C + 0.25), bevel=0.002))
    sin = bmesh.new()
    shaft_end(sin, 0.0, 0.5, IN)
    cyl(sin, 0.16, 0.035, (0, 0.035, 0), "Y", STEEL, segs=28)                      # pressure plate
    for k in range(6):                                                               # springs
        a = 2 * math.pi * k / 6
        cyl(sin, 0.014, 0.05, (0.10 * math.cos(a), 0.075, 0.10 * math.sin(a)), "Y", HAZ, segs=6)
    out.append(to_object(sin, "FeSpinIn_Clutch", location=(0, 0, C), bevel=0.002))
    sout = bmesh.new()
    shaft_end(sout, 0.0, -0.5, OUT)
    cyl(sout, 0.155, 0.03, (0, -0.02, 0), "Y", RUST, segs=28)                      # friction disc
    ring(sout, 0.155, 0.10, 0.035, (0, -0.02, 0), "Y", SOOT, segs=28)
    out.append(to_object(sout, "FeSpinOut_Clutch", location=(0, 0, C), bevel=0.002))
    return out


ENG_R, ENG_L = 0.11, 0.42                   # crank radius, connecting rod length
ENG_THROWS = (-0.48, -0.92)                 # crank throws along the shaft (Blender Y)
ENG_PHASE = (math.pi / 2, 0.0)              # crank pin angle in the built pose (0 = straight up)
ENG_BEARINGS = (-0.25, -0.70, -1.14)        # main bearings, between / around the throws
ENG_FLY = -1.31                              # flywheel plane
ENG_GUIDE = (0.70, 1.08)                     # crosshead guide bars (z)
ENG_CYL = (1.12, 1.52)                       # cylinder bottom / top (z)


def model_steam_engine():
    """Steam Engine, 3 x 3 base and 2 high; origin = floor centre of the parent (middle) cell. Same ports as the old
    model (water under the centre and on the left / right / back of the bottom layer, steam out over the top centre,
    torque out of the front centre, belt inlets on both sides of the upper layer).
    Mechanism (2026-11-24): a vertical twin. The crankshaft IS the output shaft (FeSpin_SteamFlywheel: shaft, two
    cranks 90 deg apart with counterweights, the flywheel at the front). Over each crank a cylinder (upper layer), a
    crosshead running in vertical guides (FeCrosshead_<n>, pivot = its pin) and a connecting rod (FeConrod_<n>, pivot
    = the crosshead pin, built pointing at its crank pin); FeCrankPin_<n> marks the crank pin in the built pose.
    KineticSpinner solves the slider-crank from the crankshaft's real angle every frame. Effects: FeFx_SteamVent_1 (SteamVent: while it vents with no pipe on the outlet),
    FeFx_Smoke_1 (stack), FeFx_Fire_1 + glowing coal (firebox), FeFx_Steam_* (drain cocks) while it runs."""
    b = bmesh.new()
    # bed: two I-beam rails and cross members
    for x in (-1.2, 1.2):
        box(b, (0.16, 2.96, 0.04), (x, 0, 0.02), IRON)
        box(b, (0.04, 2.96, 0.14), (x, 0, 0.09), IRON)
        box(b, (0.16, 2.96, 0.04), (x, 0, 0.16), IRON)
    for y, wd in ((-1.46, 0.08), (-0.10, 0.14), (0.55, 0.14), (1.35, 0.14)):
        box(b, (2.36, wd, 0.12), (0, y, 0.12), IRON)
    for sx in (-1, 1):                                                                # engine bed girders
        box(b, (0.10, 1.30, 0.16), (sx * 0.36, -0.80, 0.10), IRON)
    plate(b, (2.6, 1.3, 0.04), (0, 0.55, 0.20), CAST, "-Y", n=14)
    # boiler (locomotive style) along X, olive paint with brass bands and rivet seams
    BY, BZ, BR = 0.55, 0.95, 0.60
    cyl(b, BR, 2.20, (0.05, BY, BZ), "X", PAINT, segs=36)
    for x in (-0.95, -0.35, 0.35, 0.95):
        cyl(b, BR + 0.015, 0.05, (x, BY, BZ), "X", BRASS, segs=36)
    for k in range(10):
        a = math.pi * (0.15 + 0.07 * k)
        rivets(b, (-1.0, BY + (BR + 0.005) * math.cos(a), BZ + (BR + 0.005) * math.sin(a)),
               (1.1, BY + (BR + 0.005) * math.cos(a), BZ + (BR + 0.005) * math.sin(a)), 1)
    cyl(b, BR + 0.04, 0.10, (1.18, BY, BZ), "X", CAST, segs=36)                       # smokebox door end
    cyl(b, 0.25, 0.03, (1.24, BY, BZ), "X", IRON, segs=20)
    for x in (-0.80, 0.80):                                                           # saddles
        box(b, (0.22, 1.0, 0.36), (x, BY, 0.36), CAST)
    # firebox (front left): cast box, open door with fire inside
    FX, FY = -1.05, -0.95
    box(b, (0.72, 0.62, 0.72), (FX, FY, 0.56), CAST)
    for z in (0.30, 0.82):
        box(b, (0.75, 0.65, 0.04), (FX, FY, z), IRON)
    box(b, (0.36, 0.02, 0.30), (FX, FY - 0.30, 0.56), SOOT)                          # dark mouth
    for sx in (-1, 1):
        box(b, (0.04, 0.10, 0.34), (FX + sx * 0.20, FY - 0.36, 0.56), CAST)
    box(b, (0.44, 0.10, 0.04), (FX, FY - 0.36, 0.74), CAST)
    box(b, (0.44, 0.10, 0.04), (FX, FY - 0.36, 0.39), CAST)
    box(b, (0.32, 0.06, 0.04), (FX, FY - 0.34, 0.44), GLOW)                          # coal bed
    plate(b, (0.04, 0.30, 0.30), (FX - 0.40, FY - 0.33, 0.56), CAST, "-X", n=3)       # door, open
    box(b, (0.30, 0.20, 0.20), (FX, FY + 0.30, 0.30), BRICK)
    # steam dome, safety valve, whistle, gauge; steam pipe up to the outlet (top centre)
    cyl(b, 0.20, 0.30, (0, BY, BZ + BR + 0.10), "Z", BRASS, segs=24)
    cyl(b, 0.23, 0.05, (0, BY, BZ + BR + 0.27), "Z", BRASS, segs=24)
    cyl(b, 0.04, 0.16, (0.40, BY, BZ + BR + 0.06), "Z", BRASS, segs=10)
    cyl(b, 0.06, 0.03, (0.40, BY, BZ + BR + 0.15), "Z", STEEL, segs=10)
    cyl(b, 0.025, 0.18, (-0.35, BY, BZ + BR + 0.08), "Z", BRASS, segs=8)
    cyl(b, 0.05, 0.10, (-0.35, BY, BZ + BR + 0.20), "Z", BRASS, segs=10)
    cyl(b, 0.09, 0.03, (-0.70, BY - BR - 0.01, BZ + 0.25), "Y", BRASS, segs=18)
    cyl(b, 0.075, 0.032, (-0.70, BY - BR - 0.015, BZ + 0.25), "Y", GLASS, segs=18)
    beam(b, (0, BY, BZ + BR + 0.28), (0, 0.0, BZ + BR + 0.28), 0.10, 0.10, STEEL)
    cyl(b, PIPE_R, 2.0 - (BZ + BR + 0.28), (0, 0, (2.0 + BZ + BR + 0.28) / 2), "Z", STEEL, segs=16)
    flange(b, (0, 0, 1.985), "Z", OUT)
    # stack on the smokebox end, flared top
    cyl(b, 0.13, 0.62, (1.15, BY, 1.70), "Z", IRON, segs=18)
    cyl(b, 0.13, 0.12, (1.15, BY, 2.05 - 0.06), "Z", IRON, segs=18, r2=0.20)
    cyl(b, 0.18, 0.04, (1.15, BY, 1.42), "Z", CAST, segs=18)
    # water inlets (as before) with flanges, and feed pipes
    cyl(b, PIPE_R, 0.20, (0, 0, 0.10), "Z", STEEL, segs=16)
    flange(b, (0, 0, 0.015), "Z", IN)
    for sx in (-1, 1):
        cyl(b, PIPE_R, 0.24, (sx * (1.5 - 0.12), 0, C), "X", STEEL, segs=16)
        flange(b, (sx * 1.485, 0, C), "X", IN)
        beam(b, (sx * 1.38, 0, C), (sx * 0.45, 0.25, 0.55), 0.08, 0.08, STEEL)
    cyl(b, PIPE_R, 0.24, (0, 1.5 - 0.12, C), "Y", STEEL, segs=16)
    flange(b, (0, 1.485, C), "Y", IN)
    beam(b, (0, 1.38, C), (0, 0.95, 0.60), 0.08, 0.08, STEEL)
    # belt inlets on both sides of the upper layer, with wooden fuel hoppers behind them
    for sx in (-1, 1):
        conveyor_port(b, (sx * 1.5, 0, 1.25), (sx, 0, 0))
        box(b, (0.36, 0.62, 0.42), (sx * 1.13, 0, 1.25), WOOD)
        for z in (1.08, 1.42):
            box(b, (0.38, 0.64, 0.03), (sx * 1.13, 0, z), IRON)
        beam(b, (sx * 1.13, 0, 1.04), (sx * 0.90, -0.65, 0.40), 0.08, 0.08, IRON)    # stands
    # ---- vertical twin engine over the crankshaft (axis Blender Y at x 0, z C)
    for y in ENG_BEARINGS:                                                            # main bearings
        box(b, (0.26, 0.12, C - 0.18), (0, y, (C - 0.18) / 2 + 0.18), CAST)
        cyl(b, 0.085, 0.13, (0, y, C), "Y", CAST, segs=20)
        box(b, (0.24, 0.13, 0.05), (0, y, C + 0.07), CAST)                           # bearing cap
        for sx in (-1, 1):
            cyl(b, 0.012, 0.05, (sx * 0.09, y, C + 0.10), "Z", STEEL, segs=6)
        cyl(b, 0.012, 0.04, (0, y, C + 0.11), "Z", BRASS, segs=6)                     # oiler
    # A-frame columns carrying the cylinder block, a cross girder at guide height
    for y in (ENG_BEARINGS[0], ENG_BEARINGS[-1]):
        for sx in (-1, 1):
            beam(b, (sx * 0.36, y, 0.18), (sx * 0.20, y, 1.10), 0.07, 0.07, CAST)
    for sx in (-1, 1):
        box(b, (0.05, abs(ENG_BEARINGS[-1] - ENG_BEARINGS[0]) + 0.07, 0.06), (sx * 0.21, sum(ENG_BEARINGS[::2]) / 2, 1.08), CAST)
    for y in ENG_THROWS:
        # crosshead guides (vertical bars either side, the crosshead runs between them)
        for sx in (-1, 1):
            box(b, (0.03, 0.05, ENG_GUIDE[1] - ENG_GUIDE[0]), (sx * 0.095, y, sum(ENG_GUIDE) / 2), STEEL)
            box(b, (0.10, 0.03, 0.03), (sx * 0.15, y, ENG_GUIDE[1] - 0.02), CAST)
        # cylinder with lagging bands, covers, gland, drain cock; steam chest on the +X side
        cz = (ENG_CYL[0] + ENG_CYL[1]) / 2
        cyl(b, 0.15, ENG_CYL[1] - ENG_CYL[0], (0, y, cz), "Z", PAINT, segs=24)
        for z in (ENG_CYL[0] + 0.02, ENG_CYL[1] - 0.02):
            cyl(b, 0.17, 0.04, (0, y, z), "Z", CAST, segs=24)
            bolt_circle(b, 8, 0.155, (0, y, z + 0.022), "Z", STEEL, r=0.008, d=0.012)
        cyl(b, 0.155, 0.03, (0, y, cz), "Z", BRASS, segs=24)
        cyl(b, 0.05, 0.06, (0, y, ENG_CYL[0] - 0.02), "Z", BRASS, segs=12)            # gland
        box(b, (0.10, 0.18, ENG_CYL[1] - ENG_CYL[0] - 0.08), (0.20, y, cz), CAST)      # steam chest
        cyl(b, 0.012, 0.05, (0.13, y, ENG_CYL[0] + 0.02), "X", BRASS, segs=6)          # drain cock
        beam(b, (0.20, y, ENG_CYL[1] - 0.02), (0.20, 0.10, BZ + BR + 0.20), 0.05, 0.05, STEEL)   # steam pipe
    box(b, (0.30, abs(ENG_THROWS[1] - ENG_THROWS[0]), 0.10), (0.0, sum(ENG_THROWS) / 2, ENG_CYL[1] - 0.05), CAST)
    hazard(b, 2.8, (0, -1.47, 0.12), "X", h=0.08, n=28)
    out = [to_object(b, "feSteamEngine_Base", bevel=0.005)]
    # ---- crankshaft (rotating): shaft to the front flange, two cranks 90 deg apart, flywheel
    w = bmesh.new()
    shaft_end(w, -0.12, -1.5)
    pins = []
    for k, y in enumerate(ENG_THROWS):
        a_ = ENG_PHASE[k]
        px, pz = ENG_R * math.sin(a_), ENG_R * math.cos(a_)
        pins.append(Vector((px, y, C + pz)))
        for dy in (-0.045, 0.045):                                                    # webs + counterweight
            m = Matrix.Translation((0, y + dy, 0)) @ Matrix.Rotation(-a_, 4, "Y")
            r = bmesh.ops.create_cube(w, size=1.0, calc_uvs=True)
            _fin(w, CAST, m @ Matrix.Translation((0, 0, ENG_R / 2)) @ Matrix.Diagonal((0.10, 0.03, ENG_R + 0.10, 1)), r["verts"])
            r = bmesh.ops.create_cube(w, size=1.0, calc_uvs=True)
            _fin(w, RUST, m @ Matrix.Translation((0, 0, -0.07)) @ Matrix.Diagonal((0.20, 0.03, 0.08, 1)), r["verts"])
        cyl(w, 0.030, 0.12, (px, y, pz), "Y", STEEL, segs=12)                        # crank pin
    ring(w, 0.42, 0.35, 0.09, (0, ENG_FLY, 0), "Y", CAST, segs=44)                   # flywheel
    cyl(w, 0.08, 0.14, (0, ENG_FLY, 0), "Y", CAST, segs=18)
    for k in range(6):
        a_ = k * math.pi / 3
        m = Matrix.Rotation(a_, 4, "Y") @ Matrix.Translation((0.215, ENG_FLY, 0))
        r = bmesh.ops.create_cube(w, size=1.0, calc_uvs=True)
        _fin(w, CAST, m @ Matrix.Diagonal((0.28, 0.045, 0.055, 1)), r["verts"])
    out.append(to_object(w, "FeSpin_SteamFlywheel", location=(0, 0, C), bevel=0.002))
    # ---- crossheads (with piston rods into the cylinders) and connecting rods, built at crank angle 0
    for k, y in enumerate(ENG_THROWS):
        pin = pins[k]
        s0 = pin.z - C + math.sqrt(ENG_L ** 2 - pin.x ** 2)                            # crosshead above the axis
        ch = Vector((0, y, C + s0))
        x = bmesh.new()
        box(x, (0.16, 0.09, 0.08), (0, 0, 0), BRASS)                                   # crosshead block
        for sx in (-1, 1):
            box(x, (0.025, 0.07, 0.10), (sx * 0.075, 0, 0), STEEL)                    # slippers on the guides
        cyl(x, 0.022, 0.04, (0, 0, 0), "Y", STEEL, segs=10)                            # gudgeon pin
        cyl(x, 0.022, 0.48, (0, 0, 0.27), "Z", STEEL, segs=10)                         # piston rod (into the cylinder)
        cyl(x, 0.13, 0.05, (0, 0, 0.50), "Z", IRON, segs=18)                           # piston (inside)
        out.append(to_object(x, "FeCrosshead_" + str(k + 1), location=ch, bevel=0.0015))
        rd = bmesh.new()
        d = pin - ch
        beam(rd, (0, 0, 0), d, 0.035, 0.03, STEEL)                                     # the rod
        cyl(rd, 0.035, 0.05, (0, 0, 0), "Y", CAST, segs=12)                            # small end
        cyl(rd, 0.05, 0.06, d, "Y", CAST, segs=14)                                     # big end
        box(rd, (0.11, 0.065, 0.03), d + Vector((0, 0, -0.045)), CAST,
            Matrix.Rotation(math.atan2(d.x, -d.z), 4, "Y"))                            # big end cap
        out.append(to_object(rd, "FeConrod_" + str(k + 1), location=ch, bevel=0.0015))
        out.append(empty("FeCrankPin_" + str(k + 1), tuple(pin), 0.05))
    out.append(empty("FeFx_SteamVent_1", (0, 0, 2.02)))
    out.append(empty("FeFx_Smoke_1", (1.15, BY, 2.06)))
    out.append(empty("FeFx_Fire_1", (FX, FY - 0.33, 0.47)))
    out.append(empty("FeFx_Steam_1", (0.16, ENG_THROWS[0], ENG_CYL[0] + 0.01)))
    out.append(empty("FeFx_Steam_2", (0.16, ENG_THROWS[1], ENG_CYL[0] + 0.01)))
    return out


def model_m_lathe():
    """Lathe (1 block, workstation): cabinet stand, bed with ways, headstock with motor and belt guard, spinning
    chuck with the workpiece (FeSpin_x4_Chuck), carriage with tool post sliding along the bed while it works
    (FePiston_Carriage), tailstock with hand wheel."""
    b = bmesh.new()
    for x in (-0.33, 0.33):                                                           # cabinet pedestals
        plate(b, (0.26, 0.44, 0.52), (x, 0, 0.26), PAINT, "-Y", n=3)
        box(b, (0.20, 0.012, 0.16), (x, -0.226, 0.34), CAST)                        # drawer front
        box(b, (0.08, 0.02, 0.02), (x, -0.236, 0.34), STEEL)
    box(b, (0.94, 0.48, 0.03), (0, 0, 0.535), IRON)                                  # chip tray
    for sy in (-1, 1):
        box(b, (0.94, 0.02, 0.06), (0, sy * 0.23, 0.57), IRON)
    box(b, (0.90, 0.26, 0.08), (0, 0.02, 0.60), CAST)                                # bed
    for sy in (-1, 1):
        box(b, (0.90, 0.035, 0.03), (0, 0.02 + sy * 0.10, 0.655), STEEL)            # ways
    box(b, (0.80, 0.02, 0.02), (0.02, -0.12, 0.60), STEEL)                          # lead screw
    # headstock with gear cover and motor + belt guard on top
    box(b, (0.24, 0.30, 0.26), (-0.32, 0.02, 0.80), PAINT)
    box(b, (0.03, 0.30, 0.24), (-0.455, 0.02, 0.80), CAST)
    for k in range(3):
        cyl(b, 0.03, 0.03, (-0.27 + k * 0.05, -0.145, 0.88), "Y", BRASS, segs=10)   # selector knobs
    cyl(b, 0.08, 0.20, (-0.32, 0.12, 1.02), "X", PAINT, segs=18)                    # motor
    box(b, (0.06, 0.16, 0.26), (-0.44, 0.10, 0.98), HAZ)                            # belt guard
    box(b, (0.10, 0.06, 0.06), (-0.22, 0.12, 0.96), CAST)
    # tailstock + hand wheel
    box(b, (0.14, 0.18, 0.16), (0.36, 0.02, 0.74), PAINT)
    cyl(b, 0.035, 0.12, (0.30, 0.02, 0.81), "X", STEEL, segs=10)
    ring(b, 0.06, 0.05, 0.015, (0.45, 0.02, 0.80), "X", STEEL, segs=16)
    cyl(b, 0.012, 0.03, (0.43, 0.02, 0.80), "X", STEEL, segs=6)
    # work lamp on an arm
    beam(b, (0.40, 0.20, 0.60), (0.30, 0.15, 1.10), 0.02, 0.02, IRON)
    cyl(b, 0.05, 0.08, (0.28, 0.10, 1.10), "Z", HAZ, segs=12, r2=0.03)
    objs = [to_object(b, "feM_Lathe_Base", bevel=0.003)]
    ch = bmesh.new()
    cyl(ch, 0.09, 0.07, (0, 0, 0), "Y", STEEL, segs=16)
    for k in range(3):
        a_ = k * 2 * math.pi / 3
        box(ch, (0.03, 0.05, 0.05), (math.cos(a_) * 0.075, -0.04, math.sin(a_) * 0.075), CAST)
    cyl(ch, 0.035, 0.42, (0, -0.24, 0), "Y", BRASS, segs=12)
    objs.append(to_object(ch, "FeSpin_x4_Chuck", location=(-0.15, 0.02, 0.81), rotation=AX_X))
    cr = bmesh.new()                                                                  # carriage (built along Y)
    box(cr, (0.26, 0.14, 0.04), (0, 0, 0), CAST)                                    # saddle across the bed
    box(cr, (0.20, 0.10, 0.03), (0, 0, 0.035), STEEL)                               # cross slide
    box(cr, (0.06, 0.06, 0.08), (0.04, 0, 0.09), CAST)                              # tool post
    box(cr, (0.10, 0.015, 0.015), (0.10, 0, 0.11), STEEL)                           # tool bit
    ring(cr, 0.05, 0.04, 0.012, (-0.14, 0, -0.03), "X", STEEL, segs=14)              # apron wheel
    objs.append(to_object(cr, "FePiston_Carriage", location=(0.18, 0.02, 0.69), rotation=AX_X))
    return objs


def model_crusher():
    b = bmesh.new()
    box(b, (0.86, 0.72, 0.05), (0, 0, 0.025), IRON)
    for sx in (-1, 1):                                                                # heavy cast cheeks
        box(b, (0.08, 0.62, 0.66), (sx * 0.34, 0, 0.38), PAINT)
        for k in range(3):
            box(b, (0.02, 0.03, 0.62), (sx * 0.385, -0.22 + k * 0.22, 0.38), PAINT)
        for y in (0.075, -0.075):
            box(b, (0.10, 0.12, 0.12), (sx * 0.34, y, 0.72), CAST)                   # roll bearings
        box(b, (0.10, 0.16, 0.14), (sx * 0.34, 0, C), CAST)                          # drive bearings
        cyl(b, 0.012, 0.03, (sx * 0.34, 0, C + 0.08), "Z", BRASS, segs=6)
    box(b, (0.60, 0.05, 0.44), (0, 0.27, 0.46), PAINT)
    box(b, (0.60, 0.05, 0.22), (0, -0.27, 0.36), PAINT)
    # riveted hopper, hazard band on the rim
    for k, (w, z) in enumerate(((0.74, 1.00), (0.64, 0.93), (0.54, 0.86))):
        for sy in (-1, 1):
            plate(b, (w, 0.03, 0.07), (0, sy * (w / 2 - 0.02), z), IRON, "-Y" if sy < 0 else "+Y", n=4)
        for sx in (-1, 1):
            box(b, (0.03, w, 0.07), (sx * (w / 2 - 0.02), 0, z), IRON)
    hazard(b, 0.70, (0, -0.37, 1.02), "X", h=0.04, n=10)
    # drive gear guard (left) and output chute
    box(b, (0.05, 0.40, 0.42), (0.44, 0.0, 0.62), HAZ)
    box(b, (0.34, 0.26, 0.04), (0, -0.37, 0.60), STEEL)
    for sx in (-1, 1):
        box(b, (0.03, 0.26, 0.10), (sx * 0.185, -0.37, 0.64), STEEL)
    box(b, (0.36, 0.03, 0.03), (0, -0.49, 0.64), OUT)
    out = [to_object(b, "feCrusher_Base", bevel=0.003)]
    sh = bmesh.new()
    shaft_end(sh, 0.0, -0.5)
    shaft_end(sh, 0.0, 0.5)
    gear(sh, 0.12, 0.04, 18, (0, 0.415, 0), "Y", BRASS)
    out.append(to_object(sh, "FeSpin_DriveShaft", location=(0, 0, C), rotation=(0, 0, -math.pi / 2), bevel=0.002))
    for name, y, gy in (("FeSpin_x2_RollA", 0.075, True), ("FeSpin_x2_Rev_RollB", -0.075, False)):
        r = bmesh.new()
        cyl(r, 0.07, 0.58, (0, 0, 0), "Y", STEEL, segs=18)
        for k in range(12):
            a = 2 * math.pi * k / 12
            box(r, (0.022, 0.56, 0.022), (0.075 * math.cos(a), 0, 0.075 * math.sin(a)), CAST,
                Matrix.Rotation(-a, 4, "Y"))
        if gy:
            gear(r, 0.085, 0.035, 10, (0, 0.415, 0), "Y", STEEL)
            cyl(r, 0.02, 0.2, (0, 0.33, 0), "Y", STEEL, segs=8)
        out.append(to_object(r, name, location=(0, y, 0.72), rotation=(0, 0, -math.pi / 2), bevel=0.001))
    out.append(empty("FeFx_Dust_1", (0, 0, 0.98)))
    return out


def arc_solid(bm, pt, r0, r1, a0, a1, z0, z1, n, mat):
    rings_ = []
    for k in range(n + 1):
        th = a0 + (a1 - a0) * k / n
        rv = []
        for r, z in ((r0, z0), (r0, z1), (r1, z1), (r1, z0)):
            x, y = pt(r, th)
            rv.append(bm.verts.new((x, y, z)))
        rings_.append(rv)
    faces = []
    for k in range(n):
        A, B = rings_[k], rings_[k + 1]
        for i in range(4):
            j = (i + 1) % 4
            faces.append(bm.faces.new((A[i], A[j], B[j], B[i])))
    faces.append(bm.faces.new(tuple(rings_[0])))
    faces.append(bm.faces.new(tuple(reversed(rings_[-1]))))
    for f in faces:
        f.material_index = mat


def _belt_rollers(objs, back_z, front_z):
    drive = bmesh.new()
    cyl(drive, 0.055, 0.96, (0, 0, 0), "Y", STEEL, segs=18)
    for sy in (-1, 1):
        cyl(drive, 0.075, 0.04, (0, sy * 0.48, 0), "Y", CAST, segs=18)
        bolt_circle(drive, 4, 0.05, (0, sy * 0.50, 0), "Y", STEEL, r=0.008, d=0.012)
    objs.append(to_object(drive, "FeSpin_BeltDrive", location=(0, 0, C), rotation=(0, 0, math.pi / 2)))
    for name, y, z in (("FeSpin_BeltRollerFront", -0.45, front_z), ("FeSpin_BeltRollerBack", 0.45, back_z)):
        r = bmesh.new()
        cyl(r, 0.045, 0.80, (0, 0, 0), "Y", STEEL, segs=16)
        for k in range(4):
            a_ = k * math.pi / 2
            box(r, (0.012, 0.76, 0.05), (0.02 * math.cos(a_), 0, 0.02 * math.sin(a_)), SOOT,
                Matrix.Rotation(-a_, 4, "Y"))
        objs.append(to_object(r, name, location=(0, y, z), rotation=(0, 0, math.pi / 2)))


def model_conveyor():
    """Conveyor belt, same parts as the old model (Belt.cs shows/hides them): FeBeltBed, FeBeltSlats, FeRail_L/R,
    FeBeltEnd, FeCurveSet_L/R + FeCurveSlats_L/R, FeJunction, FeJunctionPosts, FeJunctionWedge, rollers.
    Travel = Blender -Y. Heavier angle-iron frame, dark rubber belt with steel cleats, hazard-striped guards."""
    base = bmesh.new()
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(base, (0.06, 0.06, 0.53), (sx * 0.44, sy * 0.42, 0.265), IRON)
            box(base, (0.10, 0.10, 0.015), (sx * 0.44, sy * 0.42, 0.0075), IRON)
        box(base, (0.06, 0.84, 0.05), (sx * 0.44, 0, 0.12), IRON)
        beam(base, (sx * 0.44, -0.40, 0.14), (sx * 0.44, 0.40, 0.48), 0.03, 0.03, RUST)   # diagonal brace
        cyl(base, 0.10, 0.03, (sx * 0.47, 0, C), "X", CAST, segs=20)
        bolt_circle(base, 4, 0.075, (sx * 0.488, 0, C), "X", STEEL, r=0.008, d=0.012)
    box(base, (0.82, 0.10, 0.04), (0, 0.42, 0.12), IRON)
    box(base, (0.82, 0.10, 0.04), (0, -0.42, 0.12), IRON)
    hazard(base, 0.80, (0, -0.475, 0.12), "X", h=0.035, n=10)
    objs = [to_object(base, "feConveyor_Base", bevel=0.003)]
    bed = bmesh.new()
    box(bed, (0.80, 0.98, 0.012), (0, 0, 0.556), IRON)
    box(bed, (0.74, 0.98, 0.012), (0, 0, 0.568), SOOT)                                # rubber belt
    objs.append(to_object(bed, "FeBeltBed"))
    for name, sx in (("FeRail_L", 1), ("FeRail_R", -1)):
        r = bmesh.new()
        box(r, (0.05, 1.0, 0.10), (sx * 0.445, 0, 0.585), PAINT)
        box(r, (0.06, 1.0, 0.02), (sx * 0.445, 0, 0.645), IRON)
        rivets(r, (sx * 0.471, -0.45, 0.56), (sx * 0.471, 0.45, 0.56), 6, axis="X")
        for dy, h in ((0.10, 0.07), (0.05, 0.05), (0.0, 0.025)):
            box(r, (0.012, 0.05, h), (sx * 0.474, -0.05 - dy, 0.60), OUT)
            box(r, (0.012, 0.05, h), (sx * 0.474, 0.30 - dy, 0.60), OUT)
        objs.append(to_object(r, name, bevel=0.002))
    end = bmesh.new()
    box(end, (0.82, 0.04, 0.12), (0, -0.47, 0.64), PAINT)
    hazard(end, 0.80, (0, -0.492, 0.64), "X", h=0.08, n=10)
    objs.append(to_object(end, "FeBeltEnd", bevel=0.002))
    sl = bmesh.new()
    for k in range(7):
        box(sl, (0.72, 0.03, 0.022), (0, -0.375 + k * 0.125, 0.585), STEEL)
        for sx in (-1, 1):
            cyl(sl, 0.007, 0.01, (sx * 0.32, -0.375 + k * 0.125, 0.597), "Z", IRON, segs=6)
    objs.append(to_object(sl, "FeBeltSlats"))
    Q = math.pi / 2
    for side, sx in (("L", 1), ("R", -1)):
        cx, cy = sx * 0.5, 0.5

        def world_pt(r, th, cx=cx, cy=cy, sx=sx):
            return (cx - sx * r * math.cos(th), cy - r * math.sin(th))

        def local_pt(r, th, sx=sx):
            return (-sx * r * math.cos(th), -r * math.sin(th))
        st = bmesh.new()
        arc_solid(st, world_pt, 0.10, 0.90, 0, Q, 0.550, 0.574, 18, SOOT)
        arc_solid(st, world_pt, 0.90, 0.96, 0, Q, 0.53, 0.64, 18, PAINT)
        arc_solid(st, world_pt, 0.89, 0.97, 0, Q, 0.64, 0.655, 18, IRON)
        arc_solid(st, world_pt, 0.04, 0.10, 0, Q, 0.53, 0.63, 6, PAINT)
        for th in (Q * 0.3, Q * 0.7):
            for k, h in enumerate((0.07, 0.045, 0.02)):
                arc_solid(st, world_pt, 0.96, 0.972, th + k * 0.06, th + k * 0.06 + 0.05, 0.59 - h / 2,
                          0.59 + h / 2, 1, OUT)
        objs.append(to_object(st, "FeCurveSet_" + side))
        cs = bmesh.new()
        n = 9
        for k in range(n):
            th = (k + 0.5) * Q / n
            arc_solid(cs, local_pt, 0.12, 0.88, th - 0.02, th + 0.02, 0.575, 0.597, 2, STEEL)
        objs.append(to_object(cs, "FeCurveSlats_" + side, location=(cx, cy, 0)))
    jn = bmesh.new()
    box(jn, (0.84, 0.92, 0.02), (0, 0, 0.565), IRON)
    for ix in range(4):
        for iy in range(4):
            x, y = -0.30 + ix * 0.2, -0.30 + iy * 0.2
            cyl(jn, 0.045, 0.012, (x, y, 0.580), "Z", CAST, segs=10)
            cyl(jn, 0.030, 0.030, (x, y, 0.596), "Z", STEEL, segs=10, r2=0.012)
    objs.append(to_object(jn, "FeJunction"))
    po = bmesh.new()
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(po, 0.05, 0.14, (sx * 0.45, sy * 0.45, 0.61), "Z", PAINT, segs=12)
            cyl(po, 0.052, 0.025, (sx * 0.45, sy * 0.45, 0.69), "Z", HAZ, segs=12)
    objs.append(to_object(po, "FeJunctionPosts"))
    wd = bmesh.new()
    for sx in (-1, 1):
        x0, y0, x1, y1 = 0.0, -0.10, sx * 0.42, -0.46
        L = math.hypot(x1 - x0, y1 - y0)
        ang = math.atan2(y1 - y0, x1 - x0)
        box(wd, (L, 0.04, 0.10), ((x0 + x1) / 2, (y0 + y1) / 2, 0.62), PAINT, Matrix.Rotation(ang, 4, "Z"))
    cyl(wd, 0.035, 0.12, (0, -0.10, 0.62), "Z", HAZ, segs=12)
    objs.append(to_object(wd, "FeJunctionWedge"))
    belt_chute(objs)
    _belt_rollers(objs, 0.56, 0.56)
    return objs



# ================================================================ round 3: duct, stand, funnel, belt chute, motors, dynamos
DUCT_W, DUCT_Z0, DUCT_Z1 = 0.46, 0.09, 0.41          # outer width, bottom, top (mouth = port 0.36 x 0.22, centre 0.25)
DUCT_SPLIT = -0.20                                   # front segment (FeDuctFront / FeDuctRamp) from here to -0.5
DZC = (DUCT_Z0 + DUCT_Z1) / 2


def duct_tube(bm, y0, y1, walls=True, top=True, bottom=True, arrows=False):
    """Straight duct box between y0..y1 (Blender Y, travel -Y): bottom, top, corner angles, optional side walls."""
    L, yc = abs(y1 - y0), (y0 + y1) / 2
    if bottom:
        box(bm, (DUCT_W, L, 0.03), (0, yc, DUCT_Z0 + 0.015), IRON)
    if top:
        plate(bm, (DUCT_W, L, 0.03), (0, yc, DUCT_Z1 - 0.015), PAINT, "-Y", n=2)
    for sx in (-1, 1):
        for z in (DUCT_Z0 + 0.02, DUCT_Z1 - 0.02):
            box(bm, (0.035, L, 0.035), (sx * (DUCT_W / 2 - 0.0175), yc, z), IRON)        # angle irons
        if walls:
            box(bm, (0.02, L, DUCT_Z1 - DUCT_Z0 - 0.04), (sx * (DUCT_W / 2 - 0.01), yc, DZC), PAINT)
    if arrows:                                                                           # direction on the lid
        for k, w in enumerate((0.16, 0.11, 0.06)):
            box(bm, (w, 0.03, 0.008), (0, yc - 0.06 - 0.035 * k, DUCT_Z1 + 0.004), OUT)


def duct_collar(bm, y, feet=True):
    """Rectangular flange ring at a duct end (mouth 0.36 x 0.22 left open), with a foot plate under it."""
    t = 0.035
    for z in (DUCT_Z0 + t / 2 - 0.01, DUCT_Z1 - t / 2 + 0.01):
        box(bm, (DUCT_W + 0.04, t, t), (0, y, z), CAST)
    for sx in (-1, 1):
        box(bm, (t, t, DUCT_Z1 - DUCT_Z0 + 0.02), (sx * (DUCT_W / 2 + 0.02 - t / 2), y, DZC), CAST)
    for sx in (-1, 1):
        for z in (DUCT_Z0 + 0.01, DUCT_Z1 - 0.01):
            cyl(bm, 0.008, t + 0.01, (sx * (DUCT_W / 2 + 0.005), y, z), "Y", STEEL, segs=6)
    if feet:
        box(bm, (DUCT_W + 0.06, 0.08, DUCT_Z0), (0, y, DUCT_Z0 / 2), IRON)               # sits on floor / stand


def model_conveyor_duct():
    """Conveyor Duct (enclosed belt). Travel = Blender -Y. Parts switched by Belt.cs BeltShape (closed):
    FeDuctWall_L/R or FeDuctSide_L/R (branch to that side face), FeDuctCapB, FeDuctFront + FeDuctCapF / FeDuctBoot,
    or FeDuctRamp (rises onto an open belt in front), FeDuctHatch (a funnel above). L = Blender +X (Unity left)."""
    b = bmesh.new()
    duct_tube(b, DUCT_SPLIT, 0.5, walls=False, arrows=True)
    duct_collar(b, 0.48)
    # drive: gear cases on both sides above the duct (the shafts come in at 0.5 m) with a chain cover across
    for sx in (-1, 1):                                       # side gear cases, on the face centre (shaft height)
        box(b, (0.20, 0.16, 0.18), (sx * 0.33, 0.0, 0.50), CAST)
        box(b, (0.21, 0.17, 0.02), (sx * 0.33, 0.0, 0.595), IRON)
        box(b, (0.10, 0.10, 0.10), (sx * 0.27, 0.0, DUCT_Z1 + 0.02), CAST)          # foot on the lid
        box(b, (0.012, 0.12, 0.10), (sx * 0.43, 0.0, 0.50), HAZ)
    out = [to_object(b, "feConveyorDuct_Base", bevel=0.003)]
    for name, sx in (("L", 1), ("R", -1)):
        w = bmesh.new()
        box(w, (0.02, 0.5 - DUCT_SPLIT, DUCT_Z1 - DUCT_Z0 - 0.04), (sx * (DUCT_W / 2 - 0.01), (0.5 + DUCT_SPLIT) / 2, DZC), PAINT)
        rivets(w, (sx * (DUCT_W / 2 + 0.002), DUCT_SPLIT + 0.05, DZC), (sx * (DUCT_W / 2 + 0.002), 0.45, DZC), 5, axis="X")
        out.append(to_object(w, "FeDuctWall_" + name, bevel=0.002))
        sd = bmesh.new()                                     # wall with an opening + a branch to the side face
        for (y0, y1) in ((DUCT_SPLIT, -0.18), (0.18, 0.5)):
            box(sd, (0.02, y1 - y0, DUCT_Z1 - DUCT_Z0 - 0.04), (sx * (DUCT_W / 2 - 0.01), (y0 + y1) / 2, DZC), PAINT)
        x0, x1 = DUCT_W / 2, 0.5
        bx = (x0 + x1) / 2
        box(sd, (x1 - x0, 0.42, 0.03), (sx * bx, 0, DUCT_Z0 + 0.015), IRON)
        plate(sd, (x1 - x0, 0.42, 0.03), (sx * bx, 0, DUCT_Z1 - 0.015), PAINT, "-Y", n=2)
        for sy in (-1, 1):
            box(sd, (x1 - x0, 0.02, DUCT_Z1 - DUCT_Z0), (sx * bx, sy * 0.20, DZC), PAINT)
        t = 0.035
        for z in (DUCT_Z0 + 0.008, DUCT_Z1 - 0.008):
            box(sd, (t, 0.46, t), (sx * (0.5 - t / 2), 0, z), CAST)
        for sy in (-1, 1):
            box(sd, (t, t, DUCT_Z1 - DUCT_Z0 + 0.02), (sx * (0.5 - t / 2), sy * 0.215, DZC), CAST)
        out.append(to_object(sd, "FeDuctSide_" + name, bevel=0.002))
    fr = bmesh.new()                                         # front straight segment with its collar
    duct_tube(fr, -0.5, DUCT_SPLIT)
    duct_collar(fr, -0.48)
    out.append(to_object(fr, "FeDuctFront", bevel=0.003))
    for name, y in (("FeDuctCapF", -0.49), ("FeDuctCapB", 0.49)):
        c = bmesh.new()
        plate(c, (0.38, 0.015, 0.24), (0, y, DZC), CAST, "-Y" if y < 0 else "+Y", n=3)
        out.append(to_object(c, name, bevel=0.002))
    bt = bmesh.new()                                         # rubber boot into a machine's port (sticks in 0.10)
    box(bt, (0.36, 0.12, 0.22), (0, -0.56, DZC), SOOT)
    box(bt, (0.38, 0.02, 0.24), (0, -0.53, DZC), STEEL)      # clamp band
    out.append(to_object(bt, "FeDuctBoot", bevel=0.004))
    rp = bmesh.new()                    # onto an open (low, 0.175 m) belt in front: the straight end of the duct
    duct_tube(rp, -0.5, DUCT_SPLIT)     # plus a transfer lip over the belt and rubber skirts at its sides
    duct_collar(rp, -0.48)
    box(rp, (0.36, 0.12, 0.012), (0, -0.55, DUCT_Z0 + 0.10), STEEL)                  # lip, just over the lona
    for sx in (-1, 1):
        box(rp, (0.012, 0.12, 0.10), (sx * 0.18, -0.55, DUCT_Z0 + 0.15), SOOT)       # skirts
    box(rp, (0.38, 0.12, 0.02), (0, -0.55, DUCT_Z1 - 0.02), PAINT)                   # hood
    out.append(to_object(rp, "FeDuctRamp", bevel=0.003))
    ht = bmesh.new()                                         # hatch: a chute up to the top face for a funnel above
    box(ht, (0.30, 0.30, 0.03), (0, 0.0, DUCT_Z1 + 0.015), CAST)
    for sx in (-1, 1):
        box(ht, (0.025, 0.26, 1.0 - DUCT_Z1), (sx * 0.13, 0.0, (1.0 + DUCT_Z1) / 2), PAINT)
        box(ht, (0.26, 0.025, 1.0 - DUCT_Z1), (0, sx * 0.13, (1.0 + DUCT_Z1) / 2), PAINT)
    box(ht, (0.32, 0.32, 0.03), (0, 0.0, 0.985), CAST)
    out.append(to_object(ht, "FeDuctHatch", bevel=0.002))
    dr = bmesh.new()                                         # two hubs on the side faces (no shaft across the top)
    for sy in (-1, 1):
        cyl(dr, 0.03, 0.30, (0, sy * 0.35, 0), "Y", STEEL, segs=12)
        cyl(dr, 0.075, 0.04, (0, sy * 0.48, 0), "Y", CAST, segs=18)
        bolt_circle(dr, 4, 0.05, (0, sy * 0.50, 0), "Y", STEEL, r=0.008, d=0.012)
    root = bpy.data.objects.new("feConveyorDuct_Root", None)
    out.append(to_object(dr, "FeSpin_BeltDrive", location=(0.0, 0.0, C), rotation=(0, 0, math.pi / 2)))
    return [root] + out


def model_conveyor_stand():
    """Conveyor Stand: angle-iron trestle 1 block high with a cradle that rises 0.09 into the block above, where a
    Conveyor Duct's feet sit."""
    b = bmesh.new()
    for sx in (-1, 1):
        for sy in (-1, 1):
            beam(b, (sx * 0.40, sy * 0.40, 0.0), (sx * 0.30, sy * 0.40, 0.97), 0.06, 0.06, IRON)
            box(b, (0.14, 0.14, 0.015), (sx * 0.40, sy * 0.40, 0.0075), IRON)
            cyl(b, 0.012, 0.03, (sx * 0.43, sy * 0.43, 0.02), "Z", STEEL, segs=6)
        beam(b, (sx * 0.38, -0.40, 0.12), (sx * 0.31, 0.40, 0.85), 0.03, 0.03, RUST)    # X braces (sides)
        beam(b, (sx * 0.38, 0.40, 0.12), (sx * 0.31, -0.40, 0.85), 0.03, 0.03, RUST)
        box(b, (0.06, 0.86, 0.05), (sx * 0.355, 0, 0.30), IRON)                         # side rails
    for sy in (-1, 1):
        box(b, (0.70, 0.06, 0.05), (0, sy * 0.40, 0.30), IRON)
    plate(b, (0.70, 0.92, 0.05), (0, 0, 0.975), CAST, "-Y", n=5)                        # top
    hazard(b, 0.70, (0, -0.465, 0.975), "X", h=0.04, n=10)
    for sx in (-1, 1):                                                                   # cradle lips
        box(b, (0.04, 0.92, 0.09), (sx * (DUCT_W / 2 + 0.05), 0, 1.0 + 0.045), CAST)
    for sy in (-0.3, 0.3):
        box(b, (DUCT_W + 0.14, 0.06, 0.02), (0, sy, 1.01), STEEL)
    return [to_object(b, "feConveyorStand_Base", bevel=0.003)]


def model_funnel():
    """Funnel, any orientation (local front = Blender -Y). Back plate on the source (+Y face), a riveted hopper on
    the axis at belt height, and three spouts (FunnelShape shows one): FeFunnelSpoutBelt onto an open belt's
    surface, FeFunnelSpoutDuct down into a duct's mouth (port height), FeFunnelSpout (to the face centre, e.g.
    facing down into a duct's hatch)."""
    b = bmesh.new()
    plate(b, (0.86, 0.06, 0.86), (0, 0.46, 0.50), CAST, "+Y", n=5)
    HZ = 0.62
    for k, (w, y) in enumerate(((0.70, 0.38), (0.56, 0.28), (0.42, 0.18), (0.28, 0.08))):
        for sz in (-1, 1):
            box(b, (w, 0.10, 0.025), (0, y, HZ + sz * (w / 2 - 0.0125)), PAINT)
        for sx in (-1, 1):
            box(b, (0.025, 0.10, w), (sx * (w / 2 - 0.0125), y, HZ), PAINT)
    box(b, (0.30, 0.04, 0.30), (0, 0.03, HZ), IRON)                                    # throat flange
    for sx in (-1, 1):                                                                 # mounting brackets
        beam(b, (sx * 0.30, 0.43, 0.15), (sx * 0.18, 0.10, HZ - 0.12), 0.03, 0.03, IRON)
    hazard(b, 0.70, (0, 0.41, 0.94), "X", h=0.035, n=10)
    out = [to_object(b, "feFunnel_Base", bevel=0.003)]

    def chute(name, p0, p1, w=0.26, h=0.16, closed=False, lip=None):
        bm = bmesh.new()
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        m = Matrix.Translation((p0 + p1) / 2) @ d.to_track_quat("Y", "Z").to_matrix().to_4x4()
        parts = [((w, d.length, 0.025), (0, 0, -h / 2), STEEL)]
        for sx in (-1, 1):
            parts.append(((0.02, d.length, h), (sx * w / 2, 0, 0), PAINT))
        if closed:
            parts.append(((w, d.length, 0.02), (0, 0, h / 2), PAINT))
        for size, off, mat in parts:
            r = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)
            _fin(bm, mat, m @ Matrix.Translation(off) @ Matrix.Diagonal((*size, 1)), r["verts"])
        if lip:
            box(bm, (w + 0.06, 0.03, h + 0.06), lip, CAST)
        out.append(to_object(bm, name, bevel=0.002))
    # the low belt (Harrison, 2026-11-24): the lona is at 0.175 m, so the spout drops to just over it
    chute("FeFunnelSpoutBelt", (0, 0.03, HZ), (0, -0.50, 0.27), w=0.30, h=0.16, lip=(0, -0.485, 0.27))
    chute("FeFunnelSpoutDuct", (0, 0.03, HZ), (0, -0.49, DZC), w=0.34, h=0.20, closed=True, lip=(0, -0.485, DZC))
    chute("FeFunnelSpout", (0, 0.03, HZ), (0, -0.49, 0.50), w=0.26, h=0.20, closed=True, lip=(0, -0.485, 0.50))
    return out


def belt_chute(objs):
    """Open belt into a machine or a duct: a steep transfer chute from the belt's end down into the port (centre
    0.25, the face at y = -0.5), sticking 0.06 into it. Shown by BeltShape."""
    bm = bmesh.new()
    p0, p1 = Vector((0, -0.44, 0.585)), Vector((0, -0.56, DZC - 0.04))
    d = p1 - p0
    m = Matrix.Translation((p0 + p1) / 2) @ d.to_track_quat("Y", "Z").to_matrix().to_4x4()
    for size, off, mat in (((0.34, d.length, 0.02), (0, 0, 0), STEEL),
                           ((0.02, d.length, 0.12), (0.17, 0, 0.05), PAINT),
                           ((0.02, d.length, 0.12), (-0.17, 0, 0.05), PAINT)):
        r = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)
        _fin(bm, mat, m @ Matrix.Translation(off) @ Matrix.Diagonal((*size, 1)), r["verts"])
    box(bm, (0.40, 0.10, 0.025), (0, -0.46, 0.70), PAINT)                              # hood over the drop
    for sx in (-1, 1):
        box(bm, (0.02, 0.10, 0.13), (sx * 0.20, -0.46, 0.64), PAINT)
        box(bm, (0.04, 0.04, 0.58), (sx * 0.20, -0.44, 0.29), IRON)                    # chute legs
    objs.append(to_object(bm, "FeBeltChute", bevel=0.002))


# ---------------------------------------------------------------- electric motors and dynamos
def finned_frame(bm, r, length, y0, z, mat=PAINT, fins=18):
    """TEFC motor frame along Y: drum with axial cooling fins, end shields with bolts."""
    cyl(bm, r, length, (0, y0, z), "Y", mat, segs=28)
    for k in range(fins):
        a = 2 * math.pi * k / fins
        if math.sin(a) < -0.6:
            continue                                                                    # none under it (feet)
        box(bm, (0.018, length * 0.92, r * 0.18), (math.cos(a) * (r + r * 0.06), y0, z + math.sin(a) * (r + r * 0.06)),
            mat, Matrix.Rotation(-a + math.pi / 2, 4, "Y"))
    for s_ in (-1, 1):
        y = y0 + s_ * (length / 2 + 0.02)
        cyl(bm, r * 0.95, 0.04, (0, y, z), "Y", CAST, segs=28)
        bolt_circle(bm, 6, r * 0.82, (0, y + s_ * 0.022, z), "Y", STEEL, r=0.008, d=0.01)
        cyl(bm, r * 0.35, 0.05, (0, y + s_ * 0.03, z), "Y", CAST, segs=16)              # bearing cap


def motor_feet(bm, w, r, z, y_span):
    for sy in (-1, 1):
        box(bm, (w, 0.08, z - r * 0.6), (0, sy * y_span, (z - r * 0.6) / 2 + 0.02), CAST)
        box(bm, (w + 0.06, 0.12, 0.025), (0, sy * y_span, 0.0125), IRON)
        for sx in (-1, 1):
            cyl(bm, 0.012, 0.03, (sx * w * 0.42, sy * y_span, 0.035), "Z", STEEL, segs=6)


def terminal_box(bm, x, y, z, s=1.0):
    box(bm, (0.14 * s, 0.12 * s, 0.10 * s), (x, y, z), CAST)
    box(bm, (0.15 * s, 0.13 * s, 0.015 * s), (x, y, z + 0.055 * s), IRON)
    cyl(bm, 0.02 * s, 0.08 * s, (x + 0.09 * s, y, z - 0.01), "X", STEEL, segs=8)       # conduit gland
    box(bm, (0.002 + 0.01 * s, 0.08 * s, 0.05 * s), (x - 0.075 * s, y, z), BRASS)     # name plate


def eye_bolt(bm, x, y, z):
    cyl(bm, 0.012, 0.04, (x, y, z), "Z", STEEL, segs=6)
    ring(bm, 0.03, 0.018, 0.012, (x, y, z + 0.045), "Y", STEEL, segs=12)


def wire(objs, loc):
    w = bpy.data.objects.new("WireOffset", None)
    w.empty_display_type = "SPHERE"
    w.empty_display_size = 0.03
    w.location = loc
    objs.append(w)


def model_electric_motor():
    b = bmesh.new()
    finned_frame(b, 0.20, 0.52, 0.0, C)
    motor_feet(b, 0.40, 0.20, C, 0.17)
    terminal_box(b, 0.0, 0.05, C + 0.25)
    eye_bolt(b, 0.0, -0.12, C + 0.21)
    hazard(b, 0.40, (0, -0.235, 0.05), "X", h=0.035, n=8)
    objs = [to_object(b, "feElectricMotor_Base", bevel=0.004)]
    rot = bmesh.new()
    shaft_end(rot, 0.0, -0.5)
    shaft_end(rot, 0.0, 0.5)
    objs.append(to_object(rot, "FeSpin_Motor1", location=(0, 0, C), bevel=0.002))
    wire(objs, (0, 0.05, C + 0.36))
    return objs


def model_electric_motor2():
    b = bmesh.new()
    finned_frame(b, 0.28, 0.60, 0.0, C, fins=22)
    motor_feet(b, 0.56, 0.28, C, 0.21)
    for y in (-0.15, 0.15):
        eye_bolt(b, 0.0, y, C + 0.31)
    terminal_box(b, 0.20, 0.08, C + 0.26, s=1.4)
    box(b, (0.36, 0.30, 0.02), (0, 0, C + 0.295), CAST)                                 # top cover plate
    hazard(b, 0.56, (0, -0.275, 0.05), "X", h=0.04, n=10)
    objs = [to_object(b, "feElectricMotor2_Base", bevel=0.004)]
    rot = bmesh.new()
    shaft_end(rot, 0.0, -0.5)
    shaft_end(rot, 0.0, 0.5)
    objs.append(to_object(rot, "FeSpin_Motor2", location=(0, 0, C), bevel=0.002))
    wire(objs, (0.20, 0.08, C + 0.40))
    return objs


def big_skid(bm):
    for x in (-1.3, 1.3):
        box(bm, (0.14, 2.96, 0.04), (x, 0, 0.02), IRON)
        box(bm, (0.04, 2.96, 0.12), (x, 0, 0.08), IRON)
        box(bm, (0.14, 2.96, 0.04), (x, 0, 0.14), IRON)
    for y in (-1.35, -0.6, 0.35, 1.35):
        box(bm, (2.56, 0.12, 0.10), (0, y, 0.10), IRON)
    plate(bm, (2.9, 2.9, 0.03), (0, 0, 0.175), CAST, "-Y", n=14)
    hazard(bm, 2.8, (0, -1.465, 0.10), "X", h=0.07, n=28)


def gear_case_front(bm):
    """Reduction / step-up gear case at the front: from the big machine's axis (z 1.05) down to the shaft at the
    front centre of the bottom layer (z 0.5)."""
    box(bm, (0.76, 0.46, 1.16), (0, -0.95, 0.76), CAST)
    for z in (0.30, 0.76, 1.22):
        box(bm, (0.80, 0.50, 0.04), (0, -0.95, z), CAST)
    for sx in (-1, 1):
        box(bm, (0.03, 0.40, 1.0), (sx * 0.395, -0.95, 0.76), CAST)
    cyl(bm, 0.03, 0.05, (0.25, -0.95, 1.36), "Z", BRASS, segs=10)                       # oil filler
    cyl(bm, 0.06, 0.03, (-0.2, -1.18, 0.90), "Y", GLASS, segs=14)                       # oil sight glass
    cyl(bm, 0.14, 0.06, (0, -1.19, C), "Y", CAST, segs=20)                              # output bearing


def model_electric_motor3():
    b = bmesh.new()
    big_skid(b)
    finned_frame(b, 0.70, 1.9, 0.40, 1.05, fins=30)
    for x in (-0.55, 0.55):
        for y in (-0.25, 1.05):
            box(b, (0.24, 0.30, 0.62), (x, y, 0.49), CAST)
    gear_case_front(b)
    # fan cowl at the back with a grille (the fan FeSpin_Motor3Fan turns behind it)
    cyl(b, 0.66, 0.14, (0, 1.40, 1.05), "Y", PAINT, segs=28)
    for k in range(5):
        box(b, (1.20, 0.02, 0.03), (0, 1.48, 0.80 + k * 0.12), STEEL)
    # control cabinet (left) and cable tray, ladder (right), terminal box and eyes on top
    plate(b, (0.40, 0.70, 1.20), (1.20, -0.50, 0.80), PAINT, "+X", n=5)
    for k in range(3):
        cyl(b, 0.05, 0.02, (1.41, -0.70 + k * 0.20, 1.20), "X", BRASS, segs=14)
        cyl(b, 0.04, 0.022, (1.415, -0.70 + k * 0.20, 1.20), "X", GLASS, segs=14)
    box(b, (0.02, 0.10, 0.10), (1.41, -0.50, 0.90), HAZ)
    beam(b, (1.20, -0.10, 1.40), (0.40, 0.40, 1.80), 0.10, 0.04, IRON)
    for sx in (-1, 1):
        beam(b, (-1.25 + sx * 0.15, 1.10, 0.18), (-1.25 + sx * 0.15, 0.60, 1.80), 0.03, 0.03, IRON)
    for k in range(6):
        box(b, (0.30, 0.03, 0.03), (-1.25, 1.03 - k * 0.085, 0.40 + k * 0.24), STEEL)
    terminal_box(b, 0.0, 0.35, 1.84, s=2.0)
    for y in (-0.2, 1.0):
        eye_bolt(b, 0.0, y, 1.76)
    objs = [to_object(b, "feElectricMotor3_Base", bevel=0.005)]
    outp = bmesh.new()
    shaft_end(outp, -1.10, -1.5)
    objs.append(to_object(outp, "FeSpin_Motor3Out", location=(0, 0, C), bevel=0.002))
    fan = bmesh.new()
    cyl(fan, 0.08, 0.10, (0, 0, 0), "Y", CAST, segs=12)
    for k in range(8):
        a_ = k * math.pi / 4
        m = Matrix.Rotation(a_, 4, "Y") @ Matrix.Translation((0.30, 0, 0))
        r = bmesh.ops.create_cube(fan, size=1.0, calc_uvs=True)
        _fin(fan, STEEL, m @ Matrix.Rotation(math.radians(25), 4, "X") @ Matrix.Diagonal((0.46, 0.015, 0.12, 1)), r["verts"])
    objs.append(to_object(fan, "FeSpin_Motor3Fan", location=(0, 1.38, 1.05)))
    wire(objs, (0, 0.35, 2.10))
    return objs


def field_yoke(bm, r, length, y0, z, poles=4):
    """Open dynamo: octagonal cast yoke, copper field coils showing between the bars, ventilation windows."""
    cyl(bm, r, length, (0, y0, z), "Y", PAINT, segs=8)
    for k in range(8):
        a = 2 * math.pi * k / 8 + math.pi / 8
        box(bm, (r * 0.55, length * 0.70, 0.012), (math.cos(a) * r * 0.93, y0, z + math.sin(a) * r * 0.93), SOOT,
            Matrix.Rotation(-a + math.pi / 2, 4, "Y"))                                  # vent windows
    for k in range(poles):
        a = 2 * math.pi * k / poles + math.pi / 4
        box(bm, (r * 0.36, length * 0.62, 0.04), (math.cos(a) * r * 0.95, y0, z + math.sin(a) * r * 0.95), COPPER,
            Matrix.Rotation(-a + math.pi / 2, 4, "Y"))                                  # coils seen in the windows
    for s_ in (-1, 1):
        cyl(bm, r * 1.02, 0.04, (0, y0 + s_ * length / 2, z), "Y", CAST, segs=8)


def insulator(bm, x, y, z, n=3, s=1.0):
    for k in range(n):
        cyl(bm, 0.035 * s, 0.02 * s, (x, y, z + k * 0.04 * s), "Z", GLASS, segs=12, r2=0.024 * s)
    cyl(bm, 0.008 * s, 0.05 * s, (x, y, z + n * 0.04 * s), "Z", COPPER, segs=6)


def model_dynamo():
    b = bmesh.new()
    field_yoke(b, 0.25, 0.40, 0.04, C)
    # brush gear around the commutator (commutator spins on the armature at y = -0.27)
    cyl(b, 0.12, 0.02, (0, -0.215, C), "Y", CAST, segs=16)
    for k in range(4):
        a = 2 * math.pi * k / 4 + math.pi / 4
        box(b, (0.03, 0.04, 0.05), (math.cos(a) * 0.115, -0.27, C + math.sin(a) * 0.115), BRASS,
            Matrix.Rotation(-a + math.pi / 2, 4, "Y"))
    motor_feet(b, 0.46, 0.25, C, 0.15)
    box(b, (0.16, 0.12, 0.08), (0, 0.04, C + 0.29), CAST)                               # terminal block
    insulator(b, -0.04, 0.04, C + 0.33)
    insulator(b, 0.04, 0.04, C + 0.33)
    beam(b, (0.10, -0.27, C + 0.10), (0.06, 0.02, C + 0.30), 0.012, 0.012, COPPER)       # brush leads
    beam(b, (-0.10, -0.27, C + 0.10), (-0.06, 0.02, C + 0.30), 0.012, 0.012, COPPER)
    hazard(b, 0.46, (0, -0.215, 0.05), "X", h=0.035, n=8)
    objs = [to_object(b, "feDynamo_Base", bevel=0.004)]
    arm = bmesh.new()
    shaft_end(arm, 0.0, -0.5)
    shaft_end(arm, 0.0, 0.5)
    cyl(arm, 0.085, 0.07, (0, -0.27, 0), "Y", COPPER, segs=16)                        # commutator
    for k in range(12):
        a = 2 * math.pi * k / 12
        box(arm, (0.006, 0.072, 0.012), (math.cos(a) * 0.086, -0.27, math.sin(a) * 0.086), SOOT,
            Matrix.Rotation(-a, 4, "Y"))                                                 # segment gaps
    objs.append(to_object(arm, "FeSpin_DynamoArmature", location=(0, 0, C), bevel=0.002))
    wire(objs, (0, 0.04, C + 0.52))
    return objs


def model_dynamo2():
    b = bmesh.new()
    big_skid(b)
    field_yoke(b, 0.80, 1.80, 0.35, 1.05, poles=6)
    for x in (-0.60, 0.60):
        for y in (-0.40, 1.10):
            box(b, (0.26, 0.32, 0.58), (x, y, 0.47), CAST)
    gear_case_front(b)
    # exciter at the back + rotor end (FeSpin_Dynamo2Rotor turns in front of it)
    cyl(b, 0.40, 0.28, (0, 1.22, 1.05), "Y", PAINT, segs=8)
    # switchboard (left): panel with gauges and knife switches; bus bars up to the insulators on top
    plate(b, (0.30, 1.0, 1.30), (1.25, -0.30, 0.85), PAINT, "+X", n=6)
    for k in range(3):
        cyl(b, 0.07, 0.02, (1.405, -0.62 + k * 0.32, 1.25), "X", BRASS, segs=16)
        cyl(b, 0.058, 0.022, (1.41, -0.62 + k * 0.32, 1.25), "X", GLASS, segs=16)
        box(b, (0.03, 0.06, 0.16), (1.41, -0.62 + k * 0.32, 0.90), COPPER)
    for k, x in enumerate((-0.30, 0.0, 0.30)):
        beam(b, (1.25, -0.30 + 0.1 * (k - 1), 1.50), (x, 0.35, 1.85), 0.025, 0.025, COPPER)
        insulator(b, x, 0.35, 1.86, n=4, s=1.4)
    for sx in (-1, 1):                                                                   # ladder (right)
        beam(b, (-1.25 + sx * 0.15, 1.15, 0.18), (-1.25 + sx * 0.15, 0.70, 1.80), 0.03, 0.03, IRON)
    for k in range(6):
        box(b, (0.30, 0.03, 0.03), (-1.25, 1.08 - k * 0.08, 0.40 + k * 0.24), STEEL)
    objs = [to_object(b, "feDynamo2_Base", bevel=0.005)]
    inp = bmesh.new()
    shaft_end(inp, -1.10, -1.5)
    objs.append(to_object(inp, "FeSpin_Dynamo2In", location=(0, 0, C), bevel=0.002))
    rotor = bmesh.new()
    cyl(rotor, 0.12, 0.10, (0, 0, 0), "Y", STEEL, segs=16)
    cyl(rotor, 0.30, 0.04, (0, 0.02, 0), "Y", COPPER, segs=24)
    for k in range(6):
        a_ = k * math.pi / 3
        m = Matrix.Rotation(a_, 4, "Y") @ Matrix.Translation((0.20, 0.05, 0))
        r = bmesh.ops.create_cube(rotor, size=1.0, calc_uvs=True)
        _fin(rotor, SOOT, m @ Matrix.Diagonal((0.20, 0.02, 0.04, 1)), r["verts"])
    objs.append(to_object(rotor, "FeSpin_Dynamo2Rotor", location=(0, 1.42, 1.05)))
    wire(objs, (0, 0.35, 2.12))
    return objs



# ================================================================ round 5: condenser, process machines, ammo press
def pipe_run(bm, pts, r=0.035, mat=None, elbows=True):
    """A pipe through a list of points (straight runs, a ball at each bend)."""
    mat = STEEL if mat is None else mat
    for a, b_ in zip(pts, pts[1:]):
        a, b_ = Vector(a), Vector(b_)
        d = b_ - a
        if d.length < 1e-4:
            continue
        m = Matrix.Translation((a + b_) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=10, radius1=r, radius2=r,
                                    depth=d.length, calc_uvs=True)
        _fin(bm, mat, m, res["verts"])
    if elbows:
        for p in pts[1:-1]:
            cyl(bm, r * 1.25, r * 2.5, p, "Z", CAST, segs=10)


def gauge(objs, bm, centre, name, r=0.07):
    """A pressure gauge facing -Y with its needle as its own object (pivot at the dial centre, pointing up)."""
    c = Vector(centre)
    cyl(bm, r, 0.03, c, "Y", BRASS, segs=20)
    cyl(bm, r * 0.86, 0.032, c + Vector((0, -0.002, 0)), "Y", GLASS, segs=20)
    for k in range(7):                                                                  # scale ticks
        a = math.radians(-135 + 45 * k)
        box(bm, (0.006, 0.004, 0.012), c + Vector((math.sin(a) * r * 0.7, -0.019, math.cos(a) * r * 0.7)),
            IN if k < 4 else (HAZ if k < 6 else OUT), Matrix.Rotation(-a, 4, "Y"))
    n = bmesh.new()
    box(n, (0.006, 0.004, r * 0.75), (0, 0, r * 0.32), OUT)
    cyl(n, 0.008, 0.008, (0, 0, 0), "Y", STEEL, segs=8)
    objs.append(to_object(n, name, location=c + Vector((0, -0.022, 0))))


def model_condenser():
    """Air-cooled condenser, 2 wide x 2 high (centred on x; parent column at x -0.5). Steam comes in at the back of
    the upper parent cell into two steam headers, goes down through two finned tube cores (front and back walls of
    a plenum box) while the fan on top (FeFan_Condenser) pulls air through them, and the condensate runs from the
    bottom headers through a sight-flow glass (FeFx_Drip_1) into a receiver drum with a level gauge (FeLevelLiquid,
    a water column in a glass tube) and leaves at the front of the lower parent cell. The steam pressure shows on a
    gauge (FeNeedle_Steam). FeFx_Steam_1: warm haze over the fan while it condenses."""
    objs_extra = []
    b = bmesh.new()
    X0, X1 = -0.93, 0.93
    for y in (-0.42, 0.42):
        box(b, (1.92, 0.08, 0.08), (0, y, 0.04), IRON)
    for x in (-0.80, 0.0, 0.80):
        box(b, (0.08, 0.92, 0.06), (x, 0, 0.11), IRON)
    hazard(b, 1.86, (0, -0.465, 0.04), "X", h=0.06, n=18)
    # receiver drum on saddles
    DY, DZ, DR = 0.08, 0.34, 0.20
    cyl(b, DR, 1.50, (0, DY, DZ), "X", PAINT, segs=28)
    for sx in (-1, 1):
        cyl(b, DR * 0.98, 0.06, (sx * 0.77, DY, DZ), "X", CAST, segs=28)                 # dished ends
        box(b, (0.10, 0.36, DZ - 0.10), (sx * 0.55, DY, (DZ - 0.10) / 2 + 0.12), CAST)  # saddles
    for x in (-0.40, 0.0, 0.40):
        cyl(b, DR + 0.01, 0.03, (x, DY, DZ), "X", IRON, segs=28)
    # level gauge on the drum front: two valve blocks and a guarded glass tube (FeLevelLiquid inside)
    GX, GY, G0, G1 = 0.55, -0.20, 0.16, 0.54
    for z in (G0, G1):
        box(b, (0.06, 0.06, 0.05), (GX, GY, z), BRASS)
        pipe_run(b, [(GX, GY + 0.03, z), (GX, DY - DR + 0.02, z if z < DZ + DR - 0.02 else DZ + 0.1)], r=0.012, mat=BRASS)
    for k in range(3):
        a = 2 * math.pi * k / 3
        cyl(b, 0.004, G1 - G0, (GX + 0.028 * math.cos(a), GY + 0.028 * math.sin(a), (G0 + G1) / 2), "Z", STEEL, segs=6)
    cyl(b, 0.006, G1 - G0 - 0.05, (GX - 0.035, GY - 0.02, (G0 + G1) / 2), "Z", HAZ, segs=6)  # scale strip
    # plenum box with the two finned cores (front and back walls), end panels, top deck
    Z0, Z1 = 0.62, 1.78
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(b, (0.06, 0.06, Z1 - Z0 + 0.06), (sx * 0.90, sy * 0.40, (Z0 + Z1) / 2), IRON)
            box(b, (0.06, 0.06, Z0 - 0.14), (sx * 0.90, sy * 0.40, (Z0 + 0.14) / 2), IRON)   # legs to the skid
        plate(b, (0.03, 0.74, Z1 - Z0), (sx * 0.905, 0, (Z0 + Z1) / 2), PAINT, "+X" if sx > 0 else "-X", n=6)
    for sy in (-1, 1):
        y = sy * 0.40
        for k in range(34):                                                                 # fins
            box(b, (0.006, 0.07, Z1 - Z0 - 0.10), (-0.82 + k * 0.05, y, (Z0 + Z1) / 2), STEEL)
        for k in range(6):                                                                  # tube rows
            cyl(b, 0.012, 1.74, (0, y, Z0 + 0.12 + k * 0.18), "X", COPPER, segs=8)
        box(b, (1.80, 0.08, 0.04), (0, y, Z0 + 0.02), IRON)
        box(b, (1.80, 0.08, 0.04), (0, y, Z1 - 0.02), IRON)
        cyl(b, 0.05, 1.82, (0, y, Z1 + 0.04), "X", PAINT, segs=14)                         # steam header
        cyl(b, 0.04, 1.82, (0, y, Z0 - 0.04), "X", PAINT, segs=12)                         # condensate header
    plate(b, (1.84, 0.84, 0.03), (0, 0, Z1 + 0.10), CAST, "-Y", n=9)
    ring(b, 0.37, 0.33, 0.12, (0, 0, Z1 + 0.17), "Z", IRON, segs=32)                        # fan shroud
    for k in range(4):
        box(b, (0.70, 0.02, 0.02), (0, 0, Z1 + 0.235), STEEL, Matrix.Rotation(k * math.pi / 4, 4, "Z"))
    cyl(b, 0.07, 0.10, (0, 0, Z1 + 0.15), "Z", CAST, segs=12)
    box(b, (0.16, 0.12, 0.12), (0.55, 0.20, Z1 + 0.18), CAST)                              # motor box
    # steam in at the back of the upper parent cell -> back header; a crossover to the front header
    cyl(b, PIPE_R, 0.10, (-0.5, 0.44, 1.0 + C), "Y", STEEL, segs=16)
    flange(b, (-0.5, 0.485, 1.0 + C), "Y", IN)
    pipe_run(b, [(-0.5, 0.40, 1.0 + C), (-0.5, 0.40, Z1 + 0.04)], r=0.06)
    pipe_run(b, [(0.88, -0.40, Z1 + 0.04), (0.96, -0.40, Z1 + 0.04), (0.96, 0.40, Z1 + 0.04), (0.88, 0.40, Z1 + 0.04)], r=0.04)
    # condensate drains to the drum: the front one through a sight-flow glass (drops inside)
    pipe_run(b, [(0.30, 0.40, Z0 - 0.04), (0.30, 0.40, 0.56), (0.30, DY + 0.10, DZ + DR - 0.02)], r=0.025)
    SFX, SFY, SFZ = -0.30, -0.40, 0.48
    pipe_run(b, [(SFX, SFY, Z0 - 0.04), (SFX, SFY, SFZ + 0.07)], r=0.025)
    for z in (SFZ + 0.07, SFZ - 0.07):
        cyl(b, 0.05, 0.02, (SFX, SFY, z), "Z", BRASS, segs=14)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        cyl(b, 0.006, 0.14, (SFX + 0.045 * math.cos(a), SFY + 0.045 * math.sin(a), SFZ), "Z", BRASS, segs=6)
    pipe_run(b, [(SFX, SFY, SFZ - 0.07), (SFX, SFY, 0.42), (SFX, DY - 0.12, DZ + 0.12)], r=0.025)
    # water out at the front of the lower parent cell
    pipe_run(b, [(-0.5, DY - DR + 0.02, DZ), (-0.5, -0.30, DZ), (-0.5, -0.30, C), (-0.5, -0.44, C)], r=0.05)
    flange(b, (-0.5, -0.485, C), "Y", OUT)
    ring(b, 0.06, 0.045, 0.012, (-0.5, -0.36, C + 0.10), "Y", RUST, segs=12)              # valve wheel
    pipe_run(b, [(-0.5, -0.36, C + 0.02), (-0.5, -0.36, C + 0.10)], r=0.008, elbows=False)
    gauge(objs_extra, b, (0.72, -0.445, 1.52), "FeNeedle_Steam")
    pipe_run(b, [(0.72, -0.43, 1.46), (0.72, -0.40, Z1 + 0.0)], r=0.01, mat=BRASS)
    objs = [to_object(b, "feCondenser_Base", bevel=0.004)] + objs_extra
    liq = bmesh.new()
    box(liq, (0.024, 0.024, G1 - G0 - 0.06), (0, 0, (G1 - G0 - 0.06) / 2), LIQUID)
    objs.append(to_object(liq, "FeLevelLiquid", location=(GX, GY, G0 + 0.03)))
    fan = bmesh.new()
    cyl(fan, 0.06, 0.05, (0, 0, 0), "Y", CAST, segs=10)
    for k in range(6):
        a_ = k * 2 * math.pi / 6
        m = Matrix.Rotation(a_, 4, "Y") @ Matrix.Translation((0.18, 0, 0))
        r = bmesh.ops.create_cube(fan, size=1.0, calc_uvs=True)
        _fin(fan, STEEL, m @ Matrix.Rotation(math.radians(25), 4, "X") @ Matrix.Diagonal((0.28, 0.012, 0.10, 1)), r["verts"])
    objs.append(to_object(fan, "FeFan_Condenser", location=(0, 0, Z1 + 0.18), rotation=(math.pi / 2, 0, 0)))
    wire(objs, (0.55, 0.20, Z1 + 0.27))
    objs.append(empty("FeFx_Steam_1", (0, 0, Z1 + 0.26)))
    objs.append(empty("FeFx_Drip_1", (SFX, SFY, SFZ + 0.05)))
    return objs


def flare(bm, objs, x, y, z0, h, name="FeFx_Fire_1"):
    """Biogas flare stack: a thin pipe with a wind cap; the flame burns at its tip while the digester works."""
    cyl(bm, 0.025, h, (x, y, z0 + h / 2), "Z", STEEL, segs=10)
    cyl(bm, 0.045, 0.05, (x, y, z0 + h), "Z", CAST, segs=12)
    for k in range(3):
        a = 2 * math.pi * k / 3
        box(bm, (0.004, 0.004, 0.06), (x + 0.05 * math.cos(a), y + 0.05 * math.sin(a), z0 + h + 0.04), STEEL)
    objs.append(empty(name, (x, y, z0 + h + 0.03)))


def model_biodigester():
    """Biodigester (1 block): a floating-drum digester. The mash tank with a porthole (the mash surface FeSurface and
    gas bubbles inside), and on top a steel gas holder that floats in a water seal: it rises with the fill and turns
    slowly while it works (FeSurface_r0.08_GasHolder, as real floating drums are turned to break the scum). Gas
    pipe with a gauge to a flare (FeFx_Fire_1). Water in at the back, the chute in front (0.60)."""
    objs = []
    b = bmesh.new()
    box(b, (0.84, 0.84, 0.05), (0, 0, 0.025), IRON)
    cyl(b, 0.36, 0.54, (0, 0.04, 0.32), "Z", PAINT, segs=32)                            # mash tank
    for z in (0.08, 0.32, 0.56):
        cyl(b, 0.375, 0.03, (0, 0.04, z), "Z", IRON, segs=32)
        for k in range(12):
            a = 2 * math.pi * k / 12
            cyl(b, 0.008, 0.012, (0.378 * math.cos(a), 0.04 + 0.378 * math.sin(a), z + 0.02), "Z", STEEL, segs=6)
    ring(b, 0.36, 0.30, 0.10, (0, 0.04, 0.64), "Z", PAINT, segs=32)                    # water seal rim
    cyl(b, 0.30, 0.01, (0, 0.04, 0.62), "Z", LIQUID, segs=32)                            # seal water
    # porthole (front): a thick brass ring with bolts; behind it the mash (FeSurface) and the bubbles
    # sight chamber bolted on the tank front (open window, dark inside): the mash level shows in it
    box(b, (0.20, 0.02, 0.26), (0.0, -0.31, 0.33), SOOT)                                 # back (on the tank)
    for sx in (-1, 1):
        box(b, (0.02, 0.10, 0.26), (sx * 0.10, -0.36, 0.33), PAINT)
    for z in (0.20, 0.46):
        box(b, (0.22, 0.10, 0.02), (0.0, -0.36, z), PAINT)
    ring(b, 0.11, 0.085, 0.03, (0.0, -0.41, 0.33), "Y", BRASS, segs=20)
    bolt_circle(b, 8, 0.098, (0.0, -0.426, 0.33), "Y", STEEL, r=0.007, d=0.01)
    # gas line: from the holder over to a gauge and the flare at the back right
    pipe_run(b, [(0.22, 0.20, 0.78), (0.30, 0.30, 0.78), (0.30, 0.30, 0.40)], r=0.02)
    gauge(objs, b, (0.30, 0.30 - 0.03, 0.55), "FeNeedle_Gas", r=0.04)
    flare(b, objs, 0.33, 0.36, 0.40, 0.55)
    # hand crank of the drum and a sampling tap
    cyl(b, 0.015, 0.05, (-0.30, -0.22, 0.20), "Y", BRASS, segs=8)
    cyl(b, 0.012, 0.025, (-0.30, -0.26, 0.17), "Z", BRASS, segs=6)
    pipe_run(b, [(0, 0.38, 0.30), (0, 0.44, C)], r=0.03)
    cyl(b, PIPE_R, 0.10, (0, 0.45, C), "Y", STEEL, segs=16)
    flange(b, (0, 0.485, C), "Y", IN)
    box(b, (0.34, 0.22, 0.04), (0, -0.38, 0.60), STEEL)                                  # out chute
    for sx in (-1, 1):
        box(b, (0.03, 0.22, 0.10), (sx * 0.185, -0.38, 0.64), STEEL)
    box(b, (0.36, 0.03, 0.03), (0, -0.49, 0.64), OUT)
    pipe_run(b, [(0, -0.30, 0.20), (0, -0.30, 0.58)], r=0.04)                            # discharge riser
    objs.insert(0, to_object(b, "feBiodigester_Base", bevel=0.003))
    gh = bmesh.new()                                                                     # the floating gas holder
    cyl(gh, 0.27, 0.16, (0, 0, -0.02), "Y", PAINT, segs=28)
    cyl(gh, 0.28, 0.02, (0, 0, -0.07), "Y", IRON, segs=28)
    cyl(gh, 0.05, 0.05, (0, 0, -0.12), "Y", STEEL, segs=10)                             # outlet
    for k in range(4):
        a = k * math.pi / 2
        box(gh, (0.02, 0.06, 0.20), (0.18 * math.cos(a), -0.10, 0.18 * math.sin(a)), IRON,
            Matrix.Rotation(-a, 4, "Y"))                                                 # stirring handles
    objs.append(to_object(gh, "FeSurface_r0.08_Spin_GasHolder", location=(0, 0.04, 0.66), rotation=AX_UP, bevel=0.002))
    ms = bmesh.new()                                                                     # mash in the sight chamber
    cyl(ms, 0.075, 0.012, (0, 0, 0), "Y", LIQUID, segs=20)
    for k in range(3):
        a = 2 * math.pi * k / 3
        cyl(ms, 0.015, 0.014, (0.04 * math.cos(a), -0.003, 0.04 * math.sin(a)), "Y", RUST, segs=8)   # scum
    objs.append(to_object(ms, "FeSurface_r0.20_Spin_Mash", location=(0, -0.36, 0.23), rotation=AX_UP))
    objs.append(empty("FeFx_Bubbles_1", (0, -0.36, 0.30)))
    return objs


def model_biodigester_big():
    """Industrial Biodigester, 1 wide x 2 high: a tall digester; the torque shaft (FeSpin_DriveShaft, across at 0.5)
    drives through bevel boxes and a chain case up to the top gear head that turns the stirrer (FeSpin, vertical,
    its paddles in an open inspection well on top: FeSurface_r0.30_Mash rises there with the fill). A tall level
    gauge (FeSurface_r0.90_Level: a mash column in a glass tube), gas dome with a gauge, the flare (FeFx_Fire_1)."""
    objs = []
    b = bmesh.new()
    box(b, (0.92, 0.92, 0.05), (0, 0, 0.025), IRON)
    cyl(b, 0.40, 1.45, (0, 0.04, 0.80), "Z", PAINT, segs=36)
    for z in (0.12, 0.48, 0.84, 1.20, 1.50):
        cyl(b, 0.415, 0.035, (0, 0.04, z), "Z", IRON, segs=36)
    cyl(b, 0.40, 0.18, (0, 0.04, 1.61), "Z", PAINT, segs=36, r2=0.30)                    # dome
    ring(b, 0.20, 0.16, 0.10, (0, 0.04, 1.73), "Z", CAST, segs=24)                       # inspection well
    cyl(b, 0.16, 0.01, (0, 0.04, 1.69), "Z", SOOT, segs=24)
    for sx in (-1, 1):
        box(b, (0.14, 0.18, 0.20), (sx * 0.40, 0, C), CAST)                              # bevel boxes on the shaft
    box(b, (0.10, 0.16, 1.40), (0.42, 0, 1.24), HAZ)                                      # chain guard up the side
    box(b, (0.36, 0.22, 0.14), (0.24, 0.04, 1.86), CAST)                                  # top gear head
    # level gauge: glass tube with guards from the bottom fitting to the top one
    LX, LY = -0.26, -0.33
    for z in (0.18, 1.32):
        box(b, (0.07, 0.07, 0.06), (LX, LY, z), BRASS)
    for k in range(3):
        a = 2 * math.pi * k / 3
        cyl(b, 0.004, 1.08, (LX + 0.03 * math.cos(a), LY + 0.03 * math.sin(a), 0.75), "Z", STEEL, segs=6)
    cyl(b, 0.006, 1.04, (LX - 0.04, LY - 0.02, 0.75), "Z", HAZ, segs=6)
    gauge(objs, b, (0.22, -0.32, 1.40), "FeNeedle_Gas", r=0.05)
    pipe_run(b, [(-0.18, 0.20, 1.66), (-0.30, 0.30, 1.66), (-0.30, 0.30, 1.20)], r=0.025)
    flare(b, objs, -0.33, 0.36, 1.20, 0.62)
    pipe_run(b, [(0, 0.42, 0.30), (0, 0.44, C)], r=0.03)
    cyl(b, PIPE_R, 0.08, (0, 0.46, C), "Y", STEEL, segs=16)
    flange(b, (0, 0.485, C), "Y", IN)
    box(b, (0.34, 0.22, 0.04), (0, -0.38, 0.60), STEEL)
    for sx in (-1, 1):
        box(b, (0.03, 0.22, 0.10), (sx * 0.185, -0.38, 0.64), STEEL)
    box(b, (0.36, 0.03, 0.03), (0, -0.49, 0.64), OUT)
    for k in range(8):                                                                   # ladder rungs on the side
        box(b, (0.02, 0.24, 0.02), (-0.43, 0.10, 0.30 + k * 0.17), STEEL)
    for sy in (-1, 1):
        box(b, (0.02, 0.02, 1.40), (-0.43, 0.10 + sy * 0.12, 0.98), STEEL)
    objs.insert(0, to_object(b, "feBiodigesterBig_Base", bevel=0.003))
    sh = bmesh.new()
    shaft_end(sh, 0.0, -0.5)
    shaft_end(sh, 0.0, 0.5)
    gear(sh, 0.09, 0.04, 14, (0, 0.40, 0), "Y", BRASS)
    objs.append(to_object(sh, "FeSpin_DriveShaft", location=(0, 0, C), rotation=(0, 0, -math.pi / 2), bevel=0.002))
    st = bmesh.new()                                                                     # stirrer: shaft + paddles
    cyl(st, 0.025, 0.30, (0, 0.15, 0), "Y", STEEL, segs=8)
    for k in range(4):
        a = math.pi * k / 2
        box(st, (0.11, 0.10, 0.02), (0.07 * math.cos(a), 0.24, 0.07 * math.sin(a)), BRASS, Matrix.Rotation(-a, 4, "Y"))
    objs.append(to_object(st, "FeSpin_x0.5_Stirrer", location=(0, 0.04, 1.93), rotation=AX_UP, bevel=0.001))
    ms = bmesh.new()
    cyl(ms, 0.15, 0.01, (0, 0, 0), "Y", LIQUID, segs=20)
    objs.append(to_object(ms, "FeSurface_r0.06_Spin_Mash", location=(0, 0.04, 1.70), rotation=AX_UP))
    col = bmesh.new()                                                                    # level column (hidden below)
    box(col, (0.022, 0.022, 1.0), (0, 0, -0.5), LIQUID)
    objs.append(to_object(col, "FeSurface_r0.95_Level", location=(LX, LY, 0.25)))
    objs.append(empty("FeFx_Bubbles_1", (0, 0.04, 1.72)))
    return objs


def model_steam_dryer():
    """Steam Dryer (1 block): a rotary drum dryer. The drum (FeWorkSpin_x0.4_Drum, tilted down to the front) rides on
    two tyres over trunnion rollers and turns while it dries; a steam jacket coil around it, the wet powder hopper at
    the back, the discharge hood into the chute in front, an exhaust stack with the vapour (FeFx_Steam_1) and
    condensate dripping from the jacket trap (FeFx_Drip_1). Steam in at the back (0.5)."""
    objs = []
    b = bmesh.new()
    box(b, (0.84, 0.84, 0.05), (0, 0, 0.025), IRON)
    for sx in (-1, 1):
        box(b, (0.06, 0.80, 0.08), (sx * 0.30, 0, 0.09), IRON)
    for y in (-0.22, 0.22):                                                              # roller stations
        for sx in (-1, 1):
            box(b, (0.08, 0.10, 0.26), (sx * 0.16, y, 0.23), CAST)
            cyl(b, 0.05, 0.06, (sx * 0.15, y, 0.358), "Y", STEEL, segs=14)              # trunnion rollers
    # hopper at the back with a feed screw tube into the drum, discharge hood at the front
    for k, (w, z) in enumerate(((0.36, 0.98), (0.28, 0.90), (0.20, 0.82))):
        for sx in (-1, 1):
            box(b, (0.02, w, 0.08), (sx * w / 2, 0.30, z), PAINT)
            box(b, (w, 0.02, 0.08), (0, 0.30 + sx * w / 2, z), PAINT)
    cyl(b, 0.05, 0.16, (0, 0.30, 0.72), "Z", STEEL, segs=12)
    box(b, (0.36, 0.14, 0.40), (0, -0.40, 0.56), PAINT)                                 # discharge hood
    box(b, (0.30, 0.02, 0.30), (0, -0.33, 0.62), SOOT)
    box(b, (0.34, 0.12, 0.04), (0, -0.44, 0.60), STEEL)
    box(b, (0.36, 0.03, 0.03), (0, -0.49, 0.64), OUT)
    cyl(b, 0.07, 0.40, (0, -0.40, 0.96), "Z", IRON, segs=14)                            # exhaust stack
    cyl(b, 0.10, 0.04, (0, -0.40, 1.16), "Z", CAST, segs=14, r2=0.07)
    # steam in (back) -> jacket header -> coil around the drum; trap with drip below
    cyl(b, PIPE_R, 0.10, (0.25, 0.45, C), "Y", STEEL, segs=16)
    flange(b, (0.0, 0.485, C), "Y", IN)
    pipe_run(b, [(0, 0.44, C), (0.30, 0.44, C), (0.30, 0.38, 0.86), (0.30, -0.20, 0.86)], r=0.03)
    for k in range(5):
        y = -0.18 + k * 0.09
        ring(b, 0.27, 0.25, 0.02, (0, y, 0.60), "Y", COPPER, segs=24)                   # steam jacket coils
    pipe_run(b, [(0.30, -0.20, 0.34), (0.36, -0.20, 0.30), (0.36, -0.20, 0.18)], r=0.02)
    box(b, (0.07, 0.07, 0.06), (0.36, -0.20, 0.15), BRASS)                              # steam trap
    gauge(objs, b, (-0.30, -0.36, 0.90), "FeNeedle_Steam", r=0.05)
    pipe_run(b, [(-0.30, -0.34, 0.84), (-0.30, -0.10, 0.84), (0, 0.38, C)], r=0.008, mat=BRASS)
    objs.insert(0, to_object(b, "feSteamDryer_Base", bevel=0.003))
    dr = bmesh.new()                                                                     # the drum along Y (local)
    ring(dr, 0.20, 0.185, 0.66, (0, 0, 0), "Y", STEEL, segs=28)
    for y in (-0.22, 0.22):
        ring(dr, 0.235, 0.20, 0.05, (0, y, 0), "Y", CAST, segs=28)                     # riding tyres
    for k in range(6):                                                                   # lifters inside
        a = 2 * math.pi * k / 6
        box(dr, (0.012, 0.62, 0.05), (0.16 * math.cos(a), 0, 0.16 * math.sin(a)), IRON, Matrix.Rotation(-a, 4, "Y"))
    gear(dr, 0.24, 0.03, 30, (0, 0.29, 0), "Y", CAST, tooth=0.02)                      # girth gear
    for sy in (-1, 1):
        ring(dr, 0.20, 0.10, 0.02, (0, sy * 0.33, 0), "Y", CAST, segs=28)               # end rings
    objs.append(to_object(dr, "FeWorkSpin_x0.4_Drum", location=(0, 0, 0.60), rotation=(math.radians(-4), 0, 0), bevel=0.002))
    objs.append(empty("FeFx_Steam_1", (0, -0.40, 1.18)))
    objs.append(empty("FeFx_Drip_1", (0.36, -0.20, 0.11)))
    return objs


def model_chem_mixer():
    """Chemical Mixer (1 block): an open stirred tank. The torque shaft (FeSpin_DriveShaft, across at 0.5) turns a
    chain up the side to a bevel head on the bridge, which turns the stirrer (FeSpin_x0.5_Stirrer, vertical, anchor
    paddles reaching the surface). The slurry surface (FeSurface_r0.22_Slurry) rises with the water buffer and
    swirls while it mixes, with bubbles; a powder hopper with a gate on the side. Water in at the back."""
    objs = []
    b = bmesh.new()
    box(b, (0.84, 0.84, 0.05), (0, 0, 0.025), IRON)
    TZ0, TZ1, TR = 0.30, 0.92, 0.29
    ring(b, TR, TR - 0.02, TZ1 - TZ0, (0, 0.02, (TZ0 + TZ1) / 2), "Z", STEEL, segs=32)   # open-top shell
    cyl(b, TR - 0.02, 0.01, (0, 0.02, TZ0 + 0.005), "Z", SOOT, segs=32)               # dark bottom inside
    ring(b, TR + 0.02, TR - 0.02, 0.04, (0, 0.02, TZ1), "Z", CAST, segs=32)          # rim
    for z in (TZ0 + 0.05, (TZ0 + TZ1) / 2, TZ1 - 0.08):
        cyl(b, TR + 0.012, 0.03, (0, 0.02, z), "Z", IRON, segs=32)
    cyl(b, TR, 0.10, (0, 0.02, TZ0 - 0.04), "Z", STEEL, segs=32, r2=0.10)             # cone bottom
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        box(b, (0.05, 0.05, TZ0), (0.25 * math.cos(a), 0.02 + 0.25 * math.sin(a), TZ0 / 2), IRON)   # legs
    for sx in (-1, 1):
        box(b, (0.12, 0.16, 0.18), (sx * 0.41, 0, C), CAST)                              # bearing boxes
    box(b, (0.08, 0.14, 0.62), (0.42, 0.0, 0.82), HAZ)                                    # chain guard
    for sx in (-1, 1):
        box(b, (0.05, 0.06, 0.22), (sx * 0.33, 0.02, 1.02), IRON)                         # bridge posts
    box(b, (0.74, 0.10, 0.05), (0, 0.02, 1.11), IRON)
    box(b, (0.16, 0.16, 0.12), (0, 0.02, 1.18), CAST)                                     # bevel head
    box(b, (0.14, 0.06, 0.08), (0.24, 0.02, 1.13), CAST)
    # powder hopper with a slide gate (left back), a spout into the tank
    for k, (w, z) in enumerate(((0.22, 1.08), (0.16, 1.00), (0.10, 0.94))):
        for s_ in (-1, 1):
            box(b, (0.02, w, 0.08), (-0.24 + s_ * w / 2, 0.26, z), PAINT)
            box(b, (w, 0.02, 0.08), (-0.24, 0.26 + s_ * w / 2, z), PAINT)
    box(b, (0.06, 0.12, 0.02), (-0.24, 0.20, 0.93), STEEL)
    pipe_run(b, [(0, 0.44, C), (0, 0.36, C), (0.10, 0.28, TZ1 + 0.02), (0.10, 0.20, TZ1 + 0.02)], r=0.025)
    cyl(b, PIPE_R, 0.08, (0, 0.46, C), "Y", STEEL, segs=16)
    flange(b, (0, 0.485, C), "Y", IN)
    box(b, (0.34, 0.22, 0.04), (0, -0.38, 0.60), STEEL)
    for sx in (-1, 1):
        box(b, (0.03, 0.22, 0.10), (sx * 0.185, -0.38, 0.64), STEEL)
    box(b, (0.36, 0.03, 0.03), (0, -0.49, 0.64), OUT)
    pipe_run(b, [(0, 0.02, TZ0 - 0.09), (0, -0.30, 0.25), (0, -0.30, 0.58)], r=0.035)      # bottom valve -> chute
    ring(b, 0.05, 0.04, 0.01, (0.06, -0.20, 0.24), "X", RUST, segs=12)
    objs.insert(0, to_object(b, "feChemMixer_Base", bevel=0.003))
    sh = bmesh.new()
    shaft_end(sh, 0.0, -0.5)
    shaft_end(sh, 0.0, 0.5)
    gear(sh, 0.08, 0.04, 12, (0, 0.42, 0), "Y", BRASS)
    objs.append(to_object(sh, "FeSpin_DriveShaft", location=(0, 0, C), rotation=(0, 0, -math.pi / 2), bevel=0.002))
    st = bmesh.new()                                                                     # anchor stirrer
    cyl(st, 0.018, 0.72, (0, 0.36, 0), "Y", STEEL, segs=8)
    for s_ in (-1, 1):
        box(st, (0.02, 0.50, 0.03), (s_ * 0.24, 0.42, 0), BRASS)                        # anchor arms (vertical)
        box(st, (0.24, 0.03, 0.03), (s_ * 0.12, 0.66, 0), BRASS)                        # bottom bar
        box(st, (0.10, 0.08, 0.012), (s_ * 0.12, 0.40, 0), BRASS, Matrix.Rotation(0.5, 4, "Y"))   # pitched blade
    objs.append(to_object(st, "FeSpin_x0.5_Stirrer", location=(0, 0.02, 1.13), rotation=AX_UP, bevel=0.001))
    sf = bmesh.new()
    cyl(sf, TR - 0.025, 0.01, (0, 0, 0), "Y", LIQUID, segs=28)
    for k in range(3):                                                                   # a swirl of foam
        a = 2 * math.pi * k / 3
        box(sf, (0.20, 0.004, 0.02), (0.12 * math.cos(a), -0.006, 0.12 * math.sin(a)), GAS, Matrix.Rotation(-a + 0.6, 4, "Y"))
    objs.append(to_object(sf, "FeSurface_r0.22_Spin_Slurry", location=(0, 0.02, TZ1 - 0.30), rotation=AX_UP))
    objs.append(empty("FeFx_Bubbles_1", (0, 0.02, TZ1 - 0.10)))
    return objs


def model_washer():
    """Washer (1 block): a trommel. A perforated drum (FeWorkSpin_x0.5_Trommel) along the travel, tilted down to the
    front, turns on rollers under a spray bar (FeFx_Spray_1, while it washes) over a trough of muddy water
    (FeSurface_r0.10_Water) dripping (FeFx_Drip_1); feed hopper at the back, the chute in front. Water in at the back."""
    objs = []
    b = bmesh.new()
    box(b, (0.84, 0.84, 0.05), (0, 0, 0.025), IRON)
    # trough (open box) under the drum
    for sx in (-1, 1):
        box(b, (0.03, 0.80, 0.30), (sx * 0.36, 0, 0.24), PAINT)
    box(b, (0.74, 0.03, 0.30), (0, 0.385, 0.24), PAINT)
    box(b, (0.74, 0.03, 0.22), (0, -0.385, 0.20), PAINT)
    box(b, (0.70, 0.76, 0.02), (0, 0, 0.10), CAST)
    hazard(b, 0.74, (0, -0.405, 0.30), "X", h=0.04, n=10)
    for y in (-0.22, 0.22):                                                              # roller frames
        for sx in (-1, 1):
            box(b, (0.05, 0.08, 0.36), (sx * 0.30, y, 0.53), IRON)
            cyl(b, 0.04, 0.05, (sx * 0.19, y, 0.47), "Y", STEEL, segs=12)
            beam(b, (sx * 0.30, y, 0.46), (sx * 0.19, y, 0.47), 0.03, 0.03, IRON)
    # spray bar on posts above the drum, fed from the inlet
    for sy in (-1, 1):
        box(b, (0.04, 0.04, 0.44), (0.30, sy * 0.30, 0.74), IRON)
    pipe_run(b, [(0, 0.44, C), (0.30, 0.44, C), (0.30, 0.38, 0.92), (0.0, 0.38, 0.92), (0.0, -0.30, 0.92)], r=0.025)
    for k in range(6):
        cyl(b, 0.012, 0.03, (0, 0.26 - k * 0.10, 0.895), "Z", BRASS, segs=6)             # nozzles
    cyl(b, PIPE_R, 0.08, (0, 0.46, C), "Y", STEEL, segs=16)
    flange(b, (0, 0.485, C), "Y", IN)
    # feed hopper at the back, discharge lip to the chute in front
    for k, (w, z) in enumerate(((0.30, 0.95), (0.22, 0.87))):
        for s_ in (-1, 1):
            box(b, (0.02, w, 0.08), (s_ * w / 2 - 0.12, 0.34, z), PAINT)
            box(b, (w, 0.02, 0.08), (-0.12, 0.34 + s_ * w / 2, z), PAINT)
    box(b, (0.34, 0.20, 0.04), (0, -0.39, 0.60), STEEL)
    for sx in (-1, 1):
        box(b, (0.03, 0.20, 0.10), (sx * 0.185, -0.39, 0.64), STEEL)
    box(b, (0.36, 0.03, 0.03), (0, -0.49, 0.64), OUT)
    objs.insert(0, to_object(b, "feWasher_Base", bevel=0.003))
    tr = bmesh.new()                                                                     # trommel cage along Y
    for y in (-0.30, 0.0, 0.30):
        ring(tr, 0.17, 0.15, 0.03, (0, y, 0), "Y", CAST, segs=24)
    for k in range(16):                                                                  # perforated slats
        a = 2 * math.pi * k / 16
        box(tr, (0.035, 0.62, 0.008), (0.16 * math.cos(a), 0, 0.16 * math.sin(a)), STEEL, Matrix.Rotation(-a + math.pi / 2, 4, "Y"))
    for k in range(4):                                                                   # lifters
        a = 2 * math.pi * k / 4 + 0.3
        box(tr, (0.01, 0.58, 0.04), (0.13 * math.cos(a), 0, 0.13 * math.sin(a)), IRON, Matrix.Rotation(-a, 4, "Y"))
    for y in (-0.22, 0.22):
        ring(tr, 0.20, 0.17, 0.04, (0, y, 0), "Y", RUST, segs=24)                      # riding rings
    objs.append(to_object(tr, "FeWorkSpin_x0.5_Trommel", location=(0, 0, 0.62), rotation=(math.radians(-5), 0, 0), bevel=0.0015))
    wt = bmesh.new()
    box(wt, (0.68, 0.74, 0.01), (0, 0, 0), LIQUID)
    objs.append(to_object(wt, "FeSurface_r0.10_Water", location=(0, 0, 0.16)))
    objs.append(empty("FeFx_Spray_1", (0, -0.02, 0.88)))
    objs.append(empty("FeFx_Drip_1", (0, 0.05, 0.44)))
    return objs


def mini_belt(bm, objs, name, p0, p1, w=0.07, rollers=True):
    """A small belt on the bench between p0 and p1 (horizontal), with side rails, legs and spinning end rollers."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    ang = math.atan2(d.y, d.x)
    m = Matrix.Translation((p0 + p1) / 2) @ Matrix.Rotation(ang, 4, "Z")
    for size, off, mat in (((L, w, 0.012), (0, 0, -0.012), SOOT), ((L, 0.01, 0.025), (0, w / 2 + 0.005, 0), PAINT),
                           ((L, 0.01, 0.025), (0, -w / 2 - 0.005, 0), PAINT), ((L - 0.04, w, 0.01), (0, 0, -0.03), IRON)):
        r = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)
        _fin(bm, mat, m @ Matrix.Translation(off) @ Matrix.Diagonal((*size, 1)), r["verts"])
    if rollers:
        for k, p in enumerate((p0, p1)):
            ro = bmesh.new()
            cyl(ro, 0.012, w, (0, 0, 0), "Y", STEEL, segs=10)
            box(ro, (0.004, w, 0.02), (0, 0, 0), CAST)
            objs.append(to_object(ro, "FeSpin_x6_%sRoller%d" % (name, k), location=p - Vector((0, 0, 0.014)),
                                  rotation=(0, 0, ang)))


def model_m_ammo():
    """Ammo Press (2 wide, 2 high): a progressive reloading press on a steel bench. Case bowl feeder and bullet
    feeder on top (they turn while it works), primer tube, powder measure, the turret / shell plate
    (FeSpin_x0.5_Turret) and the ram (FePiston_Ram). Two small belts on the bench (MachineVisual tracks): empty
    cases ride from the case bin up into the shell plate (track 1), finished rounds ride from the press out to the
    ammo box (track 2)."""
    objs = []
    b = bmesh.new()
    for x in (-0.88, 0.88):
        for y in (-0.38, 0.38):
            box(b, (0.07, 0.07, 0.86), (x, y, 0.43), IRON)
    plate(b, (1.92, 0.86, 0.05), (0, 0, 0.885), CAST, "-Y", n=12)
    for x in (-0.55, 0.0, 0.55):
        plate(b, (0.48, 0.03, 0.16), (x, -0.42, 0.74), PAINT, "-Y", n=3)
        box(b, (0.12, 0.02, 0.02), (x, -0.44, 0.76), STEEL)
    box(b, (1.80, 0.80, 0.03), (0, 0, 0.16), IRON)
    for k in range(3):
        box(b, (0.40, 0.30, 0.22), (-0.55 + k * 0.55, 0.10, 0.285), WOOD)
        box(b, (0.30, 0.01, 0.06), (-0.55 + k * 0.55, -0.055, 0.30), HAZ)
    plate(b, (1.92, 0.04, 0.95), (0, 0.43, 1.40), WOOD, "-Y", n=10)
    for k in range(6):
        box(b, (0.03, 0.02, 0.18), (0.40 + k * 0.08, 0.40, 1.55), STEEL)
    TOP = 0.91
    # press: cast base, column, upper frame, toolhead with 5 dies, handle
    PX, PY = -0.30, -0.02
    box(b, (0.26, 0.22, 0.08), (PX, PY + 0.05, TOP + 0.04), CAST)
    box(b, (0.11, 0.12, 0.80), (PX, PY + 0.14, TOP + 0.45), PAINT)
    box(b, (0.24, 0.32, 0.10), (PX, PY + 0.02, 1.80), PAINT)
    cyl(b, 0.11, 0.05, (PX, PY, 1.72), "Z", CAST, segs=18)
    for k in range(5):
        a_ = k * 2 * math.pi / 5
        cyl(b, 0.017, 0.12, (PX + 0.075 * math.cos(a_), PY + 0.075 * math.sin(a_), 1.66), "Z", STEEL, segs=8)
        cyl(b, 0.022, 0.02, (PX + 0.075 * math.cos(a_), PY + 0.075 * math.sin(a_), 1.735), "Z", CAST, segs=8)
    beam(b, (PX + 0.10, PY + 0.06, 1.60), (PX + 0.42, PY - 0.25, 1.86), 0.025, 0.025, STEEL)
    cyl(b, 0.03, 0.10, (PX + 0.44, PY - 0.27, 1.87), "X", WOOD, segs=10)
    cyl(b, 0.09, 0.02, (PX, PY, 1.26), "Z", CAST, segs=18)                               # shell plate base
    # powder measure with a sight hopper; primer tube; case feed tube from the bowl above
    cyl(b, 0.06, 0.18, (PX + 0.20, PY - 0.02, 1.62), "Z", BRASS, segs=14, r2=0.035)
    cyl(b, 0.045, 0.05, (PX + 0.20, PY - 0.02, 1.74), "Z", STEEL, segs=12)
    box(b, (0.06, 0.04, 0.03), (PX + 0.14, PY - 0.02, 1.52), CAST)
    cyl(b, 0.012, 0.40, (PX + 0.12, PY + 0.10, 1.50), "Z", GLASS, segs=8)                 # primer tube
    cyl(b, 0.022, 0.30, (PX - 0.10, PY + 0.10, 1.75), "Z", GLASS, segs=10)                # case drop tube
    # feeders on posts: case bowl (left) and bullet bowl (right)
    for (fx, fy, fz, fr) in ((PX - 0.12, PY + 0.18, 1.92, 0.12), (PX + 0.24, PY + 0.20, 1.86, 0.09)):
        beam(b, (fx, fy + 0.10, TOP), (fx, fy + 0.10, fz - 0.06), 0.03, 0.03, IRON)
        cyl(b, fr + 0.02, 0.03, (fx, fy, fz - 0.05), "Z", CAST, segs=16)
    pipe_run(b, [(PX + 0.24, PY + 0.20, 1.82), (PX + 0.10, PY + 0.05, 1.70)], r=0.012, mat=GLASS, elbows=False)
    # belt 1 (cases in): case bin at the left -> along the bench -> up a ramp into the shell plate
    box(b, (0.22, 0.20, 0.10), (-0.80, -0.10, TOP + 0.05), STEEL)
    box(b, (0.19, 0.17, 0.012), (-0.80, -0.10, TOP + 0.095), BRASS)
    T1 = [(-0.70, -0.12, TOP + 0.04), (-0.45, -0.12, TOP + 0.04)]
    mini_belt(b, objs, "In", T1[0], T1[1])
    ramp = [(-0.45, -0.12, TOP + 0.04), (PX - 0.10, PY - 0.05, 1.25)]
    pipe_run(b, ramp, r=0.018, mat=STEEL, elbows=False)                                  # guide rail up
    # belt 2 (rounds out): from the shell plate down a chute -> along the bench -> into the ammo box
    chute2 = [(PX + 0.09, PY - 0.06, 1.25), (PX + 0.16, PY - 0.12, TOP + 0.05)]
    pipe_run(b, chute2, r=0.018, mat=STEEL, elbows=False)
    T2 = [(PX + 0.18, -0.13, TOP + 0.04), (0.20, -0.13, TOP + 0.04)]
    mini_belt(b, objs, "Out", T2[0], T2[1])
    box(b, (0.22, 0.16, 0.10), (0.33, -0.13, TOP + 0.05), WOOD)                         # ammo box
    box(b, (0.20, 0.14, 0.012), (0.33, -0.13, TOP + 0.095), BRASS)
    box(b, (0.22, 0.02, 0.12), (0.33, -0.05, TOP + 0.16), WOOD, Matrix.Rotation(-0.6, 4, "X"))   # open lid
    # bins of tips and powder, bench vise, lamp
    for k, (x, mat) in enumerate(((0.62, COPPER), (0.80, BRASS))):
        box(b, (0.16, 0.20, 0.10), (x, -0.10, TOP + 0.05), STEEL)
        box(b, (0.14, 0.18, 0.012), (x, -0.10, TOP + 0.095), mat)
    box(b, (0.14, 0.18, 0.10), (-0.80, 0.22, TOP + 0.05), CAST)
    box(b, (0.16, 0.04, 0.08), (-0.80, 0.12, TOP + 0.12), STEEL)
    beam(b, (0.85, 0.30, TOP), (0.70, 0.10, 1.65), 0.025, 0.025, IRON)
    cyl(b, 0.08, 0.10, (0.66, 0.05, 1.64), "Z", HAZ, segs=14, r2=0.04)
    objs.insert(0, to_object(b, "feM_Ammo_Base", bevel=0.003))
    t = bmesh.new()                                                                      # shell plate with cases
    cyl(t, 0.09, 0.025, (0, 0, 0), "Y", STEEL, segs=18)
    for k in range(5):
        a_ = k * 2 * math.pi / 5
        cyl(t, 0.013, 0.05, (math.cos(a_) * 0.065, -0.035, math.sin(a_) * 0.065), "Y", BRASS, segs=8)
    objs.append(to_object(t, "FeSpin_x0.5_Turret", location=(PX, PY, 1.285), rotation=AX_UP))
    ram = bmesh.new()
    cyl(ram, 0.028, 0.22, (0, -0.11, 0), "Y", STEEL, segs=12)
    cyl(ram, 0.045, 0.04, (0, -0.02, 0), "Y", CAST, segs=12)
    objs.append(to_object(ram, "FePiston_Ram", location=(PX, PY, 1.42), rotation=AX_UP))
    for name, (fx, fy, fz, fr) in (("CaseBowl", (PX - 0.12, PY + 0.18, 1.92, 0.12)), ("BulletBowl", (PX + 0.24, PY + 0.20, 1.86, 0.09))):
        bw = bmesh.new()                                                                 # bowl feeders (turn)
        cyl(bw, fr, 0.06, (0, 0, 0), "Y", STEEL, segs=18, r2=fr * 0.7)
        ring(bw, fr + 0.005, fr - 0.01, 0.02, (0, -0.03, 0), "Y", CAST, segs=18)
        for k in range(6):
            a_ = k * math.pi / 3
            cyl(bw, 0.008, 0.03, (math.cos(a_) * fr * 0.6, -0.04, math.sin(a_) * fr * 0.6), "Y",
                BRASS if name == "CaseBowl" else COPPER, segs=6)
        objs.append(to_object(bw, "FeSpin_x0.3_" + name, location=(fx, fy, fz), rotation=AX_UP))
    # track 1: empty cases (path = belt then the guide up to the shell plate)
    path1 = [T1[0], T1[1], ramp[1]]
    for i, p in enumerate(path1):
        objs.append(empty("FeTrack_1_P%d" % i, p, 0.02))
    for k in range(7):
        it = bmesh.new()
        cyl(it, 0.010, 0.032, (0, 0, 0.016), "Z", BRASS, segs=8)
        objs.append(to_object(it, "FeTrackItem_1_%d" % k, location=path1[0]))
    # track 2: finished rounds (chute then the belt into the box)
    path2 = [chute2[0], chute2[1], T2[0], T2[1], (0.33, -0.13, TOP + 0.10)]
    for i, p in enumerate(path2):
        objs.append(empty("FeTrack_2_P%d" % i, p, 0.02))
    for k in range(8):
        it = bmesh.new()
        cyl(it, 0.010, 0.030, (0, 0, 0.015), "Z", BRASS, segs=8)
        cyl(it, 0.008, 0.016, (0, 0, 0.038), "Z", COPPER, segs=8, r2=0.003)
        objs.append(to_object(it, "FeTrackItem_2_%d" % k, location=path2[0]))
    return objs



# ================================================================ round 6: coal / gas engines, belt crate
def crank_linkage(objs, n, pin, ch, rod_w=0.025):
    """Crosshead (piston) + connecting rod + crank pin marker for KineticSpinner's slider-crank solver."""
    pin, ch = Vector(pin), Vector(ch)
    d = pin - ch
    rd = bmesh.new()
    beam(rd, (0, 0, 0), d, rod_w, rod_w * 0.8, STEEL)
    cyl(rd, rod_w * 1.1, 0.035, (0, 0, 0), "Y", CAST, segs=10)
    cyl(rd, rod_w * 1.5, 0.04, d, "Y", CAST, segs=12)
    objs.append(to_object(rd, "FeConrod_%d" % n, location=ch, bevel=0.001))
    objs.append(empty("FeCrankPin_%d" % n, tuple(pin), 0.03))


def model_coal_engine():
    """Coal Engine (1 block, torque source, shaft = Blender Y at 0.5 through both faces): a firebox with a chimney
    on the left, a vertical single cylinder over a crank on the shaft, the flywheel at the front. The crankshaft
    (FeSpin_EngineCrank) drives the crosshead / rod through KineticSpinner's slider-crank. Fire, coal glow and
    chimney smoke while it runs (FxVisual)."""
    objs = []
    b = bmesh.new()
    box(b, (0.92, 0.92, 0.05), (0, 0, 0.025), IRON)
    hazard(b, 0.90, (0, -0.465, 0.05), "X", h=0.04, n=12)
    # firebox (left), riveted, with an open door and coal bed; chimney up to the top
    FX = -0.27
    plate(b, (0.34, 0.50, 0.42), (FX, 0.15, 0.26), CAST, "-X", n=4)
    box(b, (0.36, 0.52, 0.03), (FX, 0.15, 0.48), IRON)
    box(b, (0.20, 0.02, 0.16), (FX, -0.105, 0.24), SOOT)                                # mouth
    box(b, (0.16, 0.03, 0.03), (FX, -0.11, 0.18), GLOW)                                 # coal bed
    plate(b, (0.02, 0.16, 0.18), (FX - 0.20, -0.17, 0.25), CAST, "-X", n=2)             # open door
    cyl(b, 0.07, 0.46, (FX, 0.30, 0.73), "Z", IRON, segs=14)
    cyl(b, 0.09, 0.04, (FX, 0.30, 0.97), "Z", CAST, segs=14)
    # main bearings on A-frames, cylinder on a column over the crank
    for y in (-0.08, 0.40):
        box(b, (0.16, 0.10, 0.40), (0, y, 0.25), CAST)
        cyl(b, 0.07, 0.11, (0, y, C), "Y", CAST, segs=16)
        cyl(b, 0.01, 0.03, (0, y, C + 0.08), "Z", BRASS, segs=6)
    for sx in (-1, 1):
        box(b, (0.03, 0.04, 0.24), (sx * 0.06, 0.16, 0.74), STEEL)                       # crosshead guides
    box(b, (0.20, 0.10, 0.04), (0, 0.16, 0.86), CAST)
    cyl(b, 0.075, 0.12, (0, 0.16, 0.92), "Z", PAINT, segs=18)                             # cylinder
    cyl(b, 0.085, 0.02, (0, 0.16, 0.985), "Z", CAST, segs=18)
    pipe_run(b, [(0.07, 0.16, 0.94), (0.16, 0.16, 0.94), (0.16, 0.20, 0.52), (FX + 0.17, 0.25, 0.40)], r=0.018)
    cyl(b, 0.04, 0.02, (0.16, 0.06, 0.80), "Y", BRASS, segs=12)                            # gauge
    objs.append(to_object(b, "feCoalEngine_Base", bevel=0.003))
    ER, EL, TY = 0.05, 0.20, 0.16                                                         # crank radius, rod, throw y
    w = bmesh.new()
    shaft_end(w, 0.0, -0.5)
    shaft_end(w, 0.0, 0.5)
    ring(w, 0.30, 0.25, 0.06, (0, -0.30, 0), "Y", CAST, segs=36)                         # flywheel
    cyl(w, 0.06, 0.09, (0, -0.30, 0), "Y", CAST, segs=14)
    for k in range(5):
        a_ = k * 2 * math.pi / 5
        m = Matrix.Rotation(a_, 4, "Y") @ Matrix.Translation((0.15, -0.30, 0))
        r = bmesh.ops.create_cube(w, size=1.0, calc_uvs=True)
        _fin(w, CAST, m @ Matrix.Diagonal((0.20, 0.03, 0.035, 1)), r["verts"])
    for dy in (-0.035, 0.035):                                                            # crank webs
        box(w, (0.05, 0.02, ER + 0.07), (0, TY + dy, ER / 2 - 0.015), RUST)
    cyl(w, 0.015, 0.09, (0, TY, ER), "Y", STEEL, segs=10)                               # crank pin (up)
    objs.append(to_object(w, "FeSpin_EngineCrank", location=(0, 0, C), bevel=0.0015))
    pin = (0, TY, C + ER)
    ch = (0, TY, C + ER + EL)
    x = bmesh.new()
    box(x, (0.09, 0.05, 0.04), (0, 0, 0), BRASS)
    cyl(x, 0.012, 0.22, (0, 0, 0.11), "Z", STEEL, segs=8)                               # piston rod
    cyl(x, 0.065, 0.04, (0, 0, 0.21), "Z", IRON, segs=14)                                # piston (inside)
    objs.append(to_object(x, "FeCrosshead_1", location=ch, bevel=0.001))
    crank_linkage(objs, 1, pin, ch)
    objs.append(empty("FeFx_Fire_1", (FX, -0.13, 0.19)))
    objs.append(empty("FeFx_Smoke_1", (FX, 0.30, 0.99)))
    return objs


def model_gas_engine():
    """Gas Engine (1 block, torque source, shaft = Blender Y at 0.5): a single-cylinder horizontal engine in the
    hit-and-miss style. Two big flywheels on the crankshaft (FeSpin_EngineCrank), the cylinder lying across (+X)
    with its cooling-water hopper and the piston / rod driven by the slider-crank; fuel tank, ignition box, exhaust
    (FeFx_Smoke_1 puffs while it runs)."""
    objs = []
    b = bmesh.new()
    box(b, (0.92, 0.92, 0.05), (0, 0, 0.025), IRON)
    for sx in (-1, 1):
        box(b, (0.08, 0.80, 0.10), (sx * 0.40, 0, 0.10), WOOD)                            # skids
    hazard(b, 0.90, (0, -0.465, 0.05), "X", h=0.04, n=12)
    # crankcase / frame with the main bearings
    box(b, (0.24, 0.40, 0.30), (0.0, 0, 0.27), CAST)
    for y in (-0.19, 0.19):
        cyl(b, 0.065, 0.07, (0, y, C), "Y", CAST, segs=16)
        box(b, (0.16, 0.07, 0.12), (0, y, 0.44), CAST)
    # the cylinder across (+X): water jacket box with an open hopper on top, head, spark plug, exhaust
    CX0, CX1 = 0.14, 0.44
    plate(b, (CX1 - CX0, 0.20, 0.20), ((CX0 + CX1) / 2, 0, C), PAINT, "-Y", n=3)
    for k in range(4):
        box(b, (0.012, 0.22, 0.22), (CX0 + 0.05 + k * 0.07, 0, C), CAST)                  # fins / bands
    box(b, (0.26, 0.16, 0.10), ((CX0 + CX1) / 2, 0, C + 0.15), PAINT)                    # water hopper
    box(b, (0.22, 0.12, 0.01), ((CX0 + CX1) / 2, 0, C + 0.195), LIQUID)
    box(b, (0.04, 0.16, 0.16), (CX1 + 0.02, 0, C), CAST)                                 # head
    cyl(b, 0.012, 0.05, (CX1 + 0.04, 0.04, C + 0.09), "Z", BRASS, segs=6)                # spark plug
    pipe_run(b, [(CX1 - 0.04, -0.10, C + 0.04), (CX1 - 0.04, -0.20, C + 0.04), (CX1 - 0.04, -0.20, 0.92)], r=0.025)
    cyl(b, 0.035, 0.06, (CX1 - 0.04, -0.20, 0.95), "Z", CAST, segs=10)                   # exhaust cap
    # fuel tank on a stand (left), line to the carb, ignition box
    cyl(b, 0.10, 0.22, (-0.30, 0.20, 0.72), "X", HAZ, segs=16)
    for sx in (-1, 1):
        box(b, (0.03, 0.03, 0.62), (-0.30 + sx * 0.08, 0.20, 0.31), IRON)
    pipe_run(b, [(-0.30, 0.20, 0.62), (0.05, 0.20, 0.62), (CX0 + 0.04, 0.08, C + 0.06)], r=0.008, mat=COPPER)
    box(b, (0.10, 0.08, 0.10), (0.20, 0.25, 0.30), CAST)                                  # ignition / magneto
    objs.append(to_object(b, "feGasEngine_Base", bevel=0.003))
    ER, EL = 0.06, 0.24
    w = bmesh.new()
    shaft_end(w, 0.0, -0.5)
    shaft_end(w, 0.0, 0.5)
    for y in (-0.31, 0.31):                                                               # twin flywheels
        ring(w, 0.32, 0.27, 0.055, (0, y, 0), "Y", CAST, segs=40)
        cyl(w, 0.06, 0.08, (0, y, 0), "Y", CAST, segs=14)
        for k in range(6):
            a_ = k * math.pi / 3
            m = Matrix.Rotation(a_, 4, "Y") @ Matrix.Translation((0.165, y, 0))
            r = bmesh.ops.create_cube(w, size=1.0, calc_uvs=True)
            _fin(w, CAST, m @ Matrix.Diagonal((0.22, 0.03, 0.035, 1)), r["verts"])
    for dy in (-0.04, 0.04):
        box(w, (ER + 0.08, 0.02, 0.06), (ER / 2 - 0.01, dy, 0), RUST)                    # crank webs
    cyl(w, 0.016, 0.10, (ER, 0, 0), "Y", STEEL, segs=10)                               # crank pin (+X)
    objs.append(to_object(w, "FeSpin_EngineCrank", location=(0, 0, C), bevel=0.0015))
    pin = (ER, 0, C)
    ch = (ER + EL, 0, C)
    x = bmesh.new()                                                                      # piston (in the cylinder)
    cyl(x, 0.07, 0.10, (0.06, 0, 0), "X", IRON, segs=16)
    cyl(x, 0.014, 0.03, (0, 0, 0), "Y", STEEL, segs=8)
    objs.append(to_object(x, "FeCrosshead_1", location=ch, bevel=0.001))
    crank_linkage(objs, 1, pin, ch, rod_w=0.022)
    objs.append(empty("FeFx_Smoke_1", (CX1 - 0.04, -0.20, 0.98)))
    return objs


def model_belt_crate():
    """Belt Storage crate (1 block): a riveted iron crate with corner posts, bands, a hinged lid, a stencil plate
    and a conveyor inlet frame on each side (it takes items from a belt pointing into any of its sides)."""
    b = bmesh.new()
    plate(b, (0.84, 0.84, 0.70), (0, 0, 0.42), PAINT, "-Y", n=6)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(b, (0.07, 0.07, 0.80), (sx * 0.42, sy * 0.42, 0.40), IRON)
            box(b, (0.10, 0.10, 0.03), (sx * 0.42, sy * 0.42, 0.015), IRON)
    for z in (0.12, 0.76):
        for s in (-1, 1):
            box(b, (0.86, 0.03, 0.04), (0, s * 0.43, z), IRON)
            box(b, (0.03, 0.86, 0.04), (s * 0.43, 0, z), IRON)
    plate(b, (0.86, 0.86, 0.05), (0, 0.0, 0.80), CAST, "-Y", n=6)                       # lid
    for x in (-0.25, 0.25):
        box(b, (0.10, 0.04, 0.04), (x, 0.44, 0.80), STEEL)                               # hinges
    box(b, (0.16, 0.03, 0.05), (0, -0.445, 0.78), STEEL)                                 # latch
    box(b, (0.30, 0.012, 0.12), (0, -0.44, 0.60), HAZ)                                   # stencil plate
    for p, n in (((0, -0.5, 0.25), (0, -1, 0)), ((0, 0.5, 0.25), (0, 1, 0)),
                 ((-0.5, 0, 0.25), (-1, 0, 0)), ((0.5, 0, 0.25), (1, 0, 0))):
        conveyor_port(b, p, n)
    return [to_object(b, "feBeltCrate_Base", bevel=0.003)]



# ================================================================ D12 blocks (PLANO_CADEIA.md section 7), all 1 x 1
# Contracts (src/ForgedInAshes): valves / compressor: fluid IN at the back (Blender +Y), OUT at the front (-Y), at
# 0.5; gauge / burner: port at the back; tapper: latex OUT at the front (its back hugs the tree); tanks: any face;
# tower section: 4 sides; processors: fluid in at the back (0.5), products onto the LOW belt in front (lona 0.175);
# torque machines: drive shaft across (Blender X) at 0.5; powered blocks: a WireOffset; in-line stations sit on the
# block ABOVE a belt: their FeReach_* parts hang down to it (kept out of the collider by FeBuild).
LOW = 0.24                                                     # chute lip over the low belt in front


def d12_base(b, w=0.90, h=0.05, mat=IRON, stripe=True):
    box(b, (w, w, h), (0, 0, h / 2), mat)
    if stripe:
        hazard(b, w - 0.02, (0, -w / 2 - 0.004, h / 2), "X", h=h * 0.8, n=12)


def back_in(b, z=C, ring_mat=None):
    cyl(b, PIPE_R, 0.20, (0, 0.40, z), "Y", STEEL, segs=16)
    flange(b, (0, 0.485, z), "Y", ring_mat if ring_mat is not None else IN)


def front_out(b, z=C):
    cyl(b, PIPE_R, 0.20, (0, -0.40, z), "Y", STEEL, segs=16)
    flange(b, (0, -0.485, z), "Y", OUT)


def low_chute(b):
    box(b, (0.32, 0.20, 0.025), (0, -0.40, LOW), STEEL)
    for sx in (-1, 1):
        box(b, (0.02, 0.20, 0.08), (sx * 0.17, -0.40, LOW + 0.04), STEEL)
    box(b, (0.34, 0.03, 0.03), (0, -0.495, LOW + 0.05), OUT)


def drive_x(objs, gear_r=0.0):
    """Torque shaft across the block (Blender X) at 0.5, spinning (KineticSpinner)."""
    sh = bmesh.new()
    shaft_end(sh, 0.0, -0.5)
    shaft_end(sh, 0.0, 0.5)
    if gear_r:
        gear(sh, gear_r, 0.04, 16, (0, 0.40, 0), "Y", BRASS)
    objs.append(to_object(sh, "FeSpin_DriveShaft", location=(0, 0, C), rotation=(0, 0, -math.pi / 2), bevel=0.002))


def side_bearings(b, w=0.18, z=C):
    for sx in (-1, 1):
        box(b, (0.12, w, z - 0.05), (sx * 0.40, 0, (z - 0.05) / 2 + 0.05), CAST)
        cyl(b, 0.07, 0.13, (sx * 0.40, 0, z), "X", CAST, segs=16)


def axial_pipe(b):
    """Pipe through the block along Y at 0.5 with flanges at both faces (in = back, green; out = front, orange)."""
    cyl(b, PIPE_R, 0.96, (0, 0, C), "Y", STEEL, segs=16)
    flange(b, (0, 0.485, C), "Y", IN)
    flange(b, (0, -0.485, C), "Y", OUT)


def arrow_on_top(b, z, y0=0.10, mat=OUT):
    for k, w in enumerate((0.10, 0.07, 0.04)):
        box(b, (w, 0.025, 0.008), (0, y0 - 0.035 * k - 0.06, z), mat)


# ---------------------------------------------------------------- pipes, valves, gauge, compressor
def model_pipe_hp():
    """High-pressure pipe: thick steel, a forged cross with heavy bolting and red pressure bands; arms like fePipe."""
    core = bmesh.new()
    box(core, (0.28, 0.28, 0.28), (0, 0, 0), STEEL)
    for v in ARM_DIRS.values():
        cyl(core, PIPE_R + 0.02, 0.03, Vector(v) * 0.14, _axname(v), CAST, segs=18)
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                cyl(core, 0.013, 0.014, (sx * 0.11, sy * 0.11, sz * 0.145), "Z", STEEL, segs=6)
    box(core, (0.12, 0.012, 0.06), (0, -0.142, 0.06), OUT)                               # "12 bar" plate
    root = bpy.data.objects.new("fePipeHP_Base", None)
    out = [root, to_object(core, "fePipe_Core", location=(0, 0, C), bevel=0.004)]
    for n, v in ARM_DIRS.items():
        bm = bmesh.new()
        vv = Vector(v)
        ax = _axname(v)
        cyl(bm, PIPE_R + 0.008, 0.36, vv * 0.31, ax, STEEL, segs=18)
        for t in (0.22, 0.38):
            cyl(bm, PIPE_R + 0.016, 0.025, vv * t, ax, RED, segs=18)
        flange(bm, vv * 0.485, ax, bolts=8)
        out.append(to_object(bm, n, location=(0, 0, C), bevel=0.002))
    return out


def valve_common(b):
    box(b, (0.30, 0.76, 0.04), (0, 0, 0.02), IRON)                                     # skid under both saddles
    for sy in (-0.30, 0.30):
        box(b, (0.10, 0.06, C - 0.10), (0, sy, (C - 0.10) / 2 + 0.04), IRON)          # pipe saddles
    axial_pipe(b)


def model_valve_shutoff():
    """Shut-off valve (gate valve): body, bonnet, rising stem and a handwheel; a signal can open / close it."""
    objs = []
    b = bmesh.new()
    valve_common(b)
    box(b, (0.22, 0.20, 0.22), (0, 0, C), CAST)
    bolt_circle(b, 8, 0.10, (0, 0, C + 0.115), "Z", STEEL, r=0.009, d=0.02)
    cyl(b, 0.07, 0.16, (0, 0, C + 0.19), "Z", CAST, segs=16)                             # bonnet
    cyl(b, 0.015, 0.16, (0, 0, C + 0.33), "Z", STEEL, segs=8)                            # stem
    ring(b, 0.12, 0.10, 0.025, (0, 0, C + 0.40), "Z", RED, segs=20)                 # handwheel
    for k in range(4):
        box(b, (0.22, 0.015, 0.015), (0, 0, C + 0.40), RED, Matrix.Rotation(k * math.pi / 4, 4, "Z"))
    box(b, (0.08, 0.06, 0.06), (0.14, 0, C + 0.10), CAST)                                # signal actuator box
    objs.append(to_object(b, "feValveShutoff_Base", bevel=0.003))
    wire(objs, (0.14, 0, C + 0.16))
    return objs


def model_valve_check():
    b = bmesh.new()
    valve_common(b)
    cyl(b, 0.13, 0.26, (0, 0, C), "Y", CAST, segs=20)                                    # swing-check body
    box(b, (0.20, 0.16, 0.08), (0, 0.02, C + 0.13), CAST)                                # cover
    bolt_circle(b, 6, 0.08, (0, 0.02, C + 0.17), "Z", STEEL, r=0.008, d=0.015)
    arrow_on_top(b, C + 0.175)
    return [to_object(b, "feValveCheck_Base", bevel=0.003)]


def model_valve_regulator(objs_name="feValveRegulator"):
    objs = []
    b = bmesh.new()
    valve_common(b)
    box(b, (0.20, 0.22, 0.20), (0, 0, C), CAST)
    cyl(b, 0.15, 0.06, (0, 0, C + 0.14), "Z", PAINT, segs=24)                            # diaphragm housing
    cyl(b, 0.16, 0.02, (0, 0, C + 0.175), "Z", CAST, segs=24)
    cyl(b, 0.04, 0.12, (0, 0, C + 0.24), "Z", CAST, segs=12)                             # spring bonnet
    cyl(b, 0.012, 0.10, (0, 0, C + 0.33), "Z", BRASS, segs=8)                            # adjusting screw
    box(b, (0.06, 0.012, 0.012), (0, 0, C + 0.385), BRASS)
    gauge(objs, b, (0.13, -0.12, C + 0.10), "FeNeedle_Out", r=0.04)
    objs.insert(0, to_object(b, objs_name + "_Base", bevel=0.003))
    return objs


def model_valve_separator():
    """Fluid separator: a filter canister with a sight glass (the chosen fluid shows) and a selector dial."""
    b = bmesh.new()
    valve_common(b)
    cyl(b, 0.13, 0.34, (0, 0, C + 0.06), "Z", CAST, segs=22)
    cyl(b, 0.14, 0.03, (0, 0, C + 0.24), "Z", STEEL, segs=22)
    bolt_circle(b, 8, 0.12, (0, 0, C + 0.255), "Z", STEEL, r=0.007, d=0.012)
    box(b, (0.05, 0.02, 0.18), (0, -0.13, C + 0.06), IRON)
    box(b, (0.03, 0.024, 0.15), (0, -0.131, C + 0.06), LIQUID)                          # sight glass
    cyl(b, 0.05, 0.02, (0.13, 0, C + 0.12), "X", BRASS, segs=14)                         # selector
    box(b, (0.006, 0.03, 0.008), (0.141, 0, C + 0.14), OUT)
    return [to_object(b, "feValveSeparator_Base", bevel=0.003)]


def model_valve_relief():
    """Relief valve: only an inlet (back); a spring bonnet and a vent pipe up that blows while it relieves."""
    objs = []
    b = bmesh.new()
    box(b, (0.30, 0.76, 0.04), (0, 0.04, 0.02), IRON)
    box(b, (0.10, 0.06, C - 0.10), (0, 0.30, (C - 0.10) / 2 + 0.04), IRON)
    cyl(b, PIPE_R, 0.50, (0, 0.25, C), "Y", STEEL, segs=16)
    flange(b, (0, 0.485, C), "Y", IN)
    cyl(b, 0.09, 0.16, (0, 0, C), "Y", CAST, segs=18)
    cyl(b, 0.07, 0.20, (0, 0, C + 0.17), "Z", RED, segs=16)                         # spring housing
    for k in range(5):
        ring(b, 0.075, 0.06, 0.012, (0, 0, C + 0.09 + k * 0.035), "Z", STEEL, segs=14)
    cyl(b, 0.01, 0.12, (0.08, 0, C + 0.22), "X", STEEL, segs=6)                          # test lever
    pipe_run(b, [(0, -0.05, C), (0, -0.20, C), (0, -0.20, 0.96)], r=0.04)               # vent stack
    cyl(b, 0.05, 0.04, (0, -0.20, 0.98), "Z", CAST, segs=12)
    objs.append(to_object(b, "feValveRelief_Base", bevel=0.003))
    objs.append(empty("FeFx_Steam_1", (0, -0.20, 1.0)))
    return objs


def model_gauge_block():
    """Pressure / flow gauge on a stand: reads the pipe at its back, big dial (FeNeedle_Gauge) facing the front, a
    signal lamp on top (FeGlow while it signals)."""
    objs = []
    b = bmesh.new()
    d12_base(b, w=0.40, h=0.04, stripe=False)
    cyl(b, PIPE_R, 0.30, (0, 0.35, C), "Y", STEEL, segs=16)
    flange(b, (0, 0.485, C), "Y", IN)
    box(b, (0.06, 0.06, C + 0.10), (0, 0.12, (C + 0.10) / 2), IRON)                     # post
    pipe_run(b, [(0, 0.20, C), (0, 0.05, C), (0, 0.05, C + 0.12)], r=0.012, mat=BRASS)
    cyl(b, 0.16, 0.05, (0, 0.0, C + 0.18), "Y", CAST, segs=28)
    gauge(objs, b, (0, -0.03, C + 0.18), "FeNeedle_Gauge", r=0.14)
    cyl(b, 0.035, 0.05, (0, 0.02, C + 0.38), "Z", GLOW, segs=12)                         # signal lamp
    cyl(b, 0.04, 0.012, (0, 0.02, C + 0.35), "Z", STEEL, segs=12)
    objs.insert(0, to_object(b, "feGauge_Base", bevel=0.003))
    return objs


def model_compressor():
    """Compressor (torque across X): a twin-cylinder V block on a receiver; gas in at the back, out at the front."""
    objs = []
    b = bmesh.new()
    d12_base(b)
    side_bearings(b)
    box(b, (0.46, 0.40, 0.30), (0, 0, 0.30), CAST)                                       # crankcase
    for sx in (-1, 1):                                                                    # V cylinders
        rot = Matrix.Rotation(sx * 0.6, 4, "Y")
        r = bmesh.ops.create_cone(b, cap_ends=True, cap_tris=False, segments=18, radius1=0.08, radius2=0.08,
                                  depth=0.24, calc_uvs=True)
        _fin(b, PAINT, Matrix.Translation((sx * 0.13, 0, 0.58)) @ rot, r["verts"])
        for k in range(5):
            r = bmesh.ops.create_cone(b, cap_ends=True, cap_tris=False, segments=18, radius1=0.095, radius2=0.095,
                                      depth=0.012, calc_uvs=True)
            _fin(b, STEEL, Matrix.Translation((sx * 0.13, 0, 0.58)) @ rot @ Matrix.Translation((0, 0, -0.08 + k * 0.04)), r["verts"])
    pipe_run(b, [(0, 0.40, C), (0, 0.22, C), (0, 0.15, 0.62)], r=0.03)
    pipe_run(b, [(-0.20, 0, 0.74), (0, -0.10, 0.80), (0, -0.30, C)], r=0.03)
    back_in(b)
    front_out(b)
    gauge(objs, b, (0.24, -0.22, 0.66), "FeNeedle_Out", r=0.05)
    objs.insert(0, to_object(b, "feCompressor_Base", bevel=0.003))
    drive_x(objs)
    return objs


# ---------------------------------------------------------------- tanks
def model_tank_liquid():
    """Liquid tank (joins its neighbours): riveted cylinder, nozzles on every face, a tall level glass with the fluid
    column (FeSurface_r0.70_Level, hidden in the tank when empty)."""
    objs = []
    b = bmesh.new()
    d12_base(b, stripe=False)
    cyl(b, 0.42, 0.86, (0, 0, 0.48), "Z", PAINT, segs=32)
    for z in (0.12, 0.48, 0.84):
        cyl(b, 0.428, 0.035, (0, 0, z), "Z", IRON, segs=32)
    cyl(b, 0.40, 0.04, (0, 0, 0.93), "Z", CAST, segs=32)
    cyl(b, 0.10, 0.06, (0, 0, 0.97), "Z", CAST, segs=16)                                 # manhole
    for v in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ax = "X" if v[0] else "Y"
        cyl(b, 0.05, 0.10, (v[0] * 0.45, v[1] * 0.45, C), ax, STEEL, segs=12)            # nozzles
    for x in (-0.27, 0.27):
        for y in (-0.27, 0.27):
            box(b, (0.05, 0.05, 0.10), (x, y, 0.08), IRON)
    LX, LY = 0.18, -0.405
    for z in (0.14, 0.86):
        box(b, (0.06, 0.05, 0.05), (LX, LY, z), BRASS)
    for k in range(3):
        a = 2 * math.pi * k / 3
        cyl(b, 0.004, 0.70, (LX + 0.022 * math.cos(a), LY - 0.02 + 0.022 * math.sin(a), 0.50), "Z", STEEL, segs=6)
    objs.append(to_object(b, "feTankLiquid_Base", bevel=0.003))
    col = bmesh.new()
    box(col, (0.02, 0.02, 0.72), (0, 0, -0.36), LIQUID)
    objs.append(to_object(col, "FeSurface_r0.70_Level", location=(LX, LY - 0.02, 0.16)))
    return objs


def model_tank_gas():
    """Gas tank: a horizontal pressure cylinder with dished ends on saddles, pressure gauge (FeNeedle_Bar), relief
    valve, hazard stripes, nozzles on every face."""
    objs = []
    b = bmesh.new()
    d12_base(b)
    cyl(b, 0.34, 0.80, (0, 0, C + 0.02), "Y", PAINT, segs=32)
    for s_ in (-1, 1):
        cyl(b, 0.34, 0.06, (0, s_ * 0.43, C + 0.02), "Y", PAINT, segs=32, r2=0.24)
        box(b, (0.56, 0.10, C - 0.20), (0, s_ * 0.26, (C - 0.20) / 2 + 0.05), CAST)
    for y in (-0.15, 0.15):
        cyl(b, 0.345, 0.05, (0, y, C + 0.02), "Y", HAZ, segs=32)
    for v in ((1, 0, 0), (-1, 0, 0)):
        cyl(b, 0.05, 0.14, (v[0] * 0.43, 0, C), "X", STEEL, segs=12)
    cyl(b, 0.05, 0.10, (0, 0, 0.92), "Z", STEEL, segs=12)
    cyl(b, 0.03, 0.08, (0.12, 0.10, 0.90), "Z", RED, segs=10)                       # relief
    gauge(objs, b, (-0.15, -0.36, C + 0.24), "FeNeedle_Bar", r=0.06)
    objs.insert(0, to_object(b, "feTankGas_Base", bevel=0.003))
    return objs


# ---------------------------------------------------------------- heat, sap
def model_gas_burner():
    """Gas burner (heats the machines it touches): a firebox with a ribbon burner behind a grate, gas train with a
    valve at the back; flames (FeFx_Fire), glow and a little smoke while lit."""
    objs = []
    b = bmesh.new()
    d12_base(b)
    plate(b, (0.80, 0.70, 0.62), (0, 0.04, 0.36), CAST, "-Y", n=6)
    box(b, (0.60, 0.02, 0.30), (0, -0.31, 0.34), SOOT)                                   # firebox mouth
    for k in range(7):
        box(b, (0.015, 0.03, 0.30), (-0.27 + k * 0.09, -0.335, 0.34), IRON)              # grate bars
    box(b, (0.56, 0.03, 0.03), (0, -0.352, 0.21), GLOW)                                  # ribbon burner (glows lit)
    box(b, (0.60, 0.05, 0.03), (0, -0.345, 0.18), CAST)
    for k in range(6):
        cyl(b, 0.012, 0.02, (-0.22 + k * 0.088, -0.352, 0.232), "Z", BRASS, segs=6)
    box(b, (0.84, 0.74, 0.05), (0, 0.04, 0.69), IRON)
    pipe_run(b, [(0, 0.40, C), (0, 0.30, C), (0.25, 0.30, C), (0.25, 0.30, 0.30)], r=0.025)
    cyl(b, PIPE_R, 0.10, (0, 0.45, C), "Y", STEEL, segs=16)
    flange(b, (0, 0.485, C), "Y", IN)
    ring(b, 0.05, 0.04, 0.01, (0.25, 0.36, C + 0.04), "Y", RED, segs=12)            # gas cock
    objs.append(to_object(b, "feGasBurner_Base", bevel=0.003))
    objs.append(empty("FeFx_Fire_1", (0, -0.32, 0.25)))
    objs.append(empty("FeFx_Smoke_1", (0, 0.04, 0.72)))
    return objs


def model_sap_tapper():
    """Sap tapper: its back hugs the tree trunk; a spile and a channel drip latex (FeFx_Drip) into a bucket with a
    latex surface (FeLiquid), drained by a pipe out of the front."""
    objs = []
    b = bmesh.new()
    for z in (0.35, 0.75):                                                                # strap round the trunk
        box(b, (0.70, 0.03, 0.04), (0, 0.48, z), RUST)
    box(b, (0.30, 0.04, 0.50), (0, 0.45, 0.55), WOOD)                                    # back board
    cyl(b, 0.02, 0.16, (0, 0.37, 0.80), "Y", STEEL, segs=8)                             # spile
    box(b, (0.06, 0.14, 0.03), (0, 0.30, 0.78), STEEL, Matrix.Rotation(0.3, 4, "X"))     # channel
    cyl(b, 0.14, 0.24, (0, 0.20, 0.42), "Z", STEEL, segs=20, r2=0.12)                   # bucket
    ring(b, 0.145, 0.13, 0.02, (0, 0.20, 0.54), "Z", IRON, segs=20)
    cyl(b, 0.125, 0.01, (0, 0.20, 0.50), "Z", LIQUID, segs=20)                           # latex in it
    box(b, (0.05, 0.05, 0.30), (0, 0.20, 0.15), IRON)
    pipe_run(b, [(0, 0.10, 0.34), (0, -0.20, 0.34), (0, -0.20, C), (0, -0.40, C)], r=0.03)
    flange(b, (0, -0.485, C), "Y", OUT)
    objs.append(to_object(b, "feSapTapper_Base", bevel=0.003))
    objs.append(empty("FeFx_Drip_1", (0, 0.24, 0.74)))
    return objs


# ---------------------------------------------------------------- distillation tower
def tower_shell(b, z0, z1, r=0.38):
    cyl(b, r, z1 - z0, (0, 0, (z0 + z1) / 2), "Z", PAINT, segs=32)
    for z in (z0 + 0.02, z1 - 0.02):
        cyl(b, r + 0.025, 0.04, (0, 0, z), "Z", CAST, segs=32)
        bolt_circle(b, 12, r + 0.012, (0, 0, z + (0.022 if z > (z0 + z1) / 2 else -0.022)), "Z", STEEL, r=0.008, d=0.012)


def model_tower_section():
    """Distillation tower section (stacks on the base): a flanged column segment with a tray, its fraction drawn off
    on all four sides (nozzles + flanges), a ladder and a level window."""
    b = bmesh.new()
    tower_shell(b, 0.0, 1.0)
    for v in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)):
        vv = Vector(v)
        ax = "X" if v[0] else "Y"
        cyl(b, PIPE_R, 0.14, vv * 0.43 + Vector((0, 0, C)), ax, STEEL, segs=16)
        flange(b, vv * 0.485 + Vector((0, 0, C)), ax, OUT)
    box(b, (0.10, 0.012, 0.20), (0.22, -0.32, 0.72), IRON)                                # window
    box(b, (0.07, 0.014, 0.16), (0.22, -0.321, 0.72), GLASS)
    for sx in (-1, 1):
        box(b, (0.02, 0.02, 1.0), (-0.30 + sx * 0.10, -0.33, 0.5), STEEL)                # ladder rails
    for k in range(5):
        box(b, (0.20, 0.02, 0.02), (-0.30, -0.33, 0.10 + k * 0.20), STEEL)
    return [to_object(b, "feTowerSection_Base", bevel=0.003)]


def model_distill_tower():
    """Distillation tower base: the reboiler (heated by a burner beside it), the feed in at the back, the bottom
    fraction out on both sides, a sight window and the first column flange on top for the sections."""
    objs = []
    b = bmesh.new()
    d12_base(b)
    tower_shell(b, 0.05, 1.0)
    box(b, (0.30, 0.02, 0.18), (0, -0.38, 0.30), SOOT)                                    # firebox window
    box(b, (0.24, 0.022, 0.04), (0, -0.381, 0.25), GLOW)
    for sx in (-1, 1):
        cyl(b, PIPE_R, 0.14, (sx * 0.43, 0, C), "X", STEEL, segs=16)
        flange(b, (sx * 0.485, 0, C), "X", OUT)
    back_in(b)
    gauge(objs, b, (0.20, -0.36, 0.70), "FeNeedle_Temp", r=0.05)
    objs.insert(0, to_object(b, "feDistillTower_Base", bevel=0.003))
    objs.append(empty("FeFx_Fire_1", (0, -0.40, 0.27)))
    return objs


# ---------------------------------------------------------------- processors
def proc_frame(b, torque=False):
    d12_base(b)
    back_in(b)
    low_chute(b)
    if torque:
        side_bearings(b)


def model_shale_retort():
    """Shale retort (heated): a brick-lined retort drum, the feed hopper, a condenser coil to the oil outlet and the
    gas off-take; glow and fire while it cooks."""
    objs = []
    b = bmesh.new()
    proc_frame(b)
    box(b, (0.70, 0.55, 0.50), (0, 0.05, 0.32), BRICK)
    for z in (0.12, 0.54):
        box(b, (0.74, 0.59, 0.04), (0, 0.05, z), IRON)
    cyl(b, 0.20, 0.62, (0, 0.05, 0.72), "X", CAST, segs=22)                               # retort drum
    for x in (-0.28, 0.28):
        cyl(b, 0.215, 0.04, (x, 0.05, 0.72), "X", STEEL, segs=22)
    box(b, (0.22, 0.02, 0.14), (0, -0.23, 0.30), SOOT)
    box(b, (0.18, 0.022, 0.03), (0, -0.231, 0.26), GLOW)
    for k in range(6):                                                                     # condenser coil
        ring(b, 0.07, 0.055, 0.015, (0.30, -0.20, 0.55 + k * 0.035), "Z", COPPER, segs=14)
    pipe_run(b, [(0.20, 0.05, 0.90), (0.30, -0.20, 0.90), (0.30, -0.20, 0.52)], r=0.025)
    pipe_run(b, [(-0.20, 0.05, 0.90), (-0.20, 0.05, 1.0)], r=0.03)
    objs.append(to_object(b, "feShaleRetort_Base", bevel=0.003))
    objs.append(empty("FeFx_Fire_1", (0, -0.25, 0.25)))
    objs.append(empty("FeFx_Smoke_1", (-0.20, 0.05, 1.0)))
    return objs


def model_cracker():
    """Catalytic cracker (400 W): an insulated reactor column with heater bands, a catalyst hopper and a cyclone."""
    objs = []
    b = bmesh.new()
    proc_frame(b)
    cyl(b, 0.22, 0.80, (-0.10, 0.05, 0.48), "Z", STEEL, segs=26)
    for k in range(5):
        cyl(b, 0.235, 0.03, (-0.10, 0.05, 0.15 + k * 0.15), "Z", COPPER, segs=26)        # heater bands
    cyl(b, 0.12, 0.30, (0.26, 0.10, 0.62), "Z", PAINT, segs=18, r2=0.04)                 # cyclone
    pipe_run(b, [(-0.10, 0.05, 0.90), (0.26, 0.10, 0.90), (0.26, 0.10, 0.78)], r=0.03)
    box(b, (0.16, 0.16, 0.12), (0.26, 0.20, 0.30), CAST)                                 # control box
    box(b, (0.10, 0.012, 0.06), (0.26, 0.115, 0.32), GLOW)
    objs.append(to_object(b, "feCracker_Base", bevel=0.003))
    wire(objs, (0.26, 0.20, 0.38))
    return objs


def model_gas_scrubber():
    """Gas scrubber: a packed column with a water spray at the top (FeFx_Spray) and an acid sump with its level."""
    objs = []
    b = bmesh.new()
    proc_frame(b)
    cyl(b, 0.22, 0.82, (0, 0.05, 0.50), "Z", PAINT, segs=26)
    for z in (0.20, 0.50, 0.80):
        cyl(b, 0.232, 0.03, (0, 0.05, z), "Z", IRON, segs=26)
    box(b, (0.08, 0.012, 0.40), (0.15, -0.165, 0.50), IRON)
    box(b, (0.05, 0.014, 0.36), (0.15, -0.166, 0.50), GLASS)
    pipe_run(b, [(0, 0.40, C), (0.25, 0.30, C), (0.25, 0.30, 0.94), (0, 0.05, 0.94)], r=0.025)
    objs.append(to_object(b, "feGasScrubber_Base", bevel=0.003))
    objs.append(empty("FeFx_Spray_1", (0, 0.05, 0.88)))
    return objs


def model_polymer_reactor():
    """Polymerisation reactor (300 W, 6 bar): a jacketed pressure vessel with a domed head, agitator motor on top,
    two gauges and a bursting disc."""
    objs = []
    b = bmesh.new()
    proc_frame(b)
    cyl(b, 0.28, 0.56, (0, 0.05, 0.42), "Z", STEEL, segs=28)
    cyl(b, 0.30, 0.40, (0, 0.05, 0.40), "Z", PAINT, segs=28)                              # jacket
    cyl(b, 0.28, 0.14, (0, 0.05, 0.77), "Z", STEEL, segs=28, r2=0.14)                    # domed head
    objs.append(to_object(b, "fePolymerReactor_Base", bevel=0.003))
    m = bmesh.new()
    finned_frame(m, 0.07, 0.14, 0.0, 0.0)
    objs.append(to_object(m, "fePolymerReactor_Motor", location=(0, 0.05, 0.95), rotation=AX_UP, bevel=0.002))
    b2 = bmesh.new()
    gauge(objs, b2, (0.20, -0.20, 0.70), "FeNeedle_Bar", r=0.045)
    cyl(b2, 0.03, 0.05, (-0.18, 0.05, 0.86), "Z", RED, segs=10)                    # bursting disc
    objs.append(to_object(b2, "fePolymerReactor_Fittings", bevel=0.002))
    wire(objs, (0, 0.05, 1.03))
    return objs


def open_tank(b, r, z0, z1, mat=STEEL, x=0.0, y=0.05):
    ring(b, r, r - 0.02, z1 - z0, (x, y, (z0 + z1) / 2), "Z", mat, segs=28)
    cyl(b, r - 0.02, 0.02, (x, y, z0 + 0.01), "Z", SOOT, segs=28)
    ring(b, r + 0.015, r - 0.015, 0.03, (x, y, z1), "Z", CAST, segs=28)


def model_coag_tank():
    """Coagulation tank: an open trough where latex and acid set; a slow paddle (FeWorkSpin) and the latex surface."""
    objs = []
    b = bmesh.new()
    proc_frame(b)
    for sx in (-1, 1):
        box(b, (0.03, 0.70, 0.36), (sx * 0.36, 0.04, 0.42), WOOD)
    for sy in (-1, 1):
        box(b, (0.72, 0.03, 0.36), (0, 0.04 + sy * 0.35, 0.42), WOOD)
    box(b, (0.72, 0.70, 0.03), (0, 0.04, 0.25), WOOD)
    for z in (0.30, 0.56):
        box(b, (0.76, 0.74, 0.03), (0, 0.04, z), RUST)
    for sx in (-1, 1):
        box(b, (0.04, 0.04, 0.40), (sx * 0.30, 0.04, 0.75), IRON)
    box(b, (0.64, 0.05, 0.04), (0, 0.04, 0.94), IRON)
    objs.append(to_object(b, "feCoagTank_Base", bevel=0.003))
    pd = bmesh.new()
    cyl(pd, 0.015, 0.40, (0, 0.20, 0), "Y", STEEL, segs=8)
    for k in range(4):
        box(pd, (0.10, 0.05, 0.012), (0.06, 0.36, 0), WOOD, Matrix.Rotation(k * math.pi / 2, 4, "Y"))
    objs.append(to_object(pd, "FeWorkSpin_x0.3_Paddle", location=(0, 0.04, 0.94), rotation=AX_UP, bevel=0.001))
    sf = bmesh.new()
    box(sf, (0.68, 0.012, 0.66), (0, 0, 0), LIQUID)
    objs.append(to_object(sf, "FeSurface_r0.20_Latex", location=(0, 0.04, 0.30), rotation=AX_UP))
    return objs


def model_calender():
    """Calender (torque): three stacked chilled rolls in heavy cast side frames (they turn), a feed table at the back
    and the sheet leaving at the front."""
    objs = []
    b = bmesh.new()
    proc_frame(b, torque=True)
    for sx in (-1, 1):
        plate(b, (0.08, 0.40, 0.80), (sx * 0.30, 0.05, 0.50), PAINT, "+X" if sx > 0 else "-X", n=4)
    box(b, (0.50, 0.24, 0.03), (0, 0.32, 0.62), STEEL)                                    # feed table
    box(b, (0.50, 0.03, 0.40), (0, -0.20, 0.42), CAST)
    objs.append(to_object(b, "feCalender_Base", bevel=0.003))
    drive_x(objs, gear_r=0.10)
    for k, z in enumerate((0.58, 0.74, 0.90)):
        r = bmesh.new()
        cyl(r, 0.075, 0.52, (0, 0, 0), "Y", STEEL, segs=20)
        name = "FeSpin_x2_Roll%d" % k if k != 1 else "FeSpin_x2_Rev_Roll1"
        objs.append(to_object(r, name, location=(0, 0.05, z), rotation=(0, 0, -math.pi / 2), bevel=0.001))
    return objs


def model_vulcanizer():
    """Vulcanising press (torque + 3 bar steam): a four-column press with heated platens; the upper platen moves
    (FePiston), steam leaks from it while it works."""
    objs = []
    b = bmesh.new()
    proc_frame(b, torque=True)
    box(b, (0.60, 0.50, 0.08), (0, 0.04, 0.30), CAST)                                     # lower platen
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(b, 0.03, 0.70, (sx * 0.24, 0.04 + sy * 0.18, 0.62), "Z", STEEL, segs=10)
    box(b, (0.62, 0.50, 0.10), (0, 0.04, 0.95), CAST)                                     # crown
    cyl(b, 0.10, 0.16, (0, 0.04, 0.86), "Z", PAINT, segs=18)                             # ram cylinder
    pipe_run(b, [(0, 0.40, C), (0.30, 0.30, 0.40)], r=0.02)
    objs.append(to_object(b, "feVulcanizer_Base", bevel=0.003))
    drive_x(objs)
    pl = bmesh.new()
    box(pl, (0.56, 0.08, 0.44), (0, 0.04, 0), CAST)
    cyl(pl, 0.04, 0.10, (0, -0.05, 0), "Y", STEEL, segs=10)
    objs.append(to_object(pl, "FePiston_Platen", location=(0, 0.04, 0.62), rotation=AX_UP, bevel=0.002))
    objs.append(empty("FeFx_Steam_1", (0.28, 0.04, 0.62)))
    return objs


def model_steel_converter():
    """Steel converter (heat + air): a Bessemer-style pear vessel on trunnions, refractory mouth glowing, an air
    blast pipe; sparks fly while it blows."""
    objs = []
    b = bmesh.new()
    proc_frame(b)
    for sx in (-1, 1):
        box(b, (0.08, 0.20, 0.60), (sx * 0.38, 0.05, 0.35), CAST)                         # trunnion stands
        cyl(b, 0.06, 0.10, (sx * 0.34, 0.05, 0.62), "X", STEEL, segs=14)
    cyl(b, 0.28, 0.40, (0, 0.05, 0.50), "Z", CAST, segs=26, r2=0.30)                     # vessel
    cyl(b, 0.30, 0.22, (0, 0.05, 0.81), "Z", CAST, segs=26, r2=0.14)                     # cone
    ring(b, 0.15, 0.10, 0.04, (0, 0.05, 0.93), "Z", BRICK, segs=20)
    cyl(b, 0.10, 0.02, (0, 0.05, 0.92), "Z", MOLTEN, segs=20)
    pipe_run(b, [(0.38, 0.05, 0.62), (0.38, 0.30, 0.62), (0.38, 0.30, 0.20), (0, 0.30, 0.20)], r=0.035)
    objs.append(to_object(b, "feSteelConverter_Base", bevel=0.003))
    objs.append(empty("FeFx_Sparks_1", (0, 0.05, 0.95)))
    objs.append(empty("FeFx_Smoke_1", (0, 0.05, 0.98)))
    return objs


def model_spring_coiler():
    """Spring coiler (torque): a wire spool feeding a turning mandrel (FeSpin) with a guide; springs in a tray."""
    objs = []
    b = bmesh.new()
    proc_frame(b, torque=True)
    box(b, (0.56, 0.40, 0.28), (0, 0.05, 0.28), PAINT)
    for sx in (-1, 1):
        box(b, (0.04, 0.10, 0.30), (sx * 0.20, 0.25, 0.55), IRON)
    box(b, (0.12, 0.10, 0.08), (0.18, -0.05, 0.60), CAST)                                 # wire guide
    for k in range(3):
        ring(b, 0.03, 0.022, 0.05, (-0.18 + k * 0.07, -0.25, 0.46), "Y", STEEL, segs=10)
    box(b, (0.30, 0.14, 0.04), (-0.12, -0.25, 0.42), STEEL)
    objs.append(to_object(b, "feSpringCoiler_Base", bevel=0.003))
    drive_x(objs, gear_r=0.09)
    sp = bmesh.new()                                                                       # spool across, turning
    cyl(sp, 0.12, 0.04, (0, -0.10, 0), "Y", WOOD, segs=18)
    cyl(sp, 0.12, 0.04, (0, 0.10, 0), "Y", WOOD, segs=18)
    cyl(sp, 0.08, 0.16, (0, 0, 0), "Y", COPPER, segs=18)
    objs.append(to_object(sp, "FeSpin_x0.5_Spool", location=(0, 0.25, 0.72), rotation=(0, 0, -math.pi / 2), bevel=0.001))
    md = bmesh.new()
    cyl(md, 0.025, 0.30, (0, 0, 0), "Y", STEEL, segs=10)
    for k in range(8):
        ring(md, 0.04, 0.03, 0.012, (0, -0.10 + k * 0.025, 0), "Y", STEEL, segs=10)
    objs.append(to_object(md, "FeSpin_x3_Mandrel", location=(0, -0.05, 0.60), rotation=(0, 0, -math.pi / 2), bevel=0.001))
    return objs


def model_temper_furnace():
    """Tempering furnace (heat + oil): a brick box furnace with a door and a quench oil tank beside it."""
    objs = []
    b = bmesh.new()
    proc_frame(b)
    box(b, (0.50, 0.60, 0.56), (-0.16, 0.05, 0.34), BRICK)
    box(b, (0.54, 0.64, 0.04), (-0.16, 0.05, 0.64), IRON)
    plate(b, (0.30, 0.04, 0.28), (-0.16, -0.27, 0.34), CAST, "-Y", n=3)
    box(b, (0.24, 0.02, 0.03), (-0.16, -0.295, 0.42), GLOW)
    cyl(b, 0.08, 0.30, (-0.16, 0.10, 0.82), "Z", IRON, segs=14)
    open_tank(b, 0.15, 0.10, 0.45, mat=STEEL, x=0.28, y=0.10)
    objs.append(to_object(b, "feTemperFurnace_Base", bevel=0.003))
    sf = bmesh.new()
    cyl(sf, 0.13, 0.01, (0, 0, 0), "Y", LIQUID, segs=20)
    objs.append(to_object(sf, "FeSurface_r0.18_Oil", location=(0.28, 0.10, 0.22), rotation=AX_UP))
    objs.append(empty("FeFx_Fire_1", (-0.16, -0.30, 0.30)))
    objs.append(empty("FeFx_Smoke_1", (-0.16, 0.10, 0.98)))
    return objs


def model_spinner():
    """Spinning frame (torque): a row of spindles (they turn fast), a fibre creel above and the drafting rollers."""
    objs = []
    b = bmesh.new()
    proc_frame(b, torque=True)
    box(b, (0.60, 0.30, 0.30), (0, 0.10, 0.30), WOOD)
    for sx in (-1, 1):
        box(b, (0.04, 0.04, 0.50), (sx * 0.28, 0.20, 0.68), WOOD)
    box(b, (0.60, 0.04, 0.04), (0, 0.20, 0.92), WOOD)
    for k in range(4):
        cyl(b, 0.05, 0.08, (-0.18 + k * 0.12, 0.20, 0.86), "Z", COPPER, segs=12)           # fibre bobbins (creel)
    objs.append(to_object(b, "feSpinner_Base", bevel=0.003))
    drive_x(objs)
    for k in range(4):
        sp = bmesh.new()
        cyl(sp, 0.012, 0.22, (0, -0.11, 0), "Y", STEEL, segs=8)
        cyl(sp, 0.03, 0.10, (0, -0.12, 0), "Y", COPPER, segs=10)
        objs.append(to_object(sp, "FeSpin_x6_Spindle%d" % k, location=(-0.18 + k * 0.12, -0.02, 0.46), rotation=AX_UP, bevel=0.001))
    return objs


def model_tannery():
    """Tannery: two wooden vats (tan liquor, FeSurface) with hides draped over a beam."""
    objs = []
    b = bmesh.new()
    proc_frame(b)
    for x in (-0.20, 0.20):
        open_tank(b, 0.18, 0.06, 0.55, mat=WOOD, x=x, y=0.08)
        for z in (0.15, 0.45):
            ring(b, 0.188, 0.175, 0.025, (x, 0.08, z), "Z", RUST, segs=24)
    box(b, (0.80, 0.04, 0.04), (0, 0.08, 0.80), WOOD)
    for sx in (-1, 1):
        box(b, (0.04, 0.04, 0.80), (sx * 0.40, 0.08, 0.40), WOOD)
    for x in (-0.25, 0.05, 0.28):
        box(b, (0.16, 0.012, 0.26), (x, 0.06, 0.67), LEATHER)                       # hides
    objs.append(to_object(b, "feTannery_Base", bevel=0.003))
    for i, x in enumerate((-0.20, 0.20)):
        sf = bmesh.new()
        cyl(sf, 0.16, 0.01, (0, 0, 0), "Y", LIQUID, segs=20)
        objs.append(to_object(sf, "FeSurface_r0.30_Liquor%d" % i, location=(x, 0.08, 0.20), rotation=AX_UP))
    return objs


def model_fermenter():
    """Fermenter: a closed vessel with an airlock bubbling (FeFx_Bubbles), a sight glass and a temperature gauge."""
    objs = []
    b = bmesh.new()
    proc_frame(b)
    cyl(b, 0.30, 0.70, (0, 0.06, 0.43), "Z", STEEL, segs=28)
    cyl(b, 0.30, 0.10, (0, 0.06, 0.83), "Z", STEEL, segs=28, r2=0.10)
    for z in (0.20, 0.50, 0.74):
        cyl(b, 0.31, 0.03, (0, 0.06, z), "Z", IRON, segs=28)
    cyl(b, 0.02, 0.10, (0, 0.06, 0.92), "Z", STEEL, segs=8)
    cyl(b, 0.04, 0.08, (0, 0.06, 0.99), "Z", GLASS, segs=12)                             # airlock
    box(b, (0.06, 0.012, 0.40), (0.16, -0.245, 0.45), IRON)
    gauge(objs, b, (-0.14, -0.255, 0.60), "FeNeedle_Temp", r=0.045)
    objs.insert(0, to_object(b, "feFermenter_Base", bevel=0.003))
    objs.append(empty("FeFx_Bubbles_1", (0, 0.06, 1.02)))
    return objs


def model_centrifuge():
    """Centrifuge (electric): a heavy drum under a clamped lid on an anti-vibration base; the rotor turns fast
    (FeWorkSpin) under a window."""
    objs = []
    b = bmesh.new()
    proc_frame(b)
    box(b, (0.66, 0.60, 0.20), (0, 0.05, 0.20), CAST)
    for x in (-0.25, 0.25):
        for y in (-0.18, 0.28):
            cyl(b, 0.05, 0.08, (x, y, 0.07), "Z", SOOT, segs=10)                          # rubber mounts
    ring(b, 0.27, 0.24, 0.36, (0, 0.05, 0.48), "Z", STEEL, segs=28)
    cyl(b, 0.24, 0.02, (0, 0.05, 0.31), "Z", SOOT, segs=28)
    ring(b, 0.28, 0.14, 0.04, (0, 0.05, 0.68), "Z", CAST, segs=28)                        # lid ring (window)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        box(b, (0.04, 0.04, 0.10), (0.27 * math.cos(a), 0.05 + 0.27 * math.sin(a), 0.68), STEEL)   # clamps
    box(b, (0.16, 0.10, 0.12), (0.26, 0.30, 0.38), CAST)
    box(b, (0.10, 0.012, 0.05), (0.26, 0.249, 0.40), GLOW)
    objs.append(to_object(b, "feCentrifuge_Base", bevel=0.003))
    ro = bmesh.new()
    cyl(ro, 0.04, 0.30, (0, 0.15, 0), "Y", STEEL, segs=10)
    for k in range(6):
        a_ = k * math.pi / 3
        box(ro, (0.20, 0.03, 0.04), (0.10 * math.cos(a_), 0.04, 0.10 * math.sin(a_)), STEEL, Matrix.Rotation(-a_, 4, "Y"))
        cyl(ro, 0.03, 0.08, (0.19 * math.cos(a_), 0.06, 0.19 * math.sin(a_)), "Y", BRASS, segs=8)
    objs.append(to_object(ro, "FeWorkSpin_x8_Rotor", location=(0, 0.05, 0.66), rotation=AX_UP, bevel=0.001))
    wire(objs, (0.26, 0.30, 0.46))
    return objs


def model_autoclave():
    """Autoclave (3 bar steam): a horizontal pressure vessel with a hinged quick-opening door and its locking
    wheel, a safety valve, gauge and steam trap."""
    objs = []
    b = bmesh.new()
    proc_frame(b)
    cyl(b, 0.28, 0.66, (0, 0.08, 0.50), "Y", STEEL, segs=30)
    for y in (-0.10, 0.20, 0.38):
        cyl(b, 0.29, 0.03, (0, y, 0.50), "Y", IRON, segs=30)
    cyl(b, 0.30, 0.06, (0, -0.25, 0.50), "Y", CAST, segs=30)                              # door
    bolt_circle(b, 12, 0.27, (0, -0.28, 0.50), "Y", STEEL, r=0.012, d=0.03)
    ring(b, 0.12, 0.10, 0.02, (0, -0.30, 0.50), "Y", RED, segs=18)                   # locking wheel
    for k in range(3):
        box(b, (0.22, 0.015, 0.015), (0, -0.30, 0.50), RED, Matrix.Rotation(k * math.pi / 3, 4, "Y"))
    for sx in (-1, 1):
        box(b, (0.10, 0.50, 0.24), (sx * 0.20, 0.08, 0.15), CAST)
    cyl(b, 0.03, 0.12, (0.10, 0.20, 0.82), "Z", RED, segs=10)
    gauge(objs, b, (-0.18, -0.30, 0.78), "FeNeedle_Bar", r=0.045)
    objs.insert(0, to_object(b, "feAutoclave_Base", bevel=0.003))
    objs.append(empty("FeFx_Steam_1", (0.10, 0.20, 0.90)))
    return objs


def model_cooker_industrial():
    """Industrial cooker (heat): two steam kettles with lids and a stirring paddle, a steam manifold and gauge."""
    objs = []
    b = bmesh.new()
    proc_frame(b)
    box(b, (0.84, 0.50, 0.40), (0, 0.10, 0.25), PAINT)
    for x in (-0.20, 0.20):
        open_tank(b, 0.17, 0.45, 0.72, mat=STEEL, x=x, y=0.10)
    pipe_run(b, [(0, 0.40, C), (-0.38, 0.36, C), (0.38, 0.36, C)], r=0.025)
    box(b, (0.30, 0.04, 0.20), (0.20, 0.22, 0.86), STEEL, Matrix.Rotation(-0.6, 4, "X"))   # open lid
    objs.append(to_object(b, "feCookerIndustrial_Base", bevel=0.003))
    for i, x in enumerate((-0.20, 0.20)):
        sf = bmesh.new()
        cyl(sf, 0.15, 0.01, (0, 0, 0), "Y", LIQUID, segs=20)
        objs.append(to_object(sf, "FeSurface_r0.18_Spin_Pot%d" % i, location=(x, 0.10, 0.50), rotation=AX_UP))
    objs.append(empty("FeFx_Steam_1", (-0.20, 0.10, 0.74)))
    objs.append(empty("FeFx_Steam_2", (0.20, 0.10, 0.74)))
    return objs


def model_mill():
    """Grain mill (torque): a millstone pair under a wooden hopper (the runner stone turns), meal spout to the front."""
    objs = []
    b = bmesh.new()
    proc_frame(b, torque=True)
    box(b, (0.60, 0.56, 0.30), (0, 0.05, 0.30), WOOD)
    cyl(b, 0.27, 0.10, (0, 0.05, 0.50), "Z", CAST, segs=26)                               # bed stone
    ring(b, 0.30, 0.27, 0.22, (0, 0.05, 0.60), "Z", WOOD, segs=26)                        # tun
    for k, (w, z) in enumerate(((0.36, 0.95), (0.26, 0.88), (0.16, 0.81))):
        for s_ in (-1, 1):
            box(b, (0.02, w, 0.08), (s_ * w / 2, 0.05, z), WOOD)
            box(b, (w, 0.02, 0.08), (0, 0.05 + s_ * w / 2, z), WOOD)
    objs.append(to_object(b, "feMill_Base", bevel=0.003))
    drive_x(objs, gear_r=0.10)
    rs = bmesh.new()
    cyl(rs, 0.25, 0.10, (0, 0, 0), "Y", CAST, segs=26)
    cyl(rs, 0.05, 0.11, (0, 0, 0), "Y", SOOT, segs=12)
    for k in range(8):
        a_ = k * math.pi / 4
        box(rs, (0.20, 0.11, 0.008), (0.12 * math.cos(a_), 0, 0.12 * math.sin(a_)), SOOT, Matrix.Rotation(-a_, 4, "Y"))
    objs.append(to_object(rs, "FeSpin_x0.5_Runner", location=(0, 0.05, 0.60), rotation=AX_UP, bevel=0.002))
    return objs


def model_juice_press():
    """Juice press (torque): a slatted basket under a screw head (the press plate goes down: FePiston), a pan and
    the juice spout."""
    objs = []
    b = bmesh.new()
    proc_frame(b, torque=True)
    box(b, (0.60, 0.56, 0.24), (0, 0.05, 0.22), CAST)
    cyl(b, 0.26, 0.03, (0, 0.05, 0.35), "Z", STEEL, segs=26)                              # pan
    for k in range(16):                                                                   # slatted basket
        a = 2 * math.pi * k / 16
        box(b, (0.03, 0.02, 0.34), (0.20 * math.cos(a), 0.05 + 0.20 * math.sin(a), 0.54), WOOD,
            Matrix.Rotation(a, 4, "Z"))
    for z in (0.42, 0.66):
        ring(b, 0.215, 0.20, 0.02, (0, 0.05, z), "Z", RUST, segs=24)
    for sx in (-1, 1):
        box(b, (0.05, 0.08, 0.60), (sx * 0.30, 0.05, 0.62), CAST)
    box(b, (0.66, 0.10, 0.08), (0, 0.05, 0.94), CAST)
    objs.append(to_object(b, "feJuicePress_Base", bevel=0.003))
    drive_x(objs)
    pp = bmesh.new()
    cyl(pp, 0.18, 0.04, (0, 0, 0), "Y", WOOD, segs=22)
    cyl(pp, 0.025, 0.24, (0, -0.12, 0), "Y", STEEL, segs=10)                             # screw
    for k in range(8):
        ring(pp, 0.035, 0.024, 0.01, (0, -0.04 - k * 0.025, 0), "Y", STEEL, segs=10)
    objs.append(to_object(pp, "FePiston_Plate", location=(0, 0.05, 0.70), rotation=AX_UP, bevel=0.001))
    return objs


def model_canner():
    """Canner (steam): a can track, the filling head and the seamer chuck (it turns while it works)."""
    objs = []
    b = bmesh.new()
    proc_frame(b)
    box(b, (0.80, 0.50, 0.40), (0, 0.10, 0.25), PAINT)
    box(b, (0.70, 0.12, 0.02), (0, -0.05, 0.46), STEEL)                                  # can track
    for k in range(5):
        cyl(b, 0.035, 0.07, (-0.28 + k * 0.14, -0.05, 0.50), "Z", STEEL, segs=12)         # cans
    box(b, (0.16, 0.16, 0.30), (-0.18, 0.12, 0.62), CAST)                                 # filler
    cyl(b, 0.05, 0.10, (-0.18, 0.12, 0.82), "Z", STEEL, segs=12)
    box(b, (0.06, 0.20, 0.40), (0.20, 0.20, 0.65), CAST)                                  # seamer column
    box(b, (0.16, 0.22, 0.06), (0.20, 0.05, 0.82), CAST)
    objs.append(to_object(b, "feCanner_Base", bevel=0.003))
    ch = bmesh.new()
    cyl(ch, 0.045, 0.06, (0, 0, 0), "Y", STEEL, segs=14)
    box(ch, (0.012, 0.06, 0.10), (0.05, 0, 0), BRASS)
    objs.append(to_object(ch, "FeWorkSpin_x3_Seamer", location=(0.20, -0.05, 0.62), rotation=AX_UP, bevel=0.001))
    objs.append(empty("FeFx_Steam_1", (-0.18, 0.12, 0.88)))
    return objs


def model_injector():
    """Injection moulding machine (electric caster): hopper, heated barrel with bands, the clamp unit with the mould;
    FeCastMetal (the polymer filling the mould) and FeCastReady (parts waiting), like the Casting Table."""
    objs = []
    b = bmesh.new()
    d12_base(b)
    back_in(b)
    low_chute(b)
    box(b, (0.80, 0.50, 0.30), (0, 0.10, 0.20), PAINT)
    cyl(b, 0.06, 0.46, (0.10, 0.10, 0.48), "X", STEEL, segs=16)                           # barrel
    for k in range(4):
        cyl(b, 0.072, 0.03, (-0.06 + k * 0.08, 0.10, 0.48), "X", COPPER, segs=16)        # heater bands
    for k, (w, z) in enumerate(((0.20, 0.78), (0.14, 0.70), (0.08, 0.62))):              # hopper
        for s_ in (-1, 1):
            box(b, (0.02, w, 0.08), (0.24 + s_ * w / 2, 0.10, z), PAINT)
            box(b, (w, 0.02, 0.08), (0.24, 0.10 + s_ * w / 2, z), PAINT)
    for sy in (-1, 1):
        cyl(b, 0.02, 0.36, (-0.26, 0.10 + sy * 0.12, 0.48), "X", STEEL, segs=8)          # tie bars
    box(b, (0.06, 0.34, 0.26), (-0.10, 0.10, 0.48), CAST)                                 # fixed platen
    box(b, (0.06, 0.34, 0.26), (-0.40, 0.10, 0.48), CAST)
    box(b, (0.14, 0.24, 0.02), (-0.24, 0.0, 0.44), SAND)                                  # mould cavity floor
    objs.append(to_object(b, "feInjector_Base", bevel=0.003))
    m = bmesh.new()
    box(m, (0.12, 0.22, 0.04), (0, 0, 0.02), MOLTEN)
    objs.append(to_object(m, "FeCastMetal", location=(-0.24, 0.0, 0.455)))
    rd = bmesh.new()
    for k in range(3):
        box(rd, (0.08, 0.06, 0.03), (-0.08 + k * 0.08, 0, 0.015), CAST)
    objs.append(to_object(rd, "FeCastReady", location=(-0.10, -0.38, LOW + 0.02)))
    wire(objs, (0.30, 0.30, 0.40))
    return objs


def model_gas_motor():
    """Gas Motor: the gas engine on a skid with two gas bottles strapped to it (it burns gas canisters)."""
    objs = model_gas_engine()
    objs[0].name = objs[0].data.name = "feGasMotor_Base"
    b = bmesh.new()
    for x in (-0.36, -0.22):
        cyl(b, 0.06, 0.50, (x, 0.34, 0.30), "Z", RED, segs=16)
        cyl(b, 0.06, 0.06, (x, 0.34, 0.58), "Z", RED, segs=16, r2=0.02)
        cyl(b, 0.015, 0.05, (x, 0.34, 0.63), "Z", BRASS, segs=8)
    box(b, (0.30, 0.02, 0.03), (-0.29, 0.27, 0.40), RUST)                                 # strap
    pipe_run(b, [(-0.36, 0.34, 0.65), (-0.10, 0.20, 0.65), (0.10, 0.08, C + 0.06)], r=0.008, mat=COPPER)
    objs.append(to_object(b, "feGasMotor_Bottles", bevel=0.002))
    return objs


# ---------------------------------------------------------------- in-line stations (sit on the block above a belt)
def inline_frame(b, objs, name, powered=False, torque=True):
    """A gantry over the belt below: a deck at the bottom of this block, a housing above it, legs hanging down to
    the belt's floor (FeReach_*, not in the collider) and a torque shaft across at 0.5 when it needs torque."""
    box(b, (0.90, 0.70, 0.05), (0, 0, 0.025), CAST)
    hazard(b, 0.88, (0, -0.354, 0.025), "X", h=0.04, n=12)
    if torque:
        side_bearings(b, z=C)
    lg = bmesh.new()
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(lg, (0.045, 0.045, 1.0), (sx * 0.47, sy * 0.32, -0.50), IRON)
            box(lg, (0.08, 0.10, 0.02), (sx * 0.47, sy * 0.32, -0.99), IRON)
        beam(lg, (sx * 0.47, -0.32, -0.95), (sx * 0.47, 0.32, -0.10), 0.025, 0.025, RUST)
    objs.append(to_object(lg, "FeReach_Legs", bevel=0.002))
    if powered:
        wire(objs, (0.30, 0.25, 0.60))


def inline_tool(objs, name, tool_bm, torque=True):
    """The working head: it moves up / down over the belt (FePiston via KineticSpinner with torque; FeWorkSpin
    otherwise)."""
    nm = ("FePiston_Inline" if torque else "FeReach_Head_") + name
    objs.append(to_object(tool_bm, nm, location=(0, 0, 0.05), rotation=AX_UP, bevel=0.0015))


def tool_ram(w=0.18, reach=0.70, head=None):
    t = bmesh.new()
    cyl(t, 0.03, reach, (0, reach / 2, 0), "Y", STEEL, segs=12)                           # down (local +Y = down)
    box(t, (w, 0.06, w), (0, reach, 0), CAST)
    if head:
        head(t, reach)
    return t


def model_inline_press():
    objs = []
    b = bmesh.new()
    inline_frame(b, objs, "InlinePress")
    box(b, (0.40, 0.36, 0.40), (0, 0.04, 0.30), PAINT)
    cyl(b, 0.16, 0.10, (0, 0.04, 0.56), "Z", CAST, segs=20)
    objs.insert(0, to_object(b, "feInlinePress_Base", bevel=0.003))
    drive_x(objs, gear_r=0.10)
    inline_tool(objs, "Ram", tool_ram(0.22, 0.62, lambda t, r: box(t, (0.24, 0.03, 0.24), (0, r + 0.04, 0), STEEL)))
    return objs


def model_doser():
    objs = []
    b = bmesh.new()
    inline_frame(b, objs, "Doser", torque=False)
    cyl(b, 0.18, 0.40, (0, 0.04, 0.40), "Z", GLASS, segs=20, r2=0.10)                    # dosing hopper
    cyl(b, 0.19, 0.03, (0, 0.04, 0.60), "Z", CAST, segs=20)
    box(b, (0.30, 0.30, 0.12), (0, 0.04, 0.12), CAST)
    pipe_run(b, [(0, 0.45, C), (0, 0.30, C), (0, 0.15, 0.40)], r=0.025)
    back_in(b)
    objs.insert(0, to_object(b, "feDoser_Base", bevel=0.003))
    nz = bmesh.new()
    cyl(nz, 0.02, 0.80, (0, 0.40, 0), "Y", STEEL, segs=10)
    cyl(nz, 0.04, 0.06, (0, 0.80, 0), "Y", BRASS, segs=10, r2=0.01)
    objs.append(to_object(nz, "FeReach_Nozzle", location=(0, 0.04, 0.06), rotation=AX_UP, bevel=0.001))
    objs.append(empty("FeFx_Drip_1", (0, 0.04, -0.76)))
    return objs


def model_inserter():
    objs = []
    b = bmesh.new()
    inline_frame(b, objs, "Inserter")
    box(b, (0.40, 0.40, 0.30), (0, 0.06, 0.25), PAINT)
    cyl(b, 0.10, 0.40, (0.22, 0.20, 0.55), "Z", GLASS, segs=16)                          # parts magazine
    objs.insert(0, to_object(b, "feInserter_Base", bevel=0.003))
    drive_x(objs)
    inline_tool(objs, "Pick", tool_ram(0.10, 0.62, lambda t, r: [box(t, (0.02, 0.08, 0.08), (s * 0.04, r + 0.05, 0), STEEL) for s in (-1, 1)]))
    return objs


def model_crimper():
    objs = []
    b = bmesh.new()
    inline_frame(b, objs, "Crimper")
    box(b, (0.36, 0.36, 0.34), (0, 0.04, 0.27), PAINT)
    ring(b, 0.12, 0.08, 0.06, (0, 0.04, 0.48), "Z", CAST, segs=16)
    objs.insert(0, to_object(b, "feCrimper_Base", bevel=0.003))
    drive_x(objs)
    inline_tool(objs, "Die", tool_ram(0.12, 0.62, lambda t, r: ring(t, 0.06, 0.035, 0.06, (0, r + 0.04, 0), "Y", STEEL, segs=12)))
    return objs


def model_wire_drawer():
    objs = []
    b = bmesh.new()
    inline_frame(b, objs, "WireDrawer")
    box(b, (0.50, 0.40, 0.30), (0, 0.06, 0.24), PAINT)
    for x in (-0.15, 0.0, 0.15):
        box(b, (0.08, 0.10, 0.10), (x, -0.20, 0.10), CAST)                                # draw dies
    objs.insert(0, to_object(b, "feWireDrawer_Base", bevel=0.003))
    drive_x(objs)
    cp = bmesh.new()
    cyl(cp, 0.14, 0.08, (0, 0, 0), "Y", STEEL, segs=22)
    cyl(cp, 0.16, 0.015, (0, -0.04, 0), "Y", CAST, segs=22)
    objs.append(to_object(cp, "FeSpin_x1_Capstan", location=(0, 0.06, 0.48), rotation=AX_UP, bevel=0.001))
    return objs


def model_grinder():
    objs = []
    b = bmesh.new()
    inline_frame(b, objs, "Grinder")
    box(b, (0.30, 0.30, 0.30), (0.20, 0.10, 0.25), PAINT)
    ring(b, 0.20, 0.12, 0.10, (0, 0.04, -0.55), "Y", HAZ, segs=24)                        # wheel guard (low)
    objs.insert(0, to_object(b, "feGrinder_Base", bevel=0.003))
    drive_x(objs)
    gw = bmesh.new()
    cyl(gw, 0.17, 0.05, (0, 0, 0), "Y", SAND, segs=24)
    cyl(gw, 0.04, 0.07, (0, 0, 0), "Y", STEEL, segs=10)
    objs.append(to_object(gw, "FeSpin_x6_InlineWheel", location=(0, 0.04, -0.55), bevel=0.001))
    sh = bmesh.new()
    box(sh, (0.04, 0.04, 0.58), (0, 0.10, -0.27), STEEL)
    objs.append(to_object(sh, "FeReach_Drop", bevel=0.001))
    objs.append(empty("FeFx_Sparks_1", (0, -0.14, -0.70)))
    return objs


def model_bender():
    objs = []
    b = bmesh.new()
    inline_frame(b, objs, "Bender")
    box(b, (0.60, 0.36, 0.34), (0, 0.04, 0.27), PAINT)
    objs.insert(0, to_object(b, "feBender_Base", bevel=0.003))
    drive_x(objs, gear_r=0.10)
    inline_tool(objs, "Punch", tool_ram(0.10, 0.62, lambda t, r: box(t, (0.50, 0.06, 0.03), (0, r + 0.04, 0), STEEL)))
    return objs


def model_welder():
    objs = []
    b = bmesh.new()
    inline_frame(b, objs, "Welder", powered=True, torque=False)
    box(b, (0.40, 0.40, 0.36), (0.10, 0.08, 0.23), PAINT)                                  # transformer
    for k in range(5):
        box(b, (0.012, 0.36, 0.30), (0.31, 0.08 - 0.15 + k * 0.075, 0.23), IRON)
    pipe_run(b, [(-0.10, 0.10, 0.30), (-0.10, 0.10, 0.06)], r=0.02, mat=SOOT)
    objs.insert(0, to_object(b, "feWelder_Base", bevel=0.003))
    tr = bmesh.new()
    cyl(tr, 0.02, 0.66, (0, 0.33, 0), "Y", SOOT, segs=8)                                   # cable down
    cyl(tr, 0.03, 0.10, (0, 0.70, 0), "Y", BRASS, segs=10, r2=0.01)                       # torch
    objs.append(to_object(tr, "FeReach_Torch", location=(-0.10, 0.10, 0.06), rotation=AX_UP, bevel=0.001))
    objs.append(empty("FeFx_Sparks_1", (-0.10, 0.10, -0.74)))
    return objs


def model_reflow_oven():
    objs = []
    b = bmesh.new()
    inline_frame(b, objs, "ReflowOven", powered=True, torque=False)
    plate(b, (0.60, 0.40, 0.20), (0, 0.04, 0.15), PAINT, "-Y", n=4)
    box(b, (0.30, 0.012, 0.06), (0, -0.165, 0.18), GLOW)
    hd = bmesh.new()                                                                       # heated hood over the belt
    box(hd, (0.64, 0.50, 0.04), (0, 0, -0.55), CAST)
    for sx in (-1, 1):
        box(hd, (0.04, 0.50, 0.26), (sx * 0.30, 0, -0.68), CAST)
    for k in range(5):
        box(hd, (0.56, 0.02, 0.015), (0, -0.20 + k * 0.10, -0.575), GLOW)               # heater elements
    objs.insert(0, to_object(b, "feReflowOven_Base", bevel=0.003))
    objs.append(to_object(hd, "FeReach_Hood", bevel=0.002))
    return objs


# ---------------------------------------------------------------- logistics and signals
def model_mech_arm():
    """Mechanical Arm (electric): a turret (FeArmYaw) with a two-link arm and a claw; it swings from behind (pick)
    to the front (place) once per transfer."""
    objs = []
    b = bmesh.new()
    cyl(b, 0.30, 0.06, (0, 0, 0.03), "Z", CAST, segs=24)
    cyl(b, 0.18, 0.14, (0, 0, 0.13), "Z", PAINT, segs=22)
    hazard(b, 0.40, (0, -0.30, 0.03), "X", h=0.04, n=8)
    objs.append(to_object(b, "feMechArm_Base", bevel=0.003))
    a = bmesh.new()                                     # built Z up, then turned so its local +Y is up
    cyl(a, 0.15, 0.10, (0, 0, 0.05), "Z", CAST, segs=20)
    box(a, (0.10, 0.10, 0.36), (0, 0, 0.28), PAINT)                                        # upper post
    beam(a, (0, 0, 0.44), (0, -0.40, 0.54), 0.06, 0.06, PAINT)                            # boom
    beam(a, (0, -0.40, 0.54), (0, -0.44, 0.30), 0.05, 0.05, STEEL)                        # forearm
    for s_ in (-1, 1):
        box(a, (0.015, 0.05, 0.10), (s_ * 0.04, -0.44, 0.24), STEEL)                      # claw
    cyl(a, 0.04, 0.12, (0, 0, 0.44), "X", BRASS, segs=12)
    bmesh.ops.transform(a, matrix=Matrix.Rotation(-math.pi / 2, 4, "X"), verts=a.verts)
    objs.append(to_object(a, "FeArmYaw", location=(0, 0, 0.20), rotation=(math.pi / 2, 0, 0), bevel=0.002))
    wire(objs, (0.18, 0.10, 0.22))
    return objs


def model_signal_lever():
    objs = []
    b = bmesh.new()
    box(b, (0.30, 0.20, 0.10), (0, 0, 0.05), CAST)
    box(b, (0.10, 0.012, 0.03), (-0.08, -0.105, 0.06), IN)
    box(b, (0.10, 0.012, 0.03), (0.08, -0.105, 0.06), OUT)
    for sx in (-1, 1):
        box(b, (0.015, 0.08, 0.06), (sx * 0.035, 0, 0.13), IRON)
    cyl(b, 0.012, 0.09, (0, 0, 0.14), "X", STEEL, segs=8)
    objs.append(to_object(b, "feSignalLever_Base", bevel=0.002))
    lv = bmesh.new()
    box(lv, (0.025, 0.025, 0.22), (0, 0, 0.11), HAZ)
    cyl(lv, 0.03, 0.05, (0, 0, 0.23), "Y", WOOD, segs=12)
    objs.append(to_object(lv, "FeLever_Signal", location=(0, 0, 0.14), bevel=0.002))
    return objs


def model_signal_receiver():
    """Signal Receiver: a junction box with a relay and a lamp (lit while it passes the signal on); wire on top."""
    objs = []
    b = bmesh.new()
    plate(b, (0.34, 0.30, 0.34), (0, 0, 0.17), PAINT, "-Y", n=3)
    box(b, (0.30, 0.02, 0.26), (0, -0.155, 0.18), CAST)
    cyl(b, 0.04, 0.03, (0.08, -0.17, 0.26), "Y", GLOW, segs=12)                           # lamp
    ring(b, 0.05, 0.04, 0.02, (0.08, -0.17, 0.26), "Y", BRASS, segs=12)
    box(b, (0.08, 0.02, 0.06), (-0.08, -0.17, 0.12), BRASS)
    insulator(b, 0, 0, 0.34, n=2)
    objs.append(to_object(b, "feSignalReceiver_Base", bevel=0.002))
    wire(objs, (0, 0, 0.44))
    return objs


# ---------------------------------------------------------------- belt logistics: Harrison's belt + our parts
BELT_SRC = os.path.join(ART, "feConveyor", "hd", "feConveyor_src.blend")
BT = 0.18                                                       # belt top (Belt.Top)


def belt_base(name):
    """The low belt's own parts (Belt.cs finds them by name), under an empty root; our additions go on top. Parts
    named FeBeltExtra_* / FeLever_BeltGate are left out of the collider (FeBuild.OptionalParts)."""
    with bpy.data.libraries.load(BELT_SRC, link=False) as (src, dst):
        dst.objects = list(src.objects)
    root = bpy.data.objects.new(name + "_Base", None)
    return [root] + [o for o in dst.objects if o is not None]


def model_belt_splitter():
    """Belt Splitter: a belt with a diverter cabinet on its right side; a pivoting deflector blade over the belt and
    arrows on the cabinet (it sends items left and right in turn)."""
    objs = belt_base("feBeltSplitter")
    b = bmesh.new()
    box(b, (0.10, 0.40, 0.30), (0.46, 0.0, BT + 0.14), PAINT)                     # cabinet on the right rail
    hazard(b, 0.38, (0.405, 0.0, BT + 0.26), "Y", h=0.04, n=6)
    cyl(b, 0.05, 0.10, (0.46, 0.0, BT + 0.33), "Z", CAST, segs=14)               # actuator
    cyl(b, 0.012, 0.10, (0.30, 0.0, BT + 0.34), "X", STEEL, segs=8)
    for s_ in (-1, 1):
        for k, w in enumerate((0.06, 0.04, 0.02)):
            box(b, (0.008, 0.02, w), (0.512, s_ * (0.06 + 0.025 * k), BT + 0.14), OUT if s_ < 0 else IN)
    beam(b, (0.42, 0.0, BT + 0.34), (0.0, 0.0, BT + 0.34), 0.03, 0.03, IRON)    # boom over the belt
    cyl(b, 0.015, 0.10, (0.0, 0.0, BT + 0.29), "Z", STEEL, segs=8)              # blade pivot
    box(b, (0.02, 0.42, 0.10), (0.0, -0.10, BT + 0.06), STEEL, Matrix.Rotation(0.35, 4, "Z"))   # deflector blade
    objs.append(to_object(b, "FeBeltExtra_Splitter", bevel=0.002))
    return objs


def model_belt_gate():
    """Belt Gate: a belt with a gantry over it; the stop flap (FeLever_BeltGate) comes down across the belt while
    the gate holds the items (Signals.Active) and swings up when it lets them pass."""
    objs = belt_base("feBeltGate")
    b = bmesh.new()
    for sx in (-1, 1):
        box(b, (0.05, 0.08, 0.50), (sx * 0.47, 0.0, BT + 0.20), IRON)
        box(b, (0.10, 0.12, 0.02), (sx * 0.47, 0.0, BT - 0.04), IRON)
    box(b, (1.0, 0.08, 0.06), (0.0, 0.0, BT + 0.46), PAINT)
    hazard(b, 0.96, (0.0, -0.045, BT + 0.46), "X", h=0.04, n=12)
    box(b, (0.14, 0.12, 0.12), (0.38, 0.0, BT + 0.55), CAST)                       # signal actuator
    cyl(b, 0.03, 0.03, (0.38, -0.06, BT + 0.56), "Y", GLOW, segs=10)
    objs.append(to_object(b, "FeBeltExtra_Gantry", bevel=0.002))
    fl = bmesh.new()                                                                # hangs from its axle (pivot)
    cyl(fl, 0.015, 0.84, (0, 0, 0), "X", STEEL, segs=8)
    box(fl, (0.80, 0.02, 0.30), (0, 0, -0.16), RED)
    for k in range(4):
        box(fl, (0.10, 0.024, 0.06), (-0.30 + k * 0.20, 0, -0.27), HAZ)
    bmesh.ops.transform(fl, matrix=Matrix.Rotation(math.radians(-35), 4, "X"), verts=fl.verts)   # +1 = straight down
    objs.append(to_object(fl, "FeLever_BeltGate", location=(0.0, 0.0, BT + 0.42), bevel=0.002))
    return objs


def model_belt_counter():
    """Belt Counter: a belt with an arch carrying a light-eye pair and a counter box with number drums."""
    objs = belt_base("feBeltCounter")
    b = bmesh.new()
    for sx in (-1, 1):
        box(b, (0.05, 0.06, 0.36), (sx * 0.47, 0.10, BT + 0.14), IRON)
        box(b, (0.06, 0.05, 0.05), (sx * 0.44, 0.10, BT + 0.08), CAST)            # light eyes
        cyl(b, 0.015, 0.02, (sx * 0.41, 0.10, BT + 0.08), "X", GLOW, segs=10)
    box(b, (1.0, 0.06, 0.05), (0.0, 0.10, BT + 0.33), IRON)
    box(b, (0.30, 0.12, 0.14), (0.0, 0.10, BT + 0.42), PAINT)                     # counter box
    box(b, (0.24, 0.012, 0.06), (0.0, 0.036, BT + 0.43), IRON)
    for k in range(4):
        cyl(b, 0.025, 0.05, (-0.09 + k * 0.06, 0.04, BT + 0.43), "X", WOOD if k % 2 else STEEL, segs=10)
    cyl(b, 0.02, 0.05, (0.17, 0.04, BT + 0.47), "Y", RED, segs=10)                # reset button
    objs.append(to_object(b, "FeBeltExtra_Counter", bevel=0.002))
    return objs


D12_MODELS = {
    "fePipeHP": model_pipe_hp, "feValveShutoff": model_valve_shutoff, "feValveCheck": model_valve_check,
    "feValveRegulator": model_valve_regulator, "feValveSeparator": model_valve_separator,
    "feValveRelief": model_valve_relief, "feGauge": model_gauge_block, "feCompressor": model_compressor,
    "feTankLiquid": model_tank_liquid, "feTankGas": model_tank_gas, "feGasBurner": model_gas_burner,
    "feSapTapper": model_sap_tapper, "feTowerSection": model_tower_section, "feDistillTower": model_distill_tower,
    "feShaleRetort": model_shale_retort, "feCracker": model_cracker, "feGasScrubber": model_gas_scrubber,
    "fePolymerReactor": model_polymer_reactor, "feCoagTank": model_coag_tank, "feCalender": model_calender,
    "feVulcanizer": model_vulcanizer, "feSteelConverter": model_steel_converter, "feSpringCoiler": model_spring_coiler,
    "feTemperFurnace": model_temper_furnace, "feSpinner": model_spinner, "feTannery": model_tannery,
    "feFermenter": model_fermenter, "feCentrifuge": model_centrifuge, "feAutoclave": model_autoclave,
    "feCookerIndustrial": model_cooker_industrial, "feMill": model_mill, "feJuicePress": model_juice_press,
    "feCanner": model_canner, "feInjector": model_injector, "feGasMotor": model_gas_motor,
    "feInlinePress": model_inline_press, "feDoser": model_doser, "feInserter": model_inserter,
    "feCrimper": model_crimper, "feWireDrawer": model_wire_drawer, "feGrinder": model_grinder,
    "feBender": model_bender, "feWelder": model_welder, "feReflowOven": model_reflow_oven,
    "feMechArm": model_mech_arm, "feSignalLever": model_signal_lever, "feSignalReceiver": model_signal_receiver,
    "feBeltSplitter": model_belt_splitter, "feBeltGate": model_belt_gate, "feBeltCounter": model_belt_counter,
}


def model_bus():
    """Power Bus (1 block): a riveted switchgear cabinet. Three copper bus bars on insulator posts across the top, a
    row of incoming insulators at the back (one per dynamo wired to it), the big outgoing insulator in front (the
    wire anchor, WireOffset), a main breaker handle on the side, an ammeter and a danger plate on the door."""
    b = bmesh.new()
    box(b, (0.80, 0.60, 0.06), (0, 0, 0.03), IRON)                                       # plinth
    hazard(b, 0.78, (0, -0.304, 0.03), "X", h=0.05, n=10)
    plate(b, (0.70, 0.50, 0.64), (0, 0, 0.38), PAINT, "-Y", n=6)                         # cabinet
    plate(b, (0.70, 0.50, 0.64), (0, 0, 0.38), PAINT, "+Y", n=6)
    box(b, (0.76, 0.56, 0.04), (0, 0, 0.72), IRON)                                       # roof
    for sx in (-1, 1):                                                                    # corner angles
        for sy in (-1, 1):
            box(b, (0.03, 0.03, 0.66), (sx * 0.355, sy * 0.255, 0.38), IRON)
    # door: frame, louvres, handle, ammeter, danger plate
    box(b, (0.56, 0.02, 0.52), (0, -0.258, 0.38), CAST)
    for k in range(5):
        box(b, (0.22, 0.012, 0.018), (0.14, -0.27, 0.20 + k * 0.04), SOOT)
    box(b, (0.03, 0.03, 0.12), (-0.22, -0.28, 0.40), STEEL)
    cyl(b, 0.07, 0.03, (-0.06, -0.275, 0.52), "Y", CAST, segs=20)
    cyl(b, 0.058, 0.032, (-0.06, -0.277, 0.52), "Y", GLASS, segs=20)
    box(b, (0.004, 0.006, 0.05), (-0.06, -0.296, 0.535), RED, Matrix.Rotation(0.5, 4, "Y"))
    box(b, (0.14, 0.008, 0.10), (0.14, -0.27, 0.53), HAZ)                                # danger plate
    box(b, (0.06, 0.010, 0.05), (0.14, -0.275, 0.53), SOOT)
    # main breaker on the right side
    box(b, (0.04, 0.12, 0.20), (-0.37, 0.0, 0.45), CAST)
    beam(b, (-0.40, 0.0, 0.45), (-0.44, 0.0, 0.60), 0.025, 0.025, RED)
    cyl(b, 0.025, 0.06, (-0.44, 0.0, 0.62), "Y", WOOD, segs=10)
    # bus bars on posts across the top
    for y in (-0.12, 0.0, 0.12):
        for x in (-0.28, 0.28):
            insulator(b, x, y, 0.74, n=2, s=0.8)
        box(b, (0.66, 0.025, 0.035), (0, y, 0.83), COPPER)
    # incoming insulators at the back (dynamo wires) and the outgoing one in front
    for k in range(4):
        insulator(b, -0.24 + k * 0.16, 0.22, 0.74, n=3, s=0.9)
        beam(b, (-0.24 + k * 0.16, 0.22, 0.86), (-0.24 + k * 0.16, 0.12, 0.83), 0.012, 0.012, COPPER)
    insulator(b, 0.0, -0.20, 0.74, n=5, s=1.2)
    beam(b, (0.0, -0.20, 0.98), (0.0, -0.12, 0.83), 0.015, 0.015, COPPER)
    objs = [to_object(b, "feBus_Base", bevel=0.003)]
    wire(objs, (0.0, -0.20, 1.02))
    return objs


# ================================================================ D13 blocks (PENDENCIAS_ASSETS.md), all 1 x 1
# Contracts: world machines / fan: shaft across (Blender X) at 0.5, working face = front (-Y); cog / windmill: shaft
# along Y (like feShaft); holder: depot top 0.82, chute = closed vertical tube; display: digits drawn by DisplayVisual
# on the front face at 0.52 m; processor: FeItemAnchor; deployer: FeItemAnchor + FeHead_; belt tunnel: the belt.


def hub_x(objs, name="FeSpin_DriveShaft"):
    """Torque shaft across X at 0.5 with couplings on both side faces (turns)."""
    drive_x(objs)
    objs[-1].name = objs[-1].data.name = name


def gearbox_body(b, w=0.62, d=0.56, h=0.62, y=0.10):
    d12_base(b)
    side_bearings(b)
    cast_housing(b, w, d, h)
    for k, z in enumerate((0.20, 0.42)):
        box(b, (w + 0.02, 0.02, 0.03), (0, y - d / 2 - 0.01 + 0.10, z), IRON)


def model_mech_drill():
    """Mechanical Drill: a geared drill head on a cast body; the auger bit (FeSpin_x2_Bit) turns along the front."""
    objs = []
    b = bmesh.new()
    d12_base(b)
    side_bearings(b)
    box(b, (0.60, 0.50, 0.56), (0, 0.18, 0.36), CAST)
    cyl(b, 0.22, 0.20, (0, -0.12, C), "Y", PAINT, segs=24)                               # drill head
    bolt_circle(b, 8, 0.19, (0, -0.22, C), "Y", STEEL, r=0.012, d=0.02)
    box(b, (0.50, 0.10, 0.06), (0, 0.42, 0.10), RUST)                                     # spoil chute at the back
    hazard(b, 0.58, (0, -0.07, 0.66), "X", h=0.04, n=8)
    objs.append(to_object(b, "feMechDrill_Base", bevel=0.003))
    hub_x(objs)
    bit = bmesh.new()
    cyl(bit, 0.07, 0.30, (0, -0.15, 0), "Y", STEEL, segs=14)
    for k in range(10):                                                                   # auger flight
        a_ = k * 0.9
        box(bit, (0.20, 0.02, 0.04), (0, -0.04 - k * 0.026, 0), STEEL, Matrix.Rotation(a_, 4, "Y"))
    cyl(bit, 0.05, 0.08, (0, -0.33, 0), "Y", STEEL, segs=12, r2=0.005)                   # tip
    objs.append(to_object(bit, "FeSpin_x2_Bit", location=(0, -0.22, C), bevel=0.001))
    objs.append(empty("FeFx_Dust_1", (0, -0.50, C)))
    return objs


def model_mech_saw():
    """Mechanical Saw: a timber-frame bench with a big circular blade at the front (FeSpin_x3_Blade, turns across)."""
    objs = []
    b = bmesh.new()
    d12_base(b)
    side_bearings(b)
    box(b, (0.56, 0.60, 0.40), (0, 0.15, 0.30), PAINT)
    box(b, (0.08, 0.50, 0.30), (0.22, -0.18, 0.62), RUST)                                 # blade guard
    ring(b, 0.40, 0.36, 0.06, (0.16, -0.10, C), "X", HAZ, segs=24)
    objs.append(to_object(b, "feMechSaw_Base", bevel=0.003))
    hub_x(objs)
    bl = bmesh.new()
    cyl(bl, 0.36, 0.012, (0, 0, 0), "Y", STEEL, segs=40)
    for k in range(24):
        a_ = 2 * math.pi * k / 24
        box(bl, (0.04, 0.014, 0.03), (0.37 * math.cos(a_), 0, 0.37 * math.sin(a_)), STEEL, Matrix.Rotation(-a_ + 0.4, 4, "Y"))
    cyl(bl, 0.06, 0.03, (0, 0, 0), "Y", CAST, segs=12)
    objs.append(to_object(bl, "FeSpin_x3_Blade", location=(0.12, -0.12, C), rotation=(0, 0, -math.pi / 2), bevel=0.001))
    objs.append(empty("FeFx_Dust_1", (0.12, -0.48, 0.30)))
    return objs


def model_mech_harvester():
    """Mechanical Harvester: a reel with tines across the front (FeSpin_x0.5_Reel) over a cutter bar, a bin behind."""
    objs = []
    b = bmesh.new()
    d12_base(b)
    side_bearings(b)
    box(b, (0.60, 0.40, 0.36), (0, 0.22, 0.26), PAINT)
    box(b, (0.84, 0.12, 0.03), (0, -0.40, 0.10), STEEL)                                   # cutter bar
    for k in range(11):
        box(b, (0.02, 0.10, 0.015), (-0.40 + k * 0.08, -0.47, 0.10), STEEL)
    for sx in (-1, 1):
        beam(b, (sx * 0.42, 0.10, 0.40), (sx * 0.42, -0.30, C), 0.04, 0.04, IRON)
    objs.append(to_object(b, "feMechHarvester_Base", bevel=0.003))
    hub_x(objs)
    r = bmesh.new()
    cyl(r, 0.025, 0.86, (0, 0, 0), "Y", STEEL, segs=10)
    for k in range(5):
        a_ = 2 * math.pi * k / 5
        for y in (-0.38, 0.0, 0.38):
            box(r, (0.02, 0.02, 0.22), (0.11 * math.cos(a_), y, 0.11 * math.sin(a_)), WOOD, Matrix.Rotation(-a_ + math.pi / 2, 4, "Y"))
        box(r, (0.03, 0.84, 0.03), (0.22 * math.cos(a_), 0, 0.22 * math.sin(a_)), WOOD)
        for t in range(6):
            box(r, (0.008, 0.008, 0.08), (0.24 * math.cos(a_), -0.35 + t * 0.14, 0.24 * math.sin(a_) - 0.04), STEEL)
    objs.append(to_object(r, "FeSpin_x0.5_Reel", location=(0, -0.30, C), rotation=(0, 0, -math.pi / 2), bevel=0.001))
    return objs


def model_deployer():
    """Deployer: a box with a push ram in front (FeHead_Ram goes out as it places) and the held block on a tray
    (FeItemAnchor)."""
    objs = []
    b = bmesh.new()
    d12_base(b)
    side_bearings(b)
    plate(b, (0.62, 0.62, 0.56), (0, 0.10, 0.35), PAINT, "-Y", n=4)
    box(b, (0.30, 0.04, 0.30), (0, -0.22, C), SOOT)                                        # ram opening
    box(b, (0.40, 0.30, 0.03), (0, 0.10, 0.65), STEEL)                                    # tray on top
    objs.append(to_object(b, "feDeployer_Base", bevel=0.003))
    hub_x(objs)
    ram = bmesh.new()
    cyl(ram, 0.035, 0.30, (0, 0.15, 0), "Y", STEEL, segs=12)
    box(ram, (0.26, 0.04, 0.26), (0, 0, 0), CAST)
    objs.append(to_object(ram, "FeHead_Ram", location=(0, -0.26, C), bevel=0.001))
    objs.append(empty("FeItemAnchor", (0, 0.10, 0.80)))
    return objs


def model_fan():
    """Industrial Fan: a ducted fan in a riveted ring facing the front, guard grille; the blades turn (FeSpin_x4)."""
    objs = []
    b = bmesh.new()
    d12_base(b)
    side_bearings(b)
    ring(b, 0.46, 0.40, 0.50, (0, 0, C), "Y", PAINT, segs=36)
    for y in (-0.24, 0.24):
        ring(b, 0.48, 0.44, 0.04, (0, y, C), "Y", CAST, segs=36)
        bolt_circle(b, 12, 0.46, (0, y, C), "Y", STEEL, r=0.008, d=0.05)
    for k in range(4):                                                                     # struts + motor pod
        a_ = k * math.pi / 2 + math.pi / 4
        box(b, (0.42, 0.03, 0.03), (0.21 * math.cos(a_), 0.16, C + 0.21 * math.sin(a_)), IRON, Matrix.Rotation(-a_, 4, "Y"))
    cyl(b, 0.12, 0.22, (0, 0.16, C), "Y", CAST, segs=18)
    for k in range(7):                                                                     # front grille
        box(b, (0.84, 0.012, 0.012), (0, -0.26, C - 0.36 + k * 0.12), STEEL)
    box(b, (0.84, 0.06, C - 0.44), (0, 0, (C - 0.44) / 2 + 0.05), CAST)
    objs.append(to_object(b, "feFan_Base", bevel=0.003))
    hub_x(objs)
    fb = bmesh.new()
    cyl(fb, 0.08, 0.10, (0, 0, 0), "Y", STEEL, segs=14)
    for k in range(6):
        a_ = 2 * math.pi * k / 6
        box(fb, (0.32, 0.012, 0.11), (0.21 * math.cos(a_), 0, 0.21 * math.sin(a_)), STEEL,
            Matrix.Rotation(-a_, 4, "Y") @ Matrix.Rotation(0.45, 4, "X"))
    objs.append(to_object(fb, "FeSpin_x4_Blades", location=(0, -0.10, C), bevel=0.001))
    objs.append(empty("FeFx_Dust_1", (0, -0.50, C)))
    return objs


def model_mech_piston():
    """Mechanical Piston: a heavy cylinder body with a gear-driven rack; the front plate is where the Piston Head
    (a block of its own) comes out."""
    objs = []
    b = bmesh.new()
    d12_base(b)
    side_bearings(b)
    cyl(b, 0.34, 0.66, (0, 0.10, C), "Y", PAINT, segs=28)
    for y in (-0.18, 0.10, 0.38):
        cyl(b, 0.355, 0.04, (0, y, C), "Y", CAST, segs=28)
    box(b, (0.84, 0.06, 0.84), (0, -0.40, C), CAST)                                       # front plate
    hazard(b, 0.80, (0, -0.435, C + 0.38), "X", h=0.05, n=10)
    box(b, (0.20, 0.30, 0.16), (0, 0.10, C + 0.38), CAST)                                 # rack box
    objs.append(to_object(b, "feMechPiston_Base", bevel=0.003))
    hub_x(objs)
    return objs


def model_piston_head():
    """Piston Head (block in front of an extended piston): a push plate and the rod back to the piston."""
    b = bmesh.new()
    box(b, (0.92, 0.10, 0.92), (0, -0.44, C), CAST)
    hazard(b, 0.90, (0, -0.495, C), "X", h=0.08, n=10)
    cyl(b, 0.09, 0.92, (0, 0.04, C), "Y", STEEL, segs=18)
    for y in (-0.20, 0.20):
        cyl(b, 0.11, 0.04, (0, y, C), "Y", BRASS, segs=18)
    return [to_object(b, "fePistonHead_Base", bevel=0.003)]


def model_cogwheel():
    """Cogwheel: a big spur gear on its shaft (axis front-back like a Shaft); its teeth reach the side faces so cogs
    side by side mesh."""
    objs = []
    b = bmesh.new()
    for sy in (-1, 1):
        box(b, (0.10, 0.06, C - 0.10), (0, sy * 0.40, (C - 0.10) / 2), IRON)
        cyl(b, 0.08, 0.08, (0, sy * 0.40, C), "Y", CAST, segs=16)
    box(b, (0.30, 0.90, 0.04), (0, 0, 0.02), IRON)
    objs.append(to_object(b, "feCogwheel_Base", bevel=0.003))
    g = bmesh.new()
    shaft_end(g, 0.0, -0.5)
    shaft_end(g, 0.0, 0.5)
    gear(g, 0.43, 0.12, 24, (0, 0, 0), "Y", BRASS, tooth=0.06)
    cyl(g, 0.30, 0.13, (0, 0, 0), "Y", CAST, segs=24)
    for k in range(6):
        a_ = k * math.pi / 3
        cyl(g, 0.06, 0.14, (0.18 * math.cos(a_), 0, 0.18 * math.sin(a_)), "Y", SOOT, segs=10)   # lightening holes
    objs.append(to_object(g, "FeSpin_Cog", location=(0, 0, C), bevel=0.002))
    return objs


def model_windmill():
    """Windmill: a timber nacelle on a post with the shaft out of the back (axis front-back); four lattice sails with
    canvas turn in front (FeSpin_WindSails, out of the collider)."""
    objs = []
    b = bmesh.new()
    box(b, (0.30, 0.30, 0.40), (0, 0.10, 0.20), WOOD)                                     # post
    box(b, (0.50, 0.70, 0.36), (0, 0.05, 0.56), WOOD)                                     # nacelle
    for z in (0.40, 0.72):
        box(b, (0.52, 0.72, 0.03), (0, 0.05, z), RUST)
    box(b, (0.56, 0.76, 0.04), (0, 0.05, 0.76), PAINT, Matrix.Rotation(0.0, 4, "X"))      # roof
    cyl(b, 0.10, 0.20, (0, -0.35, C + 0.10), "Y", CAST, segs=16)
    objs.append(to_object(b, "feWindmill_Base", bevel=0.003))
    sh = bmesh.new()
    shaft_end(sh, 0.0, 0.5)
    objs.append(to_object(sh, "FeSpin_Shaft", location=(0, 0, C), bevel=0.002))
    s = bmesh.new()
    cyl(s, 0.10, 0.12, (0, 0, 0), "Y", CAST, segs=16)
    for k in range(4):
        a_ = k * math.pi / 2 + math.pi / 8
        m = Matrix.Rotation(-a_, 4, "Y")
        box(s, (1.50, 0.05, 0.05), (0.80 * math.cos(a_), 0, 0.80 * math.sin(a_)), WOOD, m)          # whip
        for t in range(5):
            r_ = 0.45 + t * 0.24
            box(s, (0.02, 0.03, 0.34), (r_ * math.cos(a_) + 0.17 * math.cos(a_ + math.pi / 2), 0.02,
                                         r_ * math.sin(a_) + 0.17 * math.sin(a_ + math.pi / 2)), WOOD, m)
        box(s, (1.10, 0.01, 0.30), ((0.95) * math.cos(a_) + 0.17 * math.cos(a_ + math.pi / 2), 0.04,
                                    0.95 * math.sin(a_) + 0.17 * math.sin(a_ + math.pi / 2)), LEATHER, m)   # canvas
    objs.append(to_object(s, "FeSpin_WindSails", location=(0, -0.52, C + 0.10), bevel=0.001))
    return objs


def model_hose_pulley():
    """Hose Pulley: a pump body with a hose reel across (it turns with the shaft) and the hose going straight down
    through the floor (FeReach_Hose, out of the collider); outlet at the front."""
    objs = []
    b = bmesh.new()
    d12_base(b)
    side_bearings(b)
    for sx in (-1, 1):
        box(b, (0.06, 0.50, 0.70), (sx * 0.30, 0.05, 0.40), PAINT)
    box(b, (0.30, 0.20, 0.20), (0, -0.25, 0.18), CAST)                                    # pump
    front_out(b)
    cyl(b, 0.08, 0.06, (0, 0.05, 0.035), "Z", CAST, segs=14)                              # floor gland
    objs.append(to_object(b, "feHosePulley_Base", bevel=0.003))
    hub_x(objs)
    rl = bmesh.new()
    cyl(rl, 0.22, 0.03, (0, -0.24, 0), "Y", RED, segs=24)
    cyl(rl, 0.22, 0.03, (0, 0.24, 0), "Y", RED, segs=24)
    cyl(rl, 0.14, 0.46, (0, 0, 0), "Y", WOOD, segs=20)
    for k in range(5):
        ring(rl, 0.17, 0.13, 0.07, (0, -0.18 + k * 0.09, 0), "Y", SOOT, segs=20)        # coiled hose
    objs.append(to_object(rl, "FeSpin_x0.3_Reel", location=(0, 0.05, 0.74), rotation=(0, 0, -math.pi / 2), bevel=0.001))
    h = bmesh.new()
    cyl(h, 0.04, 1.6, (0, 0.05, -0.75), "Z", SOOT, segs=10)
    cyl(h, 0.07, 0.10, (0, 0.05, -1.55), "Z", BRASS, segs=12)                             # strainer
    objs.append(to_object(h, "FeReach_Hose", bevel=0.001))
    return objs


def model_depot():
    """Depot: a low steel table with a raised rim, top at 0.82 (the item shows there)."""
    b = bmesh.new()
    box(b, (0.90, 0.90, 0.05), (0, 0, 0.025), IRON)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(b, (0.08, 0.08, 0.74), (sx * 0.38, sy * 0.38, 0.42), CAST)
    box(b, (0.88, 0.88, 0.04), (0, 0, 0.80), STEEL)
    for s_ in (-1, 1):
        box(b, (0.90, 0.03, 0.05), (0, s_ * 0.435, 0.84), IRON)
        box(b, (0.03, 0.90, 0.05), (s_ * 0.435, 0, 0.84), IRON)
    box(b, (0.80, 0.80, 0.03), (0, 0, 0.30), WOOD)                                        # shelf
    hazard(b, 0.86, (0, -0.44, 0.84), "X", h=0.04, n=10)
    return [to_object(b, "feDepot_Base", bevel=0.003), empty("FeItemAnchor", (0, 0, 0.86))]


def model_item_chute():
    """Item Chute: a closed square steel tube the full height (stacks into a column), riveted bands, an inspection
    hatch; open at top and bottom."""
    b = bmesh.new()
    for s_ in (-1, 1):
        box(b, (0.56, 0.03, 1.0), (0, s_ * 0.265, 0.5), PAINT)
        box(b, (0.03, 0.56, 1.0), (s_ * 0.265, 0, 0.5), PAINT)
    for z in (0.03, 0.97):
        for s_ in (-1, 1):
            box(b, (0.62, 0.05, 0.06), (0, s_ * 0.29, z), IRON)
            box(b, (0.05, 0.62, 0.06), (s_ * 0.29, 0, z), IRON)
    box(b, (0.30, 0.02, 0.36), (0, -0.285, 0.5), CAST)                                    # hatch
    box(b, (0.10, 0.03, 0.03), (0, -0.30, 0.5), STEEL)
    return [to_object(b, "feItemChute_Base", bevel=0.003)]


def model_item_vault():
    """Item Vault: a riveted steel vault cube with a wheel door; vaults side by side read as one wall of storage."""
    b = bmesh.new()
    plate(b, (0.96, 0.96, 0.96), (0, 0, 0.48), PAINT, "-Y", n=8)
    plate(b, (0.96, 0.96, 0.96), (0, 0, 0.48), PAINT, "+Y", n=8)
    for z in (0.04, 0.92):
        box(b, (0.98, 0.98, 0.08), (0, 0, z), IRON)
    box(b, (0.62, 0.04, 0.64), (0, -0.485, 0.48), CAST)                                   # door
    bolt_circle(b, 12, 0.28, (0, -0.51, 0.48), "Y", STEEL, r=0.012, d=0.02)
    ring(b, 0.14, 0.11, 0.03, (0, -0.52, 0.48), "Y", BRASS, segs=20)                      # wheel
    for k in range(3):
        box(b, (0.26, 0.015, 0.015), (0, -0.52, 0.48), BRASS, Matrix.Rotation(k * math.pi / 3, 4, "Y"))
    for z in (0.30, 0.66):
        box(b, (0.06, 0.05, 0.08), (0.33, -0.50, z), STEEL)                               # hinges
    box(b, (0.16, 0.01, 0.06), (-0.20, -0.51, 0.72), HAZ)
    return [to_object(b, "feItemVault_Base", bevel=0.003)]


def model_item_drain():
    """Item Drain: a tipping rack over a basin; the fluid goes up the pipe on top, jars in at the back, the empty
    jars out of the low chute in front."""
    objs = []
    b = bmesh.new()
    d12_base(b)
    low_chute(b)
    open_tank(b, 0.30, 0.10, 0.42, mat=STEEL, y=0.05)
    for sx in (-1, 1):
        box(b, (0.04, 0.04, 0.50), (sx * 0.34, 0.05, 0.62), IRON)
    cyl(b, 0.02, 0.70, (0, 0.05, 0.86), "X", STEEL, segs=8)                               # tipping axle
    box(b, (0.40, 0.20, 0.04), (0, 0.05, 0.78), RUST, Matrix.Rotation(0.5, 4, "X"))      # tipping rack
    pipe_run(b, [(0.22, 0.05, 0.30), (0.22, 0.05, 0.96)], r=0.035)
    cyl(b, PIPE_R, 0.06, (0.22, 0.05, 0.97), "Z", STEEL, segs=16)
    flange(b, (0.22, 0.05, 0.985), "Z", OUT)
    box(b, (0.34, 0.04, 0.24), (0, 0.46, 0.50), IN)                                       # back intake
    objs.append(to_object(b, "feItemDrain_Base", bevel=0.003))
    sf = bmesh.new()
    cyl(sf, 0.27, 0.01, (0, 0, 0), "Y", LIQUID, segs=24)
    objs.append(to_object(sf, "FeSurface_r0.25_Basin", location=(0, 0.05, 0.14), rotation=AX_UP))
    objs.append(empty("FeItemAnchor", (0, 0.05, 0.86)))
    objs.append(empty("FeFx_Drip_1", (0, -0.02, 0.74)))
    return objs


def model_display_panel():
    """Display Panel: a steel cabinet on the front face of its block, a dark glass face just inside that face
    (DisplayVisual writes the digits 0.52 m in front of the centre), a cable gland to the block behind it."""
    b = bmesh.new()
    box(b, (0.92, 0.22, 0.74), (0, -0.37, 0.50), PAINT)                                   # cabinet
    box(b, (0.96, 0.05, 0.78), (0, -0.465, 0.50), IRON)                                   # front frame
    box(b, (0.84, 0.02, 0.62), (0, -0.485, 0.50), SOOT)                                   # dark face
    box(b, (0.80, 0.012, 0.58), (0, -0.495, 0.50), GLASS)
    box(b, (0.80, 0.50, 0.05), (0, -0.20, 0.025), IRON)                                   # foot
    for sx in (-1, 1):
        beam(b, (sx * 0.38, -0.02, 0.05), (sx * 0.38, -0.26, 0.20), 0.04, 0.04, IRON)
    pipe_run(b, [(0, -0.26, 0.50), (0, 0.10, 0.50), (0, 0.10, 0.12)], r=0.025, mat=SOOT)   # cable to the block behind
    cyl(b, 0.05, 0.06, (0, -0.25, 0.50), "Y", CAST, segs=12)
    rivets(b, (-0.45, -0.49, 0.87), (0.45, -0.49, 0.87), 8)
    return [to_object(b, "feDisplayPanel_Base", bevel=0.003)]


def model_signal_analog():
    """Analog Lever: a lever on a graduated quadrant (0..15 marks); a signal block like the lever."""
    objs = []
    b = bmesh.new()
    box(b, (0.36, 0.26, 0.12), (0, 0, 0.06), CAST)
    for k in range(16):
        a_ = -0.9 + 1.8 * k / 15
        box(b, (0.006, 0.012, 0.03 if k % 5 else 0.05), (0.20 * math.sin(a_), -0.10, 0.12 + 0.20 * math.cos(a_)), HAZ if k % 5 == 0 else STEEL,
            Matrix.Rotation(-a_, 4, "Y"))
    box(b, (0.42, 0.02, 0.24), (0, -0.09, 0.22), IRON)                                    # quadrant plate
    cyl(b, 0.015, 0.12, (0, 0, 0.14), "X", STEEL, segs=8)
    box(b, (0.10, 0.012, 0.03), (-0.12, -0.135, 0.06), IN)
    box(b, (0.10, 0.012, 0.03), (0.12, -0.135, 0.06), OUT)
    objs.append(to_object(b, "feSignalAnalog_Base", bevel=0.002))
    lv = bmesh.new()
    box(lv, (0.025, 0.025, 0.26), (0, 0, 0.13), HAZ)
    cyl(lv, 0.03, 0.05, (0, 0, 0.27), "Y", WOOD, segs=12)
    objs.append(to_object(lv, "FeLever_Analog", location=(0, -0.05, 0.14), rotation=(0, 0.3, 0), bevel=0.002))
    return objs


def radio_box(name, mast, lamp_mat):
    b = bmesh.new()
    plate(b, (0.40, 0.30, 0.34), (0, 0, 0.17), PAINT, "-Y", n=3)
    box(b, (0.36, 0.02, 0.26), (0, -0.155, 0.18), CAST)
    for k in range(3):
        cyl(b, 0.025, 0.03, (-0.10 + k * 0.10, -0.17, 0.24), "Y", BRASS, segs=10)        # frequency knobs
    cyl(b, 0.035, 0.03, (0.12, -0.17, 0.10), "Y", lamp_mat, segs=12)
    box(b, (0.12, 0.012, 0.05), (-0.06, -0.165, 0.10), GLASS)
    mast(b)
    return [to_object(b, name, bevel=0.002)]


def model_wireless_tx():
    """Wireless Transmitter: a radio box with a tall whip antenna and coil (red lamp)."""
    def mast(b):
        cyl(b, 0.03, 0.06, (0.12, 0.06, 0.37), "Z", CAST, segs=10)
        cyl(b, 0.008, 0.55, (0.12, 0.06, 0.67), "Z", STEEL, segs=6)
        for k in range(6):
            ring(b, 0.03, 0.022, 0.01, (0.12, 0.06, 0.44 + k * 0.02), "Z", COPPER, segs=10)
        cyl(b, 0.02, 0.02, (0.12, 0.06, 0.95), "Z", RED, segs=8)
    return radio_box("feWirelessTx_Base", mast, RED)


def model_wireless_rx():
    """Wireless Receiver: a radio box with a small dish on a post (blue lamp)."""
    def mast(b):
        cyl(b, 0.02, 0.20, (0.10, 0.06, 0.44), "Z", STEEL, segs=8)
        r = bmesh.ops.create_cone(b, cap_ends=False, cap_tris=False, segments=20, radius1=0.16, radius2=0.02,
                                  depth=0.08, calc_uvs=True)
        _fin(b, STEEL, Matrix.Translation((0.10, 0.02, 0.60)) @ Matrix.Rotation(-1.1, 4, "X"), r["verts"])
        cyl(b, 0.01, 0.14, (0.10, -0.02, 0.62), "Y", COPPER, segs=6)
    return radio_box("feWirelessRx_Base", mast, IN)


def model_belt_tunnel():
    """Belt Tunnel: the low belt under a riveted cover with two filter windows; the sides open where it sorts."""
    objs = belt_base("feBeltTunnel")
    b = bmesh.new()
    for sy in (-1, 1):                                                                     # portal frames front / back
        for sx in (-1, 1):
            box(b, (0.04, 0.06, 0.40), (sx * 0.30, sy * 0.46, BT + 0.18), IRON)
        box(b, (0.64, 0.06, 0.05), (0, sy * 0.46, BT + 0.38), IRON)
    box(b, (0.66, 0.96, 0.03), (0, 0, BT + 0.41), PAINT)                                  # roof
    for sx in (-1, 1):
        box(b, (0.10, 0.30, 0.12), (sx * 0.22, 0.10, BT + 0.47), CAST)                    # filter boxes
        box(b, (0.08, 0.012, 0.08), (sx * 0.22, -0.056, BT + 0.47), GLASS)
        box(b, (0.02, 0.96, 0.04), (sx * 0.32, 0, BT + 0.38), IRON)
    hazard(b, 0.62, (0, -0.49, BT + 0.38), "X", h=0.04, n=8)
    objs.append(to_object(b, "FeBeltExtra_Tunnel", bevel=0.002))
    return objs


D13_MODELS = {
    "feMechDrill": model_mech_drill, "feMechSaw": model_mech_saw, "feMechHarvester": model_mech_harvester,
    "feDeployer": model_deployer, "feFan": model_fan, "feMechPiston": model_mech_piston,
    "fePistonHead": model_piston_head, "feCogwheel": model_cogwheel, "feWindmill": model_windmill,
    "feHosePulley": model_hose_pulley, "feDepot": model_depot, "feItemChute": model_item_chute,
    "feItemVault": model_item_vault, "feItemDrain": model_item_drain, "feDisplayPanel": model_display_panel,
    "feSignalAnalog": model_signal_analog, "feWirelessTx": model_wireless_tx, "feWirelessRx": model_wireless_rx,
    "feBeltTunnel": model_belt_tunnel,
}


# ================================================================ thermal power plant, round 2 (2026-11-27)
# More detail, 7DTD look (worn steel, rivets, wooden lagging, rust), more moving parts. Contracts: SteamPlant.cs.
def shell_x(name, r0, r1, a0, a1, x0, x1, mat, n=24, z=C, objs=None, rot=0.0):
    """A ring sector around the X axis (casings with a window): angles a0..a1 in the Y-Z plane (0 = +Y, pi/2 = up)."""
    bm = bmesh.new()
    arc_solid(bm, lambda r, th: (r * math.cos(th), r * math.sin(th)), r0, r1, a0, a1, x0, x1, n, mat)
    # arc_solid builds in (x, y) polar, extruded along z -> X = z, Y = x, Z = y
    for v in bm.verts:
        x, y, zz = v.co
        v.co = Vector((zz, x, y + z))
    ob = to_object(bm, name, bevel=0.002)
    if objs is not None:
        objs.append(ob)
    return ob


def rivet_ring_x(b, x, r, n, mat=IRON):
    """Rivet heads round a drum (axis X) at x."""
    for k in range(n):
        a_ = 2 * math.pi * k / n
        cyl(b, 0.008, 0.01, (x, r * math.cos(a_), C + r * math.sin(a_)), "X", mat, segs=6)


def spinner_x(name, bm, x, y=0.0, z=C):
    """An object built along Blender Y around the origin, laid across X (spins about X like the shaft)."""
    return to_object(bm, name, location=(x, y, z), rotation=(0, 0, -math.pi / 2), bevel=0.0015)


def model_steam_turbine():
    objs = []
    b = bmesh.new()
    # --- skid: two I-beams along X, cross members, anchor bolts
    for sy in (-0.30, 0.30):
        box(b, (0.96, 0.10, 0.02), (0, sy, 0.01), IRON)
        box(b, (0.96, 0.02, 0.10), (0, sy, 0.07), IRON)
        box(b, (0.96, 0.10, 0.02), (0, sy, 0.13), IRON)
        for x in (-0.40, 0.0, 0.40):
            cyl(b, 0.012, 0.03, (x, sy + 0.035, 0.15), "Z", STEEL, segs=6)
    for x in (-0.42, 0.42):
        box(b, (0.06, 0.62, 0.04), (x, 0, 0.12), IRON)
    hazard(b, 0.92, (0, -0.37, 0.07), "X", h=0.08, n=12)
    # --- bearing pedestals with caps, oil cups
    for sx in (-1, 1):
        x = sx * 0.40
        box(b, (0.12, 0.26, C - 0.18), (x, 0, (C - 0.18) / 2 + 0.14), CAST)
        box(b, (0.14, 0.20, 0.05), (x, 0, C - 0.055), CAST)
        box(b, (0.14, 0.20, 0.06), (x, 0, C + 0.06), PAINT)                              # cap
        for sy in (-1, 1):
            cyl(b, 0.012, 0.16, (x, sy * 0.08, C), "Z", STEEL, segs=6)                    # cap studs
            cyl(b, 0.02, 0.02, (x, sy * 0.08, C + 0.10), "Z", IRON, segs=6)
        cyl(b, 0.018, 0.06, (x, 0, C + 0.12), "Z", BRASS, segs=8)                         # oil cup
        cyl(b, 0.028, 0.03, (x, 0, C + 0.16), "Z", GLASS, segs=10)
    # --- casing ends, split flange, feet, lifting eyes
    for x, r in ((-0.30, 0.31), (0.26, 0.31)):
        cyl(b, r, 0.03, (x, 0, C), "X", CAST, segs=36)
        bolt_circle(b, 14, r - 0.025, (x + (0.017 if x > 0 else -0.017), 0, C), "X", STEEL, r=0.008, d=0.012)
        cyl(b, 0.07, 0.06, (x + (0.045 if x > 0 else -0.045), 0, C), "X", IRON, segs=16)   # gland box
    for sy in (-1, 1):
        box(b, (0.56, 0.06, 0.035), (-0.02, sy * 0.33, C), CAST)                          # horizontal joint
        for k in range(8):
            cyl(b, 0.01, 0.06, (-0.27 + k * 0.072, sy * 0.33, C), "Z", STEEL, segs=6)
        box(b, (0.40, 0.10, C - 0.16), (-0.02, sy * 0.24, (C - 0.16) / 2 + 0.14), CAST)  # casing feet
    for x in (-0.22, 0.18):
        ring(b, 0.035, 0.022, 0.015, (x, 0, C + 0.345), "Y", STEEL, segs=12)              # lifting eyes
    box(b, (0.14, 0.006, 0.06), (-0.05, -0.31, C - 0.10), BRASS)                          # name plate
    # --- steam: inlet at the back, stop valve with handwheel, up into the steam chest with the throttle valve
    cyl(b, PIPE_R, 0.12, (0, 0.44, C), "Y", STEEL, segs=16)
    flange(b, (0, 0.485, C), "Y", IN, bolts=8)
    box(b, (0.14, 0.12, 0.14), (0, 0.36, C), CAST)                                        # stop valve body
    cyl(b, 0.05, 0.10, (0, 0.36, C + 0.11), "Z", CAST, segs=14)
    cyl(b, 0.012, 0.10, (0, 0.36, C + 0.20), "Z", STEEL, segs=8)
    ring(b, 0.08, 0.065, 0.018, (0, 0.36, C + 0.25), "Z", RED, segs=18)
    for k in range(3):
        box(b, (0.15, 0.012, 0.012), (0, 0.36, C + 0.25), RED, Matrix.Rotation(k * math.pi / 3, 4, "Z"))
    pipe_run(b, [(0, 0.29, C), (0, 0.29, C + 0.36), (0, 0.16, C + 0.36)], r=0.05)
    box(b, (0.30, 0.16, 0.10), (-0.02, 0.12, C + 0.34), PAINT)                            # steam chest
    bolt_circle(b, 8, 0.07, (-0.02, 0.12, C + 0.395), "Z", STEEL, r=0.008, d=0.012)
    box(b, (0.10, 0.10, 0.10), (0.15, 0.12, C + 0.40), CAST)                              # throttle valve
    gauge(objs, b, (-0.17, 0.035, C + 0.38), "FeNeedle_Steam", r=0.05)
    # --- governor column on the chest (bevel box), the flyballs spin on top
    box(b, (0.09, 0.08, 0.08), (0.40, -0.15, C + 0.12), CAST)                             # governor bevel box (on the bearing)
    box(b, (0.04, 0.06, 0.10), (0.40, -0.10, C + 0.06), CAST)
    cyl(b, 0.02, 0.08, (0.40, -0.15, C + 0.20), "Z", STEEL, segs=8)
    beam(b, (0.40, -0.15, C + 0.16), (0.15, 0.06, C + 0.40), 0.012, 0.012, STEEL)          # governor rod to the throttle
    # --- exhaust hood at the front (to the condenser)
    box(b, (0.30, 0.22, 0.30), (-0.02, -0.22, C - 0.04), CAST)
    for k in range(3):
        box(b, (0.012, 0.24, 0.30), (-0.12 + k * 0.10, -0.22, C - 0.04), IRON)            # ribs
    cyl(b, 0.11, 0.10, (-0.02, -0.38, C), "Y", CAST, segs=20)
    cyl(b, PIPE_R, 0.06, (-0.02, -0.46, C), "Y", STEEL, segs=16)
    flange(b, (-0.02, -0.485, C), "Y", OUT, bolts=8)
    # --- oil: pump bracket over the pump crank (+X side), copper lines to both bearings, drip pan
    box(b, (0.08, 0.10, 0.05), (0.33, 0.13, C + 0.30), CAST)                              # pump bracket arm
    beam(b, (0.33, 0.20, 0.14), (0.33, 0.20, C + 0.30), 0.04, 0.04, CAST)
    cyl(b, 0.035, 0.16, (0.33, 0.0, C + 0.36), "Z", BRASS, segs=14)                       # pump barrel
    box(b, (0.10, 0.10, 0.03), (0.33, 0.0, C + 0.28), CAST)
    pipe_run(b, [(0.33, 0.0, C + 0.45), (0.33, -0.10, C + 0.45), (0.40, -0.10, C + 0.18)], r=0.008, mat=COPPER)
    pipe_run(b, [(0.33, 0.04, C + 0.45), (-0.40, 0.04, C + 0.45), (-0.40, 0.04, C + 0.18)], r=0.008, mat=COPPER)
    box(b, (0.80, 0.42, 0.015), (0, 0, 0.15), SOOT)                                       # drip pan
    for x in (-0.15, 0.10):
        box(b, (0.08, 0.03, 0.02), (x, -0.30, 0.17), RUST)                                # rust scabs
    objs.insert(0, to_object(b, "feSteamTurbine_Base", bevel=0.003))
    # casing halves: the lower half closed, the upper with an inspection window (grille) over the rotor
    shell_x("feSteamTurbine_CasingLow", 0.28, 0.31, math.pi, 2 * math.pi, -0.285, 0.245, CAST, n=24, objs=objs)
    shell_x("feSteamTurbine_CasingUpL", 0.28, 0.31, 0.0, math.pi * 0.36, -0.285, 0.245, PAINT, n=10, objs=objs)
    shell_x("feSteamTurbine_CasingUpR", 0.28, 0.31, math.pi * 0.64, math.pi, -0.285, 0.245, PAINT, n=10, objs=objs)
    g = bmesh.new()                                                                       # window frame + grille
    for sx in (-1, 1):
        box(g, (0.02, 0.26, 0.03), (sx * 0.26 - 0.02, 0, C + 0.30), IRON)
    for k in range(6):
        box(g, (0.52, 0.012, 0.012), (-0.02, -0.10 + k * 0.04, C + 0.305), STEEL)
    objs.append(to_object(g, "feSteamTurbine_Grille", bevel=0.001))
    # --- moving parts
    drive_x(objs)                                                                         # shaft + couplings
    ro = bmesh.new()                                                                      # rotor: three bladed wheels
    cyl(ro, 0.06, 0.52, (0, 0, 0), "Y", STEEL, segs=16)
    for y, r, n in ((-0.18, 0.20, 22), (-0.02, 0.23, 26), (0.14, 0.26, 30)):
        cyl(ro, r * 0.55, 0.04, (0, y, 0), "Y", STEEL, segs=24)
        for k in range(n):
            a_ = 2 * math.pi * k / n
            box(ro, (0.012, 0.035, r * 0.45), (r * 0.78 * math.sin(a_), y, r * 0.78 * math.cos(a_)), BRASS,
                Matrix.Rotation(a_, 4, "Y") @ Matrix.Rotation(0.5, 4, "Z"))
        ring(ro, r + 0.005, r - 0.012, 0.04, (0, y, 0), "Y", STEEL, segs=30)
    objs.append(spinner_x("FeSpin_x8_Rotor", ro, -0.02))
    bg = bmesh.new()                                                                      # barring gear on the shaft
    gear(bg, 0.13, 0.03, 30, (0, 0, 0), "Y", CAST, tooth=0.02)
    cyl(bg, 0.05, 0.05, (0, 0, 0), "Y", STEEL, segs=14)
    for k in range(5):
        a_ = k * 2 * math.pi / 5
        cyl(bg, 0.02, 0.035, (0.08 * math.cos(a_), 0, 0.08 * math.sin(a_)), "Y", SOOT, segs=8)
    objs.append(spinner_x("FeSpin_BarringGear", bg, -0.345))
    pn = bmesh.new()                                                                      # its pinion (meshes on top)
    gear(pn, 0.035, 0.035, 8, (0, 0, 0), "Y", STEEL, tooth=0.02)
    cyl(pn, 0.01, 0.10, (0, -0.04, 0), "Y", STEEL, segs=8)
    objs.append(spinner_x("FeSpin_x3.7_Rev_BarringPinion", pn, -0.345, 0.0, C + 0.175))
    mb = bmesh.new()                                                                      # barring motor (static)
    cyl(mb, 0.045, 0.10, (-0.27, 0.0, C + 0.175), "X", PAINT, segs=14)
    box(mb, (0.06, 0.05, 0.03), (-0.27, 0.0, C + 0.23), CAST)
    objs.append(to_object(mb, "feSteamTurbine_BarringMotor", bevel=0.002))
    gv = bmesh.new()                                                                      # flyball governor
    cyl(gv, 0.008, 0.12, (0, -0.06, 0), "Y", STEEL, segs=8)
    cyl(gv, 0.02, 0.02, (0, -0.12, 0), "Y", BRASS, segs=10)
    for s_ in (-1, 1):
        beam(gv, (0, -0.12, 0), (s_ * 0.075, -0.06, 0), 0.007, 0.007, STEEL)
        beam(gv, (0, -0.02, 0), (s_ * 0.075, -0.06, 0), 0.006, 0.006, STEEL)
        cyl(gv, 0.024, 0.045, (s_ * 0.075, -0.06, 0), "Y", BRASS, segs=12)
    objs.append(to_object(gv, "FeSpin_x2_Governor", location=(0.40, -0.15, C + 0.24), rotation=AX_UP, bevel=0.001))
    # oil pump: an eccentric crank on the shaft drives the plunger (KineticSpinner slider-crank)
    ER, EL = 0.035, 0.22
    ck = bmesh.new()
    cyl(ck, 0.06, 0.03, (0, 0, 0), "Y", CAST, segs=18)
    cyl(ck, 0.012, 0.05, (0, 0, ER), "Y", STEEL, segs=8)
    objs.append(spinner_x("FeSpin_PumpCrank", ck, 0.33))
    pin = (0.33, 0.0, C + ER)
    ch = (0.33, 0.0, C + ER + EL)
    pl = bmesh.new()
    box(pl, (0.05, 0.04, 0.03), (0, 0, 0), BRASS)
    cyl(pl, 0.012, 0.12, (0, 0, 0.06), "Z", STEEL, segs=8)                                # plunger into the barrel
    objs.append(to_object(pl, "FeCrosshead_1", location=ch, bevel=0.001))
    crank_linkage(objs, 1, pin, ch, rod_w=0.016)
    objs.append(empty("FeFx_Steam_1", (0.32, 0, C + 0.06)))
    objs.append(empty("FeFx_Steam_2", (-0.36, 0, C + 0.06)))
    return objs


def model_boiler_firebox():
    """Boiler Firebox: a brick firebox in a riveted steel frame (right part of the block), cast front with double
    fire doors, draft vents, peephole and the glowing gap; a mechanical stoker on the left (hopper of coal, a screw
    in an open trough that turns while it burns); a forced-draft blower at the back (impeller turns while it burns),
    gas inlet in the middle of the back face; a heavy top plate the drum sits on."""
    objs = []
    BX, BY = -0.14, -0.09                                                                  # body centre
    b = bmesh.new()
    box(b, (0.98, 0.98, 0.05), (0, 0, 0.025), IRON)
    box(b, (0.66, 0.68, 0.86), (BX, BY, 0.48), BRICK)
    for x in (BX - 0.33, BX + 0.33):
        for y in (BY - 0.34, BY + 0.34):
            box(b, (0.06, 0.06, 0.92), (x, y, 0.49), IRON)                                # corner angles
    for z in (0.10, 0.50, 0.86):
        for s_ in (-1, 1):
            box(b, (0.70, 0.03, 0.05), (BX, BY + s_ * 0.345, z), RUST)                    # buckstays / bands
            box(b, (0.03, 0.72, 0.05), (BX + s_ * 0.335, BY, z), RUST)
        rivets(b, (BX - 0.30, BY - 0.37, z), (BX + 0.30, BY - 0.37, z), 8)
    box(b, (1.0, 1.0, 0.06), (0, 0, 0.95), CAST)                                          # top plate (drum seat)
    ring(b, 0.36, 0.30, 0.02, (0, 0, 0.985), "Z", IRON, segs=36)
    for x, y in ((0.45, 0.45), (0.45, -0.45), (-0.45, 0.45)):
        box(b, (0.06, 0.06, 0.88), (x, y, 0.48), IRON)                                    # posts under the plate
    # cast front: double doors with hinges, draft vents, peephole, glowing gap, ash pan drawer, shaker lever
    plate(b, (0.62, 0.05, 0.72), (BX, -0.455, 0.52), CAST, "-Y", n=6)
    box(b, (0.42, 0.02, 0.30), (BX, -0.482, 0.60), SOOT)
    for sx in (-1, 1):
        box(b, (0.20, 0.035, 0.28), (BX + sx * 0.106, -0.50, 0.60), IRON)                 # door leaves
        cyl(b, 0.042, 0.012, (BX + sx * 0.106, -0.52, 0.62), "Y", STEEL, segs=16)         # draft vent discs
        for k in range(4):
            box(b, (0.008, 0.014, 0.06), (BX + sx * 0.106 + (k - 1.5) * 0.017, -0.527, 0.62), SOOT)
        for z in (0.50, 0.70):
            cyl(b, 0.014, 0.05, (BX + sx * 0.205, -0.50, z), "Z", STEEL, segs=8)          # hinges
        box(b, (0.06, 0.03, 0.02), (BX + sx * 0.03, -0.525, 0.55), STEEL)                 # handles
    box(b, (0.38, 0.012, 0.02), (BX, -0.505, 0.455), GLOW)                                # glowing gap under the doors
    cyl(b, 0.025, 0.02, (BX, -0.52, 0.80), "Y", GLOW, segs=10)                            # peephole
    ring(b, 0.035, 0.025, 0.02, (BX, -0.52, 0.80), "Y", BRASS, segs=12)
    box(b, (0.50, 0.08, 0.14), (BX, -0.48, 0.22), IRON)                                   # ash pan drawer
    box(b, (0.16, 0.03, 0.02), (BX, -0.525, 0.22), STEEL)
    cyl(b, 0.02, 0.05, (0.15, -0.47, 0.30), "Y", STEEL, segs=8)                           # grate shaker lever
    beam(b, (0.15, -0.49, 0.30), (0.20, -0.49, 0.56), 0.02, 0.02, STEEL)
    cyl(b, 0.022, 0.06, (0.20, -0.49, 0.58), "Z", WOOD, segs=10)
    # mechanical stoker (left of the body, +X): hopper with coal, open trough into the body
    for w, z in ((0.22, 0.84), (0.17, 0.74), (0.12, 0.64)):
        box(b, (w * 0.9, w, 0.10), (0.36, -0.12, z), PAINT)
    box(b, (0.18, 0.20, 0.02), (0.36, -0.12, 0.895), SOOT)                                # coal on top
    box(b, (0.08, 0.08, 0.16), (0.36, -0.12, 0.52), IRON)                                 # hopper neck
    for s_ in (-1, 1):
        box(b, (0.30, 0.02, 0.10), (0.33, -0.12 + s_ * 0.07, 0.41), IRON)                 # trough walls
    box(b, (0.30, 0.16, 0.02), (0.33, -0.12, 0.36), IRON)
    box(b, (0.06, 0.18, 0.30), (0.46, -0.12, 0.20), IRON)                                 # stoker stand
    cyl(b, 0.04, 0.06, (0.47, -0.12, 0.41), "X", CAST, segs=12)                           # screw bearing / gear box
    objs.append(to_object(b, "feBoilerFirebox_Base", bevel=0.003))
    sc = bmesh.new()
    cyl(sc, 0.012, 0.26, (0, 0, 0), "Y", STEEL, segs=8)
    for k in range(14):
        box(sc, (0.10, 0.008, 0.02), (0, -0.12 + k * 0.018, 0), STEEL, Matrix.Rotation(k * 0.7, 4, "Y"))
    objs.append(to_object(sc, "FeWorkSpin_x0.6_Stoker", location=(0.33, -0.12, 0.42), rotation=(0, 0, -math.pi / 2), bevel=0.001))
    # forced-draft blower at the back (high), duct into the ash pit; gas inlet + cock in the middle of the back
    bl = bmesh.new()
    cyl(bl, 0.15, 0.10, (BX, 0.38, 0.72), "Y", PAINT, segs=24)                            # scroll housing
    ring(bl, 0.16, 0.14, 0.02, (BX, 0.435, 0.72), "Y", IRON, segs=24)
    for k in range(5):
        box(bl, (0.28, 0.01, 0.01), (BX, 0.445, 0.64 + k * 0.04), STEEL)                  # grille
    box(bl, (0.12, 0.10, 0.30), (BX, 0.32, 0.45), PAINT)                                  # duct down
    cyl(bl, 0.06, 0.12, (BX, 0.30, 0.92), "Y", CAST, segs=14)                             # motor
    cyl(bl, PIPE_R, 0.22, (0.0, 0.38, C), "Y", STEEL, segs=16)                            # gas inlet (back centre)
    flange(bl, (0.0, 0.485, C), "Y", IN)
    box(bl, (0.07, 0.07, 0.07), (0.0, 0.36, C + 0.07), BRASS)                             # gas cock
    beam(bl, (0.0, 0.36, C + 0.10), (0.10, 0.36, C + 0.12), 0.012, 0.012, RED)
    objs.append(to_object(bl, "feBoilerFirebox_Blower", bevel=0.002))
    im = bmesh.new()
    cyl(im, 0.03, 0.06, (0, 0, 0), "Y", STEEL, segs=10)
    for k in range(8):
        a_ = 2 * math.pi * k / 8
        box(im, (0.11, 0.05, 0.012), (0.065 * math.cos(a_), 0, 0.065 * math.sin(a_)), STEEL, Matrix.Rotation(-a_, 4, "Y"))
    objs.append(to_object(im, "FeWorkSpin_x6_Blower", location=(BX, 0.40, 0.72), bevel=0.001))
    objs.append(empty("FeFx_Fire_1", (BX, -0.44, 0.56)))
    objs.append(empty("FeFx_Smoke_1", (BX, -0.52, 0.76)))
    return objs


def model_boiler_drum():
    objs = []
    b = bmesh.new()
    box(b, (0.92, 0.92, 0.04), (0, 0, 0.02), IRON)
    for x in (-0.32, 0.32):                                                               # cast saddles + tie rod
        box(b, (0.10, 0.84, 0.10), (x, 0, 0.09), CAST)
        for sy in (-1, 1):
            beam(b, (x, sy * 0.40, 0.12), (x, sy * 0.28, 0.24), 0.08, 0.04, CAST)
    beam(b, (-0.32, 0.36, 0.10), (0.32, 0.36, 0.10), 0.016, 0.016, STEEL)
    # drum: steel dished ends meeting the next drum, wooden lagging with steel bands, riveted seams at the ends
    cyl(b, 0.40, 0.96, (0, 0, C), "X", STEEL, segs=40)
    for sx in (-1, 1):
        ring(b, 0.43, 0.30, 0.04, (sx * 0.48, 0, C), "X", CAST, segs=40)                  # end flange
        bolt_circle(b, 18, 0.39, (sx * 0.485, 0, C), "X", STEEL, r=0.01, d=0.05)
        ring(b, 0.30, 0.24, 0.042, (sx * 0.48, 0, C), "X", IN, segs=24)                   # water port
        rivet_ring_x(b, sx * 0.43, 0.405, 30)
    for k in range(30):                                                                   # lagging slats
        a_ = 2 * math.pi * k / 30
        box(b, (0.80, 0.075, 0.025), (0, 0.415 * math.cos(a_), C + 0.415 * math.sin(a_)), WOOD,
            Matrix.Rotation(a_ - math.pi / 2, 4, "X"))
    for x in (-0.30, 0.0, 0.30):
        ring(b, 0.44, 0.425, 0.035, (x, 0, C), "X", IRON, segs=40)                        # lagging bands
        box(b, (0.04, 0.03, 0.05), (x, 0.0, C - 0.44), STEEL)                             # band buckles
    # front: manhole with yoke, water gauge glass with cocks and guard rods, gauge with siphon, feed check valve
    cyl(b, 0.11, 0.04, (0.18, -0.43, C - 0.08), "Y", CAST, segs=24)                       # manhole cover
    box(b, (0.26, 0.03, 0.04), (0.18, -0.46, C - 0.08), STEEL)                            # yoke
    cyl(b, 0.015, 0.06, (0.18, -0.47, C - 0.08), "Y", STEEL, segs=8)
    LX, LY = -0.20, -0.47
    for z in (0.28, 0.76):
        box(b, (0.05, 0.06, 0.05), (LX, LY + 0.02, z), BRASS)                             # gauge cocks
        cyl(b, 0.008, 0.06, (LX + 0.04, LY + 0.02, z), "X", RED, segs=6)
    for k in range(4):
        a_ = 2 * math.pi * k / 4 + math.pi / 4
        cyl(b, 0.004, 0.46, (LX + 0.022 * math.cos(a_), LY - 0.01 + 0.022 * math.sin(a_), 0.52), "Z", STEEL, segs=6)
    cyl(b, 0.006, 0.10, (LX, LY + 0.02, 0.20), "Z", BRASS, segs=6)                        # drain cock
    ring(b, 0.03, 0.022, 0.012, (0.30, -0.45, 0.88), "Y", BRASS, segs=10)                 # gauge siphon loop
    pipe_run(b, [(0.30, -0.42, 0.80), (0.30, -0.45, 0.86)], r=0.006, mat=BRASS)
    for sy in (-1, 1):                                                                    # feed nozzles + check valves
        cyl(b, PIPE_R, 0.08, (-0.02, sy * 0.455, C), "Y", STEEL, segs=16)
        flange(b, (-0.02, sy * 0.485, C), "Y", IN)
        box(b, (0.10, 0.06, 0.10), (-0.02, sy * 0.43, C + 0.10), BRASS)                   # clack valve
        cyl(b, 0.025, 0.04, (-0.02, sy * 0.43, C + 0.17), "Z", BRASS, segs=10)
    # top: steam dome with the outlet, two pop safety valves, whistle with pull lever
    cyl(b, 0.16, 0.12, (0, 0, 0.92), "Z", STEEL, segs=28)
    cyl(b, 0.18, 0.025, (0, 0, 0.985), "Z", CAST, segs=28)
    bolt_circle(b, 12, 0.165, (0, 0, 0.995), "Z", STEEL, r=0.007, d=0.012)
    ring(b, 0.11, 0.08, 0.034, (0, 0, 0.985), "Z", OUT, segs=20)                          # steam outlet
    for x in (0.22, 0.32):
        cyl(b, 0.03, 0.10, (x, 0.14, 0.93), "Z", BRASS, segs=12)                          # pop valves
        cyl(b, 0.042, 0.03, (x, 0.14, 0.99), "Z", RED, segs=12)
    cyl(b, 0.015, 0.10, (-0.28, 0.12, 0.94), "Z", BRASS, segs=8)                          # whistle
    cyl(b, 0.03, 0.08, (-0.28, 0.12, 1.02), "Z", BRASS, segs=12, r2=0.024)
    beam(b, (-0.28, 0.12, 0.96), (-0.36, 0.12, 0.98), 0.01, 0.01, STEEL)
    # blowdown valve underneath
    pipe_run(b, [(0.10, 0.0, 0.10), (0.10, 0.0, 0.05), (0.10, -0.30, 0.05)], r=0.02)
    box(b, (0.06, 0.06, 0.06), (0.10, -0.30, 0.07), BRASS)
    beam(b, (0.10, -0.30, 0.10), (0.18, -0.36, 0.14), 0.012, 0.012, RED)
    # steam feed pump (donkey pump) at the back: cylinder, crosshead guide; the flywheel turns while it makes steam
    box(b, (0.12, 0.10, 0.24), (-0.32, 0.38, 0.20), CAST)
    cyl(b, 0.04, 0.10, (-0.32, 0.38, 0.37), "Z", BRASS, segs=12)
    pipe_run(b, [(-0.32, 0.38, 0.42), (-0.32, 0.30, 0.78)], r=0.01, mat=COPPER)
    gauge(objs, b, (0.30, -0.44, 0.76), "FeNeedle_Steam", r=0.07)
    objs.insert(0, to_object(b, "feBoilerDrum_Base", bevel=0.003))
    fw = bmesh.new()
    ring(fw, 0.08, 0.065, 0.025, (0, 0, 0), "Y", CAST, segs=22)
    cyl(fw, 0.015, 0.04, (0, 0, 0), "Y", STEEL, segs=10)
    for k in range(4):
        box(fw, (0.13, 0.012, 0.012), (0, 0, 0), CAST, Matrix.Rotation(k * math.pi / 4, 4, "Y"))
    objs.append(to_object(fw, "FeWorkSpin_x1.5_FeedPump", location=(-0.24, 0.40, 0.22), rotation=(0, 0, -math.pi / 2), bevel=0.001))
    col = bmesh.new()
    box(col, (0.016, 0.016, 0.44), (0, 0, -0.22), LIQUID)
    objs.append(to_object(col, "FeSurface_r0.42_Level", location=(LX, LY - 0.01, 0.31)))
    objs.append(empty("FeFx_Steam_1", (0.22, 0.14, 1.02)))
    return objs


PLANT_MODELS = {"feBoilerFirebox": model_boiler_firebox, "feBoilerDrum": model_boiler_drum,
                "feSteamTurbine": model_steam_turbine}



# ================================================================ item models (only for their inventory icon)
def model_turbine_rotor():
    """Turbine Rotor (item feTurbineRotor): the shaft with three bladed wheels growing toward the exhaust, journals
    and the coupling flange; the part that goes inside the Steam Turbine."""
    b = bmesh.new()
    cyl(b, 0.035, 0.90, (0, 0, 0.25), "X", STEEL, segs=16)                               # shaft
    for x in (-0.40, 0.36):
        cyl(b, 0.05, 0.06, (x, 0, 0.25), "X", BRASS, segs=16)                             # journals
    cyl(b, 0.09, 0.025, (-0.46, 0, 0.25), "X", CAST, segs=18)                             # coupling flange
    bolt_circle(b, 6, 0.065, (-0.475, 0, 0.25), "X", STEEL, r=0.008, d=0.012)
    for x, r, n in ((-0.16, 0.13, 20), (0.02, 0.17, 24), (0.20, 0.21, 28)):
        cyl(b, r * 0.62, 0.05, (x, 0, 0.25), "X", STEEL, segs=28)                         # disc
        cyl(b, 0.06, 0.07, (x, 0, 0.25), "X", CAST, segs=16)                              # hub
        for k in range(n):
            a_ = 2 * math.pi * k / n
            m = Matrix.Rotation(a_, 4, "X") @ Matrix.Rotation(0.5, 4, "Z")
            box(b, (0.045, 0.012, r * 0.42), (x, -r * 0.80 * math.sin(a_), 0.25 + r * 0.80 * math.cos(a_)), BRASS, m)
        ring(b, r + 0.005, r - 0.012, 0.05, (x, 0, 0.25), "X", STEEL, segs=36)            # shroud band
    return [to_object(b, "feTurbineRotor_Base", bevel=0.002)]


def model_fertilizer():
    """Fertilizer (item feFertilizer): a tied burlap sack with a heap of dark compost spilled in front."""
    b = bmesh.new()
    cyl(b, 0.20, 0.36, (0, 0.04, 0.18), "Z", LEATHER, segs=20, r2=0.15)                   # sack body
    cyl(b, 0.15, 0.08, (0, 0.04, 0.40), "Z", LEATHER, segs=16, r2=0.05)                   # neck
    ring(b, 0.06, 0.045, 0.025, (0, 0.04, 0.43), "Z", RUST, segs=12)                      # tie
    cyl(b, 0.07, 0.06, (0, 0.04, 0.48), "Z", LEATHER, segs=12, r2=0.10)                   # tuft
    box(b, (0.16, 0.012, 0.10), (0, -0.155, 0.22), PAINT)                                 # label patch
    for k in range(9):                                                                     # compost heap
        a_ = k * 0.7
        cyl(b, 0.05 + 0.01 * (k % 3), 0.03 + 0.01 * (k % 2), (0.10 * math.cos(a_) + 0.02, -0.20 + 0.05 * math.sin(a_), 0.02),
            "Z", SOOT, segs=10, r2=0.02)
    return [to_object(b, "feFertilizer_Base", bevel=0.002)]


ITEM_MODELS = {"feTurbineRotor": model_turbine_rotor, "feFertilizer": model_fertilizer}


# ================================================================ machine farming + big water wheel (2026-11-27)
def model_hydro_tower():
    """Hydroponic Tower (1 x 2 blocks): a red basin with water, a white grow column with planter cups on 4 levels,
    a rod cage with grow-light tubes (feHD_Glow: lit while it grows), a control box; water in at the back, the
    harvest out of the low chute in front, power wire on top. Each plant (FeGrow_*) grows from its cup with the
    progress of the run (FxVisual)."""
    objs = []
    b = bmesh.new()
    box(b, (0.90, 0.90, 0.04), (0, 0, 0.02), IRON)
    cyl(b, 0.40, 0.26, (0, 0, 0.17), "Z", RED, segs=36, r2=0.36)                         # basin
    ring(b, 0.42, 0.38, 0.03, (0, 0, 0.31), "Z", CAST, segs=36)
    cyl(b, 0.36, 0.01, (0, 0, 0.27), "Z", LIQUID, segs=32)                                # water in it
    cyl(b, 0.12, 1.56, (0, 0, 1.08), "Z", STEEL, segs=24)                                 # grow column
    for z in (0.60, 1.10, 1.60):
        cyl(b, 0.125, 0.02, (0, 0, z), "Z", IRON, segs=24)                                # column joints
    cyl(b, 0.14, 0.06, (0, 0, 1.88), "Z", CAST, segs=20)                                  # drip head
    pipe_run(b, [(0, 0.48, C), (0, 0.30, C), (0, 0.30, 0.30)], r=0.035)                   # water in (back)
    flange(b, (0, 0.485, C), "Y", IN)
    pipe_run(b, [(0.05, 0.10, 0.30), (0.05, 0.10, 1.80), (0.0, 0.0, 1.86)], r=0.014, mat=STEEL)   # riser to the top
    for k in range(6):                                                                    # rod cage
        a_ = 2 * math.pi * k / 6 + 0.3
        cyl(b, 0.012, 1.66, (0.38 * math.cos(a_), 0.38 * math.sin(a_), 1.13), "Z", IRON, segs=8)
    for z in (0.40, 0.95, 1.50, 1.95):
        ring(b, 0.395, 0.375, 0.015, (0, 0, z), "Z", IRON, segs=36)
    for a_ in (0.9, 3.0, 5.1):                                                            # grow lights
        x, y = 0.33 * math.cos(a_), 0.33 * math.sin(a_)
        cyl(b, 0.022, 1.30, (x, y, 1.12), "Z", GLOW, segs=10)
        for z in (0.46, 1.78):
            cyl(b, 0.03, 0.04, (x, y, z), "Z", STEEL, segs=10)
    box(b, (0.12, 0.06, 0.14), (0.26, -0.36, 1.20), SOOT)                                 # control box on a post
    cyl(b, 0.035, 0.02, (0.26, -0.395, 1.22), "Y", IN, segs=12)
    cyl(b, 0.01, 1.0, (0.26, -0.36, 0.75), "Z", STEEL, segs=6)
    low_chute(b)
    objs.append(to_object(b, "feHydroTower_Base", bevel=0.002))
    # planter cups + plants: 4 levels x 4 directions (staggered)
    pc = bmesh.new()
    n = 0
    for lv, z in enumerate((0.55, 0.95, 1.35, 1.72)):
        for k in range(4):
            a_ = k * math.pi / 2 + (lv % 2) * math.pi / 4
            cx, cy = 0.15 * math.cos(a_), 0.15 * math.sin(a_)
            cyl(pc, 0.045, 0.07, (cx, cy, z), "Z", STEEL, segs=12, r2=0.035)
            pl = bmesh.new()
            for j in range(6):                                                            # a rosette of leaves
                t = j * math.pi / 3 + 0.4 * lv
                m = Matrix.Rotation(t, 4, "Z") @ Matrix.Rotation(-(0.55 + 0.25 * (j % 2)), 4, "Y")   # leaves up and out
                box(pl, (0.16, 0.075, 0.006), tuple(m @ Vector((0.08, 0, 0))), LEAF, m)
            cyl(pl, 0.012, 0.06, (0, 0, -0.01), "Z", LEAF, segs=6)
            objs.append(to_object(pl, "FeGrow_%02d" % n, location=(cx + 0.03 * math.cos(a_), cy + 0.03 * math.sin(a_), z + 0.04),
                                  rotation=(0, 0.35 * math.cos(a_ + math.pi / 2) * 0, a_)))
            n += 1
    objs.append(to_object(pc, "feHydroTower_Cups", bevel=0.001))
    wire(objs, (0, 0, 1.92))
    return objs


def model_water_wheel():
    """Water Wheel, 3 x 3 blocks (MultiBlockDim 3,3,1; origin = the bottom middle cell): a timber wheel with two
    iron-banded rims, spokes, 16 paddles and an iron hub, on two timber trestles with bearings. The axle is the
    centre cell (1.5 m up) and comes out on both faces (couplings), turning with the wheel (FeSpin_Wheel)."""
    objs = []
    WZ = 1.5
    b = bmesh.new()
    for sy in (-1, 1):                                                                    # trestles
        y = sy * 0.44
        box(b, (2.6, 0.08, 0.10), (0, y, 0.05), WOOD)                                     # sill
        for sx in (-1, 1):
            beam(b, (sx * 1.05, y, 0.08), (sx * 0.10, y, WZ - 0.08), 0.10, 0.07, WOOD)    # legs
        beam(b, (-0.70, y, 0.55), (0.70, y, 0.55), 0.08, 0.06, WOOD)                     # brace
        for sx in (-1, 1):
            beam(b, (sx * 0.62, y, 0.58), (sx * 0.18, y, 1.10), 0.06, 0.05, WOOD)
        box(b, (0.26, 0.10, 0.18), (0, y, WZ - 0.12), CAST)                               # bearing block
        box(b, (0.22, 0.11, 0.06), (0, y, WZ + 0.10), IRON)                               # bearing cap
        for sx in (-1, 1):
            cyl(b, 0.012, 0.30, (sx * 0.09, y, WZ - 0.02), "Z", STEEL, segs=6)
        for x in (-1.0, 1.0):
            box(b, (0.14, 0.10, 0.03), (x, y, 0.015), RUST)                               # foot plates
    objs.append(to_object(b, "feWaterWheel_Base", bevel=0.003))
    w = bmesh.new()                                                                        # the wheel (built round Y)
    shaft_end(w, 0.0, -0.5)
    shaft_end(w, 0.0, 0.5)
    cyl(w, 0.20, 0.50, (0, 0, 0), "Y", CAST, segs=24)                                     # hub
    for sy in (-1, 1):
        bolt_circle(w, 8, 0.15, (0, sy * 0.255, 0), "Y", STEEL, r=0.014, d=0.02)
        ring(w, 1.42, 1.30, 0.07, (0, sy * 0.32, 0), "Y", WOOD, segs=48)                  # rims
        ring(w, 1.44, 1.41, 0.075, (0, sy * 0.32, 0), "Y", IRON, segs=48)                 # iron band
        for k in range(8):                                                                 # spokes
            a_ = 2 * math.pi * k / 8 + (0.2 if sy > 0 else 0.2)
            p0 = Vector((0.18 * math.cos(a_), sy * 0.24, 0.18 * math.sin(a_)))
            p1 = Vector((1.32 * math.cos(a_), sy * 0.32, 1.32 * math.sin(a_)))
            beam(w, tuple(p0), tuple(p1), 0.08, 0.06, WOOD)
    for k in range(16):                                                                    # paddles
        a_ = 2 * math.pi * k / 16
        m = Matrix.Rotation(-a_, 4, "Y")
        box(w, (0.30, 0.74, 0.04), (1.32 * math.cos(a_), 0, 1.32 * math.sin(a_)), WOOD, m)
        box(w, (0.05, 0.76, 0.05), (1.44 * math.cos(a_), 0, 1.44 * math.sin(a_)), IRON, m)   # strap at the tip
    objs.append(to_object(w, "FeSpin_Wheel", location=(0, 0, WZ), bevel=0.002))
    return objs


# ================================================================ D14: railways, giant machines, storage tank, station, trains
# (2026-11-27, PENDENCIAS_ASSETS.md). Axes: Blender (x, y, z) = game local (-x, -z, y): front (game +Z) = Blender -Y,
# game +X (right) = Blender -X. Units: 1 m = 1 block; origin = floor centre of the PARENT cell (the bottom middle cell
# of a multi-block).
#
# Extra contracts read by Art/UnityProject/Assets/Editor/FeBuild.cs:
#   FeCol_<n>_<sx>x<sy>x<sz>   empty: a box collider centred on it, size in cm along Blender x, y, z. When a model has
#                              any, they replace the single box round the whole model (rails must not reach into the
#                              cells beside them; the station has a walkable deck under its roof).
#   FeSignText_F / _B          empty: a TextMesh for the vanilla writable label (TEFeatureSignable), facing the front
#                              (game +Z) / the back.
# Moving parts: FeSpin_* (KineticSpinner: giant machines turn with the torque in their socket), FeRock_* (walking
# beam rocked by a crank, KineticSpinner), train wheels FeSpin_r<radius>_* and the locomotive's rods FeTrainPin_* /
# FeTrainCouple_* / FeTrainCross_* / FeTrainMain_* (TrainView), FeFx_Smoke / FeFx_Steam on the locomotive.
RAIL_TOP = 0.15                     # Rails.RailY
RAIL_C = 0.7425                     # rail centre lines: 1.435 m between the inner faces of the heads (head 0.05)
RAIL_PROFILE = [(-0.055, 0.0), (0.055, 0.0), (0.055, 0.010), (0.008, 0.020), (0.008, 0.056), (0.025, 0.060),
                (0.025, 0.082), (-0.025, 0.082), (-0.025, 0.060), (-0.008, 0.056), (-0.008, 0.020), (-0.055, 0.010)]
RAIL_BASE = RAIL_TOP - 0.082        # 0.068: foot of the rail on the tie plate
BALLAST_PROFILE = [(-1.42, 0.0), (1.42, 0.0), (1.24, 0.034), (-1.24, 0.034)]


def col_box(objs, n, centre, size):
    """A collider box (FeBuild): centre in Blender coordinates, size (x, y, z) in metres."""
    sx, sy, sz = (int(round(v * 100)) for v in size)
    objs.append(empty("FeCol_%d_%dx%dx%d" % (n, sx, sy, sz), tuple(centre), 0.2))


def sweep(bm, pts, profile, mat, closed=False, cap=True, up=Vector((0, 0, 1))):
    """Sweep a 2D profile (u = sideways, v = up) along a polyline of 3D points (the profile stays upright, tilting
    with the slope)."""
    pts = [Vector(p) for p in pts]
    rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        side = t.cross(up).normalized()
        upv = side.cross(t).normalized()
        rings.append([bm.verts.new(p + side * u + upv * v) for u, v in profile])
    n = len(profile)
    faces = []
    for i in range(len(rings) - 1):
        for j in range(n if closed or True else n - 1):
            jn = (j + 1) % n
            faces.append(bm.faces.new((rings[i][j], rings[i][jn], rings[i + 1][jn], rings[i + 1][j])))
    if cap:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat
    return faces


def offset_line(pts, d):
    """The polyline moved sideways by d (positive = to the right of the direction of travel, seen from above)."""
    pts = [Vector(p) for p in pts]
    out = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)])
        t.z = 0
        t.normalize()
        side = t.cross(Vector((0, 0, 1))).normalized()
        out.append(p + side * d)
    return out


def track_frame(p, t):
    """Matrix at p with its local Y along the track direction t, local X sideways, local Z up (tilted on slopes)."""
    t = Vector(t).normalized()
    side = t.cross(Vector((0, 0, 1))).normalized()
    upv = side.cross(t).normalized()
    m = Matrix((side, t, upv)).transposed().to_4x4()
    m.translation = Vector(p)
    return m


def sample(pts, s_list):
    """Points and tangents of a polyline at the given distances along it."""
    pts = [Vector(p) for p in pts]
    cum = [0.0]
    for a, b in zip(pts, pts[1:]):
        cum.append(cum[-1] + (b - a).length)
    out = []
    for s in s_list:
        i = 1
        while i < len(cum) - 1 and cum[i] < s:
            i += 1
        a, b = pts[i - 1], pts[i]
        f = 0.0 if cum[i] == cum[i - 1] else (s - cum[i - 1]) / (cum[i] - cum[i - 1])
        out.append((a.lerp(b, max(0.0, min(1.0, f))), (b - a).normalized()))
    return out, cum[-1]


def track(bm, centre, rails=True, sleepers=True, ballast=True, sleeper_len=2.5, skip=None, ballast_z=0.0,
          rail_from=(0, 0), bars=True):
    """A piece of track along `centre` (polyline at the FLOOR under the track, z = 0 or the slope). Sleepers every
    ~0.5 m (whole number per piece, so pieces in a row keep the spacing), tie plates and clips, two rails whose top
    is RAIL_TOP above the centre line, joint bars at both ends. skip(p) -> True leaves that sleeper out.
    rail_from = (index of the first point of the left rail, of the right rail) (switch blades)."""
    centre = [Vector(p) for p in centre]
    _, length = sample(centre, [0])
    if ballast:
        sweep(bm, [p + Vector((0, 0, ballast_z)) for p in centre], BALLAST_PROFILE, BALLAST)
    n = max(1, int(round(length / 0.5)))
    marks, _ = sample(centre, [(k + 0.5) * length / n for k in range(n)])
    for p, t in marks:
        if skip is not None and skip(p):
            continue
        m = track_frame(p, t)
        if sleepers:
            r = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)
            _fin(bm, WOOD, m @ Matrix.Translation((0, 0, 0.032)) @ Matrix.Diagonal((sleeper_len, 0.22, 0.056, 1)), r["verts"])
        for sx in (-1, 1):
            for mt, size, off in ((IRON, (0.30, 0.17, 0.008), (0, 0, 0.064)),
                                  (STEEL, (0.035, 0.05, 0.022), (-0.09, 0, 0.075)), (STEEL, (0.035, 0.05, 0.022), (0.09, 0, 0.075))):
                r = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)
                _fin(bm, mt, m @ Matrix.Translation((sx * RAIL_C + off[0], off[1], off[2])) @ Matrix.Diagonal((*size, 1)), r["verts"])
    if rails:
        for k, sx in enumerate((-1, 1)):
            line = offset_line(centre, sx * RAIL_C)[rail_from[k]:]
            if len(line) < 2:
                continue
            sweep(bm, [p + Vector((0, 0, RAIL_BASE)) for p in line], RAIL_PROFILE, STEEL)
            if bars:
                for end in (0, -1):
                    p, q = line[end], line[1] if end == 0 else line[-2]
                    t = (q - p).normalized() * (1 if end == 0 else -1)
                    m = track_frame(p, t if end == 0 else -t)
                    for side in (-1, 1):
                        r = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)
                        _fin(bm, IRON, m @ Matrix.Translation((side * 0.014, 0.10 * (1 if end == 0 else -1), RAIL_BASE + 0.038))
                             @ Matrix.Diagonal((0.008, 0.20, 0.032, 1)), r["verts"])
    return length


def arc_pts(cx, cy, r, a0, a1, n=48, z=0.0):
    return [Vector((cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
                    cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)), z)) for i in range(n + 1)]


def line_pts(a, b, n=4):
    a, b = Vector(a), Vector(b)
    return [a.lerp(b, i / n) for i in range(n + 1)]


def model_rail_straight():
    """Rail (1 x 1): south edge to north edge (Rails.cs "straight")."""
    objs = []
    b = bmesh.new()
    track(b, line_pts((0, 0.5, 0), (0, -0.5, 0), 2))
    objs.append(to_object(b, "feRailStraight_Track", bevel=0.002))
    col_box(objs, 1, (0, 0, 0.09), (1.0, 1.0, 0.18))
    return objs


def model_rail_curve():
    """Rail Curve (5 x 1 x 5): a quarter circle of radius 4.5 from the back edge of the game-left column to the
    game-right edge of the front row (Rails.cs "curve": centre (2.5, -2.5) game = (-2.5, 2.5) Blender)."""
    objs = []
    b = bmesh.new()
    track(b, arc_pts(-2.5, 2.5, 4.5, 0, -90, 64))
    objs.append(to_object(b, "feRailCurve_Track", bevel=0.002))
    col_box(objs, 1, (0, 0, 0.09), (5.0, 5.0, 0.18))
    return objs


def model_rail_ramp():
    """Rail Ramp (1 x 2 x 3): climbs one block over three, from the back (Blender +Y, floor) to the front (top of the
    next block). The track sits on a ballast bank held by timber walls."""
    objs = []
    b = bmesh.new()
    track(b, line_pts((0, 1.5, 0), (0, -1.5, 1.0), 6), ballast=False)
    # the bank: wedge of ballast under the slope, timber cribbing on both sides
    bk = bmesh.new()
    vs = []
    for y, z in ((1.5, 0.0), (-1.5, 1.0)):
        for x, zz in ((-1.42, 0.0), (1.42, 0.0), (1.24, z + 0.034), (-1.24, z + 0.034)):
            vs.append(bk.verts.new((x, y, zz if zz == 0.0 else zz)))
    # bottom stays on the floor; top follows the slope
    for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
        bk.faces.new([vs[i] for i in f]).material_index = BALLAST
    bm_join(b, bk)
    for sx in (-1, 1):
        for k in range(6):
            y0, y1 = 1.5 - k * 0.5, 1.0 - k * 0.5
            h = (k + 0.5) / 6.0
            box(b, (0.08, 0.50, max(0.04, h)), (sx * 1.40, (y0 + y1) / 2, max(0.04, h) / 2), WOOD)          # cribbing
            box(b, (0.10, 0.10, max(0.04, h) + 0.04), (sx * 1.44, y1 + 0.02, (max(0.04, h) + 0.04) / 2), WOOD)  # posts
    objs.append(to_object(b, "feRailRamp_Track", bevel=0.002))
    col_box(objs, 1, (0, 0, 0.6), (1.0, 3.0, 1.2))
    return objs


def bm_join(dst, src):
    """Copy the geometry of bmesh src into dst (materials kept), then free src."""
    me = bpy.data.meshes.new("_tmp")
    src.to_mesh(me)
    src.free()
    dst.from_mesh(me)
    bpy.data.meshes.remove(me)


def switch_stand(b, x, y, sx):
    """Hand switch stand beside the points: cast base on two long timbers, a throw lever, the target disc (red /
    green) and a lamp on top; a throw rod goes to the points."""
    box(b, (0.50, 0.30, 0.06), (x, y, 0.09), WOOD)
    box(b, (0.24, 0.20, 0.26), (x, y, 0.25), CAST)
    cyl(b, 0.035, 0.90, (x, y, 0.80), "Z", IRON, segs=10)
    cyl(b, 0.16, 0.02, (x, y + 0.02, 1.05), "Y", RED, segs=20)
    cyl(b, 0.16, 0.02, (x - sx * 0.02, y, 1.05), "X", IN, segs=20)
    box(b, (0.10, 0.10, 0.12), (x, y, 1.32), SOOT)
    cyl(b, 0.035, 0.03, (x, y - 0.05, 1.32), "Y", GLASS, segs=10)
    beam(b, (x + sx * 0.10, y, 0.40), (x + sx * 0.55, y, 0.62), 0.03, 0.03, IRON)        # lever
    cyl(b, 0.025, 0.08, (x + sx * 0.57, y, 0.63), "X", RED, segs=8)


def model_rail_switch(right=True):
    """Rail Switch (5 x 1 x 5): the straight of one column plus the curve (Rails.cs "switchR" / "switchL"). The
    curve's rails start where they leave the straight's (switch blades), long timbers carry both tracks while they
    are close, a frog plate where the rails cross, the hand switch stand beside the points."""
    objs = []
    b = bmesh.new()
    s = 1 if right else -1                      # right: straight on Blender +X (game left column), curve to Blender -X
    sx_straight = 2.0 * s
    straight = line_pts((sx_straight, 2.5, 0), (sx_straight, -2.5, 0), 10)
    if right:
        curve = arc_pts(-2.5, 2.5, 4.5, 0, -90, 64)
    else:
        curve = arc_pts(2.5, 2.5, 4.5, 180, 270, 64)

    def curve_x(y):
        dy = y - 2.5
        q = 4.5 * 4.5 - dy * dy
        return None if q < 0 else (-2.5 + math.sqrt(q)) if right else (2.5 - math.sqrt(q))

    # straight: long timbers while the curve is near (they reach under its rails)
    _, length = sample(straight, [0])
    for k in range(10):
        y = 2.5 - (k + 0.5) * 0.5
        cx = curve_x(y)
        if cx is not None and abs(cx - sx_straight) < 2.6:
            far = cx - s * 1.25
            near = sx_straight + s * 1.25
            box(b, (abs(near - far), 0.22, 0.056), ((near + far) / 2, y, 0.032), WOOD)
    track(b, straight, sleepers=False, ballast=True)
    for k in range(10):                                      # plates + clips of the straight's own short sleepers
        y = 2.5 - (k + 0.5) * 0.5
        cx = curve_x(y)
        if cx is not None and abs(cx - sx_straight) < 2.6:
            continue
        box(b, (2.5, 0.22, 0.056), (sx_straight, y, 0.032), WOOD)

    # curve: rails from where they are clear of the straight's (blades), sleepers only where the straight's do
    # not already carry them, ballast a hair lower (no z-fighting where the two beds overlap)
    starts = []
    for sxr in (-1, 1):
        line = offset_line(curve, sxr * RAIL_C)
        i = 0
        while i < len(line) - 2 and min(abs(line[i].x - (sx_straight + d)) for d in (-RAIL_C, RAIL_C)) < 0.07:
            i += 1
        starts.append(i)

    def near_straight(p):
        return abs(p.x - sx_straight) < 2.6 - 1.25 * 0 and abs(p.x - sx_straight) < 2.6

    track(b, curve, skip=near_straight, ballast_z=-0.004, rail_from=tuple(starts))
    # blades: the tapered start of the curve's rails, a slide chair under each
    for k, sxr in enumerate((-1, 1)):
        line = offset_line(curve, sxr * RAIL_C)
        p = line[starts[k]]
        box(b, (0.16, 0.30, 0.012), (p.x, p.y, RAIL_BASE - 0.004), IRON)
    # frog: where the curve's outer rail crosses the straight's inner rail
    outer = offset_line(curve, (-1 if right else 1) * RAIL_C)
    inner_x = sx_straight - s * RAIL_C
    for a_, b_ in zip(outer, outer[1:]):
        if (a_.x - inner_x) * (b_.x - inner_x) <= 0:
            f = (inner_x - a_.x) / (b_.x - a_.x) if b_.x != a_.x else 0
            p = a_.lerp(b_, f)
            box(b, (0.34, 0.90, 0.016), (p.x, p.y, RAIL_BASE - 0.006), CAST)
            for d in (-0.5, 0.5):
                box(b, (0.30, 0.06, 0.03), (p.x, p.y + d * 0.8, RAIL_BASE + 0.02), IRON)
            break
    # check rail beside the straight's outer rail at the frog, and the throw rod to the blades
    switch_stand(b, sx_straight - s * 1.65, 2.05, -s)
    beam(b, (sx_straight - s * 1.55, 2.05, 0.12), (sx_straight + s * 0.75, 2.05, 0.12), 0.03, 0.02, IRON)
    objs.append(to_object(b, "feRailSwitch%s_Track" % ("R" if right else "L"), bevel=0.002))
    col_box(objs, 1, (0, 0, 0.09), (5.0, 5.0, 0.18))
    return objs


# ---------------------------------------------------------------- shared structure helpers (giants, station)
def truss(b, base, top, z0, z1, levels, leg=0.12, brace=0.05, mat=IRON, open_faces=None):
    """A four-legged lattice tower: base / top = (half-width x, half-width y, centre x, centre y). Horizontal girts
    and X braces on every face at `levels` panels. open_faces = {face: (z_lo, z_hi)}: faces ("-Y", "+Y", "-X", "+X")
    left without braces and girts in that band (a walking beam or a pipe passes there)."""
    open_faces = open_faces or {}
    bx, by, bcx, bcy = base
    tx, ty, tcx, tcy = top

    def corner(sx, sy, z):
        f = (z - z0) / (z1 - z0)
        return Vector((bcx + (tcx - bcx) * f + sx * (bx + (tx - bx) * f), bcy + (tcy - bcy) * f + sy * (by + (ty - by) * f), z))
    for sx in (-1, 1):
        for sy in (-1, 1):
            beam(b, corner(sx, sy, z0), corner(sx, sy, z1), leg, leg, mat)
    faces = {"-Y": ((-1, -1), (1, -1)), "+Y": ((-1, 1), (1, 1)), "-X": ((-1, -1), (-1, 1)), "+X": ((1, -1), (1, 1))}
    for k in range(levels + 1):
        z = z0 + (z1 - z0) * k / levels
        for name, (c0, c1) in faces.items():
            if name in open_faces and open_faces[name][0] < z < open_faces[name][1]:
                continue
            beam(b, corner(*c0, z), corner(*c1, z), brace * 1.2, brace * 1.2, mat)
    for k in range(levels):
        za, zb = z0 + (z1 - z0) * k / levels, z0 + (z1 - z0) * (k + 1) / levels
        for name, (c0, c1) in faces.items():
            if name in open_faces and za < open_faces[name][1] and zb > open_faces[name][0]:
                continue
            beam(b, corner(*c0, za), corner(*c1, zb), brace, brace, mat)
            beam(b, corner(*c1, za), corner(*c0, zb), brace, brace, mat)


def railing(b, pts, h=1.0, post=1.1, mat=HAZ, closed=False):
    """Hand railing along a polyline: posts every ~`post` m, top and knee rails, toe board."""
    pts = [Vector(p) for p in pts] + ([Vector(pts[0])] if closed else [])
    for a, c in zip(pts, pts[1:]):
        d = c - a
        n = max(1, int(math.ceil(d.length / post)))
        for k in range(n + 1):
            p = a.lerp(c, k / n)
            cyl(b, 0.022, h, p + Vector((0, 0, h / 2)), "Z", mat, segs=8)
        for z, r in ((h, 0.022), (h * 0.5, 0.017)):
            beam(b, a + Vector((0, 0, z)), c + Vector((0, 0, z)), r * 2, r * 2, mat)
        beam(b, a + Vector((0, 0, 0.05)), c + Vector((0, 0, 0.05)), 0.012, 0.10, IRON)


def ladder(b, x, y, z0, z1, along="X", w=0.45, mat=IRON):
    """A steel ladder: two stiles, rungs every 0.3 m. along = the axis the rungs run along."""
    for s in (-1, 1):
        px, py = (x + s * w / 2, y) if along == "X" else (x, y + s * w / 2)
        box(b, (0.05, 0.05, z1 - z0), (px, py, (z0 + z1) / 2), mat)
    n = int((z1 - z0) / 0.3)
    for k in range(1, n + 1):
        z = z0 + k * (z1 - z0) / (n + 1)
        cyl(b, 0.014, w, (x, y, z), along, STEEL, segs=6)


def grating(b, x0, x1, y0, y1, z, mat=IRON, bars=0.12):
    """Floor grating: a dark deck, bearing bars and a frame (reads as a steel walkway)."""
    box(b, (x1 - x0, y1 - y0, 0.03), ((x0 + x1) / 2, (y0 + y1) / 2, z - 0.025), SOOT)
    n = max(2, int((x1 - x0) / bars))
    for k in range(n + 1):
        x = x0 + (x1 - x0) * k / n
        box(b, (0.012, y1 - y0, 0.04), (x, (y0 + y1) / 2, z - 0.01), mat)
    for x in (x0, x1):
        box(b, (0.06, y1 - y0, 0.08), (x, (y0 + y1) / 2, z - 0.03), mat)
    for y in (y0, y1):
        box(b, (x1 - x0, 0.06, 0.08), ((x0 + x1) / 2, y, z - 0.03), mat)


def i_beam(b, a, c, h=0.30, w=0.18, mat=IRON):
    """A horizontal I-beam from a to c (web vertical)."""
    a, c = Vector(a), Vector(c)
    d = c - a
    ang = math.atan2(d.y, d.x)
    m = Matrix.Rotation(ang, 4, "Z")
    mid = (a + c) / 2
    L = d.length
    box(b, (L, 0.02, h), mid, mat, m)
    for dz in (h / 2 - 0.01, -h / 2 + 0.01):
        box(b, (L, w, 0.02), mid + Vector((0, 0, dz)), mat, m)


def socket_coupling(b, y, z=C, x=0.0, sy=1):
    """Motor socket on the back face (PowerGate.SocketPos: the cell behind the middle of the back, bottom layer): a
    bearing pedestal, a yellow socket plate with bolts where the motor's shaft comes in."""
    box(b, (0.36, 0.30, z - 0.10), (x, y - sy * 0.18, (z - 0.10) / 2), CAST)
    cyl(b, 0.12, 0.22, (x, y - sy * 0.18, z), "Y", CAST, segs=20)
    for sx in (-1, 1):
        cyl(b, 0.02, 0.05, (x + sx * 0.14, y - sy * 0.18, z - 0.12), "Z", STEEL, segs=6)
    box(b, (0.50, 0.04, 0.50), (x, y - sy * 0.02, z), HAZ)
    for sx in (-1, 1):
        for sz in (-1, 1):
            cyl(b, 0.018, 0.03, (x + sx * 0.20, y, z + sz * 0.20), "Y", STEEL, segs=6)


# ---------------------------------------------------------------- Mining Rig (7 x 9 x 7)
def model_mining_rig():
    """Mining Rig (MultiBlockDim 7,9,7; origin = centre of the bottom layer). A drill rig over its own shaft: steel
    skid and substructure, a grated drill floor at 2.4 m with railings and a stair, a lattice derrick to 9 m with the
    crown block, the travelling block, the kelly and drill string turning in the rotary table (FeSpin), the
    drawworks drum, the doghouse cabin; the drive comes in at the back (motor socket, middle of the back face)
    through a gearbox and a chain case; a trommel screen under the floor turns the cuttings out onto a short belt
    that leaves by the middle of the front face at ground level (the products' exit)."""
    objs = []
    b = bmesh.new()
    H = 3.5
    FZ = 2.4
    for s in (-1, 1):
        i_beam(b, (-H + 0.1, s * (H - 0.15), 0.15), (H - 0.1, s * (H - 0.15), 0.15), h=0.30, w=0.20)
        i_beam(b, (s * (H - 0.15), -H + 0.1, 0.15), (s * (H - 0.15), H - 0.1, 0.15), h=0.30, w=0.20)
    for x in (-1.9, 1.9):
        i_beam(b, (x, -H + 0.2, 0.15), (x, H - 0.2, 0.15), h=0.28, w=0.18)
    for y in (-1.9, 1.9):
        i_beam(b, (-H + 0.2, y, 0.15), (H - 0.2, y, 0.15), h=0.28, w=0.18)
    hazard(b, 2 * H - 0.3, (0, -H + 0.04, 0.22), "X", h=0.10, n=22)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(b, (0.22, 0.22, FZ - 0.3), (sx * 2.1, sy * 2.1, 0.3 + (FZ - 0.3) / 2), IRON)
            box(b, (0.36, 0.36, 0.04), (sx * 2.1, sy * 2.1, 0.32), CAST)
    for sx in (-1, 1):
        beam(b, (sx * 2.1, -2.1, 0.45), (sx * 2.1, 2.1, FZ - 0.15), 0.08, 0.08, IRON)
        beam(b, (sx * 2.1, 2.1, 0.45), (sx * 2.1, -2.1, FZ - 0.15), 0.08, 0.08, IRON)
    beam(b, (-2.1, 2.1, 0.45), (2.1, 2.1, FZ - 0.15), 0.08, 0.08, IRON)
    beam(b, (2.1, 2.1, 0.45), (-2.1, 2.1, FZ - 0.15), 0.08, 0.08, IRON)
    grating(b, -2.3, 2.3, -2.3, -0.45, FZ)
    grating(b, -2.3, 2.3, 0.45, 2.3, FZ)
    grating(b, -2.3, -0.45, -0.45, 0.45, FZ)
    grating(b, 0.45, 2.3, -0.45, 0.45, FZ)
    railing(b, [(2.3, 1.45, FZ), (2.3, 2.3, FZ), (-2.3, 2.3, FZ), (-2.3, -2.3, FZ), (2.3, -2.3, FZ), (2.3, -1.0, FZ)])
    # stair on the Blender +X side: from the floor's gap in the railing down to the skid
    for k in range(9):
        z = FZ - (k + 1) * (FZ - 0.30) / 9
        box(b, (0.70, 0.26, 0.04), (2.75, 1.25 - k * 0.27, z), IRON)
    for sx in (2.40, 3.10):
        beam(b, (sx, 1.40, FZ), (sx, -1.20, 0.30), 0.04, 0.16, IRON)
        beam(b, (sx, 1.40, FZ + 0.95), (sx, -1.20, 1.25), 0.04, 0.04, HAZ)
    # wellhead / BOP stack under the rotary
    cyl(b, 0.42, 0.10, (0, 0, 0.35), "Z", CAST, segs=24)
    for z, r, h in ((0.65, 0.34, 0.50), (1.20, 0.38, 0.40), (1.70, 0.30, 0.45)):
        cyl(b, r, h, (0, 0, z), "Z", RED, segs=24)
        bolt_circle(b, 10, r + 0.02, (0, 0, z + h / 2), "Z", STEEL, r=0.016, d=0.03)
    for sx in (-1, 1):
        cyl(b, 0.07, 0.40, (sx * 0.55, 0, 1.20), "X", STEEL, segs=12)
        cyl(b, 0.12, 0.03, (sx * 0.76, 0, 1.20), "X", RED, segs=16)
    cyl(b, 0.18, FZ - 1.95, (0, 0, 1.95 + (FZ - 1.95) / 2), "Z", STEEL, segs=16)
    # derrick
    truss(b, (1.95, 1.95, 0, 0), (0.55, 0.55, 0, 0), FZ, 8.6, 6, leg=0.14, brace=0.055, open_faces={"-Y": (FZ, FZ + 2.2)})
    box(b, (1.4, 1.4, 0.10), (0, 0, 8.65), IRON)
    railing(b, [(-0.7, -0.7, 8.7), (0.7, -0.7, 8.7), (0.7, 0.7, 8.7), (-0.7, 0.7, 8.7)], h=0.25, post=0.7, closed=True)
    for sx in (-1, 1):
        box(b, (0.10, 0.9, 0.20), (sx * 0.30, 0, 8.78), CAST)
    grating(b, -1.45, -0.55, -0.6, 0.6, 5.7, bars=0.15)
    for k in range(6):
        y = -0.5 + k * 0.2
        beam(b, (-1.2, y, FZ + 0.05), (-1.05, y * 0.9, 5.9), 0.07, 0.07, STEEL)
    ladder(b, 1.45, -1.45, FZ, 8.5, along="X", w=0.40)
    # drawworks frame
    for sx in (-1, 1):
        box(b, (0.12, 0.9, 0.85), (sx * 0.95, 1.55, FZ + 0.43), PAINT)
    box(b, (2.0, 0.9, 0.08), (0, 1.55, FZ + 0.04), IRON)
    beam(b, (0.95, 1.20, FZ + 0.80), (1.40, 0.95, FZ + 1.30), 0.04, 0.04, STEEL)
    cyl(b, 0.012, 8.6 - (FZ + 0.85), (0.3, 1.27, (FZ + 0.85 + 8.6) / 2), "Z", STEEL, segs=6)
    # doghouse
    plate(b, (1.2, 1.6, 2.1), (-2.85, 1.2, FZ + 1.05), PAINT, "-X", n=4)
    box(b, (0.02, 0.6, 0.5), (-2.24, 1.0, FZ + 1.4), GLASS)
    box(b, (1.3, 1.7, 0.06), (-2.85, 1.2, FZ + 2.12), RUST)
    box(b, (0.02, 0.6, 1.6), (-2.24, 1.75, FZ + 0.8), SOOT)
    # gearbox + chain case (the drive from the motor socket up to the floor)
    box(b, (1.0, 0.9, 0.9), (0, 2.45, 0.75), CAST)
    for sx in (-1, 1):
        for z in (0.45, 1.05):
            box(b, (0.04, 0.92, 0.05), (sx * 0.52, 2.45, z), IRON)
    box(b, (0.30, 0.55, FZ - 1.2), (0.70, 2.10, 1.2 + (FZ - 1.2) / 2), PAINT)
    hazard(b, 0.5, (0.70, 1.82, 1.6), "Y", h=0.06, n=6)
    socket_coupling(b, H, C)
    # cuttings: chute to the trommel, trommel cradle, hopper, output belt to the front middle
    pipe_run(b, [(0, -0.2, 1.95), (0, -0.7, 1.75), (0, -0.95, 1.55)], r=0.10, mat=RUST, elbows=False)
    for y in (-1.0, -2.4):
        for sx in (-1, 1):
            box(b, (0.10, 0.10, 0.80), (sx * 0.55, y, 0.7), IRON)
            cyl(b, 0.08, 0.10, (sx * 0.42, y, 1.10), "Y", CAST, segs=12)
        box(b, (1.3, 0.20, 0.06), (0, y, 1.10), IRON)
    for sx in (-1, 1):
        box(b, (0.04, 0.9, 0.35), (sx * 0.42, -2.75, 0.75), RUST)
    box(b, (0.88, 0.04, 0.35), (0, -2.32, 0.75), RUST)
    for sx in (-1, 1):
        box(b, (0.06, 1.15, 0.12), (sx * 0.36, -2.92, 0.40), IRON)
        for y in (-2.5, -3.35):
            box(b, (0.05, 0.05, 0.36), (sx * 0.36, y, 0.18), IRON)
        box(b, (0.02, 1.0, 0.14), (sx * 0.34, -2.95, 0.55), IRON)
    box(b, (0.66, 1.10, 0.02), (0, -2.92, 0.47), SOOT)
    box(b, (0.70, 0.06, 0.05), (0, -3.46, 0.44), OUT)
    objs.append(to_object(b, "feMiningRig_Base", bevel=0.004))

    # --- moving parts (FeSpin_*: KineticSpinner, with the torque in the socket)
    k = bmesh.new()                                    # rotary table + kelly + drill string, built along local Y = up
    cyl(k, 0.38, 0.16, (0, 0, 0), "Y", CAST, segs=28)
    gear(k, 0.40, 0.06, 40, (0, -0.08, 0), "Y", STEEL, tooth=0.03)
    box(k, (0.36, 0.20, 0.36), (0, 0.16, 0), IRON)
    box(k, (0.14, 3.3, 0.14), (0, 1.75, 0), STEEL)
    cyl(k, 0.10, FZ - 2.0, (0, -(FZ - 2.0) / 2 - 0.08, 0), "Y", STEEL, segs=12)
    cyl(k, 0.16, 0.30, (0, 3.50, 0), "Y", CAST, segs=16)
    objs.append(to_object(k, "FeSpin_x0.5_Kelly", location=(0, 0, FZ + 0.08), rotation=(math.pi / 2, 0, 0), bevel=0.002))
    tb = bmesh.new()                                   # travelling block + hook over the swivel, lines to the crown
    box(tb, (0.36, 0.30, 0.80), (0, 0, 0.6), PAINT)
    for sx in (-1, 1):
        box(tb, (0.04, 0.32, 0.70), (sx * 0.20, 0, 0.6), HAZ)
    cyl(tb, 0.05, 0.35, (0, 0, 0.05), "Z", CAST, segs=12)
    top = 8.62 - (FZ + 3.9)
    for sx in (-0.12, -0.04, 0.04, 0.12):
        cyl(tb, 0.010, top - 1.0, (sx, 0, 1.0 + (top - 1.0) / 2), "Z", STEEL, segs=6)
    objs.append(to_object(tb, "feMiningRig_Block", location=(0, 0, FZ + 3.9), bevel=0.002))
    cr = bmesh.new()
    for x in (-0.18, -0.06, 0.06, 0.18):
        cyl(cr, 0.24, 0.07, (0, x, 0), "Y", STEEL, segs=24)
        ring(cr, 0.25, 0.20, 0.08, (0, x, 0), "Y", CAST, segs=24)
    cyl(cr, 0.04, 0.6, (0, 0, 0), "Y", STEEL, segs=10)
    objs.append(to_object(cr, "FeSpin_x2_Crown", location=(0, 0, 8.74), rotation=(0, 0, -math.pi / 2), bevel=0.002))
    dw = bmesh.new()
    cyl(dw, 0.32, 1.6, (0, 0, 0), "Y", CAST, segs=28)
    for y in (-0.80, 0.80):
        cyl(dw, 0.42, 0.06, (0, y, 0), "Y", STEEL, segs=28)
    for kk in range(12):
        cyl(dw, 0.335, 0.04, (0, -0.70 + kk * 0.125, 0), "Y", STEEL, segs=24)
    box(dw, (0.05, 1.5, 0.03), (0, 0, 0.345), RUST)
    objs.append(to_object(dw, "FeSpin_x1.5_Drum", location=(0, 1.55, FZ + 0.55), rotation=(0, 0, -math.pi / 2), bevel=0.002))
    sh = bmesh.new()
    cyl(sh, SHAFT_R, 0.7, (0, 0, 0), "Y", STEEL, segs=18)
    cyl(sh, FLANGE_R, 0.04, (0, 0.33, 0), "Y", CAST, segs=20)
    bolt_circle(sh, 4, 0.072, (0, 0.31, 0), "Y", STEEL, r=0.010, d=0.02)
    box(sh, (0.02, 0.4, 0.014), (0, 0, SHAFT_R + 0.004), RUST)
    objs.append(to_object(sh, "FeSpin_DriveShaft", location=(0, H - 0.36, C), bevel=0.002))
    fw = bmesh.new()
    gear(fw, 0.34, 0.06, 30, (0, 0, 0), "Y", STEEL, tooth=0.03)
    for kk in range(3):
        box(fw, (0.05, 0.05, 0.56), (0, 0, 0), IRON, Matrix.Rotation(kk * math.pi / 3, 4, "Y"))
    cyl(fw, 0.08, 0.12, (0, 0, 0), "Y", CAST, segs=14)
    objs.append(to_object(fw, "FeSpin_x0.8_Sprocket", location=(0.56, 2.45, 1.05), rotation=(0, 0, -math.pi / 2), bevel=0.002))
    tr = bmesh.new()
    ring(tr, 0.40, 0.36, 1.5, (0, 0, 0), "Y", IRON, segs=24)
    for kk in range(12):
        a_ = 2 * math.pi * kk / 12
        box(tr, (0.03, 1.5, 0.03), (0.40 * math.cos(a_), 0, 0.40 * math.sin(a_)), STEEL)
    for y in (-0.70, 0.70):
        ring(tr, 0.43, 0.38, 0.08, (0, y, 0), "Y", CAST, segs=24)
    for y in (-0.35, 0.0, 0.35):
        ring(tr, 0.41, 0.385, 0.03, (0, y, 0), "Y", RUST, segs=24)
    objs.append(to_object(tr, "FeSpin_x0.4_Trommel", location=(0, -1.70, 1.55), bevel=0.002))
    for n_, y in enumerate((-2.45, -3.40)):
        rl = bmesh.new()
        cyl(rl, 0.06, 0.66, (0, 0, 0), "Y", STEEL, segs=14)
        box(rl, (0.01, 0.6, 0.02), (0, 0, 0.06), RUST)
        objs.append(to_object(rl, "FeSpin_x3_Roller%d" % n_, location=(0, y, 0.42), rotation=(0, 0, -math.pi / 2)))
    return objs


def to_object_axis(bm, name, location, rotation, bevel=0.0):
    """to_object for a part whose spin / rock axis must be its local Y (KineticSpinner: Unity local +Z): the mesh is
    built in world-aligned coordinates around `location`, then turned back so the object can carry `rotation`."""
    R = mathutils_euler(rotation).to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=R.inverted(), verts=bm.verts)
    return to_object(bm, name, location=location, rotation=rotation, bevel=bevel)


def mathutils_euler(r):
    from mathutils import Euler
    return Euler(r, "XYZ")


ACROSS = (0, 0, -math.pi / 2)            # rotation that turns local Y onto Blender +X (an axle across the block)


# ---------------------------------------------------------------- Oil Extractor (5 x 11 x 5)
def model_oil_extractor():
    """Oil Extractor (MultiBlockDim 5,11,5). A beam pumpjack over the well with a workover derrick to 11 m: the
    walking beam (FeRock_1) rocks on the Samson post, driven by the crank and counterweights (FeSpin_x0.25_Crank) of
    the gear reducer through the pitman arms (FeRockRod_1); the horsehead lifts the polished rod (FeRockSlide_1) in
    and out of the stuffing box (KineticSpinner solves the linkage from the crank's angle). The drive comes in at the
    back (motor socket); the crude leaves by the High Pressure flange in the middle of the front face (0.5 m)."""
    objs = []
    b = bmesh.new()
    H = 2.5
    WY = -1.22                                         # the well
    PIV = Vector((0, 0.40, 3.78))                      # saddle bearing (beam pivot)
    CR = Vector((0, 1.85, 1.50))                       # crank axis
    R_ = 0.50                                          # crank radius
    END = Vector((0, 1.85, 3.66))                      # equalizer (pitman top)
    PIN = CR + Vector((0, R_, 0))                      # built pose: pin level, towards the back
    box(b, (2 * H, 2 * H, 0.15), (0, 0, 0.075), CONCRETE)
    for sx in (-1, 1):
        box(b, (0.08, 2 * H, 0.02), (sx * 2.44, 0, 0.16), HAZ)
    for sx in (-1, 1):                                 # pumpjack skid
        i_beam(b, (sx * 0.55, -0.35, 0.30), (sx * 0.55, 2.40, 0.30), h=0.30, w=0.20)
    for y in (-0.25, 0.9, 2.3):
        i_beam(b, (-0.65, y, 0.30), (0.65, y, 0.30), h=0.26, w=0.16)
    # Samson post (A-frame) + saddle bearing + ladder
    for sx in (-1, 1):
        for y0 in (-0.15, 0.95):
            beam(b, (sx * 0.55, y0, 0.45), (sx * 0.16, PIV.y, PIV.z - 0.15), 0.12, 0.10, PAINT)
        beam(b, (sx * 0.50, -0.05, 1.6), (sx * 0.50, 0.85, 1.6), 0.06, 0.06, PAINT)
        beam(b, (sx * 0.36, 0.05, 2.6), (sx * 0.36, 0.75, 2.6), 0.06, 0.06, PAINT)
    box(b, (0.40, 0.40, 0.16), (0, PIV.y, PIV.z - 0.10), CAST)
    for sx in (-1, 1):
        cyl(b, 0.10, 0.08, (sx * 0.20, PIV.y, PIV.z), "X", CAST, segs=16)
    ladder(b, 0, 1.05, 0.45, 3.4, along="X", w=0.36)
    # gear reducer round the crank axis, input from the socket
    box(b, (0.84, 0.95, 1.20), (0, CR.y, 0.30 + 0.60), PAINT)
    cyl(b, 0.48, 0.80, (0, CR.y, CR.z), "X", PAINT, segs=28)
    for sx in (-1, 1):
        cyl(b, 0.20, 0.10, (sx * 0.45, CR.y, CR.z), "X", CAST, segs=20)          # crank bearings
        cyl(b, 0.16, 0.08, (sx * 0.42, CR.y - 0.25, 0.75), "X", CAST, segs=16)   # intermediate shaft caps
    box(b, (0.86, 0.04, 0.06), (0, CR.y - 0.48, 1.30), IRON)
    hazard(b, 0.80, (0, CR.y - 0.48, 0.55), "X", h=0.08, n=8)
    socket_coupling(b, H, C)
    # guard fence round the crank
    railing(b, [(-1.15, 1.05, 0.30), (-1.15, 2.45, 0.30), (1.15, 2.45, 0.30), (1.15, 1.05, 0.30)], h=1.1, post=0.7, mat=HAZ)
    # wellhead: casing head, tee, master valves (red handwheels), stuffing box; flowline to the front flange
    cyl(b, 0.26, 0.30, (0, WY, 0.30), "Z", CAST, segs=24)
    bolt_circle(b, 8, 0.22, (0, WY, 0.46), "Z", STEEL, r=0.014, d=0.03)
    for z in (0.62, 0.98):
        cyl(b, 0.13, 0.24, (0, WY, z), "Z", STEEL, segs=18)
        cyl(b, 0.17, 0.04, (0, WY, z + 0.12), "Z", CAST, segs=18)
        cyl(b, 0.13, 0.03, (0.26, WY, z), "X", RED, segs=18)
        cyl(b, 0.02, 0.16, (0.18, WY, z), "X", STEEL, segs=6)
    cyl(b, 0.10, 0.24, (0, WY, 1.26), "Z", CAST, segs=16)                          # stuffing box
    cyl(b, 0.07, 0.40, (0, WY - 0.2, 0.80), "Y", STEEL, segs=14)                   # tee
    pipe_run(b, [(0, WY - 0.38, 0.80), (0, -1.85, 0.80), (0, -1.85, C), (0, -2.38, C)], r=0.07, mat=STEEL)
    cyl(b, 0.10, 0.14, (0, -2.22, C), "Y", CAST, segs=16)                          # check valve body
    flange(b, (0, -2.485, C), "Y", OUT, r=PIPE_R + 0.06, bolts=8)
    gauge(objs, b, (0.20, WY - 0.20, 1.10), "FeNeedle_Oil", r=0.06)
    # separator vessel on the game-right side (Blender -X) and its line from the tree
    for y in (-0.1, 1.5):
        box(b, (0.55, 0.14, 0.42), (-1.85, y, 0.36), IRON)
    cyl(b, 0.38, 2.0, (-1.85, 0.7, 0.86), "Y", PAINT, segs=28)
    for y in (-0.30, 1.70):
        cyl(b, 0.34, 0.06, (-1.85, y, 0.86), "Y", CAST, segs=24)
    for y in (0.1, 0.7, 1.3):
        cyl(b, 0.395, 0.03, (-1.85, y, 0.86), "Y", IRON, segs=28)
    pipe_run(b, [(-0.15, WY, 0.62), (-1.0, WY, 0.62), (-1.0, -0.6, 0.62), (-1.85, -0.6, 0.62), (-1.85, -0.6, 1.25),
                 (-1.85, 0.0, 1.25)], r=0.04, mat=STEEL)
    cyl(b, 0.05, 0.9, (-1.85, 1.45, 1.6), "Z", STEEL, segs=10)                     # gas vent
    cyl(b, 0.08, 0.10, (-1.85, 1.45, 2.08), "Z", SOOT, segs=12)
    # workover derrick over the well: lattice to 10.9 m, open where the beam and the flowline pass
    truss(b, (1.05, 1.10, 0, WY), (0.28, 0.30, 0, WY), 0.15, 10.40, 7, leg=0.12, brace=0.045,
          open_faces={"+Y": (2.6, 5.4), "-Y": (0.15, 1.2)})
    box(b, (0.80, 0.80, 0.10), (0, WY, 10.45), IRON)
    cyl(b, 0.20, 0.08, (0, WY, 10.68), "X", STEEL, segs=20)                        # crown sheave (static)
    for sx in (-1, 1):
        box(b, (0.06, 0.40, 0.18), (sx * 0.10, WY, 10.59), CAST)
    grating(b, -0.7, 0.7, WY - 0.75, WY - 0.30, 6.4, bars=0.14)                     # monkey board
    ladder(b, -0.20, WY - 0.26, 0.2, 10.35, along="X", w=0.30)
    cyl(b, 0.02, 0.2, (0.3, WY, 10.6), "Z", STEEL, segs=6)                         # aircraft lamp post
    cyl(b, 0.05, 0.08, (0.3, WY, 10.74), "Z", RED, segs=10)
    objs.append(to_object(b, "feOilExtractor_Base", bevel=0.004))

    # walking beam + horsehead + equalizer, pivot at the saddle; rocks about Blender X
    wb = bmesh.new()
    i_beam(wb, (0, -0.85 - PIV.y, 0.22), (0, 2.02 - PIV.y, 0.22), h=0.42, w=0.28)
    for y in (-0.6, 0.0, 0.6, 1.2):                                                # stiffeners
        box(wb, (0.26, 0.03, 0.38), (0, y, 0.22), IRON)
    ra = (Vector((0, WY, 3.78)) - PIV).length
    n = 14
    for k in range(n):                                                             # horsehead: curved plates
        a0 = math.radians(-34 + 70 * k / n)
        a1 = math.radians(-34 + 70 * (k + 1) / n)
        am = (a0 + a1) / 2
        p = Vector((0, -ra * math.cos(am), ra * math.sin(am)))
        box(wb, (0.36, 0.06, ra * (a1 - a0) + 0.01), p, PAINT, Matrix.Rotation(-am, 4, "X"))
        for sx in (-1, 1):
            q = Vector((sx * 0.17, -(ra - 0.25) * math.cos(am), (ra - 0.25) * math.sin(am)))
            box(wb, (0.02, 0.50, ra * (a1 - a0) + 0.02), q, PAINT, Matrix.Rotation(-am, 4, "X"))
    box(wb, (0.30, 0.5, 0.20), (0, -ra + 0.45, 0.22), PAINT)
    eq = END - PIV
    box(wb, (1.60, 0.20, 0.14), (0, eq.y, eq.z), CAST)                             # equalizer
    box(wb, (0.20, 0.30, 0.30), (0, eq.y, eq.z + 0.20), CAST)
    for sx in (-1, 1):
        cyl(wb, 0.07, 0.10, (sx * 0.75, eq.y, eq.z), "X", STEEL, segs=12)
    cyl(wb, 0.09, 0.44, (0, 0, 0), "X", STEEL, segs=16)                            # centre bearing pin
    objs.append(to_object_axis(wb, "FeRock_1", tuple(PIV), ACROSS, bevel=0.002))
    objs.append(empty("FeRockEnd_1", tuple(END), 0.05))
    objs.append(empty("FeRockHead_1", (0, WY, 3.78), 0.05))
    # crank, counterweights, crank pins (spins about Blender X: local Y)
    ck = bmesh.new()
    cyl(ck, 0.10, 1.70, (0, 0, 0), "X", STEEL, segs=18)
    for sx in (-1, 1):
        x = sx * 0.62
        beam(ck, (x, 0, 0), (x, R_ + 0.10, 0), 0.10, 0.22, CAST)                   # crank arm towards the pin
        for k in range(1, 9):
            a_ = math.radians(180 - 50 + 100 * (k - 0.5) / 8)
            box(ck, (0.12, 0.20, 0.30), (x, 0.46 * math.cos(a_), 0.46 * math.sin(a_)), CAST, Matrix.Rotation(a_, 4, "X"))
        box(ck, (0.13, 0.12, 0.62), (x, -0.50, 0.0), IRON)                          # weight clamp bar
        cyl(ck, 0.06, 0.24, (sx * 0.73, R_, 0), "X", STEEL, segs=12)                # crank pin
        cyl(ck, 0.09, 0.06, (sx * 0.68, R_, 0), "X", CAST, segs=12)
    objs.append(to_object_axis(ck, "FeSpin_x0.25_Crank", tuple(CR), ACROSS, bevel=0.002))
    objs.append(empty("FeRockPin_1", tuple(PIN), 0.05))
    # pitman arms: pivot at the crank pin, towards the equalizer
    pm = bmesh.new()
    d = END - PIN
    for sx in (-1, 1):
        beam(pm, (sx * 0.80, 0, 0), (sx * 0.80, d.y, d.z), 0.07, 0.10, PAINT)
        cyl(pm, 0.09, 0.12, (sx * 0.80, 0, 0), "X", CAST, segs=14)
        cyl(pm, 0.08, 0.12, (sx * 0.80, d.y, d.z), "X", CAST, segs=14)
    objs.append(to_object(pm, "FeRockRod_1", location=tuple(PIN), bevel=0.002))
    # polished rod, carrier bar, bridle (moves up and down with the horsehead)
    pr = bmesh.new()
    cyl(pr, 0.025, 2.15, (0, 0, 0.6 + 2.15 / 2), "Z", STEEL, segs=10)
    box(pr, (0.40, 0.10, 0.06), (0, 0, 2.75), CAST)
    cyl(pr, 0.05, 0.10, (0, 0, 2.83), "Z", STEEL, segs=10)                         # rod clamp
    for sx in (-1, 1):
        cyl(pr, 0.012, 3.95 - 2.75, (sx * 0.17, 0.02, (3.95 + 2.75) / 2), "Z", STEEL, segs=6)
    objs.append(to_object(pr, "FeRockSlide_1", location=(0, WY - 0.0, 0), bevel=0.001))
    # input shaft from the socket into the reducer
    sh = bmesh.new()
    cyl(sh, SHAFT_R, 0.30, (0, 0, 0), "Y", STEEL, segs=18)
    cyl(sh, FLANGE_R, 0.04, (0, 0.13, 0), "Y", CAST, segs=20)
    bolt_circle(sh, 4, 0.072, (0, 0.11, 0), "Y", STEEL, r=0.010, d=0.02)
    box(sh, (0.02, 0.2, 0.014), (0, 0, SHAFT_R + 0.004), RUST)
    objs.append(to_object(sh, "FeSpin_DriveShaft", location=(0, H - 0.18, C), bevel=0.002))
    return objs


# ---------------------------------------------------------------- Storage Tank (5 x 6 x 5)
def model_storage_tank():
    """Storage Tank (MultiBlockDim 5,6,5): a welded vertical tank on a concrete ring, cone roof with a handrail, a
    spiral stair round it, a nozzle with a flange in the middle of every side of the bottom layer (pipes connect
    there), a manway, a float gauge on a scale board (FeSurface_r4.60_Float rises with the level, FxVisual Tank) and
    a level dial (FeNeedle_Level)."""
    objs = []
    b = bmesh.new()
    R0 = 2.0
    Z0, Z1 = 0.22, 5.00
    cyl(b, 2.30, 0.22, (0, 0, 0.11), "Z", CONCRETE, segs=48)
    cyl(b, R0, Z1 - Z0, (0, 0, (Z0 + Z1) / 2), "Z", PAINT, segs=56)
    for z in (Z0 + 0.03, 1.18, 2.14, 3.10, 4.06, Z1 - 0.03):                       # course welds
        cyl(b, R0 + 0.008, 0.025, (0, 0, z), "Z", IRON, segs=56)
    for k in range(5):                                                             # staggered vertical seams
        za, zb = 0.25 + k * 0.95, 0.25 + (k + 1) * 0.95
        for j in range(3):
            a_ = 2 * math.pi * (j / 3 + (k % 2) / 6)
            box(b, (0.02, 0.02, zb - za), ((R0 + 0.006) * math.cos(a_), (R0 + 0.006) * math.sin(a_), (za + zb) / 2), IRON)
    # roof
    cyl(b, R0 + 0.06, 0.05, (0, 0, Z1 + 0.02), "Z", IRON, segs=56)
    cyl(b, R0 + 0.03, 0.45, (0, 0, Z1 + 0.25), "Z", RUST, segs=56, r2=0.25)
    cyl(b, 0.30, 0.18, (0, 0, Z1 + 0.55), "Z", CAST, segs=20)                       # roof vent
    cyl(b, 0.36, 0.05, (0, 0, Z1 + 0.66), "Z", IRON, segs=20)
    pts = [((R0 - 0.08) * math.cos(2 * math.pi * k / 20), (R0 - 0.08) * math.sin(2 * math.pi * k / 20), Z1 + 0.05) for k in range(20)]
    railing(b, pts, h=0.62, post=0.8, mat=HAZ, closed=True)
    # spiral stair: 22 treads from the ground (angle A0) up to the roof
    A0, SPAN, N = 300.0, 205.0, 22
    for k in range(N):
        a_ = math.radians(A0 + SPAN * (k + 0.5) / N)
        z = Z0 + (Z1 + 0.05 - Z0) * (k + 1) / N
        m = Matrix.Rotation(a_, 4, "Z")
        box(b, (0.40, 0.24, 0.04), m @ Vector((R0 + 0.22, 0, z)), IRON, m)
        if k % 2 == 0:
            beam(b, m @ Vector((R0 + 0.40, 0, z)), m @ Vector((R0 + 0.40, 0, z + 0.90)), 0.04, 0.04, HAZ)
            beam(b, m @ Vector((R0 + 0.04, 0, z - 0.02)), m @ Vector((R0 + 0.04, 0, z - 0.30)), 0.05, 0.05, IRON)
    for r in (R0 + 0.42,):
        hp = []
        for k in range(N + 1):
            a_ = math.radians(A0 + SPAN * k / N)
            z = Z0 + (Z1 + 0.05 - Z0) * k / N + 0.90
            hp.append(Vector((r * math.cos(a_), r * math.sin(a_), z)))
        for p, q in zip(hp, hp[1:]):
            beam(b, p, q, 0.04, 0.04, HAZ)
    # nozzles: middle of every side, bottom layer (pipe ports), with a valve
    for ax, sg in (("X", 1), ("X", -1), ("Y", 1), ("Y", -1)):
        v = Vector((sg, 0, 0)) if ax == "X" else Vector((0, sg, 0))
        cyl(b, PIPE_R, 0.50, v * (R0 + 0.24) + Vector((0, 0, C)), ax, STEEL, segs=16)
        cyl(b, 0.12, 0.14, v * (R0 + 0.22) + Vector((0, 0, C)), ax, CAST, segs=16)
        cyl(b, 0.012, 0.16, v * (R0 + 0.22) + Vector((0, 0, C + 0.16)), "Z", STEEL, segs=6)
        cyl(b, 0.09, 0.02, v * (R0 + 0.22) + Vector((0, 0, C + 0.25)), "Z", RED, segs=14)
        flange(b, tuple(v * 2.485 + Vector((0, 0, C))), ax, IN)
    # manway (front-right), placards
    m = Matrix.Rotation(math.radians(240), 4, "Z")
    cyl(b, 0.34, 0.10, m @ Vector((R0 + 0.04, 0, 0.95)), "X", CAST, segs=24, rot=m)
    for k in range(12):
        a_ = 2 * math.pi * k / 12
        p = m @ Vector((R0 + 0.10, 0.30 * math.cos(a_), 0.95 + 0.30 * math.sin(a_)))
        cyl(b, 0.015, 0.04, p, "X", STEEL, segs=6, rot=m)
    for a_deg in (165.0, 215.0):
        mm = Matrix.Rotation(math.radians(a_deg), 4, "Z")
        box(b, (0.02, 0.40, 0.40), mm @ Vector((R0 + 0.01, 0, 2.0)), HAZ, mm @ Matrix.Rotation(math.pi / 4, 4, "X"))
        box(b, (0.022, 0.30, 0.30), mm @ Vector((R0 + 0.012, 0, 2.0)), RED, mm @ Matrix.Rotation(math.pi / 4, 4, "X"))
    # float gauge (side away from the stair): a scale board, two guide wires, the float pointer rising with the level
    AG = math.radians(195)
    mg = Matrix.Rotation(AG, 4, "Z")
    box(b, (0.03, 0.22, 4.7), mg @ Vector((R0 + 0.06, 0, 0.30 + 2.35)), SOOT, mg)
    for k in range(11):
        z = 0.42 + k * 0.46
        box(b, (0.01, 0.10 if k % 5 else 0.18, 0.02), mg @ Vector((R0 + 0.08, 0, z)), HAZ, mg)
    for sy in (-1, 1):
        cyl(b, 0.006, 4.7, mg @ Vector((R0 + 0.10, sy * 0.14, 0.30 + 2.35)), "Z", STEEL, segs=6)
    box(b, (0.25, 0.30, 0.20), mg @ Vector((R0 + 0.05, 0, Z1 + 0.15)), CAST, mg)
    fl = bmesh.new()
    box(fl, (0.06, 0.30, 0.07), (0, 0, 0), RED)
    box(fl, (0.04, 0.06, 0.14), (0.02, 0.13, 0), HAZ)
    objs.append(to_object(fl, "FeSurface_r4.60_Float", location=tuple(mg @ Vector((R0 + 0.13, 0, 0.42))), rotation=(0, 0, AG)))
    # level dial on the front, on a bracket (the stair passes well above it)
    GXd = 0.45
    GYd = -(math.sqrt(R0 * R0 - GXd * GXd))
    box(b, (0.26, 0.14, 0.26), (GXd, GYd - 0.05, 1.10), IRON)
    gauge(objs, b, (GXd, GYd - 0.14, 1.10), "FeNeedle_Level", r=0.10)
    objs.append(to_object(b, "feStorageTank_Base", bevel=0.004))
    return objs


# ---------------------------------------------------------------- Train Station (9 x 4 x 3)
def model_train_station():
    """Train Station (MultiBlockDim 9,4,3: 9 along the rails, which run outside its FRONT face = Blender -Y). A brick-
    faced concrete platform one block high with a yellow edge line and steps at both ends; a canopy on cast-iron
    columns with a wooden valance; the station office (storage) with a door and windows, crates, the coal bunker
    (fuel store), a small tank on saddles with its fill pipe to the back face, benches, lamps, a clock; the name
    board hangs under the canopy with a TextMesh on each side (FeSignText_F / _B: the vanilla label). Colliders
    (FeCol_*): the deck, the steps, the office, the bunker, the tank and the roof, so players walk on the platform."""
    objs = []
    b = bmesh.new()
    X, Y = 4.5, 1.5
    D = 1.0                                              # deck height
    PX = 3.5                                             # deck ends; steps beyond
    box(b, (2 * PX, 2 * Y, D - 0.08), (0, 0, (D - 0.08) / 2), CONCRETE)
    box(b, (2 * PX + 0.02, 2 * Y + 0.02, 0.08), (0, 0, D - 0.04), CONCRETE)              # deck slab
    for k in range(int(2 * PX / 0.6)):                                                  # brick facing on the rail side
        x = -PX + 0.3 + k * 0.6
        box(b, (0.58, 0.04, D - 0.14), (x, -Y - 0.01, (D - 0.14) / 2 + 0.02), BRICK)
    box(b, (2 * PX + 0.04, 0.30, 0.05), (0, -Y + 0.13, D + 0.005), CONCRETE)             # coping
    box(b, (2 * PX, 0.10, 0.006), (0, -Y + 0.45, D + 0.004), HAZ)                        # keep-back line
    for k in range(int(2 * PX / 0.5)):                                                   # deck joints
        box(b, (0.012, 2 * Y - 0.1, 0.004), (-PX + 0.5 * (k + 1), 0.05, D + 0.003), SOOT)
    for sx in (-1, 1):                                                                   # steps down at both ends
        for k, h in enumerate((0.75, 0.5, 0.25)):
            x = sx * (PX + 0.167 + k * 0.333)
            box(b, (0.333, 2 * Y - 0.1, h), (x, 0.05, h / 2), CONCRETE)
            box(b, (0.333, 0.10, 0.01), (x, -Y + 0.15, h + 0.005), HAZ)
    # canopy: columns at the back, cantilever brackets, roof sheets, valance
    ZR = 3.55
    for x in (-3.9, -1.3, 1.3, 3.9):
        z0 = D if abs(x) < PX else 0.0
        cyl(b, 0.07, ZR - z0, (x, 1.15, z0 + (ZR - z0) / 2), "Z", CAST, segs=12)
        cyl(b, 0.13, 0.12, (x, 1.15, z0 + 0.06), "Z", CAST, segs=12)
        cyl(b, 0.10, 0.08, (x, 1.15, ZR - 0.25), "Z", CAST, segs=12)
        beam(b, (x, 1.25, ZR + 0.05), (x, -1.55, ZR - 0.10), 0.08, 0.16, IRON)          # roof beam
        beam(b, (x, 1.15, ZR - 0.70), (x, -0.30, ZR - 0.03), 0.05, 0.05, IRON)          # bracket strut
        for k in range(3):
            cyl(b, 0.12 - k * 0.03, 0.012, (x, 0.75 - k * 0.35, ZR - 0.30 + k * 0.12), "X", IRON, segs=12)
    for k in range(18):                                                                  # corrugated sheets
        x = -X + 0.25 + k * 0.5
        rot = Matrix.Rotation(math.atan2(-0.15, 2.8), 4, "X")
        box(b, (0.52, 2.95, 0.03), (x, -0.15, ZR + 0.02 - 0.0), RUST, rot)
        for j in range(4):
            box(b, (0.03, 2.95, 0.03), (x - 0.19 + j * 0.125, -0.15, ZR + 0.045), RUST, rot)
    box(b, (2 * X, 0.05, 0.12), (0, 1.40, ZR + 0.10), IRON)                              # gutter (back)
    for k in range(36):                                                                  # valance boards (front)
        x = -X + 0.125 + k * 0.25
        box(b, (0.22, 0.03, 0.34), (x, -1.62, ZR - 0.25), WOOD)
        box(b, (0.08, 0.031, 0.08), (x, -1.62, ZR - 0.45), WOOD, Matrix.Rotation(math.pi / 4, 4, "Y"))
    box(b, (2 * X, 0.06, 0.06), (0, -1.60, ZR - 0.06), PAINT)
    # station office (the storage), back left: brick walls, door, windows, sign plate
    OX0, OX1, OY0, OY1 = -3.40, -0.90, 0.05, 1.40
    ZT = 3.15
    for (x0, x1, y0, y1) in ((OX0, OX1, OY1 - 0.12, OY1), (OX0, OX0 + 0.12, OY0, OY1), (OX1 - 0.12, OX1, OY0, OY1)):
        box(b, (x1 - x0, y1 - y0, ZT - D), ((x0 + x1) / 2, (y0 + y1) / 2, D + (ZT - D) / 2), BRICK)
    # front wall with a door and a window
    box(b, (0.55, 0.12, ZT - D), (OX0 + 0.275, OY0 + 0.06, D + (ZT - D) / 2), BRICK)
    box(b, (0.55, 0.12, ZT - D), (OX1 - 0.275, OY0 + 0.06, D + (ZT - D) / 2), BRICK)
    box(b, (OX1 - OX0 - 1.1, 0.12, 0.85), ((OX0 + OX1) / 2, OY0 + 0.06, D + 0.425), BRICK)
    box(b, (OX1 - OX0 - 1.1, 0.12, 0.45), ((OX0 + OX1) / 2, OY0 + 0.06, ZT - 0.225), BRICK)
    box(b, (OX1 - OX0 - 1.1, 0.03, ZT - D - 1.30), ((OX0 + OX1) / 2, OY0 + 0.07, D + 0.85 + (ZT - D - 1.30) / 2), GLASS)
    for k in range(3):
        box(b, (0.03, 0.05, ZT - D - 1.30), (OX0 + 0.55 + (k + 1) * (OX1 - OX0 - 1.1) / 4, OY0 + 0.04, D + 0.85 + (ZT - D - 1.30) / 2), WOOD)
    box(b, (OX1 - OX0 - 1.0, 0.16, 0.05), ((OX0 + OX1) / 2, OY0 - 0.02, D + 0.84), CONCRETE)   # sill
    box(b, (0.40, 0.04, 1.95), (OX0 + 0.33, OY0 + 0.0, D + 0.975), WOOD)               # door leaf (shut)
    box(b, (0.04, 0.05, 0.05), (OX0 + 0.47, OY0 - 0.03, D + 1.0), BRASS)
    box(b, (OX1 - OX0 + 0.10, OY1 - OY0 + 0.10, 0.08), ((OX0 + OX1) / 2, (OY0 + OY1) / 2, ZT + 0.04), CONCRETE)
    box(b, (0.80, 0.03, 0.22), ((OX0 + OX1) / 2 + 0.3, OY0 - 0.02, ZT - 0.18), PAINT)       # "OFFICE" plate
    # crates (storage), coal bunker (fuel), small tank on saddles (fluid)
    for (x, y, z, s) in ((-0.55, 1.05, D, 0.55), (0.05, 1.10, D, 0.50), (-0.30, 1.10, D + 0.55, 0.45)):
        plate(b, (s, s, s), (x, y, z + s / 2), WOOD, "-Y", n=3)
        for zz in (z + 0.06, z + s - 0.06):
            box(b, (s + 0.01, s + 0.01, 0.03), (x, y, zz), IRON)
    BX0, BX1 = 0.45, 1.85
    for (x0, x1, y0, y1) in ((BX0, BX1, 1.30, 1.38), (BX0, BX0 + 0.08, 0.35, 1.38), (BX1 - 0.08, BX1, 0.35, 1.38)):
        box(b, (x1 - x0, y1 - y0, 0.90), ((x0 + x1) / 2, (y0 + y1) / 2, D + 0.45), WOOD)
    box(b, (BX1 - BX0, 0.08, 0.55), ((BX0 + BX1) / 2, 0.39, D + 0.275), WOOD)
    for x in (BX0, BX1):
        for y in (0.35, 1.38):
            box(b, (0.08, 0.08, 0.95), (x, y, D + 0.475), IRON)
    cyl(b, 0.62, 0.5, ((BX0 + BX1) / 2, 0.88, D + 0.48), "Z", SOOT, segs=10, r2=0.15)  # coal heap
    box(b, (BX1 - BX0 - 0.16, 0.9, 0.30), ((BX0 + BX1) / 2, 0.88, D + 0.25), SOOT)
    box(b, (0.6, 0.03, 0.18), ((BX0 + BX1) / 2, 0.34, D + 0.40), HAZ)                    # "FUEL" plate
    TX = 2.75
    for x in (TX - 0.55, TX + 0.55):
        box(b, (0.14, 0.75, 0.28), (x, 0.95, D + 0.14), CAST)
    cyl(b, 0.40, 1.5, (TX, 0.95, D + 0.62), "X", PAINT, segs=28)
    for x in (TX - 0.75, TX + 0.75):
        cyl(b, 0.36, 0.06, (x, 0.95, D + 0.62), "X", CAST, segs=24)
    for x in (TX - 0.35, TX + 0.35):
        cyl(b, 0.405, 0.04, (x, 0.95, D + 0.62), "X", IRON, segs=28)
    cyl(b, 0.08, 0.10, (TX, 0.95, D + 1.05), "Z", CAST, segs=12)                        # filler cap
    pipe_run(b, [(TX + 0.75, 0.95, D + 0.45), (TX + 0.95, 0.95, D + 0.45), (TX + 0.95, 1.40, D + 0.45),
                 (TX + 0.95, 1.40, C), (TX + 0.95, 1.49, C)], r=0.035)
    flange(b, (TX + 0.95, 1.485, C), "Y", IN)
    # benches facing the rails, lamps under the canopy, a clock on a bracket
    for x in (-1.9, 3.1):
        for sx in (-1, 1):
            box(b, (0.05, 0.40, 0.42), (x + sx * 0.55, -0.15, D + 0.21), CAST)
        for k in range(3):
            box(b, (1.25, 0.10, 0.03), (x, -0.30 + k * 0.12, D + 0.44), WOOD)
        for k in range(2):
            box(b, (1.25, 0.03, 0.09), (x, -0.02, D + 0.62 + k * 0.13), WOOD)
    for x in (-2.6, 0.0, 2.6):
        cyl(b, 0.008, 0.45, (x, -0.55, ZR - 0.27), "Z", STEEL, segs=6)
        cyl(b, 0.12, 0.10, (x, -0.55, ZR - 0.52), "Z", PAINT, segs=12, r2=0.03)
        cyl(b, 0.06, 0.08, (x, -0.55, ZR - 0.60), "Z", GLASS, segs=10)
    box(b, (0.05, 0.60, 0.05), (1.3, 0.80, ZR - 0.55), IRON)
    cyl(b, 0.20, 0.10, (1.3, 0.45, ZR - 0.75), "Y", CAST, segs=24)
    cyl(b, 0.17, 0.11, (1.3, 0.45, ZR - 0.75), "Y", SAND, segs=24)
    for k in range(12):
        a_ = 2 * math.pi * k / 12
        box(b, (0.012, 0.115, 0.03), (1.3 + 0.14 * math.cos(a_), 0.45, ZR - 0.75 + 0.14 * math.sin(a_)), SOOT,
            Matrix.Rotation(-a_, 4, "Y"))
    box(b, (0.012, 0.12, 0.12), (1.3, 0.45, ZR - 0.70), SOOT)
    box(b, (0.08, 0.12, 0.012), (1.34, 0.45, ZR - 0.75), SOOT)
    # the name board: hangs under the canopy over the middle of the platform
    for sx in (-1, 1):
        cyl(b, 0.008, 0.30, (sx * 1.4, -0.60, ZR - 0.18), "Z", STEEL, segs=6)
    box(b, (3.2, 0.06, 0.62), (0, -0.60, ZR - 0.62), PAINT)
    box(b, (3.3, 0.08, 0.05), (0, -0.60, ZR - 0.30), IRON)
    box(b, (3.3, 0.08, 0.05), (0, -0.60, ZR - 0.94), IRON)
    box(b, (3.04, 0.065, 0.48), (0, -0.60, ZR - 0.62), SAND)
    objs.append(to_object(b, "feTrainStation_Base", bevel=0.003))
    objs.append(empty("FeSignText_F", (0, -0.64, ZR - 0.62), 0.2))
    objs.append(empty("FeSignText_B", (0, -0.56, ZR - 0.62), 0.2))
    n = 1
    col_box(objs, n, (0, 0, D / 2), (2 * PX, 2 * Y, D)); n += 1
    for sx in (-1, 1):
        for k, h in enumerate((0.75, 0.5, 0.25)):
            col_box(objs, n, (sx * (PX + 0.167 + k * 0.333), 0, h / 2), (0.333, 2 * Y, h)); n += 1
    col_box(objs, n, ((OX0 + OX1) / 2, (OY0 + OY1) / 2, (D + ZT) / 2), (OX1 - OX0, OY1 - OY0, ZT - D)); n += 1
    col_box(objs, n, ((BX0 + BX1) / 2, 0.865, D + 0.45), (BX1 - BX0, 1.03, 0.90)); n += 1
    col_box(objs, n, (TX, 0.95, D + 0.55), (1.6, 0.85, 1.10)); n += 1
    col_box(objs, n, (0, -0.05, ZR + 0.05), (2 * X, 3.0, 0.20)); n += 1
    return objs


# ---------------------------------------------------------------- trains (prefabs <kit>CarPrefab, TrainView.cs)
# Origin = centre of the car on the rail top (y = 0 in the game), front = Blender -Y, no colliders. Wheels sit on
# the rails (tread centre RAIL_C off the middle, flange inside). Width <= 2.6 m, height <= 3.6 m.
def wheelset(name, y, r, objs, spokes=0, pins=None, x_wheel=RAIL_C):
    """An axle with two wheels (FeSpin_r<r>_<name>: TrainView turns it with the distance run). spokes > 0: a spoked
    driving wheel with a counterweight. pins = [(x, angle_deg, length)]: crank pins on the outer faces (angle 0 =
    towards the front, 90 = up)."""
    w = bmesh.new()
    cyl(w, 0.06, 2 * x_wheel + 0.10, (0, 0, 0), "X", STEEL, segs=14)
    for sx in (-1, 1):
        x = sx * x_wheel
        cyl(w, r, 0.12, (x, 0, 0), "X", STEEL, segs=36)                                # tread
        cyl(w, r + 0.03, 0.025, (x - sx * 0.055, 0, 0), "X", STEEL, segs=36)           # flange (inside)
        if spokes:
            ring(w, r - 0.01, r - 0.09, 0.13, (x, 0, 0), "X", CAST, segs=36)
            cyl(w, 0.13, 0.15, (x, 0, 0), "X", CAST, segs=20)
            for k in range(spokes):
                a_ = 2 * math.pi * k / spokes
                box(w, (0.07, 0.045, r - 0.18), (x, (r / 2) * math.cos(a_) * 1.0, (r / 2) * math.sin(a_)), CAST,
                    Matrix.Rotation(a_ - math.pi / 2, 4, "X"))
            side_pins = [pp for pp in (pins or []) if pp[0] * sx > 0]
            cw = -side_pins[0][1] if side_pins else 0.0
            for k in range(5):                                                         # counterweight (opposite the pin)
                a_ = math.radians(cw - 56 + 28 * k)
                box(w, (0.09, 0.20, 0.13), (x, (r - 0.16) * math.cos(a_), (r - 0.16) * math.sin(a_)), CAST,
                    Matrix.Rotation(a_, 4, "X"))
        else:
            cyl(w, r - 0.06, 0.13, (x, 0, 0), "X", CAST, segs=28)
            cyl(w, 0.10, 0.16, (x, 0, 0), "X", CAST, segs=16)
            box(w, (0.14, 0.03, r - 0.15), (x, 0, (r - 0.15) / 2 + 0.08), RUST)         # a mark: the turn shows
    for (px, ang, ln) in (pins or []):
        a_ = math.radians(ang)
        p = Vector((px, -0.32 * math.cos(a_), 0.32 * math.sin(a_)))
        cyl(w, 0.045, ln, p, "X", STEEL, segs=12)
        cyl(w, 0.07, 0.05, p - Vector((math.copysign(ln / 2 - 0.02, px), 0, 0)), "X", CAST, segs=12)
    objs.append(to_object_axis(w, "FeSpin_r%.2f_%s" % (r, name), (0, y, r), ACROSS, bevel=0.002))


def bogie(b, objs, yc, n, r=0.42, sp=1.5):
    """A two-axle bogie: side frames with axle boxes and leaf springs outside the wheels, a bolster."""
    for sx in (-1, 1):
        x = sx * 0.90
        box(b, (0.10, sp + 0.70, 0.14), (x, yc, r + 0.05), CAST)
        beam(b, (x, yc - sp / 2 - 0.30, r + 0.05), (x, yc, r - 0.12), 0.09, 0.10, CAST)
        beam(b, (x, yc + sp / 2 + 0.30, r + 0.05), (x, yc, r - 0.12), 0.09, 0.10, CAST)
        for dy in (-sp / 2, sp / 2):
            box(b, (0.16, 0.24, 0.24), (x, yc + dy, r), IRON)                         # axle box
            for k in range(4):
                box(b, (0.12, 0.50 - k * 0.09, 0.025), (x, yc + dy, r + 0.16 + k * 0.03), STEEL)  # springs
    box(b, (1.9, 0.30, 0.14), (0, yc, r + 0.22), CAST)                                 # bolster
    for k, dy in enumerate((-sp / 2, sp / 2)):
        wheelset("Bogie%d%d" % (n, k), yc + dy, r, objs)


def car_ends(b, L, z=1.02, beam_mat=RED):
    """Buffer beams with two buffers and a coupler hook at both ends of a car of length L."""
    for s in (-1, 1):
        y = s * (L / 2 - 0.40)
        box(b, (2.4, 0.16, 0.30), (0, y, z), beam_mat)
        for sx in (-1, 1):
            cyl(b, 0.07, 0.28, (sx * 0.85, y + s * 0.20, z), "Y", STEEL, segs=14)
            cyl(b, 0.17, 0.04, (sx * 0.85, y + s * 0.33, z), "Y", STEEL, segs=18)       # buffer heads
            cyl(b, 0.10, 0.10, (sx * 0.85, y + s * 0.10, z), "Y", CAST, segs=14)
        box(b, (0.10, 0.30, 0.08), (0, y + s * 0.18, z - 0.05), IRON)                   # coupler
        cyl(b, 0.05, 0.10, (0, y + s * 0.30, z - 0.05), "Z", IRON, segs=10)


def underframe(b, L, z=1.02, axles=()):
    for sx in (-1, 1):
        box(b, (0.10, L - 0.3, 0.24), (sx * 1.15, 0, z), IRON)                          # sole bars
        box(b, (0.08, L - 0.6, 0.18), (sx * 0.40, 0, z), IRON)                          # centre sills
    for k in range(7):
        y = -L / 2 + 0.5 + k * (L - 1.0) / 6
        if any(abs(y - a) < 0.55 for a in axles):
            continue
        box(b, (2.30, 0.08, 0.14), (0, y, z), IRON)
    cyl(b, 0.16, 1.8, (0.55, 0, z - 0.30), "Y", CAST, segs=16)                         # brake cylinder / reservoir
    for sx in (-1, 1):
        for k in range(4):
            box(b, (0.04, 0.04, 0.40), (sx * 1.15, -L / 2 + 1.0 + k * (L - 2.0) / 3, z - 0.30), IRON)


def model_loco_car():
    """Locomotive (8 m): a tank engine. Smokebox with chimney (FeFx_Smoke_1) and lamp, boiler with the steam dome
    and safety valves, side water tanks, the cab, the coal bunker; pony truck, three coupled driving axles and a
    trailing axle (FeSpin_r*: TrainView turns them with the distance run); outside cylinders with crossheads
    (FeTrainCross_n), main rods (FeTrainMain_n) and coupling rods (FeTrainCouple_n) driven from the crank pins
    (FeTrainPin_n) of the middle driver, quartered at 90 degrees (left at front dead centre, right at the top)."""
    objs = []
    b = bmesh.new()
    L = 8.0
    RD, RP = 0.70, 0.40
    AX = (-0.90, 0.55, 2.00)                    # driving axles
    ZB = 2.05                                   # boiler centre
    for sx in (-1, 1):                                                                  # main frames
        box(b, (0.06, 7.2, 0.50), (sx * 0.62, -0.15, 0.85), IRON)
        for y in AX:
            box(b, (0.08, 0.30, 0.16), (sx * 0.62, y, RD), CAST)                        # horn blocks
    car_ends(b, L, z=1.00)
    # pilot (cow catcher)
    for k in range(9):
        x = -0.9 + k * 0.225
        beam(b, (x * 0.6, -3.95, 0.12), (x, -3.70, 0.80), 0.04, 0.04, IRON)
    box(b, (2.0, 0.06, 0.06), (0, -3.92, 0.14), IRON)
    # running boards, splashers over the drivers
    for sx in (-1, 1):
        box(b, (0.36, 4.9, 0.04), (sx * 1.07, -1.05, 1.18), IRON)
        box(b, (0.04, 4.9, 0.10), (sx * 1.25, -1.05, 1.22), IRON)
    # smokebox, boiler, firebox, domes, chimney
    cyl(b, 0.76, 1.05, (0, -2.85, ZB), "Y", SOOT, segs=36)
    cyl(b, 0.70, 0.06, (0, -3.40, ZB), "Y", SOOT, segs=36)                             # smokebox door
    cyl(b, 0.08, 0.08, (0, -3.46, ZB), "Y", STEEL, segs=12)
    for k in range(2):
        box(b, (0.70, 0.04, 0.04), (0, -3.45, ZB + 0.18 - k * 0.36), STEEL)            # door straps
    cyl(b, 0.74, 3.95, (0, -0.35, ZB), "Y", PAINT, segs=36)
    for y in (-2.0, -1.0, 0.0, 1.0):
        cyl(b, 0.75, 0.05, (0, y, ZB), "Y", BRASS, segs=36)                            # boiler bands
    cyl(b, 0.20, 0.55, (0, -2.95, ZB + 0.95), "Z", SOOT, segs=20)                      # chimney
    cyl(b, 0.27, 0.12, (0, -2.95, ZB + 1.29), "Z", SOOT, segs=20, r2=0.22)
    cyl(b, 0.30, 0.10, (0, -2.95, ZB + 0.72), "Z", SOOT, segs=20, r2=0.20)
    cyl(b, 0.28, 0.45, (0, -0.85, ZB + 0.80), "Z", BRASS, segs=24, r2=0.22)            # steam dome
    cyl(b, 0.20, 0.25, (0, -1.80, ZB + 0.80), "Z", PAINT, segs=20, r2=0.15)            # sand dome
    for x in (-0.10, 0.10):
        cyl(b, 0.05, 0.30, (x, 0.95, ZB + 0.85), "Z", BRASS, segs=10)                  # safety valves
    cyl(b, 0.035, 0.25, (0.25, 1.55, 3.48), "Z", BRASS, segs=10)                       # whistle
    for sx in (-1, 1):
        beam(b, (sx * 0.62, -3.3, ZB + 0.35), (sx * 0.62, 1.2, ZB + 0.35), 0.02, 0.02, BRASS)  # handrails
    box(b, (0.22, 0.20, 0.22), (0, -3.50, ZB + 0.86), SOOT)                            # head lamp
    cyl(b, 0.08, 0.04, (0, -3.61, ZB + 0.86), "Y", GLASS, segs=14)
    for sx in (-1, 1):
        box(b, (0.16, 0.14, 0.18), (sx * 0.85, -3.70, 1.33), SOOT)                     # buffer-beam lamps
        cyl(b, 0.05, 0.03, (sx * 0.85, -3.78, 1.33), "Y", RED, segs=12)
    # side tanks
    for sx in (-1, 1):
        plate(b, (0.44, 2.9, 1.25), (sx * 1.04, -0.15, 1.83), PAINT, "+X" if sx > 0 else "-X", n=8)
        box(b, (0.46, 2.92, 0.05), (sx * 1.04, -0.15, 2.48), IRON)
        cyl(b, 0.10, 0.08, (sx * 1.04, -1.2, 2.52), "Z", BRASS, segs=12)               # filler
        box(b, (0.02, 1.2, 0.32), (sx * 1.255, -0.15, 1.95), BRASS)                    # number plate
    # cab + bunker
    CY0, CY1 = 1.30, 3.05
    for sx in (-1, 1):
        box(b, (0.06, CY1 - CY0, 1.0), (sx * 1.25, (CY0 + CY1) / 2, 1.70), PAINT)
        box(b, (0.06, 0.35, 1.2), (sx * 1.25, CY0 + 0.175, 2.80), PAINT)
        box(b, (0.06, 0.35, 1.2), (sx * 1.25, CY1 - 0.175, 2.80), PAINT)
        cyl(b, 0.02, 1.0, (sx * 1.20, CY0 + 0.55, 1.75), "Z", BRASS, segs=8)           # grab rails
    box(b, (2.5, 0.08, 2.20), (0, CY0, 2.30), PAINT)                                   # cab front (spectacle plate)
    for sx in (-1, 1):
        cyl(b, 0.18, 0.09, (sx * 0.65, CY0 - 0.01, 2.95), "Y", GLASS, segs=18)
        ring(b, 0.21, 0.17, 0.10, (sx * 0.65, CY0 - 0.01, 2.95), "Y", BRASS, segs=18)
    box(b, (2.62, CY1 - CY0 + 0.30, 0.08), (0, (CY0 + CY1) / 2, 3.42), SOOT)           # roof
    box(b, (2.30, CY1 - CY0, 0.10), (0, (CY0 + CY1) / 2, 3.50), SOOT)
    box(b, (2.4, CY1 - CY0 - 0.1, 0.06), (0, (CY0 + CY1) / 2, 1.45), WOOD)            # cab floor (over the drivers)
    box(b, (1.2, 0.5, 0.9), (0, CY0 + 0.25, 1.65), CAST)                               # firebox back plate
    box(b, (0.40, 0.04, 0.32), (0, CY0 + 0.51, 1.55), GLOW)                            # fire door glow
    gauge(objs, b, (0.45, CY0 + 0.52, 2.55), "FeTrainGauge", r=0.08)
    plate(b, (2.4, 0.85, 1.35), (0, 3.50, 1.85), PAINT, "+Y", n=6)                     # bunker
    box(b, (2.2, 0.72, 0.12), (0, 3.50, 2.52), SOOT)                                   # coal
    cyl(b, 0.34, 0.22, (0, 3.50, 2.66), "Z", SOOT, segs=9, r2=0.12)
    # cylinders, slide bars, valve chests
    for sx in (-1, 1):
        x = sx * 1.02
        cyl(b, 0.19, 0.70, (x, -2.60, RD), "Y", CAST, segs=24)
        cyl(b, 0.21, 0.05, (x, -2.95, RD), "Y", CAST, segs=24)
        cyl(b, 0.21, 0.05, (x, -2.25, RD), "Y", CAST, segs=24)
        box(b, (0.22, 0.70, 0.22), (x, -2.60, RD + 0.30), CAST)                        # valve chest
        box(b, (0.30, 0.30, 0.10), (sx * 0.80, -2.60, RD + 0.15), IRON)                # to the frame
        for dz in (-0.09, 0.09):
            box(b, (0.05, 1.15, 0.03), (sx * 1.00, -1.65, RD + dz), STEEL)             # slide bars
        box(b, (0.10, 0.10, 0.30), (sx * 1.00, -1.05, RD), IRON)                       # motion bracket
        cyl(b, 0.03, 0.10, (x, -2.90, RD - 0.22), "Z", STEEL, segs=8)                  # drain cocks
    objs.append(empty("FeFx_Smoke_1", (0, -2.95, ZB + 1.36), 0.2))
    for sx in (-1, 1):
        objs.append(empty("FeFx_Steam_%d" % (1 if sx > 0 else 2), (sx * 1.02, -2.90, RD - 0.30), 0.1))
    objs.append(to_object(b, "feTrainLocoCar_Body", bevel=0.003))
    # wheels
    wheelset("Pony", -2.85, RP, objs)
    wheelset("Trail", 3.30, RP, objs)
    for k, y in enumerate(AX):
        pins = [(0.88, 0, 0.10), (-0.88, 90, 0.10)]
        if k == 1:
            pins = [(0.94, 0, 0.22), (-0.94, 90, 0.22)]
        wheelset("Drv%d" % (k + 1), y, RD, objs, spokes=12, pins=pins)
    # rods: side 1 = Blender +X (pin at front dead centre), side 2 = Blender -X (pin at the top)
    LR = 2.0
    for n, sx, ang in ((1, 1, 0), (2, -1, 90)):
        a_ = math.radians(ang)
        off = Vector((0, -0.32 * math.cos(a_), 0.32 * math.sin(a_)))
        pin = Vector((sx * 1.00, AX[1], RD)) + off
        objs.append(empty("FeTrainPin_%d" % n, tuple(pin), 0.05))
        cr = Vector((sx * 1.00, pin.y - math.sqrt(LR * LR - (pin.z - RD) ** 2), RD))
        c = bmesh.new()                                                                 # crosshead + piston rod
        box(c, (0.10, 0.20, 0.15), (0, 0, 0), STEEL)
        cyl(c, 0.04, 0.10, (0, 0, 0), "X", CAST, segs=10)
        cyl(c, 0.035, 0.70, (sx * 0.02, -0.45, 0), "Y", STEEL, segs=12)
        objs.append(to_object(c, "FeTrainCross_%d" % n, location=tuple(cr), bevel=0.001))
        m = bmesh.new()                                                                 # main rod
        d = pin - cr
        beam(m, (0, 0, 0), (0, d.y, d.z), 0.05, 0.09, STEEL)
        cyl(m, 0.07, 0.06, (0, 0, 0), "X", STEEL, segs=12)
        cyl(m, 0.09, 0.06, (0, d.y, d.z), "X", STEEL, segs=14)
        objs.append(to_object(m, "FeTrainMain_%d" % n, location=tuple(cr + Vector((sx * 0.02, 0, 0))), bevel=0.001))
        cp = bmesh.new()                                                                # coupling rod over all three
        ys = [y + off.y for y in AX]
        beam(cp, (0, ys[0] - pin.y, 0), (0, ys[2] - pin.y, 0), 0.04, 0.08, STEEL)
        for y in ys:
            cyl(cp, 0.065, 0.05, (0, y - pin.y, 0), "X", STEEL, segs=12)
        objs.append(to_object(cp, "FeTrainCouple_%d" % n, location=(sx * 0.88, pin.y, pin.z), bevel=0.001))
    return objs


def model_wagon_cargo_car():
    """Cargo Wagon (7 m): a boxcar on two bogies, sliding doors on both sides, roof walk, ladders, brake wheel."""
    objs = []
    b = bmesh.new()
    L = 7.0
    underframe(b, L, axles=(-3.05, -1.55, 1.55, 3.05))
    car_ends(b, L)
    for k in range(2):
        bogie(b, objs, (-2.3, 2.3)[k], k)
    Z0, Z1 = 1.14, 3.25
    box(b, (2.50, L - 0.4, Z1 - Z0), (0, 0, (Z0 + Z1) / 2), RED)
    for y in [-(L - 0.4) / 2 + k * (L - 0.4) / 10 for k in range(11)]:                  # side ribs
        for sx in (-1, 1):
            box(b, (0.04, 0.07, Z1 - Z0), (sx * 1.265, y, (Z0 + Z1) / 2), IRON)
    for sy in (-1, 1):                                                                  # end ribs
        for z in (1.6, 2.2, 2.8):
            box(b, (2.50, 0.05, 0.07), (0, sy * ((L - 0.4) / 2 + 0.02), z), IRON)
    for sx in (-1, 1):
        box(b, (0.03, 1.8, Z1 - Z0 - 0.15), (sx * 1.30, 0, (Z0 + Z1) / 2), RUST)        # door
        for y in (-0.6, 0.0, 0.6):
            box(b, (0.035, 0.05, Z1 - Z0 - 0.2), (sx * 1.31, y, (Z0 + Z1) / 2), IRON)
        box(b, (0.06, 3.8, 0.06), (sx * 1.30, 0.9, Z1 - 0.02), STEEL)                   # door rails
        box(b, (0.06, 3.8, 0.06), (sx * 1.30, 0.9, Z0 + 0.05), STEEL)
        box(b, (0.04, 0.04, 0.50), (sx * 1.32, 0.80, (Z0 + Z1) / 2), STEEL)              # handle
    for k, (w, h) in enumerate(((2.58, 0.06), (2.30, 0.06), (1.80, 0.05), (1.10, 0.04))):   # roof (stepped arch)
        box(b, (w, L - 0.3, h), (0, 0, Z1 + 0.03 + k * 0.05), RUST)
    box(b, (0.50, L - 0.4, 0.04), (0, 0, Z1 + 0.24), WOOD)                              # roof walk
    for sy in (-1, 1):
        ladder(b, 1.05, sy * (L / 2 - 0.20), 1.2, 3.30, along="X", w=0.36)
    cyl(b, 0.22, 0.03, (-0.7, L / 2 - 0.08, 2.9), "Y", IRON, segs=18)                  # brake wheel
    cyl(b, 0.025, 1.7, (-0.7, L / 2 - 0.10, 2.05), "Z", IRON, segs=6)
    box(b, (0.9, 0.02, 0.35), (0.0, -(L / 2 - 0.19), 2.6), HAZ)                         # stencil plate
    objs.append(to_object(b, "feWagonCargoCar_Body", bevel=0.003))
    return objs


def model_wagon_tank_car():
    """Tank Wagon (7 m): a riveted horizontal tank on saddles, dome with hatch, walkways and handrails, ladders,
    bottom outlet valve, two bogies."""
    objs = []
    b = bmesh.new()
    L = 7.0
    underframe(b, L, axles=(-3.05, -1.55, 1.55, 3.05))
    car_ends(b, L)
    for k in range(2):
        bogie(b, objs, (-2.3, 2.3)[k], k)
    ZT, RT = 2.25, 1.05
    cyl(b, RT, L - 0.9, (0, 0, ZT), "Y", SOOT, segs=48)
    for sy in (-1, 1):
        cyl(b, RT, 0.25, (0, sy * ((L - 0.9) / 2 + 0.12), ZT), "Y", SOOT, segs=48, r2=RT * 0.75)  # dished ends
    for y in (-2.2, -0.8, 0.8, 2.2):
        cyl(b, RT + 0.012, 0.04, (0, y, ZT), "Y", IRON, segs=48)
    for y in (-1.9, 1.9):                                                              # saddles + bands
        box(b, (1.6, 0.30, 0.50), (0, y, 1.38), IRON)
        ring(b, RT + 0.03, RT, 0.10, (0, y, ZT), "Y", IRON, segs=48)
    cyl(b, 0.45, 0.30, (0, 0, ZT + RT + 0.05), "Z", SOOT, segs=28)                     # dome
    cyl(b, 0.30, 0.06, (0, 0, ZT + RT + 0.23), "Z", CAST, segs=24)
    bolt_circle(b, 10, 0.26, (0, 0, ZT + RT + 0.26), "Z", STEEL, r=0.014, d=0.02)
    for sx in (-1, 1):                                                                  # walkways + handrails
        box(b, (0.30, L - 0.6, 0.04), (sx * 1.10, 0, 1.30), WOOD)
        for y in [-(L - 1.0) / 2 + k * (L - 1.0) / 6 for k in range(7)]:
            box(b, (0.08, 0.03, 0.03), (sx * 1.07, y, ZT), IRON)                        # handrail brackets
        beam(b, (sx * 1.11, -(L - 1.0) / 2, ZT), (sx * 1.11, (L - 1.0) / 2, ZT), 0.03, 0.03, HAZ)
    for sx in (-1, 1):
        ladder(b, sx * 1.15, 0.0, 1.30, ZT + RT, along="Y", w=0.40)
    cyl(b, 0.10, 0.35, (0, 0, ZT - RT - 0.12), "Z", CAST, segs=14)                     # bottom outlet
    cyl(b, 0.10, 0.03, (0.0, 0.22, ZT - RT - 0.22), "Y", RED, segs=14)
    box(b, (0.02, 1.6, 0.30), (1.06, 1.2, ZT), HAZ)                                    # placard
    box(b, (0.02, 1.6, 0.30), (-1.06, 1.2, ZT), HAZ)
    objs.append(to_object(b, "feWagonTankCar_Body", bevel=0.003))
    return objs


def model_wagon_passenger_car():
    """Passenger Wagon (9 m): a wooden-trimmed coach with windows, an arched clerestory roof, end platforms with
    railings and steps, benches facing each other along both sides and a clear aisle; the floor is 1.0 m over the
    rail (TrainView seats the rider at the middle, 1 m up)."""
    objs = []
    b = bmesh.new()
    L = 9.0
    BL = 8.0                                     # body length; platforms beyond
    underframe(b, L, z=0.82, axles=(-3.8, -2.4, 2.4, 3.8))
    car_ends(b, L, z=0.82)
    for k in range(2):
        bogie(b, objs, (-3.1, 3.1)[k], k)
    FZ = 1.0
    box(b, (2.56, L - 0.2, 0.10), (0, 0, FZ - 0.05), WOOD)                              # floor
    WZ0, WZ1, ZR = 1.75, 2.45, 2.90
    # side walls with window openings
    nwin = 7
    pitch = (BL - 0.6) / nwin
    for sx in (-1, 1):
        x = sx * 1.25
        box(b, (0.06, BL, WZ0 - FZ), (x, 0, (FZ + WZ0) / 2), PAINT)
        box(b, (0.06, BL, ZR - WZ1), (x, 0, (WZ1 + ZR) / 2), PAINT)
        box(b, (0.07, BL, 0.06), (x, 0, WZ0 + 0.03), WOOD)                              # waist rail
        for k in range(nwin + 1):
            y = -(BL - 0.6) / 2 + k * pitch
            box(b, (0.06, 0.34, WZ1 - WZ0), (x, y, (WZ0 + WZ1) / 2), PAINT)              # window posts
        for k in range(nwin):
            y = -(BL - 0.6) / 2 + (k + 0.5) * pitch
            box(b, (0.02, pitch - 0.36, 0.03), (x, y, WZ1 - 0.20), WOOD)                 # window bar (open sash)
        box(b, (0.065, 0.30, ZR - FZ), (x, sx * 0 + (BL / 2 - 0.15), (FZ + ZR) / 2), PAINT)
        box(b, (0.065, 0.30, ZR - FZ), (x, -(BL / 2 - 0.15), (FZ + ZR) / 2), PAINT)
    for sy in (-1, 1):                                                                   # end walls with a doorway
        y = sy * (BL / 2)
        for sx in (-1, 1):
            box(b, (0.85, 0.06, ZR - FZ), (sx * 0.83, y, (FZ + ZR) / 2), PAINT)
        box(b, (0.80, 0.06, ZR - 2.10), (0, y, (2.10 + ZR) / 2), PAINT)
        # platform: railings at the sides, steps down, a gate bar
        for sx in (-1, 1):
            cyl(b, 0.025, 1.0, (sx * 1.20, sy * (L / 2 - 0.05), FZ + 0.5), "Z", IRON, segs=8)
            beam(b, (sx * 1.20, y, FZ + 1.0), (sx * 1.20, sy * (L / 2 - 0.05), FZ + 1.0), 0.03, 0.03, IRON)
            beam(b, (sx * 0.45, sy * (L / 2 - 0.05), FZ + 1.0), (sx * 1.20, sy * (L / 2 - 0.05), FZ + 1.0), 0.03, 0.03, IRON)
            for k, z in enumerate((0.70, 0.40)):
                box(b, (0.30, 0.35, 0.04), (sx * (1.10 + 0.0), sy * (BL / 2 + 0.20), z), IRON)
    # roof: arched, with a clerestory and vents
    for k, (w, h) in enumerate(((2.62, 0.06), (2.40, 0.07), (2.05, 0.07), (1.55, 0.07))):   # arched roof (stepped)
        box(b, (w, BL + 0.4, h), (0, 0, ZR + 0.03 + k * 0.065), SOOT)
    box(b, (1.10, BL - 0.8, 0.26), (0, 0, ZR + 0.36), SOOT)                             # clerestory
    for k in range(6):
        cyl(b, 0.09, 0.12, (0, -3.0 + k * 1.2, ZR + 0.55), "Z", CAST, segs=12)
    # inside: benches facing each other along both sides, the aisle clear (|x| < 0.40); ceiling lamps
    for sx in (-1, 1):
        for k in range(nwin):
            y = -(BL - 0.6) / 2 + (k + 0.5) * pitch
            for sy in (-1, 1):
                yb = y + sy * (pitch / 2 - 0.12)
                box(b, (0.78, 0.44, 0.06), (sx * 0.80, yb - sy * 0.18, FZ + 0.45), WOOD)  # seat
                box(b, (0.78, 0.06, 0.55), (sx * 0.80, yb, FZ + 0.74), WOOD)             # back
                box(b, (0.06, 0.44, 0.45), (sx * 0.43, yb - sy * 0.18, FZ + 0.22), CAST)  # end frame
        box(b, (0.30, BL - 0.8, 0.03), (sx * 1.02, 0, 2.55), IRON)                       # luggage racks
    for k in range(4):
        cyl(b, 0.10, 0.10, (0, -3.0 + k * 2.0, ZR - 0.04), "Z", GLASS, segs=14)
    box(b, (1.6, 0.02, 0.22), (0, -(BL / 2 + 0.035), 2.25), HAZ)                         # destination board
    objs.append(to_object(b, "feWagonPassengerCar_Body", bevel=0.003))
    return objs


# ---------------------------------------------------------------- train kits (1 x 1 blocks that become a car)
def model_train_kit(kind):
    """A train kit: a timber crate on a pallet, banded with steel, the car's silhouette stencilled on its front and
    sides (colour per kind), a shipping label on the lid."""
    b = bmesh.new()
    col = {"loco": OUT, "cargo": RED, "tank": HAZ, "passenger": IN}[kind]
    for k in range(5):                                                                  # pallet
        box(b, (0.92, 0.12, 0.02), (0, -0.40 + k * 0.20, 0.13), WOOD)
    for x in (-0.38, 0.0, 0.38):
        box(b, (0.12, 0.92, 0.10), (x, 0, 0.06), WOOD)
    Z0, Z1 = 0.14, 0.86
    box(b, (0.84, 0.84, Z1 - Z0), (0, 0, (Z0 + Z1) / 2), WOOD)
    for sx in (-1, 1):                                                                  # crate frame
        for sy in (-1, 1):
            box(b, (0.06, 0.06, Z1 - Z0 + 0.01), (sx * 0.41, sy * 0.41, (Z0 + Z1) / 2), WOOD)
    for z in (Z0 + 0.04, Z1 - 0.04):
        for s in (-1, 1):
            box(b, (0.86, 0.06, 0.06), (0, s * 0.41, z), WOOD)
            box(b, (0.06, 0.86, 0.06), (s * 0.41, 0, z), WOOD)
    for x in (-0.25, 0.25):                                                             # steel bands
        box(b, (0.03, 0.87, Z1 - Z0 + 0.02), (x, 0, (Z0 + Z1) / 2), STEEL)
        box(b, (0.03, 0.87, 0.012), (x, 0, Z1 + 0.006), STEEL)
    box(b, (0.30, 0.20, 0.006), (0.12, 0.10, Z1 + 0.004), SAND)                         # label
    for k in range(3):
        box(b, (0.22, 0.012, 0.004), (0.12, 0.06 + k * 0.04, Z1 + 0.008), SOOT)

    def stencil(face):
        # face: "-Y" (front) or "+X" / "-X" (sides); draws in a plane just off that face
        def at(u, v):
            if face == "-Y":
                return Vector((u, -0.425, v))
            return Vector((0.425 if face == "+X" else -0.425, u, v))
        t = (0.30, 0.006, 0.0) if face == "-Y" else (0.006, 0.30, 0.0)

        def rect(u, v, w, h, mat=col):
            size = (w, 0.006, h) if face == "-Y" else (0.006, w, h)
            box(b, size, at(u, v), mat)

        def disc(u, v, r, mat=SOOT):
            cyl(b, r, 0.008, at(u, v), "Y" if face == "-Y" else "X", mat, segs=16)
        rect(0, 0.26, 0.70, 0.02, SOOT)                                                 # rail line
        if kind == "loco":
            rect(-0.08, 0.45, 0.42, 0.16)                                               # boiler
            rect(0.20, 0.50, 0.16, 0.30)                                                # cab
            rect(-0.24, 0.60, 0.05, 0.12)                                               # chimney
            rect(0.20, 0.67, 0.22, 0.03, SOOT)                                          # cab roof
            for u in (-0.20, -0.04, 0.12):
                disc(u, 0.32, 0.055)
        elif kind == "cargo":
            rect(0, 0.48, 0.56, 0.30)
            rect(0, 0.48, 0.14, 0.26, SOOT)
            for u in (-0.20, -0.10, 0.10, 0.20):
                disc(u, 0.31, 0.035)
        elif kind == "tank":
            cyl(b, 0.14, 0.50, at(0, 0.47), "X" if face == "-Y" else "Y", col, segs=20)
            rect(0, 0.63, 0.08, 0.05)
            for u in (-0.20, -0.10, 0.10, 0.20):
                disc(u, 0.31, 0.035)
        else:
            rect(0, 0.48, 0.60, 0.28)
            for u in (-0.21, -0.07, 0.07, 0.21):
                rect(u, 0.53, 0.09, 0.08, SAND)
            rect(0, 0.64, 0.62, 0.03, SOOT)
            for u in (-0.22, -0.12, 0.12, 0.22):
                disc(u, 0.31, 0.035)
    for f in ("-Y", "+X", "-X"):
        stencil(f)
    name = {"loco": "feTrainLoco", "cargo": "feWagonCargo", "tank": "feWagonTank", "passenger": "feWagonPassenger"}[kind]
    return [to_object(b, name + "_Kit", bevel=0.002)]


D14_MODELS = {
    "feRailStraight": model_rail_straight,
    "feRailCurve": model_rail_curve,
    "feRailRamp": model_rail_ramp,
    "feRailSwitchR": lambda: model_rail_switch(True),
    "feRailSwitchL": lambda: model_rail_switch(False),
    "feMiningRig": model_mining_rig,
    "feOilExtractor": model_oil_extractor,
    "feStorageTank": model_storage_tank,
    "feTrainStation": model_train_station,
    "feTrainLoco": lambda: model_train_kit("loco"),
    "feWagonCargo": lambda: model_train_kit("cargo"),
    "feWagonTank": lambda: model_train_kit("tank"),
    "feWagonPassenger": lambda: model_train_kit("passenger"),
    "feTrainLocoCar": model_loco_car,
    "feWagonCargoCar": model_wagon_cargo_car,
    "feWagonTankCar": model_wagon_tank_car,
    "feWagonPassengerCar": model_wagon_passenger_car,
}


MODELS = {
    "feCoalEngine": model_coal_engine,
    "feBus": model_bus,
    "feGasEngine": model_gas_engine,
    "feBeltCrate": model_belt_crate,
    "feBiodigester": model_biodigester,
    "feBiodigesterBig": model_biodigester_big,
    "feSteamDryer": model_steam_dryer,
    "feChemMixer": model_chem_mixer,
    "feWasher": model_washer,
    "feConveyorDuct": model_conveyor_duct,
    # "feConveyorStand": our stand with the belt's shapes now (Art/feConveyor/build_feConveyor.py)
    "feFunnel": model_funnel,
    "feElectricMotor": model_electric_motor,
    "feElectricMotor2": model_electric_motor2,
    "feElectricMotor3": model_electric_motor3,
    "feDynamo": model_dynamo,
    "feDynamo2": model_dynamo2,
    "feGearbox": model_gearbox,
    "feSpeedBox": model_speedbox,
    "feSpinInverter": model_inverter,
    "feClutch": model_clutch,
    "feSteamEngine": model_steam_engine,
    "feM_Lathe": model_m_lathe,
    "feCrusher": model_crusher,
    "feConveyor": model_conveyor,
    "feM_Ammo": model_m_ammo,
    "feShaft": model_shaft,
    "fePipe": model_pipe,
    "feMechPump": model_mech_pump,
    "feCondenser": model_condenser,
    "feMetalChute": model_metal_chute,
    "feCaster": model_caster,
    "feM_Foundry": model_m_foundry,
    **D12_MODELS,
    **PLANT_MODELS,
    **ITEM_MODELS,
    "feHydroTower": model_hydro_tower,
    "feWaterWheel": model_water_wheel,
    **D13_MODELS,
    **D14_MODELS,
}


def build(name):
    _JIT[0] = 0
    bpy.ops.wm.read_factory_settings(use_empty=True)
    make_materials()
    objs = MODELS[name]()
    col = bpy.context.scene.collection
    for ob in objs:
        col.objects.link(ob)
    # the root must sit at the origin unrotated (the texturing step exports the hierarchy relative to it): the first
    # mesh without its own transform (a needle or a wheel made first must not become the root)
    for i, ob in enumerate(objs):
        if ob.type == "MESH" and ob.parent is None and ob.location.length < 1e-6 and Vector(ob.rotation_euler).length < 1e-6:
            objs.insert(0, objs.pop(i))
            break
    root = objs[0]
    bpy.context.view_layer.update()                # world matrices of transformed roots are valid before parenting
    for ob in objs[1:]:
        if ob.parent is not None:                  # parts loaded with their own hierarchy keep it
            continue
        ob.parent = root
        ob.matrix_parent_inverse = root.matrix_world.inverted()
    bpy.context.view_layer.update()
    tris = 0
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for ob in objs:
        if ob.type != "MESH":
            continue
        tris += sum(len(p.vertices) - 2 for p in ob.data.polygons)
        for v in ob.data.vertices:
            w_ = ob.matrix_world @ v.co
            lo = Vector(map(min, lo, w_))
            hi = Vector(map(max, hi, w_))
    d = os.path.join(ART, name, "hd")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, name + "_src.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print(f"[feHD] {name}: {len(objs)} objects, {tris} tris, bounds {tuple(round(c, 3) for c in lo)} .. "
          f"{tuple(round(c, 3) for c in hi)} -> {path}", flush=True)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else list(MODELS)
    for n in (args or list(MODELS)):
        build(n)
