def _find_package_root():
    import os

    def is_package(root):
        return os.path.isdir(os.path.join(root, "proportion_checker")) and os.path.isfile(
            os.path.join(root, "proportion_checker", "__init__.py")
        )

    seeds = [os.path.dirname(os.path.abspath(__file__)), os.getcwd()]
    try:
        import bpy

        if bpy.data.filepath:
            seeds.append(os.path.dirname(os.path.abspath(bpy.data.filepath)))
        for text in bpy.data.texts:
            if text.filepath:
                seeds.append(os.path.abspath(text.filepath))
    except Exception:
        pass

    explored = set()
    for seed in seeds:
        cur = os.path.abspath(seed)
        while cur not in explored:
            explored.add(cur)
            if is_package(cur):
                return cur
            nxt = os.path.dirname(cur)
            if nxt == cur:
                break
            cur = nxt
    return None


def _modules():
    try:
        from . import operators, ui
    except ImportError:
        import importlib
        import sys

        root = _find_package_root()
        if root is None:
            raise ImportError(
                "Could not find the 'proportion_checker' package. Run "
                "__init__.py from the package folder or install the add-on via "
                "Preferences > Add-ons."
            )
        if root not in sys.path:
            sys.path.insert(0, root)
        operators = importlib.import_module("proportion_checker.operators")
        ui = importlib.import_module("proportion_checker.ui")
    return operators, ui


def _register_class(cls):
    import bpy

    try:
        bpy.utils.register_class(cls)
    except ValueError:
        pass


def _unregister_class(cls):
    import bpy

    try:
        bpy.utils.unregister_class(cls)
    except RuntimeError:
        pass


_GIZMO_HANDLER = None
_GIZMO_POLL_HANDLER = None
_GIZMO_POLL_INTERVAL = 0.01
_GIZMO_SAVED = {}


def _measure_tool_active(space):
    import bpy

    sp = space.as_pointer()
    workspaces = []
    for wm in bpy.data.window_managers:
        for win in wm.windows:
            screen = getattr(win, "screen", None)
            ws = getattr(win, "workspace", None)
            if screen is None or ws is None:
                continue
            for area in screen.areas:
                for s in area.spaces:
                    if s.as_pointer() == sp:
                        workspaces.append(ws)
    for ws in workspaces:
        for tool in getattr(ws, "tools", ()):
            if getattr(tool, "space_type", "") != "VIEW_3D":
                continue
            if "measure" in getattr(tool, "idname", ""):
                return True
    return False


def _sync_gizmos():
    import bpy

    active = bpy.context.active_object
    is_plane = active is not None and "pc.image_path" in active
    screen = bpy.context.screen
    if screen is None:
        return

    for area in screen.areas:
        if area.type != "VIEW_3D":
            continue
        for space in area.spaces:
            if space.type != "VIEW_3D":
                continue
            key = space.as_pointer()
            if is_plane:
                if key not in _GIZMO_SAVED:
                    _GIZMO_SAVED[key] = space.show_gizmo_tool
                space.show_gizmo_tool = _measure_tool_active(space)
            elif key in _GIZMO_SAVED:
                space.show_gizmo_tool = _GIZMO_SAVED.pop(key)


def _gizmo_handler(scene, depsgraph):
    _sync_gizmos()


def _gizmo_poll():
    # Switching the active tool does not invalidate the dependency graph, so
    # re-sync from a timer to avoid stale tool-gizmo visibility.
    _sync_gizmos()
    return _GIZMO_POLL_INTERVAL


def register():
    global _GIZMO_HANDLER, _GIZMO_POLL_HANDLER
    import bpy

    operators, ui = _modules()

    _register_class(ui.PC_Properties)
    if not hasattr(bpy.types.Scene, "pc"):
        bpy.types.Scene.pc = bpy.props.PointerProperty(type=ui.PC_Properties)
    for cls in (
        operators.PC_OT_BuildGrid,
        operators.PC_OT_Compute,
        operators.PC_OT_ClearDimensions,
        operators.PC_OT_CopyTarget,
        ui.PC_PT_Main,
    ):
        _register_class(cls)

    if _GIZMO_HANDLER is None:
        _GIZMO_HANDLER = bpy.app.handlers.persistent(_gizmo_handler)
        bpy.app.handlers.depsgraph_update_post.append(_GIZMO_HANDLER)
    if not bpy.app.background and _GIZMO_POLL_HANDLER is None:
        try:
            bpy.app.timers.register(_gizmo_poll, first_interval=_GIZMO_POLL_INTERVAL)
        except ValueError:
            pass
        if bpy.app.timers.is_registered(_gizmo_poll):
            _GIZMO_POLL_HANDLER = _gizmo_poll


def unregister():
    global _GIZMO_HANDLER, _GIZMO_POLL_HANDLER
    import bpy

    if _GIZMO_POLL_HANDLER is not None:
        try:
            if bpy.app.timers.is_registered(_GIZMO_POLL_HANDLER):
                bpy.app.timers.unregister(_GIZMO_POLL_HANDLER)
        except Exception:
            pass
        _GIZMO_POLL_HANDLER = None
    if _GIZMO_HANDLER is not None:
        try:
            bpy.app.handlers.depsgraph_update_post.remove(_GIZMO_HANDLER)
        except ValueError:
            pass
        _GIZMO_HANDLER = None
    _GIZMO_SAVED.clear()

    operators, ui = _modules()

    for cls in reversed(
        (
            operators.PC_OT_BuildGrid,
            operators.PC_OT_Compute,
            operators.PC_OT_ClearDimensions,
            operators.PC_OT_CopyTarget,
            ui.PC_PT_Main,
        )
    ):
        _unregister_class(cls)
    if hasattr(bpy.types.Scene, "pc"):
        del bpy.types.Scene.pc
    _unregister_class(ui.PC_Properties)


if __name__ == "__main__":
    register()