using System;
using UnityEngine;

namespace FlyBrain.M7FReplay
{
    /// <summary>Optional renderer-only visibility control for the scientific skeleton.</summary>
    public sealed class M7FScientificSkeletonVisibility : MonoBehaviour
    {
        [SerializeField] bool visible;
        Renderer[] renderers = Array.Empty<Renderer>();
        public bool Visible => visible;
        public void Configure(Renderer[] scientificRenderers) => renderers = scientificRenderers ?? Array.Empty<Renderer>();
        public void SetVisible(bool value) { visible = value; foreach (var renderer in renderers) if (renderer != null) renderer.enabled = value; }
    }
}
