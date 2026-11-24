// Ferro & Engrenagem - mod entry point.
// The game (3.4.0 b10) loads every *.dll in the mod folder root (Mod.LoadAssemblies) and calls
// InitMod on the class that implements IModApi (Mod.InitModCode). Harmony comes from the game's
// own Mods/0_TFP_Harmony (HarmonyX 2.13); it is referenced, never shipped with this mod.
//
// Language level: C# 5 (built with the .NET Framework 4 csc.exe, see tools/build.ps1).

using System.Linq;
using System.Reflection;
using HarmonyLib;

namespace FerroEngrenagem
{
    public class FerroEngrenagemMod : IModApi
    {
        public const string HarmonyId = "com.ferroengrenagem.mod";
        public const string LogPrefix = "[FerroEngrenagem] ";

        /// <summary>Detailed diagnostics (every network change, spin states, crank input). On only when the mod
        /// folder has a file named debug.txt; otherwise the log keeps just the machines turning on / off.</summary>
        public static bool Verbose;

        public void InitMod(Mod _modInstance)
        {
            try { Verbose = System.IO.File.Exists(System.IO.Path.Combine(_modInstance.Path, "debug.txt")); }
            catch (System.Exception) { Verbose = false; }
            Processes.Load(_modInstance.Path);
            Settings.Load(_modInstance.Path);
            UiWatchdog.Ensure();
            Log.Out(LogPrefix + "InitMod: code loaded (" + Assembly.GetExecutingAssembly().GetName().Version + ")");
            var harmony = new Harmony(HarmonyId);
            harmony.PatchAll(Assembly.GetExecutingAssembly());
            var patched = harmony.GetPatchedMethods().ToList();
            Log.Out(LogPrefix + "Harmony: " + patched.Count + " method(s) patched" + (Verbose ? " (verbose log)" : ""));
            if (Verbose)
                foreach (var m in patched)
                {
                    Log.Out(LogPrefix + "  patched " + m.DeclaringType.Name + "." + m.Name);
                }
        }
    }
}
