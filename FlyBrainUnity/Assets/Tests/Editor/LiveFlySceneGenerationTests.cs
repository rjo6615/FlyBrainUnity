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
        Assert.That(rigs, Has.Length.EqualTo(1));
        Assert.That(clients, Has.Length.EqualTo(1));
        Assert.That(clients[0].Rig, Is.SameAs(rigs[0]));
        Assert.Multiple(() =>
        {
            Assert.That(clients[0].Host, Is.EqualTo("127.0.0.1"));
            Assert.That(clients[0].Port, Is.EqualTo(8765));
            Assert.That(clients[0].ConnectOnStart, Is.True);
            Assert.That(clients[0].PresentationInterpolation, Is.False);
            Assert.That(rigs[0].Joints, Has.Count.EqualTo(42));
            Assert.That(rigs[0].ValidateMapping(M7FScientificFlyRigDefinition.Names), Is.True);
            Assert.That(rigs[0].GetComponentsInChildren<Rigidbody>(true), Is.Empty);
            Assert.That(rigs[0].GetComponentsInChildren<ArticulationBody>(true), Is.Empty);
            Assert.That(rigs[0].GetComponentsInChildren<CharacterController>(true), Is.Empty);
            Assert.That(rigs[0].GetComponentsInChildren<Animator>(true), Is.Empty);
            byte[] after;
            using (var sha = SHA256.Create()) after = sha.ComputeHash(File.ReadAllBytes(artifact));
            CollectionAssert.AreEqual(before, after, "scene creation modified the canonical rig artifact");
        });

        var allowed = new[] { typeof(Transform), typeof(M7FScientificFlyBuilder), typeof(M7FFlyRig), typeof(M7FScientificSkeletonVisibility), typeof(M7FAnatomyPresentation) };
        Assert.That(rigs[0].GetComponents<Component>().Select(x => x.GetType()), Is.SubsetOf(allowed), "an unapproved movement/controller component was introduced on the fly");
        Assert.That(rigs[0].ScientificRoot.localPosition, Is.EqualTo(Vector3.zero), "scene creation executed a scientific transition");
        Assert.That(EditorSceneManager.GetActiveScene().path, Is.EqualTo(LiveFlySceneGenerator.ScenePath));
    }
}
