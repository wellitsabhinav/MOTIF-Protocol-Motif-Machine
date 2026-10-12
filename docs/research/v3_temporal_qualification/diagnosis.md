# v2 temporal qualification audit

The historical classification remains
`MOTIF_V2_UNSEEN_PROTOCOL_GENERALIZATION_PARTIAL`. Its original configuration,
selected workload, oracle, reports and frozen manifest are unchanged. This audit
uses immutable source commit `490a50c3e03f1be96784fd27f9d64b718c2aa5cc` and treats
1-Wire initialization as a known repair workload. No future unseen workload has
been researched or selected.

## What the historical counterexample establishes

The selected controller sequence is LOW 200 us, HIGH 1 us, LOW 300 us at a
20 ns core period. Neither continuous LOW interval reaches the selected 480 us
minimum. The independent oracle measures controller pulse intervals and target
ownership, without consulting instruction PCs: see
[`oracle`](../../../tools/unseen_protocol.py) and the immutable
[`workload`](../../../experiments/exchange_decomposition/third_workload.json).

The preserved model and RTL agree, but both emit a false presence pulse at
cycles `[76247, 82240)`. Existing trace windows and timing evidence are in
[`third_counterexample.json`](../../../experiments/exchange_decomposition/third_counterexample.json),
[`third_result.json`](../../../experiments/exchange_decomposition/third_result.json)
and [`third_analysis.md`](../../../experiments/exchange_decomposition/third_analysis.md).
The malformed silence requirement is a campaign robustness contract, not a
claim about unspecified DS18B20 silicon behavior.

All cycles below are zero-based normalized trace cycles. Actors consume the old
second-stage frontend observation before the frontend advances its registers.

| Cycle | Observation or action |
|---:|---|
| 50000 | Controller begins LOW. |
| 50002 | Frontend reports falling/LOW; acquisition clears actors and starts timer. |
| 50015, 50029 | ALWAYS RX alignment fields complete after 13 and 14 firings. |
| 50030 | TX handoff consumes an FF token, presents an open-drain released bit and requests timer restart. |
| 50031 | Registered handoff request starts the 749-cycle timer. |
| 59768 / 59769 | Timer captures LOW; RX consumes its thirteenth sample next cycle. |
| 60000 | Controller releases HIGH. |
| 60002 | Frontend reports HIGH and rising on mapped pins 0–2. PC is RX slot 3, count 13; no instruction fires. |
| 60003–60051 | HIGH remains in the synchronized level, but active RX listens only to TIMER. |
| 60050 / 60052 | Controller returns LOW; frontend reports falling two cycles later. RX again ignores the edge. |
| 60517 / 60518 | Next timer capture/consumption sees LOW. The entire HIGH interval fell between samples. |
| 62016 / 62017 | First field completes as zero; masked field decision accepts. |
| 74000 / 74001 | Second field completes as zero; second decision accepts. |
| 75050 / 75052 | Final controller release reaches the rising-triggered level wait. |
| 75498 | First timer wait completes. |
| 76246 / 76247 | Timer event is registered and then consumed; chained response drives LOW. |
| 82240 | False presence ends after 119.86 us. |

The HIGH is observable. It is lost as transaction history rather than lost at
the frontend. `motif/events.py:18–24` and
`src/motif_event_frontend.sv:10–20` retain sampled levels and produce qualified
edges. `motif/motifs/transaction.py:69–84` and
`src/motif_transaction.sv:148–162` execute only the active entry's sources; edge
pulses have no backlog. The shared timer in `motif/motifs/timed.py:21–40` and
`src/motif_timed_sample.sv:20–36` samples at expiry and does not invalidate its
elapsed schedule on an intervening HIGH. Field decisions inspect accumulated
sampled data, which remains zero.

## Existing responsibilities and lifecycle

WAIT level mode tests the current input; WAIT timer mode tests a registered
sample event. Neither directly accumulates continuous matching observations.
The current table has sixteen 64-bit entries, all eight 3-bit opcodes allocated,
and a four-entry immediate execution limit. Only ALWAYS successors can chain;
events are not queued. Conflicting FIFO/TX operations and excess chains abort.

Falling framing acquires only while inactive. Level framing releases on HIGH
and also gates output enable from the raw frame input, so simply selecting
level framing prevents presence after controller release. The watchdog tracks
frontend activity and aborts on inactivity; expiry cannot serve as an accepted
duration predicate. It remains an independent safety override.

Core priority is reset/disable/abort/release/watchdog or fatal condition, then
acquisition, then normal execution. Release clears partial RX/TX, table state,
pending sample and timer start. Queued FIFO contents survive frame release;
reset clears FIFOs and sticky diagnostics. Timer start is registered after a
handoff, and sample capture is consumed one cycle later. See
[`execution-model.md`](../../execution-model.md), `src/motif_core.sv:51–89` and
`motif/engine.py:115–205`.

The host rejects configuration writes while enabled, validates a program before
enabling it, and packs eight little-endian bytes per entry. Configuration costs
1,096 bits including the 1,024-bit table. Unused flag bits were accepted and
ignored in v2; assigning v3 meaning to them requires an explicit interface
version/compatibility statement, not a promise about arbitrary old binaries.

## A configuration-only repair exists for the nine selected cases

The stronger claim that no existing primitive can observe an interruption while
waiting for a timer is incorrect. RESPOND capture mode observes two sources:
its trigger captures an input response and `value[1:0]` selects completion.
Capture has precedence when both occur together. The captured response is
retained until updated or the transaction clears. See
`motif/motifs/transaction.py:105–116` and `src/motif_transaction.sv:94–111`.

The new
[`candidate configuration`](../../../experiments/temporal_qualification/configurations/v2_dual_source_response.json)
uses period 2,999, a four-cycle ALWAYS RX alignment, one FF handoff token, eight
dual-source RESPOND entries, release detection, one timer delay, constant LOW,
two timer samples for pulse width, release and termination. Eight timer
completions consume 23,992 cycles; the restart alignment and registered event
latency put final qualification at acquisition +23,999. All sixteen slots are
occupied. The candidate observes RISING interruption edges during the eight
RESPOND entries and rejects at the next timer event using the response latch.

The pinned-source reproduction passes all nine unchanged selected oracle cases
with exact model/RTL agreement over 1,302,050 cycles. The three additional
negative probes also match across model and RTL over 387,550 cycles, for a
total of 1,689,600 compared cycles. Evidence and selected trace windows are in
[`v2_composition_baseline.json`](../../../experiments/temporal_qualification/v2_composition_baseline.json).
Run `python -m tools.temporal_baseline` to reproduce from an isolated Git archive
of the pinned v2 source. The harness writes full traces only under `build/` and
checks the immutable source/trace compiler before and after. A separate
exploratory model-only boundary probe rejects 23,999 continuous LOW cycles and
accepts 24,000 and 24,001 cycles; do not infer RTL qualification for those
additional boundary probes from the original nine cases.

This is a new composition audit. It does not revise the historical architecture
freeze, classification or unseen result.

## Additional negative evidence

The same independent oracle is applied to three precisely specified additional
stimuli in
[`v2_composition_probes.json`](../../../experiments/temporal_qualification/v2_composition_probes.json).
The oracle remains unchanged, and full normalized model/RTL traces agree for
all three probes. Their measured negative results are:

| Added probe | Independent expectation | Matching candidate model/RTL observation |
|---|---|---|
| LOW 1 cycle / HIGH 1 cycle / LOW 23,998 cycles | No presence; both LOW intervals are short | False presence `[77000,82999)`: interruption occurs during alignment, before the response monitor. |
| LOW 10,000 cycles / HIGH 50 cycles / LOW 24,000 cycles | One presence after final release 84050 | No presence: delayed rejection misses the new falling edge while the frame is active. |
| Continuous LOW 29,500 cycles (590 us) | One presence, delayed 15–60 us from release 79500 | Presence `[79999,85998)`, delayed only 9.98 us because its timer phase remains anchored to acquisition. |

Each probe has 50,000 HIGH idle cycles before and after traffic and the original
four pretraffic FF tokens at cycles 8–11. These are known-workload audit probes,
not a future unseen selection. They establish limits of this configuration;
they are not an exhaustive proof over every possible sixteen-entry table.

The architectural hypothesis to preregister is therefore a compact continuous
predicate responsibility with complete sample coverage, restart/branch behavior
and configured duration independent of the shared sampling timer. Its value
must be tested beyond fixing the nine historical vectors.

## Two reviewed generic model/RTL correspondence defects

PR #10 review also found two synthetic chained-action disagreements outside
the qualified protocol profiles. Preserve these separately from the temporal
gap and correct the model against the existing source contract before relying
on new chained tests.

| Reproduction | First discrepancy | Source correspondence |
|---|---|---|
| [`handoff_wait`](../../../experiments/temporal_qualification/review/handoff_wait/model.jsonl) | Cycle 25: TIMER-triggered TX handoff loads 80 then chains a validating timer WAIT. Model compares the newly loaded TX bit, passes and pops FIFO; RTL compares the pre-edge TX bit, raises mismatch and cancels the load/pop. | WAIT uses the pre-edge TX datapath input in RTL (`src/motif_transaction.sv:203–204`). Model uses mutated `tx.bit` (`motif/motifs/transaction.py:155`). Snapshot the pre-edge bit for this predicate. |
| [`terminate_commit`](../../../experiments/temporal_qualification/review/terminate_commit/model.jsonl) | Cycle 18: one-bit RX chains DECIDE/enqueue then terminating HALT. Model retains the new FIFO byte; RTL cancels the same-cycle enqueue. | RTL cancels FIFO/TX actions on termination (`src/motif_transaction.sv:244–245`), preserving earlier queued contents. Model termination clears actors without rolling back the same-cycle operation. |

These findings refine model/source correspondence and atomic action priority.
They do not invalidate the established qualified I2C/Microwire traces or prove
that another primitive family is required. Source-line references describe
the pinned v2 implementation; v3 line numbers may move.
