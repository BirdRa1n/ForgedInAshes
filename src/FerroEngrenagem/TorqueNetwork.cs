// D8 T1: mechanical TORQUE network (Create-like). See PLANO_MOD.md 5.4.
//
// Nodes are blocks that carry torque, joined face to face:
//   Shaft      (BlockFeKinetic, FeKinetic="shaft")   two faces along its axis (FeShaftAxis in model space,
//                                                    turned by the block rotation like multiblock cells)
//   Gearbox    (BlockFeKinetic, FeKinetic="gearbox") all six faces
//   Motor      (FeMotor=true, Electric Motor)        all six faces; source: FeTorqueOutput UT while powered
//   TorqueCrank(BlockFeTorqueCrank)                  all six faces; source: FeTorqueOutput UT while turned
// A power-gated machine (FeMinPower) is a CONSUMER of the node sitting in its motor socket
// (PowerGate.SocketPos), if that node has a face pointing into the machine. It costs FeTorqueCost UT
// (default: FeMinPower x 64 / 30, so 30/60/90 W -> 64/128/192 UT) whenever it is connected (idle or not).
//
// Network = flood fill from a node. Capacity = sum of the sources; usage = sum of the machines. All sources
// spin at 32 RPM in T1 (speed boxes come in T2). usage > capacity = OVERLOADED: every machine of the network
// stops. Networks are rebuilt lazily, at most every CacheSeconds per node (block changes show up within that).
//
// Runs wherever the power gate runs (SP / host / server). The look-at readout (KineticLookController) runs
// the same flood fill on the client; on a pure MP client a motor's IsPowered comes from the synced tile entity.
//
// C# 5 only.

using System.Collections.Generic;
using UnityEngine;

namespace FerroEngrenagem
{
    public enum KineticKind { None, Shaft, Gearbox, Motor, TorqueCrank }

    [UnityEngine.Scripting.Preserve]
    public class BlockFeKinetic : Block
    {
        public KineticKind Kind = KineticKind.Gearbox;
        public Vector3i ShaftAxis = new Vector3i(0, 0, 1);   // pipe_straight.fbx lies along local Z (D8 T1 test)

        public override void Init()
        {
            base.Init();
            string k = Properties != null && Properties.Contains("FeKinetic")
                ? Properties.GetString("FeKinetic").Trim().ToLowerInvariant() : "gearbox";
            Kind = k == "shaft" ? KineticKind.Shaft : KineticKind.Gearbox;
            if (Properties != null && Properties.Contains("FeShaftAxis"))
            {
                switch (Properties.GetString("FeShaftAxis").Trim().ToLowerInvariant())
                {
                    case "x": ShaftAxis = new Vector3i(1, 0, 0); break;
                    case "z": ShaftAxis = new Vector3i(0, 0, 1); break;
                    default: ShaftAxis = new Vector3i(0, 1, 0); break;
                }
            }
            KineticLookController.Ensure();
            MotorSocketMarker.Ensure();
        }
    }

    public class TorqueNet
    {
        public readonly HashSet<Vector3i> Nodes = new HashSet<Vector3i>();
        public readonly HashSet<Vector3i> Machines = new HashSet<Vector3i>();   // machine parent positions
        public int Capacity;
        public int Usage;
        public int Sources;
        public int Rpm = 32;
        public float Time;

        public bool Overloaded { get { return Capacity > 0 && Usage > Capacity; } }
        public bool Running { get { return Capacity > 0 && !Overloaded; } }
    }

    public static class Kinetic
    {
        public const int BaseRpm = 32;
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

        public static KineticKind Kind(Block b)
        {
            if (b == null) return KineticKind.None;
            BlockFeKinetic k = b as BlockFeKinetic;
            if (k != null) return k.Kind;
            if (b is BlockFeTorqueCrank) return KineticKind.TorqueCrank;
            if (PowerGate.IsMotor(b)) return KineticKind.Motor;
            return KineticKind.None;
        }

        public static bool HasFace(BlockValue bv, Vector3i dir)
        {
            BlockFeKinetic k = bv.Block as BlockFeKinetic;
            if (k == null || k.Kind != KineticKind.Shaft) return Kind(bv.Block) != KineticKind.None;
            Vector3 a = k.shape.GetRotation(bv) * k.ShaftAxis.ToVector3();
            Vector3i axis = new Vector3i(Mathf.RoundToInt(a.x), Mathf.RoundToInt(a.y), Mathf.RoundToInt(a.z));
            return dir == axis || dir == new Vector3i(-axis.x, -axis.y, -axis.z);
        }

        /// <summary>World direction of the shaft's axis (for the look-at readout).</summary>
        public static string AxisName(BlockValue bv)
        {
            if (HasFace(bv, new Vector3i(0, 1, 0))) return "vertical";
            if (HasFace(bv, new Vector3i(1, 0, 0))) return "E-W";
            return "N-S";
        }

        /// <summary>UT a source gives (FeTorqueOutput); also the motor draws its own block watts again.</summary>
        public static int SourceOutput(Block b)
        {
            int v;
            if (outputByBlock.TryGetValue(b.blockID, out v)) return v;
            v = b.Properties != null && b.Properties.Contains("FeTorqueOutput") ? b.Properties.GetInt("FeTorqueOutput") : 0;
            outputByBlock[b.blockID] = v;
            return v;
        }

        /// <summary>UT a machine costs at base speed.</summary>
        public static int MachineCost(Block b)
        {
            int v;
            if (costByBlock.TryGetValue(b.blockID, out v)) return v;
            if (b.Properties != null && b.Properties.Contains("FeTorqueCost")) v = b.Properties.GetInt("FeTorqueCost");
            else v = Mathf.RoundToInt(PowerGate.MinPower(b) * 64f / 30f);
            costByBlock[b.blockID] = v;
            return v;
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

        static TorqueNet Build(World world, Vector3i start)
        {
            TorqueNet net = new TorqueNet();
            net.Time = UnityEngine.Time.time;
            Queue<Vector3i> open = new Queue<Vector3i>();
            open.Enqueue(start);
            net.Nodes.Add(start);
            while (open.Count > 0 && net.Nodes.Count <= MaxNodes)
            {
                Vector3i pos = open.Dequeue();
                BlockValue bv = world.GetBlock(pos);
                int cap = Capacity(world, pos, bv);
                if (cap > 0) { net.Capacity += cap; net.Sources++; }
                foreach (Vector3i d in Dirs)
                {
                    if (!HasFace(bv, d)) continue;
                    Vector3i n = new Vector3i(pos.x + d.x, pos.y + d.y, pos.z + d.z);
                    if (net.Nodes.Contains(n)) continue;
                    BlockValue nb = world.GetBlock(n);
                    if (Kind(nb.Block) != KineticKind.None)
                    {
                        if (HasFace(nb, new Vector3i(-d.x, -d.y, -d.z)))
                        {
                            net.Nodes.Add(n);
                            open.Enqueue(n);
                        }
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
                    if (net.Machines.Contains(parent)) continue;
                    if (PowerGate.SocketPos(pbv, parent) != pos) continue;
                    net.Machines.Add(parent);
                    net.Usage += MachineCost(pbv.Block);
                }
            }
            return net;
        }
    }

    // Look at a shaft / gearbox / motor: show the network (RPM, UT used / available, overload).
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

        public static string Status(TorqueNet net)
        {
            if (net == null) return "";
            if (net.Capacity <= 0)
                return string.Format(Text("feNetStopped", "Stopped: no torque source ({0} UT needed)"), net.Usage);
            if (net.Overloaded)
                return string.Format(Text("feNetOverload", "OVERLOADED: {0}/{1} UT"), net.Usage, net.Capacity);
            return string.Format(Text("feNetRunning", "{0} RPM - {1}/{2} UT"), net.Rpm, net.Usage, net.Capacity);
        }

        void Update()
        {
            if (UnityEngine.Time.time < nextUpdate) return;
            nextUpdate = UnityEngine.Time.time + 0.2f;
            prompt = null;
            promptUi = null;
            GameManager gm = GameManager.Instance;
            World world = gm == null ? null : gm.World;
            EntityPlayerLocal player = world == null ? null : world.GetPrimaryPlayer();
            if (player == null || player.IsDead()) return;
            WorldRayHitInfo hit = player.HitInfo;
            if (hit == null || !hit.bHitValid || !GameUtils.IsBlockOrTerrain(hit.tag)) return;
            if (hit.hit.distanceSq > 25f) return;
            BlockValue bv = hit.hit.blockValue;
            KineticKind kind = Kinetic.Kind(bv.Block);
            if (kind == KineticKind.None || kind == KineticKind.TorqueCrank) return;   // the crank has its own prompt
            LocalPlayerUI ui = player.PlayerUI;
            if (ui == null || ui.windowManager == null) return;
            if (ui.windowManager.IsModalWindowOpen() || ui.windowManager.IsCursorWindowOpen()) return;
            TorqueNet net = Kinetic.Get(world, hit.hit.blockPos);
            string name = bv.Block.GetLocalizedBlockName();
            if (kind == KineticKind.Shaft)
            {
                name += " (" + Kinetic.AxisName(bv) + ")";
                // diagnostic while the placeholder model's axis is confirmed in game
                string key = hit.hit.blockPos + "|" + bv.rotation;
                if (key != lastShaftLog)
                {
                    lastShaftLog = key;
                    Log.Out(FerroEngrenagemMod.LogPrefix + "look shaft at " + hit.hit.blockPos + " rot=" + bv.rotation +
                            " axis=" + Kinetic.AxisName(bv) + " net nodes=" + (net == null ? 0 : net.Nodes.Count));
                }
            }
            prompt = name + "\n" + Status(net);
            promptUi = ui;
        }

        void LateUpdate()
        {
            if (prompt != null && promptUi != null) XUiC_InteractionPrompt.SetText(promptUi, prompt);
        }

        static string Text(string key, string fallback)
        {
            string s;
            return Localization.TryGet(key, out s) && !string.IsNullOrEmpty(s) ? s : fallback;
        }
    }
}
