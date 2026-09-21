using System;
using System.IO;
using System.Security.Cryptography;
using UnityEngine;

namespace FlyBrain.M7FReplay
{
    [Serializable] public sealed class M7FArtifact { public string path, sha256; public long byte_size; }
    [Serializable] public sealed class M7FFrameCounts { public int physics, neural; }
    [Serializable] public sealed class M8Cadence { public double physics, neural; }
    [Serializable] public sealed class M8ReplayManifest
    {
        public string schema, status, consumer;
        public int physics_frames, neural_frames;
        public bool scientific_rig_changed, vis3_anatomy_changed;
        public M8Cadence cadence_ms;
        public M7FArtifact[] artifacts;
    }
    public enum ReplayDataset { M7FCanonical, M8ExtendedSpontaneous }
    [Serializable] public sealed class M7FManifest
    {
        public string schema, status, canonical_m7d_sha256, contact_mapping_classification;
        public bool contacts_available;
        public M7FFrameCounts frame_counts;
        public string[] joint_names, motor_channel_names, sensory_channel_names;
        public M7FArtifact[] artifacts;
    }

    /// <summary>Immutable arrays copied from an M7F binary. No physics API is used.</summary>
    public sealed class M7FReplayData
    {
        public const string Magic = "M7FRPLY\0";
        public readonly int PhysicsCount, NeuralCount;
        public readonly double[] PhysicsTime, BodyPosition, BodyOrientation, JointPosition;
        public readonly double[] NeuralTime, Observer, Decoder, Applied, Sensory;
        public readonly long[] DeliveredDrive, AggregateSpikes;

        internal M7FReplayData(BinaryReader reader)
        {
            var magic = System.Text.Encoding.ASCII.GetString(reader.ReadBytes(8));
            var version = reader.ReadUInt32(); PhysicsCount = checked((int)reader.ReadUInt32());
            NeuralCount = checked((int)reader.ReadUInt32()); var fields = reader.ReadUInt32();
            if (magic != Magic || version != 1 || fields != 11 || PhysicsCount < 1 || NeuralCount < 1)
                throw new InvalidDataException("M7F binary header mismatch.");
            PhysicsTime = ReadDoubles(reader, PhysicsCount);
            BodyPosition = ReadDoubles(reader, checked(PhysicsCount * 3));
            BodyOrientation = ReadDoubles(reader, checked(PhysicsCount * 4));
            JointPosition = ReadDoubles(reader, checked(PhysicsCount * 42));
            NeuralTime = ReadDoubles(reader, NeuralCount);
            Observer = ReadDoubles(reader, checked(NeuralCount * 11));
            Decoder = ReadDoubles(reader, checked(NeuralCount * 11));
            Applied = ReadDoubles(reader, checked(NeuralCount * 11));
            Sensory = ReadDoubles(reader, checked(NeuralCount * 6));
            DeliveredDrive = ReadInt64(reader, NeuralCount); AggregateSpikes = ReadInt64(reader, NeuralCount);
            if (reader.BaseStream.Position != reader.BaseStream.Length)
                throw new InvalidDataException("M7F binary has trailing bytes.");
        }

        static double[] ReadDoubles(BinaryReader reader, int count)
        {
            var values = new double[count];
            try { for (var i = 0; i < count; i++) values[i] = reader.ReadDouble(); }
            catch (EndOfStreamException e) { throw new InvalidDataException("M7F binary is truncated.", e); }
            return values;
        }
        static long[] ReadInt64(BinaryReader reader, int count)
        {
            var values = new long[count];
            try { for (var i = 0; i < count; i++) values[i] = reader.ReadInt64(); }
            catch (EndOfStreamException e) { throw new InvalidDataException("M7F binary is truncated.", e); }
            return values;
        }
        public int NeuralIndexForFrame(int frame) => Mathf.Clamp(frame / 5, 0, NeuralCount - 1);
        public Vector3 SourcePosition(int frame) => new((float)BodyPosition[frame * 3], (float)BodyPosition[frame * 3 + 1], (float)BodyPosition[frame * 3 + 2]);
        public Vector3 UnityPosition(int frame) => M7FCoordinates.SourcePositionToUnity(SourcePosition(frame)) * M7FCoordinates.MillimetresToUnity;
    }
    public sealed class M7FReplayLoader : MonoBehaviour
    {
        [SerializeField] string replayDirectory = "M7FReplay";
        [SerializeField] ReplayDataset dataset = ReplayDataset.M7FCanonical;
        public M7FManifest Manifest { get; private set; }
        public M8ReplayManifest M8Manifest { get; private set; }
        public ReplayDataset Dataset => dataset;
        public M7FReplayData Enabled { get; private set; }
        public M7FReplayData Disabled { get; private set; }

        public void Load()
        {
            if (dataset == ReplayDataset.M8ExtendedSpontaneous) { LoadM8(); return; }
            var root = Path.Combine(Application.streamingAssetsPath, replayDirectory);
            Manifest = JsonUtility.FromJson<M7FManifest>(File.ReadAllText(Path.Combine(root, "m7f_manifest.json")));
            if (Manifest == null || Manifest.schema != "M7F-CANONICAL-REPLAY.1" ||
                Manifest.status != "CANONICAL_REPLAY_EXPORT_COMPLETE") throw new InvalidDataException("M7F manifest is not COMPLETE.");
            var enabledPath = Path.Combine(root, "m7f_enabled_replay.bin");
            var disabledPath = Path.Combine(root, "m7f_disabled_replay.bin");
            VerifyArtifact(enabledPath); VerifyArtifact(disabledPath);
            Enabled = Read(enabledPath); Disabled = Read(disabledPath);
            if (Enabled.PhysicsCount != Disabled.PhysicsCount || Enabled.NeuralCount != Disabled.NeuralCount ||
                Manifest.frame_counts == null || Manifest.frame_counts.physics != Enabled.PhysicsCount ||
                Manifest.frame_counts.neural != Enabled.NeuralCount) throw new InvalidDataException("M7F cross-condition frame counts disagree.");
            for (var i = 0; i < Enabled.PhysicsCount; i++)
                if (Enabled.PhysicsTime[i] != Disabled.PhysicsTime[i]) throw new InvalidDataException("M7F physical clocks disagree.");
        }
        void LoadM8()
        {
            // M8 deliberately reuses the immutable M7F rig metadata.  Only recorded
            // state files and their own fail-closed manifest are selected here.
            var canonicalRoot = Path.Combine(Application.streamingAssetsPath, "M7FReplay");
            Manifest = JsonUtility.FromJson<M7FManifest>(File.ReadAllText(Path.Combine(canonicalRoot, "m7f_manifest.json")));
            if (Manifest == null || Manifest.schema != "M7F-CANONICAL-REPLAY.1" || Manifest.status != "CANONICAL_REPLAY_EXPORT_COMPLETE")
                throw new InvalidDataException("M7F rig metadata manifest is not COMPLETE.");

            var root = Path.Combine(Application.streamingAssetsPath, replayDirectory);
            M8Manifest = JsonUtility.FromJson<M8ReplayManifest>(File.ReadAllText(Path.Combine(root, "m8_replay_manifest.json")));
            if (M8Manifest == null || M8Manifest.schema != "M8-UNITY-REPLAY-EXPORT.1" || M8Manifest.status != "COMPLETE" ||
                M8Manifest.scientific_rig_changed || M8Manifest.vis3_anatomy_changed || M8Manifest.cadence_ms == null ||
                M8Manifest.cadence_ms.physics != .1 || M8Manifest.cadence_ms.neural != .5)
                throw new InvalidDataException("M8 replay manifest is incompatible with the validated M7F/VIS3 viewer.");

            var enabledPath = Path.Combine(root, "m8_enabled_replay.bin");
            var disabledPath = Path.Combine(root, "m8_disabled_replay.bin");
            VerifyArtifact(enabledPath, M8Manifest.artifacts, "M8"); VerifyArtifact(disabledPath, M8Manifest.artifacts, "M8");
            Enabled = Read(enabledPath); Disabled = Read(disabledPath);
            if (Enabled.PhysicsCount != Disabled.PhysicsCount || Enabled.NeuralCount != Disabled.NeuralCount ||
                Enabled.PhysicsCount != M8Manifest.physics_frames || Enabled.NeuralCount != M8Manifest.neural_frames)
                throw new InvalidDataException("M8 manifest and cross-condition frame counts disagree.");
            ValidateClocks(Enabled, Disabled, M8Manifest.cadence_ms);
        }

        static void ValidateClocks(M7FReplayData enabled, M7FReplayData disabled, M8Cadence cadence)
        {
            for (var i = 0; i < enabled.PhysicsCount; i++)
            {
                if (enabled.PhysicsTime[i] != disabled.PhysicsTime[i]) throw new InvalidDataException("M8 physical clocks disagree.");
                if (i > 0 && Math.Abs(enabled.PhysicsTime[i] - enabled.PhysicsTime[i - 1] - cadence.physics) > 1e-9)
                    throw new InvalidDataException("M8 physics cadence mismatch.");
            }
            for (var i = 0; i < enabled.NeuralCount; i++)
            {
                if (enabled.NeuralTime[i] != disabled.NeuralTime[i]) throw new InvalidDataException("M8 neural clocks disagree.");
                if (i > 0 && Math.Abs(enabled.NeuralTime[i] - enabled.NeuralTime[i - 1] - cadence.neural) > 1e-9)
                    throw new InvalidDataException("M8 neural cadence mismatch.");
            }
        }

        void VerifyArtifact(string path) => VerifyArtifact(path, Manifest.artifacts, "M7F");
        static void VerifyArtifact(string path, M7FArtifact[] artifacts, string label)
        {
            var name = Path.GetFileName(path); M7FArtifact expected = null;
            if (artifacts != null) foreach (var artifact in artifacts) if (artifact.path == name) { expected = artifact; break; }
            if (expected == null) throw new InvalidDataException($"{label} manifest has no artifact record for {name}.");
            var info = new FileInfo(path);
            if (!info.Exists) throw new FileNotFoundException($"{label} replay artifact is not staged locally. Copy the completed {name} into {info.DirectoryName} before playback; do not regenerate it.", path);
            if (info.Length != expected.byte_size) throw new InvalidDataException($"{label} artifact size mismatch: {name}.");
            using var stream = File.OpenRead(path); using var hash = SHA256.Create();
            var observed = BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
            if (!string.Equals(observed, expected.sha256, StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException($"{label} artifact SHA-256 mismatch: {name}.");
        }
        public void ConfigureM8() { dataset = ReplayDataset.M8ExtendedSpontaneous; replayDirectory = "M8Replay"; }
        public static M7FReplayData Read(string path) { using var stream = File.OpenRead(path); using var reader = new BinaryReader(stream); return new M7FReplayData(reader); }
        public static M7FReplayData Read(byte[] bytes) { using var stream = new MemoryStream(bytes, false); using var reader = new BinaryReader(stream); return new M7FReplayData(reader); }
    }
}
