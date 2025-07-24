from __future__ import annotations

import os
import time
import heapq
import pickle
import numpy as np
from rtree import index
from typing import Union
from copy import deepcopy

from .. import PolychannelShape, BezierCurveShape


class _AutorouterNode:
    """
    ###### A node in the A* search algorithm for 3D routing.
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
        ###### Parameters:
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
        ###### Less than comparison for priority queue sorting.
        ###### Compares the total cost (cost + heuristic + turns) of two nodes.
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
    ###### A class for routing channels in a 3D component using various methods.
    This class provides methods for autorouting, manual routing with polychannels,
    and routing with fractional paths. It also manages keepouts and bounding boxes
    for the component and its subcomponents.
    """

    def __init__(
        self,
        component: "Component",
        channel_size: tuple[int, int, int] = (0, 0, 0),
        channel_margin: tuple[int, int, int] = (0, 0, 0),
    ):
        """
        ###### Initializes the Router with a component and channel specifications.
        ###### Parameters:
        - component: The Component instance to route channels within.
        - channel_size: The size of the channels to be routed (tuple of 3 ints).
        - channel_margin: The margin to apply around the channels (tuple of 3 ints).
        """
        self._routes = {}
        self._component = component
        self._channel_size = channel_size
        self._channel_margin = channel_margin
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
        ###### Adds a margin to a bounding box.
        ###### Parameters:
        - bbox: The bounding box to which the margin will be added (tuple of 6 floats).
        - margin: The margin to add to each side of the bounding box (tuple of 3 floats).
        ###### Returns:
        - A new bounding box with the margin applied (tuple of 6 floats).
        """
        (x0, y0, z0, x1, y1, z1) = bbox
        mx, my, mz = margin
        return (x0 - mx, y0 - my, z0 - mz, x1 + mx, y1 + my, z1 + mz)

    def autoroute_channel(
        self,
        input_port: "Port",
        output_port: "Port",
        label: str,
        timeout: int = 120,
        heuristic_weight: int = 10,
        turn_weight: int = 2,
    ):
        """
        ###### Automatically routes a channel between two ports using A* algorithm.
        ###### Parameters:
        - input_port: The Port instance where the channel starts.
        - output_port: The Port instance where the channel ends.
        - label: A label for the routed channel.
        - timeout: The maximum time allowed for the routing operation (in seconds).
        - heuristic_weight: Weighting factor for the heuristic in the A* algorithm.
        - turn_weight: Weighting factor for the number of turns in the A* algorithm.
        ###### Raises:
        - ValueError: If either port has not been added to the component before routing.
        """
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
        }

    def route_with_polychannel(
        self,
        input_port: "Port",
        output_port: "Port",
        polychannel_shapes: list[Union[PolychannelShape, BezierCurveShape]],
        label: str,
    ):
        """
        ###### Routes a channel between two ports using a specified polychannel path.
        ###### Parameters:
        - input_port: The Port instance where the channel starts.
        - output_port: The Port instance where the channel ends.
        - polychannel_shapes: A list of PolychannelShape or BezierCurveShape instances defining the channel path.
        - label: A label for the routed channel.
        ###### Raises:
        - ValueError: If either port has not been added to the component before routing.
        """
        if input_port._parent is None:
            raise ValueError("Port must be added to component before routing! (input)")
        if output_port._parent is None:
            raise ValueError("Port must be added to component before routing! (output)")

        name = f"{input_port.get_name()}__to__{output_port.get_name()}"

        input_size = input_port.get_size(
            self._component._px_size, self._component._layer_size
        )
        input_pos = tuple(
            np.array(
                input_port.get_origin(
                    self._component._px_size, self._component._layer_size
                )
            )
            + np.array(input_size) / 2
        )
        polychannel_shapes.insert(
            0,
            PolychannelShape(
                "cube",
                position=input_pos,
                size=input_size,
                absolute_position=True,
            ),
        )
        output_size = output_port.get_size(
            self._component._px_size, self._component._layer_size
        )
        output_pos = tuple(
            np.array(
                output_port.get_origin(
                    self._component._px_size, self._component._layer_size
                )
            )
            + np.array(output_size) / 2
        )
        polychannel_shapes.append(
            PolychannelShape(
                "cube",
                position=output_pos,
                size=output_size,
                absolute_position=True,
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
        input_port: "Port",
        output_port: "Port",
        route: list[tuple[float, float, float]],
        label: str,
    ):
        """
        ###### Routes a channel between two ports using a fractional path.
        ###### Parameters:
        - input_port: The Port instance where the channel starts.
        - output_port: The Port instance where the channel ends.
        - route: A list of tuples representing the fractional path segments (each tuple contains three floats) the sum of each digit must add to 1.0.
        - label: A label for the routed channel.
        ###### Raises:
        - ValueError: If either port has not been added to the component before routing.
        """
        if input_port._parent is None:
            raise ValueError("Port must be added to component before routing! (input)")
        if output_port._parent is None:
            raise ValueError("Port must be added to component before routing! (output)")

        name = f"{input_port.get_name()}__to__{output_port.get_name()}"

        # get locations
        start_loc = input_port.get_position(
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
            input_port, output_port, path
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
        ###### Converts a path defined by a list of points into a list of PolychannelShape instances.
        ###### Parameters:
        - input_port: The Port instance where the channel starts.
        - output_port: The Port instance where the channel ends.
        - path: A list of tuples representing the path segments (each tuple contains three floats).
        ###### Returns:
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
        polychannel_shapes.append(
            PolychannelShape(
                "cube",
                position=tuple(input_pos),
                size=input_size,
                absolute_position=True,
            )
        )

        # Handle middle path segments
        for point in path[1:-1]:
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
        polychannel_shapes.append(
            PolychannelShape(
                "cube",
                position=tuple(output_pos),
                size=output_size,
                absolute_position=True,
            )
        )

        return polychannel_shapes

    def route(self):
        """
        ###### Routes all defined channels in the component.
        This method checks for cached routes, loads them if valid, and reroutes if necessary.
        It handles both manual routing with polychannels and autorouting using the A* algorithm.
        """
        print("Routing...")
        keepouts, self.cached_routes = self._load_cached_route()
        self._generate_keepout_index(keepouts)
        new_routes = []
        loaded_routes = []
        print("\r\tLoading cached routes...", end="", flush=True)
        for i, (name, route_info) in enumerate(
            self._routes.items()
        ):  # Route cached paths if valid
            input_port = route_info["input"]
            output_port = route_info["output"]
            print(
                f"\r\tLoading cached routes ({(i+1)/len(self._routes)*100:.2f}%)...",
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
                    print(f"\r\n\t\tRerouting {name}...")
            self._add_port_keepouts(removed_keepouts)
            new_routes.append((name, route_info))  # Cache is stale/missing → reroute

        # Add keepouts for cached routes
        self._generate_keepout_index()
        for name in loaded_routes:
            self._add_keepouts_from_polychannel(name, self._component.shapes[name])

        print(f"\r\n\tManual Routing...", end="", flush=True)
        for i, (name, route_info) in enumerate(new_routes):
            input_port = route_info["input"]
            output_port = route_info["output"]
            print(
                f"\r\tManual Routing ({(i+1)/len(new_routes)*100:.2f}%)...",
                end="",
                flush=True,
            )
            if route_info["route_type"] != "autoroute":  # Manual routing
                removed_keepouts = self._remove_port_keepouts(input_port, output_port)
                self._route(name, route_info)
                self._add_port_keepouts(removed_keepouts)

        print(f"\r\n\tAutorouting...", end="", flush=True)
        for i, (name, route_info) in enumerate(new_routes):  # Autoroute paths
            input_port = route_info["input"]
            output_port = route_info["output"]
            print(
                f"\r\tAutorouting ({(i+1)/len(new_routes)*100:.2f}%)...",
                end="",
                flush=True,
            )
            if route_info["route_type"] == "autoroute":  # Manual routing
                removed_keepouts = self._remove_port_keepouts(input_port, output_port)
                self._autoroute(name, route_info)
                self._add_port_keepouts(removed_keepouts)
        print()
        self._cache_routes()

    def _load_cached_route(self):
        """
        ###### Loads a cached route from a file.
        ###### Parameters:
        - name: The name of the route to load.
        ###### Returns:
        - A dictionary containing the cached route information if it exists, otherwise None.
        """
        instantiation_dir = self._component.instantiation_dir
        file_stem = self._component.instantiating_file_stem
        cache_file = (
            instantiation_dir
            / f"{file_stem}_cache"
            / f"{type(self._component).__name__}.pkl"
        )

        if os.path.exists(cache_file):
            with open(cache_file, "rb") as f:
                return pickle.load(f)
        return None, None

    def _load_route(self, name: str, route_info: dict, cached_info: dict):
        """
        ###### Validates and loads a route from cached information.
        ###### Parameters:
        - name: The name of the route to load.
        - route_info: A dictionary containing the route information to validate.
        - cached_info: A dictionary containing the cached route information.
        ###### Returns:
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
        ###### Checks if the polychannel does not violate any keepouts.
        ###### Parameters:
        - polychannel: The PolychannelShape instance representing the channel path.
        ###### Returns:
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
        ###### Routes a channel based on the provided route information.
        ###### Parameters:
        - name: The name of the route to be created.
        - route_info: A dictionary containing the route information, including input and output ports, path, and other parameters.
        - loaded: A boolean indicating whether the route is being loaded from cache (default is False).
        ###### Returns:
        - True if the route was successfully created, otherwise False.
        """
        # create polychannel
        polychannel_shapes = deepcopy(route_info["_path"])
        polychannel = self._component.make_polychannel(polychannel_shapes)

        # validate keepouts if autoroute
        if not self._validate_keepouts(polychannel):
            if route_info["route_type"] == "autoroute":
                return False
            else:
                print(f"\r\n\t\t⚠️ {name} violates keepouts!")

        # add polychannel keepout
        if not loaded:
            self._add_keepouts_from_polychannel(name, polychannel)

        # add path to component
        self._component.add_shape(name, polychannel, label=route_info["label"])
        return True

    def _add_keepouts_from_polychannel(self, name: str, polychannel: PolychannelShape):
        """
        ###### Adds keepouts from a PolychannelShape instance to the router's keepout index.
        ###### Parameters:
        - name: The name of the polychannel shape to be added.
        - polychannel: The PolychannelShape instance from which to extract keepouts.
        ###### Returns:
        - None
        """

        for j, keepout in enumerate(polychannel._keepouts):
            ko_key = f"{name}_{j}"
            ko = self._add_margin(tuple(float(x) for x in keepout), self._channel_margin)
            ko = tuple(round(x) for x in ko)
            self._keepout_index.insert(len(self.routed_keepouts.keys()), ko)
            if "__to__" in name:
                split_name = name.split("__to__")
                self.keepouts_by_port[split_name[0]].append(ko_key)
                self.keepouts_by_port[split_name[1]].append(ko_key)
            self.routed_keepouts[ko_key] = (len(self.routed_keepouts.keys()), ko)

    def _cache_routes(self):
        """
        ###### Caches the route information to a file.
        ###### Parameters:
        - name: The name of the route to be cached.
        - route_info: A dictionary containing the route information to be cached.
        ###### Returns:
        - True if the route was successfully cached, otherwise False.
        """
        instantiation_dir = self._component.instantiation_dir
        file_stem = self._component.instantiating_file_stem
        cache_file = (
            instantiation_dir
            / f"{file_stem}_cache"
            / f"{type(self._component).__name__}.pkl"
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
        ###### Removes the keepouts associated with the input and output ports.
        ###### Parameters:
        - input_port: The Port instance where the channel starts.
        - output_port: The Port instance where the channel ends.
        ###### Returns:
        - None
        """
        input_port_name = input_port.get_name()
        output_port_name = output_port.get_name()

        # remove port keepouts
        removed_keepouts = {}
        for keepout_key in (
            self.keepouts_by_port[input_port_name]
            + self.keepouts_by_port[output_port_name]
        ):
            if keepout_key not in removed_keepouts:
                keepout_idx, keepout_box = self.routed_keepouts[keepout_key]
                removed_keepouts[keepout_key] = (keepout_idx, keepout_box)
                self._keepout_index.delete(keepout_idx, keepout_box)

        return removed_keepouts

    def _add_port_keepouts(self, removed_keepouts: dict):
        """
        ###### Adds back the keepouts that were removed for the input and output ports.
        ###### Parameters:
        - removed_keepouts: A dictionary containing the keepouts that were removed.
        ###### Returns:
        - None
        """
        for keepout_key, val in removed_keepouts.items():
            keepout_idx, keepout_box = val
            self._keepout_index.insert(keepout_idx, keepout_box)

    def _autoroute(self, name: str, route_info: dict):
        """
        ###### Automatically routes a channel using the A* algorithm.
        ###### Parameters:
        - name: The name of the route to be created.
        - route_info: A dictionary containing the route information, including input and output ports, timeout, heuristic weight, and turn weight.
        ###### Returns:
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
        )
        if path is None:
            violation = True
        elif len(path) < 2:
            violation = True

        if violation:
            print(f"\r\n\t\tError: failed to route {name}")
            return

        # path to constant cross-section polychannel shapes
        polychannel_shapes = self._path_to_polychannel_shapes(
            input_port, output_port, path
        )
        route_info["_path"] = polychannel_shapes

        # add route to component
        self._route(name, route_info)

    def _a_star_3d(
        self, input_port, output_port, timeout=120, heuristic_weight=10, turn_weight=2
    ):
        """
        ###### Implements the A* algorithm for 3D routing between two ports.
        ###### Parameters:
        - input_port: The Port instance where the channel starts.
        - output_port: The Port instance where the channel ends.
        - timeout: The maximum time allowed for the routing operation (in seconds).
        - heuristic_weight: Weighting factor for the heuristic in the A* algorithm.
        - turn_weight: Weighting factor for the number of turns in the A* algorithm.
        ###### Returns:
        - A list of tuples representing the path from the input port to the output port if a valid path is found, otherwise None.
        """
        start_time = time.time()

        start = self._move_outside_port(input_port)
        goal = self._move_outside_port(output_port)

        start_valid, goal_valid = self._is_valid_points([start, goal])
        if not start_valid:
            print("\r\n\t\tInput port is blocked or invalid")
            return None
        if not goal_valid:
            print("\r\n\t\tOutput port is blocked or invalid")
            return None

        directions = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]

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
                print("\r\n\t\tChannel routing timed out")
                return None
            current = heapq.heappop(open_heap)

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
        ###### Moves the port position outside its bounding box in the direction of its vector.
        ###### Parameters:
        - port: The Port instance to be moved outside its bounding box.
        ###### Returns:
        - A tuple representing the new position of the port outside its bounding box.
        """
        pos = list(
            port.get_position(self._component._px_size, self._component._layer_size)
        )
        pos = [round(x) for x in pos]
        direction = port.to_vector()

        pos_box = self._get_box_from_pos_and_size(pos, self._channel_size)

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
        ###### Creates a bounding box from a position and size.
        ###### Parameters:
        - pos: A tuple representing the position in 3D space (x, y, z).
        - size: A tuple representing the size of the bounding box (width, height, depth).
        ###### Returns:
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
        ###### Checks if two bounding boxes intersect.
        ###### Parameters:
        - box1: The first bounding box (tuple of 6 floats).
        - box2: The second bounding box (tuple of 6 floats).
        ###### Returns:
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
        ###### Heuristic function for A* algorithm.
        ###### Parameters:
        - a: The first point in 3D space (tuple of 3 floats).
        - b: The second point in 3D space (tuple of 3 floats).
        ###### Returns:
        - The heuristic cost between the two points.
        """
        return sum(abs(a[i] - b[i]) for i in range(3))  # Manhattan

    def _reconstruct_path(self, node):
        """
        ###### Reconstructs the path from the end node to the start node.
        ###### Parameters:
        - node: The end node in the A* search tree.
        ###### Returns:
        - A list of tuples representing the path from the start node to the end node.
        """
        path = []
        while node:
            path.append(node._pos)
            node = node._parent
        return path[::-1]

    def _simplify_cardinal_path(self, points):
        """
        ###### Simplifies a path by removing unnecessary points while keeping cardinal directions.
        ###### Parameters:
        - points: A list of tuples representing the path segments (each tuple contains three floats).
        ###### Returns:
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

    def _is_valid_points(self, points):
        """
        ###### Checks if a point is valid for routing.
        ###### Parameters:
        - point: A tuple representing the point in 3D space (x, y, z).
        ###### Returns:
        - True if the point is valid for routing, otherwise False.
        """

        boxes = [self._get_box_from_pos_and_size(p, self._channel_size) for p in points]
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

    def _is_bbox_inside(self, bbox_inner, bbox_outer):
        """
        ###### Checks if one bounding box is completely inside another.
        ###### Parameters:
        - bbox_inner: The inner bounding box (tuple of 6 floats).
        - bbox_outer: The outer bounding box (tuple of 6 floats).
        ###### Returns:
        - True if the inner bounding box is completely inside the outer bounding box, otherwise False.
        """
        x0i, y0i, z0i, x1i, y1i, z1i = bbox_inner
        x0o, y0o, z0o, x1o, y1o, z1o = bbox_outer
        return (
            x0o <= x0i
            and x1i <= x1o
            and y0o <= y0i
            and y1i <= y1o
            and z0o <= z0i
            and z1i <= z1o
        )
