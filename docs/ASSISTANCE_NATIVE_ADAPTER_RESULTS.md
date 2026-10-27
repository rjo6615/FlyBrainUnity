# Assistance mechanical adapter — engineering results

2026-10-26. Implemented the mechanical component of the existing prospective
eight-arm assistance study. It is not a complete scientific campaign launcher.
No native body/CNS construction, force-law qualification, scientific physics
transition or Unity run was performed in this update. Coverage20/42,0new
admissions; independent balance/gait unproven. All20neural position actuators
remain assisted. Original parameters, acceptance and results are untouched.

Fresh branch from latest origin/newBrain at merged PR293,
fdf60fbf4d53c65834bc773cb306113e3f0dcef6. Isolated worktree preserves the user's
primary local FlyBrainUnity/Assets/Scenes/LiveFly.unity modification.

## Changed files and purpose

- `malecns_backend/live/assistance_native.py`: exact native bindings, typed
  M0/MRrecords, bounded shadow force qualification/restoration, instance-local
  event and mechanical-only trace reconstruction using existing inspectors.
- `malecns_backend/live/assistance_trial.py`: subclass/injected lifecycle adapter,
  protected neural/body-state guards, retained mechanical partials and static
  source-check CLI. Full scientific audit flag stays false.
- `tests/test_assistance_native.py`: synthetic permuted-ID force model, force/
  restoration failures, shadow alias, baseline exposure and all20001trace states.
- `tests/test_assistance_trial.py`: API surface, protected-state serialization,
  original gate-before-event order, factory/partial lifecycle and source-only CLI.
- `docs/ASSISTANCE_NATIVE_ADAPTER_V1.md`: implemented scope and remaining gates.
- `docs/evidence/assistance-native-adapter-v1/implementation.json`: exact new
  engineering source fingerprint checkpoint; explicit incomplete campaign flags.
- `docs/evidence/assistance-native-adapter-v1/engineering-checks.json`: actual
  automated/manual check receipt, separate from scientific results.
- `.gitattributes`: exact new JSON evidence bytes.
- `docs/PROJECT_HANDOFF.md`, `docs/UNITY_AND_BALANCE_ROADMAP.md`: current progress
  and complete-evaluator/controller gate before native execution.
- This results file: delivery inventory, actual checks, manual commands and limits.

## Actual checks and limitations

Validated desktop interpreter:fly-brain-interactive/.venv/Scripts/python.exe;
no dependency changes. Final check **75 passed in14.89s**:

```text
pytest -q -x -p no:cacheprovider
  tests/test_assistance_native.py
  tests/test_assistance_trial.py
  tests/test_assistance_contribution_plan.py
  tests/test_controlled_live_balance.py::test_original_spec_and_sources_remain_valid
  tests/test_controlled_live_balance.py::test_driver_full_budget_no_client_original_factory_unchanged
  tests/test_controlled_live_balance.py::test_stop_retains_partial_and_does_not_take_next_transition
  tests/test_controlled_live_balance.py::test_stop_before_init_has_no_socket_or_native_construction
  tests/test_controlled_live_balance.py::test_detach_error_cannot_discard_raw_partial_or_display_journal
  --tb=short
```

These are synthetic model/session and static tests; the unchanged no-client
observer regression uses an actual local socket. Test counts are not native
physics/CNS counts. API-surface tests inspect the installed MuJoCo class/functions
without constructing model/data. Source-check tests forbid native/CNS/loader
construction. Earlier development run had31fixture setup errors from a missing
synthetic actuator_group table; fixed the fixture. Intermediate31then65checks
passed before final additions. No actual native attempt was retried.

Saved implementation checkpoint once with exclusive output. Actual Windows
Git Bash `assistance_trial --check` passed exit0. This verifies the new source
checkpoint and old prospective design, not original full runtime prerequisites
or actual moving-model performance. Source flags explicitly say qualification/
campaign not executed, evaluator/controller not implemented.
`git diff --cached --check` passed across all11changed files.

Mechanical force reconstruction cannot substitute for command/RNG/contact/
behavior audits. Old constant-model scientific evaluators still reject R and
remain frozen. Complete eight-arm evaluator and fresh-process controller/workers,
full original source/data/environment guards, durable artifact/stop paths and
qualification transfer are required before native use. Native full-model hashing
cost is unmeasured. No native guarantee follows from synthetic force fixtures.
The internal run_arm Python function is not a standalone experimental entry point.

## Windows Git Bash after merge

This engineering check needs neither Unity Play nor LFS hydration:

```bash
cd "$HOME/Documents/FlyBrainUnity" &&
git switch newBrain &&
git pull --no-rebase --no-edit &&
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" &&
"$PY" -m pytest -q -p no:cacheprovider \
  tests/test_assistance_native.py \
  tests/test_assistance_trial.py \
  tests/test_assistance_contribution_plan.py &&
"$PY" -m malecns_backend.live.assistance_trial --check
```

Expected:70tests pass, then `ASSISTANCE ADAPTER SOURCE CHECK VERIFIED` with
explicit pending campaign/evaluator and no native qualification or physics/CNS.
No new Unity motion is expected. Do not launch the internal adapter manually.
Next integrate/test/commit full campaign gates, then the one predeclared native
qualification and eight fresh arms, preserving any failure/null/adverse outcome.
