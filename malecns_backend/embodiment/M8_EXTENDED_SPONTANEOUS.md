# M8 — extended spontaneous embodiment

M8 extends the validated M7D/B4 matched experiment from 500 ms to 10,000 ms. It does not modify or rerun M7D, M7E, M7F, VIS2, or VIS3. The only scientific-protocol change is duration; recording adds identity-bearing MuJoCo contact flags and distal-tarsus world positions.

## Canonical Windows command (run once after review)

From the repository root in the same scientific environment used for M7D:

```powershell
python -m malecns_backend.embodiment.m8_extended_spontaneous --run-windows
```

A safe, zero-transition review command is:

```powershell
python -m malecns_backend.embodiment.m8_extended_spontaneous --windows-preflight
```

The run creates a new `interface_output/m8_extended_spontaneous` namespace: immutable compressed raw telemetry, manifest, JSON/Markdown post-run analysis, and two backward-compatible M7F replay binaries plus a replay manifest. Expect roughly 20 times M7D's 16.7 MB compressed archive (approximately 335 MB, data-dependent), plus roughly 90 MB of replay binaries. Runtime should be approximately 20 times M7D, with modest additional contact-identity sampling overhead.

Full-resolution physical, motor, and sensory data use their native 0.1 ms and 0.5 ms cadences. Full-brain vectors are not stored. Aggregate CNS activity and mapped motor summaries are recorded at 0.5 ms; the configuration reserves 5 ms for any future large diagnostic summaries without changing dynamics.
