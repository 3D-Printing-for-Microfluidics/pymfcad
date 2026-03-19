import pymfcad
from pymfcad import Component, Router, Color, Cube
from pymfcad.component_library import Pinhole

# Import custom components from previous steps
from . import YJunctionMixer
from . import SerpentineChannel

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

device.add_label("bulk", Color.from_name("aqua", 127))
device.add_label("void", Color.from_name("red", 255))

device.add_bulk("bulk_shape", Cube(device._size, center=False), label="bulk")

# device.preview()

inlet_a = Pinhole()
inlet_a.translate(
    (0, 
    500 - inlet_a._size[1]/2, 
    DEVICE_Z/2 - inlet_a._size[2]/2
    )
)
inlet_b = Pinhole()
inlet_b.translate(
    (0, 
    (DEVICE_Y - 500) - inlet_b._size[1]/2, 
    DEVICE_Z/2 - inlet_b._size[2]/2
    )
)
# Y‑junction near the left side
y = YJunctionMixer()
y.translate((DEVICE_X/3, DEVICE_Y/2, DEVICE_Z/2 - y._size[2]/2))

# Serpentine between Y‑junction and outlet
serp = SerpentineChannel()
serp.translate((DEVICE_X/2, 800 - serp._size[1]/2, DEVICE_Z/2 - serp._size[2]/2))

# Outlet pinhole on the right side (flip to face inward)
outlet = Pinhole().rotate(180)
outlet.translate(
    (DEVICE_X, 
    DEVICE_Y/2 + outlet._size[1]/2, 
    DEVICE_Z/2 - outlet._size[2]/2
    )
)

device.add_subcomponent("inlet_a", inlet_a)
device.add_subcomponent("inlet_b", inlet_b)
device.add_subcomponent("y", y)
device.add_subcomponent("serp", serp)
device.add_subcomponent("outlet", outlet)

# device.preview()

router = Router(device, channel_size=(8, 8, 6), channel_margin=(8, 8, 6))

# Inlets into the Y‑junction
router.autoroute_channel(
    inlet_a.port,
    y.inlet1,
    label="void",
    direction_preference=("X", "Y", "Z"),
)
router.autoroute_channel(
    inlet_b.port,
    y.inlet2,
    label="void",
    direction_preference=("X", "Y", "Z"),
)

# Y‑junction to serpentine
router.autoroute_channel(
    y.outlet,
    serp.inlet,
    label="void",
    direction_preference=("X", "Y", "Z"),
)

# Serpentine to outlet pinhole
router.autoroute_channel(
    serp.outlet,
    outlet.port,
    label="void",
    direction_preference=("Z", "Y", "X"),
)

router.finalize_routes()

device.preview()