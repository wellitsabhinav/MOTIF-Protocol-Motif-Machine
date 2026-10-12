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
| 9 | Exchange control: bit 0 byte exchange, 1 two-wire framing, 2 address ACK, 3 data ACK |
| 10 | Seven-bit target address |
| 16 | TX FIFO write |
| 17 | RX FIFO read/pop |
| 18 | Status: bit 0 guard/config rejection, 1 empty RX read, 2 TX overflow, 3 RX overflow, 4 fill underflow, 5 framing error, 6 timeout, 7 reference issue collision |
| 19 | RX count in bits 2:0, TX count in bits 5:3, active frame in bit 6 |
| 20 | Exchange diagnostics: bit 0 resolved first-bit mismatch, 1 own pad timing fault; sticky until reset |

Disable before changing configuration. A write to control while enabled must
clear enable; other enabled configuration writes are rejected. FIFO access
remains available while running. Periods below two inhibit engine enable.
Reset initializes SPI pin assignments, a 434-cycle period, fill 255, watchdog
disabled, and the engine disabled. Configuration registers allocate 67 meaningful
bits, including enable, in the original subset; the I²C promotion adds eleven
configuration bits for a total of 78. Exchange control resets to 12 (ACK policies
enabled, exchange/two-wire framing disabled); target address resets to `0x52`.
The engine rejects enabling exchange unless RX and TX share a data pin, clock
and data differ, both are open drain, and sampling uses the external clock.
Two-wire framing requires exchange. Invalid enable requests retain the disabled
control value and set configuration rejection status.
The guardian releases an output assigned to a protected frame, clock or RX pin
and reports a guard fault. Receive-only configurations grant no output ownership.

Examples: SPI control 9 with default pin assignments; UART control 119, frame/RX
pin 2, sample period appropriate to baud; external timed stream control 5,
frame pin 0. Test periods 32 and 16 are normalized simulation examples, not the
default UART baud configuration. Enable changes and external framing must allow
the frontend pipeline to settle. A fresh falling frame edge begins acquisition.

I²C target configuration: disable control, set RX/TX register 2 to 18, open-drain
mask to 6, period to 63, exchange control to 15, address to `0x52`, and control
to 9. Protocol pins 1/2 are SCL/SDA. A repeated START reacquires while active.
The shared timer supplies transmit setup; it is not an independently programmable
exchange transition table. Host writes remain available during clock stretching.
On simultaneous full RX FIFO host-pop and exchange decision, the decision sees
the old full flag and NACKs. An empty TX FIFO host-push becomes visible to the
exchange on the following core cycle; there is no same-edge data bypass.
