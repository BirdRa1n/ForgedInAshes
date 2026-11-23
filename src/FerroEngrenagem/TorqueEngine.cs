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

        // E08 Steam Engine (D8): optional needs on top of fuel.
        //   <property name="FeNeedsWater" value="true"/>                 water next to it or below (the boiler)
        //   <property name="FeLubeItem" value="feResourceLubricant"/>    this item in its slots (SlotItem = the same)
        //   <property name="FeLubeSecondsPerUnit" value="300"/>          one unit used up per this many seconds running
        public static bool NeedsWater(Block b)
        {
            return b.Properties != null && b.Properties.Contains("FeNeedsWater") && b.Properties.GetBool("FeNeedsWater");
        }

        public static string LubeItem(Block b)
        {
            if (b.Properties == null || !b.Properties.Contains("FeLubeItem")) return null;
            string n = b.Properties.GetString("FeLubeItem").Trim();
            return n.Length == 0 ? null : n;
        }

        public static float LubeSeconds(Block b)
        {
            float v = b.Properties != null && b.Properties.Contains("FeLubeSecondsPerUnit")
                ? b.Properties.GetFloat("FeLubeSecondsPerUnit") : 300f;
            return v < 1f ? 1f : v;
        }

        /// <summary>Water in the engine's cell, below it, or in one of its four side cells (or below those).</summary>
        public static bool HasWater(World world, Vector3i pos)
        {
            for (int dx = -1; dx <= 1; dx++)
                for (int dz = -1; dz <= 1; dz++)
                {
                    if (dx != 0 && dz != 0) continue;
                    for (int dy = -1; dy <= 0; dy++)
                        if (world.IsWater(pos.x + dx, pos.y + dy, pos.z + dz)) return true;
                }
            return false;
        }

        /// <summary>Index of a slot holding the lubricant, or -1.</summary>
        public static int LubeSlot(ItemStack[] slots, string item)
        {
            if (slots == null || item == null) return -1;
            for (int i = 0; i < slots.Length; i++)
            {
                ItemStack st = slots[i];
                if (st == null || st.IsEmpty() || st.itemValue == null || st.itemValue.ItemClass == null) continue;
                if (st.itemValue.ItemClass.GetItemName() == item) return i;
            }
            return -1;
        }

        /// <summary>What stops the engine, or null when it can run (fuel and on/off are checked by IsRunning).
        /// "water" or "lube".</summary>
        public static string Missing(World world, Vector3i pos, TileEntityPowerSource te)
        {
            Block b = te.blockValue.Block;
            if (NeedsWater(b) && !HasWater(world, pos)) return "water";
            if (SteamEngine.Is(b))
            {
                FluidStore.EnsureLoaded();
                if (FluidStore.Get(pos).Amount <= 0.01f) return "water";
            }
            string lube = LubeItem(b);
            if (lube != null && LubeSlot(te.ItemSlots, lube) < 0) return "lube";
            return null;
        }

        /// <summary>On, fuelled and with what it needs (works on the server and, through the synced client data,
        /// on clients).</summary>
        public static bool IsRunning(World world, Vector3i pos)
        {
            TileEntityPowerSource te = world.GetTileEntity(pos) as TileEntityPowerSource;
            return te != null && te.IsOn && te.CurrentFuel > 0 && Missing(world, pos, te) == null;
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
            // a steam engine without water or lubricant stands still and burns nothing
            World world = GameManager.Instance == null ? null : GameManager.Instance.World;
            TileEntityPowerSource te = gen.TileEntity as TileEntityPowerSource;
            if (world != null && te != null && TorqueEngine.Missing(world, pos, te) != null) return;
            UseLube(gen, b, pos, dt);
            float acc;
            burnt.TryGetValue(pos, out acc);
            acc += dt;
            float per = TorqueEngine.SecondsPerUnit(b);
            // the big Steam Engine burns in proportion to its load
            if (SteamEngine.Is(b) && world != null) per /= SteamEngine.Factor(world, pos, b);
            if (acc >= per)
            {
                acc -= per;
                gen.CurrentFuel = (ushort)(gen.CurrentFuel - 1);
                if (gen.TileEntity != null) gen.TileEntity.SetModified();
            }
            burnt[pos] = acc;
        }

        static readonly Dictionary<Vector3i, float> lubed = new Dictionary<Vector3i, float>();

        static void UseLube(PowerGenerator gen, Block b, Vector3i pos, float dt)
        {
            string lube = TorqueEngine.LubeItem(b);
            if (lube == null) return;
            float acc;
            lubed.TryGetValue(pos, out acc);
            acc += dt;
            float per = TorqueEngine.LubeSeconds(b);
            if (acc >= per)
            {
                acc -= per;
                int i = TorqueEngine.LubeSlot(gen.Stacks, lube);
                if (i >= 0)
                {
                    ItemStack st = gen.Stacks[i];
                    st.count--;
                    if (st.count <= 0) gen.Stacks[i] = ItemStack.Empty.Clone();
                    if (gen.TileEntity != null)
                    {
                        TileEntityPowerSource te = gen.TileEntity as TileEntityPowerSource;
                        if (te != null) te.SetSendSlots();
                        gen.TileEntity.SetModified();
                    }
                }
            }
            lubed[pos] = acc;
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
            return te != null && (TorqueEngine.IsEngine(te.blockValue.Block) || Dynamo.IsInternal(te));
        }

        public static void Hide(XUiC_PowerSourceSlots grid)
        {
            if (grid == null || !IsEngine(grid.TileEntity) || grid.itemControllers == null) return;
            if (TorqueEngine.LubeItem(grid.TileEntity.blockValue.Block) != null) return;   // Steam Engine: lubricant slots
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
            if (TorqueEngine.LubeItem(__instance.TileEntity.blockValue.Block) != null) return true;
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
            if (TorqueEngine.IsEngine(__instance) || Dynamo.Is(__instance)) KineticSpinner.Attach(_ebcd, _blockPos, __instance);
            if (SteamEngine.Is(__instance)) SteamVent.Attach(_ebcd, _blockPos);
        }
    }
}

namespace FerroEngrenagem
{
    // Torque engines (coal and steam) are vanilla Generators under the hood (fuel UI), so the wire tool showed the
    // "power source" crosshair over them although they give no electricity. Show the plain crosshair instead.
    [HarmonyLib.HarmonyPatch(typeof(ItemActionConnectPower), "GetCrosshairType")]
    public static class Patch_ConnectPower_Crosshair_Engine
    {
        public static void Postfix(ItemActionData _actionData, ref ItemClass.EnumCrosshairType __result)
        {
            if (__result != ItemClass.EnumCrosshairType.PowerSource) return;
            EntityPlayerLocal pl = _actionData.invData.holdingEntity as EntityPlayerLocal;
            if (pl == null || pl.HitInfo == null || !pl.HitInfo.bHitValid) return;
            Block b = _actionData.invData.world.GetBlock(pl.HitInfo.hit.blockPos).Block;
            if (TorqueEngine.IsEngine(b)) __result = ItemClass.EnumCrosshairType.Plus;
        }
    }
}
