# Supported live-v3 contact attribution — 2026-10-24

Baseline: fetched `origin/newBrain` at 5df78a6 (merged PR #257). Protocol and
implementation were committed at 80aba8d **before** the single live experiment.
No scientific parameter, support, collision setting, encoder or legacy source was
changed. The original checkout's local commits, raw reports and replay deletions
remain untouched; this update uses a fresh isolated worktree.

## Actual live experiment

The ordinary `create_live_v3_session` completed 20000 physics transitions and
4000 neural updates over the predeclared two seconds, with 20001 recorded states.
The existing 20-channel motor inventory and six tibia proprioceptive populations
ran through the existing scientific kernel. Tactile delivery stayed disabled.
FlyGym 1.2.1 / MuJoCo 3.2.7 / NumPy 2.0.2 were used without dependency changes.

All six feet pass the specified observational context checks:

| Foot | Exact-support positive states | Clean negative states | Ambiguous direct sources | Force / reconstruction / telemetry disagreements |
|---|---:|---:|---:|---:|
| LF | 19970 | 31 | 0 | 0 / 0 / 0 |
| LM | 19946 | 55 | 0 | 0 / 0 / 0 |
| LH | 19946 | 55 | 0 | 0 / 0 / 0 |
| RF | 19902 | 99 | 0 | 0 / 0 / 0 |
| RM | 19943 | 58 | 0 | 0 / 0 / 0 |
| RH | 19938 | 63 | 0 | 0 / 0 / 0 |

All 333454 solver contact records are retained. The compiled model keeps its 2268
explicit contact pairs. Exact identities, source hashes, support/contact/dynamics
configuration fingerprints and sampled physical state remain valid; observer
state checks match before/after every read, applied forces are zero, and commands
retain zero adhesion. Every saved check is independently recomputed in tests.

Every observed positive for these sensor bodies came from the ordinary `ground`;
there were **no** positive calibration-surface observations. Do not infer that the
calibration surface or unobserved self/other-object contacts are validated in this
context. The predeclared positive criterion was the explicitly identified support
union, not a requirement for positive observations on each individual surface.

This is sampled observational attribution for one initial pose, support, seed and
trajectory. The returned contact-solver caches and force telemetry are read at the
same step boundary; no extra forward call is inserted to recompute contacts from
post-integration qpos. It does not prove continuous inter-sample geometry, causal
tactile effects, biological physiology, balance or gait. The much shorter clean
negative coverage remains visible in the table; no negative samples were selected
or manufactured and no window was shortened. No repeat or outcome-driven revision
of this live protocol was performed.

## Preserved artifacts and implementation checks

`docs/evidence/live-contact-context-v1.json.gz` is the complete gzip JSON trace
(197773063 raw bytes, 52515839 compressed bytes), stored through the repository's
existing Git LFS workflow. `live-contact-context-checkpoint.json` records both
hashes, the pre-experiment implementation commit, environment, counts and complete
evaluation. The archived isolated v2.1 prerequisite is rechecked without changing
its hashes. Previous failed/accepted calibration records remain intact.

An additional **physics-only implementation smoke check**, not scientific live
evidence, compared two fresh normal bodies for ten transitions with held reset
joint commands. Observed/unobserved qpos, qvel and telemetry matched exactly; all
eleven observed states matched reconstructed body forces. Its summary and source
hashes are in `live-contact-context-passivity.json`. No CNS ran in that check.
Unit tests use synthetic cases to test incorrect signs/frames, wrong body/geom
ownership, unexpected direct sources, inactive contacts, missing coverage, applied
forces, incomplete windows, mutation and partial errors.

Validation: 127 tests plus 9 subtests passed across the new attribution suite and
the existing v2/v1 calibration, source locks, readiness, CLI, headless, motor and
pose-transport suites. The archived live test verifies compressed/raw hashes,
unchanged sources and every reported outcome from the full raw trace. Whitespace
checks pass. The actual dry CLI exits 1 with top-level NOT_RUN and no acceptance.
Existing output overwrite protection is unit-tested. Unity was not run.

## Manual Git Bash verification and next step

In a fresh review worktree, preserve canonical LF bytes for historical raw-byte
locks with `git -c core.autocrlf=false worktree add`. Retrieve the archived trace
with the installed Git LFS before tests:

```bash
git lfs pull --include="docs/evidence/live-contact-context-v1.json.gz"
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
"$PY" -m pytest -q tests/test_live_contact_context.py tests/test_six_foot_contact_calibration_v2.py tests/test_six_foot_contact_calibration.py tests/test_tactile_targeted_contact_calibration.py tests/test_live_contact_readiness.py tests/test_live_cli.py tests/test_live_headless.py tests/test_live_motor_diagnostics.py tests/test_live_pose_transport.py
```

Expected: 127 tests plus 9 subtests pass. See LIVE_CONTACT_CONTEXT_V1.md for the dry
command (exit 1), fixed live command (exit 0 only on full acceptance), exclusive
output behavior and prohibition on rerunning unchanged failures to seek a pass.

Next is to **design**, separately version and review a matched tactile-delivery
enabled/withheld experiment in this supported context. It must preserve common,
independent candidate sampling and verify pre-intervention state/input/readout
boundaries. Later physical divergence can be an outcome; unobserved force sources
and contact types still need explicit handling. This update does not implement or
enable that intervention.
