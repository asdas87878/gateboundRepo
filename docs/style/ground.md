# Ground at a player's feet (2026-11-03)

The user's review of the first beauty pass: grand from a distance, but close up the ground was a blur, the dark tufts
fought the light base and grew along the trails, and nothing had been judged from where a player actually stands. So
every look change is now checked from **walk views**: an over-the-shoulder camera at Roblox's default field of view
(70) on a 5.2-stud player stand-in (map.json `Beauty.Views` entries with `Player`/`Facing`; `walk_road`,
`walk_meadow`, `walk_forest`, `walk_gate_road`, `walk_ruins`, `walk_bridge`).

## Base ground: colour patches + crisp detail

- **Vertex colours** carry the big patches: zone greens, dry spots, rock on steep faces, banks, field crops.
  - They're blurry by nature: one colour per 2.5 studs.
  - In Roblox, these patches are different Terrain materials or variants painted in areas: a few grass variants
    (light, dark, dry), plus Ground, Rock and Sand.
- **Tiling detail textures** keep it crisp up close.
  - `tools/art/ground_textures.py` paints them. Each averages a fixed value, so the shader multiplies the colour by
    texture ÷ average without changing the patch colour.
    - **Grass:** mottling plus blade strokes, every 12 studs.
    - **Dirt:** grit and pebbles, every 8 studs.
    - **Rock:** flat patches and cracks, every 16 studs.
  - The shader picks one by the ground's `rockw`/`dirtw` weights (`detail_material` in `vale_beauty.py`).
  - Roblox: the same images become Terrain MaterialVariant colour maps at the same studs per tile.

## Trails are meshes, not paint

Terrain paints paths as soft blends: our vertex colours do, and so do Roblox's 4-stud terrain cells. A trail's edge
is what tells a player "this is the way", so each path is a ribbon mesh laid on the ground (`trails()`, settings in
`Beauty.Trails`):
- The edge is crisp and wobbles a little.
- Across its width: a scuffed margin, packed dirt, two wheel ruts, and a crown in the middle (grassy on country lanes
  via `Crown`, dirt on main roads).
- Every face is its own shade, under the dirt detail texture.
- Stones sit half-sunk along the edges.
- The ribbon breaks for the town's cobbles and for water: bridges carry the road.
- The terrain's own painted dirt is narrower than the ribbon (`Ground.PathPaint`), so no blurry halo shows outside
  the edge.
- Roblox: MeshParts with vertex colours, laid on the terrain.

## Grass placement and colour (see also grass.md)

- **Nothing grows on a trail.** The short carpet comes back at the trail's edge thin and short, then fills in over
  about 4 studs: a worn verge (`VergeFrom`/`VergeTo`).
- **Taller clumps** stay 2-7 studs off the trails. They gather:
  - in patches (noise);
  - in a ring at the feet of rocks, trees, walls and signposts (`Shelter`): the grass feet and mowers don't reach.
- **Colour:** every blade takes the ground colour under it, kept within a few percent of it.
  - Root ×0.9 to tip ×1.08.
  - Each clump is nudged a little cooler and darker or warmer and lighter (`Vary`).
  - Dark tufts are only a sprinkle (`Accent`).
- **Flowers:** in patches, off the trails. **Pebbles:** along trail edges and banks.

## Randomised patches and outcrops (after the landscape review, landscape-review.md)

- **Patches** (`ground_patches()`, `patch_props()`, settings in `Beauty.Patches`): about 500 irregular blobs over the
  meadows, off trails, water, town, fields and steep ground. The mix of kinds depends on the zone (stony on Mossrock,
  dry on Bandit Ridge, flowery in the Sunny Meadows).

  | Kind | What it does |
  |---|---|
  | Clover | richer green, a little more grass, white clover flowers |
  | Dry straw | yellow ground, thinner grass, taller straw clumps |
  | Bare scrape | a crisp decal of worn earth, no grass, a few pebbles |
  | Flower bed | one kind of flower, dense |
  | Stony ground | a rock cluster, sparse grass |

  Roblox: painted Terrain materials or variants for the colour; the decals, rocks and flowers as small MeshParts near
  the player.
- **Outcrops** (`outcrops()`, `Beauty.Outcrops`): about 70 big boulders half-buried on slopes and crests. They lean
  with the hill, have stones at their feet, and break the grass into shapes at walking scale.
- **Grass casts no shadows** (`matched_material`). Roblox's decoration grass doesn't either, and a carpet that shades
  itself rendered near black.

## Fields up close

Painted strips read as flat stripes from a player's height. Each field strip now has a crop, picked by its colour
(`Fields.Kinds`); the plants take the field colour under them:
- **Wheat:** dense golden stalks about 2.2 studs tall.
- **Greens:** leafy plants on the ridges between furrows.
- **Bare plough:** furrows only.
- **Fallow:** ordinary meadow grass.

## Finding the way without UI (research, 2026-11-03)

A research pass covered how Elden Ring, Breath of the Wild, Ghost of Tsushima and Genshin Impact guide players
through landscapes (developer talks and interviews, analysts, practitioners). Tags: [Dev] = developer source,
[Ana] = analyst.

What we take:
1. **The Gate is the Vale's Erdtree.**
   - Elden Ring's Erdtree is one main landmark seen from almost everywhere, with smaller local ones beside it [Dev].
     The Gate's beam does that job.
   - Its glow stays a colour nothing else in the Vale uses.
   - It is revealed in stages, as BotW does: a hill, then a bridge, then the tower [Dev].
   - It is reached by a gentle climb; players tend to drift downhill [Ana].
2. **Spread the pulls.** Points of interest pull by how visible and how useful they are. BotW found that lining events
   up between towers made players feel herded [Dev]. So the ruins, the forest edge and the meadows each get a visible
   lure off the road, and the walk zig-zags.
3. **Road hierarchy with marked junctions.**
   - Lanes are narrower than the main roads (`Trails.Width`, lanes ×0.7, grassy crown).
   - A signpost stands at every junction (`signposts()`).
   - Main roads never dead-end. Lost players follow the biggest road.
4. **Ground shaped by footfall:** bare trail, short grass at the verge, tall tufts at the roadsides and at the feet of
   rocks and walls. Use terrain for worn ground and meshes for crisp edges, because Roblox terrain holds one material
   per 4-stud cell.
5. **A camera that follows slopes** (John Nesky's 50 camera rules, GDC 2014): pitch up on climbs so the Gate stays in
   frame; let trunks and grass pass the camera; keep the player near the centre. For the game's camera code.

Also:
- Guidance by light that players can ignore (Elden Ring's faint golden trail at graces) fits our waystones.
- Breadcrumbs along roads (Ghost of Tsushima's torii gates, Elden Ring's map stones) teach the route.
- "If you can see it, you can reach it" (Ghost of Tsushima): never show a lure players can't reach.
- Roblox's FieldOfView 70 is vertical, about 102° across at 16:9, so the middle distance looks small. Landmarks
  should be 4-5 times the player's height or more.
- Trees: few species per area, in clusters with open grass between, about 9 studs clear of paths
  (`Trees.PathClear`).

## Trees at player height

`tools/blender/tree_compare.py` renders broadleaf styles next to a 5.2-stud figure (`art/style/trees/sheet.jpg`).
Faceted canopies (`TreeStyle: facet`) won over smooth blobs:
- many smaller leaf clumps in a dome, each facet catching the light on its own;
- lighter undersides and bark;
- a flared root.
