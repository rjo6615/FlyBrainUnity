# Fixed six-foot matched contact calibration

## Purpose and scope

The live-v3 passive survey found exact Tarsus5 ground-contact/force agreement on
all six feet over 20001 samples, including both contact and no-contact samples.
That is posture-specific observational evidence. This batch provides the next
matched environmental calibration using the existing targeted runner, which
already supports a leg argument; its locked implementation is not changed.

Each of LF, LM, LH, RF, RM and RH receives one fresh control/contact pair, in that
fixed order. Both conditions use the existing fresh FlyGym physics and held-joint
protocol. This is not the live-v3 supported body context: it is an explicit
calibration fixture. It runs no MaleCNS, tactile encoder, neural delivery, motor
neuron decoder or gait controller. It does not measure balance or motor function.

The only planned difference within each pair is the existing surface placement:
0.01 model-unit control gap versus 0.0001 penetration above the conservative
Tarsus5 lower bound. The 0.025/0.025/0.002 half-size surface, adhesion-off position
control, 0.0001-second timestep, 0.05 seconds per condition, and engineering
comparison magnitude > 1e-12 remain fixed. No extra parameter, duration, force,
posture or seed-search options are exposed. Each leg is attempted once; a failed
leg is retained while remaining planned legs are attempted, not retried.

## Acceptance

The wrapper retains full legacy per-leg evidence and adds independent checks:

- both conditions contain all 501 samples with finite matched increasing times;
- vectors and their magnitudes are finite and mutually consistent;
- recorded contact truth agrees with exact unordered MuJoCo geom pairs;
- exact selected Tarsus5/surface names and fixed placement fields agree;
- complete reset qpos vectors match across conditions and remain unchanged by
  surface placement;
- the control never touches the selected surface and includes force-below-threshold
  negative samples; and
- the contact condition includes exact-pair positive samples, all above threshold.

COMPLETE means the planned conditions completed, not that calibration passed.
Only all passing checks yield MATCHED_CALIBRATION_ACCEPTED for a leg. Empty,
truncated, unavailable, inconsistent, nonfinite or disagreeing evidence cannot
pass. Nonfinite values are saved as null with explicit field paths and an invalid
classification; they are never silently accepted. A positive control force can
come from other collisions, including the floor: disagreement is not proof of a
bad biological sensor or a reason to tune the threshold. If the predetermined
placement fails, preserve that outcome rather than adjusting it until contact
appears. Repeated points in one contact manifold are not separate trials.

An accepted result validates this modeled force proxy in this fixture only. It
does not establish biological tactile thresholds, a measured rate response,
load sensing, reflexes, walking, or effects in the present live body context.
The next enabled/withheld neural experiment remains a separate step with a
matched baseline and explicitly modeled transduction. This runner never enables
sensory input automatically, even when all_six_accepted is true.

## Git Bash command

After merging the PR, run in the usual Windows backend Python environment:

```bash
cd ~/Documents/FlyBrainUnity
git switch newBrain
git pull origin newBrain
python -u -m malecns_backend.embodiment.six_foot_contact_calibration --live --output six-foot-contact-calibration.json
```

No Unity or CNS initialization is needed. It automatically runs twelve short
physics conditions. Let it finish and upload six-foot-contact-calibration.json.
A nonzero exit code means at least one foot did not pass; inspect the saved
report instead of changing parameters. FlyGym/MuJoCo must be installed. Output
is a new file; no historical locked artifact is overwritten. The full report is
written when the batch finishes; do not interrupt it.

Expected structural checks: six legs in the stated order, two conditions per
available leg, fixed protocol values, no CNS/tactile delivery, and complete raw
evidence. Zero contacts or disagreements are valid scientific outcomes. We do
not predict that all feet will pass the fixed placement.

Without --live the same command writes a NOT_RUN evidence template and exits
nonzero. That is not calibration data.

## Automated verification

```bash
python -m pytest -q tests/test_six_foot_contact_calibration.py tests/test_tactile_targeted_contact_calibration.py
```

The new tests reuse the actual legacy report builder with synthetic condition
measurements and verify acceptance, missing/malformed data, exact pair checks,
control contamination, fixed batch order/options, per-leg errors, strict JSON
and dry-run behavior. Physics is not simulated by these tests. The full live
six-foot calibration has not been run in the implementation environment.

Files added: six_foot_contact_calibration.py, its tests, and this document.
Existing calibration source, locked artifacts, runtime equations, motor
mappings, body support and live launcher are not modified.
