from openmfd import (
    Device,
    Settings,
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
    Slicer,
)

# Printer definition
printer = Printer(
    name="HR3v3",
    light_engines=[LightEngine(px_size=0.0076, px_count=(2560, 1600), wavelengths=[365])],
    xy_stage_available=True,
)

# Special print technique: print under vacuum
vacuum = PrintUnderVacuum(
    enabled=True,
    target_vacuum_level_torr=10.0,
    vacuum_wait_time=30.0,
)

# Layer-level technique: squeeze out resin
position_settings = PositionSettings(
    distance_up=1.0,
    final_wait=0.0,
)

# Base exposure settings (no special image techniques)
exposure_settings = ExposureSettings(
    exposure_time=250.0,
)

settings = Settings(
    printer=printer,
    resin=ResinType(),
    default_position_settings=position_settings,
    default_exposure_settings=exposure_settings,
    special_print_techniques=[vacuum],
    user="example",
    purpose="special techniques demo",
    description="Demonstrates print, layer, and image techniques.",
)

# Simple device
device = Device(
    name="SpecialTechDemo",
    position=(0, 0, 0),
    layers=80,
    layer_size=0.01,
    px_count=(2560, 1600),
    px_size=0.0076,
)

device.add_label("bulk", Color.from_name("gray", 127))
device.add_label("void", Color.from_name("aqua", 127))

bulk = Cube(device._size, center=False)
bulk.translate(device._position)

device.add_bulk("bulk", bulk, label="bulk")

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
        special_layer_techniques=[SqueezeOutResin(enabled=True, count=2, squeeze_force=5.0, squeeze_time=200.0)],
    ),
    label="void",
)

device.add_regional_settings(
    "zero_um_region",
    zero_um_region,
    ExposureSettings(
        exposure_time=250.0,
        special_image_techniques=[ZeroMicronLayer(enabled=True, count=2)],
    ),
    label="void",
)

device.add_regional_settings(
    "film_region",
    film_region,
    ExposureSettings(
        exposure_time=250.0,
        special_image_techniques=[PrintOnFilm(enabled=True, distance_up_mm=0.3)],
    ),
    label="void",
)

# Optional: override defaults at device level
# device.add_default_position_settings(position_settings)
# device.add_default_exposure_settings(exposure_settings)

# Slice
slicer = Slicer(
    device=device,
    settings=settings,
    filename="special_techniques_demo",
    minimize_file=True,
    zip_output=False,
)

slicer.make_print_file()
