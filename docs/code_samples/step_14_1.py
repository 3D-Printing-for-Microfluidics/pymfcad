import inspect
from pymfcad import Component, Port, Color, Cylinder, Cube


class Valve20px(Component):
    def __init__(self, quiet: bool = False):
        frame = inspect.currentframe()
        args, _, _, values = inspect.getargvalues(frame)
        self.init_args = [values[arg] for arg in args if arg != "self"]
        self.init_kwargs = {arg: values[arg] for arg in args if arg != "self"}

        super().__init__(
            size=(36, 36, 24),
            position=(0, 0, 0),
            px_size=0.0076,
            layer_size=0.01,
            quiet=quiet,
        )

        self.add_label("device", Color.from_name("cyan", 127))
        self.add_label("pneumatic", Color.from_name("red", 255))
        self.add_label("fluidic", Color.from_name("blue", 255))
        self.add_label("membrane", Color.from_name("green", 255))

        self.add_bulk("BulkShape", Cube((36, 36, 24), center=False), label="device")

        fluidics = Cylinder(height=2, radius=10, center_z=False).translate((18, 18, 4))
        fluidics += Cube((6, 6, 4), center=False).translate((15, 15, 0))
        fluidics += Cube((8, 10, 6), center=False).translate((14, 26, 0))
        self.add_void("FluidicShapes", fluidics, label="fluidic")

        pneumatics = Cylinder(height=11, radius=10, center_z=False).translate((18, 18, 7))
        pneumatics += Cube((8, 10, 6), center=False).translate((14, 0, 12))
        pneumatics += Cube((8, 10, 6), center=False).translate((14, 26, 12))
        self.add_void("PneumaticShapes", pneumatics, label="pneumatic")

        self.add_port(
            "F_IN",
            Port(Port.PortType.IN, (15, 15, 0), (6, 6, 4), Port.SurfaceNormal.NEG_Z),
        )
        self.add_port(
            "F_OUT",
            Port(Port.PortType.OUT, (14, 36, 0), (8, 8, 6), Port.SurfaceNormal.POS_Y),
        )
        self.add_port(
            "P_IN",
            Port(Port.PortType.INOUT, (14, 0, 12), (8, 8, 6), Port.SurfaceNormal.NEG_Y),
        )
        self.add_port(
            "P_OUT",
            Port(Port.PortType.INOUT, (14, 36, 12), (8, 8, 6), Port.SurfaceNormal.POS_Y),
        )

        from pymfcad import MembraneSettings
        self.add_label("region_membrane", Color.from_name("violet", 180))

        membrane_region = Cylinder(height=1, radius=10, center_z=False).translate((18, 18, 6))
        self.add_regional_settings(
            name="membrane_layer",
            shape=membrane_region,
            settings=MembraneSettings(
                max_membrane_thickness_um=20,
                bulk_exposure_multiplier=0.5,
                defocus_um=50,
                dilation_px=2,
            ),
            label="region_membrane",
        )

        from pymfcad import ExposureSettings
        self.add_label("region_exposure", Color.from_name("gold", 180))

        exposure_block = Cube((8, 4, 4), center=False).translate((14, 22, 0))
        self.add_regional_settings(
            name="fluidic_block",
            shape=exposure_block,
            settings=ExposureSettings(bulk_exposure_multiplier=0.7),
            label="region_exposure",
        )

        from pymfcad import PositionSettings
        self.add_label("region_position", Color.from_name("magenta", 180))

        position_region = Cylinder(height=12, radius=12, center_z=False).translate((18, 18, 7))
        self.add_regional_settings(
            name="slow_above_membrane",
            shape=position_region,
            settings=PositionSettings(
                up_speed=10.0,
                down_speed=10.0,
                up_acceleration=20.0,
                down_acceleration=20.0,
            ),
            label="region_position",
        )

        from pymfcad import SecondaryDoseSettings
        self.add_label("region_secondary", Color.from_name("cyan", 180))

        secondary_region = Cube((8, 8, 6), center=False).translate((14, 14, 0))
        self.add_regional_settings(
            name="vertical_channel_edges",
            shape=secondary_region,
            settings=SecondaryDoseSettings(
                edge_bulk_exposure_multiplier=0.6,
                edge_erosion_px=1,
                edge_dilation_px=0,
            ),
            label="region_secondary",
        )

if __name__ == "__main__":
    Valve20px().preview()