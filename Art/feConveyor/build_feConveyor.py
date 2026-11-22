"""Builds the conveyor pieces in the open Blender scene: straight and 90-degree corner.

Run inside Blender (Scripting tab, or through the Blender MCP server).
Units: 1 Blender unit = 1 m = 1 game block. Each piece is one block, origin at the
floor center of its block. Items enter through the -Y face. Made to match the
conveyor-port standard (Art/CONVEYOR_PORTS.md): belt top at 0.175 m, just above
the bottom of a port opening (0.14 m), belt narrower than the opening (0.36 m).

  feConveyor         straight: -Y face -> +Y face
  feConveyorCorner   right turn: -Y face -> +X face (centerline radius 0.5 m)

Objects per piece (<P> = feConveyor or feConveyorCorner):
  <P>_Frame              static: side channels, guide lips, legs, idlers, arrows (root)
  <P>_Belt               static mesh; UV V runs along the flow (1 tile = 0.25 m) so the
                         game can scroll the texture to animate the belt
  <P>_RollerIn/_RollerOut end drums; spin around their local X
  <P>_PortIn_1/_PortOut_1 empties on the block faces at 0.25 m, +Z pointing outward

The scene is cleared of other objects first (except the default Camera/Light and
the fePreview* helpers): save the previous model before running this.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

BELT_W, BELT_T = 0.32, 0.012
ROLL_R = 0.035
ROLL_Z = 0.134                    # roller axis height -> belt top 0.175
CH_A, CH_W, CH_H, CH_Z = 0.19, 0.03, 0.12, 0.14   # side channels (center offset, width, height, center z)
UV_TILE = 0.25
PORT_Z = 0.25
CORNER_R = 0.5
CORNER_OFFSET_X = 1.6             # where the corner sits in the scene (export puts it back at 0)

MATS = {
    "feConveyor_Iron":   ((0.15, 0.15, 0.16), 0.55, 0.85),
    "feConveyor_Rust":   ((0.30, 0.13, 0.06), 0.80, 0.35),
    "feConveyor_Steel":  ((0.55, 0.55, 0.57), 0.30, 1.00),
    "feConveyor_Rubber": ((0.06, 0.06, 0.06), 0.85, 0.00),
    "feConveyor_Paint":  ((0.85, 0.45, 0.06), 0.60, 0.20),
}
MI = {name: i for i, name in enumerate(MATS)}
IRON, RUST, STEEL, RUBBER, PAINT = (MI[n] for n in MATS)


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


def _finish(bm, mat, matrix, verts):
    bmesh.ops.transform(bm, matrix=matrix, verts=verts)
    for f in {f for v in verts for f in v.link_faces}:
        f.material_index = mat


def box_m(bm, size, matrix, mat):
    r = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)
    _finish(bm, mat, matrix @ Matrix.Diagonal((*size, 1.0)), r["verts"])


def beam(bm, a, b, w, t, mat, up=Vector((0, 0, 1))):
    """Box from a to b; local X = w (horizontal side), local Y = t (towards `up`)."""
    a, b = Vector(a), Vector(b)
    d = b - a
    z = d.normalized()
    x = up.cross(z)
    if x.length < 1e-6:
        x = Vector((1, 0, 0))
    x.normalize()
    y = z.cross(x)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = (a + b) / 2
    box_m(bm, (w, t, d.length), m, mat)


def cyl_m(bm, r, depth, matrix, mat, segs=16):
    """Cylinder along local Z, placed by matrix."""
    res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                                radius1=r, radius2=r, depth=depth, calc_uvs=True)
    _finish(bm, mat, matrix, res["verts"])


# ---------------------------------------------------------------- track mapping
class Track:
    """Maps track coords (s along the flow, a across to the right, z up) to the world.

    s runs from -half to +half; the piece's faces are at s = -half (in) and +half (out).
    """

    def __init__(self, corner):
        self.corner = corner
        self.half = (math.pi * CORNER_R / 4) if corner else 0.5

    def pos(self, s, a, z):
        if not self.corner:
            return Vector((a, s, z))
        phi = math.pi - (s + self.half) / CORNER_R
        r = CORNER_R - a
        return Vector((0.5 + r * math.cos(phi), -0.5 + r * math.sin(phi), z))

    def tangent(self, s):
        if not self.corner:
            return Vector((0, 1, 0))
        phi = math.pi - (s + self.half) / CORNER_R
        return Vector((math.sin(phi), -math.cos(phi), 0))

    def right(self, s):
        t = self.tangent(s)
        return Vector((t.y, -t.x, 0))

    def frame(self, s, a=0.0, z=0.0):
        """Matrix with local X = right, Y = flow tangent, Z = up, at (s, a, z)."""
        m = Matrix((self.right(s), self.tangent(s), Vector((0, 0, 1)))).transposed().to_4x4()
        m.translation = self.pos(s, a, z)
        return m


def sweep_beam(bm, tr, s0, s1, a, z, w, t, mat, segs):
    for k in range(segs):
        p = tr.pos(s0 + (s1 - s0) * k / segs, a, z)
        q = tr.pos(s0 + (s1 - s0) * (k + 1) / segs, a, z)
        beam(bm, p, q, w, t, mat)


# ---------------------------------------------------------------- belt
def belt_loop(L):
    """Closed belt centerline in (s, z): top run, out drum, bottom run, in drum. Returns [(s, z)]."""
    rb = ROLL_R + BELT_T / 2
    pts = []
    n_run, n_arc = 8, 10
    for i in range(n_run):                                    # top run, -L -> +L
        pts.append((-L + 2 * L * i / n_run, ROLL_Z + rb))
    for i in range(n_arc):                                    # around the out drum
        ang = math.pi / 2 - math.pi * i / n_arc
        pts.append((L + rb * math.cos(ang), ROLL_Z + rb * math.sin(ang)))
    for i in range(n_run):                                    # bottom run, +L -> -L
        pts.append((L - 2 * L * i / n_run, ROLL_Z - rb))
    for i in range(n_arc):                                    # around the in drum
        ang = -math.pi / 2 - math.pi * i / n_arc
        pts.append((-L + rb * math.cos(ang), ROLL_Z + rb * math.sin(ang)))
    return pts


def build_belt(tr, L, name):
    loop = belt_loop(L)
    n = len(loop)
    # outward normals of the loop in (s, z), by central differences
    norms = []
    for i in range(n):
        (s0, z0), (s1, z1) = loop[i - 1], loop[(i + 1) % n]
        ds, dz = s1 - s0, z1 - z0
        ln = math.hypot(ds, dz)
        norms.append((dz / ln, -ds / ln))     # left of travel in (s, z) = outward for this loop
    # arc length for V
    acc = [0.0]
    for i in range(1, n + 1):
        (s0, z0), (s1, z1) = loop[i - 1], loop[i % n]
        acc.append(acc[-1] + math.hypot(s1 - s0, z1 - z0))

    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    rings = []   # per loop point: [outer-left, outer-right, inner-right, inner-left]
    for (s, z), (ns, nz) in zip(loop, norms):
        o = (s + ns * BELT_T / 2, z + nz * BELT_T / 2)
        i_ = (s - ns * BELT_T / 2, z - nz * BELT_T / 2)
        rings.append([bm.verts.new(tr.pos(o[0], -BELT_W / 2, o[1])),
                      bm.verts.new(tr.pos(o[0], BELT_W / 2, o[1])),
                      bm.verts.new(tr.pos(i_[0], BELT_W / 2, i_[1])),
                      bm.verts.new(tr.pos(i_[0], -BELT_W / 2, i_[1]))])
    u_of = [0.0, 1.0, 1.0, 0.0]
    for i in range(n):
        j = (i + 1) % n
        v0, v1 = acc[i] / UV_TILE, acc[i + 1] / UV_TILE
        for k in range(4):
            k2 = (k + 1) % 4
            f = bm.faces.new((rings[i][k], rings[i][k2], rings[j][k2], rings[j][k]))
            f.material_index = RUBBER
            for lp, (uu, vv) in zip(f.loops, ((u_of[k], v0), (u_of[k2], v0), (u_of[k2], v1), (u_of[k], v1))):
                lp[uv].uv = (uu, vv)
    return finish_object(bm, name, smooth=False)


# ---------------------------------------------------------------- frame and rollers
def build_frame(tr, L, name):
    bm = bmesh.new()
    # On the corner, straight chord segments poke past the face: stop them 6 mm short.
    half = tr.half - (0.006 if tr.corner else 0.0)
    segs = 1 if not tr.corner else 12
    for side in (-1, 1):
        a = side * CH_A
        sweep_beam(bm, tr, -half, half, a, CH_Z, CH_W, CH_H, IRON, segs)               # channel
        sweep_beam(bm, tr, -half, half, side * 0.186, 0.222, 0.008, 0.03, RUST, segs)  # guide lip
        # flanges (C-profile look) along the channel's top and bottom, outside
        for z in (CH_Z - CH_H / 2 + 0.006, CH_Z + CH_H / 2 - 0.006):
            sweep_beam(bm, tr, -half, half, side * (CH_A + 0.025), z, 0.025, 0.012, IRON, segs)
    # Legs with feet and cross braces.
    for s in (-0.30, 0.30) if not tr.corner else (-0.26, 0.26):
        for side in (-1, 1):
            p = tr.pos(s, side * CH_A, 0.0)
            beam(bm, p + Vector((0, 0, 0.008)), tr.pos(s, side * CH_A, CH_Z - CH_H / 2), 0.035, 0.035, IRON)
            box_m(bm, (0.07, 0.07, 0.008), tr.frame(s, side * CH_A, 0.004), RUST)
        beam(bm, tr.pos(s, -CH_A, 0.045), tr.pos(s, CH_A, 0.045), 0.025, 0.025, IRON)
    # Idler rollers under the top run (static) and axle bolts for the end drums.
    for s in ((-0.2, 0.0, 0.2) if not tr.corner else (-0.17, 0.0, 0.17)):
        cyl_m(bm, 0.012, BELT_W, tr.frame(s, 0, ROLL_Z + ROLL_R - 0.013) @ AXIS["X"], STEEL, segs=8)
    for s in (-L, L):
        for side in (-1, 1):
            cyl_m(bm, 0.018, 0.012, tr.frame(s, side * (CH_A + 0.021), ROLL_Z) @ AXIS["X"], RUST, segs=6)
    # Flow arrows (orange chevrons) on the outside of both channels.
    for side in (-1, 1):
        for s in ((-0.05,) if not tr.corner else (-0.1, 0.1)):
            a = side * (CH_A + CH_W / 2 + 0.002)
            tip = tr.pos(s + 0.05, a, CH_Z)
            for dz in (-0.04, 0.04):
                beam(bm, tr.pos(s - 0.03, a, CH_Z + dz), tip, 0.004, 0.018, PAINT, up=tr.right(s) * side)
    return finish_object(bm, name)


def build_roller(tr, s, name):
    """Drum + axle along local X, origin on the axle."""
    bm = bmesh.new()
    cyl_m(bm, ROLL_R, BELT_W + 0.01, AXIS["X"], STEEL, segs=16)
    cyl_m(bm, 0.01, 2 * CH_A + 0.03, AXIS["X"], IRON, segs=8)
    for side in (-1, 1):
        cyl_m(bm, ROLL_R + 0.004, 0.008, Matrix.Translation((side * (BELT_W / 2 + 0.002), 0, 0)) @ AXIS["X"],
              IRON, segs=16)
    ob = finish_object(bm, name)
    ob.matrix_world = tr.frame(s, 0, ROLL_Z)
    return ob


def finish_object(bm, name, smooth=True):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mname in MATS:
        me.materials.append(bpy.data.materials[mname])
    for p in me.polygons:
        p.use_smooth = smooth
    if smooth:
        try:
            me.set_sharp_from_angle(angle=math.radians(35))
        except (AttributeError, TypeError):
            pass
    return bpy.data.objects.new(name, me)


def build_piece(prefix, corner, col):
    tr = Track(corner)
    # Corner drums sit radially (tilted to the face), so they need more room.
    L = tr.half - (0.07 if corner else 0.05)
    frame = build_frame(tr, L, prefix + "_Frame")
    belt = build_belt(tr, L, prefix + "_Belt")
    r_in = build_roller(tr, -L, prefix + "_RollerIn")
    r_out = build_roller(tr, L, prefix + "_RollerOut")
    objs = [frame, belt, r_in, r_out]
    for kind, s, sign in (("In", -tr.half, -1), ("Out", tr.half, 1)):
        e = bpy.data.objects.new(f"{prefix}_Port{kind}_1", None)
        e.empty_display_type = "SINGLE_ARROW"
        e.empty_display_size = 0.25
        e.location = tr.pos(s, 0, PORT_Z)
        e.rotation_euler = (tr.tangent(s) * sign).to_track_quat("Z", "Y").to_euler()
        objs.append(e)
    for ob in objs:
        col.objects.link(ob)
    bpy.context.view_layer.update()
    for ob in objs[1:]:
        mw = ob.matrix_world.copy()
        ob.parent = frame
        ob.matrix_world = mw
    return frame, objs


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

    for prefix, corner, x in (("feConveyor", False, 0.0), ("feConveyorCorner", True, CORNER_OFFSET_X)):
        col = bpy.data.collections.get(prefix) or bpy.data.collections.new(prefix)
        if col.name not in bpy.context.scene.collection.children:
            bpy.context.scene.collection.children.link(col)
        root, objs = build_piece(prefix, corner, col)
        bpy.context.view_layer.update()
        lo, hi, tris = Vector((1e9,) * 3), Vector((-1e9,) * 3), 0
        for ob in objs:
            if ob.type != "MESH":
                continue
            for v in ob.data.vertices:
                w = ob.matrix_world @ v.co
                lo, hi = Vector(map(min, lo, w)), Vector(map(max, hi, w))
            tris += sum(len(p.vertices) - 2 for p in ob.data.polygons)
        print(prefix, "bbox", tuple(round(c, 3) for c in lo), tuple(round(c, 3) for c in hi), "tris", tris)
        for ob in objs:
            if ob.type == "EMPTY":
                print("  ", ob.name, tuple(round(c, 3) for c in ob.matrix_world.translation),
                      "out-dir", tuple(round(c, 2) for c in (ob.matrix_world.to_3x3() @ Vector((0, 0, 1)))))
        root.location.x = x


main()
