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
            if (__instance.BlockID >= Block.list.Length) return;
            BlockFeCrank crank = Block.list[__instance.BlockID] as BlockFeCrank;
            if (crank == null || crank.BaseOutput <= 0) return;
            __instance.MaxOutput = (ushort)System.Math.Min(ushort.MaxValue, __instance.MaxOutput + crank.BaseOutput);
        }
    }

    [HarmonyPatch(typeof(XUiC_PowerSourceStats), "BtnRefuel_OnPress")]
    public static class Patch_PowerSourceStats_Refuel
    {
        public static bool Prefix(XUiC_PowerSourceStats __instance)
        {
            TileEntityPowerSource te = __instance.TileEntity;
            if (te != null && te.blockValue.Block is BlockFeCrank) return false;
            return true;
        }
    }
}
