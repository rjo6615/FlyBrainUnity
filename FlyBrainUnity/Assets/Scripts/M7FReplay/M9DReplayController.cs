using System;
using UnityEngine;

namespace FlyBrain.M7FReplay
{
    public sealed class M9DReplayController : MonoBehaviour
    {
        public const int FinalFrame = 15000;
        public const double FrameIntervalMs = .1;
        public const double FinalTimeMs = 1500;
        public const double ForceStartMs = 500, ForceStopMs = 520;
        public const int PerturbationReplayStartFrame = 4750;
        public const double PerturbationReplayStopMs = 650;
        public static readonly float[] AllowedSpeeds = { .05f, .1f, .25f, .5f, 1f };
        [SerializeField] M9DReplayLoader loader;
        [SerializeField] M7FFlyRig leftRig, rightRig;
        [SerializeField] M9DCondition leftCondition = M9DCondition.A_P, rightCondition = M9DCondition.B_P;
        [SerializeField] bool sideBySide = true, presentationInterpolation, trajectoryTraces = true;
        [SerializeField] float speed = 1, presentationSeparation = .36f;
        [SerializeField] M9DTrajectoryTrace leftTrace, rightTrace;
        bool replayPerturbation;
        public int Frame { get; private set; }
        public bool IsPlaying { get; private set; }
        public bool IsInitialized { get; private set; }
        public string InitializationError { get; private set; }
        public bool PresentationInterpolation => presentationInterpolation;
        public bool SideBySide => sideBySide;
        public float PresentationSpeed => speed;
        public float PresentationSeparation => presentationSeparation;
        public bool TrajectoryTracesVisible => trajectoryTraces;
        public M9DCondition LeftCondition => leftCondition;
        public M9DCondition RightCondition => rightCondition;
        public M9DReplayLoader Loader => loader;
        public M7FFlyRig LeftRig => leftRig;
        public M7FFlyRig RightRig => rightRig;
        public double TimeMs => IsInitialized ? loader.Replays[leftCondition].Time[Frame] : 0;
        double cursor;

        void Start() => Initialize();
        void Update() => AdvancePresentation(Time.unscaledDeltaTime);

        /// <summary>Validates every dependency before any replay object is dereferenced.</summary>
        public bool Initialize()
        {
            IsInitialized = false;
            Pause();
            if (!Require(loader, nameof(loader)) || !Require(leftRig, nameof(leftRig)) || !Require(rightRig, nameof(rightRig))) return false;
            if (leftRig == rightRig) return Fail("leftRig and rightRig must reference distinct scientific rigs.");
            try
            {
                if (loader.Replays.Count == 0) loader.Load();
            }
            catch (Exception exception)
            {
                return Fail($"loader failed to load and validate the frozen replay: {exception.GetType().Name}: {exception.Message}");
            }
            if (loader.Manifest == null) return Fail("loader.Manifest is null after loading.");
            if (loader.Replays.Count != 4) return Fail($"loader.Replays must contain four conditions; found {loader.Replays.Count}.");
            if (!leftRig.ValidateMapping(loader.Manifest.joint_names)) return Fail("leftRig mapping is invalid: " + leftRig.ValidationStatus);
            if (!rightRig.ValidateMapping(loader.Manifest.joint_names)) return Fail("rightRig mapping is invalid: " + rightRig.ValidationStatus);
            IsInitialized = true;
            SetComparison(leftCondition, rightCondition, sideBySide);
            SeekFrame(0);
            return true;
        }

        bool Require(UnityEngine.Object value, string dependency) => value != null || Fail($"serialized dependency '{dependency}' is not assigned.");
        bool Fail(string detail)
        {
            InitializationError = "M9D replay initialization failed: " + detail;
            Debug.LogError(InitializationError, this);
            return false;
        }

        public void AdvancePresentation(double elapsedSeconds)
        {
            if (!IsInitialized || !IsPlaying || elapsedSeconds <= 0) return;
            cursor = Math.Min(FinalTimeMs, cursor + elapsedSeconds * 1000d * speed);
            if (replayPerturbation && cursor >= PerturbationReplayStopMs) { cursor = PerturbationReplayStopMs; replayPerturbation = false; Pause(); }
            Frame = Mathf.Clamp((int)Math.Floor(cursor / FrameIntervalMs + 1e-9), 0, FinalFrame);
            Apply();
            if (Frame == FinalFrame) Pause();
        }

        void Apply()
        {
            if (!IsInitialized) return;
            var blend = presentationInterpolation && Frame < FinalFrame ? Mathf.Clamp01((float)((cursor - loader.Replays[leftCondition].Time[Frame]) / FrameIntervalMs)) : 0;
            leftRig.Apply(loader.Replays[leftCondition], Frame, Math.Min(Frame + 1, FinalFrame), blend);
            rightRig.Apply(loader.Replays[rightCondition], Frame, Math.Min(Frame + 1, FinalFrame), blend);
        }

        public bool SetComparison(M9DCondition left, M9DCondition right, bool compare)
        {
            if (!IsInitialized) return false;
            leftCondition = left; rightCondition = right; sideBySide = compare;
            leftRig.gameObject.SetActive(true); rightRig.gameObject.SetActive(compare);
            leftRig.PresentationOffset = compare ? Vector3.left * presentationSeparation * .5f : Vector3.zero;
            rightRig.PresentationOffset = compare ? Vector3.right * presentationSeparation * .5f : Vector3.zero;
            leftTrace?.Refresh(leftCondition, leftRig.PresentationOffset);
            rightTrace?.Refresh(rightCondition, rightRig.PresentationOffset);
            leftTrace?.SetVisible(trajectoryTraces); rightTrace?.SetVisible(trajectoryTraces&&compare);
            Apply();
            return true;
        }

        public void Play() { if (IsInitialized) IsPlaying = true; }
        public void Pause() => IsPlaying = false;
        public void TogglePlayback() { if (IsPlaying) Pause(); else Play(); }
        public void Restart() { Pause(); SeekFrame(0); }
        /// <summary>Presentation convenience only: changes the replay clock and display speed.</summary>
        public void ReplayPerturbation() { if (!IsInitialized) return; SeekFrame(PerturbationReplayStartFrame); SetSpeed(.1f); replayPerturbation = true; Play(); }
        public void Step(int direction) { Pause(); SeekFrame(Frame + Math.Sign(direction)); }
        public void Scrub(float normalized) { Pause(); SeekFrame(Mathf.RoundToInt(Mathf.Clamp01(normalized) * FinalFrame)); }
        public void SeekFrame(int frame) { if (!IsInitialized) return; Frame = Mathf.Clamp(frame, 0, FinalFrame); cursor = Frame * FrameIntervalMs; Apply(); }
        public void SetSpeed(float value) { foreach (var allowed in AllowedSpeeds) if (Mathf.Approximately(value, allowed)) { speed = value; return; } throw new ArgumentOutOfRangeException(nameof(value)); }
        public void SetInterpolation(bool value) { presentationInterpolation = value; Apply(); }
        public bool ForceActive => IsInitialized && TimeMs >= ForceStartMs && TimeMs < ForceStopMs &&
            (leftCondition is M9DCondition.A_P or M9DCondition.B_P || sideBySide && (rightCondition is M9DCondition.A_P or M9DCondition.B_P));
        public static string Label(M9DCondition c) => c switch { M9DCondition.A_P => "A_P — Brain Enabled + Push\nMapped MaleCNS motor output ENABLED", M9DCondition.A_C => "A_C — Brain Enabled + No Push\nMapped MaleCNS motor output ENABLED", M9DCondition.B_P => "B_P — Brain Disabled + Push\nMapped MaleCNS motor output DISABLED before physical application", _ => "B_C — Brain Disabled + No Push\nMapped MaleCNS motor output DISABLED before physical application" };
        public void SetTrajectoryTraces(bool visible) { trajectoryTraces=visible; leftTrace?.SetVisible(visible); rightTrace?.SetVisible(visible&&sideBySide); }
        public void ConfigureTraces(M9DTrajectoryTrace left, M9DTrajectoryTrace right) { leftTrace=left; rightTrace=right; SetTrajectoryTraces(true); }
        public void Configure(M9DReplayLoader value, M7FFlyRig left, M7FFlyRig right)
        {
            loader = value; leftRig = left; rightRig = right;
            leftCondition = M9DCondition.A_P; rightCondition = M9DCondition.B_P; sideBySide = true;
            leftRig.PresentationOffset=Vector3.left*presentationSeparation*.5f; rightRig.PresentationOffset=Vector3.right*presentationSeparation*.5f;
            presentationInterpolation = false; speed = 1; Frame = 0; cursor = 0; IsInitialized = false; InitializationError = null; Pause();
        }
    }
}
