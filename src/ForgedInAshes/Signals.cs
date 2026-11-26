// D12 (PLANO_CADEIA.md 4.1 d, 4.2): a simple signal, Create's "redstone" for this mod.
//
//   Emitters (a block gives the signal to the 6 blocks touching it):
//     Gauge (FeFluid=gauge)              while its reading reaches its setting
//     Signal Lever (FeSignal=lever)      on / off with E
//     Signal Receiver (FeSignal=receiver, Class Powered): while powered by a vanilla wire (switch, timer, motion
//                                        sensor, pressure plate...): the bridge from the game's wiring to the mod
//     Counter Belt (FeBeltCounter)       a short pulse every N items that pass
//   Readers: Shut-off Valve (by signal), Belt Gate (stops while signalled), Clutch (released while signalled: it
//   follows the signal when it changes, so it can still be set by hand), and any BlockPowered that is powered counts
//   as signalled itself.
//
// Lever states live in LogicStore. C# 5 only.

using System.Collections.Generic;
using UnityEngine;

namespace ForgedInAshes
{
    public static class Signals
    {
        static readonly Vector3i[] Dirs =
        {
            new Vector3i(1, 0, 0), new Vector3i(-1, 0, 0), new Vector3i(0, 1, 0),
            new Vector3i(0, -1, 0), new Vector3i(0, 0, 1), new Vector3i(0, 0, -1)
        };

        public static string Kind(Block b)
        {
            return b != null && b.Properties != null && b.Properties.Contains("FeSignal") ? b.Properties.GetString("FeSignal").Trim().ToLowerInvariant() : "";
        }

        /// <summary>D13: signal strength 0..15 the block at p gives (digital emitters: 15 when on).</summary>
        public static int Level(World world, Vector3i p)
        {
            BlockValue bv = world.GetBlock(p);
            if (Kind(bv.Block) == "analog")
            {
                int v;
                return int.TryParse(LogicStore.Field(p, "lv"), out v) ? Mathf.Clamp(v, 0, 15) : 0;
            }
            return Emits(world, p) ? 15 : 0;
        }

        /// <summary>The strongest level reaching the block at p (powered BlockPowered = 15).</summary>
        public static int LevelAt(World world, Vector3i p)
        {
            BlockValue bv = world.GetBlock(p);
            int m = bv.Block is BlockPowered && Kind(bv.Block) != "receiver" && Industrial.IsPowered(world, p) ? 15 : 0;
            foreach (Vector3i d in Dirs)
                m = Mathf.Max(m, Level(world, new Vector3i(p.x + d.x, p.y + d.y, p.z + d.z)));
            return m;
        }

        // wireless: frequency (an item name) -> on
        static readonly Dictionary<string, bool> wireless = new Dictionary<string, bool>();

        public static string Freq(Vector3i p)
        {
            return LogicStore.Field(p, "freq");
        }

        /// <summary>Does the block at p give a signal now?</summary>
        public static bool Emits(World world, Vector3i p)
        {
            BlockValue bv = world.GetBlock(p);
            if (bv.isair) return false;
            Block b = bv.Block;
            if (Fluids.Kind(b) == FluidKind.Gauge) return FluidStore.Get(Fluids.ParentOf(world, p, bv)).Sig;
            string k = Kind(b);
            if (k == "lever") return LogicStore.Get(p) == "1";
            if (k == "receiver") return Industrial.IsPowered(world, p);
            if (k == "analog") return Level(world, p) > 0;
            if (k == "wrx") { bool on; return Freq(p).Length > 0 && wireless.TryGetValue(Freq(p), out on) && on; }
            if (Belt.Is(b) && Logistics.IsCounter(b)) return Logistics.CounterPulse(p);
            return false;
        }

        /// <summary>Is the block at p signalled (an emitter touching it, or itself powered)?</summary>
        public static bool Active(World world, Vector3i p)
        {
            BlockValue bv = world.GetBlock(p);
            if (bv.Block is BlockPowered && Kind(bv.Block) != "receiver" && Industrial.IsPowered(world, p)) return true;
            foreach (Vector3i d in Dirs)
                if (Emits(world, new Vector3i(p.x + d.x, p.y + d.y, p.z + d.z))) return true;
            return false;
        }

        static readonly Dictionary<Vector3i, bool> clutchLast = new Dictionary<Vector3i, bool>();

        /// <summary>An emitter changed: clutches touching it follow (released while signalled).</summary>
        public static void Changed(World world, Vector3i emitter)
        {
            foreach (Vector3i d in Dirs)
            {
                Vector3i c = new Vector3i(emitter.x + d.x, emitter.y + d.y, emitter.z + d.z);
                BlockValue cb = world.GetBlock(c);
                if (Kinetic.Kind(cb.Block) != KineticKind.Clutch) continue;
                bool on = Active(world, c);
                bool last;
                if (clutchLast.TryGetValue(c, out last) && last == on) continue;
                clutchLast[c] = on;
                byte want = (byte)(on ? 1 : 0);
                if (cb.meta % 2 == want) continue;
                BlockValue nb = cb;
                nb.meta = want;
                world.SetBlockRPC(c, nb);
                Kinetic.Invalidate();
                Log.Out(ForgedInAshesMod.LogPrefix + "signal at " + emitter + ": clutch at " + c + (on ? " released" : " engaged"));
            }
        }

        /// <summary>Every 0.5 s (BeltTicker): receivers and counters may have changed.</summary>
        public static void Tick(World world)
        {
            LogicStore.EnsureLoaded();
            // wireless transmitters: a frequency is on when any of its transmitters is signalled
            Dictionary<string, bool> now = new Dictionary<string, bool>();
            foreach (KeyValuePair<Vector3i, string> kv in LogicStore.All)
            {
                if (!kv.Value.Contains("wtx=1") || world.GetChunkFromWorldPos(kv.Key) == null) continue;
                if (Kind(world.GetBlock(kv.Key).Block) != "wtx") continue;
                string f = Freq(kv.Key);
                if (f.Length == 0) continue;
                bool on = Active(world, kv.Key);
                bool had;
                now[f] = (now.TryGetValue(f, out had) && had) || on;
            }
            List<string> changed = new List<string>();
            foreach (KeyValuePair<string, bool> kv in now)
            {
                bool old;
                if (!wireless.TryGetValue(kv.Key, out old) || old != kv.Value) changed.Add(kv.Key);
            }
            foreach (string f in new List<string>(wireless.Keys)) if (!now.ContainsKey(f) && wireless[f]) changed.Add(f);
            wireless.Clear();
            foreach (KeyValuePair<string, bool> kv in now) wireless[kv.Key] = kv.Value;
            if (changed.Count > 0)
                foreach (KeyValuePair<Vector3i, string> kv in new List<KeyValuePair<Vector3i, string>>(LogicStore.All))
                    if (kv.Value.Contains("wrx=1") && changed.Contains(Freq(kv.Key)) && world.GetChunkFromWorldPos(kv.Key) != null)
                        Changed(world, kv.Key);
            foreach (KeyValuePair<Vector3i, string> kv in new List<KeyValuePair<Vector3i, string>>(LogicStore.All))
            {
                if (world.GetChunkFromWorldPos(kv.Key) == null) continue;
                Block b = world.GetBlock(kv.Key).Block;
                if (Kind(b) != "receiver" && !(Belt.Is(b) && Logistics.IsCounter(b))) continue;
                bool on = Emits(world, kv.Key);
                bool last;
                if (emitterLast.TryGetValue(kv.Key, out last) && last == on) continue;
                emitterLast[kv.Key] = on;
                Changed(world, kv.Key);
            }
        }

        static readonly Dictionary<Vector3i, bool> emitterLast = new Dictionary<Vector3i, bool>();

        /// <summary>The lever was pulled.</summary>
        public static string Toggle(World world, Vector3i p)
        {
            bool on = LogicStore.Get(p) != "1";
            LogicStore.Set(p, on ? "1" : "0");
            Changed(world, p);
            return on ? Kinetic.Text("feSignalOn", "SIGNAL ON") : Kinetic.Text("feSignalOff", "no signal");
        }
    }

    // ------------------------------------------------------------------ settings of logic blocks (levers, splitters,
    // counters, arms, belt gates): <save>/ForgedInAshes_logic.txt, one "x;y;z;value" per line
    public static class LogicStore
    {
        static string loadedFor;
        static bool dirty;
        public static readonly Dictionary<Vector3i, string> All = new Dictionary<Vector3i, string>();

        static string FilePath()
        {
            return ForgedInAshesMod.SaveFile("logic");
        }

        public static void EnsureLoaded()
        {
            string f = FilePath();
            if (f == null || f == loadedFor) return;
            loadedFor = f;
            All.Clear();
            dirty = false;
            if (!System.IO.File.Exists(f)) return;
            try
            {
                foreach (string line in System.IO.File.ReadAllLines(f))
                {
                    string[] t = line.Split(new char[] { ';' }, 4);
                    if (t.Length < 4) continue;
                    All[new Vector3i(int.Parse(t[0]), int.Parse(t[1]), int.Parse(t[2]))] = t[3];
                }
            }
            catch (System.Exception e)
            {
                Log.Warning(ForgedInAshesMod.LogPrefix + "logic: could not read " + f + ": " + e.Message);
            }
        }

        public static void Save()
        {
            if (!dirty || loadedFor == null) return;
            try
            {
                System.Text.StringBuilder sb = new System.Text.StringBuilder();
                foreach (KeyValuePair<Vector3i, string> kv in All)
                    sb.Append(kv.Key.x).Append(';').Append(kv.Key.y).Append(';').Append(kv.Key.z).Append(';').Append(kv.Value).Append('\n');
                System.IO.File.WriteAllText(loadedFor, sb.ToString());
                dirty = false;
            }
            catch (System.Exception e)
            {
                Log.Warning(ForgedInAshesMod.LogPrefix + "logic: could not save: " + e.Message);
            }
        }

        public static string Get(Vector3i p)
        {
            EnsureLoaded();
            string v;
            return All.TryGetValue(p, out v) ? v : "";
        }

        public static void Set(Vector3i p, string v)
        {
            EnsureLoaded();
            if (string.IsNullOrEmpty(v)) { if (All.Remove(p)) dirty = true; return; }
            string old;
            if (All.TryGetValue(p, out old) && old == v) return;
            All[p] = v;
            dirty = true;
        }

        /// <summary>"key=value|key=value" settings of one block.</summary>
        public static string Field(Vector3i p, string key)
        {
            foreach (string kv in Get(p).Split('|'))
            {
                int eq = kv.IndexOf('=');
                if (eq > 0 && kv.Substring(0, eq) == key) return kv.Substring(eq + 1);
            }
            return "";
        }

        public static void SetField(Vector3i p, string key, string value)
        {
            List<string> parts = new List<string>();
            bool done = false;
            foreach (string kv in Get(p).Split('|'))
            {
                if (kv.Length == 0) continue;
                int eq = kv.IndexOf('=');
                if (eq > 0 && kv.Substring(0, eq) == key)
                {
                    if (!string.IsNullOrEmpty(value)) parts.Add(key + "=" + value);
                    done = true;
                }
                else if (eq > 0) parts.Add(kv);
            }
            if (!done && !string.IsNullOrEmpty(value)) parts.Add(key + "=" + value);
            Set(p, string.Join("|", parts.ToArray()));
        }

        public static void MarkDirty()
        {
            dirty = true;
        }
    }

    // Signal Receivers register themselves so Signals.Tick watches them
    [HarmonyLib.HarmonyPatch(typeof(Block), "OnBlockAdded")]
    public static class Patch_Block_OnBlockAdded_Signal
    {
        public static void Postfix(Block __instance, Vector3i _blockPos, BlockValue _blockValue)
        {
            string k = Signals.Kind(__instance);
            if (_blockValue.ischild || k.Length == 0) return;
            if (k == "receiver") LogicStore.SetField(_blockPos, "rx", "1");
            else if (k == "wtx" || k == "wrx") LogicStore.SetField(_blockPos, k, "1");
        }
    }

    [HarmonyLib.HarmonyPatch(typeof(GameManager), "SaveWorld")]
    public static class Patch_GameManager_SaveWorld_Logic
    {
        public static void Prefix()
        {
            LogicStore.Save();
        }
    }

    [HarmonyLib.HarmonyPatch(typeof(GameManager), "SaveAndCleanupWorld")]
    public static class Patch_GameManager_SaveAndCleanupWorld_Logic
    {
        public static void Prefix()
        {
            LogicStore.Save();
        }
    }
}
