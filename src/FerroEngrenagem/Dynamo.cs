// Dynamo (user, 2026-11-23: "which item turns mechanical energy into electricity?"): a torque CONSUMER that is
// an electric power SOURCE. Vanilla Class="Generator" (TileEntityPowerSource + PowerGenerator, wires like any
// generator) with <property name="FeDynamo" value="true"/>:
//   - in the torque network it is a node with its shaft on local Z (both ends), costing FeTorqueCost UT at its RPM
//     like a machine (cost x (rpm/32)^2);
//   - while that network runs and counts it, every power tick keeps its generator fuelled and on, and sets its
//     MaxOutput to FeDynamoWatts x (rpm/32); without torque its fuel is emptied and vanilla turns it off.
// Fuel is internal bookkeeping only: the Refuel button / fuel row are hidden and the slots too (PowerPatches.cs,
// TorqueEngine.cs EngineSlots).
//
// C# 5 only.

using HarmonyLib;
using UnityEngine;

namespace FerroEngrenagem
{
    public static class Dynamo
    {
        public static bool Is(Block b)
        {
            return b != null && b.Properties != null && b.Properties.Contains("FeDynamo") && b.Properties.GetBool("FeDynamo");
        }

        public static bool Is(TileEntityPowerSource te)
        {
            return te != null && Is(te.blockValue.Block);
        }

        /// <summary>Watts it gives now (0 without torque).</summary>
        public static int Watts(World world, Vector3i pos, Block b)
        {
            TorqueNet net = Kinetic.Get(world, pos);
            if (net == null || !net.Running || !net.Machines.ContainsKey(pos)) return 0;
            float w = Fluids.Prop(b, "FeDynamoWatts", 60f) * net.MachineSpeed(pos);
            return Mathf.Clamp(Mathf.RoundToInt(w), 0, ushort.MaxValue);
        }
    }

    [HarmonyPatch(typeof(PowerSource), "HandleSendPower")]
    public static class Patch_PowerSource_HandleSendPower_Dynamo
    {
        public static void Prefix(PowerSource __instance)
        {
            PowerGenerator gen = __instance as PowerGenerator;
            if (gen == null || gen.BlockID >= Block.list.Length) return;
            Block b = Block.list[gen.BlockID];
            if (!Dynamo.Is(b)) return;
            World world = GameManager.Instance == null ? null : GameManager.Instance.World;
            if (world == null) return;
            int w = Dynamo.Watts(world, gen.Position, b);
            if (gen.MaxOutput != w)
            {
                gen.MaxOutput = (ushort)w;
                gen.SendHasLocalChangesToRoot();   // vanilla only re-sends power to the wires on a change
            }
            if (w > 0)
            {
                gen.CurrentFuel = gen.MaxFuel;
                if (!gen.IsOn) gen.IsOn = true;
            }
            else if (gen.CurrentFuel > 0)
            {
                gen.CurrentFuel = 0;   // vanilla ShouldAutoTurnOff then switches it off
            }
        }
    }
}
