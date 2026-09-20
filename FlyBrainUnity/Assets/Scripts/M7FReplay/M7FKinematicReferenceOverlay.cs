using System;
using System.IO;
using UnityEngine;

namespace FlyBrain.M7FReplay
{
    [Serializable] sealed class M7FReferenceFile { public M7FReferenceFrame[] frames; }
    [Serializable] sealed class M7FReferenceFrame { public int frame; public M7FReferenceSegment[] segments; }
    [Serializable] sealed class M7FReferenceSegment { public M7FReferenceJoint[] joints; }
    [Serializable] sealed class M7FReferenceJoint { public string canonical_name; public double[] pivot; }

    /// <summary>Optional, non-scientific debug overlay loaded from static validation metadata.</summary>
    public sealed class M7FKinematicReferenceOverlay : MonoBehaviour
    {
        [SerializeField] bool showReferenceOverlay;
        Transform container;

        [ContextMenu("REFRESH FRAME-0 FROZEN REFERENCE OVERLAY")]
        public void RefreshFrame0()
        {
            if (container != null) { if (Application.isPlaying) Destroy(container.gameObject); else DestroyImmediate(container.gameObject); }
            container = new GameObject("FrozenModelReferenceOverlay_DEBUG_ONLY").transform;
            container.SetParent(transform, false); container.gameObject.SetActive(showReferenceOverlay);
            var path = Path.Combine(Application.streamingAssetsPath, "M7FValidation", "m7f_frame0_kinematic_reference.json");
            var reference = JsonUtility.FromJson<M7FReferenceFile>(File.ReadAllText(path));
            var frame = Array.Find(reference.frames, value => value.frame == 0);
            var shader = Shader.Find("Standard") ?? Shader.Find("Universal Render Pipeline/Lit");
            var material = new Material(shader) { name = "Frozen reference pivot (cyan)", color = Color.cyan };
            foreach (var segment in frame.segments) foreach (var joint in segment.joints)
            {
                var marker = GameObject.CreatePrimitive(PrimitiveType.Cube); marker.name = joint.canonical_name + "_FrozenReferenceMarker";
                marker.transform.SetParent(container, false);
                var source = new Vector3((float)joint.pivot[0], (float)joint.pivot[1], (float)joint.pivot[2]);
                marker.transform.position = M7FCoordinates.SourcePositionToUnity(source) * M7FCoordinates.MillimetresToUnity;
                marker.transform.localScale = Vector3.one * .0009f; marker.GetComponent<Renderer>().sharedMaterial = material;
                var collider = marker.GetComponent<Collider>(); if (Application.isPlaying) Destroy(collider); else DestroyImmediate(collider);
            }
        }
    }
}
