import cv2
from pathlib import Path

from .uniqueimagestore import get_unique_path


def generate_position_images_from_folders(
    image_dir: Path,
    mask_dir: Path,
    settings: "PositionSettings",
    slice_metadata: list[dict],
):
    slices = slice_metadata["slices"]
    # Loop through all slices
    for i, meta in enumerate(slices):
        # Get image and mask
        name = meta["image_name"]
        mask_path = mask_dir / name
        if not mask_path.exists():
            continue

        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if mask is None or cv2.countNonZero(mask) == 0:
            continue

        # Check if any image or empty
        if cv2.countNonZero(mask) != 0:
            slices[i]["position_settings"] = settings
