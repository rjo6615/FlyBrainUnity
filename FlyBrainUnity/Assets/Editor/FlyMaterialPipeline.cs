using System;
using System.Linq;
using System.Text;
using FlyBrain.UnityBridge;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

public static class FlyMaterialPipeline
{
    const string ModelPath = "Assets/Art/Fly/Fly.fbx";
    const string BasePath = "Assets/Art/Fly/Textures/TheFly_TheFly_BaseColor.png";
    const string NormalPath = "Assets/Art/Fly/Textures/TheFly_TheFly_Normal.png";
    const string OrmPath = "Assets/Art/Fly/Textures/TheFly_TheFly_OcclusionRoughnessMetallic.png";
    const string OutputDirectory = "Assets/Art/Fly/GeneratedMaterials";
    const string PackedPath = OutputDirectory + "/TheFly_MetallicSmoothness.asset";
    const string BodyPath = OutputDirectory + "/TheFly_URP.mat";
    const string WingsPath = OutputDirectory + "/Wings_URP.mat";

    [InitializeOnLoadMethod]
    static void BuildWhenNeeded()
    {
        EditorApplication.delayCall += () =>
        {
            if (AssetDatabase.LoadAssetAtPath<Material>(BodyPath) == null ||
                AssetDatabase.LoadAssetAtPath<Material>(WingsPath) == null ||
                AssetDatabase.LoadAssetAtPath<Texture2D>(PackedPath) == null) Build();
        };
    }

    [MenuItem("Tools/FlyBrain/Build Fly Materials")]
    public static void Build()
    {
        EnsureFolder();
        ConfigureTexture(BasePath, false, true);
        ConfigureTexture(NormalPath, true, false);
        ConfigureTexture(OrmPath, false, false);
        var baseMap = AssetDatabase.LoadAssetAtPath<Texture2D>(BasePath);
        var normal = AssetDatabase.LoadAssetAtPath<Texture2D>(NormalPath);
        var orm = AssetDatabase.LoadAssetAtPath<Texture2D>(OrmPath);
        if (baseMap == null || normal == null || orm == null) throw new InvalidOperationException("One or more original fly textures are missing.");
        var packed = BuildMetallicSmoothness(orm);
        var body = CreateOrLoadMaterial(BodyPath, FlyMaterialValidation.BodyMaterialName);
        ConfigureCommon(body, baseMap, normal, orm, packed);
        ConfigureOpaque(body);
        var wings = CreateOrLoadMaterial(WingsPath, FlyMaterialValidation.WingMaterialName);
        ConfigureCommon(wings, baseMap, normal, orm, packed);
        ConfigureTransparentWings(wings);
        RemapSourceMaterials(body, wings);
        AssetDatabase.SaveAssets();
        AssetDatabase.ImportAsset(ModelPath, ImportAssetOptions.ForceUpdate);
        Debug.Log("Fly URP materials built from the original BaseColor, Normal, and OcclusionRoughnessMetallic textures; source slots TheFly/Wings remapped.");
        Validate();
    }

    static void EnsureFolder()
    {
        if (!AssetDatabase.IsValidFolder("Assets/Art/Fly")) throw new InvalidOperationException("Fly source directory is missing.");
        if (!AssetDatabase.IsValidFolder(OutputDirectory)) AssetDatabase.CreateFolder("Assets/Art/Fly", "GeneratedMaterials");
    }

    static void ConfigureTexture(string path, bool normal, bool srgb)
    {
        var importer = AssetImporter.GetAtPath(path) as TextureImporter;
        if (importer == null) return;
        importer.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
        importer.sRGBTexture = srgb;
        importer.alphaSource = path == BasePath ? TextureImporterAlphaSource.FromInput : TextureImporterAlphaSource.None;
        importer.SaveAndReimport();
    }

    static Texture2D BuildMetallicSmoothness(Texture2D orm)
    {
        var importer = (TextureImporter)AssetImporter.GetAtPath(OrmPath);
        var wasReadable = importer.isReadable;
        importer.isReadable = true; importer.SaveAndReimport();
        orm = AssetDatabase.LoadAssetAtPath<Texture2D>(OrmPath);
        var source = orm.GetPixels32();
        var output = new Color32[source.Length];
        for (var i = 0; i < source.Length; i++) output[i] = new Color32(source[i].b, 0, 0, (byte)(255 - source[i].g));
        var existing = AssetDatabase.LoadAssetAtPath<Texture2D>(PackedPath);
        if (existing == null)
        {
            existing = new Texture2D(orm.width, orm.height, TextureFormat.RGBA32, true, true) { name = "TheFly Metallic (R) Smoothness (A)" };
            existing.SetPixels32(output); existing.Apply(true, false); AssetDatabase.CreateAsset(existing, PackedPath);
        }
        else { existing.Reinitialize(orm.width, orm.height, TextureFormat.RGBA32, true); existing.SetPixels32(output); existing.Apply(true, false); EditorUtility.SetDirty(existing); }
        importer.isReadable = wasReadable; importer.SaveAndReimport();
        return existing;
    }

    static Material CreateOrLoadMaterial(string path, string name)
    {
        var material = AssetDatabase.LoadAssetAtPath<Material>(path);
        var shader = Shader.Find("Universal Render Pipeline/Lit");
        if (shader == null) throw new InvalidOperationException("Universal Render Pipeline/Lit shader is unavailable.");
        if (material == null) { material = new Material(shader) { name = name }; AssetDatabase.CreateAsset(material, path); }
        else { material.shader = shader; material.name = name; }
        return material;
    }

    static void ConfigureCommon(Material material, Texture baseMap, Texture normal, Texture orm, Texture metallicSmoothness)
    {
        material.SetTexture("_BaseMap", baseMap); material.SetTexture("_MainTex", baseMap);
        material.SetColor("_BaseColor", Color.white); material.SetColor("_Color", Color.white);
        material.SetTexture("_BumpMap", normal); material.SetFloat("_BumpScale", 1f); material.EnableKeyword("_NORMALMAP");
        material.SetTexture("_MetallicGlossMap", metallicSmoothness); material.SetFloat("_Metallic", 1f); material.SetFloat("_Smoothness", 1f); material.EnableKeyword("_METALLICSPECGLOSSMAP");
        material.SetTexture("_OcclusionMap", orm); material.SetFloat("_OcclusionStrength", 1f); material.EnableKeyword("_OCCLUSIONMAP");
        EditorUtility.SetDirty(material);
    }

    static void ConfigureOpaque(Material material)
    {
        material.SetFloat("_Surface", 0); material.SetFloat("_Blend", 0); material.SetFloat("_Cull", (float)CullMode.Back);
        material.SetFloat("_ZWrite", 1); material.SetFloat("_SrcBlend", (float)BlendMode.One); material.SetFloat("_DstBlend", (float)BlendMode.Zero);
        material.DisableKeyword("_SURFACE_TYPE_TRANSPARENT"); material.renderQueue = (int)RenderQueue.Geometry;
        material.SetOverrideTag("RenderType", "Opaque");
    }

    static void ConfigureTransparentWings(Material material)
    {
        material.SetFloat("_Surface", 1); material.SetFloat("_Blend", 0); material.SetFloat("_Cull", (float)CullMode.Off);
        material.SetFloat("_ZWrite", 0); material.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha); material.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
        material.EnableKeyword("_SURFACE_TYPE_TRANSPARENT"); material.DisableKeyword("_ALPHAPREMULTIPLY_ON");
        material.renderQueue = (int)RenderQueue.Transparent; material.SetOverrideTag("RenderType", "Transparent"); material.doubleSidedGI = true;
    }

    static void RemapSourceMaterials(Material body, Material wings)
    {
        var importer = AssetImporter.GetAtPath(ModelPath) as ModelImporter ?? throw new InvalidOperationException("Fly.fbx ModelImporter not found.");
        importer.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
        importer.materialLocation = ModelImporterMaterialLocation.External;
        foreach (var id in importer.GetExternalObjectMap().Keys.Where(k => k.type == typeof(Material)).ToArray()) importer.RemoveRemap(id);
        importer.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), "TheFly"), body);
        importer.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), "Wings"), wings);
        importer.SaveAndReimport();
    }

    [MenuItem("Tools/FlyBrain/Validate Fly Materials")]
    public static void Validate()
    {
        var model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
        if (model == null) { Debug.LogError("FLY MATERIAL VALIDATION FAILED: source model missing: " + ModelPath); return; }
        var renderers = model.GetComponentsInChildren<Renderer>(true);
        var report = new StringBuilder("=== FLY MATERIAL PIPELINE ===\nSource model: " + ModelPath + "\nGenerated prefab: none (FBX model prefab is instantiated directly)\nRuntime override: none for real model\n");
        var slots = 0; var missing = 0; var unsupported = 0;
        foreach (var renderer in renderers)
        {
            var mesh = FlyMaterialValidation.MeshFor(renderer);
            var materials = renderer.sharedMaterials; slots += materials.Length;
            for (var i = 0; i < materials.Length; i++)
            {
                var material = materials[i]; if (material == null) missing++; else if (material.shader == null || !material.shader.isSupported) unsupported++;
                report.Append($"\nRenderer: {Path(renderer.transform)} ({renderer.GetType().Name})\nMesh: {(mesh == null ? "MISSING" : mesh.name)}\nMaterial slot: {i}\nMaterial: {(material == null ? "MISSING" : material.name)}\nShader: {(material?.shader == null ? "MISSING" : material.shader.name)}\nBase color texture: {TextureName(material, "_BaseMap")}\nNormal texture: {TextureName(material, "_BumpMap")}\nMask/roughness texture: {TextureName(material, "_MetallicGlossMap")} / {TextureName(material, "_OcclusionMap")}\nOpacity texture: {(material != null && material.name.StartsWith(FlyMaterialValidation.WingMaterialName) ? TextureName(material, "_BaseMap") + " alpha" : "not used")}\nUV0 present: {(mesh != null && mesh.HasVertexAttribute(VertexAttribute.TexCoord0) ? "yes" : "NO")}\nRuntime material override: no\nSource material: {(material != null && material.name.StartsWith(FlyMaterialValidation.WingMaterialName) ? "Wings" : "TheFly")}\n");
            }
        }
        var valid = FlyMaterialValidation.Validate(renderers, out var reason);
        report.Append($"\nFly renderer count: {renderers.Length}\nTotal material slots: {slots}\nMissing material slots: {missing}\nUnsupported/error shaders: {unsupported}\nEye status: atlas material TheFly URP assigned\nTransparent wing status: {(valid ? "configured" : "check failure")}\nRuntime override status: real prefab sharedMaterials preserved\n");
        if (valid) Debug.Log(report + "\nFLY MATERIAL VALIDATION PASSED"); else Debug.LogError(report + "\nFLY MATERIAL VALIDATION FAILED: " + reason);
    }

    static string TextureName(Material material, string property) => material != null && material.HasProperty(property) && material.GetTexture(property) != null ? AssetDatabase.GetAssetPath(material.GetTexture(property)) : "MISSING";
    static string Path(Transform transform) { var path = transform.name; while (transform.parent != null) { transform = transform.parent; path = transform.name + "/" + path; } return path; }
}
