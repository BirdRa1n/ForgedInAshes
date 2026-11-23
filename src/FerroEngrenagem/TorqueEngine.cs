// D8 T4: fuel ENGINES as torque sources (Coal Engine, Gas Engine).
//
// An engine is a vanilla Class="Generator" block (fuel window, Refuel, on/off) with
//   <property name="FeTorqueEngine" value="true"/>
//   <property name="FeTorqueOutput" value="256"/>        UT while running
//   <property name="FeFuelSecondsPerUnit" value="60"/>   seconds one fuel unit lasts
// and FeFuelItem (FuelGenerator.cs) when it burns something other than gasoline. It does not power wires: its
// MaxOutput is 0 (OutputPerStack 0) and MaxPower/OutputPerFuel are 1, so vanilla TickPowerGeneration burns at
// most one unit once. It RUNS while it is on and has fuel; it then gives FeTorqueOutput UT to the torque network
// through its drive shaft (model local +Z, both ends, turning +Z like the other sources).
// Fuel burn: a postfix on PowerSource.HandleSendPower (PowerManager tick, server) takes one unit every
// FeFuelSecondsPerUnit seconds while on; vanilla ShouldAutoTurnOff turns it off at 0 fuel. It burns while on,
// loaded or not (turn it off to save fuel), like Create's engines.
//
// C# 5 only.

using System.Collections.Generic;
using HarmonyLib;
using UnityEngine;

namespace FerroEngrenagem
{
    public static class TorqueEngine
    {
        static readonly Dictionary<int, bool> engineByBlock = new Dictionary<int, bool>();
        static readonly Dictionary<int, float> secondsByBlock = new Dictionary<int, float>();

        public static bool IsEngine(Block b)
        {
            if (b == null) return false;
            bool v;
            if (engineByBlock.TryGetValue(b.blockID, out v)) return v;
            v = b.Properties != null && b.Properties.Contains("FeTorqueEngine") && b.Properties.GetBool("FeTorqueEngine");
            engineByBlock[b.blockID] = v;
            return v;
        }

        public static float SecondsPerUnit(Block b)
        {
            float v;
            if (secondsByBlock.TryGetValue(b.blockID, out v)) return v;
            v = b.Properties != null && b.Properties.Contains("FeFuelSecondsPerUnit")
                ? b.Properties.GetFloat("FeFuelSecondsPerUnit") : 30f;
            if (v < 0.5f) v = 0.5f;
            secondsByBlock[b.blockID] = v;
            return v;
        }

        /// <summary>On and fuelled (works on the server and, through the synced client data, on clients).</summary>
        public static bool IsRunning(World world, Vector3i pos)
        {
            TileEntityPowerSource te = world.GetTileEntity(pos) as TileEntityPowerSource;
            return te != null && te.IsOn && te.CurrentFuel > 0;
        }
    }

    [HarmonyPatch(typeof(PowerSource), "HandleSendPower")]
    public static class Patch_PowerSource_HandleSendPower_EngineBurn
    {
        static readonly Dictionary<Vector3i, float> burnt = new Dictionary<Vector3i, float>();
        static readonly Dictionary<Vector3i, float> lastTime = new Dictionary<Vector3i, float>();

        public static void Postfix(PowerSource __instance)
        {
            PowerGenerator gen = __instance as PowerGenerator;
            if (gen == null || gen.BlockID >= Block.list.Length) return;
            Block b = Block.list[gen.BlockID];
            if (!TorqueEngine.IsEngine(b)) return;
            Vector3i pos = gen.Position;
            float now = Time.time;
            float last;
            float dt = lastTime.TryGetValue(pos, out last) ? Mathf.Clamp(now - last, 0f, 1f) : 0f;
            lastTime[pos] = now;
            if (!gen.IsOn || gen.CurrentFuel == 0) { burnt[pos] = 0f; return; }
            float acc;
            burnt.TryGetValue(pos, out acc);
            acc += dt;
            float per = TorqueEngine.SecondsPerUnit(b);
            if (acc >= per)
            {
                acc -= per;
                gen.CurrentFuel = (ushort)(gen.CurrentFuel - 1);
                if (gen.TileEntity != null) gen.TileEntity.SetModified();
            }
            burnt[pos] = acc;
        }
    }

    // The radial "turn on" (BlockPowerSource.OnBlockActivated) and the window's On button (XUiC_PowerSourceStats.
    // btnOn_OnPress) refuse a power source whose TileEntityPowerSource.MaxOutput is 0 ("ttRequiresOneComponent",
    // IL 3.4.0 b10). Engines have no electric output on purpose (PowerSource.MaxOutput stays 0, so wires get
    // nothing): report 1 to those checks only, through the tile entity getter.
    [HarmonyPatch(typeof(TileEntityPowerSource), "MaxOutput", MethodType.Getter)]
    public static class Patch_TEPowerSource_MaxOutput_Engine
    {
        public static void Postfix(TileEntityPowerSource __instance, ref ushort __result)
        {
            if (__result == 0 && TorqueEngine.IsEngine(__instance.blockValue.Block)) __result = 1;
        }
    }

    // Engines: the vanilla generator window always has 6 slots (PowerSource.Stacks), useless here. Hide them and
    // refuse shift-click into them (same mechanism as the Crank's hidden slots, CrankSlots.cs).
    public static class EngineSlots
    {
        public static bool IsEngine(TileEntityPowerSource te)
        {
            return te != null && TorqueEngine.IsEngine(te.blockValue.Block);
        }

        public static void Hide(XUiC_PowerSourceSlots grid)
        {
            if (grid == null || !IsEngine(grid.TileEntity) || grid.itemControllers == null) return;
            foreach (XUiC_ItemStack slot in grid.itemControllers)
            {
                if (slot == null) continue;
                if (slot.ViewComponent != null) slot.ViewComponent.IsVisible = false;
                XUiC_RequiredItemStack req = slot as XUiC_RequiredItemStack;
                if (req != null) req.TakeOnly = true;
            }
        }
    }

    [HarmonyPatch(typeof(XUiC_PowerSourceSlots), "SetRequirements")]
    public static class Patch_PowerSourceSlots_SetRequirements_Engine
    {
        public static void Postfix(XUiC_PowerSourceSlots __instance)
        {
            EngineSlots.Hide(__instance);
        }
    }

    [HarmonyPatch(typeof(XUiC_PowerSourceSlots), "UpdateBackend")]
    public static class Patch_PowerSourceSlots_UpdateBackend_Engine
    {
        public static void Postfix(XUiC_PowerSourceSlots __instance)
        {
            EngineSlots.Hide(__instance);
        }
    }

    [HarmonyPatch(typeof(XUiC_PowerSourceSlots), "TryAddItemToSlot")]
    public static class Patch_PowerSourceSlots_TryAddItemToSlot_Engine
    {
        public static bool Prefix(XUiC_PowerSourceSlots __instance, ref bool __result)
        {
            if (!EngineSlots.IsEngine(__instance.TileEntity)) return true;
            __result = false;
            return false;
        }
    }

    // Engines get the spin animator on their model too (KineticSpinner.cs).
    [HarmonyPatch(typeof(BlockPowerSource), "OnBlockEntityTransformAfterActivated")]
    public static class Patch_BlockPowerSource_KineticSpinner
    {
        public static void Postfix(BlockPowerSource __instance, Vector3i _blockPos, BlockEntityData _ebcd)
        {
            if (TorqueEngine.IsEngine(__instance)) KineticSpinner.Attach(_ebcd, _blockPos, __instance);
        }
    }
}
