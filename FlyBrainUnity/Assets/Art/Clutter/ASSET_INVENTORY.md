# Presentation clutter asset inventory

Inspection date: 2026-09-16.

The category folders currently contain these object-model sources:

| Category | Source model | Intended generated prefab | Assignment |
|---|---|---|---|
| Rocks | `Rocks/rock_moss_set_02_4k.blend` | `rock_moss_set_02_4k.prefab` | Rocks |
| Twigs | `Twigs/dry_branches_medium_01_4k.blend` | `dry_branches_medium_01_4k.prefab` | Twigs |
| Organic | `Organic/periwinkle_plant_4k.blend` | `periwinkle_plant_4k.prefab` | Large Vegetation |
| Organic | `Organic/shrub_01_4k.blend` | `shrub_01_4k.prefab` | Large Vegetation |

No object model is currently present in `Leaves`; the builder reports that category as empty rather than substituting preview geometry.

`Tools > FlyBrain > Build Clutter Library` performs the authoritative hierarchy inspection through Unity's model importer. It disables imported cameras, lights, animation, and colliders; discards named preview planes/spheres and non-rendering helper branches; rejects a source if no renderable mesh remains; creates renderer-only prefabs under `GeneratedPrefabs`; creates asset-specific URP/Lit materials; and assigns every valid prefab to `FlyBrainVisualLibrary`. The command logs every rejection with its source path and reason, so a changed upstream `.blend` hierarchy never fails silently.

The builder is intentionally discovery-based. Additional `.blend`, `.fbx`, `.obj`, `.dae`, or `.3ds` models added below one of the four category folders are included the next time the command runs without a code change.
