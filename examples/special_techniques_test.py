from pymfcad import (
    Component,
    Printer,
    LightEngine,
    ResinType,
    PositionSettings,
    ExposureSettings,
    PrintUnderVacuum,
    SqueezeOutResin,
    ZeroMicronLayer,
    PrintOnFilm,
    Color,
    Cube,
    PrintFileGenerator,
)

# Base exposure settings (no special image techniques)
exposure_settings = ExposureSettings(
    bulk_exposure_multiplier=250.0 / 300.0,
)

# Layer-level technique: squeeze out resin
position_settings = PositionSettings(
    distance_up=1.0,
    final_wait=0.0,
)

# Printer definition
printer = Printer(
    name="HR3v3",
    light_engines=[
        LightEngine(
            px_size=0.0076,
            px_count=(2560, 1600),
            wavelengths=[365],
            default_exposure_settings=[exposure_settings],
        )
    ],
    xy_stage_available=True,
    vacuum_available=True,
    default_position_settings=position_settings,
)

# Special print technique: print under vacuum
vacuum = PrintUnderVacuum(
    enabled=True,
    target_vacuum_level_torr=10.0,
    vacuum_wait_time=30.0,
)

# Simple device
device = Component(
    size=(2560, 1600, 80),
    layer_size=0.01,
    px_size=0.0076,
)

device.add_label("bulk", Color.from_name("gray", 127))
device.add_label("void", Color.from_name("aqua", 127))
device.add_label("squeeze", Color.from_name("aqua", 127))
device.add_label("zero", Color.from_name("aqua", 127))
device.add_label("film", Color.from_name("aqua", 127))

bulk = Cube(device._size, center=False)
bulk.translate(device._position)

device.add_bulk("bulkshape", bulk, label="bulk")

device.add_void(
    "channel",
    Cube((800, 60, 20)).translate((200, 400, 20)),
    label="void",
)

# Image-level techniques split into separate regions
squeeze_region = Cube((2560, 1600, 20))
zero_um_region = Cube((900, 250, 40)).translate((200, 200, 20))
film_region = Cube((900, 250, 40)).translate((200, 900, 50))

device.add_regional_settings(
    "squeeze_region",
    squeeze_region,
    PositionSettings(
        special_layer_techniques=[
            SqueezeOutResin(enabled=True, count=2, squeeze_force=5.0, squeeze_time=200.0)
        ],
    ),
    label="squeeze",
)

device.add_regional_settings(
    "zero_um_region",
    zero_um_region,
    ExposureSettings(
        bulk_exposure_multiplier=250.0 / 300.0,
        special_image_techniques=[ZeroMicronLayer(enabled=True, count=2)],
    ),
    label="zero",
)

device.add_regional_settings(
    "film_region",
    film_region,
    ExposureSettings(
        bulk_exposure_multiplier=250.0 / 300.0,
        special_image_techniques=[PrintOnFilm(enabled=True, distance_up_mm=0.3)],
    ),
    label="film",
)

# Optional: override defaults at device level
# device.add_default_position_settings(position_settings)
# device.add_default_exposure_settings(exposure_settings)

device.preview()

# Slice
slicer = PrintFileGenerator(
    filename="special_techniques_demo",
    author="example",
    purpose="special techniques demo",
    description="Demonstrates print, layer, and image techniques.",
    component=device,
    printer=printer,
    resin=ResinType(bulk_exposure=300.0),
    special_print_techniques=[vacuum],
    minimize_file=True,
    zip_output=False,
)

slicer.run(overwrite=True)
