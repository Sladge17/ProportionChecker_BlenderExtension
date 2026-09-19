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
2. Build a grid of planes (collection `"ReferenceImages"`), one plane per image, centered on
   the world origin, filled row by row. The view faces the grid perpendicularly,
   filling the viewport.
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
- Configurable distance between planes, **separate horizontal and vertical**
  (`pc.gap_h`, `pc.gap_v` in metres, both default to 0). Layout in `core.grid_layout(
  widths, plane_height, gap_h, gap_v)`: in-row step = (w_i+w_{i+1})/2 + gap_h,
  row step = plane_height + gap_v; grid stays centered on the origin.
- Configurable grid offset **along the chosen normal axis only** (`pc.offset`,
  metres, default 0, may be negative): `grid_to_world(u, v, axis, offset)` adds
  `offset` onto the `axis` world component; u/v mapping unchanged.
- Grid columns (u) must follow the plane's **width** direction and rows (v) its
  **height** direction in world space *after* the `AXIS_ROTATION` is applied
  (`AXIS_MAP` = {"Z": ("X","Y"), "X": ("Y","Z"), "Y": ("Z","X")}). The width/height
  (via `core.axis_basis(axis)`, pure R = Rz*Ry*Rx) drive the perpendicular view: width
  left-right, height up-down, normal toward the viewer.
- Plane normals (front face with the texture) always point along the **positive** world
  axis: X:+X, Y:+Y, Z:+Z (`AXIS_ROTATION` = {"X": (π/2, 0, π/2),
  "Y": (π/2, 3π/2, π), "Z": (0, 0, 0)}). Be careful: Blender object Euler semantics
  differ from a naive rotation chain — validate every new euler against
  `obj.matrix_world` (or `axis_basis`) in live Blender.
- One dedicated material per plane; the image is assigned to **Base Color**.
- All planes live in a single collection named exactly `"ReferenceImages"`.
- The planes are **selectable** but transform-locked: each object gets
  `lock_location = lock_rotation = lock_scale = (True, True, True)` (movement,
  rotation and scaling via the UI are disabled). In Blender 5.x an object with
  all transform axes locked natively hides the transform manipulator under
  select-style tools (validated empirically: toggling
  `show_gizmo_object_translate/rotate/scale` and `show_gizmo_tool` on a locked
  plane changes nothing in the viewport under `builtin.select_box`). A transform
  *tool* (e.g. `builtin.rotate`) can still force its tool gizmo on, so to make
  the gizmo behaviour uniform a `depsgraph_update_post` handler (registered in
  `__init__.py`, `_gizmo_handler`) calls `_sync_gizmos()`: while the **active
  object is a grid plane** (marked with `pc.image_path`) it sets
  `space.show_gizmo_tool = False` and saves/restores the per-viewport value
  otherwise. **Exception:** while the active tool for that viewport is the
  Measure tool (`builtin.measure`, checked via `_measure_tool_active`), the tool
  gizmo is kept **visible** (otherwise the Measure tool raises "Gizmos hidden in
  this view").
  - Tool switches do **not** invalidate the dependency graph, so the sync would
    otherwise go stale (e.g. Measure shown → plane stays active → back to a
    transform tool → its gizmo lingers). A `bpy.app.timers` poll (`_gizmo_poll`,
    every 0.01 s, only in GUI mode, registered in `register()`/`unregister()`;
    note `bpy.app.timers.register` may return `None` — store/re-check via
    `bpy.app.timers.is_registered`) keeps `_sync_gizmos()` correct across tool
    switches. `_sync_gizmos()` and `_measure_tool_active()` live in `__init__.py`.
  - `WorkSpace.tools` yields only the **currently active** tool, not the full
    tool set — treat it as a single-item probe.
  - Comparing spaces/screens by `is` fails because RNA returns fresh wrappers —
    use `as_pointer()` equality. A screen with no owning window (extra
    workspaces) must be skipped when overriding context.
- Scene shading: Solid mode with texture display.
- After building, the view is set **perpendicular to the grid** filling the viewport:
  a custom ORTHO camera — `region_3d.view_rotation` derived from `axis_basis(axis)`
  (`q = Matrix((width, height, normal)).transposed().to_quaternion()`, camera looks
  along −normal so the front face faces the view, width on screen-right, height up) +
  `region_3d.view_location = (0,0,0)` + `view3d.view_selected`, wrapped in a
  `context.temp_override(window=..., screen=..., area=..., region=...)`. Screens without
  a matching window (extra workspaces) are skipped; headless mode (no window) skips
  framing entirely.

## UI (exact from spec)

- Panel in the 3D View sidebar: `bl_space_type = 'VIEW_3D'`, `bl_region_type = 'UI'`.
- Directory path input field.
- Picker for the base plane the grid is built on.
- The grid is built **automatically**: `PC_Properties` layout fields (`directory`,
  `plane_axis`, `plane_height`, `gap_h`, `gap_v`, `offset`) carry an `update=`
  callback that calls `operators.build_grid(context)`. There is **no build button**.
  `build_grid` is a no-op (existing grid kept) when the path is empty, missing or
  contains no rasters. **View framing happens on `plane_axis` change and on
  `directory` change** (`ui._rebuild_grid_framing` → `build_grid(frame=True)`); the
  other fields (`plane_height`, `gap_h`, `gap_v`, `offset`) rebuild without touching
  the camera.
- 2×2 numeric layout (mirroring `prompt.txt`):
  row 1: reference size on image / reference size real · row 2: target size on image /
  target size real. The **target size real** cell (row 2, col 2) is **read-only** and
  live-computed by a getter (proportions), so there is no separate compute button.
- A copy button (`PC_OT_CopyTarget`, `pc.copy_target`, icon `COPYDOWN`) writes the
  target size real to `context.window_manager.clipboard`. It replaces the former
  "Compute" button (a full-width "Copy to Clipboard" button; there is no small
  copy icon next to the target cell). Clipboard content is only observable in a GUI
  session; background mode ignores writes.