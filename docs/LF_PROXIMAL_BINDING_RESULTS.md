# LF proximal reference-binding results

2026-10-25. Protocol/code/tests committed at aeb4824 before generating the new
report. Fresh branch from origin/newBrain e5964d0, merged PR #265. This is static
source/reference inspection and algebraic verification: **zero new CNS or physics
transitions, zero newly admitted channels; current live-v3 remains 20/42**.

## What was resolved

The original local FlyMimic `best_combined_cvt3.xml` matches the exact raw SHA256
in the frozen registration. Its seven LF proximal tendon actuators inherit muscle
activation, gain and bias semantics, use nonnegative control ranges, positive
specified peak forces and unit tendon gear. The new report preserves all seven
actuator attribute records, their tendon sites and the muscle default. It does
not compile XML, load meshes, simulate muscle forces or use FlyMimic's MuJoCo
version in the validated FlyGym environment.

The reference force convention is now explicit: for R = -dL/dq and tensile
magnitude T >= 0, generalized torque is tau = T*R. The sign of MuJoCo's scalar
pulling force is already accounted for; flipping R again would reverse the
conditional torque. Virtual-work tests check this identity and its preservation
under the existing local inverse-transpose transform. Synthetic tensions and
displacements in these tests are test data, not chosen physiological parameters.
See the primary references and access limits in `LF_PROXIMAL_BINDING_REVIEW_V1.md`.

Component signs below apply only to positive tension at the registered reference
configuration, in basis [Coxa_yaw, Coxa, Coxa_roll]. They are **not neuron-to-angle
signs**, measured accelerations, position targets, anatomical direction labels or
decoder weights.

| Existing tendon hypothesis | Conditional tensile torque signs |
|---|---|
| Pleural promotor | [-, -, -] |
| Tergopleural promotor a | [-, -, +] |
| Tergopleural promotor b | [-, -, +] |
| Pleural remotor/abductor | [+, +, -] |
| Sternal adductor | [-, +, -] |
| Sternal anterior rotator | [-, -, +] |
| Sternal posterior rotator | [-, +, +] |

This illustrates why selecting an annotation sign or one dominant axis would lose
information. The broad promotor alternatives even differ in roll sign. None was
averaged, selected or fitted. No new outcome metric reinterprets the old frozen
zero-projection yaw results.

## What remains blocked

The existing independent anatomical class descriptions do not establish which of
the broad promotor's four repository body IDs belongs to each modeled tendon.
All five population identities (13 neurons total, including both remotor aliases)
were reverified through the complete existing admission reviewer. Each neuron has
an explicit null tendon assignment. Four classes have one current tendon
hypothesis each; that cardinality is not independent anatomical confirmation.

Spike-to-activation, activation-to-force and force-to-position-target transfers
remain unassigned, as do proximal decoder vectors and gains. The current shared
kernel applies joint-position commands, whereas this external reference describes
muscle force. Geometric covectors cannot supply that missing transfer. Existing
MotorDecoder's modeled 17-Hz activation scale remains unchanged and is not treated
as a measured proximal muscle law. No model gains, signs, thresholds, seeds,
weights, drive, ordinary tactile default or current admission flags changed.

The next concrete evidence requirement is an independently traceable neuron-to-
muscle/tendon crosswalk and an explicit interface choice: a modeled muscle-force
interface, or a separately justified engineered approximation to joint-position
targets. State activation/passive-force dynamics, units, local pose/range and
transfer validation before numerical/application gates or new scientific trials.
No executable bounded admission experiment can yet be justified from these inputs.
Keep the original scientific raw prerequisites separate; three old raw freezes
still fail in CRLF checkout representation and remain false in this review.

## Evidence and executed checks

Saved report: `docs/evidence/lf-proximal-binding-review-v1/review.json`.
Raw SHA256: `512f24804d26c7e27b6244410765f253d0d8bab304b3dc5f34555c4de70d5aee`.
The report includes portable canonical source hashes, exact source-model raw hash,
five population identities/aliases, seven separate covectors/source bindings,
per-neuron unresolved assignments and recorded raw-freeze failures.

- Focused matrix: **31 passed in 7.49 s** (16 new reference tests and 15 existing
  admission-audit tests). Identity/alias/null preservation, changed convention,
  basis/NaN/omitted alternatives, raw source changes, opposite gear/invalid muscle
  contracts, virtual work, tamper rejection and exclusive failed-output retention.
- Initial sandbox test invocation: **26 passed / 5 setup errors** because pytest
  could not create its temporary directory. Rerun with a new writable worktree
  `--basetemp` passed all 31; no code/scientific changes were made to obtain that pass.
- Actual report generation: passed in 7.27 s. Actual saved-report CLI verification:
  passed in 7.12 s, including recomputation of the upstream complete evidence matrix.
- Whitespace checks passed. No new Unity Editor run, physics experiment, neural
  initialization, dependency installation or rerun of any frozen scientific trial.
  Historical broader test failures documented in the previous admission results
  were not rerun or repaired by this focused source review.

## Modified files and purpose

- `docs/LF_PROXIMAL_BINDING_REVIEW_V1.md`: prospective reference/semantics rules,
  primary citations/access limits and explicit execution/admission boundary.
- `malecns_backend/embodiment/lf_proximal_binding_review.py`: static exact-source
  inspection, reuse of admission reviewer, preserved hypotheses and review CLI.
- `tests/test_lf_proximal_binding_review.py`: reference algebra, source/identity
  defects, no alternative selection, output protection and report tampering.
- `docs/evidence/lf-proximal-binding-review-v1/review.json`: new separately versioned
  derived reference record; old evidence unchanged.
- `docs/LF_PROXIMAL_BINDING_RESULTS.md`: findings, remaining blockers and validation.
- `docs/LEG_MAPPING_STATUS.md`: current reference progress without new admission.
- `docs/PROJECT_HANDOFF.md`: current checkpoint and exact next evidence requirement.

## Git Bash after merging the PR

```bash
cd ~/Documents/FlyBrainUnity
git switch newBrain
git pull --no-rebase --no-edit
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
MODEL="$HOME/Documents/FlyMimic/flymimic/assets/models/best_combined_cvt3.xml"
"$PY" -m malecns_backend.embodiment.lf_proximal_binding_review --model "$MODEL" --report docs/evidence/lf-proximal-binding-review-v1/review.json
code docs/LF_PROXIMAL_BINDING_RESULTS.md
```

Expected: `REFERENCE REVIEW VERIFIED`, 7 tendon hypotheses / 5 populations,
current 20/42; newly admitted/steps 0; admission BLOCKED. The old raw-freeze flags
remain false in the recorded Windows checkout; current flags are printed separately.
An absent/different FlyMimic source is a clear error; do not substitute a newer XML
or change the expected hash. This command needs no new LFS asset or Unity session.

Optional unit/reference checks (use a fresh temporary directory name):

```bash
"$PY" -m pytest -q -p no:cacheprovider --basetemp="$PWD/.pytest-tmp-binding-manual-v1" tests/test_lf_proximal_binding_review.py tests/test_remaining_leg_admission_audit.py
# Expected: 31 passed. No physics or CNS experiment.
```
