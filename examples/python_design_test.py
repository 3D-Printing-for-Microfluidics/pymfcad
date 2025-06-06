from pymfd.router import Router
from pymfd.visualizer import Visualizer
from pymfd.microfluidic_designer import Device, Component, Color, set_manifold3d_backend, set_fn

from components.valve20px import Valve20px
from components.testcube import TestCube
from components.pinhole import Pinhole


set_manifold3d_backend()
# set_fn(100)
visualizer = Visualizer()

# ############### 1 ##################
# component = Component(
#     size=(10, 10, 10),
#     position=(0, 0, 0),
#     px_size=0.0076,
#     layer_size=0.01
# )
# # Add label
# component.add_label("default", Color.from_rgba((0, 255, 0, 127)))
# # Add a cube shape
# component.add_shape("simple_cube", component.make_cube((1, 1, 1), center=False), label="default")

# # Mesh the component
# scene = visualizer.mesh_component_recursive(component)
# scene.export("pymfd/visualizer/component.glb")


################ 2 ##################
device_size = (2560, 1600, 250)
device_position = (0, 0, 0)
device = Device("TestDevice", device_size, device_position)

component = Pinhole()
device.add_subcomponent("valve", component)

# IMPORTANT: If you want to see inside the inverted device, you need to create you bulk shape last
device.add_label("device", Color.from_rgba((0, 255, 255, 63)))
bulk_cube = device.make_cube(device_size, center=False).translate(device_position)
device.add_bulk_shape("cube", bulk_cube, label="device")

# device.invert_device()

# Mesh the component
scene = visualizer.mesh_component_recursive(device, wireframe_bulk=True)
# scene = visualizer.mesh_component_recursive(device, wireframe_bulk=False)
scene.export("pymfd/visualizer/component.glb")


# ############### 3 ##################
# component = Component(
#     size=(255, 255, 15),
#     position=(0, 0, 0),
#     px_size=0.0076,
#     layer_size=0.01
# )

# component.add_subcomponent("R1", Valve20px().translate((0, 0, 0)))
# component.add_subcomponent("R2", Valve20px().rotate(90).translate((0, 0, 0)))
# component.add_subcomponent("R3", Valve20px().rotate(180).translate((0, 0, 0)))
# component.add_subcomponent("R4", Valve20px().rotate(270).translate((0, 0, 0)))

# # component.add_subcomponent("M1", TestCube().translate((10, 10, 0)))
# # component.add_subcomponent("M2", TestCube().translate((10, 10, 0)).rotate(90))
# # component.add_subcomponent("M3", TestCube().translate((10, 10, 0)).rotate(180))
# # component.add_subcomponent("M4", TestCube().translate((10, 10, 0)).rotate(270))

# # component.add_subcomponent("M1", TestCube().translate((10, 10, 0)))
# # component.add_subcomponent("M2", TestCube().translate((10, 10, 0)).mirror(mirror_x=True))
# # component.add_subcomponent("M3", TestCube().translate((10, 10, 0)).mirror(mirror_x=True, mirror_y=True))
# # component.add_subcomponent("M4", TestCube().translate((10, 10, 0)).mirror(mirror_y=True))

# # component.add_subcomponent("M1", TestCube().translate((0, 0, 0)))
# # component.add_subcomponent("M2", TestCube().mirror(mirror_x=True).translate((75, 0, 0)))
# # component.add_subcomponent("M3", TestCube().mirror(mirror_x=True, mirror_y=True).translate((150, 0, 0)))
# # component.add_subcomponent("M4", TestCube().mirror(mirror_y=True).translate((225, 0, 0)))

# # Mesh the component
# scene = visualizer.mesh_component_recursive(component)
# scene.export("pymfd/visualizer/component.glb")


# ################ router test ##################
# device_size = (150, 150, 100)
# device_position = (0, 0, 0)
# device = Device("TestDevice", device_size, device_position)

# device.add_label("autopath", Color.from_rgba((0, 255, 0, 127)))
# device.add_label("device", Color.from_name("aqua", 63))

# c1 = Valve20px().translate((18, 35, 40))
# c2 = Valve20px().translate((52, 35, 40))

# device.add_subcomponent("Valve1", c1)
# device.add_subcomponent("Valve2", c2)

# chan_size = (8, 8, 6)
# r = Router(component=device, channel_size=chan_size, channel_margin=chan_size)
# r.autoroute_channel(c2.F_OUT, c1.F_IN, label="autopath")
# r.autoroute_channel(c1.P_OUT, c2.F_IN, label="autopath")
# r.autoroute_channel(c1.F_OUT, c2.P_IN, label="autopath")
# r.autoroute_channel(c2.P_OUT, c1.P_IN, label="autopath")
# r.route()

# # IMPORTANT: If you want to see inside the inverted device, you need to create you bulk shape last
# bulk_cube = device.make_cube(device_size, center=False)
# bulk_cube.translate(device_position)
# device.add_bulk_shape("bulk1", bulk_cube, label="device")

# # device.invert_device()

# # Mesh the component
# scene = visualizer.mesh_component_recursive(device, wireframe_bulk=True)
# scene.export("pymfd/visualizer/component.glb")