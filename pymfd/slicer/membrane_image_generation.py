from __future__ import annotations

from pathlib import Path
import numpy as np
import cv2

from .uniqueimagestore import get_unique_path


def generate_membrane_images_from_folders(
    image_dir: Path,
    mask_dir: Path,
    membrane_settings: "MembraneSettings",
    slice_metadata: dict,
):
    slices = slice_metadata["slices"]

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
        # Skip the first slice (membrane needs to be sandwiched by black pixels)
        if i == 0:
            continue

        # Skip the last slice (position only) and the second to last slice (membrane needs to be sandwiched by black pixels)
        if i > len(slices) - 1:
            continue

        # Figure out how many slices are in membrane thickness
        prev_image_index = 0
        delta_z = 0
        for prev_image_index in range(len(slices[:i])):
            delta_z = abs(
                slices[i]["layer_position"] - slices[prev_image_index]["layer_position"]
            )
            if abs(delta_z - membrane_thickness_um * 1000) < 0.01:  # 0.01 um tolerance
                break
        if abs(delta_z - membrane_thickness_um * 1000) > 0.01:  # 0.01 um tolerance
            continue

        # make images
        next_image_index = i + 1
        for j in range(prev_image_index + 1, next_image_index):
            # get current/mask image
            curr_name = slices[j]["image_name"]
            curr_path = image_dir / curr_name
            curr_mask_path = mask_dir / curr_name
            if not curr_path.exists() or not curr_mask_path.exists():
                continue
            mask = cv2.imread(str(curr_mask_path.resolve()), 0)
            if mask is None or cv2.countNonZero(mask) == 0:
                continue  # Skip if mask is completely black
            image = cv2.imread(str(curr_path.resolve()), 0)
            if image is None:
                continue

            # Get previous image
            prev_name = slices[prev_image_index]["image_name"]
            prev_path = image_dir / prev_name
            if not prev_path.exists():
                continue
            prev_image = cv2.imread(str(prev_path.resolve()), 0)
            if prev_image is None:
                continue

            if next_image_index >= len(slices):
                next_image = np.zeros_like(image, dtype=np.uint8)
            else:
                next_name = slices[next_image_index]["image_name"]
                next_path = image_dir / next_name
                if not next_path.exists():
                    continue
                next_image = cv2.imread(str(next_path.resolve()), 0)
                if next_image is None:
                    continue

            mask = cv2.bitwise_and(
                cv2.bitwise_not(prev_image),
                cv2.bitwise_not(mask),
            )
            mask = cv2.bitwise_and(
                cv2.bitwise_not(next_image),
                cv2.bitwise_not(mask),
            )

            masked_membrane = cv2.bitwise_and(image, mask)
            masked_membrane = cv2.morphologyEx(
                masked_membrane, cv2.MORPH_OPEN, opening_kernel
            )

            if cv2.countNonZero(masked_membrane) == 0:
                continue

            image_minus_membrane = image - masked_membrane
            dilated_membrane = cv2.dilate(masked_membrane, dilation_kernel)

            # Overwrite original image
            cv2.imwrite(str(curr_path.resolve()), image_minus_membrane)

            # Write dilated membrane
            stem = Path(curr_name).stem
            membrane_output_path = get_unique_path(image_dir, stem, postfix="membrane")
            if "membrane_slices" not in slice_metadata:
                slice_metadata["membrane_slices"] = []
            slice_metadata["membrane_slices"].append(
                {
                    "image_name": membrane_output_path.name,
                    "layer_position": slices[j]["layer_position"],
                    "exposure_settings": membrane_settings.exposure_settings,
                    "dilation_px": dilation_px,
                    "position_settings": slices[j]["position_settings"],
                }
            )
            print(f"\tSaving membrane image to {membrane_output_path.name}")
            cv2.imwrite(str(membrane_output_path), dilated_membrane)
