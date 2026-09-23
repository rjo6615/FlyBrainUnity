using UnityEngine;

namespace FlyBrain.M7FReplay
{
    /// <summary>Identifies a renderer-only child created directly from the VIS3 manifest.</summary>
    public sealed class M7FAnatomyObject : MonoBehaviour
    {
        [SerializeField] string meshName;
        [SerializeField] string scientificParent;
        public string MeshName => meshName;
        public string ScientificParent => scientificParent;
        public void Configure(string value, string parent) { meshName = value; scientificParent = parent; }
    }
}
