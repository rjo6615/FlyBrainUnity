# M8 LF proximal replay assessment

**Final status: `PROVENANCE_FAILURE`**

The required pre-read SHA-256 check failed. The worktree path contains a
134-byte Git LFS pointer (SHA-256
`cdbfc2ed140e276a1293f288c0bccfa1a223bfbc6d40c9df5efb6c1422d7352d`), not
the 345,584,215-byte M8 archive whose required SHA-256 is
`4e39bb83dd4455d56a4d88f717615530602317efaf83a6ed241b13af89dc2a5b`.
An attempted LFS fetch failed because this checkout has no transfer URL.

The assessment therefore stopped before opening scientific data. It did not
validate timestamps or trajectories, compare encoder values, select an
interval, extract a replay, or create the proposed addendum. An addendum is not
appropriate yet because missing interval authorization is not the only blocker.

Full preregistration review found that the future artifact must contain one
unchanged 1000-ms history of six measured tibia coordinates in radians, sampled
at 1 ms in LF, LM, LH, RF, RM, RH order and shared by assay seeds 1, 2, and 3.
The `[0,250)` baseline is an assay analysis window, not authorization to select
a source interval. No outcome-independent source interval is specified.

Tracked code independently establishes physical column indices
`[5, 12, 19, 26, 33, 40]`. It also establishes that M8 neural row `i` samples
physics row `5*(i+1)` at the same 0.5-ms timestamp and records the peak encoded
rate per leg, rather than the physical angle. These source findings cannot
substitute for validation of the unavailable archive bytes.

No simulation, physics step, neural step, prior experiment, motor-interface
change, decoder assignment, or coordinate-sign assignment occurred.

No biological proprioception is claimed: the intended source values are
FlyGym/MuJoCo measured coordinates and the encoder is a modeled transformation.
