# M9D — canonical M9B external-perturbation Unity replay

M9D is a visualization-only adapter over the four frozen M9B conditions. It reads recorded physical states and writes one deterministic replay binary per condition. It imports no experiment runner and executes **zero physics transitions and zero neural transitions**. M9B and M9C are never rerun.

The Unity implementation reuses the validated M7F/VIS2/VIS3 42-joint scientific hierarchy, quaternion reconstruction, all 69 authoritative anatomy meshes per fly, and the coordinate transform `FlyGym [x,y,z] -> Unity [x,z,y]` at presentation scale `0.1`. Scientific coordinates remain unmodified in each binary. Side-by-side separation is applied only through each complete rig's `PresentationOffset`.

The force arrow is a transform-only annotation directed along Unity `+Z` (source `+Y`). It has no `Rigidbody`, collider, or force application code; its length is illustrative. M9C timeline labels are informational and cannot affect playback.

## Reviewed Windows export

Materialize the already-frozen Git LFS M9B NPZ, check that no M9D output namespace exists, check out the reviewed exporter commit, then run from the repository root:

```powershell
python -m malecns_backend.embodiment.m9d_replay_export --export-windows
```

Copy the resulting manifest and four binaries from `malecns_backend/embodiment/interface_output/m9d_unity_replay` to `FlyBrainUnity/Assets/StreamingAssets/M9DReplay` only after review. The exporter fails closed on source identities, array shape/dtype/count, nonfinite values, clocks, replay round-trip equality, and any existing output directory.
