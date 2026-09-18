# M5D-2B — Controlled Tarsus5 contact calibration

## Scope and safeguards

This is an **engineering physics calibration** only. It does not import or run
MaleCNS, inject neural activity, decode motor neurons, implement gait, or alter
the M5D-2 encoder. The existing strict threshold remains `magnitude > 1e-12`
model force units. Neural propagation is `NOT_RUN`.

## Controlled-contact protocol

The default selected leg is **LM** and the selected physical segment is
`LMTarsus5`. Two fresh simulations use the same FlyGym model, 0.0001 s physics
timestep, duration, contact sensors, observation extraction, disabled adhesion,
and passive hold of the reset joint positions.

* **NO_CONTACT:** use the validated reset pose unchanged.
* **Candidate contact:** after reset, locate the model's single root free joint,
  lower its z coordinate exactly once by `0.1` model length units, call MuJoCo
  forward dynamics, then passively hold the measured joint pose. This is an
  explicitly reported deterministic initialization intervention. There is no
  iterative pose search and no target-force tuning.

At every bounded sample, the recorder stores simulation time, the raw selected
Tarsus5 force 3-vector, its Euclidean magnitude in model force units, and the
independent MuJoCo contact state.

## Independent physical-contact verification

The implementation resolves all MuJoCo geom IDs whose names contain
`LMTarsus5`, reads each of the `data.ncon` pairs from `data.contact`, and records
both geom IDs and names. A sample is `KNOWN_CONTACT` only when one of those
resolved IDs occurs in a contact pair. Force magnitude is never used as contact
ground truth. The report includes total contact count, opposing geom details,
and `selected_tarsus5_involved` for every sample.

## Threshold evaluation

Statistics (minimum, maximum, mean, median, 1/5/25/50/75/95/99 percentiles,
exact-zero fraction, and nonzero fraction) are computed separately from
metadata-confirmed no-contact and contact samples. False positives are
no-contact magnitudes strictly greater than `1e-12`; false negatives are
confirmed-contact magnitudes less than or equal to `1e-12`.

The result is `THRESHOLD_ACCEPTED` only when at least one verified physical
contact exists and both error counts are zero. Any error produces
`THRESHOLD_REQUIRES_REVISION`; absence of independently verified contact
produces `CALIBRATION_INCONCLUSIVE`.

## Checked-in result and required live run

The repository environment does not contain FlyGym or MuJoCo, so the checked-in
JSON is explicitly `NOT_RUN`: neither distribution has been measured here,
both error counts are zero only because both sample sets are empty, and the
classification is `CALIBRATION_INCONCLUSIVE`. This must not be interpreted as
threshold acceptance or physical contact validation.

Run the following in the validated Windows environment (from the repository
root):

```bat
python -m malecns_backend.embodiment.tactile_contact_calibration --live --leg LM --duration-s 0.05 --json malecns_backend/embodiment/interface_output/tactile_contact_calibration.json
```

If that run reports verified contact, its conclusion is limited to **physical
contact observability on LM**. Structural six-leg symmetry supports reusing the
measurement mechanism, but force distributions on LF, LH, RF, RM, and RH remain
unvalidated; this milestone performs no six-leg pose search.
