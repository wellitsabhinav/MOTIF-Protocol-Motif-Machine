from motif import Engine
from motif.protocols.i2c import target
from tests.i2c_driver import Bus


def test_first_bit_sample_detects_controller_holding_wrong_level():
    engine = Engine(target())
    bus = Bus(engine)
    bus.start()
    assert bus.write(0xA5)
    bus.hold(scl=1, sda=0)
    engine.push_tx(255)
    bus.hold(80)
    assert not engine.active and not bus.output["oe"]
    assert "data_mismatch" in bus.output["faults"]
    bus.stop()
    bus.start()
    assert bus.write(0xA4) and bus.write(85)
    assert engine.pop_rx() == 85
