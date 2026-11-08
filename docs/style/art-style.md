# Art style standard

The one standard for every Gatebound asset, merged on 2026-11-06 from the fence, rock pack, houses, stone bridge, props, wooden bridges and stone sword. **Read this before making or repainting an asset.** Where the user corrected something more than once, the latest note wins.

- **Rules** are what the user said, with their words in quotes. **Working practice** is our own, learned along the way, and the user can overrule it.
- Each session's full notes, with every quote and number, are in `docs/style/lessons/` (`cottage.md`, `bridge.md`, `props.md`), and `stone-sword.md` and `rock-pack.md` beside this file.
- Studied from the Stylized Environment Lesson and two videos by DatBoiEle (private copies in `research/`): method and style only, never their assets or layouts.

## What the style is
A hand-painted illustration standing in 3D, anime and Studio Ghibli. Simple chunky shapes carry paint, and the paint carries colour, light and wear. It fails in two directions: "too realistic, like a ps3 game", and noise.

## Rules for every asset

1. **Intentional, not random.** The user's most repeated note, in every session: "too random", "too much visual noise", "more intentional", "plastered on". Group detail, put it where the eye lands, and leave plain areas. Negative space is part of the design.
2. **Big shapes read first.** Too little variety fails ("homogenous from a far", "very monotonal"), and so do too many small marks. Fix a flat far view with big shapes of light, tone and colour, not more small variation. Small marks stay close in hue and value; contrast comes from big shapes and edges.
3. **Ghibli, not realistic.** Warm lights, flat washes with firm brush edges, and coloured joints. No wet gradients, pits, near-black lines in stone or puffy per-stone shading. The ink lines on the stone sword are a choice for that asset, taken from its concept art.
4. **Sharp enough up close, soft where it counts.** Marks hold up close; highlights and glows are soft. Fully blurred lost detail ("lost some detail close up"), and harsh, sharp paint looked low-grade. **Finish: soft by default** (`crisp_paint.py --look soft`). Crisp is there when an asset calls for it: the user kept it on the stone bridge.
5. **Highlights: choose the method that suits the asset.** In every case they aren't blurry and aren't "one straight line", they're quiet on dark parts ("too much on the dark parts"), they're pale cream and never saturated or red, and strokes taper and fade rather than stopping dead. No highlight spots on corners and tops: tried and removed.
   - **Few and placed**, for big assets with many edges, such as houses and props, where a highlight on every edge turns to noise: "way less edge highlights, more strategic highlights, less randomized"; "decrease edge highlights by a lot".
   - **Varied rhythm**, for assets with a few big, plain parts, such as the fence: each edge has its own strong runs, faint stretches, gaps and bleeds, "carefully, artistically".
   - **Only where the light catches**, for faceted stones (the cobble kit, 2026-11-08). A lit edge on every bevel, meeting at every corner,
     "from afar does look just like we've added edge lines". Paint light only on the edges that face up into the sun. Vary the width
     and leave stretches out, so it looks painted by hand. `paint_cobble_kit.py` does this by the bevel's own facing.
6. **Light runs across the whole object.** Paint it in, so the asset reads under any lighting. **Lighter on top and darker low by default; houses are the exception**, with their wood darker and richer at the top. On assembled things it's "mostly collective", with each piece only slightly its own; a gradient on every piece reads as "visual clutter". Another direction is fine when an asset calls for it.
7. **Painted shadows need something casting them.** Shadows that "come in out of nowhere" were rejected twice; downward ones under rims and hoops are good. Corner darkening is "very AO like and sparse, not overdoing it"; overdone framing was "too detailed and dark".
8. **Paint fits the form.** Long wood must not look "stretched", and paint must not look "plastered on" or as if it "doesn't quite fit the geometry". Marks stay stud-sized on long parts, end grain is cut to the part's shape, and contact marks go only on faces something really touches.
9. **Calm colour, one set per Land.** No saturated single tones ("too orangey"). Darks have colour, leaning plum or blue, never black or grey. Plum goes vivid in Studio's shade, so keep it soft. Stains on plaster are never orange or yellow. **Each Land or theme picks one stone and one wood**; an asset gets recoloured when it's used in a Land, and keeps its current colours until then. The set for a Land can bend where an asset calls for it.
10. **Moss is painted, and grouped.** Paint it rather than modelling clumps. Big grouped shapes in "mainly two-tonal, maybe three-tonal", "not as heavy on the highlights". Brushwork only at its edges. Place a few chosen masses, not a scatter. `paint_moss` in `tools/art/paint_sword.py` is the recipe. The rock pack's moss is older and busier.
11. **Ground it.** Assets sink into the terrain, darker and mossy at the foot, with grass breaking the contact.
12. **A reference is a guide unless you're asked to match it.** "you dont need to stand by the reference as law either for structure. make it good ur own way." When the user asks for a match, as on the sword, match it, and measure its colours rather than guessing.
13. **Don't change land or layouts to suit an asset without asking.** The user may say no ("Leave it").

## Rules by kind of asset

**Built things (houses, masonry, stone bridges)**
- **Orderly.** Varied stones were "way too random and the bricks dont fit together well, some wrong sizes". Use one course height, parallel rows and running bond, with stones cut to fit. Use one post size and windows of one size ("exactly the same size"); differences here read as errors ("not looking uniform"). Wear lives in the paint, not in random sizes.
- **Connected.** Stone needs "some type of connecting piece" and arches built into the wall, so it all looks "cohesive".

**Houses**
- **Space:** "go liberal, even a bit more" around windows and doors. "two wood parts shouldn't be touching with each other"; only a frame's own joints may meet.
- **Windows:** "a bit bigger and square like". Soft reflections that differ per window, not uniform bars.
- **Plaster:** keeps its cream, darks are colder, and there are no highlights between streaks. Streaks cluster into one block with some fingers, curving round rather than circular or blocky.
- **Wood:** one top-to-bottom gradient across the house, and "just the wood on soft". Green wood is darker and cooler at the top, breaking into streaks.
- **Stone:** "the dark warm stone", which frames the house.
- **Prop houses** have no interiors. An interactive one, like a forge, gets "more care and attention" and VFX later.

**Nature and ruin (rocks, trees, the sword)**
- **Chunky and imperfect.** Nothing straight, level or evenly spaced: parts lean, taper and overlap. This is where irregularity belongs. Facets exist to catch paint, not to add fine detail.
- **Rocks define cliffs.** They hide terrain's polygons on steep faces. On clusters, no moss patches on side faces.
- **Trees:** no sharp colour contrast in branches; "keep this ghibli soft look".

**Wood (fence, props, bridges)**
- Keep patches close to the base colour; the first fence read as camouflage. Separate the structure from the walking surface with big value groups, not busy marks.

**Placing assets**
- Gaps, rotations, leans and broken pieces, never a clean row. Even spaced sections read as a row from far away, so leave stretches open. The user places scenes by hand, so assets arrive ready to drag, in folders.

**Lighting**
- Do it last; the asset must carry the look without it. The user would "rather stay away" from point lights (said on houses; treat it as general until told otherwise). Dark shadows and a colour in the shadows are lighting-pass tools.

## How to judge an asset
Side by side with the reference, **in Studio**, at player height, up close and from far away, from at least two sides including the shaded one. Blender can't show Studio's colours or its back-face hiding. Ask:
- From far away and blurred, do the big shapes read?
- Up close, is it painted and intentional, or noisy?
- Do highlights fade rather than stop? Does every shadow have a cause?
- Does the paint fit the shape?
- Is it part of the ground, or imposed on it?

Modular walls also get a square-on side view, which is where the user caught the uneven bricks.

**When matching a reference image** (the user, 2026-11-08: "a lot of scrutiny in the thickness of certain things, and
especially where things are placed... Some of them should overlap. The chimney should be on the roof"): before testing in
Studio, check region by region at full size against the reference: where each element sits, what overlaps or nests in
what (a tower set into the house, not beside it), what rests on what (a chimney's foot on the roof), and how thick things
are (eaves, sills, curbs, arch rings). Measure positions by back-projecting the reference's pixels through the camera, and
trace anything odd with a ray-cast from the camera rather than guessing. Structure comes before paint ("all of these things need to
be perfect in order for the textures to sit right"): roof outline and overhang, tower shape, how each part is built; check it in clay
against the reference first. Keep it cartoonish, not rigid ("tower should become smaller at the top larger at the bottom, some
windows come in at diff angles... less rigid"): tapers, slight leans, windows a few degrees off true, a gentle waviness, while sizes
and courses stay orderly. Roof flares stay gentle: a strong bell-cast with a lifted corner read as "curling up too much".
Read depth before building, because outlines can't show it (the user, on the crooked cottage: "the middle part, it sticks out. You
didn't stick it out"): an area lit like the side walls is a side face, so the part beside it stands out; visible undersides,
the shift of an edge against the wall behind it, timbers' side faces and shadow widths give overhang and relief. Wood that sticks
out too far, has the wrong shape or no tilt, and windows of the wrong shape are "a huge aesthetic detriment"; so is negative space
that differs from the reference, so copy its layout of timbers exactly.

## Working practice (ours, not the user's rules)

**Colour in Studio**
- Grade every asset after measuring it in Studio, because no one grade fits. Pale paint needs less lift than dark, and Studio's sky adds blue.

| Asset | Grade (R, G, B) | Note |
|---|---|---|
| Fence | 1.3, 1.27, 1.12 | Read 35% too dark |
| Props | Fence grade, then 1.12, 1.16, 1.06 | Dark wood |
| Stone bridge | 1.0, 0.985, 0.92 | Warmth only |
| Stone sword | 0.97, 0.99, 0.85 | Blue only |
| Houses | Per material, `studio_match` in `house_looks.py` | Plaster, stone and glass needed the most |

- **These are tied to the current lighting:** Brightness 3, ClockTime 15.6, sun (-0.74, 0.54, -0.40), OutdoorAmbient (0.43, 0.46, 0.57), Ambient 0.27. A lighting pass means measuring them again, so keep a grade as its own step, on top of the approved paint, as the houses do.
- Shaded sides go dark and blue on everything in this place. That's the lighting, not the sheets.

**Texture and triangles**
- Roblox cuts textures to 1024. Paint at double size and shrink with Lanczos.
- Texels per stud so far: surfaces seen up close 50-60; house and bridge walls 17-30; the sword 16-20; cliffs 5-9, which look soft up close.
- Don't decimate unasked. "The try count will be fine" was said about prop houses up to about 19,000 triangles. Studio-side performance is unmeasured for most assets.

**Building**
- Keep separate random streams for shape and paint, so a paint change can't move geometry.
- Check stretch and winding by script: Roblox hides back faces, and Blender doesn't.
- Test a grade on a few assets before uploading all. Uploads can only be removed from the Creator Dashboard.
- Don't rerun a placement script over hand-placed work. Swap textures instead.

**Collision**
- Meshes have no collision; invisible, locked `Collider` parts stand in.
- A character steps over anything under 3.8 studs. Blocking walls reach about 15 studs above the art, or a jump lands on top of them.

**Traps in Studio**
- The glb importer turns each mesh 180 degrees about its own centre. Place with `CFrame.new(centre) * CFrame.Angles(0, math.pi, 0)`.
- Terrain's surface sits about 2 studs above a written height (measured at both the bridge and the blockout).
- Blank dark captures mean Studio isn't drawing, usually because its window is covered. One capture per message.
- A new concave face needs `normal_update()` before triangulating, or it fills with wrong-facing triangles (holes in Roblox).
- Clear `bpy.data.objects` before a Blender build, or the default cube gets exported.
- Write patch scripts to files; heredocs with quotes break the shell.

## Assets and where they stand

| Asset | State | How it's made |
|---|---|---|
| Fence | Approved 2026-11-06. Older highlights and wrap-around contact bands | `tools/art/fence_kit.py`, `tools/studio/place_fence.luau` |
| Rock pack, 50 | Done, in Studio. Older moss | `docs/style/rock-pack.md` |
| Props | Approved in Studio. Older ruled highlight line and grain | `tools/art/props_kit.py` |
| Houses, 12 | Design chosen ("dark warm stone"); no verdict on the Studio colours | `tools/art/house_looks.py`, `tools/art/houses_upload.py`, `docs/style/lessons/cottage.md` |
| Stone bridge | In Studio, awaiting the user's OK | `tools/art/bridge_kit.py`, `docs/style/crisp-paint.md` |
| Wooden bridges (second set) | Blender only, no verdict on the last pass | `tools/art/woodbridge_b_kit.py` |
| Stone sword | In Studio, moss repainted; the user liked it | `docs/style/stone-sword.md` |
| Cobble kit (edging, setts, paving tile) | Blender only; two edging styles waiting on the user's pick | `docs/style/cobble-kit.md` |

## Where the sessions disagreed (settled by the user, 2026-11-06)
The user's approach: note both and use whichever suits the case. These are defaults, not bans.

| Question | Decision | Also allowed |
|---|---|---|
| Highlights | Both kept: choose by the asset (rule 5) | |
| Finish | Soft by default | Crisp, as on the stone bridge. Houses and the sword have no sharpening pass and stay as they are |
| Gradient direction | Lighter on top, except houses | Another direction where an asset calls for it |
| Stone and wood colours | One set per Land | So far: sandstone (stone bridge), dark warm stone (houses), blue-grey slate (wooden bridges), pale grey (rock pack), olive-grey (sword). They haven't been seen together |
