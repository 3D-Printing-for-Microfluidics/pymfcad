from __future__ import annotations

import datetime


class Settings:
    def __init__(
        self,
        header: Header,
        design: Design,
        burnin_settings: BurninSettings,
        default_position_settings: PositionSettings,
        default_exposure_settings: ExposureSettings,
    ):
        self.burnin = burnin_settings
        self.settings = {
            "Header": vars(header),
            "Design": vars(design),
            "Default layer settings": {
                "Number of duplications": 1,
                "Position settings": vars(default_position_settings),
                "Exposure settings": vars(default_exposure_settings),
            },
        }

    def save(self, filename: str = "settings.json"):
        """Save the settings to a JSON file."""
        import json

        self.settings["Burnin"] = vars(self.burnin)
        with open(filename, "w") as f:
            json.dump(self.settings, f, indent=4)

    @classmethod
    def from_file(cls, filename: str):
        """Load settings from a JSON file."""
        import json

        with open(filename, "r") as f:
            settings_data = json.load(f)
        header = Header(**settings_data["Header"])
        design = Design(**settings_data["Design"])
        burnin = BurninSettings(**settings_data["Burnin"])
        default_position = PositionSettings(
            **settings_data["Default Layer Settings"]["Position Settings"]
        )
        default_exposure = ExposureSettings(
            **settings_data["Default Layer Settings"]["Exposure Settings"]
        )
        return cls(header, design, burnin, default_position, default_exposure)


class Header:
    def __init__(
        self,
        schema_version: str,
        image_directory: str = "slices",
        print_under_vacuum: bool = False,
    ):
        self.header = {
            "Schema version": schema_version,
            "Image directory": image_directory,
            "Print under vacuum": print_under_vacuum,
        }


class ResinType:
    def __init__(
        self,
        monomer: list[tuple[str, float]] = [],
        uv_absorbers: list[tuple[str, float]] = [],
        initiators: list[tuple[str, float]] = [],
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
            isinstance(x, tuple) and len(x) == 2 for x in monomer
        ):
            raise ValueError("Monomer must be a list of tuples (name, percentage)")

        if not isinstance(uv_absorbers, list) or not all(
            isinstance(x, tuple) and len(x) == 2 for x in uv_absorbers
        ):
            raise ValueError("UV absorber must be a list of tuples (name, percentage)")

        if not isinstance(initiators, list) or not all(
            isinstance(x, tuple) and len(x) == 2 for x in initiators
        ):
            raise ValueError("Initiators must be a list of tuples (name, percentage)")

        if not isinstance(additives, list) or not all(
            isinstance(x, tuple) and len(x) == 2 for x in additives
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


class Resolution:
    def __init__(self, px_size: float = 0.0076, px_count: tuple[int, int] = (2560, 1600)):
        if not isinstance(px_size, (int, float)) or px_size <= 0:
            raise ValueError("Pixel size must be a positive number")
        if (
            not isinstance(px_count, tuple)
            or len(px_count) != 2
            or not all(isinstance(x, int) and x > 0 for x in px_count)
        ):
            raise ValueError("Pixel count must be a tuple of two positive integers")
        self.px_size = px_size
        self.px_count = px_count


class Printer:
    def __init__(self, name: str, resolutions: list[Resolution] = Resolution()):
        self.name = name
        self.resolutions = resolutions


class Design:
    def __init__(
        self,
        user: str = "",
        purpose: str = "",
        description: str = "",
        resin: ResinType = None,
        printer: Printer = None,
    ):
        self.design = {
            "User": user,
            "Purpose": purpose,
            "Description": description,
            "Resin": str(resin),
            "3D printer": printer.name,
            "Slicer": "pymfd",
            "Date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }


class BurninSettings:
    def __init__(self, burnin_times: list[int] = [10000, 5000, 2500]):
        self.burnin_times = burnin_times


class PositionSettings:
    def __init__(
        self,
        layer_thickness: float = 10.0,
        distance_up: float = 1.0,
        initial_wait: float = 0.0,
        up_speed: float = 25.0,
        up_acceleration: float = 50.0,
        up_wait: float = 0.0,
        down_speed: float = 20.0,
        down_acceleration: float = 50.0,
        force_squeeze: bool = False,
        squeeze_count: int = 0,
        squeeze_force: float = 0.0,
        squeeze_wait: float = 0.0,
        final_wait: float = 0.0,
    ):
        self.position_settings = {
            "Layer thickness (um)": layer_thickness,
            "Distance up (mm)": distance_up,
            "Initial wait (ms)": initial_wait,
            "BP up speed (mm/sec)": up_speed,
            "BP up acceleration (mm/sec^2)": up_acceleration,
            "BP up wait (ms)": up_wait,
            "BP down speed (mm/sec)": down_speed,
            "BP down acceleration (mm/sec^2)": down_acceleration,
            "Enable force squeeze": force_squeeze,
            "Squeeze count": squeeze_count,
            "Squeeze force (N)": squeeze_force,
            "Squeeze wait (ms)": squeeze_wait,
            "Final wait (ms)": final_wait,
        }


class ExposureSettings:
    def __init__(
        self,
        image_file: str = "",
        grayscale_correction: bool = False,
        image_x_offset: float = 0.0,
        image_y_offset: float = 0.0,
        exposure_time: float = 300.0,
        light_engine: str = "Visitech",
        power_setting: int = 100,
        relative_focus_position: float = 0.0,
        wait_before_exposure: float = 0.0,
        wait_after_exposure: float = 0.0,
    ):
        self.exposure_settings = {
            "Image file": image_file,
            "Do light grayscale correction": grayscale_correction,
            "Image x offset (um)": image_x_offset,
            "Image y offset (um)": image_y_offset,
            "Layer exposure time (ms)": exposure_time,
            "Light engine": light_engine,
            "Light engine power setting": power_setting,
            "Relative focus position (um)": relative_focus_position,
            "Wait before exposure (ms)": wait_before_exposure,
            "Wait after exposure (ms)": wait_after_exposure,
        }


class MembraneSettings:
    def __init__(
        self,
        membrane_thickness: float = 0.0,
        exposure_time: float = 0.0,
        dilation: int = 0,
        defocus: float = 0.0,
    ):
        pass


class EdgeDose:
    def __init__(
        self,
        edge_dose_type: str = "Errosion",
        edge_dose: float = 0.0,
        errosion: int = 0,
        dilation: int = 0,
    ):
        pass


class RoofDose:
    def __init__(
        self,
        layers_above: int = 0,
        roof_dose: float = 0.0,
        roof_errosion: int = 0,
        roof_defocus: float = 0.0,
    ):
        pass
