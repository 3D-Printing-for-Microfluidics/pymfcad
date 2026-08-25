from pymfcad import Color, Component, Cube, Port, Router


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
        levels=5,
        px_size=0.0076,
        layer_size=0.01,
        quiet=False,
    ):

        # Overall component size (bulk)
        length = channel_size[0] * loops + channel_margin[0] * (loops + 1)

        super().__init__(
            size=(
                length,
                width,
                channel_size[2] * levels + channel_margin[2] * (levels + 1),
            ),
            px_size=px_size,
            layer_size=layer_size,
            quiet=quiet,
        )

        # Labels define which geometry is solid vs. empty
        self.add_label("bulk", Color.from_name("aqua", 127))
        self.add_label("void", Color.from_name("red", 255))

        # The component starts as a solid block
        self.add_bulk("bulk_shape", Cube(self._size, center=False), label="bulk")

        # Ports define where routing starts/ends
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
                (
                    length,
                    width - 2 * channel_margin[1],
                    levels * (channel_margin[2] + channel_size[2]) - channel_margin[2],
                ),
                channel_size,
                Port.SurfaceNormal.POS_X,
            ),
        )

        router = Router(self, channel_size=channel_size, channel_margin=channel_margin)

        # Build a fractional serpentine path.
        # Each tuple is a fraction of the *total* vector from inlet to outlet.
        # All X fractions must sum to 1.0, same for Y and Z.
        total_height = (channel_size[2] + channel_margin[2]) * (levels - 1)
        layer_step = (
            (channel_size[2] + channel_margin[2]) / total_height if levels > 1 else 0.0
        )

        # We split X into small steps: left/right moves + a final nudge to reach the outlet
        x_steps = loops * 2 + 1
        x_step = 1.0 / x_steps

        serpentine = []
        for layer in range(levels):
            # Alternate direction each layer (zig-zag)
            direction = 1 if layer % 2 == 0 else -1

            for loop in range(loops):
                # Move along X into the next segment
                if layer == 0 or loop != 0:
                    serpentine.append((direction * x_step, 0.0, 0.0))

                # Sweep across Y (up/down alternates each loop)
                y_dir = 1 if loop % 2 == 0 else -1
                serpentine.append((0.0, direction * y_dir, 0.0))

                # Move along X again to complete the loop
                if layer == levels - 1 or loop != loops - 1:
                    serpentine.append((direction * x_step, 0.0, 0.0))

            # Step up in Z between levels (except after the last one)
            if layer != levels - 1:
                serpentine.append((0.0, 0.0, layer_step))

        # Final X step to land exactly on the outlet
        serpentine.append((x_step, 0.0, 0.0))

        if levels == 1:
            # If there's only one level, we need to finish the Z movement to reach the outlet
            serpentine.append((0.0, 0.0, 1.0))

        router.route_with_fractional_path(
            self.inlet, self.outlet, serpentine, label="void"
        )
        router.finalize_routes()


if __name__ == "__main__":
    SerpentineChannel().preview()
