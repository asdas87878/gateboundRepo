# Stone sword (2026-11-06, awaiting the user's verdict)

One giant moss-covered stone sword, made to match the user's concept painting (`art/kit/sword/reference/reference.png`): a field of huge swords stuck in green hills. The first asset painted with real brush marks rather than the fence's strip paint, so it's a candidate look, not yet part of `art-style.md`.

**In the place:** drag copies from `ServerStorage.SwordKit.StoneSword`; its pivot is on the ground at the blade's middle, so tilt it after placing. `Workspace.SwordPack` (a Folder at x 30000, z 950) shows one upright and one leaning. Rerunning the placement replaces those two, not copies elsewhere.

About 187 studs tall at scale 1 (blade 20 wide, 116 above ground, 12 buried). Six MeshParts and 3,573 triangles, five 1024 sheets at 16-20 pixels a stud; every copy shares them. Meshes have no collision: invisible, locked `Collider` boxes stand in, not yet walked against.

## How it's made
```
blender --background --python tools/blender/stone_sword.py -- build     (geometry, UVs, bake.npz, layout.json; seeded)
python tools/art/paint_sword.py                                         (about 50 s, the five sheets)
blender --background --python tools/blender/stone_sword.py -- render <tag> [views]     (art/kit/sword/views; tools/art/sword_compare.py <tag> puts them beside the reference)
blender --background --python tools/blender/stone_sword.py -- export
python tools/art/upload_sword.py --luau <out.luau>                      (only what changed), then run <out.luau> in Studio's edit mode
```
- **Shape:** a blade with a ridge down each side, so one big face takes light and the other shade, which is the reference's strongest read. A chunky guard with a V tongue, banded grip, spade pommel. Chips only on edges: chips on the big faces came out as shards, so wear there is painted.
- **UVs:** each face is projected flat onto a canvas (front, back, sides, top, bottom; a wrap for the grip), so strokes run straight along the blade. The blade's canvases span three parts, so paint crosses part joins without a seam.
- **Paint, in order:** one tone per flat face, broad patches, blocks of paint, streaks, dry-brush, runes, olive glaze, moss, cracks, ink, soft pale edges. Each stroke stays on the flat face it started on and frays at its ends. Colours were measured from the reference (`STONE`, `MOSS_*`).
- **Moss (the user's correction, 2026-11-06: "more intentional", two or three tones, grouped, not heavy on highlights):** one flat mid-green mass with short drips; a darker olive group along its lower edge and in a pool or two; a few patches barely lighter; a few small clusters of dark ticks. No grain and no separate highlight layer. Only the edges carry the brushwork: near them the moss skips along the bristles and stone shows through, with a few dry marks past the edge, all in the same colours. Tried and rejected on the way: leaf-like dabs (ivy), many small light and dark marks (noise), clean flat shapes with no brushed edge (camouflage).
- **Ink outline:** `Outline` is every part pushed out 0.42 studs and turned inside out, in dark Neon with no shadow. Faces a chip made are left out, so the line has small gaps at chips.
- **Grade:** Studio's sky adds blue, so the sheets are multiplied by `GRADE` (0.97, 0.99, 0.85). Measured before grading: lit stone 175, 188, 179 against the reference's 165, 185, 152; moss 108, 143, 89 against 114, 135, 70.

## Mistakes worth not repeating
- `bmesh.ops.triangulate` uses a face's stored normal. A new concave ngon has none until `normal_update()`, and fills with overlapping, wrong-facing triangles: holes in Roblox, seen here as black wedges. `prism` now checks for it.
- Blender's default cube, camera and light sit in a child collection and got exported: clear `bpy.data.objects`, not just the scene's own.
- Blender's shadows ignore backface culling, so an outline shell shades the whole object unless `visible_shadow` is off. Set `CastShadow` off in Studio too.

## Checked in Studio (2026-11-06)
Seen on the lit side from a distance and at player height, and on the shaded side close up before the final grade and the moss rework. Parts line up, sizes match, no holes in the guard after the fix.
The new moss was checked on the lit side, at a distance and at player height, just before its last small colour trim (`MOSS_*`); the trimmed sheets are uploaded and placed, but Studio had stopped drawing, so they haven't been seen or measured there.

## Not done
- Only one design: the reference has variety (hilts, damage, depth in the ground). Copies differ only by tilt and size.
- No base: the reference has dirt, small stones and grass at the foot. Terrain and rocks cover this for now.
- Not walked against. Performance not measured with many copies, and there's no simplified far version.
- The shaded side goes dark and blue under this place's lighting, as other assets do: a lighting-pass matter.
