from __future__ import annotations

import os
import time
import heapq
import pickle
import numpy as np
from rtree import index
from typing import Union
from copy import deepcopy

from .. import Polychannel, PolychannelShape, BezierCurveShape
from ..backend.manifold3d import _is_integer


class _AutorouterNode:
    """
    A node in the A* search algorithm for 3D routing.
    """

    def __init__(
        self,
        pos,
        parent=None,
        cost=0,
        turns=0,
        direction=None,
        heuristic=0,
        heuristic_weight=10,
        turn_weight=2,
    ):
        """
        Parameters:

        - pos: The position of the node in 3D space (tuple of 3 floats).
        - parent: The parent node in the search tree.
        - cost: The cost to reach this node from the start node.
        - turns: The number of turns taken to reach this node.
        - direction: The direction of the last move made to reach this node (tuple of 3 ints).
        - heuristic: The estimated cost to reach the goal from this node.
        - heuristic_weight: Weighting factor for the heuristic.
        - turn_weight: Weighting factor for the number of turns.
        """
        self._pos = pos
        self._parent = parent
        self._cost = cost
        self._turns = turns
        self._direction = direction
        self._heuristic = heuristic
        self._heuristic_weight = heuristic_weight
        self._turn_weight = turn_weight

    def __lt__(self, other):
        """
        Less than comparison for priority queue sorting.
        Compares the total cost (cost + heuristic + turns) of two nodes.
        """
        return (
            self._cost
            + self._heuristic_weight * self._heuristic
            + self._turn_weight * self._turns
        ) < (
            other._cost
            + self._heuristic_weight * other._heuristic
            + self._turn_weight * other._turns
        )


class Router:
    """
    A class for routing channels in a 3D component using various methods.
    This class provides methods for autorouting, manual routing with polychannels,
    and routing with fractional paths. It also manages keepouts and bounding boxes
    for the component and its subcomponents.
    """

    def __init__(
        self,
        component: "Component",
        channel_size: tuple[int, int, int] = (0, 0, 0),
        channel_margin: tuple[int, int, int] = (0, 0, 0),
        quiet: bool = False,
    ):
        """
        Initializes the Router with a component and channel specifications.

        Parameters:

        - component: The Component instance to route channels within.
        - channel_size: The size of the channels to be routed (tuple of 3 ints).
        - channel_margin: The margin to apply around the channels (tuple of 3 ints).
        - quiet: If True, suppresses informational output.
        """
        self._routes = {}
        self._component = component
        self._channel_size = channel_size
        self._channel_margin = channel_margin
        self._quiet = quiet
        self._bounds = self._component.get_bounding_box()
        self.nonrouted_keepouts = {}
        self.routed_keepouts = {}
        self.keepouts_by_port = {}

    def _generate_keepout_index(self, keepouts=None):
        # Generate rtree and list of keepouts from components, ports, and shapes
        # If keepouts are provided, only add new or updated keepouts to the index
        p = index.Property()
        p.dimension = 3  # because you're working in 3D
        idx = index.Index(properties=p)

        cnt = 0
        for key, subcomponent in self._component.subcomponents.items():
            # add subcomponet keepout
            ko = subcomponent.get_bounding_box(
                self._component._px_size, self._component._layer_size
            )
            if keepouts is not None and key in keepouts:
                if keepouts[key][1] != ko:
                    idx.insert(cnt, ko)
                    self.nonrouted_keepouts[key] = (cnt, ko)
                    cnt += 1
            else:
                idx.insert(cnt, ko)
                self.nonrouted_keepouts[key] = (cnt, ko)
                cnt += 1

            # add port keepout
            for port in subcomponent.ports.values():
                key = port.get_name()
                ko = self._add_margin(
                    port.get_bounding_box(
                        self._component._px_size, self._component._layer_size
                    ),
                    self._channel_margin,
                )

                if keepouts is not None and key in keepouts:
                    if keepouts[key][1] != ko:
                        idx.insert(cnt, ko)
                        self.keepouts_by_port[key] = [key]
                        self.routed_keepouts[key] = (cnt, ko)
                        cnt += 1
                    else:
                        self.keepouts_by_port[key] = []
                else:
                    idx.insert(cnt, ko)
                    self.keepouts_by_port[key] = [key]
                    self.routed_keepouts[key] = (cnt, ko)
                    cnt += 1

        # add shape keepout
        for i, (shape_name, shape) in enumerate(self._component.shapes.items()):
            for j, keepout in enumerate(shape._keepouts):
                key = f"{i}_{j}"
                if shape_name is not None:
                    key = f"{shape_name}_{j}"
                ko = self._add_margin(
                    tuple(float(x) for x in keepout), self._channel_margin
                )
                if keepouts is not None and key in keepouts:
                    if keepouts[key][1] != ko:
                        idx.insert(cnt, ko)
                        self.nonrouted_keepouts[key] = (cnt, ko)
                        cnt += 1
                else:
                    idx.insert(cnt, ko)
                    self.nonrouted_keepouts[key] = (cnt, ko)
                    cnt += 1

        self._keepout_index = idx

    def _add_margin(self, bbox, margin):
        """
        Adds a margin to a bounding box.

        Parameters:

        - bbox: The bounding box to which the margin will be added (tuple of 6 floats).
        - margin: The margin to add to each side of the bounding box (tuple of 3 floats).

        Returns:

        - A new bounding box with the margin applied (tuple of 6 floats).
        """
        (x0, y0, z0, x1, y1, z1) = bbox
        mx, my, mz = margin
        return (x0 - mx, y0 - my, z0 - mz, x1 + mx, y1 + my, z1 + mz)
    
    def _port_from_fqn(self, fqn: str) -> "Port":
        """
        Retrieves a Port instance from its fully qualified name (FQN).

        Parameters:

        - fqn: The fully qualified name of the port (str).

        Returns:

        - The Port instance corresponding to the FQN.

        Raises:

        - ValueError: If the port cannot be found.
        """
        parts = fqn.split(".")
        component = self._component
        for part in parts[:-1]:
            if part in component.subcomponents:
                component = component.subcomponents[part]
            else:
                raise ValueError(f"Component '{part}' not found in FQN '{fqn}'")
        port_name = parts[-1]
        if port_name in component.ports:
            return component.ports[port_name]
        else:
            raise ValueError(f"Port '{port_name}' not found in FQN '{fqn}'")

    def autoroute_channel(
        self,
        input_port: "Port" | str,
        output_port: "Port" | str,
        label: str,
        timeout: int = 120,
        heuristic_weight: int = 10,
        turn_weight: int = 2,
        direction_preference: tuple[str] = ("X", "Y", "Z"),
    ):
        """
        Automatically routes a channel between two ports using A* algorithm.

        Parameters:

        - input_port: The Port instance where the channel starts.
        - output_port: The Port instance where the channel ends.
        - label: A label for the routed channel.
        - timeout: The maximum time allowed for the routing operation (in seconds).
        - heuristic_weight: Weighting factor for the heuristic in the A* algorithm.
        - turn_weight: Weighting factor for the number of turns in the A* algorithm.

        Raises:

        - ValueError: If either port has not been added to the component before routing.
        """
        if isinstance(input_port, str):
            input_port = self._port_from_fqn(input_port)
        if isinstance(output_port, str):
            output_port = self._port_from_fqn(output_port)

        if input_port._parent is None:
            raise ValueError("Port must be added to component before routing! (input)")
        if output_port._parent is None:
            raise ValueError("Port must be added to component before routing! (output)")

        name = f"{input_port.get_name()}__to__{output_port.get_name()}"

        self._routes[name] = {
            "route_type": "autoroute",
            "input": input_port,
            "output": output_port,
            "label": label,
            "timeout": timeout,
            "heuristic_weight": heuristic_weight,
            "turn_weight": turn_weight,
            "direction_preference": direction_preference,
        }

    def route_with_polychannel(
        self,
        input_port: "Port" | str,
        output_port: "Port" | str,
        polychannel_shapes: list[Union[PolychannelShape, BezierCurveShape]],
        label: str,
    ):
        """
        Routes a channel between two ports using a specified polychannel path.

        Parameters:

        - input_port: The Port instance where the channel starts.
        - output_port: The Port instance where the channel ends.
        - polychannel_shapes: A list of PolychannelShape or BezierCurveShape instances defining the channel path.
        - label: A label for the routed channel.

        Raises:

        - ValueError: If either port has not been added to the component before routing.
        """
        if isinstance(input_port, str):
            input_port = self._port_from_fqn(input_port)
        if isinstance(output_port, str):
            output_port = self._port_from_fqn(output_port)

        if input_port._parent is None:
            raise ValueError("Port must be added to component before routing! (input)")
        if output_port._parent is None:
            raise ValueError("Port must be added to component before routing! (output)")
        
        name = f"{input_port.get_name()}__to__{output_port.get_name()}"

        input_size = list(input_port.get_size(
            self._component._px_size, self._component._layer_size
        ))
        input_pos = (
            np.array(
                input_port.get_origin(
                    self._component._px_size, self._component._layer_size
                )
            )
            + np.array(input_size) / 2
        )
        if input_port.get_name().startswith("None_"):
            # shift position to edge of port
            vect = input_port.to_vector()
            for i in range(3):
                if vect[i] != 0:
                    input_pos[i] -= vect[i] * input_size[i]/2
                    input_size[i] = 0
        polychannel_shapes.insert(
            0,
            PolychannelShape(
                "cube",
                position=input_pos,
                size=input_size,
                absolute_position=True,
            ),
        )
        output_size = list(output_port.get_size(
            self._component._px_size, self._component._layer_size
        ))
        output_pos = (
            np.array(
                output_port.get_origin(
                    self._component._px_size, self._component._layer_size
                )
            )
            + np.array(output_size) / 2
        )
        if output_port.get_name().startswith("None_"):
            # shift position to edge of port
            vect = output_port.to_vector()
            for i in range(3):
                if vect[i] != 0:
                    output_pos[i] -= vect[i] * output_size[i]/2
                    output_size[i] = 0
        polychannel_shapes.append(
            PolychannelShape(
                "cube",
                position=output_pos,
                size=output_size,
                absolute_position=True,
                corner_radius=0,
            )
        )

        self._routes[name] = {
            "route_type": "polychannel",
            "input": input_port,
            "output": output_port,
            "label": label,
            "_path": polychannel_shapes,
        }

    def route_with_fractional_path(
        self,
        input_port: "Port" | str,
        output_port: "Port" | str,
        route: list[tuple[float, float, float]],
        label: str,
    ):
        """
        Routes a channel between two ports using a fractional path.

        Parameters:

        - input_port: The Port instance where the channel starts.
        - output_port: The Port instance where the channel ends.
        - route: A list of tuples representing the fractional path segments (each tuple contains three floats) the sum of each digit must add to 1.0.
        - label: A label for the routed channel.

        Raises:

        - ValueError: If either port has not been added to the component before routing.
        """
        if isinstance(input_port, str):
            input_port = self._port_from_fqn(input_port)
        if isinstance(output_port, str):
            output_port = self._port_from_fqn(output_port)

        name = f"{input_port.get_name()}__to__{output_port.get_name()}"

        # get locations
        input_size = input_port.get_size(
            self._component._px_size, self._component._layer_size
        )
        start_loc = input_port.get_position(
            self._component._px_size, self._component._layer_size
        )
        output_size = output_port.get_size(
            self._component._px_size, self._component._layer_size
        )
        end_loc = output_port.get_position(
            self._component._px_size, self._component._layer_size
        )
        start_loc = [round(x) for x in start_loc]
        end_loc = [round(x) for x in end_loc]
        
        diff = tuple(a - b for a, b in zip(end_loc, start_loc))

        # relative positions to absolute path
        path = [start_loc]
        sum_x = 0.0
        sum_y = 0.0
        sum_z = 0.0
        for r in route:
            x, y, z = r
            sum_x += x
            sum_y += y
            sum_z += z
            path.append(
                (
                    start_loc[0] + round(sum_x * diff[0]),
                    start_loc[1] + round(sum_y * diff[1]),
                    start_loc[2] + round(sum_z * diff[2]),
                )
            )

        if sum_x != 1.0 or sum_y != 1.0 or sum_z != 1.0:
            raise ValueError(
                f"Fractional routing components must sum to (1.0, 1.0, 1.0) currently ({sum_x}, {sum_y}, {sum_z})"
            )

        # path to constant cross-section polychannel shapes
        polychannel_shapes = self._path_to_polychannel_shapes(
            input_port, output_port, path[1:-1]
        )

        self._routes[name] = {
            "route_type": "fractional",
            "input": input_port,
            "output": output_port,
            "label": label,
            "_path": polychannel_shapes,
        }

    def _path_to_polychannel_shapes(self, input_port, output_port, path):
        """
        Converts a path defined by a list of points into a list of PolychannelShape instances.

        Parameters:

        - input_port: The Port instance where the channel starts.
        - output_port: The Port instance where the channel ends.
        - path: A list of tuples representing the path segments (each tuple contains three floats).

        Returns:

        - A list of PolychannelShape instances representing the channel path.
        """
        polychannel_shapes = []

        # Handle input port
        input_size = input_port.get_size(
            self._component._px_size, self._component._layer_size
        )
        input_pos = (
            np.array(
                input_port.get_origin(
                    self._component._px_size, self._component._layer_size
                )
            )
            + np.array(input_size) / 2
        )
        if input_port.get_name().startswith("None_"):
            # shift position to edge of port
            vect = input_port.to_vector()
            for i in range(3):
                if vect[i] != 0:
                    input_pos[i] -= vect[i] * input_size[i]
        polychannel_shapes.append(
            PolychannelShape(
                "cube",
                position=tuple(input_pos),
                size=input_size,
                absolute_position=True,
            )
        )

        # Handle middle path segments
        for point in path:
            point_pos = np.array(point) + np.array(self._channel_size) / 2
            polychannel_shapes.append(
                PolychannelShape(
                    "cube",
                    position=tuple(point_pos),
                    size=self._channel_size,
                    absolute_position=True,
                )
            )

        # Handle output port
        output_size = output_port.get_size(
            self._component._px_size, self._component._layer_size
        )
        output_pos = (
            np.array(
                output_port.get_origin(
                    self._component._px_size, self._component._layer_size
                )
            )
            + np.array(output_size) / 2
        )
        if output_port.get_name().startswith("None_"):
            # shift position to edge of port
            vect = output_port.to_vector()
            for i in range(3):
                if vect[i] != 0:
                    output_pos[i] -= vect[i] * output_size[i]
        polychannel_shapes.append(
            PolychannelShape(
                "cube",
                position=tuple(output_pos),
                size=output_size,
                absolute_position=True,
            )
        )

        return polychannel_shapes

    def finalize_routes(self):
        """
        Routes all defined channels in the component.
        This method checks for cached routes, loads them if valid, and reroutes if necessary.
        It handles both manual routing with polychannels and autorouting using the A* algorithm.
        """
        if not self._quiet:
            print(f"\tRouting {type(self._component).__name__}...")
        keepouts, self.cached_routes = self._load_cached_route()
        self._generate_keepout_index(keepouts)
        new_routes = []
        loaded_routes = []
        if not self._quiet:
            print("\r\t\t📦 Loading cached routes...", end="", flush=True)
        for i, (name, route_info) in enumerate(
            self._routes.items()
        ):  # Route cached paths if valid
            input_port = route_info["input"]
            output_port = route_info["output"]
            if self.cached_routes is not None:
                if not self._quiet:
                    print(
                        f"\r\t\tLoading cached routes ({(i+1)/len(self._routes)*100:.2f}%)...",
                        end="",
                        flush=True,
                    )
            removed_keepouts = self._remove_port_keepouts(input_port, output_port)
            if self.cached_routes is not None and name in self.cached_routes:
                if self._load_route(name, route_info, self.cached_routes[name]):
                    self._add_port_keepouts(removed_keepouts)
                    loaded_routes.append(name)
                    continue
                else:
                    if not self._quiet:
                        print(f"\r\n\t\t\tRerouting {name}...")
            self._add_port_keepouts(removed_keepouts)
            new_routes.append((name, route_info))  # Cache is stale/missing → reroute

        # Add keepouts for cached routes
        if not self._quiet:
            print("\r\n\t\tGenerating keepouts...", end="", flush=True)
        self._generate_keepout_index()
        for i, name in enumerate(loaded_routes):
            if not self._quiet:
                print(
                    f"\r\t\tGenerating keepouts ({(i+1)/len(loaded_routes)*100:.2f}%)...",
                    end="",
                    flush=True,
                )
            self._add_keepouts_from_polychannel(name, self._component.shapes[name])

        if not self._quiet:
            print(f"\r\n\t\tManual Routing...", end="", flush=True)
        for i, (name, route_info) in enumerate(new_routes):
            input_port = route_info["input"]
            output_port = route_info["output"]
            if not self._quiet:
                print(
                    f"\r\t\tManual Routing ({(i+1)/len(new_routes)*100:.2f}%)...",
                    end="",
                    flush=True,
                )
            if route_info["route_type"] != "autoroute":  # Manual routing
                removed_keepouts = self._remove_port_keepouts(input_port, output_port)
                self._route(name, route_info)
                self._add_port_keepouts(removed_keepouts)

        if not self._quiet:
            print(f"\r\n\t\tAutorouting...", end="", flush=True)
        for i, (name, route_info) in enumerate(new_routes):  # Autoroute paths
            input_port = route_info["input"]
            output_port = route_info["output"]
            if not self._quiet:
                print(
                    f"\r\t\tAutorouting ({(i+1)/len(new_routes)*100:.2f}%)...",
                    end="",
                    flush=True,
                )
            if route_info["route_type"] == "autoroute":  # Autorouting
                removed_keepouts = self._remove_port_keepouts(input_port, output_port)
                self._autoroute(name, route_info)
                self._add_port_keepouts(removed_keepouts)
        if not self._quiet:
            print()
        self._cache_routes()

        # release memory
        del keepouts, self.cached_routes
        del self._keepout_index
        del self._routes
        self.nonrouted_keepouts = {}
        self.routed_keepouts = {}
        self.keepouts_by_port = {}

    def _load_cached_route(self):
        """
        Loads a cached route from a file.

        Parameters:

        - name: The name of the route to load.

        Returns:

        - A dictionary containing the cached route information if it exists, otherwise None.
        """
        instantiation_dir = self._component.instantiation_dir
        file_stem = self._component.instantiating_file_stem
        from .. import Component, Device, VariableLayerThicknessComponent, StitchedDevice
        if type(self._component) in (Component, Device, VariableLayerThicknessComponent, StitchedDevice):
            if self._component._name is not None:
                file_name = self._component._name
            else:
                file_name = type(self._component).__name__
        else:
            file_name = type(self._component).__name__
        cache_file = (
            instantiation_dir
            / f"{file_stem}_cache"
            / f"{file_name}.pkl"
        )

        if os.path.exists(cache_file):
            if not self._quiet:
                print(f"\t\t📦 Loading cached route from {cache_file}...")
            with open(cache_file, "rb") as f:
                return pickle.load(f)
        return None, None

    def _load_route(self, name: str, route_info: dict, cached_info: dict):
        """
        Validates and loads a route from cached information.

        Parameters:

        - name: The name of the route to load.
        - route_info: A dictionary containing the route information to validate.
        - cached_info: A dictionary containing the cached route information.

        Returns:

        - True if the route is valid and loaded successfully, otherwise False.
        """
        input_port = route_info["input"]
        output_port = route_info["output"]

        # validate route type
        if route_info["route_type"] != cached_info["route_type"]:
            return False

        # validate input and output locations
        if tuple(cached_info["input"]) != tuple(
            input_port.get_origin(self._component._px_size, self._component._layer_size)
        ) or tuple(cached_info["output"]) != tuple(
            output_port.get_origin(self._component._px_size, self._component._layer_size)
        ):
            return False

        # validate path (for non-autorouted channels)
        if "_path" in route_info.keys():
            if len(route_info["_path"]) != len(cached_info["_path"]):
                return False
            for a, b in zip(route_info["_path"], cached_info["_path"]):
                if a != b:
                    return False

        route_info["_path"] = cached_info["_path"]

        self._route(name, route_info, loaded=True)
        return True

    def _validate_keepouts(self, polychannel: "Shape"):
        """
        Checks if the polychannel does not violate any keepouts.

        Parameters:

        - polychannel: The PolychannelShape instance representing the channel path.

        Returns:

        - True if the polychannel does not violate any keepouts, otherwise False.
        """

        # check autoroute keepouts
        violation = False
        if polychannel._keepouts:
            margin = (-1, -1, -1)
            boxes = [
                self._add_margin(tuple(float(x) for x in keepout), margin)
                for keepout in polychannel._keepouts
            ]
            mins = np.array([box[:3] for box in boxes], dtype=np.float64)
            maxs = np.array([box[3:] for box in boxes], dtype=np.float64)
            try:
                _, counts = self._keepout_index.intersection_v(mins, maxs)
            except TypeError:
                # sometimes intersection_v fails when boxes are outside spactial extent
                # fall back to intersection
                counts = []
                for box in boxes:
                    ret = list(self._keepout_index.intersection(box))
                    counts.append(len(ret))
                counts = np.array(counts, dtype=np.int64)
            violation = np.any(counts > 0)

        return not violation

    def _route(self, name: str, route_info: dict, loaded: bool = False):
        """
        Routes a channel based on the provided route information.
        
        Parameters:

        - name: The name of the route to be created.
        - route_info: A dictionary containing the route information, including input and output ports, path, and other parameters.
        - loaded: A boolean indicating whether the route is being loaded from cache (default is False).
        
        Returns:

        - True if the route was successfully created, otherwise False.
        """
        # create polychannel
        polychannel_shapes = deepcopy(route_info["_path"])
        
        # check if size is odd and translation is on 0.5 (+-eps). If so, decrease translation by 0.5
        prev_size = None
        prev_position = None
        for shape in polychannel_shapes:
            size = shape._size if shape._size is not None else prev_size
            position = shape._position if shape._position is not None else prev_position
            for i in range(3):
                if size[i] % 2 == 1:
                    if _is_integer(position[i]*2):
                        shape._no_validation = True
            prev_size = shape._size if shape._size is not None else prev_size
            prev_position = shape._position if shape._position is not None else prev_position

        polychannel = Polychannel(polychannel_shapes)

        # validate keepouts if autoroute
        if not self._validate_keepouts(polychannel):
            if route_info["route_type"] == "autoroute":
                if not self._quiet:
                    print(f"\r\n\t\t\t⚠️ Autoroute failed for {name}!")
                return False
            else:
                if not self._quiet:
                    print(f"\r\n\t\t\t⚠️ {name} violates keepouts!")

        # add polychannel keepout
        if not loaded:
            self._add_keepouts_from_polychannel(name, polychannel)

        # add path to component
        self._component.add_void(name, polychannel, label=route_info["label"])
        if not route_info["input"].get_name().startswith("None_"):
            route_info["input"]._parent.connect_port(route_info["input"].get_name())
        if not route_info["output"].get_name().startswith("None_"):
            route_info["output"]._parent.connect_port(route_info["output"].get_name())
        return True

    def _add_keepouts_from_polychannel(self, name: str, polychannel: Polychannel):
        """
        Adds keepouts from a Polychannel instance to the router's keepout index.
        
        Parameters:

        - name: The name of the polychannel to be added.
        - polychannel: The Polychannel instance from which to extract keepouts.
        
        Returns:

        - None
        """

        for j, keepout in enumerate(polychannel._keepouts):
            ko_key = f"{name}_{j}"
            ko = self._add_margin(tuple(float(x) for x in keepout), self._channel_margin)
            ko = tuple(round(x) for x in ko)
            self._keepout_index.insert(len(self.routed_keepouts.keys()), ko)
            if "__to__" in name:
                split_name = name.split("__to__")
                if split_name[0] not in self.keepouts_by_port:
                    self.keepouts_by_port[split_name[0]] = []
                if split_name[1] not in self.keepouts_by_port:
                    self.keepouts_by_port[split_name[1]] = []
                self.keepouts_by_port[split_name[0]].append(ko_key)
                self.keepouts_by_port[split_name[1]].append(ko_key)
            self.routed_keepouts[ko_key] = (len(self.routed_keepouts.keys()), ko)

    def _cache_routes(self):
        """
        Caches the route information to a file.
        
        Parameters:

        - name: The name of the route to be cached.
        - route_info: A dictionary containing the route information to be cached.

        Returns:

        - True if the route was successfully cached, otherwise False.
        """
        instantiation_dir = self._component.instantiation_dir
        file_stem = self._component.instantiating_file_stem
        from .. import Component, Device, VariableLayerThicknessComponent, StitchedDevice
        if type(self._component) in (Component, Device, VariableLayerThicknessComponent, StitchedDevice):
            if self._component._name is not None:
                file_name = self._component._name
            else:
                file_name = type(self._component).__name__
        else:
            file_name = type(self._component).__name__
        cache_file = (
            instantiation_dir
            / f"{file_stem}_cache"
            / f"{file_name}.pkl"
        )

        save_routes = {}
        for name, route_info in self._routes.items():
            if route_info is not None and "_path" in route_info.keys():
                save_dict = {
                    "route_type": route_info["route_type"],
                    "input": route_info["input"].get_origin(
                        self._component._px_size, self._component._layer_size
                    ),
                    "output": route_info["output"].get_origin(
                        self._component._px_size, self._component._layer_size
                    ),
                    "_path": route_info["_path"],
                }
                save_routes[name] = save_dict
        # combine nonrouted and routed keepouts
        keepouts = {
            **self.nonrouted_keepouts,
            **self.routed_keepouts,
        }
        if len(save_routes) > 0:
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            with open(cache_file, "wb") as f:
                pickle.dump((keepouts, save_routes), f)
            return True
        return False

    def _remove_port_keepouts(self, input_port: "Port", output_port: "Port"):
        """
        Removes the keepouts associated with the input and output ports.
        
        Parameters:

        - input_port: The Port instance where the channel starts.
        - output_port: The Port instance where the channel ends.
        
        Returns:

        - None
        """
        input_port_name = input_port.get_name()
        output_port_name = output_port.get_name()

        # remove port keepouts
        removed_keepouts = {}
        for keepout_key in self.keepouts_by_port.get(
            input_port_name, []
        ) + self.keepouts_by_port.get(output_port_name, []):
            if keepout_key not in removed_keepouts:
                keepout_idx, keepout_box = self.routed_keepouts[keepout_key]
                removed_keepouts[keepout_key] = (keepout_idx, keepout_box)
                self._keepout_index.delete(keepout_idx, keepout_box)

        return removed_keepouts

    def _add_port_keepouts(self, removed_keepouts: dict):
        """
        Adds back the keepouts that were removed for the input and output ports.
        
        Parameters:

        - removed_keepouts: A dictionary containing the keepouts that were removed.
        
        Returns:

        - None
        """
        for keepout_key, val in removed_keepouts.items():
            keepout_idx, keepout_box = val
            self._keepout_index.insert(keepout_idx, keepout_box)

    def _autoroute(self, name: str, route_info: dict):
        """
        Automatically routes a channel using the A* algorithm.
        
        Parameters:

        - name: The name of the route to be created.
        - route_info: A dictionary containing the route information, including input and output ports, timeout, heuristic weight, and turn weight.
        
        Returns:

        - None
        """
        input_port = route_info["input"]
        output_port = route_info["output"]

        # A*
        violation = False
        path = self._a_star_3d(
            input_port,
            output_port,
            timeout=route_info["timeout"],
            heuristic_weight=route_info["heuristic_weight"],
            turn_weight=route_info["turn_weight"],
            direction_preference=route_info["direction_preference"],
        )
        if path is None:
            violation = True
        elif len(path) < 2:
            violation = True

        if violation:
            if not self._quiet:
                print(f"\r\n\t\t\t⚠️ Error: failed to route {name}")
            return

        # path to constant cross-section polychannel shapes
        polychannel_shapes = self._path_to_polychannel_shapes(
            input_port, output_port, path
        )
        route_info["_path"] = polychannel_shapes

        # add route to component
        self._route(name, route_info)

    def _a_star_3d(
        self,
        input_port,
        output_port,
        timeout=120,
        heuristic_weight=10,
        turn_weight=2,
        direction_preference=("X", "Y", "Z"),
    ):
        """
        Implements the A* algorithm for 3D routing between two ports.
        
        Parameters:

        - input_port: The Port instance where the channel starts.
        - output_port: The Port instance where the channel ends.
        - timeout: The maximum time allowed for the routing operation (in seconds).
        - heuristic_weight: Weighting factor for the heuristic in the A* algorithm.
        - turn_weight: Weighting factor for the number of turns in the A* algorithm.
        
        Returns:

        - A list of tuples representing the path from the input port to the output port if a valid path is found, otherwise None.
        """
        start_time = time.time()

        # Check if ports can be routed
        pos = list(
            input_port.get_position(self._component._px_size, self._component._layer_size)
        )
        pos = [round(x) for x in pos]
        pos_box = self._get_box_from_pos_and_size(pos, self._channel_size)
        if not self._is_bbox_inside(
            self._add_margin(pos_box, self._channel_margin),
            self._component.get_bounding_box(
                self._component._px_size, self._component._layer_size
            ),
            exclude_axis=input_port.to_vector(),
        ):
            if not self._quiet:
                print("\r\n\t\t\t⚠️ Input port cannot be routed with given router.")
            return None

        pos = list(
            output_port.get_position(
                self._component._px_size, self._component._layer_size
            )
        )
        pos = [round(x) for x in pos]
        pos_box = self._get_box_from_pos_and_size(pos, self._channel_size)
        if not self._is_bbox_inside(
            self._add_margin(pos_box, self._channel_margin),
            self._component.get_bounding_box(
                self._component._px_size, self._component._layer_size
            ),
            exclude_axis=output_port.to_vector(),
        ):
            if not self._quiet:
                print("\r\n\t\t\t⚠️ Output port cannot be routed with given router.")
            return None

        # Get start and goal positions
        start = self._move_outside_port(input_port)
        goal = self._move_outside_port(output_port)

        # Validate start and goal positions
        start_valid, goal_valid = self._is_valid_points([start, goal])
        if not start_valid:
            if not self._quiet:
                print("\r\n\t\t\t⚠️ Input port is blocked or invalid")
            return None
        if not goal_valid:
            if not self._quiet:
                print("\r\n\t\t\t⚠️ Output port is blocked or invalid")
            return None

        directions = []
        for axis in direction_preference:
            if axis == "X":
                directions.extend([(1, 0, 0), (-1, 0, 0)])
            elif axis == "Y":
                directions.extend([(0, 1, 0), (0, -1, 0)])
            elif axis == "Z":
                directions.extend([(0, 0, 1), (0, 0, -1)])

        open_heap = []
        start_node = _AutorouterNode(
            start,
            cost=0,
            turns=0,
            direction=None,
            heuristic=self._heuristic(start, goal),
            heuristic_weight=heuristic_weight,
            turn_weight=turn_weight,
        )
        heapq.heappush(open_heap, start_node)
        visited = {}

        while open_heap:
            if time.time() - start_time > timeout:
                if not self._quiet:
                    print("\r\n\t\t\t⚠️ Channel routing timed out")
                return None
            current = heapq.heappop(open_heap)

            # Create dynamic directions ordering based on distance to goal
            st = start
            ep = goal

            sorted_directions = []
            if abs(st[0] - ep[0]) >= abs(st[1] - ep[1]):
                sorted_directions.extend([(1, 0, 0), (-1, 0, 0)])
                sorted_directions.extend([(0, 1, 0), (0, -1, 0)])
            else:
                sorted_directions.extend([(0, 1, 0), (0, -1, 0)])
                sorted_directions.extend([(1, 0, 0), (-1, 0, 0)])
            if abs(st[2] - ep[2]) >= abs(st[0] - ep[0]) and abs(st[2] - ep[2]) >= abs(
                st[1] - ep[1]
            ):
                sorted_directions.insert(0, (0, 0, 1))
                sorted_directions.insert(1, (0, 0, -1))
            elif abs(st[0] - ep[0]) >= abs(st[2] - ep[2]) and abs(st[1] - ep[1]) >= abs(
                st[2] - ep[2]
            ):
                sorted_directions.extend([(0, 0, 1), (0, 0, -1)])
            else:
                sorted_directions.insert(2, (0, 0, 1))
                sorted_directions.insert(3, (0, 0, -1))

            if current._pos == goal:
                path = self._reconstruct_path(current)
                path = self._simplify_cardinal_path(path)

                return path

            if current._pos in visited and visited[current._pos] <= (
                current._cost,
                current._turns,
            ):
                continue
            visited[current._pos] = (current._cost, current._turns)

            # Generate all neighbor positions
            neighbor_positions = [
                tuple(current._pos[i] + d[i] for i in range(3)) for d in directions
            ]

            # Batch filter valid neighbor positions
            valid_mask = self._is_valid_points(
                neighbor_positions
            )  # Expects list -> list[bool]

            for d, neighbor_pos, is_valid in zip(
                directions, neighbor_positions, valid_mask
            ):
                if not is_valid:
                    continue

                is_turn = current._direction is not None and current._direction != d
                turn_count = current._turns + int(is_turn)
                move_cost = current._cost + 1

                neighbor_node = _AutorouterNode(
                    neighbor_pos,
                    parent=current,
                    cost=move_cost,
                    turns=turn_count,
                    direction=d,
                    heuristic=self._heuristic(neighbor_pos, goal),
                    heuristic_weight=heuristic_weight,
                    turn_weight=turn_weight,
                )
                heapq.heappush(open_heap, neighbor_node)

        return None  # No path found

    def _move_outside_port(self, port: "Port"):
        """
        Moves the port position outside its bounding box in the direction of its vector.
        
        Parameters:

        - port: The Port instance to be moved outside its bounding box.
        
        Returns:

        - A tuple representing the new position of the port outside its bounding box.
        """
        pos = list(
            port.get_position(self._component._px_size, self._component._layer_size)
        )
        pos = [round(x) for x in pos]

        if port.get_name().startswith("None_"):
            # flip vector if port belong to component
            direction = port.to_vector()
            direction = tuple(-d for d in direction)
        else:
            direction = port.to_vector()

        pos_box = self._get_box_from_pos_and_size(pos, self._channel_size)

        if port.get_name().startswith("None_"):
            while not self._is_bbox_inside(
                self._add_margin(pos_box, self._channel_margin),
                self._component.get_bounding_box(
                    self._component._px_size, self._component._layer_size
                ),
            ):
                pos = list(pos[i] + direction[i] for i in range(3))
                pos_box = self._get_box_from_pos_and_size(pos, self._channel_size)
        else:
            while self._intersects_with_bbox(
                pos_box,
                port._parent.get_bounding_box(
                    self._component._px_size, self._component._layer_size
                ),
            ):
                pos = list(pos[i] + direction[i] for i in range(3))
                pos_box = self._get_box_from_pos_and_size(pos, self._channel_size)
        return tuple(pos)

    def _get_box_from_pos_and_size(self, pos, size):
        """
        Creates a bounding box from a position and size.
        
        Parameters:

        - pos: A tuple representing the position in 3D space (x, y, z).
        - size: A tuple representing the size of the bounding box (width, height, depth).
        
        Returns:

        - A tuple representing the bounding box in 3D space (x0, y0, z0, x1, y1, z1).
        """
        return (
            pos[0],
            pos[1],
            pos[2],
            pos[0] + size[0],
            pos[1] + size[1],
            pos[2] + size[2],
        )

    def _intersects_with_bbox(self, box1, box2):
        """
        Checks if two bounding boxes intersect.
        
        Parameters:

        - box1: The first bounding box (tuple of 6 floats).
        - box2: The second bounding box (tuple of 6 floats).
        
        Returns:

        - True if the bounding boxes intersect, otherwise False.
        """
        x0a, y0a, z0a, x1a, y1a, z1a = box1
        x0b, y0b, z0b, x1b, y1b, z1b = box2
        return not (
            x1a <= x0b
            or x1b <= x0a
            or y1a <= y0b
            or y1b <= y0a
            or z1a <= z0b
            or z1b <= z0a
        )

    def _heuristic(self, a, b):
        """
        Heuristic function for A* algorithm.
        
        Parameters:

        - a: The first point in 3D space (tuple of 3 floats).
        - b: The second point in 3D space (tuple of 3 floats).
        
        Returns:

        - The heuristic cost between the two points.
        """
        return sum(abs(a[i] - b[i]) for i in range(3))  # Manhattan

    def _reconstruct_path(self, node):
        """
        Reconstructs the path from the end node to the start node.
        
        Parameters:

        - node: The end node in the A* search tree.
        
        Returns:

        - A list of tuples representing the path from the start node to the end node.
        """
        path = []
        while node:
            path.append(node._pos)
            node = node._parent
        return path[::-1]

    def _simplify_cardinal_path(self, points):
        """
        Simplifies a path by removing unnecessary points while keeping cardinal directions.
        
        Parameters:

        - points: A list of tuples representing the path segments (each tuple contains three floats).
        
        Returns:

        - A simplified list of tuples representing the path segments.
        """
        # Remove any duplicate entries
        tmp = [points[0]]
        for point in points[1:]:
            if point != tmp[-1]:
                tmp.append(point)
        points = tmp

        # Keep only cardinal points
        if len(points) <= 2:
            return points[:]

        simplified = [points[0], points[1]]
        dx, dy, dz = tuple(ai - bi for ai, bi in zip(simplified[-1], simplified[-2]))

        for i, p in enumerate(points):
            if i < 2:
                continue

            ndx, ndy, ndz = tuple(ai - bi for ai, bi in zip(p, simplified[-1]))
            if (ndx, ndy, ndz) != (dx, dy, dz):
                # Direction changed, keep current point
                simplified.append(p)
                dx, dy, dz = ndx, ndy, ndz
            else:
                simplified.pop()
                simplified.append(p)
        return simplified

    def _is_valid_points(self, points, alt_margins=None):
        """
        Checks if a point is valid for routing.
        
        Parameters:

        - point: A tuple representing the point in 3D space (x, y, z).
        
        Returns:

        - True if the point is valid for routing, otherwise False.
        """

        boxes = [self._get_box_from_pos_and_size(p, self._channel_size) for p in points]
        if alt_margins is not None:
            margin_boxes = [self._add_margin(b, alt_margins) for b in boxes]
        else:
            margin_boxes = [self._add_margin(b, self._channel_margin) for b in boxes]
        inside_mask = [self._is_bbox_inside(b, self._bounds) for b in margin_boxes]

        margin = (-1, -1, -1)
        shrunk_boxes = [
            self._add_margin(b, margin) for b, valid in zip(boxes, inside_mask) if valid
        ]

        if len(shrunk_boxes) > 0:
            mins = np.array([box[:3] for box in shrunk_boxes], dtype=np.float64)
            maxs = np.array([box[3:] for box in shrunk_boxes], dtype=np.float64)
            try:
                _, counts = self._keepout_index.intersection_v(mins, maxs)
            except TypeError:
                # sometimes intersection_v fails when boxes are outside spactial extent
                # fall back to intersection
                counts = []
                for box in shrunk_boxes:
                    ret = list(self._keepout_index.intersection(box))
                    counts.append(len(ret))
        else:
            counts = []

        result = []
        count_idx = 0
        for valid in inside_mask:
            if not valid:
                result.append(False)
            else:
                result.append(counts[count_idx] == 0)
                count_idx += 1
        return result

    def _is_bbox_inside(self, bbox_inner, bbox_outer, exclude_axis=None):
        """
        Checks if one bounding box is completely inside another.
        
        Parameters:
        
        - bbox_inner: The inner bounding box (tuple of 6 floats).
        - bbox_outer: The outer bounding box (tuple of 6 floats).
        
        Returns:

        - True if the inner bounding box is completely inside the outer bounding box, otherwise False.
        """
        x0i, y0i, z0i, x1i, y1i, z1i = bbox_inner
        x0o, y0o, z0o, x1o, y1o, z1o = bbox_outer
        if exclude_axis is not None:
            # find axis which is not 0
            axis = exclude_axis.index(next(filter(lambda v: v != 0, exclude_axis)))
            if axis == 0:
                return y0o <= y0i and y1i <= y1o and z0o <= z0i and z1i <= z1o
            elif axis == 1:
                return x0o <= x0i and x1i <= x1o and z0o <= z0i and z1i <= z1o
            elif axis == 2:
                return x0o <= x0i and x1i <= x1o and y0o <= y0i and y1i <= y1o
        return (
            x0o <= x0i
            and x1i <= x1o
            and y0o <= y0i
            and y1i <= y1o
            and z0o <= z0i
            and z1i <= z1o
        )
