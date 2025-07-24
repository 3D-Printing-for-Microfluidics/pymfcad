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

from pymfd.slicer import (
    MembraneSettings,
    SecondaryDoseSettings,
    PositionSettings,
    ExposureSettings,
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

        self.add_default_exposure_settings(
            ExposureSettings(
                exposure_time=300,
            )
        )

        self.add_default_position_settings(
            PositionSettings(
                up_acceleration=50.0,
            )
        )

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

        self.add_regional_settings(
            "membrane_settings",
            self.make_cylinder(h=2, r=3, center_xy=True).translate((9, 9, 39)),
            MembraneSettings(
                max_membrane_thickness_um=0.004,
                exposure_time=350,
                dilation_px=2,
                defocus_um=0.0,
            ),
            label="pneumatic",
        )

        self.add_regional_settings(
            "secondary_settings",
            self.make_cube((18, 18, 65), center=False),
            SecondaryDoseSettings(
                edge_exposure_time=250.0,
                edge_erosion_px=2,
                edge_dilation_px=0,
                roof_exposure_time=200.0,
                roof_erosion_px=2,
                roof_layers_above=5,
            ),
            label="pneumatic",
        )

        self.add_regional_settings(
            "exposure_settings",
            self.make_cube((18, 9, 65), center=False),
            ExposureSettings(
                exposure_time=400.0,
            ),
            label="pneumatic",
        )

        self.add_regional_settings(
            "position_settings",
            self.make_cylinder(h=2, r=3, center_xy=True).translate((9, 9, 39)),
            PositionSettings(up_acceleration=2.0),
            label="pneumatic",
        )

        self.add_bulk_shape(
            "bulk_cube",
            self.make_cube((18, 18, 65), center=False),
            label="default",
        )


device = Visitech_LRS10_Device("TestDevice", (0, 0, 0), layers=25, layer_size=0.01)
device.add_label("device", Color.from_rgba((0, 255, 255, 127)))
v = MembraneValve6px().translate((50, 50, 0))
device.add_subcomponent(f"valve", v)

bulk_cube = device.make_cube(device._size, center=False)
bulk_cube.translate(device._position)
device.add_bulk_shape("bulk_cube", bulk_cube, label="device")

device.set_burn_in_exposure([10000, 5000, 2500])

device.preview(render_bulk=False, do_bulk_difference=False, wireframe=False)


from pymfd.slicer import (
    Slicer,
    Settings,
    ResinType,
    Printer,
    LightEngine,
)

settings = Settings(
    user="Test User",
    purpose="Test Design",
    description="This is a test design for the pymfd library.",
    printer=Printer(
        name="HR3v3",
        light_engines=LightEngine(
            px_size=0.0076, px_count=(2560, 1600), wavelengths=[365]
        ),
    ),
    resin=ResinType(
        monomer=[("PEG", 100)],
        uv_absorbers=[("NPS", 2.0)],
        initiators=[("IRG", 1.0)],
        additives=[],
    ),
    print_under_vacuum=False,
    default_position_settings=PositionSettings(
        distance_up=1.0,
        initial_wait=0.0,
        up_speed=25.0,
        up_acceleration=50.0,
        up_wait=0.0,
        down_speed=20.0,
        down_acceleration=50.0,
        force_squeeze=False,
        squeeze_count=0,
        squeeze_force=0.0,
        squeeze_wait=0.0,
        final_wait=0.0,
    ),
    default_exposure_settings=ExposureSettings(
        grayscale_correction=False,
        exposure_time=500.0,
        power_setting=100,
        relative_focus_position=0.0,
        wait_before_exposure=0.0,
        wait_after_exposure=0.0,
    ),
)

slicer = Slicer(
    device=device,
    settings=settings,
    filename="test_slicer",
    minimize_file=True,
    zip_output=False,
)
slicer.make_print_file()
