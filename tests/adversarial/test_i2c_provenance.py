from motif import Engine
from motif.guardian import Request
from motif.protocols.i2c import target
from tests.i2c_driver import Bus


def override(bus, requests, abort=False):
    pins = (255 & ~6) | ((bus.scl and not bool(bus.output["oe"] & 2)) << 1) | ((bus.sda and not bool(bus.output["oe"] & 4)) << 2)
    bus.output = bus.engine.step(pins, abort=abort, requests=requests)
    return bus.output


def test_buffered_self_start_cannot_reacquire_after_abort():
    engine = Engine(target())
    bus = Bus(engine)
    bus.start()
    assert bus.write(0xA4)
    bus.hold(scl=1, sda=1)
    override(bus, [Request(0, 2, 0)])
    override(bus, [Request(0, 2, 0)], abort=True)
    for _ in range(8):
        bus.hold(1)
        assert not engine.active and not bus.output["oe"]
    bus.start()
    assert bus.write(0xA4) and bus.write(85)
    assert engine.pop_rx() == 85


def test_self_clock_truncation_is_reported_and_releases():
    engine = Engine(target())
    bus = Bus(engine)
    bus.start()
    assert bus.write(0xA4)
    bus.hold(scl=1, sda=1)
    for _ in range(8):
        override(bus, [Request(0, 1, 0)])
    assert "pad_timing" in bus.output["faults"]
    assert not engine.active and not bus.output["oe"]


def test_own_sda_activity_cannot_reset_inactivity_watchdog():
    engine = Engine(target(watchdog=64))
    bus = Bus(engine)
    bus.start()
    assert bus.write(0xA4)
    bus.hold(scl=0, sda=1)
    for cycle in range(100):
        override(bus, [Request(0, 2, 0)] if (cycle // 4) % 2 else [])
    assert "timeout" in bus.output["faults"]
    assert not engine.active and not bus.output["oe"]
