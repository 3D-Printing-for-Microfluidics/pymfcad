from __future__ import annotations

import os
import sys
import time
import heapq
import pickle
import importlib
import numpy as np
from rtree import index
from pathlib import Path
from typing import Union
from copy import deepcopy

from .. import PolychannelShape, BezierCurveShape, Port, Component
from ..backend import Shape


class AutorouterNode:
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
        self._pos = pos
        self._parent = parent
        self._cost = cost
        self._turns = turns
        self._direction = direction
        self._heuristic = heuristic
        self._heuristic_weight = heuristic_weight
        self._turn_weight = turn_weight

    def __lt__(self, other):
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
    def __init__(
        self,
        component: Component,
        channel_size: tuple[int, int, int] = (0, 0, 0),
        channel_margin: tuple[int, int, int] = (0, 0, 0),
    ):
        self._routes = {}
        self._component = component
        self._channel_size = channel_size
        self._channel_margin = channel_margin
        self._bounds = self._component.get_bounding_box()
        self._keepouts = {}

        p = index.Property()
        p.dimension = 3  # because you're working in 3D
        idx = index.Index(properties=p)

        cnt = 0
        for subcomponent in self._component.subcomponents:
            # add subcomponet keepout
            key = subcomponent._name
            ko = subcomponent.get_bounding_box()
            idx.insert(cnt, ko)
            self._keepouts[key] = (cnt, ko)
            cnt += 1

            # add port keepout
            for port in subcomponent.ports:
                key = port.get_name()
                ko = self._add_margin(port.get_bounding_box(), self._channel_margin)
                idx.insert(cnt, ko)
                self._keepouts[key] = (cnt, ko)
                cnt += 1

        # add shape keepout
        for i, shape in enumerate(self._component.shapes):
            for j, keepout in enumerate(shape._keepouts):
                key = f"{i}_{j}"
                if shape._name is not None:
                    key = f"{shape._name}_{j}"
                ko = self._add_margin(
                    tuple(float(x) for x in keepout), self._channel_margin
                )
                idx.insert(cnt, ko)
                self._keepouts[key] = (cnt, ko)
                cnt += 1

        self._keepout_index = idx

    def _add_margin(self, bbox, margin):
        (x0, y0, z0, x1, y1, z1) = bbox
        mx, my, mz = margin
        return (x0 - mx, y0 - my, z0 - mz, x1 + mx, y1 + my, z1 + mz)

    def autoroute_channel(
        self,
        input_port: Port,
        output_port: Port,
        label: str,
        timeout: int = 120,
        heuristic_weight: int = 10,
        turn_weight: int = 2,
    ):
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
        input_port: Port,
        output_port: Port,
        polychannel_shapes: list[Union[PolychannelShape, BezierCurveShape]],
        label: str,
    ):
        if input_port._parent is None:
            raise ValueError("Port must be added to component before routing! (input)")
        if output_port._parent is None:
            raise ValueError("Port must be added to component before routing! (output)")

        name = f"{input_port.get_name()}__to__{output_port.get_name()}"

        polychannel_shapes.insert(
            0,
            PolychannelShape(
                "cube",
                position=input_port.get_origin(),
                size=input_port._size,
                absolute_position=True,
            ),
        )
        polychannel_shapes.append(
            PolychannelShape(
                "cube",
                position=output_port.get_origin(),
                size=output_port._size,
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
        input_port: Port,
        output_port: Port,
        route: list[tuple[float, float, float]],
        label: str,
    ):
        if input_port._parent is None:
            raise ValueError("Port must be added to component before routing! (input)")
        if output_port._parent is None:
            raise ValueError("Port must be added to component before routing! (output)")

        name = f"{input_port.get_name()}__to__{output_port.get_name()}"

        # get locations
        start_loc = input_port._position
        end_loc = output_port._position
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
        polychannel_shapes = []

        # Handle input port
        input_pos = np.array(input_port.get_origin()) + np.array(input_port._size) / 2
        polychannel_shapes.append(
            PolychannelShape(
                "cube",
                position=tuple(input_pos),
                size=input_port._size,
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
        output_pos = np.array(output_port.get_origin()) + np.array(output_port._size) / 2
        polychannel_shapes.append(
            PolychannelShape(
                "cube",
                position=tuple(output_pos),
                size=output_port._size,
                absolute_position=True,
            )
        )

        return polychannel_shapes

    def route(self):
        print("Routing...")
        new_routes = []
        for name, route_info in self._routes.items():  # Route cached paths if valid
            cached_info = self._load_cached_route(name)
            if cached_info:
                print(f"\tLoading {name}...")
                if self._load_route(name, route_info, cached_info):
                    print(f"\t\t{name} loaded.")
                    continue
                else:
                    print(f"\t\tRerouting {name}...")
            new_routes.append((name, route_info))  # Cache is stale/missing → reroute
        for name, route_info in new_routes:
            if route_info["route_type"] != "autoroute":  # Manual routing
                print(f"\tManual Routing {name}...")
                self._route(name, route_info)
        for name, route_info in new_routes:  # Autoroute paths
            if route_info["route_type"] == "autoroute":  # Manual routing
                print(f"\tAutorouting {name}...")
                self._autoroute(name, route_info)

    def _load_cached_route(self, name: str):
        instantiation_dir = self._component.instantiation_dir
        file_stem = self._component.instantiating_file_stem
        cache_file = (
            instantiation_dir
            / f"{file_stem}_cache"
            / type(self._component).__name__
            / f"{name}.pkl"
        )

        if os.path.exists(cache_file):
            with open(cache_file, "rb") as f:
                return pickle.load(f)
        return None

    def _load_route(self, name: str, route_info: dict, cached_info: dict):
        input_port = route_info["input"]
        output_port = route_info["output"]

        # validate route type
        if route_info["route_type"] != cached_info["route_type"]:
            return False

        # validate input and output locations
        if tuple(cached_info["input"]) != tuple(input_port.get_origin()) or tuple(
            cached_info["output"]
        ) != tuple(output_port.get_origin()):
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

    def _validate_keepouts(self, input_port: Port, output_port: Port, polychannel: Shape):
        # remove port keepouts
        removed_keepouts = {}
        for keepout_key, (keepout_idx, keepout_box) in list(self._keepouts.items()):
            if (
                input_port.get_name() == keepout_key
                or output_port.get_name() == keepout_key
                or (
                    "__to__" in keepout_key
                    and (
                        input_port.get_name() in keepout_key
                        or output_port.get_name() in keepout_key
                    )
                )
            ):
                removed_keepouts[keepout_key] = (keepout_idx, keepout_box)
                self._keepout_index.delete(keepout_idx, keepout_box)
                del self._keepouts[keepout_key]

        # check autoroute keepouts
        violation = False
        for keepout in polychannel._keepouts:
            margin = (-1, -1, -1)
            ko_box = self._add_margin(tuple(float(x) for x in keepout), margin)
            intersecting = list(self._keepout_index.intersection(ko_box))
            if intersecting:
                violation = True

        # add back port keepouts
        for keepout_key, val in removed_keepouts.items():
            keepout_idx, keepout_box = val
            self._keepout_index.insert(keepout_idx, keepout_box)
            self._keepouts[keepout_key] = (keepout_idx, keepout_box)

        return not violation

    def _route(self, name: str, route_info: dict, loaded: bool = False):
        input_port = route_info["input"]
        output_port = route_info["output"]

        # create polychannel
        polychannel_shapes = deepcopy(route_info["_path"])
        polychannel = self._component.make_polychannel(polychannel_shapes)

        # validate keepouts if autoroute
        if not self._validate_keepouts(input_port, output_port, polychannel):
            if route_info["route_type"] == "autoroute":
                return False
            else:
                print(f"\t\t⚠️ {name} violates keepouts!")

        # cache results
        if not loaded:
            ret = self._cache_route(name, route_info)
            if not ret:
                print(f"⚠️ failed to cache route {name}")

        # add polychannel keepout
        for j, keepout in enumerate(polychannel._keepouts):
            ko_key = f"{name}_{j}"
            ko = self._add_margin(tuple(float(x) for x in keepout), self._channel_margin)
            ko = tuple(int(x) for x in ko)
            self._keepout_index.insert(len(self._keepouts.keys()), ko)
            self._keepouts[ko_key] = (len(self._keepouts.keys()), ko)

        # add path to component
        self._component.add_shape(name, polychannel, label=route_info["label"])
        return True

    def _cache_route(self, name: str, route_info: dict):
        instantiation_dir = self._component.instantiation_dir
        file_stem = self._component.instantiating_file_stem
        cache_file = (
            instantiation_dir
            / f"{file_stem}_cache"
            / type(self._component).__name__
            / f"{name}.pkl"
        )

        if route_info is not None:
            save_dict = {
                "route_type": route_info["route_type"],
                "input": route_info["input"].get_origin(),
                "output": route_info["output"].get_origin(),
                "_path": route_info["_path"],
            }

            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            with open(cache_file, "wb") as f:
                pickle.dump(save_dict, f)
            return True
        return False

    def _autoroute(self, name: str, route_info: dict):
        input_port = route_info["input"]
        output_port = route_info["output"]

        # remove port keepouts
        removed_keepouts = {}
        for keepout_key, (keepout_idx, keepout_box) in list(self._keepouts.items()):
            if (
                input_port.get_name() == keepout_key
                or output_port.get_name() == keepout_key
                or (
                    "__to__" in keepout_key
                    and (
                        input_port.get_name() in keepout_key
                        or output_port.get_name() in keepout_key
                    )
                )
            ):
                removed_keepouts[keepout_key] = (keepout_idx, keepout_box)
                self._keepout_index.delete(keepout_idx, keepout_box)
                del self._keepouts[keepout_key]

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

        # add back port keepouts
        for keepout_key, val in removed_keepouts.items():
            keepout_idx, keepout_box = val
            self._keepout_index.insert(keepout_idx, keepout_box)
            self._keepouts[keepout_key] = (keepout_idx, keepout_box)

        if violation:
            print(f"\t\tError: failed to route {name}")
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
        start_time = time.time()

        start = self._move_outside_port(input_port)
        goal = self._move_outside_port(output_port)

        directions = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]

        open_heap = []
        start_node = AutorouterNode(
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
                print("Channel routing timed out")
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

            for d in directions:
                neighbor_pos = tuple(current._pos[i] + d[i] for i in range(3))
                if not self._is_valid_point(neighbor_pos):
                    continue

                is_turn = current._direction is not None and current._direction != d
                turn_count = current._turns + int(is_turn)
                move_cost = current._cost + 1

                neighbor_node = AutorouterNode(
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

    def _move_outside_port(self, port: Port):
        pos = list(port._position)
        direction = port.to_vector()

        # Extend the bounding box of the port to include its margin
        port_bbox = port.get_bounding_box()

        pos_box = self._get_box_from_pos_and_size(pos, self._channel_size)

        while self._intersects_with_bbox(pos_box, port._parent.get_bounding_box()):
            pos = list(pos[i] + direction[i] for i in range(3))
            pos_box = self._get_box_from_pos_and_size(pos, self._channel_size)
        return tuple(pos)

    def _get_box_from_pos_and_size(self, pos, size):
        return (
            pos[0],
            pos[1],
            pos[2],
            pos[0] + size[0],
            pos[1] + size[1],
            pos[2] + size[2],
        )

    def _intersects_with_bbox(self, box1, box2):
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
        return sum(abs(a[i] - b[i]) for i in range(3))  # Manhattan

    def _reconstruct_path(self, node):
        path = []
        while node:
            path.append(node._pos)
            node = node._parent
        return path[::-1]

    def _simplify_cardinal_path(self, points):
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

    def _is_valid_point(self, point):
        pos_box = self._get_box_from_pos_and_size(point, self._channel_size)

        if not self._is_bbox_inside(
            self._add_margin(pos_box, self._channel_margin), self._bounds
        ):
            return False

        # Check global keepouts using Rtree
        x0, y0, z0, x1, y1, z1 = pos_box
        pos_box = (x0 + 1, y0 + 1, z0 + 1, x1 - 1, y1 - 1, z1 - 1)
        hits = list(self._keepout_index.intersection(pos_box))
        if hits:
            return False

        return True

    def _is_bbox_inside(self, bbox_inner, bbox_outer):
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
