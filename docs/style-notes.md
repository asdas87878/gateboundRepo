# Style notes (first pass, 2026-11-02)

Target: the AI-made RPG screenshot the user shared (forest road to a ruined stone gate, hooded hero, stone golems).
What makes that look, and how we get it in Roblox cheaply:

| In the reference | How we build it |
|---|---|
| Low-poly faceted shapes, every facet flat | Meshes with flat shading (hard normals), big facets, no smoothing |
| Each facet a slightly different tint (no textures) | Vertex colours per face, jittered a little; Roblox's glb importer keeps them. No texture memory at all |
| Deep blue-green pines in stacked tiers | Pines = 4-6 jittered cone tiers on a short trunk; lighter tint on up-facing facets |
| Blue-grey boulders, some moss on top | Convex-hull boulders merged into big planes; up-facing facets sometimes mossy |
| Grey brick towers, crenellated, red banners with a gold diamond | Course-by-course chipped bricks, wider plinth, merlons; cloth banner with a notched tail |
| Cream dirt road, bright grass with tufts and yellow flowers | Terrain/floor in Roblox; grass tufts and flower clumps as small double-sided meshes |
| Warm sun ahead, soft shadows, blue haze on distant mountains | Roblox `Lighting` (ShadowMap, warm sun) + `Atmosphere` haze; distant mountains as big faceted meshes |

Rules
- Units are studs (1 Blender unit = 1 stud). A player is about 5 studs tall.
- One mesh per prop, one colour attribute `Col`, no materials or textures in the export.
- Keep triangle counts small: trees ~150-300, rocks ~40-80, tufts ~30-60. Low-end PCs and mobile are targets.
- In Roblox: MeshPart `Material = SmoothPlastic`, `Color` white (so the vertex colours show as they are),
  grass/banners `DoubleSided = true`, small props `CastShadow = false`, `CanCollide`/`CanQuery` off on decoration.
