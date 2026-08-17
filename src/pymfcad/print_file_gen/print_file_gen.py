import re
import os
import cv2
import sys
import json
import copy
import shutil
import datetime
import numpy as np
from PIL import Image
import importlib.util
from pathlib import Path
from typing import Union
from types import ModuleType
from datetime import datetime

from numpy import ma

from pymfcad import __version__ as PYMFCAD_VERSION
from ..backend import slice_component, rle_encode_packed, rle_decode_packed
from .uniqueimagestore import get_unique_path, load_image_from_file, UniqueImageStore
from .json_prettier import pretty_json

from .settings import (
            Printer,
            ResinType,
            MembraneSettings,
            SecondaryDoseSettings,
            ExposureSettings,
            PositionSettings,
        )

from .image_generation import (
            generate_membrane_images_from_folders,
            generate_secondary_images_from_folders,
            generate_exposure_images_from_folders,
            generate_position_images_from_folders,
        )

class ComponentGroup:
    """
    A class representing a group of components with the same pixel size positioned within a single light engine's exposure region.
    """
    def __init__(self, printer: Printer, pixel_size: float, exposure_abs_pos_um: tuple[float, float], light_engine_stitching: tuple[int, int] = (1,1)):
        """
        Initialize a ComponentGroup.
        
        Parameters:
        - printer: The printer object containing printer settings.
        - pixel_size: The pixel size of the components in the group.
        - exposure_abs_pos_um: The absolute position of the exposure region in micrometers.
        - light_engine_stitching: The stitching configuration of the light engine exposure region.
        """
        self.printer = printer
        self.pixel_size = pixel_size
        self.le = self.printer._get_light_engine(pixel_size)
        self.stitching = light_engine_stitching
        self.exposure_abs_pos_um = exposure_abs_pos_um
        self.components = []
        self.positions = []
        self.subcomponent_adjustments = {}

        # validate that the stitching configuration is compatible with the light engine's pixel count and overlap
        region_width_px = self.le.px_count[0] * self.stitching[0] - self.le.stitched_px_overlap[0] * (self.stitching[0] - 1)
        region_height_px = self.le.px_count[1] * self.stitching[1] - self.le.stitched_px_overlap[1] * (self.stitching[1] - 1)
        region_min_x_pos = -region_width_px/2 + self.le.px_count[0]/2 +  exposure_abs_pos_um[0]
        region_min_y_pos = -region_height_px/2 + self.le.px_count[1]/2 + exposure_abs_pos_um[1]
        region_max_x_pos = region_width_px/2 - self.le.px_count[0]/2 + exposure_abs_pos_um[0]
        region_max_y_pos = region_height_px/2 - self.le.px_count[1]/2 + exposure_abs_pos_um[1]
        le_x_limits, le_y_limits = self.le.x_offset_limits, self.le.y_offset_limits
        if region_min_x_pos < le_x_limits[0] or region_max_x_pos > le_x_limits[1]:
            raise ValueError(
                f"Configuration results in exposure region x position limits ({region_min_x_pos}, {region_max_x_pos}) that exceed the light engine's x offset limits {self.le.x_offset_limits}."
            )
        if region_min_y_pos < le_y_limits[0] or region_max_y_pos > le_y_limits[1]:
            raise ValueError(
                f"Configuration results in exposure region y position limits ({region_min_y_pos}, {region_max_y_pos}) that exceed the light engine's y offset limits {self.le.y_offset_limits}."
            )

    def add_component(self, component: "Component", rel_position_px: tuple[float, float]):
        """
        Add a component to the group at a relative position in pixels (centered at 0, 0).

        Parameters:
        - component: The component to add.
        - rel_position_px: The relative position of the component in pixels.
        """

        # validate that the component's pixel size matches the group's pixel size
        if component._px_size != self.pixel_size:
            raise ValueError(
                f"Component pixel size {component._px_size} does not match group pixel size {self.pixel_size}."
            )

        # validate that the component fits within the light engine's exposure region based on the stitching configuration and the component's position
        px_count = self.le.px_count
        stitched_px_overlap=self.le.stitched_px_overlap

        region_width_px = px_count[0] * self.stitching[0] - stitched_px_overlap[0] * (self.stitching[0] - 1)
        region_height_px = px_count[1] * self.stitching[1] - stitched_px_overlap[1] * (self.stitching[1] - 1)
        component_width_px, component_height_px, _ = component.get_size(self.pixel_size, component._layer_size)
        if rel_position_px[0] - component_width_px / 2 < -region_width_px / 2 or rel_position_px[0] + component_width_px / 2 > region_width_px / 2:
            raise ValueError(
                f"Component at relative position {rel_position_px} with width {component_width_px} exceeds the light engine's exposure region width {region_width_px}."
            )
        if rel_position_px[1] - component_height_px / 2 < -region_height_px / 2 or rel_position_px[1] + component_height_px / 2 > region_height_px / 2:
            raise ValueError(
                f"Component at relative position {rel_position_px} with height {component_height_px} exceeds the light engine's exposure region height {region_height_px}."
            )

        component._name = f"Component_{len(self.components)}"
        self.components.append(component)
        self.positions.append(rel_position_px)

    def adjust_subcomponent_light_engine(self, subcomponent_fqn: str, exposure_rel_pos_um: tuple[float, float]):
        """
        Adjust the light engine exposure position for a subcomponent which uses a different light engine than the parent component.

        Parameters:
        - subcomponent_fqn: The fully qualified name of the subcomponent.
        - exposure_rel_pos_um: The relative position of the exposure region in micrometers.
        """
        # check that subcomponent_fqn is a different light engine than the parent component

        self.subcomponent_adjustments[subcomponent_fqn] = exposure_rel_pos_um

    def _get_component_le_offset(self, component: "Component") -> tuple[float, float]:
        """
        Get the light engine offset for a component based on its relative position and any subcomponent adjustments.

        Parameters:
        - component: The component for which to get the light engine offset.

        Returns:
        - A tuple of (x_offset_um, y_offset_um) in micrometers.
        """
        # check if component is in the group
        _component = component
        is_different_px_size = False
        while _component._parent is not None:
            if _component._px_size != _component._parent._px_size:
                is_different_px_size = True
            _component = _component._parent
        root_component = _component

        if component not in self.components and root_component not in self.components:
            return None, None
        elif not is_different_px_size:
            return self.exposure_abs_pos_um
        else:
            # add the TLD light engine offset
            x_offset_um = self.exposure_abs_pos_um[0]
            y_offset_um = self.exposure_abs_pos_um[1]

            # add the top level component's relative position
            root_index = self.components.index(root_component)
            x_offset_um += self.positions[root_index][0] * self.pixel_size * 1000
            y_offset_um += self.positions[root_index][1] * self.pixel_size * 1000

            # add the component's position within the top level component (center to center)
            component_pos = component.get_position(px_size=root_component._px_size, layer_size=root_component._layer_size)
            componet_size = component.get_size(px_size=root_component._px_size, layer_size=root_component._layer_size)
            x_offset_um += ((component_pos[0] + componet_size[0] / 2) - (componet_size[0] / 2)) * root_component._px_size * 1000
            y_offset_um += ((component_pos[1] + componet_size[1] / 2) - (componet_size[1] / 2)) * root_component._px_size * 1000

            # add any subcomponent adjustments for the component and its parents
            for key in component.get_fully_qualified_name():
                if key.startswith(root_component.get_fully_qualified_name()):
                    x_offset_um += self.subcomponent_adjustments.get(key, (0.0, 0.0))[0]
                    y_offset_um += self.subcomponent_adjustments.get(key, (0.0, 0.0))[1]

            return x_offset_um, y_offset_um



class PrintFileGenerator:
    def __init__(
        self,
        filename: str,
        author: str = "",
        purpose: str = "",
        description: str = "",
        component: list["Component"] = None,
        component_groups: list[ComponentGroup] = None,
        printer: Printer = None,
        resin: ResinType = None,
        special_print_techniques: list = None,
        minimize_file: bool = True,
        zip_output: bool = True,
    ):
        """
        Initialize the PrintFileGenerator with a component/component groups and settings.

        Parameters:

        - filename: Name of the output file/folder.
        - author: Name of the author.
        - purpose: Purpose of the print job.
        - description: Description of the print job.
        - component: Used for simple slicing of a single component. If multiple components are used, use component_groups instead.
        - component_groups: List of component groups to be sliced.
        - printer: Printer object containing printer settings.
        - resin: ResinType object containing resin formulation.
        - special_print_techniques: List of SpecialPrintTechniques to apply.
        - minimize_file: Whether to minimize the output file size.
        - zip_output: Whether to output as a zip file.
        """

        # Validation
        if component_groups is not None and component is not None:
            raise ValueError(
                "Cannot provide both component and component_groups. Use one or the other."
            )
        if component is not None:
            # create a component group for the single component
            component_groups = [ComponentGroup(printer, component._px_size, (0, 0))]
            component_groups[0].add_component(component, (0, 0))

        if special_print_techniques is None:
            special_print_techniques = []
        if printer is None or resin is None:
            raise ValueError("Both printer and resin settings must be provided.")

        self.filename = filename
        self.author = author
        self.purpose = purpose
        self.description = description
        self.component_groups = component_groups
        self.printer = printer
        self.resin = resin
        self.special_print_techniques = special_print_techniques
        self.minimize_file = minimize_file
        self.zip_output = zip_output

    def _check_output_exists(self, output_path: str) -> bool:
        """
        Check if the output path already exists.

        Parameters:

        - output_path: Path to check for existing output.

        Returns:

        - True if output exists, False otherwise.
        """

        if self.zip_output:
            output_path = Path(output_path + ".zip")
            return output_path.exists() and output_path.is_file()
        else:
            output_path = Path(output_path)
            return output_path.exists() and output_path.is_dir()

    def _validate_component_and_settings(self):
        pass

    def _generate_temp_directory(self) -> Path:
        """
        Generate a temporary directory for processing.

        :return: Path to the temporary directory.
        """
        # Check for and delete any old temporary directories that match the pattern
        temp_dir_pattern = re.compile(r"tmp_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}")
        for item in Path(".").iterdir():
            if item.is_dir() and temp_dir_pattern.match(item.name):
                try:
                    shutil.rmtree(item)
                    print(f"Deleted old temporary directory: {item}")
                except Exception as e:
                    print(f"Failed to delete {item}: {e}")

        temp_directory = Path(f"tmp_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}")
        temp_directory.mkdir(parents=True, exist_ok=True)
        return temp_directory

    def _copy_script_and_dependencies(self, target_dir: str):
        def _is_local_file(path: Path) -> bool:
            # Paths to exclude: stdlib, site-packages, dist-packages, frozen
            if "site-packages" in str(path):
                return False
            if "dist-packages" in str(path):
                return False
            if str(path).startswith(sys.base_prefix):
                return False
            if str(path).startswith(sys.exec_prefix):
                return False
            return True

        def _get_module_base_dir(module_path: Path) -> Path:
            """
            Determine a base directory so module paths are copied with their package structure.
            For packaged modules, this is the parent of the top-level package directory.
            For standalone modules, this is the module's parent directory.
            """
            current = module_path.parent
            top_package = None

            while (current / "__init__.py").exists():
                top_package = current
                current = current.parent

            if top_package is not None:
                return top_package.parent
            return module_path.parent

        def _copy_file_to_target(file_path: Path, target_dir: Path, base_dir: Path):
            try:
                relative_path = file_path.relative_to(base_dir)
            except ValueError:
                relative_path = file_path.name  # if not under base_dir, just use the filename
    
            destination = target_dir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, destination)
            return relative_path
        
        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        # Copy main script
        main_file = Path(sys.modules["__main__"].__file__).resolve()
        print(f"\tCopying main script: {main_file}")
        base_dir = _get_module_base_dir(main_file)
        main_file = _copy_file_to_target(main_file, target_dir, base_dir)

        # Identify and copy dependencies
        for module_name, module in sys.modules.items():
            if not isinstance(module, ModuleType):
                continue

            module_file = getattr(module, "__file__", None)
            if module_file:
                module_path = Path(module_file).resolve()
                # Only copy local (non-built-in, non-site-package) files
                if _is_local_file(module_path):
                    print(f"\tCopying module: {module_name} -> {module_path}")
                    module_base_dir = _get_module_base_dir(module_path)
                    _copy_file_to_target(module_path, target_dir, module_base_dir)
        return main_file

    def _fill_component_default_settings(self, component, info, fill_layer_position=True):
        def _get_root_component(target):
            current = target
            while current._parent is not None:
                current = current._parent
            return current

        def _relative_origin_mm(child, stop_parent):
            x_mm = 0.0
            y_mm = 0.0
            z_mm = 0.0
            current = child
            while current is not None and current is not stop_parent:
                if current._parent is None:
                    x_mm += current.get_position()[0] * current._px_size
                    y_mm += current.get_position()[1] * current._px_size
                    z_mm += current.get_position()[2] * current._layer_size
                    break
                parent = current._parent
                pos_in_parent = current.get_position(
                    px_size=parent._px_size, layer_size=parent._layer_size
                )
                x_mm += pos_in_parent[0] * parent._px_size
                y_mm += pos_in_parent[1] * parent._px_size
                z_mm += pos_in_parent[2] * parent._layer_size
                current = parent
            return x_mm, y_mm, z_mm


        # Get parent or top-level default settings
        _position_settings = None
        _exposure_settings = None
        if component._parent is not None:
            _position_settings = component._parent.default_position_settings
            _exposure_settings = component._parent.default_exposure_settings
        else:
            _position_settings = self.printer.default_position_settings
            _exposure_settings = self.printer._get_light_engine(component._px_size).default_exposure_settings[0]

        # Fill component default settings
        if component.default_exposure_settings is None:
            component.default_exposure_settings = copy.deepcopy(_exposure_settings)
        else:
            component.default_exposure_settings.fill_with_defaults(_exposure_settings)
        if component.default_position_settings is None:
            component.default_position_settings = copy.deepcopy(_position_settings)
        else:
            component.default_position_settings.fill_with_defaults(_position_settings)


        root_component = _get_root_component(component)

        ###### Fill component specific settings (layer thickness, light engine, etc.) ######
        # Set layer thickness
        component.default_position_settings.layer_thickness = component._layer_size * 1000

        # Add z_offset to slices
        if fill_layer_position:
            _, _, origin_z_mm = _relative_origin_mm(
                component, root_component
            )
            z_offset_um = origin_z_mm * 1000
            print("z_offset_um ({}):".format(component.get_fully_qualified_name()), z_offset_um)
            for slice_info in info["slices"]:
                slice_info["layer_position"] = round(
                    slice_info["layer_position"] + z_offset_um, 1
                )

        # Set light engine name
        le = self.printer._get_light_engine(
            component._px_size,
            component.default_exposure_settings.wavelength,
        )
        component.default_exposure_settings.light_engine = le.name

        # Set image offsets
        component_offset_x_um, component_offset_y_um = None, None
        for group in self.component_groups:
            component_offset_x_um, component_offset_y_um = group._get_component_le_offset(component)
            if component_offset_x_um is not None and component_offset_y_um is not None:
                break

        component.default_exposure_settings.image_x_offset = -round(component_offset_x_um,1)
        component.default_exposure_settings.image_y_offset = -round(component_offset_y_um,1)
        if component.default_exposure_settings.image_x_offset == -0.0:
            component.default_exposure_settings.image_x_offset = 0.0
        if component.default_exposure_settings.image_y_offset == -0.0:
            component.default_exposure_settings.image_y_offset = 0.0

        ###### Fill slice info settings ######
        for i, slice in enumerate(info["slices"]):
            slice["position_settings"] = component.default_position_settings
            slice["exposure_settings"] = copy.deepcopy(component.default_exposure_settings)
            slice["exposure_settings"].image_x_offset = (
                component.default_exposure_settings.image_x_offset
            )
            slice["exposure_settings"].image_y_offset = (
                component.default_exposure_settings.image_y_offset
            )
            slice["exposure_settings"].light_engine = (
                component.default_exposure_settings.light_engine
            )

            # Generate burn-in exposure settings
            if i < len(component.burnin_settings):
                burnin_ms = component.burnin_settings[i]
                resin = self.resin
                denom = resin.bulk_exposure - resin.exposure_offset
                if denom == 0:
                    raise ValueError(
                        "Resin bulk exposure must differ from exposure_offset to compute burn-in multiplier."
                    )
                slice["exposure_settings"].bulk_exposure_multiplier = (
                    (burnin_ms - resin.exposure_offset) / denom
                )
                slice["exposure_settings"].burnin = True

    def _make_secondary_images(self, sliced_components, sliced_components_data, temp_directory, save_temp_files=False):
            print("Make secondary images...")
            for component, info in zip(sliced_components, sliced_components_data):
                print(f"\t{component.get_fully_qualified_name()}")
    
                # Fill default settings for sliced components
                self._fill_component_default_settings(component, info, fill_layer_position=False)
    
                # Generate secondary, membrane, and regional images
                component_subdirectory = temp_directory / component.get_fully_qualified_name()
    
                component_index = sliced_components.index(component)
                for name, (_, settings) in component.regional_settings.items():
                    if settings is None:
                        continue
                    masks_subdirectory = (
                        temp_directory / "masks" / component.get_fully_qualified_name() / name
                    )
    
                    if isinstance(settings, MembraneSettings):
                        settings.exposure_settings.fill_with_defaults(
                            component.default_exposure_settings,
                            exceptions=["bulk_exposure_multiplier"],
                        )
                        generate_membrane_images_from_folders(
                            data=sliced_components_data[component_index],
                            image_dir=component_subdirectory,
                            mask_key=name,
                            membrane_settings=settings,
                            save_temp_files=save_temp_files,
                        )
    
                    if isinstance(settings, SecondaryDoseSettings):
                        settings.edge_exposure_settings.fill_with_defaults(
                            component.default_exposure_settings,
                            exceptions=["bulk_exposure_multiplier"],
                        )
                        settings.roof_exposure_settings.fill_with_defaults(
                            component.default_exposure_settings,
                            exceptions=["bulk_exposure_multiplier"],
                        )
                        generate_secondary_images_from_folders(
                            data=sliced_components_data[component_index],
                            image_dir=component_subdirectory,
                            mask_key=name,
                            settings=settings,
                            resin=self.resin,
                            save_temp_files=save_temp_files,
                        )
    
                    if isinstance(settings, ExposureSettings):
                        settings.fill_with_defaults(
                            component.default_exposure_settings,
                        )
                        generate_exposure_images_from_folders(
                            data=sliced_components_data[component_index],
                            image_dir=component_subdirectory,
                            mask_key=name,
                            settings=settings,
                            save_temp_files=save_temp_files,
                        )
    
                    if isinstance(settings, PositionSettings):
                        settings.fill_with_defaults(
                            component.default_position_settings,
                        )
                        generate_position_images_from_folders(
                            data=sliced_components_data[component_index],
                            mask_key=name,
                            settings=settings,
                        )
            return sliced_components, sliced_components_data

    def _sort_sliced_devices(self, sliced_devices, sliced_devices_data):
        info_by_id = {id(dev): info for dev, info in zip(sliced_devices, sliced_devices_data)}
        
        # Sort by dependency order. We need to find the devices with no subcomponents first, then their parents, and so on.
        _sliced_devices = []
        while len(_sliced_devices) < len(sliced_devices):
            for device, info in zip(sliced_devices, sliced_devices_data):
                if device in _sliced_devices:
                    continue
                positions = info.get("positions", [])
                if all(
                    component._parent is None or component._parent in _sliced_devices for component, _, _, _ in positions
                ):
                    _sliced_devices.append(device)
        _sliced_devices_data = [info_by_id[id(dev)] for dev in _sliced_devices]
        return reversed(_sliced_devices), reversed(_sliced_devices_data)

    def _get_unique_slice_image_path(self, base_name, temp_directory, parent_fqn, z):
        # Build a unique filename including z (and keep original name suffix)
        # Example: original 'slice_01.png' -> 'slice_01_z10.png' (or use get_unique_path)
        name_no_ext = base_name.rsplit(".", 1)[0]
        ext = (
            "." + base_name.rsplit(".", 1)[1]
            if "." in base_name
            else ".png"
        )
        new_name = f"{name_no_ext}_z{z}{ext}"

        # ensure directory exists
        out_dir = (
            temp_directory
            / parent_fqn
        )
        out_dir.mkdir(parents=True, exist_ok=True)

        slice_image_path = out_dir / new_name
        if slice_image_path.exists():
            # get_unique_path should generate a unique name (preserves suffix)
            slice_image_path = get_unique_path(
                out_dir, name_no_ext + f"_z{z}", suffix=ext
            )
        return slice_image_path

    def _embed_component_slices(
            self,
            sliced_devices,
            sliced_devices_data,
            temp_directory,
            save_temp_files
        ):
        embedded_devices = []
        info_by_id = {id(dev): info for dev, info in zip(sliced_devices, sliced_devices_data)}

        # Embed the slices for each device
        _sorted_devices, _sorted_devices_data = self._sort_sliced_devices(sliced_devices, sliced_devices_data)
        for device, info in zip(_sorted_devices, _sorted_devices_data): # Sort sliced devices by dependency order
            print(f"\tEmbedding {device.get_fully_qualified_name()}...")
            slice_list = []
            slice_list.extend(info.get("slices", []))
            slice_list.extend(info.get("membrane_slices", []))
            slice_list.extend(info.get("secondary_slices", []))
            slice_list.extend(info.get("exposure_slices", []))

            # group device instances by parent device
            parents = {}
            for pos in info["positions"]:
                parent = pos[0]._parent
                _id = id(parent) if parent is not None else "TOP_LEVEL"
                if _id not in parents.keys():
                    parents[_id] = {"device": parent, "positions": [pos]}
                else:
                    parents[id(parent)]["positions"].append(pos) 

            # copy slices from component into image the size of the device (translated correctly)
            for _parent_data in parents.values():
                # get parent information
                parent_device = _parent_data["device"]
                parent_positions = _parent_data["positions"]

                light_engine_resolution = self.printer._get_light_engine(
                    device._px_size, device.default_exposure_settings.wavelength
                ).px_count

                # handle top level components and embedded alt-resolutions
                for pos in parent_positions:
                    if parent_device is None or parent_device._px_size != device._px_size:
                        # duplicate info for each if more than 1 copy
                        if len(parent_positions) > 1:
                            _info = copy.deepcopy(info)
                            _slice_list = copy.deepcopy(slice_list)
                        else:
                            _info = info
                            _slice_list = slice_list

                        # set new/updated slice list
                        _info["slices"] = _slice_list

                        # update slices with instance position
                        self._fill_component_default_settings(pos[0], _info)

                        # add to final device list
                        embedded_devices.append((pos[0], _info))

                    else:
                        parent_fqn = parent_device.get_fully_qualified_name()
                        parent_info = info_by_id.get(id(parent_device))
                        if parent_info is None:
                            continue
                        parent_info.setdefault("slices", [])

                        resolution = (
                            int(parent_device.get_size()[0]),
                            int(parent_device.get_size()[1]),
                        )
                    
                        # handle remaining components
                        for slice_index, slice in enumerate(slice_list):
                            # Load the base slice image once (if it exists)
                            slice_img = slice["image_data"]
                            slice_img2 = rle_decode_packed(*slice_img)
                        
                            x = pos[1]
                            y = pos[2]
                            z = round(pos[3], 4)
                            embedded_slice_image = self._embed_image(
                                (x, y),
                                resolution,
                                slice_img2,
                                parent_fqn,
                            )

                            slice_image_path = self._get_unique_slice_image_path(
                                slice["image_name"], temp_directory, parent_fqn, z
                            )

                            # save images if save_temp_files
                            if save_temp_files:
                                cv2.imwrite(str(slice_image_path), embedded_slice_image)

                            print(
                                f"\r\t\tEmbedding {slice_image_path.name} ({slice_index+1}/{len(slice_list)}) at z={z}...",
                                end="",
                                flush=True,
                            )
                            if parent_info is not None:
                                if parent_fqn == "Component_0.Pump1":
                                    print(slice_image_path.name, z*1000, slice["layer_position"], round(slice["layer_position"] + z * 1000, 1))
                                parent_info["slices"].append(
                                    {
                                        "image_name": slice_image_path.name,
                                        "parent": None,
                                        "image_data": rle_encode_packed(embedded_slice_image),
                                        "device": None,
                                        "position": None,
                                        "layer_position": (
                                            round(slice["layer_position"] + z * 1000, 1)
                                        ),
                                        "exposure_settings": slice.get(
                                            "exposure_settings"
                                        ),
                                        "position_settings": slice.get(
                                            "position_settings"
                                        ),
                                    }
                                )
                print()


        ################################################################################

        return embedded_devices

    ########## Stitch Slices ##########

    def _make_json_file_with_header(self, main_file_path, embedded_components):
            print_settings = {
                "Header": {
                    "Schema version": "5.0.0",
                    "Image directory": (
                        "minimized_slices" if self.minimize_file else "slices"
                    ),
                },
                "Design": {
                    "User": self.author,
                    "Purpose": self.purpose,
                    "Description": self.description,
                    "Resin": str(self.resin),
                    "3D printer": self.printer.name,
                    "Design file": str(main_file_path),
                    "Slicer": "PyMFCAD v" + PYMFCAD_VERSION,
                    "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
                "Variables": {},
                "Default layer settings": {
                    "Number of duplications": 1,
                    "Position settings": self.printer.default_position_settings.to_dict(),
                    "Image settings": self.printer.light_engines[0].default_exposure_settings[0].to_dict(self.resin),
                },
                "Named position settings": {},
                "Named image settings": {},
                "Named layer groups": {},
            }
            from pymfcad import SpecialPrintTechniques
            print_settings["Special print techniques"] = SpecialPrintTechniques.to_dict(self.special_print_techniques)
    
            # Update default layer settings based on the first embedded component
            print_settings["Default layer settings"]["Position settings"][
                "Layer thickness (um)"
            ] = (embedded_components[0][0]._layer_size * 1000)
            print_settings["Default layer settings"]["Image settings"]["Image file"] = ""
            print_settings["Default layer settings"]["Image settings"]["Light engine"] = (
                embedded_components[0][0].default_exposure_settings.light_engine
            )
            print_settings["Default layer settings"]["Image settings"][
                "Image x offset (um)"
            ] = embedded_components[0][0].default_exposure_settings.image_x_offset
            print_settings["Default layer settings"]["Image settings"][
                "Image y offset (um)"
            ] = embedded_components[0][0].default_exposure_settings.image_y_offset
    
            return print_settings
    
    def _make_default_named_settings_deepcopy(self, print_settings):
        expanded_named_position_settings = copy.deepcopy(print_settings[
            "Named position settings"
        ])
        expanded_named_position_settings["default"] = print_settings[
            "Default layer settings"
        ]["Position settings"]
        expanded_named_image_settings = copy.deepcopy(print_settings["Named image settings"])
        expanded_named_image_settings["default"] = print_settings[
            "Default layer settings"
        ]["Image settings"]
        return expanded_named_position_settings, expanded_named_image_settings

    def _process_layers(self, 
                        embedded_components, 
                        temp_directory, 
                        print_settings, 
                        slices_folder, 
                        expanded_named_image_settings, 
                        expanded_named_position_settings
                        ):
        print("Combining exposures and compiling print settings...")
        layers = []
        last_layer = 0.0
        last_light_engine = None
        for layer, slices in self._iterate_slices_by_layer(embedded_components):
            print(
                f"\r\tProcessing layer at {layer:.1f} um... ",
                end="",
                flush=True,
            )

            grouped_slices = self._group_images_by_settings(slices)

            layer_thickness = layer - last_layer
            position_settings = None
            layer_settings = {}
            image_settings_list = []

            # Group slices by settings
            for group in grouped_slices:
                group_exposure_settings = None

                group_exposures = [
                    slice_info["exposure_settings"].get_exposure_time(
                        self.resin
                    )
                    for slice_info in group
                ]
                group_images = []
                for slice_info in group:
                    group_images.append(
                        {
                            "component": slice_info.get("component"),
                            "parent": slice_info.get("parent"),
                            "image_data": slice_info["image_data"],
                            "image_name": slice_info["image_name"],
                            "position": slice_info.get("position"),
                        }
                    )

                output_imgs, output_times = self._combine_exposures(
                    group_images, group_exposures, temp_directory
                )

                output_img_files = []
                for i, arr in enumerate(output_imgs):
                    slice_image_path = slices_folder / f"{layer}.png"
                    if slice_image_path.exists():
                        # get_unique_path should generate a unique name (preserves suffix)
                        slice_image_path = get_unique_path(
                            slices_folder, layer, suffix=".png"
                        )
                    if self.minimize_file:
                        slice_image_path = self.unique_image_store.add_image(
                            arr, slice_image_path
                        )
                    else:
                        Image.fromarray(arr).save(slice_image_path)
                    output_img_files.append(slice_image_path.name)

                # Update image settings from slice (just the max of wait times)
                for g, slice_info in enumerate(group):
                    group_exposure_settings = self._update_image_settings_from_slice(slice_info, group_exposure_settings)

                if not print_settings["Default layer settings"]["Image settings"].get("Image file"):
                    if output_img_files:
                        print_settings["Default layer settings"]["Image settings"]["Image file"] = output_img_files[0]

                for file, exp in zip(output_img_files, output_times):
                    # Find closest named image setting
                    exposure_settings = copy.deepcopy(group_exposure_settings)
                    exposure_settings["Layer exposure time (ms)"] = exp
                    current_light_engine = exposure_settings.get("Light engine")
                    if current_light_engine != last_light_engine:
                        le = self.printer.get_light_engine_by_name(
                            current_light_engine
                        )
                        extra_wait = (
                            le.settle_time_ms
                            if le is not None
                            else 0.0
                        )
                        if extra_wait:
                            base_wait = (
                                exposure_settings.get("Wait before exposure (ms)")
                                or 0.0
                            )
                            exposure_settings[
                                "Wait before exposure (ms)"
                            ] = base_wait + extra_wait
                        last_light_engine = current_light_engine

                    match_key = self._match_or_add_new_named_image_settings(
                        group,
                        exposure_settings,
                        expanded_named_image_settings,
                        print_settings,
                    )

                    # Set image settings
                    image_settings = {
                        "Image file": file,
                    }
                    if match_key != "default":
                        image_settings["Using named image settings"] = match_key

                    image_settings_list.append(image_settings)

                # Update position settings from slice
                for g, slice_info in enumerate(group):
                    position_settings = self._update_position_settings_from_slice(slice_info, position_settings, layer_thickness)
                    
            match_key = self._match_or_add_new_named_position_settings(
                layer,
                position_settings,
                expanded_named_position_settings,
                print_settings,
            )

            # Set position settings
            position_settings = {}
            if match_key != "default":
                position_settings["Using named position settings"] = match_key
                layer_settings["Position settings"] = position_settings

            layer_settings["Image settings list"] = image_settings_list
            layers.append(layer_settings)
            last_layer = layer
        return layers
    
    def _iterate_slices_by_layer(self, embedded_components):
        # First, collect all unique layer positions
        layer_positions = set()
        for _, info in embedded_components:
            for slice_info in info.get("slices", []):
                layer_positions.add(slice_info["layer_position"])
            info["slices"].sort(
                key=lambda x: (
                    x["layer_position"],
                    x["exposure_settings"].get_exposure_time(self.resin),
                )
            )

        # Sort layer positions
        sorted_layers = sorted(layer_positions)

        # Iterate by each layer position
        for layer in sorted_layers:
            current_layer_slices = []
            for _, info in embedded_components:
                for slice_info in info.get("slices", []):
                    if slice_info["layer_position"] == layer:
                        current_layer_slices.append(slice_info)
            yield layer, current_layer_slices
    
    def _group_images_by_settings(self, slices):
        """
        Group images by their settings.
        This will return a list of slices where all settings match, except image file, exposure time, and the 2 waits.
        """
        grouped_slices = []

        for slice_info in slices:
            # print(slice_info["image_name"])
            if len(grouped_slices) == 0:
                grouped_slices.append([slice_info])
                continue

            # Check if the current slice matches any of the existing groups
            match_found = False
            for group in grouped_slices:
                # Compare settings, ignoring image file, exposure time, and the 2 waits
                s1 = slice_info["exposure_settings"].to_dict()
                del s1["Image file"]
                del s1["Layer exposure multiplier"]
                del s1["Wait before exposure (ms)"]
                del s1["Wait after exposure (ms)"]

                s2 = group[0]["exposure_settings"].to_dict()
                del s2["Image file"]
                del s2["Layer exposure multiplier"]
                del s2["Wait before exposure (ms)"]
                del s2["Wait after exposure (ms)"]

                if s1 == s2:
                    group.append(slice_info)
                    match_found = True
                    break

            if not match_found:
                grouped_slices.append([slice_info])

        grouped_slices.sort(
            key=lambda group: (
                group[0]["exposure_settings"].light_engine,
                group[0]["exposure_settings"].image_x_offset,
                group[0]["exposure_settings"].image_y_offset,
                group[0]["exposure_settings"].relative_focus_position,
                group[0]["exposure_settings"].power_setting,
                group[0]["exposure_settings"].grayscale_correction,
            )
        )
        return grouped_slices

    def _embed_image(self, pos, resolution, image_data, fqn):
            x = round(pos[0])
            y = round(pos[1])
    
            slice_img = image_data
    
            # Create a new empty image sized to the component
            slice_image = np.zeros((resolution[1], resolution[0]), dtype=np.uint8)
    
            # Correct for numpy image origin (if you want origin at bottom-left)
            paste_y = resolution[1] - y
    
            # compute paste coordinates (top-left y coordinate for the slice_img)
            top = paste_y - slice_img.shape[0]
            left = x
            bottom = top + slice_img.shape[0]
            right = left + slice_img.shape[1]
    
            # Clip coordinates to image bounds to avoid exceptions
            top_clip = max(top, 0)
            left_clip = max(left, 0)
            bottom_clip = min(bottom, resolution[1])
            right_clip = min(right, resolution[0])
    
            # compute corresponding region in slice_img
            src_top = top_clip - top if top < 0 else 0
            src_left = left_clip - left if left < 0 else 0
            src_bottom = src_top + (bottom_clip - top_clip)
            src_right = src_left + (right_clip - left_clip)
    
            # Only paste if there's an overlap
            if bottom_clip > top_clip and right_clip > left_clip:
                try:
                    slice_image[top_clip:bottom_clip, left_clip:right_clip] = slice_img[
                        src_top:src_bottom, src_left:src_right
                    ]
                except Exception as e:
                    print(
                        f"⚠️Warning: trouble pasting slice image for {fqn} at x={x},y={y}: {e}"
                    )
    
            else:
                print(
                    f"⚠️Warning: slice image for {fqn} at x={x},y={y} is completely outside component bounds"
                )
                # still save an empty image or skip; here we'll skip
    
            return slice_image

    def _combine_exposures(self, images, exposure_times, temp_directory):
        """
        Combine binary images into minimal exposure layers using the exposure-sum method.
        Optimized to avoid repeated min-searches and masking.
        """

        def image_from_dict(slice_info):
            image = rle_decode_packed(*slice_info["image_data"])
            if slice_info.get("parent") is None:
                return image

            # # local embedding
            # resolution = (
            #     int(slice_info["parent"].get_size()[0]),
            #     int(slice_info["parent"].get_size()[1]),
            # )
            # return self._embed_image(
            #     slice_info["position"],
            #     resolution,
            #     image,
            #     slice_info["component"].get_fully_qualified_name(),
            # )

        H = 0
        W = 0
        for image in images:
            if type(image) is not dict:
                H, W = image.shape
                break
        if H == 0 or W == 0:
            H, W = image_from_dict(images[0]).shape

        # mask = np.array(image_paths)
        # N, H, W = mask.shape

        if len(images) == 1:
            if type(images[0]) is dict:
                return [image_from_dict(images[0])], exposure_times
            else:
                return images, exposure_times

        exposure_sum = np.zeros((H, W), dtype=float)
        for image, exp in zip(images, exposure_times):
            if type(image) is dict:
                img = image_from_dict(image)
                # if save_temp_files:
                #     debug_path = temp_directory / (image["parent"].get_fully_qualified_name() if image.get("parent") is not None else "no_parent") / f"{image['position']}_{image['image_name']}"
                #     cv2.imwrite(str(debug_path), img)
            else:
                img = image
            exposure_sum[img == 255] += exp

        # Find all unique nonzero exposures, sorted ascending
        unique_exposures = np.unique(exposure_sum[exposure_sum > 0])
        # print("Unique exposures:", unique_exposures)
        output_images = []
        output_exposures = []

        prev = 0
        for exp in unique_exposures:
            # Mask for pixels with exposure >= exp
            layer_mask = exposure_sum >= exp
            out_img = layer_mask.astype(np.uint8) * 255
            output_images.append(out_img)
            output_exposures.append(exp - prev)
            prev = exp

        return output_images, output_exposures

    def _update_image_settings_from_slice(self, slice_info, group_exposure_settings):
        new_image_settings = (
            slice_info["exposure_settings"].to_dict(
                self.resin
            )
        )

        if group_exposure_settings is None:
            group_exposure_settings = new_image_settings
        if (
            new_image_settings["Wait before exposure (ms)"]
            > group_exposure_settings["Wait before exposure (ms)"]
        ):
            group_exposure_settings["Wait before exposure (ms)"] = (
                new_image_settings["Wait before exposure (ms)"]
            )
        if (
            new_image_settings["Wait after exposure (ms)"]
            > group_exposure_settings["Wait after exposure (ms)"]
        ):
            group_exposure_settings["Wait after exposure (ms)"] = (
                new_image_settings["Wait after exposure (ms)"]
            )
        return group_exposure_settings

    def _match_or_find_closest_named_setting(
        self, settings, named_settings, ignore_keys=None
    ):
        if ignore_keys is None:
            ignore_keys = []

        def dict_without_keys(d, keys):
            return {k: v for k, v in d.items() if k not in keys}

        settings_filtered = dict_without_keys(settings, ignore_keys)

        best_match_key = None
        fewest_differences = None
        differences_in_best = {}

        for key, _settings in named_settings.items():
            _settings_filtered = dict_without_keys(_settings, ignore_keys)

            if settings_filtered == _settings_filtered:
                # Exact match
                return key, {}

            # Calculate differences
            differences = {
                k: settings_filtered.get(k)
                for k in set(settings_filtered) | set(_settings_filtered)
                if settings_filtered.get(k) != _settings_filtered.get(k)
            }

            num_differences = len(differences)

            if fewest_differences is None or num_differences < fewest_differences:
                best_match_key = key
                fewest_differences = num_differences
                differences_in_best = differences

        return best_match_key, differences_in_best

    def _get_unique_settings_name(self, stem: str, existing_list: list = []) -> Path:
        """
        Generate a unique file path by appending optional postfix and then _n if needed.
        E.g., stem_postfix.png, stem_postfix_1.png, etc.
        """
        count = 0
        while True:
            if count == 0:
                name = stem
            else:
                name = f"{stem}_{count}"
            if not name in existing_list:
                return name
            count += 1
    
    def _match_or_add_new_named_image_settings(self, group, exposure_settings, expanded_named_image_settings, print_settings):
        match_key, match_dict = self._match_or_find_closest_named_setting(
            exposure_settings,
            expanded_named_image_settings,
            ["Image file"],
        )

        # If no match add new named image settings
        if len(match_dict) != 0:
            if len(group) > 1 and not "_" in group[0]["image_name"][-14:]:
                settings_name = re.sub(
                    r"-slice\d+", "", group[1]["image_name"]
                ).split(".png")[0]
            else:
                settings_name = re.sub(
                    r"-slice\d+", "", group[0]["image_name"]
                ).split(".png")[0]
    
            if group[0]["exposure_settings"].burnin:
                settings_name += "_burnin"
    
            # if settings_name exists, create a new name
            if settings_name in expanded_named_image_settings:
                settings_name = self._get_unique_settings_name(
                    settings_name,
                    existing_list=expanded_named_image_settings.keys(),
                )
    
            # set named image settings
            image_settings = copy.deepcopy(match_dict)
            if match_key != "default":
                image_settings["Using named image settings"] = match_key
            print_settings["Named image settings"][
                settings_name
            ] = image_settings
            match_key = settings_name
    
            # set expanded named image settings
            expanded_named_image_settings[match_key] = exposure_settings
        
        return match_key

    def _update_position_settings_from_slice(self, slice_info, position_settings, layer_thickness):
        new_position_settings = slice_info["position_settings"].to_dict()
        if position_settings is None:
            position_settings = new_position_settings
            position_settings["Layer thickness (um)"] = layer_thickness
        else:
            for key in [
                "Distance up (mm)",
                "Initial wait (ms)",
                "Up wait (ms)",
                "Final wait (ms)",
            ]:
                if new_position_settings.get(
                    key, 1e10
                ) > position_settings.get(key, 0):
                    position_settings[key] = new_position_settings[key]
            if "Special layer techniques" in new_position_settings:
                if "Special layer techniques" not in position_settings:
                    position_settings["Special layer techniques"] = {}
                new_special = new_position_settings[
                    "Special layer techniques"
                ]
                if "Squeeze out resin" in new_special:
                    current = position_settings[
                        "Special layer techniques"
                    ].get("Squeeze out resin", {})
                    incoming = new_special["Squeeze out resin"]
                    position_settings["Special layer techniques"][
                        "Squeeze out resin"
                    ] = {
                        "Enable squeeze": current.get(
                            "Enable squeeze", False
                        )
                        or incoming.get("Enable squeeze", False),
                        "Squeeze count": max(
                            current.get("Squeeze count", 0),
                            incoming.get("Squeeze count", 0),
                        ),
                        "Squeeze force (N)": max(
                            current.get("Squeeze force (N)", 0.0),
                            incoming.get("Squeeze force (N)", 0.0),
                        ),
                        "Squeeze time (ms)": max(
                            current.get("Squeeze time (ms)", 0.0),
                            incoming.get("Squeeze time (ms)", 0.0),
                        ),
                    }
            for key in [
                "BP up speed (mm/sec)",
                "BP up acceleration (mm/sec^2)",
                "BP down speed (mm/sec)",
                "BP down acceleration (mm/sec^2)",
            ]:
                if new_position_settings.get(
                    key, 0
                ) < position_settings.get(key, 1e10):
                    position_settings[key] = new_position_settings[key]
        return position_settings

    def _match_or_add_new_named_position_settings(self, layer, position_settings, expanded_named_position_settings, print_settings):
        # Find closest named position setting
        match_key, match_dict = self._match_or_find_closest_named_setting(
            position_settings,
            expanded_named_position_settings,
        )

        # If no match add new named position settings
        if len(match_dict) != 0:
            settings_name = f"z_{layer}"

            # set named position settings
            _position_settings = copy.deepcopy(match_dict)
            if match_key != "default":
                _position_settings["Using named position settings"] = match_key
            print_settings["Named position settings"][
                settings_name
            ] = _position_settings
            match_key = settings_name

            # set expanded named image settings
            expanded_named_position_settings[match_key] = position_settings

    def _minimize_json(self, print_settings: dict, layers: list):
        # Minimize json
        print()
        print("Minimizing json...")
        new_layers = []
        last_layer = None
        for i, layer in enumerate(layers):
            if last_layer != None:
                position_setting_equality = last_layer.get(
                    "Position settings", None
                ) == layer.get("Position settings", None)
                image_setting_equality = last_layer.get(
                    "Image settings list", None
                ) == layer.get("Image settings list", None)
                if position_setting_equality and image_setting_equality:
                    duplication = int(last_layer.get("Number of duplications", 1))
                    duplication += 1
                    last_layer["Number of duplications"] = duplication
                    new_layers[-1] = last_layer
                else:
                    new_layers.append(layer)
                    last_layer = layer
            else:
                new_layers.append(layer)
                last_layer = layer
        print_settings["Layers"] = new_layers

    def _strip_xy_offsets(self, print_settings: dict):
        if not self.printer.xy_stage_available:
            def _strip_offsets(image_settings: dict):
                image_settings.pop("Image x offset (um)", None)
                image_settings.pop("Image y offset (um)", None)

            _strip_offsets(print_settings["Default layer settings"]["Image settings"])
            for image_settings in print_settings["Named image settings"].values():
                _strip_offsets(image_settings)

    def _strip_vacuum_settings(self, print_settings: dict):
         if "Special print techniques" in print_settings:
            vacuum_settings = print_settings["Special print techniques"].get(
                "Print under vacuum"
            )
            if vacuum_settings is not None and not self.printer.vacuum_available:
                if vacuum_settings.get("Enable vacuum"):
                    print(
                        "⚠️Warning: Vacuum printing requested but not supported by the printer. "
                        "Removing vacuum settings from output JSON."
                    )
                print_settings.pop("Special print techniques", None)

    def _strip_grayscale_settings(self, print_settings: dict, expanded_named_image_settings: dict):
        def _light_engine_supports_grayscale(light_engine_name: str, wavelength: int) -> bool:
            for le in self.printer.light_engines:
                if le.name != light_engine_name:
                    continue
                if wavelength in le.wavelengths:
                    index = le.wavelengths.index(wavelength)
                    if index < len(le.grayscale_available):
                        return le.grayscale_available[index]
                return False
            return False

        grayscale_unsupported_requests = []
        for name, settings in expanded_named_image_settings.items():
            if settings.get("Do grayscale correction"):
                le_name = settings.get("Light engine")
                wavelength = settings.get("Light engine wavelength (nm)")
                if not _light_engine_supports_grayscale(le_name, wavelength):
                    grayscale_unsupported_requests.append((name, le_name, wavelength))

        if grayscale_unsupported_requests:
            details = ", ".join(
                f"{n} (engine={le}, wavelength={wl}nm)"
                for n, le, wl in grayscale_unsupported_requests
            )
            print(
                "⚠️Warning: Grayscale correction requested but not supported by the printer. "
                f"Removing grayscale settings from output JSON. Affected settings: {details}."
            )

        def _strip_grayscale(image_settings: dict):
            image_settings.pop("Do grayscale correction", None)

        default_image_settings = print_settings["Default layer settings"]["Image settings"]
        if not _light_engine_supports_grayscale(
            default_image_settings.get("Light engine"),
            default_image_settings.get("Light engine wavelength (nm)"),
        ):
            _strip_grayscale(default_image_settings)

        for name, image_settings in print_settings["Named image settings"].items():
            full_settings = expanded_named_image_settings.get(name, {})
            if not _light_engine_supports_grayscale(
                full_settings.get("Light engine"),
                full_settings.get("Light engine wavelength (nm)"),
            ):
                _strip_grayscale(image_settings)

    def run(self, overwrite=False, save_temp_files=False) -> bool:
        """
        Generate a print file based on the provided component and settings.
        This function will create a temporary directory, slice the component's components,
        generate secondary and membrane images, create a JSON file with the print data,
        and create a print job zip or directory.

        Parameters:

        - overwrite (bool): If True, existing output files will be overwritten. If False, the function will check for existing output and return False if it exists.
        - save_temp_files (bool): If True, the temporary files will be saved for debugging purposes.
        """
        error = None
        try:

            # Check if output already exists
            if not overwrite and self._check_output_exists(self.filename):
                print(
                    f"Output already exists at {self.filename}. Please select a different path."
                )
                return False

            # validate the component and settings before proceeding
            self._validate_component_and_settings()

            # Create a temporary directory for processing
            temp_directory = self._generate_temp_directory()

            # Copy code to the temporary directory
            print("Copying script and dependencies...")
            main_file_path = self._copy_script_and_dependencies(temp_directory)

            sliced_components = []
            sliced_components_data = []

            # Slice the component components
            slice_dir = temp_directory if save_temp_files else None
            print("Slicing...")
            for group in self.component_groups:
                for component in group.components:
                    slice_component(
                        component, slice_dir, sliced_components, sliced_components_data
                    )

            # Generate secondary images
            sliced_components, sliced_components_data = self._make_secondary_images(
                sliced_components, sliced_components_data, temp_directory, save_temp_files
            )

            # Make print slices directory
            if self.minimize_file:
                slices_folder = temp_directory / f"minimized_slices"
                self.unique_image_store = {}
                self.unique_image_store = UniqueImageStore(slices_folder)
            else:
                slices_folder = temp_directory / "slices"
                os.mkdir(slices_folder)

            # Embed component slices into components
            print("Embedding component images...")
            embedded_components = self._embed_component_slices(
                sliced_components, sliced_components_data, temp_directory, save_temp_files
            )

            # # Process stitched slices (numpy slice the images)
            # print("Processing stitched slices...")
            # for component, info in embedded_components:


            # Make JSON file
            print_settings_filename = temp_directory / "print_settings.json"
            print_settings = self._make_json_file_with_header(main_file_path, embedded_components)

            # Create copies of named image settings. These include the defaults and are fully expanded for comparision
            expanded_named_position_settings, expanded_named_image_settings = self._make_default_named_settings_deepcopy(print_settings)

            layers = self._process_layers(
                embedded_components, 
                temp_directory, 
                print_settings, 
                slices_folder, 
                expanded_named_image_settings, 
                expanded_named_position_settings
            )

            # Minimize JSON
            if not self.minimize_file:
                print_settings["Layers"] = layers
            else:
                self._minimize_json(print_settings, layers)

            # Strip unsupported settings based on printer capabilities
            self._strip_xy_offsets(print_settings)
            self._strip_vacuum_settings(print_settings)
            self._strip_grayscale_settings(print_settings, expanded_named_image_settings)

            # Save json
            with open(print_settings_filename, "w", newline="\r\n") as fileOut:
                json.dump(pretty_json(print_settings), fileOut, indent=2)


            # Delete component and mask folders
            if not save_temp_files:
                print("Cleaning up temporary directories...")
                for component in sliced_components:
                    component_subdirectory = temp_directory / component.get_fully_qualified_name()
                    if component_subdirectory.exists():
                        shutil.rmtree(component_subdirectory)
                masks_directory = temp_directory / "masks"
                if masks_directory.exists():
                    shutil.rmtree(masks_directory)

            # Zip if requested
            if self.zip_output:
                print("Zipping output...")
                shutil.make_archive(self.filename, "zip", temp_directory)
                print(f"Output at {self.filename}...")
                # Remove the temporary directory
                shutil.rmtree(temp_directory)
            else:
                print(f"Moving output directory to {self.filename}...")
                # Move the temporary directory to the output path
                if os.path.exists(self.filename):
                    shutil.rmtree(self.filename)
                shutil.move(temp_directory, self.filename)
        
        except Exception as e:
            error = e
            import traceback
            print(
                f"❌ An error occurred during slicing: {e}. Removing temorary directory."
            )
            print(traceback.format_exc())

        finally:
            if not save_temp_files or error is None:
                # Clean up the temporary directory
                try:
                    shutil.rmtree(temp_directory)
                except Exception:
                    pass
            pass
        