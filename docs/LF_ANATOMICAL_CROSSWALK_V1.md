# LF anatomical crosswalk v1

Reference research, 2026-10-25; baseline origin/newBrain c6495bb (merged #266).
This is not a preregistered physiological experiment. Source records and atlas
figures were inspected before writing this research report. No CNS/physics
transitions, admission, decoder calibration, activity-based selection or tuning.

## New primary evidence

[The official MaleCNS download page](https://male-cns.janelia.org/download/)
identifies the v1.0 annotation release used by the original bodymap preparation
script. Its raw table is preserved unchanged as
`docs/evidence/lf-anatomical-crosswalk-v1/annotations.feather` in Git LFS.

- Original URL: https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome/body-annotations-male-cns-v1.0-minconf-0.5.feather
- SHA256: 2177e246113e4cfbf1e7772ec37c6da1955ff22e8063d0b1f833101f99a9a3b2
- Size: 14483314 bytes; 211577 source rows. This includes records outside the
  repository's selected neural runtime, not an expanded neural model.
- Attribution: MaleCNS consortium, FlyEM/HHMI Janelia, University of Cambridge,
  MRC Laboratory of Molecular Biology and Google Research; dataset CC-BY per the
  official download page. Complete original columns/values for the selected
  neurons are retained in the derived crosswalk, with no annotation edits.

Recheck the previous admission audit using its existing reviewer. Select all
source rows for the five exact annotated LF classes with the original side
fallback (somaSide L/R, otherwise rootSide). Require exhaustive equality with the
13 existing body IDs, unique IDs, exact dense-index correspondence, type, motor
superclass, front-leg subclass, T1 neuromere and expected exit nerve. A changed
source hash or missing/extra/duplicate/misidentified row stops verification.
Do not run the original prep_bodymap script or rewrite its outputs.

The table records 12 non-null `mancBodyid` matches. They are published annotation
matches, not new morphology validations. Preserve the missing match for body
1050335829; neither its `mancGroup` nor a serial-set ID is a substitute body ID.
The four promotor rows retain broad MaleCNS and MANC type labels. These data add
traceable cross-dataset identities, not finer tendon assignments.

## Anatomical atlas inspection

Primary source: Azevedo et al., *Supplementary Methods: Identification of leg
motor neuron targets*, [author-hosted appendix](https://faculty.washington.edu/tuthill/docs/azevedo24_appendix.pdf),
associated with *Connectomic reconstruction of a female Drosophila ventral nerve
cord* (2024), [article](https://pmc.ncbi.nlm.nih.gov/articles/PMC11348827/).
Downloaded full PDF SHA256:
`822c298e50da9fee3ce75f1dabda040574eac9fc854fdf92837856a82c8515f6`;
20587123 bytes, 46 PDF pages. Read page 1 and visually inspected A2/A3/A4 and
their captions on PDF pages 15-19. This resolves the prior web-reader size limit;
no new claim that MaleCNS and FANC are the same specimen.

| FANC atlas group | Figure / PDF page | Exit nerve | Class-level anatomical evidence |
|---|---|---|---|
| MNs 1-4 | A2 / 15-16 | DProN | Combined tergopleural/pleural promotor class; individual targets explicitly uncertain |
| MNs 5-6 | A3 / 17 | VProN | Sternal anterior rotator |
| MN 7 | A3 / 17 | ProAN | Sternal adductor |
| MNs 8-11 | A4 / 18-19 | ProAN | Sternal posterior rotator |
| MNs 12-13 | A4 / 18-19 | ProAN | Pleural remotor/abductor |

Figure A2 states: "we are uncertain about the exact target for each MN."
Thus this source does not resolve even the two-muscle promotor split for its own
specimen; the FlyMimic three-tendon split cannot be assigned from it. Atlas MN
numbers are a separate namespace and are **not** assigned to individual MaleCNS
body IDs by count, order, name or nerve agreement. Four single-class populations
have class-level support, not a validated specimen-to-model tendon crosswalk.
The atlas combines female FANC, peripheral XNH and genetic evidence; that scope
is retained. All derived per-neuron model-tendon assignments remain null.

## Consequence for the next implementation

Stop repeating the same annotation audit to try to split the broad promotor pool.
That needs finer independent anatomy or explicit uncertainty modeling. Keep it
out of any unambiguous tendon-binding claim. The four single-class populations
can instead support separately labeled **modeled class-to-muscle hypotheses**;
using them still requires an engineered interface and validation, not a claim of
fully established individual biological targets.

The next useful engineering step is a separately specified LF muscle-force
reference adapter and isolated implementation validation, beginning with those
four class hypotheses while leaving the broad promotor unassigned. This is a
proposed scope, not permission to bypass current admission prerequisites:

1. Reuse exact identities, existing observer and local covector registration;
   retain existing 20-motor production behavior. Keep force application separate
   from a position-target approximation and do not apply both on the same axis.
2. Treat R=-dL/dq and tau=sum(T_i R_i) as conditional reference mechanics. Require
   explicit force units, activation/passive terms, reference pose/range and a
   justified tension law before any scientific application. No geometric magnitude
   becomes a gain and no model muscle parameters transfer silently between bodies.
3. First validate force projection/isolation with synthetic known tensions in an
   isolated, separately versioned fixture. Such tests validate mechanics/software,
   not biological activation or neural recruitment. Do not tune to obtain activity.
4. Only after numerical/application gates and original raw prerequisites pass,
   preregister a bounded neural-coupling experiment in the current context. Preserve
   null recruitment and all old results; no new channel is admitted by this plan.

The executable crosswalk CLI rechecks full official annotation bytes and the
existing identity audit; atlas interpretation is a documented human reference
review, not an automatic reconstruction of anatomical matching.

## Git Bash after merging

```bash
cd ~/Documents/FlyBrainUnity
git switch newBrain
git pull --no-rebase --no-edit
git lfs pull --include="docs/evidence/lf-anatomical-crosswalk-v1/annotations.feather"
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
"$PY" -m malecns_backend.embodiment.lf_anatomical_crosswalk --report docs/evidence/lf-anatomical-crosswalk-v1/crosswalk.json
code docs/LF_ANATOMICAL_CROSSWALK_V1.md
```

Expected: CROSSWALK VERIFIED, 13 exact neurons, 12 recorded MANC body matches,
4 unresolved promotor neurons, 0 model tendon assignments; current 20/42 and
0 new CNS/physics transitions. No Unity run. Missing LFS bytes or changed source
must error; do not fetch a different release to replace the pinned table.
