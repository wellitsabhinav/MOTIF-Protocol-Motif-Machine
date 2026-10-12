"""The preregistered v2 instruction encoding; no protocol dispatch."""
from dataclasses import dataclass

RX, DECIDE, RESPOND, HANDOFF, WAIT, TX, HALT, CONTINUE = range(8)
ALWAYS, RISING, FALLING, TIMER = range(4)
CHAIN = 1024


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
    return words


def host_bytes(words):
    validate(words)
    return b"".join(word.to_bytes(8, "little") for word in words)
