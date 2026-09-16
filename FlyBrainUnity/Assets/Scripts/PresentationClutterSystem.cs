using System;
using System.Collections.Generic;
using UnityEngine;

namespace FlyBrain.UnityBridge
{
    /// <summary>Renderer-only deterministic decoration. It never participates in authoritative state or physics.</summary>
    public sealed class PresentationClutterSystem
    {
        readonly Transform root;
        readonly UnityEnvironmentManager environment;
        readonly VisualPrefabLibrary settings;
        readonly List<PlacedDisc> placed = new();
        readonly Vector3 flyInitialPosition;
        readonly Dictionary<string, CategoryDiagnostics> diagnostics = new();
        readonly List<GroundingRecord> grounded = new();
        GroundingRecord debugGrounding;

        struct PlacedDisc { public Vector2 center; public float radius; }
        public sealed class CategoryDiagnostics
        {
            public int requested, candidates, attempts, boundaryRejected, exclusionRejected,
                separationRejected, invalidBounds, instantiationExceptions, spawned;
        }
        sealed class GroundingRecord
        {
            public GameObject instance; public string prefabName; public float desiredMinY;
        }

        public bool Visible { get; private set; } = true;
        public int ObjectCount { get; private set; }
        public bool LibraryLoaded => settings != null && settings.ClutterPrefabCount > 0;
        public int PrefabCount => settings?.ClutterPrefabCount ?? 0;
        public bool SubstrateReady { get; private set; }
        public bool GenerationAttempted { get; private set; }
        public string LastError { get; private set; } = "none";
        public int Count(string category) => diagnostics.TryGetValue(category, out var d) ? d.spawned : 0;
        public bool ShouldWarn(string category) => diagnostics.TryGetValue(category, out var d) && d.requested > 0 && d.candidates > 0 && d.spawned == 0;

        public PresentationClutterSystem(Transform parent, UnityEnvironmentManager environment,
            VisualPrefabLibrary settings, Vector3 flyInitialPosition)
        {
            this.environment = environment; this.settings = settings; this.flyInitialPosition = flyInitialPosition;
            root = new GameObject("Presentation Clutter (visual only)").transform; root.SetParent(parent, false);
        }

        public void Regenerate()
        {
            for (var i = root.childCount - 1; i >= 0; i--) UnityEngine.Object.Destroy(root.GetChild(i).gameObject);
            placed.Clear(); grounded.Clear(); debugGrounding = null; diagnostics.Clear(); ObjectCount = 0; GenerationAttempted = true; LastError = "none";
            SubstrateReady = environment.TryGetSubstrateBounds(out var substrate);
            if (settings == null || settings.ClutterPrefabCount == 0) { Fail("no valid clutter prefabs in Resources/FlyBrainVisualLibrary"); return; }
            if (!SubstrateReady) { Fail("authoritative substrate renderer bounds are not available"); return; }

            Debug.Log($"[Clutter Substrate]\nGameObject: mirrored substrate renderers\n" +
                $"Renderer bounds: center={substrate.center}, size={substrate.size}\nSubstrate renderer bounds.max.y: {substrate.max.y:F6}");

            Debug.Log($"[FlyBrain Clutter Clearances]\nFly clearance: {settings.flyInitialClearanceMm:F2} mm\n" +
                $"Sugar/Bitter clearance: {settings.patchClearanceMm:F2} mm\nOdor clearance: {settings.odorClearanceMm:F2} mm\n" +
                $"Predator clearance: {settings.predatorClearanceMm:F2} mm\nWall margin: {settings.wallClearanceMm:F2} mm\n" +
                $"Substrate: {substrate.size.x / WorldVisualScale.UnityUnitsPerMillimetre:F1} x {substrate.size.z / WorldVisualScale.UnityUnitsPerMillimetre:F1} mm");

            var random = new System.Random(settings.clutterSeed);
            Scatter("Rocks", settings.rocks, substrate, random);
            Scatter("Leaves", settings.leaves, substrate, random);
            Scatter("Twigs", settings.twigs, substrate, random);
            Scatter("Organic Debris", settings.organicDebris, substrate, random);
            Scatter("Large Vegetation", settings.largeVegetation, substrate, random);
            Scatter("Micro Debris", settings.microDebris, substrate, random);
            root.gameObject.SetActive(Visible);
            VerifyGrounding();
            if (ObjectCount == 0) LastError = "placement produced zero instances; see per-category rejection diagnostics";
            Debug.Log($"[Presentation Clutter] Generated {ObjectCount} renderer-only objects (seed {settings.clutterSeed}).");
        }

        void Fail(string message) { LastError = message; Debug.LogError("[FlyBrain Clutter] Generation stopped: " + message); }
        public void Toggle() { Visible = !Visible; root.gameObject.SetActive(Visible); }

        void Scatter(string name, ClutterCategory category, Bounds substrate, System.Random random)
        {
            var d = new CategoryDiagnostics(); diagnostics[name] = d;
            if (category == null || !category.enabled) { Log(name, d, category == null ? "settings null" : "disabled"); return; }
            var valid = ValidPrefabs(category.prefabs); d.candidates = valid.Count;
            if (name == "Large Vegetation")
                Debug.Log("[Clutter:Large Vegetation] Runtime prefab candidates (" + valid.Count + "): " +
                    (valid.Count == 0 ? "<none>" : string.Join(", ", valid.ConvertAll(p => p.name))));
            var min = Mathf.Max(0, category.minimumCount); var max = Mathf.Max(min, category.maximumCount);
            d.requested = random.Next(min, max + 1);
            if (valid.Count == 0) { Log(name, d, "no prefab references with renderers"); return; }
            var group = new GameObject(name).transform; group.SetParent(root, false);
            var clusterCenters = BuildClusterCenters(substrate, name, random);

            for (var i = 0; i < d.requested; i++)
            {
                var prefab = valid[random.Next(valid.Count)];
                // Squared random strongly favours subtle small specimens but retains occasional large ones.
                var t = Next(random); var sizeMm = Mathf.Lerp(category.minimumVisualSizeMm,
                    Mathf.Max(category.minimumVisualSizeMm, category.maximumVisualSizeMm), t * t);
                var accepted = false;
                for (var attempt = 0; attempt < 60 && !accepted; attempt++)
                {
                    d.attempts++;
                    var position = CandidatePosition(substrate, sizeMm, name, clusterCenters, random);
                    GameObject instance;
                    try { instance = UnityEngine.Object.Instantiate(prefab, group); }
                    catch (Exception exception)
                    {
                        d.instantiationExceptions++; Debug.LogException(exception); continue;
                    }
                    instance.name = $"{name} {i + 1} [visual only]"; StripNonPresentationComponents(instance);
                    instance.transform.SetPositionAndRotation(position, NativeCorrection(prefab, category, name));
                    if (!TryRendererBounds(instance, out var native) || native.size.sqrMagnitude < 1e-10f)
                    { d.invalidBounds++; UnityEngine.Object.Destroy(instance); break; }
                    var longest = Mathf.Max(native.size.x, native.size.y, native.size.z);
                    instance.transform.localScale *= sizeMm * WorldVisualScale.UnityUnitsPerMillimetre / longest;
                    var yaw = category.randomRotation ? Next(random) * 360f : 0f;
                    var tilt = category.randomTiltDegrees;
                    instance.transform.rotation = Quaternion.Euler(LerpTilt(random, tilt), yaw, LerpTilt(random, tilt)) * instance.transform.rotation;
                    SyncWorldBounds(instance);
                    if (!TryRendererBounds(instance, out var before)) { d.invalidBounds++; UnityEngine.Object.Destroy(instance); break; }
                    var penetration = category.groundingPenetrationMm * WorldVisualScale.UnityUnitsPerMillimetre;
                    var desiredMinY = substrate.max.y - penetration;
                    var correction = desiredMinY - before.min.y;
                    var detailed = (name == "Rocks" || name == "Twigs") && !grounded.Exists(r => r.instance != null && r.instance.transform.parent.name == name);
                    if (detailed) LogGroundingBefore(prefab, instance, before, substrate.max.y, penetration, correction);
                    instance.transform.position += Vector3.up * correction;
                    SyncWorldBounds(instance);
                    if (!TryRendererBounds(instance, out var final)) { d.invalidBounds++; UnityEngine.Object.Destroy(instance); break; }
                    var radius = Mathf.Max(final.extents.x, final.extents.z);
                    if (!Inside(substrate, final)) { d.boundaryRejected++; UnityEngine.Object.Destroy(instance); continue; }
                    if (environment.IntersectsClutterExclusion(final.center, radius, settings)) { d.exclusionRejected++; UnityEngine.Object.Destroy(instance); continue; }
                    if (!IsSeparated(final.center, radius)) { d.separationRejected++; UnityEngine.Object.Destroy(instance); continue; }
                    if (detailed) Debug.Log($"[Clutter Grounding AFTER]\nRoot world position: {instance.transform.position}\n" +
                        $"Combined renderer bounds min Y AFTER grounding: {final.min.y:F6}\nFinal error: {final.min.y - desiredMinY:F8}");
                    placed.Add(new PlacedDisc { center = new Vector2(final.center.x, final.center.z), radius = radius });
                    var record = new GroundingRecord { instance = instance, prefabName = prefab.name, desiredMinY = desiredMinY };
                    grounded.Add(record); if (debugGrounding == null) debugGrounding = record;
                    if (!VisibleRenderers(instance).Exists(r => r.enabled && r.gameObject.activeInHierarchy))
                        Debug.LogError($"[Clutter] Instantiated {prefab.name}, but all of its renderers are invisible/disabled.");
                    d.spawned++; ObjectCount++; accepted = true;
                }
            }
            Log(name, d, d.spawned == 0 ? "zero spawned; rejection counters above identify the cause" : "complete");
            if (name == "Large Vegetation")
                foreach (var prefab in valid)
                    Debug.Log("=== VEGETATION PIPELINE TRACE ===\n" +
                        $"Source: Assets/Art/Clutter/Organic/{prefab.name}.fbx\nResolved category: Large Vegetation\n" +
                        $"Generated prefab: {prefab.name}\nGenerated prefab exists: {prefab != null}\n" +
                        $"Generated prefab renderer count: {VisibleRenderers(prefab).Count}\nAssigned library category: Large Vegetation\n" +
                        $"Serialized library reference: {prefab.name}\nRuntime library loaded: {settings != null}\n" +
                        $"Runtime LargeVegetation prefab count: {valid.Count}\nRequested vegetation instances: {d.requested}\n" +
                        $"Placement attempts: {d.attempts}\nBoundary rejects: {d.boundaryRejected}\n" +
                        $"Scientific exclusion rejects: {d.exclusionRejected}\nSeparation rejects: {d.separationRejected}\n" +
                        $"Invalid bounds rejects: {d.invalidBounds}\nInstantiation exceptions: {d.instantiationExceptions}\n" +
                        $"Successful vegetation instances: {d.spawned}\n=== END TRACE ===");
        }

        Vector3 CandidatePosition(Bounds b, float sizeMm, string category, List<Vector2> centers, System.Random random)
        {
            var wall = settings.wallClearanceMm * WorldVisualScale.UnityUnitsPerMillimetre;
            var isolatedChance = category == "Twigs" || category == "Large Vegetation" ? .72f : .45f;
            float x, z;
            if (centers.Count > 0 && Next(random) > isolatedChance)
            {
                var center = centers[random.Next(centers.Count)];
                var patch = Next(random) < .27f; // about 15% overall are broader patches.
                var radiusMm = settings.clutterClusterRadiusMm * (patch ? 1.8f : .65f);
                var angle = Next(random) * Mathf.PI * 2f; var distance = Mathf.Sqrt(Next(random)) * radiusMm * WorldVisualScale.UnityUnitsPerMillimetre;
                x = center.x + Mathf.Cos(angle) * distance; z = center.y + Mathf.Sin(angle) * distance;
            }
            else { x = Mathf.Lerp(b.min.x + wall, b.max.x - wall, Next(random)); z = Mathf.Lerp(b.min.z + wall, b.max.z - wall, Next(random)); }
            return new Vector3(x, b.max.y, z);
        }

        List<Vector2> BuildClusterCenters(Bounds b, string category, System.Random random)
        {
            var count = category == "Large Vegetation" ? 1 : category == "Twigs" ? 3 : 6;
            var list = new List<Vector2>(count); var margin = settings.wallClearanceMm * WorldVisualScale.UnityUnitsPerMillimetre;
            for (var i = 0; i < count; i++) list.Add(new Vector2(Mathf.Lerp(b.min.x + margin, b.max.x - margin, Next(random)), Mathf.Lerp(b.min.z + margin, b.max.z - margin, Next(random))));
            return list;
        }

        bool Inside(Bounds substrate, Bounds rendered)
        {
            var wall = settings.wallClearanceMm * WorldVisualScale.UnityUnitsPerMillimetre;
            return rendered.min.x >= substrate.min.x + wall && rendered.max.x <= substrate.max.x - wall &&
                   rendered.min.z >= substrate.min.z + wall && rendered.max.z <= substrate.max.z - wall;
        }
        bool IsSeparated(Vector3 p, float radius)
        {
            var point = new Vector2(p.x, p.z); var sep = settings.clutterMinimumSeparationMm * WorldVisualScale.UnityUnitsPerMillimetre;
            foreach (var q in placed) if (Vector2.Distance(point, q.center) < radius + q.radius + sep) return false;
            return Vector2.Distance(point, new Vector2(flyInitialPosition.x, flyInitialPosition.z)) >= radius + settings.flyInitialClearanceMm * WorldVisualScale.UnityUnitsPerMillimetre;
        }

        static Quaternion NativeCorrection(GameObject prefab, ClutterCategory category, string name)
        {
            foreach (var c in category.orientationCorrections ?? Array.Empty<ClutterOrientationCorrection>())
                if (c != null && c.prefab == prefab) return Quaternion.Euler(c.eulerAngles);
            if (name != "Twigs") return Quaternion.identity;
            // Imported branches whose long axis is Y are laid down before procedural yaw/tilt.
            if (TryRendererBounds(prefab, out var b) && b.size.y > Mathf.Max(b.size.x, b.size.z)) return Quaternion.Euler(0f, 0f, 90f);
            return Quaternion.identity;
        }
        static List<GameObject> ValidPrefabs(GameObject[] source)
        { var result = new List<GameObject>(); foreach (var p in source ?? Array.Empty<GameObject>()) if (p != null && p.GetComponentInChildren<Renderer>(true) != null) result.Add(p); return result; }
        static float Next(System.Random r) => (float)r.NextDouble();
        static float LerpTilt(System.Random r, float tilt) => Mathf.Lerp(-tilt, tilt, Next(r));
        static void Log(string name, CategoryDiagnostics d, string detail)
        {
            var message = $"[Clutter:{name}]\n{name} requested: {d.requested}\n{name} prefab candidates: {d.candidates}\n" +
                $"{name} placement attempts: {d.attempts}\n{name} boundary rejected: {d.boundaryRejected}\n" +
                $"{name} exclusion rejected: {d.exclusionRejected}\n{name} separation rejected: {d.separationRejected}\n" +
                $"{name} invalid bounds: {d.invalidBounds}\n{name} instantiation exceptions: {d.instantiationExceptions}\n" +
                $"{name} successfully spawned: {d.spawned}\nDetail: {detail}";
            if (d.requested > 0 && d.candidates > 0 && d.spawned == 0) Debug.LogWarning(message); else Debug.Log(message);
        }
        static List<Renderer> VisibleRenderers(GameObject go)
        {
            var result = new List<Renderer>();
            foreach (var renderer in go.GetComponentsInChildren<Renderer>(true))
                if (renderer != null && renderer.enabled && ActiveBelowRoot(renderer.transform, go.transform)) result.Add(renderer);
            return result;
        }
        static bool ActiveBelowRoot(Transform transform, Transform rootTransform)
        {
            while (transform != null)
            {
                if (!transform.gameObject.activeSelf) return false;
                if (transform == rootTransform) return true;
                transform = transform.parent;
            }
            return false;
        }
        static bool TryRendererBounds(GameObject go, out Bounds bounds)
        {
            var rs = VisibleRenderers(go); if (rs.Count == 0) { bounds = default; return false; }
            bounds = rs[0].bounds; for (var i = 1; i < rs.Count; i++) bounds.Encapsulate(rs[i].bounds); return true;
        }
        static void SyncWorldBounds(GameObject instance)
        {
            instance.transform.hasChanged = true;
            Physics.SyncTransforms();
            foreach (var renderer in instance.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                renderer.forceMatrixRecalculationPerRender = true;
        }
        static void LogGroundingBefore(GameObject prefab, GameObject instance, Bounds before, float substrateTop, float penetration, float correction)
        {
            var message = $"[Clutter Grounding BEFORE]\nPrefab name: {prefab.name}\nRoot world position: {instance.transform.position}\n" +
                $"Root world rotation: {instance.transform.rotation.eulerAngles}\nRoot lossy scale: {instance.transform.lossyScale}\n";
            foreach (var renderer in VisibleRenderers(instance))
                message += $"Renderer: {renderer.name}; type={renderer.GetType().Name}; minY={renderer.bounds.min.y:F6}; " +
                    $"maxY={renderer.bounds.max.y:F6}; center={renderer.bounds.center}; size={renderer.bounds.size}\n";
            Debug.Log(message + $"Combined renderer bounds min Y BEFORE grounding: {before.min.y:F6}\n" +
                $"Substrate top world Y: {substrateTop:F6}\nConfigured penetration in Unity units: {penetration:F6}\n" +
                $"Calculated vertical correction: {correction:F6}");
        }
        void VerifyGrounding()
        {
            Physics.SyncTransforms(); float maximum = 0f, total = 0f; var checkedCount = 0; var outside = 0;
            foreach (var record in grounded)
            {
                if (record.instance == null || !TryRendererBounds(record.instance, out var bounds)) continue;
                var error = Mathf.Abs(bounds.min.y - record.desiredMinY); maximum = Mathf.Max(maximum, error); total += error; checkedCount++;
                if (error > .002f) { outside++; Debug.LogError($"GROUNDING FAILURE: {record.prefabName} final error={error:F8}"); }
            }
            Debug.Log($"=== CLUTTER GROUNDING VERIFICATION ===\nMaximum grounding error: {maximum:F8}\n" +
                $"Average grounding error: {(checkedCount == 0 ? 0f : total / checkedCount):F8}\nObjects outside tolerance: {outside}\n=== END GROUNDING VERIFICATION ===");
        }
        public void DrawGroundingDebug()
        {
            if (debugGrounding?.instance == null || !TryRendererBounds(debugGrounding.instance, out var bounds)) return;
            const float length = .03f; var center = bounds.center;
            Debug.DrawLine(new Vector3(center.x - length, debugGrounding.desiredMinY, center.z), new Vector3(center.x + length, debugGrounding.desiredMinY, center.z), Color.green);
            Debug.DrawLine(new Vector3(center.x, bounds.min.y, center.z - length), new Vector3(center.x, bounds.min.y, center.z + length), Color.red);
        }
        static void StripNonPresentationComponents(GameObject instance)
        { foreach (var c in instance.GetComponentsInChildren<Component>(true)) if (c != null && c is not Transform && c is not Renderer && c is not MeshFilter) UnityEngine.Object.Destroy(c); }
        public void Clear() => UnityEngine.Object.Destroy(root.gameObject);
    }
}
