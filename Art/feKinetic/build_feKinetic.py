"""Builds the torque network models (D8) in the open Blender scene, one collection per block:

  feTorqueCrank      Torque Crank (the Crank without dynamo / battery / insulator; drive shaft out of the back)
  feShaft            Shaft
  feSpeedBox         Speed Box (input end + output end)
  feGearbox          Gearbox (six hubs)
  feSpinInverter     Spin Inverter (input end + output end, counter-rotating gears in a drum)
  feTorqueRegulator  Torque Regulator (input end + output end, flyball governor, handwheel)
  feClutch           Clutch (two halves in a bell housing, release lever)
  feTorqueGauge      Torque Gauge (six hubs, two dials on top, a pointer that turns)
  feWaterWheel       Water Wheel (paddle wheel on two A-frame posts; free torque from water)

Run inside Blender (Scripting tab, or through the Blender MCP server):
  exec(open(r"<repo>/Art/feKinetic/build_feKinetic.py").read())

Conventions (same as Art/feCrank):
  1 Blender unit = 1 m = 1 block; origin at the block's floor center; every model fits the 1x1x1 cell.
  The torque AXIS of a block is Blender Y, at the block center height (Z = 0.5). After the FBX export used by
  export_feKinetic.py (-Z forward, Y up, transform baked) and Unity's import, Blender +Y is Unity -Z and
  Blender -Y is Unity +Z, so:
    - the block axis is the model's local Z in Unity (what the mod expects, FeShaftAxis = z);
    - INPUT ends (Speed Box, Inverter, Regulator) are at Blender +Y (Unity -Z), OUTPUT ends at Blender -Y
      (Unity +Z). Input rings are green, output rings orange.
  Spinning parts (contract in ART_BRIEF.md / src/ForgedInAshes/KineticSpinner.cs) are objects named
  FeSpin, FeSpinIn, FeSpinOut, with tokens _Rev and _x<ratio> plus a unique suffix (the mod ignores unknown
  tokens; Blender needs unique names), e.g. FeSpinIn_SpeedBox. Each one has its PIVOT on its rotation axis and
  spins around its own local Blender Y (Unity local Z). Parts that turn around another axis are rotated objects
  (their local Y = their axis). Shafts are 0.06 m in radius and end in a 0.10 m flange flush with the block face,
  so neighbouring blocks line up.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

C = 0.5            # block center height = torque axis height
SHAFT_R = 0.06
FLANGE_R = 0.10

MATS = {
    "feKin_Wood":    ((0.30, 0.18, 0.09), 0.85, 0.0),
    "feKin_Iron":    ((0.16, 0.16, 0.17), 0.55, 0.85),
    "feKin_Steel":   ((0.42, 0.43, 0.45), 0.35, 0.95),
    "feKin_Rust":    ((0.32, 0.14, 0.06), 0.80, 0.35),
    "feKin_Brass":   ((0.70, 0.52, 0.20), 0.35, 1.0),
    "feKin_Paint":   ((0.20, 0.27, 0.22), 0.65, 0.20),
    "feKin_In":      ((0.16, 0.48, 0.16), 0.60, 0.20),
    "feKin_Out":     ((0.85, 0.45, 0.06), 0.60, 0.20),
    "feKin_Red":     ((0.65, 0.06, 0.05), 0.50, 0.00),
    "feKin_Glass":   ((0.85, 0.88, 0.85), 0.10, 0.00),
    "feKin_Water":   ((0.10, 0.35, 0.85), 0.05, 0.00),
    "feKin_Gas":     ((0.92, 0.94, 0.96), 0.60, 0.00),
    "feKin_Molten":  ((1.00, 0.38, 0.05), 0.35, 0.00),
}
MI = {name: i for i, name in enumerate(MATS)}
WOOD, IRON, STEEL, RUST, BRASS, PAINT, IN, OUT, RED, GLASS, WATERC, GASC, MOLTEN = (MI[n] for n in MATS)

AXIS = {
    "Z": Matrix.Identity(4),
    "Y": Matrix.Rotation(math.pi / 2, 4, "X"),
    "X": Matrix.Rotation(math.pi / 2, 4, "Y"),
}


def make_materials():
    for name, (rgb, rough, metal) in MATS.items():
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = m.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metal
        m.diffuse_color = (*rgb, 1.0)


# ---------------------------------------------------------------- bmesh helpers (as in build_feCrank.py)
def _finish(bm, mat, matrix, verts):
    bmesh.ops.transform(bm, matrix=matrix, verts=verts)
    for f in {f for v in verts for f in v.link_faces}:
        f.material_index = mat


def box(bm, size, loc, mat, rot=Matrix.Identity(4)):
    r = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)
    _finish(bm, mat, Matrix.Translation(loc) @ rot @ Matrix.Diagonal((*size, 1.0)), r["verts"])


def beam(bm, a, b, w, t, mat):
    a, b = Vector(a), Vector(b)
    d = b - a
    rot = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    box(bm, (w, t, d.length), (a + b) / 2, mat, rot)


def cyl(bm, r, depth, loc, axis, mat, segs=16, r2=None):
    res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                                radius1=r, radius2=r if r2 is None else r2, depth=depth, calc_uvs=True)
    _finish(bm, mat, Matrix.Translation(loc) @ AXIS[axis], res["verts"])


def ring(bm, ro, ri, depth, loc, axis, mat, segs=24):
    loops = []
    for rad, z in ((ro, -depth / 2), (ro, depth / 2), (ri, depth / 2), (ri, -depth / 2)):
        loops.append([bm.verts.new((rad * math.cos(2 * math.pi * i / segs),
                                    rad * math.sin(2 * math.pi * i / segs), z)) for i in range(segs)])
    for k in range(4):
        la, lb = loops[k], loops[(k + 1) % 4]
        for i in range(segs):
            j = (i + 1) % segs
            bm.faces.new((la[i], la[j], lb[j], lb[i]))
    _finish(bm, mat, Matrix.Translation(loc) @ AXIS[axis], [v for lp in loops for v in lp])


def gear(bm, r, depth, teeth, loc, axis, mat, tooth=0.025):
    """Spur gear: a disc plus square teeth around it."""
    cyl(bm, r, depth, loc, axis, mat, segs=max(12, teeth))
    for k in range(teeth):
        a = 2 * math.pi * k / teeth
        m = Matrix.Translation(loc) @ AXIS[axis] @ Matrix.Rotation(a, 4, "Z") @ Matrix.Translation((r + tooth / 2, 0, 0))
        rr = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)
        _finish(bm, mat, m @ Matrix.Diagonal((tooth, tooth * 1.1, depth * 0.9, 1.0)), rr["verts"])


def bolts(bm, n, rad, y, z_c, mat, axis="Y", r=0.010, d=0.02):
    for k in range(n):
        a = 2 * math.pi * k / n
        if axis == "Y":
            cyl(bm, r, d, (rad * math.cos(a), y, z_c + rad * math.sin(a)), "Y", mat, segs=6)


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


def shaft_end(bm, y_from, y_to, mat_ring=None):
    """Spinning shaft piece along Y in LOCAL coords (axis through the origin): shaft from y_from to y_to and a
    flange at y_to (the block face). mat_ring paints a thin ring on the flange (input / output colour)."""
    length = abs(y_to - y_from)
    cyl(bm, SHAFT_R, length, (0, (y_from + y_to) / 2, 0), "Y", STEEL, segs=16)
    s = 1 if y_to > y_from else -1
    cyl(bm, FLANGE_R, 0.03, (0, y_to - s * 0.015, 0), "Y", IRON, segs=20)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        cyl(bm, 0.011, 0.012, (0.072 * math.cos(a), y_to - s * 0.034, 0.072 * math.sin(a)), "Y", IRON, segs=6)
    # a flat key on the shaft, so the spin is visible
    box(bm, (0.02, length * 0.6, 0.016), (0, (y_from + y_to) / 2, SHAFT_R + 0.004), RUST)
    if mat_ring is not None:
        ring(bm, FLANGE_R + 0.004, FLANGE_R - 0.018, 0.034, (0, y_to - s * 0.015, 0), "Y", mat_ring, segs=20)


# ---------------------------------------------------------------- models
def model_shaft(col):
    bm = bmesh.new()
    shaft_end(bm, 0.0, -0.5)
    shaft_end(bm, 0.0, 0.5)
    for y in (-0.22, 0.22):   # collars
        cyl(bm, SHAFT_R + 0.012, 0.035, (0, y, 0), "Y", IRON, segs=16)
    # a static empty as the root: with a single object, Unity's FBX import makes the spinning part itself the
    # model root and FeBuild's -0.5 m offset would then drop it to the floor (bundle build, 2026-11-23)
    root = bpy.data.objects.new("feShaft_Base", None)
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = 0.2
    return [root, to_object(bm, "FeSpin_Shaft", location=(0, 0, C), bevel=0.003)]


def housing(bm, w, d, h, mat=PAINT):
    """Box housing centred on the axis, with iron edge bands and feet down to the floor."""
    box(bm, (w, d, h), (0, 0, C), mat)
    for z in (C - h / 2 + 0.02, C + h / 2 - 0.02):
        box(bm, (w + 0.01, d + 0.01, 0.025), (0, 0, z), IRON)
    for sx in (-1, 1):
        for sy in (-1, 1):
            beam(bm, (sx * (w / 2 - 0.05), sy * (d / 2 - 0.05), C - h / 2), (sx * (w / 2 - 0.02), sy * (d / 2 - 0.02), 0.0),
                 0.05, 0.05, IRON)
            box(bm, (0.10, 0.10, 0.015), (sx * (w / 2 - 0.02), sy * (d / 2 - 0.02), 0.008), IRON)


def model_speedbox(col):
    base = bmesh.new()
    housing(base, 0.56, 0.44, 0.50)
    # bearing bosses on both ends; big gear side bulge (input), small (output)
    cyl(base, 0.12, 0.04, (0, 0.24, C), "Y", IRON, segs=20)
    cyl(base, 0.12, 0.04, (0, -0.24, C), "Y", IRON, segs=20)
    ring(base, 0.13, 0.115, 0.045, (0, 0.24, C), "Y", IN, segs=20)
    ring(base, 0.13, 0.115, 0.045, (0, -0.24, C), "Y", OUT, segs=20)
    # inspection window on top with the two gears visible below
    box(base, (0.34, 0.24, 0.012), (0, 0, C + 0.256), GLASS)
    box(base, (0.38, 0.28, 0.014), (0, 0, C + 0.25), IRON)
    # ratio plate (front, +X side): "x2 x4 x1/2" slots
    box(base, (0.012, 0.20, 0.10), (0.285, 0, C + 0.10), BRASS)
    for k, z in enumerate((-0.03, 0.0, 0.03)):
        box(base, (0.014, 0.14, 0.006), (0.29, 0, C + 0.10 + z), RUST)
    out = [to_object(base, "feSpeedBox_Base", bevel=0.004)]
    # input: big gear + shaft out of the +Y face; output: small gear + shaft out of the -Y face.
    # The gears sit side by side on one axis line in the model (offset in X) only visually: one big wheel on the
    # input shaft meshing with a pinion carried by the output shaft through a lay shaft is hidden in the box.
    sin = bmesh.new()
    shaft_end(sin, -0.02, 0.5, IN)
    gear(sin, 0.16, 0.05, 24, (0, 0.06, 0), "Y", BRASS)
    out.append(to_object(sin, "FeSpinIn_SpeedBox", location=(0, 0, C), bevel=0.002))
    sout = bmesh.new()
    shaft_end(sout, 0.02, -0.5, OUT)
    gear(sout, 0.08, 0.05, 12, (0, -0.06, 0), "Y", STEEL)
    out.append(to_object(sout, "FeSpinOut_SpeedBox", location=(0, 0, C), bevel=0.002))
    return out


def model_gearbox(col):
    base = bmesh.new()
    w = 0.62
    box(base, (w, w, w), (0, 0, C), PAINT)
    for z in (C - w / 2 + 0.02, C + w / 2 - 0.02):
        box(base, (w + 0.012, w + 0.012, 0.025), (0, 0, z), IRON)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(base, (0.025, 0.025, w + 0.012), (sx * (w / 2), sy * (w / 2), C), IRON)
    # bosses on the six faces
    for axis, sign, mat_axis in (("X", 1, "X"), ("X", -1, "X"), ("Y", 1, "Y"), ("Y", -1, "Y"), ("Z", 1, "Z"), ("Z", -1, "Z")):
        loc = Vector((0, 0, C))
        loc["XYZ".index(axis)] += sign * (w / 2 + 0.01)
        cyl(base, 0.12, 0.03, loc, mat_axis, IRON, segs=20)
    out = [to_object(base, "feGearbox_Base", bevel=0.004)]
    # six hubs: short shaft + flange from the box face to the block face. Each is its own spinning object whose
    # local Y is its outward axis (rotated objects), all named FeSpin_<n>.
    rots = {
        "+Y": (0, 0, 0), "-Y": (0, 0, math.pi),
        "+X": (0, 0, -math.pi / 2), "-X": (0, 0, math.pi / 2),
        "+Z": (math.pi / 2, 0, 0), "-Z": (-math.pi / 2, 0, 0),
    }
    for k, (name, rot) in enumerate(rots.items()):
        bm = bmesh.new()
        shaft_end(bm, w / 2 - 0.03, 0.5)
        out.append(to_object(bm, "FeSpin_Gearbox" + str(k + 1), location=(0, 0, C), rotation=rot, bevel=0.002))
    return out


def model_inverter(col):
    base = bmesh.new()
    # a drum along the axis with two end plates and a stand
    cyl(base, 0.24, 0.40, (0, 0, C), "Y", PAINT, segs=28)
    for y in (-0.21, 0.21):
        cyl(base, 0.26, 0.03, (0, y, C), "Y", IRON, segs=28)
        bolts(base, 8, 0.235, y + (0.017 if y > 0 else -0.017), C, IRON)
    ring(base, 0.265, 0.245, 0.034, (0, 0.21, C), "Y", IN, segs=28)
    ring(base, 0.265, 0.245, 0.034, (0, -0.21, C), "Y", OUT, segs=28)
    # stand
    for sy in (-0.12, 0.12):
        beam(base, (-0.18, sy, 0.0), (-0.10, sy, C - 0.20), 0.05, 0.05, IRON)
        beam(base, (0.18, sy, 0.0), (0.10, sy, C - 0.20), 0.05, 0.05, IRON)
    box(base, (0.46, 0.36, 0.02), (0, 0, 0.01), IRON)
    # window on the drum showing the reversing gears, and a red curved arrow painted on top
    box(base, (0.16, 0.22, 0.012), (0, 0, C + 0.245), GLASS)
    for k in range(5):
        a = math.radians(-60 + k * 30)
        box(base, (0.03, 0.02, 0.012), (0.20 * math.sin(a), 0.0, C + 0.20 * math.cos(a) + 0.05), RED,
            Matrix.Rotation(a, 4, "Y"))
    out = [to_object(base, "feSpinInverter_Base", bevel=0.004)]
    sin = bmesh.new()
    shaft_end(sin, 0.0, 0.5, IN)
    gear(sin, 0.10, 0.04, 16, (0, 0.06, 0), "Y", BRASS)
    out.append(to_object(sin, "FeSpinIn_Inverter", location=(0, 0, C), bevel=0.002))
    sout = bmesh.new()
    shaft_end(sout, 0.0, -0.5, OUT)
    gear(sout, 0.10, 0.04, 16, (0, -0.06, 0), "Y", STEEL)
    out.append(to_object(sout, "FeSpinOut_Inverter", location=(0, 0, C), bevel=0.002))
    return out


def model_regulator(col):
    base = bmesh.new()
    housing(base, 0.46, 0.42, 0.40)
    cyl(base, 0.12, 0.04, (0, 0.22, C), "Y", IRON, segs=20)
    cyl(base, 0.12, 0.04, (0, -0.22, C), "Y", IRON, segs=20)
    ring(base, 0.13, 0.115, 0.045, (0, 0.22, C), "Y", IN, segs=20)
    ring(base, 0.13, 0.115, 0.045, (0, -0.22, C), "Y", OUT, segs=20)
    # governor column on top
    cyl(base, 0.05, 0.06, (0, 0, C + 0.23), "Z", IRON, segs=16)
    # handwheel on the +X side (setting) and a dial with a red needle
    cyl(base, 0.02, 0.08, (0.27, 0.08, C), "X", IRON, segs=8)
    ring(base, 0.09, 0.075, 0.02, (0.31, 0.08, C), "X", RED, segs=20)
    for k in range(4):
        a = k * math.pi / 2
        beam(base, (0.31, 0.08, C), (0.31, 0.08 + 0.08 * math.cos(a), C + 0.08 * math.sin(a)), 0.012, 0.012, RED)
    cyl(base, 0.07, 0.015, (0.235, -0.10, C + 0.06), "X", BRASS, segs=20)
    cyl(base, 0.06, 0.004, (0.244, -0.10, C + 0.06), "X", GLASS, segs=20)
    beam(base, (0.248, -0.10, C + 0.06), (0.248, -0.06, C + 0.09), 0.006, 0.006, RED)
    out = [to_object(base, "feTorqueRegulator_Base", bevel=0.004)]
    sin = bmesh.new()
    shaft_end(sin, 0.0, 0.5, IN)
    out.append(to_object(sin, "FeSpinIn_Regulator", location=(0, 0, C), bevel=0.002))
    sout = bmesh.new()
    shaft_end(sout, 0.0, -0.5, OUT)
    out.append(to_object(sout, "FeSpinOut_Regulator", location=(0, 0, C), bevel=0.002))
    # flyball governor: vertical spindle with two arms and balls; turns at half the speed, around Z (rotated
    # object so that its local Y is world Z)
    gov = bmesh.new()
    cyl(gov, 0.015, 0.20, (0, 0.10, 0), "Y", STEEL, segs=8)
    cyl(gov, 0.03, 0.03, (0, 0.20, 0), "Y", BRASS, segs=12)
    for s in (-1, 1):
        beam(gov, (0, 0.19, 0), (s * 0.11, 0.08, 0), 0.012, 0.012, STEEL)
        cyl(gov, 0.035, 0.07, (s * 0.12, 0.07, 0), "Z", BRASS, segs=12)
    cyl(gov, 0.035, 0.02, (0, 0.04, 0), "Y", IRON, segs=12)   # sleeve
    for s in (-1, 1):
        beam(gov, (0, 0.04, 0), (s * 0.08, 0.10, 0), 0.008, 0.008, STEEL)
    out.append(to_object(gov, "FeSpin_x0.5_Governor", location=(0, 0, C + 0.26), rotation=(math.pi / 2, 0, 0), bevel=0.002))
    return out


def model_clutch(col):
    """Clutch: two shafts meeting in a bell housing; a red lever on top (static). Engaged, both halves spin
    together; released, the mod gives the clutch no faces, so nothing spins."""
    base = bmesh.new()
    cyl(base, 0.20, 0.30, (0, 0, C), "Y", PAINT, segs=24)              # bell housing
    for y in (-0.16, 0.16):
        cyl(base, 0.215, 0.025, (0, y, C), "Y", IRON, segs=24)
        bolts(base, 8, 0.19, y + (0.014 if y > 0 else -0.014), C, IRON)
    ring(base, 0.22, 0.20, 0.03, (0, 0.16, C), "Y", IN, segs=24)
    ring(base, 0.22, 0.20, 0.03, (0, -0.16, C), "Y", OUT, segs=24)
    for sy in (-0.10, 0.10):                                                # cradle
        beam(base, (-0.16, sy, 0.0), (-0.09, sy, C - 0.16), 0.05, 0.05, IRON)
        beam(base, (0.16, sy, 0.0), (0.09, sy, C - 0.16), 0.05, 0.05, IRON)
    box(base, (0.40, 0.28, 0.02), (0, 0, 0.01), IRON)
    # release lever: pivot block on top, red arm with a knob
    box(base, (0.08, 0.10, 0.05), (0, 0, C + 0.215), IRON)
    beam(base, (0, 0, C + 0.23), (0.0, -0.10, C + 0.42), 0.025, 0.025, RED)
    cyl(base, 0.03, 0.05, (0.0, -0.105, C + 0.43), "X", WOOD, segs=12)
    out = [to_object(base, "feClutch_Base", bevel=0.004)]
    sin = bmesh.new()
    shaft_end(sin, 0.0, 0.5, IN)
    cyl(sin, 0.15, 0.03, (0, 0.03, 0), "Y", STEEL, segs=24)              # pressure plate
    out.append(to_object(sin, "FeSpinIn_Clutch", location=(0, 0, C), bevel=0.002))
    sout = bmesh.new()
    shaft_end(sout, 0.0, -0.5, OUT)
    cyl(sout, 0.15, 0.03, (0, -0.03, 0), "Y", RUST, segs=24)             # friction disc
    out.append(to_object(sout, "FeSpinOut_Clutch", location=(0, 0, C), bevel=0.002))
    return out


def model_gauge(col):
    """Torque Gauge: a small instrument box that joins all six sides (hubs like the Gearbox) with two dials on
    top; the right dial has a pointer disc that turns with the network (a quarter of the speed)."""
    base = bmesh.new()
    w = 0.52
    box(base, (w, w, w), (0, 0, C), BRASS)
    for z in (C - w / 2 + 0.02, C + w / 2 - 0.02):
        box(base, (w + 0.012, w + 0.012, 0.025), (0, 0, z), IRON)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(base, (0.025, 0.025, w + 0.012), (sx * (w / 2), sy * (w / 2), C), IRON)
    for axis, sign in (("X", 1), ("X", -1), ("Y", 1), ("Y", -1), ("Z", -1)):
        loc = Vector((0, 0, C))
        loc["XYZ".index(axis)] += sign * (w / 2 + 0.01)
        cyl(base, 0.11, 0.03, loc, axis, IRON, segs=20)
    # top: a boss for the top hub in the middle and two dials on the corners
    cyl(base, 0.11, 0.03, (0, 0, C + w / 2 + 0.01), "Z", IRON, segs=20)
    for dx, dy in ((-0.15, 0.15), (0.15, -0.15)):
        cyl(base, 0.075, 0.02, (dx, dy, C + w / 2 + 0.01), "Z", IRON, segs=24)
        cyl(base, 0.065, 0.024, (dx, dy, C + w / 2 + 0.012), "Z", GLASS, segs=24)
        for k in range(8):
            a = 2 * math.pi * k / 8
            box(base, (0.012, 0.004, 0.003), (dx + 0.052 * math.cos(a), dy + 0.052 * math.sin(a), C + w / 2 + 0.025), IRON,
                Matrix.Rotation(a, 4, "Z"))
    beam(base, (-0.15, 0.15, C + w / 2 + 0.026), (-0.11, 0.19, C + w / 2 + 0.026), 0.006, 0.003, RED)   # fixed needle
    out = [to_object(base, "feTorqueGauge_Base", bevel=0.003)]
    rots = {
        "+Y": (0, 0, 0), "-Y": (0, 0, math.pi),
        "+X": (0, 0, -math.pi / 2), "-X": (0, 0, math.pi / 2),
        "+Z": (math.pi / 2, 0, 0), "-Z": (-math.pi / 2, 0, 0),
    }
    for k, (name, rot) in enumerate(rots.items()):
        bm = bmesh.new()
        shaft_end(bm, w / 2 - 0.03, 0.5)
        out.append(to_object(bm, "FeSpin_Gauge" + str(k + 1), location=(0, 0, C), rotation=rot, bevel=0.002))
    dial = bmesh.new()   # pointer disc, local Y = up (rotated object)
    cyl(dial, 0.010, 0.012, (0, 0.0, 0), "Y", IRON, segs=8)
    box(dial, (0.006, 0.004, 0.05), (0, 0.0, 0.025), RED)
    out.append(to_object(dial, "FeSpin_x0.25_GaugeDial", location=(0.15, -0.15, C + w / 2 + 0.028),
                         rotation=(math.pi / 2, 0, 0), bevel=0.0))
    return out


def model_waterwheel(col):
    """Water Wheel: a wooden paddle wheel (radius 0.44) on an axle through the whole block, carried by two A-frame
    posts. The wheel, its iron rims and the axle with its two flanges spin as one part (slowly: 16 RPM)."""
    base = bmesh.new()
    for y in (-0.34, 0.34):
        for s_ in (-1, 1):
            beam(base, (s_ * 0.30, y, 0.0), (s_ * 0.04, y, C - 0.03), 0.06, 0.06, WOOD)
        box(base, (0.14, 0.08, 0.09), (0, y, C), IRON)                     # bearing block
        box(base, (0.16, 0.09, 0.015), (0, y, C + 0.05), RUST)
        box(base, (0.66, 0.10, 0.04), (0, y, 0.02), WOOD)                  # sill on the river bed
    out = [to_object(base, "feWaterWheel_Base", bevel=0.004)]
    w = bmesh.new()
    shaft_end(w, 0.0, -0.5)
    shaft_end(w, 0.0, 0.5)
    cyl(w, 0.07, 0.26, (0, 0, 0), "Y", WOOD, segs=16)                        # hub
    for y in (-0.11, 0.11):
        ring(w, 0.44, 0.40, 0.035, (0, y, 0), "Y", WOOD, segs=32)           # wooden rims
        ring(w, 0.445, 0.435, 0.04, (0, y, 0), "Y", IRON, segs=32)          # iron tyres
        for k in range(8):                                                   # spokes
            a = k * math.pi / 4
            m = Matrix.Rotation(a, 4, "Y") @ Matrix.Translation((0.24, y, 0))
            r = bmesh.ops.create_cube(w, size=1.0, calc_uvs=True)
            _finish(w, WOOD, m @ Matrix.Diagonal((0.34, 0.03, 0.035, 1.0)), r["verts"])
    for k in range(12):                                                      # paddles between the rims
        a = k * math.pi / 6
        m = Matrix.Rotation(a, 4, "Y") @ Matrix.Translation((0.40, 0, 0))
        r = bmesh.ops.create_cube(w, size=1.0, calc_uvs=True)
        _finish(w, WOOD, m @ Matrix.Diagonal((0.10, 0.25, 0.02, 1.0)), r["verts"])
    out.append(to_object(w, "FeSpin_WaterWheel", location=(0, 0, C), bevel=0.002))
    return out


def model_steam_engine(col):
    """Steam Engine: vertical boiler with a chimney on the -X side, a horizontal cylinder on the +X side driving a
    flywheel; the flywheel, crank disc and the axle through the whole block (with its two flanges) spin."""
    base = bmesh.new()
    box(base, (0.96, 0.96, 0.05), (0, 0, 0.025), IRON)                          # bed plate
    cyl(base, 0.20, 0.62, (-0.24, 0.10, 0.36), "Z", RUST, segs=24)              # boiler
    cyl(base, 0.21, 0.04, (-0.24, 0.10, 0.68), "Z", IRON, segs=24)
    cyl(base, 0.21, 0.04, (-0.24, 0.10, 0.08), "Z", IRON, segs=24)
    cyl(base, 0.05, 0.30, (-0.24, 0.10, 0.85), "Z", IRON, segs=12)              # chimney
    cyl(base, 0.07, 0.03, (-0.24, 0.10, 1.0 - 0.015), "Z", IRON, segs=12)
    box(base, (0.10, 0.03, 0.08), (-0.24, -0.11, 0.30), BRASS)                  # firebox door
    cyl(base, 0.035, 0.05, (-0.10, 0.10, 0.62), "X", BRASS, segs=10)            # gauge
    cyl(base, 0.09, 0.30, (0.26, 0.10, 0.22), "X", STEEL, segs=16)              # cylinder
    box(base, (0.10, 0.20, 0.10), (0.26, 0.10, 0.10), IRON)
    beam(base, (-0.04, 0.10, 0.30), (0.12, 0.10, 0.24), 0.04, 0.04, BRASS)      # steam pipe
    for y in (-0.36, 0.36):                                                     # axle bearings
        box(base, (0.12, 0.08, C - 0.04), (0, y, (C - 0.04) / 2 + 0.03), IRON)
        box(base, (0.14, 0.09, 0.08), (0, y, C), RUST)
    beam(base, (0.12, 0.10, 0.22), (0.02, -0.20, C - 0.12), 0.025, 0.025, STEEL)  # connecting rod (static)
    out = [to_object(base, "feSteamEngine_Base", bevel=0.003)]
    w = bmesh.new()
    shaft_end(w, 0.0, -0.5)
    shaft_end(w, 0.0, 0.5)
    ring(w, 0.34, 0.29, 0.07, (0, -0.22, 0), "Y", IRON, segs=36)               # flywheel
    cyl(w, 0.07, 0.10, (0, -0.22, 0), "Y", IRON, segs=16)
    for k in range(6):
        a = k * math.pi / 3
        m = Matrix.Rotation(a, 4, "Y") @ Matrix.Translation((0.18, -0.22, 0))
        r = bmesh.ops.create_cube(w, size=1.0, calc_uvs=True)
        _finish(w, IRON, m @ Matrix.Diagonal((0.23, 0.03, 0.04, 1.0)), r["verts"])
    cyl(w, 0.12, 0.03, (0, 0.20, 0), "Y", RUST, segs=20)                       # crank disc
    cyl(w, 0.02, 0.06, (0.08, 0.20, 0), "Y", STEEL, segs=8)
    out.append(to_object(w, "FeSpin_SteamFlywheel", location=(0, 0, C), bevel=0.002))
    return out


# ---------------------------------------------------------------- D9 fluid network
# Pipe arms are named after UNITY local axes (FluidNetwork.cs, PipeArms): Unity +X = Blender -X, Unity +Y = Blender
# +Z, Unity +Z = Blender -Y.
PIPE_R = 0.085


def pipe_arm(bm, axis_vec):
    """Arm from the core to the block face along a Blender unit vector, with a flange at the face (local coords,
    origin = block centre)."""
    v = Vector(axis_vec)
    ax = "X" if v.x else ("Y" if v.y else "Z")
    s_ = v.x + v.y + v.z
    mid = v * 0.31
    cyl(bm, PIPE_R, 0.38, mid, ax, STEEL, segs=14)
    cyl(bm, PIPE_R + 0.03, 0.03, v * 0.485, ax, IRON, segs=14)


def model_pipe(col):
    core = bmesh.new()
    box(core, (0.26, 0.26, 0.26), (0, 0, 0), IRON)
    for a in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
        cyl(core, 0.06, 0.02, Vector(a) * 0.135, "X" if a[0] else ("Y" if a[1] else "Z"), STEEL, segs=10)
    root = bpy.data.objects.new("fePipe_Base", None)   # static empty root at the origin (see model_shaft)
    out = [root, to_object(core, "fePipe_Core", location=(0, 0, C), bevel=0.004)]
    names = {"FeArm_PX": (-1, 0, 0), "FeArm_NX": (1, 0, 0), "FeArm_PY": (0, 0, 1), "FeArm_NY": (0, 0, -1),
             "FeArm_PZ": (0, -1, 0), "FeArm_NZ": (0, 1, 0)}
    for n, v in names.items():
        bm = bmesh.new()
        pipe_arm(bm, v)
        out.append(to_object(bm, n, location=(0, 0, C), bevel=0.002))
    return out


def model_water_tank(col):
    bm = bmesh.new()
    cyl(bm, 0.44, 0.86, (0, 0, 0.47), "Z", STEEL, segs=28)
    for z in (0.08, 0.47, 0.86):
        cyl(bm, 0.455, 0.04, (0, 0, z), "Z", IRON, segs=28)
    cyl(bm, 0.30, 0.04, (0, 0, 0.92), "Z", IRON, segs=20)
    cyl(bm, 0.10, 0.06, (0, 0, 0.96), "Z", BRASS, segs=12)
    box(bm, (0.05, 0.02, 0.60), (0, -0.445, 0.47), GLASS)          # level glass
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        beam(bm, (0.40 * math.cos(a), 0.40 * math.sin(a), 0.0), (0.40 * math.cos(a), 0.40 * math.sin(a), 0.06), 0.06, 0.06, IRON)
    return [to_object(bm, "feWaterTank_Base", bevel=0.004)]


def volute(bm, y_in, y_out):
    """Pump casing on the axis: a drum, an inlet stub to +Y (green ring) and an outlet stub to -Y (orange ring)."""
    cyl(bm, 0.22, 0.24, (0, 0, C), "Y", PAINT, segs=24)
    for y in (-0.125, 0.125):
        cyl(bm, 0.23, 0.03, (0, y, C), "Y", IRON, segs=24)
    cyl(bm, PIPE_R, 0.5 - 0.14, (0, (0.14 + 0.5) / 2, C), "Y", STEEL, segs=14)
    cyl(bm, PIPE_R + 0.03, 0.03, (0, 0.485, C), "Y", IRON, segs=14)
    ring(bm, PIPE_R + 0.035, PIPE_R + 0.01, 0.035, (0, 0.485, C), "Y", IN, segs=14)
    cyl(bm, PIPE_R, 0.5 - 0.14, (0, -(0.14 + 0.5) / 2, C), "Y", STEEL, segs=14)
    cyl(bm, PIPE_R + 0.03, 0.03, (0, -0.485, C), "Y", IRON, segs=14)
    ring(bm, PIPE_R + 0.035, PIPE_R + 0.01, 0.035, (0, -0.485, C), "Y", OUT, segs=14)
    for sx in (-1, 1):
        beam(bm, (sx * 0.16, 0, 0.0), (sx * 0.08, 0, C - 0.18), 0.06, 0.30, IRON)
    box(bm, (0.50, 0.40, 0.03), (0, 0, 0.015), IRON)


def model_mech_pump(col):
    base = bmesh.new()
    volute(base, 0.5, -0.5)
    for sx in (-0.30, 0.30):                                        # shaft bearings on the sides
        box(base, (0.07, 0.12, C - 0.04), (sx, 0, (C - 0.04) / 2 + 0.02), IRON)
        box(base, (0.09, 0.14, 0.08), (sx, 0, C), RUST)
    out = [to_object(base, "feMechPump_Base", bevel=0.004)]
    sh = bmesh.new()   # drive shaft across the block (Blender X): a rotated object whose local Y is X
    shaft_end(sh, 0.0, -0.5)
    shaft_end(sh, 0.0, 0.5)
    gear(sh, 0.12, 0.04, 14, (0, 0.20, 0), "Y", BRASS)
    out.append(to_object(sh, "FeSpin_PumpShaft", location=(0, 0, C), rotation=(0, 0, -math.pi / 2), bevel=0.002))
    return out


def wire_anchor(col, objs, loc):
    w = bpy.data.objects.new("WireOffset", None)
    w.empty_display_type = "SPHERE"
    w.empty_display_size = 0.03
    w.location = loc
    objs.append(w)


def model_elec_pump(col):
    base = bmesh.new()
    volute(base, 0.5, -0.5)
    cyl(base, 0.15, 0.36, (0.25, 0, C), "X", (MI["feKin_Paint"]), segs=20)   # motor beside the casing
    for k in range(6):
        cyl(base, 0.155, 0.015, (0.12 + k * 0.05, 0, C), "X", IRON, segs=20)  # cooling ribs
    box(base, (0.10, 0.10, 0.08), (0.25, 0, C + 0.18), IRON)                # terminal box
    cyl(base, 0.012, 0.10, (0.25, 0, C + 0.27), "Z", BRASS, segs=8)
    objs = [to_object(base, "feElecPump_Base", bevel=0.004)]
    wire_anchor(col, objs, (0.25, 0, C + 0.33))
    return objs


def model_condenser(col):
    """Condenser, 2 wide x 2 high (centred: the game shifts an even-width model by -0.5 x, BlockShapeModelEntity.GetOffsetForMultiblock; parent column = Blender x -0.5). Upper glass
    chamber = gas (steam fill FeLevelGas), lower glass chamber = liquid (water level FeLevelLiquid, blue), a copper
    condensing coil between them and a fan on top (FeFan). Steam in at the back of the upper parent cell, water out
    at the front of the lower parent cell."""
    X0, X1 = -0.95, 0.95
    cx, w = (X0 + X1) / 2, X1 - X0
    base = bmesh.new()
    box(base, (w, 0.90, 0.12), (cx, 0, 0.06), IRON)                            # plinth
    for x in (X0 + 0.03, X1 - 0.03):
        for y in (-0.42, 0.42):
            box(base, (0.06, 0.06, 1.88), (x, y, 1.0), IRON)                     # corner posts
    def chamber(z0, z1):
        h = z1 - z0
        zc = (z0 + z1) / 2
        box(base, (w - 0.12, 0.04, h), (cx, 0.40, zc), PAINT)                    # back wall
        for x in (X0 + 0.06, X1 - 0.06):
            box(base, (0.04, 0.80, h), (x, 0, zc), PAINT)                         # side walls
        for z in (z0, z1):
            box(base, (w - 0.08, 0.84, 0.05), (cx, 0, z), IRON)                  # floor / lid
        for x in (cx - 0.48, cx, cx + 0.48):                                      # window bars (front, open glass)
            box(base, (0.03, 0.03, h), (x, -0.41, zc), IRON)
        box(base, (w - 0.08, 0.03, 0.03), (cx, -0.41, zc), IRON)
    chamber(0.15, 0.95)     # liquid
    chamber(1.05, 1.82)     # gas
    for k in range(7):                                                            # condensing coil
        ring(base, 0.16, 0.13, 0.025, (cx, 0, 0.985 + (k - 3) * 0.006), "Z", BRASS, segs=18)
    for x in (cx - 0.55, cx + 0.55):
        cyl(base, 0.03, 0.10, (x, 0, 1.0), "Z", BRASS, segs=8)
    # fan shroud on top
    ring(base, 0.36, 0.33, 0.10, (cx, 0, 1.90), "Z", IRON, segs=28)
    cyl(base, 0.05, 0.10, (cx, 0, 1.90), "Z", IRON, segs=12)
    # ports: steam in at the back of the upper parent cell (white), water out at the front of the lower parent cell
    inlet_stub(base, (-0.5, 0.5, 1.0 + C), "Y", 1, GASC)
    inlet_stub(base, (-0.5, -0.5, C), "Y", -1, WATERC)
    objs = [to_object(base, "feCondenser_Base", bevel=0.004)]
    # liquid level: pivot at the chamber floor, height grows with local Z (Unity Y)
    liq = bmesh.new()
    box(liq, (w - 0.20, 0.72, 0.74), (0, 0, 0.37), WATERC)
    objs.append(to_object(liq, "FeLevelLiquid", location=(cx, 0, 0.18)))
    gas = bmesh.new()
    box(gas, (w - 0.20, 0.72, 0.70), (0, 0, 0.35), GASC)
    objs.append(to_object(gas, "FeLevelGas", location=(cx, 0, 1.08)))
    fan = bmesh.new()                                                             # blades in the local XZ plane
    for k in range(5):
        a_ = k * 2 * math.pi / 5
        m = Matrix.Rotation(a_, 4, "Y") @ Matrix.Translation((0.16, 0, 0))
        r = bmesh.ops.create_cube(fan, size=1.0, calc_uvs=True)
        _finish(fan, STEEL, m @ Matrix.Rotation(math.radians(20), 4, "X") @ Matrix.Diagonal((0.28, 0.02, 0.10, 1.0)), r["verts"])
    objs.append(to_object(fan, "FeFan_Condenser", location=(cx, 0, 1.92), rotation=(math.pi / 2, 0, 0)))
    wire_anchor(col, objs, (X1 - 0.15, 0.30, 1.98))
    return objs

def inlet_stub(bm, face_pt, axis, sign, ring_mat):
    """Pipe stub ending flush with a block face (face_pt), along axis X/Y/Z, pointing outward by sign."""
    v = Vector((1, 0, 0)) if axis == "X" else (Vector((0, 1, 0)) if axis == "Y" else Vector((0, 0, 1)))
    v = v * sign
    fp = Vector(face_pt)
    cyl(bm, PIPE_R, 0.24, fp - v * 0.12, axis, STEEL, segs=14)
    cyl(bm, PIPE_R + 0.03, 0.03, fp - v * 0.015, axis, IRON, segs=14)
    ring(bm, PIPE_R + 0.035, PIPE_R + 0.01, 0.035, fp - v * 0.015, axis, ring_mat, segs=14)


def conveyor_port(bm, face_pt, normal):
    """Conveyor input frame (Art/CONVEYOR_PORTS.md): 0.36 x 0.22 opening, iron frame, green top bar, a chute."""
    n = Vector(normal).normalized()
    up = Vector((0, 0, 1))
    m = Matrix((n.cross(up), n, up)).transposed().to_4x4()
    m.translation = Vector(face_pt)
    T = Matrix.Translation
    w, h, f = 0.36, 0.22, 0.045
    def bx(size, mat_, tm):
        r = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)
        _finish(bm, mat_, m @ tm @ Matrix.Diagonal((*size, 1.0)), r["verts"])
    for sx in (-1, 1):
        bx((f, 0.04, h + 2 * f), IRON, T((sx * (w / 2 + f / 2), -0.02, 0)))
    bx((w + 2 * f, 0.04, f), IRON, T((0, -0.02, -(h / 2 + f / 2))))
    bx((w + 2 * f, 0.04, f), IN, T((0, -0.02, h / 2 + f / 2)))
    bx((w, 0.02, h), (MI["feKin_Iron"]), T((0, -0.20, 0)))
    for sx in (-1, 1):
        bx((0.02, 0.20, h + 0.04), IRON, T((sx * (w / 2 + 0.01), -0.10, 0)))


def model_big_steam_engine(col):
    """3x3 base, 2 high. Origin = floor centre of the PARENT cell (bottom centre). Water in under the centre and on
    the left / right / back of the bottom layer (Blender +X / -X / +Y = Unity -X / +X / -Z), steam out over the top
    centre, torque out of the front centre of the bottom layer (Blender -Y face). Conveyor inputs on the sides of
    the upper layer. Two pistons (FePiston_*) and steam puffs (FeSteamPuff_*) for the mod's animators."""
    base = bmesh.new()
    box(base, (2.96, 2.96, 0.10), (0, 0, 0.05), IRON)                          # bed
    cyl(base, 0.62, 2.40, (0, 0.55, 0.95), "X", RUST, segs=32)                 # boiler
    for x in (-1.15, -0.4, 0.4, 1.15):
        cyl(base, 0.64, 0.05, (x, 0.55, 0.95), "X", IRON, segs=32)
    for x in (-0.9, 0.9):
        box(base, (0.20, 1.0, 0.34), (x, 0.55, 0.26), IRON)
    box(base, (0.70, 0.60, 0.70), (-1.05, -0.95, 0.45), IRON)                  # firebox (front left)
    box(base, (0.30, 0.04, 0.26), (-1.05, -1.26, 0.45), BRASS)
    cyl(base, 0.22, 0.30, (0, 0.55, 1.70), "Z", BRASS, segs=20)                # steam dome
    beam(base, (0, 0.55, 1.80), (0, 0.0, 1.80), 0.12, 0.12, STEEL)
    inlet_stub(base, (0, 0, 2.0), "Z", 1, OUT)                                 # steam out (top centre)
    cyl(base, 0.12, 0.70, (1.15, 1.10, 1.55), "Z", IRON, segs=16)              # chimney
    # water inlets: under the centre and on 3 sides of the bottom layer
    inlet_stub(base, (0, 0, 0.0), "Z", -1, IN)
    inlet_stub(base, (1.5, 0, C), "X", 1, IN)
    inlet_stub(base, (-1.5, 0, C), "X", -1, IN)
    inlet_stub(base, (0, 1.5, C), "Y", 1, IN)
    for v in ((0.35, 0, C), (-0.35, 0, C)):                                    # feed pipes to the boiler
        beam(base, (v[0] * 4.0, 0, C), (v[0] * 1.2, 0.30, 0.55), 0.09, 0.09, STEEL)
    beam(base, (0, 1.30, C), (0, 0.9, 0.60), 0.09, 0.09, STEEL)
    # conveyor inputs on both sides of the upper layer
    conveyor_port(base, (1.5, 0, 1.25), (1, 0, 0))
    conveyor_port(base, (-1.5, 0, 1.25), (-1, 0, 0))
    for sx in (-1, 1):
        box(base, (0.36, 0.60, 0.40), (sx * 1.15, 0, 1.25), WOOD)              # hoppers behind the ports
    # two cylinders (front) and their crosshead guides
    for sx in (-1, 1):
        cyl(base, 0.17, 0.55, (sx * 0.75, -0.10, C), "Y", STEEL, segs=20)
        cyl(base, 0.19, 0.04, (sx * 0.75, -0.37, C), "Y", IRON, segs=20)
        box(base, (0.12, 0.50, 0.06), (sx * 0.75, -0.70, C - 0.12), IRON)
        box(base, (0.20, 0.50, 0.30), (sx * 0.75, -0.10, 0.20), IRON)          # cylinder stand
    for y in (-1.25, -0.55):                                                   # output shaft bearings
        box(base, (0.18, 0.12, 0.44), (0, y, 0.30), IRON)
        box(base, (0.20, 0.14, 0.10), (0, y, C), RUST)
    out = [to_object(base, "feSteamEngine_Base", bevel=0.005)]
    w = bmesh.new()
    shaft_end(w, 0.0, -1.5)
    ring(w, 0.45, 0.39, 0.10, (0, -0.95, 0), "Y", IRON, segs=40)               # flywheel
    cyl(w, 0.08, 0.14, (0, -0.95, 0), "Y", IRON, segs=16)
    for k in range(8):
        a_ = k * math.pi / 4
        m = Matrix.Rotation(a_, 4, "Y") @ Matrix.Translation((0.23, -0.95, 0))
        r = bmesh.ops.create_cube(w, size=1.0, calc_uvs=True)
        _finish(w, IRON, m @ Matrix.Diagonal((0.32, 0.04, 0.05, 1.0)), r["verts"])
    cyl(w, 0.14, 0.04, (0, -0.55, 0), "Y", RUST, segs=20)                     # crank disc
    out.append(to_object(w, "FeSpin_SteamFlywheel", location=(0, 0, C), bevel=0.002))
    for i, sx in enumerate((-1, 1)):                                           # pistons: rod + crosshead
        pb = bmesh.new()
        cyl(pb, 0.03, 0.50, (0, 0, 0), "Y", STEEL, segs=10)
        box(pb, (0.12, 0.10, 0.10), (0, -0.25, 0), BRASS)
        cyl(pb, 0.15, 0.06, (0, 0.25, 0), "Y", IRON, segs=16)                  # piston head (in the cylinder)
        out.append(to_object(pb, "FePiston_" + str(i + 1), location=(sx * 0.75, -0.55, C), bevel=0.0))
    for i in range(6):                                                         # steam puffs over the outlet
        pf = bmesh.new()
        bmesh.ops.create_icosphere(pf, subdivisions=1, radius=0.14)
        for f_ in pf.faces:
            f_.material_index = GLASS
        out.append(to_object(pf, "FeSteamPuff_" + str(i + 1), location=(0.05 * (i % 3 - 1), 0.05 * (i % 2), 2.10)))
    return out


def motor_body(bm, r, length, paint, z, y0=0.0):
    """Electric motor along Blender Y: drum, cooling ribs, end bells, terminal box."""
    cyl(bm, r, length, (0, y0, z), "Y", paint, segs=24)
    n = int(length / 0.07)
    for k in range(n):
        y = y0 - length / 2 + 0.05 + k * 0.07
        cyl(bm, r + 0.02, 0.02, (0, y, z), "Y", IRON, segs=24)
    for s_ in (-1, 1):
        cyl(bm, r * 0.85, 0.06, (0, y0 + s_ * (length / 2 + 0.03), z), "Y", IRON, segs=24)
    box(bm, (r * 0.7, r * 0.6, r * 0.4), (0, y0, z + r + r * 0.2), IRON)


def model_electric_motor(col):
    base = bmesh.new()
    motor_body(base, 0.22, 0.56, PAINT, C)
    for sy in (-0.18, 0.18):
        box(base, (0.46, 0.08, C - 0.18), (0, sy, (C - 0.18) / 2 + 0.01), IRON)    # feet
    box(base, (0.50, 0.50, 0.03), (0, 0, 0.015), IRON)
    objs = [to_object(base, "feElectricMotor_Base", bevel=0.004)]
    rot = bmesh.new()
    shaft_end(rot, 0.0, -0.5)
    shaft_end(rot, 0.0, 0.5)
    objs.append(to_object(rot, "FeSpin_Motor1", location=(0, 0, C), bevel=0.002))
    wire_anchor(col, objs, (0, 0, C + 0.36))
    return objs


def model_electric_motor2(col):
    base = bmesh.new()
    motor_body(base, 0.30, 0.66, RUST, C)
    for y in (-0.18, 0.0, 0.18):
        ring(base, 0.33, 0.30, 0.04, (0, y, C), "Y", BRASS, segs=24)                # copper coil bands
    for sy in (-0.22, 0.22):
        box(base, (0.60, 0.10, C - 0.25), (0, sy, (C - 0.25) / 2 + 0.01), IRON)
    box(base, (0.70, 0.70, 0.04), (0, 0, 0.02), IRON)
    objs = [to_object(base, "feElectricMotor2_Base", bevel=0.004)]
    rot = bmesh.new()
    shaft_end(rot, 0.0, -0.5)
    shaft_end(rot, 0.0, 0.5)
    objs.append(to_object(rot, "FeSpin_Motor2", location=(0, 0, C), bevel=0.002))
    wire_anchor(col, objs, (0, 0, C + 0.48))
    return objs


def model_electric_motor3(col):
    """Industrial Electric Motor, 3x3 base, 2 high. Big motor on top (axis z = 1.05), reduction gear case at the
    front down to the output shaft (z = 0.5) out of the front centre of the bottom layer."""
    base = bmesh.new()
    box(base, (2.96, 2.96, 0.10), (0, 0, 0.05), IRON)
    motor_body(base, 0.72, 2.0, PAINT, 1.05, y0=0.35)
    for y in (-0.35, 0.05, 0.45, 0.85):
        ring(base, 0.76, 0.72, 0.06, (0, y, 1.05), "Y", BRASS, segs=36)
    for x in (-0.6, 0.6):
        for y in (-0.3, 1.0):
            box(base, (0.20, 0.30, 0.40), (x, y, 0.30), IRON)                   # motor feet
    box(base, (0.70, 0.40, 1.10), (0, -0.95, 0.65), IRON)                     # reduction gear case (front)
    box(base, (0.74, 0.44, 0.05), (0, -0.95, 1.20), RUST)
    for sx in (-1, 1):                                                         # cooling fans boxes on the sides
        box(base, (0.30, 1.2, 0.80), (sx * 1.15, 0.35, 0.60), PAINT)
        for k in range(5):
            box(base, (0.02, 1.0, 0.04), (sx * 1.31, 0.35, 0.30 + k * 0.13), IRON)
    box(base, (0.40, 0.40, 0.30), (0, 0.35, 1.92), IRON)                       # terminal box on top
    objs = [to_object(base, "feElectricMotor3_Base", bevel=0.005)]
    outp = bmesh.new()
    shaft_end(outp, -1.10, -1.5)
    objs.append(to_object(outp, "FeSpin_Motor3Out", location=(0, 0, C), bevel=0.002))
    fan = bmesh.new()                                                          # rotor fan at the back end
    cyl(fan, 0.05, 0.10, (0, 0, 0), "Y", STEEL, segs=10)
    for k in range(6):
        a_ = k * math.pi / 3
        m = Matrix.Rotation(a_, 4, "Y") @ Matrix.Translation((0.30, 0, 0))
        r = bmesh.ops.create_cube(fan, size=1.0, calc_uvs=True)
        _finish(fan, STEEL, m @ Matrix.Diagonal((0.50, 0.02, 0.12, 1.0)), r["verts"])
    objs.append(to_object(fan, "FeSpin_Motor3Fan", location=(0, 1.42, 1.05), bevel=0.0))
    wire_anchor(col, objs, (0, 0.35, 2.10))
    return objs



def model_dynamo(col):
    """Dynamo: field housing with copper windings on feet, a commutator, brushes and an insulator for the wire;
    the armature shaft goes through the block (both ends) and spins."""
    base = bmesh.new()
    cyl(base, 0.26, 0.50, (0, 0, C), "Y", PAINT, segs=24)
    for y in (-0.16, -0.05, 0.06, 0.17):
        ring(base, 0.29, 0.26, 0.05, (0, y, C), "Y", BRASS, segs=24)            # windings
    for s_ in (-1, 1):
        cyl(base, 0.22, 0.05, (0, s_ * 0.28, C), "Y", IRON, segs=24)            # end shields
    for sy in (-0.18, 0.18):
        box(base, (0.52, 0.10, C - 0.22), (0, sy, (C - 0.22) / 2 + 0.01), IRON)
    box(base, (0.60, 0.60, 0.03), (0, 0, 0.015), IRON)
    box(base, (0.12, 0.10, 0.10), (0, 0, C + 0.30), IRON)                       # terminal + insulator
    for k in range(3):
        cyl(base, 0.035, 0.02, (0, 0, C + 0.37 + k * 0.045), "Z", GLASS, segs=12, r2=0.024)
    objs = [to_object(base, "feDynamo_Base", bevel=0.004)]
    arm = bmesh.new()
    shaft_end(arm, 0.0, -0.5)
    shaft_end(arm, 0.0, 0.5)
    cyl(arm, 0.08, 0.06, (0, -0.36, 0), "Y", BRASS, segs=16)                    # commutator
    objs.append(to_object(arm, "FeSpin_DynamoArmature", location=(0, 0, C), bevel=0.002))
    wire_anchor(col, objs, (0, 0, C + 0.52))
    return objs


def model_dynamo2(col):
    """Industrial Dynamo, 3x3 base, 2 high: a big generator drum on top (axis z = 1.05), a gear case at the front
    down to the input shaft (front centre of the bottom layer, z = 0.5), cooling grilles, insulators on top."""
    base = bmesh.new()
    box(base, (2.96, 2.96, 0.10), (0, 0, 0.05), IRON)
    cyl(base, 0.80, 2.0, (0, 0.35, 1.05), "Y", PAINT, segs=36)
    for y in (-0.45, -0.1, 0.25, 0.6, 0.95):
        ring(base, 0.85, 0.80, 0.10, (0, y, 1.05), "Y", BRASS, segs=36)         # windings
    for s_ in (-1, 1):
        cyl(base, 0.70, 0.08, (0, 0.35 + s_ * 1.04, 1.05), "Y", IRON, segs=36)
    for x in (-0.6, 0.6):
        for y in (-0.3, 1.0):
            box(base, (0.20, 0.30, 0.40), (x, y, 0.30), IRON)
    box(base, (0.70, 0.40, 1.10), (0, -0.95, 0.65), IRON)                     # gear case (front)
    for sx in (-1, 1):
        box(base, (0.24, 1.6, 0.70), (sx * 1.20, 0.35, 0.55), PAINT)            # rectifier cabinets
        for k in range(6):
            box(base, (0.02, 1.4, 0.04), (sx * 1.33, 0.35, 0.30 + k * 0.10), IRON)
    for x in (-0.3, 0.0, 0.3):                                                  # insulators on top
        for k in range(3):
            cyl(base, 0.06, 0.03, (x, 0.35, 1.90 + k * 0.06), "Z", GLASS, segs=12, r2=0.04)
    objs = [to_object(base, "feDynamo2_Base", bevel=0.005)]
    inp = bmesh.new()
    shaft_end(inp, -1.10, -1.5)
    objs.append(to_object(inp, "FeSpin_Dynamo2In", location=(0, 0, C), bevel=0.002))
    rotor = bmesh.new()                                                        # visible rotor end at the back
    cyl(rotor, 0.12, 0.10, (0, 0, 0), "Y", STEEL, segs=16)
    for k in range(4):
        a_ = k * math.pi / 2
        m = Matrix.Rotation(a_, 4, "Y") @ Matrix.Translation((0.30, 0, 0))
        r = bmesh.ops.create_cube(rotor, size=1.0, calc_uvs=True)
        _finish(rotor, BRASS, m @ Matrix.Diagonal((0.45, 0.03, 0.10, 1.0)), r["verts"])
    objs.append(to_object(rotor, "FeSpin_Dynamo2Rotor", location=(0, 1.44, 1.05), bevel=0.0))
    wire_anchor(col, objs, (0, 0.35, 2.12))
    return objs


def model_bus(col):
    """Power Bus: a cabinet with three copper bus bars across the top and a row of insulators (one per incoming
    dynamo wire, purely visual) plus the outgoing insulator."""
    base = bmesh.new()
    box(base, (0.70, 0.50, 0.70), (0, 0, 0.40), PAINT)
    box(base, (0.74, 0.54, 0.04), (0, 0, 0.77), IRON)
    box(base, (0.74, 0.54, 0.05), (0, 0, 0.05), IRON)
    for y in (-0.15, 0.0, 0.15):
        box(base, (0.66, 0.03, 0.03), (0, y, 0.81), BRASS)                      # copper bus bars
    for x in (-0.25, -0.08, 0.08):
        for k in range(2):
            cyl(base, 0.03, 0.02, (x, 0.18, 0.84 + k * 0.035), "Z", GLASS, segs=10, r2=0.02)
    for k in range(3):
        cyl(base, 0.045, 0.025, (0.25, -0.15, 0.84 + k * 0.045), "Z", GLASS, segs=12, r2=0.03)
    box(base, (0.30, 0.02, 0.30), (0, -0.26, 0.45), GLASS)                     # inspection window
    objs = [to_object(base, "feBus_Base", bevel=0.004)]
    wire_anchor(col, objs, (0.25, -0.15, 1.0))
    return objs


def _belt_rollers(objs, back_z, front_z):
    """Spin parts of a belt: the spin axis (Unity local +Z) is the part's Blender local -Y, so the rollers are built
    along local Y and turned 90 degrees about Z to lie across the block (world X). The drive roller sits at shaft
    height (z = C) with hubs on both side faces, where a shaft plugs in."""
    drive = bmesh.new()
    cyl(drive, 0.05, 0.96, (0, 0, 0), "Y", STEEL, segs=16)
    for sy in (-1, 1):
        cyl(drive, 0.07, 0.04, (0, sy * 0.48, 0), "Y", BRASS, segs=16)
        for k in range(4):
            a_ = k * math.pi / 2
            box(drive, (0.02, 0.03, 0.10), (0.045 * math.cos(a_), sy * 0.49, 0.045 * math.sin(a_)), STEEL,
                Matrix.Rotation(-a_, 4, "Y"))
    objs.append(to_object(drive, "FeSpin_BeltDrive", location=(0, 0, C), rotation=(0, 0, math.pi / 2)))
    for name, y, z in (("FeSpin_BeltRollerFront", -0.45, front_z), ("FeSpin_BeltRollerBack", 0.45, back_z)):
        r = bmesh.new()
        cyl(r, 0.045, 0.80, (0, 0, 0), "Y", STEEL, segs=14)
        for k in range(3):
            a_ = k * 2 * math.pi / 3
            box(r, (0.012, 0.76, 0.06), (0.02 * math.cos(a_), 0, 0.02 * math.sin(a_)), IRON,
                Matrix.Rotation(-a_, 4, "Y"))
        objs.append(to_object(r, name, location=(0, y, z), rotation=(0, 0, math.pi / 2)))


def arc_solid(bm, pt, r0, r1, a0, a1, z0, z1, n, mat):
    """A solid ring sector: radii r0..r1, angles a0..a1 (pt(r, th) -> (x, y)), heights z0..z1, n segments."""
    rings = []
    for k in range(n + 1):
        th = a0 + (a1 - a0) * k / n
        ring_v = []
        for r, z in ((r0, z0), (r0, z1), (r1, z1), (r1, z0)):
            x, y = pt(r, th)
            ring_v.append(bm.verts.new((x, y, z)))
        rings.append(ring_v)
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


def model_conveyor(col):
    """Conveyor belt (D10). Travel = the block front = Unity +Z = Blender -Y. Unity left (-X) = Blender +X.
    BeltShape (Belt.cs) shows one of three looks:
      straight: FeBeltBed + FeBeltSlats (slide along the travel) + rollers, FeRail_L/R (hidden where another belt
                joins), FeBeltEnd (end stop when nothing is in front);
      curve:    FeCurveSet_L/R (quarter-ring floor around the back corner of that side, arched outer rail, inner
                fillet) + FeCurveSlats_L/R (wedges turning about the vertical axis at the corner; radius 0.5 = the
                items' arc);
      junction (2 or 3 outputs): FeJunction (transfer table with ball casters), FeJunctionPosts (corner posts),
                FeJunctionWedge (V divider when it splits to both sides only), rails / end stop as straight."""
    base = bmesh.new()
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(base, (0.06, 0.06, 0.53), (sx * 0.44, sy * 0.42, 0.265), IRON)  # legs
        box(base, (0.06, 0.84, 0.05), (sx * 0.44, 0, 0.12), IRON)               # lower stringer
        cyl(base, 0.09, 0.03, (sx * 0.47, 0, C), "X", IRON, segs=20)              # bearing plates
    box(base, (0.82, 0.10, 0.04), (0, 0.42, 0.12), IRON)                          # cross braces
    box(base, (0.82, 0.10, 0.04), (0, -0.42, 0.12), IRON)
    objs = [to_object(base, "feConveyor_Base", bevel=0.003)]
    bed = bmesh.new()
    box(bed, (0.80, 0.98, 0.02), (0, 0, 0.565), IRON)
    objs.append(to_object(bed, "FeBeltBed"))
    for name, sx in (("FeRail_L", 1), ("FeRail_R", -1)):
        r = bmesh.new()
        box(r, (0.06, 1.0, 0.10), (sx * 0.44, 0, 0.58), PAINT)
        for dy, h in ((0.10, 0.09), (0.05, 0.06), (0.0, 0.03)):                  # arrows toward -Y (the front)
            box(r, (0.012, 0.05, h), (sx * 0.476, -0.05 - dy, 0.58), OUT)
            box(r, (0.012, 0.05, h), (sx * 0.476, 0.30 - dy, 0.58), OUT)
        objs.append(to_object(r, name, bevel=0.002))
    end = bmesh.new()
    box(end, (0.82, 0.04, 0.12), (0, -0.47, 0.64), PAINT)
    box(end, (0.82, 0.045, 0.03), (0, -0.47, 0.69), OUT)
    objs.append(to_object(end, "FeBeltEnd", bevel=0.002))
    sl = bmesh.new()
    for k in range(7):
        box(sl, (0.78, 0.075, 0.03), (0, -0.375 + k * 0.125, 0.592), RUST)
    objs.append(to_object(sl, "FeBeltSlats"))
    # ---- curve look
    Q = math.pi / 2
    for side, sx in (("L", 1), ("R", -1)):
        cx, cy = sx * 0.5, 0.5                                                      # back corner of that side
        def world_pt(r, th, cx=cx, cy=cy, sx=sx):
            return (cx - sx * r * math.cos(th), cy - r * math.sin(th))
        def local_pt(r, th, sx=sx):
            return (-sx * r * math.cos(th), -r * math.sin(th))
        st = bmesh.new()
        arc_solid(st, world_pt, 0.10, 0.90, 0, Q, 0.555, 0.575, 18, IRON)          # floor
        arc_solid(st, world_pt, 0.90, 0.96, 0, Q, 0.53, 0.63, 18, PAINT)           # outer rail
        arc_solid(st, world_pt, 0.04, 0.10, 0, Q, 0.53, 0.63, 6, PAINT)            # inner fillet
        for th in (Q * 0.3, Q * 0.7):                                                # arrows along the turn
            for k, h in enumerate((0.07, 0.045, 0.02)):
                arc_solid(st, world_pt, 0.96, 0.972, th + k * 0.06, th + k * 0.06 + 0.05, 0.58 - h / 2,
                          0.58 + h / 2, 1, OUT)
        objs.append(to_object(st, "FeCurveSet_" + side, bevel=0.0))
        cs = bmesh.new()
        n = 9
        for k in range(n):
            th = (k + 0.5) * Q / n
            arc_solid(cs, local_pt, 0.12, 0.88, th - 0.035, th + 0.035, 0.577, 0.607, 2, RUST)
        objs.append(to_object(cs, "FeCurveSlats_" + side, location=(cx, cy, 0)))
    # ---- junction look
    jn = bmesh.new()
    box(jn, (0.84, 0.92, 0.02), (0, 0, 0.565), IRON)
    for ix in range(4):
        for iy in range(4):
            x, y = -0.30 + ix * 0.2, -0.30 + iy * 0.2
            cyl(jn, 0.045, 0.012, (x, y, 0.580), "Z", IRON, segs=10)
            cyl(jn, 0.030, 0.030, (x, y, 0.596), "Z", STEEL, segs=10, r2=0.012)     # ball casters
    objs.append(to_object(jn, "FeJunction"))
    po = bmesh.new()
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(po, 0.05, 0.14, (sx * 0.45, sy * 0.45, 0.61), "Z", PAINT, segs=12)
            cyl(po, 0.052, 0.025, (sx * 0.45, sy * 0.45, 0.69), "Z", OUT, segs=12)
    objs.append(to_object(po, "FeJunctionPosts"))
    wd = bmesh.new()
    for sx in (-1, 1):
        x0, y0, x1, y1 = 0.0, -0.10, sx * 0.42, -0.46
        L = math.hypot(x1 - x0, y1 - y0)
        ang = math.atan2(y1 - y0, x1 - x0)
        box(wd, (L, 0.04, 0.10), ((x0 + x1) / 2, (y0 + y1) / 2, 0.62), PAINT, Matrix.Rotation(ang, 4, "Z"))
    cyl(wd, 0.035, 0.12, (0, -0.10, 0.62), "Z", OUT, segs=12)
    objs.append(to_object(wd, "FeJunctionWedge"))
    _belt_rollers(objs, 0.56, 0.56)
    return objs


def model_conveyor_ramp(col):
    """Conveyor ramp (D10): takes items at its back (belt height 0.62) and lifts them one block up to its front
    (1.62 = the surface of a belt one block higher and one forward). 45 degrees; the slats slide up the slope."""
    base = bmesh.new()
    slope = Matrix.Rotation(-math.pi / 4, 4, "X")                                  # -Y (front) end goes up
    L = math.sqrt(2.0)
    for sx in (-1, 1):
        box(base, (0.06, L, 0.10), (sx * 0.44, 0, 1.08), PAINT, slope)              # side rails
        for dy in (0.30, -0.25):                                                     # arrows up the slope
            for k, h in enumerate((0.09, 0.06, 0.03)):
                y = dy - 0.05 * k
                box(base, (0.012, 0.05, h), (sx * 0.476, y, 1.08 + (0.0 - y)), OUT, slope)
        box(base, (0.06, 0.06, 0.53), (sx * 0.44, 0.42, 0.265), IRON)              # back legs
        box(base, (0.06, 0.06, 1.48), (sx * 0.44, -0.42, 0.74), IRON)              # front legs
        box(base, (0.06, 0.84, 0.05), (sx * 0.44, 0, 0.12), IRON)
        cyl(base, 0.09, 0.03, (sx * 0.47, 0, C), "X", IRON, segs=20)               # bearing plates
    box(base, (0.82, 0.10, 0.04), (0, 0.42, 0.12), IRON)
    box(base, (0.82, 0.10, 0.04), (0, -0.42, 0.12), IRON)
    box(base, (0.80, L, 0.02), (0, 0, 1.065), IRON, slope)                          # bed
    objs = [to_object(base, "feConveyorRamp_Base", bevel=0.003)]
    sl = bmesh.new()
    for k in range(10):
        y = 0.5 - 0.0625 - k * 0.0884
        if y < -0.45:
            break
        z = 0.62 + (0.5 - y) - 0.028
        box(sl, (0.78, 0.075, 0.03), (0, y, z), RUST, slope)
    objs.append(to_object(sl, "FeBeltSlats"))
    _belt_rollers(objs, 0.56, 1.56)
    return objs


def model_funnel(col):
    """Funnel (D10 T2): its back (Blender +Y = Unity -Z) touches a crate or a machine, its front (Blender -Y) drops
    the items onto the belt in front at belt height (0.62). A hopper narrowing to a chute; arrows point out."""
    base = bmesh.new()
    box(base, (0.86, 0.06, 0.86), (0, 0.46, 0.50), IRON)                          # back plate on the source
    for k, (w, h, y) in enumerate(((0.74, 0.74, 0.36), (0.58, 0.58, 0.24), (0.42, 0.44, 0.12), (0.30, 0.30, 0.0))):
        box(base, (w, 0.12, h), (0, y, 0.55 + k * 0.01), PAINT)                      # stepped hopper
    box(base, (0.30, 0.42, 0.06), (0, -0.25, 0.66), STEEL)                          # chute floor
    for sx in (-1, 1):
        box(base, (0.03, 0.42, 0.12), (sx * 0.165, -0.25, 0.71), STEEL)
    for k, h in enumerate((0.10, 0.07, 0.04)):                                       # arrows toward the front
        box(base, (0.012, 0.04, h), (0.38, 0.30 - k * 0.04, 0.55), OUT)
        box(base, (0.012, 0.04, h), (-0.38, 0.30 - k * 0.04, 0.55), OUT)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(base, (0.05, 0.05, 0.40), (sx * 0.38, 0.30 + sy * 0.10, 0.20), IRON)   # feet
    return [to_object(base, "feFunnel_Base", bevel=0.003)]


def model_conveyor_down(col):
    """Conveyor down ramp (D10): takes items from the belt one block UP behind it (back end at 1.62) and lowers them
    to its front at belt height (0.62). The mirror of the up ramp; the slats slide down the slope."""
    base = bmesh.new()
    slope = Matrix.Rotation(math.pi / 4, 4, "X")                                   # +Y (back) end goes up
    L = math.sqrt(2.0)
    for sx in (-1, 1):
        box(base, (0.06, L, 0.10), (sx * 0.44, 0, 1.08), PAINT, slope)              # side rails
        for dy in (0.25, -0.30):                                                     # arrows down the slope
            for k, h in enumerate((0.03, 0.06, 0.09)):
                y = dy - 0.05 * k
                box(base, (0.012, 0.05, h), (sx * 0.476, y, 1.08 + y), OUT, slope)
        box(base, (0.06, 0.06, 1.48), (sx * 0.44, 0.42, 0.74), IRON)               # back legs (tall)
        box(base, (0.06, 0.06, 0.53), (sx * 0.44, -0.42, 0.265), IRON)             # front legs
        box(base, (0.06, 0.84, 0.05), (sx * 0.44, 0, 0.12), IRON)
        cyl(base, 0.09, 0.03, (sx * 0.47, 0, C), "X", IRON, segs=20)               # bearing plates
    box(base, (0.82, 0.10, 0.04), (0, 0.42, 0.12), IRON)
    box(base, (0.82, 0.10, 0.04), (0, -0.42, 0.12), IRON)
    box(base, (0.80, L, 0.02), (0, 0, 1.065), IRON, slope)                          # bed
    objs = [to_object(base, "feConveyorDown_Base", bevel=0.003)]
    sl = bmesh.new()
    for k in range(10):
        y = -0.5 + 0.0625 + k * 0.0884
        if y > 0.45:
            break
        z = 0.62 + (0.5 + y) - 0.028
        box(sl, (0.78, 0.075, 0.03), (0, y, z), RUST, slope)
    objs.append(to_object(sl, "FeBeltSlats"))
    _belt_rollers(objs, 1.56, 0.56)
    return objs


def model_fluid_filler(col):
    """Filler (D9): a drum with a hopper on top (items in by hand or belt) and an outlet stub at its front (Blender -Y)
    that pours the fluid into a pipe. Orange band = items in."""
    base = bmesh.new()
    box(base, (0.84, 0.84, 0.06), (0, 0, 0.03), IRON)
    cyl(base, 0.36, 0.62, (0, 0.04, 0.38), "Z", PAINT, segs=28)                    # drum
    for z in (0.12, 0.38, 0.64):
        ring(base, 0.375, 0.355, 0.035, (0, 0.04, z), "Z", IRON, segs=28)
    for k, (w, h) in enumerate(((0.56, 0.10), (0.44, 0.08), (0.32, 0.06))):         # hopper
        box(base, (w, w, h), (0, 0.04, 0.74 + k * 0.08), STEEL)
    box(base, (0.58, 0.58, 0.03), (0, 0.04, 0.70), OUT)
    inlet_stub(base, (0, -0.5, C), "Y", -1, IN)
    return [to_object(base, "feFluidFiller_Base", bevel=0.003)]


def model_fluid_bottler(col):
    """Bottler (D9): an inlet stub at its back (Blender +Y) takes the fluid; a tank with a gauge window, a filling
    nozzle and a chute at its front (Blender -Y) that drops the items on the belt in front (height 0.62)."""
    base = bmesh.new()
    box(base, (0.84, 0.84, 0.06), (0, 0, 0.03), IRON)
    box(base, (0.70, 0.46, 0.80), (0, 0.16, 0.46), PAINT)                          # tank body
    box(base, (0.12, 0.02, 0.50), (0.22, -0.08, 0.46), GLASS)                      # level window
    box(base, (0.74, 0.50, 0.04), (0, 0.16, 0.88), IRON)
    cyl(base, 0.03, 0.22, (0, -0.16, 0.80), "Z", STEEL, segs=10)                   # nozzle
    box(base, (0.34, 0.40, 0.05), (0, -0.28, 0.66), STEEL)                          # chute to the belt
    for sx in (-1, 1):
        box(base, (0.03, 0.40, 0.10), (sx * 0.185, -0.28, 0.70), STEEL)
    box(base, (0.36, 0.03, 0.03), (0, -0.47, 0.72), OUT)
    inlet_stub(base, (0, 0.5, C), "Y", 1, IN)
    return [to_object(base, "feFluidBottler_Base", bevel=0.003)]


# ---------------------------------------------------------------- F8.1 metallurgy
def chute_arm(bm, v):
    """One arm of the Metal Chute from the core to the block face along v (Blender axis vector): an open U trough
    with glowing metal in it; up / down it is a closed square duct (the metal falls through)."""
    v = Vector(v)
    mid = v * 0.31
    L = 0.38
    if v.z:
        box(bm, (0.20, 0.20, L), (0, 0, C + mid.z), IRON)
        box(bm, (0.24, 0.24, 0.04), (0, 0, C + v.z * 0.48), STEEL)
        return
    along_x = bool(v.x)
    size = (L, 0.22, 0.03) if along_x else (0.22, L, 0.03)
    box(bm, size, (mid.x, mid.y, C - 0.08), IRON)                                   # floor
    for sgn in (-1, 1):
        wall = (L, 0.03, 0.14) if along_x else (0.03, L, 0.14)
        off = (0, sgn * 0.11, 0) if along_x else (sgn * 0.11, 0, 0)
        box(bm, wall, (mid.x + off[0], mid.y + off[1], C - 0.02), IRON)            # walls
    metal = (L, 0.17, 0.02) if along_x else (0.17, L, 0.02)
    box(bm, metal, (mid.x, mid.y, C - 0.055), MOLTEN)                               # the metal
    lip = (0.03, 0.26, 0.18) if along_x else (0.26, 0.03, 0.18)
    box(bm, lip, (v.x * 0.485, v.y * 0.485, C - 0.03), STEEL)                       # flange at the face


def model_metal_chute(col):
    """Metal Chute (F8.1): a pipe for molten metal. Core basin at the block centre + six arms named like the pipe's
    (FeArm_*, shown by PipeArms only toward chutes and metal ports)."""
    core = bmesh.new()
    box(core, (0.26, 0.26, 0.04), (0, 0, -0.08), IRON)
    for sx in (-1, 1):
        box(core, (0.03, 0.26, 0.14), (sx * 0.125, 0, -0.02), IRON)
        box(core, (0.26, 0.03, 0.14), (0, sx * 0.125, -0.02), IRON)
    box(core, (0.22, 0.22, 0.02), (0, 0, -0.055), MOLTEN)
    root = bpy.data.objects.new("feMetalChute_Base", None)
    out = [root, to_object(core, "feMetalChute_Core", location=(0, 0, C), bevel=0.003)]
    names = {"FeArm_PX": (-1, 0, 0), "FeArm_NX": (1, 0, 0), "FeArm_PY": (0, 0, 1), "FeArm_NY": (0, 0, -1),
             "FeArm_PZ": (0, -1, 0), "FeArm_NZ": (0, 1, 0)}
    for n, v in names.items():
        bm = bmesh.new()
        chute_arm(bm, v)
        out.append(to_object(bm, n, bevel=0.002))
    return out


def model_caster(col):
    """Casting Table (F8.1): metal comes in at its back (Blender +Y) through a hopper at chute height; a mold frame
    on the table; FeCastMetal (pivot at the bottom of the cavity, its height scaled by the fill) and FeCastReady (a
    stack of casts, shown when there are casts waiting); a chute at its front (Blender -Y) to the belt (0.62)."""
    base = bmesh.new()
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(base, (0.07, 0.07, 0.52), (sx * 0.38, sy * 0.36, 0.26), IRON)        # legs
    box(base, (0.84, 0.80, 0.08), (0, 0, 0.56), STEEL)                              # table top
    box(base, (0.84, 0.06, 0.04), (0, 0.36, 0.12), IRON)
    box(base, (0.84, 0.06, 0.04), (0, -0.36, 0.12), IRON)
    # mold frame (cavity 0.40 x 0.30, depth 0.08, bottom at 0.60)
    box(base, (0.52, 0.06, 0.10), (0, 0.18, 0.65), RUST)
    box(base, (0.52, 0.06, 0.10), (0, -0.18, 0.65), RUST)
    box(base, (0.06, 0.30, 0.10), (0.23, 0, 0.65), RUST)
    box(base, (0.06, 0.30, 0.10), (-0.23, 0, 0.65), RUST)
    # hopper at the back, at chute height, with a spout over the mold
    box(base, (0.30, 0.12, 0.04), (0, 0.44, C - 0.08 + 0.02), IRON)
    for sx in (-1, 1):
        box(base, (0.03, 0.12, 0.16), (sx * 0.135, 0.44, C), IRON)
    box(base, (0.12, 0.30, 0.04), (0, 0.30, 0.74), IRON, Matrix.Rotation(-0.5, 4, "X"))   # spout
    box(base, (0.10, 0.12, 0.30), (0, 0.44, 0.66), IRON)
    box(base, (0.30, 0.03, 0.03), (0, 0.49, C + 0.06), IN)
    # chute to the belt in front
    box(base, (0.34, 0.24, 0.04), (0, -0.40, 0.60), STEEL)
    box(base, (0.36, 0.03, 0.03), (0, -0.49, 0.64), OUT)
    out = [to_object(base, "feCaster_Base", bevel=0.003)]
    metal = bmesh.new()
    box(metal, (0.40, 0.30, 0.08), (0, 0, 0.04), MOLTEN)                            # z 0..0.08 above its pivot
    out.append(to_object(metal, "FeCastMetal", location=(0, 0, 0.60)))
    ready = bmesh.new()
    for k, (x, y) in enumerate(((-0.10, -0.06), (0.10, -0.06), (0.0, 0.06))):
        box(ready, (0.16, 0.08, 0.05), (x, y, 0.025 + (0.05 if k == 2 else 0)), STEEL)
    out.append(to_object(ready, "FeCastReady", location=(0.24, -0.22, 0.60)))
    return out


# ---------------------------------------------------------------- F8.2 process machines
# 1x1, front = Blender -Y (products drop on the belt in front at 0.62), back = Blender +Y (fluid inlet at C).
# Crusher and Chemical Mixer: drive shaft across the block (Blender X) at C, like the Mechanical Pump.
def out_chute(bm):
    box(bm, (0.34, 0.26, 0.04), (0, -0.37, 0.60), STEEL)
    for sx in (-1, 1):
        box(bm, (0.03, 0.26, 0.10), (sx * 0.185, -0.37, 0.64), STEEL)
    box(bm, (0.36, 0.03, 0.03), (0, -0.49, 0.64), OUT)


def drive_shaft(name="FeSpin_DriveShaft"):
    sh = bmesh.new()
    shaft_end(sh, 0.0, -0.5)
    shaft_end(sh, 0.0, 0.5)
    return to_object(sh, name, location=(0, 0, C), rotation=(0, 0, -math.pi / 2), bevel=0.002)


def model_crusher(col):
    base = bmesh.new()
    box(base, (0.84, 0.70, 0.06), (0, 0, 0.03), IRON)
    for sx in (-1, 1):
        box(base, (0.08, 0.60, 0.62), (sx * 0.36, 0, 0.37), PAINT)                  # side cheeks (bearings)
        box(base, (0.10, 0.16, 0.12), (sx * 0.36, 0, C), RUST)
    box(base, (0.64, 0.06, 0.40), (0, 0.27, 0.46), PAINT)                             # back wall
    box(base, (0.64, 0.06, 0.20), (0, -0.27, 0.36), PAINT)                            # front wall (low)
    # hopper on top, open
    for k, (w, z) in enumerate(((0.70, 0.98), (0.60, 0.92), (0.50, 0.86))):
        for sy in (-1, 1):
            box(base, (w, 0.03, 0.06), (0, sy * (w / 2 - 0.02), z), IRON)
        for sx in (-1, 1):
            box(base, (0.03, w, 0.06), (sx * (w / 2 - 0.02), 0, z), IRON)
    out_chute(base)
    out = [to_object(base, "feCrusher_Base", bevel=0.003)]
    out.append(drive_shaft())
    for name, y in (("FeSpin_x2_RollA", 0.075), ("FeSpin_x2_Rev_RollB", -0.075)):
        r = bmesh.new()
        cyl(r, 0.07, 0.58, (0, 0, 0), "Y", STEEL, segs=16)
        for k in range(10):
            a = 2 * math.pi * k / 10
            box(r, (0.02, 0.56, 0.02), (0.075 * math.cos(a), 0, 0.075 * math.sin(a)), IRON)   # teeth
        out.append(to_object(r, name, location=(0, y, 0.72), rotation=(0, 0, -math.pi / 2), bevel=0.001))
    return out


def model_chem_mixer(col):
    base = bmesh.new()
    box(base, (0.84, 0.84, 0.06), (0, 0, 0.03), IRON)
    cyl(base, 0.30, 0.66, (0, 0.04, 0.45), "Z", STEEL, segs=28)                      # tank
    for z in (0.14, 0.45, 0.77):
        cyl(base, 0.315, 0.03, (0, 0.04, z), "Z", IRON, segs=28)
    ring(base, 0.31, 0.26, 0.04, (0, 0.04, 0.80), "Z", IRON, segs=28)               # open rim
    cyl(base, 0.26, 0.02, (0, 0.04, 0.70), "Z", GASC, segs=28)                       # the mix inside
    for sx in (-1, 1):
        box(base, (0.12, 0.14, 0.16), (sx * 0.40, 0, C), RUST)                        # gear boxes on the shaft
        beam(base, (sx * 0.36, 0.04, 0.84), (sx * 0.30, 0.04, 0.95), 0.04, 0.04, IRON)
    box(base, (0.64, 0.06, 0.05), (0, 0.04, 0.96), IRON)                              # bridge with the motor head
    box(base, (0.14, 0.14, 0.12), (0, 0.04, 1.0), PAINT)
    inlet_stub(base, (0, 0.5, C), "Y", 1, IN)
    out_chute(base)
    out = [to_object(base, "feChemMixer_Base", bevel=0.003)]
    out.append(drive_shaft())
    st = bmesh.new()                                                                 # stirrer: built along Y, stood up
    cyl(st, 0.02, 0.42, (0, 0.21, 0), "Y", STEEL, segs=8)
    for k in range(3):
        a = 2 * math.pi * k / 3
        box(st, (0.20 * abs(math.cos(a)) + 0.02, 0.06, 0.20 * abs(math.sin(a)) + 0.02),
            (0.10 * math.cos(a), 0.36, 0.10 * math.sin(a)), BRASS)
    out.append(to_object(st, "FeSpin_x0.5_Stirrer", location=(0, 0.04, 0.96), rotation=AX_UP, bevel=0.001))
    return out


def model_washer(col):
    base = bmesh.new()
    box(base, (0.84, 0.84, 0.06), (0, 0, 0.03), IRON)
    for sx in (-1, 1):
        box(base, (0.04, 0.70, 0.46), (sx * 0.38, 0.02, 0.29), PAINT)
    box(base, (0.80, 0.04, 0.46), (0, 0.36, 0.29), PAINT)
    box(base, (0.80, 0.04, 0.30), (0, -0.33, 0.21), PAINT)
    box(base, (0.72, 0.66, 0.02), (0, 0.02, 0.42), WATERC)                            # water
    box(base, (0.66, 0.50, 0.02), (0, 0.04, 0.54), IRON)                              # sieve frame
    for k in range(9):
        box(base, (0.015, 0.48, 0.03), (-0.28 + k * 0.07, 0.04, 0.55), STEEL)         # sieve bars
    for sx in (-1, 1):
        box(base, (0.04, 0.04, 0.20), (sx * 0.31, 0.04, 0.46), IRON)
    box(base, (0.08, 0.30, 0.06), (0, 0.22, 0.62), STEEL)                             # spray bar
    inlet_stub(base, (0, 0.5, C), "Y", 1, IN)
    out_chute(base)
    return [to_object(base, "feWasher_Base", bevel=0.003)]


def model_steam_dryer(col):
    base = bmesh.new()
    box(base, (0.80, 0.70, 0.90), (0, 0.06, 0.50), PAINT)                             # cabinet
    for k in range(6):
        box(base, (0.60, 0.03, 0.03), (0, -0.30, 0.30 + k * 0.10), IRON)             # louvers
    for k in range(4):
        cyl(base, 0.025, 0.66, (0, 0.42, 0.20 + k * 0.16), "X", STEEL, segs=10)      # steam coil at the back
    box(base, (0.84, 0.74, 0.05), (0, 0.06, 0.97), IRON)
    cyl(base, 0.06, 0.03, (0.26, -0.30, 0.86), "Y", GLASS, segs=16)                   # gauge
    cyl(base, 0.04, 0.10, (-0.25, 0.10, 1.04), "Z", STEEL, segs=10)                   # vent
    inlet_stub(base, (0, 0.5, C), "Y", 1, IN)
    out_chute(base)
    return [to_object(base, "feSteamDryer_Base", bevel=0.003)]


# ---------------------------------------------------------------- industrial versions (electric)
def model_induction_furnace(col):
    """Induction Furnace: 2 wide x 2 high (centred, x -1..1). A crucible in a copper coil, a control cabinet, a
    hood on top; metal spouts at the bottom of each side (the Metal Chute joins any outer side of the bottom)."""
    bm = bmesh.new()
    box(bm, (1.96, 0.96, 0.10), (0, 0, 0.05), IRON)
    box(bm, (0.80, 0.80, 1.30), (0.52, 0, 0.75), PAINT)                              # cabinet (right)
    for k in range(5):
        box(bm, (0.50, 0.02, 0.05), (0.52, -0.41, 0.55 + k * 0.14), IRON)           # vents
    box(bm, (0.20, 0.02, 0.14), (0.52, -0.41, 1.25), GLASS)                          # display
    cyl(bm, 0.36, 0.95, (-0.45, 0, 0.60), "Z", STEEL, segs=28)                       # crucible
    for k in range(7):
        ring(bm, 0.40, 0.36, 0.05, (-0.45, 0, 0.22 + k * 0.12), "Z", BRASS, segs=28)   # induction coil
    cyl(bm, 0.30, 0.02, (-0.45, 0, 1.08), "Z", MOLTEN, segs=28)                      # glowing melt
    ring(bm, 0.38, 0.30, 0.06, (-0.45, 0, 1.10), "Z", IRON, segs=28)
    box(bm, (0.90, 0.90, 0.08), (-0.45, 0, 1.75), IRON)                               # hood
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(bm, (0.05, 0.05, 0.60), (-0.45 + sx * 0.40, sy * 0.40, 1.45), IRON)
    cyl(bm, 0.10, 0.18, (-0.45, 0, 1.88), "Z", STEEL, segs=14)                       # flue
    beam(bm, (0.12, 0, 1.30), (-0.20, 0, 1.30), 0.08, 0.08, RED)                      # power cable
    for sx in (-1, 1):
        box(bm, (0.16, 0.16, 0.10), (sx * 0.92, 0, C - 0.05), OUT)                   # metal spouts (sides)
    for sy in (-1, 1):
        box(bm, (0.16, 0.10, 0.10), (-0.45, sy * 0.46, C - 0.05), OUT)                # front / back
        box(bm, (0.16, 0.10, 0.10), (0.52, sy * 0.46, C - 0.05), OUT)
    out = [to_object(bm, "feInductionFurnace_Base", bevel=0.003)]
    wire_anchor(col, out, (0.52, 0.0, 1.42))
    return out


def model_caster_electric(col):
    """Industrial Casting Table: the Casting Table plus an electric fan blowing on the mold."""
    out = model_caster(col)
    out[0].name = "feCasterElectric_Base"
    fan = bmesh.new()
    box(fan, (0.06, 0.06, 0.40), (0.38, 0.0, 0.80), IRON)                              # post
    cyl(fan, 0.14, 0.10, (0.30, 0.0, 0.96), "X", PAINT, segs=20)                       # fan housing
    ring(fan, 0.16, 0.14, 0.03, (0.24, 0.0, 0.96), "X", IRON, segs=20)
    for k in range(4):
        box(fan, (0.01, 0.02, 0.24), (0.24, 0.0, 0.96), STEEL, Matrix.Rotation(k * math.pi / 4, 4, "X"))
    out.append(to_object(fan, "feCasterElectric_Fan", bevel=0.002))
    wire_anchor(col, out, (0.38, 0.0, 1.0))
    return out


def model_retort_kiln(col):
    """Retort Kiln: a brick oven with an iron retort drum inside, a door, a chimney; wood in from any side, charcoal
    out of the chute in front."""
    bm = bmesh.new()
    box(bm, (0.94, 0.90, 0.06), (0, 0, 0.03), IRON)
    box(bm, (0.90, 0.80, 0.70), (0, 0.04, 0.40), RUST)                                # brick body
    for z in (0.18, 0.36, 0.54, 0.72):
        box(bm, (0.92, 0.82, 0.02), (0, 0.04, z), IRON)                               # courses
    cyl(bm, 0.24, 0.70, (0, 0.04, 0.48), "X", STEEL, segs=20)                         # retort drum
    for sx in (-1, 1):
        cyl(bm, 0.26, 0.04, (sx * 0.36, 0.04, 0.48), "X", IRON, segs=20)
    box(bm, (0.30, 0.03, 0.24), (0, -0.37, 0.30), IRON)                                # fire door
    box(bm, (0.24, 0.02, 0.18), (0, -0.39, 0.30), MOLTEN)
    cyl(bm, 0.08, 0.24, (0.28, 0.24, 0.86), "Z", IRON, segs=14)                       # chimney
    box(bm, (0.14, 0.08, 0.10), (-0.30, -0.36, 0.70), PAINT)                           # electric heater box
    out_chute(bm)
    out = [to_object(bm, "feRetortKiln_Base", bevel=0.003)]
    wire_anchor(col, out, (-0.30, -0.36, 0.76))
    return out


def model_biodigester(col):
    """Biodigester: a sealed green tank with a dome (gas), a sight glass with the brown mash, water in at its back,
    the chute in front."""
    bm = bmesh.new()
    box(bm, (0.84, 0.84, 0.06), (0, 0, 0.03), IRON)
    cyl(bm, 0.36, 0.62, (0, 0.04, 0.37), "Z", PAINT, segs=28)                        # tank
    for z in (0.10, 0.38, 0.66):
        cyl(bm, 0.375, 0.03, (0, 0.04, z), "Z", IRON, segs=28)
    cyl(bm, 0.30, 0.16, (0, 0.04, 0.74), "Z", PAINT, segs=28, r2=0.12)               # dome
    cyl(bm, 0.05, 0.14, (0, 0.04, 0.88), "Z", STEEL, segs=10)                         # gas valve
    cyl(bm, 0.07, 0.03, (0, 0.04, 0.96), "Z", RED, segs=10)
    box(bm, (0.10, 0.02, 0.40), (0.18, -0.30, 0.36), GLASS)                           # sight glass
    box(bm, (0.08, 0.02, 0.22), (0.18, -0.31, 0.27), RUST)                            # the mash
    inlet_stub(bm, (0, 0.5, C), "Y", 1, IN)
    out_chute(bm)
    return [to_object(bm, "feBiodigester_Base", bevel=0.003)]


def model_biodigester_big(col):
    """Industrial Biodigester: 1 wide x 2 high (parent = bottom cell). A tall green digester with bands and a sight
    glass, the torque shaft through gear boxes on the bottom sides, a chain case up to a top gear head turning the
    stirrer (FeSpin, vertical), water in at the back, the chute in front."""
    bm = bmesh.new()
    box(bm, (0.92, 0.92, 0.06), (0, 0, 0.03), IRON)
    cyl(bm, 0.40, 1.55, (0, 0.04, 0.86), "Z", PAINT, segs=32)                         # tank
    for z in (0.16, 0.55, 0.95, 1.35):
        cyl(bm, 0.415, 0.04, (0, 0.04, z), "Z", IRON, segs=32)                        # bands
    cyl(bm, 0.40, 0.22, (0, 0.04, 1.74), "Z", PAINT, segs=32, r2=0.16)                # dome
    box(bm, (0.12, 0.02, 0.90), (0.20, -0.33, 0.95), GLASS)                            # sight glass
    box(bm, (0.09, 0.02, 0.55), (0.20, -0.34, 0.75), RUST)                             # the mash level
    for sx in (-1, 1):
        box(bm, (0.12, 0.16, 0.18), (sx * 0.42, 0, C), RUST)                           # gear boxes on the shaft
    box(bm, (0.08, 0.12, 1.30), (0.44, 0, 1.18), IRON)                                 # chain case up the side
    box(bm, (0.30, 0.20, 0.14), (0.30, 0.04, 1.86), IRON)                              # top gear head
    cyl(bm, 0.05, 0.16, (-0.25, 0.25, 1.86), "Z", STEEL, segs=10)                      # gas valve
    cyl(bm, 0.07, 0.03, (-0.25, 0.25, 1.95), "Z", RED, segs=10)
    inlet_stub(bm, (0, 0.5, C), "Y", 1, IN)
    out_chute(bm)
    out = [to_object(bm, "feBiodigesterBig_Base", bevel=0.003)]
    out.append(drive_shaft())
    st = bmesh.new()                                                                 # stirrer head on top
    cyl(st, 0.03, 0.20, (0, 0.10, 0), "Y", STEEL, segs=8)
    for k in range(4):
        a = math.pi * k / 2
        box(st, (0.24 * abs(math.cos(a)) + 0.03, 0.04, 0.24 * abs(math.sin(a)) + 0.03),
            (0.12 * math.cos(a), 0.05, 0.12 * math.sin(a)), BRASS)
    out.append(to_object(st, "FeSpin_x0.5_Stirrer", location=(0, 0.04, 1.99), rotation=AX_UP, bevel=0.001))
    return out


# ---------------------------------------------------------------- production machines (phase 6)
# Footprints: 1x1 = x -0.5..0.5; 2 wide (MultiBlockDim 2,2,1) = x -1..1 (the game shifts an even width by half a
# block, so the model is centred); 3 wide = x -1.5..1.5. Depth 1 (y -0.5..0.5), height up to the block count.
# Front = Blender -Y (the side the player works at). Moving parts (MachineVisual, Belt.cs neighbour file
# MachineVisual.cs): FeSpin_* turn about their Unity local +Z (= the part's Blender local -Y) while the machine
# crafts; FePiston_* slide along it. Built along local Y, then: no rotation = axis front-back, (0, 0, pi/2) = axis
# across (X), (-pi/2, 0, 0) = vertical.
AX_X = (0, 0, math.pi / 2)
AX_UP = (-math.pi / 2, 0, 0)


def _legs(bm, w, d, h, mat=IRON, t=0.07):
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(bm, (t, t, h), (sx * (w / 2 - t / 2), sy * (d / 2 - t / 2), h / 2), mat)


def _bench(bm, w, d=0.9, h=0.9, top=WOOD):
    _legs(bm, w, d, h - 0.06)
    box(bm, (w, d, 0.06), (0, 0, h - 0.03), top)
    box(bm, (w - 0.1, d - 0.1, 0.03), (0, 0, 0.18), IRON)                           # lower shelf


def _wheel(bm_name_objs, name, loc, r, depth, mat, rot, spokes=6, ring_mat=None):
    """A spinning wheel / disc built along local Y (its axis), placed at loc with rot."""
    w = bmesh.new()
    cyl(w, r * 0.25, depth * 1.4, (0, 0, 0), "Y", STEEL, segs=12)
    ring(w, r, r * 0.86, depth, (0, 0, 0), "Y", ring_mat or mat, segs=24)
    for k in range(spokes):
        a_ = k * 2 * math.pi / spokes
        box(w, (r * 0.9, depth * 0.6, 0.03), (math.cos(a_) * r * 0.45, 0, math.sin(a_) * r * 0.45), mat,
            Matrix.Rotation(-a_, 4, "Y"))
    bm_name_objs.append(to_object(w, name, location=loc, rotation=rot, bevel=0.002))


def model_m_foundry(col):
    """Foundry (2 wide, 2 high): brick furnace with a glowing mouth, a crucible on a tilting frame and a chimney."""
    b = bmesh.new()
    box(b, (1.9, 0.9, 1.2), (0, 0.02, 0.6), RUST)                                   # brick body
    for z in (0.3, 0.6, 0.9):
        box(b, (1.92, 0.92, 0.02), (0, 0.02, z), IRON)                                 # bands
    box(b, (0.8, 0.04, 0.45), (-0.35, -0.44, 0.55), OUT)                              # glowing mouth
    box(b, (0.9, 0.06, 0.55), (-0.35, -0.45, 0.55), IRON)
    cyl(b, 0.22, 0.85, (0.55, 0.15, 1.6), "Z", IRON, segs=16, r2=0.16)               # chimney
    cyl(b, 0.25, 0.05, (0.55, 0.15, 2.0), "Z", IRON, segs=16)
    for sx in (-1, 1):
        box(b, (0.05, 0.05, 0.5), (0.55 + sx * 0.3, -0.45, 1.45), IRON)               # crucible frame
    objs = [to_object(b, "feM_Foundry_Base", bevel=0.004)]
    cr = bmesh.new()
    cyl(cr, 0.2, 0.3, (0, 0, 0), "Y", IRON, segs=16, r2=0.14)
    cyl(cr, 0.16, 0.02, (0, -0.16, 0), "Y", OUT, segs=16)
    objs.append(to_object(cr, "FeSpin_x0.1_Crucible", location=(0.55, -0.45, 1.45), rotation=AX_X))
    return objs


def model_m_press(col):
    """Parts Press (2 wide, 2 high): two columns, a crown with the motor, a flywheel and the ram going up and down."""
    b = bmesh.new()
    box(b, (1.8, 0.85, 0.35), (0, 0, 0.175), IRON)                                    # base
    box(b, (0.9, 0.6, 0.08), (0, -0.05, 0.39), STEEL)                                 # bolster
    for sx in (-1, 1):
        box(b, (0.22, 0.5, 1.5), (sx * 0.62, 0, 1.1), PAINT)                           # columns
    box(b, (1.6, 0.6, 0.35), (0, 0, 1.75), PAINT)                                      # crown
    box(b, (0.4, 0.35, 0.25), (0.5, 0.15, 2.0), IRON)                                  # motor
    objs = [to_object(b, "feM_Press_Base", bevel=0.004)]
    ram = bmesh.new()
    box(ram, (0.8, 0.12, 0.6), (0, 0, 0), STEEL)                                       # ram plate (local)
    box(ram, (0.2, 0.5, 0.2), (0, -0.3, 0), STEEL)                                      # stem (up in world)
    objs.append(to_object(ram, "FePiston_Ram", location=(0, -0.05, 1.05), rotation=AX_UP))
    _wheel(objs, "FeSpin_Flywheel", (0.92, 0, 1.75), 0.32, 0.08, IRON, AX_X)
    return objs


def model_m_lathe(col):
    """Lathe (1 block): bed, headstock with the spinning chuck and a workpiece, tool post and tailstock."""
    b = bmesh.new()
    _legs(b, 0.9, 0.5, 0.6)
    box(b, (0.95, 0.45, 0.08), (0, 0, 0.64), IRON)                                    # bed
    box(b, (0.28, 0.36, 0.32), (-0.32, 0.02, 0.84), PAINT)                             # headstock
    box(b, (0.14, 0.2, 0.16), (0.36, 0.02, 0.76), PAINT)                               # tailstock
    box(b, (0.12, 0.12, 0.12), (0.08, -0.12, 0.74), STEEL)                             # tool post
    objs = [to_object(b, "feM_Lathe_Base", bevel=0.003)]
    ch = bmesh.new()
    cyl(ch, 0.09, 0.06, (0, 0, 0), "Y", STEEL, segs=14)
    for k in range(3):
        a_ = k * 2 * math.pi / 3
        box(ch, (0.03, 0.04, 0.05), (math.cos(a_) * 0.08, -0.03, math.sin(a_) * 0.08), IRON)
    cyl(ch, 0.035, 0.42, (0, -0.24, 0), "Y", BRASS, segs=10)                           # workpiece
    objs.append(to_object(ch, "FeSpin_x4_Chuck", location=(-0.15, 0.02, 0.82), rotation=AX_X))
    return objs


def model_m_kiln(col):
    """Charcoal Kiln (2 wide, 2 high): a domed brick kiln with a door and a smoking chimney."""
    b = bmesh.new()
    cyl(b, 0.9, 0.9, (0, 0, 0.45), "Z", RUST, segs=28)
    cyl(b, 0.9, 0.6, (0, 0, 1.2), "Z", RUST, segs=28, r2=0.35)                       # dome
    box(b, (0.5, 0.06, 0.55), (0, -0.88, 0.35), IRON)                                  # door
    box(b, (0.1, 0.03, 0.1), (0.15, -0.92, 0.35), BRASS)
    cyl(b, 0.12, 0.6, (0.3, 0.2, 1.7), "Z", IRON, segs=12)
    return [to_object(b, "feM_Kiln_Base", bevel=0.004)]


def model_m_ammo(col):
    """Ammo Press (2 wide, 2 high): bench with a turret reloading press (the turret turns) and a powder hopper."""
    b = bmesh.new()
    _bench(b, 1.9)
    box(b, (0.12, 0.12, 0.8), (-0.3, 0.1, 1.3), PAINT)                                 # press column
    box(b, (0.5, 0.2, 0.12), (-0.3, -0.05, 1.7), PAINT)
    cyl(b, 0.14, 0.3, (0.4, 0.1, 1.15), "Z", GLASS, segs=14, r2=0.06)                 # powder hopper
    for k in range(4):
        box(b, (0.12, 0.12, 0.08), (0.55 + (k % 2) * 0.15, -0.2 + (k // 2) * 0.15, 0.94), BRASS)   # case boxes
    objs = [to_object(b, "feM_Ammo_Base", bevel=0.003)]
    t = bmesh.new()
    cyl(t, 0.16, 0.06, (0, 0, 0), "Y", STEEL, segs=16)
    for k in range(5):
        a_ = k * 2 * math.pi / 5
        cyl(t, 0.025, 0.12, (math.cos(a_) * 0.11, -0.06, math.sin(a_) * 0.11), "Y", BRASS, segs=8)
    objs.append(to_object(t, "FeSpin_x0.5_Turret", location=(-0.3, -0.05, 1.3), rotation=AX_UP))
    return objs


def model_m_assembler(col):
    """Assembler (2 wide, 2 high): heavy bench with a vise, a drill press (the chuck turns) and a parts board."""
    b = bmesh.new()
    _bench(b, 1.9)
    box(b, (0.25, 0.2, 0.12), (-0.6, -0.3, 0.96), IRON)                                # vise
    box(b, (0.1, 0.1, 0.9), (0.5, 0.25, 1.35), PAINT)                                  # drill column
    box(b, (0.35, 0.3, 0.25), (0.5, 0.1, 1.7), PAINT)                                  # drill head
    box(b, (1.8, 0.04, 0.9), (0, 0.43, 1.45), WOOD)                                    # pegboard
    for k in range(5):
        box(b, (0.04, 0.06, 0.25), (-0.8 + k * 0.2, 0.38, 1.55), STEEL)               # tools
    objs = [to_object(b, "feM_Assembler_Base", bevel=0.003)]
    d = bmesh.new()
    cyl(d, 0.04, 0.08, (0, 0, 0), "Y", STEEL, segs=10)
    cyl(d, 0.012, 0.2, (0, 0.12, 0), "Y", IRON, segs=8)
    objs.append(to_object(d, "FeSpin_x6_Drill", location=(0.5, 0.05, 1.55), rotation=AX_UP))
    return objs


def model_m_modbench(col):
    """Mod Bench (2 wide, 2 high): bench with a magnifier lamp, a parts tray and a weapon on a stand."""
    b = bmesh.new()
    _bench(b, 1.9, top=IRON)
    box(b, (0.05, 0.05, 0.6), (-0.7, 0.2, 1.2), STEEL)
    box(b, (0.05, 0.4, 0.05), (-0.7, 0.0, 1.5), STEEL)
    cyl(b, 0.14, 0.04, (-0.7, -0.2, 1.47), "Z", GLASS, segs=16)                       # magnifier
    box(b, (0.7, 0.12, 0.08), (0.3, -0.1, 1.0), IRON)                                  # rifle on a stand
    box(b, (0.3, 0.04, 0.04), (0.75, -0.1, 1.02), IRON)
    for k in range(6):
        box(b, (0.12, 0.12, 0.04), (-0.2 + (k % 3) * 0.15, 0.25 + (k // 3) * 0.13, 0.92), OUT if k % 2 else BRASS)
    return [to_object(b, "feM_ModBench_Base", bevel=0.003)]


def model_m_loom(col):
    """Loom (2 wide, 2 high): a wooden frame with warp threads, a cloth roll that turns and a pedal beam."""
    b = bmesh.new()
    for sx in (-1, 1):
        box(b, (0.1, 0.8, 0.1), (sx * 0.85, 0, 0.05), WOOD)
        for sy in (-1, 1):
            box(b, (0.08, 0.08, 1.6), (sx * 0.85, sy * 0.35, 0.8), WOOD)
    box(b, (1.8, 0.08, 0.08), (0, 0.35, 1.55), WOOD)
    box(b, (1.8, 0.08, 0.08), (0, -0.35, 1.55), WOOD)
    for k in range(17):                                                                 # warp threads
        box(b, (0.01, 0.7, 0.01), (-0.8 + k * 0.1, 0, 1.1), GLASS)
    box(b, (1.6, 0.06, 0.4), (0, 0.05, 1.3), GLASS)                                    # heddle frame
    objs = [to_object(b, "feM_Loom_Base", bevel=0.003)]
    r = bmesh.new()
    cyl(r, 0.12, 1.6, (0, 0, 0), "Y", PAINT, segs=18)
    cyl(r, 0.04, 1.75, (0, 0, 0), "Y", WOOD, segs=10)
    objs.append(to_object(r, "FeSpin_x0.3_ClothRoll", location=(0, -0.3, 0.75), rotation=AX_X))
    return objs


def model_m_refinery(col):
    """Refinery (3 wide, 2 high): a distillation column, two tanks, a heater and pipes; the pump wheel turns."""
    b = bmesh.new()
    box(b, (2.9, 0.9, 0.08), (0, 0, 0.04), IRON)
    cyl(b, 0.28, 1.9, (-1.0, 0.0, 1.0), "Z", STEEL, segs=20)                          # column
    for z in (0.4, 0.8, 1.2, 1.6):
        ring(b, 0.3, 0.27, 0.05, (-1.0, 0.0, z), "Z", IRON, segs=20)
    cyl(b, 0.35, 1.0, (0.1, 0.1, 0.55), "Z", PAINT, segs=20)                          # tank 1
    cyl(b, 0.3, 0.8, (0.9, 0.15, 0.45), "Z", PAINT, segs=20)                           # tank 2
    cyl(b, 0.04, 1.2, (-0.45, 0.0, 1.8), "X", STEEL, segs=8)                           # pipes
    cyl(b, 0.04, 0.8, (0.5, -0.2, 1.1), "X", STEEL, segs=8)
    box(b, (0.5, 0.4, 0.3), (0.9, -0.2, 1.05), IRON)                                    # heater
    box(b, (0.3, 0.03, 0.12), (0.9, -0.41, 1.05), OUT)
    objs = [to_object(b, "feM_Refinery_Base", bevel=0.004)]
    _wheel(objs, "FeSpin_PumpWheel", (-0.45, -0.38, 0.55), 0.2, 0.05, IRON, (0, 0, 0), spokes=4, ring_mat=RED)
    return objs


def model_m_lab(col):
    """Laboratory (3 wide, 2 high): a long bench with flasks, a fume hood and a centrifuge that spins."""
    b = bmesh.new()
    _bench(b, 2.9, top=PAINT)
    box(b, (0.9, 0.7, 0.9), (-0.9, 0.05, 1.35), STEEL)                                 # fume hood
    box(b, (0.8, 0.02, 0.5), (-0.9, -0.31, 1.2), GLASS)
    for k in range(6):
        cyl(b, 0.06, 0.18, (0.0 + (k % 3) * 0.18, -0.15 + (k // 3) * 0.2, 0.99), "Z", GLASS, segs=10, r2=0.025)
    box(b, (0.5, 0.4, 0.3), (0.95, 0.1, 1.05), PAINT)                                   # centrifuge body
    objs = [to_object(b, "feM_Lab_Base", bevel=0.003)]
    c = bmesh.new()
    cyl(c, 0.17, 0.04, (0, 0, 0), "Y", STEEL, segs=18)
    for k in range(4):
        a_ = k * math.pi / 2
        cyl(c, 0.03, 0.06, (math.cos(a_) * 0.11, -0.03, math.sin(a_) * 0.11), "Y", GLASS, segs=8)
    objs.append(to_object(c, "FeSpin_x8_Rotor", location=(0.95, 0.1, 1.22), rotation=AX_UP))
    return objs


def model_m_kitchen(col):
    """Kitchen (1 block): an iron stove with two pots, an oven door and a stovepipe."""
    b = bmesh.new()
    box(b, (0.9, 0.7, 0.85), (0, 0.05, 0.425), IRON)
    box(b, (0.5, 0.03, 0.35), (0, -0.31, 0.35), RUST)                                  # oven door
    box(b, (0.3, 0.03, 0.04), (0, -0.33, 0.48), BRASS)
    cyl(b, 0.16, 0.22, (-0.2, 0.0, 0.96), "Z", STEEL, segs=16)                        # pots
    cyl(b, 0.13, 0.16, (0.22, 0.1, 0.93), "Z", RUST, segs=16)
    cyl(b, 0.07, 1.0, (0.3, 0.3, 1.3), "Z", IRON, segs=10)                            # stovepipe
    return [to_object(b, "feM_Kitchen_Base", bevel=0.003)]


def model_m_electronics(col):
    """Electronics Bench (2 wide, 2 high): bench with an oscilloscope, a soldering station, coil spools that turn."""
    b = bmesh.new()
    _bench(b, 1.9, top=PAINT)
    box(b, (0.5, 0.35, 0.35), (-0.55, 0.15, 1.08), IRON)                               # oscilloscope
    box(b, (0.3, 0.02, 0.22), (-0.6, -0.03, 1.1), IN)
    box(b, (0.25, 0.2, 0.1), (0.1, 0.1, 0.95), RED)                                     # soldering station
    box(b, (1.8, 0.04, 0.6), (0, 0.43, 1.3), WOOD)                                      # shelf board
    objs = [to_object(b, "feM_Electronics_Base", bevel=0.003)]
    sp = bmesh.new()
    for k in range(3):
        cyl(sp, 0.09, 0.12, (0, -0.3 + k * 0.3, 0), "Y", BRASS, segs=14)
        cyl(sp, 0.11, 0.02, (0, -0.37 + k * 0.3, 0), "Y", IRON, segs=14)
        cyl(sp, 0.11, 0.02, (0, -0.23 + k * 0.3, 0), "Y", IRON, segs=14)
    cyl(sp, 0.02, 1.0, (0, 0, 0), "Y", STEEL, segs=8)
    objs.append(to_object(sp, "FeSpin_x0.5_Spools", location=(0.55, 0.2, 1.35), rotation=AX_X))
    return objs


def model_m_metalshop(col):
    """Metal Shop (2 wide, 2 high): an anvil, a bending brake with a moving blade and sheet stock."""
    b = bmesh.new()
    box(b, (0.3, 0.25, 0.4), (-0.6, 0, 0.2), IRON)                                      # anvil stand
    box(b, (0.55, 0.25, 0.15), (-0.6, 0, 0.47), STEEL)
    cyl(b, 0.08, 0.2, (-0.94, 0, 0.47), "X", STEEL, segs=10, r2=0.02)                  # horn
    for sx in (-1, 1):
        box(b, (0.12, 0.6, 1.0), (0.3 + sx * 0.5, 0, 0.5), PAINT)                      # brake cheeks
    box(b, (1.1, 0.5, 0.12), (0.3, 0, 0.9), IRON)                                      # bed
    for k in range(4):
        box(b, (0.8, 0.5, 0.015), (0.3, 0.1, 0.05 + k * 0.02), STEEL)                   # sheet stock
    objs = [to_object(b, "feM_MetalShop_Base", bevel=0.003)]
    bl = bmesh.new()
    box(bl, (1.0, 0.25, 0.06), (0, 0, 0), STEEL)
    objs.append(to_object(bl, "FePiston_Blade", location=(0.3, -0.1, 1.2), rotation=AX_UP))
    return objs


def model_m_sawmill(col):
    """Sawmill (1 block): a saw table with a big circular blade that turns and a log on the carriage."""
    b = bmesh.new()
    _legs(b, 0.95, 0.8, 0.6)
    box(b, (0.98, 0.82, 0.06), (0, 0, 0.63), IRON)
    cyl(b, 0.12, 0.8, (0.25, 0.0, 0.78), "Y", WOOD, segs=14)                          # log
    box(b, (0.1, 0.3, 0.2), (-0.1, 0.25, 0.75), PAINT)                                   # guard
    objs = [to_object(b, "feM_Sawmill_Base", bevel=0.003)]
    bl = bmesh.new()
    cyl(bl, 0.28, 0.015, (0, 0, 0), "Y", STEEL, segs=28)
    for k in range(16):
        a_ = k * 2 * math.pi / 16
        box(bl, (0.04, 0.016, 0.04), (math.cos(a_) * 0.29, 0, math.sin(a_) * 0.29), IRON, Matrix.Rotation(-a_, 4, "Y"))
    objs.append(to_object(bl, "FeSpin_x8_Blade", location=(-0.1, 0.0, 0.66), rotation=AX_X))
    return objs


def model_m_mixer(col):
    """Concrete Mixer (1 block): a tilted drum that turns on a frame with a motor."""
    b = bmesh.new()
    _legs(b, 0.8, 0.8, 0.35)
    box(b, (0.8, 0.8, 0.06), (0, 0, 0.38), IRON)
    box(b, (0.25, 0.25, 0.2), (0.25, 0.25, 0.5), PAINT)                                  # motor
    for sx in (-1, 1):
        box(b, (0.05, 0.05, 0.4), (sx * 0.3, 0, 0.6), IRON)
    objs = [to_object(b, "feM_Mixer_Base", bevel=0.003)]
    d = bmesh.new()
    cyl(d, 0.3, 0.5, (0, 0, 0), "Y", OUT, segs=20, r2=0.18)
    cyl(d, 0.3, 0.12, (0, 0.28, 0), "Y", OUT, segs=20, r2=0.24)
    for k in range(3):
        ring(d, 0.31, 0.29, 0.03, (0, -0.15 + k * 0.15, 0), "Y", IRON, segs=20)
    objs.append(to_object(d, "FeSpin_x0.5_Drum", location=(0, 0.0, 0.8), rotation=(math.radians(-30), 0, 0)))
    return objs


def model_m_garage(col):
    """Garage (2 wide, 2 high): a two-post lift with its arms going up and down, a tire rack and an engine stand."""
    b = bmesh.new()
    box(b, (1.9, 0.9, 0.04), (0, 0, 0.02), IRON)
    for sx in (-1, 1):
        box(b, (0.14, 0.14, 1.9), (sx * 0.85, 0.3, 0.95), RED)                          # lift posts
    for k in range(3):
        cyl(b, 0.22, 0.12, (-0.4 + k * 0.4, 0.33, 0.25), "Y", IRON, segs=16)            # tires
    box(b, (0.3, 0.3, 0.3), (0.3, -0.2, 0.35), PAINT)                                    # engine block
    box(b, (0.05, 0.05, 0.2), (0.3, -0.2, 0.1), IRON)
    objs = [to_object(b, "feM_Garage_Base", bevel=0.003)]
    arms = bmesh.new()
    for sx in (-1, 1):
        box(arms, (0.6, 0.08, 0.06), (sx * 0.6, 0, 0), STEEL)
    objs.append(to_object(arms, "FePiston_LiftArms", location=(0, 0.1, 0.9), rotation=AX_UP))
    return objs


def model_m_robotics(col):
    """Robotics Bench (2 wide, 2 high): bench with a robot arm whose base turns, a drone on a stand and parts bins."""
    b = bmesh.new()
    _bench(b, 1.9, top=PAINT)
    box(b, (0.4, 0.3, 0.12), (0.5, -0.05, 0.98), IRON)                                  # drone body
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(b, 0.1, 0.01, (0.5 + sx * 0.25, -0.05 + sy * 0.18, 1.05), "Z", STEEL, segs=12)
    for k in range(4):
        box(b, (0.2, 0.2, 0.1), (-0.15 + k * 0.22, 0.32, 0.95), OUT if k % 2 else IN)
    objs = [to_object(b, "feM_Robotics_Base", bevel=0.003)]
    arm = bmesh.new()
    cyl(arm, 0.12, 0.08, (0, 0, 0), "Y", IRON, segs=16)                                 # turning base (local)
    box(arm, (0.08, 0.5, 0.08), (0, -0.28, 0.0), RED)                                    # upper arm (up)
    box(arm, (0.3, 0.06, 0.06), (0.15, -0.5, 0.0), RED)                                  # forearm
    box(arm, (0.06, 0.1, 0.06), (0.3, -0.45, 0.0), STEEL)                                # gripper
    objs.append(to_object(arm, "FeSpin_x0.3_RobotArm", location=(-0.6, -0.05, 0.94), rotation=AX_UP))
    return objs


AXLE_Z = C


def model_torque_crank(col):
    """The Crank (Art/feCrank) without dynamo, belt, battery compartment and insulator; its axle sits at the block
    centre height and runs through the back frame to a flange on the back face (Blender +Y), where shafts join."""
    FRONT_Y, BACK_Y = -0.30, 0.30
    bm = bmesh.new()
    for x in (-0.30, 0.0, 0.30):
        box(bm, (0.285, 0.92, 0.06), (x, 0, 0.03), WOOD)
    for y in (-0.40, 0.40):
        box(bm, (0.94, 0.05, 0.008), (0, y, 0.064), RUST)
        for x in (-0.40, -0.30, 0.0, 0.30, 0.40):
            cyl(bm, 0.011, 0.012, (x, y, 0.072), "Z", IRON, segs=6)
    for y in (FRONT_Y, BACK_Y):
        for s in (-1, 1):
            beam(bm, (s * 0.33, y, 0.06), (s * 0.05, y, AXLE_Z - 0.02), 0.07, 0.07, WOOD)
        out_ = -0.055 if y < 0 else 0.055
        box(bm, (0.46, 0.04, 0.06), (0, y + out_, 0.26), WOOD)
        box(bm, (0.17, 0.10, 0.10), (0, y, AXLE_Z), IRON)
        box(bm, (0.19, 0.11, 0.015), (0, y, AXLE_Z + 0.055), RUST)
        for s in (-1, 1):
            cyl(bm, 0.012, 0.02, (s * 0.065, y, AXLE_Z + 0.07), "Z", IRON, segs=6)
            box(bm, (0.10, 0.09, 0.012), (s * 0.31, y, 0.066), IRON)
    # rear bearing at the back face for the drive shaft
    box(bm, (0.14, 0.06, AXLE_Z - 0.06), (0, 0.44, (AXLE_Z - 0.06) / 2 + 0.06), IRON)
    box(bm, (0.16, 0.08, 0.08), (0, 0.44, AXLE_Z), RUST)
    base = to_object(bm, "feTorqueCrank_Base", bevel=0.004)

    rot = bmesh.new()   # local coords: origin on the axle, spins around local Y
    cyl(rot, 0.025, 0.40, (0, -0.20, 0), "Y", IRON)            # front axle part -0.40..0
    cyl(rot, 0.035, 0.02, (0, -0.40, 0), "Y", IRON, segs=6)
    ring(rot, 0.26, 0.22, 0.06, (0, 0, 0), "Y", IRON, segs=32)
    ring(rot, 0.265, 0.255, 0.064, (0, 0, 0), "Y", RUST, segs=32)
    cyl(rot, 0.06, 0.09, (0, 0, 0), "Y", IRON)
    for k in range(6):
        a = k * math.pi / 3
        m = Matrix.Rotation(a, 4, "Y") @ Matrix.Translation((0.14, 0, 0))
        r = bmesh.ops.create_cube(rot, size=1.0, calc_uvs=True)
        _finish(rot, IRON, m @ Matrix.Diagonal((0.17, 0.03, 0.035, 1.0)), r["verts"])
    shaft_end(rot, 0.0, 0.5)                                    # drive shaft to the back face
    arm_y, throw = -0.38, 0.20
    box(rot, (0.05, 0.03, throw), (0, arm_y, -throw / 2), RUST)
    cyl(rot, 0.03, 0.03, (0, arm_y, 0), "Y", RUST)
    cyl(rot, 0.03, 0.03, (0, arm_y, -throw), "Y", RUST)
    cyl(rot, 0.012, 0.11, (0, -0.44, -throw), "Y", IRON, segs=8)
    cyl(rot, 0.022, 0.08, (0, -0.45, -throw), "Y", WOOD, segs=12)
    cyl(rot, 0.026, 0.01, (0, -0.495, -throw), "Y", IRON, segs=12)
    # named like the Crank's rotor: CrankSpinner turns it while the player cranks; the FeSpin token lets
    # KineticSpinner find it too.
    rotor = to_object(rot, "feCrank_Rotor", location=(0, 0, AXLE_Z), bevel=0.003)
    return [base, rotor]


MODELS = {
    "feTorqueCrank": model_torque_crank,
    "feShaft": model_shaft,
    "feSpeedBox": model_speedbox,
    "feGearbox": model_gearbox,
    "feSpinInverter": model_inverter,
    "feTorqueRegulator": model_regulator,
    "feClutch": model_clutch,
    "feTorqueGauge": model_gauge,
    "feWaterWheel": model_waterwheel,
    "feSteamEngine": model_big_steam_engine,
    "fePipe": model_pipe,
    "feWaterTank": model_water_tank,
    "feMechPump": model_mech_pump,
    "feElecPump": model_elec_pump,
    "feCondenser": model_condenser,
    "feElectricMotor": model_electric_motor,
    "feElectricMotor2": model_electric_motor2,
    "feElectricMotor3": model_electric_motor3,
    "feDynamo": model_dynamo,
    "feDynamo2": model_dynamo2,
    "feBus": model_bus,
    "feConveyor": model_conveyor,
    "feConveyorRamp": model_conveyor_ramp,
    "feFunnel": model_funnel,
    "feConveyorDown": model_conveyor_down,
    "feFluidFiller": model_fluid_filler,
    "feFluidBottler": model_fluid_bottler,
    "feMetalChute": model_metal_chute,
    "feCaster": model_caster,
    "feCrusher": model_crusher,
    "feChemMixer": model_chem_mixer,
    "feWasher": model_washer,
    "feSteamDryer": model_steam_dryer,
    "feInductionFurnace": model_induction_furnace,
    "feCasterElectric": model_caster_electric,
    "feRetortKiln": model_retort_kiln,
    "feBiodigester": model_biodigester,
    "feBiodigesterBig": model_biodigester_big,
    "feM_Foundry": model_m_foundry,
    "feM_Press": model_m_press,
    "feM_Lathe": model_m_lathe,
    "feM_Kiln": model_m_kiln,
    "feM_Ammo": model_m_ammo,
    "feM_Assembler": model_m_assembler,
    "feM_ModBench": model_m_modbench,
    "feM_Loom": model_m_loom,
    "feM_Refinery": model_m_refinery,
    "feM_Lab": model_m_lab,
    "feM_Kitchen": model_m_kitchen,
    "feM_Electronics": model_m_electronics,
    "feM_MetalShop": model_m_metalshop,
    "feM_Sawmill": model_m_sawmill,
    "feM_Mixer": model_m_mixer,
    "feM_Garage": model_m_garage,
    "feM_Robotics": model_m_robotics,
}


def main():
    make_materials()
    for ob in list(bpy.data.objects):
        if ob.name in ("Cube",):
            bpy.data.objects.remove(ob, do_unlink=True)
    report = {}
    for name, fn in MODELS.items():
        col = bpy.data.collections.get(name)
        if col:
            for ob in list(col.objects):
                bpy.data.objects.remove(ob, do_unlink=True)
        else:
            col = bpy.data.collections.new(name)
            bpy.context.scene.collection.children.link(col)
        objs = fn(col)
        root = objs[0]
        for ob in objs:
            col.objects.link(ob)
        for ob in objs[1:]:
            ob.parent = root
            ob.matrix_parent_inverse = root.matrix_world.inverted()
        bpy.context.view_layer.update()
        lo = Vector((1e9,) * 3)
        hi = Vector((-1e9,) * 3)
        tris = 0
        for ob in objs:
            if ob.data is None:
                continue
            for v in ob.data.vertices:
                w = ob.matrix_world @ v.co
                lo = Vector(map(min, lo, w))
                hi = Vector(map(max, hi, w))
            tris += sum(len(p.vertices) - 2 for p in ob.data.polygons) if ob.data else 0
        report[name] = {"objects": [o.name for o in objs], "tris": tris,
                        "min": [round(c, 3) for c in lo], "max": [round(c, 3) for c in hi]}
    return report


REPORT = main()
print(REPORT)
