from dataclasses import dataclass


@dataclass(frozen=True)
class Edges:
    level: int
    rising: int
    falling: int


class Frontend:
    """Actors consume old stage-two levels and their qualified edge pulses."""

    def __init__(self):
        self.first = self.second = self.previous = 0xFF
        self.warmup = 0

    def step(self, pins):
        level = self.second
        valid = self.warmup >= 2
        result = Edges(level, level & ~self.previous & 255 if valid else 0,
                       self.previous & ~level & 255 if valid else 0)
        self.previous, self.second, self.first = level, self.first, pins & 255
        self.warmup = min(2, self.warmup + 1)
        return result
