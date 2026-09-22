# M9A-3 Attempt 3 — matched-control perturbation calibration

## Status and scope

**NOT RUN.** Attempt 3 is a separately preregistered physics-only calibration. It does not test MaleCNS, stabilization, balance, reflexes, locomotion, gait, or biological function. Attempt 2 remains frozen as `NO_PREREGISTERED_CANDIDATE_QUALIFIES`; its evidence is provenance only and must never be rescored with the Attempt-3 reducer.

Attempt-2 forensics found an exactly shared P/C initialization transient (speed `41.54495248689062`, state 61, `6.100000000000003 ms`, velocity `[-4.922182135683325, -0.9162088712959617, -41.24215999999658]`) before intervention. Attempt 3 therefore characterizes the baseline separately rather than raising or retaining the former absolute-speed qualification limit.

## Frozen protocol

For each ascending magnitude **0.256, 0.512, 1.024, 2.048**, fresh matched P/C runtimes use corrected M7D/B4 initialization, fixed 42-joint commands, disabled adhesion, FlyGym 1.2.1/MuJoCo 3.2.7, 0.1-ms physics cadence, and 15,001 states through 1500 ms. P receives world-frame `[0, magnitude, 0]` at the unique authoritative Thorax COM with zero torque on exactly outgoing transition indices 5000–5199 (500 ms inclusive, 520 ms exclusive); C is always zero-forced. Window membership is index-based.

Complete physical telemetry, timestamps, commands, and all pre-force states must match exactly and be finite. The interval `0 <= t < 500 ms` records per-condition maximum speed, displacement, tilt, fall, rollover, and contact state descriptively.

Starting at the first post-force state, measurable divergence is `>=1e-9`. Meaningfulness requires contact divergence, root-position divergence `>=0.005 mm`, shortest-arc orientation divergence `>=0.25 deg`, or distal-tarsus divergence `>=0.01 mm`. P−C safety limits are respectively `<=0.5 mm`, `<=30 deg`, and velocity divergence `<=5.0`. Absolute guards require finite telemetry, no fall/rollover through 750 ms, and each condition at `<=1.5 mm` displacement and `<=60 deg` tilt. Absolute speed is descriptive only and never catastrophic or qualifying.

The lowest candidate passing every gate is selected. If none passes, the result is `NO_PREREGISTERED_CANDIDATE_QUALIFIES`; there is no escalation.

## Execution boundary

The isolated output directory is `interface_output/m9a_3_matched_control_calibration_attempt_3`. Exclusive creation protects all prior evidence. The dedicated Windows preflight constructs two fresh physics runtimes only for static identity and initialization inspection; it advances zero physics transitions, imports/constructs no MaleCNS, and advances zero neural transitions.

```powershell
python -m malecns_backend.embodiment.m9a_3_attempt_3_calibration --windows-preflight
# FUTURE SEPARATE AUTHORIZATION ONLY — DO NOT RUN AS PART OF PREREGISTRATION:
python -m malecns_backend.embodiment.m9a_3_attempt_3_calibration --run-windows
```
