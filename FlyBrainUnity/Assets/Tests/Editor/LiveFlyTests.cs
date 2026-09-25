using System;
using System.Linq;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools.Utils;
using FlyBrain.LiveFly;
using FlyBrain.M7FReplay;

public sealed class LiveFlyTests
{
    static double RotationAngleDegrees(Quaternion before,Quaternion after)
    {
        var relative=Quaternion.Inverse(before)*after;
        var vectorMagnitude=Math.Sqrt((double)relative.x*relative.x+(double)relative.y*relative.y+(double)relative.z*relative.z);
        return 2d*Math.Atan2(vectorMagnitude,Math.Abs((double)relative.w))*Mathf.Rad2Deg;
    }

    static string Array(string values)=>"["+values+"]";
    static string Names()=>Array(string.Join(",",M7FScientificFlyRigDefinition.CanonicalNames.Select(x=>"\""+x+"\"")));
    static string Hello(string session="s",int version=1,int count=42,string names=null)=>"{\"type\":\"hello\",\"protocol\":\"live_fly_pose\",\"version\":"+version+",\"session_id\":\""+session+"\",\"joint_count\":"+count+",\"joint_names\":"+(names??Names())+",\"root_quaternion_order\":\"wxyz\"}";
    static string Pose(string session="s",string quaternion="1,0,0,0",int joints=42)=>"{\"type\":\"pose\",\"protocol\":\"live_fly_pose\",\"version\":1,\"session_id\":\""+session+"\",\"sequence\":7,\"sim_time_seconds\":0.25,\"root_position\":[1,2,3],\"root_quaternion_wxyz\":["+quaternion+"],\"joint_positions\":"+Array(string.Join(",",Enumerable.Range(0,joints)))+"}";

    [Test] public void HelloRequiresVersionCountAndExactM7FOrder()
    {
        var h=LiveFlyProtocol.ParseHello(Hello(),M7FScientificFlyRigDefinition.Names);Assert.That(h.SessionId,Is.EqualTo("s"));
        Assert.Throws<LiveFlyProtocolException>(()=>LiveFlyProtocol.ParseHello(Hello(version:2),M7FScientificFlyRigDefinition.Names));
        Assert.Throws<LiveFlyProtocolException>(()=>LiveFlyProtocol.ParseHello(Hello(count:41),M7FScientificFlyRigDefinition.Names));
        var reversed=Array(string.Join(",",M7FScientificFlyRigDefinition.CanonicalNames.Reverse().Select(x=>"\""+x+"\"")));
        Assert.Throws<LiveFlyProtocolException>(()=>LiveFlyProtocol.ParseHello(Hello(names:reversed),M7FScientificFlyRigDefinition.Names));
    }

    [Test] public void PoseRequiresHelloSessionAndAllShapes()
    {
        var p=LiveFlyProtocol.ParsePose(Pose(quaternion:"0.5,0.1,0.2,0.3"),"s");
        CollectionAssert.AreEqual(new[]{.5,.1,.2,.3},p.RootQuaternionWxyz,"wire order remains w,x,y,z");
        Assert.Throws<LiveFlyProtocolException>(()=>LiveFlyProtocol.ParsePose(Pose(),"other"));
        Assert.Throws<LiveFlyProtocolException>(()=>LiveFlyProtocol.ParsePose(Pose(joints:41),"s"));
        Assert.Throws<LiveFlyProtocolException>(()=>LiveFlyProtocol.ParsePose("{bad", "s"));
    }

    [Test] public void ActualPythonWireMessagesAcceptMixedJsonNumberRepresentations()
    {
        // Mirrors json.dumps(..., separators=(",", ":")) output from
        // malecns_backend.live.protocol, including hello-only diagnostic fields
        // and the integer/decimal/exponent mixture emitted by real snapshots.
        const string session="51ed8943-7ba3-4327-9059-b4aece175607";
        var hello="{\"type\":\"hello\",\"protocol\":\"live_fly_pose\",\"version\":1,\"session_id\":\""+session+"\",\"joint_count\":42,\"joint_names\":"+Names()+",\"physics_dt_seconds\":0.0001,\"neural_dt_seconds\":0.0005,\"root_quaternion_order\":\"wxyz\",\"source_length_unit\":\"millimetres\",\"coordinate_convention\":\"FlyGym right-handed Z-up; unconverted MuJoCo coordinates\",\"rig/model identity\":\"FlyGym NeuroMechFly, validated MaleCNS 42-leg-joint action order\"}";
        var joints=string.Join(",",Enumerable.Range(0,42).Select(i=>i%3==0?"0":i%3==1?"-1.25e-3":"0.5"));
        var pose="{\"type\":\"pose\",\"protocol\":\"live_fly_pose\",\"version\":1,\"session_id\":\""+session+"\",\"sequence\":127,\"sim_time_seconds\":2,\"root_position\":[0,-1.25e-3,2.5],\"root_quaternion_wxyz\":[1,0.0,0,0],\"joint_positions\":["+joints+"],\"physics_transitions\":20000,\"neural_transitions\":4000,\"finite\":true}";

        var parsedHello=LiveFlyProtocol.ParseHello(hello,M7FScientificFlyRigDefinition.Names);
        var parsedPose=LiveFlyProtocol.ParsePose(pose,parsedHello.SessionId);
        Assert.That(parsedPose.Sequence,Is.EqualTo(127));
        Assert.That(parsedPose.SimTimeSeconds,Is.EqualTo(2d));
        Assert.That(parsedPose.RootPosition[1],Is.EqualTo(-.00125d));
        Assert.That(parsedPose.JointPositions.Length,Is.EqualTo(42));
    }

    [Test] public void PositionUsesValidatedM7FScaleAndReflectedBasis()
    {
        Assert.That(LiveFlyCoordinates.PositionMmToUnity(new[]{1d,2d,3d}),Is.EqualTo(new Vector3(.1f,.3f,.2f)).Using(Vector3ComparerWithEqualsOperator.Instance));
    }

    [Test] public void QuaternionConversionIsBasisConjugation()
    {
        var identity=LiveFlyCoordinates.QuaternionWxyzToUnity(new[]{1d,0d,0d,0d});
        Assert.That(Quaternion.Angle(identity,Quaternion.identity),Is.LessThan(1e-4));
        var source=Quaternion.AngleAxis(90,Vector3.right);
        var converted=LiveFlyCoordinates.QuaternionWxyzToUnity(new[]{(double)source.w,source.x,source.y,source.z});
        var expected=Quaternion.AngleAxis(-90,Vector3.right); // axial x -> -x under det(B) B
        Assert.That(Quaternion.Angle(converted,expected),Is.LessThan(1e-3));
    }

    [Test] public void NewestPoseSlotHasCapacityOneAndCountsReplacement()
    {
        var slot=new NewestPoseSlot();var a=LiveFlyProtocol.ParsePose(Pose(),"s");var b=LiveFlyProtocol.ParsePose(Pose().Replace("\"sequence\":7","\"sequence\":8"),"s");
        slot.Publish(a);slot.Publish(b);Assert.That(slot.ReplacedCount,Is.EqualTo(1));Assert.That(slot.TryTake(out var newest),Is.True);Assert.That(newest.Sequence,Is.EqualTo(8));Assert.That(slot.TryTake(out _),Is.False);
    }

    [Test] public void RigReceivesEveryAuthoritativeJointInDirectMode()
    {
        var go=new GameObject("live-test");
        try
        {
            go.AddComponent<M7FScientificFlyBuilder>().Rebuild();var rig=go.GetComponent<M7FFlyRig>();Assert.That(rig.ValidateMapping(M7FScientificFlyRigDefinition.Names),Is.True);
            var before=rig.Joints.Select(x=>x.transform.localRotation).ToArray();var values=Enumerable.Range(1,42).Select(i=>i*.001).ToArray();
            var position=LiveFlyCoordinates.PositionMmToUnity(new[]{1d,2d,3d});var rotation=LiveFlyCoordinates.QuaternionWxyzToUnity(new[]{1d,0d,0d,0d});rig.ApplyLivePose(position,rotation,values);
            Assert.That(rig.ScientificRoot.position,Is.EqualTo(position).Using(Vector3ComparerWithEqualsOperator.Instance));Assert.That(Quaternion.Angle(rig.ScientificRoot.rotation,rotation),Is.LessThan(1e-4));
            // Quaternion.Angle intentionally snaps sufficiently small rotations to
            // zero.  atan2 over the relative quaternion preserves this 0.001 rad
            // case without changing the expected value or tolerance.
            for(var i=0;i<42;i++)Assert.That(RotationAngleDegrees(before[i],rig.Joints[i].transform.localRotation),Is.EqualTo(values[i]*Mathf.Rad2Deg).Within(.002),"joint "+i);
        }
        finally{UnityEngine.Object.DestroyImmediate(go);}
    }
}
