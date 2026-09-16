using System.Collections.Generic;
using UnityEngine;

namespace FlyBrain.UnityBridge
{
    /// <summary>
    /// Decorative, renderer-only scatter. It never writes to the mirrored environment and
    /// deliberately creates no colliders, rigid bodies, or other simulation components.
    /// </summary>
    public sealed class PresentationClutterSystem
    {
        readonly Transform root;
        readonly UnityEnvironmentManager environment;
        readonly VisualPrefabLibrary settings;
        readonly List<PlacedDisc> placed = new();
        readonly Vector3 flyInitialPosition;
        readonly Dictionary<string, int> counts = new();

        struct PlacedDisc { public Vector2 center; public float radius; }

        public bool Visible { get; private set; } = true;
        public int ObjectCount { get; private set; }
        public bool LibraryLoaded => settings != null && settings.ClutterPrefabCount > 0;
        public int PrefabCount => settings?.ClutterPrefabCount ?? 0;
        public bool SubstrateReady { get; private set; }
        public bool GenerationAttempted { get; private set; }
        public string LastError { get; private set; } = "none";
        public int Count(string category) => counts.TryGetValue(category, out var count) ? count : 0;

        public PresentationClutterSystem(Transform parent, UnityEnvironmentManager environment,
            VisualPrefabLibrary settings, Vector3 flyInitialPosition)
        {
            this.environment = environment;
            this.settings = settings;
            this.flyInitialPosition = flyInitialPosition;
            root = new GameObject("Presentation Clutter (visual only)").transform;
            root.SetParent(parent, false);
        }

        public void Regenerate()
        {
            for (var i = root.childCount - 1; i >= 0; i--) Object.Destroy(root.GetChild(i).gameObject);
            placed.Clear();
            counts.Clear(); ObjectCount = 0;
            GenerationAttempted = true;
            LastError = "none";
            SubstrateReady = environment.TryGetSubstrateBounds(out var substrate);
            if (settings == null || settings.ClutterPrefabCount == 0)
            {
                LastError = "no valid clutter prefabs in Resources/FlyBrainVisualLibrary";
                Debug.LogError("[FlyBrain Clutter] Generation stopped: " + LastError +
                    ". Run Tools > FlyBrain > Build Clutter Library and resolve every reported import error.");
                return;
            }
            if (!SubstrateReady)
            {
                LastError = "authoritative substrate renderer bounds are not available";
                Debug.LogWarning("[FlyBrain Clutter] Generation stopped: " + LastError + ".");
                return;
            }

            Debug.Log($"[FlyBrain Clutter] Substrate bounds: {substrate.size.x:F3} x {substrate.size.z:F3} Unity units " +
                $"({substrate.size.x / WorldVisualScale.UnityUnitsPerMillimetre:F1} x " +
                $"{substrate.size.z / WorldVisualScale.UnityUnitsPerMillimetre:F1} mm); wall margin {settings.wallClearanceMm:F1} mm; " +
                $"fly exclusion {settings.flyInitialClearanceMm:F1} mm; taste {settings.patchClearanceMm:F1} mm; " +
                $"odor {settings.odorClearanceMm:F1} mm; predator {settings.predatorClearanceMm:F1} mm; " +
                $"minimum separation {settings.clutterMinimumSeparationMm:F1} mm.");

            var random = new System.Random(settings.clutterSeed);
            Scatter("Rocks", settings.rocks, substrate, random);
            Scatter("Leaves", settings.leaves, substrate, random);
            Scatter("Twigs", settings.twigs, substrate, random);
            Scatter("Organic Debris", settings.organicDebris, substrate, random);
            Scatter("Vegetation", settings.largeVegetation, substrate, random);
            root.gameObject.SetActive(Visible);
            if (ObjectCount == 0)
            {
                LastError = "normal placement produced zero instances";
                TryDiagnosticSpawn(substrate);
            }
            else Debug.Log($"[Presentation Clutter] Generated {ObjectCount} renderer-only objects (seed {settings.clutterSeed}).");
        }

        public void Toggle()
        {
            Visible = !Visible;
            root.gameObject.SetActive(Visible);
        }

        void Scatter(string categoryName, ClutterCategory category, Bounds substrate, System.Random random)
        {
            counts[categoryName] = 0;
            if (category == null) { LogCategory(categoryName, false, 0, 0, 0, 0, 0, "category settings are null"); return; }
            var serializedPrefabs = category.prefabs?.Length ?? 0;
            if (!category.enabled) { LogCategory(categoryName, false, serializedPrefabs, 0, 0, 0, 0, "disabled"); return; }
            if (serializedPrefabs == 0) { LogCategory(categoryName, true, 0, 0, 0, 0, 0, "prefab list is empty"); return; }
            var valid = new List<GameObject>();
            foreach (var prefab in category.prefabs)
                if (prefab != null && prefab.GetComponentInChildren<Renderer>(true) != null) valid.Add(prefab);
            if (valid.Count == 0) { LogCategory(categoryName, true, 0, 0, 0, 0, 0, "all prefab references are null or lack a Renderer"); return; }

            var group = new GameObject(categoryName).transform;
            group.SetParent(root, false);
            var minimum = Mathf.Max(0, category.minimumCount);
            var maximum = Mathf.Max(minimum, category.maximumCount);
            var count = random.Next(minimum, maximum + 1);
            var attempts = 0; var rejectedBounds = 0; var rejectedExclusion = 0; var rejectedSeparation = 0;
            for (var i = 0; i < count; i++)
            {
                var sizeMm = Mathf.Lerp(category.minimumVisualSizeMm,
                    Mathf.Max(category.minimumVisualSizeMm, category.maximumVisualSizeMm), NextFloat(random));
                var radius = sizeMm * WorldVisualScale.UnityUnitsPerMillimetre * .5f;
                if (!TryPosition(substrate, radius, random, out var position, ref attempts,
                    ref rejectedBounds, ref rejectedExclusion, ref rejectedSeparation)) continue;

                var instance = Object.Instantiate(valid[random.Next(valid.Count)], group);
                instance.name = $"{categoryName} {i + 1} [visual only]";
                StripNonPresentationComponents(instance);
                instance.transform.SetPositionAndRotation(position, Quaternion.identity);
                var yaw = category.randomRotation ? NextFloat(random) * 360f : 0f;
                var tilt = category.randomTiltDegrees;
                instance.transform.rotation = Quaternion.Euler(
                    Mathf.Lerp(-tilt, tilt, NextFloat(random)), yaw,
                    Mathf.Lerp(-tilt, tilt, NextFloat(random)));

                if (!TryRendererBounds(instance, out var nativeBounds)) { Object.Destroy(instance); continue; }
                var longest = Mathf.Max(nativeBounds.size.x, nativeBounds.size.y, nativeBounds.size.z);
                if (longest <= Mathf.Epsilon) { Object.Destroy(instance); continue; }
                instance.transform.localScale *= sizeMm * WorldVisualScale.UnityUnitsPerMillimetre / longest;

                TryRendererBounds(instance, out var finalBounds);
                instance.transform.position += Vector3.up * (substrate.max.y - finalBounds.min.y +
                    category.groundingOffsetMm * WorldVisualScale.UnityUnitsPerMillimetre);
                placed.Add(new PlacedDisc { center = new Vector2(position.x, position.z), radius = radius });
                counts[categoryName]++; ObjectCount++;
            }
            LogCategory(categoryName, true, valid.Count, count, attempts,
                rejectedBounds + rejectedExclusion + rejectedSeparation, counts[categoryName],
                $"rejected bounds {rejectedBounds}, exclusion {rejectedExclusion}, separation/fly {rejectedSeparation}");
        }

        bool TryPosition(Bounds substrate, float radius, System.Random random, out Vector3 position,
            ref int attempts, ref int rejectedBounds, ref int rejectedExclusion, ref int rejectedSeparation)
        {
            var wall = settings.wallClearanceMm * WorldVisualScale.UnityUnitsPerMillimetre;
            for (var attempt = 0; attempt < 50; attempt++)
            {
                attempts++;
                float x, z;
                if (placed.Count > 0 && NextFloat(random) < settings.clutterClusterChance)
                {
                    var anchor = placed[random.Next(placed.Count)].center;
                    var angle = NextFloat(random) * Mathf.PI * 2f;
                    var distance = Mathf.Sqrt(NextFloat(random)) * settings.clutterClusterRadiusMm * WorldVisualScale.UnityUnitsPerMillimetre;
                    x = anchor.x + Mathf.Cos(angle) * distance; z = anchor.y + Mathf.Sin(angle) * distance;
                }
                else
                {
                    x = Mathf.Lerp(substrate.min.x + wall + radius, substrate.max.x - wall - radius, NextFloat(random));
                    z = Mathf.Lerp(substrate.min.z + wall + radius, substrate.max.z - wall - radius, NextFloat(random));
                }
                if (x < substrate.min.x + wall + radius || x > substrate.max.x - wall - radius ||
                    z < substrate.min.z + wall + radius || z > substrate.max.z - wall - radius)
                { rejectedBounds++; continue; }
                position = new Vector3(x, substrate.max.y, z);
                if (!IsSeparated(position, radius)) { rejectedSeparation++; continue; }
                if (environment.IntersectsClutterExclusion(position, radius, settings)) { rejectedExclusion++; continue; }
                return true;
            }
            position = default;
            return false;
        }

        bool IsSeparated(Vector3 position, float radius)
        {
            var point = new Vector2(position.x, position.z);
            var separation = settings.clutterMinimumSeparationMm * WorldVisualScale.UnityUnitsPerMillimetre;
            foreach (var item in placed)
                if (Vector2.Distance(point, item.center) < radius + item.radius + separation) return false;
            if (HorizontalDistance(position, flyInitialPosition) < radius + settings.flyInitialClearanceMm * WorldVisualScale.UnityUnitsPerMillimetre) return false;
            return true;
        }

        static void LogCategory(string name, bool enabled, int prefabs, int requested, int attempts,
            int rejected, int spawned, string detail) => Debug.Log($"[Clutter:{name}]\nEnabled: {enabled}\nPrefabs: {prefabs}\n" +
                $"Requested: {requested}\nSubstrate bounds available: true\nAttempts: {attempts}\nRejected: {rejected}\n" +
                $"Spawned: {spawned}\nDetail: {detail}");

        void TryDiagnosticSpawn(Bounds substrate)
        {
            GameObject prefab = null;
            foreach (var category in new[] { settings.rocks, settings.leaves, settings.twigs, settings.organicDebris, settings.largeVegetation })
                if (category?.prefabs != null)
                    foreach (var candidate in category.prefabs)
                        if (candidate != null && candidate.GetComponentInChildren<Renderer>(true) != null) { prefab = candidate; break; }
            if (prefab == null) return;
            try
            {
                var instance = Object.Instantiate(prefab, root);
                instance.name = "Diagnostic clutter [visual only]";
                StripNonPresentationComponents(instance);
                instance.transform.position = new Vector3(substrate.center.x, substrate.max.y, substrate.center.z);
                if (!TryRendererBounds(instance, out var bounds)) throw new System.InvalidOperationException("prefab has no renderer bounds after instantiation");
                instance.transform.position += Vector3.up * (substrate.max.y - bounds.min.y);
                ObjectCount = 1; counts["Diagnostic"] = 1;
                LastError = "normal placement produced zero; diagnostic fallback spawned one instance";
                Debug.LogWarning($"[FlyBrain Clutter] Diagnostic prefab spawned successfully at {instance.transform.position}. " +
                    "This confirms prefab instantiation works; inspect the placement rejection diagnostics above.");
            }
            catch (System.Exception exception)
            {
                LastError = "diagnostic prefab instantiation failed: " + exception.Message;
                Debug.LogError("[FlyBrain Clutter] " + LastError);
            }
        }

        static float HorizontalDistance(Vector3 a, Vector3 b) =>
            Vector2.Distance(new Vector2(a.x, a.z), new Vector2(b.x, b.z));

        static float NextFloat(System.Random random) => (float)random.NextDouble();

        static bool TryRendererBounds(GameObject go, out Bounds bounds)
        {
            var renderers = go.GetComponentsInChildren<Renderer>(true);
            if (renderers.Length == 0) { bounds = default; return false; }
            bounds = renderers[0].bounds;
            for (var i = 1; i < renderers.Length; i++) bounds.Encapsulate(renderers[i].bounds);
            return true;
        }

        static void StripNonPresentationComponents(GameObject instance)
        {
            foreach (var component in instance.GetComponentsInChildren<Component>(true))
                if (component != null && component is not Transform && component is not Renderer && component is not MeshFilter)
                    Object.Destroy(component);
        }

        public void Clear() => Object.Destroy(root.gameObject);
    }
}
