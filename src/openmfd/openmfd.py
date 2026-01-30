from __future__ import annotations

import sys
import inspect
import importlib
from math import gcd
from enum import Enum
from pathlib import Path
from typing import Union
from functools import reduce
from fractions import Fraction

from .backend import (
    Shape,
    Color,
    Cube,
    render_component,
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
    Class representing a port in a microfluidic device.

    Ports are used to connect components and define their interaction with the environment.

    Each port has a type (IN, OUT, INOUT), a position in 3D space, a size, and a surface normal.

    The surface normal defines the direction in which the port is oriented.
    """

    class PortType(Enum):
        """
        Enumeration for port types.
        
        - IN: Port for input.
        - OUT: Port for output.
        - INOUT: Port for input and/or output.

        """

        IN = 1
        OUT = 2
        INOUT = 3

    class SurfaceNormal(Enum):
        """
        Enumeration for surface normals.

        - POS_X: Positive X direction.
        - POS_Y: Positive Y direction.
        - POS_Z: Positive Z direction.
        - NEG_X: Negative X direction.
        - NEG_Y: Negative Y direction.
        - NEG_Z: Negative Z direction.
        """

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

    def copy(self) -> "Port":
        """Create a copy of the port."""
        p = Port(
            self._type,
            self._position,
            self._size,
            self._surface_normal,
        )
        p._parent = self._parent
        p._name = self._name
        return p

    def get_name(self) -> str:
        # """Get the name of the port, including parent name."""
        if self._name is None:
            raise ValueError(f"Port has not been named")
        else:
            return f"{self._parent._name}_{self._name}"

    def get_fully_qualified_name(self) -> str:
        # """Get the fully qualified name of the port, including all parent components names."""
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
        # """Convert the surface normal to a vector."""
        try:
            return self._vector_map[self._surface_normal]
        except KeyError:
            raise ValueError(f"Unsupported surface normal: {self._surface_normal}")

    def get_bounding_box(
        self, px_size: float = None, layer_size: float = None
    ) -> tuple[int, int, int, int, int, int]:
        # """
        # Get the bounding box of the port.
        # The bounding box is defined by the position and size of the port,
        # adjusted based on the surface normal direction.

        # Parameters:
        # - px_size (float, optional): The pixel size in mm. If not provided, uses the component's pixel size.
        # - layer_size (float, optional): The layer size in mm. If not provided, uses the component's layer size.

        # Returns:
        # - A tuple of six integers representing the bounding box coordinates:
        # (min_x, min_y, min_z, max_x, max_y, max_z)
        # """
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
            round(pos[0] * self._parent._px_size / _px_size, 3),
            round(pos[1] * self._parent._px_size / _px_size, 3),
            round(pos[2] * self._parent._layer_size / _layer_size, 3),
            round(pos[0] * self._parent._px_size / _px_size, 3)
            + round(size[0] * self._parent._px_size / _px_size, 3),
            round(pos[1] * self._parent._px_size / _px_size, 3)
            + round(size[1] * self._parent._px_size / _px_size, 3),
            round(pos[2] * self._parent._layer_size / _layer_size, 3)
            + round(size[2] * self._parent._layer_size / _layer_size, 3),
        )

    def get_origin(self, px_size: float = None, layer_size: float = None):
        # """
        # Get the origin of the port, which is the minimum corner of its bounding box.

        # Parameters:
        # - px_size (float, optional): The pixel size in mm. If not provided, uses the component's pixel size.
        # """
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
            round(self._position[0] * self._parent._px_size / _px_size, 3),
            round(self._position[1] * self._parent._px_size / _px_size, 3),
            round(self._position[2] * self._parent._layer_size / _layer_size, 3),
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
            round(self._size[0] * self._parent._px_size / _px_size, 3),
            round(self._size[1] * self._parent._px_size / _px_size, 3),
            round(self._size[2] * self._parent._layer_size / _layer_size, 3),
        )

    def get_color(self):
        # """
        # Get the color of the port based on its type.

        # The color is determined as follows:

        # - IN ports are green
        # - OUT ports are red
        # - INOUT ports are blue
        # - If the type is not recognized, it defaults to white.

        # Returns:

        # - Color: The color of the port.
        # """
        if self._type == Port.PortType.IN:
            return Color.from_name("g", 255)  # Green
        elif self._type == Port.PortType.OUT:
            return Color.from_name("r", 255)  # Red
        elif self._type == Port.PortType.INOUT:
            return Color.from_name("b", 255)  # Blue
        else:
            return Color.from_name("w", 255)  # White


class Component(_InstantiationTrackerMixin):
    """
    Base class for components in a microfluidic device.

    - Components can contain shapes, ports, subcomponents, and labels.
    - Each component has a size, position, pixel size, and layer size.
    - Components can be translated, rotated, mirrored, and rendered.
    """

    def __init__(
        self,
        size: tuple[int, int, int],
        position: tuple[int, int, int],
        px_size: float = 0.0076,
        layer_size: float = 0.01,
        hide_in_render: bool = False,
        quiet: bool = False,
    ):
        """
        Parameters:

        - size (tuple[int, int, int]): The size of the component in pixels (width, height, depth).
        - position (tuple[int, int, int]): The position of the component in 3D space (x, y, z).
        - px_size (float): The size of a pixel in mm. Default is 0.0076 m.
        - layer_size (float): The size of a layer in mm. Default is 0.01 m.
        - hide_in_render (bool): Whether to hide the component in renders (nessiary for complex components like TPMS). Default is False.
        - quiet (bool): Whether to suppress creation messages. Default is False.
        """
        super().__init__()
        if not quiet:
            print(f"Creating {type(self).__name__} component...")
        self._parent = None
        self._name = None
        self._position = position
        self._size = size
        self._px_size = px_size
        self._layer_size = layer_size
        self.hide_in_render = hide_in_render
        self.quiet = quiet
        self._translations = [0, 0, 0]
        self._rotation = 0
        self._mirroring = [False, False]
        self.shapes = {}
        self.bulk_shapes = {}
        self.ports = {}
        self.connected_ports = []
        self.subcomponents = {}
        self.default_exposure_settings = None
        self.default_position_settings = None
        self.regional_settings = {}
        self.burnin_settings = []
        self.labels = {}

    def __eq__(self, other):
        # """
        # Check if two components are equivilant based on their attribute.

        # We only need to compare the instantiated attributes, the rotation, and mirroring.
        # """
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
        # """
        # Custom attribute lookup for Component.

        # This method is called when an attribute is not found in the usual places.

        # It allows accessing ports by their names.
        # """
        if name in self.ports:
            return self.ports[name]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def get_fully_qualified_name(self):
        # """Get the fully qualified name of the component, including all parent components names."""
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
        # """
        # Get the bounding box of the component.

        # The bounding box is defined by the position and size of the component.

        # Parameters:

        # - px_size (float, optional): The pixel size in mm. If not provided, uses the component's pixel size.
        # - layer_size (float, optional): The layer size in mm. If not provided, uses the component's layer size.

        # Returns:

        # - A tuple of six integers representing the bounding box coordinates:
        # """
        _px_size = self._px_size if px_size is None else px_size
        _layer_size = self._layer_size if layer_size is None else layer_size

        min_x = round(self._position[0] * self._px_size / _px_size, 3)
        max_x = round(
            (self._position[0] + self._size[0]) * self._px_size / _px_size, 3
        )
        min_y = round(self._position[1] * self._px_size / _px_size, 3)
        max_y = round(
            (self._position[1] + self._size[1]) * self._px_size / _px_size, 3
        )
        min_z = round(self._position[2] * self._layer_size / _layer_size, 3)
        max_z = round(
            (self._position[2] + self._size[2]) * self._layer_size / _layer_size, 3
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
            round(self._size[0] * self._px_size / _px_size, 3),
            round(self._size[1] * self._px_size / _px_size, 3),
            round(self._size[2] * self._layer_size / _layer_size, 3),
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
            round(self._position[0] * self._px_size / _px_size, 3),
            round(self._position[1] * self._px_size / _px_size, 3),
            round(self._position[2] * self._layer_size / _layer_size, 3),
        )

    def get_ports(self) -> dict[str, Port]:
        """
        Get a dictionary of ports in the component.

        Returns:
        - dict[str, Port]: A dictionary mapping port names to Port objects.
        """
        return self.ports
    
    def get_labels(self) -> dict[str, Color]:
        """
        Get a dictionary of labels in the component.
        
        Returns:
        - dict[str, Color]: A dictionary mapping label names to Color objects.
        """
        return self.labels
    
    # return dictionary of lists with a dictionary for each type of shape
    def get_shapes(self) -> dict[str, dict[str, Shape]]:
        """
        Get a dictionary of shapes in the component.

        Returns:
        - dict[str, dict[str, Shape]]: A dictionary with keys 'voids' and 'bulks' containing dictionaries of shape names.
        """
        return {
            "voids": self.shapes,
            "bulks": self.bulk_shapes,
            "regional_settings": {k: v[0] for k, v in self.regional_settings.items()},
        }
    
    def get_subcomponents(self) -> dict[str, Component]:
        """
        Get a dictionary of subcomponents in the component.
        
        Returns:
        - dict[str, Component]: A dictionary mapping subcomponent names to Component objects.
        """
        return self.subcomponents

    def _validate_name(self, name):
        # """
        # Validate the name for a new port.

        # Raises:

        # - ValueError: If the name already exists in the component or is not a valid Python identifier.
        # """
        for p in self.ports.keys():
            if p == name:
                raise ValueError(
                    f"Port with name '{name}' already exists in component {self._name}"
                )
        for s in self.shapes.keys():
            if s == name:
                raise ValueError(
                    f"Void with name '{name}' already exists in component {self._name}"
                )
        for s in self.bulk_shapes.keys():
            if s == name:
                raise ValueError(
                    f"Bulk with name '{name}' already exists in component {self._name}"
                )
        for r in self.regional_settings.keys():
            if r == name:
                raise ValueError(
                    f"Regional settings with name '{name}' already exists in component {self._name}"
                )
        for c in self.subcomponents.keys():
            if c == name:
                raise ValueError(
                    f"Subcomponent with name '{name}' already exists in component {self._name}"
                )
        for l in self.labels.keys():
            if l == name:
                raise ValueError(
                    f"Label with name '{name}' already exists in component {self._name}"
                )
        
        if not name.isidentifier():
            raise ValueError(
                f"Name '{name}' is not a valid Python identifier (e.g. no spaces, starts with letter, etc.)"
            )
        if hasattr(self, name):
            raise ValueError(f"Name '{name}' conflicts with existing attributes")

    def add_label(self, name: str, color: Color):
        """
        Add a label to the component.

        Parameters:

        - name (str): The name of the label (must be a unique python identifier).
        - color (Color): The color of the label, which can be a Color object or a tuple of RGBA values.
        """
        self._validate_name(name)
        self.labels[name] = color

    def add_labels(self, mapping: dict[str, Color]):
        """
        Add multiple labels to the component.

        Parameters:

        - mapping (dict[str, Color]): A dictionary mapping label names to their colors.
        """
        for name, color in mapping.items():
            self.add_label(name, color)

    def add_void(self, name: str, shape: Shape, label: str):
        """
        Add a shape to the component.

        Parameters:

        - name (str): The name of the shape (must be a unique python identifier).
        - shape (Shape): The shape to be added.
        - label (str): The label for the shape, which should be a key in the component's labels dictionary.
        """
        self._validate_name(name)
        if shape._parent is not None:
            raise ValueError(
                f"Shape '{shape._name}' has already been added to component '{shape._parent._name}' and cannot be added again."
            )

        shape._name = name
        shape._parent = self
        shape._color = self.labels[label]
        shape._label = label
        self.shapes[name] = shape

    def add_bulk(self, name: str, shape: Shape, label: str):
        """
        Add a bulk shape to the component.

        Parameters:

        - name (str): The name of the bulk shape (must be a unique python identifier).
        - shape (Shape): The bulk shape to be added.
        - label (str): The label for the bulk shape, which should be a key in the component's labels dictionary.
        """
        self._validate_name(name)
        if shape._parent is not None:
            raise ValueError(
                f"Shape '{shape._name}' has already been added to component '{shape._parent._name}' and cannot be added again."
            )

        shape._name = name
        shape._parent = self
        shape._color = self.labels[label]
        shape._label = label
        self.bulk_shapes[name] = shape

    def add_port(self, name: str, port: Port):
        """
        Add a port to the component.

        Parameters:

        - name (str): The name of the port (must be a unique python identifier).
        - port (Port): The port to be added.
        """
        self._validate_name(name)
        if port._parent is not None:
            raise ValueError(
                f"Port '{port._name}' has already been added to component '{port._parent._name}' and cannot be added again."
            )

        port._name = name
        port._parent = self
        self.ports[name] = port

    def add_subcomponent(
        self, name: str, component: Component, hide_in_render: bool = False
    ):
        """
        Add a subcomponent to the component.

        Parameters:

        - name (str): The name of the subcomponent (must be a unique python identifier).
        - component (Component): The subcomponent to be added.
        """
        self._validate_name(name)
        if component._parent is not None:
            raise ValueError(
                f"Component '{component._name}' has already been added to component '{component._parent._name}' and cannot be added again."
            )

        component._name = name
        component._parent = self
        component.run_translate()

        def update_labels(comp: Component, prefix: str = None, parent_labels: dict = None):
            """
            Update labels in the component and its subcomponents to include the prefix.
            If label matches a label in the parent component, it is not changed.
            """
            for label in list(comp.labels.keys()):
                new_label = f"{prefix}.{label}"
                comp.labels[new_label] = comp.labels.pop(label)
            for shape in comp.shapes.values():
                shape._label = f"{prefix}.{shape._label}"
            for shape in comp.bulk_shapes.values():
                shape._label = f"{prefix}.{shape._label}"
            for shape, _ in comp.regional_settings.values():
                shape._label = f"{prefix}.{shape._label}"
            for subcomp in comp.subcomponents.values():
                update_labels(subcomp, prefix, comp.labels)
        update_labels(component, name, self.labels)

        self.subcomponents[name] = component

        if hide_in_render:
            component.hide_in_render = True

    def add_default_exposure_settings(
        self,
        settings: ExposureSettings,
    ):
        """
        Add default exposure settings to the component.

        Parameters:

        - settings (ExposureSettings): The exposure settings to be added.
        """
        self.default_exposure_settings = settings

    def add_default_position_settings(
        self,
        settings: PositionSettings,
    ):
        """
        Add default position settings to the component.

        Parameters:

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
        Add regional settings in a given shape to the component.

        Parameters:

        - name (str): The name of the regional settings (must be a unique python identifier).
        - shape (Shape): The shape to which the regional settings apply.
        - settings (Union[PositionSettings, ExposureSettings, MembraneSettings, SecondaryDoseSettings]): The settings to be applied in the shape.
        - label (str): The label for the regional settings, which should be a key in the component's labels dictionary.
        """
        self._validate_name(name)
        if shape._parent is not None:
            raise ValueError(
                f"Shape '{shape._name}' has already been added to component '{shape._parent._name}' and cannot be added again."
            )

        shape._name = name
        shape._parent = self
        shape._color = self.labels[label]
        shape._label = label

        # check for collisions with other settings
        for existing_name, (
            existing_shape,
            existing_settings,
        ) in self.regional_settings.items():
            combined_shape = shape.copy() & existing_shape.copy()
            if (
                type(settings) == type(existing_settings)
                and not combined_shape._object.is_empty()
            ):
                raise ValueError(
                    f"Regional settings '{name}' collides with existing settings '{existing_name}' in component {self._name}"
                )

        self.regional_settings[name] = (shape, settings)

    def set_burn_in_exposure(self, exposure_times: list[float]):
        """
        Set burn-in exposure times for the component.

        Parameters:

        - exposure_times (list[float]): List of exposure times in seconds for the burn-in process.
        """
        self.burnin_settings = exposure_times

    def relabel(self, mapping: dict[Union[Component, Shape, str], str], recursive = False, _color_mapping: dict[str, Color] = None):
        """
        Relabel listed shapes and labels with new labels.

        Parameters:

        - mapping (dict[Union[Component, Shape, str], str]): A dictionary mapping shapes or labels (or their fully qualified names) to new label names.
        - recursive (bool): If True, relabel subcomponents recursively. Default is False.
        - _color_mapping (dict[str, Color], optional): Internal use only. A dictionary mapping new label names to their colors.
        
        Raises:
        - ValueError: If a shape or label is not found in the component.
        """
        
        if _color_mapping is None:
            _color_mapping = {}
            for _, new_label in mapping.items():
                if new_label in self.labels:
                    _color_mapping[new_label] = self.labels[new_label]
                    continue
                raise ValueError(
                    f"New label '{new_label}' not found in component '{self._name}'"
                )

        for key, new_label in mapping.items():
            shape = None
            if isinstance(key, Shape):
                shape = key
            elif isinstance(key, str):
                # try to resolve fqn to lowest level component
                parts = key.split(".")
                component = self
                for part in parts[:-1]:
                    if part in component.subcomponents:
                        component = component.subcomponents[part]
                    else:
                        raise ValueError(
                            f"Component '{part}' not found in '{component._name}'"
                        )
                key_ending = parts[-1]

                for subcomponent in component.subcomponents.values():
                    subcomponent.relabel({key_ending: new_label}, recursive=recursive, _color_mapping=_color_mapping)
                if key_ending in component.labels or (recursive and any(key.endswith(f".{key_ending}") for key in component.labels.keys())):
                    if key_ending in component.labels:
                        label_key = key_ending
                    else:
                        label_matches = [
                            key
                            for key in component.labels.keys()
                            if key.endswith(f".{key_ending}")
                        ]
                        label_key = label_matches[0]
                    component.labels[new_label] = component.labels.pop(label_key)

                    for shape in [
                        *component.shapes.values(),
                        *component.bulk_shapes.values(),
                        *[s for s, _ in component.regional_settings.values()],
                    ]:
                        if shape._label == label_key or (recursive and shape._label.endswith(
                            f".{key_ending}"
                        )):
                            shape._label = new_label
                            shape._color = _color_mapping[new_label]
                    continue
                elif key_ending in component.shapes or (recursive and any(key.endswith(f".{key_ending}") for key in component.shapes.keys())):
                    if key_ending in component.shapes:
                        shape = component.shapes[key_ending]
                    else:
                        shape_matches = [
                            key
                            for key in component.shapes.keys()
                            if key.endswith(f".{key_ending}")
                        ]
                        shape = component.shapes[shape_matches[0]]
                elif key_ending in component.bulk_shapes or (recursive and any(
                    key.endswith(f".{key_ending}") for key in component.bulk_shapes.keys()
                )):
                    if key_ending in component.bulk_shapes:
                        shape = component.bulk_shapes[key_ending]
                    else:
                        shape_matches = [
                            key
                            for key in component.bulk_shapes.keys()
                            if key.endswith(f".{key_ending}")
                        ]
                        shape = component.bulk_shapes[shape_matches[0]]
                elif key_ending in component.regional_settings or (recursive and any(
                    key.endswith(f".{key_ending}") for key in component.regional_settings.keys()
                )):
                    if key_ending in component.regional_settings:
                        shape = component.regional_settings[key_ending][0]
                    else:
                        shape_matches = [
                            key
                            for key in component.regional_settings.keys()
                            if key.endswith(f".{key_ending}")
                        ]
                        shape = component.regional_settings[shape_matches[0]][0]
                else:
                    if _color_mapping is None:
                        raise ValueError(
                            f"Shape or label '{key_ending}' not found in component '{component._name}'"
                        )
                    else:
                        continue
            else:
                raise ValueError(f"Invalid key type: {type(key)}, must be Shape or str")

            # update shape label and color
            shape._label = new_label
            shape._color = _color_mapping[new_label]

    def connect_port(self, port: Port):
        """
        Label port as connected.

        Parameters:

        - port (Port): Port to connect.
        """
        if port not in self.connected_ports:
            self.connected_ports.append(port)

    def translate(
        self, translation: tuple[int, int, int], _internal: bool = False
    ) -> Component:
        """
        Translate the component by a given translation vector.

        Parameters:

        - translation (tuple[int, int, int]): The translation vector in parent pixels/layers (dx, dy, dz) to apply to the component.
        - _internal (bool): If True, the translation uses the component's pixels/layers for internal calculations and opperates immediatly. Default is False.
        
        Returns:

        - self: The translated component.
        """
        if self._parent is None and not _internal:
            self._translations[0] += translation[0]
            self._translations[1] += translation[1]
            self._translations[2] += translation[2]
        else:
            if not _internal:
                translation = (
                    round(translation[0] / self._px_size * self._parent._px_size, 3),
                    round(translation[1] / self._px_size * self._parent._px_size, 3),
                    round(translation[2] / self._layer_size * self._parent._layer_size, 3),
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
            round(self._translations[0] / self._px_size * self._parent._px_size, 3),
            round(self._translations[1] / self._px_size * self._parent._px_size, 3),
            round(self._translations[2] / self._layer_size * self._parent._layer_size, 3),
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
        Rotate the component around the Z axis by a given angle.
        
        Parameters:

        - rotation (int): The angle in degrees to rotate the component. Must be a multiple of 90.
        - in_place (bool): If True, the component is rotated in place. Default is False.
        
        Returns:

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

            if rot in (90, 270):
                self._size = (self._size[1], self._size[0], self._size[2])
        else:
            # Update position and size for non in-place rotation (position is negative-negative corner)
            if rot == 90:
                self._position = (
                    self._position[0] - self._size[1],
                    self._position[1],
                    self._position[2],
                )
            elif rot == 180:
                self._position = (
                    self._position[0] - self._size[0],
                    self._position[1] - self._size[1],
                    self._position[2],
                )
            elif rot == 270:
                self._position = (
                    self._position[0],
                    self._position[1] - self._size[0],
                    self._position[2],
                )

            if rot in (90, 270):
                self._size = (self._size[1], self._size[0], self._size[2])
        return self

    def mirror(
        self, mirror_x: bool = False, mirror_y: bool = False, in_place: bool = False
    ) -> Component:
        """
        Mirror the component along the X and/or Y axes.
        
        Parameters:

        - mirror_x (bool): If True, mirrors the component along the X axis. Default is False.
        - mirror_y (bool): If True, mirrors the component along the Y axis. Default is False.
        - in_place (bool): If True, performs the mirroring in place. Default is False.
        
        Returns:

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
        else:
            # Update position for non in-place mirroring (position is negative-negative corner)
            if mirror_x and not mirror_y:
                self._position = (
                    self._position[0] - self._size[0],
                    self._position[1],
                    self._position[2],
                )
            elif not mirror_x and mirror_y:
                self._position = (
                    self._position[0],
                    self._position[1] - self._size[1],
                    self._position[2],
                )

        return self

    def render(self, filename: str = "component.glb", do_bulk_difference: bool = True):
        """
        Render the component to a GLB file.
        
        Parameters:

        - filename (str): The name of the output GLB file. Default is "component.glb".
        - do_bulk_difference (bool): If True, applies a difference operation for bulk shapes. Default is True.
        
        Returns:

        - None: The rendered scene is exported to the specified file.
        """
        if not self.quiet:
            print("Rendering Component...")
        scene = render_component(
            component=self,
            path=filename,
            render_bulk=do_bulk_difference,
            do_bulk_difference=do_bulk_difference,
            preview=False,
        )

    @classmethod
    def preview_components(
        cls,
        components: "Component | list[Component]",
        preview_dir: str = "preview",
    ):
        """
        Preview one or more components in GLB files.

        Parameters:

        - components (Component | list[Component]): Components to preview. If a list is provided,
          each entry is exported with __vN suffixes (v1, v2, ...). If a single component is provided,
          no suffix is added.
        - preview_dir (str): The directory where the preview GLB file will be saved. Default is "preview/".

        Returns:

        - None: The rendered scene is exported to the specified file.
        """
        if components is None:
            return None
        if isinstance(components, (list, tuple)):
            components_list = list(components)
        else:
            components_list = [components]

        if any(not getattr(model, "quiet", False) for model in components_list):
            print("Generating Preview...")

        if len(components_list) <= 1:
            scene = render_component(
                component=components_list[0],
                path=preview_dir,
                preview=True,
            )
            return scene

        for index, component in enumerate(components_list, start=1):
            clear_directory = index == 1
            render_component(
                component=component,
                path=preview_dir,
                preview=True,
                version_suffix=f"__v{index}",
                empty_directory=clear_directory
            )

        return None

    def preview(
        self,
        preview_dir: str = "preview",
    ):
        """
        Preview the component in a GLB file.

        Parameters:

        - preview_dir (str): The directory where the preview GLB file will be saved. Default is "preview/".

        Returns:

        - None: The rendered scene is exported to the specified file.
        """
        return self.preview_components(self, preview_dir=preview_dir)


def float_gcf(numbers, max_denominator=10**6):
    """
    Calculate the greatest common factor (GCF) of a list of floating-point numbers.
    """
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
        quiet: bool = False,
    ):
        """
        Initialize a VariableLayerThicknessComponent.

        Parameters:

        - size (tuple[int, int, int]): The size of the component in pixels/layers (width, height, depth).
        - position (tuple[int, int, int]): The position of the component in parent pixels/layers (x, y, z).
        - px_size (float): The pixel size in mm. Default is 0.0076.
        - layer_sizes (list[tuple[int, float]]): A list of layer sizes (as tuples) where each tuple contains the number of duplicates and its size in mm.
        - quiet (bool): If True, suppresses informational output. Default is False.
        """
        self._layer_sizes = layer_sizes

        layer_count = sum(layer_size[0] for layer_size in layer_sizes)

        if layer_count != size[2]:
            raise ValueError(
                f"Layers in layer sizes {layer_count} does not match component height {size[2]}"
            )
        layer_size = float_gcf([layer_size[1] for layer_size in layer_sizes])
        if not quiet:
            print(
                f"\tℹ️ Using common denominator of {layer_size} for layer size for modeling."
            )
            print(
                "\t\tFor best results, component height should be an integer multiple of parent component layers."
            )
        super().__init__(size, position, px_size, layer_size, quiet=quiet)

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
        # """
        # Get the bounding box of the component.

        # The bounding box is defined by the position and size of the component.

        # Parameters:

        # - px_size (float, optional): The pixel size in mm. If not provided, uses the component's pixel size.
        # - layer_size (float, optional): The layer size in mm. If not provided, uses the component's layer size.

        # Returns:

        # - A tuple of six integers representing the bounding box coordinates:
        # """
        _px_size = self._px_size if px_size is None else px_size
        _layer_size = self._layer_size if layer_size is None else layer_size

        min_x = round(self._position[0] * self._px_size / _px_size, 3)
        max_x = round(
            (self._position[0] + self._size[0]) * self._px_size / _px_size, 3
        )
        min_y = round(self._position[1] * self._px_size / _px_size, 3)
        max_y = round(
            (self._position[1] + self._size[1]) * self._px_size / _px_size, 3
        )
        min_z = round(self._position[2] * self._layer_size / _layer_size, 3)
        max_z = round(
            (self._position[2] + self._size[2]) * self._layer_size / _layer_size, 3
        )
        return (min_x, min_y, min_z, max_x, max_y, max_z)

    def get_size(
        self, px_size: float = None, layer_size: float = None
    ) -> tuple[int, int, int]:
        # """
        # Get the size of the component.

        # Parameters:

        # - px_size (float, optional): The pixel size in mm. If not provided, uses the component's pixel size.
        # - layer_size (float, optional): The layer size in mm. If not provided, uses the component's layer size.

        # Returns:

        # - A tuple of three integers representing the size of the component (width, height, depth).
        # """
        _px_size = self._px_size if px_size is None else px_size
        _layer_size = self._layer_size if layer_size is None else layer_size
        return (
            round(self._size[0] * self._px_size / _px_size, 3),
            round(self._size[1] * self._px_size / _px_size, 3),
            round(self._get_device_height() / _layer_size, 3),
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
        quiet: bool = False,
    ):
        """
        Initialize a generic Device.

        Parameters:

        - name (str): The name of the device.
        - position (tuple[int, int, int]): The position of the device in parent pixels/layers (x, y, z).
        - layers (int): The number of layers in the device.
        - layer_size (float): The layer size in mm.
        - px_count (tuple[int, int]): The pixel count of the device (width, height). Default is (2560, 1600).
        - px_size (float): The pixel size in mm. Default is 0.0076.
        - quiet (bool): If True, suppresses informational output. Default is False.
        """
        
        frame = inspect.currentframe()
        args, _, _, values = inspect.getargvalues(frame)
        self.init_args = [values[arg] for arg in args if arg != "self"]
        self.init_kwargs = {arg: values[arg] for arg in args if arg != "self"}

        super().__init__(
            (px_count[0], px_count[1], layers),
            position,
            px_size,
            layer_size,
            quiet=quiet,
        )
        self._name = name


class StitchedDevice(Device):
    def __init__(
        self,
        name: str,
        position: tuple[int, int, int],
        layers: int,
        layer_size: float,
        tiles_x: int,
        tiles_y: int,
        base_px_count: tuple[int, int] = (2560, 1600),
        overlap_px: int = 0,
        px_size: float = 0.0076,
        quiet: bool = False,
    ):
        """
        Initialize a StitchedDevice.

        Parameters:

        - name (str): The name of the device.
        - position (tuple[int, int, int]): The position of the device in parent pixels/layers (x, y, z).
        - layers (int): The number of layers in the device.
        - layer_size (float): The layer size in mm.
        - tiles_x (int): The number of tiles in the X direction.
        - tiles_y (int): The number of tiles in the Y direction.
        - base_px_count (tuple[int, int]): The pixel count of a single tile (width, height). Default is (2560, 1600).
        - overlap_px (int): The number of overlapping pixels between tiles. Default is 0.
        - px_size (float): The pixel size in mm. Default is 0.0076.
        - quiet (bool): If True, suppresses informational output. Default is False.
        """

        frame = inspect.currentframe()
        args, _, _, values = inspect.getargvalues(frame)
        self.init_args = [values[arg] for arg in args if arg != "self"]
        self.init_kwargs = {arg: values[arg] for arg in args if arg != "self"}

        if tiles_x < 1 or tiles_y < 1:
            raise ValueError("tiles_x and tiles_y must be >= 1")
        if overlap_px < 0:
            raise ValueError("overlap_px must be >= 0")
        if overlap_px >= base_px_count[0] or overlap_px >= base_px_count[1]:
            raise ValueError(
                "overlap_px must be smaller than base_px_count in both dimensions"
            )

        stitched_px_count = (
            base_px_count[0] * tiles_x - overlap_px * (tiles_x - 1),
            base_px_count[1] * tiles_y - overlap_px * (tiles_y - 1),
        )
        super().__init__(
            name,
            position,
            layers,
            layer_size,
            px_count=stitched_px_count,
            px_size=px_size,
            quiet=quiet,
        )
        self.tiles_x = tiles_x
        self.tiles_y = tiles_y
        self.base_px_count = base_px_count
        self.overlap_px = overlap_px


class Visitech_LRS10_Device(Device):
    def __init__(
        self,
        name: str,
        position: tuple[int, int, int],
        layers: int = 0,
        layer_size: float = 0.01,
        quiet: bool = False,
    ):
        """
        Initialize a device for a Visitech light engine with LRS10 Lens.
        Parameters:
        - name (str): The name of the device.
        - position (tuple[int, int, int]): The position of the device in parent pixels/layers (x, y, z).
        - layers (int): The number of layers in the device.
        - layer_size (float): The layer size in mm.
        - quiet (bool): If True, suppresses informational output. Default is False.
        """

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
            quiet=quiet,
        )


class Visitech_LRS20_Device(Device):
    def __init__(
        self,
        name: str,
        position: tuple[int, int, int],
        layers: int = 0,
        layer_size: float = 0.01,
        quiet: bool = False,
    ):
        """
        Initialize a device for a Visitech light engine with LRS20 Lens.
        Parameters:
        - name (str): The name of the device.
        - position (tuple[int, int, int]): The position of the device in parent pixels/layers (x, y, z).
        - layers (int): The number of layers in the device.
        - layer_size (float): The layer size in mm.
        - quiet (bool): If True, suppresses informational output. Default is False.
        """

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
            quiet=quiet,
        )


class Wintech_Device(Device):
    def __init__(
        self,
        name: str,
        position: tuple[int, int, int],
        layers: int = 0,
        layer_size: float = 0.0015,
        quiet: bool = False,
    ):
        """
        Initialize a Wintech light engine device.
        Parameters:
        - name (str): The name of the device.
        - position (tuple[int, int, int]): The position of the device in parent pixels/layers (x, y, z).
        - layers (int): The number of layers in the device.
        - layer_size (float): The layer size in mm.
        - quiet (bool): If True, suppresses informational output. Default is False.
        """

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
            quiet=quiet,
        )