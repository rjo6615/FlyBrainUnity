using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using UnityEngine;
using UnityEngine.Rendering;

namespace FlyBrain.M7FReplay
{
    [Serializable] public sealed class M7FAnatomyManifest
    {
        public string schema, flygym_version, mjcf, mjcf_sha256, basis;
        public float presentation_scale;
        public M7FAnatomyPlacement[] meshes;
    }

    [Serializable] public sealed class M7FAnatomyPlacement
    {
        public string mesh_name, source_stl, body, scientific_body, role;
        public double[] mesh_scale, position, quaternion_wxyz;
    }

    /// <summary>Deterministic, deliberately small loader for the generated v/f-only VIS3 OBJ dialect.</summary>
    public static class M7FGeneratedObjLoader
    {
        public static Mesh Load(string path, string name)
        {
            var vertices = new List<Vector3>(); var triangles = new List<int>();
            foreach (var raw in File.ReadLines(path))
            {
                if (raw.StartsWith("v ", StringComparison.Ordinal))
                {
                    var p = raw.Split((char[])null, StringSplitOptions.RemoveEmptyEntries);
                    if (p.Length != 4) throw new InvalidDataException("VIS3 OBJ vertex must have three coordinates: " + path);
                    vertices.Add(new Vector3(F(p[1]), F(p[2]), F(p[3]))); // already scaled and basis-converted by VIS3A
                }
                else if (raw.StartsWith("f ", StringComparison.Ordinal))
                {
                    var p = raw.Split((char[])null, StringSplitOptions.RemoveEmptyEntries);
                    if (p.Length != 4) throw new InvalidDataException("VIS3 OBJ must contain triangles only: " + path);
                    triangles.Add(I(p[1], vertices.Count)); triangles.Add(I(p[2], vertices.Count)); triangles.Add(I(p[3], vertices.Count));
                }
                else if (raw.Length != 0 && raw[0] != '#') throw new InvalidDataException("Unsupported VIS3 OBJ statement: " + raw);
            }
            if (vertices.Count == 0 || triangles.Count == 0) throw new InvalidDataException("VIS3 OBJ is empty: " + path);
            var mesh = new Mesh { name = name, indexFormat = vertices.Count > 65535 ? IndexFormat.UInt32 : IndexFormat.UInt16 };
            mesh.SetVertices(vertices); mesh.SetTriangles(triangles, 0, true); mesh.RecalculateNormals(); mesh.RecalculateBounds(); return mesh;
        }
        static float F(string value) => float.Parse(value, NumberStyles.Float, CultureInfo.InvariantCulture);
        static int I(string value, int vertexCount)
        {
            if (value.IndexOf('/') >= 0 || !int.TryParse(value, NumberStyles.Integer, CultureInfo.InvariantCulture, out var i) || i <= 0 || i > vertexCount)
                throw new InvalidDataException("VIS3 OBJ face index is invalid: " + value);
            return i - 1;
        }
    }

    /// <summary>Attaches baked anatomy beneath validated body transforms; it never writes to those transforms.</summary>
    public sealed class M7FAnatomyPresentation : MonoBehaviour
    {
        public const string DirectoryName = "M7FAnatomy";
        public const string ManifestName = "m7f_vis3_anatomy.json";
        public const int ExpectedCount = 69;
        [SerializeField] Material anatomyMaterial;
        public Transform PresentationRoot { get; private set; }
        public int LoadedCount { get; private set; }

        public static M7FAnatomyManifest LoadManifest(string root = null)
        {
            root ??= Path.Combine(Application.streamingAssetsPath, DirectoryName);
            var manifest = JsonUtility.FromJson<M7FAnatomyManifest>(File.ReadAllText(Path.Combine(root, ManifestName)));
            if (manifest == null || manifest.schema != "M7F-VIS3-ANATOMY.1" || manifest.meshes == null || manifest.meshes.Length != ExpectedCount ||
                manifest.basis != "[x,y,z] -> [x,z,y]" || !Mathf.Approximately(manifest.presentation_scale, M7FCoordinates.MillimetresToUnity))
                throw new InvalidDataException("VIS3 anatomy manifest schema, count, basis, or baked scale is invalid.");
            return manifest;
        }

        [ContextMenu("BUILD AUTHORITATIVE ANATOMY (PRESENTATION ONLY)")]
        public void Rebuild()
        {
            var rig = GetComponent<M7FFlyRig>();
            if (rig == null || rig.ScientificRoot == null) throw new InvalidOperationException("Build the validated scientific rig before VIS3 anatomy.");
            foreach (var old in GetComponentsInChildren<M7FAnatomyObject>(true)) SafeDestroy(old.gameObject);
            if (PresentationRoot != null) SafeDestroy(PresentationRoot.gameObject);
            var directory = Path.Combine(Application.streamingAssetsPath, DirectoryName); var manifest = LoadManifest(directory);
            var scientific = new Dictionary<string, Transform>(StringComparer.Ordinal);
            foreach (var value in rig.ScientificRoot.GetComponentsInChildren<Transform>(true))
                if (!scientific.ContainsKey(value.name)) scientific.Add(value.name, value);
            PresentationRoot = new GameObject("Authoritative Anatomy — PRESENTATION ONLY").transform;
            PresentationRoot.SetParent(transform, false); LoadedCount = 0;
            var material = anatomyMaterial != null ? anatomyMaterial : MakeMaterial();
            var names = new HashSet<string>(StringComparer.Ordinal);
            foreach (var placement in manifest.meshes)
            {
                if (!names.Add(placement.mesh_name)) throw new InvalidDataException("Duplicate VIS3 placement: " + placement.mesh_name);
                if (placement.role != "visual") throw new InvalidDataException("Non-visual VIS3 geometry is forbidden: " + placement.mesh_name);
                if (!scientific.TryGetValue(placement.scientific_body, out var parent)) throw new InvalidDataException("Missing scientific parent: " + placement.scientific_body);
                var path = Path.Combine(directory, placement.mesh_name + ".obj"); if (!File.Exists(path)) throw new FileNotFoundException("Missing VIS3 OBJ", path);
                var anchor = new GameObject("Presentation — " + placement.mesh_name); anchor.transform.SetParent(parent, false);
                anchor.transform.localPosition = M7FCoordinates.SourcePositionToUnity(M7FScientificFlyRigDefinition.Vector(placement.position)) * M7FCoordinates.MillimetresToUnity;
                anchor.transform.localRotation = M7FCoordinates.SourceQuaternionToUnity(M7FScientificFlyRigDefinition.QuaternionWxyz(placement.quaternion_wxyz));
                anchor.transform.localScale = Vector3.one; // scale and reflection are already baked into OBJ vertices
                var go = new GameObject(placement.mesh_name); go.transform.SetParent(anchor.transform, false);
                go.AddComponent<MeshFilter>().sharedMesh = M7FGeneratedObjLoader.Load(path, placement.mesh_name);
                go.AddComponent<MeshRenderer>().sharedMaterial = material; anchor.AddComponent<M7FAnatomyObject>().Configure(placement.mesh_name, placement.scientific_body); LoadedCount++;
            }
            ValidatePresentation(transform, LoadedCount);
        }

        public static void ValidatePresentation(Transform root, int expectedCount = ExpectedCount)
        {
            var objects = root == null ? Array.Empty<M7FAnatomyObject>() : root.GetComponentsInChildren<M7FAnatomyObject>(true);
            if (objects.Length != expectedCount) throw new InvalidOperationException("VIS3 presentation count mismatch.");
            foreach (var item in objects) foreach (var component in item.GetComponentsInChildren<Component>(true))
            {
                if (component is Rigidbody || component is Collider || component is ArticulationBody || component is CharacterController ||
                    component is Joint || component is Animator || component is Animation)
                    throw new InvalidOperationException("Physics, animation, joints, and IK-capable components are forbidden in VIS3 presentation.");
                if (component is MonoBehaviour && !(component is M7FAnatomyObject))
                    throw new InvalidOperationException("Unapproved presentation behaviour (including possible IK) is forbidden: " + component.GetType().FullName);
                var t = component as Transform;
                if (t != null && (t.localScale.x < 0 || t.localScale.y < 0 || t.localScale.z < 0)) throw new InvalidOperationException("Negative-scale reflection is forbidden in VIS3 presentation.");
            }
        }

        static Material MakeMaterial() { var shader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard"); return new Material(shader) { name = "M7F authoritative anatomy", color = new Color(.28f, .20f, .14f) }; }
        static void SafeDestroy(UnityEngine.Object value) { if (Application.isPlaying) UnityEngine.Object.Destroy(value); else UnityEngine.Object.DestroyImmediate(value); }
    }
}
