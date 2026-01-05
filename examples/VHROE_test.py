import inspect
from pymfd.component_library import Pinhole

from pymfd import *

set_fn(50)

vdev = Visitech_LRS10_Device("vdev", position=(10, 0, 0), layers=100, layer_size=0.015)

wdev = Wintech_Device("wdev", position=(100, 0, 1000), layers=100, layer_size=0.0015)

vdev.add_label("device", Color.from_name("aqua", 100))
wdev.add_label("device", Color.from_name("blue", 100))

vdev.add_bulk_shape(
    "v_bulk", Cube(vdev._size, center=False).translate(vdev._position), label="device"
)
wdev.add_bulk_shape(
    "w_bulk", Cube(wdev._size, center=False).translate(wdev._position), label="device"
)
vdev.add_subcomponent("wintech", wdev.translate((0, 0, 0)))
vdev.add_subcomponent("wintech", wdev.translate((100, 0, 0)))

vdev.preview()
# dev.preview()

settings = Settings(
    # user="Test User",
    # purpose="Test Design",
    # description="This is a test design for the pymfd library.",
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
                origin=(960.0, 540.0),
            ),
        ],
        vaccum_available=True,
        xy_stage_available=True,
    ),
    resin=ResinType(),
    print_under_vacuum=True,
    default_position_settings=PositionSettings(
        # distance_up=1.0,
        # initial_wait=0.0,
        # up_speed=25.0,
        # up_acceleration=50.0,
        # up_wait=0.0,
        # down_speed=20.0,
        # down_acceleration=50.0,
        # force_squeeze=False,
        # squeeze_count=0,
        # squeeze_force=0.0,
        # squeeze_wait=0.0,
        # final_wait=0.0,
    ),
    default_exposure_settings=ExposureSettings(
        grayscale_correction=True,
        # exposure_time=300.0,
        # power_setting=100,
        # relative_focus_position=0.0,
        # wait_before_exposure=0.0,
        # wait_after_exposure=0.0,
    ),
)

slicer = Slicer(
    device=vdev,
    settings=settings,
    filename="test_slicer",
    minimize_file=True,
    zip_output=False,
)
slicer.make_print_file()
