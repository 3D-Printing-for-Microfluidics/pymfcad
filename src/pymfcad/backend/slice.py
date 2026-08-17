import time
import math
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw
from shapely.geometry import Polygon

from . import Cube, Shape

def rle_encode_packed(img: np.ndarray):
    h, w = img.shape
    bits = (img > 0).astype(np.uint8)

    packed = np.packbits(bits, axis=None)

    diff = np.diff(packed, prepend=packed[0] ^ 1)
    run_starts = np.nonzero(diff)[0]

    run_lengths = np.diff(np.append(run_starts, packed.size))
    values = packed[run_starts]

    return values, run_lengths, (h, w)

def rle_decode_packed(values, run_lengths, shape):
    h, w = shape
    packed = np.repeat(values, run_lengths)

    bits = np.unpackbits(packed)[:h * w]
    return (bits.reshape(h, w) * 255).astype(np.uint8)

def rle_is_all_zeros(values):
    return np.all(values == 0)

def rle_is_all_non_zeros(values):
    return np.all(values != 0)


def _is_clockwise(polygon: np.ndarray) -> bool:
    """
    Return True if the 2D polygon (Nx2) is clockwise.

    Parameters:

    - polygon (np.ndarray): Polygon points as an Nx2 array.

    Returns:

    - bool: True when the polygon is clockwise.
    """
    area = 0
    n = len(polygon)

    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        area += x1 * y2 - x2 * y1

    return area < 0


def _slice(
    _type: str,
    component: "Component",
    composite_shape: "Shape",
    directory: Path,
    slice_list: list[dict],
) -> None:
    """
    Slice the component and save slices in the directory.

    Parameters:

    - _type (str): String indicating the type of slice (e.g. "masks").
    - component (Component): Component to be sliced.
    - composite_shape (Shape): Composite shape of the component to be sliced.
    - directory (Path): Directory to save the slices.
    - slice_list (list[dict]): List of dictionaries to store slice info.
    """

    # Slice manifold at layer height and resolution.
    from .. import VariableLayerThicknessComponent

    resolution = (int(component.get_size()[0]), int(component.get_size()[1]))

    if isinstance(component, VariableLayerThicknessComponent):
        expanded_layer_sizes = component._expand_layer_sizes()

    # Slice at layer size.
    slice_num = 0
    slice_position = 0
    actual_slice_position = 0.5
    component_height = component.get_size()[2]
    if _type != "":
        _type = " " + _type
    print(f"\tSlicing {type(component).__name__}{_type}...")
    while actual_slice_position < component_height:
        slice_height = component.get_position()[2] + actual_slice_position
        polygons = composite_shape._object.slice(slice_height).to_polygons()
        print(
            f"\r\t\tLayer {slice_num} at z={actual_slice_position:.4f}/{slice_position:.4f}/{slice_height:.4f} ({len(polygons)} polygons)",
            end="",
            flush=True,
        )

        # Translate polygons into component-local pixel space (XY only).
        polygons = [poly - np.array(component.get_position()[:2]) for poly in polygons]

        # Create a blank grayscale image.
        img = Image.new("L", resolution, 0)
        draw = ImageDraw.Draw(img)

        for poly in polygons:
            clockwise = _is_clockwise(poly)

            # Snap to the pixel grid.
            transformed = np.round(poly).astype(int)
            transformed[:, 1] = img.height - transformed[:, 1]
            points = [tuple(p) for p in transformed]

            # Determine fill color based on orientation.
            fill_color = 0 if clockwise else 255

            # Convert polygon and offset inward slightly to avoid edge artifacts.
            p = Polygon(points)
            px_offset = 0.1
            shrunk = p.buffer(-px_offset)
            # Only process if still valid.
            if not shrunk.is_empty and shrunk.geom_type == "Polygon":
                coords = np.array(shrunk.exterior.coords)
                # Floor to fix polygon inclusivity issues.
                transformed = np.floor(coords).astype(int)
                points = [tuple(p) for p in transformed]

            draw.polygon(points, fill=fill_color)

        # Save the slice image.
        if directory is not None:
            img.save(
                f"{directory}/{component.get_fully_qualified_name()}-slice{slice_num:04}.png"
            )

        if isinstance(component, VariableLayerThicknessComponent):
            # If the component has variable layer thickness, use the per-layer values.
            slice_position += expanded_layer_sizes[slice_num]
            if slice_num < len(expanded_layer_sizes) - 1:
                actual_slice_position += (
                    expanded_layer_sizes[slice_num] / component._layer_size / 2
                    + expanded_layer_sizes[slice_num + 1] / component._layer_size / 2
                )
            else:
                # If this is the last slice, just use the layer size.
                actual_slice_position += (
                    expanded_layer_sizes[slice_num] / component._layer_size
                )
        else:
            slice_position += component._layer_size
            actual_slice_position += 1.0


        slice_list.append(
            {
                "image_name": f"{component.get_fully_qualified_name()}-slice{slice_num:04}.png",
                "image_data": rle_encode_packed(np.array(img)),
                "layer_position": round(slice_position * 1000, 1),
            }
        )

        slice_num += 1

    print()

def slice_component(
    component: "Component",
    temp_directory: Path | None,
    sliced_components: list["Component"],
    sliced_components_data: list[dict],
) -> None:
    """
    Slice the component's components and save them in the temporary directory.

    Parameters:

    - component (Component): Component to be sliced.
    - temp_directory (Path): Path to the temporary directory where slices will be saved. If none, slices are not saved to disk.
    - sliced_components (list[Component]): List to store sliced components.
    - sliced_components_data (list[dict]): List of dictionaries to store slice info.

    Raises:

        - RuntimeError: Attempted to subtract without a bulk shape.
    """
    # Calculate component relative position
    if component._parent is None:
        parent = None
        x_pos = component.get_position()[0]
        y_pos = component.get_position()[1]
        z_pos = component.get_position()[2] * component._layer_size
    else:
        parent = component._parent
        component_pos = component.get_position(
            px_size=parent._px_size, layer_size=parent._layer_size
        )
        parent_pos = parent.get_position(
            px_size=parent._px_size, layer_size=parent._layer_size
        )
        x_pos = component_pos[0] - parent_pos[0]
        y_pos = component_pos[1] - parent_pos[1]
        z_pos = (component_pos[2] - parent_pos[2]) * parent._layer_size

    # Skip slicing when this component instance was already processed.
    component_index = -1
    if component in sliced_components:
        component_index = sliced_components.index(component)
        sliced_components_data[component_index]["positions"].append(
            (component, x_pos, y_pos, z_pos)
        )
        return
    else:
        sliced_components.append(component)
        sliced_components_data.append(
            {
                "positions": [(component, x_pos, y_pos, z_pos)],
                "slices": [],
                "masks": {}
            }
        )
        component_index = len(sliced_components) - 1

    # Create a subdirectory for this component.
    component_subdirectory = None
    if temp_directory is not None:
        component_subdirectory = temp_directory / component.get_fully_qualified_name()
        component_subdirectory.mkdir(parents=True)

    # Start by unioning this component's bulk shapes.
    if len(list(component.bulk_shapes.values())) == 0:
        raise RuntimeError("Tried to slice component without bulk shape")
    composite_shape = Shape.union(list(component.bulk_shapes.values()))
    

    # Accumulate subcomponent bounding boxes and recursively process subcomponents.
    bbox_cubes = []
    for sub in component.subcomponents.values():
        if sub._subtract_bounding_box:
            bbox = sub.get_bounding_box(component._px_size, component._layer_size)
            bbox_cube = Cube(
                size=(
                    (bbox[3] - bbox[0]) - component._px_size * 0.1,
                    (bbox[4] - bbox[1]) - component._px_size * 0.1,
                    (bbox[5] - bbox[2]) - component._layer_size * 0.1,
                ),
                center=False,
            ).translate(
                (
                    bbox[0] + component._px_size * 0.05,
                    bbox[1] + component._px_size * 0.05,
                    bbox[2] + component._layer_size * 0.05,
                )
            )
            bbox_cubes.append(bbox_cube)

        slice_component(
            sub,
            temp_directory,
            sliced_components,
            sliced_components_data,
        )

    # Accumulate this component's shapes (e.g., voids or cutouts) and bbox cubes.
    if len(list(component.shapes.values()) + bbox_cubes) > 0:
        local_shapes = Shape.union(list(component.shapes.values()) + bbox_cubes)
    

        # Subtract this component's shapes (e.g., voids or cutouts).
        if local_shapes is not None and composite_shape is None:
            raise RuntimeError("Tried to subtract without bulk")
        elif local_shapes is not None:
            composite_shape = composite_shape - local_shapes

    # Slice the component.
    _slice(
        "",
        component,
        composite_shape,
        component_subdirectory,
        sliced_components_data[component_index]["slices"],
    )

    # Slice the component's masks.
    for key, (mask, settings) in component.regional_settings.items():
        if settings is None:
            continue
        masks_subdirectory = None
        if temp_directory is not None:
            masks_subdirectory = (
                temp_directory / "masks" / component.get_fully_qualified_name() / key
            )
            masks_subdirectory.mkdir(parents=True)

        sliced_components_data[component_index]["masks"][key] = []

        _slice(
            f"{key} masks",
            component,
            mask,
            masks_subdirectory,
            sliced_components_data[component_index]["masks"][key],
        )
