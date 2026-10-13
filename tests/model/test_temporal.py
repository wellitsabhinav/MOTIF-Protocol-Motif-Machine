"""Independent duration expectations, not an RTL-shaped implementation copy."""
from collections import deque
from itertools import product

import pytest

from motif import Config, Engine
from motif.motifs.shift import ShiftTX
from motif.motifs.transaction import FieldShift, Transaction
from motif.transaction import (Entry, program, temporal_wait, delay_wait, WAIT, HALT,
                               RESPOND, HANDOFF, RX, DECIDE, TX, TIMER, RISING,
                               CHAIN, TEMPORAL, INTERRUPT_BRANCH, CONTINUE)


def machine(entries):
    return Transaction(program(entries)), FieldShift(), ShiftTX(), deque(), deque()


def step(parts, bit=0, **events):
    ex, rx, tx, rf, tf = parts
    return ex.tick(events.get("rising", False), events.get("falling", False), bit,
                   rx, tx, rf, tf, 4, events.get("settled", False), events.get("settled_bit", 0))


@pytest.mark.parametrize("level", [0, 1])
@pytest.mark.parametrize("threshold", [1, 2, 3, 8, 16])
def test_exact_observation_count_and_registered_completion(level, threshold):
    parts = machine([temporal_wait(level, threshold, next=1), Entry(HALT)])
    ex = parts[0]
    for count in range(1, threshold + 1):
        _, events, _ = step(parts, level)
        assert ex.pc == 0
        assert ex.temporal_count == count
        assert ex.temporal_done == (count == threshold)
        assert ("temporal_qualified" in events) == (count == threshold)
    step(parts, 1-level)
    assert ex.pc == 1 and not ex.temporal_started and not ex.temporal_done


def test_maximum_threshold_does_not_wrap():
    parts = machine([temporal_wait(0, 65535, next=1), Entry(HALT)])
    for _ in range(65534):
        step(parts)
    assert parts[0].temporal_count == 65534 and not parts[0].temporal_done
    step(parts)
    assert parts[0].temporal_count == 65535 and parts[0].temporal_done
    step(parts, 1)
    assert parts[0].pc == 1 and parts[0].temporal_count == 0


@pytest.mark.parametrize("partial", [1, 2, 3])
def test_false_observation_before_or_on_threshold_restarts(partial):
    parts = machine([temporal_wait(0, 4, next=1), Entry(HALT)])
    for _ in range(partial):
        step(parts)
    _, events, _ = step(parts, 1)
    assert "temporal_interrupt" in events
    assert parts[0].pc == 0 and parts[0].temporal_count == 0
    for _ in range(3):
        step(parts)
        assert not parts[0].temporal_done
    step(parts)
    assert parts[0].temporal_done


def test_multiple_one_observation_interruptions_do_not_accumulate():
    parts = machine([temporal_wait(0, 4, next=1), Entry(HALT)])
    for bit in [0, 0, 1, 0, 1, 0, 0, 0, 1]:
        step(parts, bit)
        assert not parts[0].temporal_done and parts[0].pc == 0
    assert parts[0].temporal_count == 0


def test_interruption_branch_requires_a_started_partial_interval():
    parts = machine([temporal_wait(0, 3, "branch", next=1, alternate=2), Entry(HALT), Entry(HALT)])
    for _ in range(100):
        assert "temporal_interrupt" not in step(parts, 1)[1]
        assert parts[0].pc == 0
    step(parts)
    assert "temporal_interrupt" in step(parts, 1)[1]
    assert parts[0].pc == 2 and parts[0].temporal_count == 0


def test_constant_true_delay_ignores_input_levels():
    parts = machine([delay_wait(4, next=1), Entry(HALT)])
    for bit in [0, 1, 0, 1]:
        assert "temporal_interrupt" not in step(parts, bit)[1]
    assert parts[0].temporal_done
    step(parts)
    assert parts[0].pc == 1


def test_two_temporal_entries_in_a_chain_are_deferred():
    parts = machine([delay_wait(1, next=1, chain=True), delay_wait(1, next=2), Entry(HALT)])
    step(parts)
    assert parts[0].temporal_done
    step(parts)
    assert parts[0].pc == 1 and parts[0].temporal_count == 0
    assert parts[0].executed_entries == [0]
    step(parts)
    assert parts[0].temporal_done and parts[0].temporal_count == 1
    step(parts)
    assert parts[0].pc == 2


def test_ordinary_chain_can_begin_qualification_on_the_same_observation():
    parts = machine([Entry(RESPOND, next=1, argument=3, flags=CHAIN), delay_wait(2, next=2), Entry(HALT)])
    step(parts)
    assert parts[0].executed_entries == [0, 1]
    assert parts[0].pc == 1 and parts[0].temporal_count == 1


def test_second_temporal_entry_after_four_actions_is_deferred_without_fifth_execution():
    parts = machine([delay_wait(1, next=1, chain=True),
                     Entry(CONTINUE, next=2, flags=CHAIN),
                     Entry(CONTINUE, next=3, flags=CHAIN),
                     Entry(CONTINUE, next=4, flags=CHAIN),
                     delay_wait(1, next=5), Entry(HALT)])
    step(parts)
    _, events, _ = step(parts)
    assert "composition_fault" not in events
    assert parts[0].executed_entries == [0, 1, 2, 3]
    assert parts[0].pc == 4 and parts[0].temporal_count == 0


@pytest.mark.parametrize("threshold", range(1, 5))
@pytest.mark.parametrize("level", [0, 1])
def test_exhaustive_small_threshold_completion_against_run_length_oracle(threshold, level):
    for bits in product((0, 1), repeat=7):
        parts = machine([temporal_wait(level, threshold, next=1), Entry(HALT)])
        streak, first = 0, None
        for index, bit in enumerate(bits):
            streak = streak + 1 if bit == level else 0
            if streak >= threshold and first is None:
                first = index
        seen = []
        for index, bit in enumerate(bits):
            if "temporal_qualified" in step(parts, bit)[1]:
                seen.append(index)
        assert seen == ([] if first is None else [first])


@pytest.mark.parametrize("lifecycle", ["reset", "abort", "disable", "watchdog", "release"])
def test_engine_lifecycle_clears_partial_qualification(lifecycle):
    cfg = Config(frame="level", transmit=False, watchdog=5 if lifecycle == "watchdog" else 0,
                 program=program([temporal_wait(0, 20, next=1), Entry(HALT)]))
    engine = Engine(cfg)
    for _ in range(4):
        engine.step(255)
    for _ in range(4):
        engine.step(250)
    assert engine.exchange.temporal_count > 0
    if lifecycle == "disable":
        engine.enabled = False
    engine.step(251 if lifecycle == "release" else 250,
                reset=lifecycle == "reset", abort=lifecycle == "abort")
    if lifecycle in ("watchdog", "release"):
        for _ in range(10):
            engine.step(251 if lifecycle == "release" else 250)
    assert engine.exchange.temporal_count == 0
    assert not engine.exchange.temporal_done and not engine.active


def test_acquisition_counts_first_matching_observation_and_suppresses_output():
    engine = Engine(Config(frame="falling", transmit=False,
                          program=program([temporal_wait(0, 1, next=1, chain=True),
                                           Entry(RESPOND, next=2, value=0), Entry(HALT)])))
    for _ in range(4):
        engine.step(255)
    rows = [engine.step(250) for _ in range(3)]
    assert "frame_start" in rows[-1]["events"]
    assert engine.exchange.temporal_done and engine.exchange.pc == 0
    assert not rows[-1]["oe"]
    row = engine.step(250)
    assert "response_emit" in row["events"] and row["oe"] == 8


@pytest.mark.parametrize("entry", [
    Entry(WAIT, flags=TEMPORAL, argument=3),
    Entry(WAIT, trigger=RISING, flags=TEMPORAL, argument=3, mask=1),
    Entry(WAIT, flags=TEMPORAL, argument=1, mask=1),
    Entry(WAIT, flags=TEMPORAL | 1, argument=3, mask=1),
    Entry(WAIT, flags=TEMPORAL | 16, argument=3, mask=1),
    Entry(WAIT, flags=TEMPORAL, argument=7, mask=1),
    Entry(WAIT, flags=TEMPORAL, argument=3, value=2, mask=1),
    Entry(WAIT, flags=TEMPORAL | INTERRUPT_BRANCH, argument=2, mask=1),
    Entry(WAIT, flags=TEMPORAL, argument=2, value=1, mask=1),
])
def test_invalid_temporal_encoding_is_rejected(entry):
    with pytest.raises(ValueError, match="temporal"):
        program([entry])


def test_chained_handoff_wait_uses_preedge_tx_bit():
    parts = machine([Entry(HANDOFF, TIMER, 1, argument=2, flags=CHAIN),
                     Entry(WAIT, next=2, argument=2, flags=2), Entry(HALT)])
    parts[4].append(0x80)
    events = step(parts, settled=True, settled_bit=1)[1]
    assert "data_mismatch" in events and list(parts[4]) == [0x80]


def test_chained_tx_wait_uses_preedge_tx_bit():
    parts = machine([Entry(TX, RISING, 1, flags=CHAIN),
                     Entry(WAIT, next=2, argument=2, flags=2), Entry(HALT)])
    parts[2].load(0x80)
    parts[2].remaining = 1
    assert "data_mismatch" not in step(parts, rising=True, settled=True, settled_bit=1)[1]


def test_terminating_halt_cancels_same_cycle_fifo_work_and_preserves_old_entries():
    parts = machine([Entry(RX, RISING, 1, argument=1, flags=CHAIN),
                     Entry(DECIDE, next=2, value=1, mask=1, flags=3 | CHAIN),
                     Entry(HALT, flags=1)])
    parts[3].append(0x55)
    assert "frame_terminate" in step(parts, bit=1, rising=True)[1]
    assert list(parts[3]) == [0x55]
    assert parts[0].executed_entries == [0, 1, 2]


@pytest.mark.parametrize("repeated_start", [False, True])
def test_registered_validation_end_preempts_temporal_acquisition(repeated_start):
    cfg = Config(frame="two_wire", sample="timer", period=2, validate_stop=True,
                 transmit=False, rx_pin=2, tx_pin=2, open_drain=4,
                 program=program([delay_wait(100, next=1, chain=True),
                                  Entry(RESPOND,next=2), Entry(HALT,flags=2)]))
    engine = Engine(cfg)
    rows = []
    for cycle in range(40):
        pins = 255
        if cycle == 8 or repeated_start and cycle >= 27: pins &= ~4
        if cycle in (9,10): pins &= ~2
        rows.append(engine.step(pins))
    assert not rows[29]['active']
    assert 'frame_start' not in rows[29]['events']
    assert not rows[29]['oe']
    assert not engine.rx_fifo
