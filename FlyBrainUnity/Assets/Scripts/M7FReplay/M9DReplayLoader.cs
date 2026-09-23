using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using UnityEngine;

namespace FlyBrain.M7FReplay
{
    /// <summary>Reads and validates the frozen M9D replay artifacts. It never runs a simulation.</summary>
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
