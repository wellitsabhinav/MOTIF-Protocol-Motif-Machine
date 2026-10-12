from collections import deque
from dataclasses import dataclass

from .events import Frontend
from .guardian import Guardian, Request
from .motifs import ShiftRXCount, ShiftTX, TimedSample
from .motifs.exchange import ByteExchange


@dataclass(frozen=True)
class Config:
    frame: str = "level"
    frame_pin: int = 0
    clock_pin: int = 1
    rx_pin: int = 2
    tx_pin: int = 3
    sample: str = "rising"
    transmit: bool = True
    lsb_first: bool = False
    period: int = 434
    validate_start: bool = False
    validate_stop: bool = False
    open_drain: int = 0
    watchdog: int = 0
    fill: int = 255
    exchange: bool = False
    address: int = 0x52
    ack_address: bool = True
    ack_data: bool = True

    def __post_init__(self):
        if self.frame not in ("level", "falling", "two_wire") or self.sample not in ("rising", "timer"):
            raise ValueError("Unsupported event source")
        if any(not 0 <= pin < 8 for pin in (self.frame_pin, self.clock_pin, self.rx_pin, self.tx_pin)):
            raise ValueError("Pin outside eight-pin engine")
        if not 2 <= self.period <= 65535 or not 0 <= self.watchdog <= 65535:
            raise ValueError("Timer outside sixteen-bit range")
        if not 0 <= self.fill <= 255 or not 0 <= self.open_drain <= 255:
            raise ValueError("Byte configuration outside range")
        if not 0 <= self.address < 128:
            raise ValueError("Address outside seven-bit range")
        if self.exchange and (self.rx_pin != self.tx_pin or self.sample != "rising"):
            raise ValueError("Byte exchange requires a shared data pin and external clock")
        if self.frame == "two_wire" and not self.exchange:
            raise ValueError("Two-wire framing requires byte exchange")
        if self.frame == "two_wire" and self.open_drain & ((1 << self.rx_pin) | (1 << self.clock_pin)) != ((1 << self.rx_pin) | (1 << self.clock_pin)):
            raise ValueError("Two-wire data and clock must be open drain")


class Engine:
    fifo_depth = 4

    def __init__(self, config):
        self.enabled = False
        self.tx_fifo = deque()
        self.rx_fifo = deque()
        self.configure(config)
        self.enabled = True

    def configure(self, config):
        if self.enabled:
            raise RuntimeError("Disable engine before configuration")
        self.config = config
        self.frontend = Frontend()
        self.rx = ShiftRXCount(config.lsb_first)
        self.tx = ShiftTX(config.lsb_first)
        self.timer = TimedSample(config.period, config.validate_start, config.validate_stop)
        self.guardian = Guardian(config.open_drain, config.watchdog)
        self.exchange = ByteExchange(config.address, config.ack_address, config.ack_data)
        self.active = False
        self.pending = None
        self.exchange.clear()
        self.pending_bit = 0
        self.cycle = 0
        self.faults = set()

    def push_tx(self, byte):
        if not 0 <= byte <= 255:
            raise ValueError("TX byte outside range")
        if len(self.tx_fifo) == self.fifo_depth:
            raise OverflowError("TX FIFO full")
        self.tx_fifo.append(byte)

    def pop_rx(self):
        return self.rx_fifo.popleft() if self.rx_fifo else None

    def _load_tx(self):
        if not self.tx_fifo:
            self.faults.add("tx_underflow")
        self.tx.load(self.tx_fifo.popleft() if self.tx_fifo else self.config.fill)

    def _release(self):
        self.active = False
        self.rx.clear()
        self.tx.value = 0
        self.tx.remaining = 0
        self.timer.stop()
        self.pending = None
        self.exchange.clear()

    def step(self, pins, reset=False, abort=False, requests=None):
        cfg = self.config
        edge = self.frontend.step(pins)
        fires = []
        events = []
        byte = None
        previous_pending = self.pending
        sampled_bit = self.pending_bit if previous_pending == "sample" else bool(edge.level & (1 << cfg.rx_pin))
        self.pending = None
        framed_level = not bool(edge.level & (1 << cfg.frame_pin))
        release = cfg.frame == "level" and self.active and not framed_level
        acquire = bool(edge.falling & (1 << cfg.frame_pin)) and not self.active
        if cfg.frame == "two_wire":
            clock_high = bool(edge.level & (1 << cfg.clock_pin))
            clock_was_high = clock_high and not bool(edge.rising & (1 << cfg.clock_pin))
            acquire = clock_was_high and bool(edge.falling & (1 << cfg.rx_pin))
            release = clock_was_high and bool(edge.rising & (1 << cfg.rx_pin))
        progress_mask = 1 << cfg.rx_pin
        if cfg.sample == "rising":
            progress_mask |= 1 << cfg.clock_pin
        if cfg.frame != "two_wire":
            progress_mask |= 1 << cfg.frame_pin
        progress = bool((edge.rising | edge.falling) & progress_mask)
        timed_out = self.guardian.tick(self.active, acquire, progress, abort)
        if reset or not self.enabled or abort or release or timed_out:
            self._release()
            fires += ["FRAME_RELEASE", "RESET_COUNTER"]
            if reset:
                self.frontend = Frontend()
                self.guardian = Guardian(cfg.open_drain, cfg.watchdog)
                self.tx_fifo.clear()
                self.rx_fifo.clear()
                self.faults.clear()
        elif acquire:
            self.active = True
            self.rx.clear()
            self.exchange.clear()
            fires += ["FRAME_ACQUIRE", "RESET_COUNTER"]
            events.append("frame_start")
            if cfg.sample == "timer":
                self.timer.start()
            if cfg.transmit and not cfg.exchange:
                self._load_tx()
                fires.append("SHIFT_TX_LOAD")
        elif self.active:
            if cfg.exchange:
                exchange_fires, exchange_events, byte = self.exchange.tick(
                    bool(edge.rising & (1 << cfg.clock_pin)), bool(edge.falling & (1 << cfg.clock_pin)),
                    bool(edge.level & (1 << cfg.rx_pin)), self.rx, self.tx,
                    self.rx_fifo, self.tx_fifo, self.fifo_depth)
                fires += exchange_fires
                events += exchange_events
            if cfg.sample == "timer":
                self.pending = self.timer.tick(bool(edge.level & (1 << cfg.rx_pin)))
                self.pending_bit = bool(edge.level & (1 << cfg.rx_pin))
                if self.pending:
                    fires.append("TIMED_SAMPLE")
            sample = not cfg.exchange and ((cfg.sample == "rising" and bool(edge.rising & (1 << cfg.clock_pin))) or previous_pending == "sample")
            if sample:
                byte = self.rx.fire(sampled_bit)
                fires.append("SHIFT_RX_COUNT")
                if byte is not None:
                    events.append("byte_complete")
                    if cfg.validate_stop:
                        self.assembled = byte
                    elif len(self.rx_fifo) < self.fifo_depth:
                        self.rx_fifo.append(byte)
                    else:
                        self.faults.add("rx_overflow")
            if previous_pending in ("invalid_start", "invalid_stop", "stop_valid"):
                if previous_pending == "stop_valid" and len(self.rx_fifo) < self.fifo_depth:
                    self.rx_fifo.append(self.assembled)
                elif previous_pending != "stop_valid":
                    self.faults.add(previous_pending)
                else:
                    self.faults.add("rx_overflow")
                self._release()
                fires += ["FRAME_RELEASE", "RESET_COUNTER"]
            if cfg.transmit and not cfg.exchange and edge.falling & (1 << cfg.clock_pin):
                if self.tx.fire():
                    events.append("tx_complete")
                    self._load_tx()
                fires.append("SHIFT_TX")
        generated = [Request(0, cfg.tx_pin, self.tx.bit)] if self.active and cfg.transmit else []
        ownership = {0: 1 << cfg.tx_pin} if self.active else {}
        if cfg.exchange:
            generated = []
            ownership = {0: (1 << cfg.tx_pin) | (1 << cfg.clock_pin)} if self.active else {}
            if self.active and self.exchange.drive_low:
                generated.append(Request(0, cfg.tx_pin, 0))
            if self.active and self.exchange.stretch:
                generated.append(Request(0, cfg.clock_pin, 0))
        requested = generated if requests is None else requests
        raw_kill = reset or not self.enabled or abort or (cfg.frame == "level" and bool(pins & (1 << cfg.frame_pin)))
        data, oe = self.guardian.apply(requested, ownership, raw_kill)
        self.cycle += 1
        return {"cycle": self.cycle, "events": events, "fires": fires, "levels": edge.level,
                "rising": edge.rising, "falling": edge.falling, "rx_value": self.rx.value,
                "rx_count": self.rx.count, "byte": byte, "tx_value": self.tx.value,
                "tx_remaining": self.tx.remaining, "active": self.active, "data": data,
                "oe": oe, "faults": sorted(self.faults | self.guardian.faults)}
