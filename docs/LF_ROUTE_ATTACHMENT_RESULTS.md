# LF source-route / target-attachment audit results

2026-10-25; fresh baseline4702f8e (merged PR279).
**ROUTE_AUDIT_VERIFIED_TARGET_ATTACHMENTS_UNRESOLVED**.
Static source and saved-evidence review; no new native/physics/CNS experiment.

## Evidence established

The four selected single-class tendon hypotheses each use two ordered source
sites: first owned by the exact XML Thorax body, second by LFCoxa. All eight
definitions are unique and have explicit finite local coordinates. Existing
binding inspector, complete source XML/assets manifest and source-pose authority
are reused. Raw actuator parameters and route order are unchanged. The wider
five-population/seven-hypothesis review and unresolved individual neuron binding
are not replaced by this narrower four-route inventory.

| Route | Source site stem (first/second suffixes) | Owner bodies |
|---|---|---|
| Remotor/abductor |LFC_pleural_remotor_and_abductor_LFC_Miller29_p1 / p296|Thorax / LFCoxa|
| Adductor |LFC_sternal_adductor_LFC_Miller33_p1 / p296|Thorax / LFCoxa|
| Anterior rotator |LFC_sternal_anterior_rotator_LFC_Miller31_p1 / p296|Thorax / LFCoxa|
| Posterior rotator |LFC_sternal_posterior_rotator_LFC_Miller32_p1 / p296|Thorax / LFCoxa|

XML ownership is distinct from compiled indices. The original source-pose record
established LFCoxa body19; source Thorax/site compiled IDs were not established
by this audit and remain null. Native target Thorax3/LFCoxa13 are already verified
body counterparts, not endpoint assignments. Each target site ID, coordinate,
correspondence authority, attachment transform and length/velocity registration
remains null. No copied source coordinates are used as native attachments.

## Target gap and asset distinctions

The exact target XML defines zero sites and zero tendons. The archived compiled
native model has37runtime sites and zero tendons; none of the eight exact source
site names appears in its site inventory. This distinguishes runtime sensor/site
creation from source muscle-site definitions. No claim of globally absent anatomy
is made from missing names. This model supplies no established target endpoint
correspondence through those definitions.

The active target `LFCoxa` mesh reference is `../mesh/RFCoxa.stl`, scale
`1000 -1000 1000`. A separate installed `LFCoxa.stl` file exists but is not that
active mesh. Neither file was changed or substituted.

| Carrier body | Selected source mesh facets | Active target mesh facets | Ordered numeric vertices identical? |
|---|---:|---:|---|
| Thorax |5629|5629|No|
| LFCoxa |2078|3679|No|

All raw assets retain their original manifest hashes. Binary-STL summaries ignore
header/normals/attribute bytes when hashing ordered vertices. These unequal data
identities do not prove different physical shape or anatomical non-homology:
ordering, frames, representations and tessellation can differ. No alignment,
nearest-surface match, shape threshold or physical scale was fitted or adopted.

The original coxa-yaw sign authority uses the named Femur body's origin as a
displacement landmark. Its exact preregistration is verified; that sign metric
does not establish an anatomical muscle insertion or authorize an attachment.

## Checks actually performed

- Source XML/selected routes/ownership and full original asset manifest verified
  against the exact local source. Target XML, active meshes and unused left mesh
  rechecked against original installed-input locks; extracts rederived from bytes.
- Existing saved orientation evaluator re-verifies all15poses/196measurements.
  This is saved-evidence verification; the native campaign was not rerun.
- Reference/tamper tests cover binary-STL truncation/count/nonfinite failures,
  header-only differences, XML identity ambiguity, unresolved includes, altered
  asset extracts and refusal to infer target coordinates, scale or anatomical
  homology. Real saved reconstruction has native construction/kinematics/forward/
  step, solver and live-audit entry points made fatal.
- Initial50tests passed49.72s (20new audit +16binding +14unit-lineage). Before
  delivery the counterpart-ID field was clarified to avoid implying target
  endpoint ownership. The first development report was retained in local scratch;
  fresh final output reconstructed unchanged findings. No scientific gate or
  source/model observation changed.
- Final batch: **50 tests passed in59.04s** across the audit, binding and
  unit-lineage suites. Windows Git Bash saved replay, staged whitespace and
  LFS-pointer checks passed. No dependencies or validated environment changed.

## Roadmap and bounded next task

Production remains **20/42**, new admissions0. Current milestone: a trustworthy
LF proximal muscle-force interface. Native orientation agreement is preserved;
target attachments, length/velocity, physical unit/converter lineage, anatomical
neuron binding, neural activation and original raw scientific prerequisites remain
open. No force application, neural tuning or new Unity behavior is introduced.

Next predeclare paired source endpoint/native body-frame observations. Resolve
the eight source site IDs and owner-body IDs in the locked compiled source;
reconstruct two-point source lengths and finite derivatives over the entire
existing15-pose schedule against old tendon-length/moment-arm observations.
Record target body/mesh frames at mapped poses without assigning target muscle
sites. This supplies a checked geometric observer and translation/frame evidence,
not anatomical correspondence or permission to transplant paths/apply forces.
The protocol must fix observations/budgets before execution; retain all outcomes.

## Windows Git Bash after merging

```bash
cd ~/Documents/FlyBrainUnity &&
git switch newBrain &&
git pull --no-rebase --no-edit &&
git lfs pull --include="malecns_backend/embodiment/interface_output/integrated_whole_leg_readiness.json,docs/evidence/lf-anatomical-crosswalk-v1/annotations.feather,docs/evidence/lf-pose-force-v1*/run/validation.json,docs/evidence/lf-activation-transient-v1/run/validation.json,docs/evidence/lf-activation-integrator-v1/run/validation.json,docs/evidence/lf-native-isolation-v1*/run/validation.json,docs/evidence/lf-synthetic-coupling-v*/run/validation.json,docs/evidence/lf-target-orientation-v1/run/validation.json" &&
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" &&
"$PY" -m malecns_backend.embodiment.lf_route_attachment \
  --report docs/evidence/lf-route-attachment-v1/run/audit.json
```

Expected: `ROUTE AUDIT VERIFIED`,4source routes/8sites, target attachments
UNRESOLVED, transfer BLOCKED; target XML0sites/0tendons, compiled37sites/0tendons,
20/42 and0new admissions. Review executes no native/physics/CNS calls. Original
raw prerequisites recorded/current remain false at this checkpoint; no hash waiver.
Unity can remain closed. Optional exact original source/assets check:

```bash
"$PY" -m malecns_backend.embodiment.lf_route_attachment \
  --report docs/evidence/lf-route-attachment-v1/run/audit.json \
  --source-model "$HOME/Documents/FlyMimic/flymimic/assets/models/best_combined_cvt3.xml"
```
