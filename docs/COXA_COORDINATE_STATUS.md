# Coxa coordinate status

Policy: `COXA_ADMISSION_QUESTION_V1.md` Part A, approved by the user on 2026-11-02.

**CONDITIONAL coordinates are counted separately and are never part of the admitted
count.** They may be enabled only through the labelled hypothesis session path
(`coxa_hypothesis_loop.create_hypothesis_session`). Every result that uses them carries the
label `COXA_CONDITIONAL_H1`. Any later preregistered failure revokes the status, and the
revocation is recorded here.

**Totals: 20/42 admitted (v3, unchanged); +2 conditional.**

| Coordinate | Status | Evidence |
|---|---|---|
| joint_LFCoxa | **CONDITIONAL** (H1, sign +1) | D3 (seed 1, all channels); `COXA_ADMISSION_RESULTS.md` CONFIRMED 3/3 seeds, isolated |
| joint_LHCoxa | **CONDITIONAL** (H1, sign +1) | same |
| joint_RFCoxa | BLOCKED_BY_INPUT | D3: hair plates 120 Hz, coxa MNs 0.55 Hz; `RF_COXA_EXCITATION_RESULTS.md` (activity gap); `RF_RELAY_INTERVENTION_RESULTS.md`; anatomy vs reconstruction still open: BANC cross-check INCONCLUSIVE_INTEGRITY (`RF_HAIR_PLATE_CROSS_CONNECTOME_RESULTS.md`) |
| joint_RHCoxa_roll | BLOCKED_BY_INPUT | D3: RH hair plates 0.16 Hz in the held posture |
| joint_LFCoxa_yaw, joint_LHCoxa_roll, joint_LHCoxa_yaw | UNTESTED | The reflex measure tests only the fore-aft component |
| Middle-leg coxa (9) | UNTESTED | Middle-leg hair-plate encoder silent in this context |
| All other coxa coordinates | UNTESTED | — |

Current as of 2026-11-03.
