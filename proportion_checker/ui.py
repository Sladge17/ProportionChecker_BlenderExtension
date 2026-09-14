import os

import bpy

from .core import compute_target_real, scan_directory


def _count_images(path):
    if not path:
        return 0
    try:
        return len(scan_directory(path))
    except (NotADirectoryError, OSError):
        return 0


class PC_Properties(bpy.types.PropertyGroup):
    directory: bpy.props.StringProperty(
        name="Директория", subtype="DIR_PATH", default=""
    )
    plane_axis: bpy.props.EnumProperty(
        name="Направление нормали",
        description="Ось, вдоль которой направлена нормаль плоскостей сетки",
        default="X",
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
    )
    gap_h: bpy.props.FloatProperty(
        name="По горизонтали",
        description="Расстояние между плоскостями по горизонтали",
        default=0.0,
        min=0.0,
        unit="LENGTH",
    )
    gap_v: bpy.props.FloatProperty(
        name="По вертикали",
        description="Расстояние между плоскостями по вертикали",
        default=0.0,
        min=0.0,
        unit="LENGTH",
    )
    ref_size_img: bpy.props.FloatProperty(
        name="Опорный размер на изображении", default=1.0
    )
    ref_size_real: bpy.props.FloatProperty(
        name="Опорный размер, реальный", default=1.0
    )
    target_size_img: bpy.props.FloatProperty(
        name="Целевой размер на изображении", default=1.0
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
        box.label(text="Расстояние между плоскостями:")
        row = box.row(align=True)
        row.prop(props, "gap_h")
        row.prop(props, "gap_v")
        box.label(text="Направление нормали:")
        row = box.row(align=True)
        row.prop_enum(props, "plane_axis", "X")
        row.prop_enum(props, "plane_axis", "Y")
        row.prop_enum(props, "plane_axis", "Z")
        box.operator("pc.build_grid", text="Построить сетку", icon="IMPORT")

        box = layout.box()
        box.label(text="Пропорции", icon="DRIVER_DISTANCE")
        self._draw_table(box, props)
        box.operator("pc.compute", text="Вычислить", icon="PLAY")

    def _draw_table(self, box, props):
        row = box.row(align=True)
        row.label(text="")
        row.label(text="На изображении")
        row.label(text="Реальный")

        row = box.row(align=True)
        row.label(text="Опорный")
        row.prop(props, "ref_size_img", text="")
        row.prop(props, "ref_size_real", text="")

        row = box.row(align=True)
        row.label(text="Целевой")
        row.prop(props, "target_size_img", text="")
        ro = row.row(align=True)
        ro.enabled = False
        ro.prop(props, "target_size_real", text="")
        row.operator("pc.copy_target", text="", icon="COPYDOWN")