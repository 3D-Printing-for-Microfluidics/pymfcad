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

        router = Router(self, channel_size=channel_size, channel_margin=channel_margin)

        # Build a 2D serpentine path (Z stays at 0.0)
        x_steps = loops * 2 + 1
        x_step = 1.0 / x_steps

        serpentine = []
        direction = 1
        for loop in range(loops):
            # Move along X into the next segment
            serpentine.append((direction * x_step, 0.0, 0.0))

            # Sweep across Y (up/down alternates each loop)
            y_dir = 1 if loop % 2 == 0 else -1
            serpentine.append((0.0, direction * y_dir, 0.0))

            # Move along X again to complete the loop
            serpentine.append((direction * x_step, 0.0, 0.0))

        # Final X step to land exactly on the outlet
        serpentine.append((x_step, 0.0, 1.0))

        router.route_with_fractional_path(self.inlet, self.outlet, serpentine, label="void")
        router.finalize_routes()

if __name__ == "__main__":
    SerpentineChannel().preview()