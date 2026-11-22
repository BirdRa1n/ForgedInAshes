"""Builds the Flywheel item (I02, item feFlywheel) in the open Blender scene.

Run inside Blender (Scripting tab, or through the Blender MCP server).
An item, not a block: recipe 4 Gear + 2 Iron Plate + 1 Iron Shaft (PLANO_MOD.md, section 6).
The look follows the recipe: two riveted iron plates form the web, a toothed ring
gear forms the rim, and a machined shaft runs through the hub.

Units: meters. Diameter ~0.42 m. Origin at the center of mass; the wheel spins
around local Y (same convention as the rotating parts of the machines).

The scene is cleared of other objects first (except the default Camera/Light and
the fePreview* helpers): save the previous model before running this.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

PITCH_R, TEETH, TOOTH_H = 0.195, 36, 0.022
RIM_IN = 0.15
WEB_T = 0.022          # each of the two plates
SEAM = 0.004
RIM_W = 0.10           # heavy rim, wider than the web
TEETH_W = 0.03         # ring-gear band on the +Y edge of the rim

MATS = {
    "feFlywheel_Iron":  ((0.15, 0.15, 0.16), 0.55, 0.85),
    "feFlywheel_Rust":  ((0.30, 0.13, 0.06), 0.80, 0.35),
    "feFlywheel_Steel": ((0.55, 0.55, 0.57), 0.30, 1.00),
    "feFlywheel_Soot":  ((0.04, 0.04, 0.04), 0.90, 0.20),
}
MI = {name: i for i, name in enumerate(MATS)}
IRON, RUST, STEEL, SOOT = (MI[n] for n in MATS)


def make_materials():
    for name, (rgb, rough, metal) in MATS.items():
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = m.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metal
        m.diffuse_color = (*rgb, 1.0)


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


def build():
    bm = bmesh.new()
    root = PITCH_R - TOOTH_H / 2
    # Heavy smooth rim, plus a ring-gear band on its +Y edge (the "4 Gears").
    smooth_w = RIM_W - TEETH_W
    ring(bm, PITCH_R + TOOTH_H / 2, RIM_IN, smooth_w, (0, -TEETH_W / 2, 0), "Y", IRON, segs=48)
    ty = RIM_W / 2 - TEETH_W / 2
    ring(bm, root, RIM_IN, TEETH_W, (0, ty, 0), "Y", IRON, segs=TEETH * 2)
    tw = 2 * math.pi * PITCH_R / TEETH * 0.5
    for k in range(TEETH):
        m = Matrix.Rotation(2 * math.pi * k / TEETH, 4, "Y") @ Matrix.Translation((root + TOOTH_H / 2, ty, 0))
        box_m(bm, (TOOTH_H, TEETH_W, tw), m, IRON)
    ring(bm, PITCH_R + TOOTH_H / 2 + 0.002, PITCH_R + TOOTH_H / 2 - 0.004, 0.012,
         (0, -RIM_W / 2 + 0.02, 0), "Y", STEEL, segs=48)          # machined balance band
    # Rust bands on the rim faces.
    for s in (-1, 1):
        ring(bm, root - 0.004, RIM_IN + 0.012, 0.004, (0, s * (RIM_W / 2 + 0.001), 0), "Y", RUST, segs=TEETH)

    # Web: two plates (the "2 Iron Plates") with a visible seam and lightening holes.
    for s in (-1, 1):
        y = s * (SEAM / 2 + WEB_T / 2)
        ring(bm, RIM_IN + 0.004, 0.05, WEB_T, (0, y, 0), "Y", IRON, segs=36)
        for k in range(6):
            a = 2 * math.pi * k / 6 + math.pi / 6
            c = Vector((0.10 * math.cos(a), y + s * (WEB_T / 2 + 0.0005), 0.10 * math.sin(a)))
            cyl(bm, 0.030, 0.002, c, "Y", SOOT, segs=12)          # dark recess reads as a hole
            ring(bm, 0.034, 0.030, 0.004, c, "Y", RUST, segs=12)   # chamfered edge
        # Rivets around the web, joining the two plates.
        for k in range(12):
            a = 2 * math.pi * k / 12
            c = (0.135 * math.cos(a), s * (SEAM / 2 + WEB_T + 0.003), 0.135 * math.sin(a))
            cyl(bm, 0.008, 0.006, c, "Y", IRON, segs=6)

    # Hub with bolt circle.
    cyl(bm, 0.055, 0.09, (0, 0, 0), "Y", IRON, segs=16)
    for s in (-1, 1):
        ring(bm, 0.058, 0.040, 0.012, (0, s * 0.045, 0), "Y", RUST, segs=16)
        for k in range(6):
            a = 2 * math.pi * k / 6
            c = (0.042 * math.cos(a), s * 0.052, 0.042 * math.sin(a))
            cyl(bm, 0.007, 0.008, c, "Y", STEEL, segs=6)

    # Machined shaft (the "1 Iron Shaft") with a key on one side.
    cyl(bm, 0.022, 0.30, (0, 0, 0), "Y", STEEL, segs=16)
    for s in (-1, 1):
        cyl(bm, 0.026, 0.012, (0, s * 0.144, 0), "Y", IRON, segs=16)   # end collars
    box_m(bm, (0.010, 0.06, 0.008), Matrix.Translation((0, 0.105, 0.024)), IRON)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("feFlywheel")
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
    # No bevel modifier: it more than doubles the triangle count, too much for an item.
    return bpy.data.objects.new("feFlywheel", me)


def main():
    keep = {"Camera", "Light"}
    for ob in list(bpy.data.objects):
        if ob.name not in keep and not ob.name.startswith("fePreview"):
            bpy.data.objects.remove(ob, do_unlink=True)
    for coll in list(bpy.data.collections):
        if coll.name != "feFlywheel" and not coll.objects and not coll.children:
            bpy.data.collections.remove(coll)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    for m in list(bpy.data.materials):
        if m.users == 0:
            bpy.data.materials.remove(m)
    make_materials()
    col = bpy.data.collections.get("feFlywheel")
    if not col:
        col = bpy.data.collections.new("feFlywheel")
        bpy.context.scene.collection.children.link(col)
    ob = build()
    col.objects.link(ob)
    bpy.context.view_layer.update()
    xs = [v.co for v in ob.data.vertices]
    lo = Vector((min(v.x for v in xs), min(v.y for v in xs), min(v.z for v in xs)))
    hi = Vector((max(v.x for v in xs), max(v.y for v in xs), max(v.z for v in xs)))
    print("bbox min", tuple(round(c, 3) for c in lo), "max", tuple(round(c, 3) for c in hi))
    print("triangles (before bevel):", sum(len(p.vertices) - 2 for p in ob.data.polygons))


main()
