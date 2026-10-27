# Assistance-contribution design checkpoint — 2026-10-26

The next experiment is specified, not implemented or run. Eight fresh arms will
cross22baseline-only position servos held/neutralized,20neural inputs continued/
withdrawn and fixed push/no-push. The20neural position actuators stay intact;
this tests partial assistance contribution, not completely unassisted balance.
Existing motor coverage20/42, zero new admissions. No neural/physics parameter,
threshold, source lock, old acceptance or historical evidence was changed.

PR292 merged at3baaaa7afea3e24c716723ca633dfda0d45ee626. This update uses a fresh
branch from that origin/newBrain. User reports the new V1.1 recorded movement
looks normal, no unexpected issues, similar to earlier runs. Saved human review
is confirmed; acquisition's zero sent frames still preclude live-delivery claims.
The primary checkout's local LiveFly.unity edit is untouched.

## Changed files and purpose

- `docs/ASSISTANCE_CONTRIBUTION_V1.md`: prospective interventions, exact boundary,
  native binding/force qualification, integrity, outcomes, limitations and budget.
- `malecns_backend/live/assistance_contribution_plan.py`: pure static plan builder/
  read-only verifier; exclusive new output, original reference locks and fingerprints.
- `tests/test_assistance_contribution_plan.py`: partitions, all arm phases, malformed/
  altered plans, overwrite refusal and no-native/no-CNS construction boundary.
- `docs/evidence/assistance-contribution-v1/protocol.json`: saved prospective plan;
  native IDs remain null and implementation/qualification/execution flags false.
- `docs/evidence/assistance-contribution-v1/design-checks.json`: actual static-check
  receipt and user-reported recorded observation, distinct from measured science.
- `.gitattributes`: preserve exact bytes of new evidence JSON.
- `docs/PROJECT_HANDOFF.md`, `docs/UNITY_AND_BALANCE_ROADMAP.md`: latest status,
  confirmed recorded review and immediate implementation gate.
- This results document: checks, commands and limits.

## Actual checks

Validated desktop Python3.12 environment, unchanged dependencies:
`fly-brain-interactive/.venv/Scripts/python.exe`.

- `pytest -q -p no:cacheprovider tests/test_assistance_contribution_plan.py
  --tb=short`: **26 passed in0.88s**. Static/unit tests; fresh subprocess forbids
  FlyGym/MuJoCo/dm_control imports, CNS construction and loader calls.
- Emitted prospective protocol once using exclusive `--output`; succeeded.
- Verified saved protocol with actual Windows Git Bash and the validated Python
  path; exit0, `STATIC DESIGN VERIFIED`. No scientific execution in these checks.
- `git diff --cached --check`: passed, no whitespace errors in the nine-file diff.

The prior accepted report is read under its original raw SHA; this is NOT a
re-evaluation of all prior native data, nor verification of future execution
prerequisites. No new physics transitions, CNS updates, native qualification,
runtime actuator binding or Unity poses. Planned160,000physics/32,000neural are
future budget, not executed totals. Existing3-coordinate LF isolation evidence
does not establish the proposed22-coordinate intervention during motion.

## Windows Git Bash after merge

Stop an old replay if it is still looping, then run this static check from the
main checkout. No LFS pull or Unity Play is required for this design check.

```bash
cd "$HOME/Documents/FlyBrainUnity" &&
git switch newBrain &&
git pull --no-rebase --no-edit &&
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" &&
"$PY" -m pytest -q -p no:cacheprovider tests/test_assistance_contribution_plan.py &&
"$PY" -m malecns_backend.live.assistance_contribution_plan \
  --verify docs/evidence/assistance-contribution-v1/protocol.json
```

Expected:26tests pass, then `STATIC DESIGN VERIFIED` with eight PLANNED arms and
explicit no native/CNS experiment. Unity will not show new motion from this check.
Do not use `--output` to replace the committed plan.

Next implement/test the versioned adapter and phase-aware evaluator, commit them,
then perform ONE predeclared qualification/campaign with full source guards and
all eight fresh arms. Retain failed/null/adverse results without retry or tuning.
The ongoing milestone is measuring mechanical support versus neural contribution;
independent balance and walking remain unestablished.
