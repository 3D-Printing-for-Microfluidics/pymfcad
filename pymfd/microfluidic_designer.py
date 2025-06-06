from __future__ import annotations

import inspect
from enum import Enum
from pathlib import Path

from pymfd.backend import Backend, Manifold3D, Color

_backend:Backend = None

def set_manifold3d_backend():
    global _backend
    _backend = Manifold3D()
    set_fn(20)

def get_backend() -> Backend:
    global _backend
    if _backend is None:
        raise ValueError("Backend not set. Please set the backend using set_backend().")
    return _backend

def set_fn(fn):
    global _backend
    _backend.set_fn(fn)


class InstantiationTrackerMixin:
    def __init__(self):
        # Get the first relevant frame outside of this class
        for frame_info in inspect.stack():
            filename = frame_info.filename
            if 'site-packages' in filename or filename == __file__:
                continue
            self._instantiation_path = Path(filename).resolve()
            break

    @property
    def instantiation_dir(self):
        """Return (directory, filename_stem) of the file that instantiated the component, if it's a Device or Component."""
        class_name = type(self).__name__

        if class_name in {'Device', 'Component'}:
            return self._instantiation_path.parent

        # Fallback: use where the class is defined
        module_name = self.__class__.__module__
        module = sys.modules.get(module_name) or importlib.import_module(module_name)
        path = Path(module.__file__).resolve()
        return path.parent

    @property
    def instantiating_file_stem(self):
        """Return (directory, filename_stem) of the file that instantiated the component, if it's a Device or Component."""
        class_name = type(self).__name__

        if class_name in {'Device', 'Component'}:
            return self._instantiation_path.stem

        # Fallback: use where the class is defined
        module_name = self.__class__.__module__
        module = sys.modules.get(module_name) or importlib.import_module(module_name)
        path = Path(module.__file__).resolve()
        return path.stem


class Port(InstantiationTrackerMixin):
    class PortType(Enum):
        IN = 1
        OUT = 2
        INOUT = 3

    class SurfaceNormal(Enum):
        POS_X = 1
        POS_Y = 2
        POS_Z = 3
        NEG_X = 4
        NEG_Y = 5
        NEG_Z = 6

    _vector_map = {
        SurfaceNormal.POS_X: (1, 0, 0),
        SurfaceNormal.POS_Y: (0, 1, 0),
        SurfaceNormal.POS_Z: (0, 0, 1),
        SurfaceNormal.NEG_X: (-1, 0, 0),
        SurfaceNormal.NEG_Y: (0, -1, 0),
        SurfaceNormal.NEG_Z: (0, 0, -1),
    }

    def __init__(self, _type: PortType, position: tuple[int, int, int],
                 size: tuple[int, int, int], surface_normal: SurfaceNormal):
        super().__init__()
        self.parent = None
        self.name = None
        self.type = _type
        self.position = position
        self.size = size
        self.surface_normal = surface_normal

    def get_name(self):
        if self.name is None:
            raise ValueError(f"Port has not been named")
        else:
            return f"{self.parent.name}_{self.name}"

    def get_fully_qualified_name(self):
        if self.name is None:
            raise ValueError(f"Port has not been named")
        name = self.name
        parent = self.parent
        while parent is not None:
            if parent.name is not None:
                name = f"{parent.name}.{name}"
                parent = parent.parent
            else:
                name = f"{parent.instantiating_file_stem}.{name}"
                return name
        return name

    def to_vector(self) -> tuple[int, int, int]:
        try:
            return self._vector_map[self.surface_normal]
        except KeyError:
            raise ValueError(f"Unsupported surface normal: {self.surface_normal}")

    def get_bounding_box(self) -> tuple[int, int, int, int, int, int]:
        dx, dy, dz = self._vector_map[self.surface_normal]
        pos = list(self.position)
        size = self.size

        # For negative directions, shift start back by size
        if dx < 0:
            pos[0] -= size[0]
        if dy < 0:
            pos[1] -= size[1]
        if dz < 0:
            pos[2] -= size[2]

        return (
            pos[0], pos[1], pos[2],
            pos[0] + size[0],
            pos[1] + size[1],
            pos[2] + size[2]
        )

    def get_origin(self): # get the -/-/- coordinate
        return self.get_bounding_box()[0:3]

    def get_color(self):
        if self.type == Port.PortType.IN:
            return Color.from_name("green", 255)  # Green
        elif self.type == Port.PortType.OUT:
            return Color.from_name("red", 255)  # Red
        elif self.type == Port.PortType.INOUT:
            return Color.from_name("blue", 255)  # Blue
        else:
            return Color.from_name("white", 255)  # White

class Component(InstantiationTrackerMixin):
    def __init__(self, size:tuple[int,int,int], position:tuple[int, int, int], px_size:float = 0.0076, layer_size:float = 0.01):
        super().__init__()
        self.parent = None
        self.name = None
        self.position = position
        self.size = size
        self.px_size = px_size
        self.layer_size = layer_size
        self.shapes = []
        self.ports = []
        self.subcomponents = []
        self.labels = {}

    # def __getattr__(self, name):
    #     # Only called if the normal attribute lookup fails
    #     for attr_dict in (self.shapes, self.ports, self.subcomponents):
    #         if name in attr_dict:
    #             return attr_dict[name]
    #     raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def get_fully_qualified_name(self):
        if self.name is None:
            raise ValueError(f"Component has not been named")
        name = self.name
        parent = self.parent
        while parent is not None:
            if parent.name is not None:
                name = f"{parent.name}.{name}"
                parent = parent.parent
            else:
                name = f"{parent.instantiating_file_stem}.{name}"
                return name
        return name

    def get_bounding_box(self):
        min_x = self.position[0]
        max_x = self.position[0] + self.size[0]
        min_y = self.position[1]
        max_y = self.position[1] + self.size[1]
        min_z = self.position[2]
        max_z = self.position[2] + self.size[2]
        return (min_x, min_y, min_z, max_x, max_y, max_z)

    def _validate_name(self, name):
        for l in self.labels:
            if l == name:
                raise ValueError(f"Label with name '{name}' already exists in component {self.name}")
        for p in self.ports:
            if p.name == name:
                raise ValueError(f"Port with name '{name}' already exists in component {self.name}")
        for s in self.shapes:
            if s.name == name:
                raise ValueError(f"Shape with name '{name}' already exists in component {self.name}")
        for c in self.subcomponents:
            if c.name == name:
                raise ValueError(f"Commponent with name '{name}' already exists in component {self.name}")
        if not name.isidentifier():
            raise ValueError(f"Name '{name}' is not a valid Python identifier (e.g. no spaces, starts with letter, etc.)")
        if hasattr(self, name):
            raise ValueError(f"Name '{name}' conflicts with existing attributes")

    def add_label(self, name:str, color:Color):
        self._validate_name(name)
        self.labels[name] = color
        setattr(self, name, color)

    def add_shape(self, name:str, shape:Backend.Shape, label:str):
        self._validate_name(name)
        shape.name = name
        shape.parent = self
        shape.color = self.labels[label]
        self.shapes.append(shape)
        setattr(self, name, shape)

    def add_port(self, name:str, port:Port):
        self._validate_name(name)
        port.name = name
        port.parent = self
        self.ports.append(port)
        setattr(self, name, port)

    def add_subcomponent(self, name:str, component:Component):
        self._validate_name(name)
        component.name = name
        component.parent = self
        self.subcomponents.append(component)
        setattr(self, name, component)

        for label, color in component.labels.items():
            self.labels[f"{name}.{label}"] = color

    def relabel_subcomponents(self, subcomponents:list[Component], label:str):
        for c in subcomponents:
            c.relabel_labels(c.labels.keys(), label, self.labels[label])

    def relabel_labels(self, labels:list[str], label:str, color:Color=None):
        if color is None:
            color = self.labels[label]
        for l, c in self.labels.items():
            if l in labels:
                c.change_to_color(color)
        for c in self.subcomponents:
            c.relabel_labels(labels, label, color)

    def relabel_shapes(self, shapes:list[Shape], label:str):
        for s in shapes:
            s.color = self.labels[label]

    def make_cube(self, size:tuple[int, int, int], center:bool=False) -> Backend.Cube:
        return get_backend().Cube(size, self.px_size, self.layer_size, center=center)

    def make_cylinder(self, h:int, r:float=None, r1:float=None, r2:float=None, center:bool=False, fn:int=0) -> Backend.Cylinder:
        return get_backend().Cylinder(h, r, r1, r2, self.px_size, self.layer_size, center=center, fn=fn)

    def make_sphere(self, r:float=None, center:bool=True, fn:int=0) -> Backend.Cylinder:
        return get_backend().Sphere(r, self.px_size, self.layer_size, fn=fn)

    def translate(self, translation:tuple[int, int, int], set_origin:bool=True) -> Component:
        for component in self.subcomponents:
            component.translate(translation)
        for shape in self.shapes:
            shape.translate(translation)
        for port in self.ports:
            port.position = (port.position[0] + translation[0], port.position[1] + translation[1], port.position[2] + translation[2])
        if set_origin:
            self.position = (self.position[0] + translation[0], self.position[1] + translation[1], self.position[2] + translation[2])
        return self

    def rotate(self, rotation:int, in_place:bool = False) -> Component:
        if rotation % 90 != 0:
            raise ValueError("Rotation must be a multiple of 90 degrees")

        if in_place:
            original_position = self.position
            # Translate the component to position for in-place rotation
            self.translate((-self.position[0], -self.position[1], -self.position[2]), set_origin=False)

        for component in self.subcomponents:
            component.rotate(rotation)

        for shape in self.shapes:
            shape.rotate((0,0,rotation))

        rot = rotation % 360

        # Mapping for 90-degree rotation steps around Z axis
        vector_rotation_map = {
            90: {
                Port.SurfaceNormal.POS_X: (Port.SurfaceNormal.POS_Y, (-1, 0)),
                Port.SurfaceNormal.POS_Y: (Port.SurfaceNormal.NEG_X, (0, 0)),
                Port.SurfaceNormal.NEG_X: (Port.SurfaceNormal.NEG_Y, (-1, 0)),
                Port.SurfaceNormal.NEG_Y: (Port.SurfaceNormal.POS_X, (0, 0)),
            },
            180: {
                Port.SurfaceNormal.POS_X: (Port.SurfaceNormal.NEG_X, (0, -1)),
                Port.SurfaceNormal.POS_Y: (Port.SurfaceNormal.NEG_Y, (-1, 0)),
                Port.SurfaceNormal.NEG_X: (Port.SurfaceNormal.POS_X, (0, -1)),
                Port.SurfaceNormal.NEG_Y: (Port.SurfaceNormal.POS_Y, (-1, 0)),
            },
            270: {
                Port.SurfaceNormal.POS_X: (Port.SurfaceNormal.NEG_Y, (0, 0)),
                Port.SurfaceNormal.POS_Y: (Port.SurfaceNormal.POS_X, (0, -1)),
                Port.SurfaceNormal.NEG_X: (Port.SurfaceNormal.POS_Y, (0, 0)),
                Port.SurfaceNormal.NEG_Y: (Port.SurfaceNormal.NEG_X, (0, -1)),
            }
        }

        for port in self.ports:
            x, y, z = port.position
            size_x, size_y = port.size[0], port.size[1]

            if rot == 90:
                port.position = (-y, x, z)
            elif rot == 180:
                port.position = (-x, -y, z)
            elif rot == 270:
                port.position = (y, -x, z)

            if port.surface_normal in vector_rotation_map.get(rot, {}):
                new_vector, (dx, dy) = vector_rotation_map[rot][port.surface_normal]
                port.position = (
                    port.position[0] + dx * port.size[0],
                    port.position[1] + dy * port.size[1],
                    port.position[2]
                )
                port.surface_normal = new_vector

            # Adjust Z ports if needed
            if port.surface_normal in (Port.SurfaceNormal.POS_Z, Port.SurfaceNormal.NEG_Z):
                if rot == 90:
                    port.position = (port.position[0] - port.size[0], port.position[1], port.position[2])
                elif rot == 180:
                    port.position = (port.position[0] - port.size[0], port.position[1] - port.size[1], port.position[2])
                elif rot == 270:
                    port.position = (port.position[0], port.position[1] - port.size[1], port.position[2])

        if in_place:
            # Translate the component so new negative-negative corner is at original position
            if rot == 90:
                self.translate((original_position[0]+self.size[1], original_position[1], original_position[2]), set_origin=False)
            elif rot == 180:
                self.translate((original_position[0]+self.size[0], original_position[1]+self.size[1], original_position[2]), set_origin=False)
            elif rot == 270:
                self.translate((original_position[0], original_position[1]+self.size[0], original_position[2]), set_origin=False)

        return self

    def mirror(self, mirror_x:bool = False, mirror_y:bool = False, in_place:bool = False) -> Component:
        if not mirror_x and not mirror_y:
            return self  # No mirroring requested

        if mirror_x and mirror_y:
            return self.rotate(180, in_place=in_place)

        if in_place:
            original_position = self.position
            # Translate the component to position for in-place mirroring
            self.translate((-self.position[0], -self.position[1], -self.position[2]), set_origin=False)

        for component in self.subcomponents:
            component.mirror(mirror_x, mirror_y)

        for shape in self.shapes:
            shape.mirror((mirror_x, mirror_y, False))

        # Surface normal flips
        mirror_vector_map = {
            'x': {
                Port.SurfaceNormal.POS_X: Port.SurfaceNormal.NEG_X,
                Port.SurfaceNormal.NEG_X: Port.SurfaceNormal.POS_X,
            },
            'y': {
                Port.SurfaceNormal.POS_Y: Port.SurfaceNormal.NEG_Y,
                Port.SurfaceNormal.NEG_Y: Port.SurfaceNormal.POS_Y,
            },
        }

        for port in self.ports:
            x, y, z = port.position
            sx, sy = port.size[0], port.size[1]

            if mirror_x:
                x = -x - sx
                # If pointing in +X or -X, correct for sticking out
                if port.surface_normal == Port.SurfaceNormal.POS_X:
                    x += sx
                elif port.surface_normal == Port.SurfaceNormal.NEG_X:
                    x += sx
                port.surface_normal = mirror_vector_map['x'].get(port.surface_normal, port.surface_normal)

            if mirror_y:
                y = -y - sy
                # If pointing in +Y or -Y, correct for sticking out
                if port.surface_normal == Port.SurfaceNormal.POS_Y:
                    y += sy
                elif port.surface_normal == Port.SurfaceNormal.NEG_Y:
                    y += sy
                port.surface_normal = mirror_vector_map['y'].get(port.surface_normal, port.surface_normal)

            port.position = (x, y, z)

        if in_place:
            # Translate the component so new negative-negative corner is at original position
            if mirror_x and not mirror_y:
                self.translate((original_position[0] + self.size[0], original_position[1], original_position[2]), set_origin=False)
            elif not mirror_x and mirror_y:
                self.translate((original_position[0], original_position[1] + self.size[1], original_position[2]), set_origin=False)

        return self


class Device(Component):
    def __init__(self, name:str, size:tuple[int,int,int], position:tuple[int, int, int], px_size:float = 0.0076, layer_size:float = 0.01):
        super().__init__(size, position, px_size, layer_size)
        self.name = name
        self.inverted = False
        self.bulk_shape = []

    def add_bulk_shape(self, name:str, shape:Backend.Shape, label:str):
        self._validate_name(name)
        shape.name = name
        shape.parent = self
        shape.color = self.labels[label]
        self.bulk_shape.append(shape)
        setattr(self, name, shape)

    def invert_device(self):
        if self.inverted:
            raise ValueError("Device already inverted")

        self.inverted = True
        
        # make device from bulk shape
        device = None
        for s in self.bulk_shape:
            if device is None:
                device = s
            else:
                device += s
            print(f"Adding bulk shape {s} to device {self.name}")

        if device is None:
            raise ValueError("No bulk shape found in device")

        def invert_helper(component:Component):
            nonlocal device
            for c in component.subcomponents:
                invert_helper(c)
            for s in component.shapes:
                device -= s

        invert_helper(self)
        self.shapes = [device]