import trimesh
import numpy as np
from trimesh.scene import Scene
from trimesh.visual import ColorVisuals

from . import Color


def _draw_bounding_box(
    scene: Scene,
    size: tuple[int, int, int],
    origin: tuple[int, int, int],
    color: Color,
    px_size: float,
    layer_size: float,
    name: str = "bbox",
) -> None:
    """Helper function to draw a bounding box in the scene."""
    # draw lines for component bounding box
    bbox_size = (size[0] * px_size, size[1] * px_size, size[2] * layer_size)
    bbox_origin = (origin[0] * px_size, origin[1] * px_size, origin[2] * layer_size)
    translation = trimesh.transformations.translation_matrix(bbox_origin)
    translation[:3, 3] = [o + s / 2 for o, s in zip(bbox_origin, bbox_size)]
    bbox = trimesh.path.creation.box_outline(
        extents=np.array(bbox_size), transform=translation
    )
    bbox.colors = [color._to_rgba()]
    scene.add_geometry(bbox)


def _draw_arrow(
    scene: Scene,
    length: float,
    position: np.typing.NDArray[np.int_],
    direction: np.typing.NDArray[np.int_],
    port: "Port",
    reflect: bool = False,
    half_size: bool = False,
) -> None:
    """Helper function to draw an arrow in the scene."""
    # Align Z axis with arrow direction
    axis = np.array([0, 0, 1])
    if not np.allclose(axis, direction):
        rot = trimesh.geometry.align_vectors(axis, direction)
    else:
        rot = np.eye(4)
    reflect_matrix = (
        trimesh.transformations.reflection_matrix(
            point=[0, 0, length / 2], normal=[0, 0, 1]
        )
        if reflect
        else np.eye(4)
    )
    transform = rot @ reflect_matrix

    arrow = trimesh.creation.cone(
        radius=length * 0.25, height=length, sections=8, transform=transform
    )

    center_offset = np.array([0, 0, 0])
    if half_size:
        if not reflect:
            center_offset = direction * (length)
    else:
        center_offset = direction * (length / 2)

    arrow.apply_translation(position - center_offset)
    arrow.visual.vertex_colors = port.get_color()._to_rgba()
    scene.add_geometry(arrow)


def _draw_port(scene: Scene, port: "Port", component: "Component") -> None:
    """Helper function to draw a port in the scene."""
    arrow_direction = np.array(port.to_vector())
    adjusted_pos = np.array(port.get_origin())

    # Scale to real-world units
    scale = np.array([component._px_size, component._px_size, component._layer_size])
    size_scaled = np.array(port.get_size()) * scale
    pos_scaled = adjusted_pos * scale

    # Center the bounding box
    bbox_center = pos_scaled + size_scaled / 2

    # Draw port bounding box
    _draw_bounding_box(
        scene,
        size=port.get_size(),
        origin=adjusted_pos,
        color=port.get_color(),
        px_size=component._px_size,
        layer_size=component._layer_size,
        name=f"port-{port._name}",
    )

    # Arrow positioning
    arrow_length = np.dot(
        size_scaled, np.abs(arrow_direction)
    )  # length in the pointing direction
    arrow_position = np.array(bbox_center)

    if port._type.name == "INOUT":
        arrow_length = arrow_length / 2
        _draw_arrow(
            scene,
            arrow_length,
            arrow_position,
            arrow_direction,
            port,
            reflect=True,
            half_size=True,
        )
        _draw_arrow(
            scene,
            arrow_length,
            arrow_position,
            arrow_direction,
            port,
            reflect=False,
            half_size=True,
        )

    # IN arrow
    if port._type.name == "IN":
        _draw_arrow(
            scene, arrow_length, arrow_position, arrow_direction, port, reflect=True
        )

    # OUT arrow
    if port._type.name == "OUT":
        _draw_arrow(
            scene, arrow_length, arrow_position, arrow_direction, port, reflect=False
        )


def _manifold3d_shape_to_trimesh(shape: "Shape") -> trimesh.Trimesh:
    """
    ###### Convert a Manifold3D shape to a trimesh object.

    ###### Parameters:
    - shape (Shape): The Manifold3D shape to convert.

    ###### Returns:
    - tm (trimesh.Trimesh): The converted trimesh object.
    """
    m = shape._object.to_mesh()
    tm = trimesh.Trimesh(vertices=m.vert_properties, faces=m.tri_verts)
    rgba = shape._color._to_float()
    tm.visual = ColorVisuals(tm, vertex_colors=[rgba] * len(tm.vertices))
    return tm


def _manifold3d_shape_to_wireframe(shape: "Shape") -> trimesh.Trimesh:
    """
    ###### Convert a Manifold3D shape to a wireframe representation using trimesh.

    ###### Parameters:
    - shape (Shape): The Manifold3D shape to convert.

    ###### Returns:
    - tm (trimesh.Trimesh): The wireframe trimesh object.
    """
    mesh = _manifold3d_shape_to_trimesh(shape)
    edges = mesh.edges_unique
    vertices = mesh.vertices
    entities = [trimesh.path.entities.Line([e[0], e[1]]) for e in edges]
    return trimesh.path.Path3D(entities=entities, vertices=vertices)


def _component_to_manifold(
    component: "Component",
    render_bulk: bool = True,
    do_bulk_difference: bool = True,
) -> tuple[dict[str, "Shape"], dict[str, "Shape"], list[tuple["Port", "Component"]]]:
    """
    ###### Convert a Component to manifolds and bulk shapes for rendering.

    ###### Parameters:
    - component (Component): The Component to convert.
    - render_bulk (bool): Whether to render bulk shapes.
    - do_bulk_difference (bool): Whether to perform a difference operation on bulk shapes.

    ###### Returns:
    - manifolds (dict): Dictionary of manifolds keyed by color.
    - bulk_manifolds (dict): Dictionary of bulk shapes keyed by color.
    - ports (list): List of ports to draw.
    """
    bulk_manifolds = {}
    manifolds = {}
    ports = []

    def recurse(comp: "Component", parent_name: str = ""):
        """
        Recursive function to traverse the component tree and collect shapes and ports.
        """
        name = f"{parent_name}/{comp._name}" if parent_name else comp._name

        # itterate subcomponents
        for sub in comp.subcomponents.values():
            recurse(sub, name)

        # itterate bulk shapes (if device and not inverted)
        for bulk in comp.bulk_shapes.values():
            key = str(bulk._color)
            if key in bulk_manifolds.keys():
                bulk_manifolds[key] += bulk.copy(_internal=True)
            else:
                bulk_manifolds[key] = bulk.copy(_internal=True)

        # itterate shapes (will also draw an inverted device)
        for shape in comp.shapes.values():
            key = str(shape._color)
            if key in manifolds.keys():
                manifolds[key] += shape.copy(_internal=True)
            else:
                manifolds[key] = shape.copy(_internal=True)

        # get list of routes
        route_names = []
        if comp._parent is not None:
            for s in comp._parent.shapes.keys():
                if "__to__" in s:
                    route_names.append(s)
        # append ports not in a route
        for port in comp.ports.values():
            port_name = port.get_name()
            draw_port = True
            for n in route_names:
                if port_name in n:
                    draw_port = False
            if draw_port:
                ports.append((port, comp))

    recurse(component)

    if do_bulk_difference:
        if not render_bulk:
            raise ValueError(
                "Cannot render do bulk difference without rendering bulk device"
            )

        diff = None
        for m in bulk_manifolds.values():
            if diff is None:
                diff = m
            else:
                diff += m
        for m in manifolds.values():
            diff -= m
        manifolds = {}
        bulk_manifolds = {"device": diff}

    return manifolds, bulk_manifolds, ports


def render_component(
    component: "Component",
    render_bulk: bool = True,
    do_bulk_difference: bool = True,
    flatten_scene: bool = True,
    wireframe_bulk: bool = False,
    show_assists: bool = False,
) -> trimesh.Trimesh | Scene:
    """
    ###### Render a Component to a Scene.

    ###### Parameters:
    - component (Component): The Component to render.
    - render_bulk (bool): Whether to render bulk shapes.
    - do_bulk_difference (bool): Whether to perform a difference operation on bulk shapes.
    - flatten_scene (bool): Whether to flatten the scene to a single mesh.
    - wireframe_bulk (bool): Whether to render bulk shapes as wireframes.
    - show_assists (bool): Whether to show port assist arrows.

    ###### Returns:
    - scene (Scene or trimesh.Trimesh): The rendered scene or flattened mesh.
    """
    print("Rendering Component...")
    scene = Scene()

    manifolds, bulk_manifolds, ports = _component_to_manifold(
        component, render_bulk=render_bulk, do_bulk_difference=do_bulk_difference
    )

    if show_assists:
        for port in ports:
            p, c = port
            _draw_port(scene, p, c)

    for m in manifolds.values():
        mesh = _manifold3d_shape_to_trimesh(m)
        scene.add_geometry(mesh)

    if render_bulk:
        for m in bulk_manifolds.values():
            if wireframe_bulk:
                mesh = _manifold3d_shape_to_wireframe(m)
            else:
                mesh = _manifold3d_shape_to_trimesh(m)
            scene.add_geometry(mesh)

    # draw component bounding box
    _draw_bounding_box(
        scene,
        size=component.get_size(),
        origin=component.get_position(),
        color=Color.from_name("black", 255),
        px_size=component._px_size,
        layer_size=component._layer_size,
    )

    if flatten_scene:
        return scene.to_mesh()  # for flattening (trimesh only)
        # return scene.to_geometry() # for flattening (also allows Path3D and Path2D)
    else:
        return scene
