# M5D-2C — Targeted LM Tarsus5 surface-contact calibration

## Scope and checked-in status

This is a physics-only measurement. It does not run neural propagation,
generate tactile spikes, inject drive, decode motor neurons, or apply neural
motor output. The tactile threshold remains the unchanged, **provisional**
strict comparison `magnitude > 1e-12` model force units.

The checked-in JSON has `run_status: NOT_RUN` because this repository
environment does not provide the validated Windows FlyGym/MuJoCo runtime. It
therefore reports zero measured samples, `NO_VERIFIED_CONTACT`, and
`CALIBRATION_INCONCLUSIVE`; those values are not a physical result.

## Matched physical protocol

Each condition creates a fresh Fly and simulation with the ordinary reset
pose, position control, adhesion disabled, a 0.0001 s timestep, and the same
36 contact-sensor placements. A static box geom named
`m5d2c_calibration_surface`, with half-size `(0.025, 0.025, 0.002)` model length
units, is the sole added environment object.

After reset, the implementation resolves the exact namespace-independent geom
basenames `LMTarsus5` and `m5d2c_calibration_surface`. It reads the distal
geom's `geom_xpos` and conservative `geom_rbound`; the estimated world lower
bound is `geom_xpos.z - geom_rbound`. The surface is centered at the Tarsus5 x
and y coordinates. Its top is placed:

* **CONTROL:** exactly `0.01` model length units below that lower bound.
* **CONTACT:** exactly `0.0001` model length units above that lower bound (one
  predetermined penetration offset).

This is one bounded geometric placement, not iterative force tuning. No fly
root, joint, actuator, adhesion, timestep, physics, or contact parameter is
changed. The full `qpos` vector is captured immediately before and after the
surface move and the live run aborts unless the vectors are exactly equal.

## Independent verification and observations

Every sample records simulation time, the raw LM Tarsus5
`observation["contact_forces"]` vector, magnitude in **model force units**,
`data.ncon`, every MuJoCo contact pair with IDs and names, whether the selected
pair is present, and ground truth. `KNOWN_CONTACT` requires the exact unordered
pair comprising the resolved LM Tarsus5 geom ID and resolved calibration
surface geom ID. Self-contact, another leg or segment, generic contacts, and a
nonzero force observation cannot establish ground truth.

Sensor correspondence is classified as follows:

* `SENSOR_CORRESPONDENCE_CONFIRMED`: at least one exact-pair contact sample
  exists and at least one corresponding selected force magnitude is nonzero.
* `CONTACT_CONFIRMED_SENSOR_ZERO`: exact-pair contact exists but all selected
  force magnitudes are zero.
* `NO_VERIFIED_CONTACT`: the exact pair never occurs.

Only the first classification permits evaluation of `magnitude > 1e-12`.
Otherwise the threshold classification is `CALIBRATION_INCONCLUSIVE`, and
false-positive/false-negative fields remain null rather than suggesting a
measurement was performed. A correspondence-confirmed report includes sample
counts, min/max/mean/median, 1/5/25/50/75/95/99 percentiles, exact-zero
fractions, and strict-threshold false positives and false negatives.

## Result fields to inspect after the authoritative live run

The JSON identifies both exact geoms under `control` and `contact`, documents
surface positions and offsets under `placement`, and provides the full reset
pose proof under `pose_proof`. Top-level fields report verified-contact and
nonzero-force sample counts, correspondence classification, and threshold
classification. If the one predetermined placement fails to make the exact
pair, stop with `NO_VERIFIED_CONTACT` / `CALIBRATION_INCONCLUSIVE`; do not tune
the offset.

## Exact Windows command

Run from the repository root in Command Prompt or PowerShell:

```bat
python -m malecns_backend.embodiment.tactile_targeted_contact_calibration --live --leg LM --duration-s 0.05 --json malecns_backend/embodiment/interface_output/tactile_targeted_contact_calibration.json
```

Do not proceed to neural propagation.
