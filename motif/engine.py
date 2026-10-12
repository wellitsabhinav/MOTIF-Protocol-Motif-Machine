from collections import deque
from dataclasses import dataclass

from .events import Frontend
from .guardian import Guardian, Request
from .motifs import ShiftRXCount, ShiftTX, TimedSample
from .motifs.transaction import Transaction, FieldShift
from .transaction import validate, Entry, HALT
from .pad_history import PadHistory


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
    program: tuple = ()
    frame_active_high: bool = False
    hold_clock: bool = False
    pad_timing_check: bool = False

    @property
    def exchange(self):
        return bool(self.program)

    def __post_init__(self):
        integer_fields = ("frame_pin", "clock_pin", "rx_pin", "tx_pin", "period", "open_drain", "watchdog", "fill")
        boolean_fields = ("transmit", "lsb_first", "validate_start", "validate_stop", "frame_active_high", "hold_clock", "pad_timing_check")
        if any(type(getattr(self, name)) is not int for name in integer_fields) or any(type(getattr(self, name)) is not bool for name in boolean_fields):
            raise ValueError("Configuration must use bounded integer and Boolean fields")
        if self.frame not in ("level", "falling", "two_wire") or self.sample not in ("rising", "timer"):
            raise ValueError("Unsupported event source")
        if any(not 0 <= pin < 8 for pin in (self.frame_pin, self.clock_pin, self.rx_pin, self.tx_pin)):
            raise ValueError("Pin outside eight-pin engine")
        if not 2 <= self.period <= 65535 or not 0 <= self.watchdog <= 65535:
            raise ValueError("Timer outside sixteen-bit range")
        if not 0 <= self.fill <= 255 or not 0 <= self.open_drain <= 255:
            raise ValueError("Byte configuration outside range")
        if type(self.program) is not tuple:
            raise ValueError("Program must use immutable bounded entries")
        if self.program:
            validate(self.program)
        if self.transmit and not self.exchange and self.tx_pin in (self.rx_pin, self.clock_pin, self.frame_pin):
            raise ValueError("Target output must not alias protected protocol inputs")
        if self.exchange and self.clock_pin == self.rx_pin:
            raise ValueError("Transaction requires distinct clock and data pins")
        if self.frame == "two_wire" and not self.exchange:
            raise ValueError("Two-wire framing requires byte exchange")
        if self.exchange and self.rx_pin == self.tx_pin and not self.open_drain & (1 << self.rx_pin):
            raise ValueError("Shared data output must be open drain")
        if self.exchange and self.tx_pin in (self.clock_pin, self.frame_pin):
            raise ValueError("Data output must not alias clock or frame input")
        if self.hold_clock and not self.open_drain & (1 << self.clock_pin):
            raise ValueError("Hold output must be open drain")


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
        self.rx = FieldShift(config.lsb_first) if config.exchange else ShiftRXCount(config.lsb_first)
        self.tx = ShiftTX(config.lsb_first)
        self.timer = TimedSample(config.period, config.validate_start, config.validate_stop)
        self.guardian = Guardian(config.open_drain, config.watchdog)
        self.exchange = Transaction(config.program or (Entry(HALT).encode(),) * 16, config.transmit)
        self.pad_history = PadHistory()
        self.last_oe = 0
        self.active = False
        self.pending = None
        self.exchange.clear()
        self.pending_bit = 0
        self.pending_timer_start = False
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
        self.pending_timer_start = False

    def step(self, pins, reset=False, abort=False, requests=None):
        cfg = self.config
        edge = self.frontend.step(pins)
        own = self.pad_history.step(int(bool(self.last_oe & (1 << cfg.clock_pin))) | (int(bool(self.last_oe & (1 << cfg.rx_pin))) << 1))
        fires = []
        events = []
        byte = None
        previous_pending = self.pending
        previous_timer_start = self.pending_timer_start
        self.pending_timer_start = False
        sampled_bit = self.pending_bit if previous_pending == "sample" else bool(edge.level & (1 << cfg.rx_pin))
        self.pending = None
        framed_level = bool(edge.level & (1 << cfg.frame_pin)) == cfg.frame_active_high
        release = cfg.frame == "level" and self.active and not framed_level
        frame_edge = edge.rising if cfg.frame == "level" and cfg.frame_active_high else edge.falling
        acquire = bool(frame_edge & (1 << cfg.frame_pin)) and not self.active
        if cfg.frame == "two_wire":
            clock_high = bool(edge.level & (1 << cfg.clock_pin))
            clock_was_high = clock_high and not bool(edge.rising & (1 << cfg.clock_pin))
            acquire = clock_was_high and bool(edge.falling & (1 << cfg.rx_pin)) and not ((own.current | own.previous) & 2)
            release = clock_was_high and bool(edge.rising & (1 << cfg.rx_pin))
        progress_mask = 1 << cfg.rx_pin
        if cfg.sample == "rising":
            progress_mask |= 1 << cfg.clock_pin
        if cfg.frame != "two_wire":
            progress_mask |= 1 << cfg.frame_pin
        progress = bool((edge.rising | edge.falling) & progress_mask)
        pad_timing = False
        if cfg.exchange:
            progress = bool((edge.rising | edge.falling) & (1 << cfg.clock_pin)) and not ((own.current | own.previous) & 1)
            own_changes = own.current ^ own.previous
            self_clock_fall = bool(edge.falling & (1 << cfg.clock_pin)) and bool(own_changes & own.current & 1)
            self_data_edge = bool((edge.rising | edge.falling) & (1 << cfg.rx_pin)) and bool(own_changes & 2)
            clock_stable_high = bool(edge.level & (1 << cfg.clock_pin)) and not bool(edge.rising & (1 << cfg.clock_pin))
            pad_timing = cfg.pad_timing_check and self.active and not self.guardian.tripped and (self_clock_fall or (clock_stable_high and self_data_edge))
            if pad_timing:
                self.faults.add("pad_timing")
                events.append("pad_timing_fault")
        timed_out = self.guardian.tick(self.active, acquire, progress, abort or pad_timing)
        if reset or not self.enabled or abort or release or timed_out:
            self._release()
            fires += ["FRAME_RELEASE", "RESET_COUNTER"]
            if reset:
                self.frontend = Frontend()
                self.guardian = Guardian(cfg.open_drain, cfg.watchdog)
                self.pad_history = PadHistory()
                self.last_oe = 0
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
                    self.rx_fifo, self.tx_fifo, self.fifo_depth, previous_pending == "sample", self.pending_bit)
                fires += exchange_fires
                events += exchange_events
                if set(exchange_events) & {"data_mismatch", "composition_fault", "frame_terminate"}:
                    self.faults.update(set(exchange_events) & {"data_mismatch", "composition_fault"})
                    self._release()
                    fires += ["FRAME_RELEASE", "RESET_COUNTER"]
                self.pending_timer_start = self.active and "turnaround_begin" in exchange_events
                if previous_pending == "sample" and cfg.sample != "timer":
                    self.timer.stop()
            if previous_timer_start and cfg.exchange and self.active:
                self.timer.start()
            elif cfg.sample == "timer" or (cfg.exchange and self.exchange.waiting_timer):
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
        ownership = {0: 1 << cfg.tx_pin} if self.active and cfg.transmit else {}
        if cfg.exchange:
            generated = []
            ownership = {0: (1 << cfg.tx_pin) | ((1 << cfg.clock_pin) if cfg.transmit and cfg.hold_clock else 0)} if self.active else {}
            if self.active and self.exchange.drive_enable and (not cfg.open_drain & (1 << cfg.tx_pin) or not self.exchange.drive_value):
                generated.append(Request(0, cfg.tx_pin, int(self.exchange.drive_value)))
            if self.active and self.exchange.hold:
                generated.append(Request(0, cfg.clock_pin, 0))
        requested = generated if requests is None else requests
        raw_kill = reset or not self.enabled or abort or (cfg.frame == "level" and bool(pins & (1 << cfg.frame_pin)) != cfg.frame_active_high)
        data, oe = self.guardian.apply(requested, ownership, raw_kill)
        self.last_oe = oe
        self.cycle += 1
        return {"cycle": self.cycle, "events": events, "fires": fires, "levels": edge.level,
                "rising": edge.rising, "falling": edge.falling, "rx_value": self.rx.value,
                "rx_count": self.rx.count, "byte": byte, "tx_value": self.tx.value,
                "tx_remaining": self.tx.remaining, "active": self.active, "data": data,
                "oe": oe, "faults": sorted(self.faults | self.guardian.faults)}
