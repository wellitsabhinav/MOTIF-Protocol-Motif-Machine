import random

import pytest

from motif import Engine
from motif.guardian import Request
from motif.protocols.i2c import target
from tests.i2c_driver import Bus


@pytest.mark.parametrize("byte", [0, 255, 85, 170])
def test_i2c_write_read_repeated_start(byte):
    engine = Engine(target())
    bus = Bus(engine)
    bus.start()
    assert bus.write(0xA4)
    assert bus.write(byte)
    assert engine.pop_rx() == byte
    engine.push_tx(byte ^ 255)
    bus.start()
    assert bus.write(0xA5)
    assert bus.read(ack=False) == byte ^ 255
    bus.stop()
    assert not engine.active and not bus.output["oe"]


@pytest.mark.parametrize("seed", [19, 20261012])
def test_i2c_random_back_to_back(seed):
    rng = random.Random(seed)
    engine = Engine(target())
    bus = Bus(engine)
    for transaction in range(80):
        payload = [rng.randrange(256) for _ in range(3)]
        bus.start()
        assert bus.write(0xA4), (seed, transaction)
        for byte in payload:
            assert bus.write(byte), (seed, transaction)
        assert [engine.pop_rx() for _ in payload] == payload, (seed, transaction)
        bus.stop()
        for byte in payload:
            engine.push_tx(byte)
        bus.start()
        assert bus.write(0xA5)
        assert [bus.read(ack=index < 2) for index in range(3)] == payload, (seed, transaction)
        bus.stop()


def test_wrong_address_nack_and_recovery():
    engine = Engine(target())
    bus = Bus(engine)
    bus.start()
    assert not bus.write(0xA6)
    assert not bus.write(255)
    bus.stop()
    bus.start()
    assert bus.write(0xA4) and bus.write(85)
    assert engine.pop_rx() == 85


@pytest.mark.parametrize("options,address_ack,data_ack", [({"ack_address": False}, False, False), ({"ack_data": False}, True, False)])
def test_configured_nack(options, address_ack, data_ack):
    bus = Bus(Engine(target(**options)))
    bus.start()
    assert bus.write(0xA4) == address_ack
    assert bus.write(85) == data_ack
    assert bus.engine.pop_rx() is None
    bus.stop()


@pytest.mark.parametrize("termination", ["stop", "start"])
@pytest.mark.parametrize("bits", [0, 1, 4, 7])
def test_partial_abort_rearms(termination, bits):
    engine = Engine(target())
    bus = Bus(engine)
    bus.start()
    for _ in range(bits):
        bus.hold(scl=0, sda=1)
        bus.hold(scl=1)
    getattr(bus, termination)()
    if termination == "stop":
        bus.start()
    assert bus.write(0xA4)
    assert bus.write(170)
    assert engine.pop_rx() == 170


@pytest.mark.parametrize("setup_cycles", [13, 63])
@pytest.mark.parametrize("byte", [85, 170])
def test_clock_stretch_until_fifo_data_available(setup_cycles, byte):
    engine = Engine(target(setup_cycles=setup_cycles))
    bus = Bus(engine)
    bus.start()
    assert bus.write(0xA5)
    assert bus.output["oe"] & 2
    bus.hold(200, scl=1)
    assert bus.output["oe"] & 2
    engine.push_tx(byte)
    bus.hold(1, scl=1)
    assert bus.output["oe"] & 2, "SCL must remain stretched while the first data bit settles"
    assert bool(bus.output["oe"] & 4) == (not bool(byte & 128))
    for _ in range(setup_cycles - 1):
        bus.hold(1)
        assert bus.output["oe"] & 2
    bus.hold(8)
    assert not bus.output["oe"] & 2
    assert bus.read() == byte
    bus.stop()


def test_controller_low_and_opt_in_timeout():
    engine = Engine(target(watchdog=64))
    bus = Bus(engine)
    bus.start()
    assert bus.write(0xA4)
    bus.hold(80, scl=0)
    assert "timeout" in bus.output["faults"] and not bus.output["oe"]
    bus.stop()
    bus.start()
    assert bus.write(0xA4) and bus.write(0)
    assert engine.pop_rx() == 0


def test_full_receive_fifo_nacks_without_corruption():
    engine = Engine(target())
    bus = Bus(engine)
    bus.start()
    assert bus.write(0xA4)
    for value in range(4):
        assert bus.write(value)
    assert not bus.write(99)
    assert [engine.pop_rx() for _ in range(4)] == list(range(4))


def test_executor_cannot_drive_sda_high():
    engine = Engine(target())
    bus = Bus(engine)
    bus.start()
    trace = engine.step(249, requests=[Request(0, 2, 1)])
    assert not trace["oe"] & 4 and "drive_high" in trace["faults"]


@pytest.mark.parametrize("termination", ["start", "stop"])
def test_partial_data_byte_termination(termination):
    engine = Engine(target())
    bus = Bus(engine)
    bus.start()
    assert bus.write(0xA4)
    for bit in [1, 0, 1, 0]:
        bus.hold(scl=0, sda=bit)
        bus.hold(scl=1)
    getattr(bus, termination)()
    if termination == "stop":
        bus.start()
    assert bus.write(0xA4) and bus.write(85)
    assert engine.pop_rx() == 85
    assert engine.pop_rx() is None


def test_100khz_cycle_schedule_and_long_idle():
    engine = Engine(target())
    bus = Bus(engine, spacing=250)
    bus.start()
    assert bus.write(0xA4) and bus.write(170)
    bus.hold(2000, scl=0)
    assert engine.active and "timeout" not in bus.output["faults"]
    bus.stop()
    assert engine.pop_rx() == 170


def test_reset_mid_address_then_new_transaction():
    engine = Engine(target())
    bus = Bus(engine)
    bus.start()
    bus.hold(sda=1, scl=0)
    bus.hold(scl=1)
    bus.output = engine.step(255, reset=True)
    bus.stop()
    bus.start()
    assert bus.write(0xA4) and bus.write(0)
    assert engine.pop_rx() == 0


def test_explicit_abort_of_stretch_and_automatic_rearm():
    engine = Engine(target())
    bus = Bus(engine)
    bus.start()
    assert bus.write(0xA5)
    assert bus.output["oe"] & 2
    bus.output = engine.step(249, abort=True)
    assert not bus.output["oe"]
    bus.stop()
    bus.start()
    assert bus.write(0xA4) and bus.write(255)
    assert engine.pop_rx() == 255
