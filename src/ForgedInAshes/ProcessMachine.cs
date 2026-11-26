// F8.2 (PLANO_CRAFT.md, D11): a generic process machine (FeFluid processor). What it does comes from
// Data/fe_processes.xml: every non-planned <process> whose machine = this block's name.
//
//   Items in: by belt (any side, BeltMachines.Insert), a Mechanical Arm, or "Put the item in hand"; kept in a stock of
//     up to 8 crafts of each ingredient.
//   Fluids (D12, PLANO_CADEIA.md 9): input 1 at its BACK, input 2 at its BOTTOM; outputs 1..3 at its TOP, RIGHT and LEFT.
//     The first input is the old Amount/Fluid buffer; the others live in FluidState.Tanks ("in1=water:12,out0=..").
//     A tower base (FeTower=true) keeps fraction 1 (its first fluid output) and offers it on its right and left; each
//     further fraction goes to the Tower Section stacked k blocks above it (no section there: that fraction is lost).
//   Runs the first process it has everything for (or the one chosen): time seconds, at the torque speed when the
//     process asks torque (the block is then also a torque machine), only while powered when it is electric, only with
//     a lit burner next to it when the process (or the block, FeHeat) asks heat (electric machines heat themselves),
//     and only with the pressure asked at its gas inputs.
//   Out: items on the belt in front, or "Take the products"; by-products (extra, with a chance) too. Up to 64 wait.
//   In-line stations (FeInline=true, Inline.cs) take their first input from the belt under them, not from the stock.
//   State in FluidState: Steam = progress (s), Mold = running process id, Stock = ingredients, Out = products waiting,
//   Tanks = extra fluid buffers, Off = switched off from its panel, Pick = the recipe chosen.
//
// C# 5 only.

using System.Collections.Generic;
using System.Globalization;
using System.Text;
using UnityEngine;

namespace ForgedInAshes
{
    public static class ProcessMachine
    {
        public const int MaxOut = 64;
        const int StockCrafts = 8;

        public static bool Is(Block b)
        {
            return Fluids.Kind(b) == FluidKind.Processor;
        }

        public static List<Process> Of(Block b)
        {
            return Processes.For(b.GetBlockName());
        }

        public static bool IsInline(Block b)
        {
            return b != null && b.Properties != null && b.Properties.Contains("FeInline") && b.Properties.GetBool("FeInline");
        }

        public static bool IsTower(Block b)
        {
            return b != null && b.Properties != null && b.Properties.Contains("FeTower") && b.Properties.GetBool("FeTower");
        }

        /// <summary>The fluid its back port takes (null = none).</summary>
        public static string FluidIn(Block b)
        {
            foreach (Process p in Of(b)) if (p.FluidIn != null) return p.FluidIn;
            return null;
        }

        // ------------------------------------------------------------ maps "key=value,..."
        public static Dictionary<string, int> Map(string text)
        {
            Dictionary<string, int> d = new Dictionary<string, int>();
            foreach (string kv in (text ?? "").Split(','))
            {
                int eq = kv.IndexOf('=');
                int n;
                if (eq > 0 && int.TryParse(kv.Substring(eq + 1), out n) && n > 0) d[kv.Substring(0, eq)] = n;
            }
            return d;
        }

        public static string Unmap(Dictionary<string, int> d)
        {
            StringBuilder sb = new StringBuilder();
            foreach (KeyValuePair<string, int> kv in d)
            {
                if (kv.Value <= 0) continue;
                if (sb.Length > 0) sb.Append(',');
                sb.Append(kv.Key).Append('=').Append(kv.Value);
            }
            return sb.ToString();
        }

        static Dictionary<string, int> Stock(FluidState s)
        {
            return Map(s.Stock);
        }

        static void SetStock(FluidState s, Dictionary<string, int> d)
        {
            s.Stock = Unmap(d);
            FluidStore.MarkDirty();
        }

        /// <summary>Products waiting (old saves: Made / Count are moved into Out).</summary>
        public static Dictionary<string, int> Outs(FluidState s)
        {
            Dictionary<string, int> d = Map(s.Out);
            if (s.Count > 0 && !string.IsNullOrEmpty(s.Made))
            {
                int have;
                d.TryGetValue(s.Made, out have);
                d[s.Made] = have + s.Count;
                s.Count = 0;
                s.Made = "";
                s.Out = Unmap(d);
            }
            return d;
        }

        public static int OutTotal(FluidState s)
        {
            int n = 0;
            foreach (int v in Outs(s).Values) n += v;
            return n;
        }

        // ------------------------------------------------------------ fluid buffers: slot "in0" = Amount/Fluid
        public class Tank
        {
            public string Fluid = "";
            public float Amount;
        }

        public static Dictionary<string, Tank> Tanks(FluidState s)
        {
            Dictionary<string, Tank> d = new Dictionary<string, Tank>();
            foreach (string kv in (s.Tanks ?? "").Split(','))
            {
                int eq = kv.IndexOf('='), co = kv.IndexOf(':');
                float a;
                if (eq <= 0 || co <= eq) continue;
                if (!float.TryParse(kv.Substring(co + 1), NumberStyles.Float, CultureInfo.InvariantCulture, out a)) continue;
                d[kv.Substring(0, eq)] = new Tank { Fluid = kv.Substring(eq + 1, co - eq - 1), Amount = a };
            }
            return d;
        }

        public static void SetTanks(FluidState s, Dictionary<string, Tank> d)
        {
            StringBuilder sb = new StringBuilder();
            foreach (KeyValuePair<string, Tank> kv in d)
            {
                if (kv.Value.Amount <= 0.01f) continue;
                if (sb.Length > 0) sb.Append(',');
                sb.Append(kv.Key).Append('=').Append(kv.Value.Fluid).Append(':')
                  .Append(kv.Value.Amount.ToString("0.###", CultureInfo.InvariantCulture));
            }
            s.Tanks = sb.ToString();
        }

        /// <summary>Litres of fluid in slot ("in0", "in1", "out0".."out2").</summary>
        public static float Level(FluidState s, string slot, out string fluid)
        {
            if (slot == "in0") { fluid = s.Fluid; return s.Amount; }
            Tank t;
            if (Tanks(s).TryGetValue(slot, out t)) { fluid = t.Fluid; return t.Amount; }
            fluid = "";
            return 0f;
        }

        static void AddLevel(FluidState s, string slot, string fluid, float litres)
        {
            if (slot == "in0")
            {
                s.Amount = Mathf.Max(0f, s.Amount + litres);
                s.Fluid = s.Amount > 0.01f ? fluid : "";
                if (s.Amount <= 0.01f) s.Amount = 0f;
                return;
            }
            Dictionary<string, Tank> d = Tanks(s);
            Tank t;
            if (!d.TryGetValue(slot, out t)) { t = new Tank(); d[slot] = t; }
            t.Amount = Mathf.Max(0f, t.Amount + litres);
            t.Fluid = t.Amount > 0.01f ? fluid : "";
            SetTanks(s, d);
        }

        static float Buffer(Block b)
        {
            return Fluids.Prop(b, "FeFluidBuffer", 20f);
        }

        // fluids each slot may hold (from all its processes)
        static List<string> InFluids(Block b, int slot)
        {
            List<string> l = new List<string>();
            foreach (Process p in Of(b))
                if (p.FluidIns.Length > slot && !l.Contains(p.FluidIns[slot])) l.Add(p.FluidIns[slot]);
            return l;
        }

        static bool OutMetal(Block b, int slot)
        {
            foreach (Process p in Of(b))
                if (p.FluidOuts.Length > slot && Fluids.IsMetal(p.FluidOuts[slot])) return true;
            return false;
        }

        static int OutSlots(Block b)
        {
            int n = 0;
            foreach (Process p in Of(b)) n = Mathf.Max(n, p.FluidOuts.Length);
            return n;
        }

        static readonly Vector3[] InFaces = { Vector3.back, Vector3.down };
        static readonly Vector3[] OutFaces = { Vector3.up, Vector3.right, Vector3.left };

        static Vector3i Rot(BlockValue bv, Vector3 v)
        {
            return Fluids.Rot(bv, v);
        }

        /// <summary>The fluid ports of a process machine (FluidPort.Fluid of an out port = "out0".."out2" slot via Cell+Dir).</summary>
        public static void FluidPorts(World world, Vector3i pos, BlockValue bv, List<FluidPort> l)
        {
            FluidState s = FluidStore.Get(pos);
            for (int i = 0; i < InFaces.Length; i++)
            {
                List<string> fl = InFluids(bv.Block, i);
                if (fl.Count == 0) continue;
                string held;
                float lv = Level(s, "in" + i, out held);
                FluidPort port = new FluidPort { Owner = pos, Cell = pos, Dir = Rot(bv, InFaces[i]), Out = false, Metal = Fluids.IsMetal(fl[0]) };
                if (lv > 0.01f) port.Fluid = held;
                else if (fl.Count == 1) port.Fluid = fl[0];
                else { port.Fluid = ""; port.Accepts = fl.ToArray(); }
                l.Add(port);
            }
            int outs = OutSlots(bv.Block);
            if (IsTower(bv.Block))
            {
                string f0;
                Level(s, "out0", out f0);
                foreach (Vector3 side in new Vector3[] { Vector3.right, Vector3.left })
                    l.Add(new FluidPort { Owner = pos, Cell = pos, Dir = Rot(bv, side), Out = true, Fluid = f0 });
                return;
            }
            for (int i = 0; i < outs && i < OutFaces.Length; i++)
            {
                string f;
                Level(s, "out" + i, out f);
                l.Add(new FluidPort { Owner = pos, Cell = pos, Dir = Rot(bv, OutFaces[i]), Out = true, Fluid = f, Metal = OutMetal(bv.Block, i) });
            }
        }

        static string SlotOf(FluidPort port, BlockValue bv)
        {
            if (!port.Out)
            {
                for (int i = 0; i < InFaces.Length; i++) if (port.Dir == Rot(bv, InFaces[i])) return "in" + i;
                return "in0";
            }
            if (IsTower(bv.Block)) return "out0";
            for (int i = 0; i < OutFaces.Length; i++) if (port.Dir == Rot(bv, OutFaces[i])) return "out" + i;
            return "out0";
        }

        static BlockValue BV(Vector3i p)
        {
            World w = GameManager.Instance == null ? null : GameManager.Instance.World;
            return w == null ? BlockValue.Air : w.GetBlock(p);
        }

        /// <summary>Fluid demand of an input port this tick.</summary>
        public static float Demand(World world, Vector3i p, BlockValue bv, FluidState s, FluidPort port)
        {
            if (s.Off) return 0f;
            string slot = SlotOf(port, bv);
            string held;
            float lv = Level(s, slot, out held);
            return Mathf.Max(0f, Buffer(bv.Block) - lv);
        }

        /// <summary>Old single-port overload (back port).</summary>
        public static float Demand(World world, Vector3i p, BlockValue bv, FluidState s)
        {
            string f = FluidIn(bv.Block);
            if (f == null) return 0f;
            if (s.Amount > 0.01f && s.Fluid != f) return 0f;
            return Mathf.Max(0f, Buffer(bv.Block) - s.Amount);
        }

        public static float Offer(FluidPort port, FluidState s)
        {
            string held;
            return Level(s, SlotOf(port, BV(port.Owner)), out held);
        }

        public static void Took(FluidPort port, FluidState s, float amount)
        {
            string slot = SlotOf(port, BV(port.Owner));
            string held;
            Level(s, slot, out held);
            AddLevel(s, slot, held, -amount);
        }

        public static void Got(FluidPort port, FluidState s, float amount, string fluid)
        {
            AddLevel(s, SlotOf(port, BV(port.Owner)), fluid, amount);
        }

        /// <summary>Minimum pressure (bar) asked at an input: the most any allowed process asks.</summary>
        public static float MinBar(Block b, FluidState s)
        {
            float m = 0f;
            foreach (Process p in Allowed(b, s)) m = Mathf.Max(m, p.Pressure);
            return m;
        }

        /// <summary>The recipe the player chose with "Choose recipe" (null = automatic).</summary>
        public static Process Picked(Block b, FluidState s)
        {
            if (s == null || string.IsNullOrEmpty(s.Pick)) return null;
            foreach (Process p in Of(b)) if (p.Id == s.Pick) return p;
            return null;
        }

        /// <summary>The processes it may run now: only the chosen one, or all of them (automatic).</summary>
        public static List<Process> Allowed(Block b, FluidState s)
        {
            Process pk = Picked(b, s);
            return pk != null ? new List<Process> { pk } : Of(b);
        }

        static int Need(Block b, FluidState s, string item)
        {
            int n = 0;
            bool inline = IsInline(b);
            foreach (Process p in Allowed(b, s))
                for (int i = inline ? 1 : 0; i < p.Inputs.Length; i++)
                    if (p.Inputs[i] == item) n = Mathf.Max(n, p.Counts[i]);
            return n;
        }

        /// <summary>A belt (or the hand) gives st: how many it takes.</summary>
        public static int Insert(World world, Vector3i p, ItemStack st)
        {
            if (st == null || st.IsEmpty() || st.itemValue.ItemClass == null) return 0;
            Block b = world.GetBlock(p).Block;
            string name = st.itemValue.ItemClass.GetItemName();
            FluidStore.EnsureLoaded();
            FluidState s = FluidStore.Get(p);
            int need = Need(b, s, name);
            if (need <= 0) return 0;
            if (!FluidStore.Devices.Contains(p)) FluidStore.Register(p);
            Dictionary<string, int> d = Stock(s);
            int have;
            d.TryGetValue(name, out have);
            int take = Mathf.Min(st.count, need * StockCrafts - have);
            if (take <= 0) return 0;
            d[name] = have + take;
            SetStock(s, d);
            return take;
        }

        /// <summary>Has it the stock and fluids for pr (skip = inputs taken from elsewhere, e.g. the belt)?</summary>
        public static bool Ready(Block b, Process pr, Dictionary<string, int> d, FluidState s, int skip, out string why)
        {
            why = "";
            for (int i = skip; i < pr.Inputs.Length; i++)
            {
                int have;
                d.TryGetValue(pr.Inputs[i], out have);
                if (have < pr.Counts[i]) { why = "items"; return false; }
            }
            for (int i = 0; i < pr.FluidIns.Length; i++)
            {
                string held;
                float lv = Level(s, "in" + i, out held);
                if (held != pr.FluidIns[i] || lv < pr.LitersIn[i] - 0.01f) { why = "fluid"; return false; }
            }
            for (int i = 0; i < pr.FluidOuts.Length; i++)
            {
                if (IsTower(b) && i > 0) continue;
                string held;
                float lv = Level(s, "out" + i, out held);
                if (lv > 0.01f && held != pr.FluidOuts[i]) { why = "outfluid"; return false; }
                if (lv + pr.LitersOut[i] > Mathf.Max(Buffer(b), pr.LitersOut[i]) * 4f) { why = "full"; return false; }
            }
            int extra = pr.Extra != null ? pr.ExtraCount : 0;
            if (OutTotal(s) + (pr.Output != null ? pr.OutCount : 0) + extra > MaxOut) { why = "full"; return false; }
            return true;
        }

        /// <summary>Speed of the run now (0 = it waits; s.Note says why).</summary>
        public static float Speed(World world, Vector3i p, Process pr, FluidState s)
        {
            Block b = world.GetBlock(p).Block;
            bool electric = Industrial.IsElectric(b);
            if ((pr.Heat || (b.Properties != null && b.Properties.Contains("FeHeat") && b.Properties.GetBool("FeHeat"))) && !electric
                && !FluidControl.HeatFrom(world, p))
            {
                s.Note = "heat";
                return 0f;
            }
            if (pr.Pressure > 0f && s.InBar + 0.001f < pr.Pressure) { s.Note = "pressure"; return 0f; }
            if (electric)
            {
                if (!Industrial.IsPowered(world, p)) { s.Note = "power"; return 0f; }
                return Fluids.Prop(b, "FeProcSpeed", 1f);
            }
            if (pr.Torque <= 0f) return 1f;
            TorqueNet net = Kinetic.Get(world, p);
            if (net == null || !net.Running || !net.Machines.ContainsKey(p)) { s.Note = "torque"; return 0f; }
            return net.MachineSpeed(p);
        }

        /// <summary>The products of one run (items into Out, fluids into the out slots or the tower sections).</summary>
        public static void Produce(World world, Vector3i p, BlockValue bv, Process run, FluidState s, int times)
        {
            Dictionary<string, int> o = Outs(s);
            int have;
            if (run.Output != null)
            {
                o.TryGetValue(run.Output, out have);
                o[run.Output] = have + run.OutCount * times;
            }
            if (run.Extra != null)
            {
                int n = 0;
                for (int k = 0; k < times; k++) if (Random.value <= run.Chance) n += run.ExtraCount;
                if (n > 0)
                {
                    o.TryGetValue(run.Extra, out have);
                    o[run.Extra] = have + n;
                }
            }
            s.Out = Unmap(o);
            for (int i = 0; i < run.FluidOuts.Length; i++)
            {
                float l = run.LitersOut[i] * times;
                if (IsTower(bv.Block) && i > 0) { TowerFill(world, p, i, run.FluidOuts[i], l); continue; }
                AddLevel(s, "out" + i, run.FluidOuts[i], l);
            }
            FluidStore.MarkDirty();
        }

        // fraction k goes to the Tower Section k blocks above (sections must be stacked without gaps)
        static void TowerFill(World world, Vector3i p, int k, string fluid, float litres)
        {
            for (int i = 1; i <= k; i++)
                if (Fluids.Kind(world.GetBlock(new Vector3i(p.x, p.y + i, p.z)).Block) != FluidKind.TowerSection) return;
            Vector3i sp = new Vector3i(p.x, p.y + k, p.z);
            if (!FluidStore.Devices.Contains(sp)) FluidStore.Register(sp);
            FluidState ss = FluidStore.Get(sp);
            if (ss.Amount > 0.01f && ss.Fluid != fluid) return;
            float cap = Fluids.Prop(world.GetBlock(sp).Block, "FeFluidBuffer", 500f);
            ss.Amount = Mathf.Min(cap, ss.Amount + litres);
            ss.Fluid = fluid;
        }

        /// <summary>How many Tower Sections are stacked on this base.</summary>
        public static int TowerSections(World world, Vector3i p)
        {
            int n = 0;
            while (n < 8 && Fluids.Kind(world.GetBlock(new Vector3i(p.x, p.y + n + 1, p.z)).Block) == FluidKind.TowerSection) n++;
            return n;
        }

        /// <summary>Every 0.5 s: run a process, then put the products on the belt in front.</summary>
        public static void Tick(World world, Vector3i p, BlockValue bv, FluidState s, float dt)
        {
            Dictionary<string, int> d = Stock(s);
            if (IsInline(bv.Block)) { Inline.PushOut(world, p, s); return; }
            if (!s.Off)
            {
                Process run = null;
                List<Process> allowed = Allowed(bv.Block, s);
                string why = "", w;
                foreach (Process pr in allowed)
                    if (pr.Id == s.Mold && Ready(bv.Block, pr, d, s, 0, out w)) { run = pr; break; }
                if (run == null)
                    foreach (Process pr in allowed)
                    {
                        if (Ready(bv.Block, pr, d, s, 0, out w)) { run = pr; break; }
                        if (why.Length == 0 || w == "full") why = w;
                    }
                if (run == null)
                {
                    s.Steam = 0f;
                    s.Note = why == "full" ? "full" : "wait";
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
                            for (int i = 0; i < run.FluidIns.Length; i++)
                            {
                                string held;
                                Level(s, "in" + i, out held);
                                AddLevel(s, "in" + i, held, -run.LitersIn[i]);
                            }
                            Produce(world, p, bv, run, s, 1);
                            BeltMachines.Note(world, p, run.Id + " -> " + (run.Output != null ? run.OutCount + "x " + run.Output : "fluids"));
                        }
                    }
                    FluidStore.MarkDirty();
                }
            }
            PushOut(world, p, bv, s);
        }

        /// <summary>Products waiting go to the belt in front.</summary>
        public static void PushOut(World world, Vector3i p, BlockValue bv, FluidState s)
        {
            Dictionary<string, int> o = Outs(s);
            if (o.Count == 0) return;
            Vector3i f = Fluids.Rot(bv, Vector3.forward);
            Vector3i dst = new Vector3i(p.x + f.x, p.y + f.y, p.z + f.z);
            if (!Belt.Accepts(world, dst, f)) return;
            float entry = Belt.EntryP(world, dst, f);
            List<BeltItem> items = BeltStore.Items(dst, false);
            if (!Belt.Room(items, entry)) return;
            if (items != null && entry == 0f)
                foreach (BeltItem it0 in items) if (it0.P < entry + Belt.Gap) return;
            string first = null;
            foreach (string k in o.Keys) { first = k; break; }
            ItemValue iv = ItemClass.GetItem(first, false);
            if (iv == null || iv.IsEmpty()) { o.Remove(first); s.Out = Unmap(o); return; }
            int n = Mathf.Min(o[first], Mathf.Max(1, iv.ItemClass.Stacknumber.Value));
            BeltItem it = BeltStore.Add(dst, new ItemStack(iv, n), entry);
            Belt.ChooseExit(world, dst, world.GetBlock(dst), it);
            o[first] -= n;
            s.Out = Unmap(o);
            FluidStore.MarkDirty();
        }

        public static string ItemName(string item)
        {
            ItemValue iv = ItemClass.GetItem(item, false);
            return iv == null || iv.IsEmpty() || iv.ItemClass == null ? item : iv.ItemClass.GetLocalizedItemName();
        }

        public static string NoteText(string note)
        {
            switch (note)
            {
                case "torque": return Kinetic.Text("feFluidNoTorque", "No torque on its shaft");
                case "power": return Kinetic.Text("feFluidNoPower", "No power: wire it to a power source");
                case "full": return Kinetic.Text("feCasterFull", "Full: take the casts or put a belt in front");
                case "heat": return Kinetic.Text("feProcNoHeat", "No heat: put a lit Gas Burner against it");
                case "pressure": return Kinetic.Text("feProcNoPressure", "Pressure too low at its gas input (use a Compressor)");
            }
            return "";
        }

        public static string Describe(World world, Vector3i p, BlockValue bv, FluidState s)
        {
            StringBuilder sb = new StringBuilder();
            List<Process> ps = Of(bv.Block);
            if (ps.Count == 0) return Kinetic.Text("feProcNone", "No processes for this machine");
            Process pk = Picked(bv.Block, s);
            sb.Append(pk == null ? Kinetic.Text("feProcAutoShort", "Recipe: automatic") : string.Format(Kinetic.Text("feProcPicked", "Recipe: {0}"), Label(pk)));
            foreach (Process pr in ps)
                if (pr.Id == s.Mold && s.Steam > 0f)
                    sb.Append("  ").Append(Mathf.RoundToInt(100f * s.Steam / Mathf.Max(0.1f, pr.Time))).Append('%');
            if (s.Off) sb.Append("\n").Append(Kinetic.Text("feProcOff", "Switched off"));
            string n = NoteText(s.Note);
            if (n.Length > 0) sb.Append("\n").Append(n);
            sb.Append("\n").Append(Kinetic.Text("feProcPanelHint", "E: panel"));
            return sb.ToString();
        }

        /// <summary>Full readout for the Machine Panel.</summary>
        public static string Panel(World world, Vector3i p, BlockValue bv, FluidState s)
        {
            StringBuilder sb = new StringBuilder();
            List<Process> ps = Of(bv.Block);
            Process pk = Picked(bv.Block, s);
            sb.Append("[e0a030]").Append(pk == null ? Kinetic.Text("feProcAuto", "Recipe: automatic (the first one it has everything for)")
                                                       : string.Format(Kinetic.Text("feProcPicked", "Recipe: {0}"), Label(pk))).Append("[-]\n");
            Process cur = null;
            foreach (Process pr in ps) if (pr.Id == s.Mold) cur = pr;
            float frac = cur == null ? 0f : Mathf.Clamp01(s.Steam / Mathf.Max(0.1f, cur.Time));
            sb.Append(Bar(frac, 30)).Append("  ").Append(Mathf.RoundToInt(frac * 100f)).Append("%");
            if (cur != null) sb.Append("   ").Append(Label(cur));
            sb.Append("\n\n");
            Dictionary<string, int> d = Stock(s);
            List<string> st = new List<string>();
            foreach (KeyValuePair<string, int> kv in d) st.Add(kv.Value + "x " + ItemName(kv.Key));
            sb.Append(string.Format(Kinetic.Text("feProcStock", "Inside: {0}"), st.Count == 0 ? "-" : string.Join(", ", st.ToArray()))).Append("\n");
            List<string> ou = new List<string>();
            foreach (KeyValuePair<string, int> kv in Outs(s)) ou.Add(kv.Value + "x " + ItemName(kv.Key));
            sb.Append(string.Format(Kinetic.Text("feProcOutList", "Ready: {0}"), ou.Count == 0 ? "-" : string.Join(", ", ou.ToArray()))).Append("\n");
            float buf = Buffer(bv.Block);
            for (int i = 0; i < InFaces.Length; i++)
            {
                if (InFluids(bv.Block, i).Count == 0) continue;
                string f;
                float lv = Level(s, "in" + i, out f);
                sb.Append(i == 0 ? Kinetic.Text("fePanelInBack", "In (back)") : Kinetic.Text("fePanelInBottom", "In (bottom)")).Append(": ")
                  .Append(Bar(lv / Mathf.Max(1f, buf), 16)).Append(' ').Append(Mathf.RoundToInt(lv)).Append(" L ")
                  .Append(f.Length > 0 ? Fluids.FluidName(f) : string.Join("/", NamesOf(InFluids(bv.Block, i))));
                if (Fluids.IsGas(f)) sb.Append("  ").Append(s.InBar.ToString("0.0", CultureInfo.InvariantCulture)).Append(" bar");
                sb.Append("\n");
            }
            string[] outName = IsTower(bv.Block)
                ? new string[] { Kinetic.Text("fePanelOutSides", "Out (sides)") }
                : new string[] { Kinetic.Text("fePanelOutTop", "Out (top)"), Kinetic.Text("fePanelOutRight", "Out (right)"), Kinetic.Text("fePanelOutLeft", "Out (left)") };
            for (int i = 0; i < OutSlots(bv.Block) && i < outName.Length; i++)
            {
                string f;
                float lv = Level(s, "out" + i, out f);
                sb.Append(outName[i]).Append(": ").Append(Bar(lv / Mathf.Max(1f, buf * 4f), 16)).Append(' ').Append(Mathf.RoundToInt(lv))
                  .Append(" L ").Append(f.Length > 0 ? Fluids.FluidName(f) : "-").Append("\n");
            }
            if (IsTower(bv.Block))
                sb.Append(string.Format(Kinetic.Text("fePanelSections", "Tower sections stacked: {0}"), TowerSections(world, p))).Append("\n");
            sb.Append(Kinetic.Text("fePanelItemsOut", "Items out: the belt in front")).Append("\n");
            if (s.Off) sb.Append("[ff6060]").Append(Kinetic.Text("feProcOff", "Switched off")).Append("[-]\n");
            string n = NoteText(s.Note);
            if (n.Length > 0) sb.Append("[ff6060]").Append(n).Append("[-]\n");
            return sb.ToString();
        }

        static List<string> NamesOf(List<string> fl)
        {
            List<string> r = new List<string>();
            foreach (string f in fl) r.Add(Fluids.FluidName(f));
            return r;
        }

        public static string Bar(float frac, int width)
        {
            int n = Mathf.Clamp(Mathf.RoundToInt(Mathf.Clamp01(frac) * width), 0, width);
            return "[60d060]" + new string('|', n) + "[-][404040]" + new string('|', width - n) + "[-]";
        }

        /// <summary>"1x Nitre Earth (10x Rotting Flesh + 4x Bone + 20 L Water)".</summary>
        public static string Label(Process pr)
        {
            List<string> ins = new List<string>();
            for (int i = 0; i < pr.Inputs.Length; i++) ins.Add(pr.Counts[i] + "x " + ItemName(pr.Inputs[i]));
            for (int i = 0; i < pr.FluidIns.Length; i++) ins.Add(Mathf.RoundToInt(pr.LitersIn[i]) + " L " + Fluids.FluidName(pr.FluidIns[i]));
            List<string> outs = new List<string>();
            if (pr.Output != null) outs.Add(pr.OutCount + "x " + ItemName(pr.Output));
            for (int i = 0; i < pr.FluidOuts.Length; i++) outs.Add(Mathf.RoundToInt(pr.LitersOut[i]) + " L " + Fluids.FluidName(pr.FluidOuts[i]));
            if (pr.Extra != null) outs.Add((pr.Chance < 1f ? Mathf.RoundToInt(pr.Chance * 100f) + "% " : "") + pr.ExtraCount + "x " + ItemName(pr.Extra));
            return string.Join(" + ", outs.ToArray()) + " (" + string.Join(" + ", ins.ToArray()) + ")";
        }

        public const string PickCommand = "fe_proc_pick";
        public const string PanelCommand = "fe_panel";

        /// <summary>Choose recipe: automatic -> 1st -> 2nd -> ... -> automatic.</summary>
        static string Cycle(Block b, FluidState s)
        {
            List<Process> ps = Of(b);
            int i = -1;
            for (int k = 0; k < ps.Count; k++) if (ps[k].Id == s.Pick) i = k;
            i++;
            return Choose(b, s, i < ps.Count ? ps[i].Id : "");
        }

        /// <summary>Set the chosen recipe ("" = automatic).</summary>
        public static string Choose(Block b, FluidState s, string id)
        {
            s.Pick = id ?? "";
            s.Steam = 0f;
            FluidStore.MarkDirty();
            Process pk = Picked(b, s);
            return pk == null ? Kinetic.Text("feProcAuto", "Recipe: automatic (the first one it has everything for)")
                              : string.Format(Kinetic.Text("feProcPicked", "Recipe: {0}"), Label(pk));
        }

        /// <summary>Everything waiting goes to the player.</summary>
        public static string TakeAll(World world, Vector3i p, EntityPlayerLocal player)
        {
            FluidState s = FluidStore.Get(p);
            Dictionary<string, int> o = Outs(s);
            if (o.Count == 0) return Kinetic.Text("feProcNothing", "Nothing made yet");
            List<string> got = new List<string>();
            foreach (KeyValuePair<string, int> kv in o)
            {
                ItemValue iv = ItemClass.GetItem(kv.Key, false);
                if (iv == null || iv.IsEmpty()) continue;
                ItemStack st = new ItemStack(iv, kv.Value);
                if (!player.bag.AddItem(st)) GameManager.Instance.ItemDropServer(st, player.GetPosition(), Vector3.zero, -1, 60f, false);
                got.Add(kv.Value + "x " + iv.ItemClass.GetLocalizedItemName());
            }
            s.Out = "";
            FluidStore.MarkDirty();
            return string.Format(Kinetic.Text("feTookList", "Took: {0}"), string.Join(", ", got.ToArray()));
        }

        /// <summary>The item in hand goes in.</summary>
        public static string PutHeld(World world, Vector3i p, EntityPlayerLocal player)
        {
            ItemStack held = player.inventory.holdingItemStack;
            if (held == null || held.IsEmpty()) return Kinetic.Text("feProcHold", "Hold an ingredient of this machine");
            int took = Insert(world, p, held);
            if (took <= 0) return Kinetic.Text("fePourNo", "It does not take this (or it is full)");
            ItemStack left = held.Clone();
            left.count -= took;
            player.inventory.SetItem(player.inventory.holdingItemIdx, left.count > 0 ? left : ItemStack.Empty.Clone());
            return string.Format(Kinetic.Text("feProcPut", "Put in {0}"), took);
        }

        public static string Activate(World world, Vector3i p, string cmd, EntityPlayerLocal player)
        {
            FluidStore.EnsureLoaded();
            if (!FluidStore.Devices.Contains(p)) FluidStore.Register(p);
            FluidState s = FluidStore.Get(p);
            if (cmd == PanelCommand) { FeUi.OpenMachine(player, p); return null; }
            if (cmd == PickCommand) { FeUi.OpenPicker(player, p); return null; }
            if (cmd == "fe_cast_take") return TakeAll(world, p, player);
            return PutHeld(world, p, player);
        }

        /// <summary>The radial of a process machine: panel first (tap E), then put / recipe / take.</summary>
        public static BlockActivationCommand[] Commands(BlockActivationCommand? take)
        {
            List<BlockActivationCommand> l = new List<BlockActivationCommand>
            {
                new BlockActivationCommand(PanelCommand, "search", true, false, null),
                new BlockActivationCommand("fe_put", "loot_sort", true, false, null),
                new BlockActivationCommand(PickCommand, "tool", true, false, null),
                new BlockActivationCommand("fe_cast_take", "hand", true, false, null)
            };
            if (take.HasValue) l.Add(take.Value);
            return l.ToArray();
        }

        public static bool IsCommand(string cmd)
        {
            return cmd == "fe_put" || cmd == "fe_cast_take" || cmd == PickCommand || cmd == PanelCommand;
        }
    }
}
