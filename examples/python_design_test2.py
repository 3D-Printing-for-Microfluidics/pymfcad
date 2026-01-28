from openmfd import (
    set_fn,
    Visitech_LRS10_Device,
    Component,
    Color,
    Cube,
    Router,
    Slicer,
    Settings,
    ResinType,
    Printer,
    LightEngine,
    PositionSettings,
    ExposureSettings,
)
from openmfd.component_library import Valve20px

set_fn(50)

settings = Settings(
    # user="Test User",
    # purpose="Test Design",
    # description="This is a test design for the OpenMFD library.",
    printer=Printer(
        name="HR3v3",
        light_engines=[
            LightEngine(px_size=0.0076, px_count=(2560, 1600), wavelengths=[365])
        ],
    ),
    resin=ResinType(),
    default_position_settings=PositionSettings(
        # distance_up=1.0,
        # initial_wait=0.0,
        # up_speed=25.0,
        # up_acceleration=50.0,
        # up_wait=0.0,
        # down_speed=20.0,
        # down_acceleration=50.0,
        # final_wait=0.0,
    ),
    default_exposure_settings=ExposureSettings(
        # grayscale_correction=False,
        # exposure_time=300.0,
        # power_setting=100,
        # relative_focus_position=0.0,
        # wait_before_exposure=0.0,
        # wait_after_exposure=0.0,
    ),
)
settings.save("settings.json")
settings = Settings.from_file("settings.json")
settings.save("settings2.json")


device = Visitech_LRS10_Device("TestDevice", (0, 0, 0), layers=250, layer_size=0.01)

device.add_label("device", Color.from_rgba((0, 255, 255, 127)))
device.add_label("pneumatic", Color.from_rgba((0, 255, 0, 127)))
device.add_label("fluidic", Color.from_rgba((255, 0, 255, 127)))
device.add_label("highlight", Color.from_rgba((255, 255, 255, 127)))
device.add_label("membrane", Color.from_rgba((255, 255, 0, 127)))

chan_size = (8, 8, 6)

# x = 2
# y = 2
# z = 2

# x = 2
# y = 2
# z = 7

x = 50
y = 32
z = 7
# z = 1

valve_grid = []
for l in range(z):
    valve_col = []
    for c in range(x):
        valve_row = []
        for r in range(y):
            v = Valve20px(quiet=True)
            mirror = False
            if c % 2 == 1:
                mirror = not mirror
            if l % 2 == 1:
                mirror = not mirror
            v.mirror(mirror_y=mirror, in_place=True)
            # v.translate((c * 50 + 50, r * 50 + 50, l * 40 + 20))
            v.translate((c * 48 + 25, r * 48 + 25, l * 35 + 15))
            if mirror:
                valve_row.insert(0, v)
            else:
                valve_row.append(v)

            device.add_subcomponent(f"Valve_{c}_{r}_{l}", v)

        if l % 2 == 1:
            valve_col.insert(0, valve_row)
        else:
            valve_col.append(valve_row)
    valve_grid.append(valve_col)

device.relabel({
    "device": "device",
    "pneumatic": "pneumatic",
    "fluidic": "fluidic",
    "membrane": "membrane",
    valve_grid[0][0][0].shapes["FluidicChamber"]: "highlight",
    "Valve_1_1_0.PneumaticShapes": "highlight",
}, recursive=True)

rtr = Router(component=device, channel_size=chan_size, channel_margin=chan_size)
for l in range(z):
    for c in range(x):
        for r in range(y):
            v1 = None
            v2 = None
            if r != 0:
                v1 = valve_grid[l][c][r - 1]
                v2 = valve_grid[l][c][r]
            elif c != 0:
                v1 = valve_grid[l][c - 1][-1]
                v2 = valve_grid[l][c][0]
            elif l != 0:
                v1 = valve_grid[l - 1][-1][-1]
                v2 = valve_grid[l][0][0]
            else:
                continue
            try:
                rtr.autoroute_channel(v1.F_OUT, v2.F_IN, label="fluidic")
            except TypeError:
                pass
            try:
                rtr.autoroute_channel(v1.P_OUT, v2.P_IN, label="pneumatic")
            except TypeError:
                pass

rtr.finalize_routes()

# IMPORTANT: If you want to see inside the inverted device, you need to create you bulk shape last
bulk_cube = Cube(device._size, center=False)
bulk_cube.translate(device._position)
device.add_bulk("bulk_cube", bulk_cube, label="device")

# Mesh the component
# device.render("component.glb", do_bulk_difference=False)
# device.render("component.glb")
device.preview()

slicer = Slicer(
    device=device,
    settings=settings,
    filename="test_slicer",
    minimize_file=True,
    zip_output=False,
)
slicer.make_print_file()
