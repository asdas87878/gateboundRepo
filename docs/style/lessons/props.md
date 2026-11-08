# Lessons: props and wooden bridges

From the props session, 2026-11-06. Covers barrels, crates, carts and signs (`tools/art/props_kit.py`), the first bridge set (`tools/art/woodbridge_kit.py`) and the second set from the user's image (`tools/art/woodbridge_b_kit.py`).

Sections 1 and 2 separate the user's words from what I did. Anything marked **(my conclusion)** is mine, not the user's rule. Spelling in quotes is as typed.

## 1. What the user said

### Props, in order
1. **Highlights:** "decrease edge highlights by a lot, they look too blurry, too low quality and too random".
2. **Corner darkening:** "now lets get some darkening around some corners to kind of frame it a little bit, very AO like and sparse, not overdoing it".
3. **Another dark layer:** "is there another subtle layer of darkening in a different way we could add". I offered options; they picked "Add the gradient".
4. **Highlight spots:** "now lets get a faint bit of AO like highlights around some grouping vertices at points to where it would make like some highlight spots in good places like corners and tops".
5. **Spots on crates:** "some corners like on the boxes should have it".
6. **Spots stopping at seams:** "on corners its not properly spreading between things, like on one box the hihglights stop on top".
7. **Reversal, replaces 4 to 6:** "lets get rid of that last highlight step". The highlight spots were removed.
8. **Style question:** "what could be done to further improve the anime like ghibli style were going for and the roblox like anime style thing". From my options they picked "Colour and shadow shapes".
9. **Shadow rule, with a barrel screenshot:** "some of the shadows likje this one here just come in out of nowhere and woulnd tlook too good, the down ones and other things r good tho. ygm?"
10. **Sharpening:** "add the sharpening pass which the other agent made", then "Use soft", choosing soft over crisp.
11. **Studio:** "Yes, Studio next", "Scene shows fine", then "Approved" on the props as they looked in Studio.

### Wooden bridges, in order
12. **The ask:** "Let's try make a few wooden bridges. an arched one, a flat one etc"
13. **First set notes:** "Some of them look stretched, some of the highlights are just too much on the dark parts. I do like it overall, but some like the stretched wood, the long parts of wood can look a bit too stretched, and the highlights can just look like one straight line. I'm also thinking maybe we could add some like accent with like a darker thing. We could add maybe some brick or something, or some stone. We can take hints from the other agents."
14. **Go-ahead:** "Do all three" (fixed-scale grain; tapered highlights; dark timber, iron and stone). I recommended stone over brick and they accepted that without commenting on brick.
15. **New direction:** "try this", with an image of three bridges (`art/kit/woodbridge_b/reference.webp`): chunky flat, lattice arch with mossy caps, rope bridge.
16. **Critique of the match to that image:** "Kind of looks too from afar, just and maybe up close, just a bit too orangey, and there's just something lacking in the framing of it. Maybe it's just like the very monotonal feel that makes it not the best... Give it a critical look of artistic design choice."
17. **Go-ahead:** "Yes, apply it". That was my art pass: calmer colour, three values, plum shadows, stone ends, varied posts, a red banner. They chose this button rather than "Skip the accent".
18. **Verdict and shadow note:** "These look pretty good now. I will say bring them in a second, but before that could you fix the shadows which come in randomly. I dont like that."
19. **Form note:** "how could we make this look a bit more intentional? I feel like some of it looks like the texture was just plastered on. And while it does look hand-painted and nice, it looks like it doesn't quite fit the geometry or the form of some of the objects."
20. **Go-ahead:** "Yes, apply them". They haven't given a verdict on the result yet.

### Reversals
- Highlight spots: asked for (4 to 6), then removed (7).
- The fix for 1 caused 13: I replaced blurry highlights with one crisp thin line, which they then called "one straight line". Tapered strokes replaced it on the bridges. The props still have the line.
- From the concept image's single orange tone (15) to three values and a calmer colour (16, 17). **(my conclusion)** They didn't reject the image's shapes, only the colour and monotony.

## 2. Rejected

**By the user**
- Blurry edge highlights with a random rhythm on every edge: "too blurry, too low quality and too random".
- AO-like highlight spots at corners and tops: tried, then removed.
- Painted side shadows with no visible cause: "come in out of nowhere". Downward shadows under hoops and rims were kept: "the down ones and other things r good".
- One ruled highlight line: "one straight line".
- Strong highlights on dark wood: "too much on the dark parts".
- Long wood that looks stretched.
- Saturated single-tone orange: "too orangey", "very monotonal".
- Shadows on the bridges "which come in randomly".
- Paint that doesn't follow the form: "plastered on".
- The crisp look of the sharpening pass: they chose soft.

**Failed or rejected by me (my conclusion)**
- Knots and scratches on shared deck planks repeat as a stripe down the walkway, so planks now have almost none.
- Moss wrapped right round a post looks like a green ring. Flat moss mats on the deck look crude, so I removed them.
- The first rope pass was too thick and stripy, with too much sag.
- An S-curve arch looks like a hump. A plain circular curve looks better.
- I said the barrel's stripe was the render's sun. It was my painted shadow's edge. Don't blame the renderer before checking the paint.
- A hard plum band on posts below deck level, which I added and then removed: nothing casts it on outer faces.

## 3. What worked

### Colour
- **Fence grade:** `GRADE` (1.3, 1.27, 1.12), from `fence_kit.py`.
- **Props lift, measured in Studio:** `STUDIO_LIFT` (1.12, 1.16, 1.06), applied on top of `GRADE`.

| Studio reading (RGB) | Before lift | After lift |
|---|---|---|
| Fence rail, lit | 143 94 70 | no change |
| Fence rail, shade | 73 55 52 | no change |
| Barrel, lit | 120 79 66 | 140 101 72 |
| Barrel, shade | 64 42 41 | 77 54 45 |
| Crate top, lit | 172 116 86 | 194 141 91 |
| Crate frame, shade | 57 38 38 | 64 46 41 |

- **Shadow colour:** plum `SHADOW` (70, 48, 70).
- **Painted light tints (`props_kit.py`):** lit gold `LIT_TINT` (1.07, 1.03, 0.9), underside plum `UNDER_TINT` (0.76, 0.67, 0.76), top faces `TOP_TINT` (1.13, 1.08, 0.93).
- **Bridge wood values, before grade (`woodbridge_b_kit.py`):**
  - `WOOD_LIGHT` base (114, 76, 60): deck and top rails.
  - `WOOD_MID` base (96, 63, 54): lattice, lower rails, replaced boards, pegs.
  - `WOOD_DARK` base (74, 50, 50): posts, beams, legs, braces.
- **Other bridge colours, final:**
  - Slate base (126, 122, 128) with grade (1, 0.985, 0.92).
  - Straw rope (188, 160, 116).
  - Muted red banner (146, 54, 52).
  - Muted moss (96, 112, 60).
- **Rejected colour, for comparison:** the orange base was (124, 68, 40) before grade, about (181, 100, 48) after, roughly 73% saturation. The new light wood lands near (166, 112, 71).

### Paint layers on the approved props
Fence wood paint with no fence highlights, then one thin crisp line on chosen edges, then the gold-to-plum gradient, then shadow shapes with a hand-cut edge (`cut_edge`), then sparse corner darkening (`ao_spots`), then the soft crisp pass (`finish_sheet`, `crisp_paint.py`).

### Bridge methods (the newest; the user hasn't judged the last pass)
- **Fixed-scale grain:** `fixed_grain` wraps the fence painter's stroke functions, so marks stay stud-sized past 5 studs. The fence's own painter is untouched.
- **Tapered highlights:** short strokes that swell and thin, and that multiply the wood underneath rather than painting one colour, so dark wood gets a quieter highlight (`highlights`).
- **Paint fitted to form (`Kit` in `woodbridge_b_kit.py`):**
  - Each part type gets its own strip at its true size.
  - End grain is cut to the part's shape, with rings at a fixed stud spacing.
  - Contact marks go only on the faces something really touches (`touches`).
  - Rail and brace ends darken where they enter something (`ends_dark`).
  - Top rails are paler where hands run (`hand_worn`).
- **Declare, pack, then paint:** all strips are declared first, then packed, then painted, with separate random streams for shapes and paint so paint changes can't move shapes.
- **Stone by block size:** block lengths are limited to 2.2 to 3.9 studs, so none outgrows its paint.
- **Far-view test:** render from about 100 studs, plain and blurred. **(my conclusion)** If the big shapes don't read when blurred, fix the values, not the detail.

### Texel density and sheets
- **Wood:** 50 texels per stud.
- **Stone:** 30, and 38 on the stones standing at the deck ends. The stone bridge's walls are 28.
- **Coverage:** a 1024 sheet at 50 covers only about 419 sq studs. Each bridge has about 3,500 to 4,300, counting repeats and hidden faces, so repeated parts must share paint.
- **Sheets:** props share one 1024 sheet. Set B has one sheet per bridge, each bridge one mesh.

### Triangles
| Asset | Triangles |
|---|---|
| BarrelA, BarrelOpen | 156 each |
| BarrelPile | 592 |
| CrateA, CrateSmall | 124 each |
| CrateBroken | 264 |
| CrateStack | 528 |
| Cart / CartBroken | 772 / 800 |
| SignPost, SignLean | 148 each |
| First bridges: arched, flat, plank, broken | 3,184 / 3,048 / 768 / 2,928 |
| Second bridges: chunky, lattice, rope | 4,832 / 7,408 / 5,468 |

### Scripts
- **Props:** `python tools/art/props_kit.py art/kit/props [--look crisp|soft|none]`, then `blender --background --python tools/blender/props_kit.py -- art/kit/props`, then `tools/studio/place_props.luau`.
- **Bridges:** the same pattern with `woodbridge_kit.py` and `woodbridge_b_kit.py`, into `art/kit/woodbridge` and `art/kit/woodbridge_b`. The art scripts take `--sheet` for the comparison sheet.

## 4. Technical traps
- **A shared random stream couples paint to shape.** Removing a post's contact bands changed every prop's geometry, and removing stone planes changed the bridges. Keep separate streams, or keep the draws. Check with `md5sum` on the OBJs before and after a paint change.
- **`screen_capture` ignores a camera direction set from Luau:** every shot faces the same way. Pass `camera_position` and `look_at_position` to the tool.
- **Blank Studio captures:** captures came back as a dark viewport with only the axis gizmo. It cleared by the time the user checked Studio and I retried; I don't know the cause. Captures also fought over the camera, so they need Studio to be free.
- **End caps used half their tile:** `cap_uv` in `props_kit.py` only asks for 0.26 to 0.74 of a tile, so all end grain sat at half detail. `TileSpec.uv` opens this out in set B. The props still have it.
- **Stretched end grain looks stamped:** one tile squeezed onto every end shape gives the wavy marks. Cut each tile to the part's shape.
- **Paint scaled to the strip, not the part:** the fence painter sizes grain as 35 to 95% of strip length, so a 19-stud beam looked stretched without its UVs being stretched. Later, posts and stone used far past their painted size were really stretched. Measure with a per-triangle texel check (`stretch_report`).
- **A corner mark spanning shared tiles must be uniform:** random spots stop dead at a crate's tile seams (user note 6).
- **Contact bands wrap all four sides of a beam's strip:** on a sign post they showed on the back, where nothing touches, and didn't even line up with the boards.
- **Importer rotation:** setting `rotation_euler` wiped the OBJ importer's rotation and laid every prop on its side. Bake it with `transform_apply`.
- **Winding on mirrored or upside-down beams:** `moved()` rejects mirrors. A beam's top band can face down depending on draw direction, so `bar` and `sweep` swap ends to keep it up.
- **Sheet packing:** shelves ran out of room. The skyline packer works, but order matters.
- **Bash heredocs:** a heredoc containing apostrophes failed to parse, so I put edit scripts in files.
- **A false pass in a test:** a check for "lights" matched "highlights" in a docstring. Grep the code rather than trust a loose string match.

## 5. Scope

**The user's words behind them, my scoping**
- [All assets] A painted shadow goes only where something visibly casts it. Downward shadows under parts are fine.
- [All assets] Edge highlights are few and placed, not blurry, not random, and not one ruled line.
- [All assets] Highlights must not be strong on dark parts.
- [All assets] Long timber must not look stretched.
- [All assets] Paint must fit the form, not look plastered on.
- [All assets] Avoid saturated, single-tone colour. It reads "orangey" and "monotonal".
- [Unsure] Soft rather than crisp for the sharpening pass: they said it about the props. The bridge session may have its own answer.
- [Unsure] AO-like highlight spots are out: they removed them on props, and I don't know if that's general.
- [Only props] Sparse AO-like corner darkening and the gold-to-plum gradient. They asked for these on props, and it may suit other assets.

**(my conclusions, the user hasn't stated these)**
- [All assets] Three value groups, so the structure and walking surface separate from afar.
- [All assets] Judge from far away and blurred, as well as up close.
- [All assets] Grade only after a Studio reading. Pale paint needs less lift than dark.
- [All assets] Keep shape and paint random streams separate.
- [All assets] Check texel density numerically.
- [Unsure] One muted accent per hero asset. They accepted it on the bridges, not as a rule.
- [Unsure] Blue-grey stone as a frame for wood: they asked for "brick or something, or some stone", and I chose the stone.
- [Only props] Plank-like repeats shouldn't carry knots or scratches when they line up in a row.

## 6. Still open

**Props**
- **Status:** approved by the user in Studio.
- **Assets:** model `128094429859101`, texture `121270248937308`. Moderation was still "Reviewing" at upload, though it showed in Studio.
- **Unsaved:** the test row in `Workspace.Land1.Props` isn't saved in the place, as far as I know.
- **Not done:** the final scatter on Land 1.
- **Older paint:** props still have the ruled line, the half-size end grain, stretched-looking long planks and the old grain scale. Nothing has been decided about bringing them up to the bridges' method.

**First bridge set** (`art/kit/woodbridge`): Blender only. The user said "I do like it overall" before the second set replaced it as the focus. Whether to keep it is undecided.

**Second bridge set** (`art/kit/woodbridge_b`)
- **Status:** Blender only, nothing uploaded. "These look pretty good now" came before the shadow and form passes, and there's no verdict yet on the form pass. They said they'd bring them in "in a second".
- **Unverified:** colours in Studio, the dark timber's weight, contact mark strength and the arch's 7,408 triangles.
- **Issues I've flagged myself:** rail shoulders read as pale clips, foot moss on the arch looks like a smudge, and the chunky and arch sheets are nearly full.
- **Design change to check with the user:** I gave the rope bridge one A-frame per side, because the frames in their image would block the path.
- **Not done:** walkable deck colliders, tall invisible rail blockers (the bridge session found a character steps over anything under 3.8 studs), and fitting to a real river. The chunky and arch bridges have no piers.
- **Unsure:** the bridge session found a 180 degree turn about each glb part's centre. I saw no such problem on the props, but I haven't tested the bridges.

**Fence:** unchanged. It still has its older highlights and wrap-around contact bands, so it now differs from the bridges up close. Matching it is undecided.

**Brick:** the user mentioned it; I steered to stone. It hasn't been tried.
