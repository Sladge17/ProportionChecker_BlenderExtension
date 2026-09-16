import os

import bpy

from .core import compute_target_real, scan_directory
from .operators import build_grid


def _rebuild_grid(self, context):
    scene = getattr(context, "scene", None)
    if scene is None:
        return
    try:
        build_grid(context)
    except Exception:
        pass


def _rebuild_grid_framing(self, context):
    scene = getattr(context, "scene", None)
    if scene is None:
        return
    try:
        build_grid(context, frame=True)
    except Exception:
        pass


def _count_images(path):
    if not path:
        return 0
    try:
        return len(scan_directory(path))
    except (NotADirectoryError, OSError):
        return 0


class PC_Properties(bpy.types.PropertyGroup):
    directory: bpy.props.StringProperty(
        name="Директория", subtype="DIR_PATH", default="", update=_rebuild_grid_framing
    )
    plane_axis: bpy.props.EnumProperty(
        name="Направление нормали",
        description="Ось, вдоль которой направлена нормаль плоскостей сетки",
        default="X",
        update=_rebuild_grid_framing,
        items=(
            ("X", "X", "Нормаль вдоль оси X"),
            ("Y", "Y", "Нормаль вдоль оси Y"),
            ("Z", "Z", "Нормаль вдоль оси Z"),
        ),
    )
    plane_height: bpy.props.FloatProperty(
        name="Высота плоскости",
        default=1.0,
        min=0.0001,
        unit="LENGTH",
        update=_rebuild_grid,
    )
    gap_h: bpy.props.FloatProperty(
        name="По горизонтали",
        description="Расстояние между плоскостями по горизонтали",
        default=0.0,
        min=0.0,
        unit="LENGTH",
        update=_rebuild_grid,
    )
    gap_v: bpy.props.FloatProperty(
        name="По вертикали",
        description="Расстояние между плоскостями по вертикали",
        default=0.0,
        min=0.0,
        unit="LENGTH",
        update=_rebuild_grid,
    )
    offset: bpy.props.FloatProperty(
        name="Смещение вдоль нормали",
        description="Смещение всей сетки вдоль выбранного направления нормали",
        default=0.0,
        unit="LENGTH",
        update=_rebuild_grid,
    )
    ref_size_img: bpy.props.FloatProperty(
        name="Опорный размер на изображении", default=0.0, min=0.0
    )
    ref_size_real: bpy.props.FloatProperty(
        name="Опорный размер, реальный", default=0.0, min=0.0
    )
    target_size_img: bpy.props.FloatProperty(
        name="Целевой размер на изображении", default=0.0, min=0.0
    )

    def get_target_size_real(self):
        try:
            return compute_target_real(
                self.ref_size_img, self.ref_size_real, self.target_size_img
            )
        except ValueError:
            return 0.0

    target_size_real: bpy.props.FloatProperty(
        name="Целевой размер, реальный",
        description="Вычисляется автоматически (только для чтения)",
        get=get_target_size_real,
    )


class PC_PT_Main(bpy.types.Panel):
    bl_label = "ProportionChecker"
    bl_idname = "PC_PT_Main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Reference"

    @classmethod
    def poll(cls, context):
        return context.scene is not None

    def draw(self, context):
        props = context.scene.pc
        layout = self.layout

        box = layout.box()
        box.label(text="Исходные данные", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.prop(props, "directory", text="")
        box.label(text=f"Изображений: {_count_images(props.directory)}")

        box = layout.box()
        box.label(text="Сетка плоскостей", icon="GRID")
        box.prop(props, "plane_height")
        box.label(text="Направление нормали:")
        row = box.row(align=True)
        row.prop_enum(props, "plane_axis", "X")
        row.prop_enum(props, "plane_axis", "Y")
        row.prop_enum(props, "plane_axis", "Z")
        box.label(text="Расстояние между плоскостями:")
        row = box.row(align=True)
        row.prop(props, "gap_h")
        row.prop(props, "gap_v")
        box.prop(props, "offset")

        box = layout.box()
        box.label(text="Пропорции", icon="DRIVER_DISTANCE")
        self._draw_table(box, props)
        box.operator("pc.copy_target", text="Скопировать в буфер", icon="COPYDOWN")

    def _draw_table(self, box, props):
        row = box.row(align=True)

        col_label = row.column(align=True)
        col_label.label(text="")
        col_label.label(text="Опорный")
        col_label.label(text="Целевой")

        col_img = row.column(align=True)
        col_img.label(text="На изображении")
        col_img.prop(props, "ref_size_img", text="")
        col_img.prop(props, "target_size_img", text="")

        col_real = row.column(align=True)
        col_real.label(text="Реальный")
        col_real.prop(props, "ref_size_real", text="")
        ro = col_real.row()
        ro.alignment = "CENTER"
        ro.label(text=f"{props.target_size_real:.6g}")