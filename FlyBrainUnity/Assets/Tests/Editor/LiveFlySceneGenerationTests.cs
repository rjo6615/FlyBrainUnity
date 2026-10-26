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
    // SendMessage of a lifecycle callback asserts ShouldRunBehaviour in EditMode.
    // Invoke the actual callback directly without changing runtime execution mode.
    static void TickCamera(M7FReplayCamera view)
    {
        typeof(M7FReplayCamera).GetMethod("LateUpdate",
            System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic)
            .Invoke(view, null);
    }

    [TestCase(1.777778f, false)]
    [TestCase(.5625f, false)]
    [TestCase(.5625f, true)]
    public void FrameRenderedTargetFitsOffsetPoseAndKeepsWorldReference(float aspect, bool orthographic)
    {
        var target = GameObject.CreatePrimitive(PrimitiveType.Cube);
        var cameraObject = new GameObject("framing test camera");
        try
        {
            target.transform.position = new Vector3(.4f, .7f, -.2f);
            target.transform.localScale = new Vector3(.12f, .04f, .2f);
            target.transform.rotation = Quaternion.Euler(13f, 37f, 9f);
            var position = target.transform.position;
            var rotation = target.transform.rotation;
            var scale = target.transform.localScale;
            var camera = cameraObject.AddComponent<Camera>();
            camera.aspect = aspect;
            camera.orthographic = orthographic;
            camera.nearClipPlane = .001f;
            cameraObject.transform.rotation = Quaternion.Euler(25f, 35f, 0f);
            var view = cameraObject.AddComponent<M7FReplayCamera>();
            Assert.That(view.FrameRenderedTarget(target.transform), Is.True);
            var bounds = target.GetComponent<Renderer>().bounds;
            for (var x = -1; x <= 1; x += 2)
            for (var y = -1; y <= 1; y += 2)
            for (var z = -1; z <= 1; z += 2)
            {
                var corner = bounds.center + Vector3.Scale(bounds.extents, new Vector3(x, y, z));
                var point = camera.WorldToViewportPoint(corner);
                Assert.That(point.x, Is.InRange(0f, 1f));
                Assert.That(point.y, Is.InRange(0f, 1f));
                Assert.That(point.z, Is.InRange(camera.nearClipPlane, camera.farClipPlane));
            }
            Assert.That(target.transform.position, Is.EqualTo(position));
            Assert.That(target.transform.rotation, Is.EqualTo(rotation));
            Assert.That(target.transform.localScale, Is.EqualTo(scale));
            Assert.That(view.CurrentMode, Is.EqualTo(M7FCameraMode.WorldFixed));
            var fixedPosition = cameraObject.transform.position;
            var fixedRotation = cameraObject.transform.rotation;
            target.transform.position += Vector3.right;
            TickCamera(view);
            Assert.That(cameraObject.transform.position, Is.EqualTo(fixedPosition));
            Assert.That(cameraObject.transform.rotation, Is.EqualTo(fixedRotation));
        }
        finally
        {
            Object.DestroyImmediate(cameraObject);
            Object.DestroyImmediate(target);
        }
    }

    [Test]
    public void FrameRenderedTargetWithoutGeometryLeavesCameraUnchanged()
    {
        var target = new GameObject("empty framing target");
        var cameraObject = new GameObject("framing camera");
        try
        {
            cameraObject.AddComponent<Camera>();
            var view = cameraObject.AddComponent<M7FReplayCamera>();
            var before = cameraObject.transform.position;
            Assert.That(view.FrameRenderedTarget(target.transform), Is.False);
            Assert.That(cameraObject.transform.position, Is.EqualTo(before));
            Assert.That(view.FrameRenderedTarget(null), Is.False);
        }
        finally
        {
            Object.DestroyImmediate(cameraObject);
            Object.DestroyImmediate(target);
        }
    }

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
            TickCamera(replayCamera);
            Assert.That(cameraObject.transform.position, Is.Not.EqualTo(orbitStart));

            replayCamera.SetMode(M7FCameraMode.WorldFixed);
            var lockedPosition = cameraObject.transform.position;
            var lockedRotation = cameraObject.transform.rotation;

            targetObject.transform.position += new Vector3(2f, 0f, 1f);
            TickCamera(replayCamera);

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
