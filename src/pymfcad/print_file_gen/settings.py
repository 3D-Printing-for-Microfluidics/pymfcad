from __future__ import annotations

import json
from pathlib import Path


class SpecialPrintTechniques:
    def __init__(self):
        pass

    @classmethod
    def to_dict(cls, techniques_list: list[SpecialPrintTechniques]) -> dict:
        temp_dict = {}
        for spt in techniques_list:
            if isinstance(spt, PrintUnderVacuum):
                temp_dict["Print under vacuum"] = spt.to_dict()
        return temp_dict

    @classmethod
    def from_dict(cls, data: dict) -> SpecialPrintTechniques:
        if "Enable vacuum" in data:
            return PrintUnderVacuum.from_dict(data)
        else:
            raise ValueError("Unsupported special print technique")


class PrintUnderVacuum(SpecialPrintTechniques):
    def __init__(
        self,
        enabled: bool = False,
        target_vacuum_level_torr: float = 10.0,
        vacuum_wait_time: float = 0.0,
    ):
        """
        Settings for printing under vacuum.

        Parameters:

        - enabled: Whether to enable printing under vacuum.
        - target_vacuum_level_torr: Target vacuum level in Torr.
        - vacuum_wait_time: Time to wait to reach target vacuum level in seconds.
        """
        self.enabled = enabled
        self.target_vacuum_level_torr = target_vacuum_level_torr
        self.vacuum_wait_time = vacuum_wait_time

    def to_dict(self):
        return {
            "Enable vacuum": self.enabled,
            "Target vacuum level (Torr)": self.target_vacuum_level_torr,
            "Vacuum wait time (sec)": self.vacuum_wait_time,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PrintUnderVacuum:
        return cls(
            enabled=data.get("Enable vacuum", False),
            target_vacuum_level_torr=data.get("Target vacuum level (Torr)", 10.0),
            vacuum_wait_time=data.get("Vacuum wait time (sec)", 0.0),
        )


class ResinType:
    def __init__(
        self,
        bulk_exposure: float,
        exposure_offset: float = 0.0,
        monomer: list[tuple[str, float]] = [("PEG", 100)],
        uv_absorbers: list[tuple[str, float]] = [("NPS", 2.0)],
        initiators: list[tuple[str, float]] = [("IRG", 1.0)],
        additives: list[tuple[str, float]] = [],
    ):
        """
        Initialize the resin formulation.

        Parameters:

        - bulk_exposure: Base exposure time for bulk polymerization in milliseconds.
        - exposure_offset: Optional exposure offset before polymerization begins in milliseconds. Used to adjust for polymerization delay from oxygen inhibition or other added inhibitors.
        - monomer: List of tuples (name, percentage) for monomers.
        - uv_absorbers: List of tuples (name, percentage) for UV absorbers.
        - initiators: List of tuples (name, percentage) for photoinitiators.
        - additives: List of tuples (name, percentage) for additives.

        Resin naming convention:

        - Use 3 letter abbreviations for materials.
        - Follow with a dash and the percent amount of the material
        - If it's a monomer or oligimer, the percent is the fraction of total monomer/oligimer
        - If it's an absorber, photoinitiator, or additive, the percent is a w/w fraction of the total resin mass
        - When there are multiple materials in a category, separate them with a single underscore, _
        - Separate categories of materials with two underscores, __
        - Schema: MoA-XX_MoB-XX__AbA-XX_AbB-XX__PIA-XX_PIB_XX__AdA-XX_AdB-XX
        - where:
            - MoA, MoB - monomers A and B
            - AbA, AbB - absorbers A and B
            - PIA, PIB - photoinitiators A and B
            - AdA, AdB - additives A and B
            - XX - number


        """

        if not isinstance(bulk_exposure, (int, float)) or bulk_exposure <= 0:
            raise ValueError("bulk_exposure must be a positive number")
        if not isinstance(exposure_offset, (int, float)) or exposure_offset < 0:
            raise ValueError("exposure_offset must be a non-negative number")

        if not isinstance(monomer, list) or not all(
            (isinstance(x, tuple) or isinstance(x, list)) and len(x) == 2 for x in monomer
        ):
            raise ValueError("Monomer must be a list of tuples (name, percentage)")

        if not isinstance(uv_absorbers, list) or not all(
            (isinstance(x, tuple) or isinstance(x, list)) and len(x) == 2
            for x in uv_absorbers
        ):
            raise ValueError("UV absorber must be a list of tuples (name, percentage)")

        if not isinstance(initiators, list) or not all(
            (isinstance(x, tuple) or isinstance(x, list)) and len(x) == 2
            for x in initiators
        ):
            raise ValueError("Initiators must be a list of tuples (name, percentage)")

        if not isinstance(additives, list) or not all(
            (isinstance(x, tuple) or isinstance(x, list)) and len(x) == 2
            for x in additives
        ):
            raise ValueError("Additives must be a list of tuples (name, percentage)")

        if not all(
            0 <= x[1] <= 100 for x in monomer + uv_absorbers + initiators + additives
        ):
            raise ValueError("All percentages must be between 0 and 100")
        if sum(x[1] for x in monomer) != 100.0:
            raise ValueError("Monomer percentages must add up to 100%")
        if sum(x[1] for x in uv_absorbers + initiators + additives) > 100:
            raise ValueError(
                "UV absorber, initiators, and additives percentages must not exceed 100%"
            )

        self.monomer = monomer
        self.uv_absorbers = uv_absorbers
        self.initiators = initiators
        self.additives = additives
        self.bulk_exposure = float(bulk_exposure)
        self.exposure_offset = float(exposure_offset)

    def __str__(self):
        # String matching schema
        monomer_str = "_".join(
            f"{name}-{percentage:.2f}" for name, percentage in self.monomer
        )
        uv_absorber_str = "_".join(
            f"{name}-{percentage:.2f}" for name, percentage in self.uv_absorbers
        )
        initiators_str = "_".join(
            f"{name}-{percentage:.2f}" for name, percentage in self.initiators
        )
        if len(self.additives) == 0:
            return f"{monomer_str}__{uv_absorber_str}__{initiators_str}"
        else:
            additives_str = "_".join(
                f"{name}-{percentage:.2f}" for name, percentage in self.additives
            )
            return f"{monomer_str}__{uv_absorber_str}__{initiators_str}__{additives_str}"

    def to_dict(self) -> dict:
        return {
            "bulk_exposure": self.bulk_exposure,
            "exposure_offset": self.exposure_offset,
            "monomer": [list(x) for x in self.monomer],
            "uv_absorbers": [list(x) for x in self.uv_absorbers],
            "initiators": [list(x) for x in self.initiators],
            "additives": [list(x) for x in self.additives],
        }

    @classmethod
    def from_dict(cls, data: dict) -> ResinType:
        return cls(
            bulk_exposure=data.get("bulk_exposure"),
            exposure_offset=data.get("exposure_offset", 0.0),
            monomer=[tuple(x) for x in data.get("monomer", [])],
            uv_absorbers=[tuple(x) for x in data.get("uv_absorbers", [])],
            initiators=[tuple(x) for x in data.get("initiators", [])],
            additives=[tuple(x) for x in data.get("additives", [])],
        )

    def save(self, file_path: str | Path):
        """Save resin formulation to a JSON file."""
        path = Path(file_path)
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_file(cls, file_path: str | Path) -> ResinType:
        """Load a resin formulation from a JSON file."""
        path = Path(file_path)
        with path.open("r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))


class ExposureSettings:
    def __init__(
        self,
        # image_file: str = None,
        grayscale_correction: bool = None,
        # image_x_offset: float = None,
        # image_y_offset: float = None,
        bulk_exposure_multiplier: float = None,
        # light_engine: str = None,
        power_setting: int = None,
        wavelength: int = None,
        relative_focus_position: float = None,
        wait_before_exposure: float = None,
        wait_after_exposure: float = None,
        special_image_techniques: list[SpecialImageTechniques] = [],
        **kwargs,
    ):
        """
        Initialize exposure settings for layer exposure.

        Parameters:

        - grayscale_correction: Whether to apply grayscale correction.
        - bulk_exposure_multiplier: Multiplier applied to resin bulk exposure.
        - power_setting: Power setting of the light engine in percentage.
        - wavelength: Wavelength of the light engine in nm.
        - relative_focus_position: Relative focus position in microns.
        - wait_before_exposure: Wait time before exposure in milliseconds.
        - wait_after_exposure: Wait time after exposure in milliseconds.
        - special_image_techniques: List of SpecialImageTechniques to apply.

        Default Values:

        - grayscale_correction: bool = False,
        - bulk_exposure_multiplier: float = 1.0,
        - power_setting: int = 100,
        - wavelength: int = 365,
        - relative_focus_position: float = 0.0,
        - wait_before_exposure: float = 0.0,
        - wait_after_exposure: float = 0.0,
        """

        self.image_file = None
        self.grayscale_correction = grayscale_correction
        self.image_x_offset = None
        self.image_y_offset = None
        self.bulk_exposure_multiplier = bulk_exposure_multiplier
        self.light_engine = None
        self.power_setting = power_setting
        self.wavelength = wavelength
        self.relative_focus_position = relative_focus_position
        self.wait_before_exposure = wait_before_exposure
        self.wait_after_exposure = wait_after_exposure
        self.special_image_techniques = special_image_techniques
        self.burnin = False

    def __eq__(self, other):
        # """Check equality of exposure settings."""
        if not isinstance(other, ExposureSettings):
            return False
        return self.to_dict() == other.to_dict()

    def copy(self):
        """Create a copy of the exposure settings."""
        return ExposureSettings(
            # image_file=self.image_file,
            grayscale_correction=self.grayscale_correction,
            # image_x_offset=self.image_x_offset,
            # image_y_offset=self.image_y_offset,
            bulk_exposure_multiplier=self.bulk_exposure_multiplier,
            # light_engine=self.light_engine,
            power_setting=self.power_setting,
            wavelength=self.wavelength,
            relative_focus_position=self.relative_focus_position,
            wait_before_exposure=self.wait_before_exposure,
            wait_after_exposure=self.wait_after_exposure,
            special_image_techniques=self.special_image_techniques.copy(),
        )

    def get_exposure_time(self, resin: ResinType) -> float | None:
        if self.bulk_exposure_multiplier is None:
            return None
        return (
            resin.bulk_exposure - resin.exposure_offset
        ) * self.bulk_exposure_multiplier + resin.exposure_offset

    def fill_with_defaults(
        self, defaults: ExposureSettings = None, exceptions: list[str] = None
    ):
        if defaults is None:
            defaults = ExposureSettings(
                grayscale_correction=False,
                bulk_exposure_multiplier=1.0,
                power_setting=100,
                wavelength=365,
                relative_focus_position=0.0,
                wait_before_exposure=0.0,
                wait_after_exposure=0.0,
            )

        # """Fill in None values with defaults."""
        for var in vars(self):
            if exceptions and var in exceptions:
                continue
            if getattr(self, var) is None:
                setattr(self, var, getattr(defaults, var))

    def to_dict(self, resin=None):
        # """Convert exposure settings to a dictionary."""
        temp_dict = {
            "Image file": self.image_file,
            "Do grayscale correction": self.grayscale_correction,
            "Image x offset (um)": self.image_x_offset,
            "Image y offset (um)": self.image_y_offset,
        }
        if resin is not None:
            temp_dict["Layer exposure time (ms)"] = self.get_exposure_time(resin)
        else:
            temp_dict["Layer exposure multiplier"] = self.bulk_exposure_multiplier
        temp_dict.update(
            {
                "Light engine": self.light_engine,
                "Light engine power setting": self.power_setting,
                "Light engine wavelength (nm)": self.wavelength,
                "Relative focus position (um)": self.relative_focus_position,
                "Wait before exposure (ms)": self.wait_before_exposure,
                "Wait after exposure (ms)": self.wait_after_exposure,
            }
        )
        if len(self.special_image_techniques) > 0:
            temp_dict["Special image techniques"] = SpecialImageTechniques.to_dict(
                self.special_image_techniques
            )
        return temp_dict

    @classmethod
    def from_dict(cls, data: dict) -> ExposureSettings:
        c = cls(
            grayscale_correction=data.get("Do grayscale correction"),
            bulk_exposure_multiplier=data.get("Layer exposure multiplier"),
            power_setting=data.get("Light engine power setting"),
            wavelength=data.get("Light engine wavelength (nm)"),
            relative_focus_position=data.get("Relative focus position (um)"),
            wait_before_exposure=data.get("Wait before exposure (ms)"),
            wait_after_exposure=data.get("Wait after exposure (ms)"),
            special_image_techniques=[
                SpecialImageTechniques.from_dict(sit)
                for sit in data.get("Special image techniques", [])
            ],
        )
        c.image_file = data.get("Image file")
        c.image_x_offset = data.get("Image x offset (um)")
        c.image_y_offset = data.get("Image y offset (um)")
        c.light_engine = data.get("Light engine")
        return c


class LightEngine:
    def __init__(
        self,
        name: str = "visitech",
        px_size: float = 0.0076,
        px_count: tuple[int, int] = (2560, 1600),
        wavelengths: list[int] = [365],
        default_exposure_settings: list[ExposureSettings] = [ExposureSettings()],
        grayscale_available: list[bool] = [False],
        settle_time_ms: float = 0.0,
        stitched_px_overlap=(0, 0),
        x_offset_limits: tuple[(int, float), (int, float)] = (0, 0),
        y_offset_limits: tuple[(int, float), (int, float)] = (0, 0),
    ):
        """
        Initialize a LightEngine object.

        Parameters:

        - name: Name of the light engine.
        - px_size: Pixel size in mm.
        - px_count: Tuple of (width, height) pixel count.
        - wavelengths: List of supported wavelengths in nm (first wavelength is the default).
        - grayscale_available: List of booleans indicating if grayscale is available for each wavelength.
        - default_exposure_settings: List of default exposure settings for each wavelength.
        - settle_time_ms: Extra wait time in milliseconds for the first exposure
            after switching to this light engine.
        - x_offset_limits: Tuple of (min_x, max_x) exposure position offset limits in microns.
        - y_offset_limits: Tuple of (min_y, max_y) exposure position offset limits in microns.
        - stitched_px_overlap: Tuple of (x_overlap, y_overlap) in pixels for stitched workspaces.
        """
        if not isinstance(px_size, (int, float)) or px_size <= 0:
            raise ValueError("Pixel size must be a positive number")
        if (
            not (isinstance(px_count, tuple) or isinstance(px_count, list))
            or len(px_count) != 2
            or not all(isinstance(x, int) and x > 0 for x in px_count)
        ):
            raise ValueError("Pixel count must be a tuple of two positive integers")
        if (
            not (
                isinstance(stitched_px_overlap, tuple)
                or isinstance(stitched_px_overlap, list)
            )
            or len(stitched_px_overlap) != 2
            or not all(isinstance(x, int) and x >= 0 for x in stitched_px_overlap)
        ):
            raise ValueError(
                "Stitched pixel overlap must be a tuple of two non-negative integers"
            )
        if (
            not (isinstance(x_offset_limits, tuple) or isinstance(x_offset_limits, list))
            or len(x_offset_limits) != 2
            or not all(isinstance(x, (int, float)) for x in x_offset_limits)
        ):
            raise ValueError("X offset limits must be a tuple of two numbers")
        if (
            not (isinstance(y_offset_limits, tuple) or isinstance(y_offset_limits, list))
            or len(y_offset_limits) != 2
            or not all(isinstance(y, (int, float)) for y in y_offset_limits)
        ):
            raise ValueError("Y offset limits must be a tuple of two numbers")
        if x_offset_limits[0] > x_offset_limits[1]:
            raise ValueError("X offset limits must be in the order (min_x, max_x)")
        if y_offset_limits[0] > y_offset_limits[1]:
            raise ValueError("Y offset limits must be in the order (min_y, max_y)")
        if not isinstance(wavelengths, list) or not all(
            isinstance(x, int) and x > 0 for x in wavelengths
        ):
            raise ValueError("Wavelengths must be a list of positive integers")
        if not isinstance(grayscale_available, list) or not all(
            isinstance(x, bool) for x in grayscale_available
        ):
            raise ValueError("Grayscale availability must be a list of booleans")
        if not isinstance(settle_time_ms, (int, float)) or settle_time_ms < 0:
            raise ValueError("Settle time must be a non-negative number")
        self.name = name
        self.px_size = px_size
        self.px_count = px_count
        self.stitched_px_overlap = stitched_px_overlap
        self.x_offset_limits = x_offset_limits
        self.y_offset_limits = y_offset_limits
        self.wavelengths = wavelengths
        self.grayscale_available = grayscale_available
        self.default_exposure_settings = default_exposure_settings
        for es in self.default_exposure_settings:
            es.fill_with_defaults()
        self.settle_time_ms = float(settle_time_ms)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "px_size": self.px_size,
            "px_count": list(self.px_count),
            "wavelengths": list(self.wavelengths),
            "default_exposure_settings": [
                es.to_dict() for es in self.default_exposure_settings
            ],
            "grayscale_available": list(self.grayscale_available),
            "settle_time_ms": self.settle_time_ms,
            "stitched_px_overlap": list(self.stitched_px_overlap),
            "x_offset_limits": list(self.x_offset_limits),
            "y_offset_limits": list(self.y_offset_limits),
        }

    @classmethod
    def from_dict(cls, data: dict) -> LightEngine:
        return cls(
            name=data.get("name", "visitech"),
            px_size=data.get("px_size", 0.0076),
            px_count=tuple(data.get("px_count", (2560, 1600))),
            stitched_px_overlap=tuple(data.get("stitched_px_overlap", (0, 0))),
            x_offset_limits=tuple(data.get("x_offset_limits", (0, 0))),
            y_offset_limits=tuple(data.get("y_offset_limits", (0, 0))),
            wavelengths=list(data.get("wavelengths", [365])),
            grayscale_available=list(data.get("grayscale_available", [False])),
            default_exposure_settings=[
                ExposureSettings.from_dict(es)
                for es in data.get("default_exposure_settings", [{}])
            ],
            settle_time_ms=data.get("settle_time_ms", 0.0),
        )


class PositionSettings:
    def __init__(
        self,
        # layer_thickness: float = None,
        distance_up: float = None,
        initial_wait: float = None,
        up_speed: float = None,
        up_acceleration: float = None,
        up_wait: float = None,
        down_speed: float = None,
        down_acceleration: float = None,
        final_wait: float = None,
        special_layer_techniques: list[SpecialLayerTechniques] = [],
    ):
        """
        Initialize position settings for layer movement.

        Parameters:

        - distance_up: Distance to move up in mm.
        - initial_wait: Initial wait time in milliseconds.
        - up_speed: Speed to move up in mm/sec.
        - up_acceleration: Acceleration to move up in mm/sec^2.
        - up_wait: Wait time after moving up in milliseconds.
        - down_speed: Speed to move down in mm/sec.
        - down_acceleration: Acceleration to move down in mm/sec^2.
        - final_wait: Final wait time in milliseconds.
        - special_layer_techniques: List of SpecialLayerTechniques to apply.

        Default Values:

        - distance_up: float = 1.0,
        - initial_wait: float = 0.0,
        - up_speed: float = 25.0,
        - up_acceleration: float = 50.0,
        - up_wait: float = 0.0,
        - down_speed: float = 20.0,
        - down_acceleration: float = 50.0,
        - final_wait: float = 0.0,
        """

        self.layer_thickness = None
        self.distance_up = distance_up
        self.initial_wait = initial_wait
        self.up_speed = up_speed
        self.up_acceleration = up_acceleration
        self.up_wait = up_wait
        self.down_speed = down_speed
        self.down_acceleration = down_acceleration
        self.final_wait = final_wait
        self.special_layer_techniques = special_layer_techniques

    def __eq__(self, other):
        # """Check equality of position settings."""
        if not isinstance(other, PositionSettings):
            return False
        return self.to_dict() == other.to_dict()

    def copy(self):
        """Create a copy of the position settings."""
        return PositionSettings(
            # layer_thickness=self.layer_thickness,
            distance_up=self.distance_up,
            initial_wait=self.initial_wait,
            up_speed=self.up_speed,
            up_acceleration=self.up_acceleration,
            up_wait=self.up_wait,
            down_speed=self.down_speed,
            down_acceleration=self.down_acceleration,
            final_wait=self.final_wait,
            special_layer_techniques=self.special_layer_techniques.copy(),
        )

    def fill_with_defaults(
        self, defaults: PositionSettings = None, exceptions: list[str] = None
    ):
        if defaults is None:
            defaults = PositionSettings(
                distance_up=1.0,
                initial_wait=0.0,
                up_speed=25.0,
                up_acceleration=50.0,
                up_wait=0.0,
                down_speed=20.0,
                down_acceleration=50.0,
                final_wait=0.0,
            )
        # """Fill in None values with defaults."""
        for var in vars(self):
            if exceptions and var in exceptions:
                continue
            if getattr(self, var) is None:
                setattr(self, var, getattr(defaults, var))

    def to_dict(self):
        # """Convert position settings to a dictionary."""
        temp_dict = {
            "Layer thickness (um)": self.layer_thickness,
            "Distance up (mm)": self.distance_up,
            "Initial wait (ms)": self.initial_wait,
            "BP up speed (mm/sec)": self.up_speed,
            "BP up acceleration (mm/sec^2)": self.up_acceleration,
            "Up wait (ms)": self.up_wait,
            "BP down speed (mm/sec)": self.down_speed,
            "BP down acceleration (mm/sec^2)": self.down_acceleration,
            "Final wait (ms)": self.final_wait,
        }
        if len(self.special_layer_techniques) > 0:
            temp_dict["Special layer techniques"] = SpecialLayerTechniques.to_dict(
                self.special_layer_techniques
            )
        return temp_dict

    @classmethod
    def from_dict(cls, data: dict) -> PositionSettings:
        c = cls(
            distance_up=data.get("Distance up (mm)"),
            initial_wait=data.get("Initial wait (ms)"),
            up_speed=data.get("BP up speed (mm/sec)"),
            up_acceleration=data.get("BP up acceleration (mm/sec^2)"),
            up_wait=data.get("Up wait (ms)"),
            down_speed=data.get("BP down speed (mm/sec)"),
            down_acceleration=data.get("BP down acceleration (mm/sec^2)"),
            final_wait=data.get("Final wait (ms)"),
            special_layer_techniques=[
                SpecialLayerTechniques.from_dict(slt)
                for slt in data.get("Special layer techniques", [])
            ],
        )
        c.layer_thickness = data.get("Layer thickness (um)")
        return c


class Printer:
    def __init__(
        self,
        name: str,
        light_engines: list[LightEngine],
        xy_stage_available: bool = False,
        vacuum_available: bool = False,
        default_position_settings: PositionSettings = PositionSettings(),
    ):
        """
        Initialize a Printer object.

        Parameters:

        - name: Name of the printer.
        - light_engines: List of LightEngine objects.
        - xy_stage_available: Whether the printer has an XY stage.
        - vacuum_available: Whether the printer supports vacuum printing.
        - default_position_settings: Default position settings for the printer.
        """
        self.name = name
        self.light_engines = (
            [light_engines] if isinstance(light_engines, LightEngine) else light_engines
        )
        self.xy_stage_available = xy_stage_available
        self.vacuum_available = vacuum_available
        self.default_position_settings = default_position_settings
        self.default_position_settings.fill_with_defaults()

    def get_light_engine_by_name(self, name: str) -> LightEngine | None:
        """Return the light engine matching the given name, or None if not found."""
        for le in self.light_engines:
            if le.name == name:
                return le
        return None

    def _get_light_engine(self, px_size, wavelength=None):
        """Get the light engine with the specified pixel size, pixel count, and wavelength."""
        for le in self.light_engines:
            if wavelength is None:
                if le.px_size == px_size:
                    return le
            if le.px_size == px_size and wavelength in le.wavelengths:
                return le
        raise ValueError(
            f"No matching light engine found (px_size={px_size}, wavelength={wavelength})"
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "light_engines": [le.to_dict() for le in self.light_engines],
            "xy_stage_available": self.xy_stage_available,
            "vacuum_available": self.vacuum_available,
            "default_position_settings": self.default_position_settings.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Printer:
        light_engines = [
            LightEngine.from_dict(le) for le in data.get("light_engines", [])
        ]
        return cls(
            name=data.get("name", ""),
            light_engines=light_engines,
            xy_stage_available=data.get("xy_stage_available", False),
            vacuum_available=data.get("vacuum_available", False),
            default_position_settings=PositionSettings.from_dict(
                data.get("default_position_settings", {})
            ),
        )

    def save(self, file_path: str | Path):
        """Save printer configuration to a JSON file."""
        path = Path(file_path)
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_file(cls, file_path: str | Path) -> Printer:
        """Load a printer configuration from a JSON file."""
        path = Path(file_path)
        with path.open("r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))


class SpecialLayerTechniques:
    def __init__(self):
        pass

    @classmethod
    def to_dict(cls, techniques_list: list[SpecialLayerTechniques]) -> dict:
        temp_dict = {}
        for slt in techniques_list:
            if isinstance(slt, SqueezeOutResin):
                temp_dict["Squeeze out resin"] = slt.to_dict()
        return temp_dict

    @classmethod
    def from_dict(cls, data: dict) -> SpecialLayerTechniques:
        if "Enable Squeeze" in data:
            return SqueezeOutResin.from_dict(data)
        else:
            raise ValueError("Unsupported special layer technique")


class SqueezeOutResin(SpecialLayerTechniques):
    def __init__(
        self,
        enabled: bool = False,
        count: int = 0,
        squeeze_force: float = 0.0,
        squeeze_time: float = 0.0,
    ):
        """
        Settings for squeezing out resin between layers.

        Parameters:

        - enabled: Whether to enable squeeze out resin.
        - count: Number of squeezes to perform.
        - squeeze_force: Force to apply during squeeze in Newtons.
        - squeeze_time: Time to hold the squeeze in milliseconds.
        """
        self.enabled = enabled
        self.count = count
        self.squeeze_force = squeeze_force
        self.squeeze_time = squeeze_time

    def to_dict(self):
        return {
            "Enable squeeze": self.enabled,
            "Squeeze count": self.count,
            "Squeeze force (N)": self.squeeze_force,
            "Squeeze time (ms)": self.squeeze_time,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SqueezeOutResin:
        return cls(
            enabled=data.get("Enable squeeze", False),
            count=data.get("Squeeze count", 0),
            squeeze_force=data.get("Squeeze force (N)", 0.0),
            squeeze_time=data.get("Squeeze time (ms)", 0.0),
        )


class SpecialImageTechniques:
    def __init__(self):
        pass

    @classmethod
    def to_dict(cls, techniques_list: list[SpecialImageTechniques]) -> dict:
        temp_dict = {}
        for sit in techniques_list:
            if isinstance(sit, ZeroMicronLayer):
                temp_dict["Zero micron layer"] = sit.to_dict()
            elif isinstance(sit, PrintOnFilm):
                temp_dict["Print on film"] = sit.to_dict()
        return temp_dict

    @classmethod
    def from_dict(cls, data: dict) -> SpecialImageTechniques:
        if "Enable zero micron" in data:
            return ZeroMicronLayer.from_dict(data)
        elif "Enable print on film" in data:
            return PrintOnFilm.from_dict(data)
        else:
            raise ValueError("Unsupported special image technique")


class ZeroMicronLayer(SpecialImageTechniques):
    def __init__(self, enabled: bool = False, count: int = 0):
        """
        Settings for zero micron layers.

        Parameters:

        - enabled: Whether to enable zero micron layers.
        - count: Number of zero micron layers to apply.
        """
        self.enabled = enabled
        self.count = count

    def to_dict(self):
        return {
            "Enable zero micron": self.enabled,
            "Zero micron count": self.count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ZeroMicronLayer:
        return cls(
            enabled=data.get("Enable zero micron", False),
            count=data.get("Zero micron count", 0),
        )


class PrintOnFilm(SpecialImageTechniques):
    def __init__(
        self, enabled: bool = False, distance_up_mm: float = 0.3, up_wait: float = 20000.0
    ):
        """
        Settings for printing on film.

        Parameters:

        - enabled: Whether to enable printing on film.
        - distance_up_mm: Distance to move up in mm when printing on film.
        - up_wait: Wait time at the up position in milliseconds before exposing the image.
        """
        self.enabled = enabled
        self.distance_up = distance_up_mm
        self.up_wait = up_wait

    def to_dict(self):
        return {
            "Enable print on film": self.enabled,
            "Distance up (mm)": self.distance_up,
            "Up wait (ms)": self.up_wait,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PrintOnFilm:
        return cls(
            enabled=data.get("Enable print on film", False),
            distance_up_mm=data.get("Distance up (mm)", 0.3),
            up_wait=data.get("Up wait (ms)", 20000.0),
        )


class MembraneSettings:
    def __init__(
        self,
        exposure_settings: ExposureSettings = ExposureSettings(),
        max_membrane_thickness_um: float = 0.0,
        dilation_px: int = 0,
        scan_for_membrane: bool = True,
    ):
        """
        Initialize membrane settings for membrane exposure.

        Parameters:

        - exposure_settings: ExposureSettings object for membrane exposure.
        - max_membrane_thickness_um: Maximum membrane thickness in microns.
        - dilation_px: Membrane dilation in pixels
        - scan_for_membrane: Whether to scan slices for membranes or use masks directly.
        """

        self.max_membrane_thickness_um = max_membrane_thickness_um
        self.dilation_px = dilation_px
        self.scan_for_membrane = scan_for_membrane
        self.exposure_settings = exposure_settings

    def __eq__(self, other):
        # """Check equality of membrane settings."""
        if not isinstance(other, MembraneSettings):
            return False
        return (
            self.max_membrane_thickness_um == other.max_membrane_thickness_um
            and self.dilation_px == other.dilation_px
            and self.scan_for_membrane == other.scan_for_membrane
            and self.exposure_settings == other.exposure_settings
        )

    def copy(self):
        """Create a copy of the membrane settings."""
        return MembraneSettings(
            max_membrane_thickness_um=self.max_membrane_thickness_um,
            exposure_settings=self.exposure_settings.copy(),
            dilation_px=self.dilation_px,
            scan_for_membrane=self.scan_for_membrane,
        )


class SecondaryDoseSettings:
    def __init__(
        self,
        edge_bulk_exposure_multiplier: float = None,
        edge_erosion_px: int = 0,
        edge_dilation_px: int = 0,
        roof_bulk_exposure_multiplier: float = None,
        roof_erosion_px: int = 0,
        roof_layers_above: int = 0,
    ):
        """
        Initialize secondary dose settings for edges and roofs.

        Parameters:

        - edge_bulk_exposure_multiplier: Multiplier applied to resin bulk exposure for edge features.
        - edge_erosion_px: Erosion in pixels
        - edge_dilation_px: Dilation in pixels
        - roof_bulk_exposure_multiplier: Multiplier applied to resin bulk exposure for roof features.
        - roof_erosion_px: Erosion in pixels
        - roof_layers_above: Number of layers above roof features to apply secondary dose.
        """

        if edge_bulk_exposure_multiplier is None:
            if edge_erosion_px > 0 or edge_dilation_px > 0:
                raise ValueError(
                    "Edge exposure multiplier must be set if edge erosion or dilation is specified"
                )
        if roof_bulk_exposure_multiplier is None:
            if roof_erosion_px > 0 or roof_layers_above > 0:
                raise ValueError(
                    "Roof exposure multiplier must be set if roof erosion or layers above is specified"
                )
        self.edge_erosion_px = edge_erosion_px
        self.edge_dilation_px = edge_dilation_px
        self.roof_erosion_px = roof_erosion_px
        self.roof_layers_above = roof_layers_above
        self.edge_exposure_settings = ExposureSettings(
            bulk_exposure_multiplier=edge_bulk_exposure_multiplier
        )
        self.roof_exposure_settings = ExposureSettings(
            bulk_exposure_multiplier=roof_bulk_exposure_multiplier
        )

    def __eq__(self, other):
        # """Check equality of secondary dose settings."""
        if not isinstance(other, SecondaryDoseSettings):
            return False
        return (
            self.edge_erosion_px == other.edge_erosion_px
            and self.edge_dilation_px == other.edge_dilation_px
            and self.roof_erosion_px == other.roof_erosion_px
            and self.roof_layers_above == other.roof_layers_above
            and self.edge_exposure_settings == other.edge_exposure_settings
            and self.roof_exposure_settings == other.roof_exposure_settings
        )

    def copy(self):
        """Create a copy of the secondary dose settings."""
        return SecondaryDoseSettings(
            edge_bulk_exposure_multiplier=self.edge_exposure_settings.bulk_exposure_multiplier,
            edge_erosion_px=self.edge_erosion_px,
            edge_dilation_px=self.edge_dilation_px,
            roof_bulk_exposure_multiplier=self.roof_exposure_settings.bulk_exposure_multiplier,
            roof_erosion_px=self.roof_erosion_px,
            roof_layers_above=self.roof_layers_above,
        )
