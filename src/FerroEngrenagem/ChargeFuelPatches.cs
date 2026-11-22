// F2-T03 (D6): the Parts Press (fePress) and the Lathe (feLathe) burn ONLY Charge (feCharge).
//
// Vanilla behaviour (IL of 3.4.0 b10):
//  - Fuel slots accept any item (XUiC_ItemStack.CanSwap returns true); "is fuel" = ItemClass.GetFuelValue > 0.
//  - TileEntityWorkstation.HandleFuel: when the current burn runs out and getTotalFuelSeconds() > 0, it removes
//    ONE item from fuel[0] and adds GetFuelTime(fuel[0]) seconds.
//  - XUiC_WorkstationFuelGrid.hasAnyFuel / hasFuelStack / HasRequirement decide the on/off button and whether
//    recipes can run, also by FuelValue.
// So for our stations we (1) count only Charge in every fuel query and (2) move Charge stacks to the front of
// the fuel array before HandleFuel runs, so no other item is ever consumed. Other items may sit in the slots
// but never burn. Every other workstation keeps vanilla behaviour.
//
// C# 5 only (built with the .NET Framework 4 csc.exe).

using System.Reflection;
using HarmonyLib;

namespace FerroEngrenagem
{
    public static class ChargeFuel
    {
        public const string ChargeItemName = "feCharge";
        // Block property that opts a workstation into "Charge only" fuel (blocks.xml):
        //   <property name="FeChargeOnly" value="true"/>
        public const string ChargeOnlyProperty = "FeChargeOnly";

        // Cache per block id: this runs every tick for every workstation.
        static readonly System.Collections.Generic.Dictionary<int, bool> cache =
            new System.Collections.Generic.Dictionary<int, bool>();

        public static bool IsChargeStation(Block block)
        {
            if (block == null) return false;
            bool result;
            if (cache.TryGetValue(block.blockID, out result)) return result;
            DynamicProperties p = block.Properties;
            bool has = p != null && p.Contains(ChargeOnlyProperty);
            result = has && p.GetBool(ChargeOnlyProperty);
            cache[block.blockID] = result;
            // Diagnostic (F3-T02 bug hunt): one line per block id, only for our blocks or when the flag is set.
            string name = block.GetBlockName();
            if (result || (name != null && name.StartsWith("fe")))
            {
                Log.Out(FerroEngrenagemMod.LogPrefix + "station '" + name + "' id=" + block.blockID +
                        " hasProp=" + has + " raw='" + (has ? p.GetString(ChargeOnlyProperty) : "") +
                        "' chargeOnly=" + result);
            }
            return result;
        }

        public static bool IsChargeStation(TileEntityWorkstation te)
        {
            if (te == null) return false;
            return IsChargeStation(te.blockValue.Block);
        }

        public static bool IsCharge(ItemStack stack)
        {
            if (stack == null || stack.IsEmpty()) return false;
            ItemValue iv = stack.itemValue;
            if (iv == null) return false;
            ItemClass ic = iv.ItemClass;
            return ic != null && ic.GetItemName() == ChargeItemName;
        }

        public static float ChargeSeconds(ItemStack[] stacks)
        {
            if (stacks == null) return 0f;
            float total = 0f;
            for (int i = 0; i < stacks.Length; i++)
            {
                if (IsCharge(stacks[i]))
                {
                    total += (float)ItemClass.GetFuelValue(stacks[i].itemValue) * stacks[i].count;
                }
            }
            return total;
        }

        // Stable partition: Charge stacks first, everything else after, in the same array.
        public static void MoveChargeToFront(ItemStack[] stacks)
        {
            if (stacks == null || stacks.Length < 2 || IsCharge(stacks[0])) return;
            bool anyCharge = false;
            for (int i = 1; i < stacks.Length; i++) { if (IsCharge(stacks[i])) { anyCharge = true; break; } }
            if (!anyCharge) return;
            ItemStack[] copy = (ItemStack[])stacks.Clone();
            int w = 0;
            for (int i = 0; i < copy.Length; i++) { if (IsCharge(copy[i])) stacks[w++] = copy[i]; }
            for (int i = 0; i < copy.Length; i++) { if (!IsCharge(copy[i])) stacks[w++] = copy[i]; }
        }
    }

    // ---------- tile entity (server/authoritative side) ----------

    [HarmonyPatch(typeof(TileEntityWorkstation), "GetFuelTime")]
    public static class Patch_TEW_GetFuelTime
    {
        public static void Postfix(TileEntityWorkstation __instance, ItemStack _fuel, ref float __result)
        {
            if (ChargeFuel.IsChargeStation(__instance) && !ChargeFuel.IsCharge(_fuel)) __result = 0f;
        }
    }

    [HarmonyPatch(typeof(TileEntityWorkstation), "getFuelTime")]
    public static class Patch_TEW_getFuelTime
    {
        public static void Postfix(TileEntityWorkstation __instance, ItemStack _itemStack, ref float __result)
        {
            if (ChargeFuel.IsChargeStation(__instance) && !ChargeFuel.IsCharge(_itemStack)) __result = 0f;
        }
    }

    [HarmonyPatch(typeof(TileEntityWorkstation), "getTotalFuelSeconds")]
    public static class Patch_TEW_getTotalFuelSeconds
    {
        public static void Postfix(TileEntityWorkstation __instance, ItemStack[] ___fuel, ref float __result)
        {
            if (ChargeFuel.IsChargeStation(__instance)) __result = ChargeFuel.ChargeSeconds(___fuel);
        }
    }

    [HarmonyPatch(typeof(TileEntityWorkstation), "HandleFuel")]
    public static class Patch_TEW_HandleFuel
    {
        static bool warned;

        public static void Prefix(TileEntityWorkstation __instance, ItemStack[] ___fuel)
        {
            if (ChargeFuel.IsChargeStation(__instance))
            {
                ChargeFuel.MoveChargeToFront(___fuel);
                return;
            }
            // Diagnostic: a block named fe* that is NOT charge-only while burning something.
            Block b = __instance.blockValue.Block;
            string n = b == null ? null : b.GetBlockName();
            if (!warned && n != null && n.StartsWith("fe") && n != "feFoundry" && __instance.IsBurning)
            {
                warned = true;
                Log.Warning(FerroEngrenagemMod.LogPrefix + "HandleFuel on '" + n + "' (id " + b.blockID +
                            ") is NOT treated as charge-only");
            }
        }
    }

    // ---------- UI (on/off button, "needs fuel" for recipes) ----------

    public static class FuelGridHelper
    {
        static readonly FieldInfo fWorkstationData = AccessTools.Field(typeof(XUiC_WorkstationGrid), "workstationData");
        static readonly FieldInfo fItemControllers = AccessTools.Field(typeof(XUiC_ItemStackGrid), "itemControllers");

        public static XUiM_Workstation Data(XUiC_WorkstationFuelGrid grid)
        {
            return fWorkstationData == null ? null : fWorkstationData.GetValue(grid) as XUiM_Workstation;
        }

        public static bool IsChargeGrid(XUiC_WorkstationFuelGrid grid)
        {
            XUiM_Workstation data = Data(grid);
            return data != null && ChargeFuel.IsChargeStation(data.TileEntity);
        }

        public static bool AnyChargeInGrid(XUiC_WorkstationFuelGrid grid)
        {
            XUiC_ItemStack[] slots = fItemControllers == null ? null : fItemControllers.GetValue(grid) as XUiC_ItemStack[];
            if (slots == null) return false;
            for (int i = 0; i < slots.Length; i++)
            {
                if (slots[i] != null && ChargeFuel.IsCharge(slots[i].ItemStack)) return true;
            }
            return false;
        }

        public static bool Burning(XUiC_WorkstationFuelGrid grid)
        {
            XUiM_Workstation data = Data(grid);
            return data != null && data.GetBurnTimeLeft() > 0f;
        }
    }

    [HarmonyPatch(typeof(XUiC_WorkstationFuelGrid), "hasAnyFuel")]
    public static class Patch_FuelGrid_hasAnyFuel
    {
        public static void Postfix(XUiC_WorkstationFuelGrid __instance, ref bool __result)
        {
            if (FuelGridHelper.IsChargeGrid(__instance))
                __result = FuelGridHelper.Burning(__instance) || FuelGridHelper.AnyChargeInGrid(__instance);
        }
    }

    [HarmonyPatch(typeof(XUiC_WorkstationFuelGrid), "hasFuelStack")]
    public static class Patch_FuelGrid_hasFuelStack
    {
        public static void Postfix(XUiC_WorkstationFuelGrid __instance, ref bool __result)
        {
            if (FuelGridHelper.IsChargeGrid(__instance)) __result = FuelGridHelper.AnyChargeInGrid(__instance);
        }
    }

    [HarmonyPatch(typeof(XUiC_WorkstationFuelGrid), "HasRequirement")]
    public static class Patch_FuelGrid_HasRequirement
    {
        public static void Postfix(XUiC_WorkstationFuelGrid __instance, ref bool __result)
        {
            if (FuelGridHelper.IsChargeGrid(__instance))
                __result = FuelGridHelper.Burning(__instance) || FuelGridHelper.AnyChargeInGrid(__instance);
        }
    }
}
