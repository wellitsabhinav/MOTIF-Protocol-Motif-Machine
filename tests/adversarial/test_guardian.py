import random

from motif import Engine
from motif.guardian import Guardian, Request
from motif.protocols.spi import target
from tests.drivers import Wires


def test_stale_oe_is_suppressed_on_raw_deselection():
    engine = Engine(target())
    wires = Wires(engine)
    wires.hold(p0=1, p1=0)
    wires.hold(p0=0)
    assert engine.active
    assert not engine.step(255, requests=[Request(0, 3, 1)])["oe"]


def test_random_executor_requests():
    rng = random.Random(141)
    guard = Guardian(open_drain=255)
    for _ in range(5000):
        pin, bit, owned = rng.randrange(8), rng.randrange(2), rng.randrange(2)
        data, oe = guard.apply([Request(0, pin, bit)], {0: (1 << pin) if owned else 0})
        assert not data
        assert not oe or (owned and not bit)


def test_conflicting_requests_release_pad():
    guard = Guardian()
    assert not guard.apply([Request(0, 2, 0), Request(1, 2, 1), Request(2, 2, 0)], {0: 4, 1: 4, 2: 4})[1]


def test_timeout_cannot_be_bypassed_by_requests():
    guard = Guardian(watchdog=4)
    for _ in range(4):
        guard.tick(True)
    assert guard.tripped
    assert not guard.apply([Request(0, 1, 0)], {0: 2})[1]
    guard.tick(True, acquire=True, progress=True)
    assert guard.apply([Request(0, 1, 0)], {0: 2})[1]
