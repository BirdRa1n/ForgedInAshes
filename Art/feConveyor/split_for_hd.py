"""Splits feConveyor.blend (Harrison's build_feConveyor.py) into one source .blend per block for the HD texture
pass (F:\\IA\\texturizar.bat): Art/<block>/hd/<block>_src.blend with only that collection's objects, names kept
(Belt.cs / ConveyorStand.cs find the parts by name, ".001" suffixes included).

Moving band (user 2026-11-24: "what must move is the belt band itself, not just lines"): the rubber band faces
(material feConveyor_Rubber in FeBeltBed / FeCurveSet_* / FeBeltFill_* / the ramps' _Base) get their own material
"feBelt_Band" and a UV layer "BandUV": u = across the band, v = along the travel in tiles of 0.25 m (v grows toward
where the items go; around the loop, through the curve about its corner, and so on). The texturizer keeps that
material and that UV (configs: materiais_efeito + materiais_uv_proprio); FeBuild gives it the tileable band texture
(Art/feFx/belt_band_*.png) and BeltShape scrolls its offset with the belt speed. The separate cleat objects
(FeBeltSlats, FeCurveSlats_*, FeBeltFillSlats_*) are dropped: the cleats are molded in the band texture now.

    blender -b Art/feConveyor/feConveyor.blend --python Art/feConveyor/split_for_hd.py
"""
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

ART = os.path.dirname(os.path.dirname(os.path.abspath(bpy.data.filepath)))
SRC = bpy.data.filepath
TILE = 0.25                                   # m of band per texture tile (two cleats)
TOP, BELT_W, BELT_T, ROLL_R = 0.175, 0.32, 0.012, 0.035
ROLL_Z = TOP - ROLL_R - BELT_T / 2
RB = ROLL_R + BELT_T / 2                       # band centre line radius round a drum
L_RUN = 0.45
DROP = ("FeBeltSlats", "FeCurveSlats", "FeBeltFillSlats")


def band_material():
    m = bpy.data.materials.get("feBelt_Band")
    if m is None:
        m = bpy.data.materials.new("feBelt_Band")
        m.use_nodes = True
        b = m.node_tree.nodes.get("Principled BSDF")
        b.inputs["Base Color"].default_value = (0.05, 0.05, 0.05, 1)
        b.inputs["Roughness"].default_value = 0.85
        m.diffuse_color = (0.05, 0.05, 0.05, 1)
    return m


def loop_s(y, z, half_run):
    """Distance along the closed band (local frame: travel toward -y, surface z = 0), from the back of the top run."""
    rz = ROLL_Z - TOP
    L = 4 * half_run + 2 * math.pi * RB
    if -half_run <= y <= half_run:
        if z > rz:
            return half_run - y, L                                    # top run
        return 2 * half_run + math.pi * RB + (y + half_run), L         # bottom run (back toward the back drum)
    if y < -half_run:                                                  # round the front drum
        a = math.atan2(z - rz, y + half_run)                           # top pi/2 -> front pi -> bottom 3pi/2
        if a < 0:
            a += 2 * math.pi
        return 2 * half_run + RB * (a - math.pi / 2), L
    a = math.atan2(z - rz, y - half_run)                               # back drum: -pi/2 bottom .. pi/2 top
    return 4 * half_run + math.pi * RB + RB * (a + math.pi / 2), L


def set_band(ob, uvfun, rubber_mat):
    """Faces of ob with rubber_mat -> feBelt_Band, BandUV from uvfun(local co) -> (u, s, period)."""
    me = ob.data
    idx = [i for i, m in enumerate(me.materials) if m and m.name == rubber_mat]
    if not idx:
        return 0
    band = band_material()
    if "feBelt_Band" not in [m.name for m in me.materials if m]:
        me.materials.append(band)
    bi = [m.name if m else "" for m in me.materials].index("feBelt_Band")
    uvl = me.uv_layers.get("BandUV") or me.uv_layers.new(name="BandUV")
    n = 0
    for p in me.polygons:
        if p.material_index not in idx:
            continue
        p.material_index = bi
        vals = [uvfun(me.vertices[me.loops[li].vertex_index].co) for li in p.loop_indices]
        period = vals[0][2]
        ss = [s for _, s, _ in vals]
        if period and max(ss) - min(ss) > period / 2:                  # the face across the loop's seam
            ss = [s + period if s < period / 2 else s for s in ss]
        for li, (u, _, per), s in zip(p.loop_indices, vals, ss):
            uvl.data[li].uv = (u, s / TILE)
        n += 1
    return n


def flat_uv(co):
    s, L = loop_s(co.y, co.z - TOP, L_RUN)
    return (co.x + BELT_W / 2) / BELT_W, s * round(L / TILE) * TILE / L, round(L / TILE) * TILE


def ramp_uv(up):
    ang = -math.pi / 4 if up else math.pi / 4
    inv = (Matrix.Translation((0, 0, TOP + 0.5)) @ Matrix.Rotation(ang, 4, "X")).inverted()
    half_run = math.sqrt(2.0) / 2 - 0.05

    def f(co):
        lc = inv @ Vector(co)
        s, L = loop_s(lc.y, lc.z, half_run)
        return (lc.x + BELT_W / 2) / BELT_W, s * round(L / TILE) * TILE / L, round(L / TILE) * TILE
    return f


def curve_uv(sx):
    cx, cy = sx * 0.5, 0.5

    def f(co):
        dx, dy = (cx - co.x) * sx, cy - co.y                           # wp(r, th) = (cx - sx r cos th, cy - r sin th)
        r, th = math.hypot(dx, dy), math.atan2(dy, dx)
        return (r - (0.5 - BELT_W / 2)) / BELT_W, 0.5 * th, 0.0
    return f


def split_outer_rail(ob, sx):
    """The curve's outer guard rail (and its arrows) as an object of its own, FeCurveRail_L/R: on a split (straight on
    + this turn, BeltLook.SplitL/R) the curve shows without it, so the rail does not cross the straight belt."""
    cx, cy = sx * 0.5, 0.5
    r0, r1, z0 = 0.5 + 0.19 - 0.02, 0.5 + 0.19 + 0.02, 0.168 - 0.001
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    sel = [f for f in bm.faces
           if all(r0 <= math.hypot(v.co.x - cx, v.co.y - cy) <= r1 and v.co.z >= z0 for v in f.verts)]
    if not sel:
        bm.free()
        return None
    nb = bmesh.new()
    vmap = {}
    for f in sel:
        vs = []
        for v in f.verts:
            if v not in vmap:
                vmap[v] = nb.verts.new(v.co)
            vs.append(vmap[v])
        nf = nb.faces.new(vs)
        nf.material_index = f.material_index
    bmesh.ops.delete(bm, geom=sel, context="FACES")
    bm.to_mesh(ob.data)
    bm.free()
    me = bpy.data.meshes.new("FeCurveRail_" + ("L" if sx > 0 else "R"))
    nb.to_mesh(me)
    nb.free()
    for m in ob.data.materials:
        me.materials.append(m)
    rail = bpy.data.objects.new(me.name, me)
    rail.matrix_world = ob.matrix_world
    for c in ob.users_collection:
        c.objects.link(rail)
    return rail


def merge_copy(src, name):
    """A side INPUT (a belt feeding this one from the side, BeltLook.MergeL/R): the curve of the other side turned
    180 degrees about the block centre, so it runs from the side face to the front; its BandUV v is negated, so the
    band scrolls from the side toward the front like the items."""
    me = src.data.copy()
    me.name = name
    me.transform(Matrix.Rotation(math.pi, 4, "Z"))
    uvl = me.uv_layers.get("BandUV")
    if uvl:
        for d in uvl.data:
            d.uv = (d.uv[0], -d.uv[1])
    ob = bpy.data.objects.new(name, me)
    ob.matrix_world = src.matrix_world
    for c in src.users_collection:
        c.objects.link(ob)
    return ob


def fill_uv(co):
    return co.x / BELT_W, -co.y, 0.0


# build_feConveyor.py lays the pieces side by side in X for display; each goes back to the block's centre here
# (as export_feConveyor.py does), or the ramp / stand would show metres away from their block in the game
OFFSET = {"feConveyor": 0.0, "feConveyorRamp": 1.6, "feConveyorDown": 3.2, "feConveyorStand": 4.8}

for name in ("feConveyor", "feConveyorRamp", "feConveyorDown", "feConveyorStand"):
    bpy.ops.wm.open_mainfile(filepath=SRC)
    keep = {o.name for o in bpy.data.collections[name].objects}
    for o in list(bpy.data.objects):
        if o.name not in keep or o.name.startswith(DROP):
            bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections):
        if c.name != name:
            bpy.data.collections.remove(c)
    for o in bpy.data.objects:
        if o.parent is None:
            o.location.x -= OFFSET[name]
    for o in list(bpy.data.objects):
        if o.type != "MESH":
            continue
        n = 0
        if o.name.startswith("FeBeltBed"):
            n = set_band(o, flat_uv, "feConveyor_Rubber")
        elif o.name.startswith("FeCurveSet_"):
            sx = 1 if o.name.startswith("FeCurveSet_L") else -1
            n = set_band(o, curve_uv(sx), "feConveyor_Rubber")
            r = split_outer_rail(o, sx)
            print("[split] outer rail", o.name, "->", r.name if r else None, len(r.data.polygons) if r else 0)
        elif o.name.startswith("FeBeltFill_"):
            n = set_band(o, fill_uv, "feConveyor_Rubber")
        elif name in ("feConveyorRamp", "feConveyorDown") and o.name.endswith("_Base"):
            n = set_band(o, ramp_uv(name == "feConveyorRamp"), "feConveyor_Rubber")
        if n:
            print("[split] band", name, o.name, n, "faces")
    if name == "feConveyor":
        # input from Unity left (Blender +X, "_L") = the right curve turned round, and the other way
        for tag, other in (("L", "R"), ("R", "L")):
            cs, rl = bpy.data.objects.get("FeCurveSet_" + other), bpy.data.objects.get("FeCurveRail_" + other)
            if cs:
                merge_copy(cs, "FeMerge_" + tag)
            if rl:
                merge_copy(rl, "FeMergeRail_" + tag)
            print("[split] merge", tag, "from", other)
    d = os.path.join(ART, name, "hd")
    os.makedirs(d, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(d, name + "_src.blend"))
    print("[split]", name, len([o for o in bpy.data.objects]), "objects")
