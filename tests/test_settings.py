from __future__ import annotations

from pathlib import Path

import pytest

from pymfcad.print_file_gen import (
	ExposureSettings,
	LightEngine,
	MembraneSettings,
	PositionSettings,
	PrintOnFilm,
	PrintUnderVacuum,
	Printer,
	ResinType,
	SecondaryDoseSettings,
	Settings,
	SqueezeOutResin,
	ZeroMicronLayer,
)


def _build_settings() -> Settings:
	resin = ResinType(
		bulk_exposure=120.0,
		exposure_offset=5.0,
		monomer=[("PEG", 100.0)],
		uv_absorbers=[("NPS", 2.0)],
		initiators=[("IRG", 1.0)],
		additives=[("TEMPOL", 0.02)],
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
		distance_up=2.0,
		special_layer_techniques=[
			SqueezeOutResin(enabled=True, count=1, squeeze_force=1.2, squeeze_time=3.0)
		],
	)
	exposure = ExposureSettings(
		bulk_exposure_multiplier=1.1,
		special_image_techniques=[
			ZeroMicronLayer(enabled=True, count=2),
			PrintOnFilm(enabled=True, distance_up_mm=0.2),
		],
	)
	return Settings(
		printer=printer,
		resin=resin,
		default_position_settings=position,
		default_exposure_settings=exposure,
		special_print_techniques=[
			PrintUnderVacuum(
				enabled=True, target_vacuum_level_torr=12.0, vacuum_wait_time=5.0
			)
		],
		user="tester",
		purpose="unit-test",
		description="settings roundtrip",
	)


def test_position_settings_copy_and_equality():
	original = PositionSettings(
		distance_up=2.0,
		special_layer_techniques=[
			SqueezeOutResin(enabled=True, count=1, squeeze_force=1.2, squeeze_time=3.0)
		],
	)
	copied = original.copy()

	assert copied == original

	copied.distance_up = 3.0
	assert copied != original

	copied.special_layer_techniques.append(SqueezeOutResin(enabled=False, count=0))
	assert len(original.special_layer_techniques) == 1


def test_exposure_settings_copy_and_equality():
	original = ExposureSettings(
		bulk_exposure_multiplier=1.2,
		power_setting=80,
		special_image_techniques=[
			ZeroMicronLayer(enabled=True, count=1),
			PrintOnFilm(enabled=True, distance_up_mm=0.1),
		],
	)
	copied = original.copy()

	assert copied == original

	copied.power_setting = 90
	assert copied != original

	copied.special_image_techniques.append(ZeroMicronLayer(enabled=False, count=0))
	assert len(original.special_image_techniques) == 2


def test_membrane_settings_copy_and_equality():
	original = MembraneSettings(
		max_membrane_thickness_um=5.0,
		bulk_exposure_multiplier=1.3,
		dilation_px=2,
		defocus_um=10.0,
		special_image_techniques=[ZeroMicronLayer(enabled=True, count=2)],
	)
	copied = original.copy()

	assert copied == original

	copied.dilation_px = 4
	assert copied != original


def test_secondary_dose_settings_copy_and_equality():
	original = SecondaryDoseSettings(
		edge_bulk_exposure_multiplier=1.2,
		edge_erosion_px=1,
		edge_dilation_px=2,
		roof_bulk_exposure_multiplier=2.0,
		roof_erosion_px=1,
		roof_layers_above=2,
	)
	copied = original.copy()

	assert copied == original

	copied.edge_dilation_px = 3
	assert copied != original


def test_settings_save_and_load_roundtrip(tmp_path):
	settings = _build_settings()
	path = tmp_path / "settings.json"

	settings.save(path)
	assert path.exists()

	loaded = Settings.from_file(path)
	assert loaded.to_dict() == settings.to_dict()


def test_resin_save_and_load_roundtrip(tmp_path):
	resin = ResinType(
		bulk_exposure=90.0,
		exposure_offset=2.0,
		monomer=[("PEG", 100.0)],
		uv_absorbers=[("NPS", 2.0)],
		initiators=[("IRG", 1.0)],
		additives=[],
	)
	path = tmp_path / "resin.json"

	resin.save(path)
	assert path.exists()

	loaded = ResinType.from_file(path)
	assert loaded.to_dict() == resin.to_dict()


def test_printer_save_and_load_roundtrip(tmp_path):
	light_engine = LightEngine(
		name="le",
		px_size=0.01,
		px_count=(100, 50),
		wavelengths=[365, 405],
		grayscale_available=[False, True],
	)
	printer = Printer(name="Printer", light_engines=[light_engine], xy_stage_available=True)
	path = tmp_path / "printer.json"

	printer.save(path)
	assert path.exists()

	loaded = Printer.from_file(path)
	assert loaded.to_dict() == printer.to_dict()


def test_settings_serialize_rejects_unknown_special_print_technique():
	class _UnknownPrintTechnique:
		pass

	settings = _build_settings()
	settings.special_print_techniques = [_UnknownPrintTechnique()]

	with pytest.raises(ValueError, match="Unsupported special print technique"):
		settings.to_dict()


def test_settings_serialize_rejects_unknown_layer_technique():
	class _UnknownLayerTechnique:
		pass

	settings = _build_settings()
	settings.default_position_settings.special_layer_techniques = [
		_UnknownLayerTechnique()
	]

	with pytest.raises(ValueError, match="Unsupported special layer technique"):
		settings.to_dict()


def test_settings_serialize_rejects_unknown_image_technique():
	class _UnknownImageTechnique:
		pass

	settings = _build_settings()
	settings.default_exposure_settings.special_image_techniques = [
		_UnknownImageTechnique()
	]

	with pytest.raises(ValueError, match="Unsupported special image technique"):
		settings.to_dict()


def test_resin_validation_errors():
	with pytest.raises(ValueError, match="bulk_exposure must be a positive number"):
		ResinType(bulk_exposure=0)
	with pytest.raises(ValueError, match="exposure_offset must be a non-negative number"):
		ResinType(bulk_exposure=10, exposure_offset=-1)
	with pytest.raises(ValueError, match="Monomer must be a list of tuples"):
		ResinType(bulk_exposure=10, monomer="PEG")
	with pytest.raises(ValueError, match="UV absorber must be a list of tuples"):
		ResinType(
			bulk_exposure=10,
			monomer=[("PEG", 100.0)],
			uv_absorbers="NPS",
			initiators=[("IRG", 1.0)],
			additives=[],
		)
	with pytest.raises(ValueError, match="Initiators must be a list of tuples"):
		ResinType(
			bulk_exposure=10,
			monomer=[("PEG", 100.0)],
			uv_absorbers=[("NPS", 2.0)],
			initiators="IRG",
			additives=[],
		)
	with pytest.raises(ValueError, match="Additives must be a list of tuples"):
		ResinType(
			bulk_exposure=10,
			monomer=[("PEG", 100.0)],
			uv_absorbers=[("NPS", 2.0)],
			initiators=[("IRG", 1.0)],
			additives="X",
		)
	with pytest.raises(ValueError, match="All percentages must be between 0 and 100"):
		ResinType(
			bulk_exposure=10,
			monomer=[("PEG", 100.0)],
			uv_absorbers=[("NPS", -1.0)],
			initiators=[("IRG", 1.0)],
			additives=[],
		)
	with pytest.raises(ValueError, match="Monomer percentages must add up to 100%"):
		ResinType(
			bulk_exposure=10,
			monomer=[("PEG", 90.0)],
			uv_absorbers=[("NPS", 2.0)],
			initiators=[("IRG", 1.0)],
			additives=[],
		)
	with pytest.raises(ValueError, match="UV absorber, initiators, and additives percentages"):
		ResinType(
			bulk_exposure=10,
			monomer=[("PEG", 100.0)],
			uv_absorbers=[("NPS", 80.0)],
			initiators=[("IRG", 30.0)],
			additives=[],
		)


def test_light_engine_validation_errors():
	with pytest.raises(ValueError, match="Pixel size must be a positive number"):
		LightEngine(px_size=0)
	with pytest.raises(ValueError, match="Pixel count must be a tuple of two positive integers"):
		LightEngine(px_count=(0, 10))
	with pytest.raises(ValueError, match="Wavelengths must be a list of positive integers"):
		LightEngine(wavelengths=[-1])
	with pytest.raises(ValueError, match="Grayscale availability must be a list of booleans"):
		LightEngine(grayscale_available=["no"])


def test_printer_get_light_engine_error():
	light_engine = LightEngine(
		name="A",
		px_size=0.01,
		px_count=(100, 50),
		wavelengths=[365],
	)
	printer = Printer(name="Printer", light_engines=[light_engine])

	with pytest.raises(ValueError, match="No matching light engine found"):
		printer._get_light_engine(0.02, 365)


def test_secondary_dose_settings_validation_errors():
	with pytest.raises(ValueError, match="Edge exposure multiplier must be set"):
		SecondaryDoseSettings(edge_bulk_exposure_multiplier=None, edge_erosion_px=1)
	with pytest.raises(ValueError, match="Roof exposure multiplier must be set"):
		SecondaryDoseSettings(roof_bulk_exposure_multiplier=None, roof_layers_above=1)
