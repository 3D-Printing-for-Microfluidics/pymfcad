from microfluidic_designer import Component, Port, NetType

class Valve20px(Component):
    def __init__(self, name):
        super().__init__(name, (0,0,0), size=(36, 36, 24), px_size=0.0076, layer_size=0.01) # px_size=1.0, layer_size=1.0)

        self.add_nettype(NetType(name="pneumatic", color=(255, 0, 0, 255)))
        self.add_nettype(NetType(name="fluidic", color=(0, 0, 255, 255)))

        self.add_shape(self.make_cylinder(h=2, r=10, center=False, nettype="fluidic").translate((18,18,4)))
        self.add_shape(self.make_cube((6, 6, 4), center=False, nettype="fluidic").translate((15,15,0)))
        self.add_shape(self.make_cube((8, 10, 6), center=False, nettype="fluidic").translate((14,26,0)))

        pneumatics = self.make_cylinder(h=11, r=10, center=False, nettype="pneumatic").translate((18,18,7))
        pneumatics += self.make_cube((8, 10, 6), center=False, nettype="pneumatic").translate((14,0,12))
        pneumatics += self.make_cube((8, 10, 6), center=False, nettype="pneumatic").translate((14,26,12))
        self.add_shape(pneumatics)

        self.add_port(Port("F_IN", Port.PortType.IN, (15, 15, 0), (6, 6, 4), Port.Pointing_Vector.NEG_Z))
        self.add_port(Port("F_OUT", Port.PortType.OUT, (14, 36, 0), (8, 8, 6), Port.Pointing_Vector.POS_Y))
        self.add_port(Port("P_IN", Port.PortType.INOUT, (14, 0, 12), (8, 8, 6), Port.Pointing_Vector.NEG_Y))
        self.add_port(Port("P_OUT", Port.PortType.INOUT, (14, 36, 12), (8, 8, 6), Port.Pointing_Vector.POS_Y))
