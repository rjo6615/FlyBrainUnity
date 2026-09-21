# M7F-VIS2 P4 — residual joint-axis metric diagnosis

## Decision and status

The residual is classified **ANGULAR_VALIDATION_METRIC_FLOAT_PRECISION_ERROR**.
The acceptance tolerance remains `2e-4` radians. The rig, replay, reference
JSON, coordinate and quaternion conversions, scale, and M7D/M7E are unchanged.
Only evaluation of the same unsigned angle has changed, from single-precision
`acos(dot)` to double-precision `atan2(||a x b||, a dot b)` after
double-precision normalization.

> **UNITY SCIENTIFIC RIG: NOT YET VALIDATED**

That status cannot change until the unchanged nine-frame Windows gate passes.

## Phase 1: computation and conditioning audit

The former validator normalized two `Vector3` values, evaluated
`Vector3.Dot`, clamped it, and called `Mathf.Acos`. Every operation in that
path was binary32 (`System.Single`). It was therefore exactly the computation
under audit.

For the reported frame 540 `joint_LHTarsus1` values:

| evaluation | angle (radians) |
|---|---:|
| former Unity float dot + float acos | 0.00048828125 (reported; 0.0004882812548506386 using the reported dot in double `acos`) |
| normalized component arithmetic + acos, all binary64 | 5.118716966306524e-7 |
| normalized binary64 atan2(cross norm, dot) | 5.121565679716428e-7 |

The raw vector delta is
`[-4.172325134277344e-7, 4.0978193283081055e-8,
2.980232238769531e-7]`, with norm `5.143734290921165e-7`. The reported
binary32 dot is `0.99999988079071045`; the normalized binary64 dot is
`0.999999999999869`. At the reported float dot, the magnitude of the
derivative of `acos`, `1/sqrt(1-dot^2)`, is about 2048. A one-ULP dot error
is consequently magnified into a quantized angle hundreds of times larger
than the underlying direction difference.

For representative identical finite axes, both acos formulations and the
stable formulation produce zero (subject to whether a separately rounded dot
lands exactly on one), while the stable cross norm is exactly zero and hence
`atan2(0, positive)=0`. Opposite axes produce approximately pi. A zero or
non-finite input is invalid and the repaired evaluator returns positive
infinity so acceptance fails closed.

## Phase 2: representation versus kinematics

The corrected Windows report supplied for this diagnosis retains only the
aggregate maximum/RMS and the single worst sample; it does not contain the
per-sample vectors for the other float-acos exceedances. It is therefore not
possible to honestly manufacture a frame/joint table for those samples from
that artifact. The complete available offending sample is:

| frame | joint | expected | actual | delta | delta norm | float dot | normalized double dot | float acos | double acos | double atan2 |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|
| 540 | joint_LHTarsus1 | `[0.65671324729919434, 0.049622122198343277, 0.75250601768493652]` | `[0.65671283006668091, 0.04962216317653656, 0.7525063157081604]` | `[-4.172325134277344e-7, 4.0978193283081055e-8, 2.980232238769531e-7]` | 5.143734290921165e-7 | 0.99999988079071045 | 0.999999999999869 | 4.8828125e-4 | 5.118716966306524e-7 | 5.121565679716428e-7 |

This sample is about 390 times below the acceptance tolerance under the stable
measurement. The next authoritative Windows run evaluates every joint/frame
with that stable measurement; it will still fail, without suppression, if any
real residual exceeds `2e-4` radians.

## Phase 3: precision trace

1. MuJoCo exposes `data.xaxis` as native double and Python reads it as binary64.
2. JSON serialization preserves those binary64 values as decimal text; the
   authoritative JSON is unchanged.
3. Unity `JsonUtility` loads each reference component into `double[]`, retaining
   binary64 at this stage.
4. `M7FScientificFlyRigDefinition.Vector` explicitly converts each component
   to float because Unity's `Vector3` is binary32. This is the first unavoidable
   conversion for a value entering Unity's transform system.
5. Coordinate conversion permutes/negates `Vector3` components and therefore
   remains binary32.
6. Unity `Transform` position/rotation, quaternion composition, and the
   reconstructed `rotation * localAxis` direction are binary32. This is the
   unavoidable representation precision of the rendered rig.
7. The old validator then performed normalization, dot, and acos in binary32,
   adding an avoidable ill-conditioned final reduction. The repair promotes
   the already-reconstructed components to double, normalizes them in double,
   and uses the stable atan2 identity. It cannot restore information lost in
   the Transform, but it measures the angle represented by those floats
   without introducing the float-acos artifact.

No native simulation was rerun, and `mj_step` remains zero.

## Windows rerun

From the repository root:

```powershell
& "C:\Program Files\Unity\Hub\Editor\6000.3.10f1\Editor\Unity.exe" -batchmode -quit -projectPath .\FlyBrainUnity -runTests -testPlatform EditMode -testFilter FlyBrain.Tests.M7FReplayTests.NineNativeMjForwardFramesAreTheNumericalAcceptanceGate -testResults .\m7f_vis2_unity_results.xml -logFile .\m7f_vis2_unity.log
```
