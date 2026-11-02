# Right-front coxa MN excitation — design (V1)

Designed 2026-11-01, after the drive-asymmetry result was merged (PR #310). This
document is the design only. No code has been written and nothing has run. The protocol
JSON, module and tests are written and hash-locked at build time, and committed before
the single run.

## Why

The drive-asymmetry replay (`COXA_DRIVE_ASYMMETRY_RESULTS.md`) showed a second gap that
the structural factors cannot explain. Besides their hair plates, the best posterior coxa
MNs receive excitation from the rest of the network:

| Leg | Excitation from the rest of the network |
|---|---:|
| LF | 8.6 |
| LH | 22.1 |
| RF | 0.2 |

This was measured in Step C arm A_ON (held posture, hair plates on). In LH that excitation
is twice the hair-plate drive.

**Question:** why does RF lack it? There are three candidate explanations:

| Explanation | Meaning |
|---|---|
| **Wiring** | RF coxa MNs have fewer or weaker excitatory input partners in the connectome |
| **Activity** | The partners exist, but they were quiet in this run |
| **Consequence** | The left-side extra excitation is itself driven by the left hair plates through interneurons, so RF's weak hair plates also leave RF without it |

**Data only.** The analysis replays the two held-posture Step C arms already recorded
locally:

- **A_OFF:** hair plates off.
- **A_ON:** hair plates on.

They share one seed, one external schedule and the same random draws. Nothing is
simulated or changed.

## Fixed inputs

| Input | Source | Lock |
|---|---|---|
| Step C raw arms A_OFF, A_ON | local, uncommitted | sha256 from the committed Step C report (`arm_sha256`): A_OFF 2aa48719…, A_ON 8c2d90e6… |
| Sensory sets, MN sets, engine weights | exactly as in the drive-asymmetry V1 module (`coxa_drive_asymmetry`: `sensory_sets` / `leg_pools` / `mn_sets`, `edges_into` / `rule_weights`, `MaleCNSBrain`) | Its protocol hash; its engine audit is repeated |
| Replay | `coxa_drive_asymmetry.replay`, reused unchanged; it must again be REPLAY_EXACT or REPLAY_CLOSE in both arms | Same rule as V1 |
| Target MNs | Each leg's best-driven posterior MN as in V1 (146868 RF, 146498 LF, 144071 LH), plus the whole posterior pool per leg | Read from the committed V1 `result.json` (hash-locked) |
| Window | 520–2000 ms, Step C convention | Unchanged |

## Measures

- **E1 Per-partner excitation.** For each target MN, the window-mean excitatory
  conductance is attributed to each presynaptic neuron j. Over the window, j's
  contribution is its effective weight × psp × (its delivered spikes, each decayed
  exactly as in the engine). The contributions sum to the replayed excitatory g; this is
  checked to within 1e-6 relative.
- **E2 Classes of "other" excitation**, meaning everything except the leg's own hair
  plates:
  - by presynaptic superclass and type;
  - by side of origin (somaSide/rootSide);
  - by whether the partner is downstream of the leg's own hair plates. **Downstream**
    means a floored direct edge from any of the leg's own SNpp45 neurons.
- **E3 Hair-evoked vs baseline.** The same partner's contribution is compared in A_ON
  and A_OFF:
  - **Baseline:** the A_OFF value.
  - **Hair-evoked:** A_ON minus A_OFF.
- **E4 Potential vs realized input (wiring vs activity).** For the "other" excitatory
  partners of a target MN:
  - **W_pot:** Σ_j eff(j→m), the excitatory input weight available, using floored engine
    weights.
  - **Realized:** g_other = W_pot × ρ, where ρ = g_other / W_pot is the
    activity-weighted delivery rate.

  Comparing RF with LF:

  log(g_other,RF / g_other,LF) = log(W_pot ratio) [**WIRING**] + log(ρ ratio) [**ACTIVITY**]

  The two terms sum exactly. They are computed per arm.
- **E5 Homolog type table (descriptive).** For each presynaptic type contributing on
  either side, it reports:
  - the effective weight onto RF vs LF;
  - the mean rate of that type's right-side vs left-side neurons in each arm.

## Labels (decided by these rules only)

**Integrity.** All of the following must hold:

- the hashes match;
- the V1 engine audit passes;
- the replay is REPLAY_EXACT or REPLAY_CLOSE in both arms;
- the E1 sum check passes;
- A_ON and A_OFF share the external schedule and the per-tick uniforms.

Otherwise the result is `INCONCLUSIVE_INTEGRITY`, with no labels.

**Q1: where does LF/LH "other" excitation come from?** Measured on the best-driven MN
in A_ON:

| Label | Rule |
|---|---|
| `HAIR_EVOKED` | In both LF and LH, hair-evoked (A_ON − A_OFF) is at least 50 % of g_other |
| `BASELINE` | In both legs, it is under 50 % |
| `MIXED_LEGS` | Otherwise |

**Q2: what is RF's gap against LF?** In A_ON, on the best-driven MNs:

| Label | Rule |
|---|---|
| `WIRING_GAP` | The WIRING log term is the more negative, and the ACTIVITY term is not within 10 % of it |
| `ACTIVITY_GAP` | The ACTIVITY log term is the more negative, and the WIRING term is not within 10 % of it |
| `MIXED` | Both terms are negative, with magnitudes within 10 % of each other |
| `NO_GAP` | Neither term is negative |

**Q2b:** the same rule applied to RF against LH.

**Q3: is the gap a consequence of RF's weak hair plates?** This compares g_other on the
best-driven MN between the two arms.

| Label | Rule |
|---|---|
| `CONSEQUENCE_OF_HAIR_PLATES` | In A_OFF, RF ≥ 0.67 × LF (a small baseline gap), and in A_ON, RF < 0.33 × LF (the gap appears with hair plates) |
| `PRE_EXISTING_ASYMMETRY` | In A_OFF, RF < 0.67 × LF |
| `NOT_DETERMINED` | Otherwise |

**Pool-level repeat (descriptive).** Q1–Q3 are recomputed over the whole posterior pool
(summed g and W_pot). This is reported, not used for labels.

## What this can and cannot decide

**It can say** whether the missing excitation is missing wiring or missing activity. It
can also say whether the left-side excitation is evoked by the hair plates through
interneurons. If so, RF's single structural deficit (small hair-plate neurons) would
explain both gaps.

**It cannot say** whether any connectome difference is real anatomy or a reconstruction
artifact. Nor does it show that the identified partners matter causally. Passive replay
of one seed is not an intervention.

**Nothing here is a fix.** Silencing partners, adding drive or changing weights would be
a separately versioned intervention.

## Predictions (expectations, not criteria)

- Q1 `HAIR_EVOKED` for LF. LF's other excitation looks hair-driven (Step C OFF coxa MN
  rates were about 2 Hz). LH is less certain: its g_other is large, and part of it may
  be baseline.
- Q2 `ACTIVITY_GAP` and Q3 `CONSEQUENCE_OF_HAIR_PLATES`. In this picture, RF's partners
  exist but are not recruited, because RF's hair plates are too weak to recruit them.
- A `WIRING_GAP` would instead point to a second, independent connectome asymmetry on
  RF.

## Build and run plan (on approval)

1. Write `docs/evidence/rf-coxa-excitation-v1/protocol.json`, which makes the rules
   above exact.
2. Write `malecns_backend/embodiment/rf_coxa_excitation.py`. It imports the V1 module
   unchanged and adds the per-partner attribution and the labels.
3. Write `tests/test_rf_coxa_excitation.py`. Its synthetic tests cover:
   - per-partner attribution summing to the replayed g on a tiny engine network;
   - the WIRING/ACTIVITY identity;
   - the label rules.
4. Commit and hash-lock everything, run once, then commit `result.json` and the results
   write-up. The raw arms stay local.
