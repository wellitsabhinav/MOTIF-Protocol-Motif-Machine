# Execution model

`Engine.step(pins, reset=False, abort=False)` advances one core cycle. A two-stage
frontend advances its registers while actors consume the old second-stage level
and its qualified edge pulses. Edge reporting is suppressed during initialization.

Priority is reset/disable/abort/release/timeout, acquisition, then normal firing.
Acquisition clears partial receive state and arms configured actors. A terminal
receive firing samples and shifts the eighth bit, resets the bit count and emits
field completion together. Transaction fields are bounded to 1–16 bits; ordinary
receive configurations still complete bytes. Timed sampling captures its input bit with its event;
the receive actor consumes that registered event on the following cycle.
For unvalidated RX, FIFO deposit participates in the same compound terminal
firing using the precomputed next byte. UART stop validation consumes a registered
event on a later tick. Transaction RX stores the completed field; the configured
graph selects the next decision and whether to chain it immediately. Terminal TX
advance and refill likewise commit together as one compound firing.

Release discards partial receive assembly and in-flight transmit state. Completed
RX bytes and queued TX bytes remain available. Loading a TX shifter consumes its
queued byte; an interrupted loaded byte is not automatically retransmitted.
SPI streams preload the following byte at a terminal falling edge; missing data
uses the configured fill byte and reports underflow. RX overflow discards the
new byte and reports overflow. Reset empties FIFOs and clears diagnostics.

SPI raw deselection gates OE immediately, independently of synchronized engine
release. Ownership acquisition remains synchronized. Reset and disable suppress
OE. Acquisition requires a fresh qualified configured frame edge; an asserted
framing level cannot reacquire a timed-out transaction. The watchdog observes
frontend pin activity, not executor progress claims.
An enabled watchdog trips after its configured number of inactive cycles during
an active frame. A new qualified frame acquisition rearms it. Status is sticky
until reset and is separate from the transaction trip state.

The v2 graph executes at most four distinct immediate ALWAYS entries per cycle.
Triggers consume the cycle's edge or registered timer event without a backlog;
only the active entry can observe them. Sampled boundary-response capture has
priority over completion if both sources fire. Conflicting FIFO/TX actions and
excessive chains abort. This is not an arbitrary concurrent event monitor.

The fixed pipeline adds synchronization and firing latency. Protocol drivers must
allow the documented frontend to observe each level; maximum wire rates are not
yet qualified. Initial tests use at least eight core cycles per SPI half-phase.

## V3 continuous temporal qualification

Temporal WAIT observes every active core cycle. RX-level persistence and
constant-true delay share one count, started bit and registered-complete bit;
the shared timed sampler retains its prior semantics. A threshold T means T
consecutive matching synchronized observations, with the first counting as one.
When entry zero is temporal, acquisition clears the old epoch then counts its
matching observation while suppressing ordinary actions and responses.

A false predicate before completion immediately clears progress. Restart mode
waits in place for a fresh interval; interruption-branch mode selects `alternate`
only if a partial interval had started. An initially false input does not branch.
The T-th matching observation registers success; normal execution consumes it on
the following cycle and may chain the successor. A subsequent false observation
does not invalidate a completed interval. A false T-th candidate does prevent it.

A chain can enter a temporal wait and count the current observation. After a
temporal operation has been evaluated in that cycle, a second temporal entry is
deferred. It is not counted twice and does not execute as a fifth action. Existing
revisit/conflicting-action faults and the four-distinct-entry bound remain.
Actual ordered entry observations, rather than configured possible successors,
are retained in simulation diagnostics without additional hardware registers.

Reset, disable, abort, release, watchdog and fatal conditions discard progress
and registered completion. A new acquisition may seed a fresh entry-zero epoch.
Guardian suppression and configuration immutability retain their priorities.
Continuity is established only for observations the existing frontend can sample;
no analog or unsampled subcycle persistence guarantee is implied.

Two disclosed v2 model correspondence corrections match unchanged ordinary RTL
behavior: TX-bit validation uses the pre-edge TX bit even after a chained load or
shift, and a terminating HALT cancels same-cycle FIFO work while preserving earlier
queued entries. Their original counterexamples remain in the v3 audit evidence.

The declarative I²C v2 profile preserves the following externally visible
behavior. Two-wire framing recognizes SDA transitions while SCL was and remains high.
START, including repeated START, cancels the previous exchange and acquires a
fresh address frame. STOP releases it. Simultaneous SCL/SDA transitions are not
treated as qualified START/STOP. First-word matching and byte acceptance consume
registered receive completion on the following core cycle. ACK drive begins at
the following falling SCL edge and ends after the ninth rising/falling pair.

An address miss or configured rejection leaves SDA released through the ninth
clock and disables further exchange until a framing boundary. A full RX FIFO
NACKs and discards the new byte. On reads, an empty TX FIFO stretches SCL low at
a byte boundary until data arrives. Controller NACK terminates transmission.
TX preparation holds SCL low while the first data bit settles. A registered
turnaround event arms the shared timer; its registered expiry releases SCL.
The default setup interval is 63 core cycles, plus two event-pipeline cycles:
1.3 µs at the 50 MHz reference point. This conservatively covers Standard-mode
rise time plus data setup at that point. `setup_cycles` is configurable; digital
tests also exercise a 13-cycle interval with ideal instantaneous wire transitions.
Analog rise time and voltage thresholds still require physical qualification.
The controller driver waits for resolved SCL high before starting its high period.
At expiry the timer samples resolved SDA. A first-bit mismatch aborts the
transaction, reports `data_mismatch`, releases outputs and allows a fresh START.
This is a check at the transmit handoff, not complete bus-collision detection.

The default watchdog is disabled, allowing indefinite I²C waits; an explicitly
enabled inactivity watchdog releases outputs on expiry. Only external SCL edges
reset that I²C watchdog. Own SDA activity and unrelated pin activity do not.
Six bits of guarded drive history align own clock/data requests with synchronized
pin edges. A delayed self-generated START cannot rearm after abort. A detected
own SCL truncation or own SDA transition during stable SCL high trips protection
and reports `pad_timing`. This digital causality check does not prove complete
protocol timing or bus arbitration. Automatic rearm requires a qualified new START.
