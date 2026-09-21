using System.Text;
using UnityEngine;

namespace FlyBrain.M7FReplay
{
    /// <summary>Compact runtime controls, telemetry, timeline, and indelible provenance.</summary>
    public sealed class M7FScientificUI : MonoBehaviour
    {
        [SerializeField] M7FReplayController controller;
        Vector2 motorScroll;
        static readonly (double time, string label)[] Milestones = {
            (0, "initial state"), (54.0, "mapped motor activity / decoder-admitted divergence"),
            (54.1, "admitted-joint / whole-body divergence"), (54.5, "tibial sensory divergence"),
            (78.5, "delivered sensory-drive / downstream CNS divergence"), (121, "near RH tibia max A/B divergence"),
            (157.0, "observer / mapped motor-state divergence"), (250, "strong RM/RH divergence region"),
            (398, "later large joint-divergence region begins"), (425, "later large joint-divergence region ends")
        };

        public void Configure(M7FReplayController replayController) => controller = replayController;

        void OnGUI()
        {
            if (controller == null) return;
            GUILayout.BeginArea(new Rect(12, 12, 440, Screen.height - 24), GUI.skin.box);
            GUILayout.Label("M7F CANONICAL REPLAY");
            GUILayout.Label($"Playback: {(controller.IsPlaying ? "PLAYING" : "PAUSED")}    speed: {controller.PlaybackSpeed:g}x");
            GUILayout.Label($"Loaded: {(controller.IsLoaded ? "YES" : "NO")}    enabled: {(controller.EnabledReplayLoaded ? "YES" : "NO")}    disabled: {(controller.DisabledReplayLoaded ? "YES" : "NO")}");
            GUILayout.Label($"Last applied physical frame: {controller.LastAppliedFrame}");
            if (!controller.IsLoaded) { GUILayout.EndArea(); return; }
            GUILayout.Label(controller.ConditionLabel);
            var skeleton = controller.EnabledRig.GetComponent<M7FScientificSkeletonVisibility>();
            var showSkeleton = GUILayout.Toggle(skeleton != null && skeleton.Visible, "Scientific Skeleton");
            SetSkeleton(controller.EnabledRig, showSkeleton); SetSkeleton(controller.DisabledRig, showSkeleton);
            GUILayout.Label($"Canonical time: {controller.TimeMs:F1} ms    physical frame: {controller.Frame}");
            GUILayout.Label($"Neural sample: {controller.NeuralIndex}    time: {Current.NeuralTime[controller.NeuralIndex]:F1} ms");
            GUILayout.BeginHorizontal();
            if (GUILayout.Button(controller.IsPlaying ? "Pause" : "Play")) controller.TogglePlayback();
            if (GUILayout.Button("Restart")) controller.Restart(); if (GUILayout.Button("< Frame")) controller.Step(-1); if (GUILayout.Button("Frame >")) controller.Step(1);
            GUILayout.EndHorizontal();
var currentScrub = controller.Frame / (float)(Current.PhysicsCount - 1);
var scrub = GUILayout.HorizontalSlider(currentScrub, 0f, 1f);

if (!Mathf.Approximately(scrub, currentScrub))
    controller.ScrubNormalized(scrub);

GUILayout.BeginHorizontal();            if (GUILayout.Button("Enabled")) controller.SetCondition(M7FCondition.Enabled);
            if (GUILayout.Button("Disabled")) controller.SetCondition(M7FCondition.Disabled);
            if (GUILayout.Button("Side-by-side")) controller.SetCondition(M7FCondition.SideBySide);
            GUILayout.EndHorizontal();
            GUILayout.Label("Speed (presentation):"); GUILayout.BeginHorizontal(); foreach (var speed in M7FReplayController.AllowedSpeeds) if (GUILayout.Button($"{speed:g}x")) controller.SetSpeed(speed); GUILayout.EndHorizontal();
            var interpolate = GUILayout.Toggle(controller.PresentationInterpolation, "Presentation interpolation (never scientific evidence)"); if (interpolate != controller.PresentationInterpolation) controller.SetInterpolation(interpolate);
            DrawTimeline(); DrawTelemetry(); DrawProvenance(); GUILayout.EndArea();
        }

        M7FReplayData Current => controller.Condition == M7FCondition.Disabled ? controller.Loader.Disabled : controller.Loader.Enabled;
        static void SetSkeleton(M7FFlyRig rig, bool visible) { var value = rig == null ? null : rig.GetComponent<M7FScientificSkeletonVisibility>(); if (value != null && value.Visible != visible) value.SetVisible(visible); }
        void DrawTimeline()
        {
            GUILayout.Label("Canonical milestones (exact values are in manifest)");
            GUILayout.BeginHorizontal();
            foreach (var marker in Milestones)
                if (GUILayout.Button($"{marker.time:g} ms")) controller.SeekFrame(M7FReplayController.FrameForCanonicalTime(marker.time, Current.PhysicsCount));
            GUILayout.EndHorizontal();
            var rect = GUILayoutUtility.GetRect(400, 26); GUI.Box(rect, GUIContent.none);
            var duration = Current.PhysicsTime[^1];
            foreach (var marker in Milestones) { var x = rect.x + (float)(marker.time / duration) * rect.width; GUI.DrawTexture(new Rect(x, rect.y, 1, rect.height), Texture2D.whiteTexture); GUI.Label(new Rect(x + 2, rect.y, 55, 20), marker.label); }
            var cursor = rect.x + (float)(controller.TimeMs / duration) * rect.width; GUI.DrawTexture(new Rect(cursor - 1, rect.y, 3, rect.height), Texture2D.whiteTexture);
        }
        void DrawTelemetry()
        {
            var p = Current.SourcePosition(controller.Frame); var n = controller.NeuralIndex;
            GUILayout.Label($"Body source position: [{p.x:G6}, {p.y:G6}, {p.z:G6}] mm");
            var q = Current.BodyOrientation; var qi = controller.Frame * 4;
            var upZ = 1f - 2f * ((float)(q[qi + 1] * q[qi + 1] + q[qi + 2] * q[qi + 2]));
            GUILayout.Label($"Body-up Z: {upZ:G6}");
            motorScroll = GUILayout.BeginScrollView(motorScroll, GUILayout.Height(165));
            GUILayout.Label("Motor: observer | decoder | applied contribution");
            var names = controller.Loader.Manifest.motor_channel_names;
            for (var i = 0; i < 11; i++) GUILayout.Label($"{names[i],-16} {Current.Observer[n*11+i],10:G5} | {Current.Decoder[n*11+i],10:G5} | {Current.Applied[n*11+i],10:G5}");
            GUILayout.Label("Tibial sensory: LF LM LH RF RM RH");
            var line = new StringBuilder(); for (var i = 0; i < 6; i++) line.Append($"{Current.Sensory[n*6+i]:G5}  "); GUILayout.Label(line.ToString());
            GUILayout.Label($"Delivered sensory drive count: {Current.DeliveredDrive[n]}    Aggregate CNS spikes/activity: {Current.AggregateSpikes[n]}");
            GUILayout.Label(controller.Loader.Manifest.contacts_available ? "RECORDED CONTACT TELEMETRY AVAILABLE" : "CONTACT IDENTITY UNAVAILABLE");
            GUILayout.EndScrollView();
        }
        void DrawProvenance()
        {
            GUILayout.Label("Source: RECORDED CANONICAL M7D STATES");
            GUILayout.Label("M7D SHA: 92b5c645a88fe74e5d6aa0988478c374e8fde3a0e923d42cc13974a3e60d8444");
            GUILayout.Label("Duration: 500 ms | Physics states: 5001 | Neural updates: 1000");
            GUILayout.Label("New physics transitions: 0 | New neural transitions: 0 | Unity physics drives replay: NO");
            GUILayout.Label("Presentation interpolation: OFF by default | Contact identity: UNAVAILABLE");
            GUILayout.Label("Walking classification: NONE | Gait classification: NONE | Biological function inference: NONE");
        }
    }
}
