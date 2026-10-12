from collections import deque

from motif.events import Frontend
from motif.guardian import Guardian, Request
from motif.motifs import ShiftRXCount, ShiftTX


class SequentialSPI:
    """Single-issue fused shift/count, FIFO and TX-load operations.

    This reference covers SPI mode 0 only. It is not a general protocol machine.
    Events are captured with their sampled data before operations are serialized.
    """

    fifo_depth = 4

    def __init__(self, config):
        self.config = config
        self.frontend = Frontend()
        self.guardian = Guardian(config.open_drain, config.watchdog)
        self.rx, self.tx = ShiftRXCount(config.lsb_first), ShiftTX(config.lsb_first)
        self.rx_fifo, self.tx_fifo, self.operations = deque(), deque(), deque()
        self.active = False
        self.issued = self.cycle = 0
        self.max_backlog = 0

    def push_tx(self, byte):
        if len(self.tx_fifo) == 4:
            raise OverflowError("TX FIFO full")
        self.tx_fifo.append(byte)

    def pop_rx(self):
        return self.rx_fifo.popleft() if self.rx_fifo else None

    def step(self, pins):
        edge = self.frontend.step(pins)
        cfg = self.config
        selected = not bool(edge.level & (1 << cfg.frame_pin))
        if self.active and not selected:
            self.active = False
            self.operations.clear()
            self.rx.clear()
            self.tx.remaining = 0
        elif selected and not self.active and self.frontend.warmup >= 2:
            self.active = True
            self.rx.clear()
            self.operations.append(("load", None))
        elif self.active:
            if edge.rising & (1 << cfg.clock_pin):
                self.operations.append(("receive", bool(edge.level & (1 << cfg.rx_pin))))
            if edge.falling & (1 << cfg.clock_pin):
                self.operations.append(("transmit", None))
        if len(self.operations) > 4:
            raise OverflowError("Sequential event queue exceeded four operations")
        self.max_backlog = max(self.max_backlog, len(self.operations))
        if self.operations:
            op, value = self.operations.popleft()
            self.issued += 1
            if op == "receive":
                byte = self.rx.fire(value)
                if byte is not None:
                    self.operations.append(("enqueue", byte))
            elif op == "enqueue":
                if len(self.rx_fifo) < 4:
                    self.rx_fifo.append(value)
            elif op == "transmit":
                if self.tx.fire():
                    self.operations.append(("load", None))
            else:
                self.tx.load(self.tx_fifo.popleft() if self.tx_fifo else cfg.fill)
        requests = [Request(0, cfg.tx_pin, self.tx.bit)] if self.active else []
        data, oe = self.guardian.apply(requests, {0: 1 << cfg.tx_pin} if self.active else {}, bool(pins & (1 << cfg.frame_pin)))
        self.cycle += 1
        return {"data": data, "oe": oe, "cycle": self.cycle}
