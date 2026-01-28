from __future__ import annotations

from pathlib import Path
import re

import cv2
import numpy as np
from PIL import Image

from .uniqueimagestore import get_unique_path
from ..backend import rle_encode_packed, rle_decode_packed, rle_is_all_zeros, rle_is_all_non_zeros

def get_slice_list_from_data(
    data: dict,
) -> list[dict]:
    """Get slice list from slice data."""
    return data["slices"]

def get_mask_list_from_data(
    data: dict,
    mask_key: str,
) -> list[dict] | None:
    """Get mask list from slice data."""
    if "masks" in data and mask_key in data["masks"]:
        return data["masks"][mask_key]
    return None

def get_slice(
    slice_data: list[dict],
    invert_check: bool = False,
) -> dict | None:
    image = slice_data.get("image_data")
    if image is not None:
        if invert_check and not rle_is_all_non_zeros(image[0]):
            return rle_decode_packed(*image)
        elif not invert_check and not rle_is_all_zeros(image[0]):
            return rle_decode_packed(*image)
    return None

def get_mask_from_masks_data(
    masks_data: list[dict],
    image_name: str,
) -> np.ndarray | None:
    """Get mask from slice data."""
    for mask_info in masks_data:
        if mask_info["image_name"] == image_name:
            if not rle_is_all_zeros(mask_info["image_data"][0]):
                return rle_decode_packed(*mask_info["image_data"])
    return None

def generate_position_images_from_folders(
    data: list[dict],
    mask_key: str,
    settings: "PositionSettings",
):
    """Generate position images from existing image and mask folders."""
    slices = get_slice_list_from_data(data)
    masks = get_mask_list_from_data(data, mask_key)
    if masks is None:
        return
    
    for i, meta in enumerate(slices):
        mask = get_mask_from_masks_data(masks, meta["image_name"])
        if mask is not None:
            slices[i]["position_settings"] = settings

def generate_exposure_images_from_folders(
    data: dict,
    image_dir: Path,
    mask_key: str,
    settings: "ExposureSettings",
    save_temp_files: bool = False,
):
    """Generate exposure images from existing image and mask folders."""
    slices = get_slice_list_from_data(data)
    masks = get_mask_list_from_data(data, mask_key)
    if masks is None:
        return
    for _, meta in enumerate(slices):
        # get image and mask
        name = meta["image_name"]
        mask = get_mask_from_masks_data(masks, name)
        if mask is None:
            continue

        image = get_slice(meta)
        if image is None:
            continue

        # make exposure image
        exposure_image = np.bitwise_and(image, mask)
        image = np.bitwise_and(image, np.bitwise_not(mask))

        # save images and update metadata
        stem = Path(name).stem
        if save_temp_files:
            image_path = image_dir / name
            print(f"\t\tOverwriting image at {image_path.name} without exposure region")
            Image.fromarray(image).save(image_path)
        meta["image_data"] = rle_encode_packed(image)

        # save exposure image if not empty
        if np.count_nonzero(exposure_image) != 0:
            exposure_path = get_unique_path(image_dir, stem, postfix="regional")
            if "exposure_slices" not in data:
                data["exposure_slices"] = []
            data["exposure_slices"].append(
                {
                    "image_name": exposure_path.name,
                    "image_data": rle_encode_packed(exposure_image),
                    "layer_position": meta["layer_position"],
                    "exposure_settings": settings,
                    "position_settings": meta["position_settings"],
                }
            )
            if save_temp_files:
                print(f"\t\tSaving exposure image to {exposure_path.name}")
                Image.fromarray(exposure_image).save(exposure_path)


def generate_membrane_images_from_folders(
    data: dict,
    image_dir: Path,
    mask_key: str,
    membrane_settings: "MembraneSettings",
    save_temp_files: bool = False,
):
    """Generate membrane images from existing image and mask folders."""
    slices = get_slice_list_from_data(data)
    masks = get_mask_list_from_data(data, mask_key)
    if masks is None:
        return

    membrane_thickness_um = membrane_settings.max_membrane_thickness_um
    dilation_px = membrane_settings.dilation_px

    dilation_kernel_size = 2 * dilation_px + 1
    dilation_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (dilation_kernel_size, dilation_kernel_size)
    )

    opening_kernel_size = 3
    opening_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (opening_kernel_size, opening_kernel_size)
    )

    # loop through all slices
    for i in range(len(slices)):
        # Figure out how many slices are in membrane thickness
        prev_image_index = 0
        delta_z = 0
        for prev_image_index in range(len(slices[:i])):
            delta_z = abs(
                slices[i]["layer_position"] - slices[prev_image_index]["layer_position"]
            )
            if abs(delta_z - membrane_thickness_um) < 0.01:  # 0.01 um tolerance
                break
        if abs(delta_z - membrane_thickness_um) > 0.01:  # 0.01 um tolerance
            continue

        # make images
        next_image_index = i + 1
        for j in range(prev_image_index + 1, next_image_index):
            curr_name = slices[j]["image_name"]
            mask = get_mask_from_masks_data(masks, curr_name)
            if mask is None:
                continue
            image = get_slice(slices[j])
            if image is None:
                continue

            if prev_image_index < 0:
                prev_image = np.zeros_like(image, dtype=np.uint8)
            else:
                prev_image = get_slice(slices[prev_image_index], invert_check=True)
                if prev_image is None:
                    continue

            if next_image_index >= len(slices):
                next_image = np.zeros_like(image, dtype=np.uint8)
            else:
                next_image = get_slice(slices[next_image_index], invert_check=True)
                if next_image is None:
                    continue
            
            # make mask where both prev and next images are black and mask is white
            tmp = cv2.bitwise_and(
                cv2.bitwise_not(prev_image),
                cv2.bitwise_not(next_image),
            )
            mask = cv2.bitwise_and(tmp, mask)

            masked_membrane = cv2.bitwise_and(image, mask)
            masked_membrane = cv2.morphologyEx(
                masked_membrane, cv2.MORPH_OPEN, opening_kernel
            )

            if cv2.countNonZero(masked_membrane) == 0:
                continue

            image_minus_membrane = image - masked_membrane
            dilated_membrane = cv2.dilate(masked_membrane, dilation_kernel)

            # Overwrite original image
            if save_temp_files:
                curr_path = image_dir / curr_name
                print(f"\t\tOverwriting image at {curr_path.name} without membrane")
                cv2.imwrite(str(curr_path.resolve()), image_minus_membrane)
            slices[j]["image_data"] = rle_encode_packed(image_minus_membrane)

            # Write dilated membrane
            stem = Path(curr_name).stem
            membrane_output_path = get_unique_path(image_dir, stem, postfix="membrane")
            if "membrane_slices" not in data:
                data["membrane_slices"] = []
            data["membrane_slices"].append(
                {
                    "image_name": membrane_output_path.name,
                    "image_data": rle_encode_packed(dilated_membrane),
                    "layer_position": slices[j]["layer_position"],
                    "exposure_settings": membrane_settings.exposure_settings,
                    "dilation_px": dilation_px,
                    "position_settings": slices[j]["position_settings"],
                }
            )
            if save_temp_files:
                print(f"\t\tSaving membrane image to {membrane_output_path.name}")
                cv2.imwrite(str(membrane_output_path), dilated_membrane)

def generate_secondary_images_from_folders(
    data: dict,
    image_dir: Path,
    mask_key: str,
    settings: "SecondaryDoseSettings",
    save_temp_files: bool = False,
):
    """Generate secondary images from existing image and mask folders."""
    # Primary (trivial) case
    # 1. Edge == Roof == Bulk -> D

    # Secondary does cases
    # 1. Roof == Bulk
    #   a. Edge < Bulk -> D, E
    #   b. Edge > Bulk -> D, D-E
    # 2. Edge == Bulk
    #   a. Roof < Bulk -> D, R
    #   b. Roof > Bulk -> D, D-R
    # 3. Edge == Roof
    #   a. Edge < Bulk -> D, E&R
    #   b. Edge > Bulk -> D, D-(E&R)

    # Tertiary dose cases
    # 1. Bulk > Edge > Roof -> D, R, E&R
    # 2. Bulk > Roof > Edge -> D, E, E&R
    # 3. Edge > Bulk > Roof -> D, R, (D-E)&R
    # 4. Roof > Bulk > Edge -> D, E, (D-R)&E
    # 5. Edge > Roof > Bulk -> D, D-(E&R), (D-E)&R
    # 6. Roof > Edge > Bulk -> D, D-(E&R), (D-R)&E

    # i[0] = image
    # i[-1] = previous image
    # D = Dilated
    # E = Eroded
    # R = Roof -> D - (i[0] - (i[-1] & i[-2] & ...))

    # Extract settings
    edge_dose = settings.edge_exposure_settings.exposure_time
    erosion_px = settings.edge_erosion_px
    dilation_px = settings.edge_dilation_px

    roof_dose = settings.roof_exposure_settings.exposure_time
    roof_erosion_px = settings.roof_erosion_px
    layers_above = settings.roof_layers_above

    # Create kernels for morphological operations
    erosion_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (2 * erosion_px + 1, 2 * erosion_px + 1)
    )
    dilation_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (2 * dilation_px + 1, 2 * dilation_px + 1)
    )
    roof_erosion_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (2 * roof_erosion_px + 1, 2 * roof_erosion_px + 1)
    )

    # Loop through all slices
    slices = get_slice_list_from_data(data)
    masks = get_mask_list_from_data(data, mask_key)
    prev_images = []
    for _, meta in enumerate(slices):
        # Get image and mask
        name = meta["image_name"]
        image = get_slice(meta)
        if image is None:
            continue
        mask = get_mask_from_masks_data(masks, name)
        if mask is None:
            continue

        # Add membrane images back before doing morphological operations
        membrane_images = [
            info
            for info in data.get("membrane_slices", [])
            if re.search(
                rf"^{re.escape(Path(name).stem)}_membrane.*\.png$", info["image_name"]
            )
        ]
        membranes = np.zeros_like(image, dtype=np.uint8)
        if len(membrane_images) > 0:
            for membrane_image in membrane_images:
                membrane_dilation_px = membrane_image["dilation_px"]
                membrane_dilation_kernel_size = 2 * membrane_dilation_px + 1
                membrane_dilation_kernel = cv2.getStructuringElement(
                    cv2.MORPH_RECT,
                    (membrane_dilation_kernel_size, membrane_dilation_kernel_size),
                )
                membrane = membrane_image["image_data"]
                og_membrane = cv2.erode(membrane, membrane_dilation_kernel)
                membranes = cv2.bitwise_or(membranes, og_membrane)

        # Preform morphological operations
        eroded = cv2.erode(cv2.bitwise_or(image, membranes), erosion_kernel)
        dilated = cv2.dilate(cv2.bitwise_or(image, membranes), dilation_kernel)
        eroded = cv2.bitwise_and(eroded, cv2.bitwise_not(membranes))
        dilated = cv2.bitwise_and(dilated, cv2.bitwise_not(membranes))

        # Make edge image
        edge_image = cv2.bitwise_and(dilated, cv2.bitwise_not(eroded))

        # Make roof image
        roof_image = None
        if layers_above > 0:
            roof_image = np.full_like(image, 255, dtype=np.uint8)
            for prev_image in prev_images:
                eroded_prev = cv2.erode(prev_image, roof_erosion_kernel)
                roof_image = cv2.bitwise_and(roof_image, eroded_prev)

            roof_eroded = cv2.erode(image, roof_erosion_kernel)
            roof_image = (
                cv2.bitwise_and(
                    roof_eroded, cv2.bitwise_not(cv2.bitwise_or(roof_image, membranes))
                )
                if membranes is not None
                else cv2.bitwise_and(roof_eroded, cv2.bitwise_not(roof_image))
            )

        if len(prev_images) >= layers_above and layers_above > 0:
            prev_images.pop(0)
        if layers_above > 0:
            prev_images.append(image.copy())

        # Make bulk image
        bulk_image = cv2.bitwise_and(
            image,
            cv2.bitwise_not(
                cv2.bitwise_or(
                    edge_image,
                    roof_image if roof_image is not None else np.zeros_like(image),
                )
            ),
        )

        if roof_dose is None and edge_dose is None:
            continue
        elif edge_dose is None:
            edge_image = None
        elif roof_dose is None:
            roof_image = None
        elif edge_dose >= roof_dose:
            edge_image = cv2.bitwise_and(edge_image, cv2.bitwise_not(roof_image))
        else:
            roof_image = cv2.bitwise_and(roof_image, cv2.bitwise_not(edge_image))

        # Calculate masked bulk
        outside = cv2.bitwise_and(image, image, mask=cv2.bitwise_not(mask))
        inside = cv2.bitwise_and(bulk_image, bulk_image, mask=mask)
        bulk_image = cv2.add(outside, inside)

        # Calculate masked edge and roof
        if edge_image is not None:
            edge_image = cv2.bitwise_and(edge_image, mask)
        if roof_image is not None:
            roof_image = cv2.bitwise_and(roof_image, mask)

        # Check if any image is None or empty
        if cv2.countNonZero(bulk_image) == 0:
            bulk_image = None
        if edge_image is not None and cv2.countNonZero(edge_image) == 0:
            edge_image = None
        if roof_image is not None and cv2.countNonZero(roof_image) == 0:
            roof_image = None

        # Save images
        if "secondary_slices" not in data:
            data["secondary_slices"] = []
        stem = Path(name).stem
        if bulk_image is not None and cv2.bitwise_xor(bulk_image, image).any():
            meta["image_data"] = rle_encode_packed(bulk_image)
            if save_temp_files:
                image_path = image_dir / name
                print(f"\t\tOverwriting image at {image_path.name} without secondary regions")
                cv2.imwrite(str(image_path), bulk_image)
        if edge_image is not None:
            edge_path = get_unique_path(image_dir, stem, postfix="edge")
            data["secondary_slices"].append(
                {
                    "image_name": edge_path.name,
                    "image_data": rle_encode_packed(edge_image),
                    "layer_position": meta["layer_position"],
                    "exposure_settings": settings.edge_exposure_settings,
                    "position_settings": meta["position_settings"],
                }
            )
            if save_temp_files:
                print(f"\t\tSaving edge image to {edge_path.name}")
                cv2.imwrite(str(edge_path), edge_image)
        if roof_image is not None:
            roof_path = get_unique_path(image_dir, stem, postfix="roof")
            data["secondary_slices"].append(
                {
                    "image_name": roof_path.name,
                    "image_data": rle_encode_packed(roof_image),
                    "layer_position": meta["layer_position"],
                    "exposure_settings": settings.roof_exposure_settings,
                    "position_settings": meta["position_settings"],
                }
            )
            if save_temp_files:
                print(f"\t\tSaving roof image to {roof_path.name}")
                cv2.imwrite(str(roof_path), roof_image)
