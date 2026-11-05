# Antennal gravity sense, Step D2: what comes first when ON arms fall? (design, V1)

Designed 2026-11-05. This is the design only. No code exists and nothing has been computed.
On approval, the rules below are copied into
`docs/evidence/jo-rollover-timing-v1/protocol.json`, hash-locked in code, and committed before
any replay runs.

Related document: Step D, `JO_ZONE_CROSSING_RESULTS.md` (`INTEGRITY_ACCEPTED`).

## Why this step

In Step D, **5 of the 12 tilted arms with antenna input (ON DOWN20) turned over**:
- G1_DOWN20 in seeds 19, 21 and 24;
- FLIP_DOWN20 in seeds 23 and 24.

No arm without antenna input (OFF) fell, and no LEVEL arm fell. All arms within a seed share
the same random numbers and the same body state up to the tilt. The only difference between
an ON arm and its matched OFF arm is therefore the JO input at the brain boundary, plus its
consequences.

For the balance goal, this matters more than the labels. In this reconstruction, adding the
antennal gravity sense can make the body fall on a slope. Step D2 asks **in what order things
happen** before a fall:
- Does the brain's motor command diverge from the OFF arm first?
- Does the body diverge first?
- Do the legs lose ground contact first?

**This is descriptive.** Temporal order is not proof of cause.

**Already seen (disclosed):** from the Step D report, I have seen the per-arm peak and mean
tilt, the mean pitch and roll, the window d, and the DN contrasts. I have not seen any time
course, onset time, support count, or command trace of any arm.

## Data (no new simulation)

- **The 37 local raw Step D arms.** Each must match its sha256 in the Step D report
  (`docs/evidence/jo-zone-crossing-v1/run/report.json`, sha e64811f7…).
- **Analysed pairs:** each of the 24 ON arms (G1/FLIP × LEVEL/DOWN20 × seeds 19–24) against
  the matched OFF arm with the same seed and tilt. The 12 LEVEL pairs are controls, since none
  fell.
- **Recorded per stored state (0.1 ms):** qpos, gravity, 42 commanded joints, and supports
  (the number of legs whose Tarsus5 touches the ground).
- **Recorded per neural tick (0.5 ms):** fired, jo_d and the JO rates.

## Definitions (fixed now)

All times are counted from the tilt (stored state 5005, 500.5 ms) to the end of the run
(2000 ms).

| Quantity | Definition |
|---|---|
| Tilt | Angle between the Thorax z axis and −ĝ, using the recorded gravity (`body_angles`, Step C) |
| **FELL** | Tilt ≥ 45° at any stored state after 5005. Otherwise **UPRIGHT**. |
| t_fall | First state with tilt ≥ 45° |
| Baseline | For any ON − OFF difference x(t), the mean of x over states 4005–5005 (400.5–500.5 ms, before the tilt). This removes the tonic difference due to JO input. |
| **t_body** | First state after 5005 where the baselined ON − OFF tilt difference is > 5° and stays > 5° up to t_fall (FELL), or to the end (UPRIGHT; usually none) |
| **t_cmd** | First state after 5005 where the baselined ON − OFF difference of any of the 20 admitted commanded joints is > 0.05, which is 20 % of the 0.25 channel bound |
| **t_support** | First state after 5005 where ON supports < 3 while matched OFF supports ≥ 3 |
| t_JO | First tick after the tilt whose recorded E rate differs from its pre-tilt value, on either side (E on in FLIP, E off in G1) |

Why 5° and 0.05:
- The OFF DOWN20 mean tilt varies by about 0.5° across seeds (16.9–17.4°), so 5° is about
  ten times the seed spread.
- 0.05 is a fifth of the channel bound.

Both were chosen before any time course was seen. They will not be changed.

## Questions and labels

**Q1, per FELL arm (order).** One label per arm:

| Label | Rule |
|---|---|
| `COMMAND_FIRST` | t_cmd exists and t_cmd < t_body − 10 ms |
| `BODY_FIRST` | t_body exists and (no t_cmd, or t_cmd > t_body + 10 ms) |
| `CONCURRENT` | both exist and \|t_cmd − t_body\| ≤ 10 ms |
| `UNRESOLVED` | t_body not found (the tilt difference grows without staying above 5°) |

Each FELL arm also reports:
- t_JO, t_cmd, t_body, t_support and t_fall, in ms after the tilt;
- the first admitted channel to cross 0.05, and its sign.

**Q1 summary:** `ORDER_COMMAND_FIRST` if at least 4 of the 5 FELL arms are `COMMAND_FIRST`;
`ORDER_BODY_FIRST` if at least 4 are `BODY_FIRST`; otherwise `ORDER_MIXED`.

**Q2, FELL against UPRIGHT ON DOWN20 arms (5 against 7).** Each feature is measured over the
early window from 500.5 ms to the earlier of 550 ms and the arm's t_body:

| Feature | Definition |
|---|---|
| F1 | max over the 20 channels of \|baselined ON − OFF commanded joint\|, averaged over the window |
| F2 | per leg (6 legs), the baselined ON − OFF mean leg-MN rate over that leg's pools (pools as in Step C; T1/T2/T3 left/right → LF/LM/LH/RF/RM/RH); reported per leg, with the maximum \|value\| used for the label |
| F3 | minimum ON supports in the window |
| F4 | mean recorded d (L, R) in the window |

Per feature: `SEPARATES` if every FELL value lies above every UPRIGHT value, or every one
below; otherwise `OVERLAPS`. With 5 against 7, complete separation has an exact
probability under random labelling of 2/792 ≈ 0.0025. That is a description, not a
significance claim. Four features are checked, and no correction is applied.

**Controls (reported, not labelled):**
- the same quantities for the 12 LEVEL pairs (the expectation is no t_body);
- the ON − OFF command and MN differences in the 50 ms before t_body in each FELL arm.

## Integrity (all required, else `INCONCLUSIVE_INPUT` with no labels)

- **R1:** all 37 arm sha256 values equal the Step D report.
- **R2:** the per-arm peak tilt, recomputed exactly as Step D computed it (same window and
  function), equals the Step D report's `tilt_max_deg` within 1e-9.
- **R3:** FELL is exactly the 5 arms named above, all OFF arms are UPRIGHT, and all LEVEL
  arms are UPRIGHT. This is consistent with the already disclosed peaks. R3 is a check that
  the right arms are being read, not an outcome.
- **R4:** pre-tilt identity. For each pair, the ON and OFF qpos at state 0 are equal (Step D
  I4).

## Design expectation (recorded before any time course is seen)

Only ON arms fall, and the matched OFF arm differs only by JO input. The expectation is
therefore **`ORDER_COMMAND_FIRST`**, with F1 `SEPARATES` (larger in FELL). If this is wrong,
it is recorded as wrong.

`BODY_FIRST` would mean the body starts to diverge before any admitted command does. That
would point to:
- passive mechanics from the tonic JO-driven posture (for example, the about 4–5° G1 roll);
- or command differences below 0.05 that act over time.

## What each outcome means (declared now)

- **`ORDER_COMMAND_FIRST`:** the falls follow a JO-driven change in admitted motor commands
  after the tilt. A later protocol could test this causally, for example by yoking those
  commands into an OFF arm. Not shown here.
- **`ORDER_BODY_FIRST`:** the falls start from posture or mechanics present before the tilt.
  The tonic JO-driven posture becomes the candidate.
- **`ORDER_MIXED`:** there is no single route. Reported per arm.
- **A `SEPARATES` feature:** an early marker of falling. It is not a cause.

## Limits

- Descriptive replay with 5 FELL arms. Order is not cause. The 10 ms margin cannot resolve
  faster sequences.
- The 20 admitted channels are the only neural route to the body. Unadmitted joints are
  not driven by the brain in this context; their MN activity is read out only.
- The thresholds (5°, 0.05, supports < 3) are engineering choices.
- Step D's limits apply. The tilt is an idealised gravity step, and the JO transduction is
  modelled.
- No balance, corrective, zone-sign or motor-coordinate claim.

## Build and run plan (on approval)

1. Write `protocol.json` with these rules.
2. Write `malecns_backend/embodiment/jo_rollover_timing.py`. It reuses `antennal_gravity_live`
   (`body_angles`, `pools`, `counts`) and `jo_zone_crossing.split`; there are no new
   physics or encoders.
3. Write synthetic tests: onset detection, the baseline, the labels at their boundaries,
   SEPARATES/OVERLAPS, and the integrity failures.
4. Run a plumbing smoke on two LEVEL control pairs only (exit status only; discarded).
5. Commit and push the preregistration, run the replay once (a few minutes), evaluate once,
   and record the results, the handoff and the roadmap.
