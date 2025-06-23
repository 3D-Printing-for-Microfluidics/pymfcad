import numpy as np
from typing import Union
from scipy.special import comb

class PolychannelShape:
    def __init__(self, shape_type:str=None, position:tuple[int,int,int]=None, size:tuple[int,int,int]=None, rounded_cube_radius:tuple[float,float,float]=None, rotation:tuple[float,float,float]=None, absolute_position:bool=None, corner_radius:float=None):
        self.shape_type = shape_type  # e.g., "cube", "sphere", "rounded_cube" (default to last shape type)
        self.size = size  # e.g., (width, height, depth) (default to last size)
        self.rounded_cube_radius = rounded_cube_radius  # e.g., (rx, ry, rz) for rounded cubes (default to last radius)
        self.position = position  # e.g., (x, y, z) (default to last position)
        self.rotation = rotation  # e.g., (rx, ry, rz) in degrees (default to no rotation (0, 0, 0))
        self.absolute_position = absolute_position, # If True, position is absolute; if False, relative to last shape (default to False)
        self.corner_radius = corner_radius # e.g. radius for non-manhattan corners (default to 0)

    def __eq__(self, other):
        if isinstance(other, PolychannelShape):
            return (
                self.shape_type == other.shape_type and
                self.size == other.size and
                self.rounded_cube_radius == other.rounded_cube_radius and
                self.position == other.position and
                self.rotation == other.rotation and
                self.absolute_position == other.absolute_position and
                self.corner_radius == other.corner_radius
                )
        return False

    def __ne__(self, other):
        return not self.__eq__(other)
    
class BezierCurveShape:
    def __init__(
        self,
        control_points: list[tuple[int, int, int]],
        number_of_segments: int,
        shape_type: str = None,
        size: tuple[int, int, int] = None,
        position: tuple[int, int, int] = None,
        rounded_cube_radius: tuple[float, float, float] = None,
        rotation: tuple[float, float, float] = None,
        absolute_position: bool = None,
        corner_radius: float = None
    ):
        self.shape_type = shape_type
        self.control_points = control_points
        self.size = size
        self.position = position
        self.rounded_cube_radius = rounded_cube_radius
        self.rotation = rotation
        self.absolute_position = absolute_position
        self.corner_radius = corner_radius
        self.number_of_segments = number_of_segments

    def generate(self, last_shape: PolychannelShape) -> list[PolychannelShape]:
        def bezier(t, points):
            n = len(points) - 1
            return sum(comb(n, i) * (1 - t)**(n - i) * t**i * np.array(p) for i, p in enumerate(points))
        
        def lerp(a, b, t):
            return tuple(a[i] * (1 - t) + b[i] * t for i in range(len(a)))

        shape_type = self.shape_type
        if shape_type != last_shape.shape_type:
            shape_type = "rounded_cube"

        shape.control_points.insert(0, last_shape.position)
        shape.control_points.append(self.position)

        ts = np.linspace(0, 1, self.number_of_segments)
        shapes = []
        for t in ts:
            position = tuple(bezier(t, shape.control_points))
            blended_size = lerp(last_shape.size, self.size, t)
            blended_radius = lerp(last_shape.rounded_cube_radius, shape.rounded_cube_radius, t)
            blended_rotation = lerp(last_shape.rotation, self.rotation, t)

            shape = PolychannelShape(
                shape_type=shape_type,
                size=blended_size,
                rounded_cube_radius=blended_radius,
                position=position,
                rotation=blended_rotation,
                absolute_position=True
            )
            shapes.append(shape)

        return shapes
    
def _validate_polychannel_shapes(shapes: list[Union[PolychannelShape, BezierCurveShape]]) -> list[Union[PolychannelShape, BezierCurveShape]]:
    """
    Validate polychannel shapes to ensure all shapes have a defined type, size, and position.
    This function modifies the input list in place.
    """
    for i, shape in enumerate(shapes):
        if i == 0:
            if shape.shape_type is None:
                raise ValueError("Shape type must be specified for the first shape in a polychannel")
            if shape.size is None:
                raise ValueError("Size must be specified for the first shape in a polychannel")
            if shape.rounded_cube_radius is None and shape.shape_type == "rounded_cube":
                raise ValueError("Rounded cube radius must be specified for the first round cube shape in a polychannel")
            elif shape.shape_type == "cube":
                shape.rounded_cube_radius = (0, 0, 0)
            elif shape.shape_type == "sphere":
                shape.rounded_cube_radius = (shape.size[0]/2, shape.size[1]/2, shape.size[2]/2)
            if shape.position is None:
                shape.position = (0, 0, 0)
            if shape.rotation is None:
                shape.rotation = (0, 0, 0)
            if shape.corner_radius is None:
                shape.corner_radius = 0
            if type(shape) is BezierCurveShape:
                raise ValueError("Bezier curve cannot be the first shape in a polychannel")
        else:
            if shape.shape_type is None:
                shape.shape_type = shape[i-1].shape_type
            if shape.size is None:
                shape.size = shape[i-1].size
            if shape.rounded_cube_radius is None:
                if shape.shape_type == "cube":
                    shape.rounded_cube_radius = (0,0,0)
                elif shape.shape_type == "sphere":
                    shape.rounded_cube_radius = (shape.size[0]/2, shape.size[1]/2, shape.size[2]/2)
                elif shape.shape_type == "rounded_cube":
                    shape.rounded_cube_radius = shape[i-1].rounded_cube_radius
                else:
                    raise ValueError(f"Unsupported shape type: {shape.shape_type}")
            if shape.absolute_position is None:
                shape.absolute_position = False
            if shape.position is None:
                shape.position = shape[i-1].position
            if not shape.absolute_position:
                shape.position = tuple(shape.position[i] + shape[i-1].position[i] for i in range(3))
            if shape.rotation is None:
                shape.rotation = (0, 0, 0)
            if shape.corner_radius is None:
                shape.corner_radius = 0

        if type(shape) is BezierCurveShape:
            if shape.control_points is None or len(shape.control_points) < 2:
                raise ValueError("Bezier curve requires at least 2 control points")
            if not shape.absolute_position:
                shape.control_points = [tuple(np.array(p) + np.array(shape[i - 1].position)) for p in shape.control_points]
            if shape.number_of_segments is None or shape.number_of_segments < 2:
                raise ValueError("Bezier curve requires at least 2 segments")
            
        shape.absolute_position = True

    return shapes
    
def _arc_between_angle_3d(A, B, C, r, n):
    A = np.array(A, dtype=float)
    B = np.array(B, dtype=float)
    C = np.array(C, dtype=float)

    # Unit vectors along BA and BC
    BA = A - B
    BC = C - B
    uBA = BA / np.linalg.norm(BA)
    uBC = BC / np.linalg.norm(BC)

    # r must be less than BA and BC length
    print
    if r > round(np.linalg.norm(BA)) or r > round(np.linalg.norm(BC)):
        print(f"Radius r: {r}")
        print(f"Incoming and outgoing channel lengths: {np.linalg.norm(BA)}, {np.linalg.norm(BC)}")
        raise ValueError("Radius r is larger than incoming and outgoing channel lengths")

    # Angle and bisector
    cos_theta = np.clip(np.dot(uBA, uBC), -1.0, 1.0)
    theta = np.arccos(cos_theta)
    half_theta = theta / 2

    # Distance along BA and BC to arc endpoints
    offset = r / np.tan(half_theta)
    if round(offset) > round(np.linalg.norm(BA)) or round(offset) > round(np.linalg.norm(BC)):
        print(f"Offset: {offset}")
        print(f"Incoming and outgoing channel lengths: {np.linalg.norm(BA)}, {np.linalg.norm(BC)}")
        raise ValueError("Arc radius is too large geometry")
    P1 = B + uBA * offset  # start of arc
    P2 = B + uBC * offset  # end of arc

    # Angle bisector direction
    bisector = (uBA + uBC)
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

    return arc_points

def _round_polychannel_corners(shapes:list[Union[PolychannelShape, BezierCurveShape]], n:int) -> list[Union[PolychannelShape, BezierCurveShape]]:
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
        if shape.corner_radius > 0:
            if i == 0 or i == len(shapes) - 1:
                raise ValueError("First and last shapes in a polychannel cannot have a corner radius")
            # Calculate the arc points
            arc_points = _arc_between_angle_3d(
                shapes[i - 1].position,
                shape.position,
                shapes[i + 1].position,
                shape.corner_radius,
                n
            )
            # Create new rounded shapes from the arc points
            for point in arc_points:
                rounded_shapes.append(PolychannelShape(
                    shape_type=shape.shape_type,
                    position=point,
                    size=shape.size,
                    rounded_cube_radius=shape.rounded_cube_radius,
                    rotation=shape.rotation,
                    absolute_position=True,
                    corner_radius=shape.corner_radius
                ))
        else:
            # If no corner radius, just append the shape as is
            rounded_shapes.append(shape)

    return rounded_shapes

def _expand_bezier_shapes(shapes:list[Union[PolychannelShape, BezierCurveShape]]) -> list[Union[PolychannelShape, BezierCurveShape]]:
    """
    Expand Bezier shapes into a list of PolychannelShapes.
    This function modifies the input list in place.
    """
    expanded_shapes = []
    for shape in shapes:
        if isinstance(shape, BezierCurveShape):
            expanded_shapes.extend(shape.generate(shape))
        else:
            expanded_shapes.append(shape)
    return expanded_shapes

def _preprocess_polychannel_shapes(shapes: list[Union[PolychannelShape, BezierCurveShape]]) -> list[Union[PolychannelShape, BezierCurveShape]]:
    """
    Preprocess polychannel shapes validating their properties, rounding corners, and expanding Bezier curves.
    This function modifies the input list in place.
    """
    shapes = _validate_polychannel_shapes(shapes)
    shapes = _round_polychannel_corners(shapes, 20)
    shapes = _expand_bezier_shapes(shapes)
    return shapes