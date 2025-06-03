from __future__ import annotations

import os
import sys
import time
import heapq
import pickle
import importlib
from rtree import index
from pathlib import Path
from microfluidic_designer import Port


heuristic_weight = 10
turn_weight = 2
timeout = 120 # per channel in seconds


# # Blend shape
# r = shape/2;
# translate(position) rotate(a=a, v=v)  scale(size) hull(){
#     translate([-0.5+r,-0.5+r,-0.5+r]) sphere(d=r*2);
#     translate([-0.5+r,-0.5+r,0.5-r]) sphere(d=r*2);
#     translate([-0.5+r,0.5-r,-0.5+r]) sphere(d=r*2);
#     translate([-0.5+r,0.5-r,0.5-r]) sphere(d=r*2);
#     translate([0.5-r,-0.5+r,-0.5+r]) sphere(d=r*2);
#     translate([0.5-r,-0.5+r,0.5-r]) sphere(d=r*2);
#     translate([0.5-r,0.5-r,-0.5+r]) sphere(d=r*2);
#     translate([0.5-r,0.5-r,0.5-r]) sphere(d=r*2);
# }

class PolychannelShape:
        def __init__(self, shape_type, size, position, rotation=(0, 0, 0), absolute_position=False):
            self.shape_type = shape_type  # e.g., "cube", "cylinder"
            self.size = size  # e.g., (width, height, depth)
            self.position = position  # e.g., (x, y, z)
            self.rotation = rotation  # e.g., (rx, ry, rz) in degrees
            self.absolute_position = absolute_position

class AutorouterNode:
        def __init__(self, pos, parent=None, cost=0, turns=0, direction=None, heuristic=0):
            self.pos = pos
            self.parent = parent
            self.cost = cost
            self.turns = turns
            self.direction = direction
            self.heuristic = heuristic

        def __lt__(self, other):
            return (self.cost + heuristic_weight * self.heuristic + turn_weight * self.turns) < \
                (other.cost + heuristic_weight * other.heuristic + turn_weight * other.turns)


class Router:
    def __init__(self, component:Component, channel_size:tuple[int, int, int]=(0,0,0), channel_margin:tuple[int, int, int]=(0,0,0)):
        self.component = component
        self.channel_size = channel_size
        self.channel_margin = channel_margin
        self.bounds = self.component.get_bounding_box()
        self.routes = {}
        self.keepouts = {}

        p = index.Property()
        p.dimension = 3  # because you're working in 3D
        idx = index.Index(properties=p)

        cnt = 0
        for subcomponent in self.component.subcomponents:
            # add subcomponet keepout
            key = subcomponent.name
            ko = subcomponent.get_bounding_box()
            self.keepouts[key] = (cnt, ko)
            idx.insert(cnt, ko)
            cnt += 1

            # add port keepout
            for port in subcomponent.ports:
                key = port.get_port_name()
                ko = (self._add_margin(port.get_bounding_box(), self.channel_margin))
                self.keepouts[key] = (cnt, ko)
                idx.insert(cnt, ko)
                cnt += 1

        # add shape keepout
        for i, shape in enumerate(self.component.model):
            for j, keepout in enumerate(shape.keepouts):
                key = f"{i}_{j}"
                if shape.name is not None:
                    key = f"{shape.name}_{j}"
                ko = (self._add_margin(tuple(float(x) for x in keepout), self.channel_margin))
                self.keepouts[key] = (cnt, ko)
                idx.insert(cnt, ko)
                cnt += 1

        self.keepout_index = idx


    def polychannel(self, shapes:list[PolychannelShape], nettype="default"):
        shape_list = []
        last_shape = None
        for shape in shapes:
            if shape.shape_type == "cube":
                cube = self.component.make_cube(shape.size, center=False, nettype=nettype)
                cube.rotate(shape.rotation)
                if shape.absolute_position or last_shape is None:
                    cube.translate(shape.position)
                else:
                    cube.translate(tuple(shape.position[i] + last_shape.position[i] for i in range(3)))
                shape_list.append(cube)

            elif shape.shape_type == "sphr":
                sphere = self.component.make_sphere(
                    radius=1, center=False, nettype=nettype
                )
                sphere.resize(shape.size)
                sphere.rotate(shape.rotation)
                if shape.absolute_position or last_shape is None:
                    sphere.translate(shape.position)
                else:
                    sphere.translate(tuple(shape.position[i] + last_shape.position[i] for i in range(3)))
                shape_list.append(sphere)

            else:
                raise ValueError(f"Unsupported shape type: {shape.shape_type}")

            last_shape = shape

        # Hull shapes pairwise
        if len(shape_list) > 1:
            path = shape_list[0].hull(shape_list[1])
            last_shape = shape_list[1]
            for shape in shape_list[2:]:
                path += last_shape.hull(shape)
                last_shape = shape
            return path
        else:
            return None

    def _get_box_from_pos_and_size(self, pos, size):
        return (
            pos[0], pos[1], pos[2],
            pos[0] + size[0],
            pos[1] + size[1],
            pos[2] + size[2],
        )

    def _move_outside_port(self, port: Port):
        pos = list(port.position)
        direction = port.pointing_vector_to_vector()

        # Extend the bounding box of the port to include its margin
        port_bbox = port.get_bounding_box()

        pos_box = self._get_box_from_pos_and_size(pos, self.channel_size)

        while self._intersects_with_bbox(pos_box, port.parent.get_bounding_box()):
            pos = list(pos[i] + direction[i] for i in range(3))
            pos_box = self._get_box_from_pos_and_size(pos, self.channel_size)
        return tuple(pos)

    def _heuristic(self, a, b):
        return sum(abs(a[i] - b[i]) for i in range(3))  # Manhattan

    def _add_margin(self, bbox, margin):
        (x0, y0, z0, x1, y1, z1) = bbox
        mx, my, mz = margin
        return (x0 - mx, y0 - my, z0 - mz, x1 + mx, y1 + my, z1 + mz)

    def _intersects_with_bbox(self, box1, box2):
        x0a, y0a, z0a, x1a, y1a, z1a = box1
        x0b, y0b, z0b, x1b, y1b, z1b = box2
        return not (x1a <= x0b or x1b <= x0a or
                    y1a <= y0b or y1b <= y0a or
                    z1a <= z0b or z1b <= z0a)

    def _is_bbox_inside(self, bbox_inner, bbox_outer):
        x0i, y0i, z0i, x1i, y1i, z1i = bbox_inner
        x0o, y0o, z0o, x1o, y1o, z1o = bbox_outer
        return (
            x0o <= x0i and x1i <= x1o and
            y0o <= y0i and y1i <= y1o and
            z0o <= z0i and z1i <= z1o
        )


    def _is_valid_point(self, point):
        pos_box = self._get_box_from_pos_and_size(point, self.channel_size)

        if not self._is_bbox_inside(self._add_margin(pos_box, self.channel_margin), self.bounds):
            return False

        # Check global keepouts using Rtree
        x0, y0, z0, x1, y1, z1 = pos_box
        pos_box = (x0+1, y0+1, z0+1, x1-1, y1-1, z1-1)
        hits = list(self.keepout_index.intersection(pos_box))
        if hits:
            return False
        
        return True

    def _reconstruct_path(self, node):
        path = []
        while node:
            path.append(node.pos)
            node = node.parent
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

    def _a_star_3d(self, input_port, output_port):
        start_time = time.time()

        start = self._move_outside_port(input_port)
        goal = self._move_outside_port(output_port)

        directions = [
            (1, 0, 0), (-1, 0, 0),
            (0, 1, 0), (0, -1, 0),
            (0, 0, 1), (0, 0, -1)
        ]

        open_heap = []
        start_node = AutorouterNode(start, cost=0, turns=0, direction=None, heuristic=self._heuristic(start, goal))
        heapq.heappush(open_heap, start_node)
        visited = {}

        while open_heap:
            if time.time() - start_time > timeout:
                print("Channel routing timed out")
                return None
            current = heapq.heappop(open_heap)

            if current.pos == goal:
                path = self._reconstruct_path(current)
                path = self._simplify_cardinal_path(path)

                return path

            if current.pos in visited and visited[current.pos] <= (current.cost, current.turns):
                continue
            visited[current.pos] = (current.cost, current.turns)

            for d in directions:
                neighbor_pos = tuple(current.pos[i] + d[i] for i in range(3))
                if not self._is_valid_point(neighbor_pos):
                    continue

                is_turn = (current.direction is not None and current.direction != d)
                turn_count = current.turns + int(is_turn)
                move_cost = current.cost + 1

                neighbor_node = AutorouterNode(
                    neighbor_pos,
                    parent=current,
                    cost=move_cost,
                    turns=turn_count,
                    direction=d,
                    heuristic=self._heuristic(neighbor_pos, goal)
                )
                heapq.heappush(open_heap, neighbor_node)

        return None  # No path found

    def _get_instantiation_info(self):
        """Return (directory, filename_stem) of the file that instantiated the component, if it's a Device or Component."""
        class_name = type(self.component).__name__

        if class_name in {'Device', 'Component'}:
            return self.component.instantiation_dir, self.component.instantiating_file_stem

        # Fallback: use where the class is defined
        module_name = self.component.__class__.__module__
        module = sys.modules.get(module_name) or importlib.import_module(module_name)
        path = Path(module.__file__).resolve()
        return path.parent, path.stem
    
    def _load_or_compute_a_star(self, input_port, output_port):
        # Get base path and file name
        instantiation_dir, file_stem = self._get_instantiation_info()

        # Build cache directory path: <instantiator>/<ClassName>_cache/
        cache_dir = instantiation_dir / f"{file_stem}_cache" / type(self.component).__name__

        # Final cache file path
        cache_file = cache_dir / f"{input_port.get_port_name()}__to__{output_port.get_port_name()}.pkl"

        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as f:
                return pickle.load(f)

        # Compute and cache the result
        removed_keepouts = {}
        for keepout_key, (keepout_idx, keepout_box) in self.keepouts.items():
            if input_port.get_port_name() in keepout_key or output_port.get_port_name() in keepout_key:
                removed_keepouts[keepout_idx] = keepout_box
                self.keepout_index.delete(keepout_idx, keepout_box)
                
        result = self._a_star_3d(input_port, output_port)

        for keepout_idx, keepout_box in removed_keepouts.items():
            self.keepout_index.insert(keepout_idx, keepout_box)

        if result is not None:
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            with open(cache_file, 'wb') as f:
                pickle.dump(result, f)

        return result

    def autoroute_channel(self, input_port, output_port, nettype="default"):

        if input_port.parent is None:
            raise ValueError("Port must be added to component before routing! (input)")
        if output_port.parent is None:
            raise ValueError("Port must be added to component before routing! (output)")

        name = f"{input_port.get_port_name()}__to__{output_port.get_port_name()}"

        self.routes[name] = {
            "Route Type": "autoroute",
            "Input": input_port,
            "Output": output_port,
            "Nettype": nettype
        }

    def route(self):
        for name, val in self.routes.items():
            if val["Route Type"] == "autoroute":
                path = self._load_or_compute_a_star(val["Input"], val["Output"])

            # Make polychannel path
            if len(path) < 2:
                return None

            polychannel_path = [
                PolychannelShape("cube", val["Input"].size, val["Input"].get_adjusted_position(), absolute_position=True)
            ]
            for point in path[1:-1]:
                polychannel_path.append(PolychannelShape("cube", self.channel_size, point, absolute_position=True))
            polychannel_path.append(PolychannelShape("cube", val["Output"].size, val["Output"].get_adjusted_position(), absolute_position=True))

            polychannel = self.polychannel(polychannel_path, nettype=val["Nettype"])
            polychannel.name = name

            # add polychannel keepout
            for j, keepout in enumerate(polychannel.keepouts):
                ko_key = f"{name}_{j}"
                ko = (self._add_margin(tuple(float(x) for x in keepout), self.channel_margin))
                self.keepouts[ko_key] = (len(self.keepouts.keys()), ko)
                self.keepout_index.insert(len(self.keepouts.keys()), ko)

            self.component.add_shape(polychannel)