# The hub island (blockout Proposed 2026-11-08)

A fresh start for the hub. It's a floating saucer with the "Silent" poster's shape and the tree-stump painting's ambience: very high up, a sunny green land far below, a giant tree silhouette fading into the haze, a clear blue sky. Player plots hang around it on bridges, so everyone can see who has the best base. This is the island's shape only: no buildings yet. It replaces the composition in `haven.md`, which is kept for reference.

Build: `blender --background --python tools/blender/hub_blockout.py -- art/hub` (about 1 minute). It writes `art/hub/hub_blockout.blend` (open it to look around) and renders to `art/hub/blockout/` (`sheet.jpg`). Every number is at the top of the script. `--flat-deck` drops the terraces, `--no-plots` the plots, `--views hero,bridge` renders only those views.

## Shape, top to bottom
| Layer | Size (studs) | From the references |
|---|---|---|
| Deck (grass) | 940 across, rising about 26 to the middle in two low terraces with stone retaining walls (off-centre, not round) | The town climbs toward the middle, like the painting's central crag |
| Grass lip | Rolls over the edge and drips down the wall in grouped tongues | The painting's dripping grass cap |
| Arcade | 64 arched bays, 37 wide and 36 tall, on a 50-tall band with string and base courses and keystones | The poster's pale band with arches |
| Flange | The widest point, 1,050 across: 40 chunky blocks with dark joints | The poster's wide ring |
| Rock skirt | A ragged ring of faceted dark rocks hanging under the flange, longer in waves | The poster's dark ragged band |
| Lower band, step, bowl | 730 across with two grooves; then the bowl, about 500 across, with two stepped rings, rounding off 400 below the deck | The poster's stepped underside |
| Docks | 8 stone platforms on buttress piers, with gate posts, each the head of a plot's bridge; north stays open toward the tree | Ours |
| Waterfalls | 2 off the front, fading as they fall | Both references |
| Plots | 8 islands about 220 across, 70 below the deck and 940 from the middle, on 260-long rope bridges | The user's idea: bases come out from the edges |

- Height for the views: the land is 3,200 studs below the deck, a broken cloud layer at 1,650 below, and the tree 42,000 away at bearing 32 (a bit east of north), about 19,000 tall.
- Walks at 16 studs a second: across the deck about 60 s. Dock to plot about 17 s. Plot to the middle of the deck about 50 s, so a quicker way home will be needed again (a launch pad or a waystone).
- Shapes are cartoon-chunky: generous bevels, rings about 1.5% out of round, block sizes varied by only a stud or two (built things stay orderly, per art-style.md).

## How to texture it (proposal)
These are the methods the user's sessions have already proven (survey: `side-session-notes/.../texturing-methods.md`), chosen for a 1,000-stud object that's seen from a stud away and from a mile away.

1. **Build it as a kit, not one giant mesh.** One unique texture on a 1,000-stud island would give about 1 pixel per stud. The saucer repeats, so split it into modules that share painted sheets:
   - an arcade bay and a dock pier;
   - three flange blocks and six skirt rocks;
   - band and bowl sectors.

   Paint them with the approved per-texel 3D painter (Cycles AO bake, our brush recipes, soft finish): close parts at 20-30 px a stud, the bowl at 5-9 px, since it's only seen from far.
2. **One stone set for the hub.** Pale cream stone with lavender-blue shade, as in the poster. Use orderly coursed masonry on the arcade and flange (one course height, running bond), and the rock-pack style for the skirt. Make it lighter on top and cooler and bluer going down, as big horizontal bands of value, so the shape reads from far before any detail does.
3. **Value from the shape.** Bake crevice occlusion, height and bands into the sheets (the "Salt strata" idea from the other project) so the arch recesses, joints and the underside's steps read even under flat light.
4. **The deck is Roblox terrain grass**, the approved low-key tiles and blades, with paths by our blockout-to-terrain route when the town goes in. The lip and drips are painted meshes in the grass's own colour (checked with `grass_match.py`, within 3 L).
5. **A look target first.** Paint over our hero and bridge renders with an image model, keeping the composition (as `art/haven/prompts.md` does), then sample its colours rather than guess them. That costs credits, so it needs the user's OK first.

**Around it**
- **Sky:** a painted clear gradient sky with the giant tree painted into the faces near the horizon. It can't be geometry 42,000 studs away (streaming, and draw distance at low settings). The earlier painted cyan sky was rejected for flat clouds and washing out the scene: keep the clouds out of this sky, or keep the approved Stylized Skybox's.
- **Clouds:** painted cloud cards in layers (the other project's method). The 3D puffs in these renders look like cotton balls, as they did there.
- **The land below:** too far down for Roblox terrain, since terrain past about 1,024 studs doesn't load on the client. Use a few big painted low-poly ground meshes kept loaded (Persistent), hazed by Atmosphere, with the far horizon in the sky's lower half.

## Bigger, with a town on it (Proposed 2026-11-08, in the new base place)
The user asked for a much bigger hub with the vibe of their reference: a terraced storybook town with cobbled streets, stone
retaining walls and stairs, white flower beds, lamp posts, benches and a round planter. They will hand-place the assets; Claude makes
the assets, the lighting and the textures. The vibe is the target, not the reference's layout.

**Scale:** deck 1,800 studs across (was 940), flange 2,000. That's about 2 minutes to walk across at 16 studs a second. Eight plots,
300 across, sit 70 below on 240-stud bridges, their centres 1,330 from the middle. The arrival dock is at -z, and the town climbs
toward +z, so the afternoon sun (ClockTime 15.6, from -x -z) lights the faces the arrival view sees.

**The composition** (`art/hub/plan.png`):
| Zone | Where | What goes there |
|---|---|---|
| Arrival dock | -z rim | Sky-ship arrivals later; Market street starts here |
| Waystone plaza | 600 in | Home: the waystone in a round flower ring, dock master, notice board, benches |
| Market street | Up the middle | Cobbled, 26 wide, lamps both sides, shops with gaps for flowers and alleys |
| Upper town | Terrace 16 up, 1,000 across, not round | Ring road (cobble), the town square: inn, town hall, forge, guild hall, stalls, quest board |
| The Crown | Terrace 36 up | Gate court: six theme arches facing out, the Climb tower, a trophy hall, a lookout toward the giant tree |
| Residents' lane | +x side | Eleven houses for rescued NPCs along a cobbled lane |
| Flower gardens | -x side | Two low flower terraces, a greenhouse, a gardener; a pond with two streams that pour off the rim as waterfalls |
| Orchard, tree lookout | +z rim | Trees by hand; a sandy lookout with benches |
| Rim promenade | All round, 68 in from the edge | Sand path; a low parapet on the edge, open at the docks and waterfalls |
| Spokes | 8 sand paths | Ring road to each plot dock |

**Build:**
- `python tools/art/hub_layout.py` writes `art/hub/layout.json`, `art/hub/plan.png` and the filled `art/hub/studio/build_hub.luau`.
  Every number is in that file. It also checks that no building lot sits across a change of level.
- Run the filled script in Studio's edit mode (`tools/studio/build_hub.luau` is the template). It took about 2 seconds.
- Each layer has its own folder in `Workspace.Hub` and is rebuilt only when it's on in `RUN` at the top of the script.
- **Turn a layer off once you've edited it by hand.** Terrain rewrites the deck and the plots, so hand sculpting there is lost.

**The layers in Studio:**
| Layer | What it builds |
|---|---|
| Setup | Removes the Baseplate; spawn at the waystone plaza |
| Materials | The approved low-key grass and faded rock tiles, mud and sand tiles, terrain colours (cobble and sand tinted pale), grass blades on |
| Lighting | The values every asset's grade was measured under (Brightness 3, ClockTime 15.6, OutdoorAmbient 110, 118, 145), plus roblox-lighting.md section 9's extras: warm ColorShift_Top, sky light 0.35, soft shadows 0.15, a light haze, bloom 0.3, grade +0.08 saturation. The Stylized Skybox (8755940451) went in through the toolbox, because the script's LoadAsset failed |
| Terrain | Deck and terraces as terrain: grass, cobble streets and plazas, sand paths, Pavement for the gate court, the pond and streams as water, Rock under the cliffs; the plots' grass tops |
| Island | Cylinder stand-ins for the saucer (arcade band, flange, rock skirt, stepped bowl), two waterfall cards, a green land 3,200 below |
| Walls | 982 segments: retaining walls round every raised level (2.5 above it), the rim parapet |
| Stairs | 18 ramps where streets cross a wall, each tagged with the stair asset it needs |
| Lots | 49 ghost boxes, each labelled with a kit house (attribute `Asset`) or the asset still needed (`Needs`). A yellow strip marks the door side (a kit house's +z) |
| Docks | Stone platforms with gate posts; plank bridges with rope rails to the plots |
| Plots | Rock stand-ins under the plots |
| Guides | Lamp posts and benches marking the rhythm along Market street and round the plazas |
| Labels | Zone names floating over the map |

**Every asset we have is in the place** (installed 2026-11-08, no new uploads): `ServerStorage` has HouseKit (12), RockPack (50, moss and
clean), SwordKit, TreeKit (21), FenceKit (4), PropsKit (11) and BridgeKit (the assembled StoneBridge and its pieces). Shelves to copy
from are near x 30,000: `Workspace.RockPack`, `HousePack`, `SwordPack` and `KitShelf` (`tools/studio/kit_shelf.luau`). Select a
shelf's ShelfGround and press F. The fence, props, bridge and house scripts now install just their kit in a place with no
`Workspace.Land1`.

## Assets the hub still needs (to make, in this order)
1. **Ground tiles:** pale warm cobble flagstones for streets and plazas, a light sandy path tile. The terrain uses Roblox's own
   Cobblestone, tinted, for now.
2. **Walls and stairs kit:** retaining wall straights and curves with caps, corners, wide stairs (straight and curved), balustrade
   and parapet pieces for the rim.
3. **Street dressing:** wooden lamp posts with hanging lanterns, wall lanterns, benches, signposts, the round stone planter.
4. **Planting:** white daisy and pink flower beds, low hedges, neat cypress cones and topiary (the kit's pines are wild), window
   boxes. The trees we have suit the orchard and the rim.
5. **Centrepieces:** the waystone, six theme arches, the Climb tower, market stalls, a quest and notice board, a greenhouse, the dock
   gates and rope plank bridges (the second wooden bridge set is in Blender, no verdict yet).
6. **A tower house:** an octagonal tower with a red tiled roof (Rose Cottage's tiles), and Rose Cottage itself (built, not uploaded).
7. **The island:** the saucer as kit pieces (arcade bay, flange blocks, skirt rocks, bowl), the grass lip and drips, waterfalls,
   cloud cards, the sky with the giant tree, the painted land below.

## Open
- Is the scale right now (1,800-stud deck, 2,000 flange)? The first blockout's 940 was too small.
- Do the terraces stay, or should the deck be flat for the user to shape?
- The plots: ring of 8 below the deck on bridges, or a crescent on one side?
- What goes on the deck: a town (shops, forge, quest NPCs), the gates to the Lands, the Climb? Where the Lands are now that the world is a land far below.
- Not checked: triangle counts or Roblox performance. Nothing is in Studio.
