using UnityEngine;

namespace FlyBrain.M7FReplay
{
    /// <summary>Transform-only annotation. It has no Rigidbody and contains no force API.</summary>
    public sealed class M9DForceArrow : MonoBehaviour
    {
        [SerializeField] M9DReplayController controller; [SerializeField] Transform authoritativeThorax; [SerializeField] float illustrativeLength = .4f;
        public const string Annotation = "RECORDED EXTERNAL PERTURBATION";
        public const string Detail = "Canonical magnitude 1.024 | canonical interval [500, 520) ms | arrow size is presentation-only, NOT a physical force scale";
        public Vector3 UnityDirection => Vector3.forward; public float IllustrativeLength => illustrativeLength;
        void LateUpdate() { foreach (var renderer in GetComponentsInChildren<Renderer>(true)) renderer.enabled=controller != null && controller.ForceActive; if (authoritativeThorax != null) { transform.position=authoritativeThorax.position; transform.rotation=Quaternion.LookRotation(UnityDirection); } }
        public void Configure(M9DReplayController value, Transform thorax) { controller=value; authoritativeThorax=thorax; }
    }
}
