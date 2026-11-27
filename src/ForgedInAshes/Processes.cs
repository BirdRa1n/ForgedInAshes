// F8.0 (PLANO_CRAFT.md, D11): the chain craft processes, read from <mod>/Data/fe_processes.xml at start-up.
// Each machine of the chain (Caster, Crusher, in-line stations... from F8.1 on) asks Processes.For(machine) what it can
// do. Entries marked planned="true" are designs only and are skipped here. tools/check_processes.py checks the file.
//
// D12 (PLANO_CADEIA.md, 2026-11-24): a process may take up to two fluids (fluid_in="a,b" liters="x,y"), give several
// fluids (fluid_out="a,b" out_liters="x,y"), a by-product (extra / extra_count / chance), ask a minimum gas pressure on
// its fluid inputs (pressure, bar) and heat from a burner next to it (heat="true"). <fluid> entries declare the fluids
// (class liquid | gas | molten, the item they bottle into and its litres, the readout name).
//
// C# 5 only.

using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Xml;

namespace ForgedInAshes
{
    public class Process
    {
        public string Id, Kind, Machine, Mold, FluidIn, FluidOut, Text;
        public string[] Inputs = new string[0];
        public int[] Counts = new int[0];
        public string Output;
        public int OutCount = 1;
        public float Liters, OutLiters, Time, Torque;
        // D12
        public string[] FluidIns = new string[0];
        public float[] LitersIn = new float[0];
        public string[] FluidOuts = new string[0];
        public float[] LitersOut = new float[0];
        public string Extra;
        public int ExtraCount = 1;
        public float Chance = 1f;
        public float Pressure;
        public bool Heat;
        // 2026-11-27 (machine farming): inputs that are NOT used up (keep="plantedCorn1": the seed stays planted) and
        // an optional booster item (boost="feFertilizer" boost_speed="2.5"): with one in the stock the run goes
        // boost_speed times faster and uses one booster
        public string[] Keep = new string[0];
        public string Boost;
        public float BoostSpeed = 1f;
    }

    public class FluidDef
    {
        public string Name, Text, Class = "liquid", Item;
        public float Per;
    }

    public static class Processes
    {
        static readonly Dictionary<string, List<Process>> byMachine = new Dictionary<string, List<Process>>();
        static readonly List<Process> none = new List<Process>();
        public static readonly List<Process> All = new List<Process>();
        public static readonly Dictionary<string, FluidDef> FluidDefs = new Dictionary<string, FluidDef>();
        public static readonly Dictionary<string, string> MachineText = new Dictionary<string, string>();

        public static List<Process> For(string machine)
        {
            List<Process> l;
            return byMachine.TryGetValue(machine, out l) ? l : none;
        }

        static float F(XmlElement e, string a)
        {
            float v;
            return float.TryParse(e.GetAttribute(a), NumberStyles.Float, CultureInfo.InvariantCulture, out v) ? v : 0f;
        }

        static string S(XmlElement e, string a)
        {
            string v = e.GetAttribute(a);
            return string.IsNullOrEmpty(v) ? null : v;
        }

        static float[] Floats(string s, int n)
        {
            float[] r = new float[n];
            string[] t = (s ?? "").Split(',');
            for (int i = 0; i < n; i++)
            {
                float v;
                r[i] = i < t.Length && float.TryParse(t[i], NumberStyles.Float, CultureInfo.InvariantCulture, out v) ? v : 0f;
            }
            return r;
        }

        public static void Load(string modPath)
        {
            byMachine.Clear();
            All.Clear();
            FluidDefs.Clear();
            MachineText.Clear();
            string f = Path.Combine(Path.Combine(modPath, "Data"), "fe_processes.xml");
            if (!File.Exists(f)) { Log.Warning(ForgedInAshesMod.LogPrefix + "processes: " + f + " not found"); return; }
            int active = 0, planned = 0;
            try
            {
                XmlDocument doc = new XmlDocument();
                doc.Load(f);
                foreach (XmlNode n in doc.DocumentElement.GetElementsByTagName("fluid"))
                {
                    XmlElement e = n as XmlElement;
                    if (e == null || S(e, "name") == null) continue;
                    FluidDef d = new FluidDef();
                    d.Name = S(e, "name");
                    d.Text = S(e, "text") ?? d.Name;
                    d.Class = S(e, "class") ?? (d.Name.StartsWith("molten_") ? "molten" : "liquid");
                    d.Item = S(e, "item");
                    d.Per = F(e, "per");
                    FluidDefs[d.Name] = d;
                }
                foreach (XmlNode n in doc.DocumentElement.GetElementsByTagName("machine"))
                {
                    XmlElement e = n as XmlElement;
                    if (e != null && S(e, "name") != null) MachineText[S(e, "name")] = S(e, "text") ?? S(e, "name");
                }
                foreach (XmlNode n in doc.DocumentElement.GetElementsByTagName("process"))
                {
                    XmlElement e = n as XmlElement;
                    if (e == null) continue;
                    if (e.GetAttribute("planned") == "true") { planned++; continue; }
                    Process p = new Process();
                    p.Id = S(e, "id");
                    p.Kind = S(e, "kind");
                    p.Machine = S(e, "machine");
                    p.Mold = S(e, "mold");
                    p.Text = S(e, "text");
                    p.Output = S(e, "output");
                    p.Time = F(e, "time");
                    p.Torque = F(e, "torque");
                    p.Pressure = F(e, "pressure");
                    p.Heat = e.GetAttribute("heat") == "true";
                    p.Extra = S(e, "extra");
                    if (S(e, "extra_count") != null) p.ExtraCount = (int)F(e, "extra_count");
                    if (S(e, "chance") != null) p.Chance = F(e, "chance");
                    if (S(e, "keep") != null) p.Keep = S(e, "keep").Split(',');
                    p.Boost = S(e, "boost");
                    if (S(e, "boost_speed") != null) p.BoostSpeed = F(e, "boost_speed");
                    if (S(e, "out_count") != null) p.OutCount = (int)F(e, "out_count");
                    if (S(e, "fluid_in") != null)
                    {
                        p.FluidIns = e.GetAttribute("fluid_in").Split(',');
                        p.LitersIn = Floats(S(e, "liters"), p.FluidIns.Length);
                        p.FluidIn = p.FluidIns[0];
                        p.Liters = p.LitersIn[0];
                    }
                    if (S(e, "fluid_out") != null)
                    {
                        p.FluidOuts = e.GetAttribute("fluid_out").Split(',');
                        p.LitersOut = Floats(S(e, "out_liters"), p.FluidOuts.Length);
                        p.FluidOut = p.FluidOuts[0];
                        p.OutLiters = p.LitersOut[0];
                    }
                    if (S(e, "input") != null)
                    {
                        p.Inputs = e.GetAttribute("input").Split(',');
                        string[] c = (S(e, "count") ?? "").Split(',');
                        p.Counts = new int[p.Inputs.Length];
                        for (int i = 0; i < p.Inputs.Length; i++)
                        {
                            int k;
                            p.Counts[i] = i < c.Length && int.TryParse(c[i], out k) ? k : 1;
                        }
                    }
                    if (p.Machine == null) continue;
                    List<Process> l;
                    if (!byMachine.TryGetValue(p.Machine, out l)) { l = new List<Process>(); byMachine[p.Machine] = l; }
                    l.Add(p);
                    All.Add(p);
                    active++;
                }
            }
            catch (System.Exception ex)
            {
                Log.Warning(ForgedInAshesMod.LogPrefix + "processes: could not read " + f + ": " + ex.Message);
                return;
            }
            Log.Out(ForgedInAshesMod.LogPrefix + "processes: " + active + " active, " + planned + " planned, " + FluidDefs.Count + " fluids");
        }

        /// <summary>The processes that make this item (output or by-product).</summary>
        public static List<Process> Making(string item)
        {
            List<Process> r = new List<Process>();
            foreach (Process p in All)
                if (p.Output == item || p.Extra == item) r.Add(p);
            return r;
        }

        /// <summary>The processes that give this fluid.</summary>
        public static List<Process> MakingFluid(string fluid)
        {
            List<Process> r = new List<Process>();
            foreach (Process p in All)
                if (System.Array.IndexOf(p.FluidOuts, fluid) >= 0) r.Add(p);
            return r;
        }

        public static string MachineName(string machine)
        {
            Block b = Block.GetBlockByName(machine, false);
            if (b != null) return b.GetLocalizedBlockName();
            string t;
            return MachineText.TryGetValue(machine, out t) ? t : machine;
        }
    }
}
