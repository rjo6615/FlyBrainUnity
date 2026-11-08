# Antennal gravity Step D5: does the fly fall because the JO senses the tilt? (design)

Designed 2026-11-08. **Status: designed only** (no protocol, code or run). Closed-loop physics
experiment in the Step D context (live CNS output drives the body), with the existing JO C/E
encoder. No change to the engine, weights, mappings, signs, gains, encoder or motor admission.

## Why this step

The rhythm track (V1, R1–R9, L1) found no rhythm source in the live engine without tuning it,
so work returns to balance and posture, which does not depend on a rhythm.

The balance-relevant finding so far comes from the antennal gravity track.
- **Step D (closed loop, 6 seeds):** with the JO gravity sense on, 5 of 12 arms tilted 20°
  nose-down rolled over (G1 3/6, FLIP 2/6). No OFF arm and no LEVEL arm did. This was an
  outcome, not gated, and it has never been tested prospectively.
- **D2–D4 v2 (open-loop yokes of those 5 falls):** the falls are late (0.6–1.4 s after the
  tilt) and abrupt. They need the post-tilt commands on all six legs, at full dose, in a
  specific direction. The pre-tilt posture is neither needed nor sufficient.
- **What the yokes cannot say.** The post-tilt commands in an ON arm come from everything the
  CNS received after the tilt: the JO signal *and* the proprioceptive feedback from a body
  that was already moving differently. So it is unknown whether the falls need the JO to
  *sense the tilt*, or whether a JO input that carries no tilt information would also topple
  the fly.

D5 asks, in the closed loop:

> **Q1.** On fresh seeds, does a fly with the JO gravity sense on roll over after a 20°
> nose-down tilt more often than a fly with it off? (Step D's unplanned observation, now
> preregistered.)
>
> **Q2.** If the JO input is frozen at its value at the moment of the tilt, so it carries no
> information about the tilt, does the fly still roll over?

Q2 is a matched intervention. A frozen arm and its sighted partner (same type, same seed) are
identical up to the tilt, because gravity is identical before it, so they must match exactly
until then (integrity Z2). After the tilt, the only difference is whether the JO input follows
the sensed tilt.

## Conditions (declared)

- **Context:** Step D's `Trial` unchanged (push-response N context, assisted posture, hair
  plates, the 20 admitted coordinates, adhesion and external force as in Step D). Each arm runs
  20,000 physics steps (4,000 neural ticks). Gravity is G0, then R_y(−20°)·G0 from stored
  state 5006 (DOWN20, Step D's tilt).
- **JO types:** OFF (JO withheld), G1 and FLIP (Step D's zone assignments), each **sighted**
  (Step D's encoder, unchanged).
- **FROZEN** (new, an engineering probe, not physiology): the same encoder and zone
  assignment up to the tilt. After it, every JO population receives the rate it received at
  the last neural tick before gravity is rotated, held constant to the end. Delivery (Poisson
  forced spikes through `set_external_drive`) is unchanged. Only the rate stops following the
  encoder.
- **Seeds:** CNS seeds 25–36 (fresh; 1–24 are used by earlier live steps).

| Condition | JO input after the tilt | Arms |
|---|---|---|
| OFF_DOWN20 | withheld | 12 |
| G1_DOWN20 | sighted G1 | 12 |
| G1F_DOWN20 | frozen at the G1 pre-tilt rate | 12 |
| FLIP_DOWN20 | sighted FLIP | 12 |
| FLIPF_DOWN20 | frozen at the FLIP pre-tilt rate | 12 |
| REPRO | Step D's G1_DOWN20_19, rerun | 1 |

**61 arms**, each in a fresh process, about 4.4 h at Step D's measured cost (~4.3 min per arm).
No LEVEL arms are run. Step D showed that no LEVEL arm rolled over, and LEVEL cannot separate
sighted from frozen, because the JO input barely changes.

## Outcome measure

- **Fall:** body tilt relative to the recorded gravity reaches 45° at any stored state after
  5005. This uses `jo_command_yoke.outcome` (Step D's `body_angles`) unchanged. Also reported:
  the fall time and the peak tilt.
- Arms that do not fall by the end are censored at the end of the run (about 1.5 s after the
  tilt). Step D's falls all happened inside that window.

## Criteria (declared)

**Q1, replication (sighted vs OFF).** Pool the sighted arms (G1 + FLIP, 24) and compare them
with OFF (12) using a one-sided Fisher exact test (sighted falls more).

| Label | Rule |
|---|---|
| `JO_FALLS_REPLICATED` | p ≤ 0.05 |
| `JO_FALLS_NOT_REPLICATED` | sighted fall fraction ≤ OFF fall fraction |
| `JO_FALLS_WEAK` | otherwise |

**Q2, frozen vs sighted (paired by type and seed, pooled over G1 and FLIP; 24 pairs).**
- Let b be the pairs where sighted falls and frozen does not.
- Let c be the pairs where frozen falls and sighted does not.
- Use an exact binomial (sign) test on b of b + c at 0.5.

| Label | Rule (first matching row) |
|---|---|
| `UNDERPOWERED` | fewer than 5 sighted falls in total |
| `RESPONSE_NEEDED` | b > c and one-sided p ≤ 0.05: freezing the JO input prevents falls |
| `RESPONSE_PROTECTIVE` | c > b and one-sided p ≤ 0.05: freezing the JO input causes falls |
| `RESPONSE_NOT_NEEDED` | c ≥ b: frozen arms fall at least as often |
| `INDETERMINATE` | otherwise |

**Reported, not gated:**
- the same Q2 counts per type (G1 and FLIP separately);
- frozen vs OFF (one-sided Fisher);
- fall times and peak tilts;
- JO d and rates after the tilt (sighted) and the held rates (frozen);
- for each pair, the first state where the bodies differ (it must be after 5005).

## Integrity (declared now)

- **Z1, completeness:** 61 arms, each with 20,001 stored states and 4,000 neural ticks.
- **Z2, matched until the tilt:** each frozen arm equals its sighted partner exactly (qpos at
  every stored state, and fired neurons at every neural tick) through state 5005. If not, the
  step is `INCONCLUSIVE`.
- **Z3, freeze audit:** in frozen arms, every JO set's delivered rate after the tilt equals the
  sighted partner's rate at the last tick before it, at every tick. Sighted arms' rates equal
  the encoder output at every tick.
- **Z4, gravity and forces:** G0 through state 5005, then R_y(−20°)·G0. No applied wrench.
  This is Step D's I5 check.
- **Z5, OFF:** the JO set is withheld at every tick (Step D's rule).
- **Z6, reproduction (hard gate):** REPRO equals Step D's archived G1_DOWN20_19 exactly (qpos
  at every state and fired neurons at every tick). It fell in Step D. If it does not match
  exactly, the step is `INCONCLUSIVE`.
- **Z7, sources:** the hashes of Step D's protocol, module and report, the encoder module and
  the engine files match the values recorded in the protocol.

## Expectations (recorded now)

- **E1:** Q1 is `JO_FALLS_REPLICATED` (Step D: 5/12 vs 0/12).
- **E2:** pooled Q2 is `RESPONSE_NEEDED`. D3 and D4 v2 show the falls follow from the
  post-tilt commands in a specific direction.
- **E3 (per type, reported):** FLIP frozen falls less often than FLIP sighted, because the
  FLIP fall follows the E-onset response at the tilt. G1 frozen falls at least as often as
  G1 sighted, because G1's tilt response is weak (E goes off) and freezing keeps E on.

Wrong expectations are recorded as wrong.

## What each outcome means (declared now)

- **Q1 `JO_FALLS_REPLICATED`:** with the modelled JO gravity sense on, the closed-loop fly is
  *less* stable under this tilt than without it. The track's working sense is destabilising,
  not corrective. `NOT_REPLICATED` or `WEAK` would mean Step D's 5/12 does not hold up on
  fresh seeds, and D2–D4's dissection described a rare event.
- **Q2 `RESPONSE_NEEDED`:** the falls need the JO input to follow the tilt. Sensing the tilt,
  as currently transduced and wired, drives the fly over. The next question would be which
  route carries that response (for example, Step D's E-onset path via DNp73/DNbe001), in a
  separate design.
- **Q2 `RESPONSE_NOT_NEEDED`:** the falls do not need the JO to sense the tilt. A JO input
  that only sets the pre-tilt state is enough. The instability would then belong to the
  JO-on operating state, not to a tilt response.
- **Q2 `RESPONSE_PROTECTIVE`:** the JO response to the tilt helps keep the fly up. That would
  be the first evidence of a stabilising, neurally mediated tilt response. It would need its
  own replication before any balance claim.
- **In no case** does D5 establish balance, a corrective reflex or a biological role for JO
  zones. FROZEN is a probe; real JO neurons do not freeze.

## Limits

- One tilt (20° nose-down, a step change) and one context (assisted posture, Step D).
- Modelled JO transduction (Step B's encoder) and Step D's two zone assignments.
- 12 seeds per condition. Fall is a binary outcome at a fixed 45° threshold, censored at the
  end of the run.
- FROZEN holds the rate, not the spike train. The JO still receives Poisson input at that rate.
- The pre-tilt state differs between JO types and OFF. Q2 controls for this within a type;
  Q1 does not.
- Closed loop, so any difference after the tilt compounds. Divergence is an outcome, not an
  exclusion.
- Raw arms stay local and untracked; their sha256 values go into the report.
- Motor coordinates are unchanged (20/42 admitted, +4 conditional).

## Build and run plan (on approval)

1. `docs/evidence/jo-frozen-response-v1/protocol.json`: conditions, seeds, criteria, source and
   engine hashes, expectations.
2. `malecns_backend/live/jo_frozen_response.py`. It reuses:
   - `jo_zone_crossing.Trial` (bind, tilt, JO step), extended only by the freeze;
   - `jo_command_yoke.outcome` (fall);
   - Step D's integrity checks for gravity and OFF withholding.
3. Unit tests: the freeze rule (rate held from the last pre-tilt tick), the Q1/Q2 labels on toy
   counts, and the exact tests.
4. A plumbing smoke: one frozen arm with a non-protocol seed, stopped before the tilt plus 50
   steps. It is discarded and disclosed, and only its exit status and freeze audit are read.
5. Commit and push the preregistration. Run once in the background, evaluate once, then record
   the results, handoff and roadmap.

## Build-time notes (before any protocol arm)

- No amendments to the design's conditions, seeds, criteria or expectations. The protocol is
  `docs/evidence/jo-frozen-response-v1/protocol.json` (sha a1ab56a7…).
- **Freeze rule as built.** `Freeze` wraps the Step B encoder. Every encode while the trial's
  tilt event is unset is delivered and stored. From the first encode after gravity is rotated,
  the stored output (rates and recorded d) is delivered instead, and the live d is recorded
  alongside (`jo_live_d`). Sighted arms pass through the same wrapper, which never holds.
  REPRO runs `jo_zone_crossing.run_arm('G1_DOWN20_19')` unchanged.
- **Reproduction check as built.** Z6 uses `coxa_offset_yoke.reproduces` (qpos and commands at
  every state; fired, RNG uniforms and hair-plate delivery at every tick) plus JO delivery. That
  is stricter than the design's qpos-and-fired wording.
- **Raw arms.** They are written to the main checkout's untracked
  `docs/evidence/jo-frozen-response-v1/run/`, beside Step D's archives. `console.txt` and
  `report.json` are committed.
- **Plumbing.**
  - The smoke ran with the protocol lock stubbed out (it was not yet written): G1F, seed 0
    (not a protocol seed), 5,055 steps (the tilt plus 50), 139 s. It was discarded.
  - Only these were read: exit status (SMOKE, no error); 1,000 pre-tilt ticks never held and
    11 post-tilt ticks all held at the last pre-tilt rates; JO delivery present; seed 0 and
    type G1F recorded. The body and the fall measure were not inspected.
  - The Step D reference archive's sha (7392cc15…) was checked.
  - 6 new tests pass (20 with the Step D and D3 tests).
