# Look passes: copying a reference to learn a look

A pass rebuilds the reference screenshot in Blender, compares it with the original, and logs a score. Changes go into
one spec file, so every pass is reproducible. The results are in [look-rules.md](look-rules.md).

## Files

| Path | What |
|---|---|
| `art/look/ashen_ref/frame.png` | the reference game frame, cropped out of the YouTube screenshot (1336 x 752) |
| `art/look/ashen_ref/areas.json` | comparison boxes (sky, mountains, trees, towers, banner, grass, road, rocks, stele) and the HUD/character mask |
| `art/look/ashen_ref/scene.json` | the spec: camera, sky, light, terrain, roads, placements, forests, scatter, post, palette |
| `art/look/ashen_ref/passes/<name>/` | beauty.png, depth.png, final.png, sheet.jpg, side.jpg, stats.json, placements.json, spec.json |
| `art/look/ashen_ref/passes/log.md` | every pass: score, layout, what changed |
| `art/look/ashen_ref/progress.jpg` | reference and passes 2, 5, 10, 15, 21 |

## Tools

- `python tools/look_pass.py <spec> <name> [--post] [--note "..."]` runs one pass in about 20 s:
  - `tools/blender/look_match.py` builds and renders the scene (beauty + a depth pass).
  - `tools/art/look_post.py` adds haze from depth, bloom and the grade.
  - `tools/art/look_compare.py` scores it and writes the sheet.
  - `--post` reuses the render and only redoes the post (haze and grade tuning).
- `python tools/art/side_by_side.py <pass dir> [--stack] [--crop x0,y0,x1,y1]` puts the reference and a pass together.
- `python tools/art/pass_table.py <pass dir> ...` gives per-area L, a, b for several passes against the reference.
- `python tools/art/look_global.py <image> ...` gives brightness, contrast, chroma and detail per band (sky, middle,
  ground), outside the HUD.
- `python tools/art/colour_tool.py lab|nudge|chroma` converts sRGB hex to and from Lab and nudges palette colours.

## How placement works

The spec is written in reference pixels. An object's `Px` is where its base touches the ground in the screenshot. A
ray from the camera through that pixel is marched onto the terrain. `TopPx` is the row of its top, and the object is
scaled until its top lands there. `Depth` pins an object at a distance instead, and `Pad` levels the ground under it.
The gate stands in a plane facing the camera (`CentrePx`, `Depth`). Roads are pixel polylines with a width per point.
`placements.json` records every object in studs; that's where the scale table in the rules comes from.

## Scores

- **score**: the mean over the areas of |ΔL| + Δ(a,b) in CIELAB. 0 means the same colours.
- **layout**: the mean colour difference of both frames blurred, outside the mask, so it also counts shapes.

Pass 2 scored 22.3 (layout 19.2); pass 21 scored 5.8 (layout 10.5). Below about 6 the boxes are dominated by small
layout differences (a tuft or a shadow edge in a box), so judge by eye and the band numbers from there.

## Lessons about the method

- **Check the camera model first.** Straight verticals plus a high horizon meant a lens shift. Before switching
  (pass 5), every tower came out with the wrong proportions.
- **Look at the boxes, not just the numbers.** Two "grass" boxes were really road and shadow in the reference.
- **Test lighting as a small batch** (three directions in one go) instead of one change per pass.
