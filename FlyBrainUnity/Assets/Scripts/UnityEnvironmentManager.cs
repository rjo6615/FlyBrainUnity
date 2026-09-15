using System.Collections.Generic;
using System.Text;
using UnityEngine;

namespace FlyBrain.UnityBridge
{
    public sealed class UnityEnvironmentManager
    {
        readonly Dictionary<string, GameObject> objects = new();
        readonly Dictionary<string, TextMesh> labels = new();
        readonly Transform root;
        bool labelsVisible;
        public bool IsSynchronized { get; private set; }
        public int ObjectCount => objects.Count;
        public int DefinitionObjectCount { get; private set; }
        public float GroundSurfaceY { get; private set; }
        public Bounds Bounds { get; private set; } = new(Vector3.zero, Vector3.one);

        public UnityEnvironmentManager(Transform parent)
        {
            root = new GameObject("Python Environment (read only)").transform;
            root.SetParent(parent, false);
        }

        public void ApplyDefinition(EnvironmentDefinition definition)
        {
            var wanted = new HashSet<string>();
            DefinitionObjectCount = definition.objects.Length;
            var diagnostic = new StringBuilder("[Unity Environment]\n")
                .Append("Received definition with ").Append(DefinitionObjectCount).Append(" objects:");
            foreach (var item in definition.objects)
            {
                diagnostic.Append("\n- ").Append(item.id);
                if (string.IsNullOrEmpty(item.id) || item.position?.Length != 3 || item.size?.Length != 3) continue;
                wanted.Add(item.id);
                if (!objects.TryGetValue(item.id, out var go))
                {
                    go = CreatePresentation(item);
                    go.name = $"{item.id} ({item.kind})";
                    go.transform.SetParent(root, false);
                    Object.Destroy(go.GetComponent<Collider>());
                    objects.Add(item.id, go);
                    if (item.dynamic) labels.Add(item.id, CreateLabel(item.id));
                }
                go.transform.position = WorldVisualScale.Position(item.position);
                if (item.kind == "substrate")
                {
                    var dimensions = WorldVisualScale.Dimensions(item.size);
                    GroundSurfaceY = go.transform.position.y + dimensions.y * .5f;
                    go.transform.localScale = dimensions;
                }
                else go.transform.localScale = WorldVisualScale.Dimensions(item.size);
                SetColor(go.GetComponent<Renderer>(), item.color);
                go.SetActive(true);
            }
            foreach (var pair in new List<KeyValuePair<string, GameObject>>(objects))
                if (!wanted.Contains(pair.Key))
                {
                    Object.Destroy(pair.Value); objects.Remove(pair.Key);
                    if (labels.TryGetValue(pair.Key, out var label)) Object.Destroy(label.gameObject);
                    labels.Remove(pair.Key);
                }
            RecalculateBounds();
            IsSynchronized = true;
            Debug.Log(diagnostic.ToString());
            if (objects.TryGetValue("substrate", out var substrate))
            {
                var renderer = substrate.GetComponent<Renderer>();
                Debug.Log("[Unity Substrate]\n" +
                    $"Position: {substrate.transform.position}\n" +
                    $"Rotation: {substrate.transform.rotation.eulerAngles}\n" +
                    $"Scale: {substrate.transform.localScale}\n" +
                    $"Renderer bounds center: {renderer.bounds.center}\n" +
                    $"Renderer bounds size: {renderer.bounds.size}");
            }
        }

        public void ApplyState(EnvironmentState state)
        {
            if (state.objects == null) return;
            foreach (var item in state.objects)
                if (objects.TryGetValue(item.id, out var go) && item.position?.Length == 3)
                    go.transform.position = WorldVisualScale.Position(item.position);
            RecalculateBounds();
        }

        public void ToggleLabels()
        {
            labelsVisible = !labelsVisible;
            foreach (var label in labels.Values) if (label != null) label.gameObject.SetActive(labelsVisible);
        }

        public bool LabelsVisible => labelsVisible;

        static GameObject CreatePresentation(EnvironmentObject item) =>
            GameObject.CreatePrimitive(PrimitiveFor(item.kind));

        TextMesh CreateLabel(string id)
        {
            var go = new GameObject($"Label {id}");
            go.transform.SetParent(root, false);
            var text = go.AddComponent<TextMesh>();
            text.text = id; text.fontSize = 32; text.characterSize = .025f;
            text.anchor = TextAnchor.LowerCenter; text.alignment = TextAlignment.Center;
            text.color = Color.white;
            go.SetActive(labelsVisible);
            return text;
        }

        public void FaceLabels(Camera camera)
        {
            if (!labelsVisible || camera == null) return;
            foreach (var pair in labels)
                if (pair.Value != null && objects.TryGetValue(pair.Key, out var owner))
                {
                    var bounds = owner.GetComponent<Renderer>().bounds;
                    pair.Value.transform.position = new Vector3(bounds.center.x, bounds.max.y + .08f, bounds.center.z);
                    pair.Value.transform.rotation = camera.transform.rotation;
                }
        }

        static PrimitiveType PrimitiveFor(string kind) =>
            kind == "predator" ? PrimitiveType.Sphere :
            kind != null && kind.StartsWith("odor_") ? PrimitiveType.Sphere :
            kind != null && kind.StartsWith("taste_") ? PrimitiveType.Cylinder : PrimitiveType.Cube;

        static void SetColor(Renderer renderer, float[] rgba)
        {
            if (renderer == null) return;
            var shader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
            renderer.material = new Material(shader);
            if (rgba?.Length >= 4) renderer.material.color = new Color(rgba[0], rgba[1], rgba[2], rgba[3]);
        }

        void RecalculateBounds()
        {
            var initialized = false; var bounds = new Bounds(Vector3.zero, Vector3.one);
            foreach (var go in objects.Values)
                foreach (var renderer in go.GetComponentsInChildren<Renderer>())
                    if (!initialized) { bounds = renderer.bounds; initialized = true; } else bounds.Encapsulate(renderer.bounds);
            Bounds = bounds;
        }

        public void Clear()
        {
            foreach (var go in objects.Values) Object.Destroy(go);
            foreach (var label in labels.Values) if (label != null) Object.Destroy(label.gameObject);
            objects.Clear(); labels.Clear(); IsSynchronized = false; DefinitionObjectCount = 0; GroundSurfaceY = 0;
        }
    }
}
