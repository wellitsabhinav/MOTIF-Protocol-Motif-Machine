from ..engine import Config
from ..transaction import Entry, program, RX, DECIDE, RESPOND, HANDOFF, WAIT, TX, HALT, RISING, FALLING, CHAIN


def target(address=0x52, watchdog=0, ack_address=True, ack_data=True, setup_cycles=63):
    if type(address) is not int or not 0 <= address < 128:
        raise ValueError("Address outside seven-bit range")
    if type(ack_address) is not bool or type(ack_data) is not bool:
        raise ValueError("Acceptance policy must be Boolean")
    words = program([
        Entry(RX, RISING, 1, argument=8),
        Entry(DECIDE, next=2, argument=3, value=address << 1, mask=254, flags=int(ack_address) | 8),
        Entry(RESPOND, FALLING, 3, argument=1, flags=1),
        Entry(RESPOND, FALLING, 4, 15, argument=3, flags=2 | CHAIN),
        Entry(WAIT, next=5, argument=0, flags=1 | CHAIN),
        Entry(HANDOFF, next=6, alternate=7, flags=1 | CHAIN),
        Entry(WAIT, next=10, argument=2, flags=3),
        Entry(RX, RISING, 8, argument=8),
        Entry(DECIDE, next=9, flags=int(ack_data) | 2 | 4),
        Entry(RESPOND, FALLING, 11, argument=1, flags=1),
        Entry(TX, FALLING, 12, flags=2 | 4),
        Entry(RESPOND, FALLING, 4, 15, argument=3, flags=2 | CHAIN),
        Entry(RESPOND, RISING, 4, 15, argument=2, value=FALLING, flags=1 | CHAIN),
    ])
    return Config(frame="two_wire", clock_pin=1, rx_pin=2, tx_pin=2,
                  open_drain=6, program=words, hold_clock=True, pad_timing_check=True,
                  watchdog=watchdog, period=setup_cycles)
