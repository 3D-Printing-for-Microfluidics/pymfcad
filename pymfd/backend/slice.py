import time
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw
from shapely.geometry import Polygon

from . import Cube

# def slice_component(
#     component: Component,
#     render_bulk: bool = True,
#     do_bulk_difference: bool = True,
# ) -> None:
#     """
#     ###### Slice a Component and save each slice as an image.

#     ###### Parameters:
#     - component (Component): The Component to slice.
#     - render_bulk (bool): Whether to render bulk shapes.
#     - do_bulk_difference (bool): Whether to perform a difference operation on bulk shapes.

#     ###### Returns:
#     - None: Saves images to disk.
#     """
#     manifolds, bulk_manifolds, _ = _component_to_manifold(
#         component, render_bulk=render_bulk, do_bulk_difference=do_bulk_difference
#     )

#     manifold = None
#     for m in manifolds.values():
#         if manifold is None:
#             manifold = m
#         else:
#             manifold += m

#     if render_bulk:
#         bulk_manifold = None
#         for m in bulk_manifolds.values():
#             if bulk_manifold is None:
#                 bulk_manifold = m
#             else:
#                 bulk_manifold += m
#         if do_bulk_difference:
#             bulk_manifold -= manifold
#             manifold = bulk_manifold
#         else:
#             manifold += manifold

#     print("Slice")

#     slice_num = 0
#     z_height = 0
#     while z_height < component._size[2]:
#         polygons = manifold._object.slice(
#             component._position[2] * component._layer_size
#             + z_height * component._layer_size
#         ).to_polygons()

#         print(f"Slice {slice_num} at z={z_height}")

#         # Create a new blank grayscale image
#         img = Image.new("L", (2560, 1600), 0)
#         draw = ImageDraw.Draw(img)

#         # Step 3: Draw each polygon
#         for poly in polygons:
#             # snap to pixel grid
#             transformed = np.round(poly / component._px_size).astype(int)
#             transformed[:, 1] = img.height - transformed[:, 1]
#             points = [tuple(p) for p in transformed]

#             # Determine fill color based on orientation
#             if _is_clockwise(transformed):
#                 fill_color = 255  # solid
#             else:
#                 fill_color = 0  # hole

#             # Convert poly (Nx2 numpy array) to shapely polygon and offset inward by small amount in px sdpace
#             p = Polygon(points)
#             px_offset = 0.1
#             shrunk = p.buffer(-px_offset)
#             # Only process if still valid
#             if not shrunk.is_empty and shrunk.geom_type == "Polygon":
#                 coords = np.array(shrunk.exterior.coords)
#                 # do floor to fix issues with polygon inclusivity
#                 transformed = np.floor(coords).astype(int)
#                 points = [tuple(p) for p in transformed]

#             # Draw polygon
#             draw.polygon(points, fill=fill_color)

#         # 5. Save or show the image
#         img.save(f"slice{slice_num}.png")
#         img.show()

#         slice_num += 1
#         z_height += 1


def _is_clockwise(polygon: np.ndarray) -> bool:
    """
    Returns True if the 2D polygon (Nx2) is clockwise.
    Based on the signed area.
    """
    x = polygon[:, 0]
    y = polygon[:, 1]
    return np.sum((x[1:] - x[:-1]) * (y[1:] + y[:-1])) > 0


def slice(
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
    ############## Only slice components when nessicary ##############
    # Check if component with same instantiation parameters has already been sliced
    if device in sliced_devices:
        device_index = sliced_devices.index(device)
        sliced_devices_info[device_index]["positions"].append(
            (
                device.get_position()[0] * device._px_size,
                device.get_position()[1] * device._px_size,
                device.get_position()[2] * device._layer_size,
            )
        )
        return
    else:
        sliced_devices.append(device)
        sliced_devices_info.append(
            {
                "positions": [
                    (
                        device.get_position()[0] * device._px_size,
                        device.get_position()[1] * device._px_size,
                        device.get_position()[2] * device._layer_size,
                    )
                ],
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

        slice(
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

    ############## Slice manifold at layer height and resolution ##############
    resolution = None
    from .. import Device, VariableLayerThicknessComponent

    if isinstance(device, Device):
        resolution = device.resolution.px_count
    else:
        resolution = (int(device.get_size()[0]), int(device.get_size()[1]))

    if isinstance(device, VariableLayerThicknessComponent):
        expanded_layer_sizes = device._expand_layer_sizes()

    # Slice at layer size
    slice_num = 0
    z_height = (
        expanded_layer_sizes[0] / 2
        if isinstance(device, VariableLayerThicknessComponent)
        else device._layer_size / 2
    )
    device_height = (
        device._get_device_height()
        if isinstance(device, VariableLayerThicknessComponent)
        else device.get_size()[2] * device._layer_size
    )
    while z_height < device_height:
        slice_height = device.get_position()[2] * device._layer_size + z_height
        polygons = composite_shape._object.slice(slice_height).to_polygons()
        print(
            f"slice {slice_num} at z={z_height:.4f}/{slice_height:.4f} ({len(polygons)} polygons)"
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
        img.save(f"{device_subdirectory}/slice{slice_num}.png")

        sliced_devices_info[-1]["slices"].append(
            {
                "image_name": f"slice{slice_num}.png",
                "layer_position": z_height,
            }
        )

        if isinstance(device, VariableLayerThicknessComponent):
            # If the device has variable layer thickness, use the layer size from the device
            if slice_num < len(expanded_layer_sizes) - 1:
                z_height += (
                    expanded_layer_sizes[slice_num] / 2
                    + expanded_layer_sizes[slice_num + 1] / 2
                )
            else:
                # If this is the last slice, just use the layer size
                z_height += expanded_layer_sizes[slice_num]
        else:
            z_height += device._layer_size
        slice_num += 1

    # slicing() -> images at px_size and layer_size
    # 	check if in unique_component_index
    # 		if not unique return else add to index
    # 	_loop_components()
    # 	    union bulk
    # 	    subtract shapes
    # 		if not exposure device
    # 			if layer_size is equal
    # 				_loop_components()
    # 			else:
    # 				slicing() in own directory
    # 		else:
    # 			slicing() in new directory
    # 	slice at layer_size
    # 		slice
    # 		add to index of image_name and layer position
    # 	If layers align, merge images
