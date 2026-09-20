using System;
using System.IO;
using UnityEngine;

namespace FlyBrain.M7FReplay
{
    [Serializable] public sealed class M7FRigProvenance
    {
        public string flygym_version, mujoco_version, mjcf_filename, mjcf_sha256, assembled_xml_sha256;
        public string source, coordinate_convention, model_length_unit;
        public float model_length_to_unity;
    }
    [Serializable] public sealed class M7FAuthoritativeJoint
    {
        public string name, type;
        public double[] local_position, local_axis;
        public int declaration_order, canonical_replay_index, mj_joint_id, mj_qpos_address;
    }
    [Serializable] public sealed class M7FAuthoritativeBody
    {
        public string name, parent_body;
        public double[] local_position, local_quaternion_wxyz, segment_endpoint_local;
        public M7FAuthoritativeJoint[] joints;
    }
    [Serializable] public sealed class M7FAuthoritativeRig
    {
        public string schema, status;
        public M7FRigProvenance provenance;
        public M7FAuthoritativeBody root_body;
        public string[] canonical_joint_names;
        public M7FAuthoritativeBody[] bodies;
    }

    /// <summary>
    /// Loader and coordinate conversion for constants extracted from the compiled
    /// FlyGym 1.2.1 seqik model. MaleCNS XML is deliberately not consulted.
    /// </summary>
    public static class M7FScientificFlyRigDefinition
    {
        public const int JointCount = 42;
        public const string ArtifactName = "m7f_authoritative_rig.json";
        static M7FAuthoritativeRig cached;

        public static M7FAuthoritativeRig Load(string path = null)
        {
            path ??= Path.Combine(Application.streamingAssetsPath, "M7FValidation", ArtifactName);
            var value = JsonUtility.FromJson<M7FAuthoritativeRig>(File.ReadAllText(path));
            if (value == null || value.schema != "M7F-VIS2-AUTHORITATIVE-RIG.1" ||
                value.status != "AUTHORITATIVE_CONSTANTS_EXTRACTED" || value.root_body == null || value.root_body.name != "Thorax" || value.bodies == null || value.bodies.Length != 24 ||
                value.canonical_joint_names == null || value.canonical_joint_names.Length != JointCount)
                throw new InvalidDataException("M7F VIS2 authoritative rig artifact is incomplete or has the wrong schema.");
            var names = new System.Collections.Generic.HashSet<string>();
            var count = 0;
            foreach (var body in value.bodies) foreach (var joint in body.joints)
            {
                count++;
                if (joint.type != "hinge" || !names.Add(joint.name) || joint.canonical_replay_index < 0 || joint.canonical_replay_index >= JointCount)
                    throw new InvalidDataException("M7F VIS2 authoritative joint mapping is invalid.");
                if (value.canonical_joint_names[joint.canonical_replay_index] != joint.name)
                    throw new InvalidDataException("M7F VIS2 canonical-name mapping is inconsistent.");
            }
            if (count != JointCount) throw new InvalidDataException("M7F VIS2 authoritative rig does not contain exactly 42 hinges.");
            return value;
        }

        public static M7FAuthoritativeRig Data => cached ??= Load();
        public static string[] CanonicalNames => Data.canonical_joint_names;
        public static bool IsCanonical(string name) => Array.IndexOf(CanonicalNames, name) >= 0;
        public static System.Collections.Generic.IReadOnlyList<string> Names => CanonicalNames;
        public static Vector3 SourceAxis(string canonicalName)
        {
            foreach (var body in Data.bodies) foreach (var joint in body.joints)
                if (joint.name == canonicalName) return Vector(joint.local_axis);
            throw new ArgumentOutOfRangeException(nameof(canonicalName));
        }
        public static Vector3 UnityAxis(string canonicalName) => M7FCoordinates.SourceAxialToUnity(SourceAxis(canonicalName));
        public static Vector3 Vector(double[] value) => new((float)value[0], (float)value[1], (float)value[2]);
        public static Quaternion QuaternionWxyz(double[] value) => new((float)value[1], (float)value[2], (float)value[3], (float)value[0]);
    }

    public static class M7FCoordinates
    {
        public const float MillimetresToUnity = .1f;
        public static Vector3 SourcePositionToUnity(Vector3 value) => new(value.x, value.z, value.y);
        public static Vector3 SourceAxialToUnity(Vector3 axis) => -SourcePositionToUnity(axis);
        public static Quaternion SourceQuaternionToUnity(Quaternion source)
        {
            if (!IsFinite(source) || source.sqrMagnitude < 1e-12f) throw new ArgumentException("Source quaternion must be finite and non-zero.");
            source = Quaternion.Normalize(source);
            return Quaternion.LookRotation(SourcePositionToUnity(source * Vector3.forward), SourcePositionToUnity(source * Vector3.up));
        }
        public static bool IsFinite(Quaternion q) => !(float.IsNaN(q.x) || float.IsInfinity(q.x) || float.IsNaN(q.y) || float.IsInfinity(q.y) || float.IsNaN(q.z) || float.IsInfinity(q.z) || float.IsNaN(q.w) || float.IsInfinity(q.w));
    }
}
