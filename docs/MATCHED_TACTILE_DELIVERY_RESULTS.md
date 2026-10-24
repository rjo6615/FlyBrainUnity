# Matched tactile delivery — 2026-10-24

The fixed protocol and experimental boundary were committed at 24af69f before
execution, from latest origin/newBrain def9f24. One WITHHELD arm then one ENABLED
arm ran in the existing FlyGym 1.2.1 / MuJoCo 3.2.7 / NumPy 2.0.2 environment.
Each completed 20000 physics transitions, 4000 neural updates and 20001 states.
No retries, scientific revisions, source-lock refreshes or parameter tuning ran.

All predeclared integrity checks passed: exact initial matching, calibrated ground
context in both arms, independent/common candidate sampling before feedback,
2269-slot common CNS uniforms throughout, actual refractory eligibility, external
delivery masks, unmodified proprioceptive delivery and verified motor readouts.
The locked encoder, neural runtime, kernel and ordinary live factory are unchanged.

## Measured simulation outcome

| First measured boundary | Simulation time |
|---|---:|
| Eligible tactile delivery opportunity / CNS divergence | 0.5 ms |
| Downstream state divergence excluding all external-input neurons | 2.5 ms |
| Downstream spike divergence excluding all external-input neurons | 5.5 ms |
| Mapped motor spike, decoder and command divergence | 14.5 ms |
| Measured joint, whole-physical-state and contact-force divergence | 14.6 ms |

| Foot | WITHHELD eligible / delivered | ENABLED eligible / delivered |
|---|---:|---:|
| LF | 575 / 0 | 8557 / 8557 |
| LM | 607 / 0 | 5051 / 5051 |
| LH | 1229 / 0 | 21060 / 21060 |
| RF | 773 / 0 | 1255 / 1255 |
| RM | 840 / 0 | 11483 / 11483 |
| RH | 2454 / 0 | 17025 / 17025 |

After physical feedback diverges, contact onsets and candidate totals may differ;
they are not required to remain identical. The pre-delivery and pre-feedback
matching checks passed. These are onset events from the unchanged encoder, not
an artificial sustained-contact retrigger or a retry selected for activity.

Among the previously investigated v3 motor channels, WITHHELD/ENABLED observed
spike totals were right-front femur 0/56, left-front tarsus 0/9, and right-front
tarsus 0/0. Motor readout spikes and physical joint motion are different measures:
passive mechanical coupling can move a coordinate whose mapped neurons are silent.

Full-window **posthoc descriptive magnitudes**, not acceptance thresholds:
maximum A/B measured joint differences included left-middle tibia 15.10 degrees,
left-front femur roll 13.48 degrees, right-middle tibia 13.44 degrees, right-front
femur 7.29 degrees and left-front tarsus 6.27 degrees. Maximum root separation was
0.291869 model mm; final separation was 0.203117 model mm. Separation between arms
is not distance walked. All 42 coordinate differences and per-channel spike
totals are preserved in the checkpoint.

This supports a tactile-input effect through the simulated CNS/motor/body loop
under this modeled transduction and paired sampling context. It does not establish
useful movement, biological sensory physiology, balance, gait, or generalization
to other seeds, poses or collisions. No positive calibration-surface coverage was
present; both trajectories retained verified ground attribution without ambiguous
direct sources. The prospective common-slot assay schedule differs from ordinary
live compact RNG sampling in both arms. Ordinary live tactile delivery is still off.

## Evidence and checks

`docs/evidence/matched-tactile-v1.json.gz` preserves the complete pair (566098712
raw JSON bytes / 143669202 gzip bytes) through Git LFS. The checkpoint records both
hashes, implementation commit, protocol, environment, full evaluation and descriptive
magnitudes. It is a summary, not a replacement for raw evidence. Existing prior
failed and accepted results, original local commits and replay deletions remain intact.

The recorded-pose replay uses the existing output-only 42-joint protocol and
server. A real TCP smoke check verified hello and two actual recorded endpoint
poses without CNS/physics steps. Synthetic replay tests cover individual and
alternating arms. No Unity Editor or visual-rig validation was executed here.

Automated results: 166 tests plus 9 subtests pass in the focused experiment,
calibration, attribution, propagation and live-boundary suites, including full raw
paired-evidence hash/source verification and re-evaluation. The separate older
tactile-contact suite has 6 passing tests and one unchanged baseline hash failure.
Its historical cause is documented in MATCHED_TACTILE_DELIVERY_V1.md; no lock or
artifact was rewritten. Whitespace checks pass. Actual dry CLI exits 1 / NOT_RUN;
exclusive-output and partial-error behavior are tested.

## Unity review now

Use the existing `FlyBrainUnity` project and `Assets/Scenes/LiveFly.unity`. No scene
regeneration is needed. If the scene is absent, the existing menu is
`FlyBrain > Live Fly > Create Live Fly Scene`. Run only one pose publisher on 8765.

In Git Bash from this PR checkout:

```bash
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
git lfs pull --include="docs/evidence/matched-tactile-v1.json.gz"
"$PY" -m malecns_backend.live.tactile_replay --input docs/evidence/matched-tactile-v1.json.gz --condition BOTH --speed 0.1
```

The command first validates the saved pair, which can take time; it does not
initialize a CNS. Once it prints RECORDED, enter Play in LiveFly. WITHHELD then
ENABLED each play for about 20 wall seconds with a one-second pause, repeating
until Ctrl+C. Simulation time rewinds between saved clips. The terminal labels
the active recorded condition; the existing Unity overlay shows connection and
pose diagnostics, not sensory spike counts. Use `--condition ENABLED` or WITHHELD
for one arm, or `--once` to stop after one pass.

Compare middle/hind tibia and femur-roll changes, then the right-front femur and
left-front tarsus. A normal `python -m malecns_backend.live --motor-interface v3`
session remains the existing proprioceptive-only baseline; it does not enable
this experiment by merging the PR. This replay is review of measured poses,
not another scientific run or a newly scripted movement controller.

Manual regression command (expected 166 passed, 9 subtests passed):

```bash
"$PY" -m pytest -q tests/test_matched_tactile_delivery.py tests/test_live_contact_context.py tests/test_six_foot_contact_calibration_v2.py tests/test_six_foot_contact_calibration.py tests/test_tactile_targeted_contact_calibration.py tests/test_live_contact_readiness.py tests/test_live_cli.py tests/test_live_headless.py tests/test_live_motor_diagnostics.py tests/test_live_pose_transport.py tests/test_tactile_propagation.py
```

Next: inspect this paired replay and review the intervention/context evidence
before designing any ordinary live tactile mode, further motor expansion or
balance experiment. Preserve the silent right-front tarsus result.
