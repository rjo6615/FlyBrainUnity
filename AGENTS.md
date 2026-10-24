# FlyBrainUnity agent instructions

Read `docs/PROJECT_HANDOFF.md` before continuing project work. It records the
current evidence, unresolved questions and immediate next task. Verify the live
repository and PR state; a handoff is a dated checkpoint, not a substitute for
inspection. Consult any more specific instructions in the directories you edit.

## Goal and scientific constraints

The goal is connectome-driven, neurally emergent body/environment interaction,
progressing toward 42 motor coordinates, richer senses, balance and eventually
walking. Do not substitute scripted gait, direct sensory-to-actuator rules or
behavior machinery for neural emergence.

- Distinguish anatomical evidence, measured simulation observations, modeled
  transduction/physiology, engineering interventions and biological claims.
- Do not change thresholds, per-joint gains, weights, mappings, drive or seeds
  merely to produce motor activity. A demonstrated implementation defect may
  be corrected with reference evidence and appropriate tests; do not present
  reference fidelity as biological validation or guaranteed behavioral benefit.
- Specify experimental conditions and acceptance criteria before inspecting
  outcomes. Preserve null, failed, partial and inconclusive results. Never
  shorten/select a window, drop contaminated samples, retry, or tune an
  intervention until it passes without explicitly versioning the new protocol
  and explaining the scientific question. Do not overwrite historical evidence.
- Reuse existing validated encoders, kernels, mapping authorities and observers.
  Search before adding a competing implementation. Resolve body IDs and dense
  indices exactly; names or structural paths alone do not establish function.
- Preserve source/artifact locks. Do not refresh a hash to hide a scientific
  change or bypass a failed prerequisite. Add separately versioned evidence
  where needed and state the limits of its context.
- Passive observations do not prove causal effects, independent balance or gait.
  Matched interventions require the appropriate baseline and measured integrity
  checks; physical divergence after neural intervention can be an outcome.

## Branches and delivery

- Start each update on a fresh branch from the latest `origin/newBrain`.
  `newBrain`, not `main`, is the baseline and PR target.
- Protect unrelated local edits. Use an isolated worktree when appropriate;
  do not reset, clean, overwrite or commit the user's unrelated files/results.
- Make focused changes, run relevant checks, then open a PR targeting `newBrain`.
  Leave merging to the user unless explicitly instructed otherwise.
- Every PR/final delivery must list changed files, purpose, automated checks and
  their actual results, manual commands and expected outcomes, and material
  limitations. Distinguish executed physics/CNS experiments from mocked tests.
- Provide user commands for Windows Git Bash. Use the existing validated Python
  environment where available; do not assume bare `python` points to it.
- If permissions, missing tools or dependencies prevent a check/PR, report that
  directly. Never claim it ran or silently replace the requested experiment.

## Local execution

The main Python runtime is `malecns_backend`; the Unity project is
`FlyBrainUnity/`. `fly-brain-main` contains the checked-in JS reference model;
`fly-brain-interactive` contains earlier embodiment code and may contain the
user's validated Windows virtual environment. Inspect actual paths before use.

Use small unit/reference tests for implementation checks. Full FlyGym/MuJoCo
experiments and CNS initialization may be slow. Keep output and raw evidence,
report progress, and do not run duplicate expensive simulations without a reason.
Do not add dependencies or change the validated physics environment incidentally.
