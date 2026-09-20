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
        public float PlaybackSpeed => playbackSpeed;
        public bool IsLoaded => loader != null && loader.Enabled != null && loader.Disabled != null;
        public bool EnabledReplayLoaded => loader != null && loader.Enabled != null;
        public bool DisabledReplayLoaded => loader != null && loader.Disabled != null;
        public int LastAppliedFrame { get; private set; } = -1;
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
            AdvancePlayback(Time.unscaledDeltaTime);
        }
        /// <summary>Advances the presentation clock. The argument is Unity time in seconds.</summary>
        public void AdvancePlayback(double elapsedSeconds)
        {
            if (!IsPlaying) return;
            if (!IsLoaded)
            {
                IsPlaying = false;
                Debug.LogError("M7F PLAYBACK: cannot advance because both canonical replays are not loaded.", this);
                return;
            }
            cursorMs += elapsedSeconds * 1000.0 * playbackSpeed;
            if (cursorMs >= loader.Enabled.PhysicsTime[^1]) { cursorMs = loader.Enabled.PhysicsTime[^1]; IsPlaying = false; }
            Frame = FrameForCanonicalTime(cursorMs, loader.Enabled.PhysicsCount);
            var blend = presentationInterpolation && Frame + 1 < loader.Enabled.PhysicsCount ? Mathf.Clamp01((float)((cursorMs - loader.Enabled.PhysicsTime[Frame]) / .1)) : 0f;
            Apply(blend); FrameChanged?.Invoke();
        }
        public static int FrameForCanonicalTime(double milliseconds, int physicsCount)
        {
            if (physicsCount < 1) throw new ArgumentOutOfRangeException(nameof(physicsCount));
            return Mathf.Clamp((int)Math.Floor(milliseconds / .1 + 1e-9), 0, physicsCount - 1);
        }
        void Apply(float blend)
        {
            var next = Mathf.Min(Frame + 1, loader.Enabled.PhysicsCount - 1);
            enabledRig.Apply(loader.Enabled, Frame, next, blend); disabledRig.Apply(loader.Disabled, Frame, next, blend);
            LastAppliedFrame = Frame;
        }
        public void Play()
        {
            if (!IsLoaded) { IsPlaying = false; Debug.LogError("M7F PLAYBACK: PLAY rejected because both canonical replays are not loaded.", this); return; }
            IsPlaying = true; Debug.Log("M7F PLAYBACK: PLAY", this);
        }
        public void Pause() { IsPlaying = false; Debug.Log("M7F PLAYBACK: PAUSE", this); }
        public void TogglePlayback() { if (IsPlaying) Pause(); else Play(); }
        public void Restart() { IsPlaying = false; SeekFrame(0); Debug.Log("M7F PLAYBACK: RESTART", this); }
        public void Step(int delta) { Pause(); SeekFrame(Frame + Math.Sign(delta)); }
        public void ScrubNormalized(float value) { Pause(); SeekFrame(Mathf.RoundToInt(Mathf.Clamp01(value) * (loader.Enabled.PhysicsCount - 1))); }
        public void SeekFrame(int frame)
        {
            if (!IsLoaded) { Debug.LogError("M7F PLAYBACK: seek rejected because both canonical replays are not loaded.", this); return; }
            Frame = Mathf.Clamp(frame, 0, loader.Enabled.PhysicsCount - 1); cursorMs = loader.Enabled.PhysicsTime[Frame]; Apply(0f); FrameChanged?.Invoke();
        }
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
        {
            loader = replayLoader; enabledRig = enabledScientificRig; disabledRig = disabledScientificRig;
            condition = M7FCondition.Enabled; presentationInterpolation = false;
            enabledRig.gameObject.SetActive(true); disabledRig.gameObject.SetActive(false);
        }
    }
}
