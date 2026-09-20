using System;
using System.Collections.Generic;
using UnityEngine;

namespace FlyBrain.M7FReplay
{
    /// <summary>
    /// Frozen visualization metadata transcribed from fruitfly.xml.  MuJoCo lists
    /// coincident hinges in XML order: abduct(z), twist(y), extend(x) at the coxa,
    /// then twist(y), extend(x) at the femur, followed by tibia/tarsus extend(x).
    /// A reflection B(x,y,z)=(x,z,y) changes an axial vector as det(B)B, hence the
    /// Unity hinge axes below are -B(sourceAxis), not a guessed component swap.
    /// </summary>
    public static class M7FScientificFlyRigDefinition
    {
        public const int JointCount = 42;
        public const string Evidence = "fly-brain-main/body/flybody/fruitfly.xml lines 92-190, 460-655";
        public static readonly string[] Legs = { "LF", "LM", "LH", "RF", "RM", "RH" };
        static readonly string[] Suffixes = { "Coxa", "Coxa_roll", "Coxa_yaw", "Femur", "Femur_roll", "Tibia", "Tarsus1" };

        public static readonly string[] CanonicalNames = BuildNames();
        static string[] BuildNames()
        {
            var result = new string[JointCount]; var n = 0;
            foreach (var leg in Legs) foreach (var suffix in Suffixes) result[n++] = "joint_" + leg + suffix;
            return result;
        }

        public static Vector3 SourceAxis(string canonicalName)
        {
            if (canonicalName.EndsWith("Coxa_roll", StringComparison.Ordinal)) return Vector3.forward;
            if (canonicalName.EndsWith("Coxa_yaw", StringComparison.Ordinal) || canonicalName.EndsWith("Femur_roll", StringComparison.Ordinal)) return Vector3.up;
            return Vector3.right;
        }

        public static Vector3 UnityAxis(string canonicalName) => M7FCoordinates.SourceAxialToUnity(SourceAxis(canonicalName));

        // XML order is significant for multiple hinges on one MuJoCo body.
        public static string[] HierarchyOrder(string leg) => new[] {
            "joint_" + leg + "Coxa_roll", "joint_" + leg + "Coxa_yaw", "joint_" + leg + "Coxa",
            "joint_" + leg + "Femur_roll", "joint_" + leg + "Femur", "joint_" + leg + "Tibia", "joint_" + leg + "Tarsus1"
        };

        public static bool IsCanonical(string name) => Array.IndexOf(CanonicalNames, name) >= 0;
        public static IReadOnlyList<string> Names => CanonicalNames;

        // w,x,y,z values copied verbatim from the six coxa/femur/tibia/tarsus bodies in the frozen MJCF.
        static readonly float[,,] BodyQuaternions = {
            { {-.532f,.787f,-.311f,-.0229f}, {0,0,.252f,.968f}, {.186f,.162f,.677f,-.694f}, {.039f,.998f,.00674f,.0474f} },
            { {-.371f,.917f,-.126f,-.0722f}, {0,0,.128f,.992f}, {.107f,.0834f,.656f,-.742f}, {-.148f,.978f,-.0216f,-.143f} },
            { {.681f,-.529f,-.0882f,.498f}, {0,0,-.668f,-.744f}, {-.117f,-.104f,-.711f,.685f}, {-.23f,.963f,-.033f,-.138f} },
            { {.319f,.011f,-.543f,-.777f}, {0,0,.261f,.965f}, {.163f,.148f,.688f,-.692f}, {-.0745f,-.995f,.0133f,.0704f} },
            { {.126f,-.0709f,-.374f,-.916f}, {0,0,.134f,.991f}, {.0902f,.103f,.659f,-.739f}, {.15f,-.982f,.0172f,.113f} },
            { {-.0854f,-.505f,-.673f,-.534f}, {0,0,.661f,.751f}, {-.121f,-.111f,-.708f,.686f}, {.223f,-.965f,.0313f,.136f} }
        };
        static readonly Vector3[,] BodyPositions = {
            { new(.0317f,.0209f,-.0272f), new(0,.0437f,0), new(0,.0697f,0), new(0,-.051f,.00175f) },
            { new(-.0144f,.0241f,-.0425f), new(0,.0281f,0), new(0,.083f,0), new(0,-.0668f,.00175f) },
            { new(-.0377f,.0192f,-.0402f), new(-.00398f,.0232f,-.00668f), new(0,.0779f,.00000016f), new(0,-.0715f,.00175f) },
            { new(.0317f,-.0209f,-.0272f), new(0,-.0436f,0), new(0,-.0698f,0), new(0,.0515f,-.00175f) },
            { new(-.0144f,-.0241f,-.0425f), new(0,-.0282f,0), new(0,-.084f,0), new(0,.0665f,-.00175f) },
            { new(-.0377f,-.0192f,-.0402f), new(.00383f,-.0232f,.0066f), new(0,-.077f,.000000196f), new(0,.0721f,-.00175f) }
        };

        public static Quaternion BodyReferenceRotation(string leg, int segment)
        {
            var index = Array.IndexOf(Legs, leg); if (index < 0 || segment < 0 || segment > 3) throw new ArgumentOutOfRangeException();
            var source = new Quaternion(BodyQuaternions[index,segment,1], BodyQuaternions[index,segment,2], BodyQuaternions[index,segment,3], BodyQuaternions[index,segment,0]);
            return M7FCoordinates.SourceQuaternionToUnity(source);
        }
        public static Vector3 BodyReferencePosition(string leg, int segment)
        {
            var index = Array.IndexOf(Legs, leg); if (index < 0 || segment < 0 || segment > 3) throw new ArgumentOutOfRangeException();
            return M7FCoordinates.SourcePositionToUnity(BodyPositions[index, segment]) * M7FCoordinates.MillimetresToUnity;
        }
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
            var forward = SourcePositionToUnity(source * Vector3.forward);
            var up = SourcePositionToUnity(source * Vector3.up);
            return Quaternion.LookRotation(forward, up);
        }

        public static bool IsFinite(Quaternion q) => !(float.IsNaN(q.x) || float.IsInfinity(q.x) || float.IsNaN(q.y) || float.IsInfinity(q.y) || float.IsNaN(q.z) || float.IsInfinity(q.z) || float.IsNaN(q.w) || float.IsInfinity(q.w));
    }
}
