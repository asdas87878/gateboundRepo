# rpg-game (working title)

A Roblox RPG: the kind of game the user played on Roblox as a kid, made much better. Target look: a low-poly,
flat-shaded fantasy world (pine forests, stone ruins, red banners, blue haze), from an AI-made reference the user shared.
Claude builds the models and writes most of the code. The user is strong on game design and Studio, and their Luau is basic.
Plan for co-op from the start: server-authoritative, per-player state.

- Toolchain as in the FPS project (`C:\Users\blast\New folder`): `rokit.toml`, `rojo serve`, `stylua src`, `selene src`.
- `src/server` -> ServerScriptService.Server (`Main` loads `Services/`), `src/client` -> StarterPlayerScripts.Client
  (`Main` loads `Controllers/`), `src/shared` -> ReplicatedStorage.Shared. Modules have optional `Init` (no yield) / `Start`.
- Lands: `docs/lands/` (Gate 1 = `land1-verdant-vale.md`; maps from `art/lands/<land>/map.json` by `tools/art/land_map.py`).
  Trees: keep the solid kit pines; the card-branch trees (`card_trees.py`) are parked by the user's choice.
- Game design draft: `docs/game-design.md` (fun-first rules, Lands/Gates, loot, pets, hidden skills, decisions; section 14 is the current direction and overrides older sections).
- The hub, fresh start (2026-11-08, blockout Proposed): a floating saucer after the user's two references, player plots on bridges around it, land far below, giant tree silhouette; `docs/lands/hub.md`, `tools/blender/hub_blockout.py -- art/hub` (`art/hub/blockout/sheet.jpg`).
  Bigger (1,800-stud deck) with a terraced town, in the user's new base place (unpublished "Place1", Rojo-synced): `tools/art/hub_layout.py`
  (plan `art/hub/plan.png`, filled `art/hub/studio/build_hub.luau`; layers in `Workspace.Hub`, rebuilt only when on in `RUN`); every kit
  installed with no new uploads, shelves at x 30,000 (`tools/studio/kit_shelf.luau`); the hub's asset to-do list is in hub.md.
- Cobble kit (2026-11-08, in the base place): Chisel edging in Pebble's blue-grey (ChiselSlate, plus moss), one-row border stones
  (SettCool), the paving MaterialVariant HubPaving; `tools/blender/cobble_kit.py`, `tools/art/paint_cobble_kit.py`,
  `tools/art/upload_cobble_kit.py`, `tools/studio/cobble_kit.luau`. Plans for the Part-path border generator, the walls and connecting
  pieces: `docs/style/cobble-kit.md`.
- Flower beds (2026-11-08, first pass, in the base place): a painted leaf mound plus painted flower and leaf cards, White/Pink/Mixed;
  `tools/blender/flower_kit.py`, `tools/art/paint_flower_kit.py`, `tools/art/upload_flower_kit.py`, `tools/studio/flower_kit.luau`,
  `docs/style/flower-beds.md`.
- The Haven (older composition, kept for reference; home hub with player plots, Lands as floating islands; composition Proposed): `docs/lands/haven.md`, `art/haven/layout.json` -> `tools/blender/haven_blockout.py -- art/haven` (views) + `tools/art/haven_plan.py` (plan, sheet); ChatGPT prompts in `art/haven/prompts.md`. The 30 Lands in six themes: `docs/lands/lands-list.md`.
- **Before making or repainting any asset, read `docs/style/art-style.md`:** the one art standard, merged from every asset session, with Studio grades, collision rules and known traps. Add what the user teaches you to it.
- The user blocks out environments by hand; Claude makes assets. Rock pack (50 rocks, moss and clean, shelf at `Workspace.RockPack`): `docs/style/rock-pack.md`. A blockout folder becomes terrain with `tools/studio/blockout_to_terrain.luau` (only its own area; the blocks go to `ServerStorage.Blockouts`): `docs/style/terrain-method.md`. Giant stone sword, painted with real brush marks after the user's concept (awaiting their verdict): `docs/style/stone-sword.md`.
- Matching a painted reference in Blender and Studio (private study, `research/pink_cottage/README.md`): `tools/blender/pink_cottage.py`
  (islands with paint coordinates per face, packing, Cycles occlusion bake, glb export), `tools/art/paint_pink_cottage.py` (a painter per
  material: fish-scale slates, coursed stone, plaster, planks, grass), `tools/art/ref_overlay.py` (render vs reference line-up),
  `tools/studio/place_pink_cottage.luau` (placement, lighting, per-sheet grade). Roblox lighting research and what Studio measured:
  `docs/style/roblox-lighting.md`.
- The look: `docs/look-rules.md` (the numbers learned by copying the reference screenshot: camera, scale, light, sky,
  haze, palette, terrain, scatter, models, Roblox mapping). How the copy passes work: `docs/look-passes.md`
  (`python tools/look_pass.py art/look/ashen_ref/scene.json <name> --note "..."`, ~20 s a pass; spec in
  `art/look/ashen_ref/scene.json`, pixel-anchored placement; tools in `tools/art/` and `tools/blender/look_match.py`).
  The reference camera is level with a lens shift (verticals straight, horizon at row 262); Roblox can't shift.
- Models: `tools/blender/kit.py` (the generators: pines, boulders, grass, flowers, bushes, towers, arches, ruins,
  banners, poles, stele, mountains, hero/golem stand-ins; flat or smooth shading, per-face/per-corner vertex colours, no
  textures, studs). `tools/blender/starter_kit.py -- --render --export` builds every piece with the look's palette,
  renders `art/kit/renders/lineup.png` and writes `art/kit/glb/<Name>.glb` + triangle counts.
- Beauty pass (the finished look of a Land, rendered): `tools/blender/vale_beauty.py -- art/lands/land1/map.json <out>
  [--views a,b] [--quick] [--grass <style>]`, settings in map.json `Beauty`, kit `tools/blender/kit_vale.py` (broadleaves,
  masonry `coursed_ring`/`coursed_block`, banners, keep, bridge, mill, floating island), grass `tools/blender/grass_kit.py`
  + `vale_grass_ab.sh`, sky `tools/art/sky_paint.py` (noise cloud `Layers` in perspective; `tools/art/noise2d.py`),
  post `tools/art/look_post.py <view dir> <map.json> --key Beauty`; full-quality hero views + sheet: `bash tools/blender/vale_final.sh`
  (`art/lands/land1/beauty/final/`). Rules: `docs/style/look-direction.md`,
  `docs/style/grass.md`, `docs/style/ground.md` (the player-level rules). Judge every look change from the **walk views**
  (`walk_*` in `Beauty.Views`: a 5.2-stud stand-in, over-the-shoulder camera at FieldOfView 70), not only the vistas.
  Ground detail textures: `tools/art/ground_textures.py`; trails are ribbon meshes (`Beauty.Trails`); tree styles:
  `tools/blender/tree_compare.py` (faceted canopies chosen). Harsh comparison with good games and the ranked fixes:
  `docs/style/landscape-review.md`, measured by `tools/art/scene_metrics.py` and `tools/art/walk_review.py` (reference frames stay in `research/`).
  Grass must match the ground's colour: check with `tools/art/grass_match.py` (grass on vs `--grass none`, within
  ±3 L); grass casts no shadows and is lit with a straight-up normal on both faces (`grass_kit.py`). Reference footage is measured by `tools/art/frame_study.py` (clips and frames stay in the
  gitignored `research/`, study only).
- Stylized look (target since 2026-11-04, private reference in `research/stylized_lesson`): rock kit `tools/blender/rock_kit.py -- build|render`
  + `tools/art/paint_rock_kit.py` (9 modular pieces, one shared colour texture painted per texel in 3D, numbers at the top
  of the painter; `art/kit/rocks`). Not in Studio yet.
