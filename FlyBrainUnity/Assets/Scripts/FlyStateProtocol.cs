using System;
using UnityEngine;

namespace FlyBrain.UnityBridge
{
    [Serializable] public sealed class MessageHeader { public string type; public int protocol_version; }
    [Serializable] public sealed class MovementState { public float left_drive, right_drive, speed_mm_s; }
    [Serializable]
    public sealed class FlyStateMessage
    {
        public string type; public int protocol_version; public double time;
        public float[] position, orientation, rotation; public string behavior;
        public MovementState movement;
        public bool IsValid => type == "fly_state" && protocol_version == 1 &&
            position?.Length == 3 && orientation?.Length == 3;
    }
    [Serializable]
    public sealed class EnvironmentObject
    {
        public string id, kind; public float[] position, size, color; public bool dynamic;
    }
    [Serializable] public sealed class EnvironmentDefinition
    {
        public string type; public int protocol_version; public EnvironmentObject[] objects;
        public bool IsValid => type == "environment_definition" && protocol_version == 1 && objects != null;
    }
    [Serializable] public sealed class EnvironmentTransform { public string id; public float[] position; }
    [Serializable] public sealed class EnvironmentState
    {
        public string type; public int protocol_version; public double time; public EnvironmentTransform[] objects;
    }

    /// <summary>The single presentation-only calibration for every Python dimension.</summary>
    public static class WorldVisualScale
    {
        // 1 Python millimetre = 0.1 Unity visual unit. Scientific wire values are unchanged.
        public const float UnityUnitsPerMillimetre = 0.1f;
        public static Vector3 Position(float[] xyz) =>
            new(xyz[0] * UnityUnitsPerMillimetre, xyz[2] * UnityUnitsPerMillimetre,
                xyz[1] * UnityUnitsPerMillimetre);
        public static Vector3 Dimensions(float[] xyz) =>
            new(xyz[0] * UnityUnitsPerMillimetre, xyz[2] * UnityUnitsPerMillimetre,
                xyz[1] * UnityUnitsPerMillimetre);
        public static Quaternion Orientation(float[] xyz)
        {
            var forward = new Vector3(xyz[0], xyz[2], xyz[1]);
            return forward.sqrMagnitude > 1e-6f
                ? Quaternion.LookRotation(forward.normalized, Vector3.up) : Quaternion.identity;
        }
    }
}
