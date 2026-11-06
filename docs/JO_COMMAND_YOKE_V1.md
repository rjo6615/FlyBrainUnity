# Antennal gravity sense, Step D3: which commands make the ON arms fall? (design, V1)

Designed 2026-11-05.

**Status 2026-11-06:** preregistered (27e253b, protocol 3fbb281d), 45 arms run once and
evaluated once. `INTEGRITY_ACCEPTED`. Every leg group is `NECESSARY_NOT_SUFFICIENT` in all 5
sources (CONSISTENT in G1 and FLIP). POST_ONLY falls in 5/5, PRE_ONLY in 0/5; the FLIP time
test is degenerate (ON and OFF bodies identical until after the tilt). E1 and E2 NOT_HELD.
See `JO_COMMAND_YOKE_RESULTS.md`. The design text below is unchanged.

Related documents:
- Step D, `JO_ZONE_CROSSING_RESULTS.md`: 5 of 12 ON DOWN20 arms fell; no OFF arm fell.
- Step D2, `JO_ROLLOVER_TIMING_RESULTS.md`: the falls are late (583–1415 ms after the tilt)
  and abrupt (about 30 ms). No early-window marker separates them, and the command-order
  label is not diagnostic.

## Why this step

**The body depends only on the commands it receives.**
- Adhesion is disabled (constant zero).
- No external force or wrench is applied.
- The only time-varying physical input besides the 42 commanded joint positions is the
  declared gravity step at state 5005.

Matched ON and OFF arms share the same initial state. The fall in an ON arm is therefore
fully determined by its command stream. Replaying the whole ON stream would just reproduce
the fall, so that is used only as an integrity check.

The informative question is **which part of the ON command stream is sufficient, and which
part is necessary**, for each fall:
- **by leg group:** the FLIP falls showed front-leg commands at or near the channel bound;
  the G1 falls showed raised right-hind MN activity;
- **by time:** the commands before the tilt (the tonic JO posture) against the commands after
  it.

This tests D2's hypothesis directly. That hypothesis is that JO-driven posture puts the body
in a less stable regime, rather than the body making a timed response to the tilt.

## Method (reuses the validated yoke path)

This uses the established yoke path of `coxa_offset_yoke`. The outgoing action at transition
n is replaced, at `sim.step`, by an archived command row (source `samples[n+1]`).
- **Context:** the Step D trial for `OFF_DOWN20_s`, with JO withheld, the same tilt at state
  5005 and the same CNS seed as the source.
- **Commands:** all 42 commanded coordinates are taken from a declared mix of two archives,
  so the CNS output does not reach the body. The CNS still runs, because the existing session
  requires it, but it is only read out.
- **Archives:** for the fallen arm A_s, the ON archive is A_s's recorded commands, and the OFF
  archive is OFF_DOWN20_s's. Both are local raw Step D arms, checked against the Step D report
  hashes.
- **The 22 unadmitted coordinates:** they always come from the OFF archive. The report states
  whether they differ between the ON and OFF archives at all; they are expected to be
  identical, since baseline servos are not neural.

Leg groups of the 20 admitted channels (exact indices from `initial.channels`):

| Group | Channels |
|---|---|
| FRONT | LF/RF Femur, Femur_roll, Tibia, Tarsus1 (indices 3–6, 24–27) |
| MIDDLE | LM/RM Femur, Femur_roll, Tibia (10–12, 31–33) |
| HIND | LH/RH Femur, Femur_roll, Tibia (17–19, 38–40) |

## Arms

For each of the 5 fallen arms (G1_DOWN20 in seeds 19, 21 and 24; FLIP_DOWN20 in seeds 23
and 24):

| Condition | Admitted commands at each transition |
|---|---|
| FULL_ON | ON for all 20 channels at all times. Integrity: must reproduce A_s exactly. |
| ONLY_FRONT / ONLY_MIDDLE / ONLY_HIND | ON for that group, OFF for the other groups, at all times (sufficiency) |
| NO_FRONT / NO_MIDDLE / NO_HIND | OFF for that group, ON for the other groups, at all times (necessity) |
| PRE_ONLY | ON for all 20 channels for transitions 0–5004 (up to the tilt), OFF from transition 5005 on |
| POST_ONLY | OFF up to the tilt, ON for all 20 channels from transition 5005 on |

That is 9 conditions × 5 fallen arms = **45 fresh-process arms**, about 3.7 h at the Step D
rate. Each runs once and is evaluated once.

## Measures and labels

- **Fall:** tilt ≥ 45° at any stored state after 5005 (the Step D2 rule, `body_angles`).
  t_fall is reported in ms after the tilt.
- **Outcome per arm:** `FALLS` or `STAYS_UP`, with t_fall and peak tilt.

Per fallen arm and leg group:

| Label | Rule |
|---|---|
| `SUFFICIENT_AND_NECESSARY` | ONLY_X falls and NO_X stays up |
| `SUFFICIENT_NOT_NECESSARY` | ONLY_X falls and NO_X falls |
| `NECESSARY_NOT_SUFFICIENT` | ONLY_X stays up and NO_X stays up |
| `NEITHER` | ONLY_X stays up and NO_X falls |

| Time label | Rule |
|---|---|
| `PRE_TILT_SUFFICIENT` | PRE_ONLY falls |
| `POST_TILT_SUFFICIENT` | POST_ONLY falls |

Both, one or neither can apply. Each is reported per arm.

**Summary per assignment** (G1: 3 arms, FLIP: 2 arms): a group or time label is
**CONSISTENT** within an assignment if every arm of that assignment has it. Otherwise it is
reported per arm. No pooling across G1 and FLIP, whose falls looked different in D2.

## Integrity (all required, else `INCONCLUSIVE_INTEGRITY`, no labels)

- **Y1 Complete:** all 45 arms are COMPLETE, with 20,001 samples.
- **Y2 Reproduction:** each FULL_ON arm's qpos equals its source ON arm's qpos at every
  stored state (exact equality). This establishes that the body is determined by the applied
  commands on this path.
- **Y3 Yoke audit:** at every transition of every arm, the applied 42 commands equal the
  declared mix of the two archives exactly. Adhesion is all zero.
- **Y4 Gravity:** the recorded gravity is G0 through state 5005 and R_y(−20°)·G0 from 5006
  on. No applied wrench; zero external and generalized applied maxima.
- **Y5 Sources:** the 10 source archives (5 ON, 4 distinct OFF) match the Step D report
  sha256.

## Design expectations (recorded before any arm runs)

- **E1, FLIP:** FRONT is `SUFFICIENT_AND_NECESSARY` and POST_ONLY falls. In D2, the front-leg
  commands near the bound appeared before divergence, and the E-onset drive starts at the
  tilt.
- **E2, G1:** PRE_ONLY falls. G1's E drive is tonic before the tilt and turns off after it,
  so the expectation is that the pre-tilt posture sets up the fall. Which group is
  responsible is not predicted; HIND is a weak guess, from the raised RH MN activity.
- Wrong expectations are recorded as wrong.

## What each outcome means (declared now)

- **A group `SUFFICIENT_AND_NECESSARY`:** that leg group's JO-driven commands carry the fall
  in this open-loop setting. It is the place to look for why sensing tilt destabilises
  rather than corrects.
- **`PRE_TILT_SUFFICIENT` only:** the tonic JO posture before the tilt is enough. That
  supports the reading that the fly sits in a less stable regime.
- **`POST_TILT_SUFFICIENT` only:** the post-tilt command change is enough. The falls are a
  delayed consequence of the tilt response.
- **Mixed or none:** the fall needs a combination of groups or periods. It is reported per
  arm.

## Limits

- **Open loop.** Mixed command streams never occurred in a closed loop. Sufficiency here
  does not mean that the closed-loop brain would produce the same fall.
- **Switching archives at the tilt** (PRE_ONLY, POST_ONLY) puts a step in the commanded
  positions at the same moment as the gravity step.
- Five fallen arms. The labels are per arm, with no statistics.
- The CNS runs only because the session requires it; its output does not reach the body.
- Step D's limits apply. No balance, corrective, zone-sign or motor-coordinate claim (20/42
  admitted, +4 conditional).

## Build and run plan (on approval)

1. Write `protocol.json` with these rules and the source hashes.
2. Write `malecns_backend/live/jo_command_yoke.py`. It subclasses the Step D `Trial` and uses
   `coxa_offset_yoke`'s `sim.step` override pattern with a full 42-coordinate mixed schedule.
   Evaluation reuses `body_angles` and Step D2's fall rule.
3. Write synthetic tests: the mix construction per condition, the yoke audit, the labels and
   the integrity failures.
4. Run a plumbing smoke: one 50-step mixed arm (exit status and yoke audit only; discarded).
5. Commit and push the preregistration, run the 45 arms once in the background, evaluate
   once, and record the results, the handoff and the roadmap.
