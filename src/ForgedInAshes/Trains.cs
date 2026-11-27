// D14 (user 2026-11-27): trains. A train is a locomotive and its wagons running on the rails of Rails.cs along a route
// of stations; it drives itself. Trains never collide (with each other or with anything): no block signalling.
//
//   Locomotive kit (feTrainLoco): placed within 4 m of a rail it becomes a new train there (the block goes away),
//     facing the way the kit faced. Burns train fuel: Coal, Gas Cans or Fuel Gas Canisters (no wood, charcoal or
//     biofuel), FeTrainFuel units each.
//   Wagon kits (feWagonCargo items, feWagonTank liquids, feWagonPassenger people): placed within 10 m of a train they
//     are coupled at its end.
//   Train Station (feTrainStation, a big storage with a writable label = its name): stands beside the rails; trains
//     stop at the rail point nearest to it. Belts / arms / funnels fill or empty it like a crate; pipes on its outer
//     sides fill or empty its tank. Its own fuel store (hand, or fuel items arriving by belt while not full) refuels
//     trains. Mode Load: trains take its items / fluid (as much as the wagons hold). Mode Unload: trains leave theirs.
//   Train Panel (look at the locomotive, E): map of the rails and stations, the route (stations in order), run / stop,
//     fuel, cargo; pick the train up again.
//
// Movement: the train keeps a polyline of rails (its Track): the rails behind it (where its wagons are) and the way
// planned to the next station; it moves its head along it. At a station it waits Dwell seconds (loading, unloading,
// refuelling), plans the way to the next station of its route (turning back there if that way is shorter: the order of
// its cars is reversed, the locomotive pushes) and goes. State in <save>/ForgedInAshes_trains.txt.
//
// Server / host (single player for now). C# 5 only.

using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEngine;

namespace ForgedInAshes
{
    public class TrainCar
    {
        public string Kind;                 // loco, cargo, tank, passenger
        public ItemStack[] Items = new ItemStack[0];
        public string Fluid = "";
        public float Amount;

        public float Length { get { return Kind == "loco" ? 8f : Kind == "passenger" ? 9f : 7f; } }

        public static string KitOf(string kind)
        {
            switch (kind)
            {
                case "loco": return "feTrainLoco";
                case "cargo": return "feWagonCargo";
                case "tank": return "feWagonTank";
                case "passenger": return "feWagonPassenger";
            }
            return "";
        }

        public static string KindOfKit(string block)
        {
            switch (block)
            {
                case "feTrainLoco": return "loco";
                case "feWagonCargo": return "cargo";
                case "feWagonTank": return "tank";
                case "feWagonPassenger": return "passenger";
            }
            return "";
        }
    }

    public class Train
    {
        public int Id;
        public List<TrainCar> Cars = new List<TrainCar>();
        public List<Vector3i> Route = new List<Vector3i>();
        public int Leg;                     // index in Route of the station it goes to / stands at
        public bool Run;
        public float Fuel;
        public string State = "stopped";    // stopped, moving, dwell, noroute, nofuel
        public float Wait;
        public float V;                     // m/s
        public float S;                     // head position along Track
        public List<Vector3> Track = new List<Vector3>();
        public List<float> Cum = new List<float>();
        public Vector3i AtStation = new Vector3i(0, int.MinValue, 0);

        public const float Gap = 0.8f;

        public float Length
        {
            get
            {
                float l = 0f;
                foreach (TrainCar c in Cars) l += c.Length + Gap;
                return Mathf.Max(0f, l - Gap);
            }
        }

        public TrainCar Loco
        {
            get { foreach (TrainCar c in Cars) if (c.Kind == "loco") return c; return null; }
        }

        public void Recum()
        {
            Cum.Clear();
            float d = 0f;
            for (int i = 0; i < Track.Count; i++)
            {
                if (i > 0) d += Vector3.Distance(Track[i - 1], Track[i]);
                Cum.Add(d);
            }
        }

        public float TrackLength { get { return Cum.Count == 0 ? 0f : Cum[Cum.Count - 1]; } }

        public Vector3 At(float s)
        {
            if (Track.Count == 0) return Vector3.zero;
            if (s <= 0f || Track.Count == 1) return Track[0];
            if (s >= TrackLength) return Track[Track.Count - 1];
            int i = Cum.BinarySearch(s);
            if (i >= 0) return Track[i];
            i = ~i;
            float t = (s - Cum[i - 1]) / Mathf.Max(0.0001f, Cum[i] - Cum[i - 1]);
            return Vector3.Lerp(Track[i - 1], Track[i], t);
        }

        /// <summary>Centre and facing of car i (0 = the head car) on the track.</summary>
        public void CarPose(int i, out Vector3 pos, out Quaternion rot)
        {
            float off = 0f;
            for (int k = 0; k < i; k++) off += Cars[k].Length + Gap;
            float L = Cars[i].Length;
            Vector3 front = At(S - off - 0.15f * L), back = At(S - off - 0.85f * L);
            pos = (front + back) * 0.5f;
            Vector3 f = front - back;
            rot = f.sqrMagnitude > 0.0001f ? Quaternion.LookRotation(f.normalized, Vector3.up) : Quaternion.identity;
        }

        /// <summary>Keep the track short: forget the rails well behind the last car.</summary>
        public void Trim()
        {
            float keep = S - Length - 30f;
            if (keep < 200f) return;
            int cut = 0;
            while (cut < Cum.Count - 2 && Cum[cut + 1] < keep) cut++;
            if (cut <= 0) return;
            float shift = Cum[cut];
            Track.RemoveRange(0, cut);
            S -= shift;
            Recum();
        }
    }

    public static class TrainStore
    {
        public static readonly List<Train> All = new List<Train>();
        static string loadedFor;
        public static bool Dirty;

        static string FilePath() { return ForgedInAshesMod.SaveFile("trains"); }

        public static Train Get(int id)
        {
            foreach (Train t in All) if (t.Id == id) return t;
            return null;
        }

        public static int NextId()
        {
            int m = 0;
            foreach (Train t in All) m = Mathf.Max(m, t.Id);
            return m + 1;
        }

        static string F(float v) { return v.ToString("0.###", CultureInfo.InvariantCulture); }

        static float PF(string s)
        {
            float v;
            return float.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out v) ? v : 0f;
        }

        static string Items(ItemStack[] a)
        {
            StringBuilder sb = new StringBuilder();
            foreach (ItemStack s in a)
            {
                if (s == null || s.IsEmpty() || s.itemValue.ItemClass == null) continue;
                if (sb.Length > 0) sb.Append(',');
                sb.Append(s.itemValue.ItemClass.GetItemName()).Append(':').Append(s.count);
            }
            return sb.ToString();
        }

        static ItemStack[] ParseItems(string v, int slots)
        {
            ItemStack[] a = new ItemStack[slots];
            for (int i = 0; i < slots; i++) a[i] = ItemStack.Empty.Clone();
            int k = 0;
            foreach (string part in v.Split(','))
            {
                int c = part.LastIndexOf(':');
                int n;
                if (c <= 0 || !int.TryParse(part.Substring(c + 1), out n) || k >= slots) continue;
                ItemValue iv = ItemClass.GetItem(part.Substring(0, c), false);
                if (iv == null || iv.IsEmpty()) continue;
                a[k++] = new ItemStack(iv, n);
            }
            return a;
        }

        public static void EnsureLoaded()
        {
            string f = FilePath();
            if (f == null || f == loadedFor) return;
            loadedFor = f;
            All.Clear();
            if (!File.Exists(f)) return;
            Train t = null;
            foreach (string raw in File.ReadAllLines(f))
            {
                string line = raw.Trim();
                if (line.Length == 0) continue;
                int sp = line.IndexOf(' ');
                string key = sp < 0 ? line : line.Substring(0, sp);
                string val = sp < 0 ? "" : line.Substring(sp + 1);
                try
                {
                    switch (key)
                    {
                        case "train":
                            t = new Train();
                            int.TryParse(val, out t.Id);
                            All.Add(t);
                            break;
                        case "state":
                            {
                                string[] a = val.Split(';');
                                t.Run = a[0] == "1";
                                int.TryParse(a[1], out t.Leg);
                                t.Fuel = PF(a[2]);
                                t.State = a[3];
                                t.S = PF(a[4]);
                                t.Wait = PF(a[5]);
                                break;
                            }
                        case "route":
                            foreach (string r in val.Split(';'))
                            {
                                string[] c = r.Split(',');
                                if (c.Length == 3) t.Route.Add(new Vector3i(int.Parse(c[0]), int.Parse(c[1]), int.Parse(c[2])));
                            }
                            break;
                        case "car":
                            {
                                string[] a = val.Split(';');
                                TrainCar car = new TrainCar { Kind = a[0], Fluid = a.Length > 1 ? a[1] : "", Amount = a.Length > 2 ? PF(a[2]) : 0f };
                                car.Items = ParseItems(a.Length > 3 ? a[3] : "", TrainStations.Slots(car.Kind));
                                t.Cars.Add(car);
                                break;
                            }
                        case "track":
                            foreach (string pnt in val.Split(';'))
                            {
                                string[] c = pnt.Split(',');
                                if (c.Length == 3) t.Track.Add(new Vector3(PF(c[0]), PF(c[1]), PF(c[2])));
                            }
                            t.Recum();
                            break;
                    }
                }
                catch (System.Exception e)
                {
                    Log.Warning(ForgedInAshesMod.LogPrefix + "trains: bad line '" + line + "': " + e.Message);
                }
            }
            foreach (Train x in All) if (x.State == "moving" || x.State == "dwell") x.State = x.Run ? "noroute" : "stopped";
        }

        public static void Save()
        {
            string f = FilePath();
            if (f == null) return;
            StringBuilder sb = new StringBuilder();
            foreach (Train t in All)
            {
                t.Trim();
                sb.Append("train ").Append(t.Id).Append('\n');
                sb.Append("state ").Append(t.Run ? "1" : "0").Append(';').Append(t.Leg).Append(';').Append(F(t.Fuel)).Append(';')
                  .Append(t.State).Append(';').Append(F(t.S)).Append(';').Append(F(t.Wait)).Append('\n');
                sb.Append("route ");
                for (int i = 0; i < t.Route.Count; i++)
                    sb.Append(i > 0 ? ";" : "").Append(t.Route[i].x).Append(',').Append(t.Route[i].y).Append(',').Append(t.Route[i].z);
                sb.Append('\n');
                foreach (TrainCar c in t.Cars)
                    sb.Append("car ").Append(c.Kind).Append(';').Append(c.Fluid).Append(';').Append(F(c.Amount)).Append(';').Append(Items(c.Items)).Append('\n');
                sb.Append("track ");
                for (int i = 0; i < t.Track.Count; i++)
                    sb.Append(i > 0 ? ";" : "").Append(F(t.Track[i].x)).Append(',').Append(F(t.Track[i].y)).Append(',').Append(F(t.Track[i].z));
                sb.Append('\n');
            }
            try { File.WriteAllText(f, sb.ToString()); Dirty = false; }
            catch (System.Exception e) { Log.Warning(ForgedInAshesMod.LogPrefix + "trains: " + e.Message); }
        }
    }

    // ------------------------------------------------------------------ simulation
    public class TrainSim : MonoBehaviour
    {
        static GameObject host;
        float nextSave, nextRetry;

        public const float MaxSpeed = 14f, Accel = 0.8f, Brake = 1.2f, Dwell = 12f;

        public static void Ensure()
        {
            if (host != null) return;
            host = new GameObject("ForgedInAshes.TrainSim");
            Object.DontDestroyOnLoad(host);
            host.AddComponent<TrainSim>();
            host.AddComponent<TrainView>();
        }

        void Update()
        {
            GameManager gm = GameManager.Instance;
            World world = gm == null ? null : gm.World;
            if (world == null || GameIO.GetSaveGameDir() == null) return;
            if (!SingletonMonoBehaviour<ConnectionManager>.Instance.IsServer) return;
            TrainStore.EnsureLoaded();
            float dt = Mathf.Min(Time.deltaTime, 0.1f);
            bool retry = Time.time >= nextRetry;
            if (retry) nextRetry = Time.time + 3f;
            foreach (Train t in TrainStore.All)
            {
                try { Step(world, t, dt, retry); }
                catch (System.Exception e) { Log.Warning(ForgedInAshesMod.LogPrefix + "train " + t.Id + ": " + e.Message); t.State = "noroute"; }
            }
            if (Time.time >= nextSave) { nextSave = Time.time + 30f; TrainStore.Save(); }
        }

        void OnApplicationQuit() { TrainStore.Save(); }

        static float FuelPerMetre(Train t)
        {
            return 0.02f + 0.004f * (t.Cars.Count - 1);   // units per metre (a unit of Coal lasts ~50 m alone)
        }

        static void Step(World world, Train t, float dt, bool retry)
        {
            if (t.Track.Count < 2) { t.State = "noroute"; return; }
            if (!t.Run && t.State != "dwell")
            {
                t.V = Mathf.MoveTowards(t.V, 0f, Brake * 2f * dt);
                if (t.V > 0f) Advance(t, dt);
                if (t.V <= 0f) t.State = "stopped";
                return;
            }
            switch (t.State)
            {
                case "stopped":
                case "noroute":
                case "nofuel":
                    if (!retry) return;
                    if (t.Route.Count == 0) { t.State = "noroute"; return; }
                    if (t.Fuel <= 0f) { t.State = "nofuel"; TryRefuelAtStation(world, t); return; }
                    Plan(world, t);
                    return;
                case "dwell":
                    t.Wait -= dt;
                    if (t.Wait > 0f) return;
                    if (t.Route.Count == 0) { t.State = "stopped"; return; }
                    t.Leg = (t.Leg + 1) % t.Route.Count;
                    Plan(world, t);
                    return;
                case "moving":
                    {
                        float left = t.TrackLength - t.S;
                        if (t.Fuel <= 0f)
                        {
                            t.V = Mathf.MoveTowards(t.V, 0f, Brake * dt);
                            if (t.V <= 0f) { t.State = "nofuel"; return; }
                        }
                        else
                        {
                            float brakeAt = t.V * t.V / (2f * Brake) + 1f;
                            float target = left <= brakeAt ? Mathf.Max(1.2f, Mathf.Sqrt(2f * Brake * Mathf.Max(0f, left - 0.5f))) : MaxSpeed;
                            t.V = t.V < target ? Mathf.Min(target, t.V + Accel * dt) : Mathf.Max(target, t.V - Brake * dt);
                        }
                        float moved = Advance(t, dt);
                        t.Fuel = Mathf.Max(0f, t.Fuel - moved * FuelPerMetre(t));
                        if (t.TrackLength - t.S <= 0.05f) Arrive(world, t);
                        return;
                    }
            }
        }

        static float Advance(Train t, float dt)
        {
            float before = t.S;
            t.S = Mathf.Min(t.TrackLength, t.S + t.V * dt);
            if (t.S >= t.TrackLength) t.V = 0f;
            return t.S - before;
        }

        static void Arrive(World world, Train t)
        {
            t.V = 0f;
            t.State = "dwell";
            t.Wait = Dwell;
            t.AtStation = t.Leg < t.Route.Count ? t.Route[t.Leg] : new Vector3i(0, int.MinValue, 0);
            if (t.Leg < t.Route.Count) TrainStations.Work(world, t, t.Route[t.Leg]);
            TrainStore.Dirty = true;
        }

        static void TryRefuelAtStation(World world, Train t)
        {
            if (t.AtStation.y != int.MinValue) TrainStations.Refuel(world, t, t.AtStation);
        }

        /// <summary>Plan the way from where the head is to the station Route[Leg], turning back if that is shorter.</summary>
        public static void Plan(World world, Train t)
        {
            t.Trim();
            if (t.Route.Count == 0) { t.State = "noroute"; return; }
            if (t.Leg >= t.Route.Count) t.Leg = 0;
            RailPos goal = TrainStations.Stop(world, t.Route[t.Leg]);
            if (goal.Edge == null) { t.State = "noroute"; return; }
            Vector3 head = t.At(t.S), ahead = t.At(t.S + 0.5f), behind = t.At(t.S - 1f);
            Vector3 heading = (t.S + 0.5f <= t.TrackLength ? ahead - head : head - behind);
            if (heading.sqrMagnitude < 0.0001f) heading = head - behind;
            heading.Normalize();
            List<Vector3> fwd = PathFrom(head, heading, goal);
            float len = t.Length;
            Vector3 rear = t.At(t.S - len);
            Vector3 rearHeading = (t.At(t.S - len - 0.5f) - rear);
            if (rearHeading.sqrMagnitude < 0.0001f) rearHeading = -heading;
            List<Vector3> back = PathFrom(rear, rearHeading.normalized, goal);
            float fl = PolyLen(fwd), bl = PolyLen(back) + len;
            if (fwd == null && back == null) { t.State = "noroute"; return; }
            List<Vector3> trail = new List<Vector3>();
            if (fwd != null && (back == null || fl <= bl))
            {
                // keep the rails behind the head (the wagons are on them)
                float from = Mathf.Max(0f, t.S - len - 10f);
                for (int i = 0; i < t.Track.Count; i++) if (t.Cum[i] > from && t.Cum[i] < t.S - 0.01f) trail.Add(t.Track[i]);
                trail.Insert(0, t.At(from));
                trail.Add(head);
                SetTrack(t, trail, fwd);
            }
            else
            {
                // turn back: the last car leads, the order of the cars is reversed (the locomotive pushes)
                float from = Mathf.Max(0f, t.S - len - 1f);
                trail.Add(head);
                for (int i = t.Track.Count - 1; i >= 0; i--) if (t.Cum[i] < t.S - 0.01f && t.Cum[i] > from) trail.Add(t.Track[i]);
                trail.Add(rear);
                t.Cars.Reverse();
                SetTrack(t, trail, back);
            }
            t.State = "moving";
            t.AtStation = new Vector3i(0, int.MinValue, 0);
            TrainStore.Dirty = true;
        }

        static void SetTrack(Train t, List<Vector3> trail, List<Vector3> path)
        {
            List<Vector3> pts = new List<Vector3>(trail);
            float trailLen = PolyLen(trail);
            for (int i = 1; i < path.Count; i++) pts.Add(path[i]);
            t.Track = pts;
            t.Recum();
            t.S = trailLen;
        }

        static List<Vector3> PathFrom(Vector3 p, Vector3 heading, RailPos goal)
        {
            RailPos at = Rails.Locate(p, 2.5f);
            if (at.Edge == null) return null;
            int dir = Vector3.Dot(Rails.Heading(at.Edge, at.S, 1), heading) >= 0f ? 1 : -1;
            return Rails.Path(at, dir, goal);
        }

        public static float PolyLen(List<Vector3> l)
        {
            if (l == null) return float.MaxValue;
            float d = 0f;
            for (int i = 1; i < l.Count; i++) d += Vector3.Distance(l[i - 1], l[i]);
            return d;
        }

        // ------------------------------------------------------------ kits
        /// <summary>A locomotive kit placed near a rail becomes a train there (true when it did).</summary>
        public static bool NewTrain(World world, Vector3 at, Vector3 facing)
        {
            TrainStore.EnsureLoaded();
            RailPos p = Rails.Locate(at, 4f);
            if (p.Edge == null) return false;
            int dir = Vector3.Dot(Rails.Heading(p.Edge, p.S, 1), facing) >= 0f ? 1 : -1;
            Train t = new Train { Id = TrainStore.NextId(), Fuel = 0f };
            t.Cars.Add(new TrainCar { Kind = "loco" });
            // the rails behind the head, for the cars to stand on
            List<Vector3> behind = Rails.Walk(p.Edge, p.S, -dir, 140f);
            behind.Reverse();
            t.Track = behind;
            t.Recum();
            t.S = t.TrackLength;
            TrainStore.All.Add(t);
            TrainStore.Dirty = true;
            TrainStore.Save();
            Log.Out(ForgedInAshesMod.LogPrefix + "train " + t.Id + " placed at " + p.Edge.At(p.S));
            return true;
        }

        /// <summary>A wagon kit placed near a train is coupled at its end (true when it was).</summary>
        public static bool Couple(Vector3 at, string kind)
        {
            TrainStore.EnsureLoaded();
            Train best = null;
            float bd = 10f;
            foreach (Train t in TrainStore.All)
                for (int i = 0; i < t.Cars.Count; i++)
                {
                    Vector3 pos;
                    Quaternion rot;
                    t.CarPose(i, out pos, out rot);
                    float d = Vector3.Distance(pos, at);
                    if (d < bd) { bd = d; best = t; }
                }
            if (best == null || best.Cars.Count >= 13) return false;
            TrainCar c = new TrainCar { Kind = kind };
            c.Items = new ItemStack[TrainStations.Slots(kind)];
            for (int i = 0; i < c.Items.Length; i++) c.Items[i] = ItemStack.Empty.Clone();
            best.Cars.Add(c);
            TrainStore.Dirty = true;
            TrainStore.Save();
            return true;
        }

        /// <summary>Pick a train up: its kits (and cargo items) go to the player, or drop at its feet.</summary>
        public static void PickUp(World world, Train t, EntityPlayerLocal player)
        {
            List<ItemStack> give = new List<ItemStack>();
            foreach (TrainCar c in t.Cars)
            {
                ItemValue kit = ItemClass.GetItem(TrainCar.KitOf(c.Kind), false);
                if (kit != null && !kit.IsEmpty()) give.Add(new ItemStack(kit, 1));
                foreach (ItemStack s in c.Items) if (s != null && !s.IsEmpty()) give.Add(s.Clone());
            }
            foreach (ItemStack s in give)
                if (player == null || !player.inventory.AddItem(s) && !player.bag.AddItem(s))
                    GameManager.Instance.ItemDropServer(s, player != null ? player.position : t.At(t.S), Vector3.zero, -1, 300f, false);
            TrainStore.All.Remove(t);
            TrainStore.Save();
        }
    }

    // ------------------------------------------------------------------ stations
    public static class TrainStations
    {
        public const int CargoSlots = 40;
        public const float TankLitres = 20000f, LocoFuelMax = 1000f, StationFuelMax = 2000f;

        public static int Slots(string kind) { return kind == "cargo" ? CargoSlots : 0; }

        public static bool Is(Block b)
        {
            return b != null && b.Properties != null && b.Properties.Contains("FeTrainStation") && b.Properties.GetBool("FeTrainStation");
        }

        /// <summary>Fuel units of a train fuel item (0 = not train fuel: no wood, charcoal or biofuel).</summary>
        public static float FuelValue(ItemClass ic)
        {
            if (ic == null) return 0f;
            switch (ic.GetItemName())
            {
                case "resourceCoal": return 25f;
                case "ammoGasCan": return 4f;
                case "feGasCanister": return 60f;
            }
            return 0f;
        }

        public static string Name(World world, Vector3i p)
        {
            TileEntityComposite tc = world.GetTileEntity(p) as TileEntityComposite;
            TEFeatureSignable sign = tc == null ? null : tc.GetFeature<TEFeatureSignable>();
            AuthoredText at = sign == null ? null : sign.GetAuthoredText();
            string n = at == null ? "" : (at.Text ?? "").Replace("\n", " ").Trim();
            if (n.Length > 0) { LogicStore.SetField(p, "name", n.Replace("|", "/").Replace("=", "-")); return n; }
            string saved = LogicStore.Field(p, "name");
            return saved.Length > 0 ? saved : string.Format(Kinetic.Text("feStationNoName", "Station {0},{1}"), p.x, p.z);
        }

        public static bool Unloads(Vector3i p) { return LogicStore.Field(p, "mode") == "unload"; }

        public static void ToggleMode(Vector3i p) { LogicStore.SetField(p, "mode", Unloads(p) ? "" : "unload"); }

        public static float FuelStock(Vector3i p)
        {
            float v;
            return float.TryParse(LogicStore.Field(p, "fuel"), NumberStyles.Float, CultureInfo.InvariantCulture, out v) ? v : 0f;
        }

        static void SetFuelStock(Vector3i p, float v)
        {
            LogicStore.SetField(p, "fuel", v <= 0f ? "" : v.ToString("0.##", CultureInfo.InvariantCulture));
        }

        /// <summary>Put train fuel into the station's fuel store; returns how many items it took.</summary>
        public static int AddFuel(Vector3i p, ItemStack st)
        {
            if (st == null || st.IsEmpty()) return 0;
            float per = FuelValue(st.itemValue.ItemClass);
            if (per <= 0f) return 0;
            float room = StationFuelMax - FuelStock(p);
            int n = Mathf.Min(st.count, Mathf.FloorToInt(room / per));
            if (n <= 0) return 0;
            SetFuelStock(p, FuelStock(p) + n * per);
            return n;
        }

        /// <summary>Every station that exists (LogicStore entries marked st=1).</summary>
        public static List<Vector3i> All()
        {
            LogicStore.EnsureLoaded();
            List<Vector3i> l = new List<Vector3i>();
            foreach (KeyValuePair<Vector3i, string> kv in LogicStore.All)
                if (kv.Value.Contains("st=1")) l.Add(kv.Key);
            l.Sort(delegate (Vector3i a, Vector3i b) { return a.x != b.x ? a.x.CompareTo(b.x) : a.z.CompareTo(b.z); });
            return l;
        }

        public static void Register(Vector3i p) { LogicStore.SetField(p, "st", "1"); TrainSim.Ensure(); }

        /// <summary>The rail point where trains stop for the station at p (nearest rail within 12 m of its centre).</summary>
        public static RailPos Stop(World world, Vector3i p)
        {
            return Rails.Locate(new Vector3(p.x + 0.5f, p.y + Rails.RailY, p.z + 0.5f), 12f);
        }

        // ------------------------------------------------------------ fluid ports
        /// <summary>Pipes on any outer side of the bottom layer: they fill its tank (mode Load) or are filled from it
        /// (mode Unload).</summary>
        public static void Ports(World world, Vector3i pos, BlockValue bv, List<FluidPort> l)
        {
            FluidState s = FluidStore.Get(pos);
            bool unload = Unloads(pos);
            foreach (KeyValuePair<Vector3i, Vector3i> f in MultiCells.BottomFaces(bv, pos))
            {
                if (unload) l.Add(new FluidPort { Owner = pos, Cell = f.Key, Dir = f.Value, Out = true, Fluid = s.Fluid });
                else l.Add(new FluidPort { Owner = pos, Cell = f.Key, Dir = f.Value, Out = false, Fluid = s.Fluid,
                                           Accepts = s.Fluid.Length > 0 ? new string[] { s.Fluid } : new string[] { "*" } });
            }
        }

        // ------------------------------------------------------------ work at a stop
        static TEFeatureStorage Storage(World world, Vector3i p, out TileEntityComposite tc)
        {
            tc = world.GetTileEntity(p) as TileEntityComposite;
            return tc == null ? null : tc.GetFeature<TEFeatureStorage>();
        }

        public static void Refuel(World world, Train t, Vector3i p)
        {
            float want = LocoFuelMax - t.Fuel;
            float give = Mathf.Min(want, FuelStock(p));
            if (give <= 0f) return;
            t.Fuel += give;
            SetFuelStock(p, FuelStock(p) - give);
            if (t.State == "nofuel") t.State = "stopped";
        }

        public static void Work(World world, Train t, Vector3i p)
        {
            if (world.GetChunkFromWorldPos(p) == null || !Is(world.GetBlock(p).Block))
            {
                Log.Out(ForgedInAshesMod.LogPrefix + "train " + t.Id + ": station at " + p + " not loaded or gone, nothing exchanged");
                return;
            }
            Refuel(world, t, p);
            TileEntityComposite tc;
            TEFeatureStorage store = Storage(world, p, out tc);
            FluidStore.EnsureLoaded();
            FluidState fs = FluidStore.Get(p);
            float cap = Fluids.Prop(world.GetBlock(p).Block, "FeFluidCapacity", 20000f);
            int moved = 0;
            float litres = 0f;
            bool busy = tc != null && tc.IsUserAccessing();
            foreach (TrainCar c in t.Cars)
            {
                if (c.Kind == "cargo" && store != null && store.ItemGrid != null && !busy)
                {
                    if (Unloads(p)) moved += MoveItems(c.Items, store, false);
                    else moved += MoveItems(c.Items, store, true);
                }
                else if (c.Kind == "tank")
                {
                    if (Unloads(p))
                    {
                        if (c.Amount > 0f && (fs.Amount <= 0.01f || fs.Fluid == c.Fluid))
                        {
                            float n = Mathf.Min(c.Amount, cap - fs.Amount);
                            if (n > 0f) { fs.Amount += n; fs.Fluid = c.Fluid; c.Amount -= n; litres += n; if (c.Amount <= 0.01f) { c.Amount = 0f; c.Fluid = ""; } }
                        }
                    }
                    else if (fs.Amount > 0.01f && (c.Amount <= 0.01f || c.Fluid == fs.Fluid))
                    {
                        float n = Mathf.Min(fs.Amount, TankLitres - c.Amount);
                        if (n > 0f) { c.Amount += n; c.Fluid = fs.Fluid; fs.Amount -= n; litres += n; if (fs.Amount <= 0.01f) { fs.Amount = 0f; fs.Fluid = ""; } }
                    }
                }
            }
            if (tc != null && moved > 0) tc.SetModified();
            FluidStore.MarkDirty();
            Log.Out(ForgedInAshesMod.LogPrefix + "train " + t.Id + " at " + Name(world, p) + (Unloads(p) ? ": unloaded " : ": loaded ")
                    + moved + " items, " + Mathf.RoundToInt(litres) + " L; fuel " + Mathf.RoundToInt(t.Fuel));
        }

        /// <summary>Move items between a wagon and the station grid; toWagon = load. Returns the items moved.</summary>
        static int MoveItems(ItemStack[] wagon, TEFeatureStorage store, bool toWagon)
        {
            ItemStackGrid grid = store.ItemGrid;
            int moved = 0;
            if (toWagon)
            {
                for (int i = 0; i < grid.Length; i++)
                {
                    ItemStack slot = grid[i];
                    if (slot == null || slot.IsEmpty()) continue;
                    ItemStack rest = slot.Clone();
                    int before = rest.count;
                    Put(wagon, rest);
                    if (rest.count == before) continue;
                    moved += before - rest.count;
                    store.UpdateSlot(i, rest.count > 0 ? rest : ItemStack.Empty.Clone());
                }
            }
            else
            {
                for (int w = 0; w < wagon.Length; w++)
                {
                    ItemStack s = wagon[w];
                    if (s == null || s.IsEmpty()) continue;
                    int before = s.count;
                    PutGrid(store, s);
                    moved += before - s.count;
                    if (s.count <= 0) wagon[w] = ItemStack.Empty.Clone();
                }
            }
            return moved;
        }

        static int Max(ItemStack s) { return s.itemValue.ItemClass == null ? 1 : Mathf.Max(1, s.itemValue.ItemClass.Stacknumber.Value); }

        /// <summary>Put st into the slots (stacking first); st.count becomes what did not fit.</summary>
        public static void Put(ItemStack[] slots, ItemStack st)
        {
            int max = Max(st);
            for (int i = 0; i < slots.Length && st.count > 0; i++)
            {
                ItemStack s = slots[i];
                if (s == null || s.IsEmpty() || s.itemValue.type != st.itemValue.type || s.count >= max) continue;
                int n = Mathf.Min(st.count, max - s.count);
                s.count += n;
                st.count -= n;
            }
            for (int i = 0; i < slots.Length && st.count > 0; i++)
            {
                if (slots[i] != null && !slots[i].IsEmpty()) continue;
                int n = Mathf.Min(st.count, max);
                slots[i] = new ItemStack(st.itemValue.Clone(), n);
                st.count -= n;
            }
        }

        static void PutGrid(TEFeatureStorage store, ItemStack st)
        {
            ItemStackGrid grid = store.ItemGrid;
            int max = Max(st);
            for (int i = 0; i < grid.Length && st.count > 0; i++)
            {
                ItemStack s = grid[i];
                if (s == null || s.IsEmpty() || s.itemValue.type != st.itemValue.type || s.count >= max) continue;
                int n = Mathf.Min(st.count, max - s.count);
                ItemStack ns = s.Clone();
                ns.count += n;
                store.UpdateSlot(i, ns);
                st.count -= n;
            }
            for (int i = 0; i < grid.Length && st.count > 0; i++)
            {
                ItemStack s = grid[i];
                if (s != null && !s.IsEmpty()) continue;
                int n = Mathf.Min(st.count, max);
                store.UpdateSlot(i, new ItemStack(st.itemValue.Clone(), n));
                st.count -= n;
            }
        }

        public static string Describe(World world, Vector3i p)
        {
            FluidState fs = FluidStore.Get(p);
            StringBuilder sb = new StringBuilder();
            sb.Append(string.Format(Kinetic.Text("feStationInfo", "Station \"{0}\" - mode: {1}"), Name(world, p),
                Unloads(p) ? Kinetic.Text("feStationUnload", "trains UNLOAD here") : Kinetic.Text("feStationLoad", "trains LOAD here")));
            sb.Append("\n").Append(string.Format(Kinetic.Text("feStationFuel", "Train fuel: {0} / {1}"), Mathf.RoundToInt(FuelStock(p)), Mathf.RoundToInt(StationFuelMax)));
            if (fs.Amount > 0.01f)
                sb.Append(" - ").Append(string.Format(Kinetic.Text("feStationTank", "tank: {0} L of {1}"), Mathf.RoundToInt(fs.Amount), Kinetic.Text("feFluid_" + fs.Fluid, fs.Fluid)));
            if (RailsNear(world, p) == false) sb.Append("\n").Append(Kinetic.Text("feStationNoRail", "No rail within 12 m: trains cannot stop here"));
            return sb.ToString();
        }

        static bool RailsNear(World world, Vector3i p) { return Stop(world, p).Edge != null; }
    }

    /// <summary>The Train Station: a big writable storage (vanilla composite: storage, lock, label = its name).</summary>
    [UnityEngine.Scripting.Preserve]
    public class BlockFeStation : BlockCompositeTileEntity
    {
        public override void Init()
        {
            base.Init();
            TrainSim.Ensure();
        }

        public override void OnBlockAdded(WorldBase _world, Chunk _chunk, Vector3i _blockPos, BlockValue _blockValue, PlatformUserIdentifierAbs _addedByPlayer)
        {
            base.OnBlockAdded(_world, _chunk, _blockPos, _blockValue, _addedByPlayer);
            if (!_blockValue.ischild) TrainStations.Register(_blockPos);
        }

        public override void OnBlockLoaded(WorldBase _world, Vector3i _blockPos, BlockValue _blockValue)
        {
            base.OnBlockLoaded(_world, _blockPos, _blockValue);
            if (!_blockValue.ischild) TrainStations.Register(_blockPos);
        }

        public override void OnBlockRemoved(WorldBase _world, Chunk _chunk, Vector3i _blockPos, BlockValue _blockValue)
        {
            base.OnBlockRemoved(_world, _chunk, _blockPos, _blockValue);
            if (!_blockValue.ischild) LogicStore.Set(_blockPos, null);
        }

        public override BlockActivationCommand[] GetBlockActivationCommands(WorldBase _world, BlockValue _blockValue, Vector3i _blockPos, EntityAlive _entityFocusing)
        {
            BlockActivationCommand[] b = base.GetBlockActivationCommands(_world, _blockValue, _blockPos, _entityFocusing) ?? new BlockActivationCommand[0];
            BlockActivationCommand[] r = new BlockActivationCommand[b.Length + 2];
            b.CopyTo(r, 0);
            r[b.Length] = new BlockActivationCommand("fe_station_fuel", "campfire", true, false, null);
            r[b.Length + 1] = new BlockActivationCommand("fe_station_mode", "loot_sack", true, false, null);
            return r;
        }

        public override bool OnBlockActivated(string _commandName, WorldBase _world, Vector3i _blockPos, BlockValue _blockValue, EntityPlayerLocal _player)
        {
            Vector3i p = Fluids.ParentOf((World)_world, _blockPos, _blockValue);
            if (_commandName == "fe_station_mode") { TrainStations.ToggleMode(p); return true; }
            if (_commandName == "fe_station_fuel")
            {
                ItemStack held = _player.inventory.holdingItemStack;
                int n = TrainStations.AddFuel(p, held == null ? null : held.Clone());
                if (n > 0) _player.inventory.DecHoldingItem(n);
                else GameManager.ShowTooltip(_player, Kinetic.Text("feStationFuelHint", "Hold Coal, Gas Cans or Fuel Gas Canisters (no wood, charcoal or biofuel)"));
                return true;
            }
            return base.OnBlockActivated(_commandName, _world, _blockPos, _blockValue, _player);
        }

        public override string GetActivationText(WorldBase _world, BlockValue _blockValue, Vector3i _blockPos, EntityAlive _entityFocusing)
        {
            string b = base.GetActivationText(_world, _blockValue, _blockPos, _entityFocusing) ?? "";
            World w = (World)_world;
            Vector3i p = Fluids.ParentOf(w, _blockPos, _blockValue);
            return b + "\n" + KineticLookController.Escape(TrainStations.Describe(w, p));
        }
    }

    /// <summary>Locomotive and wagon kits: placed near rails / a train they turn into a train / a coupled wagon.</summary>
    [UnityEngine.Scripting.Preserve]
    public class BlockFeTrainKit : Block
    {
        public override void Init()
        {
            base.Init();
            TrainSim.Ensure();
        }

        public override void OnBlockAdded(WorldBase _world, Chunk _chunk, Vector3i _blockPos, BlockValue _blockValue, PlatformUserIdentifierAbs _addedByPlayer)
        {
            base.OnBlockAdded(_world, _chunk, _blockPos, _blockValue, _addedByPlayer);
            if (_blockValue.ischild || !SingletonMonoBehaviour<ConnectionManager>.Instance.IsServer) return;
            World world = (World)_world;
            string kind = TrainCar.KindOfKit(GetBlockName());
            Vector3 at = _blockPos.ToVector3() + new Vector3(0.5f, 0.2f, 0.5f);
            Vector3 facing = Fluids.Rot(_blockValue, Vector3.forward).ToVector3();
            bool ok = kind == "loco" ? TrainSim.NewTrain(world, at, facing) : TrainSim.Couple(at, kind);
            Vector3i pos = _blockPos;
            string name = GetBlockName();
            // remove the kit block a moment later (not inside the placement)
            GameManager.Instance.StartCoroutine(RemoveLater(world, pos, ok ? null : name));
        }

        static System.Collections.IEnumerator RemoveLater(World world, Vector3i pos, string giveBack)
        {
            yield return null;
            world.SetBlockRPC(pos, BlockValue.Air);
            if (giveBack != null)
            {
                ItemValue iv = ItemClass.GetItem(giveBack, false);
                if (iv != null && !iv.IsEmpty())
                    GameManager.Instance.ItemDropServer(new ItemStack(iv, 1), pos.ToVector3() + new Vector3(0.5f, 0.5f, 0.5f), Vector3.zero, -1, 300f, false);
                EntityPlayerLocal pl = world.GetPrimaryPlayer();
                if (pl != null)
                    GameManager.ShowTooltip(pl, giveBack == "feTrainLoco"
                        ? Kinetic.Text("feTrainNeedRail", "Place the locomotive on (or within 4 m of) a rail")
                        : Kinetic.Text("feWagonNeedTrain", "Place the wagon within 10 m of a train"));
            }
        }
    }
}
