# LF unit and conversion-lineage audit V1

Read-only source audit, not an experiment, biological calibration or new admission.
The following rules govern the saved audit. No model construction, integration,
conversion/optimization rerun, dependency change or production coupling occurs.

## Scope and decision rules

- Start with the original locked FlyMimic XML and V1 transfer review. Preserve
  every upstream lock and all historical null/failed/inconclusive findings.
- Inventory the tracked local FlyMimic source tree and Git history. Extract the
  two included OpenSim models, exact selected muscle parameters, unit labels,
  gravity, representative body masses/inertias, and original MJCF parameters.
  Same names, approximate values or shared commits do not prove derivation.
- Compare numeric peak-force ratios as diagnostics only. Muscle optimization
  can change parameters independently; do not fit a conversion from these ratios.
  In particular no average, selected muscle, observation scale or gravity ratio
  becomes a physical force multiplier.
- Record a conversion PDF as independently inspected evidence. Its title, plots
  and printed units do not hash-bind it to the original locked XML. Do not use
  printed aggregate errors as new acceptance criteria or as a transfer pass.
- Record what the converter revision/configuration, intermediate models, logs,
  validation inputs and post-conversion edits actually establish. Missing records
  within the tracked-tree scope are missing, not inferred from `_cvt3` names.
- Inventory target raw geometry masses separately from compiled body masses.
  Do not compare aggregate masses of different body sets as a unit calibration.
- Supported declarations and diagnostic hypotheses stay distinct. Unsupported
  source/target physical conversion entries remain null. Target clock seconds
  is supported by the existing pinned source context.
- A verified audit means reproducible inspection, not verified conversion lineage
  or scientific admission. Verification must fail on changed source snapshots,
  altered identities/parameters, new conversions or fabricated lineage evidence.

## Primary references inspected 2026-10-25

- [Author FlyMimic repository](https://github.com/gizemozd/FlyMimic) describes the
  converted models and links to original OpenSim development. That linked
  `gizemozd/neuromechfly-muscles` endpoint remained inaccessible during inspection.
- [MyoConverter pipeline](https://myoconverter.readthedocs.io/en/latest/pipeline.html)
  distinguishes XML conversion, moment-arm optimization and force-length
  optimization. Logs, intermediate XMLs and validation outputs can document those
  steps; generic current documentation does not identify the revision used here.
- [MuJoCo 3.2.7 unit conventions](https://mujoco.readthedocs.io/en/3.2.7/overview.html#units-are-unspecified)
  require a consistent chosen base-unit system; numeric XML values do not specify
  it automatically.

Local source evidence is extracted from `rjo6615/FlyMimic`, recorded HEAD and file
introduction commits. It is not presented as a fresh authenticated upstream
checkout. The local source tree and untracked registration exports are not edited.
The source project declares Apache-2.0; this audit stores narrow data extracts and
hashes, not a replacement model or a redistributed PDF.

## Reproduction and limits

Normal replay uses pinned extracts and the existing transfer-review verifier;
it requires neither an external clone nor PDF libraries. Optional `--source-root`
rechecks the two original OpenSim raw files and locked XML, reparsing their data
without compilation. PDF bytes are checked too; visual interpretation remains a
recorded human/agent inspection, not an automated proof. Target XML extract hash
must agree with the original native input manifest.

If exact conversion lineage remains unavailable, keep force coupling blocked.
The next independent gate can be a **non-actuating target orientation-registration
assay**, separately specified before execution: reuse existing source poses/map,
resolve exact native LF bodies/joints, compare target frames and finite-angle
derivatives, with zero force application/integration/CNS. It can test geometry
without inventing mass/force units. It does not resolve physical scaling,
anatomical binding, neural conversion or original raw prerequisites. Authoritative
conversion records are still needed before choosing a physical force transfer.
