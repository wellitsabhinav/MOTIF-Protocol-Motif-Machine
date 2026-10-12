"""Independent timing/ownership assertions, including the malformed contract."""
import json
from pathlib import Path

from tools.unseen_protocol import oracle, pulse_intervals, check_selection


def example(interrupted=False, delay=30, width=120, extra_pin=False):
    workload = json.loads(Path('experiments/exchange_decomposition/third_workload.json').read_text())
    # One sample per microsecond keeps this oracle unit test small. Production
    # qualification retains the selected 20ns core period without rescaling.
    workload['core_period_ns'] = 1000
    controller = [1]*1000 + ([0]*200+[1]+[0]*300 if interrupted else [0]*500) + [1]*1000
    low = [False]*len(controller)
    start = (1501 if interrupted else 1500)+delay
    low[start:start+width] = [True]*width
    oe = [(4 if bit else 0) | (2 if extra_pin else 0) for bit in low]
    return oracle(controller, low, [0]*len(low), oe, workload, {'expected_presence': 0 if interrupted else 1})


def test_oracle_measures_continuous_pulses_and_independent_timing():
    assert pulse_intervals([False, True, True, False, True]) == [(1, 3), (4, 5)]
    assert example()['passed']
    assert not example(delay=14)['passed']
    assert not example(width=241)['passed']
    assert not example(extra_pin=True)['passed']


def test_oracle_rejects_combining_two_short_lows():
    result = example(interrupted=True)
    assert result['qualified_controller_releases_cycles'] == []
    assert result['errors'] == ['Expected 0 presence pulse(s), observed 1']


def test_selected_contract_is_immutable_and_refers_to_the_original_freeze():
    assert check_selection()['workload'] == 'one_wire_reset_presence_target'
