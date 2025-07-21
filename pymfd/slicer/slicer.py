# Processing a exposure device with settings
# Check if output already exists
# Create temp folder
# Copy code to temp folder
# slicing() -> images at px_size and layer_size
# 	check if in unique_component_index
# 		if not unique return else add to index
# 	union bulk
# 	subtract shapes
# 	_loop_components()
# 		if not exposure device
# 			if layer_size is equal
# 				_loop_components()
# 			else:
# 				slicing() in own directory
# 		else:
# 			slicing() in new directory
# 	slice at layer_size
# 		slice
# 		add to index of image_name and layer position
# 	If layers align, merge images
# Generate secondary and membrane images
# Generate JSON
# 	make minimal slices folder
# Create print job zip/directory
# Clean up temp folder

import re
import os
import cv2
import sys
import json
import shutil
import numpy as np
import importlib.util
from pathlib import Path
from typing import Union
from types import ModuleType
from datetime import datetime

# from .secondary_image_generation import generate_secondary_images

# from .generate_print_file import create_print_file
from ..backend import slice_component
from .uniqueimagestore import get_unique_path, load_image_from_file, UniqueImageStore
from .json_prettier import pretty_json


class Slicer:
    def __init__(
        self,
        device,
        settings: dict,
        filename: str,
        minimize_file: bool = True,
        zip_output: bool = True,
    ):
        """
        ###### Initialize the Slicer with a device and settings.

        ###### Parameters:
        - device: Device to be sliced.
        - settings: Slicer settings dictionary.
        - filename: Name of the output file.
        - zip_output: Whether to output as a zip file.
        """
        self.device = device
        self.settings = settings
        self.filename = filename
        self.minimize_file = minimize_file
        self.zip_output = zip_output

    def check_output_exists(self, output_path: str) -> bool:
        """
        ###### Check if the output path already exists.

        ###### Parameters:
        - output_path: Path to check for existing output.

        ###### Returns:
        - True if output exists, False otherwise.
        """

        if self.zip_output:
            output_path = Path(output_path + ".zip")
            return output_path.exists() and output_path.is_file()
        else:
            output_path = Path(output_path)
            return output_path.exists() and output_path.is_dir()

    def generate_temp_directory(self) -> Path:
        """
        Generate a temporary directory for processing.

        :return: Path to the temporary directory.
        """
        temp_directory = Path(f"tmp_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}")
        temp_directory.mkdir(parents=True, exist_ok=True)
        return temp_directory

    def _copy_script_and_dependencies(self, target_dir: str):
        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        # Copy main script
        main_file = Path(sys.modules["__main__"].__file__).resolve()
        print(f"\tCopying main script: {main_file}")
        main_file = self._copy_file_to_target(main_file, target_dir, Path.cwd())

        # Identify and copy dependencies
        for module_name, module in sys.modules.items():
            if not isinstance(module, ModuleType):
                continue

            module_file = getattr(module, "__file__", None)
            if module_file:
                module_path = Path(module_file).resolve()
                # Only copy local (non-built-in, non-site-package) files
                if self._is_local_file(module_path):
                    print(f"\tCopying module: {module_name} -> {module_path}")
                    self._copy_file_to_target(module_path, target_dir, Path.cwd())
        return main_file

    def _is_local_file(self, path: Path) -> bool:
        # Paths to exclude: stdlib, site-packages, dist-packages, frozen
        if "site-packages" in str(path):
            return False
        if "dist-packages" in str(path):
            return False
        if str(path).startswith(sys.base_prefix):
            return False
        if str(path).startswith(sys.exec_prefix):
            return False
        return str(path).startswith(str(Path.cwd()))

    def _copy_file_to_target(self, file_path: Path, target_dir: Path, base_dir: Path):
        try:
            relative_path = file_path.relative_to(base_dir)
        except ValueError:
            relative_path = file_path.name  # if not under base_dir, just use the filename

        destination = target_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, destination)
        return relative_path

    def _fill_device_settings(self, device, info):
        settings_owner = device._parent if device._parent is not None else self.settings
        if device.default_exposure_settings is None:
            device.default_exposure_settings = (
                settings_owner.default_exposure_settings.copy()
            )
        else:
            device.default_exposure_settings.fill_with_defaults(
                settings_owner.default_exposure_settings,
            )
        if device.default_position_settings is None:
            device.default_position_settings = (
                settings_owner.default_position_settings.copy()
            )
        else:
            device.default_position_settings.fill_with_defaults(
                settings_owner.default_position_settings,
            )

        for slice in info["slices"]:
            slice["exposure_settings"] = device.default_exposure_settings
            slice["position_settings"] = device.default_position_settings

    def _make_secondary_images(
        self, device, temp_directory, sliced_devices, sliced_devices_info
    ):
        from . import (
            generate_membrane_images_from_folders,
            generate_secondary_images_from_folders,
            generate_exposure_images_from_folders,
            generate_position_images_from_folders,
            MembraneSettings,
            SecondaryDoseSettings,
            ExposureSettings,
            PositionSettings,
        )

        device_subdirectory = temp_directory / device.get_fully_qualified_name()

        # Create membrane images from the sliced devices
        for name, (_, settings) in device.regional_settings.items():
            masks_subdirectory = (
                temp_directory / "masks" / device.get_fully_qualified_name() / name
            )
            device_index = sliced_devices.index(device)
            if isinstance(settings, MembraneSettings):
                settings.exposure_settings.fill_with_defaults(
                    device.default_exposure_settings,
                    exceptions=["exposure_time"],
                )
                generate_membrane_images_from_folders(
                    image_dir=device_subdirectory,
                    mask_dir=masks_subdirectory,
                    membrane_settings=settings,
                    slice_metadata=sliced_devices_info[device_index],
                )

        # Create secondary images from the sliced devices
        for name, (_, settings) in device.regional_settings.items():
            masks_subdirectory = (
                temp_directory / "masks" / device.get_fully_qualified_name() / name
            )
            device_index = sliced_devices.index(device)
            if isinstance(settings, SecondaryDoseSettings):
                settings.edge_exposure_settings.fill_with_defaults(
                    device.default_exposure_settings,
                    exceptions=["exposure_time"],
                )
                settings.roof_exposure_settings.fill_with_defaults(
                    device.default_exposure_settings,
                    exceptions=["exposure_time"],
                )
                generate_secondary_images_from_folders(
                    image_dir=device_subdirectory,
                    mask_dir=masks_subdirectory,
                    settings=settings,
                    slice_metadata=sliced_devices_info[device_index],
                )

        # Create exposure images from the sliced devices
        for name, (_, settings) in device.regional_settings.items():
            masks_subdirectory = (
                temp_directory / "masks" / device.get_fully_qualified_name() / name
            )
            device_index = sliced_devices.index(device)
            if isinstance(settings, ExposureSettings):
                settings.fill_with_defaults(
                    device.default_exposure_settings,
                )
                generate_exposure_images_from_folders(
                    image_dir=device_subdirectory,
                    mask_dir=masks_subdirectory,
                    settings=settings,
                    slice_metadata=sliced_devices_info[device_index],
                )

        # Create position images from the sliced devices
        for name, (_, settings) in device.regional_settings.items():
            masks_subdirectory = (
                temp_directory / "masks" / device.get_fully_qualified_name() / name
            )
            device_index = sliced_devices.index(device)
            if isinstance(settings, PositionSettings):
                settings.fill_with_defaults(
                    device.default_position_settings,
                )
                generate_position_images_from_folders(
                    image_dir=device_subdirectory,
                    mask_dir=masks_subdirectory,
                    settings=settings,
                    slice_metadata=sliced_devices_info[device_index],
                )

    def _embed_component_slices(
        self,
        sliced_devices,
        sliced_devices_info,
        temp_directory,
        slices_folder,
    ):
        from .. import Device

        embedded_devices = []
        for device, info in zip(reversed(sliced_devices), reversed(sliced_devices_info)):
            # If its a device, just copy the images from sliced_devices_info into the folder
            if isinstance(device, Device):
                embedded_devices.append((device, info))
                if self.minimize_file:
                    self.unique_image_store = UniqueImageStore(slices_folder)
                    for image in info["slices"]:
                        image_path = (
                            temp_directory
                            / device.get_fully_qualified_name()
                            / image["image_name"]
                        )
                        image_path = self.unique_image_store.add_image(
                            load_image_from_file(image_path), image_path
                        )
                        image_path = image_path
                        image["image_name"] = f"{image_path.name}"
                else:
                    # Create a subdirectory for the device
                    # device_subdirectory = (
                    #     slices_folder / device.get_fully_qualified_name()
                    # )

                    # Copy the all images from temp_directory/fqn to slices/fqn
                    shutil.copytree(
                        temp_directory / device.get_fully_qualified_name(),
                        slices_folder,
                        dirs_exist_ok=True,
                    )

            # If its a component, we need to insert its slices into its parent components (relabeling if necessary)
            else:
                positions = info["positions"]
                # get list of unique devices (not hashable) from positions
                unique_devices = []
                for pos in positions:
                    if pos[0] is not None and pos[0] not in unique_devices:
                        unique_devices.append(pos[0])
                # copy slices from component into image the size of the device (translated correctly)
                for parent_device in unique_devices:
                    resolution = (
                        int(parent_device.get_size()[0]),
                        int(parent_device.get_size()[1]),
                    )
                    slice_list = []
                    slice_list.extend(info["slices"])
                    if "membrane_slices" in info:
                        slice_list.extend(info["membrane_slices"])
                    if "secondary_slices" in info:
                        slice_list.extend(info["secondary_slices"])
                    if "exposure_slices" in info:
                        slice_list.extend(info["exposure_slices"])
                    for slice in slice_list:
                        # Create a new image with the same size as the device
                        slice_image = np.zeros(
                            (resolution[1], resolution[0]), dtype=np.uint8
                        )
                        # Load the slice image
                        slice_path = (
                            temp_directory
                            / device.get_fully_qualified_name()
                            / slice["image_name"]
                        )
                        if slice_path.exists():
                            slice_img = cv2.imread(str(slice_path), cv2.IMREAD_UNCHANGED)
                        if slice_img is None:
                            print(f"Warning: Slice image {slice_path} not found.")
                            continue
                        # Replace the corresponding region in the slice image
                        for pos in positions:
                            if pos[0] == parent_device:
                                x = int(pos[1])
                                y = int(pos[2])
                                z = pos[3]

                                # Correct for numpy image origin
                                y = resolution[1] - y
                                # Assuming slice_img is a 2D image
                                slice_image[
                                    y - slice_img.shape[0] : y, x : x + slice_img.shape[1]
                                ] = slice_img

                        # check if image path exists (if so, generate a new name)
                        slice_image_path = (
                            temp_directory
                            / parent_device.get_fully_qualified_name()
                            / slice["image_name"]
                        )
                        if slice_image_path.exists():
                            # Generate a new name for the slice image
                            name = (
                                "slice"
                                + slice["image_name"].split(".")[0].split("slice")[1]
                            )
                            stem = name.split("_")[0]
                            if "_" in name and len(name.split("_")) > 2:
                                postfix = name.split("_")[1]
                            else:
                                postfix = ""
                            slice_image_path = get_unique_path(
                                temp_directory / parent_device.get_fully_qualified_name(),
                                stem,
                                postfix=postfix,
                                suffix=".png",
                            )
                        # Save the slice image
                        cv2.imwrite(str(slice_image_path), slice_image)
                        # Add image metadata to the parent info
                        parent_index = sliced_devices.index(parent_device)
                        sliced_devices_info[parent_index]["slices"].append(
                            {
                                "image_name": slice_image_path.name,
                                "layer_position": round(
                                    slice["layer_position"] + z * 1000, 1
                                ),
                                "exposure_settings": slice["exposure_settings"],
                                "position_settings": slice["position_settings"],
                            }
                        )

        return embedded_devices

    def _iterate_slices_by_layer(self, embedded_devices):
        # First, collect all unique layer positions
        layer_positions = set()
        for _, info in embedded_devices:
            for slice_info in info.get("slices", []):
                layer_positions.add(slice_info["layer_position"])
            info["slices"].sort(
                key=lambda x: (
                    x["layer_position"],
                    x["exposure_settings"].exposure_time,
                )
            )

        # Sort layer positions
        sorted_layers = sorted(layer_positions)

        # Iterate by each layer position
        for layer in sorted_layers:
            current_layer_slices = []
            for device_obj, info in embedded_devices:
                for slice_info in info.get("slices", []):
                    if slice_info["layer_position"] == layer:
                        current_layer_slices.append((device_obj, slice_info))
            yield layer, current_layer_slices

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

    def make_print_file(self) -> bool:
        """
        Generate a print file based on the provided device and settings.
        This function will create a temporary directory, slice the device's components,
        generate secondary and membrane images, create a JSON file with the print data,
        and create a print job zip or directory.
        """
        try:

            # # Check if output already exists
            # if self.check_output_exists(self.filename):
            #     print(
            #         f"Output already exists at {self.filename}. Please select a different path."
            #     )
            #     return False

            # Create a temporary directory for processing
            temp_directory = self.generate_temp_directory()

            # Copy code to the temporary directory
            print("Copying script and dependencies...")
            main_file_path = self._copy_script_and_dependencies(temp_directory)

            # Slice the device components
            sliced_devices = []
            sliced_devices_info = []
            print("Slicing...")
            slice_component(
                self.device, temp_directory, sliced_devices, sliced_devices_info
            )

            print("Make secondary images...")
            from .. import Device

            for device, info in zip(sliced_devices, sliced_devices_info):
                # Fill default settings for sliced devices
                self._fill_device_settings(device, info)

                # Fill device specific settings
                if isinstance(device, Device):
                    device.default_position_settings.layer_thickness = (
                        device._layer_size * 1000
                    )
                    le = self.settings.printer.get_light_engine(
                        device._px_size,
                        device._size[0:2],
                        device.default_exposure_settings.wavelength,
                    )
                    device.default_exposure_settings.light_engine = le.name
                    x_offset = device.get_position()[0] - le.origin[0]
                    y_offset = device.get_position()[1] - le.origin[1]
                    if not self.settings.printer.xy_stage_available and (
                        x_offset != 0 or y_offset != 0
                    ):
                        raise ValueError(
                            f"Device {device.get_fully_qualified_name()} is not compatible with the printer. (Printer missing XY stage support)"
                            "Please adjust the device position or use a different printer."
                        )
                    device.default_exposure_settings.image_x_offset = x_offset
                    device.default_exposure_settings.image_y_offset = y_offset

                # Generate secondary, membrane, and regional images
                self._make_secondary_images(
                    device, temp_directory, sliced_devices, sliced_devices_info
                )

            # Make slices directory
            if self.minimize_file:
                slices_folder = temp_directory / f"minimized_slices"
            else:
                slices_folder = temp_directory / "slices"
            os.mkdir(slices_folder)

            print("Flatten component images...")
            # Embed component slices into devices
            self.unique_image_store = {}
            embedded_devices = self._embed_component_slices(
                sliced_devices, sliced_devices_info, temp_directory, slices_folder
            )

            # Make json file
            print("Compile print settings...")
            print_settings_filename = temp_directory / "print_settings.json"
            print_settings = {
                "Header": {
                    "Schema version": self.settings.settings["Schema version"],
                    "Image directory": (
                        "minimized_slices" if self.minimize_file else "slices"
                    ),
                    "Print under vacuum": self.settings.settings["Print under vacuum"],
                },
                "Design": {
                    "User": self.settings.settings["User"],
                    "Purpose": self.settings.settings["Purpose"],
                    "Description": self.settings.settings["Description"],
                    "Resin": self.settings.settings["Resin"],
                    "3D printer": self.settings.settings["3D printer"],
                    "Design file": str(main_file_path),
                    "Slicer": self.settings.settings["Slicer"],
                    "Date": self.settings.settings["Date"],
                },
                "Variables": {},
                "Default layer settings": self.settings.settings[
                    "Default layer settings"
                ],
                "Named position settings": {},
                "Named image settings": {},
            }
            print_settings["Default layer settings"]["Position settings"][
                "Layer thickness (um)"
            ] = (embedded_devices[0][0]._layer_size * 1000)
            fqn = embedded_devices[0][0].get_fully_qualified_name()
            print_settings["Default layer settings"]["Image settings"][
                "Image file"
            ] = f"{fqn}/{fqn}-slice0000.png"
            print_settings["Default layer settings"]["Image settings"]["Light engine"] = (
                embedded_devices[0][0].default_exposure_settings.light_engine
            )
            print_settings["Default layer settings"]["Image settings"][
                "Image x offset (um)"
            ] = embedded_devices[0][0].default_exposure_settings.image_x_offset
            print_settings["Default layer settings"]["Image settings"][
                "Image y offset (um)"
            ] = embedded_devices[0][0].default_exposure_settings.image_y_offset

            # Create copies of named image settings. These include the defaults and are fully expanded for comparision
            expanded_named_position_settings = print_settings[
                "Named position settings"
            ].copy()
            expanded_named_position_settings["default"] = print_settings[
                "Default layer settings"
            ]["Position settings"]
            expanded_named_image_settings = print_settings["Named image settings"].copy()
            expanded_named_image_settings["default"] = print_settings[
                "Default layer settings"
            ]["Image settings"]

            # Loop z positions
            layers = []
            last_layer = 0.0
            for layer, slices in self._iterate_slices_by_layer(embedded_devices):
                layer_thickness = layer - last_layer
                position_settings = None
                layer_settings = {}
                image_settings_list = []
                for device_obj, slice_info in slices:
                    # Update position settings from slice
                    new_position_settings = slice_info["position_settings"].to_dict()
                    if position_settings is None:
                        position_settings = new_position_settings
                        position_settings["Layer thickness (um)"] = layer_thickness
                    else:
                        if (
                            "Enable force squeeze" in new_position_settings
                            and new_position_settings["Enable force squeeze"] == True
                        ):
                            position_settings["Enable force squeeze"] = True
                        for key in [
                            "Distance up (mm)",
                            "Initial wait (ms)",
                            "Up wait (ms)",
                            "Final wait (ms)",
                            "Squeeze count",
                            "Squeeze force (N)",
                            "Squeeze wait (ms)",
                        ]:
                            if new_position_settings.get(
                                key, 1e10
                            ) > position_settings.get(key, 0):
                                position_settings[key] = new_position_settings[key]
                        for key in [
                            "BP up speed (mm/sec)",
                            "BP up acceleration (mm/sec^2)",
                            "BP down speed (mm/sec)",
                            "BP down acceleration (mm/sec^2)",
                        ]:
                            if new_position_settings.get(key, 0) < position_settings.get(
                                key, 1e10
                            ):
                                position_settings[key] = new_position_settings[key]

                    # Find closest named image setting
                    match_key, match_dict = self._match_or_find_closest_named_setting(
                        slice_info["exposure_settings"].to_dict(),
                        expanded_named_image_settings,
                        ["Image file"],
                    )

                    # If no match add new named image settings
                    if len(match_dict) != 0:
                        settings_name = re.sub(
                            r"-slice\d+", "", slice_info["image_name"]
                        ).split(".png")[0]

                        # set named image settings
                        image_settings = match_dict.copy()
                        if match_key != "default":
                            image_settings["Using named image settings"] = match_key
                        print_settings["Named image settings"][
                            settings_name
                        ] = image_settings
                        match_key = settings_name

                        # set expanded named image settings
                        expanded_named_image_settings[match_key] = slice_info[
                            "exposure_settings"
                        ].to_dict()

                    # Set image settings
                    image_settings = {
                        "Image file": slice_info["image_name"],
                    }
                    if match_key != "default":
                        image_settings["Using named image settings"] = match_key

                    image_settings_list.append(image_settings)

                # Find closest named position setting
                match_key, match_dict = self._match_or_find_closest_named_setting(
                    position_settings,
                    expanded_named_position_settings,
                )

                # If no match add new named position settings
                if len(match_dict) != 0:
                    settings_name = f"z_{layer}"

                    # set named position settings
                    _position_settings = match_dict.copy()
                    if match_key != "default":
                        _position_settings["Using named position settings"] = match_key
                    print_settings["Named position settings"][
                        settings_name
                    ] = _position_settings
                    match_key = settings_name

                    # set expanded named image settings
                    expanded_named_position_settings[match_key] = position_settings

                # Set position settings
                position_settings = {}
                if match_key != "default":
                    position_settings["Using named position settings"] = match_key
                    layer_settings["Position settings"] = position_settings

                layer_settings["Image settings list"] = image_settings_list
                layers.append(layer_settings)
                last_layer = layer

            if not self.minimize_file:
                print_settings["Layers"] = layers
            else:
                # Minimize json
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

            # Save json
            with open(print_settings_filename, "w", newline="\r\n") as fileOut:
                json.dump(pretty_json(print_settings), fileOut, indent=2)

            # Delete device and mask folders
            print("Cleaning up temporary directories...")
            for device in sliced_devices:
                device_subdirectory = temp_directory / device.get_fully_qualified_name()
                if device_subdirectory.exists():
                    shutil.rmtree(device_subdirectory)
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
            import traceback

            print(f"An error occurred during slicing: {e}. Removing temorary directory.")
            print(traceback.format_exc())
            # Clean up the temporary directory
            shutil.rmtree(temp_directory)
