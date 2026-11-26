// D13 (user 2026-11-25: "um Create com pé no chão"): torque machines that act on the world. Each is a torque
// consumer (FeKinetic=pump: a shaft on its left or right, FeTorqueCost UT) with FeWorld=<kind>; its FRONT is where
// it works. Ticked every 0.5 s by BeltTicker (server / host).
//
//   drill      Mechanical Drill: wears down the block in front (stone, ore, soil, wood blocks; not trees, not
//              containers, not the mod's machines, not bedrock) at FeWorkPower damage per second at 32 RPM; when it
//              breaks it gives its Harvest drops (as a pickaxe would) into the block BEHIND (crate, belt, chute,
//              machine) or drops them on the ground.
//   saw        Mechanical Saw: the same for trees (the whole tree) and wooden blocks; drops wood.
//   harvester  Mechanical Harvester: harvests the ripe crop in front (planted...Harvest blocks), gives the crop,
//              and plants the seed stage again.
//   deployer   Deployer: places the block / seed it holds into the cell in front (it takes items like a machine:
//              belt, arm, funnel or hand). One every FeWorkSeconds.
//   piston     Mechanical Piston: while it gets a signal it extends one block per FeWorkSeconds up to FeRange,
//              pushing up to 12 plain blocks (no containers, machines, trees or terrain); without the signal it
//              retracts. The head is the block "fePistonHead".
//   fan        Industrial Fan: blows FeRange blocks ahead. What is right in front of it decides what the air does:
//              water   -> it washes   (processes kind="wash" of machine feFan)
//              a lit Gas Burner -> it heats (processes kind="dry" of machine feFan)
//              nothing -> it only pushes the dropped items.
//              Items on belts and items on the ground in the air stream are processed after Time seconds of air.
//   State (work done, held item, piston length) in LogicStore.
//
// C# 5 only.

using System.Collections.Generic;
using System.Globalization;
using UnityEngine;

namespace ForgedInAshes
{
    public static class WorldMachines
    {
        public static readonly HashSet<Vector3i> All = new HashSet<Vector3i>();

        public static string Kind(Block b)
        {
            return b != null && b.Properties != null && b.Properties.Contains("FeWorld") ? b.Properties.GetString("FeWorld").Trim().ToLowerInvariant() : "";
        }

        public static bool Is(Block b) { return Kind(b).Length > 0; }

        public static BlockValue Bv(Block b)
        {
            BlockValue v = BlockValue.Air;
            v.type = b.blockID;
            return v;
        }

        static float F(Vector3i p, string key)
        {
            float v;
            return float.TryParse(LogicStore.Field(p, key), NumberStyles.Float, CultureInfo.InvariantCulture, out v) ? v : 0f;
        }

        static void SetF(Vector3i p, string key, float v)
        {
            LogicStore.SetField(p, key, v <= 0f ? "" : v.ToString("0.##", CultureInfo.InvariantCulture));
        }

        static float Speed(World world, Vector3i p)
        {
            TorqueNet net = Kinetic.Get(world, p);
            if (net == null || !net.Running || !net.Machines.ContainsKey(p)) return 0f;
            return net.MachineSpeed(p);
        }

        public static void Register(Vector3i p)
        {
            LogicStore.SetField(p, "wm", "1");
            All.Add(p);
            BeltTicker.Ensure();
        }

        public static void TickAll(World world)
        {
            LogicStore.EnsureLoaded();
            if (All.Count == 0)
                foreach (KeyValuePair<Vector3i, string> kv in LogicStore.All)
                    if (kv.Value.Contains("wm=1")) All.Add(kv.Key);
            List<Vector3i> gone = new List<Vector3i>();
            foreach (Vector3i p in All)
            {
                if (world.GetChunkFromWorldPos(p) == null) continue;
                BlockValue bv = world.GetBlock(p);
                string k = Kind(bv.Block);
                if (k.Length == 0) { gone.Add(p); continue; }
                try
                {
                    switch (k)
                    {
                        case "drill":
                        case "saw": Break(world, p, bv, k, 0.5f); break;
                        case "harvester": Harvest(world, p, bv, 0.5f); break;
                        case "deployer": Deploy(world, p, bv, 0.5f); break;
                        case "piston": Piston(world, p, bv, 0.5f); break;
                        case "fan": Fan.Tick(world, p, bv, 0.5f); break;
                    }
                }
                catch (System.Exception e)
                {
                    BeltMachines.Note(world, p, k + " failed: " + e.Message);
                }
            }
            foreach (Vector3i p in gone) { All.Remove(p); LogicStore.Set(p, null); }
        }

        static Vector3i Front(BlockValue bv, Vector3i p, int n)
        {
            Vector3i f = Fluids.Rot(bv, Vector3.forward);
            return new Vector3i(p.x + f.x * n, p.y + f.y * n, p.z + f.z * n);
        }

        static Vector3i Back(BlockValue bv, Vector3i p)
        {
            Vector3i f = Fluids.Rot(bv, Vector3.forward);
            return new Vector3i(p.x - f.x, p.y - f.y, p.z - f.z);
        }

        // ------------------------------------------------------------ drill / saw
        static bool IsTree(Block b)
        {
            return b != null && b.GetBlockName().StartsWith("tree", System.StringComparison.Ordinal);
        }

        static bool Breakable(World world, Vector3i c, BlockValue t, string kind, out string why)
        {
            why = "";
            if (t.isair || t.isWater) { why = "empty"; return false; }
            Block b = t.Block;
            string n = b.GetBlockName();
            if (n.StartsWith("fe", System.StringComparison.Ordinal) || n.Contains("Bedrock") || n.Contains("bedrock")) { why = "hard"; return false; }
            if (world.GetTileEntity(Fluids.ParentOf(world, c, t)) != null) { why = "container"; return false; }
            bool tree = IsTree(b);
            bool wood = b.blockMaterial != null && b.blockMaterial.id != null && b.blockMaterial.id.ToLowerInvariant().Contains("wood");
            if (kind == "saw") { if (!tree && !wood) { why = "notwood"; return false; } }
            else if (tree) { why = "tree"; return false; }
            return true;
        }

        static void Break(World world, Vector3i p, BlockValue bv, string kind, float dt)
        {
            Vector3i c = Front(bv, p, 1);
            BlockValue t = world.GetBlock(c);
            string why;
            if (!Breakable(world, c, t, kind, out why)) { SetF(p, "w", 0f); LogicStore.SetField(p, "note", why); return; }
            float v = Speed(world, p);
            if (v <= 0f) { LogicStore.SetField(p, "note", "torque"); return; }
            LogicStore.SetField(p, "note", "");
            Vector3i target = Fluids.ParentOf(world, c, t);
            BlockValue tb = world.GetBlock(target);
            float need = Mathf.Max(1f, tb.Block.MaxDamage);
            float w = F(p, "w") + dt * v * Fluids.Prop(bv.Block, "FeWorkPower", 60f);
            if (w < need) { SetF(p, "w", w); return; }
            SetF(p, "w", 0f);
            Vector3 drop = c.ToVector3() + new Vector3(0.5f, 0.5f, 0.5f);
            List<ItemStack> got = Drops(world, tb, target, drop);
            world.SetBlockRPC(target, BlockValue.Air);
            Deliver(world, p, bv, got, drop);
            BeltMachines.Note(world, p, kind + " broke " + tb.Block.GetBlockName() + " at " + target);
        }

        /// <summary>The Harvest drops of a block, collected as stacks (they are not spawned).</summary>
        static List<ItemStack> Drops(World world, BlockValue bv, Vector3i pos, Vector3 at)
        {
            List<ItemStack> l = new List<ItemStack>();
            if (bv.Block.itemsToDrop == null) return l;
            List<Block.SItemDropProb> list;
            if (!bv.Block.itemsToDrop.TryGetValue(EnumDropEvent.Harvest, out list) || list == null)
                if (!bv.Block.itemsToDrop.TryGetValue(EnumDropEvent.Destroy, out list) || list == null) return l;
            foreach (Block.SItemDropProb d in list)
            {
                if (string.IsNullOrEmpty(d.name) || Random.value > d.prob) continue;
                ItemValue iv = ItemClass.GetItem(d.name, false);
                if (iv == null || iv.IsEmpty()) continue;
                int n = d.minCount >= d.maxCount ? d.minCount : Random.Range(d.minCount, d.maxCount + 1);
                if (n > 0) l.Add(new ItemStack(iv, n));
            }
            return l;
        }

        /// <summary>Products go into the block behind the machine (crate, belt, chute, machine), else to the ground.</summary>
        static void Deliver(World world, Vector3i p, BlockValue bv, List<ItemStack> items, Vector3 at)
        {
            Vector3i back = Back(bv, p);
            BlockValue bb = world.GetBlock(back);
            foreach (ItemStack st in items)
            {
                ItemStack s = st.Clone();
                if (!bb.isair)
                {
                    if (Belt.Is(bb.Block))
                    {
                        List<BeltItem> its = BeltStore.Items(back, true);
                        if (Belt.Room(its, 0.5f)) { BeltItem it = BeltStore.Add(back, s, 0.5f); Belt.ChooseExit(world, back, bb, it); continue; }
                    }
                    else
                    {
                        BeltMachines.Insert(world, Fluids.ParentOf(world, back, bb), s);
                        if (s.count <= 0) continue;
                    }
                }
                GameManager.Instance.ItemDropServer(s, at, Vector3.zero, -1, 300f, false);
            }
        }

        // ------------------------------------------------------------ harvester
        public static string SeedOf(string crop)
        {
            // plantedCorn3HarvestPlayer -> plantedCorn1
            int i = crop.IndexOf("3Harvest", System.StringComparison.Ordinal);
            return i > 0 ? crop.Substring(0, i) + "1" : null;
        }

        static void Harvest(World world, Vector3i p, BlockValue bv, float dt)
        {
            if (Speed(world, p) <= 0f) { LogicStore.SetField(p, "note", "torque"); return; }
            float w = F(p, "w") + dt;
            if (w < Fluids.Prop(bv.Block, "FeWorkSeconds", 2f)) { SetF(p, "w", w); return; }
            SetF(p, "w", 0f);
            // the cell in front, and the one below it (crops grow on the plot under the machine's front)
            foreach (Vector3i c in new Vector3i[] { Front(bv, p, 1), new Vector3i(Front(bv, p, 1).x, p.y - 1, Front(bv, p, 1).z) })
            {
                BlockValue t = world.GetBlock(c);
                if (t.isair) continue;
                string n = t.Block.GetBlockName();
                string seed = SeedOf(n);
                if (seed == null) continue;
                Vector3 at = c.ToVector3() + new Vector3(0.5f, 0.5f, 0.5f);
                List<ItemStack> got = Drops(world, t, c, at);
                Block sb = Block.GetBlockByName(seed, false);
                world.SetBlockRPC(c, sb != null ? Bv(sb) : BlockValue.Air);
                Deliver(world, p, bv, got, at);
                LogicStore.SetField(p, "note", "");
                BeltMachines.Note(world, p, "harvested " + n + (sb != null ? ", replanted" : ""));
                return;
            }
            LogicStore.SetField(p, "note", "nocrop");
        }

        // ------------------------------------------------------------ deployer
        public static ItemStack Held(Vector3i p)
        {
            string n = LogicStore.Field(p, "item");
            int c;
            if (n.Length == 0 || !int.TryParse(LogicStore.Field(p, "n"), out c) || c <= 0) return null;
            ItemValue iv = ItemClass.GetItem(n, false);
            return iv == null || iv.IsEmpty() ? null : new ItemStack(iv, c);
        }

        static void SetHeld(Vector3i p, string item, int n)
        {
            LogicStore.SetField(p, "item", n > 0 ? item : "");
            LogicStore.SetField(p, "n", n > 0 ? n.ToString() : "");
        }

        /// <summary>A belt / arm / hand gives st to a world machine (only the Deployer keeps items). Returns how many.</summary>
        public static int Insert(World world, Vector3i p, ItemStack st)
        {
            if (Kind(world.GetBlock(p).Block) != "deployer" || st == null || st.IsEmpty() || st.itemValue.ItemClass == null) return 0;
            if (!st.itemValue.ItemClass.IsBlock()) return 0;
            ItemStack h = Held(p);
            string name = st.itemValue.ItemClass.GetItemName();
            if (h != null && h.itemValue.ItemClass.GetItemName() != name) return 0;
            int have = h == null ? 0 : h.count;
            int take = Mathf.Min(st.count, Mathf.Max(1, st.itemValue.ItemClass.Stacknumber.Value) - have);
            if (take <= 0) return 0;
            SetHeld(p, name, have + take);
            return take;
        }

        static void Deploy(World world, Vector3i p, BlockValue bv, float dt)
        {
            ItemStack h = Held(p);
            if (h == null) { LogicStore.SetField(p, "note", "empty"); return; }
            if (Speed(world, p) <= 0f) { LogicStore.SetField(p, "note", "torque"); return; }
            float w = F(p, "w") + dt;
            if (w < Fluids.Prop(bv.Block, "FeWorkSeconds", 1f)) { SetF(p, "w", w); return; }
            SetF(p, "w", 0f);
            Vector3i c = Front(bv, p, 1);
            BlockValue t = world.GetBlock(c);
            if (!t.isair) { LogicStore.SetField(p, "note", "blocked"); return; }
            BlockValue nb = h.itemValue.ToBlockValue(false);
            if (nb.isair) return;
            nb.rotation = bv.rotation;
            if (!nb.Block.CanPlaceBlockAt(world, c, nb, false)) { LogicStore.SetField(p, "note", "cannot"); return; }
            world.SetBlockRPC(c, nb);
            SetHeld(p, h.itemValue.ItemClass.GetItemName(), h.count - 1);
            LogicStore.SetField(p, "note", "");
        }

        // ------------------------------------------------------------ piston
        const int MaxPush = 12;

        static bool Movable(World world, Vector3i c, BlockValue t)
        {
            if (t.isair) return true;
            if (t.isWater || t.ischild || t.Block.isMultiBlock) return false;
            if (t.Block.shape != null && t.Block.shape.IsTerrain()) return false;
            if (world.GetTileEntity(c) != null) return false;
            string n = t.Block.GetBlockName();
            if (n == "fePistonHead") return false;
            if (n.StartsWith("fe", System.StringComparison.Ordinal) && (Fluids.Kind(t.Block) != FluidKind.None || Kinetic.Kind(t.Block) != KineticKind.None)) return false;
            return !IsTree(t.Block);
        }

        static void Piston(World world, Vector3i p, BlockValue bv, float dt)
        {
            int len = (int)F(p, "len");
            int range = (int)Fluids.Prop(bv.Block, "FeRange", 6f);
            bool want = Signals.Active(world, p);
            float w = F(p, "w") + dt * Mathf.Max(0f, Speed(world, p));
            if (w < Fluids.Prop(bv.Block, "FeWorkSeconds", 0.5f)) { SetF(p, "w", w); return; }
            SetF(p, "w", 0f);
            Block head = Block.GetBlockByName("fePistonHead", false);
            if (head == null) return;
            if (want && len < range)
            {
                // push: find the first air cell within MaxPush after the head
                Vector3i start = Front(bv, p, len + 1);
                int k = 0;
                for (; k <= MaxPush; k++)
                {
                    Vector3i c = Front(bv, p, len + 1 + k);
                    BlockValue t = world.GetBlock(c);
                    if (t.isair) break;
                    if (!Movable(world, c, t)) { LogicStore.SetField(p, "note", "blocked"); return; }
                }
                if (k > MaxPush) { LogicStore.SetField(p, "note", "blocked"); return; }
                for (int i = k; i > 0; i--)
                {
                    Vector3i from = Front(bv, p, len + i);
                    Vector3i to = Front(bv, p, len + 1 + i);
                    world.SetBlockRPC(to, world.GetBlock(from));
                }
                BlockValue hb = Bv(head);
                hb.rotation = bv.rotation;
                world.SetBlockRPC(start, hb);
                if (len > 0) world.SetBlockRPC(Front(bv, p, len), hb);   // the pole
                SetF(p, "len", len + 1);
                LogicStore.SetField(p, "note", "");
            }
            else if (!want && len > 0)
            {
                Vector3i tip = Front(bv, p, len);
                if (world.GetBlock(tip).Block == head) world.SetBlockRPC(tip, BlockValue.Air);
                SetF(p, "len", len - 1);
            }
        }

        // ------------------------------------------------------------ readout
        public static string Describe(World world, Vector3i p, BlockValue bv)
        {
            string k = Kind(bv.Block);
            string note = LogicStore.Field(p, "note");
            string t = "";
            switch (k)
            {
                case "drill":
                case "saw":
                {
                    Vector3i c = Front(bv, p, 1);
                    BlockValue tb = world.GetBlock(Fluids.ParentOf(world, c, world.GetBlock(c)));
                    float need = tb.isair ? 1f : Mathf.Max(1f, tb.Block.MaxDamage);
                    t = tb.isair ? Kinetic.Text("feWmNothing", "Nothing in front")
                                 : string.Format(Kinetic.Text("feWmBreaking", "Breaking {0}: {1}%"), tb.Block.GetLocalizedBlockName(), Mathf.RoundToInt(100f * F(p, "w") / need));
                    t += "\n" + Kinetic.Text("feWmDrops", "Drops go into the block behind it (crate, belt, chute) or to the ground");
                    break;
                }
                case "harvester": t = Kinetic.Text("feWmHarvest", "Harvests the ripe crop in front (or in front and below) and plants it again"); break;
                case "deployer":
                {
                    ItemStack h = Held(p);
                    t = h == null ? Kinetic.Text("feWmEmpty", "Holds nothing: give it blocks or seeds (belt, arm, hand)")
                                  : string.Format(Kinetic.Text("feWmHolds", "Holds {0}x {1}: places them in front"), h.count, h.itemValue.ItemClass.GetLocalizedItemName());
                    break;
                }
                case "piston":
                    t = string.Format(Kinetic.Text("feWmPiston", "Extended {0} / {1} - extends while it gets a signal"), (int)F(p, "len"), (int)Fluids.Prop(bv.Block, "FeRange", 6f));
                    break;
                case "fan": t = Fan.Describe(world, p, bv); break;
            }
            switch (note)
            {
                case "torque": t += "\n" + Kinetic.Text("feFluidNoTorque", "No torque on its shaft"); break;
                case "blocked": t += "\n" + Kinetic.Text("feWmBlocked", "Blocked"); break;
                case "container": t += "\n" + Kinetic.Text("feWmContainer", "It does not break containers"); break;
                case "tree": t += "\n" + Kinetic.Text("feWmTree", "Trees: use a Mechanical Saw"); break;
                case "notwood": t += "\n" + Kinetic.Text("feWmNotWood", "The saw cuts trees and wood only"); break;
                case "hard": t += "\n" + Kinetic.Text("feWmHard", "It cannot break this"); break;
                case "nocrop": t += "\n" + Kinetic.Text("feWmNoCrop", "No ripe crop in front"); break;
                case "cannot": t += "\n" + Kinetic.Text("feWmCannot", "It cannot place that there"); break;
            }
            return t;
        }

        public static string PutHeld(World world, Vector3i p, EntityPlayerLocal player)
        {
            ItemStack held = player.inventory.holdingItemStack;
            if (held == null || held.IsEmpty()) return Kinetic.Text("feWmHoldBlock", "Hold the blocks or seeds to give it");
            int n = Insert(world, p, held);
            if (n <= 0) return Kinetic.Text("fePourNo", "It does not take this (or it is full)");
            ItemStack left = held.Clone();
            left.count -= n;
            player.inventory.SetItem(player.inventory.holdingItemIdx, left.count > 0 ? left : ItemStack.Empty.Clone());
            return string.Format(Kinetic.Text("feProcPut", "Put in {0}"), n);
        }
    }

    // ------------------------------------------------------------------ Industrial Fan
    public static class Fan
    {
        static readonly Dictionary<int, float> beltExposure = new Dictionary<int, float>();
        static readonly Dictionary<int, float> dropExposure = new Dictionary<int, float>();

        public static string Medium(World world, Vector3i p, BlockValue bv, out int skip)
        {
            Vector3i f = Fluids.Rot(bv, Vector3.forward);
            Vector3i c = new Vector3i(p.x + f.x, p.y + f.y, p.z + f.z);
            skip = 1;
            if (world.IsWater(c.x, c.y, c.z)) return "wash";
            BlockValue t = world.GetBlock(c);
            if (Fluids.Kind(t.Block) == FluidKind.Burner)
            {
                Vector3i par = Fluids.ParentOf(world, c, t);
                if (!FluidStore.Devices.Contains(par)) FluidStore.Register(par);
                FluidState bs = FluidStore.Get(par);
                bs.HeatAsk = 1.5f;
                if (bs.Steam > 0f && !bs.Off) return "dry";
                return "cold";
            }
            skip = 0;
            return "";
        }

        static Process For(string medium, ItemStack st)
        {
            if (medium.Length == 0 || st == null || st.itemValue.ItemClass == null) return null;
            string n = st.itemValue.ItemClass.GetItemName();
            foreach (Process pr in Processes.For("feFan"))
                if (pr.Kind == medium && pr.Inputs.Length > 0 && pr.Inputs[0] == n) return pr;
            return null;
        }

        static ItemStack Convert(Process pr, ItemStack st)
        {
            ItemValue ov = ItemClass.GetItem(pr.Output, false);
            if (ov == null || ov.IsEmpty()) return st;
            int k = st.count / Mathf.Max(1, pr.Counts[0]);
            if (k <= 0) return st;
            return new ItemStack(ov, k * pr.OutCount);
        }

        public static void Tick(World world, Vector3i p, BlockValue bv, float dt)
        {
            TorqueNet net = Kinetic.Get(world, p);
            if (net == null || !net.Running || !net.Machines.ContainsKey(p)) { LogicStore.SetField(p, "note", "torque"); return; }
            float v = net.MachineSpeed(p);
            LogicStore.SetField(p, "note", "");
            int skip;
            string medium = Medium(world, p, bv, out skip);
            if (medium == "cold") medium = "";
            Vector3i f = Fluids.Rot(bv, Vector3.forward);
            int range = (int)Fluids.Prop(bv.Block, "FeRange", 5f);
            for (int i = 1 + skip; i <= range + skip; i++)
            {
                Vector3i c = new Vector3i(p.x + f.x * i, p.y + f.y * i, p.z + f.z * i);
                BlockValue cb = world.GetBlock(c);
                // the air stream stops at a solid block that is not a belt
                if (!cb.isair && !Belt.Is(cb.Block) && !world.IsWater(c.x, c.y, c.z)) break;
                if (Belt.Is(cb.Block))
                {
                    List<BeltItem> items = BeltStore.Items(c, false);
                    if (items != null)
                        foreach (BeltItem it in items)
                        {
                            Process pr = For(medium, it.Stack);
                            if (pr == null) continue;
                            float e;
                            beltExposure.TryGetValue(it.Id, out e);
                            e += dt * v;
                            if (e >= pr.Time) { it.Stack = Convert(pr, it.Stack); beltExposure.Remove(it.Id); BeltStore.MarkDirty(); }
                            else beltExposure[it.Id] = e;
                        }
                }
            }
            // dropped items in the stream: processed, or pushed along when there is no medium
            Vector3 a = p.ToVector3() + new Vector3(0.5f, 0.5f, 0.5f);
            Vector3 dir = f.ToVector3();
            List<Entity> list = world.Entities.list;
            for (int i = 0; i < list.Count; i++)
            {
                EntityItem e = list[i] as EntityItem;
                if (e == null || e.IsDead() || e.itemStack == null || e.itemStack.IsEmpty()) continue;
                Vector3 d = e.position - a;
                float along = Vector3.Dot(d, dir);
                if (along < 0.5f + skip || along > range + skip + 0.5f) continue;
                if ((d - dir * along).magnitude > 0.7f) continue;
                Process pr = For(medium, e.itemStack);
                if (pr != null)
                {
                    float x;
                    dropExposure.TryGetValue(e.entityId, out x);
                    x += dt * v;
                    if (x >= pr.Time)
                    {
                        ItemStack st = Convert(pr, e.itemStack);
                        Vector3 pos = e.position;
                        world.RemoveEntity(e.entityId, EnumRemoveEntityReason.Despawned);
                        GameManager.Instance.ItemDropServer(st, pos, Vector3.zero, -1, 300f, false);
                        dropExposure.Remove(e.entityId);
                    }
                    else dropExposure[e.entityId] = x;
                }
                else if (medium.Length == 0)
                    e.SetPosition(e.position + dir * Mathf.Min(0.6f, 0.4f * v), true);
            }
            if (beltExposure.Count > 4096) beltExposure.Clear();
            if (dropExposure.Count > 4096) dropExposure.Clear();
        }

        public static string Describe(World world, Vector3i p, BlockValue bv)
        {
            int skip;
            string m = Medium(world, p, bv, out skip);
            string t = m == "wash" ? Kinetic.Text("feFanWash", "Blows through water: washes the items in its stream")
                     : m == "dry" ? Kinetic.Text("feFanHeat", "Blows through a lit burner: heats the items in its stream")
                     : m == "cold" ? Kinetic.Text("feFanCold", "The burner in front is not lit")
                     : Kinetic.Text("feFanPush", "Blows air: pushes the dropped items (water or a lit burner in front: washes / heats)");
            return t + "\n" + string.Format(Kinetic.Text("feFanRange", "Range: {0} blocks"), (int)Fluids.Prop(bv.Block, "FeRange", 5f));
        }
    }

    // world machines register themselves when placed
    [HarmonyLib.HarmonyPatch(typeof(Block), "OnBlockAdded")]
    public static class Patch_Block_OnBlockAdded_WorldMachine
    {
        public static void Postfix(Block __instance, Vector3i _blockPos, BlockValue _blockValue)
        {
            if (_blockValue.ischild || !WorldMachines.Is(__instance)) return;
            if (GameManager.Instance == null || GameManager.Instance.World == null) return;
            WorldMachines.Register(_blockPos);
        }
    }
}
