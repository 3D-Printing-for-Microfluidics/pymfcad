### Y JUNCTION
import inspect
from pymfcad import Component, Port, Color, Cube, Polychannel, PolychannelShape


class YJunctionMixer(Component):
    """
    Simple Y-junction mixer with two inlets and one outlet.
    """

    def __init__(
        self,
        channel_size=(8, 8, 6),
        channel_margin=(8, 8, 6),
        px_size=0.0076,
        layer_size=0.01,
        quiet=False,
    ):
        frame = inspect.currentframe()
        args, _, _, values = inspect.getargvalues(frame)
        self.init_args = [values[arg] for arg in args if arg != "self"]
        self.init_kwargs = {arg: values[arg] for arg in args if arg != "self"}

        super().__init__(
            size=(
                4 * channel_size[0],
                2 * channel_size[1] + 3 * channel_margin[1],
                channel_size[2] + 2 * channel_margin[2],
            ),
            position=(0, 0, 0),
            px_size=px_size,
            layer_size=layer_size,
            quiet=quiet,
        )

        self.add_label("bulk", Color.from_name("aqua", 127))
        self.add_label("void", Color.from_name("red", 255))

        self.add_bulk(
            "bulk_shape",
            Cube(self._size, center=False),
            label="bulk",
        )

        y_shape = Polychannel(
            [
                PolychannelShape(
                    "cube",
                    position=(0, channel_margin[1], channel_size[2]),
                    size=(0, channel_size[1], channel_size[2]),
                ),
                PolychannelShape(
                    "cube",
                    position=(4 * channel_size[0], 1 * channel_margin[1], 0),
                    size=(0, channel_size[1], channel_size[2]),
                ),
                PolychannelShape(
                    "cube",
                    position=(-4 * channel_size[0], 1 * channel_margin[1], 0),
                    size=(0, channel_size[1], channel_size[2]),
                ),
            ]
        )
        y_shape.translate(
            (
                0,
                channel_size[1] / 2,
                channel_margin[2] / 2,
            )
        )
        self.add_void("y_channel", y_shape, label="void")

        self.add_port(
            "inlet1",
            Port(
                Port.PortType.IN,
                (0, channel_margin[1], channel_size[2]),
                channel_size,
                Port.SurfaceNormal.NEG_X,
            ),
        )
        self.add_port(
            "inlet2",
            Port(
                Port.PortType.IN,
                (0, channel_size[1] + 2 * channel_margin[1], channel_size[2]),
                channel_size,
                Port.SurfaceNormal.NEG_X,
            ),
        )
        self.add_port(
            "outlet",
            Port(
                Port.PortType.OUT,
                (
                    4 * channel_size[0],
                    channel_size[1] + channel_margin[1],
                    channel_size[2],
                ),
                channel_size,
                Port.SurfaceNormal.POS_X,
            ),
        )


if __name__ == "__main__":
    YJunctionMixer().preview()
