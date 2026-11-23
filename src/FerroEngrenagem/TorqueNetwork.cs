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
    public enum KineticKind { None, Shaft, Gearbox, SpeedBox, Motor, TorqueCrank }

    [UnityEngine.Scripting.Preserve]
    public class BlockFeKinetic : Block
    {
        public static readonly float[] Ratios = { 2f, 4f, 0.5f };   // speed box setting = block meta

        public KineticKind Kind = KineticKind.Gearbox;
        public Vector3i ShaftAxis = new Vector3i(0, 0, 1);   // pipe_straight.fbx lies along local Z (D8 T1 test)

        public override void Init()
        {
            base.Init();
            string k = Properties != null && Properties.Contains("FeKinetic")
                ? Properties.GetString("FeKinetic").Trim().ToLowerInvariant() : "gearbox";
            Kind = k == "shaft" ? KineticKind.Shaft : k == "speedbox" ? KineticKind.SpeedBox : KineticKind.Gearbox;
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

        // E on a speed box changes its ratio (KineticLookController); no radial.
        public override bool HasBlockActivationCommands(WorldBase _world, BlockValue _blockValue, Vector3i _blockPos,
                                                        EntityAlive _entityFocusing)
        {
            return false;
        }
    }

    public class TorqueNet
    {
        public readonly Dictionary<Vector3i, float> Factor = new Dictionary<Vector3i, float>();   // node -> speed factor
        public readonly Dictionary<Vector3i, float> Machines = new Dictionary<Vector3i, float>(); // parent -> factor
        public int Capacity;
        public int Usage;
        public int Sources;
        public float RefRpm = Kinetic.BaseRpm;   // RPM of a node with factor 1
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
            return KineticKind.None;
        }

        /// <summary>World direction of an axial block's +axis (shaft / speed box); zero for the others.</summary>
        public static Vector3i Axis(BlockValue bv)
        {
            BlockFeKinetic k = bv.Block as BlockFeKinetic;
            if (k == null || (k.Kind != KineticKind.Shaft && k.Kind != KineticKind.SpeedBox)) return Vector3i.zero;
            Vector3 a = k.shape.GetRotation(bv) * k.ShaftAxis.ToVector3();
            return new Vector3i(Mathf.RoundToInt(a.x), Mathf.RoundToInt(a.y), Mathf.RoundToInt(a.z));
        }

        public static bool HasFace(BlockValue bv, Vector3i dir)
        {
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
            Queue<Vector3i> open = new Queue<Vector3i>();
            open.Enqueue(start);
            net.Factor[start] = 1f;
            while (open.Count > 0 && net.Factor.Count <= MaxNodes)
            {
                Vector3i pos = open.Dequeue();
                BlockValue bv = world.GetBlock(pos);
                float f = net.Factor[pos];
                int cap = Capacity(world, pos, bv);
                if (cap > 0)
                {
                    net.Capacity += cap;
                    net.Sources++;
                    float r = BaseRpm / f;   // this source turns at BaseRpm
                    if (!haveRef) { net.RefRpm = r; haveRef = true; }
                    else if (!Same(net.RefRpm, r)) net.Locked = true;
                }
                foreach (Vector3i d in Dirs)
                {
                    if (!HasFace(bv, d)) continue;
                    Vector3i n = new Vector3i(pos.x + d.x, pos.y + d.y, pos.z + d.z);
                    BlockValue nb = world.GetBlock(n);
                    Vector3i back = new Vector3i(-d.x, -d.y, -d.z);
                    float leave = f * LeaveMult(bv, d);
                    if (Kind(nb.Block) != KineticKind.None)
                    {
                        if (!HasFace(nb, back)) continue;
                        float nf = leave * EnterMult(nb, back);
                        float seen;
                        if (net.Factor.TryGetValue(n, out seen))
                        {
                            if (!Same(seen, nf)) net.Locked = true;   // a loop that disagrees on speed
                            continue;
                        }
                        net.Factor[n] = nf;
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
                }
            }
            foreach (KeyValuePair<Vector3i, float> m in net.Machines)
                net.Usage += MachineCostAt(world.GetBlock(m.Key).Block, ClampRpm(net.RefRpm * m.Value));
            return net;
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

            // E on a speed box: next ratio (every frame, so the key press is not missed)
            if (looking && Kinetic.Kind(bv.Block) == KineticKind.SpeedBox && WasActivatePressed(player))
            {
                BlockValue nbv = bv;
                nbv.meta = (byte)((bv.meta + 1) % BlockFeKinetic.Ratios.Length);
                world.SetBlockRPC(pos, nbv);
                Kinetic.Invalidate();
                nextUpdate = 0f;
                Log.Out(FerroEngrenagemMod.LogPrefix + "speed box at " + pos + " -> x" + BlockFeKinetic.Ratio(nbv));
            }

            if (UnityEngine.Time.time < nextUpdate) return;
            nextUpdate = UnityEngine.Time.time + 0.2f;
            prompt = null;
            promptUi = null;
            if (!looking) return;
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
            prompt = name + "\n" + Status(net, pos);
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
