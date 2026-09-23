using System;
using UnityEngine;

namespace FlyBrain.M7FReplay
{
    public sealed class M9DReplayController : MonoBehaviour
    {
        public static readonly float[] AllowedSpeeds = { .05f, .1f, .25f, .5f, 1f };
        [SerializeField] M9DReplayLoader loader; [SerializeField] M7FFlyRig leftRig, rightRig;
        [SerializeField] M9DCondition leftCondition = M9DCondition.A_P, rightCondition = M9DCondition.B_P;
        [SerializeField] bool sideBySide = true, presentationInterpolation; [SerializeField] float speed = 1, presentationSeparation = .08f;
        public int Frame { get; private set; } public bool IsPlaying { get; private set; }
        public bool PresentationInterpolation => presentationInterpolation; public bool SideBySide => sideBySide;
        public M9DCondition LeftCondition => leftCondition; public M9DCondition RightCondition => rightCondition;
        public double TimeMs => loader != null && loader.Replays.Count == 4 ? loader.Replays[leftCondition].Time[Frame] : 0;
        double cursor;
        void Start() { if (loader.Replays.Count == 0) loader.Load(); if (!leftRig.ValidateMapping(loader.Manifest.joint_names) || !rightRig.ValidateMapping(loader.Manifest.joint_names)) { enabled = false; return; } SetComparison(leftCondition, rightCondition, sideBySide); SeekFrame(0); }
        void Update() { if (!IsPlaying) return; cursor = Math.Min(1500, cursor + Time.unscaledDeltaTime * 1000 * speed); Frame = Mathf.Clamp((int)Math.Floor(cursor / .1 + 1e-9), 0, 15000); Apply(); if (Frame == 15000) IsPlaying = false; }
        void Apply() { var blend = presentationInterpolation && Frame < 15000 ? Mathf.Clamp01((float)((cursor - loader.Replays[leftCondition].Time[Frame]) / .1)) : 0; leftRig.Apply(loader.Replays[leftCondition], Frame, Math.Min(Frame+1,15000), blend); rightRig.Apply(loader.Replays[rightCondition], Frame, Math.Min(Frame+1,15000), blend); }
        public void SetComparison(M9DCondition left, M9DCondition right, bool compare) { leftCondition=left; rightCondition=right; sideBySide=compare; leftRig.gameObject.SetActive(true); rightRig.gameObject.SetActive(compare); leftRig.PresentationOffset=compare ? Vector3.left*presentationSeparation*.5f : Vector3.zero; rightRig.PresentationOffset=compare ? Vector3.right*presentationSeparation*.5f : Vector3.zero; if (loader.Replays.Count == 4) Apply(); }
        public void Play() => IsPlaying = true; public void Pause() => IsPlaying = false; public void TogglePlayback() { if (IsPlaying) Pause(); else Play(); }
        public void Restart() { Pause(); SeekFrame(0); } public void Step(int direction) { Pause(); SeekFrame(Frame + Math.Sign(direction)); }
        public void Scrub(float normalized) { Pause(); SeekFrame(Mathf.RoundToInt(Mathf.Clamp01(normalized)*15000)); }
        public void SeekFrame(int frame) { Frame=Mathf.Clamp(frame,0,15000); cursor=Frame*.1; if (loader.Replays.Count == 4) Apply(); }
        public void SetSpeed(float value) { foreach (var allowed in AllowedSpeeds) if (Mathf.Approximately(value,allowed)) { speed=value; return; } throw new ArgumentOutOfRangeException(nameof(value)); }
        public void SetInterpolation(bool value) { presentationInterpolation=value; Apply(); }
        public bool ForceActive => TimeMs >= 500 && TimeMs < 520 &&
            (leftCondition is M9DCondition.A_P or M9DCondition.B_P ||
             sideBySide && (rightCondition is M9DCondition.A_P or M9DCondition.B_P));
        public static string Label(M9DCondition c) => c switch { M9DCondition.A_P => "A_P — Brain Enabled + Push\nMapped MaleCNS motor output ENABLED", M9DCondition.A_C => "A_C — Brain Enabled + No Push\nMapped MaleCNS motor output ENABLED", M9DCondition.B_P => "B_P — Brain Disabled + Push\nMapped MaleCNS motor output DISABLED before physical application", _ => "B_C — Brain Disabled + No Push\nMapped MaleCNS motor output DISABLED before physical application" };
        public void Configure(M9DReplayLoader value, M7FFlyRig left, M7FFlyRig right) { loader=value; leftRig=left; rightRig=right; presentationInterpolation=false; }
    }
}
