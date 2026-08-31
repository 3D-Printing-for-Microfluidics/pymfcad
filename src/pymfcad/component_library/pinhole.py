from pymfcad import Color, Component, Cube, Polychannel, PolychannelShape, Port


class Pinhole(Component):
    """
    Simple 144 px pinhole component.

    Ports:

    - port:
        - Type: INOUT
        - Size: (8, 8, 6)
        - Normal: POS_X
    """

    def __init__(
        self, channel_size: tuple[int, int, int] = (8, 8, 6), quiet: bool = False
    ):
        """Initialize a Pinhole component."""
        pinhole_height = 144
        pinhole_width = 110
        pinhole_length = 200
        taper_length = 50
        total_length = pinhole_length + taper_length

        super().__init__(
            size=(total_length, pinhole_height, pinhole_width),
            px_size=0.0076,
            layer_size=0.01,
            quiet=quiet,
        )  # px_size=1.0, layer_size=1.0)

        self.add_label("bulk", Color.from_name("aqua", 255))
        self.add_label("void", Color.from_name("aqua", 255))

        shape = Polychannel(
            [
                PolychannelShape(
                    "sphere",
                    position=(0, pinhole_height / 2, pinhole_width / 2),
                    size=(0, pinhole_height, pinhole_width),
                ),
                PolychannelShape(
                    "sphere",
                    position=(pinhole_length, 0, 0),
                    size=(0, pinhole_height, pinhole_width),
                ),
                PolychannelShape(
                    "cube",
                    position=(taper_length, 0, 0),
                    size=(0, channel_size[1], channel_size[2]),
                ),
            ]
        )

        self.add_void("pinhole", shape, label="void")

        self.add_bulk(
            "BulkShape",
            Cube((total_length, pinhole_height, pinhole_width), center=False),
            label="bulk",
        )

        self.add_port(
            "port",
            Port(
                Port.PortType.INOUT,
                (
                    total_length,
                    (pinhole_height - channel_size[1]) / 2,
                    (pinhole_width - channel_size[2]) / 2,
                ),
                channel_size,
                Port.SurfaceNormal.POS_X,
            ),
        )
