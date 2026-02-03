from openmfd import Component, Port, Color, Cube, Router, set_fn, PolychannelShape


class OddChannelRouting(Component):
    """
    Example component that autoroutes several odd-sized channels.
    """

    def __init__(
        self,
        channel_size: tuple[int, int, int] = (1, 1, 1),
        channel_margin: tuple[int, int, int] = (0, 0, 0),
        quiet: bool = False,
    ):
        super().__init__(
            size=(160, 90, 30),
            position=(0, 0, 0),
            px_size=0.01,
            layer_size=0.01,
            quiet=quiet,
        )

        # Labels
        self.add_label("device", Color.from_name("cyan", 127))
        self.add_label("fluidic", Color.from_name("magenta", 127))

        # Ports (odd-sized channels)
        self.add_port(
            "A_IN",
            Port(
                Port.PortType.IN,
                (0, 0, 0),
                channel_size,
                Port.SurfaceNormal.NEG_X,
            ),
        )
        self.add_port(
            "A_OUT",
            Port(
                Port.PortType.OUT,
                (160, 20, 15),
                channel_size,
                Port.SurfaceNormal.POS_X,
            ),
        )

        # Route channels
        router = Router(
            component=self, channel_size=channel_size, channel_margin=channel_margin
        )
        router.autoroute_channel(self.A_IN, self.A_OUT, label="fluidic")
        # router.route_with_fractional_path(self.A_IN, self.A_OUT, [(1,1,1)], label="fluidic")
        # router.route_with_polychannel(self.A_IN, self.A_OUT, [
        #     PolychannelShape("cube", (0,0,30 - channel_size[2]))
        #     ], label="fluidic")
        router.finalize_routes()

        # Build bulk shape
        self.add_bulk("BulkShape", Cube(self._size, center=False), label="device")


if __name__ == "__main__":
    set_fn(50)
    OddChannelRouting().preview()
