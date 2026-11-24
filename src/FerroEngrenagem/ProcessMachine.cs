// F8.2 (PLANO_CRAFT.md, D11): a generic process machine (FeFluid processor). What it does comes from
// Data/fe_processes.xml: every non-planned <process> whose machine = this block's name.
//
//   Items in: by belt (any side, BeltMachines.Insert) or "Put the item in hand"; kept in a stock of up to 8 crafts of
//     each ingredient. Fluid in: its back port (the fluid_in of its processes: water for the Washer and the Chemical
//     Mixer, steam for the Steam Dryer), buffer FeFluidBuffer L.
//   Runs the first process it has everything for: time seconds, at the torque speed when the process asks torque (the
//     block is then also a torque machine: FeKinetic pump, a shaft on its left or right side).
//   Out: the belt in front, or "Take the casts / products" (fe_cast_take). Up to 64 products wait.
//   State in FluidState: Amount/Fluid = fluid buffer, Steam = progress (s), Mold = running process id, Made/Count =
//   products waiting, Stock = "item=n,..." ingredients.
//
// C# 5 only.

using System.Collections.Generic;
using System.Text;
using UnityEngine;

namespace FerroEngrenagem
{
    public static class ProcessMachine
    {
        const int MaxOut = 64;
        const int StockCrafts = 8;

        public static bool Is(Block b)
        {
            return Fluids.Kind(b) == FluidKind.Processor;
        }

        static List<Process> Of(Block b)
        {
            return Processes.For(b.GetBlockName());
        }

        /// <summary>The fluid its back port takes (null = none).</summary>
        public static string FluidIn(Block b)
        {
            foreach (Process p in Of(b)) if (p.FluidIn != null) return p.FluidIn;
            return null;
        }

        static Dictionary<string, int> Stock(FluidState s)
        {
            Dictionary<string, int> d = new Dictionary<string, int>();
            foreach (string kv in (s.Stock ?? "").Split(','))
            {
                int eq = kv.IndexOf('=');
                int n;
                if (eq > 0 && int.TryParse(kv.Substring(eq + 1), out n) && n > 0) d[kv.Substring(0, eq)] = n;
            }
            return d;
        }

        static void SetStock(FluidState s, Dictionary<string, int> d)
        {
            StringBuilder sb = new StringBuilder();
            foreach (KeyValuePair<string, int> kv in d)
            {
                if (kv.Value <= 0) continue;
                if (sb.Length > 0) sb.Append(',');
                sb.Append(kv.Key).Append('=').Append(kv.Value);
            }
            s.Stock = sb.ToString();
            FluidStore.MarkDirty();
        }

        static int Need(Block b, string item)
        {
            int n = 0;
            foreach (Process p in Of(b))
                for (int i = 0; i < p.Inputs.Length; i++)
                    if (p.Inputs[i] == item) n = Mathf.Max(n, p.Counts[i]);
            return n;
        }

        /// <summary>A belt (or the hand) gives st: how many it takes.</summary>
        public static int Insert(World world, Vector3i p, ItemStack st)
        {
            if (st == null || st.IsEmpty() || st.itemValue.ItemClass == null) return 0;
            Block b = world.GetBlock(p).Block;
            string name = st.itemValue.ItemClass.GetItemName();
            int need = Need(b, name);
            if (need <= 0) return 0;
            FluidStore.EnsureLoaded();
            if (!FluidStore.Devices.Contains(p)) FluidStore.Register(p);
            FluidState s = FluidStore.Get(p);
            Dictionary<string, int> d = Stock(s);
            int have;
            d.TryGetValue(name, out have);
            int take = Mathf.Min(st.count, need * StockCrafts - have);
            if (take <= 0) return 0;
            d[name] = have + take;
            SetStock(s, d);
            return take;
        }

        static bool Ready(Process pr, Dictionary<string, int> d, FluidState s)
        {
            for (int i = 0; i < pr.Inputs.Length; i++)
            {
                int have;
                d.TryGetValue(pr.Inputs[i], out have);
                if (have < pr.Counts[i]) return false;
            }
            if (pr.FluidIn != null && (s.Fluid != pr.FluidIn || s.Amount < pr.Liters - 0.01f)) return false;
            if (s.Count > 0 && s.Made != pr.Output) return false;
            return s.Count + pr.OutCount <= MaxOut;
        }

        static float Speed(World world, Vector3i p, Process pr, FluidState s)
        {
            Block b = world.GetBlock(p).Block;
            if (Industrial.IsElectric(b))
            {
                if (!Industrial.IsPowered(world, p)) { s.Note = "power"; return 0f; }
                return Fluids.Prop(b, "FeProcSpeed", 1f);
            }
            if (pr.Torque <= 0f) return 1f;
            TorqueNet net = Kinetic.Get(world, p);
            if (net == null || !net.Running || !net.Machines.ContainsKey(p)) { s.Note = "torque"; return 0f; }
            return net.MachineSpeed(p);
        }

        /// <summary>Fluid demand of its back port this tick.</summary>
        public static float Demand(World world, Vector3i p, BlockValue bv, FluidState s)
        {
            string f = FluidIn(bv.Block);
            if (f == null) return 0f;
            if (s.Amount > 0.01f && s.Fluid != f) return 0f;
            return Mathf.Max(0f, Fluids.Prop(bv.Block, "FeFluidBuffer", 20f) - s.Amount);
        }

        /// <summary>Every 0.5 s: run a process, then put the products on the belt in front.</summary>
        public static void Tick(World world, Vector3i p, BlockValue bv, FluidState s, float dt)
        {
            Dictionary<string, int> d = Stock(s);
            Process run = null;
            foreach (Process pr in Of(bv.Block))
                if (pr.Id == s.Mold && Ready(pr, d, s)) { run = pr; break; }
            if (run == null)
                foreach (Process pr in Of(bv.Block))
                    if (Ready(pr, d, s)) { run = pr; break; }
            if (run == null)
            {
                s.Steam = 0f;
                s.Note = s.Count >= MaxOut ? "full" : "wait";
            }
            else
            {
                if (run.Id != s.Mold) { s.Mold = run.Id; s.Steam = 0f; }
                float v = Speed(world, p, run, s);
                if (v > 0f)
                {
                    s.Note = "";
                    s.Steam += dt * v;
                    if (s.Steam >= run.Time)
                    {
                        s.Steam = 0f;
                        for (int i = 0; i < run.Inputs.Length; i++) d[run.Inputs[i]] = d[run.Inputs[i]] - run.Counts[i];
                        SetStock(s, d);
                        if (run.FluidIn != null)
                        {
                            s.Amount -= run.Liters;
                            if (s.Amount <= 0.01f) { s.Amount = 0f; s.Fluid = ""; }
                        }
                        s.Made = run.Output;
                        s.Count += run.OutCount;
                        BeltMachines.Note(world, p, run.Id + " -> " + run.OutCount + "x " + run.Output);
                    }
                }
                FluidStore.MarkDirty();
            }
            if (s.Count <= 0 || string.IsNullOrEmpty(s.Made)) return;
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

        static string ItemName(string item)
        {
            ItemValue iv = ItemClass.GetItem(item, false);
            return iv == null || iv.IsEmpty() || iv.ItemClass == null ? item : iv.ItemClass.GetLocalizedItemName();
        }

        public static string Describe(World world, Vector3i p, BlockValue bv, FluidState s)
        {
            StringBuilder sb = new StringBuilder();
            Dictionary<string, int> d = Stock(s);
            List<Process> ps = Of(bv.Block);
            if (ps.Count == 0) return Kinetic.Text("feProcNone", "No processes for this machine");
            sb.Append(Kinetic.Text("feProcMakes", "Makes:"));
            foreach (Process pr in ps)
            {
                List<string> ins = new List<string>();
                for (int i = 0; i < pr.Inputs.Length; i++) ins.Add(pr.Counts[i] + "x " + ItemName(pr.Inputs[i]));
                if (pr.FluidIn != null) ins.Add(Mathf.RoundToInt(pr.Liters) + " L " + Fluids.FluidName(pr.FluidIn));
                sb.Append("\n  ").Append(string.Join(" + ", ins.ToArray())).Append(" -> ").Append(pr.OutCount).Append("x ")
                  .Append(ItemName(pr.Output));
            }
            if (d.Count > 0)
            {
                List<string> st = new List<string>();
                foreach (KeyValuePair<string, int> kv in d) st.Add(kv.Value + "x " + ItemName(kv.Key));
                sb.Append("\n").Append(string.Format(Kinetic.Text("feProcStock", "Inside: {0}"), string.Join(", ", st.ToArray())));
            }
            string f = FluidIn(bv.Block);
            if (f != null)
                sb.Append("\n").Append(string.Format(Kinetic.Text("feFluidStored", "{0}: {1} / {2} L"), Fluids.FluidName(f),
                    Mathf.RoundToInt(s.Fluid == f ? s.Amount : 0f), Mathf.RoundToInt(Fluids.Prop(bv.Block, "FeFluidBuffer", 20f))));
            foreach (Process pr in ps)
                if (pr.Id == s.Mold && s.Steam > 0f)
                    sb.Append("\n").Append(string.Format(Kinetic.Text("feProcWorking", "Working: {0}%"),
                        Mathf.RoundToInt(100f * s.Steam / Mathf.Max(0.1f, pr.Time))));
            if (s.Count > 0) sb.Append("\n").Append(string.Format(Kinetic.Text("feCasterReady", "Ready: {0}x {1}"), s.Count, ItemName(s.Made)));
            if (s.Note == "torque") sb.Append("\n").Append(Kinetic.Text("feFluidNoTorque", "No torque on its shaft"));
            else if (s.Note == "power") sb.Append("\n").Append(Kinetic.Text("feFluidNoPower", "No power: wire it to a power source"));
            else if (s.Note == "full") sb.Append("\n").Append(Kinetic.Text("feCasterFull", "Full: take the casts or put a belt in front"));
            return sb.ToString();
        }

        /// <summary>Radial commands: fe_put (the item in hand) and fe_cast_take (the products).</summary>
        public static string Activate(World world, Vector3i p, string cmd, EntityPlayerLocal player)
        {
            FluidStore.EnsureLoaded();
            FluidState s = FluidStore.Get(p);
            if (cmd == "fe_cast_take")
            {
                if (s.Count <= 0 || string.IsNullOrEmpty(s.Made)) return Kinetic.Text("feProcNothing", "Nothing made yet");
                ItemValue iv = ItemClass.GetItem(s.Made, false);
                if (iv == null || iv.IsEmpty()) return Kinetic.Text("feProcNothing", "Nothing made yet");
                int n = s.Count;
                s.Count = 0;
                ItemStack st = new ItemStack(iv, n);
                if (!player.bag.AddItem(st)) GameManager.Instance.ItemDropServer(st, player.GetPosition(), Vector3.zero, -1, 60f, false);
                FluidStore.MarkDirty();
                return string.Format(Kinetic.Text("feBottled", "Took {0}x {1}"), n, iv.ItemClass.GetLocalizedItemName());
            }
            ItemStack held = player.inventory.holdingItemStack;
            if (held == null || held.IsEmpty()) return Kinetic.Text("feProcHold", "Hold an ingredient of this machine");
            int took = Insert(world, p, held);
            if (took <= 0) return Kinetic.Text("fePourNo", "It does not take this (or it is full)");
            ItemStack left = held.Clone();
            left.count -= took;
            player.inventory.SetItem(player.inventory.holdingItemIdx, left.count > 0 ? left : ItemStack.Empty.Clone());
            return string.Format(Kinetic.Text("feProcPut", "Put in {0}"), took);
        }
    }
}
