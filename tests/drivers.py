class Wires:
    def __init__(self, engine, spacing=8):
        self.engine = engine
        self.spacing = spacing
        self.pins = 255
        self.trace = []

    def hold(self, cycles=None, **pins):
        if cycles is None:
            cycles = self.spacing
        for key, value in pins.items():
            pin = int(key[1:])
            self.pins = (self.pins | (1 << pin)) if value else (self.pins & ~(1 << pin))
        for _ in range(cycles):
            self.trace.append(self.engine.step(self.pins))
        return self.trace[-1]

    def spi(self, rx, tx):
        self.hold(p0=1, p1=0)
        self.engine.push_tx(tx)
        self.hold(p0=0)
        received = 0
        for index in range(7, -1, -1):
            self.hold(p2=(rx >> index) & 1)
            received = (received << 1) | ((self.trace[-1]["data"] >> 3) & 1)
            self.hold(p1=1)
            self.hold(p1=0)
        self.hold(p0=1)
        return received

    def uart(self, byte, period=32, stop=1):
        self.hold(period, p2=1)
        self.hold(period, p2=0)
        for index in range(8):
            self.hold(period, p2=(byte >> index) & 1)
        self.hold(period, p2=stop)
        self.hold(8, p2=1)
