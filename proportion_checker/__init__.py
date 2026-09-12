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


def _modules():
    try:
        from . import operators, ui
    except ImportError:
        import importlib
        import os
        import sys

        parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent not in sys.path:
            sys.path.insert(0, parent)
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


def register():
    import bpy

    operators, ui = _modules()

    _register_class(ui.PC_Properties)
    if not hasattr(bpy.types.Scene, "pc"):
        bpy.types.Scene.pc = bpy.props.PointerProperty(type=ui.PC_Properties)
    for cls in (
        operators.PC_OT_BuildGrid,
        operators.PC_OT_Compute,
        operators.PC_OT_SelectDirectory,
        ui.PC_PT_Main,
    ):
        _register_class(cls)


def unregister():
    import bpy

    operators, ui = _modules()

    for cls in reversed(
        (
            operators.PC_OT_BuildGrid,
            operators.PC_OT_Compute,
            operators.PC_OT_SelectDirectory,
            ui.PC_PT_Main,
        )
    ):
        _unregister_class(cls)
    if hasattr(bpy.types.Scene, "pc"):
        del bpy.types.Scene.pc
    _unregister_class(ui.PC_Properties)


if __name__ == "__main__":
    register()