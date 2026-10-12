import random

import pytest

from motif import Engine
from motif.motifs import ShiftRXCount
from motif.protocols.spi import target
from motif.protocols.uart import receiver
from tests.drivers import Wires


@pytest.mark.parametrize("byte", [0, 255, 85, 170])
def test_boundary_full_duplex(byte):
    engine = Engine(target())
    wire = Wires(engine)
    assert wire.spi(byte, byte ^ 255) == byte ^ 255
    assert engine.pop_rx() == byte
    assert not wire.trace[-1]["oe"]


@pytest.mark.parametrize("seed", [7, 41, 20261012])
def test_random_spi_without_global_reset(seed):
    rng = random.Random(seed)
    engine = Engine(target())
    wire = Wires(engine)
    for frame in range(200):
        rx, tx = rng.randrange(256), rng.randrange(256)
        assert wire.spi(rx, tx) == tx, (seed, frame)
        assert engine.pop_rx() == rx, (seed, frame)


@pytest.mark.parametrize("byte", [0, 255, 85, 170, 49])
def test_uart(byte):
    engine = Engine(receiver(32))
    wire = Wires(engine)
    wire.uart(byte)
    assert engine.pop_rx() == byte
    assert not engine.active


def test_uart_bad_stop_and_recovery():
    engine = Engine(receiver(32))
    wire = Wires(engine)
    wire.uart(85, stop=0)
    assert engine.pop_rx() is None
    assert "invalid_stop" in engine.faults
    wire.uart(170)
    assert engine.pop_rx() == 170


def test_atomic_terminal_count():
    actor = ShiftRXCount()
    for bit in [1] * 7:
        assert actor.fire(bit) is None
    assert actor.fire(1) == 255
    assert actor.count == 0


def test_config_requires_disabled_engine():
    engine = Engine(target())
    with pytest.raises(RuntimeError):
        engine.configure(receiver())


def test_partial_frame_abort_and_rearm():
    engine = Engine(target())
    wire = Wires(engine)
    wire.hold(p0=1, p1=0)
    wire.hold(p0=0)
    for _ in range(3):
        wire.hold(p1=1, p2=1)
        wire.hold(p1=0)
    engine.step(wire.pins, abort=True)
    wire.hold(p0=1)
    assert engine.pop_rx() is None
    assert wire.spi(85, 170) == 170
    assert engine.pop_rx() == 85


def test_fifo_bounds_and_reset():
    engine = Engine(target())
    for byte in range(4):
        engine.push_tx(byte)
    with pytest.raises(OverflowError):
        engine.push_tx(4)
    trace = engine.step(255, reset=True)
    assert not trace["oe"] and not engine.tx_fifo and not engine.rx_fifo
