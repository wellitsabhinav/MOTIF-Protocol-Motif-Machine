from dataclasses import dataclass


@dataclass(frozen=True)
class DriveHistory:
    current: int
    previous: int


class PadHistory:
    """Six bits of guarded-drive provenance aligned with qualified pin samples."""

    def __init__(self):
        self.first = self.second = self.previous = 0

    def step(self, drive):
        result = DriveHistory(self.second, self.previous)
        self.previous, self.second, self.first = self.second, self.first, drive & 3
        return result
