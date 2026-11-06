# Antennal gravity sense, Step D4 v2: direction of the post-tilt commands, with the live joint ranges (design)

Designed 2026-11-06. Design only: no protocol, code or run yet.

Related documents:
- D4 v1 design `JO_COMMAND_DIRECTION_V1.md` and results `JO_COMMAND_DIRECTION_RESULTS.md`
  (protocol a7e804f2, report 8dc55e70). That evidence stays as recorded; v2 does not replace
  or relabel it.
- Step D3, `JO_COMMAND_YOKE_RESULTS.md`: the post-tilt ON commands alone topple an
  OFF-posture body (POST_ONLY 5/5); every leg group is needed.

## Why a second version

D4 v1 asked whether the **direction** of the JO-driven post-tilt command change matters, or
only its size. It could not answer, because its protocol clipped every transformed value to
[−1.35, 1.30] rad. That range is the default `MotorSafety` dataclass. The live session never
uses it. Five admitted coordinates (LM/RM femur and tibia, LH femur) sit outside it at all
times, so POST_NEG, POST_HALF and POST_SCRAMBLE pinned the middle legs at the bound. The
direction, pattern and dose labels are confounded.

v2 asks the same question with the clip rule corrected and verified at run time. Nothing else
about the question changes.

## What the live range actually is (evidence gathered for this design)

- **Live decoder construction:** in the Step D session each admitted channel's pipeline is
  `MatchedControlPipeline(True, MotorSafety(joint_min, joint_max, bound, 4 rad/s))`, with
  `joint_min`/`joint_max` from `resolve_joint_metadata`
  (`malecns_backend/embodiment/_windows_m8_live_condition.py`). That function takes the joint
  range if `jnt_limited`, intersected with the actuator `ctrlrange` if `ctrllimited`.
- **Recorded values:** the NeuroMechFly leg joints are compiled with `jnt_limited = false`,
  and the position actuators have `ctrlrange` [−1e6, 1e6].
  - `m6b_final_preflight.json` and `m6b_live_limit_diagnostic.json` classify the joints as
    `JOINT_RANGE_UNAVAILABLE`, with effective target range [−1e6, 1e6].
  - The live `m10b_manifest.json` records `joint_min_rad` −1e6 and `joint_max_rad` +1e6 for
    11 of the 20 admitted coordinates (3, 5, 10, 12, 17, 19, 26, 31, 33, 38, 40).
  - The femur-roll coordinates (4, 11, 18, 25, 32, 39) and the other coxa/femur coordinates
    have no checked-in live record of their own. They are expected to be the same, but this is
    **verified at run time** (Z6), not assumed.
- **So the live joint-range clamp is a no-op** for these coordinates. What limits a live
  command is the bounded offset around the measured position (±0.25 rad or less) and the slew
  limit (4 rad/s). The yoke path bypasses the pipeline and writes the declared positions
  directly, so neither applies, in v1 or v2.
- **Unclipped D4 transforms, from the archives (inputs, not outcomes):**
  - The largest absolute command is 2.03 rad (NEG and SCRAMBLE) and 1.89 rad (HALF), far
    inside ±1e6.
  - NEG and SCRAMBLE values go up to 0.26 rad beyond the range spanned by ON and OFF at the
    same transition; HALF never leaves it.
  - The largest commanded step at the tilt equals POST_ONLY's: 0.245 rad in G1 for NEG and
    SCRAMBLE, half of that for HALF, and 0.001 rad in FLIP. v1's 0.45–0.49 rad steps were
    clipping artifacts.
- **v1 determinism anchor:** in all 15 v1 transformed arms, qpos equals the v1 POST_ONLY arm of
  the same source at every state 0–5005 exactly, and differs at 5006. The pre-tilt schedule is
  identical, so this is required again in v2.

## Method (D4 v1 unchanged except the clip rule)

Context, yoke path, archives, scramble vector and fall rule are those of D4 v1 and D3:
- Step D trial OFF_DOWN20_s with JO withheld, the tilt at state 5005, the source's CNS seed.
- All 42 commanded coordinates come from the declared schedule. The CNS runs, but its output
  does not reach the body. Adhesion is zero.
- Transitions 0–5004, and the 22 unadmitted coordinates throughout, come from the OFF archive.
- For n ≥ 5005, with Δ(n) = ON(n) − OFF(n) on the 20 admitted coordinates:

| Condition | Admitted command at transition n ≥ 5005 |
|---|---|
| POST_NEG | OFF − Δ |
| POST_HALF | OFF + 0.5 Δ |
| POST_SCRAMBLE | OFF + s ⊙ Δ, with the **same** v1 sign vector s (rng 20261106; 10 of 20 flipped). It is not redrawn: redrawing after seeing v1 would be a selection. |

**Clip rule v2.** Each admitted coordinate is clipped to **its own live decoder range**,
declared per coordinate in the protocol as [−1e6, 1e6] (from the records above). Every arm
records the range the live session actually built for each admitted channel. If any recorded
range differs from the declared one, the run is `INCONCLUSIVE_INTEGRITY` (Z6). With these
ranges the expected number of clipped values is **zero in every arm**, and this is a gate (Z7),
not a diagnostic.

**Not re-run (reused from v1, sha-checked).** POST_ONLY for the 5 fallen sources and the 7
upright POST_ONLY controls. Their schedules use ON values directly, with no arithmetic and no
clip, so they are unaffected by the defect and would be bit-identical duplicates. Their v1
outcomes are the POST_ONLY reference. E3 (upright controls) was answered in v1 (NOT_HELD) and
is not re-asked.

## Arms

5 fallen sources (G1_DOWN20 19, 21, 24; FLIP_DOWN20 23, 24) × 3 conditions = **15
fresh-process arms**, about 65 min at the v1 rate. Each runs once and is evaluated once.

## Measures and labels

- **Fall:** tilt ≥ 45° at any stored state 5006–20000. t_fall in ms after the tilt.
- **Labels per fallen source:** identical to v1.
  - `DIRECTION_SPECIFIC` if POST_NEG stays up, `DIRECTION_NONSPECIFIC` if it falls.
  - `PATTERN_SPECIFIC` if POST_SCRAMBLE stays up, `PATTERN_NONSPECIFIC` if it falls.
  - `HALF_DOSE_STAYS_UP` or `HALF_DOSE_FALLS` from POST_HALF.
  - POST_ONLY (v1) must have fallen for the source to be labelled; it did in all 5.
- **Summary within G1 (3) and within FLIP (2):** CONSISTENT if the same for every source,
  otherwise MIXED. No pooling.
- **Reported, not gates:**
  - peak tilt;
  - largest step at the tilt;
  - per coordinate, the largest excursion beyond the ON/OFF span;
  - per arm, transitions whose commanded change exceeds the live slew limit (4 rad/s);
  - a v1 ↔ v2 table per arm (outcome, t_fall or peak tilt). This is descriptive: what
    removing the clip changed.

## Integrity (all required, else `INCONCLUSIVE_INTEGRITY`, no labels)

- **Z1 Complete:** 15 arms COMPLETE, with 20,001 samples and 4,000 ticks.
- **Z2 Pre-tilt anchor:** each v2 arm's qpos equals the v1 POST_ONLY arm of its source at every
  state 0–5005 exactly.
- **Z3 Yoke audit:** applied 42 commands equal the declared schedule exactly at every
  transition; adhesion all zero.
- **Z4 Gravity:** G0 through state 5005, R_y(−20°)·G0 from 5006; no applied wrench; zero
  external and generalized applied maxima.
- **Z5 Sources:** these all match their recorded sha256 values:
  - the Step D, D3 and D4 v1 reports;
  - the 9 Step D archives (5 fallen ON, OFF seeds 19, 21, 23, 24);
  - the 5 v1 POST_ONLY arms (sha256 values from the v1 report).

  Each arm also records its source and seed.
- **Z6 Live range:** each arm records, at attach, the `MotorSafety` range the live session
  built for each of the 20 admitted channels (exactly one channel per admitted coordinate).
  At bind it records the compiled `jnt_limited`, `jnt_range`, `actuator_ctrllimited` and
  `actuator_ctrlrange` of those 20 actuators. Required:
  - every recorded channel range equals the declared one;
  - every applied value lies inside it and inside the actuator `ctrlrange` (where
    `ctrllimited`).
- **Z7 No clipping:** zero clipped values in every arm.

**Preflight (before any arm).** The 50-step plumbing smoke (POST_NEG__G1_DOWN20_19,
discarded) is read for three things only:
- exit status;
- the yoke audit;
- the Z6 ranges.

If the recorded ranges differ from the declared ones, no arm runs. The preflight failure is
recorded and a new design is needed. The smoke ends before the tilt and reveals no outcome.

## Design expectations

**Disclosure:** these are written **after** seeing v1's confounded outcomes. With the middle
legs pinned, NEG and HALF stayed up and SCRAMBLE fell in all 5 sources. So v2 is not a blind
prediction. To avoid fitting the expectations to v1, they are carried over **verbatim** from
the v1 design and not revised:
- **E1:** POST_NEG stays up in at least 4 of 5 fallen sources (direction matters).
- **E2:** POST_HALF stays up in all 5 (the falls behave like a threshold).
- No new expectation is added about SCRAMBLE.
- Wrong expectations are recorded as wrong.

## What each outcome means (declared now)

These are as in v1:
- **`DIRECTION_SPECIFIC` and `PATTERN_SPECIFIC`:** the JO-driven post-tilt change of the
  fallen arms has a specific destabilising direction in this open loop.
- **`DIRECTION_NONSPECIFIC`:** a change of that size topples the body in either direction;
  the falls say nothing about the sign of the JO response.
- **`DIRECTION_SPECIFIC` with `PATTERN_NONSPECIFIC`:** reversing the change prevents the fall,
  but another direction of the same size does not. So the reversed direction is special,
  rather than the original one being uniquely destabilising.
- **Mixed:** reported per source.

Two further points:
- **v1 ↔ v2 differences** show what pinning the middle legs did. They are descriptive and
  say nothing about the JO route.
- **Combined with v1's G1 upright controls**, which fell under POST_ONLY: if G1 is
  `DIRECTION_SPECIFIC`, the destabilising direction is shared by fallen and upright G1 arms,
  and the closed-loop pre-tilt posture is what kept the upright ones up.

## Limits

- **Open loop.** The mixed streams never occurred in a closed loop.
- **NEG and SCRAMBLE are probes, not physiology.**
  - Their values go up to 0.26 rad outside anything the live session produced at that
    transition.
  - They step at the tilt by as much as POST_ONLY does.
  - They can exceed the live slew limit.

  All three are reported.
- **No clip means no joint-limit protection.** The leg joints are compiled unlimited, so a
  commanded 2.03 rad is physically reachable here. ON commands already reach 1.99 rad.
- **One scramble vector.** It is reused from v1 and is not a distribution.
- **The expectations are not blind** (see the disclosure above).
- **Sample size.** Five fallen sources; labels per source, no statistics.
- **Inherited limits.** Step D's limits apply: idealised gravity step, modelled JO
  transduction.
- **No claims.** No balance, corrective-response or biological-cause claim. No motor
  coordinate status change (20/42 admitted, +4 conditional).

## Build and run plan (on approval)

1. Write `docs/evidence/jo-command-direction-v2/protocol.json` with these rules, the per-
   coordinate declared ranges, the v1 sign vector and the source hashes (including the v1
   report and the 5 v1 POST_ONLY arms).
2. Write `malecns_backend/live/jo_command_direction_v2.py`. It reuses the v1 module (`split`,
   `SIGN`, `Trial`, archive loading, `degenerate`, labels, consistency) and D3's yoke audit,
   gravity check and fall rule, adding:
   - the per-coordinate clip;
   - the Z6 range record (at bind and attach);
   - Z2 against v1 POST_ONLY;
   - Z7;
   - the v1 ↔ v2 table.

   The v1 module is not edited.
3. Write synthetic tests, including commands **outside** [−1.35, 1.30] (the case v1's tests
   missed). They cover the schedules, the zero-clip expectation, a declared/recorded range
   mismatch (Z6), a Z2 mismatch and the labels.
4. Run the plumbing preflight (above). Then commit and push the preregistration, run the 15
   arms once in the background, evaluate once, and record the results, the handoff and the
   roadmap.
