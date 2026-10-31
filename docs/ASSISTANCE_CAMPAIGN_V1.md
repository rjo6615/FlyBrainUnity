# Assistance campaign V1 — eight-arm controller, workers and evaluator

2026-10-31. Engineering implementation of the frozen prospective design in
[ASSISTANCE_CONTRIBUTION_V1.md](ASSISTANCE_CONTRIBUTION_V1.md) and
`docs/evidence/assistance-contribution-v1/protocol.json`. Neither the design,
its protocol, the mechanical adapter nor any frozen auditor/source is changed.
No native qualification or physics/CNS campaign has run under this code yet.

## Entry point and fixed policy

`python -m malecns_backend.live.assistance_campaign`:

- `--check`: static source checkpoint against
  `docs/evidence/assistance-campaign-v1/implementation.json`.
- `--output DIR`: new exclusive folder; complete construction-free original
  prerequisites only (graph, data, environment, authorities, design).
- `--output DIR --live --review-note TEXT`: the ONE campaign. Requires verified
  complete prerequisites and every campaign/adapter/design/frozen source
  committed at HEAD. Fixed order A_NC, A_WC, A_NP, A_WP, R_NC, R_WC, R_NP, R_WP;
  one fresh OS worker per arm; first non-COMPLETE arm or stop ends the campaign.
  No retry, resume, prior-control reuse or fall-based truncation exists.
- `--evaluate DIR`: re-audit saved raw evidence without native/CNS execution.

The complete V1.1 original prerequisite (`balance_source_prerequisites`,
original seven-artifact data, environment, design/authorities, graph_w3 Git
blob) is checked in the controller before AND after the campaign, and in every
worker before initialization AND after acquisition; worker records must equal
the controller's. Workers re-verify controller schema/policy/spec/sources/commit.

## Qualification transfer

Only the first actual A_NC model is qualified (adapter's one shadow MjData,
12 resets/12 forwards, no live forward/reset/integration/CNS). The A_NC worker
always publishes its qualification record separately as
`A_NC.qualification.json.gz`, including failed/partial cases. The controller
re-evaluates that file by hash; a failure stops the campaign with later arms
unstarted. Later workers receive that exact artifact, verify its hash, re-run
the offline qualification evaluator and pass it to the adapter Trial, which
requires the actual initialized model to equal qualified M0 before any step.

## Evaluator

Integrity requires all eight COMPLETE arms with distinct fresh PIDs and:

- Per arm, the original audit mathematics (contact/force reconstruction at
  rtol 1e-10/atol 1e-14, declared push arrays, command/safety replay, CNS and
  per-leg RNG replay) via the frozen helpers. A arms must be ACCEPTED by the
  frozen constant-model `audit_arm`, and its result must equal the piecewise
  audit. R arms use the explicit piecewise guard: configuration identity M0 at
  states 0..5005 and an independently derived MR (only the 22 selected gain/bias
  rows zeroed) at 5006..20000. The frozen auditor still rejects R; it is not
  weakened or bypassed by relabeling.
- Mechanical trace audit of all 20,001 states (existing adapter), recorded MR
  equal to derived MR, mechanical/configuration arrays agreeing, identical
  transferred qualification and qualified M0 in every arm, and mechanical
  samples matching the scientific samples' time/ctrl/applied forces.
- Declared prefixes: all eight equal through state 5000/neural tick 1000 and
  full-run CNS/per-leg RNG; within each push class the four arms' applied
  physical histories and pre-gate neural rows equal through state 5005. A_x/R_x
  complete state-0..5005 and tick-1001 equality is reported as a diagnostic.

Behavior is computed only after integrity is accepted: original per-level
behavior, eight declared pair comparisons (four A vs R, four N vs W) with the
0.25 deg mean AND peak rule, posture/root/velocity/support descriptors, own-
control recovery with `CONTROL_POSTURE_LOSS_CONFOUNDS_RECOVERY` when the no-push
control has rollover, up_z<=0.5, low height or <3 support samples in the cleared
window, and signed root/up-vector contrasts. No arm is selected and no
percentage of balance support is inferred.

Display journals and old-reference comparison (A arms only) are diagnostics;
they never change scientific integrity. A saved-replay entry point for this new
schema is NOT implemented; old replay adapters correctly reject it.

## Limits

Tests use synthetic models/sessions and real child OS processes with a
synthetic adapter; no native FlyGym/MuJoCo model or CNS is constructed. Actual
22-coordinate binding, force qualification, full-model hashing cost on the
moving native model (per-state model identity) and raw size are unmeasured.
All 20 neural position servos still assist. Coverage 20/42, zero admissions;
independent balance and gait remain unproven.
