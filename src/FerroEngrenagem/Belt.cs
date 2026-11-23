// D10 T1 (user, 2026-11-23): conveyor belts moved by torque, Create-like.
//
//   feConveyor (Class FeConveyor = BlockFeKinetic, FeKinetic=conveyor): one block, items travel to the block's FRONT
//   (model local +Z). In the torque network every belt is a node and a machine (FeTorqueCost UT each at 32 RPM, x
//   (rpm/32)^2): its roller axis is the model's local X, so a shaft on the LEFT or RIGHT of any belt drives it, and a
//   belt is linked to the belt in front of it / behind it (one feeds the other), so a whole line is one network.
//   Speed: FeBeltSpeed blocks/s at 32 RPM, proportional to the RPM. No torque: the items stop where they are.
//
//   Items are logical (BeltStore: per belt a list of stacks with a position 0..1 along it), moved by the server
//   (BeltTicker, 10 times a second) and saved in <save>/FerroEngrenagem_belts.txt. At the end of the line (nothing
//   that takes them) they stop and queue; they never fall off. Dropped items (the drop key) landing on a belt are
//   taken onto it. Removing a belt drops its items on the ground.
//   The host draws the items (BeltRenderer) and moves the belt surface (BeltSurface: child "FeBeltSlats" slides
//   along local Z). Like the fluids, single player / host only for now (F2-T06).
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
        public float P;      // 0 = back edge, 1 = front edge
        public int Moved;    // tick it was last moved onto another belt
    }

    public static class Belt
    {
        public const int Capacity = 4;
        public const float Gap = 0.25f;
        public const float Top = 0.62f;    // height of the belt surface above the block's floor

        public static bool Is(Block b)
        {
            return Kinetic.Kind(b) == KineticKind.Conveyor;
        }

        public static Vector3i Front(BlockValue bv)
        {
            return Fluids.Rot(bv, Vector3.forward);
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

        /// <summary>Is the belt at a joined to the belt at a + d (one feeds the other)?</summary>
        public static bool Linked(World world, Vector3i a, BlockValue abv, Vector3i d)
        {
            Vector3i b = Add(a, d);
            BlockValue bbv = world.GetBlock(b);
            if (!Is(bbv.Block)) return false;
            Vector3i back = new Vector3i(-d.x, -d.y, -d.z);
            return Front(abv) == d || Front(bbv) == back;
        }

        /// <summary>Torque faces of a belt: its roller ends (left/right) unless another belt is there, and the
        /// belts it is linked to along the line.</summary>
        public static bool HasTorqueFace(World world, Vector3i pos, BlockValue bv, Vector3i d)
        {
            Vector3i axis = Kinetic.Axis(bv);
            Vector3i n = Add(pos, d);
            if (d == axis || d == new Vector3i(-axis.x, -axis.y, -axis.z))
                return !Is(world.GetBlock(n).Block);   // side by side belts do not drive each other
            if (d.y != 0) return false;
            return Linked(world, pos, bv, d);
        }

        /// <summary>Blocks per second the belt at pos moves now (0 = stopped).</summary>
        public static float Speed(World world, Vector3i pos, BlockValue bv)
        {
            TorqueNet net = Kinetic.Get(world, pos);
            if (net == null || !net.Running || !net.Machines.ContainsKey(pos)) return 0f;
            return Fluids.Prop(bv.Block, "FeBeltSpeed", 1f) * net.MachineSpeed(pos);
        }

        public static string Describe(World world, Vector3i pos, BlockValue bv, TorqueNet net)
        {
            BeltStore.EnsureLoaded();
            List<BeltItem> items = BeltStore.Items(pos, false);
            int n = items == null ? 0 : items.Count;
            float v = Speed(world, pos, bv);
            string t = string.Format(Kinetic.Text("feBeltInfo", "Items: {0} / {1} - {2} blocks/s"), n, Capacity,
                                     v.ToString("0.0", CultureInfo.InvariantCulture));
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
                        if (data == null) continue;
                        sb.Append(kv.Key.x).Append(';').Append(kv.Key.y).Append(';').Append(kv.Key.z).Append(';')
                          .Append(it.P.ToString("0.###", CultureInfo.InvariantCulture)).Append(';')
                          .Append(it.Stack.count).Append(';').Append(data).Append('\n');
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

        void OnApplicationQuit()
        {
            BeltStore.Save();
        }

        // dropped items lying on a belt get on it
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
                if (wp.y < cell.y + Belt.Top - 0.35f) continue;   // under / beside the belt, not on it
                Vector3i f = Belt.Front(bv);
                float p = Mathf.Clamp(Vector3.Dot(wp - (cell.ToVector3() + new Vector3(0.5f, 0f, 0.5f)), f.ToVector3()) + 0.5f, 0.05f, 0.95f);
                List<BeltItem> items = BeltStore.Items(cell, false);
                if (!Belt.Room(items, p))
                {
                    // try the nearest free spot
                    bool ok = false;
                    for (float q = 0.05f; q <= 0.95f; q += 0.05f)
                        if (Belt.Room(items, q)) { p = q; ok = true; break; }
                    if (!ok) continue;
                }
                BeltStore.Add(cell, e.itemStack.Clone(), p);
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
                Vector3i f = Belt.Front(bv);
                Vector3i np = new Vector3i(pos.x + f.x, pos.y + f.y, pos.z + f.z);
                float limit = 1f;
                for (int i = 0; i < items.Count; i++)
                {
                    BeltItem it = items[i];
                    if (it.Moved == tick) { limit = it.P - Belt.Gap; continue; }
                    float target = Mathf.Min(it.P + v * dt, limit);
                    if (i == 0 && it.P + v * dt >= 1f && TryPass(world, pos, f, np, it, it.P + v * dt - 1f))
                    {
                        items.RemoveAt(i);
                        i--;
                        limit = 1f;
                        changed = true;
                        continue;
                    }
                    if (target > it.P) { it.P = target; changed = true; }
                    limit = it.P - Belt.Gap;
                }
            }
            BeltStore.Prune();
            if (changed) BeltStore.MarkDirty();
        }

        // the item at the front edge goes onto the belt in front (from its back: at the start; from its side: in the
        // middle). Anything else in front: it waits (D10 T3 adds the machine inputs, T2 the funnels).
        bool TryPass(World world, Vector3i from, Vector3i f, Vector3i to, BeltItem it, float over)
        {
            if (!Loaded(world, to)) return false;
            BlockValue nbv = world.GetBlock(to);
            if (!Belt.Is(nbv.Block)) return false;
            Vector3i nf = Belt.Front(nbv);
            if (nf == new Vector3i(-f.x, -f.y, -f.z)) return false;   // head on
            float entry = nf == f ? 0f : 0.5f;
            List<BeltItem> next = BeltStore.Items(to, true);
            float p = Mathf.Min(entry + over, entry + 0.2f);
            if (!Belt.Room(next, p)) return false;
            if (entry == 0f)
                foreach (BeltItem o in next) if (o.P < p + Belt.Gap) return false;
            it.P = p;
            it.Moved = tick;
            next.Add(it);
            return true;
        }
    }

    // ------------------------------------------------------------------ host visuals
    // The items: one model per stack (the dropped-item model, or a small box for blocks), gliding to its spot.
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
                Vector3 f = Belt.Front(bv).ToVector3();
                Vector3 c = pos.ToVector3() + new Vector3(0.5f, Belt.Top, 0.5f);
                foreach (BeltItem it in items)
                {
                    Vector3 target = c + f * (it.P - 0.5f) - Origin.position;
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
                        s.Go.transform.rotation = Quaternion.LookRotation(f);
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

    // The belt surface: child "FeBeltSlats" slides along local Z (the travel) by one slat spacing, over and over.
    public class BeltSurface : MonoBehaviour
    {
        const float Spacing = 0.125f;
        Vector3i pos;
        Transform slats;
        Vector3 basePos;
        float speed, offset, next;

        public static void Attach(BlockEntityData ebcd, Vector3i pos)
        {
            if (ebcd == null || ebcd.transform == null || GameManager.IsDedicatedServer) return;
            BeltSurface s = ebcd.transform.GetComponent<BeltSurface>();
            if (s == null) s = ebcd.transform.gameObject.AddComponent<BeltSurface>();
            s.pos = pos;
            s.slats = Find(ebcd.transform, "FeBeltSlats");
            if (s.slats != null) s.basePos = s.slats.localPosition;
            s.next = 0f;
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
            if (slats == null) return;
            if (Time.time >= next)
            {
                next = Time.time + 0.5f;
                World world = GameManager.Instance == null ? null : GameManager.Instance.World;
                speed = world == null ? 0f : Belt.Speed(world, pos, world.GetBlock(pos));
            }
            if (speed <= 0f) return;
            offset = Mathf.Repeat(offset + speed * Time.deltaTime, Spacing);
            slats.localPosition = basePos + Vector3.forward * offset;
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
            BeltSurface.Attach(_ebcd, _blockPos);
        }
    }
}
