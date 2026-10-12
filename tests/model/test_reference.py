import random

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
