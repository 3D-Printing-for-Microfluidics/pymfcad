from pymfd import Component, Port, Color

class Valve20px(Component):
    """
    20 px membrane valve
    - 3 layer fluidic chamber
    - 11 layer pneumatic chamber
    - 1 layer membrane

    Ports:
    - F_IN:
        - Type: IN
        - Size: (6, 6, 4)
        - Normal: NEG_Z
    - F_OUT:
        - Type: OUT
        - Size: (8, 8, 6)
        - Normal: POS_Y
    - P_IN:
        - Type: INOUT
        - Size: (8, 8, 6)
        - Normal: NEG_Y
    - P_OUT:
        - Type: INOUT
        - Size: (8, 8, 6)
        - Normal: POS_Y
    """
    def __init__(self):
        super().__init__(size=(36, 36, 24), position=(0,0,0), px_size=0.0076, layer_size=0.01) # px_size=1.0, layer_size=1.0)

        self.add_label("pneumatic", Color.from_name("red", 255))
        self.add_label("fluidic", Color.from_name("blue", 255))

        self.add_shape("FluidicChamber", self.make_cylinder(h=2, r=10, center=False).translate((18,18,4)), label="fluidic")
        self.add_shape("FluidicInput", self.make_cube((6, 6, 4), center=False).translate((15,15,0)), label="fluidic")
        self.add_shape("FluidicOutput", self.make_cube((8, 10, 6), center=False).translate((14,26,0)), label="fluidic")

        pneumatics = self.make_cylinder(h=11, r=10, center=False).translate((18,18,7))
        pneumatics += self.make_cube((8, 10, 6), center=False).translate((14,0,12))
        pneumatics += self.make_cube((8, 10, 6), center=False).translate((14,26,12))
        self.add_shape("PneumaticShapes", pneumatics, label="pneumatic")

        self.add_port("F_IN", Port(Port.PortType.IN, (15, 15, 0), (6, 6, 4), Port.SurfaceNormal.NEG_Z))
        self.add_port("F_OUT", Port(Port.PortType.OUT, (14, 36, 0), (8, 8, 6), Port.SurfaceNormal.POS_Y))
        self.add_port("P_IN", Port(Port.PortType.INOUT, (14, 0, 12), (8, 8, 6), Port.SurfaceNormal.NEG_Y))
        self.add_port("P_OUT", Port(Port.PortType.INOUT, (14, 36, 12), (8, 8, 6), Port.SurfaceNormal.POS_Y))