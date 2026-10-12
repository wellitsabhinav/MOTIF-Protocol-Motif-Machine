# Architecture

The engine has eight protocol pins, bounded 1–16-bit transaction reception,
byte RX/TX FIFOs and byte TX storage, a sixteen-bit sample timer and a sixteen-bit
guardian watchdog. Non-transaction receive modes remain byte-oriented.
Receive/count is a single compound firing. Framing and timed sampling have
bounded local state.

The event plane carries pin edges, timer samples, byte completion and framing
events. Byte data moves through fixed shifter/FIFO paths. There is no arbitrary
byte crossbar. V2 adds a bounded event/action graph: sixteen 64-bit entries with
triggers, successor/alternate indices, arguments, mask/value and flags. Four
generic transaction operations share RX/TX machinery and use continuation and
termination support opcodes. A four-bit PC and halted bit are sequencing costs;
1024 bits of table storage are configuration costs. Immediate chaining visits
at most four distinct ALWAYS entries in a cycle. Conflicts, loops and excess
work abort the frame.

Protocol helpers construct configurations of the same engine. Configuration is
accepted only while disabled. The guardian receives pad requests and ownership
information independently of shifter contents. It controls all final DATA/OE.
Open-drain requests can pull low or release. Conflicting requests release a pad.
Non-exchange receive-only configurations grant no transmit ownership. Their
target transmit pin must be separate from protected input roles; the RTL guardian
independently clamps host-loaded assignments that violate this rule.
Transactions may share an open-drain data pin or use separate RX/TX pins.
Configured hold permission can own a separate open-drain clock output.

The current model has one sample timer. Additional timer instances are not yet
needed by the qualified configurations. Pin levels are digital; analog thresholds,
pull-up sizing, metastability probability and silicon behavior are not modeled.

The legacy nine-state BYTE_EXCHANGE coupled field interpretation, ownership,
responses and waiting. Its mandatory per-byte controller response broke the
independent continuous Microwire word. V2 separates FIELD_DECISION,
DIRECTION_HANDOFF, BOUNDARY_RESPONSE and WAIT_POLICY. Their implementations
contain no protocol-name branches or dedicated protocol FSM. Declarative helpers
compose I²C ninth-clock responses or continuous Microwire bytes using the same
operations. The shared timer checks the first I²C TX bit before releasing hold.

Inherited two-wire framing and clock/data provenance predicates remain explicit
integration machinery; the design is not an arbitrary event crossbar. The frozen
table lacks continuous input-level duration qualification, as the unseen
initialization counterexample demonstrates. The
[report](../experiments/exchange_decomposition/report.md) gives the preregistration,
cost accounting, validated users and negative result. V2 has synthesis evidence
but no routed physical qualification after the unseen workload failed.
