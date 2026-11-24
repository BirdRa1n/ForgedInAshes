// F8.0 (PLANO_CRAFT.md, D11): the chain craft processes, read from <mod>/Data/fe_processes.xml at start-up.
// Each machine of the chain (Caster, Crusher, in-line stations... from F8.1 on) asks Processes.For(machine) what it can
// do. Entries marked planned="true" are designs only and are skipped here. tools/check_processes.py checks the file.
//
// C# 5 only.

using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Xml;

namespace FerroEngrenagem
{
    public class Process
    {
        public string Id, Kind, Machine, Mold, FluidIn, FluidOut, Text;
        public string[] Inputs = new string[0];
        public int[] Counts = new int[0];
        public string Output;
        public int OutCount = 1;
        public float Liters, OutLiters, Time, Torque;
    }

    public static class Processes
    {
        static readonly Dictionary<string, List<Process>> byMachine = new Dictionary<string, List<Process>>();
        static readonly List<Process> none = new List<Process>();

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

        public static void Load(string modPath)
        {
            byMachine.Clear();
            string f = Path.Combine(Path.Combine(modPath, "Data"), "fe_processes.xml");
            if (!File.Exists(f)) { Log.Warning(FerroEngrenagemMod.LogPrefix + "processes: " + f + " not found"); return; }
            int active = 0, planned = 0;
            try
            {
                XmlDocument doc = new XmlDocument();
                doc.Load(f);
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
                    p.FluidIn = S(e, "fluid_in");
                    p.FluidOut = S(e, "fluid_out");
                    p.Text = S(e, "text");
                    p.Output = S(e, "output");
                    p.Liters = F(e, "liters");
                    p.OutLiters = F(e, "out_liters");
                    p.Time = F(e, "time");
                    p.Torque = F(e, "torque");
                    if (S(e, "out_count") != null) p.OutCount = (int)F(e, "out_count");
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
                    active++;
                }
            }
            catch (System.Exception ex)
            {
                Log.Warning(FerroEngrenagemMod.LogPrefix + "processes: could not read " + f + ": " + ex.Message);
                return;
            }
            Log.Out(FerroEngrenagemMod.LogPrefix + "processes: " + active + " active, " + planned + " planned");
        }
    }
}
