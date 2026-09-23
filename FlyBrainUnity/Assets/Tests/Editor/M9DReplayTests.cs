using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Reflection.Emit;
using FlyBrain.M7FReplay;
using NUnit.Framework;
using UnityEngine;

namespace FlyBrain.Tests
{
    public sealed class M9DReplayTests
    {
        [Test] public void PresentationPlaybackStateAndClockAreDeterministic()
        {
            var owner=new GameObject("M9D playback test"); var controller=owner.AddComponent<M9DReplayController>();
            controller.Configure(owner.AddComponent<M9DReplayLoader>(),Rig(owner.transform,"left"),Rig(owner.transform,"right"));
            Assert.That(controller.Frame,Is.Zero); Assert.That(controller.IsPlaying,Is.False);
            controller.Play(); Assert.That(controller.IsPlaying,Is.True);
            controller.AdvancePresentation(.001); Assert.That(controller.Frame,Is.EqualTo(10),"Unity seconds must be converted to canonical milliseconds");
            controller.Pause(); controller.AdvancePresentation(1); Assert.That(controller.Frame,Is.EqualTo(10));
            controller.SetSpeed(.5f); controller.Play(); controller.AdvancePresentation(.001); Assert.That(controller.Frame,Is.EqualTo(15),"speed scales only the presentation clock");
            controller.Step(1); Assert.That(controller.Frame,Is.EqualTo(16)); Assert.That(controller.IsPlaying,Is.False);
            controller.SeekFrame(M9DReplayController.FinalFrame-1); controller.Play(); controller.AdvancePresentation(1);
            Assert.That(controller.Frame,Is.EqualTo(M9DReplayController.FinalFrame)); Assert.That(controller.IsPlaying,Is.False);
            controller.Play(); controller.AdvancePresentation(1); Assert.That(controller.Frame,Is.EqualTo(M9DReplayController.FinalFrame)); Assert.That(controller.IsPlaying,Is.False);
            Assert.That(owner.GetComponentsInChildren<Rigidbody>(true),Is.Empty); Assert.That(owner.GetComponentsInChildren<Collider>(true),Is.Empty);
            UnityEngine.Object.DestroyImmediate(owner);
        }

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
            Assert.That(owner.GetComponents<Component>().Select(value=>value.GetType()),Is.EquivalentTo(new[]{typeof(Transform),typeof(M9DForceArrow)}));
            Assert.That(typeof(M9DForceArrow).GetFields(BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.DeclaredOnly)
                .Select(field=>$"{field.Name}:{field.FieldType.FullName}"),Is.EquivalentTo(new[]{
                    $"controller:{typeof(M9DReplayController).FullName}",$"authoritativeThorax:{typeof(Transform).FullName}",$"illustrativeLength:{typeof(float).FullName}"}));
            Assert.That(CalledMethods(UnityDirectionGetter),Is.EqualTo(new MethodBase[]{Vector3ForwardGetter}),"UnityDirection must remain the fixed presentation-space +Z direction");
            Assert.That(ReferencedFields(UnityDirectionGetter),Is.Empty,"UnityDirection must not read or mutate component, physics, or scientific state");
            foreach(var method in typeof(M9DForceArrow).GetMethods(BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.DeclaredOnly))
                foreach(var called in CalledMethods(method)) Assert.That(IsPresentationOnlyCall(called),Is.True,$"{method.Name} calls prohibited API {called.DeclaringType?.FullName}.{called.Name}");
            UnityEngine.Object.DestroyImmediate(owner);
        }

        static bool IsPresentationOnlyCall(MethodBase method)
        {
            var owner=method.DeclaringType;
            if(owner==typeof(M9DForceArrow))return method==UnityDirectionGetter;
            if(owner==typeof(M9DReplayController))return method.Name=="get_ForceActive";
            if(owner==typeof(UnityEngine.Object))return method.Name is "op_Implicit" or "op_Inequality";
            if(owner==typeof(Component))return method.Name=="get_transform" || method.Name=="GetComponentsInChildren" && method is MethodInfo info && info.IsGenericMethod && info.GetGenericArguments().SequenceEqual(new[]{typeof(Renderer)});
            if(owner==typeof(Renderer))return method.Name=="set_enabled";
            if(owner==typeof(Transform))return method.Name is "get_position" or "set_position" or "set_rotation";
            if(owner==typeof(Vector3))return method.Name=="get_forward";
            return owner==typeof(Quaternion) && method.Name=="LookRotation";
        }

        static MethodBase[] CalledMethods(MethodInfo method)
        {
            var body=method.GetMethodBody(); if(body==null)return Array.Empty<MethodBase>();
            var il=body.GetILAsByteArray(); var calls=new System.Collections.Generic.List<MethodBase>();
            for(var offset=0;offset<il.Length;)
            {
                OpCode opcode; var first=il[offset++];
                if(first==0xfe)opcode=MultiByteOpCodes[il[offset++]]; else opcode=SingleByteOpCodes[first];
                if(opcode.OperandType is OperandType.InlineMethod)
                {
                    var token=BitConverter.ToInt32(il,offset); calls.Add(method.Module.ResolveMethod(token,method.DeclaringType?.GetGenericArguments(),method.GetGenericArguments()));
                }
                offset+=OperandSize(opcode.OperandType,il,offset);
            }
            return calls.ToArray();
        }

        static FieldInfo[] ReferencedFields(MethodInfo method)
        {
            var body=method.GetMethodBody(); if(body==null)return Array.Empty<FieldInfo>();
            var il=body.GetILAsByteArray(); var fields=new System.Collections.Generic.List<FieldInfo>();
            for(var offset=0;offset<il.Length;)
            {
                OpCode opcode; var first=il[offset++];
                if(first==0xfe)opcode=MultiByteOpCodes[il[offset++]]; else opcode=SingleByteOpCodes[first];
                if(opcode.OperandType is OperandType.InlineField)
                {
                    var token=BitConverter.ToInt32(il,offset); fields.Add(method.Module.ResolveField(token,method.DeclaringType?.GetGenericArguments(),method.GetGenericArguments()));
                }
                offset+=OperandSize(opcode.OperandType,il,offset);
            }
            return fields.ToArray();
        }

        static int OperandSize(OperandType type,byte[] il,int offset) => type switch
        {
            OperandType.InlineNone=>0, OperandType.ShortInlineBrTarget or OperandType.ShortInlineI or OperandType.ShortInlineVar=>1,
            OperandType.InlineVar=>2, OperandType.InlineI8 or OperandType.InlineR=>8,
            OperandType.InlineSwitch=>4+BitConverter.ToInt32(il,offset)*4, _=>4
        };

        static readonly MethodInfo UnityDirectionGetter=typeof(M9DForceArrow).GetProperty(nameof(M9DForceArrow.UnityDirection),BindingFlags.Instance|BindingFlags.Public|BindingFlags.DeclaredOnly).GetGetMethod();
        static readonly MethodInfo Vector3ForwardGetter=typeof(Vector3).GetProperty(nameof(Vector3.forward),BindingFlags.Static|BindingFlags.Public).GetGetMethod();
        static readonly OpCode[] SingleByteOpCodes=BuildOpCodes(false), MultiByteOpCodes=BuildOpCodes(true);
        static OpCode[] BuildOpCodes(bool multiByte)
        {
            var values=new OpCode[256];
            foreach(var field in typeof(OpCodes).GetFields(BindingFlags.Public|BindingFlags.Static))
            {
                var opcode=(OpCode)field.GetValue(null); var value=(ushort)opcode.Value;
                if((value>0xff)==multiByte)values[value&0xff]=opcode;
            }
            return values;
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
