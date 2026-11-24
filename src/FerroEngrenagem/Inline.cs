// D12 / PLANO_CRAFT.md 6.5 (Create's "sequenced assembly"): in-line stations.
//
// A station (a process machine with FeInline=true) sits ON TOP of a belt. An item on that belt whose kind is the FIRST
// input of one of the station's processes stops in the middle of the belt, the station works on it (time, torque or
// power, its other inputs from its own stock - by belt at its level, a funnel, an arm or by hand - and its fluids from
// its back port), and the item becomes the product and goes on. A stack is worked as a whole: k = count / first count
// crafts at once (as many as its stock allows). By-products and what is left of the stack drop back on the belt.
// Sequences (casing -> powder -> tip -> crimp) are chains of distinct "incomplete" items, one station each.
//
// C# 5 only.

using System.Collections.Generic;
using UnityEngine;

namespace FerroEngrenagem
{
    public static class Inline
    {
        /// <summary>The station on top of the belt at pos (false when none).</summary>
        public static bool StationAt(World world, Vector3i pos, out Vector3i station, out BlockValue sbv)
        {
            station = new Vector3i(pos.x, pos.y + 1, pos.z);
            sbv = world.GetBlock(station);
            if (sbv.isair || !ProcessMachine.Is(sbv.Block) || !ProcessMachine.IsInline(sbv.Block)) return false;
            station = Fluids.ParentOf(world, station, sbv);
            return true;
        }

        static Process For(Block b, FluidState s, ItemStack st)
        {
            if (st == null || st.IsEmpty() || st.itemValue.ItemClass == null) return null;
            string n = st.itemValue.ItemClass.GetItemName();
            foreach (Process p in ProcessMachine.Allowed(b, s))
                if (p.Inputs.Length > 0 && p.Inputs[0] == n && st.count >= p.Counts[0]) return p;
            return null;
        }

        /// <summary>Does the station want this item (it stops under it)?</summary>
        public static bool Wants(World world, Vector3i station, BlockValue sbv, ItemStack st)
        {
            FluidStore.EnsureLoaded();
            FluidState s = FluidStore.Get(station);
            return !s.Off && For(sbv.Block, s, st) != null;
        }

        /// <summary>The item is under the station: work on it. Returns true when it is done (the stack changed).</summary>
        public static bool Work(World world, Vector3i belt, Vector3i station, BlockValue sbv, BeltItem it, float dt)
        {
            if (!FluidStore.Devices.Contains(station)) FluidStore.Register(station);
            FluidState s = FluidStore.Get(station);
            Process p = For(sbv.Block, s, it.Stack);
            if (p == null) return false;
            Dictionary<string, int> d = ProcessMachine.Map(s.Stock);
            string why;
            if (!ProcessMachine.Ready(sbv.Block, p, d, s, 1, out why)) { s.Note = why == "full" ? "full" : "wait"; s.Steam = 0f; return false; }
            if (p.Id != s.Mold) { s.Mold = p.Id; s.Steam = 0f; }
            float v = ProcessMachine.Speed(world, station, p, s);
            if (v <= 0f) return false;
            s.Note = "";
            s.Steam += dt * v;
            FluidStore.MarkDirty();
            if (s.Steam < p.Time) return false;
            s.Steam = 0f;
            // how many crafts at once: the stack, limited by the station's stock and fluids
            int k = it.Stack.count / Mathf.Max(1, p.Counts[0]);
            for (int i = 1; i < p.Inputs.Length; i++)
            {
                int have;
                d.TryGetValue(p.Inputs[i], out have);
                k = Mathf.Min(k, have / Mathf.Max(1, p.Counts[i]));
            }
            for (int i = 0; i < p.FluidIns.Length; i++)
            {
                string held;
                float lv = ProcessMachine.Level(s, "in" + i, out held);
                if (p.LitersIn[i] > 0f) k = Mathf.Min(k, Mathf.FloorToInt(lv / p.LitersIn[i] + 0.001f));
            }
            if (k <= 0) return false;
            for (int i = 1; i < p.Inputs.Length; i++) d[p.Inputs[i]] = d[p.Inputs[i]] - p.Counts[i] * k;
            s.Stock = ProcessMachine.Unmap(d);
            for (int i = 0; i < p.FluidIns.Length; i++)
            {
                string held;
                float lv = ProcessMachine.Level(s, "in" + i, out held);
                Dictionary<string, ProcessMachine.Tank> tk = ProcessMachine.Tanks(s);
                if (i == 0) { s.Amount = Mathf.Max(0f, s.Amount - p.LitersIn[i] * k); if (s.Amount <= 0.01f) { s.Amount = 0f; s.Fluid = ""; } }
                else
                {
                    ProcessMachine.Tank t;
                    if (tk.TryGetValue("in" + i, out t)) { t.Amount = Mathf.Max(0f, t.Amount - p.LitersIn[i] * k); ProcessMachine.SetTanks(s, tk); }
                }
            }
            int rest = it.Stack.count - k * p.Counts[0];
            // the product replaces the stack on the belt; by-products and the rest wait in the station (Out)
            ItemValue ov = p.Output == null ? null : ItemClass.GetItem(p.Output, false);
            FluidState tmp = s;
            if (ov != null && !ov.IsEmpty())
            {
                it.Stack = new ItemStack(ov, p.OutCount * k);
                Process noMain = new Process { Output = null, Extra = p.Extra, ExtraCount = p.ExtraCount, Chance = p.Chance,
                                               FluidOuts = p.FluidOuts, LitersOut = p.LitersOut };
                ProcessMachine.Produce(world, station, sbv, noMain, tmp, k);
            }
            else
            {
                ProcessMachine.Produce(world, station, sbv, p, tmp, k);
                it.Stack.count = 0;
            }
            if (rest > 0)
            {
                Dictionary<string, int> o = ProcessMachine.Outs(s);
                string n = p.Inputs[0];
                int have;
                o.TryGetValue(n, out have);
                o[n] = have + rest;
                s.Out = ProcessMachine.Unmap(o);
            }
            BeltStore.MarkDirty();
            BeltMachines.Note(world, station, p.Id + " in line -> " + (ov != null ? p.OutCount * k + "x " + p.Output : "fluids"));
            return true;
        }

        /// <summary>Every 0.5 s: what waits in a station (by-products, rest of stacks) drops back on the belt under it.</summary>
        public static void PushOut(World world, Vector3i station, FluidState s)
        {
            Dictionary<string, int> o = ProcessMachine.Outs(s);
            if (o.Count == 0) return;
            Vector3i belt = new Vector3i(station.x, station.y - 1, station.z);
            BlockValue bb = world.GetBlock(belt);
            if (!Belt.Is(bb.Block)) return;
            List<BeltItem> items = BeltStore.Items(belt, true);
            float p = 0.75f;
            if (!Belt.Room(items, p)) return;
            string first = null;
            foreach (string k in o.Keys) { first = k; break; }
            ItemValue iv = ItemClass.GetItem(first, false);
            if (iv == null || iv.IsEmpty()) { o.Remove(first); s.Out = ProcessMachine.Unmap(o); return; }
            int n = Mathf.Min(o[first], Mathf.Max(1, iv.ItemClass.Stacknumber.Value));
            BeltItem it = BeltStore.Add(belt, new ItemStack(iv, n), p);
            Belt.ChooseExit(world, belt, bb, it);
            o[first] -= n;
            s.Out = ProcessMachine.Unmap(o);
            FluidStore.MarkDirty();
        }
    }
}
