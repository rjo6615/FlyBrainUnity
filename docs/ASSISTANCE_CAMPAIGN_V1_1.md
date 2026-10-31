# Assistance campaign V1.1 — corrected live-data guard

2026-10-31. Separately versioned engineering correction after the ONE executed
V1 attempt (`docs/evidence/assistance-campaign-v1/run-desktop-01`, commit
953b607) stopped at A_NC model binding: `mechanical capture mutated native data`,
1 recorded state, 0 physics transitions, 0 neural updates, qualification not
started, 7 arms unstarted. INCOMPLETE/INCONCLUSIVE_INTEGRITY; preserved as is.

## Diagnosis (no fly model, no CNS)

The V1 guard hashed every exposed numeric MjData buffer. On standalone toy
MuJoCo 3.2.7 models with contacts/constraints, arena-backed scratch buffers
changed between consecutive reads with no intervening call: `dof_island`,
`dof_islandind`, `island_dofind` (islands disabled) in a survey, and also
`efc_AR_rowadr`, `efc_AR_rownnz`, `efc_island`, `island_efcind` in a later
real-MjData test. A three-field exclusion was drafted first and rejected by its
own tests before commit. The capture's calls are read-only. The V1 guard
recorded no field names, so the actual fly fields are inferred, not observed.

## Change

`assistance_native_v1_1` guards MuJoCo's documented complete simulation state,
`mjSTATE_INTEGRATION` (time, qpos, qvel, act, qacc_warmstart, ctrl,
qfrc_applied, xfrc_applied, eq_active, mocap_pos, mocap_quat, userdata,
plugin_state), read field by field without a native call; a test proves equality
with `mj_getState(mjSTATE_INTEGRATION)` on real MjData. Derived buffers are
recomputed by mj_step from that state. Any changed field is named. `live_guard`
is recorded in the qualification, mechanical context, boundary event and arm.
Qualification budget/probes/tolerances, force audits, model phases, Trial
lifecycle and every scientific parameter/acceptance rule are unchanged.
`assistance_trial_v1_1` subclasses the executed adapter Trial;
`assistance_campaign_v1_1` reuses the V1 evaluator helpers, gates and policy,
locks the amendment (`docs/evidence/assistance-campaign-v1_1/protocol.json`), the
failed report and the executed V1 source checkpoint, and requires a V1.1-guard
qualification.

Executed V1 modules are immutable records. A new attempt writes to
`docs/evidence/assistance-campaign-v1_1/run-desktop-01` and requires explicit
user approval; no retry. Coverage 20/42; independent balance and gait unproven.
