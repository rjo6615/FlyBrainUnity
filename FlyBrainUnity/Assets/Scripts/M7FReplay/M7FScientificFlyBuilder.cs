using System;
using System.Collections.Generic;
using UnityEngine;

namespace FlyBrain.M7FReplay
{
    /// <summary>Builds only the transform rig serialized from native MuJoCo constants. No physics, IK, or fitting.</summary>
    public sealed class M7FScientificFlyBuilder : MonoBehaviour
    {
        [SerializeField] bool showAxisIndicators = false;
        public const float SegmentRadius = .00035f;
        public const float PivotDiameter = .0008f;
        public const float ApproximateVisualRadius = .03f;

        [ContextMenu("BUILD AUTHORITATIVE SCIENTIFIC FLY (NO PHYSICS)")]
        public void Rebuild()
        {
            for (var i = transform.childCount - 1; i >= 0; i--) SafeDestroy(transform.GetChild(i).gameObject);
            var root = Child(transform, "ScientificRoot — SCIENTIFIC RIG ONLY");
            var material = Material("M7F authoritative skeleton", new Color(.16f, .72f, .78f));
            var pivotMaterial = Material("M7F authoritative pivots", new Color(.95f, .75f, .18f));
            var data = M7FScientificFlyRigDefinition.Data; var definitions = data.bodies;
            var thorax = Child(root, "Thorax");
            thorax.localPosition = M7FCoordinates.SourcePositionToUnity(M7FScientificFlyRigDefinition.Vector(data.root_body.local_position)) * M7FCoordinates.MillimetresToUnity;
            thorax.localRotation = M7FCoordinates.SourceQuaternionToUnity(M7FScientificFlyRigDefinition.QuaternionWxyz(data.root_body.local_quaternion_wxyz));
            var finalFrames = new Dictionary<string, Transform> { ["Thorax"] = thorax };
            var pending = new List<M7FAuthoritativeBody>(definitions);
            while (pending.Count != 0)
            {
                var progress = false;
                for (var i = pending.Count - 1; i >= 0; i--)
                {
                    var body = pending[i];
                    if (!finalFrames.TryGetValue(body.parent_body, out var parent)) continue;
                    finalFrames[body.name] = BuildBody(parent, body, material, pivotMaterial);
                    pending.RemoveAt(i); progress = true;
                }
                if (!progress) throw new InvalidOperationException("Authoritative body hierarchy has a missing parent or cycle.");
            }
            var rig = GetComponent<M7FFlyRig>() ?? gameObject.AddComponent<M7FFlyRig>();
            rig.Configure(root, Array.Empty<M7FJointBinding>()); rig.AutoBindCanonicalJoints();
            var skeleton = GetComponent<M7FScientificSkeletonVisibility>() ?? gameObject.AddComponent<M7FScientificSkeletonVisibility>();
            skeleton.Configure(root.GetComponentsInChildren<Renderer>(true)); skeleton.SetVisible(false);
            var legacy = GetComponent<M7FKinematicReferenceOverlay>(); if (legacy != null) SafeDestroy(legacy);
        }

        Transform BuildBody(Transform parent, M7FAuthoritativeBody body, Material segmentMaterial, Material pivotMaterial)
        {
            var bodyBase = Child(parent, body.name + "_BodyBase");
            bodyBase.localPosition = M7FCoordinates.SourcePositionToUnity(M7FScientificFlyRigDefinition.Vector(body.local_position)) * M7FCoordinates.MillimetresToUnity;
            bodyBase.localRotation = M7FCoordinates.SourceQuaternionToUnity(M7FScientificFlyRigDefinition.QuaternionWxyz(body.local_quaternion_wxyz));
            var frame = bodyBase; var previousPivot = Vector3.zero;
            Array.Sort(body.joints, (a, b) => a.declaration_order.CompareTo(b.declaration_order));
            foreach (var joint in body.joints)
            {
                var pivot = M7FCoordinates.SourcePositionToUnity(M7FScientificFlyRigDefinition.Vector(joint.local_position)) * M7FCoordinates.MillimetresToUnity;
                var hinge = Child(frame, joint.name); hinge.localPosition = pivot - previousPivot;
                Primitive(hinge, joint.name + "_Pivot", PrimitiveType.Sphere, Vector3.zero, Vector3.one * PivotDiameter, pivotMaterial);
                if (showAxisIndicators) AddSegment(hinge, joint.name + "_Axis", M7FCoordinates.SourceAxialToUnity(M7FScientificFlyRigDefinition.Vector(joint.local_axis)).normalized * .002f, pivotMaterial);
                var after = Child(hinge, joint.name + "_AfterPivot"); after.localPosition = -pivot;
                frame = after; previousPivot = Vector3.zero;
            }
            var pose = Child(frame, body.name);
            var endpoint = M7FCoordinates.SourcePositionToUnity(M7FScientificFlyRigDefinition.Vector(body.segment_endpoint_local)) * M7FCoordinates.MillimetresToUnity;
            AddSegment(pose, body.name + "_Segment", endpoint, segmentMaterial);
            return pose;
        }

        static void AddSegment(Transform parent, string name, Vector3 endpoint, Material material)
        {
            var length = endpoint.magnitude;
            var visual = Primitive(parent, name, PrimitiveType.Cylinder, endpoint * .5f, new Vector3(SegmentRadius, length * .5f, SegmentRadius), material);
            visual.localRotation = Quaternion.FromToRotation(Vector3.up, endpoint.normalized);
            var distal = Child(parent, name + "_DistalReference"); distal.localPosition = endpoint;
        }
        static Transform Child(Transform parent, string name) { var value = new GameObject(name).transform; value.SetParent(parent, false); return value; }
        static Transform Primitive(Transform parent, string name, PrimitiveType type, Vector3 position, Vector3 scale, Material material)
        {
            var value = GameObject.CreatePrimitive(type); value.name = name; value.transform.SetParent(parent, false); value.transform.localPosition = position; value.transform.localScale = scale;
            var collider = value.GetComponent<Collider>(); if (collider != null) SafeDestroy(collider); value.GetComponent<Renderer>().sharedMaterial = material; return value.transform;
        }
        static Material Material(string name, Color color) { var shader = Shader.Find("Standard") ?? Shader.Find("Universal Render Pipeline/Lit"); return new Material(shader) { name = name, color = color }; }
        static void SafeDestroy(UnityEngine.Object value) { if (Application.isPlaying) UnityEngine.Object.Destroy(value); else UnityEngine.Object.DestroyImmediate(value); }
    }

    /// <summary>Optional renderer-only overlay. It does not change any scientific transform.</summary>
    public sealed class M7FScientificSkeletonVisibility : MonoBehaviour
    {
        [SerializeField] bool visible;
        Renderer[] renderers = Array.Empty<Renderer>();
        public bool Visible => visible;
        public void Configure(Renderer[] scientificRenderers) => renderers = scientificRenderers ?? Array.Empty<Renderer>();
        public void SetVisible(bool value) { visible = value; foreach (var renderer in renderers) if (renderer != null) renderer.enabled = value; }
    }
}
