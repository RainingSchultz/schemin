# Blender kit

The Blender code is `foundation/blender/`. Load this page only for the blender route.

Use Blender when the scene needs:

1. Constructive solid geometry (boolean cutaways, extruded microfluidic tubes, bevels, twisted helices).
2. Participating volumes or fog (laser beams in scattering media, gas clouds).
3. Multi-bounce photoreal glass or liquid caustics (Cycles).

Render with `blender -b --factory-startup -P figure/render3d.py`. Modules, each with a demo in `foundation/demo/render3d_*.py`:

- `scene.py` — photonics: chip, fibre, lens, beam.
- `bio3d.py` — cells, tissue, organoids, membranes, DNA, proteins.
- `device3d.py` — layer stacks, crystals, electrodes, molecules from SMILES.
- `apparatus3d.py` — glassware, instruments, landscapes.
- `mol3d.py` — 3D molecules. Set `MOL3D_PYTHON` when RDKit lives in another interpreter.

Labels, math, and panel letters stay in the SVG. Place the PNG with `L.image` and the anchor JSON. Photographic words ("photoreal", "photographic", "realistic glass") select the photographic look and `3d=render`. Otherwise use illustration mode so the render matches the flat panels. The full rules are step 3 of `reference/process.md`.
