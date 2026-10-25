# Paired LF endpoint/body-frame observation V1.1

Prospective correction to V1, committed before a NEW campaign. Original V1
protocol/runner/raw record remain unchanged. V1 ended INTEGRITY_FAILURE during
target metadata inspection: one source compile, one target initializer7forwards/
3resets, ZERO kinematics probes and zero integration/CNS. No endpoint outcomes
were observed or selected. Original raw631895bytes SHA256
4de986daefb60a8528f7fb361cc0dfe0d7120af109140ace52bf4804ca28d598.

## Demonstrated implementation defect and exact correction

V1 correctly normalized body/geom lookup names but compared a full compiled mesh
name with an unprefixed source XML name. The installed dm_control MJCF namespace
contract independently demonstrates `mesh_Thorax` becomes `fly/mesh_Thorax` after
attachment, without compiling any model. Existing `namespace_component` is the
project authority for this attachment prefix; it is reused, not replaced.

V1.1 stores BOTH full raw mesh names and their terminal components. Numeric
geom_dataid, geom_bodyid and full model/table hashes are unchanged. Require each
selected mesh terminal name to equal the XML name AND full mesh prefix to equal
the corresponding full geom prefix. Thus exact attachment ownership is retained,
not relaxed into a fuzzy/suffix match. All raw full names remain in the record.
Require the full source model/initial-state identity to equal the preserved V1
source compilation, as well as the target's original native baseline identity.

Use V1 observer/algebra/evaluator checks unchanged, with V1.1's own schema and an
additional explicit namespace-integrity check. Reuse its entire211kinematics
schedule, source/target models, poses, epsilon, budgets, state/range/accounting and
failure classifications. No module-global monkeypatch or model parameter change.
The V1 schema check still rejects V1.1; new evaluator separately validates V1.1
before composing the unchanged non-schema guards.

## Scope and acceptance

All V1 requirements/limits apply. One fresh source compile and one target native
initializer,105source/106target kinematics,0probe forwards/resets/integration/CNS.
No force application, target muscle sites, registration fit, neural/seed/gain/
physiology change, tolerance/window/pose selection or automatic retry.

V1.1 classifications keep the V1 result prefixes for integrity/range/disagreement
but accepted geometry is ENDPOINT_FRAME_V1_1_OBSERVER_VERIFIED_TRANSFER_BLOCKED.
Any failure is retained in its own namespace. Historical V1 stays a setup integrity
failure regardless of V1.1 outcome. This correction validates reference bookkeeping,
not anatomy, physical transfer, nonzero-velocity physiology, balance or admission.
