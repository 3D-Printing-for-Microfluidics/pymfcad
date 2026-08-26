from pymfcad import (
    Color,
    Component,
    Cube,
)
from pymfcad.component_library import Pinhole, Valve20px

from .serpentine_channel import SerpentineChannel
from .y_junction_mixer import YJunctionMixer

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

# Inlet pinholes
inlet_a = Pinhole()
inlet_a.translate((0, 500 - inlet_a._size[1] / 2, DEVICE_Z / 2 - inlet_a._size[2] / 2))
inlet_b = Pinhole()
inlet_b.translate(
    (0, (DEVICE_Y - 500) - inlet_b._size[1] / 2, DEVICE_Z / 2 - inlet_b._size[2] / 2)
)

# Pneumatic pinholes
pneumatic_a = Pinhole().rotate(90)
pneumatic_a.translate(
    (400 + pneumatic_a._size[0] / 2, 0, DEVICE_Z / 2 - pneumatic_a._size[2] / 2)
)
pneumatic_b = Pinhole().rotate(-90)
pneumatic_b.translate(
    (400 - pneumatic_b._size[0] / 2, DEVICE_Y, DEVICE_Z / 2 - pneumatic_a._size[2] / 2)
)

# 20 px valves
valve_a = Valve20px().rotate(-90)
valve_a.translate((500, 500 + valve_a._size[0] / 2, DEVICE_Z / 2 - valve_a._size[2] / 2))
valve_b = Valve20px().rotate(-90)
valve_b.translate(
    (500, (DEVICE_Y - 500) + valve_b._size[0] / 2, DEVICE_Z / 2 - valve_b._size[2] / 2)
)

# Mixer + serpentine + outlet pinhole
mixer = YJunctionMixer().translate((DEVICE_X / 3, DEVICE_Y / 2, 150))
serp = SerpentineChannel()
serp.translate((DEVICE_X / 2, 800 - serp._size[1] / 2, 150 - serp._size[2] / 2))
outlet = Pinhole().rotate(180)
outlet.translate(
    (DEVICE_X, DEVICE_Y / 2 + outlet._size[1] / 2, DEVICE_Z / 2 - outlet._size[2] / 2)
)

device.add_subcomponent("inlet_a", inlet_a)
device.add_subcomponent("inlet_b", inlet_b)
device.add_subcomponent("pneu_a", pneumatic_a)
device.add_subcomponent("pneu_b", pneumatic_b)
device.add_subcomponent("valve_a", valve_a)
device.add_subcomponent("valve_b", valve_b)
device.add_subcomponent("mixer", mixer)
device.add_subcomponent("serp", serp)
device.add_subcomponent("outlet", outlet)

device.relabel(
    {
        "bulk": "bulk",
        "device": "bulk",
        "fluidic": "fluidic",
        "pneumatic": "pneumatic",
        "membrane": "membrane",
        "mixer.void": "fluidic",
        "serp.void": "fluidic",
        "inlet_a.void": "fluidic",
        "inlet_b.void": "fluidic",
        "outlet.void": "fluidic",
        "pneu_a.void": "pneumatic",
        "pneu_b.void": "pneumatic",
    },
    recursive=True,
)

device.preview()
