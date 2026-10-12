import pytest

from motif import Config
from motif.guardian import Request


@pytest.mark.parametrize("parameters", [{"period": 3.5}, {"rx_pin": True}, {"watchdog": 65536}, {"transmit": 2}, {"address": -1}])
def test_configuration_has_a_bounded_encoding(parameters):
    with pytest.raises(ValueError):
        Config(**parameters)


@pytest.mark.parametrize("arguments", [(0, 8, 0), (8, 2, 0), (0, 2, 2)])
def test_request_cannot_address_nonexistent_pads(arguments):
    with pytest.raises(ValueError):
        Request(*arguments)
