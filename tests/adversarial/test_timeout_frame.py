from dataclasses import replace

from motif import Engine
from motif.protocols.spi import target
from tests.drivers import Wires


def test_timeout_does_not_reacquire_stale_asserted_frame():
    engine = Engine(replace(target(), watchdog=16))
    wire = Wires(engine)
    wire.hold(p0=1, p1=0)
    wire.hold(p0=0)
    wire.hold(100)
    assert not engine.active
    assert not wire.trace[-1]["oe"]
    wire.hold(p0=1)
    wire.hold(p0=0)
    assert engine.active
