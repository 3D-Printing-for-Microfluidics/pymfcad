from pymfcad import (
    Color,
    Component,
    Cube,
)

PX_SIZE = 0.0076
LAYER_SIZE = 0.01

DEVICE_X = 2560
DEVICE_Y = 1600
DEVICE_Z = 300

device = Component(
    size=[DEVICE_X, DEVICE_Y, DEVICE_Z],
    layer_size=LAYER_SIZE,
    px_size=PX_SIZE,
)

device.add_label("bulk", Color.from_name("aqua", 127))
device.add_label("fluidic", Color.from_name("blue", 255))
device.add_label("pneumatic", Color.from_name("red", 255))
device.add_label("membrane", Color.from_name("green", 255))

device.add_bulk("bulk_shape", Cube(device._size, center=False), label="bulk")

device.preview()
