# Coxa hypothesis D1/D2 — results

Protocol `docs/evidence/coxa-hypothesis-v1/protocol.json` (sha 147228…) and code were
committed at e4f2791 before the single run. Geometry and data only: no CNS and no
physics stepping. Nothing is admitted; H1/H2 are labelled hypotheses.

**Status: `D1_D2_READY`**. All checks passed: anterior frame (0.9997), D1a (18 nonzero
action vectors), D1b (`+joint_<leg>Coxa` moves the tip posteriorly in all six legs,
reproducing Step B), and D2a (every pool's body IDs equal the audit candidates; the
kernel's supplemental resolver accepts H1, H2 and H1_FLIP).

Raw output: `docs/evidence/coxa-hypothesis-v1/run/result.json` (sha ef2fbd…) and
`console.txt` (sha 658415…).

## D1 — what each coxa DoF does to the leg tip at the standing pose

Tip velocity per rad in the Thorax frame (anterior, outward, dorsal):

| Leg | +Coxa | +Coxa_roll | +Coxa_yaw | Walking range (rad) Coxa / roll / yaw |
|---|---|---|---|---|
| LF | (-1.57, 0.00, -1.19) | (0.00, 1.17, 0.00) | (0.00, 1.57, 0.00) | 0.55 / **0.68** / 0.35 |
| LM | (-1.37, -0.05, 0.20) | (-0.72, -0.16, -0.01) | (0.00, 1.18, 1.00) | **0.59** / 0.17 / 0.27 |
| LH | (-1.40, -0.23, 1.20) | (-0.85, -1.17, -0.20) | (0.00, 1.22, 1.10) | **0.50** / 0.44 / 0.25 |
| RF | (-1.49, 0.00, -1.21) | (-0.01, -1.21, 0.00) | (0.00, -1.49, 0.01) | 0.55 / **0.68** / 0.35 |
| RM | (-1.24, -0.03, 0.25) | (0.89, 0.23, 0.01) | (0.00, -1.14, -1.01) | **0.59** / 0.17 / 0.27 |
| RH | (-1.35, -0.17, 1.22) | (1.02, 0.84, -0.18) | (0.00, -1.19, -1.24) | **0.50** / 0.44 / 0.25 |

**Findings:**
- `+Coxa` is the main fore-aft DoF in every leg.
- In the front legs, Coxa_roll and Coxa_yaw produce almost the same tip motion (pure
  lateral). With the coxa hanging nearly vertical, the two axes are close to
  degenerate, so tip geometry at rest cannot tell them apart.
- The rest pose is not mirror-symmetric. In the hind legs, Coxa_roll moves the tip
  anteriorly on the left but posteriorly on the right (the sign follows the joint
  frame), and the magnitudes differ.

**D1c cross-check (reported, not a gate):** the H1 swing joint matches the largest
recorded walking range in 3/6 legs (LM, LH, RM). Mismatches: LF and RF (H1 Coxa;
recorded walking moves Coxa_roll most), and RH (H1 Coxa_roll; walking moves Coxa
most).

## D2 — the two bindings

**H1 (name-geometry; any coxa DoF):**

| Leg | Promotor | Remotor/abductor | Adductor | Ant. rotator | Post. rotator |
|---|---|---|---|---|---|
| LF | Coxa − | Coxa_yaw + (0.707 vs roll 0.704) | Coxa_yaw − | Coxa − | Coxa + |
| LM | — | Coxa + | Coxa_yaw − | Coxa − | Coxa + |
| LH | — | Coxa_yaw + (0.53) | Coxa_roll + | Coxa − | Coxa + |
| RF | Coxa − | Coxa_yaw − (near-tie with roll) | Coxa_yaw + | Coxa − | Coxa + |
| RM | — | Coxa + | Coxa_yaw + | Coxa − | Coxa + |
| RH | — | **UNASSIGNED** (0.49) | Coxa_yaw + | Coxa_roll + (0.76 vs Coxa 0.74) | Coxa_roll − |

The result is 13 channels: Coxa in 5 legs (all antagonist pairs) plus roll/yaw
channels. The signs are internally consistent: anterior pools move the joint
negatively and posterior pools positively on Coxa, matching Step B.

**H2 (bodymap labels; rotators restricted to Coxa_yaw):** it differs from H1. Under
the fixed swing named action, a rotator on Coxa_yaw has cos = 0.00, so **all 12
rotator pools are unassigned**, as are the LM and RM adductors. The result is 8 channels,
with no posterior-rotator pool anywhere.

**What this means for D3:**
- In the middle and hind legs, the hair-plate targets (sternal posterior rotators)
  are bound to Coxa in H1 (LM, LH, RM) or to Coxa_roll in RH, and are absent in H2.
  H1 vs H2 is therefore a sharp contrast.
- In the front legs, the main hair-plate target (remotor/abductor) lands on yaw in
  H1 (lateral) and on roll in H2. In both, the front-leg posterior swing comes only
  from secondary pools: the posterior rotator in H1, and nothing posterior in H2.

## Fragile points (recorded, not acted on)

- **Near-ties:** LF/RF remotor/abductor, roll vs yaw (margin 0.003); RH rotators,
  roll vs Coxa (0.02); RH remotor/abductor just below the 0.5 floor (0.49); LH
  remotor/abductor just above it (0.53).
- **Single-pose basis:** the assignments are local derivatives at one asymmetric rest
  pose, and left/right differences come from that pose. No change is made: the rule
  and the pose were fixed in advance.
- **Swing reading in H2:** H2 as preregistered uses the swing reading for rotators,
  so it is effectively "bodymap labels without rotators". A true twist reading
  (rotators producing long-axis rotation) cannot be scored with tip displacement and
  would need a separately versioned measure.

## Next

D3 (closed-loop resistance-reflex test: C0, H1, H1_FLIP, H2) gets its own hash-locked
protocol and adapter before it runs. Two engineering notes for it:
- `live_v3_motor_interface.validate_v3` deliberately refuses coxa admission, so D3
  needs a separate hypothesis-labelled session path rather than editing v3.
- I3 compares C0 with the saved Step C A_ON record, which is local only.
