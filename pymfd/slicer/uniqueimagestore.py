import sys
import PIL
import shutil
import hashlib
import numpy as np
from PIL import Image
from pathlib import Path
from typing import NamedTuple
from collections import defaultdict


def get_unique_path(
    base_path: Path, stem: str, suffix: str = ".png", postfix: str = ""
) -> Path:
    """
    Generate a unique file path by appending optional postfix and then _n if needed.
    E.g., stem_postfix.png, stem_postfix_1.png, etc.
    """
    count = 0
    while True:
        if count == 0:
            filename = (
                f"{stem}_{postfix}{suffix}" if postfix is not "" else f"{stem}{suffix}"
            )
        else:
            filename = (
                f"{stem}_{postfix}_{count}{suffix}"
                if postfix is not ""
                else f"{stem}_{count}{suffix}"
            )
        full_path = base_path / filename
        if not full_path.exists():
            return full_path
        count += 1


def load_image_from_file(image_file):
    """Given image_file, load image as numpy array"""
    return np.array(Image.open(_ensure_path(image_file)))


def save_image_png(image_array, file):
    """Save numpy.ndarray as grayscale png image."""
    temp_img = Image.fromarray(image_array, mode="L")  # 'L'=8-bit pixels, black and white
    temp_img.save(file, format="PNG")


def hash_image(img):
    """Use sha1 for image hash."""
    assert isinstance(img, np.ndarray)
    sha1 = hashlib.sha1(img.tobytes())
    hashvalue = sha1.hexdigest()
    return hashvalue


def _ensure_path(filepath):
    """Only work with instances of Path."""
    if not isinstance(filepath, Path):
        if isinstance(filepath, str):
            filepath = Path(filepath)
        else:
            raise ValueError(f"{filepath} must be a Path or str")
    return filepath


class UniqueImageStore:
    """Store and retrieve only unique images.

    DANGER: instantiating an object will delete any existing
    directory passed to it. DO NOT PASS IT Path.cwd()!!!!
    """

    def __init__(self, image_directory):
        """image_directory is where the new unique images will be put"""

        # Only work with instances of Path
        self.image_directory = _ensure_path(image_directory)

        # Delete any pre-existing image directory and images
        self._remove_existing_dir()

        # Create fresh directory for images
        self.image_directory.mkdir()

        # Track unique images with default dict. Schema:
        # <hashvalue>: ["xx.png", "yy.png", "zz.png"]
        # The first filename is the one that will be used
        # as the unique image for all of the rest
        self.image_files = defaultdict(list)

        # Track images that have been added by storing tuple
        # (<desired image file>, <hash_value>, <actual image file>)
        self._image_history = []

    def _remove_existing_dir(self):
        if self.image_directory.exists():
            shutil.rmtree(self.image_directory)

    def add_image(self, img, filename):
        """Add an image to the image store.

        Must provide both the image and a desired file name, which is
        usually just the original slice file name. This can be provided
        as a Path or as a str.
        """

        filename = _ensure_path(filename).name

        hashvalue = hash_image(img)
        self.image_files[hashvalue].append(filename)

        if len(self.image_files[hashvalue]) == 1:
            image_file = filename
            save_image_png(img, self.image_directory / image_file)
        else:
            image_file = self.get_image_file(hashvalue)

        self._image_history.append((filename, hashvalue, image_file))
        return Path(image_file)

    def get_image_file(self, hashvalue):
        """Retrieve image file based on hash value"""
        return self.image_files[hashvalue][0]

    def get_image(self, hashvalue):
        """Retrieve image based on hash value"""
        full_file_name = self.image_directory / self.get_image_file(hashvalue)
        return load_image_from_file(full_file_name)

    @property
    def num_original_images(self):
        return len(self._image_history)

    @property
    def num_unique_images(self):
        return len(self.image_files)

    def __repr__(self):
        return f"UniqueImageStore({repr(self.image_directory)})"
