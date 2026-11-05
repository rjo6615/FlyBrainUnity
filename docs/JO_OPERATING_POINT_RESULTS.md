# Antennal gravity sense, Step C2 (JO operating-point attribution): results

Run 2026-11-05. The run used the preregistered protocol
`docs/evidence/jo-operating-point-v1/protocol.json` (sha 1527f2fc…), committed and pushed
in d3d76db before the run. It ran once and was evaluated once.
- The run replays geometry only. The recorded qpos of the 36 Step C seed arms went through
  `mj_forward` in the Step B runtime model, with 1,183,536 calls. There was no CNS and no
  physics stepping.
- Two Step C plumbing smokes (scratch, discarded) fixed the tick-to-state mapping before
  the protocol was written. One attribution smoke (2 arms) was discarded unread except for
  its exit status.
- Raw output: `docs/evidence/jo-operating-point-v1/run/result.json` (sha 981ee47c…), with
  `console.txt` alongside.
- Design: `JO_OPERATING_POINT_V1.md`.

## Verdict

| Check | Result |
|---|---|
| J1 inputs (report and 36 arm hashes) | pass |
| Factor addresses (exact joint names = declared qpos) | pass |
| J2 replay: recomputed d vs recorded `jo_d`, 144,000 ticks | pass, maximum difference **0.0** (bit-exact) |
| J3 state-0 d = Step B rest | pass, maximum difference 0.0 |
| J4 Shapley additivity | pass, maximum error 2.2e-16 |

**`INTEGRITY_ACCEPTED`**

| Question | Left | Right |
|---|---|---|
| Q1: drift from state 0 to pre-tilt state 5005 | **`DOMINANT_ROOT`** | **`DOMINANT_ROOT`** |
| Q2: change to the window mean, UP arms | **`DOMINANT_GRAVITY`** | **`DOMINANT_GRAVITY`** |
| Q2: change to the window mean, DOWN arms | **`DOMINANT_GRAVITY`** | **`DOMINANT_GRAVITY`** |

## Attribution (medians over arms; d units; Step B pitch slope ≈ 0.0168 per degree)

**Q1, before the tilt** (36 arms; total change −0.030 L / −0.025 R, range −0.081 to −0.017):

| Factor | Left | Right | Sign with the total |
|---|---:|---:|---|
| ROOT | −0.064 | −0.060 | 36/36 |
| NECK | +0.033 | +0.034 | 0/36 (opposes) |
| A2 | +0.0007 | +0.0007 | opposes |
| A3 (a2–a3 joint) | +0.0001 | +0.0001 | opposes |
| ARISTA | 0.0000 | 0.0000 | — |
| GRAVITY | 0 (no tilt yet) | 0 | — |

What happened physically:
- **The body pitched nose-up** by 3.4–6.2° relative to gravity in the first 500 ms. That
  lowered d by about 0.06.
- **The passive neck sagged nose-down** by about 2.0° (joint_Head 1.99–2.00° in every arm).
  That raised d by about 0.033 and cancelled about half of the body effect.
- **The antenna joints barely moved.** The a2–a3 pitch was 0.013–0.014°, and A2, A3 and
  ARISTA together contributed under 0.001.

**Q2, window mean** (18 arms per tilt):

| | Total | GRAVITY | ROOT | NECK | A2+A3+ARISTA |
|---|---:|---:|---:|---:|---:|
| UP, L | −0.226 | −0.165 | −0.096 | +0.034 | +0.002 |
| UP, R | −0.215 | −0.163 | −0.088 | +0.034 | +0.002 |
| DOWN, L | +0.146 | +0.170 | −0.057 | +0.032 | +0.001 |
| DOWN, R | +0.145 | +0.169 | −0.057 | +0.032 | +0.001 |

- The tilt itself dominates, as expected for a 10° tilt.
- **Beside it, the body posture lowers d in both tilt directions.** Relative to gravity, the
  body sat at:
  - −14.1 to −16.1° pitch under UP (10° tilt plus about 5° extra nose-up);
  - +6.1 to +6.7° under DOWN (10° tilt minus about 3.5°).
- The neck sag (+0.032 to +0.034) persists. The antenna joints stay negligible (a2–a3 pitch
  ≤ 0.031°).
- The window-mean d was −0.378 to −0.323 (UP) and −0.021 to +0.018 (DOWN).

**Tilt contrast (DOWN − UP, window mean; per seed and arm type):**
- The total is +0.34 to +0.38. Of that, GRAVITY is +0.335 to +0.339, the 20° difference in
  tilt.
- ROOT adds +0.036 to +0.047 in OFF and FLIP, because UP pitches the body further nose-up
  than DOWN does. In G1 it adds only +0.008 to +0.030. The tonic E drive in G1 changes the
  postural response; that is a physical outcome of the neural input (see Step C), not a
  defect.
- NECK and the antenna joints contribute −0.003 or less.

**By arm type (Q1, left):**

| | ROOT | Total |
|---|---:|---:|
| OFF | −0.062 | −0.028 |
| FLIP | −0.062 | −0.028 |
| G1 | −0.089 | −0.055 |

The OFF and FLIP medians are identical. In seed 13, G1 pitches about 0.5° more nose-up
than OFF before the tilt and rolls about 4°.

## Interpretation (as declared)

**Q1 `DOMINANT_ROOT`:** the pre-tilt offset is a postural state of the assisted-posture
context, a nose-up pitch of about 4° relative to gravity. As declared:
- the encoder needs no change;
- a later JO design should set its tilt range around this live operating point, not around
  Step B's level-head geometry.

**Secondary findings** (reported, not labelled):
- **The passive neck is a consistent confound of about +0.033 in d** (about 2° of
  nose-down head sag). Real flies stabilise the head actively; this model has no neck motor
  control. It partly offsets the body's nose-up pitch. Any JO step should list it, and any
  fix needs its own design.
- **The passive antenna joints contribute nothing material** (under 0.002 in every
  decomposition; a2–a3 deflection about 0.01–0.03°). The design's concern about
  uncalibrated antenna-joint sag is therefore not the source of the offset.

  A corollary, stated as an observation and not tested: in this model the a2–a3 joint
  barely deflects under gravity. A JO encoder that read this joint's angle would carry
  almost no tilt signal unless the antenna mechanics were changed. That would be a modelling
  decision needing its own evidence, not a tuning step.

**Q2 `DOMINANT_GRAVITY`:** the window change comes mainly from the tilt itself. The
quantity of interest beside it is posture, and it is also the cause of the "d stays ≤ 0"
outcome in Step C:
- from Step B's rest −0.144, the tilt alone (+0.170) would have put the nose-down window at
  about +0.03, and the neck sag (+0.032) at about +0.06;
- the body's nose-up bias (ROOT −0.057) brought it back to about 0.

**Consequence for the next JO step** (a suggestion, not a result): to engage both zones,
the declared tilts must be placed around the live pre-tilt d ≈ −0.18 (window postures
included), for example tilts that bring the measured d to clearly positive values.
Because posture responds to the tilt, any such design should state its expected d from
these measured contributions and verify it as an integrity condition, not assume it.

The Step C labels and the encoder are unchanged.

## Limits

- **This is a geometric attribution of recorded states.** It makes no neural or causal
  claim.
- **Shapley attribution of a nonlinear function depends on the reference** (each arm's
  state 0, declared).
- **One context** (assisted posture, the Step C arms).
- **Stiffnesses are FlyGym defaults.** "Negligible antenna sag" holds for those values only.
- No motor coordinate status changes: 20/42 admitted, +4 conditional.

## Reproduce (Windows Git Bash)

The analysis refuses to overwrite an existing output, so a re-check writes a new file.

```bash
P="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
PYTHONPATH="$PWD" "$P" -m malecns_backend.embodiment.jo_operating_point --arms "$HOME/Documents/FlyBrainUnity/docs/evidence/antennal-gravity-live-v1/run" --output docs/evidence/jo-operating-point-v1/run/result.recheck.json
```

Expected output: `INTEGRITY_ACCEPTED`, with Q1 `DOMINANT_ROOT` and Q2 `DOMINANT_GRAVITY`
on both sides (about 8 minutes).
