# Flower beds (first pass, 2026-11-08; in Studio)

**The user's direction:** a combination of solid sphere-like elements and decal elements, and painted flower images on planes for the
petals ("a 3D decal type of an image, a plane, and then painterly type around it"). They may bring references and assets for the
next pass. This first try is mine.

## How a bed is made
Each piece is a Model of two MeshParts:
- **Mound:** solid soft blobs (squashed half-ellipsoids, sunk into the ground), painted with overlapping leaves. The texture repeats
  round each blob, so leaves keep their size. It runs dark at the foot to lit on top.
- **Cards:** double-sided planes with painted images, from a 4 x 4 atlas:
  - cells 0-7 are leaf fans growing from the bottom middle; they stand on the mound's sides by their foot, leaning out, to break
    the outline;
  - cells 8-15 are flower clusters over a few leaves; they sit on the mound's tops, facing up and a little outward.
- **Lighting rules from the foliage test** (`foliage-method.md`): normals lean 65% toward straight up, there's no cast shadow, and
  the cards use AlphaMode Transparency with colour spread under the clear parts (no dark fringes).
- **Painted, not photographed:** every leaf and petal is a shape in two or three tones, lit from above, drawn at 4x and shrunk.
  - Daisies: white petals, shaded on the lower side, a yellow eye.
  - Pink blossoms: five petals with a darker eye.
  - Lilac: small four-petal florets.
  - Yellow buttercups.

## Pieces (ServerStorage.FlowerKit, White / Pink / Mixed: the same meshes, another card texture)
| Piece | Fits | Pivot |
|---|---|---|
| BedRound | a ring of 8 edging Curve6 (radius 4.7) | the ring's centre |
| BedLong | between two straight edging runs 5 apart, 8 long | the start of its centre line, running +X |
| BedEnd | a long bed's rounded end (two edging Corners) | the end's centre; the half disc is on its +X side |
| Clump, ClumpWide | loose, to dot round rocks, trees and paths | the centre |

- Triangles: BedRound 3,880, BedLong 1,800, BedEnd 770, Clump 980, ClumpWide 1,250.
- Examples are in the cobble shelf's example beds (`Workspace.CobbleShelf.Example.Beds`) and on `Workspace.FlowerShelf`.

## Build
- `blender --background --python tools/blender/flower_kit.py -- build` (`art/kit/flowers`: blend, `FlowerKit.glb`, `kit.json`)
- `python tools/art/paint_flower_kit.py` (about 6 s): `FlowerMound_Color.png`, `FlowerCards_White/Pink/Mixed.png`
- `python tools/art/upload_flower_kit.py --luau art/kit/flowers/flower_kit_filled.luau`, then run that in Studio
  (`tools/studio/flower_kit.luau` is the template)

**Trap:** a Model with a PrimaryPart pivots on that part's pivot and ignores WorldPivot. Give the PrimaryPart a PivotOffset instead.

## Not done yet
- Judged only in one Studio capture.
- Performance of stacked transparent cards is unmeasured.
- The mound texture is generic leaves.
- No taller flowers or variety of height yet.
- The colours aren't graded under the hub's lighting.
