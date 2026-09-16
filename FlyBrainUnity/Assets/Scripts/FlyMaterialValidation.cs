using System;
using System.Collections.Generic;
using System.Text;
using UnityEngine;
using UnityEngine.Rendering;

namespace FlyBrain.UnityBridge
{
    /// <summary>Runtime-safe material checks shared by the debug HUD and editor validator.</summary>
    public static class FlyMaterialValidation
    {
        public const string BodyMaterialName = "TheFly_URP";
        public const string WingMaterialName = "Wings_URP";

        public static bool Validate(Renderer[] renderers, out string reason)
        {
            var failures = new List<string>();
            if (renderers == null || renderers.Length == 0) failures.Add("renderer missing: live fly has no renderers");
            var body = false; var wings = false;
            foreach (var renderer in renderers ?? Array.Empty<Renderer>())
            {
                if (renderer == null) { failures.Add("renderer missing: null renderer entry"); continue; }
                var mesh = MeshFor(renderer);
                if (mesh == null) failures.Add($"{renderer.name}: mesh missing");
                else if (!mesh.HasVertexAttribute(VertexAttribute.TexCoord0) || mesh.uv == null || mesh.uv.Length != mesh.vertexCount)
                    failures.Add($"{renderer.name}/{mesh.name}: UV0 missing or count {mesh.uv?.Length ?? 0} != vertex count {mesh.vertexCount}");
                var materials = renderer.sharedMaterials;
                if (materials.Length == 0) failures.Add($"{renderer.name}: no material slots");
                for (var slot = 0; slot < materials.Length; slot++)
                {
                    var material = materials[slot];
                    if (material == null) { failures.Add($"{renderer.name} slot {slot}: material null"); continue; }
                    if (material.shader == null || !material.shader.isSupported) failures.Add($"{renderer.name} slot {slot}/{material.name}: shader missing or unsupported");
                    else if (!material.shader.name.Equals("Universal Render Pipeline/Lit", StringComparison.Ordinal)) failures.Add($"{renderer.name} slot {slot}/{material.name}: wrong shader '{material.shader.name}'");
                    if (!material.HasProperty("_BaseMap") || material.GetTexture("_BaseMap") == null) failures.Add($"{renderer.name} slot {slot}/{material.name}: Base Map null");
                    if (material.name.Equals(BodyMaterialName, StringComparison.Ordinal))
                    {
                        body = true;
                        if (material.GetTexture("_BumpMap") == null) failures.Add($"{material.name}: Normal Map null");
                        if (material.GetTexture("_MetallicGlossMap") == null || material.GetTexture("_OcclusionMap") == null) failures.Add($"{material.name}: metallic/smoothness or occlusion map null");
                        if (material.GetColor("_BaseColor") != Color.white) failures.Add($"{material.name}: Base Color tint is not white ({material.GetColor("_BaseColor")})");
                    }
                    if (material.name.Equals(WingMaterialName, StringComparison.Ordinal))
                    {
                        wings = true;
                        if (!material.HasProperty("_Surface") || material.GetFloat("_Surface") <= .5f) failures.Add($"{material.name}: wing material not transparent");
                        if (!material.HasProperty("_Cull") || material.GetFloat("_Cull") != 0f) failures.Add($"{material.name}: wing material not double-sided");
                        if (!material.HasProperty("_ZWrite") || material.GetFloat("_ZWrite") != 0f) failures.Add($"{material.name}: wing ZWrite must be off");
                    }
                }
            }
            if (!body) failures.Add($"body material mismatch: expected {BodyMaterialName}");
            if (!wings) failures.Add($"wing material mismatch: expected {WingMaterialName}");
            reason = failures.Count == 0 ? "OK" : string.Join("\n", failures);
            return failures.Count == 0;
        }

        public static Mesh MeshFor(Renderer renderer)
        {
            if (renderer is SkinnedMeshRenderer skinned) return skinned.sharedMesh;
            var filter = renderer.GetComponent<MeshFilter>();
            return filter == null ? null : filter.sharedMesh;
        }
    }
}
