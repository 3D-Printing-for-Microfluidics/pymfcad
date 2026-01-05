import inspect
import tracemalloc

tracemalloc.start()
from pymfd.component_library import Pinhole

from pymfd import *

set_fn(50)


class Valve20px(VariableLayerThicknessComponent):
    def __init__(self):
        # Setup initial args/kwargs
        frame = inspect.currentframe()
        args, _, _, values = inspect.getargvalues(frame)
        self.init_args = [values[arg] for arg in args if arg != "self"]
        self.init_kwargs = {arg: values[arg] for arg in args if arg != "self"}
        super().__init__(
            size=(36, 36, 24),
            position=(0, 0, 0),
            px_size=0.0076,
            layer_sizes=[(6, 0.01), (2, 0.005), (16, 0.01)],
        )

        # Setup labels
        self.add_label("device", Color.from_name("cyan", 255))
        self.add_label("pneumatic", Color.from_name("red", 255))
        self.add_label("fluidic", Color.from_name("blue", 255))
        self.add_label("membrane", Color.from_name("green", 128))
        self.add_label("slow", Color.from_name("pink", 128))
        self.add_label("extra", Color.from_name("gray", 128))

        # Add ports
        self.add_port(
            "F_IN",
            Port(Port.PortType.IN, (15, 15, 0), (6, 6, 8), Port.SurfaceNormal.NEG_Z),
        )
        self.add_port(
            "F_OUT",
            Port(Port.PortType.OUT, (36, 14, 0), (8, 8, 12), Port.SurfaceNormal.POS_X),
        )
        self.add_port(
            "P_IN",
            Port(Port.PortType.INOUT, (14, 0, 24), (8, 8, 12), Port.SurfaceNormal.NEG_Y),
        )
        self.add_port(
            "P_OUT",
            Port(Port.PortType.INOUT, (14, 36, 24), (8, 8, 12), Port.SurfaceNormal.POS_Y),
        )

        # Build void shapes
        fluidics = Cylinder(height=4, radius=10, center_z=False).translate((18, 18, 8))
        fluidics += Cube((4, 4, 8), center=False).translate((16, 16, 0))
        fluidics += Cube((10, 8, 12), center=False).translate((26, 14, 0))
        self.add_void("FluidicShapes", fluidics, label="fluidic")

        pneumatics = Cylinder(height=22, radius=10, center_z=False).translate(
            (18, 18, 14)
        )
        pneumatics += Cube((8, 10, 12), center=False).translate((14, 0, 24))
        pneumatics += Cube((8, 10, 12), center=False).translate((14, 26, 24))
        self.add_void("PneumaticShapes", pneumatics, label="pneumatic")

        # Add regional settings
        self.add_regional_settings(
            "MembraneExposure",
            Cylinder(height=2, radius=10, center_z=False).translate((18, 18, 12)),
            MembraneSettings(
                max_membrane_thickness_um=20,
                exposure_time=500,
                defocus_um=50,
                dilation_px=2,
            ),
            label="membrane",
        )

        self.add_regional_settings(
            "SlowRegion",
            Cylinder(height=20, radius=10, center_z=False).translate((18, 18, 12)),
            PositionSettings(
                up_speed=5.0, up_acceleration=5.0, down_speed=5.0, down_acceleration=5.0
            ),
            label="slow",
        )

        self.add_regional_settings(
            "SecondaryDose",
            Cube((8, 8, 8), center=False).translate((14, 14, 0)),
            SecondaryDoseSettings(
                edge_exposure_time=250.0,
                edge_erosion_px=2,
            ),
            label="extra",
        )

        # Build bulk shape
        self.add_bulk_shape("BulkShape", Cube((36, 36, 48), center=False), label="device")


# Valve20px().preview()


class DC(VariableLayerThicknessComponent):
    def __init__(self):
        # Setup initial args/kwargs
        frame = inspect.currentframe()
        args, _, _, values = inspect.getargvalues(frame)
        self.init_args = [values[arg] for arg in args if arg != "self"]
        self.init_kwargs = {arg: values[arg] for arg in args if arg != "self"}
        super().__init__(
            size=(36, 36, 24),
            position=(0, 0, 0),
            px_size=0.0076,
            layer_sizes=[(6, 0.01), (2, 0.005), (16, 0.01)],
        )

        # Setup labels
        self.add_label("device", Color.from_name("cyan", 255))
        self.add_label("pneumatic", Color.from_name("red", 255))
        self.add_label("fluidic", Color.from_name("blue", 255))
        self.add_label("membrane", Color.from_name("green", 128))
        self.add_label("slow", Color.from_name("aqua", 128))

        # Add ports
        self.add_port(
            "F_IN",
            Port(Port.PortType.IN, (0, 14, 0), (8, 8, 12), Port.SurfaceNormal.NEG_X),
        )
        self.add_port(
            "F_OUT",
            Port(Port.PortType.OUT, (36, 14, 0), (8, 8, 12), Port.SurfaceNormal.POS_X),
        )
        self.add_port(
            "P_IN",
            Port(Port.PortType.INOUT, (14, 0, 24), (8, 8, 12), Port.SurfaceNormal.NEG_Y),
        )
        self.add_port(
            "P_OUT",
            Port(Port.PortType.INOUT, (14, 36, 24), (8, 8, 12), Port.SurfaceNormal.POS_Y),
        )

        # Build void shapes
        fluidics = Cylinder(height=4, radius=10, center_z=False).translate((18, 18, 8))
        fluidics += Cube((10, 8, 12), center=False).translate((0, 14, 0))
        fluidics += Cube((10, 8, 12), center=False).translate((26, 14, 0))
        self.add_void("FluidicShapes", fluidics, label="fluidic")

        pneumatics = Cylinder(height=22, radius=10, center_z=False).translate(
            (18, 18, 14)
        )
        pneumatics += Cube((8, 10, 12), center=False).translate((14, 0, 24))
        pneumatics += Cube((8, 10, 12), center=False).translate((14, 26, 24))
        self.add_void("PneumaticShapes", pneumatics, label="pneumatic")

        # Add regional settings
        self.add_regional_settings(
            "MembraneExposure",
            Cylinder(height=2, radius=10, center_z=False).translate((18, 18, 12)),
            MembraneSettings(
                max_membrane_thickness_um=20,
                exposure_time=500,
                defocus_um=50,
                dilation_px=2,
            ),
            label="membrane",
        )

        self.add_regional_settings(
            "SlowRegion",
            Cylinder(height=20, radius=10, center_z=False).translate((18, 18, 12)),
            PositionSettings(
                up_speed=5.0, up_acceleration=5.0, down_speed=5.0, down_acceleration=5.0
            ),
            label="slow",
        )

        # Build bulk shape
        self.add_bulk_shape("BulkShape", Cube((36, 36, 48), center=False), label="device")


# DC().preview()


class Pump(Component):
    def __init__(self):
        # Setup initial args/kwargs
        frame = inspect.currentframe()
        args, _, _, values = inspect.getargvalues(frame)
        self.init_args = [values[arg] for arg in args if arg != "self"]
        self.init_kwargs = {arg: values[arg] for arg in args if arg != "self"}
        super().__init__(
            size=(125, 36, 36),
            position=(0, 0, 0),
            px_size=0.0076,
            layer_size=0.01,
        )

        # Setup labels
        self.add_label("device", Color.from_name("cyan", 255))
        self.add_label("pneumatic", Color.from_name("red", 255))
        self.add_label("fluidic", Color.from_name("blue", 255))
        self.add_label("membrane", Color.from_name("green", 128))

        # Add ports
        self.add_port(
            "F_IN",
            Port(Port.PortType.IN, (0, 14, 6), (8, 8, 6), Port.SurfaceNormal.NEG_X),
        )
        self.add_port(
            "F_OUT",
            Port(Port.PortType.OUT, (125, 14, 12), (8, 8, 6), Port.SurfaceNormal.POS_X),
        )
        self.add_port(
            "P1_IN",
            Port(Port.PortType.INOUT, (14, 0, 24), (8, 8, 6), Port.SurfaceNormal.NEG_Y),
        )
        self.add_port(
            "P2_IN",
            Port(Port.PortType.INOUT, (59, 0, 24), (8, 8, 6), Port.SurfaceNormal.NEG_Y),
        )
        self.add_port(
            "P3_IN",
            Port(Port.PortType.INOUT, (103, 0, 24), (8, 8, 6), Port.SurfaceNormal.NEG_Y),
        )
        self.add_port(
            "P1_OUT",
            Port(Port.PortType.INOUT, (14, 36, 24), (8, 8, 6), Port.SurfaceNormal.POS_Y),
        )
        self.add_port(
            "P2_OUT",
            Port(Port.PortType.INOUT, (59, 36, 24), (8, 8, 6), Port.SurfaceNormal.POS_Y),
        )
        self.add_port(
            "P3_OUT",
            Port(Port.PortType.INOUT, (103, 36, 24), (8, 8, 6), Port.SurfaceNormal.POS_Y),
        )

        # Build void shapes

        # Add components
        v1 = Valve20px().translate([0, 0, 12])
        dc = DC().translate([45, 0, 12])
        v2 = Valve20px().translate([89, 0, 12])
        self.add_subcomponent("Valve1", v1)
        self.add_subcomponent("DC", dc)
        self.add_subcomponent("Valve2", v2)

        # Route channels
        r = Router(component=self, channel_size=(8, 8, 6), channel_margin=(8, 8, 6))
        r.autoroute_channel(self.F_IN, v1.F_IN, label="fluidic")
        r.autoroute_channel(v1.F_OUT, dc.F_IN, label="fluidic")
        r.autoroute_channel(dc.F_OUT, v2.F_IN, label="fluidic")
        r.route()

        # Mark unrouted ports as connected
        v1.connect_port(v1.P_IN.get_name())
        v1.connect_port(v1.P_OUT.get_name())
        dc.connect_port(dc.P_IN.get_name())
        dc.connect_port(dc.P_OUT.get_name())
        v2.connect_port(v2.P_IN.get_name())
        v2.connect_port(v2.P_OUT.get_name())
        v2.connect_port(v2.F_OUT.get_name())

        # Build bulk shape
        self.add_bulk_shape(
            "BulkShape", Cube((125, 36, 36), center=False), label="device"
        )


# Pump().rotate(270, in_place=True).mirror(
#     mirror_x=False, mirror_y=False, in_place=True
# ).preview()


class TJunction(Component):
    def __init__(self):
        frame = inspect.currentframe()
        args, _, _, values = inspect.getargvalues(frame)
        self.init_args = [values[arg] for arg in args if arg != "self"]
        self.init_kwargs = {arg: values[arg] for arg in args if arg != "self"}

        super().__init__(
            size=(24, 24, 18), position=(0, 0, 0), px_size=0.0076, layer_size=0.01
        )

        # Setup labels
        self.add_label("device", Color.from_name("cyan", 255))
        self.add_label("fluidic", Color.from_name("blue", 255))

        # Add ports
        self.add_port(
            "F_IN1",
            Port(Port.PortType.IN, (0, 8, 6), (8, 8, 6), Port.SurfaceNormal.NEG_X),
        )
        self.add_port(
            "F_IN2",
            Port(Port.PortType.IN, (24, 8, 6), (8, 8, 6), Port.SurfaceNormal.POS_X),
        )
        self.add_port(
            "F_OUT",
            Port(Port.PortType.OUT, (8, 24, 6), (8, 8, 6), Port.SurfaceNormal.POS_Y),
        )

        # Route channels
        r = Router(component=self, channel_size=(8, 8, 6), channel_margin=(8, 8, 6))
        r.route_with_fractional_path(
            self.F_IN2, self.F_OUT, [(1, 0, 1), (0, 1, 0)], label="fluidic"
        )
        r.route_with_fractional_path(
            self.F_IN1, self.F_OUT, [(1, 0, 1), (0, 1, 0)], label="fluidic"
        )
        r.route()

        # Build bulk shape
        self.add_bulk_shape("BulkShape", Cube((24, 24, 18), center=False), label="device")


# TJunction().preview()


class ViewingRegion(Component):
    def __init__(self):
        frame = inspect.currentframe()
        args, _, _, values = inspect.getargvalues(frame)
        self.init_args = [values[arg] for arg in args if arg != "self"]
        self.init_kwargs = {arg: values[arg] for arg in args if arg != "self"}

        super().__init__(
            size=(48, 48, 18), position=(0, 0, 0), px_size=0.0076, layer_size=0.01
        )

        # Setup labels
        self.add_label("device", Color.from_name("cyan", 255))
        self.add_label("fluidic", Color.from_name("blue", 255))

        # Add ports
        self.add_port(
            "F_IN",
            Port(Port.PortType.IN, (0, 20, 6), (8, 8, 6), Port.SurfaceNormal.NEG_X),
        )
        self.add_port(
            "F_OUT",
            Port(Port.PortType.OUT, (48, 20, 6), (8, 8, 6), Port.SurfaceNormal.POS_X),
        )

        # Route channels
        r = Router(component=self, channel_size=(8, 8, 6), channel_margin=(8, 8, 6))
        r.route_with_polychannel(
            self.F_IN,
            self.F_OUT,
            [
                PolychannelShape("cube", (12, 0, 0), (0, 36, 6)),
                PolychannelShape("cube", (24, 0, 0), (0, 36, 6)),
            ],
            label="fluidic",
        )
        r.route()

        # Build bulk shape
        self.add_bulk_shape("BulkShape", Cube((48, 48, 18), center=False), label="device")


# ViewingRegion().preview()


class HARChannel(Component):
    def __init__(self):
        frame = inspect.currentframe()
        args, _, _, values = inspect.getargvalues(frame)
        self.init_args = [values[arg] for arg in args if arg != "self"]
        self.init_kwargs = {arg: values[arg] for arg in args if arg != "self"}

        super().__init__(
            size=(72, 24, 36), position=(0, 0, 0), px_size=0.0076, layer_size=0.01
        )

        # Setup labels
        self.add_label("device", Color.from_name("cyan", 255))
        self.add_label("fluidic", Color.from_name("blue", 255))

        # Add ports
        self.add_port(
            "F_IN",
            Port(Port.PortType.IN, (0, 8, 15), (8, 8, 6), Port.SurfaceNormal.NEG_X),
        )
        self.add_port(
            "F_OUT",
            Port(Port.PortType.OUT, (72, 8, 15), (8, 8, 6), Port.SurfaceNormal.POS_X),
        )

        # Route channels
        r = Router(component=self, channel_size=(8, 8, 6), channel_margin=(8, 8, 6))
        r.route_with_polychannel(
            self.F_IN,
            self.F_OUT,
            [
                PolychannelShape("cube", (12, 0, 0), (0, 2, 24)),
                PolychannelShape("cube", (48, 0, 0), (0, 2, 24)),
            ],
            label="fluidic",
        )
        r.route()

        # Build bulk shape
        self.add_bulk_shape("BulkShape", Cube((72, 24, 36), center=False), label="device")


# HARChannel().preview()


class SerpentineChannel(Component):
    def __init__(
        self,
        channel_size: tuple[int, int, int] = (8, 8, 6),
        width: int = 4,
        turns: int = 4,
        layers: int = 3,
    ):
        frame = inspect.currentframe()
        args, _, _, values = inspect.getargvalues(frame)
        self.init_args = [values[arg] for arg in args if arg != "self"]
        self.init_kwargs = {arg: values[arg] for arg in args if arg != "self"}

        super().__init__(
            size=(
                (2 * turns + 4) * channel_size[0],
                width,
                (2 * layers + 1) * channel_size[2],
            ),
            position=(0, 0, 0),
            px_size=0.0076,
            layer_size=0.01,
        )

        # Setup labels
        self.add_label("device", Color.from_name("cyan", 255))
        self.add_label("fluidic", Color.from_name("blue", 255))

        # Add ports
        self.add_port(
            "F_IN",
            Port(
                Port.PortType.IN,
                (0, width / 2 - channel_size[1] / 2, channel_size[2]),
                channel_size,
                Port.SurfaceNormal.NEG_X,
            ),
        )
        self.add_port(
            "F_OUT",
            Port(
                Port.PortType.OUT,
                (
                    (2 * turns + 4) * channel_size[0] if layers % 2 else 0,
                    width / 2 - channel_size[1] / 2,
                    (2 * layers - 1) * channel_size[2],
                ),
                channel_size,
                Port.SurfaceNormal.POS_X if layers % 2 else Port.SurfaceNormal.NEG_X,
            ),
        )

        r = Router(component=self, channel_size=channel_size, channel_margin=channel_size)
        shape_list = [
            PolychannelShape(
                shape_type="cube",
                size=channel_size,
                position=(2 * channel_size[0], 0, 0),
                corner_radius=channel_size[0],
            ),
        ]
        for i in range(layers):
            dir = 1 if i % 2 == 0 else -1
            for j in range(turns):
                y_pos = width / 2 - channel_size[1]
                if j % 2 == 0:
                    y_pos = -y_pos
                shape_list.extend(
                    [
                        PolychannelShape(
                            position=(0, y_pos, 0),
                        ),
                        PolychannelShape(
                            position=(dir * 2 * channel_size[0], 0, 0),
                        ),
                        PolychannelShape(
                            position=(0, -y_pos, 0),
                        ),
                    ]
                )
            if i < layers - 1:
                shape_list.append(
                    PolychannelShape(
                        position=(0, 0, 2 * channel_size[2]),
                    )
                )
        r.route_with_polychannel(
            self.F_IN,
            self.F_OUT,
            shape_list,
            "fluidic",
        )
        r.route()

        # Build bulk shape
        self.add_bulk_shape(
            "BulkShape",
            Cube(
                (
                    (2 * turns + 4) * channel_size[0],
                    width,
                    (2 * layers + 1) * channel_size[2],
                ),
                center=False,
            ),
            label="device",
        )


# SerpentineChannel(width=256, turns=10, layers=3).preview()

# Pinhole(channel_size=(8, 8, 6)).preview()


dev = Visitech_LRS10_Device(
    "FullTestDevice", position=(0, 0, 0), layers=250, layer_size=0.01
)

dev.add_label("device", Color.from_name("aqua", 100))
dev.add_label("edge", Color.from_name("red", 100))
dev.add_label("control", Color.from_name("fuchsia", 255))
dev.add_label("fluidic", Color.from_name("aqua", 255))

device_width = 1600
device_length = 2560
pinhole_width = 110
pinhole_height = 144
pinhole_length = 250
pump_width = 36
mixer_width = 24
view_width = 48
harc_width = 24
harc_height = 36
serp_width = 1200
f_in1 = Pinhole(channel_size=(8, 8, 6)).translate((0, 500, 75))
f_in2 = Pinhole(channel_size=(8, 8, 6)).translate(
    (0, device_width - 500 - pinhole_width, 75)
)
f_out = (
    Pinhole(channel_size=(8, 8, 6))
    .rotate(180, in_place=True)
    .translate((device_length - pinhole_length, device_width / 2 - pinhole_width / 2, 75))
)
v1_control = (
    Pinhole(channel_size=(8, 8, 6)).rotate(90, in_place=True).translate((300, 0, 75))
)
v1_flush = (
    Pinhole(channel_size=(8, 8, 6))
    .rotate(270, in_place=True)
    .translate((300, device_width - pinhole_length, 75))
)
dc_control = (
    Pinhole(channel_size=(8, 8, 6)).rotate(90, in_place=True).translate((600, 0, 75))
)
dc_flush = (
    Pinhole(channel_size=(8, 8, 6))
    .rotate(270, in_place=True)
    .translate((600, device_width - pinhole_length, 75))
)
v2_control = (
    Pinhole(channel_size=(8, 8, 6)).rotate(90, in_place=True).translate((900, 0, 75))
)
v2_flush = (
    Pinhole(channel_size=(8, 8, 6))
    .rotate(270, in_place=True)
    .translate((900, device_width - pinhole_length, 75))
)
pump1 = Pump().translate((600, 700, 150))
pump2 = Pump().translate((600, device_width - 700 - pump_width, 150))
mixer = (
    TJunction()
    .rotate(270, in_place=True)
    .translate((700, device_width / 2 - mixer_width / 2, 150))
)
view1 = ViewingRegion().translate((800, device_width / 2 - view_width / 2, 150))
harc = HARChannel().translate(
    (900, device_width / 2 - harc_width / 2, 150 - harc_height / 2 + 9)
)
serp = SerpentineChannel(width=serp_width, turns=40, layers=15).translate(
    (1200, device_width / 2 - serp_width / 2, 25)
)
view2 = ViewingRegion().translate((2000, device_width / 2 - view_width / 2, 150))

dev.add_subcomponent("F_IN1", f_in1)
dev.add_subcomponent("F_IN2", f_in2)
dev.add_subcomponent("F_OUT", f_out)
dev.add_subcomponent("V1_CONT", v1_control)
dev.add_subcomponent("V1_FLUSH", v1_flush)
dev.add_subcomponent("DC_CONT", dc_control)
dev.add_subcomponent("DC_FLUSH", dc_flush)
dev.add_subcomponent("V2_CONT", v2_control)
dev.add_subcomponent("V2_FLUSH", v2_flush)
dev.add_subcomponent("Pump1", pump1)
dev.add_subcomponent("Pump2", pump2)
dev.add_subcomponent("TMixer", mixer)
dev.add_subcomponent("ViewingRegion1", view1)
dev.add_subcomponent("HARChannel", harc)
dev.add_subcomponent("SerpentineChannel", serp)
dev.add_subcomponent("ViewingRegion2", view2)

r = Router(component=dev, channel_size=(8, 8, 6), channel_margin=(8, 8, 6))

# Fluidic lines
r.autoroute_channel(f_in1.port, pump1.F_IN, label="fluidic")
r.autoroute_channel(f_in2.port, pump2.F_IN, label="fluidic")
r.autoroute_channel(pump1.F_OUT, mixer.F_IN2, label="fluidic")
r.autoroute_channel(pump2.F_OUT, mixer.F_IN1, label="fluidic")
r.autoroute_channel(mixer.F_OUT, view1.F_IN, label="fluidic")
r.autoroute_channel(view1.F_OUT, harc.F_IN, label="fluidic")
r.autoroute_channel(harc.F_OUT, serp.F_IN, label="fluidic")
r.route_with_polychannel(
    serp.F_OUT,
    view2.F_IN,
    [
        BezierCurveShape(
            position=(120, 0, -43),
            control_points=[
                (40, 0, 0),
                (80, 0, -43),
            ],
            bezier_segments=20,
            absolute_position=False,
        ),
    ],
    label="fluidic",
)
r.route_with_polychannel(
    view2.F_OUT,
    f_out.port,
    [
        BezierCurveShape(
            position=(254, 17, -29),
            control_points=[(0, 0, 0)],
            bezier_segments=20,
            absolute_position=False,
        ),
    ],
    label="fluidic",
)

# Control and flush lines
r.autoroute_channel(
    v1_control.port, pump1.P1_IN, label="control", direction_preference=("Z", "Y", "X")
)
r.autoroute_channel(pump1.P1_OUT, pump2.P1_IN, label="control")
r.autoroute_channel(
    pump2.P1_OUT, v1_flush.port, label="control", direction_preference=("X", "Y", "Z")
)
r.autoroute_channel(
    dc_control.port, pump1.P2_IN, label="control", direction_preference=("Z", "Y", "X")
)
r.autoroute_channel(pump1.P2_OUT, pump2.P2_IN, label="control")
r.autoroute_channel(
    pump2.P2_OUT, dc_flush.port, label="control", direction_preference=("X", "Y", "Z")
)
r.autoroute_channel(
    v2_control.port, pump1.P3_IN, label="control", direction_preference=("Z", "Y", "X")
)
r.autoroute_channel(pump1.P3_OUT, pump2.P3_IN, label="control")
r.autoroute_channel(
    pump2.P3_OUT, v2_flush.port, label="control", direction_preference=("X", "Y", "Z")
)

# Finalize routing
r.route()

# Color channels
dev.relabel_labels(["pneumatic"], "control")
dev.relabel_labels(["fluidic"], "fluidic")
dev.relabel_labels(["bulk"], "device")
dev.relabel_labels(
    [
        "V1_CONT.void",
        "V1_FLUSH.void",
        "DC_CONT.void",
        "DC_FLUSH.void",
        "V2_CONT.void",
        "V2_FLUSH.void",
    ],
    "control",
)
dev.relabel_labels(
    [
        "F_IN1.void",
        "F_IN2.void",
        "F_OUT.void",
    ],
    "fluidic",
)
# dev.relabel_subcomponents(
#     [v1_control, v1_flush, dc_control, dc_flush, v2_control, v2_flush], "control"
# )
# dev.relabel_subcomponents(
#     [f_in1, f_in2, mixer, view1, harc, serp, view2, f_out], "fluidic"
# )

# Add regional settings
dev.add_regional_settings(
    "EdgeExposure",
    Cube((2560, 1600, 250), center=False).translate((0, 0, 0))
    - Cube((2460, 1500, 250), center=False).translate((50, 50, 0)),
    ExposureSettings(exposure_time=1000),
    label="edge",
)

dev.set_burn_in_exposure([10000, 5000, 2500])

dev.add_bulk_shape(
    "BulkShape",
    Cube((2560, 1600, 250), center=False).translate((0, 0, 0)),
    label="device",
)

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics("lineno")
print("[ Top 10 ]")
for stat in top_stats[:10]:
    print(stat)

dev.preview()

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics("lineno")
print("[ Top 10 ]")
for stat in top_stats[:10]:
    print(stat)

settings = Settings(
    # user="Test User",
    # purpose="Test Design",
    # description="This is a test design for the pymfd library.",
    printer=Printer(
        name="HR3v3",
        light_engines=[
            LightEngine(
                px_size=0.0076,
                px_count=(2560, 1600),
                wavelengths=[365],
                grayscale_available=[False],
            )
        ],
        vaccum_available=False,
    ),
    resin=ResinType(),
    print_under_vacuum=True,
    default_position_settings=PositionSettings(
        # distance_up=1.0,
        # initial_wait=0.0,
        # up_speed=25.0,
        # up_acceleration=50.0,
        # up_wait=0.0,
        # down_speed=20.0,
        # down_acceleration=50.0,
        # force_squeeze=False,
        # squeeze_count=0,
        # squeeze_force=0.0,
        # squeeze_wait=0.0,
        # final_wait=0.0,
    ),
    default_exposure_settings=ExposureSettings(
        grayscale_correction=True,
        # exposure_time=300.0,
        # power_setting=100,
        # relative_focus_position=0.0,
        # wait_before_exposure=0.0,
        # wait_after_exposure=0.0,
    ),
)

slicer = Slicer(
    device=dev,
    settings=settings,
    filename="test_slicer",
    minimize_file=True,
    zip_output=False,
)
slicer.make_print_file()
