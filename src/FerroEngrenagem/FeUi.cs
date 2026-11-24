// D12 (PLANO_CADEIA.md 5): the mod's own windows (Config/XUi_InGame/windows.xml, window groups in xui.xml).
//
//   feMachine   Machine Panel (tap E on a process machine): recipe, progress, stock, products, fluid bars, why it
//               waits; buttons Choose recipe / Put the item in hand / Take the products / On-Off.
//   fePicker    Recipe Picker: icons of the recipes of a process machine or of a mod workstation (fixed recipe), with
//               search and pages; "automatic" / "off" on top.
//   feConfig    Settings of the control blocks (valves, gauge, splitter, gate, counter, filter belt, funnel, arm,
//               clutch / speed box / regulator): - / + / Mode / Item in hand.
//   feNetwork   Network Panel (hold the Engineer's Wrench, hold E on a pipe, shaft, belt or machine -> Network).
//   feGuide     Production Guide (the Engineer's Manual, use it): every item with a recipe, searchable; an item's
//               page shows how it is made (machine, ingredients) and what uses it; ingredients are clickable.
//
// The windows open a few frames after the radial menu closed (RecipeBook.cs: opening a modal window inside the
// radial callback broke the held item). Single player / host for now (the actions call the server code directly).
//
// C# 5 only.

using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using UnityEngine;

namespace FerroEngrenagem
{
    public static class FeUi
    {
        public const string ConfigCommand = "fe_config";
        public const string NetCommand = "fe_net";
        public const string CraftPickCommand = "fe_craft_pick";
        public const string Wrench = "feEngineerWrench";

        public static Vector3i Target;
        public static EntityPlayerLocal Player;

        static World W()
        {
            return GameManager.Instance == null ? null : GameManager.Instance.World;
        }

        public static void Open(EntityPlayerLocal player, string window)
        {
            Player = player;
            if (GameManager.Instance != null) GameManager.Instance.StartCoroutine(OpenWhenFree(player, window));
        }

        static IEnumerator OpenWhenFree(EntityPlayerLocal player, string window)
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
            try
            {
                if (ui != null && ui.windowManager != null) ui.windowManager.Open(window, true);
            }
            catch (System.Exception e)
            {
                Log.Warning(FerroEngrenagemMod.LogPrefix + "window " + window + ": " + e.Message);
            }
            if (ui == null || ui.windowManager == null || !ui.windowManager.IsWindowOpen(window))
                Log.Warning(FerroEngrenagemMod.LogPrefix + "window " + window + " did not open");
        }

        public static void OpenMachine(EntityPlayerLocal player, Vector3i p) { Target = p; XUiC_FePicker.Craft = false; Open(player, "feMachine"); }
        public static void OpenPicker(EntityPlayerLocal player, Vector3i p) { Target = p; XUiC_FePicker.Craft = false; Open(player, "fePicker"); }
        public static void OpenCraftPicker(EntityPlayerLocal player, Vector3i p) { Target = p; XUiC_FePicker.Craft = true; Open(player, "fePicker"); }
        public static void OpenConfig(EntityPlayerLocal player, Vector3i p) { Target = p; Open(player, "feConfig"); }
        public static void OpenNetwork(EntityPlayerLocal player, Vector3i p) { Target = p; Open(player, "feNetwork"); }

        public static void OpenGuide(EntityPlayerLocal player, string item)
        {
            XUiC_FeGuide.Start = item;
            Open(player, "feGuide");
        }

        static bool HoldsWrench(EntityAlive e)
        {
            EntityPlayerLocal pl = e as EntityPlayerLocal;
            if (pl == null || pl.inventory == null) return false;
            ItemValue iv = pl.inventory.holdingItemItemValue;
            return iv != null && !iv.IsEmpty() && iv.ItemClass != null && iv.ItemClass.GetItemName() == Wrench;
        }

        /// <summary>Holding the Engineer's Wrench: "Network" goes first in the radial.</summary>
        public static void AddNetCommand(EntityAlive focusing, ref BlockActivationCommand[] cmds)
        {
            if (!HoldsWrench(focusing)) return;
            if (cmds == null) cmds = new BlockActivationCommand[0];
            foreach (BlockActivationCommand c in cmds) if (c.text == NetCommand) return;
            BlockActivationCommand[] r = new BlockActivationCommand[cmds.Length + 1];
            r[0] = new BlockActivationCommand(NetCommand, "search", true, false, null);
            cmds.CopyTo(r, 1);
            cmds = r;
        }

        /// <summary>Blocks that open the Settings window.</summary>
        public static bool HasConfig(Block b)
        {
            if (b == null) return false;
            FluidKind k = Fluids.Kind(b);
            if (k == FluidKind.Valve || k == FluidKind.Gauge) return true;
            if (b is BlockFeArm || b is BlockFeFunnel) return true;
            if (Belt.Is(b) && (Logistics.IsSplitter(b) || Logistics.IsGate(b) || Logistics.IsCounter(b) || Belt.IsFilter(b))) return true;
            KineticKind kk = Kinetic.Kind(b);
            return kk == KineticKind.Clutch || kk == KineticKind.SpeedBox || kk == KineticKind.Regulator;
        }

        /// <summary>The mod's window commands, from any block class. True when handled.</summary>
        public static bool HandleCommand(string cmd, World w, Vector3i pos, BlockValue bv, EntityPlayerLocal player)
        {
            Vector3i p = Fluids.ParentOf(w, pos, bv);
            switch (cmd)
            {
                case ConfigCommand: OpenConfig(player, p); return true;
                case NetCommand: OpenNetwork(player, pos); return true;
                case CraftPickCommand: OpenCraftPicker(player, p); return true;
                case ProcessMachine.PanelCommand:
                    if (!ProcessMachine.Is(bv.Block)) return false;
                    OpenMachine(player, p);
                    return true;
            }
            return false;
        }

        public static string IconOf(string item)
        {
            ItemClass ic = ItemClass.GetItemClass(item, false);
            if (ic == null) return "";
            string n = ic.GetIconName();
            return string.IsNullOrEmpty(n) ? item : n;
        }

        // ------------------------------------------------------------ settings of the control blocks
        static string F1(float v) { return v.ToString("0.0", CultureInfo.InvariantCulture); }

        public static string ConfigTitle()
        {
            World w = W();
            return w == null ? "" : w.GetBlock(Target).Block.GetLocalizedBlockName();
        }

        public static string ConfigText()
        {
            World w = W();
            if (w == null) return "";
            BlockValue bv = w.GetBlock(Target);
            Block b = bv.Block;
            FluidKind k = Fluids.Kind(b);
            StringBuilder sb = new StringBuilder();
            if (k == FluidKind.Valve || k == FluidKind.Gauge)
            {
                FluidState s = FluidStore.Get(Target);
                sb.Append("[e0a030]").Append(FluidControl.SettingText(b, s)).Append("[-]\n\n");
                sb.Append(FluidControl.Describe(w, Target, bv, s)).Append("\n\n");
                string t = k == FluidKind.Gauge ? "gauge" : FluidControl.ValveType(b);
                if (t == "registro") sb.Append(Kinetic.Text("feCfgHelpMode", "Mode: open / closed / by signal"));
                else if (t == "separador") sb.Append(Kinetic.Text("feCfgHelpSep", "Mode: next fluid. Item in hand: the fluid of that item"));
                else if (t != "retencao") sb.Append(Kinetic.Text("feCfgHelpPlus", "- / +: change the value"));
                return sb.ToString();
            }
            if (b is BlockFeArm)
            {
                sb.Append(Logistics.DescribeArm(w, Target, bv)).Append("\n\n");
                sb.Append(Kinetic.Text("feCfgHelpArm", "- / +: items at a time. Mode: reach 1 or 2 blocks. Item in hand: filter (empty hand: any)"));
                return sb.ToString();
            }
            if (b is BlockFeFunnel)
            {
                sb.Append(Funnel.Describe(w, Target, bv)).Append("\n\n");
                sb.Append(Kinetic.Text("feCfgHelpFunnel", "- / +: items at a time. Item in hand: filter (empty hand: any)"));
                return sb.ToString();
            }
            if (Belt.Is(b))
            {
                sb.Append(Belt.Describe(w, Target, bv, Kinetic.Get(w, Target))).Append("\n\n");
                if (Logistics.IsSplitter(b)) sb.Append(Kinetic.Text("feCfgHelpSplit", "Mode: next ratio (front : each side)"));
                else if (Logistics.IsGate(b)) sb.Append(Kinetic.Text("feCfgHelpGate", "Mode: stop while signalled / run only while signalled"));
                else if (Logistics.IsCounter(b)) sb.Append(Kinetic.Text("feCfgHelpCounter", "- / +: items per signal. Mode: reset the count"));
                else sb.Append(Kinetic.Text("feCfgHelpFilter", "Item in hand: the filter (empty hand clears)"));
                return sb.ToString();
            }
            sb.Append(KineticLookController.Describe(Target, bv, false)).Append("\n\n");
            sb.Append(Kinetic.Text("feCfgHelpKinetic", "Mode: next setting"));
            return sb.ToString();
        }

        static string HeldItem()
        {
            if (Player == null || Player.inventory == null) return null;
            ItemValue iv = Player.inventory.holdingItemItemValue;
            if (iv == null || iv.IsEmpty() || iv.ItemClass == null || iv.ItemClass.GetItemName() == "meleeHandPlayer") return null;
            return iv.ItemClass.GetItemName();
        }

        /// <summary>act: "minus", "plus", "mode", "hand".</summary>
        public static void ConfigAct(string act)
        {
            World w = W();
            if (w == null) return;
            BlockValue bv = w.GetBlock(Target);
            Block b = bv.Block;
            FluidKind k = Fluids.Kind(b);
            int sign = act == "minus" ? -1 : 1;
            if (k == FluidKind.Valve || k == FluidKind.Gauge)
            {
                FluidState s = FluidStore.Get(Target);
                string t = k == FluidKind.Gauge ? "gauge" : FluidControl.ValveType(b);
                if (t == "registro" && act == "mode")
                    s.Pick = s.Pick == "" ? "closed" : s.Pick == "closed" ? "signal" : "";
                else if (t == "separador" && act == "mode")
                {
                    List<string> fl = new List<string> { "", Fluids.Water, Fluids.Steam, Fluids.Oil, Fluids.Gasoline, Fluids.Lubricant };
                    foreach (string f in Processes.FluidDefs.Keys) if (!fl.Contains(f) && !Fluids.IsMetal(f)) fl.Add(f);
                    int i = fl.IndexOf(s.Pick);
                    s.Pick = fl[(i + 1) % fl.Count];
                }
                else if (t == "separador" && act == "hand")
                {
                    float per;
                    string f = HeldItem() == null ? null : Fluids.FluidOfItem(HeldItem(), out per);
                    s.Pick = f ?? "";
                }
                else if ((act == "minus" || act == "plus") && t != "registro" && t != "separador" && t != "retencao")
                {
                    bool gas = Fluids.IsGas(s.Fluid);
                    float def = t == "gauge" ? (gas ? 5f : 90f) : FluidControl.DefaultSetting(t);
                    float step = t == "reguladora" ? 10f : t == "gauge" && !gas ? 5f : 0.5f;
                    float v = FluidControl.Setting(s, def) + sign * step;
                    float max = t == "gauge" && !gas ? 100f : t == "reguladora" ? 2000f : 12f;
                    s.Pick = Mathf.Clamp(v, step, max).ToString("0.#", CultureInfo.InvariantCulture);
                }
                FluidStore.MarkDirty();
                return;
            }
            if (b is BlockFeArm || b is BlockFeFunnel)
            {
                if (act == "hand") { LogicStore.SetField(Target, "f", HeldItem() ?? ""); return; }
                if (act == "mode" && b is BlockFeArm) { LogicStore.SetField(Target, "r", Logistics.Reach(Target) == 1 ? "2" : "1"); return; }
                int a = Logistics.Amount(Target, b is BlockFeFunnel ? (int)Fluids.Prop(b, "FeFunnelAmount", 16f) : 8);
                int[] steps = { 1, 2, 4, 8, 16, 32, 64 };
                int idx = System.Array.IndexOf(steps, a);
                if (idx < 0) idx = 3;
                idx = Mathf.Clamp(idx + sign, 0, steps.Length - 1);
                if (act == "minus" || act == "plus") LogicStore.SetField(Target, "a", steps[idx].ToString());
                return;
            }
            if (Belt.Is(b))
            {
                if (Logistics.IsSplitter(b) && act == "mode")
                {
                    int i = System.Array.IndexOf(Logistics.Ratios, Logistics.Ratio(Target));
                    LogicStore.SetField(Target, "ratio", Logistics.Ratios[(i + 1) % Logistics.Ratios.Length]);
                }
                else if (Logistics.IsGate(b) && act == "mode")
                    LogicStore.SetField(Target, "inv", LogicStore.Field(Target, "inv") == "1" ? "" : "1");
                else if (Logistics.IsCounter(b))
                {
                    if (act == "mode") LogicStore.SetField(Target, "c", "0");
                    else if (act == "minus" || act == "plus")
                        LogicStore.SetField(Target, "n", Mathf.Clamp(Logistics.CounterN(Target) + sign * (Logistics.CounterN(Target) >= 20 ? 10 : 1), 1, 1000).ToString());
                }
                else if (Belt.IsFilter(b) && act == "hand") BeltStore.SetFilter(Target, HeldItem());
                return;
            }
            if (act == "mode")
            {
                int n = BlockFeKinetic.Settings(Kinetic.Kind(b));
                if (n <= 0) return;
                BlockValue nbv = bv;
                nbv.meta = (byte)((bv.meta + 1) % n);
                w.SetBlockRPC(Target, nbv);
                Kinetic.Invalidate();
            }
        }

        // ------------------------------------------------------------ network panel
        public static string NetworkText()
        {
            World w = W();
            if (w == null) return "";
            BlockValue bv = w.GetBlock(Target);
            StringBuilder sb = new StringBuilder();
            sb.Append("[e0a030]").Append(bv.Block.GetLocalizedBlockName()).Append("[-]  ").Append(Target.ToString()).Append("\n\n");
            TorqueNet tn = Kinetic.Get(w, Target);
            if (tn != null)
            {
                sb.Append("[e0a030]").Append(Kinetic.Text("feNetTorque", "Torque network")).Append("[-]\n");
                sb.Append(string.Format(Kinetic.Text("feNetTorqueLine", "Sources: {0} - capacity {1} UT - used {2} UT - {3} RPM - {4} nodes, {5} machines"),
                    tn.Sources, tn.Capacity, tn.Usage, Mathf.RoundToInt(tn.RefRpm), tn.Nodes.Count, tn.Machines.Count)).Append("\n");
                sb.Append(ProcessMachine.Bar(tn.Capacity > 0 ? (float)tn.Usage / tn.Capacity : 0f, 40)).Append("\n");
                if (tn.Overloaded) sb.Append("[ff6060]").Append(Kinetic.Text("feNetOverload", "OVERLOADED: the machines ask more than the sources give")).Append("[-]\n");
                if (tn.Locked) sb.Append("[ff6060]").Append(string.Format(Kinetic.Text("feNetLocked", "LOCKED: {0}"), tn.LockReason)).Append("[-]\n");
                if (!tn.Running && !tn.Overloaded && !tn.Locked) sb.Append(Kinetic.Text("feNetStopped", "Stopped: no source running")).Append("\n");
                sb.Append("\n");
            }
            FluidNet fn;
            if (FluidTicker.NetByPipe.TryGetValue(Target, out fn))
            {
                sb.Append("[e0a030]").Append(Kinetic.Text("feNetFluid", "Fluid network")).Append("[-]\n");
                sb.Append(string.Format(Kinetic.Text("feNetFluidLine", "{0}: {1} L/min - {2} pipes - tanks {3} L"),
                    Fluids.FluidName(fn.Fluid), Mathf.RoundToInt(fn.FlowPerMin), fn.Pipes.Count, Mathf.RoundToInt(fn.Stored))).Append("\n");
                if (Fluids.IsGas(fn.Fluid))
                    sb.Append(string.Format(Kinetic.Text("feNetBar", "Pressure {0} bar (weakest pipe {1} bar)"), F1(fn.Pressure), F1(fn.MaxBar))).Append("\n");
                if (fn.Blocked) sb.Append("[ff6060]").Append(Kinetic.Text("feFluidBlocked", "BLOCKED: two different fluids in this pipe")).Append("[-]\n");
                if (fn.Leak) sb.Append("[ff6060]").Append(Kinetic.Text("fePipeLeak", "LEAKING: the pressure is above what the pipes stand (use High Pressure Pipes)")).Append("[-]\n");
                Dictionary<string, int> ins = new Dictionary<string, int>(), outs = new Dictionary<string, int>();
                HashSet<Vector3i> seen = new HashSet<Vector3i>();
                foreach (FluidPort port in fn.Ports)
                {
                    if (!seen.Add(port.Owner)) continue;
                    string n = w.GetBlock(port.Owner).Block.GetLocalizedBlockName();
                    Dictionary<string, int> d = port.Out ? outs : ins;
                    d[n] = (d.ContainsKey(n) ? d[n] : 0) + 1;
                }
                sb.Append(Kinetic.Text("feNetGives", "Give into it: ")).Append(Join(outs)).Append("\n");
                sb.Append(Kinetic.Text("feNetTakes", "Take from it: ")).Append(Join(ins)).Append("\n\n");
            }
            if (Fluids.Kind(bv.Block) != FluidKind.None && !Fluids.IsConduit(Fluids.Kind(bv.Block)))
                sb.Append(KineticLookController.Escape(FluidText.Describe(Target, bv, false))).Append("\n\n");
            if (Belt.Is(bv.Block)) sb.Append(Belt.Describe(w, Target, bv, tn)).Append("\n");
            return sb.ToString();
        }

        static string Join(Dictionary<string, int> d)
        {
            if (d.Count == 0) return "-";
            List<string> l = new List<string>();
            foreach (KeyValuePair<string, int> kv in d) l.Add(kv.Value > 1 ? kv.Value + "x " + kv.Key : kv.Key);
            return string.Join(", ", l.ToArray());
        }
    }

    // ================================================================== controllers
    public abstract class XUiC_FeBase : XUiController
    {
        float next;

        protected void Hook(string id, XUiEvent_OnPressEventHandler h)
        {
            XUiController c = GetChildById(id);
            if (c != null) c.OnPress += h;
        }

        protected void Close()
        {
            xui.playerUI.windowManager.Close(WindowGroup, false);
        }

        public override void Update(float _dt)
        {
            base.Update(_dt);
            if (Time.time < next) return;
            next = Time.time + 0.5f;
            if (GameManager.Instance == null || GameManager.Instance.World == null || FeUi.Player == null) return;
            try { Tick(); }
            catch (System.Exception e) { Log.Warning(FerroEngrenagemMod.LogPrefix + GetType().Name + ": " + e.Message); }
        }

        protected virtual void Tick() { }

        /// <summary>The bindings of the window. The game also asks them while loading (no world yet) and while
        /// the window is closed: then (and on any error) every fe* binding is empty instead of an exception.</summary>
        protected abstract bool Binding(ref string _value, string _bindingName);

        public override bool GetBindingValueInternal(ref string _value, string _bindingName)
        {
            bool ours = _bindingName != null && _bindingName.StartsWith("fe", System.StringComparison.Ordinal);
            if (ours && (GameManager.Instance == null || GameManager.Instance.World == null || FeUi.Player == null))
            {
                _value = _bindingName.Length > 4 && (_bindingName[3] == 'v') ? "false" : "";
                return true;
            }
            try
            {
                if (Binding(ref _value, _bindingName)) return true;
            }
            catch (System.Exception e)
            {
                if (ours)
                {
                    _value = "";
                    if (!warned) { warned = true; Log.Warning(FerroEngrenagemMod.LogPrefix + GetType().Name + " binding " + _bindingName + ": " + e.Message); }
                    return true;
                }
            }
            return base.GetBindingValueInternal(ref _value, _bindingName);
        }

        static bool warned;

        public override void OnClose()
        {
            base.OnClose();
            EntityPlayerLocal pl = xui != null && xui.playerUI != null ? xui.playerUI.entityPlayer : null;
            if (pl != null && GameManager.Instance != null) GameManager.Instance.StartCoroutine(RecipeBook.UnstickHand(pl));
        }
    }

    [UnityEngine.Scripting.Preserve]
    public class XUiC_FeMachine : XUiC_FeBase
    {
        public override void Init()
        {
            base.Init();
            Hook("feMBtnPick", (s, m) => { Close(); FeUi.OpenPicker(FeUi.Player, FeUi.Target); });
            Hook("feMBtnPut", (s, m) => { Act("put"); });
            Hook("feMBtnTake", (s, m) => { Act("take"); });
            Hook("feMBtnOnOff", (s, m) => { Act("onoff"); });
            Hook("feMBtnClose", (s, m) => Close());
        }

        string msg = "";

        void Act(string a)
        {
            World w = GameManager.Instance.World;
            FluidState st = FluidStore.Get(FeUi.Target);
            if (a == "put") msg = ProcessMachine.PutHeld(w, FeUi.Target, FeUi.Player);
            else if (a == "take") msg = ProcessMachine.TakeAll(w, FeUi.Target, FeUi.Player);
            else { st.Off = !st.Off; FluidStore.MarkDirty(); msg = st.Off ? Kinetic.Text("feProcOff", "Switched off") : Kinetic.Text("feProcOn", "Switched on"); }
            RefreshBindings();
        }

        public override void OnOpen()
        {
            base.OnOpen();
            msg = "";
            RefreshBindings();
        }

        protected override void Tick() { RefreshBindings(); }

        protected override bool Binding(ref string _value, string _bindingName)
        {
            World w = GameManager.Instance == null ? null : GameManager.Instance.World;
            switch (_bindingName)
            {
                case "fetitle":
                    _value = w == null ? "" : w.GetBlock(FeUi.Target).Block.GetLocalizedBlockName();
                    return true;
                case "febody":
                    if (w == null) { _value = ""; return true; }
                    BlockValue bv = w.GetBlock(FeUi.Target);
                    _value = ProcessMachine.Is(bv.Block) ? ProcessMachine.Panel(w, FeUi.Target, bv, FluidStore.Get(FeUi.Target)) : "";
                    if (msg.Length > 0) _value += "\n[a0c0ff]" + msg + "[-]";
                    return true;
                case "feonoff":
                    _value = FluidStore.Get(FeUi.Target).Off ? Kinetic.Text("feBtnTurnOn", "Turn on") : Kinetic.Text("feBtnTurnOff", "Turn off");
                    return true;
            }
            return false;
        }
    }

    [UnityEngine.Scripting.Preserve]
    public class XUiC_FePicker : XUiC_FeBase
    {
        public static bool Craft;
        const int Rows = 10;
        int page;
        string search = "";

        class Row { public string Id, Icon, Text; public bool Chosen; }
        List<Row> rows = new List<Row>();

        public override void Init()
        {
            base.Init();
            for (int i = 0; i < Rows; i++)
            {
                int k = i;
                Hook("fePRow" + i, (s, m) => Pick(k));
            }
            Hook("fePPrev", (s, m) => { if (page > 0) { page--; RefreshBindings(); } });
            Hook("fePNext", (s, m) => { if ((page + 1) * Rows < rows.Count) { page++; RefreshBindings(); } });
            Hook("fePClose", (s, m) => Close());
        }

        void Build()
        {
            rows.Clear();
            World w = GameManager.Instance.World;
            BlockValue bv = w.GetBlock(FeUi.Target);
            string q = search.Trim().ToLowerInvariant();
            if (!Craft && ProcessMachine.Is(bv.Block))
            {
                FluidState s = FluidStore.Get(FeUi.Target);
                rows.Add(new Row { Id = "", Icon = "", Text = Kinetic.Text("feProcAuto", "Recipe: automatic (the first one it has everything for)"), Chosen = s.Pick == "" });
                foreach (Process p in ProcessMachine.Of(bv.Block))
                {
                    string label = ProcessMachine.Label(p);
                    if (q.Length > 0 && !label.ToLowerInvariant().Contains(q)) continue;
                    string icon = p.Output != null ? FeUi.IconOf(p.Output) : p.Inputs.Length > 0 ? FeUi.IconOf(p.Inputs[0]) : "";
                    rows.Add(new Row { Id = p.Id, Icon = icon, Text = label + "  (" + RecipeTime(p.Time) + ")", Chosen = s.Pick == p.Id });
                }
            }
            else
            {
                string cur = AutoCraft.Current(FeUi.Target);
                rows.Add(new Row { Id = null, Icon = "", Text = Kinetic.Text("feAutoOff", "Fixed recipe off"), Chosen = cur == "" });
                HashSet<string> seen = new HashSet<string>();
                foreach (Recipe r in AutoCraft.Recipes(bv.Block))
                {
                    if (!seen.Add(r.GetName())) continue;
                    ItemClass oc = r.GetOutputItemClass();
                    string name = oc == null ? r.GetName() : oc.GetLocalizedItemName();
                    List<string> ins = new List<string>();
                    foreach (ItemStack st in r.ingredients)
                        if (st != null && st.itemValue.ItemClass != null) ins.Add(st.count + "x " + st.itemValue.ItemClass.GetLocalizedItemName());
                    string text = r.count + "x " + name + "  <-  " + string.Join(" + ", ins.ToArray());
                    if (q.Length > 0 && !text.ToLowerInvariant().Contains(q)) continue;
                    rows.Add(new Row { Id = r.GetName(), Icon = r.GetIcon(), Text = text, Chosen = cur == r.GetName() });
                }
            }
            if (page * Rows >= rows.Count) page = 0;
        }

        static string RecipeTime(float t)
        {
            return t >= 60f ? Mathf.RoundToInt(t / 6f) / 10f + " min" : Mathf.RoundToInt(t) + " s";
        }

        void Pick(int i)
        {
            int idx = page * Rows + i;
            if (idx >= rows.Count) return;
            World w = GameManager.Instance.World;
            BlockValue bv = w.GetBlock(FeUi.Target);
            string msg;
            if (!Craft && ProcessMachine.Is(bv.Block)) msg = ProcessMachine.Choose(bv.Block, FluidStore.Get(FeUi.Target), rows[idx].Id);
            else msg = AutoCraft.Choose(w, FeUi.Target, bv.Block, rows[idx].Id);
            Log.Out(FerroEngrenagemMod.LogPrefix + "picker at " + FeUi.Target + ": " + msg);
            GameManager.ShowTooltip(FeUi.Player, msg, false, false, 0f);
            Close();
        }

        public override void OnOpen()
        {
            base.OnOpen();
            page = 0;
            search = "";
            Build();
            RefreshBindings();
        }

        protected override bool Binding(ref string _value, string _bindingName)
        {
            if (_bindingName == "fetitle")
            {
                World w = GameManager.Instance.World;
                _value = string.Format(Kinetic.Text("fePickerTitle", "Choose the recipe: {0}"), w.GetBlock(FeUi.Target).Block.GetLocalizedBlockName());
                return true;
            }
            if (_bindingName == "fepage")
            {
                _value = (page + 1) + " / " + Mathf.Max(1, (rows.Count + Rows - 1) / Rows);
                return true;
            }
            if (_bindingName.StartsWith("fept") || _bindingName.StartsWith("fepi") || _bindingName.StartsWith("fepv"))
            {
                int i;
                if (!int.TryParse(_bindingName.Substring(4), out i)) return false;
                int idx = page * Rows + i;
                Row r = idx < rows.Count ? rows[idx] : null;
                if (_bindingName.StartsWith("fept")) _value = r == null ? "" : (r.Chosen ? "[60d060]> " : "") + r.Text + (r.Chosen ? "[-]" : "");
                else if (_bindingName.StartsWith("fepi")) _value = r == null ? "" : r.Icon;
                else _value = r == null ? "false" : "true";
                return true;
            }
            return false;
        }
    }

    [UnityEngine.Scripting.Preserve]
    public class XUiC_FeConfig : XUiC_FeBase
    {
        public override void Init()
        {
            base.Init();
            Hook("feCMinus", (s, m) => { FeUi.ConfigAct("minus"); RefreshBindings(); });
            Hook("feCPlus", (s, m) => { FeUi.ConfigAct("plus"); RefreshBindings(); });
            Hook("feCMode", (s, m) => { FeUi.ConfigAct("mode"); RefreshBindings(); });
            Hook("feCHand", (s, m) => { FeUi.ConfigAct("hand"); RefreshBindings(); });
            Hook("feCClose", (s, m) => Close());
        }

        public override void OnOpen() { base.OnOpen(); RefreshBindings(); }
        protected override void Tick() { RefreshBindings(); }

        protected override bool Binding(ref string _value, string _bindingName)
        {
            if (_bindingName == "fetitle") { _value = FeUi.ConfigTitle(); return true; }
            if (_bindingName == "febody") { _value = FeUi.ConfigText(); return true; }
            return false;
        }
    }

    [UnityEngine.Scripting.Preserve]
    public class XUiC_FeNetwork : XUiC_FeBase
    {
        public override void Init()
        {
            base.Init();
            Hook("feNClose", (s, m) => Close());
        }

        public override void OnOpen() { base.OnOpen(); RefreshBindings(); }
        protected override void Tick() { RefreshBindings(); }

        protected override bool Binding(ref string _value, string _bindingName)
        {
            if (_bindingName == "fetitle") { _value = Kinetic.Text("feNetTitle", "Network Panel"); return true; }
            if (_bindingName == "febody") { _value = FeUi.NetworkText(); return true; }
            return false;
        }
    }

    // ------------------------------------------------------------------ Production Guide
    [UnityEngine.Scripting.Preserve]
    public class XUiC_FeGuide : XUiC_FeBase
    {
        public static string Start;
        const int Rows = 12;
        int page;
        string search = "", item;
        readonly List<string> history = new List<string>();
        List<string> rowItems = new List<string>();
        List<string> rowText = new List<string>();
        string body = "";

        public override void Init()
        {
            base.Init();
            for (int i = 0; i < Rows; i++)
            {
                int k = i;
                Hook("feGRow" + i, (s, m) => Click(k));
            }
            Hook("feGPrev", (s, m) => { if (page > 0) { page--; RefreshBindings(); } });
            Hook("feGNext", (s, m) => { if ((page + 1) * Rows < rowItems.Count) { page++; RefreshBindings(); } });
            Hook("feGIndex", (s, m) => { item = null; history.Clear(); Build(); });
            Hook("feGHand", (s, m) =>
            {
                ItemValue iv = FeUi.Player == null ? null : FeUi.Player.inventory.holdingItemItemValue;
                if (iv != null && !iv.IsEmpty() && iv.ItemClass != null) Go(iv.ItemClass.GetItemName());
            });
            Hook("feGBack", (s, m) =>
            {
                if (history.Count == 0) { item = null; Build(); return; }
                item = history[history.Count - 1];
                history.RemoveAt(history.Count - 1);
                Build();
            });
            Hook("feGClose", (s, m) => Close());
            Hook("feGLetter", (s, m) => { search = NextLetter(search, 1); item = null; Build(); });
            Hook("feGLetterBack", (s, m) => { search = NextLetter(search, -1); item = null; Build(); });
        }

        static string RemoveAccent(string t)
        {
            string a = "ÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç", b = "AAAAEEIOOOUCaaaaeeiooouc";
            System.Text.StringBuilder sb = new System.Text.StringBuilder(t);
            for (int i = 0; i < sb.Length; i++)
            {
                int k = a.IndexOf(sb[i]);
                if (k >= 0) sb[i] = b[k];
            }
            return sb.ToString();
        }

        void Go(string it)
        {
            if (item != null) history.Add(item);
            item = it;
            Build();
        }

        void Click(int i)
        {
            int idx = page * Rows + i;
            if (idx < rowItems.Count && rowItems[idx] != null) Go(rowItems[idx]);
        }

        public override void OnOpen()
        {
            base.OnOpen();
            history.Clear();
            item = Start;
            Start = null;
            search = "";
            Build();
        }

        const string Letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

        static string NextLetter(string cur, int step)
        {
            int i = cur.Length == 0 ? -1 : Letters.IndexOf(cur[0]);
            i += step;
            if (i < -1) i = Letters.Length - 1;
            if (i >= Letters.Length) i = -1;
            return i < 0 ? "" : Letters[i].ToString();
        }

        void Build()
        {
            page = 0;
            if (item == null) BuildIndex();
            else BuildItem(item);
            RefreshBindings();
        }

        void BuildIndex()
        {
            rowItems = new List<string>();
            rowText = new List<string>();
            string q = search.Trim().ToLowerInvariant();
            List<KeyValuePair<string, string>> l = new List<KeyValuePair<string, string>>();
            foreach (string n in GuideData.Items())
            {
                string loc = ProcessMachine.ItemName(n);
                if (q.Length > 0 && !RemoveAccent(loc).ToLowerInvariant().StartsWith(q)) continue;
                l.Add(new KeyValuePair<string, string>(loc, n));
            }
            l.Sort((a, b) => string.Compare(a.Key, b.Key, System.StringComparison.CurrentCultureIgnoreCase));
            foreach (KeyValuePair<string, string> kv in l) { rowItems.Add(kv.Value); rowText.Add(kv.Key); }
            body = string.Format(Kinetic.Text("feGuideIndex", "Index: {0} items. Letter filter with the A / Z buttons, click an item, or hold one and press \"Item in hand\"."), l.Count);
        }

        void BuildItem(string it)
        {
            rowItems = new List<string>();
            rowText = new List<string>();
            StringBuilder sb = new StringBuilder();
            sb.Append("[e0a030]").Append(ProcessMachine.ItemName(it)).Append("[-]\n");
            List<string> routes = GuideData.Routes(it);
            if (routes.Count == 0) sb.Append(Kinetic.Text("feGuideNoRoute", "No recipe: found in the world (loot, mining, harvest, traders)")).Append("\n");
            for (int i = 0; i < routes.Count && i < 6; i++) sb.Append("- ").Append(routes[i]).Append("\n");
            if (routes.Count > 6) sb.Append(string.Format(Kinetic.Text("feGuideMore", "... and {0} more"), routes.Count - 6)).Append("\n");
            body = sb.ToString();
            foreach (string ing in GuideData.Ingredients(it))
            {
                rowItems.Add(ing);
                rowText.Add("[a0c0ff]" + Kinetic.Text("feGuideNeeds", "needs") + "[-]  " + ProcessMachine.ItemName(ing));
            }
            foreach (string u in GuideData.Uses(it))
            {
                rowItems.Add(u);
                rowText.Add("[60d060]" + Kinetic.Text("feGuideUsedIn", "used in") + "[-]  " + ProcessMachine.ItemName(u));
            }
        }

        protected override bool Binding(ref string _value, string _bindingName)
        {
            switch (_bindingName)
            {
                case "fetitle": _value = Kinetic.Text("feGuideTitle", "Production Guide"); return true;
                case "feletter": _value = search.Length == 0 ? Kinetic.Text("feGuideAll", "All") : search; return true;
                case "febody": _value = body; return true;
                case "fepage": _value = (page + 1) + " / " + Mathf.Max(1, (rowItems.Count + Rows - 1) / Rows); return true;
            }
            if (_bindingName.StartsWith("fegt") || _bindingName.StartsWith("fegi") || _bindingName.StartsWith("fegv"))
            {
                int i;
                if (!int.TryParse(_bindingName.Substring(4), out i)) return false;
                int idx = page * Rows + i;
                bool has = idx < rowItems.Count;
                if (_bindingName.StartsWith("fegt")) _value = has ? rowText[idx] : "";
                else if (_bindingName.StartsWith("fegi")) _value = has ? FeUi.IconOf(rowItems[idx]) : "";
                else _value = has ? "true" : "false";
                return true;
            }
            return false;
        }
    }

    /// <summary>What the Guide knows: every recipe of the game and every chain process.</summary>
    public static class GuideData
    {
        static List<string> items;
        static Dictionary<string, List<string>> uses;

        static void Ensure()
        {
            if (items != null) return;
            HashSet<string> set = new HashSet<string>();
            uses = new Dictionary<string, List<string>>();
            List<Recipe> all = CraftingManager.GetAllRecipes();
            if (all != null)
                foreach (Recipe r in all)
                {
                    if (r == null || r.IsScrap || r.wildcardForgeCategory) continue;
                    ItemClass oc = r.GetOutputItemClass();
                    if (oc == null) continue;
                    string o = oc.GetItemName();
                    set.Add(o);
                    foreach (ItemStack st in r.ingredients)
                        if (st != null && st.itemValue.ItemClass != null) Use(st.itemValue.ItemClass.GetItemName(), o);
                }
            foreach (Process p in Processes.All)
            {
                string o = p.Output ?? p.Extra;
                if (p.Output != null) set.Add(p.Output);
                if (p.Extra != null) set.Add(p.Extra);
                if (o == null) continue;
                foreach (string i in p.Inputs) Use(i, o);
                if (p.Mold != null) Use(p.Mold, o);
            }
            items = new List<string>(set);
        }

        static void Use(string ing, string product)
        {
            List<string> l;
            if (!uses.TryGetValue(ing, out l)) { l = new List<string>(); uses[ing] = l; }
            if (!l.Contains(product)) l.Add(product);
        }

        public static List<string> Items()
        {
            Ensure();
            return items;
        }

        public static List<string> Uses(string item)
        {
            Ensure();
            List<string> l;
            return uses.TryGetValue(item, out l) ? l : new List<string>();
        }

        static string Area(string a)
        {
            if (string.IsNullOrEmpty(a)) return Kinetic.Text("feGuideHand", "by hand (inventory)");
            Block b = Block.GetBlockByName(a, false);
            return b != null ? b.GetLocalizedBlockName() : a;
        }

        public static List<string> Routes(string item)
        {
            List<string> r = new List<string>();
            foreach (Process p in Processes.Making(item))
                r.Add(Processes.MachineName(p.Machine) + ": " + ProcessMachine.Label(p) + (p.Mold != null ? " [" + ProcessMachine.ItemName(p.Mold) + "]" : ""));
            List<Recipe> rs = CraftingManager.GetAllRecipes(item);
            if (rs != null)
                foreach (Recipe rc in rs)
                {
                    if (rc == null || rc.IsScrap || rc.wildcardForgeCategory) continue;
                    List<string> ins = new List<string>();
                    foreach (ItemStack st in rc.ingredients)
                        if (st != null && st.itemValue.ItemClass != null) ins.Add(st.count + "x " + st.itemValue.ItemClass.GetLocalizedItemName());
                    r.Add(Area(rc.craftingArea) + ": " + rc.count + "x <- " + string.Join(" + ", ins.ToArray()));
                }
            return r;
        }

        public static List<string> Ingredients(string item)
        {
            List<string> r = new List<string>();
            foreach (Process p in Processes.Making(item))
            {
                foreach (string i in p.Inputs) if (!r.Contains(i)) r.Add(i);
                if (p.Mold != null && !r.Contains(p.Mold)) r.Add(p.Mold);
            }
            List<Recipe> rs = CraftingManager.GetAllRecipes(item);
            if (rs != null)
                foreach (Recipe rc in rs)
                {
                    if (rc == null || rc.IsScrap || rc.wildcardForgeCategory) continue;
                    foreach (ItemStack st in rc.ingredients)
                        if (st != null && st.itemValue.ItemClass != null && !r.Contains(st.itemValue.ItemClass.GetItemName()))
                            r.Add(st.itemValue.ItemClass.GetItemName());
                }
            return r;
        }
    }

    /// <summary>The Engineer's Manual: use it (left click) to open the Production Guide.</summary>
    [UnityEngine.Scripting.Preserve]
    public class ItemActionFeGuide : ItemAction
    {
        public override void ExecuteAction(ItemActionData _actionData, bool _bReleased)
        {
            if (!_bReleased) return;
            EntityPlayerLocal pl = _actionData == null || _actionData.invData == null ? null : _actionData.invData.holdingEntity as EntityPlayerLocal;
            if (pl != null) FeUi.OpenGuide(pl, null);
        }
    }
}
