using System;
using UnityEngine;

namespace FlyBrain.UnityBridge
{
    [Serializable]
    public sealed class VisualPrefabSlot
    {
        [Tooltip("Optional replacement. Leave empty to use the built-in scientific primitive.")]
        public GameObject prefab;
        [Tooltip("Optional presentation material. This can be used on either a custom prefab or the built-in scientific primitive.")]
        public Material material;
        [Tooltip("Applied only below the authoritative transform.")]
        public Vector3 modelScale = Vector3.one;
        public Vector3 modelRotationOffset;
        public Vector3 modelPositionOffset;
        [Tooltip("UV tiling applied to the optional material without changing any authoritative transform or geometry.")]
        public Vector2 materialTiling = Vector2.one;

        [Header("Visual grounding (presentation only)")]
        [Tooltip("Align this model's rendered bottom with the mirrored substrate without moving its authoritative parent.")]
        public bool autoGroundVisual;
        [Tooltip("Additional world-space height above the detected surface, after automatic grounding.")]
        public float groundingOffset;
        [Tooltip("Do not calibrate grounding when the authoritative root is farther above the surface than this. This preserves real flight/jump height.")]
        [Min(0f)] public float maximumGroundingRootHeight = .25f;
    }

    [Serializable]
    public sealed class ClutterCategory
    {
        public bool enabled = true;
        [Tooltip("Presentation-only prefabs. An empty list is valid and produces no clutter.")]
        public GameObject[] prefabs = Array.Empty<GameObject>();
        [Min(0)] public int minimumCount;
        [Min(0)] public int maximumCount;
        [Tooltip("Approximate longest rendered dimension, in real-world millimetres.")]
        [Min(.01f)] public float minimumVisualSizeMm = 1f;
        [Min(.01f)] public float maximumVisualSizeMm = 4f;
        [Tooltip("Presentation-only depth in millimetres that visible geometry is embedded below the substrate.")]
        [Min(0f)] public float groundingPenetrationMm = .05f;
        public bool randomRotation = true;
        [Range(0f, 45f)] public float randomTiltDegrees = 8f;
        [Tooltip("Optional presentation rotation fixes, matched by prefab reference before random yaw/tilt.")]
        public ClutterOrientationCorrection[] orientationCorrections = Array.Empty<ClutterOrientationCorrection>();
    }

    [Serializable]
    public sealed class ClutterOrientationCorrection
    {
        public GameObject prefab;
        public Vector3 eulerAngles;
    }

    /// <summary>Presentation-only assets and camera tuning. No value here changes wire/scientific state.</summary>
    [CreateAssetMenu(menuName = "Fly Brain/Visual Prefab Library", fileName = "FlyBrainVisualLibrary")]
    public sealed class VisualPrefabLibrary : ScriptableObject
    {
        [Header("Authoritative object type mappings")]
        public VisualPrefabSlot fly = new();
        public VisualPrefabSlot substrate = new();
        public VisualPrefabSlot wall = new();
        public VisualPrefabSlot predator = new();
        public VisualPrefabSlot sugar = new();
        public VisualPrefabSlot bitter = new();
        public VisualPrefabSlot foodOdor = new();
        public VisualPrefabSlot dangerOdor = new();

        [Header("Procedural clutter (presentation only)")]
        [Tooltip("Changing this value produces a different deterministic layout on the next run.")]
        public int clutterSeed = 164;
        public ClutterCategory rocks = new() { minimumCount = 20, maximumCount = 35,
            minimumVisualSizeMm = 1f, maximumVisualSizeMm = 7f, groundingPenetrationMm = .15f, randomTiltDegrees = 20f };
        public ClutterCategory leaves = new() { minimumCount = 20, maximumCount = 40,
            minimumVisualSizeMm = 2f, maximumVisualSizeMm = 8f, groundingPenetrationMm = .03f, randomTiltDegrees = 15f };
        public ClutterCategory twigs = new() { minimumCount = 10, maximumCount = 18,
            minimumVisualSizeMm = 3f, maximumVisualSizeMm = 15f, groundingPenetrationMm = .10f, randomTiltDegrees = 12f };
        public ClutterCategory organicDebris = new() { minimumCount = 15, maximumCount = 30,
            minimumVisualSizeMm = 1f, maximumVisualSizeMm = 6f, groundingPenetrationMm = .05f, randomTiltDegrees = 15f };
        [Tooltip("Sparse, larger presentation-only plants discovered in the Organic source folder.")]
        public ClutterCategory largeVegetation = new() { minimumCount = 4, maximumCount = 8,
            minimumVisualSizeMm = 8f, maximumVisualSizeMm = 25f, groundingPenetrationMm = .10f, randomTiltDegrees = 3f };
        [Tooltip("Tiny renderer-only gravel. The builder assigns reusable rock and organic-debris prefabs here.")]
        public ClutterCategory microDebris = new() { minimumCount = 25, maximumCount = 60,
            minimumVisualSizeMm = .3f, maximumVisualSizeMm = 1.5f, groundingPenetrationMm = .05f, randomTiltDegrees = 25f };
        [Range(0f, 1f), Tooltip("Chance that a debris item is positioned near an earlier item instead of uniformly.")]
        public float clutterClusterChance = .68f;
        [Min(.1f)] public float clutterClusterRadiusMm = 8f;
        [Min(0f)] public float clutterMinimumSeparationMm = .5f;
        [Min(0f)] public float wallClearanceMm = 1.5f;
        [Min(0f)] public float flyInitialClearanceMm = 4f;
        [Min(0f)] public float patchClearanceMm = 3f;
        [Min(0f)] public float odorClearanceMm = 2f;
        [Min(0f)] public float predatorClearanceMm = 5f;

        [Header("Camera controls (presentation only)")]
        [Min(.01f)] public float orbitSensitivity = .18f;
        [Tooltip("Percentage of the current camera distance changed by one mouse-wheel notch.")]
        [Range(1f, 50f)] public float zoomPercentagePerNotch = 20f;
        [Min(.001f)] public float panSensitivity = .0025f;
        [Tooltip("Closest distance while viewing the complete environment (Unity units).")]
        [Min(.001f)] public float minimumOverviewDistance = .01f;
        [Tooltip("Closest distance in Follow Fly mode (Unity units).")]
        [Min(.001f)] public float minimumFollowDistance = .008f;
        [Tooltip("Closest distance after focusing an object or the fly (Unity units).")]
        [Min(.0005f)] public float minimumFocusDistance = .003f;
        [Min(.1f)] public float maximumZoomDistance = 100f;
        [Range(-89f, 89f)] public float minimumPitch = -15f;
        [Range(-89f, 89f)] public float maximumPitch = 85f;
        [Min(.01f)] public float cameraSmoothTime = .08f;
        [Min(.01f)] public float focusTransitionTime = .25f;
        public bool showCameraHelp = true;

        [Header("Macro follow camera")]
        [Min(.05f)] public float followDistance = 1.15f;
        [Min(0f)] public float followHeight = .65f;
        [Min(0f)] public float lookAheadDistance = .35f;
        [Range(15f, 90f)] public float followFieldOfView = 42f;
        [Min(.01f)] public float followSmoothSeconds = .12f;

        public VisualPrefabSlot ForKind(string kind)
        {
            var key = (kind ?? string.Empty).ToLowerInvariant().Replace(':', '_');
            if (key == "substrate") return substrate;
            if (key == "wall" || key.StartsWith("wall_")) return wall;
            if (key == "predator") return predator;
            if (key == "taste_sugar") return sugar;
            if (key == "taste_bitter") return bitter;
            if (key == "odor_food" || key == "odor_attractive") return foodOdor;
            if (key == "odor_danger" || key == "odor_aversive") return dangerOdor;
            return null;
        }

        public static VisualPrefabLibrary LoadOrDefault()
        {
            var configured = Resources.Load<VisualPrefabLibrary>("FlyBrainVisualLibrary");
            if (configured != null)
            {
                Debug.Log($"[FlyBrain Clutter]\nLibrary: {configured.name} (Resources/FlyBrainVisualLibrary)\n" +
                    $"Rocks prefabs: {PrefabCount(configured.rocks)}\nLeaves prefabs: {PrefabCount(configured.leaves)}\n" +
                    $"Twigs prefabs: {PrefabCount(configured.twigs)}\nOrganic prefabs: {PrefabCount(configured.organicDebris)}\n" +
                    $"Vegetation prefabs: {PrefabCount(configured.largeVegetation)}\nMicro debris prefabs: {PrefabCount(configured.microDebris)}");
                return configured;
            }

            Debug.LogError("[FlyBrain Clutter] Resources/FlyBrainVisualLibrary could not be loaded. " +
                "The transient defaults contain no clutter prefabs; run Tools > FlyBrain > Build Clutter Library.");
            return CreateInstance<VisualPrefabLibrary>();
        }

        public int ClutterPrefabCount
        {
            get
            {
                var unique = new System.Collections.Generic.HashSet<GameObject>();
                foreach (var category in new[] { rocks, leaves, twigs, organicDebris, largeVegetation, microDebris })
                    foreach (var prefab in category?.prefabs ?? Array.Empty<GameObject>())
                        if (prefab != null && prefab.GetComponentInChildren<Renderer>(true) != null) unique.Add(prefab);
                return unique.Count;
            }
        }

        public int PrefabCountFor(ClutterCategory category) => PrefabCount(category);

        static int PrefabCount(ClutterCategory category)
        {
            if (category?.prefabs == null) return 0;
            var count = 0;
            foreach (var prefab in category.prefabs)
                if (prefab != null && prefab.GetComponentInChildren<Renderer>(true) != null) count++;
            return count;
        }
    }
}
