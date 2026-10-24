# Frozen group-context posture analysis v1 — results

Protocol, analyzer and synthetic tests were committed at `e7f808f` before computing
the new time-aligned peaks and vector interactions, from latest `origin/newBrain`
`feb2f007b2013696dfa41d1c420b7b3c1c4e849e` (merged PR #263). Previously published
scalar outcomes were already known and remain unchanged. See
[the specification](GROUP_POSTURE_ANALYSIS_V1.md).

All analysis integrity checks passed: eight complete finite aligned traces, exact
equality of the four undisturbed controls, pre-force matching through 500 ms and
exact reproduction of the saved response summaries. Full frozen provenance and
upstream evaluations were reverified before reduction. **Zero new CNS or physics
transitions.** No motor admission, physiology, encoder, acceptance or scene change.

## What the timing explains

All peaks below use the fixed cleared-force 520.1..2000.0 ms window. Body tilt is
relative to world upright. Full relative orientation is distance from the moving
undisturbed control and includes heading. Relative body-up angle excludes pure yaw.
These quantities are not interchangeable and their peaks occur at different times.

| Policy | Absolute tilt peak (deg, ms) | Relative orientation peak (deg, ms) | Relative body-up peak (deg, ms) |
|---|---:|---:|---:|
| Full closed loop | 7.323098 at 1998.7 | 12.798550 at 2000.0 | 7.788052 at 774.2 |
| Tibia commands replayed | 9.667409 at 1785.2 | 9.881202 at 911.3 | 7.067780 at 885.5 |
| Complement commands replayed | 14.781105 at 777.6 | 6.094436 at 913.7 | 5.341171 at 911.0 |
| All commands replayed | 9.947980 at 774.1 | 1.447819 at 957.6 | 1.375219 at 958.4 |

At the complementary replay's largest absolute tilt, its body is tilted 14.781105
degrees while the undisturbed control is already tilted 10.512604 degrees; full
orientation error then is 4.288840 degrees. Thus large world tilt can coexist
with a modest error from a leaning control.

At the full closed-loop maximum relative orientation error (2000 ms), body tilt
is 7.306163 degrees and control tilt is 4.115659, while the body-up mismatch is
7.542373 degrees and full orientation error is 12.798550. Heading/twist is included
in full orientation; do not subtract these angles to calculate yaw. Its relative
maximum is the last saved state, so behavior beyond two seconds remains unknown.

Full closed loop retains the lowest observed absolute peak tilt among these four
policies and the largest departure from its undisturbed orientation. This is a
modeled posture-related motor-application effect with tradeoffs, not evidence of
general balance, intent, biological physiology, gait or complete recovery. All
preceding NOT_RECOVERED_IN_WINDOW outcomes, velocity/height/contact tradeoffs and
RF tibia/RF Tarsus1 null command exposures remain unchanged.

## Predeclared vector interaction

The signed interaction is all replay minus tibia replay minus complement replay
plus full closed loop, each a pushed-minus-own-control world vector. Root-vector
interaction peaks at **0.263570 model mm at 911.9 ms**, with xyz
[0.003593, -0.262681, 0.021328] model mm. Its post-force mean norm is 0.125576 model
mm. This exceeds the inherited .005 model-mm engineering resolution and is labeled
RESOLVED_ROOT_VECTOR_NONADDITIVITY. Signed xyz time integrals are
[0.047140, 0.058252, 0.067009] model-mm seconds.

The dimensionless body-up-vector interaction peaks at **0.173875 at 940.8 ms**,
xyz [0.137448, 0.105054, 0.017448], with mean norm 0.067655. This is neither a
rotation angle nor a statistical significance measure. No angular threshold or
single-channel mechanism is assigned. Coupled neural/sensory/mechanical feedback
and compensation prevent treating the groups as independent additive percentages.

The full-resolution plots show every stored point over 0..2000 ms, without
smoothing or selected windows. Yellow marks the 500..520 ms pulse, dotted line
the 520.1 ms analysis start. Labels/units/layout were visually inspected using
both synthetic pre-execution figures and the actual resulting figures.

## Evidence, checks and roadmap

`docs/evidence/group-posture-analysis-v1/analysis.json` preserves source/reference/
artifact hashes, analysis implementation commit and complete outcomes. Numeric
`aligned-traces.npz` contains root position, quaternion, world velocity, up_z and
exact support counts for all eight arms and 20001 states each (no object/pickle
arrays; 16667467 compressed bytes). Original full raw archives remain intact.
`posture.png` and `interaction.png` are standalone scientific figures. Environment:
NumPy 2.0.2 / Matplotlib 3.11.2; no dependency changes.

75 focused tests passed, covering new geometry/timing/interaction math, canonical
inventory, malformed/partial/changed evidence, exclusive outputs, numeric NPZ,
the committed aligned analysis, original compressed/raw hashes and existing
recovery/command contracts. Two old archived simulation/TCP tests were explicitly
excluded from this matrix; their full frozen evaluations were recomputed by the
analysis itself. No claim that new simulations/TCP checks ran here. The separate
legacy tactile-contact suite remains 6 passed / 1 unchanged metadata artifact-hash
failure (a8f8c045... expected, c8fdd337... actual); no hash or artifact was refreshed.
Whitespace checks pass. The earlier full simulator experiment checks are preserved.

Motor admission remains **20/42 model coordinates**, not 48% of biological mapping
or project completion. See [the leg status](LEG_MAPPING_STATUS.md) for group and
sensory coverage. This update returns the roadmap to auditing existing evidence
for the remaining 18 coxa and four middle/hind Tarsus1 coordinates, before a
separate next-admission protocol. No extra motor/sensory interface is enabled.

## Git Bash after merging

No Unity run is needed for this analysis update. From VS Code Git Bash:

```bash
cd ~/Documents/FlyBrainUnity
git switch newBrain
git pull --no-rebase --no-edit
git lfs pull --include="docs/evidence/**"
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
"$PY" -m malecns_backend.live.group_posture_review --report docs/evidence/group-posture-analysis-v1/analysis.json
code docs/evidence/group-posture-analysis-v1/posture.png docs/evidence/group-posture-analysis-v1/interaction.png
```

Expected: VERIFIED, motor admission 20/42, the four frozen tilt/orientation peaks,
root interaction 0.263570 model mm; VS Code opens both charts. Review checks original
raw hashes and recomputes the aligned analysis, without CNS/physics or pose streaming.
The merge-style pull preserves known local unpublished commits and avoids an editor.

Manual test command (expected 75 passed, 2 deselected):

```bash
"$PY" -m pytest -q -p no:cacheprovider tests/test_group_posture_analysis.py tests/test_tactile_recovery.py tests/test_complement_command_dissection.py --deselect=tests/test_tactile_recovery.py::test_archived_recovery_full_analysis_and_actual_pose_tcp --deselect=tests/test_complement_command_dissection.py::test_archived_complement_evidence_and_actual_tcp
```

The new module alone has 21 passing tests. For an optional full recomputation,
use a fresh directory: `"$PY" -m malecns_backend.live.group_posture_analysis
--output-dir group-posture-review-new`. It revalidates all upstream evaluations and
produces fresh equivalent analysis/plots, with zero scientific transitions. Existing
directories are refused; the original published output must not be overwritten.
