class TimedSample:
    """Bounded sample schedule with optional leading/trailing level checks."""

    def __init__(self, period, validate_start=False, validate_stop=False):
        self.period = period
        self.validate_start = validate_start
        self.validate_stop = validate_stop
        self.running = False
        self.phase = "data"
        self.left = self.samples = 0

    def start(self):
        self.running = True
        self.samples = 0
        self.phase = "start" if self.validate_start else "data"
        self.left = self.period // 2 if self.validate_start else self.period

    def stop(self):
        self.running = False

    def tick(self, bit):
        if not self.running:
            return None
        self.left -= 1
        if self.left:
            return None
        self.left = self.period
        if self.phase == "start":
            if bit:
                self.stop()
                return "invalid_start"
            self.phase = "data"
            return "start_valid"
        if self.phase == "stop":
            self.stop()
            return "stop_valid" if bit else "invalid_stop"
        self.samples = (self.samples + 1) % 8
        if not self.samples and self.validate_stop:
            self.phase = "stop"
        return "sample"
