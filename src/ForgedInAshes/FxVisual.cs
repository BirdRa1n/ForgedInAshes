// HD models' effects (Art/feHD/build_feHD.py, materials and particles made by Art/UnityProject FeBuild.cs):
//   FeMolten material   glowing metal: heat follows the metal (colour by metal), the texture scrolls while it flows,
//                       and it cools down to a dark crust when the flow stops (Metal Chute, Foundry launder,
//                       crucible, the cast in the Casting Table mold)
//   FeLiquid material   sight glasses / levels: colour of the fluid in it (pipe network, pump, condenser, quench trough)
//   FeGlow material     fire door slits: on, flickering, while the Foundry burns
//   FePour_* objects    falling stream of molten metal, shown while metal pours there
//   FeFx_* particles    FeFx_Steam_* (white), FeFx_Smoke_* (dark), FeFx_Sparks_* (embers): emit while the block works
// State comes from FluidStore / FluidTicker / the workstation tile entity (single player / host), like the other
// client visuals of the mod (CasterVisual, CondenserVisual). Client-side only.
//
// C# 5 only.

using System.Collections.Generic;
using HarmonyLib;
using UnityEngine;

namespace ForgedInAshes
{
    public class FxVisual : MonoBehaviour
    {
        class Slot
        {
            public Renderer R;
            public int Index;
        }

        Vector3i pos;
        FluidKind kind;
        readonly List<Slot> molten = new List<Slot>();
        readonly List<Slot> liquid = new List<Slot>();
        readonly List<Slot> glow = new List<Slot>();
        readonly List<GameObject> pours = new List<GameObject>();
        readonly List<ParticleSystem> steam = new List<ParticleSystem>();
        readonly List<ParticleSystem> smoke = new List<ParticleSystem>();
        readonly List<ParticleSystem> sparks = new List<ParticleSystem>();
        readonly List<ParticleSystem> fire = new List<ParticleSystem>();
        readonly List<ParticleSystem> splash = new List<ParticleSystem>();
        readonly List<ParticleSystem> dust = new List<ParticleSystem>();
        readonly List<ParticleSystem> drip = new List<ParticleSystem>();
        readonly List<ParticleSystem> spray = new List<ParticleSystem>();
        readonly List<ParticleSystem> bubbles = new List<ParticleSystem>();

        // process machines without a torque shaft: FeWorkSpin_[x<mult>]_* turn about their local +Z while it works
        class WorkSpin
        {
            public Transform T;
            public float Mult = 1f;
        }
        readonly List<WorkSpin> workSpins = new List<WorkSpin>();

        // FeSurface_r<range>_*: a liquid surface (pivot at the EMPTY level) that rises by up to <range> m with the
        // fluid buffer, and turns slowly about its local +Z while the machine works (the stir / the swirl)
        class Surface
        {
            public Transform T;
            public Vector3 Base;
            public float Range = 0.3f;
            public bool Spin;              // "_Spin" in the name: round surfaces turn while it works
        }
        // FeNeedle_* on a process machine (gas / steam gauges): pressure while it works (the Condenser's is
        // CondenserVisual's)
        // FeGrow_*: plants of a farming machine (Hydroponic Tower): they grow with the progress of the run (seedling ->
        // full size) and are small again after each harvest
        readonly List<Transform> grows = new List<Transform>();
        readonly List<Vector3> grows0 = new List<Vector3>();
        float growGoal, growNow;
        readonly List<Transform> needles = new List<Transform>();
        readonly List<Quaternion> needles0 = new List<Quaternion>();
        float pressure;
        readonly List<Surface> surfaces = new List<Surface>();
        float fill, fillNow, workSpeed;
        float needleGoal = -1f;                    // >= 0: the needles show this (tanks, gauge, valves)
        Transform armYaw;                          // FeArmYaw: the Mechanical Arm's turret (swings back <-> front)
        Quaternion armYaw0;
        bool armOn;
        float armPeriod = 1f, armT;
        bool working, dripping;
        Renderer castMetal;
        Transform lever;                 // FeLever_*: the Clutch lever (thrown one way engaged, the other released)
        Quaternion leverRest;
        float leverNow, leverGoal, lastProgress;
        MaterialPropertyBlock mpb;

        // state (goals set every 0.25 s, eased every frame)
        string metal = "", fluid = "";
        float heat, heatGoal, castHeat, castHeatGoal, glowNow, glowGoal, scroll, flowSpeed;
        bool pouring, steaming, smoking, sparking, burning, dusting;
        float next;

        static readonly int EmissionColor = Shader.PropertyToID("_EmissionColor");
        static readonly int ColorId = Shader.PropertyToID("_Color");
        static readonly int MainTexSt = Shader.PropertyToID("_MainTex_ST");

        public static void Attach(BlockEntityData ebcd, Vector3i pos, Block block)
        {
            if (ebcd == null || ebcd.transform == null || GameManager.IsDedicatedServer) return;
            FxVisual v = ebcd.transform.GetComponent<FxVisual>();
            if (v == null)
            {
                if (!HasFx(ebcd.transform)) return;
                v = ebcd.transform.gameObject.AddComponent<FxVisual>();
            }
            v.Init(pos, Fluids.Kind(block), block);
        }

        static bool FindName(Transform t, string n)
        {
            if (t.name.StartsWith(n, System.StringComparison.Ordinal)) return true;
            for (int i = 0; i < t.childCount; i++) if (FindName(t.GetChild(i), n)) return true;
            return false;
        }

        static bool HasFx(Transform t)
        {
            if (t.GetComponentsInChildren<ParticleSystem>(true).Length > 0) return true;
            if (t.name.StartsWith("feCoalGenerator") || FindName(t, "feCoalGen_Crank")) return true;
            foreach (Transform c in t.GetComponentsInChildren<Transform>(true))
                if (c.name.StartsWith("FeLever", System.StringComparison.Ordinal) || c.name.StartsWith("FeWorkSpin", System.StringComparison.Ordinal) ||
                    c.name.StartsWith("FeArmYaw", System.StringComparison.Ordinal) || c.name.StartsWith("FeNeedle", System.StringComparison.Ordinal) ||
                    c.name.StartsWith("FeSurface", System.StringComparison.Ordinal) || c.name.StartsWith("FeGrow", System.StringComparison.Ordinal)) return true;
            foreach (Renderer r in t.GetComponentsInChildren<Renderer>(true))
                foreach (Material m in r.sharedMaterials)
                    if (m != null && (m.name.StartsWith("FeMolten") || m.name.StartsWith("FeLiquid") || m.name.StartsWith("FeGlow")))
                        return true;
            return false;
        }

        bool engine, fuelGen;

        void Init(Vector3i p, FluidKind k, Block b)
        {
            pos = p;
            kind = k;
            engine = SteamEngine.Is(b) || TorqueEngine.IsEngine(b);   // fuel engines: fire, glow, smoke too
            fuelGen = !engine && b is BlockPowerSource && FuelGenerator.FuelItem(b) != null;   // Coal Generator
            lastE = lastB = lastLiquid = Color.clear;                 // pooled models: re-send everything once
            lastCast = lastGlow = -1f;
            far = false;
            nextFar = 0f;
            mpb = mpb ?? new MaterialPropertyBlock();
            molten.Clear(); liquid.Clear(); glow.Clear(); pours.Clear();
            steam.Clear(); smoke.Clear(); sparks.Clear(); fire.Clear(); splash.Clear(); dust.Clear();
            drip.Clear(); spray.Clear(); bubbles.Clear(); workSpins.Clear(); surfaces.Clear();
            needles.Clear(); needles0.Clear(); pressure = 0f;
            grows.Clear(); grows0.Clear(); growGoal = growNow = 0f;
            armYaw = null; armOn = false; armT = 0f;
            castMetal = null;
            lever = null;
            foreach (Renderer r in GetComponentsInChildren<Renderer>(true))
            {
                if (r is ParticleSystemRenderer) continue;
                if (r.name.StartsWith("FeCastMetal", System.StringComparison.Ordinal)) { castMetal = r; continue; }
                Material[] ms = r.sharedMaterials;
                for (int i = 0; i < ms.Length; i++)
                {
                    if (ms[i] == null) continue;
                    Slot s = new Slot { R = r, Index = i };
                    if (ms[i].name.StartsWith("FeMolten")) molten.Add(s);
                    else if (ms[i].name.StartsWith("FeLiquid")) liquid.Add(s);
                    else if (ms[i].name.StartsWith("FeGlow")) glow.Add(s);
                }
            }
            foreach (Transform t in GetComponentsInChildren<Transform>(true))
            {
                if (t.name.StartsWith("FePour", System.StringComparison.Ordinal)) pours.Add(t.gameObject);
                // Coal Generator HD (Art/feCoalGenerator): its crank and the dynamo rotor (2x, the other way) turn
                // while it burns; it is not a torque block, so KineticSpinner does not drive them
                if (fuelGen && (t.name.EndsWith("_Crank", System.StringComparison.Ordinal) ||
                                t.name.EndsWith("_DynamoRotor", System.StringComparison.Ordinal)))
                    workSpins.Add(new WorkSpin { T = t, Mult = t.name.EndsWith("_Crank", System.StringComparison.Ordinal) ? 1.5f : -3f });
                if (armYaw == null && t.name.StartsWith("FeArmYaw", System.StringComparison.Ordinal))
                {
                    armYaw = t;
                    armYaw0 = t.localRotation;
                }
                if (t.name.StartsWith("FeWorkSpin", System.StringComparison.Ordinal))
                {
                    WorkSpin w = new WorkSpin { T = t };
                    foreach (string tok in t.name.Split('_'))
                    {
                        float m;
                        if (tok.Length > 1 && tok[0] == 'x' && float.TryParse(tok.Substring(1), System.Globalization.NumberStyles.Float,
                                System.Globalization.CultureInfo.InvariantCulture, out m)) w.Mult = m;
                    }
                    workSpins.Add(w);
                }
                if (t.name.StartsWith("FeSurface", System.StringComparison.Ordinal))
                {
                    Surface sf = new Surface { T = t, Base = t.localPosition, Spin = t.name.Contains("_Spin") };
                    foreach (string tok in t.name.Split('_'))
                    {
                        float r;
                        if (tok.Length > 1 && tok[0] == 'r' && float.TryParse(tok.Substring(1), System.Globalization.NumberStyles.Float,
                                System.Globalization.CultureInfo.InvariantCulture, out r)) sf.Range = r;
                    }
                    surfaces.Add(sf);
                }
                if (t.name.StartsWith("FeGrow", System.StringComparison.Ordinal))
                {
                    grows.Add(t);
                    grows0.Add(t.localScale);
                }
                if (k != FluidKind.Condenser && t.name.StartsWith("FeNeedle", System.StringComparison.Ordinal))
                {
                    needles.Add(t);
                    needles0.Add(t.localRotation);
                }
                if (lever == null && t.name.StartsWith("FeLever", System.StringComparison.Ordinal))
                {
                    lever = t;
                    leverRest = t.localRotation;
                }
            }
            foreach (ParticleSystem ps in GetComponentsInChildren<ParticleSystem>(true))
            {
                string n = ps.name;
                if (n.StartsWith("FeFx_SteamVent", System.StringComparison.Ordinal)) continue;   // driven by SteamVent
                if (n.StartsWith("FeFx_Smoke", System.StringComparison.Ordinal)) smoke.Add(ps);
                else if (n.StartsWith("FeFx_Sparks", System.StringComparison.Ordinal)) sparks.Add(ps);
                else if (n.StartsWith("FeFx_Fire", System.StringComparison.Ordinal)) fire.Add(ps);
                else if (n.StartsWith("FeFx_Splash", System.StringComparison.Ordinal)) splash.Add(ps);
                else if (n.StartsWith("FeFx_Dust", System.StringComparison.Ordinal)) dust.Add(ps);
                else if (n.StartsWith("FeFx_Drip", System.StringComparison.Ordinal)) drip.Add(ps);
                else if (n.StartsWith("FeFx_Spray", System.StringComparison.Ordinal)) spray.Add(ps);
                else if (n.StartsWith("FeFx_Bubbles", System.StringComparison.Ordinal)) bubbles.Add(ps);
                else steam.Add(ps);
            }
            heat = castHeat = glowNow = 0f;
            pouring = steaming = smoking = sparking = burning = dusting = false;
            leverNow = leverGoal = 0f;
            lastProgress = 0f;
            next = 0f;
            Apply(steam, false); Apply(smoke, false); Apply(sparks, false);
            Apply(fire, false); Apply(splash, false); Apply(dust, false);
            Apply(drip, false); Apply(spray, false); Apply(bubbles, false);
            working = dripping = false;
            fill = fillNow = workSpeed = 0f;
            foreach (GameObject g in pours) g.SetActive(false);
        }

        // ------------------------------------------------------------ colours
        /// <summary>Emission colour of a molten metal at full heat (linear, HDR).</summary>
        static Color MetalGlow(string m)
        {
            switch (m)
            {
                case Fluids.MoltenSteel: return new Color(1.0f, 0.62f, 0.28f) * 5.5f;
                case Fluids.MoltenBrass: return new Color(1.0f, 0.58f, 0.16f) * 3.5f;
                case Fluids.MoltenLead: return new Color(0.9f, 0.45f, 0.22f) * 0.9f;   // ~330 C: barely glows
                default: return new Color(1.0f, 0.36f, 0.07f) * 4.5f;                  // iron
            }
        }

        /// <summary>Surface colour of the metal (cold crust / shiny lead).</summary>
        static Color MetalBase(string m, float h)
        {
            Color cold = m == Fluids.MoltenLead ? new Color(0.75f, 0.76f, 0.80f)
                       : (m == Fluids.MoltenBrass ? new Color(0.62f, 0.48f, 0.22f) : new Color(0.42f, 0.42f, 0.44f));
            return Color.Lerp(cold, Color.white, h);
        }

        static Color Heated(string m, float h)
        {
            if (h <= 0.001f) return Color.black;
            // cooling metal goes from yellow-orange through cherry red to dark
            Color hot = MetalGlow(m);
            Color red = new Color(0.8f, 0.08f, 0.01f) * (hot.maxColorComponent * 0.35f);
            return Color.Lerp(red, hot, Mathf.Clamp01(h * 1.4f - 0.2f)) * Mathf.Pow(h, 1.3f);
        }

        static Color FluidColor(string f)
        {
            switch (f)
            {
                case Fluids.Water: return new Color(0.10f, 0.30f, 0.42f, 0.72f);
                case Fluids.Steam: return new Color(0.92f, 0.93f, 0.95f, 0.35f);
                case Fluids.Oil: return new Color(0.03f, 0.025f, 0.02f, 0.96f);
                case Fluids.Gasoline: return new Color(0.58f, 0.44f, 0.10f, 0.70f);
                case Fluids.Lubricant: return new Color(0.42f, 0.28f, 0.06f, 0.88f);
                case "mash": return new Color(0.22f, 0.15f, 0.06f, 0.97f);            // digester mash
                case "slurry": return new Color(0.16f, 0.16f, 0.15f, 0.95f);          // coal + nitre slurry
                case "washwater": return new Color(0.30f, 0.28f, 0.20f, 0.85f);       // muddy wash water
                case "latex": return new Color(0.92f, 0.90f, 0.82f, 0.95f);
                case "crude_oil": return new Color(0.04f, 0.03f, 0.02f, 0.97f);
                case "": return new Color(0.05f, 0.06f, 0.06f, 0.90f);                 // empty glass
                default: return new Color(0.35f, 0.40f, 0.30f, 0.80f);
            }
        }

        // ------------------------------------------------------------ state
        void Sample()
        {
            World world = GameManager.Instance == null ? null : GameManager.Instance.World;
            if (world == null) return;
            FluidStore.EnsureLoaded();
            BlockValue bv = world.GetBlock(pos);
            Vector3i owner = Fluids.ParentOf(world, pos, bv);
            FluidState s = FluidStore.Get(owner);
            heatGoal = 0f; glowGoal = 0f; flowSpeed = 0f;
            pouring = steaming = smoking = sparking = burning = dusting = false;
            working = dripping = false;
            needleGoal = -1f;
            if (lever != null)
            {
                // D12: the Signal Lever follows its own state, the Belt Gate's bar comes down while it stops the belt
                string sk = Signals.Kind(bv.Block);
                if (sk == "lever") leverGoal = Signals.Emits(world, owner) ? 1f : -1f;
                else if (Logistics.IsGate(bv.Block)) leverGoal = Signals.Active(world, owner) ? 1f : -1f;
                else leverGoal = BlockFeKinetic.Engaged(bv) ? 1f : -1f;
            }
            if (Signals.Kind(bv.Block) == "receiver") glowGoal = Signals.Emits(world, owner) ? 1f : 0f;
            if (armYaw != null)
            {
                TileEntityPowered ate = world.GetTileEntity(owner) as TileEntityPowered;
                armOn = ate != null && ate.IsPowered;
                armPeriod = Mathf.Max(0.5f, Fluids.Prop(bv.Block, "FeArmSeconds", 1f));
            }
            if (fuelGen)
            {
                TileEntityPowerSource gte = world.GetTileEntity(owner) as TileEntityPowerSource;
                working = gte != null && gte.IsOn && gte.CurrentFuel > 0;
                smoking = steaming = working;
                Show();
                return;
            }
            if (engine)
            {
                // Steam Engine: fire, coal glow and stack smoke while it runs, the drain cocks puff (FeFx_Steam_*);
                // the exhaust plume over the outlet belongs to SteamVent (FeFx_SteamVent_*)
                bool run = TorqueEngine.IsRunning(world, owner);
                burning = smoking = steaming = run;
                glowGoal = run ? 1f : 0f;
                fluid = Fluids.Water;                                     // the Gas Engine's cooling hopper
                Show();
                return;
            }
            switch (kind)
            {
                case FluidKind.Chute:
                case FluidKind.Pipe:
                {
                    FluidNet net;
                    bool has = FluidTicker.NetByPipe.TryGetValue(pos, out net) && net != null;
                    string f = has ? net.Fluid : "";
                    bool flows = has && net.FlowPerMin > 0.1f;
                    if (Fluids.IsMetal(f))
                    {
                        metal = f;
                        if (flows) { heatGoal = 1f; flowSpeed = 0.35f; }
                    }
                    else fluid = flows || has ? f : "";
                    break;
                }
                case FluidKind.Smelter:
                {
                    TileEntityWorkstation ws = world.GetTileEntity(owner) as TileEntityWorkstation;
                    bool lit = ws != null && ws.IsBurning;
                    if (Industrial.IsElectric(bv.Block)) lit = s.Steam > 0.5f;
                    if (s.Fluid.Length > 0) metal = s.Fluid;
                    bool full = s.Amount > 0.01f;
                    bool out_ = s.LastFlow > 0.1f;
                    heatGoal = out_ ? 1f : (full ? (lit ? 0.85f : 0.45f) : 0f);
                    flowSpeed = out_ ? 0.3f : 0.03f;
                    glowGoal = lit ? 1f : 0f;
                    smoking = lit;
                    sparking = lit && full;
                    burning = lit;
                    pouring = Pour(out_);
                    break;
                }
                case FluidKind.Caster:
                {
                    if (s.Fluid.Length > 0) metal = s.Fluid;
                    Process pr = null;
                    foreach (Process p in Processes.For(MetalWorks.CasterBlock))
                        if (p.Kind == "cast" && p.Mold == s.Mold && p.FluidIn == s.Fluid) { pr = p; break; }
                    bool hasMetal = s.Amount > 0.01f;
                    bool full = pr != null && s.Amount >= pr.Liters - 0.01f;
                    float cooled = full && pr.Time > 0f ? Mathf.Clamp01(s.Steam / pr.Time) : 0f;
                    castHeatGoal = !hasMetal ? 0f : (full ? 1f - cooled : 1f);
                    pouring = Pour(s.LastFlow > 0.1f);
                    heatGoal = pouring ? 1f : 0f;                 // the stream itself
                    flowSpeed = 0.5f;
                    steaming = full && castHeatGoal > 0.1f;       // the cast steams while it cools
                    fluid = Fluids.Water;                         // quench trough
                    break;
                }
                case FluidKind.MechPump:
                case FluidKind.ElecPump:
                    fluid = s.LastFlow > 0.01f ? Fluids.Water : "";
                    break;
                case FluidKind.Condenser:
                    fluid = Fluids.Water;
                    steaming = s.LastFlow > 0.01f;
                    dripping = s.LastFlow > 0.01f || s.Steam > 0.5f;          // condensate running to the receiver
                    break;
                case FluidKind.Burner:
                    burning = s.Steam > 0.5f;                                   // heat stored = lit
                    glowGoal = burning ? 1f : 0f;
                    smoking = burning;
                    working = burning;                                          // Boiler Firebox: blower + stoker turn
                    break;
                case FluidKind.Tapper:
                    dripping = s.LastFlow > 0.01f || s.Amount > 0.01f;
                    fluid = "latex";
                    break;
                case FluidKind.Tank:
                case FluidKind.GasTank:
                {
                    float tcap = Fluids.Prop(bv.Block, "FeFluidCapacity", 2000f);
                    fill = tcap > 0f ? Mathf.Clamp01(s.Amount / tcap) : 0f;
                    fluid = s.Amount > 0.01f ? s.Fluid : "";
                    needleGoal = kind == FluidKind.GasTank ? Mathf.Clamp01(s.Amount / Mathf.Max(1f, tcap) / Fluids.Prop(bv.Block, "FeMaxBar", 10f)) : fill;
                    break;
                }
                case FluidKind.Gauge:
                    needleGoal = s.Bar > 0.01f ? Mathf.Clamp01(s.Bar / 12f) : Mathf.Clamp01(s.LastFlow / 600f);
                    glowGoal = Signals.Emits(world, owner) ? 1f : 0f;
                    fluid = s.Fluid;
                    break;
                case FluidKind.Valve:
                    fluid = s.Amount > 0.01f ? s.Fluid : "";
                    steaming = FluidControl.ValveType(bv.Block) == "alivio" && s.LastFlow > 0.01f;   // relief venting
                    needleGoal = Mathf.Clamp01(s.Bar / 12f);
                    break;
                case FluidKind.TowerSection:
                    fluid = s.Fluid;
                    break;
                case FluidKind.Boiler:
                {
                    // thermal plant drum (SteamPlant.cs): Amount = water, Steam = steam; the gauge reads the steam,
                    // the level glass the water, the safety valve blows off when the steam is nearly full
                    float wcap = Fluids.Prop(bv.Block, "FeFluidBuffer", 1000f);
                    float scap = Fluids.Prop(bv.Block, "FeSteamBuffer", 600f);
                    fill = wcap > 0f ? Mathf.Clamp01(s.Amount / wcap) : 0f;
                    fluid = s.Amount > 0.01f ? "water" : "";
                    needleGoal = scap > 0f ? Mathf.Clamp01(s.Steam / scap) : 0f;
                    steaming = scap > 0f && s.Steam > 0.9f * scap;
                    working = s.Steam > 1f && s.Amount > 1f;                    // the feed pump runs while it boils
                    break;
                }
                case FluidKind.Turbine:
                {
                    // steam turbine: Amount = steam in, Bar = steam L/min used; a little gland steam while it runs
                    float tbuf = Fluids.Prop(bv.Block, "FeFluidBuffer", 120f);
                    working = s.Bar > 0.01f;
                    steaming = working;
                    needleGoal = tbuf > 0f ? Mathf.Clamp01(s.Amount / tbuf) : 0f;
                    break;
                }
                case FluidKind.Processor:
                    // working = its progress (FluidState.Steam) moved since the last look
                    working = s.Steam > 0f && Mathf.Abs(s.Steam - lastProgress) > 0.001f;
                    lastProgress = s.Steam;
                    dusting = steaming = working;
                    dripping = working;
                    float cap = Fluids.Prop(bv.Block, "FeFluidBuffer", 20f);
                    fill = cap > 0f ? Mathf.Clamp01(s.Amount / cap) : 0f;
                    // what is in the tank: the mash of a digester, the slurry of the mixer, the wash water
                    string bn = bv.Block.GetBlockName();
                    fluid = bn.Contains("Biodigester") ? "mash" : (bn.Contains("ChemMixer") ? "slurry"
                          : (bn.Contains("Washer") ? "washwater" : (s.Fluid.Length > 0 ? s.Fluid : Fluids.Water)));
                    if (fill <= 0.01f && !working) fluid = "";
                    bool heat = bv.Block.Properties != null && (bv.Block.Properties.Contains("FeHeat") || bv.Block.Properties.Contains("FeTower"));
                    burning = working && (fluid == "mash" || heat);               // biogas flare / heated machines
                    sparking = working;                                           // grinder, welder (if they have sparks)
                    glowGoal = working && heat ? 1f : 0f;
                    if (grows.Count > 0)
                    {
                        // farming: the plants follow the run's progress; grow lights on while it grows
                        Process gp = null;
                        foreach (Process pr in ProcessMachine.Of(bv.Block)) if (pr.Id == s.Mold) { gp = pr; break; }
                        growGoal = gp != null && gp.Time > 0f ? Mathf.Clamp01(s.Steam / gp.Time) : 0f;
                        if (bv.Block.Properties != null && bv.Block.Properties.Contains("FeGrowLight")) glowGoal = working ? 1f : 0f;
                    }
                    break;
                default:
                    steaming = smoking = sparking = s.LastFlow > 0.01f;
                    break;
            }
            // machine sound (MachineSound.cs): a boiler / relief valve sounds while it blows steam, the rest while
            // they burn or work
            bool loud = kind == FluidKind.Boiler || kind == FluidKind.Valve ? steaming : (working || burning);
            MachineSound.Report(transform, pos, bv.Block, loud);
            Show();
        }

        // the fluid network moves metal in steps: keep the stream on 0.8 s after the last flow seen so it does not
        // blink on and off while a mold fills (user report 2026-11-24)
        float lastPour = -10f;

        bool Pour(bool flowing)
        {
            if (flowing) lastPour = Time.time;
            return Time.time - lastPour < 0.8f;
        }

        void Show()
        {
            foreach (GameObject g in pours) if (g.activeSelf != pouring) g.SetActive(pouring);
            Apply(steam, steaming);
            Apply(smoke, smoking);
            Apply(sparks, sparking);
            Apply(fire, burning);
            Apply(splash, pouring);
            Apply(dust, dusting);
            Apply(drip, dripping);
            Apply(spray, working);
            Apply(bubbles, working || (fill > 0.05f && kind == FluidKind.Processor && fluid == "mash"));
        }

        static void Apply(List<ParticleSystem> list, bool on)
        {
            foreach (ParticleSystem ps in list)
            {
                if (ps == null) continue;
                if (on && !ps.isEmitting) ps.Play(true);
                else if (!on && ps.isEmitting) ps.Stop(true, ParticleSystemStopBehavior.StopEmitting);
            }
        }

        // perf (2026-11-24): every pipe carries this component (its sight glass), so far away it sleeps and near it
        // only re-sends material values that changed
        const float FarSqr = 45f * 45f;
        bool far;
        float nextFar;
        Color lastE = Color.clear, lastB = Color.clear, lastLiquid = Color.clear;
        float lastCast = -1f, lastGlow = -1f;

        void StopAll()
        {
            Apply(steam, false); Apply(smoke, false); Apply(sparks, false); Apply(fire, false);
            Apply(splash, false); Apply(dust, false); Apply(drip, false); Apply(spray, false); Apply(bubbles, false);
        }

        void Update()
        {
            if (Time.time >= nextFar)
            {
                nextFar = Time.time + 1f + (pos.x & 3) * 0.05f;
                Camera cam = Camera.main;
                bool f = cam != null && (cam.transform.position - transform.position).sqrMagnitude > FarSqr;
                if (f != far)
                {
                    far = f;
                    if (far) StopAll();
                    else next = 0f;
                }
            }
            if (far) return;
            if (Time.time >= next)
            {
                next = Time.time + 0.25f;
                Sample();
            }
            float dt = Time.deltaTime;
            // heats fast, cools slowly (metal left in a chute cools in ~10 s, darkening through red)
            heat = heatGoal > heat ? Mathf.MoveTowards(heat, heatGoal, 2f * dt) : Mathf.MoveTowards(heat, heatGoal, 0.1f * dt);
            castHeat = castHeatGoal > castHeat ? Mathf.MoveTowards(castHeat, castHeatGoal, 2f * dt)
                                               : Mathf.MoveTowards(castHeat, castHeatGoal, 0.5f * dt);
            glowNow = Mathf.MoveTowards(glowNow, glowGoal, dt);
            workSpeed = Mathf.MoveTowards(workSpeed, working ? 1f : 0f, 0.8f * dt);           // spins up / runs down
            if (grows.Count > 0)
            {
                // grow smoothly; after a harvest (goal drops) snap back to seedlings
                growNow = growGoal < growNow - 0.2f ? growGoal : Mathf.MoveTowards(growNow, growGoal, 0.2f * dt);
                float sc = 0.2f + 0.8f * growNow;
                for (int i = 0; i < grows.Count; i++) if (grows[i] != null) grows[i].localScale = grows0[i] * sc;
            }
            if (armYaw != null && armOn)
            {
                // the arm swings from behind (pick) to the front (place) and back once per transfer period
                armT += dt / armPeriod;
                float yaw = 90f - 180f * (0.5f - 0.5f * Mathf.Cos(armT * Mathf.PI * 2f));
                armYaw.localRotation = armYaw0 * Quaternion.AngleAxis(yaw - 90f, Vector3.forward);
            }
            if (needles.Count > 0)
            {
                float goalP = needleGoal >= 0f ? needleGoal : (working ? 0.6f : 0.12f * fill);
                pressure = Mathf.MoveTowards(pressure, goalP, 0.3f * dt);
                float shake = working ? 1.5f * Mathf.Sin(Time.time * 19f) : 0f;
                for (int i = 0; i < needles.Count; i++)
                    if (needles[i] != null)
                        needles[i].localRotation = needles0[i] * Quaternion.AngleAxis(135f - 270f * pressure + shake, Vector3.forward);
            }
            if (workSpeed > 0.001f)
                foreach (WorkSpin w in workSpins)
                    if (w.T != null) w.T.Rotate(Vector3.forward, 120f * w.Mult * workSpeed * dt, Space.Self);
            if (surfaces.Count > 0)
            {
                fillNow = Mathf.MoveTowards(fillNow, fill, 0.2f * dt);
                foreach (Surface sf in surfaces)
                {
                    if (sf.T == null) continue;
                    Vector3 up = sf.T.parent != null ? sf.T.parent.InverseTransformDirection(transform.up) : Vector3.up;
                    float bob = workSpeed * 0.004f * Mathf.Sin(Time.time * 5f + sf.Base.x * 7f);
                    sf.T.localPosition = sf.Base + up * (fillNow * sf.Range + bob);
                    if (sf.Spin && workSpeed > 0.001f) sf.T.Rotate(Vector3.forward, 25f * workSpeed * dt, Space.Self);
                }
            }
            if (lever != null && leverNow != leverGoal)
            {
                leverNow = Mathf.MoveTowards(leverNow, leverGoal, 4f * dt);       // a quick throw (~0.5 s)
                lever.localRotation = leverRest * Quaternion.AngleAxis(35f * leverNow, Vector3.right);
            }
            scroll += flowSpeed * dt;
            if (scroll > 100f) scroll -= 100f;

            if (molten.Count > 0)
            {
                Color e = Heated(metal, heat);
                Color b = MetalBase(metal, heat);
                Vector4 st = new Vector4(1f, 1f, 0f, scroll);
                if (e != lastE || b != lastB || (flowSpeed > 0f && heat > 0.001f))
                {
                    lastE = e;
                    lastB = b;
                    foreach (Slot sl in molten) SetMolten(sl, e, b, st);
                }
            }
            if (castMetal != null && (castHeat != lastCast || castHeat > 0.001f))
            {
                lastCast = castHeat;
                mpb.Clear();
                mpb.SetColor(EmissionColor, Heated(metal, castHeat));
                mpb.SetColor(ColorId, MetalBase(metal, castHeat));
                mpb.SetVector(MainTexSt, new Vector4(1f, 1f, 0f, scroll * 0.1f));
                castMetal.SetPropertyBlock(mpb);
            }
            if (liquid.Count > 0)
            {
                Color c = FluidColor(fluid);
                if (c != lastLiquid)
                {
                lastLiquid = c;
                foreach (Slot sl in liquid)
                {
                    if (sl.R == null) continue;
                    mpb.Clear();
                    mpb.SetColor(ColorId, c);
                    sl.R.SetPropertyBlock(mpb, sl.Index);
                }
                }
            }
            if (glow.Count > 0 && (glowNow > 0.001f || lastGlow != 0f))
            {
                lastGlow = glowNow > 0.001f ? glowNow : 0f;
                float flicker = glowNow * (0.8f + 0.2f * Mathf.PerlinNoise(Time.time * 3f, pos.x * 0.37f));
                Color g = new Color(1f, 0.33f, 0.06f) * 5f * flicker;
                foreach (Slot sl in glow)
                {
                    if (sl.R == null) continue;
                    mpb.Clear();
                    mpb.SetColor(EmissionColor, g);
                    sl.R.SetPropertyBlock(mpb, sl.Index);
                }
            }
        }

        void SetMolten(Slot sl, Color emission, Color baseColor, Vector4 st)
        {
            if (sl.R == null) return;
            mpb.Clear();
            mpb.SetColor(EmissionColor, emission);
            mpb.SetColor(ColorId, baseColor);
            mpb.SetVector(MainTexSt, st);
            sl.R.SetPropertyBlock(mpb, sl.Index);
        }
    }

    // Block, BlockPowered and BlockPowerSource each declare the method (the last two without calling the base), so
    // all three are patched; Attach is idempotent and skips models without effects.
    [HarmonyPatch(typeof(Block), "OnBlockEntityTransformAfterActivated")]
    public static class Patch_Block_FxVisual
    {
        public static void Postfix(Block __instance, Vector3i _blockPos, BlockEntityData _ebcd)
        {
            if (__instance.GetBlockName().StartsWith("fe", System.StringComparison.Ordinal))
                FxVisual.Attach(_ebcd, _blockPos, __instance);
        }
    }

    [HarmonyPatch(typeof(BlockPowered), "OnBlockEntityTransformAfterActivated")]
    public static class Patch_BlockPowered_FxVisual
    {
        public static void Postfix(BlockPowered __instance, Vector3i _blockPos, BlockEntityData _ebcd)
        {
            if (__instance.GetBlockName().StartsWith("fe", System.StringComparison.Ordinal))
                FxVisual.Attach(_ebcd, _blockPos, __instance);
        }
    }

    [HarmonyPatch(typeof(BlockPowerSource), "OnBlockEntityTransformAfterActivated")]
    public static class Patch_BlockPowerSource_FxVisual
    {
        public static void Postfix(BlockPowerSource __instance, Vector3i _blockPos, BlockEntityData _ebcd)
        {
            if (__instance.GetBlockName().StartsWith("fe", System.StringComparison.Ordinal))
                FxVisual.Attach(_ebcd, _blockPos, __instance);
        }
    }
}
