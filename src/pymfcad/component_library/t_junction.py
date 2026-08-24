from pymfcad import Color, Component, Cube, Port, Router


class TJunction(Component):
    """
    Simple T Junction with configurable channel size and margin.

    Ports:

    - F_IN1:
        - Type: IN
        - Size: channel_size
        - Normal: NEG_X
    - F_IN2:
        - Type: IN
        - Size: channel_size
        - Normal: POS_X
    - F_OUT:
        - Type: OUT
        - Size: channel_size
        - Normal: POS_Y
    """

    def __init__(
        self, channel_size=(8, 8, 6), channel_margin=(8, 8, 6), quiet: bool = False
    ):
        """Initialize a T Junction component."""

        super().__init__(
            size=(
                channel_size[0] + channel_margin[0] * 2,
                channel_size[1] + channel_margin[1] * 2,
                channel_size[2] + channel_margin[2] * 2,
            ),
            px_size=0.0076,
            layer_size=0.01,
            quiet=quiet,
        )

        # Setup labels
        self.add_label("device", Color.from_name("cyan", 255))
        self.add_label("fluidic", Color.from_name("blue", 255))

        # Add ports
        self.add_port(
            "F_IN1",
            Port(
                Port.PortType.IN,
                (0, channel_margin[1], channel_margin[2]),
                channel_size,
                Port.SurfaceNormal.NEG_X,
            ),
        )
        self.add_port(
            "F_IN2",
            Port(
                Port.PortType.IN,
                (
                    channel_size[0] + channel_margin[0] * 2,
                    channel_margin[1],
                    channel_margin[2],
                ),
                channel_size,
                Port.SurfaceNormal.POS_X,
            ),
        )
        self.add_port(
            "F_OUT",
            Port(
                Port.PortType.OUT,
                (
                    channel_margin[0],
                    channel_size[1] + channel_margin[1] * 2,
                    channel_margin[2],
                ),
                channel_size,
                Port.SurfaceNormal.POS_Y,
            ),
        )

        # Route channels
        r = Router(
            component=self, channel_size=channel_size, channel_margin=channel_margin
        )
        r.route_with_fractional_path(
            self.F_IN2, self.F_OUT, [(1, 0, 1), (0, 1, 0)], label="fluidic"
        )
        r.route_with_fractional_path(
            self.F_IN1, self.F_OUT, [(1, 0, 1), (0, 1, 0)], label="fluidic"
        )
        r.finalize_routes()

        # Build bulk shape
        self.add_bulk("BulkShape", Cube(self._size, center=False), label="device")
