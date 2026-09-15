bl_info = {
    "name": "ProportionChecker",
    "author": "ProportionChecker",
    "version": (0, 1, 0),
    "blender": (5, 0, 0),
    "location": "3D View > Sidebar > Reference",
    "description": (
        "Строит сетку плоскостей с изображениями из выбранной директории "
        "и вычисляет целевые размеры методом пропорций"
    ),
    "category": "Mesh",
}


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
                "Не удалось найти пакет 'proportion_checker'. Запускайте "
                "__init__.py из папки пакета или установите аддон через "
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
_GIZMO_SAVED = {}


def _gizmo_handler(scene, depsgraph):
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
                space.show_gizmo_tool = False
            elif key in _GIZMO_SAVED:
                space.show_gizmo_tool = _GIZMO_SAVED.pop(key)


def register():
    global _GIZMO_HANDLER
    import bpy

    operators, ui = _modules()

    _register_class(ui.PC_Properties)
    if not hasattr(bpy.types.Scene, "pc"):
        bpy.types.Scene.pc = bpy.props.PointerProperty(type=ui.PC_Properties)
    for cls in (
        operators.PC_OT_BuildGrid,
        operators.PC_OT_Compute,
        operators.PC_OT_CopyTarget,
        ui.PC_PT_Main,
    ):
        _register_class(cls)

    if _GIZMO_HANDLER is None:
        _GIZMO_HANDLER = bpy.app.handlers.persistent(_gizmo_handler)
        bpy.app.handlers.depsgraph_update_post.append(_GIZMO_HANDLER)


def unregister():
    global _GIZMO_HANDLER
    import bpy

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