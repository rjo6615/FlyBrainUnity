# Antennal gravity sense, Step C (live JO tilt routing to leg MNs): results

Run 2026-11-05. The run used the preregistered protocol
`docs/evidence/antennal-gravity-live-v1/protocol.json` (sha 05655b40…), committed and pushed
in 0ef9dbe before any arm ran. All 37 arms ran once in fresh processes, and the run was
evaluated once.
- Two 50-step smoke arms (tilt moved early) checked plumbing only and were deleted unread.
- The raw `.json.gz` arms stay local (untracked); their sha256 values are in
  `run/report.json`. Per-arm progress is in `run/console.txt`.
- Design: `ANTENNAL_GRAVITY_LIVE_V1.md`.

These are executed physics + CNS simulations (FlyGym/MuJoCo, maleCNS LIF), not mocks.

## Verdict

| | Result |
|---|---|
| Integrity I1–I7 | **all pass → `INTEGRITY_ACCEPTED`**. REPRO_N0_7 reproduces the local N0_7 arm exactly. |
| Physical precondition (OFF arms < 45° from gravity) | pass: OFF peak tilt 17.5° |
| **G1** (C = +d, E = −d) | **`JO_TILT_PATTERN_CONSISTENT`**: ρ = 0.702, p = 2/64 = 1/32 (the floor). All 15 seed-pair correlations are positive (0.26 to 0.95). |
| **FLIP** (E = +d, C = −d) | **`JO_TILT_PATTERN_WEAK`**: ρ = 0.064, p = 14/64 = 0.219. 6 of 15 pair correlations are negative (−0.43 to 0.52). |
| r_GF (reported, not labelled) | +0.386. That is far from the −1 an additive response would give. |

The two assignments disagree. As declared, this is reported as it stands, and neither
assignment is promoted. Neither identifies the true zone sign.

## What the tilt actually did to the JO drive

At the first tick after the tilt, the per-seed means of the left and right d were:

| | UP (nose-up 10°) | DOWN (nose-down 10°) |
|---|---:|---:|
| OFF / FLIP arms | −0.331 to −0.341 | −0.007 to +0.003 |
| G1 arms | −0.337 to −0.374 | −0.044 to −0.006 |

The design expected DOWN d ≈ +0.03 and UP d ≈ −0.31, taken from Step B's geometry with a
level head. The live body starts slightly nose-up, so **DOWN only brought d to about zero.**
The sign-sanity check (d_DOWN > d_UP in every pair) passed as preregistered. But d stayed
at or below zero in both tilt directions, so the tilt hardly reached the "+d" zone at all:
- **Under G1,** the tilt contrast is almost entirely a change in **E-set** drive, from
  about 40 Hz (UP) to about 1 Hz (DOWN). The C set stays near 0 Hz.
- **Under FLIP,** the same contrast is carried by the **C set**, and the E set is silent.

So, in this context, the G1/FLIP comparison is effectively a comparison of the E route
against the C route, each modulated over the same range. It is not a test of the
sign-mirrored use of both zones. This was not anticipated in the design, and it is recorded
here, not corrected.

## Measured contrasts

**Leg MN pools.** 44 pools were included (leg × actuator class, at least one spike in any
seed arm in the window).

| Arm type | mean \|Δ\| per seed (Hz) | ‖S‖ per seed (Hz) |
|---|---|---|
| OFF | 0.39–0.80 | — |
| G1 | 1.03–1.74 | 12.0–28.4 |
| FLIP | 0.40–0.83 | 3.7–12.4 |

Under G1, 20 of the 44 pools have S of the same sign in all 6 seeds. The largest seed
medians are:
- positive (DOWN raises the rate relative to OFF): T3 right femur_twist +9.3 Hz,
  T3 right coxa_abduct +7.3 Hz, T3 right coxa +6.8 Hz, T3 right femur +1.0 Hz;
- negative: T2 right adhere_claw, coxa_twist and tarsus2, each −3.2 Hz; T2 right tibia
  −1.7 Hz.

Under FLIP, 11 pools have the same sign in all seeds, but they are all pools with a median
of 0 (silent contrasts).

**Descending neurons** (direct JO targets from Step A). These are DOWN − UP rates in Hz for
seeds 13–18.

| DN | OFF | G1 | FLIP |
|---|---|---|---|
| DNp73 | 0 in all | −15.5 to −21.3 | 0 in all |
| DNbe001 | 0 in all | −11.1 to −16.2 | 0 in all |
| DNg29 | 0 in all | −8.4 to −11.1 | −0.3 to −1.4 |
| DNp18 | 0 in all | −5.7 to −10.5 | 0 in all |
| pIP1 | 0 in all | −4.1 to −7.4 | 0 in all |

These five DNs are silent without JO input. Under G1, every one tracks the E drive with the
same sign in all six seeds. Under FLIP (the C route), only DNg29 responds, and weakly.

**Tonic effect before the tilt** (mean leg-MN rate, 0–500 ms, Hz):

| | Seeds 13–18 |
|---|---|
| OFF | 5.8–7.0 |
| G1 (E ≈ 17 Hz tonic) | 15.8–20.2 |
| FLIP (C ≈ 17 Hz tonic) | identical to OFF in 4 seeds, and 5.8–6.0 in the other two |

So the tonic E input alone roughly triples leg-MN activity. The tonic C input leaves it
essentially unchanged.

**Body.** Window means of pitch relative to gravity (+ = nose-down) were:

| | UP | DOWN |
|---|---|---|
| OFF | −15.4 to −16.0° | +6.5 to +6.7° |
| FLIP | the same as OFF to within 0.6° | the same as OFF to within 0.6° |
| G1 | −14.1 to −15.3° | +6.1 to +6.6° |

- **Roll.** The roll mean was 0.2–1.1° in OFF and FLIP, but 3.5–5.4° in G1, in both
  tilts. The tonic E drive acts on posture through the 20 admitted channels: a physical
  outcome of the neural input, not a balance response.
- **Peak tilt** relative to gravity was 17.5° in OFF, 18.9° in G1 and 17.4° in FLIP.
- **First ON/OFF physical difference** (G1_UP vs OFF_UP qpos) came at stored states
  371–676, which is 37–68 ms. That is well before the tilt.

**Per side.** The left and right means of S_G1 vary in sign across seeds. They are labelled
with the reconstruction asymmetry (right JO sets far less connected), and none is read as
roll sensing.

## Design expectations (written in the design before the run)

| Expectation | Outcome |
|---|---|
| JO drive difference of about 0.17 per 10° (DOWN ≈ +0.03, UP ≈ −0.31) | **Partly wrong.** The difference was about 0.33 between tilts, as expected, but the operating point was shifted: DOWN ≈ 0, UP ≈ −0.34. |
| Additive responses would give r_GF ≈ −1 (stated as a linearity check, not a prediction) | **Not additive.** r_GF = +0.39, and the two assignments got different labels. |

## Interpretation (as declared)

**G1 `JO_TILT_PATTERN_CONSISTENT`.** A sustained 10° pitch, encoded as E-set drive, passes
through the connectome to a seed-reproducible change in leg-MN activity beyond the other
senses. The main route is through the direct DN targets, chiefly DNp73 and DNbe001. This
establishes an information path that balance would need.
- It does **not** show the pattern is corrective. The largest effects fall on coxa and
  femur-twist pools that drive no admitted joint.
- It is not balance.

**FLIP `WEAK`.** The same tilt range delivered through the C set gives only a weak,
seed-inconsistent leg-MN pattern, and barely reaches the five DNs.

The difference between the two is **not** evidence about which zone is the true
gravity-sensing one. The tilt in this context modulates only one zone per assignment, and
the zone sign is a modelling choice. The difference shows that, as reconstructed, the E set
has far stronger downstream reach to leg MNs and these DNs than the C set. This is
consistent with the larger E populations and synapse counts from Step A.

## Limits

- **Modelled kinematic transduction.** The 120 Hz scale is an engineering choice, and the
  G1 label is arbitrary.
- **The tilt is idealised:** a step rotation of gravity, with no rotational transient.
- **The tonic E drive in G1 changes the body and network before the tilt** (roll 4–5°, MN
  rate ×3, physical divergence by 37–68 ms). Δ_OFF subtraction is therefore only a
  first-order control. Part of S_G1 may come from G1's different operating state rather than
  from the tilt-dependent JO signal alone.
- **The operating point sat at d ≤ 0,** so this tested one-zone modulation per assignment,
  not opposite-zone use.
- **Coxa MNs drive nothing,** so the MN patterns are read out. They act only through the 20
  admitted channels.
- **The right-side JO reconstruction is far less connected.** Sets were used as
  reconstructed.
- **Six seeds, one tilt size, one 1.5 s window.** p = 1/32 is the smallest p this design
  can produce.
- No motor coordinate status changes: 20/42 admitted, +4 conditional.

## Reproduce (Windows Git Bash)

The single-arm command writes `<arm>.json.gz` into the output folder; run it into a scratch
folder to avoid touching the evidence. The evaluator refuses to overwrite an existing
report, so a re-check writes a new file.

```bash
P="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
PYTHONPATH="$PWD" "$P" -m malecns_backend.live.antennal_gravity_live --arm G1_DOWN_13 --output scratch-recheck
PYTHONPATH="$PWD" "$P" -m malecns_backend.live.antennal_gravity_live --evaluate docs/evidence/antennal-gravity-live-v1/run --repro-ref "$HOME/Documents/FlyBrainUnity/docs/evidence/coxa-push-replication-v1/run/N0_7.json.gz" --cache "$HOME/Documents/FlyBrainUnity/.cache/malecns-v1" --output docs/evidence/antennal-gravity-live-v1/run/report.recheck.json
```
