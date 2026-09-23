using System;
using System.IO;
using System.Reflection;
using FlyBrain.M7FReplay;
using NUnit.Framework;
using UnityEngine;

namespace FlyBrain.Tests
{
    public sealed class M9DReplayTests
    {
        [Test] public void LoaderParsesExactPhysicalSchemaAndRejectsTrailingBytes()
        {
            var bytes=ReplayBytes(); var replay=M9DReplayLoader.Read(bytes);
            Assert.That(replay.StateCount,Is.EqualTo(15001)); Assert.That(replay.Time[^1],Is.EqualTo(1500).Within(1e-9));
            Assert.That(replay.BodyPosition.Length,Is.EqualTo(15001*3)); Assert.That(replay.BodyOrientation.Length,Is.EqualTo(15001*4)); Assert.That(replay.JointPosition.Length,Is.EqualTo(15001*42));
            Array.Resize(ref bytes,bytes.Length+1); Assert.Throws<InvalidDataException>(()=>M9DReplayLoader.Read(bytes));
        }

        [Test] public void ComparisonOffsetsArePresentationOnlyAndDefaultPairIsAPVersusBP()
        {
            var owner=new GameObject("M9D test"); var controller=owner.AddComponent<M9DReplayController>(); var left=Rig(owner.transform,"left"); var right=Rig(owner.transform,"right"); var loader=owner.AddComponent<M9DReplayLoader>(); controller.Configure(loader,left,right);
            controller.SetComparison(M9DCondition.A_P,M9DCondition.B_P,true);
            Assert.That(controller.LeftCondition,Is.EqualTo(M9DCondition.A_P)); Assert.That(controller.RightCondition,Is.EqualTo(M9DCondition.B_P)); Assert.That(controller.SideBySide,Is.True);
            Assert.That(left.PresentationOffset,Is.EqualTo(Vector3.left*.04f)); Assert.That(right.PresentationOffset,Is.EqualTo(Vector3.right*.04f));
            Assert.That(controller.PresentationInterpolation,Is.False); UnityEngine.Object.DestroyImmediate(owner);
        }

        [Test] public void ForceArrowIsPurePresentationAndCannotApplyForce()
        {
            var owner=new GameObject("arrow"); var arrow=owner.AddComponent<M9DForceArrow>();
            Assert.That(owner.GetComponent<Rigidbody>(),Is.Null); Assert.That(owner.GetComponent<Collider>(),Is.Null);
            Assert.That(arrow.UnityDirection,Is.EqualTo(Vector3.forward)); Assert.That(M9DForceArrow.Annotation,Does.Contain("visualization only"));
            foreach(var method in typeof(M9DForceArrow).GetMethods(BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic)) Assert.That(method.Name,Does.Not.Contain("Force"));
            UnityEngine.Object.DestroyImmediate(owner);
        }

        [Test] public void ScientificLabelsUseRequiredMotorGateLanguage()
        {
            Assert.That(M9DReplayController.Label(M9DCondition.A_P),Does.Contain("Mapped MaleCNS motor output ENABLED"));
            Assert.That(M9DReplayController.Label(M9DCondition.B_P),Does.Contain("DISABLED before physical application"));
        }

        static M7FFlyRig Rig(Transform parent,string name) { var value=new GameObject(name); value.transform.SetParent(parent); return value.AddComponent<M7FFlyRig>(); }
        static byte[] ReplayBytes()
        {
            using var stream=new MemoryStream(); using(var writer=new BinaryWriter(stream,System.Text.Encoding.UTF8,true)) { writer.Write(System.Text.Encoding.ASCII.GetBytes(M9DReplayData.Magic)); writer.Write((uint)1); writer.Write((uint)15001); writer.Write((uint)42); for(var i=0;i<15001;i++)writer.Write(i*.1); for(var i=0;i<15001*3;i++)writer.Write(0d); for(var i=0;i<15001;i++){writer.Write(1d);writer.Write(0d);writer.Write(0d);writer.Write(0d);} for(var i=0;i<15001*42;i++)writer.Write(0d); } return stream.ToArray();
        }
    }
}
