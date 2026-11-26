// E01 Crank slots (user, 2026-11-22): the Crank is the starting generator. Its power-source window keeps only
//   slot 0 = Battery Bank Module (feBatteryModule)  -- like the forge's crucible / the campfire's grill
//   slot 1 = one car battery (carBattery)          -- locked (take-only) unless the module is in slot 0
// The other 4 slots of the vanilla grid (PowerSource always has 6 Stacks) are hidden. No Flywheels here: the
// crank's output is the fixed FeCrankBaseOutput (PowerPatches.cs).
// With module + battery: cranking past a full generator charges the battery; when the cranked fuel runs out, the
// battery feeds the generator, so the wire keeps its power after you stop turning.
//
// Vanilla (IL 3.4.0 b10):
//  - XUiC_PowerSourceSlots.SetRequirements: every XUiC_RequiredItemStack gets SetAllowedItemClassSingle(SlotItem).
//    XUiC_RequiredItemStack.CanSwap refuses items outside its allowed list and anything when TakeOnly is set
//    (except taking the stack out).
//  - XUiC_PowerSourceSlots.UpdateBackend writes the grid back into TileEntityPowerSource.ItemSlots (slot change).
//  - XUiC_PowerSourceSlots.TryAddItemToSlot (shift-click) only accepts SlotItem.
//  - Battery charge = ItemValue.MaxUseTimes - UseTimes (PowerBatteryBank lowers UseTimes to charge).
//  - PowerSource.HandleSendPower: IsOn -> TickPowerGeneration (generator: 1 fuel per power tick) -> auto-off at 0
//    fuel (PowerGenerator.ShouldAutoTurnOff).
//
// C# 5 only.

using HarmonyLib;
using UnityEngine;

namespace ForgedInAshes
{
    public static class CrankSlots
    {
        public const int ModuleSlot = 0;
        public const int BatterySlot = 1;
        public const string ModuleItem = "feBatteryModule";
        public const string BatteryItem = "carBattery";

        public static bool IsCrank(TileEntityPowerSource te)
        {
            return te != null && te.blockValue.Block is BlockFeCrank;
        }

        public static bool IsCrank(PowerItem item)
        {
            return item != null && item.BlockID < Block.list.Length && Block.list[item.BlockID] is BlockFeCrank;
        }

        static bool Is(ItemStack s, string itemName)
        {
            if (s == null || s.IsEmpty() || s.itemValue == null) return false;
            ItemClass ic = s.itemValue.ItemClass;
            return ic != null && ic.GetItemName() == itemName;
        }

        public static bool HasModule(ItemStack[] slots)
        {
            return slots != null && slots.Length > ModuleSlot && Is(slots[ModuleSlot], ModuleItem);
        }

        // The battery stack, only when the module is installed (a battery left without the module does nothing).
        public static ItemStack ActiveBattery(ItemStack[] slots)
        {
            if (!HasModule(slots) || slots.Length <= BatterySlot) return null;
            return Is(slots[BatterySlot], BatteryItem) ? slots[BatterySlot] : null;
        }

        public static bool HasBatteryItem(ItemStack[] slots)
        {
            return slots != null && slots.Length > BatterySlot && Is(slots[BatterySlot], BatteryItem);
        }

        // Charge units left in a battery stack (MaxUseTimes - UseTimes).
        public static int Charge(ItemStack battery)
        {
            if (battery == null) return 0;
            return Mathf.Max(0, battery.itemValue.MaxUseTimes - Mathf.CeilToInt(battery.itemValue.UseTimes));
        }

        public static int Room(ItemStack battery)
        {
            if (battery == null) return 0;
            return Mathf.Max(0, Mathf.FloorToInt(battery.itemValue.UseTimes));
        }

        // Applies the per-slot rules to an open crank window (called after vanilla SetRequirements and after every
        // slot change, so putting the module in unlocks the battery slot at once).
        public static void ApplyRules(XUiC_PowerSourceSlots grid)
        {
            if (grid == null || !IsCrank(grid.TileEntity) || grid.itemControllers == null) return;
            bool module = HasModule(grid.TileEntity.ItemSlots);
            for (int i = 0; i < grid.itemControllers.Length; i++)
            {
                XUiC_ItemStack slot = grid.itemControllers[i];
                if (slot == null) continue;
                XUiC_RequiredItemStack req = slot as XUiC_RequiredItemStack;
                if (i == ModuleSlot || i == BatterySlot)
                {
                    if (slot.ViewComponent != null) slot.ViewComponent.IsVisible = true;
                    if (req == null) continue;
                    req.SetAllowedItemClassSingle(ItemClass.GetItemClass(i == ModuleSlot ? ModuleItem : BatteryItem,
                                                                         false));
                    req.TakeOnly = i == BatterySlot && !module;
                }
                else
                {
                    if (slot.ViewComponent != null) slot.ViewComponent.IsVisible = false;
                    if (req != null) req.TakeOnly = true;
                }
            }
        }
    }

    [HarmonyPatch(typeof(XUiC_PowerSourceSlots), "SetRequirements")]
    public static class Patch_PowerSourceSlots_SetRequirements
    {
        public static void Postfix(XUiC_PowerSourceSlots __instance)
        {
            CrankSlots.ApplyRules(__instance);
        }
    }

    [HarmonyPatch(typeof(XUiC_PowerSourceSlots), "UpdateBackend")]
    public static class Patch_PowerSourceSlots_UpdateBackend
    {
        public static void Postfix(XUiC_PowerSourceSlots __instance)
        {
            CrankSlots.ApplyRules(__instance);
        }
    }

    // Shift-click from the inventory: the module goes to slot 0, a battery to slot 1 (only with the module).
    [HarmonyPatch(typeof(XUiC_PowerSourceSlots), "TryAddItemToSlot")]
    public static class Patch_PowerSourceSlots_TryAddItemToSlot
    {
        public static bool Prefix(XUiC_PowerSourceSlots __instance, ItemClass itemClass, ItemStack itemStack,
                                  ref bool __result)
        {
            TileEntityPowerSource te = __instance.TileEntity;
            if (!CrankSlots.IsCrank(te)) return true;
            __result = false;
            if (itemClass == null || itemStack == null || itemStack.IsEmpty()) return false;
            ItemStack[] slots = te.ItemSlots;
            string name = itemClass.GetItemName();
            int target = -1;
            if (name == CrankSlots.ModuleItem) target = CrankSlots.ModuleSlot;
            else if (name == CrankSlots.BatteryItem && CrankSlots.HasModule(slots)) target = CrankSlots.BatterySlot;
            if (target < 0 || slots == null || slots.Length <= target || !slots[target].IsEmpty()) return false;
            slots[target] = new ItemStack(itemStack.itemValue.Clone(), 1);
            te.ItemSlots = slots;
            te.SetSendSlots();
            __instance.SetSlots(te.ItemSlots);
            CrankSlots.ApplyRules(__instance);
            __result = true;
            return false;
        }
    }

    // With module + battery, the battery feeds the generator when the cranked fuel runs out (server side; runs
    // before vanilla burns fuel and auto-turns the generator off).
    [HarmonyPatch(typeof(PowerSource), "HandleSendPower")]
    public static class Patch_PowerSource_HandleSendPower_CrankBattery
    {
        const int RefillFuel = 10;   // fuel units moved from the battery per power tick when the generator is empty

        public static void Prefix(PowerSource __instance)
        {
            PowerGenerator gen = __instance as PowerGenerator;
            if (gen == null || !gen.IsOn || gen.CurrentFuel > 0 || !CrankSlots.IsCrank(gen)) return;
            ItemStack battery = CrankSlots.ActiveBattery(gen.Stacks);
            int take = Mathf.Min(CrankSlots.Charge(battery), Mathf.Min(RefillFuel, gen.MaxFuel));
            if (take <= 0) return;
            battery.itemValue.UseTimes += take;
            gen.CurrentFuel = (ushort)take;
            if (gen.TileEntity != null) gen.TileEntity.SetModified();
        }
    }
}
