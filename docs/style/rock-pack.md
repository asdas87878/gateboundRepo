# Rock pack (2026-11-06)

50 rocks for building scenes by hand, each with moss and clean paint. The user blocks out environments themself; this is what they build from.

**In the place:** masters in `ServerStorage.RockPack` (`Moss` and `Clean`, a folder per group). A shelf to copy from is at `Workspace.RockPack`, at x 30000, a Folder so a click picks one rock: select its `ShelfGround` in the Explorer and press F. Moss aisle first, then the clean one. Each rock's pivot is at its foot. Rocks under 2 studs tall have no collision.

| Group | Count | What |
|---|---|---|
| Clusters | 11 | Already composed, one piece each: tall, low, stacked, twin, stepped, wide, small |
| Blocks | 10 | Single chunky blocks: cube, tall, wide, wedge, notched, split |
| Modular | 6 | Exact sizes on a 4-stud grid with flat tops, so they stack and line up: `Mod8x8x8`, `Mod16x16x8`, `Mod16x16x16`, `Mod32x16x8`, `ModCorner16`, `ModStep16` |
| Cliffs | 11 | Big rock faces, 48-113 studs wide: slab, columns, strata, terrace, buttress, corner, overhang, crag, arch, long wall, foot rubble |
| Loose | 6 | Two boulders, two shelves, a spire, a pebble scatter |
| FromBefore | 6 | From the earlier kits, repainted to match: `WallWide`, `WallStep`, `FootWide`, `SlabLong`, `BoulderWide`, `Corner` |

44,549 triangles for one of each; the heaviest is `CliffWallLong` at 3,357. 33 sheets at 1024, each in two paints (models 129400180408641 and 121152188517515, all ids in `art/kit/rock_pack/roblox.json`).

## How it's made
```
blender --background --python tools/blender/rock_pack.py -- build
python tools/art/paint_rock_pack.py --workers 4          (about 20 minutes)
blender --background --python tools/blender/rock_pack.py -- render all Moss
blender --background --python tools/blender/rock_pack.py -- export
python tools/art/upload_rock_pack.py                     (only what changed)
python tools/art/rock_pack_luau.py <out.luau>            then run <out.luau> in Studio's edit mode
```
- **The 50 are `KEEP` in `rock_pack.py`.** About 170 are defined; `--all` builds them, so more can be swapped in or added cheaply. Rerunning `rock_pack.luau` replaces the masters and the shelf, not rocks already placed in a scene.
- **A rebuild changes the UVs**, so repaint after one. To fix something small in the built file, edit `rock_pack.blend` rather than rebuilding. To add one piece without touching the rest, build it alone (`build --only <Name> --out art/kit/rock_pack/extra`), as `Corner` was: it replaced `NatCrag`, whose folded shape read as broken in Studio, so `Corner` isn't in `rock_pack.blend`. A full rebuild picks it up from `KEEP`.
- **Repainting without rebuilding** keeps the UVs, so the new sheets fit every placed copy: upload, then map old texture ids to new ones on every SurfaceAppearance, as done on 2026-11-06. Fresh uploads show white for a few seconds in Studio.
- **Shape:** a lump is a box with a tapered, tilted or leaning top, cut by planes: chips, chamfers and shallow facets that split a face into two planes. Only edges over 25° get a bevel and a highlight; shallower highlights came out as dashes across the faces.
- **Paint:** one tone per plane, each lump lighter at its top and darker at its foot; firm dark crevices only where surfaces really meet; soft pale highlights in long runs and gaps. The crisp pass (`docs/style/crisp-paint.md`) runs with few big brush shapes, which otherwise came out as pale ellipses on plain faces. Colours are in `PALETTES`.
- **Colour of the reference:** the lilac in the user's reference shot is blue haze over pale grey stone, so the paint stays the same stone as the earlier rocks and the bridge. Haze belongs to the scene's atmosphere. A new palette is a repaint and upload: themed Lands can use this.

## Checked in Studio (2026-11-06)
Seen from the front at a distance, at player height and from behind. No inside-out faces. Under the place's light the stone reads as the same blue-lilac as the user's reference. Cliff fronts face -Z on the shelf. On the shaded side rocks go dark navy: that's the place's lighting, for a lighting pass.

## Not done
- Performance not measured. Sheets cost memory only when used, but a scene using all of them in both paints would be heavy (very roughly 350 MB of texture, an estimate).
- Cliffs are painted at 5-9 texels a stud, against 16-22 for clusters and blocks, so they're soft up close: use them behind, with clusters and blocks at their feet.
- A few crevices keep some faint speckle after the repaint.
