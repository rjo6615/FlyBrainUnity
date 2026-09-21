using System.IO;
using System.Security.Cryptography;
using FlyBrain.M7FReplay;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.TestTools;

namespace FlyBrain.Tests
{
    public sealed class M7FReplayTests
    {
        static Transform Descendant(Transform root, string name)
        { foreach (var value in root.GetComponentsInChildren<Transform>(true)) if (value.name == name) return value; return null; }
        static byte[] Fixture()
        {
            using var stream = new MemoryStream(); using var writer = new BinaryWriter(stream);
            writer.Write(System.Text.Encoding.ASCII.GetBytes(M7FReplayData.Magic));
            writer.Write((uint)1); writer.Write((uint)6); writer.Write((uint)1); writer.Write((uint)11);
            for (var i = 0; i < 6; i++) writer.Write(i * .1);            // time
            for (var i = 0; i < 18; i++) writer.Write((double)i);       // position
            for (var i = 0; i < 24; i++) writer.Write(i % 4 == 0 ? 1d : 0d); // quaternion
            for (var i = 0; i < 252; i++) writer.Write(i * .001);       // joints
            writer.Write(.5);                                           // neural time
            for (var i = 0; i < 11 * 3; i++) writer.Write((double)i);   // observer/decoder/applied
            for (var i = 0; i < 6; i++) writer.Write((double)i);        // sensory
            writer.Write((long)7); writer.Write((long)9);
            return stream.ToArray();
        }

        [Test] public void LoaderPreservesCanonicalValuesAndIndexesNeuralCadence()
        {
            var replay = M7FReplayLoader.Read(Fixture());
            Assert.That(replay.PhysicsCount, Is.EqualTo(6)); Assert.That(replay.NeuralCount, Is.EqualTo(1));
            Assert.That(replay.PhysicsTime[5], Is.EqualTo(.5)); Assert.That(replay.JointPosition[251], Is.EqualTo(.251));
            Assert.That(replay.NeuralIndexForFrame(5), Is.Zero);
        }

        [Test] public void CoordinateConversionUsesValidatedProjectConvention()
        {
            var replay = M7FReplayLoader.Read(Fixture());
            Assert.That(replay.UnityPosition(1).x, Is.EqualTo(.3f).Within(1e-6));
            Assert.That(replay.UnityPosition(1).y, Is.EqualTo(.5f).Within(1e-6));
            Assert.That(replay.UnityPosition(1).z, Is.EqualTo(.4f).Within(1e-6));
        }

        [Test] public void PolarAndAxialVectorsRespectImproperBasisDeterminant()
        {
            var source = new Vector3(2, 3, 5);
            Assert.That(M7FCoordinates.SourcePositionToUnity(source), Is.EqualTo(new Vector3(2, 5, 3)));
            Assert.That(M7FCoordinates.SourceAxialToUnity(source), Is.EqualTo(new Vector3(-2, -5, -3)));
            Assert.That(Vector3.Dot(Vector3.Cross(
                M7FCoordinates.SourcePositionToUnity(Vector3.right),
                M7FCoordinates.SourcePositionToUnity(Vector3.up)),
                M7FCoordinates.SourcePositionToUnity(Vector3.forward)), Is.EqualTo(-1));
        }

        [Test] public void BuilderCreatesExactlyOneCompleteTransformOnlyFlyAndAutoBinds42()
        {
            var go = new GameObject("test scientific fly");
            try
            {
                go.AddComponent<M7FScientificFlyBuilder>().Rebuild(); var rig = go.GetComponent<M7FFlyRig>();
                Assert.That(rig, Is.Not.Null); Assert.That(rig.ValidationStatus, Is.EqualTo("42 / 42 JOINTS BOUND"));
                Assert.That(rig.Joints.Count, Is.EqualTo(42));
                var names = new System.Collections.Generic.HashSet<string>(); var transforms = new System.Collections.Generic.HashSet<Transform>();
                foreach (var binding in rig.Joints) { Assert.That(names.Add(binding.jointName), Is.True); Assert.That(transforms.Add(binding.transform), Is.True); }
                CollectionAssert.AreEquivalent(M7FScientificFlyRigDefinition.CanonicalNames, names);
                Assert.That(go.GetComponentsInChildren<Rigidbody>(true), Is.Empty);
                Assert.That(go.GetComponentsInChildren<Collider>(true), Is.Empty);
                Assert.That(go.GetComponentsInChildren<ArticulationBody>(true), Is.Empty);
            }
            finally { Object.DestroyImmediate(go); }
        }

        [Test] public void MissingAndAmbiguousNamesFailClosed()
        {
            var go = new GameObject("test binding failures");
            try
            {
                var builder = go.AddComponent<M7FScientificFlyBuilder>(); builder.Rebuild(); var rig = go.GetComponent<M7FFlyRig>();
                Object.DestroyImmediate(rig.Joints[0].transform.gameObject);
                LogAssert.Expect(LogType.Error, "M7F REQUIRED JOINT MISSING: joint_LFCoxa");
                rig.AutoBindCanonicalJoints();
                StringAssert.Contains("MISSING", rig.LastMappingError);
                builder.Rebuild(); rig = go.GetComponent<M7FFlyRig>();
                var duplicate = new GameObject(M7FScientificFlyRigDefinition.CanonicalNames[0]); duplicate.transform.SetParent(go.transform);
                LogAssert.Expect(LogType.Error, "M7F AMBIGUOUS RECURSIVE JOINT NAME: joint_LFCoxa");
                rig.AutoBindCanonicalJoints(); StringAssert.Contains("AMBIGUOUS", rig.LastMappingError);
            }
            finally { Object.DestroyImmediate(go); }
        }

        [TestCase("joint_LFCoxa", -1, 0, 0)]
        [TestCase("joint_LFCoxa_roll", 0, -1, 0)]
        [TestCase("joint_LFCoxa_yaw", 0, 0, -1)]
        [TestCase("joint_LFFemur_roll", 0, 0, -1)]
        public void AxialVectorConversionIncludesReflectionSign(string name, float x, float y, float z)
        { Assert.That(M7FScientificFlyRigDefinition.UnityAxis(name), Is.EqualTo(new Vector3(x, y, z))); }

        [Test] public void RootQuaternionBasisConversionPreservesMappedForwardAndUp()
        {
            var cases = new[] {
                Quaternion.identity,
                Quaternion.AngleAxis(90, Vector3.right), Quaternion.AngleAxis(-90, Vector3.right),
                Quaternion.AngleAxis(90, Vector3.up), Quaternion.AngleAxis(-90, Vector3.up),
                Quaternion.AngleAxis(90, Vector3.forward), Quaternion.AngleAxis(-90, Vector3.forward),
                Quaternion.Normalize(new Quaternion(.2f, -.3f, .4f, .8f))
            };
            foreach (var source in cases)
            {
                // R_Unity Bv = B R_Source v, i.e. R_Unity = B R_Source B^-1.
                var expectedForward = M7FCoordinates.SourcePositionToUnity(source * Vector3.up);
                var expectedUp = M7FCoordinates.SourcePositionToUnity(source * Vector3.forward);
                var unityQ = M7FCoordinates.SourceQuaternionToUnity(source);
                var right = unityQ * Vector3.right; var up = unityQ * Vector3.up; var forward = unityQ * Vector3.forward;
                var magnitudeSquared = unityQ.x * unityQ.x + unityQ.y * unityQ.y + unityQ.z * unityQ.z + unityQ.w * unityQ.w;

                Assert.That(M7FCoordinates.IsFinite(unityQ), Is.True);
                Assert.That(magnitudeSquared, Is.EqualTo(1f).Within(1e-5f));
                Assert.That((forward - expectedForward).magnitude, Is.LessThan(1e-5f));
                Assert.That((up - expectedUp).magnitude, Is.LessThan(1e-5f));
                Assert.That(forward.magnitude, Is.EqualTo(1f).Within(1e-5f));
                Assert.That(up.magnitude, Is.EqualTo(1f).Within(1e-5f));
                Assert.That(Mathf.Abs(Vector3.Dot(up, forward)), Is.LessThan(1e-5f));
                Assert.That(Vector3.Dot(Vector3.Cross(right, up), forward), Is.GreaterThan(.9999f));
                Assert.That(Mathf.Abs(Quaternion.Dot(unityQ, M7FCoordinates.SourceQuaternionToUnity(source))), Is.EqualTo(1f).Within(1e-6f));
            }
        }

        [TestCase(1, 0, 0)]
        [TestCase(0, 1, 0)]
        [TestCase(0, 0, 1)]
        public void PositiveNinetyDegreeSourceRotationsUseConvertedAxialAxis(float x, float y, float z)
        {
            var sourceAxis = new Vector3(x, y, z);
            var converted = M7FCoordinates.SourceQuaternionToUnity(Quaternion.AngleAxis(90, sourceAxis));
            var derived = Quaternion.AngleAxis(90, M7FCoordinates.SourceAxialToUnity(sourceAxis));
            Assert.That(Mathf.Abs(Quaternion.Dot(converted, derived)), Is.EqualTo(1).Within(1e-5));
            foreach (var basis in new[] { Vector3.right, Vector3.up, Vector3.forward })
                Assert.That(converted * M7FCoordinates.SourcePositionToUnity(basis),
                    Is.EqualTo(M7FCoordinates.SourcePositionToUnity(Quaternion.AngleAxis(90, sourceAxis) * basis)).Using(Vector3ComparerWithEqualsOperator.Instance));
        }

        [Test] public void MultipleHingesOnOneBodyFollowAuthoritativeDeclarationOrder()
        {
            var go = new GameObject("multi hinge order test");
            try
            {
                go.AddComponent<M7FScientificFlyBuilder>().Rebuild(); var rig = go.GetComponent<M7FFlyRig>();
                foreach (var body in M7FScientificFlyRigDefinition.Data.bodies)
                {
                    var ordered = (M7FAuthoritativeJoint[])body.joints.Clone();
                    System.Array.Sort(ordered, (a, b) => a.declaration_order.CompareTo(b.declaration_order));
                    for (var i = 1; i < ordered.Length; i++)
                    {
                        var child = Descendant(rig.ScientificRoot, ordered[i].name);
                        var ancestor = Descendant(rig.ScientificRoot, ordered[i - 1].name);
                        Assert.That(child.IsChildOf(ancestor), Is.True, body.name + " hinge composition order");
                    }
                }
            }
            finally { Object.DestroyImmediate(go); }
        }

        [Test] public void ScientificInputsOrderingAndAcceptanceThresholdsRemainImmutable()
        {
            Assert.That(M7FAuthoritativeRigValidator.PositionTolerance, Is.EqualTo(2e-5f));
            Assert.That(M7FAuthoritativeRigValidator.AngularToleranceRadians, Is.EqualTo(2e-4f));
            Assert.That(Sha256(Path.Combine(Application.streamingAssetsPath, "M7FValidation", "m7f_authoritative_rig.json")), Is.EqualTo("d8cd7e58bb33fff5e102484d937100d7afd7dc1f4156b39dc2a27f65c0c29eb7"));
            Assert.That(Sha256(Path.Combine(Application.streamingAssetsPath, "M7FValidation", "m7f_mujoco_reference_frames.json")), Is.EqualTo("cd7c372214df6dc71071d05114ccdc2ccdca0f6dd48442797980772720f0fa5d"));
            var manifest = JsonUtility.FromJson<M7FManifest>(File.ReadAllText(Path.Combine(Application.streamingAssetsPath, "M7FReplay", "m7f_manifest.json")));
            CollectionAssert.AreEqual(manifest.joint_names, M7FScientificFlyRigDefinition.CanonicalNames);
        }

        static string Sha256(string path)
        {
            using var stream = File.OpenRead(path); using var hash = SHA256.Create();
            return System.BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
        }

        [Test] public void JointApplicationIsAbsoluteSoDirectSeekEqualsNonSequentialSeek()
        {
            var go = new GameObject("seek test");
            try
            {
                go.AddComponent<M7FScientificFlyBuilder>().Rebuild(); var rig = go.GetComponent<M7FFlyRig>(); var replay = M7FReplayLoader.Read(Fixture());
                rig.Apply(replay, 3, 3, 0); var direct = rig.Joints[0].transform.localRotation;
                rig.Apply(replay, 1, 1, 0); rig.Apply(replay, 2, 2, 0); rig.Apply(replay, 3, 3, 0);
                Assert.That(Quaternion.Angle(direct, rig.Joints[0].transform.localRotation), Is.LessThan(1e-5f));
            }
            finally { Object.DestroyImmediate(go); }
        }

        [Test] public void ScientificSegmentsAndPivotsComeFromAuthoritativeArtifact()
        {
            var go = new GameObject("kinematic geometry test");
            try
            {
                go.AddComponent<M7FScientificFlyBuilder>().Rebuild(); var rig = go.GetComponent<M7FFlyRig>();
                foreach (var body in M7FScientificFlyRigDefinition.Data.bodies)
                {
                    var distal = Descendant(rig.ScientificRoot, body.name + "_Segment_DistalReference");
                    var expected = M7FCoordinates.SourcePositionToUnity(M7FScientificFlyRigDefinition.Vector(body.segment_endpoint_local)) * M7FCoordinates.MillimetresToUnity;
                    Assert.That(distal, Is.Not.Null); Assert.That((distal.localPosition - expected).magnitude, Is.LessThan(1e-7f));
                }
                foreach (var binding in rig.Joints)
                {
                    var marker = Descendant(binding.transform, binding.jointName + "_Pivot");
                    Assert.That(marker, Is.Not.Null); Assert.That(marker.gameObject.activeSelf, Is.True);
                    Assert.That(marker.localPosition, Is.EqualTo(Vector3.zero));
                }
            }
            finally { Object.DestroyImmediate(go); }
        }

        [Test] public void AuthoritativeArtifactDeclaresCompiledFlyGymProvenanceAndMapping()
        {
            var data = M7FScientificFlyRigDefinition.Data;
            Assert.That(data.provenance.flygym_version, Is.EqualTo("1.2.1"));
            Assert.That(data.provenance.mujoco_version, Is.EqualTo("3.2.7"));
            Assert.That(data.provenance.mjcf_filename, Is.EqualTo("neuromechfly_seqik_kinorder_ypr.xml"));
            Assert.That(data.provenance.mjcf_sha256, Has.Length.EqualTo(64));
            var addresses = new System.Collections.Generic.HashSet<int>();
            foreach (var body in data.bodies) foreach (var joint in body.joints) Assert.That(addresses.Add(joint.mj_qpos_address), Is.True);
            Assert.That(addresses.Count, Is.EqualTo(42));
        }

        [Test] public void NineNativeMjForwardFramesAreTheNumericalAcceptanceGate()
        {
            var go = new GameObject("authoritative validation");
            try
            {
                var loader = go.AddComponent<M7FReplayLoader>(); loader.Load();
                go.AddComponent<M7FScientificFlyBuilder>().Rebuild();
                var report = M7FAuthoritativeRigValidator.Validate(go.GetComponent<M7FFlyRig>(), loader.Enabled, M7FAuthoritativeRigValidator.Load());
                Assert.That(report.PivotPosition.Samples, Is.EqualTo(9 * 42));
                Assert.That(report.BodyPosition.Samples, Is.EqualTo(9 * 24));
                Assert.That(report.SegmentEndpoint.Samples, Is.EqualTo(9 * 24));
                Assert.That(report.PivotPosition.Maximum, Is.LessThanOrEqualTo(M7FAuthoritativeRigValidator.PositionTolerance));
                Assert.That(report.AxisAngular.Maximum, Is.LessThanOrEqualTo(M7FAuthoritativeRigValidator.AngularToleranceRadians));
                Assert.That(report.BodyOrientation.Maximum, Is.LessThanOrEqualTo(M7FAuthoritativeRigValidator.AngularToleranceRadians));
            }
            finally { Object.DestroyImmediate(go); }
        }

        [Test] public void InterpolationAndClassificationDefaultsRemainScientificBoundarySafe()
        {
            var go = new GameObject("controller defaults");
            try { var controller = go.AddComponent<M7FReplayController>(); Assert.That(controller.PresentationInterpolation, Is.False); Assert.That(controller.ConditionLabel.ToLowerInvariant(), Does.Not.Contain("gait").And.Not.Contain("walking")); }
            finally { Object.DestroyImmediate(go); }
        }

        [TestCase(0.0, 0)]
        [TestCase(0.1, 1)]
        [TestCase(1.0, 10)]
        [TestCase(54.0, 540)]
        [TestCase(54.1, 541)]
        [TestCase(500.0, 5000)]
        [TestCase(501.0, 5000)]
        public void CanonicalMillisecondsMapToDiscretePhysicalFrames(double milliseconds, int expected)
        { Assert.That(M7FReplayController.FrameForCanonicalTime(milliseconds, 5001), Is.EqualTo(expected)); }

        [Test] public void PlaybackControlsClockSeekingAndUiToggleShareOneState()
        {
            var go = new GameObject("playback controls test");
            try
            {
                var loader = go.AddComponent<M7FReplayLoader>(); loader.Load();
                var enabled = new GameObject("enabled"); enabled.transform.SetParent(go.transform); enabled.AddComponent<M7FScientificFlyBuilder>().Rebuild();
                var disabled = new GameObject("disabled"); disabled.transform.SetParent(go.transform); disabled.AddComponent<M7FScientificFlyBuilder>().Rebuild();
                var controller = go.AddComponent<M7FReplayController>(); controller.Configure(loader, enabled.GetComponent<M7FFlyRig>(), disabled.GetComponent<M7FFlyRig>());
                Assert.That(enabled.GetComponent<M7FFlyRig>().ValidateMapping(loader.Manifest.joint_names), Is.True);
                Assert.That(disabled.GetComponent<M7FFlyRig>().ValidateMapping(loader.Manifest.joint_names), Is.True);

                controller.TogglePlayback(); Assert.That(controller.IsPlaying, Is.True, "UI toggle must use controller playback state");
                controller.AdvancePlayback(.0001); Assert.That(controller.Frame, Is.EqualTo(1), "Unity seconds must convert to replay milliseconds");
                controller.Pause(); Assert.That(controller.IsPlaying, Is.False);
                controller.Restart(); Assert.That(controller.Frame, Is.Zero); Assert.That(controller.TimeMs, Is.Zero); Assert.That(controller.LastAppliedFrame, Is.Zero);
                controller.Step(1); Assert.That(controller.Frame, Is.EqualTo(1));
                controller.Step(-1); Assert.That(controller.Frame, Is.Zero);
                controller.Step(-1); Assert.That(controller.Frame, Is.Zero);
                controller.SeekFrame(540); Assert.That(controller.Frame, Is.EqualTo(540)); Assert.That(controller.LastAppliedFrame, Is.EqualTo(540));
                controller.SeekFrame(7); controller.SeekFrame(540); Assert.That(controller.Frame, Is.EqualTo(540), "seek must be absolute");
                controller.SetSpeed(2); controller.Restart(); controller.Play(); controller.AdvancePlayback(.0001); Assert.That(controller.Frame, Is.EqualTo(2));
                controller.SeekFrame(5000); controller.Play(); controller.AdvancePlayback(1); Assert.That(controller.Frame, Is.EqualTo(5000)); Assert.That(controller.IsPlaying, Is.False);
                controller.Step(1); Assert.That(controller.Frame, Is.EqualTo(5000));
                controller.SeekFrame(123); Assert.That(controller.IsPlaying, Is.False); Assert.That(controller.LastAppliedFrame, Is.EqualTo(123));
            }
            finally { Object.DestroyImmediate(go); }
        }

        [Test] public void SceneMenuCreatesRequiredSystemsTwoRigsAndPhysicsFreeGround()
        {
            Assert.That(EditorApplication.ExecuteMenuItem("Fly Brain/M7F/Create Canonical Replay Scene"), Is.True);
            var top = GameObject.Find("M7F Canonical Replay"); Assert.That(top, Is.Not.Null);
            Assert.That(top.transform.Find("ReplaySystem").GetComponent<M7FReplayLoader>(), Is.Not.Null);
            Assert.That(top.transform.Find("ReplaySystem").GetComponent<M7FReplayController>(), Is.Not.Null);
            Assert.That(top.transform.Find("ReplaySystem").GetComponent<M7FScientificUI>(), Is.Not.Null);
            var rigs = top.GetComponentsInChildren<M7FFlyRig>(true); Assert.That(rigs.Length, Is.EqualTo(2));
            foreach (var rig in rigs) Assert.That(rig.ValidationStatus, Is.EqualTo("42 / 42 JOINTS BOUND"));
            var ground = GameObject.Find("VisualGround — PRESENTATION REFERENCE ONLY"); Assert.That(ground, Is.Not.Null); Assert.That(ground.GetComponent<Collider>(), Is.Null); Assert.That(ground.GetComponent<Rigidbody>(), Is.Null);
            Assert.That(top.GetComponentsInChildren<ArticulationBody>(true), Is.Empty);
            Object.DestroyImmediate(top);
        }

        [Test] public void TruncatedBinaryFailsClosed()
        {
            var bytes = Fixture(); System.Array.Resize(ref bytes, bytes.Length - 1);
            Assert.Throws<InvalidDataException>(() => M7FReplayLoader.Read(bytes));
        }
    }
}
