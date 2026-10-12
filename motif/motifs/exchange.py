class ByteExchange:
    """Bounded first-word match, ninth-clock response and direction handoff.

    The phase vocabulary is fixed. Configuration cannot add states or transitions.
    RX/TX data remains in the shared shifters and FIFOs.
    """

    def __init__(self, address, ack_address=True, ack_data=True):
        self.address = address
        self.ack_address = ack_address
        self.ack_data = ack_data
        self.clear()

    def clear(self):
        self.phase = "rx"
        self.header = True
        self.next_role = "rx"
        self.ack = self.drive_low = self.stretch = False
        self.controller_ack = False
        self.pending_byte = 0

    def _transmit(self, tx, fifo, fires, events):
        if fifo:
            tx.load(fifo.popleft())
            self.phase = "settle"
            self.drive_low = not tx.bit
            self.stretch = True
            fires.append("SHIFT_TX_LOAD")
            events.append("turnaround_begin")
        else:
            self.phase = "stretch"
            self.stretch = True
            self.drive_low = False
            fires.append("STRETCH_UNTIL_READY")

    def tick(self, rising, falling, bit, rx, tx, rx_fifo, tx_fifo, capacity, settled=False, settled_bit=0):
        fires, events = [], []
        byte = None
        if self.phase == "stretch":
            if tx_fifo:
                self._transmit(tx, tx_fifo, fires, events)
                fires.append("STRETCH_UNTIL_READY")
        elif self.phase == "settle":
            if settled:
                self.phase = "tx" if settled_bit == tx.bit else "idle"
                self.stretch = False
                if settled_bit != tx.bit:
                    self.drive_low = False
                    events.append("data_mismatch")
                fires.append("STRETCH_UNTIL_READY")
        elif self.phase == "rx" and rising:
            byte = rx.fire(bit)
            fires.append("SHIFT_RX_COUNT")
            if byte is not None:
                events.append("byte_complete")
                self.pending_byte = byte
                self.phase = "decide"
        elif self.phase == "decide":
                if self.header:
                    self.ack = (self.pending_byte >> 1) == self.address and self.ack_address
                    self.next_role = "tx" if self.pending_byte & 1 else "rx"
                    self.header = False
                    fires.append("MATCH_FIRST_WORD")
                    events.append("address_match" if self.ack else "address_miss")
                else:
                    self.ack = self.ack_data and len(rx_fifo) < capacity
                    if self.ack:
                        rx_fifo.append(self.pending_byte)
                    else:
                        events.append("receive_nack")
                self.phase = "ack_setup"
        elif self.phase == "ack_setup" and falling:
            self.drive_low = self.ack
            self.phase = "ack_hold"
            fires.append("OPEN_DRAIN_ACK")
        elif self.phase == "ack_hold" and falling:
            self.drive_low = False
            fires += ["OPEN_DRAIN_ACK", "TURNAROUND"]
            if not self.ack:
                self.phase = "idle"
            elif self.next_role == "tx":
                self._transmit(tx, tx_fifo, fires, events)
            else:
                self.phase = "rx"
        elif self.phase == "tx" and falling:
            complete = tx.fire()
            fires.append("SHIFT_TX")
            if complete:
                self.phase = "controller_ack"
                self.drive_low = False
                self.controller_ack = False
                fires.append("TURNAROUND")
                events.append("tx_complete")
            else:
                self.drive_low = not tx.bit
        elif self.phase == "controller_ack":
            if rising:
                self.controller_ack = not bit
                fires.append("OPEN_DRAIN_ACK_SAMPLE")
            elif falling:
                fires.append("TURNAROUND")
                if self.controller_ack:
                    self._transmit(tx, tx_fifo, fires, events)
                else:
                    self.phase = "idle"
                    events.append("transmit_nack")
        return fires, events, byte
