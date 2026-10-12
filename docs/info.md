## How it works

MOTIF groups serial I/O work into bounded compound operations. A shared receive
actor samples, shifts and counts bits; a transmit actor advances output data;
framing and timed sampling supply events. Four-byte RX and TX FIFOs connect the
engine to a dedicated SPI host port. A separate guardian controls final pad
output enables and open-drain behavior. Reset, disable and raw SPI deselection
release protected outputs.

The RTL supports SPI mode-0 target, UART 8N1 reception, externally framed timed
byte reception and seven-bit I²C target exchange through runtime configuration.
The expanded CMOS5L implementation passes 50 MHz timing, DRC/LVS, official
precheck and routed-netlist host testing. Analog compliance and fabricated
silicon are not established. The fixed I²C exchange does not implement Microwire.

## How to test

Keep reset low for at least four core clocks, then release it. The engine starts
disabled. Host SPI mode 0 uses ui[0] SCLK, ui[1] active-low CS, ui[2] MOSI and
uo[0] MISO. Send three bytes per command: command 2 for write or 1 for read,
register address, then data or dummy. Reads return data in the third byte.
Allow at least eight core clocks per host half-phase.

Write control register 0 with value 9 for default SPI mode-0 target pins:
uio[0] CS_n, uio[1] SCLK, uio[2] MOSI, uio[3] MISO. Write transmit bytes to
register 16 and read received bytes from register 17. Disable before changing
configuration. Register 18 exposes status; register 19 exposes FIFO levels.
For I²C, disable control, write register 2=18, open-drain mask 6=6, period
registers 3=63 and 4=0, exchange control 9=15 and target address 10=0x52, then
enable with control 0=9. SCL/SDA use uio[1]/uio[2]. Register 20 reports exchange
diagnostics. See the host-interface document for remaining settings and limits.

The automated testbench exercises host configuration, FIFO exchange, protocol
transactions, output release and reconfiguration. Model/RTL differential checks
and compact formal checks are documented in the repository.

## External hardware

A core clock source and digital controller are required. Protocol electrical
interfaces must match the board's voltage and drive capabilities. Open-drain
configurations need external pull-ups. No analog or fabricated-silicon behavior
is claimed by the digital model. No external memory is required.
