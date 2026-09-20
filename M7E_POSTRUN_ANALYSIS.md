# M7E read-only post-run analysis

## Scope and separation

M7E is a standalone NumPy analyzer for the immutable canonical M7D evidence. The
canonical `m7d_raw.npz` is intentionally absent from the Codex analysis workflow
and must remain local and ignored. The analyzer was authored and tested without
reading the canonical raw result, using deterministic synthetic telemetry only.
Canonical execution occurs only on the user's Windows machine.

M7E performs **zero physics transitions and zero neural transitions**. It does
not import FlyGym, MuJoCo, a MaleCNS brain/runtime, or an M7/M7D runner. It never
opens the source archive for writing and refuses to replace completed M7E output.

This is exploratory/descriptive analysis of a 500-ms record. That short duration
limits frequency resolution and cannot establish a stable oscillator from one
spectral peak. M7E does not classify walking, gait, tripod gait, stance, swing,
biological motor function, biological reflexes, or behavioral intent.

## Frozen provenance and schema

Production preflight and analysis require both tracked M7D JSON artifacts to be
`COMPLETE`, plus the raw archive with exactly:

* byte size `16737088`;
* SHA-256 `92b5c645a88fe74e5d6aa0988478c374e8fde3a0e923d42cc13974a3e60d8444`.

The NPZ is loaded with `allow_pickle=False`. Its inventory must exactly match the
manifest: two named conditions, 5,001 physics states with 42 joint positions,
and 1,000 neural samples with six sensory and eleven admitted motor interfaces.
All manifest shapes/dtypes, finite flags, finite numeric values, monotonic clocks,
0.1-ms physics cadence, physics-derived 0.5-ms neural timestamps, and identical
condition clocks are checked. The 42-joint order is the frozen FlyGym actuator
order already recorded by the project; it is not inferred from result magnitude.

## Analysis

The report puts enabled-minus-disabled comparisons first. It includes body path,
displacement, height, body-up Z, quaternion orientation/yaw change, and velocity;
all-joint range, variation, standard deviation, RMS velocity and reversals;
admitted-joint divergence/onset/integration and motor relationship; per-leg
aggregates; observer, decoder, and physically admitted contribution metrics;
sensory and delivered-drive differences; causal milestone reconstruction; and
comparison with the M7D summary.

Temporal descriptions include centered crossings, extrema, autocorrelation,
periodogram peak/power fraction, estimated cycle count, and a conservative label.
Pairwise motor-interface cross-correlations report normalized peak, lag, zero-lag
value, sign language, and active overlap. Thresholds are fixed numerical-precision
rules, not fitted to canonical results. The archive's contact-force vectors lack
recorded geom-to-leg identity, so M7E explicitly declines to invent support or
per-leg contact classifications.

The analysis writes only:

* `interface_output/m7e_postrun_analysis/m7e_analysis.json`
* `interface_output/m7e_postrun_analysis/m7e_manifest.json`

No derived NPZ or plots are required or generated automatically.

## Windows commands

Run preflight first; it validates provenance/schema/output availability but does
not perform analysis:

```powershell
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.m7e_postrun_analysis --windows-preflight
```

Only after reviewing a passing preflight, the future analysis command is:

```powershell
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.m7e_postrun_analysis --analyze-windows
```

Do not run the analysis before that review.
