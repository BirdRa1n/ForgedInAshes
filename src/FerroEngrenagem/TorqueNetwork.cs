// D8: mechanical TORQUE network (Create-like). See PLANO_MOD.md 5.4.
//
// Nodes are blocks that carry torque, joined face to face:
//   Shaft      (BlockFeKinetic, FeKinetic="shaft")    two faces along its axis (FeShaftAxis in model space,
//                                                     turned by the block rotation like multiblock cells)
//   Gearbox    (BlockFeKinetic, FeKinetic="gearbox")  all six faces
//   SpeedBox   (BlockFeKinetic, FeKinetic="speedbox") two faces along its axis: INPUT at -axis, OUTPUT at +axis;
//                                                     output RPM = input RPM x ratio (block meta: x2, x4, x1/2;
//                                                     E cycles it). Works both ways (entering by the output
//                                                     divides).
//   Clutch     (FeKinetic="clutch")                   axial; meta 0 engaged, 1 released (no faces at all)
//   Regulator  (FeKinetic="regulator")                axial pass-through; caps what is behind its output end
//                                                     (ComputeUsage: zones, limit = 100/75/50/25 % of capacity)
//   Gauge      (FeKinetic="gauge")                    all six faces; detailed look-at readout
//   Motor      (FeMotor=true, Electric Motor)         all six faces; source: FeTorqueOutput UT while powered
//   TorqueCrank(BlockFeTorqueCrank)                   all six faces; source: FeTorqueOutput UT while turned
// A power-gated machine (FeMinPower) is a CONSUMER of the node in its motor socket (PowerGate.SocketPos), if that
// node has a face pointing into the machine.
//
// Network = flood fill from a node; every node gets a speed FACTOR relative to the start node (speed boxes
// multiply it). Sources all turn at BaseRpm (32): each one fixes the network's reference speed; two sources that
// would need different speeds = LOCKED (nothing runs). Machine RPM = reference x its factor, capped at MaxRpm.
// Capacity = sum of the sources (UT). Usage = sum over machines of cost x (rpm / 32)^2 (T2, approved: 2x faster =
// 4x torque). Machine cost = FeTorqueCost or FeMinPower x 64/30 (30/60/90 W -> 64/128/192 UT), whenever
// connected. usage > capacity = OVERLOADED: every machine of the network stops. Crafting speed = rpm / 32.
// Networks are rebuilt lazily, at most every CacheSeconds per node (Invalidate() after a speed box change).
//
// Runs wherever the power gate runs (SP / host / server). The look-at readout (KineticLookController) runs the
// same flood fill on the client; on a pure MP client a motor's IsPowered comes from the synced tile entity.
//
// C# 5 only.

using System.Collections.Generic;
using UnityEngine;

namespace FerroEngrenagem
{
    public enum KineticKind { None, Shaft, Gearbox, SpeedBox, Clutch, Regulator, Gauge, Inverter, Motor, TorqueCrank, Engine }

    [UnityEngine.Scripting.Preserve]
    public class BlockFeKinetic : Block
    {
        public static readonly float[] Ratios = { 2f, 4f, 0.5f };      // speed box setting = block meta
        public static readonly int[] Limits = { 100, 75, 50, 25 };     // regulator setting (%) = block meta

        public KineticKind Kind = KineticKind.Gearbox;
        public Vector3i ShaftAxis = new Vector3i(0, 0, 1);   // pipe_straight.fbx lies along local Z (D8 T1 test)

        public override void Init()
        {
            base.Init();
            string k = Properties != null && Properties.Contains("FeKinetic")
                ? Properties.GetString("FeKinetic").Trim().ToLowerInvariant() : "gearbox";
            switch (k)
            {
                case "shaft": Kind = KineticKind.Shaft; break;
                case "speedbox": Kind = KineticKind.SpeedBox; break;
                case "clutch": Kind = KineticKind.Clutch; break;
                case "regulator": Kind = KineticKind.Regulator; break;
                case "gauge": Kind = KineticKind.Gauge; break;
                case "inverter": Kind = KineticKind.Inverter; break;
                default: Kind = KineticKind.Gearbox; break;
            }
            if (Properties != null && Properties.Contains("FeShaftAxis"))
            {
                switch (Properties.GetString("FeShaftAxis").Trim().ToLowerInvariant())
                {
                    case "x": ShaftAxis = new Vector3i(1, 0, 0); break;
                    case "y": ShaftAxis = new Vector3i(0, 1, 0); break;
                    default: ShaftAxis = new Vector3i(0, 0, 1); break;
                }
            }
            KineticLookController.Ensure();
            MotorSocketMarker.Ensure();
        }

        public static float Ratio(BlockValue bv)
        {
            return Ratios[bv.meta % Ratios.Length];
        }

        public static int LimitPercent(BlockValue bv)
        {
            return Limits[bv.meta % Limits.Length];
        }

        /// <summary>Clutch: meta 0 = engaged (passes torque), 1 = released.</summary>
        public static bool Engaged(BlockValue bv)
        {
            return bv.meta % 2 == 0;
        }

        /// <summary>How many settings E cycles through (0 = no setting).</summary>
        public static int Settings(KineticKind kind)
        {
            switch (kind)
            {
                case KineticKind.SpeedBox: return Ratios.Length;
                case KineticKind.Clutch: return 2;
                case KineticKind.Regulator: return Limits.Length;
                default: return 0;
            }
        }

        // ModelEntity blocks get the spin animator (KineticSpinner.cs). Shape="New" blocks are meshed into the
        // chunk and have no transform to animate (the pipe placeholders).
        public override void OnBlockEntityTransformAfterActivated(WorldBase _world, Vector3i _blockPos,
                                                                  BlockValue _blockValue, BlockEntityData _ebcd)
        {
            base.OnBlockEntityTransformAfterActivated(_world, _blockPos, _blockValue, _ebcd);
            KineticSpinner.Attach(_ebcd, _blockPos, this);
        }

        // Standing, E on a speed box / clutch / regulator changes its setting (KineticLookController); crouching,
        // E opens the vanilla radial with "take" (CanPickup in XML), like the Crank.
        public override bool HasBlockActivationCommands(WorldBase _world, BlockValue _blockValue, Vector3i _blockPos,
                                                        EntityAlive _entityFocusing)
        {
            bool crouch = _entityFocusing != null && _entityFocusing.IsCrouching;
            return crouch && base.HasBlockActivationCommands(_world, _blockValue, _blockPos, _entityFocusing);
        }
    }

    public class TorqueNet
    {
        public readonly Dictionary<Vector3i, float> Factor = new Dictionary<Vector3i, float>();   // node -> speed factor
        public readonly Dictionary<Vector3i, float> Machines = new Dictionary<Vector3i, float>(); // parent -> factor
        public readonly Dictionary<Vector3i, Vector3i> MachineNode = new Dictionary<Vector3i, Vector3i>(); // parent -> socket node
        public readonly Dictionary<Vector3i, float> MachineScale = new Dictionary<Vector3i, float>(); // regulator slow-down
        public readonly Dictionary<Vector3i, RegZone> Regulators = new Dictionary<Vector3i, RegZone>();
        // spin direction: world angular velocity direction of each node (right-hand rule, unit axis vector; for a
        // gearbox/gauge the one of the shaft that drives it, for an inverter the one of its -axis end)
        public readonly Dictionary<Vector3i, Vector3i> Omega = new Dictionary<Vector3i, Vector3i>();
        public readonly Dictionary<Vector3i, Vector3i> EntryN = new Dictionary<Vector3i, Vector3i>();  // gearbox entry face
        public readonly Dictionary<Vector3i, Vector3i> WrongSpin = new Dictionary<Vector3i, Vector3i>(); // parent -> node
        public int Capacity;
        public int Usage;
        public int Sources;
        public float RefRpm = Kinetic.BaseRpm;   // RPM of a node with factor 1
        public int Sign = 1;                     // relative spins x Sign = real spins (decided by a source)
        public bool Locked;
        public float Time;

        public ICollection<Vector3i> Nodes { get { return Factor.Keys; } }
        public bool Overloaded { get { return Capacity > 0 && Usage > Capacity; } }
        public bool Running { get { return Capacity > 0 && !Overloaded && !Locked; } }

        public float RpmAt(Vector3i node)
        {
            float f;
            return Factor.TryGetValue(node, out f) ? Kinetic.ClampRpm(RefRpm * f) : 0f;
        }

        public float MachineRpm(Vector3i parent)
        {
            float f;
            return Machines.TryGetValue(parent, out f) ? Kinetic.ClampRpm(RefRpm * f) : 0f;
        }

        /// <summary>Crafting speed multiplier: rpm / 32, slowed down by regulators that cap it.</summary>
        public float MachineSpeed(Vector3i parent)
        {
            float s;
            if (!MachineScale.TryGetValue(parent, out s)) s = 1f;
            return MachineRpm(parent) / Kinetic.BaseRpm * s;
        }
    }

    /// <summary>What sits behind a Torque Regulator's output (D8 T3).</summary>
    public class RegZone
    {
        public Vector3i Pos;
        public int Percent;
        public int Limit;        // UT it lets through = Percent of the network capacity
        public int Wanted;       // UT the zone would use at full speed
        public int Used;         // UT it really uses = min(Wanted, Limit)
        public float Scale = 1f; // speed factor applied to its machines when Wanted > Limit
        public bool Bypassed;    // the zone loops back to the input side: the regulator does nothing
        public readonly HashSet<Vector3i> Nodes = new HashSet<Vector3i>();
        public readonly List<Vector3i> Children = new List<Vector3i>();   // regulators inside the zone
    }

    public static class Kinetic
    {
        public const float BaseRpm = 32f;
        public const float MaxRpm = 256f;
        public const float MinRpm = 4f;
        const int MaxNodes = 1024;
        const float CacheSeconds = 0.5f;

        static readonly Vector3i[] Dirs =
        {
            new Vector3i(1, 0, 0), new Vector3i(-1, 0, 0), new Vector3i(0, 1, 0),
            new Vector3i(0, -1, 0), new Vector3i(0, 0, 1), new Vector3i(0, 0, -1)
        };

        static readonly Dictionary<Vector3i, TorqueNet> byNode = new Dictionary<Vector3i, TorqueNet>();
        static readonly Dictionary<int, int> outputByBlock = new Dictionary<int, int>();
        static readonly Dictionary<int, int> costByBlock = new Dictionary<int, int>();

        public static float ClampRpm(float rpm)
        {
            return Mathf.Clamp(rpm, MinRpm, MaxRpm);
        }

        public static KineticKind Kind(Block b)
        {
            if (b == null) return KineticKind.None;
            BlockFeKinetic k = b as BlockFeKinetic;
            if (k != null) return k.Kind;
            if (b is BlockFeTorqueCrank) return KineticKind.TorqueCrank;
            if (PowerGate.IsMotor(b)) return KineticKind.Motor;
            if (TorqueEngine.IsEngine(b)) return KineticKind.Engine;
            return KineticKind.None;
        }

        /// <summary>World direction of an axial block's +axis (shaft, speed box, clutch, regulator, inverter, and
        /// the drive shaft of the sources: model local +Z); zero for gearbox / gauge (all six faces).</summary>
        public static Vector3i Axis(BlockValue bv)
        {
            Vector3 local;
            switch (Kind(bv.Block))
            {
                case KineticKind.Shaft:
                case KineticKind.SpeedBox:
                case KineticKind.Clutch:
                case KineticKind.Regulator:
                case KineticKind.Inverter:
                    local = ((BlockFeKinetic)bv.Block).ShaftAxis.ToVector3();
                    break;
                case KineticKind.Motor:
                case KineticKind.TorqueCrank:
                case KineticKind.Engine:
                    local = Vector3.forward;   // sources: the model's local +Z is the drive shaft; they turn +Z
                    break;
                default:
                    return Vector3i.zero;
            }
            Vector3 a = bv.Block.shape.GetRotation(bv) * local;
            return new Vector3i(Mathf.RoundToInt(a.x), Mathf.RoundToInt(a.y), Mathf.RoundToInt(a.z));
        }

        public static bool IsSource(KineticKind k)
        {
            return k == KineticKind.Motor || k == KineticKind.TorqueCrank || k == KineticKind.Engine;
        }

        static int Dot(Vector3i a, Vector3i b)
        {
            return a.x * b.x + a.y * b.y + a.z * b.z;
        }

        static Vector3i Neg(Vector3i a)
        {
            return new Vector3i(-a.x, -a.y, -a.z);
        }

        static Vector3i Mul(int c, Vector3i a)
        {
            return new Vector3i(c * a.x, c * a.y, c * a.z);
        }

        /// <summary>Spin carried out of a node through face d, as +1/-1 along d (right-hand rule): straight
        /// through keeps the angular velocity; a gearbox turning 90 degrees flips it (bevel gears); an inverter
        /// flips it between its two ends.</summary>
        static int OutSpin(KineticKind kind, Vector3i axis, Vector3i omega, Vector3i entryN, Vector3i d)
        {
            if (kind == KineticKind.Gearbox || kind == KineticKind.Gauge)
            {
                if (d == entryN || d == Neg(entryN)) return Dot(omega, d);
                return Dot(omega, entryN);
            }
            if (kind == KineticKind.Inverter && d == axis) return -Dot(omega, d);   // omega = the -axis end's
            return Dot(omega, d);
        }

        /// <summary>Angular velocity a node takes when spin c (along travel d) enters it.</summary>
        static Vector3i EnterOmega(KineticKind kind, Vector3i axis, Vector3i d, int c)
        {
            Vector3i v = Mul(c, d);
            if (kind == KineticKind.Inverter && d == Neg(axis)) return Neg(v);   // entered by its +axis end
            return v;
        }

        public static bool HasFace(BlockValue bv, Vector3i dir)
        {
            if (Kind(bv.Block) == KineticKind.Clutch && !BlockFeKinetic.Engaged(bv)) return false;   // released
            Vector3i axis = Axis(bv);
            if (axis == Vector3i.zero) return Kind(bv.Block) != KineticKind.None;
            return dir == axis || dir == new Vector3i(-axis.x, -axis.y, -axis.z);
        }

        static bool IsSpeedBox(BlockValue bv)
        {
            return Kind(bv.Block) == KineticKind.SpeedBox;
        }

        /// <summary>Speed factor change when torque leaves node A (block a) through face d.</summary>
        static float LeaveMult(BlockValue a, Vector3i d)
        {
            return IsSpeedBox(a) && d == Axis(a) ? BlockFeKinetic.Ratio(a) : 1f;
        }

        /// <summary>Speed factor change when torque enters node B (block b) through its face e.</summary>
        static float EnterMult(BlockValue b, Vector3i e)
        {
            return IsSpeedBox(b) && e == Axis(b) ? 1f / BlockFeKinetic.Ratio(b) : 1f;
        }

        public static string DirName(Vector3i d)
        {
            string[] n = Text("feDirNames", "E,W,Up,Down,N,S").Split(',');
            for (int i = 0; i < Dirs.Length && i < n.Length; i++) if (Dirs[i] == d) return n[i];
            return "?";
        }

        /// <summary>World direction of an axial block (for the look-at readout).</summary>
        public static string AxisName(BlockValue bv)
        {
            Vector3i a = Axis(bv);
            if (a.y != 0) return Text("feAxisVertical", "vertical");
            if (a.x != 0) return DirName(new Vector3i(1, 0, 0)) + "-" + DirName(new Vector3i(-1, 0, 0));
            return DirName(new Vector3i(0, 0, 1)) + "-" + DirName(new Vector3i(0, 0, -1));
        }

        /// <summary>UT a source gives (FeTorqueOutput).</summary>
        public static int SourceOutput(Block b)
        {
            int v;
            if (outputByBlock.TryGetValue(b.blockID, out v)) return v;
            v = b.Properties != null && b.Properties.Contains("FeTorqueOutput") ? b.Properties.GetInt("FeTorqueOutput") : 0;
            outputByBlock[b.blockID] = v;
            return v;
        }

        /// <summary>UT a machine costs at base speed (32 RPM).</summary>
        public static int MachineCost(Block b)
        {
            int v;
            if (costByBlock.TryGetValue(b.blockID, out v)) return v;
            if (b.Properties != null && b.Properties.Contains("FeTorqueCost")) v = b.Properties.GetInt("FeTorqueCost");
            else v = Mathf.RoundToInt(PowerGate.MinPower(b) * 64f / 30f);
            costByBlock[b.blockID] = v;
            return v;
        }

        /// <summary>UT a machine costs at this RPM: cost x (rpm / 32)^2.</summary>
        public static int MachineCostAt(Block b, float rpm)
        {
            float s = rpm / BaseRpm;
            return Mathf.CeilToInt(MachineCost(b) * s * s);
        }

        static int Capacity(World world, Vector3i pos, BlockValue bv)
        {
            switch (Kind(bv.Block))
            {
                case KineticKind.Motor:
                {
                    TileEntityPowered p = world.GetTileEntity(pos) as TileEntityPowered;
                    if (p == null) return 0;
                    // D7 had the motor draw the machine's watts; with torque it draws its own block watts again
                    PowerItem item = p.GetPowerItem();
                    int own = bv.Block.Properties.Contains("RequiredPower") ? bv.Block.Properties.GetInt("RequiredPower") : 30;
                    if (item != null && item.RequiredPower != own)
                    {
                        item.RequiredPower = (ushort)own;
                        p.RequiredPower = own;
                    }
                    return p.IsPowered ? SourceOutput(bv.Block) : 0;
                }
                case KineticKind.TorqueCrank:
                    return TorqueState.IsSpinning(pos) ? SourceOutput(bv.Block) : 0;
                case KineticKind.Engine:
                    return TorqueEngine.IsRunning(world, pos) ? SourceOutput(bv.Block) : 0;
                default:
                    return 0;
            }
        }

        /// <summary>Forget cached networks (a speed box changed).</summary>
        public static void Invalidate()
        {
            byNode.Clear();
        }

        /// <summary>The network that node belongs to (null if no torque block there).</summary>
        public static TorqueNet Get(World world, Vector3i node)
        {
            TorqueNet net;
            if (byNode.TryGetValue(node, out net) && UnityEngine.Time.time - net.Time < CacheSeconds) return net;
            BlockValue start = world.GetBlock(node);
            if (Kind(start.Block) == KineticKind.None) return null;
            net = Build(world, node);
            foreach (Vector3i n in net.Nodes) byNode[n] = net;
            return net;
        }

        static bool Same(float a, float b)
        {
            return Mathf.Abs(a - b) <= 0.001f * Mathf.Max(Mathf.Abs(a), Mathf.Abs(b));
        }

        static TorqueNet Build(World world, Vector3i start)
        {
            TorqueNet net = new TorqueNet();
            net.Time = UnityEngine.Time.time;
            bool haveRef = false;
            int sign = 0;   // +1/-1 once a source block fixes the real spin direction (relative spins until then)
            Dictionary<Vector3i, int> machineSpin = new Dictionary<Vector3i, int>();   // parent -> relative spin in
            Queue<Vector3i> open = new Queue<Vector3i>();
            open.Enqueue(start);
            net.Factor[start] = 1f;
            {
                BlockValue sbv = world.GetBlock(start);
                Vector3i a = Axis(sbv);
                net.Omega[start] = a == Vector3i.zero ? new Vector3i(1, 0, 0) : a;
                net.EntryN[start] = new Vector3i(1, 0, 0);
            }
            while (open.Count > 0 && net.Factor.Count <= MaxNodes)
            {
                Vector3i pos = open.Dequeue();
                BlockValue bv = world.GetBlock(pos);
                KineticKind kind = Kind(bv.Block);
                Vector3i axis = Axis(bv);
                Vector3i omega = net.Omega[pos];
                Vector3i entryN = net.EntryN.ContainsKey(pos) ? net.EntryN[pos] : Vector3i.zero;
                float f = net.Factor[pos];
                if (IsSource(kind))
                {
                    // a source turns its own +axis: compare with the spin the network gives it
                    int r = omega == axis ? 1 : -1;
                    if (sign == 0) sign = r;
                    else if (sign != r) net.Locked = true;   // two sources turning against each other
                    int cap = Capacity(world, pos, bv);
                    if (cap > 0)
                    {
                        net.Capacity += cap;
                        net.Sources++;
                        float rr = BaseRpm / f;   // this source turns at BaseRpm
                        if (!haveRef) { net.RefRpm = rr; haveRef = true; }
                        else if (!Same(net.RefRpm, rr)) net.Locked = true;
                    }
                }
                foreach (Vector3i d in Dirs)
                {
                    if (!HasFace(bv, d)) continue;
                    Vector3i n = new Vector3i(pos.x + d.x, pos.y + d.y, pos.z + d.z);
                    BlockValue nb = world.GetBlock(n);
                    Vector3i back = Neg(d);
                    float leave = f * LeaveMult(bv, d);
                    int c = OutSpin(kind, axis, omega, entryN, d);
                    KineticKind nk = Kind(nb.Block);
                    if (nk != KineticKind.None)
                    {
                        if (!HasFace(nb, back)) continue;
                        float nf = leave * EnterMult(nb, back);
                        float seen;
                        if (net.Factor.TryGetValue(n, out seen))
                        {
                            if (!Same(seen, nf)) net.Locked = true;   // a loop that disagrees on speed
                            Vector3i nEntry = net.EntryN.ContainsKey(n) ? net.EntryN[n] : Vector3i.zero;
                            if (OutSpin(nk, Axis(nb), net.Omega[n], nEntry, back) != -c)
                                net.Locked = true;                   // a loop that disagrees on direction
                            continue;
                        }
                        net.Factor[n] = nf;
                        net.Omega[n] = EnterOmega(nk, Axis(nb), d, c);
                        if (nk == KineticKind.Gearbox || nk == KineticKind.Gauge) net.EntryN[n] = back;
                        open.Enqueue(n);
                        continue;
                    }
                    // a machine whose motor socket is this node?
                    if (PowerGate.MinPower(nb.Block) <= 0) continue;
                    Vector3i parent = n;
                    BlockValue pbv = nb;
                    if (nb.ischild && nb.Block.multiBlockPos != null)
                    {
                        parent = nb.Block.multiBlockPos.GetParentPos(n, nb);
                        pbv = world.GetBlock(parent);
                    }
                    if (net.Machines.ContainsKey(parent)) continue;
                    if (PowerGate.SocketPos(pbv, parent) != pos) continue;
                    net.Machines[parent] = leave;
                    net.MachineNode[parent] = pos;
                    machineSpin[parent] = c;   // +1 = turning the right way into the machine (once sign applied)
                }
                if (kind == KineticKind.Regulator) net.Regulators[pos] = new RegZone();
            }
            // real directions: the first source decides (no source at all: keep the relative ones)
            if (sign == 0) sign = 1;
            net.Sign = sign;
            if (sign < 0)
            {
                List<Vector3i> keys = new List<Vector3i>(net.Omega.Keys);
                foreach (Vector3i k in keys) net.Omega[k] = Neg(net.Omega[k]);
            }
            // a machine fed the wrong way round does not run and takes no torque (fix: a Spin Inverter)
            foreach (KeyValuePair<Vector3i, int> m in machineSpin)
            {
                if (m.Value * sign > 0) continue;
                net.WrongSpin[m.Key] = net.MachineNode[m.Key];
                net.Machines.Remove(m.Key);
                net.MachineNode.Remove(m.Key);
            }
            ComputeUsage(world, net);
            return net;
        }

        // D8 T3: usage with Torque Regulators. Each regulator's ZONE = the nodes reached from its output end
        // without passing another regulator (those become its child zones). Root zone = the rest. A zone uses
        // min(wanted, limit), limit = percent x network capacity; when it wants more, its machines slow down so
        // that cost x (speed)^2 fits (scale = sqrt(limit / wanted)). A zone that loops back to the regulator's own
        // input is BYPASSED (the regulator does nothing).
        static void ComputeUsage(World world, TorqueNet net)
        {
            // 1. zones
            foreach (KeyValuePair<Vector3i, RegZone> kv in net.Regulators)
            {
                Vector3i rpos = kv.Key;
                RegZone z = kv.Value;
                BlockValue rbv = world.GetBlock(rpos);
                z.Pos = rpos;
                z.Percent = BlockFeKinetic.LimitPercent(rbv);
                Vector3i outDir = Axis(rbv);
                Vector3i first = new Vector3i(rpos.x + outDir.x, rpos.y + outDir.y, rpos.z + outDir.z);
                if (!net.Factor.ContainsKey(first)) continue;   // nothing connected on the output side
                Queue<Vector3i> open = new Queue<Vector3i>();
                open.Enqueue(first);
                z.Nodes.Add(first);
                while (open.Count > 0)
                {
                    Vector3i p = open.Dequeue();
                    BlockValue pbv = world.GetBlock(p);
                    if (Kind(pbv.Block) == KineticKind.Regulator)
                    {
                        // entered by its input end -> child zone; by its output end -> loop back to the upstream
                        if (p == rpos) { z.Bypassed = true; continue; }
                        if (!z.Children.Contains(p)) z.Children.Add(p);
                        continue;   // do not cross another regulator
                    }
                    foreach (Vector3i d in Dirs)
                    {
                        if (!HasFace(pbv, d)) continue;
                        Vector3i n = new Vector3i(p.x + d.x, p.y + d.y, p.z + d.z);
                        if (z.Nodes.Contains(n) || !net.Factor.ContainsKey(n)) continue;
                        if (n == rpos)
                        {
                            // back at our own regulator: only fine through its output end (where we started)
                            if (d != new Vector3i(-outDir.x, -outDir.y, -outDir.z)) z.Bypassed = true;
                            continue;
                        }
                        BlockValue nb = world.GetBlock(n);
                        if (!HasFace(nb, new Vector3i(-d.x, -d.y, -d.z))) continue;
                        z.Nodes.Add(n);
                        open.Enqueue(n);
                    }
                }
                // a child regulator entered through its OUTPUT end belongs upstream of it, not to us
                z.Children.RemoveAll(c => !EnteredByInput(world, c, z.Nodes, rpos));
            }

            // 2. limits from the network capacity
            foreach (RegZone z in net.Regulators.Values)
                z.Limit = Mathf.FloorToInt(net.Capacity * z.Percent / 100f);

            // 3. wanted UT per machine, then zones bottom-up (memoized recursion)
            Dictionary<Vector3i, int> machineCost = new Dictionary<Vector3i, int>();
            foreach (KeyValuePair<Vector3i, float> m in net.Machines)
                machineCost[m.Key] = MachineCostAt(world.GetBlock(m.Key).Block, ClampRpm(net.RefRpm * m.Value));
            HashSet<Vector3i> inZone = new HashSet<Vector3i>();
            foreach (RegZone z in net.Regulators.Values) if (!z.Bypassed) inZone.UnionWith(z.Nodes);

            Dictionary<Vector3i, int> done = new Dictionary<Vector3i, int>();
            int root = 0;
            foreach (KeyValuePair<Vector3i, int> m in machineCost)
            {
                Vector3i node = net.MachineNode[m.Key];
                if (!inZone.Contains(node)) root += m.Value;
            }
            HashSet<Vector3i> childOfSomeone = new HashSet<Vector3i>();
            foreach (RegZone z in net.Regulators.Values) if (!z.Bypassed) childOfSomeone.UnionWith(z.Children);
            foreach (KeyValuePair<Vector3i, RegZone> kv in net.Regulators)
            {
                if (kv.Value.Bypassed || childOfSomeone.Contains(kv.Key)) continue;
                root += ZoneUsed(net, kv.Key, machineCost, done, 0);
            }
            net.Usage = root;

            // 4. slow-down of the machines inside limited zones (inner zones inherit the outer scale)
            foreach (KeyValuePair<Vector3i, RegZone> kv in net.Regulators)
            {
                if (kv.Value.Bypassed || childOfSomeone.Contains(kv.Key)) continue;
                ApplyScale(net, kv.Key, 1f, 0);
            }
        }

        static bool EnteredByInput(World world, Vector3i reg, HashSet<Vector3i> zoneNodes, Vector3i owner)
        {
            BlockValue bv = world.GetBlock(reg);
            Vector3i a = Axis(bv);
            Vector3i inNeighbor = new Vector3i(reg.x - a.x, reg.y - a.y, reg.z - a.z);
            return inNeighbor == owner || zoneNodes.Contains(inNeighbor);
        }

        static int ZoneUsed(TorqueNet net, Vector3i reg, Dictionary<Vector3i, int> machineCost,
                            Dictionary<Vector3i, int> done, int depth)
        {
            int v;
            if (done.TryGetValue(reg, out v)) return v;
            RegZone z = net.Regulators[reg];
            int wanted = 0;
            if (depth < 16)
            {
                foreach (KeyValuePair<Vector3i, int> m in machineCost)
                    if (z.Nodes.Contains(net.MachineNode[m.Key])) wanted += m.Value;
                foreach (Vector3i c in z.Children)
                    if (net.Regulators.ContainsKey(c) && !net.Regulators[c].Bypassed)
                        wanted += ZoneUsed(net, c, machineCost, done, depth + 1);
            }
            z.Wanted = wanted;
            z.Used = Mathf.Min(wanted, z.Limit);
            z.Scale = wanted > z.Limit ? (z.Limit <= 0 ? 0f : Mathf.Sqrt((float)z.Limit / wanted)) : 1f;
            done[reg] = z.Used;
            return z.Used;
        }

        static void ApplyScale(TorqueNet net, Vector3i reg, float outer, int depth)
        {
            RegZone z = net.Regulators[reg];
            float s = outer * z.Scale;
            foreach (KeyValuePair<Vector3i, Vector3i> m in net.MachineNode)
                if (z.Nodes.Contains(m.Value)) net.MachineScale[m.Key] = s;
            if (depth >= 16) return;
            foreach (Vector3i c in z.Children)
                if (net.Regulators.ContainsKey(c) && !net.Regulators[c].Bypassed) ApplyScale(net, c, s, depth + 1);
        }

        internal static string Text(string key, string fallback)
        {
            string s;
            return Localization.TryGet(key, out s) && !string.IsNullOrEmpty(s) ? s : fallback;
        }
    }

    // Look at a shaft / gearbox / speed box / motor: show the network (RPM here, UT used / available, overload).
    // E on a speed box cycles its ratio.
    public class KineticLookController : MonoBehaviour
    {
        static GameObject host;
        string prompt;
        LocalPlayerUI promptUi;
        float nextUpdate;
        string lastShaftLog;

        public static void Ensure()
        {
            if (host != null || GameManager.IsDedicatedServer) return;
            host = new GameObject("FerroEngrenagem.KineticLookController");
            Object.DontDestroyOnLoad(host);
            host.AddComponent<KineticLookController>();
        }

        public static string Status(TorqueNet net, Vector3i node)
        {
            if (net == null) return "";
            if (net.Locked) return Kinetic.Text("feNetLocked", "LOCKED: sources would turn at different speeds");
            if (net.Capacity <= 0)
                return string.Format(Kinetic.Text("feNetStopped", "Stopped: no torque source ({0} UT needed)"), net.Usage);
            if (net.Overloaded)
                return string.Format(Kinetic.Text("feNetOverload", "OVERLOADED: {0}/{1} UT"), net.Usage, net.Capacity);
            return string.Format(Kinetic.Text("feNetRunning", "{0} RPM - {1}/{2} UT"),
                                 Mathf.RoundToInt(net.RpmAt(node)), net.Usage, net.Capacity);
        }

        bool Looking(out World world, out EntityPlayerLocal player, out LocalPlayerUI ui, out Vector3i pos,
                     out BlockValue bv)
        {
            world = null; player = null; ui = null; pos = Vector3i.zero; bv = BlockValue.Air;
            GameManager gm = GameManager.Instance;
            world = gm == null ? null : gm.World;
            player = world == null ? null : world.GetPrimaryPlayer();
            if (player == null || player.IsDead()) return false;
            WorldRayHitInfo hit = player.HitInfo;
            if (hit == null || !hit.bHitValid || !GameUtils.IsBlockOrTerrain(hit.tag)) return false;
            if (hit.hit.distanceSq > 25f) return false;
            bv = hit.hit.blockValue;
            pos = hit.hit.blockPos;
            ui = player.PlayerUI;
            if (ui == null || ui.windowManager == null) return false;
            if (ui.windowManager.IsModalWindowOpen() || ui.windowManager.IsCursorWindowOpen()) return false;
            return true;
        }

        void Update()
        {
            World world;
            EntityPlayerLocal player;
            LocalPlayerUI ui;
            Vector3i pos;
            BlockValue bv;
            bool looking = Looking(out world, out player, out ui, out pos, out bv);

            // E on a speed box / clutch / regulator: next setting (every frame, so the key press is not missed)
            int settings = looking ? BlockFeKinetic.Settings(Kinetic.Kind(bv.Block)) : 0;
            if (settings > 0 && !player.IsCrouching && WasActivatePressed(player))
            {
                BlockValue nbv = bv;
                nbv.meta = (byte)((bv.meta + 1) % settings);
                world.SetBlockRPC(pos, nbv);
                Kinetic.Invalidate();
                nextUpdate = 0f;
                Log.Out(FerroEngrenagemMod.LogPrefix + bv.Block.GetBlockName() + " at " + pos + " -> setting " + nbv.meta);
            }

            if (UnityEngine.Time.time < nextUpdate) return;
            nextUpdate = UnityEngine.Time.time + 0.2f;
            prompt = null;
            promptUi = null;
            if (!looking || player.IsCrouching) return;   // crouching: the vanilla "take" prompt
            bv = world.GetBlock(pos);
            KineticKind kind = Kinetic.Kind(bv.Block);
            if (kind == KineticKind.None || kind == KineticKind.TorqueCrank) return;   // the crank has its own prompt
            TorqueNet net = Kinetic.Get(world, pos);
            string name = bv.Block.GetLocalizedBlockName();
            if (kind == KineticKind.Shaft)
            {
                name += " (" + Kinetic.AxisName(bv) + ")";
                // diagnostic while the placeholder model's axis is confirmed in game
                string key = pos + "|" + bv.rotation;
                if (key != lastShaftLog)
                {
                    lastShaftLog = key;
                    Log.Out(FerroEngrenagemMod.LogPrefix + "look shaft at " + pos + " rot=" + bv.rotation +
                            " axis=" + Kinetic.AxisName(bv) + " net nodes=" + (net == null ? 0 : net.Nodes.Count));
                }
            }
            else if (kind == KineticKind.SpeedBox)
            {
                Vector3i a = Kinetic.Axis(bv);
                float ratio = BlockFeKinetic.Ratio(bv);
                name += " " + RatioText(ratio) + "\n" + string.Format(
                    Kinetic.Text("feSpeedBoxInfo", "in: {0} side, out: {1} side - {2} to change"),
                    Kinetic.DirName(new Vector3i(-a.x, -a.y, -a.z)), Kinetic.DirName(a), KeyName(player));
                if (net != null && net.Running)
                    name += "\n" + string.Format(Kinetic.Text("feSpeedBoxRpm", "{0} RPM in, {1} RPM out"),
                        Mathf.RoundToInt(net.RpmAt(pos)), Mathf.RoundToInt(Kinetic.ClampRpm(net.RpmAt(pos) * ratio)));
            }
            else if (kind == KineticKind.Clutch)
            {
                name += ": " + (BlockFeKinetic.Engaged(bv) ? Kinetic.Text("feClutchOn", "engaged")
                                                          : Kinetic.Text("feClutchOff", "released")) +
                        " - " + string.Format(Kinetic.Text("feKeyToChange", "{0} to change"), KeyName(player));
                if (!BlockFeKinetic.Engaged(bv)) { prompt = name; promptUi = ui; return; }   // its own net is just itself
            }
            else if (kind == KineticKind.Regulator)
            {
                Vector3i a = Kinetic.Axis(bv);
                name += " " + BlockFeKinetic.LimitPercent(bv) + "%\n" + string.Format(
                    Kinetic.Text("feSpeedBoxInfo", "in: {0} side, out: {1} side - {2} to change"),
                    Kinetic.DirName(new Vector3i(-a.x, -a.y, -a.z)), Kinetic.DirName(a), KeyName(player));
                RegZone z;
                if (net != null && net.Regulators.TryGetValue(pos, out z))
                {
                    if (z.Bypassed) name += "\n" + Kinetic.Text("feRegBypassed", "Bypassed: the output loops back to the input side");
                    else
                    {
                        name += "\n" + string.Format(Kinetic.Text("feRegInfo", "Lets through {0} UT, behind it wants {1} UT"),
                                                     z.Limit, z.Wanted);
                        if (z.Scale < 0.999f)
                            name += " - " + string.Format(Kinetic.Text("feRegSlow", "machines at {0}% speed"),
                                                          Mathf.RoundToInt(z.Scale * 100f));
                    }
                }
            }
            else if (kind == KineticKind.Gauge && net != null)
            {
                int pct = net.Capacity > 0 ? Mathf.RoundToInt(100f * net.Usage / net.Capacity) : 0;
                name += "\n" + string.Format(Kinetic.Text("feGaugeInfo",
                            "Sources: {0} - Machines: {1} - Regulators: {2} - Load: {3}%"),
                            net.Sources, net.Machines.Count, net.Regulators.Count, pct);
            }
            if (kind == KineticKind.Motor || kind == KineticKind.Clutch || kind == KineticKind.Inverter)
                name += " (" + Kinetic.AxisName(bv) + ")";
            prompt = name + "\n" + Status(net, pos);
            if (kind == KineticKind.Engine)
                prompt += "\n" + string.Format(Kinetic.Text("feEngineOpen", "{0} to open (fuel, on/off)"), KeyName(player));
            if (net != null)
                foreach (KeyValuePair<Vector3i, Vector3i> w in net.WrongSpin)
                    if (w.Value == pos)
                        prompt += "\n" + string.Format(Kinetic.Text("feWrongSpin",
                            "{0} turns the wrong way: add a Spin Inverter"), world.GetBlock(w.Key).Block.GetLocalizedBlockName());
            promptUi = ui;
        }

        void LateUpdate()
        {
            if (prompt != null && promptUi != null) XUiC_InteractionPrompt.SetText(promptUi, prompt);
        }

        static string RatioText(float r)
        {
            return r < 1f ? "x1/" + Mathf.RoundToInt(1f / r) : "x" + Mathf.RoundToInt(r);
        }

        static bool WasActivatePressed(EntityPlayerLocal player)
        {
            PlayerActionsLocal input = player.playerInput;
            if (input == null) return false;
            if (input.Activate != null && input.Activate.WasPressed) return true;
            PlayerActionsPermanent perm = input.PermanentActions;
            return perm != null && perm.Activate != null && perm.Activate.WasPressed;
        }

        static string KeyName(EntityPlayerLocal player)
        {
            PlayerActionsLocal input = player.playerInput;
            if (input == null || input.PermanentActions == null) return "[E]";
            return XUiUtils.GetBindingXuiMarkupString(input.PermanentActions.Activate,
                XUiUtils.EmptyBindingStyle.EmptyString, XUiUtils.DisplayStyle.Plain, null);
        }
    }
}
