# Experiment 3 — Live Fly v1 motor-output observability

## Status

**IMPLEMENTED, VALIDATION-ONLY, NOT AUTHORIZED, NOT RUN.** The implementation
adds no runtime hook and performs no scientific transitions. A later,
prospective change must supply both a reviewed passive observation hook and a
cryptographically frozen authorization verifier before execution can exist.

The requested frozen prior object
`ea81974f59ce9a67a382c20d605b385765f10b33` was not present in this shallow
checkout during implementation. Its ancestry was therefore **not verified**.
No file from that prior experiment was changed.

## Fixed assay

The assay compares the existing Live Fly v1 enabled condition with its existing
matched control, which zeros only the final contributions of the exact 11
admitted channels. It admits no new motor population and freezes the seed,
initialization, 0.5-ms neural cadence, 0.1-ms physics cadence, sensory pathway,
decoder equations/constants/signs, safety bounds, joint limits, slew limits,
and FlyGym/MuJoCo contract.

The ordered channel inventory and complete neural/physics record contracts are
stored in `interface_output/live_v1_motor_output_experiment/implementation_design.json`.
Each future condition must start from a separate equivalent fresh state.

## Safety boundary

* Import and ordinary invocation do nothing.
* `--help` only renders CLI help.
* `--validate` reads and verifies the static design and reports zero transitions.
* `--execute` always raises `PermissionError` before importing a runtime.
* Dropping a file at the proposed authorization path cannot bypass the gate.
* Tests use pure records and injected counters only; they never construct
  MaleCNS, FlyGym, or MuJoCo.

## Future report

For each channel the report schema reserves the requested activity, decoder,
clamp/slew, lag, and physical-divergence summaries. It also reserves passive
motion reporting for the other 31 joints. Only the six requested categorical
labels are permitted. No natural-behavior, intent, sufficiency, causal,
decoder-correctness, or biological-functional inference is permitted.

## Readiness

Run:

```bash
python -m malecns_backend.embodiment.live_v1_motor_output_experiment --validate
```

Expected readiness is `NOT_READY_UNAUTHORIZED`, with zero neural and physics
transitions. This is the exact safe status until a separate authorization and
passive observation-hook review occurs.
