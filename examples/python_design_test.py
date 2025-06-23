from pymfd.router import Router
from pymfd.components import Valve20px, TestCube, Pinhole
from pymfd import PolychannelShape, BezierCurveShape, Device, Component, Color, set_manifold3d_backend, set_fn

set_manifold3d_backend()
set_fn(50)

# ############### 1 Test all basic components ##################
# component = Component(
#     size=(2560, 1600, 10),
#     position=(0, 0, 0),
#     px_size=0.0076,
#     layer_size=0.01
# )
# chan_size = (8, 8, 6)
# # Add label
# component.add_label("default", Color.from_rgba((0, 255, 0, 127)))
# # Add a shape
# # component.add_shape("simple_cube", component.make_cube((2, 2, 2), center=False).translate((1,1,1)), label="default")
# # component.add_shape("simple_round_cube", component.make_rounded_cube((10, 10, 10), (2.5,2.5,2.5), center=True), label="default")
# # component.add_shape("simple_sphere", component.make_sphere((2,2,2), center=True), label="default")
# # component.add_shape("simple_cylinder", component.make_cylinder(r=1, h=2, center_xy=False, center_z=False), label="default")
# # component.add_shape("text", component.make_text("Hello Greg!!"), label="default")
# # component.add_shape("import", component.import_model("examples/Diamond_21.stl").resize((1,1,1)), label="default")
# # component.add_shape("tpms", component.make_tpms_cell((10,10,8)), label="default")
# component.add_shape("polychannel", component.make_polychannel(
#     [
#         PolychannelShape("sphere", position=(0,20,0), size=chan_size),
#         PolychannelShape("sphere", position=(-33,0,0), size=chan_size, corner_radius=10),
#         PolychannelShape("rounded_cube", position=(0,0,-30), size=chan_size, rounded_cube_radius=(1,1,1)),
#         PolychannelShape("sphere", position=(0,-41,0), size=chan_size),
#     ]
# ), label="default")
# # component.add_shape("beziercurve", component.make_polychannel(
# #     [
# #         PolychannelShape("cube", position=(0,0,0), size=chan_size),
# #         BezierCurveShape(control_points=[(500,0,0),(500,500,0)], number_of_segments=100, shape_type="sphere", position=(500, 500, 500)),
# #     ]
# # ), label="default")

# # Mesh the component
# component.preview()
# # component.render()
# # component.slice_component()


# ################ 2 Test subcomonents ##################
# device_size = (2560, 1600, 250)
# device_position = (0, 0, 0)
# device = Device("TestDevice", device_size, device_position)

# component = Pinhole()
# device.add_subcomponent("valve", component)

# # IMPORTANT: If you want to see inside the inverted device, you need to create you bulk shape last
# device.add_label("device", Color.from_rgba((0, 255, 255, 63)))
# bulk_cube = device.make_cube(device_size, center=False).translate(device_position)
# device.add_bulk_shape("cube", bulk_cube, label="device")

# # Mesh the component
# component.render()


# ############### 3 Test translations, mirroring and rotations ##################
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
# component.render()


# ################ 4 Test Routing ##################
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
# # r.autoroute_channel(c2.F_OUT, c1.F_IN, label="autopath")
# # r.autoroute_channel(c1.P_OUT, c2.F_IN, label="autopath")
# # r.autoroute_channel(c1.F_OUT, c2.P_IN, label="autopath")
# # r.autoroute_channel(c2.P_OUT, c1.P_IN, label="autopath")
# # r.route_with_fractional_path(c2.P_OUT, c1.F_IN, [(0,-1,0),(1,0,0),(0,0,2),(0,2,0),(0,0,-1)], label="autopath")
# print(c2.P_OUT.position, c1.F_IN.position, tuple(a-b for a, b in zip(c1.F_IN.position, c2.P_OUT.position)))
# r.route_with_polychannel(c2.P_OUT, c1.F_IN, [
#         PolychannelShape("sphere", position=(0,20,0), size=chan_size),
#         PolychannelShape("sphere", position=(-33,0,0), size=chan_size),
#         PolychannelShape("sphere", position=(0,0,-30), size=chan_size),
#         PolychannelShape("sphere", position=(0,-41,0), size=chan_size),
#     ], label="autopath")
# r.route()

# # IMPORTANT: If you want to see inside the inverted device, you need to create you bulk shape last
# bulk_cube = device.make_cube(device_size, center=False)
# bulk_cube.translate(device_position)
# device.add_bulk_shape("bulk1", bulk_cube, label="device")

# # Mesh the component
# device.preview()
# # device.render()
# # device.slice_component()