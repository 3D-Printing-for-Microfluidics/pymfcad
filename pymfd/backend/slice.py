import time
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw
from shapely.geometry import Polygon

from . import Cube


def _is_clockwise(polygon: np.ndarray) -> bool:
    """
    Returns True if the 2D polygon (Nx2) is clockwise.
    Based on the signed area.
    """
    x = polygon[:, 0]
    y = polygon[:, 1]
    return np.sum((x[1:] - x[:-1]) * (y[1:] + y[:-1])) > 0


def _slice(
    device: "Device",
    composite_shape: "Shape",
    directory: Path,
    sliced_devices: list,
    sliced_devices_info: list,
):

    ############## Slice manifold at layer height and resolution ##############
    from .. import VariableLayerThicknessComponent

    resolution = (int(device.get_size()[0]), int(device.get_size()[1]))

    if isinstance(device, VariableLayerThicknessComponent):
        expanded_layer_sizes = device._expand_layer_sizes()

    # Slice at layer size
    slice_num = 0
    slice_position = 0
    actual_slice_position = (
        expanded_layer_sizes[0] / 2
        if isinstance(device, VariableLayerThicknessComponent)
        else device._layer_size / 2
    )
    device_height = (
        device._get_device_height()
        if isinstance(device, VariableLayerThicknessComponent)
        else device.get_size()[2] * device._layer_size
    )
    print(f"\tSlicing {type(device).__name__}...")
    while actual_slice_position < device_height:
        slice_height = (
            device.get_position()[2] * device._layer_size + actual_slice_position
        )
        polygons = composite_shape._object.slice(slice_height).to_polygons()
        print(
            f"\t\tLayer {slice_num} at z={actual_slice_position:.4f}/{slice_position:.4f}/{slice_height:.4f} ({len(polygons)} polygons)"
        )

        # Translate polygons from device position to pixel space
        # subtract device position (x&y only, convert to pixel space) from polygons
        # This assumes polygons are in mm, so we need to convert to pixel space
        polygons = [
            poly - np.array(device.get_position()[:2]) * device._px_size
            for poly in polygons
        ]

        # Create a new blank grayscale image
        img = Image.new("L", resolution, 0)
        draw = ImageDraw.Draw(img)

        # Step 3: Draw each polygon
        for poly in polygons:
            # snap to pixel grid
            transformed = np.round(poly / device._px_size).astype(int)
            transformed[:, 1] = img.height - transformed[:, 1]
            points = [tuple(p) for p in transformed]

            # Determine fill color based on orientation
            if _is_clockwise(transformed):
                fill_color = 255  # solid
            else:
                fill_color = 0  # hole

            # Convert poly (Nx2 numpy array) to shapely polygon and offset inward by small amount in px sdpace
            p = Polygon(points)
            px_offset = 0.1
            shrunk = p.buffer(-px_offset)
            # Only process if still valid
            if not shrunk.is_empty and shrunk.geom_type == "Polygon":
                coords = np.array(shrunk.exterior.coords)
                # do floor to fix issues with polygon inclusivity
                transformed = np.floor(coords).astype(int)
                points = [tuple(p) for p in transformed]

            # Draw polygon
            draw.polygon(points, fill=fill_color)

        # 5. Save or show the image
        img.save(
            f"{directory}/{device.get_fully_qualified_name()}-slice{slice_num:04}.png"
        )

        if isinstance(device, VariableLayerThicknessComponent):
            # If the device has variable layer thickness, use the layer size from the device
            slice_position += expanded_layer_sizes[slice_num]
            if slice_num < len(expanded_layer_sizes) - 1:
                actual_slice_position += (
                    expanded_layer_sizes[slice_num] / 2
                    + expanded_layer_sizes[slice_num + 1] / 2
                )
            else:
                # If this is the last slice, just use the layer size
                actual_slice_position += expanded_layer_sizes[slice_num]
        else:
            slice_position += device._layer_size
            actual_slice_position += device._layer_size

        if len(sliced_devices) > 0:
            device_index = sliced_devices.index(device)
            sliced_devices_info[device_index]["slices"].append(
                {
                    "image_name": f"{device.get_fully_qualified_name()}-slice{slice_num:04}.png",
                    "layer_position": round(slice_position * 1000, 1),
                }
            )

        slice_num += 1


def slice_component(
    device: "Device",
    temp_directory: Path,
    sliced_devices: list,
    sliced_devices_info: list,
    _recursed: bool = False,
):
    """
    ###### Slice the device's components and save them in the temporary directory.

    ###### Parameters:
    - device: Device to be sliced.
    - temp_directory: Path to the temporary directory where slices will be saved.
    - sliced_devices: Dictionary to store sliced devices.
    - _create_subdirectory: Whether to create a subdirectory for the slices.
    """
    # Calculate device relative position
    if device._parent is None:
        parent = None
        x_pos = device.get_position()[0]
        y_pos = device.get_position()[1]
        z_pos = device.get_position()[2] * device._layer_size
    else:
        parent = device._parent
        x_pos = device.get_position()[0] - device._parent.get_position()[0]
        y_pos = device.get_position()[1] - device._parent.get_position()[1]
        z_pos = (
            device.get_position()[2] - device._parent.get_position()[2]
        ) * device._layer_size
    ############## Only slice components when nessicary ##############
    # Check if component with same instantiation parameters has already been sliced
    if device in sliced_devices:
        device_index = sliced_devices.index(device)
        sliced_devices_info[device_index]["positions"].append(
            (parent, x_pos, y_pos, z_pos)
        )
        return
    else:
        sliced_devices.append(device)
        sliced_devices_info.append(
            {
                "positions": [(parent, x_pos, y_pos, z_pos)],
                "slices": [],
            }
        )

    # Create a subdirectory for this device
    device_subdirectory = temp_directory / device.get_fully_qualified_name()
    device_subdirectory.mkdir(parents=True)

    ############## Create manifold of component ##############
    # Start by unioning this component's bulk shapes
    composite_shape = None
    for bulk in device.bulk_shapes:
        composite_shape = (
            bulk.copy(_internal=True)
            if composite_shape is None
            else composite_shape + bulk.copy(_internal=True)
        )

    local_shapes = None
    # Accumulate this component's shapes (e.g. voids or cutouts)
    for shape in device.shapes:
        local_shapes = (
            shape.copy(_internal=True)
            if local_shapes is None
            else local_shapes + shape.copy(_internal=True)
        )

    # Accumulate subcomponent bboxes and recursively process subcomponents
    for sub in device.subcomponents:
        bbox = sub.get_bounding_box(device._px_size, device._layer_size)
        bbox_cube = Cube(
            size=(
                (bbox[3] - bbox[0]),
                (bbox[4] - bbox[1]),
                (bbox[5] - bbox[2]),
            ),
            px_size=device._px_size,
            layer_size=device._layer_size,
            center=False,
        ).translate(
            (
                bbox[0],
                bbox[1],
                bbox[2],
            )
        )
        local_shapes = local_shapes + bbox_cube if local_shapes is not None else bbox_cube

        slice_component(
            sub,
            temp_directory,
            sliced_devices,
            sliced_devices_info,
            _recursed=True,
        )

    # Subtract this component's shapes (e.g. voids or cutouts)
    if composite_shape is None:
        raise RuntimeError("Tried to subtract without bulk")
    composite_shape = (
        composite_shape - local_shapes if local_shapes is not None else composite_shape
    )
    time.sleep(0.1)

    # Slice the device
    _slice(
        device,
        composite_shape,
        device_subdirectory,
        sliced_devices,
        sliced_devices_info,
    )

    # Slice the device's masks
    for key, (mask, settings) in device.regional_settings.items():
        masks_subdirectory = (
            temp_directory / "masks" / device.get_fully_qualified_name() / key
        )
        masks_subdirectory.mkdir(parents=True)
        _slice(
            device,
            mask,
            masks_subdirectory,
            [],
            [],
        )
