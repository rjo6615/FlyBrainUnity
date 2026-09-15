using System.IO;
using UnityEditor;
using UnityEngine;

namespace FlyBrain.UnityBridge.Editor
{
    /// <summary>
    /// Imports the Poly Haven source maps correctly and packs inverted roughness into
    /// the alpha channel expected by URP/Lit's metallic/smoothness workflow.
    /// This is editor-only asset preparation; height is deliberately not applied.
    /// </summary>
    [InitializeOnLoad]
    internal static class BrownMudLeavesMaterialSetup
    {
        const string Root = "Assets/Art/Ground";
        const string DiffusePath = Root + "/textures/brown_mud_leaves_01_diff_4k.jpg";
        const string NormalPath = Root + "/textures/brown_mud_leaves_01_nor_gl_4k.exr";
        const string RoughnessPath = Root + "/textures/brown_mud_leaves_01_rough_4k.exr";
        const string HeightPath = Root + "/textures/brown_mud_leaves_01_disp_4k.png";
        const string PackedPath = Root + "/textures/brown_mud_leaves_01_metallic_smoothness.png";
        const string MaterialPath = Root + "/Materials/Brown Mud Leaves Ground.mat";

        static BrownMudLeavesMaterialSetup() => EditorApplication.delayCall += EnsureAssets;

        [MenuItem("Fly Brain/Art/Rebuild Brown Mud Leaves Ground Material")]
        static void Rebuild()
        {
            AssetDatabase.DeleteAsset(PackedPath);
            EnsureAssets();
        }

        static void EnsureAssets()
        {
            ConfigureTexture(NormalPath, true, false);
            ConfigureTexture(RoughnessPath, false, false);
            ConfigureTexture(HeightPath, false, false);

            if (AssetDatabase.LoadAssetAtPath<Texture2D>(PackedPath) == null)
                PackSmoothness();

            Directory.CreateDirectory(Root + "/Materials");
            var material = AssetDatabase.LoadAssetAtPath<Material>(MaterialPath);
            if (material == null)
            {
                var shader = Shader.Find("Universal Render Pipeline/Lit");
                if (shader == null) return;
                material = new Material(shader) { name = "Brown Mud Leaves Ground" };
                AssetDatabase.CreateAsset(material, MaterialPath);
            }

            material.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(DiffusePath));
            material.SetTexture("_BumpMap", AssetDatabase.LoadAssetAtPath<Texture2D>(NormalPath));
            material.SetFloat("_BumpScale", 1f);
            material.SetTexture("_MetallicGlossMap", AssetDatabase.LoadAssetAtPath<Texture2D>(PackedPath));
            material.SetFloat("_Metallic", 0f);
            material.SetFloat("_Smoothness", 1f);
            material.SetFloat("_SmoothnessTextureChannel", 0f);
            material.EnableKeyword("_NORMALMAP");
            material.EnableKeyword("_METALLICSPECGLOSSMAP");
            EditorUtility.SetDirty(material);
            AssetDatabase.SaveAssets();
        }

        static void ConfigureTexture(string path, bool normalMap, bool sRgb)
        {
            if (AssetImporter.GetAtPath(path) is not TextureImporter importer) return;
            var desiredType = normalMap ? TextureImporterType.NormalMap : TextureImporterType.Default;
            if (importer.textureType == desiredType && importer.sRGBTexture == sRgb) return;
            importer.textureType = desiredType;
            importer.sRGBTexture = sRgb;
            importer.SaveAndReimport();
        }

        static void PackSmoothness()
        {
            if (AssetImporter.GetAtPath(RoughnessPath) is not TextureImporter importer) return;
            var wasReadable = importer.isReadable;
            importer.isReadable = true;
            importer.SaveAndReimport();

            var roughness = AssetDatabase.LoadAssetAtPath<Texture2D>(RoughnessPath);
            if (roughness == null) return;
            var source = roughness.GetPixels();
            var packed = new Texture2D(roughness.width, roughness.height, TextureFormat.RGBA32, true, true);
            for (var i = 0; i < source.Length; i++)
                source[i] = new Color(0f, 0f, 0f, 1f - source[i].r);
            packed.SetPixels(source);
            packed.Apply(true, false);
            File.WriteAllBytes(PackedPath, packed.EncodeToPNG());
            Object.DestroyImmediate(packed);

            importer.isReadable = wasReadable;
            importer.SaveAndReimport();
            AssetDatabase.ImportAsset(PackedPath, ImportAssetOptions.ForceSynchronousImport);
            ConfigureTexture(PackedPath, false, false);
        }
    }
}
