from pymfcad import (
    Device,
    StitchedDevice,
    Component,
    Settings,
    Printer,
    LightEngine,
    ResinType,
    PositionSettings,
    ExposureSettings,
    Color,
    Cube,
    Slicer,
    Polychannel,
    PolychannelShape,
    TPMS,
    TPMSComponent
)

# Printer with XY stage (recommended when using offsets)
settings = Settings(
    printer=Printer(
        name="MR1v1",
        light_engines=[
            LightEngine(
                "visitech", px_size=0.0152, px_count=(2560, 1600), wavelengths=[405], settle_time_ms=5000
            ),
            LightEngine(
                "wintech", px_size=0.00075, px_count=(1920, 1080), wavelengths=[365], settle_time_ms=5000
            ),
        ],
        xy_stage_available=True,
    ),
    resin=ResinType(
        bulk_exposure=1000.0,
        monomer=[("PEG", 100)],
        uv_absorbers=[("AVO", 2.48), ("NPS", 2.69)],
        initiators=[("IRG", 1)],
    ),
    default_position_settings=PositionSettings(),
    default_exposure_settings=ExposureSettings(),
    user="Dallin Miner",
    purpose="Long TPMS Test",
    description="Test print for ~15cm HPLC column"
)

# Outer device (lower resolution, larger pixel size)
outer = Device.with_visitech_2x(
    name="OuterDevice",
    position=(0, 0, 0),
    layers=100,
    layer_size=0.015
)

outer.add_default_exposure_settings(ExposureSettings(wavelength=405, power_setting=300, bulk_exposure_multiplier=1.0))
outer.add_default_position_settings(PositionSettings(distance_up=1.0, 
                                                     up_speed=50.0, 
                                                     up_acceleration=350.0,
                                                     down_speed=50.0,
                                                     down_acceleration=350.0))

outer.add_label("bulk_outer", Color.from_name("gray", 127))
outer.add_label("void", Color.from_name("aqua", 127))

# Outer bulk
# outer_bulk = Cube(outer._size, center=False).translate(outer._position)
outer_bulk = Cube((1000, 600, 100)).translate((outer._size[0]/2 - 500, outer._size[1]/2 - 300, 0))
outer.add_bulk("outer_bulk", outer_bulk, label="bulk_outer")

pinhole_d = 70
pinhole_l = 100
channel_w = 10
channel_h = 10

chan_list = []
chan_list += [
    PolychannelShape(
        "sphere",
        position=(outer._size[0]/2 - 500, outer._size[1]/2, 50),
        size=(0, pinhole_d, pinhole_d)
    ),
    PolychannelShape(
        "sphere",
        position=(pinhole_l, 0, 0),
        size=(0, pinhole_d, pinhole_d)
    ),
    PolychannelShape(
        "cube",
        position=(0, 0, 0),
        size=(0, channel_w, channel_h)
    ),
    PolychannelShape(
        "cube",
        position=(80, 0, 0),
        size=(channel_w, channel_w, channel_h),
    ),
    PolychannelShape(
        "cube",
        position=(0, 0, 45),
        size=(channel_w, channel_w, channel_h),
    ),
    PolychannelShape(
        "cube",
        position=(0, -200, 0),
        size=(channel_w, channel_w, channel_h),
    ),
    PolychannelShape(
        "cube",
        position=(100, 0, 0),
        size=(channel_w, channel_w, channel_h),
        corner_radius=10
    ),
]


for i in range(10):
    chan_list += [
        PolychannelShape(
        "cube",
        position=(440, 0, 0),
        size=(channel_w, channel_w, channel_h),
    ),
    PolychannelShape(
        "cube",
        position=(0, 20, 0),
        size=(channel_w, channel_w, channel_h),
    ),
    PolychannelShape(
        "cube",
        position=(-440, 0, 0),
        size=(channel_w, channel_w, channel_h)
    ),
    PolychannelShape(
        "cube",
        position=(0, 20, 0),
        size=(channel_w, channel_w, channel_h)
    ),
]

chan_list += [
    PolychannelShape(
        "cube",
        position=(440, 0, 0),
        size=(channel_w, channel_w, channel_h),
    ),
    PolychannelShape(
        "cube",
        position=(100, 0, 0),
        size=(channel_w, channel_w, channel_h),
        corner_radius=0
    ),
    PolychannelShape(
        "cube",
        position=(0, -200, 0),
        size=(channel_w, channel_w, channel_h),
    ),
    PolychannelShape(
        "cube",
        position=(0, 0, -45),
        size=(channel_w, channel_w, channel_h),
    ),
    PolychannelShape(
        "cube",
        position=(80, 0, 0),
        size=(channel_w, channel_w, channel_h),
    ),
    PolychannelShape(
        "sphere",
        position=(0, 0, 0),
        size=(0, pinhole_d, pinhole_d),
    ),
    PolychannelShape(
        "sphere",
        position=(pinhole_l, 0, 0),
        size=(0, pinhole_d, pinhole_d)
    ),
]

channel = Polychannel(chan_list)
outer.add_void("channel", channel, label="void")

stitched_wintech = StitchedDevice.with_wintech(
    name="StitchedDemo",
    position=(0, 0, 0),
    layers=100,
    layer_size=0.0015,
    tiles_x=2, #5
    tiles_y=2, #8
    overlap_px=0,
)
stitched_wintech.add_default_exposure_settings(ExposureSettings(wavelength=365, power_setting=60, bulk_exposure_multiplier=0.01))
stitched_wintech.add_default_position_settings(PositionSettings(distance_up=0.5, 
                                                up_speed=25.0, 
                                                up_acceleration=1.0,
                                                down_speed=20.0,
                                                down_acceleration=50.0))
stitched_wintech.add_label("bulk", Color.from_name("blue", 127))
stitched_wintech.add_label("void", Color.from_name("aqua", 127))

# stitched_wintech.add_bulk("bulk_shape", Cube((1,1,1), center=False), label="bulk")
# tpms = TPMSComponent(stitched_wintech._size, 
#                     position=(0,0,900), 
#                     unit_cell_size=(20, 20, 10),
#                     tpms_func=TPMS.diamond,
#                     fill=0.0,
#                     refinement=20,
#                     px_size=0.00075,
#                     layer_size=0.0015
#                     )
# stitched_wintech.add_subcomponent("tpms", tpms)

from pymfcad import TPMSGrid
stitched_wintech.add_bulk("bulk_shape", TPMSGrid(
    size=stitched_wintech._size,
    unit_cell_size=(40, 40, 20),
    func=TPMS.diamond,
    fill=0.0,
    refinement=20,
    quiet=True
), label="bulk")

# Embed the inner device into the outer device
# calculate translation (center inner device within outer device)
translation_x = (outer._size[0]*outer._px_size - stitched_wintech._size[0]*stitched_wintech._px_size) / 2
translation_y = (outer._size[1]*outer._px_size - stitched_wintech._size[1]*stitched_wintech._px_size) / 2
print(outer._size, stitched_wintech._size, translation_x, translation_y, translation_x / outer._px_size, translation_y / outer._px_size)
stitched_wintech.translate((translation_x / outer._px_size, translation_y / outer._px_size, 90))  # translation in outer device pixels/layers
outer.add_subcomponent("stitched_wintech", stitched_wintech, subtract_bounding_box=False, hide_in_render=False)

outer.preview()

slicer = Slicer(
    device=outer,
    settings=settings,
    filename="long_tpms_column",
    minimize_file=True,
    zip_output=False,
)

slicer.make_print_file()
