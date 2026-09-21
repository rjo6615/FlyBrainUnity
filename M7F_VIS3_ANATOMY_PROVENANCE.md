# M7F-VIS3 anatomical presentation provenance

## Scientific boundary

VIS3 does not change M7D/M7E, replay binaries, joint order, the authoritative rig or native reference JSON, the MuJoCo-to-Unity mapping, scale, or quaternion conversion. Presentation is a renderer-only child of validated scientific transforms and never drives those transforms.

## Authoritative source and reproducible extraction

The sole accepted source is FlyGym **1.2.1** `data/mjcf/neuromechfly_seqik_kinorder_ypr.xml`, SHA-256 `413b3a1dcb7537d08122e16f256f27ec0d8bb9f52c58670345b6c24c9e72e05a`, from the installation recorded in `m7f_mujoco_crosscheck.json`. Run:

```powershell
py tools/import_m7f_vis3_anatomy.py --flygym-root fly-brain-interactive\.venv\Lib\site-packages\flygym
```

The importer rejects any other MJCF hash. It walks every body/geom, resolves every referenced asset mesh, records mesh name, STL filename, owning MJCF body, mesh scale, geom position, geom quaternion, intended scientific parent, and collision/visual role in `Assets/StreamingAssets/M7FAnatomy/m7f_vis3_anatomy.json`. It copies no unrelated package content. The generated inventory is therefore the reviewable authority rather than a hand-maintained or guessed list.

## Coordinate and topology audit

STL vertices are in the model's MuJoCo right-handed, Z-up source coordinates. Import bakes `B(x,y,z)=(x,z,y)` and the frozen presentation scale `0.1` directly into OBJ vertices, after component-wise MJCF mesh scale. Since `det(B)=-1`, each triangle is explicitly emitted `(v0,v2,v1)`. This restores outward winding and generated Unity normals without a negative Transform scale. Geom positions and quaternions remain in the manifest so the Unity attachment layer can apply the existing position and quaternion conversion functions; that conversion must not be replaced or visually fitted.

## License and distribution

FlyGym/NMF model assets are governed by the upstream FlyGym distribution and repository license. Keep upstream copyright/license notices with any generated mesh delivery. The extraction command selects only meshes referenced by the authoritative MJCF. No package code or unrelated data is copied.

## Current checkout status

The authoritative FlyGym installation is not present in this Linux checkout and network package access is unavailable. Consequently no substitute, inferred, or decorative geometry has been committed. Run the extraction on the recorded Windows environment before enabling anatomical presentation or claiming VIS3 anatomical validation. The existing VIS2 scientific numerical gate remains the acceptance gate and must be rerun unchanged.
