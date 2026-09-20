using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace FlyBrain.M7FReplay
{
    [Serializable] public sealed class M7FNativeJoint { public string canonical_name; public double[] pivot, axis; }
    [Serializable] public sealed class M7FNativeBody
    {
        public string leg, segment, body, parent_body;
        public double[] position, orientation_wxyz, endpoint;
        public M7FNativeJoint[] joints;
    }
    [Serializable] public sealed class M7FNativeFrame
    {
        public int frame;
        public double[] root_position, root_orientation_wxyz;
        public M7FNativeBody[] bodies;
    }
    [Serializable] public sealed class M7FNativeCounters { public int mj_forward_calls, mj_step_calls, physics_transitions, neural_transitions; }
    [Serializable] public sealed class M7FNativeReference
    {
        public string schema, status, source_crosscheck_schema;
        public M7FNativeFrame[] frames;
        public M7FNativeCounters counters;
    }
    public sealed class M7FValidationMetric
    {
        public double Maximum, Rms; public int Samples, WorstFrame; public string WorstElement;
        double squared;
        public void Add(double value, int frame, string element) { squared += value * value; Samples++; if (value > Maximum) { Maximum = value; WorstFrame = frame; WorstElement = element; } }
        public void Finish() { Rms = Samples == 0 ? 0 : Math.Sqrt(squared / Samples); }
    }
    public sealed class M7FValidationReport
    {
        public readonly M7FValidationMetric RootPosition = new(), RootOrientation = new(), PivotPosition = new(), AxisAngular = new(), BodyPosition = new(), BodyOrientation = new(), SegmentEndpoint = new();
        public IEnumerable<M7FValidationMetric> Metrics { get { yield return RootPosition; yield return RootOrientation; yield return PivotPosition; yield return AxisAngular; yield return BodyPosition; yield return BodyOrientation; yield return SegmentEndpoint; } }
    }

    /// <summary>Numerical acceptance gate against nine independent native mj_forward frames.</summary>
    public static class M7FAuthoritativeRigValidator
    {
        public const float PositionTolerance = 2e-5f; // Unity units; accommodates JSON -> float serialization.
        public const float AngularToleranceRadians = 2e-4f;

        public static M7FNativeReference Load(string path = null)
        {
            path ??= Path.Combine(Application.streamingAssetsPath, "M7FValidation", "m7f_mujoco_reference_frames.json");
            var value = JsonUtility.FromJson<M7FNativeReference>(File.ReadAllText(path));
            if (value == null || value.schema != "M7F-VIS2-MUJOCO-REFERENCE.1" || value.status != "NATIVE_MJ_FORWARD_COMPLETE" ||
                value.frames == null || value.frames.Length != 9 || value.counters == null || value.counters.mj_forward_calls != 9 ||
                value.counters.mj_step_calls != 0 || value.counters.physics_transitions != 0 || value.counters.neural_transitions != 0)
                throw new InvalidDataException("Native M7F MuJoCo reference is incomplete or is not static-forward-only.");
            return value;
        }

        public static M7FValidationReport Validate(M7FFlyRig rig, M7FReplayData replay, M7FNativeReference reference)
        {
            var report = new M7FValidationReport(); var transforms = new Dictionary<string, Transform>();
            foreach (var value in rig.ScientificRoot.GetComponentsInChildren<Transform>(true)) transforms[value.name] = value;
            var bindings = new Dictionary<string, M7FJointBinding>(); foreach (var value in rig.Joints) bindings[value.jointName] = value;
            foreach (var frame in reference.frames)
            {
                rig.Apply(replay, frame.frame, frame.frame, 0);
                Position(report.RootPosition, rig.ScientificRoot.position, frame.root_position, frame.frame, "root");
                Rotation(report.RootOrientation, rig.ScientificRoot.rotation, frame.root_orientation_wxyz, frame.frame, "root");
                foreach (var body in frame.bodies)
                {
                    var pose = transforms[body.body];
                    Position(report.BodyPosition, pose.position, body.position, frame.frame, body.body);
                    Rotation(report.BodyOrientation, pose.rotation, body.orientation_wxyz, frame.frame, body.body);
                    Position(report.SegmentEndpoint, transforms[body.body + "_Segment_DistalReference"].position, body.endpoint, frame.frame, body.body);
                    foreach (var joint in body.joints)
                    {
                        var binding = bindings[joint.canonical_name];
                        Position(report.PivotPosition, binding.transform.position, joint.pivot, frame.frame, joint.canonical_name);
                        var expected = M7FCoordinates.SourceAxialToUnity(M7FScientificFlyRigDefinition.Vector(joint.axis)).normalized;
                        var actual = (binding.transform.rotation * binding.localAxis).normalized;
                        report.AxisAngular.Add(Mathf.Acos(Mathf.Clamp(Vector3.Dot(expected, actual), -1, 1)), frame.frame, joint.canonical_name);
                    }
                }
            }
            foreach (var metric in report.Metrics) metric.Finish();
            if (report.RootPosition.Maximum > PositionTolerance || report.PivotPosition.Maximum > PositionTolerance ||
                report.BodyPosition.Maximum > PositionTolerance || report.SegmentEndpoint.Maximum > PositionTolerance ||
                report.RootOrientation.Maximum > AngularToleranceRadians || report.AxisAngular.Maximum > AngularToleranceRadians ||
                report.BodyOrientation.Maximum > AngularToleranceRadians)
                throw new InvalidDataException($"AUTHORITATIVE UNITY RIG VALIDATION FAILED: pivot max={report.PivotPosition.Maximum}, axis max={report.AxisAngular.Maximum}, body max={report.BodyPosition.Maximum}");
            return report;
        }

        static void Position(M7FValidationMetric metric, Vector3 actual, double[] source, int frame, string element)
        { metric.Add((actual - M7FCoordinates.SourcePositionToUnity(M7FScientificFlyRigDefinition.Vector(source)) * M7FCoordinates.MillimetresToUnity).magnitude, frame, element); }
        static void Rotation(M7FValidationMetric metric, Quaternion actual, double[] source, int frame, string element)
        {
            var expected = M7FCoordinates.SourceQuaternionToUnity(M7FScientificFlyRigDefinition.QuaternionWxyz(source));
            metric.Add(Quaternion.Angle(actual, expected) * Mathf.Deg2Rad, frame, element);
        }
    }
}
