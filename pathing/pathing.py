################################# Plotting Code #################################
import matplotlib.pyplot as plt
import itertools

def visualize_paths(paths, keepouts=None, path_keepouts=None):
    """
    Visualize multiple 3D paths and optional keepout zones.

    Parameters:
    - paths: list of paths, where each path is a list of (x, y, z) points
    - keepouts: list of (xmin, ymin, zmin, xmax, ymax, zmax) boxes
    """
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    colors = itertools.cycle(['blue', 'orange', 'purple', 'cyan', 'magenta', 'lime', 'brown', 'pink'])
    
    for i, path in enumerate(paths):
        color = next(colors)
        xs, ys, zs = zip(*path)
        ax.set_aspect('equal', adjustable='box')
        ax.plot(xs, ys, zs, marker='o', color=color, label=f'Path {i + 1}')
        ax.scatter(xs[0], ys[0], zs[0], color='green', s=100, label=f'Start {i + 1}')
        ax.scatter(xs[-1], ys[-1], zs[-1], color='red', s=100, label=f'End {i + 1}')

    # Plot keepouts
    if keepouts:
        for box in keepouts:
            min, max = box
            draw_keepout(ax, min, max, path=False)
    if path_keepouts:
        for box in path_keepouts:
            min, max = box
            draw_keepout(ax, min, max, path=True)

    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.legend()
    plt.tight_layout()
    plt.show()

def draw_keepout(ax, min, max, path=True):
    """
    Draw a wireframe box representing a keepout region.
    """
    xmin, ymin, zmin = min
    xmax, ymax, zmax = max

    # Vertices of a cuboid
    corners = [
        (xmin, ymin, zmin), (xmax, ymin, zmin), (xmax, ymax, zmin), (xmin, ymax, zmin),
        (xmin, ymin, zmax), (xmax, ymin, zmax), (xmax, ymax, zmax), (xmin, ymax, zmax)
    ]

    # 12 edges connecting the corners
    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7)
    ]

    for i, j in edges:
        x = [corners[i][0], corners[j][0]]
        y = [corners[i][1], corners[j][1]]
        z = [corners[i][2], corners[j][2]]
        if path:
            ax.plot(x, y, z, color='gray', linestyle='--')
        else:
            ax.plot(x, y, z, color='red', linestyle='--')


################################# Pathing Code #################################
import math
import heapq
import numpy as np

heuristic_weight = 100
turn_weight = 2

class Node:
    def __init__(self, pos, parent=None, cost=0, turns=0, direction=None):
        self.pos = pos
        self.parent = parent
        self.cost = cost
        self.turns = turns
        self.direction = direction

    def __lt__(self, other):
        return (self.cost + heuristic_weight*self.heuristic) < (other.cost + heuristic_weight*other.heuristic)
    
def round_half_down(n):
    if n > 0:
        return math.ceil(n - 0.5)
    else:
        return math.floor(n + 0.5)

def quantize(point, xy_step, z_step):
    x, y, z = point
    return (
        round_half_down(x / xy_step) * xy_step,
        round_half_down(y / xy_step) * xy_step,
        round_half_down(z / z_step) * z_step
    )

def is_in_keepouts(pos, shape, keepouts):
    x, y, z = pos
    dx, dy, dz = shape
    half_dx_n, half_dy_n, half_dz_n = dx // 2, dy // 2, dz // 2
    half_dx_p, half_dy_p, half_dz_p = dx // 2, dy // 2, dz // 2

    if dx%2 == 1:
        half_dx_p += 1

    if dy%2 == 1:
        half_dy_p += 1

    if dz%2 == 1:
        half_dz_p += 1
        
    for box in keepouts:
        min, max = box
        x0, y0, z0 = min
        x1, y1, z1 = max
        
        if x0-half_dx_n <= x <= x1+half_dx_p and y0-half_dy_n <= y <= y1+half_dy_p and z0-half_dz_n <= z <= z1+half_dz_p:
            return True
    return False


def is_in_endpoint_keepout(pos, shape, start, end, pointing_vector_start, pointing_vector_end):
    def matches_except_pointing(pos, ref, pointing_vector, pointing_away):
        axis = next(i for i, v in enumerate(pointing_vector) if v != 0)
        # All other dims must match exactly
        for i in range(3):
            if i != axis and pos[i] != ref[i]:
                return False

        if pointing_vector[axis] > 0:
            sign_check = (pos[axis] >= ref[axis])
        else:
            sign_check = (pos[axis] <= ref[axis])

        # Flip sign check if vector points towards ref (not away)
        if not pointing_away:
            sign_check = not sign_check

        return sign_check

    start_keepout = (
        (start[0]-shape[0], start[1]-shape[1], start[2]-shape[2]),
        (start[0]+shape[0], start[1]+shape[1], start[2]+shape[2])
    )
    if is_in_keepouts(pos, shape, [start_keepout]) and matches_except_pointing(pos, start, pointing_vector_start, pointing_away=True):
        return True

    end_keepout = (
        (end[0]-shape[0], end[1]-shape[1], end[2]-shape[2]),
        (end[0]+shape[0], end[1]+shape[1], end[2]+shape[2])
    )
    if is_in_keepouts(pos, shape, [end_keepout]) and matches_except_pointing(pos, end, pointing_vector_end, pointing_away=False):
        return True

    return False

def get_neighbors(bounds, pos, xy_step, z_step):
    min, max = bounds
    x_min, y_min, z_min = min
    x_max, y_max, z_max = max
    x, y, z = pos
    directions = [
        (xy_step, 0, 0), (-xy_step, 0, 0),
        (0, xy_step, 0), (0, -xy_step, 0),
        (0, 0, z_step), (0, 0, -z_step),
    ]

    neighbors = []
    for dx, dy, dz in directions:
        nx, ny, nz = x + dx, y + dy, z + dz
        if x_min <= nx <= x_max and y_min <= ny <= y_max and z_min <= nz <= z_max:
            neighbors.append((nx, ny, nz))
    return neighbors

def direction_change(prev_dir, new_dir):
    if prev_dir is None:
        return False
    return not np.allclose(prev_dir, new_dir)

def normalize(v):
    return v / np.linalg.norm(v)

def compute_heuristic(p1, p2):
    return np.linalg.norm(np.array(p1) - np.array(p2))

def generate_initial_path_by_path_size(start, pointing_vector, path_size, xy_step, z_step, invert = False):
    # Determine dominant direction
    vec = np.array(pointing_vector)
    dominant_axis = np.argmax(np.abs(vec))
    min_dist = path_size[dominant_axis]//2  # Get width/height/depth based on axis
    direction = normalize(vec)
    
    if invert:
        if path_size[dominant_axis]%2 == 1:
            min_dist += 1
        step_vector = direction * min_dist
        new_point = tuple(np.array(start) - step_vector)
    else:
        step_vector = direction * min_dist
        new_point = tuple(np.array(start) + step_vector)
    return quantize(new_point, xy_step, z_step)
    # return new_point

def path_from_node(node):
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

def weighted_a_star_3d(bounds, start, end, pointing_vector_start, pointing_vector_end,
              xy_step, z_step, keepouts, path_size):

    start = quantize(start, xy_step, z_step)
    end = quantize(end, xy_step, z_step)

    # Generate second and second-last points
    pre_start = generate_initial_path_by_path_size(start, pointing_vector_start, path_size, xy_step, z_step)
    pre_end = generate_initial_path_by_path_size(end, pointing_vector_end, path_size, xy_step, z_step, invert=True)

    open_set = []
    visited = set()

    root = Node(pre_start, parent=Node(start), cost=0, turns=0, direction=None)
    root.heuristic = compute_heuristic(pre_start, pre_end)
    heapq.heappush(open_set, root)

    while open_set:
        current = heapq.heappop(open_set)

        if current.pos == pre_end:
            final_node = Node(end, parent=Node(pre_end, parent=current), cost=current.cost, turns=current.turns)
            return simplify_cardinal_path(path_from_node(final_node))

        if current.pos in visited:
            continue
        visited.add(current.pos)

        for neighbor in get_neighbors(bounds, current.pos, xy_step, z_step):
            if neighbor in visited or (is_in_keepouts(neighbor, path_size, keepouts) and not is_in_endpoint_keepout(neighbor, path_size, start, end, pointing_vector_start, pointing_vector_end)):
                continue

            move_vector = tuple(np.array(neighbor) - np.array(current.pos))
            move_direction = normalize(np.array(move_vector)) if np.linalg.norm(move_vector) > 0 else None

            turn_penalty = turn_weight if direction_change(current.direction, move_direction) else 0
            cost = current.cost + np.linalg.norm(np.array(move_vector))
            turns = current.turns + turn_penalty

            node = Node(neighbor, parent=current, cost=cost, turns=turns, direction=move_direction)
            node.heuristic = compute_heuristic(neighbor, pre_end) + turns * xy_step  # weight turns
            heapq.heappush(open_set, node)

    return None  # No path found

def path_ports(bounds, path_size, xy_step, z_step, keepouts, start, end):
    if start.type != "output":
        print("Pathing error: Starting port must be type \"input\"!")
        return None
    if end.type != "input":
        print("Pathing error: Ending port must be type \"output\"!")
        return None

    start_dominant_axis = np.argmax(np.abs(np.array(start.pointing_vector)))
    end_dominant_axis = np.argmax(np.abs(np.array(end.pointing_vector)))
    start_shape = start.shape[:start_dominant_axis] + (0,) + start.shape[start_dominant_axis:]
    end_shape = end.shape[:end_dominant_axis] + (0,) + end.shape[end_dominant_axis:]

    if start_shape[0] != 0 and end_shape[0] != 0 and start_shape[0] != end_shape[0]:
        print("Pathing error: Starting and ending shapes must have the same x dimension.")
    if start_shape[1] != 0 and end_shape[1] != 0 and start_shape[1] != end_shape[1]:
        print("Pathing error: Starting and ending shapes must have the same y dimension.")
    if start_shape[2] != 0 and end_shape[2] != 0 and start_shape[2] != end_shape[2]:
        print("Pathing error: Starting and ending shapes must have the same z dimension.")
    
    if start_dominant_axis != end_dominant_axis:
        shape = tuple(max(ai, bi) for ai, bi in zip(start_shape, end_shape))
    else:
        if start_dominant_axis == 2:
            # we don't have any z information (we will match the smallest x/y)
            size = min(start_shape[0], start_shape[1])
            size = math.ceil(size/z_step)*z_step
            shape = (start_shape[0], start_shape[1], size)
        else:
            if start_dominant_axis == 0:
                shape = (start_shape[1], start_shape[1], start_shape[2])
            if start_dominant_axis == 1:
                shape = (start_shape[0], start_shape[0], start_shape[2])

    print(shape)
    return weighted_a_star_3d(bounds, start.position, end.position, start.pointing_vector, end.pointing_vector, xy_step, z_step, keepouts, path_size)


################################# Generate path keepouts #################################
def get_keepout_boxes_from_paths(shape, paths):
    dx, dy, dz = shape
    half_dx, half_dy, half_dz = dx // 2, dy // 2, dz // 2
    
    boxes = []

    for path in paths:
        for p1, p2 in zip(path[:-1], path[1:]):
            # Get mins and maxes of both points with shape
            x1_min, y1_min, z1_min = p1[0] - half_dx, p1[1] - half_dy, p1[2] - half_dz
            x1_max, y1_max, z1_max = p1[0] + half_dx, p1[1] + half_dy, p1[2] + half_dz

            x2_min, y2_min, z2_min = p2[0] - half_dx, p2[1] - half_dy, p2[2] - half_dz
            x2_max, y2_max, z2_max = p2[0] + half_dx, p2[1] + half_dy, p2[2] + half_dz

            if dx%2 == 1:
                x1_max += 1
                x2_max += 1

            if dy%2 == 1:
                y1_max += 1
                y2_max += 1

            if dz%2 == 1:
                z1_max += 1
                z2_max += 1

            # Combine into one bounding box
            x_min, y_min, z_min = min(x1_min, x2_min), min(y1_min, y2_min), min(z1_min, z2_min)
            x_max, y_max, z_max = max(x1_max, x2_max), max(y1_max, y2_max), max(z1_max, z2_max)

            boxes.append(((x_min, y_min, z_min), (x_max, y_max, z_max)))
    return boxes