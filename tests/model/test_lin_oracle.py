"""Independent tiny electrical examples and mock public LIN acceptance traces."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from tools.lin_oracle import FifoSample, HostRead, LinContract, evaluate, reference


# Four observations per nominal cell, eleven cells per receiver threshold.
C = LinContract(bit_cycles=4, break_observations=44, posttraffic_high_cycles=8)


def wire(*runs):
    return [level for level, count in runs for _ in range(count)]


def byte(value=0x55, stop=1):
    return wire((0, 4), *((value >> bit & 1, 4) for bit in range(8)), (stop, 4))


def prefix(low=52, value=0x55, stop=1, delimiter=5):
    return wire((0, low), (1, delimiter)) + byte(value, stop)


def evaluate_mock(line, acceptances=(), read_values=(0x55,), oe_at=None, cuts=()):
    """Public FIFO mock; receives only externally chosen acceptance timestamps."""
    traffic_end = len(line)
    drain_start = traffic_end + C.posttraffic_high_cycles
    # A token appearing on the inclusive latest cycle is only readable PRE-edge
    # on the next cycle.  Leave that single observation before the first pop.
    reads = [HostRead(drain_start + 1 + index, value) for index, value in enumerate(read_values)]
    complete = line + [1] * (C.posttraffic_high_cycles + len(reads) + 2)
    rows = []
    queue = []
    for cycle in range(len(complete)):
        if drain_start + 1 <= cycle < drain_start + 1 + len(reads) and queue:
            queue.pop(0)
        for accepted_cycle, value in acceptances:
            if cycle == accepted_cycle:
                queue.append(value)
        rows.append(FifoSample(cycle, len(queue), queue[0] if queue else None))
    oe = [0] * len(complete)
    if oe_at is not None:
        oe[oe_at] = 0x80  # Check all outputs, not only the receive pad.
    return evaluate(complete, cuts, C, rows, reads, oe, traffic_end)


def codes(result):
    return {error.code for error in result.errors}


def test_independent_centers_and_latency_window():
    line = [1] * 3 + prefix()
    (token,) = reference(line, (), C)
    assert token.value == 0x55
    assert (token.break_start, token.break_end, token.byte_start) == (3, 55, 60)
    assert (token.stop_start, token.stop_end) == (96, 100)
    assert (token.earliest, token.latest) == (96, 108)


@pytest.mark.parametrize("low, count", [(43, 0), (44, 1), (45, 1), (48, 1), (80, 1)])
def test_continuous_threshold_not_master_generation_minimum(low, count):
    assert len(reference(prefix(low), (), C)) == count


@pytest.mark.parametrize("high", [1, 2, 5])
def test_observable_high_splits_break_and_cannot_accumulate(high):
    line = wire((0, 24), (1, high), (0, 24), (1, 5)) + byte()
    assert reference(line, (), C) == ()


def test_ordinary_zero_and_sync_without_break():
    assert reference(byte(0) + [1] * 5 + byte(), (), C) == ()
    assert reference(byte(), (), C) == ()


@pytest.mark.parametrize("value, stop", [(0x54, 1), (0xAA, 1), (0, 1), (0x55, 0)])
def test_wrong_sync_or_low_stop_clears_qualification(value, stop):
    assert reference(prefix(value=value, stop=stop), (), C) == ()


def test_high_pulse_away_from_data_center_does_not_make_wrong_byte_sync():
    line = prefix(value=0x54)
    first_data_start = 52 + 5 + 4
    line[first_data_start] = 1  # One observation, not the first-data center.
    assert reference(line, (), C) == ()


def test_valid_start_sample_required():
    line = prefix()
    line[52 + 5 + 2] = 1
    assert reference(line, (), C) == ()


def test_no_new_delimiter_or_upper_bound_requirement():
    assert len(reference(prefix(low=1000, delimiter=1), (), C)) == 1


def test_pending_byte_replaced_by_new_separated_break():
    line = wire((0, 52), (1, 5)) + prefix()
    (token,) = reference(line, (), C)
    assert (token.break_start, token.byte_start) == (57, 114)


def test_wrong_byte_then_fresh_break_accepts_only_fresh_header():
    first = prefix(value=0) + [1] * 8
    (token,) = reference(first + prefix(), (), C)
    assert token.break_start == len(first)


def test_wrong_byte_does_not_qualify_later_sync_without_fresh_break():
    assert reference(prefix(value=0) + [1] * 8 + byte(), (), C) == ()


def test_new_qualifying_low_after_a_split_false_break():
    false = wire((0, 24), (1, 1), (0, 24), (1, 5)) + byte() + [1] * 8
    (token,) = reference(false + prefix(), (), C)
    assert token.break_start == len(false)


def test_back_to_back_tokens_use_distinct_stops():
    first = prefix() + [1] * 8
    tokens = reference(first + prefix(), (), C)
    assert len(tokens) == 2
    assert tokens[1].stop_start - tokens[0].stop_start == len(first)


def test_lifecycle_cuts_split_held_low_and_cancel_pending_sync():
    assert reference(prefix(), [32], C) == ()
    assert reference(prefix(), [52 + 5 + 4], C) == ()
    assert reference(prefix(), [52], C) == ()  # Release belongs to new epoch.
    line = prefix() + [1] * 8 + prefix()
    tokens = reference(line, [32], C)
    assert len(tokens) == 1 and tokens[0].epoch == 1


def test_unreleased_break_and_unobserved_stop_have_no_token():
    assert reference([0] * 80, (), C) == ()
    assert reference(prefix()[:-3], (), C) == ()


@pytest.mark.parametrize("cycle", [93, 105])
def test_public_token_at_each_window_endpoint_passes(cycle):
    # With no initial HIGH: byte start57, stop begins93, latest105.
    result = evaluate_mock(prefix(), [(cycle, 0x55)])
    assert result.passed, result.errors
    assert result.to_dict()["passed"] is True


@pytest.mark.parametrize("cycle, code", [(92, "early_token"), (106, "late_token")])
def test_public_token_outside_window_fails(cycle, code):
    assert code in codes(evaluate_mock(prefix(), [(cycle, 0x55)]))


def test_missing_acceptance_and_empty_mandatory_read_fail():
    result = evaluate_mock(prefix(), read_values=(None,))
    assert {"missing_token", "missing_read"} <= codes(result)


def test_wrong_observed_token_fails_public_head_and_read():
    result = evaluate_mock(prefix(), [(95, 0x54)], read_values=(0x54,))
    assert {"wrong_public_head", "wrong_token"} <= codes(result)


def test_duplicate_acceptance_is_visible_even_after_one_correct_drain():
    result = evaluate_mock(prefix(), [(95, 0x55), (96, 0x55)])
    assert {"duplicate_token", "occupancy_remaining"} <= codes(result)


def test_count_jump_is_multiple_acceptance_not_one_event():
    result = evaluate_mock(prefix(), [(95, 0x55), (95, 0x55)])
    assert len(result.observed_acceptances) == 2
    assert "duplicate_token" in codes(result)


def test_spurious_acceptance_without_any_qualified_prefix():
    result = evaluate_mock(byte(), [(20, 0x55)], read_values=())
    assert {"spurious_token", "occupancy_remaining"} <= codes(result)


def test_receive_only_all_output_enables_are_checked():
    result = evaluate_mock(prefix(), [(95, 0x55)], oe_at=3)
    assert "output_enabled" in codes(result)


def test_host_read_must_match_preedge_endpoint():
    result = evaluate_mock(prefix(), [(95, 0x55)], read_values=(0x54,))
    assert {"host_read_mismatch", "wrong_token"} <= codes(result)


def test_count_without_expected_drain_read_cannot_pass():
    result = evaluate_mock(prefix(), [(95, 0x55)], read_values=())
    assert {"missing_read", "occupancy_remaining"} <= codes(result)


def test_successful_two_token_fifo_and_preedge_draining():
    first = prefix() + [1] * 8
    result = evaluate_mock(first + prefix(), [(95, 0x55), (95 + len(first), 0x55)],
                           read_values=(0x55, 0x55))
    assert result.passed, result.errors


def test_observations_cannot_omit_fifo_or_oe_cycles():
    line = [1] * 12
    result = evaluate(line, (), C, [FifoSample(0, 0)], (), [0], 4)
    assert {"incomplete_fifo_observation", "incomplete_oe_observation"} <= codes(result)


def test_unexplained_fifo_disappearance_fails():
    line = prefix() + [1] * 10
    rows = [FifoSample(cycle, int(cycle == 95), 0x55) for cycle in range(len(line))]
    result = evaluate(line, (), C, rows, (), [0] * len(line), len(prefix()))
    assert {"unexpected_fifo_loss", "missing_read"} <= codes(result)


def test_early_host_read_and_nonhigh_margin_fail():
    line = [1] * 4 + [0] + [1] * 7
    rows = [FifoSample(cycle, 0) for cycle in range(len(line))]
    result = evaluate(line, (), C, rows, [HostRead(8, None)], [0] * len(line), 4)
    assert {"host_read_timing", "nonhigh_margin"} <= codes(result)


def test_actual_selected_contract_and_modified_numeric_constant():
    path = Path(__file__).parents[2] / "experiments/temporal_qualification/unseen/selected_workload.json"
    selected = json.loads(path.read_text(encoding="utf-8"))
    assert LinContract.from_selection(selected) == LinContract()
    changed = deepcopy(selected)
    changed["bounded_electrical_scope"]["receiver_threshold_observations"] = 27499
    with pytest.raises(ValueError, match="receiver_threshold_observations"):
        LinContract.from_selection(changed)
    changed = deepcopy(selected)
    changed["host_and_oracle_inputs"]["posttraffic_high_cycles"] = 4999
    with pytest.raises(ValueError, match="posttraffic_high_cycles"):
        LinContract.from_selection(changed)


@pytest.mark.parametrize("line, cuts", [([0, 2], ()), ([0, 1], (-1,)), ([0, 1], (3,))])
def test_invalid_electrical_inputs_are_rejected(line, cuts):
    with pytest.raises(ValueError):
        reference(line, cuts, C)
