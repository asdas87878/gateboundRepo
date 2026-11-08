# Rock kit (v3, 2026-11-05)

The rock pack (`docs/style/rock-pack.md`) is the newer set for building by hand. This kit is what the river scene's rocks use.

32 pieces, 6,951 triangles in total, five 1024 colour sheets (Roblox cuts every texture to 1024, checked with a loaded image).
Shape (v3, from the reference's rocks): `rock_bmesh` is now a wide cobble, not a chamfered box: an irregular 5-7 sided footprint (`FOOT_SQUARE`), a shoulder partway up (`SHOULDER`), and a flat top plane that tilts (`TILT`, the wedge), narrower than the foot (`INSET`). `CHUNK` lowers and widens every piece, `LUMP_FUSE` overlaps lumps so a piece reads as one rock, `EDGE_ANGLE` 32 limits bevels and highlights, `SIDE_EDGE` quiets upright highlights.
Earlier versions: `art/kit/rocks/v1`, `v2`, `ServerStorage.RockKit_v1`, `RockKit_v2`, `Rocks_v1`. The displace-and-decimate kit (below) stays available for other rock types; the user rejected it for the main rocks.

| Role | Pieces |
|---|---|
| Detail | Chip, ChipFlat, ChipTall, Stone |
| Boulders | BoulderSmall, BoulderRound, BoulderTall, Boulder, BoulderWide |
| Foot (where a wall meets the ground) | FootStub, FootWide, FootWedge |
| Slabs (shore, steps) | SlabSmall, Slab, SlabLong, SlabStack, SlabBroken, CapSlab |
| Blocks (stack into walls) | BlockSmall, Block, BlockTall, BlockLean, BlockChunk |
| Walls (fill a cliff face) | WallMid, WallWide, WallLong, WallHigh, WallStep, CliffWide, CliffTall |
| Shapes | Corner, Spire |

## Route
```
blender --background --python tools/blender/rock_kit.py -- build
python tools/art/paint_rock_kit.py
blender --background --python tools/blender/rock_kit.py -- render
blender --background --python tools/blender/rock_kit.py -- export
```
Shapes are in `SPECS` and `SHAPE` in rock_kit.py; paint colours are at the top of paint_rock_kit.py. Upload the sheets (`--image`) and `RockKit.glb`. Rebuilding changes the UV layout, so a texture only fits the build it was painted on.
UVs: `layout_uvs` in rock_kit.py (flat charts, shelf-packed at even density, about 60% of each sheet; Blender's packer shrank everything to under 1% with many islands). Sheets `ATLASES`: A big walls and B, C at about 11 texels a stud, D 17, E 23.

In the test place: masters in `ServerStorage.RockKit` (model 104261961954802, moss sheets, SurfaceAppearance Color 222, 222, 216), a palette to copy from at `Workspace.RockPalette` (baseplate, z about -300).

## Colour pass (the frog video's recipe)
No Painter needed, and the earlier paint stays underneath: `paint_rock_kit.py` adds hue layers over the value bands, then the cracks and edge highlights go on top. `COLOUR` scales them; 0 gives the grey version. Grey backup: `RockKit_Color_grey.png`.
| Layer | From the video | Here |
|---|---|---|
| Darks go blue | Darker shade of the base | `SHADE_COOL` on the low value bands |
| Stroke patches | BnW spots + Blur Slope | `strokes()`: warped noise on the 3D surface, teal, ochre, slate |
| Side colour | Two side light generators | Facing: `SIDE_COOL`, `SIDE_WARM` |
| Crevices | AO generator | Existing lump crevices, `CREVICE_DEEP` |
| Highlights | Curvature | The existing edge highlights, unchanged |
| Moss, optional | Light generator from above | `RockKit_<sheet>_Moss.png`: upward faces, jagged edge |
| Sheet | Moss | Plain |
|---|---|---|
| A | 117228874069468 | 79307655708685 |
| B | 74394005294023 | 116912694367145 |
| C | 86888578181958 | 87096234529879 |
| D | 92582687991238 | 72040850424047 |
| E | 81394955860390 | 120751012133239 |
Moss is matched to the terrain grass as lit in Studio (`MOSS` 349f4c, `MOSS_LIT`, darker `MOSS_DARK` at its edge). Walls use moss; shore and water rocks use plain, because moss on wet flat rocks read as lily pads.

## Placing
`tools/studio/place_rocks.luau` (numbers in `CONFIG`, change `Seed` for a new arrangement). **It deletes and rebuilds `Workspace.Rocks`, so hand-placed rocks belong in another folder.** The user's first hand edits were lost this way. The lesson's rules it follows: large wide rocks on the face, no piece repeated next to itself, an upper tier set back, flatter foot rocks off parallel with gaps, small stones in loose groups.
A rock on a steep slope must sit on the lowest ground under its footprint, or it hangs in the air.

## Step 2 zones
`tools/studio/place_rock_zones.luau` builds `Rocks_NearMore` (61), `Rocks_Far` (126), `Rocks_End` (48), `Rocks_Shore` (99), `Rocks_Water` (28); with `Rocks` (64). Shore and Water were redone later, see below: 343 in all. Each zone rebuilds only its own folder; `Run` picks zones. It never touches `Workspace.Rocks`.

## Tested
Play mode: walked x -150 to -6 along the path with no stuck moments or falls. Frame rate NOT measured: frames stayed at 66.7 ms with the rocks removed too and GPU time read 0, so Studio wasn't drawing. Repeat with Studio visible.

## Not done
- Performance on any device. Memory read 1459 MB in that session, which includes Studio.
- Grass overhang on rock tops: moss now gives most of the effect; voxel terrain at 4 studs would be lumpy, so left out.
- Shaded sides stay navy. The lower v3 rocks show more faceted terrain above the wall (the upper tier could rise or grow).
- A hand paint-over.

## Natural rocks (test, 2026-11-05)
From the "Low Poly Rocks" tutorial (private copy in `research/rock_video/`): bevelled cube, subdivide, Displace with Voronoi distance-squared, Decimate in steps. `tools/blender/rock_natural.py -- build|render|export`, then `paint_rock_kit.py --kit rocks_natural`. Outputs `art/kit/rocks_natural`. 12 pieces, 5,522 triangles, 3 sheets.
Added beyond the video: wide foot, `BOX` 5.5 (lower = potato), `TARGET_SHARE` and `FLAT_ANGLE` 16 for few big planes, `HIGHLIGHT_ANGLE` 40 (at 24 the highlights formed a web), same paint.
Verdict: not for the main rocks, maybe for other rock types. Masters remain in `ServerStorage.RockNatural` (model 107691944122553; moss sheets A 77820793522403, B 96984812370858, C 89840844943015; plain C 79561465678796); the test wall was removed.

## Shore and water (2026-11-05)
`place_rock_zones.luau` now places small stones at chosen spots (`ShoreSpots`, `Stepping`, `WaterSpots`): 12 groups of 1, 3 or 5 on the bends, 5 stepping stones at x -26, 3 lone stones. 44 rocks (was 127), widest 6.6 studs, plain sheets, no collision under 2 studs tall. A kit swap with fixed bases sinks stones with a lower new shape: water stones' tops must be reset to about 0.55 above the water.

## Rejected placement tries (2026-11-05)
Kit is v2 (`RockKit`, moss/plain ids: A 137931462822661/128940563516709, B 88463318686619/111834703646301, C 101459269225189/101267229971765, D 78314945448041/130648739309181, E 123578232466712/84250033846591). The sheet table above lists v3 ids, not in use. Path-side wall restored from `ServerStorage.Rocks_v1`; NearMore, Far, End regenerated from their seed.
Tried and rejected by the user: v3 tilted cobble shapes (`art/kit/rocks/v3`, `RockKit_v3`); automatic exposed-terrain fill; full terrace walls (`tools/studio/build_rock_walls.luau`, kept but not in use: covered the terrain but overdone). The user prefers the conservative layout and will adjust by hand. Known leftovers in it: some floating rocks, some crowding the path, some exposed terrain. Shore stones were raised slightly during this.
