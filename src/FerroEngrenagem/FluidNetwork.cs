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

namespace FerroEngrenagem
{
    public enum FluidKind { None, Pipe, Tank, MechPump, ElecPump, Condenser, SteamEngine }

    public class FluidPort
    {
        public Vector3i Owner;     // device parent position
        public Vector3i Cell;      // the device cell the port is on
        public Vector3i Dir;       // outward direction
        public bool Out;           // true = offers fluid, false = takes fluid
        public string Fluid;       // fluid it handles
    }

    public class FluidState
    {
        public string Fluid = "";  // stored fluid (tanks, engine water)
        public float Amount;       // stored litres
        public float Steam;        // steam buffer (engines) / condensed water buffer (condensers)
        public float LastFlow;     // L/min moved last tick (readout)
        public string Note = "";   // readout: why it does not run
    }

    public class FluidNet
    {
        public readonly HashSet<Vector3i> Pipes = new HashSet<Vector3i>();
        public readonly List<FluidPort> Ports = new List<FluidPort>();
        public string Fluid = "";
        public bool Blocked;
        public float FlowPerMin;
    }

    public static class Fluids
    {
        public const string Water = "water";
        public const string Steam = "steam";
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
                }
            }
            kindByBlock[b.blockID] = k;
            return k;
        }

        public static float Prop(Block b, string name, float def)
        {
            return b.Properties != null && b.Properties.Contains(name) ? b.Properties.GetFloat(name) : def;
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
                case FluidKind.Condenser:
                    // 2 wide x 2 high (parent = bottom cell of its own column): steam in at the back of the upper
                    // cell (gas chamber), water out at the front of the lower cell (liquid chamber)
                    l.Add(new FluidPort { Owner = pos, Cell = Add(pos, new Vector3i(0, 1, 0)), Dir = Rot(bv, Vector3.back), Out = false, Fluid = Steam });
                    l.Add(new FluidPort { Owner = pos, Cell = pos, Dir = Rot(bv, Vector3.forward), Out = true, Fluid = Water });
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
            return HasPortAt(world, n, Neg(p.Dir));
        }

        /// <summary>Does a device cell have a port facing dir (for pipe connections and the arms of pipe models)?</summary>
        public static bool HasPortAt(World world, Vector3i cell, Vector3i dir)
        {
            BlockValue bv = world.GetBlock(cell);
            FluidKind k = Kind(bv.Block);
            if (k == FluidKind.None) return false;
            if (k == FluidKind.Pipe) return true;
            Vector3i owner = ParentOf(world, cell, bv);
            foreach (FluidPort p in Ports(world, owner))
                if (p.Cell == cell && p.Dir == dir) return true;
            return false;
        }

        /// <summary>Network that the cell+dir side of a port leads into (pipes, or the facing port of another
        /// device). The key is the first pipe, or the pair of device cells.</summary>
        public static FluidNet NetFrom(World world, FluidPort start, Dictionary<string, FluidPort[]> allPorts)
        {
            FluidNet net = new FluidNet();
            Vector3i first = Add(start.Cell, start.Dir);
            BlockValue fb = world.GetBlock(first);
            if (Kind(fb.Block) != FluidKind.Pipe)
            {
                // device facing device directly
                net.Ports.Add(start);
                Vector3i owner = ParentOf(world, first, fb);
                if (Kind(fb.Block) != FluidKind.None)
                    foreach (FluidPort p in Ports(world, owner))
                        if (p.Cell == first && p.Dir == Neg(start.Dir)) net.Ports.Add(p);
                return net;
            }
            Queue<Vector3i> open = new Queue<Vector3i>();
            open.Enqueue(first);
            net.Pipes.Add(first);
            HashSet<string> seenPorts = new HashSet<string>();
            while (open.Count > 0 && net.Pipes.Count < 2048)
            {
                Vector3i p = open.Dequeue();
                foreach (Vector3i d in Dirs)
                {
                    Vector3i n = Add(p, d);
                    BlockValue nb = world.GetBlock(n);
                    FluidKind nk = Kind(nb.Block);
                    if (nk == FluidKind.None) continue;
                    if (nk == FluidKind.Pipe)
                    {
                        if (net.Pipes.Add(n)) open.Enqueue(n);
                        continue;
                    }
                    Vector3i owner = ParentOf(world, n, nb);
                    foreach (FluidPort port in Ports(world, owner))
                    {
                        if (port.Cell != n || port.Dir != Neg(d)) continue;
                        string key = port.Owner + "|" + port.Cell + "|" + port.Dir + "|" + port.Out;
                        if (seenPorts.Add(key)) net.Ports.Add(port);
                    }
                }
            }
            return net;
        }

        /// <summary>World water cells around a pump intake (the cell behind the pump and its neighbours).</summary>
        public static int IntakeWater(World world, Vector3i pump, BlockValue bv)
        {
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
            string dir = GameIO.GetSaveGameDir();
            return string.IsNullOrEmpty(dir) ? null : Path.Combine(dir, "FerroEngrenagem_fluids.txt");
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
                    states[p] = s;
                }
            }
            catch (System.Exception e)
            {
                Log.Warning(FerroEngrenagemMod.LogPrefix + "fluids: could not read " + f + ": " + e.Message);
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
                      .Append(s.Steam.ToString("0.###", CultureInfo.InvariantCulture)).Append('\n');
                }
                File.WriteAllText(loadedFor, sb.ToString());
                dirty = false;
            }
            catch (System.Exception e)
            {
                Log.Warning(FerroEngrenagemMod.LogPrefix + "fluids: could not save: " + e.Message);
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
            host = new GameObject("FerroEngrenagem.FluidTicker");
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
            List<FluidPort> tankPorts = new List<FluidPort>();
            foreach (Vector3i p in FluidStore.Devices)
            {
                if (!Loaded(world, p)) continue;
                BlockValue bv = world.GetBlock(p);
                FluidKind k = Fluids.Kind(bv.Block);
                FluidState s = FluidStore.Get(p);
                s.LastFlow = 0f;
                foreach (FluidPort port in Fluids.Ports(world, p))
                {
                    switch (k)
                    {
                        case FluidKind.MechPump:
                        case FluidKind.ElecPump:
                            offer[port] = PumpRate(world, p, bv, s) * dt / 60f;
                            break;
                        case FluidKind.Condenser:
                            if (port.Out) offer[port] = s.Steam;   // water condensed earlier, waiting to leave
                            else demand[port] = CondenserIntake(world, p, bv, s) * dt / 60f;
                            break;
                        case FluidKind.SteamEngine:
                            if (port.Out) offer[port] = s.Steam;
                            else demand[port] = Mathf.Max(0f, Fluids.Prop(bv.Block, "FeWaterTank", 2000f) - s.Amount);
                            break;
                        case FluidKind.Tank:
                            tankPorts.Add(port);
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
            foreach (FluidPort start in all)
            {
                if (done.Contains(start)) continue;
                FluidNet net = Fluids.NetFrom(world, start, null);
                // match the ports of the net to our port objects (Ports() builds new objects each call)
                List<FluidPort> members = new List<FluidPort>();
                foreach (FluidPort a in all)
                    foreach (FluidPort b in net.Ports)
                        if (a.Owner == b.Owner && a.Cell == b.Cell && a.Dir == b.Dir && a.Out == b.Out) { members.Add(a); break; }
                if (!members.Contains(start)) members.Add(start);
                foreach (FluidPort m in members) done.Add(m);
                foreach (Vector3i pp in net.Pipes) NetByPipe[pp] = net;
                Flow(world, net, members, offer, demand, dt);
            }

            // 3. the machines turn what they received into their products (and engines run)
            foreach (Vector3i p in FluidStore.Devices)
            {
                if (!Loaded(world, p)) continue;
                BlockValue bv = world.GetBlock(p);
                FluidKind k = Fluids.Kind(bv.Block);
                if (k == FluidKind.SteamEngine) SteamEngine.Run(world, p, bv, FluidStore.Get(p), dt);
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
        static void Flow(World world, FluidNet net, List<FluidPort> members, Dictionary<FluidPort, float> offer,
                         Dictionary<FluidPort, float> demand, float dt)
        {
            // which fluid?
            HashSet<string> fluids = new HashSet<string>();
            List<FluidPort> offers = new List<FluidPort>(), demands = new List<FluidPort>(), tanks = new List<FluidPort>();
            foreach (FluidPort m in members)
            {
                if (Fluids.Kind(world.GetBlock(m.Owner).Block) == FluidKind.Tank)
                {
                    if (m.Out) tanks.Add(m);   // one entry per tank side is enough (Out ports)
                    FluidState ts = FluidStore.Get(m.Owner);
                    if (ts.Amount > 0.01f && ts.Fluid.Length > 0) fluids.Add(ts.Fluid);
                    continue;
                }
                float v;
                if (offer.TryGetValue(m, out v)) { offers.Add(m); if (v > 0.0001f) fluids.Add(m.Fluid); }
                if (demand.ContainsKey(m)) demands.Add(m);
            }
            // a tank reached through several sides counts once
            List<FluidPort> uniqueTanks = new List<FluidPort>();
            HashSet<Vector3i> tankOwners = new HashSet<Vector3i>();
            foreach (FluidPort t in tanks) if (tankOwners.Add(t.Owner)) uniqueTanks.Add(t);

            if (fluids.Count > 1) { net.Blocked = true; return; }
            string fluid = fluids.Count == 1 ? new List<string>(fluids)[0] : "";
            net.Fluid = fluid;

            float O = 0f, D = 0f;
            foreach (FluidPort o in offers) if (o.Fluid == fluid || fluid.Length == 0) O += offer[o];
            List<FluidPort> wanted = new List<FluidPort>();
            foreach (FluidPort d in demands) if (d.Fluid == fluid || fluid.Length == 0) { D += demand[d]; wanted.Add(d); }

            float direct = Mathf.Min(O, D);
            float spareOffer = O - direct, missing = D - direct;

            // tanks: absorb the spare offer, cover the missing demand
            float tankIn = 0f, tankOut = 0f;
            if (fluid.Length > 0)
            {
                foreach (FluidPort t in uniqueTanks)
                {
                    FluidState ts = FluidStore.Get(t.Owner);
                    if (ts.Amount > 0.01f && ts.Fluid != fluid) continue;
                    float cap = Fluids.Prop(world.GetBlock(t.Owner).Block, "FeFluidCapacity", 4000f);
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
                Got(world, d, share, dt);
            }
            net.FlowPerMin = Mathf.Max(given, received) / dt * 60f;
        }

        // An offer port gave `amount` litres.
        static void Took(World world, FluidPort o, float amount, float dt)
        {
            FluidState s = FluidStore.Get(o.Owner);
            FluidKind k = Fluids.Kind(world.GetBlock(o.Owner).Block);
            if (k == FluidKind.Condenser || k == FluidKind.SteamEngine) s.Steam = Mathf.Max(0f, s.Steam - amount);
            s.LastFlow += amount / dt * 60f;
        }

        // A demand port received `amount` litres.
        static void Got(World world, FluidPort d, float amount, float dt)
        {
            BlockValue bv = world.GetBlock(d.Owner);
            FluidState s = FluidStore.Get(d.Owner);
            FluidKind k = Fluids.Kind(bv.Block);
            if (k == FluidKind.SteamEngine) { s.Amount += amount; s.Fluid = Fluids.Water; }
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
            if (!_blockValue.ischild && Fluids.Kind(this) != FluidKind.Pipe) FluidStore.Register(_blockPos);
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
            return new BlockActivationCommand[]
            {
                new BlockActivationCommand("take", "hand", Pickup.CanBuildHere(_world, _blockPos), false, null)
            };
        }

        public override bool OnBlockActivated(string _commandName, WorldBase _world, Vector3i _blockPos,
                                              BlockValue _blockValue, EntityPlayerLocal _player)
        {
            if (_commandName != "take") return false;
            float delay = Properties != null && Properties.Contains("TakeDelay") ? Properties.GetFloat("TakeDelay") : 2f;
            takeItemWithTimer(_blockPos, _blockValue, _player, delay);
            return true;
        }

        public override string GetActivationText(WorldBase _world, BlockValue _blockValue, Vector3i _blockPos,
                                                 EntityAlive _entityFocusing)
        {
            return KineticLookController.Escape(FluidText.Describe(_blockPos, _blockValue, true)) + "\n" +
                   Kinetic.Text("feHintTake", "Hold {0} to take");
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
                {
                    FluidNet net;
                    if (!FluidTicker.NetByPipe.TryGetValue(pos, out net))
                        return (name + "\n" + Fluids.Text("feFluidIdle", "No flow")).Trim();
                    if (net.Blocked)
                        return (name + "\n" + Fluids.Text("feFluidBlocked", "BLOCKED: two different fluids in this pipe")).Trim();
                    return (name + "\n" + string.Format(Fluids.Text("feFluidFlow", "{0}: {1} L/min"),
                        Fluids.FluidName(net.Fluid), Mathf.RoundToInt(net.FlowPerMin))).Trim();
                }
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
                    if (s.Note == "power") t += "\n" + Fluids.Text("feFluidNoPower", "No power: wire it to a power source");
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
            if (!(__instance is BlockPowered) || _blockValue.ischild) return;
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

        public static void Attach(BlockEntityData ebcd, Vector3i pos)
        {
            if (ebcd == null || ebcd.transform == null || GameManager.IsDedicatedServer) return;
            PipeArms a = ebcd.transform.GetComponent<PipeArms>();
            if (a == null) a = ebcd.transform.gameObject.AddComponent<PipeArms>();
            a.pos = pos;
            a.next = 0f;
            for (int i = 0; i < 6; i++) a.arms[i] = Find(ebcd.transform, Names[i]);
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

        void Update()
        {
            if (Time.time < next) return;
            next = Time.time + 0.5f;
            World world = GameManager.Instance == null ? null : GameManager.Instance.World;
            if (world == null) return;
            for (int i = 0; i < 6; i++)
            {
                if (arms[i] == null) continue;
                // the arm's direction in the world (the model may be rotated)
                Vector3 w = transform.TransformDirection(Local[i]);
                Vector3i d = new Vector3i(Mathf.RoundToInt(w.x), Mathf.RoundToInt(w.y), Mathf.RoundToInt(w.z));
                Vector3i n = new Vector3i(pos.x + d.x, pos.y + d.y, pos.z + d.z);
                bool on = Fluids.HasPortAt(world, n, new Vector3i(-d.x, -d.y, -d.z));
                if (arms[i].gameObject.activeSelf != on) arms[i].gameObject.SetActive(on);
            }
        }
    }
}
