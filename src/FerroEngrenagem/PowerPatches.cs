// D7: small patches on the vanilla power UI for the mod's power sources.
//
// XUiC_PowerSourceStats.BtnRefuel_OnPress refuels any generator with the first item tagged "gasoline" (IL,
// 3.4.0 b10). The Crank is a generator fed only by cranking, so its Refuel button does nothing.
//
// C# 5 only.

using HarmonyLib;

namespace FerroEngrenagem
{
    // The crank has a base output without any Flywheel (FeCrankBaseOutput, watts): otherwise the first power of a
    // game would need a Flywheel, which is made in the Lathe, which needs power (bootstrap loop). Each Flywheel
    // in its slots adds OutputPerStack on top (vanilla RefreshPowerStats sums the slots).
    [HarmonyPatch(typeof(PowerSource), "RefreshPowerStats")]
    public static class Patch_PowerSource_RefreshPowerStats
    {
        public static void Postfix(PowerSource __instance)
        {
            ApplyCrankOutput(__instance);
        }

        internal static void ApplyCrankOutput(PowerSource __instance)
        {
            if (__instance.BlockID >= Block.list.Length) return;
            BlockFeCrank crank = Block.list[__instance.BlockID] as BlockFeCrank;
            if (crank == null || crank.BaseOutput <= 0) return;
            // User (2026-11-22): no Flywheels in the crank any more; its slots hold the Battery Bank Module and one
            // battery (CrankSlots.cs), which must not add watts. Output = the fixed base only.
            __instance.MaxOutput = (ushort)System.Math.Min(ushort.MaxValue, crank.BaseOutput);
        }
    }

    // A freshly placed power source gets MaxOutput = OutputPerStack * SlotCount in SetValuesFromBlock (IL 3.4.0
    // b10); RefreshPowerStats only runs from SetSlots / TryAddItemToSlot (world load, slot change). The crank has
    // OutputPerStack 0, so a NEW crank sent 0 W until the world was reloaded (D7 test 2026-11-22: motor never
    // powered). Apply the base output here too.
    [HarmonyPatch(typeof(PowerSource), "SetValuesFromBlock")]
    public static class Patch_PowerSource_SetValuesFromBlock
    {
        public static void Postfix(PowerSource __instance)
        {
            Patch_PowerSource_RefreshPowerStats.ApplyCrankOutput(__instance);
        }
    }

    // The crank's "fuel" is cranked energy, not gasoline: hide the stats row that shows it with the gas-can icon
    // ("{fueltitle}: {fuel}/{maxfuel}") and the Refuel button; both are visible="{showfuel}" in windows.xml
    // (windowPowerSourceStats). The stored energy is shown in the crank's own prompt (Crank.cs).
    [HarmonyPatch(typeof(XUiC_PowerSourceStats), "GetBindingValueInternal")]
    public static class Patch_PowerSourceStats_HideCrankFuel
    {
        public static void Postfix(XUiC_PowerSourceStats __instance, ref string value, string bindingName,
                                   ref bool __result)
        {
            if (bindingName != "showfuel") return;
            TileEntityPowerSource te = __instance.TileEntity;
            if (te != null && (te.blockValue.Block is BlockFeCrank || Dynamo.IsInternal(te)))
            {
                value = "false";
                __result = true;
            }
        }
    }

    [HarmonyPatch(typeof(XUiC_PowerSourceStats), "BtnRefuel_OnPress")]
    public static class Patch_PowerSourceStats_Refuel
    {
        public static bool Prefix(XUiC_PowerSourceStats __instance)
        {
            TileEntityPowerSource te = __instance.TileEntity;
            if (te != null && (te.blockValue.Block is BlockFeCrank || Dynamo.IsInternal(te))) return false;
            return true;
        }
    }

    // Picking up / replacing a power source: vanilla TileEntityPowerSource.ReplacedBy (IL 3.4.0 b10) drops its
    // slot items PLUS CurrentFuel turned into the first item tagged "gasoline" in a DroppedLootContainer. The
    // crank's fuel is cranked spin, not gasoline (user, 2026-11-22: a bag of gas cans fell out when taking a
    // charged crank): zero it first, so only the slot items (module, battery) drop.
    [HarmonyPatch(typeof(TileEntityPowerSource), "ReplacedBy")]
    public static class Patch_PowerSource_ReplacedBy_NoCrankGas
    {
        public static void Prefix(TileEntityPowerSource __instance, BlockValue _bvOld)
        {
            if (!(_bvOld.Block is BlockFeCrank)) return;
            if (__instance.CurrentFuel > 0) __instance.CurrentFuel = 0;
        }
    }
}
