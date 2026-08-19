from pymfcad import (
    Device,
    Cube,
    RoundedCube,
    Sphere,
    Cylinder,
    TextExtrusion,
    ImportModel,
    TPMS,
    Polychannel,
    PolychannelShape,
    BezierCurveShape,
    Component,
    Color,
    set_fn,
    Router,
)
from pymfcad.component_library import Valve20px, TestCube, Pinhole

set_fn(50)

# # ############### 1 Test all basic components ##################
# component = Component(
#     size=(2560, 1600, 10), position=(0, 0, 0), px_size=0.0076, layer_size=0.01
# )
# chan_size = (8, 8, 6)
# # Add label
# component.add_label("default", Color.from_rgba((0, 255, 0, 127)))
# # Add a shape
# # component.add_bulk(
# #     "simple_cube",
# #     Cube((2, 2, 2), center=False).translate((1, 1, 1)),
# #     label="default",
# # )
# # component.add_bulk(
# #     "simple_round_cube",
# #     RoundedCube((10, 10, 10), (2.5, 2.5, 2.5), center=True),
# #     label="default",
# # )
# # component.add_bulk("simple_sphere", Sphere((2, 2, 2), center=False), label="default")
# # component.add_bulk(
# #     "simple_cylinder",
# #     Cylinder(radius=1, height=2, center_xy=False, center_z=False),
# #     label="default",
# # )
# # component.add_bulk("text", TextExtrusion("Hello!!"), label="default")
# # component.add_bulk(
# #     "import",
# #     ImportModel("examples/Diamond_51.stl").resize((10, 10, 8)).translate((-10, 0, 0)),
# #     label="default",
# # )
# # component.add_bulk(
# #     f"tpms",
# #     TPMS(func=TPMS.diamond, size=(10, 10, 8), fill=0.0, refinement=50),
# #     label="default",
# # )
# # component.add_bulk(
# #     "polychannel",
# #     Polychannel(
# #         [
# #             PolychannelShape("cube", position=(0, 20, 0), size=chan_size),
# #             PolychannelShape(
# #                 "sphere", position=(-33, 0, 0), size=chan_size, corner_radius=10
# #             ),
# #             PolychannelShape(
# #                 "rounded_cube",
# #                 position=(0, 0, -30),
# #                 size=chan_size,
# #                 rounded_cube_radius=(1, 1, 1),
# #                 corner_radius=0,
# #             ),
# #             PolychannelShape("cube", position=(0, -41, 0), size=chan_size),
# #         ]
# #     ),
# #     label="default",
# # )
# # component.add_bulk(
# #     "beziercurve",
# #     Polychannel(
# #         [
# #             PolychannelShape("sphere", position=(0, 0, 0), size=chan_size),
# #             BezierCurveShape(
# #                 control_points=[(100, 0, 0), (100, 100, 0)],
# #                 bezier_segments=10,
# #                 shape_type="sphere",
# #                 position=(100, 100, 100),
# #             ),
# #         ]
# #     ),
# #     label="default",
# # )

# # Mesh the component
# component.preview()

# ################ 2 Test subcomonents ##################
# device_size = (2560, 1600, 250)
# device_position = (0, 0, 0)
# device = Device.with_visitech_1x("TestDevice", device_position, layers=250, layer_size=0.01)

# component = Valve20px()
# device.add_subcomponent("valve", component)

# # IMPORTANT: If you want to see inside the inverted device, you need to create you bulk shape last
# device.add_label("device", Color.from_rgba((0, 255, 255, 63)))
# bulk_cube = Cube(device_size, center=False).translate(device_position)
# device.add_bulk("cube", bulk_cube, label="device")

# # Mesh the component
# # device.render()
# component.preview()


# ############### 3 Test translations, mirroring and rotations ##################
# component = Component(
#     size=(255, 255, 15), position=(0, 0, 0), px_size=0.0076, layer_size=0.01
# )

# component.add_label("default", Color.from_rgba((0, 255, 0, 0)))

# # # Rotation then translation
# c1 = TestCube().translate((10, 10, 0))
# c2 = TestCube().rotate(90).translate((10, 10, 0))
# c3 = TestCube().rotate(180).translate((10, 10, 0))
# c4 = TestCube().rotate(270).translate((10, 10, 0))

# # Translation then rotation
# # c1 = TestCube().translate((10, 10, 0))
# # c2 = TestCube().translate((10, 10, 0)).rotate(90)
# # c3 = TestCube().translate((10, 10, 0)).rotate(180)
# # c4 = TestCube().translate((10, 10, 0)).rotate(270)

# # # Inplace rotation
# # c1 = TestCube().translate((0, 0, 0))
# # c2 = TestCube().rotate(90, in_place=True).translate((75, 0, 0))
# # c3 = TestCube().rotate(180, in_place=True).translate((150, 0, 0))
# # c4 = TestCube().rotate(270, in_place=True).translate((225, 0, 0))

# # # Mirroring than translation
# # c1 = TestCube().translate((10, 10, 0))
# # c2 = TestCube().mirror(mirror_x=True).translate((10, 10, 0))
# # c3 = TestCube().mirror(mirror_x=True, mirror_y=True).translate((10, 10, 0))
# # c4 = TestCube().mirror(mirror_y=True).translate((10, 10, 0))

# # # Translation then mirroring
# # c1 = TestCube().translate((10, 10, 0))
# # c2 = TestCube().translate((10, 10, 0)).mirror(mirror_x=True)
# # c3 = TestCube().translate((10, 10, 0)).mirror(mirror_x=True, mirror_y=True)
# # c4 = TestCube().translate((10, 10, 0)).mirror(mirror_y=True)

# # # Inplace mirroring
# # c1 = TestCube().translate((0, 0, 0))
# # c2 = TestCube().mirror(mirror_x=True, in_place=True).translate((75, 0, 0))
# # c3 = TestCube().mirror(mirror_x=True, mirror_y=True, in_place=True).translate((150, 0, 0))
# # c4 = TestCube().mirror(mirror_y=True, in_place=True).translate((225, 0, 0))

# component.add_subcomponent("C1", c1)
# component.add_subcomponent("C2", c2)
# component.add_subcomponent("C3", c3)
# component.add_subcomponent("C4", c4)

# component.add_bulk(
#     "bulk_cube", Cube(component._size, center=False), label="default"
# )

# # Mesh the component
# component.preview()


# ################ 4 Test Routing ##################
# device_size = (150, 150, 100)
# device_position = (0, 0, 0)
# device = Device.with_visitech_1x("TestDevice", device_position, layers=250, layer_size=0.01)

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
# # r.route_with_fractional_path(
# #     c2.P_OUT,
# #     c1.F_IN,
# #     [(0, -1, 0), (1, 0, 0), (0, 0, 2), (0, 2, 0), (0, 0, -1)],
# #     label="autopath",
# # )
# # r.route_with_polychannel(
# #     c2.P_OUT,
# #     c1.F_IN,
# #     [
# #         PolychannelShape("sphere", position=(0, 20, 0), size=chan_size),
# #         PolychannelShape(position=(-33, 0, 0)),
# #         PolychannelShape(position=(0, 0, -30)),
# #         PolychannelShape(position=(0, -41, 0)),
# #     ],
# #     label="autopath",
# # )
# r.finalize_routes()

# # IMPORTANT: If you want to see inside the inverted device, you need to create you bulk shape last
# bulk_cube = Cube(device_size, center=False)
# bulk_cube.translate(device_position)
# device.add_bulk("bulkcube", bulk_cube, label="device")

# # Mesh the component
# device.preview()
# # device.render()

# ############## 6 Create serpentine channel ##################
# component = Component(
#     size=(2560, 1600, 20), position=(0, 0, 0), px_size=0.0076, layer_size=0.01
# )
# chan_size = (8, 8, 6)
# # Add label
# component.add_label("default", Color.from_rgba((0, 255, 0, 127)))
# # Add a shape
# component.add_bulk(
#     "polychannel",
#     Polychannel(
#         [
#             PolychannelShape("cube", position=(0, 0, 0), size=(8, 8, 6)),
#             PolychannelShape(position=(0, 0, 16), corner_radius=8),
#             PolychannelShape(position=(100, 0, 0)),
#             PolychannelShape(position=(0, 16, 0)),
#             PolychannelShape(position=(-100, 0, 0)),
#             PolychannelShape(position=(0, 16, 0)),
#             PolychannelShape(position=(100, 0, 0)),
#             PolychannelShape(position=(0, 16, 0)),
#             PolychannelShape(position=(-100, 0, 0)),
#             PolychannelShape(position=(0, 16, 0)),
#             PolychannelShape(position=(100, 0, 0)),
#             PolychannelShape(position=(0, 0, -16), corner_radius=0),
#         ]
#     ),
#     label="default",
# )

# # Mesh the component
# component.preview()
