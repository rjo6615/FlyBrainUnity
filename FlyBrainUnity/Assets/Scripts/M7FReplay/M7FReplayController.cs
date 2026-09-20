using System;
using UnityEngine;

namespace FlyBrain.M7FReplay
{
    public enum M7FCondition { Enabled, Disabled, SideBySide }

    public sealed class M7FReplayController : MonoBehaviour
    {
        public static readonly float[] AllowedSpeeds = { .1f, .25f, .5f, 1f, 2f, 5f, 10f };
        [SerializeField] M7FReplayLoader loader;
        [SerializeField] M7FFlyRig enabledRig, disabledRig;
        [SerializeField] M7FCondition condition;
        [SerializeField] bool presentationInterpolation;
        [SerializeField] float playbackSpeed = 1f;
        [SerializeField] float sideBySideOffset = .08f;
        public bool IsPlaying { get; private set; }
        public int Frame { get; private set; }
        public M7FCondition Condition => condition;
        public bool PresentationInterpolation => presentationInterpolation;
        public M7FReplayLoader Loader => loader;
        public event Action FrameChanged;
        double cursorMs;

        void Start()
        {
            if (loader.Enabled == null) loader.Load();
            if (!enabledRig.ValidateMapping(loader.Manifest.joint_names) || !disabledRig.ValidateMapping(loader.Manifest.joint_names)) { enabled = false; return; }
            SetCondition(condition); Apply(0f);
        }
        void Update()
        {
            if (!IsPlaying || loader.Enabled == null) return;
            cursorMs += Time.unscaledDeltaTime * 1000.0 * playbackSpeed;
            if (cursorMs >= loader.Enabled.PhysicsTime[^1]) { cursorMs = loader.Enabled.PhysicsTime[^1]; IsPlaying = false; }
            Frame = Mathf.Clamp((int)Math.Floor(cursorMs / .1 + 1e-9), 0, loader.Enabled.PhysicsCount - 1);
            var blend = presentationInterpolation && Frame + 1 < loader.Enabled.PhysicsCount ? Mathf.Clamp01((float)((cursorMs - loader.Enabled.PhysicsTime[Frame]) / .1)) : 0f;
            Apply(blend); FrameChanged?.Invoke();
        }
        void Apply(float blend)
        {
            var next = Mathf.Min(Frame + 1, loader.Enabled.PhysicsCount - 1);
            enabledRig.Apply(loader.Enabled, Frame, next, blend); disabledRig.Apply(loader.Disabled, Frame, next, blend);
        }
        public void Play() => IsPlaying = true;
        public void Pause() => IsPlaying = false;
        public void Restart() { Pause(); SeekFrame(0); }
        public void Step(int delta) { Pause(); SeekFrame(Frame + Math.Sign(delta)); }
        public void ScrubNormalized(float value) { Pause(); SeekFrame(Mathf.RoundToInt(Mathf.Clamp01(value) * (loader.Enabled.PhysicsCount - 1))); }
        public void SeekFrame(int frame) { Frame = Mathf.Clamp(frame, 0, loader.Enabled.PhysicsCount - 1); cursorMs = loader.Enabled.PhysicsTime[Frame]; Apply(0f); FrameChanged?.Invoke(); }
        public void SetSpeed(float speed) { foreach (var allowed in AllowedSpeeds) if (Mathf.Approximately(speed, allowed)) { playbackSpeed = speed; return; } throw new ArgumentOutOfRangeException(nameof(speed)); }
        public void SetInterpolation(bool value) { presentationInterpolation = value; Apply(0f); }
        public void SetCondition(M7FCondition value)
        {
            condition = value; enabledRig.gameObject.SetActive(value != M7FCondition.Disabled); disabledRig.gameObject.SetActive(value != M7FCondition.Enabled);
            enabledRig.PresentationOffset = value == M7FCondition.SideBySide ? Vector3.left * sideBySideOffset * .5f : Vector3.zero;
            disabledRig.PresentationOffset = value == M7FCondition.SideBySide ? Vector3.right * sideBySideOffset * .5f : Vector3.zero;
        }
        public string ConditionLabel => condition switch { M7FCondition.Enabled => "NEURAL MOTOR ENABLED", M7FCondition.Disabled => "MATCHED MOTOR-DISABLED CONTROL", _ => "SIDE-BY-SIDE — PRESENTATION OFFSETS ACTIVE" };
        public double TimeMs => loader.Enabled?.PhysicsTime[Frame] ?? 0;
        public int NeuralIndex => loader.Enabled?.NeuralIndexForFrame(Frame) ?? 0;
        public M7FFlyRig EnabledRig => enabledRig;
        public M7FFlyRig DisabledRig => disabledRig;
        public void Configure(M7FReplayLoader replayLoader, M7FFlyRig enabledScientificRig, M7FFlyRig disabledScientificRig)
        { loader = replayLoader; enabledRig = enabledScientificRig; disabledRig = disabledScientificRig; condition = M7FCondition.SideBySide; presentationInterpolation = false; }
    }
}
