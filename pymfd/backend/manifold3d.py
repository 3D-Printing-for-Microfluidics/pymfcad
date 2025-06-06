from manifold3d import set_circular_segments, Manifold
from .generic_backend import Backend

class Manifold3D(Backend):
    """
    Manifold3D backend.
    """
    def set_fn(self, fn):
        """
        Set the number of facets for the shapes.
        """
        set_circular_segments(fn)

    class Shape(Backend.Shape):
        """
        Manifold3D shape.
        """
        def __init__(self, px_size:float, layer_size:float, allow_half_integer_translations:bool = False):
            super().__init__(px_size, layer_size, allow_half_integer_translations)
        
        def translate(self, translation:tuple[float, float, float]) -> 'Shape':
            super().translate(translation)
            self.object = self.object.translate((translation[0] * self.px_size, translation[1] * self.px_size, translation[2] * self.layer_size))
            return self

        def rotate(self, rotation:tuple[float, float, float]) -> 'Shape':
            super().rotate(rotation)
            self.object = self.object.rotate(rotation)
            return self

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

        def hull(self, other: 'Shape') -> 'Shape':
            super().hull(other)
            self.object = Manifold.batch_hull([self.object, other.object])
            return self

    class Cube(Backend.Cube, Shape):
        """
        Manifold3D cube.
        """
        def __init__(self, size:tuple[int, int, int], px_size:float, layer_size:float, center:bool=False):
            super().__init__(size, px_size, layer_size, center)
            self.object = Manifold.cube((size[0]*px_size, size[1]*px_size, size[2]*layer_size), center=center)

    class Cylinder(Backend.Cylinder, Shape):
        """
        Manifold3D cylinder.
        """
        def __init__(self, height:int, radius:float=None, bottom_r:float=None, top_r:float=None, px_size:float=None, layer_size:float=None, center:bool=False, fn=0):
            super().__init__(height, radius, bottom_r, top_r, px_size, layer_size, center, fn)

            bottom = bottom_r if bottom_r is not None else radius
            top = top_r if top_r is not None else radius
            self.object = Manifold.cylinder(height=height*layer_size, radius_low=bottom*px_size, radius_high=top*px_size, circular_segments=fn, center=center)

    class Sphere(Backend.Sphere, Shape):
        """
        Manifold3D sphere.
        """
        def __init__(self, radius:float, px_size:float=None, layer_size:float=None, fn=0):
            super().__init__(radius, px_size, layer_size, fn)
            self.object = Manifold.sphere(radius=radius*px_size, circular_segments=fn)