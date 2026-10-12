import random
from dataclasses import replace

from motif import Engine
from motif.protocols.spi import target
from reference.sequential_spi import SequentialSPI
from tests.drivers import Wires


def test_sequential_reference_same_wire_transactions():
    rng = random.Random(908)
    parallel, sequential = Engine(target()), SequentialSPI(target())
    motif_wire, reference_wire = Wires(parallel), Wires(sequential)
    for frame in range(150):
        rx, tx = rng.randrange(256), rng.randrange(256)
        assert motif_wire.spi(rx, tx) == reference_wire.spi(rx, tx) == tx, frame
        assert parallel.pop_rx() == sequential.pop_rx() == rx, frame
    assert sequential.issued == 150 * 19
    assert sequential.max_backlog == 1


def test_reference_matches_abort_timeout_and_reset_contract():
    for implementation in (Engine, SequentialSPI):
        engine = implementation(replace(target(), watchdog=32))
        wire = Wires(engine)
        wire.spi(0x55, 0xAA)
        engine.push_tx(0x11)
        engine.push_tx(0x22)
        wire.hold(p0=0)
        engine.step(wire.pins, abort=True)
        wire.hold(8)
        assert not engine.active
        assert engine.pop_rx() == 0x55
        assert list(engine.tx_fifo) == [0x22]
        wire.hold(p0=1)
        wire.hold(p0=0)
        assert engine.active
        wire.hold(40)
        assert not engine.active and not wire.trace[-1]["oe"]
        assert "timeout" in wire.trace[-1]["faults"]
        engine.step(wire.pins, reset=True)
        assert not engine.rx_fifo and not engine.tx_fifo and not engine.active
