from pymfcad import *
from pymfcad.printer_library import MR1v1
from pymfcad.resin_library import NPS

set_fn(50)

vdev = Component(size=(2560, 1600, 100), px_size=0.0152, layer_size=0.015)
vdev.add_default_exposure_settings(ExposureSettings(wavelength=405))

wdev = Component(size=(1920, 1080, 100), px_size=0.00075, layer_size=0.0015)

vdev.add_label("device", Color.from_name("aqua", 100))
wdev.add_label("device", Color.from_name("blue", 100))

vdev.add_bulk("v_bulk", Cube(vdev._size, center=False), label="device")
wdev.add_bulk("w_bulk", Cube(wdev._size, center=False), label="device")
wdev.add_void(
    "test_void",
    Cube((100, 100, 100), center=False).translate((0, 0, 0)),
    label="device",
)
wdev.translate((0, 0, 90))
wdev2 = wdev.copy().translate((150, 150, 0))

vdev.add_subcomponent("wintech", wdev)
vdev.add_subcomponent("wintech2", wdev2)

# wdev2.preview()
vdev.preview()

slicer = PrintFileGenerator(
    component=vdev,
    printer=MR1v1,
    resin=NPS,
    filename="VHROE_demo",
    minimize_file=True,
    zip_output=False,
)
slicer.run()
