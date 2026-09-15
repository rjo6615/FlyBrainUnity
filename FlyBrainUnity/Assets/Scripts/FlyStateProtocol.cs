using System;
using UnityEngine;

namespace FlyBrain.UnityBridge
{
    [Serializable]
    public sealed class MovementState
    {
        public float left_drive;
        public float right_drive;
        public float speed_mm_s;
    }

    [Serializable]
    public sealed class FlyStateMessage
    {
        public string type;
        public int protocol_version;
        public double time;
        public float[] position;
        public float[] orientation;
        public float[] rotation;
        public string behavior;
        public MovementState movement;

        public bool IsValid => type == "fly_state" && protocol_version == 1 &&
                               position?.Length == 3 && orientation?.Length == 3;
    }

    /// <summary>Only this class knows how FlyGym axes map into Unity.</summary>
    public static class FlyGymCoordinates
    {
        public const float MillimetresToMetres = 0.001f;

        // FlyGym is right-handed and Z-up. Unity is left-handed and Y-up.
        // Keeping X and swapping Y/Z produces the required handedness change.
        public static Vector3 Position(float[] source)
        {
            return new Vector3(source[0], source[2], source[1]) * MillimetresToMetres;
        }

        public static Quaternion Orientation(float[] source)
        {
            var forward = new Vector3(source[0], source[2], source[1]);
            return forward.sqrMagnitude > 0.000001f
                ? Quaternion.LookRotation(forward.normalized, Vector3.up)
                : Quaternion.identity;
        }
    }
}
