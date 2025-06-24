from .. import Component, Port, Color, PolychannelShape
from ..router import Router


class Pinhole(Component):
    """
    Simple 144 px pinhole component.

    Ports:
    - port:
        - Type: INOUT
        - Size: (8, 8, 6)
        - Normal: POS_X
    """

    def __init__(self, channel_size: tuple[int, int, int] = (8, 8, 6)):
        pinhole_height = 144
        pinhole_width = 110
        pinhole_length = 200
        taper_length = 50
        total_length = pinhole_length + taper_length

        super().__init__(
            size=(total_length, pinhole_height, pinhole_width),
            position=(0, 0, 0),
            px_size=0.0076,
            layer_size=0.01,
        )  # px_size=1.0, layer_size=1.0)

        self.add_label("default", Color.from_name("aqua", 255))

        shape = self.make_polychannel(
            [
                PolychannelShape(
                    "sphere", position=(0, 0, 0), size=(0, pinhole_height, pinhole_width)
                ),
                PolychannelShape(
                    "sphere",
                    position=(pinhole_length, 0, 0),
                    size=(0, pinhole_height, pinhole_width),
                ),
                PolychannelShape(
                    "cube",
                    position=(taper_length, pinhole_height / 2, pinhole_width / 2),
                    size=(0, channel_size[1], channel_size[2]),
                    center=True,
                ),
            ]
        )

        self.add_shape("pinhole", shape, label="default")

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
