# Presentation clutter FBX inventory

Inspection date: 2026-09-16. FBX is the only authoritative presentation-model format consumed by the builder.

| FBX source | Source folder | Resolved runtime category | Generated prefab | Repository preflight |
|---|---|---|---|---|
| `Assets/Art/Clutter/Organic/celandine_01_4k.fbx` | Organic | Large Vegetation | `Assets/Art/Clutter/GeneratedPrefabs/celandine_01_4k.prefab` | FBX and diffuse/alpha/normal/roughness maps present |
| `Assets/Art/Clutter/Organic/grass_medium_02_4k.fbx` | Organic | Large Vegetation | `Assets/Art/Clutter/GeneratedPrefabs/grass_medium_02_4k.prefab` | FBX and diffuse/alpha/normal/roughness maps present |
| `Assets/Art/Clutter/Organic/periwinkle_plant_4k.fbx` | Organic | Large Vegetation | `Assets/Art/Clutter/GeneratedPrefabs/periwinkle_plant_4k.prefab` | FBX and diffuse/opacity/normal/roughness maps present |
| `Assets/Art/Clutter/Rocks/rock_moss_set_02_4k.fbx` | Rocks | Rocks | `Assets/Art/Clutter/GeneratedPrefabs/rock_moss_set_02_4k.prefab` | FBX and diffuse/normal/roughness maps present |
| `Assets/Art/Clutter/Twigs/dry_branches_medium_01_4k.fbx` | Twigs | Twigs | `Assets/Art/Clutter/GeneratedPrefabs/dry_branches_medium_01_4k.prefab` | FBX and diffuse/normal/roughness maps present |

There is no FBX source in `Leaves`. There is also **no `shrub_01_4k.fbx` in this repository**: only the obsolete `.blend` and shrub textures are present. The FBX-only builder therefore deliberately does not discover or serialize shrub. Exporting `shrub_01_4k.fbx` into `Organic` will classify it as Large Vegetation on the next build without moving it or creating a Vegetation source folder.

## Unity import report

Run **Tools > FlyBrain > Build Clutter Library** in Unity. For every discovered FBX, the Console now emits source folder, resolved runtime category, generated prefab path, renderer validity, native combined renderer bounds, URP/Lit material-conversion status, and accepted/rejected status with an exact reason. Those native bounds and generated prefab references are Unity-import results and cannot be truthfully precomputed from the source files without Unity's model importer.

The builder disables imported cameras, lights, animation, and colliders; strips every component except transforms, renderers, and mesh filters; preserves legitimate planar foliage; and only removes preview geometry identified by preview-specific names. Vegetation materials use URP/Lit, alpha clipping and double-sided rendering when foliage/opacity is detected.
