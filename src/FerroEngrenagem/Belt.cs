// D10 (user, 2026-11-23): conveyor belts moved by torque, Create-like.
//
//   feConveyor (Class FeConveyor = BlockFeKinetic, FeKinetic=conveyor): one block, items travel to the block's FRONT
//   (model local +Z). Roller axis = the model's local X: a shaft on the LEFT or RIGHT of any belt drives the line.
//   feConveyorRamp (FeBeltRise=1): same, but it takes items at its back and gives them to the belt one block UP and
//   one block forward (stack ramps for a staircase of items).
//
//   Where a belt sends its items (Outputs):
//     - the belt in front (from its back: at its start; from its side: in its middle = a merge);
//     - the belts on its left / right that point AWAY from it (a curve; with both sides a split in two; with the
//       front too a split in three). The items are dealt round robin between the outputs, one each.
//     - a ramp: only the belt above-in-front.
//   Belts joined that way (Links, both directions) are one torque network: every belt is a node and a machine
//   (FeTorqueCost UT each at 32 RPM, x (rpm/32)^2). Speed: FeBeltSpeed blocks/s at 32 RPM. No torque: items stop.
//
//   Items are logical (BeltStore: per belt a list of stacks, position 0..1, chosen exit), moved by the server (10 Hz)
//   and saved in <save>/FerroEngrenagem_belts.txt. With nowhere to go they stop and queue. Dropped items landing on a
//   belt get on it. Removing a belt drops its items.
//   The host draws the items (BeltRenderer: straight, a quarter arc on a curve, the slope on a ramp) and shapes the
//   belt (BeltShape: side rails open where another belt joins, an end stop when nothing is in front, curve guides on
//   the turning side, the surface "FeBeltSlats" sliding). Single player / host only for now (F2-T06).
//
// C# 5 only.

using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEngine;

namespace FerroEngrenagem
{
    public class BeltItem
    {
        public int Id;
        public ItemStack Stack;
        public float P;              // 0 = back edge, 1 = front edge (a ramp: bottom to top)
        public Vector3i Exit;        // offset of the belt it goes to
        public bool HasExit;
        public int Moved;            // tick it was last moved onto another belt
    }

    public static class Belt
    {
        public const int Capacity = 4;
        public const float Gap = 0.25f;
        public const float Top = 0.62f;    // height of the belt surface above the block's floor
        static readonly Vector3i Up = new Vector3i(0, 1, 0);
        static readonly Vector3i[] Flat = { new Vector3i(1, 0, 0), new Vector3i(-1, 0, 0), new Vector3i(0, 0, 1), new Vector3i(0, 0, -1) };
        static readonly Dictionary<Vector3i, int> turn = new Dictionary<Vector3i, int>();

        public static bool Is(Block b)
        {
            return Kinetic.Kind(b) == KineticKind.Conveyor;
        }

        public static bool IsRamp(Block b)
        {
            return Is(b) && Fluids.Prop(b, "FeBeltRise", 0f) > 0f;
        }

        public static Vector3i Front(BlockValue bv)
        {
            return Fluids.Rot(bv, Vector3.forward);
        }

        public static Vector3i Left(BlockValue bv)
        {
            return Fluids.Rot(bv, Vector3.left);
        }

        /// <summary>Roller spin that moves the top of the belt forward: up x front.</summary>
        public static Vector3i W(BlockValue bv)
        {
            Vector3i f = Front(bv);
            return new Vector3i(f.z, 0, -f.x);
        }

        static Vector3i Add(Vector3i a, Vector3i b)
        {
            return new Vector3i(a.x + b.x, a.y + b.y, a.z + b.z);
        }

        static Vector3i Sub(Vector3i a, Vector3i b)
        {
            return new Vector3i(a.x - b.x, a.y - b.y, a.z - b.z);
        }

        static Vector3i Neg(Vector3i a)
        {
            return new Vector3i(-a.x, -a.y, -a.z);
        }

        /// <summary>Does the belt at target take items travelling in (horizontal) direction dir?</summary>
        public static bool Accepts(World world, Vector3i target, Vector3i dir)
        {
            BlockValue t = world.GetBlock(target);
            if (!Is(t.Block)) return false;
            Vector3i tf = Front(t);
            if (IsRamp(t.Block)) return tf == dir;        // a ramp only from its back
            return tf != Neg(dir);                         // not head on
        }

        /// <summary>Where an item coming in direction dir starts on the target: its start, or its middle (side).</summary>
        public static float EntryP(World world, Vector3i target, Vector3i dir)
        {
            return Front(world.GetBlock(target)) == dir ? 0f : 0.5f;
        }

        /// <summary>The belts this belt gives items to (absolute positions).</summary>
        public static List<Vector3i> Outputs(World world, Vector3i pos, BlockValue bv)
        {
            List<Vector3i> l = new List<Vector3i>();
            Vector3i f = Front(bv);
            if (IsRamp(bv.Block))
            {
                Vector3i c = Add(Add(pos, f), Up);
                if (Accepts(world, c, f)) l.Add(c);
                return l;
            }
            Vector3i fc = Add(pos, f);
            if (Accepts(world, fc, f)) l.Add(fc);
            Vector3i left = Left(bv);
            foreach (Vector3i s in new Vector3i[] { left, Neg(left) })
            {
                Vector3i c = Add(pos, s);
                BlockValue cb = world.GetBlock(c);
                if (Is(cb.Block) && Front(cb) == s) l.Add(c);   // pointing away from us: a curve / split
            }
            return l;
        }

        /// <summary>D10 T3: the machine input this (flat) belt points into, if any: a conveyor port of a device (the
        /// Steam Engine's upper side cells, Fluids.ConveyorPorts) whose cell is in front and faces this belt.</summary>
        public static bool MachineAt(World world, Vector3i pos, BlockValue bv, out Vector3i cell, out Vector3i parent)
        {
            cell = Vector3i.zero;
            parent = Vector3i.zero;
            if (IsRamp(bv.Block)) return false;
            Vector3i f = Front(bv);
            Vector3i c = Add(pos, f);
            BlockValue cb = world.GetBlock(c);
            if (Fluids.Kind(cb.Block) == FluidKind.None) return false;
            Vector3i par = Fluids.ParentOf(world, c, cb);
            foreach (FluidPort port in Fluids.ConveyorPorts(world, par))
                if (port.Cell == c && port.Dir == Neg(f)) { cell = c; parent = par; return true; }
            return false;
        }

        /// <summary>Every place the items of this belt can go: the belt outputs, then a machine input.</summary>
        public static List<Vector3i> Exits(World world, Vector3i pos, BlockValue bv)
        {
            List<Vector3i> l = Outputs(world, pos, bv);
            Vector3i cell, parent;
            if (MachineAt(world, pos, bv, out cell, out parent)) l.Add(cell);
            return l;
        }

        /// <summary>Belts joined to this one either way (they give to it or take from it): one torque line.</summary>
        public static List<Vector3i> Links(World world, Vector3i pos, BlockValue bv)
        {
            List<Vector3i> l = Outputs(world, pos, bv);
            foreach (Vector3i h in Flat)
            {
                foreach (Vector3i c in new Vector3i[] { Add(pos, h), Add(Sub(pos, Up), h) })
                {
                    if (l.Contains(c)) continue;
                    BlockValue cb = world.GetBlock(c);
                    if (!Is(cb.Block)) continue;
                    if (Outputs(world, c, cb).Contains(pos)) l.Add(c);
                }
            }
            return l;
        }

        /// <summary>Torque faces of a belt towards NON-belt blocks: its roller ends (left / right).</summary>
        public static bool HasTorqueFace(World world, Vector3i pos, BlockValue bv, Vector3i d)
        {
            Vector3i axis = Kinetic.Axis(bv);
            if (d != axis && d != Neg(axis)) return false;
            return !Is(world.GetBlock(Add(pos, d)).Block);
        }

        /// <summary>Blocks per second the belt at pos moves now (0 = stopped).</summary>
        public static float Speed(World world, Vector3i pos, BlockValue bv)
        {
            TorqueNet net = Kinetic.Get(world, pos);
            if (net == null || !net.Running || !net.Machines.ContainsKey(pos)) return 0f;
            return Fluids.Prop(bv.Block, "FeBeltSpeed", 1f) * net.MachineSpeed(pos);
        }

        /// <summary>Give the item its exit: the next output in turn (round robin per belt).</summary>
        public static void ChooseExit(World world, Vector3i pos, BlockValue bv, BeltItem it)
        {
            List<Vector3i> outs = Exits(world, pos, bv);
            if (outs.Count == 0) { it.HasExit = false; return; }
            int k;
            turn.TryGetValue(pos, out k);
            turn[pos] = k + 1;
            it.Exit = Sub(outs[k % outs.Count], pos);
            it.HasExit = true;
        }

        /// <summary>World point (without the floating origin) and travel direction of an item on a belt.</summary>
        public static Vector3 PathPoint(Vector3i pos, BlockValue bv, BeltItem it, out Vector3 dir)
        {
            Vector3 c = pos.ToVector3() + new Vector3(0.5f, Top, 0.5f);
            Vector3 f = Front(bv).ToVector3();
            if (IsRamp(bv.Block))
            {
                dir = (f + Vector3.up).normalized;
                return c + f * (it.P - 0.5f) + Vector3.up * it.P;
            }
            if (it.HasExit && it.Exit.y == 0)
            {
                Vector3 e = it.Exit.ToVector3();
                if (Mathf.Abs(Vector3.Dot(e, f)) < 0.5f && it.P >= 0f)
                {
                    // a curve: quarter arc from the back edge to the side edge around the back corner of that side
                    Vector3 corner = c - f * 0.5f + e * 0.5f;
                    float th = Mathf.Clamp01(it.P) * Mathf.PI * 0.5f;
                    dir = (e * Mathf.Sin(th) + f * Mathf.Cos(th)).normalized;
                    return corner + (-e * Mathf.Cos(th) + f * Mathf.Sin(th)) * 0.5f;
                }
            }
            dir = f;
            return c + f * (it.P - 0.5f);
        }

        public static string Describe(World world, Vector3i pos, BlockValue bv, TorqueNet net)
        {
            BeltStore.EnsureLoaded();
            List<BeltItem> items = BeltStore.Items(pos, false);
            int n = items == null ? 0 : items.Count;
            float v = Speed(world, pos, bv);
            string t = string.Format(Kinetic.Text("feBeltInfo", "Items: {0} / {1} - {2} blocks/s"), n, Capacity,
                                     v.ToString("0.0", CultureInfo.InvariantCulture));
            int outs = Outputs(world, pos, bv).Count;
            if (outs > 1) t += "\n" + string.Format(Kinetic.Text("feBeltSplit", "Splits the items between {0} belts"), outs);
            if (items != null && n > 0)
            {
                StringBuilder sb = new StringBuilder();
                for (int i = 0; i < items.Count && i < 3; i++)
                {
                    if (i > 0) sb.Append(", ");
                    sb.Append(items[i].Stack.count).Append("x ").Append(items[i].Stack.itemValue.ItemClass.GetLocalizedItemName());
                }
                t += "\n" + sb.ToString();
            }
            if (v <= 0f) t += "\n" + Kinetic.Text("feBeltStopped", "Stopped: no torque (put a shaft on the left or right of any belt of the line)");
            return t;
        }

        /// <summary>Room for an item at position p on this belt?</summary>
        public static bool Room(List<BeltItem> items, float p)
        {
            if (items == null) return true;
            if (items.Count >= Capacity) return false;
            foreach (BeltItem it in items)
                if (Mathf.Abs(it.P - p) < Gap - 0.001f) return false;
            return true;
        }

        public static void DropAll(World world, Vector3i pos)
        {
            BeltStore.EnsureLoaded();
            List<BeltItem> items = BeltStore.Items(pos, false);
            turn.Remove(pos);
            if (items == null) return;
            if (GameManager.Instance != null)
                foreach (BeltItem it in items)
                    GameManager.Instance.ItemDropServer(it.Stack, pos.ToVector3() + new Vector3(0.5f, 0.75f, 0.5f),
                                                       Vector3.zero, -1, 300f, false);
            BeltStore.Remove(pos);
        }
    }

    // ------------------------------------------------------------------ storage
    public static class BeltStore
    {
        static string loadedFor;
        static bool dirty;
        static int nextId = 1;
        static readonly Dictionary<Vector3i, List<BeltItem>> belts = new Dictionary<Vector3i, List<BeltItem>>();

        public static ICollection<Vector3i> Belts { get { return belts.Keys; } }

        static string FilePath()
        {
            string dir = GameIO.GetSaveGameDir();
            return string.IsNullOrEmpty(dir) ? null : Path.Combine(dir, "FerroEngrenagem_belts.txt");
        }

        public static void EnsureLoaded()
        {
            string f = FilePath();
            if (f == null || f == loadedFor) return;
            loadedFor = f;
            belts.Clear();
            dirty = false;
            if (!File.Exists(f)) return;
            try
            {
                foreach (string line in File.ReadAllLines(f))
                {
                    string[] t = line.Split(';');
                    if (t.Length < 6) continue;
                    Vector3i p = new Vector3i(int.Parse(t[0]), int.Parse(t[1]), int.Parse(t[2]));
                    ItemValue iv = ReadItem(t[5]);
                    if (iv == null || iv.IsEmpty()) continue;
                    BeltItem it = new BeltItem();
                    it.Id = nextId++;
                    it.P = float.Parse(t[3], CultureInfo.InvariantCulture);
                    it.Stack = new ItemStack(iv, int.Parse(t[4]));
                    if (t.Length >= 9)
                    {
                        it.Exit = new Vector3i(int.Parse(t[6]), int.Parse(t[7]), int.Parse(t[8]));
                        it.HasExit = it.Exit != Vector3i.zero;
                    }
                    Items(p, true).Add(it);
                }
            }
            catch (System.Exception e)
            {
                Log.Warning(FerroEngrenagemMod.LogPrefix + "belts: could not read " + f + ": " + e.Message);
            }
        }

        public static void Save()
        {
            if (!dirty || loadedFor == null) return;
            try
            {
                StringBuilder sb = new StringBuilder();
                foreach (KeyValuePair<Vector3i, List<BeltItem>> kv in belts)
                    foreach (BeltItem it in kv.Value)
                    {
                        string data = WriteItem(it.Stack.itemValue);
                        // never overwrite the file with a partial list (at quit the item classes may be gone)
                        if (data == null) return;
                        Vector3i ex = it.HasExit ? it.Exit : Vector3i.zero;
                        sb.Append(kv.Key.x).Append(';').Append(kv.Key.y).Append(';').Append(kv.Key.z).Append(';')
                          .Append(it.P.ToString("0.###", CultureInfo.InvariantCulture)).Append(';')
                          .Append(it.Stack.count).Append(';').Append(data).Append(';')
                          .Append(ex.x).Append(';').Append(ex.y).Append(';').Append(ex.z).Append('\n');
                    }
                File.WriteAllText(loadedFor, sb.ToString());
                dirty = false;
            }
            catch (System.Exception e)
            {
                Log.Warning(FerroEngrenagemMod.LogPrefix + "belts: could not save: " + e.Message);
            }
        }

        // the vanilla item serializer keeps quality, durability and mods
        static string WriteItem(ItemValue iv)
        {
            try
            {
                using (MemoryStream ms = new MemoryStream())
                {
                    PooledBinaryWriter bw = new PooledBinaryWriter();
                    bw.SetBaseStream(ms);
                    iv.Write(bw);
                    bw.Flush();
                    return System.Convert.ToBase64String(ms.ToArray());
                }
            }
            catch (System.Exception e)
            {
                Log.Warning(FerroEngrenagemMod.LogPrefix + "belts: could not write an item: " + e.Message);
                return null;
            }
        }

        static ItemValue ReadItem(string data)
        {
            try
            {
                using (MemoryStream ms = new MemoryStream(System.Convert.FromBase64String(data)))
                {
                    PooledBinaryReader br = new PooledBinaryReader();
                    br.SetBaseStream(ms);
                    ItemValue iv = new ItemValue();
                    iv.Read(br);
                    return iv;
                }
            }
            catch (System.Exception e)
            {
                Log.Warning(FerroEngrenagemMod.LogPrefix + "belts: could not read an item: " + e.Message);
                return null;
            }
        }

        public static List<BeltItem> Items(Vector3i p, bool create)
        {
            List<BeltItem> l;
            if (!belts.TryGetValue(p, out l) && create) { l = new List<BeltItem>(); belts[p] = l; }
            return l;
        }

        public static BeltItem Add(Vector3i p, ItemStack stack, float pos)
        {
            BeltItem it = new BeltItem();
            it.Id = nextId++;
            it.Stack = stack;
            it.P = pos;
            Items(p, true).Add(it);
            dirty = true;
            return it;
        }

        public static void Remove(Vector3i p)
        {
            if (belts.Remove(p)) dirty = true;
        }

        public static void Prune()
        {
            List<Vector3i> empty = new List<Vector3i>();
            foreach (KeyValuePair<Vector3i, List<BeltItem>> kv in belts) if (kv.Value.Count == 0) empty.Add(kv.Key);
            foreach (Vector3i p in empty) belts.Remove(p);
        }

        public static void MarkDirty()
        {
            dirty = true;
        }
    }

    // ------------------------------------------------------------------ server tick
    public class BeltTicker : MonoBehaviour
    {
        static GameObject host;
        const float Step = 0.1f;
        float next, nextAbsorb, nextSave;
        int tick;

        public static void Ensure()
        {
            if (host != null) return;
            host = new GameObject("FerroEngrenagem.BeltTicker");
            Object.DontDestroyOnLoad(host);
            host.AddComponent<BeltTicker>();
            if (!GameManager.IsDedicatedServer) host.AddComponent<BeltRenderer>();
        }

        void Update()
        {
            GameManager gm = GameManager.Instance;
            World world = gm == null ? null : gm.World;
            if (world == null) return;
            if (!SingletonMonoBehaviour<ConnectionManager>.Instance.IsServer) return;
            if (Time.time < next) return;
            next = Time.time + Step;
            BeltStore.EnsureLoaded();
            tick++;
            if (Time.time >= nextAbsorb) { nextAbsorb = Time.time + 0.5f; Absorb(world); }
            Move(world, Step);
            if (Time.time >= nextSave) { nextSave = Time.time + 30f; BeltStore.Save(); }
        }

        // dropped items lying on a (flat) belt get on it
        static void Absorb(World world)
        {
            List<Entity> list = world.Entities.list;
            List<EntityItem> found = new List<EntityItem>();
            for (int i = 0; i < list.Count; i++)
            {
                EntityItem e = list[i] as EntityItem;
                if (e != null && !e.IsDead() && e.itemStack != null && !e.itemStack.IsEmpty()) found.Add(e);
            }
            foreach (EntityItem e in found)
            {
                Vector3 wp = e.position;
                Vector3i cell = World.worldToBlockPos(wp);
                BlockValue bv = world.GetBlock(cell);
                if (!Belt.Is(bv.Block))
                {
                    cell = World.worldToBlockPos(wp - new Vector3(0f, 0.3f, 0f));
                    bv = world.GetBlock(cell);
                    if (!Belt.Is(bv.Block)) continue;
                }
                if (Belt.IsRamp(bv.Block)) continue;
                if (wp.y < cell.y + Belt.Top - 0.35f) continue;   // under / beside the belt, not on it
                Vector3i f = Belt.Front(bv);
                float p = Mathf.Clamp(Vector3.Dot(wp - (cell.ToVector3() + new Vector3(0.5f, 0f, 0.5f)), f.ToVector3()) + 0.5f, 0.05f, 0.95f);
                List<BeltItem> items = BeltStore.Items(cell, false);
                if (!Belt.Room(items, p))
                {
                    bool ok = false;
                    for (float q = 0.05f; q <= 0.95f; q += 0.05f)
                        if (Belt.Room(items, q)) { p = q; ok = true; break; }
                    if (!ok) continue;
                }
                BeltItem it = BeltStore.Add(cell, e.itemStack.Clone(), p);
                Belt.ChooseExit(world, cell, bv, it);
                world.RemoveEntity(e.entityId, EnumRemoveEntityReason.Despawned);
            }
        }

        static bool Loaded(World world, Vector3i p)
        {
            return world.GetChunkFromWorldPos(p) != null;
        }

        void Move(World world, float dt)
        {
            List<Vector3i> keys = new List<Vector3i>(BeltStore.Belts);
            bool changed = false;
            foreach (Vector3i pos in keys)
            {
                List<BeltItem> items = BeltStore.Items(pos, false);
                if (items == null || items.Count == 0 || !Loaded(world, pos)) continue;
                BlockValue bv = world.GetBlock(pos);
                if (!Belt.Is(bv.Block)) { BeltStore.Remove(pos); changed = true; continue; }   // block gone
                float v = Belt.Speed(world, pos, bv);
                if (v <= 0f) continue;
                items.Sort(delegate (BeltItem a, BeltItem b) { return b.P.CompareTo(a.P); });   // front first
                float limit = 1f;
                for (int i = 0; i < items.Count; i++)
                {
                    BeltItem it = items[i];
                    if (it.Moved == tick) { limit = it.P - Belt.Gap; continue; }
                    float reach = it.P + v * dt;
                    if (i == 0 && reach >= 1f && Pass(world, pos, bv, it, reach - 1f))
                    {
                        items.RemoveAt(i);
                        i--;
                        limit = 1f;
                        changed = true;
                        continue;
                    }
                    float target = Mathf.Min(reach, limit);
                    if (target > it.P) { it.P = target; changed = true; }
                    limit = it.P - Belt.Gap;
                }
            }
            BeltStore.Prune();
            if (changed) BeltStore.MarkDirty();
        }

        // the item at the end goes to its exit; when that one is full (or gone) it tries the other outputs, so a
        // split never stalls on one blocked branch
        bool Pass(World world, Vector3i from, BlockValue bv, BeltItem it, float over)
        {
            List<Vector3i> outs = Belt.Exits(world, from, bv);
            if (outs.Count == 0) return false;
            Vector3i mcell, mparent;
            bool machine = Belt.MachineAt(world, from, bv, out mcell, out mparent);
            Vector3i first = it.HasExit ? new Vector3i(from.x + it.Exit.x, from.y + it.Exit.y, from.z + it.Exit.z) : outs[0];
            int start = outs.IndexOf(first);
            if (start < 0) start = 0;
            for (int k = 0; k < outs.Count; k++)
            {
                Vector3i to = outs[(start + k) % outs.Count];
                if (machine && to == mcell)
                {
                    if (BeltMachines.Insert(world, mparent, it.Stack)) return true;   // all of it went in
                    continue;                                                         // the rest waits at the end
                }
                if (TryPass(world, from, to, it, over)) return true;
            }
            return false;
        }

        bool TryPass(World world, Vector3i from, Vector3i to, BeltItem it, float over)
        {
            if (!Loaded(world, to)) return false;
            Vector3i dir = new Vector3i(to.x - from.x, 0, to.z - from.z);   // horizontal travel (a ramp also rises)
            if (!Belt.Accepts(world, to, dir)) return false;
            float entry = Belt.EntryP(world, to, dir);
            List<BeltItem> next = BeltStore.Items(to, true);
            float p = Mathf.Min(entry + over, entry + 0.2f);
            if (!Belt.Room(next, p)) return false;
            if (entry == 0f)
                foreach (BeltItem o in next) if (o.P < p + Belt.Gap) return false;
            it.P = p;
            it.Moved = tick;
            BlockValue tbv = world.GetBlock(to);
            Belt.ChooseExit(world, to, tbv, it);
            next.Add(it);
            return true;
        }
    }

    // ------------------------------------------------------------------ machine inputs (D10 T3)
    public static class BeltMachines
    {
        /// <summary>Put as much of the stack as the machine takes; true when nothing is left. Steam Engine (and any
        /// torque engine with conveyor ports): its fuel item (Charcoal) goes to the fuel, its lubricant to the slots.
        /// Other items are refused and wait on the belt.</summary>
        public static bool Insert(World world, Vector3i parent, ItemStack st)
        {
            if (st == null || st.IsEmpty()) return true;
            TileEntityPowerSource te = world.GetTileEntity(parent) as TileEntityPowerSource;
            PowerGenerator gen = te == null ? null : te.GetPowerItem() as PowerGenerator;
            if (gen == null) return false;
            Block b = world.GetBlock(parent).Block;
            int took = 0;
            ItemClass fuel = FuelGenerator.FuelItem(b);
            if (fuel != null && st.itemValue.type == fuel.Id)
            {
                int per = Mathf.Max(1, FuelGenerator.FuelPerItem(b));
                int room = (gen.MaxFuel - gen.CurrentFuel) / per;
                took = Mathf.Min(room, st.count);
                if (took > 0) gen.CurrentFuel = (ushort)Mathf.Min(gen.MaxFuel, gen.CurrentFuel + took * per);
            }
            else
            {
                string lube = TorqueEngine.LubeItem(b);
                ItemClass ic = st.itemValue.ItemClass;
                if (lube != null && ic != null && ic.GetItemName() == lube && gen.Stacks != null)
                {
                    int max = Mathf.Max(1, ic.Stacknumber.Value);
                    int left = st.count;
                    for (int i = 0; i < gen.Stacks.Length && left > 0; i++)
                    {
                        ItemStack slot = gen.Stacks[i];
                        if (slot != null && !slot.IsEmpty() && slot.itemValue.type == st.itemValue.type && slot.count < max)
                        {
                            int n = Mathf.Min(left, max - slot.count);
                            slot.count += n;
                            left -= n;
                        }
                    }
                    for (int i = 0; i < gen.Stacks.Length && left > 0; i++)
                    {
                        if (gen.Stacks[i] == null || gen.Stacks[i].IsEmpty())
                        {
                            int n = Mathf.Min(left, max);
                            gen.Stacks[i] = new ItemStack(st.itemValue.Clone(), n);
                            left -= n;
                        }
                    }
                    took = st.count - left;
                    if (took > 0) te.SetSendSlots();
                }
            }
            if (took <= 0) return false;
            st.count -= took;
            te.SetModified();
            BeltStore.MarkDirty();
            return st.count <= 0;
        }
    }

    // ------------------------------------------------------------------ host visuals
    // The items: one model per stack (the dropped-item model, or a small box for blocks), gliding along its path.
    public class BeltRenderer : MonoBehaviour
    {
        class Shown
        {
            public GameObject Go;
            public AssetManagement.InstanceHandle<GameObject> Handle;
            public bool HasHandle;
            public Vector3 Pos;
            public int Seen;
        }

        readonly Dictionary<int, Shown> shown = new Dictionary<int, Shown>();
        int frame;

        void LateUpdate()
        {
            GameManager gm = GameManager.Instance;
            World world = gm == null ? null : gm.World;
            EntityPlayerLocal pl = world == null ? null : world.GetPrimaryPlayer();
            if (world == null || pl == null) { Clear(); return; }
            frame++;
            Vector3 me = pl.position;
            foreach (Vector3i pos in BeltStore.Belts)
            {
                if ((pos.ToVector3() - me).sqrMagnitude > 60f * 60f) continue;
                List<BeltItem> items = BeltStore.Items(pos, false);
                if (items == null || items.Count == 0) continue;
                BlockValue bv = world.GetBlock(pos);
                if (!Belt.Is(bv.Block)) continue;
                foreach (BeltItem it in items)
                {
                    Vector3 dir;
                    Vector3 target = Belt.PathPoint(pos, bv, it, out dir) - Origin.position;
                    Shown s;
                    if (!shown.TryGetValue(it.Id, out s))
                    {
                        s = Make(it.Stack);
                        s.Pos = target;
                        shown[it.Id] = s;
                    }
                    s.Seen = frame;
                    if ((s.Pos - target).sqrMagnitude > 2.25f) s.Pos = target;
                    else s.Pos = Vector3.MoveTowards(s.Pos, target, 3f * Time.deltaTime + 0.002f);
                    if (s.Go != null)
                    {
                        s.Go.transform.position = s.Pos;
                        Vector3 flat = new Vector3(dir.x, 0f, dir.z);
                        if (flat.sqrMagnitude > 0.001f)
                            s.Go.transform.rotation = Quaternion.Slerp(s.Go.transform.rotation, Quaternion.LookRotation(flat), 10f * Time.deltaTime);
                    }
                }
            }
            List<int> gone = new List<int>();
            foreach (KeyValuePair<int, Shown> kv in shown) if (kv.Value.Seen != frame) gone.Add(kv.Key);
            foreach (int id in gone) { Kill(shown[id]); shown.Remove(id); }
        }

        void Clear()
        {
            foreach (Shown s in shown.Values) Kill(s);
            shown.Clear();
        }

        static void Kill(Shown s)
        {
            if (s.HasHandle) s.Handle.Destroy();
            if (s.Go != null) Object.Destroy(s.Go);
        }

        static Shown Make(ItemStack stack)
        {
            Shown s = new Shown();
            GameObject root = new GameObject("FeBeltItem");
            s.Go = root;
            GameObject model = null;
            try
            {
                ItemClass ic = stack.itemValue.ItemClass;
                if (ic != null && !ic.IsBlock())
                {
                    s.Handle = ic.CloneModel(stack.itemValue, root.transform, BlockShape.MeshPurpose.Drop);
                    s.HasHandle = true;
                    model = s.Handle.Instance;
                }
            }
            catch (System.Exception e)
            {
                Log.Warning(FerroEngrenagemMod.LogPrefix + "belt item model: " + e.Message);
            }
            if (model == null)
            {
                model = GameObject.CreatePrimitive(PrimitiveType.Cube);
                model.transform.SetParent(root.transform, false);
                Renderer r0 = model.GetComponent<Renderer>();
                if (r0 != null) r0.material.color = new Color(0.55f, 0.45f, 0.35f);
            }
            foreach (Collider col in model.GetComponentsInChildren<Collider>(true)) Object.Destroy(col);
            foreach (Rigidbody rb in model.GetComponentsInChildren<Rigidbody>(true)) Object.Destroy(rb);
            model.SetActive(true);
            model.transform.localPosition = Vector3.zero;
            model.transform.localRotation = Quaternion.identity;
            model.transform.localScale = Vector3.one;
            // fit into ~0.35 m and sit on the belt
            Renderer[] rends = model.GetComponentsInChildren<Renderer>(true);
            if (rends.Length > 0)
            {
                Bounds b = rends[0].bounds;
                foreach (Renderer r in rends) b.Encapsulate(r.bounds);
                float size = Mathf.Max(b.size.x, Mathf.Max(b.size.y, b.size.z));
                float k = size > 0.001f ? 0.35f / size : 1f;
                model.transform.localScale = Vector3.one * k;
                Vector3 bottom = new Vector3(b.center.x, b.min.y, b.center.z) - root.transform.position;
                model.transform.localPosition = -bottom * k;
            }
            return s;
        }
    }

    // The belt's own model: rails open where another belt joins on that side, the end stop shows when nothing is in
    // front, the curve guide on a turning side; the surface "FeBeltSlats" slides along the travel (up the slope on a
    // ramp) by one slat spacing, over and over.
    public class BeltShape : MonoBehaviour
    {
        const float Spacing = 0.125f;
        const float CurveStep = 10f;   // degrees between the slats of a curve
        Vector3i pos;
        Transform slats, bed, railL, railR, end, setL, setR, cslL, cslR, rollF, rollB, junction, posts, wedge;
        Vector3 basePos, slide;
        Quaternion baseL, baseR;
        float speed, offset, angle, next;
        int mode;   // 0 straight, 1 curve left, 2 curve right, 3 junction (2 or 3 outputs)

        public static void Attach(BlockEntityData ebcd, Vector3i pos, Block block)
        {
            if (ebcd == null || ebcd.transform == null || GameManager.IsDedicatedServer) return;
            BeltShape s = ebcd.transform.GetComponent<BeltShape>();
            if (s == null) s = ebcd.transform.gameObject.AddComponent<BeltShape>();
            Transform t = ebcd.transform;
            s.pos = pos;
            s.slats = Find(t, "FeBeltSlats");
            s.bed = Find(t, "FeBeltBed");
            s.railL = Find(t, "FeRail_L");
            s.railR = Find(t, "FeRail_R");
            s.end = Find(t, "FeBeltEnd");
            s.setL = Find(t, "FeCurveSet_L");
            s.setR = Find(t, "FeCurveSet_R");
            s.cslL = Find(t, "FeCurveSlats_L");
            s.cslR = Find(t, "FeCurveSlats_R");
            s.rollF = Find(t, "FeSpin_BeltRollerFront");
            s.rollB = Find(t, "FeSpin_BeltRollerBack");
            s.junction = Find(t, "FeJunction");
            s.posts = Find(t, "FeJunctionPosts");
            s.wedge = Find(t, "FeJunctionWedge");
            if (s.slats != null) s.basePos = s.slats.localPosition;
            if (s.cslL != null) s.baseL = s.cslL.localRotation;
            if (s.cslR != null) s.baseR = s.cslR.localRotation;
            s.slide = Belt.IsRamp(block) ? (Vector3.forward + Vector3.up) : Vector3.forward;
            s.next = 0f;
            if (!Belt.IsRamp(block)) s.Apply(0, false, false, false, false, false);
        }

        static Transform Find(Transform t, string n)
        {
            // prefix: Blender renames a second "FeBeltSlats" in the same .blend to "FeBeltSlats.001"; exact names
            // first so "FeJunction" does not pick "FeJunctionPosts"
            Transform r = FindExact(t, n);
            return r != null ? r : FindPrefix(t, n);
        }

        static Transform FindExact(Transform t, string n)
        {
            if (t.name == n) return t;
            for (int i = 0; i < t.childCount; i++)
            {
                Transform r = FindExact(t.GetChild(i), n);
                if (r != null) return r;
            }
            return null;
        }

        static Transform FindPrefix(Transform t, string n)
        {
            if (t.name.StartsWith(n + ".", System.StringComparison.Ordinal)) return t;
            for (int i = 0; i < t.childCount; i++)
            {
                Transform r = FindPrefix(t.GetChild(i), n);
                if (r != null) return r;
            }
            return null;
        }

        static void Show(Transform t, bool on)
        {
            if (t != null && t.gameObject.activeSelf != on) t.gameObject.SetActive(on);
        }

        // openL / openR: another belt joins on that side; front: something takes the items in front;
        // both: it splits to both sides only (the V divider)
        void Apply(int m, bool openL, bool openR, bool front, bool both, bool unused)
        {
            mode = m;
            bool straight = m == 0, junc = m == 3;
            Show(slats, straight);
            Show(bed, straight);
            Show(rollF, straight);
            Show(rollB, straight);
            Show(setL, m == 1);
            Show(cslL, m == 1);
            Show(setR, m == 2);
            Show(cslR, m == 2);
            Show(junction, junc);
            Show(posts, junc);
            Show(wedge, junc && both);
            Show(railL, (straight || junc) && !openL);
            Show(railR, (straight || junc) && !openR);
            Show(end, (straight || junc) && !front);
        }

        void Update()
        {
            if (Time.time >= next)
            {
                next = Time.time + 0.5f;
                World world = GameManager.Instance == null ? null : GameManager.Instance.World;
                if (world != null)
                {
                    BlockValue bv = world.GetBlock(pos);
                    speed = Belt.Speed(world, pos, bv);
                    if (!Belt.IsRamp(bv.Block))
                    {
                        List<Vector3i> links = Belt.Links(world, pos, bv);
                        List<Vector3i> exits = Belt.Exits(world, pos, bv);
                        Vector3i l = Belt.Left(bv), f = Belt.Front(bv);
                        Vector3i pl = new Vector3i(pos.x + l.x, pos.y, pos.z + l.z);
                        Vector3i pr = new Vector3i(pos.x - l.x, pos.y, pos.z - l.z);
                        Vector3i pf = new Vector3i(pos.x + f.x, pos.y, pos.z + f.z);
                        bool outL = exits.Contains(pl), outR = exits.Contains(pr), outF = exits.Contains(pf);
                        int m = 0;
                        if (exits.Count >= 2) m = 3;
                        else if (outL) m = 1;
                        else if (outR) m = 2;
                        Apply(m, links.Contains(pl), links.Contains(pr), outF, outL && outR && !outF, false);
                    }
                }
            }
            if (speed <= 0f) return;
            if (mode == 1 || mode == 2)
            {
                // the slats turn around the back corner: radius 0.5 m, so speed / 0.5 rad/s
                angle = Mathf.Repeat(angle + speed / 0.5f * Mathf.Rad2Deg * Time.deltaTime, CurveStep);
                if (mode == 1 && cslL != null) cslL.localRotation = baseL * Quaternion.Euler(0f, -angle, 0f);
                if (mode == 2 && cslR != null) cslR.localRotation = baseR * Quaternion.Euler(0f, angle, 0f);
                return;
            }
            if (mode == 3 || slats == null) return;   // the junction table does not move
            offset = Mathf.Repeat(offset + speed * Time.deltaTime, Spacing);
            slats.localPosition = basePos + slide * offset;
        }
    }

    [UnityEngine.Scripting.Preserve]
    public class BlockFeConveyor : BlockFeKinetic
    {
        public override void Init()
        {
            base.Init();
            BeltTicker.Ensure();
        }

        public override void OnBlockRemoved(WorldBase _world, Chunk _chunk, Vector3i _blockPos, BlockValue _blockValue)
        {
            base.OnBlockRemoved(_world, _chunk, _blockPos, _blockValue);
            World w = _world as World;
            if (w != null && SingletonMonoBehaviour<ConnectionManager>.Instance.IsServer) Belt.DropAll(w, _blockPos);
        }

        public override void OnBlockEntityTransformAfterActivated(WorldBase _world, Vector3i _blockPos,
                                                                  BlockValue _blockValue, BlockEntityData _ebcd)
        {
            base.OnBlockEntityTransformAfterActivated(_world, _blockPos, _blockValue, _ebcd);
            BeltShape.Attach(_ebcd, _blockPos, this);
        }
    }

    // save the belts with the world (before the game unloads the items; at application quit it is too late)
    [HarmonyLib.HarmonyPatch(typeof(GameManager), "SaveAndCleanupWorld")]
    public static class Patch_GameManager_SaveAndCleanupWorld_Belts
    {
        public static void Prefix()
        {
            BeltStore.MarkDirty();
            BeltStore.Save();
        }
    }

    [HarmonyLib.HarmonyPatch(typeof(GameManager), "SaveWorld")]
    public static class Patch_GameManager_SaveWorld_Belts
    {
        public static void Prefix()
        {
            BeltStore.Save();
        }
    }
}
