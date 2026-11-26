"""Builds our low conveyor (belt top at port height) for the D10 belt code (src/ForgedInAshes/Belt.cs).

Run inside Blender (Scripting tab, the Blender MCP server, or `blender --background --python`).
Units: 1 Blender unit = 1 m = 1 game block; origin at the floor centre of the block.

Contract with Belt.cs / KineticSpinner.cs (same as Dario's first model, Art/feKinetic model_conveyor):
  - travel = the block front = Unity +Z = Blender -Y; Unity left (-X) = Blender +X (the "_L" parts);
  - belt surface at Belt.Top = 0.18 (ours: 0.175, the bottom of a machine's port opening is 0.14, its centre
    0.25, Art/CONVEYOR_PORTS.md), so a belt plugs straight into a machine port with no chute;
  - the parts BeltShape shows or hides (every one a top-level object, no parent: the FBX bake breaks grandchildren):
      straight: FeBeltBed (frame, legs, rubber belt), FeBeltSlats (cleats sliding 0.125 m toward the front, over
                and over), FeSpin_BeltRollerFront/Back, FeRail_L/R (hidden where another belt joins that side),
                FeBeltEnd (stop bar when nothing takes the items in front);
      curve:    FeCurveSet_L/R (quarter-ring belt around the back corner of that side, radius 0.5 = the items'
                arc) + FeCurveSlats_L/R (cleats turning about the vertical axis through that corner);
      junction: FeJunction (transfer table with ball casters), FeJunctionPosts, FeJunctionWedge (V divider);
      drive:    FeBeltDrive_L/R (bearing stand + chain guard) and FeSpin_BeltDrive_L/R (shaft coupling at the
                block's centre height 0.5, on that side face). Shown only on a side where a torque block (shaft,
                gearbox, motor...) touches the belt, so a line of belts stays clean.
  - spin parts are built along local Y and turned 90 degrees about Z (spin axis = Unity local +Z).

Pieces (one collection each): feConveyor (all the looks above), feConveyorRamp (up one block: back at 0.175,
front at 1.175), feConveyorDown (back at 1.175, front at 0.175). The ramps have only base, slats, rollers and
drive. The scene is cleared first (except Camera/Light/fePreview*): save anything else before running this.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

TOP = 0.175                       # belt surface
BELT_W, BELT_T = 0.32, 0.012
ROLL_R = 0.035
ROLL_Z = TOP - ROLL_R - BELT_T / 2   # roller axis (0.134)
L_RUN = 0.45                      # drums at +-L_RUN along the travel
CH_X, CH_W = 0.19, 0.03           # side channels: centre offset, width
CH_Z0, CH_Z1 = 0.075, 0.168       # channel bottom / top (just under the belt surface)
RAIL_Z1 = 0.235                   # guide rail top
C = 0.5                           # torque axis height (shafts)
SPACING = 0.125                   # BeltShape.Spacing
Q = math.pi / 2

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
AXIS = {"Z": Matrix.Identity(4), "Y": Matrix.Rotation(Q, 4, "X"), "X": Matrix.Rotation(Q, 4, "Y")}


def _finish(bm, mat, matrix, verts):
    bmesh.ops.transform(bm, matrix=matrix, verts=verts)
    for f in {f for v in verts for f in v.link_faces}:
        f.material_index = mat


def box(bm, size, loc, mat, rot=Matrix.Identity(4)):
    r = bmesh.ops.create_cube(bm, size=1.0)
    _finish(bm, mat, Matrix.Translation(loc) @ rot @ Matrix.Diagonal((*size, 1.0)), r["verts"])


def beam(bm, a, b, w, t, mat, up=Vector((0, 0, 1))):
    """Box from a to b; local X = w (horizontal), local Y = t (towards `up`)."""
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
    r = bmesh.ops.create_cube(bm, size=1.0)
    _finish(bm, mat, m @ Matrix.Diagonal((w, t, d.length, 1.0)), r["verts"])


def cyl(bm, r, depth, loc, axis, mat, segs=16, r2=None):
    res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                                radius1=r, radius2=r if r2 is None else r2, depth=depth)
    _finish(bm, mat, Matrix.Translation(loc) @ AXIS[axis], res["verts"])


def arc_solid(bm, pt, r0, r1, a0, a1, z0, z1, n, mat):
    """Solid ring sector: radii r0..r1, angles a0..a1 (pt(r, th) -> (x, y)), heights z0..z1, n segments."""
    rings = []
    for k in range(n + 1):
        th = a0 + (a1 - a0) * k / n
        ring = []
        for r, z in ((r0, z0), (r0, z1), (r1, z1), (r1, z0)):
            x, y = pt(r, th)
            ring.append(bm.verts.new((x, y, z)))
        rings.append(ring)
    faces = []
    for k in range(n):
        A, B = rings[k], rings[k + 1]
        for i in range(4):
            j = (i + 1) % 4
            faces.append(bm.faces.new((A[i], A[j], B[j], B[i])))
    faces.append(bm.faces.new(tuple(rings[0])))
    faces.append(bm.faces.new(tuple(reversed(rings[-1]))))
    for f in faces:
        f.material_index = mat


def to_object(bm, name, col, location=(0, 0, 0), rotation=(0, 0, 0), smooth=True):
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
    ob = bpy.data.objects.new(name, me)
    ob.location = location
    ob.rotation_euler = rotation
    col.objects.link(ob)
    return ob


# ---------------------------------------------------------------- straight run (local frame)
# A straight run is built in a local frame with the belt surface at z = 0 and the travel toward -Y, between
# y = -half and +half; `place` maps it into the block (identity + TOP for the flat belt, a 45 degree tilt for ramps).

def rubber_loop(bm, half_run):
    """Closed rubber belt around the two drums (local frame, surface at z = 0)."""
    rz = ROLL_Z - TOP
    rb = ROLL_R + BELT_T / 2
    pts = []
    n_run, n_arc = 6, 10
    for i in range(n_run):
        pts.append((half_run - 2 * half_run * i / n_run, rz + rb))           # top run, back -> front
    for i in range(n_arc):
        a = Q + math.pi * i / n_arc                                           # around the front drum
        pts.append((-half_run + rb * math.cos(a), rz + rb * math.sin(a)))
    for i in range(n_run):
        pts.append((-half_run + 2 * half_run * i / n_run, rz - rb))          # bottom run
    for i in range(n_arc):
        a = -Q + math.pi * i / n_arc                                          # around the back drum
        pts.append((half_run + rb * math.cos(a), rz + rb * math.sin(a)))
    n = len(pts)
    rings = []
    for i, (y, z) in enumerate(pts):
        (y0, z0), (y1, z1) = pts[i - 1], pts[(i + 1) % n]
        dy, dz = y1 - y0, z1 - z0
        ln = math.hypot(dy, dz)
        ny, nz = -dz / ln, dy / ln                                            # outward
        o = (y + ny * BELT_T / 2, z + nz * BELT_T / 2)
        i_ = (y - ny * BELT_T / 2, z - nz * BELT_T / 2)
        rings.append([bm.verts.new((-BELT_W / 2, o[0], o[1])), bm.verts.new((BELT_W / 2, o[0], o[1])),
                      bm.verts.new((BELT_W / 2, i_[0], i_[1])), bm.verts.new((-BELT_W / 2, i_[0], i_[1]))])
    for i in range(n):
        j = (i + 1) % n
        for k in range(4):
            k2 = (k + 1) % 4
            f = bm.faces.new((rings[i][k], rings[i][k2], rings[j][k2], rings[j][k]))
            f.material_index = RUBBER


def run_frame(bm, half, half_run):
    """Side channels (C profile), idlers, drum axle bolts (local frame)."""
    cz0, cz1 = CH_Z0 - TOP, CH_Z1 - TOP
    for sx in (-1, 1):
        box(bm, (CH_W, 2 * half, cz1 - cz0), (sx * CH_X, 0, (cz0 + cz1) / 2), IRON)
        for z in (cz0 + 0.006, cz1 - 0.006):                                  # flanges outside
            box(bm, (0.025, 2 * half, 0.012), (sx * (CH_X + 0.025), 0, z), IRON)
        for y in (-half_run, half_run):
            cyl(bm, 0.018, 0.012, (sx * (CH_X + 0.021), y, ROLL_Z - TOP), "X", RUST, segs=6)
    for y in (-0.2, 0.0, 0.2):
        cyl(bm, 0.012, BELT_W, (0, y * half / 0.5, -0.013 - BELT_T / 2), "X", STEEL, segs=8)
    box(bm, (2 * CH_X - CH_W, 2 * half - 0.04, 0.006), (0, 0, cz0 + 0.003), RUST)   # drip tray


def run_rails(bm, half, sides=(-1, 1)):
    """Guide rails above the channels with orange arrows toward the front (local frame)."""
    rz0, rz1 = CH_Z1 - TOP, RAIL_Z1 - TOP
    for sx in sides:
        box(bm, (0.012, 2 * half, rz1 - rz0), (sx * (CH_X - 0.004), 0, (rz0 + rz1) / 2), RUST)
        box(bm, (0.03, 2 * half, 0.01), (sx * CH_X, 0, rz1), IRON)                         # top lip
        for y0 in (0.25 * half / 0.5, -0.20 * half / 0.5):
            tip = Vector((sx * (CH_X + 0.004), y0 - 0.05, (rz0 + rz1) / 2))
            for dz in (-0.025, 0.025):
                beam(bm, (sx * (CH_X + 0.004), y0 + 0.02, (rz0 + rz1) / 2 + dz), tip, 0.004, 0.014, PAINT,
                     up=Vector((sx, 0, 0)))


def run_slats(bm, half):
    """Cleats on the top run, SPACING apart along the travel; BeltShape slides them one spacing forward."""
    n = int(round(2 * (half - 0.0625) / SPACING)) + 1
    for k in range(n):
        y = (half - 0.0625) - k * SPACING
        box(bm, (BELT_W - 0.02, 0.018, 0.008), (0, y, 0.004), RUBBER)
        box(bm, (BELT_W - 0.03, 0.006, 0.004), (0, y - 0.006, 0.010), STEEL)


def roller(col, name, loc_local, place):
    """Drum along local Y, object turned 90 degrees about Z (spin axis = Unity local +Z = across the block)."""
    bm = bmesh.new()
    cyl(bm, ROLL_R, BELT_W + 0.01, (0, 0, 0), "Y", STEEL, segs=16)
    cyl(bm, 0.01, 2 * CH_X + 0.03, (0, 0, 0), "Y", IRON, segs=8)
    for s in (-1, 1):
        cyl(bm, ROLL_R + 0.004, 0.008, (0, s * (BELT_W / 2 + 0.002), 0), "Y", IRON, segs=16)
        box(bm, (0.006, 0.012, 2 * ROLL_R - 0.01), (0, s * BELT_W / 4, 0), IRON)   # a lag strip you see turn
    p = place @ Vector(loc_local)
    return to_object(bm, name, col, location=p, rotation=(0, 0, Q))


# ---------------------------------------------------------------- drive (shaft coupling on a side face)
def drive(col, sx, chain_to, tag):
    """Bearing stand at the side face (x = sx * 0.44) with the coupling at shaft height, and a chain guard down
    to the belt frame at `chain_to` (x, y, z). tag "L" (Blender +X) or "R"."""
    bm = bmesh.new()
    x = sx * 0.44
    box(bm, (0.12, 0.18, 0.012), (x, 0, 0.006), RUST)                        # foot plate
    box(bm, (0.045, 0.07, C - 0.06), (x, 0, (C - 0.06) / 2 + 0.012), IRON)   # post
    for sy in (-1, 1):
        beam(bm, (x, sy * 0.08, 0.012), (x, sy * 0.02, 0.30), 0.03, 0.02, IRON)   # braces
    box(bm, (0.06, 0.13, 0.11), (x, 0, C), IRON)                              # bearing block
    cyl(bm, 0.048, 0.07, (x, 0, C), "X", STEEL, segs=16)
    for sy in (-1, 1):
        for sz in (-1, 1):
            cyl(bm, 0.008, 0.075, (x, sy * 0.045, C + sz * 0.035), "X", RUST, segs=6)
    top = Vector((sx * 0.40, 0, C))
    low = Vector(chain_to)
    beam(bm, top, low, 0.035, 0.07, PAINT, up=Vector((0, 1, 0)))             # chain guard
    cyl(bm, 0.045, 0.04, tuple(low), "X", PAINT, segs=12)                     # lower sprocket cover
    to_object(bm, "FeBeltDrive_" + tag, col)
    hub = bmesh.new()
    cyl(hub, 0.07, 0.025, (0, 0, 0), "Y", STEEL, segs=18)                     # coupling flange
    # Both hubs keep the same orientation (rotation Z 90 degrees, like the rollers) so they turn the same way as
    # the shaft; local -Y = world +X, so the square socket goes on local -Y for L and +Y for R (always outward).
    box(hub, (0.05, 0.03, 0.05), (0, -sx * 0.02, 0), IRON)                     # square socket
    for k in range(4):
        a = k * Q + Q / 2
        cyl(hub, 0.008, 0.03, (0.048 * math.cos(a), 0, 0.048 * math.sin(a)), "Y", RUST, segs=6)
    to_object(hub, "FeSpin_BeltDrive_" + tag, col, location=(sx * 0.475, 0, C), rotation=(0, 0, Q))


# ---------------------------------------------------------------- feConveyor (flat, all looks)
def legs(bm, ys, xs=(-CH_X, CH_X)):
    for y in ys:
        for x in xs:
            box(bm, (0.035, 0.035, CH_Z0 - 0.008), (x, y, (CH_Z0 + 0.008) / 2), IRON)
            box(bm, (0.07, 0.07, 0.008), (x, y, 0.004), RUST)
        beam(bm, (xs[0], y, 0.045), (xs[1], y, 0.045), 0.025, 0.025, IRON)


def build_flat(col):
    place = Matrix.Translation((0, 0, TOP))
    half = 0.5
    # straight look
    bed = bmesh.new()
    run_frame(bed, half, L_RUN)
    rubber_loop(bed, L_RUN)
    bmesh.ops.transform(bed, matrix=place, verts=bed.verts)
    legs(bed, (-0.30, 0.30))
    to_object(bed, "FeBeltBed", col)
    sl = bmesh.new()
    run_slats(sl, L_RUN)
    bmesh.ops.transform(sl, matrix=place, verts=sl.verts)
    to_object(sl, "FeBeltSlats", col)
    for name, sx in (("FeRail_L", 1), ("FeRail_R", -1)):
        r = bmesh.new()
        run_rails(r, half, sides=(sx,))
        bmesh.ops.transform(r, matrix=place, verts=r.verts)
        to_object(r, name, col)
    roller(col, "FeSpin_BeltRollerFront", (0, -L_RUN, ROLL_Z - TOP), place)
    roller(col, "FeSpin_BeltRollerBack", (0, L_RUN, ROLL_Z - TOP), place)
    # wide belt: a belt beside running the same way -> the gap up to the side face is belt too (both belts show
    # their fill, so the two meet at the shared face)
    for tag, sx in (("L", 1), ("R", -1)):
        fl = bmesh.new()
        x0, x1 = BELT_W / 2 + 0.005, 0.5
        box(fl, (x1 - x0, 1.0, 0.006), (sx * (x0 + x1) / 2, 0, TOP - 0.003), RUBBER)
        box(fl, (0.025, 1.0, CH_Z1 - CH_Z0), (sx * 0.4875, 0, (CH_Z0 + CH_Z1) / 2), IRON)    # edge channel
        box(fl, (x1 - x0, 1.0, 0.006), (sx * (x0 + x1) / 2, 0, CH_Z0 + 0.003), RUST)          # tray under it
        for y in (-0.30, 0.30):
            box(fl, (0.03, 0.03, CH_Z0), (sx * 0.4875, y, CH_Z0 / 2), IRON)                   # legs
        to_object(fl, "FeBeltFill_" + tag, col)
        fs = bmesh.new()
        n = int(round(2 * (L_RUN - 0.0625) / SPACING)) + 1
        for k in range(n):
            y = (L_RUN - 0.0625) - k * SPACING
            box(fs, (x1 - x0 - 0.02, 0.018, 0.008), (sx * (x0 + x1) / 2, y, TOP + 0.004), RUBBER)
            box(fs, (x1 - x0 - 0.03, 0.006, 0.004), (sx * (x0 + x1) / 2, y - 0.006, TOP + 0.010), STEEL)
        to_object(fs, "FeBeltFillSlats_" + tag, col)
    end = bmesh.new()
    box(end, (2 * CH_X + 0.03, 0.03, 0.075), (0, -0.475, TOP + 0.04), PAINT)
    box(end, (2 * CH_X + 0.035, 0.035, 0.015), (0, -0.475, TOP + 0.08), IRON)
    for sx in (-1, 1):
        box(end, (0.03, 0.035, 0.12), (sx * CH_X, -0.475, TOP + 0.0), IRON)
    to_object(end, "FeBeltEnd", col)

    # curve looks: pivot at the back corner of that side; radius 0.5 is the belt's centre line
    for tag, sx in (("L", 1), ("R", -1)):
        cx, cy = sx * 0.5, 0.5

        def wp(r, th, cx=cx, cy=cy, sx=sx):
            return (cx - sx * r * math.cos(th), cy - r * math.sin(th))

        def lp(r, th, sx=sx):
            return (-sx * r * math.cos(th), -r * math.sin(th))

        r_in, r_out = 0.5 - BELT_W / 2, 0.5 + BELT_W / 2
        ch_in, ch_out = 0.5 - CH_X, 0.5 + CH_X
        st = bmesh.new()
        arc_solid(st, wp, r_in, r_out, 0, Q, TOP - BELT_T, TOP, 18, RUBBER)                    # belt
        arc_solid(st, wp, r_in + 0.01, r_out - 0.01, 0, Q, TOP - 0.05, TOP - 0.04, 12, RUST)  # bed plate
        for rc in (ch_in, ch_out):
            arc_solid(st, wp, rc - CH_W / 2, rc + CH_W / 2, 0, Q, CH_Z0, CH_Z1, 14, IRON)      # channels
        arc_solid(st, wp, ch_out - 0.006, ch_out + 0.006, 0, Q, CH_Z1, RAIL_Z1, 16, RUST)      # outer rail
        arc_solid(st, wp, ch_out - 0.015, ch_out + 0.015, 0, Q, RAIL_Z1 - 0.005, RAIL_Z1 + 0.005, 16, IRON)
        arc_solid(st, wp, ch_in - 0.006, ch_in + 0.006, 0, Q, CH_Z1, RAIL_Z1, 8, RUST)         # inner rail
        for th in (Q * 0.3, Q * 0.7):                                                          # arrows
            for k, h in enumerate((0.05, 0.034, 0.018)):
                arc_solid(st, wp, ch_out + 0.006, ch_out + 0.012, th + k * 0.05, th + k * 0.05 + 0.04,
                          (CH_Z1 + RAIL_Z1) / 2 - h / 2, (CH_Z1 + RAIL_Z1) / 2 + h / 2, 1, PAINT)
        for th in (Q * 0.2, Q * 0.8):                                                          # legs
            for rc in (ch_in, ch_out):
                x, y = wp(rc, th)
                box(st, (0.035, 0.035, CH_Z0 - 0.008), (x, y, (CH_Z0 + 0.008) / 2), IRON)
                box(st, (0.07, 0.07, 0.008), (x, y, 0.004), RUST)
            a, b = wp(ch_in, th), wp(ch_out, th)
            beam(st, (a[0], a[1], 0.045), (b[0], b[1], 0.045), 0.025, 0.025, IRON)
        to_object(st, "FeCurveSet_" + tag, col)
        cs = bmesh.new()
        n = 9                                                   # BeltShape.CurveStep = 10 degrees
        for k in range(n):
            th = (k + 0.5) * Q / n
            arc_solid(cs, lp, r_in + 0.01, r_out - 0.01, th - 0.012, th + 0.012, TOP, TOP + 0.008, 1, RUBBER)
        to_object(cs, "FeCurveSlats_" + tag, col, location=(cx, cy, 0))

    # junction look: a transfer table the size of the block, on four corner posts
    jn = bmesh.new()
    box(jn, (0.90, 0.90, 0.012), (0, 0, TOP - 0.022), IRON)
    box(jn, (0.86, 0.86, 0.04), (0, 0, TOP - 0.05), RUST)
    for ix in range(5):
        for iy in range(5):
            x, y = -0.32 + ix * 0.16, -0.32 + iy * 0.16
            cyl(jn, 0.026, 0.008, (x, y, TOP - 0.012), "Z", IRON, segs=10)
            cyl(jn, 0.018, 0.016, (x, y, TOP - 0.006), "Z", STEEL, segs=10, r2=0.006)    # ball casters
    to_object(jn, "FeJunction", col)
    po = bmesh.new()
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(po, (0.05, 0.05, TOP + 0.06), (sx * 0.44, sy * 0.44, (TOP + 0.06) / 2), IRON)
            box(po, (0.08, 0.08, 0.008), (sx * 0.44, sy * 0.44, 0.004), RUST)
            box(po, (0.06, 0.06, 0.02), (sx * 0.44, sy * 0.44, TOP + 0.07), PAINT)
    to_object(po, "FeJunctionPosts", col)
    wd = bmesh.new()
    for sx in (-1, 1):
        beam(wd, (0, -0.05, TOP + 0.04), (sx * 0.36, -0.42, TOP + 0.04), 0.02, 0.07, PAINT)
    cyl(wd, 0.03, 0.09, (0, -0.05, TOP + 0.045), "Z", IRON, segs=12)
    to_object(wd, "FeJunctionWedge", col)

    for tag, sx in (("L", 1), ("R", -1)):
        drive(col, sx, (sx * (CH_X + 0.03), 0.0, (CH_Z0 + CH_Z1) / 2), tag)


# ---------------------------------------------------------------- ramps
def build_ramp(col, prefix, up):
    """up: back at TOP, front at TOP + 1 (45 degrees); else the mirror (down ramp)."""
    ang = -math.pi / 4 if up else math.pi / 4
    place = Matrix.Translation((0, 0, TOP + 0.5)) @ Matrix.Rotation(ang, 4, "X")
    half = math.sqrt(2.0) / 2
    half_run = half - 0.05

    def surf_z(y):                                   # belt surface height above world y
        return TOP + 0.5 - y if up else TOP + 0.5 + y

    base = bmesh.new()
    run_frame(base, half, half_run)
    rubber_loop(base, half_run)
    run_rails(base, half)
    bmesh.ops.transform(base, matrix=place, verts=base.verts)
    for y in (-0.40, 0.40):                          # legs to the underside of the channels
        top = surf_z(y) - 0.16
        for x in (-CH_X, CH_X):
            box(base, (0.035, 0.035, top - 0.008), (x, y, (top + 0.008) / 2), IRON)
            box(base, (0.07, 0.07, 0.008), (x, y, 0.004), RUST)
        beam(base, (-CH_X, y, min(0.045, top / 2)), (CH_X, y, min(0.045, top / 2)), 0.025, 0.025, IRON)
        if top > 0.4:
            beam(base, (-CH_X, y, top * 0.6), (CH_X, y, top * 0.6), 0.025, 0.025, IRON)
            for x in (-CH_X, CH_X):
                beam(base, (x, y, 0.05), (x, -y * 0.2, top * 0.55), 0.02, 0.02, IRON)   # diagonal braces
    to_object(base, prefix + "_Base", col)
    sl = bmesh.new()
    n = 7
    for k in range(n):
        y = 0.4375 - k * SPACING                     # world y; BeltShape slides them (0.125 fwd, 0.125 up/down)
        ly = y * math.sqrt(2.0)                      # along the slope
        box(sl, (BELT_W - 0.02, 0.018, 0.008), (0, ly, 0.004), RUBBER)
        box(sl, (BELT_W - 0.03, 0.006, 0.004), (0, ly - 0.006, 0.010), STEEL)
    bmesh.ops.transform(sl, matrix=place, verts=sl.verts)
    to_object(sl, "FeBeltSlats", col)
    roller(col, "FeSpin_BeltRollerFront", (0, -half_run, ROLL_Z - TOP), place)
    roller(col, "FeSpin_BeltRollerBack", (0, half_run, ROLL_Z - TOP), place)
    for tag, sx in (("L", 1), ("R", -1)):
        drive(col, sx, (sx * (CH_X + 0.03), 0.0, surf_z(0.0) - 0.11), tag)


# ---------------------------------------------------------------- Conveyor Stand (feConveyorStand)
def leg(bm, x, y, z1):
    box(bm, (0.045, 0.045, z1 - 0.012), (x, y, (z1 + 0.012) / 2), IRON)
    box(bm, (0.10, 0.10, 0.012), (x, y, 0.006), RUST)
    box(bm, (0.07, 0.07, 0.012), (x, y, z1 - 0.006), RUST)                   # cap the belt's foot stands on


def tie(bm, a, b, z, mat=IRON, w=0.03):
    beam(bm, (a[0], a[1], z), (b[0], b[1], z), w, w, mat)


def cross(bm, a, b, z0, z1):
    beam(bm, (a[0], a[1], z0), (b[0], b[1], z1), 0.02, 0.02, RUST)
    beam(bm, (b[0], b[1], z0), (a[0], a[1], z1), 0.02, 0.02, RUST)


def build_stand(col):
    """One block high trestle under a belt, in the belt's frame (travel -Y). StandShape (ConveyorStand.cs) shows
    the shape of the belt above it and turns it to that belt's rotation: FeStand_Straight (also under ramps and
    with nothing above), FeStand_Curve_L/R, FeStand_Junction, and FeStand_Duct (deck and cradle lips for a
    Conveyor Duct, with the straight one). Legs stand right under the belt's own feet."""
    H = 1.0
    st = bmesh.new()
    pts = [(sx * CH_X, sy * 0.30) for sy in (-1, 1) for sx in (-1, 1)]
    for x, y in pts:
        leg(st, x, y, H)
    for sy in (-1, 1):
        for z in (0.12, 0.55, H - 0.04):
            tie(st, (-CH_X, sy * 0.30), (CH_X, sy * 0.30), z)
    for sx in (-1, 1):
        for z in (0.12, H - 0.04):
            tie(st, (sx * CH_X, -0.30), (sx * CH_X, 0.30), z)
        cross(st, (sx * CH_X, -0.30), (sx * CH_X, 0.30), 0.14, H - 0.06)
    to_object(st, "FeStand_Straight", col)

    for tag, sx in (("L", 1), ("R", -1)):
        cx, cy = sx * 0.5, 0.5

        def wp(r, th, cx=cx, cy=cy, sx=sx):
            return (cx - sx * r * math.cos(th), cy - r * math.sin(th))

        cv = bmesh.new()
        ths = (Q * 0.2, Q * 0.8)
        rs = (0.5 - CH_X, 0.5 + CH_X)
        for th in ths:
            for r in rs:
                leg(cv, *wp(r, th), H)
            for z in (0.12, 0.55, H - 0.04):
                tie(cv, wp(rs[0], th), wp(rs[1], th), z)
        for r in rs:
            for z in (0.12, H - 0.04):
                arc_solid(cv, wp, r - 0.015, r + 0.015, ths[0], ths[1], z - 0.015, z + 0.015, 8, IRON)
        cross(cv, wp(rs[1], ths[0]), wp(rs[1], ths[1]), 0.14, H - 0.06)
        to_object(cv, "FeStand_Curve_" + tag, col)

    jn = bmesh.new()
    corners = [(sx * 0.44, sy * 0.44) for sy in (-1, 1) for sx in (-1, 1)]
    for x, y in corners:
        leg(jn, x, y, H)
    for a, b in ((corners[0], corners[1]), (corners[2], corners[3]), (corners[0], corners[2]), (corners[1], corners[3])):
        for z in (0.12, H - 0.04):
            tie(jn, a, b, z)
        cross(jn, a, b, 0.14, H - 0.06)
    to_object(jn, "FeStand_Junction", col)

    dk = bmesh.new()
    box(dk, (0.56, 0.92, 0.03), (0, 0, H - 0.015), IRON)                    # deck the duct's feet sit on
    for sx in (-1, 1):
        box(dk, (0.04, 0.92, 0.09), (sx * 0.30, 0, H + 0.045), IRON)         # cradle lips
        box(dk, (0.045, 0.92, 0.012), (sx * 0.30, 0, H + 0.094), PAINT)
    to_object(dk, "FeStand_Duct", col)


# ---------------------------------------------------------------- main
PIECES = (("feConveyor", 0.0), ("feConveyorRamp", 1.6), ("feConveyorDown", 3.2),
          ("feConveyorStand", 4.8))   # display offsets in X


def main():
    keep = {"Camera", "Light"}
    for ob in list(bpy.data.objects):
        if ob.name not in keep and not ob.name.startswith("fePreview"):
            bpy.data.objects.remove(ob, do_unlink=True)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    make_materials()
    for name, dx in PIECES:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
        if name == "feConveyor":
            build_flat(col)
        elif name == "feConveyorStand":
            build_stand(col)
        else:
            build_ramp(col, name, up=(name == "feConveyorRamp"))
        tris = 0
        lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
        bpy.context.view_layer.update()
        for ob in col.objects:
            for v in ob.data.vertices:
                w = ob.matrix_world @ v.co
                lo, hi = Vector(map(min, lo, w)), Vector(map(max, hi, w))
            tris += sum(len(p.vertices) - 2 for p in ob.data.polygons)
            ob.location.x += dx
        print(name, "bbox", tuple(round(c, 3) for c in lo), tuple(round(c, 3) for c in hi), "tris", tris,
              "objects", sorted(o.name for o in col.objects))


main()
