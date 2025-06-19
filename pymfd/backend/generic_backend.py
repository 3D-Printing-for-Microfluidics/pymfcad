from __future__ import annotations

import functools
import numpy as np
from enum import Enum
from abc import ABC, abstractmethod

def _is_integer(val: float) -> bool:
    return abs(val - round(val)) < 1e-6

class Backend(ABC):
    """
    Abstract base class for all backends.
    """
    def set_fn(self, fn):
        """
        Set the number of facets for the shapes.

        Input:
        - fn (int): The number of facets.
        """
        pass

    class Shape(ABC):
        """
        Abstract base class for all shapes.
        """
        @abstractmethod
        def __init__(self, px_size:float, layer_size:float):
            """
            Initialize the shape.

            Input:
            - px_size (float): The size of the pixels.
            - layer_size (float): The size of the layers.
            """
            self.name = None
            self.parent = None
            self.color = None
            self.px_size = px_size
            self.layer_size = layer_size
            self.object = None
            self.keepouts = []

        def _translate_keepouts(self, translation: tuple[float, float, float]):
            """
            Translate the keepouts.

            Input:
            - translation (tuple[float, float, float]): The translation.
            """
            dx, dy, dz = translation
            self.keepouts = [
                [x0 + dx, y0 + dy, z0 + dz, x1 + dx, y1 + dy, z1 + dz]
                for x0, y0, z0, x1, y1, z1 in self.keepouts
            ]

        def _rotate_point(self, point:tuple[float, float, float], rotation:tuple[float, float, float]):
            """
            Rotate a point around origin (0,0,0) with Euler angles (in degrees) in XYZ order.
            
            Input:
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
            Rotate the keepouts.

            Input:
            - rotation (tuple[float, float, float]): The rotation.
            """
            rotated_keepouts = []
            for x0, y0, z0, x1, y1, z1 in self.keepouts:
                # Get all 8 corners
                corners = [
                    [x, y, z]
                    for x in (x0, x1)
                    for y in (y0, y1)
                    for z in (z0, z1)
                ]
                rotated_corners = [self._rotate_point(pt, rotation) for pt in corners]
                xs, ys, zs = zip(*rotated_corners)
                rotated_keepouts.append([min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)])
            self.keepouts = rotated_keepouts

        def _scale_keepouts(self, scale: tuple[float, float, float]) -> None:
            """
            Scale the keepouts.

            Input:
            - scale (tuple[float, float, float]): The scale.
            """
            sx, sy, sz = scale
            self.keepouts = [
                [
                    x0 * sx,
                    y0 * sy,
                    z0 * sz,
                    x1 * sx,
                    y1 * sy,
                    z1 * sz,
                ]
                for x0, y0, z0, x1, y1, z1 in self.keepouts
            ]

        def _mirror_keepouts(self, axis: tuple[bool, bool, bool]):
            """
            Mirror the keepouts.

            Input:
            - axis (tuple[bool, bool, bool]): The axis to mirror.
            """
            flip_x, flip_y, flip_z = axis
            new_keepouts = []
            for x0, y0, z0, x1, y1, z1 in self.keepouts:
                nx0, nx1 = sorted([-x0, -x1]) if flip_x else (x0, x1)
                ny0, ny1 = sorted([-y0, -y1]) if flip_y else (y0, y1)
                nz0, nz1 = sorted([-z0, -z1]) if flip_z else (z0, z1)
                new_keepouts.append([nx0, ny0, nz0, nx1, ny1, nz1])
            self.keepouts = new_keepouts

        @abstractmethod
        def translate(self, translation:tuple[int, int, int]) -> 'Shape':
            """
            Translate the shape.

            Input:
            - translation (tuple[int, int, int]): The translation.

            Returns:
            - self (Shape): The translated shape.
            """
            self._translate_keepouts(translation)

        @abstractmethod
        def rotate(self, rotation:tuple[float, float, float]) -> 'Shape':
            """
            Rotate the shape.

            Input:
            - rotation (tuple[float, float, float]): The rotation.

            Returns:
            - self (Shape): The rotated shape.
            """
            self._rotate_keepouts(rotation)

        @abstractmethod
        def resize(self, size:tuple[int, int, int]) -> 'Shape':
            """
            Resize the shape.

            Input:
            - size (tuple[int, int, int]): The size.

            Returns:
            - self (Shape): The resized shape.
            """
            bounds = self.object.bounding_box()
            sx = size[0] / (bounds[3] - bounds[0])/self.px_size
            sy = size[1] / (bounds[4] - bounds[1])/self.px_size
            sz = size[2] / (bounds[5] - bounds[2])/self.layer_size

            self._scale_keepouts((sx, sy, sz))

        @abstractmethod
        def mirror(self, axis:tuple[bool, bool, bool]) -> 'Shape':
            """
            Mirror the shape.

            Input:
            - axis (tuple[bool, bool, bool]): The axis to mirror.

            Returns:
            - self (Shape): The mirrored shape.
            """
            self._mirror_keepouts(axis)

        @abstractmethod
        def __add__(self, other:'Shape') -> 'Shape': # union
            """
            Union the shape with another shape.

            Input:
            - other (Shape): The other shape.

            Returns:
            - self (Shape): The union of the two shapes.
            """
            self.keepouts.extend(other.keepouts)

        @abstractmethod
        def __sub__(self, other:'Shape') -> 'Shape': # difference
            """
            Difference the shape with another shape.

            Input:
            - other (Shape): The other shape.

            Returns:
            - self (Shape): The difference of the two shapes.
            """
            pass

        @abstractmethod
        def hull(self, other:'Shape') -> 'Shape':
            """
            Hull the shape with another shape.

            Input:
            - other (Shape): The other shape.

            Returns:
            - self (Shape): The hull of the two shapes.
            """
            # Combine keepouts
            self.keepouts.extend(other.keepouts)

            # Get both bounding boxes
            b1 = self.object.bounding_box()
            b1 = (b1[0]/self.px_size, b1[1]/self.px_size, b1[2]/self.layer_size, b1[3]/self.px_size, b1[4]/self.px_size, b1[5]/self.layer_size)
            b2 = other.object.bounding_box()
            b2 = (b2[0]/self.px_size, b2[1]/self.px_size, b2[2]/self.layer_size, b2[3]/self.px_size, b2[4]/self.px_size, b2[5]/self.layer_size)

            # Determine bridge keepout bounds
            x0 = min(b1[0], b2[0])
            y0 = min(b1[1], b2[1])
            z0 = min(b1[2], b2[2])
            x1 = max(b1[3], b2[3])
            y1 = max(b1[4], b2[4])
            z1 = max(b1[5], b2[5])

            # Determine the separation axis
            size1 = (b1[3] - b1[0], b1[4] - b1[1], b1[5] - b1[2])
            size2 = (b2[3] - b2[0], b2[4] - b2[1], b2[5] - b2[2])

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

            self.keepouts.append([
                bridge_min[0], bridge_min[1], bridge_min[2],
                bridge_max[0], bridge_max[1], bridge_max[2]
            ])

        def add_bbox_to_keepout(self, bbox:tuple[float]):
            # add keepout
            bbox = (bbox[0]/self.px_size, bbox[1]/self.px_size, bbox[2]/self.layer_size, bbox[3]/self.px_size, bbox[4]/self.px_size, bbox[5]/self.layer_size)
            self.keepouts.append(bbox)

    class Cube(Shape, ABC):
        """
        Abstract base class for all cube shapes.
        """
        @abstractmethod
        def __init__(self, size:tuple[int, int, int], px_size:float, layer_size:float, center:bool=False):
            """
            Initialize the cube shape.

            Input:
            - size (tuple[int, int, int]): The size of the cube.
            - px_size (float): The size of the pixels.
            - layer_size (float): The size of the layers.
            - center (bool): Whether to center the cube.
            """
            super().__init__(px_size, layer_size)

    class Cylinder(Shape, ABC):
        """
        Abstract base class for all cylinder shapes.
        """
        @abstractmethod
        def __init__(self, height:int, radius:float=None, bottom_r:float=None, top_r:float=None, px_size:float=None, layer_size:float=None, center_xy:bool=True, center_z:bool=False, fn=0):
            """
            Initialize the cylinder shape.

            Input:
            - height (int): The height of the cylinder.
            - radius (float): The radius of the cylinder.
            - bottom_r (float): The radius of the bottom of the cylinder.
            - top_r (float): The radius of the top of the cylinder.
            - px_size (float): The size of the pixels.
            - layer_size (float): The size of the layers.
            - center_xy (bool): Whether to center the cylinder in xy.
            - center_z (bool): Whether to center the cylinder in z.
            - fn (int): The number of facets.
            """
            super().__init__(px_size, layer_size)

            # only allow radiuses to be multiples of 0.5
            if radius is not None:
                if not _is_integer(radius*2):
                    raise ValueError("Cylinder radius must be a multiple of 0.5")
            if bottom_r is not None:
                if not _is_integer(bottom_r*2):
                    raise ValueError("Cylinder radius (bottom) must be a multiple of 0.5")
            if top_r is not None:
                if not _is_integer(top_r*2):
                    raise ValueError("Cylinder radius (top) must be a multiple of 0.5")

            # validate shape is fully constrained
            bottom = bottom_r if bottom_r is not None else radius
            top = top_r if top_r is not None else radius
            if bottom is None or top is None:
                raise ValueError("Either radius or bottom_r and top_r must be provided.")

            if top % 2 != bottom % 2:
                raise ValueError("Cylinder top and bottom radius must both be either even or odd.")

    class Sphere(Shape, ABC):
        """
        Abstract base class for all sphere shapes.
        """
        @abstractmethod
        def __init__(self, size:tuple[int, int, int], px_size:float=None, layer_size:float=None, center:bool=True, fn=0):
            """
            Initialize the ellipsoid shape.

            Input:
            - size (int): The size of the ellipsoid.
            - px_size (float): The size of the pixels.
            - layer_size (float): The size of the layers.
            - fn (int): The number of facets.
            """
            super().__init__(px_size, layer_size)

    class RoundedCube(Shape, ABC):
        """
        Abstract base class for all rounded cube shapes.
        """
        def __init__(self, size:tuple[int, int, int], radius:tuple[float, float, float], px_size:float, layer_size:float, center:bool=False, fn:int=0):
            super().__init__(px_size, layer_size)

    class TextExtrusion(Shape, ABC):
        """
        Abstract base class for all text extrusion shapes.
        """
        def __init__(self, text:str, height:int, font:str="arial", font_size:int=10, px_size:float=None, layer_size:float=None):
            super().__init__(px_size, layer_size)

    class ImportModel(Shape, ABC):
        """
        Abstract base class for all ImportModel imports.
        """
        def __init__(self, filename:str, auto_repair:bool=True, px_size:float=None, layer_size:float=None):
            super().__init__(px_size, layer_size)

    class TPMS(Shape):
        @functools.cache
        def gyroid(x:float, y:float, z:float) -> bool:
            a = np.radians(360)
            return (
                np.cos(a * x) * np.sin(a * y) +
                np.cos(a * y) * np.sin(a * z) +
                np.cos(a * z) * np.sin(a * x)
            )

        @functools.cache
        def diamond(x:float, y:float, z:float) -> bool:
            a = np.radians(360)
            return (
                np.sin(a*(x)) * np.sin(a*(y)) * np.sin(a*(z)) + 
                np.sin(a*(x)) * np.cos(a*(y)) * np.cos(a*(z)) + 
                np.cos(a*(x)) * np.sin(a*(y)) * np.cos(a*(z)) + 
                np.cos(a*(x)) * np.cos(a*(y)) * np.sin(a*(z))
            )

        def __init__(self, size:tuple[int, int, int], func:Callable[[int, int, int], int]=diamond, px_size:float=None, layer_size:float=None):
            super().__init__(px_size, layer_size)

    def render(self, component:Component, render_bulk:bool=True, do_bulk_difference:bool=True, flatten_scene:bool=True, wireframe_bulk:bool=False, show_assists:bool=False):
        pass

    def slice_component(self, component:Component, render_bulk:bool=True, do_bulk_difference:bool=True):
        pass