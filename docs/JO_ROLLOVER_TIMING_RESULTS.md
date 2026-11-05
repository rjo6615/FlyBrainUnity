# Antennal gravity sense, Step D2 (rollover timing replay): results

Run 2026-11-05. The run used the preregistered protocol
`docs/evidence/jo-rollover-timing-v1/protocol.json` (sha 12ca7a70…), committed and pushed in
d25245d before the replay. It ran once (about 1 minute) and was evaluated once.
- One plumbing smoke on two LEVEL control pairs was discarded; only its exit status was read.
  It found that the reset state (state 0) records no commanded joints. That state is stored
  as NaN and lies outside every definition. The fix and a test were added before the
  preregistration commit.
- Output: `docs/evidence/jo-rollover-timing-v1/run/result.json` (sha dd372b92…), with
  `console.txt` alongside.
- Design: `JO_ROLLOVER_TIMING_V1.md`.

## Verdict

| Check | Result |
|---|---|
| R1: 37 arm hashes equal the Step D report; report hash | pass |
| R2: recomputed peak tilt equals the report within 1e-9 | pass |
| R3: FELL set is exactly the 5 named arms; no OFF or LEVEL arm fell | pass |
| R4: state-0 qpos equal in every pair | pass |

**`INTEGRITY_ACCEPTED`**

| Question | Result |
|---|---|
| Q1: order in each FELL arm | **COMMAND_FIRST in 5 of 5**, so **`ORDER_COMMAND_FIRST`** |
| Q2: F1 commands, F2 per-leg MN, F3 supports, F4 d (early window) | **all `OVERLAPS`** |
| Expectation: order | **HELD** (by the rule; the next section shows the rule does not discriminate) |
| Expectation: F1 SEPARATES | **NOT_HELD** |

## The order label does not discriminate (from the preregistered controls)

The design expected the command threshold (0.05, a fifth of the channel bound) to mark a
tilt-related change. The controls show it does not:
- **Admitted commands cross 0.05 in almost every ON arm, whether or not the arm fell or was
  tilted.**
  - G1 LEVEL arms, with no tilt: t_cmd is 0.1–19.6 ms in all 6.
  - Upright DOWN20 arms: G1 0.1–4.1 ms; FLIP 22–93 ms.
  - FLIP LEVEL arms: 3 of 6 never cross; the others cross at 22, 327 and 994 ms.
- **In the fallen arms, t_cmd comes 0.1–96 ms after the tilt, but the falls come 583–1415 ms
  after it.** A 500–1,300 ms lead does not identify a trigger.

So `COMMAND_FIRST` says only that ON and OFF commands already differ beyond 0.05 long
before any fall. That is true in arms that fall and in arms that do not. It is recorded as
the protocol's label, and **it is not evidence that a post-tilt command change caused the
falls.**

## Timings (ms after the tilt)

| Arm | t_cmd (first channel) | t_support | t_body | t_fall | t_fall − t_body |
|---|---|---:|---:|---:|---:|
| G1_DOWN20_19 | 19.6 (RHTibia, +) | 227.7 | 556.3 | 583.3 | 27 |
| G1_DOWN20_21 | 0.1 (RHFemur_roll, −) | 325.8 | 867.6 | 898.4 | 31 |
| G1_DOWN20_24 | 0.1 (RMTibia, +) | 137.1 | 1132.3 | 1161.7 | 29 |
| FLIP_DOWN20_23 | 91.6 (LFTibia, +) | 266.4 | 946.5 | 980.9 | 34 |
| FLIP_DOWN20_24 | 96.1 (RHFemur_roll, −) | 279.2 | 1380.9 | 1415.0 | 34 |

What the timings show:
- **The falls are abrupt and late.** In every fallen arm, the sustained body divergence
  (> 5° beyond the matched OFF arm) starts only **27–34 ms before 45°**. The falls occur
  583–1415 ms after the tilt, long after the 50 ms early window, and are spread across the
  run.
- **Losing tripod support (fewer than 3 legs on the ground while OFF has 3 or more) is
  common, not specific to the falls.**
  - It happens 137–326 ms after the tilt in every fallen arm.
  - It also happens in all 7 upright DOWN20 arms (175–598 ms) and in 4 of 6 G1 LEVEL arms.
  - It never happens in a FLIP LEVEL arm.
- **The zone switch (d > 0) happens at the first tick (0.5 ms) in every DOWN20 arm,** as
  expected for a gravity step.
- Q2: no early-window feature (500.5–550 ms) separates the arms that fell from those that
  stayed upright.

## The last 50 ms before body divergence (reported, not labelled; fallen arms only)

| Arm | Largest baselined \|ON − OFF\| commands | Per-leg baselined MN change (Hz) |
|---|---|---|
| G1_DOWN20_19 | RHFemur_roll 0.11, LMFemur 0.07, RHTibia 0.07 | RH +7.1, RM −3.5, LF −2.1 |
| G1_DOWN20_21 | LMFemur 0.11, LHTibia 0.07, RHFemur_roll 0.06 | RH +10.0, LF +3.1, LH −2.5 |
| G1_DOWN20_24 | LMFemur 0.13, LMTibia 0.10, RHFemur_roll 0.04 | RH +6.3, LH +4.2 |
| FLIP_DOWN20_23 | **LFTarsus1 0.24**, RFFemur_roll 0.21, LFFemur_roll 0.20 | **LF +20.0, RF +17.5**, RM +12.6, RH +7.8 |
| FLIP_DOWN20_24 | **LFTarsus1 0.25**, LFFemur_roll 0.22, RFFemur_roll 0.21 | **LF +19.1, RF +19.1**, RH +12.9, RM +7.4 |

These are descriptive. There is no matched pre-fall window in the upright arms, so
**they cannot be read as fall-specific.**
- **The two FLIP falls look alike.** Just before the body diverges, front-leg commands sit at
  or near the 0.25 channel bound (LF Tarsus1 and both front femur rolls), and front-leg MN
  rates are raised by about 18–20 Hz.
- **All three G1 falls show raised right-hind MN activity** (+6 to +10 Hz) and moderate
  middle-leg femur commands.

## Declared interpretation and what it means here

The protocol's declared reading of `ORDER_COMMAND_FIRST` is: "falls follow a JO-driven change
in admitted commands". Read with the controls, this is **trivially satisfied and not
diagnostic**, because ON and OFF commands differ early in arms that do not fall.

What the replay does establish descriptively:
- the falls are late, abrupt events of about 30 ms;
- the spread in time across the run is wide, from 583 to 1415 ms;
- no early-window marker separates the arms that fell;
- tripod-support loss is common and not specific to falling.

This pattern fits a body that is put by JO-driven commands into a less stable posture
regime, and that then tips over at variable times. It does not fit a direct, timed response
to the tilt. That reading is a hypothesis, not shown here.

**Not claimed:** the cause of the falls, balance, a corrective response, the zone sign, or
any motor coordinate change (20/42 admitted, +4 conditional).

## Limits

- Descriptive replay with 5 fallen arms. Order in time is not cause.
- The command threshold was within the range of ongoing ON−OFF variability, so Q1 cannot
  discriminate. This is recorded rather than re-thresholded. Any new threshold would need a
  new versioned protocol.
- Commands are sampled per stored state and MN activity per 0.5 ms tick; the 10 ms margin
  cannot resolve faster sequences.
- Step D's limits apply: an idealised gravity step, modelled JO transduction, and a sparser
  right-side JO reconstruction.

## Reproduce (Git Bash; writes a separate file; needs the 37 local Step D raw arms)

```bash
P="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
PYTHONPATH="$PWD" "$P" -m malecns_backend.embodiment.jo_rollover_timing --arms "$HOME/Documents/FlyBrainUnity/docs/evidence/jo-zone-crossing-v1/run" --output docs/evidence/jo-rollover-timing-v1/run/result.recheck.json
```

Expected: the same status, labels and timings as `result.json`.
