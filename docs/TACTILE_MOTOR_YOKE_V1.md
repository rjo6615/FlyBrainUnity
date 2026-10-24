# Tactile motor-command yoke v1

Prospective specification, 2026-10-24, before new scientific execution. Test
whether disturbance-contingent motor-command changes contribute to the observed
continued-tactile disturbance response. Preserve the adverse recovery-v1 result.

## Conditions and estimand

Run exactly two fresh conditions in order Y_C, Y_P. Each uses seed 1, two seconds,
20000 physics transitions, 4000 neural updates and 20001 saved observations.
Both keep tactile enabled, all 20 admitted motors, the common 2269-slot CNS RNG
schedule, unchanged encoder/physiology/decoder/support/collisions and existing
scientific kernel. CNS, sensory encoding and motor decoding continue normally.

Immediately before every physical transition, replace the proposed 42-coordinate
joint action with the exact action from that transition of archived matched-pair
ENABLED (ON_C). Sample n+1 records the action applied during outgoing transition n.
Do not substitute measured joint angles, ctrl, interpolated commands, zero motor
drive or held initial posture. Use the recorded commanded_joints field exactly.
Require finite 42-vectors, zero six-element adhesion and verified complete source
archive. Record both proposed and applied actions. Explicitly use the entire
undisturbed command schedule, including its previously recorded future values:
this is a causal open-loop engineering intervention, not an online controller.

Y_C has no push and must reproduce ON_C exactly throughout: initial state, model
identity, all physical/contact/encoder observations, neural records, RNG schedule
and proposed/applied commands. This fresh arm tests transport/timing fidelity,
not a new independent baseline replicate. Any discrepancy rejects integrity.
Compare contact names after stripping only generated namespace prefixes, with
full exact IDs/ownership independently validated in each arm; compare every other
contact field exactly. Generated instance names are not physical differences.

Y_P receives the unchanged recovery-v1 pulse: world [0,1.024,0] at exact Thorax
COM, zero torque, outgoing transitions 5000..5199. Reuse the existing force
callback and full exact sparse-wrench audit. Require exact Y_C/Y_P physical and
neural matching through 500 ms, common full-window RNG uniforms, full applied
command equality to ON_C, intact readout and all non-force contact checks.
Post-push CNS/proposed commands may diverge legitimately while applied commands
remain yoked. Report the first proposed/applied difference and altered-transition
count. No exposure means limited interpretation, not a reason to rerun.

Reuse only fully hash/source/evaluation-verified recovery-v1 ON_P/ON_C closed-loop
traces. Compare Y_P minus Y_C with ON_P minus ON_C using unchanged recovery-v1
metrics, world angular-velocity conversion, resolution and sustained-return bands.
For peak AND mean orientation, label YOKING_REDUCES_RESPONSE if both yoked-minus-
closed differences are below -0.25 deg, YOKING_INCREASES_RESPONSE if both exceed
+0.25 deg, otherwise MIXED_OR_UNRESOLVED. Report height, velocities, support,
rollover, absolute tilt and recovery independently. Integrity never requires a
favorable outcome. This tests aggregate disturbance-contingent motor-command
application, not individual channels, biological intent or balance/gait proof.
Baseline time-varying actuation and passive mechanics remain present in Y_P.

## Evidence and integrity

Commit protocol and implementation before execution. Record all fresh raw
samples/neural records, proposed/applied actions, actual wrench evidence, source
locks, environment and pre-execution commit; gzip JSON with raw/compressed hashes.
Reserve output directory exclusively, preserve partial/error/nonfinite records,
stop after interruption, no retries or force/seed/threshold tuning. Historical
sources and evidence remain unchanged. Reuse recovery's full contact/delivery
audit; its original source-list check is retained and explicitly superseded by
the stronger new-source-set equality check, since the new runner adds sources.
No other requirement is removed. The old no-force rejection remains visible in
pushed arms and is replaced only by the existing exact planned-force audit.

Ordinary live tactile mode remains off. No Unity scene/controller changes.
One modeled pulse/window/seed cannot establish biological stabilization or
passive-versus-active baseline support. Report null, adverse and rejected results.

## Git Bash

```bash
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
"$PY" -m pytest -q tests/test_tactile_motor_yoke.py
"$PY" -m malecns_backend.live.tactile_motor_yoke --output-dir motor-yoke-dry
echo $? # 1 / NOT_RUN; directory must be new
"$PY" -m malecns_backend.live.tactile_motor_yoke --live --output-dir docs/evidence/tactile-motor-yoke-v1
```

The live command is the single prospective pair or an explicitly planned
independent replication, never repeated attempts to obtain a favorable response.
