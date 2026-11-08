# Landscape review: why the Vale still feels off (2026-11-03)

The user asked for a harsh comparison with good games. Our walk views and vistas were measured with the same numbers
as gameplay frames from Genshin Impact (Mondstadt), Breath of the Wild, the GPT-6.2 reference, Lonely Mountains:
Downhill, Valheim and Ghost of Tsushima (`tools/art/scene_metrics.py`). The frames stay private in the gitignored
`research/`; only the numbers are here.

## The numbers

"Land" is the lower 60% of the frame. Lightness L is 0-100. Chroma is colour strength. Fine/coarse is small-mark detail
over big-shape detail (above 1 = busy). Edges are the share of strong-edge pixels near/mid/far.

| Set | L p5 / p50 / p95 | Dark chroma | Hue variety (bits) | Macro patches | Fine/coarse | Edges near / mid / far |
|---|---|---|---|---|---|---|
| **Ours, walk views (before this review)** | **5 / 32 / 57** | **14.1** | **1.69** | 8.4 | **0.79** | **9% / 8% / 7%** |
| Ours, walk views (after this round, `beauty/w07`) | 6 / 38 / 62 | 14.3 | 1.87 | 8.9 | 0.71 | 14% / 11% / 7% |
| Ours, vistas | 7 / 42 / 72 | 12.8 | 1.76 | 13.5 | 0.63 | 11% / 9% / 7% |
| Genshin Impact, Mondstadt fields | 41 / 73 / 84 | 45.5 | 2.01 | 9.3 | 0.46 | 2% / 4% / 6% |
| Breath of the Wild, fields | 23 / 52 / 78 | 17.9 | 2.18 | 11.4 | 0.54 | 4% / 4% / 7% |
| GPT-6.2 reference game | 23 / 46 / 65 | 13.4 | 1.85 | 7.8 | 0.52 | 8% / 2% / 3% |
| Lonely Mountains: Downhill | 39 / 61 / 74 | 18.7 | 1.80 | 7.2 | 0.29 | 1% / 1% / 2% |
| Valheim, meadows | 24 / 51 / 73 | 21.4 | 1.60 | 9.8 | 0.64 | 7% / 4% / 5% |
| Ghost of Tsushima, blossom grove (photoreal, moody) | 2 / 28 / 68 | 5.7 | 1.06 | 11.7 | 0.74 | 3% / 14% / 26% |

After this round:
- The median lightness rose from 32 to 38.
- Colour variety rose from 1.69 to 1.87, past GPT-6.2.
- The small-mark busyness eased from 0.79 to 0.71.
- Still unsolved:
  - The darks are still crushed. Partly that's the black player stand-in in every frame; partly the canopy
    undersides.
  - Shadows are still grey (14 against Genshin's 45): the fill light alone can't colour them.
  - The near ground is now busier (14% edges), from the outcrops and patch props.

## Side by side at walking height (`research/compare_walk_vs_games.jpg`, private)

Our three walk views over frames from Genshin, BotW, GPT-6.2, Lonely Mountains, Valheim and Ghost of Tsushima. What
the eye sees that the numbers only hint at:
- **Our road reads as a crack.**
  - It's darker than the grass around it: mid-brown with dark rut stripes.
  - In every reference the path is the lightest thing on the ground: Genshin's warm sand, BotW's pale dirt, GPT-6.2's
    tan road. The eye follows light, so their paths lead and ours hides.
  - Theirs are also wide (2-3 character widths) with soft, grassy edges.
- **Our grass reads as static.**
  - Every thin blade has its own highlight and dark gap, from the boots to 90 studs.
  - The references are either soft masses with lit tops (Genshin, BotW, Valheim), or smooth ground with a few long,
    sweeping tufts (Genshin's path edges, GPT-6.2).
  - Ours is the worst of both: a carpet made of spikes.
- **Ours is olive and mid-key; theirs is high-key.**
  - Genshin and BotW: bright lime under a cyan sky, sunlit ground near white.
  - GPT-6.2, the user's target, is closer to us in colour, but its ground is smoother and its road lighter, so it
    still reads cleaner.
- **No big shape near the player.**
  - Most reference frames have one big thing within about 20 studs: a rounded boulder, a giant tree, a ruin wall,
    a cliff.
  - Ours: a flat field to the skyline, with the castle as the only shape.
- **The character.** Theirs are lit and colourful; our stand-in is a black block that is the darkest, biggest thing in
  every walk view. Not the landscape's fault, but it drags every frame down until there's a real avatar.
- **Where we hold up:**
  - Sky and clouds, the mountain ranges, the sense of scale, the castle's silhouette and the crop fields compare well.
  - The grand view the user liked is real; the ground under the player is what lets it down.

## What's wrong, worst first

1. **It's dark where the player stands.**
   - Our land's median lightness is 32. Every stylised reference sits between 46 and 73, and Genshin, the closest
     match to what we're making, sits at 73.
   - Our darks are crushed to 5, near black; theirs start at 23-41.
   - Causes:
     - The grass carpet shaded itself: every blade cast a shadow on the next. Roblox's decoration grass casts no
       shadows, so the renders were darker than the game would ever be.
     - The blades had dark roots, and the forest canopies have near-black undersides.
     - The fill light was a neutral grey-green.
2. **Our shadows are grey; theirs are coloured.** Dark chroma is 14 against Genshin's 45.
   - Genshin, BotW and Lonely Mountains all paint shadows a rich teal or violet; a stylised world never lets a shadow
     go grey.
   - Ours were the lit colour minus light, plus a neutral fill.
3. **It's busy everywhere, with nowhere for the eye to rest.**
   - Fine/coarse is 0.79 against 0.46-0.54. The mid and far ground is as full of edges as the foreground (8% and 7%
     against GPT-6.2's 2% and 3%).
   - We spray detail evenly over the whole Vale: grass to 150 studs, single trees every few dozen studs, dotted hedges,
     scattered pebbles.
   - Good games put detail where the player is and leave big calm shapes behind: an open meadow, then a dense wood,
     then a clean hillside.
   - From a walk view our meadow is one fine noise from the boots to the horizon.
4. **The land has no shapes at walking scale.**
   - The terrain is soft noise: no outcrops, banks, ledges, gullies or crests.
   - Genshin's fields are broken by big boulders and rock shelves, terraces and cliffs at the edges of clearings.
   - BotW's triangle rule needs medium shapes that hide and reveal. We had almost none, so every walk view is "a lawn,
     then the skyline".
5. **Trees are lollipops on a lawn.**
   - Singles sprinkled across the meadows, a handful of variants repeated.
   - Woods start as a wall: no belt of shrubs, saplings and tall grass at the edge.
   - Good games group trees into groves with open grass between, and soften edges with understorey.
6. **One green.** Hue variety is 1.69 bits against Genshin 2.01 and BotW 2.18. The ground had soft patches but no
   real changes of colour: dry straw, clover, bare earth, moss, flower beds.
7. **The light is a static noon.**
   - No cloud shadows moving across the land; in BotW and Genshin they give scale and life.
   - No shafts of light in the woods, no rim light.
   - (Roblox has no cloud shadows built in, so this one needs a trick or goes without.)
8. **Water is a flat mirror with a hard edge.** No shore: wet band, reeds, stones, foam, a gradient from shallow to
   deep.
9. **Buildings stand on the grass like toys on a carpet.** No foundation or rubble, no tufts against walls, no worn
   ground at doors and gates.
10. **No life.** No birds, butterflies, pollen or smoke from chimneys. Stills hide wind, but a frame with nothing moving
    reads as a model.

## What good games do that we didn't

- **Genshin:**
  - High-key land: bright lime grass, light ground, saturated teal shadows.
  - Big blue-grey boulders and rock shelves as mid-ground shapes.
  - Ground textures smooth near the player, so detail sits on objects, not in the floor.
  - Paths as soft tan strips with tall clumps along the edges.
- **BotW:** layered landforms (triangles in three sizes), strong haze layering, groves on hilltops, cloud shadows.
- **Lonely Mountains:** almost no fine noise (fine/coarse 0.29). The look is big flat facets, clean light and a few
  flower clusters for colour.
- **GPT-6.2:**
  - Detail in the foreground only (edges 8% near, 2% mid).
  - Pine groves as dark masses against light ground.
  - Clear roads.

## Fixes, ranked by impact

| # | Fix | Status |
|---|---|---|
| 1 | Grass casts no shadows (as in Roblox); lighter blades (root ×0.95, tip ×1.14), about 20% sparser | done in this round |
| 2 | Coloured shadows: a cool sky-blue fill standing in for a blue OutdoorAmbient | done in this round (tune by eye) |
| 3 | Randomised patches: clover, dry straw, bare scrapes, flower beds, stony ground | done in this round |
| 4 | Calm the distance: grass only to ~95 studs; trees gathered into fewer, denser groves | done in this round |
| 5 | Rock outcrops on slopes and crests, each with stones at its foot: walk-scale shapes | done in this round |
| 6 | **Roads lighter than the grass:** pale sand-tan, wider main roads (2-3 characters), soft grassy edges, ruts only a hint | next: the quickest big win |
| 7 | **Grass as masses, not spikes:** a short, smooth carpet that reads as ground, and fewer, bigger, softer tufts with lit tips as the feature | next |
| 8 | **Colour key A/B:** today's GPT-6.2 olive against a brighter Genshin-leaning lime with cyan sky. The user picks | next |
| 9 | One big shape within ~20 studs of most walking spots (a boulder, a big tree, a ruin wall) | partly (outcrops); more with Tripo models |
| 10 | Landforms: banks along sunken lanes, ledges and terraces, low cliffs at the edges of clearings | next |
| 11 | Forest edges: a belt of shrubs, saplings and tall grass; groves with understorey | next (the user's Tripo trees can carry this) |
| 12 | Shorelines: wet band, reeds, stones, shallow-water colour | next |
| 13 | Building footings: stone plinths, rubble, tufts against walls, worn ground at gates | next (with the user's Tripo houses) |
| 14 | Life: birds, butterflies, chimney smoke, drifting pollen | in the game, with Roblox particles |
| 15 | Cloud shadows | test in Roblox: a slow-moving dark decal layer or skip |

## Second diagnosis, after the grass colour fix (2026-11-04, `beauty/w09/diagnosis.jpg`)

The one-line version: the player stands on a lawn looking at a postcard. The impressive things are all far away, and
the ground underfoot has no shape and nothing on it. That is why it holds up from a distance and not up close. The grass
itself is no longer the problem.

`tools/art/walk_review.py` (walk views against reference frames):

| Measure | Ours (w09) | GPT-6.2 | Genshin | BotW | Valheim |
|---|---|---|---|---|---|
| Sky's share of the frame (median skyline from the top) | 34% | 19% | 5% | 18% | 9% |
| Near ground, tuft-scale contrast | 2.7 | 3.2 | 2.9 | 3.9 | 5.9 |
| Near ground, clump-scale contrast (plain meadow alone: 2.8) | 3.3 | 4.6 | 3.6 | 4.9 | 4.9 |
| Near ground, big light and dark masses (plain meadow alone: 3.9) | 6.5 | 7.5 | 8.0 | 8.0 | 8.8 |
| Road lightness minus grass lightness | -34, -16 | +15 | +14 | +6 | not measured |

Ours is the average of four walk views. Its big-mass figure is lifted by the wheat and by the hard mountain shadow, so
the plain meadow number is the fairer one. Part of the sky share is the walk views' camera angle (about 5 degrees down),
but tilting it down only shows more lawn.

Worst first:
1. **The land has no shape where you walk.** On the road and in the meadow the height range within 150 studs (about 9
   seconds of walking) is only 5-7 studs, against a camera 6.6 studs up. About 80% of the ground to 150 studs is in plain
   view, so little hides or reveals anything, and slopes never catch the light.
2. **Nothing is near the player.** In the meadow view the nearest thing taller than a flower is a lone tree far off. The
   reference frames usually have a boulder, tree or wall close by.
3. **The road.**
   - It is darker than the grass; in the references it is lighter, and the eye follows it.
   - It is orange-brown where theirs is yellow-tan, in ruler-straight stripes and flat patchwork quads.
   - **Bug:** the mesh follows the smoothed line (`smooth_line`), but the ground paint, terrain flattening and grass
     clearing use the raw path. They sit up to 17 studs apart, off by more than the road's half width on 19-26% of five
     of the six paths. So `meadow_town` shows two roads, and grass grows on the mesh one. This is a real cause of the
     earlier "grass on the trails" problem.
   - **Bridges don't connect:** deck ends sit 1.7-5.7 studs above the ground and the road runs under them.
4. **Several art styles in one frame.** Soft, blurry ground and clouds; hard canopy facets a couple of studs wide; grass
   blades about a tenth of a stud wide; smooth near mountains against crisp, glassy far ones. The references hold one
   language throughout. Tripo models could add another look, so test one tree and one house in the walk views first.
5. **No big areas of light and dark on the ground.** No cloud shadows and hardly any slope. The one big shadow, from the
   eastern mountains about 400 studs away, cuts a hard line across the Gate hill. Canopies are too dark: 40% of the forest
   view is near-black.
6. **Placement reads as scatter.** Hedge bushes like beads on a string, pebbles in a dotted line, flowers on dark stilts
   sprinkled evenly, lone trees. Nothing says people live here: no fences, carts or farm tracks.
7. **The beam and island read as graphics.** A hard white hairline with no glow; a grey cut-out whose waterfalls look like
   legs.

Tested and not a problem: detail isn't squeezed into a thin band any more than in the references (38% of it in the
busiest fifth of rows, against 38-39% for Genshin and GPT-6.2).

Limit of this review: these are still renders. Wind, camera motion and sound change how a place feels, and Roblox terrain
won't reproduce this ground exactly.

## For the user's Tripo models (houses, trees)

- **Trees:**
  - Clumped, soft canopy silhouettes with light-to-mid green tops.
  - Undersides no darker than about L 30, so the canopy shadow stays coloured, not black.
  - A few species per area, each in 2-3 sizes.
  - Also make saplings and shrubs for forest edges.
- **Houses:**
  - A stone plinth or footing at the base, so they sit in the ground.
  - Roof colours from the Vale palette (slate blue `#4d6584`, tile red `#b0573a`).
  - Keep fronts and doors readable from the road.
- **Everything:** check it next to the 5.2-stud stand-in. A door is about 3.5 × 6.5 studs; a cottage eave sits about
  1.5-2 players up.
