# Roblox lighting and camera, for matching Blender to Studio (researched 2026-11-08)

Written for the cottage showcase: hand-painted ColorMaps on MeshParts (SurfaceAppearance, no other maps), seen about 37
degrees down through a long lens, warm afternoon sun from the upper left, blue sky. Studio was not opened for this; every
Studio fact comes from the sources at the end. Each claim carries a label:

- **[Doc]** official Roblox docs, or a Roblox staff post on the DevForum.
- **[Comm]** DevForum community report or measurement (not confirmed by Roblox).
- **[Blender]** measured here in Blender 5.2.2 (scripts in my scratchpad, not in the repo).
- **[Est]** my own inference. Not verified in Studio; the calibration in section 8.4 replaces these with numbers.

## Short answers

- **Technology is gone.** Since 2025-07-23 two properties replace it: `LightingStyle` (Realistic = old Future; Soft = old
  ShadowMap or Voxel) and `PrioritizeLightingQuality`. New places start on **Soft**; set **Realistic**. [Doc]
- **Tone mapping:** linear HDR rendering with a custom **filmic curve (toe, straight middle, shoulder)**, not ACES. The
  numbers were never published. It does not depend on the lighting style; `ColorGradingEffect.TonemapperPreset` picks
  Default (post-2019 curve) or Retro (old Compatibility curve). [Doc] One measured point: a scene value of 1.0 (a white sky
  texel) shows as **223/255**. [Comm]
- **ExposureCompensation** is in stops before the tone map, range -5 to 5. Same meaning as Blender's Exposure. [Doc]
- **Sun direction:** `GetSunDirection() = (sin θ·cos α, -cos θ·cos α, -sin α)` with θ = 15° × ClockTime and
  α = 23.5° - GeographicLatitude. It matches this project's measured sun to 2 decimals. Inverse: Latitude =
  23.5 + asin(d.Z); ClockTime = atan2(d.X, -d.Y) / 15°, mod 24. (Section 3.)
- **Sun colour:** the engine's own sun is neutral from about 6:30 to 17:30. Warmth has to come from `ColorShift_Top`. [Comm]
- **SurfaceAppearance with only a ColorMap:** metalness 0 [Doc]. The default roughness is not documented, so give every
  painted SurfaceAppearance one shared flat RoughnessMap. `MeshPart.Color` doesn't tint the map;
  `SurfaceAppearance.Color` multiplies it. [Doc]
- **Camera:** `FieldOfView` is **vertical**, 1 to 120°, default 70. [Doc] Orthographic projection exists only as a
  **Studio beta (2026-10-30)**, and sun shadows aren't correct in it yet. There's no lens shift. [Doc]
- **Long lens from far away:** shadow detail, local lights, mesh LOD (250 and 500 studs) and PBR detail all drop with
  distance from the camera. [Doc/Comm] Keep the camera within about 250 studs, set `Camera.Focus` on the cottage, and use
  `RenderFidelity = Precise` if you have to go farther.
- **Blender scale:** a sun of strength S lights a white surface it faces to S/π, and a uniform world colour W lights it
  to W. [Blender] So Roblox Brightness B corresponds to a Blender sun strength of about π × k × B, where k is unknown
  (likely 0.75 to 1). [Est] Measure k once with section 8.4.

## 1. How a Roblox frame is built

The model below is the best current one. Each step is labelled with how sure it is.

1. Colours (`Color3` properties, Part colours, ColorMaps) are sRGB. The renderer converts them to linear and lights in
   linear HDR. [Doc, Future Is Bright phase 1, 2018]
2. Per surface: `ColorMap × SurfaceAppearance.Color × (sun + ambient + sky)`, plus specular.
   - **Sun:** Brightness × sun colour × max(0, N·L) × shadow. The sun colour comes from the time of day and is shifted by
     `ColorShift_Top`. [Doc for the inputs; Est for the exact maths]
   - **Ambient:** `OutdoorAmbient` where the 4×4×4-stud lighting voxel sees the sky; `Ambient` where it's sheltered. [Doc]
     It is a flat term: as far as anyone can tell it ignores the surface normal and has no small-scale ambient occlusion.
     [Est; Comm: "ambient occlusion is barely visible in Future", 2024-25]
   - **Sky (IBL):** `EnvironmentDiffuseScale` × light from the skybox. It depends on the normal: faces pointing up get
     the upper sky. It's added on top of the ambients. [Doc]
   - There's no bounce light between objects, apart from a single indoor environment probe used for reflections. [Est]
3. `Atmosphere` scatters along the view ray and takes most of its colour from the skybox. [Doc]
4. The image is scaled by 2^ExposureCompensation, gets bloom added (bloom works in HDR, with thresholds above 1), and is
   tone mapped. [Doc]
5. `ColorCorrectionEffect` runs after the tone map, on clipped display colours. [Comm, 2024 feature request]

## 2. Lighting properties

"Class default" is what a bare `Lighting` gets in the API dump (v0.746). Templates set their own values: the Baseplate's
Ambient and OutdoorAmbient are 70, 70, 70. [Doc, outdoor-lighting tutorial] To see the rest on your fresh Baseplate, use
the printout below.

| Property | Range, defaults | What it does physically | Notes |
|---|---|---|---|
| `LightingStyle` | Realistic / Soft. New places: Soft | Realistic: per-pixel local lights with specular and shadows, shadow-mapped sun. Soft: flatter look, local lights from the voxel grid | Map: Future = Realistic + PLQ on; ShadowMap = Soft + PLQ on; Voxel = Soft + PLQ off [Doc]. Realistic + PLQ off = Future with a shorter shading distance [Doc] |
| `PrioritizeLightingQuality` | bool, default true | When quality drops, true keeps shadows and shaders at close range and gives up view distance | Keeps big shadows to larger distances [Doc] |
| `Technology` | deprecated, scripts can't read it | none | Compatibility was removed in Oct 2024 and became Voxel + Retro tone map [Doc] |
| `Brightness` | float. Docs show 0.5 to 3.75. Class default 1 | Multiplier on direct sun (or moon) light | Also scales the ColorShift effects [Doc]. In 2018, Roblox said HDR needs about 2 where legacy used 1 [Doc] |
| `ExposureCompensation` | -5 to 5, default 0 | Whole scene × 2^EV before the tone map | Also brightens the sky. High values show colour banding [Comm] |
| `Ambient` | Color3. Docs default 0, 0, 0 | Flat fill in sheltered voxels | Applies everywhere when GlobalShadows is off [Doc] |
| `OutdoorAmbient` | Color3. Docs default 127 grey | Flat fill where the voxel sees sky. In practice, the colour of sun shadows outdoors | Clamped to be at least Ambient in each channel [Doc] |
| `EnvironmentDiffuseScale` | 0 to 1, class default 0 | Adds diffuse light from the skybox (IBL) | Lower the ambients when you raise it [Doc]. A bright blue sky at 1 makes shade noticeably blue [Est; `art-style.md` notes "Studio's sky adds blue"] |
| `EnvironmentSpecularScale` | 0 to 1, default 0 | Sky reflections, sharp on smooth surfaces | Metalness does nothing at 0 [Doc] |
| `ColorShift_Top` | Color3, default black (no shift) | Tints direct light on faces turned to the sun | Effect grows with Brightness [Doc]. The usual way to warm the sun [Comm] |
| `ColorShift_Bottom` | Color3 | Meant to tint faces turned away from the sun | Does nothing with ShadowMap/Future at quality level 5 or higher. Bug open since 2023, still reported 2026-10-14 [Comm] |
| `GlobalShadows` | bool | All sun shadows, and the indoor/outdoor ambient split | Off: no shadows, `Ambient` everywhere [Doc] |
| `ShadowSoftness` | 0 (hard) to 1 (soft). Docs default 0.2 | Blur of sun shadow edges | Realistic only [Doc; staff 2025-04-11]. Doesn't affect local lights [Comm] |
| `ClockTime` / `TimeOfDay` | 0 to 24 hours | Sun position, plus the time-of-day colour curves | Doesn't run on its own. ClockTime isn't saved itself; TimeOfDay is [Doc] |
| `GeographicLatitude` | degrees. Class default 41.733 | Slides the sun's daily path toward +Z or -Z (section 3) | |
| `FogColor`, `FogStart`, `FogEnd` | studs from the camera. FogEnd default 100000 | Old linear fog | Hidden when Lighting has an Atmosphere [Doc] |
| `ExtendLightRangeTo120` | hidden | none | Local light `Range` is capped at 120 studs [Doc] |

The 2025 Unified Lighting post said scripts can't set `LightingStyle` or `PrioritizeLightingQuality`. The current API lists
both as writable. If a command-bar or MCP write fails, set them in the Properties window. [Doc]

**Printout of the current setup** (command bar):

```lua
local L = game:GetService("Lighting")
for _, p in {"LightingStyle", "PrioritizeLightingQuality", "Brightness", "ExposureCompensation", "Ambient",
	"OutdoorAmbient", "EnvironmentDiffuseScale", "EnvironmentSpecularScale", "ColorShift_Top", "GlobalShadows",
	"ShadowSoftness", "ClockTime", "GeographicLatitude"} do
	print(p, L[p])
end
print("SunDirection", L:GetSunDirection())
for _, c in L:GetChildren() do
	print(c.ClassName, c.Name)
end
```

### Tone mapping
- 2018: the whole pipeline moved to gamma-correct HDR "with a tonemapper that tries to maintain balance between keeping the
  content look reasonable but handling overly bright regions nicer". [Doc, zeuxcg]
- 2019: the curve is filmic: a toe where dark colours "flatten out" (they lose detail), a straight middle that keeps hue,
  and a shoulder that compresses highlights. Toe and shoulder controls were promised and never shipped. [Doc, zeuxcg]
- 2024: `ColorGradingEffect` (in Lighting) has `TonemapperPreset`. **Default** is the post-2019 curve, "vivid colors and high
  contrasts". **Retro** imitates pre-2019 Roblox: less saturation and contrast. Any preset works with any lighting style,
  and no more presets are planned. [Doc]
- The curve's numbers are not public; a question in Feb 2026 got no answer. [Comm]
- Known points: sky texture 1.0 → 223/255 with Default. [Comm, 2024] With Retro, people report the sky's raw colours
  showing. [Comm, 2025] Blender's view transforms at the same input are in section 8.2.

## 3. Sun direction

**Formula** [Comm: reverse-engineered engine code, used by Nevermore's SunPositionUtils to place the sun "where Roblox is
rendering the sun"; checked against this project]:

```
θ = 2π × ClockTime / 24                (15 degrees per hour)
α = 23.5° - GeographicLatitude         (the engine's tilt term; its day-of-year part changes this by under 0.01°)
GetSunDirection() = ( sin θ · cos α ,  -cos θ · cos α ,  -sin α )
```

**Check:** `docs/style/lessons/cottage.md` recorded ClockTime 15.6 with sun (-0.74, 0.54, -0.40). The formula with
latitude 0 gives (-0.742, 0.539, -0.399).

**What it means:**
- The sun is up from exactly 6:00 to 18:00 at every latitude. It rises toward +X and sets toward -X.
- Elevation = asin(-cos θ · cos α). Noon elevation = 90° - |α|.
- Latitude doesn't tilt the sun's daily circle, it slides it sideways: toward +Z when latitude is above 23.5, toward -Z
  below. The sun always climbs straight up from the horizon.
- **Latitude 23.5 is the simple case:** the sun stays in the X-Y plane. In the afternoon it stands due -X at an elevation
  of 15° × (18 - ClockTime).

**Inverse** (to place the sun along a chosen unit vector d):
`GeographicLatitude = 23.5 + asin(d.Z)` in degrees, and `ClockTime = (atan2(d.X, -d.Y) in degrees / 15) mod 24`.
For any sun higher than about 24°, every heading can be reached with a latitude inside ±90.

**Examples** (elevation / heading, where heading 0 = toward -Z and 90 = toward +X):

| Latitude | 9:00 | 12:00 | 14:00 | 15:00 | 15:30 | 16:00 | 17:00 |
|---|---|---|---|---|---|---|---|
| 0 | 40.4 / 58 | 66.5 / 0 | 52.6 / 311 | 40.4 / 302 | 33.9 / 299 | 27.3 / 297 | 13.7 / 294 |
| 23.5 | 45 / 90 | 90 | 60 / 270 | 45 / 270 | 37.5 / 270 | 30 / 270 | 15 / 270 |
| 41.733 | 42.2 / 115 | 71.8 / 180 | 55.3 / 237 | 42.2 / 245 | 35.3 / 247 | 28.4 / 249 | 14.2 / 251 |

**Colour over the day** [Comm, from the same reverse-engineered code]: the sun's light colour is a constant neutral grey
from 6:30 to 17:30. From 17:30 to 18:00 it drops through a dim warm tone to dark red. The sky tint stays white over the same
hours. So for a warm afternoon: keep ClockTime somewhere in 13 to 17, add a warm `ColorShift_Top`, and choose the direction
freely with latitude.

**Aim the sun relative to a fixed camera** (command bar). `REL_AZ` is measured from the camera's view direction, swinging
to the left: 0 = sun beyond the subject (backlight), 90 = from screen-left, 180 = from behind the camera.

```lua
local Lighting = game:GetService("Lighting")
local cam = workspace.CurrentCamera
local REL_AZ, ELEV = 80, 40 -- degrees
local f = (cam.CFrame.LookVector * Vector3.new(1, 0, 1)).Unit
local r = (cam.CFrame.RightVector * Vector3.new(1, 0, 1)).Unit
local a, e = math.rad(REL_AZ), math.rad(ELEV)
local d = (f * math.cos(a) - r * math.sin(a)) * math.cos(e) + Vector3.yAxis * math.sin(e)
Lighting.GeographicLatitude = 23.5 + math.deg(math.asin(d.Z))
Lighting.ClockTime = (math.deg(math.atan2(d.X, -d.Y)) / 15) % 24
print("asked", d, "got", Lighting:GetSunDirection())
```

For "sun from the upper left, shadows falling down-right", use REL_AZ 60 to 100 and ELEV 35 to 45. In a 3/4 view, REL_AZ
60 lights the left wall at a glancing angle and leaves the right wall in shade. Around 100, the left wall is lit more
squarely and shadows run straight right. [Est, geometry]

`Sky.SkyboxOrientation` turns the sky images but not the sun or moon [Doc], so a painted sky can be turned to suit the
camera without moving the light.

**In Blender** (1 Blender unit = 1 stud, Blender Z up): Roblox (x, y, z) becomes Blender (x, -z, y).

```python
import bpy, math
from mathutils import Vector

def rbx(v):  # Roblox Y-up -> Blender Z-up
    return Vector((v[0], -v[2], v[1]))

sun = bpy.data.objects["Sun"]
sun.rotation_euler = rbx((-0.742, 0.539, -0.399)).to_track_quat('Z', 'Y').to_euler()  # paste GetSunDirection()
```

## 4. How SurfaceAppearance shades

| Topic | What happens | Source |
|---|---|---|
| Maps | ColorMap (sRGB albedo + alpha), NormalMap, RoughnessMap, MetalnessMap, emissive mask (+ EmissiveStrength, EmissiveTint). Maps are 1024 at most | [Doc] |
| Only a ColorMap | Metalness is 0 when there's no metalness map | [Doc, 2023 version of the PBR page] |
| Roughness without a map | Not documented. Distant SurfaceAppearances that drop their maps are reported to look shiny, "like plastic", which suggests the default isn't fully rough | [Comm, 2024] |
| Specular | Sun specular in every style; Future also gives local lights specular. Fresnel can add sheen at grazing angles "even with rough surfaces"; adding about 0.1 roughness helps | [Doc] |
| `SurfaceAppearance.Color` | Multiplies the ColorMap (white = no change) | [Doc] |
| `MeshPart.Color` | Does **not** tint the ColorMap. In Overlay mode (the default) it shows through wherever ColorMap alpha is below 1 | [Doc] |
| AlphaMode Overlay | Default. Alpha blends the map over `MeshPart.Color` | [Doc] |
| AlphaMode Transparency | Alpha cuts the surface. With `MeshPart.Transparency` 0: hard cut-out with proper depth sorting (leaves). With 0.02 or more: soft blending, but not every effect works | [Doc] |
| AlphaMode TintMask | Alpha says where `SurfaceAppearance.Color` tints | [Doc] |
| AlphaMode Opaque | Ignores alpha. Beta: File > Beta Features > MaterialVariant Alpha Mode | [Doc] |
| Normals | The mesh's vertex normals are the shading normals; the normal map's Z is the mesh normal. Normal maps are tangent space, OpenGL (+Y), and need tangents in the export | [Doc] |
| Custom split normals | Kept on import. Not stated in the docs, but this project's weighted and hard-edge normals show in Studio | [Est] |
| Back faces | Culled unless `MeshPart.DoubleSided` | [Doc] |
| Distance | `RenderFidelity` Automatic: highest under 250 studs from the camera, medium at 250 to 500, lowest beyond (the lowest also loses shine) | [Doc] |
| Low-end devices | Texture streaming can scale textures down | [Comm, 2026] |

**For the painted cottage:**
- Export ColorMaps with alpha 1 everywhere, or no alpha channel. In Overlay mode, soft alpha edges let `MeshPart.Color`
  bleed through.
- Upload one tiny flat RoughnessMap (white, or about 0.9) and use it on every painted SurfaceAppearance. Then the
  specular is known, and Blender can copy it: Principled Roughness at the same value, Specular IOR Level 0.5 (4% reflection).
- Keep `EnvironmentSpecularScale` low (0 to 0.2) so the paint doesn't mirror the sky.

## 5. Post effects, Atmosphere and Sky

Class defaults are from the API dump; the Baseplate template sets its own.

| Object.property | Class default | What it does | Stylized range |
|---|---|---|---|
| Atmosphere.Density | 0.395 | Air particles: hides distant objects and terrain. It reaches the sky only through those objects | 0.1 to 0.4 |
| Atmosphere.Offset | 0 | Low: distant objects blend into the sky (too low lets the sky "ghost" through them). High: they stand out as silhouettes, and LOD popping shows | 0.1 to 0.3 |
| Atmosphere.Haze | 0 | Haze above the horizon and into the distance | 0 to 2 |
| Atmosphere.Color | 200, 170, 108 | Hue of the haze. Needs Haze | Near the scene's average colour [Doc tutorial] |
| Atmosphere.Glare | 0 | Glow around the sun. Needs Haze above 0 | 0 to 1 |
| Atmosphere.Decay | 92, 60, 14 | Hue away from the sun. Needs Haze and Glare above 0 | |
| Sky.SunAngularSize | 21 (0 to 60) | Size of the sun disc in degrees | |
| Sky.CelestialBodiesShown | true | Sun, moon and stars on or off | Off if the painted sky has its own sun |
| Sky.SkyboxOrientation | 0, 0, 0 | Turns the six faces (Y first). Not the sun | |
| BloomEffect.Intensity / Size / Threshold | 0.4 / 24 px / 0.95 | HDR bloom. Size is in screen pixels, so it changes with capture resolution | Threshold 1.5 to 2.5 after the HDR move [Doc 2018]; intensity 0.2 to 0.5 |
| ColorCorrectionEffect.Brightness / Contrast / Saturation / TintColor | 0 / 0 / 0 / white | After the tone map, clipped. Brightness -1 = black, +1 = white; Saturation -1 = grey; TintColor multiplies | Saturation +0.05 to 0.15, Contrast +0.05 to 0.1, a faintly warm tint |
| ColorGradingEffect.TonemapperPreset | Default | Default or Retro curve | Default |
| SunRaysEffect.Intensity / Spread | 0.25 / 1 (both 0 to 1) | Rays around the sun. Only when the sun is on screen | Off for a 37°-down shot |
| DepthOfFieldEffect.FarIntensity / FocusDistance / InFocusRadius / NearIntensity | 0.75 / 0.05 / 10 / 0.75 | Blur away from the focus. Distances in studs | Far 0.05 to 0.15 with FocusDistance = camera distance. Studio may cap the distances (unverified) |
| BlurEffect.Size | 24 | Whole-screen blur | Off |

Notes:
- The skybox's lower half lights objects from below through the IBL. Make it darker than the upper half and close to the
  ground colour. [Doc]
- Sky textures can't exceed 1.0, so a white sky shows as about 223 and a sunlit white wall outshines it. [Comm]
- Atmosphere is applied along the camera ray. A camera 150+ studs away puts the cottage behind a long stretch of haze,
  so use a lower Density than for a player-height view. [Est]

## 6. Camera

| Property | Facts |
|---|---|
| `FieldOfView` | **Vertical**, clamped 1 to 120, default 70. Horizontal FOV = 2·atan(tan(v/2) × aspect) [Doc] |
| `FieldOfViewMode` | Vertical (default), Diagonal or MaxAxis: which FOV stays fixed when the window resizes. `DiagonalFieldOfView` and `MaxAxisFieldOfView` give the others [Doc] |
| `NearPlaneZ` | Read-only, between -0.1 and -0.5 [Doc] |
| `Focus` | Where the engine spends lighting detail (local lights may not render far from it). Default camera scripts set it; a Scriptable camera must set it every frame [Doc]. Shadows "prioritize distance from the focus point" but have a hard cut-off by distance [Doc, staff 2023]. Since June 2025, lighting quality follows Focus [Comm] |
| `ProjectionType` Orthographic | **Studio beta since 2026-10-30** (File > Beta Features > Orthographic Camera). It can't be published yet. `OrthographicSize` is the view height in studs (default 35, 0.001 to 100000), `OrthographicMode` is Vertical, Horizontal, Diagonal or MaxAxis. Known issues: sun shadows aren't correct, specular is computed as if perspective, the near plane cuts geometry when the camera is inside the scene, ViewportFrames stay perspective [Doc]. Depth of field breaks, and shadow and light quality still fade with distance [Comm] |
| `ViewStretch` | 0.5 to 2.0, horizontal stretch, both projections [Doc] |
| Lens shift | None. Staff: keep the camera CFrame orthonormal; skewing it "breaks everything else" [Doc, 2026-11-02] |
| Free camera | Shift+P in a playtest. Mouse wheel zooms the FOV, the up arrow opens settings (DoF, Bloom, Colour Correction, Colour Grading). Ctrl+Shift+G/C/B/N hide UI [Doc] |

**Long-lens framing.** Distance for a frame that shows H studs vertically at the subject: D = (H/2) / tan(FOV/2).
For H = 50 studs and a subject 40 studs deep along the view:

| FieldOfView | Distance | Near/far size ratio | Blender lens (36 mm, 16:9, Sensor Fit Auto) |
|---|---|---|---|
| 70 (default) | 36 | 3.55 | 14.5 mm |
| 30 | 93 | 1.55 | 37.8 mm |
| 25 | 113 | 1.43 | 45.7 mm |
| 20 | 142 | 1.33 | 57.4 mm |
| 18 | 158 | 1.29 | 63.9 mm |
| 15 | 190 | 1.24 | 76.9 mm |
| 10 | 286 | 1.15 | 115.7 mm |
| 6 | 477 | 1.09 | 193.2 mm |

True isometric looks down 35.26°, and 2:1 pixel-art isometric 30°; the illustration's 37° is close to both. Turn the camera
45° to the cottage's front for the classic 3/4.

**Problems with a narrow FOV from far away:**
1. **Sun shadows:** shadow-map detail falls with distance, then stops at a hard cut-off. [Doc, staff 2023] Shadows have
   been seen handing over to voxel lighting past about 600 studs (2021), and leaves losing shadows at moderate range
   (2025). [Comm] Stay under about 250 studs, set Focus, and keep ShadowSoftness at 0.1 to 0.2 to hide stair-steps.
2. **Mesh LOD** is decided by distance from the camera, not the focus (250 and 500 studs). [Doc] Use `RenderFidelity
   Precise` on hero meshes beyond 250 studs.
3. **PBR detail:** far SurfaceAppearances lose their maps and look plastic. [Comm, 2024 and 2025]
4. **Local lights** switch off away from the camera and Focus. [Doc]
5. **Atmosphere and fog** thicken with camera distance (section 5).
6. **Depth precision:** the tiny-FOV trick "causes z-fighting and precision issues" and can get content culled on low-end
   devices. [Doc, staff 2026-10-30] At 150 to 300 studs this shouldn't matter. [Est]
7. **Play mode:** streaming loads around the player, not the camera. The draw distance at the lowest quality is now 500
   studs (since 2026-11-05). Studio edit mode at quality 21 shows everything. [Doc]
8. **No sky in frame:** looking 37° down, the horizon only enters the frame if the FOV is over 74°. The sky then reaches
   the image only through IBL and ambient colour, and the background is ground, so replace the Baseplate grid. [Est]

**Set the camera** (command bar). Studio's edit camera may take control back; set `CameraType` to Fixed again when done.

```lua
local target = Vector3.new(0, 10, 0)          -- cottage centre
local FOV, PITCH, YAW, FRAME = 18, 37, 45, 50 -- degrees, degrees down, degrees around Y, studs shown vertically
local dist = (FRAME / 2) / math.tan(math.rad(FOV / 2))
local cam = workspace.CurrentCamera
cam.CameraType = Enum.CameraType.Scriptable
cam.FieldOfView = FOV
cam.CFrame = CFrame.new(target) * CFrame.Angles(0, math.rad(YAW), 0) * CFrame.Angles(-math.rad(PITCH), 0, 0)
	* CFrame.new(0, 0, dist)
cam.Focus = CFrame.new(target)
print("camera at", cam.CFrame.Position, "distance", dist)
```

**In Blender:** set Sensor Fit to Vertical and set the angle to the Roblox FieldOfView (`cam.sensor_fit = 'VERTICAL';
cam.angle_y = math.radians(fov)`). Use the same aspect ratio as the Studio viewport, and convert positions with (x, -z, y).

## 7. Shadows

- **Sun shadows** use shadow maps with Realistic, and with Soft + PrioritizeLightingQuality on. Soft with it off uses the
  4×4×4-stud voxel grid, which can't shadow objects smaller than about 4 studs properly. [Doc]
- **Reach and quality:** both depend on the quality level, and the lowest levels fall back to voxel shadows. [Doc 2019]
  PrioritizeLightingQuality keeps large shadows out to larger distances. [Doc 2025] There's a hard cut-off by distance
  from the camera; Roblox publishes no numbers. [Doc, staff 2023] Future-style shadows need quality level 4 or higher.
  [Comm] Judge at Studio's Editor Quality Level 21, but expect less on weak devices.
- **Softness:** `ShadowSoftness` 0 to 1, Realistic only. Shadows are on or off per pixel: no partial or coloured shadows
  through glass. [Doc; Comm 2022]
- **CastShadow** is per part. Leave it on in general; turning it off can cause artifacts on shadows falling on that part.
  [Doc]
- **Transparency:** parts and decals stop casting sun shadows at a Transparency of about 0.75 and above; below that they
  cast full shadows. [Comm, 2020 and 2022]
- **Decals and Textures** cast alpha-shaped shadows (people use them to cast "shadow figures"). In 2019 they ignored
  CastShadow on transparent parts. [Comm]
- **Leaf cards:** SurfaceAppearance with AlphaMode Transparency and `MeshPart.Transparency` 0 renders as a true cut-out.
  [Doc] It is reported to cast "proper", leaf-shaped shadows. [Comm, 2022] Not in the docs; check one card in Studio
  before relying on it.
- **Shadow colour** comes from the ambient (OutdoorAmbient or Ambient) plus the sky IBL, not from ColorShift_Bottom (which
  doesn't work). Outdoors, OutdoorAmbient is effectively the shadow colour. [Est; Comm]
- Local-light shadows cost a lot: spot shadows are cheapest, point shadows the most expensive. Per-pixel light distance
  depends on quality. [Doc, 2020] (This project avoids point lights on houses anyway.)

## 8. Blender equivalence

### 8.1 Measured in Blender 5.2.2 [Blender]
- A sun of strength S on a white, fully rough surface facing it gives S/π: strength 1 → 0.318, and 0.159 at 60°
  incidence. Same in Cycles and EEVEE.
- A uniform world colour W lights an open white surface to W (Cycles 1.000, EEVEE 0.992).
- EEVEE's world light was **not** darkened by a tall black wall beside the ground, with raytracing on or off; its
  occlusion is screen-space only. That is close to Roblox's flat ambient.
- Cycles darkened the ground beside the same wall to 0.50 to 0.69: ambient occlusion that Roblox doesn't have.

### 8.2 View transforms (Blender 5.2.2, sRGB display, output 0 to 255)

| Scene value | 0.02 | 0.05 | 0.1 | 0.18 | 0.25 | 0.5 | 0.75 | 1.0 | 1.5 | 2 | 3 | 4 | 8 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Standard | 39 | 63 | 89 | 118 | 137 | 188 | 225 | 255 | clip | clip | clip | clip | clip |
| Filmic | 41 | 70 | 99 | 128 | 144 | 177 | 195 | 206 | 219 | 228 | 237 | 242 | 251 |
| Filmic + High Contrast | 25 | 55 | 90 | 128 | 149 | 190 | 209 | 220 | 232 | 239 | 245 | 249 | 253 |
| AgX | 32 | 58 | 87 | 118 | 136 | 170 | 186 | 197 | 209 | 217 | 227 | 233 | 245 |
| AgX + AgX - High Contrast | 16 | 42 | 76 | 118 | 143 | 186 | 206 | 217 | 230 | 238 | 247 | 253 | 255 |
| Khronos PBR Neutral | 8 | 34 | 70 | 105 | 127 | 181 | 219 | 239 | 248 | 250 | 252 | 253 | 254 |
| ACES 1.3 | 11 | 32 | 58 | 91 | 114 | 165 | 192 | 207 | 223 | 231 | 239 | 244 | 251 |
| **Roblox Default** | toe ("flattens") | | | | | | | **≈223** [Comm] | | | | | |

On the one known point, **Filmic + High Contrast** (220) is the closest built-in, and it also has a filmic toe and shoulder.
**Standard**, which this project's Blender scripts use now, has no toe and clips at 1.0. That fits the cottage lesson: lit
sides matched, while shaded sides came out darker (and bluer, from the ambient) in Studio. [Est]

### 8.3 Mapping table

| Roblox | Blender | Status |
|---|---|---|
| Colours are sRGB, lighting is linear | Image textures as sRGB; convert colour swatches to linear for shader inputs | [Doc] |
| Default tone map | View Transform Filmic, Look High Contrast, or a measured LUT on a linear EXR (section 8.4) | [Est] |
| Retro tone map | Standard, if Retro really is identity below 1.0 (test it) | [Comm/Est] |
| `ExposureCompensation` | Colour Management Exposure (both are stops before the transform) | [Doc] |
| `GetSunDirection()` (x, y, z) | Sun lamp +Z pointed along (x, -z, y) (section 3 snippet) | [Doc + geometry] |
| `Brightness` B | Sun strength ≈ π × k × B, k about 0.75 to 1. So B = 3 → 7.1 to 9.4 | [Est] |
| Sun colour (neutral, shifted by `ColorShift_Top`) | Sun colour = a white card's RGB measured in Studio with your ColorShift_Top | [Est] |
| `OutdoorAmbient` (flat) | Uniform world colour = sRGB→linear(OutdoorAmbient) × a, with a ≈ 1. EEVEE, raytracing off | [Est] |
| `EnvironmentDiffuseScale` × skybox | Add the skybox image to the world at strength EDS × s, with s ≈ 1 | [Est] |
| `Ambient` (sheltered) | Ignore for exteriors; Blender has no indoor/outdoor voxel switch | [Est] |
| No bounce light, no small-scale AO | EEVEE with raytracing off. In Cycles, set diffuse bounces to 0 and accept the extra occlusion | [Blender + Est] |
| `ShadowSoftness` | Sun Angle ≈ penumbra width / distance from the occluder edge (in radians), measured in Studio | [Est] |
| Specular (GGX, dielectric 4%) | Principled: Roughness = your RoughnessMap value, Specular IOR Level 0.5 | [Doc + Est] |
| Atmosphere | Mist pass mixed toward the Atmosphere colour, or turn Atmosphere down and skip it | [Est] |
| Bloom (HDR) | Compositor Glare (Bloom) before the view transform | [Est] |
| ColorCorrection (after the tone map, clipped) | Apply to the finished image after the view transform, not in the compositor | [Comm] |
| `FieldOfView` (vertical) | Sensor Fit Vertical, same angle, same aspect ratio | [Doc] |

**Worked example:** Brightness 3, OutdoorAmbient (0.43, 0.46, 0.57) (= 110, 118, 145), EnvironmentDiffuseScale 1.
- **Sun:** strength 7.1 to 9.4. White unless ColorShift_Top is set.
- **World:** uniform (0.156, 0.181, 0.283), plus the skybox at strength 1 for the EnvironmentDiffuseScale part. With a
  bright blue sky, the sky part is larger than the OutdoorAmbient part, which is why Studio's shade reads blue.
- **Colour management:** Filmic + High Contrast, Exposure 0.

### 8.4 Calibration (about 15 minutes in Studio, then Blender can be trusted)
1. **Fresh Baseplate.** Editor Quality Level 21. LightingStyle Realistic, PrioritizeLightingQuality on.
2. **Clean light:** disable every PostEffect; set Atmosphere Density, Haze and Glare to 0; Ambient = OutdoorAmbient = 0;
   EnvironmentDiffuseScale = EnvironmentSpecularScale = 0; ColorShift_Top = 0; Brightness 1; ExposureCompensation 0;
   GeographicLatitude 23.5 and ClockTime 12, which puts the sun straight up. Check GetSunDirection ≈ (0, 1, 0).
3. **Cards:** 9 grey cards with their tops facing up, ideally one MeshPart plane with a 9-step grey ColorMap and the white
   roughness map (the same path as the assets). SmoothPlastic parts are a fallback:

   ```lua
   local folder = Instance.new("Folder")
   folder.Name = "LightCalibration"
   folder.Parent = workspace
   for i, v in {255, 224, 192, 160, 128, 96, 64, 32, 16} do
   	local p = Instance.new("Part")
   	p.Anchored = true
   	p.Material = Enum.Material.SmoothPlastic
   	p.Size = Vector3.new(4, 1, 4)
   	p.Color = Color3.fromRGB(v, v, v)
   	p.CFrame = CFrame.new((i - 5) * 5, 50, 0)
   	p.Parent = folder
   end
   ```

4. **Exposure sweep:** step ExposureCompensation from -4 to +3 one stop at a time, capturing each step. Read each card's
   median screen value. Input y = linear(card) × 2^EV, in units of "white card under Brightness 1". The pairs (y,
   screen value) are Roblox's curve g. k is folded in, so Blender only needs sun strength = π × Brightness and g as its
   display transform: render a linear EXR and apply g per channel in numpy.
5. **Ambient:** set Brightness 0 and OutdoorAmbient 128 grey (linear 0.216). The cards give g(a × 0.216 × card), so a
   follows. Then set EnvironmentDiffuseScale 1 with your sky to get the sky term the same way.
6. **Softness:** a 10-stud pole at ShadowSoftness 0.15. Penumbra width ÷ pole length gives the Blender sun angle.
7. **Warm sun:** Brightness 1 with your ColorShift_Top, white card RGB ÷ neutral card RGB = Blender sun colour.
8. **Optional:** repeat step 4 with ColorGradingEffect set to Retro to see whether it's close to Standard.

## 9. Recommended starting values for a sunny stylized scene

My recommendation, not taken from a source. Tune by eye against the illustration, from both sides of the cottage.

| Setting | Value | Why |
|---|---|---|
| LightingStyle / PrioritizeLightingQuality | Realistic / on | Shadow-mapped sun, ShadowSoftness works |
| Brightness | 2.5 (2 to 3) | Lit plaster stays under the shoulder |
| ExposureCompensation | 0 | Use Brightness and the ambients first |
| ColorShift_Top | 255, 226, 184 | Warm afternoon sun; the engine's sun is neutral before 17:30 |
| ColorShift_Bottom | 0, 0, 0 | Does nothing anyway |
| OutdoorAmbient | 120, 128, 158 | Cool lavender-blue shade that stays readable (this project wants darks with colour, not black) |
| Ambient | 70, 72, 92 | Sheltered areas a step darker |
| EnvironmentDiffuseScale | 0.35 | A little sky blue that changes with facing; raise it for bluer roofs |
| EnvironmentSpecularScale | 0.1 | Paint shouldn't mirror the sky |
| GlobalShadows / ShadowSoftness | true / 0.15 | Crisp edges that hide shadow-map steps at 150+ studs |
| Sun | ELEV 38 to 45, REL_AZ 70 to 100 (section 3 snippet) | From the upper left, shadows to the lower right |
| Atmosphere | Density 0.12, Offset 0.2, Haze 0.5, Glare 0, Color 190, 215, 240, Decay 150, 160, 190 | Light veil only; the camera is far away |
| Sky | This project's Stylized Skybox (8755940451), lower half darker | IBL colour comes from it |
| Bloom | Intensity 0.3, Size 24, Threshold 2.5 | No glow on sunlit plaster |
| ColorCorrection | Saturation 0.08, Contrast 0.05, Brightness 0, TintColor 255, 250, 244 | Gentle; it clips |
| ColorGrading | Default (A/B against Retro once) | |
| SunRays / DepthOfField | Off / off (or Far 0.05) | Sun is off screen; keep the paint sharp |
| Camera | FOV 18, pitch 37, yaw 45 to the front, about 158 studs for a 50-stud frame, Focus on the cottage | Under the 250-stud LOD step |
| Studio | Editor Quality Level 21; Graphics Mode Automatic (not OpenGL); replace the Baseplate grid with ground | Full quality; clean backdrop |

**Fresh Baseplate checklist:** Quality 21 → LightingStyle Realistic → printout (section 2) to record the template values
→ set the values above → camera snippet → sun snippet → print GetSunDirection and paste it into Blender.

## 10. Builder presets and showcase tips

| Source (date) | Values |
|---|---|
| Roblox core curriculum, "Island Jump" stylized islands [Doc] | Ambient 16, 16, 16. OutdoorAmbient 134, 158, 190. ColorShift_Top 196, 222, 255. ShadowSoftness 0. Realistic. ClockTime 9, GeographicLatitude 78 (sun 24° up). Atmosphere Density 0.375, Offset 0.17 |
| Roblox tutorial "Enhance outdoor environments" [Doc] | Realistic. EnvironmentDiffuseScale and EnvironmentSpecularScale 1. ClockTime 17. Ambient = OutdoorAmbient 156, 136, 176 (evening purple). Atmosphere Density 0.272, Haze 1, Color 85, 78, 54 |
| Roblox environmental-art curriculum, sci-fi laser tag [Doc] | Ambient = OutdoorAmbient 26, 34, 36. Realistic. ShadowSoftness 0.15. Latitude -18. Atmosphere Density 0.285, Offset 0.65, Glare 0.3, Haze 2, Decay 254, 254, 254. Bloom 1.5 / Size 56. DoF Far 0.05 |
| AerialsAbove, "Building and Showcase TIPS" (2020-06) [Comm] | Warm OutdoorAmbient; darker Ambient for stronger shadows; very warm ColorShift_Top "for a soft glowing sun". Use ColorCorrection, but go light on sun rays, DoF, contrast and exposure |
| Bethink (Adopt Me), quoted on the forum (2020-06) [Comm] | Voxel. ColorCorrection Brightness 0.2, Contrast 0.1, Saturation 0.12, TintColor 255, 243, 235 |
| Forum answer for a cartoony look (2023-01) [Comm] | ShadowMap, Brightness 2.5, ExposureCompensation 0.1, ShadowSoftness 0.05, warm ColorCorrection |
| Ahlvie, Kingdom Life II (2020-08) [Comm] | Animate ColorShift_Top through the day to warm the sun |
| This project's terrain lesson (`terrain-method.md`) | Atmosphere Color 114, 255, 220; Decay 64, 114, 132; Offset 0.25; Density about 0.3; ClockTime 12 |

**Framing a showcase shot:**
- 16:9 at 1920×1080. Keep the important parts out of the bottom strip, where the player count covers thumbnails. [Doc]
- Use the free camera (Shift+P) for stills and Ctrl+Shift+G/C/B/N to hide UI. [Doc]
- Put the strongest light-dark contrast on the cottage. Frame with darker shapes at the edges (a pine or rock, as this
  project's hero views do), and leave quiet ground around the subject.
- A sun 35 to 45° up gives long, readable shadows. Noon sun flattens the forms.
- Keep the shaded side readable with coloured ambient rather than raising the exposure.

## 10b. Measured in Studio (2026-11-08, the pink cottage study, Realistic style)
A painted scene matched against a reference by sampling the same areas in a Studio capture (research/pink_cottage/studio).
- **OutdoorAmbient lights from above only.** Walls get about half of it, so a Blender world light (even from all round)
  leaves Studio walls darker and roofs lighter. Put most ambient in `Ambient`: Ambient 146,138,134 with OutdoorAmbient
  80,78,82, Brightness 2.8, ExposureCompensation 0.45 matched the reference's lit-to-shade ratio (about 0.72, same hue).
- **Slates and other up-facing paint read about 20% lighter** than in Blender under that light. `SurfaceAppearance.Color`
  multiplies the ColorMap live, so it works as a per-asset grade without re-uploading (slates 0.76, 0.77, 0.81).
- **Vertex colours are read as sRGB** by the glb importer: export the sRGB-encoded values, or dark greens come out black.
- **SmoothPlastic is glossy** under Realistic lighting (white sun spots on foliage). A SurfaceAppearance with only a bright
  RoughnessMap makes it matte and keeps the vertex colours.
- **GUI is tone-mapped too:** a LightInfluence-0 SurfaceGui sky came out greyed with blue capped near 220. Its `Brightness`
  above 1 (1.4) and more saturated colours bring it back.
- The default place's DepthOfField blurs a far camera, and Atmosphere hazes a backdrop 1,000 studs off: turn both down for a
  showcase view. `MeshPart.RenderFidelity = Precise` can be set from the command bar and keeps detail at 280 studs.
- The sun formula in section 3 placed the sun exactly on Blender's direction (asked and got -0.608, 0.643, 0.467).

## 11. Still to verify in Studio
1. k, the Default tone curve, the ambient scale a and the sky scale s (section 8.4).
2. The roughness a SurfaceAppearance uses without a RoughnessMap.
3. Leaf-shaped shadows from SurfaceAppearance cut-outs.
4. How ShadowSoftness relates to Blender's sun angle.
5. Whether Retro behaves like Blender's Standard below 1.0.
6. The shadow cut-off at quality 21 for the chosen camera distance.
7. Ranges the docs don't give: the Brightness maximum, Atmosphere Haze and Glare maximums, DoF distance caps.

## Sources

Official Roblox documentation (create.roblox.com, read 2026-11-08; pages stamped 2026-11-06):
- [Lighting class](https://create.roblox.com/docs/reference/engine/classes/Lighting): properties, ExposureCompensation range, 120-stud light range.
- [Global lighting guide](https://create.roblox.com/docs/environment/lighting): ShadowSoftness 0 to 1 (Realistic only), LightingStyle, PrioritizeLightingQuality.
- [Atmosphere class](https://create.roblox.com/docs/reference/engine/classes/Atmosphere) and [Atmospheric effects](https://create.roblox.com/docs/environment/atmosphere).
- [Post-processing effects](https://create.roblox.com/docs/environment/post-processing-effects): ColorGradingEffect and the quality-level note; [BloomEffect](https://create.roblox.com/docs/reference/engine/classes/BloomEffect), [ColorCorrectionEffect](https://create.roblox.com/docs/reference/engine/classes/ColorCorrectionEffect), [ColorGradingEffect](https://create.roblox.com/docs/reference/engine/classes/ColorGradingEffect), [SunRaysEffect](https://create.roblox.com/docs/reference/engine/classes/SunRaysEffect), [DepthOfFieldEffect](https://create.roblox.com/docs/reference/engine/classes/DepthOfFieldEffect); enums [TonemapperPreset](https://create.roblox.com/docs/reference/engine/enums/TonemapperPreset), [LightingStyle](https://create.roblox.com/docs/reference/engine/enums/LightingStyle), [Technology](https://create.roblox.com/docs/reference/engine/enums/Technology).
- [Sky class](https://create.roblox.com/docs/reference/engine/classes/Sky) and [Skyboxes](https://create.roblox.com/docs/environment/skybox).
- [SurfaceAppearance class](https://create.roblox.com/docs/reference/engine/classes/SurfaceAppearance), [PBR textures](https://create.roblox.com/docs/art/modeling/surface-appearance), [AlphaMode](https://create.roblox.com/docs/reference/engine/enums/AlphaMode), [Material references](https://create.roblox.com/docs/art/modeling/material-reference), [Texture specifications](https://create.roblox.com/docs/art/modeling/texture-specifications); the 2023-08-29 version of the PBR page in [Roblox/creator-docs](https://github.com/Roblox/creator-docs) ("default value to 0.0 if a metalness map is not present").
- [MeshPart class](https://create.roblox.com/docs/reference/engine/classes/MeshPart), [Meshes](https://create.roblox.com/docs/parts/meshes) and [RenderFidelity](https://create.roblox.com/docs/reference/engine/enums/RenderFidelity): 250 and 500 stud levels.
- [Camera class](https://create.roblox.com/docs/reference/engine/classes/Camera) (FOV, FieldOfViewMode, Focus, NearPlaneZ, orthographic properties, ViewStretch) and [FieldOfViewMode](https://create.roblox.com/docs/reference/engine/enums/FieldOfViewMode).
- [Light sources](https://create.roblox.com/docs/effects/light-sources), [Light](https://create.roblox.com/docs/reference/engine/classes/Light), [PointLight](https://create.roblox.com/docs/reference/engine/classes/PointLight), [SpotLight](https://create.roblox.com/docs/reference/engine/classes/SpotLight), [BasePart](https://create.roblox.com/docs/reference/engine/classes/BasePart) (CastShadow, Transparency).
- [Customize global lighting](https://create.roblox.com/docs/tutorials/curriculums/core/building/customize-global-lighting) (Island Jump), [Construct your world](https://create.roblox.com/docs/tutorials/curriculums/environmental-art/construct-your-world) ("Studio begins every game with Soft"), [Enhance outdoor environments](https://create.roblox.com/docs/tutorials/use-case-tutorials/lighting/enhance-outdoor-environments) (default ambients 70, 70, 70; skybox lower hemisphere).
- [Free camera mode](https://create.roblox.com/docs/workspace/camera/free-camera) and [Thumbnails](https://create.roblox.com/docs/production/publishing/thumbnails).
- API dump v0.746 class defaults: [MaximumADHD/Roblox-Client-Tracker](https://github.com/MaximumADHD/Roblox-Client-Tracker) `Full-API-Dump.json`.

Roblox announcements and staff posts (DevForum):
- [Future Is Bright: Phase 1 - Studio beta](https://devforum.roblox.com/t/182687), 2018-10-03 (zeuxcg): HDR, tone mapper, voxel engine.
- [Future Is Bright: Phase 1 Released](https://devforum.roblox.com/t/207935), 2018-12-03 (zeuxcg): linear-space HDR, Brightness 1 → 2, Bloom threshold 1.5 to 2.5.
- [Future Is Bright: Phase 2 - Studio beta](https://devforum.roblox.com/t/269370), 2019-04-18: ShadowMap, ShadowSoftness, CastShadow, quality-dependent shadow distance.
- [Future Is Bright: Phase 2 Released, post 111](https://devforum.roblox.com/t/278531/111), 2019-05-21 (zeuxcg): toe / linear / shoulder curve.
- [Future Is Bright: Phase 2.5 Released](https://devforum.roblox.com/t/429543), 2020-01-10: PBR, IBL, EnvironmentDiffuse/SpecularScale 0 to 1.
- [Future is Bright Phase 3 Released](https://devforum.roblox.com/t/878634), 2020-11-19: Future, per-pixel local lights, costs.
- [Indoor Dynamic Environment Maps Beta](https://devforum.roblox.com/t/1115802), 2021-03-17.
- [New Studio Template - Baseplate 2021](https://devforum.roblox.com/t/1127446), 2021-03-24.
- [Compatibility Lighting becomes Retro Tone Mapping](https://devforum.roblox.com/t/3128560), 2024-08-21 (updated to 2024-10-01).
- [Unified Lighting](https://devforum.roblox.com/t/3401512), 2025-01-21, fully live 2025-07-23.
- [ShadowSoftness under Soft](https://devforum.roblox.com/t/3509181), staff reply 2025-04-11.
- [Culling distance and Camera.Focus](https://devforum.roblox.com/t/2079173), staff reply 2023-06-28.
- [Setting Camera.Focus does not render much around the focus](https://devforum.roblox.com/t/3250370), 2024-11-07 (staff 2024-11-14), and [lighting quality now follows Focus](https://devforum.roblox.com/t/3709654), 2025-06-13.
- [Texture with Complex MeshPart](https://devforum.roblox.com/t/2925144), staff reply 2024-06-04: use AlphaMode Transparency for depth-correct cut-outs.
- [Orthographic Camera Studio Beta](https://devforum.roblox.com/t/4966772), 2026-10-30 (staff replies 2026-11-02).
- [Minimum draw distance 500 studs](https://devforum.roblox.com/t/4977292), 2026-11-05.

Community (DevForum and open source):
- [Skies are unusably dark](https://devforum.roblox.com/t/2890103) (Elttob), 2024-03-25: sky 1.0 → 223; 2025-02 replies on Retro.
- [Make ColorCorrectionEffect unclipped](https://devforum.roblox.com/t/2961693) (Elttob), 2024-05-08.
- [Code behind roblox tonemapper?](https://devforum.roblox.com/t/4423779), 2026-02-22: no published values.
- [ColorShift_Bottom non-functional on ShadowMap and Future](https://devforum.roblox.com/t/2340429), 2023-05-17, still open 2026-10-14.
- [Lighting no longer casting through 0.75 transparency](https://devforum.roblox.com/t/620040), 2020-06-10; [Make invisible decal cast a shadow?](https://devforum.roblox.com/t/1689185), 2022-03-04; [decal shadows and CastShadow](https://devforum.roblox.com/t/279989), 2019-05-14; [Hacky Transparent Shadows](https://devforum.roblox.com/t/1789151), 2022-05-12.
- [SurfaceAppearance Transparency "draws proper shadows"](https://devforum.roblox.com/t/1675194), 2022-02-22.
- [Shadow quality dropping over long distances](https://devforum.roblox.com/t/1518058), 2021-10-21; [Shadows disappearing on leaves](https://devforum.roblox.com/t/3593769), 2025-04-04; [SurfaceAppearance and base material specularity](https://devforum.roblox.com/t/2805864), 2024-01-23.
- [Sun direction formula question](https://devforum.roblox.com/t/3594002) (2025) and [FORMULA ... to Sun Direction](https://devforum.roblox.com/t/3921848), 2025-09-06.
- [Nevermore SunPositionUtils](https://github.com/Quenty/NevermoreEngine/blob/main/src/sunpositionutils/src/Shared/SunPositionUtils.lua) and the reverse-engineered [lighting.md](https://raw.githubusercontent.com/iryl1/RBX_DOCUMENTATIONS/c0db57fedf0540db2cd9eb65404ad258c3e21295/lighting.md): sun formula and time-of-day colour curves.
- [Building and Showcase TIPS](https://devforum.roblox.com/t/639045) (AerialsAbove), 2020-06-22; [Map Design and Scene Building](https://devforum.roblox.com/t/709866) (Ahlvie), 2020-08-06; [Which lighting style for cartoon maps](https://devforum.roblox.com/t/643528), 2020-06-25; [Lighting Settings For Cartoony Style](https://devforum.roblox.com/t/2167959), 2023-01-28.

Project data: `docs/style/lessons/cottage.md` (measured sun direction and Studio colours, 2026-11-06).
