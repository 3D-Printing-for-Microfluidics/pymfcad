from __future__ import annotations

import numpy as np
from enum import Enum
from abc import ABC, abstractmethod
from manifold3d import Manifold

def _is_integer(val: float) -> bool:
    return abs(val - round(val)) < 1e-6

class NetType:
    def __init__(self, name:str = "Default", color:tuple[int, int, int, int] = (0, 255, 255, 255)):
        self.name = name
        self.color = color

class Backend:
    class Shape(ABC):
        @abstractmethod
        def __init__(self, px_size:float, layer_size:float, nettype:NetType = NetType(), allow_half_integer_translations:bool = False):
            self.px_size = px_size
            self.layer_size = layer_size
            self.nettype = nettype
            self.allow_half_integer_translations = allow_half_integer_translations
            self.object = None
            self.keepouts = []

        def _translate_keepouts(self, translation: tuple[float, float, float]):
            dx, dy, dz = translation
            self.keepouts = [
                [x0 + dx, y0 + dy, z0 + dz, x1 + dx, y1 + dy, z1 + dz]
                for x0, y0, z0, x1, y1, z1 in self.keepouts
            ]

        def _rotate_point(self, point:tuple[float, float, float], rotation:tuple[float, float, float]):
            """Rotate a point around origin (0,0,0) with Euler angles (in degrees) in XYZ order."""
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
            flip_x, flip_y, flip_z = axis
            new_keepouts = []
            for x0, y0, z0, x1, y1, z1 in self.keepouts:
                nx0, nx1 = (-x1, -x0) if flip_x else (x0, x1)
                ny0, ny1 = (-y1, -y0) if flip_y else (y0, y1)
                nz0, nz1 = (-z1, -z0) if flip_z else (z0, z1)
                new_keepouts.append([nx0, ny0, nz0, nx1, ny1, nz1])
            self.keepouts = new_keepouts

        @abstractmethod
        def translate(self, translation:tuple[float, float, float]) -> 'Shape':
            if not self.allow_half_integer_translations and (not _is_integer(translation[0]) or 
                                   not _is_integer(translation[1]) or 
                                   not _is_integer(translation[2])):
                raise ValueError("Translation must be an integer for this shape.")
            self._translate_keepouts(translation)

        @abstractmethod
        def rotate(self, rotation:tuple[float, float, float]) -> 'Shape':
            self._rotate_keepouts(rotation)

        # @abstractmethod
        # def scale(self, scale:tuple[float, float, float]) -> 'Shape': # would need to snap to grid
        #     pass

        @abstractmethod
        def resize(self, size:tuple[int, int, int]) -> 'Shape':
            bounds = self.object.bounding_box()
            sx = size[0] / (bounds[3] - bounds[0])/self.px_size
            sy = size[1] / (bounds[4] - bounds[1])/self.px_size
            sz = size[2] / (bounds[5] - bounds[2])/self.layer_size

            self._scale_keepouts((sx, sy, sz))

        @abstractmethod
        def mirror(self, axis:tuple[bool, bool, bool]) -> 'Shape':
            self._mirror_keepouts(axis)

        @abstractmethod
        def __add__(self, other:'Shape') -> 'Shape': # union
            self.keepouts.extend(other.keepouts)

        @abstractmethod
        def __sub__(self, other:'Shape') -> 'Shape': # difference
            pass

        # @abstractmethod
        # def __mul__(self, other:'Shape') -> 'Shape': # intersection
        #     pass

        @abstractmethod
        def hull(self, other:'Shape') -> 'Shape':
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

    class Cube(Shape, ABC):
        @abstractmethod
        def __init__(self, size:tuple[int, int, int], px_size:float, layer_size:float, center:bool=False, nettype:NetType = NetType()):
            super().__init__(px_size, layer_size, nettype)

            # allow half translations if using center and at least one dimention is odd
            if center and (size[0] % 2 != 0 or 
                           size[1] % 2 != 0 or 
                           size[2] % 2 != 0):
                self.allow_half_integer_translations = True
            else:
                self.allow_half_integer_translations = False

            # add keepout
            if center:
                self.keepouts.append((-size[0]/2, -size[1]/2, -size[2]/2,size[0]/2, size[1]/2, size[2]/2))
            else:
                self.keepouts.append((0,0,0,size[0], size[1], size[2]))

    class Cylinder(Shape, ABC):
        @abstractmethod
        def __init__(self, height:int, radius:float=None, px_size:float=None, layer_size:float=None, bottom_r:float=None, top_r:float=None, center:bool=False, nettype:NetType = NetType(), fn=20):
            super().__init__(px_size, layer_size, nettype)

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
                
            # allow half translations if using center and height is odd or at least one diameter is odd
            if (center and height % 2 != 0) or (not _is_integer(bottom) or not _is_integer(top)):
                self.allow_half_integer_translations = True
            else:
                self.allow_half_integer_translations = False

            # add keepout
            radius = max(bottom, top)
            if center:
                self.keepouts.append((-radius,-radius,-height/2,radius,radius,height/2))
            else:
                self.keepouts.append((-radius,-radius,0,radius,radius,height))

    class Sphere(Shape, ABC):
        @abstractmethod
        def __init__(px_size, layer_size, nettype):
            super().__init__(px_size, layer_size, nettype)

            # only allow radius to be multiples of 0.5
            if radius is not None:
                if not _is_integer(radius*2):
                    raise ValueError("Sphere radius must be a multiple of 0.5")

            # allow half translations if diameter is odd
            if not _is_integer(radius):
                self.allow_half_integer_translations = True
            else:
                self.allow_half_integer_translations = False

            # add keepout
            self.keepouts.append((-radius,-radius,-radius,radius,radius,radius))

class Manifold3D(Backend):
    class Shape(Backend.Shape):
        def __init__(self, px_size:float, layer_size:float, nettype:NetType = NetType(), allow_half_integer_translations:bool = False):
            super().__init__(px_size, layer_size, nettype, allow_half_integer_translations)
        
        def translate(self, translation:tuple[float, float, float]) -> 'Shape':
            super().translate(translation)
            self.object = self.object.translate((translation[0] * self.px_size, translation[1] * self.px_size, translation[2] * self.layer_size))
            return self

        def rotate(self, rotation:tuple[float, float, float]) -> 'Shape':
            super().rotate(rotation)
            self.object = self.object.rotate(rotation)
            return self

        # def scale(self, scale:tuple[float, float, float]) -> 'Shape':
        #     self.object = self.object.scale(scale)
        #     return self

        def resize(self, size: tuple[int, int, int]) -> 'Shape':
            super().resize(size)
            bounds = self.object.bounding_box()
            sx = size[0]*self.px_size / (bounds[3] - bounds[0])
            sy = size[1]*self.px_size / (bounds[4] - bounds[1])
            sz = size[2]*self.layer_size / (bounds[5] - bounds[2])

            self.object = self.object.scale((sx, sy, sz))
            return self

        def mirror(self, axis:tuple[bool, bool, bool]) -> 'Shape':
            super().mirror(axis)
            self.object = self.object.mirror(axis)
            return self

        def __add__(self, other:'Shape') -> 'Shape': # union
            super().__add__(other)
            self.object = self.object + other.object
            return self

        def __sub__(self, other:'Shape') -> 'Shape': # difference
            super().__sub__(other)
            self.object = self.object - other.object
            return self

        # def __mul__(self, other:'Shape') -> 'Shape': # intersection
        #     return self.object * other.object

        def hull(self, other: 'Shape') -> 'Shape':
            super().hull(other)
            self.object = Manifold.batch_hull([self.object, other.object])
            return self

    class Cube(Backend.Cube, Shape):
        def __init__(self, size:tuple[int, int, int], px_size:float, layer_size:float, center:bool=False, nettype:NetType = NetType()):
            super().__init__(size, px_size, layer_size, center, nettype)
            self.object = Manifold.cube((size[0]*px_size, size[1]*px_size, size[2]*layer_size), center=center)

    class Cylinder(Backend.Cylinder, Shape):
        def __init__(self, height:int, radius:float=None, px_size:float=None, layer_size:float=None, bottom_r:float=None, top_r:float=None, center:bool=False, nettype:NetType = NetType(), fn:int=20):
            super().__init__(height, radius, px_size, layer_size, bottom_r, top_r, center, nettype, fn)

            bottom = bottom_r if bottom_r is not None else radius
            top = top_r if top_r is not None else radius
            self.object = Manifold.cylinder(height=height*layer_size, radius_low=bottom*px_size, radius_high=top*px_size, circular_segments=fn, center=center)

    class Sphere(Backend.Sphere, Shape):
        def __init__(self, radius:float, px_size:float, layer_size:float, nettype:NetType = NetType(), fn:int=20):
            super().__init__(radius, px_size, layer_size, nettype, fn)
            self.object = Manifold.sphere(radius=radius*px_size, circular_segments=fn)