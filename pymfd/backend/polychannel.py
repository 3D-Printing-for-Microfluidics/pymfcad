import numpy as np
from typing import Union
from scipy.special import comb
from . import Shape, Cube, Sphere, RoundedCube


def _lerp(
    a: tuple[float, float, float], b: tuple[float, float, float], t: float
) -> tuple[float, float, float]:
    """
    Linear interpolation between two points a and b with parameter t.
    Points can be positions, sizes, rounded cube radii, or any other 3D vector.
    a, b: 3 dimensional tuples or lists.
    t: Parameter value (0 <= t <= 1).
    Returns a point that is t percent of the way from a to b.
    """
    return tuple(a[i] * (1 - t) + b[i] * t for i in range(len(a)))


class PolychannelShape:
    """
    ###### Represents a shape in a polychannel.
    """

    def __init__(
        self,
        shape_type: str = None,
        position: tuple[int, int, int] = None,
        size: tuple[int, int, int] = None,
        rounded_cube_radius: tuple[float, float, float] = None,
        rotation: tuple[float, float, float] = None,
        absolute_position: bool = None,
        corner_radius: float = None,
        corner_segments: int = None,
        fn: int = None,
        _no_validation: bool = False,
    ):
        """
        ###### Parameters:
        - shape_type: Type of shape (e.g., "cube", "sphere", "rounded_cube").
        - position: Position of the shape in 3D space (x, y, z).
        - size: Size of the shape (width, height, depth).
        - rounded_cube_radius: Radius for rounded cubes (rx, ry, rz).
        - rotation: Rotation of the shape in degrees (rx, ry, rz).
        - absolute_position: If True, the position is absolute; if False, it is relative to the last shape.
        - corner_radius: Radius for non-manhattan corners.
        - corner_segments: Number of segments for non-manhattan corners.
        - fn: Number of facets for rounded shapes.
        - _no_validation: If True, skip validation (for internal use).

        ###### Default behaviors are as follows:
        - shape_type: Defaults to last shape's shape_type'.
        - size: Defaults to the last shape's size.
        - rounded_cube_radius: Defaults to the last shape's radius
            - cubes have a radius of 0
            - spheres have a radius of (size[0]/2, size[1]/2, size[2]/2)
        - position: Defaults to the last shape's position.
            - If absolute_position is False, it will be relative to the last shape's position.
        - rotation: Defaults to last shape's rotation ((0, 0, 0) if first shape).
        - corner_radius: Defaults the last shape's radius (0 if first shape).
        - corner_segments: Defaults to last shape's segments (10 if not specified).
        - fn: Default to manifold3D's default value (if not specified).

        If the shape is the first in a polychannel, it must have a defined type, size, and position (and rounded_cube_radius if rounded_cube shape).
        """
        self._shape_type = shape_type
        self._size = size
        self._rounded_cube_radius = rounded_cube_radius
        self._position = position
        self._rotation = rotation
        self._absolute_position = absolute_position
        self._corner_radius = corner_radius
        self._corner_segments = corner_segments
        self._fn = fn
        self._no_validation = _no_validation

    def __eq__(self, other) -> bool:
        if isinstance(other, PolychannelShape):
            return (
                self._shape_type == other._shape_type
                and self._size == other._size
                and self._rounded_cube_radius == other._rounded_cube_radius
                and self._position == other._position
                and self._rotation == other._rotation
                and self._absolute_position == other._absolute_position
                and self._corner_radius == other._corner_radius
                and self._corner_segments == other._corner_segments
                and self._fn == other._fn
                and self._no_validation == other._no_validation
            )
        return False

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)


class BezierCurveShape:
    """
    ###### Represents a Bezier curve shape in a polychannel.
    """

    def __init__(
        self,
        control_points: list[tuple[int, int, int]],
        bezier_segments: int,
        shape_type: str = None,
        size: tuple[int, int, int] = None,
        position: tuple[int, int, int] = None,
        rounded_cube_radius: tuple[float, float, float] = None,
        rotation: tuple[float, float, float] = None,
        absolute_position: bool = None,
        corner_radius: float = None,
        corner_segments: int = None,
        fn: int = None,
        _no_validation: bool = False,
    ):
        """
        ###### Parameters:
        - control_points: List of control points defining the Bezier curve.
        - bezier_segments: Number of segments to divide the curve into.

        ###### Inputs for the final shape of the curve:
        - shape_type: Type of shape (e.g., "cube", "sphere", "rounded_cube").
        - size: Size of shape.
        - position: Position of the shape in 3D space.
        - rounded_cube_radius: Radius (if rounded cube).
        - rotation: Rotation of the shape in degrees (x, y, z).
        - absolute_position: If True, the position is absolute; if False, it is relative to the last shape.
        - corner_radius: Radius for non-manhattan corners.
        - corner_segments: Number of segments for non-manhattan corners.
        - fn: Number of facets for rounded shapes.
        - _no_validation: If True, skip validation (for internal use).

        ###### Default behaviors are as follows:
        - shape_type: Defaults to last shape's shape_type'.
        - size: Defaults to the last shape's size.
        - rounded_cube_radius: Defaults to the last shape's radius
            - cubes have a radius of 0
            - spheres have a radius of (size[0]/2, size[1]/2, size[2]/2)
        - position: Defaults to the last shape's position.
            - If absolute_position is False, it will be relative to the last shape's position.
        - rotation: Defaults to last shape's rotation ((0, 0, 0) if first shape).
        - corner_radius: Defaults to last shape's radius (0 if first shape).
        - corner_segments: Defaults to last shape's segments (10 if not specified).
        - fn: Default to manifold3D's default value (if not specified).

        ###### Bezier curves cannot be the first shape in a polychannel!
        """
        self._shape_type = shape_type
        self._control_points = control_points
        self._bezier_segments = bezier_segments
        self._size = size
        self._position = position
        self._rounded_cube_radius = rounded_cube_radius
        self._rotation = rotation
        self._absolute_position = absolute_position
        self._corner_radius = corner_radius
        self._corner_segments = corner_segments
        self._fn = fn
        self._no_validation = _no_validation

    def __eq__(self, other) -> bool:
        if isinstance(other, BezierCurveShape):
            return (
                self._shape_type == other._shape_type
                and self._size == other._size
                and self._rounded_cube_radius == other._rounded_cube_radius
                and self._position == other._position
                and self._rotation == other._rotation
                and self._absolute_position == other._absolute_position
                and self._corner_radius == other._corner_radius
                and self._corner_segments == other._corner_segments
                and self._control_points == other._control_points
                and self._bezier_segments == other._bezier_segments
                and self._fn == other._fn
                and self._no_validation == other._no_validation
            )
        return False

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)

    def _generate(self, last_shape: PolychannelShape) -> list[PolychannelShape]:
        """Generate a list of PolychannelShape objects representing the Bezier curve."""

        def _bezier(
            t: float, points: list[tuple[int, int, int]]
        ) -> tuple[float, float, float]:
            """
            Calculate a point on the Bezier curve at parameter t using the Bernstein polynomial.
            points: List of control points defining the Bezier curve.
            t: Parameter value (0 <= t <= 1).
            Returns the point on the curve as a tuple (x, y, z).
            """
            n = len(points) - 1
            return sum(
                comb(n, i) * (1 - t) ** (n - i) * t**i * np.array(p)
                for i, p in enumerate(points)
            )

        shape_type = self._shape_type
        if shape_type != last_shape._shape_type:
            shape_type = "rounded_cube"

        self._control_points.insert(0, last_shape._position)
        self._control_points.append(self._position)

        ts = np.linspace(0, 1, self._bezier_segments)
        shapes = []
        for t in ts:
            position = tuple(_bezier(t, self._control_points))
            blended_size = _lerp(last_shape._size, self._size, t)
            blended_radius = _lerp(
                last_shape._rounded_cube_radius, self._rounded_cube_radius, t
            )
            blended_rotation = _lerp(last_shape._rotation, self._rotation, t)

            _no_validation = True
            if t == 0 or t == 1:
                _no_validation = False

            shape = PolychannelShape(
                shape_type=shape_type,
                size=blended_size,
                rounded_cube_radius=blended_radius,
                position=position,
                rotation=blended_rotation,
                absolute_position=True,
                fn=self._fn,
                _no_validation=_no_validation,
            )
            shapes.append(shape)

        return shapes


class Polychannel(Shape):
    """
    ###### Represents a polychannel, which is a collection of shapes that are hulls of each other.
    ###### It can contain PolychannelShape and BezierCurveShape objects..
    ###### The shapes are automatically validated and rounded corners are created for non-manhattan corners.
    """

    def __init__(
        self,
        shapes: list[Union["PolychannelShape", "BezierCurveShape"]],
        px_size: float = 0.0076,
        layer_size: float = 0.01,
        show_only_shapes: bool = False,
    ):
        """
        ###### Initialize a Polychannel object.
        ###### Parameters:
        - shapes: List of PolychannelShape or BezierCurveShape objects defining the polychannel.
        - px_size: Pixel size in mm (default: 0.0076).
        - layer_size: Layer size in mm (default: 0.01).
        - show_only_shapes: If True, only show the shapes without hulls (default: False).
        """
        super().__init__(px_size, layer_size)
        shape_list = []
        shapes = self._validate_polychannel_shapes(shapes)
        shapes = self._round_polychannel_corners(shapes, px_size, layer_size)
        shapes = self._expand_bezier_shapes(shapes)
        for shape in shapes:
            if shape._shape_type == "cube":
                s = Cube(
                    shape._size,
                    px_size,
                    layer_size,
                    center=True,
                    _no_validation=shape._no_validation,
                )
            elif shape._shape_type == "sphere":
                s = Sphere(
                    shape._size,
                    px_size,
                    layer_size,
                    center=True,
                    fn=shape._fn,
                    _no_validation=shape._no_validation,
                )
            elif shape._shape_type == "rounded_cube":
                s = RoundedCube(
                    shape._size,
                    shape._rounded_cube_radius,
                    px_size,
                    layer_size,
                    center=True,
                    fn=shape._fn,
                    _no_validation=shape._no_validation,
                )
            else:
                raise ValueError(f"Unsupported shape type: {shape._shape_type}")
            s.rotate(shape._rotation)
            s.translate(shape._position)
            shape_list.append(s)

        # Hull shapes pairwise
        if len(shape_list) > 1:
            if show_only_shapes:
                path = shape_list[0]
                for shape in shape_list[1:]:
                    path += shape
            else:
                path = shape_list[0].hull(shape_list[1])
                last_shape = shape_list[1]
                for shape in shape_list[2:]:
                    path += last_shape.hull(shape)
                    last_shape = shape
            self._object = path._object
            self._keepouts = path._keepouts
        else:
            raise ValueError("Polychannel requires at least 2 shapes")

    def _validate_polychannel_shapes(
        self,
        shapes: list[Union[PolychannelShape, BezierCurveShape]],
    ) -> list[Union[PolychannelShape, BezierCurveShape]]:
        """
        Validate polychannel shapes to ensure all shapes have a defined type, size, and position.
        This function modifies the input list in place.
        """
        for i, shape in enumerate(shapes):
            if i == 0:
                if shape._shape_type is None:
                    raise ValueError(
                        "Shape type must be specified for the first shape in a polychannel"
                    )
                if shape._size is None:
                    raise ValueError(
                        "Size must be specified for the first shape in a polychannel"
                    )
                if (
                    shape._rounded_cube_radius is None
                    and shape._shape_type == "rounded_cube"
                ):
                    raise ValueError(
                        "Rounded cube radius must be specified for the first round cube shape in a polychannel"
                    )
                elif shape._shape_type == "cube":
                    shape._rounded_cube_radius = (0, 0, 0)
                elif shape._shape_type == "sphere":
                    shape._rounded_cube_radius = (
                        shape._size[0] / 2,
                        shape._size[1] / 2,
                        shape._size[2] / 2,
                    )
                if shape._position is None:
                    shape._position = (0, 0, 0)
                if type(shape) is BezierCurveShape:
                    raise ValueError(
                        "Bezier curve cannot be the first shape in a polychannel"
                    )
                if shape._corner_radius is None:
                    shape._corner_radius = 0
                if shape._corner_segments is None:
                    shape._corner_segments = 10
                if shape._rotation is None:
                    shape._rotation = (0, 0, 0)
            else:
                if shape._shape_type is None:
                    shape._shape_type = shapes[i - 1]._shape_type
                if shape._size is None:
                    shape._size = shapes[i - 1]._size
                if shape._rounded_cube_radius is None:
                    if shape._shape_type == "cube":
                        shape._rounded_cube_radius = (0, 0, 0)
                    elif shape._shape_type == "sphere":
                        shape._rounded_cube_radius = (
                            shape._size[0] / 2,
                            shape._size[1] / 2,
                            shape._size[2] / 2,
                        )
                    elif shape._shape_type == "rounded_cube":
                        shape._rounded_cube_radius = shapes[i - 1]._rounded_cube_radius
                    else:
                        raise ValueError(f"Unsupported shape type: {shape._shape_type}")
                if shape._absolute_position is None:
                    shape._absolute_position = False
                if shape._position is None:
                    shape._position = shapes[i - 1]._position
                if not shape._absolute_position:
                    shape._position = tuple(
                        shape._position[j] + shapes[i - 1]._position[j] for j in range(3)
                    )
                if shape._corner_radius is None:
                    shape._corner_radius = shapes[i - 1]._corner_radius
                if shape._corner_segments is None:
                    shape._corner_segments = shapes[i - 1]._corner_segments
                if shape._rotation is None:
                    shape._rotation = shapes[i - 1]._rotation

            if type(shape) is BezierCurveShape:
                if shape._control_points is None or len(shape._control_points) < 1:
                    raise ValueError("Bezier curve requires at least 1 control points")
                if not shape._absolute_position:
                    shape._control_points = [
                        tuple(np.array(p) + np.array(shapes[i - 1]._position))
                        for p in shape._control_points
                    ]
                if shape._bezier_segments is None or shape._bezier_segments < 2:
                    raise ValueError("Bezier curve requires at least 2 segments")

            shape._absolute_position = True

        return shapes

    def _round_polychannel_corners(
        self,
        shapes: list[Union[PolychannelShape, BezierCurveShape]],
        px_size: float,
        layer_size: float,
    ) -> list[Union[PolychannelShape, BezierCurveShape]]:
        """
        Use arc function to create non-manhattan corners for polychannel shapes.
        Loop through all shapes. If corner radius is 0 (or None initially) do nothing. If it is not 0, replace it with the arc shapes.
        For future shapes if there radius is None, use the last shape's radius.
        If there are less than 3 shapes, return the shapes as is. The first and last shape cannot have a corner radius.
        """
        if len(shapes) < 3:
            return shapes

        # Create a new list to hold the rounded shapes
        rounded_shapes = []
        for i, shape in enumerate(shapes):
            if shape._corner_radius > 0:
                if i == 0 or i == len(shapes) - 1:
                    raise ValueError(
                        "First and last shapes in a polychannel cannot have a corner radius"
                    )
                # Calculate the arc points
                arc_points, rotations, start_dir, end_dir = self._arc_between_angle_3d(
                    shapes[i - 1]._position,
                    shape._position,
                    shapes[i + 1]._position,
                    shape._corner_radius,
                    shape._corner_segments,
                )
                if arc_points is None:
                    # Straight line, no arc needed
                    rounded_shapes.append(shape)
                    continue

                # Blend the start and end sizes in real space
                start_size = list(shape._size)
                start_size[0] = start_size[0] * px_size
                start_size[1] = start_size[1] * px_size
                start_size[2] = start_size[2] * layer_size
                end_size = start_size.copy()
                start_size[start_dir] = 0
                end_size[end_dir] = end_size[start_dir]
                end_size[start_dir] = 0

                # Create new rounded shapes from the arc points
                ts = np.linspace(0, 1, shape._corner_segments)
                for point, rotation, t in zip(arc_points, rotations, ts):
                    # Interpolate the size based on the parameter t and convert back to px/layer
                    size = list(_lerp(start_size, end_size, t))
                    size[0] = size[0] / px_size
                    size[1] = size[1] / px_size
                    size[2] = size[2] / layer_size

                    _no_validation = True
                    if t == 0:
                        _no_validation = False

                    rounded_shapes.append(
                        PolychannelShape(
                            shape_type=shape._shape_type,
                            position=point,
                            size=size,
                            rounded_cube_radius=shape._rounded_cube_radius,
                            rotation=tuple(
                                a + b for a, b in zip(shape._rotation, rotation)
                            ),
                            absolute_position=True,
                            corner_radius=shape._corner_radius,
                            _no_validation=_no_validation,
                        )
                    )
            else:
                # If no corner radius, just append the shape as is
                rounded_shapes.append(shape)

        return rounded_shapes

    def _arc_between_angle_3d(
        self,
        A: tuple[int, int, int],
        B: tuple[int, int, int],
        C: tuple[int, int, int],
        r: float,
        n: int,
    ) -> tuple[
        list[tuple[float, float, float]], list[tuple[float, float, float]], int, int
    ]:
        """
        ###### Calculate a 3D arc between points A, B, and C with radius r.
        ###### Parameters:
        - A: Start point of the arc.
        - B: Middle point of the arc (where the arc starts and ends).
        - C: End point of the arc.
        - r: Radius of the arc.
        - n: Number of points to generate along the arc.

        ###### Returns:
        - arc_points: List of points along the arc.
        - rotation_vectors: List of rotation vectors for each point.
        - start_dir: Index of the direction along BA (0 for x, 1 for y, 2 for z).
        - end_dir: Index of the direction along BC (0 for x, 1 for y, 2 for z).
        """
        A = np.array(A, dtype=float)
        B = np.array(B, dtype=float)
        C = np.array(C, dtype=float)

        # Unit vectors along BA and BC
        BA = A - B
        BC = C - B
        uBA = BA / np.linalg.norm(BA)
        uBC = BC / np.linalg.norm(BC)

        # r must be less than BA and BC length
        if r > round(np.linalg.norm(BA)) or r > round(np.linalg.norm(BC)):
            print(f"Radius r: {r}")
            print(
                f"Incoming and outgoing channel lengths: {np.linalg.norm(BA)}, {np.linalg.norm(BC)}"
            )
            raise ValueError(
                "Radius r is larger than incoming and outgoing channel lengths"
            )

        # Angle and bisector
        cos_theta = np.clip(np.dot(uBA, uBC), -1.0, 1.0)
        theta = np.arccos(cos_theta)
        half_theta = theta / 2

        # Distance along BA and BC to arc endpoints
        offset = r / np.tan(half_theta)
        if round(offset) > round(np.linalg.norm(BA)) or round(offset) > round(
            np.linalg.norm(BC)
        ):
            print(f"Offset: {offset}")
            print(
                f"Incoming and outgoing channel lengths: {np.linalg.norm(BA)}, {np.linalg.norm(BC)}"
            )
            raise ValueError("Arc radius is too large geometry")
        P1 = B + uBA * offset  # start of arc
        P2 = B + uBC * offset  # end of arc

        # Angle bisector direction
        bisector = uBA + uBC
        if np.linalg.norm(bisector) == 0:
            return None, None, None, None  # Straight line, no arc needed
        bisector /= np.linalg.norm(bisector)

        # Arc center lies along the bisector
        center = B + bisector * (r / np.sin(half_theta))

        # Construct local 2D basis for arc plane
        v1 = P1 - center
        v2 = P2 - center

        # Normal to arc plane
        normal = np.cross(v1, v2)
        normal /= np.linalg.norm(normal)

        # Basis vectors in the arc plane
        u = v1 / np.linalg.norm(v1)
        v = np.cross(normal, u)
        v /= np.linalg.norm(v)

        # Angles for sweep
        start_angle = 0
        end_angle = np.arctan2(np.dot(v2, v), np.dot(v2, u))

        # Ensure shortest arc (toward B)
        if end_angle < 0:
            end_angle += 2 * np.pi
        if end_angle > np.pi:
            end_angle -= 2 * np.pi

        # Generate arc points
        angles = np.linspace(start_angle, end_angle, n)
        arc_points = [center + r * (np.cos(a) * u + np.sin(a) * v) for a in angles]

        rotation_vectors = [tuple(normal * np.degrees(a)) for a in angles]
        return (
            arc_points,
            rotation_vectors,
            np.argmax(np.abs(uBA)),
            np.argmax(np.abs(uBC)),
        )

    def _expand_bezier_shapes(
        self,
        shapes: list[Union[PolychannelShape, BezierCurveShape]],
    ) -> list[Union[PolychannelShape, BezierCurveShape]]:
        """
        Expand Bezier shapes into a list of PolychannelShapes.
        This function modifies the input list in place.
        """
        expanded_shapes = []
        for i, shape in enumerate(shapes):
            if isinstance(shape, BezierCurveShape):
                expanded_shapes.extend(shape._generate(shapes[i - 1]))
            else:
                expanded_shapes.append(shape)
        return expanded_shapes
