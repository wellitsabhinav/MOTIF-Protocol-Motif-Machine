# Candidate assessment and exact replacement

P1 registers only the first read and retains subsequent dependent reads. It
costs +3.628759% raw area and leaves slow WNS −5.126348 ns even with ideal
buffering. P3's endpoint cut requires FIFO reservations/snapshot handling and
does not cut transaction-state/TX endpoints. Its mapping timeout supplies no
timing result. P4 is an exact control-localization rewrite (46 next-state bits
and all combinational outputs proved for arbitrary table/state/control inputs),
but mapping also timed out. Neither timeout is treated as negative timing.

P2 is the promising kernel: first select/predecode, then a registered instruction,
then one operation per core cycle. It retains all sixteen programmable 64-bit
entries and all eight generic opcodes. It is not a qualified implementation:
`DECIDE(push, CHAIN) → HALT(terminate)` leaks a byte that v3 cancels. Repeated
events, acquisition cache alignment and all four-action fault semantics need
explicit control. [Semantic receipts](evidence/p2_semantic_sanity.json) record
positive protocol probes and this independent negative. No protocol-specific RTL
or timing constants are used.

## Recommended three-stage microarchitecture

**F — select and predecode.** Keep the host-visible 16×64 table, immutable while
enabled. Register a 66-bit internal µop: one-hot opcode 8; one-hot trigger 4;
successor/alternate 4+4; argument 8; value 16; mask 16; flags 0–4 plus CHAIN 6.
Keep host validation of reserved fields. Select the predicted *resolved*
successor from the preceding single execution step; no speculative branch or
four-read combinational chain. Hold the descriptor while its event/WAIT is
unready. Invalidate/refetch PC 0 on reset, acquisition and epoch cancellation.
Preload entry zero while disabled; configuration writes invalidate its cache.

**E — execute one generic operation.** Capture the eligible edge/timer/bit,
pre-edge FIFO flags/head and TX bit in a 16-bit event snapshot. Use working
transaction and RX/TX registers across microsteps, forwarding field/decision
results. Keep 16 visited bits, a three-bit step count and three seen-action bits.
Enter only ALWAYS successors in a chain, reject revisits, conflicting loads/
shifts/pushes and a fifth action. External successor events are not reused.
One eligible queued snapshot (16+valid bits) covers a bounded arrival during
commit; queue overflow aborts/releases rather than silently dropping input.
This is a bounded sequencer, not an out-of-order processor.

**C — atomic side-effect commit.** Accumulate RX push/data, TX FIFO retirement,
timer-start intent and next pad request until the chain terminates successfully.
Separate actor working-state updates from FIFO pop/push and visible pad updates.
Final HALT/termination/fault checks cancel the entire packet as in v3; fault or
lifecycle cancellation clears in-flight working state. A completed earlier FIFO
entry survives frame release. Maintain local three-bit committed DATA/OE/hold
requests, then pass through the unchanged independent guardian. Reset/raw kill/
watchdog/release suppress output immediately and flush busy/queued/commit-valid
state; a stale packet cannot commit into a reacquired frame. The host continues
to observe the actual FIFO; reserved RX pushes and TX retirements are reflected
in internal readiness, with pre-event flags retained for decisions. No full-RX
same-event pop rescue or empty-TX same-event push bypass is introduced.

**Temporal observer.** Keep the existing count/started/done state and observe the
synchronized level every core cycle, independently of serializer busy state.
Add a resident threshold/mode/level/valid descriptor (19 bits); registered
completion is consumed once. Seed the acquisition observation, clear on false,
reset and lifecycle boundaries, and count a second temporal entry only on a
later core observation. Delay/qualification units count real core cycles, not
microsteps. The shared timed sampler retains its separate registered events.

## State and latency allocation

| Added allocation | Bits |
|---|---:|
| µop register | 66 |
| Active event snapshot | 16 |
| One queued snapshot including valid | 17 |
| Visited / step / temporal-seen / action-seen | 23 |
| Deferred RX byte+push / TX pop / timer / pad / exception / valid / busy | 19 |
| Resident temporal descriptor | 19 |
| **Proposed total** | **160** |

No programmable state/configuration is added. P2 measures +66 declared bits
(+65 mapped FFs); **160 is a design allocation, not a measured integrated count**.
The remaining 94 FFs would cost 4,604.9472 µm² at the mapped dfrbpq area before
their logic/clock/buffering. This is a cost bound for the registers only.

With the head descriptor resident and successor fetch overlapping each execution
step, a chain of up to four operations plus commit adds at most five core cycles
(100 ns at 20 ns). Refetch after cancellation may add one further cycle; that
case is outside ordinary event-to-commit latency. Require >=8 core cycles between
eligible wire events and sufficient configured timer spacing for a batch;
unsupported arrival pressure faults. This is a new versioned latency contract,
not cycle-compatible frozen v3. Do not promise a faster maximum wire rate.

I²C ACK/handoff/stretch must be revalidated with the controller's resolved SCL;
existing 63-cycle setup has considerable digital margin, without hardcoding it.
SPI/UART/timed stream can retain their fixed actor path. Microwire needs the
continuous-word sample oracle with the new dispatch delay. LIN's break detector
must retain one-cycle interruption visibility; its prefix/timer configuration
must be recalibrated and checked against all 34 original cases. 1-Wire must retain
continuous low observations and release-relative delay, checked against all 18
repair cases. These are acceptance obligations, not newly claimed passes.
