import pymfcad
from pymfcad import Color, Cube

# Make sure the files are named y_junction_mixer.py and serpentine_channel.py and are in the same folder as this script. If you saved them elsewhere, update the import path accordingly.

PX_SIZE = 0.0076
LAYER_SIZE = 0.01

DEVICE_X = 2560
DEVICE_Y = 1600
DEVICE_Z = 300

# Create a new component (final print = bulk minus voids)
device = pymfcad.Component(
    size=[DEVICE_X, DEVICE_Y, DEVICE_Z],
    layer_size=LAYER_SIZE,
    px_size=PX_SIZE,
)

device.add_label("bulk", Color.from_name("aqua", 127))
device.add_label("void", Color.from_name("red", 255))

device.add_bulk("bulk_shape", Cube(device._size, center=False), label="bulk")

device.preview()
