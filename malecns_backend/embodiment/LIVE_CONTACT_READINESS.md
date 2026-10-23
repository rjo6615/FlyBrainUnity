# Contact feedback readiness in the current live v3 posture

## Audit decision

The current checked-in historical LM artifacts are COMPLETE: targeted Tarsus5
calibration reports SENSOR_CORRESPONDENCE_CONFIRMED, propagation reports P7, and
the 100-ms motor experiment reports
MOTOR_CAUSALITY_CONFIRMED_NO_FEEDBACK_WITHIN_WINDOW. Some old narrative milestone
documents still describe their original NOT_RUN placeholders. Use the actual
result files and locked scope; do not mistake those old descriptions for the
current artifact status.

Those experiments concern LM Tarsus5 with a particular calibration surface.
They do not validate all six force rows in the present live posture. The existing
TactileContactEncoder models a 120-Hz maximum, 20-ms onset transient at the
engineering threshold 1e-12 model force units. These are engineering choices,
not biological response measurements. It must not be enabled for new contexts
merely to obtain additional motor activity.

The current live v3 factories explicitly use proprioception_only=True. The
legacy optional tactile path in the shared kernel selects only the LM encoder
frame. Existing tarsal-contact telemetry aggregates Tarsus1 through Tarsus5;
it is broader than the encoder's selected Tarsus5 force row. The new passive
survey supplies the missing exact-distal observation before defining a matched
sensory-delivery experiment.

## New observation

At every observed physics step, the survey reads the existing force observation
and exact compiled geometry identities. It records, per leg:

- Tarsus5 force row (5, 11, 17, 23, 29, 35), magnitude and peak;
- whether a geom attached to the exact Tarsus5 body contacts a recognized ground
  geom (using the existing compiled-name ground inventory);
- counts of contact with/without above-threshold force, force without ground
  contact, and neither;
- first exact contact-pair IDs and contact onsets (including initial observed
  contact, which need not be a newly occurring physical onset).

The standalone observer opts in with collect_distal_contact. Ordinary live
observers do not request or compute these additional fields. The survey has no
encoder, neural RNG, event-delivery, motor-controller, support or parameter
mutation. The existing v3 session continues its ordinary proprioceptive/motor
operation while the observer collects bounded aggregates. Added observation may
increase wall time but does not change the modeled simulation timestep.

A contact/force coincidence is observational evidence, not calibrated force
attribution. A force without ground contact can reflect collision with another
object or the fly itself; it is not automatically a sensor false positive.
The ground inventory recognizes named ground/surface/platform geoms and is not
an inventory of arbitrary possible external objects. No-contact and zero-force
outcomes remain inconclusive for contexts not encountered during the survey.

No report status automatically admits tactile delivery or establishes a
biological threshold, load sensor, neural effect, or balancing reflex. The
next experiment must retain matched initial physics, support and neural
parameters, generate comparable candidate inputs, and withhold delivery in its
control. Post-intervention physical trajectories can diverge in closed loop;
they are outcomes, not necessarily matching failures. No such matched comparison
is claimed in this PR.

## Manual measurement

After merging/pulling newBrain, from the repository root in the normal validated
Windows Python environment (FlyGym/MuJoCo and full connectome data required):

```bash
python -u -m malecns_backend.live.contact_readiness --duration-s 2 --output v3-contact-readiness.json
```

Unity is not required. Let the command stop automatically after two simulated
seconds; wall time includes ordinary CNS initialization and can be much longer.
No Ctrl+C is needed. If interrupted, a partial report is saved with
completed=false and must not be treated as the full experiment.

Expected: completed=true, positive samples, six leg records, correct force-row
indices, and tactile_delivery_enabled=false. Contact counts need not be positive
for every leg. Share v3-contact-readiness.json; we will use it to choose the
supported scope for the matched enabled/withheld experiment. No threshold, force,
posture, duration or neural gain should be adjusted in response to a null result.

Fast automated checks (no physics execution):

```bash
python -m pytest -q tests/test_live_contact_readiness.py tests/test_live_cli.py tests/test_live_headless.py tests/test_live_motor_diagnostics.py tests/test_live_pose_transport.py
```

The real live survey has not been executed in the implementation environment.
Tests use geometry/force doubles and check exact Tarsus5 ownership, reversed pair
ordering, exclusion of other tarsal contacts, input immutability, invalid values,
bounded sampling, saved output and interruption cleanup.
