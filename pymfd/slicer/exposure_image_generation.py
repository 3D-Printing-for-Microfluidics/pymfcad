import numpy as np
from PIL import Image
from pathlib import Path


from .uniqueimagestore import get_unique_path


def generate_exposure_images_from_folders(
    image_dir: Path,
    mask_dir: Path,
    settings: "ExposureSettings",
    slice_metadata: dict,
):
    slices = slice_metadata["slices"]
    for _, meta in enumerate(slices):
        name = meta["image_name"]
        image_path = image_dir / name
        mask_path = mask_dir / name
        if not mask_path.exists():
            continue

        try:
            mask = np.array(Image.open(mask_path))
        except Exception:
            continue
        if np.count_nonzero(mask) == 0:
            continue

        if meta.get("image_data") is None and not image_path.exists():
            continue
        elif meta.get("image_data") is not None:
            image = meta["image_data"]
        else:
            try:
                image = np.array(Image.open(image_path))
            except Exception:
                continue

        if np.count_nonzero(image) != 0:
            exposure_image = np.bitwise_and(image, mask)
            image = np.bitwise_and(image, np.bitwise_not(mask))

            stem = Path(name).stem
            Image.fromarray(image).save(image_path)
            meta["image_data"] = image
            if np.count_nonzero(exposure_image) != 0:
                exposure_path = get_unique_path(image_dir, stem, postfix="regional")
                if "exposure_slices" not in slice_metadata:
                    slice_metadata["exposure_slices"] = []
                slice_metadata["exposure_slices"].append(
                    {
                        "image_name": exposure_path.name,
                        "image_data": exposure_image,
                        "layer_position": meta["layer_position"],
                        "exposure_settings": settings,
                        "position_settings": meta["position_settings"],
                    }
                )
                Image.fromarray(exposure_image).save(exposure_path)
