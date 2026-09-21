using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using FlyBrain.M7FReplay;
using NUnit.Framework;
using UnityEngine;

namespace FlyBrain.Tests
{
    /// <summary>VIS3 presentation gate; intentionally separate from the unchanged VIS2 numerical gate.</summary>
    public sealed class M7FVis3AnatomyTests
    {
        static string Root => Path.Combine(Application.streamingAssetsPath, M7FAnatomyPresentation.DirectoryName);

        [Test] public void ManifestIsTheCompleteExtractedSixtyNineMeshInventory()
        {
            var manifest = M7FAnatomyPresentation.LoadManifest(Root);
            Assert.That(manifest.meshes, Has.Length.EqualTo(69));
            var placements = new HashSet<string>();
            foreach (var item in manifest.meshes)
            {
                Assert.That(placements.Add(item.mesh_name), Is.True, "duplicate placement " + item.mesh_name);
                Assert.That(item.body, Is.Not.Empty); Assert.That(item.scientific_body, Is.Not.Empty);
                Assert.That(item.source_stl, Does.EndWith(".stl")); Assert.That(item.role, Is.EqualTo("visual"));
                Assert.That(File.Exists(Path.Combine(Root, item.mesh_name + ".obj")), Is.True, item.mesh_name);
            }
            Assert.That(Directory.GetFiles(Root, "*.obj"), Has.Length.EqualTo(69));
        }

        [Test] public void AnatomyAttachesToManifestParentsWithOnlyRemainingLocalTransform()
        {
            var go = new GameObject("VIS3 anatomy test");
            try
            {
                go.AddComponent<M7FScientificFlyBuilder>().Rebuild(); var rig = go.GetComponent<M7FFlyRig>();
                var before = new Dictionary<Transform, (Vector3 p, Quaternion q, Vector3 s)>();
                foreach (var t in rig.ScientificRoot.GetComponentsInChildren<Transform>(true)) before[t] = (t.localPosition, t.localRotation, t.localScale);
                var manifest = M7FAnatomyPresentation.LoadManifest(Root); var presentation = go.AddComponent<M7FAnatomyPresentation>(); presentation.Rebuild();
                Assert.That(presentation.LoadedCount, Is.EqualTo(69));
                foreach (var item in manifest.meshes)
                {
                    M7FAnatomyObject found = null;
                    foreach (var candidate in go.GetComponentsInChildren<M7FAnatomyObject>(true)) if (candidate.MeshName == item.mesh_name) found = candidate;
                    Assert.That(found, Is.Not.Null, item.mesh_name); Assert.That(found.transform.parent.name, Is.EqualTo(item.scientific_body));
                    var expectedPosition = M7FCoordinates.SourcePositionToUnity(M7FScientificFlyRigDefinition.Vector(item.position)) * M7FCoordinates.MillimetresToUnity;
                    var expectedRotation = M7FCoordinates.SourceQuaternionToUnity(M7FScientificFlyRigDefinition.QuaternionWxyz(item.quaternion_wxyz));
                    Assert.That((found.transform.localPosition - expectedPosition).magnitude, Is.LessThan(1e-7f), item.mesh_name);
                    Assert.That(Quaternion.Angle(found.transform.localRotation, expectedRotation), Is.LessThan(1e-5f), item.mesh_name);
                    Assert.That(found.transform.localScale, Is.EqualTo(Vector3.one), "baked 0.1 scale must not be applied again");
                    Assert.That(found.transform.GetChild(0).localScale, Is.EqualTo(Vector3.one), "no second reflection or scaling");
                }
                M7FAnatomyPresentation.ValidatePresentation(go.transform);
                foreach (var pair in before) { Assert.That(pair.Key.localPosition, Is.EqualTo(pair.Value.p)); Assert.That(pair.Key.localRotation, Is.EqualTo(pair.Value.q)); Assert.That(pair.Key.localScale, Is.EqualTo(pair.Value.s)); }
            }
            finally { Object.DestroyImmediate(go); }
        }

        [Test] public void GeneratedObjIsAlreadyConvertedAndHasNoRuntimeHandednessOperation()
        {
            var mesh = M7FGeneratedObjLoader.Load(Path.Combine(Root, "mesh_Thorax.obj"), "audit");
            try
            {
                Assert.That((mesh.vertices[0] - new Vector3(-0.0101651196f, 0.0370736641f, 0.000752501956f)).magnitude, Is.LessThan(1e-9f));
                CollectionAssert.AreEqual(new[] { 0, 2, 1 }, new[] { mesh.triangles[0], mesh.triangles[1], mesh.triangles[2] });
            }
            finally { Object.DestroyImmediate(mesh); }
        }

        [Test] public void ScientificArtifactsAndCanonicalReplaysRemainByteIdentical()
        {
            Assert.That(Sha("M7FValidation/m7f_authoritative_rig.json"), Is.EqualTo("d8cd7e58bb33fff5e102484d937100d7afd7dc1f4156b39dc2a27f65c0c29eb7"));
            Assert.That(Sha("M7FValidation/m7f_mujoco_reference_frames.json"), Is.EqualTo("cd7c372214df6dc71071d05114ccdc2ccdca0f6dd48442797980772720f0fa5d"));
            var loader = new GameObject("hash validation").AddComponent<M7FReplayLoader>();
            try { loader.Load(); Assert.That(loader.Enabled, Is.Not.Null); Assert.That(loader.Disabled, Is.Not.Null); } finally { Object.DestroyImmediate(loader.gameObject); }
        }

        static string Sha(string relative)
        {
            using var stream = File.OpenRead(Path.Combine(Application.streamingAssetsPath, relative)); using var hash = SHA256.Create();
            return System.BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
        }
    }
}
