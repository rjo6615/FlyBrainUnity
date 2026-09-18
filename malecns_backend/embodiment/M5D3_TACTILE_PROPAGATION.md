# M5D-3 — verified physical tactile → MaleCNS causal propagation

## Checked-in status

**NOT_RUN.** The checked-in JSON is a protocol artifact, not a scientific
result. This environment has not run the validated Windows FlyGym/MuJoCo
stack. No causal classification or timing result is claimed.

Run the fixed 100 ms experiment on the validated Windows environment:

```powershell
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.tactile_propagation_audit --live --duration-ms 100 --json malecns_backend\embodiment\interface_output\tactile_propagation.json
```

## Locked input and modeled transduction

The physical source is LM Tarsus5 (FlyGym `contact_forces` row 11). Contact
truth requires the exact unordered MuJoCo pair between `1/LMTarsus5` and
`m5d2c_calibration_surface`, placed with the validated 0.0001 model-unit
penetration. Force alone cannot establish contact truth. The accepted
`magnitude > 1e-12` comparison is an engineering zero/nonzero threshold for
this modeled interface, not a biological tactile threshold.

The encoder remains an onset-only, linearly decaying 120 Hz maximum modeled
rate over 20 ms. Sustained contact does not retrigger; release rearms. These
are modeled engineering parameters, not measured biological responses.

## Biological population and delivery

The intervention uses all 378 exact body IDs and dense indices in the
annotation-backed `tactile T2 left` population. It does not subsample. Every
candidate is passed only through `MaleCNSBrain.set_external_drive`; the code
does not write voltage, conductance, threshold, weight, connectivity, or spike
counter arrays.

Two fresh conditions use the same seed, configuration, reset, surface
placement, physical and neural timesteps, duration, encoder, and RNG
organization. Both encoders generate candidates and consume RNG. In
`TACTILE_DISABLED`, those candidates are withheld at the existing external
drive boundary. Candidate sequences and per-sample SHA-256 RNG-state
checkpoints must match.

## Isolation and interpretation

No motor activity is decoded or applied. Joints are held identically. Mapped
motor populations are passive observations only. Physical matching compares
sample schedule, fly reset qpos, LM Tarsus5 force magnitude, exact-pair contact
state, and contact timing with exact (`0.0`) tolerance. A mismatch produces
`PHYSICAL_MATCH_FAILED` rather than a causal claim.

Downstream metrics remove all 378 directly driven tactile indices. The report
separates state, synaptic-input, spike-timing, and spike-count divergence.
A multi-source directed CSR search supplies anatomical path length for early
differing cells; reachability is anatomical context and is never labeled
dynamic causality or functional role.

P6 is the minimum positive propagation result; P7 additionally identifies a
mapped-motor difference but remains observational. P4 and P5 are preserved
without rate, duration, threshold, weight, or drive tuning.
