using System;
using UnityEngine;

namespace FlyBrain.UnityBridge
{
    [Serializable]
    public sealed class VisualPrefabSlot
    {
        [Tooltip("Optional replacement. Leave empty to use the built-in scientific primitive.")]
        public GameObject prefab;
        [Tooltip("Applied only below the authoritative transform.")]
        public Vector3 modelScale = Vector3.one;
        public Vector3 modelRotationOffset;
        public Vector3 modelPositionOffset;
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
            return configured != null ? configured : CreateInstance<VisualPrefabLibrary>();
        }
    }
}
