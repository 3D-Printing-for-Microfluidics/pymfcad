from microfluidic_designer import Component, Port, NetType

class TestCube(Component):
    def __init__(self, name):
        super().__init__(name, (0,0,0), size=(30, 30, 15), px_size=0.0076, layer_size=0.01) # px_size=1.0, layer_size=1.0)

        self.add_shape(self.make_cube((30, 30, 15), center=False))

        self.add_port(Port(self, "F_OUT", Port.PortType.IN, (0, 11, 0), (7, 7, 5), Port.Pointing_Vector.NEG_X))
        self.add_port(Port(self, "F_OUT", Port.PortType.OUT, (0, 11, 5), (7, 7, 5), Port.Pointing_Vector.NEG_X))
        self.add_port(Port(self, "F_OUT", Port.PortType.INOUT, (0, 11, 10), (7, 7, 5), Port.Pointing_Vector.NEG_X))
        self.add_port(Port(self, "F_OUT", Port.PortType.IN, (30, 11, 0), (7, 7, 5), Port.Pointing_Vector.POS_X))
        self.add_port(Port(self, "F_OUT", Port.PortType.OUT, (30, 11, 5), (7, 7, 5), Port.Pointing_Vector.POS_X))
        self.add_port(Port(self, "F_OUT", Port.PortType.INOUT, (30, 11, 10), (7, 7, 5), Port.Pointing_Vector.POS_X))

        self.add_port(Port(self, "F_OUT", Port.PortType.IN, (11, 0, 0), (7, 7, 5), Port.Pointing_Vector.NEG_Y))
        self.add_port(Port(self, "F_OUT", Port.PortType.OUT, (11, 0, 5), (7, 7, 5), Port.Pointing_Vector.NEG_Y))
        self.add_port(Port(self, "F_OUT", Port.PortType.INOUT, (11, 0, 10), (7, 7, 5), Port.Pointing_Vector.NEG_Y))
        self.add_port(Port(self, "F_OUT", Port.PortType.IN, (11, 30, 0), (7, 7, 5), Port.Pointing_Vector.POS_Y))
        self.add_port(Port(self, "F_OUT", Port.PortType.OUT, (11, 30, 5), (7, 7, 5), Port.Pointing_Vector.POS_Y))
        self.add_port(Port(self, "F_OUT", Port.PortType.INOUT, (11, 30, 10), (7, 7, 5), Port.Pointing_Vector.POS_Y))

        self.add_port(Port(self, "F_OUT", Port.PortType.IN, (0, 0, 0), (7, 7, 5), Port.Pointing_Vector.NEG_Z))
        self.add_port(Port(self, "F_OUT", Port.PortType.OUT, (7, 7, 0), (7, 7, 5), Port.Pointing_Vector.NEG_Z))
        self.add_port(Port(self, "F_OUT", Port.PortType.INOUT, (14, 14, 0), (7, 7, 5), Port.Pointing_Vector.NEG_Z))
        self.add_port(Port(self, "F_OUT", Port.PortType.IN, (0, 0, 15), (7, 7, 5), Port.Pointing_Vector.POS_Z))
        self.add_port(Port(self, "F_OUT", Port.PortType.OUT, (7, 7, 15), (7, 7, 5), Port.Pointing_Vector.POS_Z))
        self.add_port(Port(self, "F_OUT", Port.PortType.INOUT, (14, 14, 15), (7, 7, 5), Port.Pointing_Vector.POS_Z))