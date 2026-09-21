# M9A — physics-only perturbation calibration

M9A is a new, preregistered experiment namespace. It reuses the exact M7D/M8
corrected tripod initialization and inherited fixed 42-actuator position
semantics. It adds no biological interface and runs no MaleCNS transition.

The sweep applies a direct MuJoCo `xfrc_applied` lateral force to the uniquely
resolved compiled body named `Thorax`. Every external force and torque entry is
zeroed before each transition; only that body receives the candidate force,
from 500 ms inclusive through 520 ms exclusive. The force is zero before and
after that half-open interval. The four frozen native-unit magnitudes are
0.0001, 0.0002, 0.0004, and 0.0008. Each fresh candidate is observed for
1500 ms. The runner fails closed if authoritative thorax, ground, or distal
tarsus identity cannot be established.

Selection criteria are declared by `protocol()` before execution. Selection is
the lowest candidate which is finite, changes authoritative contact, causes at
least 0.05 mm root displacement or 5 degrees of tilt, stays within the 1.5 mm
and 60 degree launch/instability ceilings, causes no fall or rollover by 600
ms, and reduces displacement or tilt deviation by at least 25% in the frozen
late window. No neural quantity is available to selection.

Run the zero-transition identity/configuration gate, then the one permitted
calibration sweep, in the pinned Windows environment:

```powershell
python -m malecns_backend.embodiment.m9a_perturbation_calibration --windows-preflight
python -m malecns_backend.embodiment.m9a_perturbation_calibration --run-windows
```

The run creates an exclusive JSON report, JSON manifest, and one hashed numeric
NPZ per candidate under `interface_output/m9a_perturbation_calibration`. It
refuses to overwrite evidence. Until those outputs exist and report
`COMPLETE`, no perturbation is selected and M9B is not permitted.

M9A establishes only a calibrated external physical perturbation. It cannot
demonstrate balance, postural control, reflexes, biological function, or neural
recovery.
