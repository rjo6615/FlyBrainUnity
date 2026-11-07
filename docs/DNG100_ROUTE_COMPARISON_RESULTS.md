# Rhythm, Step R4 (structural route comparison into the core): results

Run 2026-11-06 under the preregistered protocol
`docs/evidence/dng100-route-comparison-v1/protocol.json` (sha 7c173a35…). The protocol, module
and tests were committed and pushed in 7a5a8ac before any protocol computation.
- **Run:** one command, 2.5 s, run once and evaluated in the same process.
- **Output:** `docs/evidence/dng100-route-comparison-v1/run/result.json` (sha f2184542…), with
  `console.txt` alongside.
- **Design:** `DNG100_ROUTE_COMPARISON_V1.md` (no amendments; build notes disclose one load
  check and one test-expectation correction).

**Structure only**, on R1's signed 2,111-neuron network. No simulation, body or physics.

## Verdict: SIGNATURE_DNG100_LIKE_RHYTHMIC

- **One metric separates** the three RHYTHMIC DNs from the 17 others: `twohop_E1`, the net
  two-hop synaptic drive into E1 (p = 2/1,140 = 0.0018, threshold 0.0042). The three RHYTHMIC
  DNs have the three largest values of all 20 controls.
- **DNg100_L is beyond them on the rhythmic side:** its `twohop_E1` (25,309) is larger than any
  control's.
- No other metric reached the threshold (smallest other p: `out_weight` 0.012).

| Metric | p | RHYTHMIC (1087 / 129181 / 130496) | NONRHYTHMIC median | DNg100_L |
|---|---|---|---|---|
| **twohop_E1** | **0.0018** | 17,756 / 18,180 / 6,726 | 0 | **25,309** |
| out_weight | 0.012 | 901 / 2,731 / 1,927 | 407 | 1,641 |
| out_degree | 0.019 | 37 / 108 / 66 | 20 | 70 |
| direct_mn | 0.030 | 0 / 163 / 211 | 0 | 0 |
| core_focus | 0.032 | 0.014 / 0.015 / 0.025 | 0.002 | 0.016 |
| core_hops | 0.12 | 2.33 / 1.67 / 2.00 | 2.33 | 2.00 |
| direct_E1 | 0.15 | 0 / 6 / 0 | 0 | 0 |
| twohop_I1 | 0.15 | 0 / 217 / 688 | 0 | 30 |
| i1_share | 0.23 | 0 / 0.009 / 0.045 | 0.21 (n = 11) | 0.0011 |
| twohop_E2 | 0.50 | 35 / 3,749 / −801 | 0 | 1,112 |
| direct_E2, direct_I1 | 1.0 | all 0 | 0 | 0 |

Synapse-count units for weights (count ≥ 5, signed); `i1_share` NaN for 6 controls with no
excitatory two-hop drive into the core (excluded from that test as declared).

| Expectation | Outcome |
|---|---|
| X1 (NO_SIGNATURE) | **wrong**: `twohop_E1` separates |
| X2 (DNg100 out_degree > every RHYTHMIC DN's) | **wrong**: 70 vs 37 / 108 / 66 (DNg75_R is higher) |
| X3 (DNg100 i1_share > every RHYTHMIC DN's) | **wrong**: 0.0011 vs 0 / 0.009 / 0.045 (above DNp09_R only) |

**Integrity.** All pass:
- I1: hashes; R1 network body-ID hash; control list; the group rule returned exactly
  1087, 129181, 130496.
- I2: DNg100_L's 13 two-hop intermediates (by core cell) equal R2's exactly.
- I3: 4 new tests passed (26 together with R1, R1b, R2 and R3).
- I4: 21 DNs × 12 metrics complete.

## Reported, not gated

- **Identities** (cache instance names): 1087 DNp09_R (body 11177); 129181
  DNg75(hb1874217622)_R (body 520300); 130496 DNa02_L (body 523769).
- **Shared intermediates.** No intermediate is shared by all three RHYTHMIC DNs.
  - DNp09_R shares 4 with DNg100_L (dense 46, 122053, 129181, 145002), including DNg75_R itself.
  - DNg75_R shares 3 with DNg100_L (46, 4559, 122053).
  - DNa02_L shares none: its routes into the core run through a separate set of 8 cells.
- **DNg75_R** is one of DNg100_L's intermediates to E1 (known from R2); no other RHYTHMIC DN is.
- **I1 access.** DNg100_L's two-hop drive into the core is almost all onto E1 (25,309) with
  little onto I1 (30). DNg75_R and DNa02_L have more two-hop drive onto I1 (217, 688).
- **Sizes.** s_R1 / s_VNC / ρ: DNg100_L 30.8 / 22.7 / 1.35; DNp09_R 9.2 / 3.7 / 2.49; DNg75_R
  17.2 / 9.7 / 1.78; DNa02_L 28.9 / 16.7 / 1.73.

## What this means (per the design's declared outcomes)

- **Declared consequence of SIGNATURE_DNG100_LIKE_RHYTHMIC.** The rhythm-driving controls
  differ from the other controls on these route features (strong two-hop drive into E1), but
  DNg100_L looks like them on that feature, more so. The difference between DNg100's steady
  output and these DNs' oscillation is therefore not explained by these two-hop route features;
  the design pointed to network dynamics, such as R2's all-or-none ignition.
- **What the separating metric does say.** Strong two-hop drive into E1 is shared by every
  DN that drove the core oscillation in R3, and DNg100_L has the most of it. That fits the core
  being E1-led. It does not show that DNg100's larger drive is the cause of its steady state;
  that would be a dynamics question.
- **Not separating** (descriptive only, not tested): DNg100_L's near-absence of two-hop drive
  onto I1, and its lack of direct MN contacts, compared with DNg75_R and DNa02_L.
- **Next.** As declared, the next step is the preregistered control-DN rhythm test (core
  silencing, both size versions), which would establish whether the oscillation is real and
  needs E1, E2 and I1.

## Limits

- **Three RHYTHMIC DNs**, from an unplanned R1SIZE-only R3 observation without core silencing.
- **Structure only:** two-hop routes in R1's isolated network; longer routes and dynamics are
  not captured.
- **Signed synapse counts** with R1's transmitter signs; no physiology.
- **Twelve chosen metrics.** One separated; several others had p 0.01–0.03, which does not meet
  the corrected threshold and is not claimed.
- **Wiring is identical in both size versions**, so R4 cannot explain why the oscillation
  appeared only with R1's sizes.
- **No body or physics.** Motor coordinates are unchanged (20/42 admitted, +4 conditional).
