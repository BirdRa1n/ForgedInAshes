// F8.1 (PLANO_CRAFT.md, D11): metallurgy.
//
//   Foundry (FeFluid smelter): scrap / ingots that arrive by belt (or "Melt the item in hand") melt into its metal
//     buffer (FeMetalBuffer L, one metal at a time), burning the fuel in its fuel slots (1 s of fuel value per second
//     of melting). The melt processes (input, litres, seconds) come from Data/fe_processes.xml (kind="melt",
//     machine = the block name). The metal leaves through any outer side of its bottom layer with a Metal Chute.
//   Metal Chute (FeFluid chute): a pipe for molten metal only (FluidNetwork: chutes and pipes never join).
//   Casting Table (FeFluid caster): holds one mold (an item; kind="cast" processes say which metals it takes and
//     what it makes). Takes metal at its back up to one cast, cools it (time; twice as fast next to a tank of water),
//     then the casts go on the belt in front, or to the player ("Take the casts"). Changing the mold only while empty.
//   State in FluidState (Amount/Fluid = metal, Steam = heat (Foundry) or cooling time (Table), Mold, Made, Count).
//
// C# 5 only.

using System.Collections.Generic;
using HarmonyLib;
using UnityEngine;

namespace FerroEngrenagem
{
    public static class MetalWorks
    {
        const string CasterBlock = "feCaster";
        const int MaxCasts = 64;

        // ------------------------------------------------------------ processes
        static Process MeltOf(string machine, string item)
        {
            foreach (Process p in Processes.For(machine))
                if (p.Kind == "melt" && p.Inputs.Length > 0 && p.Inputs[0] == item && p.FluidOut != null) return p;
            return null;
        }

        static Process CastOf(string mold, string fluid)
        {
            if (string.IsNullOrEmpty(mold)) return null;
            foreach (Process p in Processes.For(CasterBlock))
                if (p.Kind == "cast" && p.Mold == mold && (fluid == null || p.FluidIn == fluid)) return p;
            return null;
        }

        static readonly Dictionary<string, string[]> metalsCache = new Dictionary<string, string[]>();

        /// <summary>The metals a mold takes (null = no mold).</summary>
        public static string[] MoldMetals(string mold)
        {
            if (string.IsNullOrEmpty(mold)) return null;
            string[] r;
            if (metalsCache.TryGetValue(mold, out r)) return r;
            List<string> l = new List<string>();
            foreach (Process p in Processes.For(CasterBlock))
                if (p.Kind == "cast" && p.Mold == mold && p.FluidIn != null && !l.Contains(p.FluidIn)) l.Add(p.FluidIn);
            r = l.ToArray();
            metalsCache[mold] = r;
            return r;
        }

        public static bool IsMold(string item)
        {
            return CastOf(item, null) != null;
        }

        static string ItemName(string item)
        {
            ItemValue iv = ItemClass.GetItem(item, false);
            return iv == null || iv.IsEmpty() || iv.ItemClass == null ? item : iv.ItemClass.GetLocalizedItemName();
        }

        // ------------------------------------------------------------ Foundry
        static void Ensure(World world, Vector3i p)
        {
            FluidStore.EnsureLoaded();
            if (!FluidStore.Devices.Contains(p) && SingletonMonoBehaviour<ConnectionManager>.Instance.IsServer) FluidStore.Register(p);
        }

        /// <summary>Melt what fits of st into the Foundry at p. Returns how many items melted (st is not changed).</summary>
        public static int Melt(World world, Vector3i p, TileEntityWorkstation te, ItemStack st, out string why)
        {
            why = "";
            if (st == null || st.IsEmpty() || st.itemValue.ItemClass == null) return 0;
            Block b = world.GetBlock(p).Block;
            Process pr = MeltOf(b.GetBlockName(), st.itemValue.ItemClass.GetItemName());
            if (pr == null) { why = Kinetic.Text("feMeltNo", "This does not melt here"); return 0; }
            Ensure(world, p);
            FluidState s = FluidStore.Get(p);
            if (s.Amount > 0.01f && s.Fluid.Length > 0 && s.Fluid != pr.FluidOut)
            {
                why = string.Format(Kinetic.Text("feMeltOther", "It holds {0}: let it flow out first"), Fluids.FluidName(s.Fluid));
                return 0;
            }
            float cap = Fluids.Prop(b, "FeMetalBuffer", 200f);
            int n = Mathf.Min(st.count, Mathf.FloorToInt((cap - s.Amount) / Mathf.Max(0.01f, pr.OutLiters) + 0.001f));
            if (n <= 0) { why = Kinetic.Text("feMeltFull", "Its metal is full: connect a Metal Chute to it"); return 0; }
            int done = 0;
            ItemStack[] fuel = te == null ? null : te.Fuel;
            while (done < n)
            {
                if (s.Steam < pr.Time)
                {
                    if (te == null) break;   // Induction Furnace: only the heat its power built up
                    bool burnt = false;
                    for (int i = 0; fuel != null && i < fuel.Length && !burnt; i++)
                    {
                        if (fuel[i] == null || fuel[i].IsEmpty()) continue;
                        int v = ItemClass.GetFuelValue(fuel[i].itemValue);
                        if (v <= 0) continue;
                        s.Steam += v;
                        fuel[i].count--;
                        if (fuel[i].count <= 0) fuel[i] = ItemStack.Empty.Clone();
                        burnt = true;
                    }
                    if (!burnt) break;
                    te.Fuel = fuel;
                    te.SetModified();
                    continue;
                }
                s.Steam -= pr.Time;
                s.Amount += pr.OutLiters;
                s.Fluid = pr.FluidOut;
                done++;
            }
            if (done == 0)
                why = te == null
                    ? (Industrial.IsPowered(world, p) ? Kinetic.Text("feMeltHeating", "Heating up: wait a moment")
                                                      : Kinetic.Text("feFluidNoPower", "No power: wire it to a power source"))
                    : Kinetic.Text("feMeltNoFuel", "No fuel to melt it: put fuel in the Foundry");
            if (done > 0) FluidStore.MarkDirty();
            return done;
        }

        public static string DescribeSmelter(World world, Vector3i p)
        {
            Ensure(world, p);
            FluidState s = FluidStore.Get(p);
            Block b = world.GetBlock(p).Block;
            string t = string.Format(Kinetic.Text("feFluidStored", "{0}: {1} / {2} L"), Fluids.FluidName(s.Fluid),
                                     Mathf.RoundToInt(s.Amount), Mathf.RoundToInt(Fluids.Prop(b, "FeMetalBuffer", 200f)));
            if (s.Steam > 0.5f) t += " - " + string.Format(Kinetic.Text("feMeltHeat", "heat {0} s"), Mathf.RoundToInt(s.Steam));
            return t;
        }

        // ------------------------------------------------------------ Casting Table
        static bool WaterNear(World world, Vector3i p)
        {
            foreach (Vector3i d in new Vector3i[] { new Vector3i(1, 0, 0), new Vector3i(-1, 0, 0), new Vector3i(0, 0, 1), new Vector3i(0, 0, -1), new Vector3i(0, -1, 0) })
            {
                Vector3i n = new Vector3i(p.x + d.x, p.y + d.y, p.z + d.z);
                if (world.IsWater(n.x, n.y, n.z)) return true;
                if (Fluids.Kind(world.GetBlock(n).Block) == FluidKind.Tank)
                {
                    FluidState ts = FluidStore.Get(n);
                    if (ts.Fluid == Fluids.Water && ts.Amount > 1f) return true;
                }
            }
            return false;
        }

        /// <summary>Litres of metal the table takes this tick.</summary>
        public static float CasterDemand(World world, Vector3i p, BlockValue bv, FluidState s, float dt)
        {
            if (string.IsNullOrEmpty(s.Mold)) { s.Note = "mold"; return 0f; }
            if (s.Count >= MaxCasts) { s.Note = "full"; return 0f; }
            float rate = Fluids.Prop(bv.Block, "FeFluidRate", 300f) * dt / 60f;
            if (s.Amount > 0.01f)
            {
                Process pr = CastOf(s.Mold, s.Fluid);
                if (pr == null) return 0f;
                if (s.Count > 0 && s.Made != pr.Output) { s.Note = "full"; return 0f; }
                s.Note = "";
                return Mathf.Clamp(pr.Liters - s.Amount, 0f, rate);
            }
            float dose = float.MaxValue;
            foreach (Process pr in Processes.For(CasterBlock))
                if (pr.Kind == "cast" && pr.Mold == s.Mold && (s.Count == 0 || s.Made == pr.Output)) dose = Mathf.Min(dose, pr.Liters);
            if (dose == float.MaxValue) { s.Note = "full"; return 0f; }
            s.Note = "";
            return Mathf.Min(dose, rate);
        }

        /// <summary>Every 0.5 s: cool a full cast, then put the casts on the belt in front.</summary>
        public static void TickCaster(World world, Vector3i p, BlockValue bv, FluidState s)
        {
            Process pr = s.Amount > 0.01f ? CastOf(s.Mold, s.Fluid) : null;
            if (pr != null && s.Amount >= pr.Liters - 0.01f)
            {
                float cool = WaterNear(world, p) ? 1f : 0.5f;
                if (Industrial.IsElectric(bv.Block) && Industrial.IsPowered(world, p))
                    cool = 0.5f * Fluids.Prop(bv.Block, "FeCoolFactor", 4f);   // the electric fan
                s.Steam += cool;
                if (s.Steam >= pr.Time)
                {
                    s.Steam = 0f;
                    s.Amount -= pr.Liters;
                    if (s.Amount <= 0.01f) { s.Amount = 0f; s.Fluid = ""; }
                    s.Made = pr.Output;
                    s.Count += pr.OutCount;
                    BeltMachines.Note(world, p, "cast " + pr.OutCount + "x " + pr.Output + " (" + pr.FluidIn + ", " + s.Mold + ")");
                }
                FluidStore.MarkDirty();
            }
            if (s.Count <= 0 || s.Made.Length == 0) return;
            Vector3i f = Fluids.Rot(bv, Vector3.forward);
            Vector3i dst = new Vector3i(p.x + f.x, p.y + f.y, p.z + f.z);
            if (!Belt.Accepts(world, dst, f)) return;
            float entry = Belt.EntryP(world, dst, f);
            List<BeltItem> items = BeltStore.Items(dst, false);
            if (!Belt.Room(items, entry)) return;
            if (items != null && entry == 0f)
                foreach (BeltItem o in items) if (o.P < entry + Belt.Gap) return;
            ItemValue iv = ItemClass.GetItem(s.Made, false);
            if (iv == null || iv.IsEmpty()) return;
            int n = Mathf.Min(s.Count, Mathf.Max(1, iv.ItemClass.Stacknumber.Value));
            BeltItem it = BeltStore.Add(dst, new ItemStack(iv, n), entry);
            Belt.ChooseExit(world, dst, world.GetBlock(dst), it);
            s.Count -= n;
            FluidStore.MarkDirty();
        }

        public static string DescribeCaster(World world, Vector3i p, BlockValue bv, FluidState s)
        {
            if (string.IsNullOrEmpty(s.Mold))
                return Kinetic.Text("feCasterNoMold", "No mold: hold a mold and choose \"Change the mold\"");
            string[] metals = MoldMetals(s.Mold);
            List<string> names = new List<string>();
            if (metals != null) foreach (string m in metals) names.Add(Fluids.FluidName(m));
            string t = string.Format(Kinetic.Text("feCasterMold", "Mold: {0} (takes {1})"), ItemName(s.Mold), string.Join(", ", names.ToArray()));
            Process pr = s.Amount > 0.01f ? CastOf(s.Mold, s.Fluid) : null;
            if (pr != null)
            {
                t += "\n" + string.Format(Kinetic.Text("feFluidStored", "{0}: {1} / {2} L"), Fluids.FluidName(s.Fluid),
                                          Mathf.RoundToInt(s.Amount), Mathf.RoundToInt(pr.Liters));
                if (s.Amount >= pr.Liters - 0.01f)
                    t += " - " + string.Format(Kinetic.Text("feCasterCooling", "cooling {0}%"),
                                               Mathf.RoundToInt(100f * s.Steam / Mathf.Max(0.1f, pr.Time)));
            }
            else t += "\n" + Kinetic.Text("feCasterWaiting", "Waiting for metal at its back (Metal Chute)");
            if (s.Count > 0) t += "\n" + string.Format(Kinetic.Text("feCasterReady", "Ready: {0}x {1}"), s.Count, ItemName(s.Made));
            if (s.Note == "full") t += "\n" + Kinetic.Text("feCasterFull", "Full: take the casts or put a belt in front");
            return t;
        }

        /// <summary>Radial commands of the Casting Table.</summary>
        public static string Activate(World world, Vector3i p, string cmd, EntityPlayerLocal player)
        {
            FluidStore.EnsureLoaded();
            FluidState s = FluidStore.Get(p);
            if (cmd == "fe_cast_take")
            {
                if (s.Count <= 0 || s.Made.Length == 0) return Kinetic.Text("feCasterNone", "Nothing cast yet");
                ItemValue iv = ItemClass.GetItem(s.Made, false);
                if (iv == null || iv.IsEmpty()) return Kinetic.Text("feCasterNone", "Nothing cast yet");
                ItemStack st = new ItemStack(iv, s.Count);
                int n = s.Count;
                s.Count = 0;
                if (!player.bag.AddItem(st)) GameManager.Instance.ItemDropServer(st, player.GetPosition(), Vector3.zero, -1, 60f, false);
                FluidStore.MarkDirty();
                return string.Format(Kinetic.Text("feBottled", "Took {0}x {1}"), n, iv.ItemClass.GetLocalizedItemName());
            }
            // fe_mold: put the mold in your hand in (giving back the old one), or with an empty hand take it out
            ItemStack held = player.inventory.holdingItemStack;
            string heldName = held == null || held.IsEmpty() || held.itemValue.ItemClass == null ? null : held.itemValue.ItemClass.GetItemName();
            bool heldMold = heldName != null && IsMold(heldName);
            if (!heldMold && s.Mold.Length == 0) return Kinetic.Text("feCasterHoldMold", "Hold a mold to put it in");
            if (s.Amount > 0.01f) return Kinetic.Text("feCasterBusy", "There is metal in the mold: wait for the cast");
            string old = s.Mold;
            if (heldMold)
            {
                if (heldName == old) return string.Format(Kinetic.Text("feCasterMold", "Mold: {0} (takes {1})"), ItemName(old), "...");
                ItemStack left = held.Clone();
                left.count--;
                player.inventory.SetItem(player.inventory.holdingItemIdx, left.count > 0 ? left : ItemStack.Empty.Clone());
                s.Mold = heldName;
            }
            else s.Mold = "";
            s.Steam = 0f;
            if (old.Length > 0)
            {
                ItemValue ov = ItemClass.GetItem(old, false);
                if (ov != null && !ov.IsEmpty())
                {
                    ItemStack back = new ItemStack(ov, 1);
                    if (!player.bag.AddItem(back)) GameManager.Instance.ItemDropServer(back, player.GetPosition(), Vector3.zero, -1, 60f, false);
                }
            }
            FluidStore.MarkDirty();
            Log.Out(FerroEngrenagemMod.LogPrefix + "caster at " + p + ": mold " + (old.Length > 0 ? old : "none") + " -> " + (s.Mold.Length > 0 ? s.Mold : "none"));
            return s.Mold.Length > 0
                ? string.Format(Kinetic.Text("feCasterMold", "Mold: {0} (takes {1})"), ItemName(s.Mold), MetalList(s.Mold))
                : Kinetic.Text("feCasterMoldOut", "Mold taken out");
        }

        static string MetalList(string mold)
        {
            List<string> names = new List<string>();
            string[] m = MoldMetals(mold);
            if (m != null) foreach (string x in m) names.Add(Fluids.FluidName(x));
            return string.Join(", ", names.ToArray());
        }

        /// <summary>Every 0.5 s: an electric smelter builds up heat while powered (FeMeltSpeed s of melting per s,
        /// up to FeHeatMax).</summary>
        public static void TickElectricSmelter(World world, Vector3i p, BlockValue bv, FluidState s)
        {
            if (!Industrial.IsPowered(world, p)) { s.Note = "power"; return; }
            s.Note = "";
            float max = Fluids.Prop(bv.Block, "FeHeatMax", 20f);
            if (s.Steam < max) { s.Steam = Mathf.Min(max, s.Steam + 0.5f * Fluids.Prop(bv.Block, "FeMeltSpeed", 2f)); FluidStore.MarkDirty(); }
        }

        /// <summary>Is this a Foundry with a melt buffer?</summary>
        public static bool IsSmelter(Block b)
        {
            return Fluids.Kind(b) == FluidKind.Smelter;
        }
    }

    // Foundry: "Melt the item in hand" and the metal readout
    [HarmonyPatch(typeof(BlockWorkstation), "GetBlockActivationCommands")]
    public static class Patch_Workstation_Commands_Melt
    {
        public static void Postfix(BlockWorkstation __instance, ref BlockActivationCommand[] __result)
        {
            if (!MetalWorks.IsSmelter(__instance) || __result == null) return;
            foreach (BlockActivationCommand c in __result) if (c.text == "fe_melt") return;
            BlockActivationCommand[] r = new BlockActivationCommand[__result.Length + 1];
            __result.CopyTo(r, 0);
            r[__result.Length] = new BlockActivationCommand("fe_melt", "loot_sort", true, false, null);
            __result = r;
        }
    }

    [HarmonyPatch(typeof(BlockWorkstation), "OnBlockActivated", new System.Type[] { typeof(string), typeof(WorldBase), typeof(Vector3i), typeof(BlockValue), typeof(EntityPlayerLocal) })]
    public static class Patch_Workstation_Activated_Melt
    {
        public static bool Prefix(string _commandName, WorldBase _world, Vector3i _blockPos, BlockValue _blockValue, EntityPlayerLocal _player, ref bool __result)
        {
            if (_commandName != "fe_melt") return true;
            World w = _world as World;
            __result = true;
            if (w == null) return false;
            Vector3i p = Fluids.ParentOf(w, _blockPos, _blockValue);
            TileEntityWorkstation te = w.GetTileEntity(p) as TileEntityWorkstation;
            ItemStack held = _player.inventory.holdingItemStack;
            if (te == null || held == null || held.IsEmpty())
            {
                GameManager.ShowTooltip(_player, Kinetic.Text("feMeltHold", "Hold the scrap or ingots to melt"), false, false, 0f);
                return false;
            }
            string why;
            int n = MetalWorks.Melt(w, p, te, held, out why);
            if (n > 0)
            {
                ItemStack left = held.Clone();
                left.count -= n;
                _player.inventory.SetItem(_player.inventory.holdingItemIdx, left.count > 0 ? left : ItemStack.Empty.Clone());
                why = string.Format(Kinetic.Text("feMelted", "Melted {0}"), n);
            }
            GameManager.ShowTooltip(_player, why, false, false, 0f);
            return false;
        }
    }

    [HarmonyPatch(typeof(BlockWorkstation), "GetActivationText")]
    public static class Patch_Workstation_Text_Melt
    {
        public static void Postfix(BlockWorkstation __instance, WorldBase _world, BlockValue _blockValue, Vector3i _blockPos, ref string __result)
        {
            if (!MetalWorks.IsSmelter(__instance)) return;
            World w = _world as World;
            if (w == null) return;
            string d = MetalWorks.DescribeSmelter(w, Fluids.ParentOf(w, _blockPos, _blockValue));
            __result = (string.IsNullOrEmpty(__result) ? "" : __result + "\n") + KineticLookController.Escape(d);
        }
    }
}
