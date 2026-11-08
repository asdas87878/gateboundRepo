# Forest types (Proposed 2026-11-06)

A forest reads from its layers, trunk rhythm, leaf shape and colour together, not from one good tree. Trees use the leaf-card method (`docs/style/foliage-method.md`, the user's choice), with `tools/blender/foliage_species.py` for species and leaf shapes from `make_foliage_textures.py <folder> broad small needle`.

| Forest | What makes it read | Canopy | Lower layer | Colour | Spacing |
|---|---|---|---|---|---|
| Deep wood | Closed canopy, heavy trunks, shade on the ground, gaps of light | Elm, oak (broad leaves) | Saplings, big shrubs, ferns | Deep teal-green over dark ground | Tight, uneven, with small clearings |
| Birch glade | Bright and vertical, pale trunks, sky between crowns | Birch (small leaves) | Low shrubs, saplings | Light yellow-green | Open, in loose clusters |
| Pine stand | Dark, upright, tiered silhouettes, open floor | Pine (needles) | A few ferns | Blue-green, dark | Regular-ish, tall trunks in rhythm |
| Orchard | Planted rows, round trees, tended | Apple (broad leaves) | Almost none, mown grass | Warm green | Grid, with a few missing or off-line |

## Rules for any forest
- **An edge belt:** saplings and shrubs where wood meets open ground; never trees starting as a wall.
- **Three sizes at least:** a few big ones lead, most are medium, some young.
- **Clearings:** gaps let light in and give the eye somewhere to rest.
- **Keep colours in a family:** each forest gets its own tint, with small variation inside it.

## Test patches
`tools/studio/tree_kit.luau` (masters in `ServerStorage.TreeKit`) then `tools/studio/forest_lab.luau` (`Workspace.ForestLab`, x 20000: five patches, 673 pieces). Sheet: `art/kit/foliage/species/forests_sheet.jpg`. Frame rate not measured.

## Giants and canopy (2026-11-06)
Giant: 135-170 studs before scaling, four leaders, tiers of long level branches, 36 leaf clumps, about 7,300 triangles. Canopy7 and Canopy23: a flat mass of leaves with no trunk (880 triangles), hung between trees at 66-145 studs to close the ceiling cheaply.
Trunks: `paint_trunk.py` now paints bark ribbons with framing grooves, darker ribbon edges and a pale ridge line (`RIBBONS`, `GROOVE`, `RIDGE`), the user's ask for more intentional trunks.
Known: giants' top tips show pale bare stubs, bare branches stick out below the leaves, canopy undersides are dark teal.

## Colossal trees (2026-11-06)
`tools/blender/colossal_tree.py`: a trunk about 60 studs across and 300-350 tall before scaling, 8 root buttresses, five tiers of huge limbs with flat leaf pads and open air between them. Three meshes (Trunk, Limbs, Crown), about 18,000 triangles a tree, two bark sheets; more trunk texture low down (`vpower`). `Workspace.ForestLab.ColossalWood`: 31 of them with a mid layer and floor, 1,207 pieces in the lab in total. Sheet: `art/kit/foliage/species/colossal_sheet.jpg`. Play test inside the wood on the dev PC (GTX 1660S): 60 fps, the cap, worst frame 22 ms, 1,573 mesh parts loaded, memory 2.3 GB including Studio. Not a low-end result, and one standing spot only.
Limbs now bend (`limb_path`), start inside the trunk with a thick collar. Bark is warm in the texture.
**Light, what worked:** only about a third of crowns cast shadow, so real sun dapples the floor; soft-textured beams (`art/kit/foliage/light_shaft.png`) along the sun's direction. **What failed:** warm PointLights on trunks cut off in a hard band, and untextured beams read as glass panels.
Shadow-free crowns and shafts don't line up with real gaps; fine at this stage. Roots look plain very close up.
Also: branches now go all round on single- and two-trunk trees (they were all aimed one way); branch bark sits close to one colour; leaves always cover leader tips.

## In Land 1 (2026-11-06)
`tools/studio/place_forests.luau` (built by a generator from `art/lands/verdant_vale/spec.json`'s wood polygons): `Workspace.Land1.Forests`, a type per area: HighWood and Thornwood (5 colossal in all, with mid trees and floor), Pines, Glade, Grove, Orchard, Frames; 351 pieces. Keeps off roads, water, rock, the bridge, cottages, props and fences by reading the terrain. Old trees moved to `ServerStorage.Land1TreesOld`. The user said it looks good at this density. Colossals stay 300 studs apart (`spread` 150); lower it for more. Rerun after `build_land_small.luau`. Not walked in Play yet.
