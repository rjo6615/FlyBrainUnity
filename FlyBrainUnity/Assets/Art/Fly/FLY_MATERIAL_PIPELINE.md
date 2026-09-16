# Fly material pipeline

- **Rendered source:** `Assets/Art/Fly/Fly.fbx` (referenced directly by `Resources/FlyBrainVisualLibrary`; no generated fly prefab).
- **FBX source material names:** `TheFly` and `Wings`.
- **Original texture set:** `TheFly_TheFly_BaseColor.png` (RGBA, including wing opacity), `TheFly_TheFly_Normal.png`, and `TheFly_TheFly_OcclusionRoughnessMetallic.png` (R=occlusion, G=roughness, B=metallic).
- **Finding:** case **A/E**. The complete textures were already in Unity, but the FBX importer had created untextured default materials and no external material remaps. The textures therefore survived asset copying, while their assignments/conversion were lost.
- **Runtime:** the real FBX model is instantiated without any material assignment. `new Material` is used only by the fallback/debug primitives.
- **Repair:** `Tools > FlyBrain > Build Fly Materials` creates persistent URP/Lit `TheFly URP` and `Wings URP` assets in `GeneratedMaterials`, repacks ORM blue to Unity metallic red and inverted roughness to smoothness alpha, and remaps the two FBX source slots without altering hierarchy, meshes, UVs, normals, or tangents. The build runs once automatically when those generated assets are absent.
- **Anatomy:** the source uses one UV atlas for the body (including red compound eyes, head, thorax, abdomen, and legs) and a separate `Wings` source slot. Anatomical colors/details therefore remain the authored atlas mapping rather than guessed renderer-name colors.
- **Wings:** alpha-blended, Z-write off, double-sided URP/Lit; BaseColor alpha supplies membrane transparency and the atlas preserves its vein detail.
