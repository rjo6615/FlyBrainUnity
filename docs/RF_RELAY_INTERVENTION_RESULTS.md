# Hair-plate relay intervention V1 — results

Run 2026-11-02, once per arm, after the preregistration commit 80433ba (protocol sha
29b756b7…). Design: `RF_RELAY_INTERVENTION_V1.md`. Report:
`docs/evidence/rf-relay-intervention-v1/run/report.json` (sha 5820e404…). Each arm ran in a
fresh process (about 4.7 min each), then the evaluation ran once.

**Every arm is an engineering intervention on the model.** Withheld transmission and forced
events test causal roles inside this simulation. They are not biological manipulations,
and nothing here changes weights, thresholds, mappings, the encoder or the motor interface.

## Verdict

| Question | Label | Prediction |
|---|---|---|
| Q_NEC: is the left relay necessary for LF? | **NOT_NECESSARY** (L_SIL ratio 0.823; L_SHAM 0.977) | CONTRIBUTES (failed) |
| Q_SUF: is the right relay sufficient for RF? | **NONSPECIFIC** (R_SHAM +5.9 Hz ≥ 2 Hz; R_INJ +22.6 Hz) | PARTIAL (failed) |

`SENSORY_CONFOUNDED` is false for both questions. Read that with care: the primary legs'
hair-plate rate was at the encoder's 120 Hz ceiling in every arm, so this check could not
have detected a change (see Protocol flaws).

## Integrity: all accepted

| Check | Result |
|---|---|
| I1 complete (20,001 samples, 4,000 ticks, five arms) | pass |
| I2 identical uniforms and schedule | pass |
| I3 C0 reproduces saved A_ON exactly (fired, uniforms, hair deliveries, qpos) | pass |
| I4 interventions verified per tick | pass |
| I5 prefix identity before the first intervention | pass |

- First intervention tick: L_SIL 89, L_SHAM 51, R_INJ and R_SHAM 21.
- Injection events blocked by refractoriness: 18 of 279 in each injection arm.
- Every descriptive replay was REPLAY_EXACT.

## Measured rates (window 520–2000 ms)

Posterior coxa MN pool rates in Hz. The V1 pools have 6 MNs in LF and 4 in RF.

| Arm | LF | LH | RF | RM | RH | LM |
|---|---:|---:|---:|---:|---:|---:|
| C0 | 48.3 | 44.7 | 1.52 | 1.93 | 3.38 | 0.29 |
| L_SIL | 39.8 | 48.9 | 1.18 | 3.28 | 3.83 | 0.68 |
| L_SHAM | 47.2 | 45.6 | 1.35 | 1.06 | 3.60 | 0.48 |
| R_INJ | 46.6 | 46.2 | **24.2** | 1.54 | 3.04 | 0.39 |
| R_SHAM | 44.9 | 48.1 | 7.43 | 1.83 | 3.94 | 0.97 |

Best-MN rates in Hz:

| Arm | LF best | RF best |
|---|---:|---:|
| C0 | 81.1 | 4.05 |
| L_SIL | 68.2 | — |
| L_SHAM | 79.7 | — |
| R_INJ | — | 47.3 |
| R_SHAM | — | 14.9 |

Rates of the intervention sets themselves, in Hz:

| Arm | LEFT_RELAY | RIGHT_RELAY | LEFT_SHAM | RIGHT_SHAM |
|---|---:|---:|---:|---:|
| C0 | 19.4 | 0 | 12.0 | 0 |
| L_SIL | 13.7 | 0 | 10.5 | 0 |
| R_INJ | 18.6 | 16.5 | 11.5 | 0 |
| R_SHAM | 18.2 | **1.94** | 11.8 | 16.5 |

R_INJ's RF pool rate (24.155 Hz) sits exactly on the RESCUED threshold (0.5 × C0 LF =
24.155 Hz). That is an arithmetic coincidence of spike counts: RF's 143 spikes over 4 MNs
equal one third of LF's 429 spikes over 6 MNs. RESCUED would have applied (≥), but
NONSPECIFIC takes precedence by the preregistered rule.

## Excitation decomposition of the primary best MNs (descriptive)

The values are window-mean conductances. The V1 replay and V2 attribution are unchanged,
and withheld spikes are removed from delivery.

| Case | g_hair | g_other | from relay set | g_inh |
|---|---:|---:|---:|---:|
| C0, LF best | 19.56 | 8.59 | LEFT_RELAY 6.52 | −2.18 |
| L_SIL, LF best | 19.56 | 1.51 | 0 | −0.92 |
| L_SHAM, LF best | 19.56 | 7.79 | LEFT_RELAY 6.41 | −2.42 |
| C0, RF best | 6.02 | 0.18 | 0 | 0 |
| R_INJ, RF best | 6.02 | 8.98 | RIGHT_RELAY 8.84 | 0 |
| R_SHAM, RF best | 6.02 | 2.57 | **RIGHT_RELAY 2.09** | −0.03 |

## What this shows inside the model

- **The left relay is the main non-hair excitation onto LF, but LF does not need it.**
  Silencing it removed about 82 % of the LF best MN's other excitation (8.59 → 1.51).
  LF pool firing fell only 18 %, because LF's direct hair-plate drive (19.6) is already well
  above g* (8.09). By the preregistered cut (0.8), the label is NOT_NECESSARY. The ratio
  (0.823) is close to that boundary.
- **Driving the right relay raises RF strongly, but the sham was not clean.** Injecting
  left-matched trains (delivered at 16.5 Hz) raised RF pool firing from 1.5 to 24.2 Hz and
  the RF best MN from 4 to 47 Hz. The right relay delivered 8.84 of RF's 8.98 other
  excitation. The sham raised RF by 5.9 Hz, so the label is NONSPECIFIC.
- **Exploratory (post hoc, not a label):** the sham's effect went mostly through the
  relay itself. Sham injection recruited the right relay to 1.94 Hz, and that gave 2.09 of
  the sham's 2.57 other excitation onto the RF best MN. The relay-attributable gain was
  8.84 in R_INJ against 2.09 in R_SHAM. This suggests the right relay can carry LF-like
  drive to RF once active, but the preregistered control does not establish it.
- The right relay copies stayed silent in C0 and were not recruited by L_SIL. Their
  silence is an input problem, consistent with the earlier result that RF hair plates make
  about a quarter as many synapses onto them.
- The physical effects were small. There were no rollovers, and the largest change in
  mean tilt was +0.57° (L_SIL). Spillover onto the 20 admitted channels was a few Hz at
  most; LH femur roll varied between 27.7 and 33.5 Hz across arms.

## Protocol flaws (recorded, labels not reinterpreted)

1. **The sham rule did not exclude edges onto the relay.** It required no floored edge
   onto any replayed coxa MN, but did not exclude edges onto RIGHT_RELAY. In R_SHAM, the
   injected sham neurons recruited the relay (1.94 Hz). So the sham partly tested the
   relay rather than a neutral control, and the NONSPECIFIC label is partly caused by this
   flaw. A V2 would need sham neurons with no path into the relay set, under a new,
   separately versioned protocol.
2. **The sensory-confound check was saturated.** The primary legs' window-mean hair-plate
   rate was 120 Hz, the encoder cap, in every arm, so a 10 % change could not show. The
   flag is uninformative here.
3. **Equal-precision boundary.** R_INJ landed exactly on the RESCUED threshold. Its label
   would have depended on ≥ versus >, had NONSPECIFIC not taken precedence.

## Limits

- One seed, assisted posture, open-loop coxa (no coxa channel admitted).
- These are engineering manipulations of the model.
- The relay types were chosen post hoc; this was their first prospective test.
- A causal role inside the model does not separate real anatomy from a reconstruction
  artifact.
- No coordinate is admitted. Motor coverage stays 20/42.

## Evidence

**Raw arms** are local and uncommitted, in
`docs/evidence/rf-relay-intervention-v1/run/<arm>.json.gz` of the main checkout.

| Arm | sha256 |
|---|---|
| C0 | a338224bb3b0a5ce6c7521030d23504f95766e11641222dcaa955613302e6ca4 |
| L_SIL | c0d5bb8f01067bb8c3c5abc46ee4f172d2bc80d2975ba81164cc1908c90ee196 |
| L_SHAM | a57af08102cf5db50327aa038599ae7b9eb11f8e52470fd46f1dfd0e057e2792 |
| R_INJ | b2376c87c595da8542137274256b38e330ff9a2cab9e0302d61ab27528620388 |
| R_SHAM | c9e478094a936576f78d9c590950ca6de695902c0ccf4d715b563e5d549224c7 |

**Committed:** `protocol.json`, `run/report.json`, `run/console_<arm>.txt` and
`run/console_evaluate.txt`.
