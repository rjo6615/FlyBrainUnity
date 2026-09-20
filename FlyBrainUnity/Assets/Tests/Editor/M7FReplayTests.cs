using System.IO;
using FlyBrain.M7FReplay;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.TestTools;

namespace FlyBrain.Tests
{
    public sealed class M7FReplayTests
    {
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
                var expectedForward = M7FCoordinates.SourcePositionToUnity(source * Vector3.forward);
                var expectedUp = M7FCoordinates.SourcePositionToUnity(source * Vector3.up);
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

        [Test] public void InterpolationAndClassificationDefaultsRemainScientificBoundarySafe()
        {
            var go = new GameObject("controller defaults");
            try { var controller = go.AddComponent<M7FReplayController>(); Assert.That(controller.PresentationInterpolation, Is.False); Assert.That(controller.ConditionLabel.ToLowerInvariant(), Does.Not.Contain("gait").And.Not.Contain("walking")); }
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
