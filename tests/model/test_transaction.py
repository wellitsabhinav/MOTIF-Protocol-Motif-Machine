from collections import deque
from pathlib import Path
import hashlib
import subprocess

import pytest

from motif import Config
from motif.motifs.transaction import FieldShift, Transaction
from motif.motifs.shift import ShiftTX
from motif.transaction import Entry, program, RX, DECIDE, RESPOND, WAIT, HANDOFF, TX, HALT, CONTINUE, RISING, FALLING, CHAIN, host_bytes
from tools.exchange_decomposition import microwire_case, i2c_cases


@pytest.mark.parametrize("length", [1,8,9,16])
@pytest.mark.parametrize("lsb", [False,True])
def test_bounded_fields_independent_of_byte_boundary(length,lsb):
    rx=FieldShift(lsb)
    word=((1<<length)-1)//3
    bits=[(word>>i)&1 for i in (range(length) if lsb else range(length-1,-1,-1))]
    for bit in bits[:-1]: assert rx.fire(bit,length) is None
    assert rx.fire(bits[-1],length)==word
    assert rx.count==0


def actor(entries, tx_data=()):
    machine=Transaction(program(entries))
    rx,tx=FieldShift(),ShiftTX()
    return machine,rx,tx,deque(),deque(tx_data)


def tick(parts,rising=False,falling=False,bit=0,settled=False,settled_bit=0):
    m,rx,tx,rf,tf=parts
    return m.tick(rising,falling,bit,rx,tx,rf,tf,4,settled,settled_bit)


def test_response_does_not_consume_successor_external_event():
    p=actor([Entry(RESPOND,FALLING,1,value=0,flags=CHAIN), Entry(RESPOND,FALLING,2,value=1)])
    tick(p,falling=True)
    assert p[0].pc==1 and p[0].drive_value==0
    tick(p,falling=True)
    assert p[0].pc==2 and p[0].drive_value==1


def test_sampled_response_completion_uses_previous_capture():
    p=actor([Entry(RESPOND,RISING,1,2,argument=2,value=FALLING,flags=1)])
    tick(p,falling=True)
    assert p[0].pc==2
    p[0].clear()
    tick(p,rising=True,bit=0)
    assert p[0].pc==0 and p[0].response
    tick(p,falling=True)
    assert p[0].pc==1


def test_waiting_can_have_no_hold_output():
    p=actor([Entry(WAIT,next=1),Entry(HALT)])
    p[0].desired_role=1
    tick(p)
    assert p[0].pc==0 and not p[0].hold
    p[4].append(0x80)
    tick(p)
    assert p[0].pc==1 and not p[0].hold


@pytest.mark.parametrize("presented",[False,True])
def test_last_bit_presentation_is_distinct_from_consumption(presented):
    p=actor([Entry(TX,RISING,1,flags=int(presented)),Entry(HALT,flags=2)])
    p[2].load(0x5a)
    for _ in range(6): tick(p,rising=True)
    assert p[0].pc==0 and p[2].remaining==2
    tick(p,rising=True)
    assert p[0].pc==(1 if presented else 0)
    assert p[2].remaining==1
    if not presented:
        tick(p,rising=True)
        assert p[0].pc==1 and p[2].remaining==0


def test_full_fifo_decision_does_not_assume_host_pop():
    p=actor([Entry(DECIDE,next=1,flags=1|2|4)])
    p[3].extend([1,2,3,4]);p[0].pending_field=99
    tick(p)
    assert not p[0].accepted and list(p[3])==[1,2,3,4]


def test_immediate_cycles_abort_without_unbounded_interpretation():
    p=actor([Entry(CONTINUE,next=0,flags=CHAIN)])
    _,events,_=tick(p)
    assert "composition_fault" in events and p[0].halted
    assert not p[0].drive_enable and not p[0].hold


def test_fifth_immediate_action_is_not_an_architecture_extension():
    p=actor([Entry(CONTINUE,next=i+1,flags=CHAIN) for i in range(4)]+[Entry(HALT)])
    assert "composition_fault" in tick(p)[1]


def test_encoder_round_trip_and_fixed_host_table_size():
    entry=Entry(DECIDE,RISING,5,6,argument=63,value=0xa55a,mask=65535,flags=1033)
    assert Entry.decode(entry.encode())==entry
    assert len(host_bytes(program([entry])))==128


@pytest.mark.parametrize("bad", [(), (0,)*16, (-1,)*16, (1<<64,)*16])
def test_invalid_table_cannot_be_enabled(bad):
    if not bad:
        Config(program=bad)
    else:
        with pytest.raises(ValueError): Config(program=bad)


def test_microwire_uses_frozen_word_oracle_and_no_host_sequence():
    engine,result=microwire_case()
    assert result["observed_word_hex"]==result["expected_word_hex"]=="0xa55a"
    assert sum(action[3] for action in engine.actions)==2
    assert all(not r["oe"] & 7 for r in engine.rows)


def test_preregistration_is_unchanged_from_its_commit():
    path="experiments/exchange_decomposition/preregistered_architecture.json"
    expected=subprocess.check_output(["git","show","d3ca35e2221f8e7654f4c42fa79ab7992e8ee8d8:"+path])
    assert Path(path).read_bytes().replace(b"\r\n",b"\n")==expected
