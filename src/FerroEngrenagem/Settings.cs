// D12-4 (PLANO_CADEIA.md 11): Data/fe_settings.xml, read at start-up.
//
//   <setting name="VanillaShortcuts" value="remove"/>   default: the shortcuts the chains replace are gone
//   <setting name="VanillaShortcuts" value="expensive"/>: they come back at 3x their cost (Data/fe_fallback.xml,
//                                                          written by tools/gen_chain.py), added when the recipes load
//
// C# 5 only.

using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Xml;
using HarmonyLib;

namespace FerroEngrenagem
{
    public static class Settings
    {
        static readonly Dictionary<string, string> values = new Dictionary<string, string>();
        public static string ModPath = "";

        public static string Get(string name, string def)
        {
            string v;
            return values.TryGetValue(name, out v) ? v : def;
        }

        public static void Load(string modPath)
        {
            ModPath = modPath;
            values.Clear();
            string f = Path.Combine(Path.Combine(modPath, "Data"), "fe_settings.xml");
            if (!File.Exists(f)) return;
            try
            {
                XmlDocument doc = new XmlDocument();
                doc.Load(f);
                foreach (XmlNode n in doc.DocumentElement.GetElementsByTagName("setting"))
                {
                    XmlElement e = n as XmlElement;
                    if (e != null && e.GetAttribute("name").Length > 0) values[e.GetAttribute("name")] = e.GetAttribute("value");
                }
                Log.Out(FerroEngrenagemMod.LogPrefix + "settings: VanillaShortcuts=" + Get("VanillaShortcuts", "remove"));
            }
            catch (System.Exception ex)
            {
                Log.Warning(FerroEngrenagemMod.LogPrefix + "settings: " + ex.Message);
            }
        }

        /// <summary>"expensive": add the fallback recipes (once per recipe load).</summary>
        public static void AddFallbacks()
        {
            if (Get("VanillaShortcuts", "remove") != "expensive") return;
            string f = Path.Combine(Path.Combine(ModPath, "Data"), "fe_fallback.xml");
            if (!File.Exists(f)) return;
            int n = 0;
            try
            {
                XmlDocument doc = new XmlDocument();
                doc.Load(f);
                foreach (XmlNode node in doc.DocumentElement.GetElementsByTagName("recipe"))
                {
                    XmlElement e = node as XmlElement;
                    if (e == null) continue;
                    ItemValue outV = ItemClass.GetItem(e.GetAttribute("name"), false);
                    if (outV == null || outV.IsEmpty()) continue;
                    Recipe r = new Recipe();
                    r.itemValueType = outV.type;
                    int c;
                    r.count = int.TryParse(e.GetAttribute("count"), out c) ? c : 1;
                    r.craftingArea = e.GetAttribute("craft_area");
                    float t;
                    r.craftingTime = float.TryParse(e.GetAttribute("craft_time"), NumberStyles.Float, CultureInfo.InvariantCulture, out t) ? t : 10f;
                    r.ingredients = new List<ItemStack>();
                    bool ok = true;
                    foreach (XmlNode ing in e.GetElementsByTagName("ingredient"))
                    {
                        XmlElement ie = ing as XmlElement;
                        ItemValue iv = ItemClass.GetItem(ie.GetAttribute("name"), false);
                        int k;
                        if (iv == null || iv.IsEmpty() || !int.TryParse(ie.GetAttribute("count"), out k)) { ok = false; break; }
                        r.AddIngredient(iv, k);
                    }
                    if (!ok) continue;
                    r.Init();
                    CraftingManager.AddRecipe(r);
                    n++;
                }
            }
            catch (System.Exception ex)
            {
                Log.Warning(FerroEngrenagemMod.LogPrefix + "fallback recipes: " + ex.Message);
            }
            Log.Out(FerroEngrenagemMod.LogPrefix + "VanillaShortcuts=expensive: added " + n + " fallback recipe(s)");
        }
    }

    [HarmonyPatch(typeof(CraftingManager), "PostInit")]
    public static class Patch_CraftingManager_PostInit_Fallback
    {
        public static void Postfix()
        {
            Settings.AddFallbacks();
        }
    }
}
