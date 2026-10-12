# Exchange decomposition source audit

Baseline production source: `d639a9aa8bf8e51f99c514a05a477a0b3c582d91`.
Historical experiment snapshot: `7a74a1772dd178e498228667b54ec6a2fd39373a`.
The historical classification remains `MOTIF_BYTE_EXCHANGE_PROTOCOL_SPECIFIC`.

## State and transition responsibilities

| Existing state/logic | Semantic responsibility | I2C-specific? | Generic part | Candidate primitive |
|---|---|---|---|---|
| RX, rising event, rx_count == 7 | Sample initial/data word and detect its boundary | Fixed eight-bit initial field is over-coupled | Bounded sampling/shifting/counting | SHIFT_RX_COUNT, configurable field length |
| RX -> DECIDE, pending_byte | Register the completed field for a subsequent decision | No | Field capture and one-cycle decision alignment | FIELD_DECISION |
| DECIDE with header | Compare pending_byte[7:1] to address | Seven-bit address interpretation is structural | Masked field equality | FIELD_DECISION |
| DECIDE, pending_byte[0], transmit_i | Select next role and reject disabled direction | Direction position and meaning are structural | Configured field-bit/fixed direction and permission | FIELD_DECISION |
| DECIDE without header | Accept policy and pre-edge FIFO capacity; push accepted byte | ACK terminology is specific | Acceptance predicate and conditional enqueue | FIELD_DECISION |
| DECIDE -> ACK_SETUP regardless of acceptance | Require a response after each received byte | Yes | Route to a separately selected response | BOUNDARY_RESPONSE |
| ACK_SETUP on falling | Drive accepted-low response | Mandatory ninth-clock active-low response is specific | Configured event, response value and drive | BOUNDARY_RESPONSE |
| ACK_HOLD on next falling | Release response, reject/continue, choose role | Mandatory clock slot is specific | Conditional continuation and ownership handoff | BOUNDARY_RESPONSE, DIRECTION_HANDOFF |
| ACK_HOLD ignores whether rising occurred | Malformed event behavior | Legacy behavior, not ideal protocol validation | Each configured event is consumed once | Action-table executor |
| TX on falling | Consume presented bit and drive next bit | Falling source is fixed | Event-selected SHIFT_TX | SHIFT_TX |
| TX terminal -> CONTROLLER_ACK, drive release | Interrupt every byte for controller response | Yes; decisive A5FF counterexample | Configurable word-boundary destination | BOUNDARY_RESPONSE |
| CONTROLLER_ACK rising | Capture inverted input level, including repeated samples | Active-low ACK meaning is specific | Configured sampled response polarity | BOUNDARY_RESPONSE |
| CONTROLLER_ACK falling | Continue on captured value or halt | ACK continuation rule is specific | Conditional branch on a captured response | BOUNDARY_RESPONSE |
| prepare_tx, tx_empty | Readiness-dependent load or wait | No | Wait for pre-edge FIFO availability | WAIT_POLICY |
| prepare_tx, tx_load, turnaround | Load byte, select first bit, start setup schedule | No, except mandatory stretching | Transfer datapath ownership and prepare output | DIRECTION_HANDOFF |
| STRETCH until !tx_empty | Controlled readiness waiting | Owning SCL is specific | Optional hold-output request during wait | WAIT_POLICY |
| SETTLE with timer event | Compare resolved first bit, release hold, continue or abort | Mandatory setup stretching is specific | Timed level validation and readiness | WAIT_POLICY |
| IDLE | Stop actor while frame can remain active | No | Halt with explicit output/frame policy | TERMINATE composition outcome |
| clear_i / reset | Reset transaction state, release requests | No | Lifecycle priority and state initialization | Existing frame/reset mechanisms |

## Every declared state variable

The macro allocates 18 bits: phase_o=4, header=1, next_role=1, ack=1,
controller_ack=1, pending_byte=8, drive_low_o=1, stretch_o=1. Combinational
`*_next` signals and `prepare_tx` allocate no independent storage.

`phase_o` couples field reception, decision, response, ownership, wait and halt.
`header` couples initial-field qualification to a special first byte.
`next_role` is a reusable direction result. `ack` mixes acceptance with output
polarity and continuation. `controller_ack` is a captured response predicate.
`pending_byte` is decision data. `drive_low_o` is a restricted pad request.
`stretch_o` mixes readiness/timing state with a particular clock output.

## Integration audit

- Core acquisition/release selects falling/active-low framing or data-edge with
  stable-high clock. Repeated acquisition resets RX and exchange state; STOP,
  reset, disable, abort, watchdog expiry and mismatch suppress actor actions.
- Own OE passes through three two-bit provenance stages. Own data activity must
  not create acquisition; own clock activity must not feed watchdog progress.
  Clock truncation and data transitions while clock is stable high abort.
- The timer starts one cycle after turnaround. Registered expiry is consumed on
  the next actor tick: preparation to setup release is period+2 cycles.
- The shared RX/TX shifters and four-byte FIFOs carry data. FIFO decisions use
  pre-edge flags; a concurrent full RX pop does not rescue exchange acceptance,
  and an empty TX push is visible on the next cycle. Release preserves FIFO
  contents, while reset clears them. Partial RX and consumed TX data are not
  reconstructed by host behavior.
- The host rejects exchange unless RX/TX share a data pin, external sampling is
  used, data differs from clock, and data/clock are open drain. These restrictions
  prevent compliant separate DI/DO composition and must be replaced explicitly.
- Core requests hardcode low data and optional low clock; ownership deliberately
  allows shared RX/TX. The guardian alone authorizes final OE and applies raw
  kill, fatal, ownership and open-drain protections.
- Current framing cannot acquire active-high CS normally. Current TX advances
  on falling only. The nine-bit Microwire command, dummy zero, separate DI/DO,
  active-high CS and rising-edge output changes cannot be repaired solely by
  renaming ACK states.

## Decomposition conclusion

Field qualification, ownership handoff, boundary response and waiting have
separate data/event contracts. Readiness waiting and timed validation share an
independent wait policy, with hold-pin ownership optional. A bounded 16-entry
action table makes the control graph configuration rather than fixed protocol
RTL. Existing shifts, framing, FIFOs, timer, watchdog and guardian remain shared;
their required width/event/routing additions must be preregistered too.

No third workload has been researched or selected for this decomposition.
