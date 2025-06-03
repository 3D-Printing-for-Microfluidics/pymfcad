from microfluidic_designer import set_manifold3d_backend, Device, Component, NetType
from components.valve20px import Valve20px
from router import Router
from visualizer import Visualizer

set_manifold3d_backend()
visualizer = Visualizer()

device_size = (2560, 1600, 500)
device_position = (0, 0, 0)
device = Device("TestDevice", device_position, device_size)

device.add_nettype(NetType(name="pneumatic", color=(0, 255, 0, 255)))
device.add_nettype(NetType(name="fluidic", color=(0, 255, 255, 255)))

chan_size = (8, 8, 6)

x = 10
y = 10
z = 5

valve_grid = []
for l in range(z):
    valve_col = []
    for c in range(x):
        valve_row = []
        for r in range(y):
            v = Valve20px(f"Valve-{l}-{c}-{r}")
            mirror = False
            if c%2 == 1:
                mirror = not mirror
            if l%2 == 1:
                mirror = not mirror
            v.mirror(mirror_y=mirror, in_place=True)
            v.translate(((c+1)*50, (r+1)*50, (l+1)*38))
            if mirror:
                valve_row.insert(0, v)
            else:
                valve_row.append(v)

            device.add_subcomponent(v)
        if l%2 == 1:
            valve_col.insert(0, valve_row)
        else:
            valve_col.append(valve_row)
    valve_grid.append(valve_col)

rtr = Router(component=device, channel_size=chan_size, channel_margin=chan_size)
for l in range(z):
    for c in range(x):
        for r in range(y):
            v1 = None
            v2 = None
            if r != 0:
                v1 = valve_grid[l][c][r-1]
                v2 = valve_grid[l][c][r]
            elif c != 0:
                v1 = valve_grid[l][c-1][-1]
                v2 = valve_grid[l][c][0]
            elif l != 0:
                v1 = valve_grid[l-1][-1][-1]
                v2 = valve_grid[l][0][0]
            else:
                continue
            try:
                rtr.autoroute_channel(v1.get_port("F_OUT"), v2.get_port("F_IN"), nettype="fluidic")
            except TypeError:
                pass
            try:
                rtr.autoroute_channel(v1.get_port("P_OUT"), v2.get_port("P_IN"), nettype="pneumatic")
            except TypeError:
                pass
rtr.route()

# IMPORTANT: If you want to see inside the inverted device, you need to create you bulk shape last

bulk_cube = device.make_cube(device_size, center=False, nettype="device")
bulk_cube.translate(device_position)
device.add_bulk_shape(bulk_cube)

# device.invert_device()

# Mesh the component
scene = visualizer.mesh_component_recursive(device, wireframe_bulk=True)
scene.export("component.glb")