"""Builds the torque network models (D8) in the open Blender scene, one collection per block:

  feTorqueCrank      Torque Crank (the Crank without dynamo / battery / insulator; drive shaft out of the back)
  feShaft            Shaft
  feSpeedBox         Speed Box (input end + output end)
  feGearbox          Gearbox (six hubs)
  feSpinInverter     Spin Inverter (input end + output end, counter-rotating gears in a drum)
  feTorqueRegulator  Torque Regulator (input end + output end, flyball governor, handwheel)

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
  Spinning parts (contract in ART_BRIEF.md / src/FerroEngrenagem/KineticSpinner.cs) are objects named
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
}
MI = {name: i for i, name in enumerate(MATS)}
WOOD, IRON, STEEL, RUST, BRASS, PAINT, IN, OUT, RED, GLASS = (MI[n] for n in MATS)

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
