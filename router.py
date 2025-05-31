import heapq
import time
from functools import cache
from microfluidic_designer import Port, get_backend

import pickle
import os
import hashlib

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

def polychannel(component, shapes:list[PolychannelShape], nettype="default"):
    shape_list = []
    last_shape = None
    for shape in shapes:
        if shape.shape_type == "cube":
            cube = component.make_cube(shape.size, center=False, nettype=nettype)
            cube.rotate(shape.rotation)
            if shape.absolute_position or last_shape is None:
                cube.translate(shape.position)
            else:
                cube.translate(tuple(shape.position[i] + last_shape.position[i] for i in range(3)))
            shape_list.append(cube)

        elif shape.shape_type == "sphr":
            sphere = component.make_sphere(
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

class Node:
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

def get_box_from_pos_and_size(pos, size):
    return (
        pos[0], pos[1], pos[2],
        pos[0] + size[0],
        pos[1] + size[1],
        pos[2] + size[2],
    )

def move_outside_port(port: Port, chan_size):
    pos = list(port.position)
    direction = port.pointing_vector_to_vector()

    # Extend the bounding box of the port to include its margin
    port_bbox = port.get_bounding_box()

    pos_box = get_box_from_pos_and_size(pos, chan_size)

    while intersects_with_bbox(pos_box, port.parent.get_bounding_box()):
        pos = list(pos[i] + direction[i] for i in range(3))
        pos_box = get_box_from_pos_and_size(pos, chan_size)
    return tuple(pos)

def heuristic(a, b):
    return sum(abs(a[i] - b[i]) for i in range(3))  # Manhattan

def add_margin(bbox, margin):
    (x0, y0, z0, x1, y1, z1) = bbox
    mx, my, mz = margin
    return (x0 - mx, y0 - my, z0 - mz, x1 + mx, y1 + my, z1 + mz)

def intersects_with_bbox(box1, box2):
    x0a, y0a, z0a, x1a, y1a, z1a = box1
    x0b, y0b, z0b, x1b, y1b, z1b = box2
    return not (x1a <= x0b or x1b <= x0a or
                y1a <= y0b or y1b <= y0a or
                z1a <= z0b or z1b <= z0a)

def is_bbox_inside(bbox_inner, bbox_outer):
    x0i, y0i, z0i, x1i, y1i, z1i = bbox_inner
    x0o, y0o, z0o, x1o, y1o, z1o = bbox_outer
    return (
        x0o <= x0i and x1i <= x1o and
        y0o <= y0i and y1i <= y1o and
        z0o <= z0i and z1i <= z1o
    )

def is_valid_point(point, bounds, component_keepouts, keepouts, chan_size, chan_margin):
    pos_box = get_box_from_pos_and_size(point, chan_size)

    tmp = []

    for ko in component_keepouts:
        if intersects_with_bbox(pos_box, ko):
            return False
        tmp.append(ko)

    pos_box = add_margin(pos_box, chan_margin)

    for ko in keepouts:
        if intersects_with_bbox(pos_box, ko):
            return False
        tmp.append(add_margin(ko, chan_margin))
            
    if not is_bbox_inside(pos_box, bounds):
        return False
    # print(tmp)
    # print()
    return True

def reconstruct_path(node):
    path = []
    while node:
        path.append(node.pos)
        node = node.parent
    return path[::-1]

def simplify_cardinal_path(points):
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

def a_star_3d(input_port, output_port, channel_size, channel_margin, bounds, component_keepouts, keepouts):
    start_time = time.time()
    start = move_outside_port(input_port, channel_size)
    goal = move_outside_port(output_port, channel_size)

    directions = [
        (1, 0, 0), (-1, 0, 0),
        (0, 1, 0), (0, -1, 0),
        (0, 0, 1), (0, 0, -1)
    ]

    open_heap = []
    start_node = Node(start, cost=0, turns=0, direction=None, heuristic=heuristic(start, goal))
    heapq.heappush(open_heap, start_node)
    visited = {}

    while open_heap:
        if time.time() - start_time > timeout:
            print("Channel routing timed out")
            return None
        current = heapq.heappop(open_heap)

        if current.pos == goal:
            path = reconstruct_path(current)
            path = simplify_cardinal_path(path)

            return path

        if current.pos in visited and visited[current.pos] <= (current.cost, current.turns):
            continue
        visited[current.pos] = (current.cost, current.turns)

        for d in directions:
            neighbor_pos = tuple(current.pos[i] + d[i] for i in range(3))
            if not is_valid_point(neighbor_pos, bounds, component_keepouts, keepouts, channel_size, channel_margin):
                continue

            is_turn = (current.direction is not None and current.direction != d)
            turn_count = current.turns + int(is_turn)
            move_cost = current.cost + 1

            neighbor_node = Node(
                neighbor_pos,
                parent=current,
                cost=move_cost,
                turns=turn_count,
                direction=d,
                heuristic=heuristic(neighbor_pos, goal)
            )
            heapq.heappush(open_heap, neighbor_node)

    return None  # No path found

# def cache_path(func_name, *args, **kwargs):
#     # Create a hash of the arguments
#     # print("Cache path")
#     key_data = (args, kwargs)
#     # print(key_data)
#     # print(pickle.dumps(key_data))
#     key = hashlib.md5(pickle.dumps(key_data)).hexdigest()
#     # print(key)
#     return f"cache/cache_{func_name}_{key}.pkl"

def cache_a_star(func_name, in_p, out_p):
    # Create a hash of the arguments
    # print("Cache path")
    # print(key_data)
    # print(pickle.dumps(key_data))
    # print(key)
    return f"cache/cache_{func_name}_{in_p}_{out_p}.pkl"

def load_or_compute_a_star(input_port, output_port, channel_size, channel_margin, bounds, component_keepouts, keepouts):
    # print("Make cache name")
    # cache_file = cache_path("a_star_3d", input_port.position, output_port.position, channel_size, channel_margin, bounds, component_keepouts, keepouts)
    cache_file = cache_a_star("a_star_3d", f"{input_port.parent.name}_{input_port.name}", f"{output_port.parent.name}_{output_port.name}")

    # print("Check if cache exists")
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            # print("Loading cached result...")
            return pickle.load(f)

    # Compute and cache the result
    # print("Computing a_star_3d...")
    result = a_star_3d(input_port, output_port, channel_size, channel_margin, bounds, component_keepouts, keepouts)

    if result is not None:
        with open(cache_file, 'wb') as f:
            pickle.dump(result, f)

    return result

def autoroute_channel(component, input_port, output_port, channel_size, channel_margin, nettype="default"):

    bounds = component.get_bounding_box()
    keepouts = [] # will stay channel margin away from
    component_keepouts = [] # will not stay channel margin away from

    for subcomponent in component.subcomponents:
        component_keepouts.append(subcomponent.get_bounding_box())
        for port in subcomponent.ports:
            if port != input_port and port != output_port:
                keepouts.append(port.get_bounding_box())
    for shape in component.model:
        for keepout in shape.keepouts:
            keepouts.append(tuple(float(x) for x in keepout))

    path = load_or_compute_a_star(
        input_port, output_port, channel_size, channel_margin, bounds, component_keepouts, keepouts
    )

    # Make polychannel path
    if len(path) < 2:
        return None

    polychannel_path = [
        PolychannelShape("cube", input_port.size, input_port.get_adjusted_position(), absolute_position=True)
    ]
    for point in path[1:-1]:
        polychannel_path.append(PolychannelShape("cube", channel_size, point, absolute_position=True))
    polychannel_path.append(PolychannelShape("cube", output_port.size, output_port.get_adjusted_position(), absolute_position=True))

    return polychannel(component, polychannel_path, nettype=nettype)