# Host interface

The dedicated host SPI port uses mode 0 and MSB-first 24-bit frames: command,
address, and data/dummy byte. Command 2 writes; command 1 reads. Read data appears
on the third byte. Deassert CS between commands. RX FIFO reads pop only after the
third byte completes. The data and nonempty flag are captured before the third
byte. An empty snapshot returns zero and does not consume a byte that arrives
during the response; status reports the empty read. Unknown commands have no
effect; unknown reads return zero.
Use at least eight core cycles per host half-phase in this initial qualification.

| Address | Purpose |
|---|---|
| 0 | Control: bit 0 enable, 1 falling-edge framing, 2 timed sampling, 3 TX enable, 4 LSB-first, 5 start validation, 6 stop validation |
| 1 | Frame pin in bits 2:0; clock pin in bits 5:3 |
| 2 | RX pin in bits 2:0; TX pin in bits 5:3 |
| 3, 4 | Sample period, low/high byte |
| 5 | TX fill byte |
| 6 | Open-drain pin mask |
| 7, 8 | Inactivity watchdog, low/high byte; zero disables |
| 9, 10 | Retired legacy I2C configuration; reads return zero and writes set rejection |
| 16 | TX FIFO write |
| 17 | RX FIFO read/pop |
| 18 | Status: bit 0 guard/config rejection, 1 empty RX read, 2 TX overflow, 3 RX overflow, 4 fill underflow, 5 framing error, 6 timeout, 7 reference issue collision |
| 19 | RX count in bits 2:0, TX count in bits 5:3, active frame in bit 6 |
| 20 | Transaction diagnostics: bit 0 resolved first-bit mismatch, 1 own pad timing fault, 2 composition fault; sticky until reset |
| 21 | Interface version, currently 3 |
| 22 | Transaction control: bit 0 table enable, 1 clock-level-qualified data framing, 2 active-high frame polarity, 3 hold-clock permission, 4 own-pad timing validation |
| 128–255 | Sixteen 64-bit action entries, eight little-endian bytes per entry |

Disable before changing configuration. A write to control while enabled must
clear enable; other enabled configuration writes are rejected. FIFO access
remains available while running. Periods below two inhibit engine enable.
Reset initializes SPI pin assignments, a 434-cycle period, fill 255, watchdog
disabled, and the engine disabled. V3 retains 1,096 configuration bits: 72
global bits and 1,024 table bits. Transaction control and table reset to zero.
Enabling a table with an invalid receive length or continuation predicate is
rejected. Invalid temporal encodings are also rejected. Shared RX/TX requires open-drain data; a hold route requires explicit
permission and open-drain clock. Clock and RX differ, and TX cannot alias a
protected clock/frame input. Qualified data framing requires the table path.
Invalid transaction enable requests retain the disabled
control value and set configuration rejection status.
For non-exchange configurations the guardian releases an output assigned to a
protected frame, clock or RX pin and reports a guard fault. Transactions may
share RX/TX or use separate input and output pins. A configured hold may own
clock. TX permission controls FIFO transmission; boundary responses remain
available for receive-side responses.

Examples: SPI control 9 with default pin assignments; UART control 119, frame/RX
pin 2, sample period appropriate to baud; external timed stream control 5,
frame pin 0. Test periods 32 and 16 are normalized simulation examples, not the
default UART baud configuration. Enable changes and external framing must allow
the frontend pipeline to settle. A fresh falling frame edge begins acquisition.

I²C target configuration: disable control, load the 128 table bytes from
`motif.protocols.i2c.target(...).program`, set RX/TX register 2 to 18,
open-drain mask to 6, period to 63, transaction control to 27, and control to 9.
Protocol pins 1/2 are SCL/SDA. A repeated START reacquires while active.
The shared timer supplies configured transmit setup. Host FIFO writes remain
available during controlled waiting.
On simultaneous full RX FIFO host-pop and exchange decision, the decision sees
the old full flag and NACKs. An empty TX FIFO host-push becomes visible to the
exchange on the following core cycle; there is no same-edge data bypass.

The entry encoding is fixed by the committed preregistration: opcode[2:0],
trigger[4:3], successor[8:5], alternate[12:9], argument[20:13], value[36:21],
mask[52:37], flags[63:53]. Opcodes select shared receive/transmit, field decision,
response, handoff, wait, termination or continuation. A chain can execute at
most four distinct entries and enters only unconditional successors. The same
external edge cannot execute two successive edge-triggered entries.

For the bounded Microwire READ, load the published configuration, use separate
DI/DO on pins 2/3, active-high CS on pin 0 and clock on pin 1, transaction control
5, and control 9. Preload A5 and 5A. Its table emits the dummy zero and presents
two bytes continuously on rising clock events. The legacy register contract is
reproducible in the historical snapshot and is not translated by v2.

## V3 temporal WAIT

The sixteen-entry encoding and eight opcodes remain unchanged. WAIT flags bit 2
selects `TEMPORAL_QUALIFY`. Argument 3 qualifies the configured synchronized RX
level against value bit 0; argument 2 qualifies a constant-true elapsed delay.
The mask operand holds a threshold of 1–65,535 consecutive core observations.
Flags bit 3 selects interruption branching to `alternate`; otherwise a partial
interruption restarts the wait. Success advances to `next`. CHAIN remains flags
bit 10. Temporal entries require ALWAYS and forbid hold/mismatch flags, reserved
operand bits and zero thresholds. Constant-true delay requires value zero and no
interruption branch. Validation is identical in the packing model and RTL host.

`motif.transaction.temporal_wait(...)` and `delay_wait(...)` compile these entries
without changing table storage. Qualified v2 profiles have unchanged encodings.
Old binary tables that used formerly ignored temporal-tag bits acquire v3 meaning;
arbitrary ignored-bit compatibility is not promised. Host software can inspect
register 21 before programming.

The first matching observation counts as one, including acquisition's sample
when entry zero is temporal. The T-th matching observation registers completion,
consumed on the following executor cycle. False on the T-th candidate observation
prevents qualification; false after registered completion cannot revoke it.
The operation adds a separate sixteen-bit counter and two lifecycle bits, with
no configuration growth. See the immutable v3 preregistration and execution model
for interruption, chaining and lifecycle priorities.
