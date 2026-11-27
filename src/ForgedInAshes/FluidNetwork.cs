// D9: FLUID network (Create-like pipes). See PLANO_MOD.md 5.5.
//
// A block takes part with <property name="FeFluid" value="..."/>:
//   pipe         joins all six sides to pipes and to device ports
//   tank         Water Tank: stores FeFluidCapacity L of one fluid; a port on every side (buffer of the network)
//   mechpump     Mechanical Pump (BlockFeKinetic, FeKinetic=pump: a torque consumer): pulls liquid from the world
//                water at its intake (local -Z) and pushes it out of its outlet (local +Z); FeFluidRate L/min at
//                32 RPM, proportional to its RPM
//   elecpump     Electric Pump (Class Powered): the same while powered; FeFluidRate L/min
//   condenser    Condenser (Class Powered): steam in at local -Z, water out at local +Z; while powered it condenses
//                up to FeFluidRate L/min of steam and gives back FeCondenseRatio of it as water
//   steamengine  Steam Engine (multiblock 3x2x3 Generator, TorqueEngine.cs): water in under its parent cell (the
//                bottom centre), steam out over the top centre cell; internal water tank FeWaterTank L
//
// Fluids: "water", "steam". One network (pipes + the ports touching them, or two ports facing each other directly)
// carries ONE fluid; two fluids offered into the same network = BLOCKED (nothing moves).
// World water is an endless source for pumps (needs FeIntakeWater water cells around the intake; the game's water
// volume is not touched).
//
// Simulation: FluidTicker (server / host) every TickSeconds:
//   1. devices produce: pumps (water), condensers (water condensed in the previous tick), steam engines (steam);
//   2. per network: offers go to the demands (steam engine water space, condenser steam intake), proportionally;
//      surplus fills the tanks, missing demand drains the tanks; unused pump offer is simply not pumped, unused
//      steam is vented by the engine (its buffer is capped).
// Device positions and stored fluid live in FluidStore (a text file in the save game folder), because pipes,
// pumps and tanks are plain blocks without tile entities.
//
// C# 5 only.

using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using HarmonyLib;
using UnityEngine;

namespace ForgedInAshes
{
    public enum FluidKind { None, Pipe, Tank, MechPump, ElecPump, Condenser, SteamEngine, Filler, Bottler, Refinery, Chute, Smelter, Caster, Processor,
                            GasTank, Valve, Gauge, Burner, Tapper, TowerSection, Boiler, Turbine }

    /// <summary>Identity of a port (owner, cell, side, direction) for sets and lookups, without building strings.</summary>
    public struct PortKey : System.IEquatable<PortKey>
    {
        public Vector3i Owner, Cell, Dir;
        public bool Out;

        public PortKey(FluidPort p)
        {
            Owner = p.Owner; Cell = p.Cell; Dir = p.Dir; Out = p.Out;
        }

        public bool Equals(PortKey o)
        {
            return Out == o.Out && Owner == o.Owner && Cell == o.Cell && Dir == o.Dir;
        }

        public override bool Equals(object o)
        {
            return o is PortKey && Equals((PortKey)o);
        }

        public override int GetHashCode()
        {
            unchecked
            {
                int h = Owner.GetHashCode();
                h = h * 397 ^ Cell.GetHashCode();
                h = h * 397 ^ Dir.GetHashCode();
                return h * 2 + (Out ? 1 : 0);
            }
        }
    }

    public class FluidPort
    {
        public Vector3i Owner;     // device parent position
        public Vector3i Cell;      // the device cell the port is on
        public Vector3i Dir;       // outward direction
        public bool Out;           // true = offers fluid, false = takes fluid
        public string Fluid;       // fluid it handles
        public bool Metal;         // F8.1: molten metal port (joins Metal Chutes only, never pipes)
        public string[] Accepts;   // F8.1: a demand port taking any of these (the Casting Table's mold metals)
    }

    public class FluidState
    {
        public string Fluid = "";  // stored fluid (tanks, engine water)
        public float Amount;       // stored litres
        public float Steam;        // steam buffer (engines) / condensed water buffer (condensers)
        public float LastFlow;     // L/min moved last tick (readout)
        public string Note = "";   // readout: why it does not run
        public string Mold = "";   // F8.1 Casting Table: the mold in it
        public string Made = "";   // F8.1 Casting Table: the item its finished casts are
        public int Count;          // F8.1 Casting Table: finished casts waiting to leave
        public string Stock = "";  // F8.2 process machine: ingredients inside ("item=n,...")
        public string Pick = "";   // process machine: the recipe the player chose ("" = automatic, first ready);
                                   // D12 valves / gauges: their setting
        // D12 (saved): extra fluid buffers "slot=fluid:litres,..." (process machines: in1, out0..out2), products
        // waiting "item=n,..." and the machine switched off
        public string Tanks = "";
        public string Out = "";
        public bool Off;
        // D12 (runtime): pressure of the network at its ports (bar), the pressure it offers at, signal, heat asked
        public float Bar, InBar, OutBar;
        public bool Sig;
        public float HeatAsk;
    }

    public class FluidNet
    {
        public readonly HashSet<Vector3i> Pipes = new HashSet<Vector3i>();
        public readonly List<FluidPort> Ports = new List<FluidPort>();
        public string Fluid = "";
        public bool Blocked;
        public float FlowPerMin;
        public float Pressure;     // D12: bar (gases)
        public float MaxBar = 99f; // D12: the weakest pipe of the network
        public bool Leak;          // D12: pressure above what its pipes stand: gas escapes
        public float Volume;       // D12: litres of gas tanks at 1 bar
        public float Stored;       // litres in its tanks
    }

    public static class Fluids
    {
        public const string Water = "water";
        public const string Steam = "steam";
        public const string Oil = "oil";
        public const string Gasoline = "gasoline";
        public const string Lubricant = "lubricant";
        // F8.1 (PLANO_CRAFT.md): molten metals. They run in Metal Chutes only (a pipe never carries them).
        public const string MoltenBrass = "molten_brass";
        public const string MoltenLead = "molten_lead";
        public const string MoltenIron = "molten_iron";
        public const string MoltenSteel = "molten_steel";

        public static bool IsMetal(string f)
        {
            return f != null && f.StartsWith("molten_", System.StringComparison.Ordinal);
        }

        /// <summary>D12: gases (steam, shale gas, fuel gas, compressed air) have a pressure.</summary>
        public static bool IsGas(string f)
        {
            if (string.IsNullOrEmpty(f)) return false;
            if (f == Steam) return true;
            FluidDef d;
            return Processes.FluidDefs.TryGetValue(f, out d) && d.Class == "gas";
        }

        /// <summary>Pipes and Metal Chutes: the blocks a network runs through.</summary>
        public static bool IsConduit(FluidKind k)
        {
            return k == FluidKind.Pipe || k == FluidKind.Chute;
        }

        // D9: fluids that are also items (the Filler pours the items in, the Bottler and the Refinery turn the fluid
        // back into items): fluid, item, litres per item
        static readonly string[,] ItemFluids =
        {
            { Oil, "resourceOil", "10" },
            { Gasoline, "ammoGasCan", "1" },
            { Lubricant, "feResourceLubricant", "10" },
        };

        /// <summary>The fluid an item becomes, with its litres per item; null when it is not a fluid item.</summary>
        public static string FluidOfItem(string item, out float litres)
        {
            litres = 0f;
            foreach (FluidDef d in Processes.FluidDefs.Values)
                if (d.Item == item && d.Per > 0f) { litres = d.Per; return d.Name; }
            for (int i = 0; i < ItemFluids.GetLength(0); i++)
                if (ItemFluids[i, 1] == item)
                {
                    litres = float.Parse(ItemFluids[i, 2], CultureInfo.InvariantCulture);
                    return ItemFluids[i, 0];
                }
            return null;
        }

        /// <summary>The item a fluid is bottled into, with its litres per item; null when it cannot be bottled.</summary>
        public static string ItemOfFluid(string fluid, out float litres)
        {
            litres = 0f;
            FluidDef fd;
            if (fluid != null && Processes.FluidDefs.TryGetValue(fluid, out fd) && fd.Item != null && fd.Per > 0f)
            {
                litres = fd.Per;
                return fd.Item;
            }
            for (int i = 0; i < ItemFluids.GetLength(0); i++)
                if (ItemFluids[i, 0] == fluid)
                {
                    litres = float.Parse(ItemFluids[i, 2], CultureInfo.InvariantCulture);
                    return ItemFluids[i, 1];
                }
            return null;
        }
        public const float TickSeconds = 0.5f;

        static readonly Vector3i[] Dirs =
        {
            new Vector3i(1, 0, 0), new Vector3i(-1, 0, 0), new Vector3i(0, 1, 0),
            new Vector3i(0, -1, 0), new Vector3i(0, 0, 1), new Vector3i(0, 0, -1)
        };

        static readonly Dictionary<int, FluidKind> kindByBlock = new Dictionary<int, FluidKind>();

        public static FluidKind Kind(Block b)
        {
            if (b == null) return FluidKind.None;
            FluidKind k;
            if (kindByBlock.TryGetValue(b.blockID, out k)) return k;
            k = FluidKind.None;
            if (b.Properties != null && b.Properties.Contains("FeFluid"))
            {
                switch (b.Properties.GetString("FeFluid").Trim().ToLowerInvariant())
                {
                    case "pipe": k = FluidKind.Pipe; break;
                    case "tank": k = FluidKind.Tank; break;
                    case "mechpump": k = FluidKind.MechPump; break;
                    case "elecpump": k = FluidKind.ElecPump; break;
                    case "condenser": k = FluidKind.Condenser; break;
                    case "steamengine": k = FluidKind.SteamEngine; break;
                    case "filler": k = FluidKind.Filler; break;
                    case "bottler": k = FluidKind.Bottler; break;
                    case "refinery": k = FluidKind.Refinery; break;
                    case "chute": k = FluidKind.Chute; break;
                    case "smelter": k = FluidKind.Smelter; break;
                    case "caster": k = FluidKind.Caster; break;
                    case "processor": k = FluidKind.Processor; break;
                    case "gastank": k = FluidKind.GasTank; break;
                    case "valve": k = FluidKind.Valve; break;
                    case "gauge": k = FluidKind.Gauge; break;
                    case "burner": k = FluidKind.Burner; break;
                    case "tapper": k = FluidKind.Tapper; break;
                    case "towersection": k = FluidKind.TowerSection; break;
                    case "boiler": k = FluidKind.Boiler; break;
                    case "turbine": k = FluidKind.Turbine; break;
                }
            }
            kindByBlock[b.blockID] = k;
            return k;
        }

        static readonly Dictionary<string, int> propIds = new Dictionary<string, int>();
        static readonly Dictionary<long, float> propCache = new Dictionary<long, float>();

        /// <summary>A float block property, or def when the block does not have it. Cached per (block id, name):
        /// DynamicProperties.GetFloat parses the text on every call, and the fluid tick asks for these per device and
        /// per port twice a second. Block properties never change while a game runs.</summary>
        public static float Prop(Block b, string name, float def)
        {
            int id;
            if (!propIds.TryGetValue(name, out id)) { id = propIds.Count; propIds[name] = id; }
            long key = ((long)b.blockID << 16) | (long)id;
            float v;
            if (!propCache.TryGetValue(key, out v))
            {
                v = b.Properties != null && b.Properties.Contains(name) ? b.Properties.GetFloat(name) : float.NaN;
                propCache[key] = v;
            }
            return float.IsNaN(v) ? def : v;
        }

        public static Vector3i Rot(BlockValue bv, Vector3 local)
        {
            Vector3 a = bv.Block.shape.GetRotation(bv) * local;
            return new Vector3i(Mathf.RoundToInt(a.x), Mathf.RoundToInt(a.y), Mathf.RoundToInt(a.z));
        }

        static Vector3i Add(Vector3i a, Vector3i b)
        {
            return new Vector3i(a.x + b.x, a.y + b.y, a.z + b.z);
        }

        static Vector3i Neg(Vector3i a)
        {
            return new Vector3i(-a.x, -a.y, -a.z);
        }

        /// <summary>The device parent of a cell (multiblock children point at their parent).</summary>
        public static Vector3i ParentOf(World world, Vector3i pos, BlockValue bv)
        {
            if (bv.ischild && bv.Block.multiBlockPos != null) return bv.Block.multiBlockPos.GetParentPos(pos, bv);
            return pos;
        }

        /// <summary>The ports of the device whose parent is at pos (none for pipes).</summary>
        public static List<FluidPort> Ports(World world, Vector3i pos)
        {
            List<FluidPort> l = new List<FluidPort>();
            BlockValue bv = world.GetBlock(pos);
            FluidKind k = Kind(bv.Block);
            switch (k)
            {
                case FluidKind.Tank:
                case FluidKind.GasTank:
                    foreach (Vector3i d in Dirs)
                    {
                        l.Add(new FluidPort { Owner = pos, Cell = pos, Dir = d, Out = true, Fluid = "" });
                        l.Add(new FluidPort { Owner = pos, Cell = pos, Dir = d, Out = false, Fluid = "" });
                    }
                    break;
                case FluidKind.MechPump:
                case FluidKind.ElecPump:
                    l.Add(new FluidPort { Owner = pos, Cell = pos, Dir = Rot(bv, Vector3.forward), Out = true, Fluid = Water });
                    break;
                case FluidKind.Filler:
                    // pours what it holds out of its front
                    l.Add(new FluidPort { Owner = pos, Cell = pos, Dir = Rot(bv, Vector3.forward), Out = true, Fluid = FluidStore.Get(pos).Fluid });
                    break;
                case FluidKind.Bottler:
                case FluidKind.Refinery:
                    // takes in at its back: the fluid it holds, or (empty) any fluid that can be bottled
                    l.Add(new FluidPort { Owner = pos, Cell = pos, Dir = Rot(bv, Vector3.back), Out = false, Fluid = FluidStore.Get(pos).Fluid });
                    break;
                case FluidKind.Condenser:
                    // 2 wide x 2 high (parent = bottom cell of its own column): steam in at the back of the upper
                    // cell (gas chamber), water out at the front of the lower cell (liquid chamber)
                    l.Add(new FluidPort { Owner = pos, Cell = Add(pos, new Vector3i(0, 1, 0)), Dir = Rot(bv, Vector3.back), Out = false, Fluid = Steam });
                    l.Add(new FluidPort { Owner = pos, Cell = pos, Dir = Rot(bv, Vector3.forward), Out = true, Fluid = Water });
                    break;
                case FluidKind.Smelter:
                    // F8.1 Foundry (2 wide x 2 high, parent = bottom cell, the other bottom cell at local -X): molten
                    // metal leaves through any outer side of its bottom layer that has a Metal Chute
                    {
                        FluidState ss = FluidStore.Get(pos);
                        Vector3i other = Add(pos, Rot(bv, Vector3.left));
                        foreach (Vector3 side in new Vector3[] { Vector3.right, Vector3.forward, Vector3.back })
                            l.Add(new FluidPort { Owner = pos, Cell = pos, Dir = Rot(bv, side), Out = true, Fluid = ss.Fluid, Metal = true });
                        foreach (Vector3 side in new Vector3[] { Vector3.left, Vector3.forward, Vector3.back })
                            l.Add(new FluidPort { Owner = pos, Cell = other, Dir = Rot(bv, side), Out = true, Fluid = ss.Fluid, Metal = true });
                    }
                    break;
                case FluidKind.Caster:
                    // F8.1 Casting Table: metal in at its back; takes the metals its mold accepts
                    {
                        FluidState cs = FluidStore.Get(pos);
                        l.Add(new FluidPort { Owner = pos, Cell = pos, Dir = Rot(bv, Vector3.back), Out = false,
                                              Fluid = cs.Amount > 0.01f ? cs.Fluid : "", Metal = true,
                                              Accepts = MetalWorks.MoldMetals(cs.Mold) });
                    }
                    break;
                case FluidKind.Processor:
                    // F8.2 / D12: its fluid inputs (back, bottom) and outputs (top, right, left; a tower base: right
                    // and left) - ProcessMachine.FluidPorts
                    ProcessMachine.FluidPorts(world, pos, bv, l);
                    break;
                case FluidKind.Valve:
                    FluidControl.Ports(world, pos, bv, l);
                    break;
                case FluidKind.Boiler:
                    SteamPlant.BoilerPorts(pos, l);
                    break;
                case FluidKind.Turbine:
                    SteamPlant.TurbinePorts(pos, bv, l);
                    break;
                case FluidKind.Gauge:
                    l.Add(new FluidPort { Owner = pos, Cell = pos, Dir = Rot(bv, Vector3.back), Out = false, Fluid = "" });
                    break;
                case FluidKind.Burner:
                    l.Add(new FluidPort { Owner = pos, Cell = pos, Dir = Rot(bv, Vector3.back), Out = false, Fluid = "",
                                          Accepts = FluidControl.BurnerFuels });
                    break;
                case FluidKind.Tapper:
                    l.Add(new FluidPort { Owner = pos, Cell = pos, Dir = Rot(bv, Vector3.forward), Out = true, Fluid = FluidControl.Latex });
                    break;
                case FluidKind.TowerSection:
                    {
                        FluidState ts = FluidStore.Get(pos);
                        foreach (Vector3i d in Dirs)
                            if (d.y == 0) l.Add(new FluidPort { Owner = pos, Cell = pos, Dir = d, Out = true, Fluid = ts.Fluid });
                    }
                    break;
                case FluidKind.SteamEngine:
                    // parent = bottom centre cell (vanilla multiblock layout: x/z -1..1, y 0..1). Water in under the
                    // centre and on the left, right and back of the bottom layer; steam out over the top centre.
                    l.Add(new FluidPort { Owner = pos, Cell = pos, Dir = new Vector3i(0, -1, 0), Out = false, Fluid = Water });
                    foreach (Vector3 side in new Vector3[] { Vector3.left, Vector3.right, Vector3.back })
                    {
                        Vector3i d = Rot(bv, side);
                        l.Add(new FluidPort { Owner = pos, Cell = Add(pos, d), Dir = d, Out = false, Fluid = Water });
                    }
                    Vector3i top = Add(pos, new Vector3i(0, 1, 0));
                    l.Add(new FluidPort { Owner = pos, Cell = top, Dir = new Vector3i(0, 1, 0), Out = true, Fluid = Steam });
                    break;
            }
            return l;
        }

        /// <summary>Conveyor (item) inputs of a device, for the markers only until conveyors exist (phase 5): the
        /// Steam Engine takes items on the left and right of its upper layer.</summary>
        public static List<FluidPort> ConveyorPorts(World world, Vector3i pos)
        {
            List<FluidPort> l = new List<FluidPort>();
            BlockValue bv = world.GetBlock(pos);
            if (Kind(bv.Block) != FluidKind.SteamEngine) return l;
            foreach (Vector3 side in new Vector3[] { Vector3.left, Vector3.right })
            {
                Vector3i d = Rot(bv, side);
                l.Add(new FluidPort { Owner = pos, Cell = new Vector3i(pos.x + d.x, pos.y + 1, pos.z + d.z), Dir = d, Out = false, Fluid = "items" });
            }
            return l;
        }

        /// <summary>Is there something that takes or gives fluid on the other side of this port?</summary>
        public static bool PortConnected(World world, FluidPort p)
        {
            Vector3i n = Add(p.Cell, p.Dir);
            return HasPortAt(world, n, Neg(p.Dir), p.Metal);
        }

        /// <summary>Does a device cell have a port facing dir (for pipe connections and the arms of pipe models)?</summary>
        public static bool HasPortAt(World world, Vector3i cell, Vector3i dir)
        {
            return HasPortAt(world, cell, dir, false);
        }

        /// <summary>metal: asked for a Metal Chute (molten metal ports) instead of a pipe.</summary>
        public static bool HasPortAt(World world, Vector3i cell, Vector3i dir, bool metal)
        {
            BlockValue bv = world.GetBlock(cell);
            if (bv.isair) return false;   // perf: most pipe arms face air; skip the device scan below
            FluidKind k = Kind(bv.Block);
            if (k == FluidKind.None)
            {
                // a multiblock cell the world does not report as the device (seen on the Condenser's upper cell):
                // ask the registered devices whose ports sit on that cell
                FluidStore.EnsureLoaded();
                foreach (Vector3i dev in FluidStore.Devices)
                {
                    if (Mathf.Abs(dev.x - cell.x) > 2 || Mathf.Abs(dev.y - cell.y) > 2 || Mathf.Abs(dev.z - cell.z) > 2) continue;
                    foreach (FluidPort p in Ports(world, dev))
                        if (p.Cell == cell && p.Dir == dir && p.Metal == metal) return true;
                }
                return false;
            }
            if (IsConduit(k)) return k == (metal ? FluidKind.Chute : FluidKind.Pipe);
            Vector3i owner = ParentOf(world, cell, bv);
            foreach (FluidPort p in Ports(world, owner))
                if (p.Cell == cell && p.Dir == dir && p.Metal == metal) return true;
            return false;
        }

        /// <summary>Network that the cell+dir side of a port leads into (pipes, or the facing port of another
        /// device). The key is the first pipe, or the pair of device cells.</summary>
        public static FluidNet NetFrom(World world, FluidPort start, Dictionary<string, FluidPort[]> allPorts)
        {
            FluidNet net = new FluidNet();
            Vector3i first = Add(start.Cell, start.Dir);
            BlockValue fb = world.GetBlock(first);
            FluidKind want = start.Metal ? FluidKind.Chute : FluidKind.Pipe;
            FluidKind fk = Kind(fb.Block);
            if (fk != want)
            {
                // device facing device directly (a conduit of the other sort leads nowhere)
                net.Ports.Add(start);
                Vector3i owner = ParentOf(world, first, fb);
                if (fk != FluidKind.None && !IsConduit(fk))
                    foreach (FluidPort p in Ports(world, owner))
                        if (p.Cell == first && p.Dir == Neg(start.Dir) && p.Metal == start.Metal) net.Ports.Add(p);
                return net;
            }
            Queue<Vector3i> open = new Queue<Vector3i>();
            open.Enqueue(first);
            net.Pipes.Add(first);
            HashSet<PortKey> seenPorts = new HashSet<PortKey>();
            while (open.Count > 0 && net.Pipes.Count < 2048)
            {
                Vector3i p = open.Dequeue();
                foreach (Vector3i d in Dirs)
                {
                    Vector3i n = Add(p, d);
                    BlockValue nb = world.GetBlock(n);
                    FluidKind nk = Kind(nb.Block);
                    if (nk == FluidKind.None) continue;
                    if (IsConduit(nk))
                    {
                        if (nk == want && net.Pipes.Add(n)) open.Enqueue(n);
                        continue;
                    }
                    Vector3i owner = ParentOf(world, n, nb);
                    foreach (FluidPort port in Ports(world, owner))
                    {
                        if (port.Cell != n || port.Dir != Neg(d) || port.Metal != start.Metal) continue;
                        if (seenPorts.Add(new PortKey(port))) net.Ports.Add(port);
                    }
                }
            }
            return net;
        }

        /// <summary>World water cells around a pump intake (the cell behind the pump and its neighbours).</summary>
        public static int IntakeWater(World world, Vector3i pump, BlockValue bv)
        {
            int depth = (int)Prop(bv.Block, "FeIntakeDepth", 0f);
            if (depth > 0)
            {
                // D13 Hose Pulley: the hose goes down through air (or water) to the first water and counts the pool
                for (int dy = 1; dy <= depth; dy++)
                {
                    int y = pump.y - dy;
                    if (world.IsWater(pump.x, y, pump.z))
                    {
                        int w = 0;
                        for (int dx = -2; dx <= 2; dx++)
                            for (int dz = -2; dz <= 2; dz++)
                                for (int d2 = 0; d2 <= 1; d2++)
                                    if (world.IsWater(pump.x + dx, y - d2, pump.z + dz)) w++;
                        return w;
                    }
                    if (!world.GetBlock(new Vector3i(pump.x, y, pump.z)).isair) return 0;
                }
                return 0;
            }
            Vector3i intake = Add(pump, Rot(bv, Vector3.back));
            int n = 0;
            for (int dx = -1; dx <= 1; dx++)
                for (int dy = -1; dy <= 0; dy++)
                    for (int dz = -1; dz <= 1; dz++)
                        if (world.IsWater(intake.x + dx, intake.y + dy, intake.z + dz)) n++;
            return n;
        }

        internal static string Text(string key, string fallback)
        {
            return Kinetic.Text(key, fallback);
        }

        public static string FluidName(string f)
        {
            if (f == Water) return Text("feFluidWater", "Water");
            if (f == Steam) return Text("feFluidSteam", "Steam");
            if (f == Oil) return Text("feFluidOil", "Oil");
            if (f == Gasoline) return Text("feFluidGasoline", "Gasoline");
            if (f == Lubricant) return Text("feFluidLubricant", "Lubricant");
            if (f == MoltenBrass) return Text("feFluidMoltenBrass", "Molten Brass");
            if (f == MoltenLead) return Text("feFluidMoltenLead", "Molten Lead");
            if (f == MoltenIron) return Text("feFluidMoltenIron", "Molten Iron");
            if (f == MoltenSteel) return Text("feFluidMoltenSteel", "Molten Steel");
            FluidDef d;
            if (!string.IsNullOrEmpty(f) && Processes.FluidDefs.TryGetValue(f, out d)) return Text("feFluid_" + f, d.Text);
            return Text("feFluidNone", "empty");
        }
    }

    // ------------------------------------------------------------------ persistence + device registry
    public static class FluidStore
    {
        static string loadedFor;
        static bool dirty;
        static readonly Dictionary<Vector3i, FluidState> states = new Dictionary<Vector3i, FluidState>();
        public static readonly HashSet<Vector3i> Devices = new HashSet<Vector3i>();

        static string FilePath()
        {
            return ForgedInAshesMod.SaveFile("fluids");
        }

        public static void EnsureLoaded()
        {
            string f = FilePath();
            if (f == null || f == loadedFor) return;
            loadedFor = f;
            states.Clear();
            Devices.Clear();
            dirty = false;
            if (!File.Exists(f)) return;
            try
            {
                foreach (string line in File.ReadAllLines(f))
                {
                    string[] t = line.Split(';');
                    if (t.Length < 6) continue;
                    Vector3i p = new Vector3i(int.Parse(t[0]), int.Parse(t[1]), int.Parse(t[2]));
                    Devices.Add(p);
                    FluidState s = new FluidState();
                    s.Fluid = t[3];
                    s.Amount = float.Parse(t[4], CultureInfo.InvariantCulture);
                    s.Steam = float.Parse(t[5], CultureInfo.InvariantCulture);
                    if (t.Length >= 9)
                    {
                        s.Mold = t[6];
                        s.Made = t[7];
                        s.Count = int.Parse(t[8]);
                    }
                    if (t.Length >= 10) s.Stock = t[9];
                    if (t.Length >= 11) s.Pick = t[10];
                    if (t.Length >= 12) s.Tanks = t[11];
                    if (t.Length >= 13) s.Out = t[12];
                    if (t.Length >= 14) s.Off = t[13] == "1";
                    states[p] = s;
                }
            }
            catch (System.Exception e)
            {
                Log.Warning(ForgedInAshesMod.LogPrefix + "fluids: could not read " + f + ": " + e.Message);
            }
        }

        public static void Save()
        {
            if (!dirty || loadedFor == null) return;
            try
            {
                StringBuilder sb = new StringBuilder();
                foreach (Vector3i p in Devices)
                {
                    FluidState s = Get(p);
                    sb.Append(p.x).Append(';').Append(p.y).Append(';').Append(p.z).Append(';').Append(s.Fluid).Append(';')
                      .Append(s.Amount.ToString("0.###", CultureInfo.InvariantCulture)).Append(';')
                      .Append(s.Steam.ToString("0.###", CultureInfo.InvariantCulture)).Append(';')
                      .Append(s.Mold).Append(';').Append(s.Made).Append(';').Append(s.Count).Append(';')
                      .Append(s.Stock).Append(';').Append(s.Pick).Append(';').Append(s.Tanks).Append(';')
                      .Append(s.Out).Append(';').Append(s.Off ? "1" : "0").Append('\n');
                }
                File.WriteAllText(loadedFor, sb.ToString());
                dirty = false;
            }
            catch (System.Exception e)
            {
                Log.Warning(ForgedInAshesMod.LogPrefix + "fluids: could not save: " + e.Message);
            }
        }

        public static FluidState Get(Vector3i p)
        {
            FluidState s;
            if (!states.TryGetValue(p, out s)) { s = new FluidState(); states[p] = s; }
            return s;
        }

        public static void MarkDirty()
        {
            dirty = true;
        }

        public static void Register(Vector3i p)
        {
            EnsureLoaded();
            if (Devices.Add(p)) dirty = true;
            FluidTicker.Ensure();
        }

        public static void Unregister(Vector3i p)
        {
            EnsureLoaded();
            if (Devices.Remove(p)) { states.Remove(p); dirty = true; }
        }
    }

    // ------------------------------------------------------------------ simulation
    public class FluidTicker : MonoBehaviour
    {
        static GameObject host;
        float next, nextSave;
        public static readonly Dictionary<Vector3i, FluidNet> NetByPipe = new Dictionary<Vector3i, FluidNet>();

        public static void Ensure()
        {
            if (host != null) return;
            host = new GameObject("ForgedInAshes.FluidTicker");
            Object.DontDestroyOnLoad(host);
            host.AddComponent<FluidTicker>();
        }

        void Update()
        {
            GameManager gm = GameManager.Instance;
            World world = gm == null ? null : gm.World;
            if (world == null) return;
            if (!SingletonMonoBehaviour<ConnectionManager>.Instance.IsServer) return;
            if (Time.time < next) return;
            next = Time.time + Fluids.TickSeconds;
            FluidStore.EnsureLoaded();
            Tick(world, Fluids.TickSeconds);
            if (Time.time >= nextSave) { nextSave = Time.time + 30f; FluidStore.Save(); }
        }

        void OnApplicationQuit()
        {
            FluidStore.Save();
        }

        static bool Loaded(World world, Vector3i p)
        {
            return world.GetChunkFromWorldPos(p) != null;   // null while that chunk is not loaded
        }

        static void Tick(World world, float dt)
        {
            // drop devices whose block is gone
            List<Vector3i> gone = new List<Vector3i>();
            foreach (Vector3i p in FluidStore.Devices)
            {
                if (!Loaded(world, p)) continue;
                BlockValue bv = world.GetBlock(p);
                if (Fluids.Kind(bv.Block) == FluidKind.None || bv.ischild) gone.Add(p);
            }
            foreach (Vector3i p in gone) FluidStore.Unregister(p);

            // 1. production of this tick
            Dictionary<FluidPort, float> offer = new Dictionary<FluidPort, float>();
            Dictionary<FluidPort, float> demand = new Dictionary<FluidPort, float>();
            Dictionary<FluidPort, float> offerBar = new Dictionary<FluidPort, float>();
            List<FluidPort> tankPorts = new List<FluidPort>();
            List<FluidPort> readers = new List<FluidPort>();
            foreach (Vector3i p in FluidStore.Devices)
            {
                if (!Loaded(world, p)) continue;
                BlockValue bv = world.GetBlock(p);
                FluidKind k = Fluids.Kind(bv.Block);
                FluidState s = FluidStore.Get(p);
                s.LastFlow = 0f;
                if (k == FluidKind.Tapper) FluidControl.TapperProduce(world, p, bv, s, dt);
                List<FluidPort> devPorts = Fluids.Ports(world, p);
                int metalOuts = 0;
                if (k == FluidKind.Smelter)
                    foreach (FluidPort port in devPorts) if (Fluids.PortConnected(world, port)) metalOuts++;
                foreach (FluidPort port in devPorts)
                {
                    switch (k)
                    {
                        case FluidKind.Smelter:
                            // the metal it holds, shared among the sides that have a chute
                            if (s.Amount > 0.01f && s.Fluid.Length > 0 && metalOuts > 0 && Fluids.PortConnected(world, port))
                                offer[port] = s.Amount / metalOuts;
                            break;
                        case FluidKind.Caster:
                            demand[port] = MetalWorks.CasterDemand(world, p, bv, s, dt);
                            break;
                        case FluidKind.Processor:
                            if (port.Out) { offer[port] = ProcessMachine.Offer(port, s); offerBar[port] = Fluids.Prop(bv.Block, "FeOutBar", 2f); }
                            else demand[port] = ProcessMachine.Demand(world, p, bv, s, port);
                            break;
                        case FluidKind.Valve:
                            if (port.Out) { offer[port] = FluidControl.ValveOffer(world, p, bv, s, dt); offerBar[port] = s.OutBar; }
                            else demand[port] = FluidControl.ValveDemand(world, p, bv, s, dt);
                            break;
                        case FluidKind.Gauge:
                            readers.Add(port);
                            break;
                        case FluidKind.Boiler:
                            if (port.Out) { offer[port] = s.Steam; offerBar[port] = Fluids.Prop(bv.Block, "FeOutBar", 4f); }
                            else demand[port] = SteamPlant.BoilerDemand(bv, s);
                            break;
                        case FluidKind.Turbine:
                            if (port.Out) { offer[port] = s.Steam; offerBar[port] = 1f; }
                            else demand[port] = SteamPlant.TurbineDemand(bv, s);
                            break;
                        case FluidKind.Burner:
                            demand[port] = FluidControl.BurnerDemand(bv, s, dt);
                            break;
                        case FluidKind.Tapper:
                        case FluidKind.TowerSection:
                            if (s.Amount > 0.01f && s.Fluid.Length > 0) { offer[port] = s.Amount; offerBar[port] = 1.5f; }
                            break;
                        case FluidKind.MechPump:
                        case FluidKind.ElecPump:
                            offer[port] = PumpRate(world, p, bv, s) * dt / 60f;
                            break;
                        case FluidKind.Condenser:
                            if (port.Out) offer[port] = s.Steam;   // water condensed earlier, waiting to leave
                            else demand[port] = CondenserIntake(world, p, bv, s) * dt / 60f;
                            break;
                        case FluidKind.SteamEngine:
                            if (port.Out) { offer[port] = s.Steam; offerBar[port] = Fluids.Prop(bv.Block, "FeOutBar", 2f); }
                            else demand[port] = Mathf.Max(0f, Fluids.Prop(bv.Block, "FeWaterTank", 2000f) - s.Amount);
                            break;
                        case FluidKind.Tank:
                        case FluidKind.GasTank:
                            tankPorts.Add(port);
                            break;
                        case FluidKind.Filler:
                            if (s.Amount > 0.01f && s.Fluid.Length > 0) offer[port] = s.Amount;
                            break;
                        case FluidKind.Bottler:
                        case FluidKind.Refinery:
                            demand[port] = Mathf.Max(0f, Fluids.Prop(bv.Block, "FeFluidBuffer", 100f) - s.Amount);
                            break;
                    }
                }
            }

            // 2. networks: group every port with the network in front of it
            NetByPipe.Clear();
            HashSet<FluidPort> done = new HashSet<FluidPort>();
            List<FluidPort> all = new List<FluidPort>(offer.Keys);
            all.AddRange(demand.Keys);
            all.AddRange(tankPorts);
            all.AddRange(readers);
            // our port objects by identity (Ports() builds new objects each call, so the net's ports are other objects)
            Dictionary<PortKey, FluidPort> byKey = new Dictionary<PortKey, FluidPort>();
            Dictionary<FluidPort, int> order = new Dictionary<FluidPort, int>();
            foreach (FluidPort a in all)
            {
                PortKey ak = new PortKey(a);
                if (!byKey.ContainsKey(ak)) byKey[ak] = a;
                if (!order.ContainsKey(a)) order[a] = order.Count;
            }
            foreach (FluidPort start in all)
            {
                if (done.Contains(start)) continue;
                FluidNet net = Fluids.NetFrom(world, start, null);
                // match the ports of the net to our port objects (was a scan of every port for every net port)
                List<FluidPort> members = new List<FluidPort>();
                HashSet<FluidPort> inNet = new HashSet<FluidPort>();
                foreach (FluidPort b in net.Ports)
                {
                    FluidPort a;
                    if (byKey.TryGetValue(new PortKey(b), out a) && inNet.Add(a)) members.Add(a);
                }
                // same order as before (the order of "all"): the share-out in Flow follows it
                members.Sort(delegate (FluidPort x, FluidPort y) { return order[x].CompareTo(order[y]); });
                if (inNet.Add(start)) members.Add(start);
                foreach (FluidPort m in members) done.Add(m);
                foreach (Vector3i pp in net.Pipes) NetByPipe[pp] = net;
                Flow(world, net, members, offer, demand, offerBar, dt);
            }

            // 3. joined tanks share their content (communicating vessels, Create-like multi-block tanks); so do the
            // drums of one boiler
            FluidControl.EqualizeTanks(world);
            SteamPlant.EqualizeBoilers(world);

            // 4. the machines turn what they received into their products (and engines run)
            foreach (Vector3i p in FluidStore.Devices)
            {
                if (!Loaded(world, p)) continue;
                BlockValue bv = world.GetBlock(p);
                FluidKind k = Fluids.Kind(bv.Block);
                if (k == FluidKind.SteamEngine) SteamEngine.Run(world, p, bv, FluidStore.Get(p), dt);
                else if (k == FluidKind.Burner) FluidControl.BurnerTick(world, p, bv, FluidStore.Get(p), dt);
                else if (k == FluidKind.Gauge) FluidControl.GaugeTick(world, p, bv, FluidStore.Get(p));
                else if (k == FluidKind.Boiler) SteamPlant.BoilerTick(world, p, bv, FluidStore.Get(p), dt);
                else if (k == FluidKind.Turbine) SteamPlant.TurbineTick(world, p, bv, FluidStore.Get(p), dt);
            }
            FluidStore.MarkDirty();
        }

        static float PumpRate(World world, Vector3i p, BlockValue bv, FluidState s)
        {
            float rate = Fluids.Prop(bv.Block, "FeFluidRate", 100f);
            int need = (int)Fluids.Prop(bv.Block, "FeIntakeWater", 3f);
            if (Fluids.IntakeWater(world, p, bv) < need)
            {
                s.Note = "intake";
                return 0f;
            }
            if (Fluids.Kind(bv.Block) == FluidKind.MechPump)
            {
                TorqueNet net = Kinetic.Get(world, p);
                if (net == null || !net.Running || !net.Machines.ContainsKey(p)) { s.Note = "torque"; return 0f; }
                s.Note = "";
                return rate * net.MachineSpeed(p);
            }
            TileEntityPowered te = world.GetTileEntity(p) as TileEntityPowered;
            if (te == null || !te.IsPowered) { s.Note = "power"; return 0f; }
            s.Note = "";
            return rate;
        }

        static float CondenserIntake(World world, Vector3i p, BlockValue bv, FluidState s)
        {
            TileEntityPowered te = world.GetTileEntity(p) as TileEntityPowered;
            if (te == null || !te.IsPowered) { s.Note = "power"; return 0f; }
            s.Note = "";
            float cap = Fluids.Prop(bv.Block, "FeFluidBuffer", 200f);
            if (s.Steam >= cap) return 0f;   // its water outlet is backed up
            return Fluids.Prop(bv.Block, "FeFluidRate", 120f);
        }

        // Move fluid inside one network.
        // D12: gases have a pressure. With gas tanks in the network it is what they hold / their volume at 1 bar; without,
        // it is the pressure the sources push at, lower when they cannot cover the demand. Sources stop filling the
        // tanks at their own pressure; demands that ask a minimum pressure get nothing below it; a network above what
        // its weakest pipe stands (FeMaxBar) leaks.
        static void Flow(World world, FluidNet net, List<FluidPort> members, Dictionary<FluidPort, float> offer,
                         Dictionary<FluidPort, float> demand, Dictionary<FluidPort, float> offerBar, float dt)
        {
            // which fluid?
            HashSet<string> fluids = new HashSet<string>();
            List<FluidPort> offers = new List<FluidPort>(), demands = new List<FluidPort>(), tanks = new List<FluidPort>();
            List<FluidPort> gauges = new List<FluidPort>();
            foreach (FluidPort m in members)
            {
                FluidKind mk = Fluids.Kind(world.GetBlock(m.Owner).Block);
                if (mk == FluidKind.Tank || mk == FluidKind.GasTank)
                {
                    if (m.Out) tanks.Add(m);   // one entry per tank side is enough (Out ports)
                    FluidState ts = FluidStore.Get(m.Owner);
                    if (ts.Amount > 0.01f && ts.Fluid.Length > 0) fluids.Add(ts.Fluid);
                    continue;
                }
                if (mk == FluidKind.Gauge) { gauges.Add(m); continue; }
                float v;
                if (offer.TryGetValue(m, out v)) { offers.Add(m); if (v > 0.0001f && m.Fluid.Length > 0) fluids.Add(m.Fluid); }
                if (demand.ContainsKey(m)) demands.Add(m);
            }
            // a tank reached through several sides counts once
            List<FluidPort> uniqueTanks = new List<FluidPort>();
            HashSet<Vector3i> tankOwners = new HashSet<Vector3i>();
            foreach (FluidPort t in tanks) if (tankOwners.Add(t.Owner)) uniqueTanks.Add(t);

            foreach (Vector3i pp in net.Pipes) net.MaxBar = Mathf.Min(net.MaxBar, Fluids.Prop(world.GetBlock(pp).Block, "FeMaxBar", 4f));

            if (fluids.Count > 1) { net.Blocked = true; Readers(world, gauges, net); return; }
            string fluid = fluids.Count == 1 ? new List<string>(fluids)[0] : "";
            net.Fluid = fluid;
            bool gas = Fluids.IsGas(fluid);

            // tanks that can take this fluid: liquid tanks hold liquids, gas tanks gases
            List<FluidPort> useTanks = new List<FluidPort>();
            float vol = 0f, stored = 0f;
            foreach (FluidPort t in uniqueTanks)
            {
                FluidKind tk = Fluids.Kind(world.GetBlock(t.Owner).Block);
                if (fluid.Length > 0 && (tk == FluidKind.GasTank) != gas) continue;
                FluidState ts = FluidStore.Get(t.Owner);
                if (ts.Amount > 0.01f && ts.Fluid != fluid) continue;
                useTanks.Add(t);
                vol += Fluids.Prop(world.GetBlock(t.Owner).Block, "FeFluidCapacity", 4000f);
                stored += ts.Amount;
            }

            float O = 0f, srcBar = 0f;
            foreach (FluidPort o in offers)
                if (o.Fluid == fluid || fluid.Length == 0)
                {
                    O += offer[o];
                    float b;
                    if (offer[o] > 0.0001f && offerBar.TryGetValue(o, out b)) srcBar = Mathf.Max(srcBar, b);
                }
            if (gas && srcBar <= 0f && O > 0f) srcBar = 1f;

            // demand that wants this fluid (pressure checked below)
            float Dall = 0f;
            List<FluidPort> want0 = new List<FluidPort>();
            float bl;
            foreach (FluidPort d in demands)
                if (d.Fluid == fluid || fluid.Length == 0 ||
                    (d.Accepts != null ? (d.Fluid.Length == 0 && (System.Array.IndexOf(d.Accepts, fluid) >= 0 || System.Array.IndexOf(d.Accepts, "*") >= 0))
                                       : (d.Fluid.Length == 0 && Fluids.ItemOfFluid(fluid, out bl) != null)))
                { Dall += demand[d]; want0.Add(d); }

            float P = 0f;
            if (gas)
            {
                if (vol > 0f) P = stored / vol;
                else P = Dall > 0f ? srcBar * Mathf.Clamp01(O / Dall) : (O > 0f ? srcBar : 0f);
            }
            net.Pressure = P;
            net.Volume = vol;

            float D = 0f;
            List<FluidPort> wanted = new List<FluidPort>();
            foreach (FluidPort d in want0)
            {
                FluidState ds = FluidStore.Get(d.Owner);
                ds.InBar = P;
                float need = FluidControl.MinBar(world, d);
                if (gas && need > 0f && P + 0.001f < need) { ds.Note = "pressure"; continue; }
                D += demand[d];
                wanted.Add(d);
            }

            float direct = Mathf.Min(O, D);
            float spareOffer = O - direct, missing = D - direct;

            // tanks: absorb the spare offer (gas: only up to the sources' pressure and the tank's rating), cover the
            // missing demand
            float tankIn = 0f, tankOut = 0f;
            if (fluid.Length > 0)
            {
                foreach (FluidPort t in useTanks)
                {
                    FluidState ts = FluidStore.Get(t.Owner);
                    Block tb = world.GetBlock(t.Owner).Block;
                    float cap = Fluids.Prop(tb, "FeFluidCapacity", 4000f);
                    if (gas) cap *= Mathf.Min(srcBar > 0f ? srcBar : P, Fluids.Prop(tb, "FeMaxBar", 10f));
                    if (spareOffer > 0f)
                    {
                        float put = Mathf.Min(spareOffer, cap - ts.Amount);
                        if (put > 0f) { ts.Amount += put; ts.Fluid = fluid; spareOffer -= put; tankIn += put; }
                    }
                    if (missing > 0f && ts.Amount > 0f)
                    {
                        float take = Mathf.Min(missing, ts.Amount);
                        ts.Amount -= take; missing -= take; tankOut += take;
                        if (ts.Amount <= 0.01f) { ts.Amount = 0f; ts.Fluid = ""; }
                    }
                }
            }

            // what the offers really gave and the demands really got
            float given = direct + tankIn;            // taken from the offers
            float received = direct + tankOut;        // delivered to the demands
            if (gas && P > net.MaxBar + 0.01f)
            {
                // above what the pipes stand: it leaks (a fifth of what moves and 2% of the tanks per tick)
                net.Leak = true;
                received *= 0.8f;
                foreach (FluidPort t in useTanks)
                {
                    FluidState ts = FluidStore.Get(t.Owner);
                    ts.Amount *= 0.98f;
                }
            }
            foreach (FluidPort o in offers)
            {
                if (O <= 0f) break;
                float share = offer[o] / O * given;
                Took(world, o, share, dt);
            }
            foreach (FluidPort d in wanted)
            {
                if (D <= 0f) break;
                float share = demand[d] / D * received;
                Got(world, d, share, dt, fluid);
            }
            net.FlowPerMin = Mathf.Max(given, received) / dt * 60f;
            stored = 0f;
            foreach (FluidPort t in useTanks) stored += FluidStore.Get(t.Owner).Amount;
            net.Stored = stored;
            if (gas && vol > 0f) net.Pressure = stored / vol;
            Readers(world, gauges, net);
        }

        // gauges read the network they are on
        static void Readers(World world, List<FluidPort> gauges, FluidNet net)
        {
            foreach (FluidPort g in gauges)
            {
                FluidState gs = FluidStore.Get(g.Owner);
                gs.Fluid = net.Fluid;
                gs.Bar = net.Pressure;
                gs.LastFlow = net.FlowPerMin;
                gs.Amount = net.Stored;
                gs.Steam = net.Volume;
                gs.Note = net.Blocked ? "blocked" : net.Leak ? "leak" : "";
            }
        }

        // An offer port gave `amount` litres.
        static void Took(World world, FluidPort o, float amount, float dt)
        {
            FluidState s = FluidStore.Get(o.Owner);
            FluidKind k = Fluids.Kind(world.GetBlock(o.Owner).Block);
            if (k == FluidKind.Condenser || k == FluidKind.SteamEngine || k == FluidKind.Boiler || k == FluidKind.Turbine) s.Steam = Mathf.Max(0f, s.Steam - amount);
            else if (k == FluidKind.Filler || k == FluidKind.Smelter || k == FluidKind.Tapper || k == FluidKind.TowerSection
                     || k == FluidKind.Valve)
            {
                s.Amount = Mathf.Max(0f, s.Amount - amount);
                if (s.Amount <= 0.01f) { s.Amount = 0f; s.Fluid = ""; }
            }
            else if (k == FluidKind.Processor) ProcessMachine.Took(o, s, amount);
            s.LastFlow += amount / dt * 60f;
        }

        // A demand port received `amount` litres.
        static void Got(World world, FluidPort d, float amount, float dt, string fluid)
        {
            BlockValue bv = world.GetBlock(d.Owner);
            FluidState s = FluidStore.Get(d.Owner);
            FluidKind k = Fluids.Kind(bv.Block);
            if (k == FluidKind.SteamEngine || k == FluidKind.Boiler) { s.Amount += amount; s.Fluid = Fluids.Water; }
            else if (k == FluidKind.Turbine) { s.Amount += amount; s.Fluid = Fluids.Steam; s.LastFlow += amount / dt * 60f; }
            else if (k == FluidKind.Processor)
            {
                if (amount > 0f && fluid.Length > 0) { ProcessMachine.Got(d, s, amount, fluid); s.LastFlow += amount / dt * 60f; }
            }
            else if (k == FluidKind.Caster || k == FluidKind.Valve)
            {
                if (amount > 0f && fluid.Length > 0) { s.Amount += amount; s.Fluid = fluid; s.LastFlow += amount / dt * 60f; }
                if (k == FluidKind.Valve) FluidControl.ValveGot(world, d.Owner, bv, s);
            }
            else if (k == FluidKind.Burner)
            {
                if (amount > 0f) { FluidControl.BurnerGot(bv, s, amount); s.LastFlow += amount / dt * 60f; }
            }
            else if (k == FluidKind.Bottler || k == FluidKind.Refinery)
            {
                if (amount > 0f && fluid.Length > 0) { s.Amount += amount; s.Fluid = fluid; s.LastFlow += amount / dt * 60f; }
            }
            else if (k == FluidKind.Condenser)
            {
                // condense now: water waits in the buffer (s.Steam) to leave through the outlet next tick
                s.Steam += amount * Fluids.Prop(bv.Block, "FeCondenseRatio", 0.9f);
                s.LastFlow += amount / dt * 60f;
            }
        }
    }
    // ------------------------------------------------------------------ pipe and tank blocks
    [UnityEngine.Scripting.Preserve]
    public class BlockFeFluid : Block
    {
        public override void Init()
        {
            base.Init();
            FluidTicker.Ensure();
            MotorSocketMarker.Ensure();
        }

        public override void OnBlockAdded(WorldBase _world, Chunk _chunk, Vector3i _blockPos, BlockValue _blockValue,
                                          PlatformUserIdentifierAbs _addedByPlayer)
        {
            base.OnBlockAdded(_world, _chunk, _blockPos, _blockValue, _addedByPlayer);
            if (!_blockValue.ischild && !Fluids.IsConduit(Fluids.Kind(this))) FluidStore.Register(_blockPos);
        }

        public override void OnBlockRemoved(WorldBase _world, Chunk _chunk, Vector3i _blockPos, BlockValue _blockValue)
        {
            base.OnBlockRemoved(_world, _chunk, _blockPos, _blockValue);
            if (!_blockValue.ischild) FluidStore.Unregister(_blockPos);
        }

        public override void OnBlockEntityTransformAfterActivated(WorldBase _world, Vector3i _blockPos,
                                                                  BlockValue _blockValue, BlockEntityData _ebcd)
        {
            base.OnBlockEntityTransformAfterActivated(_world, _blockPos, _blockValue, _ebcd);
            PipeArms.Attach(_ebcd, _blockPos);
            if (Fluids.Kind(this) == FluidKind.Caster) CasterVisual.Attach(_ebcd, _blockPos);
            MachineItems.Attach(_ebcd, _blockPos, this);
        }

        public override bool HasBlockActivationCommands(WorldBase _world, BlockValue _blockValue, Vector3i _blockPos,
                                                        EntityAlive _entityFocusing)
        {
            return true;
        }

        public override BlockActivationCommand[] GetBlockActivationCommands(WorldBase _world, BlockValue _blockValue,
                                                                           Vector3i _blockPos,
                                                                           EntityAlive _entityFocusing)
        {
            BlockActivationCommand[] r = Commands(_world, _blockPos);
            RecipeBook.AddCommand(this, ref r);
            FeUi.AddNetCommand(_entityFocusing, ref r);
            return r;
        }

        BlockActivationCommand[] Commands(WorldBase _world, Vector3i _blockPos)
        {
            BlockActivationCommand take = new BlockActivationCommand("take", "hand", Pickup.CanBuildHere(_world, _blockPos), false, null);
            FluidKind k = Fluids.Kind(this);
            if (k == FluidKind.Valve || k == FluidKind.Gauge)
                return new BlockActivationCommand[] { new BlockActivationCommand(FeUi.ConfigCommand, "tool", true, false, null), take };
            if (k == FluidKind.Burner)
                return new BlockActivationCommand[] { new BlockActivationCommand("fe_put", "loot_sort", true, false, null), take };
            if (k == FluidKind.Filler)
                return new BlockActivationCommand[] { new BlockActivationCommand("fe_pour", "loot_sort", true, false, null), take };
            if (k == FluidKind.Bottler)
                return new BlockActivationCommand[] { new BlockActivationCommand("fe_bottle", "loot_sort", true, false, null), take };
            if (k == FluidKind.Processor) return ProcessMachine.Commands(take);
            if (k == FluidKind.Caster)
                return new BlockActivationCommand[]
                {
                    new BlockActivationCommand("fe_cast_take", "loot_sort", true, false, null),
                    new BlockActivationCommand("fe_mold", "tool", true, false, null), take
                };
            return new BlockActivationCommand[] { take };
        }

        public override bool OnBlockActivated(string _commandName, WorldBase _world, Vector3i _blockPos,
                                              BlockValue _blockValue, EntityPlayerLocal _player)
        {
            World w = _world as World;
            if (_commandName == RecipeBook.Command)
            {
                RecipeBook.Open(this, _player);
                return true;
            }
            if (_commandName == "fe_pour" && w != null)
            {
                ItemStack held = _player.inventory.holdingItemStack;
                if (held == null || held.IsEmpty()) return true;
                ItemStack copy = held.Clone();
                int before = copy.count;
                FluidDevices.Pour(w, _blockPos, copy);
                int used = before - copy.count;
                if (used > 0)
                {
                    ItemStack left = held.Clone();
                    left.count -= used;
                    _player.inventory.SetItem(_player.inventory.holdingItemIdx, left.count > 0 ? left : ItemStack.Empty.Clone());
                }
                GameManager.ShowTooltip(_player, used > 0 ? string.Format(Kinetic.Text("fePoured", "Poured {0}"), used)
                                                          : Kinetic.Text("fePourNo", "It does not take this (or it is full)"), false, false, 0f);
                return true;
            }
            if (_commandName == "fe_bottle" && w != null)
            {
                ItemStack st = FluidDevices.Bottle(w, _blockPos, 1000);
                if (st != null && !st.IsEmpty() && !_player.bag.AddItem(st)) GameManager.Instance.ItemDropServer(st, _player.GetPosition(), Vector3.zero, -1, 60f, false);
                GameManager.ShowTooltip(_player, st == null ? Kinetic.Text("feBottleNo", "Not enough fluid for one item yet")
                    : string.Format(Kinetic.Text("feBottled", "Took {0}x {1}"), st.count, st.itemValue.ItemClass.GetLocalizedItemName()), false, false, 0f);
                return true;
            }
            if (w != null && FeUi.HandleCommand(_commandName, w, _blockPos, _blockValue, _player)) return true;
            if (Fluids.Kind(this) == FluidKind.Processor && ProcessMachine.IsCommand(_commandName) && w != null)
            {
                string pm = ProcessMachine.Activate(w, Fluids.ParentOf(w, _blockPos, _blockValue), _commandName, _player);
                if (pm != null) GameManager.ShowTooltip(_player, pm, false, false, 0f);
                return true;
            }
            if (Fluids.Kind(this) == FluidKind.Burner && _commandName == "fe_put" && w != null)
            {
                GameManager.ShowTooltip(_player, FluidControl.BurnerPutHeld(w, _blockPos, _player), false, false, 0f);
                return true;
            }
            if ((_commandName == "fe_mold" || _commandName == "fe_cast_take") && w != null)
            {
                GameManager.ShowTooltip(_player, MetalWorks.Activate(w, _blockPos, _commandName, _player), false, false, 0f);
                return true;
            }
            if (_commandName != "take") return false;
            float delay = Properties != null && Properties.Contains("TakeDelay") ? Properties.GetFloat("TakeDelay") : 2f;
            takeItemWithTimer(_blockPos, _blockValue, _player, delay);
            return true;
        }

        public override string GetActivationText(WorldBase _world, BlockValue _blockValue, Vector3i _blockPos,
                                                 EntityAlive _entityFocusing)
        {
            FluidKind k = Fluids.Kind(this);
            string hint = k == FluidKind.Filler ? Kinetic.Text("feHintPour", "{0} pour the item in your hand - hold {0}: take")
                        : k == FluidKind.Bottler ? Kinetic.Text("feHintBottle", "{0} take the bottled items - hold {0}: take")
                        : k == FluidKind.Processor ? Kinetic.Text("feHintPanel", "{0} panel - hold {0}: put, recipe, take")
                        : k == FluidKind.Valve || k == FluidKind.Gauge ? Kinetic.Text("feHintConfig", "{0} settings - hold {0}: take")
                        : k == FluidKind.Burner ? Kinetic.Text("feHintBurner", "{0} put the fuel in your hand - hold {0}: take")
                        : k == FluidKind.Caster ? Kinetic.Text("feHintCaster", "{0} take the casts - hold {0}: change the mold (the one in your hand) or take")
                        : Kinetic.Text("feHintTake", "Hold {0} to take");
            return KineticLookController.Escape(FluidText.Describe(_blockPos, _blockValue, true)) + "\n" + hint;
        }
    }

    // ------------------------------------------------------------------ readouts
    public static class FluidText
    {
        public static string Describe(Vector3i pos, BlockValue bv, bool withName)
        {
            World world = GameManager.Instance == null ? null : GameManager.Instance.World;
            if (world == null) return "";
            FluidStore.EnsureLoaded();
            Vector3i owner = Fluids.ParentOf(world, pos, bv);
            FluidKind k = Fluids.Kind(bv.Block);
            string name = withName ? bv.Block.GetLocalizedBlockName() : "";
            FluidState s = FluidStore.Get(owner);
            switch (k)
            {
                case FluidKind.Pipe:
                case FluidKind.Chute:
                {
                    FluidNet net;
                    if (!FluidTicker.NetByPipe.TryGetValue(pos, out net))
                        return (name + "\n" + Fluids.Text("feFluidIdle", "No flow")).Trim();
                    if (net.Blocked)
                        return (name + "\n" + Fluids.Text("feFluidBlocked", "BLOCKED: two different fluids in this pipe")).Trim();
                    {
                        string t = name + "\n" + string.Format(Fluids.Text("feFluidFlow", "{0}: {1} L/min"),
                            Fluids.FluidName(net.Fluid), Mathf.RoundToInt(net.FlowPerMin));
                        if (Fluids.IsGas(net.Fluid))
                            t += "\n" + string.Format(Fluids.Text("fePipeBar", "Pressure {0} bar (this pipe stands {1})"),
                                net.Pressure.ToString("0.0", CultureInfo.InvariantCulture), Mathf.RoundToInt(Fluids.Prop(bv.Block, "FeMaxBar", 4f)));
                        if (net.Leak) t += "\n" + Fluids.Text("fePipeLeak", "LEAKING: the pressure is above what the pipes stand (use High Pressure Pipes)");
                        return t.Trim();
                    }
                }
                case FluidKind.Filler:
                case FluidKind.Bottler:
                case FluidKind.Refinery:
                {
                    string t = name + "\n" + string.Format(Fluids.Text("feFluidStored", "{0}: {1} / {2} L"),
                        Fluids.FluidName(s.Fluid), Mathf.RoundToInt(s.Amount),
                        Mathf.RoundToInt(Fluids.Prop(bv.Block, "FeFluidBuffer", k == FluidKind.Filler ? 1000f : 100f)));
                    if (k == FluidKind.Filler) t += "\n" + Fluids.Text("feFillerInfo", "Takes Oil, Gas Cans and Lubricant (belt, funnel or hand) and pours them out of its front");
                    else if (k == FluidKind.Bottler) t += "\n" + Fluids.Text("feBottlerInfo", "Takes fluid at its back and gives items: on the belt in front, or in your hand");
                    else t += "\n" + Fluids.Text("feRefineryFluidInfo", "Fluid in at its back: used as ingredients of its fixed recipe");
                    return t.Trim();
                }
                case FluidKind.Caster:
                    return (name + "\n" + MetalWorks.DescribeCaster(world, owner, bv, s)).Trim();
                case FluidKind.Processor:
                    return (name + "\n" + ProcessMachine.Describe(world, owner, bv, s)).Trim();
                case FluidKind.Smelter:
                {
                    string t = name + "\n" + MetalWorks.DescribeSmelter(world, owner);
                    if (s.Note == "power") t += "\n" + Fluids.Text("feFluidNoPower", "No power: wire it to a power source");
                    return t.Trim();
                }
                case FluidKind.GasTank:
                    {
                        float cap = Fluids.Prop(bv.Block, "FeFluidCapacity", 2000f);
                        return (name + "\n" + string.Format(Fluids.Text("feGasStored", "{0}: {1} L = {2} bar (max {3})"),
                            Fluids.FluidName(s.Fluid), Mathf.RoundToInt(s.Amount),
                            (s.Amount / Mathf.Max(1f, cap)).ToString("0.0", CultureInfo.InvariantCulture),
                            Mathf.RoundToInt(Fluids.Prop(bv.Block, "FeMaxBar", 10f)))).Trim();
                    }
                case FluidKind.Valve:
                case FluidKind.Gauge:
                case FluidKind.Burner:
                case FluidKind.Tapper:
                case FluidKind.TowerSection:
                    return (name + "\n" + FluidControl.Describe(world, owner, bv, s)).Trim();
                case FluidKind.Boiler:
                case FluidKind.Turbine:
                    return (name + "\n" + SteamPlant.Describe(world, owner, bv, s)).Trim();
                case FluidKind.Tank:
                    return (name + "\n" + string.Format(Fluids.Text("feFluidStored", "{0}: {1} / {2} L"),
                        Fluids.FluidName(s.Fluid), Mathf.RoundToInt(s.Amount),
                        Mathf.RoundToInt(Fluids.Prop(bv.Block, "FeFluidCapacity", 4000f)))).Trim();
                case FluidKind.MechPump:
                case FluidKind.ElecPump:
                {
                    string t = name + "\n" + string.Format(Fluids.Text("feFluidPumping", "Pumping {0}: {1} L/min"),
                        Fluids.FluidName(Fluids.Water), Mathf.RoundToInt(s.LastFlow));
                    if (s.Note == "intake") t += "\n" + Fluids.Text("feFluidNoIntake", "No water at the intake (the back side): put it in a river or a lake");
                    else if (s.Note == "torque") t += "\n" + Fluids.Text("feFluidNoTorque", "No torque on its shaft");
                    else if (s.Note == "power") t += "\n" + Fluids.Text("feFluidNoPower", "No power: wire it to a power source");
                    return t.Trim();
                }
                case FluidKind.Condenser:
                {
                    string t = name + "\n" + string.Format(Fluids.Text("feFluidCondensing", "Condensing: {0} L/min of steam"),
                        Mathf.RoundToInt(s.LastFlow));
                    float cap = Fluids.Prop(bv.Block, "FeFluidBuffer", 200f);
                    t += "\n" + string.Format(Fluids.Text("feCondenserWater", "Condensed water waiting: {0} / {1} L"),
                        Mathf.RoundToInt(s.Steam), Mathf.RoundToInt(cap));
                    if (s.Note == "power") t += "\n" + Fluids.Text("feFluidNoPower", "No power: wire it to a power source");
                    else if (s.Steam >= cap)
                        t += "\n" + Fluids.Text("feCondenserFull", "FULL: the water outlet (front, bottom) has nowhere to go, so no steam is taken in");
                    return t.Trim();
                }
                case FluidKind.SteamEngine:
                    return (name + "\n" + string.Format(Fluids.Text("feSteamTanks", "Water {0} / {1} L - steam out {2} L/min - load {3}%"),
                        Mathf.RoundToInt(s.Amount), Mathf.RoundToInt(Fluids.Prop(bv.Block, "FeWaterTank", 2000f)),
                        Mathf.RoundToInt(s.LastFlow), Mathf.RoundToInt(SteamEngine.LastLoad(owner) * 100f))).Trim();
            }
            return "";
        }
    }

    // Electric pump and condenser (Class Powered): BlockPowered does not override OnBlockAdded (IL 3.4.0 b10), so
    // the registration hooks the base Block.OnBlockAdded; BlockFeFluid and BlockPowerSource register themselves.
    [HarmonyPatch(typeof(Block), "OnBlockAdded")]
    public static class Patch_Block_OnBlockAdded_Fluid
    {
        public static void Postfix(Block __instance, Vector3i _blockPos, BlockValue _blockValue)
        {
            if (_blockValue.ischild || __instance is BlockFeFluid || __instance is BlockPowerSource) return;
            if (Fluids.Kind(__instance) != FluidKind.None) FluidStore.Register(_blockPos);
        }
    }

    [HarmonyPatch(typeof(BlockPowered), "OnBlockRemoved")]
    public static class Patch_BlockPowered_OnBlockRemoved_Fluid
    {
        public static void Postfix(BlockPowered __instance, Vector3i _blockPos, BlockValue _blockValue)
        {
            if (!_blockValue.ischild && Fluids.Kind(__instance) != FluidKind.None) FluidStore.Unregister(_blockPos);
        }
    }

    [HarmonyPatch(typeof(BlockPowerSource), "OnBlockAdded")]
    public static class Patch_BlockPowerSource_OnBlockAdded_Fluid
    {
        public static void Postfix(BlockPowerSource __instance, Vector3i _blockPos, BlockValue _blockValue)
        {
            if (!_blockValue.ischild && Fluids.Kind(__instance) != FluidKind.None) FluidStore.Register(_blockPos);
        }
    }

    [HarmonyPatch(typeof(BlockPowerSource), "OnBlockRemoved")]
    public static class Patch_BlockPowerSource_OnBlockRemoved_Fluid
    {
        public static void Postfix(BlockPowerSource __instance, Vector3i _blockPos, BlockValue _blockValue)
        {
            if (!_blockValue.ischild && Fluids.Kind(__instance) != FluidKind.None) FluidStore.Unregister(_blockPos);
        }
    }

    [HarmonyPatch(typeof(BlockPowered), "GetActivationText")]
    public static class Patch_BlockPowered_ActivationText_Fluid
    {
        public static void Postfix(BlockPowered __instance, BlockValue _blockValue, Vector3i _blockPos, ref string __result)
        {
            if (Fluids.Kind(__instance) == FluidKind.None) return;
            string d = KineticLookController.Escape(FluidText.Describe(_blockPos, _blockValue, true));
            __result = string.IsNullOrEmpty(__result) ? d : __result + "\n" + d;
        }
    }

    // save with the world
    [HarmonyPatch(typeof(GameManager), "SaveWorld")]
    public static class Patch_GameManager_SaveWorld_Fluids
    {
        public static void Postfix()
        {
            FluidStore.MarkDirty();
            FluidStore.Save();
        }
    }

    [HarmonyPatch(typeof(GameManager), "SaveAndCleanupWorld")]
    public static class Patch_GameManager_SaveAndCleanupWorld_Fluids
    {
        public static void Prefix()
        {
            FluidStore.MarkDirty();
            FluidStore.Save();
        }
    }

    // ------------------------------------------------------------------ pipe model arms
    // Pipe models carry six arms named FeArm_PX, FeArm_NX, FeArm_PY, FeArm_NY, FeArm_PZ, FeArm_NZ (local +/- axes of
    // the model). Each is shown only when that side connects to a pipe or to a device port.
    public class PipeArms : MonoBehaviour
    {
        static readonly string[] Names = { "FeArm_PX", "FeArm_NX", "FeArm_PY", "FeArm_NY", "FeArm_PZ", "FeArm_NZ" };
        static readonly Vector3[] Local =
        {
            Vector3.right, Vector3.left, Vector3.up, Vector3.down, Vector3.forward, Vector3.back
        };

        Vector3i pos;
        readonly Transform[] arms = new Transform[6];
        float next;
        bool reported;

        public static void Attach(BlockEntityData ebcd, Vector3i pos)
        {
            if (ebcd == null || ebcd.transform == null || GameManager.IsDedicatedServer) return;
            PipeArms a = ebcd.transform.GetComponent<PipeArms>();
            if (a == null) a = ebcd.transform.gameObject.AddComponent<PipeArms>();
            a.pos = pos;
            a.next = 0f;
            a.reported = false;
            for (int i = 0; i < 6; i++)
            {
                // Blender renames a second "FeArm_PX" in the same .blend (the Metal Chute) to "FeArm_PX.001"
                a.arms[i] = Find(ebcd.transform, Names[i]);
                if (a.arms[i] == null) a.arms[i] = FindPrefix(ebcd.transform, Names[i] + ".");
            }
            // diagnostic (verbose only since 2026-11-24): a pipe next to a device
            World world = GameManager.Instance == null ? null : GameManager.Instance.World;
            if (world != null && ForgedInAshesMod.Verbose)
                for (int i = 0; i < 6; i++)
                {
                    Vector3i n = new Vector3i(pos.x + Dirs6[i].x, pos.y + Dirs6[i].y, pos.z + Dirs6[i].z);
                    FluidKind nk = Fluids.Kind(world.GetBlock(n).Block);
                    if (nk == FluidKind.None || Fluids.IsConduit(nk)) continue;
                    Log.Out(ForgedInAshesMod.LogPrefix + "pipe arms attached at " + pos + " (next to " + world.GetBlock(n).Block.GetBlockName()
                            + " at " + n + ") active=" + ebcd.transform.gameObject.activeInHierarchy
                            + " enabled=" + a.enabled + " arms found=" + Found(a.arms));
                    break;
                }
        }

        static readonly Vector3i[] Dirs6 =
        {
            new Vector3i(1, 0, 0), new Vector3i(-1, 0, 0), new Vector3i(0, 1, 0), new Vector3i(0, -1, 0),
            new Vector3i(0, 0, 1), new Vector3i(0, 0, -1)
        };

        static int Found(Transform[] t)
        {
            int c = 0;
            foreach (Transform x in t) if (x != null) c++;
            return c;
        }

        static Transform Find(Transform t, string n)
        {
            if (t.name == n) return t;
            for (int i = 0; i < t.childCount; i++)
            {
                Transform r = Find(t.GetChild(i), n);
                if (r != null) return r;
            }
            return null;
        }

        static Transform FindPrefix(Transform t, string n)
        {
            if (t.name.StartsWith(n, System.StringComparison.Ordinal)) return t;
            for (int i = 0; i < t.childCount; i++)
            {
                Transform r = FindPrefix(t.GetChild(i), n);
                if (r != null) return r;
            }
            return null;
        }

        void Update()
        {
            if (Time.time < next) return;
            next = Time.time + 0.5f;
            World world = GameManager.Instance == null ? null : GameManager.Instance.World;
            if (world == null) return;
            bool first = !reported && ForgedInAshesMod.Verbose;
            reported = true;
            for (int i = 0; i < 6; i++)
            {
                // the arm's direction in the world (the model may be rotated)
                Vector3 w = transform.TransformDirection(Local[i]);
                Vector3i d = new Vector3i(Mathf.RoundToInt(w.x), Mathf.RoundToInt(w.y), Mathf.RoundToInt(w.z));
                Vector3i n = new Vector3i(pos.x + d.x, pos.y + d.y, pos.z + d.z);
                bool on = Fluids.HasPortAt(world, n, new Vector3i(-d.x, -d.y, -d.z),
                                           Fluids.Kind(world.GetBlock(pos).Block) == FluidKind.Chute);
                if (first)
                {
                    // diagnostic, once per pipe: every arm that faces a device (not a pipe)
                    BlockValue nbv = world.GetBlock(n);
                    FluidKind nk = Fluids.Kind(nbv.Block);
                    if (nk != FluidKind.None && !Fluids.IsConduit(nk))
                        Log.Out(ForgedInAshesMod.LogPrefix + "pipe at " + pos + " faces " + nbv.Block.GetBlockName()
                                + (nbv.ischild ? " (child)" : "") + " at " + n + " via " + Names[i] + " dir " + d
                                + ": port=" + on + " arm=" + (arms[i] == null ? "MISSING" : (arms[i].gameObject.activeSelf ? "shown" : "hidden"))
                                + " modelRot=" + transform.rotation.eulerAngles.ToString("F0"));
                }
                if (arms[i] == null) continue;
                if (arms[i].gameObject.activeSelf != on)
                {
                    arms[i].gameObject.SetActive(on);
                    Block nb = world.GetBlock(n).Block;
                    if (ForgedInAshesMod.Verbose && !Fluids.IsConduit(Fluids.Kind(nb)) && Fluids.Kind(nb) != FluidKind.None)
                        Log.Out(ForgedInAshesMod.LogPrefix + "pipe at " + pos + " arm " + Names[i] + " -> " + n + " ("
                                + nb.GetBlockName() + ") " + (on ? "ON" : "OFF") + " arm world pos "
                                + arms[i].position.ToString("F2"));
                }
            }
        }
    }

    // ------------------------------------------------------------------ D9: Filler, Bottler, Refinery inlet
    public static class FluidDevices
    {
        /// <summary>Filler: pour fluid items in (oil, gas cans, lubricant). Takes what fits; changes st.count.</summary>
        public static void Pour(World world, Vector3i p, ItemStack st)
        {
            if (st == null || st.IsEmpty() || st.itemValue.ItemClass == null) return;
            FluidStore.EnsureLoaded();
            float per;
            string fluid = Fluids.FluidOfItem(st.itemValue.ItemClass.GetItemName(), out per);
            if (fluid == null) return;
            FluidState s = FluidStore.Get(p);
            if (s.Amount > 0.01f && s.Fluid.Length > 0 && s.Fluid != fluid) return;   // holds another fluid
            float cap = Fluids.Prop(world.GetBlock(p).Block, "FeFluidBuffer", 1000f);
            int n = Mathf.Min(st.count, Mathf.FloorToInt((cap - s.Amount) / per));
            if (n <= 0) return;
            s.Amount += n * per;
            s.Fluid = fluid;
            st.count -= n;
            FluidStore.MarkDirty();
        }

        /// <summary>Bottler: up to max items from what it holds (null when not enough for one).</summary>
        public static ItemStack Bottle(World world, Vector3i p, int max)
        {
            FluidStore.EnsureLoaded();
            FluidState s = FluidStore.Get(p);
            float per;
            string item = Fluids.ItemOfFluid(s.Fluid, out per);
            if (item == null || per <= 0f) return null;
            int n = Mathf.Min(max, Mathf.FloorToInt(s.Amount / per + 0.001f));
            if (n <= 0) return null;
            ItemValue iv = ItemClass.GetItem(item, false);
            if (iv == null || iv.IsEmpty()) return null;
            s.Amount -= n * per;
            if (s.Amount <= 0.01f) { s.Amount = 0f; s.Fluid = ""; }
            FluidStore.MarkDirty();
            return new ItemStack(iv, n);
        }

        /// <summary>Every 0.5 s (BeltTicker): Bottlers put items on the belt in front; Refineries turn what they hold
        /// into ingredients for their fixed recipe.</summary>
        public static void TickAll(World world)
        {
            FluidStore.EnsureLoaded();
            foreach (Vector3i p in FluidStore.Devices)
            {
                if (world.GetChunkFromWorldPos(p) == null) continue;
                BlockValue bv = world.GetBlock(p);
                FluidKind k = Fluids.Kind(bv.Block);
                if (k == FluidKind.Caster)
                {
                    MetalWorks.TickCaster(world, p, bv, FluidStore.Get(p));
                    continue;
                }
                if (k == FluidKind.Processor)
                {
                    ProcessMachine.Tick(world, p, bv, FluidStore.Get(p), 0.5f);
                    continue;
                }
                if (k == FluidKind.Smelter && Industrial.IsElectric(bv.Block))
                {
                    MetalWorks.TickElectricSmelter(world, p, bv, FluidStore.Get(p));
                    continue;
                }
                if (k == FluidKind.Bottler)
                {
                    Vector3i f = Fluids.Rot(bv, Vector3.forward);
                    Vector3i dst = new Vector3i(p.x + f.x, p.y + f.y, p.z + f.z);
                    if (!Belt.Accepts(world, dst, f)) continue;
                    float entry = Belt.EntryP(world, dst, f);
                    List<BeltItem> items = BeltStore.Items(dst, false);
                    if (!Belt.Room(items, entry)) continue;
                    if (items != null && entry == 0f)
                    {
                        bool blocked = false;
                        foreach (BeltItem o in items) if (o.P < entry + Belt.Gap) blocked = true;
                        if (blocked) continue;
                    }
                    ItemStack st = Bottle(world, p, 16);
                    if (st == null) continue;
                    BeltItem it = BeltStore.Add(dst, st, entry);
                    Belt.ChooseExit(world, dst, world.GetBlock(dst), it);
                }
                else if (k == FluidKind.Refinery)
                {
                    FluidState s = FluidStore.Get(p);
                    float per;
                    string item = Fluids.ItemOfFluid(s.Fluid, out per);
                    if (item == null) continue;
                    int n = Mathf.FloorToInt(s.Amount / per + 0.001f);
                    if (n <= 0) continue;
                    ItemValue iv = ItemClass.GetItem(item, false);
                    if (iv == null || iv.IsEmpty()) continue;
                    ItemStack st = new ItemStack(iv, n);
                    BeltMachines.Insert(world, p, st);
                    int used = n - st.count;
                    if (used <= 0) continue;
                    s.Amount -= used * per;
                    if (s.Amount <= 0.01f) { s.Amount = 0f; s.Fluid = ""; }
                    FluidStore.MarkDirty();
                }
            }
        }
    }
}
