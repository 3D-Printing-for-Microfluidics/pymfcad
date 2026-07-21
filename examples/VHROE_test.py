from pymfcad import *
from pymfcad.component_library import Pinhole

set_fn(50)

vdev = Device.with_visitech_1x("vdev", position=(0, 0, 0), layers=100, layer_size=0.015)

wdev = Device.with_wintech("wdev", position=(0, 0, 0), layers=100, layer_size=0.0015)

vdev.add_label("device", Color.from_name("aqua", 100))
wdev.add_label("device", Color.from_name("blue", 100))

vdev.add_bulk(
    "v_bulk", Cube(vdev._size, center=False), label="device"
)
wdev.add_bulk(
    "w_bulk", Cube(wdev._size, center=False), label="device"
)
wdev.add_void(
    "test_void",
    Cube((100, 100, 100), center=False).translate((0, 0, 0)),
    label="device",
)
wdev.translate((0, 0, 100))
wdev2 = wdev.copy().translate((150, 150, 0))

vdev.add_subcomponent("wintech", wdev)
vdev.add_subcomponent("wintech2", wdev2)

# wdev2.preview()
vdev.preview()

settings = Settings(
    # user="Test User",
    # purpose="Test Design",
    # description="This is a test design for the PyMFCAD library.",
    printer=Printer(
        name="HR3v3",
        light_engines=[
            LightEngine(
                name="visitech",
                px_size=0.0076,
                px_count=(2560, 1600),
                wavelengths=[365],
                grayscale_available=[True],
            ),
            LightEngine(
                name="wintech",
                px_size=0.00075,
                px_count=(1920, 1080),
                wavelengths=[365],
                grayscale_available=[False],
            ),
        ],
        vacuum_available=True,
        xy_stage_available=True,
    ),
    resin=ResinType(bulk_exposure=300.0),
    default_position_settings=PositionSettings(
        # distance_up=1.0,
        # initial_wait=0.0,
        # up_speed=25.0,
        # up_acceleration=50.0,
        # up_wait=0.0,
        # down_speed=20.0,
        # down_acceleration=50.0,
        # final_wait=0.0,
    ),
    default_exposure_settings=ExposureSettings(
        grayscale_correction=True,
        # bulk_exposure_multiplier=300.0 / 300.0,
        # power_setting=100,
        # relative_focus_position=0.0,
        # wait_before_exposure=0.0,
        # wait_after_exposure=0.0,
    ),
)

slicer = Slicer(
    device=vdev,
    settings=settings,
    filename="VHROE_demo",
    minimize_file=True,
    zip_output=False,
)
slicer.make_print_file()
