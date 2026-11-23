// D7 + D8: machines run on TORQUE. A machine block opts in with <property name="FeMinPower" value="30"/>
// (historic name; its torque cost is FeTorqueCost or FeMinPower x 64/30 UT). It crafts only while the block in
// its MOTOR SOCKET belongs to a running torque network (TorqueNetwork.cs) that counts it as a consumer: an
// Electric Motor wired to power, a Torque Crank being turned, or shafts / gearboxes leading to them.
//
// Motor socket (user, 2026-11-22: "the motor must be in a specific position to plug it into the machine"):
// the block cell next to the machine's footprint on the side FeMotorSide (back|front|left|right, default back),
// at the machine's lowest layer, in the middle column (left-of-middle for even widths). Computed in the
// machine's local space and rotated like vanilla rotates multiblock cells (MultiBlockArray.Get: shape rotation
// * local pos, rounded). MotorSocketMarker.cs draws it while the player holds a motor.
//
// Vanilla crafting runs in two places (IL of 3.4.0 b10):
//  - window closed: TileEntityWorkstation.HandleRecipeQueue(float) (from UpdateTick) -> Prefix skips it.
//  - window open:   XUiC_RecipeStack.Update counts down while the queue "IsCrafting"; vanilla halts/resumes the
//                   queue in XUiC_WorkstationWindowGroup.Update from the fuel state -> Postfix halts/resumes
//                   it from our power state instead.
//
// C# 5 only.

using System.Collections.Generic;
using HarmonyLib;
using UnityEngine;

namespace FerroEngrenagem
{
    public static class PowerGate
    {
        public const string MinPowerProperty = "FeMinPower";
        public const string MotorProperty = "FeMotor";
        public const string MotorSideProperty = "FeMotorSide";
        const float CacheSeconds = 0.5f;

        static readonly Dictionary<int, int> minPowerByBlock = new Dictionary<int, int>();
        static readonly Dictionary<int, bool> motorByBlock = new Dictionary<int, bool>();
        static readonly Dictionary<int, Vector3i> sideByBlock = new Dictionary<int, Vector3i>();
        static readonly Dictionary<Vector3i, KeyValuePair<float, bool>> poweredCache =
            new Dictionary<Vector3i, KeyValuePair<float, bool>>();

        public static int MinPower(Block block)
        {
            if (block == null) return 0;
            int v;
            if (minPowerByBlock.TryGetValue(block.blockID, out v)) return v;
            v = 0;
            DynamicProperties p = block.Properties;
            if (p != null && p.Contains(MinPowerProperty)) v = p.GetInt(MinPowerProperty);
            minPowerByBlock[block.blockID] = v;
            return v;
        }

        public static bool IsMotor(Block block)
        {
            if (block == null) return false;
            bool v;
            if (motorByBlock.TryGetValue(block.blockID, out v)) return v;
            DynamicProperties p = block.Properties;
            v = p != null && p.Contains(MotorProperty) && p.GetBool(MotorProperty);
            motorByBlock[block.blockID] = v;
            return v;
        }

        /// <summary>Something that can sit in a motor socket and drive the machine (motor or torque crank).</summary>
        public static bool IsDriver(Block block)
        {
            return Kinetic.Kind(block) != KineticKind.None;
        }

        public static bool IsGated(TileEntityWorkstation te)
        {
            return te != null && MinPower(te.blockValue.Block) > 0;
        }

        /// <summary>Local direction (machine space) of the side that holds the motor socket.</summary>
        static Vector3i Side(Block block)
        {
            Vector3i v;
            if (sideByBlock.TryGetValue(block.blockID, out v)) return v;
            string s = block.Properties != null && block.Properties.Contains(MotorSideProperty)
                ? block.Properties.GetString(MotorSideProperty).Trim().ToLowerInvariant() : "back";
            switch (s)
            {
                case "front": v = new Vector3i(0, 0, 1); break;
                case "left": v = new Vector3i(-1, 0, 0); break;
                case "right": v = new Vector3i(1, 0, 0); break;
                default: v = new Vector3i(0, 0, -1); break;
            }
            sideByBlock[block.blockID] = v;
            return v;
        }

        /// <summary>World position of the motor socket of the machine whose PARENT block is at parentPos.</summary>
        public static Vector3i SocketPos(BlockValue machine, Vector3i parentPos)
        {
            Block block = machine.Block;
            Vector3i side = Side(block);
            // local footprint cells (single block: just the origin)
            List<Vector3i> cells = new List<Vector3i>();
            if (block.isMultiBlock && block.multiBlockPos != null)
                cells.AddRange(block.multiBlockPos.pos);
            else
                cells.Add(Vector3i.zero);

            int minY = int.MaxValue;
            foreach (Vector3i c in cells) if (c.y < minY) minY = c.y;
            // the outermost cells on the socket side, at the lowest layer
            bool alongX = side.x != 0;
            int edge = int.MinValue;
            foreach (Vector3i c in cells)
            {
                if (c.y != minY) continue;
                int d = alongX ? c.x * side.x : c.z * side.z;
                if (d > edge) edge = d;
            }
            List<int> across = new List<int>();
            foreach (Vector3i c in cells)
            {
                if (c.y != minY) continue;
                int d = alongX ? c.x * side.x : c.z * side.z;
                if (d != edge) continue;
                int a = alongX ? c.z : c.x;
                if (!across.Contains(a)) across.Add(a);
            }
            across.Sort();
            int mid = across.Count == 0 ? 0 : across[(across.Count - 1) / 2];
            Vector3i local = alongX
                ? new Vector3i(edge * side.x + side.x, minY, mid)
                : new Vector3i(mid, minY, edge * side.z + side.z);

            Vector3 r = block.shape.GetRotation(machine) * local.ToVector3();
            return new Vector3i(parentPos.x + Mathf.RoundToInt(r.x), parentPos.y + Mathf.RoundToInt(r.y),
                                parentPos.z + Mathf.RoundToInt(r.z));
        }

        /// <summary>D8: the node in this machine's socket belongs to a running torque network that counts this
        /// machine as a consumer (TorqueNetwork.cs).</summary>
        public static bool HasPower(TileEntityWorkstation te)
        {
            if (te == null || MinPower(te.blockValue.Block) <= 0) return true;
            Vector3i pos = te.ToWorldPos();
            float now = Time.time;
            KeyValuePair<float, bool> cached;
            if (poweredCache.TryGetValue(pos, out cached) && now - cached.Key < CacheSeconds) return cached.Value;

            bool ok = false;
            float speed = 1f;
            Vector3i socket = Vector3i.zero;
            string info = "no world";
            World world = GameManager.Instance == null ? null : GameManager.Instance.World;
            if (world != null)
            {
                socket = SocketPos(world.GetBlock(pos), pos);
                TorqueNet net = Kinetic.Get(world, socket);
                if (net == null) info = "socket empty";
                else if (net.WrongSpin.ContainsKey(pos)) info = "wrong spin direction (needs a Spin Inverter)";
                else if (!net.Machines.ContainsKey(pos)) info = "socket block does not face the machine";
                else
                {
                    ok = net.Running;
                    float rpm = net.MachineRpm(pos);
                    speed = net.MachineSpeed(pos);
                    info = "net nodes=" + net.Nodes.Count + " sources=" + net.Sources + " machines=" + net.Machines.Count
                           + " " + net.Usage + "/" + net.Capacity + " UT rpm=" + Mathf.RoundToInt(rpm) + " speed=x" +
                           speed.ToString("0.##") + (net.Overloaded ? " OVERLOAD" : "") + (net.Locked ? " LOCKED(" + net.LockReason + ")" : "");
                }
            }
            // Diagnostic: one line whenever the result or the network summary for this machine changes.
            string key = ok + "|" + socket + "|" + info;
            string lastKey;
            if (!lastLog.TryGetValue(pos, out lastKey) || lastKey != key)
            {
                lastLog[pos] = key;
                Log.Out(FerroEngrenagemMod.LogPrefix + "power " + te.blockValue.Block.GetBlockName() + " at " + pos +
                        " rot=" + te.blockValue.rotation + " socket=" + socket + " cost=" +
                        Kinetic.MachineCost(te.blockValue.Block) + " UT: " + info + " -> " + (ok ? "ON" : "OFF"));
            }
            poweredCache[pos] = new KeyValuePair<float, bool>(now, ok);
            speedCache[pos] = speed;
            return ok;
        }

        static readonly Dictionary<Vector3i, float> speedCache = new Dictionary<Vector3i, float>();

        /// <summary>D8 T2: crafting speed multiplier of a powered machine (its RPM / 32). 1 when not gated.</summary>
        public static float Speed(TileEntityWorkstation te)
        {
            if (!IsGated(te) || !HasPower(te)) return 1f;
            float v;
            return speedCache.TryGetValue(te.ToWorldPos(), out v) ? v : 1f;
        }

        static readonly Dictionary<Vector3i, string> lastLog = new Dictionary<Vector3i, string>();
    }

    // window closed: the tile entity does not advance its queue without power; with power, time runs x Speed
    [HarmonyPatch(typeof(TileEntityWorkstation), "HandleRecipeQueue")]
    public static class Patch_TEW_HandleRecipeQueue
    {
        public static bool Prefix(TileEntityWorkstation __instance, ref float _timePassed)
        {
            if (!PowerGate.IsGated(__instance)) return true;
            if (!PowerGate.HasPower(__instance)) return false;
            _timePassed *= PowerGate.Speed(__instance);
            return true;
        }
    }

    // window open: halt / resume the UI queue like vanilla does for fuel, and remember which queue is the
    // open machine's (its recipe stacks count down x Speed)
    [HarmonyPatch(typeof(XUiC_WorkstationWindowGroup), "Update")]
    public static class Patch_WorkstationWindow_Update
    {
        internal static XUiC_CraftingQueue OpenQueue;
        internal static TileEntityWorkstation OpenTe;

        public static void Postfix(XUiC_WorkstationWindowGroup __instance, XUiC_CraftingQueue ___craftingQueue)
        {
            XUiM_Workstation data = __instance.WorkstationData;
            TileEntityWorkstation te = data == null ? null : data.TileEntity;
            if (___craftingQueue == null || !PowerGate.IsGated(te)) return;
            OpenQueue = ___craftingQueue;
            OpenTe = te;
            bool powered = PowerGate.HasPower(te);
            bool crafting = ___craftingQueue.IsCrafting();
            if (!powered && crafting) ___craftingQueue.HaltCrafting();
            else if (powered && !crafting) ___craftingQueue.ResumeCrafting();
        }
    }

    // window open: XUiC_RecipeStack.Update(float _dt) counts the craft down by _dt (IL 3.4.0 b10)
    [HarmonyPatch(typeof(XUiC_RecipeStack), "Update")]
    public static class Patch_RecipeStack_Update_Speed
    {
        public static void Prefix(XUiC_RecipeStack __instance, ref float _dt, XUiC_CraftingQueue ___Owner)
        {
            TileEntityWorkstation te = Patch_WorkstationWindow_Update.OpenTe;
            if (te == null || ___Owner == null || ___Owner != Patch_WorkstationWindow_Update.OpenQueue) return;
            _dt *= PowerGate.Speed(te);
        }
    }
}
