# Poly Haven ground-asset inspection

Inspection date: 2026-09-15. The compressed Blender sources and their Unity model-import settings were inspected directly. These downloads are Poly Haven **material preview scenes**, not object packs. Their renderable hierarchy is a flat preview plane plus a dense UV sphere used to demonstrate the same surface material; the remaining source objects are render-preview helpers (camera, lights, and empties). Unity's model importer has `addColliders: 0`, but is currently configured to import source cameras and lights.

| Source | Renderable meshes in the imported hierarchy | Approximate source-space dimensions | Materials | External PBR maps | Classification / decision |
|---|---|---|---|---|---|
| `brown_mud_leaves_01_4k.blend` | 2: `Plane` (4 vertices, 1 polygon) and `Sphere` (1,986 vertices, 2,048 polygons) | Preview plane and roughly spherical material swatch; Blender 4 stores vertex positions as attributes, so exact dimensions are not recoverable from the legacy `MVert` records | 1 surface material | diffuse JPG, OpenGL normal EXR, roughness EXR, displacement PNG; project also has the separately generated metallic/smoothness map | A tileable mud-and-leaf **surface**, not loose leaves or debris. Reject for clutter. It remains the ground material source. |
| `forest_leaves_02_4k.blend` | 2: `Plane` (4 vertices, 1 polygon) and `Sphere` (1,986 vertices, 2,048 polygons) | plane ≈ 3.001 × 3.001 × 0; sphere swatch ≈ 3.010 × 3.010 × 3.001 source units | 1 surface material | diffuse JPG, OpenGL normal EXR, roughness JPG, displacement PNG | A leaf-litter **surface** baked into textures. It contains no individual leaves or clusters. Reject for clutter. |
| `forest_leaves_04_4k.blend` | 2: `Plane` (4 vertices, 1 polygon) and `Sphere` (1,986 vertices, 2,048 polygons) | plane ≈ 1.500 × 1.500 × 0; sphere swatch ≈ 1.505 × 1.505 × 1.500 source units | 1 surface material | diffuse JPG, OpenGL normal EXR, roughness JPG, displacement PNG | A leaf-litter **surface** baked into textures. It contains no individual leaves or clusters. Reject for clutter. |
| `rock_face_04_4k.blend` | Material-preview scene (plane/sphere preview geometry; no discrete rock objects) | Surface preview scale is not meaningful as a real rock size | 1 surface material | diffuse JPG, OpenGL normal EXR, roughness EXR, displacement PNG | A continuous cliff/rock-face **surface**. It is neither an individual stone nor plausible millimetre-scale geology. Reject for clutter rather than shrinking a cliff texture into a pebble. |
| `rocky_trail_4k.blend` | 2: `Plane` (4 vertices, 1 polygon) and `Sphere` (1,986 vertices, 2,048 polygons) | plane preview ≈ 2 × 2 and sphere swatch ≈ 2.007 × 1.999 × 2.006 source units | 1 surface material | diffuse JPG, OpenGL normal EXR, roughness EXR, displacement PNG | A rocky-ground/trail **surface**; the visible stones are baked surface detail, not separable meshes. Reject for clutter. |

## Prefab extraction result

No presentation prefab was extracted. The `Rocks`, `Leaves`, and `Organic` folders are intentionally empty: making a prefab from a preview sphere or plane would not extract the pictured leaf/stone, and shrinking the rock-face surface would be visually misleading. The runtime clutter library therefore ships with valid empty prefab lists and the simulation operates normally with no decorative instances.

## Recommended object downloads

Download actual 3D model assets rather than materials/textures:

- isolated dry leaves or torn leaf fragments with silhouette geometry and front/back material;
- individual gravel stones / small rounded pebbles (preferably a varied set);
- short isolated twigs, bark chips, and wood splinters;
- small moss clumps, lichen tufts, seed husks, or other isolated organic debris.

Prefer clean-pivot assets with one object per variant, but pivot and native scale are not requirements: the clutter system normalizes size from combined renderer bounds and grounds the lowest rendered point automatically.
