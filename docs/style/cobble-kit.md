# Cobble kit, paths, walls and connecting pieces (2026-11-08)

The user's ask: small stone assets to place all over the hub. That means edging stones round flower beds, and compact cobbles
round the paved areas, after their reference. Two kinds of path, both needed:
- a **terrain path**, painted terrain;
- a **structured path**, made of Parts, with a cobble border generated round it.

The style is cartoon and Ghibli-like, iterated through a few designs before choosing.

## v2, after the user's notes (2026-11-08)
- **Hand-painted light, not edge lines.** Light now goes only on the edges that face up into the sun, judged by each bevel's own
  facing. It's a stroke that swells and thins, with stretches left unpainted. Before, every bevel and every corner where three
  bevels met was lit, which read as outlines from afar. The pebbles' lit shoulder follows the same rule.
- **Border stones:**
  - one row, not two: `Sett_Row8A`/`B`, `Row4`, `Row2`, curves, one square corner stone;
  - larger and rectangular: 1.5 to 2.6 long, about 1.3 wide, the same low height;
  - more varied, fitted tight (joints 0.02 to 0.06);
  - about half have a thin crack across their width, some partway.
- **Bed edging stones:** lower (0.5 to 0.8 showing), sunk 0.32 into the ground, narrower and longer (1.6 to 2.5). The singles
  follow suit.
- `sheet_v2.jpg` shows both styles again. The first sheet is `sheet.jpg`.
- **The user liked Chisel's painting and Pebble's colour**, so `ChiselSlate` paints the Chisel pieces with Pebble's blue-grey
  (`Cobble_ChiselSlate_Color.png` and `_Moss`; same meshes, another colour map). It's shown with the blue-grey border stones in
  `sheet_v3.jpg`. Most of the two styles' difference is their shape: flat planes make the painted bands read as planes of tone,
  while a smooth pebble turns them into one gradient.

## In Studio (2026-11-08)
- **Uploaded:** the Chisel edging and the border stones (`CobbleKit.glb`), the ChiselSlate colour and moss maps, SettCool and the
  paving tile. Ids are in `art/kit/cobbles/roblox.json`. Built by `cobble_kit.py -- export Chisel,Sett` and
  `upload_cobble_kit.py --luau art/kit/cobbles/cobble_kit_filled.luau`.
- **`tools/studio/cobble_kit.luau`** (the template) installs:
  - `ServerStorage.CobbleKit`: Edging, EdgingMoss and Border, every pivot at the run's start on the ground;
  - `MaterialService.HubPaving`, the flagstone tile on Slate, 16 studs a repeat. Any Part takes it with Material Slate and
    MaterialVariant HubPaving;
  - `Workspace.CobbleShelf`, with a worked example: a paved square with its border, a round bed and a long bed.
- Each piece carries a `Chain` attribute saying how to join the next one.

## The kit (built, painted, rendered)
- `tools/blender/cobble_kit.py -- build|render|export` builds 32 pieces and 24,000 triangles in all, into `art/kit/cobbles`.
- `tools/art/paint_cobble_kit.py` paints the sheets (about 1:40), all 1,024 square, at 52 to 68 texels a stud:
  - `Cobble_<Style>_Color.png`, plus `_Moss.png` for the edging styles;
  - `Cobble_SettCool_Color.png`, the setts in blue-grey;
  - `Paving_Color.png`, a seamless 16-stud flagstone tile.
- `sheet.jpg` compares the two styles side by side, high, at eye height and close up.

| Style | Look | Pieces |
|---|---|---|
| Pebble (A) | Soft rounded stones (superellipsoids with low lumps), smooth, blue-grey slate as in the reference | 5 singles, 2 straights (8 studs), curves r6/r12/r24, a 90 degree corner (r2.5), a loose cluster |
| Chisel (B) | The stylized rock kit's stones, smaller: flat planes, bevels with a painted light edge, its pale stone | the same 11 |
| Sett | Cut paving stones, bevelled boxes in tidy courses: warm grey, or blue-grey (`SettCool`, same meshes, another colour map) | single, one-course and two-course straights (8), two-course curves r8/r16/r32, a 2x2 corner block, a loose cluster |

**Chaining:**
- Every run starts at its origin on the ground. Straights run 8 studs along +X.
- A curve turns left round a centre on +Y. Turned 180 degrees it turns right, so one piece does both.
- Curves are cut so circles come out whole:
  - radius 6 takes 8 pieces, 12 takes 12, 24 takes 24;
  - setts: radius 8, 16 and 32 take 8, 16 and 32 pieces.
- A round bed of radius 6 is eight Curve6 pieces. A long bed is straights and pairs of corners.
- Stones sit 0.12 studs into the ground, so a piece on a gentle slope doesn't float.

**Seen so far** (Blender only, under Blender's light):
- Pebble reads closest to the reference from the high view: soft edging. Up close it's smooth, and the painted marks hardly show.
- Chisel reads as painted up close (planes and lit edges), and it matches the rocks we already have.
- The setts read well as a border at every distance.
- Next look passes, if wanted: more brushwork on Pebble, a mossy version in Studio, and a third style (flat-topped river stones).

## Two kinds of path
**Terrain path (organic):**
- A painted terrain material: the sandy path and dirt tiles, MaterialVariants as now.
- Terrain grass blades give it the jagged edge (`terrain-method.md`).
- Loose pieces dress the edges: the clusters, singles and broken setts.
- Still to make: a pale sandy path tile for the hub. The approved Mud and Sand tiles are the Vale's colours.

**Structured path (Parts):**
- You draw the paved area with Parts: blocks, wedges, and cylinders for round plazas. Size and turn them freely, in a folder
  (`Workspace.Paving`) or tagged `Paved`.
- Each Part's top is the paving, with the flagstone tile as a MaterialVariant on a base material like Slate, StudsPerTile 16.
- **Border generator** (to write, `tools/studio/pave_borders.luau`):
  1. Walk each paved Part's top outline.
  2. Drop the edges another paved Part covers, so joined Parts get one border round the outside.
  3. Lay double-sett strips along the straight edges, outside the paving. Shorter strips (4, 2 and 1 setts long) fill each
     edge's end exactly.
  4. Put a corner block at every outer corner, and curves round cylinders and rounded ends at the nearest of r8, r16 or r32.
  5. Scatter a few broken setts.
- It rebuilds only its own folder (`Workspace.Paving.Borders`), so you can edit the Parts and run it again.
- Strips of about 17 setts keep the count of instances low: about 12 per 100 studs of edge.

## Walls (thinking, not built)
The reference's retaining walls are big blue-grey blocks in tidy courses with a lighter rounded cap. Stairs have cheek walls and
plain treads.
- **Made the same way as the cobbles:** each block real geometry (a bevelled, slightly irregular box), several per piece, one
  painted sheet per stone set. Light is painted in bands, joints are dark, there's a lit edge on the arrises, and the stone is
  lighter on top and bluer low down, as hub.md describes.
- **Built things stay orderly** (art-style.md): one course height, running bond, sizes varying by only a little.
- **Pieces on an 8-stud grid:** straight sections 4, 8 and 16 high (the terrace steps are 16 and 20). Each comes in two or
  three bond variants so repeats don't show. Also outer and inner corners, end caps, and caps as their own strips, set half a
  section along so they bridge the joints.
- **Curves:** the terraces are blobby, so a wall follows them in straight 8-stud sections with small turns. The joins hide under
  a **pillar**, a square post with a cap that takes any angle, every two or three sections. That's a classic garden wall, and it
  avoids a curved piece for every radius.
- **Stairs:** straight flights rising 4, 8 and 16 (wide enough for the 26, 22 and 12 stud streets), a landing, cheek walls with
  caps that step down, balustrade posts and rails.
- **Placing:** the same idea as the border generator. You mark a wall's line, and a script lays sections and pillars along it
  with the right heights from the ground. The hub's grey stand-in walls (`Workspace.Hub.Walls`) would be its first input.

## Other pieces to place about the hub
In order of how much they add, from hub.md's list:
- lamp posts with hanging lanterns, benches, the round stone planter;
- flower clumps (white daisies, pink) to fill the beds;
- stepping stones, bollards, low hedges, cypress cones.
