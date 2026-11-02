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
- Game design draft: `docs/game-design.md` (fun-first rules, Lands/Gates, loot, pets, hidden skills, decisions).
- The look: `docs/look-rules.md` (the numbers learned by copying the reference screenshot: camera, scale, light, sky,
  haze, palette, terrain, scatter, models, Roblox mapping). How the copy passes work: `docs/look-passes.md`
  (`python tools/look_pass.py art/look/ashen_ref/scene.json <name> --note "..."`, ~20 s a pass; spec in
  `art/look/ashen_ref/scene.json`, pixel-anchored placement; tools in `tools/art/` and `tools/blender/look_match.py`).
  The reference camera is level with a lens shift (verticals straight, horizon at row 262); Roblox can't shift.
- Models: `tools/blender/kit.py` (the generators: pines, boulders, grass, flowers, bushes, towers, arches, ruins,
  banners, poles, stele, mountains, hero/golem stand-ins; flat or smooth shading, per-face/per-corner vertex colours, no
  textures, studs). `tools/blender/starter_kit.py -- --render --export` builds every piece with the look's palette,
  renders `art/kit/renders/lineup.png` and writes `art/kit/glb/<Name>.glb` + triangle counts.
