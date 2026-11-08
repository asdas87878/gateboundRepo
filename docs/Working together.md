# Working together

How the user and Claude work on Gatebound, and what's been learned. Claude reads this at the start of every session. The user can edit
it like any note: anything changed here is how Claude works from then on.

## Who does what
- **The user:** strong in game design, Studio and assets; basic Luau. They block out environments and scenes by hand in Studio,
  because it comes out more curated.
- **Claude:** writes the code, makes the models and textures, and enhances what the user builds.
- **Assets arrive ready to place:** named folders, a shelf to copy from, pivots at the foot (or the start of a run). Never re-place
  or regenerate the user's hand-built layout unasked.
- **Design talks:** pitch ideas in plain, concrete terms, and check they're understood before building on them. Voice-mode brain
  dumps go in the [Inbox](Inbox.md).

## How to work
- **Speed matters.** Do the thing and report briefly.
  - Take a screenshot only when the result is visual and being judged, or the user asks. Check non-visual work with numbers.
  - Skip Blender renders when the user says so: put things straight into Studio.
- **Parallel sessions:** run independent work in its own session, but only one session drives Studio at a time.
- **Look passes:** before long reference-matching rework passes, tell the user first. They may want to raise the effort setting.
- **Never use computer use on the user's PC.** If access is missing, ask for a connector or an API.
- **Image generation costs credits:** ask before spending any.
- **Roblox uploads are permanent:** upload only what's chosen. The key comes from the environment and is never printed.
- **Git:** commit or push only when asked.
- **Reference studies:** footage and screenshots stay in the gitignored `research/`, and are for style and method only. Never copy
  a reference's layout or assets.

## Art lessons (the full rules are in the [art style](style/art-style.md))
- **The look:** anime, Studio Ghibli, hand-painted. Judge in Studio, at player height, up close and far, from two sides including
  the shaded one.
- **Structure before paint.** Check the shape in clay first. Keep it cartoonish, not rigid: tapers, slight leans, gentle waviness,
  orderly sizes.
- **Paint with shapes, not filtered noise:** the user dislikes splotches.
  - Moss: two or three flat tones in big groups.
  - Highlights: pale cream, placed where the light catches, never a line round every edge.
- **Read a reference's source colours before copying what its render shows.** Shadow and sun aren't paint.
- **Meshes:** don't decimate; get the low-poly look from the smoothing angle. Use weighted normals by default.
- **The sky:** keep the Stylized Skybox (8755940451).

## Studio traps
- **Captures:** send one screen capture per message (two together cost minutes). After moving the camera far, wait about 7 seconds
  for terrain to load. Blank or dark captures, or 15 fps, mean Studio's window is covered.
- **The glb importer** turns each mesh 180 degrees about its centre: place with `CFrame.new(centre) * CFrame.Angles(0, math.pi, 0)`.
- **Model pivots:** a Model with a PrimaryPart pivots on that part and ignores WorldPivot. Set the PrimaryPart's PivotOffset.
- **Terrain** sits about 2 studs above the written height. Past about 1,024 studs it doesn't load on the client.
- **If the Studio connector fails,** `tools/studio/studio_mcp.py` reaches Studio directly.
- **Placement scripts:** don't rerun one over hand-placed work.

## The PC
- **The machine:** i5-9400F, GTX 1660 Super, 16 GB. A realistic low-end target for performance.
- **The drives:** C: is a small SSD that's nearly full. D: is a failing HDD, so keep the project off D: and backed up.
