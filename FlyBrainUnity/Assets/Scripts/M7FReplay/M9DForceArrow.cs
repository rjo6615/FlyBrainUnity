using UnityEngine;

namespace FlyBrain.M7FReplay
{
    /// <summary>Transform-only annotation. It has no Rigidbody and contains no force API.</summary>
    public sealed class M9DForceArrow : MonoBehaviour
    {
        [SerializeField] M9DReplayController controller; [SerializeField] Transform authoritativeThorax; [SerializeField] float illustrativeLength = .12f;
        public const string Annotation = "External perturbation — visualization only";
        public Vector3 UnityDirection => Vector3.forward; public float IllustrativeLength => illustrativeLength;
        void LateUpdate() { foreach (var renderer in GetComponentsInChildren<Renderer>(true)) renderer.enabled=controller != null && controller.ForceActive; if (authoritativeThorax != null) { transform.position=authoritativeThorax.position; transform.rotation=Quaternion.LookRotation(UnityDirection); } }
        public void Configure(M9DReplayController value, Transform thorax) { controller=value; authoritativeThorax=thorax; }
    }
}
