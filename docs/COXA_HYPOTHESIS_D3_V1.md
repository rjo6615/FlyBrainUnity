# Coxa hypothesis D3 — closed-loop resistance-reflex test, design

Status: **design only**. No code and no run. This refines Step D3 of
[the track design](COXA_HYPOTHESIS_TRACK_V1.md) using the
[D1/D2 results](COXA_HYPOTHESIS_D1_D2_RESULTS.md). Its labels, bars and arms are
the ones fixed there, and nothing below changes them. Additions are
implementation detail, integrity checks and descriptive outputs, all fixed
before any D3 code runs. The protocol JSON is hash-locked and committed with the
code, before the single run.

## Question (unchanged)

The loop runs hair plate → CNS → coxa joint → hair plate. When it is closed with
the rule-built H1 binding, does it behave as a resistance reflex? That is, does the
coxa move **posteriorly** where hair plates fire, while the sign-flipped control
moves it anteriorly? Does H1 fit better than H2? The labels are
`RESISTANCE_CONSISTENT`, `SIGN_ONLY_CONSISTENT` or `NOT_CONSISTENT`, and
`H1_FAVOURED`, `H2_FAVOURED` or `NOT_DISTINGUISHED`.

## Arms

All four arms use the same setup as Step C **A_ON**: assisted posture (no row
release), hair plates delivered, the same seed, the same external schedule, the
Step B encoder, 20,000 physics steps / 4,000 neural ticks and the
520–2000 ms window. Each arm runs once, in its own fresh process, in this order.

| Arm | Session | Coxa channels |
|---|---|---|
| C0 | Step C `create_session`, unchanged | none |
| H1 | hypothesis session | D2 `channels.H1` (13) |
| H1_FLIP | hypothesis session | D2 `channels.H1_FLIP` (13) |
| H2 | hypothesis session | D2 `channels.H2` (8) |

D2 recorded `h2_identical_to_h1 = false`, so H2 runs.

## Implementation (reuse, nothing competing)

- **Adapter:** the Step C `Trial` is reused unchanged for arm A_ON. It provides
  the encoder, the input boundary, RNG checks and the motor readout check. There
  is no new sensory code.
- **Channel definitions:** these are loaded verbatim from
  `docs/evidence/coxa-hypothesis-v1/run/result.json` after a sha256 check
  (ef2fbd…). They are never re-derived.
- **Hypothesis session:** `live/coxa_hypothesis_loop.py` builds a derived
  copy of the v3 protocol/records/table.
  - `v3.validate_v3` must pass on the copy first.
  - Only the H coxa rows are then marked `neural_motor_admission`, with
    `motor_status = COXA_HYPOTHESIS_<arm>`, `handling = baseline_plus_neural_contribution`
    and the D2 coordinate sign. No v1/v2/v3 object is mutated.
- **Gate and admission assertion:** these are new, but each is the v3 function's
  logic over the exact inventory `V3_MOTOR + H names`. They refuse any other
  nonzero output. The existing enabled/disabled condition boundary is unchanged.
- **Kernel path:** the kernel path is unchanged. It passes
  `supplemental_motor_channels = v3.SUPPLEMENTAL_MOTOR_CHANNELS ∪ H` and reuses the
  existing observer (40 ms), activation (17 Hz half), decoder modes, slew
  (4 rad/s), and `safe_contribution_bound`. A read-only probe showed this bound gives
  0.25 rad for coxa joints, whose metadata resolves to ±1e6.
- **v3 itself is untouched:** it keeps refusing coxa admission, so the 20-channel
  runtime and every earlier experiment stay as they were.

## Preflight (before the C0 arm; failure means no run, recorded as `PREFLIGHT_FAILED`)

- **P1:** the D2 result hash and status (`D1_D2_READY`) match.
- **P2:** the kernel's resolver accepts `v3 supplemental ∪ H` for each H arm. No
  coxa body ID overlaps any historical (tibia/femur) channel's dense indices.
- **P3:** no coxa readout neuron is in the 444-neuron external schedule.
- **P4:** the saved Step C A_ON raw file is present and its hash equals the
  committed Step C report (`arm_sha256.A_ON`, 8c2d90…).
- **P5:** the hypothesis derivation leaves the v3 contract valid for the
  v3-only rows. The derived table differs from v3 only in the declared H rows.

## Integrity (all must pass, else `INCONCLUSIVE_INTEGRITY`, with no Q3/Q4 labels)

- **I1:** every arm is COMPLETE, with no kernel instability flag and no
  unauthorized-output error.
- **I2:** per-tick `uniforms_sha256` is identical in all arms.
- **I3:** C0 equals the saved Step C A_ON in `fired`, `uniforms_sha256`,
  `hair_delivered` and `qpos` at every tick/sample. This is the reproducibility check.
- **I4:** every arm commands the same 20 v3 channel indices with the same definitions.
  - In H arms, |commanded − baseline| ≤ 0.25 rad + 1e-9 on every H joint at every
    sample.
  - Joints outside V3 + H are commanded at baseline exactly.
- **I5:** each H arm is identical to C0 (qpos, commanded joints, fired) up to the
  first sample where an H joint's command differs from baseline. Divergence
  before that is a failure.

## Measures and labels (from the track design, unchanged)

- **Firing legs:** legs whose C0 window-mean hair-plate rate is > 0 Hz. Step C
  suggests LF, RF, LH and RH, but the set is taken from C0, not assumed. Middle legs
  are reported but excluded.
- **Primary measure:** per firing leg, Δf = window-mean `hair_forward` (the Step B
  coxa forward component, recorded per tick) in the arm, minus the same in C0.
  A posterior shift means Δf ≤ −0.02.
- **Q3:**
  - `RESISTANCE_CONSISTENT` if H1 shifts posterior in at least 3 firing legs **and**
    H1_FLIP has Δf ≥ +0.02 in at least 3 of the same legs.
  - `SIGN_ONLY_CONSISTENT` if only the H1 part holds.
  - Otherwise `NOT_CONSISTENT`.
  - If fewer than 3 firing legs exist, Q3 is `NOT_TESTABLE`.
- **Q4:** count of firing legs with a posterior shift, H1 vs H2:
  `H1_FAVOURED`, `H2_FAVOURED` or `NOT_DISTINGUISHED` (equal counts).

**Descriptive (not gated):**
- Per-leg Δf time courses.
- Hair-plate rate and delivered events.
- Coxa MN rates (posterior/anterior sets from Step C).
- Per-channel commanded offset, saturation (|offset| = 0.25) and slew-limited
  time fraction.
- Coxa joint angles.
- Body tilt.
- First divergence state vs C0.

## Predictions recorded before running (from D2, so a reader can check them)

- **H1 swing paths:** posterior rotators drive `+Coxa` (posterior) in LF, LM, LH,
  RF and RM, and `−Coxa_roll` in RH. D1 shows RH `+Coxa_roll` moves the tip
  anterior-outward, so `−Coxa_roll` is posterior-inward. The LH adductor is on
  `+Coxa_roll`, which is also posterior-inward. Middle legs have silent encoders
  and are excluded.
- **Front legs:** the main hair-plate target (remotor/abductor) is bound to
  Coxa_yaw, which is sideways, not posterior. A front-leg posterior shift then
  depends on posterior-rotator recruitment, which Step A did not show to be
  dominant there. **Front-leg failures are a live possibility, not a defect.**
- **H2:** it has no posterior-rotator pool. Its posterior paths are front-leg
  remotor/abductor (on roll, sideways) and middle-leg remotor/abductor (on `+Coxa`,
  excluded legs). In firing legs, the front promotor `−Coxa` is anterior. The hind
  adductors (LH `+Coxa_roll`, RH `−Coxa_roll`) are posterior-inward, so H2 can
  shift the hind legs posteriorly only if hair plates recruit adductors. H2 is
  therefore expected to show fewer posterior shifts than H1, but not necessarily
  none.

These are expectations, not acceptance criteria. Both a match and a mismatch are
recorded as they come out.

## Interpretation limits

- One seed, assisted posture and offset-on-servo actuation. A shift is a setpoint
  shift held by the posture servo, not muscle force or free posture.
- An H1 pass shows consistency of the whole chain with one published reflex. It
  does not validate the binding, admit any coordinate, or show balance. Motor
  coverage stays **20/42 proven**.
- The D2 near-ties (front roll vs yaw, RH roll vs Coxa) mean small geometric
  differences decide some bindings. D3 does not revisit them.
- H2 as preregistered drops all rotators, so it tests "bodymap labels without
  rotators", not a twist reading.

## Cost and outputs

- **Cost:** four arms of about 5 minutes each, plus evaluation.
- **Raw arms:** stay local, uncommitted (about 40 MB each), as for Step C.
- **Committed outputs:** the protocol, `report.json` (with arm hashes), `console.txt`
  and a results write-up. After the result, an optional local Unity replay of
  C0/H1/H1_FLIP via the existing replay tooling, if wanted.
