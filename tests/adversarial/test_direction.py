from motif import Engine
from motif.guardian import Request
from motif.protocols.uart import receiver
from tests.drivers import Wires


def test_receive_only_configuration_does_not_grant_output_ownership():
    engine = Engine(receiver(32))
    wire = Wires(engine)
    wire.hold(p2=1)
    wire.hold(p2=0)
    assert engine.active
    trace = engine.step(wire.pins, requests=[Request(0, 3, 1)])
    assert not trace["oe"] and "ownership" in trace["faults"]
