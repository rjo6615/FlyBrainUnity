# M5D-5B — Six-tibia proprioceptive closed-loop causal test

## Status and scope

This is a **locked protocol**, not a scientific result. The checked-in primary
artifact is truthfully `NOT_RUN`. The first successful canonical Windows run
is Scientific Run #1; it is run once with seed 1 for 100 ms (0.1-ms physics,
0.5-ms neural updates), with no retry, sweep, or tuning.

## Architecture

Both conditions run full FlyGym physics, full MaleCNS, the unchanged M5D-5A
six-leg `SensoryEncoder` channels, and the unchanged LM Tarsus5 tactile
channel. Both observe the mapped antagonist motor populations, update the
40-ms spike-rate filters and existing decoder, and pass through an independent
instance of the M5D-4C common physical-command pipeline. The sole intervention
is `admitted_neural_contribution = raw_neural_contribution` in
`CLOSED_LOOP_ENABLED`, versus zero in `MOTOR_OUTPUT_DISABLED`. Baselines,
history, limits, slew, final clamp, action construction, and MuJoCo control are
common code. In particular, the disabled path never directly writes a freshly
measured position in place of target history.

The six locked channels/actuators are LF/5/T1-left/23, LM/12/T2-left/80,
LH/19/T3-left/93, RF/26/T1-right/13, RM/33/T2-right/83, and
RH/40/T3-right/100 (392 directly driven neurons).

## Locked interfaces and counterfactual RNG

The encoder remains: angle range [-1.35, 1.30] rad, Gaussian width 0.25
normalized, maximum 120 Hz, rates <=5 Hz cut to zero, zero baseline, and event
probability `rate_hz * 0.5 / 1000`. The decoder remains: spike-count-to-Hz,
40-ms low-pass, 17-Hz half activation, extensor minus flexor, maximum 0.25-rad
offset, physical joint limits, ±4-rad/s slew, and final clamps.

Each condition recreates the same six PCG64 streams from
`SeedSequence(1).spawn(6)` in LF, LM, LH, RF, RM, RH order. Draw counters and
draw identity distinguish stream desynchronization from different threshold
outcomes caused by physically different rates. Tactile candidates likewise
use common random numbers until their physical source differs.

## Evidence rules

C0–C13 record, respectively: active proprioceptive delivery; mapped motor
event; nonzero raw decoding; admitted enabled contribution; six-tibia action;
MuJoCo control; physical state; tibia source; proprioceptive rate; aligned-draw
candidate; delivered proprioception; later downstream non-proprioceptive CNS
state; later downstream non-proprioceptive CNS spike; and mapped motor
divergence after qualified feedback CNS divergence. C11/C12 must be strictly
after C10 and C13 must be later than the qualified CNS boundary. Null evidence
stays null and classifications fail closed.

All 392 directly driven proprioceptive neurons are excluded from downstream
metrics. Direct tactile neurons are separately identified and excluded where
applicable. Exact pre-intervention equality covers physical state/contact,
six angles, both sensory encodings/candidates/deliveries, neural and decoder
state, targets/history, all 42 actions, and MuJoCo control.

## Provenance and execution

The authoritative COMPLETE M5D-5A JSON is raw-byte SHA-256 locked and checked
semantically. Its two implementation files are canonical-LF SHA-256 locked.
M5D-5A's verifier recursively checks the established M5D-4E/4D/4C chain.
Failure is closed and historical artifacts are not modified.

Canonical Windows command (from repository root):

```powershell
python -m malecns_backend.embodiment.proprioceptive_closed_loop_audit --live --duration-ms 100 --seed 1 --json malecns_backend/embodiment/interface_output/proprioceptive_closed_loop_100ms.json
```

No gait, CPG, tripod, scripted coordination, new drive/noise, model, mapping,
gain, or parameter tuning is introduced. Interpret results only as behavior of
the modeled sensory and motor interfaces.
