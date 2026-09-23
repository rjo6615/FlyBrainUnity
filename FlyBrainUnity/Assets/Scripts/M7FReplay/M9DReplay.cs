using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using UnityEngine;

namespace FlyBrain.M7FReplay
{
    public enum M9DCondition { A_P, A_C, B_P, B_C }
    [Serializable] public sealed class M9DConditionEntry { public string id, artifact; public int state_count; public bool neural_motor_enabled, perturbation_present; }
    [Serializable] public sealed class M9DForce { public double magnitude_native, start_ms_inclusive, stop_ms_exclusive, first_potentially_affected_state_ms; public int transition_start_inclusive, transition_stop_exclusive; public double[] world_direction_source_xyz, unity_direction_xyz, torque_source_xyz; public string target; }
    [Serializable] public sealed class M9DCoordinateConversion { public string mapping, stored_coordinates; public double presentation_scale; }
    [Serializable] public sealed class M9DManifest
    {
        public string schema, status, exporter_source_commit; public int joint_count, physics_transitions, neural_transitions;
        public bool presentation_interpolation_default, unity_physics_authoritative;
        public string[] joint_names; public M7FArtifact[] artifacts; public M9DConditionEntry[] conditions;
        public M9DForce force; public M9DCoordinateConversion coordinate_conversion;
    }

    public sealed class M9DReplayData
    {
        public const string Magic = "M9DRPLY\0";
        public readonly int StateCount; public readonly double[] Time, BodyPosition, BodyOrientation, JointPosition;
        internal M9DReplayData(BinaryReader reader)
        {
            var magic = System.Text.Encoding.ASCII.GetString(reader.ReadBytes(8)); var version = reader.ReadUInt32();
            StateCount = checked((int)reader.ReadUInt32()); var joints = reader.ReadUInt32();
            if (magic != Magic || version != 1 || StateCount != 15001 || joints != 42) throw new InvalidDataException("M9D header mismatch.");
            Time = Read(reader, StateCount); BodyPosition = Read(reader, StateCount * 3);
            BodyOrientation = Read(reader, StateCount * 4); JointPosition = Read(reader, StateCount * 42);
            if (reader.BaseStream.Position != reader.BaseStream.Length) throw new InvalidDataException("M9D binary has trailing bytes.");
            for (var i = 0; i < StateCount; i++)
            {
                if (Math.Abs(Time[i] - i * .1) > 2e-7) throw new InvalidDataException("M9D canonical clock mismatch.");
                if (!Finite(BodyPosition, i * 3, 3) || !Finite(BodyOrientation, i * 4, 4) || !Finite(JointPosition, i * 42, 42)) throw new InvalidDataException("M9D contains nonfinite state data.");
            }
        }
        static bool Finite(double[] values, int start, int count) { for (var i = start; i < start + count; i++) if (double.IsNaN(values[i]) || double.IsInfinity(values[i])) return false; return true; }
        static double[] Read(BinaryReader reader, int count) { var result = new double[count]; try { for (var i = 0; i < count; i++) result[i] = reader.ReadDouble(); } catch (EndOfStreamException e) { throw new InvalidDataException("M9D binary is truncated.", e); } return result; }
        public Vector3 UnityPosition(int frame) => M7FCoordinates.SourcePositionToUnity(new Vector3((float)BodyPosition[frame*3], (float)BodyPosition[frame*3+1], (float)BodyPosition[frame*3+2])) * M7FCoordinates.MillimetresToUnity;
    }

    public sealed class M9DReplayLoader : MonoBehaviour
    {
        [SerializeField] string replayDirectory = "M9DReplay";
        public M9DManifest Manifest { get; private set; }
        public IReadOnlyDictionary<M9DCondition, M9DReplayData> Replays => replays;
        readonly Dictionary<M9DCondition, M9DReplayData> replays = new();
        public void Load()
        {
            var root = Path.Combine(Application.streamingAssetsPath, replayDirectory);
            Manifest = JsonUtility.FromJson<M9DManifest>(File.ReadAllText(Path.Combine(root, "m9d_replay_manifest.json")));
            if (Manifest == null || Manifest.schema != "M9D-CANONICAL-M9B-UNITY-REPLAY.1" || Manifest.status != "COMPLETE" ||
                Manifest.joint_count != 42 || Manifest.joint_names == null || Manifest.joint_names.Length != 42 ||
                Manifest.physics_transitions != 0 || Manifest.neural_transitions != 0 || Manifest.unity_physics_authoritative ||
                Manifest.presentation_interpolation_default || Manifest.coordinate_conversion == null ||
                Manifest.coordinate_conversion.mapping != "[x,y,z] -> [x,z,y]" || Manifest.coordinate_conversion.presentation_scale != .1 ||
                Manifest.force == null || Manifest.force.start_ms_inclusive != 500 || Manifest.force.stop_ms_exclusive != 520)
                throw new InvalidDataException("M9D manifest violates the frozen replay contract.");
            replays.Clear();
            if (Manifest.conditions == null || Manifest.conditions.Length != 4) throw new InvalidDataException("M9D requires four conditions.");
            foreach (var entry in Manifest.conditions)
            {
                if (!Enum.TryParse(entry.id, out M9DCondition condition) || replays.ContainsKey(condition) || entry.state_count != 15001) throw new InvalidDataException("M9D condition declaration mismatch.");
                var path = Path.Combine(root, entry.artifact); Verify(path, entry.artifact); replays.Add(condition, Read(path));
            }
            if (replays.Count != 4) throw new InvalidDataException("M9D conditions are incomplete.");
        }
        void Verify(string path, string name)
        {
            M7FArtifact expected = null; foreach (var artifact in Manifest.artifacts) if (artifact.path == name) expected = artifact;
            if (expected == null) throw new InvalidDataException("M9D artifact is undeclared."); var info = new FileInfo(path);
            if (!info.Exists || info.Length != expected.byte_size) throw new InvalidDataException("M9D artifact size mismatch.");
            using var input = File.OpenRead(path); using var sha = SHA256.Create(); var observed = BitConverter.ToString(sha.ComputeHash(input)).Replace("-", "").ToLowerInvariant();
            if (!string.Equals(observed, expected.sha256, StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("M9D artifact hash mismatch.");
        }
        public static M9DReplayData Read(string path) { using var input = File.OpenRead(path); using var reader = new BinaryReader(input); return new M9DReplayData(reader); }
        public static M9DReplayData Read(byte[] bytes) { using var input = new MemoryStream(bytes, false); using var reader = new BinaryReader(input); return new M9DReplayData(reader); }
    }
}
