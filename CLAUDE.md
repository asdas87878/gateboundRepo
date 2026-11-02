# rpg-game (working title)

A Roblox RPG: the kind of game the user played on Roblox as a kid, made much better. Target look: a low-poly,
flat-shaded fantasy world (pine forests, stone ruins, red banners, blue haze), from an AI-made reference the user shared.
Claude builds the models and writes most of the code. The user is strong on game design and Studio, and their Luau is basic.
Plan for co-op from the start: server-authoritative, per-player state.

- Toolchain as in the FPS project (`C:\Users\blast\New folder`): `rokit.toml`, `rojo serve`, `stylua src`, `selene src`.
- `src/server` -> ServerScriptService.Server (`Main` loads `Services/`), `src/client` -> StarterPlayerScripts.Client
  (`Main` loads `Controllers/`), `src/shared` -> ReplicatedStorage.Shared. Modules have optional `Init` (no yield) / `Start`.
- Game design draft: `docs/game-design.md` (fun-first rules, Lands/Gates, loot, pets, hidden skills). Look rules: `docs/style-notes.md`. Models: `tools/blender/starter_kit.py` (Blender 5.2 headless,
  `-- --render --export`): props built in code, flat shading, per-face vertex colours (no textures), studs as units;
  renders in `art/kit/renders`, one glb per prop in `art/kit/glb`, source `art/kit/StarterKit.blend`.
