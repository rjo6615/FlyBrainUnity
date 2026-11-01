# Coxa hypothesis D3 — results

Protocol `docs/evidence/coxa-hypothesis-d3-v1/protocol.json` (sha b8d524…), the code
and the tests were committed at f4c06a8 before anything ran. The preflight passed, and
then the four arms each ran once, in their own process, in the order C0, H1, H1_FLIP,
H2. The evaluation ran once. CNS and physics were executed (not mocked). Nothing was
retried, re-windowed or tuned.

## Labels

| | Result |
|---|---|
| Preflight | `PREFLIGHT_PASSED` (P1, P2, P4, P5 true; P3 enforced at run time) |
| Integrity | `INTEGRITY_ACCEPTED`: I1–I5 all true. C0 reproduces the saved Step C A_ON in spikes, random draws, hair-plate deliveries and every qpos sample |
| **Q3** | **`NOT_CONSISTENT`**: H1 shifted posteriorly by ≥ 0.02 in 2 of 4 firing legs; 3 were required |
| **Q4** | **`H1_FAVOURED`** (H1 2 legs, H2 0) |

By the preregistered rule, the closed loop as a whole is **not** consistent with the
resistance reflex. That result stands. The per-leg data show where it holds and
where it does not.

## Per-leg forward-component change vs C0 (window 520–2000 ms)

| Leg | C0 hair rate | H1 Δf | H1_FLIP Δf | H2 Δf | Coxa MN rate C0 (Hz) |
|---|---:|---:|---:|---:|---:|
| LF | 120 Hz | **−0.173** | **+0.145** | +0.008 | 22.7 |
| LH | 120 Hz | **−0.191** | **+0.206** | −0.005 | 32.3 |
| RF | 120 Hz | −0.005 | +0.027 | +0.002 | 0.55 |
| RH | 0.16 Hz | −0.013 | +0.022 | +0.000 | 3.7 |
| LM / RM (excluded, silent encoder) | 0 | −0.010 / +0.006 | −0.009 / −0.018 | −0.028 / −0.009 | 0.4 / 1.7 |

**What the data show (descriptive):**
- **Left front and left hind legs form a working resistance loop.** In both, H1 moves
  the coxa back about 9× the 0.02 bar, and the flipped wiring moves it forward
  by a similar amount. On the H1 `+Coxa` channel the commanded offsets average
  +0.17 rad (LF) and +0.22 rad (LH), below the 0.25 rad cap (max 0.216 / 0.245). With
  the flip they average −0.17 and −0.22 rad. In LH the loop also feeds back on the
  sensor: hair-plate rate falls from 120 to 109.6 Hz under H1, the negative feedback
  the reflex predicts. It cannot rise under the flip, because the encoder is already
  saturated at 120 Hz.
- **Right front fails on the neural side, not the geometric side.** Its hair plates fire
  at the maximum (120 Hz), but its coxa MNs barely respond (0.55 Hz), so the
  `RFCoxa` channel never moves (offset 0.000). This matches the right-front weakness
  seen before: 5 hair plates and 194 direct synapses (Step A), and almost no Step C
  response.
- **Right hind barely counts as a firing leg.** At 0.16 Hz it passes the
  preregistered `> 0 Hz` rule, but its coxa sits well behind the encoder threshold
  in the live run (f = −0.31). Its small shifts point the predicted way (H1 −0.013,
  FLIP +0.022), and H1_FLIP raises its hair-plate rate to 32 Hz, but H1 stays below
  the bar.
- **H2 produces no posterior shift in any firing leg.** Its largest channel,
  `LFCoxa_roll` (+0.23 rad), moves the leg sideways. This confirms that the
  rotator pools H2 drops carry the fore-aft reflex.

**Other descriptive numbers:**
- **Body tilt** (mean / peak): C0 3.8° / 5.7°, H1 10.6° / 13.4°, H1_FLIP 1.4° / 5.7°,
  H2 3.5° / 5.7°. The H1 resistance setpoints tilt the assisted body more. This is
  not a balance measure.
- **First coxa command:** state 216 for H1 and H1_FLIP, 231 for H2. Physical
  divergence from C0 starts at the same states.
- **Hair-plate deliveries:** C0 3215, H1 3144, H1_FLIP 3663, H2 3326.

## Interpretation and limits

- The preregistered label is NOT_CONSISTENT. Two strong, sign-reversing legs do not
  meet the three-leg rule, and the rule is not revisited.
- The failure has an identifiable cause in our engine: the right-front hair-plate →
  coxa MN pathway is weak (this is what drives its result, not the binding), and RH
  is essentially below threshold. Whether the right-side weakness is real anatomy,
  a reconstruction artifact or an engine property is an open, separately versioned
  question.
- Where hair plates do recruit coxa MNs (LF, LH), the name-geometry binding produces
  a closed loop that behaves as a resistance reflex and reverses under the flip.
  This is consistency in two legs, not validation of the binding.
- Limits: one seed, assisted posture, offset-on-servo actuation (a shift is a
  servo setpoint shift). Nothing is admitted; motor coverage stays **20/42 proven**.

## Evidence

- Committed: `protocol.json`; and in `run/`: `preflight.json`, `report.json`,
  `console.txt` and `evaluate_console.txt`.
- Raw arms are local, uncommitted (about 40 MB each); sha256 values are in `report.json`:
  - C0 93fbf1…
  - H1 4203ae…
  - H1_FLIP ffa9d9…
  - H2 78215f…
- The C0 file hash differs from Step C A_ON's because its record adds the channel
  inventory. I3 compares content.
