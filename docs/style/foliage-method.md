# Foliage method (tested 2026-11-04)

From the tutorial "The RIGHT way in making Stylized Trees & Plants" (private copy and transcript in `research/foliage_video2/`), built on our
own textures and tools. One test tree and bush, in a blank test place.

## Route
1. `python tools/art/make_foliage_textures.py art/kit/foliage`: `leaves_white.png` (2 x 2 atlas of white leaf clusters, values in `CELLS`,
   colour spread under the transparent parts so there's no dark fringe) and `bark_white.png` (seamless tile).
2. `blender --background --python tools/blender/foliage_kit.py -- art/kit/foliage`: `FoliageTest.glb` (TreeTrunk, TreeCrown, BushCrown; 1 unit = 1 stud).
   Settings at the top: `TREE`, `BUSH`, `UP_LEAN`, `TRUNK_UP`. Height and depth pick each card's atlas cell: dark low and inside, light on top.
3. Upload: `python "C:/Users/blast/New folder/tools/roblox/upload_asset.py" <file> --image` for textures, no flag for the glb. Insert the model id.
4. In Studio, each MeshPart gets a `SurfaceAppearance`: ColorMap, Color (the tint), AlphaMode Transparency on leaves. Crowns: no collide/query/touch, CastShadow on with the two lights below.

A new image can take a few seconds to load: until then a crown shows solid squares.

## What the test found
| Try | Result |
|---|---|
| Sphere normals (video's second option) + self-shadow | Good shape, almost black underneath at noon |
| Normals leaning up (`UP_LEAN` 0.72) + self-shadow | Still a heavy dark underside |
| + CastShadow off | Soft and bright, the closest. **Chosen** |
| + the video's two PointLights | Overblown and minty: unneeded once the crown is bright |
| 24 -> 42 cards a clump | Fills the crown, but flat until the atlas's dark cell dropped to 0.42 |

## Trunk (rebuilt after the user's review)
Why the first trunk fell short of the video's: one tube forking at mid-height into a star, blunt straight branches, rings that twisted, and one tinted tile.
Now: `foliage_kit.py` builds 4 leaders fused from the ground up, on long S-curves tapering to points, with branches along them and rings that don't twist.
Each tube has its own area of one atlas. `python tools/art/paint_trunk.py art/kit/foliage` paints `bark_painted.png` per texel from `trunk_tubes.json` (colours at the top:
root-to-tip ramp, brush patches, painted light, crotch shading from real distances to other limbs, ridges, warm and mossy patches). SurfaceAppearance Color stays white on it.
Pass 3 (what the video really does, read from his texture in Photopea at 13:56): his paint is a narrow muted mauve-brown, base #675856, with no navy and no black. His navy limbs are the crown's cast shadow under blue sky light,
and his sunlit base is tan because of a low sun. Levels he applied: in 26, gamma 1.4, 203; out 12, 255. Trunk normals point almost straight up (`TRUNK_UP` 0.88), his "flatten" step.
`paint_trunk.py` now draws real strokes in 3 layers (broad, medium, thin accents; about 4 s) from his sampled palette, with no painted light or shadow. Trunk 1,746 triangles, 3 leaders, thicker.
His two PointLights are for the crown shadow: with CastShadow on, the crown goes dark and the lights bring it back while the ground shadow stays (test: inner 150, 165, 255, brightness 1.5; top 170, 255, 130, brightness 2). They spill onto nearby terrain, and the cost per tree isn't measured.
Test ids: model 127828548033654, painted bark 133256224343230 (`GRADE` in paint_trunk.py matched it to the video). Studio: ClockTime 15.6 in the test place.
Pass 4 (random strokes replaced): `paint_trunk.py` places colour by form, per texel. Each limb's distance from the other limbs gives a pale mass down its exposed middle, dark wedges in the forks and thin red-brown edges;
pale edge lines run beside the grooves and along limbs; olive foot + pink mass above it + olive streak on one limb; detail fades with height (`FADE_FROM`, `FADE_TO`, `TOP_DETAIL`). Mesh: skirt, pinched waist, then the Y (`FootSpacing`, `WaistPinch`, `WaistAt`), slower bends, 1,800 triangles.
Test ids: model 76784265423279, painted bark 135345266224983. `GRADE` (1.25, 1.27, 1.0) measured lit mean 129,109,93 vs the video's 129,106,93.
Pass 5: faceted mesh (own vertices per quad, normals lean to the face, `FACET_CHISEL`, `FACET_TWIST`, `TRUNK_UP` 0.82). `paint_trunk.py` stamps brush marks: crisp head, one hard and one soft side, dry-brush tail fading along bristles, each placed and coloured by form. Dark grows down from forks only where a noise gate allows.
Edge highlights use the rock kit's recipe on the mesh's convex facet edges: soft-sided band, wobble, noise breaks, stronger facing up, `EDGE_STRENGTH` 0.32. Lighting.OutdoorAmbient 110, 118, 145 lifts the shadow side. Branches now start above the fork.
Jagged spikes fixed: tails feather (`BRISTLE`), heads are round (`HEAD_SOFT`), the broad layer is blurred before details (`UNDER_BLUR`), painting at 2x then shrinking (`SUPERSAMPLE`); about 23 s. Then texture back: a medium stroke layer over the blended base, `BRISTLE` 0.5, `UNDER_BLUR` 1.4, `GRAIN` 0.035. Test ids: model 99841946653476, painted bark 78685499746350. Lit mean 131,114,105 vs the video's 129,106,93.
Still rough: darks shallower than his (5th percentile luma 85 vs 61), shadow side goes pale grey, facets subtle, foot a little light.

## Numbers in the test
Tree 3,504 triangles (trunk 1,992, crown 1,512), which is a lot for a kit tree; bush 360. Crown tint 60, 178, 78; bush 50, 168, 84.
Test ids: model 119893784893995, leaves 135970127157400, painted bark 126515033027590.

## Crown shadows (tested 2026-11-04)
Crown CastShadow on (bushes off) + 2 PointLights, Shadows off, parented to invisible parts. Scale by r = the smaller of the crown's X and Z:
- Inner: crown centre minus 0.05 of its height; colour 150, 175, 255; brightness 0.25 (0.7 looked too bright to the user); range r x 0.55 (lights the limbs).
- Top: crown centre plus 0.6 of its height; colour 205, 255, 175; brightness 0.6 (down from 1.7); range r x 0.7 (leaf normals lean up, so the light must sit above them).
Too much top brightness or range washes the crown and bleaches the trunk (3 and r x 1.05 did). Inside the crown they did almost nothing.
Stress test, Studio play mode, the dev PC (GTX 1660S), 60 trees / 120 lights in view, earlier smaller light ranges: 16.7-16.8 ms in every setup, so no visible cost, but the frame rate was capped at 60, which can hide a cost. Not a low-end result.
Terrain grass blades vanished near one camera during this work, with lights on or off and after toggling Decoration. `Terrain:ReadVoxels` + `WriteVoxels` of the same data (a rebuild) brought them back. Moving the light parts did not remove them again; the trigger is unknown, so check in play mode.

## Open
- Performance not measured. Each card is drawn twice (real back faces), and stacked transparency can be costly on low-end devices.
- Bark is a plain tile, not hand-painted. Trunks are visibly plain up close.
- All crowns use one mesh so far, with scale and rotation for variety. A kit needs several shapes.

## Species (2026-11-06, the user's choice of method over a new one)
`blender --background --python tools/blender/foliage_species.py -- art/kit/foliage/species` (Birch, Apple, Elm, two seeds each: `SPECIES` settings on `foliage_kit`'s TREE) -> `tools/art/paint_trunk.py <folder>` per tree -> upload `Tree.glb` and `bark_painted.png` -> `tools/studio/tree_kit.luau` (masters in `ServerStorage.TreeKit`, same setup as `Workspace.Foliage`; leaf tints in its `KIT`). Triangles: Birch about 1,800, Apple about 2,400, Elm 3,400-3,700, all heavy for mass placement; not tested in numbers.
