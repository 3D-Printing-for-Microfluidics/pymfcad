from __future__ import annotations

import os
import trimesh
import freetype
import numpy as np
from numba import njit

from collections.abc import Callable
from manifold3d import set_circular_segments, Manifold, Mesh, CrossSection, OpType


def _is_integer(val: float) -> bool:
    """
    ###### Check if a float value is close to an integer.
    """
    return abs(val - round(val)) < 1e-6


def set_fn(fn: int) -> None:
    """
    ###### Set the default number of facets for round shapes.

    ######  Parameters:
    - fn (int): Number of facets for circular segments.
    """
    set_circular_segments(fn)


set_fn(20)  # Set default circular segments to 20


class Shape:
    """
    ###### Manifold3D generic shape class.
    """

    def __init__(self, px_size: float, layer_size: float):
        self._name = None
        self._parent = None
        self._color = None
        self._px_size = px_size
        self._layer_size = layer_size
        self._object = None
        self._keepouts = []

    def _translate_keepouts(self, translation: tuple[float, float, float]) -> None:
        """
        ###### Translate the keepouts.

        ###### Parameters:
        - translation (tuple[float, float, float]): The translation.
        """
        dx, dy, dz = translation
        self._keepouts = [
            [x0 + dx, y0 + dy, z0 + dz, x1 + dx, y1 + dy, z1 + dz]
            for x0, y0, z0, x1, y1, z1 in self._keepouts
        ]

    def _rotate_point(
        self, point: tuple[float, float, float], rotation: tuple[float, float, float]
    ) -> None:
        """
        ###### Rotate a point around origin (0,0,0) with Euler angles (in degrees) in XYZ order.

        ###### Parameters:
        - point (tuple[float, float, float]): The point to rotate.
        - rotation (tuple[float, float, float]): The rotation.
        """
        # Convert degrees to radians
        rx, ry, rz = np.radians(rotation)
        x, y, z = point

        # Rotate around X
        cos_rx, sin_rx = np.cos(rx), np.sin(rx)
        y, z = y * cos_rx - z * sin_rx, y * sin_rx + z * cos_rx

        # Rotate around Y
        cos_ry, sin_ry = np.cos(ry), np.sin(ry)
        x, z = x * cos_ry + z * sin_ry, -x * sin_ry + z * cos_ry

        # Rotate around Z
        cos_rz, sin_rz = np.cos(rz), np.sin(rz)
        x, y = x * cos_rz - y * sin_rz, x * sin_rz + y * cos_rz

        return [x, y, z]

    def _rotate_keepouts(self, rotation: tuple[float, float, float]):
        """
        ###### Rotate the keepouts.

        ###### Parameters:
        - rotation (tuple[float, float, float]): The rotation.
        """
        rotated_keepouts = []
        for x0, y0, z0, x1, y1, z1 in self._keepouts:
            # Get all 8 corners
            corners = [[x, y, z] for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
            rotated_corners = [self._rotate_point(pt, rotation) for pt in corners]
            xs, ys, zs = zip(*rotated_corners)
            rotated_keepouts.append(
                [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)]
            )
        self._keepouts = rotated_keepouts

    def _scale_keepouts(self, scale: tuple[float, float, float]) -> None:
        """
        ###### Scale the keepouts.

        ###### Parameters:
        - scale (tuple[float, float, float]): The scale.
        """
        sx, sy, sz = scale
        self._keepouts = [
            [
                x0 * sx,
                y0 * sy,
                z0 * sz,
                x1 * sx,
                y1 * sy,
                z1 * sz,
            ]
            for x0, y0, z0, x1, y1, z1 in self._keepouts
        ]

    def _mirror_keepouts(self, axis: tuple[bool, bool, bool]) -> None:
        """
        ###### Mirror the keepouts.

        ###### Parameters:
        - axis (tuple[bool, bool, bool]): The axis to mirror.
        """
        flip_x, flip_y, flip_z = axis
        new_keepouts = []
        for x0, y0, z0, x1, y1, z1 in self._keepouts:
            nx0, nx1 = sorted([-x0, -x1]) if flip_x else (x0, x1)
            ny0, ny1 = sorted([-y0, -y1]) if flip_y else (y0, y1)
            nz0, nz1 = sorted([-z0, -z1]) if flip_z else (z0, z1)
            new_keepouts.append([nx0, ny0, nz0, nx1, ny1, nz1])
        self._keepouts = new_keepouts

    def translate(self, translation: tuple[int, int, int]) -> "Shape":
        """
        ###### Translate the shape by a given translation vector.

        ###### Parameters:
        - translation (tuple[int, int, int]): The translation vector.

        ###### Returns:
        - self (Shape): The translated shape.
        """
        self._translate_keepouts(translation)
        self._object = self._object.translate(
            (
                translation[0] * self._px_size,
                translation[1] * self._px_size,
                translation[2] * self._layer_size,
            )
        )
        return self

    def rotate(self, rotation: tuple[float, float, float]) -> "Shape":
        """
        ###### Rotate the shape by a given rotation vector (in degrees).

        ###### Parameters:
        - rotation (tuple[float, float, float]): The rotation vector in degrees.

        ###### Returns:
        - self (Shape): The rotated shape.
        """
        self._rotate_keepouts(rotation)
        self._object = self._object.rotate(rotation)
        return self

    def resize(self, size: tuple[int, int, int]) -> "Shape":
        """
        ###### Resize the shape to a given size in px/layer space.

        ###### Parameters:
        - size (tuple[int, int, int]): The new size in px/layer space.

        ###### Returns:
        - self (Shape): The resized shape.
        """
        # if size if 0 set it near 0
        if size[0] == 0:
            size = (0.0001, size[1], size[2])
        if size[1] == 0:
            size = (size[0], 0.0001, size[2])
        if size[2] == 0:
            size = (size[0], size[1], 0.0001)
        bounds = self._object.bounding_box()
        # convert bounds to px/layer
        bounds = [
            bounds[0] / self._px_size,
            bounds[1] / self._px_size,
            bounds[2] / self._layer_size,
            bounds[3] / self._px_size,
            bounds[4] / self._px_size,
            bounds[5] / self._layer_size,
        ]
        # calculate scale factors in px/layer space
        sx = size[0] / (bounds[3] - bounds[0])
        sy = size[1] / (bounds[4] - bounds[1])
        sz = size[2] / (bounds[5] - bounds[2])

        self._scale_keepouts((sx, sy, sz))
        self._object = self._object.scale((sx, sy, sz))
        return self

    def mirror(self, axis: tuple[bool, bool, bool]) -> "Shape":
        """
        ###### Mirror the shape along the specified axes.

        ###### Parameters:
        - axis (tuple[bool, bool, bool]): A tuple indicating which axes to mirror (x, y, z).

        ###### Returns:
        - self (Shape): The mirrored shape.
        """
        self._mirror_keepouts(axis)
        self._object = self._object.mirror(axis)
        return self

    def __add__(self, other: "Shape") -> "Shape":
        """
        ###### Combine two shapes using union operation.

        ###### Parameters:
        - other (Shape): The other shape to combine with.

        ###### Returns:
        - self (Shape): The combined shape.
        """
        self._keepouts.extend(other._keepouts)
        self._object = self._object + other._object
        return self

    def __sub__(self, other: "Shape") -> "Shape":
        """
        ###### Subtract another shape from this shape.

        ###### Parameters:
        - other (Shape): The shape to subtract.

        ###### Returns:
        - self (Shape): The resulting shape after subtraction.
        """
        self._object = self._object - other._object
        return self

    def _intersect_boxes(self, box1, box2):
        # Compute the intersection of two axis-aligned bounding boxes
        x_min = max(box1[0], box2[0])
        y_min = max(box1[1], box2[1])
        z_min = max(box1[2], box2[2])
        x_max = min(box1[3], box2[3])
        y_max = min(box1[4], box2[4])
        z_max = min(box1[5], box2[5])

        # Check for non-empty intersection
        if x_min < x_max and y_min < y_max and z_min < z_max:
            return [x_min, y_min, z_min, x_max, y_max, z_max]
        else:
            return None

    def _intersect_keepouts(self, list1, list2):
        intersections = []
        for box1 in list1:
            for box2 in list2:
                inter = self._intersect_boxes(box1, box2)
                if inter:
                    intersections.append(inter)
        return intersections

    def __and__(self, other: "Shape") -> "Shape":
        """
        ###### Intersect this shape with another shape.

        ###### Parameters:
        - other (Shape): The shape to intersect with.

        ###### Returns:
        - self (Shape): The resulting shape after intersection.
        """
        self._keepouts = self._intersect_keepouts(self._keepouts, other._keepouts)
        self._object = Manifold.batch_boolean(
            [self._object, other._object],
            OpType.Intersect,
        )
        return self

    def hull(self, other: "Shape") -> "Shape":
        """
        ###### Create a convex hull of this shape and another shape.
        ###### This method combines the keepouts of both shapes and creates a bridge between their bounding boxes.

        ###### Parameters:
        - other (Shape): The other shape to combine with.

        ###### Returns:
        - self (Shape): The resulting shape after creating the hull.
        """
        # Combine keepouts
        self._keepouts.extend(other._keepouts)

        # Get both bounding boxes
        b1 = self._object.bounding_box()
        b1 = (
            b1[0] / self._px_size,
            b1[1] / self._px_size,
            b1[2] / self._layer_size,
            b1[3] / self._px_size,
            b1[4] / self._px_size,
            b1[5] / self._layer_size,
        )
        b2 = other._object.bounding_box()
        b2 = (
            b2[0] / self._px_size,
            b2[1] / self._px_size,
            b2[2] / self._layer_size,
            b2[3] / self._px_size,
            b2[4] / self._px_size,
            b2[5] / self._layer_size,
        )

        center1 = [(b1[0] + b1[3]) / 2, (b1[1] + b1[4]) / 2, (b1[2] + b1[5]) / 2]
        center2 = [(b2[0] + b2[3]) / 2, (b2[1] + b2[4]) / 2, (b2[2] + b2[5]) / 2]
        deltas = [abs(center1[i] - center2[i]) for i in range(3)]

        # The separation axis is the one with the largest center delta
        sep_axis = deltas.index(max(deltas))

        # Create a bridge box between bounding boxes along the separation axis
        bridge_min = [0, 0, 0]
        bridge_max = [0, 0, 0]

        for i in range(3):
            if i == sep_axis:
                bridge_min[i] = min(b1[i], b2[i])
                bridge_max[i] = max(b1[i + 3], b2[i + 3])
            else:
                bridge_min[i] = min(b1[i], b2[i])
                bridge_max[i] = max(b1[i + 3], b2[i + 3])

        self._keepouts.append(
            [
                bridge_min[0],
                bridge_min[1],
                bridge_min[2],
                bridge_max[0],
                bridge_max[1],
                bridge_max[2],
            ]
        )

        self._object = Manifold.batch_hull([self._object, other._object])
        return self

    def copy(self, _internal=False) -> "Shape":
        """
        ###### Create a copy of the shape.

        ###### Parameters:
        - _internal (bool): If True, copy internal properties like name, parent, and color. (internal use only)

        ###### Returns:
        - Shape: A new Shape instance with the same properties.
        """
        new_shape = Shape(self._px_size, self._layer_size)
        if _internal:
            new_shape._name = self._name
            new_shape._parent = self._parent
            new_shape._color = self._color
        mesh = self._object.to_mesh()
        new_shape._object = Manifold(mesh)
        new_shape._keepouts = self._keepouts.copy()
        return new_shape

    def _add_bbox_to_keepout(self, bbox: tuple[float]) -> None:
        # add keepout
        bbox = (
            bbox[0] / self._px_size,
            bbox[1] / self._px_size,
            bbox[2] / self._layer_size,
            bbox[3] / self._px_size,
            bbox[4] / self._px_size,
            bbox[5] / self._layer_size,
        )
        self._keepouts.append(bbox)


class Cube(Shape):
    """
    ###### Manifold3D cube.
    """

    def __init__(
        self,
        size: tuple[int, int, int],
        px_size: float,
        layer_size: float,
        center: bool = False,
        _no_validation: bool = False,
    ):
        """
        ###### Parameters:
        - size (tuple[int, int, int]): Size of the cube in px/layer space.
        - px_size (float): Pixel size in mm.
        - layer_size (float): Layer height in mm.
        - center (bool): Whether to center the cube at the origin.
        - _no_validation (bool): If True, skip validation checks for odd dimensions (internal use).
        """
        super().__init__(px_size, layer_size)

        # shift half a pixel if odd and centered
        x = 0
        y = 0
        z = 0
        if center and not _no_validation:
            if size[0] % 2 != 0:
                print(
                    f"⚠️ Centered cube x dimension is odd. Shifting 0.5 px to align with px grid"
                )
                x = 0.5
            if size[1] % 2 != 0:
                print(
                    f"⚠️ Centered cube y dimension is odd. Shifting 0.5 px to align with px grid"
                )
                y = 0.5
            if size[2] % 2 != 0:
                print(
                    f"⚠️ Centered cube z dimension is odd. Shifting 0.5 px to align with px grid"
                )
                z = 0.5

        if size[0] == 0:
            size = (0.0001, size[1], size[2])
        if size[1] == 0:
            size = (size[0], 0.0001, size[2])
        if size[2] == 0:
            size = (size[0], size[1], 0.0001)

        self._object = Manifold.cube(
            (size[0] * px_size, size[1] * px_size, size[2] * layer_size),
            center=center,
        ).translate((x * px_size, y * px_size, z * layer_size))
        self._add_bbox_to_keepout(self._object.bounding_box())


class Cylinder(Shape):
    """
    ###### Manifold3D cylinder.
    """

    def __init__(
        self,
        height: int,
        radius: float = None,
        bottom_r: float = None,
        top_r: float = None,
        px_size: float = None,
        layer_size: float = None,
        center_xy: bool = True,
        center_z: bool = False,
        fn: int = 0,
    ):
        """
        ###### Parameters:
        - height (int): Height of the cylinder in layer space.
        - radius (float): Radius of the cylinder in px space.
        - bottom_r (float): Bottom radius of the cylinder in px space.
        - top_r (float): Top radius of the cylinder in px space.
        - px_size (float): Pixel size in mm.
        - layer_size (float): Layer height in mm.
        - center_xy (bool): Whether to center the cylinder in XY plane.
        - center_z (bool): Whether to center the cylinder in Z plane.
        - fn (int): Number of facets for the circular segments.
        """
        super().__init__(px_size, layer_size)

        # only allow radiuses to be multiples of 0.5
        if radius is not None:
            if not _is_integer(radius * 2):
                raise ValueError("Cylinder radius must be a multiple of 0.5")
        if bottom_r is not None:
            if not _is_integer(bottom_r * 2):
                raise ValueError("Cylinder radius (bottom) must be a multiple of 0.5")
        if top_r is not None:
            if not _is_integer(top_r * 2):
                raise ValueError("Cylinder radius (top) must be a multiple of 0.5")

        # validate shape is fully constrained
        bottom = bottom_r if bottom_r is not None else radius
        top = top_r if top_r is not None else radius
        if bottom is None or top is None:
            raise ValueError("Either radius or bottom_r and top_r must be provided.")

        if top % 2 != bottom % 2:
            raise ValueError(
                "Cylinder top and bottom radius must both be either even or odd."
            )

        bottom = bottom_r if bottom_r is not None else radius
        top = top_r if top_r is not None else radius

        xy = 0
        z = 0
        if center_z and height % 2 != 0:
            print(
                f"⚠️ Centered cylinder z dimension is odd. Shifting 0.5 px to align with px grid"
            )
            z = 0.5
        if height == 0:
            height = 0.0001
        if center_xy:
            if top * 2 % 2 != 0:  # can check either to or bottom
                print(
                    f"⚠️ Centered cylinder radius is odd. Shifting 0.5 px to align with px grid"
                )
                xy = 0.5
            self._object = Manifold.cylinder(
                height=height * layer_size,
                radius_low=bottom * px_size,
                radius_high=top * px_size,
                circular_segments=fn,
                center=center_z,
            ).translate((xy * px_size, xy * px_size, z * layer_size))
        else:
            radius = max(bottom, top)
            self._object = Manifold.cylinder(
                height=height * layer_size,
                radius_low=bottom * px_size,
                radius_high=top * px_size,
                circular_segments=fn,
                center=center_z,
            ).translate((radius * px_size, radius * px_size, z * layer_size))
        self._add_bbox_to_keepout(self._object.bounding_box())


class Sphere(Shape):
    """
    ###### Manifold3D ellipsoid.
    """

    def __init__(
        self,
        size: tuple[int, int, int],
        px_size: float = None,
        layer_size: float = None,
        center: bool = True,
        fn: int = 0,
        _no_validation: bool = False,
    ):
        """
        ###### Parameters:
        - size (tuple[int, int, int]): Size of the sphere in px/layer space.
        - px_size (float): Pixel size in mm.
        - layer_size (float): Layer height in mm.
        - center (bool): Whether to center the sphere at the origin.
        - fn (int): Number of facets for the circular segments.
        - _no_validation (bool): If True, skip validation checks for odd dimensions (internal use).
        """
        super().__init__(px_size, layer_size)
        if center:
            x = 0
            y = 0
            z = 0
            if not _no_validation:
                if size[0] % 2 != 0:
                    print(
                        f"⚠️ Centered sphere x dimension is odd. Shifting 0.5 px to align with px grid"
                    )
                    x = 0.5
                if size[1] % 2 != 0:
                    print(
                        f"⚠️ Centered sphere y dimension is odd. Shifting 0.5 px to align with px grid"
                    )
                    y = 0.5
                if size[2] % 2 != 0:
                    print(
                        f"⚠️ Centered sphere z dimension is odd. Shifting 0.5 px to align with px grid"
                    )
                    z = 0.5

        if size[0] == 0:
            size = (0.0001, size[1], size[2])
        if size[1] == 0:
            size = (size[0], 0.0001, size[2])
        if size[2] == 0:
            size = (size[0], size[1], 0.0001)

        if fn is None or fn < 0:
            self._object = Manifold.sphere(radius=1)
        else:
            self._object = Manifold.sphere(radius=1, circular_segments=fn)
        self.resize(size)

        if center:
            self._object = self._object.translate(
                (x * px_size, y * px_size, z * layer_size)
            )
        else:
            self._object = self._object.translate(
                (
                    size[0] / 2 * px_size,
                    size[1] / 2 * px_size,
                    size[2] / 2 * layer_size,
                )
            )
        self._add_bbox_to_keepout(self._object.bounding_box())


class RoundedCube(Shape):
    """
    ###### Manifold3D rounded cube.
    """

    def __init__(
        self,
        size: tuple[int, int, int],
        radius: tuple[float, float, float],
        px_size: float,
        layer_size: float,
        center: bool = False,
        fn: int = 0,
        _no_validation: bool = False,
    ):
        """
        ###### Parameters:
        - size (tuple[int, int, int]): Size of the rounded cube in px/layer space.
        - radius (tuple[float, float, float]): Radius of the rounded corners in px/layer space.
        - px_size (float): Pixel size in mm.
        - layer_size (float): Layer height in mm.
        - center (bool): Whether to center the rounded cube at the origin.
        - fn (int): Number of facets for the circular segments.
        - _no_validation (bool): If True, skip validation checks for odd dimensions (internal use).
        """
        super().__init__(px_size, layer_size)

        # shift half a pixel if odd and centered
        x = 0
        y = 0
        z = 0
        if center and not _no_validation:
            if size[0] % 2 != 0:
                print(
                    f"⚠️ Centered rounded cube x dimension is odd. Shifting 0.5 px to align with px grid"
                )
                x = 0.5
            if size[1] % 2 != 0:
                print(
                    f"⚠️ Centered rounded cube y dimension is odd. Shifting 0.5 px to align with px grid"
                )
                y = 0.5
            if size[2] % 2 != 0:
                print(
                    f"⚠️ Centered rounded cube z dimension is odd. Shifting 0.5 px to align with px grid"
                )
                z = 0.5

        if size[0] == 0:
            size = (0.0001, size[1], size[2])
        if size[1] == 0:
            size = (size[0], 0.0001, size[2])
        if size[2] == 0:
            size = (size[0], size[1], 0.0001)

        radius = list(radius)
        if radius[0] <= 0:
            radius[0] = 0.0001
        if radius[1] <= 0:
            radius[1] = 0.0001
        if radius[2] <= 0:
            radius[2] = 0.0001

        spheres = []
        for i in range(2):
            for j in range(2):
                for k in range(2):
                    if fn is None or fn < 0:
                        s = Manifold.sphere(radius=1)
                    else:
                        s = Manifold.sphere(radius=1, circular_segments=fn)
                    s = s.scale(
                        (
                            radius[0] * px_size,
                            radius[1] * px_size,
                            radius[2] * layer_size,
                        )
                    )
                    _x = (size[0] / 2 - radius[0]) if i else -(size[0] / 2 - radius[0])
                    _y = (size[1] / 2 - radius[1]) if j else -(size[1] / 2 - radius[1])
                    _z = (size[2] / 2 - radius[2]) if k else -(size[2] / 2 - radius[2])
                    s = s.translate(
                        (
                            (x + _x) * px_size,
                            (y + _y) * px_size,
                            (z + _z) * layer_size,
                        )
                    )
                    if not center:
                        s = s.translate(
                            (
                                size[0] / 2 * px_size,
                                size[1] / 2 * px_size,
                                size[2] / 2 * layer_size,
                            )
                        )
                    spheres.append(s)

        self._object = Manifold.batch_hull(spheres)
        self._add_bbox_to_keepout(self._object.bounding_box())


class TextExtrusion(Shape):
    """
    ###### Manifold3D text extrusion shapes.
    """

    def __init__(
        self,
        text: str,
        height: int,
        font: str = "arial",
        font_size: int = 10,
        px_size: float = None,
        layer_size: float = None,
    ):
        """
        ###### Parameters:
        - text (str): The text to extrude.
        - height (int): Height of the extrusion in layer space.
        - font (str): Font name to use for the text.
        - font_size (int): Font size in px.
        - px_size (float): Pixel size in mm.
        - layer_size (float): Layer height in mm.
        """
        super().__init__(px_size, layer_size)

        def glyph_to_polygons(face, char, scale=1.0, curve_steps=10):
            face.load_char(char, freetype.FT_LOAD_NO_BITMAP)
            outline = face.glyph.outline
            points = np.array(outline.points, dtype=np.float32) * scale
            tags = outline.tags
            contours = outline.contours

            polys = []
            start = 0
            for end in contours:
                pts = points[start : end + 1]
                tgs = tags[start : end + 1]
                n = len(pts)

                # Wrap-around: emulate circular indexing
                pts = list(pts)
                tgs = list(tgs)
                pts.append(pts[0])
                tgs.append(tgs[0])

                path = []
                i = 0
                while i < n:
                    pt1 = pts[i]
                    tag1 = tgs[i] & 1
                    if tag1:  # on-curve
                        path.append(pt1)
                        i += 1
                    else:
                        # pt1 is control point
                        if tgs[i + 1] & 1:  # next is on-curve
                            pt2 = pts[i + 1]
                            p0 = path[-1] if path else (pt1 + pt2) / 2
                            for t in np.linspace(0, 1, curve_steps):
                                p = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * pt1 + t**2 * pt2
                                path.append(p)
                            i += 2
                        else:
                            # next is off-curve → implied on-curve midpoint
                            mid = (pt1 + pts[i + 1]) / 2
                            p0 = path[-1] if path else mid
                            for t in np.linspace(0, 1, curve_steps):
                                p = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * pt1 + t**2 * mid
                                path.append(p)
                            i += 1

                if len(path) >= 3:
                    polys.append(np.array(path))
                start = end + 1

            return polys

        def text_to_manifold(
            text, font_path="Arial.ttf", font_size=50, height=1.0, spacing=1.1
        ):
            face = freetype.Face(font_path)
            face.set_char_size(font_size * 64)

            offset_x = 0
            result = Manifold()

            for char in text:
                if char == " ":
                    offset_x += font_size * spacing / 4
                    continue

                polys = glyph_to_polygons(face, char, scale=1.0 / 64.0)
                if not polys:
                    continue

                all_loops = []
                for poly in polys:
                    loop = list(
                        reversed(
                            [
                                [
                                    float(p[0] + offset_x) * px_size,
                                    float(p[1]) * px_size,
                                ]
                                for p in poly
                            ]
                        )
                    )
                    all_loops.append(loop)

                # Create cross section with outer + holes
                xsec = CrossSection(all_loops)
                if xsec.is_empty():
                    print(f"Invalid CrossSection for character '{char}'")
                    continue

                extruded = xsec.extrude(height * layer_size)
                if extruded.num_vert() == 0:
                    print(f"Extrusion failed for character '{char}'")
                    continue
                result += extruded
                offset_x += (face.glyph.advance.x / 64.0) * spacing

            return result

        if height == 0:
            height = 0.0001

        self._object = text_to_manifold(
            text, height=height, font_path=f"pymfd/backend/fonts/{font}.ttf"
        )
        self._add_bbox_to_keepout(self._object.bounding_box())


class ImportModel(Shape):
    """
    ###### Manifold3D 3d model import.
    """

    def __init__(
        self,
        filename: str,
        auto_repair: bool = True,
        px_size: float = None,
        layer_size: float = None,
    ):
        """
        ###### Parameters:
        - filename (str): Path to the 3D model file.
        - auto_repair (bool): Whether to automatically repair the mesh if it has issues.
        - px_size (float): Pixel size in mm.
        - layer_size (float): Layer height in mm.

        This class loads a 3D model file and converts it to a Manifold3D object.
        It checks for common mesh issues such as watertightness, winding consistency, and emptiness.
        If the mesh has issues, it attempts to repair them if `auto_repair` is set to True.
        If the mesh cannot be repaired or is still not watertight, it raises an error.
        """
        super().__init__(px_size, layer_size)

        def load_3d_file_to_manifold(path, auto_repair=True) -> Manifold:
            """
            ###### Load a 3D file and convert it to a Manifold3D object.

            ###### Parameters:
            - path (str): Path to the 3D model file.
            - auto_repair (bool): Whether to automatically repair the mesh if it has issues.

            ###### Returns:
            - Manifold3D object.
            """

            ext = os.path.splitext(filename)[1].lower()
            print(f"📦 Loading: {filename} (.{ext[1:]})")

            # try:
            mesh = trimesh.load(filename, force="mesh")

            if isinstance(mesh, trimesh.Scene):
                print("🔁 Flattening scene...")
                mesh = mesh.to_mesh()

            issues = []
            if not mesh.is_watertight:
                issues.append("❌ Mesh is not watertight (required for Manifold3D).")
            if not mesh.is_winding_consistent:
                issues.append("⚠️ Face winding is inconsistent (normals may be wrong).")
            if mesh.is_empty or len(mesh.faces) == 0:
                issues.append("❌ Mesh is empty or has no faces.")
            if not mesh.is_volume:
                issues.append("⚠️ Mesh may not define a solid volume.")

            if issues:
                print("\n".join(issues))
                if not auto_repair:
                    raise ValueError(
                        "Mesh has critical issues. Aborting due to `auto_repair=False`."
                    )

            if auto_repair:
                print("🛠 Attempting repair steps...")
                mesh = mesh.copy()
                trimesh.repair.fill_holes(mesh)
                trimesh.repair.fix_normals(mesh)
                mesh.remove_degenerate_faces()
                mesh.remove_duplicate_faces()
                mesh.remove_infinite_values()
                mesh.remove_unreferenced_vertices()

            if not mesh.is_watertight:
                raise ValueError(
                    "❌ Mesh is still not watertight after repair. Cannot proceed."
                )

            # Convert to MeshGL
            verts = np.asarray(mesh.vertices, dtype=np.float32)
            faces = np.asarray(mesh.faces, dtype=np.uint32)
            mesh_obj = Mesh(verts, faces)

            manifold = Manifold(mesh_obj)
            print("✅ Successfully converted mesh to Manifold.")
            return manifold

        self._object = load_3d_file_to_manifold(filename, auto_repair)
        self._add_bbox_to_keepout(self._object.bounding_box())

        # except Exception as e:
        #     raise ValueError(f"❌ Error loading mesh: {e}")
        #     print(f"🔥 Error loading mesh: {e}")
        #     return None


class TPMS(Shape):
    """
    ###### Manifold3D triply periodic minimal surface (TPMS) shapes.
    """

    @njit
    def gyroid(x: float, y: float, z: float) -> bool:
        """###### Gyroid TPMS function."""
        a = np.radians(360)
        return (
            np.cos(a * x) * np.sin(a * y)
            + np.cos(a * y) * np.sin(a * z)
            + np.cos(a * z) * np.sin(a * x)
        )

    @njit
    def diamond(x, y, z):
        a = np.radians(360.0)
        return (
            np.sin(a * x) * np.sin(a * y) * np.sin(a * z)
            + np.sin(a * x) * np.cos(a * y) * np.cos(a * z)
            + np.cos(a * x) * np.sin(a * y) * np.cos(a * z)
            + np.cos(a * x) * np.cos(a * y) * np.sin(a * z)
        )

    def __init__(
        self,
        size: tuple[int, int, int],
        cells: tuple[int, int, int] = (1, 1, 1),
        func: Callable[[int, int, int], int] = diamond,
        fill: float = 0.0,
        refinement: int = 10,
        px_size: float = None,
        layer_size: float = None,
    ):
        """
        ###### Parameters:
        - size (tuple[int, int, int]): Size of the TPMS unit cell in px/layer space.
        - cells (tuple[int, int, int]): Number of unit cells in each dimension.
        - func (Callable[[float, float, float], bool]): Function defining the TPMS shape.
        - fill (float): Level set value for the TPMS shape ranges from -1 to 1 (isosurface at 0)
        - refinement (int): Number of subdivisions for the level set grid.
        - px_size (float): Pixel size in mm.
        - layer_size (float): Layer height in mm.

        This class generates a TPMS shape using a level set method.
        """
        super().__init__(px_size, layer_size)

        bounds = [
            0.0,
            0.0,
            0.0,
            1.0 * cells[0],
            1.0 * cells[1],
            1.0 * cells[2],
        ]  # bounding box
        # bounds = [0.0, 0.0, 0.0, 10.0, 10.0, 10.0]  # bounding box
        edge_length = 1 / refinement
        self._object = Manifold.level_set(func, bounds, edge_length, level=fill)
        size = (
            size[0] * cells[0],
            size[1] * cells[1],
            size[2] * cells[2],
        )
        self.resize(size)
        self._add_bbox_to_keepout(self._object.bounding_box())
