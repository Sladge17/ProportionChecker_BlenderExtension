# AGENTS.md

## Project

Blender add-on **ProportionChecker**. Spec lives in `prompt.txt` (Russian) and is the
source of truth; the working tree currently has no add-on code yet. Functionality:

1. Load a folder path, scan it for raster images.
2. Build a grid of planes (collection `"Reference"`), one plane per image, centered on
   the world origin, filled row by row.
3. Compute target real sizes via proportions and show them in the UI.

## Runtime / how to run code

- Code runs in Blender's embedded Python (`bpy`) — never run add-on code with a plain
  `python` interpreter.
- Target Blender 5.0+. Installed here: Blender 5.2.1 (snap, `/snap/bin/blender`).
  Re-check deprecations before relying on old `.bpy` APIs.
- A live Blender is connected via the Blender MCP server — use its tools
  (`execute_blender_code`, scene/object inspection, screenshots) to verify bpy code and
  scene state; it's much faster than restarting headless runs.
- Headless check: `blender --background --python-expr "..."`.
- Add-on must be installable via `Preferences > Add-ons` (bl_info + register/unregister).

## Spec facts easy to get wrong (from prompt.txt)

- Grid shape: `cols = ceil(sqrt(N))`, `rows = ceil(N / cols)`.
  Sanity check: 4→2x2, 5→3x2, 7→3x3, 9→3x3.
- Plane height = 1 m (default); width keeps the image aspect ratio.
- One dedicated material per plane; the image is assigned to **Base Color**.
- All planes live in a single collection named exactly `"Reference"`.
- Scene shading: Solid mode with texture display.

## UI (exact from spec)

- Panel in the 3D View sidebar: `bl_space_type = 'VIEW_3D'`, `bl_region_type = 'UI'`.
- Directory path input field.
- Picker for the base plane the grid is built on.
- 2×2 numeric layout (mirroring `prompt.txt`):
  row 1: reference size on image / reference size real · row 2: target size on image /
  target size real. The **target size real** cell (row 2, col 2) is **read-only**.
- One button computes target size real by proportions.