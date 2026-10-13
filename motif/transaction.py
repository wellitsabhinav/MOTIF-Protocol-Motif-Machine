"""Bounded v3 encoding: temporal qualification is a tagged generic WAIT."""
from dataclasses import dataclass

RX, DECIDE, RESPOND, HANDOFF, WAIT, TX, HALT, CONTINUE = range(8)
ALWAYS, RISING, FALLING, TIMER = range(4)
CHAIN = 1024
TEMPORAL = 4
INTERRUPT_BRANCH = 8


def is_temporal(entry):
    return entry.opcode == WAIT and bool(entry.flags & TEMPORAL)


def temporal_wait(level, cycles, on_interrupt="restart", next=15, alternate=15, chain=False):
    if type(level) is not int or level not in (0, 1):
        raise ValueError("Temporal level must be zero or one")
    if on_interrupt not in ("restart", "branch"):
        raise ValueError("Temporal interruption must restart or branch")
    entry = Entry(WAIT, next=next, alternate=alternate, argument=3, value=level,
                  mask=cycles, flags=TEMPORAL | (INTERRUPT_BRANCH if on_interrupt == "branch" else 0) | (CHAIN if chain else 0))
    validate(program([entry]))
    return entry


def delay_wait(cycles, next=15, chain=False):
    entry = Entry(WAIT, next=next, argument=2, mask=cycles,
                  flags=TEMPORAL | (CHAIN if chain else 0))
    validate(program([entry]))
    return entry


@dataclass(frozen=True)
class Entry:
    opcode: int
    trigger: int = ALWAYS
    next: int = 15
    alternate: int = 15
    argument: int = 0
    value: int = 0
    mask: int = 0
    flags: int = 0

    def encode(self):
        widths = (3, 2, 4, 4, 8, 16, 16, 11)
        values = (self.opcode, self.trigger, self.next, self.alternate,
                  self.argument, self.value, self.mask, self.flags)
        result, offset = 0, 0
        for value, width in zip(values, widths):
            if type(value) is not int or not 0 <= value < 1 << width:
                raise ValueError("Entry operand outside preregistered encoding")
            result |= value << offset
            offset += width
        return result

    @classmethod
    def decode(cls, word):
        if type(word) is not int or not 0 <= word < 1 << 64:
            raise ValueError("Instruction outside 64-bit encoding")
        values = []
        for width in (3, 2, 4, 4, 8, 16, 16, 11):
            values.append(word & ((1 << width) - 1))
            word >>= width
        return cls(*values)


def program(entries):
    if len(entries) > 16:
        raise ValueError("Architecture contains exactly sixteen slots")
    result = tuple(e.encode() for e in entries) + (Entry(HALT).encode(),) * (16 - len(entries))
    validate(result)
    return result


def validate(words):
    if not isinstance(words, tuple) or len(words) != 16:
        raise ValueError("Program must be an immutable sixteen-entry tuple")
    for word in words:
        e = Entry.decode(word)
        if e.opcode == RX and not 1 <= (e.argument & 31) <= 16:
            raise ValueError("Receive field outside 1..16-bit range")
        if e.opcode == CONTINUE and (e.argument & 7) > 5:
            raise ValueError("Unsupported continuation predicate")
        if is_temporal(e):
            if (e.trigger != ALWAYS or e.argument not in (2, 3) or not e.mask or
                    e.value > 1 or e.flags & ~(TEMPORAL | INTERRUPT_BRANCH | CHAIN) or
                    (e.argument == 2 and (e.value or e.flags & INTERRUPT_BRANCH))):
                raise ValueError("Invalid temporal WAIT encoding")
    return words


def host_bytes(words):
    validate(words)
    return b"".join(word.to_bytes(8, "little") for word in words)


def configuration(mapping):
    """Compile declarative configuration data through the frozen public types."""
    from .engine import Config
    values = dict(mapping)
    if "program" in values:
        values["program"] = tuple(int(w, 0) if isinstance(w, str) else w for w in values["program"])
    return Config(**values)
