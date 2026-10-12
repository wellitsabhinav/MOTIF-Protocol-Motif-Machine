"""Independent executable semantics of the committed v2 contract."""
from ..transaction import (Entry, RX, DECIDE, RESPOND, HANDOFF, WAIT, TX,
                           HALT, CONTINUE, ALWAYS, TIMER, CHAIN)


class FieldShift:
    def __init__(self, lsb_first=False):
        self.lsb_first = lsb_first
        self.clear()

    def clear(self):
        self.value = self.count = 0

    def fire(self, bit, length=8):
        if self.lsb_first:
            self.value = (self.value >> 1) | (int(bit) << (length - 1))
        else:
            self.value = ((self.value << 1) | int(bit)) & ((1 << length) - 1)
        self.count += 1
        if self.count == length:
            self.count = 0
            return self.value
        return None


class Transaction:
    def __init__(self, words, transmit=True):
        self.entries = tuple(Entry.decode(word) for word in words)
        self.transmit = transmit
        self.clear()

    def clear(self):
        self.pc = self.pending_field = 0
        self.desired_role = self.role = 0
        self.accepted = self.response = self.drive_enable = self.drive_value = self.hold = self.halted = False

    @property
    def phase(self):
        return ("rx", "decide", "respond", "handoff", "wait", "tx", "halt", "continue")[self.entries[self.pc].opcode]

    @property
    def waiting_timer(self):
        e = self.entries[self.pc]
        return not self.halted and e.opcode == WAIT and (e.argument & 3) == 2

    @property
    def ack(self):
        return self.accepted

    @property
    def stretch(self):
        return self.hold

    def tick(self, rising, falling, bit, rx, tx, rx_fifo, tx_fifo, capacity, settled=False, settled_bit=0):
        fires, events, byte = [], [], None
        visited = set()
        sources = (True, rising, falling, settled)
        old_rx, old_tx = list(rx_fifo), list(tx_fifo)
        old_full, old_empty = len(old_rx) == capacity, not old_tx
        loads = pushes = shifts = 0

        def fatal(name):
            events.append(name)
            self.drive_enable = self.hold = False
            self.halted = True
            rx_fifo.clear(); rx_fifo.extend(old_rx)
            tx_fifo.clear(); tx_fifo.extend(old_tx)

        for execution in range(4):
            if self.halted:
                break
            e = self.entries[self.pc]
            capture = e.opcode == RESPOND and (e.argument & 3) == 2
            if not sources[e.trigger] and not (capture and sources[e.value & 3]):
                break
            if self.pc in visited:
                fatal("composition_fault")
                break
            visited.add(self.pc)
            previous_pc = self.pc
            advanced = False
            op = e.opcode
            if op == RX:
                byte = rx.fire(settled_bit if e.trigger == TIMER else bit, e.argument & 31)
                fires.append("SHIFT_RX_COUNT")
                if byte is not None:
                    self.pending_field = byte
                    self.pc = e.next
                    advanced = True
                    events.append("field_complete")
            elif op == DECIDE:
                mode = e.argument & 3
                selected = self.desired_role if mode == 0 else 0 if mode == 1 else 1 if mode == 2 else (self.pending_field >> ((e.argument >> 2) & 15)) & 1
                self.desired_role = selected
                self.accepted = bool(e.flags & 1) and (self.pending_field & e.mask) == (e.value & e.mask)
                self.accepted &= not (e.flags & 4) or not old_full
                self.accepted &= not (e.flags & 8) or self.transmit or not selected
                if self.accepted and e.flags & 2:
                    rx_fifo.append(self.pending_field & 255)
                    pushes += 1
                fires.append("FIELD_DECISION")
                events.append("decision_accept" if self.accepted else "decision_reject")
                self.pc = e.next if self.accepted or not (e.flags & 16) else e.alternate
                advanced = True
            elif op == RESPOND:
                mode = e.argument & 3
                fires.append("BOUNDARY_RESPONSE")
                if mode == 2:
                    if sources[e.trigger]:
                        self.response = bool(bit) ^ bool(e.flags & 1)
                        events.append("response_capture")
                    else:
                        self.drive_enable = False
                        self.pc = e.next if self.response else e.alternate
                        advanced = True
                        events.append("response_continue" if self.response else "response_terminate")
                else:
                    if mode == 3:
                        self.drive_enable = False
                    else:
                        self.drive_enable = True
                        self.drive_value = bool(self.accepted if mode == 1 else e.value & 1) ^ bool(e.flags & 1)
                    predicate = self.accepted if e.flags & 2 else self.response if e.flags & 4 else True
                    self.pc = e.next if predicate else e.alternate
                    advanced = True
                    events.append("response_release" if mode == 3 else "response_emit")
            elif op == HANDOFF:
                selector = e.argument & 3
                selected = self.desired_role if selector == 0 else int(selector == 2)
                fires.append("DIRECTION_HANDOFF")
                self.role = selected
                if selected:
                    if not self.transmit or old_empty:
                        fatal("composition_fault")
                        break
                    tx.load(old_tx[0])
                    tx_fifo.popleft()
                    loads += 1
                    self.drive_enable = True
                    self.drive_value = bool(tx.bit)
                    fires.append("SHIFT_TX_LOAD")
                    if e.flags & 1:
                        events.append("turnaround_begin")
                    self.pc = e.next
                else:
                    self.drive_enable = self.hold = False
                    self.pc = e.alternate
                advanced = True
            elif op == WAIT:
                mode = e.argument & 3
                fires.append("WAIT_POLICY")
                self.hold = bool(e.flags & 1) and bool(self.desired_role)
                ready = (not self.desired_role or not old_empty) if mode == 0 else not old_full if mode == 1 else settled if mode == 2 else bool(bit) == bool(e.value & 1)
                if ready:
                    if mode == 2 and e.flags & 2 and bool(settled_bit) != bool(tx.bit):
                        fatal("data_mismatch")
                        break
                    if mode != 0:
                        self.hold = False
                    self.pc = e.next
                    advanced = True
                    events.append("wait_complete")
            elif op == TX:
                fires.append("SHIFT_TX")
                shifts += 1
                if not tx.remaining:
                    fatal("composition_fault")
                    break
                boundary = tx.remaining == (2 if e.flags & 1 else 1)
                tx.fire()
                self.drive_enable = True
                self.drive_value = bool(tx.bit)
                if boundary:
                    if e.flags & 2:
                        self.drive_enable = False
                    if e.flags & 4:
                        self.response = False
                    self.pc = e.next
                    advanced = True
                    events.append("tx_complete")
            elif op == HALT:
                self.halted = True
                if not e.flags & 2:
                    self.drive_enable = self.hold = False
                if e.flags & 1:
                    events.append("frame_terminate")
                events.append("transaction_halt")
            else:
                predicates = (True, self.accepted, self.response, bool(self.desired_role), old_full, old_empty)
                self.pc = e.next if predicates[e.argument & 7] else e.alternate
                advanced = True
            if loads > 1 or pushes > 1 or shifts > 1 or (loads and shifts):
                fatal("composition_fault")
                break
            if not advanced or not e.flags & CHAIN or self.entries[self.pc].trigger != ALWAYS:
                break
            if self.pc == previous_pc or self.pc in visited or execution == 3:
                fatal("composition_fault")
                break
        return fires, events, byte
