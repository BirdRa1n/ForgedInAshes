// D10 (user, 2026-11-23: "do everything"): fixed recipe. A machine of the mod (workstation named fe*) repeats one
// recipe by itself with the ingredients that arrive by belt.
//
//   - Radial command "Fixed recipe" (hold E on the machine): turns it on with the recipe in its queue (craft it once by
//     hand first) or turns it off. The readout shows the recipe and the ingredients waiting.
//   - A belt pointing into the machine (any side) delivers: fuel to its fuel slots and smeltable material to its input
//     (the Foundry), as vanilla; INGREDIENTS of the fixed recipe go to an internal store (up to 5 crafts' worth).
//   - Every 0.5 s, when the queue is empty and the store holds all the ingredients, it queues one craft. The output
//     lands in its output slots; a Funnel can take it out onto a belt.
//   State in <save>/ForgedInAshes_autocraft.txt. Turning it off (or removing the machine) drops the stored
//   ingredients on the ground. Single player / host.
//
// C# 5 only.

using System.Collections.Generic;
using System.IO;
using System.Text;
using HarmonyLib;
using UnityEngine;

namespace ForgedInAshes
{
    public static class AutoCraft
    {
        class Entry
        {
            public string Recipe = "";
            public string Area = "";
            public bool On;
            public readonly Dictionary<string, int> Store = new Dictionary<string, int>();   // item name -> count
        }

        static string loadedFor;
        static bool dirty;
        static readonly Dictionary<Vector3i, Entry> entries = new Dictionary<Vector3i, Entry>();
        const int Batches = 5;

        public static bool IsMachine(Block b)
        {
            return b is BlockWorkstation && b.GetBlockName().StartsWith("fe", System.StringComparison.Ordinal);
        }

        static string FilePath()
        {
            return ForgedInAshesMod.SaveFile("autocraft");
        }

        public static void EnsureLoaded()
        {
            string f = FilePath();
            if (f == null || f == loadedFor) return;
            loadedFor = f;
            entries.Clear();
            dirty = false;
            if (!File.Exists(f)) return;
            try
            {
                foreach (string line in File.ReadAllLines(f))
                {
                    string[] t = line.Split(';');
                    if (t.Length < 7) continue;
                    Entry e = new Entry();
                    e.On = t[3] == "1";
                    e.Recipe = t[4];
                    e.Area = t[5];
                    foreach (string kv in t[6].Split(','))
                    {
                        int eq = kv.IndexOf('=');
                        if (eq <= 0) continue;
                        e.Store[kv.Substring(0, eq)] = int.Parse(kv.Substring(eq + 1));
                    }
                    entries[new Vector3i(int.Parse(t[0]), int.Parse(t[1]), int.Parse(t[2]))] = e;
                }
            }
            catch (System.Exception ex)
            {
                Log.Warning(ForgedInAshesMod.LogPrefix + "autocraft: could not read " + f + ": " + ex.Message);
            }
        }

        public static void Save()
        {
            if (!dirty || loadedFor == null) return;
            try
            {
                StringBuilder sb = new StringBuilder();
                foreach (KeyValuePair<Vector3i, Entry> kv in entries)
                {
                    sb.Append(kv.Key.x).Append(';').Append(kv.Key.y).Append(';').Append(kv.Key.z).Append(';')
                      .Append(kv.Value.On ? "1" : "0").Append(';').Append(kv.Value.Recipe).Append(';')
                      .Append(kv.Value.Area).Append(';');
                    bool first = true;
                    foreach (KeyValuePair<string, int> it in kv.Value.Store)
                    {
                        if (it.Value <= 0) continue;
                        if (!first) sb.Append(',');
                        sb.Append(it.Key).Append('=').Append(it.Value);
                        first = false;
                    }
                    sb.Append('\n');
                }
                File.WriteAllText(loadedFor, sb.ToString());
                dirty = false;
            }
            catch (System.Exception ex)
            {
                Log.Warning(ForgedInAshesMod.LogPrefix + "autocraft: could not save: " + ex.Message);
            }
        }

        static Recipe Find(Entry e)
        {
            if (e == null || e.Recipe.Length == 0 || CraftingManager.GetRecipes(e.Recipe) == null) return null;
            foreach (Recipe r in CraftingManager.GetRecipes(e.Recipe))
                if (r.craftingArea == e.Area) return r;
            return null;
        }

        static int Need(Recipe r, string item)
        {
            int n = 0;
            foreach (ItemStack ing in r.ingredients)
                if (ing.itemValue.ItemClass != null && ing.itemValue.ItemClass.GetItemName() == item) n += ing.count;
            return n;
        }

        /// <summary>A belt delivers an item that is neither fuel nor smeltable: keep it if the fixed recipe uses it.
        /// Returns how many were taken.</summary>
        public static int Store(World world, Vector3i p, ItemStack st)
        {
            EnsureLoaded();
            Entry e;
            if (!entries.TryGetValue(p, out e) || !e.On) return 0;
            Recipe r = Find(e);
            if (r == null || st.itemValue.ItemClass == null) return 0;
            string name = st.itemValue.ItemClass.GetItemName();
            int need = Need(r, name);
            if (need <= 0) return 0;
            int have;
            e.Store.TryGetValue(name, out have);
            int take = Mathf.Min(st.count, need * Batches - have);
            if (take <= 0) return 0;
            e.Store[name] = have + take;
            dirty = true;
            return take;
        }

        static bool QueueEmpty(RecipeQueueItem[] q)
        {
            if (q == null) return false;
            foreach (RecipeQueueItem it in q)
                if (it != null && it.Recipe != null && it.Multiplier > 0) return false;
            return true;
        }

        public static void TickAll(World world)
        {
            EnsureLoaded();
            List<Vector3i> gone = new List<Vector3i>();
            foreach (KeyValuePair<Vector3i, Entry> kv in entries)
            {
                Vector3i p = kv.Key;
                Entry e = kv.Value;
                if (world.GetChunkFromWorldPos(p) == null) continue;
                if (!IsMachine(world.GetBlock(p).Block)) { gone.Add(p); continue; }
                if (!e.On) continue;
                TileEntityWorkstation ws = world.GetTileEntity(p) as TileEntityWorkstation;
                Recipe r = Find(e);
                if (ws == null || r == null || ws.IsUserAccessing()) continue;
                RecipeQueueItem[] q = ws.Queue;
                if (!QueueEmpty(q)) continue;
                PullLinked(world, p, r, e);
                bool all = true;
                foreach (ItemStack ing in r.ingredients)
                {
                    if (ing.itemValue.ItemClass == null) continue;
                    int have;
                    e.Store.TryGetValue(ing.itemValue.ItemClass.GetItemName(), out have);
                    if (have < ing.count) { all = false; break; }
                }
                if (!all) continue;
                foreach (ItemStack ing in r.ingredients)
                {
                    if (ing.itemValue.ItemClass == null) continue;
                    string n = ing.itemValue.ItemClass.GetItemName();
                    e.Store[n] = e.Store[n] - ing.count;
                }
                RecipeQueueItem item = new RecipeQueueItem();
                item.Recipe = r;
                item.Multiplier = 1;
                float time = r.craftingTime > 0f ? r.craftingTime : 5f;
                item.CraftingTimeLeft = time;
                item.OneItemCraftTime = time;
                item.IsCrafting = true;
                item.Quality = 1;
                item.StartingEntityId = -1;
                q[q.Length - 1] = item;
                ws.Queue = q;
                ws.SetModified();
                dirty = true;
            }
            foreach (Vector3i p in gone) { Drop(world, p); entries.Remove(p); dirty = true; }
        }

        // ------------------------------------------------------------ D12 / N09: crates linked to the machine
        static readonly Vector3i[] Dirs6 =
        {
            new Vector3i(1, 0, 0), new Vector3i(-1, 0, 0), new Vector3i(0, 1, 0),
            new Vector3i(0, -1, 0), new Vector3i(0, 0, 1), new Vector3i(0, 0, -1)
        };

        static TEFeatureStorage StorageAt(World world, Vector3i c, out TileEntityComposite tc)
        {
            tc = null;
            BlockValue bv = world.GetBlock(c);
            if (bv.isair || bv.ischild) return null;
            tc = world.GetTileEntity(c) as TileEntityComposite;
            return tc == null ? null : tc.GetFeature<TEFeatureStorage>();
        }

        const int MaxCrates = 16;

        /// <summary>Crates touching the machine, and crates touching those (up to MaxCrates).</summary>
        public static List<Vector3i> LinkedCrates(World world, Vector3i machine)
        {
            List<Vector3i> found = new List<Vector3i>();
            HashSet<Vector3i> seen = new HashSet<Vector3i>();
            Queue<Vector3i> q = new Queue<Vector3i>();
            // the machine's own cells (multiblocks: every cell whose parent is the machine)
            List<Vector3i> cells = new List<Vector3i>();
            for (int dx = -2; dx <= 2; dx++)
                for (int dy = 0; dy <= 2; dy++)
                    for (int dz = -2; dz <= 2; dz++)
                    {
                        Vector3i c = new Vector3i(machine.x + dx, machine.y + dy, machine.z + dz);
                        BlockValue cb = world.GetBlock(c);
                        if (c == machine || (cb.ischild && Fluids.ParentOf(world, c, cb) == machine)) cells.Add(c);
                    }
            foreach (Vector3i c in cells) seen.Add(c);
            foreach (Vector3i c in cells)
                foreach (Vector3i d in Dirs6)
                {
                    Vector3i n = new Vector3i(c.x + d.x, c.y + d.y, c.z + d.z);
                    if (seen.Contains(n)) continue;
                    seen.Add(n);
                    TileEntityComposite tc;
                    if (StorageAt(world, n, out tc) != null) q.Enqueue(n);
                }
            while (q.Count > 0 && found.Count < MaxCrates)
            {
                Vector3i c = q.Dequeue();
                found.Add(c);
                foreach (Vector3i d in Dirs6)
                {
                    Vector3i n = new Vector3i(c.x + d.x, c.y + d.y, c.z + d.z);
                    if (seen.Contains(n)) continue;
                    seen.Add(n);
                    TileEntityComposite tc;
                    if (StorageAt(world, n, out tc) != null) q.Enqueue(n);
                }
            }
            return found;
        }

        /// <summary>Fill the store from the linked crates, only when the whole recipe is there (never half of it).</summary>
        static void PullLinked(World world, Vector3i p, Recipe r, Entry e)
        {
            Block b = world.GetBlock(p).Block;
            if (b.Properties != null && b.Properties.Contains("FeLinkCrates") && !b.Properties.GetBool("FeLinkCrates")) return;
            Dictionary<string, int> missing = new Dictionary<string, int>();
            foreach (ItemStack ing in r.ingredients)
            {
                if (ing.itemValue.ItemClass == null || ing.count <= 0) continue;
                string n = ing.itemValue.ItemClass.GetItemName();
                int have;
                e.Store.TryGetValue(n, out have);
                int miss = ing.count - have;
                if (miss > 0) missing[n] = (missing.ContainsKey(n) ? missing[n] : 0) + miss;
            }
            if (missing.Count == 0) return;
            List<Vector3i> crates = LinkedCrates(world, p);
            if (crates.Count == 0) return;
            Dictionary<string, int> avail = new Dictionary<string, int>();
            foreach (Vector3i c in crates)
            {
                TileEntityComposite tc;
                TEFeatureStorage st = StorageAt(world, c, out tc);
                if (st == null || st.ItemGrid == null) continue;
                if (tc.IsUserAccessing()) return;   // a player is using one: wait
                ItemStackGrid g = st.ItemGrid;
                for (int i = 0; i < g.Length; i++)
                {
                    ItemStack it = g[i];
                    if (it == null || it.IsEmpty() || it.itemValue.ItemClass == null) continue;
                    string n = it.itemValue.ItemClass.GetItemName();
                    if (!missing.ContainsKey(n)) continue;
                    avail[n] = (avail.ContainsKey(n) ? avail[n] : 0) + it.count;
                }
            }
            foreach (KeyValuePair<string, int> kv in missing)
            {
                int a;
                if (!avail.TryGetValue(kv.Key, out a) || a < kv.Value) return;
            }
            foreach (KeyValuePair<string, int> kv in missing)
            {
                int left = kv.Value;
                foreach (Vector3i c in crates)
                {
                    if (left <= 0) break;
                    TileEntityComposite tc;
                    TEFeatureStorage st = StorageAt(world, c, out tc);
                    if (st == null || st.ItemGrid == null) continue;
                    ItemStackGrid g = st.ItemGrid;
                    for (int i = 0; i < g.Length && left > 0; i++)
                    {
                        ItemStack it = g[i];
                        if (it == null || it.IsEmpty() || it.itemValue.ItemClass == null || it.itemValue.ItemClass.GetItemName() != kv.Key) continue;
                        int n = Mathf.Min(left, it.count);
                        ItemStack rest = it.Clone();
                        rest.count -= n;
                        st.UpdateSlot(i, rest.count > 0 ? rest : ItemStack.Empty.Clone());
                        tc.SetModified();
                        left -= n;
                    }
                }
                int have;
                e.Store.TryGetValue(kv.Key, out have);
                e.Store[kv.Key] = have + kv.Value - left;
            }
            dirty = true;
            BeltMachines.Note(world, p, "took the ingredients of " + r.GetName() + " from " + crates.Count + " linked crate(s)");
        }

        /// <summary>D12 Recipe Picker: the recipes of this machine.</summary>
        public static List<Recipe> Recipes(Block b)
        {
            return RecipesOf(b.GetBlockName());
        }

        public static string Current(Vector3i p)
        {
            EnsureLoaded();
            Entry e;
            return entries.TryGetValue(p, out e) && e.On ? e.Recipe : "";
        }

        /// <summary>Choose a recipe by name (null = off).</summary>
        public static string Choose(World world, Vector3i p, Block b, string recipe)
        {
            EnsureLoaded();
            Entry e;
            if (!entries.TryGetValue(p, out e)) { e = new Entry(); entries[p] = e; }
            if (recipe == null)
            {
                Drop(world, p);
                e.On = false;
                dirty = true;
                return Kinetic.Text("feAutoOff", "Fixed recipe off");
            }
            Recipe r = null;
            foreach (Recipe x in RecipesOf(b.GetBlockName())) if (x.GetName() == recipe) { r = x; break; }
            if (r == null) return Kinetic.Text("feAutoNone", "This machine has no recipes");
            if (r.GetName() != e.Recipe) Drop(world, p);
            e.Recipe = r.GetName();
            e.Area = r.craftingArea ?? "";
            e.On = true;
            dirty = true;
            return string.Format(Kinetic.Text("feAutoOn", "Fixed recipe: {0}"), Localization.Get(e.Recipe, false));
        }

        static void Drop(World world, Vector3i p)
        {
            Entry e;
            if (!entries.TryGetValue(p, out e) || GameManager.Instance == null) return;
            foreach (KeyValuePair<string, int> it in e.Store)
            {
                if (it.Value <= 0) continue;
                ItemValue iv = ItemClass.GetItem(it.Key, false);
                if (iv == null || iv.IsEmpty()) continue;
                GameManager.Instance.ItemDropServer(new ItemStack(iv, it.Value), p.ToVector3() + new Vector3(0.5f, 1.2f, 0.5f),
                                                   Vector3.zero, -1, 300f, false);
            }
            e.Store.Clear();
        }

        /// <summary>Radial command: on with the recipe in the queue, or off (stored ingredients dropped).</summary>
        public static string Toggle(World world, Vector3i p)
        {
            EnsureLoaded();
            Entry e;
            if (entries.TryGetValue(p, out e) && e.On)
            {
                Drop(world, p);
                e.On = false;
                dirty = true;
                return Kinetic.Text("feAutoOff", "Fixed recipe off");
            }
            TileEntityWorkstation ws = world.GetTileEntity(p) as TileEntityWorkstation;
            Recipe r = null;
            if (ws != null && ws.Queue != null)
                for (int i = ws.Queue.Length - 1; i >= 0 && r == null; i--)
                    if (ws.Queue[i] != null && ws.Queue[i].Recipe != null && ws.Queue[i].Multiplier > 0) r = ws.Queue[i].Recipe;
            if (r == null && e != null) r = Find(e);
            if (r == null) return Kinetic.Text("feAutoNoRecipe", "Craft the recipe once in this machine first, then turn the fixed recipe on");
            if (e == null) { e = new Entry(); entries[p] = e; }
            e.Recipe = r.GetName();
            e.Area = r.craftingArea ?? "";
            e.On = true;
            dirty = true;
            return string.Format(Kinetic.Text("feAutoOn", "Fixed recipe: {0}"), Localization.Get(e.Recipe, false));
        }

        /// <summary>F8.0 (N10, "Choose production"): the recipes of this machine's craft area, in a stable order.</summary>
        static List<Recipe> RecipesOf(string area)
        {
            List<Recipe> l = new List<Recipe>();
            List<Recipe> all = CraftingManager.GetAllRecipes();
            if (all == null) return l;
            foreach (Recipe r in all)
                if (r != null && r.craftingArea == area && !l.Contains(r)) l.Add(r);
            l.Sort(delegate (Recipe a, Recipe b) { return string.CompareOrdinal(a.GetName(), b.GetName()); });
            return l;
        }

        /// <summary>Radial commands "next / previous production": pick the recipe without crafting it by hand first.
        /// Turns the fixed recipe on; a different recipe drops the ingredients stored for the old one.</summary>
        public static string Cycle(World world, Vector3i p, string area, int step, string held)
        {
            EnsureLoaded();
            List<Recipe> l = RecipesOf(area);
            if (l.Count == 0) return Kinetic.Text("feAutoNone", "This machine has no recipes");
            Entry e;
            if (!entries.TryGetValue(p, out e)) { e = new Entry(); entries[p] = e; }
            int at = -1;
            for (int i = 0; i < l.Count; i++)
                if (l[i].GetName() == e.Recipe && l[i].craftingArea == e.Area) { at = i; break; }
            int next = at < 0 ? (step > 0 ? 0 : l.Count - 1) : ((at + step) % l.Count + l.Count) % l.Count;
            // holding something this machine makes: jump straight to it (49 recipes are a long way to cycle)
            if (held != null && (at < 0 || l[at].GetName() != held))
                for (int i = 0; i < l.Count; i++)
                    if (l[i].GetName() == held) { next = i; break; }
            Recipe r = l[next];
            if (r.GetName() != e.Recipe) Drop(world, p);
            e.Recipe = r.GetName();
            e.Area = r.craftingArea ?? "";
            e.On = true;
            dirty = true;
            return string.Format(Kinetic.Text("feAutoPick", "Production {0}/{1}: {2}"), next + 1, l.Count,
                                 Localization.Get(e.Recipe, false));
        }

        public static string Describe(Vector3i p)
        {
            EnsureLoaded();
            Entry e;
            if (!entries.TryGetValue(p, out e) || !e.On) return "";
            Recipe r = Find(e);
            if (r == null) return "";
            StringBuilder sb = new StringBuilder();
            sb.Append(string.Format(Kinetic.Text("feAutoOn", "Fixed recipe: {0}"), Localization.Get(e.Recipe, false)));
            foreach (ItemStack ing in r.ingredients)
            {
                if (ing.itemValue.ItemClass == null) continue;
                string n = ing.itemValue.ItemClass.GetItemName();
                int have;
                e.Store.TryGetValue(n, out have);
                sb.Append("\n  ").Append(ing.itemValue.ItemClass.GetLocalizedItemName()).Append(": ").Append(have)
                  .Append(" / ").Append(ing.count);
            }
            return sb.ToString();
        }
    }

    // radial command on the mod's machines
    [HarmonyPatch(typeof(BlockWorkstation), "GetBlockActivationCommands")]
    public static class Patch_Workstation_Commands_AutoCraft
    {
        public static void Postfix(BlockWorkstation __instance, ref BlockActivationCommand[] __result)
        {
            RecipeBook.AddCommand(__instance, ref __result);
            if (!AutoCraft.IsMachine(__instance) || __result == null) return;
            foreach (BlockActivationCommand c in __result) if (c.text == "fe_autocraft") return;
            BlockActivationCommand[] r = new BlockActivationCommand[__result.Length + 1];
            __result.CopyTo(r, 0);
            r[__result.Length] = new BlockActivationCommand("fe_autocraft", "electric_switch", true, false, null);
            // F8.0 (N10): choose the production without crafting it by hand first
            System.Array.Resize(ref r, r.Length + 3);
            r[r.Length - 3] = new BlockActivationCommand(FeUi.CraftPickCommand, "tool", true, false, null);
            r[r.Length - 2] = new BlockActivationCommand("fe_recipe_next", "loot_sort", true, false, null);
            r[r.Length - 1] = new BlockActivationCommand("fe_recipe_prev", "loot_sort", true, false, null);
            __result = r;
        }
    }

    [HarmonyPatch(typeof(BlockWorkstation), "OnBlockActivated", new System.Type[] { typeof(string), typeof(WorldBase), typeof(Vector3i), typeof(BlockValue), typeof(EntityPlayerLocal) })]
    public static class Patch_Workstation_Activated_AutoCraft
    {
        public static bool Prefix(BlockWorkstation __instance, string _commandName, WorldBase _world, Vector3i _blockPos, EntityPlayerLocal _player, ref bool __result)
        {
            if (_commandName == RecipeBook.Command)
            {
                RecipeBook.Open(__instance, _player);
                __result = true;
                return false;
            }
            World w = _world as World;
            if (w != null && FeUi.HandleCommand(_commandName, w, _blockPos, w.GetBlock(_blockPos), _player)) { __result = true; return false; }
            if (_commandName != "fe_autocraft" && _commandName != "fe_recipe_next" && _commandName != "fe_recipe_prev")
                return true;
            if (w != null)
            {
                string msg;
                if (_commandName == "fe_autocraft") msg = AutoCraft.Toggle(w, _blockPos);
                else
                {
                    BlockValue bv = w.GetBlock(_blockPos);
                    ItemStack hs = _player.inventory.holdingItemStack;
                    string held = hs == null || hs.IsEmpty() || hs.itemValue.ItemClass == null ? null : hs.itemValue.ItemClass.GetItemName();
                    msg = AutoCraft.Cycle(w, _blockPos, bv.Block.GetBlockName(), _commandName == "fe_recipe_next" ? 1 : -1, held);
                }
                GameManager.ShowTooltip(_player, msg, false, false, 0f);
                Log.Out(ForgedInAshesMod.LogPrefix + "autocraft at " + _blockPos + ": " + msg);
            }
            __result = true;
            return false;
        }
    }

    [HarmonyPatch(typeof(BlockWorkstation), "GetActivationText")]
    public static class Patch_Workstation_Text_AutoCraft
    {
        public static void Postfix(BlockWorkstation __instance, Vector3i _blockPos, ref string __result)
        {
            if (!AutoCraft.IsMachine(__instance)) return;
            World w = GameManager.Instance == null ? null : GameManager.Instance.World;
            if (w != null) BeltMachines.RescueHidden(w, _blockPos, w.GetTileEntity(_blockPos) as TileEntityWorkstation);
            string d = AutoCraft.Describe(_blockPos);
            if (d.Length == 0) return;
            __result = (string.IsNullOrEmpty(__result) ? "" : __result + "\n") + KineticLookController.Escape(d);
        }
    }

    [HarmonyPatch(typeof(GameManager), "SaveAndCleanupWorld")]
    public static class Patch_GameManager_SaveAndCleanupWorld_AutoCraft
    {
        public static void Prefix()
        {
            AutoCraft.Save();
        }
    }

    [HarmonyPatch(typeof(GameManager), "SaveWorld")]
    public static class Patch_GameManager_SaveWorld_AutoCraft
    {
        public static void Prefix()
        {
            AutoCraft.Save();
        }
    }
}
