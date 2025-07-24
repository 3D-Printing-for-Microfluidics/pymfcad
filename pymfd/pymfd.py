from __future__ import annotations

import sys
import inspect
import importlib
from enum import Enum
from pathlib import Path
from typing import Union
from collections.abc import Callable

from .backend import (
    Shape,
    Cube,
    Cylinder,
    Sphere,
    RoundedCube,
    TextExtrusion,
    ImportModel,
    TPMS,
    Polychannel,
    PolychannelShape,
    BezierCurveShape,
    render_component,
    # slice_component,
    Color,
)

from .slicer import (
    ExposureSettings,
    PositionSettings,
    MembraneSettings,
    SecondaryDoseSettings,
)

_instantiation_paths = {}


class _InstantiationTrackerMixin:
    """Mixin class to track where a component was instantiated."""

    def __init__(self):
        name = type(self).__name__
        if name not in _instantiation_paths:
            # Get the first relevant frame outside of this class
            for frame_info in inspect.stack():
                filename = frame_info.filename
                if "site-packages" in filename or filename == __file__:
                    continue
                self._instantiation_path = Path(filename).resolve()
                _instantiation_paths[name] = self._instantiation_path
                break
        else:
            # If already instantiated, use the existing path
            self._instantiation_path = _instantiation_paths[name]

    @property
    def instantiation_dir(self) -> Path:
        """Return directory of the file that instantiated the component, if it's a Component type or a Device subtype, otherwise the location the module is defined"""
        if self is type(Component) or isinstance(self, Device):
            return self._instantiation_path.parent

        # Fallback: use where the class is defined
        module_name = self.__class__.__module__
        module = sys.modules.get(module_name) or importlib.import_module(module_name)
        path = Path(module.__file__).resolve()
        return path.parent

    @property
    def instantiating_file_stem(self) -> str:
        """Return filename_stem of the file that instantiated the component, if it's a Component type or a Device subtype, otherwise the location the module is defined"""
        from . import Device, Component

        if self is type(Component) or isinstance(self, Device):
            return self._instantiation_path.stem

        # Fallback: use where the class is defined
        module_name = self.__class__.__module__
        module = sys.modules.get(module_name) or importlib.import_module(module_name)
        path = Path(module.__file__).resolve()
        return path.stem


class Port(_InstantiationTrackerMixin):
    """
    ###### Class representing a port in a microfluidic device.
    ###### Ports are used to connect components and define their interaction with the environment.
    ###### Each port has a type (IN, OUT, INOUT), a position in 3D space, a size, and a surface normal.
    ###### The surface normal defines the direction in which the port is oriented.
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
        ###### Initialize a port.

        ###### Parameters:
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
        """Get the name of the port, including parent name."""
        if self._name is None:
            raise ValueError(f"Port has not been named")
        else:
            return f"{self._parent._name}_{self._name}"

    def get_fully_qualified_name(self) -> str:
        """Get the fully qualified name of the port, including all parent components names."""
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

    def get_bounding_box(
        self, px_size: float = None, layer_size: float = None
    ) -> tuple[int, int, int, int, int, int]:
        """
        Get the bounding box of the port.
        The bounding box is defined by the position and size of the port,
        adjusted based on the surface normal direction.

        Parameters:
        - px_size (float, optional): The pixel size in mm. If not provided, uses the component's pixel size.
        - layer_size (float, optional): The layer size in mm. If not provided, uses the component's layer size.

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

        _px_size = self._parent._px_size if px_size is None else px_size
        _layer_size = self._parent._layer_size if layer_size is None else layer_size

        return (
            pos[0] * self._parent._px_size / _px_size,
            pos[1] * self._parent._px_size / _px_size,
            pos[2] * self._parent._layer_size / _layer_size,
            pos[0] * self._parent._px_size / _px_size
            + size[0] * self._parent._px_size / _px_size,
            pos[1] * self._parent._px_size / _px_size
            + size[1] * self._parent._px_size / _px_size,
            pos[2] * self._parent._layer_size / _layer_size
            + size[2] * self._parent._layer_size / _layer_size,
        )

    def get_origin(self, px_size: float = None, layer_size: float = None):
        """
        Get the origin of the port, which is the minimum corner of its bounding box.

        Parameters:
        - px_size (float, optional): The pixel size in mm. If not provided, uses the component's pixel size.
        """
        return self.get_bounding_box(px_size, layer_size)[0:3]

    def get_position(
        self, px_size: float = None, layer_size: float = None
    ) -> tuple[int, int, int]:
        """
        Get the position of the port in 3D space.

        Parameters:
        - px_size (float, optional): The pixel size in mm. If not provided, uses the component's pixel size.
        - layer_size (float, optional): The layer size in mm. If not provided, uses the component's layer size.

        Returns:
        - A tuple of three integers representing the position of the port (x, y, z).
        """

        _px_size = self._parent._px_size if px_size is None else px_size
        _layer_size = self._parent._layer_size if layer_size is None else layer_size
        return (
            self._position[0] * self._parent._px_size / _px_size,
            self._position[1] * self._parent._px_size / _px_size,
            self._position[2] * self._parent._layer_size / _layer_size,
        )

    def get_size(
        self, px_size: float = None, layer_size: float = None
    ) -> tuple[int, int, int]:
        """
        Get the size of the port.

        Parameters:
        - px_size (float, optional): The pixel size in mm. If not provided, uses the component's pixel size.

        Returns:
        - A tuple of three integers representing the size of the port (width, height, depth).
        """
        _px_size = self._parent._px_size if px_size is None else px_size
        _layer_size = self._parent._layer_size if layer_size is None else layer_size
        return (
            self._size[0] * self._parent._px_size / _px_size,
            self._size[1] * self._parent._px_size / _px_size,
            self._size[2] * self._parent._layer_size / _layer_size,
        )

    def get_color(self):
        """
        ###### Get the color of the port based on its type.

        ###### The color is determined as follows:
        - IN ports are green
        - OUT ports are red
        - INOUT ports are blue
        - If the type is not recognized, it defaults to white.

        ###### Returns:
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
    """
    ###### Base class for components in a microfluidic device.
    ###### Components can contain shapes, ports, subcomponents, and labels.
    ###### Each component has a size, position, pixel size, and layer size.
    ###### Components can be translated, rotated, mirrored, and rendered.
    """

    def __init__(
        self,
        size: tuple[int, int, int],
        position: tuple[int, int, int],
        px_size: float = 0.0076,
        layer_size: float = 0.01,
    ):
        """
        ###### Parameters:
        - size (tuple[int, int, int]): The size of the component in pixels (width, height, depth).
        - position (tuple[int, int, int]): The position of the component in 3D space (x, y, z).
        - px_size (float): The size of a pixel in mm. Default is 0.0076 m.
        - layer_size (float): The size of a layer in mm. Default is 0.01 m.
        """
        super().__init__()
        self._parent = None
        self._name = None
        self._position = position
        self._size = size
        self._px_size = px_size
        self._layer_size = layer_size
        self._translations = [0, 0, 0]
        self._rotation = 0
        self._mirroring = [False, False]
        self.shapes = {}
        self.bulk_shapes = {}
        self.ports = {}
        self.subcomponents = {}
        self.default_exposure_settings = None
        self.default_position_settings = None
        self.regional_settings = {}
        self.burnin_settings = []
        self.labels = {}

    def __eq__(self, other):
        """
        ###### Check if two components are equivilant based on their attribute.
        ###### We only need to compare the instantiated attributes, the rotation, and mirroring.
        """
        if not isinstance(other, Component):
            return False
        if not type(self) == type(other):
            return False
        if self._rotation != other._rotation:
            return False
        if self._mirroring != other._mirroring:
            return False
        if len(self.init_args) != len(other.init_args):
            return False
        for i, arg in enumerate(self.init_args):
            if arg != other.init_args[i]:
                return False
        if len(self.init_kwargs) != len(other.init_kwargs):
            return False
        for k, v in self.init_kwargs.items():
            if k not in other.init_kwargs or v != other.init_kwargs[k]:
                return False
        return True

    def __getattr__(self, name):
        """
        ###### Custom attribute lookup for Component.
        ###### This method is called when an attribute is not found in the usual places.
        ###### It allows accessing ports by their names."""
        if name in self.ports:
            return self.ports[name]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def get_fully_qualified_name(self):
        """Get the fully qualified name of the component, including all parent components names."""
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

    def get_bounding_box(
        self, px_size: float = None, layer_size: float = None
    ) -> tuple[int, int, int, int, int, int]:
        """
        Get the bounding box of the component.
        The bounding box is defined by the position and size of the component.

        Parameters:
        - px_size (float, optional): The pixel size in mm. If not provided, uses the component's pixel size.
        - layer_size (float, optional): The layer size in mm. If not provided, uses the component's layer size.

        Returns:
        - A tuple of six integers representing the bounding box coordinates:
        """
        _px_size = self._px_size if px_size is None else px_size
        _layer_size = self._layer_size if layer_size is None else layer_size

        min_x = self._position[0] * self._px_size / _px_size
        max_x = (
            self._position[0] * self._px_size / _px_size
            + self._size[0] * self._px_size / _px_size
        )
        min_y = self._position[1] * self._px_size / _px_size
        max_y = (
            self._position[1] * self._px_size / _px_size
            + self._size[1] * self._px_size / _px_size
        )
        min_z = self._position[2] * self._layer_size / _layer_size
        max_z = (
            self._position[2] * self._layer_size / _layer_size
            + self._size[2] * self._layer_size / _layer_size
        )
        return (min_x, min_y, min_z, max_x, max_y, max_z)

    def get_size(
        self, px_size: float = None, layer_size: float = None
    ) -> tuple[int, int, int]:
        """
        Get the size of the component.

        Parameters:
        - px_size (float, optional): The pixel size in mm. If not provided, uses the component's pixel size.
        - layer_size (float, optional): The layer size in mm. If not provided, uses the component's layer size.

        Returns:
        - A tuple of three integers representing the size of the component (width, height, depth).
        """
        _px_size = self._px_size if px_size is None else px_size
        _layer_size = self._layer_size if layer_size is None else layer_size
        return (
            self._size[0] * self._px_size / _px_size,
            self._size[1] * self._px_size / _px_size,
            self._size[2] * self._layer_size / _layer_size,
        )

    def get_position(
        self, px_size: float = None, layer_size: float = None
    ) -> tuple[int, int, int]:
        """
        Get the position of the component in 3D space.

        Parameters:
        - px_size (float, optional): The pixel size in mm. If not provided, uses the component's pixel size.
        - layer_size (float, optional): The layer size in mm. If not provided, uses the component's layer size.

        Returns:
        - A tuple of three integers representing the position of the component (x, y, z).
        """
        _px_size = self._px_size if px_size is None else px_size
        _layer_size = self._layer_size if layer_size is None else layer_size
        return (
            self._position[0] * self._px_size / _px_size,
            self._position[1] * self._px_size / _px_size,
            self._position[2] * self._layer_size / _layer_size,
        )

    def _validate_name(self, name):
        """
        ###### Validate the name for a new port.
        ###### Raises:
        - ValueError: If the name already exists in the component or is not a valid Python identifier.
        """
        for p in self.ports.keys():
            if p == name:
                raise ValueError(
                    f"Port with name '{name}' already exists in component {self._name}"
                )
        if not name.isidentifier():
            raise ValueError(
                f"Name '{name}' is not a valid Python identifier (e.g. no spaces, starts with letter, etc.)"
            )
        if hasattr(self, name):
            raise ValueError(f"Name '{name}' conflicts with existing attributes")

    def add_label(self, name: str, color: Color):
        """
        ###### Add a label to the component.
        ###### Parameters:
        - name (str): The name of the label (mut be a unique python identifier).
        - color (Color): The color of the label, which can be a Color object or a tuple of RGBA values.
        """
        self._validate_name(name)
        self.labels[name] = color

    def add_shape(self, name: str, shape: Shape, label: str):
        """
        ###### Add a shape to the component.
        ###### Parameters:
        - name (str): The name of the shape (mut be a unique python identifier).
        - shape (Shape): The shape to be added.
        - label (str): The label for the shape, which should be a key in the component's labels dictionary.
        """
        self._validate_name(name)
        shape._name = name
        shape._parent = self
        shape._color = self.labels[label]
        self.shapes[name] = shape

    def add_bulk_shape(self, name: str, shape: Shape, label: str):
        """
        ###### Add a bulk shape to the component.
        ###### Parameters:
        - name (str): The name of the bulk shape (mut be a unique python identifier).
        - shape (Shape): The bulk shape to be added.
        - label (str): The label for the bulk shape, which should be a key in the component's labels dictionary.
        """
        self._validate_name(name)
        shape._name = name
        shape._parent = self
        shape._color = self.labels[label]
        self.bulk_shapes[name] = shape

    def add_port(self, name: str, port: Port):
        """
        ###### Add a port to the component.
        ###### Parameters:
        - name (str): The name of the port (mut be a unique python identifier).
        - port (Port): The port to be added.
        """
        self._validate_name(name)
        port._name = name
        port._parent = self
        self.ports[name] = port

    def add_subcomponent(self, name: str, component: Component):
        """
        ###### Add a subcomponent to the component.
        ###### Parameters:
        - name (str): The name of the subcomponent (mut be a unique python identifier).
        - component (Component): The subcomponent to be added.
        """
        self._validate_name(name)
        component._name = name
        component._parent = self
        component.run_translate()
        self.subcomponents[name] = component

        for label, color in component.labels.items():
            self.labels[f"{name}.{label}"] = color

    def add_default_exposure_settings(
        self,
        settings: ExposureSettings,
    ):
        """
        ###### Add default exposure settings to the component.
        ###### Parameters:
        - settings (ExposureSettings): The exposure settings to be added.
        """
        self.default_exposure_settings = settings

    def add_default_position_settings(
        self,
        settings: PositionSettings,
    ):
        """
        ###### Add default position settings to the component.
        ###### Parameters:
        - settings (PositionSettings): The position settings to be added.
        """
        self.default_position_settings = settings

    def add_regional_settings(
        self,
        name: str,
        shape: Shape,
        settings: Union[
            PositionSettings,
            ExposureSettings,
            MembraneSettings,
            SecondaryDoseSettings,
        ],
        label: str,
    ):
        """
        ###### Add regional settings in a given shape to the component.
        ###### Parameters:
        - name (str): The name of the regional settings (must be a unique python identifier).
        - shape (Shape): The shape to which the regional settings apply.
        - settings (Union[PositionSettings, ExposureSettings, MembraneSettings, SecondaryDoseSettings]): The settings to be applied in the shape.
        - label (str): The label for the regional settings, which should be a key in the component's labels dictionary.
        """
        self._validate_name(name)
        shape._name = name
        shape._parent = self
        shape._color = self.labels[label]

        # check for collisions with other settings
        for existing_name, (
            existing_shape,
            existing_settings,
        ) in self.regional_settings.items():
            if (
                type(settings) == type(existing_settings)
                and not (existing_shape.copy() & shape.copy())._object.is_empty()
            ):
                raise ValueError(
                    f"Regional settings '{name}' collides with existing settings '{existing_name}' in component {self._name}"
                )

        self.regional_settings[name] = (shape, settings)

    def set_burn_in_exposure(self, exposure_times: list[float]):
        """
        ###### Set burn-in exposure times for the component.
        ###### Parameters:
        - exposure_times (list[float]): List of exposure times in seconds for the burn-in process.
        """
        self.burnin_settings = exposure_times

    def relabel_subcomponents(self, subcomponents: list[Component], label: str):
        """
        ###### Relabel listed subcomponents with a new label.
        ###### Parameters:
        - subcomponents (list[Component]): List of subcomponents to relabel.
        - label (str): The new label to apply to the subcomponents.
        """
        for c in subcomponents:
            c.relabel_labels(c.labels.keys(), label, self.labels[label])

    def relabel_labels(self, labels: list[str], label: str, _color: Color = None):
        """
        ###### Relabel subcomponent labels with a new label and color.
        ###### Parameters:
        - labels (list[str]): List of labels to relabel.
        - label (str): The new label to apply.
        - _color (Color, optional): The color to apply to the labels. If None, uses the color of the specified label. (internal use only)
        """
        if _color is None:
            _color = self.labels[label]
        for l, c in self.labels.items():
            if l in labels:
                c._change_to_color(_color)
        for c in self.subcomponents.values():
            c.relabel_labels(labels, label, _color)

    def relabel_shapes(self, shapes: list[Shape], label: str):
        """
        ###### Relabel shapes with a new label.
        ###### Parameters:
        - shapes (list[Shape]): List of shapes to relabel.
        - label (str): The new label to apply to the shapes.
        """
        for s in shapes:
            s._color = self.labels[label]

    def make_cube(self, size: tuple[int, int, int], center: bool = False) -> Cube:
        """
        ###### Create a cube shape.
        ###### Parameters:
        - size (tuple[int, int, int]): The size of the cube in pixels/layers (width, height, depth).
        - center (bool): If True, the cube is centered at the origin. Default is False.
        ###### Returns:
        - Cube: An instance of the Cube class representing the created cube shape.
        """
        return Cube(size, self._px_size, self._layer_size, center=center)

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
        """
        ###### Create a cylinder shape.
        ###### Parameters:
        - h (int): The height of the cylinder in layers.
        - r (float, optional): The radius of the cylinder. If not provided, r1 and r2 must be specified.
        - r1 (float, optional): The radius of the bottom of the cylinder. If not provided, r must be specified.
        - r2 (float, optional): The radius of the top of the cylinder. If not provided, r must be specified.
        - center_xy (bool): If True, the cylinder is centered in the XY plane. Default is True.
        - center_z (bool): If True, the cylinder is centered in the Z direction. Default is False.
        - fn (int): The number of facets for the cylinder. Default is 0, which uses the default resolution.
        ###### Returns:
        - Cylinder: An instance of the Cylinder class representing the created cylinder shape.
        """
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
    ) -> Sphere:
        """
        ###### Create a sphere shape.
        ###### Parameters:
        - size (tuple[int, int, int]): The size of the sphere in pixels/layers (width, height, depth).
        - center (bool): If True, the sphere is centered at the origin. Default is True.
        - fn (int): The number of facets for the sphere. Default is 0, which uses the default resolution.
        ###### Returns:
        - Sphere: An instance of the Sphere class representing the created sphere shape.
        """
        return Sphere(size, self._px_size, self._layer_size, center=center, fn=fn)

    def make_rounded_cube(
        self,
        size: tuple[int, int, int],
        radius: tuple[int, int, int],
        center: bool = False,
        fn: int = 0,
    ) -> RoundedCube:
        """
        ###### Create a rounded cube shape.
        ###### Parameters:
        - size (tuple[int, int, int]): The size of the rounded cube in pixels (width, height, depth).
        - radius (tuple[int, int, int]): The radius of the rounded corners in pixels/layers (rx, ry, rz).
        - center (bool): If True, the rounded cube is centered at the origin. Default is False.
        - fn (int): The number of facets for the rounded cube. Default is 0, which uses the default resolution.
        ###### Returns:
        - RoundedCube: An instance of the RoundedCube class representing the created rounded cube shape.
        """
        return RoundedCube(
            size,
            radius,
            self._px_size,
            self._layer_size,
            center=center,
            fn=fn,
        )

    def make_text(
        self, text: str, height: int = 1, font: str = "arial", font_size: int = 10
    ) -> TextExtrusion:
        """
        ###### Create a text extrusion shape.
        ###### Parameters:
        - text (str): The text to be extruded.
        - height (int): The height of the text extrusion in layers. Default is 1.
        - font (str): The font to be used for the text. Default is "arial".
        - font_size (int): The size of the font in pixels. Default is 10.
        ###### Returns:
        - TextExtrusion: An instance of the TextExtrusion class representing the created text shape.
        """
        return TextExtrusion(
            text, height, font, font_size, self._px_size, self._layer_size
        )

    def import_model(self, filename: str, auto_repair: bool = True) -> ImportModel:
        """
        ###### Import a 3D model from a file.
        ###### Parameters:
        - filename (str): The path to the 3D model file (e.g., STL, OBJ).
        - auto_repair (bool): If True, attempts to repair the model if it has issues. Default is True.
        ###### Returns:
        - ImportModel: An instance of the ImportModel class representing the imported model.
        """
        return ImportModel(filename, auto_repair, self._px_size, self._layer_size)

    def make_tpms_cell(
        self,
        size: tuple[int, int, int],
        cells: tuple[int, int, int] = (1, 1, 1),
        func: Callable[[int, int, int], int] = TPMS.diamond,
        fill: int = 0,
        refinement: int = 10,
    ) -> TPMS:
        """
        ###### Create a TPMS (Triply Periodic Minimal Surface) cell.
        ###### Parameters:
        - size (tuple[int, int, int]): The size of the TPMS unit cell in pixels.
        - cells (tuple[int, int, int]): The number of cells in each dimension (x, y, z).
        - func (Callable[[int, int, int], int]): The function to generate the TPMS surface.
        - fill (int): The fill factor for the TPMS surface ranging from -1 to 1 (isosurface at 0).
        - refinement (int): Number of subdivisions for the TPMS grid.
        ###### Returns:
        - TPMS: An instance of the TPMS class representing the generated surface.
        """
        return TPMS(size, cells, func, fill, refinement, self._px_size, self._layer_size)

    def make_polychannel(
        self,
        shapes: list[Union[PolychannelShape, BezierCurveShape]],
        show_only_shapes: bool = False,
    ) -> Shape:
        """
        ###### Create a polychannel shape from a list of shapes.
        ###### Parameters:
        - shapes (list[Union[PolychannelShape, BezierCurveShape]]): List of shapes to be included in the polychannel.
        - show_only_shapes (bool): If True, only the shapes are shown in the polychannel, without the channel itself. Default is False.
        ###### Returns:
        - Polychannel: An instance of the Polychannel class representing the created polychannel shape.
        """
        return Polychannel(shapes, self._px_size, self._layer_size, show_only_shapes)

    def translate(
        self, translation: tuple[int, int, int], _internal: bool = False
    ) -> Component:
        """
        ###### Translate the component by a given translation vector.
        ###### Parameters:
        - translation (tuple[int, int, int]): The translation vector in parent pixels/layers (dx, dy, dz) to apply to the component.
        - _internal (bool): If True, the translation uses the component's pixels/layers for internal calculations and opperates immediatly. Default is False.
        ###### Returns:
        - self: The translated component.
        """
        if self._parent is None and not _internal:
            self._translations[0] += translation[0]
            self._translations[1] += translation[1]
            self._translations[2] += translation[2]
        else:
            if not _internal:
                translation = (
                    translation[0] / self._px_size * self._parent._px_size,
                    translation[1] / self._px_size * self._parent._px_size,
                    translation[2] / self._layer_size * self._parent._layer_size,
                )
            for component in self.subcomponents.values():
                component.translate(translation)
            for shape in self.shapes.values():
                shape.translate(translation)
            for bulk_shape in self.bulk_shapes.values():
                bulk_shape.translate(translation)
            for shape, _ in self.regional_settings.values():
                shape.translate(translation)
            for port in self.ports.values():
                port._position = (
                    port._position[0] + translation[0],
                    port._position[1] + translation[1],
                    port._position[2] + translation[2],
                )
            if not _internal:
                self._position = (
                    self._position[0] + translation[0],
                    self._position[1] + translation[1],
                    self._position[2] + translation[2],
                )
        return self

    def run_translate(self) -> Component:
        translation = (
            self._translations[0] / self._px_size * self._parent._px_size,
            self._translations[1] / self._px_size * self._parent._px_size,
            self._translations[2] / self._layer_size * self._parent._layer_size,
        )

        for component in self.subcomponents.values():
            component.translate(translation)
        for shape in self.shapes.values():
            shape.translate(translation)
        for bulk_shape in self.bulk_shapes.values():
            bulk_shape.translate(translation)
        for shape, _ in self.regional_settings.values():
            shape.translate(translation)
        for port in self.ports.values():
            port._position = (
                port._position[0] + translation[0],
                port._position[1] + translation[1],
                port._position[2] + translation[2],
            )
        # if set_origin:
        self._position = (
            self._position[0] + translation[0],
            self._position[1] + translation[1],
            self._position[2] + translation[2],
        )

    def rotate(self, rotation: int, in_place: bool = False) -> Component:
        """
        ###### Rotate the component around the Z axis by a given angle.
        ###### Parameters:
        - rotation (int): The angle in degrees to rotate the component. Must be a multiple of 90.
        - in_place (bool): If True, the component is rotated in place. Default is False.
        ###### Returns:
        - self: The rotated component.
        """
        if rotation % 90 != 0:
            raise ValueError("Rotation must be a multiple of 90 degrees")

        self._rotation = (self._rotation + rotation) % 360

        if in_place:
            original_position = self._position
            # Translate the component to position for in-place rotation
            self.translate(
                (-self._position[0], -self._position[1], -self._position[2]),
                _internal=True,
            )

        for component in self.subcomponents.values():
            component.rotate(rotation)

        for shape in self.shapes.values():
            shape.rotate((0, 0, rotation))

        for bulk_shape in self.bulk_shapes.values():
            bulk_shape.rotate((0, 0, rotation))

        for shape, _ in self.regional_settings.values():
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

        for port in self.ports.values():
            x, y, z = port._position

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
                    _internal=True,
                )
            elif rot == 180:
                self.translate(
                    (
                        original_position[0] + self._size[0],
                        original_position[1] + self._size[1],
                        original_position[2],
                    ),
                    _internal=True,
                )
            elif rot == 270:
                self.translate(
                    (
                        original_position[0],
                        original_position[1] + self._size[0],
                        original_position[2],
                    ),
                    _internal=True,
                )

        return self

    def mirror(
        self, mirror_x: bool = False, mirror_y: bool = False, in_place: bool = False
    ) -> Component:
        """
        ###### Mirror the component along the X and/or Y axes.
        ###### Parameters:
        - mirror_x (bool): If True, mirrors the component along the X axis. Default is False.
        - mirror_y (bool): If True, mirrors the component along the Y axis. Default is False.
        - in_place (bool): If True, performs the mirroring in place. Default is False.
        ###### Returns:
        - self: The mirrored component.
        """
        if not mirror_x and not mirror_y:
            return self  # No mirroring requested

        if mirror_x and mirror_y:
            return self.rotate(180, in_place=in_place)

        self._mirroring = [mirror_x ^ self._mirroring[0], mirror_y ^ self._mirroring[1]]

        if in_place:
            original_position = self._position
            # Translate the component to position for in-place mirroring
            self.translate(
                (-self._position[0], -self._position[1], -self._position[2]),
                _internal=True,
            )

        for component in self.subcomponents.values():
            component.mirror(mirror_x, mirror_y)

        for shape in self.shapes.values():
            shape.mirror((mirror_x, mirror_y, False))

        for bulk_shape in self.bulk_shapes.values():
            bulk_shape.mirror((mirror_x, mirror_y, False))

        for shape, _ in self.regional_settings.values():
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

        for port in self.ports.values():
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
                    _internal=True,
                )
            elif not mirror_x and mirror_y:
                self.translate(
                    (
                        original_position[0],
                        original_position[1] + self._size[1],
                        original_position[2],
                    ),
                    _internal=True,
                )

        return self

    def render(self, filename: str = "component.glb", do_bulk_difference: bool = True):
        """
        ###### Render the component to a GLB file.
        ###### Parameters:
        - filename (str): The name of the output GLB file. Default is "component.glb".
        - do_bulk_difference (bool): If True, applies a difference operation for bulk shapes. Default is True.
        ###### Returns:
        - None: The rendered scene is exported to the specified file.
        """
        scene = render_component(
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
        """
        ###### Preview the component in a GLB file.
        ###### Parameters:
        - filename (str): The name of the output GLB file. Default is "pymfd/viewer/component.glb".
        - render_bulk (bool): If True, renders bulk shapes. Default is False.
        - do_bulk_difference (bool): If True, applies a difference operation for bulk shapes. Default is False.
        - wireframe (bool): If True, renders the scene in wireframe mode. Default is False.
        ###### Returns:
        - None: The rendered scene is exported to the specified file.
        """
        scene = render_component(
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


from math import gcd
from functools import reduce
from fractions import Fraction


def float_gcf(numbers, max_denominator=10**6):
    if not numbers:
        raise ValueError("Input list must not be empty")

    # Convert all floats to Fractions
    fracs = [Fraction(x).limit_denominator(max_denominator) for x in numbers]

    # Get least common multiple (LCM) of all denominators
    def lcm(a, b):
        return abs(a * b) // gcd(a, b)

    common_den = reduce(lcm, (f.denominator for f in fracs))

    # Convert all to integers with common denominator
    int_values = [int(f * common_den) for f in fracs]

    # Compute GCF of these integers
    result = reduce(gcd, int_values)

    # Convert back to float
    return result / common_den


class VariableLayerThicknessComponent(Component):
    """
    A component with variable layer thickness, allowing for different layer sizes at each height.
    """

    def __init__(
        self,
        size: tuple[int, int, int],
        position: tuple[int, int, int],
        px_size: float = 0.0076,
        layer_sizes: list[tuple[int, float]] = [(1, 0.01)],
    ):
        """
        Initialize a VariableLayerThicknessComponent.

        Parameters:
        - size (tuple[int, int, int]): The size of the component in pixels/layers (width, height, depth).
        - position (tuple[int, int, int]): The position of the component in parent pixels/layers (x, y, z).
        - px_size (float): The pixel size in mm. Default is 0.0076.
        - layer_sizes (list[tuple[int, float]]): A list of layer sizes (as tuples) where each tuple contains the number of duplicates and its size in mm.
        """
        self._layer_sizes = layer_sizes

        layer_count = sum(layer_size[0] for layer_size in layer_sizes)

        if layer_count != size[2]:
            raise ValueError(
                f"Layers in layer sizes {layer_count} does not match component height {size[2]}"
            )
        layer_size = float_gcf([layer_size[1] for layer_size in layer_sizes])
        print(f"Using common denominator of {layer_size} for layer size for modeling.")
        print(
            "For best results, VariableLayerThicknessComponent height should align with parent component layers."
        )
        super().__init__(size, position, px_size, layer_size)

    def _expand_layer_sizes(self) -> list[float]:
        """Expand the layer sizes into a list of heights for each layer."""
        expanded_sizes = []
        for count, size in self._layer_sizes:
            expanded_sizes.extend([size] * count)
        return expanded_sizes

    def _get_device_height(self) -> float:
        """Get the height of the device in mm based on the layer sizes."""
        return sum(
            self._layer_sizes[i][0] * self._layer_sizes[i][1]
            for i in range(len(self._layer_sizes))
        )

    def get_bounding_box(
        self, px_size: float = None, layer_size: float = None
    ) -> tuple[int, int, int, int, int, int]:
        """
        Get the bounding box of the component.
        The bounding box is defined by the position and size of the component.

        Parameters:
        - px_size (float, optional): The pixel size in mm. If not provided, uses the component's pixel size.
        - layer_size (float, optional): The layer size in mm. If not provided, uses the component's layer size.

        Returns:
        - A tuple of six integers representing the bounding box coordinates:
        """
        _px_size = self._px_size if px_size is None else px_size
        _layer_size = self._layer_size if layer_size is None else layer_size

        min_x = self._position[0] * self._px_size / _px_size
        max_x = (
            self._position[0] * self._px_size / _px_size
            + self._size[0] * self._px_size / _px_size
        )
        min_y = self._position[1] * self._px_size / _px_size
        max_y = (
            self._position[1] * self._px_size / _px_size
            + self._size[1] * self._px_size / _px_size
        )
        min_z = self._position[2] * self._layer_size / _layer_size
        max_z = (
            self._position[2] * self._layer_size / _layer_size
            + self._get_device_height() / _layer_size
        )
        return (min_x, min_y, min_z, max_x, max_y, max_z)

    def get_size(
        self, px_size: float = None, layer_size: float = None
    ) -> tuple[int, int, int]:
        """
        Get the size of the component.

        Parameters:
        - px_size (float, optional): The pixel size in mm. If not provided, uses the component's pixel size.
        - layer_size (float, optional): The layer size in mm. If not provided, uses the component's layer size.

        Returns:
        - A tuple of three integers representing the size of the component (width, height, depth).
        """
        _px_size = self._px_size if px_size is None else px_size
        _layer_size = self._layer_size if layer_size is None else layer_size
        return (
            self._size[0] * self._px_size / _px_size,
            self._size[1] * self._px_size / _px_size,
            self._get_device_height() / _layer_size,
        )


class Device(Component):
    def __init__(
        self,
        name: str,
        position: tuple[int, int, int],
        layers: int = 0,
        layer_size: float = 0.01,
        px_count: tuple[int, int] = (2560, 1600),
        px_size: float = 0.0076,
    ):
        super().__init__(
            (px_count[0], px_count[1], layers),
            position,
            px_size,
            layer_size,
        )
        self._name = name


class Visitech_LRS10_Device(Device):
    def __init__(
        self,
        name: str,
        position: tuple[int, int, int],
        layers: int = 0,
        layer_size: float = 0.01,
    ):
        frame = inspect.currentframe()
        args, _, _, values = inspect.getargvalues(frame)
        self.init_args = [values[arg] for arg in args if arg != "self"]
        self.init_kwargs = {arg: values[arg] for arg in args if arg != "self"}
        super().__init__(
            name,
            position,
            layers,
            layer_size,
            px_count=(2560, 1600),
            px_size=0.0076,
        )

        # super().__init__(
        #     name,
        #     position,
        #     layers,
        #     layer_size,
        #     px_count=(200, 200),
        #     px_size=0.0076,
        # )

        # super().__init__(
        #     name,
        #     position,
        #     layers,
        #     layer_size,
        #     px_count=(200, 200),
        #     px_size=0.0076,
        # )


class Visitech_LRS20_Device(Device):
    def __init__(
        self,
        name: str,
        position: tuple[int, int, int],
        layers: int = 0,
        layer_size: float = 0.01,
    ):
        frame = inspect.currentframe()
        args, _, _, values = inspect.getargvalues(frame)
        self.init_args = [values[arg] for arg in args if arg != "self"]
        self.init_kwargs = {arg: values[arg] for arg in args if arg != "self"}

        super().__init__(
            name,
            position,
            layers,
            layer_size,
            px_count=(2560, 1600),
            px_size=0.0152,
        )


class Wintech_Device(Device):
    def __init__(
        self,
        name: str,
        position: tuple[int, int, int],
        layers: int = 0,
        layer_size: float = 0.01,
    ):
        frame = inspect.currentframe()
        args, _, _, values = inspect.getargvalues(frame)
        self.init_args = [values[arg] for arg in args if arg != "self"]
        self.init_kwargs = {arg: values[arg] for arg in args if arg != "self"}

        super().__init__(
            name,
            position,
            layers,
            layer_size,
            px_count=(1920, 1080),
            px_size=0.00075,
        )
