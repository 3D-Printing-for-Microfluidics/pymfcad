import numpy as np
import re
from pathlib import Path
import cv2
import os

from .uniqueimagestore import get_unique_path


def generate_secondary_images_from_folders(
    image_dir: Path,
    mask_dir: Path,
    settings: "SecondaryDoseSettings",
    slice_metadata: dict,
):
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
    slices = slice_metadata["slices"]
    prev_images = []
    for _, meta in enumerate(slices):
        # Get image and mask
        name = meta["image_name"]
        image_path = image_dir / name
        mask_path = mask_dir / name
        if not image_path.exists() or not mask_path.exists():
            continue

        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if mask is None or cv2.countNonZero(mask) == 0:
            continue

        image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            continue

        # Add membrane images back before doing morphological operations
        membrane_images = [
            info
            for info in slice_metadata["membrane_slices"]
            if re.search(
                rf"^{re.escape(Path(name).stem)}_membrane.*\.png$", info["image_name"]
            )
        ]
        membranes = np.zeros_like(image, dtype=np.uint8)
        if len(membrane_images) > 0:
            for membrane_image in membrane_images:
                path = image_dir / membrane_image["image_name"]
                membrane_dilation_px = membrane_image["dilation_px"]
                membrane_dilation_kernel_size = 2 * membrane_dilation_px + 1
                membrane_dilation_kernel = cv2.getStructuringElement(
                    cv2.MORPH_RECT,
                    (membrane_dilation_kernel_size, membrane_dilation_kernel_size),
                )
                membrane = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
                if membrane is not None:
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

        if len(prev_images) >= layers_above:
            prev_images.pop(0)
        prev_images.append(image.copy())

        # Make bulk image
        bulk_image = cv2.bitwise_and(
            image, cv2.bitwise_not(cv2.bitwise_or(edge_image, roof_image))
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
        if cv2.countNonZero(edge_image) == 0:
            edge_image = None
        if cv2.countNonZero(roof_image) == 0:
            roof_image = None

        # Save images
        if "secondary_slices" not in slice_metadata:
            slice_metadata["secondary_slices"] = []
        stem = Path(name).stem
        if bulk_image is not None and cv2.bitwise_xor(bulk_image, image).any():
            cv2.imwrite(str(image_path), bulk_image)
        if edge_image is not None:
            edge_path = get_unique_path(image_dir, stem, postfix="edge")
            slice_metadata["secondary_slices"].append(
                {
                    "image_name": edge_path.name,
                    "layer_position": meta["layer_position"],
                    "exposure_settings": settings.edge_exposure_settings,
                    "position_settings": meta["position_settings"],
                }
            )
            cv2.imwrite(str(edge_path), edge_image)
        if roof_image is not None:
            roof_path = get_unique_path(image_dir, stem, postfix="roof")
            slice_metadata["secondary_slices"].append(
                {
                    "image_name": roof_path.name,
                    "layer_position": meta["layer_position"],
                    "exposure_settings": settings.roof_exposure_settings,
                    "position_settings": meta["position_settings"],
                }
            )
            cv2.imwrite(str(roof_path), roof_image)
