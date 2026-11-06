# Rhythm, Step R1b: does our neuron-size scaling match the preprint's? (design)

Designed 2026-11-06. Preregistered 2026-11-06 in `docs/evidence/dng100-size-audit-v1/protocol.json`
(sha256 3813e577…); not yet run. Structure-only audit: no neural simulation.

## Why this step

R1 (`DNG100_RATE_MODEL_RESULTS.md`) ran the preprint's rate model on our front-left network and
never engaged the E1–E2–I1 core:
- 58 of 64 DNg100 replicates had no active front-left MN;
- the silenced conditions were bit-identical to DNg100 alone.

In that model each neuron's gain and threshold scale with its size relative to the dataset
median (a = a*/s, θ = θ*·s). DNg100_L had s = 30.7, so at the preprint's starting drive it fired
below 1 Hz.

**A likely mismatch in what "size" means.** The preprint used MANC, a connectome of the
**ventral nerve cord only**. A descending neuron (DN) or ascending neuron (AN) in MANC is cut
off at the neck, so its MANC volume is only its nerve-cord portion. Our maleCNS is the whole
CNS, so `neuron_size.bin` gives a DN's **whole** volume, brain arbor included. If DNg100's size
is mostly in the brain, R1 used an s several times larger than the preprint's model would. That
would be an implementation-fidelity difference, not a biological finding.

R1b asks:

> **How much does using whole-CNS volumes, instead of nerve-cord-only volumes, change the size
> scaling of DNg100 and the other neurons in R1's network? Is the difference large enough to
> count as a material fidelity defect in R1?**

It does **not** re-run R1, change any drive, or look for a rhythm. If the defect is material,
the correction is a separately preregistered R1 v2.

## Evidence gathered for this design (structure only)

- **Size values.** `fly-brain-main/public/data/neuron_size.bin` holds one float per neuron.
  - No checked-in script documents its source or units.
  - The values fit whole-neuron voxel counts: DNg100_L is 1.67e10. The nerve-cord median R1 used
    is 5.43e8.
  - Units cancel in s, which is a ratio. What matters is which part of each neuron is counted.
- **Local skeletons.** `fly-brain-main/public/data/skeletons.flys` is display skeletons decoded
  by the checked-in `src/codec/skel.js` `decodeSkel`.
  - It covers all 165,122 neurons, none missing, with 5.28 million vertices, in µm.
  - DNg100_L has 484 vertices; E1, E2 and I1 have 46–75.
- **The neck is visible in the coordinates.** Along the third axis (z, µm), percentiles
  (1st / 50th / 99th) of every 7th vertex by region:

  | Region | 1st | 50th | 99th |
  |---|---|---|---|
  | Central brain | 96 | 198 | 299 |
  | Optic lobe | 166 | 266 | 343 |
  | Nerve cord intrinsic (vnc_*) | 544 | 766 | 1,045 |
  | DN/AN | 146 | 588 | 1,008 (they span both) |

  So a single z plane can separate brain from nerve cord. Its exact position is set by a rule
  below, not by eye.

## Method

**1. Neck plane.**
- Brain-intrinsic neurons are central-brain and optic-lobe superclasses (`REGION_OF` regions
  0 and 1, excluding DN/AN/sensory_*/efferent). Cord-intrinsic neurons are superclasses
  starting `vnc_`.
- z* is the plane that minimises the fraction of misclassified vertices: brain vertices with
  z > z*, plus cord vertices with z < z*. It is searched in 1 µm steps over all vertices.
- The misclassification rate is reported. It must be < 1 % (gate G1).

**2. Nerve-cord fraction per neuron.**
- For neuron i: f_i = (skeleton cable length with z > z*) / (total cable length).
- A segment crossing z* is split at the plane.
- Cable length is the sum of segment lengths from `decodeSkel` `seg`/`pos`.

**3. Nerve-cord size proxy:** size_VNC,i = size_i × f_i.
- **This assumes volume is spread along the cable in proportion to length.** That is not
  exact, because thick neurites hold more volume per µm. The proxy is a declared
  approximation, and its limits are listed below.

**4. Scaling under both definitions.**
- s_R1,i = size_i / m_R1, with m_R1 = 542,747,200, R1's nerve-cord-region median.
- s_VNC,i = size_VNC,i / m_VNC. m_VNC is the same median rule (upper-middle element of positive
  values over the same superclass set) applied to size_VNC.
- Ratio ρ_i = s_R1,i / s_VNC,i. ρ > 1 means R1 over-scaled the neuron.

**5. Report:**
- ρ and both s values for DNg100_L/R, E1, E2, I1 and the 68 MNs;
- the distribution of ρ over R1's network by class: MNs, cord-intrinsic premotor, ascending
  premotor, DNs;
- the number of network neurons with s > 20 under each definition;
- m_R1 and m_VNC.

## Labels (declared now)

| Label | Rule |
|---|---|
| `SIZE_MISMATCH_MATERIAL` | G1 passes and either (a) ρ ≥ 2 for DNg100_L, or (b) the median ρ over R1's network DNs is ≥ 2. |
| `SIZE_MISMATCH_MINOR` | G1 passes and neither (a) nor (b). |
| `INCONCLUSIVE` | G1 fails (no clean neck plane); or DNg100_L, E1, E2 or I1 has zero cable length; or a source hash mismatch. |

For cord-intrinsic neurons (E1, E2, I1, MNs), f ≈ 1 is expected, so ρ ≈ m_VNC / m_R1. That is
reported but does not drive the label.

**Integrity**
- I1: source sha256 values for `neuron_size.bin`, `skeletons.flys`, `skel.js`, `meta.json` and
  `neurons.bin`, plus the maleCNS cache fingerprints through `load_cache`.
- I2: dense index ↔ skeleton index identity. Skeleton N equals meta N, and for 20 declared
  neurons (the five core cells and 15 rng-drawn ones) the soma lies within the skeleton's
  bounding box.
- I3: synthetic unit tests for the plane search, segment splitting and ρ.

## Expectation (recorded before computing anything beyond the table above)

- **X1:** `SIZE_MISMATCH_MATERIAL` through (a). Basis: DN arbors in the brain are often
  extensive. DNg100_L's z extent and cable split have not been computed. This is a guess; a
  wrong guess is recorded as wrong.

## What each outcome means (declared now)

- **MATERIAL:**
  - R1 over-scaled the stimulated DN, and possibly the network's DNs. Under the preprint's
    definition they would respond to much less drive.
  - R1's non-engagement is then at least partly an artefact of our reconstruction.
  - Next: a preregistered **R1 v2** using size_VNC for DNs and ANs (cord-intrinsic neurons
    unchanged), with everything else as R1, and R1's evidence kept as recorded.
- **MINOR:** the size definition does not explain R1's non-engagement. The next question is
  the descriptive recruitment map: where DNg100's signal stops on its way to E1/E2/I1 and the
  MNs, at fixed declared drives.
- **In neither case** does it show a rhythm or say anything about the LIF engine.
  - The LIF engine also uses size scaling (`region_scales`, size_alpha 0.609, capped).
  - Any bearing on V1 would be a separate question.

## Limits

- **Cable-length proxy for volume.** It is not a measured nerve-cord volume. Thick axons in the
  neck connective could make the true f differ.
- **Display skeletons are coarse** (DNg100_L has 484 vertices), so cable length is
  approximate.
- **A single plane approximates the neck.** G1 reports how well it separates the two regions.
- **The source of `neuron_size.bin` is undocumented.** Only the relative definition is
  audited, not the absolute units against MANC. MANC data stay unused: the project is
  local-only, and no download or request is made.
- **Structure only.** No simulation, no rhythm claim, no motor coordinate status change
  (20/42 admitted, +4 conditional).

## Build and run plan (on approval)

1. `docs/evidence/dng100-size-audit-v1/protocol.json`: rules, source hashes and the I2
   neuron draw.
2. A Node script, `tests/js/` or `fly-brain-main/scripts/`-style, using `decodeSkel`, that
   exports per-neuron total and z > z* cable plus the plane search. A Python module,
   `malecns_backend/embodiment/dng100_size_audit.py`, computes ρ, the labels and the report,
   reusing `region_scales` for the median rule.
3. Synthetic tests for the plane search, crossing-segment split, ρ and label rules.
4. Commit and push the preregistration; run once (seconds); record the results, handoff and
   roadmap.

## Build-time amendments (before any plane, cable fraction or size ratio was computed)

- **Brain superclasses, stated exactly.** Names starting `cb_`, `ol_` or `visual_`, excluding names
  containing `sensory` or `efferent`. `ENS` and `unknown` are not named central-brain or optic-lobe
  superclasses and are left out.
- **I2 tolerance and soma unit.** The soma must lie within the skeleton's bounding box ± 10 µm (the
  design gave no tolerance; display skeletons can stop short of the soma). Soma values are 8 nm
  units (× 0.008 = µm), found by comparing the first 100 neurons' somas with their skeleton
  extents. The I2 draw is `default_rng(20261108)`, 15 neurons with skeleton vertices and a finite
  soma; `--describe` showed all 20 checks inside before registration.
- **Edge cases declared.** f = 0 gives ρ = ∞ (counted in the DN median); no cable gives NaN
  (excluded and counted). The plane tie rule is the lower-middle minimising candidate.
- **Pipeline.** `skeleton_dump.mjs` runs the checked-in `decodeSkel` and writes a temporary flat
  binary; all computation is in `dng100_size_audit.py`.
- **Tests.** Two synthetic tests first failed from arithmetic errors in their own expected values
  (tie range and an upper-middle median), not in the module; corrected.
