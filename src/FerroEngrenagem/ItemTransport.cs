// D13: more ways to move and keep items, Create-like but plain.
//
//   Item Chute (FeChute=true): a closed vertical chute. Items put into any chute cell (belt pointing into it, funnel,
//     arm, a world machine behind it) fall one cell every 0.25 s; at the bottom they go into what is under the
//     column (crate, machine, belt, depot, vault). With an Industrial Fan under the column blowing UP, they rise
//     instead and leave at the top. Up to 4 stacks per cell (kept in BeltStore like belt items, saved with them).
//   Depot (FeDepot=true): holds one stack on top, in plain view. Belts, funnels and arms put; arms take. An in-line
//     station on top of it works on the stack like on a belt (press, inserter, doser...).
//   Item Vault (FeVault=true, a crate block): vaults touching each other are one storage: what goes into one fills
//     the cluster, an arm taking from one takes from the cluster.
//   Belt Tunnel (a belt, FeBeltTunnel=true): sorts by item: the left filter goes left, the right filter goes right,
//     everything else straight on (Settings window: item in hand, Mode = which side you set).
//
// C# 5 only.

using System.Collections.Generic;
using UnityEngine;

namespace FerroEngrenagem
{
    public static class ItemTransport
    {
        public const int ChuteCap = 4;
        static readonly Vector3i Up = new Vector3i(0, 1, 0), Down = new Vector3i(0, -1, 0);
        static readonly Vector3i[] Dirs6 =
        {
            new Vector3i(1, 0, 0), new Vector3i(-1, 0, 0), new Vector3i(0, 1, 0),
            new Vector3i(0, -1, 0), new Vector3i(0, 0, 1), new Vector3i(0, 0, -1)
        };

        static bool Flag(Block b, string prop)
        {
            return b != null && b.Properties != null && b.Properties.Contains(prop) && b.Properties.GetBool(prop);
        }

        public static bool IsChute(Block b) { return Flag(b, "FeChute"); }
        public static bool IsDepot(Block b) { return Flag(b, "FeDepot"); }
        public static bool IsVault(Block b) { return Flag(b, "FeVault"); }
        public static bool IsTunnel(Block b) { return Flag(b, "FeBeltTunnel"); }

        /// <summary>Holds items in BeltStore (chutes, depots): not a belt but its items are kept there.</summary>
        public static bool Holder(Block b) { return IsChute(b) || IsDepot(b); }

        static Vector3i Add(Vector3i a, Vector3i b) { return new Vector3i(a.x + b.x, a.y + b.y, a.z + b.z); }

        // ------------------------------------------------------------ insert / take
        /// <summary>Put st into a chute / depot (changes st.count). True when it all went in.</summary>
        public static bool Insert(World world, Vector3i p, ItemStack st)
        {
            Block b = world.GetBlock(p).Block;
            List<BeltItem> items = BeltStore.Items(p, true);
            if (IsDepot(b))
            {
                if (items.Count > 0)
                {
                    BeltItem it = items[0];
                    if (it.Stack.itemValue.type != st.itemValue.type) return false;
                    int max = Mathf.Max(1, st.itemValue.ItemClass.Stacknumber.Value);
                    int n = Mathf.Min(st.count, max - it.Stack.count);
                    if (n <= 0) return false;
                    it.Stack.count += n;
                    st.count -= n;
                }
                else
                {
                    BeltStore.Add(p, st.Clone(), 0.5f);
                    st.count = 0;
                }
                BeltStore.MarkDirty();
                return st.count <= 0;
            }
            if (items.Count >= ChuteCap) return false;
            BeltStore.Add(p, st.Clone(), 0.5f);
            st.count = 0;
            BeltStore.MarkDirty();
            return true;
        }

        /// <summary>Take up to amount from a chute / depot (peek = only look).</summary>
        public static ItemStack Take(Vector3i p, int amount, string filter, bool peek)
        {
            List<BeltItem> items = BeltStore.Items(p, false);
            if (items == null || items.Count == 0) return null;
            foreach (BeltItem it in items)
            {
                if (!string.IsNullOrEmpty(filter) && (it.Stack.itemValue.ItemClass == null || it.Stack.itemValue.ItemClass.GetItemName() != filter)) continue;
                int n = Mathf.Min(amount, it.Stack.count);
                ItemStack got = new ItemStack(it.Stack.itemValue.Clone(), n);
                if (!peek)
                {
                    it.Stack.count -= n;
                    if (it.Stack.count <= 0) items.Remove(it);
                    BeltStore.MarkDirty();
                }
                return got;
            }
            return null;
        }

        // ------------------------------------------------------------ chutes
        static bool FanUp(World world, Vector3i bottom)
        {
            Vector3i c = Add(bottom, Down);
            BlockValue bv = world.GetBlock(c);
            if (WorldMachines.Kind(bv.Block) != "fan" || Fluids.Rot(bv, Vector3.forward) != Up) return false;
            TorqueNet net = Kinetic.Get(world, c);
            return net != null && net.Running && net.Machines.ContainsKey(c);
        }

        static Vector3i Bottom(World world, Vector3i p)
        {
            Vector3i c = p;
            for (int i = 0; i < 64 && IsChute(world.GetBlock(Add(c, Down)).Block); i++) c = Add(c, Down);
            return c;
        }

        static float next;

        /// <summary>Every 0.25 s (BeltTicker): items fall (or rise) one cell; at the end they leave the column.</summary>
        public static void Tick(World world)
        {
            if (Time.time < next) return;
            next = Time.time + 0.25f;
            List<Vector3i> keys = new List<Vector3i>(BeltStore.Belts);
            HashSet<Vector3i> moved = new HashSet<Vector3i>();
            foreach (Vector3i p in keys)
            {
                List<BeltItem> items = BeltStore.Items(p, false);
                if (items == null || items.Count == 0 || world.GetChunkFromWorldPos(p) == null) continue;
                BlockValue bv = world.GetBlock(p);
                if (IsDepot(bv.Block)) { Depot(world, p, bv, items); continue; }
                if (!IsChute(bv.Block)) continue;
                if (moved.Contains(p)) continue;
                Vector3i dir = FanUp(world, Bottom(world, p)) ? Up : Down;
                Vector3i to = Add(p, dir);
                BeltItem it = items[0];
                BlockValue tb = world.GetBlock(to);
                bool done = false;
                if (IsChute(tb.Block))
                {
                    List<BeltItem> next2 = BeltStore.Items(to, true);
                    if (next2.Count < ChuteCap) { items.RemoveAt(0); next2.Add(it); moved.Add(to); done = true; }
                }
                else if (Belt.Is(tb.Block))
                {
                    List<BeltItem> bi = BeltStore.Items(to, true);
                    if (Belt.Room(bi, 0.5f)) { items.RemoveAt(0); it.P = 0.5f; bi.Add(it); Belt.ChooseExit(world, to, tb, it); done = true; }
                }
                else if (!tb.isair)
                {
                    ItemStack s = it.Stack;
                    if (BeltMachines.Insert(world, Fluids.ParentOf(world, to, tb), s) || s.count <= 0) { items.RemoveAt(0); done = true; }
                }
                if (done) BeltStore.MarkDirty();
            }
        }

        // ------------------------------------------------------------ depots
        static void Depot(World world, Vector3i p, BlockValue bv, List<BeltItem> items)
        {
            Vector3i st;
            BlockValue sbv;
            if (!Inline.StationAt(world, p, out st, out sbv)) return;
            BeltItem it = items[0];
            if (!Inline.Wants(world, st, sbv, it.Stack)) return;
            it.P = 0.5f;
            if (Inline.Work(world, p, st, sbv, it, 0.25f) && it.Stack.count <= 0) items.RemoveAt(0);
        }

        // ------------------------------------------------------------ vaults
        public static List<Vector3i> Cluster(World world, Vector3i start)
        {
            List<Vector3i> l = new List<Vector3i>();
            Block b = world.GetBlock(start).Block;
            HashSet<Vector3i> seen = new HashSet<Vector3i> { start };
            Queue<Vector3i> q = new Queue<Vector3i>();
            q.Enqueue(start);
            while (q.Count > 0 && l.Count < 64)
            {
                Vector3i c = q.Dequeue();
                l.Add(c);
                foreach (Vector3i d in Dirs6)
                {
                    Vector3i n = Add(c, d);
                    if (seen.Contains(n) || world.GetBlock(n).Block != b) continue;
                    seen.Add(n);
                    q.Enqueue(n);
                }
            }
            return l;
        }

        // ------------------------------------------------------------ tunnels
        public static List<Vector3i> TunnelExits(World world, Vector3i pos, BlockValue bv, ItemStack st, List<Vector3i> outs)
        {
            string name = st == null || st.itemValue.ItemClass == null ? "" : st.itemValue.ItemClass.GetItemName();
            Vector3i left = Belt.Left(bv);
            string fl = LogicStore.Field(pos, "fl"), fr = LogicStore.Field(pos, "fr");
            List<Vector3i> l = new List<Vector3i>();
            foreach (Vector3i o in outs)
            {
                Vector3i d = new Vector3i(o.x - pos.x, o.y - pos.y, o.z - pos.z);
                bool isLeft = d == left, isRight = d == new Vector3i(-left.x, -left.y, -left.z);
                if (isLeft) { if (fl.Length > 0 && fl == name) l.Add(o); }
                else if (isRight) { if (fr.Length > 0 && fr == name) l.Add(o); }
                else if (name != fl && name != fr) l.Add(o);
            }
            return l;
        }

        public static string DescribeTunnel(Vector3i pos)
        {
            string fl = LogicStore.Field(pos, "fl"), fr = LogicStore.Field(pos, "fr");
            return string.Format(Kinetic.Text("feTunnelInfo", "Tunnel: left {0}, right {1}, the rest straight on"),
                fl.Length == 0 ? "-" : ProcessMachine.ItemName(fl), fr.Length == 0 ? "-" : ProcessMachine.ItemName(fr));
        }

        public static string Describe(World world, Vector3i p, BlockValue bv)
        {
            List<BeltItem> items = BeltStore.Items(p, false);
            List<string> l = new List<string>();
            if (items != null) foreach (BeltItem it in items) l.Add(it.Stack.count + "x " + it.Stack.itemValue.ItemClass.GetLocalizedItemName());
            string t = l.Count == 0 ? Kinetic.Text("feHolderEmpty", "Empty") : string.Join(", ", l.ToArray());
            if (IsChute(bv.Block))
                t += "\n" + (FanUp(world, Bottom(world, p)) ? Kinetic.Text("feChuteUp", "A fan under the column blows the items UP")
                                                            : Kinetic.Text("feChuteDown", "Items fall to what is under the column"));
            else t += "\n" + Kinetic.Text("feDepotInfo", "Belts, funnels and arms put items here; arms take them; a station on top works on them");
            return t;
        }
    }

    // ------------------------------------------------------------------ Chute and Depot blocks (plain blocks)
    [UnityEngine.Scripting.Preserve]
    public class BlockFeHolder : Block
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

        public override bool HasBlockActivationCommands(WorldBase _world, BlockValue _blockValue, Vector3i _blockPos, EntityAlive _entityFocusing)
        {
            return true;
        }

        public override BlockActivationCommand[] GetBlockActivationCommands(WorldBase _world, BlockValue _blockValue, Vector3i _blockPos, EntityAlive _entityFocusing)
        {
            return new BlockActivationCommand[]
            {
                new BlockActivationCommand("fe_cast_take", "hand", true, false, null),
                new BlockActivationCommand("fe_put", "loot_sort", true, false, null),
                new BlockActivationCommand("take", "hand", Pickup.CanBuildHere(_world, _blockPos), false, null)
            };
        }

        public override bool OnBlockActivated(string _commandName, WorldBase _world, Vector3i _blockPos, BlockValue _blockValue, EntityPlayerLocal _player)
        {
            World w = _world as World;
            if (w == null) return false;
            if (_commandName == "fe_cast_take")
            {
                List<string> got = new List<string>();
                ItemStack s;
                while ((s = ItemTransport.Take(_blockPos, 100000, null, false)) != null)
                {
                    if (!_player.bag.AddItem(s)) GameManager.Instance.ItemDropServer(s, _player.GetPosition(), Vector3.zero, -1, 60f, false);
                    got.Add(s.count + "x " + s.itemValue.ItemClass.GetLocalizedItemName());
                }
                GameManager.ShowTooltip(_player, got.Count == 0 ? Kinetic.Text("feHolderEmpty", "Empty")
                    : string.Format(Kinetic.Text("feTookList", "Took: {0}"), string.Join(", ", got.ToArray())), false, false, 0f);
                return true;
            }
            if (_commandName == "fe_put")
            {
                ItemStack held = _player.inventory.holdingItemStack;
                if (held == null || held.IsEmpty()) return true;
                ItemStack c = held.Clone();
                int before = c.count;
                ItemTransport.Insert(w, _blockPos, c);
                if (c.count < before)
                {
                    ItemStack left = held.Clone();
                    left.count = c.count;
                    _player.inventory.SetItem(_player.inventory.holdingItemIdx, left.count > 0 ? left : ItemStack.Empty.Clone());
                }
                return true;
            }
            if (_commandName != "take") return false;
            takeItemWithTimer(_blockPos, _blockValue, _player, 1f);
            return true;
        }

        public override string GetActivationText(WorldBase _world, BlockValue _blockValue, Vector3i _blockPos, EntityAlive _entityFocusing)
        {
            World w = _world as World;
            if (w == null) return "";
            return KineticLookController.Escape(GetLocalizedBlockName() + "\n" + ItemTransport.Describe(w, _blockPos, _blockValue))
                   + "\n" + Kinetic.Text("feHintHolder", "{0} take the items - hold {0}: put, take");
        }
    }
}
