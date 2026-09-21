using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
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
        public double Maximum, Rms;
        public int Samples, WorstFrame;
        public string WorstElement, Expected, Actual, Detail;
        double squared;

        public void Add(double value, int frame, string element, string expected, string actual, string detail = null)
        {
            squared += value * value; Samples++;
            if (Samples != 1 && value <= Maximum) return;
            Maximum = value; WorstFrame = frame; WorstElement = element;
            Expected = expected; Actual = actual; Detail = detail;
        }

        public void Finish() { Rms = Samples == 0 ? 0 : Math.Sqrt(squared / Samples); }
    }

    public sealed class M7FValidationFrameReport
    {
        public readonly int Frame;
        public readonly M7FValidationMetric RootPosition = new(), RootOrientation = new(), PivotPosition = new(), AxisAngular = new(), BodyPosition = new(), BodyOrientation = new(), SegmentEndpoint = new();
        public M7FValidationFrameReport(int frame) { Frame = frame; }
        public IEnumerable<M7FValidationMetric> Metrics { get { yield return RootPosition; yield return RootOrientation; yield return PivotPosition; yield return AxisAngular; yield return BodyPosition; yield return BodyOrientation; yield return SegmentEndpoint; } }
    }

    public sealed class M7FValidationReport
    {
        public readonly M7FValidationMetric RootPosition = new(), RootOrientation = new(), PivotPosition = new(), AxisAngular = new(), BodyPosition = new(), BodyOrientation = new(), SegmentEndpoint = new();
        public readonly List<M7FValidationFrameReport> Frames = new();
        public string FrameZeroHierarchyTrace;
        public IEnumerable<M7FValidationMetric> Metrics { get { yield return RootPosition; yield return RootOrientation; yield return PivotPosition; yield return AxisAngular; yield return BodyPosition; yield return BodyOrientation; yield return SegmentEndpoint; } }

        public string DiagnosticText()
        {
            var text = new StringBuilder("AUTHORITATIVE UNITY RIG VALIDATION FAILED\n");
            AppendMetrics(text, "ALL FRAMES", this);
            foreach (var frame in Frames) AppendMetrics(text, $"FRAME {frame.Frame}", frame);
            text.AppendLine("FRAME 0 HIERARCHY TRACE (authoritative body order; parent before child):");
            text.Append(FrameZeroHierarchyTrace);
            text.AppendLine("CONVENTION AUDIT: B(x,y,z)=(x,z,y), det(B)=-1; polar=Bv; axial=-Bv; rotation=B R B^-1 (implemented by mapping rotated forward/up, not by applying B as a quaternion).");
            text.AppendLine("STATUS: UNITY SCIENTIFIC RIG: NOT YET VALIDATED");
            return text.ToString();
        }

        static void AppendMetrics(StringBuilder text, string heading, M7FValidationReport report)
        {
            var metrics = new[] { report.RootPosition, report.RootOrientation, report.PivotPosition, report.AxisAngular, report.BodyPosition, report.BodyOrientation, report.SegmentEndpoint };
            AppendMetrics(text, heading, metrics);
        }

        static void AppendMetrics(StringBuilder text, string heading, M7FValidationFrameReport report)
        {
            var metrics = new[] { report.RootPosition, report.RootOrientation, report.PivotPosition, report.AxisAngular, report.BodyPosition, report.BodyOrientation, report.SegmentEndpoint };
            AppendMetrics(text, heading, metrics);
        }

        static void AppendMetrics(StringBuilder text, string heading, M7FValidationMetric[] metrics)
        {
            var names = new[] { "root position", "root orientation", "joint pivot position", "joint axis direction", "body position", "body orientation", "segment endpoint" };
            text.AppendLine(heading + ":");
            for (var i = 0; i < metrics.Length; i++)
            {
                var m = metrics[i]; var angular = i == 1 || i == 3 || i == 5;
                text.Append("  ").Append(names[i]).Append(": max=").Append(F(m.Maximum));
                if (angular) text.Append(" rad (").Append(F(m.Maximum * Mathf.Rad2Deg)).Append(" deg)");
                text.Append(", RMS=").Append(F(m.Rms));
                if (angular) text.Append(" rad (").Append(F(m.Rms * Mathf.Rad2Deg)).Append(" deg)");
                text.Append(", worst frame=").Append(m.WorstFrame).Append(", element=").Append(m.WorstElement)
                    .Append(", expected=").Append(m.Expected).Append(", actual=").Append(m.Actual);
                if (!string.IsNullOrEmpty(m.Detail)) text.Append(", ").Append(m.Detail);
                text.AppendLine();
            }
        }

        internal static string F(double value) => value.ToString("R", CultureInfo.InvariantCulture);
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
            var hierarchy = new StringBuilder();
            foreach (var frame in reference.frames)
            {
                var perFrame = new M7FValidationFrameReport(frame.frame); report.Frames.Add(perFrame);
                rig.Apply(replay, frame.frame, frame.frame, 0);
                Position(report.RootPosition, perFrame.RootPosition, rig.ScientificRoot.position, frame.root_position, frame.frame, "freejoint/root");
                Rotation(report.RootOrientation, perFrame.RootOrientation, rig.ScientificRoot.rotation, frame.root_orientation_wxyz, frame.frame, "freejoint/root");
                if (frame.frame == 0)
                {
                    hierarchy.Append("  freejoint/root: position=").Append(V(rig.ScientificRoot.position)).Append(", orientation=").Append(Q(rig.ScientificRoot.rotation)).AppendLine();
                    hierarchy.Append("  freejoint/root -> Thorax (recovered static local transform): position=").Append(V(transforms["Thorax"].position))
                        .Append(", orientation=").Append(Q(transforms["Thorax"].rotation)).AppendLine();
                }
                foreach (var body in frame.bodies)
                {
                    var pose = transforms[body.body];
                    var bodyPositionError = Position(report.BodyPosition, perFrame.BodyPosition, pose.position, body.position, frame.frame, body.body);
                    var bodyRotationError = Rotation(report.BodyOrientation, perFrame.BodyOrientation, pose.rotation, body.orientation_wxyz, frame.frame, body.body);
                    var endpointError = Position(report.SegmentEndpoint, perFrame.SegmentEndpoint, transforms[body.body + "_Segment_DistalReference"].position, body.endpoint, frame.frame, body.body);
                    if (frame.frame == 0) hierarchy.Append("  ").Append(body.parent_body).Append(" -> ").Append(body.body)
                        .Append(": position=").Append(M7FValidationReport.F(bodyPositionError)).Append(", orientation=").Append(M7FValidationReport.F(bodyRotationError))
                        .Append(" rad, endpoint=").Append(M7FValidationReport.F(endpointError)).AppendLine();
                    foreach (var joint in body.joints)
                    {
                        var binding = bindings[joint.canonical_name];
                        var pivotError = Position(report.PivotPosition, perFrame.PivotPosition, binding.transform.position, joint.pivot, frame.frame, joint.canonical_name);
                        var expected = M7FCoordinates.SourceAxialToUnity(M7FScientificFlyRigDefinition.Vector(joint.axis)).normalized;
                        var actual = (binding.transform.rotation * binding.localAxis).normalized;
                        var dot = Mathf.Clamp(Vector3.Dot(expected, actual), -1, 1); var angle = Mathf.Acos(dot);
                        var detail = "dot(expected,actual)=" + M7FValidationReport.F(dot) + ", actual ~= -expected: " + (dot < -.9999f ? "YES" : "no");
                        Add(report.AxisAngular, perFrame.AxisAngular, angle, frame.frame, joint.canonical_name,
                            "MuJoCo=" + A(joint.axis) + " -> Unity(axial)=" + V(expected), V(actual), detail);
                        if (frame.frame == 0) hierarchy.Append("    joint ").Append(joint.canonical_name).Append(": pivot=").Append(M7FValidationReport.F(pivotError))
                            .Append(", axis=").Append(M7FValidationReport.F(angle)).Append(" rad, ").Append(detail).AppendLine();
                    }
                }
                foreach (var metric in perFrame.Metrics) metric.Finish();
            }
            report.FrameZeroHierarchyTrace = hierarchy.ToString();
            foreach (var metric in report.Metrics) metric.Finish();
            if (report.RootPosition.Maximum > PositionTolerance || report.PivotPosition.Maximum > PositionTolerance ||
                report.BodyPosition.Maximum > PositionTolerance || report.SegmentEndpoint.Maximum > PositionTolerance ||
                report.RootOrientation.Maximum > AngularToleranceRadians || report.AxisAngular.Maximum > AngularToleranceRadians ||
                report.BodyOrientation.Maximum > AngularToleranceRadians)
                throw new InvalidDataException(report.DiagnosticText());
            return report;
        }

        static double Position(M7FValidationMetric all, M7FValidationMetric frameMetric, Vector3 actual, double[] source, int frame, string element)
        {
            var expected = M7FCoordinates.SourcePositionToUnity(M7FScientificFlyRigDefinition.Vector(source)) * M7FCoordinates.MillimetresToUnity;
            var delta = actual - expected; var detail = "actual-expected=" + V(delta);
            Add(all, frameMetric, delta.magnitude, frame, element, "MuJoCo=" + A(source) + " -> Unity=" + V(expected), V(actual), detail); return delta.magnitude;
        }

        static double Rotation(M7FValidationMetric all, M7FValidationMetric frameMetric, Quaternion actual, double[] source, int frame, string element)
        {
            var expected = M7FCoordinates.SourceQuaternionToUnity(M7FScientificFlyRigDefinition.QuaternionWxyz(source));
            var relative = Quaternion.Normalize(actual * Quaternion.Inverse(expected));
            var angle = Quaternion.Angle(actual, expected) * Mathf.Deg2Rad;
            Add(all, frameMetric, angle, frame, element, "MuJoCo(wxyz)=" + A(source) + " -> Unity=" + Q(expected), Q(actual), "relative(actual*inverse(expected))=" + Q(relative)); return angle;
        }

        static void Add(M7FValidationMetric all, M7FValidationMetric frame, double value, int frameIndex, string element, string expected, string actual, string detail)
        { all.Add(value, frameIndex, element, expected, actual, detail); frame.Add(value, frameIndex, element, expected, actual, detail); }

        static string V(Vector3 value) => "[" + M7FValidationReport.F(value.x) + "," + M7FValidationReport.F(value.y) + "," + M7FValidationReport.F(value.z) + "]";
        static string Q(Quaternion value) => "[w=" + M7FValidationReport.F(value.w) + ",x=" + M7FValidationReport.F(value.x) + ",y=" + M7FValidationReport.F(value.y) + ",z=" + M7FValidationReport.F(value.z) + "]";
        static string A(double[] value)
        {
            var text = new StringBuilder("[");
            for (var i = 0; i < value.Length; i++) { if (i != 0) text.Append(','); text.Append(M7FValidationReport.F(value[i])); }
            return text.Append(']').ToString();
        }
    }
}
