// Thermal power plant (user 2026-11-25): "the user builds an engine the way and size he wants, a thermal power
// plant that gives torque and electricity". The Steam Engine stays the simple stopgap engine; this is the big one.
//
//   Boiler Firebox (FeFluid=burner, a bigger Gas Burner): burns fuel items or fuel gas; heats what touches it.
//   Boiler Drum (FeFluid=boiler): water in by pipe on its 4 sides, steam out at the top (FeOutBar bar). Every lit
//     firebox touching the drum boils FeSteamPerHeat L/min, up to FeSteamMax per drum. Drums touching each other are
//     ONE boiler (water and steam are shared, like the joined tanks), so a plant grows by adding drums and fireboxes.
//   Steam Turbine (FeFluid=turbine + a torque source, FeSteamTurbine): steam in at its back (at least FeMinBar), used
//     steam out at its front (to a Condenser, closing the water loop). It offers FeTorqueOutput UT while its steam
//     buffer is full (less as it empties) and uses FeSteamRate L/min x the load of its shaft. Many turbines on one
//     shaft add up. Electricity: Dynamos on the same shaft (Dynamo.cs) turn torque into power.
//
// State: drum Amount = water, Steam = steam; turbine Amount = steam in, Steam = used steam out, Bar = steam L/min used.
// C# 5 only.

using System.Collections.Generic;
using UnityEngine;

namespace FerroEngrenagem
{
    public static class SteamPlant
    {
        static readonly Vector3i[] Dirs =
        {
            new Vector3i(1, 0, 0), new Vector3i(-1, 0, 0), new Vector3i(0, 1, 0),
            new Vector3i(0, -1, 0), new Vector3i(0, 0, 1), new Vector3i(0, 0, -1)
        };

        public static bool IsTurbine(Block b)
        {
            return b != null && b.Properties != null && b.Properties.Contains("FeSteamTurbine") && b.Properties.GetBool("FeSteamTurbine");
        }

        // ------------------------------------------------------------ ports
        public static void BoilerPorts(Vector3i pos, List<FluidPort> l)
        {
            FluidState s = FluidStore.Get(pos);
            foreach (Vector3i d in Dirs)
            {
                if (d.y < 0) continue;   // the bottom touches the firebox
                if (d.y > 0) l.Add(new FluidPort { Owner = pos, Cell = pos, Dir = d, Out = true, Fluid = Fluids.Steam });
                else l.Add(new FluidPort { Owner = pos, Cell = pos, Dir = d, Out = false, Fluid = Fluids.Water });
            }
        }

        public static void TurbinePorts(Vector3i pos, BlockValue bv, List<FluidPort> l)
        {
            l.Add(new FluidPort { Owner = pos, Cell = pos, Dir = Fluids.Rot(bv, Vector3.back), Out = false, Fluid = Fluids.Steam });
            l.Add(new FluidPort { Owner = pos, Cell = pos, Dir = Fluids.Rot(bv, Vector3.forward), Out = true, Fluid = Fluids.Steam });
        }

        // ------------------------------------------------------------ boiler
        static int LitFireboxes(World world, Vector3i p)
        {
            int n = 0;
            foreach (Vector3i d in Dirs)
            {
                Vector3i c = new Vector3i(p.x + d.x, p.y + d.y, p.z + d.z);
                BlockValue bv = world.GetBlock(c);
                if (Fluids.Kind(bv.Block) != FluidKind.Burner) continue;
                Vector3i par = Fluids.ParentOf(world, c, bv);
                if (!FluidStore.Devices.Contains(par)) FluidStore.Register(par);
                FluidState bs = FluidStore.Get(par);
                bs.HeatAsk = 1.5f;   // the firebox burns while a drum asks heat
                if (bs.Steam > 0f && !bs.Off) n++;
            }
            return n;
        }

        public static float BoilerDemand(BlockValue bv, FluidState s)
        {
            return Mathf.Max(0f, Fluids.Prop(bv.Block, "FeFluidBuffer", 1000f) - s.Amount);
        }

        public static void BoilerTick(World world, Vector3i p, BlockValue bv, FluidState s, float dt)
        {
            int fires = LitFireboxes(world, p);
            float rate = Mathf.Min(fires * Fluids.Prop(bv.Block, "FeSteamPerHeat", 90f), Fluids.Prop(bv.Block, "FeSteamMax", 180f));
            float room = Fluids.Prop(bv.Block, "FeSteamBuffer", 600f) - s.Steam;
            float boil = Mathf.Min(Mathf.Min(s.Amount, rate * dt / 60f), Mathf.Max(0f, room));
            s.Amount -= boil;
            s.Steam += boil;
            s.Fluid = s.Amount > 0.01f ? Fluids.Water : "";
            s.Bar = boil / dt * 60f;   // L/min boiled now (readout)
            s.Note = fires == 0 ? "nofire" : s.Amount <= 0.01f ? "nowater" : room <= 0.01f ? "full" : "";
        }

        /// <summary>Drums touching each other share water and steam (one boiler).</summary>
        public static void EqualizeBoilers(World world)
        {
            HashSet<Vector3i> seen = new HashSet<Vector3i>();
            foreach (Vector3i start in new List<Vector3i>(FluidStore.Devices))
            {
                if (seen.Contains(start) || world.GetChunkFromWorldPos(start) == null) continue;
                Block b = world.GetBlock(start).Block;
                if (Fluids.Kind(b) != FluidKind.Boiler) continue;
                List<Vector3i> cl = new List<Vector3i>();
                Queue<Vector3i> q = new Queue<Vector3i>();
                q.Enqueue(start);
                seen.Add(start);
                while (q.Count > 0 && cl.Count < 256)
                {
                    Vector3i c = q.Dequeue();
                    cl.Add(c);
                    foreach (Vector3i d in Dirs)
                    {
                        Vector3i n = new Vector3i(c.x + d.x, c.y + d.y, c.z + d.z);
                        if (seen.Contains(n) || world.GetBlock(n).Block != b) continue;
                        seen.Add(n);
                        if (!FluidStore.Devices.Contains(n)) FluidStore.Register(n);
                        q.Enqueue(n);
                    }
                }
                if (cl.Count < 2) continue;
                float w = 0f, st = 0f;
                foreach (Vector3i c in cl) { FluidState s = FluidStore.Get(c); w += s.Amount; st += s.Steam; }
                foreach (Vector3i c in cl)
                {
                    FluidState s = FluidStore.Get(c);
                    s.Amount = w / cl.Count;
                    s.Steam = st / cl.Count;
                    s.Fluid = s.Amount > 0.01f ? Fluids.Water : "";
                }
            }
        }

        public static int BoilerSize(World world, Vector3i p, out float boilPerMin)
        {
            Block b = world.GetBlock(p).Block;
            HashSet<Vector3i> seen = new HashSet<Vector3i> { p };
            Queue<Vector3i> q = new Queue<Vector3i>();
            q.Enqueue(p);
            int n = 0;
            boilPerMin = 0f;
            while (q.Count > 0 && n < 256)
            {
                Vector3i c = q.Dequeue();
                n++;
                boilPerMin += FluidStore.Get(c).Bar;
                foreach (Vector3i d in Dirs)
                {
                    Vector3i m = new Vector3i(c.x + d.x, c.y + d.y, c.z + d.z);
                    if (seen.Contains(m) || world.GetBlock(m).Block != b) continue;
                    seen.Add(m);
                    q.Enqueue(m);
                }
            }
            return n;
        }

        // ------------------------------------------------------------ turbine
        public static float TurbineDemand(BlockValue bv, FluidState s)
        {
            return Mathf.Max(0f, Fluids.Prop(bv.Block, "FeFluidBuffer", 120f) - s.Amount);
        }

        /// <summary>How much of its rated output the turbine can give now (its steam buffer, 1 = full).</summary>
        public static float Readiness(Block b, FluidState s)
        {
            if (s.InBar + 0.001f < Fluids.Prop(b, "FeMinBar", 1.5f) && s.Amount < Fluids.Prop(b, "FeFluidBuffer", 120f) * 0.9f) return 0f;
            return Mathf.Clamp01(s.Amount / (0.5f * Fluids.Prop(b, "FeFluidBuffer", 120f)));
        }

        public static int Capacity(World world, Vector3i pos, BlockValue bv)
        {
            FluidStore.EnsureLoaded();
            if (!FluidStore.Devices.Contains(pos)) FluidStore.Register(pos);
            return Mathf.RoundToInt(Kinetic.SourceOutput(bv.Block) * Readiness(bv.Block, FluidStore.Get(pos)));
        }

        public static void TurbineTick(World world, Vector3i p, BlockValue bv, FluidState s, float dt)
        {
            TorqueNet net = Kinetic.Get(world, p);
            float load = net != null && net.Running && net.Capacity > 0 ? Mathf.Clamp((float)net.Usage / net.Capacity, 0.1f, 1f) : 0f;
            if (Readiness(bv.Block, s) <= 0f) load = 0f;
            float use = Mathf.Min(s.Amount, Fluids.Prop(bv.Block, "FeSteamRate", 240f) * load * dt / 60f);
            s.Amount -= use;
            s.Steam = Mathf.Min(Fluids.Prop(bv.Block, "FeFluidBuffer", 120f) * 2f, s.Steam + use * 0.9f);
            s.Bar = use / dt * 60f;
            s.Fluid = s.Amount > 0.01f ? Fluids.Steam : "";
        }

        // ------------------------------------------------------------ readouts
        public static string Describe(World world, Vector3i p, BlockValue bv, FluidState s)
        {
            if (Fluids.Kind(bv.Block) == FluidKind.Boiler)
            {
                float boil;
                int n = BoilerSize(world, p, out boil);
                string t = string.Format(Kinetic.Text("feBoilerInfo", "Boiler of {0} drum(s): water {1} L, steam {2} L, boiling {3} L/min"),
                    n, Mathf.RoundToInt(s.Amount * n), Mathf.RoundToInt(s.Steam * n), Mathf.RoundToInt(boil));
                if (s.Note == "nofire") t += "\n" + Kinetic.Text("feBoilerNoFire", "No lit Boiler Firebox touching this drum");
                else if (s.Note == "nowater") t += "\n" + Kinetic.Text("feBoilerNoWater", "No water: pipe water into a side");
                else if (s.Note == "full") t += "\n" + Kinetic.Text("feBoilerFull", "Steam full: pipe it from the top to turbines");
                return t;
            }
            string u = string.Format(Kinetic.Text("feTurbineInfo", "Steam in {0} L ({1} bar) - using {2} L/min - ready {3}%"),
                Mathf.RoundToInt(s.Amount), s.InBar.ToString("0.0", System.Globalization.CultureInfo.InvariantCulture),
                Mathf.RoundToInt(s.Bar), Mathf.RoundToInt(100f * Readiness(bv.Block, s)));
            u += "\n" + Kinetic.Text("feTurbineHow", "Steam in at the back, used steam out at the front; Dynamos on its shaft make electricity");
            return u;
        }
    }
}
