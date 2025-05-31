from microfluidic_designer import set_manifold3d_backend
from visualizer import Visualizer

set_manifold3d_backend()
visualizer = Visualizer()

################ 1 ##################
# from microfluidic_designer import Component, NetType
# component = Component(
#     name="SimpleCube",
#     position=(0, 0, 0),
#     size=(10, 10, 10),
#     px_size=0.0076,
#     layer_size=0.01
# )
# # Add a cube shape
# component.add_shape(component.make_cube((1, 1, 1), center=False, nettype=NetType(name="Cube", color=(255, 0, 0, 255))))
#
# # Mesh the component
# scene = visualizer.mesh_component_recursive(component)
# scene.export("component.glb")


# ################ 2 ##################
# from microfluidic_designer import Device, NetType
# from valve20px import Valve20px

# device_size = (50, 50, 38)
# device_position = (0, 0, 0)
# device = Device("TestDevice", device_position, device_size)

# component = Valve20px("Valve")
# device.add_subcomponent(component)

# # IMPORTANT: If you want to see inside the inverted device, you need to create you bulk shape last
# device.add_nettype(NetType(name="device", color=(0, 255, 255, 63)))
# bulk_cube = device.make_cube(device_size, center=False, nettype="device").translate(device_position)
# device.add_bulk_shape(bulk_cube)

# # device.invert_device()

# # Mesh the component
# scene = visualizer.mesh_component_recursive(device, wireframe_bulk=True)
# # scene = visualizer.mesh_component_recursive(device, wireframe_bulk=False)
# scene.export("component.glb")


# ############### 3 ##################
# from microfluidic_designer import Component, NetType
# from testcube import TestCube
# from valve20px import Valve20px

# component = Component(
#     name="",
#     position=(0, 0, 0),
#     size=(255, 255, 15),
#     px_size=0.0076,
#     layer_size=0.01
# )

# # component.add_subcomponent(Valve20px("1").translate((0, 0, 0)))
# # component.add_subcomponent(Valve20px("R2").rotate(90).translate((0, 0, 0)))
# # component.add_subcomponent(Valve20px("R3").rotate(180).translate((0, 0, 0)))
# # component.add_subcomponent(Valve20px("R4").rotate(270).translate((0, 0, 0)))

# # component.add_subcomponent(TestCube("1").translate((10, 10, 0)))
# # component.add_subcomponent(TestCube("M2").translate((10, 10, 0)).rotate(90))
# # component.add_subcomponent(TestCube("M3").translate((10, 10, 0)).rotate(180))
# # component.add_subcomponent(TestCube("M4").translate((10, 10, 0)).rotate(270))

# component.add_subcomponent(TestCube("1").translate((10, 10, 0)))
# component.add_subcomponent(TestCube("M2").translate((10, 10, 0)).mirror(mirror_x=True))
# component.add_subcomponent(TestCube("M3").translate((10, 10, 0)).mirror(mirror_x=True, mirror_y=True))
# component.add_subcomponent(TestCube("M4").translate((10, 10, 0)).mirror(mirror_y=True))

# # component.add_subcomponent(TestCube("1").translate((0, 0, 0)))
# # component.add_subcomponent(TestCube("M2").mirror(mirror_x=True).translate((75, 0, 0)))
# # component.add_subcomponent(TestCube("M3").mirror(mirror_x=True, mirror_y=True).translate((150, 0, 0)))
# # component.add_subcomponent(TestCube("M4").mirror(mirror_y=True).translate((225, 0, 0)))

# # Mesh the component
# scene = visualizer.mesh_component_recursive(component)
# scene.export("component.glb")


################ router test ##################
from microfluidic_designer import Device, Component, NetType
from valve20px import Valve20px
from router import autoroute_channel

device_size = (150, 150, 100)
device_position = (0, 0, 0)
device = Device("TestDevice", device_position, device_size)

device.add_nettype(NetType(name="autopath", color=(0, 255, 0, 127)))
device.add_nettype(NetType(name="device", color=(0, 255, 255, 63)))

c1 = Valve20px("Valve").translate((18, 35, 40))
c2 = Valve20px("Valve").translate((52, 35, 40))

device.add_subcomponent(c1)
device.add_subcomponent(c2)

chan_size = (8, 8, 6)
device.add_shape(autoroute_channel(device, c2.get_port("F_OUT"), c1.get_port("F_IN"), channel_size=chan_size, channel_margin=chan_size, nettype="autopath"))
device.add_shape(autoroute_channel(device, c1.get_port("P_OUT"), c2.get_port("F_IN"), channel_size=chan_size, channel_margin=chan_size, nettype="autopath"))
device.add_shape(autoroute_channel(device, c1.get_port("F_OUT"), c2.get_port("P_IN"), channel_size=chan_size, channel_margin=chan_size, nettype="autopath"))
device.add_shape(autoroute_channel(device, c2.get_port("P_OUT"), c1.get_port("P_IN"), channel_size=chan_size, channel_margin=chan_size, nettype="autopath"))

# device.route(c2.get_port("F_OUT"), c1.get_port("F_IN"), channel_size=chan_size, channel_margin=chan_size, nettype="autopath")
# device.route(c1.get_port("P_OUT"), c2.get_port("F_IN"), channel_size=chan_size, channel_margin=chan_size, nettype="autopath")
# device.route(c1.get_port("F_OUT"), c2.get_port("P_IN"), channel_size=chan_size, channel_margin=chan_size, nettype="autopath")
# device.route(c2.get_port("P_OUT"), c1.get_port("P_IN"), channel_size=chan_size, channel_margin=chan_size, nettype="autopath")

# IMPORTANT: If you want to see inside the inverted device, you need to create you bulk shape last

bulk_cube = device.make_cube(device_size, center=False, nettype="device")
bulk_cube.translate(device_position)
device.add_bulk_shape(bulk_cube)

# device.invert_device()

# Mesh the component
scene = visualizer.mesh_component_recursive(device, wireframe_bulk=True)
scene.export("component.glb")