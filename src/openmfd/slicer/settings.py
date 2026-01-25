from __future__ import annotations

import json
import datetime
from pathlib import Path

class SpecialPrintTechniques:
    def __init__(self):
        pass

class PrintUnderVacuum(SpecialPrintTechniques):
    def __init__(self, enabled: bool = False, target_vacuum_level_torr: float = 10.0, vacuum_wait_time: float = 0.0):
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

class Settings:
    def __init__(
        self,
        printer: Printer,
        resin: ResinType,
        default_position_settings: PositionSettings,
        default_exposure_settings: ExposureSettings,
        special_print_techniques: list[SpecialPrintTechniques] = [],
        user: str = "",
        purpose: str = "",
        description: str = "",
    ):
        """
        Initialize the settings for slicer object.

        Parameters:

        - printer: Printer object containing printer settings.
        - resin: ResinType object containing resin formulation.
        - default_position_settings: Default PositionSettings for layers.
        - default_exposure_settings: Default ExposureSettings for layers.
        - special_print_techniques: List of SpecialPrintTechniques to apply.
        - user: Name of the user creating the settings.
        - purpose: Purpose of the print job.
        - description: Description of the print job.
        """
        self.resin = resin
        self.printer = printer
        self.user = user
        self.purpose = purpose
        self.description = description
        self.special_print_techniques = special_print_techniques

        # Set default values for position and exposure settings
        if default_position_settings.distance_up is None:
            default_position_settings.distance_up = 1.0
        if default_position_settings.initial_wait is None:
            default_position_settings.initial_wait = 0.0
        if default_position_settings.up_speed is None:
            default_position_settings.up_speed = 25.0
        if default_position_settings.up_acceleration is None:
            default_position_settings.up_acceleration = 50.0
        if default_position_settings.up_wait is None:
            default_position_settings.up_wait = 0.0
        if default_position_settings.down_speed is None:
            default_position_settings.down_speed = 20.0
        if default_position_settings.down_acceleration is None:
            default_position_settings.down_acceleration = 50.0
        if default_position_settings.final_wait is None:
            default_position_settings.final_wait = 0.0

        if default_exposure_settings.grayscale_correction is None:
            default_exposure_settings.grayscale_correction = False
        if default_exposure_settings.exposure_time is None:
            default_exposure_settings.exposure_time = 300.0
        if default_exposure_settings.power_setting is None:
            default_exposure_settings.power_setting = 100
        if default_exposure_settings.wavelength is None:
            default_exposure_settings.wavelength = 365
        if default_exposure_settings.relative_focus_position is None:
            default_exposure_settings.relative_focus_position = 0.0
        if default_exposure_settings.wait_before_exposure is None:
            default_exposure_settings.wait_before_exposure = 0.0
        if default_exposure_settings.wait_after_exposure is None:
            default_exposure_settings.wait_after_exposure = 0.0

        self.default_position_settings = default_position_settings
        self.default_exposure_settings = default_exposure_settings

        self.settings = {
            "Schema version": "5.0.0",
            "User": user,
            "Purpose": purpose,
            "Description": description,
            "Resin": str(resin),
            "3D printer": printer.name,
            "Slicer": "OpenMFD",
            "Date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Default layer settings": {
                "Number of duplications": 1,
                "Position settings": default_position_settings.to_dict(),
                "Image settings": default_exposure_settings.to_dict(),
            }
        }

        self.settings["Special print techniques"] = {}

        for sps in special_print_techniques:
            if isinstance(sps, PrintUnderVacuum):
                self.settings["Special print techniques"]["Print under vacuum"] = {
                    "Enable vacuum": sps.enabled,
                    "Target vacuum level (Torr)": sps.target_vacuum_level_torr,
                    "Vacuum wait time (sec)": sps.vacuum_wait_time,
                }

    def _serialize_special_print_techniques(self) -> list[dict]:
        techniques = []
        for spt in self.special_print_techniques:
            if isinstance(spt, PrintUnderVacuum):
                techniques.append(
                    {
                        "type": "PrintUnderVacuum",
                        "enabled": spt.enabled,
                        "target_vacuum_level_torr": spt.target_vacuum_level_torr,
                        "vacuum_wait_time": spt.vacuum_wait_time,
                    }
                )
            else:
                raise ValueError(
                    f"Unsupported special print technique: {type(spt).__name__}"
                )
        return techniques

    @staticmethod
    def _deserialize_special_print_techniques(data: list[dict]) -> list[SpecialPrintTechniques]:
        techniques: list[SpecialPrintTechniques] = []
        for item in data:
            technique_type = item.get("type")
            if technique_type == "PrintUnderVacuum":
                techniques.append(
                    PrintUnderVacuum(
                        enabled=item.get("enabled", False),
                        target_vacuum_level_torr=item.get("target_vacuum_level_torr", 10.0),
                        vacuum_wait_time=item.get("vacuum_wait_time", 0.0),
                    )
                )
            else:
                raise ValueError(f"Unsupported special print technique type: {technique_type}")
        return techniques

    @staticmethod
    def _serialize_special_layer_techniques(techniques: list[SpecialLayerTechniques]) -> list[dict]:
        serialized = []
        for slt in techniques:
            if isinstance(slt, SqueezeOutResin):
                serialized.append(
                    {
                        "type": "SqueezeOutResin",
                        "enabled": slt.enabled,
                        "count": slt.count,
                        "squeeze_force": slt.squeeze_force,
                        "squeeze_time": slt.squeeze_time,
                    }
                )
            else:
                raise ValueError(
                    f"Unsupported special layer technique: {type(slt).__name__}"
                )
        return serialized

    @staticmethod
    def _deserialize_special_layer_techniques(data: list[dict]) -> list[SpecialLayerTechniques]:
        techniques: list[SpecialLayerTechniques] = []
        for item in data:
            technique_type = item.get("type")
            if technique_type == "SqueezeOutResin":
                techniques.append(
                    SqueezeOutResin(
                        enabled=item.get("enabled", False),
                        count=item.get("count", 0),
                        squeeze_force=item.get("squeeze_force", 0.0),
                        squeeze_time=item.get("squeeze_time", 0.0),
                    )
                )
            else:
                raise ValueError(f"Unsupported special layer technique type: {technique_type}")
        return techniques

    @staticmethod
    def _serialize_special_image_techniques(techniques: list[SpecialImageTechniques]) -> list[dict]:
        serialized = []
        for sit in techniques:
            if isinstance(sit, ZeroMicronLayer):
                serialized.append(
                    {
                        "type": "ZeroMicronLayer",
                        "enabled": sit.enabled,
                        "count": sit.count,
                    }
                )
            elif isinstance(sit, PrintOnFilm):
                serialized.append(
                    {
                        "type": "PrintOnFilm",
                        "enabled": sit.enabled,
                        "distance_up_mm": sit.distance_up,
                    }
                )
            else:
                raise ValueError(
                    f"Unsupported special image technique: {type(sit).__name__}"
                )
        return serialized

    @staticmethod
    def _deserialize_special_image_techniques(data: list[dict]) -> list[SpecialImageTechniques]:
        techniques: list[SpecialImageTechniques] = []
        for item in data:
            technique_type = item.get("type")
            if technique_type == "ZeroMicronLayer":
                techniques.append(
                    ZeroMicronLayer(
                        enabled=item.get("enabled", False),
                        count=item.get("count", 0),
                    )
                )
            elif technique_type == "PrintOnFilm":
                techniques.append(
                    PrintOnFilm(
                        enabled=item.get("enabled", False),
                        distance_up_mm=item.get("distance_up_mm", 0.3),
                    )
                )
            else:
                raise ValueError(f"Unsupported special image technique type: {technique_type}")
        return techniques

    def _serialize_position_settings(self) -> dict:
        return {
            "distance_up": self.default_position_settings.distance_up,
            "initial_wait": self.default_position_settings.initial_wait,
            "up_speed": self.default_position_settings.up_speed,
            "up_acceleration": self.default_position_settings.up_acceleration,
            "up_wait": self.default_position_settings.up_wait,
            "down_speed": self.default_position_settings.down_speed,
            "down_acceleration": self.default_position_settings.down_acceleration,
            "final_wait": self.default_position_settings.final_wait,
            "special_layer_techniques": self._serialize_special_layer_techniques(
                self.default_position_settings.special_layer_techniques
            ),
        }

    def _serialize_exposure_settings(self) -> dict:
        return {
            "grayscale_correction": self.default_exposure_settings.grayscale_correction,
            "exposure_time": self.default_exposure_settings.exposure_time,
            "power_setting": self.default_exposure_settings.power_setting,
            "wavelength": self.default_exposure_settings.wavelength,
            "relative_focus_position": self.default_exposure_settings.relative_focus_position,
            "wait_before_exposure": self.default_exposure_settings.wait_before_exposure,
            "wait_after_exposure": self.default_exposure_settings.wait_after_exposure,
            "special_image_techniques": self._serialize_special_image_techniques(
                self.default_exposure_settings.special_image_techniques
            ),
        }

    @staticmethod
    def _deserialize_position_settings(data: dict) -> PositionSettings:
        return PositionSettings(
            distance_up=data.get("distance_up"),
            initial_wait=data.get("initial_wait"),
            up_speed=data.get("up_speed"),
            up_acceleration=data.get("up_acceleration"),
            up_wait=data.get("up_wait"),
            down_speed=data.get("down_speed"),
            down_acceleration=data.get("down_acceleration"),
            final_wait=data.get("final_wait"),
            special_layer_techniques=Settings._deserialize_special_layer_techniques(
                data.get("special_layer_techniques", [])
            ),
        )

    @staticmethod
    def _deserialize_exposure_settings(data: dict) -> ExposureSettings:
        return ExposureSettings(
            grayscale_correction=data.get("grayscale_correction"),
            exposure_time=data.get("exposure_time"),
            power_setting=data.get("power_setting"),
            wavelength=data.get("wavelength"),
            relative_focus_position=data.get("relative_focus_position"),
            wait_before_exposure=data.get("wait_before_exposure"),
            wait_after_exposure=data.get("wait_after_exposure"),
            special_image_techniques=Settings._deserialize_special_image_techniques(
                data.get("special_image_techniques", [])
            ),
        )

    def to_dict(self) -> dict:
        return {
            "schema_version": "1.0",
            "printer": self.printer.to_dict(),
            "resin": self.resin.to_dict(),
            "default_position_settings": self._serialize_position_settings(),
            "default_exposure_settings": self._serialize_exposure_settings(),
            "special_print_techniques": self._serialize_special_print_techniques(),
            "user": self.user,
            "purpose": self.purpose,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Settings:
        printer = Printer.from_dict(data["printer"])
        resin = ResinType.from_dict(data["resin"])
        default_position_settings = cls._deserialize_position_settings(
            data.get("default_position_settings", {})
        )
        default_exposure_settings = cls._deserialize_exposure_settings(
            data.get("default_exposure_settings", {})
        )
        special_print_techniques = cls._deserialize_special_print_techniques(
            data.get("special_print_techniques", [])
        )
        return cls(
            printer=printer,
            resin=resin,
            default_position_settings=default_position_settings,
            default_exposure_settings=default_exposure_settings,
            special_print_techniques=special_print_techniques,
            user=data.get("user", ""),
            purpose=data.get("purpose", ""),
            description=data.get("description", ""),
        )

    def save(self, file_path: str | Path):
        path = Path(file_path)
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_file(cls, file_path: str | Path) -> Settings:
        path = Path(file_path)
        with path.open("r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

class ResinType:
    def __init__(
        self,
        monomer: list[tuple[str, float]] = [("PEG", 100)],
        uv_absorbers: list[tuple[str, float]] = [("NPS", 2.0)],
        initiators: list[tuple[str, float]] = [("IRG", 1.0)],
        additives: list[tuple[str, float]] = [],
    ):
        """
        Initialize the resin formulation.
        
        Parameters:

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
            "monomer": [list(x) for x in self.monomer],
            "uv_absorbers": [list(x) for x in self.uv_absorbers],
            "initiators": [list(x) for x in self.initiators],
            "additives": [list(x) for x in self.additives],
        }

    @classmethod
    def from_dict(cls, data: dict) -> ResinType:
        return cls(
            monomer=[tuple(x) for x in data.get("monomer", [])],
            uv_absorbers=[tuple(x) for x in data.get("uv_absorbers", [])],
            initiators=[tuple(x) for x in data.get("initiators", [])],
            additives=[tuple(x) for x in data.get("additives", [])],
        )

    def save(self, file_path: str | Path):
        path = Path(file_path)
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_file(cls, file_path: str | Path) -> ResinType:
        path = Path(file_path)
        with path.open("r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

class LightEngine:
    def __init__(
        self,
        name: str = "visitech",
        px_size: float = 0.0076,
        px_count: tuple[int, int] = (2560, 1600),
        wavelengths: list[int] = [365],
        grayscale_available: list[bool] = [False],
        origin: tuple[float, float] = (0.0, 0.0),  # Origin of image mm (x, y)
    ):
        """
        Initialize a LightEngine object.

        Parameters:

        - name: Name of the light engine.
        - px_size: Pixel size in mm.
        - px_count: Tuple of (width, height) pixel count.
        - wavelengths: List of supported wavelengths in nm.
        - grayscale_available: List of booleans indicating if grayscale is available for each wavelength.
        - origin: Tuple of (x, y) origin in mm.
        """
        if not isinstance(px_size, (int, float)) or px_size <= 0:
            raise ValueError("Pixel size must be a positive number")
        if (
            not (isinstance(px_count, tuple) or isinstance(px_count, list))
            or len(px_count) != 2
            or not all(isinstance(x, int) or x <= 0 for x in px_count)
        ):
            raise ValueError("Pixel count must be a tuple of two positive integers")
        if not isinstance(wavelengths, list) or not all(
            isinstance(x, int) and x > 0 for x in wavelengths
        ):
            raise ValueError("Wavelengths must be a list of positive integers")
        if not isinstance(grayscale_available, list) or not all(
            isinstance(x, bool) for x in grayscale_available
        ):
            raise ValueError("Grayscale availability must be a list of booleans")
        if (
            not (isinstance(origin, tuple) or isinstance(origin, list))
            or len(origin) != 2
            or not all(isinstance(x, (int, float)) for x in origin)
        ):
            raise ValueError("Origin must be a tuple of two numbers (x, y)")
        self.name = name
        self.px_size = px_size
        self.px_count = px_count
        self.wavelengths = wavelengths
        self.grayscale_available = grayscale_available
        self.origin = origin

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "px_size": self.px_size,
            "px_count": list(self.px_count),
            "wavelengths": list(self.wavelengths),
            "grayscale_available": list(self.grayscale_available),
            "origin": list(self.origin),
        }

    @classmethod
    def from_dict(cls, data: dict) -> LightEngine:
        return cls(
            name=data.get("name", "visitech"),
            px_size=data.get("px_size", 0.0076),
            px_count=tuple(data.get("px_count", (2560, 1600))),
            wavelengths=list(data.get("wavelengths", [365])),
            grayscale_available=list(data.get("grayscale_available", [False])),
            origin=tuple(data.get("origin", (0.0, 0.0))),
        )

class Printer:
    def __init__(
        self,
        name: str,
        light_engines: list[LightEngine],
        xy_stage_available: bool = False,
        vacuum_available: bool = False,
    ):
        """
        Initialize a Printer object.

        Parameters:

        - name: Name of the printer.
        - light_engines: List of LightEngine objects.
        - xy_stage_available: Whether the printer has an XY stage.
        - vacuum_available: Whether the printer supports vacuum printing.
        """
        self.name = name
        self.light_engines = (
            [light_engines] if isinstance(light_engines, LightEngine) else light_engines
        )
        self.xy_stage_available = xy_stage_available
        self.vacuum_available = vacuum_available


    def _get_light_engine(self, px_size, px_count, wavelength):
        """Get the light engine with the specified pixel size, pixel count, and wavelength."""
        for le in self.light_engines:
            if (
                le.px_size == px_size
                and le.px_count[0] == px_count[0]
                and le.px_count[1] == px_count[1]
                and wavelength in le.wavelengths
            ):
                return le
        raise ValueError(
            f"No matching light engine found (px_size={px_size}, px_count={px_count}, wavelength={wavelength})"
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "light_engines": [le.to_dict() for le in self.light_engines],
            "xy_stage_available": self.xy_stage_available,
            "vacuum_available": self.vacuum_available,
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
        )

    def save(self, file_path: str | Path):
        path = Path(file_path)
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_file(cls, file_path: str | Path) -> Printer:
        path = Path(file_path)
        with path.open("r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

class SpecialLayerTechniques:
    def __init__(self):
        pass

class SqueezeOutResin(SpecialLayerTechniques):
    def __init__(self, enabled: bool = False, count: int = 0, squeeze_force: float = 0.0, squeeze_time: float = 0.0):
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
            temp_dict["Special layer techniques"] = {}
            for slt in self.special_layer_techniques:
                if isinstance(slt, SqueezeOutResin):
                    temp_dict["Special layer techniques"]["Squeeze out resin"] = {
                        "Enable squeeze": slt.enabled,
                        "Squeeze count": slt.count,
                        "Squeeze force (N)": slt.squeeze_force,
                        "Squeeze time (ms)": slt.squeeze_time,
                    }
        return temp_dict

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
        self, defaults: PositionSettings, exceptions: list[str] = None
    ):
        # """Fill in None values with defaults."""
        for var in vars(self):
            if exceptions and var in exceptions:
                continue
            if getattr(self, var) is None:
                setattr(self, var, getattr(defaults, var))

class SpecialImageTechniques:
    def __init__(self):
        pass

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

class PrintOnFilm(SpecialImageTechniques):
    def __init__(self, enabled: bool = False, distance_up_mm: float = 0.3):
        """
        Settings for printing on film.

        Parameters:

        - enabled: Whether to enable printing on film.
        - distance_up_mm: Distance to move up in mm when printing on film.
        """
        self.enabled = enabled
        self.distance_up = distance_up_mm

class ExposureSettings:
    def __init__(
        self,
        # image_file: str = None,
        grayscale_correction: bool = None,
        # image_x_offset: float = None,
        # image_y_offset: float = None,
        exposure_time: float = None,
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
        - exposure_time: Exposure time in milliseconds.
        - power_setting: Power setting of the light engine in percentage.
        - wavelength: Wavelength of the light engine in nm.
        - relative_focus_position: Relative focus position in microns.
        - wait_before_exposure: Wait time before exposure in milliseconds.
        - wait_after_exposure: Wait time after exposure in milliseconds.
        - special_image_techniques: List of SpecialImageTechniques to apply.

        Default Values:

        - grayscale_correction: bool = False,
        - exposure_time: float = 0.0,
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
        self.exposure_time = exposure_time
        self.light_engine = None
        self.power_setting = power_setting
        self.wavelength = wavelength
        self.relative_focus_position = relative_focus_position
        self.wait_before_exposure = wait_before_exposure
        self.wait_after_exposure = wait_after_exposure
        self.special_image_techniques = special_image_techniques
        self.burnin = False

    def to_dict(self):
        # """Convert exposure settings to a dictionary."""
        temp_dict = {
            "Image file": self.image_file,
            "Do light grayscale correction": self.grayscale_correction,
            "Image x offset (um)": self.image_x_offset,
            "Image y offset (um)": self.image_y_offset,
            "Layer exposure time (ms)": self.exposure_time,
            "Light engine": self.light_engine,
            "Light engine power setting": self.power_setting,
            "Light engine wavelength (nm)": self.wavelength,
            "Relative focus position (um)": self.relative_focus_position,
            "Wait before exposure (ms)": self.wait_before_exposure,
            "Wait after exposure (ms)": self.wait_after_exposure,
        }
        if len(self.special_image_techniques) > 0:
            temp_dict["Special image techniques"] = {}
            for sit in self.special_image_techniques:
                if isinstance(sit, ZeroMicronLayer):
                    temp_dict["Special image techniques"]["Zero micron layer"] = {
                        "Enable zero micron": sit.enabled,
                        "Zero micron count": sit.count,
                    }
                if isinstance(sit, PrintOnFilm):
                    temp_dict["Special image techniques"]["Print on film"] = {
                        "Enable print on film": sit.enabled,
                        "Distance up (mm)": sit.distance_up,
                    }
        return temp_dict

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
            exposure_time=self.exposure_time,
            # light_engine=self.light_engine,
            power_setting=self.power_setting,
            wavelength=self.wavelength,
            relative_focus_position=self.relative_focus_position,
            wait_before_exposure=self.wait_before_exposure,
            wait_after_exposure=self.wait_after_exposure,
            special_image_techniques=self.special_image_techniques.copy(),
        )

    def fill_with_defaults(
        self, defaults: ExposureSettings, exceptions: list[str] = None
    ):
        # """Fill in None values with defaults."""
        for var in vars(self):
            if exceptions and var in exceptions:
                continue
            if getattr(self, var) is None:
                setattr(self, var, getattr(defaults, var))

class MembraneSettings:
    def __init__(
        self,
        max_membrane_thickness_um: float = 0.0,
        exposure_time: float = 0.0,
        dilation_px: int = 0,
        defocus_um: float = 0.0,
        special_image_techniques: list[SpecialImageTechniques] = [],
    ):
        """
        Initialize membrane settings for membrane exposure.

        Parameters:

        - max_membrane_thickness_um: Maximum membrane thickness in microns.
        - exposure_time: Exposure time for membrane in milliseconds.
        - dilation_px: Dilation in pixels
        - defocus_um: Defocus position in microns.
        - special_image_techniques: List of SpecialImageTechniques to apply.
        """

        self.max_membrane_thickness_um = max_membrane_thickness_um
        self.dilation_px = dilation_px
        self.exposure_settings = ExposureSettings(
            exposure_time=exposure_time,
            relative_focus_position=defocus_um,
            special_image_techniques=special_image_techniques,
        )

    def __eq__(self, other):
        # """Check equality of membrane settings."""
        if not isinstance(other, MembraneSettings):
            return False
        return (
            self.max_membrane_thickness_um == other.max_membrane_thickness_um
            and self.dilation_px == other.dilation_px
            and self.exposure_settings == other.exposure_settings
        )

    def copy(self):
        """Create a copy of the membrane settings."""
        return MembraneSettings(
            max_membrane_thickness_um=self.max_membrane_thickness_um,
            exposure_time=self.exposure_settings.exposure_time,
            dilation_px=self.dilation_px,
            defocus_um=self.exposure_settings.relative_focus_position,
            special_image_techniques=self.exposure_settings.special_image_techniques.copy(),
        )

class SecondaryDoseSettings:
    def __init__(
        self,
        edge_exposure_time: float = None,
        edge_erosion_px: int = 0,
        edge_dilation_px: int = 0,
        roof_exposure_time: float = None,
        roof_erosion_px: int = 0,
        roof_layers_above: int = 0,
    ):
        """
        Initialize secondary dose settings for edges and roofs.

        Parameters:

        - edge_exposure_time: Exposure time for edge features in milliseconds.
        - edge_erosion_px: Erosion in pixels
        - edge_dilation_px: Dilation in pixels
        - roof_exposure_time: Exposure time for roof features in milliseconds.
        - roof_erosion_px: Erosion in pixels
        - roof_layers_above: Number of layers above roof features to apply secondary dose.
        """

        if edge_exposure_time is None:
            if edge_erosion_px > 0 or edge_dilation_px > 0:
                raise ValueError(
                    "Edge exposure time must be set if edge erosion or dilation is specified"
                )
        if roof_exposure_time is None:
            if roof_erosion_px > 0 or roof_layers_above > 0:
                raise ValueError(
                    "Roof exposure time must be set if roof erosion or layers above is specified"
                )
        self.edge_erosion_px = edge_erosion_px
        self.edge_dilation_px = edge_dilation_px
        self.roof_erosion_px = roof_erosion_px
        self.roof_layers_above = roof_layers_above
        self.edge_exposure_settings = ExposureSettings(exposure_time=edge_exposure_time)
        self.roof_exposure_settings = ExposureSettings(
            exposure_time=roof_exposure_time
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
            edge_exposure_time=self.edge_exposure_settings.exposure_time,
            edge_erosion_px=self.edge_erosion_px,
            edge_dilation_px=self.edge_dilation_px,
            roof_exposure_time=self.roof_exposure_settings.exposure_time,
            roof_erosion_px=self.roof_erosion_px,
            roof_layers_above=self.roof_layers_above,
        )
