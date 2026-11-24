// Recipe book (user request after the F8.2 test): hold E on any mod machine -> "Recipes" opens a window with the full
// list of what that machine makes: its chain processes (Data/fe_processes.xml) and its workstation recipes
// (recipes.xml craft_area). Long lists are paged.
//
// The window is Config/XUi/windows.xml "feRecipes" (window_group in xui.xml), controller XUiC_FeRecipes below.
// If the window does not open (XUi failed to load), the first lines go to a tooltip instead.
//
// 2026-11-24 (bug: after opening the book from the Washer, the toolbelt would not change slot any more, not even by
// number): the command runs inside the radial menu's callback, and opening a modal window there force-closed the
// radial in the middle of its own close; the held item's holster / draw transition (Hand.isSwitching) could stay
// stuck, and PlayerMoveController refuses slot changes while the hand is switching. Now the window opens a few
// frames later, once no modal window is open (like the game does with crates and workbenches), and when it closes
// a watchdog finishes a hand transition still stuck after 1 s (Hand.CompleteTransition).
//
// C# 5 only.

using System.Collections;
using System.Collections.Generic;
using HarmonyLib;
using System.Text;
using UnityEngine;

namespace FerroEngrenagem
{
    public static class RecipeBook
    {
        public const string Command = "fe_recipes";
        public const string Window = "feRecipes";

        static string ItemName(string item)
        {
            ItemValue iv = ItemClass.GetItem(item, false);
            return iv == null || iv.IsEmpty() || iv.ItemClass == null ? item : iv.ItemClass.GetLocalizedItemName();
        }

        static string Secs(float t)
        {
            return t >= 60f ? Mathf.RoundToInt(t / 60f * 10f) / 10f + " min" : Mathf.RoundToInt(t) + " s";
        }

        static List<Process> ProcessesOf(Block b)
        {
            List<Process> l = Processes.For(b.GetBlockName());
            if (l.Count == 0 && Fluids.Kind(b) == FluidKind.Caster) l = Processes.For(MetalWorks.CasterBlock);
            return l;
        }

        static string Line(Process p)
        {
            List<string> ins = new List<string>();
            for (int i = 0; i < p.Inputs.Length; i++) ins.Add(p.Counts[i] + "x " + ItemName(p.Inputs[i]));
            if (p.FluidIn != null) ins.Add(Mathf.RoundToInt(p.Liters) + " L " + Fluids.FluidName(p.FluidIn));
            if (p.Mold != null)
                ins.Add(string.Format(Kinetic.Text("feRecipesMold", "mold {0}"), ItemName(p.Mold)));
            List<string> outs = new List<string>();
            if (p.Output != null) outs.Add(p.OutCount + "x " + ItemName(p.Output));
            if (p.FluidOut != null) outs.Add(Mathf.RoundToInt(p.OutLiters) + " L " + Fluids.FluidName(p.FluidOut));
            string t = string.Join(" + ", ins.ToArray()) + "  ->  " + string.Join(" + ", outs.ToArray());
            List<string> extra = new List<string>();
            if (p.Time > 0f) extra.Add(Secs(p.Time));
            if (p.Torque > 0f) extra.Add(string.Format(Kinetic.Text("feRecipesTorque", "torque {0}"), Mathf.RoundToInt(p.Torque)));
            return extra.Count > 0 ? t + "   (" + string.Join(", ", extra.ToArray()) + ")" : t;
        }

        static string[] AreasOf(Block b)
        {
            string a = null;
            if (b.Properties != null && b.Properties.Contains("Workstation", "CraftingAreaRecipes"))
                a = b.Properties.GetString("Workstation", "CraftingAreaRecipes");
            if (string.IsNullOrEmpty(a)) a = b.GetBlockName();
            return a.Split(',');
        }

        static List<string> WorkstationLines(Block b)
        {
            List<string> r = new List<string>();
            if (!(b is BlockWorkstation) || CraftingManager.GetAllRecipes() == null) return r;
            HashSet<string> areas = new HashSet<string>();
            foreach (string a in AreasOf(b)) if (a.Trim().StartsWith("fe")) areas.Add(a.Trim());
            if (areas.Count == 0) return r;
            List<KeyValuePair<string, string>> l = new List<KeyValuePair<string, string>>();
            foreach (Recipe rc in CraftingManager.GetAllRecipes())
            {
                if (rc == null || rc.craftingArea == null || !areas.Contains(rc.craftingArea)) continue;
                ItemClass oc = rc.GetOutputItemClass();
                if (oc == null) continue;
                List<string> ins = new List<string>();
                if (rc.ingredients != null)
                    foreach (ItemStack st in rc.ingredients)
                        if (st != null && st.itemValue != null && st.itemValue.ItemClass != null)
                            ins.Add(st.count + "x " + st.itemValue.ItemClass.GetLocalizedItemName());
                string name = oc.GetLocalizedItemName();
                l.Add(new KeyValuePair<string, string>(name, rc.count + "x " + name + "  <-  " + string.Join(" + ", ins.ToArray())
                                                       + (rc.craftingTime > 0f ? "   (" + Secs(rc.craftingTime) + ")" : "")));
            }
            l.Sort((x, y) => string.Compare(x.Key, y.Key, System.StringComparison.CurrentCultureIgnoreCase));
            foreach (KeyValuePair<string, string> kv in l) r.Add(kv.Value);
            return r;
        }

        /// <summary>Every line of the book of this machine (empty = no recipes, no command).</summary>
        public static List<string> Lines(Block b)
        {
            List<string> r = new List<string>();
            if (b == null || !b.GetBlockName().StartsWith("fe")) return r;
            List<Process> ps = ProcessesOf(b);
            if (ps.Count > 0)
            {
                r.Add("[e0a030]" + Kinetic.Text("feRecipesChain", "Chain processes (automatic)") + "[-]");
                foreach (Process p in ps) r.Add("  " + Line(p));
            }
            List<string> ws = WorkstationLines(b);
            if (ws.Count > 0)
            {
                if (r.Count > 0) r.Add("");
                r.Add("[e0a030]" + string.Format(Kinetic.Text("feRecipesCraft", "Crafting recipes ({0})"), ws.Count) + "[-]");
                foreach (string s in ws) r.Add("  " + s);
            }
            return r;
        }

        static readonly Dictionary<string, bool> has = new Dictionary<string, bool>();

        public static bool Has(Block b)
        {
            if (b == null) return false;
            string n = b.GetBlockName();
            bool v;
            if (!has.TryGetValue(n, out v)) { v = Lines(b).Count > 0; has[n] = v; }
            return v;
        }

        /// <summary>Adds the "Recipes" radial command when the block has a book.</summary>
        public static void AddCommand(Block b, ref BlockActivationCommand[] cmds)
        {
            if (!Has(b)) return;
            if (cmds == null) cmds = new BlockActivationCommand[0];
            foreach (BlockActivationCommand c in cmds) if (c.text == Command) return;
            BlockActivationCommand[] r = new BlockActivationCommand[cmds.Length + 1];
            cmds.CopyTo(r, 0);
            r[cmds.Length] = new BlockActivationCommand(Command, "book", true, false, null);
            cmds = r;
        }

        public static void Open(Block b, EntityPlayerLocal player)
        {
            List<string> lines = Lines(b);
            string title = string.Format(Kinetic.Text("feRecipesTitle", "Recipes: {0}"), b.GetLocalizedBlockName());
            if (GameManager.Instance != null)
                GameManager.Instance.StartCoroutine(OpenWhenFree(b, player, lines, title));
            else
                OpenNow(b, player, lines, title);
        }

        /// <summary>Waits until the radial menu (and any other modal window) has fully closed, then opens.</summary>
        static IEnumerator OpenWhenFree(Block b, EntityPlayerLocal player, List<string> lines, string title)
        {
            LocalPlayerUI ui = LocalPlayerUI.GetUIForPlayer(player);
            // wait for the radial (a modal window) to finish closing; never force it (a radial left registered as open
            // but hidden suppressed every look text afterwards - UiWatchdog.cs)
            float until = Time.realtimeSinceStartup + 5f;
            while (ui != null && ui.windowManager != null && ui.windowManager.IsModalWindowOpen() && Time.realtimeSinceStartup < until)
                yield return null;
            if (ui == null || ui.windowManager == null) yield break;
            if (ui.windowManager.IsModalWindowOpen())
            {
                GUIWindow m = ui.windowManager.GetModalWindow();
                Log.Warning(FerroEngrenagemMod.LogPrefix + "window not opened: another modal window is still open (" + (m == null ? "?" : m.Id) + ")");
                yield break;
            }
            yield return null;
            yield return null;
            OpenNow(b, player, lines, title);
        }

        /// <summary>After the book closes: a hand transition still running after 1 s is stuck; finish it.</summary>
        public static IEnumerator UnstickHand(EntityPlayerLocal player)
        {
            yield return new WaitForSecondsRealtime(1f);
            if (player == null || player.inventory == null || !player.inventory.IsHandSwitching()) yield break;
            yield return new WaitForSecondsRealtime(1f);
            if (player == null || player.inventory == null || !player.inventory.IsHandSwitching()) yield break;
            try
            {
                AccessTools.Method(typeof(Hand), "CompleteTransition").Invoke(player.inventory.Hand, null);
                Log.Warning(FerroEngrenagemMod.LogPrefix + "recipe book: the held item was stuck switching; finished the transition");
            }
            catch (System.Exception e)
            {
                Log.Warning(FerroEngrenagemMod.LogPrefix + "recipe book: could not unstick the hand: " + e.Message);
            }
        }

        static void OpenNow(Block b, EntityPlayerLocal player, List<string> lines, string title)
        {
            LocalPlayerUI ui = LocalPlayerUI.GetUIForPlayer(player);
            bool shown = false;
            try
            {
                XUiC_FeRecipes.Title = title;
                XUiC_FeRecipes.Lines = lines;
                if (ui != null && ui.windowManager != null)
                {
                    ui.windowManager.Open(Window, true);
                    shown = ui.windowManager.IsWindowOpen(Window);
                }
            }
            catch (System.Exception e)
            {
                Log.Warning(FerroEngrenagemMod.LogPrefix + "recipe book window: " + e.Message);
            }
            if (!shown)
            {
                StringBuilder sb = new StringBuilder(title);
                for (int i = 0; i < lines.Count && i < 6; i++) sb.Append("\n").Append(lines[i]);
                GameManager.ShowTooltip(player, sb.ToString(), false, false, 0f);
            }
            Log.Out(FerroEngrenagemMod.LogPrefix + "recipe book " + b.GetBlockName() + ": " + lines.Count + " lines, window=" + shown);
        }
    }

    /// <summary>Controller of the "feRecipes" window: title, a page of lines, previous / next / close.</summary>
    [UnityEngine.Scripting.Preserve]
    public class XUiC_FeRecipes : XUiController
    {
        public static string Title = "";
        public static List<string> Lines = new List<string>();
        const int PerPage = 20;
        int page;

        int Pages
        {
            get { return Mathf.Max(1, (Lines.Count + PerPage - 1) / PerPage); }
        }

        void Hook(string id, XUiEvent_OnPressEventHandler h)
        {
            XUiController c = GetChildById(id);
            if (c != null) c.OnPress += h;
        }

        public override void Init()
        {
            base.Init();
            Hook("feRecipesPrev", (s, m) => { if (page > 0) { page--; RefreshBindings(); } });
            Hook("feRecipesNext", (s, m) => { if (page < Pages - 1) { page++; RefreshBindings(); } });
            Hook("feRecipesClose", (s, m) => xui.playerUI.windowManager.Close(WindowGroup, false));
        }

        public override void OnOpen()
        {
            base.OnOpen();
            page = 0;
            RefreshBindings();
        }

        public override void OnClose()
        {
            base.OnClose();
            EntityPlayerLocal pl = xui != null && xui.playerUI != null ? xui.playerUI.entityPlayer : null;
            if (pl != null && GameManager.Instance != null) GameManager.Instance.StartCoroutine(RecipeBook.UnstickHand(pl));
        }

        public override bool GetBindingValueInternal(ref string _value, string _bindingName)
        {
            switch (_bindingName)
            {
                case "fetitle":
                    _value = Title ?? "";
                    return true;
                case "febody":
                    StringBuilder sb = new StringBuilder();
                    for (int i = page * PerPage; i < Lines.Count && i < (page + 1) * PerPage; i++)
                        sb.Append(Lines[i]).Append('\n');
                    if (Lines.Count == 0) sb.Append(Kinetic.Text("feProcNone", "No processes for this machine"));
                    _value = sb.ToString();
                    return true;
                case "fepage":
                    _value = (page + 1) + " / " + Pages;
                    return true;
            }
            return base.GetBindingValueInternal(ref _value, _bindingName);
        }
    }
}
