# Host interface

The dedicated host SPI port uses mode 0 and MSB-first 24-bit frames: command,
address, and data/dummy byte. Command 2 writes; command 1 reads. Read data appears
on the third byte. Deassert CS between commands. RX FIFO reads pop only after the
third byte completes. Unknown commands have no effect; unknown reads return zero.
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
| 16 | TX FIFO write |
| 17 | RX FIFO read/pop |
| 18 | Status: bit 0 guard/config rejection, 1 empty RX read, 2 TX overflow, 3 RX overflow, 4 fill underflow, 5 framing error, 6 timeout, 7 reference issue collision |
| 19 | RX count in bits 2:0, TX count in bits 5:3, active frame in bit 6 |

Disable before changing configuration. A write to control while enabled must
clear enable; other enabled configuration writes are rejected. FIFO access
remains available while running. Periods below two inhibit engine enable.
Reset initializes SPI pin assignments, a 434-cycle period, fill 255, watchdog
disabled, and the engine disabled. Configuration registers allocate 67 meaningful
bits, including enable. Other encodings belong to the model-only I²C extension.

Examples: SPI control 9 with default pin assignments; UART control 119, frame/RX
pin 2, sample period appropriate to baud; external timed stream control 5,
frame pin 0. Test periods 32 and 16 are normalized simulation examples, not the
default UART baud configuration. Enable changes and external framing must allow
the frontend pipeline to settle. A fresh falling frame edge begins acquisition.
