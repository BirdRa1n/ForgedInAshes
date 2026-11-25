// Ferro & Engrenagem: turns the Blender FBX exports in Art/<block>/<block>.fbx into
// 7DTD block prefabs and builds the mod's asset bundle.
//
// Prefab layout copied from vanilla block prefabs of 7DTD 3.4.0 (forgeWorkstationPrefab,
// table_sawPrefab in crafting.bundle, inspected with UnityPy):
//   root   : layer 16 ("TerrainCollision"), tag "T_Block" (tag index 20004, so the
//            TagManager must list Item, T_Mesh, B_Mesh, T_Mesh_B, T_Block in this order),
//            solid BoxCollider(s) on the root
//   child  : the model, layer 0, moved -0.5 m in Y (the block origin is the center of the
//            bottom block; our Blender models have their origin on the floor)
// Model path in blocks.xml (DataLoader.ParseDataPathIdentifier):
//   Model="#@modfolder:Resources/ferroengrenagem.unity3d?<block>Prefab"
//
// Menu: FerroEngrenagem > Build All. Batch:
//   Unity.exe -batchmode -quit -projectPath Art/UnityProject -executeMethod FeBuild.BuildAll
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static class FeBuild
{
    // Blocks to export (folder and FBX name under Art/). Items are not handled here yet.
    static readonly string[] Blocks =
    {
        "feCrank",
        // D8 torque network (Art/feKinetic/build_feKinetic.py)
        "feTorqueCrank", "feShaft", "feSpeedBox", "feGearbox", "feSpinInverter", "feTorqueRegulator",
        "feClutch", "feTorqueGauge", "feWaterWheel", "feSteamEngine",
        // D9 fluid network
        "fePipe", "feWaterTank", "feMechPump", "feElecPump", "feCondenser",
        "feElectricMotor", "feElectricMotor2", "feElectricMotor3", "feDynamo",
        "feDynamo2", "feBus", "feConveyor", "feConveyorRamp", "feFunnel", "feConveyorDuct", "feConveyorStand", "feCoalGenerator", "feCoalEngine", "feGasEngine", "feBeltCrate", "feConveyorDown", "feFluidFiller", "feFluidBottler", "feMetalChute", "feCaster", "feCrusher", "feChemMixer", "feWasher", "feSteamDryer", "feInductionFurnace", "feCasterElectric", "feRetortKiln", "feBiodigester", "feBiodigesterBig",
        // D13 (Art/feHD/build_feHD.py, D13_MODELS)
        "feMechDrill", "feMechSaw", "feMechHarvester", "feDeployer", "feFan", "feMechPiston", "fePistonHead", "feCogwheel", "feWindmill", "feHosePulley", "feDepot", "feItemChute", "feItemVault", "feItemDrain", "feDisplayPanel", "feSignalAnalog", "feWirelessTx", "feWirelessRx", "feBeltTunnel",
        // thermal power plant (PLANT_MODELS)
        "feBoilerFirebox", "feBoilerDrum", "feSteamTurbine",
        // D12 (Art/feHD/build_feHD.py, D12_MODELS)
        "fePipeHP", "feValveShutoff", "feValveCheck", "feValveRegulator", "feValveSeparator", "feValveRelief", "feGauge", "feCompressor", "feTankLiquid", "feTankGas", "feGasBurner", "feSapTapper", "feTowerSection", "feDistillTower", "feShaleRetort", "feCracker", "feGasScrubber", "fePolymerReactor", "feCoagTank", "feCalender", "feVulcanizer", "feSteelConverter", "feSpringCoiler", "feTemperFurnace", "feSpinner", "feTannery", "feFermenter", "feCentrifuge", "feAutoclave", "feCookerIndustrial", "feMill", "feJuicePress", "feCanner", "feInjector", "feGasMotor", "feInlinePress", "feDoser", "feInserter", "feCrimper", "feWireDrawer", "feGrinder", "feBender", "feWelder", "feReflowOven", "feMechArm", "feSignalLever", "feSignalReceiver", "feBeltSplitter", "feBeltGate", "feBeltCounter",
        "feM_Foundry", "feM_Press", "feM_Lathe", "feM_Kiln", "feM_Ammo", "feM_Assembler", "feM_ModBench", "feM_Loom", "feM_Refinery", "feM_Lab", "feM_Kitchen", "feM_Electronics", "feM_MetalShop", "feM_Sawmill", "feM_Mixer", "feM_Garage", "feM_Robotics"
    };

    const string ModelsDir = "Assets/Models";
    const string PrefabDir = "Assets/Prefabs";
    const string BundleName = "ferroengrenagem.unity3d";
    const int BlockLayer = 16;          // TerrainCollision
    const string BlockTag = "T_Block";

    static string ProjectRoot => Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
    static string ArtDir => Path.GetFullPath(Path.Combine(ProjectRoot, ".."));
    static string OutDir => Path.GetFullPath(Path.Combine(ProjectRoot, "..", "..", "Mods", "FerroEngrenagem", "Resources"));

    [MenuItem("FerroEngrenagem/Build All")]
    public static void BuildAll()
    {
        SyncModels();
        BuildPrefabs();
        BuildBundle();
    }

    [MenuItem("FerroEngrenagem/1. Sync FBX from Art")]
    public static void SyncModels()
    {
        Directory.CreateDirectory(Path.Combine(ProjectRoot, ModelsDir));
        Directory.CreateDirectory(Path.Combine(ProjectRoot, HdDir));
        Directory.CreateDirectory(Path.Combine(ProjectRoot, FxDir));
        foreach (var b in Blocks)
        {
            // HD remake (Art/<block>/hd/<block>_HD.fbx + PBR atlas, made by F:\IA texturizar): used when present
            var hd = Path.Combine(ArtDir, b, "hd", b + "_HD.fbx");
            var src = File.Exists(hd) ? hd : Path.Combine(ArtDir, b, b + ".fbx");
            if (!File.Exists(src)) { Debug.LogError($"[FE] missing {src}"); continue; }
            File.Copy(src, Path.Combine(ProjectRoot, ModelsDir, b + ".fbx"), true);
            if (src != hd) continue;
            foreach (var map in HdMaps)
            {
                var png = Path.Combine(ArtDir, b, "hd", $"{b}_{map}.png");
                if (File.Exists(png)) File.Copy(png, Path.Combine(ProjectRoot, HdDir, $"{b}_{map}.png"), true);
            }
            Debug.Log($"[FE] {b}: HD model");
        }
        foreach (var f in Directory.GetFiles(Path.Combine(ArtDir, "feFx"), "*.png"))
            File.Copy(f, Path.Combine(ProjectRoot, FxDir, Path.GetFileName(f)), true);
        AssetDatabase.Refresh();
        // texture import settings: normal maps as normal maps, data maps linear
        foreach (var guid in AssetDatabase.FindAssets("t:Texture2D", new[] { HdDir, FxDir }))
        {
            var path = AssetDatabase.GUIDToAssetPath(guid);
            var ti = (TextureImporter)AssetImporter.GetAtPath(path);
            bool changed = false;
            void Set<T>(T now, T want, System.Action<T> apply) { if (!Equals(now, want)) { apply(want); changed = true; } }
            if (path.EndsWith("_Normal.png")) Set(ti.textureType, TextureImporterType.NormalMap, v => ti.textureType = v);
            if (path.EndsWith("_MetallicSmoothness.png") || path.EndsWith("_heat.png"))
                Set(ti.sRGBTexture, false, v => ti.sRGBTexture = v);
            if (path.StartsWith(FxDir) && !path.Contains("molten"))
                Set(ti.alphaIsTransparency, true, v => ti.alphaIsTransparency = v);
            // metal / smoothness maps at 512 (they hardly show up close; keeps the bundle under GitHub's 100 MiB per file)
            Set(ti.maxTextureSize, path.EndsWith("_MetallicSmoothness.png") ? 512 : 2048, v => ti.maxTextureSize = v);
            // crunch: ~5x smaller bundle (35 MB -> ~7 MB for the first seven HD models); small loss, fine for props
            Set(ti.crunchedCompression, true, v => ti.crunchedCompression = v);
            Set(ti.compressionQuality, 60, v => ti.compressionQuality = v);
            if (changed) ti.SaveAndReimport();
        }
    }

    // ------------------------------------------------------------------ HD materials and effects
    const string HdDir = "Assets/Models/HD";
    const string FxDir = "Assets/Fx";
    const string MatDir = "Assets/Materials";
    // Wire anchors for powered models that have no WireOffset empty (Unity model space: x = -Blender x, y = up)
    static readonly System.Collections.Generic.Dictionary<string, Vector3> WireFallback =
        new System.Collections.Generic.Dictionary<string, Vector3> { { "feCoalGenerator", new Vector3(-0.42f, 1.30f, 0f) } };

    static readonly string[] OptionalParts = { "FeBeltChute", "FeDuctBoot", "FeDuctRamp", "FeDuctHatch", "FeFunnelSpout", "FeSurface", "FeTrackItem", "FeBeltDrive", "FeSpin_BeltDrive", "FeReach", "FePiston_Inline", "FeSpin_x6_Inline", "FeBeltExtra", "FeLever_BeltGate", "FeSpin_WindSails" };
    static readonly string[] HdMaps = { "Albedo", "Normal", "MetallicSmoothness", "Emission" };

    static Material SaveMat(Material m, string name)
    {
        Directory.CreateDirectory(Path.Combine(ProjectRoot, MatDir));
        var path = $"{MatDir}/{name}.mat";
        var old = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (old != null) { old.shader = m.shader; old.CopyPropertiesFromMaterial(m); old.shaderKeywords = m.shaderKeywords; old.renderQueue = m.renderQueue; old.globalIlluminationFlags = m.globalIlluminationFlags; EditorUtility.SetDirty(old); return old; }
        AssetDatabase.CreateAsset(m, path);
        return m;
    }

    static Texture2D Tex(string path) => AssetDatabase.LoadAssetAtPath<Texture2D>(path);

    /// <summary>The block's own PBR atlas material (Standard, metallic workflow); null when it has no HD model.</summary>
    static Material HdMaterial(string b)
    {
        var alb = Tex($"{HdDir}/{b}_Albedo.png");
        if (alb == null) return null;
        var m = new Material(Shader.Find("Standard"));
        m.SetTexture("_MainTex", alb);
        var nrm = Tex($"{HdDir}/{b}_Normal.png");
        if (nrm != null) { m.SetTexture("_BumpMap", nrm); m.EnableKeyword("_NORMALMAP"); }
        var ms = Tex($"{HdDir}/{b}_MetallicSmoothness.png");
        if (ms != null) { m.SetTexture("_MetallicGlossMap", ms); m.EnableKeyword("_METALLICGLOSSMAP"); m.SetFloat("_GlossMapScale", 1f); }
        var em = Tex($"{HdDir}/{b}_Emission.png");
        if (em != null)
        {
            m.SetTexture("_EmissionMap", em); m.SetColor("_EmissionColor", Color.white * 3f); m.EnableKeyword("_EMISSION");
            m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
        }
        return SaveMat(m, b + "_HD");
    }

    static void Transparent(Material m, bool premultiply)
    {
        m.SetFloat("_Mode", premultiply ? 3f : 2f);
        m.SetInt("_SrcBlend", (int)(premultiply ? UnityEngine.Rendering.BlendMode.One : UnityEngine.Rendering.BlendMode.SrcAlpha));
        m.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
        m.SetInt("_ZWrite", 0);
        m.DisableKeyword("_ALPHATEST_ON");
        if (premultiply) m.EnableKeyword("_ALPHAPREMULTIPLY_ON"); else m.EnableKeyword("_ALPHABLEND_ON");
        m.renderQueue = 3000;
    }

    static Material molten, liquid, gas, glow, smoke, spark, flame, band;

    /// <summary>Shared effect materials. FxVisual (the mod's C#) recolours them per block with property blocks:
    /// _EmissionColor (heat / metal colour), _Color (fluid colour), _MainTex_ST offset (flow).</summary>
    static void EffectMaterials()
    {
        molten = new Material(Shader.Find("Standard"));
        molten.SetTexture("_MainTex", Tex($"{FxDir}/molten_crust.png"));
        molten.SetTexture("_EmissionMap", Tex($"{FxDir}/molten_heat.png"));
        molten.SetColor("_Color", Color.white);
        molten.SetColor("_EmissionColor", Color.black);          // cold until the mod heats it
        molten.SetFloat("_Glossiness", 0.35f);
        molten.SetFloat("_Metallic", 0.2f);
        molten.EnableKeyword("_EMISSION");
        molten.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
        molten = SaveMat(molten, "FeMolten");

        liquid = new Material(Shader.Find("Standard"));
        liquid.SetColor("_Color", new Color(0.05f, 0.06f, 0.06f, 0.9f)); // empty sight glass until the mod colours it
        liquid.SetFloat("_Glossiness", 0.96f);
        liquid.SetFloat("_Metallic", 0f);
        Transparent(liquid, true);
        liquid = SaveMat(liquid, "FeLiquid");

        gas = new Material(Shader.Find("Standard"));
        gas.SetColor("_Color", new Color(0.92f, 0.94f, 0.96f, 0.35f));
        gas.SetFloat("_Glossiness", 0.2f);
        Transparent(gas, false);
        gas = SaveMat(gas, "FeGas");

        glow = new Material(Shader.Find("Standard"));
        glow.SetColor("_Color", new Color(0.08f, 0.05f, 0.04f));
        glow.SetColor("_EmissionColor", Color.black);            // off until it burns
        glow.EnableKeyword("_EMISSION");
        glow.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
        glow = SaveMat(glow, "FeGlow");

        smoke = new Material(Shader.Find("Legacy Shaders/Particles/Alpha Blended"));
        smoke.SetTexture("_MainTex", Tex($"{FxDir}/smoke_puff.png"));
        smoke.SetColor("_TintColor", new Color(0.5f, 0.5f, 0.5f, 0.5f));
        smoke = SaveMat(smoke, "FeSmoke");

        spark = new Material(Shader.Find("Legacy Shaders/Particles/Additive"));
        spark.SetTexture("_MainTex", Tex($"{FxDir}/spark.png"));
        spark.SetColor("_TintColor", new Color(1f, 0.55f, 0.2f, 0.6f));
        spark = SaveMat(spark, "FeSpark");

        flame = new Material(Shader.Find("Legacy Shaders/Particles/Additive"));
        flame.SetTexture("_MainTex", Tex($"{FxDir}/flame.png"));
        flame.SetColor("_TintColor", new Color(1f, 0.6f, 0.3f, 0.7f));
        flame = SaveMat(flame, "FeFlame");

        // the conveyor band (material feBelt_Band, Art/feConveyor/split_for_hd.py): tileable rubber with molded
        // cleats, its own UV (v = along the travel, 1 tile = 0.25 m); BeltShape scrolls _MainTex_ST with the speed
        band = new Material(Shader.Find("Standard"));
        band.SetTexture("_MainTex", Tex($"{FxDir}/belt_band_Albedo.png"));
        band.SetTexture("_BumpMap", Tex($"{FxDir}/belt_band_Normal.png"));
        band.EnableKeyword("_NORMALMAP");
        band.SetFloat("_Glossiness", 0.22f);
        band.SetFloat("_Metallic", 0f);
        band = SaveMat(band, "FeBeltBand");
    }

    /// <summary>Swaps the imported FBX materials: "<block>_HD" -> atlas, feHD_Molten / Liquid / Gas / Glow -> effects.</summary>
    static void ApplyMaterials(GameObject inst, Material hd)
    {
        foreach (var r in inst.GetComponentsInChildren<Renderer>(true))
        {
            var mats = r.sharedMaterials;
            for (int i = 0; i < mats.Length; i++)
            {
                var n = mats[i] == null ? "" : mats[i].name;
                if (hd != null && n.EndsWith("_HD")) mats[i] = hd;
                else if (n.StartsWith("feHD_Molten") || n.StartsWith("feKin_Molten")) mats[i] = molten;
                else if (n.StartsWith("feHD_Liquid")) mats[i] = liquid;
                else if (n.StartsWith("feHD_Gas")) mats[i] = gas;
                else if (n.StartsWith("feHD_Glow")) mats[i] = glow;
                else if (n.StartsWith("feBelt_Band")) mats[i] = band;
            }
            r.sharedMaterials = mats;
        }
    }

    /// <summary>A particle look: name prefix -> settings. All emit along world up (the prefab is unrotated here).</summary>
    class Fx
    {
        public string Prefix; public bool Additive, Stretch; public Material Mat;
        public float Life0, Life1, Speed0, Speed1, Size0, Size1, Grav, Rate, Angle, Radius, Grow; public int Max;
        public Color Col;
    }

    static Fx[] FxLooks() => new[]
    {
        // fire inside a firebox: short, licking flames that stay under the lintel
        new Fx { Prefix = "FeFx_Fire", Additive = true, Mat = flame, Life0 = 0.25f, Life1 = 0.45f, Speed0 = 0.15f, Speed1 = 0.35f,
                 Size0 = 0.08f, Size1 = 0.16f, Grav = -0.15f, Rate = 26f, Angle = 8f, Radius = 0.14f, Grow = 0.4f, Max = 40,
                 Col = new Color(1f, 0.75f, 0.45f, 0.9f) },
        // hot metal hitting the mold / launder: few low, short sparks
        new Fx { Prefix = "FeFx_Splash", Additive = true, Stretch = true, Mat = spark, Life0 = 0.2f, Life1 = 0.45f, Speed0 = 0.4f,
                 Speed1 = 1.0f, Size0 = 0.012f, Size1 = 0.03f, Grav = 1.0f, Rate = 22f, Angle = 55f, Radius = 0.02f, Grow = 1f,
                 Max = 30, Col = new Color(1f, 0.75f, 0.35f, 1f) },
        new Fx { Prefix = "FeFx_Sparks", Additive = true, Stretch = true, Mat = spark, Life0 = 0.4f, Life1 = 0.9f, Speed0 = 1.0f,
                 Speed1 = 2.2f, Size0 = 0.02f, Size1 = 0.05f, Grav = 0.6f, Rate = 18f, Angle = 25f, Radius = 0.08f, Grow = 1f,
                 Max = 60, Col = new Color(1f, 0.7f, 0.3f, 1f) },
        new Fx { Prefix = "FeFx_Smoke", Mat = smoke, Life0 = 2.2f, Life1 = 3.5f, Speed0 = 0.3f, Speed1 = 0.7f, Size0 = 0.3f,
                 Size1 = 0.5f, Grav = -0.04f, Rate = 6f, Angle = 12f, Radius = 0.08f, Grow = 2.4f, Max = 40,
                 Col = new Color(0.18f, 0.17f, 0.16f, 0.55f) },
        new Fx { Prefix = "FeFx_Dust", Mat = smoke, Life0 = 1.0f, Life1 = 1.8f, Speed0 = 0.1f, Speed1 = 0.3f, Size0 = 0.15f,
                 Size1 = 0.3f, Grav = -0.01f, Rate = 8f, Angle = 40f, Radius = 0.25f, Grow = 2f, Max = 30,
                 Col = new Color(0.55f, 0.50f, 0.42f, 0.35f) },
        // condensate dripping in a sight-flow glass / off a wet drum: falling drops
        new Fx { Prefix = "FeFx_Drip", Stretch = true, Mat = smoke, Life0 = 0.35f, Life1 = 0.5f, Speed0 = 0f, Speed1 = 0.05f,
                 Size0 = 0.012f, Size1 = 0.02f, Grav = 1.0f, Rate = 7f, Angle = 2f, Radius = 0.01f, Grow = 1f, Max = 12,
                 Col = new Color(0.65f, 0.80f, 0.95f, 0.8f) },
        // water spray from a spray bar: pointed DOWN (negative speed), fine and fast
        new Fx { Prefix = "FeFx_Spray", Stretch = true, Mat = smoke, Life0 = 0.25f, Life1 = 0.4f, Speed0 = -1.4f, Speed1 = -0.8f,
                 Size0 = 0.02f, Size1 = 0.045f, Grav = 0.8f, Rate = 70f, Angle = 28f, Radius = 0.12f, Grow = 1f, Max = 60,
                 Col = new Color(0.80f, 0.90f, 1.0f, 0.45f) },
        // gas / air bubbles bursting on a liquid surface
        new Fx { Prefix = "FeFx_Bubbles", Mat = smoke, Life0 = 0.4f, Life1 = 0.9f, Speed0 = 0.03f, Speed1 = 0.10f,
                 Size0 = 0.02f, Size1 = 0.05f, Grav = -0.02f, Rate = 14f, Angle = 70f, Radius = 0.18f, Grow = 1.6f, Max = 24,
                 Col = new Color(0.85f, 0.82f, 0.70f, 0.45f) },
        // exhaust steam of the engine: a strong white plume
        new Fx { Prefix = "FeFx_SteamVent", Mat = smoke, Life0 = 1.6f, Life1 = 2.6f, Speed0 = 1.2f, Speed1 = 2.0f, Size0 = 0.25f,
                 Size1 = 0.45f, Grav = -0.08f, Rate = 14f, Angle = 8f, Radius = 0.06f, Grow = 3f, Max = 60,
                 Col = new Color(0.95f, 0.95f, 0.97f, 0.55f) },
        new Fx { Prefix = "FeFx_Steam", Mat = smoke, Life0 = 1.8f, Life1 = 3.0f, Speed0 = 0.25f, Speed1 = 0.6f, Size0 = 0.2f,
                 Size1 = 0.4f, Grav = -0.04f, Rate = 5f, Angle = 12f, Radius = 0.06f, Grow = 2.2f, Max = 40,
                 Col = new Color(0.92f, 0.93f, 0.95f, 0.45f) },
    };

    /// <summary>FeFx_* empties become particle systems (look by name prefix, see FxLooks). They do not play on their
    /// own: FxVisual / SteamVent start and stop them from the block's state.</summary>
    static void AddParticles(Transform root)
    {
        var looks = FxLooks();
        foreach (var t in root.GetComponentsInChildren<Transform>(true))
        {
            if (!t.name.StartsWith("FeFx_")) continue;
            Fx fx = null;
            foreach (var l in looks) if (t.name.StartsWith(l.Prefix)) { fx = l; break; }
            if (fx == null) { Debug.LogError($"[FE] unknown effect {t.name}"); continue; }
            t.rotation = Quaternion.LookRotation(Vector3.up, Vector3.forward);
            var ps = t.gameObject.GetComponent<ParticleSystem>();
            if (ps == null) ps = t.gameObject.AddComponent<ParticleSystem>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main;
            main.playOnAwake = false;
            main.loop = true;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.maxParticles = fx.Max;
            main.startLifetime = new ParticleSystem.MinMaxCurve(fx.Life0, fx.Life1);
            main.startSpeed = new ParticleSystem.MinMaxCurve(fx.Speed0, fx.Speed1);
            main.startSize = new ParticleSystem.MinMaxCurve(fx.Size0, fx.Size1);
            main.startRotation = new ParticleSystem.MinMaxCurve(0f, 6.28f);
            main.gravityModifier = fx.Grav;
            main.startColor = fx.Col;
            var em = ps.emission;
            em.rateOverTime = fx.Rate;
            var sh = ps.shape;
            sh.shapeType = ParticleSystemShapeType.Cone;
            sh.angle = fx.Angle;
            sh.radius = fx.Radius;
            var col = ps.colorOverLifetime;
            col.enabled = true;
            var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(Color.white, 1f) },
                      new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(1f, 0.12f), new GradientAlphaKey(0f, 1f) });
            col.color = g;
            var size = ps.sizeOverLifetime;
            size.enabled = fx.Grow != 1f;
            size.size = new ParticleSystem.MinMaxCurve(1f, AnimationCurve.Linear(0f, fx.Grow < 1f ? 1f : 0.5f, 1f, fx.Grow));
            var rot = ps.rotationOverLifetime;
            rot.enabled = !fx.Stretch;
            rot.z = new ParticleSystem.MinMaxCurve(-0.6f, 0.6f);
            var pr = t.GetComponent<ParticleSystemRenderer>();
            pr.sharedMaterial = fx.Mat;
            pr.renderMode = fx.Stretch ? ParticleSystemRenderMode.Stretch : ParticleSystemRenderMode.Billboard;
            if (fx.Stretch) { pr.velocityScale = 0.04f; pr.lengthScale = 1f; }
            pr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            pr.receiveShadows = false;
        }
    }

    [MenuItem("FerroEngrenagem/2. Build Prefabs")]
    public static void BuildPrefabs()
    {
        Directory.CreateDirectory(Path.Combine(ProjectRoot, PrefabDir));
        EffectMaterials();
        foreach (var b in Blocks)
        {
            var model = AssetDatabase.LoadAssetAtPath<GameObject>($"{ModelsDir}/{b}.fbx");
            if (model == null) { Debug.LogError($"[FE] FBX not imported: {b}"); continue; }

            var root = new GameObject(b + "Prefab") { layer = BlockLayer, tag = BlockTag };
            var inst = (GameObject)PrefabUtility.InstantiatePrefab(model);
            PrefabUtility.UnpackPrefabInstance(inst, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
            inst.name = b;
            inst.transform.SetParent(root.transform, false);
            inst.transform.localPosition = new Vector3(0f, -0.5f, 0f);
            ApplyMaterials(inst, HdMaterial(b));
            // falling metal streams only show while metal flows (FxVisual); hidden before the collider is measured
            foreach (var t in inst.GetComponentsInChildren<Transform>(true))
                if (t.name.StartsWith("FePour")) t.gameObject.SetActive(false);

            // Powered blocks: TileEntityPowered.set_BlockTransform uses blockTransform.Find("WireOffset"),
            // i.e. a DIRECT child of the prefab root, as the wire anchor. Move it up there.
            // Blender renames a second "WireOffset" in the same .blend to "WireOffset.001": accept any of them.
            var wire = FindDeep(inst.transform, "WireOffset") ?? FindPrefix(inst.transform, "WireOffset");
            Vector3 wirePos;
            if (wire == null && WireFallback.TryGetValue(b, out wirePos))
            {
                // models made before the WireOffset contract: an anchor at a fixed place (model space, Unity axes)
                wire = new GameObject("WireOffset").transform;
                wire.SetParent(inst.transform, false);
                wire.localPosition = wirePos;
            }
            if (wire != null) wire.name = "WireOffset";
            if (wire != null) wire.SetParent(root.transform, true);

            // One solid box around everything that renders, in root space.
            // optional joint pieces that reach into the next block (shown by Belt.cs) do not size the collider
            var rends = root.GetComponentsInChildren<Renderer>()
                .Where(r => !OptionalParts.Any(o => r.name.StartsWith(o))).ToArray();
            if (rends.Length > 0)
            {
                var bounds = rends[0].bounds;
                foreach (var r in rends.Skip(1)) bounds.Encapsulate(r.bounds);
                // Keep the collider inside the block's own cells: placing a block runs
                // GameUtils.IsColliderWithinBlock (an OverlapBox on the TerrainCollision layer) on the target
                // cell, so a few cm sticking out (the Conveyor Stand's cradle, 0.09 up; a ramp's ends) forbid
                // placing anything there. Overhangs under 0.15 past a cell face (faces at k + 0.5 in root space)
                // are cut at that face, on every axis; real multi-cell models are kept.
                Vector3 lo = root.transform.InverseTransformPoint(bounds.min);
                Vector3 hi = root.transform.InverseTransformPoint(bounds.max);
                for (int a = 0; a < 3; a++)
                {
                    hi[a] = Mathf.Min(hi[a], Mathf.Ceil(hi[a] - 0.65f) + 0.5f);
                    lo[a] = Mathf.Max(lo[a], Mathf.Floor(lo[a] + 0.65f) - 0.5f);
                }
                var col = root.AddComponent<BoxCollider>();
                col.center = (lo + hi) / 2f;
                col.size = hi - lo;
                Debug.Log($"[FE] {b}: collider center {col.center} size {col.size}");
            }
            AddParticles(root.transform);   // after the collider: particle renderers must not size it

            // Spinning parts (KineticSpinner turns them around their local +Z): log where they sit and where their
            // +Z points in prefab-root space, to check the Blender -> FBX -> Unity axis conversion.
            foreach (var t in root.GetComponentsInChildren<Transform>(true))
            {
                if (!t.name.StartsWith("FeSpin") && !t.name.EndsWith("_Rotor")) continue;
                var p = root.transform.InverseTransformPoint(t.position);
                var z = root.transform.InverseTransformDirection(t.forward);
                Debug.Log($"[FE] {b}: spin part {t.name} at ({p.x:0.00}, {p.y:0.00}, {p.z:0.00}) +Z -> ({z.x:0.00}, {z.y:0.00}, {z.z:0.00})");
            }

            var path = $"{PrefabDir}/{root.name}.prefab";
            PrefabUtility.SaveAsPrefabAsset(root, path);
            Object.DestroyImmediate(root);
            AssetImporter.GetAtPath(path).assetBundleName = BundleName;
            Debug.Log($"[FE] prefab {path}");
        }
        AssetDatabase.SaveAssets();
    }

    static Transform FindPrefix(Transform t, string prefix)
    {
        if (t.name.StartsWith(prefix)) return t;
        for (int i = 0; i < t.childCount; i++)
        {
            var r = FindPrefix(t.GetChild(i), prefix);
            if (r != null) return r;
        }
        return null;
    }

    static Transform FindDeep(Transform t, string name)
    {
        if (t.name == name) return t;
        for (int i = 0; i < t.childCount; i++)
        {
            var r = FindDeep(t.GetChild(i), name);
            if (r != null) return r;
        }
        return null;
    }

    [MenuItem("FerroEngrenagem/3. Build Bundle")]
    public static void BuildBundle()
    {
        var tmp = Path.Combine(ProjectRoot, "Build", "Bundles");
        Directory.CreateDirectory(tmp);
        BuildPipeline.BuildAssetBundles(tmp, BuildAssetBundleOptions.ChunkBasedCompression,
                                        BuildTarget.StandaloneWindows64);
        Directory.CreateDirectory(OutDir);
        var src = Path.Combine(tmp, BundleName);
        File.Copy(src, Path.Combine(OutDir, BundleName), true);
        Debug.Log($"[FE] bundle -> {Path.Combine(OutDir, BundleName)} ({new FileInfo(src).Length} bytes)");
    }
}
