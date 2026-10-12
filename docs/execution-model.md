# Execution model

`Engine.step(pins, reset=False, abort=False)` advances one core cycle. A two-stage
frontend advances its registers while actors consume the old second-stage level
and its qualified edge pulses. Edge reporting is suppressed during initialization.

Priority is reset/disable/abort/release/timeout, acquisition, then normal firing.
Acquisition clears partial receive state and arms configured actors. A terminal
receive firing samples and shifts the eighth bit, resets the bit count and emits
byte completion together. Timed sampling captures its input bit with its event;
the receive actor consumes that registered event on the following cycle.

Release discards partial receive assembly and in-flight transmit state. Completed
RX bytes and queued TX bytes remain available. Loading a TX shifter consumes its
queued byte; an interrupted loaded byte is not automatically retransmitted.
SPI streams preload the following byte at a terminal falling edge; missing data
uses the configured fill byte and reports underflow. RX overflow discards the
new byte and reports overflow. Reset empties FIFOs and clears diagnostics.

SPI raw deselection gates OE immediately, independently of synchronized engine
release. Ownership acquisition remains synchronized. Reset and disable suppress
OE. The watchdog observes frontend pin activity, not executor progress claims.
An enabled watchdog trips after its configured number of inactive cycles during
an active frame. A new qualified frame acquisition rearms it. Status is sticky
until reset and is separate from the transaction trip state.

The fixed pipeline adds synchronization and firing latency. Protocol drivers must
allow the documented frontend to observe each level; maximum wire rates are not
yet qualified. Initial tests use at least eight core cycles per SPI half-phase.

Two-wire framing recognizes SDA transitions while SCL was and remains high.
START, including repeated START, cancels the previous exchange and acquires a
fresh address frame. STOP releases it. Simultaneous SCL/SDA transitions are not
treated as qualified START/STOP. First-word matching and byte acceptance consume
registered receive completion on the following core cycle. ACK drive begins at
the following falling SCL edge and ends after the ninth rising/falling pair.

An address miss or configured rejection leaves SDA released through the ninth
clock and disables further exchange until a framing boundary. A full RX FIFO
NACKs and discards the new byte. On reads, an empty TX FIFO stretches SCL low at
a byte boundary until data arrives. Controller NACK terminates transmission.
The default watchdog is disabled, allowing indefinite I²C waits; an explicitly
enabled inactivity watchdog releases outputs on expiry. Unrelated pin activity
does not reset that watchdog. Automatic rearm requires a qualified new START.
