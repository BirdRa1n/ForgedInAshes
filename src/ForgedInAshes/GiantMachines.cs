// D14 (user 2026-11-27): two giant machines, bigger than a small house, that work a whole chunk-sized area.
//
//   Mining Rig (feMiningRig, FeWorld="miner")
//     Needs a lot of torque in its motor socket (FeMinPower, a shaft on its socket side). Works the disc of radius
//     FeMineRadius (16 = one chunk) under it, layer by layer from just below its base down to bedrock. Every terrain
//     cell (stone, ores, sand, gravel, soil) gives its Harvest drops, and every one that is not soil becomes soil
//     (terrDirt, same density): the ground keeps its shape, there are no holes. The only hole is the drill shaft under
//     its centre. Each cell is visited once (cursor in LogicStore), so a rig ends up exhausted. Products go out of its
//     FRONT (the cell in front of the middle of its front face, at ground level): belt, crate, chute or machine; they
//     wait in an internal buffer (FeMineBuffer stacks) and the rig pauses while that is full.
//   Oil Extractor (feOilExtractor, FeWorld="oilwell", FeFluid="oilwell")
//     Surveys the disc of radius FeSurveyRadius under it (without breaking anything) and counts the shale blocks
//     (terrOreOilDeposit): the reserve is shale x FeLitresPerShale. With torque in its socket it pumps crude oil at
//     FeFluidRate L/min (x speed) until the reserve is gone; the oil leaves through its front port and needs High
//     Pressure Pipes (FeNeedPipeBar: on a weaker pipe network it leaks).
//
// Both are multi-block ModelEntity blocks (BlockFeGiant); state in LogicStore; ticked by WorldMachines.TickAll.
// Server / host. C# 5 only.

using System.Collections.Generic;
using System.Globalization;
using System.Text;
using UnityEngine;

namespace ForgedInAshes
{
    /// <summary>World cells of multi-block blocks.</summary>
    public static class MultiCells
    {
        /// <summary>Every world cell of the block whose parent is at parent (just parent for a 1x1 block).</summary>
        public static List<Vector3i> Of(BlockValue bv, Vector3i parent)
        {
            List<Vector3i> l = new List<Vector3i>();
            Block b = bv.Block;
            if (b == null || !b.isMultiBlock || b.multiBlockPos == null) { l.Add(parent); return l; }
            for (int i = 0; i < b.multiBlockPos.Length; i++)
            {
                Vector3i o = b.multiBlockPos.Get(i, bv.type, bv.rotation);
                l.Add(new Vector3i(parent.x + o.x, parent.y + o.y, parent.z + o.z));
            }
            return l;
        }

        /// <summary>The bottom-layer cell at the middle of the face of the block that looks along the rotated local
        /// direction local (Vector3.forward = its front), and that direction in the world.</summary>
        public static Vector3i Edge(BlockValue bv, Vector3i parent, Vector3 local, out Vector3i dir)
        {
            dir = Fluids.Rot(bv, local);
            List<Vector3i> cells = Of(bv, parent);
            int minY = int.MaxValue;
            foreach (Vector3i c in cells) minY = Mathf.Min(minY, c.y);
            int best = int.MinValue;
            foreach (Vector3i c in cells)
                if (c.y == minY) best = Mathf.Max(best, (c.x - parent.x) * dir.x + (c.z - parent.z) * dir.z);
            List<Vector3i> edge = new List<Vector3i>();
            foreach (Vector3i c in cells)
                if (c.y == minY && (c.x - parent.x) * dir.x + (c.z - parent.z) * dir.z == best) edge.Add(c);
            Vector3i d = dir;
            edge.Sort(delegate (Vector3i a, Vector3i b) { return (a.x * d.z + a.z * d.x).CompareTo(b.x * d.z + b.z * d.x); });
            return edge.Count == 0 ? parent : edge[edge.Count / 2];
        }

        /// <summary>The outward faces of the bottom layer: (cell, outward direction), for ports all around.</summary>
        public static List<KeyValuePair<Vector3i, Vector3i>> BottomFaces(BlockValue bv, Vector3i parent)
        {
            List<Vector3i> cells = Of(bv, parent);
            HashSet<Vector3i> set = new HashSet<Vector3i>(cells);
            int minY = int.MaxValue;
            foreach (Vector3i c in cells) minY = Mathf.Min(minY, c.y);
            Vector3i[] dirs = { new Vector3i(1, 0, 0), new Vector3i(-1, 0, 0), new Vector3i(0, 0, 1), new Vector3i(0, 0, -1) };
            List<KeyValuePair<Vector3i, Vector3i>> l = new List<KeyValuePair<Vector3i, Vector3i>>();
            foreach (Vector3i c in cells)
            {
                if (c.y != minY) continue;
                foreach (Vector3i d in dirs)
                    if (!set.Contains(new Vector3i(c.x + d.x, c.y, c.z + d.z))) l.Add(new KeyValuePair<Vector3i, Vector3i>(c, d));
            }
            return l;
        }

        public static int MinY(BlockValue bv, Vector3i parent)
        {
            int minY = int.MaxValue;
            foreach (Vector3i c in Of(bv, parent)) minY = Mathf.Min(minY, c.y);
            return minY;
        }
    }

    public static class GiantMachines
    {
        static readonly Dictionary<int, List<Vector2i>> discs = new Dictionary<int, List<Vector2i>>();

        /// <summary>Columns of a disc of radius r around (0,0), nearest first (the rig digs outwards).</summary>
        public static List<Vector2i> Disc(int r)
        {
            List<Vector2i> l;
            if (discs.TryGetValue(r, out l)) return l;
            l = new List<Vector2i>();
            for (int x = -r; x <= r; x++)
                for (int z = -r; z <= r; z++)
                    if (x * x + z * z <= r * r) l.Add(new Vector2i(x, z));
            l.Sort(delegate (Vector2i a, Vector2i b) { return (a.x * a.x + a.y * a.y).CompareTo(b.x * b.x + b.y * b.y); });
            discs[r] = l;
            return l;
        }

        static int I(Vector3i p, string k)
        {
            int v;
            return int.TryParse(LogicStore.Field(p, k), out v) ? v : 0;
        }

        static float F(Vector3i p, string k)
        {
            float v;
            return float.TryParse(LogicStore.Field(p, k), NumberStyles.Float, CultureInfo.InvariantCulture, out v) ? v : 0f;
        }

        static void SetF(Vector3i p, string k, float v)
        {
            LogicStore.SetField(p, k, v.ToString("0.###", CultureInfo.InvariantCulture));
        }

        static void Note(Vector3i p, string why) { LogicStore.SetField(p, "note", why); }

        /// <summary>Speed of a machine powered through its motor socket (0 = stopped / not enough torque).</summary>
        public static float SocketSpeed(World world, Vector3i p, BlockValue bv)
        {
            TorqueNet net = Kinetic.Get(world, PowerGate.SocketPos(bv, p));
            if (net == null || !net.Running || !net.Machines.ContainsKey(p)) return 0f;
            return net.MachineSpeed(p);
        }

        public static bool Off(Vector3i p) { return LogicStore.Field(p, "off") == "1"; }

        public static void Toggle(Vector3i p) { LogicStore.SetField(p, "off", Off(p) ? "" : "1"); }

        static bool IsBedrock(Block b)
        {
            string n = b.GetBlockName();
            return n.IndexOf("edrock", System.StringComparison.Ordinal) >= 0;
        }

        static bool IsShale(Block b)
        {
            string n = b.GetBlockName();
            return n.IndexOf("OilDeposit", System.StringComparison.Ordinal) >= 0 || n.IndexOf("OilShale", System.StringComparison.Ordinal) >= 0;
        }

        static bool IsSoil(Block b)
        {
            return b.GetBlockName() == "terrDirt";
        }

        // ------------------------------------------------------------ buffer ("item:n,item:n")
        static List<ItemStack> Buffer(Vector3i p)
        {
            List<ItemStack> l = new List<ItemStack>();
            foreach (string part in LogicStore.Field(p, "buf").Split(','))
            {
                int c = part.LastIndexOf(':');
                int n;
                if (c <= 0 || !int.TryParse(part.Substring(c + 1), out n) || n <= 0) continue;
                ItemValue iv = ItemClass.GetItem(part.Substring(0, c), false);
                if (iv != null && !iv.IsEmpty()) l.Add(new ItemStack(iv, n));
            }
            return l;
        }

        static void SetBuffer(Vector3i p, List<ItemStack> l)
        {
            Dictionary<string, int> sum = new Dictionary<string, int>();
            List<string> order = new List<string>();
            foreach (ItemStack s in l)
            {
                if (s == null || s.IsEmpty() || s.itemValue.ItemClass == null) continue;
                string n = s.itemValue.ItemClass.GetItemName();
                if (!sum.ContainsKey(n)) { sum[n] = 0; order.Add(n); }
                sum[n] += s.count;
            }
            StringBuilder sb = new StringBuilder();
            foreach (string n in order)
            {
                if (sb.Length > 0) sb.Append(',');
                sb.Append(n).Append(':').Append(sum[n]);
            }
            LogicStore.SetField(p, "buf", sb.ToString());
        }

        static int Stacks(List<ItemStack> l)
        {
            int n = 0;
            foreach (ItemStack s in l)
            {
                int max = s.itemValue.ItemClass == null ? 1 : Mathf.Max(1, s.itemValue.ItemClass.Stacknumber.Value);
                n += (s.count + max - 1) / max;
            }
            return n;
        }

        /// <summary>Push the buffer into the block in front of the output face (belt, crate, chute, machine).</summary>
        static void Flush(World world, Vector3i p, BlockValue bv, List<ItemStack> buf)
        {
            Vector3i dir;
            Vector3i edge = MultiCells.Edge(bv, p, Vector3.forward, out dir);
            Vector3i outCell = new Vector3i(edge.x + dir.x, edge.y, edge.z + dir.z);
            if (world.GetChunkFromWorldPos(outCell) == null) return;
            BlockValue ob = world.GetBlock(outCell);
            if (ob.isair) return;
            for (int i = 0; i < buf.Count; i++)
            {
                ItemStack s = buf[i];
                if (s.count <= 0) continue;
                int max = s.itemValue.ItemClass == null ? 1 : Mathf.Max(1, s.itemValue.ItemClass.Stacknumber.Value);
                ItemStack part = new ItemStack(s.itemValue.Clone(), Mathf.Min(max, s.count));
                int before = part.count;
                if (Belt.Is(ob.Block))
                {
                    List<BeltItem> its = BeltStore.Items(outCell, true);
                    if (!Belt.Room(its, 0.5f)) return;
                    BeltItem it = BeltStore.Add(outCell, part, 0.5f);
                    Belt.ChooseExit(world, outCell, ob, it);
                    s.count -= before;
                    return;   // one stack per tick onto a belt
                }
                BeltMachines.Insert(world, Fluids.ParentOf(world, outCell, ob), part);
                s.count -= before - part.count;
                if (part.count > 0) return;   // the target is full
            }
        }

        // ------------------------------------------------------------ Mining Rig
        public static void TickMiner(World world, Vector3i p, BlockValue bv, float dt)
        {
            List<ItemStack> buf = Buffer(p);
            Flush(world, p, bv, buf);
            buf.RemoveAll(delegate (ItemStack s) { return s.count <= 0; });
            try
            {
                if (LogicStore.Field(p, "done") == "1") { Note(p, "done"); return; }
                if (Off(p)) { Note(p, "off"); return; }
                if (Stacks(buf) >= (int)Fluids.Prop(bv.Block, "FeMineBuffer", 40f)) { Note(p, "full"); return; }
                float v = SocketSpeed(world, p, bv);
                if (v <= 0f) { Note(p, "torque"); return; }
                float budget = F(p, "carry") + dt * v * Fluids.Prop(bv.Block, "FeMineRate", 8f);
                int n = Mathf.Min(64, (int)budget);
                SetF(p, "carry", budget - n);
                int r = (int)Fluids.Prop(bv.Block, "FeMineRadius", 16f);
                List<Vector2i> disc = Disc(r);
                int baseY = MultiCells.MinY(bv, p);
                int layer = Mathf.Max(1, I(p, "y"));
                int idx = I(p, "i");
                List<BlockChangeInfo> changes = new List<BlockChangeInfo>();
                Block dirt = Block.GetBlockByName("terrDirt", false);
                BlockValue dirtBv = dirt == null ? BlockValue.Air : WorldMachines.Bv(dirt);
                int mined = I(p, "mined"), ores = I(p, "ores");
                for (int k = 0; k < n; k++)
                {
                    int y = baseY - layer;
                    if (y < 3) { LogicStore.SetField(p, "done", "1"); break; }
                    Vector2i c = disc[idx];
                    Vector3i cell = new Vector3i(p.x + c.x, y, p.z + c.y);
                    if (world.GetChunkFromWorldPos(cell) == null) { Note(p, "chunk"); break; }
                    BlockValue t = world.GetBlock(cell);
                    bool shaft = c.x == 0 && c.y == 0;
                    if (!t.isair && !t.isWater && t.Block.shape != null && t.Block.shape.IsTerrain() && !IsBedrock(t.Block))
                    {
                        Vector3 at = cell.ToVector3() + new Vector3(0.5f, 0.5f, 0.5f);
                        buf.AddRange(WorldMachines.Drops(world, t, cell, at));
                        mined++;
                        if (t.Block.GetBlockName().StartsWith("terrOre", System.StringComparison.Ordinal)) ores++;
                        if (shaft) changes.Add(new BlockChangeInfo(cell, BlockValue.Air, MarchingCubes.DensityAir));
                        else if (!IsSoil(t.Block) && dirt != null) changes.Add(new BlockChangeInfo(cell, dirtBv, world.GetDensity(cell)));
                    }
                    else if (shaft && !t.isair && !t.isWater && IsBedrock(t.Block))
                    {
                        LogicStore.SetField(p, "done", "1");
                        break;
                    }
                    idx++;
                    if (idx >= disc.Count) { idx = 0; layer++; }
                }
                LogicStore.SetField(p, "y", layer.ToString());
                LogicStore.SetField(p, "i", idx.ToString());
                LogicStore.SetField(p, "mined", mined.ToString());
                LogicStore.SetField(p, "ores", ores.ToString());
                if (changes.Count > 0) world.SetBlocksRPC(changes);
                if (LogicStore.Field(p, "note") != "chunk") Note(p, "");
            }
            finally
            {
                SetBuffer(p, buf);
            }
        }

        // ------------------------------------------------------------ Oil Extractor
        public static void TickOilWell(World world, Vector3i p, BlockValue bv, float dt)
        {
            int r = (int)Fluids.Prop(bv.Block, "FeSurveyRadius", 24f);
            List<Vector2i> disc = Disc(r);
            int baseY = MultiCells.MinY(bv, p);
            if (LogicStore.Field(p, "surveyed") != "1")
            {
                // survey without breaking anything, a slice per tick (a radius-24 disc down to bedrock is ~100k cells)
                int layer = Mathf.Max(1, I(p, "sy"));
                int idx = I(p, "si");
                int shale = I(p, "shale");
                for (int k = 0; k < 3000; k++)
                {
                    int y = baseY - layer;
                    if (y < 3)
                    {
                        float litres = shale * Fluids.Prop(bv.Block, "FeLitresPerShale", 300f);
                        LogicStore.SetField(p, "surveyed", "1");
                        SetF(p, "left", litres);
                        SetF(p, "total", litres);
                        Log.Out(ForgedInAshesMod.LogPrefix + "oil extractor at " + p + ": " + shale + " shale blocks within " + r
                                + " blocks, reserve " + Mathf.RoundToInt(litres) + " L");
                        break;
                    }
                    Vector2i c = disc[idx];
                    Vector3i cell = new Vector3i(p.x + c.x, y, p.z + c.y);
                    if (world.GetChunkFromWorldPos(cell) == null) { Note(p, "chunk"); LogicStore.SetField(p, "sy", layer.ToString()); LogicStore.SetField(p, "si", idx.ToString()); LogicStore.SetField(p, "shale", shale.ToString()); return; }
                    BlockValue t = world.GetBlock(cell);
                    if (!t.isair && IsShale(t.Block)) shale++;
                    idx++;
                    if (idx >= disc.Count) { idx = 0; layer++; }
                }
                LogicStore.SetField(p, "sy", layer.ToString());
                LogicStore.SetField(p, "si", idx.ToString());
                LogicStore.SetField(p, "shale", shale.ToString());
                if (LogicStore.Field(p, "surveyed") != "1") { Note(p, "survey"); return; }
            }
            float left = F(p, "left");
            if (left <= 0.01f) { Note(p, "dry"); return; }
            if (Off(p)) { Note(p, "off"); return; }
            float v = SocketSpeed(world, p, bv);
            if (v <= 0f) { Note(p, "torque"); return; }
            FluidStore.EnsureLoaded();
            if (!FluidStore.Devices.Contains(p)) FluidStore.Register(p);
            FluidState s = FluidStore.Get(p);
            float cap = Fluids.Prop(bv.Block, "FeFluidBuffer", 2000f);
            float make = Mathf.Min(Mathf.Min(left, cap - s.Amount), Fluids.Prop(bv.Block, "FeFluidRate", 120f) * v * dt / 60f);
            if (make <= 0f) { Note(p, "full"); return; }
            s.Fluid = "crude_oil";
            s.Amount += make;
            SetF(p, "left", left - make);
            Note(p, "");
        }

        /// <summary>The oil extractor's single fluid port: out of the middle of its front face.</summary>
        public static void OilWellPorts(World world, Vector3i pos, BlockValue bv, List<FluidPort> l)
        {
            Vector3i dir;
            Vector3i edge = MultiCells.Edge(bv, pos, Vector3.forward, out dir);
            l.Add(new FluidPort { Owner = pos, Cell = edge, Dir = dir, Out = true, Fluid = "crude_oil" });
        }

        // ------------------------------------------------------------ readout
        public static string Describe(World world, Vector3i p, BlockValue bv)
        {
            string k = WorldMachines.Kind(bv.Block);
            StringBuilder sb = new StringBuilder();
            string note = LogicStore.Field(p, "note");
            if (k == "miner")
            {
                int r = (int)Fluids.Prop(bv.Block, "FeMineRadius", 16f);
                sb.Append(string.Format(Kinetic.Text("feMinerInfo", "Layer {0} below its base, radius {1} - {2} blocks worked, {3} of them ore"),
                    Mathf.Max(1, I(p, "y")), r, I(p, "mined"), I(p, "ores")));
                int st = Stacks(Buffer(p));
                if (st > 0) sb.Append("\n").Append(string.Format(Kinetic.Text("feMinerBuffer", "Waiting to leave by the front: {0} stacks"), st));
            }
            else if (k == "oilwell")
            {
                if (LogicStore.Field(p, "surveyed") != "1")
                    sb.Append(string.Format(Kinetic.Text("feOilSurvey", "Surveying the ground: layer {0}, {1} shale blocks so far"), Mathf.Max(1, I(p, "sy")), I(p, "shale")));
                else
                    sb.Append(string.Format(Kinetic.Text("feOilReserve", "Reserve: {0} of {1} L of crude oil ({2} shale blocks)"),
                        Mathf.RoundToInt(F(p, "left")), Mathf.RoundToInt(F(p, "total")), I(p, "shale")));
                FluidState s = FluidStore.Get(p);
                sb.Append("\n").Append(string.Format(Kinetic.Text("feOilBuffer", "In the tank: {0} L - needs High Pressure Pipes"), Mathf.RoundToInt(s.Amount)));
            }
            string why = NoteText(note);
            if (why.Length > 0) sb.Append("\n").Append(why);
            TorqueNet net = Kinetic.Get(world, PowerGate.SocketPos(bv, p));
            sb.Append("\n").Append(string.Format(Kinetic.Text("feGiantTorque", "Needs {0} UT in its motor socket"), PowerGate.MinPower(bv.Block)));
            if (net != null) sb.Append(" - ").Append(KineticLookController.Status(net, PowerGate.SocketPos(bv, p)));
            return sb.ToString();
        }

        static string NoteText(string note)
        {
            switch (note)
            {
                case "done": return Kinetic.Text("feMinerDone", "Exhausted: it reached bedrock");
                case "off": return Kinetic.Text("feGiantOff", "Switched off");
                case "full": return Kinetic.Text("feGiantFull", "Waiting: its output is full");
                case "torque": return Kinetic.Text("feGiantNoTorque", "Stopped: not enough torque in its motor socket");
                case "chunk": return Kinetic.Text("feGiantChunk", "Waiting for that part of the area to load");
                case "survey": return Kinetic.Text("feOilSurveying", "Surveying the shale vein...");
                case "dry": return Kinetic.Text("feOilDry", "Dry: the vein is exhausted (or there is no shale in reach)");
            }
            return "";
        }
    }

    /// <summary>The block class of the giant machines: registers with WorldMachines, shows its readout, On / Off.</summary>
    [UnityEngine.Scripting.Preserve]
    public class BlockFeGiant : Block
    {
        public override void Init()
        {
            base.Init();
            BeltTicker.Ensure();
        }

        public override void OnBlockAdded(WorldBase _world, Chunk _chunk, Vector3i _blockPos, BlockValue _blockValue, PlatformUserIdentifierAbs _addedByPlayer)
        {
            base.OnBlockAdded(_world, _chunk, _blockPos, _blockValue, _addedByPlayer);
            if (!_blockValue.ischild) WorldMachines.Register(_blockPos);
        }

        public override void OnBlockLoaded(WorldBase _world, Vector3i _blockPos, BlockValue _blockValue)
        {
            base.OnBlockLoaded(_world, _blockPos, _blockValue);
            if (!_blockValue.ischild) WorldMachines.Register(_blockPos);
        }

        // The model's moving parts (drill string, crown, drum, trommel; the pumpjack's crank and walking beam) turn
        // with the torque in the motor socket (KineticSpinner, machine mode: the parent block is the machine).
        public override void OnBlockEntityTransformAfterActivated(WorldBase _world, Vector3i _blockPos,
                                                                  BlockValue _blockValue, BlockEntityData _ebcd)
        {
            base.OnBlockEntityTransformAfterActivated(_world, _blockPos, _blockValue, _ebcd);
            if (!_blockValue.ischild) KineticSpinner.AttachMachine(_ebcd, _blockPos, this);
        }

        public override bool HasBlockActivationCommands(WorldBase _world, BlockValue _blockValue, Vector3i _blockPos, EntityAlive _entityFocusing)
        {
            return true;
        }

        public override BlockActivationCommand[] GetBlockActivationCommands(WorldBase _world, BlockValue _blockValue, Vector3i _blockPos, EntityAlive _entityFocusing)
        {
            return new BlockActivationCommand[] { new BlockActivationCommand("fe_onoff", "electric_switch", true, false, null) };
        }

        public override bool OnBlockActivated(string _commandName, WorldBase _world, Vector3i _blockPos, BlockValue _blockValue, EntityPlayerLocal _player)
        {
            Vector3i p = Fluids.ParentOf((World)_world, _blockPos, _blockValue);
            if (_commandName == "fe_onoff") { GiantMachines.Toggle(p); return true; }
            return false;
        }

        public override string GetActivationText(WorldBase _world, BlockValue _blockValue, Vector3i _blockPos, EntityAlive _entityFocusing)
        {
            World w = (World)_world;
            Vector3i p = Fluids.ParentOf(w, _blockPos, _blockValue);
            BlockValue pbv = w.GetBlock(p);
            string text = pbv.Block.GetLocalizedBlockName() + "\n" + GiantMachines.Describe(w, p, pbv);
            return KineticLookController.Escape(text) + "\n" + string.Format(Kinetic.Text("feGiantHint", "{0} on / off"), "{0}");
        }
    }
}
