from __future__ import annotations

import pytest

from pymfcad import Component, PositionSettings, SqueezeOutResin
from pymfcad.backend import Color, Cube
from pymfcad.backend.slice import slice_component


def _build_parent_component(size=(40, 30, 20)) -> Component:
    comp = Component(size=size, quiet=True)
    comp.add_label("device", Color.from_name("gray", 255))
    comp.add_label("fluidic", Color.from_name("blue", 255))
    return comp


@pytest.mark.mesh
def test_component_slicing(tmp_path):
    comp = _build_parent_component()
    comp._name = "test_component"

    # Should raise an error if no bulks are defined
    with pytest.raises(RuntimeError, match="Tried to slice component without bulk shape"):
        slice_component(comp, None, [], [])

    comp.add_bulk("device_bulk", Cube(size=(40, 30, 20), center=False), label="device")

    slice_component(comp, None, [], [])

    # Create a temporary directory to store the slices
    output_dir = tmp_path / "slices"
    output_dir.mkdir()
    # Add a regional setting so masks will be generated
    from pymfcad import ExposureSettings

    comp.add_regional_settings(
        "regional_test",
        Cube(size=(40, 30, 20), center=False),
        ExposureSettings(),
        "fluidic",
    )

    slice_component(comp, output_dir, [], [])

    # Check that subdirectory (FQN) was created
    subdir = output_dir / "test_component"
    assert (
        subdir.exists() and subdir.is_dir()
    ), "Subdirectory for component was not created"

    # Check that mask directory was created
    mask_dir = output_dir / "masks"
    assert mask_dir.exists() and mask_dir.is_dir(), "Mask directory was not created"
    mask_subdir = mask_dir / "test_component"
    assert (
        mask_subdir.exists() and mask_subdir.is_dir()
    ), "Subdirectory for component masks was not created"
    masks_regional_dir = mask_subdir / "regional_test"
    assert (
        masks_regional_dir.exists() and masks_regional_dir.is_dir()
    ), "Subdirectory for regional masks was not created"

    # Check that slices and mask slices were created for each layer
    for layer in range(20):
        slice_path = subdir / f"test_component-slice{layer:04d}.png"
        assert slice_path.exists(), f"Slice image for layer {layer} was not created"
        mask_slice_path = masks_regional_dir / f"test_component-slice{layer:04d}.png"
        assert (
            mask_slice_path.exists()
        ), f"Mask slice image for layer {layer} was not created"


def test_special_layer_techniques_are_serialized():
    settings = PositionSettings(
        special_layer_techniques=[
            SqueezeOutResin(enabled=True, count=2, squeeze_force=5.0, squeeze_time=200.0)
        ]
    )

    payload = settings.to_dict()

    assert (
        payload["Special layer techniques"]["Squeeze out resin"]["Enable squeeze"] is True
    )
    assert payload["Special layer techniques"]["Squeeze out resin"]["Squeeze count"] == 2
