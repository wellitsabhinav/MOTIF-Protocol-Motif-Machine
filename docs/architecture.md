# Architecture

The model has one configurable engine with eight protocol pins, eight-bit RX/TX
shifters, four-byte FIFOs, a sixteen-bit sample timer and a sixteen-bit guardian
watchdog. Receive/count is a single compound firing. Transmit state advances on
the configured clock edge. Framing and timed sampling have bounded local state.

The event plane carries pin edges, timer samples, byte completion and framing
events. Byte data moves through fixed shifter/FIFO paths. There is no arbitrary
byte crossbar, instruction stream or programmable state-transition table.

Protocol helpers construct configurations of the same engine. Configuration is
accepted only while disabled. The guardian receives pad requests and ownership
information independently of shifter contents. It controls all final DATA/OE.
Open-drain requests can pull low or release. Conflicting requests release a pad.

The current model has one sample timer. Additional timer instances are not yet
needed by the qualified configurations. Pin levels are digital; analog thresholds,
pull-up sizing, metastability probability and silicon behavior are not modeled.
