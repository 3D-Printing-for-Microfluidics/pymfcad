import re
import os
import cv2
import sys
import json
import shutil
import numpy as np
from PIL import Image
import importlib.util
from pathlib import Path
from typing import Union
from types import ModuleType
from datetime import datetime

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

    def _check_output_exists(self, output_path: str) -> bool:
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

    def _generate_temp_directory(self) -> Path:
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

    def _fill_device_default_settings(self, device, info):
        # Fill device default settings
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

        # Fill device specific settings
        from .. import Device

        if isinstance(device, Device):
            device.default_position_settings.layer_thickness = device._layer_size * 1000
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
        else:
            device.default_exposure_settings.light_engine = (
                device._parent.default_exposure_settings.light_engine
            )
            device.default_exposure_settings.image_x_offset = (
                device._parent.default_exposure_settings.image_x_offset
            )
            device.default_exposure_settings.image_y_offset = (
                device._parent.default_exposure_settings.image_x_offset
            )

        # Fill slice info settings
        for i, slice in enumerate(info["slices"]):
            slice["position_settings"] = device.default_position_settings
            slice["exposure_settings"] = device.default_exposure_settings.copy()
            slice["exposure_settings"].image_x_offset = (
                device.default_exposure_settings.image_x_offset
            )
            slice["exposure_settings"].image_y_offset = (
                device.default_exposure_settings.image_y_offset
            )
            slice["exposure_settings"].light_engine = (
                device.default_exposure_settings.light_engine
            )

            # Generate burn-in exposure settings
            if i < len(device.burnin_settings):
                slice["exposure_settings"].exposure_time = device.burnin_settings[i]
                slice["exposure_settings"].burnin = True

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

    def _embed_image(self, pos, resolution, image_data, fqn):
        x = round(pos[0])
        y = round(pos[1])

        slice_img = image_data

        # Create a new empty image sized to the device
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
                f"⚠️Warning: slice image for {fqn} at x={x},y={y} is completely outside device bounds"
            )
            # still save an empty image or skip; here we'll skip

        return slice_image

    def _embed_component_slices(
        self,
        sliced_devices,
        sliced_devices_info,
        temp_directory,
        slices_folder,
    ):
        from .. import Device

        embedded_devices = []
        # print(sliced_devices, sliced_devices_info)
        for device, info in zip(reversed(sliced_devices), reversed(sliced_devices_info)):
            print(f"\tEmbedding {device.get_fully_qualified_name()}...")
            # If its a device, just copy the images from sliced_devices_info into the folder
            if isinstance(device, Device):
                embedded_devices.append((device, info))

                slice_list = []
                slice_list.extend(info.get("slices", []))
                # print(
                #     f"\t\t base slices for device ({parent_device.get_fully_qualified_name()}): {len(info.get('slices', []))}"
                # )
                slice_list.extend(info.get("membrane_slices", []))
                # print(
                #     f"\t\t membrane slices for device ({parent_device.get_fully_qualified_name()}): {len(info.get('membrane_slices', []))}"
                # )
                slice_list.extend(info.get("secondary_slices", []))
                # print(
                #     f"\t\t secondary slices for device ({parent_device.get_fully_qualified_name()}): {len(info.get('secondary_slices', []))}"
                # )
                slice_list.extend(info.get("exposure_slices", []))
                # print(
                #     f"\t\t exposure slices for device ({parent_device.get_fully_qualified_name()}): {len(info.get('exposure_slices', []))}"
                # )
                info["slices"] = slice_list

                # if self.minimize_file:
                #     for image in info["slices"]:
                #         image_path = (
                #             temp_directory
                #             / device.get_fully_qualified_name()
                #             / image["image_name"]
                #         )
                #         image["image_name"] = f"{image_path.name}"
                # else:
                #     # os.mkdir(slices_folder, exist_ok=True)
                #     # Copy the all images from temp_directory/fqn to slices/fqn
                #     shutil.copytree(
                #         temp_directory / device.get_fully_qualified_name(),
                #         slices_folder,
                #         dirs_exist_ok=True,
                #     )

            # If its a component, we need to insert its slices into its parent components (relabeling if necessary)
            else:
                positions = info["positions"]
                # get list of unique devices (not hashable) from positions
                unique_devices = []
                for pos in positions:
                    if pos[0] is not None and pos[0] not in unique_devices:
                        unique_devices.append(pos[0])
                        # print(f"APPEND UNIQUE {pos[0]}")
                # copy slices from component into image the size of the device (translated correctly)
                for parent_device in unique_devices:
                    resolution = (
                        int(parent_device.get_size()[0]),
                        int(parent_device.get_size()[1]),
                    )

                    # aggregate slices from info once per parent_device
                    slice_list = []
                    slice_list.extend(info.get("slices", []))
                    # print(
                    #     f"\t\t base slices for device ({parent_device.get_fully_qualified_name()}): {len(info.get('slices', []))}"
                    # )
                    slice_list.extend(info.get("membrane_slices", []))
                    # print(
                    #     f"\t\t membrane slices for device ({parent_device.get_fully_qualified_name()}): {len(info.get('membrane_slices', []))}"
                    # )
                    slice_list.extend(info.get("secondary_slices", []))
                    # print(
                    #     f"\t\t secondary slices for device ({parent_device.get_fully_qualified_name()}): {len(info.get('secondary_slices', []))}"
                    # )
                    slice_list.extend(info.get("exposure_slices", []))
                    # print(
                    #     f"\t\t exposure slices for device ({parent_device.get_fully_qualified_name()}): {len(info.get('exposure_slices', []))}"
                    # )

                    # build list of positions belonging to this parent_device
                    positions_for_parent = [
                        pos for pos in positions if pos[0] == parent_device
                    ]

                    # # z indexes for this device (unique)
                    # z_indexes = []
                    # for pos in positions_for_parent:
                    #     if pos[3] not in z_indexes:
                    #         z_indexes.append(pos[3])

                    for slice_index, slice in enumerate(slice_list):
                        # Load the base slice image once (if it exists)
                        # print(
                        #     temp_directory,
                        #     device,
                        #     device.get_fully_qualified_name(),
                        #     slice["image_name"],
                        # )
                        slice_path = (
                            temp_directory
                            / device.get_fully_qualified_name()
                            / slice["image_name"]
                        )
                        slice_img = slice["image_data"]
                        # slice_img = None
                        # if slice_path.exists():
                        #     slice_img = cv2.imread(str(slice_path), cv2.IMREAD_UNCHANGED)

                        # if slice_img is None:
                        #     print(f"Warning: Slice image {slice_path} not found.")
                        #     continue

                        # For each position for this parent_device we create a separate slice image
                        for pos in positions_for_parent:
                            # if isinstance(parent_device, Device):
                            x = pos[1]
                            y = pos[2]
                            z = round(pos[3], 4)
                            slice_image = self._embed_image(
                                (x, y),
                                resolution,
                                slice_img,
                                parent_device.get_fully_qualified_name(),
                            )

                            # Build a unique filename including z (and keep original name suffix)
                            # Example: original 'slice_01.png' -> 'slice_01_z10.png' (or use get_unique_path)
                            base_name = slice["image_name"]
                            name_no_ext = base_name.rsplit(".", 1)[0]
                            ext = (
                                "." + base_name.rsplit(".", 1)[1]
                                if "." in base_name
                                else ".png"
                            )
                            new_name = f"{name_no_ext}_z{z}{ext}"

                            # ensure directory exists
                            out_dir = (
                                temp_directory / parent_device.get_fully_qualified_name()
                            )
                            out_dir.mkdir(parents=True, exist_ok=True)

                            slice_image_path = out_dir / new_name
                            if slice_image_path.exists():
                                # get_unique_path should generate a unique name (preserves suffix)
                                slice_image_path = get_unique_path(
                                    out_dir, name_no_ext + f"_z{z}", suffix=ext
                                )

                            parent_index = sliced_devices.index(parent_device)

                            # Save the slice image
                            # if isinstance(parent_device, Device):
                            #     cv2.imwrite(str(slice_image_path), slice_image)

                            print(
                                f"\r\t\tEmbedding {slice['image_name'] if isinstance(parent_device, Device) else slice_image_path.name} ({slice_index+1}/{len(slice_list)}) at z={z}...",
                                end="",
                                flush=True,
                            )
                            sliced_devices_info[parent_index]["slices"].append(
                                {
                                    "image_name": (
                                        slice["image_name"]
                                        if isinstance(parent_device, Device)
                                        else slice_image_path.name
                                    ),
                                    "parent": (
                                        parent_device
                                        if isinstance(parent_device, Device)
                                        else None
                                    ),
                                    "image_data": (
                                        slice_img
                                        if isinstance(parent_device, Device)
                                        else np.array(slice_image)
                                    ),
                                    "device": (
                                        device
                                        if isinstance(parent_device, Device)
                                        else None
                                    ),
                                    "position": (
                                        round(pos[1]),
                                        (
                                            round(
                                                pos[2],
                                            )
                                            if isinstance(parent_device, Device)
                                            else None
                                        ),
                                    ),
                                    "layer_position": (
                                        round(slice["layer_position"] + z * 1000, 1)
                                    ),
                                    "exposure_settings": slice.get("exposure_settings"),
                                    "position_settings": slice.get("position_settings"),
                                }
                            )
                    print()

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
                        current_layer_slices.append(slice_info)
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
                del s1["Layer exposure time (ms)"]
                del s1["Wait before exposure (ms)"]
                del s1["Wait after exposure (ms)"]

                s2 = group[0]["exposure_settings"].to_dict()
                del s2["Image file"]
                del s2["Layer exposure time (ms)"]
                del s2["Wait before exposure (ms)"]
                del s2["Wait after exposure (ms)"]

                if s1 == s2:
                    group.append(slice_info)
                    match_found = True
                    break

            if not match_found:
                # print("Adding new group")
                # print(slice_info["exposure_settings"].to_dict())
                # for group in grouped_slices:
                #     print(group[0]["exposure_settings"].to_dict())
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

    def _load_binary_images(self, image_paths):
        """Load images and convert to boolean masks (True = pixel lit)."""
        imgs = []
        for p in image_paths:
            arr = np.array(Image.open(p))
            imgs.append(arr == 255)
        return np.array(imgs)  # shape: (N, H, W)

    def _compress_exposures(self, images, exposure_times, temp_directory):
        """
        Combine binary images into minimal exposure layers using the exposure-sum method.
        Optimized to avoid repeated min-searches and masking.
        """

        def image_from_dict(slice_info):
            resolution = (
                int(slice_info["parent"].get_size()[0]),
                int(slice_info["parent"].get_size()[1]),
            )
            return self._embed_image(
                slice_info["position"],
                resolution,
                slice_info["image_data"],
                slice_info["device"].get_fully_qualified_name(),
            )

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

        exposure_sum = np.zeros((H, W), dtype=float)
        for image, exp in zip(images, exposure_times):
            if type(image) is dict:
                img = image_from_dict(image)
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

    def make_print_file(self) -> bool:
        """
        Generate a print file based on the provided device and settings.
        This function will create a temporary directory, slice the device's components,
        generate secondary and membrane images, create a JSON file with the print data,
        and create a print job zip or directory.
        """
        try:

            # # Check if output already exists
            # if self._check_output_exists(self.filename):
            #     print(
            #         f"Output already exists at {self.filename}. Please select a different path."
            #     )
            #     return False

            # Create a temporary directory for processing
            temp_directory = self._generate_temp_directory()

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
            for device, info in zip(sliced_devices, sliced_devices_info):
                print(f"\t{device.get_fully_qualified_name()}")

                # Fill default settings for sliced devices
                self._fill_device_default_settings(device, info)

                # Generate secondary, membrane, and regional images
                self._make_secondary_images(
                    device, temp_directory, sliced_devices, sliced_devices_info
                )

            # Make slices directory
            if self.minimize_file:
                slices_folder = temp_directory / f"minimized_slices"
                self.unique_image_store = {}
                self.unique_image_store = UniqueImageStore(slices_folder)
            else:
                slices_folder = temp_directory / "slices"
                os.mkdir(slices_folder)

            print("Embedding component images...")
            # Embed component slices into devices
            embedded_devices = self._embed_component_slices(
                sliced_devices, sliced_devices_info, temp_directory, slices_folder
            )

            # print le
            for device, info in embedded_devices:
                print(
                    f"\tDevice {device.get_fully_qualified_name()} uses light engine: {device.default_exposure_settings.light_engine}"
                )

            # embedded_devices = []
            # for device, info in zip(sliced_devices, sliced_devices_info):
            #     if isinstance(device, Device):
            #         embedded_devices.append((device, info))

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

            # Update default layer settings based on the first embedded device
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
                print(
                    f"\r\tProcessing layer at {layer:.1f} um... ",
                    end="",
                    flush=True,
                )

                layer_thickness = layer - last_layer
                position_settings = None
                layer_settings = {}
                image_settings_list = []

                # Group slices by settings
                grouped_slices = self._group_images_by_settings(slices)
                for group in grouped_slices:
                    group_exposure_settings = None

                    group_exposures = [
                        slice_info["exposure_settings"].exposure_time
                        for slice_info in group
                    ]
                    group_images = []
                    for slice_info in group:
                        if slice_info.get("parent") is not None:
                            group_images.append(
                                {
                                    "device": slice_info["device"],
                                    "parent": slice_info["parent"],
                                    "image_data": slice_info["image_data"],
                                    "image_name": slice_info["image_name"],
                                    "position": slice_info["position"],
                                }
                            )
                        else:
                            group_images.append(slice_info["image_data"])

                    # Compress exposures
                    if len(group_images) > 1:
                        output_imgs, output_times = self._compress_exposures(
                            group_images, group_exposures, temp_directory
                        )
                    else:
                        output_imgs = group_images
                        output_times = group_exposures
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
                        new_image_settings = slice_info["exposure_settings"].to_dict()
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

                    for file, exp in zip(output_img_files, output_times):
                        # Find closest named image setting
                        exposure_settings = group_exposure_settings.copy()
                        exposure_settings["Layer exposure time (ms)"] = exp
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
                            image_settings = match_dict.copy()
                            if match_key != "default":
                                image_settings["Using named image settings"] = match_key
                            print_settings["Named image settings"][
                                settings_name
                            ] = image_settings
                            match_key = settings_name

                            # set expanded named image settings
                            expanded_named_image_settings[match_key] = exposure_settings

                        # Set image settings
                        image_settings = {
                            "Image file": file,
                        }
                        if match_key != "default":
                            image_settings["Using named image settings"] = match_key

                        image_settings_list.append(image_settings)

                    # Update position settings from slice
                    for g, slice_info in enumerate(group):
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
                                if new_position_settings.get(
                                    key, 0
                                ) < position_settings.get(key, 1e10):
                                    position_settings[key] = new_position_settings[key]

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

            print(
                f"❌ An error occurred during slicing: {e}. Removing temorary directory."
            )
            print(traceback.format_exc())

        finally:
            # Clean up the temporary directory
            # try:
            #     shutil.rmtree(temp_directory)
            # except Exception:
            #     pass
            pass
