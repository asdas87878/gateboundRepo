# Look direction for the Lands (2026-11-03)

The user's call after the Breath of the Wild study: take BotW's lighting and colour sense only, not how its pieces are
built (it looks dated). The end look stays close to the GPT-6.2 reference (clean low-poly, teal pines, olive-green
ground, grey stone ruins, red banners), made more striking with the best low-poly methods. Bright sun with darkish
shadows is the core.

## Measured references (frames in `research/`, gitignored; only numbers here)

`tools/art/frame_study.py stats` on daytime gameplay frames:

| | Breath of the Wild, fields (26 frames) | GPT-6.2 game (17 frames) | Target for the Vale |
|---|---|---|---|
| Sunlit grass | `#a9cb62` (L 77, very saturated lime) | `#81925f` (L 58, olive-lime) | L ~62-66, a -16, b ~30 |
| Shaded grass | `#586e40` (L 44) | `#3c4f35` (L 31) | L ~30-34: dark, a little teal |
| Sky (middle value) | `#76a4c4` (strong blue) | `#9fb7b6` (teal-grey) | between: `#8fb4c4` |
| Ground band colour strength | 36-41 | 24-25 | ~28-32 |
| Distance | strong blue haze, layered mountains | blue-grey mountains, light haze | blue-grey layers, haze from ~150 studs |

Second round: low-poly games with modern lighting, the "best methods" end of low poly.

| | Lonely Mountains: Downhill (26 frames) | Valheim, meadows (7 frames) |
|---|---|---|
| Sunlit grass | `#a1b17e` (L 70) | `#90ab5a` (L 66) |
| Shaded grass | `#5d734e` (L 46: shadows lifted) | `#3a5932` (L 34) |
| Colour strength, lower frame | 16 (pastel) | 37-41 |
| Rock | pale lavender greys (`#898499`, `#a59fa9`, `#c1b9c0`) with violet shadows (`#4e4b60`) | - |
| What to take | flat facets shaded by shape, lavender rock, flower clusters as the only strong colour | backlit haze, sunlit grass tips |

GPT-6.2 sits between Lonely Mountains (pastel, lifted shadows) and BotW (saturated, bright). We take GPT-6.2's
numbers and Lonely Mountains' lavender rock. The Roblox RPG footage we looked at (Vesteria) was mostly night scenes
and menus, so it gave no numbers.

## What the Vale passes settled (v01-v06 and `final/`, `art/lands/land1/beauty/`; `progress.jpg` shows the arc)

Measured on the seven final views:

| Measure | Pass 2 | Final | GPT-6.2 |
|---|---|---|---|
| Sunlit grass | `#849c5a`, L 61, chroma 37 | `#7d9365`, L 58, chroma 27 | `#81925f`, L 58, chroma 29 |
| Shaded grass | L 26 | `#293e22`, L 24 | `#3c4f35`, L 31 |

Sunlit grass is now on target. Shadows stay a step darker than GPT-6.2, which is the bright-sun, dark-shadow look.

What the passes settled:

- **Side light, not backlight.** Looking into the sun (v03) made every view milky and flat. The sun now comes from the
  east, 28 degrees up, warm (`#ffedcc`). It is about 90 degrees to most views, so forms and long shadows read.
- **Ground saturation x0.75.** Pass 2 measured our sunlit grass at colour strength 37 against the target's 29.
- **Mountains:**
  - The ring of mountains is ridged noise (crests, saddles, gullies).
  - Pine forest climbs to a wandering tree line (~140 studs), on darker, cooler slope grass.
  - Lavender-grey rock shows only on steep faces, light on crests and dark in gullies. No stripes.
- **Sky:**
  - Noise cumulus in perspective: a slab marched in slices gives flat dark bases and lit tops.
  - The cumulus stays in a band up to ~45 degrees; overhead it smears.
  - Faint cirrus above.
- **Haze** curve power 1.5: the middle distance stays clear and the far ranges fade out.
- **Masonry:** towers and walls are laid in stone courses with staggered joints, one shade per block, with red banners.
  This is what made the castle read like the reference.
- **Farmland:** strip fields around the mill and along the river, with hedgerows. They give the vistas pattern and
  scale.
- **Framing:** hero views get a foreground (a dark pine or rock at the frame's edge).
- **Cameras** are level with a lens shift, so towers don't lean. In game the player camera is roughly level anyway.
- **Fill light** (`Light.Fill`, after the walk views): a shadowless, slightly green-neutral fill (1.0) with lower sky
  ambient (0.65). Blender's sky light is blocked by every canopy, so forests rendered black. Roblox's OutdoorAmbient
  fills shadows everywhere, canopy or not, so the fill is the honest stand-in. Open-field shadows stay dark.
- **Player level first:** every change is now judged from the walk views too (`docs/style/ground.md`). Up close, the
  first beauty pass was a blur with dark specks.

To carry into Roblox (not done yet):
- **Sky:** cut the painted sky (`sky_paint.paint`) into the six skybox faces.
- **Fields:** Terrain painted with crop-coloured materials, or flat MeshParts with vertex colours.
- **Masonry:** meshes as built. Triangle counts: wall tower 642, wall run 612, keep 6,878 (the landmark; the one to
  split for LOD).
- **Floating island:** one mesh, no collision.

## Rules

- **Light:** a strong warm sun (Blender 3.8, `#fff0d6`, 38 degrees up, side-on to the main views) and low, slightly
  cool fill, so shadows stay dark (about half the brightness of sunlit ground). Crisp shadow edges.
- **Colour:**
  - Grass is olive-lime in sun and dark teal-olive in shade.
  - Pines are teal (`#5a8a78`, undersides `#355b50`). Broadleaf canopies go from olive (`#93b05a`) on top to dark green
    (`#2a4a38`) below.
  - Rocks are cool grey with moss caps.
  - Stone is light warm grey, with red banners and blue slate roofs as accents.
- **Grass:** the mixed method in [grass.md](grass.md).
- **Sky:** painted, teal-blue, with soft cumulus near the horizon and wisps above. No hard-edged "bubble" clouds.
- **Distance:** BotW's three layers. Detail up close; fog in the middle, including mist that pools in low ground; far
  mountains as simple hazed silhouettes, snowy at the top. Detail thins with distance.
- **Composition** (BotW's field design): big landmarks visible from far away (the keep, the Gate's beam); medium shapes
  that hide and then reveal; small pieces for pacing. Points of interest spread unevenly, ranked by how visible and
  important they are.
- **Roblox mapping** (to check in Studio):

  | Look element | Roblox |
  |---|---|
  | Lighting | Future (or ShadowMap on low settings); Brightness ~3; warm sun via the Sky's sun colour; `OutdoorAmbient` low and slightly cool so shadows stay dark; `EnvironmentDiffuseScale` ~0.3 |
  | Haze | `Atmosphere` blue-grey (Density ~0.3, Haze ~1) |
  | Post | Bloom subtle; `ColorCorrection` Contrast +0.1, Saturation +0.05 |
  | Ground | Terrain, with `Grass` (decoration grass on) and `Ground`/`Mud` for paths, `Rock`/`Slate` for cliffs. `MaterialColors` set to the palette above |
  | Props | Our meshes, vertex colours |
- **Low-poly craft** (community tips):
  - few colours per object;
  - flat facets on hard things, smooth shading on soft things (canopies, grass, rock caps);
  - no noisy texture detail;
  - colour correction and a good skybox matter more than polygons;
  - use contrast to steer the eye to focal points.
