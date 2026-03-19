import pymfcad

c = pymfcad.Component(size=(15,15,15), position=(0, 0, 0), px_size=0.01, layer_size=0.01)
c.add_port("p1", pymfcad.Port(pymfcad.Port.PortType.IN, position=(0, 5, 5), size=(5,5,5), surface_normal=pymfcad.Port.SurfaceNormal.NEG_X))
c.add_port("p2", pymfcad.Port(pymfcad.Port.PortType.INOUT, position=(5, 0, 5), size=(5,5,5), surface_normal=pymfcad.Port.SurfaceNormal.NEG_Y))
c.add_port("p3", pymfcad.Port(pymfcad.Port.PortType.OUT, position=(15, 5, 5), size=(5,5,5), surface_normal=pymfcad.Port.SurfaceNormal.POS_X))

c.add_label("bulk", pymfcad.Color(255, 0, 0, 255))
c.add_bulk("bulk_shape", pymfcad.Cube(size=(10,10,10)), label="bulk")

c.preview()