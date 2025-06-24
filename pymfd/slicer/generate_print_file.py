import os
import sys
import json
import re
import glob
import shutil
from pathlib import Path
from contextlib import nullcontext
from zipfile import ZipFile, ZIP_DEFLATED
from PIL import Image

from .json_prettier import pretty_json
from .uniqueimagestore import UniqueImageStore, load_image_from_file


def lookup_le(le, slicer_settings):
    light_engine = slicer_settings["light_engines"][le]
    return light_engine["json_name"]


def validate_slice(imageFile, size=(2560, 1600)):
    try:
        with Image.open(imageFile) as pil_image:
            if (
                pil_image.format == "PNG"
                and pil_image.mode == "L"
                and pil_image.size == size
            ):
                return True  # image is correct format and mode
    except (OSError, FileNotFoundError):
        return False
    return False  # image is bad


def create_design_json(design_settings):
    return {
        "User": design_settings["user"],
        "Purpose": design_settings["purpose"],
        "Description": design_settings["description"],
        "Resin": design_settings["resin"],
        "3D printer": design_settings["printer"],
        "Slicer": design_settings["slicer"],
        "Date": design_settings["date"],
    }


def create_defaults_json(stl, version, slicer_settings, temp_directory):
    _uuid = stl["uuid"]
    settings = stl["settings"]
    def_layer_settings = {
        "Number of duplications": 1,
        "Position settings": {
            "Layer thickness (um)": float(settings["layer_thickness_um"]),
            "Distance up (mm)": float(settings["up_dist"]),
            "Initial wait (ms)": int(settings["initial_wait"]),
            "BP up speed (mm/sec)": float(settings["up_speed"]),
            "BP up acceleration (mm/sec^2)": float(settings["up_accel"]),
            "Up wait (ms)": int(settings["up_wait"]),
            "BP down speed (mm/sec)": float(settings["down_speed"]),
            "BP down acceleration (mm/sec^2)": float(settings["down_accel"]),
            "Final wait (ms)": int(settings["final_wait"]),
        },
        "Image settings": {
            "Image file": f"{_uuid}/out0001.png",
            "Layer exposure time (ms)": float(settings["exp_time_ms"]),
            "Light engine power setting": int(settings["le_power"]),
            "Relative focus position (um)": float(settings["defocus"]),
            "Wait before exposure (ms)": int(settings["before_exp_wait"]),
            "Wait after exposure (ms)": int(settings["after_exp_wait"]),
        },
    }
    if version >= 3:
        def_layer_settings["Image settings"]["Image x offset (um)"] = float(
            settings["x_offset"]
        )
        def_layer_settings["Image settings"]["Image y offset (um)"] = float(
            settings["y_offset"]
        )
    if version >= 4:
        def_layer_settings["Image settings"]["Light engine"] = lookup_le(
            settings["le"], slicer_settings
        )

    if settings["en_secondary"] or settings["en_roof"]:
        if not (temp_directory / _uuid / "slices/out0001.png").exists():
            def_layer_settings["Image settings"][
                "Image file"
            ] = f"{_uuid}/out0001_primary.png"
    return def_layer_settings


def create_named_position_settings(stls, default_position_settings):
    # Named position settings
    named_position_settings = {}
    for i in range(len(stls)):
        _uuid = stls[i]["uuid"]
        settings = stls[i]["settings"]
        # create default position setting for stl
        if i != 0:
            position_settings = {
                "Layer thickness (um)": float(settings["layer_thickness_um"]),
                "Distance up (mm)": float(settings["up_dist"]),
                "Initial wait (ms)": int(settings["initial_wait"]),
                "BP up speed (mm/sec)": float(settings["up_speed"]),
                "BP up acceleration (mm/sec^2)": float(settings["up_accel"]),
                "Up wait (ms)": int(settings["up_wait"]),
                "BP down speed (mm/sec)": float(settings["down_speed"]),
                "BP down acceleration (mm/sec^2)": float(settings["down_accel"]),
                "Final wait (ms)": int(settings["final_wait"]),
            }
            named_position_settings[f"{_uuid}_default"] = position_settings

    # remove unchanged settings
    for named_settings_key in list(named_position_settings):
        named_settings = named_position_settings[named_settings_key]
        for key in list(named_settings):
            value = named_settings[key]
            if "Using named position settings" in named_settings:
                parent_settings = named_settings["Using named position settings"]
                if value == named_position_settings[parent_settings].get(key, None):
                    del named_settings[key]
            try:
                if value == default_position_settings[key]:
                    del named_settings[key]
            except KeyError:
                pass
    return named_position_settings


def create_named_image_settings(stls, default_image_settings, version, slicer_settings):
    # Named image settings
    named_image_settings = {}
    for i in range(len(stls)):
        _uuid = stls[i]["uuid"]
        settings = stls[i]["settings"]
        # create default image setting for stl
        if i != 0:
            image_settings = {
                "Image file": f"{_uuid}/out0001.png",
                "Layer exposure time (ms)": float(settings["exp_time_ms"]),
                "Light engine power setting": int(settings["le_power"]),
                "Relative focus position (um)": float(settings["defocus"]),
                "Wait before exposure (ms)": int(settings["before_exp_wait"]),
                "Wait after exposure (ms)": int(settings["after_exp_wait"]),
            }
            if version >= 3:
                image_settings["Image x offset (um)"] = float(settings["x_offset"])
                image_settings["Image y offset (um)"] = float(settings["y_offset"])
            if version >= 4:
                image_settings["Light engine"] = lookup_le(
                    settings["le"], slicer_settings
                )
            named_image_settings[f"{_uuid}_default"] = image_settings

        # # create burn-in image setting for stl
        # for j, exp in enumerate(settings["burn_in_ms"].split(",")):
        #     named_image_settings[f"{_uuid}_burn_in_{j}"] = {
        #         "Using named image settings": f"{_uuid}_default",
        #         "Layer exposure time (ms)": int(exp),
        #     }

        # create membrane image setting for stl
        if settings["en_membranes"]:
            membrane_image_settings = {
                "Layer exposure time (ms)": float(settings["membrane_exp_ms"]),
                "Relative focus position (um)": float(settings["membrane_defocus"]),
            }
            if i != 0:
                membrane_image_settings["Using named image settings"] = f"{_uuid}_default"
            named_image_settings[f"{_uuid}_membrane"] = membrane_image_settings

        # create secondary image setting for stl
        if settings["en_secondary"] or settings["en_roof"]:

            # calculate exposure times
            bulk_dose = float(settings[f"exp_time_ms"])
            edge_dose = float(settings[f"secondary_exp_time_ms"])
            roof_dose = float(settings[f"roof_exp_time_ms"])
            primary_dose = 0
            secondary_dose = 0
            tertiary_dose = 0

            if (
                (edge_dose == roof_dose)
                or not settings["en_roof"]
                or not settings["en_secondary"]
            ):
                if not settings["en_secondary"]:
                    doses = [bulk_dose, roof_dose]
                else:
                    doses = [bulk_dose, edge_dose]

                if doses[0] == doses[1]:
                    continue

                doses.sort()

                primary_dose = doses[0]
                secondary_dose = doses[1] - primary_dose
                # if edge_dose < bulk_dose:
                #     primary_dose = edge_dose
                #     secondary_dose = bulk_dose - edge_dose
                # else:
                #     primary_dose = bulk_dose
                #     secondary_dose = edge_dose - bulk_dose
            else:
                doses = [bulk_dose, edge_dose, roof_dose]
                doses.sort()

                primary_dose = doses[0]
                secondary_dose = doses[1] - primary_dose
                tertiary_dose = doses[2] - secondary_dose

                tertiary_image_settings = {
                    "Layer exposure time (ms)": tertiary_dose,
                }

                if i != 0:
                    tertiary_image_settings["Using named image settings"] = (
                        f"{_uuid}_default"
                    )
                named_image_settings[f"{_uuid}_tertiary"] = tertiary_image_settings

            primary_image_settings = {
                "Layer exposure time (ms)": primary_dose,
            }
            secondary_image_settings = {
                "Layer exposure time (ms)": secondary_dose,
            }
            if i != 0:
                primary_image_settings["Using named image settings"] = f"{_uuid}_default"
                secondary_image_settings["Using named image settings"] = (
                    f"{_uuid}_default"
                )
            named_image_settings[f"{_uuid}_primary"] = primary_image_settings
            named_image_settings[f"{_uuid}_secondary"] = secondary_image_settings

    # remove unchanged settings
    for named_settings_key in list(named_image_settings):
        named_settings = named_image_settings[named_settings_key]
        for key in list(named_settings):
            value = named_settings[key]
            if "Using named image settings" in named_settings:
                parent_settings = named_settings["Using named image settings"]
                if value == named_image_settings[parent_settings].get(key, None):
                    del named_settings[key]
            try:
                if value == default_image_settings[key]:
                    del named_settings[key]
            except KeyError:
                pass
    return named_image_settings


def get_setting_from_position_settings(data, setting, pos_setting):
    """Get value of a position settings variable in a named position setting. Will unpack inheritance"""
    if pos_setting in data["Named position settings"]:
        value = data["Named position settings"][pos_setting].get(setting, None)
        if value is not None:
            return value
        while True:
            parent = data["Named position settings"][pos_setting].get(
                "Using named position settings", None
            )
            if value is None:
                break
            pos_setting = parent
            value = data["Named position settings"][pos_setting].get(setting, None)
            if value is not None:
                return value
    return data["Default layer settings"]["Position settings"][setting]


def create_file(
    output_filename,
    stls,
    temp_directory,
    design_settings=None,
    stitched_images=False,
    stitched_info=None,
    minimal_file=True,
    slicer_settings=None,
    zip_output=False,
    progress=None,
):
    data = {}

    temp_directory = Path(temp_directory)
    slices_folder = temp_directory / "slices"
    minimal_slices_folder = temp_directory / f"minimized_{slices_folder.name}"
    if minimal_file:
        os.mkdir(minimal_slices_folder)

    # Sort image paths into dictionary by distance
    digit_regex = re.compile(r"(\d+)")
    image_paths = {}
    for stl in stls:
        _uuid = stl["uuid"]
        settings = stl["settings"]
        # if stitched_images:
        #     images = glob.glob(f"{temp_directory}/{_uuid}/slices/diced_images/out*.png")
        # else:
        #     images = glob.glob(f"{temp_directory}/{_uuid}/slices/out*.png")
        images = glob.glob(f"{temp_directory}/{_uuid}/slices/out*.png")
        images.sort()

        z_thick = float(settings["layer_thickness_um"])
        z_offset = float(settings["z_offset"])
        for image in images:
            # validate image
            light_engine = slicer_settings["light_engines"][settings["le"]]
            size = tuple(light_engine["resolution"])

            if not validate_slice(image, size=size):
                error_msg = "Error: Bad slice provided: " + image + "\n"
                error_msg += "All images must be 8-bit grayscale PNG format"
                sys.exit(error_msg)

            suffix = image.replace(".", "_").split("_")[-2]
            image_info = {"uuid": _uuid, "type": suffix, "path": image}

            image_num = int(digit_regex.findall(image)[-1])
            z_pos = z_offset + z_thick * image_num

            if z_pos in image_paths.keys():
                image_paths[z_pos].append(image_info)
            else:
                image_paths[z_pos] = [image_info]
    image_paths_keys = list(image_paths)
    image_paths_keys.sort()

    # get schema version
    version = 2
    for stl in stls:
        settings = stl["settings"]
        if version < 3 and (settings["le"] == "Visitech (LRS-05)"):
            print("\tUsing LRS-05 and v3")
            version = 3
        elif version < 4 and (
            settings["le"] == "Visitech (LRS-20 405nm)"
            or settings["le"] == "Visitech (LRS-20 365nm)"
            or settings["le"] == "Wintech"
        ):
            print("\tUsing LRS-20 or wintech and v4")
            version = 4
        if version < 3 and (
            float(settings["x_offset"]) != 0 or float(settings["y_offset"]) != 0
        ):
            print("\tUsing x-offseet and at least v3")
            version = 3
    json_version = {2: "2.3.0", 3: "3.1.0", 4: "4.1.0"}

    # Set JSON Header
    header = {
        "Schema version": json_version[version],
        "Image directory": slices_folder.name,
    }
    if minimal_file:
        header["Image directory"] = minimal_slices_folder.name
        unique_stores = {}
        for stl in stls:
            _uuid = stl["uuid"]
            unique_stores[_uuid] = UniqueImageStore(minimal_slices_folder / _uuid)
    data["Header"] = header

    # Set JSON Design
    if design_settings:
        data["Design"] = create_design_json(design_settings)

    # Set JSON Default layer settings
    data["Default layer settings"] = create_defaults_json(
        stls[0], version, slicer_settings, temp_directory
    )

    # Set named JSON settings
    data["Named position settings"] = create_named_position_settings(
        stls, data["Default layer settings"]["Position settings"]
    )
    data["Named image settings"] = create_named_image_settings(
        stls, data["Default layer settings"]["Image settings"], version, slicer_settings
    )

    ############################################################################################

    try:
        if not zip_output:
            output_folder = Path(
                Path(output_filename).parent / Path(output_filename).stem
            )
            # make directory if it doesn't exist, else throw error
            if output_folder.exists():
                error_msg = "Error: The directory '" + str(output_folder)
                error_msg += "' already exists. Delete it or use a different name."
                print(error_msg)
                return False
                # sys.exit(error_msg)
            os.mkdir(output_folder)
        with (
            ZipFile(output_filename, "x", compression=ZIP_DEFLATED, compresslevel=6)
            if zip_output
            else nullcontext()
        ) as myzip:
            if progress is not None:
                progress("Generating print file", 0, len(image_paths_keys))

            # if stitched_images:
            #     digit_regex = re.compile(r"(\d+).+(\d+).+(\d+)")
            # else:
            #     digit_regex = re.compile(r"(\d+)")

            burn_ins = {}
            for stl in stls:
                split = stl["settings"]["burn_in_ms"].split(",")
                if len(split) == 1 and split[0] == "":
                    continue
                burn_ins[stl["uuid"]] = split

            last_distance = 0
            layers = []
            for i, distance in enumerate(image_paths_keys):
                thickness = distance - last_distance

                layer = {}
                layer_uuids = []

                # image settings list
                image_settings_list = []
                for image_info in image_paths[distance]:
                    _uuid = image_info["uuid"]
                    image_type = image_info["type"]
                    image_path = Path(image_info["path"])

                    layer_uuids.append(_uuid)

                    # save image to zip
                    if minimal_file:
                        image_path = unique_stores[_uuid].add_image(
                            load_image_from_file(image_path), image_path
                        )
                        image_path = _uuid / image_path
                    else:
                        if zip_output:
                            myzip.write(
                                image_path,
                                arcname=Path(slices_folder.name)
                                / _uuid
                                / image_path.name,
                            )
                        else:
                            os.makedirs(
                                output_folder / slices_folder.name / _uuid, exist_ok=True
                            )
                            shutil.move(
                                image_path,
                                output_folder
                                / slices_folder.name
                                / _uuid
                                / image_path.name,
                            )

                    image_settings = {"Image file": f"{_uuid}/{image_path.name}"}

                    # burn-in
                    if _uuid in burn_ins and len(burn_ins[_uuid]) > 0:
                        image_settings["Layer exposure time (ms)"] = float(
                            burn_ins[_uuid][0]
                        )
                        del burn_ins[_uuid][0]

                    if image_type == "primary":  # primary image
                        image_settings["Using named image settings"] = f"{_uuid}_primary"

                    elif image_type == "secondary":  # secondary image
                        image_settings["Using named image settings"] = (
                            f"{_uuid}_secondary"
                        )

                    elif image_type == "tertiary":  # tertiary image
                        image_settings["Using named image settings"] = f"{_uuid}_tertiary"

                    elif image_type == "membrane":  # membrane image
                        image_settings["Using named image settings"] = f"{_uuid}_membrane"

                    else:  # normal image
                        if f"{_uuid}_default" in data["Named image settings"].keys():
                            image_settings["Using named image settings"] = (
                                f"{_uuid}_default"
                            )

                    image_settings_list.append(image_settings)
                layer["Image settings list"] = image_settings_list

                # position settings list
                if len(layer_uuids) != 1:
                    layer_uuids.sort(
                        key=lambda _uuid: (
                            get_setting_from_position_settings(
                                data, "Layer thickness (um)", f"{_uuid}_default"
                            ),
                            get_setting_from_position_settings(
                                data, "BP up acceleration (mm/sec^2)", f"{_uuid}_default"
                            ),
                            get_setting_from_position_settings(
                                data, "BP up speed (mm/sec)", f"{_uuid}_default"
                            ),
                            get_setting_from_position_settings(
                                data,
                                "BP down acceleration (mm/sec^2)",
                                f"{_uuid}_default",
                            ),
                            get_setting_from_position_settings(
                                data, "BP down speed (mm/sec)", f"{_uuid}_default"
                            ),
                            -get_setting_from_position_settings(
                                data, "Final wait (ms)", f"{_uuid}_default"
                            ),
                            -get_setting_from_position_settings(
                                data, "Up wait (ms)", f"{_uuid}_default"
                            ),
                            -get_setting_from_position_settings(
                                data, "Initial wait (ms)", f"{_uuid}_default"
                            ),
                            -get_setting_from_position_settings(
                                data, "Distance up (mm)", f"{_uuid}_default"
                            ),
                        )
                    )
                _uuid = layer_uuids[0]

                named_setting = f"{_uuid}_default"
                position_settings = {}

                # add position settings if they exist
                if named_setting in data["Named position settings"]:
                    position_settings["Using named position settings"] = named_setting

                # adjust layer thickness if nessicary
                if (
                    get_setting_from_position_settings(
                        data, "Layer thickness (um)", named_setting
                    )
                    != thickness
                ):
                    position_settings["Layer thickness (um)"] = thickness

                if len(position_settings) != 0:
                    layer["Position settings"] = position_settings

                layers.append(layer)
                last_distance = distance
                if progress is not None:
                    if not progress("Generating print file", i, len(image_paths_keys)):
                        os.remove(output_filename)
                        return False

            # Set JSON Layers
            data["Layers"] = layers

            # write json settings to zip archive
            print_settings_filename = Path("print_settings.json")

            # minimize json file
            if minimal_file:
                image_count = 0
                image_progress = 0
                for stl in stls:
                    image_count += len(
                        list((minimal_slices_folder / stl["uuid"]).iterdir())
                    )
                if progress is not None:
                    progress("Saving images", 0, len(image_paths_keys))

                # save minimal images
                for stl in stls:
                    _uuid = stl["uuid"]
                    directory = minimal_slices_folder / _uuid
                    for i, image_path in enumerate(directory.iterdir()):
                        if image_path.suffix == ".png":
                            if zip_output:
                                myzip.write(
                                    image_path,
                                    arcname=Path(minimal_slices_folder.name)
                                    / _uuid
                                    / image_path.name,
                                )
                                os.remove(image_path)
                            else:
                                os.makedirs(
                                    output_folder / minimal_slices_folder.name / _uuid,
                                    exist_ok=True,
                                )
                                shutil.move(
                                    image_path,
                                    output_folder
                                    / minimal_slices_folder.name
                                    / _uuid
                                    / image_path.name,
                                )
                            if progress is not None:
                                image_progress += 1
                                progress("Saving images", image_progress, image_count)
                    os.rmdir(directory)
                minimal_slices_folder.rmdir()

                # make minimal json
                new_layers = []
                last_layer = None
                if progress is not None:
                    progress("Minimizing JSON", 0, len(data["Layers"]))
                for i, layer in enumerate(data["Layers"]):
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
                    if progress is not None:
                        progress("Minimizing JSON", i, len(data["Layers"]))
                data["Layers"] = new_layers

            # copy stl and scad files
            if progress is not None:
                progress("Saving STLs", 0, len(stls))
            for i, stl in enumerate(stls):
                _uuid = stl["uuid"]
                parent = temp_directory
                path = parent / f"{_uuid}"
                if zip_output:
                    myzip.write(path, arcname=_uuid)
                    for j, fn in enumerate(path.iterdir()):
                        if fn.is_file():
                            afn = fn.relative_to(parent)
                            myzip.write(fn, arcname=afn)
                else:
                    os.makedirs(output_folder / _uuid, exist_ok=True)
                    for j, fn in enumerate(path.iterdir()):
                        if fn.is_file():
                            afn = fn.relative_to(parent)
                            shutil.move(fn, output_folder / afn)
                if progress is not None:
                    progress("Saving STLs", i, len(stls))

            with open(print_settings_filename, "w", newline="\r\n") as fileOut:
                json.dump(pretty_json(data), fileOut, indent=2)
            if zip_output:
                myzip.write(print_settings_filename)
                os.remove(print_settings_filename)
            else:
                shutil.move(print_settings_filename, output_folder)
    except FileExistsError:
        error_msg = "Error: The file '" + output_filename
        error_msg += "' already exists. Delete it or use a different name."
        print(error_msg)
        return False
        # sys.exit(error_msg)
    return output_filename

    #         for i, curr_img in enumerate(image_paths):
    #             regex_search = digit_regex.search(curr_img.name)
    #             image_num = int(regex_search.group(1))

    #             # if we are on a new layer, create a new layer
    #             if image_num != last_image_num:
    #                 if i != 0:
    #                     layer_num += 1
    #                 layer = {}
    #                 image_settings = []
    #             else:
    #                 layer = data["Layers"][-1]
    #                 image_settings = layer["Image settings list"]

    #             # apply exposure times to images
    #             # if image name ends in a number, it is a primary image

    #             exposure = {"Image file": curr_img.name}
    #             if re.search(r"\d+$", curr_img.stem) is not None:
    #                 # apply burn in exposure time if applicable
    #                 if layer_num < len(bi_exp_ms) and bi_exp_ms[layer_num] > exp_time_ms:
    #                     exposure["Layer exposure time (ms)"] = bi_exp_ms[layer_num]
    #             else:  # if image name ends in a letter, it is a secondary image
    #                 last_exposure = image_settings[-1]
    #                 last_exposure_time = last_exposure.get(
    #                     "Layer exposure time (ms)", exp_time_ms
    #                 )
    #                 last_exposure["Layer exposure time (ms)"] = min(
    #                     last_exposure_time, edge_dose_time_ms
    #                 )
    #                 exposure["Layer exposure time (ms)"] = max(
    #                     0, last_exposure_time - edge_dose_time_ms
    #                 )
    #                 image_settings[-1] = last_exposure

    #             if stitched_images:
    #                 px_pitch = float(stitched_info["pixel_pitch"])
    #                 x_overlap = int(stitched_info["overlap"])
    #                 y_overlap = int(stitched_info["overlap"])
    #                 x_region = int(regex_search.group(2))
    #                 y_region = int(regex_search.group(3))
    #                 x_start_px = stitched_info["x_boundries"][x_region]
    #                 y_start_px = stitched_info["y_boundries"][y_region]
    #                 x_end_px = stitched_info["x_boundries"][x_region + 1]
    #                 y_end_px = stitched_info["y_boundries"][y_region + 1]

    #                 if x_region == 0:
    #                     x_overlap = 0
    #                 if y_region == 0:
    #                     y_overlap = 0

    #                 img_width = (x_end_px - x_start_px) + x_overlap
    #                 img_height = (y_end_px - y_start_px) + y_overlap
    #                 left_padding = (2560 - img_width) // 2
    #                 top_padding = (1600 - img_height) // 2

    #                 x_offset_um = (x_start_px - x_overlap - left_padding) * px_pitch
    #                 y_offset_um = (y_start_px - y_overlap - top_padding) * px_pitch
    #                 #  hr4 coordinate system is rotated 90 degrees to the visitech's
    #                 exposure["Image y offset (um)"] = default_y_offset + x_offset_um
    #                 exposure["Image x offset (um)"] = default_x_offset + y_offset_um

    #             image_settings.append(exposure)
    #             layer["Image settings list"] = image_settings

    #             if image_num != last_image_num:
    #                 data["Layers"].append(layer)
    #                 last_image_num = image_num
    #             else:
    #                 data["Layers"][-1] = layer
