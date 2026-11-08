# Rose Cottage (2026-11-08, not in Studio yet)

A new house in the old house kit's family (cream plaster, square windows, a green door and shutters, lots of plain plaster around
every piece of wood), made a bit cooler with the crooked cottage study's chunky pink tiles, bell-cast roofs, wood painting and colours.
It's my own design rather than a copy of a reference, because the user found the reference copy "falls apart up close".
`sheet.jpg`: hero | up close | far | clay.

## The design
- **L plan.** A 1.5-storey main block (17 x 10) and a jettied two-storey gable wing (9 wide) standing 4 studs forward on the right.
- **The main roof** has a gentle bell-cast. In the inside corner its eave swings out and down over the porch (a catslide), so the door
  is sheltered by the house's own roof. The dormer sits over the shuttered window; the chimney (cream render, brick top, clay pot)
  rises near the left gable.
- **The wing.** Its upper floor stands 0.7 out over a row of joist ends and a bressumer. The upper floor has two curved braces under
  the plate. The gable is plain, with barges, a pendant at the apex and a ridge beak.
- **The porch.** One post on a stone pad, a beam into the wing's corner post, one curved brace. Beside it: a lantern on an iron
  bracket, and a climbing rose (the name).

## Spacing rules (house_base.py)
- 1.35 studs of plaster from a window or door surround to other wood or the roof.
- Separate wood parts don't touch.
- Windows are square at 2.6; the dormer's is 0.8 of that.
- **Wood placement.** Only where a house has it: corner posts, sill beams, floor beams and plates, door posts and lintel, the jetty.
  Everything between is plain plaster.
- **Wood sizes.** Slimmer than the crooked study's: corner posts 0.9 square standing 0.3 out of the plaster, window surrounds 0.42
  wide standing 0.15 out.
- **Shutters.** They need about 6 studs of wall with their margins. That's why the main block is 17 long and the gable end 10 deep.
- **No brick patches or painted moss.** Both read as stamps on clean plaster.

## Rebuild (from the RpgGame root)
```
blender --background --python tools/blender/rose_cottage.py -- build
blender --background --python tools/blender/rose_cottage.py -- bake_ao 40
COTTAGE_OUT=art/kit/rosecottage python tools/art/paint_crooked_cottage.py
blender --background --python tools/blender/rose_cottage.py -- render <tag> --view=hero|near|far|back [--clay] [--flat]
```
The builder imports `tools/blender/crooked_cottage.py` as its library: tiles, roof faces, timbers, windows and render.
- `lay_tiles(..., inside=True)` ends every row flush with the face's edges, laying a narrower tile where the bond leaves a gap. Without
  it, a far verge seen from below showed end tiles floating past the barge.
- The verge edge strips reach up under the tile lips (`VERGE_EDGE`).

## Still to do
- The back and right side are plain (one window each, no detail pass yet).
- The rose is a rough first pass (a column of leaf balls with pink dots).
- Not exported or uploaded. Studio placement waits on the user's choice of place.
