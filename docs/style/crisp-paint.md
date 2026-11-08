# Crisp paint (from the stone bridge, 2026-11-06)

Makes a texture hold up close, with firm brush edges and a slight painted grain. Tool: `tools/art/crisp_paint.py`. It's a painted look, not pixel art: no fixed palette or pixel grid.

## On a finished sheet
Same layout, so it fits the existing model. Colours come from the sheet; no palette is needed.
```bash
python tools/art/crisp_paint.py art/kit/props/Props_Color.png art/kit/props/Props_Color_Crisp.png --grain x
```
- `--look crisp` (default) or `--look soft`. Soft keeps the grain but stays gentle: fainter shapes, paler marks, almost no sharpen, and each island keeps its average colour, so nothing gets darker.
- `--shapes`, `--marks`, `--dark`, `--sharpen`: override one ingredient of the look (1 = crisp's amount). Shapes and marks make the grain; dark and sharpen make it hard and heavy.
- `--grain x`: wood painted with its grain along x (fence, props). `--grain none`: stone, marks in any direction.
- `--strength 1.0`: scales all of it. Try 0.6 for less, 1.4 for more.
- `--seed 5`: another arrangement.

Rerun after rebuilding a kit: rebuilding replaces the input sheet. The pass works island by island, so nothing crosses a seam. If a sheet has no flat background colour, it's treated as one big island and marks can cross seams.

Check it, with back faces hidden as in Roblox. Keep the out folder separate from the sheets, because renders are named after them:
```bash
blender --background --python tools/blender/crisp_preview.py -- art/kit/props <out folder> art/kit/props/Props_Color.png art/kit/props/Props_Color_Crisp.png --only BarrelA,CrateA,SignPost --spread 8
```

## Inside a painter
`from crisp_paint import crisp_pass, brushed_wash, chisel_marks, hewn_plane, sharpen`. `bridge_kit.py` paints its stone this way (`python tools/art/bridge_kit.py art/kit/bridge Sandstone soft` for its soft look). Paint at double size (`scale=2`), then shrink with Lanczos.

## What makes the look
1. **Hard-edged brush shapes** (`brushed_mask`): an ellipse roughened with noise, cut hard, then blurred about 0.4 sheet pixels. Most of the grain comes from this.
2. **Chisel marks** (`chisel_marks`): clusters of short strokes stamped pixel by pixel, close in colour to the surface.
3. **Sharpen** (`sharpen`): amount 0.9 gives each painted edge a thin light and dark side.
4. **Enough pixels**: the bridge's close-up parts are 54 texels a stud, the fence is 50. Below about 30 it goes soft, whatever the paint.

Keep highlights and glows soft on top (`art-style.md` rule 3). Keep the shapes close in colour, or it turns to camouflage.

## Not checked yet
Tested in Blender only, on the bridge and a crate from a copy of the props sheet. Roblox filters and compresses textures its own way, so judge the grain in Studio.
