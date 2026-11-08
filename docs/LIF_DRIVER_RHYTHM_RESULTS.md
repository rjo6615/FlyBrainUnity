# LIF return, Step L1 (rate-model rhythm drivers in the live engine): results

Run 2026-11-08 under the preregistered protocol
`docs/evidence/lif-driver-rhythm-v1/protocol.json` (sha 47278c7c…). The protocol, module and
tests were committed and pushed in 7db80a5 before any protocol simulation.
- **Run:** one command in the background, 4 reproduction plus 288 protocol simulations of 3 s,
  1,845 s, run once and evaluated in the same process.
- **Output:** `docs/evidence/lif-driver-rhythm-v1/run/result.json` (sha 4d00b72f…), with
  `console.txt` alongside.
- **Design:** `LIF_DRIVER_RHYTHM_V1.md` (no amendments).

This was a **neural-only simulation in the live, calibrated whole-CNS LIF engine**, untuned. No
body or physics were involved, and the engine, weights and mappings were not changed.

## Verdict: NOT_REPRODUCED_IN_LIF

| Target | Class | Best rate | Best score | Frequency | Feasible seeds at best rate |
|---|---|---|---|---|---|
| DNg75_R | `NOT_RHYTHMIC` | 200 Hz | 0.328 | 2.1 Hz | 12/16 |
| DNa02_L | `NOT_RHYTHMIC` | 25 Hz | 0.427 | 2.8 Hz | 1/16 |
| DNp09_R (secondary) | `NO_MN_OUTPUT` | — | — | — | 0/16 at every rate |

- Both primaries clear V1's control p80 (0.216) but stay below 0.5, at about 2–3 Hz, outside the
  5–20 Hz band.
- The rate model gave these DNs 0.98 and 0.93 at about 13 Hz (R5, R1's sizes).

| Expectation | Outcome |
|---|---|
| X1 (DNg75_R not rhythmic) | **held** |
| X2 (DNa02_L not rhythmic) | **held** |
| X3 (NOT_REPRODUCED_IN_LIF) | **held** |

**Integrity.** All pass:
- I1: hashes; the engine equals V1's; targets resolved from body IDs to the expected dense
  indices; E1/E2 and the 68 MNs equal V1's; control p80 equals V1's stored value.
- **I2: all 4 V1 reproduction simulations matched exactly** (score and per-MN spike counts).
- I3: 5 new tests passed (59 together with the rhythm tests).
- I4: 288 simulations: 192 STIM, plus 48 silencing for each of the two targets with a feasible
  rate.

## Per target (reported, not gated)

**DNg75_R.**
- At 25–100 Hz, no front-left MN is active in any seed.
- At 200 Hz, one MN is active (162458, a sternal anterior rotator, about 2 Hz over the run) in
  12/16 seeds. Per-seed scores range 0.16–0.84.
- E1, E2 and I1 never fire at 5 spikes or more.
- Silencing E1, E2 or the sham cell leaves the score unchanged (0.328, 0.328, 0.327). The output
  does not go through the core.

**DNa02_L.**
- **The declared best-rate rule picked 25 Hz, where only one seed was feasible.** There, one MN
  scored 0.427 at 2.8 Hz.
- At 50–200 Hz every seed is feasible, with scores of 0.26–0.34 and frequencies of about 2 Hz.
- At 200 Hz, 9 front-left MNs are active. They are coxa and trochanter motor neurons:
  sternal posterior rotators, pleural remotor/abductors, a tergopleural promotor, femur
  reductors and a trochanter flexor. Their mean rates over the run are 2.5–44 Hz.
- 5 of these 9 are among the 16 MNs that DNg100 activates at 100 Hz in V1.
- At 200 Hz, E1, E2 and I1 are active in all 16 seeds, at low rates (3.9, 7.6 and 3.6 Hz), with
  median trace rhythmicity of about 0.27.
- **Silencing ran at 25 Hz** because of the best-rate choice, so it rests on a single feasible
  seed. Its scores equal STIM (0.427), which makes it uninformative about the core.

**DNp09_R.** No front-left MN is active at any rate. It has no direct synapse onto them.

## What this means (per the design's declared outcomes)

- **Declared consequence of NOT_REPRODUCED_IN_LIF.** The rate model's front-left rhythm does not
  transfer to the live engine for the three DNs it picked out.
  - DNg75_R reaches one MN, and only at 200 Hz.
  - DNa02_L drives a coxa/trochanter set, slowly (about 2 Hz) and without a rhythm score of
    0.5.
  - DNp09_R reaches none.
- **Reading (a hypothesis, not a result).**
  - In the live engine, these DNs barely engage the E1/E2 core.
  - Only DNa02_L at 200 Hz activates it at all, at a few Hz.
  - So the live engine and the rate model differ in how descending drive reaches the core, not
    just in whether the core oscillates.
  - Any reason (spiking versus rate dynamics, whole-CNS context, calibrated parameters, the drive
    form) is a separate question. The engine must not be tuned until it oscillates.
- **Declared-rule caveat.** V1's best-rate rule let a single feasible seed choose DNa02_L's best
  rate and silencing rate. This changes no class, because no rate reached 0.5. But it made
  DNa02_L's silencing conditions uninformative. Any follow-up should declare a minimum number of
  feasible seeds.
- **In no case** does L1 show walking, assign biological roles, or change the live engine,
  weights, mappings or motor admission.

## Limits

- **Three DNs,** chosen by the reconstructed rate model; other DNs are untested.
- **Poisson forced-spike drive** at four rates. The rate model used a constant input.
- **16 seeds per condition.** The specificity reference is V1's stored control distribution
  (only 2 of 20 controls feasible).
- **Silencing ran at the best rate only.** For DNa02_L that rate had one feasible seed.
- **Front-left MNs only;** other legs are not read.
- **Neural only:** no body or physics. Motor coordinates are unchanged (20/42 admitted, +4
  conditional).
