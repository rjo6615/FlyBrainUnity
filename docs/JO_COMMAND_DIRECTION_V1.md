# Antennal gravity sense, Step D4: does the direction of the post-tilt commands matter? (design, V1)

Designed 2026-11-06. This is the design only. No code exists and nothing has run. On
approval, the rules below are copied into `docs/evidence/jo-command-direction-v1/protocol.json`,
hash-locked in code, and committed before any arm runs.

Related documents:
- Step D, `JO_ZONE_CROSSING_RESULTS.md`: 5 of 12 ON DOWN20 arms fell; no OFF arm fell.
- Step D2, `JO_ROLLOVER_TIMING_RESULTS.md`: the falls are late (583–1415 ms) and abrupt.
- Step D3, `JO_COMMAND_YOKE_RESULTS.md`: open loop, the post-tilt ON commands alone make the
  body fall from an OFF posture (POST_ONLY 5/5); the pre-tilt commands do not (0/5). Every leg
  group is necessary and none is sufficient.

## Why this step

D3 found that the change in the post-tilt commands, spread over all six legs, topples the
body. It cannot say **why**. Two readings predict different things:

- **Direction matters.** The JO-driven change pushes the legs in a specific, destabilising
  direction. Then the same change with its sign reversed, or with its pattern scrambled,
  should not topple the body. This would be the first balance-relevant property of the JO
  route: sensing tilt moves the legs the wrong way.
- **Only size matters.** Any change of that size on all six legs topples the body, whatever
  its direction. Then the sign-reversed change should topple it too, and the result says
  nothing about balance.

Two further controls separate size from the specific source:
- **A smaller dose** of the same change (half the size).
- **The post-tilt commands of the 7 ON DOWN20 arms that stayed upright** in Step D, replayed
  the same way (POST_ONLY). If they also topple an OFF-posture body, the fallen arms' commands
  are not special; if they do not, they are.

## Method (reuses the D3 yoke path unchanged)

The context, yoke path, archives and fall rule are those of D3
(`malecns_backend/live/jo_command_yoke.py`):
- Step D trial OFF_DOWN20_s, with JO withheld, the tilt at state 5005 and the source's CNS seed.
- All 42 commanded coordinates come from the declared schedule. The CNS runs but its output
  does not reach the body. Adhesion must be zero.
- The 22 unadmitted coordinates always come from the OFF archive (D3 showed they are identical
  ON/OFF).
- For transitions 0–5004, all 20 admitted coordinates come from the OFF archive (as in D3
  POST_ONLY).

For transitions n ≥ 5005, with Δ(n) = ON(n) − OFF(n) on the 20 admitted coordinates:

| Condition | Admitted command at transition n ≥ 5005 |
|---|---|
| POST_ONLY | OFF + Δ (= ON). Integrity: must equal the D3 POST_ONLY arm exactly. |
| POST_NEG | OFF − Δ (sign reversed on every channel) |
| POST_HALF | OFF + 0.5 Δ (same direction, half the size) |
| POST_SCRAMBLE | OFF + s ⊙ Δ, where s is a fixed ±1 vector over the 20 channels with exactly 10 entries −1, drawn once from `numpy.random.default_rng(20261106)` and written into the protocol before any run |

Every mixed value is clipped to the decoder's joint range [−1.35, 1.30] rad (`MotorSafety`),
the same range the live decoder enforces. The number of clipped values and the largest
per-transition change in a commanded coordinate are reported for every arm; they are not
gates.

**Upright controls.** For each of the 7 ON DOWN20 arms that stayed up in Step D (G1 seeds 20,
22, 23; FLIP seeds 19, 20, 21, 22), POST_ONLY in its own OFF_DOWN20 context. If the ON and OFF
bodies of that source were identical up to the tilt (first qpos difference after state
5005), POST_ONLY is the source arm itself and the control is labelled `DEGENERATE`; it still
runs and is reported, but it is not counted.

## Arms

5 fallen sources × 4 conditions + 7 upright POST_ONLY = **27 fresh-process arms**, about
2.1 h at the D3 rate. Each runs once and is evaluated once.

Archives: 12 ON (5 fallen, 7 upright) and 6 OFF (seeds 19–24), all local raw Step D arms
checked against the Step D report hashes; plus the 5 D3 POST_ONLY arms checked against the D3
report hashes.

## Measures and labels

- **Fall:** tilt ≥ 45° at any stored state 5006–20000 (D3 rule). t_fall in ms after the tilt.
- **Also reported:** peak tilt; mean |Δ| over the post-tilt window per arm (fallen against
  upright sources, descriptive).

Per fallen source:

| Label | Rule |
|---|---|
| `DIRECTION_SPECIFIC` | POST_NEG stays up |
| `DIRECTION_NONSPECIFIC` | POST_NEG falls |
| `PATTERN_SPECIFIC` | POST_SCRAMBLE stays up |
| `PATTERN_NONSPECIFIC` | POST_SCRAMBLE falls |
| `HALF_DOSE_FALLS` / `HALF_DOSE_STAYS_UP` | POST_HALF outcome |

Summary within G1 (3 sources) and within FLIP (2 sources): a label is **CONSISTENT** if it is
the same for every source of that assignment, otherwise **MIXED**. No pooling.

Upright controls: the number of non-degenerate upright POST_ONLY arms that fall, per
assignment, with each arm listed.

## Integrity (all required, else `INCONCLUSIVE_INTEGRITY`, no labels)

- **Z1 Complete:** all 27 arms COMPLETE, with 20,001 samples and 4,000 ticks.
- **Z2 Reproduction:** each fallen-source POST_ONLY arm's qpos equals the D3 POST_ONLY arm's
  qpos at every stored state exactly.
- **Z3 Yoke audit:** every arm's applied 42 commands equal the declared (clipped) schedule
  exactly at every transition; adhesion all zero.
- **Z4 Gravity:** G0 through state 5005, R_y(−20°)·G0 from 5006; no applied wrench; zero
  external and generalized applied maxima.
- **Z5 Sources:** the Step D report, the D3 report, the 18 Step D archives and the 5 D3
  POST_ONLY arms match their recorded sha256; each arm records its source and seed.

## Design expectations (recorded before any arm runs)

- **E1:** POST_NEG stays up in at least 4 of 5 fallen sources (direction matters). A weak
  guess: the falls are abrupt and need all three leg groups, which suggests a specific
  configuration rather than a generic perturbation.
- **E2:** POST_HALF stays up in all 5 (the falls behave like a threshold).
- **E3:** no non-degenerate upright control falls.
- Wrong expectations are recorded as wrong.

## What each outcome means (declared now)

- **`DIRECTION_SPECIFIC` and `PATTERN_SPECIFIC`, upright controls stay up:** the JO-driven
  post-tilt change of the fallen arms has a specific destabilising direction. In this open
  loop, the JO route moves the legs against stability. This is where to look for why sensing
  tilt does not correct it.
- **`DIRECTION_NONSPECIFIC`:** a change of that size topples the body in either direction.
  The falls say nothing about the sign of the JO response; the body is simply near a
  stability margin under the tilt.
- **Upright controls fall:** the post-tilt commands of arms that stayed up also topple an
  OFF-posture body, so in closed loop something else (the pre-tilt posture, or how the
  commands developed with the body) kept those arms up.
- **Mixed:** reported per source.

## Limits

- **Open loop.** The mixed streams never occurred in a closed loop.
- **POST_NEG and POST_SCRAMBLE are not physiological.** No neural activity produced them. They
  are probes of the body's response to the size and direction of a command change.
- **One scramble vector.** One fixed sign pattern is a single sample of "another direction",
  not a distribution.
- **Clipping and steps.** Clipping can shrink a reversed change near the joint range. Every
  POST condition switches at the tilt, putting a step in the commanded positions at the
  gravity step (real in G1, absent in FLIP POST_ONLY); reversed and scrambled changes can
  also exceed the decoder's slew limit. Both are reported.
- Five fallen and seven upright sources; labels per source, no statistics.
- Step D's limits apply: idealised gravity step, modelled JO transduction.
- No balance, corrective-response or biological-cause claim. No motor coordinate status
  change (20/42 admitted, +4 conditional).

## Build and run plan (on approval)

1. Draw the scramble vector, then write `protocol.json` with these rules, the vector and the
   source hashes.
2. Write `malecns_backend/live/jo_command_direction.py`. It reuses D3's `Trial`, `run_arm`
   machinery, archive loading, yoke audit, gravity check and fall rule, adding only the new
   schedules and labels.
3. Write synthetic tests: the schedule per condition, clipping, the degenerate rule, labels,
   and integrity failures.
4. Run a plumbing smoke: one 50-step POST_NEG arm (exit status and yoke audit only; discarded).
5. Commit and push the preregistration, run the 27 arms once in the background, evaluate
   once, and record the results, the handoff and the roadmap.
