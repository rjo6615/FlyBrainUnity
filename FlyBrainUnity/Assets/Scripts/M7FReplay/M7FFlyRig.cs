using System;
using System.Collections.Generic;
using UnityEngine;

namespace FlyBrain.M7FReplay
{
    [Serializable] public sealed class M7FJointBinding { public string jointName; public Transform transform; public Vector3 localAxis = Vector3.right; }

    /// <summary>Transform-only visual rig. Joint values are never fed to Unity physics.</summary>
    public sealed class M7FFlyRig : MonoBehaviour
    {
        [SerializeField] Transform root;
        [SerializeField] M7FJointBinding[] joints = Array.Empty<M7FJointBinding>();
        Quaternion[] restRotations;
        int[] sourceIndices;
        public string LastMappingError { get; private set; }
        public Vector3 PresentationOffset { get; set; }

        public bool ValidateMapping(IReadOnlyList<string> required)
        {
            if (joints.Length != required.Count) { LastMappingError = $"M7F requires exactly {required.Count} joint bindings; found {joints.Length}."; Debug.LogError(LastMappingError, this); return false; }
            var map = new Dictionary<string, int>(); sourceIndices = new int[joints.Length];
            for (var i = 0; i < joints.Length; i++)
            {
                if (joints[i] == null || string.IsNullOrEmpty(joints[i].jointName) || joints[i].transform == null) continue;
                if (map.ContainsKey(joints[i].jointName)) { LastMappingError = $"M7F DUPLICATE JOINT BINDING: {joints[i].jointName}"; Debug.LogError(LastMappingError, this); return false; }
                map[joints[i].jointName] = i;
            }
            for (var source = 0; source < required.Count; source++)
            {
                var name = required[source];
                if (!map.TryGetValue(name, out var binding)) { LastMappingError = $"M7F REQUIRED JOINT MISSING: {name}"; Debug.LogError(LastMappingError, this); return false; }
                sourceIndices[binding] = source;
            }
            if (map.Count != required.Count) { LastMappingError = "M7F joint table contains unexpected or incomplete bindings."; Debug.LogError(LastMappingError, this); return false; }
            restRotations = new Quaternion[joints.Length]; for (var i = 0; i < joints.Length; i++) restRotations[i] = joints[i].transform.localRotation;
            LastMappingError = null; return true;
        }

        public void Apply(M7FReplayData data, int frame, int nextFrame, float presentationBlend)
        {
            if (data == null || restRotations == null) return;
            frame = Mathf.Clamp(frame, 0, data.PhysicsCount - 1); nextFrame = Mathf.Clamp(nextFrame, 0, data.PhysicsCount - 1);
            root.position = Vector3.Lerp(data.UnityPosition(frame), data.UnityPosition(nextFrame), presentationBlend) + PresentationOffset;
            root.rotation = Quaternion.Slerp(SourceQuaternion(data, frame), SourceQuaternion(data, nextFrame), presentationBlend);
            for (var i = 0; i < joints.Length; i++)
            {
                var source = sourceIndices[i]; var a = (float)data.JointPosition[frame * 42 + source]; var b = (float)data.JointPosition[nextFrame * 42 + source];
                joints[i].transform.localRotation = restRotations[i] * Quaternion.AngleAxis(Mathf.Lerp(a, b, presentationBlend) * Mathf.Rad2Deg, joints[i].localAxis.normalized);
            }
        }

        static Quaternion SourceQuaternion(M7FReplayData data, int frame)
        {
            // FlyGym/MuJoCo free-joint quaternion is w,x,y,z. Convert by mapping
            // its rotated forward/up vectors through [x,y,z] -> [x,z,y].
            var i = frame * 4; var q = new Quaternion((float)data.BodyOrientation[i + 1], (float)data.BodyOrientation[i + 2], (float)data.BodyOrientation[i + 3], (float)data.BodyOrientation[i]);
            Vector3 Convert(Vector3 v) => new(v.x, v.z, v.y);
            return Quaternion.LookRotation(Convert(q * Vector3.forward), Convert(q * Vector3.up));
        }
    }
}
