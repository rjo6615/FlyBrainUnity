# LF transfer prerequisite review results

2026-10-25; baseline98fb1f5, merged PR276. Read-only evidence/source review;
no new physical or neural experiment. Source/protocol rules are in
`LF_TRANSFER_PREREQUISITES_V1.md`; saved output is
`evidence/lf-transfer-prerequisites-v1/run/review.json`.

Result: **TRANSFER_REVIEW_VERIFIED_PHYSICAL_ANATOMICAL_NEURAL_RAW_GATES_OPEN**.
The saved V2 evaluator still verifies all nine synthetic cases. Original failed
V1 remains INTEGRITY_FAILURE. Neither record was rewritten.

| Gate | Review finding |
|---|---|
| Software coupling | Verified under the original constant-coefficient synthetic context |
| Physical scale/lineage | Four explicit peak-force parameters exist; a complete source-to-target dimensional conversion remains unresolved |
| Geometry | Source pose assay and modeled rotation map exist; actual target attachment/length registration is not validated |
| Length/velocity | Preserve the source law and parameters; frozen zero-velocity reference forces are insufficient for moving target muscles |
| Anatomy | Five populations, seven tendon hypotheses, thirteen exact neurons; individual tendon bindings stay null |
| Neural conversion | No supported proximal spike-to-activation law established |
| Original raw requirements | Failed original scientific prerequisites remain false; no replacement locks |

The four source peak-force values are28.7481,12.9,10.5807,157.429 in unresolved
source force units. They override the muscle default force=-1; automatic acc0
scaling does not describe these four explicit parameters. Source gravity-9801
and mesh scale1000, versus FlyGym gravity-9810, are clues rather than a complete
unit convention. The source task's actuator-force observation divides by1000;
this does not establish a physical conversion for applied force. Source/target
force and torque conversions stay null. FlyGym clock seconds is explicitly
documented. Primary sources and their limits are linked in the V1 protocol.

This verifies reference-model semantics, not biological calibration. The source
paper identifies uncertainty in optimized muscle properties. It does not supply
an exact MaleCNS spike-to-force calibration. No muscle parameter, gain, threshold,
seed, mapping, raw lock or production control was changed.

## Checks actually performed

- Original source XML raw hash and all four selected muscle attributes checked
  against the existing binding authority; compiler/option/mesh-scale snapshot
  captured. FlyGym context source hash matches the original native input manifest.
- Saved review generated and verified through Windows Git Bash. Original V2
  preflight/evaluator reused; no native body/solver/CNS execution in this review.
- New source/tamper tests reconstruct real saved evidence with native construction,
  forward, step, activation dynamics, solver and live audit entry points forbidden.
  These are software/reference checks, not executed CNS/physics experiments.
- Initial11pass/9setup errors: sandbox temporary directory creation denied. Local
  scratch resolved this without code/scientific changes. Initial broader run:
  49pass/1fail because sparse checkout omitted canonical historical B4/M7 NPZs.
  Hydrated the original two LFS objects; failed legacy case then passed. This
  broader crosswalk test includes native model inventory, not physics integration.
- Final batch: **50 passed in27.74s** across `test_lf_transfer_prerequisites.py`,
  `test_lf_proximal_binding_review.py` and `test_lf_anatomical_crosswalk.py`.
  Windows Git Bash saved-review command passed. Whitespace and staged LFS-pointer
  checks passed. No dependency additions or environment changes.

## Windows Git Bash after merging this PR

Each `&&` stops the block if an earlier sync/check fails. Preserve local files
and commits; this block does not reset or clean them.

```bash
cd ~/Documents/FlyBrainUnity &&
git switch newBrain &&
git pull --no-rebase --no-edit &&
git lfs pull --include="malecns_backend/embodiment/interface_output/integrated_whole_leg_readiness.json,docs/evidence/lf-anatomical-crosswalk-v1/annotations.feather,docs/evidence/lf-pose-force-v1*/run/validation.json,docs/evidence/lf-activation-transient-v1/run/validation.json,docs/evidence/lf-activation-integrator-v1/run/validation.json,docs/evidence/lf-native-isolation-v1*/run/validation.json,docs/evidence/lf-synthetic-coupling-v*/run/validation.json" &&
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" &&
"$PY" -m malecns_backend.embodiment.lf_transfer_prerequisites \
  --report docs/evidence/lf-transfer-prerequisites-v1/run/review.json
```

Expected: `TRANSFER REVIEW VERIFIED`, software prerequisite9/9; physical,
anatomical, neural and raw gates OPEN;20/42,0new admissions,0physics/CNS
transitions. Original recorded/current raw prerequisites false at this checkpoint;
if newline representation differs, current state is reported separately without
rewriting history or enabling transfer. No Unity run is needed for this review.

Next is exact source-unit/parameter-conversion lineage, followed by a separately
specified target length/velocity/finite-angle assay if supported. Those gates,
anatomical binding, neural conversion and original raw requirements precede a
bounded headless moving-fly experiment and then a meaningful new Unity test.
Independent neural balance and walking remain unestablished;20/42 measures motor
admission coverage, not overall project completion.
