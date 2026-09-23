using System;
using UnityEngine;

namespace FlyBrain.M7FReplay
{
    public sealed class M9DReplayController : MonoBehaviour
    {
        public const int FinalFrame = 15000;
        public const double FrameIntervalMs = .1;
        public const double FinalTimeMs = 1500;
        public static readonly float[] AllowedSpeeds = { .05f, .1f, .25f, .5f, 1f };
        [SerializeField] M9DReplayLoader loader; [SerializeField] M7FFlyRig leftRig, rightRig;
        [SerializeField] M9DCondition leftCondition = M9DCondition.A_P, rightCondition = M9DCondition.B_P;
        [SerializeField] bool sideBySide = true, presentationInterpolation; [SerializeField] float speed = 1, presentationSeparation = .08f;
        public int Frame { get; private set; } public bool IsPlaying { get; private set; }
        public bool PresentationInterpolation => presentationInterpolation; public bool SideBySide => sideBySide;
        public M9DCondition LeftCondition => leftCondition; public M9DCondition RightCondition => rightCondition;
        public double TimeMs => loader != null && loader.Replays.Count == 4 ? loader.Replays[leftCondition].Time[Frame] : 0;
        double cursor;
        void Start() { if (loader.Replays.Count == 0) loader.Load(); if (!leftRig.ValidateMapping(loader.Manifest.joint_names) || !rightRig.ValidateMapping(loader.Manifest.joint_names)) { Debug.LogError("M9D presentation rig mapping is invalid; replay state will not be applied.",this); return; } SetComparison(leftCondition, rightCondition, sideBySide); SeekFrame(0); }
        void Update() => AdvancePresentation(Time.unscaledDeltaTime);
        public void AdvancePresentation(double elapsedSeconds)
        {
            if (!IsPlaying || elapsedSeconds <= 0) return;
            cursor = Math.Min(FinalTimeMs, cursor + elapsedSeconds * 1000d * speed);
            Frame = Mathf.Clamp((int)Math.Floor(cursor / FrameIntervalMs + 1e-9), 0, FinalFrame);
            Apply();
            if (Frame == FinalFrame) Pause();
        }
        void Apply() { if(loader == null || loader.Replays.Count != 4)return; var blend = presentationInterpolation && Frame < FinalFrame ? Mathf.Clamp01((float)((cursor - loader.Replays[leftCondition].Time[Frame]) / FrameIntervalMs)) : 0; leftRig.Apply(loader.Replays[leftCondition], Frame, Math.Min(Frame+1,FinalFrame), blend); rightRig.Apply(loader.Replays[rightCondition], Frame, Math.Min(Frame+1,FinalFrame), blend); }
        public void SetComparison(M9DCondition left, M9DCondition right, bool compare) { leftCondition=left; rightCondition=right; sideBySide=compare; leftRig.gameObject.SetActive(true); rightRig.gameObject.SetActive(compare); leftRig.PresentationOffset=compare ? Vector3.left*presentationSeparation*.5f : Vector3.zero; rightRig.PresentationOffset=compare ? Vector3.right*presentationSeparation*.5f : Vector3.zero; if (loader.Replays.Count == 4) Apply(); }
        public void Play() => IsPlaying = true; public void Pause() => IsPlaying = false; public void TogglePlayback() { if (IsPlaying) Pause(); else Play(); }
        public void Restart() { Pause(); SeekFrame(0); } public void Step(int direction) { Pause(); SeekFrame(Frame + Math.Sign(direction)); }
        public void Scrub(float normalized) { Pause(); SeekFrame(Mathf.RoundToInt(Mathf.Clamp01(normalized)*FinalFrame)); }
        public void SeekFrame(int frame) { Frame=Mathf.Clamp(frame,0,FinalFrame); cursor=Frame*FrameIntervalMs; Apply(); }
        public void SetSpeed(float value) { foreach (var allowed in AllowedSpeeds) if (Mathf.Approximately(value,allowed)) { speed=value; return; } throw new ArgumentOutOfRangeException(nameof(value)); }
        public void SetInterpolation(bool value) { presentationInterpolation=value; Apply(); }
        public bool ForceActive => TimeMs >= 500 && TimeMs < 520 &&
            (leftCondition is M9DCondition.A_P or M9DCondition.B_P ||
             sideBySide && (rightCondition is M9DCondition.A_P or M9DCondition.B_P));
        public static string Label(M9DCondition c) => c switch { M9DCondition.A_P => "A_P — Brain Enabled + Push\nMapped MaleCNS motor output ENABLED", M9DCondition.A_C => "A_C — Brain Enabled + No Push\nMapped MaleCNS motor output ENABLED", M9DCondition.B_P => "B_P — Brain Disabled + Push\nMapped MaleCNS motor output DISABLED before physical application", _ => "B_C — Brain Disabled + No Push\nMapped MaleCNS motor output DISABLED before physical application" };
        public void Configure(M9DReplayLoader value, M7FFlyRig left, M7FFlyRig right) { loader=value; leftRig=left; rightRig=right; presentationInterpolation=false; speed=1; Pause(); SeekFrame(0); }
    }
}
