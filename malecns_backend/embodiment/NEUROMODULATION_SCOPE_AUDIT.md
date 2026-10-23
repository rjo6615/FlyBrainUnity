# Slow neuromodulation: scope before intervention

## Result

Using the checked-in reference Neuromod class, canonical raw graph, and calibrated
minimum of six synapses, none of the seven right-front-tarsus motor neurons or
selected pathway intermediates is a direct OA target. The two responsive motor
comparison cells also have no direct OA input. All 21 watched cells have zero
held-fed threshold shift in this static calculation.

The reference contains 37 OA cells, 16 IPCs, and 10004 unique direct OA targets.
The target superclass inventory contains no `vnc_*` class. It does contain 227
descending and 80 ascending neurons, so indirect effects on the tested pathways
remain possible. Direct anatomical exclusion is not proof of no network effect.
Do not use this result to invent OA input or lower the watched cells' thresholds.

## What the reference actually does

Source: `fly-brain-main/src/sim/neuromod.js` and `src/sim/fly.js` at the baseline
recorded in this PR. The fast neural constructor separately removes OA fast
transmitter signs. The slow system then:

- selects OA cells by `OA-` type prefix and IPCs by exact `IPC` type;
- initializes low-pass modeled rates at 2 Hz for OA and 5 Hz for IPC;
- uses index-keyed resting-threshold calibration from `neuromod.json`;
- adds sugar-dependent IPC conductance and AKH/insulin-dependent input to an
  assumed OA receptor subset; locomotor feedback supplies another input;
- updates release every 10 ms and target threshold shifts every 50 ms;
- accumulates **raw anatomical OA counts** meeting the cutoff, not fast effective
  weights (which are zero for OA); and
- sets a saturating target threshold shift `2*x/(x+400)` mV, where x is the sum
  of OA anatomical counts times modeled release rates. Modulatory cells have
  their own threshold/AHP update.

FlyAgent calls the slow update every 1 ms before two 0.5-ms neural steps. Its
energy and locomotion signals come from the reference body/behavior context.
Porting only the threshold formula would not reproduce that context.

## Scientific status and assumptions

This is a controlled modeling project, not an exact or fully validated biological
replica. The reference itself explicitly states that OA receptor identities per
cell are unavailable: it treats synaptic targets alike and assumes the AKHR OA
subset from cell-type names. Its energy scaling, thresholds, rates, and 2-mV
shift are model choices/calibration, not measurements from these watched cells.
`neuromod.json` records calibration at fedEnergy 0.85 for 60 seconds. This is not
an instruction to choose an energy value that makes a motor fire.

The audit verifies that calibration indices cover exactly the current OA/IPC
populations and that values are finite. That checks population consistency, not
independent experimental validation of each calibrated threshold. Source hashes
in the JSON identify the exact inputs used. Body IDs are serialized as strings.

The report calls the actual reference `modulate()` on a detached threshold-only
receiver with the reference's held initial fed rates. It runs no LIF integration,
changes no live brain state, and predicts no spikes. Zero direct shifts here
also follow from missing qualifying OA edges, irrespective of the chosen held
OA rate. This is a structural scope result, not a dynamic neuromodulation trial.

## Decision

Do not enable a new physiological mechanism by default on this evidence. There
is no direct OA correction to apply to the silent right-tarsus neurons in this
reference model. A later indirect-effects experiment may still be useful, but
must be explicit and optional, preserve the current baseline, use the complete
reference mechanism and a prospectively specified physiological input schedule,
and report recruitment and numerical stability even when the result is negative.
It must not tune per-joint gains, thresholds, weights, or select successful seeds.
Any improvement would establish an effect within the modeled conditions, not
biological correctness or gait.

That future experiment must also distinguish neuromodulation from the reference
Intrinsic and Motor modules: copying their behavior decisions/gait machinery
would not establish neurally emergent locomotion in this project.

## Reproduce and review

Node is sufficient; Python, Unity, FlyGym and MuJoCo are unnecessary:

```bash
node --test tests/js/neuromod_scope_audit.test.mjs
node fly-brain-main/scripts/neuromod_scope_audit.mjs --output neuromodulation-scope.json
```

Expected: 3 passing tests; 37 OA cells, 16 IPCs, 10004 unique direct targets, all
21 watched cells with zero direct OA synapses and held-fed shift. Compare the
output against `NEUROMODULATION_SCOPE_AUDIT.json`. Repeated runs on identical
source data should be byte-identical. The tests cover raw-count/cutoff semantics,
actual reference shift calculation, deterministic output, unchanged input data,
calibration population failures, finite values and unknown watched identities.
No motor movement is an expected or required outcome of this audit.

Modified files are the standalone audit script, its Node tests, this report, and
the generated static JSON. No runtime model or live launcher is modified.
