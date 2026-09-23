using UnityEngine;
using UnityEngine.InputSystem;

namespace FlyBrain.M7FReplay
{
    public enum M7FCameraMode { Orbit, FollowBody, FixedSide, FixedTop, FixedFront, FixedRear }
    public sealed class M7FReplayCamera : MonoBehaviour
    {
        [SerializeField] Transform target;
        [SerializeField] M7FCameraMode mode;
        [SerializeField] float distance = 4f, framingRadius = M7FScientificFlyBuilder.ApproximateVisualRadius, yaw = 35f, pitch = 25f;
        [SerializeField] M7FFlyRig comparisonLeft, comparisonRight;
        void LateUpdate()
        {
            if (target == null) return;
            var mouse = Mouse.current;
            if (mode == M7FCameraMode.Orbit && mouse != null && mouse.rightButton.isPressed) { var d = mouse.delta.ReadValue(); yaw += d.x * .15f; pitch = Mathf.Clamp(pitch - d.y * .15f, -80f, 80f); }
            if (mouse != null) distance = Mathf.Clamp(distance - mouse.scroll.ReadValue().y * .002f, .2f, 30f);
            var rotation = mode switch { M7FCameraMode.FixedSide => Quaternion.Euler(0, 90, 0), M7FCameraMode.FixedTop => Quaternion.Euler(90, 0, 0), M7FCameraMode.FixedFront => Quaternion.Euler(0, 0, 0), M7FCameraMode.FixedRear => Quaternion.Euler(0, 180, 0), _ => Quaternion.Euler(pitch, yaw, 0) };
            var center=target.position;
            if(comparisonLeft!=null) { var includeRight=comparisonRight!=null&&comparisonRight.gameObject.activeInHierarchy; center=includeRight?(comparisonLeft.ScientificRoot.position+comparisonRight.ScientificRoot.position)*.5f:comparisonLeft.ScientificRoot.position; var span=includeRight?Vector3.Distance(comparisonLeft.ScientificRoot.position,comparisonRight.ScientificRoot.position):0; distance=Mathf.Max(distance,(span+framingRadius*2f)*1.15f); }
            transform.SetPositionAndRotation(center - rotation * Vector3.forward * distance, rotation);
        }
        public void SetMode(M7FCameraMode value) => mode = value;
        public void ResetView() { distance = 4f; yaw = 35f; pitch = 25f; mode = M7FCameraMode.Orbit; }
        public void Configure(Transform viewTarget, float visualRadius) { target = viewTarget; framingRadius = Mathf.Max(.1f, visualRadius); distance = framingRadius * 3f; ResetView(); distance = framingRadius * 3f; }
        public void ConfigureComparison(M7FFlyRig left,M7FFlyRig right) { comparisonLeft=left; comparisonRight=right; }
    }
}
