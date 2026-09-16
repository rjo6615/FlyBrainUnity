using System;
using UnityEngine;
using UnityEngine.Rendering;

namespace FlyBrain.UnityBridge
{
    /// <summary>Runtime-safe material checks shared by the debug HUD and editor validator.</summary>
    public static class FlyMaterialValidation
    {
        public const string BodyMaterialName = "TheFly URP";
        public const string WingMaterialName = "Wings URP";

        public static bool Validate(Renderer[] renderers, out string reason)
        {
            if (renderers == null || renderers.Length == 0) { reason = "no renderers"; return false; }
            var body = false; var wings = false;
            foreach (var renderer in renderers)
            {
                if (renderer == null) { reason = "null renderer"; return false; }
                var mesh = MeshFor(renderer);
                if (mesh == null || !mesh.HasVertexAttribute(VertexAttribute.TexCoord0)) { reason = $"{renderer.name}: missing UV0"; return false; }
                var materials = renderer.sharedMaterials;
                if (materials.Length == 0) { reason = $"{renderer.name}: no material slots"; return false; }
                foreach (var material in materials)
                {
                    if (material == null || material.shader == null || !material.shader.isSupported) { reason = $"{renderer.name}: missing/unsupported material"; return false; }
                    if (!material.shader.name.Equals("Universal Render Pipeline/Lit", StringComparison.Ordinal)) { reason = $"{material.name}: not URP/Lit"; return false; }
                    if (!material.HasProperty("_BaseMap") || material.GetTexture("_BaseMap") == null) { reason = $"{material.name}: missing Base Map"; return false; }
                    if (material.name.StartsWith(BodyMaterialName, StringComparison.Ordinal)) body = material.GetTexture("_BumpMap") != null;
                    if (material.name.StartsWith(WingMaterialName, StringComparison.Ordinal))
                        wings = material.HasProperty("_Surface") && material.GetFloat("_Surface") > .5f &&
                            material.HasProperty("_Cull") && material.GetFloat("_Cull") == 0f;
                }
            }
            if (!body) { reason = "body material or normal map missing"; return false; }
            if (!wings) { reason = "transparent double-sided wing material missing"; return false; }
            reason = "OK"; return true;
        }

        public static Mesh MeshFor(Renderer renderer)
        {
            if (renderer is SkinnedMeshRenderer skinned) return skinned.sharedMesh;
            var filter = renderer.GetComponent<MeshFilter>();
            return filter == null ? null : filter.sharedMesh;
        }
    }
}
