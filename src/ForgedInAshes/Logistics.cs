// D12 (PLANO_CADEIA.md 4.2): control of what passes on the belts.
//
//   Belt Splitter (a belt, FeBeltSplit=true): deals the items between its outputs in a ratio (front : each side),
//     set in its settings window: 1:1, 2:1, 3:1, 1:2, 1:3, front only, sides only.
//   Belt Gate (a belt, FeBeltGate=true): stops while it gets a signal (inverted: runs only while signalled).
//   Counter Belt (a belt, FeBeltCounter=true): counts the items leaving it and gives a 1 s signal every N.
//   Mechanical Arm (Class FeArm, powered): every FeArmSeconds it takes up to N items from what is BEHIND it (a crate,
//     a machine's products, the end of a belt) and gives them to what is IN FRONT (1 or 2 blocks away): a machine, a
//     crate, a burner, a generator or a belt. Item filter, amount and reach in its settings window.
//   Settings live in LogicStore (fields "ratio", "inv", "n", "c", "f", "a", "r").
//
// C# 5 only.

using System.Collections.Generic;
using UnityEngine;

namespace ForgedInAshes
{
    public static class Logistics
    {
        public static readonly string[] Ratios = { "1:1", "2:1", "3:1", "1:2", "1:3", "1:0", "0:1" };

        static bool Flag(Block b, string prop)
        {
            return b != null && b.Properties != null && b.Properties.Contains(prop) && b.Properties.GetBool(prop);
        }

        public static bool IsSplitter(Block b) { return Flag(b, "FeBeltSplit"); }
        public static bool IsGate(Block b) { return Flag(b, "FeBeltGate"); }
        public static bool IsCounter(Block b) { return Flag(b, "FeBeltCounter"); }

        public static string Ratio(Vector3i p)
        {
            string r = LogicStore.Field(p, "ratio");
            return r.Length == 0 ? "1:1" : r;
        }

        static readonly Dictionary<Vector3i, int> turn = new Dictionary<Vector3i, int>();

        /// <summary>Splitter: pick the next output by its ratio (outs[0] is the front when there is one).</summary>
        public static Vector3i Pick(World world, Vector3i pos, BlockValue bv, List<Vector3i> outs)
        {
            string[] t = Ratio(pos).Split(':');
            int wf = 1, ws = 1;
            if (t.Length == 2) { int.TryParse(t[0], out wf); int.TryParse(t[1], out ws); }
            Vector3i f = Belt.Front(bv);
            List<Vector3i> seq = new List<Vector3i>();
            foreach (Vector3i o in outs)
            {
                bool front = o.x - pos.x == f.x && o.z - pos.z == f.z;
                int w = front ? wf : ws;
                for (int i = 0; i < w; i++) seq.Add(o);
            }
            if (seq.Count == 0) return outs[0];
            int k;
            turn.TryGetValue(pos, out k);
            turn[pos] = k + 1;
            return seq[k % seq.Count];
        }

        /// <summary>Allowed outputs of a splitter (a 0 weight closes that way).</summary>
        public static List<Vector3i> Filter(Vector3i pos, BlockValue bv, List<Vector3i> outs)
        {
            string r = Ratio(pos);
            if (r != "1:0" && r != "0:1") return outs;
            Vector3i f = Belt.Front(bv);
            List<Vector3i> l = new List<Vector3i>();
            foreach (Vector3i o in outs)
            {
                bool front = o.x - pos.x == f.x && o.z - pos.z == f.z;
                if (front == (r == "1:0")) l.Add(o);
            }
            return l;
        }

        /// <summary>Gate: stopped now?</summary>
        public static bool GateShut(World world, Vector3i p)
        {
            bool sig = Signals.Active(world, p);
            return LogicStore.Field(p, "inv") == "1" ? !sig : sig;
        }

        // ------------------------------------------------------------ counter
        static readonly Dictionary<Vector3i, float> pulseUntil = new Dictionary<Vector3i, float>();

        public static int CounterN(Vector3i p)
        {
            int n;
            return int.TryParse(LogicStore.Field(p, "n"), out n) && n > 0 ? n : 10;
        }

        public static int CounterCount(Vector3i p)
        {
            int n;
            return int.TryParse(LogicStore.Field(p, "c"), out n) ? n : 0;
        }

        /// <summary>An item (stack of count) left the counter belt at p.</summary>
        public static void Counted(World world, Vector3i p, int count)
        {
            int c = CounterCount(p) + count;
            int n = CounterN(p);
            if (c >= n)
            {
                c %= n;
                pulseUntil[p] = Time.time + 1f;
                Signals.Changed(world, p);
            }
            LogicStore.SetField(p, "c", c.ToString());
        }

        public static bool CounterPulse(Vector3i p)
        {
            float t;
            return pulseUntil.TryGetValue(p, out t) && Time.time < t;
        }

        // ------------------------------------------------------------ mechanical arm
        public static readonly HashSet<Vector3i> Arms = new HashSet<Vector3i>();
        static readonly Dictionary<Vector3i, float> armNext = new Dictionary<Vector3i, float>();

        public static void TickArms(World world)
        {
            LogicStore.EnsureLoaded();
            foreach (KeyValuePair<Vector3i, string> kv in LogicStore.All)
                if (kv.Value.Contains("arm=1")) Arms.Add(kv.Key);
            List<Vector3i> gone = new List<Vector3i>();
            foreach (Vector3i p in Arms)
            {
                if (world.GetChunkFromWorldPos(p) == null) continue;
                BlockValue bv = world.GetBlock(p);
                if (!(bv.Block is BlockFeArm)) { gone.Add(p); continue; }
                float next;
                if (armNext.TryGetValue(p, out next) && Time.time < next) continue;
                armNext[p] = Time.time + Fluids.Prop(bv.Block, "FeArmSeconds", 1f);
                if (!Industrial.IsPowered(world, p)) continue;
                Move(world, p, bv);
            }
            foreach (Vector3i p in gone) { Arms.Remove(p); LogicStore.Set(p, null); }
        }

        public static int Reach(Vector3i p)
        {
            return LogicStore.Field(p, "r") == "2" ? 2 : 1;
        }

        public static int Amount(Vector3i p, int def)
        {
            int n;
            return int.TryParse(LogicStore.Field(p, "a"), out n) && n > 0 ? n : def;
        }

        static bool Matches(ItemStack st, string filter)
        {
            return string.IsNullOrEmpty(filter) || (st != null && st.itemValue.ItemClass != null && st.itemValue.ItemClass.GetItemName() == filter);
        }

        /// <summary>One move of the arm at p.</summary>
        static void Move(World world, Vector3i p, BlockValue bv)
        {
            Vector3i f = Fluids.Rot(bv, Vector3.forward);
            Vector3i src = new Vector3i(p.x - f.x, p.y - f.y, p.z - f.z);
            int r = Reach(p);
            Vector3i dst = new Vector3i(p.x + f.x * r, p.y + f.y * r, p.z + f.z * r);
            string filter = LogicStore.Field(p, "f");
            int amount = Amount(p, 8);
            ItemStack got = TakeFrom(world, src, amount, filter, true);
            if (got == null) return;
            if (!CanGive(world, dst, got)) return;
            got = TakeFrom(world, src, amount, filter, false);
            if (got == null) return;
            ItemStack left = Give(world, dst, got, f);
            if (left != null && left.count > 0)
            {
                // could not give it all: put the rest back where it came from, or drop it
                if (!PutBack(world, src, left))
                    GameManager.Instance.ItemDropServer(left, p.ToVector3() + new Vector3(0.5f, 0.8f, 0.5f), Vector3.zero, -1, 300f, false);
            }
            BeltMachines.Note(world, p, "arm moved " + (got.count - (left == null ? 0 : left.count)) + "x " + got.itemValue.ItemClass.GetItemName());
        }

        /// <summary>Take (or with peek only look at) up to amount items matching filter from the source cell.</summary>
        public static ItemStack TakeFrom(World world, Vector3i c, int amount, string filter, bool peek)
        {
            BlockValue cb = world.GetBlock(c);
            if (cb.isair) return null;
            if (Belt.Is(cb.Block))
            {
                List<BeltItem> items = BeltStore.Items(c, false);
                if (items == null || items.Count == 0) return null;
                BeltItem best = null;
                foreach (BeltItem it in items) if (Matches(it.Stack, filter) && (best == null || it.P > best.P)) best = it;
                if (best == null || best.P < 0.6f) return null;
                int n = Mathf.Min(amount, best.Stack.count);
                ItemStack got = new ItemStack(best.Stack.itemValue.Clone(), n);
                if (!peek)
                {
                    best.Stack.count -= n;
                    if (best.Stack.count <= 0) items.Remove(best);
                    BeltStore.MarkDirty();
                }
                return got;
            }
            Vector3i par = Fluids.ParentOf(world, c, cb);
            if (ItemTransport.Holder(cb.Block)) return ItemTransport.Take(c, amount, filter, peek);
            if (ItemTransport.IsVault(cb.Block))
            {
                foreach (Vector3i v in ItemTransport.Cluster(world, c))
                {
                    if (v == c) continue;
                    ItemStack g = TakeStorage(world, v, amount, filter, peek);
                    if (g != null) return g;
                }
            }
            if (ProcessMachine.Is(cb.Block))
            {
                FluidState s = FluidStore.Get(par);
                Dictionary<string, int> o = ProcessMachine.Outs(s);
                foreach (KeyValuePair<string, int> kv in o)
                {
                    if (!string.IsNullOrEmpty(filter) && kv.Key != filter) continue;
                    ItemValue iv = ItemClass.GetItem(kv.Key, false);
                    if (iv == null || iv.IsEmpty()) continue;
                    int n = Mathf.Min(amount, kv.Value);
                    if (!peek)
                    {
                        o[kv.Key] = kv.Value - n;
                        s.Out = ProcessMachine.Unmap(o);
                        FluidStore.MarkDirty();
                    }
                    return new ItemStack(iv, n);
                }
                return null;
            }
            TileEntity te = world.GetTileEntity(par);
            if (te == null || te.IsUserAccessing()) return null;
            TileEntityWorkstation ws = te as TileEntityWorkstation;
            if (ws != null)
            {
                ItemStack[] outp = ws.Output;
                if (outp == null) return null;
                for (int i = 0; i < outp.Length; i++)
                {
                    if (outp[i] == null || outp[i].IsEmpty() || !Matches(outp[i], filter)) continue;
                    int n = Mathf.Min(amount, outp[i].count);
                    ItemStack got = new ItemStack(outp[i].itemValue.Clone(), n);
                    if (!peek)
                    {
                        outp[i].count -= n;
                        if (outp[i].count <= 0) outp[i] = ItemStack.Empty.Clone();
                        ws.Output = outp;
                        ws.SetModified();
                    }
                    return got;
                }
                return null;
            }
            return TakeStorage(world, par, amount, filter, peek);
        }

        static ItemStack TakeStorage(World world, Vector3i par, int amount, string filter, bool peek)
        {
            TileEntityComposite tc = world.GetTileEntity(par) as TileEntityComposite;
            if (tc == null || tc.IsUserAccessing()) return null;
            TEFeatureStorage store = tc.GetFeature<TEFeatureStorage>();
            if (store == null || store.ItemGrid == null) return null;
            ItemStackGrid grid = store.ItemGrid;
            for (int i = 0; i < grid.Length; i++)
            {
                ItemStack slot = grid[i];
                if (slot == null || slot.IsEmpty() || !Matches(slot, filter)) continue;
                int n = Mathf.Min(amount, slot.count);
                ItemStack got = new ItemStack(slot.itemValue.Clone(), n);
                if (!peek)
                {
                    ItemStack rest = slot.Clone();
                    rest.count -= n;
                    store.UpdateSlot(i, rest.count > 0 ? rest : ItemStack.Empty.Clone());
                    tc.SetModified();
                }
                return got;
            }
            return null;
        }

        static bool CanGive(World world, Vector3i dst, ItemStack st)
        {
            BlockValue db = world.GetBlock(dst);
            if (db.isair) return false;
            if (Belt.Is(db.Block)) return Belt.Room(BeltStore.Items(dst, false), 0.5f);
            return true;
        }

        /// <summary>Give st to the cell in front; returns what is left (null = all given).</summary>
        static ItemStack Give(World world, Vector3i dst, ItemStack st, Vector3i dir)
        {
            BlockValue db = world.GetBlock(dst);
            if (Belt.Is(db.Block))
            {
                List<BeltItem> items = BeltStore.Items(dst, true);
                if (!Belt.Room(items, 0.5f)) return st;
                BeltItem it = BeltStore.Add(dst, st, 0.5f);
                Belt.ChooseExit(world, dst, db, it);
                return null;
            }
            Vector3i par = Fluids.ParentOf(world, dst, db);
            ItemStack copy = st.Clone();
            BeltMachines.Insert(world, par, copy);
            return copy.count > 0 ? copy : null;
        }

        static bool PutBack(World world, Vector3i src, ItemStack st)
        {
            BlockValue sb = world.GetBlock(src);
            if (Belt.Is(sb.Block))
            {
                List<BeltItem> items = BeltStore.Items(src, true);
                if (!Belt.Room(items, 0.9f)) return false;
                BeltItem it = BeltStore.Add(src, st, 0.9f);
                Belt.ChooseExit(world, src, sb, it);
                return true;
            }
            ItemStack copy = st.Clone();
            BeltMachines.Insert(world, Fluids.ParentOf(world, src, sb), copy);
            return copy.count <= 0;
        }

        public static string DescribeArm(World world, Vector3i p, BlockValue bv)
        {
            string f = LogicStore.Field(p, "f");
            string t = string.Format(Kinetic.Text("feArmInfo", "Takes from behind, gives {0} block(s) in front, {1} at a time"), Reach(p), Amount(p, 8));
            t += "\n" + (f.Length == 0 ? Kinetic.Text("feArmAny", "Filter: any item")
                                       : string.Format(Kinetic.Text("feArmFilter", "Filter: {0}"), ProcessMachine.ItemName(f)));
            if (!Industrial.IsPowered(world, p)) t += "\n" + Kinetic.Text("feFluidNoPower", "No power: wire it to a power source");
            return t;
        }
    }

    // ------------------------------------------------------------------ Mechanical Arm block (powered)
    [UnityEngine.Scripting.Preserve]
    public class BlockFeArm : BlockPowered
    {
        public override void OnBlockAdded(WorldBase _world, Chunk _chunk, Vector3i _blockPos, BlockValue _blockValue,
                                          PlatformUserIdentifierAbs _addedByPlayer)
        {
            base.OnBlockAdded(_world, _chunk, _blockPos, _blockValue, _addedByPlayer);
            if (_blockValue.ischild) return;
            LogicStore.SetField(_blockPos, "arm", "1");
            Logistics.Arms.Add(_blockPos);
            BeltTicker.Ensure();
        }

        public override void OnBlockRemoved(WorldBase _world, Chunk _chunk, Vector3i _blockPos, BlockValue _blockValue)
        {
            base.OnBlockRemoved(_world, _chunk, _blockPos, _blockValue);
            Logistics.Arms.Remove(_blockPos);
            LogicStore.Set(_blockPos, null);
        }

        public override string GetActivationText(WorldBase _world, BlockValue _blockValue, Vector3i _blockPos, EntityAlive _entityFocusing)
        {
            World w = _world as World;
            if (w == null) return base.GetActivationText(_world, _blockValue, _blockPos, _entityFocusing);
            if (!Logistics.Arms.Contains(_blockPos)) { LogicStore.SetField(_blockPos, "arm", "1"); Logistics.Arms.Add(_blockPos); }
            return KineticLookController.Escape(GetLocalizedBlockName() + "\n" + Logistics.DescribeArm(w, _blockPos, _blockValue))
                   + "\n" + Kinetic.Text("feHintConfig", "{0} settings - hold {0}: take");
        }
    }

    // ------------------------------------------------------------------ Signal Lever (plain block) and Receiver (powered)
    [UnityEngine.Scripting.Preserve]
    public class BlockFeLever : Block
    {
        public override bool HasBlockActivationCommands(WorldBase _world, BlockValue _blockValue, Vector3i _blockPos, EntityAlive _entityFocusing)
        {
            return true;
        }

        public override BlockActivationCommand[] GetBlockActivationCommands(WorldBase _world, BlockValue _blockValue, Vector3i _blockPos, EntityAlive _entityFocusing)
        {
            return new BlockActivationCommand[]
            {
                new BlockActivationCommand("fe_lever", "electric_switch", true, false, null),
                new BlockActivationCommand("take", "hand", Pickup.CanBuildHere(_world, _blockPos), false, null)
            };
        }

        public override bool OnBlockActivated(string _commandName, WorldBase _world, Vector3i _blockPos, BlockValue _blockValue, EntityPlayerLocal _player)
        {
            World w = _world as World;
            if (_commandName == "fe_lever" && w != null)
            {
                if (Signals.Kind(this) == "analog")
                {
                    int v;
                    int.TryParse(LogicStore.Field(_blockPos, "lv"), out v);
                    v = (v + 1) % 16;
                    LogicStore.SetField(_blockPos, "lv", v.ToString());
                    Signals.Changed(w, _blockPos);
                    GameManager.ShowTooltip(_player, string.Format(Kinetic.Text("feAnalogLevel", "Signal strength: {0} / 15"), v), false, false, 0f);
                }
                else if (Signals.Kind(this) == "wtx" || Signals.Kind(this) == "wrx")
                {
                    FeUi.OpenConfig(_player, _blockPos);
                }
                else GameManager.ShowTooltip(_player, Signals.Toggle(w, _blockPos), false, false, 0f);
                return true;
            }
            if (_commandName != "take") return false;
            takeItemWithTimer(_blockPos, _blockValue, _player, 1f);
            return true;
        }

        public override void OnBlockRemoved(WorldBase _world, Chunk _chunk, Vector3i _blockPos, BlockValue _blockValue)
        {
            base.OnBlockRemoved(_world, _chunk, _blockPos, _blockValue);
            World w = _world as World;
            LogicStore.Set(_blockPos, null);
            if (w != null) Signals.Changed(w, _blockPos);
        }

        public override string GetActivationText(WorldBase _world, BlockValue _blockValue, Vector3i _blockPos, EntityAlive _entityFocusing)
        {
            World w = _world as World;
            string k = Signals.Kind(this);
            string state;
            if (k == "analog") state = string.Format(Kinetic.Text("feAnalogLevel", "Signal strength: {0} / 15"), LogicStore.Field(_blockPos, "lv").Length == 0 ? "0" : LogicStore.Field(_blockPos, "lv"));
            else if ((k == "wtx" || k == "wrx") && w != null)
            {
                string f = Signals.Freq(_blockPos);
                state = (f.Length == 0 ? Kinetic.Text("feWirelessNoFreq", "No frequency: E, then Item in hand") : string.Format(Kinetic.Text("feWirelessFreq", "Frequency: {0}"), ProcessMachine.ItemName(f)))
                        + " - " + ((k == "wtx" ? Signals.Active(w, _blockPos) : Signals.Emits(w, _blockPos)) ? Kinetic.Text("feSignalOn", "SIGNAL ON") : Kinetic.Text("feSignalOff", "no signal"));
            }
            else state = LogicStore.Get(_blockPos) == "1" ? Kinetic.Text("feSignalOn", "SIGNAL ON") : Kinetic.Text("feSignalOff", "no signal");
            return KineticLookController.Escape(GetLocalizedBlockName() + "\n" + state)
                   + "\n" + (k == "wtx" || k == "wrx" ? Kinetic.Text("feHintConfig", "{0} settings - hold {0}: take") : Kinetic.Text("feHintLever", "{0} pull the lever - hold {0}: take"));
        }
    }
}
