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
        "feDynamo2", "feBus", "feConveyor", "feConveyorRamp", "feFunnel", "feConveyorDown", "feFluidFiller", "feFluidBottler"
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
        foreach (var b in Blocks)
        {
            var src = Path.Combine(ArtDir, b, b + ".fbx");
            if (!File.Exists(src)) { Debug.LogError($"[FE] missing {src}"); continue; }
            File.Copy(src, Path.Combine(ProjectRoot, ModelsDir, b + ".fbx"), true);
        }
        AssetDatabase.Refresh();
    }

    [MenuItem("FerroEngrenagem/2. Build Prefabs")]
    public static void BuildPrefabs()
    {
        Directory.CreateDirectory(Path.Combine(ProjectRoot, PrefabDir));
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

            // Powered blocks: TileEntityPowered.set_BlockTransform uses blockTransform.Find("WireOffset"),
            // i.e. a DIRECT child of the prefab root, as the wire anchor. Move it up there.
            // Blender renames a second "WireOffset" in the same .blend to "WireOffset.001": accept any of them.
            var wire = FindDeep(inst.transform, "WireOffset") ?? FindPrefix(inst.transform, "WireOffset");
            if (wire != null) wire.name = "WireOffset";
            if (wire != null) wire.SetParent(root.transform, true);

            // One solid box around everything that renders, in root space.
            var rends = root.GetComponentsInChildren<Renderer>();
            if (rends.Length > 0)
            {
                var bounds = rends[0].bounds;
                foreach (var r in rends.Skip(1)) bounds.Encapsulate(r.bounds);
                var col = root.AddComponent<BoxCollider>();
                col.center = root.transform.InverseTransformPoint(bounds.center);
                col.size = bounds.size;
                Debug.Log($"[FE] {b}: collider center {col.center} size {col.size}");
            }

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
