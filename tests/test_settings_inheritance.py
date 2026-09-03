import pytest

from pymfcad import Component
from pymfcad.backend import Color, Cube
from pymfcad.print_file_gen import (
    ExposureSettings,
    LightEngine,
    PositionSettings,
    Printer,
    PrintFileGenerator,
    ResinType,
)


def _generator() -> PrintFileGenerator:
    return PrintFileGenerator(
        filename="unused",
        workspaces=[],
        printer=Printer(name="test", light_engines=[LightEngine()]),
        resin=ResinType(bulk_exposure=100),
    )


def _settings_info() -> dict:
    return {"slices": [{"layer_position": 0.0}]}


def test_child_settings_keep_priority_by_default():
    parent = Component(size=(10, 10, 10), quiet=True)
    child = Component(size=(5, 5, 5), quiet=True)
    parent.add_subcomponent("child", child)
    parent.default_exposure_settings = ExposureSettings(power_setting=25)
    parent.default_position_settings = PositionSettings(distance_up=2)
    child.default_exposure_settings = ExposureSettings(power_setting=75)
    child.default_position_settings = PositionSettings(distance_up=3)

    _generator()._fill_component_default_settings(child, _settings_info())

    assert child.default_exposure_settings.power_setting == 75
    assert child.default_position_settings.distance_up == 3


def test_use_parent_settings_child_defaults_and_regional_values():
    parent = Component(size=(10, 10, 10), quiet=True)
    child = Component(size=(5, 5, 5), quiet=True, use_parent_settings=True)
    parent.add_subcomponent("child", child)
    parent.default_exposure_settings = ExposureSettings(power_setting=25)
    parent.default_position_settings = PositionSettings(distance_up=2)
    _generator()._fill_component_default_settings(child, _settings_info())

    assert child.default_exposure_settings.power_setting == 25
    assert child.default_position_settings.distance_up == 2

    with pytest.raises(ValueError):
        child.add_default_exposure_settings(ExposureSettings(power_setting=75))
    with pytest.raises(ValueError):
        child.add_default_position_settings(PositionSettings(distance_up=3))
    with pytest.raises(ValueError):
        child.add_regional_settings(
            "local_region",
            Cube(size=(1, 1, 1)),
            ExposureSettings(power_setting=75),
            "child.region",
        )
    with pytest.raises(ValueError):
        child.set_burn_in_exposure([200.0])


def test_parent_region_is_materialized_on_child_and_clipped_to_child_bbox():
    parent = Component(size=(10, 10, 10), quiet=True)
    child = Component(size=(4, 4, 4), quiet=True, use_parent_settings=True)
    child.translate((3, 3, 3))
    parent.add_subcomponent("child", child)
    parent.add_label("region", Color.from_name("red", 255))
    parent.add_regional_settings(
        "region_settings",
        Cube(size=(3, 3, 3)).translate((1, 1, 1)),
        ExposureSettings(power_setting=25),
        "region",
    )

    inherited = child.regional_settings["_inherited_region_settings"]
    inherited_shape, inherited_settings = inherited

    assert tuple(round(value, 6) for value in inherited_shape._object.bounding_box()) == (
        3,
        3,
        3,
        4,
        4,
        4,
    )
    assert inherited_settings.power_setting == 25


def test_parent_burnin_is_trimmed_to_child_start_layer():
    parent = Component(size=(10, 10, 20), quiet=True)
    child_at_last_burnin_layer = Component(
        size=(2, 2, 2), quiet=True, use_parent_settings=True
    ).translate((0, 0, 2))
    child_after_burnin = Component(
        size=(2, 2, 2), quiet=True, use_parent_settings=True
    ).translate((4, 0, 10))
    parent.add_subcomponent("last_burnin", child_at_last_burnin_layer)
    parent.add_subcomponent("after_burnin", child_after_burnin)

    parent.set_burn_in_exposure([100.0, 200.0, 300.0])

    assert child_at_last_burnin_layer.burnin_settings == [300.0]
    assert child_after_burnin.burnin_settings == []
