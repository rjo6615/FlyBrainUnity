using System.IO;
using System.Security.Cryptography;
using FlyBrain.M7FReplay;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;

namespace FlyBrain.Tests
{
    public sealed class M8ReplayPresentationTests
    {
        M7FReplayLoader loader;
        GameObject owner;

        [SetUp] public void LoadValidatedM8()
        {
            owner = new GameObject("M8 presentation test");
            loader = owner.AddComponent<M7FReplayLoader>();
            loader.ConfigureM8(); loader.Load();
        }

        [TearDown] public void Cleanup() { Object.DestroyImmediate(owner); }

        [Test] public void ManifestAndBothRecordedBinariesValidateBeforeUse()
        {
            Assert.That(loader.M8Manifest.schema, Is.EqualTo("M8-UNITY-REPLAY-EXPORT.1"));
            Assert.That(loader.M8Manifest.cadence_ms.physics, Is.EqualTo(.1));
            Assert.That(loader.M8Manifest.cadence_ms.neural, Is.EqualTo(.5));
            Assert.That(Hash("m8_enabled_replay.bin"), Is.EqualTo("56a19ef572338e454febe4249578a54787e697bba87a2a4a4f7a11976e69b558"));
            Assert.That(Hash("m8_disabled_replay.bin"), Is.EqualTo("29569c8b8612acda0cd5b12471a00ba80599b7e6c7b5e77ea4e200ea47dfd843"));
        }

        [Test] public void ConditionsAreDistinctAndContainTheDeclaredCompleteTimeline()
        {
            Assert.That(loader.Enabled, Is.Not.SameAs(loader.Disabled));
            Assert.That(loader.Enabled.PhysicsCount, Is.EqualTo(100001));
            Assert.That(loader.Disabled.PhysicsCount, Is.EqualTo(100001));
            Assert.That(loader.Enabled.NeuralCount, Is.EqualTo(20000));
            Assert.That(loader.Disabled.NeuralCount, Is.EqualTo(20000));
            Assert.That(loader.Enabled.PhysicsTime[^1], Is.EqualTo(10000.0).Within(1e-6));
            Assert.That(loader.Disabled.PhysicsTime[^1], Is.EqualTo(10000.0).Within(1e-6));
        }

        [Test] public void FirstAndFinalRecordedFramesApplyToTheExistingScientificRig()
        {
            var fly = new GameObject("existing M7F scientific rig"); fly.transform.SetParent(owner.transform);
            fly.AddComponent<M7FScientificFlyBuilder>().Rebuild(); var rig = fly.GetComponent<M7FFlyRig>();
            Assert.That(rig.ValidateMapping(loader.Manifest.joint_names), Is.True);
            Assert.DoesNotThrow(() => rig.Apply(loader.Enabled, 0, 0, 0));
            Assert.DoesNotThrow(() => rig.Apply(loader.Enabled, 100000, 100000, 0));
            Assert.DoesNotThrow(() => rig.Apply(loader.Disabled, 0, 0, 0));
            Assert.DoesNotThrow(() => rig.Apply(loader.Disabled, 100000, 100000, 0));
        }

        [Test] public void DedicatedSceneKeepsEnabledDefaultAndUsesVis3Anatomy()
        {
            Assert.That(EditorApplication.ExecuteMenuItem("Fly Brain/M8/Create Extended Spontaneous Replay Scene"), Is.True);
            var top = GameObject.Find("M8 Extended Spontaneous Replay"); Assert.That(top, Is.Not.Null);
            var sceneLoader = top.transform.Find("ReplaySystem").GetComponent<M7FReplayLoader>();
            var controller = top.transform.Find("ReplaySystem").GetComponent<M7FReplayController>();
            Assert.That(sceneLoader.Dataset, Is.EqualTo(ReplayDataset.M8ExtendedSpontaneous));
            Assert.That(controller.Condition, Is.EqualTo(M7FCondition.Enabled));
            Assert.That(top.GetComponentsInChildren<M7FAnatomyObject>(true), Has.Length.EqualTo(138));
            Assert.That(top.GetComponent<M7FCanonicalReplayPresentation>().ShowLegacyBridgeDebugPresentation, Is.False);
            Object.DestroyImmediate(top);
        }

        static string Hash(string name)
        {
            using var input = File.OpenRead(Path.Combine(Application.streamingAssetsPath, "M8Replay", name));
            using var sha = SHA256.Create();
            return System.BitConverter.ToString(sha.ComputeHash(input)).Replace("-", "").ToLowerInvariant();
        }
    }
}

