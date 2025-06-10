from pymfd.microfluidic_designer import Component, Port, Color, PolychannelShape
from pymfd.router import Router

class Pinhole(Component):
    """
    Simple 144 px pinhole component. 
    
    Ports:
    - port:
        - Type: INOUT
        - Size: (8, 8, 6)
        - Normal: POS_X
    """
    def __init__(self):
        super().__init__(size=(250, 144, 110), position=(0,0,0), px_size=0.0076, layer_size=0.01) # px_size=1.0, layer_size=1.0)

        self.add_label("default", Color.from_name("aqua", 255))

        rtr = Router(component=self)
        shape = self.make_polychannel([
            PolychannelShape("sphr", (0,144,110), (0,0,0)),
            PolychannelShape("sphr", (0,144,110), (200,0,0)),
            PolychannelShape("cube", (0,8,6), (50,-4,-4)),
        ]).translate((0,72,55))

        self.add_shape("pinhole", shape, label="default")

        self.add_port("port", Port(Port.PortType.INOUT, (250, 68, 106), (8, 8, 6), Port.SurfaceNormal.POS_X))