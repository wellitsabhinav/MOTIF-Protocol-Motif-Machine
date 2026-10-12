from motif import Engine
from motif.protocols.timed_stream import receiver
from tests.drivers import Wires


def test_external_frame_timed_stream():
    engine = Engine(receiver(16))
    wires = Wires(engine)
    wires.hold(p0=1)
    wires.hold(4, p0=0, p2=1)
    for byte in [85, 170, 255]:
        for index in range(7, -1, -1):
            wires.hold(16, p2=(byte >> index) & 1)
    wires.hold(8, p0=1)
    assert [engine.pop_rx() for _ in range(3)] == [85, 170, 255]
    assert not engine.active
