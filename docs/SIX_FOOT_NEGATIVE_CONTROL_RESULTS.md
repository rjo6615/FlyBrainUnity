# Six-foot isolated calibration results — 2026-10-24

Work started from fetched origin/newBrain at 93e7404 (PR #256). Original checkout
edits, raw v1 uploads, source locks, and the v1 rejection remain intact. The raw
v1 upload SHA-256 matches docs/evidence/contact-calibration-checkpoint.json.

The protocol was committed before physics (f925f34). That first run completed
all twelve arms and rejected all feet due to identity-table and float precision
integrity failures. The documented v2.1 implementation correction was committed
before its verification repeat (ee091cb). It fixes the FlyGym namespace and uses
the legacy observer's float64 convention without changing scientific parameters,
conditions, acceptance, or window. No placement tuning or selective retries ran.

Both full JSON reports are preserved losslessly in docs/evidence/*.json.gz;
six-foot-contact-v2-checkpoint.json records raw/compressed hashes, implementation
commits, environment versions, and per-foot outcomes. Regression tests decompress
both, verify hashes, and recompute every saved acceptance check.

The v2.1 physics run accepted all six feet in the isolated assay. Each arm has
501 samples (6012 total); all 3006 negative samples have zero contact and zero
force, with positive conservative geometric clearance. All masks remain as
prescribed, no explicit pairs or unexpected collisions occur, and positive
exact-contact samples exceed the unchanged 1e-12 threshold.

| Foot | Negative contact samples | Positive exact-contact samples |
|---|---:|---:|
| LF | 0 | 51 |
| LM | 0 | 97 |
| LH | 0 | 87 |
| RF | 0 | 52 |
| RM | 0 | 97 |
| RH | 0 | 88 |

This is a collision-isolation calibration, not ordinary supported live-v3 physics.
Removing explicit floor/self pairs also switches the selected positive pair to
MuJoCo's dynamic geom-pair contact settings rather than FlyGym's explicit floor
pair settings. No solver parameters were tuned; the contexts are not equivalent.
The negative excludes all collisions by topology and parks the surface remotely;
sampled geometry supports separation, while masks supply continuous exclusion.
It is a clean engineering zero-input baseline, not a near-contact sensitivity or
multi-contact specificity assay. No CNS ran and no tactile input was enabled.

Before any delivery experiment, specify how the calibration context transfers to
the intended live body, including other collisions and support. A matched
tactile-enabled/withheld experiment remains separate and requires independent
candidate sampling and verified readout/input boundaries. These results do not
establish biological transduction, independent balance, or gait.

Validation: 87 tests plus 9 subtests passed across v2, v1, locked targeted
calibration, contact readiness, CLI, headless, motor diagnostics and pose transport.
The initial raw-byte lock failure was Windows CRLF checkout conversion; restoring
canonical LF bytes only in the isolated checkout resolved it without tracked
source changes or refreshed expected hashes. Both bounded physics runs actually
executed in existing FlyGym 1.2.1 / MuJoCo 3.2.7 / NumPy 2.0.2. Unit fixtures are
synthetic; the compressed records are actual physics. Unity/CNS tests were not run.

Manual Git Bash commands and expected exit codes are in
SIX_FOOT_NEGATIVE_CONTROL_V2.md and SIX_FOOT_NEGATIVE_CONTROL_V2_1.md. To run the
broader executed regression set, append these files to the documented pytest command:

```bash
tests/test_live_contact_readiness.py tests/test_live_cli.py tests/test_live_headless.py tests/test_live_motor_diagnostics.py tests/test_live_pose_transport.py
```

On Windows with core.autocrlf=true, create the fresh PR checkout with
`git -c core.autocrlf=false worktree add ...` to retain canonical LF bytes required
by historical raw-byte locks. Do not change lock hashes to match CRLF conversion.
