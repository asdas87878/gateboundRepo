# Grass (2026-11-03)

How grass is made in this game, from community practice and a side-by-side test. Tools: `tools/blender/grass_kit.py`
(building blocks), `tools/blender/grass_bench.py -- <out>` (the test scene), results in `art/style/grass/bench1/sheet.jpg`.

## What the community says

- **Point the blade normals straight up**, so grass shades like the ground under it instead of flickering light and
  dark blade by blade. A softer variant blends from up-normals at the root to the blade's own normals at the tip.
  ([Polycount](https://polycount.com/discussion/comment/2725667), [Unreal forum](https://forums.unrealengine.com/t/grass-lighting/152158/2))
- **Root colour = the ground colour**, then a gradient to lighter tips (fake occlusion at the root). The grass then
  melts into the terrain instead of sitting on it. ([Unity forum](https://discussions.unity.com/t/grass-568179/568179))
- **Clumps, not single blades**, with colour variation at two scales (patches and finer bands) and lighter tip
  colours. ([Godot stylised grass shader](https://forum.godotengine.org/t/free-stylized-3d-grass-shader-cc0/134880))
- **Dense near the camera, thinning with distance**; per-blade bend by height (the
  [Ghost of Tsushima talk](https://gdcvault.com/play/1027214/Advanced-Graphics-Summit-Procedural-Grass) and community
  re-implementations such as [GodotGrass](https://github.com/2Retr0/GodotGrass)).
- **Don't over-saturate grass**; that's the most common low-poly mistake.
  ([Game Developer](https://www.gamedeveloper.com/design/how-to-make-low-poly-look-good))
- **Roblox:** its built-in terrain grass is the cheapest by far, because it's a shader. Mesh grass is fine for accents
  if collisions are off and the meshes are reused (instanced). It costs more at scale, so test with the MicroProfiler.
  ([DevForum: alternatives to grass](https://devforum.roblox.com/t/alternatives-to-grass/423304),
  [grass with parts](https://devforum.roblox.com/t/grass-with-parts-its-it-reliable/189487))

## The test (same meadow, light and camera)

| Method | Verdict |
|---|---|
| none (ground only) | flat, reads as a lawn |
| clumps with their own colours (the first Vale try) | too dark and heavy: blades don't match the ground |
| **matched clumps** (ground colour, root-to-tip gradient, up-normals) | natural, light, the ground's patches show through |
| cards (crossed textured planes) | realistic but noisy, needs alpha cut-outs |
| **carpet** (dense short blades) | calm, fine; looks like Roblox's terrain grass |
| chunky low-poly triangles | stylised but messy facets |
| **mixed: carpet + taller drifts + flowers** | the best: calm base, clump variety where it matters, colour dots |

On the bench, the mixed method looked best.

## In the Vale (pass 4, `art/style/grass/vale_ab/sheet.jpg`)

The bench's winner didn't survive the real Land. Seen from a player's height, the carpet fills the whole foreground and
the meadow reads as a wheat field. `bash tools/blender/vale_grass_ab.sh <out> <view> <style>...` renders one view per
style (styles in map.json `Beauty.GrassStyles`):

| Style | Verdict |
|---|---|
| mixed (tall carpet + drifts) | a wheat field; hides the road and the ground's colour patches |
| short (short carpet + tufts) | lush but dark and heavy, still hides the road |
| **tufts** (no carpet: darker tufts scattered thinly, denser along path edges and in patches, many flowers) | the GPT-6.2 look: the ground's colours, the road and the flowers all read |

Tufts won that round: about 1.1 studs tall, 14 blades, tinted darker than the ground (`b4c89a`), flowers at 0.8.

## At a player's feet (walk views, `art/lands/land1/beauty/w0N/sheet.jpg`)

The user's verdict on tufts, seen at player level: dark grass coming out of a light base is fine in small amounts, but
most grass should match the base colour or sit just off it, by varying amounts. Tufts had also crowded the trail edges,
where grass shouldn't be. So the Vale now uses the **matched** style:
- A carpet of short blades (about 0.6 studs) in the ground's own colour: root ×1.0 to tip ×1.08.
- Taller clumps in patches and at the feet of things.
- Each clump is up to 5% lighter or darker and 4% warmer or cooler (`Vary: {"Light": 0.05, "Hue": 0.04}`). The
  variation averages out to exactly the ground's colour.
- No dark accent tufts (`Accent` 0).

Placement is in ground.md: nothing on trails, a worn verge, shelter rings.

## Same colour as the ground (2026-11-03)

The user, after the walk views: the grass still needed to stop being dark, be the same colour as the ground's grass,
and have no shadows on it. There were three causes:
1. **Half of every blade was lit from below.** Blade normals pointed straight up so the grass would shade like the
   ground, but Blender flips the normal of a face seen from behind, so that side pointed down and got no sun. Fix: the
   material's shading normal is a fixed straight-up vector, the same on both faces (`matched_material`).
2. **Grass shaded itself.** Each blade cast a shadow on the ones behind it and on the ground. Fix: every scatter layer
   is its own object with shadow casting off (`scatter`), as in Roblox (decoration grass casts none; our tufts have
   `CastShadow` off). Grass still receives the shadows the ground receives, under trees, so it keeps the ground's
   colour there too.
3. **The colour settings leaned dark:** darker roots, a cool tint per clump, and dark accent tufts. Fix: the settings
   above.

Measured by `tools/art/grass_match.py`: the same views with and without grass, over the ground in front of the player.
Lightness (L, 0-100) change when grass is added:

| View | Before (w07) | After (w08) |
|---|---|---|
| Road | -14.2 | +0.7 |
| Meadow | -23.1 | -2.9 |
| Gate road | -7.1 | -1.7 |

Colour strength now changes by about 1 or less. Any new grass setting should keep this check within ±3 L.

| Layer | Blender preview | Roblox |
|---|---|---|
| Carpet where grass grows, not on trails | short matched blades | Terrain `Grass` with decoration grass on: it takes the material's colour, which is the "matches the base" look for free |
| Clumps in patches and at the feet of rocks, trees, walls | taller matched clumps, each a little cooler or warmer | MeshPart tufts, `Color` from the ground under them ± a few percent, `CanCollide`/`CanQuery`/`CanTouch` off, `CastShadow` off, only near the player |
| Flowers in patches (white, yellow, orange, a little blue) | flower meshes | small MeshParts, same settings |
| Crops on fields (wheat, leafy rows) | matched clumps in rows | MeshPart rows near the player; far off, the field colour alone |
| Pebbles by trails and water | small boulders | small MeshParts |
