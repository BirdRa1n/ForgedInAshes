// Industrial versions (user, 2026-11-24): electric machines built on the F8 code, for full automation.
//   Induction Furnace (FeFluid smelter, Class Powered): melts like the Foundry but with electricity instead of fuel
//     (heat builds up only while powered, FeMeltSpeed seconds of melting per second).
//   Industrial Casting Table (FeFluid caster, Class Powered): an electric fan cools FeCoolFactor times faster.
//   Retort Kiln / Biodigester and other electric process machines (FeFluid processor, Class Powered): run only while
//     powered (ProcessMachine.Speed).
// BlockPowered has its own radial and readout: these patches add the mod's commands (put / take / mold / melt) and
// the models' visuals. Single player / host, like the rest.
//
// Also: alternative fuel for the engines (FeAltFuel item, FeAltFuelPer items = 1 fuel unit): the Biofuel in the Gas
// Engine burns three cans for what one gas can gives.
//
// C# 5 only.

using System.Collections.Generic;
using HarmonyLib;
using UnityEngine;

namespace FerroEngrenagem
{
    public static class Industrial
    {
        public static bool IsPowered(World world, Vector3i p)
        {
            TileEntityPowered te = world.GetTileEntity(p) as TileEntityPowered;
            return te != null && te.IsPowered;
        }

        public static bool IsElectric(Block b)
        {
            return b is BlockPowered;
        }

        // ------------------------------------------------------------ alternative engine fuel
        static readonly Dictionary<Vector3i, int> altLeft = new Dictionary<Vector3i, int>();

        public static string AltFuel(Block b)
        {
            return b != null && b.Properties != null && b.Properties.Contains("FeAltFuel") ? b.Properties.GetString("FeAltFuel") : null;
        }

        /// <summary>Feed alt-fuel items (st) to an engine: every FeAltFuelPer items add 1 fuel unit. Returns how many
        /// items it took (0 when full).</summary>
        public static int FeedAlt(Vector3i p, Block b, PowerGenerator gen, ItemStack st)
        {
            int per = Mathf.Max(1, (int)Fluids.Prop(b, "FeAltFuelPer", 3f));
            int left;
            altLeft.TryGetValue(p, out left);
            int took = 0;
            while (took < st.count && gen.CurrentFuel < gen.MaxFuel)
            {
                took++;
                left++;
                if (left >= per) { left = 0; gen.CurrentFuel = (ushort)(gen.CurrentFuel + 1); }
            }
            altLeft[p] = left;
            return took;
        }
    }

    // ------------------------------------------------------------ radial commands of the electric F8 machines
    [HarmonyPatch(typeof(BlockPowered), "GetBlockActivationCommands")]
    public static class Patch_BlockPowered_Commands_Industrial
    {
        public static void Postfix(BlockPowered __instance, EntityAlive _entityFocusing, ref BlockActivationCommand[] __result)
        {
            FluidKind k = Fluids.Kind(__instance);
            List<BlockActivationCommand> add = new List<BlockActivationCommand>();
            if (k == FluidKind.Processor) add.AddRange(ProcessMachine.Commands(null));
            else if (k == FluidKind.Valve) add.Add(new BlockActivationCommand(FeUi.ConfigCommand, "tool", true, false, null));
            else if (FeUi.HasConfig(__instance)) add.Add(new BlockActivationCommand(FeUi.ConfigCommand, "tool", true, false, null));
            else if (k == FluidKind.Caster)
            {
                add.Add(new BlockActivationCommand("fe_cast_take", "loot_sort", true, false, null));
                add.Add(new BlockActivationCommand("fe_mold", "tool", true, false, null));
            }
            else if (k == FluidKind.Smelter)
                add.Add(new BlockActivationCommand("fe_melt", "loot_sort", true, false, null));
            if (add.Count > 0)
            {
                if (__result != null) add.AddRange(__result);
                __result = add.ToArray();
            }
            RecipeBook.AddCommand(__instance, ref __result);
            if (k != FluidKind.None) FeUi.AddNetCommand(_entityFocusing, ref __result);
        }
    }

    [HarmonyPatch(typeof(BlockPowered), "OnBlockActivated", new System.Type[] { typeof(string), typeof(WorldBase), typeof(Vector3i), typeof(BlockValue), typeof(EntityPlayerLocal) })]
    public static class Patch_BlockPowered_Activated_Industrial
    {
        public static bool Prefix(BlockPowered __instance, string _commandName, WorldBase _world, Vector3i _blockPos,
                                  BlockValue _blockValue, EntityPlayerLocal _player, ref bool __result)
        {
            if (_commandName == RecipeBook.Command)
            {
                RecipeBook.Open(__instance, _player);
                __result = true;
                return false;
            }
            World w = _world as World;
            if (w != null && FeUi.HandleCommand(_commandName, w, _blockPos, _blockValue, _player)) { __result = true; return false; }
            if (_commandName != "fe_put" && _commandName != "fe_cast_take" && _commandName != "fe_mold" && _commandName != "fe_melt"
                && !ProcessMachine.IsCommand(_commandName))
                return true;
            __result = true;
            if (w == null) return false;
            Vector3i p = Fluids.ParentOf(w, _blockPos, _blockValue);
            FluidKind k = Fluids.Kind(__instance);
            string msg = null;
            if (k == FluidKind.Processor) msg = ProcessMachine.Activate(w, p, _commandName, _player);
            else if (k == FluidKind.Caster) msg = MetalWorks.Activate(w, p, _commandName, _player);
            else if (k == FluidKind.Smelter && _commandName == "fe_melt")
            {
                ItemStack held = _player.inventory.holdingItemStack;
                if (held == null || held.IsEmpty()) msg = Kinetic.Text("feMeltHold", "Hold the scrap or ingots to melt");
                else
                {
                    int n = MetalWorks.Melt(w, p, null, held, out msg);
                    if (n > 0)
                    {
                        ItemStack left = held.Clone();
                        left.count -= n;
                        _player.inventory.SetItem(_player.inventory.holdingItemIdx, left.count > 0 ? left : ItemStack.Empty.Clone());
                        msg = string.Format(Kinetic.Text("feMelted", "Melted {0}"), n);
                    }
                }
            }
            if (msg != null) GameManager.ShowTooltip(_player, msg, false, false, 0f);
            return false;
        }
    }

    [HarmonyPatch(typeof(BlockPowered), "OnBlockEntityTransformAfterActivated")]
    public static class Patch_BlockPowered_Visual_Industrial
    {
        public static void Postfix(BlockPowered __instance, Vector3i _blockPos, BlockEntityData _ebcd)
        {
            if (Fluids.Kind(__instance) == FluidKind.Caster) CasterVisual.Attach(_ebcd, _blockPos);
            MachineItems.Attach(_ebcd, _blockPos, __instance);
        }
    }
}
