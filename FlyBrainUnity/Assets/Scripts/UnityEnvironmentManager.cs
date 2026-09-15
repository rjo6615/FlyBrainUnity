using System.Collections.Generic;
using UnityEngine;

namespace FlyBrain.UnityBridge
{
    public sealed class UnityEnvironmentManager
    {
        readonly Dictionary<string, GameObject> objects = new();
        readonly Transform root;
        public bool IsSynchronized { get; private set; }
        public int ObjectCount => objects.Count;
        public Bounds Bounds { get; private set; } = new(Vector3.zero, Vector3.one);

        public UnityEnvironmentManager(Transform parent)
        {
            root = new GameObject("Python Environment (read only)").transform;
            root.SetParent(parent, false);
        }

        public void ApplyDefinition(EnvironmentDefinition definition)
        {
            var wanted = new HashSet<string>();
            foreach (var item in definition.objects)
            {
                if (string.IsNullOrEmpty(item.id) || item.position?.Length != 3 || item.size?.Length != 3) continue;
                wanted.Add(item.id);
                if (!objects.TryGetValue(item.id, out var go))
                {
                    go = GameObject.CreatePrimitive(PrimitiveFor(item.kind));
                    go.name = $"{item.id} ({item.kind})";
                    go.transform.SetParent(root, false);
                    Object.Destroy(go.GetComponent<Collider>());
                    objects.Add(item.id, go);
                }
                go.transform.position = WorldVisualScale.Position(item.position);
                go.transform.localScale = WorldVisualScale.Dimensions(item.size);
                SetColor(go.GetComponent<Renderer>(), item.color);
                go.SetActive(true);
            }
            foreach (var pair in new List<KeyValuePair<string, GameObject>>(objects))
                if (!wanted.Contains(pair.Key)) { Object.Destroy(pair.Value); objects.Remove(pair.Key); }
            RecalculateBounds();
            IsSynchronized = true;
        }

        public void ApplyState(EnvironmentState state)
        {
            if (state.objects == null) return;
            foreach (var item in state.objects)
                if (objects.TryGetValue(item.id, out var go) && item.position?.Length == 3)
                    go.transform.position = WorldVisualScale.Position(item.position);
            RecalculateBounds();
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
            objects.Clear(); IsSynchronized = false;
        }
    }
}
