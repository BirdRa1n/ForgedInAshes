// D14 trains: what the player sees and touches (TrainSim moves the trains, this draws them).
//
//   Cars: the prefab <kind>Prefab from the mod bundle (feTrainLocoPrefab, feWagonCargoPrefab, feWagonTankPrefab,
//   feWagonPassengerPrefab: made by the 3D models session, PENDENCIAS_ASSETS.md); until they exist, coloured boxes.
//   Their colliders are switched off: trains collide with nothing (user 2026-11-27).
//   Look at a car within 5 m: the prompt shows what it is; E on the locomotive (or a cargo / tank wagon) opens the
//   Train Panel; E on the passenger wagon (or the locomotive while crouching) takes a seat, E again (or jump) leaves.
//   Riding keeps the player at the seat every frame (no fall damage).
//
// Client side, single player / host. C# 5 only.

using System.Collections.Generic;
using System.Text;
using UnityEngine;

namespace ForgedInAshes
{
    public class TrainView : MonoBehaviour
    {
        class CarGo
        {
            public GameObject Go;
            public string Kind;
            public int Seen;
        }

        readonly Dictionary<string, CarGo> cars = new Dictionary<string, CarGo>();
        int frame;
        string prompt;
        bool promptShown;
        public static int RideTrain = -1, RideCar = -1;
        static readonly Dictionary<string, GameObject> prefabs = new Dictionary<string, GameObject>();

        static GameObject Prefab(string kind)
        {
            string name = TrainCar.KitOf(kind) + "Prefab";
            GameObject g;
            if (prefabs.TryGetValue(name, out g)) return g;
            g = null;
            try
            {
                g = DataLoader.LoadAsset<GameObject>("#@modfolder(ForgedInAshes):Resources/forgedinashes.unity3d?" + name, false);
            }
            catch (System.Exception) { g = null; }
            prefabs[name] = g;
            return g;
        }

        static GameObject Make(string kind)
        {
            GameObject p = Prefab(kind);
            GameObject go;
            if (p != null) go = Object.Instantiate(p);
            else
            {
                // placeholder until the model exists: a box of the car's size and colour
                go = new GameObject("FeTrainCar_" + kind);
                GameObject box = GameObject.CreatePrimitive(PrimitiveType.Cube);
                box.transform.SetParent(go.transform, false);
                float L = kind == "loco" ? 8f : kind == "passenger" ? 9f : 7f;
                box.transform.localScale = new Vector3(2.6f, kind == "tank" ? 2.4f : 3f, L);
                box.transform.localPosition = new Vector3(0f, (kind == "tank" ? 2.4f : 3f) * 0.5f + 0.35f, 0f);
                Renderer r = box.GetComponent<Renderer>();
                if (r != null)
                    r.material.color = kind == "loco" ? new Color(0.45f, 0.12f, 0.08f) : kind == "tank" ? new Color(0.15f, 0.18f, 0.22f)
                                     : kind == "passenger" ? new Color(0.12f, 0.3f, 0.18f) : new Color(0.35f, 0.3f, 0.25f);
            }
            foreach (Collider c in go.GetComponentsInChildren<Collider>(true)) c.enabled = false;
            foreach (Rigidbody rb in go.GetComponentsInChildren<Rigidbody>(true)) rb.isKinematic = true;
            return go;
        }

        void LateUpdate()
        {
            GameManager gm = GameManager.Instance;
            World world = gm == null ? null : gm.World;
            EntityPlayerLocal pl = world == null ? null : world.GetPrimaryPlayer();
            if (world == null || pl == null) { Clear(); return; }
            frame++;
            TrainStore.EnsureLoaded();
            Vector3 me = pl.position;
            foreach (Train t in TrainStore.All)
            {
                if (t.Track.Count < 2) continue;
                if ((t.At(t.S) - me).sqrMagnitude > 250f * 250f) continue;
                for (int i = 0; i < t.Cars.Count; i++)
                {
                    string key = t.Id + "/" + i + "/" + t.Cars[i].Kind;
                    CarGo cg;
                    if (!cars.TryGetValue(key, out cg)) { cg = new CarGo { Go = Make(t.Cars[i].Kind), Kind = t.Cars[i].Kind }; cars[key] = cg; }
                    cg.Seen = frame;
                    Vector3 pos;
                    Quaternion rot;
                    t.CarPose(i, out pos, out rot);
                    if (cg.Go != null) cg.Go.transform.SetPositionAndRotation(pos - Origin.position, rot);
                }
            }
            List<string> gone = new List<string>();
            foreach (KeyValuePair<string, CarGo> kv in cars) if (kv.Value.Seen != frame) gone.Add(kv.Key);
            foreach (string k in gone) { if (cars[k].Go != null) Destroy(cars[k].Go); cars.Remove(k); }
            Ride(world, pl);
            Interact(world, pl);
        }

        void Clear()
        {
            foreach (CarGo c in cars.Values) if (c.Go != null) Destroy(c.Go);
            cars.Clear();
            RideTrain = RideCar = -1;
        }

        // ------------------------------------------------------------ aiming at a car
        /// <summary>The car under the crosshair within maxDist (ray against the car boxes).</summary>
        static bool Aim(EntityPlayerLocal pl, float maxDist, out Train train, out int car, out float dist)
        {
            train = null;
            car = -1;
            dist = maxDist;
            Camera cam = pl.playerCamera != null ? pl.playerCamera : Camera.main;
            if (cam == null) return false;
            Vector3 o = cam.transform.position + Origin.position, d = cam.transform.forward;
            foreach (Train t in TrainStore.All)
                for (int i = 0; i < t.Cars.Count; i++)
                {
                    Vector3 pos;
                    Quaternion rot;
                    t.CarPose(i, out pos, out rot);
                    if ((pos - o).sqrMagnitude > (maxDist + 6f) * (maxDist + 6f)) continue;
                    Quaternion inv = Quaternion.Inverse(rot);
                    Vector3 lo = inv * (o - pos), ld = inv * d;
                    Bounds b = new Bounds(new Vector3(0f, 1.8f, 0f), new Vector3(2.8f, 3.6f, t.Cars[i].Length));
                    Ray r = new Ray(lo, ld);
                    float hit;
                    if (b.IntersectRay(r, out hit) && hit < dist) { dist = hit; train = t; car = i; }
                }
            return train != null;
        }

        static string KindName(string kind)
        {
            switch (kind)
            {
                case "loco": return Kinetic.Text("feTrainLoco", "Locomotive");
                case "cargo": return Kinetic.Text("feWagonCargo", "Cargo Wagon");
                case "tank": return Kinetic.Text("feWagonTank", "Tank Wagon");
                case "passenger": return Kinetic.Text("feWagonPassenger", "Passenger Wagon");
            }
            return kind;
        }

        void Interact(World world, EntityPlayerLocal pl)
        {
            LocalPlayerUI ui = LocalPlayerUI.GetUIForPlayer(pl);
            bool free = ui != null && ui.windowManager != null && !ui.windowManager.IsModalWindowOpen();
            PlayerActionsLocal input = pl.playerInput;
            bool press = input != null && input.Activate != null && input.Activate.WasPressed;
            if (RideTrain >= 0)
            {
                SetPrompt(ui, Kinetic.Text("feTrainRiding", "Riding - press {0} or jump to get off").Replace("{0}", "[action:local:Activate]"));
                bool jump = input != null && input.Jump != null && input.Jump.WasPressed;
                if (free && (press || jump)) GetOff(world, pl);
                return;
            }
            Train t;
            int car;
            float dist;
            float block = pl.HitInfo != null && pl.HitInfo.bHitValid ? Mathf.Sqrt(pl.HitInfo.hit.distanceSq) : 99f;
            if (!free || !Aim(pl, 5f, out t, out car, out dist) || dist > block + 0.1f) { SetPrompt(ui, null); return; }
            TrainCar c = t.Cars[car];
            string what = KindName(c.Kind) + " - " + string.Format(Kinetic.Text("feTrainNumber", "train {0}"), t.Id);
            bool crouch = pl.IsCrouching;
            bool seat = c.Kind == "passenger" || (c.Kind == "loco" && crouch);
            string act = seat ? Kinetic.Text("feTrainBoard", "{0} take a seat") : Kinetic.Text("feTrainOpenPanel", "{0} Train Panel");
            SetPrompt(ui, what + "\n" + act.Replace("{0}", "[action:local:Activate]"));
            if (!press) return;
            if (seat) { RideTrain = t.Id; RideCar = car; return; }
            TrainPanel.Open(pl, t.Id);
        }

        void SetPrompt(LocalPlayerUI ui, string text)
        {
            if (ui == null) return;
            if (text == null)
            {
                if (promptShown) { XUiC_InteractionPrompt.SetText(ui, null); promptShown = false; }
                return;
            }
            XUiC_InteractionPrompt.SetText(ui, text);
            promptShown = true;
        }

        // ------------------------------------------------------------ riding
        static Vector3 Seat(Train t, int car)
        {
            Vector3 pos;
            Quaternion rot;
            t.CarPose(Mathf.Clamp(car, 0, t.Cars.Count - 1), out pos, out rot);
            return pos + Vector3.up * 1.0f;
        }

        void Ride(World world, EntityPlayerLocal pl)
        {
            if (RideTrain < 0) return;
            Train t = TrainStore.Get(RideTrain);
            if (t == null || pl.IsDead() || RideCar >= t.Cars.Count) { RideTrain = RideCar = -1; return; }
            Vector3 seat = Seat(t, RideCar);
            pl.SetPosition(seat, false);
            pl.motion = Vector3.zero;
            pl.fallDistance = 0f;
        }

        static void GetOff(World world, EntityPlayerLocal pl)
        {
            Train t = TrainStore.Get(RideTrain);
            if (t != null)
            {
                Vector3 pos;
                Quaternion rot;
                t.CarPose(Mathf.Clamp(RideCar, 0, t.Cars.Count - 1), out pos, out rot);
                pl.SetPosition(pos + rot * Vector3.right * 2.4f + Vector3.up * 0.3f, true);
                pl.fallDistance = 0f;
            }
            RideTrain = RideCar = -1;
        }
    }

    // ------------------------------------------------------------------ Train Panel
    public static class TrainPanel
    {
        public static int TrainId = -1;
        public const int MapSize = 512;

        public static void Open(EntityPlayerLocal pl, int id)
        {
            TrainId = id;
            FeUi.Open(pl, "feTrain");
        }

        public static Train Current { get { return TrainStore.Get(TrainId); } }

        // tiny 3x5 digits for the station numbers on the map
        static readonly string[] Digits = {
            "111101101101111", "010110010010111", "111001111100111", "111001111001111", "101101111001001",
            "111100111001111", "111100111101111", "111001001001001", "111101111101111", "111101111001111" };

        static void Put(Color32[] px, int x, int y, Color32 c)
        {
            if (x < 0 || y < 0 || x >= MapSize || y >= MapSize) return;
            px[y * MapSize + x] = c;
        }

        static void Line(Color32[] px, int x0, int y0, int x1, int y1, Color32 c)
        {
            int dx = Mathf.Abs(x1 - x0), dy = -Mathf.Abs(y1 - y0), sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1, err = dx + dy;
            int guard = 0;
            while (guard++ < 4096)
            {
                Put(px, x0, y0, c);
                Put(px, x0 + 1, y0, c);
                if (x0 == x1 && y0 == y1) break;
                int e2 = 2 * err;
                if (e2 >= dy) { err += dy; x0 += sx; }
                if (e2 <= dx) { err += dx; y0 += sy; }
            }
        }

        static void Number(Color32[] px, int x, int y, int n, Color32 c)
        {
            string s = n.ToString();
            for (int k = 0; k < s.Length; k++)
            {
                string g = Digits[s[k] - '0'];
                for (int r = 0; r < 5; r++)
                    for (int col = 0; col < 3; col++)
                        if (g[r * 3 + col] == '1')
                            for (int a = 0; a < 2; a++) for (int b = 0; b < 2; b++) Put(px, x + k * 8 + col * 2 + a, y - r * 2 - b, c);
            }
        }

        /// <summary>Top-down map: rails (brass), stations (numbered, cyan; those of the route in white), trains (red).</summary>
        public static Texture2D Map(World world, List<Vector3i> stations, Train cur, Texture2D tex)
        {
            if (tex == null) tex = new Texture2D(MapSize, MapSize, TextureFormat.RGBA32, false);
            Color32[] px = new Color32[MapSize * MapSize];
            Color32 bg = new Color32(16, 19, 24, 255);
            for (int i = 0; i < px.Length; i++) px[i] = bg;
            float minX = float.MaxValue, minZ = float.MaxValue, maxX = float.MinValue, maxZ = float.MinValue;
            List<RailEdge> edges = Rails.Edges;
            foreach (RailEdge e in edges)
                foreach (Vector3 p in e.Pts) { minX = Mathf.Min(minX, p.x); maxX = Mathf.Max(maxX, p.x); minZ = Mathf.Min(minZ, p.z); maxZ = Mathf.Max(maxZ, p.z); }
            foreach (Vector3i s in stations) { minX = Mathf.Min(minX, s.x); maxX = Mathf.Max(maxX, s.x); minZ = Mathf.Min(minZ, s.z); maxZ = Mathf.Max(maxZ, s.z); }
            if (minX > maxX) { minX = -10; maxX = 10; minZ = -10; maxZ = 10; }
            float span = Mathf.Max(20f, Mathf.Max(maxX - minX, maxZ - minZ)) * 1.12f;
            float cx = (minX + maxX) * 0.5f, cz = (minZ + maxZ) * 0.5f;
            System.Func<Vector3, Vector2> P = delegate (Vector3 w)
            {
                return new Vector2((w.x - cx) / span * MapSize + MapSize * 0.5f, (w.z - cz) / span * MapSize + MapSize * 0.5f);
            };
            Color32 rail = new Color32(232, 163, 61, 255);
            foreach (RailEdge e in edges)
                for (int i = 1; i < e.Pts.Count; i++)
                {
                    Vector2 a = P(e.Pts[i - 1]), b = P(e.Pts[i]);
                    Line(px, (int)a.x, (int)a.y, (int)b.x, (int)b.y, rail);
                }
            if (cur != null && cur.Track.Count > 1)
            {
                Color32 way = new Color32(76, 195, 217, 255);
                for (int i = 1; i < cur.Track.Count; i++)
                    if (cur.Cum[i] >= cur.S)
                    {
                        Vector2 a = P(cur.Track[i - 1]), b = P(cur.Track[i]);
                        Line(px, (int)a.x, (int)a.y, (int)b.x, (int)b.y, way);
                    }
            }
            for (int k = 0; k < stations.Count; k++)
            {
                Vector2 c = P(stations[k].ToVector3());
                bool inRoute = cur != null && cur.Route.Contains(stations[k]);
                Color32 col = inRoute ? new Color32(255, 255, 255, 255) : new Color32(76, 195, 217, 255);
                for (int a = -4; a <= 4; a++) for (int b = -4; b <= 4; b++) Put(px, (int)c.x + a, (int)c.y + b, col);
                Number(px, (int)c.x + 7, (int)c.y + 12, k + 1, col);
            }
            foreach (Train t in TrainStore.All)
            {
                if (t.Track.Count < 2) continue;
                Vector2 c = P(t.At(t.S));
                Color32 col = t == cur ? new Color32(255, 70, 60, 255) : new Color32(200, 90, 90, 255);
                for (int a = -3; a <= 3; a++) for (int b = -3; b <= 3; b++) Put(px, (int)c.x + a, (int)c.y + b, col);
            }
            tex.SetPixels32(px);
            tex.Apply(false);
            return tex;
        }

        public static string Status(World world, Train t)
        {
            if (t == null) return Kinetic.Text("feTrainGone", "This train is gone.");
            StringBuilder sb = new StringBuilder();
            string st;
            switch (t.State)
            {
                case "moving": st = string.Format(Kinetic.Text("feTrainMoving", "Running to {0} - {1} km/h"), StationName(world, t, t.Leg), Mathf.RoundToInt(t.V * 3.6f)); break;
                case "dwell": st = string.Format(Kinetic.Text("feTrainDwell", "At {0}, leaving in {1} s"), StationName(world, t, t.Leg), Mathf.CeilToInt(t.Wait)); break;
                case "nofuel": st = Kinetic.Text("feTrainNoFuel", "OUT OF FUEL: refuel it here (fuel in hand) or at a station"); break;
                case "noroute": st = t.Route.Count == 0 ? Kinetic.Text("feTrainNoRoute", "No route: add stations below")
                                                       : Kinetic.Text("feTrainNoWay", "No way along the rails to the next station"); break;
                default: st = Kinetic.Text("feTrainStopped", "Stopped"); break;
            }
            sb.Append(st).Append("\n");
            sb.Append(string.Format(Kinetic.Text("feTrainFuelLine", "Fuel {0} / {1} - {2} cars"), Mathf.RoundToInt(t.Fuel), Mathf.RoundToInt(TrainStations.LocoFuelMax), t.Cars.Count));
            int items = 0, stacks = 0, slots = 0;
            float litres = 0f, cap = 0f;
            int seats = 0;
            foreach (TrainCar c in t.Cars)
            {
                if (c.Kind == "cargo") { slots += c.Items.Length; foreach (ItemStack s in c.Items) if (s != null && !s.IsEmpty()) { stacks++; items += s.count; } }
                else if (c.Kind == "tank") { cap += TrainStations.TankLitres; litres += c.Amount; }
                else if (c.Kind == "passenger") seats += 8;
            }
            if (slots > 0) sb.Append("\n").Append(string.Format(Kinetic.Text("feTrainCargo", "Cargo: {0} items in {1} / {2} slots"), items, stacks, slots));
            if (cap > 0f) sb.Append("\n").Append(string.Format(Kinetic.Text("feTrainLiquid", "Tanks: {0} / {1} L"), Mathf.RoundToInt(litres), Mathf.RoundToInt(cap)));
            if (seats > 0) sb.Append("\n").Append(string.Format(Kinetic.Text("feTrainSeats", "Passenger seats: {0}"), seats));
            return sb.ToString();
        }

        static string StationName(World world, Train t, int leg)
        {
            if (leg < 0 || leg >= t.Route.Count) return "?";
            return TrainStations.Name(world, t.Route[leg]);
        }

        public static void Refuel(EntityPlayerLocal pl, Train t)
        {
            ItemStack held = pl.inventory.holdingItemStack;
            if (held == null || held.IsEmpty()) return;
            float per = TrainStations.FuelValue(held.itemValue.ItemClass);
            if (per <= 0f) { GameManager.ShowTooltip(pl, Kinetic.Text("feStationFuelHint", "Hold Coal, Gas Cans or Fuel Gas Canisters (no wood, charcoal or biofuel)")); return; }
            int n = Mathf.Min(held.count, Mathf.FloorToInt((TrainStations.LocoFuelMax - t.Fuel) / per));
            if (n <= 0) return;
            t.Fuel += n * per;
            pl.inventory.DecHoldingItem(n);
            if (t.State == "nofuel") t.State = "stopped";
            TrainStore.Dirty = true;
        }
    }

    [UnityEngine.Scripting.Preserve]
    public class XUiC_FeTrain : XUiC_FeBase
    {
        const int Rows = 9, RouteRows = 6;
        int page;
        List<Vector3i> stations = new List<Vector3i>();
        Texture2D tex;
        XUiV_Texture view;

        public override void Init()
        {
            base.Init();
            for (int i = 0; i < Rows; i++)
            {
                int k = i;
                Hook("feTSt" + i, (s, m) => { AddStation(page * Rows + k); });
            }
            for (int i = 0; i < RouteRows; i++)
            {
                int k = i;
                Hook("feTRt" + i, (s, m) => { RemoveLeg(k); });
            }
            Hook("feTRun", (s, m) => { Train t = TrainPanel.Current; if (t != null) { t.Run = !t.Run; TrainStore.Dirty = true; } Refresh(); });
            Hook("feTClear", (s, m) => { Train t = TrainPanel.Current; if (t != null) { t.Route.Clear(); t.Leg = 0; TrainStore.Dirty = true; } Refresh(); });
            Hook("feTFuel", (s, m) => { Train t = TrainPanel.Current; if (t != null && FeUi.Player != null) TrainPanel.Refuel(FeUi.Player, t); Refresh(); });
            Hook("feTPrev", (s, m) => { if (page > 0) page--; Refresh(); });
            Hook("feTNext", (s, m) => { if ((page + 1) * Rows < stations.Count) page++; Refresh(); });
            Hook("feTPick", (s, m) =>
            {
                Train t = TrainPanel.Current;
                World w = GameManager.Instance == null ? null : GameManager.Instance.World;
                if (t != null && w != null) TrainSim.PickUp(w, t, FeUi.Player);
                Close();
            });
            Hook("feTClose", (s, m) => Close());
            XUiController map = GetChildById("feTMap");
            view = map == null ? null : map.ViewComponent as XUiV_Texture;
        }

        void AddStation(int idx)
        {
            Train t = TrainPanel.Current;
            if (t == null || idx < 0 || idx >= stations.Count || t.Route.Count >= 12) return;
            t.Route.Add(stations[idx]);
            TrainStore.Dirty = true;
            Refresh();
        }

        void RemoveLeg(int k)
        {
            Train t = TrainPanel.Current;
            if (t == null || k >= t.Route.Count) return;
            t.Route.RemoveAt(k);
            if (t.Leg >= t.Route.Count) t.Leg = 0;
            TrainStore.Dirty = true;
            Refresh();
        }

        void Refresh()
        {
            World w = GameManager.Instance == null ? null : GameManager.Instance.World;
            if (w == null) return;
            stations = TrainStations.All();
            if (view != null)
            {
                tex = TrainPanel.Map(w, stations, TrainPanel.Current, tex);
                view.Texture = tex;
            }
            RefreshBindings();
        }

        public override void OnOpen() { base.OnOpen(); page = 0; Refresh(); }
        protected override void Tick() { Refresh(); }

        protected override bool Binding(ref string _value, string _bindingName)
        {
            World w = GameManager.Instance == null ? null : GameManager.Instance.World;
            Train t = TrainPanel.Current;
            switch (_bindingName)
            {
                case "fetitle":
                    _value = t == null ? Kinetic.Text("feTrainPanel", "Train Panel") : string.Format(Kinetic.Text("feTrainPanelN", "Train Panel - train {0}"), t.Id);
                    return true;
                case "febody": _value = TrainPanel.Status(w, t); return true;
                case "ferun": _value = t != null && t.Run ? Kinetic.Text("feTrainBtnStop", "Stop") : Kinetic.Text("feTrainBtnRun", "Run"); return true;
                case "fepage": _value = (page + 1) + " / " + Mathf.Max(1, (stations.Count + Rows - 1) / Rows); return true;
            }
            // station rows: fest<i> text, fesv<i> visible; route rows: fert<i>, ferv<i> (the 'v' at index 3 marks the
            // visibility bindings for XUiC_FeBase while no world is loaded)
            if (_bindingName.Length > 4 && (_bindingName.StartsWith("fest", System.StringComparison.Ordinal) || _bindingName.StartsWith("fesv", System.StringComparison.Ordinal)))
            {
                bool vis = _bindingName[3] == 'v';
                int i;
                if (!int.TryParse(_bindingName.Substring(4), out i)) return false;
                int idx = page * Rows + i;
                if (vis) { _value = idx < stations.Count ? "true" : "false"; return true; }
                _value = idx < stations.Count && w != null ? (idx + 1) + ". " + TrainStations.Name(w, stations[idx]) : "";
                return true;
            }
            if (_bindingName.Length > 4 && (_bindingName.StartsWith("fert", System.StringComparison.Ordinal) || _bindingName.StartsWith("ferv", System.StringComparison.Ordinal)))
            {
                bool vis = _bindingName[3] == 'v';
                int i;
                if (!int.TryParse(_bindingName.Substring(4), out i)) return false;
                bool has = t != null && i < t.Route.Count;
                if (vis) { _value = has ? "true" : "false"; return true; }
                if (!has || w == null) { _value = ""; return true; }
                int num = stations.IndexOf(t.Route[i]) + 1;
                _value = (t.Leg == i ? "> " : "") + (i + 1) + ". " + TrainStations.Name(w, t.Route[i]) + (num > 0 ? "  (#" + num + ")" : "") + "   [x]";
                return true;
            }
            return false;
        }
    }
}
