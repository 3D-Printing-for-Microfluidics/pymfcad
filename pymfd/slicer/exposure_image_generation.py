import cv2
from pathlib import Path

from .uniqueimagestore import get_unique_path


def generate_exposure_images_from_folders(
    image_dir: Path,
    mask_dir: Path,
    settings: "ExposureSettings",
    slice_metadata: list[dict],
):
    slices = slice_metadata["slices"]
    # Loop through all slices
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

        # Check if any image or empty
        if cv2.countNonZero(image) != 0:

            exposure_image = cv2.bitwise_and(image, mask)
            image = cv2.bitwise_and(image, cv2.bitwise_not(mask))

            # Save images
            stem = Path(name).stem
            if image is not None:
                cv2.imwrite(str(image_path), image)
            if cv2.countNonZero(exposure_image) != 0:
                exposure_path = get_unique_path(image_dir, stem, postfix="regional")
                if "exposure_slices" not in slice_metadata:
                    slice_metadata["exposure_slices"] = []
                slice_metadata["exposure_slices"].append(
                    {
                        "image_name": exposure_path.name,
                        "layer_position": meta["layer_position"],
                        "exposure_settings": settings,
                        "position_settings": meta["position_settings"],
                    }
                )
                cv2.imwrite(str(exposure_path), exposure_image)
