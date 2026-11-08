# Lessons from the stone bridge (2026-11-06)

Raw notes for merging into one standard, not a standard yet. Anything marked **(mine)** is my own conclusion, and the user did not say it. Only the quotes in section 1 are the user's words.

Asset: `tools/art/bridge_kit.py`, `tools/blender/bridge_kit.py`, `tools/art/bridge_luau.py`, `tools/art/bridge_sheet.py`, output in `art/kit/bridge/`.

## 1. What the user said

All user messages, in order. The "Context" and "What it replaced" lines are mine, for reading them.

1. **"looks way too random and the bricks dont fit together well, some wrong sizes, especially from a side view"**
   - Context: the first version, with varied stone heights in slate.
   - What it replaced: varied, irregular stones became strict rows.
2. **"what could be done to make this look less homogenous from a far"**
   - Context: the strict rows, now one grey-blue average at a distance. It was a question, and I offered five ranked options.
3. **"Yes, do those three"**
   - The three: paint light across the whole bridge; clusters of tone; big moss and ivy shapes in a few chosen places.
   - Not chosen: ordered size changes; silhouette changes (parapet bays, banners, lanterns).
4. **"its much better now but it still looks like its maybe trying to be too realistic, like a ps3 game. when we want it to feel more ghibli esque"**
   - What it replaced: grey stone, wet gradients, cracks and near-black joints became warm light stone and flat washes.
5. **"looks way better now from a far, but its lost some detail close up, or sharpness in detail rather. how could we go about solving that"**
   - The user interrupted before I answered, and this was the next message.
6. **"go ahead with the new palette light sandstone ver"**
   - Chose Sandstone over Dove and Rose. The grey slate was already gone.
7. **"what did you do for making the texture look nice and semi pixelated in texture close up"**
   - My reading: approval of the crisp pass's close-up grain, in their word "nice". The pixelation was a side effect, not something I aimed for.
8. **"can we make that a method so i can apply iit to the prop objects of another agent"**
   - Led to `tools/art/crisp_paint.py` and `docs/style/crisp-paint.md`.
9. **"is there anyway we could do that half n half in which it keeps the pixelation type thing whilst maybe not darkening and crisping it as much so it looks a bit soft still"**
   - Led to `--look soft`.
10. **"keep crisp for bridge, just update the other agent thing and ill run it"**
    - I recommended soft for the bridge, and the user overruled that: the bridge stays crisp.
    - They did not say which look the props should use. The command I gave them used `--look soft`.
11. **"we can go studio when its ur turn"**, then **"Yes, go"**, then **"It's in front"**
    - Scheduling only. The last one was about Studio being the front window, which captures need.
12. **"Leave it"**
    - Answer to my question about filling the notch in the river bank beside the far post, so the land stays unfilled.
    - It is not a verdict on the comparison sheet.

**The parent session's brief, not the user's words:** chunky coursed stone, arches, low parapets, a few loose stones, sensible collision, players mustn't fall off the ends, ends meet the road. Don't change the spec or `land_small.py`. Reference images are study only. Don't decimate unasked.

**Reversals, in order**
- Irregular stones became strict rows (message 1).
- Flat tone became big shapes of light, tone and green (messages 2-3).
- Grey realism became warm Ghibli (message 4).
- Soft washes became crisp brush edges for sharpness up close (messages 5 and 7). The Ghibli colour and flat light stayed, so crisp did not replace Ghibli.
- My soft pick for the bridge became crisp (message 10).

## 2. Rejected

**By the user**
- Stones of varied height, and rows that stretch or wander: "way too random", "dont fit together", "wrong sizes".
- A wall where every part averages to one tone: "homogenous from a far".
- Grey stone, dark wet gradients, cracks and pits, near-black joints, puffy per-stone shading: "too realistic, like a ps3 game". Which of these drove the comment is **(mine)**; the user named only the overall read.
- Washes with soft edges everywhere: "lost some detail close up, or sharpness in detail".
- Soft look on the bridge: "keep crisp for bridge". Soft itself was not rejected; it was requested for the props.
- Filling the notch by the far post: "Leave it".

**By me, shown or mentioned to the user with no objection (mine)**
- Dove palette: it drifted back toward the old grey. Rose: pinker than anything else planned for the land. The user never commented on either directly.
- A broken coping gap, a stone fallen on the deck, stray moss on the arch feet and pier caps, and most of the loose stones. I removed these during the strict rewrite and offered to bring them back. The user didn't ask for them.

**Failed on my own check (mine)**
- Ivy built as triangular shapes read as bunting. Overlapping leaf clumps replaced it, but it is still lumpy up close.
- Ground-based dropping of stones next to arches left dark holes. Stones are now cut to fit under the rings and run on under the banks.
- Scattered tone variation averages back to grey at a distance, so clusters are used instead.
- The first soft look lost the grain, so `shapes` and `marks` were raised back up.

## 3. What worked

**Masonry** (`bridge_kit.py`)
- Every wall stone is one height, `COURSE = 2.3`, with widths from a set: `WIDTHS = (2.2, 3.4, 4.4, 5.4)`. `JOINT = 0.05`.
- Running bond: no joint within 0.85 of the joint in the row above.
- Rows run parallel to the deck by shear, so the hump never stretches a row.
- Stones are cut by half-plane clipping under arch rings and at pier edges (`Mesh.clip`, `add_clipped`).
- Each stone is a pillow: a face plus a chamfer band, mapped to a painted card on the sheet. Coping and string courses are unrolled strips.
- Shape: spans 30, 38, 30; `PIER = 9`; `RING = 2.2`; `PARAPET = 2.2`; `APRON = 7`, running down to 0.2 under the road; `WING = 7`; `NOSE = 3.4`.
- Judge with a square-on side view. The user's complaint was "especially from a side view", and earlier views hid it.

**Reading from far away** (user-approved: "much better", then "looks way better now from a far")
- Light by height, `LEVEL_VALUE`: lip 1.02, lit 1.06, mid 1.0, low 0.93, water 0.86. Plus a shadow band under the ledge and coping.
- Hand-placed tone `PATCHES`, about 5-6 per side, with `TONE` pale (1.12, 1.08, 1.0) and dark (0.86, 0.88, 0.98), which is cooler rather than blacker.
- Coping and arch rings paler than the wall, so the arches and top line read first.
- Four ivy curtains, each off to one side of a span, leaf clumps on the pier tops, and an algae line at the water.

**Colour: Sandstone** (the user's pick, `SCHEMES`)
- Base 190 178 156, light 214 202 176, warm 204 180 146, dusk 158 152 158, cool 168 170 172.
- Mortar 112 100 114 (plum, not black), crack 122 112 118, shadow 122 120 156 (lavender), wet 136 146 160.
- Deck base 206 192 164, deck light 224 210 180, deck dusk 176 166 160.
- Edge highlight 254 246 224, pale edge 236 226 200, moss 132 182 88, dark moss 82 142 88, algae 104 160 138.

**Paint**
- Flat gouache washes with firm brush edges, not per-stone normals. Flat normals, specular 0 in preview.
- Crisp method in `tools/art/crisp_paint.py`, guide in `docs/style/crisp-paint.md`. It runs on any finished sheet, with `--look crisp|soft`, `--grain x|none`, `--strength`, `--shapes`, `--marks`, `--dark`, `--sharpen`, `--seed`.
- Crisp amounts: hard brush mask blurred about 0.4 pixels; marks 0.5 opacity; sharpen 0.9.
- Soft amounts: `shapes` 1.1, `marks` 0.9, `dark` 0.35, `sharpen` 0.2, and each island keeps its average colour.
- Paint at double size and shrink with Lanczos.

**Texel density and cost**
- Up-close parts (deck, inner parapet, coping): 54 texels a stud on their own 1024 sheet. Before, they had about 30, which is where the user saw it go soft.
- Walls 28 (up from 23), arch rings 34. The fence is 50.
- 14,171 triangles, 7 meshes, two 1024 sheets. BridgeA 2817, B 2571, C 3573, TopA 1638, TopB 1472, TopC 1610, Loose 490.
- 78 invisible colliders, and the meshes have no collision.

**Grade measured in Studio** (the brighter half of the pixels in a box on the lit wall)

| | R G B | red/blue |
|---|---|---|
| Blender | 202 199 182 | 1.11 |
| Studio, before grade | 216 213 207 | 1.05 |
| Studio, after grade | 216 211 197 | 1.10 |

- `GRADE = (1.0, 0.985, 0.92)`: warm only. The fence needed a lift of 1.3, 1.27, 1.12, so one fixed grade does not fit all assets.
- The lit wall ended up warm enough and a little brighter than Blender.
- Shaded wall: 91 110 143 before, 91 107 130 after, so still blue. **(mine)** That comes from the land's lighting, and the sheet can't fix it.
- The before and after readings use the same pixel box. I didn't re-verify that the two cameras were identical.

**Scripts**
```bash
python tools/art/bridge_kit.py art/kit/bridge [Sandstone] [crisp|soft]
```
```bash
blender --background --python tools/blender/bridge_kit.py -- art/kit/bridge
```
```bash
python tools/art/bridge_luau.py 76270751925424 109288797326259 128914057925264
```
```bash
python tools/art/bridge_sheet.py art/kit/bridge
```
`bridge_luau.py` writes `tools/studio/place_bridge.luau`, which needs rerunning after `build_land_small.luau`. `bridge_sheet.py` writes `compare_reference.jpg` and `compare_studio.jpg`.

## 4. Technical traps

**In Studio**
- **Glb turned 180°:** each part arrives turned about its own centre, so spans step out of line at the joints and a dark wall crosses the deck. Fix: `* CFrame.Angles(0, math.pi, 0)`. The cottage had this too.
- **Terrain is higher than the height map:** Studio's voxel ground reads about 1.9 studs above it along the bridge line, and the water stays at 8. The ends were buried. Fix: `Lift = 1.9`. After it, the deck sits 0.4 above the ground at the near end and 0.1 at the far end.
- **Side effect of the lift:** the painted waterline now sits about 2 studs above the water.
- **Low walls don't block:** a character steps over anything under its hip height, 3.8 studs from root to floor. A 3-stud parapet stopped nobody. A collider reaching 9 above the stone let a single jump land on its invisible top (root reached 40.7). `WALL_UP = 15` held after 1, 3 and 6 jumps.
- **Capture problems:** blank dark frames mean Studio isn't the front window. Dark mirror water and a thin green line mean the camera is inside a hill, so raycast the ground first. See also memory `studio-capture-camera`.
- **Moderation:** images marked "Reviewing" at upload still rendered in captures.
- **Grey-box return:** `build_land_small.luau` brings the grey-box back, so the placement must be rerun.

**Geometry**
- **Preview hid the walls:** overwriting the importer's object rotation turned the bridge the wrong way in the preview. Compose the matrix instead.
- **Winding:** wing faces were culled on one side from a wrong outward sign. `Mesh.check` now checks every triangle.
- **Spikes above the parapet:** the hump pushed top stones past the coping. The shear design fixed it.
- **Open or poking parts:** the coping's open underside showed sky under the overhang, so the beam is now closed. Post caps had slits, so they now meet at the corners. The keystone poked through the string course (`RING` 2.7 to 2.2, key +0.12).

**Tools**
- `crisp_preview.py`: an out folder equal to the sheets folder overwrites the input sheets, because renders are named after them.
- `crisp_paint.py`: a sheet with no flat background is treated as one island, so marks can cross seams.

## 5. Scope

Every tag is **(mine)**, because the user never stated a scope. "User" means the user asked for it on the bridge; "Mine" means I concluded it. Merging should confirm the tags.

| Rule | Source | Tag |
|---|---|---|
| Built masonry is orderly: one course height, parallel rows, running bond, stones fitted | User | [Unsure] all built stonework, likely including the cottage's |
| Too much random variation reads as wrong, not as hand-made | User, on bricks | [Unsure] |
| Judge from far away as well as close, and fix a flat far read with big shapes, not more small variation | User asked; method mine | [All assets] |
| Ghibli, not realistic: warm lights, soft coloured joints, lavender shadows, no noise, pits or cracks | User | [All assets] |
| Sharp enough up close while staying Ghibli | User | [All assets] |
| Semi-pixelated painted grain is liked | User, "look nice" | [Unsure] |
| Crisp look | User, for the bridge only | [Only bridges] |
| Soft look on props | User asked for it; final choice not stated | [Unsure] |
| Sandstone palette | User, for the bridge | [Only bridges] |
| About 50+ texels a stud on surfaces seen up close | Mine | [All assets] |
| Second sheet for the up-close parts | Mine | [Only bridges], centrepieces at most |
| Square-on side view on review sheets for modular walls | Mine, from the user's complaint | [Unsure] |
| Measure and grade each asset in Studio; pale paint needs less lift | Mine | [All assets] |
| Apply the 180° turn to imported glbs | Mine | [All assets] |
| Allow for terrain about 1.9 above the height map | Mine, measured at this spot only | [Unsure] on whether it's the same everywhere |
| Blocking walls need colliders well above the art; 15 above held here | Mine | [All assets] that must block |
| Land changes need the user's approval, and it can be no | Brief; user, "Leave it" | [All assets] |

## 6. Still open

**Status:** in Studio at `Workspace.Land1.StoneBridge`, with the graded sheets. **Not approved yet:** the user hasn't commented on `art/kit/bridge/compare_studio.jpg`. The look was approved in stages in Blender: rows and far read ("much better"), Sandstone, crisp. The place isn't saved and nothing is committed.

**Not decided by the user**
- The river crossing: the bridge runs only about 23° off the river's line, so nearly all of it sits over water. Changing it means changing the spec.
- Shaded side going blue, which is the land's lighting. The cottage has the same issue.
- Deck moss looking a bit like stickers up close.
- Players can't jump off the bridge. Lowering the walls would leave an invisible ledge above the stone.
- The waterline sitting about 2 studs above the water.
- Log bridge: not started, and the grey-box `BridgeLog` is still there.
- Two sheets against the fence's one-sheet template, which I flagged and they didn't answer.
- Whether the edge highlights fit. The bridge uses the rhythm from art-style rule 5, while memory `highlights-strategic` says buildings get few planned highlights, never a random rhythm on every edge. That memory isn't from this session, and the user hasn't judged the bridge against it.

**Known issue the user chose to leave:** the notch in the bank beside the far post. The ramp corner hangs over a hole, and a test character walking diagonally off the road fell to about y 9.7 and was still stuck when that test ended. I didn't check whether it could climb out.

**Unverified**
- Whether Roblox keeps the crisp grain up close. I judged the Studio captures overall, not the grain itself.
- Runtime performance, with 14,171 triangles at RenderFidelity Precise.
- Parapets: jumps were tested only at mid-span with `WALL_UP = 15`.
- Parapets and wings: walking was blocked at s = 12, 40, 70, 100 and 127 and at all four wings, at `WALL_UP = 9`. Taller walls can't weaken this, but it wasn't rerun.
- Walking and walls were tested before the colour grade, which changed neither the mesh nor the colliders.
- Under the arches: only the near arch was walked.
- The warm stone beside the slate rock kit, not seen together in Studio.
