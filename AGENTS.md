# AGENTS.md

## Project

Blender add-on **ProportionChecker**. Spec lives in `prompt.txt` (Russian) and is the
source of truth. Package layout:

- `proportion_checker/core.py` — pure logic (grid shape/layout/axes, proportions,
  directory scan); no `bpy`, unit-testable.
- `proportion_checker/operators.py` — `PC_OT_BuildGrid`, `PC_OT_Compute`,
  `PC_OT_CopyTarget`, purge and shading helpers.
- `proportion_checker/ui.py` — `PC_Properties` (Scene) and the sidebar `PC_PT_Main`.
- `proportion_checker/__init__.py` — `bl_info` and idempotent `register`/`unregister`.

Functionality:

1. Load a folder path, scan it for raster images.
2. Build a grid of planes (collection `"Reference"`), one plane per image, centered on
   the world origin, filled row by row. Collection is **non-selectable** and the view
   faces the grid perpendicularly, filling the viewport.
3. Compute target real sizes via proportions and show them in the UI; the result can be
   copied to the clipboard.

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
- Dev-run from a Text Editor buffer (Run Script) sets `__file__` to a fake path like
  `/__init__.py` even when the text was opened from disk, so the package is located via
  `_find_package_root()`: it walks up from `__file__`'s dir, `os.getcwd()`, the current
  `.blend` file, and every `bpy.data.texts` buffer's `filepath`, looking for a dir
  containing `proportion_checker/__init__.py`, then adds it to `sys.path`. A clear
  `ImportError` is raised if the package isn't discoverable.

## Spec facts easy to get wrong (from prompt.txt)

- Grid shape: `cols = ceil(sqrt(N))`, `rows = ceil(N / cols)`.
  Sanity check: 4→2x2, 5→3x2, 7→3x3, 9→3x3.
- Plane height = 1 m (default); width keeps the image aspect ratio.
- One dedicated material per plane; the image is assigned to **Base Color**.
- All planes live in a single collection named exactly `"Reference"`.
- Scene shading: Solid mode with texture display.
- The `"Reference"` collection is **non-selectable**: Blender 5 has **no
  `LayerCollection.restrict_select`**, so it is implemented per-object as
  `obj.hide_select = True` (set on every plane after the build).
- After building, the view is set **perpendicular to the grid** filling the viewport:
  `region_3d.view_perspective = 'ORTHO'` + `view3d.view_axis` (`AXIS_VIEW = {"X":
  "RIGHT", "Y": "FRONT", "Z": "TOP"}`) + `view3d.view_selected`, wrapped in a
  `context.temp_override(window=..., screen=..., area=..., region=...)`. Files without
  a matching window (extra screens) are skipped; headless mode (no window) skips
  framing entirely. `view_selected` must run while planes are still selectable, so
  hide_select is applied *after* framing.

## UI (exact from spec)

- Panel in the 3D View sidebar: `bl_space_type = 'VIEW_3D'`, `bl_region_type = 'UI'`.
- Directory path input field.
- Picker for the base plane the grid is built on.
- 2×2 numeric layout (mirroring `prompt.txt`):
  row 1: reference size on image / reference size real · row 2: target size on image /
  target size real. The **target size real** cell (row 2, col 2) is **read-only**.
- One button computes target size real by proportions.
- A copy button (`PC_OT_CopyTarget`, `pc.copy_target`, icon `COPYDOWN`) writes the
  target size real to `context.window_manager.clipboard`. Clipboard content is only
  observable in a GUI session; background mode ignores writes.