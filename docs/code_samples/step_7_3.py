### POLYCHANNEL
## Base
import pymfcad

# Define constants for device dimensions and resolution
# Pixel/layer units are the core constraint for DLP‑SLA printing.
PX_SIZE = 0.0076
LAYER_SIZE = 0.01

DEVICE_WIDTH = 2560
DEVICE_LENGTH = 1600
DEVICE_HEIGHT = 300

# Create a new device (final print = bulk minus voids)
device = pymfcad.Device(
    name="example_device",
    position=(0, 0, 0),
    layers=DEVICE_HEIGHT,
    layer_size=LAYER_SIZE,
    px_count=(DEVICE_WIDTH, DEVICE_LENGTH),
    px_size=PX_SIZE,
)

# Add labels for bulk and void regions (labels are just named color groups)
device.add_label("bulk", pymfcad.Color.from_name("aqua", 120))
device.add_label("void", pymfcad.Color.from_name("tomato", 255))

# Define bulk region and add it to the device
bulk = pymfcad.Cube((DEVICE_WIDTH, DEVICE_LENGTH, DEVICE_HEIGHT))
device.add_bulk("bulk_shape", bulk, label="bulk")

# Define channel dimensions and position
CHANNEL_SIZE = (2560, 13, 10)
CHANNEL_POS = (0, 800, 150)
PINHOLE_WIDTH = 150
PINHOLE_LENGTH = 200
# Convert a physical width to layer units to keep pinholes circular in mm
PINHOLE_HEIGHT = PINHOLE_WIDTH * PX_SIZE / LAYER_SIZE


polychannel = pymfcad.Polychannel(
    [
        pymfcad.PolychannelShape(
            shape_type="sphere",
            position=(CHANNEL_POS[0], CHANNEL_POS[1], CHANNEL_POS[2]),
            size=(0, PINHOLE_WIDTH, PINHOLE_HEIGHT),
        ),
        pymfcad.PolychannelShape(
            position=(PINHOLE_LENGTH, 0, 0),
        ),
        pymfcad.PolychannelShape(
            shape_type="cube",
            position=(0, 0, 0),
            size=(0, CHANNEL_SIZE[1], CHANNEL_SIZE[2]),
        ),
        pymfcad.PolychannelShape(
            position=(CHANNEL_SIZE[0] - PINHOLE_LENGTH * 2, 0, 0),
        ),
        pymfcad.PolychannelShape(
            shape_type="sphere",
            position=(0, 0, 0),
            size=(0, PINHOLE_WIDTH, PINHOLE_HEIGHT),
        ),
        pymfcad.PolychannelShape(
            position=(PINHOLE_LENGTH, 0, 0),
        ),
    ]
)

device.add_void("polychannel_unit", polychannel, label="void")


# Preview the device
device.preview()
