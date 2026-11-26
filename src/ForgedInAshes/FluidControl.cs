// D12 (PLANO_CADEIA.md 4.1): control blocks of the fluid network, and the new fluid devices.
//
//   Valves (FeFluid=valve, FeValve=...): fluid comes in at the BACK, waits in a small buffer (FeFluidBuffer L) and goes
//   out at the FRONT, so each valve splits two networks:
//     registro    Shut-off valve: open / closed / by signal (open while a signal reaches it: a powered wire, a lever, a
//                 gauge or a counter next to it - Signals.cs)
//     retencao    Check valve: one way only (that is what the back-to-front buffer is)
//     reguladora  Regulator: liquids at most N L/min; gases at most N bar on its outlet
//     separador   Separator: lets only one fluid through (its setting; "" = the first one that comes)
//     alivio      Relief valve (back port only): above N bar it vents what comes in
//     compressor  Compressor (a torque machine): pushes the gas out at N bar (up to 10), FeFluidRate L/min at 32 RPM
//   Gauge (FeFluid=gauge): reads the network on its back port (fluid, bar, litres in the tanks, flow) and gives a
//     signal when the pressure (gases) or the fill of the tanks (liquids, %) reaches its setting.
//   Gas Burner (FeFluid=burner): burns fuel gas from its back port, or fuel items put in by hand / belt, and heats every
//     machine touching it that asks heat (ProcessMachine.Speed -> HeatFrom). Burns only while one asks.
//   Sap Tapper (FeFluid=tapper): its back against a living tree trunk, gives latex at its front (FeLatexRate of the tree:
//     the Rubber Tree a lot, oak and maple little).
//   Tanks (Tank, GasTank) of the same block touching each other share what they hold (EqualizeTanks): a 3x3x6 of
//   Liquid Tanks is one big tank.
//
// C# 5 only.

using System.Collections.Generic;
using System.Globalization;
using System.Text;
using UnityEngine;

namespace ForgedInAshes
{
    public static class FluidControl
    {
        public const string Latex = "latex";
        public static readonly string[] BurnerFuels = { "fuel_gas", "shale_gas" };
        static readonly string[] Any = { "*" };

        static readonly Vector3i[] Dirs =
        {
            new Vector3i(1, 0, 0), new Vector3i(-1, 0, 0), new Vector3i(0, 1, 0),
            new Vector3i(0, -1, 0), new Vector3i(0, 0, 1), new Vector3i(0, 0, -1)
        };

        public static string ValveType(Block b)
        {
            return b != null && b.Properties != null && b.Properties.Contains("FeValve")
                ? b.Properties.GetString("FeValve").Trim().ToLowerInvariant() : "retencao";
        }

        public static float Setting(FluidState s, float def)
        {
            float v;
            return float.TryParse(s.Pick, NumberStyles.Float, CultureInfo.InvariantCulture, out v) ? v : def;
        }

        public static float DefaultSetting(string type)
        {
            switch (type)
            {
                case "reguladora": return 60f;
                case "alivio": return 8f;
                case "compressor": return 6f;
                case "gauge": return 5f;
            }
            return 0f;
        }

        // ------------------------------------------------------------ valves
        public static void Ports(World world, Vector3i pos, BlockValue bv, List<FluidPort> l)
        {
            FluidState s = FluidStore.Get(pos);
            string t = ValveType(bv.Block);
            string holds = s.Amount > 0.01f ? s.Fluid : "";
            FluidPort inp = new FluidPort { Owner = pos, Cell = pos, Dir = Fluids.Rot(bv, Vector3.back), Out = false, Fluid = holds };
            if (holds.Length == 0)
            {
                if (t == "separador" && s.Pick.Length > 0) inp.Fluid = s.Pick;
                else inp.Accepts = Any;
            }
            l.Add(inp);
            if (t != "alivio")
                l.Add(new FluidPort { Owner = pos, Cell = pos, Dir = Fluids.Rot(bv, Vector3.forward), Out = true, Fluid = holds });
        }

        public static bool Open(World world, Vector3i p, BlockValue bv, FluidState s)
        {
            if (s.Off) return false;
            if (ValveType(bv.Block) != "registro") return true;
            if (s.Pick == "closed") return false;
            if (s.Pick == "signal") return Signals.Active(world, p);
            return true;
        }

        static float CompressorSpeed(World world, Vector3i p, FluidState s)
        {
            TorqueNet net = Kinetic.Get(world, p);
            if (net == null || !net.Running || !net.Machines.ContainsKey(p)) { s.Note = "torque"; return 0f; }
            s.Note = "";
            return net.MachineSpeed(p);
        }

        public static float ValveDemand(World world, Vector3i p, BlockValue bv, FluidState s, float dt)
        {
            if (!Open(world, p, bv, s)) return 0f;
            string t = ValveType(bv.Block);
            float buf = Fluids.Prop(bv.Block, "FeFluidBuffer", 40f);
            float room = Mathf.Max(0f, buf - s.Amount);
            if (t == "alivio") return s.InBar > Setting(s, DefaultSetting(t)) ? 400f : 0f;
            if (t == "reguladora" && !Fluids.IsGas(s.Fluid))
            {
                // D13: an analog signal next to it opens it that much (15 = its full setting)
                int lv = Signals.LevelAt(world, p);
                float k = lv > 0 ? lv / 15f : 1f;
                return Mathf.Min(room, Setting(s, DefaultSetting(t)) * k * dt / 60f);
            }
            if (t == "compressor") return Mathf.Min(room, Fluids.Prop(bv.Block, "FeFluidRate", 300f) * CompressorSpeed(world, p, s) * dt / 60f);
            return room;
        }

        public static float ValveOffer(World world, Vector3i p, BlockValue bv, FluidState s, float dt)
        {
            string t = ValveType(bv.Block);
            if (!Open(world, p, bv, s)) { s.OutBar = 0f; return 0f; }
            if (t == "compressor") s.OutBar = CompressorSpeed(world, p, s) > 0f ? Mathf.Clamp(Setting(s, DefaultSetting(t)), 1f, Fluids.Prop(bv.Block, "FeMaxBar", 10f)) : 0f;
            else if (t == "reguladora" && Fluids.IsGas(s.Fluid)) s.OutBar = Mathf.Min(s.InBar, Setting(s, DefaultSetting(t)));
            else s.OutBar = s.InBar;
            return s.Amount;
        }

        public static void ValveGot(World world, Vector3i p, BlockValue bv, FluidState s)
        {
            if (ValveType(bv.Block) == "alivio" && s.Amount > 0f)
            {
                s.LastFlow = s.Amount * 120f;
                s.Amount = 0f;
                s.Fluid = "";
                s.Note = "vent";
            }
        }

        /// <summary>Minimum pressure a demand port asks (gases).</summary>
        public static float MinBar(World world, FluidPort d)
        {
            BlockValue bv = world.GetBlock(d.Owner);
            FluidKind k = Fluids.Kind(bv.Block);
            if (k == FluidKind.Processor) return ProcessMachine.MinBar(bv.Block, FluidStore.Get(d.Owner));
            return 0f;
        }

        // ------------------------------------------------------------ gauge
        public static void GaugeTick(World world, Vector3i p, BlockValue bv, FluidState s)
        {
            bool gas = Fluids.IsGas(s.Fluid);
            float thr = Setting(s, gas ? 5f : 90f);
            bool was = s.Sig;
            if (gas) s.Sig = s.Bar >= thr;
            else s.Sig = s.Steam > 0f && s.Amount / s.Steam * 100f >= thr;
            if (was != s.Sig) Signals.Changed(world, p);
        }

        // ------------------------------------------------------------ burner
        static readonly string[,] FuelItems =
        {
            { "resourceCoal", "40" }, { "feResourceCharcoal", "40" }, { "resourceWood", "8" }, { "feBiofuel", "60" },
            { "resourceOilShale", "20" }, { "feCoalDust", "15" }, { "ammoGasCan", "6" },
        };

        public static float FuelSeconds(string item)
        {
            for (int i = 0; i < FuelItems.GetLength(0); i++)
                if (FuelItems[i, 0] == item) return float.Parse(FuelItems[i, 1], CultureInfo.InvariantCulture);
            return 0f;
        }

        static float MaxHeat(Block b)
        {
            return Fluids.Prop(b, "FeHeatMax", 240f);
        }

        public static float BurnerDemand(BlockValue bv, FluidState s, float dt)
        {
            if (s.Off || s.HeatAsk <= 0f || s.Steam >= MaxHeat(bv.Block) - 5f) return 0f;
            return Fluids.Prop(bv.Block, "FeFluidRate", 30f) * dt / 60f * 2f;
        }

        public static void BurnerGot(BlockValue bv, FluidState s, float litres)
        {
            s.Steam = Mathf.Min(MaxHeat(bv.Block), s.Steam + litres * Fluids.Prop(bv.Block, "FeHeatPerLitre", 2f));
        }

        public static void BurnerTick(World world, Vector3i p, BlockValue bv, FluidState s, float dt)
        {
            if (s.HeatAsk > 0f && s.Steam > 0f && !s.Off)
            {
                s.Steam = Mathf.Max(0f, s.Steam - dt);
                s.Note = "burning";
            }
            else s.Note = s.Steam > 0f ? "" : "nofuel";
            s.HeatAsk = Mathf.Max(0f, s.HeatAsk - dt);
        }

        /// <summary>Fuel items into a burner (belt / arm / hand): how many it took.</summary>
        public static int BurnerInsert(World world, Vector3i p, ItemStack st)
        {
            if (st == null || st.IsEmpty() || st.itemValue.ItemClass == null) return 0;
            float per = FuelSeconds(st.itemValue.ItemClass.GetItemName());
            if (per <= 0f) return 0;
            FluidStore.EnsureLoaded();
            if (!FluidStore.Devices.Contains(p)) FluidStore.Register(p);
            FluidState s = FluidStore.Get(p);
            float max = MaxHeat(world.GetBlock(p).Block);
            int n = Mathf.Min(st.count, Mathf.FloorToInt((max - s.Steam) / per));
            if (n <= 0) return 0;
            s.Steam += n * per;
            FluidStore.MarkDirty();
            return n;
        }

        public static string BurnerPutHeld(World world, Vector3i p, EntityPlayerLocal player)
        {
            ItemStack held = player.inventory.holdingItemStack;
            if (held == null || held.IsEmpty()) return Kinetic.Text("feBurnerHold", "Hold coal, charcoal, wood, biofuel or shale");
            int n = BurnerInsert(world, p, held);
            if (n <= 0) return Kinetic.Text("fePourNo", "It does not take this (or it is full)");
            ItemStack left = held.Clone();
            left.count -= n;
            player.inventory.SetItem(player.inventory.holdingItemIdx, left.count > 0 ? left : ItemStack.Empty.Clone());
            return string.Format(Kinetic.Text("feProcPut", "Put in {0}"), n);
        }

        /// <summary>Is a lit burner touching the machine at p? Asks every burner touching it for heat.</summary>
        public static bool HeatFrom(World world, Vector3i p)
        {
            bool hot = false;
            foreach (Vector3i d in Dirs)
            {
                Vector3i c = new Vector3i(p.x + d.x, p.y + d.y, p.z + d.z);
                BlockValue bv = world.GetBlock(c);
                if (Fluids.Kind(bv.Block) != FluidKind.Burner) continue;
                Vector3i par = Fluids.ParentOf(world, c, bv);
                if (!FluidStore.Devices.Contains(par)) FluidStore.Register(par);
                FluidState bs = FluidStore.Get(par);
                bs.HeatAsk = 1.5f;
                if (bs.Steam > 0f && !bs.Off) hot = true;
            }
            return hot;
        }

        // ------------------------------------------------------------ sap tapper
        public static float TreeRate(Block b)
        {
            if (b == null) return 0f;
            if (b.Properties != null && b.Properties.Contains("FeLatexRate")) return b.Properties.GetFloat("FeLatexRate");
            string n = b.GetBlockName();
            if (!n.StartsWith("tree", System.StringComparison.Ordinal)) return 0f;
            if (n.Contains("Burnt") || n.Contains("Dead") || n.Contains("Stump") || n.Contains("Grass") || n.Contains("Cactus")) return 0f;
            if (n.Contains("Oak") || n.Contains("Maple") || n.Contains("PlainsTree")) return 0.3f;
            return 0f;
        }

        public static void TapperProduce(World world, Vector3i p, BlockValue bv, FluidState s, float dt)
        {
            Vector3i b = Fluids.Rot(bv, Vector3.back);
            float rate = TreeRate(world.GetBlock(new Vector3i(p.x + b.x, p.y + b.y, p.z + b.z)).Block);
            if (rate <= 0f) { s.Note = "notree"; return; }
            s.Note = "";
            float cap = Fluids.Prop(bv.Block, "FeFluidBuffer", 50f);
            if (s.Amount > 0.01f && s.Fluid != Latex) return;
            s.Amount = Mathf.Min(cap, s.Amount + rate * Fluids.Prop(bv.Block, "FeTapFactor", 1f) * dt / 60f);
            s.Fluid = Latex;
        }

        // ------------------------------------------------------------ joined tanks
        public static void EqualizeTanks(World world)
        {
            HashSet<Vector3i> seen = new HashSet<Vector3i>();
            List<Vector3i> devs = new List<Vector3i>(FluidStore.Devices);
            foreach (Vector3i start in devs)
            {
                if (seen.Contains(start) || world.GetChunkFromWorldPos(start) == null) continue;
                Block sb = world.GetBlock(start).Block;
                FluidKind k = Fluids.Kind(sb);
                if (k != FluidKind.Tank && k != FluidKind.GasTank) continue;
                List<Vector3i> cluster = new List<Vector3i>();
                Queue<Vector3i> q = new Queue<Vector3i>();
                q.Enqueue(start);
                seen.Add(start);
                while (q.Count > 0 && cluster.Count < 128)
                {
                    Vector3i c = q.Dequeue();
                    cluster.Add(c);
                    foreach (Vector3i d in Dirs)
                    {
                        Vector3i n = new Vector3i(c.x + d.x, c.y + d.y, c.z + d.z);
                        if (seen.Contains(n)) continue;
                        if (world.GetBlock(n).Block != sb) continue;
                        seen.Add(n);
                        if (!FluidStore.Devices.Contains(n)) FluidStore.Register(n);
                        q.Enqueue(n);
                    }
                }
                if (cluster.Count < 2) continue;
                string fluid = "";
                float total = 0f, cap = 0f;
                bool mixed = false;
                foreach (Vector3i c in cluster)
                {
                    FluidState ts = FluidStore.Get(c);
                    cap += Fluids.Prop(sb, "FeFluidCapacity", 4000f);
                    if (ts.Amount <= 0.01f) continue;
                    if (fluid.Length == 0) fluid = ts.Fluid;
                    else if (ts.Fluid != fluid) mixed = true;
                    total += ts.Amount;
                }
                if (mixed || cap <= 0f) continue;
                foreach (Vector3i c in cluster)
                {
                    FluidState ts = FluidStore.Get(c);
                    ts.Amount = total * Fluids.Prop(sb, "FeFluidCapacity", 4000f) / cap;
                    ts.Fluid = ts.Amount > 0.01f ? fluid : "";
                }
            }
        }

        /// <summary>Litres and capacity of the joined tank this block belongs to.</summary>
        public static void TankTotal(World world, Vector3i start, out float amount, out float cap, out int blocks)
        {
            amount = 0f;
            cap = 0f;
            blocks = 0;
            Block sb = world.GetBlock(start).Block;
            HashSet<Vector3i> seen = new HashSet<Vector3i> { start };
            Queue<Vector3i> q = new Queue<Vector3i>();
            q.Enqueue(start);
            while (q.Count > 0 && blocks < 128)
            {
                Vector3i c = q.Dequeue();
                blocks++;
                amount += FluidStore.Get(c).Amount;
                cap += Fluids.Prop(sb, "FeFluidCapacity", 4000f);
                foreach (Vector3i d in Dirs)
                {
                    Vector3i n = new Vector3i(c.x + d.x, c.y + d.y, c.z + d.z);
                    if (seen.Contains(n) || world.GetBlock(n).Block != sb) continue;
                    seen.Add(n);
                    q.Enqueue(n);
                }
            }
        }

        // ------------------------------------------------------------ readouts
        static string Bar1(float v)
        {
            return v.ToString("0.0", CultureInfo.InvariantCulture);
        }

        public static string SettingText(Block b, FluidState s)
        {
            FluidKind k = Fluids.Kind(b);
            if (k == FluidKind.Gauge)
            {
                bool gas = Fluids.IsGas(s.Fluid);
                return string.Format(Kinetic.Text("feGaugeSet", "Signal at: {0}"), gas ? Bar1(Setting(s, 5f)) + " bar" : Mathf.RoundToInt(Setting(s, 90f)) + "%");
            }
            string t = ValveType(b);
            switch (t)
            {
                case "registro":
                    return s.Pick == "closed" ? Kinetic.Text("feValveClosed", "Closed")
                         : s.Pick == "signal" ? Kinetic.Text("feValveSignal", "By signal (open while it gets a signal)")
                         : Kinetic.Text("feValveOpen", "Open");
                case "reguladora":
                    return string.Format(Kinetic.Text("feValveLimit", "Limit: {0} L/min (liquids) or {0} bar (gases)"), Mathf.RoundToInt(Setting(s, 60f)));
                case "separador":
                    return string.Format(Kinetic.Text("feValveOnly", "Lets through: {0}"),
                        s.Pick.Length > 0 ? Fluids.FluidName(s.Pick) : Kinetic.Text("feValveAnyFirst", "the first fluid that comes"));
                case "alivio":
                    return string.Format(Kinetic.Text("feValveVent", "Vents above {0} bar"), Bar1(Setting(s, 8f)));
                case "compressor":
                    return string.Format(Kinetic.Text("feValveCompress", "Pushes out at {0} bar"), Bar1(Setting(s, 6f)));
            }
            return Kinetic.Text("feValveCheck", "One way: from its back to its front");
        }

        public static string Describe(World world, Vector3i p, BlockValue bv, FluidState s)
        {
            FluidKind k = Fluids.Kind(bv.Block);
            StringBuilder sb = new StringBuilder();
            switch (k)
            {
                case FluidKind.Valve:
                    sb.Append(SettingText(bv.Block, s));
                    sb.Append("\n").Append(string.Format(Kinetic.Text("feValveFlow", "{0}: {1} L/min, in {2} bar, out {3} bar"),
                        Fluids.FluidName(s.Fluid), Mathf.RoundToInt(s.LastFlow), Bar1(s.InBar), Bar1(s.OutBar)));
                    if (!Open(world, p, bv, s)) sb.Append("\n").Append(Kinetic.Text("feValveIsShut", "Shut: nothing passes"));
                    if (s.Note == "torque") sb.Append("\n").Append(Kinetic.Text("feFluidNoTorque", "No torque on its shaft"));
                    break;
                case FluidKind.Gauge:
                    if (Fluids.IsGas(s.Fluid))
                        sb.Append(string.Format(Kinetic.Text("feGaugeGas", "{0}: {1} bar, {2} L/min"), Fluids.FluidName(s.Fluid), Bar1(s.Bar), Mathf.RoundToInt(s.LastFlow)));
                    else
                        sb.Append(string.Format(Kinetic.Text("feGaugeLiquid", "{0}: tanks {1} / {2} L, {3} L/min"), Fluids.FluidName(s.Fluid),
                            Mathf.RoundToInt(s.Amount), Mathf.RoundToInt(s.Steam), Mathf.RoundToInt(s.LastFlow)));
                    sb.Append("\n").Append(SettingText(bv.Block, s)).Append(" - ").Append(s.Sig ? Kinetic.Text("feSignalOn", "SIGNAL ON") : Kinetic.Text("feSignalOff", "no signal"));
                    if (s.Note == "leak") sb.Append("\n").Append(Kinetic.Text("fePipeLeak", "LEAKING: the pressure is above what the pipes stand (use High Pressure Pipes)"));
                    break;
                case FluidKind.Burner:
                    sb.Append(string.Format(Kinetic.Text("feBurnerHeat", "Heat stored: {0} s"), Mathf.RoundToInt(s.Steam)));
                    sb.Append("\n").Append(s.Note == "burning" ? Kinetic.Text("feBurnerOn", "Burning: heating the machines it touches")
                        : s.Steam > 0f ? Kinetic.Text("feBurnerIdle", "Lit, waiting for a machine that asks heat")
                        : Kinetic.Text("feBurnerNoFuel", "No fuel: fuel gas by pipe at its back, or coal / charcoal / wood / biofuel"));
                    break;
                case FluidKind.Tapper:
                    sb.Append(string.Format(Kinetic.Text("feTapperInfo", "Latex: {0} / {1} L"), Mathf.RoundToInt(s.Amount), Mathf.RoundToInt(Fluids.Prop(bv.Block, "FeFluidBuffer", 50f))));
                    if (s.Note == "notree") sb.Append("\n").Append(Kinetic.Text("feTapperNoTree", "Its back must touch a living trunk (Rubber Tree: a lot; oak / maple: little)"));
                    break;
                case FluidKind.TowerSection:
                    sb.Append(string.Format(Kinetic.Text("feFluidStored", "{0}: {1} / {2} L"), Fluids.FluidName(s.Fluid), Mathf.RoundToInt(s.Amount),
                        Mathf.RoundToInt(Fluids.Prop(bv.Block, "FeFluidBuffer", 500f))));
                    sb.Append("\n").Append(Kinetic.Text("feTowerSectionInfo", "Stack it on a Distillation Tower base: each section gives one fraction on its sides"));
                    break;
            }
            return sb.ToString();
        }
    }
}
