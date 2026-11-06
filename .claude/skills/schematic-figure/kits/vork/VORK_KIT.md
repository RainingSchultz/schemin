# vork 3D & Shader Kit for Scientific Schematics

## Core Principle: 3D Apparatus & Shaders in `vork`, Typography & Callouts in SVG
NEVER render text labels, math symbols, callout lines, or panel letters ("a", "b", "c") inside `vork`.
1. Build and render the 3D physical setup or shader field in `vork` as a high-resolution PNG.
2. Export 2D screen-space coordinates `(svg_x, svg_y)` of named 3D landmarks using `kits/vork/scene_builder.py`.
3. Composite the rendered PNG into the `schematic-figure` SVG canvas and attach crisp vector arrows, math labels, and colorbars to the projected `(svg_x, svg_y)` anchors.

## CLI Discovery Rule
Before authoring raw `vork` JSON or custom Slang hooks with unfamiliar fields, run:
- `vork help` (overview & quickstart)
- `vork help field <field_name>` (exact schema for a node/material property)
- `vork help programs --all` (exact Slang hook signatures for the installed version)

## Workflow & Render Profiles by Depth

Match `schematic-figure` depth levels to `vork` render profiles:

### Phase 1: Layout & Camera Previs (Mandatory for all depths)
Generate `figure/vork_scene.json` via `scene_builder.py` and run:
`vork render figure/vork_scene.json --profile std/previs --out figure/out/previs.png`
Inspect `previs.png` to verify:
- No objects are clipped by the camera frustum.
- The apparatus fills 65–80% of the frame with clean negative space for SVG labels.
- Key components do not occlude each other along the camera view vector.

### Phase 2: Lighting & Shader Verification (`draft` depth stops here)
Once framing is locked, test ray-traced lighting and Slang shaders:
`vork render figure/vork_scene.json --profile std/draft --out figure/out/draft.png`
If specular highlights are blown out or shadows obscure an important mechanism, adjust light `energy` and `translation` before moving on.

### Phase 3: Publication Render (`standard` and `full` depth)
Render at 2x target print resolution (e.g., 2100px wide for an 89 mm single-column figure at 600 DPI):
`vork render figure/vork_scene.json --profile std/final --set samples=32 --out figure/out/render_3d.png`
*Note:* Default `std/final` uses 8 samples + OIDN denoising. For fine lattices, sharp wave contours, or spectral highlights, always pass `--set samples=32` to prevent denoiser mottling.

## Guardrails (vork Research Preview Limits)
- **No Participating Volumes/Fog:** `vork` currently ignores fog and participating volumes. For laser beams or optical paths, either use a semi-transparent emissive cylinder mesh in `vork`, draw the beam as a vector gradient overlay in the SVG compositor, or switch to the `blender` kit.
- **No Constructive Solid Geometry (Booleans):** `vork` does not have boolean cutaway modifiers. Assemble scenes from primitives (`sphere`, `grid`, `cone`, `cylinder`, `box`), external meshes, or Slang shaders (`programs/`).

Shader paths stored in the scene JSON are relative to the working directory. The default in `add_wave_or_potential_plane` is `kits/vork/programs/wave_potential_field.slang`. Run `vork render` from the skill repository, or pass an absolute `program_path`. `scene_builder.py` needs NumPy.
