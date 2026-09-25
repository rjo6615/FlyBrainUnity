using System;
using System.Collections.Generic;
using UnityEngine;

namespace FlyBrain.M7FReplay
{
    [Serializable] public sealed class M7FJointBinding { public string jointName; public Transform transform; public Vector3 sourceAxis; public Vector3 localAxis; }

    /// <summary>Transform-only visual rig. Joint values are never fed to Unity physics.</summary>
    public sealed class M7FFlyRig : MonoBehaviour
    {
        [SerializeField] Transform root;
        [SerializeField] M7FJointBinding[] joints = Array.Empty<M7FJointBinding>();
        [SerializeField] Vector3 presentationOffset;
        Quaternion[] restRotations;
        int[] sourceIndices;
        public string LastMappingError { get; private set; }
        public string ValidationStatus => LastMappingError ?? (restRotations == null ? "NOT VALIDATED" : "42 / 42 JOINTS BOUND");
        public Vector3 PresentationOffset { get => presentationOffset; set => presentationOffset = value; }
        public IReadOnlyList<M7FJointBinding> Joints => joints;
        public Transform ScientificRoot => root;

        public void Configure(Transform scientificRoot, M7FJointBinding[] bindings) { root = scientificRoot; joints = bindings ?? Array.Empty<M7FJointBinding>(); restRotations = null; }

        [ContextMenu("AUTO-BIND CANONICAL 42 JOINTS")]
        public void AutoBindCanonicalJoints()
        {
            var matches = new Dictionary<string, List<Transform>>();
            foreach (var transformInRig in GetComponentsInChildren<Transform>(true))
                if (M7FScientificFlyRigDefinition.IsCanonical(transformInRig.name))
                {
                    if (!matches.TryGetValue(transformInRig.name, out var list)) matches[transformInRig.name] = list = new List<Transform>();
                    list.Add(transformInRig);
                }
            var bindings = new M7FJointBinding[M7FScientificFlyRigDefinition.JointCount];
            for (var i = 0; i < bindings.Length; i++)
            {
                var name = M7FScientificFlyRigDefinition.CanonicalNames[i];
                if (!matches.TryGetValue(name, out var found) || found.Count != 1)
                { LastMappingError = !matches.ContainsKey(name) ? $"M7F REQUIRED JOINT MISSING: {name}" : $"M7F AMBIGUOUS RECURSIVE JOINT NAME: {name}"; Debug.LogError(LastMappingError, this); joints = Array.Empty<M7FJointBinding>(); return; }
                bindings[i] = new M7FJointBinding { jointName = name, transform = found[0], sourceAxis = M7FScientificFlyRigDefinition.SourceAxis(name), localAxis = M7FScientificFlyRigDefinition.UnityAxis(name) };
            }
            joints = bindings; ValidateMapping(M7FScientificFlyRigDefinition.Names);
        }

        public bool ValidateMapping(IReadOnlyList<string> required)
        {
            if (joints.Length != required.Count) { LastMappingError = $"M7F requires exactly {required.Count} joint bindings; found {joints.Length}."; Debug.LogError(LastMappingError, this); return false; }
            var map = new Dictionary<string, int>(); var transforms = new HashSet<Transform>(); sourceIndices = new int[joints.Length];
            for (var i = 0; i < joints.Length; i++)
            {
                if (joints[i] == null || string.IsNullOrEmpty(joints[i].jointName) || joints[i].transform == null) { LastMappingError = $"M7F NULL/INCOMPLETE JOINT BINDING AT {i}."; return false; }
                if (map.ContainsKey(joints[i].jointName)) { LastMappingError = $"M7F DUPLICATE JOINT BINDING: {joints[i].jointName}"; Debug.LogError(LastMappingError, this); return false; }
                if (!transforms.Add(joints[i].transform)) { LastMappingError = $"M7F DUPLICATE TRANSFORM BINDING: {joints[i].transform.name}"; Debug.LogError(LastMappingError, this); return false; }
                if (!M7FScientificFlyRigDefinition.IsCanonical(joints[i].jointName)) { LastMappingError = $"M7F NON-CANONICAL JOINT: {joints[i].jointName}"; return false; }
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

        public static Quaternion SourceQuaternion(M7FReplayData data, int frame)
        {
            // FlyGym/MuJoCo free-joint quaternion is w,x,y,z. Convert by mapping
            // its rotated forward/up vectors through [x,y,z] -> [x,z,y].
            var i = frame * 4; var q = new Quaternion((float)data.BodyOrientation[i + 1], (float)data.BodyOrientation[i + 2], (float)data.BodyOrientation[i + 3], (float)data.BodyOrientation[i]);
            return M7FCoordinates.SourceQuaternionToUnity(q);
        }

        public void Apply(M9DReplayData data, int frame, int nextFrame, float presentationBlend)
        {
            if (data == null || restRotations == null) return;
            frame = Mathf.Clamp(frame, 0, data.StateCount - 1); nextFrame = Mathf.Clamp(nextFrame, 0, data.StateCount - 1);
            root.position = Vector3.Lerp(data.UnityPosition(frame), data.UnityPosition(nextFrame), presentationBlend) + PresentationOffset;
            root.rotation = Quaternion.Slerp(SourceQuaternion(data.BodyOrientation, frame), SourceQuaternion(data.BodyOrientation, nextFrame), presentationBlend);
            for (var i = 0; i < joints.Length; i++) { var source=sourceIndices[i]; var a=(float)data.JointPosition[frame*42+source]; var b=(float)data.JointPosition[nextFrame*42+source]; joints[i].transform.localRotation=restRotations[i]*Quaternion.AngleAxis(Mathf.Lerp(a,b,presentationBlend)*Mathf.Rad2Deg,joints[i].localAxis.normalized); }
        }

        static Quaternion SourceQuaternion(double[] orientation, int frame)
        {
            var i=frame*4; return M7FCoordinates.SourceQuaternionToUnity(new Quaternion((float)orientation[i+1],(float)orientation[i+2],(float)orientation[i+3],(float)orientation[i]));
        }

        /// <summary>Applies one already converted live pose.  This is presentation-only;
        /// every joint scalar is the authoritative MuJoCo qpos in radians.</summary>
        public void ApplyLivePose(Vector3 unityPosition, Quaternion unityRotation, IReadOnlyList<double> jointPositions)
        {
            if (restRotations == null) throw new InvalidOperationException("M7F rig must be validated before applying a live pose.");
            if (jointPositions == null || jointPositions.Count != M7FScientificFlyRigDefinition.JointCount)
                throw new ArgumentException("A live pose must contain exactly 42 joint positions.", nameof(jointPositions));
            root.position = unityPosition + PresentationOffset;
            root.rotation = unityRotation;
            for (var i = 0; i < joints.Length; i++)
            {
                var radians = jointPositions[sourceIndices[i]];
                joints[i].transform.localRotation = restRotations[i] * Quaternion.AngleAxis((float)radians * Mathf.Rad2Deg, joints[i].localAxis.normalized);
            }
        }
    }
}
