# LF unit/conversion-lineage audit results

2026-10-25; fresh baseline6dcbc4f (merged PR277).
**LINEAGE_AUDIT_VERIFIED_CONVERSION_AND_PHYSICAL_SCALE_UNRESOLVED**.
This is a static source audit, not new physics, CNS, conversion or Unity execution.
Production remains20/42; new admissions0. All original evidence/locks retained.

## What was found

The local source fork contains `best_combined.osim`, `best_combined_full.osim` and
a63-page conversion PDF. The two OpenSim files have identical selected muscle
parameter sets. All were introduced alongside the locked MJCF in the same initial
source commit97d77223100135cea0e39a8493767255dfc2b65d. Shared history does not
identify which OpenSim input, converter version/configuration or edits produced
our exact XML. The snapshot records raw hashes, Git blob IDs, byte correspondence
to committed sources, source HEAD and the tracked-tree search scope.

| Selected muscle | OpenSim peak-force parameter | Locked MJCF peak-force parameter | Numeric ratio, not unit conversion |
|---|---:|---:|---:|
| Remotor/abductor |16.07337443|28.7481|1.78855412|
| Adductor |9.07997319|12.9|1.42070904|
| Anterior rotator |50.19042056|10.5807|0.210811144|
| Posterior rotator |98.16552432|157.429|1.60370966|

These distinct changes cannot be explained by one common numeric multiplier
alone. They do not establish an implementation defect: converter optimization
can alter model parameters. Both source models preserve100us/400us activation
constants numerically, which does not demonstrate biological time constants.
OpenSim fiber/slack lengths and contraction velocity are recorded alongside
MuJoCo lengthrange/normalized-range/vmax, without asserting one-to-one equivalence.

The OpenSim declarations are literally `m`/`N`, with gravity near9806.65. The locked
MJCF has gravity9801 and scaled meshes; target FlyGym has scaled gravity9810.
Those facts do not resolve the complete physical base-unit conventions. Target
clock seconds is documented. Source inertial masses and target raw geom masses
are separately inventoried; different body sets and compilation rules are not a
mass-unit calibration. All unsupported length/mass/time/force/torque/velocity
conversion entries remain null. No multiplier is averaged, selected or applied.

## Conversion evidence and limitations

The PDF is titled for `best_combined_full`. Full rendered pages1/50-53 show its
summary and four named LF muscle force-length comparisons. Text pages1/2/47 and
rendered overview48-63 were also inspected. Source-reported aggregate means/stds
are6.9522/6.9838cm (endpoints),.0375/.0447cm (moment arms),.1759/.0909Fmax (force).
These are printed claims, not independently reproduced measurements or acceptance
criteria. No exact hash link to our locked XML was established; printed cm/N plot
labels do not prove biological units. The PDF is hashed in the snapshot, not
redistributed or treated as exact-XML validation.

The recorded local tracked tree contains no matched conversion log, cvt1/cvt2
intermediate XML, Step1/2/3 validation inputs or converter revision/config under
the documented search patterns. This does not assert global absence. The author
repository's linked original-muscle endpoint remained inaccessible. No contact
with authors was attempted. [MyoConverter's pipeline documentation](https://myoconverter.readthedocs.io/en/latest/pipeline.html)
explains that conversion and moment-arm/force-length optimization are separate
stages; current generic documentation cannot identify the historical revision.
The source package declares MuJoCo3.3.2/dm_control1.0.30; the validated local
3.2.7/1.0.27 environment was not changed or represented as source-environment parity.

## Checks actually run

- **50 tests passed in 42.88s**: 14 new audit, 20 transfer-review and 16 binding checks. The actual
  saved-evidence reconstruction runs with native construction/forward/step/muscle
  dynamics, solver and live-audit fallback entry points made fatal. Other tests
  exercise XML identity failures, tamper rejection and refusal to infer a force
  conversion even from equal synthetic ratios or matching printed unit labels.
- Optional source-root check verifies original raw bytes and reparses both OpenSim
  models and the locked MJCF; PDF and package declaration raw bytes also checked.
- PDF reading used existing bundled pypdf/PDFium. An initial optional PyMuPDF
  import was unavailable; no installation or validated-environment change.
- Saved Windows Git Bash replay, staged whitespace check and LFS-pointer checks
  passed. No moving-fly or activation experiment was run.

## Windows Git Bash after merging

```bash
cd ~/Documents/FlyBrainUnity &&
git switch newBrain &&
git pull --no-rebase --no-edit &&
git lfs pull --include="malecns_backend/embodiment/interface_output/integrated_whole_leg_readiness.json,docs/evidence/lf-anatomical-crosswalk-v1/annotations.feather,docs/evidence/lf-pose-force-v1*/run/validation.json,docs/evidence/lf-activation-transient-v1/run/validation.json,docs/evidence/lf-activation-integrator-v1/run/validation.json,docs/evidence/lf-native-isolation-v1*/run/validation.json,docs/evidence/lf-synthetic-coupling-v*/run/validation.json" &&
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" &&
"$PY" -m malecns_backend.embodiment.lf_unit_lineage \
  --report docs/evidence/lf-unit-lineage-v1/run/audit.json
```

Expected: `UNIT/LINEAGE AUDIT VERIFIED`, physical conversion UNRESOLVED, coupling
BLOCKED, four diagnostic ratios,20/42,0new admissions and0physics/CNS transitions.
Original raw prerequisites recorded/current remain false at this checkpoint;
representation differences are displayed without rewriting history or admission.
Default replay requires no external clone/PDF runtime. Optional local source check:

```bash
"$PY" -m malecns_backend.embodiment.lf_unit_lineage \
  --report docs/evidence/lf-unit-lineage-v1/run/audit.json \
  --source-root "$HOME/Documents/FlyMimic"
```

## Roadmap and next decision

The active milestone remains a trustworthy LF proximal muscle-force interface,
not established independent balance or gait. Next predeclare and implement a
**non-actuating native target orientation-registration assay**, reusing the whole
existing15-pose source map and exact native LF identities. No force application,
integration or CNS; preserve geometry failures/inconclusive outcomes. This can
advance a separate geometry gate while physical scale stays blocked. Authoritative
unit/conversion records, anatomical binding, neural activation conversion and
original raw prerequisites remain required before moving-fly force transfer.
There is no new Unity behavior to inspect from this source audit.
