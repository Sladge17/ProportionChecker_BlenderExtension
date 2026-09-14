"""Pure logic for ProportionChecker — no bpy dependency, unit-testable outside Blender."""

import math
import os

RASTER_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".bmp", ".tga", ".tif", ".tiff", ".webp", ".exr", ".hdr",
})

# World axes that grid columns (u, plane width) and rows (v, plane height) map onto,
# per chosen plane-normal axis, considering how the plane rotates (see AXIS_ROTATION).
# Chosen so that the width runs left-right and the height up-down on screen
# (Z: X/Y, X: Y/Z, Y: Z/X).
AXIS_MAP = {
    "Z": ("X", "Y"),
    "X": ("Y", "Z"),
    "Y": ("Z", "X"),
}

# Euler rotation (radians, Blender XYZ order, R = Rz*Ry*Rx) that orients a XY-plane
# (normal +Z) onto the requested axis. The plane normal (front face with the texture)
# always points along the positive world axis: X:+X, Y:+Y, Z:+Z.
AXIS_ROTATION = {
    "X": (math.pi / 2.0, 0.0, math.pi / 2.0),
    "Y": (math.pi / 2.0, 3.0 * math.pi / 2.0, math.pi),
    "Z": (0.0, 0.0, 0.0),
}


def axis_basis(axis):
    """World-space (width, height, normal) unit vectors of the plane basis for an axis.

    Mirrors Blender's Euler XYZ composition (R = Rz*Ry*Rx, applied to the vector as
    R*v) used for `obj.rotation_euler = AXIS_ROTATION[axis]`. Pure math, no bpy.
    """
    ex, ey, ez = AXIS_ROTATION[axis]
    cx, sx = math.cos(ex), math.sin(ex)
    cy, sy = math.cos(ey), math.sin(ey)
    cz, sz = math.cos(ez), math.sin(ez)

    def apply(v):
        x, y, z = v
        return (
            x * cy * cz + y * (cz * sx * sy - cx * sz) + z * (cx * cz * sy + sx * sz),
            x * cy * sz + y * (cx * cz + sx * sy * sz) + z * (-cz * sx + cx * sy * sz),
            -x * sy + y * cy * sx + z * cx * cy,
        )

    return apply((1.0, 0.0, 0.0)), apply((0.0, 1.0, 0.0)), apply((0.0, 0.0, 1.0))


def grid_shape(n):
    """Grid columns/rows: cols = ceil(sqrt(n)), rows = ceil(n / cols).

    Sanity: 4 -> (2, 2), 5 -> (3, 2), 7 -> (3, 3), 9 -> (3, 3).
    """
    if n <= 0:
        return (0, 0)
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    return (cols, rows)


def plane_width(img_w, img_h, plane_height=1.0):
    """Width of a plane keeping the image aspect ratio at the given height."""
    if img_h <= 0:
        raise ValueError("image height must be > 0")
    if img_w <= 0:
        raise ValueError("image width must be > 0")
    if plane_height <= 0:
        raise ValueError("plane height must be > 0")
    return plane_height * (img_w / img_h)


def grid_layout(widths, plane_height=1.0, gap_h=0.0, gap_v=0.0):
    """Compute per-plane grid placement.

    Fills the grid row by row, rows left-aligned, whole grid centered on the origin.
    `gap_h` is the distance between neighbouring planes in a row (horizontal),
    `gap_v` between rows (vertical); both default to 0.
    Returns a list of dicts: {index, row, col, u, v, width, height}.
    u/v are offsets along the grid-column/row directions (centered on 0,0).
    """
    n = len(widths)
    if n == 0:
        return []
    cols, rows = grid_shape(n)
    row_widths = [
        sum(widths[r * cols:(r + 1) * cols])
        + max(0, len(widths[r * cols:(r + 1) * cols]) - 1) * gap_h
        for r in range(rows)
    ]
    grid_width = max(row_widths)
    grid_height = rows * plane_height + (rows - 1) * gap_v
    left = -grid_width / 2.0

    row_offsets = [0.0] * rows
    layout = []
    for i, w in enumerate(widths):
        r = i // cols
        u = left + row_offsets[r] + w / 2.0
        v = grid_height / 2.0 - r * (plane_height + gap_v) - plane_height / 2.0
        row_offsets[r] += w + gap_h
        layout.append({
            "index": i,
            "row": r,
            "col": i % cols,
            "u": u,
            "v": v,
            "width": w,
            "height": plane_height,
        })
    return layout


def grid_to_world(u, v, axis):
    """Map local grid offsets (u along columns, v along rows) to world coordinates."""
    u_axis, v_axis = AXIS_MAP[axis]
    vec = {"X": 0.0, "Y": 0.0, "Z": 0.0}
    vec[u_axis] = u
    vec[v_axis] = v
    return (vec["X"], vec["Y"], vec["Z"])


def compute_target_real(ref_size_img, ref_size_real, target_size_img):
    """Target real size via cross-multiplication. Raises ValueError on bad input."""
    if ref_size_img == 0:
        raise ValueError("reference size on image must be non-zero")
    return target_size_img * ref_size_real / ref_size_img


def scan_directory(path):
    """Top-level, case-insensitive raster image search. Sorted by filename."""
    if not os.path.isdir(path):
        raise NotADirectoryError(path)
    names = [
        fn for fn in sorted(os.listdir(path))
        if os.path.splitext(fn)[1].lower() in RASTER_EXTENSIONS
        and os.path.isfile(os.path.join(path, fn))
    ]
    return [os.path.join(path, fn) for fn in names]