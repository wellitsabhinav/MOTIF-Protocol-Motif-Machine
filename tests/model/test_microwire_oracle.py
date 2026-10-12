import pytest

from tools.byte_exchange_falsification import oracle


def test_independent_read_format():
    command, response = oracle(0, 0xa55a)
    assert command == [1, 1, 0, 0, 0, 0, 0, 0, 0]
    assert response == [1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0]
    assert oracle(63, 65535) == ([1, 1, 0] + [1] * 6, [1] * 16)


@pytest.mark.parametrize("address,word", [(-1, 0), (64, 0), (0, -1), (0, 65536)])
def test_oracle_rejects_outside_bounded_scope(address, word):
    with pytest.raises(ValueError):
        oracle(address, word)
