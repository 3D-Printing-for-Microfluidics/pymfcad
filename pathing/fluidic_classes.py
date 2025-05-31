class Port:
    def __init__(self, name, type, shape, position, pointing_vector):
        self.name = name
        self.type = type
        self.shape = shape
        self.position = position
        self.pointing_vector = pointing_vector
        self.translation = []

    def translate(self, v):
        self.translation.append(v)

    @property
    def position(self):
        return tuple(sum(x) for x in zip(*(self.translation + [self._position])))
    
    @position.setter
    def position(self, value):
        self._position = value
        return self._position

class MicrofluidicModule:
    def __init__(self, bounding_box):
        self.bounding_box = bounding_box
        self.translation = []
        # self.rotation = 0
        # self.mirroring = [False, False]

        self.ports = []

        # self.geometry = make_pin_valve_geometry(length, radius)
        # self.slicing_profile = {
        #     "default_exposure": 0.6,
        #     "lift_speed": 1.2,
        #     "delays": {"after_exposure": 0.5}
        # }

    @property
    def bounding_box(self):
        return [tuple(a + b for a, b in zip(base, self.get_translation())) for base in self._bounding_box]
    
    @bounding_box.setter
    def bounding_box(self, value):
        self._bounding_box = value

    def get_translation(self):
        return tuple(sum(x) for x in zip(*self.translation))

    def translate(self, v):
        self.translation.append(v)
        for port in self.ports:
            port.translate(v)
        return self

    # def get_rotation(self):
    #     return self.rotation

    # def rotate(self, a):
    #     self.rotation += a
    #     while self.rotation > 360:
    #         self.rotation -= 360
    #     return self.rotation

    # def get_mirroring(self):
    #     return self.mirroring

    # def mirror(self, v):
    #     if v[0]:
    #         self.mirroring[0] = not self.mirroring[0]
    #     if v[1]:
    #         self.mirroring[1] = not self.mirroring[1]
    #     return self.mirroring

    def add_port(self, name, type, shape, position, pointing_vector):
        self.ports.append(Port(name, type, shape, position, pointing_vector))

    def get_port(self, name):
        for port in self.ports:
            if port.name == name:
                return port

    # def build(self):
    #     pass

# class MicrofluidicDevice(MicrofluidicModule):
