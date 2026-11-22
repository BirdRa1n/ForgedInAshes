// D7: machines run on WATTS from the vanilla power network, through an "Electric Motor" block.
//
// A machine block opts in with <property name="FeMinPower" value="30"/> (watts). It crafts only while an
// Electric Motor (a block with <property name="FeMotor" value="true"/>, vanilla Class="Powered" consumer wired
// like a light) sits in the machine's MOTOR SOCKET and is powered. The motor draws the machine's FeMinPower
// from the network (its PowerItem.RequiredPower is set to it), so a 30 W crank cannot run a 60 W machine.
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

        /// <summary>The motor in this machine's socket is powered and draws the machine's FeMinPower.</summary>
        public static bool HasPower(TileEntityWorkstation te)
        {
            int need = te == null ? 0 : MinPower(te.blockValue.Block);
            if (need <= 0) return true;
            Vector3i pos = te.ToWorldPos();
            float now = Time.time;
            KeyValuePair<float, bool> cached;
            if (poweredCache.TryGetValue(pos, out cached) && now - cached.Key < CacheSeconds) return cached.Value;

            bool ok = false, motor = false;
            int watts = 0;
            Vector3i socket = Vector3i.zero;
            World world = GameManager.Instance == null ? null : GameManager.Instance.World;
            if (world != null)
            {
                socket = SocketPos(world.GetBlock(pos), pos);
                TileEntityPowered p = world.GetTileEntity(socket) as TileEntityPowered;
                if (p != null && IsMotor(p.blockValue.Block))
                {
                    motor = true;
                    // the motor draws what the machine needs (PowerItem exists only where the network runs:
                    // SP / host / server)
                    PowerItem item = p.GetPowerItem();
                    if (item != null && item.RequiredPower != need)
                    {
                        item.RequiredPower = (ushort)Mathf.Min(ushort.MaxValue, need);
                        p.RequiredPower = need;
                    }
                    if (p.IsPowered) watts = need;
                }
                ok = watts >= need;
            }
            // Diagnostic (D7 bring-up): one line whenever the result for this machine changes.
            KeyValuePair<float, bool> prev;
            bool hadPrev = poweredCache.TryGetValue(pos, out prev);
            if (!hadPrev || prev.Value != ok)
            {
                Log.Out(FerroEngrenagemMod.LogPrefix + "power " + te.blockValue.Block.GetBlockName() + " at " + pos +
                        " rot=" + te.blockValue.rotation + " socket=" + socket + ": motor=" + motor +
                        " watts=" + watts + "/" + need + " -> " + (ok ? "ON" : "OFF"));
            }
            poweredCache[pos] = new KeyValuePair<float, bool>(now, ok);
            return ok;
        }
    }

    // window closed: the tile entity does not advance its queue without power
    [HarmonyPatch(typeof(TileEntityWorkstation), "HandleRecipeQueue")]
    public static class Patch_TEW_HandleRecipeQueue
    {
        public static bool Prefix(TileEntityWorkstation __instance)
        {
            return !PowerGate.IsGated(__instance) || PowerGate.HasPower(__instance);
        }
    }

    // window open: halt / resume the UI queue like vanilla does for fuel
    [HarmonyPatch(typeof(XUiC_WorkstationWindowGroup), "Update")]
    public static class Patch_WorkstationWindow_Update
    {
        public static void Postfix(XUiC_WorkstationWindowGroup __instance, XUiC_CraftingQueue ___craftingQueue)
        {
            XUiM_Workstation data = __instance.WorkstationData;
            TileEntityWorkstation te = data == null ? null : data.TileEntity;
            if (___craftingQueue == null || !PowerGate.IsGated(te)) return;
            bool powered = PowerGate.HasPower(te);
            bool crafting = ___craftingQueue.IsCrafting();
            if (!powered && crafting) ___craftingQueue.HaltCrafting();
            else if (powered && !crafting) ___craftingQueue.ResumeCrafting();
        }
    }
}
