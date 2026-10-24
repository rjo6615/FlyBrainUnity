# Remaining leg motor-admission evidence — results

Audit branch baseline: latest `origin/newBrain` at
`d747f8007959b961e648d9cc92afd50ea4a9e587` (merged PR #264). The initial v1 rules,
auditor and tests were committed at `0128b86`. Its failed output is preserved;
the alias correction/specification/tests were committed at `2996dcc` before the
new exclusive v1.1 result. No scientific assay or admission experiment ran.

**All 22 remaining coordinates were inspected. None is ready for direct motor
admission from the checked-in evidence alone. Current admission remains 20/42.**

| Remaining group | Coordinates | Evidence found | Required next evidence |
|---|---:|---|---|
| Coxa / Coxa_roll | 12 | Exact candidate neuron identities, but shared populations/physical-axis assignments | Population-to-muscle binding and justified multi-axis action/sign/decoder semantics |
| Coxa_yaw | 6 | Unique directional candidates; historical mechanical rotations recorded | Anatomical activation/action-to-coordinate sign bridge; current-context admission prerequisites |
| Middle/hind Tarsus1 | 4 | No exact current tarsus_T2/T3 population mapping | Exact target populations, not neighboring Tarsus2 or mirrored front-leg pools |

The complete [22-row matrix](evidence/remaining-leg-admission-audit-v1_1/matrix.md)
and [JSON](evidence/remaining-leg-admission-audit-v1_1/audit.json) retain every exact
action index, candidate population/body ID/dense index, current admission reason,
annotation alias, mapping ambiguity, historical geometric/null record and blocker.
Every resolved candidate was checked against the current decoded neurons.flyn
index, interface_map and bodymap. This loads data, not a neural runtime or graph
simulation. Current admission is rebuilt through the existing validated data-only
v3 factory; no flags, coordinate signs, gains or neural parameters are changed.

## Findings that prevent unsupported shortcuts

The six Coxa_yaw anatomical bridge records all retain the original
ANATOMICAL_SIGN_GEOMETRICALLY_UNRESOLVED classification: positive and negative
anterior projections are both zero, and no anterior coordinate sign was assigned.
The existing classifier was replayed on the saved evidence without changing its
metric/tolerances. Recorded mechanical rotation is not an anatomical activation
sign. No frozen geometry experiment was rerun or reinterpreted for a pass.

All four missing Tarsus1 targets remain absent in the current exact body-map
actuator labels. Tarsus2 annotations do exist in middle/hind legs, often also
associated with adhesion. They are retained as related non-candidates, not
silently reassigned to Tarsus1. Front populations are not mirrored to other legs.

Later LF reference evidence contains a local three-axis registration and seven
tendon covectors, all reproducing the recorded inverse-transpose transformation
within 1e-12 (maximum observed error 6.94e-18). It is LF-only at documented reference
configurations, not a finite-angle/pose-independent population mapping, a decoder
weight or an admission. Its own explicit limitations are retained.

| LF reference candidate | Body IDs | Count |
|---|---|---:|
| Tergopleural/Pleural promotor | 800061, 801173, 807281, 934091 | 4 |
| Pleural remotor/abductor | 802509, 803803 | 2 |
| Sternal adductor | 813480 | 1 |
| Sternal anterior rotator | 806923, 919509 | 2 |
| Sternal posterior rotator | 801915, 804851, 808640, 1050335829 | 4 |

All five recorded recruitment decisions were NOT_RECRUITED_UNDER_TEST_CONDITION
for LF_MIN_BOUND/LF_MAX_BOUND in seeds 1/2/3, with recorded event crosschecks true.
These are stored null summaries in an older 11-motor sensory-replay context,
not a new per-spike replay audit or proof of inevitable silence in current
20-motor tactile conditions. Activity is not used to rank admission candidates.

## Preserved implementation failure and raw-lock limitations

v1 stopped with `duplicate exact population names`; its 206-byte error report
remains in `docs/evidence/remaining-leg-admission-audit-v1/audit.json`. The global
name-uniqueness assumption was incorrect. For example, the same exact remotor/
abductor neurons carry both coxa and coxa_abduct annotations. v1.1 independently
validates every selected alias has the same complete unique neuron identity/count/
direction and an exhaustive matching bodymap metadata record, retaining all target
aliases. Different-identity or missing/extra aliases fail. No last-record-wins
selection or population union. See [the correction](REMAINING_LEG_ADMISSION_AUDIT_V1_1.md).

Three historical raw freeze checks fail in this fresh Windows checkout because
CRLF representation differs from frozen raw bytes. The corresponding canonical LF
bytes match both the unchanged expected hashes and the original Git blobs. Both
facts are reported separately: **all_original_raw_freezes_satisfied is false**.
No original artifact, expected hash or raw-byte verifier was modified; canonical
content correspondence is not an original prerequisite pass. Before future
scientific execution, satisfy those original prerequisites separately. The audit's
integrity success describes accurate evidence inspection, not admission readiness.

The review command allows only canonical source-content equivalence across
checkouts and prints recorded/current original raw-lock results separately. It
never relabels a raw failure as a pass. Main mapping/sign prerequisites remain
unsatisfied even if an LF checkout satisfies the old raw bytes.

## Next admission workstream

Start with the **LF proximal reference-binding/sign prerequisites**, because it
has the existing multi-axis reference foundation. Resolve population-to-muscle
activation semantics and preserve the broad promotor's three distinct tendon
hypotheses; do not choose or average a favorable tendon/axis. Then write the
separate bounded validation/admission protocol with independently justified
numeric/application criteria and current-context pairing. No new sign, decoder
vector or gain is assigned here. See
[the concrete prerequisite plan](LF_PROXIMAL_ADMISSION_PREREQUISITES_V1.md).

This is progress on knowing exactly what blocks the remaining coordinates; it
does not increase the admitted count. No direct live enablement, neural tuning,
activity threshold adjustment, repeated assay until activity, balancing/gait
controller or biological function claim is justified by this audit.

## Actual checks

New audit tests and relevant current-v3/v2/coxa-contract matrix: **55 passed,
5 failed in 153.79 s**. The five failures also reproduce on the unchanged primary
checkout without the new auditor (5 failed in 0.29 s); old code/tests/artifact have
no diff from the baseline. They are retained, not bypassed:

- M6B history test expects NOT_RUN in an artifact whose frozen state is COMPLETE.
- Two anatomical-bridge tests and one mechanical-sign test call preflight in
  occupied frozen output namespaces, correctly receiving overwrite refusal.
- One CRLF fixture converts already-CRLF input again and violates the frozen hash.

The 15 new audit tests pass within that matrix, including full saved-matrix
recomputation, exact identity/alias rejection, provenance reporting, non-admission,
exclusive output and no-execute CLI. Actual v1.1 audit and exact user-facing review
CLI both passed. All original raw-lock failures remain visible. Whitespace checks
pass. No brain construction, neural/physics transition, Unity Editor run, dependency
change, older-result rewrite or new motor admission occurred in the auditor.

## Git Bash after merging

No Unity run is needed. In VS Code Git Bash:

```bash
cd ~/Documents/FlyBrainUnity
git switch newBrain
git pull --no-rebase --no-edit
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
"$PY" -m malecns_backend.embodiment.remaining_leg_admission_review --report docs/evidence/remaining-leg-admission-audit-v1_1/audit.json
code docs/evidence/remaining-leg-admission-audit-v1_1/matrix.md docs/LF_PROXIMAL_ADMISSION_PREREQUISITES_V1.md
```

Expected: AUDIT VERIFIED, current 20/42, 22 remaining, zero admissions/transitions;
blocker counts 12 shared-axis / 6 sign bridge / 4 exact-target mapping. Historical
raw-lock false is explicitly reported in CRLF checkouts and is not admission
approval. VS Code opens the complete matrix and next prerequisite plan.

Manual new tests (expected 15 passed):

```bash
"$PY" -m pytest -q -p no:cacheprovider tests/test_remaining_leg_admission_audit.py
```

Full relevant matrix (expected recorded baseline 55 passed / 5 failed in this
checkout; see reasons above):

```bash
"$PY" -m pytest -q -p no:cacheprovider tests/test_remaining_leg_admission_audit.py tests/test_live_v3_motor_interface.py tests/test_live_v2_motor_interface.py tests/test_m6b_coxa_yaw_sign_diagnostic.py tests/test_coxa_yaw_anatomical_sign_bridge.py tests/test_coxa_yaw_sign_validation.py
```

Optional fresh read-only generation uses a new directory:
`"$PY" -m malecns_backend.embodiment.remaining_leg_admission_audit --output-dir
remaining-leg-audit-review-new`. Existing output is refused; both historical v1
and published v1.1 outputs remain preserved.
