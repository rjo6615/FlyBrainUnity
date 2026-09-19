# M5D-5B — Six-tibia proprioceptive closed-loop causal test

## Status and scope

This is a **locked protocol**, not a scientific result. The first Windows
invocation aborted in `verify_provenance()` before either live condition began.
It produced no scientific trajectory: all C0-C13 milestones are null and all
RNG draw counters are zero. The failure is preserved verbatim as
`interface_output/proprioceptive_closed_loop_100ms_first_attempt_provenance_failure.json`.
It is **not** Scientific Run #1. The next successfully executing canonical
Windows run remains Scientific Run #1; it is run once with seed 1 for 100 ms
(0.1-ms physics, 0.5-ms neural updates), with no retry, sweep, or tuning.

The next invocation passed that corrected provenance check but found that the
documented repository-local Windows adapter had accidentally been omitted from
the M5D-5B implementation commit. It likewise entered neither condition. Its
verbatim no-trajectory report is preserved as
`interface_output/proprioceptive_closed_loop_100ms_first_attempt_unavailable.json`.
Neither failed invocation is Scientific Run #1. The next successfully
executing canonical Windows run is Scientific Run #1.

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

The omitted module is now the repository-local
`_windows_proprioceptive_closed_loop_adapter`. It is integration code rather
than a placeholder or alternate simulator: it calls the established M5D-4C
FlyGym arena constructor, constructs the actual `MaleCNSBrain`, and returns two
raw traces to the M5D-5B reducer. Thus the original import name and separation
between live acquisition and evidence reduction were correct; the file was the
missing implementation.

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

### M5D-5A artifact-lock diagnostic

The former artifact lock, `c52be9d9b1989c4631d6f7907f13465cebf645492b8114654e0a3dc898f3833d`,
is the LF checkout/blob of the authoritative COMPLETE result introduced at
commit `6797480a33a6cb0f7952784c661e1ca0e0f7eaf5`. It is not the earlier `NOT_RUN`
or `FAILED` artifact. The Windows file has the same JSON and scientific content
but one CRLF record terminator; its raw SHA-256 is
`3e0131be35d7b00004e1e014e5007ff7455b422b7fd67a2cd25a67eadead5ca9`.
The mismatch is therefore `STALE_LOCK`, `LINE_ENDING_ONLY`, and
`JSON_SERIALIZATION_ONLY`, not a scientific-content difference. The raw lock
now names the authoritative Windows bytes, and `.gitattributes` marks only this
artifact `-text` so Git cannot normalize those bytes while the JSON remains
viewable and diffable.

In addition to the exact byte lock, validation requires the real artifact paths
`schema`, `run_status`, `classification`, `provenance.verified`,
`candidate_parity`, `physics_identical`,
`aggregate.directly_driven_proprioceptive_neurons`, and the five fields under
`protocol` (`seed`, `duration_ms`, `physics_dt_ms`, `neural_dt_ms`, and
`automatic_retries`). Any mismatch fails closed.

Canonical Windows command (from repository root):

```powershell
python -m malecns_backend.embodiment.proprioceptive_closed_loop_audit --live --duration-ms 100 --seed 1 --json malecns_backend/embodiment/interface_output/proprioceptive_closed_loop_100ms.json
```

No gait, CPG, tripod, scripted coordination, new drive/noise, model, mapping,
gain, or parameter tuning is introduced. Interpret results only as behavior of
the modeled sensory and motor interfaces.
