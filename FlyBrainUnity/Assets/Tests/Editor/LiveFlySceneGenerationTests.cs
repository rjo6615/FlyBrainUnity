using System.IO;
using System.Linq;
using System.Security.Cryptography;
using FlyBrain.LiveFly;
using FlyBrain.M7FReplay;
using NUnit.Framework;
using UnityEditor.SceneManagement;
using UnityEngine;

public sealed class LiveFlySceneGenerationTests
{
    [Test]
    public void SharedBuilderCreatesSavedOutputOnlyLiveFlySceneWithoutChangingCanonicalRig()
    {
        var artifact = Path.Combine(Application.streamingAssetsPath, "M7FValidation", M7FScientificFlyRigDefinition.ArtifactName);
        byte[] before;
        using (var sha = SHA256.Create()) before = sha.ComputeHash(File.ReadAllBytes(artifact));
        var top = LiveFlySceneGenerator.BuildAndSaveScene();

        var rigs = top.GetComponentsInChildren<M7FFlyRig>(true);
        var clients = top.GetComponentsInChildren<LiveFlyClient>(true);
        var cameras = top.GetComponentsInChildren<M7FReplayCamera>(true);
        var ground = top.GetComponentsInChildren<Renderer>(true)
            .First(renderer => renderer.gameObject.name == "Visual Ground — PRESENTATION REFERENCE ONLY");

        Assert.AreEqual(1, rigs.Length);
        Assert.AreEqual(1, clients.Length);
        Assert.AreEqual(1, cameras.Length);
        Assert.That(clients[0].Rig, Is.SameAs(rigs[0]));
        Assert.That(clients[0].Host, Is.EqualTo("127.0.0.1"));
        Assert.That(clients[0].Port, Is.EqualTo(8765));
        Assert.That(clients[0].ConnectOnStart, Is.True);
        Assert.That(clients[0].PresentationInterpolation, Is.False);
        Assert.That(cameras[0].CurrentMode, Is.EqualTo(M7FCameraMode.WorldFixed));
        Assert.AreEqual(42, rigs[0].Joints.Count);
        Assert.That(rigs[0].ValidateMapping(M7FScientificFlyRigDefinition.Names), Is.True);

        Assert.IsNull(ground.GetComponent<Collider>());
        Assert.IsNotNull(ground.sharedMaterial);
        Assert.That(ground.sharedMaterial.name, Does.Contain("LiveFlyGround"));
        Assert.That(ground.sharedMaterial.shader.name, Is.EqualTo("Universal Render Pipeline/Lit"));
        var groundColor = ground.sharedMaterial.GetColor("_BaseColor");
        Assert.That(groundColor.r, Is.EqualTo(LiveFlySceneGenerator.GroundColor.r).Within(.001f));
        Assert.That(groundColor.g, Is.EqualTo(LiveFlySceneGenerator.GroundColor.g).Within(.001f));
        Assert.That(groundColor.b, Is.EqualTo(LiveFlySceneGenerator.GroundColor.b).Within(.001f));
        Assert.That(groundColor.a, Is.EqualTo(LiveFlySceneGenerator.GroundColor.a).Within(.001f));

        Assert.AreEqual(0, rigs[0].GetComponentsInChildren<Rigidbody>(true).Length);
        Assert.AreEqual(0, rigs[0].GetComponentsInChildren<ArticulationBody>(true).Length);
        Assert.AreEqual(0, rigs[0].GetComponentsInChildren<CharacterController>(true).Length);
        Assert.AreEqual(0, rigs[0].GetComponentsInChildren<Animator>(true).Length);
        byte[] after;
        using (var sha = SHA256.Create()) after = sha.ComputeHash(File.ReadAllBytes(artifact));
        CollectionAssert.AreEqual(before, after, "scene creation modified the canonical rig artifact");

        var allowed = new[] { typeof(Transform), typeof(M7FScientificFlyBuilder), typeof(M7FFlyRig), typeof(M7FScientificSkeletonVisibility), typeof(M7FAnatomyPresentation) };
        Assert.IsTrue(rigs[0].GetComponents<Component>().Select(x => x.GetType()).All(type => allowed.Contains(type)), "an unapproved movement/controller component was introduced on the fly");
        Assert.That(rigs[0].ScientificRoot.localPosition, Is.EqualTo(Vector3.zero), "scene creation executed a scientific transition");
        Assert.That(EditorSceneManager.GetActiveScene().path, Is.EqualTo(LiveFlySceneGenerator.ScenePath));
    }

    [Test]
    public void WorldFixedPreservesCameraPoseWhileOrbitTracksTarget()
    {
        var targetObject = new GameObject("target");
        var cameraObject = new GameObject("camera");
        try
        {
            var replayCamera = cameraObject.AddComponent<M7FReplayCamera>();
            replayCamera.Configure(targetObject.transform, .03f);

            var orbitStart = cameraObject.transform.position;
            targetObject.transform.position += new Vector3(1f, .5f, -.25f);
            replayCamera.SendMessage("LateUpdate");
            Assert.That(cameraObject.transform.position, Is.Not.EqualTo(orbitStart));

            replayCamera.SetMode(M7FCameraMode.WorldFixed);
            var lockedPosition = cameraObject.transform.position;
            var lockedRotation = cameraObject.transform.rotation;

            targetObject.transform.position += new Vector3(2f, 0f, 1f);
            replayCamera.SendMessage("LateUpdate");

            Assert.That(cameraObject.transform.position, Is.EqualTo(lockedPosition));
            Assert.That(cameraObject.transform.rotation, Is.EqualTo(lockedRotation));
        }
        finally
        {
            Object.DestroyImmediate(cameraObject);
            Object.DestroyImmediate(targetObject);
        }
    }

}
