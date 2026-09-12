import math
import os
import tempfile
import unittest

from proportion_checker.core import (
    AXIS_MAP,
    AXIS_ROTATION,
    RASTER_EXTENSIONS,
    compute_target_real,
    grid_layout,
    grid_shape,
    grid_to_world,
    plane_width,
    scan_directory,
)


class TestGridShape(unittest.TestCase):
    def test_reference_cases(self):
        for n, expected in ((1, (1, 1)), (4, (2, 2)), (5, (3, 2)), (7, (3, 3)), (9, (3, 3))):
            with self.subTest(n=n):
                self.assertEqual(grid_shape(n), expected)

    def test_non_positive(self):
        self.assertEqual(grid_shape(0), (0, 0))


class TestPlaneWidth(unittest.TestCase):
    def test_aspect(self):
        self.assertAlmostEqual(plane_width(200, 100), 2.0)
        self.assertAlmostEqual(plane_width(100, 100), 1.0)
        self.assertAlmostEqual(plane_width(50, 100), 0.5)

    def test_custom_height(self):
        self.assertAlmostEqual(plane_width(200, 100, plane_height=3.0), 6.0)

    def test_invalid(self):
        for w, h in ((0, 100), (-1, 100), (100, 0), (100, -1)):
            with self.subTest(w=w, h=h):
                with self.assertRaises(ValueError):
                    plane_width(w, h)


class TestGridLayout(unittest.TestCase):
    def test_uniform_2x2(self):
        layout = grid_layout([1.0, 1.0, 1.0, 1.0])
        self.assertEqual(len(layout), 4)
        self.assertEqual([(p["row"], p["col"]) for p in layout], [(0, 0), (0, 1), (1, 0), (1, 1)])
        for p in layout:
            self.assertEqual(p["height"], 1.0)
            self.assertEqual(p["width"], 1.0)
        # центрирование у
        vs = sorted(p["v"] for p in layout)
        self.assertAlmostEqual(vs[0], -0.5)
        self.assertAlmostEqual(vs[-1], 0.5)
        # центрирование x
        us = [p["u"] for p in layout]
        self.assertAlmostEqual(min(us), -0.5)
        self.assertAlmostEqual(max(us), 0.5)

    def test_5_images(self):
        layout = grid_layout([1.0] * 5)
        shape = grid_shape(5)
        self.assertEqual(shape, (3, 2))
        self.assertEqual([p["row"] for p in layout[3:]], [1, 1])

    def test_varying_widths_bbox_centered(self):
        layout = grid_layout([2.0, 0.5, 1.0, 1.0])
        # глобальный bbox сетки должен центрироваться на 0 по обеим осям
        edges_u = [p["u"] - p["width"] / 2 for p in layout] + [p["u"] + p["width"] / 2 for p in layout]
        edges_v = [p["v"] - p["height"] / 2 for p in layout] + [p["v"] + p["height"] / 2 for p in layout]
        self.assertAlmostEqual((min(edges_u) + max(edges_u)) / 2.0, 0.0, places=6)
        self.assertAlmostEqual((min(edges_v) + max(edges_v)) / 2.0, 0.0, places=6)
        # ряды выровнены по одному левому краю (левый край первого элемента ряда)
        row_lefts = {
            min(p["u"] - p["width"] / 2 for p in layout if p["row"] == r)
            for r in {p["row"] for p in layout}
        }
        self.assertEqual(len(row_lefts), 1)
        self.assertAlmostEqual(next(iter(row_lefts)), -1.25, places=6)

    def test_gap(self):
        layout = grid_layout([1.0, 1.0], gap=0.5)
        self.assertAlmostEqual(layout[1]["u"] - layout[0]["u"], 1.5)

    def test_empty(self):
        self.assertEqual(grid_layout([]), [])


class TestGridToWorld(unittest.TestCase):
    def test_z_axis(self):
        self.assertEqual(grid_to_world(1.0, 2.0, "Z"), (1.0, 2.0, 0.0))

    def test_x_axis(self):
        self.assertEqual(grid_to_world(1.0, 2.0, "X"), (0.0, 1.0, 2.0))

    def test_y_axis(self):
        self.assertEqual(grid_to_world(1.0, 2.0, "Y"), (1.0, 0.0, 2.0))

    def test_axis_map_consistent(self):
        for axis, (u_axis, v_axis) in AXIS_MAP.items():
            with self.subTest(axis=axis):
                self.assertEqual(len(grid_to_world(1.0, 1.0, axis)), 3)
                self.assertIn(u_axis, "XYZ")
                self.assertIn(v_axis, "XYZ")
                self.assertNotEqual(u_axis, v_axis)

    def test_columns_follow_width_rows_follow_height(self):
        for axis, euler in AXIS_ROTATION.items():
            with self.subTest(axis=axis):
                width_dir = mathutils_vector_rotate((1.0, 0.0, 0.0), euler)
                height_dir = mathutils_vector_rotate((0.0, 1.0, 0.0), euler)
                u_axis = "XYZ"[max(range(3), key=lambda i: abs(grid_to_world(1.0, 0.0, axis)[i]))]
                v_axis = "XYZ"[max(range(3), key=lambda i: abs(grid_to_world(0.0, 1.0, axis)[i]))]
                w_axis = "XYZ"[max(range(3), key=lambda i: abs(width_dir[i]))]
                h_axis = "XYZ"[max(range(3), key=lambda i: abs(height_dir[i]))]
                self.assertEqual(u_axis, w_axis)
                self.assertEqual(v_axis, h_axis)

    def test_rotation_normals(self):
        expected = {"X": 1.0, "Y": -1.0, "Z": 1.0}
        for axis, euler in AXIS_ROTATION.items():
            with self.subTest(axis=axis):
                normal = mathutils_vector_rotate((0.0, 0.0, 1.0), euler)
                primary = {"X": normal[0], "Y": normal[1], "Z": normal[2]}[axis]
                self.assertAlmostEqual(primary, expected[axis], places=6)


def mathutils_vector_rotate(vec, euler):
    x, y, z = vec
    cx, sx = math.cos(euler[0]), math.sin(euler[0])
    cy, sy = math.cos(euler[1]), math.sin(euler[1])
    cz, sz = math.cos(euler[2]), math.sin(euler[2])
    # R = Rz*Ry*Rx (Blender XYZ euler order)
    x1 = x * cy * cz + y * (cz * sx * sy - cx * sz) + z * (cx * cz * sy + sx * sz)
    y1 = x * cy * sz + y * (cx * cz + sx * sy * sz) + z * (-cz * sx + cx * sy * sz)
    z1 = -x * sy + y * cy * sx + z * cx * cy
    return (x1, y1, z1)


class TestComputeTargetReal(unittest.TestCase):
    def test_basic(self):
        self.assertAlmostEqual(compute_target_real(10, 5, 20), 10.0)

    def test_signed(self):
        self.assertAlmostEqual(compute_target_real(-10, 5, 20), -10.0)

    def test_ref_img_zero(self):
        with self.assertRaises(ValueError):
            compute_target_real(0, 5, 20)


class TestScanDirectory(unittest.TestCase):
    def test_filters_sorts_and_top_level_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("b.JPG", "a.png", "c.webp", "skip.txt", "d.gif"):
                with open(os.path.join(tmp, name), "w") as f:
                    f.write("x")
            os.mkdir(os.path.join(tmp, "subdir.png.rest"))
            with open(os.path.join(tmp, "subdir.png.rest/nested.png"), "w") as f:
                f.write("x")
            found = scan_directory(tmp)
            names = [os.path.basename(p) for p in found]
            self.assertEqual(names, ["a.png", "b.JPG", "c.webp"])

    def test_missing_dir(self):
        with self.assertRaises(NotADirectoryError):
            scan_directory("/nonexistent/path/xyz")


class TestRasterExtensions(unittest.TestCase):
    def test_has_common(self):
        for ext in (".png", ".jpg", ".jpeg", ".bmp", ".tga", ".webp", ".exr", ".hdr"):
            self.assertIn(ext, RASTER_EXTENSIONS)


if __name__ == "__main__":
    unittest.main()