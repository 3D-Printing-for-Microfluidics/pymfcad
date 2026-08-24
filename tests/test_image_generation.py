from __future__ import annotations

import pytest
from pathlib import Path

from pymfcad import Component
from pymfcad.backend import Color, Cube

from pymfcad.print_file_gen import (
    ExposureSettings,
    LightEngine,
    PositionSettings,
    Printer,
    ResinType,
    PrintFileGenerator,
    MembraneSettings,
    SecondaryDoseSettings,
)


def _build_parent_component() -> Component:
    comp = Component(size=(20, 20, 40), px_size=0.01, layer_size=0.01)
    comp.add_label("device", Color.from_name("gray", 255))
    comp.add_label("fluidic", Color.from_name("blue", 255))
    return comp


def _build_settings() -> Settings:
    resin = ResinType(
        bulk_exposure=100.0,
        exposure_offset=10.0,
        monomer=[("PEG", 100.0)],
        uv_absorbers=[("NPS", 2.0)],
        initiators=[("IRG", 1.0)],
        additives=[],
    )

    light_engine = LightEngine(
        name="test_engine",
        px_size=0.01,
        px_count=(20, 20),
        wavelengths=[365],
        grayscale_available=[False],
    )
    printer = Printer(name="TestPrinter", light_engines=[light_engine])

    return resin, printer


@pytest.mark.fast
def test_image_generation_with_saving(tmp_path):
    comp = _build_parent_component()
    resin, printer = _build_settings()

    comp.add_bulk("bulk", Cube(size=(20, 20, 40)), label="device")
    comp.add_void("void1", Cube(size=(5, 5, 1)).translate((2, 2, 1)), label="fluidic")
    comp.add_void("void3", Cube(size=(5, 5, 2)).translate((2, 2, 34)), label="fluidic")
    comp.add_void("void4", Cube(size=(5, 5, 2)).translate((2, 2, 37)), label="fluidic")
    comp.add_regional_settings(
        "membrane1",
        Cube(size=(10, 10, 1)).translate((0, 0, 0)),
        label="fluidic",
        settings=MembraneSettings(max_membrane_thickness_um=10),
    )
    comp.add_regional_settings(
        "membrane2",
        Cube(size=(10, 10, 1)).translate((0, 0, 5)),
        label="fluidic",
        settings=MembraneSettings(max_membrane_thickness_um=10),
    )
    comp.add_regional_settings(
        "membrane3",
        Cube(size=(10, 10, 3)).translate((0, 0, 35)),
        label="fluidic",
        settings=MembraneSettings(max_membrane_thickness_um=10),
    )
    comp.add_regional_settings(
        "membrane4",
        Cube(size=(10, 10, 1)).translate((0, 0, 39)),
        label="fluidic",
        settings=MembraneSettings(max_membrane_thickness_um=10),
    )

    comp.add_void("void5", Cube(size=(5, 5, 1)).translate((2, 2, 17)), label="fluidic")
    comp.add_void("void6", Cube(size=(5, 5, 2)).translate((2, 2, 19)), label="fluidic")
    comp.add_regional_settings(
        "membrane5",
        Cube(size=(10, 10, 1)).translate((0, 0, 18)),
        label="fluidic",
        settings=MembraneSettings(max_membrane_thickness_um=10),
    )
    comp.add_regional_settings(
        "secondary_dose",
        Cube(size=(10, 10, 9)).translate((0, 0, 13)),
        label="fluidic",
        settings=SecondaryDoseSettings(
            edge_bulk_exposure_multiplier=1.5,
            edge_erosion_px=1,
            edge_dilation_px=1,
            roof_bulk_exposure_multiplier=2.0,
            roof_erosion_px=1,
            roof_layers_above=1,
        ),
    )
    comp.add_regional_settings(
        "exposure_override",
        Cube(size=(10, 10, 1)).translate((0, 0, 24)),
        label="fluidic",
        settings=ExposureSettings(bulk_exposure_multiplier=0.5),
    )
    comp.add_regional_settings(
        "position_override",
        Cube(size=(10, 10, 1)).translate((0, 0, 27)),
        label="fluidic",
        settings=PositionSettings(distance_up=2.0),
    )

    comp.preview()

    slicer = PrintFileGenerator(
        filename=tmp_path / "out",
        author="tester",
        purpose="unit-test",
        description="settings roundtrip",
        component=comp,
        printer=printer,
        resin=resin,
        zip_output=False,
    )
    slicer.run(save_temp_files=True)
