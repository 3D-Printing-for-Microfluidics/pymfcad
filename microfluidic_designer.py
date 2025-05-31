from __future__ import annotations
from enum import Enum

# from router import autoroute_channel
from backends import NetType, Backend, Manifold3D

_backend:Backend = None

def set_manifold3d_backend():
    global _backend
    _backend = Manifold3D()

def get_backend() -> Backend:
    global _backend
    if _backend is None:
        raise ValueError("Backend not set. Please set the backend using set_backend().")
    return _backend
        
# class Router:
#     def __init__(self):

class Port:
    class PortType(Enum):
        IN = 1
        OUT = 2
        INOUT = 3

    class Pointing_Vector(Enum):
        POS_X = 1
        POS_Y = 2
        POS_Z = 3
        NEG_X = 4
        NEG_Y = 5
        NEG_Z = 6

    _vector_map = {
        Pointing_Vector.POS_X: (1, 0, 0),
        Pointing_Vector.POS_Y: (0, 1, 0),
        Pointing_Vector.POS_Z: (0, 0, 1),
        Pointing_Vector.NEG_X: (-1, 0, 0),
        Pointing_Vector.NEG_Y: (0, -1, 0),
        Pointing_Vector.NEG_Z: (0, 0, -1),
    }

    def __init__(self, parent:Component, name: str, _type: PortType, position: tuple[int, int, int],
                 size: tuple[int, int, int], pointing_vector: Pointing_Vector):
        self.parent = parent
        self.name = name
        self.type = _type
        self.position = position
        self.size = size
        self.pointing_vector = pointing_vector

    def pointing_vector_to_vector(self) -> tuple[int, int, int]:
        try:
            return self._vector_map[self.pointing_vector]
        except KeyError:
            raise ValueError(f"Unsupported pointing vector: {self.pointing_vector}")

    def get_bounding_box(self) -> tuple[int, int, int, int, int, int]:
        dx, dy, dz = self._vector_map[self.pointing_vector]
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

    def get_adjusted_position(self):
        return self.get_bounding_box()[0:3]

class Component:
    def __init__(self, name:str, position:tuple[int, int, int], size:tuple[int,int,int], px_size:float = 0.0076, layer_size:float = 0.01):
        self.name = name
        self.position = position
        self.size = size
        self.px_size = px_size
        self.layer_size = layer_size
        self.model = []
        self.ports = []
        self.subcomponents = []
        self.netlist = {
            "default": NetType(name="default", color=(0, 255, 255, 127))
        }

    def get_bounding_box(self):
        min_x = self.position[0]
        max_x = self.position[0] + self.size[0]
        min_y = self.position[1]
        max_y = self.position[1] + self.size[1]
        min_z = self.position[2]
        max_z = self.position[2] + self.size[2]
        return (min_x, min_y, min_z, max_x, max_y, max_z)

    def get_nettype_list(self) -> dict[str, NetType]:
        return self.netlist

    def add_nettype(self, nettype:NetType):
        self.netlist[nettype.name] = nettype

    def add_shape(self, shape:Backend.Shape):
        self.model.append(shape)

    def add_port(self, port:Port):
        self.ports.append(port)

    def get_port(self, name:str) -> Port:
        for port in self.ports:
            if port.name == name:
                return port
        raise ValueError(f"Port with name {name} not found in component {self.name}")

    def add_subcomponent(self, component:Component):
        self.subcomponents.append(component)

    def make_cube(self, size:tuple[int, int, int], center:bool=False, nettype:str = "default") -> Backend.Cube:
        nettype = self.netlist[nettype]
        return get_backend().Cube(size, self.px_size, self.layer_size, center=center, nettype=nettype)

    def make_cylinder(self, h:int, r:float=None, r1:float=None, r2:float=None, center:bool=False, nettype:str="default", fn:int=20) -> Backend.Cylinder:
        nettype = self.netlist[nettype]
        return get_backend().Cylinder(h, r, self.px_size, self.layer_size, r1, r2, center=center, nettype=nettype, fn=fn)

    def make_sphere(self, r:float=None, nettype:str = "default", fn:int=20) -> Backend.Cylinder:
        nettype = self.netlist[nettype]
        return get_backend().Sphere(r, self.px_size, self.layer_size, nettype=nettype, fn=fn)

    # def route(self, input_port:Port, output_port:Port, channel_size:tuple[int, int, int], channel_margin:tuple[int, int, int], nettype:str="default"):
    #     self.add_shape(autoroute_channel(self, input_port, output_port, channel_size=channel_size, channel_margin=channel_margin, nettype=nettype))

    def translate(self, translation:tuple[int, int, int], set_origin:bool=True) -> Component:
        for component in self.subcomponents:
            component.translate(translation)
        for shape in self.model:
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

        for shape in self.model:
            shape.rotate((0,0,rotation))

        rot = rotation % 360

        # Mapping for 90-degree rotation steps around Z axis
        vector_rotation_map = {
            90: {
                Port.Pointing_Vector.POS_X: (Port.Pointing_Vector.POS_Y, (-1, 0)),
                Port.Pointing_Vector.POS_Y: (Port.Pointing_Vector.NEG_X, (0, 0)),
                Port.Pointing_Vector.NEG_X: (Port.Pointing_Vector.NEG_Y, (-1, 0)),
                Port.Pointing_Vector.NEG_Y: (Port.Pointing_Vector.POS_X, (0, 0)),
            },
            180: {
                Port.Pointing_Vector.POS_X: (Port.Pointing_Vector.NEG_X, (0, -1)),
                Port.Pointing_Vector.POS_Y: (Port.Pointing_Vector.NEG_Y, (-1, 0)),
                Port.Pointing_Vector.NEG_X: (Port.Pointing_Vector.POS_X, (0, -1)),
                Port.Pointing_Vector.NEG_Y: (Port.Pointing_Vector.POS_Y, (-1, 0)),
            },
            270: {
                Port.Pointing_Vector.POS_X: (Port.Pointing_Vector.NEG_Y, (0, 0)),
                Port.Pointing_Vector.POS_Y: (Port.Pointing_Vector.POS_X, (0, -1)),
                Port.Pointing_Vector.NEG_X: (Port.Pointing_Vector.POS_Y, (0, 0)),
                Port.Pointing_Vector.NEG_Y: (Port.Pointing_Vector.NEG_X, (0, -1)),
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

            if port.pointing_vector in vector_rotation_map.get(rot, {}):
                new_vector, (dx, dy) = vector_rotation_map[rot][port.pointing_vector]
                port.position = (
                    port.position[0] + dx * port.size[0],
                    port.position[1] + dy * port.size[1],
                    port.position[2]
                )
                port.pointing_vector = new_vector

            # Adjust Z ports if needed
            if port.pointing_vector in (Port.Pointing_Vector.POS_Z, Port.Pointing_Vector.NEG_Z):
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

        for shape in self.model:
            shape.mirror((mirror_x, mirror_y, False))

        # Pointing vector flips
        mirror_vector_map = {
            'x': {
                Port.Pointing_Vector.POS_X: Port.Pointing_Vector.NEG_X,
                Port.Pointing_Vector.NEG_X: Port.Pointing_Vector.POS_X,
            },
            'y': {
                Port.Pointing_Vector.POS_Y: Port.Pointing_Vector.NEG_Y,
                Port.Pointing_Vector.NEG_Y: Port.Pointing_Vector.POS_Y,
            },
        }

        for port in self.ports:
            x, y, z = port.position
            sx, sy = port.size[0], port.size[1]

            if mirror_x:
                x = -x - sx
                # If pointing in +X or -X, correct for sticking out
                if port.pointing_vector == Port.Pointing_Vector.POS_X:
                    x += sx
                elif port.pointing_vector == Port.Pointing_Vector.NEG_X:
                    x += sx
                port.pointing_vector = mirror_vector_map['x'].get(port.pointing_vector, port.pointing_vector)

            if mirror_y:
                y = -y - sy
                # If pointing in +Y or -Y, correct for sticking out
                if port.pointing_vector == Port.Pointing_Vector.POS_Y:
                    y += sy
                elif port.pointing_vector == Port.Pointing_Vector.NEG_Y:
                    y += sy
                port.pointing_vector = mirror_vector_map['y'].get(port.pointing_vector, port.pointing_vector)

            port.position = (x, y, z)

        if in_place:
            # Translate the component so new negative-negative corner is at original position
            if mirror_x and not mirror_y:
                self.translate((original_position[0] + self.size[0], original_position[1], original_position[2]), set_origin=False)
            elif not mirror_x and mirror_y:
                self.translate((original_position[0], original_position[1] + self.size[1], original_position[2]), set_origin=False)

        return self


class Device(Component):
    def __init__(self, name:str, position:tuple[int, int, int], size:tuple[int,int,int], px_size:float = 0.0076, layer_size:float = 0.01):
        super().__init__(name, position, size, px_size, layer_size)
        self.inverted = False
        self.bulk_shape = []
        self.add_nettype(NetType(name="device", color=(0, 255, 255, 127)))

    def add_bulk_shape(self, shape:Backend.Shape):
        self.bulk_shape.append(shape)

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
            for s in component.model:
                device -= s

        invert_helper(self)
        self.model = [device]