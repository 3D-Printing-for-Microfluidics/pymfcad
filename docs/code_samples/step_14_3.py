from pymfcad import (
    Color,
    Component,
    Cube,
    Cylinder,
    ExposureSettings,
    MembraneSettings,
    Port,
)


class Valve20px(Component):
    def __init__(self, quiet: bool = False):

        super().__init__(
            size=(36, 36, 24),
            px_size=0.0076,
            layer_size=0.01,
            quiet=quiet,
        )

        self.add_label("device", Color.from_name("cyan", 127))
        self.add_label("pneumatic", Color.from_name("red", 255))
        self.add_label("fluidic", Color.from_name("blue", 255))
        self.add_label("membrane", Color.from_name("green", 255))
        self.add_label("region_membrane", Color.from_name("violet", 127))
        self.add_label("region_exposure", Color.from_name("gold", 127))

        self.add_bulk("BulkShape", Cube((36, 36, 24), center=False), label="device")

        self.add_void(
            "FluidicChamber",
            Cylinder(height=2, radius=10, center_z=False).translate((18, 18, 4)),
            label="fluidic",
        )
        self.add_void(
            "FluidicInput",
            Cube((6, 6, 4), center=False).translate((15, 15, 0)),
            label="fluidic",
        )
        self.add_void(
            "FluidicOutput",
            Cube((8, 10, 6), center=False).translate((14, 26, 0)),
            label="fluidic",
        )

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

        membrane_region = Cylinder(height=1, radius=10, center_z=False).translate(
            (18, 18, 6)
        )
        self.add_regional_settings(
            name="membrane_layer",
            shape=membrane_region,
            settings=MembraneSettings(
                ExposureSettings(
                    bulk_exposure_multiplier=0.5,
                    relative_focus_position=50,
                ),
                max_membrane_thickness_um=20,
                dilation_px=2,
            ),
            label="region_membrane",
        )

        exposure_block = Cube((8, 4, 4), center=False).translate((14, 22, 0))
        self.add_regional_settings(
            name="fluidic_block",
            shape=exposure_block,
            settings=ExposureSettings(bulk_exposure_multiplier=2.0),
            label="region_exposure",
        )


if __name__ == "__main__":
    Valve20px().preview()
