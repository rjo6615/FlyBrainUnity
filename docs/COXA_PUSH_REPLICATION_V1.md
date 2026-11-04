# Push response and offset yoke on six new seeds: replication and noise estimate — design (V1)

Designed 2026-11-04, after the offset-yoke results were merged (PR #319). This is the design
only. No code has been written and nothing has run. The protocol, code and tests will be
hash-locked and committed before any arm runs.

**Status 2026-11-04:** preregistered (80ad349, protocol 01a6ea1c…), 55 arms run once, evaluated
once: `INTEGRITY_ACCEPTED`; F and B both `AMPLIFICATION_DIRECTIONAL`, `OFFSETS_DO_NOT_REPRODUCE`,
`FREE_COMMANDS_INCREASE_D`. See `COXA_PUSH_REPLICATION_RESULTS.md`. The text below is unchanged.

## Why this question

Two whole-body coxa results rest on three CNS seeds that disagree strongly.

| Test | Label | Spread over seeds 1–3 |
|---|---|---|
| Push response (`COXA_PUSH_RESPONSE_RESULTS.md`) | LOOP_AMPLIFIES, both directions | R = D(C)/D(N) 1.24–2.04 |
| Offset yoke (`COXA_OFFSET_YOKE_RESULTS.md`) | OFFSETS_DO_NOT_REPRODUCE, both directions | E = D(Y)/D(C) 0.51–1.11; R_Y = D(Y)/D(N) 0.70–1.43 |

The 10 % bars in both tests are engineering resolutions, and there is no noise estimate.
So it is open whether either label is robust, and whether seed 1 (where the yoke matched
C) is an outlier or ordinary scatter. Any further body-level coxa test would inherit the
same problem. This test asks the same questions again on fresh seeds, with the rules fixed
first, and measures the spread.

## Question

On six never-used CNS seeds, do the two earlier labels replicate? And how large is the
seed-to-seed spread of R, E and R_Y?

## Context and arms (unchanged from the two earlier tests)

Every arm uses the push-response context exactly:
- Step C A_ON, the assisted posture;
- the encoder and the 20 v3 channels;
- the Thorax pulse through `external_force_by_transition`: ±1.024 for transitions
  5,000–5,199, zero torque;
- 20,000 physics and 4,000 neural transitions;
- the seed applied as `brain.rng = default_rng(seed)` at attach.

**The arm sets are reused without change.**
- **N:** no coxa channel.
- **C:** the four CONDITIONAL channels, H1, through the labelled hypothesis session. The
  definition sha is dd337259….
- **Y:** the N configuration, with coxa actions 0, 7, 14 and 28 yoked to this run's own
  `C0_s` archive, using the sample n+1 convention. This is the offset-yoke method.

For each seed, the arms run in this order, so each Y arm's source already exists:

> N0, NF, NB, C0, CF, CB, Y0, YF, YB

**Seeds are 7, 8, 9, 10, 11 and 12.** None has been used before: seeds 1–3 were used in
the push-response and yoke tests, and 4–6 in middle-leg C3.

**One reproduction arm runs first.** `REPRO_N0_1` reruns push-response `N0_1`. It must
equal that local raw arm (hash in the push-response report, 849b97cf…) over the whole
run. This confirms the environment has not changed since the earlier tests.

That is 6 × 9 + 1 = **55 fresh-process arms, about 4.5 h**. Each runs once.

The X (H1_FLIP) arms are not repeated. Q_SIGN is not part of this replication.

## Integrity (all required, else `INCONCLUSIVE_INTEGRITY` with no labels)

1. **I1 Completeness.** All 55 arms are COMPLETE, with 20,001 samples and 4,000 ticks.
2. **I2 Reproduction.** `REPRO_N0_1` equals push-response `N0_1` exactly: every sample's
   qpos and commands, and every tick's spikes, uniforms and hair deliveries. The source
   raw arm must match its report hash.
3. **I3 Common random numbers.** Within each seed, all 9 arms have identical per-tick
   uniforms and schedule.
4. **I4 Exact force.** This is the push-response audit, unchanged. `_0` arms apply no
   force.
5. **I5 Channels and bounds.** These are the push-response I5 rules for N and C:
   - the v3 inventory is identical;
   - N arms never change the coxa commands;
   - C arms carry exactly the four channels, the hash and the label, with |offset| ≤ 0.25;
   - other non-v3 commands equal N.
6. **I6 Yoke.** These are the offset-yoke rules for Y:
   - the source is this run's `C0_s`, by recorded hash;
   - `Y0_s` equals `C0_s` over the whole run;
   - the applied action equals the proposal with the four indices from the source, at
     every transition;
   - there is no hypothesis channel.
7. **I7 Prefixes and seeds.**
   - Pushed arms equal their own `_0` arm through physics index 5,000.
   - C arms equal N until their first coxa command.
   - The tick-1 uniforms of seeds 7–12 differ from each other and from seeds 1–3.
   - Every arm records its seed.

**Pulse precondition** (`INCONCLUSIVE_PULSE`, no labels): `NF_s` and `NB_s` must be
resolved perturbations relative to `N0_s` in every new seed and both directions, by the
push-response rule.

## Measures

D is unchanged from both earlier tests. It is the trapezoidal integral of
‖root(pushed) − root(own `_0` control)‖ over stored states 5,201–20,000, in model mm·s,
computed with `coxa_push_response.deviation_integral`.

For each direction p ∈ {F, B} and new seed s:
- **R = D(Cp_s) / D(Np_s)**
- **E = D(Yp_s) / D(Cp_s)**
- **R_Y = D(Yp_s) / D(Np_s)**

**Reported (not labelled).** These pool the new seeds 7–12 with seeds 1–3, labelled as
pooled, never relabelling the earlier tests:
- per direction, the 9-seed median, range, mean and standard deviation of log R, log E
  and log R_Y;
- the standard deviation of D(N) between seeds;
- `metrics.response` for every pushed arm;
- tilt;
- the C-arm loop modulation (mean |c(Cp) − c(C0)| per coxa index, and the number of
  differing transitions).

## Labels (per direction, on the six new seeds only; decided by these rules only)

**Q1: does LOOP_AMPLIFIES replicate?**

| Label | Rule |
|---|---|
| `AMPLIFICATION_REPLICATES` | R ≥ 1.10 in all 6 new seeds (the original bar) |
| `AMPLIFICATION_DIRECTIONAL` | not the above, but R > 1 in all 6 (exact sign test, one-sided p = 1/64) |
| `AMPLIFICATION_NOT_REPLICATED` | otherwise |

**Q2: does OFFSETS_DO_NOT_REPRODUCE replicate?**
- **Q2a** applies the offset-yoke rule unchanged to the six new seeds:
  - `OFFSETS_REPRODUCE` if R_Y ≥ 1.10 and 0.90 ≤ E ≤ 1.10 in all 6;
  - `OFFSETS_PARTLY_REPRODUCE` if R_Y ≥ 1.10 in all 6, but E is outside the band in at
    least 1;
  - `OFFSETS_DO_NOT_REPRODUCE` otherwise.
  The earlier label replicates if Q2a is `OFFSETS_DO_NOT_REPRODUCE`.
- **Q2b** looks at the sign of E:

| Label | Rule |
|---|---|
| `FREE_COMMANDS_INCREASE_D` | E < 1 in all 6 new seeds |
| `FREE_COMMANDS_DECREASE_D` | E > 1 in all 6 |
| `NO_CONSISTENT_SIGN` | otherwise |

  Here "free commands" means the C arms' closed-loop coxa commands after the push,
  compared with the yoked fixed ones.

**Q3: the noise estimate.** This is reported only, not labelled. The spread is described
above. A future protocol may set its bars from it. This one does not change any earlier
bar or label.

## What each outcome means (declared now)

**Q1 = `AMPLIFICATION_REPLICATES` or `AMPLIFICATION_DIRECTIONAL`.** In this assisted
posture and for this pulse, the conditional coxa channels reliably make the body easier
to displace fore-aft. That is a robust body-level property of the current conditional
wiring. It is not a balance contribution.

**Q1 = `AMPLIFICATION_NOT_REPLICATED`.** The earlier LOOP_AMPLIFIES was not robust beyond
its three seeds. It stays recorded as the result for seeds 1–3.

**Q2a = `OFFSETS_DO_NOT_REPRODUCE` with Q2b = `FREE_COMMANDS_INCREASE_D`.** The
amplification depends consistently on the coxa commands being free after the push, not
on posture alone.

**Q2b = `NO_CONSISTENT_SIGN`.** The yoke contrast is dominated by seed-level divergence.
The earlier mechanism finding stays a three-seed result.

In every case:
- no channel, weight, threshold, gain, magnitude or seed changes;
- no coordinate status changes, because this is not an admission test;
- coverage stays 20/42 admitted, +4 conditional;
- the earlier reports, labels and texts are not edited.

## Predictions (expectations, not criteria)

- **Q1:** `AMPLIFICATION_DIRECTIONAL` or `REPLICATES`, moderate confidence. All six
  earlier R values were 1.24 or more.
- **Q2b:** `NO_CONSISTENT_SIGN`, low confidence. E was above 1 in seed 1 and below 1 in
  seeds 2 and 3.

## Limits

- **Position-assisted posture.** This is not independent balance.
- **Seeds vary only stochastic sensory timing.** That is the only variability this
  measures.
- **The sign test needs unanimity.** With 6 seeds, only 6/6 gives one-sided p < 0.05.
  The test cannot tell a moderate effect from none.
- **One engineering pulse,** and only the four fore-aft conditional channels.
- **The reproduction arm checks the environment, not the model.** It confirms the code
  and environment are unchanged. It does not validate the model biologically.
- **Disk.** The raw arms are local, about 37 MB each, so about 2 GB in total.

## Build and run plan (on approval)

1. **Protocol.** Write `docs/evidence/coxa-push-replication-v1/protocol.json`. It holds:
   - the seeds, the arm order and the reproduction reference;
   - the C definition hash and the yoke indices;
   - integrity, the precondition, the measures and the labels.
2. **Code.** Write `malecns_backend/live/coxa_push_replication.py`.
   - It reuses `coxa_push_response` (Trial behaviour, `create_session`, `force_ok`,
     `deviation_integral`, `prefix_equal`) and `coxa_offset_yoke` (`selected_action`,
     `schedule`, `yoke_audit`) by import.
   - Both modules have their seed sets fixed, so the new module provides seed-generic
     Trial subclasses.
   - The two locked modules are not edited.
3. **Tests.** Write `tests/test_coxa_push_replication.py` using synthetic arms. It covers:
   - the arm parsing and the order;
   - each label boundary, including the sign rule;
   - each integrity fault and the pulse precondition;
   - the pooled summary.
4. **Smoke.**
   - Run 1,500 steps of `REPRO_N0_1` and check that it equals the start of push-response
     `N0_1` exactly.
   - Run 5,300 steps of `CF_7` and check the force, inventory and seed.
   - Run 1,500 steps of `Y0_7` against a short `C0_7` smoke archive and check the yoke
     audit. The build allows a short schedule in smoke mode only.
   - Discard all smokes, then commit and hash-lock.
5. **Run.** Each of the 55 arms once (about 4.5 h), then the evaluation once. Record the
   results, the handoff and the roadmap.
