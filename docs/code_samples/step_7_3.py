import pymfcad

# Define constants for device dimensions and resolution
# Pixel/layer units are the core constraint for DLP‑SLA 3D printing.
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

# Add labels for bulk and void regions (labels are just named color groups)
device.add_label("bulk", pymfcad.Color.from_name("aqua", 120))
device.add_label("void", pymfcad.Color.from_name("tomato", 200))

# Define bulk region and add it to the component
bulk = pymfcad.Cube((DEVICE_X, DEVICE_Y, DEVICE_Z))
device.add_bulk("bulk_shape", bulk, label="bulk")

# Define channel dimensions and position
CHANNEL_SIZE = (2560, 13, 10)
CHANNEL_POS = (0, 800, 150)

# Create a channel (centered for easy placement, then translated)
channel = pymfcad.Cube(CHANNEL_SIZE, center=True)
# Translate to absolute coordinates (centered x, absolute y/z)
channel.translate((CHANNEL_POS[0] + CHANNEL_SIZE[0] // 2, CHANNEL_POS[1], CHANNEL_POS[2]))
device.add_void("channel", channel, label="void")

# Define pinhole dimensions
PINHOLE_WIDTH = 150
PINHOLE_LENGTH = 200
# Convert a physical width to layer units to keep pinholes circular in mm
PINHOLE_HEIGHT = PINHOLE_WIDTH * PX_SIZE / LAYER_SIZE

# Create pinholes and add them as voids
pinhole_a = pymfcad.Cylinder(height=1, radius=1).rotate((0, 90, 0))
# Resize to keep pinholes circular in mm (px and layer sizes differ)
pinhole_a.resize((PINHOLE_LENGTH, PINHOLE_WIDTH, PINHOLE_HEIGHT))
pinhole_a.translate((CHANNEL_POS[0], CHANNEL_POS[1], CHANNEL_POS[2]))

pinhole_b = pymfcad.Cylinder(height=1, radius=1).rotate((0, 90, 0))
# Resize to keep pinholes circular in mm (px and layer sizes differ)
pinhole_b.resize((PINHOLE_LENGTH, PINHOLE_WIDTH, PINHOLE_HEIGHT))
pinhole_b.translate(
    (CHANNEL_POS[0] + CHANNEL_SIZE[0] - PINHOLE_LENGTH, CHANNEL_POS[1], CHANNEL_POS[2])
)

device.add_void("pin_a", pinhole_a, label="void")
device.add_void("pin_b", pinhole_b, label="void")

device.preview()
