using UnityEngine;

namespace FlyBrain.M7FReplay
{
    public sealed class M9DScientificUI : MonoBehaviour
    {
        [SerializeField] M9DReplayController controller; [SerializeField] M7FReplayCamera replayCamera;
        static readonly (double time, string label)[] Markers = { (500,"force begins"), (520,"force ends"), (500.1,"physical trajectory divergence (M9C)"), (500.5,"modeled proprioceptive encoding divergence (M9C)"), (508.5,"delivered sensory/CNS interaction divergence (M9C)"), (556,"decoder-output interaction divergence (M9C)"), (557,"admitted physical motor-contribution interaction divergence (M9C)"), (557.1,"subsequent physical divergence (M9C)") };
        public void Configure(M9DReplayController value, M7FReplayCamera camera=null) { controller=value; replayCamera=camera; }
        void OnGUI()
        {
            if (controller == null) return; GUILayout.BeginArea(new Rect(12,12,620,Screen.height-24),GUI.skin.box);
            GUILayout.Label("M9D — CANONICAL M9B EXTERNAL PERTURBATION REPLAY");
            GUILayout.Label("Recorded canonical M9B replay. Unity does not simulate neural or physical dynamics.");
            GUILayout.Label(M9DReplayController.Label(controller.LeftCondition)); if (controller.SideBySide) GUILayout.Label(M9DReplayController.Label(controller.RightCondition));
            GUILayout.Label($"Canonical time: {controller.TimeMs:F1} ms    physical frame: {controller.Frame}");
            GUILayout.BeginHorizontal(); if(GUILayout.Button(controller.IsPlaying?"Pause":"Play"))controller.TogglePlayback(); if(GUILayout.Button("Restart"))controller.Restart(); if(GUILayout.Button("< Frame"))controller.Step(-1); if(GUILayout.Button("Frame >"))controller.Step(1); GUILayout.EndHorizontal();
            var normalizedFrame=controller.Frame/(float)M9DReplayController.FinalFrame; var scrub=GUILayout.HorizontalSlider(normalizedFrame,0,1); if(!Mathf.Approximately(scrub,normalizedFrame))controller.Scrub(scrub);
            GUILayout.Label("Speed (presentation):"); GUILayout.BeginHorizontal(); foreach(var value in M9DReplayController.AllowedSpeeds)if(GUILayout.Button($"{value:g}x"))controller.SetSpeed(value); GUILayout.EndHorizontal();
            var interpolation=GUILayout.Toggle(controller.PresentationInterpolation,"Presentation-only interpolation (OFF by default)"); if(interpolation!=controller.PresentationInterpolation)controller.SetInterpolation(interpolation);
            GUILayout.BeginHorizontal(); GUILayout.Label("Camera: synchronized orbit/zoom"); if(GUILayout.Button("Reset view"))replayCamera?.ResetView(); if(GUILayout.Button("Thorax/legs close-up"))replayCamera?.Configure(controller.transform.root,.18f); GUILayout.EndHorizontal();
            GUILayout.BeginHorizontal(); foreach(M9DCondition value in System.Enum.GetValues(typeof(M9DCondition)))if(GUILayout.Button(value.ToString()))controller.SetComparison(value,controller.RightCondition,false); GUILayout.EndHorizontal();
            GUILayout.BeginHorizontal(); if(GUILayout.Button("A_P vs B_P (default)"))controller.SetComparison(M9DCondition.A_P,M9DCondition.B_P,true); if(GUILayout.Button("A_P vs A_C"))controller.SetComparison(M9DCondition.A_P,M9DCondition.A_C,true); if(GUILayout.Button("B_P vs B_C"))controller.SetComparison(M9DCondition.B_P,M9DCondition.B_C,true); GUILayout.EndHorizontal();
            GUILayout.Label("Any pair (left vs right):");
            foreach(M9DCondition left in System.Enum.GetValues(typeof(M9DCondition))) { GUILayout.BeginHorizontal(); foreach(M9DCondition right in System.Enum.GetValues(typeof(M9DCondition))) if(GUILayout.Button($"{left} / {right}"))controller.SetComparison(left,right,true); GUILayout.EndHorizontal(); }
            GUILayout.Label("Timeline 0–1500 ms (M9C annotations are informational only)"); foreach(var marker in Markers)GUILayout.Label($"{marker.time:F1} ms — {marker.label}");
            if(controller.ForceActive)GUILayout.Label(M9DForceArrow.Annotation+" (arrow length is illustrative only)");
            GUILayout.Label("Physics transitions = 0 | Neural transitions = 0 | Unity physics authoritative = false"); GUILayout.EndArea();
        }
    }
}
