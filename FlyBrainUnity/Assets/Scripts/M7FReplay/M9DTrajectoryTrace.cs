using UnityEngine;

namespace FlyBrain.M7FReplay
{
    /// <summary>Presentation-only polyline made directly from recorded canonical root samples.</summary>
    [RequireComponent(typeof(LineRenderer))]
    public sealed class M9DTrajectoryTrace : MonoBehaviour
    {
        public const int FirstFrame = 5000;
        [SerializeField] M9DReplayController controller;
        [SerializeField] LineRenderer line;
        public bool Visible => line != null && line.enabled;
        public const string Annotation = "RECORDED ROOT/COM TRAJECTORY TRACE (presentation only)";

        public void Configure(M9DReplayController value, Color color)
        {
            controller=value; line=GetComponent<LineRenderer>(); line.useWorldSpace=true; line.widthMultiplier=.006f;
            line.startColor=color; line.endColor=color; line.enabled=true;
        }
        public void SetVisible(bool value) { if(line!=null) line.enabled=value; }
        public void Refresh(M9DCondition condition, Vector3 presentationOffset)
        {
            if(controller==null || controller.Loader==null || !controller.Loader.Replays.TryGetValue(condition,out var replay))return;
            var points=RecordedPoints(replay,presentationOffset);
            var count=points.Length;
            line.positionCount=count; line.SetPositions(points);
        }
        public static Vector3[] RecordedPoints(M9DReplayData replay,Vector3 presentationOffset)
        {
            var count=replay.StateCount-FirstFrame; var points=new Vector3[count];
            for(var i=0;i<count;i++) points[i]=replay.UnityPosition(FirstFrame+i)+presentationOffset;
            return points;
        }
    }
}
