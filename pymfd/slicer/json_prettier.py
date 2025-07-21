json_order = [
    "Header",
    "Design",
    "Default layer settings",
    "Variables",
    "Named position settings",
    "Named image settings",
    "Templates",
    "Layers",
    "Schema version",
    "Image directory",
    "Print under vacuum",
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
    "Number of duplications",
    "Position settings",
    "Image settings",
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
    "Final wait (ms)",
    "Using named image settings",
    "Image file",
    "Do light grayscale correction",
    "Do dark grayscale correction",
    "Image x offset (um)",
    "Image y offset (um)",
    "Layer exposure time (ms)",
    "Light engine",
    "Light engine power setting",
    "Light engine wavelength (nm)",
    "Relative focus position (um)",
    "Wait before exposure (ms)",
    "Wait after exposure (ms)",
]


def pretty_json(input):
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
