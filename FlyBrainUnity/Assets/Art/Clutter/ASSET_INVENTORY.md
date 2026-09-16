# Presentation clutter asset inventory

Inspection date: 2026-09-16.

The category folders currently contain these preferred object-model sources:

| Category | Preferred source model | Intended generated prefab | Assignment | Matching lower-priority source |
|---|---|---|---|---|
| Rocks | `Rocks/rock_moss_set_02_4k.fbx` | `rock_moss_set_02_4k.prefab` | Rocks | `Rocks/rock_moss_set_02_4k.blend` (ignored) |
| Twigs | `Twigs/dry_branches_medium_01_4k.fbx` | `dry_branches_medium_01_4k.prefab` | Twigs | `Twigs/dry_branches_medium_01_4k.blend` (ignored) |
| Organic | `Organic/celandine_01_4k.fbx` | `celandine_01_4k.prefab` | Organic | none |
| Organic | `Organic/grass_medium_02_4k.fbx` | `grass_medium_02_4k.prefab` | Organic | none |
| Organic | `Organic/periwinkle_plant_4k.fbx` | `periwinkle_plant_4k.prefab` | Large Vegetation | `Organic/periwinkle_plant_4k.blend` (ignored) |
| Organic | `Organic/shrub_01_4k.blend` | `shrub_01_4k.prefab` | Large Vegetation | no FBX is present; the Blender source remains a fallback |

No object model is currently present in `Leaves`. Despite the expected source list, there is currently no `shrub_01_4k.fbx` in the repository. Exporting that source to the same folder will automatically make FBX the preferred source on the next build.

`Tools > FlyBrain > Build Clutter Library` groups sources by category and filename before importing them. It selects FBX first, so a matching `.blend` is never loaded or reported as an error. Other formats remain ordered fallbacks. The command performs the authoritative hierarchy inspection through Unity's model importer, retains valid `MeshRenderer` and `SkinnedMeshRenderer` geometry (including skin bones), disables imported cameras, lights, animation, and colliders, discards named preview planes/spheres and non-rendering helper branches, and rejects a source if no renderable mesh remains.

The builder creates presentation-only prefabs under `GeneratedPrefabs`, creates asset-specific URP/Lit materials from available base-color, normal, roughness, ambient-occlusion, and opacity textures, and assigns every valid prefab to the serialized `FlyBrainVisualLibrary`. The Console reports FBX discovery/acceptance totals, every ignored duplicate, renderer/mesh/vertex evidence for each accepted source, every rejection with its exact reason, and the number of prefab references reloaded from the saved library asset.
