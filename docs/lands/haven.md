# The Haven (structure agreed 2026-11-06, composition Proposed)

The home of the game: a shared floating island where everyone lands, with a plot for each player around it. The Lands are floating islands visible in the sky from here. Nothing is in Studio yet.

Source: `art/haven/layout.json` (its Lands written by `python tools/art/haven_lands.py`, where the sky is composed). Renders: `blender --background --python tools/blender/haven_blockout.py -- art/haven` writes `art/haven/composition/<View>.png` (about a minute). Plan and review sheet: `python tools/art/haven_plan.py` (`plan.png`, `views_sheet.jpg`). ChatGPT prompts per view: [prompts](../../art/haven/prompts.md).

## The composition
An amphitheatre, built so every important spot has a view:
- **Middle:** the main island (360 across) with a raised plaza and The Climb, the endless tower (320 tall): the landmark you can see from everywhere.
- **North:** six arches on a curved promenade, one per theme, each on the straight line from the tower to its theme's first Land, so from the plaza the arch frames that Land. Land 1's arch glows; the others are dark until their theme opens.
- **Further north, in the sky:** 30 Lands (`docs/lands/lands-list.md`) in six columns of five, stacked above and below each other, 3,200 to 16,000 studs away. Each theme's rock has its own colour, so you can tell it from below, and its grass, sand or snow spills over the rim. Land 1 is big and close. Land 30, The Crown, hangs dead ahead at the top of the sky, so you can see the end from your first minute. Beating a boss wakes the next one.
- **South:** eight plot islands (170 across) in a crescent on bridges (185 long, 12 s). From any plot you look across your bridge at the tower with the Lands behind. Your plot's neighbours sit either side, so you see what other players have built.
- **Plaza's south side:** market stalls and a stream that runs to the rim and falls into the clouds.
- **Below:** a sea of clouds, with small islets scattered about.

## Views
| | Where | What it must show |
|---|---|---|
| A | Your plot | Your buildings framing the shot, the bridge, the tower, the Lands behind |
| B | The bridge | The bridge as a line leading up the tower |
| C | The plaza | Land 1's arch framing Land 1 |
| D | The promenade | The row of arches curving away |
| E | Plot edge | A neighbour who has built more than you |
| F | High up | The whole place, for a poster or the icon |
| G | Promenade, looking up | The sky of Lands, stacked up to Land 30 |

## Decided, and open
- Each plot: one 36-across spot for the main building and seven 28-across spots in a horseshoe, open towards the bridge so buildings never block your view. Assumes set plots: **plots vs free building is still open.**
- Your plot to an arch is a 38-second walk. That's too long to repeat every trip: **proposed fix, a launch pad on each plot** that flings you to the plaza (about 8 s, and fun). Going home is instant by waystone.
- Six arches, not 30: thirty wouldn't fit or frame anything. **Proposed:** you pick any opened Land of that theme at its arch.
- The islands in the sky are simple stand-ins, about 30 low-detail models; a real Land only loads when you go through an arch. Roblox may drop very distant models at low graphics settings (not tested), so they may need to be smaller models placed closer, which looks the same from the Haven.
- Not tested: memory at a full server of eight built-up plots.
- When the Haven goes into Studio, the old Lands and test areas get moved out of the Workspace, not deleted. Home spawn and the `BlockoutTravel` script live inside `ValeV3`, so they have to move with care.
