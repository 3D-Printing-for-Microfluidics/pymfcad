import inspect
from pymfd import (
    set_fn,
    Visitech_LRS10_Device,
    Component,
    VariableLayerThicknessComponent,
    Port,
    Color,
    PolychannelShape,
)

set_fn(100)


class MembraneValve6px(VariableLayerThicknessComponent):
    def __init__(self):
        frame = inspect.currentframe()
        args, _, _, values = inspect.getargvalues(frame)
        self.init_args = [values[arg] for arg in args if arg != "self"]
        self.init_kwargs = {arg: values[arg] for arg in args if arg != "self"}
        super().__init__(
            size=(18, 18, 13),
            position=(0, 0, 0),
            px_size=0.0076,
            layer_sizes=[
                (7, 0.01),
                (1, 0.008),
                (1, 0.004),
                (1, 0.008),
                (3, 0.01),
            ],
        )
        # all z coordinates/sizes are in units of the greatest common denominator of the layer sizes (0.002 mm in this case)
        # the sum of the layer sizes should be an integer multiple of the parent component's layer size (0.01 mm in this case)

        self.add_label("default", Color.from_name("aqua", 127))
        self.add_label("pneumatic", Color.from_name("blue", 127))
        self.add_label("fluidic", Color.from_name("red", 127))

        self.add_shape(
            "fluidic_channel",
            self.make_polychannel(
                [
                    PolychannelShape("cube", position=(0, 9, 12), size=(0, 6, 25)),
                    PolychannelShape(position=(9, 0, 0), size=(2, 6, 25)),
                    PolychannelShape(position=(0, 0, 0), size=(2, 2, 25)),
                    PolychannelShape(position=(0, 0, 18), size=(2, 2, 0)),
                ],
            ),
            label="fluidic",
        )

        self.add_shape(
            "fluidic_channel2",
            self.make_polychannel(
                [
                    PolychannelShape("cube", position=(9, 9, 32), size=(0, 6, 5)),
                    PolychannelShape(position=(3, 0, 0), size=(0, 6, 5)),
                    PolychannelShape(position=(0, 0, 0), size=(0, 0, 0)),
                    PolychannelShape(position=(0, 0, -10), size=(0, 0, 0)),
                    PolychannelShape(position=(0, 0, 0), size=(0, 6, 25)),
                    PolychannelShape(position=(6, 0, 0), size=(0, 6, 25)),
                ],
            ),
            label="fluidic",
        )

        self.add_shape(
            "fluidic_chamber",
            self.make_cylinder(h=9, r=3, center_xy=True).translate((9, 9, 30)),
            label="fluidic",
        )
        self.add_shape(
            "pneumatic_chamber",
            self.make_cylinder(h=19, r=3, center_xy=True).translate((9, 9, 41)),
            label="pneumatic",
        )

        self.add_bulk_shape(
            "bulk_cube",
            self.make_cube((18, 18, 65), center=False),
            label="default",
        )


# class SqueezeValve2px(Component):
#     def __init__(self):
#         frame = inspect.currentframe()
#         args, _, _, values = inspect.getargvalues(frame)
#         self.init_args = [values[arg] for arg in args if arg != "self"]
#         self.init_kwargs = {arg: values[arg] for arg in args if arg != "self"}

#         super().__init__(
#             size=(20, 20, 20), position=(0, 0, 0), px_size=0.0076, layer_size=0.01
#         )  # px_size=1.0, layer_size=1.0)


device = Visitech_LRS10_Device("TestDevice", (0, 0, 0), layers=25, layer_size=0.01)
device.add_label("device", Color.from_rgba((0, 255, 255, 127)))
v = MembraneValve6px()
device.add_subcomponent(f"valve", v)

bulk_cube = device.make_cube(device._size, center=False)
bulk_cube.translate(device._position)
device.add_bulk_shape("bulk_cube", bulk_cube, label="device")

device.preview(render_bulk=False, do_bulk_difference=False, wireframe=False)

from pymfd.slicer import Slicer

slicer = Slicer(
    device=device,
    settings={},
    filename="test_slicer",
)
slicer.make_print_file()
