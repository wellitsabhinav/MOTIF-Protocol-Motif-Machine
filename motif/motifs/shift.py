class ShiftRXCount:
    """Sample, shift, count, and complete in one architectural firing."""

    def __init__(self, lsb_first=False):
        self.lsb_first = lsb_first
        self.value = self.count = 0

    def clear(self):
        self.value = self.count = 0

    def fire(self, bit):
        if self.lsb_first:
            self.value = (self.value >> 1) | (int(bit) << 7)
        else:
            self.value = ((self.value << 1) | int(bit)) & 255
        self.count += 1
        if self.count == 8:
            result = self.value
            self.count = 0
            return result
        return None


class ShiftTX:
    def __init__(self, lsb_first=False):
        self.lsb_first = lsb_first
        self.value = self.remaining = 0

    def load(self, value):
        self.value = value & 255
        self.remaining = 8

    @property
    def bit(self):
        return self.value & 1 if self.lsb_first else (self.value >> 7) & 1

    def fire(self):
        if not self.remaining:
            return False
        self.value = self.value >> 1 if self.lsb_first else (self.value << 1) & 255
        self.remaining -= 1
        return self.remaining == 0
