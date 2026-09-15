using System.Collections.Generic;
using System.Text;
using UnityEngine;

namespace FlyBrain.UnityBridge
{
    public sealed class UnityEnvironmentManager
    {
        readonly Dictionary<string, GameObject> objects = new();
        readonly Dictionary<string, TextMesh> labels = new();
        readonly Dictionary<string, string> kinds = new();
        readonly Transform root;
        readonly VisualPrefabLibrary visuals;
        bool debugVisible = true;
        public bool IsSynchronized { get; private set; }
        public int ObjectCount => objects.Count;
        public int DefinitionObjectCount { get; private set; }
        public float GroundSurfaceY { get; private set; }
        public Bounds Bounds { get; private set; } = new(Vector3.zero, Vector3.one);

        public UnityEnvironmentManager(Transform parent, VisualPrefabLibrary visualLibrary)
        {
            visuals = visualLibrary;
            root = new GameObject("Python Environment (read only)").transform;
            root.SetParent(parent, false);
        }

        public void ApplyDefinition(EnvironmentDefinition definition)
        {
            var wanted = new HashSet<string>();
            DefinitionObjectCount = definition.objects.Length;
            var diagnostic = new StringBuilder("[Unity Environment]\nReceived definition with ")
                .Append(DefinitionObjectCount).Append(" objects:");
            foreach (var item in definition.objects)
            {
                diagnostic.Append("\n- ").Append(item.id);
                if (string.IsNullOrEmpty(item.id) || item.position?.Length != 3 || item.size?.Length != 3) continue;
                wanted.Add(item.id);
                if (!objects.TryGetValue(item.id, out var go))
                {
                    go = CreatePresentation(item);
                    go.name = $"{item.id} ({item.kind}) [authoritative root]";
                    go.transform.SetParent(root, false);
                    objects.Add(item.id, go); kinds[item.id] = item.kind;
                    if (item.dynamic) labels.Add(item.id, CreateLabel(item.id));
                }
                go.transform.position = WorldVisualScale.Position(item.position);
                var dimensions = WorldVisualScale.Dimensions(item.size);
                go.transform.localScale = dimensions;
                if (item.kind == "substrate") GroundSurfaceY = go.transform.position.y + dimensions.y * .5f;
                SetFallbackAppearance(go, item);
                go.SetActive(true);
            }
            foreach (var pair in new List<KeyValuePair<string, GameObject>>(objects))
                if (!wanted.Contains(pair.Key))
                {
                    Object.Destroy(pair.Value); objects.Remove(pair.Key); kinds.Remove(pair.Key);
                    if (labels.TryGetValue(pair.Key, out var label)) Object.Destroy(label.gameObject);
                    labels.Remove(pair.Key);
                }
            ApplyDebugVisibility(); RecalculateBounds(); IsSynchronized = true;
            Debug.Log(diagnostic.ToString());
        }

        GameObject CreatePresentation(EnvironmentObject item)
        {
            var authoritativeRoot = new GameObject("Authoritative transform");
            var slot = visuals.ForKind(item.kind);
            var visual = slot?.prefab != null ? Object.Instantiate(slot.prefab) : GameObject.CreatePrimitive(PrimitiveFor(item.kind));
            visual.name = slot?.prefab != null ? "Custom visual" : "Fallback scientific primitive";
            visual.transform.SetParent(authoritativeRoot.transform, false);
            visual.transform.localPosition = slot?.modelPositionOffset ?? Vector3.zero;
            visual.transform.localRotation = Quaternion.Euler(slot?.modelRotationOffset ?? Vector3.zero);
            visual.transform.localScale = slot?.modelScale ?? Vector3.one;
            foreach (var collider in visual.GetComponentsInChildren<Collider>()) Object.Destroy(collider);
            return authoritativeRoot;
        }

        public void ApplyState(EnvironmentState state)
        {
            if (state.objects == null) return;
            foreach (var item in state.objects)
                if (objects.TryGetValue(item.id, out var go) && item.position?.Length == 3)
                    go.transform.position = WorldVisualScale.Position(item.position);
            RecalculateBounds();
        }

        public void SetDebugVisible(bool visible) { debugVisible = visible; ApplyDebugVisibility(); }
        public bool DebugVisible => debugVisible;

        void ApplyDebugVisibility()
        {
            foreach (var label in labels.Values) if (label != null) label.gameObject.SetActive(debugVisible);
            foreach (var pair in objects)
                if (IsSensoryKind(kinds[pair.Key])) pair.Value.SetActive(debugVisible);
        }

        TextMesh CreateLabel(string id)
        {
            var go = new GameObject($"Label {id}"); go.transform.SetParent(root, false);
            var text = go.AddComponent<TextMesh>(); text.text = id; text.fontSize = 32; text.characterSize = .025f;
            text.anchor = TextAnchor.LowerCenter; text.alignment = TextAlignment.Center; text.color = Color.white;
            return text;
        }

        public void FaceLabels(Camera camera)
        {
            if (!debugVisible || camera == null) return;
            foreach (var pair in labels)
                if (pair.Value != null && objects.TryGetValue(pair.Key, out var owner))
                {
                    var bounds = RendererBounds(owner);
                    pair.Value.transform.position = new Vector3(bounds.center.x, bounds.max.y + .08f, bounds.center.z);
                    pair.Value.transform.rotation = camera.transform.rotation;
                }
        }

        static bool IsSensoryKind(string kind) => kind != null &&
            (kind.StartsWith("odor_") || kind.StartsWith("odor:") || kind.StartsWith("taste_") || kind.StartsWith("taste:"));
        static PrimitiveType PrimitiveFor(string kind) => kind == "predator" ? PrimitiveType.Sphere :
            kind != null && (kind.StartsWith("odor_") || kind.StartsWith("odor:")) ? PrimitiveType.Sphere :
            kind != null && (kind.StartsWith("taste_") || kind.StartsWith("taste:")) ? PrimitiveType.Cylinder : PrimitiveType.Cube;

        static void SetFallbackAppearance(GameObject rootObject, EnvironmentObject item)
        {
            if (rootObject.transform.childCount == 0 || rootObject.transform.GetChild(0).name != "Fallback scientific primitive") return;
            var renderer = rootObject.GetComponentInChildren<Renderer>(); if (renderer == null) return;
            var shader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
            var material = new Material(shader);
            var color = item.color?.Length >= 4 ? new Color(item.color[0], item.color[1], item.color[2], item.color[3]) : Color.gray;
            if (item.kind == "substrate") { color = new Color(.12f, .075f, .035f); material.SetFloat("_Smoothness", .12f); }
            else if (item.kind != null && item.kind.StartsWith("wall"))
            {
                color = new Color(.72f, .9f, .92f, .18f);
                material.SetFloat("_Surface", 1); material.SetFloat("_Blend", 0); material.SetFloat("_ZWrite", 0);
                material.EnableKeyword("_SURFACE_TYPE_TRANSPARENT"); material.renderQueue = 3000;
            }
            material.color = color; renderer.material = material;
        }

        static Bounds RendererBounds(GameObject go)
        {
            var renderers = go.GetComponentsInChildren<Renderer>();
            var bounds = renderers.Length > 0 ? renderers[0].bounds : new Bounds(go.transform.position, Vector3.zero);
            for (var i = 1; i < renderers.Length; i++) bounds.Encapsulate(renderers[i].bounds);
            return bounds;
        }

        void RecalculateBounds()
        {
            var initialized = false; var bounds = new Bounds(Vector3.zero, Vector3.one);
            foreach (var go in objects.Values) foreach (var renderer in go.GetComponentsInChildren<Renderer>())
                if (!initialized) { bounds = renderer.bounds; initialized = true; } else bounds.Encapsulate(renderer.bounds);
            Bounds = bounds;
        }

        public void Clear()
        {
            foreach (var go in objects.Values) Object.Destroy(go);
            foreach (var label in labels.Values) if (label != null) Object.Destroy(label.gameObject);
            objects.Clear(); labels.Clear(); kinds.Clear(); IsSynchronized = false; DefinitionObjectCount = 0; GroundSurfaceY = 0;
        }
    }
}
