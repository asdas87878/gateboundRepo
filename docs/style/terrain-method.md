# Terrain method (tested 2026-11-04)

Study of the "Stylized Environment Lesson" tutorial (the source of our target screenshot; private copy, transcript and frames
in `research/foliage_tutorial/`, never in the game). Tested in a blank Baseplate on my own layout, terrain only, no props.

## The method, in the lesson's order
1. **References:** form reference (dictates shape) vs style reference (dictates genre).
2. **Assets first:** a free stylized Sketchfab pack, sorted into folders. Trees, rocks, plants and fences are not made in the video.
3. **Block out with Parts and wedges**, in modular pieces that get copied. Slopes are doubled ("double slope", like subdividing)
   so they convert softly. Layers: shore, walkable path shelf, steep cliff facade, background hill. Curve everything.
   Clipping doesn't matter. Keep the player's room in mind. Avoid corner wedges and unions: the plugin can't convert them.
4. **Convert with the Part to Terrain plugin:** tops grass, steep faces stone, shallows sand.
5. **"Normalize" by hand:** Sculpt/Smooth/Flatten until nothing is straight or flat. Cliffs get a lip, sand gets waves, then paint fixes
   the edges and the path. Always judge from the player's low angle.
6. **Build blockouts:** grey boxes save the space for the house and bridge.
7. **Rocks define the cliffs** (not the terrain): large rocks, layered, not parallel, flatter stubbier ones where they meet the ground,
   rotated for four variations, sizes grading into the cliff. Terrain over their tops reads as overhanging grass.
8. **Colour:** skybox, atmosphere, then terrain colours, checked with a palette maker.
9. **Dressing:** fences with gaps, trees (rescale or rotate 90+ degrees when neighbours, some on the outside of the map, don't overcrowd),
   leaves used as bushes, small plants where colour is needed.

## His numbers, read off the video
| Setting | Value |
|---|---|
| Atmosphere Color | 114, 255, 220 (blue-green: a mix of water, sky and grass) |
| Atmosphere Decay | 64, 114, 132 |
| Atmosphere Glare / Haze | 10 / 0 |
| Atmosphere Offset | 0.25 |
| Atmosphere Density | not read exactly: 0.496 was a test, he settles lower. We used 0.3 |
| Lighting children | Sky, Bloom, DepthOfField, SunRays (their values were not shown) |
| ClockTime | 12 |
| Grass colour | 55, 190, 168 |
| Ground colour | 140, 130, 104 |
| Sand colour | 255, 243, 228 (mellowed from a brighter one) |
| Rock colour | 170, 171, 175 |
| Water wave size | 0 (waves hid his splash particles) |

Custom terrain materials: a MaterialVariant with a terrain base material, assigned in MaterialService. He paints the path with one.
The ground grass is Roblox's own terrain decoration, recoloured.

## Custom materials and the path edge (tested 2026-11-04)
The lesson's path border has the same soft engine blend as ours (visible as a green glow in enlarged frames). It reads well because
the grass base is flat and matches the blades, the dirt is calm, and blades break the edge. No special blend texture is needed.
- Tiles: `tools/art/make_terrain_tiles.py art/kit/terrain` (seamless, near-white, soft value patches; the terrain colour tints them).
- Make a `MaterialVariant` in MaterialService (BaseMaterial, ColorMap, StudsPerTile 40-48, MaterialPattern Organic), then
  `MaterialService:SetBaseMaterialOverride(base, name)`. Test ids: Grass 72568163985484, Dirt 111329541267911, Sand 109067172199234.
- Test colours: Grass 40, 178, 108; path Mud 160, 112, 78; Sand 245, 222, 130.
- Washed-out water was WaterReflectance 1 mirroring the white sky. Test: reflectance 0.15, transparency 0.25, colour 70, 215, 200.
  Atmosphere Density 0.22, Glare 1, Bloom intensity 0.4, threshold 1.6.

## To fix later (the user's notes, 2026-11-04)
Material placement is broken in places: some walls that should be rock show ground, and the terrain splits off oddly in spots. Not looked into yet.

## What the test showed
- The whole pipeline scripts: Parts to terrain is `Terrain:FillBlock` / `FillWedge` (395 parts in 0.13 s), no plugin needed for us.
- A noise warp plus one soft pass over the voxels replaces the first rough stage of hand normalizing. It does not replace the
  deliberate hand work (cliff lips, sand waves in chosen places, composition).
- His grass colour assumes his texture: on the default texture it goes cyan. Ours: Grass 44, 168, 104; Sand 244, 226, 150; path Mud 122, 66, 48.
- The sky and atmosphere changed the look more than any terrain step.
- The default Rock texture is noisy and high-contrast, which is one reason his rocks cover the cliffs.
- Not tested: performance, custom terrain materials, Bloom/DepthOfField/SunRays values, in-game (only edit-mode captures).

## Sky (2026-11-04)
Current: free Creator Store "Stylized Skybox" (asset 8755940451). Tried and rejected by the user: a sky painted in the lesson's measured cyan (`tools/art/make_painted_sky.py --preset Lesson`, `art/style/sky/Lesson`, not in use).
Its colour matched (top about 36, 195, 240 vs our 2, 46, 157), but the clouds looked flat and the bright sky washed out the scene through ambient light.

## Diagnosis of the scripted terrain (2026-11-04, the user: jagged shores and walkways)
Same land rebuilt on side slices in the test place (x about 860-2600), one step added each time. Numbers are raycast samples of the collision surface along one walkway line and one shore, x -110 to -30. Not checked by eye yet: Studio wasn't drawing.
| Build | Walkway bumpiness | Waterline jumps over 1.5 studs | Top voxels under 20% full |
|---|---|---|---|
| A raw Parts to terrain | 0.032 | 2 | 19% |
| B + noise warp | 0.096 | 2 | 44% |
| C + warp + blur | 0.076 | 3 | 90% |
| D + warp + blur + water step (what the scene used) | 0.076 | 2 | 65% |
| E smooth height field, same voxels | 0.005 | 0 | 15% |
Sand-to-grass edge in the scene: wobble 2.47 studs, biggest jump 15. On E: 1.00, 3.3. 13% of walkway samples in the scene are Rock (warp moved cliff material or shape in).
Causes: the noise warp stood in for the lesson's hand "normalization" (10:00-16:00 of his video, from hours of work); the blur leaves thin slivers on top; materials were painted per 4-stud column on the warped surface. Not the cause: the blockout heights, or the water step (first suspicion, wrong).

Correction, same day: the blockout does hurt the shore. Surface heights across the river at x -55, every 5 studs (water level 8): raw A goes S6, S6, G11; the scene S6, S6, S14; smooth E S6, S9, S11, S13. So in A and the scene the ground jumps past the waterline in one 5-stud step, with little exposed sand. Likely source: the slope builder's fill blocks under each wedge make a wall at the start of the next slope, and they're Grass under sand. The earlier waterline numbers didn't catch this.

Seen by eye, same day: E has a clean beach and waterline; A shows a sawtooth sand-grass edge, seam notches and almost no beach; the scene shows crumpled folds on the banks, creases across the path, and grass and rock blotches on the walkway.
Checking in Studio: terrain shows a coarse version until the camera has been near it a few seconds, and Studio stops drawing when its window is covered. Set the camera, wait about 7 s, then capture; keep Studio visible.

## Current method: height field (rebuilt 2026-11-05)
`tools/studio/build_terrain.luau` (run in edit mode; numbers in `CONFIG` at the top; clears ALL terrain, then re-seats `Workspace.Foliage` on grass). One surface height from distance to the river's edge; materials from the finished surface: slope over 0.85 rock, the path band mud, banks under about 12.5 sand, otherwise grass. Replaces the Parts + warp + blur route.
Result: walkway bumpiness 0.002 (was 0.076), no rock samples on the walkway (13% before), beach and waterline clean by eye. Hand sculpting and rocks still come next.
Still rough: small waterline kinks from the 4-stud voxels, a blade-free band beside the path, stretched streaky rock texture on steep slopes, plain beach, end wall too flat and even.

## Painted terrain tiles (tested 2026-11-05)
From the "KEY in making Roblox games" video's Substance Painter recipe (private copy and transcript in `research/key_video/`): base colour, then colour layers through BnW spot masks (lower balance, raise contrast), Blur Slope, a directional blur, a blur, a sharpen. `tools/art/paint_terrain_tiles.py art/kit/terrain/painted` does that chain in numpy, seamless, about 50 s for both styles (no Painter needed). Its light, AO and curvature layers and hand paint need a model's own UVs, so they apply to rocks, not repeating tiles.
Chosen so far: style `planes` (soft value steps). MaterialVariants in MaterialService, terrain colour multiplies the map:
| Material | Image id | StudsPerTile | Terrain colour |
|---|---|---|---|
| Grass | 70626934798814 | 36 | 7cc25a |
| Mud (path) | 92003948476311 | 22 | 176, 146, 92 |
| Sand | 108417294349064 | 36 | f6e39a |
| Rock | 109569450752968 | 26 | 142, 146, 140 |
Tile size matters as much as the paint: at 40-60 studs per tile the strokes vanished at walking distance. Grass blades take the terrain colour, which took them from cyan to green.
The earlier `make_terrain_tiles.py` had a scale bug (noise size in pixels): its "calm" tiles were faint per-pixel static, so that earlier finding was really "flat colour reads clean". Don't reuse it.
Still rough: slight repeat pattern on large grass areas from above, faceted rock looks scalloped and dark in shadow, blades oversized close up, rock facets come from Roblox's terrain mesh and may shift with distance.

## Shape-built tiles (2026-11-05, replaces the painted tiles above for grass, path and cliff)
The user disliked splotches and over-blended areas: filtered noise has no shapes. `tools/art/paint_shape_tiles.py art/kit/terrain/shapes` (about 13 s) draws actual shapes, seamlessly: overlapping grass clumps with lit blades, dirt from layered dry strokes and pebbles, Worn (dirt + broken grass islands), cliff (two-scale Voronoi planes, cracks, pale upper rims).
| Terrain material | Image id | StudsPerTile | Terrain colour |
|---|---|---|---|
| Grass | 92100943406214 | 30 | 9fd767 |
| Mud (path) | 99828434307675 | 20 | ae9681 |
| Ground (Worn, around the path) | 113865123945015 | 20 | adcf67 |
| Rock | 126964885674751 | 34 | 158, 160, 150 |
| Sand | 108417294349064 (planes tile) | 36 | f6e39a |
Worn band: `WornWidth` in build_terrain.luau; a Ground band outside the path gives the grass-to-dirt transition the engine's blend can't. Worn has no blades because it isn't Grass.
Untested idea: `TerrainDetail` under a MaterialVariant gives different top/side/bottom textures (Roblox docs), so a Grass cliff side could be rock with no material painting.

## Low-key pass (2026-11-05, current; replaces the table above for Grass and Rock)
How the lesson's jagged path edge works, seen in enlarged frames (14:17): it isn't a texture. It's Roblox's terrain grass blades growing up to the dirt at random angles, on a nearly plain ground, over plain dirt. Blades only grow on Grass, so a band of another material beside the path (the Worn tile, removed; `WornWidth` 0) takes the edge away. Painted blades in a tile all point one way and read as decals.
| Terrain material | Image id | StudsPerTile | Terrain colour |
|---|---|---|---|
| Grass (plain, faint dry strokes every way) | 120413043594048 | 40 | 62, 150, 72 |
| Rock (faded) | 97571239280875 | 40 | 122, 128, 126 |
Fading rock: `CLIFF_FADE` 0.42 pulls the tile toward its mean colour, the fine cell lines are gone, and cracks and rims are softer. Lower the terrain colour too, or sun blows faded stone to white. Other levers: StudsPerTile (bigger = calmer), or a separate colour for a tone change. Terrain colour is instant to try; the rest need a re-upload.
Known: in spots a one-voxel bare band remains beside the path.

## From the user's own blockout (2026-11-06, the route now that the user blocks out by hand)
`tools/studio/blockout_to_terrain.luau` (edit mode, numbers in `CONFIG`, first run on `land1manual`, 6 s for 8 blocks). No plugin. It reads the folder's block Parts and wedges at any angle (other shapes are skipped and named in its report), and takes the top of the highest block over each point as one height surface, so overhangs and caves don't convert. Then: edges bend (`Wander`; a height surface can't fold, unlike the old 3D warp), three box blurs round walls into cliffs (`Soft`), slow relief on the flats (`Relief`). Voxels get occupancy from four height samples each, so turned walls have no sawtooth.
- **Paint comes from the finished surface:** steep (`RockSlope`) is Rock, the hollow at a slope's foot is Mud (`FootDirt`), the rest Grass; voxels more than 6 studs down are Rock. The dirt band gives the blades a jagged edge against something, as in the lesson.
- **Scope:** writes only inside the blockout's bounds plus `Margin`, unlike `build_terrain.luau`, which clears all terrain. A rerun rewrites that area, so hand sculpting and painting there is lost.
- **Blocks:** moved to `ServerStorage.Blockouts.<Folder>` after converting. To change the shape, drag the folder back to Workspace, edit, rerun.
- **Land edges:** ground that ends slopes down to the blockout's lowest point, so a thin slab becomes a solid rock skirt, not a plate.
- **Height:** Roblox draws the surface about 2 studs above what the occupancy formula says (8.01 over a 6.05 block top). `SURFACE_LIFT` takes that off: now 5.96, range 4.46-7.66 with relief. `build_terrain.luau` has the same lift, uncorrected.
- **Overall textures** are global: the MaterialVariants in MaterialService replace the base materials everywhere, and `Terrain.MaterialColors` tints them. Nothing per Land yet.

Checked in Studio from player height, close to a cliff foot and from above. Not done: walked in play mode, performance. Rock faces show the terrain mesh's large triangles, which the rock pack is meant to cover.
