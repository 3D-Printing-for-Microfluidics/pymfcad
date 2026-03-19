### SERPINTINE CHANNEL COMPONENT

import inspect
from pymfcad import Component, Port, Router, Color, Cube


class SerpentineChannel(Component):
    """
    Simple serpentine channel with two ports.
    """

    def __init__(
        self,
        channel_size=(8, 8, 6),
        channel_margin=(16, 16, 6),
        width=800,
        loops=11,
        layers=5,
        px_size=0.0076,
        layer_size=0.01,
        quiet=False,
    ):
        frame = inspect.currentframe()
        args, _, _, values = inspect.getargvalues(frame)
        self.init_args = [values[arg] for arg in args if arg != "self"]
        self.init_kwargs = {arg: values[arg] for arg in args if arg != "self"}

        length = channel_size[0] * loops + channel_margin[0] * (loops + 1)

        super().__init__(
            size=(length, width, channel_size[2]*layers + channel_margin[2]*(layers + 1)),
            position=(0, 0, 0),
            px_size=px_size,
            layer_size=layer_size,
            quiet=quiet,
        )

        self.add_label("bulk", Color.from_name("aqua", 127))
        self.add_label("void", Color.from_name("red", 255))

        self.add_bulk("bulk_shape", Cube(self._size, center=False), label="bulk")

        self.add_port(
            "inlet",
            Port(
                Port.PortType.IN,
                (0, channel_margin[1], channel_margin[2]),
                channel_size,
                Port.SurfaceNormal.NEG_X,
            ),
        )
        self.add_port(
            "outlet",
            Port(
                Port.PortType.OUT,
                (length, width - 2 * channel_margin[1], layers*(channel_margin[2] + channel_size[2]) - channel_margin[2]),
                channel_size,
                Port.SurfaceNormal.POS_X,
            ),
        )

        # Router builds the void geometry from a path
        router = Router(self, channel_size=channel_size, channel_margin=channel_margin)

        # Simple fractional path: go straight in X, then offset in Y, then finish in X
        # X fractions must sum to 1.0, Y fractions must sum to 1.0, Z fractions to 1.0
        simple_path = [
            (0.6, 0.0, 0.0),  # move mostly along X
            (0.0, 1.0, 0.0),  # shift to the outlet's Y
            (0.0, 0.0, 1.0),  # shift to the outlet's Z
            (0.4, 0.0, 0.0),  # finish X to reach the outlet
        ]

        router.route_with_fractional_path(self.inlet, self.outlet, simple_path, label="void")
        router.finalize_routes()

if __name__ == "__main__":
    SerpentineChannel().preview()