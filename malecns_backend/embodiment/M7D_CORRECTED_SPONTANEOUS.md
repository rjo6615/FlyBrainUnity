# M7D corrected-embodiment spontaneous MaleCNS experiment

M7D is a new, matched, observational experiment. It neither modifies nor
reruns M7 or M7C-B4. The runner reuses the frozen MaleCNS seed, neural cadence,
six tibial proprioceptive interfaces, and eleven admitted M6C/M7 motor
interfaces. It changes only the physical initialization to canonical B4's
exact static FlyGym tripod pose at `(0, 0, 0.6045752232266313)`.

Both conditions start in fresh runtimes. The disabled condition runs the same
brain, encoders, observers, and decoders, then zeros only the eleven admitted
contributions immediately before physical application. The 31 other
actuators retain their time-zero tripod targets. Adhesion is disabled. The
canonical calibration surface remains fixed. There is no gait, stance, swing,
balance, postural, target, reference, reward, RL/AI, optimization, scripted
drive, adhesion scheduling, recovery, or adaptive controller.

The preflight verifies B4's summary, manifest, and raw artifact (including the
required raw SHA-256), current M6C evidence locks, exact interfaces, exact
physical construction, matched initial state, environment versions, fixed
numeric telemetry, output availability, and two fresh runtime initializations.
It performs zero physics and zero neural transitions.

```powershell
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.m7d_corrected_spontaneous --windows-preflight
```

After reviewing that output, the separately authorized science command is:

```powershell
# DO NOT RUN YET
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.m7d_corrected_spontaneous --run-windows
```

The fixed experiment is 500 ms at 0.1 ms physics cadence (5,000 transitions,
5,001 states per condition) and inherited 0.5 ms MaleCNS cadence (1,000 neural
updates). A finite fall does not terminate recording. Outputs are compact,
numeric NPZ plus JSON summary/manifest; a COMPLETE result or raw NPZ is never
overwritten. `walking` and `tripod_gait_classification` remain null.
