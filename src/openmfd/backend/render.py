from __future__ import annotations

import gc
import trimesh
import numpy as np
from pathlib import Path
from trimesh.scene import Scene
from trimesh.visual import ColorVisuals
from trimesh.visual.material import PBRMaterial

from . import Shape
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
    """
    Draw a bounding box in the scene.

    Parameters:

    - scene (Scene): Scene to draw into.
    - size (tuple[int, int, int]): Bounding box size in px/layer units.
    - origin (tuple[int, int, int]): Bounding box origin in px/layer units.
    - color (Color): Color to use for the bounding box.
    - px_size (float): Pixel size scaling.
    - layer_size (float): Layer height scaling.
    - name (str): Geometry name.
    """
    # Build a wireframe box in world units.
    bbox_size = (size[0] * px_size, size[1] * px_size, size[2] * layer_size)
    bbox_origin = (origin[0] * px_size, origin[1] * px_size, origin[2] * layer_size)
    translation = trimesh.transformations.translation_matrix(bbox_origin)
    translation[:3, 3] = [o + s / 2 for o, s in zip(bbox_origin, bbox_size)]
    bbox = trimesh.path.creation.box_outline(
        extents=np.array(bbox_size), transform=translation
    )
    bbox.colors = [color._to_rgba()]
    scene.add_geometry(bbox)
    del bbox


def _draw_arrow(
    scene: Scene,
    length: float,
    position: np.typing.NDArray[np.int_],
    direction: np.typing.NDArray[np.int_],
    port: "Port",
    reflect: bool = False,
    half_size: bool = False,
) -> None:
    """
    Draw an arrow in the scene.

    Parameters:

    - scene (Scene): Scene to draw into.
    - length (float): Arrow length in world units.
    - position (np.typing.NDArray[np.int_]): Arrow position.
    - direction (np.typing.NDArray[np.int_]): Arrow direction vector.
    - port (Port): Port that defines the color.
    - reflect (bool): Whether to reflect the arrow along its axis.
    - half_size (bool): Whether to offset by half length instead of full length.
    """
    # Align the local Z axis to the arrow direction.
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
    del arrow


def _draw_port(scene: Scene, port: "Port", component: "Component") -> None:
    """
    Draw a port in the scene.

    Parameters:

    - scene (Scene): Scene to draw into.
    - port (Port): Port to draw.
    - component (Component): Component owning the port.
    """
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

    if port._type.name == "IN":
        _draw_arrow(
            scene, arrow_length, arrow_position, arrow_direction, port, reflect=True
        )

    if port._type.name == "OUT":
        _draw_arrow(
            scene, arrow_length, arrow_position, arrow_direction, port, reflect=False
        )


def _manifold3d_shape_to_trimesh(shape: "Shape") -> trimesh.Trimesh:
    """
    Convert a Manifold3D shape to a trimesh object.

    Parameters:

    - shape (Shape): The Manifold3D shape to convert.

    Returns:

    - trimesh.Trimesh: The converted trimesh object.
    """
    m = shape._object.to_mesh()
    tm = trimesh.Trimesh(vertices=m.vert_properties, faces=m.tri_verts)
    rgba = shape._color._to_float()
    if len(rgba) == 3:
        rgba = (*rgba, 1.0)
    vertex_rgba = (rgba[0], rgba[1], rgba[2], 1.0)
    tm.visual = ColorVisuals(tm, vertex_colors=[vertex_rgba] * len(tm.vertices))
    tm.visual.material = PBRMaterial(baseColorFactor=rgba)
    return tm


def _manifold3d_shape_to_wireframe(
    shape: "Shape", coplanar_tol: float = 1e-5
) -> trimesh.path.Path3D:
    """
    Convert a Manifold3D shape to a wireframe Path3D, removing edges between coplanar faces.

    Parameters:

    - shape (Shape): The Manifold3D shape.
    - coplanar_tol (float): Cosine similarity tolerance for coplanarity (1.0 = perfectly coplanar).

    Returns:

    - Path3D: A wireframe path with redundant coplanar internal edges removed.
    """
    m = shape._object.to_mesh()
    vertices = np.asarray(m.vert_properties)
    faces = np.asarray(m.tri_verts)

    # Compute face normals.
    face_normals, _ = trimesh.triangles.normals(vertices[faces])

    # Map edges to faces that share them.
    edge_face_map = {}

    for face_idx, face in enumerate(faces):
        tri_edges = [
            tuple(sorted((face[0], face[1]))),
            tuple(sorted((face[1], face[2]))),
            tuple(sorted((face[2], face[0]))),
        ]
        for edge in tri_edges:
            edge_face_map.setdefault(edge, []).append(face_idx)

    # Filter edges
    retained_edges = []

    for edge, face_indices in edge_face_map.items():
        if len(face_indices) == 1:
            # Border edge.
            retained_edges.append(edge)
        elif len(face_indices) == 2:
            # Shared by two triangles — check coplanarity.
            n1 = face_normals[face_indices[0]]
            n2 = face_normals[face_indices[1]]
            cos_angle = np.dot(n1, n2)
            if cos_angle < 1.0 - coplanar_tol:
                retained_edges.append(edge)
        else:
            # Non-manifold edge (shared by more than 2 faces) — keep for visibility.
            retained_edges.append(edge)

    # Create the wireframe path.
    entities = [trimesh.path.entities.Line([e[0], e[1]]) for e in retained_edges]
    del retained_edges, face_normals, edge_face_map
    return trimesh.path.Path3D(entities=entities, vertices=vertices)


def _component_to_manifold(
    component: "Component",
    render_bulk: bool = True,
    do_bulk_difference: bool = True,
) -> tuple[
    dict[str, "Shape"],
    dict[str, "Shape"],
    dict[str, "Shape"],
    "Shape" | None,
    list[tuple["Port", "Component"]],
]:
    """
    Convert a Component to manifolds and bulk shapes for rendering.

    Parameters:

    - component (Component): The Component to convert.
    - render_bulk (bool): Whether to render bulk shapes.
    - do_bulk_difference (bool): Whether to perform a difference operation on bulk shapes.

    Returns:

    - tuple[dict[str, Shape], dict[str, Shape], dict[str, Shape], Shape | None, list[tuple[Port, Component]]]:
        Manifolds, bulk manifolds, regional manifolds, bulk diff, and ports to draw.

    Raises:

    - ValueError: Bulk difference requested without bulk rendering.
    """
    bulk_manifolds = {}
    manifolds = {}
    regional_manifolds = {}
    ports = []

    def accumulate_shape(comp: "Component", _top_level: bool = True) -> None:
        """
        Accumulate shapes from the component and its subcomponents.

        Parameters:

        - comp (Component): Component to traverse.
        - _top_level (bool): Whether this is the top-level component.
        """
        # Iterate shapes (includes inverted devices).
        for shape in comp.shapes.values():
            # key = str(shape._color)
            key = str(shape._label)
            tmp_shape = shape.copy(_internal=True)
            tmp_shape._object = tmp_shape._object.scale(
                [comp._px_size, comp._px_size, comp._layer_size]
            )
            if key in manifolds.keys():
                manifolds[key].append(tmp_shape)
            else:
                manifolds[key] = [tmp_shape]

        # Iterate subcomponents.
        for sub in comp.subcomponents.values():
            if not sub.hide_in_render:
                accumulate_shape(sub, _top_level=False)

        if _top_level:
            # Merge shapes of the same key.
            for key, shape_list in manifolds.items():
                if len(shape_list) > 0:
                    manifolds[key] = Shape._batch_boolean_add(shape_list)

    def accumulate_bulk_shape(comp: "Component") -> dict[str, "Shape"]:
        """
        Accumulate bulk shapes from the component and its subcomponents.

        Parameters:

        - comp (Component): Component to traverse.

        Returns:

        - dict[str, Shape]: Bulk shapes grouped by label.
        """
        # Iterate bulk shapes (device-only).
        bulks = {}
        comp_cubes = None
        comp_bulks = {}

        if len(comp.bulk_shapes) == 0:
            raise ValueError(
                f"Component {comp._name} has no bulk shapes to render."
            )

        for bulk in comp.bulk_shapes.values():
            # key = str(bulk._color)
            key = str(bulk._label)
            temp_bulk = bulk.copy(_internal=True)
            temp_bulk._object = temp_bulk._object.scale(
                [comp._px_size, comp._px_size, comp._layer_size]
            )
            if key in bulks.keys():
                bulks[key].append(temp_bulk)
            else:
                bulks[key] = [temp_bulk]

        # Iterate subcomponents.
        for sub in comp.subcomponents.values():
            if sub._subtract_bounding_box:
                bbox = sub.get_bounding_box(comp._px_size, comp._layer_size)
                from . import Cube

                bbox_cube = Cube(
                    size=(
                        (bbox[3] - bbox[0]) - comp._px_size * 0.1,
                        (bbox[4] - bbox[1]) - comp._px_size * 0.1,
                        (bbox[5] - bbox[2]) - comp._layer_size * 0.1,
                    ),
                    center=False,
                ).translate(
                    (
                        bbox[0] + comp._px_size * 0.05,
                        bbox[1] + comp._px_size * 0.05,
                        bbox[2] + comp._layer_size * 0.05,
                    )
                )
                bbox_cube._object = bbox_cube._object.scale(
                    [comp._px_size, comp._px_size, comp._layer_size]
                )
                if comp_cubes is None:
                    comp_cubes = [bbox_cube]
                else:
                    comp_cubes.append(bbox_cube)

            if not sub.hide_in_render:
                _bulks = accumulate_bulk_shape(sub)
                for key, item in _bulks.items():
                    if key in comp_bulks.keys():
                        comp_bulks[key].append(item)
                    else:
                        comp_bulks[key] = [item]

        comp_cubes = Shape._batch_boolean_add(comp_cubes) if comp_cubes is not None else None
        for key, bulk in bulks.items():
            if len(bulk) == 0:
                continue
            bulks[key] = Shape._batch_boolean_add(bulk)
            bulks[key] = bulks[key] - comp_cubes if comp_cubes is not None else bulks[key]
            if key in comp_bulks.keys():
                bulks[key] = Shape._batch_boolean_add([bulks[key]] + comp_bulks[key])
        for key, bulk in comp_bulks.items():
            if key not in bulks.keys():
                bulks[key] = Shape._batch_boolean_add(comp_bulks[key])
        return bulks

    def accumulate_regional_settings(comp: "Component", _top_level: bool = True) -> None:
        """
        Accumulate regional settings from the component and its subcomponents.

        Parameters:

        - comp (Component): Component to traverse.
        - _top_level (bool): Whether this is the top-level component.
        """
        for shape, setting in comp.regional_settings.values():
            if setting is None:
                if shape._name == "default_exposure_settings_region":
                    prefix = "default_exposure_settings_"
                elif shape._name == "default_position_settings_region":
                    prefix = "default_position_settings_"
                elif shape._name == "burnin_region":
                    prefix = "burnin_"
                else:
                    raise ValueError(
                        f"Regional setting for shape with name/label ({shape._name}, {shape._label}) is None."
                    )
            elif type(setting).__name__ == "MembraneSettings":
                prefix = "membrane_settings_"
            elif type(setting).__name__ == "PositionSettings":
                prefix = "position_settings_"
            elif type(setting).__name__ == "ExposureSettings":
                prefix = "exposure_settings_"
            elif type(setting).__name__ == "SecondaryDoseSettings":
                prefix = "secondary_dose_settings_"
            else:
                prefix = ""
            # key = str(shape._color)
            key = prefix + str(shape._label)
            tmp_shape = shape.copy(_internal=True)
            tmp_shape._object = tmp_shape._object.scale(
                [comp._px_size, comp._px_size, comp._layer_size]
            )
            if key in regional_manifolds.keys():
                regional_manifolds[key].append(tmp_shape)
            else:
                regional_manifolds[key] = [tmp_shape]

        # Iterate subcomponents.
        for sub in comp.subcomponents.values():
            if not sub.hide_in_render:
                accumulate_regional_settings(sub, _top_level=False)

        if _top_level:
            # Merge shapes of the same key.
            for key, shape_list in regional_manifolds.items():
                if len(shape_list) > 0:
                    regional_manifolds[key] = Shape._batch_boolean_add(shape_list)

    def get_unconnected_ports(comp: "Component") -> None:
        """
        Recursive function to traverse the component tree and collect unconnected ports.

        Parameters:

        - comp (Component): Component to traverse.
        """
        # Append ports not in a route.
        for port in comp.ports.values():
            if port.get_name() not in comp.connected_ports:
                ports.append((port, comp))

        # Iterate subcomponents.
        for sub in comp.subcomponents.values():
            get_unconnected_ports(sub)

    accumulate_shape(component)
    if render_bulk:
        bulk_manifolds = accumulate_bulk_shape(component)
    accumulate_regional_settings(component)
    if _draw_port:
        get_unconnected_ports(component)

    diff = None
    if do_bulk_difference:
        if not render_bulk:
            raise ValueError(
                "Cannot render do bulk difference without rendering bulk device"
            )

        diff = Shape._batch_boolean_add_then_subtract(list(bulk_manifolds.values()), list(manifolds.values()))

    return manifolds, bulk_manifolds, regional_manifolds, diff, ports


def render_component(
    component: "Component",
    path: str = "",
    render_bulk: bool = True,
    do_bulk_difference: bool = True,
    preview: bool = False,
    version_suffix: str | None = None,
    empty_directory: bool = True,
) -> trimesh.Trimesh | Scene:
    """
    Render a Component to a Scene.

    Parameters:

    - component (Component): The Component to render.
    - path (str): The directory or file path to save the rendered output.
    - render_bulk (bool): Whether to render bulk shapes.
    - do_bulk_difference (bool): Whether to perform a difference operation on bulk shapes.
    - preview (bool): If True, exports individual GLB files for previewing. If False, exports a single file.

    Returns:

    - trimesh.Trimesh | Scene: The rendered scene or flattened mesh.

    Raises:

    - ValueError: Bulk difference requested without bulk rendering.
    """

    manifolds, bulk_manifolds, regional_manifolds, diff, ports = _component_to_manifold(
        component, render_bulk=render_bulk, do_bulk_difference=do_bulk_difference
    )

    if preview:
        print("Exporting preview...")
        p = Path(path)
        try:
            p.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            # Clear existing previews before exporting.
            if empty_directory:
                for f in p.iterdir():
                    if f.is_file() and f.suffix.lower() != ".json":
                        f.unlink()

        suffix = version_suffix or ""

        def preview_name(base: str) -> str:
            return f"{base}{suffix}.glb"

        bbox_scene = Scene()
        _draw_bounding_box(
            bbox_scene,
            size=component.get_size(),
            origin=component.get_position(),
            color=Color.from_name("black", 255),
            px_size=component._px_size,
            layer_size=component._layer_size,
        )
        bbox_scene.export(f"{path}/{preview_name('bounding_box')}")
        diff_scene = Scene()
        if diff is not None:
            mesh = _manifold3d_shape_to_trimesh(diff)
            diff_scene.add_geometry(mesh)
            del mesh
            diff_scene.export(f"{path}/{preview_name('device')}")
            del diff_scene
        if len(manifolds) > 0:
            for k, v in manifolds.items():
                void_scene = Scene()
                mesh = _manifold3d_shape_to_trimesh(v)
                void_scene.add_geometry(mesh)
                del mesh
                void_scene.export(f"{path}/{preview_name(f'void_{k}')}")
                del void_scene
            del manifolds
        if len(bulk_manifolds) > 0:
            for k, v in bulk_manifolds.items():
                bulk_scene = Scene()
                mesh = _manifold3d_shape_to_trimesh(v)
                bulk_scene.add_geometry(mesh)
                del mesh
                bulk_scene.export(f"{path}/{preview_name(f'bulk_{k}')}")
                del bulk_scene
            del bulk_manifolds
        if len(regional_manifolds) > 0:
            for k, v in regional_manifolds.items():
                regional_scene = Scene()
                mesh = _manifold3d_shape_to_trimesh(v)
                regional_scene.add_geometry(mesh)
                del mesh
                regional_scene.export(f"{path}/{preview_name(f'regional_{k}')}")
                del regional_scene
            del regional_manifolds
        if len(ports) > 0:
            port_scene = Scene()
            for port in ports:
                p, c = port
                _draw_port(port_scene, p, c)
            port_scene.export(f"{path}/{preview_name('ports')}")
            del port_scene

    else:
        if diff is not None:
            del manifolds
            manifolds = {}
            del bulk_manifolds
            bulk_manifolds = {"device": diff}

        scene = Scene()
        for m in manifolds.values():
            mesh = _manifold3d_shape_to_trimesh(m)
            scene.add_geometry(mesh)
            del mesh
        del manifolds

        if render_bulk:
            for m in bulk_manifolds.values():
                mesh = _manifold3d_shape_to_trimesh(m)
                scene.add_geometry(mesh)
                del mesh
            del bulk_manifolds
        del diff

        mesh = scene.to_mesh()
        del scene

        print("Exporting render...")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        mesh.export(path)
        del mesh
        gc.collect()
