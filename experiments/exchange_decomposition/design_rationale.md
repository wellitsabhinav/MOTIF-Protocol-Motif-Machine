# Why the decomposition follows from the failed baseline

The legacy macro first captured a byte, then qualified a seven-bit address,
selected direction from bit zero, emitted a fixed ninth-clock response, and
required a controller response after every transmitted byte. Its mandatory
controller-response state interrupted A55A after A5. This is valid permanent
negative evidence, not a bug in the independent oracle.

The selected operations separate qualification, ownership, response and waiting.
Each can be described using fields, predicates, events, readiness and output
requests without referring to a protocol name. Their table and routing are part
of the architecture, including their storage cost; generic names alone do not
establish reuse.

The table contains 16 fixed 64-bit entries. Existing shifting and lifecycle
actions can be composed with the four new primitives. Immediate chains are
bounded to four distinct entries and can enter only unconditional successors.
This allows release/readiness/handoff on one qualified boundary without
consuming the same external edge twice. The RX-to-decision boundary remains
registered where the configuration omits CHAIN.

The initial receive field is bounded to 16 bits because the already specified
workloads require eight and nine bits. TX remains byte storage; last-bit
presentation and consumption are distinct configurable boundary meanings.
Two FIFO bytes can therefore provide a continuous word without a word-specific
controller. Explicit framing polarity, output event and ownership configuration
remove the integration restrictions discovered in the source audit.

The I2C composition preserves the original timing and malformed-event behavior.
The Microwire composition uses active-high framing, nine-bit field qualification,
the dummy zero, and two rising-event byte presentations. It never owns clock.
Both compositions and every permitted operation are committed before model/RTL
implementation. No third protocol has been researched or selected.

An insufficiency of this contract ends the experiment. Correcting an implementation
to this contract is permitted and must be recorded separately from semantics.
