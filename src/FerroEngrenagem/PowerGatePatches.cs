// D7 step 1: machines run on WATTS from the vanilla power network, through an "Electric Motor" block.
//
// A machine block opts in with <property name="FeMinPower" value="30"/> (watts). It crafts only while the
// Electric Motors (blocks with <property name="FeMotor" value="true"/>, vanilla Class="Powered" consumers wired
// like a light) found near it are powered and their RequiredPower adds up to at least FeMinPower.
//
// Vanilla crafting runs in two places (IL of 3.4.0 b10):
//  - window closed: TileEntityWorkstation.HandleRecipeQueue(float) (from UpdateTick) -> Prefix skips it.
//  - window open:   XUiC_RecipeStack.Update counts down while the queue "IsCrafting"; vanilla halts/resumes the
//                   queue in XUiC_WorkstationWindowGroup.Update from the fuel state -> Postfix halts/resumes
//                   it from our power state instead.
// "Near" = a box around the machine's tile entity position (multiblock machines are up to 3 wide and may be
// rotated): dx/dz -SEARCH..+SEARCH, dy -1..+2.
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
        const int SEARCH = 3;
        const float CacheSeconds = 0.5f;

        static readonly Dictionary<int, int> minPowerByBlock = new Dictionary<int, int>();
        static readonly Dictionary<int, bool> motorByBlock = new Dictionary<int, bool>();
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

        /// <summary>Sum of RequiredPower of powered motors near the machine &gt;= its FeMinPower.</summary>
        public static bool HasPower(TileEntityWorkstation te)
        {
            int need = te == null ? 0 : MinPower(te.blockValue.Block);
            if (need <= 0) return true;
            Vector3i pos = te.ToWorldPos();
            float now = Time.time;
            KeyValuePair<float, bool> cached;
            if (poweredCache.TryGetValue(pos, out cached) && now - cached.Key < CacheSeconds) return cached.Value;

            bool ok = false;
            World world = GameManager.Instance == null ? null : GameManager.Instance.World;
            if (world != null)
            {
                int watts = 0;
                for (int dx = -SEARCH; dx <= SEARCH && !ok; dx++)
                    for (int dy = -1; dy <= 2 && !ok; dy++)
                        for (int dz = -SEARCH; dz <= SEARCH && !ok; dz++)
                        {
                            TileEntityPowered p = world.GetTileEntity(new Vector3i(pos.x + dx, pos.y + dy, pos.z + dz))
                                as TileEntityPowered;
                            if (p == null || !IsMotor(p.blockValue.Block) || !p.IsPowered) continue;
                            watts += p.RequiredPower;
                            ok = watts >= need;
                        }
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
