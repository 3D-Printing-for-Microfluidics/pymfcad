import time
import math
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw
from shapely.geometry import Polygon

from . import Cube, Shape, TPMS

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
    device: "Device",
    composite_shape: "Shape",
    directory: Path,
    slice_list: list[dict],
) -> None:
    """
    Slice the device and save slices in the directory.

    Parameters:

    - _type (str): String indicating the type of slice (e.g. "masks").
    - device (Device): Device to be sliced.
    - composite_shape (Shape): Composite shape of the device to be sliced.
    - directory (Path): Directory to save the slices.
    - slice_list (list[dict]): List of dictionaries to store slice info.
    """

    # Slice manifold at layer height and resolution.
    from .. import VariableLayerThicknessComponent

    resolution = (int(device.get_size()[0]), int(device.get_size()[1]))

    if isinstance(device, VariableLayerThicknessComponent):
        expanded_layer_sizes = device._expand_layer_sizes()

    # Slice at layer size.
    slice_num = 0
    slice_position = 0
    actual_slice_position = 0.5
    device_height = device.get_size()[2]
    if _type != "":
        _type = " " + _type
    print(f"\tSlicing {type(device).__name__}{_type}...")
    while actual_slice_position < device_height:
        slice_height = device.get_position()[2] + actual_slice_position
        polygons = composite_shape._object.slice(slice_height).to_polygons()
        print(
            f"\r\t\tLayer {slice_num} at z={actual_slice_position:.4f}/{slice_position:.4f}/{slice_height:.4f} ({len(polygons)} polygons)",
            end="",
            flush=True,
        )

        # Translate polygons into device-local pixel space (XY only).
        polygons = [poly - np.array(device.get_position()[:2]) for poly in polygons]

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
                f"{directory}/{device.get_fully_qualified_name()}-slice{slice_num:04}.png"
            )

        if isinstance(device, VariableLayerThicknessComponent):
            # If the device has variable layer thickness, use the per-layer values.
            slice_position += expanded_layer_sizes[slice_num]
            if slice_num < len(expanded_layer_sizes) - 1:
                actual_slice_position += (
                    expanded_layer_sizes[slice_num] / device._layer_size / 2
                    + expanded_layer_sizes[slice_num + 1] / device._layer_size / 2
                )
            else:
                # If this is the last slice, just use the layer size.
                actual_slice_position += (
                    expanded_layer_sizes[slice_num] / device._layer_size
                )
        else:
            slice_position += device._layer_size
            actual_slice_position += 1.0


        slice_list.append(
            {
                "image_name": f"{device.get_fully_qualified_name()}-slice{slice_num:04}.png",
                "image_data": rle_encode_packed(np.array(img)),
                "layer_position": round(slice_position * 1000, 1),
            }
        )

        slice_num += 1

    print()


def _slice_tpms_component(
    device: "Device",
    unit_cell_size: tuple[int, int, int],
    tpms_func,
    tpms_fill: float,
    tpms_refinement: int,
    directory: Path,
    slice_list: list[dict],
) -> None:
    """
    Slice a TPMSComponent by tiling a single unit cell across XY and Z.

    Parameters:

    - device (Device): The TPMSComponent to slice.
    - unit_cell_size (tuple[int, int, int]): Unit cell size in px/layer space.
    - tpms_func: TPMS level-set function.
    - tpms_fill (float): Level-set value for the TPMS isosurface.
    - tpms_refinement (int): Level-set grid subdivisions per unit cell.
    - directory (Path): Directory to save slices.
    - slice_list (list[dict]): List of dictionaries to store slice info.
    """
    resolution = (int(device.get_size()[0]), int(device.get_size()[1]))
    cell_x, cell_y, cell_z = unit_cell_size
    cell_z_int = int(cell_z)
    tiles_x = int(math.ceil(resolution[0] / cell_x))
    tiles_y = int(math.ceil(resolution[1] / cell_y))

    unit_cell = TPMS(
        size=unit_cell_size,
        cells=(1, 1, 1),
        func=tpms_func,
        fill=tpms_fill,
        refinement=tpms_refinement,
        quiet=True,
    )

    def render_unit_cell_layer(local_z: float) -> tuple[np.ndarray, int]:
        polygons = unit_cell._object.slice(local_z).to_polygons()

        img = Image.new("L", resolution, 0)
        draw = ImageDraw.Draw(img)

        for poly in polygons:
            base = np.round(poly).astype(float)
            base[:, 1] = -base[:, 1]

            fill_color = 255 if _is_clockwise(base) else 0

            p = Polygon([tuple(p) for p in base])
            px_offset = 0.1
            shrunk = p.buffer(-px_offset)
            if shrunk.is_empty or shrunk.geom_type != "Polygon":
                continue

            coords = np.array(shrunk.exterior.coords)
            base_points = np.floor(coords).astype(int)

            base_min = base_points.min(axis=0)
            base_max = base_points.max(axis=0)

            for tx in range(tiles_x):
                for ty in range(tiles_y):
                    offset_x = tx * cell_x
                    offset_y = ty * cell_y
                    tile_offset = np.array([offset_x, img.height - offset_y])
                    points = base_points + tile_offset

                    points_min = base_min + tile_offset
                    points_max = base_max + tile_offset
                    if (
                        points_max[0] < 0
                        or points_min[0] >= img.width
                        or points_max[1] < 0
                        or points_min[1] >= img.height
                    ):
                        continue

                    draw.polygon([tuple(p) for p in points], fill=fill_color)

        return np.array(img), len(polygons)

    cached_layers = []
    cached_rle = []
    cached_counts = []
    for layer_index in range(cell_z_int):
        layer_img, poly_count = render_unit_cell_layer(float(layer_index))
        cached_layers.append(layer_img)
        cached_rle.append(rle_encode_packed(layer_img))
        cached_counts.append(poly_count)

    slice_num = 0
    slice_position = 0
    actual_slice_position = 0.00
    device_height = device.get_size()[2]
    print(f"\tSlicing TPMS {type(device).__name__}...")

    while actual_slice_position < device_height:
        local_z = actual_slice_position % cell_z
        layer_index = int(local_z) % cell_z_int
        print(
            f"\r\t\tLayer {slice_num} at z={actual_slice_position:.4f}/{slice_position:.4f}/{local_z:.4f} ({cached_counts[layer_index]} polygons)",
            end="",
            flush=True,
        )

        img_array = cached_layers[layer_index]

        if directory is not None:
            Image.fromarray(img_array).save(
                f"{directory}/{device.get_fully_qualified_name()}-slice{slice_num:04}.png"
            )

        slice_position += device._layer_size
        actual_slice_position += 1.0

        slice_list.append(
            {
                "image_name": f"{device.get_fully_qualified_name()}-slice{slice_num:04}.png",
                "image_data": cached_rle[layer_index],
                "layer_position": round(slice_position * 1000, 1),
            }
        )

        slice_num += 1

    print()


def slice_component(
    device: "Device",
    temp_directory: Path | None,
    sliced_devices: list["Device"],
    sliced_devices_data: list[dict],
) -> None:
    """
    Slice the device's components and save them in the temporary directory.

    Parameters:

    - device (Device): Device to be sliced.
    - temp_directory (Path): Path to the temporary directory where slices will be saved. If none, slices are not saved to disk.
    - sliced_devices (list[Device]): List to store sliced devices.
    - sliced_devices_data (list[dict]): List of dictionaries to store slice info.

    Raises:

        - RuntimeError: Attempted to subtract without a bulk shape.
    """
    # Calculate device relative position
    if device._parent is None:
        parent = None
        x_pos = device.get_position()[0]
        y_pos = device.get_position()[1]
        z_pos = device.get_position()[2] * device._layer_size
    else:
        parent = device._parent
        device_pos = device.get_position(
            px_size=parent._px_size, layer_size=parent._layer_size
        )
        parent_pos = parent.get_position(
            px_size=parent._px_size, layer_size=parent._layer_size
        )
        x_pos = device_pos[0] - parent_pos[0]
        y_pos = device_pos[1] - parent_pos[1]
        z_pos = (device_pos[2] - parent_pos[2]) * parent._layer_size

    # Skip slicing when this component instance was already processed.
    device_index = -1
    if device in sliced_devices:
        device_index = sliced_devices.index(device)
        sliced_devices_data[device_index]["positions"].append(
            (parent, x_pos, y_pos, z_pos)
        )
        return
    else:
        sliced_devices.append(device)
        sliced_devices_data.append(
            {
                "positions": [(parent, x_pos, y_pos, z_pos)],
                "slices": [],
                "masks": {}
            }
        )
        device_index = len(sliced_devices) - 1

    # Create a subdirectory for this device.
    device_subdirectory = None
    if temp_directory is not None:
        device_subdirectory = temp_directory / device.get_fully_qualified_name()
        device_subdirectory.mkdir(parents=True)

    from .. import TPMSComponent

    if isinstance(device, TPMSComponent):
        if device.subcomponents or device.shapes or device.bulk_shapes:
            raise RuntimeError("TPMSComponent cannot have subcomponents, voids, or bulks.")
        _slice_tpms_component(
            device=device,
            unit_cell_size=device.unit_cell_size,
            tpms_func=device.tpms_func,
            tpms_fill=device.tpms_fill,
            tpms_refinement=device.tpms_refinement,
            directory=device_subdirectory,
            slice_list=sliced_devices_data[device_index]["slices"],
        )
        return

    # Start by unioning this component's bulk shapes.
    if len(list(device.bulk_shapes.values())) == 0:
        raise RuntimeError("Tried to slice component without bulk shape")
    composite_shape = Shape.union(list(device.bulk_shapes.values()))
    

    # Accumulate subcomponent bounding boxes and recursively process subcomponents.
    bbox_cubes = []
    for sub in device.subcomponents.values():
        if sub._subtract_bounding_box:
            bbox = sub.get_bounding_box(device._px_size, device._layer_size)
            bbox_cube = Cube(
                size=(
                    (bbox[3] - bbox[0]) - device._px_size * 0.1,
                    (bbox[4] - bbox[1]) - device._px_size * 0.1,
                    (bbox[5] - bbox[2]) - device._layer_size * 0.1,
                ),
                center=False,
            ).translate(
                (
                    bbox[0] + device._px_size * 0.05,
                    bbox[1] + device._px_size * 0.05,
                    bbox[2] + device._layer_size * 0.05,
                )
            )
            bbox_cubes.append(bbox_cube)

        slice_component(
            sub,
            temp_directory,
            sliced_devices,
            sliced_devices_data,
        )

    # Accumulate this component's shapes (e.g., voids or cutouts) and bbox cubes.
    if len(list(device.shapes.values()) + bbox_cubes) > 0:
        local_shapes = Shape.union(list(device.shapes.values()) + bbox_cubes)
    

        # Subtract this component's shapes (e.g., voids or cutouts).
        if local_shapes is not None and composite_shape is None:
            raise RuntimeError("Tried to subtract without bulk")
        elif local_shapes is not None:
            composite_shape = composite_shape - local_shapes

    # Slice the device.
    _slice(
        "",
        device,
        composite_shape,
        device_subdirectory,
        sliced_devices_data[device_index]["slices"],
    )

    # Slice the device's masks.
    for key, (mask, settings) in device.regional_settings.items():
        if settings is None:
            continue
        masks_subdirectory = None
        if temp_directory is not None:
            masks_subdirectory = (
                temp_directory / "masks" / device.get_fully_qualified_name() / key
            )
            masks_subdirectory.mkdir(parents=True)

        sliced_devices_data[device_index]["masks"][key] = []

        _slice(
            f"{key} masks",
            device,
            mask,
            masks_subdirectory,
            sliced_devices_data[device_index]["masks"][key],
        )
