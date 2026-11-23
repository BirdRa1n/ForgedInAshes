// D10 (user, 2026-11-23: "do everything"): fixed recipe. A machine of the mod (workstation named fe*) repeats one
// recipe by itself with the ingredients that arrive by belt.
//
//   - Radial command "Fixed recipe" (hold E on the machine): turns it on with the recipe in its queue (craft it once by
//     hand first) or turns it off. The readout shows the recipe and the ingredients waiting.
//   - A belt pointing into the machine (any side) delivers: fuel to its fuel slots and smeltable material to its input
//     (the Foundry), as vanilla; INGREDIENTS of the fixed recipe go to an internal store (up to 5 crafts' worth).
//   - Every 0.5 s, when the queue is empty and the store holds all the ingredients, it queues one craft. The output
//     lands in its output slots; a Funnel can take it out onto a belt.
//   State in <save>/FerroEngrenagem_autocraft.txt. Turning it off (or removing the machine) drops the stored
//   ingredients on the ground. Single player / host.
//
// C# 5 only.

using System.Collections.Generic;
using System.IO;
using System.Text;
using HarmonyLib;
using UnityEngine;

namespace FerroEngrenagem
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
            string dir = GameIO.GetSaveGameDir();
            return string.IsNullOrEmpty(dir) ? null : Path.Combine(dir, "FerroEngrenagem_autocraft.txt");
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
                Log.Warning(FerroEngrenagemMod.LogPrefix + "autocraft: could not read " + f + ": " + ex.Message);
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
                Log.Warning(FerroEngrenagemMod.LogPrefix + "autocraft: could not save: " + ex.Message);
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
            if (!AutoCraft.IsMachine(__instance) || __result == null) return;
            foreach (BlockActivationCommand c in __result) if (c.text == "fe_autocraft") return;
            BlockActivationCommand[] r = new BlockActivationCommand[__result.Length + 1];
            __result.CopyTo(r, 0);
            r[__result.Length] = new BlockActivationCommand("fe_autocraft", "electric_switch", true, false, null);
            __result = r;
        }
    }

    [HarmonyPatch(typeof(BlockWorkstation), "OnBlockActivated", new System.Type[] { typeof(string), typeof(WorldBase), typeof(Vector3i), typeof(BlockValue), typeof(EntityPlayerLocal) })]
    public static class Patch_Workstation_Activated_AutoCraft
    {
        public static bool Prefix(string _commandName, WorldBase _world, Vector3i _blockPos, EntityPlayerLocal _player, ref bool __result)
        {
            if (_commandName != "fe_autocraft") return true;
            World w = _world as World;
            if (w != null)
            {
                string msg = AutoCraft.Toggle(w, _blockPos);
                GameManager.ShowTooltip(_player, msg, false, false, 0f);
                Log.Out(FerroEngrenagemMod.LogPrefix + "autocraft at " + _blockPos + ": " + msg);
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
