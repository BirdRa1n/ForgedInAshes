// D14 trains: what the player sees and touches (TrainSim moves the trains, this draws them).
//
//   Cars: the prefab <kit>CarPrefab from the mod bundle (feTrainLocoCarPrefab, feWagonCargoCarPrefab,
//   feWagonTankCarPrefab, feWagonPassengerCarPrefab: Art/feHD/build_feHD.py; <kit>Prefab is the kit block's crate);
//   without the bundle, coloured boxes. TrainCarVisual animates them: wheels (FeSpin_r<radius>_*) roll with the
//   distance run, the locomotive's rods follow its crank pins, smoke and steam while it runs.
//   Their colliders are switched off: trains collide with no block and no other train (user 2026-11-27). The
//   PLAYER does not pass through them (user 2026-11-27: "make the wagons solid"): Solid() keeps the player out of each
//   car's shape (boxes per kind, SolidBoxes) every frame and lets them stand on the roofs, carried along as the
//   train moves. Done by hand, not with physics colliders: the game's block raycasts and the rails stay untouched.
//   Look at a car within 6 m: the prompt shows what it is. E on the locomotive takes the driver's place in its cab
//   and the camera goes outside (third person, pulled back to show the train): W accelerates, S brakes / reverses,
//   space brakes, A / D pick the branch at the next switches, crouch opens the Train Panel (its Run = autopilot on
//   the route), E gets off. E on the passenger wagon: a seat with the same outside view, E or jump gets off. E on a
//   cargo / tank wagon (or crouch + E on the locomotive) opens the Train Panel (user 2026-11-27: "the game should
//   understand it as a vehicle"; "the passenger only gets the outside view of the wagon").
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
            public Vector3 Pos, LastPos;
            public Quaternion Rot, LastRot;
            public bool HasLast;
            public float Length;
        }

        readonly Dictionary<string, CarGo> cars = new Dictionary<string, CarGo>();
        int frame;
        string prompt;
        bool promptShown;
        public static int RideTrain = -1, RideCar = -1;
        static readonly Dictionary<string, GameObject> prefabs = new Dictionary<string, GameObject>();

        static GameObject Prefab(string kind)
        {
            string name = TrainCar.KitOf(kind) + "CarPrefab";
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
            if (p != null) go.AddComponent<TrainCarVisual>();
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
                    cg.LastPos = cg.Pos;
                    cg.LastRot = cg.Rot;
                    cg.HasLast = cg.Pos != Vector3.zero;
                    cg.Pos = pos;
                    cg.Rot = rot;
                    cg.Length = t.Cars[i].Length;
                    if (cg.Go != null)
                    {
                        cg.Go.transform.SetPositionAndRotation(pos - Origin.position, rot);
                        TrainCarVisual vis = cg.Go.GetComponent<TrainCarVisual>();
                        if (vis != null) vis.Step(pos, rot, t.Run && Mathf.Abs(t.V) > 0.05f, Mathf.Abs(t.V));
                    }
                }
            }
            List<string> gone = new List<string>();
            foreach (KeyValuePair<string, CarGo> kv in cars) if (kv.Value.Seen != frame) gone.Add(kv.Key);
            foreach (string k in gone) { if (cars[k].Go != null) Destroy(cars[k].Go); cars.Remove(k); }
            Ride(world, pl);
            if (RideTrain < 0) Solid(pl);
            Interact(world, pl);
        }

        // ------------------------------------------------------------ the player does not walk through cars
        // Boxes per car kind in car space (x across, y up from the rail top, z forward): min x, max x, bottom, top,
        // min z, max z. They follow the models: the locomotive is low over the boiler and tanks (front) and high at the
        // cab and bunker (back).
        static float[][] SolidBoxes(string kind, float L)
        {
            switch (kind)
            {
                case "loco":
                    return new float[][] { new float[] { -1.3f, 1.3f, 0.1f, 2.85f, -1.30f, 4.0f },
                                           new float[] { -1.3f, 1.3f, 0.1f, 3.52f, -4.0f, -1.30f } };
                case "tank":
                    return new float[][] { new float[] { -1.27f, 1.27f, 0.1f, 3.32f, -L / 2, L / 2 } };
                case "passenger":
                    return new float[][] { new float[] { -1.31f, 1.31f, 0.1f, 3.42f, -L / 2, L / 2 } };
            }
            return new float[][] { new float[] { -1.3f, 1.3f, 0.1f, 3.35f, -L / 2, L / 2 } };
        }

        const float PlayerRadius = 0.35f, PlayerHeight = 1.75f, StepUp = 0.55f;
        string standingOn;

        void Solid(EntityPlayerLocal pl)
        {
            if (pl.IsDead()) { standingOn = null; return; }
            Vector3 p = pl.position;
            bool moved = false, stood = false;
            string onNow = null;
            // standing on a roof last frame: ride along with that car's motion (and turn)
            CarGo carrier;
            if (standingOn != null && cars.TryGetValue(standingOn, out carrier) && carrier.HasLast)
            {
                Vector3 local = Quaternion.Inverse(carrier.LastRot) * (p - carrier.LastPos);
                Vector3 np = carrier.Pos + carrier.Rot * local;
                if ((np - p).sqrMagnitude > 0.000001f) { p = np; moved = true; }
            }
            foreach (KeyValuePair<string, CarGo> kv in cars)
            {
                CarGo c = kv.Value;
                if ((c.Pos - p).sqrMagnitude > (c.Length * 0.5f + 4f) * (c.Length * 0.5f + 4f)) continue;
                Quaternion inv = Quaternion.Inverse(c.Rot);
                foreach (float[] b in SolidBoxes(c.Kind, c.Length))
                {
                    Vector3 l = inv * (p - c.Pos);
                    float x0 = b[0] - PlayerRadius, x1 = b[1] + PlayerRadius, z0 = b[4] - PlayerRadius, z1 = b[5] + PlayerRadius;
                    if (l.x <= x0 || l.x >= x1 || l.z <= z0 || l.z >= z1) continue;          // not over / in the box
                    if (l.y >= b[3] + 0.02f || l.y + PlayerHeight <= b[2]) continue;          // above it or under it
                    if (l.y >= b[3] - StepUp)
                    {
                        l.y = b[3];                                                          // on the roof
                        stood = true;
                        onNow = kv.Key;
                    }
                    else
                    {
                        // push out through the nearest side or end
                        float dl = l.x - x0, dr = x1 - l.x, db = l.z - z0, df = z1 - l.z;
                        float m = Mathf.Min(Mathf.Min(dl, dr), Mathf.Min(db, df));
                        if (m == dl) l.x = x0; else if (m == dr) l.x = x1; else if (m == db) l.z = z0; else l.z = z1;
                    }
                    p = c.Pos + c.Rot * l;
                    moved = true;
                }
            }
            standingOn = onNow;
            if (!moved) return;
            pl.SetPosition(p, false);
            if (stood)
            {
                if (pl.motion.y < 0f) pl.motion = new Vector3(pl.motion.x, 0f, pl.motion.z);
                pl.fallDistance = 0f;
            }
        }

        void Clear()
        {
            foreach (CarGo c in cars.Values) if (c.Go != null) Destroy(c.Go);
            cars.Clear();
            RideTrain = RideCar = -1;
        }

        // ------------------------------------------------------------ aiming at a car
        /// <summary>The car under the crosshair within maxDist (ray against the car boxes).</summary>
        static bool InsideCar(Train t, int i, Vector3 p, float pad)
        {
            Vector3 pos;
            Quaternion rot;
            t.CarPose(i, out pos, out rot);
            Vector3 l = Quaternion.Inverse(rot) * (p - pos);
            return Mathf.Abs(l.x) < 1.4f + pad && l.y > -0.5f - pad && l.y < 3.6f + pad && Mathf.Abs(l.z) < t.Cars[i].Length * 0.5f + pad;
        }

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

        float nextDiag;
        bool activateWas, jumpWas, crouchWas, leftWas, rightWas;

        // ------------------------------------------------------------ outside view while riding
        bool viewSaved, wasFirstPerson;
        Vector3 offset0;

        static Vector3 ViewOffset(string kind)
        {
            // vp_FPCamera.Position3rdPersonOffset: up, back from the rider (the vehicles do the same through
            // EntityVehicle.GetCameraOffset -> EntityPlayerLocal.RefreshDrivingCameraPositions, IL 3.4.0 b10)
            return kind == "loco" ? new Vector3(0f, 1.6f, -9f) : new Vector3(0f, 1.8f, -10f);
        }

        void EnterView(EntityPlayerLocal pl)
        {
            if (viewSaved) return;
            wasFirstPerson = pl.bFirstPersonView;
            vp_FPCamera cam = pl.vp_FPCamera;
            if (cam != null) offset0 = cam.Position3rdPersonOffset;
            viewSaved = true;
            pl.SetFirstPersonView(false, true);
        }

        void KeepView(EntityPlayerLocal pl, string kind)
        {
            vp_FPCamera cam = pl.vp_FPCamera;
            if (cam != null) cam.Position3rdPersonOffset = ViewOffset(kind);
            if (pl.bFirstPersonView) pl.SetFirstPersonView(false, true);
        }

        void LeaveView(EntityPlayerLocal pl)
        {
            if (!viewSaved || pl == null) return;
            viewSaved = false;
            vp_FPCamera cam = pl.vp_FPCamera;
            if (cam != null) cam.Position3rdPersonOffset = offset0;
            pl.SetFirstPersonView(wasFirstPerson, true);
        }

        static string SteerName(int s)
        {
            return s < 0 ? Kinetic.Text("feTrainSteerL", "left") : s > 0 ? Kinetic.Text("feTrainSteerR", "right")
                 : Kinetic.Text("feTrainSteerS", "straight");
        }

        // E is read from BOTH action sets with our own edge detection: the game delivers Activate through
        // PlayerActionsPermanent (the local set's Activate.WasPressed never fired: test 2026-11-27 17:25, no
        // "train use" line at all). Same pattern as Crank.IsActivateHeld.
        static bool ActivateHeld(EntityPlayerLocal pl)
        {
            PlayerActionsLocal input = pl.playerInput;
            if (input == null) return false;
            if (input.Activate != null && input.Activate.IsPressed) return true;
            PlayerActionsPermanent perm = input.PermanentActions;
            return perm != null && perm.Activate != null && perm.Activate.IsPressed;
        }

        static bool JumpHeld(EntityPlayerLocal pl)
        {
            PlayerActionsLocal input = pl.playerInput;
            if (input == null) return false;
            if (input.Jump != null && input.Jump.IsPressed) return true;
            return input.VehicleActions != null && input.VehicleActions.Hop != null && input.VehicleActions.Hop.IsPressed;
        }

        void Interact(World world, EntityPlayerLocal pl)
        {
            LocalPlayerUI ui = LocalPlayerUI.GetUIForPlayer(pl);
            bool free = ui != null && ui.windowManager != null && !ui.windowManager.IsModalWindowOpen();
            PlayerActionsLocal input = pl.playerInput;
            bool held = ActivateHeld(pl), jheld = JumpHeld(pl);
            bool press = held && !activateWas, jumpPress = jheld && !jumpWas;
            activateWas = held;
            jumpWas = jheld;
            if (RideTrain >= 0)
            {
                Train rt = TrainStore.Get(RideTrain);
                bool driver = rt != null && RideCar >= 0 && RideCar < rt.Cars.Count && rt.Cars[RideCar].Kind == "loco";
                bool ch = input != null && input.Crouch != null && input.Crouch.IsPressed;
                bool lh = input != null && input.MoveLeft != null && input.MoveLeft.IsPressed;
                bool rh = input != null && input.MoveRight != null && input.MoveRight.IsPressed;
                bool crouchPress = ch && !crouchWas, leftPress = lh && !leftWas, rightPress = rh && !rightWas;
                crouchWas = ch;
                leftWas = lh;
                rightWas = rh;
                if (press || jumpPress)
                    Log.Out(ForgedInAshesMod.LogPrefix + "train " + RideTrain + ": riding car " + RideCar + ", " + (press ? "E" : "jump")
                            + " pressed, free=" + free);
                if (driver)
                {
                    // the controls go to the train (the rider is held at the seat every frame, so walking does nothing)
                    bool fw = free && input != null && input.MoveForward != null && input.MoveForward.IsPressed;
                    bool bk = free && input != null && input.MoveBack != null && input.MoveBack.IsPressed;
                    rt.Throttle = fw ? 1f : bk ? -1f : 0f;
                    rt.Brake = free && jheld;
                    if (free && (fw || bk) && !rt.Manual)
                    {
                        rt.Manual = true;                                            // the driver takes over
                        rt.Run = false;
                        TrainStore.Dirty = true;
                    }
                    if (free && leftPress) rt.Steer = rt.Steer > 0 ? 0 : -1;
                    if (free && rightPress) rt.Steer = rt.Steer < 0 ? 0 : 1;
                    string txt = Kinetic.Text("feTrainDriving",
                        "Driving {2} km/h - W accelerate, S brake / reverse, space brake, A/D next switch: {1}, crouch: Train Panel, {0} get off")
                        .Replace("{0}", "[action:local:Activate]").Replace("{1}", SteerName(rt.Steer))
                        .Replace("{2}", Mathf.RoundToInt(rt.V * 3.6f).ToString());
                    if (rt.Run) txt += "\n" + Kinetic.Text("feTrainAutopilot", "Autopilot on the route (W or S takes over)");
                    if (rt.Fuel <= 0f) txt += "\n" + Kinetic.Text("feTrainNoFuel", "No fuel");
                    SetPrompt(ui, txt);
                    if (free && crouchPress) { TrainPanel.Open(pl, RideTrain); return; }
                    if (free && press) GetOff(world, pl);
                    return;
                }
                SetPrompt(ui, Kinetic.Text("feTrainRiding", "Riding - press {0} or jump to get off").Replace("{0}", "[action:local:Activate]"));
                if (free && (press || jumpPress)) GetOff(world, pl);
                return;
            }
            Train t = null;
            int car = -1;
            float dist = 99f;
            bool aimed = free && Aim(pl, 6f, out t, out car, out dist);
            float block = 99f;
            if (aimed && pl.HitInfo != null && pl.HitInfo.bHitValid)
            {
                // a block in front of the car hides it; one inside the car's box (the rail, the ground under the
                // wheels, the kit's spot) does not
                Vector3 hp = pl.HitInfo.hit.pos;
                if (!InsideCar(t, car, hp, 0.3f)) block = Mathf.Sqrt(pl.HitInfo.hit.distanceSq);
            }
            if (press && Time.time >= nextDiag)
            {
                nextDiag = Time.time + 0.5f;
                Log.Out(ForgedInAshesMod.LogPrefix + "train use: aimed=" + aimed + (aimed ? " train " + t.Id + " car " + car + " (" + t.Cars[car].Kind
                        + ") dist " + dist.ToString("0.00") : "") + " block " + (block > 90f ? "none" : block.ToString("0.00")) + " free=" + free
                        + " trains=" + TrainStore.All.Count);
            }
            if (!aimed || dist > block + 0.1f) { SetPrompt(ui, null); return; }
            TrainCar c = t.Cars[car];
            string what = KindName(c.Kind) + " - " + string.Format(Kinetic.Text("feTrainNumber", "train {0}"), t.Id);
            bool crouch = pl.IsCrouching;
            bool seat = c.Kind == "passenger" || (c.Kind == "loco" && !crouch);
            string act = c.Kind == "loco" && seat ? Kinetic.Text("feTrainCab", "{0} get into the cab (crouch: Train Panel)")
                       : seat ? Kinetic.Text("feTrainBoard", "{0} take a seat") : Kinetic.Text("feTrainOpenPanel", "{0} Train Panel");
            SetPrompt(ui, what + "\n" + act.Replace("{0}", "[action:local:Activate]"));
            if (!press) return;
            if (seat)
            {
                RideTrain = t.Id;
                RideCar = car;
                crouchWas = leftWas = rightWas = true;                             // no stale presses on the way in
                jumpWas = true;
                EnterView(pl);
                Log.Out(ForgedInAshesMod.LogPrefix + "train " + t.Id + ": player boards car " + car + " (" + c.Kind + ")");
                return;
            }
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
            car = Mathf.Clamp(car, 0, t.Cars.Count - 1);
            t.CarPose(car, out pos, out rot);
            // feTrainLocoCar: cab floor 1.45 m, 2.2 m behind the middle; feWagonPassengerCar: floor 1.0 m, middle
            Vector3 local = t.Cars[car].Kind == "loco" ? new Vector3(0f, 1.47f, -2.2f) : new Vector3(0f, 1.02f, 0f);
            return pos + rot * local;
        }

        void Ride(World world, EntityPlayerLocal pl)
        {
            if (RideTrain < 0) return;
            Train t = TrainStore.Get(RideTrain);
            if (t == null || pl.IsDead() || RideCar >= t.Cars.Count) { RideTrain = RideCar = -1; LeaveView(pl); return; }
            if (t.Cars[RideCar].Kind == "loco") t.Driver = true;
            KeepView(pl, t.Cars[RideCar].Kind);
            Vector3 seat = Seat(t, RideCar);
            pl.SetPosition(seat, false);
            pl.motion = Vector3.zero;
            pl.fallDistance = 0f;
        }

        void GetOff(World world, EntityPlayerLocal pl)
        {
            Train t = TrainStore.Get(RideTrain);
            LeaveView(pl);
            if (t != null)
            {
                t.Driver = false;
                t.Throttle = 0f;
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
            Hook("feTRun", (s, m) => { Train t = TrainPanel.Current; if (t != null) { t.Run = !t.Run; if (t.Run) { t.Manual = false; t.V = Mathf.Max(0f, t.V); t.State = "stopped"; } TrainStore.Dirty = true; } Refresh(); });
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

    /// <summary>Animation of a train car model (client side): FeSpin_r<radius>_* wheels roll with the distance the car
    /// moved along its own forward; on the locomotive, FeTrainPin_n (empty on a driving wheel's crank pin) drives
    /// FeTrainCouple_n (coupling rod: moves with the pin), FeTrainCross_n (crosshead: slides along the car, at the
    /// main rod's length from the pin) and FeTrainMain_n (main rod: from the crosshead pin to the crank pin);
    /// FeFx_Smoke / FeFx_Steam particles run while the train runs. Captured once from the pristine model, in the
    /// car root's space.</summary>
    public class TrainCarVisual : MonoBehaviour
    {
        class Wheel
        {
            public Transform T;
            public float R = 0.45f;
        }

        class Rods
        {
            public Transform Wheel, Couple, Cross, Main;
            public Vector3 PinInWheel, Pin0, Couple0, Cross0, MainOff, Dir0;
            public Quaternion Main0;
            public float L, Sign;
        }

        readonly List<Wheel> wheels = new List<Wheel>();
        readonly List<Rods> rods = new List<Rods>();
        readonly List<ParticleSystem> smoke = new List<ParticleSystem>();
        bool captured, hasLast, puffing;
        Vector3 last;

        void Capture()
        {
            captured = true;
            Dictionary<string, Transform> byName = new Dictionary<string, Transform>();
            foreach (Transform t in GetComponentsInChildren<Transform>(true))
            {
                byName[t.name] = t;
                if (!t.name.StartsWith("FeSpin", System.StringComparison.Ordinal)) continue;
                Wheel w = new Wheel { T = t };
                foreach (string tok in t.name.Split('_'))
                {
                    float r;
                    if (tok.Length > 1 && tok[0] == 'r' && float.TryParse(tok.Substring(1), System.Globalization.NumberStyles.Float,
                            System.Globalization.CultureInfo.InvariantCulture, out r) && r > 0.05f) w.R = r;
                }
                wheels.Add(w);
            }
            for (int n = 1; n <= 4; n++)
            {
                Transform pin;
                if (!byName.TryGetValue("FeTrainPin_" + n, out pin)) continue;
                Rods r = new Rods();
                float bestD = float.MaxValue;
                foreach (Wheel w in wheels)
                {
                    float d = (w.T.position - pin.position).sqrMagnitude;
                    if (d < bestD) { bestD = d; r.Wheel = w.T; }
                }
                if (r.Wheel == null) continue;
                byName.TryGetValue("FeTrainCouple_" + n, out r.Couple);
                byName.TryGetValue("FeTrainCross_" + n, out r.Cross);
                byName.TryGetValue("FeTrainMain_" + n, out r.Main);
                r.PinInWheel = r.Wheel.InverseTransformPoint(pin.position);
                r.Pin0 = transform.InverseTransformPoint(pin.position);
                if (r.Couple != null) r.Couple0 = transform.InverseTransformPoint(r.Couple.position);
                if (r.Cross != null)
                {
                    r.Cross0 = transform.InverseTransformPoint(r.Cross.position);
                    Vector3 w0 = r.Cross0 - r.Pin0;
                    r.L = w0.magnitude;
                    r.Sign = w0.z >= 0f ? 1f : -1f;
                    r.Dir0 = (r.Pin0 - r.Cross0).normalized;
                    if (r.Main != null)
                    {
                        r.MainOff = transform.InverseTransformPoint(r.Main.position) - r.Cross0;
                        r.Main0 = Quaternion.Inverse(transform.rotation) * r.Main.rotation;
                    }
                }
                rods.Add(r);
            }
            foreach (ParticleSystem ps in GetComponentsInChildren<ParticleSystem>(true))
                if (ps.name.StartsWith("FeFx_Smoke", System.StringComparison.Ordinal) || ps.name.StartsWith("FeFx_Steam", System.StringComparison.Ordinal))
                    smoke.Add(ps);
        }

        /// <summary>Called by TrainView after placing the car: pos / rot in absolute world space.</summary>
        public void Step(Vector3 pos, Quaternion rot, bool running, float speed)
        {
            if (!captured) Capture();
            float ds = 0f;
            if (hasLast)
            {
                Vector3 d = pos - last;
                if (d.sqrMagnitude < 400f) ds = Vector3.Dot(d, rot * Vector3.forward);
            }
            last = pos;
            hasLast = true;
            if (Mathf.Abs(ds) > 0.00001f)
            {
                foreach (Wheel w in wheels)
                {
                    if (w.T == null) continue;
                    // rolling forward = turning about the car's +X; the part turns about its own +Z
                    float sgn = Vector3.Dot(transform.InverseTransformDirection(w.T.forward), Vector3.right) >= 0f ? 1f : -1f;
                    w.T.Rotate(Vector3.forward, sgn * ds / w.R * Mathf.Rad2Deg, Space.Self);
                }
                foreach (Rods r in rods) Solve(r);
            }
            if (running != puffing)
            {
                puffing = running;
                foreach (ParticleSystem ps in smoke)
                {
                    if (ps == null) continue;
                    if (running) ps.Play(true);
                    else ps.Stop(true, ParticleSystemStopBehavior.StopEmitting);
                }
            }
            if (running)
                foreach (ParticleSystem ps in smoke)
                {
                    if (ps == null) continue;
                    ParticleSystem.EmissionModule em = ps.emission;
                    em.rateOverTimeMultiplier = 6f + speed * 2.5f;
                }
        }

        void Solve(Rods r)
        {
            if (r.Wheel == null) return;
            Vector3 pin = transform.InverseTransformPoint(r.Wheel.TransformPoint(r.PinInWheel));
            if (r.Couple != null) r.Couple.position = transform.TransformPoint(r.Couple0 + (pin - r.Pin0));
            if (r.Cross == null) return;
            // the crosshead stays on its line along the car (x, y of the built pose), the rod's length from the pin
            float dy = pin.y - r.Cross0.y, dx = pin.x - r.Cross0.x;
            float dz = Mathf.Sqrt(Mathf.Max(0f, r.L * r.L - dy * dy - dx * dx));
            Vector3 cross = new Vector3(r.Cross0.x, r.Cross0.y, pin.z + r.Sign * dz);
            r.Cross.position = transform.TransformPoint(cross);
            if (r.Main != null)
            {
                r.Main.position = transform.TransformPoint(cross + r.MainOff);
                r.Main.rotation = transform.rotation * (Quaternion.FromToRotation(r.Dir0, (pin - cross).normalized) * r.Main0);
            }
        }
    }
}
