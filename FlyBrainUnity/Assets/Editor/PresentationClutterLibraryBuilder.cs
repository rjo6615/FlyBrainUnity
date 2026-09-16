using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using FlyBrain.UnityBridge;
using UnityEditor;
using UnityEngine;

/// <summary>Build-time extraction of renderer-only decoration from imported model assets.</summary>
[InitializeOnLoad]
public static class PresentationClutterLibraryBuilder
{
    const string Root = "Assets/Art/Clutter";
    const string Output = Root + "/GeneratedPrefabs";
    const string Materials = Output + "/Materials";
    const string LibraryPath = "Assets/Resources/FlyBrainVisualLibrary.asset";
    static readonly string[] Categories = { "Rocks", "Leaves", "Twigs", "Organic" };
    // The order is significant.  In particular, never load a Blender source when an
    // exported FBX with the same category/name is available.
    static readonly string[] ModelExtensions = { ".fbx", ".obj", ".dae", ".3ds", ".blend" };

    static PresentationClutterLibraryBuilder()
    {
        EditorApplication.playModeStateChanged += state =>
        {
            if (state != PlayModeStateChange.ExitingEditMode) return;
            var library = AssetDatabase.LoadAssetAtPath<VisualPrefabLibrary>(LibraryPath);
            if (library != null && library.ClutterPrefabCount > 0) return;
            Debug.LogWarning("[FlyBrain Clutter Builder] The serialized library has zero valid prefabs. " +
                "Building it now before Play Mode so runtime cannot silently use empty lists.");
            Build();
        };
    }

    [MenuItem("Tools/FlyBrain/Build Clutter Library")]
    public static void Build()
    {
        EnsureFolder(Output); EnsureFolder(Materials);
        var sources = DiscoverSources();
        var fbxSources = sources.Where(s => s.Extension == ".fbx").ToArray();
        var acceptedFbx = 0; var created = 0; var rejected = new List<string>();
        var result = Categories.ToDictionary(c => c, _ => new List<GameObject>());
        var vegetation = new List<GameObject>();

        foreach (var sourceInfo in sources)
        {
            var path = sourceInfo.Path;
            ConfigureImporter(path);
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (model == null)
            {
                var blenderHint = Path.GetExtension(path).Equals(".blend", StringComparison.OrdinalIgnoreCase)
                    ? " Unity cannot convert this .blend file. Install a Blender version supported by this Unity Editor, " +
                      "restart Unity, and reimport the asset; alternatively export the source as FBX."
                    : string.Empty;
                rejected.Add($"{path}: Unity did not import a GameObject hierarchy.{blenderHint}");
                Debug.LogError($"[FlyBrain Clutter Builder] Import failed: {path}.{blenderHint}");
                continue;
            }
            GameObject prefab;
            string reason;
            try { prefab = Extract(path, model, out reason); }
            catch (Exception exception)
            {
                prefab = null;
                reason = $"prefab extraction threw {exception.GetType().Name}: {exception.Message}";
                Debug.LogException(exception);
            }
            if (prefab == null) { rejected.Add($"{path}: {reason}"); continue; }
            if (sourceInfo.Extension == ".fbx") acceptedFbx++;
            created++;
            if (sourceInfo.Category == "Organic" && IsVegetation(path)) vegetation.Add(prefab);
            else result[sourceInfo.Category].Add(prefab);
        }

        var library = AssetDatabase.LoadAssetAtPath<VisualPrefabLibrary>(LibraryPath);
        if (library == null)
        {
            EnsureFolder("Assets/Resources");
            library = ScriptableObject.CreateInstance<VisualPrefabLibrary>();
            AssetDatabase.CreateAsset(library, LibraryPath);
        }
        library.rocks.prefabs = result["Rocks"].ToArray();
        library.leaves.prefabs = result["Leaves"].ToArray();
        library.twigs.prefabs = result["Twigs"].ToArray();
        library.organicDebris.prefabs = result["Organic"].ToArray();
        library.largeVegetation.prefabs = vegetation.ToArray();
        ApplyNaturalDefaults(library);
        EditorUtility.SetDirty(library); AssetDatabase.SaveAssets(); AssetDatabase.Refresh();

        // Reload the serialized object rather than trusting the in-memory instance.
        library = AssetDatabase.LoadAssetAtPath<VisualPrefabLibrary>(LibraryPath);
        var assigned = result.Values.Sum(list => list.Count) + vegetation.Count;
        var summary = "=== FlyBrain Clutter Build ===\n\n" +
            $"FBX sources discovered: {fbxSources.Length}\nFBX sources accepted: {acceptedFbx}\n" +
            $"FBX sources rejected: {fbxSources.Length - acceptedFbx}\n\n" +
            $"Preferred sources discovered: {sources.Count}\nSources rejected: {rejected.Count}\n" +
            $"Generated prefabs: {created}\n\nRocks assigned: {result["Rocks"].Count}\n" +
            $"Leaves assigned: {result["Leaves"].Count}\nTwigs assigned: {result["Twigs"].Count}\n" +
            $"Organic assigned: {result["Organic"].Count}\nVegetation assigned: {vegetation.Count}\n\n" +
            $"Saved library:\n{LibraryPath}\nSerialized prefab references verified: {library?.ClutterPrefabCount ?? 0}" +
            (sources.SelectMany(s => s.Ignored).Any() ? "\n\nIgnored lower-priority duplicates:\n  " +
                string.Join("\n  ", sources.SelectMany(s => s.Ignored)) : string.Empty) +
            (rejected.Count == 0 ? "\n\nRejected: none" : "\n\nRejected:\n  " + string.Join("\n  ", rejected));
        if (created == 0)
            Debug.LogError(summary + "\n\nERROR: Generated prefabs = 0. The library was not built; inspect the import failures above.");
        else if (assigned == 0 || library == null || library.ClutterPrefabCount != assigned)
            Debug.LogError(summary + $"\n\nERROR: Expected {assigned} serialized prefab references, but reloaded " +
                $"{library?.ClutterPrefabCount ?? 0} from the library asset.");
        else Debug.Log(summary);
        Validate();
    }

    [MenuItem("Tools/FlyBrain/Validate Clutter Library")]
    public static void Validate()
    {
        var library = AssetDatabase.LoadAssetAtPath<VisualPrefabLibrary>(LibraryPath);
        if (library == null) { Debug.LogError($"[Presentation Clutter] Missing {LibraryPath}. Run Build Clutter Library."); return; }
        var warnings = new List<string>();
        ValidateCategory("Rocks", library.rocks, warnings);
        ValidateCategory("Leaves", library.leaves, warnings);
        ValidateCategory("Twigs", library.twigs, warnings);
        ValidateCategory("Organic", library.organicDebris, warnings);
        ValidateCategory("Large Vegetation", library.largeVegetation, warnings);
        var report = "Presentation Clutter Library\n\n" + Report(library);
        if (warnings.Count == 0) Debug.Log(report + "\nValidation passed: renderer-only prefabs and URP materials are ready.");
        else Debug.LogWarning(report + "\nWarnings:\n  " + string.Join("\n  ", warnings));
    }

    [MenuItem("Tools/FlyBrain/Regenerate Clutter")]
    public static void Regenerate()
    {
        Build();
        if (!EditorApplication.isPlaying) { Debug.Log("[Presentation Clutter] Assets regenerated. Enter Play Mode to scatter them."); return; }
        foreach (var bridge in UnityEngine.Object.FindObjectsByType<UnityFlyBridge>(FindObjectsSortMode.None))
            bridge.RegeneratePresentationClutter();
    }

    static GameObject Extract(string sourcePath, GameObject source, out string reason)
    {
        var clone = UnityEngine.Object.Instantiate(source);
        clone.name = Path.GetFileNameWithoutExtension(sourcePath);
        foreach (var renderer in clone.GetComponentsInChildren<Renderer>(true))
            if (IsPreview(renderer.gameObject.name)) UnityEngine.Object.DestroyImmediate(renderer.gameObject);

        foreach (var renderer in clone.GetComponentsInChildren<Renderer>(true))
            if (!HasRenderableMesh(renderer)) UnityEngine.Object.DestroyImmediate(renderer);

        foreach (var component in clone.GetComponentsInChildren<Component>(true).Reverse())
            if (component != null && component is not Transform && component is not Renderer && component is not MeshFilter)
                UnityEngine.Object.DestroyImmediate(component);
        var requiredTransforms = new HashSet<Transform>();
        foreach (var renderer in clone.GetComponentsInChildren<Renderer>(true))
        {
            AddAncestors(renderer.transform, clone.transform, requiredTransforms);
            if (renderer is SkinnedMeshRenderer skinned)
                foreach (var bone in skinned.bones.Where(bone => bone != null))
                    AddAncestors(bone, clone.transform, requiredTransforms);
        }
        RemoveEmptyBranches(clone.transform, requiredTransforms);
        var renderers = clone.GetComponentsInChildren<Renderer>(true);
        if (renderers.Length == 0)
        {
            UnityEngine.Object.DestroyImmediate(clone); reason = "no usable renderers after cameras/lights/helpers/preview shapes were removed"; return null;
        }
        if (renderers.Any(r => r.sharedMaterials.Length == 0 || r.sharedMaterials.Any(m => m == null)))
            Debug.LogWarning($"[Presentation Clutter Builder] {sourcePath}: one or more mesh slots had no material; assigning a generated URP material.");
        var material = BuildMaterial(sourcePath, renderers);
        foreach (var renderer in renderers)
        {
            var count = Math.Max(1, renderer.sharedMaterials.Length);
            renderer.sharedMaterials = Enumerable.Repeat(material, count).ToArray();
            renderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On;
            renderer.receiveShadows = true;
        }
        var prefabPath = $"{Output}/{Sanitize(clone.name)}.prefab";
        var prefab = PrefabUtility.SaveAsPrefabAsset(clone, prefabPath);
        var meshes = renderers.Select(RendererMesh).Where(mesh => mesh != null).ToArray();
        Debug.Log($"[FlyBrain Clutter Builder] Accepted {sourcePath}: {renderers.Length} renderer(s), " +
            $"{meshes.Length} mesh(es), {meshes.Sum(mesh => mesh.vertexCount)} vertices; material {AssetDatabase.GetAssetPath(material)}.");
        UnityEngine.Object.DestroyImmediate(clone);
        reason = null;
        return prefab;
    }

    static bool HasRenderableMesh(Renderer renderer) => RendererMesh(renderer) != null;
    static Mesh RendererMesh(Renderer renderer)
    {
        if (renderer is SkinnedMeshRenderer skinned) return skinned.sharedMesh;
        return renderer is MeshRenderer && renderer.TryGetComponent<MeshFilter>(out var filter) ? filter.sharedMesh : null;
    }

    static Material BuildMaterial(string sourcePath, Renderer[] renderers)
    {
        var name = Path.GetFileNameWithoutExtension(sourcePath);
        var path = $"{Materials}/{Sanitize(name)}_URP.mat";
        var material = AssetDatabase.LoadAssetAtPath<Material>(path);
        var shader = Shader.Find("Universal Render Pipeline/Lit");
        if (shader == null) throw new InvalidOperationException("Universal Render Pipeline/Lit shader was not found");
        if (material == null)
        {
            material = new Material(shader) { name = name + " URP" };
            AssetDatabase.CreateAsset(material, path);
        }
        else material.shader = shader;

        var imported = renderers.SelectMany(r => r.sharedMaterials).FirstOrDefault(m => m != null);
        if (imported != null) material.SetColor("_BaseColor", imported.HasProperty("_Color") ? imported.color : Color.white);
        var stem = name.Replace("_4k", "");
        var diffuse = FindTexture(stem, "diff"); var normal = FindTexture(stem, "nor");
        var roughness = FindTexture(stem, "rough"); var occlusion = FindTexture(stem, "ao");
        var opacity = FindTexture(stem, "opacity") ?? FindTexture(stem, "alpha");
        var baseMap = opacity != null && diffuse != null ? BuildCutoutTexture(name, diffuse, opacity) : diffuse;
        if (baseMap != null) material.SetTexture("_BaseMap", baseMap);
        if (normal != null)
        {
            ConfigureNormalMap(normal); material.SetTexture("_BumpMap", normal); material.EnableKeyword("_NORMALMAP");
        }
        material.SetFloat("_Metallic", 0f); material.SetFloat("_Smoothness", .22f);
        if (roughness != null)
        {
            var metallicSmoothness = BuildMetallicSmoothnessTexture(name, roughness);
            material.SetTexture("_MetallicGlossMap", metallicSmoothness);
            material.EnableKeyword("_METALLICSPECGLOSSMAP");
        }
        if (occlusion != null)
        {
            material.SetTexture("_OcclusionMap", occlusion); material.SetFloat("_OcclusionStrength", 1f);
            material.EnableKeyword("_OCCLUSIONMAP");
        }
        if (opacity != null || IsVegetation(sourcePath))
        {
            // URP/Lit alpha clipping reads the combined base-color alpha generated above.
            material.SetFloat("_AlphaClip", 1f); material.SetFloat("_Cutoff", .35f);
            material.EnableKeyword("_ALPHATEST_ON"); material.renderQueue = (int)UnityEngine.Rendering.RenderQueue.AlphaTest;
            material.doubleSidedGI = true; material.SetFloat("_Cull", 0f);
        }
        EditorUtility.SetDirty(material); return material;
    }

    static Texture2D BuildMetallicSmoothnessTexture(string name, Texture2D roughness)
    {
        var path = $"{Materials}/{Sanitize(name)}_MetallicSmoothness.png";
        var wasReadable = IsReadable(roughness); SetReadable(roughness, true);
        var pixels = roughness.GetPixels32();
        for (var i = 0; i < pixels.Length; i++)
        {
            var smoothness = (byte)(255 - pixels[i].r);
            pixels[i] = new Color32(0, 0, 0, smoothness);
        }
        var packed = new Texture2D(roughness.width, roughness.height, TextureFormat.RGBA32, true);
        packed.SetPixels32(pixels); packed.Apply(); File.WriteAllBytes(path, packed.EncodeToPNG());
        UnityEngine.Object.DestroyImmediate(packed); SetReadable(roughness, wasReadable);
        AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
        return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
    }

    static Texture2D BuildCutoutTexture(string name, Texture2D color, Texture2D opacity)
    {
        var path = $"{Materials}/{Sanitize(name)}_BaseColorAlpha.png";
        var colorWasReadable = IsReadable(color); var opacityWasReadable = IsReadable(opacity);
        SetReadable(color, true); SetReadable(opacity, true);
        var width = color.width; var height = color.height;
        var colors = color.GetPixels32();
        var mask = opacity.GetPixels32();
        for (var y = 0; y < height; y++) for (var x = 0; x < width; x++)
        {
            var mi = Mathf.Clamp(y * opacity.height / height, 0, opacity.height - 1) * opacity.width +
                     Mathf.Clamp(x * opacity.width / width, 0, opacity.width - 1);
            var ci = y * width + x; colors[ci].a = mask[mi].r;
        }
        var combined = new Texture2D(width, height, TextureFormat.RGBA32, true);
        combined.SetPixels32(colors); combined.Apply();
        File.WriteAllBytes(path, combined.EncodeToPNG()); UnityEngine.Object.DestroyImmediate(combined);
        SetReadable(color, colorWasReadable); SetReadable(opacity, opacityWasReadable);
        AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
        return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
    }

    static void SetReadable(Texture2D texture, bool value)
    {
        var path = AssetDatabase.GetAssetPath(texture);
        if (AssetImporter.GetAtPath(path) is TextureImporter importer && importer.isReadable != value)
        { importer.isReadable = value; importer.SaveAndReimport(); }
    }

    static bool IsReadable(Texture2D texture) =>
        AssetImporter.GetAtPath(AssetDatabase.GetAssetPath(texture)) is TextureImporter importer && importer.isReadable;

    static void ConfigureNormalMap(Texture2D texture)
    {
        if (AssetImporter.GetAtPath(AssetDatabase.GetAssetPath(texture)) is not TextureImporter importer ||
            importer.textureType == TextureImporterType.NormalMap) return;
        importer.textureType = TextureImporterType.NormalMap; importer.SaveAndReimport();
    }

    static Texture2D FindTexture(string stem, string token)
    {
        var normalized = stem.ToLowerInvariant();
        return AssetDatabase.FindAssets("t:Texture2D", new[] { Root + "/textures" })
            .Select(AssetDatabase.GUIDToAssetPath)
            .Where(p => Path.GetFileNameWithoutExtension(p).ToLowerInvariant().StartsWith(normalized) &&
                        Path.GetFileNameWithoutExtension(p).ToLowerInvariant().Contains(token))
            .Select(AssetDatabase.LoadAssetAtPath<Texture2D>).FirstOrDefault(t => t != null);
    }

    static List<SourceInfo> DiscoverSources()
    {
        var discovered = new List<SourceInfo>();
        foreach (var category in Categories)
        {
            var candidates = AssetDatabase.FindAssets("", new[] { $"{Root}/{category}" })
                .Select(AssetDatabase.GUIDToAssetPath)
                .Where(path => ModelExtensions.Contains(Path.GetExtension(path).ToLowerInvariant()))
                .GroupBy(path => Path.GetFileNameWithoutExtension(path), StringComparer.OrdinalIgnoreCase);
            foreach (var group in candidates)
            {
                var ordered = group.OrderBy(path => Array.IndexOf(ModelExtensions,
                    Path.GetExtension(path).ToLowerInvariant())).ThenBy(path => path, StringComparer.Ordinal).ToArray();
                discovered.Add(new SourceInfo(category, ordered[0], ordered.Skip(1).ToArray()));
            }
        }
        return discovered.OrderBy(source => Array.IndexOf(Categories, source.Category))
            .ThenBy(source => source.Path, StringComparer.Ordinal).ToList();
    }

    sealed class SourceInfo
    {
        public readonly string Category;
        public readonly string Path;
        public readonly string Extension;
        public readonly string[] Ignored;

        public SourceInfo(string category, string path, string[] ignored)
        {
            Category = category; Path = path;
            Extension = System.IO.Path.GetExtension(path).ToLowerInvariant();
            Ignored = ignored;
        }
    }

    static void ConfigureImporter(string path)
    {
        if (AssetImporter.GetAtPath(path) is not ModelImporter importer) return;
        var changed = importer.importCameras || importer.importLights || importer.addCollider || importer.importAnimation;
        importer.importCameras = false; importer.importLights = false; importer.addCollider = false; importer.importAnimation = false;
        if (changed) importer.SaveAndReimport();
    }

    static void ValidateCategory(string name, ClutterCategory category, List<string> warnings)
    {
        var prefabs = category?.prefabs ?? Array.Empty<GameObject>();
        if (prefabs.Length == 0) warnings.Add($"{name}: empty category");
        foreach (var prefab in prefabs)
        {
            if (prefab == null) { warnings.Add($"{name}: missing prefab or source asset"); continue; }
            var prefabPath = AssetDatabase.GetAssetPath(prefab);
            if (string.IsNullOrEmpty(prefabPath) || !prefabPath.StartsWith(Output + "/", StringComparison.Ordinal))
                warnings.Add($"{name}/{prefab.name}: reference is not a generated prefab asset");
            if (!SourceExists(prefab.name)) warnings.Add($"{name}/{prefab.name}: missing source asset");
            var renderers = prefab.GetComponentsInChildren<Renderer>(true);
            if (renderers.Length == 0) { warnings.Add($"{name}/{prefab.name}: missing renderer"); continue; }
            foreach (var renderer in renderers)
            {
                if (!HasRenderableMesh(renderer)) warnings.Add($"{name}/{prefab.name}: renderer has no mesh");
                foreach (var material in renderer.sharedMaterials)
                    if (material == null) warnings.Add($"{name}/{prefab.name}: missing material");
                    else if (material.shader == null || !material.shader.name.StartsWith("Universal Render Pipeline/"))
                        warnings.Add($"{name}/{prefab.name}: incompatible shader '{material.shader?.name ?? "missing"}'");
            }
            var bounds = CombinedLocalBounds(prefab);
            if (bounds.size.sqrMagnitude < 1e-10f || bounds.size.magnitude > 100000f)
                warnings.Add($"{name}/{prefab.name}: absurd native bounds {bounds.size}");
        }
    }

    static Bounds CombinedLocalBounds(GameObject prefab)
    {
        var clone = UnityEngine.Object.Instantiate(prefab); clone.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
        var rs = clone.GetComponentsInChildren<Renderer>(true); var b = rs.Length == 0 ? default : rs[0].bounds;
        for (var i = 1; i < rs.Length; i++) b.Encapsulate(rs[i].bounds);
        UnityEngine.Object.DestroyImmediate(clone); return b;
    }

    static string Report(VisualPrefabLibrary library) =>
        CategoryReport("Rocks", library.rocks) + CategoryReport("Leaves", library.leaves) +
        CategoryReport("Twigs", library.twigs) + CategoryReport("Organic", library.organicDebris) +
        CategoryReport("Large Vegetation", library.largeVegetation) +
        $"\nConfigured ranges: rocks {library.rocks.minimumCount}-{library.rocks.maximumCount}, leaves {library.leaves.minimumCount}-{library.leaves.maximumCount}, " +
        $"twigs {library.twigs.minimumCount}-{library.twigs.maximumCount}, organic {library.organicDebris.minimumCount}-{library.organicDebris.maximumCount}, vegetation {library.largeVegetation.minimumCount}-{library.largeVegetation.maximumCount}.";
    static string CategoryReport(string name, ClutterCategory c) =>
        $"{name}:\n  {(c?.prefabs?.Length ?? 0)} prefabs\n" + string.Concat((c?.prefabs ?? Array.Empty<GameObject>()).Where(p => p != null).Select(p => $"  {p.name}\n"));

    static void ApplyNaturalDefaults(VisualPrefabLibrary l)
    {
        Set(l.rocks, 7, 14, 3, 10, 10); Set(l.leaves, 6, 12, 2, 8, 12);
        Set(l.twigs, 2, 5, 3, 15, 7); Set(l.organicDebris, 5, 10, 1, 6, 10);
        Set(l.largeVegetation, 1, 2, 15, 40, 2);
        l.clutterClusterChance = .68f; l.clutterClusterRadiusMm = 8f;
    }
    static void Set(ClutterCategory c, int minCount, int maxCount, float minSize, float maxSize, float tilt)
    { c.enabled = true; c.minimumCount = minCount; c.maximumCount = maxCount; c.minimumVisualSizeMm = minSize; c.maximumVisualSizeMm = maxSize; c.randomTiltDegrees = tilt; }

    static bool IsVegetation(string path) { var s = path.ToLowerInvariant(); return s.Contains("plant") || s.Contains("shrub") || s.Contains("fern") || s.Contains("flower") || s.Contains("vegetation"); }
    static bool SourceExists(string prefabName) => AssetDatabase.FindAssets("", Categories.Select(c => $"{Root}/{c}").ToArray())
        .Select(AssetDatabase.GUIDToAssetPath).Any(p => ModelExtensions.Contains(Path.GetExtension(p).ToLowerInvariant()) &&
                                                   Path.GetFileNameWithoutExtension(p) == prefabName);
    static bool IsPreview(string name) { var n = name.ToLowerInvariant(); return n == "plane" || n == "sphere" || n.Contains("preview") || n.Contains("material_ball") || n.Contains("uv_sphere"); }
    static string Sanitize(string value) => string.Concat(value.Select(c => char.IsLetterOrDigit(c) || c == '_' || c == '-' ? c : '_'));
    static void AddAncestors(Transform transform, Transform root, HashSet<Transform> required)
    {
        while (transform != null)
        {
            required.Add(transform);
            if (transform == root) break;
            transform = transform.parent;
        }
    }
    static void RemoveEmptyBranches(Transform parent, HashSet<Transform> required)
    {
        for (var i = parent.childCount - 1; i >= 0; i--)
        {
            var child = parent.GetChild(i); RemoveEmptyBranches(child, required);
            if (!required.Contains(child)) UnityEngine.Object.DestroyImmediate(child.gameObject);
        }
    }
    static void EnsureFolder(string path)
    {
        var parts = path.Split('/'); var current = parts[0];
        for (var i = 1; i < parts.Length; i++) { var next = current + "/" + parts[i]; if (!AssetDatabase.IsValidFolder(next)) AssetDatabase.CreateFolder(current, parts[i]); current = next; }
    }
}
