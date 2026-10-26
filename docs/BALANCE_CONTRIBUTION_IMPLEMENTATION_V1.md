# Balance-contribution V1 implementation checkpoint

2026-10-26. **IMPLEMENTED_SYNTHETIC_CHECKS_PASS_NATIVE_NOT_RUN**.
The original [prospective protocol](BALANCE_CONTRIBUTION_V1.md) and its JSON
remain unchanged historical design records. The execution schema is separately
`balance-contribution-execution-v1`; no scientific outcome is claimed here.

The new `malecns_backend/live/balance_contribution.py` implements an isolated
ScientificSession adapter, recorder, fixed four-arm runner, saved-evidence
evaluator and CLI. Ordinary live and Unity defaults, the frozen kernel, encoders,
motor mappings, neural parameters, actuator gains and safety code are unchanged.
Coverage remains **20/42**, new admissions **0**, LF target correspondence **0/8**.
Independent balance and walking remain unestablished.

## Implementation

- Fresh NC/WC/NP/WP instances, seed 1, 20,000 physics transitions and 4,000 neural
  updates per arm. Integer scheduling preserves the initial state, force-on
  outgoing 5000..5199 and terminal update 4000 as retained/unapplied.
- Uses the original M9B force function, 392-slot CNS schedule, six original
  proprioceptive encoders and samplers, current v3 motor authority and unchanged
  MatchedControlPipeline. Withdrawal is at tick 1001 before safety. No final
  contribution gate, safety-history reset, target hard zero or custom ramp.
- Reuses the construction-free static authority reader. No legacy live inventory
  model is constructed as a prerequisite. Frozen M5A IDs are leads only: the
  reused native inventory resolver and validator check the actual experimental
  model and all recorded IDs/addresses before kernel channel construction.
- Records exact native model/contact/sensor/actuator tables, free-root addresses,
  full applied wrench/generalized-force arrays, native ctrl, proposals versus
  actual outgoing commands, safety replay, raw/gated decoder inputs, motor
  readouts, neural state digests, sensory rates/events and RNG streams.
- Checks original graph/neuron/calibration files against the design baseline's
  Git bytes or original LFS OIDs. Six data artifacts use exact raw bytes;
  brain_params.json uses canonical LF source correspondence, with both actual
  and original raw hashes retained. This text check does not waive a binary or
  historical scientific raw lock. Loaded body-ID order, CSR, weights, delay and
  full ModelConfig are recorded and matched across arms.
- Separately records observed initialization constructor/reset/forward/native
  entries and CNS load/init/reset entries. This is Python/C API entry accounting;
  native internals invisible to the profiler are not counted or claimed absent.
  Initialization precedes the scientific state-zero boundary. No settling calls
  are removed, and zero time alone never establishes zero constructor work.
- Independently replays every safety update and both RNG schedules, checks all-arm
  and same-push prefixes, all force arrays, exact 20/22 isolation, full clocks and
  terminal ownership. Counterfactual exposure and actual between-arm outgoing
  command differences are separate. Contact reconstruction uses the existing
  observer; ordinary ground support counts use the existing recovery helper.
  Calibration-surface and unexpected distal contacts remain visible limitations,
  never deleted samples or implicit ordinary-ground support.
- Reuses the original recovery bands and resolution, preserving NO_BAND_EXIT,
  unrecovered and sustained-return results. Reports whole cleared-window pushed
  world tilt peak/mean/RMS, no-push posture, relative recovery/height/speed/support
  measures and full signed factorial root/up vectors. Integrity and behavior are
  separate; a complete null can be replay-eligible without proving balance.
- Exclusive output directories and files prevent replacement. Arm captures are
  saved before the next arm starts. Errors/interruptions preserve partial data,
  close the session and stop without retries; unstarted arms remain absent and
  cannot satisfy coverage. The existing lossless nonfinite serializer preserves
  failed NaN/infinity values as explicit markers. Saved arm hashes are checked.

The runner refuses scientific execution unless all environment/source/raw
prerequisites pass and its implementation matches a committed Git blob. There
are no duration, force, seed, window or retry switches.

## Actual checks and failures

New engineering checks: **23 passed**, including a complete synthetic 80,004-state
four-arm null, fixed-budget command replay, raw withdrawal versus slew, actual
5005/5006 boundary, terminal proposal ownership, real 392-slot sampling on a small
400-neuron fixture, candidate/CNS replay corruption rejection, world-frame and
factorial math, native-construction import guards, factory settings, partial
interruption preservation, exclusive writes and raw-artifact tamper rejection.
The synthetic fixture is manufactured evidence for the evaluator, not a FlyGym
simulation, anatomical finding or neural-balance result.

Existing neural runtime checks: **13 passed**, including JS reference parity.
These use synthetic networks, including the existing CNS-sized shape fixture;
they do not initialize the actual connectome experiment. The first sandbox run
had 12 passes/1 Node filesystem-permission error; an elevated rerun passed all 13.
The first new-test development run had 16 passes/3 errors: importing a nonfinite
helper unnecessarily imported SciPy. Reusing the existing construction-free
lossless serializer corrected that dependency boundary. Subsequent 19-, 20- and
23-test runs passed as implementation checks were added. None was a physics run.

The legacy desktop venv launcher points at missing Python 3.10.11 under
`C:/Users/legen/AppData/Local/Programs/Python/Python310`. The bundled test runtime
is Python 3.12.14 / NumPy 2.3.5, with no FlyGym, MuJoCo, dm_control, pyarrow or
pytest. It is suitable for the executed unittest checks but fails the protocol's
validated runtime requirement (NumPy 2.0.2, FlyGym 1.2.1, MuJoCo 3.2.7,
dm_control 1.0.27). No dependencies were installed or upgraded.

An initial read-only prerequisite inspection encountered an unhydrated M6C LFS
pointer. Original cached M6C, annotation and contact-context bytes were hydrated
only in the isolated worktree (3 objects, 252 MB); hashes/locks were not refreshed.
The next static authority check reached missing pyarrow. This does not establish
that later authorities pass. Final native/runtime prerequisites remain unverified.
Seven original neural/calibration source identities passed their recorded modes.

The preserved [first static report](evidence/balance-contribution-implementation-v1/preflight-01/report.json)
records the earlier implementation's missing packages/pyarrow and zero scientific,
native and CNS initialization counts. Later implementation changes are not
retroactively attributed to that report. The final separately saved refusal
report will record the final code fingerprint and original-neural-data check.
No original failed evidence is overwritten.

**No actual FlyGym/MuJoCo body, connectome initialization, four-arm experiment,
accepted Unity replay or new biological result was produced.** Real factory,
native instrumentation and recorder behavior remain to be validated in the
declared environment. Synthetic coverage is not native runtime readiness.

## Changed files and purposes

- `malecns_backend/live/balance_contribution.py`: adapter, recorder, runner,
  static preflight, evidence persistence and evaluator.
- `tests/test_balance_contribution.py`: synthetic engineering checks above.
- `.gitattributes`: exact new report bytes and future raw-arm LFS namespace.
- This document: implementation, actual checks, failures, limits and commands.
- `PROJECT_HANDOFF.md`, `UNITY_AND_BALANCE_ROADMAP.md`: current continuation,
  unchanged coverage and next gate.
- `evidence/balance-contribution-implementation-v1/`: exclusive prerequisite
  reports; these are static/refusal evidence, not experimental arms.

## Windows Git Bash commands

After the user merges the PR, pull without overwriting unrelated edits:

```bash
cd ~/Documents/FlyBrainUnity &&
git switch newBrain &&
git pull --no-rebase --no-edit
```

Use an actually working validated Python 3.12 interpreter. The former
`fly-brain-interactive/.venv/Scripts/python.exe` path is broken on this machine;
do not silently recreate it or substitute bare python. Set `PY` to the restored
validated interpreter's absolute path before these commands. For example, only
after that environment has been restored at the old location:

```bash
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
"$PY" -m unittest discover -s tests -p test_balance_contribution.py -v
"$PY" -m unittest discover -s tests -p test_neural_runtime.py -v
```

Expected: 23 new checks and 13 existing checks pass. Node must be available for
the existing JS parity check. These are engineering/reference checks only.

Run static preflight into a new directory:

```bash
"$PY" -m malecns_backend.live.balance_contribution \
  --output "docs/evidence/balance-contribution-execution-v1/preflight-$(date +%Y%m%d-%H%M%S)"
```

Expected on this machine today: nonzero exit and verified=false, with missing
dependencies reported; no native/CNS construction. On the validated environment,
all original prerequisites must pass, including actual hydrated LFS evidence.
Follow the existing guarded repair documentation if a historical raw lock fails;
do not update expected hashes. A successful preflight is still not a fly result.

Only after all checks pass and implementation is committed, execute the one
fixed four-arm protocol in its own exclusive namespace:

```bash
RUN="docs/evidence/balance-contribution-execution-v1/run-$(date +%Y%m%d-%H%M%S)"
"$PY" -m malecns_backend.live.balance_contribution --live --output "$RUN"
"$PY" -m malecns_backend.live.balance_contribution --evaluate "$RUN"
```

Expected if complete and intact: NC/WC/NP/WP raw gzip files and report.json,
80,000 physics transitions, 16,000 neural updates, INTEGRITY_ACCEPTED and a
separate descriptive outcome, which may be null/negative/unrecovered. A refusal,
interruption, nonfinite or mismatch yields nonzero exit/INCONCLUSIVE_INTEGRITY;
preserve its namespace and diagnose it without automatic retry or tuning.
Do not use another timestamp to repeat a scientific attempt without a separately
explained/versioned question. Pose review in Unity follows valid evidence using
the existing transport; this PR adds no Unity mode.

Next concrete gate: restore/access the validated environment, finish original
static prerequisites, then validate the real session within the single fixed
execution. Independent anatomy remains separate; do not resume anatomical
observer campaigns as a substitute for the selected balance workstream.
