using UnityEngine;
using UnityEngine.InputSystem;

namespace FlyBrain.M7FReplay
{
    public enum M7FCameraMode { Orbit, FollowBody, FixedSide, FixedTop }
    public sealed class M7FReplayCamera : MonoBehaviour
    {
        [SerializeField] Transform target;
        [SerializeField] M7FCameraMode mode;
        [SerializeField] float distance = 4f, yaw = 35f, pitch = 25f;
        void LateUpdate()
        {
            if (target == null) return;
            var mouse = Mouse.current;
            if (mode == M7FCameraMode.Orbit && mouse != null && mouse.rightButton.isPressed) { var d = mouse.delta.ReadValue(); yaw += d.x * .15f; pitch = Mathf.Clamp(pitch - d.y * .15f, -80f, 80f); }
            if (mouse != null) distance = Mathf.Clamp(distance - mouse.scroll.ReadValue().y * .002f, .2f, 30f);
            var rotation = mode switch { M7FCameraMode.FixedSide => Quaternion.Euler(0, 90, 0), M7FCameraMode.FixedTop => Quaternion.Euler(90, 0, 0), _ => Quaternion.Euler(pitch, yaw, 0) };
            transform.SetPositionAndRotation(target.position - rotation * Vector3.forward * distance, rotation);
        }
        public void SetMode(M7FCameraMode value) => mode = value;
        public void ResetView() { distance = 4f; yaw = 35f; pitch = 25f; mode = M7FCameraMode.Orbit; }
    }
}
