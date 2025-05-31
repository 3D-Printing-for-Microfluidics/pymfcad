from fluidic_classes import MicrofluidicModule
from pathing import weighted_a_star_3d, get_keepout_boxes_from_paths, visualize_paths, path_ports

class IOBlock(MicrofluidicModule):
    def __init__(self, chan_size = (4,4,4)):
        dx, dy, dz = chan_size
        half_dx_n, half_dy_n, half_dz_n = dx // 2, dy // 2, dz // 2
        half_dx_p, half_dy_p, half_dz_p = dx // 2, dy // 2, dz // 2

        if dx%2 == 1:
            half_dx_p += 1

        if dy%2 == 1:
            half_dy_p += 1

        if dz%2 == 1:
            half_dz_p += 1

        self.bounding_box = ((-half_dx_n,-half_dy_n,-half_dz_n), (half_dx_p,half_dy_p,half_dz_p))
        self.ports = []
        self.translation = []
        self.add_port("x+ out", "output", (dx,dx), (half_dx_p,0,0), (1,0,0))
        self.add_port("x- out", "output", (dx,dx), (-half_dx_n,0,0), (-1,0,0))
        self.add_port("y+ out", "output", (dy,dy), (0,half_dy_p,0), (0,1,0))
        self.add_port("y- out", "output", (dy,dy), (0,-half_dy_n,0), (0,-1,0))
        self.add_port("z+ out", "output", (dz,dz), (0,0,half_dz_p), (0,0,1))
        self.add_port("z- out", "output", (dz,dz), (0,0,-half_dz_n), (0,0,-1))
        self.add_port("x+ in", "input", (dx,dx), (-half_dx_n,0,0), (1,0,0))
        self.add_port("x- in", "input", (dx,dx), (half_dx_p,0,0), (-1,0,0))
        self.add_port("y+ in", "input", (dy,dy), (0,-half_dy_n,0), (0,1,0))
        self.add_port("y- in", "input", (dy,dy), (0,half_dy_p,0), (0,-1,0))
        self.add_port("z+ in", "input", (dz,dz), (0,0,-half_dz_n), (0,0,1))
        self.add_port("z- in", "input", (dz,dz), (0,0,half_dz_p), (0,0,-1))


## TEST 1
px = 1.0
layer = 1.0

chan_size = (10*px, 10*px, 7*layer)
chan_keepout = (15*px,15*px,10*layer)
device_size = ((0*px,0*px,0*layer), (2560*px, 1600*px, 1000*layer))

m1 = IOBlock((100*px, 100*px, 100*layer)).translate((100*px, 100*px, 100*layer))
m2 = IOBlock((100*px, 100*px, 100*layer)).translate((2510*px, 1550*px, 950*layer))

keepouts = [m1.bounding_box, m2.bounding_box]
paths = []
paths.append(path_ports(device_size, chan_size, px, layer, keepouts, m1.get_port("x+ out"), m2.get_port("x+ in")))
visualize_paths(paths, keepouts=keepouts, path_keepouts=get_keepout_boxes_from_paths(chan_keepout, paths))

## TEST 2
px = 1.0
layer = 1.0

chan_size = (2*px, 2*px, 2*layer)
chan_keepout = (4*px,4*px,4*layer)
device_size = ((0,0,0), (50,50,50))

nnn = IOBlock((4*px,4*px,4*layer)).translate((10*px, 10*px, 10*layer))
nnp = IOBlock((4*px,4*px,4*layer)).translate((10*px, 10*px, 40*layer))
npn = IOBlock((4*px,4*px,4*layer)).translate((10*px, 40*px, 10*layer))
npp = IOBlock((4*px,4*px,4*layer)).translate((10*px, 40*px, 40*layer))
pnn = IOBlock((4*px,4*px,4*layer)).translate((40*px, 10*px, 10*layer))
pnp = IOBlock((4*px,4*px,4*layer)).translate((40*px, 10*px, 40*layer))
ppn = IOBlock((4*px,4*px,4*layer)).translate((40*px, 40*px, 10*layer))
ppp = IOBlock((4*px,4*px,4*layer)).translate((40*px, 40*px, 40*layer))


paths = []
staic_keepouts = [nnn.bounding_box, nnp.bounding_box, npn.bounding_box, npp.bounding_box, pnn.bounding_box, pnp.bounding_box, ppn.bounding_box, ppp.bounding_box]
dynamic_keepouts = staic_keepouts
paths.append(path_ports(device_size, chan_size, px, layer, dynamic_keepouts, nnn.get_port("x+ out"), ppp.get_port("x+ in")))
dynamic_keepouts = (get_keepout_boxes_from_paths(chan_keepout, paths))
paths.append(path_ports(device_size, chan_size, px, layer, dynamic_keepouts, nnp.get_port("x- out"), ppn.get_port("x- in")))
dynamic_keepouts = (get_keepout_boxes_from_paths(chan_keepout, paths))
paths.append(path_ports(device_size, chan_size, px, layer, dynamic_keepouts, npn.get_port("y+ out"), pnp.get_port("y+ in")))
dynamic_keepouts = (get_keepout_boxes_from_paths(chan_keepout, paths))
paths.append(path_ports(device_size, chan_size, px, layer, dynamic_keepouts, npp.get_port("y- out"), pnn.get_port("y- in")))
dynamic_keepouts = (get_keepout_boxes_from_paths(chan_keepout, paths))
visualize_paths(paths)
visualize_paths(paths, keepouts=staic_keepouts, path_keepouts=dynamic_keepouts)