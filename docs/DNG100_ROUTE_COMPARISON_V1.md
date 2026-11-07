# Rhythm, Step R4: how do DNg100's routes into the core differ from the rhythm-driving DNs'? (design)

Designed 2026-11-06. **Status: designed only (no protocol, code or run).** Structure only: no
simulation, no body or physics.

## Why this step

- **R3** (`DNG100_ENGAGED_RHYTHM_RESULTS.md`) found no DNg100 rhythm with the E1–E2–I1 core
  engaged. DNg100 pushed the core into saturated steady states in both size versions.
- **Unplanned observation in R3** (R1SIZE only, no silencing): three of R1's 20 control DNs
  drove a front-left MN rhythm at 13–14 Hz, with the E1, E2 and I1 traces oscillating too:
  DNg75_R (dense 129181, score 0.97), DNa02_L (130496, 0.95) and DNp09_R (1087, 0.52). These
  runs recruited 127–184 neurons.
- R3's declared outcome said any further step should be a structural comparison, not tuning.

R4 asks:

> **On R1's network wiring, do the DNs that drove a core oscillation in R3 reach E1, E2 and I1
> differently from the DNs that did not, and on which side of that difference does DNg100_L
> fall?**

**Status of the premise (disclosed).** The rhythmic group comes from an unplanned observation
that has not been tested for core dependence, and that disappeared with cord-only sizes. R4
does not establish that phenomenon. It is a cheap, deterministic structural description meant
to generate hypotheses. Wiring is the same in both size versions, so R4 cannot by itself
explain why the oscillation appears only with R1's sizes; sizes are reported, not gated.

**Already known (disclosed).**
- R2 listed DNg100_L's two-hop intermediates to each core cell; DNg75_R (129181) is one of E1's.
- R1, R2 and R3 established that DNg100_L reaches E1 in two hops.
- No control DN's routes, weights or degrees have been computed or inspected.

## Groups (declared rule; no choice after seeing structure)

| Group | Rule | Expected members |
|---|---|---|
| RHYTHMIC | R1's control DNs with R3 `arms.R1SIZE.controls[k].score ≥ 0.5` (R3's C1 threshold) | 1087, 129181, 130496 |
| NONRHYTHMIC | R1's other control DNs | the remaining 17 |
| DNG100 | DNg100_L (dense 10045) | 1 |

The rule is applied to R3's committed `result.json` at run time. If it does not return exactly
the three expected members, the run stops as INCONCLUSIVE.

## Metrics (fixed now; M = 12 gated)

All on R1's signed matrix `W[post, pre]` (sign × synapse count, count ≥ 5, within the 2,111-neuron
network), from stimulated DN `s`. Core cells c ∈ {E1, E2, I1}.

| # | Metric | Definition |
|---|---|---|
| 1–3 | `direct_E1`, `direct_E2`, `direct_I1` | W[c, s] |
| 4–6 | `twohop_E1`, `twohop_E2`, `twohop_I1` | Σ_k W[c, k]·W[k, s], over all network k ≠ s, c (net signed) |
| 7 | `i1_share` | excitatory two-hop drive to I1 ÷ the sum over E1, E2, I1; "excitatory" = paths with both edges positive. NaN if the sum is 0 |
| 8 | `core_focus` | excitatory two-hop drive into the three core cells ÷ s's excitatory two-hop drive into all network cells. NaN if 0 |
| 9 | `out_degree` | number of network cells j with W[j, s] ≠ 0 |
| 10 | `out_weight` | Σ_j \|W[j, s]\| |
| 11 | `direct_mn` | Σ W[m, s] over the 68 front-left MNs |
| 12 | `core_hops` | mean unweighted hop distance from s to E1, E2, I1 (R2's `hops`; inf if unreachable) |

**Reported only (not gated)**
- Each DN's two-hop intermediates per core cell, with body IDs and names; the overlap among the
  RHYTHMIC DNs' intermediates, and with DNg100_L's.
- Whether any RHYTHMIC DN is itself one of DNg100_L's intermediates (129181 is known to be).
- Each DN's size in both versions (s_R1, s_VNC) and ρ = s_R1/s_VNC.
- Each DN's body ID, name and transmitter.

## Criteria (declared now)

**Separation (per metric).** Exact two-sided permutation test of the Mann–Whitney statistic
(mid-ranks for ties) over all C(20, 3) = 1,140 assignments of 3 RHYTHMIC labels to the 20
control DNs. A metric **separates** if p ≤ 0.05/12 (0.00417). With no ties, that requires
the RHYTHMIC rank sum to be one of the top two (or bottom two) possible values. NaN values are
excluded from that metric's test, which is then run on the remaining assignments; a metric with
any NaN in RHYTHMIC does not separate.

**DNg100_L placement (per separating metric).**
- **Nonrhythmic side:** DNg100_L's value lies strictly outside the RHYTHMIC range, in the
  direction of the NONRHYTHMIC median.
- **Otherwise:** within the RHYTHMIC range or beyond it on the rhythmic side.

**Verdict**

| Verdict | Rule |
|---|---|
| `SIGNATURE_DNG100_DIFFERS` | ≥ 1 metric separates, and DNg100_L is on the nonrhythmic side of at least one |
| `SIGNATURE_DNG100_LIKE_RHYTHMIC` | ≥ 1 metric separates, and DNg100_L is not on the nonrhythmic side of any |
| `NO_SIGNATURE` | no metric separates |
| `INCONCLUSIVE` | an integrity failure |

## Integrity (declared now)

- **I1 sources:** file hashes (R1, R2 and R3 modules; R3's `result.json` sha 099e42a7…); R1's
  network body-ID hash (cdcfcd23…); R1's control list unchanged; the group rule returns exactly
  the expected three.
- **I2 structural reproduction (hard gate):** DNg100_L's two-hop intermediates per core cell
  must equal R2's `result.json` exactly.
- **I3 tests:** metric functions on a toy W; the exact permutation test (known separation and
  tie cases); placement and verdict.
- **I4 completeness:** 21 DNs × 12 metrics, all computed (NaN or inf allowed only where
  defined above).

## Expectations (recorded before any R4 computation)

- **X1:** `NO_SIGNATURE`. With only 3 RHYTHMIC DNs and a strict threshold, I expect no metric
  to separate.
- **X2:** DNg100_L's `out_degree` exceeds every RHYTHMIC DN's (diffuse output, consistent with
  R2's all-or-none ignition).
- **X3:** DNg100_L's `i1_share` exceeds every RHYTHMIC DN's (consistent with R3's I1-dominated
  VNCSIZE state).

Wrong expectations are recorded as wrong.

## What each outcome means (declared now)

- **SIGNATURE_DNG100_DIFFERS:** a candidate structural difference between how DNg100 and the
  rhythm-driving DNs reach the core. It is a hypothesis about route, not a cause: testing it
  needs a preregistered simulation, starting with whether the control-DN oscillation is real
  and needs E1, E2 and I1.
- **SIGNATURE_DNG100_LIKE_RHYTHMIC:** the rhythm-driving DNs differ from the others, but
  DNg100 looks like them on those metrics. The difference would then lie in network dynamics
  (such as R2's ignition), not in these route features.
- **NO_SIGNATURE:** these route features do not distinguish the rhythm-driving DNs, at this
  sample size. This does not show that structure is irrelevant.
- **In every case:** the next step would be the preregistered control-DN rhythm test (core
  silencing, both size versions). R4 shows no rhythm, walking or biological claim, and changes
  no engine, mapping or motor admission.

## Limits

- **Three RHYTHMIC DNs**, from an unplanned R1SIZE-only observation without silencing.
- **Structure only:** two-hop routes in R1's isolated network; longer routes and the network's
  recurrent dynamics are not captured.
- **Weights are signed synapse counts**, with R1's transmitter signs; no physiology.
- **Twelve chosen metrics:** others could separate where these do not.
- **No body or physics.** Motor coordinates are unchanged (20/42 admitted, +4 conditional).

## Build and run plan (on approval)

1. `docs/evidence/dng100-route-comparison-v1/protocol.json`: groups rule, metrics, criteria,
   hashes, expectations.
2. `malecns_backend/embodiment/dng100_route_comparison.py`. It reuses:
   - `dng100_rate_model`: Model, CELLS, dense, control_dns;
   - `dng100_recruitment_map`: hops, intermediates, cord_only_sizes.
3. Unit tests (I3). No plumbing run is needed beyond loading the network; any load check will
   print no metric values and will be disclosed.
4. Commit and push the preregistration. Run once (seconds), evaluate in the same process, and
   record the results, handoff and roadmap.
