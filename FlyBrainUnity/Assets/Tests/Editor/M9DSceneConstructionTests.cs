using System.IO;
using System.Linq;
using FlyBrain.M7FReplay;
using NUnit.Framework;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace FlyBrain.Tests
{
    public sealed class M9DSceneConstructionTests
    {
        const string TemporaryScene = "Assets/Tests/Editor/M9DGeneratedConstructionTest.unity";

        [TearDown] public void TearDown()
        {
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            AssetDatabase.DeleteAsset(TemporaryScene);
        }

        [Test] public void MenuGenerationPathPersistsCompleteReferenceSafePresentation()
        {
            Assert.That(EditorApplication.ExecuteMenuItem("Fly Brain/M9D/Create External Perturbation Replay Scene"), Is.True);
            Assert.That(EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene(), TemporaryScene), Is.True);
            EditorSceneManager.OpenScene(TemporaryScene, OpenSceneMode.Single);
            var controller = Object.FindObjectOfType<M9DReplayController>();
            var ui = Object.FindObjectOfType<M9DScientificUI>();
            var top = controller.transform.root.gameObject;
            Assert.That(top.GetComponentsInChildren<Transform>(true).Sum(value => GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(value.gameObject)), Is.Zero);
            Assert.That(controller.Loader, Is.Not.Null);
            Assert.That(controller.LeftRig.Joints, Has.Count.EqualTo(42));
            Assert.That(controller.RightRig.Joints, Has.Count.EqualTo(42));
            Assert.That(ui.Controller, Is.SameAs(controller));
            Assert.That(ui.ReplayCamera, Is.Not.Null);
            Assert.That(controller.LeftCondition, Is.EqualTo(M9DCondition.A_P));
            Assert.That(controller.RightCondition, Is.EqualTo(M9DCondition.B_P));
            Assert.That(controller.SideBySide, Is.True);
            Assert.That(controller.PresentationInterpolation, Is.False);
            Assert.That(controller.PresentationSpeed, Is.EqualTo(1));
            Assert.That(top.GetComponentsInChildren<M7FAnatomyObject>(true), Has.Length.EqualTo(138));
            Assert.That(top.GetComponentsInChildren<Rigidbody>(true), Is.Empty);
            Assert.That(top.GetComponentsInChildren<Collider>(true), Is.Empty);
        }

        [Test] public void RuntimeInitializationPlaybackAndNavigationApplyRecordedFrames()
        {
            var replayRoot = Path.Combine(Application.streamingAssetsPath, "M9DReplay");
            if (!File.Exists(Path.Combine(replayRoot, "m9d_replay_manifest.json")) || Directory.GetFiles(replayRoot, "*.bin").Length != 4)
                Assert.Ignore("Frozen canonical M9D replay artifacts are not installed in this checkout.");
            Assert.That(EditorApplication.ExecuteMenuItem("Fly Brain/M9D/Create External Perturbation Replay Scene"), Is.True);
            var controller = Object.FindObjectOfType<M9DReplayController>();
            Assert.That(controller.Initialize(), Is.True, controller.InitializationError);
            Assert.That(controller.Frame, Is.Zero);
            var poseAtFrameZero = controller.LeftRig.ScientificRoot.GetComponentsInChildren<Transform>(true)
                .ToDictionary(value => value, value => (value.position, value.rotation));
            controller.Play(); controller.AdvancePresentation(.001);
            Assert.That(controller.Frame, Is.EqualTo(10));
            Assert.That(controller.TimeMs, Is.EqualTo(1).Within(1e-9));
            Assert.That(poseAtFrameZero.Any(item => item.Key.position != item.Value.position || item.Key.rotation != item.Value.rotation), Is.True,
                "recorded replay advancement must change at least one scientific pose transform");
            controller.Pause(); var paused = controller.Frame; controller.AdvancePresentation(1); Assert.That(controller.Frame, Is.EqualTo(paused));
            controller.Step(1); Assert.That(controller.Frame, Is.EqualTo(paused + 1));
            controller.Scrub(.5f); Assert.That(controller.Frame, Is.EqualTo(7500));
            controller.Restart(); Assert.That(controller.Frame, Is.Zero);
        }

        [Test] public void UnassignedControllerNamesDependencyAndUiDoesNotThrow()
        {
            var owner = new GameObject("unconfigured M9D");
            var controller = owner.AddComponent<M9DReplayController>();
            LogAssert.Expect(LogType.Error, "M9D replay initialization failed: serialized dependency 'loader' is not assigned.");
            Assert.That(controller.Initialize(), Is.False);
            Assert.That(controller.InitializationError, Does.Contain("loader"));
            Assert.DoesNotThrow(() => controller.SetComparison(M9DCondition.A_P, M9DCondition.B_P, true));
            Assert.DoesNotThrow(() => owner.AddComponent<M9DScientificUI>().Configure(controller));
            Object.DestroyImmediate(owner);
        }
    }
}
