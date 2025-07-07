from pymfd.component_library import Valve20px
from pymfd.router import Router
from pymfd import set_fn, Visitech_LRS10_Device, Component, Color
from pymfd.slicer import Slicer

# from pymfd.slicer import (
#     Settings,
#     Header,
#     Design,
#     ResinType,
#     Printer,
#     Resolution,
#     BurninSettings,
#     PositionSettings,
#     ExposureSettings,
# )

set_fn(50)

# settings = Settings(
#     header=Header(
#         schema_version="4.0.0", image_directory="slices", print_under_vacuum=False
#     ),
#     design=Design(
#         user="Test User",
#         purpose="Test Design",
#         description="This is a test design for the pymfd library.",
#         resin=ResinType(
#             monomer=[("PEG", 100)],
#             uv_absorbers=[("NPS", 2.0)],
#             initiators=[("IRG", 1.0)],
#             additives=[],
#         ),
#         printer=Printer(
#             name="HR3v3", resolutions=Resolution(px_size=0.0076, px_count=(2560, 1600))
#         ),
#     ),
#     burnin_settings=BurninSettings(burnin_times=[10000, 5000, 2500]),
#     default_position_settings=PositionSettings(
#         layer_thickness=10.0,
#         distance_up=1.0,
#         initial_wait=0.0,
#         up_speed=25.0,
#         up_acceleration=50.0,
#         up_wait=0.0,
#         down_speed=20.0,
#         down_acceleration=50.0,
#         force_squeeze=False,
#         squeeze_count=0,
#         squeeze_force=0.0,
#         squeeze_wait=0.0,
#         final_wait=0.0,
#     ),
#     default_exposure_settings=ExposureSettings(
#         image_file="",
#         grayscale_correction=False,
#         image_x_offset=0.0,
#         image_y_offset=0.0,
#         exposure_time=300.0,
#         light_engine="visitech",
#         power_setting=100,
#         relative_focus_position=0.0,
#         wait_before_exposure=0.0,
#         wait_after_exposure=0.0,
#     ),
# )
# # settings.save("settings.json")


device = Visitech_LRS10_Device("TestDevice", (0, 0, 0), layers=100, layer_size=0.01)

device.add_label("device", Color.from_rgba((0, 255, 255, 127)))
device.add_label("pneumatic", Color.from_rgba((0, 255, 0, 127)))
device.add_label("fluidic", Color.from_rgba((255, 0, 255, 127)))
device.add_label("white", Color.from_rgba((255, 255, 255, 127)))

chan_size = (8, 8, 6)

# x = 10
# y = 10
# z = 10

x = 2
y = 2
z = 2

valve_grid = []
for l in range(z):
    valve_col = []
    for c in range(x):
        valve_row = []
        for r in range(y):
            v = Valve20px()
            mirror = False
            if c % 2 == 1:
                mirror = not mirror
            if l % 2 == 1:
                mirror = not mirror
            v.mirror(mirror_y=mirror, in_place=True)
            v.translate(((c + 1) * 50, (r + 1) * 50, (l + 1) * 38))
            if mirror:
                valve_row.insert(0, v)
            else:
                valve_row.append(v)

            device.add_subcomponent(f"Valve_{l}_{c}_{r}", v)
            device.relabel_labels([f"Valve_{l}_{c}_{r}.pneumatic"], "pneumatic")
            device.relabel_labels([f"Valve_{l}_{c}_{r}.fluidic"], "fluidic")

        if l % 2 == 1:
            valve_col.insert(0, valve_row)
        else:
            valve_col.append(valve_row)
    valve_grid.append(valve_col)

device.relabel_subcomponents([valve_grid[0][0][0]], "device")
device.relabel_shapes([valve_grid[0][0][0].FluidicChamber], "white")

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
rtr.route()

# IMPORTANT: If you want to see inside the inverted device, you need to create you bulk shape last
bulk_cube = device.make_cube(device._size, center=False)
bulk_cube.translate(device._position)
device.add_bulk_shape("bulk_cube", bulk_cube, label="device")

# Mesh the component
# device.render(do_bulk_difference=False)
# device.render(do_bulk_difference=True)
device.preview(render_bulk=False, do_bulk_difference=False, wireframe=False)
# device.preview(render_bulk=True, do_bulk_difference=False, wireframe=False)
# device.preview(render_bulk=True, do_bulk_difference=False, wireframe=True)
# device.preview(render_bulk=True, do_bulk_difference=True, wireframe=False)
# device.preview(render_bulk=True, do_bulk_difference=True, wireframe=True)
# device.slice()

slicer = Slicer(
    device=device,
    settings={},
    filename="test_slicer",
)
slicer.make_print_file()
