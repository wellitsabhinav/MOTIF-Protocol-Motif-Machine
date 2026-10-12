from dataclasses import dataclass


@dataclass(frozen=True)
class Request:
    owner: int
    pin: int
    data: int
    oe: bool = True

    def __post_init__(self):
        if type(self.owner) is not int or not 0 <= self.owner < 8 or type(self.pin) is not int or not 0 <= self.pin < 8:
            raise ValueError("Request owner/pin outside three-bit range")
        if self.data not in (0, 1) or type(self.oe) is not bool:
            raise ValueError("Request DATA/OE must be binary")


class Guardian:
    """Final authority over pad drive. No shifter state is inspected."""

    def __init__(self, open_drain=0, watchdog=0):
        self.open_drain = open_drain
        self.watchdog = watchdog
        self.age = 0
        self.tripped = False
        self.faults = set()

    def tick(self, active, acquire=False, progress=False, abort=False):
        if acquire:
            self.tripped = False
            self.age = 0
        if abort:
            self.tripped = True
            self.faults.add("abort")
        if not active or progress:
            self.age = 0
        elif self.watchdog:
            self.age = min(self.watchdog, self.age + 1)
            if self.age == self.watchdog:
                self.tripped = True
                self.faults.add("timeout")
        return self.tripped

    def apply(self, requests, ownership, kill=False):
        data = oe = 0
        seen = set()
        for request in requests:
            mask = 1 << request.pin
            if not request.oe:
                continue
            if request.pin in seen:
                oe &= ~mask
                self.faults.add("conflict")
                continue
            seen.add(request.pin)
            if kill or self.tripped:
                continue
            if not ownership.get(request.owner, 0) & mask:
                self.faults.add("ownership")
                continue
            if self.open_drain & mask and request.data:
                self.faults.add("drive_high")
                continue
            oe |= mask
            if request.data and not self.open_drain & mask:
                data |= mask
        return data & oe, oe
