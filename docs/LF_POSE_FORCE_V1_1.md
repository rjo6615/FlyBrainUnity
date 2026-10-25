# LF pose/force v1.1: native sparse transmission decoding

Prospective correction, 2026-10-25. Commit before a separately archived fixed
repeat. All 15 poses, 137 explicit forward calls, source XML/assets, activation/
control probes, finite-difference epsilon and acceptance tolerances remain those
of LF_POSE_FORCE_V1.md. No model, force scale or neural parameter is changed.

V1 protocol/code/input manifest committed at 51a22f3 before execution. Its complete
137-call record is preserved at docs/evidence/lf-pose-force-v1/run/validation.json,
3222353 bytes, raw SHA256
5413ad619c1f8b3fb08b2468c9dc3667cd715365246f7ca933e5ebc10aba6252.
The overall result failed; native force-law/dynamics and orientation/Jacobian
checks passed, while all pose tendon-derivative/total-force checks and the central
R reproduction failed. Retain every observation and that failed evaluation.

The implementation incorrectly reshaped actuator_moment as a dense nu*nv matrix.
[MuJoCo 3.2.7 data definitions](https://mujoco.readthedocs.io/en/3.2.7/APIreference/APItypes.html)
specify sparse transmission values plus moment_rownnz, moment_rowadr and
moment_colind. Allocated storage size does not establish dense row layout. The
archived central tendon-length finite differences reproduce the original frozen
R_M within 2.765e-11 even though the incorrectly decoded moments do not. This
isolates a representation defect without tuning geometry or thresholds.

V1.1 uses native mju_sparse2dense with those exact row descriptors. Preserve full
raw values/row counts/addresses/column indices as well as the converted matrix in
every observation. Saved review independently reconstructs the sparse matrix with
SciPy CSR and requires equality to the recorded dense matrix within 1e-12. Reject
bad shapes, noninteger/out-of-range descriptors, nonfinite used values or duplicate
columns. A new synthetic sparse-layout unit test must distinguish compressed rows
from a misleading allocated dense-sized buffer.

The new schema is lf-pose-force-v1.1; the measurement namespace is
docs/evidence/lf-pose-force-v1_1/run/. Reuse the original committed input manifest
unchanged. V1 remains failed and its JSON is never overwritten or re-evaluated
into a historical pass. The repeat is justified by this documented implementation
correction, not by new acceptance, pose selection or behavior. Sparse conversion
and muscle helper calls do not add mj_forward/mj_step calls. The new saved review
still performs no model construction or dynamics.

Scope remains a modeled rotational correspondence and source-force fidelity at
sampled poses; no actual FlyGym finite-angle registration, cross-body force scale,
neural activation law, production actuator replacement, new admission or biological
validation. Old raw prerequisites remain reported separately and unresolved.
