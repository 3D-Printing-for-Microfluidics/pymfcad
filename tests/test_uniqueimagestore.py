from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from openmfd.slicer.uniqueimagestore import (
    UniqueImageStore,
    _ensure_path,
    get_unique_path,
    hash_image,
    load_image_from_file,
)


def test_get_unique_path(tmp_path: Path):
    base = tmp_path
    first = get_unique_path(base, "slice", ".png")
    assert first.name == "slice.png"
    first.write_bytes(b"x")

    second = get_unique_path(base, "slice", ".png")
    assert second.name == "slice_1.png"

    with_postfix = get_unique_path(base, "slice", ".png", postfix="a")
    assert with_postfix.name == "slice_a.png"


def test_ensure_path_accepts_path_and_str(tmp_path: Path):
    path = _ensure_path(tmp_path)
    assert isinstance(path, Path)

    path_str = _ensure_path(str(tmp_path))
    assert isinstance(path_str, Path)

    with pytest.raises(ValueError):
        _ensure_path(123)


def test_unique_image_store_dedup_and_history(tmp_path: Path):
    store_dir = tmp_path / "images"
    store = UniqueImageStore(store_dir)

    img_a = np.zeros((4, 4), dtype=np.uint8)
    img_b = np.zeros((4, 4), dtype=np.uint8)
    img_c = np.full((4, 4), 255, dtype=np.uint8)

    file_a = store.add_image(img_a, "a.png")
    file_b = store.add_image(img_b, "b.png")
    file_c = store.add_image(img_c, "c.png")

    assert file_a.name == "a.png"
    assert file_b.name == "a.png"
    assert file_c.name == "c.png"

    assert store.num_original_images == 3
    assert store.num_unique_images == 2

    loaded = load_image_from_file(store.image_directory / "a.png")
    assert np.array_equal(loaded, img_a)


def test_unique_image_store_get_image(tmp_path: Path):
    store = UniqueImageStore(tmp_path / "images")
    img = np.full((3, 3), 123, dtype=np.uint8)
    store.add_image(img, "img.png")
    h = hash_image(img)
    loaded = store.get_image(h)
    assert np.array_equal(loaded, img)


def test_unique_image_store_removes_existing_dir(tmp_path: Path):
    existing = tmp_path / "existing"
    existing.mkdir()
    (existing / "old.png").write_bytes(b"old")

    store = UniqueImageStore(existing)
    assert store.image_directory.exists()
    assert not (existing / "old.png").exists()


def test_unique_image_store_repr(tmp_path: Path):
    store = UniqueImageStore(tmp_path / "store")
    assert "UniqueImageStore" in repr(store)
