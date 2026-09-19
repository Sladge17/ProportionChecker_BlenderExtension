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
        name="Directory", subtype="DIR_PATH", default="", update=_rebuild_grid_framing
    )
    plane_axis: bpy.props.EnumProperty(
        name="View Direction",
        description="Axis along which the normals of the grid planes point",
        default="X",
        update=_rebuild_grid_framing,
        items=(
            ("X", "X", "Normal along the X axis"),
            ("Y", "Y", "Normal along the Y axis"),
            ("Z", "Z", "Normal along the Z axis"),
        ),
    )
    plane_height: bpy.props.FloatProperty(
        name="Image Height",
        default=1.0,
        min=0.0001,
        unit="LENGTH",
        update=_rebuild_grid,
    )
    gap_h: bpy.props.FloatProperty(
        name="Horizontal",
        description="Horizontal distance between planes",
        default=0.0,
        min=0.0,
        unit="LENGTH",
        update=_rebuild_grid,
    )
    gap_v: bpy.props.FloatProperty(
        name="Vertical",
        description="Vertical distance between planes",
        default=0.0,
        min=0.0,
        unit="LENGTH",
        update=_rebuild_grid,
    )
    offset: bpy.props.FloatProperty(
        name="View Offset",
        description="Offset of the whole grid along the selected normal direction",
        default=0.0,
        unit="LENGTH",
        update=_rebuild_grid,
    )
    ref_size_img: bpy.props.FloatProperty(
        name="Source size on image", default=0.0, min=0.0
    )
    ref_size_real: bpy.props.FloatProperty(
        name="Source size real", default=0.0, min=0.0
    )
    target_size_img: bpy.props.FloatProperty(
        name="Target size on image", default=0.0, min=0.0
    )

    def get_target_size_real(self):
        try:
            return compute_target_real(
                self.ref_size_img, self.ref_size_real, self.target_size_img
            )
        except ValueError:
            return 0.0

    target_size_real: bpy.props.FloatProperty(
        name="Target size real",
        description="Computed automatically (read-only)",
        get=get_target_size_real,
    )


class PC_PT_Main(bpy.types.Panel):
    bl_label = "ProportionChecker"
    bl_idname = "PC_PT_Main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ReferenceTools"

    @classmethod
    def poll(cls, context):
        return context.scene is not None

    def draw(self, context):
        props = context.scene.pc
        layout = self.layout

        box = layout.box()
        box.label(text="Reference Images", icon="FILE_FOLDER")
        row = box.row(align=True)
        row.prop(props, "directory", text="")
        box.label(text=f"Images: {_count_images(props.directory)}")

        box = layout.box()
        box.label(text="Images Grid", icon="GRID")
        box.prop(props, "plane_height")
        box.label(text="View Direction:")
        row = box.row(align=True)
        row.prop_enum(props, "plane_axis", "X")
        row.prop_enum(props, "plane_axis", "Y")
        row.prop_enum(props, "plane_axis", "Z")
        box.label(text="Distance between images:")
        row = box.row(align=True)
        row.prop(props, "gap_h")
        row.prop(props, "gap_v")
        box.prop(props, "offset")

        box = layout.box()
        box.label(text="Dimensions", icon="DRIVER_DISTANCE")
        self._draw_table(box, props)
        box.operator("pc.clear_dimensions", text="Clear", icon="X")
        box.operator("pc.copy_target", text="Copy to Buffer", icon="COPYDOWN")

    def _draw_table(self, box, props):
        row = box.row(align=True)

        col_label = row.column(align=True)
        col_label.label(text="")
        col_label.label(text="Source")
        col_label.label(text="Target")

        col_img = row.column(align=True)
        hdr_img = col_img.row()
        hdr_img.alignment = "CENTER"
        hdr_img.label(text="On image")
        col_img.prop(props, "ref_size_img", text="")
        col_img.prop(props, "target_size_img", text="")

        col_real = row.column(align=True)
        hdr_real = col_real.row()
        hdr_real.alignment = "CENTER"
        hdr_real.label(text="Real")
        col_real.prop(props, "ref_size_real", text="")
        ro = col_real.row()
        ro.alignment = "CENTER"
        ro.label(text=f"{props.target_size_real:.6g}")