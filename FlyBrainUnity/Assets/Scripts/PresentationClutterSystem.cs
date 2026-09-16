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
            if (!environment.TryGetSubstrateBounds(out var substrate))
            {
                Debug.LogWarning("[Presentation Clutter] Nothing generated: the authoritative substrate has no rendered bounds.");
                return;
            }

            var random = new System.Random(settings.clutterSeed);
            Scatter("Rocks", settings.rocks, substrate, random);
            Scatter("Leaves", settings.leaves, substrate, random);
            Scatter("Twigs", settings.twigs, substrate, random);
            Scatter("Organic Debris", settings.organicDebris, substrate, random);
            Scatter("Vegetation", settings.largeVegetation, substrate, random);
            root.gameObject.SetActive(Visible);
            if (ObjectCount == 0)
                Debug.LogWarning("[Presentation Clutter] Zero objects generated. Run Tools > FlyBrain > Build Clutter Library and inspect its report.");
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
            if (!category.enabled || category.prefabs == null || category.prefabs.Length == 0) return;
            var valid = new List<GameObject>();
            foreach (var prefab in category.prefabs)
                if (prefab != null && prefab.GetComponentInChildren<Renderer>(true) != null) valid.Add(prefab);
            if (valid.Count == 0) return;

            var group = new GameObject(categoryName).transform;
            group.SetParent(root, false);
            var minimum = Mathf.Max(0, category.minimumCount);
            var maximum = Mathf.Max(minimum, category.maximumCount);
            var count = random.Next(minimum, maximum + 1);
            for (var i = 0; i < count; i++)
            {
                var sizeMm = Mathf.Lerp(category.minimumVisualSizeMm,
                    Mathf.Max(category.minimumVisualSizeMm, category.maximumVisualSizeMm), NextFloat(random));
                var radius = sizeMm * WorldVisualScale.UnityUnitsPerMillimetre * .5f;
                if (!TryPosition(substrate, radius, random, out var position)) continue;

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
        }

        bool TryPosition(Bounds substrate, float radius, System.Random random, out Vector3 position)
        {
            var wall = settings.wallClearanceMm * WorldVisualScale.UnityUnitsPerMillimetre;
            for (var attempt = 0; attempt < 50; attempt++)
            {
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
                    z < substrate.min.z + wall + radius || z > substrate.max.z - wall - radius) continue;
                position = new Vector3(x, substrate.max.y, z);
                if (!IsClear(position, radius)) continue;
                return true;
            }
            position = default;
            return false;
        }

        bool IsClear(Vector3 position, float radius)
        {
            var point = new Vector2(position.x, position.z);
            var separation = settings.clutterMinimumSeparationMm * WorldVisualScale.UnityUnitsPerMillimetre;
            foreach (var item in placed)
                if (Vector2.Distance(point, item.center) < radius + item.radius + separation) return false;
            if (HorizontalDistance(position, flyInitialPosition) < radius + settings.flyInitialClearanceMm * WorldVisualScale.UnityUnitsPerMillimetre) return false;
            return !environment.IntersectsClutterExclusion(position, radius, settings);
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
