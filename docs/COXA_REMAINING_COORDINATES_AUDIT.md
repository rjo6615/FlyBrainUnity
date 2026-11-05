# Remaining coxa coordinates: can the existing method test them? — desk audit (V1)

2026-11-04, after the push replication was merged (PR #320). This is a **desk audit of
results already committed in the repository**. Nothing new was run, no protocol is
registered, and no coordinate status changes. It asks one question: can the existing
CONDITIONAL route (Part A, C1–C4, using the imposed-displacement C2/C3 method) test any of
the 14 coxa coordinates that are neither CONDITIONAL nor already blocked, or that are
blocked for a reason a new versioned test could address?

## The method's three requirements

The C2/C3 method passes a coordinate only if a closed loop exists:

1. **Sensory route.** The leg's SNpp45 hair plates are driven by the existing
   forward-limit encoder (`hair_plate_encoder`: forward component f of the coxa long axis,
   coxa origin to femur origin, in the Thorax frame).
2. **Rule-fixed binding.** The H1 binding (`COXA_HYPOTHESIS_D1_D2_RESULTS.md`) has a channel
   on the coordinate whose pools receive hair-plate input.
3. **Measurable consequence.** Moving the coordinate changes f. The C2 rule is a change in f
   (PC df ≤ −0.02, PF df ≥ +0.02). A coordinate that cannot change f cannot pass and cannot
   fail. Its result would be null by construction, not a falsification.

## Evidence used (all committed; nothing recomputed)

**Encoder visibility.** `docs/evidence/hair-plate-encoder-v1/run/result.json`, field
`axis_direction_per_0p1rad`, gives the change in f for +0.1 rad of each coxa DoF at the rest
pose.

| Leg | Coxa | Coxa_roll | Coxa_yaw |
|---|---|---|---|
| LF | −0.0999 | +0.00049 | 0.0 |
| LM | −0.0996 | +0.00014 | ~0 |
| LH | −0.0997 | −0.00003 | ~0 |
| RF | −0.0998 | −0.00044 | ~0 |
| RM | −0.0998 | −0.00013 | ~0 |
| RH | −0.0946 | +0.00002 | ~0 |

Roll and yaw change f by at most 0.5 % of what Coxa does, in every leg. Both rotate about
axes through the coxa origin that lie close to the coxa long axis, so the long axis that the
encoder reads barely moves. The tip-level D1 vectors differ (roll moves the LM/LH/RM/RH tips
fore-aft) because the femur and tibia act as a lever. The encoder does not see the tip.

**Hair-plate input to each bound pool.** These are direct synapses from
`docs/evidence/hair-plate-identity-v1/run/result.json`. **Binding** is from
`docs/evidence/coxa-hypothesis-v1/run/result.json`, `channels.H1`.

## Classification of the 18 coxa coordinates

| Coordinate | Current status | H1 channel (pools, sign) | Direct HP synapses onto bound pools | Changes f? | Testable by the existing method? |
|---|---|---|---|---|---|
| LF / LM / LH / RM Coxa | CONDITIONAL | yes | yes | yes | (done) |
| RF Coxa | BLOCKED_BY_INPUT | yes | RF input blocked | yes | no (input) |
| RH Coxa | UNTESTED | **none** (RH rotators bound to roll, 0.76 vs 0.74; remotor/abductor unassigned, 0.49) | (213 onto the posterior rotator, bound elsewhere) | yes (−0.095) | **no: binding** |
| RH Coxa_roll | BLOCKED_BY_INPUT | yes (ant. rotator + / post. rotator −) | 213 / 0 | **no** | no (input and visibility) |
| LF Coxa_yaw | UNTESTED | yes (remotor/abductor + / adductor −) | 445 / 7 | **no** | no: visibility |
| LH Coxa_roll | UNTESTED | yes (adductor, unidirectional +) | 12 | **no** | no: visibility |
| LH Coxa_yaw | UNTESTED | yes (remotor/abductor, unidirectional +) | 8 | **no** | no: visibility |
| RH Coxa_yaw | UNTESTED | yes (adductor, unidirectional +) | 21 | **no** | no: visibility |
| LM Coxa_yaw | UNTESTED | yes (adductor, unidirectional −) | 0 | **no** | no: no route, visibility |
| RM Coxa_yaw | UNTESTED | yes (adductor, unidirectional +) | 0 | **no** | no: no route, visibility |
| RF Coxa_yaw | UNTESTED | yes (adductor + / remotor/abductor −) | RF input blocked | **no** | no: input, visibility |
| LF / LM / RF / RM Coxa_roll | UNTESTED | **none** | — | **no** | no: binding, visibility |

**Result: none of the 14 coordinates outside the CONDITIONAL four can be tested by the
existing encoder, binding and C2 measure.**
- All 12 roll/yaw coordinates, including the already-blocked RH Coxa_roll, are invisible to the
  encoder.
- RH Coxa is visible, but H1 assigns it no channel.
- RF Coxa is blocked by input.

## What would be needed (each its own versioned decision; none is proposed as a default)

- **Roll/yaw senses.** This needs a modeled transduction that responds to coxa roll or
  yaw. M5B-2 (`M5B_MULTI_AXIS_COXA_AUDIT.md`) already concluded that local metadata gives the
  hair plates no axis, tuning or direction. A multi-axis encoder is therefore not defensible
  from local evidence, and choosing one would be an invented axis, not reconstruction. That
  conclusion stands.
- **A tip-based measure.** One could replace f with the leg-tip movement, so that roll/yaw
  outcomes become measurable. But the hair plates would still sense only fore-aft
  displacement. The only prediction left would be "the bound pool moves the tip in its named
  direction", which is how H1 assigned the pool in the first place. A sign-flip control would
  then be circular. This route cannot give independent C2 evidence. I would not recommend
  it.
- **RH Coxa.** This needs a new, separately versioned binding rule. The H1 near-tie
  (0.76 vs 0.74) was fixed in advance. Re-choosing it after seeing which assignment is
  testable would be selecting for a result. Any new rule must be justified independently of
  that outcome. RH hair plates are also silent at rest (0.16 Hz), so the test would also need
  the middle-leg imposed displacement.

## Consequences

- Within the current validated components, **the coxa track has reached its ceiling**:
  20/42 admitted, +4 conditional. The other remaining coordinates (middle/hind Tarsus1) are
  source-blocked (`DISTAL_ANATOMICAL_QUALIFICATION_RESULTS.md`). So none of the 22
  unadmitted coordinates is testable with the existing encoders, bindings and measures.
- **Further motor coverage needs new evidence, not a new test.** The evidence would be a
  roll/yaw-specific sense, an independently justified binding, or the source data blocking
  Tarsus1. Per the local-only constraint, no external data is sought.
- **Record keeping.** `COXA_COORDINATE_STATUS.md` lists "Other middle-leg coxa (7)", but
  only four middle-leg coxa coordinates (LM/RM roll and yaw) are not CONDITIONAL. That row is
  inconsistent and should be reconciled. This audit does not edit the status file.

## Limits

- The visibility figures are a derivative at one rest pose. Roll or yaw at a very different
  pose could tilt the long axis more. The method's own displacements are small (about
  0.2 rad), so this is unlikely to change the conclusion, but it was not measured.
- While checking the archive format, I looked at one spike count in an existing arm: in
  coxa-admission `C0_1`, LF remotor/abductor MNs fired 147 and 153 spikes over 2 s. It is
  reported here for completeness. No classification uses it.
- This audit classifies against the current method only. It says nothing about the biology
  of roll/yaw proprioception.
