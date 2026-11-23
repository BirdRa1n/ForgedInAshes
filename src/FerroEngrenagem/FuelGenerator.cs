// D7 step 3: generators that burn a mod item instead of gasoline (the Coal Generator burns Charcoal).
//
// A vanilla Class="Generator" block opts in with
//   <property name="FeFuelItem" value="feResourceCharcoal"/>   item burned instead of the "gasoline" tag
//   <property name="FeFuelPerItem" value="1"/>                 generator fuel units per item (default 1)
//
// Vanilla (IL 3.4.0 b10) hard-codes gasoline in three places, all on XUiC_PowerSourceStats.tag / the gasoline
// tag; for these blocks we do the same work with the fuel item:
//  - XUiC_PowerSourceStats.BtnRefuel_OnPress: takes up to 250 (and up to MaxFuel - CurrentFuel) items from the
//    toolbelt, else the backpack; server: PowerGenerator.CurrentFuel += n (clamped), CurrentPower = MaxPower;
//    client: ClientData.AddedFuel = n + SetModified. Sound "useactions/gas_refill".
//  - GetBindingValueInternal "fueltitle" = Localization "xuiGas" -> the fuel item's name.
//  - TileEntityPowerSource.ReplacedBy (pick up / replace): drops slots + CurrentFuel as gas cans -> we drop the
//    fuel back as the fuel item and zero CurrentFuel first.
//
// C# 5 only.

using System.Collections.Generic;
using HarmonyLib;
using UnityEngine;

namespace FerroEngrenagem
{
    public static class FuelGenerator
    {
        const string FuelItemProperty = "FeFuelItem";
        const string FuelPerItemProperty = "FeFuelPerItem";

        static readonly Dictionary<int, ItemClass> fuelByBlock = new Dictionary<int, ItemClass>();

        /// <summary>The item this generator burns, or null for vanilla (gasoline) generators.</summary>
        public static ItemClass FuelItem(Block block)
        {
            if (block == null) return null;
            ItemClass ic;
            if (fuelByBlock.TryGetValue(block.blockID, out ic)) return ic;
            ic = null;
            if (block.Properties != null && block.Properties.Contains(FuelItemProperty))
            {
                string name = block.Properties.GetString(FuelItemProperty).Trim();
                ic = name.Length == 0 ? null : ItemClass.GetItemClass(name, false);   // "" = vanilla gasoline
                if (ic == null && name.Length > 0)
                    Log.Warning(FerroEngrenagemMod.LogPrefix + block.GetBlockName() + ": unknown FeFuelItem " + name);
            }
            fuelByBlock[block.blockID] = ic;
            return ic;
        }

        public static int FuelPerItem(Block block)
        {
            int v = 1;
            if (block != null && block.Properties != null && block.Properties.Contains(FuelPerItemProperty))
                v = block.Properties.GetInt(FuelPerItemProperty);
            return v < 1 ? 1 : v;
        }

        /// <summary>Refuel from the player's inventory. Returns false when nothing was added.</summary>
        public static bool Refuel(XUiC_PowerSourceStats stats, TileEntityPowerSource te, ItemClass fuel)
        {
            int per = FuelPerItem(te.blockValue.Block);
            int room = (te.MaxFuel - te.CurrentFuel) / per;
            if (room <= 0) return false;
            int want = Mathf.Min(250, room);
            EntityPlayerLocal player = stats.xui.playerUI.entityPlayer;
            ItemValue iv = new ItemValue(fuel.Id, false);
            int got = player.inventory.DecItem(iv, want, false, null);
            if (got == 0) got = player.bag.DecItem(iv, want, false, null);
            if (got == 0)
            {
                Audio.Manager.PlayInsidePlayerHead("ui_denied", -1, 0f, false, false);
                GameManager.ShowTooltip(player, string.Format(Localization.Get("feFuelNeeded", false),
                                                              fuel.GetLocalizedItemName()), false, false, 0f);
                return false;
            }
            stats.xui.CollectedItemList.RemoveItemStack(new ItemStack(iv, got));
            int add = got * per;
            if (SingletonMonoBehaviour<ConnectionManager>.Instance.IsServer)
            {
                PowerGenerator gen = te.GetPowerItem() as PowerGenerator;
                if (gen != null)
                {
                    gen.CurrentFuel = (ushort)Mathf.Min(gen.MaxFuel, gen.CurrentFuel + add);
                    gen.CurrentPower = gen.MaxPower;
                }
            }
            else
            {
                te.ClientData.AddedFuel = (ushort)add;
                te.SetModified();
            }
            Audio.Manager.PlayInsidePlayerHead("useactions/gas_refill", -1, 0f, false, false);
            stats.RefreshBindings();
            return true;
        }
    }

    [HarmonyPatch(typeof(XUiC_PowerSourceStats), "BtnRefuel_OnPress")]
    public static class Patch_PowerSourceStats_Refuel_FuelItem
    {
        public static bool Prefix(XUiC_PowerSourceStats __instance)
        {
            TileEntityPowerSource te = __instance.TileEntity;
            if (te == null) return true;
            ItemClass fuel = FuelGenerator.FuelItem(te.blockValue.Block);
            if (fuel == null) return true;
            FuelGenerator.Refuel(__instance, te, fuel);
            return false;
        }
    }

    [HarmonyPatch(typeof(XUiC_PowerSourceStats), "GetBindingValueInternal")]
    public static class Patch_PowerSourceStats_FuelTitle
    {
        public static void Postfix(XUiC_PowerSourceStats __instance, ref string value, string bindingName,
                                   ref bool __result)
        {
            if (bindingName != "fueltitle") return;
            TileEntityPowerSource te = __instance.TileEntity;
            ItemClass fuel = te == null ? null : FuelGenerator.FuelItem(te.blockValue.Block);
            if (fuel == null) return;
            value = fuel.GetLocalizedItemName();
            __result = true;
        }
    }

    // Pick up / replace: give the unburned fuel back as the fuel item instead of gas cans.
    [HarmonyPatch(typeof(TileEntityPowerSource), "ReplacedBy")]
    public static class Patch_PowerSource_ReplacedBy_FuelItem
    {
        public static void Prefix(TileEntityPowerSource __instance, BlockValue _bvOld)
        {
            ItemClass fuel = FuelGenerator.FuelItem(_bvOld.Block);
            if (fuel == null || __instance.CurrentFuel == 0) return;
            int count = __instance.CurrentFuel / FuelGenerator.FuelPerItem(_bvOld.Block);
            __instance.CurrentFuel = 0;
            if (count <= 0 || !SingletonMonoBehaviour<ConnectionManager>.Instance.IsServer) return;
            List<ItemStack> stacks = new List<ItemStack>();
            int max = Mathf.Max(1, fuel.Stacknumber.Value);
            while (count > 0)
            {
                int n = Mathf.Min(count, max);
                stacks.Add(new ItemStack(new ItemValue(fuel.Id, false), n));
                count -= n;
            }
            GameManager.Instance.DropContentInLootContainerServer(-1, "DroppedLootContainer",
                __instance.ToWorldCenterPos(), stacks.ToArray(), false, null);
        }
    }
}
