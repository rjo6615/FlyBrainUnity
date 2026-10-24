# FlyBrainUnity — local Codex handoff

Checkpoint: 2026-10-24. Repository: `rjo6615/FlyBrainUnity`.
Verified baseline for the negative-control update: `newBrain` at
`93e740477a6ad02f61bc341d313a7a77c53a46fd`, which merges PR #256.
Fetch and inspect current state before starting work.

## What the user wants

A scientifically controlled connectome-based fly whose movement emerges from
neural activity coupled to body physics and environmental senses. The intended
sequence is expanding the anatomically supported motor inventory toward all 42
coordinates, adding senses, then testing balance and locomotion. Stable gait
has not been established. Do not make neurons fire merely to make a joint move.
The user explicitly reaffirmed this constraint during the recent work.

Each update uses a new branch from latest `newBrain` and a PR back to `newBrain`.
The user reviews/merges. Include files changed, tests actually run, manual Git
Bash instructions and expected outcomes. Keep negative results and experimental
limitations visible. Read root `AGENTS.md` for enduring workflow requirements.

## Current runtime and code map

- `malecns_backend/neural.py`: calibrated NumPy LIF runtime; graph CSR rows are
  presynaptic. Default dt=0.5 ms, rest/reset=-52 mV, threshold=-45 mV,
  tau_mem=20 ms, tau_syn=5 ms, PSP scale=0.55, minimum synapses=6,
  refractory=3.76 ms, inhibitory gain=0.606. Conductance mode is active.
- `fly-brain-main/src/lif.js`, `src/brainmodel.js`, `src/ratenet.js`, and
  `public/data/brain_params.json`: checked-in fast-neural reference and calibration.
- `malecns_backend/live/__main__.py` and `live/headless.py`: live launcher/session
  factories. Default interface v1=11 motors; v2=17; v3=20. All currently use six
  tibia proprioceptive populations (392 neurons), with tactile delivery disabled.
- `malecns_backend/embodiment/_windows_m8_live_condition.py`: shared scientific
  transition kernel, observers and optional passive probes. Reuse it rather than
  invent a second embodiment loop. Its optional old tactile path selects LM only.
- `embodiment/sensory.py`: existing modeled tibia angle encoder. Preferred angles
  depend on frozen list order, not measured individual sensory tuning.
- `live/upstream_diagnostics.py` and `live/presynaptic_trace.py`: body-ID/readout
  checks, post-step states, selected shortest positive paths and input activity.
- `live/sensory_coverage.py`: offline midpoint/up/down prescribed-angle experiment,
  optional pathway diagnostics, no physical body or motor commands.
- `live/contact_readiness.py`: bounded passive live-v3 exact Tarsus5/force survey.
- `embodiment/tactile_contact.py`: existing contact-only onset encoder. Engineering
  threshold 1e-12 model force units, maximum modeled rate 120 Hz, 20-ms linear
  onset pulse, no sustained-contact retrigger. These are not biological measurements.
- `embodiment/tactile_targeted_contact_calibration.py`: legacy environment-only
  targeted calibration; already accepts all six leg arguments. Source is locked
  by later milestone provenance and should remain intact.
- `embodiment/six_foot_contact_calibration.py`: new fixed batch and strict evaluator.

The authoritative maps are checked-in artifacts; inspect consumers and tests
before editing. Do not infer roles from similar names. Historical COMPLETE data
can coexist with older narrative docs saying NOT_RUN; inspect actual artifacts.

## Established recent findings

### Candidate motors and prescribed sensory stimulation

The three investigated v3 channels are `joint_RFFemur`, `joint_LFTarsus1`, and
`joint_RFTarsus1`. All were silent in the original resting live run. Identity and
observer checks passed; input reached some cells but remained subthreshold.

A seed-1, 10-second-per-condition offline experiment recruited all 392 sensors:

| Candidate channel | Midpoint spikes | Upward sweep | Downward sweep |
|---|---:|---:|---:|
| Right front femur | 3 | 1 | 3 |
| Left front tarsus | 2 | 1 | 1 |
| Right front tarsus | 0 | 0 | 0 |

The traced repeat reproduced those totals. On selected path
815569 -> 800022 -> 903285 -> 820110, counts were 363/144/0/0 at midpoint,
404/148/2/0 upward, and 392/40/0/0 downward. Motor 820110 received excitation but
remained at least 6.2316 mV below threshold in upward-condition post-step samples.
Other selected intermediates 902679 and 46348 never spiked in these conditions.
Paths are structural examples, not exhaustive causal routes. Voltage is sampled
after spike reset and synaptic decay; maxima are not pre-spike peaks. Separate
excitation/inhibition peaks cannot be subtracted as simultaneous net drive.
These sparse results establish neither useful movement nor biological function.

### Neural scaling and neuromodulation

PR #252 corrected a demonstrated regional median convention mismatch: JS uses
upper middle size for even populations; Python had averaged the middle pair.
The canonical VNC input-scale effect is about +0.001515%, too small to claim as
an explanation/remedy for the silent tarsus. Actual calibrated JS constructor
and 160-step mixed-input parity checks pass. User independently ran the 14-test
neural/parity check successfully. See `embodiment/NEURAL_SCALING_AUDIT.md`.

Python removes OA fast signs but omits the reference's separate slow modulation
system. This documented scope difference is not automatically a bug. PR #253's
static reference audit found 37 OA cells, 16 IPCs and 10004 direct OA targets.
None of the 21 watched cells (including seven right-tarsus motors and selected
intermediates) has direct OA input at minSyn=6. No direct target is in a vnc_*
superclass; descending/ascending targets leave indirect effects possible.
No physiology was enabled. See `embodiment/NEUROMODULATION_SCOPE_AUDIT.md/.json`.

### Contact readiness: positive observational result

User ran PR #254's two-second current-v3 passive survey:
`v3-contact-readiness.json`, completed=true, 20001 samples, no tactile delivery.
All feet had positive and negative exact Tarsus5-ground contact samples.
Force-above-1e-12 matched exact contact presence with zero mismatches in every
sample for every foot. This is posture-specific correspondence evidence, not a
matched threshold calibration or proof of biological sensing/balance.

### Latest calibration: controls contaminated, no feet admitted

User ran PR #255's fixed six-foot calibration and uploaded
`six-foot-contact-calibration.json`. All twelve physics conditions completed.
Each condition contains 501 samples over 0.05 seconds at dt=0.0001 seconds.
All six feet failed exactly `control_never_touches_target_surface`; accepted_legs
is empty and all_six_accepted=false. Other strict checks passed.

| Foot | Control contact samples | Contact-condition contact samples | First control contact (ms) |
|---|---:|---:|---:|
| LF | 44 | 46 | 2.9 |
| LM | 92 | 92 | 3.1 |
| LH | 80 | 82 | 3.4 |
| RF | 45 | 46 | 2.9 |
| RM | 91 | 89 | 3.1 |
| RH | 79 | 83 | 3.4 |

The nominal negative surface starts with a 0.01 model-unit gap but is contacted
during the trajectory. Exact contact/force presence agrees in **all 6012 samples**
(6 feet x 2 conditions x 501). Thus the strict failure is the negative-control
design, not a demonstrated sensor failure. The older threshold evaluator filters
out contacted control samples before computing false positives; its
THRESHOLD_ACCEPTED output must not override the newer full-condition rejection.
Do not drop those samples, shorten the window after seeing contact times, or
weaken acceptance merely to admit the feet.

A derived machine-readable summary with source-file hashes is in
`docs/evidence/contact-calibration-checkpoint.json`. It is a summary of user-run
measurements, not the complete raw record or automatic experimental approval.
The raw uploads may not be committed; look in the user's repository/root outputs
before requesting files. If unavailable, retain the checkpoint and distinguish
what cannot be independently rechecked. Do not rerun an unchanged failed protocol.

## Latest update — separately versioned isolated control implemented

`embodiment/six_foot_contact_calibration_v2.py` implements the predeclared
collision-isolation protocol in `docs/SIX_FOOT_NEGATIVE_CONTROL_V2.md`. Both arms
exclude ground, self and other-foot collisions. The negative surface is remote
and collision-disabled; the positive permits only the exact selected pair.
This changes physical support/collision context and does not validate ordinary
live-v3 contact. Original v1 sources/evidence/acceptance remain intact.

Actual local physics completed both twelve-arm runs. Initial v2 rejected all feet
for implementation integrity defects (auto-generated namespaces and float32 norm
precision). The separately documented v2.1 correction fixes those contracts,
without weakening checks or changing physical/neural parameters. It was committed
before its justified verification repeat. All six pass v2.1 in the isolated assay.
Full rejected and accepted evidence, hashes, environment and checks are preserved
under `docs/evidence/six-foot-v2*.json.gz` and
`docs/evidence/six-foot-contact-v2-checkpoint.json`. See
`docs/SIX_FOOT_NEGATIVE_CONTROL_RESULTS.md` for counts and limits.

Immediate next decision: design how this isolated calibration transfers to the
intended supported live-body context, including unselected collisions, before a
separate matched tactile-delivery-enabled/withheld experiment. No delivery is
enabled by this update; acceptance here alone does not establish that transfer.

## Completed predecessor task — negative-control design requirements

1. Inspect the actual legacy calibration runner, six-foot wrapper/evaluator,
   latest raw report if available, and existing tests/provenance locks.
2. Identify a defensible environment-only negative-control design that maintains
   independently verifiable separation throughout the planned window. An initial
   gap alone is insufficient. State what collision sources the control excludes
   and how total force versus exact-pair contact will be interpreted.
3. Document/version the revised protocol before inspecting its outcomes. Keep the
   engineering threshold, transduction choices and neural parameters fixed. Any
   change of support, constraint or calibration context must be explicit and
   applied consistently where matching requires it; do not disguise it as a test
   of the ordinary live body. Do not tune surface offsets until it passes.
4. Implement a focused, separately versioned runner or reusable adapter and tests;
   preserve the locked legacy source and old evidence. Require exact identities,
   intact matched poses/schedules, clean negative evidence and verified positive
   contact. Record failed and inconclusive outcomes without automatic retries.
5. Open a PR from latest `newBrain` with concrete Git Bash commands. Run relevant
   local tests and, if the validated local physics environment is available, the
   approved bounded experiment. Report exactly which checks/experiments ran.

Do **not** enable tactile input yet. After an accepted calibration, the next
separate step is a matched tactile-delivery-enabled versus withheld experiment,
reusing the existing encoder with independent/common candidate sampling and
verified input/readout boundaries. Subsequent physical divergence in closed loop
can be an outcome; require matching before the intervention. Neither calibration
nor new motor activity by itself establishes balancing or gait.

## Local environment, tests and handoff usage

User's Git Bash checkout: `~/Documents/FlyBrainUnity`. Bare `python` has worked
for their recent runs. An older validated environment may be at
`fly-brain-interactive/.venv/Scripts/python.exe`; inspect rather than assume.
Node is needed for JS reference checks. Live physics needs FlyGym/MuJoCo; do not
silently install/upgrade physics dependencies or treat mocks as physics results.
The prior remote environment lacked FlyGym; local Codex should verify what is
actually available. Full CNS loading can take minutes; use physics-only tests
for the current calibration question. Unity is not required for these CLI runs.

Useful quick checks from repository root:

```bash
python -m pytest -q tests/test_six_foot_contact_calibration.py tests/test_tactile_targeted_contact_calibration.py
python -m pytest -q tests/test_live_contact_readiness.py tests/test_live_cli.py tests/test_live_headless.py tests/test_live_motor_diagnostics.py tests/test_live_pose_transport.py
python -m pytest -q tests/test_calibrated_neural_parity.py tests/test_neural_runtime.py
node --test tests/js/neuromod_scope_audit.test.mjs
```

Latest calibration implementation validation: 57 tests + 9 subtests passed across
the batch, old targeted calibration (including artifact locks), contact survey,
CLI/headless/motor/transport. Earlier broader neural-audit testing encountered
three missing-FlyGym failures and one differing historical-artifact comparison;
these reproduced with original code. Reassess locally rather than assuming
these remain the only failures or updating artifacts to pass tests.

Before edits, fetch, protect unrelated local changes and start a new branch from
`origin/newBrain`. Follow root agent instructions. Keep this checkpoint current
when a substantive new result changes the next decision.
