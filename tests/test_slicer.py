from __future__ import annotations

from pathlib import Path

import pytest

from pymfcad.print_file_gen import (
    ExposureSettings,
    LightEngine,
    PositionSettings,
    PrintOnFilm,
    PrintUnderVacuum,
    Printer,
    ResinType,
    Settings,
    Slicer,
    SqueezeOutResin,
    ZeroMicronLayer,
)


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
        name="visitech",
        px_size=0.0076,
        px_count=(2560, 1600),
        wavelengths=[365],
        grayscale_available=[False],
    )
    printer = Printer(name="TestPrinter", light_engines=[light_engine])

    position = PositionSettings(
        special_layer_techniques=[SqueezeOutResin(enabled=True, count=2, squeeze_force=1.0, squeeze_time=5.0)]
    )
    exposure = ExposureSettings(
        special_image_techniques=[ZeroMicronLayer(enabled=True, count=1), PrintOnFilm(enabled=True, distance_up_mm=0.2)]
    )

    return Settings(
        printer=printer,
        resin=resin,
        default_position_settings=position,
        default_exposure_settings=exposure,
        special_print_techniques=[PrintUnderVacuum(enabled=True, target_vacuum_level_torr=12.0, vacuum_wait_time=5.0)],
        user="tester",
        purpose="unit-test",
        description="settings roundtrip",
    )


def test_settings_defaults_and_roundtrip():
    settings = _build_settings()

    assert settings.default_position_settings.distance_up == pytest.approx(1.0)
    assert settings.default_position_settings.up_speed == pytest.approx(25.0)
    assert settings.default_position_settings.down_speed == pytest.approx(20.0)

    assert settings.default_exposure_settings.grayscale_correction is False
    assert settings.default_exposure_settings.bulk_exposure_multiplier == pytest.approx(1.0)
    assert settings.default_exposure_settings.power_setting == 100
    assert settings.default_exposure_settings.wavelength == 365

    data = settings.to_dict()
    reloaded = Settings.from_dict(data)

    assert reloaded.resin.to_dict() == settings.resin.to_dict()
    assert reloaded.printer.to_dict() == settings.printer.to_dict()
    assert reloaded.default_position_settings == settings.default_position_settings
    assert reloaded.default_exposure_settings == settings.default_exposure_settings


def test_printer_light_engine_selection():
    le_1 = LightEngine(name="A", px_size=0.0076, px_count=(2560, 1600), wavelengths=[365])
    le_2 = LightEngine(name="B", px_size=0.0152, px_count=(2560, 1600), wavelengths=[365])
    printer = Printer(name="Printer", light_engines=[le_1, le_2])

    selected = printer._get_light_engine(0.0152, 365)
    assert selected.name == "B"


def test_slicer_output_checks(tmp_path):
    slicer_zip = Slicer(device=None, settings={}, filename="out", zip_output=True)
    zip_path = tmp_path / "output"
    (tmp_path / "output.zip").write_bytes(b"zip")
    assert slicer_zip._check_output_exists(str(zip_path)) is True

    slicer_dir = Slicer(device=None, settings={}, filename="out", zip_output=False)
    dir_path = tmp_path / "output_dir"
    dir_path.mkdir()
    assert slicer_dir._check_output_exists(str(dir_path)) is True


def test_slicer_temp_directory_creation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    slicer = Slicer(device=None, settings={}, filename="out", zip_output=True)
    temp_dir = slicer._generate_temp_directory()
    assert temp_dir.exists()
    assert temp_dir.is_dir()
