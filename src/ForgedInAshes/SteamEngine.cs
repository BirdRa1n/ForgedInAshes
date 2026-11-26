// D9: the big Steam Engine (multiblock 3x2x3, vanilla Class=Generator + FeTorqueEngine + FeFluid=steamengine).
//
//   water in   under the parent cell (bottom centre), from a pipe or a pump directly below
//   steam out  over the top centre cell, into a pipe (to a Condenser); with nowhere to go it is vented
//   torque out the front centre cell of the bottom layer (local +Z of the model; one end)
//   items      Charcoal through the Refuel button, Lubricant in its slots (conveyors into the sides: phase 5)
//
// It gives UP TO FeTorqueOutput UT. Charcoal and water are used in proportion to the LOAD = what the torque
// network really uses of its capacity (at least FeIdleLoad when it runs idle): at full load FeWaterPerMin L/min of
// water become steam and one Charcoal lasts FeFuelSecondsPerUnit seconds. Its internal water tank holds
// FeWaterTank L (FluidStore); the steam buffer FeSteamBuffer L.
//
// C# 5 only.

using System.Collections.Generic;
using UnityEngine;

namespace ForgedInAshes
{
    public static class SteamEngine
    {
        static readonly Dictionary<Vector3i, float> lastLoad = new Dictionary<Vector3i, float>();

        public static bool Is(Block b)
        {
            return Fluids.Kind(b) == FluidKind.SteamEngine;
        }

        public static float LastLoad(Vector3i parent)
        {
            float v;
            return lastLoad.TryGetValue(parent, out v) ? v : 0f;
        }

        /// <summary>Fraction of its capacity the network is using (0..1); 0 when the network does not run.</summary>
        public static float Load(World world, Vector3i parent)
        {
            TorqueNet net = Kinetic.Get(world, parent);
            if (net == null || !net.Running || net.Capacity <= 0) return 0f;
            return Mathf.Clamp01((float)net.Usage / net.Capacity);
        }

        /// <summary>Consumption factor: the load, at least the idle share while it runs.</summary>
        public static float Factor(World world, Vector3i parent, Block b)
        {
            return Mathf.Max(Fluids.Prop(b, "FeIdleLoad", 0.1f), Load(world, parent));
        }

        public static void Run(World world, Vector3i p, BlockValue bv, FluidState s, float dt)
        {
            float load = Load(world, p);
            lastLoad[p] = load;
            if (!TorqueEngine.IsRunning(world, p)) return;
            float f = Mathf.Max(Fluids.Prop(bv.Block, "FeIdleLoad", 0.1f), load);
            float use = Mathf.Min(s.Amount, Fluids.Prop(bv.Block, "FeWaterPerMin", 60f) * f * dt / 60f);
            s.Amount -= use;
            if (s.Amount <= 0.01f) { s.Amount = 0f; }
            s.Fluid = Fluids.Water;
            s.Steam = Mathf.Min(s.Steam + use, Fluids.Prop(bv.Block, "FeSteamBuffer", 500f));   // the rest is vented
        }
    }
}
