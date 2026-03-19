import pymfcad
from pymfcad import Device, Router, Port, Color, Cube, PolychannelShape, BezierCurveShape
from pymfcad.component_library import Pinhole, Valve20px

from . import YJunctionMixer
from . import SerpentineChannel

PX_SIZE = 0.0076
LAYER_SIZE = 0.01

DEVICE_X = 2560
DEVICE_Y = 1600
DEVICE_Z = 300

device = Device(
    name="full_device",
    position=(0, 0, 0),
    layers=DEVICE_Z,
    layer_size=LAYER_SIZE,
    px_count=(DEVICE_X, DEVICE_Y),
    px_size=PX_SIZE,
)

device.add_label("bulk", Color.from_name("aqua", 127))
device.add_label("fluidic", Color.from_name("blue", 255))
device.add_label("pneumatic", Color.from_name("red", 255))
device.add_label("membrane", Color.from_name("green", 255))

device.add_bulk("bulk_shape", Cube(device._size, center=False), label="bulk")

# device.preview()

# Inlet pinholes
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

pneumatic_a = Pinhole().rotate(90)
pneumatic_a.translate(
    (400 + pneumatic_a._size[0]/2, 
     0, 
     DEVICE_Z/2 - pneumatic_a._size[2]/2)
)
pneumatic_b = Pinhole().rotate(-90)
pneumatic_b.translate(
    (400 - pneumatic_b._size[0]/2, 
     DEVICE_Y, 
     DEVICE_Z/2 - pneumatic_a._size[2]/2)
    )

# 20 px valves
valve_a = Valve20px().rotate(-90)
valve_a.translate(
    (500, 
    500 + valve_a._size[0]/2, 
    DEVICE_Z/2 - valve_a._size[2]/2
    )
)
valve_b = Valve20px().rotate(-90)
valve_b.translate(
    (500, 
    (DEVICE_Y - 500) + valve_b._size[0]/2, 
    DEVICE_Z/2 - valve_b._size[2]/2
    )
)

# Mixer + serpentine + outlet pinhole
mixer = YJunctionMixer().translate((DEVICE_X/3, DEVICE_Y/2, 150))
serp = SerpentineChannel()
serp.translate((DEVICE_X/2, 800 - serp._size[1]/2, 150 - serp._size[2]/2))
outlet = Pinhole().rotate(180)
outlet.translate((DEVICE_X, DEVICE_Y/2 + outlet._size[1]/2, DEVICE_Z/2 - outlet._size[2]/2))


device.add_subcomponent("inlet_a", inlet_a)
device.add_subcomponent("inlet_b", inlet_b)
device.add_subcomponent("pneu_a", pneumatic_a)
device.add_subcomponent("pneu_b", pneumatic_b)
device.add_subcomponent("valve_a", valve_a)
device.add_subcomponent("valve_b", valve_b)
device.add_subcomponent("mixer", mixer)
device.add_subcomponent("serp", serp)
device.add_subcomponent("outlet", outlet)

# device.preview()

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

# device.preview()

router = Router(device, channel_size=(8, 8, 6), channel_margin=(8, 8, 6))

# Inlets → valves → mixer
router.autoroute_channel(inlet_a.port, valve_a.F_IN, label="fluidic", direction_preference=("Z", "Y", "X"))
router.autoroute_channel(inlet_b.port, valve_b.F_IN, label="fluidic", direction_preference=("Z", "Y", "X"))
router.autoroute_channel(valve_a.F_OUT, mixer.inlet1, label="fluidic")
router.autoroute_channel(valve_b.F_OUT, mixer.inlet2, label="fluidic")

# Mixer → serpentine
router.autoroute_channel(mixer.outlet, serp.inlet, label="fluidic")

# router.finalize_routes()
# device.preview()

# Serpentine → expanded viewing area → outlet (polychannel routing)
view_path = [
    PolychannelShape(shape_type="cube", position=(0, 0, 0), size=(8, 8, 6)),
    PolychannelShape(position=(0, -serp._size[1]/2, 0), size=(8, 8, 6)),
    PolychannelShape(position=(0, 0, -serp._size[2]/2), size=(8, 8, 6)),
    PolychannelShape(position=(50, 0, 0), size=(0, 8, 6)),
    PolychannelShape(position=(20, 0, 0), size=(0, 100, 6)),
    PolychannelShape(position=(100, 0, 0), size=(0, 100, 6)),
    PolychannelShape(position=(20, 0, 0), size=(0, 8, 6)),
]
router.route_with_polychannel(serp.outlet, outlet.port, view_path, label="fluidic")

# router.finalize_routes()
# device.preview()

diff_x = valve_a.P_IN._position[0] - pneumatic_a.port._position[0] - valve_a.P_IN._size[0]/2 - pneumatic_a.port._size[0]/2
diff_y = valve_a.P_IN._position[1] - pneumatic_a.port._position[1] - valve_a.P_IN._size[1]/2 + pneumatic_a.port._size[1]/2
diff_z = valve_a.P_IN._position[2] - pneumatic_a.port._position[2]
router.route_with_polychannel(
    pneumatic_a.port,
    valve_a.P_IN,
    [
        BezierCurveShape(
            control_points=[(3 * diff_x, diff_y/2, 0), (-3 * diff_x, diff_y/2, 0)],
            bezier_segments=50,
            position=(diff_x, diff_y, diff_z),
            size=(8, 8, 6),
            shape_type="cube",
            rounded_cube_radius=(3, 3, 3),
        )
    ],
    label="pneumatic",
)

diff_x = valve_b.P_IN._position[0] - pneumatic_b.port._position[0] - valve_b.P_IN._size[0]/2 - pneumatic_b.port._size[0]/2
diff_y = valve_b.P_IN._position[1] - pneumatic_b.port._position[1] + valve_b.P_IN._size[1]/2 + pneumatic_b.port._size[1]/2
diff_z = valve_b.P_IN._position[2] - pneumatic_b.port._position[2]
router.route_with_polychannel(
    pneumatic_b.port,
    valve_b.P_IN,
    [
        BezierCurveShape(
            control_points=[(3 * diff_x, diff_y/2, 0), (-3 * diff_x, diff_y/2, 0)],
            bezier_segments=50,
            position=(diff_x, diff_y, diff_z),
            size=(8, 8, 6),
            shape_type="cube",
            rounded_cube_radius=(3, 3, 3),
        )
    ],
    label="pneumatic",
)

# router.finalize_routes()
# device.preview()

# External (unused) control ports
device.add_port(
    "ctrl_a_stub",
    Port(Port.PortType.INOUT, (800, 0, 200), (8, 8, 6), Port.SurfaceNormal.NEG_Y),
)
device.add_port(
    "ctrl_b_stub",
    Port(Port.PortType.INOUT, (800, DEVICE_Y, 200), (8, 8, 6), Port.SurfaceNormal.POS_Y),
)

router.autoroute_channel(valve_a.P_OUT, device.ports["ctrl_a_stub"], label="pneumatic", direction_preference=("Z", "X", "Y"))
router.autoroute_channel(valve_b.P_OUT, device.ports["ctrl_b_stub"], label="pneumatic", direction_preference=("Z", "X", "Y"))

# router.finalize_routes()
# device.preview()

# # Mark them as connected so they don’t show as unconnected ports
device.connect_port(device.ports["ctrl_a_stub"])
device.connect_port(device.ports["ctrl_b_stub"])

router.finalize_routes()
device.preview()

# Render to a file for sharing or slicing
device.render("full_device.stl")
device.render("full_device.glb")
device.render("full_device.3mf")