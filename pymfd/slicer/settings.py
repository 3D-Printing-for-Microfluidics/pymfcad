from __future__ import annotations

import json
import datetime


class Settings:
    def __init__(
        self,
        printer: Printer,
        resin: ResinType,
        default_position_settings: PositionSettings,
        default_exposure_settings: ExposureSettings,
        print_under_vacuum: bool = False,
        user: str = "",
        purpose: str = "",
        description: str = "",
    ):
        self.resin = resin
        self.printer = printer

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
        if default_position_settings.force_squeeze is None:
            default_position_settings.force_squeeze = False
        if default_position_settings.squeeze_count is None:
            default_position_settings.squeeze_count = 0
        if default_position_settings.squeeze_force is None:
            default_position_settings.squeeze_force = 0.0
        if default_position_settings.squeeze_wait is None:
            default_position_settings.squeeze_wait = 0.0
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
            "Print under vacuum": print_under_vacuum,
            "User": user,
            "Purpose": purpose,
            "Description": description,
            "Resin": str(resin),
            "3D printer": printer.name,
            "Slicer": "pymfd",
            "Date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Default layer settings": {
                "Number of duplications": 1,
                "Position settings": default_position_settings.to_dict(),
                "Image settings": default_exposure_settings.to_dict(),
            },
        }

    def save(self, filename: str = "settings.json"):
        """Save the settings to a JSON file."""
        save_settings = self.settings.copy()
        save_settings["Resin"] = vars(self.resin)
        save_settings["Printer name"] = self.printer.name
        save_settings["Printer xy stage available"] = self.printer.xy_stage_available
        save_settings["Printer vacuum available"] = self.printer.vaccum_available
        save_settings["Printer light engines"] = [
            vars(le) for le in self.printer.light_engines
        ]
        default_position_settings = vars(self.default_position_settings).copy()
        del default_position_settings["layer_thickness"]
        save_settings["Default position settings"] = default_position_settings
        default_exposure_settings = vars(self.default_exposure_settings).copy()
        del default_exposure_settings["image_file"]
        del default_exposure_settings["image_x_offset"]
        del default_exposure_settings["image_y_offset"]
        del default_exposure_settings["light_engine"]
        save_settings["Default exposure settings"] = default_exposure_settings
        del save_settings["3D printer"]
        del save_settings["Default layer settings"]
        with open(filename, "w") as f:
            json.dump(save_settings, f, indent=4)

    @classmethod
    def from_file(cls, filename: str):
        """Load settings from a JSON file."""
        with open(filename, "r") as f:
            settings_data = json.load(f)
        resin = ResinType(**settings_data["Resin"])
        light_engines = [
            LightEngine(**le) for le in settings_data["Printer light engines"]
        ]
        printer = Printer(
            settings_data["Printer name"],
            light_engines,
            settings_data["Printer xy stage available"],
            settings_data["Printer vacuum available"],
        )
        default_position = PositionSettings(**settings_data["Default position settings"])
        default_exposure = ExposureSettings(**settings_data["Default exposure settings"])
        return cls(
            print_under_vacuum=settings_data["Print under vacuum"],
            user=settings_data["User"],
            purpose=settings_data["Purpose"],
            description=settings_data["Description"],
            resin=resin,
            printer=printer,
            default_position_settings=default_position,
            default_exposure_settings=default_exposure,
        )


class ResinType:
    def __init__(
        self,
        monomer: list[tuple[str, float]] = [("PEG", 100)],
        uv_absorbers: list[tuple[str, float]] = [("NPS", 2.0)],
        initiators: list[tuple[str, float]] = [("IRG", 1.0)],
        additives: list[tuple[str, float]] = [],
    ):
        # Resin naming convention:
        # Use 3 letter abbreviations for materials.
        # Follow with a dash and the percent amount of the material
        # If it's a monomer or oligimer, the percent is the fraction of total monomer/oligimer
        # If it's an absorber, photoinitiator, or additive, the percent is a w/w fraction of the total resin mass
        # When there are multiple materials in a category, separate them with a single underscore, _
        # Separate categories of materials with two underscores, __
        # Schema: MoA-XX_MoB-XX__AbA-XX_AbB-XX__PIA-XX_PIB_XX__AdA-XX_AdB-XX
        # where:
        #     MoA, MoB - monomers A and B
        #     AbA, AbB - absorbers A and B
        #     PIA, PIB - photoinitiators A and B
        #     AdA, AdB - additives A and B
        #     XX - number

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


class Printer:
    def __init__(
        self,
        name: str,
        light_engines: list[LightEngine] = LightEngine(),
        xy_stage_available: bool = False,
        vaccum_available: bool = False,
    ):
        self.name = name
        self.light_engines = (
            [light_engines] if isinstance(light_engines, LightEngine) else light_engines
        )
        self.xy_stage_available = xy_stage_available
        self.vaccum_available = vaccum_available

    def save(self, filename: str):
        """Save the printer settings to a JSON file."""
        printer_data = {
            "name": self.name,
            "light_engines": [vars(le) for le in self.light_engines],
            "xy_stage_available": self.xy_stage_available,
            "vaccum_available": self.vaccum_available,
        }
        with open(filename, "w") as f:
            json.dump(printer_data, f, indent=4)

    @classmethod
    def from_file(cls, filename: str):
        with open(filename, "r") as f:
            printer_data = json.load(f)
        light_engines = [LightEngine(**le) for le in printer_data["light_engines"]]
        return cls(
            printer_data["name"],
            light_engines,
            printer_data["xy_stage_available"],
            printer_data["vaccum_available"],
        )

    def get_light_engine(self, px_size, px_count, wavelength):
        """Get the light engine with the specified pixel size, pixel count, and wavelength."""
        for le in self.light_engines:
            if (
                le.px_size == px_size
                and le.px_count[0] == px_count[0]
                and le.px_count[1] == px_count[1]
                and wavelength in le.wavelengths
            ):
                return le
        raise ValueError("No matching light engine found")


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
        force_squeeze: bool = None,
        squeeze_count: int = None,
        squeeze_force: float = None,
        squeeze_wait: float = None,
        final_wait: float = None,
    ):
        # DEFAULT VALUES
        # # layer_thickness: float = 10.0,
        # distance_up: float = 1.0,
        # initial_wait: float = 0.0,
        # up_speed: float = 25.0,
        # up_acceleration: float = 50.0,
        # up_wait: float = 0.0,
        # down_speed: float = 20.0,
        # down_acceleration: float = 50.0,
        # force_squeeze: bool = False,
        # squeeze_count: int = 0,
        # squeeze_force: float = 0.0,
        # squeeze_wait: float = 0.0,
        # final_wait: float = 0.0,

        self.layer_thickness = None
        self.distance_up = distance_up
        self.initial_wait = initial_wait
        self.up_speed = up_speed
        self.up_acceleration = up_acceleration
        self.up_wait = up_wait
        self.down_speed = down_speed
        self.down_acceleration = down_acceleration
        self.force_squeeze = force_squeeze
        self.squeeze_count = squeeze_count
        self.squeeze_force = squeeze_force
        self.squeeze_wait = squeeze_wait
        self.final_wait = final_wait

    def to_dict(self):
        """Convert position settings to a dictionary."""
        return {
            "Layer thickness (um)": self.layer_thickness,
            "Distance up (mm)": self.distance_up,
            "Initial wait (ms)": self.initial_wait,
            "BP up speed (mm/sec)": self.up_speed,
            "BP up acceleration (mm/sec^2)": self.up_acceleration,
            "Up wait (ms)": self.up_wait,
            "BP down speed (mm/sec)": self.down_speed,
            "BP down acceleration (mm/sec^2)": self.down_acceleration,
            "Enable force squeeze": self.force_squeeze,
            "Squeeze count": self.squeeze_count,
            "Squeeze force (N)": self.squeeze_force,
            "Squeeze wait (ms)": self.squeeze_wait,
            "Final wait (ms)": self.final_wait,
        }

    def __eq__(self, other):
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
            force_squeeze=self.force_squeeze,
            squeeze_count=self.squeeze_count,
            squeeze_force=self.squeeze_force,
            squeeze_wait=self.squeeze_wait,
            final_wait=self.final_wait,
        )

    def fill_with_defaults(
        self, defaults: PositionSettings, exceptions: list[str] = None
    ):
        for var in vars(self):
            if exceptions and var in exceptions:
                continue
            if getattr(self, var) is None:
                setattr(self, var, getattr(defaults, var))


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
        on_film: bool = False,
        **kwargs,
    ):
        # DEFAULT VALUES
        # # image_file: str = "out0001.png",
        # grayscale_correction: bool = False,
        # # image_x_offset: float = 0.0,
        # # image_y_offset: float = 0.0,
        # exposure_time: float = 0.0,
        # # light_engine: str = "visitech",
        # power_setting: int = 100,
        # wavelength: int = 365,
        # relative_focus_position: float = 0.0,
        # wait_before_exposure: float = 0.0,
        # wait_after_exposure: float = 0.0,

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
        self.on_film = on_film
        self.burnin = False

    def to_dict(self):
        """Convert exposure settings to a dictionary."""
        return {
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

    def __eq__(self, other):
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
            on_film=self.on_film,
        )

    def fill_with_defaults(
        self, defaults: ExposureSettings, exceptions: list[str] = None
    ):
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
        on_film: bool = False,
    ):
        self.max_membrane_thickness_um = max_membrane_thickness_um
        self.dilation_px = dilation_px
        self.exposure_settings = ExposureSettings(
            exposure_time=exposure_time,
            relative_focus_position=defocus_um,
            on_film=on_film,
        )

    def __eq__(self, other):
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
            on_film=self.exposure_settings.on_film,
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
        roof_on_film: bool = False,
    ):
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
            exposure_time=roof_exposure_time, on_film=roof_on_film
        )

    def __eq__(self, other):
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
            roof_on_film=self.roof_exposure_settings.on_film,
        )
