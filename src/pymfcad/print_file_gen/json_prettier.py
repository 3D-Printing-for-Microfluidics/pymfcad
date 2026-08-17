json_order = [
    "Header",
    "Design",
    "Default layer settings",
    "Special print techniques",
    "Variables",
    "Named position settings",
    "Named image settings",
    "Named layer groups",
    "Templates",
    "Layers",
    "Schema version",
    "Image directory",
    "Comment",
    "User",
    "Purpose",
    "Description",
    "Resin",
    "3D printer",
    "Design file",
    "STL file",
    "Slicer",
    "Date",
    "Parent template",
    "Using templates",
    "Position settings",
    "Image settings",
    "Print under vacuum",
    "Enable vacuum",
    "Target vacuum level (Torr)",
    "Vacuum wait time (sec)",
    "Squeeze out resin",
    "Enable squeeze",
    "0 um layer",
    "Enable 0 um layer",
    "Print on film",
    "Enable print on film",
    "Number of duplications",
    "Image settings list",
    "Using named position settings",
    "Layer thickness (um)",
    "Distance up (mm)",
    "Initial wait (ms)",
    "BP up speed (mm/sec)",
    "BP up acceleration (mm/sec^2)",
    "Up wait (ms)",
    "BP down speed (mm/sec)",
    "BP down acceleration (mm/sec^2)",
    "Enable force squeeze",
    "Squeeze count",
    "Squeeze force (N)",
    "Squeeze wait (ms)",
    "Squeeze time (ms)",
    "Final wait (ms)",
    "Special layer techniques",
    "Using named image settings",
    "Image file",
    "Do grayscale correction",
    "Image x offset (um)",
    "Image y offset (um)",
    "Layer exposure time (ms)",
    "Light engine",
    "Light engine power setting",
    "Light engine wavelength (nm)",
    "Relative focus position (um)",
    "Wait before exposure (ms)",
    "Wait after exposure (ms)",
    "Special image techniques",
]


def pretty_json(input):
    """Prettify JSON dictionary or list by ordering keys according to json_order."""
    if type(input) is dict:
        new_dict = {}
        for item in json_order:
            if item in input.keys():
                new_dict[item] = pretty_json(input[item])
                del input[item]
        for item in input.keys():
            new_dict[item] = pretty_json(input[item])
        return new_dict
    elif type(input) is list:
        new_list = []
        for item in input:
            new_list.append(pretty_json(item))
        return new_list
    else:
        return input
