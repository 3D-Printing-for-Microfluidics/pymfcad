import inspect
from .. import Component, Port, Color, Cube


class TestCube(Component):
    """
    ###### Port test cube. Used to test visualization and component geometric transformations.
    """

    def __init__(self):
        frame = inspect.currentframe()
        args, _, _, values = inspect.getargvalues(frame)
        self.init_args = [values[arg] for arg in args if arg != "self"]
        self.init_kwargs = {arg: values[arg] for arg in args if arg != "self"}

        super().__init__(
            size=(30, 30, 15), position=(0, 0, 0), px_size=0.0076, layer_size=0.01
        )  # px_size=1.0, layer_size=1.0)

        self.add_label("cube", Color.from_name("aqua", 255))
        self.add_bulk_shape("cubeshape", Cube((30, 30, 15), center=False), "cube")

        self.add_port(
            "NEG_X_IN",
            Port(Port.PortType.IN, (0, 11, 0), (7, 7, 5), Port.SurfaceNormal.NEG_X),
        )
        self.add_port(
            "NEG_X_OUT",
            Port(Port.PortType.OUT, (0, 11, 5), (7, 7, 5), Port.SurfaceNormal.NEG_X),
        )
        self.add_port(
            "NEG_X_INOUT",
            Port(Port.PortType.INOUT, (0, 11, 10), (7, 7, 5), Port.SurfaceNormal.NEG_X),
        )
        self.add_port(
            "POS_X_IN",
            Port(Port.PortType.IN, (30, 11, 0), (7, 7, 5), Port.SurfaceNormal.POS_X),
        )
        self.add_port(
            "POS_X_OUT",
            Port(Port.PortType.OUT, (30, 11, 5), (7, 7, 5), Port.SurfaceNormal.POS_X),
        )
        self.add_port(
            "POS_X_INOUT",
            Port(Port.PortType.INOUT, (30, 11, 10), (7, 7, 5), Port.SurfaceNormal.POS_X),
        )

        self.add_port(
            "NEG_Y_IN",
            Port(Port.PortType.IN, (11, 0, 0), (7, 7, 5), Port.SurfaceNormal.NEG_Y),
        )
        self.add_port(
            "NEG_Y_OUT",
            Port(Port.PortType.OUT, (11, 0, 5), (7, 7, 5), Port.SurfaceNormal.NEG_Y),
        )
        self.add_port(
            "NEG_Y_INOUT",
            Port(Port.PortType.INOUT, (11, 0, 10), (7, 7, 5), Port.SurfaceNormal.NEG_Y),
        )
        self.add_port(
            "POS_Y_IN",
            Port(Port.PortType.IN, (11, 30, 0), (7, 7, 5), Port.SurfaceNormal.POS_Y),
        )
        self.add_port(
            "POS_Y_OUT",
            Port(Port.PortType.OUT, (11, 30, 5), (7, 7, 5), Port.SurfaceNormal.POS_Y),
        )
        self.add_port(
            "POS_Y_INOUT",
            Port(Port.PortType.INOUT, (11, 30, 10), (7, 7, 5), Port.SurfaceNormal.POS_Y),
        )

        self.add_port(
            "NEG_Z_IN",
            Port(Port.PortType.IN, (0, 0, 0), (7, 7, 5), Port.SurfaceNormal.NEG_Z),
        )
        self.add_port(
            "NEG_Z_OUT",
            Port(Port.PortType.OUT, (7, 7, 0), (7, 7, 5), Port.SurfaceNormal.NEG_Z),
        )
        self.add_port(
            "NEG_Z_INOUT",
            Port(Port.PortType.INOUT, (14, 14, 0), (7, 7, 5), Port.SurfaceNormal.NEG_Z),
        )
        self.add_port(
            "POS_Z_IN",
            Port(Port.PortType.IN, (0, 0, 15), (7, 7, 5), Port.SurfaceNormal.POS_Z),
        )
        self.add_port(
            "POS_Z_OUT",
            Port(Port.PortType.OUT, (7, 7, 15), (7, 7, 5), Port.SurfaceNormal.POS_Z),
        )
        self.add_port(
            "POS_Z_INOUT",
            Port(Port.PortType.INOUT, (14, 14, 15), (7, 7, 5), Port.SurfaceNormal.POS_Z),
        )
