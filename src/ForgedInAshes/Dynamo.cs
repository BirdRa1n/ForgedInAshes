// Dynamo (user, 2026-11-23: "which item turns mechanical energy into electricity?"): a torque CONSUMER that is
// an electric power SOURCE. Vanilla Class="Generator" (TileEntityPowerSource + PowerGenerator, wires like any
// generator) with <property name="FeDynamo" value="true"/>:
//   - in the torque network it is a node with its shaft on local Z (both ends; the Industrial Dynamo is a 3x2x3
//     multiblock whose shaft is the front centre of its bottom layer), costing FeTorqueCost UT at its RPM like a
//     machine (cost x (rpm/32)^2);
//   - while that network runs and counts it, every power tick keeps its generator fuelled and on, and sets its
//     MaxOutput to FeDynamoWatts x (rpm/32); without torque its fuel is emptied and vanilla turns it off.
// Fuel is internal bookkeeping only: the Refuel button / fuel row are hidden and the slots too.
//
// Power Bus (FeBus): vanilla lets a power source take a parent only when it is a battery bank
// (TileEntityPowerSource.CanHaveParent: PowerItemType == 7, IL 3.4.0 b10), so two generators can never share a
// wire. The Bus is a generator that the player wires TO dynamos (and to other buses): those children may have it
// as their parent (CanHaveParent postfix), their own output drops to 0 and the Bus outputs the SUM of their watts
// on its own wires. PowerManager.Update ticks every PowerSource, children included, so the dynamos keep
// computing their watts. Vanilla generators, solar panels and batteries cannot join a Bus.
//
// C# 5 only.

using System.Collections.Generic;
using HarmonyLib;
using UnityEngine;

namespace ForgedInAshes
{
    public static class Dynamo
    {
        static readonly Dictionary<Vector3i, int> contribution = new Dictionary<Vector3i, int>();

        static readonly Dictionary<int, bool> dynamoByBlock = new Dictionary<int, bool>();

        /// <summary>Cached per block id: Kinetic.Kind asks it for every non-mod neighbour while building a network.</summary>
        public static bool Is(Block b)
        {
            if (b == null) return false;
            bool v;
            if (dynamoByBlock.TryGetValue(b.blockID, out v)) return v;
            v = b.Properties != null && b.Properties.Contains("FeDynamo") && b.Properties.GetBool("FeDynamo");
            dynamoByBlock[b.blockID] = v;
            return v;
        }

        public static bool Is(TileEntityPowerSource te)
        {
            return te != null && Is(te.blockValue.Block);
        }

        public static bool IsBus(Block b)
        {
            return b != null && b.Properties != null && b.Properties.Contains("FeBus") && b.Properties.GetBool("FeBus");
        }

        public static bool IsBus(TileEntityPowerSource te)
        {
            return te != null && IsBus(te.blockValue.Block);
        }

        /// <summary>Dynamo or Bus: generators whose fuel is internal (no Refuel, no slots).</summary>
        public static bool IsInternal(TileEntityPowerSource te)
        {
            return Is(te) || IsBus(te);
        }

        /// <summary>Watts a dynamo gives now (0 without torque).</summary>
        public static int Watts(World world, Vector3i pos, Block b)
        {
            Vector3i node = Kinetic.NodeOf(world, pos);
            TorqueNet net = Kinetic.Get(world, node);
            if (net == null || !net.Running || !net.Machines.ContainsKey(node)) return 0;
            float w = Fluids.Prop(b, "FeDynamoWatts", 60f) * net.MachineSpeed(node);
            return Mathf.Clamp(Mathf.RoundToInt(w), 0, ushort.MaxValue);
        }

        /// <summary>Watts a child of a Bus adds to it (dynamos: their watts; buses: their own sum).</summary>
        public static int Contribution(Vector3i pos)
        {
            int v;
            return contribution.TryGetValue(pos, out v) ? v : 0;
        }

        internal static void SetContribution(Vector3i pos, int w)
        {
            contribution[pos] = w;
        }

        internal static bool UnderBus(PowerItem item)
        {
            PowerSource parent = item.Parent as PowerSource;
            return parent != null && parent.BlockID < Block.list.Length && IsBus(Block.list[parent.BlockID]);
        }

        /// <summary>Keep an internal-fuel generator on with `w` watts, or let it turn off.</summary>
        internal static void Drive(PowerGenerator gen, int outW, bool on)
        {
            if (gen.MaxOutput != outW)
            {
                gen.MaxOutput = (ushort)Mathf.Clamp(outW, 0, ushort.MaxValue);
                gen.SendHasLocalChangesToRoot();   // vanilla only re-sends power to the wires on a change
            }
            if (on)
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

    [HarmonyPatch(typeof(PowerSource), "HandleSendPower")]
    public static class Patch_PowerSource_HandleSendPower_Dynamo
    {
        public static void Prefix(PowerSource __instance)
        {
            PowerGenerator gen = __instance as PowerGenerator;
            if (gen == null || gen.BlockID >= Block.list.Length) return;
            Block b = Block.list[gen.BlockID];
            World world = GameManager.Instance == null ? null : GameManager.Instance.World;
            if (world == null) return;
            if (Dynamo.Is(b))
            {
                int w = Dynamo.Watts(world, gen.Position, b);
                bool bus = Dynamo.UnderBus(gen);
                Dynamo.SetContribution(gen.Position, bus ? w : 0);
                // under a Bus its watts go up to the Bus; its own wires get nothing
                Dynamo.Drive(gen, bus ? 0 : w, w > 0);
            }
            else if (Dynamo.IsBus(b))
            {
                int sum = 0;
                if (gen.Children != null)
                    foreach (PowerItem c in gen.Children)
                        if (c is PowerSource) sum += Dynamo.Contribution(c.Position);
                bool bus = Dynamo.UnderBus(gen);
                Dynamo.SetContribution(gen.Position, bus ? sum : 0);
                Dynamo.Drive(gen, bus ? 0 : sum, sum > 0);
            }
        }
    }

    // A dynamo or bus may be wired as the CHILD of a Bus (vanilla only allows battery banks to have a parent).
    [HarmonyPatch(typeof(TileEntityPowerSource), "CanHaveParent")]
    public static class Patch_TEPowerSource_CanHaveParent_Bus
    {
        public static void Postfix(TileEntityPowerSource __instance, IPowered powered, ref bool __result)
        {
            if (__result || !Dynamo.IsInternal(__instance)) return;
            TileEntityPowerSource parent = powered as TileEntityPowerSource;
            if (parent != null && Dynamo.IsBus(parent)) __result = true;
        }
    }

    // the server-side twin of CanHaveParent (PowerSource.CanParent returns false for every source)
    [HarmonyPatch(typeof(PowerSource), "CanParent")]
    public static class Patch_PowerSource_CanParent_Bus
    {
        public static void Postfix(PowerSource __instance, PowerItem newParent, ref bool __result)
        {
            if (__result || __instance.BlockID >= Block.list.Length) return;
            Block b = Block.list[__instance.BlockID];
            if (!Dynamo.Is(b) && !Dynamo.IsBus(b)) return;
            if (newParent != null && newParent.BlockID < Block.list.Length && Dynamo.IsBus(Block.list[newParent.BlockID]))
                __result = true;
        }
    }

    // Bus readout: how many sources it joins and their sum
    [HarmonyPatch(typeof(BlockPowerSource), "GetActivationText")]
    public static class Patch_BlockPowerSource_ActivationText_Bus
    {
        public static void Postfix(BlockPowerSource __instance, Vector3i _blockPos, ref string __result)
        {
            if (!Dynamo.IsBus(__instance)) return;
            World world = GameManager.Instance == null ? null : GameManager.Instance.World;
            TileEntityPowerSource te = world == null ? null : world.GetTileEntity(_blockPos) as TileEntityPowerSource;
            PowerGenerator gen = te == null ? null : te.GetPowerItem() as PowerGenerator;
            int n = 0, sum = 0;
            if (gen != null && gen.Children != null)
                foreach (PowerItem c in gen.Children)
                    if (c is PowerSource) { n++; sum += Dynamo.Contribution(c.Position); }
            string line = string.Format(Kinetic.Text("feBusInfo", "Joins {0} source(s): {1} W"), n, sum);
            __result = string.IsNullOrEmpty(__result) ? KineticLookController.Escape(line)
                                                      : __result + "\n" + KineticLookController.Escape(line);
        }
    }
}
