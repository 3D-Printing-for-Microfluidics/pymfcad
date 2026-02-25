import numpy as np
from typing import Union
from scipy.special import comb
from . import Shape, Cube, Sphere, RoundedCube


def _lerp(
    a: tuple[float, float, float], b: tuple[float, float, float], t: float
) -> tuple[float, float, float]:
    """
    Linearly interpolate between two 3D points.

    Parameters:

    - a (tuple[float, float, float]): Start point.
    - b (tuple[float, float, float]): End point.
    - t (float): Parameter value from 0 to 1.

    Returns:

    - tuple[float, float, float]: Interpolated point.
    """
    return tuple(a[i] * (1 - t) + b[i] * t for i in range(len(a)))


class PolychannelShape:
    """
    Represents a shape in a polychannel.
    """

    def __init__(
        self,
        shape_type: str | None = None,
        position: tuple[int, int, int] | None = None,
        size: tuple[int, int, int] | None = None,
        rounded_cube_radius: tuple[float, float, float] | None = None,
        rotation: tuple[float, float, float] | None = None,
        absolute_position: bool | None = None,
        corner_radius: float | None = None,
        corner_segments: int | None = None,
        fn: int | None = None,
        _no_validation: bool = False,
    ) -> None:
        """
        Initialize a polychannel shape definition.

        Parameters:

        - shape_type (str | None): Type of shape (e.g., "cube", "sphere", "rounded_cube").
        - position (tuple[int, int, int] | None): Position of the shape in 3D space (x, y, z).
        - size (tuple[int, int, int] | None): Size of the shape (width, height, depth).
        - rounded_cube_radius (tuple[float, float, float] | None): Radius for rounded cubes (rx, ry, rz).
        - rotation (tuple[float, float, float] | None): Rotation of the shape in degrees (rx, ry, rz).
        - absolute_position (bool | None): If True, the position is absolute; if False, it is relative to the last shape.
        - corner_radius (float | None): Radius for non-manhattan corners.
        - corner_segments (int | None): Number of segments for non-manhattan corners.
        - fn (int | None): Number of facets for rounded shapes.
        - _no_validation (bool): If True, skip validation (for internal use).

        Default behaviors are as follows:

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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PolychannelShape):
            return False

        def _eq_field(a: object, b: object) -> bool:
            # Compare numpy arrays or array-like objects properly
            if isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
                return np.array_equal(a, b)
            # Compare tuples/lists of numbers (possibly from numpy)
            if isinstance(a, (tuple, list, np.ndarray)) and isinstance(
                b, (tuple, list, np.ndarray)
            ):
                try:
                    return np.allclose(np.array(a), np.array(b))
                except Exception:
                    return a == b
            return a == b

        return (
            self._shape_type == other._shape_type
            and _eq_field(self._size, other._size)
            and _eq_field(self._rounded_cube_radius, other._rounded_cube_radius)
            and _eq_field(self._position, other._position)
            and _eq_field(self._rotation, other._rotation)
            and self._absolute_position == other._absolute_position
            and self._corner_radius == other._corner_radius
            and self._corner_segments == other._corner_segments
            and self._fn == other._fn
            and self._no_validation == other._no_validation
        )

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)


class BezierCurveShape:
    """
    Represents a Bezier curve shape in a polychannel.
    """

    def __init__(
        self,
        control_points: list[tuple[int, int, int]],
        bezier_segments: int,
        shape_type: str | None = None,
        size: tuple[int, int, int] | None = None,
        position: tuple[int, int, int] | None = None,
        rounded_cube_radius: tuple[float, float, float] | None = None,
        rotation: tuple[float, float, float] | None = None,
        absolute_position: bool | None = None,
        corner_radius: float | None = None,
        corner_segments: int | None = None,
        fn: int | None = None,
        _no_validation: bool = False,
    ) -> None:
        """
        Initialize a Bezier curve shape definition.

        Parameters:

        - control_points (list[tuple[int, int, int]]): List of control points defining the Bezier curve.
        - bezier_segments (int): Number of segments to divide the curve into.
        - shape_type (str | None): Type of shape (e.g., "cube", "sphere", "rounded_cube").
        - size (tuple[int, int, int] | None): Size of shape.
        - position (tuple[int, int, int] | None): Position of the shape in 3D space.
        - rounded_cube_radius (tuple[float, float, float] | None): Radius (if rounded cube).
        - rotation (tuple[float, float, float] | None): Rotation of the shape in degrees (x, y, z).
        - absolute_position (bool | None): If True, the position is absolute; if False, it is relative to the last shape.
        - corner_radius (float | None): Radius for non-manhattan corners.
        - corner_segments (int | None): Number of segments for non-manhattan corners.
        - fn (int | None): Number of facets for rounded shapes.
        - _no_validation (bool): If True, skip validation (for internal use).

        Default behaviors are as follows:

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

        Bezier curves cannot be the first shape in a polychannel!
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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BezierCurveShape):
            return False

        def _eq_field(a: object, b: object) -> bool:
            # Compare numpy arrays or array-like objects properly
            if isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
                return np.array_equal(a, b)
            # Compare tuples/lists of numbers (possibly from numpy)
            if isinstance(a, (tuple, list, np.ndarray)) and isinstance(
                b, (tuple, list, np.ndarray)
            ):
                try:
                    print(f"Comparing {a} and {b} with allclose")
                    print(f"np.array(a) = {np.array(a)}, np.array(b) = {np.array(b)}")
                    print(f"allclose result: {np.allclose(np.array(a), np.array(b))}")
                    return np.allclose(np.array(a), np.array(b))
                except Exception:
                    return a == b
            return a == b

        return (
            self._shape_type == other._shape_type
            and _eq_field(self._size, other._size)
            and _eq_field(self._rounded_cube_radius, other._rounded_cube_radius)
            and _eq_field(self._position, other._position)
            and _eq_field(self._rotation, other._rotation)
            and self._absolute_position == other._absolute_position
            and self._corner_radius == other._corner_radius
            and self._corner_segments == other._corner_segments
            and _eq_field(self._control_points, other._control_points)
            and self._bezier_segments == other._bezier_segments
            and self._fn == other._fn
            and self._no_validation == other._no_validation
        )

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def _generate(self, last_shape: PolychannelShape) -> list[PolychannelShape]:
        """
        Generate a list of PolychannelShape objects representing the Bezier curve.

        Parameters:

        - last_shape (PolychannelShape): The previous shape to interpolate from.

        Returns:

        - list[PolychannelShape]: Shapes along the curve.
        """

        def _bezier(
            t: float, points: list[tuple[int, int, int]]
        ) -> tuple[float, float, float]:
            """
            Calculate a point on the Bezier curve using the Bernstein polynomial.

            Parameters:

            - t (float): Parameter value from 0 to 1.
            - points (list[tuple[int, int, int]]): Control points defining the curve.

            Returns:

            - tuple[float, float, float]: Point on the curve.
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
    A polychannel is a collection of shapes that are hulled together.

    It can contain PolychannelShape and BezierCurveShape objects.
    
    The shapes are automatically validated and rounded corners are created for non-manhattan corners.
    """

    def __init__(
        self,
        shapes: list[Union["PolychannelShape", "BezierCurveShape"]],
        show_only_shapes: bool = False,
        quiet: bool = False,
    ) -> None:
        """
        Initialize a Polychannel object.

        Parameters:

        - shapes (list[Union[PolychannelShape, BezierCurveShape]]): Shapes defining the polychannel.
        - show_only_shapes (bool): If True, only show the shapes without hulls.
        - quiet (bool): If True, suppresses informational output.

        Raises:

        - ValueError: Polychannel requires at least 2 shapes or an unsupported shape type is used.
        """
        super().__init__()
        shape_list = []
        shapes = self._validate_polychannel_shapes(shapes)
        shapes = self._round_polychannel_corners(shapes)
        shapes = self._expand_bezier_shapes(shapes)
        for shape in shapes:
            if shape._shape_type == "cube":
                s = Cube(
                    shape._size,
                    center=True,
                    quiet=quiet,
                    _no_validation=shape._no_validation,

                )
            elif shape._shape_type == "sphere":
                s = Sphere(
                    shape._size,
                    center=True,
                    fn=shape._fn,
                    quiet=quiet,
                    _no_validation=shape._no_validation,
                )
            elif shape._shape_type == "rounded_cube":
                s = RoundedCube(
                    shape._size,
                    shape._rounded_cube_radius,
                    center=True,
                    fn=shape._fn,
                    quiet=quiet,
                    _no_validation=shape._no_validation,
                )
            else:
                raise ValueError(f"Unsupported shape type: {shape._shape_type}")
            s.rotate(shape._rotation)
            s.translate(shape._position)
            shape_list.append(s)

        # Hull shapes pairwise to form a continuous channel.
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

        Parameters:

        - shapes (list[Union[PolychannelShape, BezierCurveShape]]): Shapes to validate.

        Returns:

        - list[Union[PolychannelShape, BezierCurveShape]]: Validated shapes.

        Raises:

        - ValueError: Required shape fields are missing or unsupported types are used.
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
    ) -> list[Union[PolychannelShape, BezierCurveShape]]:
        """
        Use arc function to create non-manhattan corners for polychannel shapes.

        Loop through all shapes. If corner radius is 0 (or None initially) do nothing. If it is not 0, replace it with the arc shapes.

        For future shapes if there radius is None, use the last shape's radius.

        If there are less than 3 shapes, return the shapes as is. The first and last shape cannot have a corner radius.

        Parameters:

        - shapes (list[Union[PolychannelShape, BezierCurveShape]]): Shapes to round.

        Returns:

        - list[Union[PolychannelShape, BezierCurveShape]]: Shapes with rounded corners.

        Raises:

        - ValueError: First/last shapes have a corner radius or radius exceeds segment lengths.
        """
        if len(shapes) < 3:
            return shapes

        rounded_shapes = []
        for i, shape in enumerate(shapes):
            if shape._corner_radius > 0:
                if i == 0 or i == len(shapes) - 1:
                    raise ValueError(
                        "First and last shapes in a polychannel cannot have a corner radius"
                    )
                # Calculate the arc points and local rotations.
                arc_points, rotations, start_dir, end_dir = self._arc_between_angle_3d(
                    shapes[i - 1]._position,
                    shape._position,
                    shapes[i + 1]._position,
                    shape._corner_radius,
                    shape._corner_segments,
                )
                if arc_points is None:
                    # Straight line, no arc needed.
                    rounded_shapes.append(shape)
                    continue

                # Blend the start/end sizes along the arc.
                start_size = list(shape._size)
                end_size = start_size.copy()
                start_size[start_dir] = 0
                end_size[end_dir] = end_size[start_dir]
                end_size[start_dir] = 0

                # Create rounded shapes along the arc.
                ts = np.linspace(0, 1, shape._corner_segments)
                for point, rotation, t in zip(arc_points, rotations, ts):
                    # Interpolate the size based on the parameter t and convert back to px/layer
                    size = list(_lerp(start_size, end_size, t))

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
        list[tuple[float, float, float]] | None,
        list[tuple[float, float, float]] | None,
        int | None,
        int | None,
    ]:
        """
        Calculate a 3D arc between points A, B, and C with radius r.

        Parameters:

        - A (tuple[int, int, int]): Start point of the arc.
        - B (tuple[int, int, int]): Middle point of the arc (where the arc starts and ends).
        - C (tuple[int, int, int]): End point of the arc.
        - r (float): Radius of the arc.
        - n (int): Number of points to generate along the arc.

        Returns:

        - list[tuple[float, float, float]] | None: Points along the arc.
        - list[tuple[float, float, float]] | None: Rotation vectors for each point.
        - int | None: Index of the direction along BA (0 for x, 1 for y, 2 for z).
        - int | None: Index of the direction along BC (0 for x, 1 for y, 2 for z).

        Raises:

        - ValueError: Radius exceeds incoming or outgoing channel lengths.
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
            print(f"\tℹ️ Radius r: {r}")
            print(
                f"\tℹ️ Incoming and outgoing channel lengths: {np.linalg.norm(BA)}, {np.linalg.norm(BC)}"
            )
            raise ValueError(
                "❌ Radius r is larger than incoming and outgoing channel lengths"
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
            print(f"\tℹ️ Offset: {offset}")
            print(
                f"\tℹ️ Incoming and outgoing channel lengths: {np.linalg.norm(BA)}, {np.linalg.norm(BC)}"
            )
            raise ValueError("❌ Arc radius is too large geometry")
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

        Parameters:

        - shapes (list[Union[PolychannelShape, BezierCurveShape]]): Shapes to expand.

        Returns:

        - list[Union[PolychannelShape, BezierCurveShape]]: Expanded shape list.
        """
        expanded_shapes = []
        for i, shape in enumerate(shapes):
            if isinstance(shape, BezierCurveShape):
                expanded_shapes.extend(shape._generate(shapes[i - 1]))
            else:
                expanded_shapes.append(shape)
        return expanded_shapes
