from __future__ import annotations

import sys
import inspect
import importlib
from enum import Enum
from pathlib import Path
from typing import Union
from scipy.special import comb
from typing import TYPE_CHECKING

from .backend import (
    Shape,
    Cube,
    Cylinder,
    Sphere,
    RoundedCube,
    TextExtrusion,
    ImportModel,
    TPMS,
    _render,
    _slice_component,
    Color,
    PolychannelShape,
    BezierCurveShape,
    _preprocess_polychannel_shapes,
)

if TYPE_CHECKING:
    from collections.abs import Callable


class _InstantiationTrackerMixin:
    """Mixin class to track where a component was instantiated."""

    def __init__(self):
        # Get the first relevant frame outside of this class
        for frame_info in inspect.stack():
            filename = frame_info.filename
            if "site-packages" in filename or filename == __file__:
                continue
            self._instantiation_path = Path(filename).resolve()
            break

    @property
    def instantiation_dir(self) -> Path:
        """Return (directory, filename_stem) of the file that instantiated the component, if it's a Device or Component."""
        class_name = type(self).__name__

        if class_name in {"Device", "Component"}:
            return self._instantiation_path.parent

        # Fallback: use where the class is defined
        module_name = self.__class__.__module__
        module = sys.modules.get(module_name) or importlib.import_module(module_name)
        path = Path(module.__file__).resolve()
        return path.parent

    @property
    def instantiating_file_stem(self) -> str:
        """Return (directory, filename_stem) of the file that instantiated the component, if it's a Device or Component."""
        class_name = type(self).__name__

        if class_name in {"Device", "Component"}:
            return self._instantiation_path.stem

        # Fallback: use where the class is defined
        module_name = self.__class__.__module__
        module = sys.modules.get(module_name) or importlib.import_module(module_name)
        path = Path(module.__file__).resolve()
        return path.stem


class Port(_InstantiationTrackerMixin):
    """
    Class representing a port in a microfluidic device.
    Ports are used to connect components and define their interaction with the environment.
    Each port has a type (IN, OUT, INOUT), a position in 3D space, a size, and a surface normal.
    The surface normal defines the direction in which the port is oriented.
    """

    class PortType(Enum):
        """Enumeration for port types."""

        IN = 1
        OUT = 2
        INOUT = 3

    class SurfaceNormal(Enum):
        """Enumeration for surface normals."""

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

    def __init__(
        self,
        _type: PortType,
        position: tuple[int, int, int],
        size: tuple[int, int, int],
        surface_normal: SurfaceNormal,
    ):
        """
        Initialize a port.

        Parameters:
        - _type (PortType): The type of the port (IN, OUT, INOUT).
        - position (tuple[int, int, int]): The position of the port in 3D space.
        - size (tuple[int, int, int]): The size of the port.
        - surface_normal (SurfaceNormal): The surface normal of the port, defining its orientation.
        """
        super().__init__()
        self._parent = None
        self._name = None
        self._type = _type
        self._position = position
        self._size = size
        self._surface_normal = surface_normal

    def get_name(self) -> str:
        """Get the name of the port."""
        if self._name is None:
            raise ValueError(f"Port has not been named")
        else:
            return f"{self._parent._name}_{self._name}"

    def get_fully_qualified_name(self) -> str:
        """Get the fully qualified name of the port, including parent component names."""
        if self._name is None:
            raise ValueError(f"Port has not been named")
        name = self._name
        parent = self._parent
        while parent is not None:
            if parent._name is not None:
                name = f"{parent._name}.{name}"
                parent = parent._parent
            else:
                name = f"{parent.instantiating_file_stem}.{name}"
                return name
        return name

    def to_vector(self) -> tuple[int, int, int]:
        """Convert the surface normal to a vector."""
        try:
            return self._vector_map[self._surface_normal]
        except KeyError:
            raise ValueError(f"Unsupported surface normal: {self._surface_normal}")

    def get_bounding_box(self) -> tuple[int, int, int, int, int, int]:
        """
        Get the bounding box of the port.
        The bounding box is defined by the position and size of the port,
        adjusted based on the surface normal direction.

        Returns:
        - A tuple of six integers representing the bounding box coordinates:
        (min_x, min_y, min_z, max_x, max_y, max_z)
        """
        dx, dy, dz = self._vector_map[self._surface_normal]
        pos = list(self._position)
        size = self._size

        # For negative directions, shift start back by size
        if dx < 0:
            pos[0] -= size[0]
        if dy < 0:
            pos[1] -= size[1]
        if dz < 0:
            pos[2] -= size[2]

        return (
            pos[0],
            pos[1],
            pos[2],
            pos[0] + size[0],
            pos[1] + size[1],
            pos[2] + size[2],
        )

    def get_origin(self):
        """Get the origin of the port, which is the minimum corner of its bounding box."""
        return self.get_bounding_box()[0:3]

    def get_color(self):
        """
        Get the color of the port based on its type.

        The color is determined as follows:
        - IN ports are green
        - OUT ports are red
        - INOUT ports are blue
        - If the type is not recognized, it defaults to white.

        Returns:
        - Color: The color of the port.
        """
        if self._type == Port.PortType.IN:
            return Color.from_name("green", 255)  # Green
        elif self._type == Port.PortType.OUT:
            return Color.from_name("red", 255)  # Red
        elif self._type == Port.PortType.INOUT:
            return Color.from_name("blue", 255)  # Blue
        else:
            return Color.from_name("white", 255)  # White


class Component(_InstantiationTrackerMixin):
    def __init__(
        self,
        size: tuple[int, int, int],
        position: tuple[int, int, int],
        px_size: float = 0.0076,
        layer_size: float = 0.01,
    ):
        super().__init__()
        self._parent = None
        self._name = None
        self._position = position
        self._size = size
        self._px_size = px_size
        self._layer_size = layer_size
        self.shapes = []
        self.bulk_shape = []
        self.ports = []
        self.subcomponents = []
        self.labels = {}

    def __getattr__(self, name):
        # Only called if the normal attribute lookup fails
        for attr_dict in (self.shapes, self.ports, self.subcomponents):
            if name in attr_dict:
                return attr_dict[name]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def get_fully_qualified_name(self):
        if self._name is None:
            raise ValueError(f"Component has not been named")
        name = self._name
        parent = self._parent
        while parent is not None:
            if parent._name is not None:
                name = f"{parent._name}.{name}"
                parent = parent._parent
            else:
                name = f"{parent.instantiating_file_stem}.{name}"
                return name
        return name

    def get_bounding_box(self):
        min_x = self._position[0]
        max_x = self._position[0] + self._size[0]
        min_y = self._position[1]
        max_y = self._position[1] + self._size[1]
        min_z = self._position[2]
        max_z = self._position[2] + self._size[2]
        return (min_x, min_y, min_z, max_x, max_y, max_z)

    def _validate_name(self, name):
        for l in self.labels:
            if l == name:
                raise ValueError(
                    f"Label with name '{name}' already exists in component {self._name}"
                )
        for p in self.ports:
            if p._name == name:
                raise ValueError(
                    f"Port with name '{name}' already exists in component {self._name}"
                )
        for s in self.shapes:
            if s._name == name:
                raise ValueError(
                    f"Shape with name '{name}' already exists in component {self._name}"
                )
        for c in self.subcomponents:
            if c._name == name:
                raise ValueError(
                    f"Commponent with name '{name}' already exists in component {self._name}"
                )
        if not name.isidentifier():
            raise ValueError(
                f"Name '{name}' is not a valid Python identifier (e.g. no spaces, starts with letter, etc.)"
            )
        if hasattr(self, name):
            raise ValueError(f"Name '{name}' conflicts with existing attributes")

    def add_label(self, name: str, color: Color):
        self._validate_name(name)
        self.labels[name] = color
        setattr(self, name, color)

    def add_shape(self, name: str, shape: Shape, label: str):
        self._validate_name(name)
        shape._name = name
        shape._parent = self
        shape._color = self.labels[label]
        self.shapes.append(shape)
        setattr(self, name, shape)

    def add_bulk_shape(self, name: str, shape: Shape, label: str):
        self._validate_name(name)
        shape._name = name
        shape._parent = self
        shape._color = self.labels[label]
        self.bulk_shape.append(shape)
        setattr(self, name, shape)

    def add_port(self, name: str, port: Port):
        self._validate_name(name)
        port._name = name
        port._parent = self
        self.ports.append(port)
        setattr(self, name, port)

    def add_subcomponent(self, name: str, component: Component):
        self._validate_name(name)
        component._name = name
        component._parent = self
        self.subcomponents.append(component)
        setattr(self, name, component)

        for label, color in component.labels.items():
            self.labels[f"{name}.{label}"] = color

    def relabel_subcomponents(self, subcomponents: list[Component], label: str):
        for c in subcomponents:
            c.relabel_labels(c.labels.keys(), label, self.labels[label])

    def relabel_labels(self, labels: list[str], label: str, color: Color = None):
        if color is None:
            color = self.labels[label]
        for l, c in self.labels.items():
            if l in labels:
                c._change_to_color(color)
        for c in self.subcomponents:
            c.relabel_labels(labels, label, color)

    def relabel_shapes(self, shapes: list[Shape], label: str):
        for s in shapes:
            s._color = self.labels[label]

    def make_cube(
        self, size: tuple[int, int, int], center: bool = False, _no_validation=True
    ) -> Cube:
        return Cube(
            size,
            self._px_size,
            self._layer_size,
            center=center,
            _no_validation=_no_validation,
        )

    def make_cylinder(
        self,
        h: int,
        r: float = None,
        r1: float = None,
        r2: float = None,
        center_xy: bool = True,
        center_z: bool = False,
        fn: int = 0,
    ) -> Cylinder:
        return Cylinder(
            h,
            r,
            r1,
            r2,
            self._px_size,
            self._layer_size,
            center_xy=center_xy,
            center_z=center_z,
            fn=fn,
        )

    def make_sphere(
        self,
        size: tuple[int, int, int],
        center: bool = True,
        fn: int = 0,
        _no_validation=True,
    ) -> Sphere:
        return Sphere(
            size,
            self._px_size,
            self._layer_size,
            center=center,
            fn=fn,
            _no_validation=_no_validation,
        )

    def make_rounded_cube(
        self,
        size: tuple[int, int, int],
        radius: tuple[int, int, int],
        center: bool = False,
        fn: int = 0,
        _no_validation=True,
    ) -> RoundedCube:
        return RoundedCube(
            size,
            radius,
            self._px_size,
            self._layer_size,
            center=center,
            fn=fn,
            _no_validation=_no_validation,
        )

    def make_text(
        self, text: str, height: int = 1, font: str = "arial", font_size: int = 10
    ) -> TextExtrusion:
        return TextExtrusion(
            text, height, font, font_size, self._px_size, self._layer_size
        )

    def import_model(self, filename: str, auto_repair: bool = True) -> ImportModel:
        return ImportModel(filename, auto_repair, self._px_size, self._layer_size)

    def make_tpms_cell(
        self,
        size: tuple[int, int, int],
        func: Callable[[int, int, int], int] = TPMS.diamond,
    ) -> TPMS:
        return TPMS(size, func, self._px_size, self._layer_size)

    def make_polychannel(
        self,
        shapes: list[Union[PolychannelShape, BezierCurveShape]],
        show_only_shapes: bool = False,
    ) -> Shape:
        shape_list = []
        shapes = _preprocess_polychannel_shapes(
            shapes, px_size=self._px_size, layer_size=self._layer_size
        )
        for shape in shapes:
            if shape._shape_type == "cube":
                s = self.make_cube(
                    shape._size, center=True, _no_validation=shape._no_validation
                )
            elif shape._shape_type == "sphere":
                s = self.make_sphere(
                    shape._size, center=True, _no_validation=shape._no_validation
                )
            elif shape._shape_type == "rounded_cube":
                s = self.make_rounded_cube(
                    shape._size,
                    shape._rounded_cube_radius,
                    center=True,
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
                return path
            else:
                path = shape_list[0].hull(shape_list[1])
                last_shape = shape_list[1]
                for shape in shape_list[2:]:
                    path += last_shape.hull(shape)
                    last_shape = shape
                return path
        else:
            raise ValueError("Polychannel requires at least 2 shapes")

    def translate(
        self, translation: tuple[int, int, int], set_origin: bool = True
    ) -> Component:
        for component in self.subcomponents:
            component.translate(translation)
        for shape in self.shapes:
            shape.translate(translation)
        for port in self.ports:
            port._position = (
                port._position[0] + translation[0],
                port._position[1] + translation[1],
                port._position[2] + translation[2],
            )
        if set_origin:
            self._position = (
                self._position[0] + translation[0],
                self._position[1] + translation[1],
                self._position[2] + translation[2],
            )
        return self

    def rotate(self, rotation: int, in_place: bool = False) -> Component:
        if rotation % 90 != 0:
            raise ValueError("Rotation must be a multiple of 90 degrees")

        if in_place:
            original_position = self._position
            # Translate the component to position for in-place rotation
            self.translate(
                (-self._position[0], -self._position[1], -self._position[2]),
                set_origin=False,
            )

        for component in self.subcomponents:
            component.rotate(rotation)

        for shape in self.shapes:
            shape.rotate((0, 0, rotation))

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
            },
        }

        for port in self.ports:
            x, y, z = port._position
            size_x, size_y = port._size[0], port._size[1]

            if rot == 90:
                port._position = (-y, x, z)
            elif rot == 180:
                port._position = (-x, -y, z)
            elif rot == 270:
                port._position = (y, -x, z)

            if port._surface_normal in vector_rotation_map.get(rot, {}):
                new_vector, (dx, dy) = vector_rotation_map[rot][port._surface_normal]
                port._position = (
                    port._position[0] + dx * port._size[0],
                    port._position[1] + dy * port._size[1],
                    port._position[2],
                )
                port._surface_normal = new_vector

            # Adjust Z ports if needed
            if port._surface_normal in (
                Port.SurfaceNormal.POS_Z,
                Port.SurfaceNormal.NEG_Z,
            ):
                if rot == 90:
                    port._position = (
                        port._position[0] - port._size[0],
                        port._position[1],
                        port._position[2],
                    )
                elif rot == 180:
                    port._position = (
                        port._position[0] - port._size[0],
                        port._position[1] - port._size[1],
                        port._position[2],
                    )
                elif rot == 270:
                    port._position = (
                        port._position[0],
                        port._position[1] - port._size[1],
                        port._position[2],
                    )

        if in_place:
            # Translate the component so new negative-negative corner is at original position
            if rot == 90:
                self.translate(
                    (
                        original_position[0] + self._size[1],
                        original_position[1],
                        original_position[2],
                    ),
                    set_origin=False,
                )
            elif rot == 180:
                self.translate(
                    (
                        original_position[0] + self._size[0],
                        original_position[1] + self._size[1],
                        original_position[2],
                    ),
                    set_origin=False,
                )
            elif rot == 270:
                self.translate(
                    (
                        original_position[0],
                        original_position[1] + self._size[0],
                        original_position[2],
                    ),
                    set_origin=False,
                )

        return self

    def mirror(
        self, mirror_x: bool = False, mirror_y: bool = False, in_place: bool = False
    ) -> Component:
        if not mirror_x and not mirror_y:
            return self  # No mirroring requested

        if mirror_x and mirror_y:
            return self.rotate(180, in_place=in_place)

        if in_place:
            original_position = self._position
            # Translate the component to position for in-place mirroring
            self.translate(
                (-self._position[0], -self._position[1], -self._position[2]),
                set_origin=False,
            )

        for component in self.subcomponents:
            component.mirror(mirror_x, mirror_y)

        for shape in self.shapes:
            shape.mirror((mirror_x, mirror_y, False))

        # Surface normal flips
        mirror_vector_map = {
            "x": {
                Port.SurfaceNormal.POS_X: Port.SurfaceNormal.NEG_X,
                Port.SurfaceNormal.NEG_X: Port.SurfaceNormal.POS_X,
            },
            "y": {
                Port.SurfaceNormal.POS_Y: Port.SurfaceNormal.NEG_Y,
                Port.SurfaceNormal.NEG_Y: Port.SurfaceNormal.POS_Y,
            },
        }

        for port in self.ports:
            x, y, z = port._position
            sx, sy = port._size[0], port._size[1]

            if mirror_x:
                x = -x - sx
                # If pointing in +X or -X, correct for sticking out
                if port._surface_normal == Port.SurfaceNormal.POS_X:
                    x += sx
                elif port._surface_normal == Port.SurfaceNormal.NEG_X:
                    x += sx
                port._surface_normal = mirror_vector_map["x"].get(
                    port._surface_normal, port._surface_normal
                )

            if mirror_y:
                y = -y - sy
                # If pointing in +Y or -Y, correct for sticking out
                if port._surface_normal == Port.SurfaceNormal.POS_Y:
                    y += sy
                elif port._surface_normal == Port.SurfaceNormal.NEG_Y:
                    y += sy
                port._surface_normal = mirror_vector_map["y"].get(
                    port._surface_normal, port._surface_normal
                )

            port._position = (x, y, z)

        if in_place:
            # Translate the component so new negative-negative corner is at original position
            if mirror_x and not mirror_y:
                self.translate(
                    (
                        original_position[0] + self._size[0],
                        original_position[1],
                        original_position[2],
                    ),
                    set_origin=False,
                )
            elif not mirror_x and mirror_y:
                self.translate(
                    (
                        original_position[0],
                        original_position[1] + self._size[1],
                        original_position[2],
                    ),
                    set_origin=False,
                )

        return self

    def render(self, filename: str = "component.glb", do_bulk_difference: bool = True):
        scene = _render(
            component=self,
            render_bulk=True,
            do_bulk_difference=do_bulk_difference,
            flatten_scene=True,
            wireframe_bulk=False,
            show_assists=False,
        )
        scene.export(filename)

    def preview(
        self,
        filename: str = "pymfd/viewer/component.glb",
        render_bulk: bool = False,
        do_bulk_difference: bool = False,
        wireframe: bool = False,
    ):
        scene = _render(
            component=self,
            render_bulk=render_bulk,
            do_bulk_difference=do_bulk_difference,
            flatten_scene=False,
            wireframe_bulk=wireframe,
            show_assists=True,
        )
        scene.export(filename)
        # from trimesh.viewer.notebook import scene_to_html
        # html_str = scene_to_html(scene)

        # # Inject transparency code
        # transparency_patch = """
        # scene.traverse((child) => {
        #     if (child.isMesh) {
        #         let mat = child.material;
        #         mat.vertexColors = THREE.VertexColors;
        #         mat.metalness = 0.5
        #         mat.transparent = true;
        #         mat.side = THREE.FrontSide;
        #         mat.opacity = 1.0;
        #         if (child.geometry && child.geometry.attributes.color) {
        #             const colors = child.geometry.attributes.color.array;
        #             if (colors.length >= 4) {
        #                 mat.opacity = colors[3];      // alpha of first vertex
        #             }
        #         }
        #     }
        # });
        # """

        # # Add it just before animation starts
        # html_str = html_str.replace("animate();", transparency_patch + "\nanimate();")

        # with open("scene.html", "w") as f:
        #     f.write(html_str)

    def slice_component(
        self, filename: str = "component.glb", do_bulk_difference: bool = True
    ):
        _slice_component(component=self, render_bulk=False, do_bulk_difference=False)


class Device(Component):
    def __init__(
        self,
        name: str,
        size: tuple[int, int, int],
        position: tuple[int, int, int],
        px_size: float = 0.0076,
        layer_size: float = 0.01,
    ):
        super().__init__(size, position, px_size, layer_size)
        self._name = name


# class Device(Component):
#     def __init__(self, resolution:Resolution, position:tuple[int, int, int], layers:int=0, layer_size:float=0.01):
#         super().__init__((resolution.px_count[0],resolution.px_count[1],layers), position, resolution._px_size, layer_size)

# class Visitech_LRS10_Device(Device):
#     def __init__(self, position:tuple[int, int, int], layers:int=0, layer_size:float=0.01):
#         resolution = Resolution(px_size=0.0076, px_count=(2560, 1600))
#         super().__init__(resolution, position, layers, layer_size)

# class Visitech_LRS20_Device(Device):
#     def __init__(self, position:tuple[int, int, int], layers:int=0, layer_size:float=0.01):
#         resolution = Resolution(px_size=0.0152, px_count=(2560, 1600))
#         super().__init__(resolution, position, layers, layer_size)

# class Wintech_Device(Device):
#     def __init__(self, position:tuple[int, int, int], layers:int=0, layer_size:float=0.01):
#         resolution = Resolution(px_size=0.00075, px_count=(1920, 1080))
#         super().__init__(resolution, position, layers, layer_size)
