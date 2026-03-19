### Parameterized
import pymfcad

# Define constants for device dimensions and resolution
# Pixel/layer units are the core constraint for DLP‑SLA printing.
PX_SIZE = 0.0076
LAYER_SIZE = 0.01

DEVICE_X = 2560
DEVICE_Y = 1600
DEVICE_Z = 300

# Create a new device (final print = bulk minus voids)
device = pymfcad.Device(
    name="example_device",
    position=(0, 0, 0),
    layers=DEVICE_Z,
    layer_size=LAYER_SIZE,
    px_count=(DEVICE_X, DEVICE_Y),
    px_size=PX_SIZE,
)

# Add labels for bulk and void regions (labels are just named color groups)
device.add_label("bulk", pymfcad.Color.from_name("aqua", 120))
device.add_label("void", pymfcad.Color.from_name("tomato", 200))

# Define bulk region and add it to the device
bulk = pymfcad.Cube((DEVICE_X, DEVICE_Y, DEVICE_Z))
device.add_bulk("bulk_shape", bulk, label="bulk")


# Define channel and pinhole dimensions and position
CHANNEL_SIZE = (2560, 13, 10)
CHANNEL_POS = (0, 800, 150)
PINHOLE_WIDTH = 150
PINHOLE_LENGTH = 200
# Convert a physical width to layer units to keep pinholes circular in mm
PINHOLE_HEIGHT = PINHOLE_WIDTH * PX_SIZE / LAYER_SIZE

# Create a channel (centered for easy placement, then translated)
channel = pymfcad.Cube(CHANNEL_SIZE, center=True)
# Translate to absolute device coordinates (centered x, absolute y/z)
channel.translate((CHANNEL_POS[0]+CHANNEL_SIZE[0]//2, CHANNEL_POS[1], CHANNEL_POS[2]))

# Create pinholes
pinhole_a = pymfcad.Cylinder(height=1, radius=1).rotate((0,90,0))
# Resize to keep pinholes circular in mm (px and layer sizes differ)
pinhole_a.resize((PINHOLE_LENGTH, PINHOLE_WIDTH, PINHOLE_HEIGHT))
pinhole_a.translate((CHANNEL_POS[0], CHANNEL_POS[1], CHANNEL_POS[2]))

pinhole_b = pymfcad.Cylinder(height=1, radius=1).rotate((0,90,0))
# Resize to keep pinholes circular in mm (px and layer sizes differ)
pinhole_b.resize((PINHOLE_LENGTH, PINHOLE_WIDTH, PINHOLE_HEIGHT))
pinhole_b.translate((CHANNEL_POS[0]+CHANNEL_SIZE[0]-PINHOLE_LENGTH, CHANNEL_POS[1], CHANNEL_POS[2]))

# Combine channel and pinholes into a single void region (boolean union)
channel_unit = channel + pinhole_a + pinhole_b


# Parametric toggles make it easy to explore variants without editing geometry
INCLUDE_TEXT = True

FONT_SIZE = 100
FONT_HEIGHT = 10
LABELS = ["A", "B", "C", "D", "E"]

for i, letter in enumerate(LABELS):
    offset = (0, (i-2) * 300, 0)

    unit = channel_unit.copy().translate(offset)
    device.add_void(f"channel_{letter}", unit, label="void")

    # Example conditional: only add text for the first four
    if i < 4:
        text = pymfcad.TextExtrusion(letter, height=FONT_HEIGHT, font_size=FONT_SIZE)
        text.rotate((90, 0, 90))
        text.translate((CHANNEL_POS[0], CHANNEL_POS[1] + (i-2) * 300 - 20, CHANNEL_POS[2] + PINHOLE_HEIGHT/2 + 10))
        # text = text.translate((CHANNEL_POS[0] + PINHOLE_LENGTH + 10, CHANNEL_POS[1] + (i-2) * 300 + 10, DEVICE_Z - FONT_HEIGHT))
        device.add_void(f"label_{letter}", text, label="void")

# Preview the device
device.preview()
