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

        struct PlacedDisc { public Vector2 center; public float radius; public string category; }
        public sealed class CategoryDiagnostics
        {
            public int requested, candidates, attempts, boundaryRejected, wallRejected, flyRejected, sugarRejected, bitterRejected,
                odorRejected, predatorRejected, separationRejected, invalidBounds, invalidScale, noRenderers, instantiationExceptions, groundingFailures, otherFailures, spawned;
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
            Debug.Log("[Clutter Generation Order] Large Vegetation -> Rocks -> Twigs -> Leaves -> Organic Debris -> Micro Debris");
            Debug.Log(environment.ClutterExclusionReport(settings));
            Scatter("Large Vegetation", settings.largeVegetation, substrate, random);
            Scatter("Rocks", settings.rocks, substrate, random);
            Scatter("Twigs", settings.twigs, substrate, random);
            Scatter("Leaves", settings.leaves, substrate, random);
            Scatter("Organic Debris", settings.organicDebris, substrate, random);
            Scatter("Micro Debris", settings.microDebris, substrate, random);
            root.gameObject.SetActive(Visible);
            VerifyGrounding();
            if (ObjectCount == 0) LastError = "placement produced zero instances; see per-category rejection diagnostics";
            Debug.Log($"[Presentation Clutter] Generated {ObjectCount} renderer-only objects (seed {settings.clutterSeed}).");
        }

        void Fail(string message) { LastError = message; Debug.LogError("[FlyBrain Clutter] Generation stopped: " + message); }
        public void Toggle() { Visible = !Visible; root.gameObject.SetActive(Visible); }

        enum PlacementResult
        {
            ACCEPTED, OUTSIDE_SUBSTRATE, WALL_EXCLUSION, FLY_EXCLUSION, SUGAR_EXCLUSION,
            BITTER_EXCLUSION, ODOR_EXCLUSION, PREDATOR_EXCLUSION, CLUTTER_SEPARATION,
            INVALID_BOUNDS, INVALID_SCALE, NO_RENDERERS, INSTANTIATION_EXCEPTION,
            GROUNDING_FAILURE, OTHER
        }

        void Scatter(string name, ClutterCategory category, Bounds substrate, System.Random random)
        {
            var d = new CategoryDiagnostics(); diagnostics[name] = d;
            if (category == null || !category.enabled) { Log(name, d, category == null ? "settings null" : "disabled"); return; }
            var valid = ValidPrefabs(category.prefabs); d.candidates = valid.Count;
            var min = Mathf.Max(0, category.minimumCount); var max = Mathf.Max(min, category.maximumCount);
            d.requested = random.Next(min, max + 1);
            var vegetation = name == "Large Vegetation";
            if (vegetation) LogVegetationCandidates(category, valid, d.requested, substrate);
            if (valid.Count == 0) { Log(name, d, "no prefab references with renderers"); if (vegetation) LogVegetationResult(d); return; }
            var group = new GameObject(name).transform; group.SetParent(root, false);
            var clusterCenters = BuildClusterCenters(substrate, name, random);

            for (var i = 0; i < d.requested; i++)
            {
                var prefab = valid[random.Next(valid.Count)];
                var t = Next(random); var sizeMm = Mathf.Lerp(category.minimumVisualSizeMm,
                    Mathf.Max(category.minimumVisualSizeMm, category.maximumVisualSizeMm), t * t);
                var accepted = false; var instanceAttempts = 0; var finalReason = PlacementResult.OTHER;
                var nativePrefab = RendererBoundsAtIdentity(prefab);
                var targetUnits = sizeMm * WorldVisualScale.UnityUnitsPerMillimetre;
                // Plants are normalized by their upright axis. A broad canopy must not silently shrink plant height.
                var sourceDimension = vegetation ? nativePrefab.size.y : Mathf.Max(nativePrefab.size.x, nativePrefab.size.y, nativePrefab.size.z);
                var scale = sourceDimension > 0f ? targetUnits / sourceDimension : float.NaN;
                var predicted = nativePrefab.size * scale;
                if (vegetation)
                    Debug.Log($"=== VEGETATION INSTANCE {i + 1}/{d.requested} ===\nChosen prefab: {prefab.name}\n" +
                        $"Target size mm: {sizeMm:F4}\nCalculated Unity scale: {scale:F8}\nNative bounds: {nativePrefab}\n" +
                        $"Scaled expected bounds: {predicted}\nMaximum placement attempts allowed: 60");

                if (VisibleRenderers(prefab).Count == 0)
                { d.noRenderers++; finalReason = PlacementResult.NO_RENDERERS; if (vegetation) LogAttempt(i, 0, finalReason, Vector3.zero, "prefab has no enabled active renderers"); }
                else if (!FiniteBounds(nativePrefab))
                { d.invalidBounds++; finalReason = PlacementResult.INVALID_BOUNDS; if (vegetation) LogAttempt(i, 0, finalReason, Vector3.zero, "native renderer bounds are non-finite or empty"); }
                else if (!FinitePositive(scale) || scale > 10000f || !FiniteVector(predicted))
                { d.invalidScale++; finalReason = PlacementResult.INVALID_SCALE; if (vegetation) LogAttempt(i, 0, finalReason, Vector3.zero, "scale is NaN, infinite, non-positive, or absurd (>10000)"); }
                else for (var attempt = 0; attempt < 60 && !accepted; attempt++)
                {
                    d.attempts++; instanceAttempts++;
                    var position = CandidatePosition(substrate, sizeMm, name, clusterCenters, random);
                    GameObject instance;
                    try { instance = UnityEngine.Object.Instantiate(prefab, group); }
                    catch (Exception exception)
                    { d.instantiationExceptions++; finalReason = PlacementResult.INSTANTIATION_EXCEPTION; if (vegetation) LogAttempt(i, instanceAttempts, finalReason, position, exception.Message); Debug.LogException(exception); continue; }
                    instance.name = $"{name} {i + 1} [visual only]"; StripNonPresentationComponents(instance);
                    instance.transform.SetPositionAndRotation(position, NativeCorrection(prefab, category, name));
                    if (!TryRendererBounds(instance, out var native) || !FiniteBounds(native))
                    { d.invalidBounds++; finalReason = PlacementResult.INVALID_BOUNDS; UnityEngine.Object.Destroy(instance); if (vegetation) LogAttempt(i, instanceAttempts, finalReason, position, "instance native bounds invalid"); break; }
                    instance.transform.localScale *= scale;
                    var yaw = category.randomRotation ? Next(random) * 360f : 0f; var tilt = category.randomTiltDegrees;
                    instance.transform.rotation = Quaternion.Euler(LerpTilt(random, tilt), yaw, LerpTilt(random, tilt)) * instance.transform.rotation;
                    SyncWorldBounds(instance);
                    if (!TryRendererBounds(instance, out var before) || !FiniteBounds(before))
                    { d.invalidBounds++; finalReason = PlacementResult.INVALID_BOUNDS; UnityEngine.Object.Destroy(instance); if (vegetation) LogAttempt(i, instanceAttempts, finalReason, position, "scaled bounds invalid"); break; }
                    var penetration = category.groundingPenetrationMm * WorldVisualScale.UnityUnitsPerMillimetre;
                    var desiredMinY = substrate.max.y - penetration; var correction = desiredMinY - before.min.y;
                    var detailed = (name == "Rocks" || name == "Twigs") && !grounded.Exists(r => r.instance != null && r.instance.transform.parent.name == name);
                    if (detailed) LogGroundingBefore(prefab, instance, before, substrate.max.y, penetration, correction);
                    instance.transform.position += Vector3.up * correction; SyncWorldBounds(instance);
                    if (!TryRendererBounds(instance, out var final) || !FiniteBounds(final))
                    { d.groundingFailures++; finalReason = PlacementResult.GROUNDING_FAILURE; UnityEngine.Object.Destroy(instance); if (vegetation) LogAttempt(i, instanceAttempts, finalReason, position, "post-grounding bounds invalid"); break; }
                    var radius = PlacementRadius(final, targetUnits, vegetation);
                    finalReason = ClassifyPlacement(substrate, final, radius, vegetation);
                    if (finalReason != PlacementResult.ACCEPTED)
                    { CountRejection(d, finalReason); UnityEngine.Object.Destroy(instance); if (vegetation) LogAttempt(i, instanceAttempts, finalReason, position, $"footprint={radius:F5}"); continue; }
                    if (vegetation) LogAttempt(i, instanceAttempts, PlacementResult.ACCEPTED, position, $"footprint={radius:F5}");
                    if (detailed) Debug.Log($"[Clutter Grounding AFTER]\nRoot world position: {instance.transform.position}\nCombined renderer bounds min Y AFTER grounding: {final.min.y:F6}\nFinal error: {final.min.y - desiredMinY:F8}");
                    placed.Add(new PlacedDisc { center = new Vector2(final.center.x, final.center.z), radius = radius, category = name });
                    var record = new GroundingRecord { instance = instance, prefabName = prefab.name, desiredMinY = desiredMinY };
                    grounded.Add(record); if (debugGrounding == null) debugGrounding = record;
                    d.spawned++; ObjectCount++; accepted = true;
                }
                if (vegetation) Debug.Log($"Attempts: {instanceAttempts}\nAccepted: {accepted}\nFinal failure reason: {(accepted ? PlacementResult.ACCEPTED : finalReason)}");
            }
            Log(name, d, d.spawned == 0 ? "zero spawned; exact rejection counters above identify the cause" : "complete");
            if (vegetation) { LogVegetationResult(d); if (d.spawned == 0) DiagnosticVegetationSpawn(valid[0], category, substrate, group, random); }
        }

        void LogVegetationCandidates(ClutterCategory category, List<GameObject> valid, int requested, Bounds substrate)
        {
            var source = category.prefabs ?? Array.Empty<GameObject>();
            var wall = settings.wallClearanceMm * WorldVisualScale.UnityUnitsPerMillimetre;
            var message = $"=== LARGE VEGETATION RUNTIME ===\nRequested count: {requested}\n" +
                $"Library vegetation array length: {source.Length}\nValid vegetation prefab count: {valid.Count}\n" +
                $"Substrate width: {substrate.size.x:F6}\nSubstrate depth: {substrate.size.z:F6}\n" +
                $"Usable width after wall margin: {Mathf.Max(0f, substrate.size.x - wall * 2f):F6}\n" +
                $"Usable depth after wall margin: {Mathf.Max(0f, substrate.size.z - wall * 2f):F6}";
            for (var i = 0; i < source.Length; i++)
            {
                var prefab = source[i];
                message += $"\n--- Candidate {i} ---\nArray index: {i}\nPrefab reference: {(prefab == null ? "null" : "non-null")}";
                if (prefab == null) continue;
                var all = prefab.GetComponentsInChildren<Renderer>(true); var enabled = VisibleRenderers(prefab);
                var boundsOk = TryRendererBounds(prefab, out var bounds);
                var materials = new List<string>(); var shaders = new List<string>();
                foreach (var renderer in all) foreach (var material in renderer.sharedMaterials)
                    if (material != null) { if (!materials.Contains(material.name)) materials.Add(material.name); var shader = material.shader == null ? "<null>" : material.shader.name; if (!shaders.Contains(shader)) shaders.Add(shader); }
                var longest = boundsOk ? Mathf.Max(bounds.size.x, bounds.size.y, bounds.size.z) : 0f;
                var target = category.minimumVisualSizeMm * WorldVisualScale.UnityUnitsPerMillimetre;
                var scale = boundsOk && bounds.size.y > 0f ? target / bounds.size.y : float.NaN;
                var predicted = bounds.size * scale; var footprint = PlacementRadius(new Bounds(Vector3.zero, predicted), target, true);
                message += $"\nprefab.name: {prefab.name}\nPrefab asset path: {AssetPath(prefab)}\nActive state: {prefab.activeSelf}\n" +
                    $"Total renderer count: {all.Length}\nEnabled renderer count: {enabled.Count}\nTotal mesh-filter count: {prefab.GetComponentsInChildren<MeshFilter>(true).Length}\n" +
                    $"Combined native renderer bounds: {(boundsOk ? bounds.ToString() : "INVALID")}\nBounds size: {bounds.size}\n" +
                    $"Material names: {(materials.Count == 0 ? "<none>" : string.Join(", ", materials))}\nShader names: {(shaders.Count == 0 ? "<none>" : string.Join(", ", shaders))}\n" +
                    $"native bounds size X: {bounds.size.x:F8}\nnative bounds size Y: {bounds.size.y:F8}\nnative bounds size Z: {bounds.size.z:F8}\n" +
                    $"longest dimension: {longest:F8}\ntarget dimension: upright Y ({target:F8} Unity units / {category.minimumVisualSizeMm:F2} mm)\n" +
                    $"calculated scale multiplier: {scale:F8}\nFINAL predicted bounds size after scaling: {predicted}\n" +
                    $"Vegetation placement radius: {footprint:F8} Unity units / {footprint / WorldVisualScale.UnityUnitsPerMillimetre:F4} mm\n" +
                    $"SOURCE FBX: Assets/Art/Clutter/Organic/{prefab.name}.fbx\nGENERATED PREFAB: {AssetPath(prefab)}\n" +
                    $"SERIALIZED LIBRARY REFERENCE: {prefab.name}\nRUNTIME PREFAB INSTANCE: pending placement";
            }
            Debug.Log(message + "\n=== END VEGETATION CANDIDATES ===");
        }

        PlacementResult ClassifyPlacement(Bounds substrate, Bounds rendered, float radius, bool vegetation)
        {
            if (!Inside(substrate, rendered)) return PlacementResult.OUTSIDE_SUBSTRATE;
            if (environment.TryGetClutterExclusion(rendered.center, radius, settings, out var exclusion, out _, out _))
            {
                if (exclusion == ClutterExclusionReason.Wall) return PlacementResult.WALL_EXCLUSION;
                if (exclusion == ClutterExclusionReason.Sugar) return PlacementResult.SUGAR_EXCLUSION;
                if (exclusion == ClutterExclusionReason.Bitter) return PlacementResult.BITTER_EXCLUSION;
                if (exclusion == ClutterExclusionReason.Odor) return PlacementResult.ODOR_EXCLUSION;
                if (exclusion == ClutterExclusionReason.Predator) return PlacementResult.PREDATOR_EXCLUSION;
            }
            var point = new Vector2(rendered.center.x, rendered.center.z);
            if (Vector2.Distance(point, new Vector2(flyInitialPosition.x, flyInitialPosition.z)) <
                radius + settings.flyInitialClearanceMm * WorldVisualScale.UnityUnitsPerMillimetre) return PlacementResult.FLY_EXCLUSION;
            var separation = settings.clutterMinimumSeparationMm * WorldVisualScale.UnityUnitsPerMillimetre;
            foreach (var q in placed)
            {
                // Decorative grit never vetoes an important plant, including regeneration into an existing ordering.
                if (vegetation && q.category == "Micro Debris") continue;
                if (Vector2.Distance(point, q.center) < radius + q.radius + separation) return PlacementResult.CLUTTER_SEPARATION;
            }
            return PlacementResult.ACCEPTED;
        }

        static float PlacementRadius(Bounds bounds, float targetUnits, bool vegetation)
        {
            var horizontal = Mathf.Max(bounds.extents.x, bounds.extents.z);
            if (!vegetation) return horizontal;
            // Only the XZ ground footprint participates in separation. Cap canopy overhang at 35% of plant height.
            return Mathf.Clamp(horizontal, targetUnits * .08f, targetUnits * .35f);
        }

        static void CountRejection(CategoryDiagnostics d, PlacementResult reason)
        {
            switch (reason)
            {
                case PlacementResult.OUTSIDE_SUBSTRATE: d.boundaryRejected++; break;
                case PlacementResult.WALL_EXCLUSION: d.wallRejected++; break;
                case PlacementResult.FLY_EXCLUSION: d.flyRejected++; break;
                case PlacementResult.SUGAR_EXCLUSION: d.sugarRejected++; break;
                case PlacementResult.BITTER_EXCLUSION: d.bitterRejected++; break;
                case PlacementResult.ODOR_EXCLUSION: d.odorRejected++; break;
                case PlacementResult.PREDATOR_EXCLUSION: d.predatorRejected++; break;
                case PlacementResult.CLUTTER_SEPARATION: d.separationRejected++; break;
                case PlacementResult.INVALID_BOUNDS: d.invalidBounds++; break;
                case PlacementResult.INVALID_SCALE: d.invalidScale++; break;
                case PlacementResult.NO_RENDERERS: d.noRenderers++; break;
                case PlacementResult.INSTANTIATION_EXCEPTION: d.instantiationExceptions++; break;
                case PlacementResult.GROUNDING_FAILURE: d.groundingFailures++; break;
                default: d.otherFailures++; break;
            }
        }

        static void LogAttempt(int instanceIndex, int attempt, PlacementResult reason, Vector3 position, string detail) =>
            Debug.Log($"[Vegetation attempt] Instance: {instanceIndex + 1}; Attempt: {attempt}; Position: {position}; Result: {reason}; Detail: {detail}");

        static void LogVegetationResult(CategoryDiagnostics d) => Debug.Log(
            $"=== LARGE VEGETATION RESULT ===\nRequested: {d.requested}\nCandidates available: {d.candidates}\nTotal placement attempts: {d.attempts}\n" +
            $"Outside substrate: {d.boundaryRejected}\nWall exclusions: {d.wallRejected}\nFly exclusions: {d.flyRejected}\nSugar exclusions: {d.sugarRejected}\n" +
            $"Bitter exclusions: {d.bitterRejected}\nOdor exclusions: {d.odorRejected}\nPredator exclusions: {d.predatorRejected}\n" +
            $"Clutter separation exclusions: {d.separationRejected}\nInvalid bounds: {d.invalidBounds}\nInvalid scale: {d.invalidScale}\n" +
            $"No renderers: {d.noRenderers}\nInstantiation exceptions: {d.instantiationExceptions}\nGrounding failures: {d.groundingFailures}\n" +
            $"Other failures: {d.otherFailures}\nSUCCESSFULLY SPAWNED: {d.spawned}\n=== END RESULT ===");

        void DiagnosticVegetationSpawn(GameObject prefab, ClutterCategory category, Bounds substrate, Transform group, System.Random random)
        {
            var succeeded = false; var visible = false; var groundedOk = false; var rendererCount = 0; var final = default(Bounds); var position = Vector3.zero;
            var native = RendererBoundsAtIdentity(prefab); var targetMm = category.minimumVisualSizeMm;
            var scale = targetMm * WorldVisualScale.UnityUnitsPerMillimetre / native.size.y;
            for (var attempt = 0; attempt < 60 && !succeeded; attempt++)
            {
                position = CandidatePosition(substrate, targetMm, "Large Vegetation", new List<Vector2>(), random);
                GameObject instance = null;
                try
                {
                    instance = UnityEngine.Object.Instantiate(prefab, group); instance.name = "DIAGNOSTIC vegetation [visual only]";
                    StripNonPresentationComponents(instance); instance.transform.SetPositionAndRotation(position, NativeCorrection(prefab, category, "Large Vegetation"));
                    instance.transform.localScale *= scale; instance.transform.rotation = Quaternion.Euler(0f, Next(random) * 360f, 0f) * instance.transform.rotation;
                    SyncWorldBounds(instance); if (!TryRendererBounds(instance, out var before)) { UnityEngine.Object.Destroy(instance); continue; }
                    var desired = substrate.max.y - category.groundingPenetrationMm * WorldVisualScale.UnityUnitsPerMillimetre;
                    instance.transform.position += Vector3.up * (desired - before.min.y); SyncWorldBounds(instance);
                    if (!TryRendererBounds(instance, out final) || !Inside(substrate, final)) { UnityEngine.Object.Destroy(instance); continue; }
                    var radius = PlacementRadius(final, targetMm * WorldVisualScale.UnityUnitsPerMillimetre, true);
                    // The diagnostic ignores only clutter separation; scientific and fly exclusions remain authoritative.
                    if (environment.TryGetClutterExclusion(final.center, radius, settings, out _, out _, out _) ||
                        Vector2.Distance(new Vector2(final.center.x, final.center.z), new Vector2(flyInitialPosition.x, flyInitialPosition.z)) < radius + settings.flyInitialClearanceMm * WorldVisualScale.UnityUnitsPerMillimetre)
                    { UnityEngine.Object.Destroy(instance); continue; }
                    var renderers = VisibleRenderers(instance); rendererCount = renderers.Count;
                    visible = renderers.Exists(r => r.enabled && r.gameObject.activeInHierarchy); groundedOk = Mathf.Abs(final.min.y - desired) <= .002f; succeeded = true;
                }
                catch (Exception exception) { if (instance != null) UnityEngine.Object.Destroy(instance); Debug.LogException(exception); }
            }
            Debug.Log($"=== DIAGNOSTIC VEGETATION SPAWN ===\nDiagnostic prefab: {prefab.name}\nInstantiation succeeded: {succeeded}\n" +
                $"Renderer count: {rendererCount}\nFinal renderer bounds: {final}\nVisible: {visible}\nGrounded: {groundedOk}\nPosition: {position}\n" +
                "Ignored only clutter-vs-clutter separation: YES\n=== END DIAGNOSTIC VEGETATION SPAWN ===");
        }

        static Bounds RendererBoundsAtIdentity(GameObject prefab) => TryRendererBounds(prefab, out var bounds) ? bounds : default;
        static bool FinitePositive(float value) => !float.IsNaN(value) && !float.IsInfinity(value) && value > 0f;
        static bool FiniteVector(Vector3 value) => FinitePositive(value.x) && FinitePositive(value.y) && FinitePositive(value.z);
        static bool FiniteBounds(Bounds bounds) => FiniteVector(bounds.size) &&
            !float.IsNaN(bounds.center.x) && !float.IsInfinity(bounds.center.x) &&
            !float.IsNaN(bounds.center.y) && !float.IsInfinity(bounds.center.y) &&
            !float.IsNaN(bounds.center.z) && !float.IsInfinity(bounds.center.z);
        static string AssetPath(GameObject prefab)
        {
#if UNITY_EDITOR
            return UnityEditor.AssetDatabase.GetAssetPath(prefab);
#else
            return "<asset path unavailable in player build>";
#endif
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
                $"{name} wall/fly/sugar/bitter/odor/predator rejected: {d.wallRejected}/{d.flyRejected}/{d.sugarRejected}/{d.bitterRejected}/{d.odorRejected}/{d.predatorRejected}\n" +
                $"{name} separation rejected: {d.separationRejected}\n{name} invalid bounds/scale/no renderers: {d.invalidBounds}/{d.invalidScale}/{d.noRenderers}\n" +
                $"{name} instantiation/grounding/other failures: {d.instantiationExceptions}/{d.groundingFailures}/{d.otherFailures}\n" +
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
