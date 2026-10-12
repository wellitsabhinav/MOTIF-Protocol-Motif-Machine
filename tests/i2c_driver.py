class Bus:
    """Independent controller; wired-AND resolution includes target requests."""

    def __init__(self, engine, spacing=8):
        self.engine = engine
        self.spacing = spacing
        self.scl = self.sda = 1
        self.output = {"oe": 0, "data": 0}
        self.trace = []
        self.hold(16)

    def hold(self, cycles=None, scl=None, sda=None):
        if scl is not None:
            self.scl = scl
        if sda is not None:
            self.sda = sda
        for _ in range(cycles or self.spacing):
            target_scl = not bool(self.output["oe"] & 2)
            target_sda = not bool(self.output["oe"] & 4)
            pins = (255 & ~6) | ((self.scl and target_scl) << 1) | ((self.sda and target_sda) << 2)
            self.output = self.engine.step(pins)
            self.trace.append(self.output)
        return self.output

    @property
    def data(self):
        return self.sda and not bool(self.output["oe"] & 4)

    def start(self):
        self.hold(scl=0, sda=1)
        self.hold(scl=1)
        self.hold(sda=0)
        self.hold(scl=0)

    def stop(self):
        self.hold(scl=0, sda=0)
        self.hold(scl=1)
        self.hold(sda=1)

    def write(self, byte):
        for index in range(7, -1, -1):
            self.hold(scl=0, sda=(byte >> index) & 1)
            self.hold(scl=1)
        self.hold(scl=0, sda=1)
        self.hold(scl=1)
        acknowledged = not self.data
        self.hold(scl=0)
        return acknowledged

    def read(self, ack=False):
        result = 0
        self.hold(sda=1)
        for _ in range(8):
            self.hold(scl=1)
            if self.output["oe"] & 2:
                raise RuntimeError("Controller must wait for stretched SCL")
            result = (result << 1) | int(self.data)
            self.hold(scl=0)
        self.hold(sda=0 if ack else 1)
        self.hold(scl=1)
        self.hold(scl=0)
        self.hold(sda=1)
        return result
