import os

import bpy

from .core import (
    AXIS_ROTATION,
    compute_target_real,
    grid_layout,
    grid_to_world,
    plane_width,
    scan_directory,
)

PC_MARK = "pc.image_path"


def _load_image(filepath):
    img = bpy.data.images.load(filepath, check_existing=True)
    try:
        img.colorspace_settings.name = "sRGB"
    except Exception:
        pass
    img[PC_MARK] = filepath
    return img


def _plane_mesh(name, width, height):
    mesh = bpy.data.meshes.new(name)
    hw, hh = width / 2.0, height / 2.0
    verts = [(-hw, -hh, 0.0), (hw, -hh, 0.0), (hw, hh, 0.0), (-hw, hh, 0.0)]
    mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
    mesh.update()
    uv = mesh.uv_layers.new(name="UVMap")
    for li, (u, v) in enumerate([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]):
        uv.data[li].uv = (u, v)
    return mesh


def _build_material(name, image):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    ng = mat.node_tree
    bsdf = ng.nodes.get("Principled BSDF")
    tex = ng.nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.extension = "CLIP"
    if bsdf is not None and "Base Color" in bsdf.inputs:
        ng.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    mat[PC_MARK] = True
    return mat


def _ensure_collection(context):
    col = bpy.data.collections.get("Reference")
    if col is None:
        col = bpy.data.collections.new("Reference")
    if context.scene.collection is not None and col.name not in context.scene.collection.children:
        context.scene.collection.children.link(col)
    return col


def _purge_addon_data():
    for obj in list(bpy.data.objects):
        if PC_MARK in obj:
            bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        if PC_MARK in mesh and mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    for mat in list(bpy.data.materials):
        if PC_MARK in mat and mat.users == 0:
            bpy.data.materials.remove(mat)
    bpy.context.view_layer.update()


def _set_solid_texture_shading():
    for screen in bpy.data.screens:
        for area in screen.areas:
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    space.shading.type = "SOLID"
                    space.shading.color_type = "TEXTURE"


AXIS_VIEW = {"X": "RIGHT", "Y": "FRONT", "Z": "TOP"}


def _select_objects(objects):
    for obj in objects:
        obj.select_set(True)
        obj.hide_set(False)
    if objects:
        bpy.context.view_layer.objects.active = objects[0]


def _frame_view_perpendicular(axis):
    view_type = AXIS_VIEW[axis]
    windows = []
    for wm in bpy.data.window_managers:
        windows.extend(wm.windows)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            regions = [r for r in area.regions if r.type == "WINDOW"]
            spaces = [s for s in area.spaces if s.type == "VIEW_3D"]
            if not regions or not spaces:
                continue
            win = next((w for w in windows if w.screen == screen), None)
            if win is None:
                continue
            try:
                with bpy.context.temp_override(
                    window=win, screen=screen, area=area, region=regions[0]
                ):
                    spaces[0].region_3d.view_perspective = "ORTHO"
                    bpy.ops.view3d.view_axis(type=view_type)
                    bpy.ops.view3d.view_selected()
            except Exception:
                pass


class PC_OT_BuildGrid(bpy.types.Operator):
    bl_idname = "pc.build_grid"
    bl_label = "Построить сетку"
    bl_description = "Сканирует директорию и строит сетку плоскостей с изображениями"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return context.scene is not None

    def execute(self, context):
        props = context.scene.pc
        path = props.directory
        if not path:
            self.report({"ERROR"}, "Укажите директорию с изображениями")
            return {"CANCELLED"}
        try:
            files = scan_directory(path)
        except NotADirectoryError:
            self.report({"ERROR"}, f"Директория не существует: {path}")
            return {"CANCELLED"}
        if not files:
            self.report({"ERROR"}, "В директории не найдено растровых изображений")
            return {"CANCELLED"}

        _purge_addon_data()
        col = _ensure_collection(context)

        planes = []
        skipped = 0
        for fp in files:
            try:
                img = _load_image(fp)
                w, h = img.size
                width = plane_width(w, h, props.plane_height)
            except Exception as exc:
                skipped += 1
                self.report({"WARNING"}, f"Пропущено {os.path.basename(fp)}: {exc}")
                continue
            planes.append((fp, img, width))

        if not planes:
            self.report({"ERROR"}, "Не удалось загрузить ни одного изображения")
            return {"CANCELLED"}

        layouts = grid_layout([p[2] for p in planes], plane_height=props.plane_height)
        created = []
        for item, (fp, img, width) in zip(layouts, planes):
            stem = os.path.splitext(os.path.basename(fp))[0]
            mesh = _plane_mesh(stem, width, props.plane_height)
            mesh[PC_MARK] = True
            obj = bpy.data.objects.new(stem, mesh)
            obj.rotation_euler = AXIS_ROTATION[props.plane_axis]
            obj.location = grid_to_world(item["u"], item["v"], props.plane_axis)
            obj[PC_MARK] = fp
            obj.data.materials.append(_build_material(stem, img))
            col.objects.link(obj)
            created.append(obj)

        _set_solid_texture_shading()
        bpy.context.view_layer.update()

        _select_objects(created)
        _frame_view_perpendicular(props.plane_axis)

        for obj in created:
            obj.hide_select = True
        bpy.context.view_layer.update()

        self.report(
            {"INFO"},
            f"Построено плоскостей: {len(planes)} (пропущено: {skipped})",
        )
        return {"FINISHED"}


class PC_OT_Compute(bpy.types.Operator):
    bl_idname = "pc.compute"
    bl_label = "Вычислить"
    bl_description = "Вычисляет целевой размер (реальный) методом пропорций"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return context.scene is not None

    def execute(self, context):
        props = context.scene.pc
        try:
            value = compute_target_real(
                props.ref_size_img, props.ref_size_real, props.target_size_img
            )
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, f"Целевой реальный размер: {value:.6g}")
        return {"FINISHED"}


class PC_OT_CopyTarget(bpy.types.Operator):
    bl_idname = "pc.copy_target"
    bl_label = "Копировать"
    bl_description = "Копирует целевой реальный размер в буфер обмена"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return context.scene is not None

    def execute(self, context):
        props = context.scene.pc
        try:
            value = compute_target_real(
                props.ref_size_img, props.ref_size_real, props.target_size_img
            )
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        context.window_manager.clipboard = f"{value:g}"
        self.report({"INFO"}, f"Скопировано: {value:g}")
        return {"FINISHED"}