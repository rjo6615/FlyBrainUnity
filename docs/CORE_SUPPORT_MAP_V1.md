# Engine fidelity Step F2: what outside the leg network keeps DNg100_L's core active? (design)

Designed 2026-11-10. **Status: run 2026-11-10: NEEDED_NOT_SUFFICIENT** (BRAIN, VNC and AN each needed; no group
enough alone). See `CORE_SUPPORT_MAP_RESULTS.md`. This is a neural-only
simulation (no body, no physics) in the live, calibrated whole-CNS LIF engine. It does not change
the live engine, its calibration, weights, signs, mappings or motor admission. Lesions exist only
in model copies.

## Why this step

- **F1's declared next step cannot be done locally.** F1 named a desk review of whether the core
  cells (E1, E2, I1) spike or are graded. No local source covers their physiology: the repository
  docs and textbook mention graded neurons only for the lamina and APL. The project is local-only,
  so that review would have no evidence to review. It stays open, not done.
- **F1's unplanned observation is fully local and testable.**
  - In the live engine, DNg100_L at 100 Hz engages E1 and E2 in 8 of 8 seeds (about 26 and 41 Hz),
    with about 2.3 % of the CNS active. Its motor output stays tonic.
  - Restricting the engine to R1's 2,111-neuron front-left network abolishes that engagement, and so
    does restoring full inhibition.
  - Nearly all of E1's direct input is inside the network, so what is lost is upstream or recurrent.
- **Why it matters.** This is the only core engagement found in the live engine. If it comes from a
  specific circuit outside the leg network, that circuit can be named and studied. If it comes from
  a broad whole-CNS state, then motor-network activity in the live engine, including the
  destabilising responses in the balance track, depends on global state rather than specific routes.
  That would change how the balance work should be approached.

F2 asks:

> Which part of the CNS outside R1's network does DNg100_L's core engagement need, and is any one
> part enough by itself?

## Groups (declared now, by superclass, outside R1's network)

R1's network (2,111 neurons, membership sha cdcfcd23…) is always kept. The rest of the CNS is split
into seven disjoint groups that together cover it:

| Group | Superclasses | Neurons |
|---|---|---|
| OPTIC | `ol_*`, `visual_*` | 99,156 |
| BRAIN | `cb_*` (not sensory) | 32,343 |
| VNC | `vnc_*` (not sensory) | 12,941 |
| AN | `ascending_neuron`, `efferent_ascending` | 1,749 |
| DN | `descending_neuron`, `efferent_descending` | 414 |
| SENSORY | any superclass containing `sensory` | 15,845 |
| OTHER | `ENS`, `unknown` | 563 |

SENSORY neurons receive no synaptic input in the engine (the sensory mask), and there is no sensory
drive here. So they are expected to stay silent, and the SENSORY group is a built-in sham.

## Conditions

**Simulation.** F1's harness unchanged: L1's `one`, neural only, 3 s, Poisson forced drive on
DNg100_L at **100 Hz** (V1's rate; F1 found 100 and 200 Hz alike), **seeds 1–8**.

| Condition | Weights |
|---|---|
| LIVE | the live engine (gate: equals F1's S0 DNg100_L 100 Hz runs exactly) |
| LIVE_VIA_WEIGHTS | the live weights rebuilt through the `effective_weights` path, nothing removed (gate: equals LIVE exactly) |
| ISOLATED | only edges inside R1's network (gate: equals F1's S1 DNg100_L 100 Hz runs exactly) |
| MINUS_X (7) | every outgoing edge of group X zeroed; everything else as LIVE (necessity) |
| ONLY_X (7) | only edges with both ends in the network or X (sufficiency) |

17 conditions × 8 seeds = **136 simulations**, about 25–30 min at F1's measured cost.

Lesions zero outgoing weights, so the lesioned neurons can still fire, but nothing they do reaches
any other neuron. Their spikes are counted and reported.

## Readout and criteria (declared)

Per simulation, over 250–3,000 ms:
- E1, E2 and I1 mean rates;
- the number of front-left MNs active;
- the rhythm score (reported only);
- the number of active neurons in the network and in each group.

**Engaged** (F1's rule): E1 and E2 **both** ≥ 10 Hz in the same seed, in at least 5 of 8 seeds.
- A group is **NEEDED** if MINUS_X is not engaged.
- A group is **SUFFICIENT** if ONLY_X is engaged.

| Label (first matching row) | Rule |
|---|---|
| `INCONCLUSIVE` | a gate fails, a lesion audit fails, LIVE itself is not engaged, or the run is incomplete |
| `LOCALISED` | some group is both NEEDED and SUFFICIENT |
| `NEEDED_NOT_SUFFICIENT` | some group is NEEDED, and no NEEDED group is SUFFICIENT |
| `REDUNDANT` | no group is NEEDED, and some group is SUFFICIENT |
| `DISTRIBUTED` | no group is NEEDED and none is SUFFICIENT |

**Reported, not gated:**
- every condition's rates, MN counts and scores;
- the per-group active-neuron map in LIVE (where the ~2.3 % of active neurons are);
- whether MINUS_SENSORY equals LIVE exactly and ONLY_SENSORY equals ISOLATED exactly (the sham);
- any condition that engages the core when LIVE's neighbouring conditions do not (non-monotonic
  effects).

## Integrity (declared now)

- **Z1 sources:** the hashes of `neural.py`, `brain_params.json`, the L1 module, the F1 module and its
  result, and the cache fingerprints. Network membership must match cdcfcd23….
- **Z2 reproduction:** the LIVE, LIVE_VIA_WEIGHTS and ISOLATED gates above (hard).
- **Z3 lesion audit:**
  - MINUS_X weights equal LIVE's except the outgoing edges of X, which are zero;
  - ONLY_X weights equal LIVE's on edges with both ends in the network or X, and are zero elsewhere;
  - signs and configuration are unchanged in every condition.
- **Z4 completeness:** 136 simulations of 3 s.

## Expectations (recorded now)

- **X1:** VNC is NEEDED. DNg100 is mostly a nerve-cord neuron (69 % of its cable), so the rest of the
  cord is the most likely source of recurrent support.
- **X2:** ONLY_VNC is engaged, so the label is `LOCALISED` (VNC).
- **X3:** the sham holds: MINUS_SENSORY equals LIVE, and ONLY_SENSORY equals ISOLATED.

Wrong expectations are recorded as wrong.

## What each outcome means (declared now)

- **`LOCALISED` (group X):** the leg network plus X is enough, and X is needed. A later, separately
  designed step could narrow the support within X (for example, by hemilineage or type), still
  neural only.
- **`NEEDED_NOT_SUFFICIENT`:** X is needed, but only together with other groups. The support is a
  combination.
- **`REDUNDANT`:** more than one route can each sustain the engagement.
- **`DISTRIBUTED`:** no single group is needed and none is enough. The core engagement would be a
  broad whole-CNS state, not a specific route. Live-engine motor activity would then need to be read
  as state-dependent, which is relevant to the balance track's destabilising responses.
- **In no case** does F2 show rhythm, balance, walking or a biological role, or justify an engine
  change. The lesions are probes.

## Limits

- One DN (DNg100_L), one rate, one leg network and 8 seeds.
- The groups are coarse superclass partitions. A group can contain both supporting and opposing
  neurons, so "not needed" does not mean "has no effect".
- The only lesion type is transmission removal (outgoing weights zeroed).
- The 10 Hz engagement bar is declared, not derived.
- Neural only. Motor coordinates are unchanged (20/42 admitted, +4 conditional).

## Build and run plan (on approval)

1. `docs/evidence/core-support-map-v1/protocol.json`: groups, conditions, seeds, criteria, source
   hashes and expectations.
2. `malecns_backend/embodiment/core_support_map.py`. It reuses F1's `Edges`, isolated weight rule,
   readout and engagement rule, L1's harness and R1's network builder.
3. Unit tests on toy data: the group partition (disjoint and covering), the lesion construction and
   audit, and the labels.
4. A plumbing smoke: one MINUS_VNC simulation on a non-protocol seed, discarded and disclosed; only
   its exit status and lesion audit are read.
5. Commit and push the preregistration. Run once, evaluate once, then record the results, handoff
   and roadmap.

## Build-time notes (before any protocol simulation)

Protocol: `docs/evidence/core-support-map-v1/protocol.json` (sha 60359bb6…). No amendments to the
groups, conditions, seeds, criteria or expectations.

**As built:**
- **Z1** also checks the group sizes against this design's table, the driver's dense index (36), the
  core cells and the 68 MNs.
- **Gates.** The LIVE gate also compares the whole-CNS active fraction with F1's. The ISOLATED gate
  compares F1's network-only active fraction. Runs are compared after JSON normalisation (NaN as
  null), as stored.
- **Construction.** Every condition except LIVE is built through the `effective_weights` path from
  one pre-gain weight array, using the constructor's own rule. The constructor then applies the
  inhibitory gain. LIVE_VIA_WEIGHTS checks that this path reproduces LIVE. The lesion audit for LIVE
  is trivial, because LIVE is the reference.
- **Active-neuron counts** come from the engine's spike counts over the whole 3 s run, not 250–3,000
  ms. They are reported only.
- **"Non-monotonic" is made precise:** a group X is SUFFICIENT while a different group Y is NEEDED.
  ONLY_X leaves out Y, yet engages the core, while MINUS_Y keeps X and does not. Such pairs are
  listed.
- **Plumbing.** The smoke used MINUS_VNC with seed 0 (not a protocol seed), before the protocol was
  written. Only its exit status and lesion audit were read: passed, 935,434 edges removed, 501,533
  nonzero weights changed. The simulation took 5.0 s. Its core rates, MNs and activity were not
  inspected.
- New tests: 5 in `tests/test_core_support_map.py`, on toy data (15 together with F1's).
