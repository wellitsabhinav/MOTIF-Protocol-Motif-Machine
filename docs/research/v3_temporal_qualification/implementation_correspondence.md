# Model correspondence corrections

The immutable [preregistration](preregistration.json) remains unchanged at
commit `637aeb947e7726ce0ef6347f0788c2803149f091`, with LF-normalized SHA-256
`2c294fc24c46c0a14bb16e24087ece1fbb60e347939536fedd9141ce1ed21522`.
The corrections below make the model describe existing RTL priorities. They
are separate from the new tagged WAIT responsibility; no shared timer or
frontend RTL was redesigned.

| Preserved reproduction | Original disagreement | Implemented correspondence |
|---|---|---|
| [Handoff followed by WAIT](../../../experiments/temporal_qualification/review/handoff_wait/model.jsonl) | The model validated a newly loaded TX bit; RTL validated the pre-edge bit. | Snapshot the pre-edge TX value for WAIT validation. |
| [Enqueue followed by terminating HALT](../../../experiments/temporal_qualification/review/terminate_commit/model.jsonl) | The model retained a same-cycle FIFO enqueue that RTL cancelled. | Roll back same-cycle FIFO operations on terminating HALT, retaining previously queued contents. |
| [Registered timer end coincident with acquisition](../../../experiments/temporal_qualification/review/timer_end_acquisition/finding.json) | The model acquired a new frame while existing RTL gave the registered validation end priority. A related table-mode valid-stop path accessed an ordinary UART assembly field that did not exist. | Give the registered end the existing RTL lifecycle priority, preserve sticky invalid-start/stop diagnostics, and route ordinary validated RX deposits only in the ordinary non-table receiver. |

The third discrepancy was reproduced in isolated frozen v2 source
`490a50c3e03f1be96784fd27f9d64b718c2aa5cc`, using an ordinary CONTINUE entry.
Its negative trace, the initial v3 discrepancy, and corrected v3 agreement are
preserved separately. It was therefore inherited, rather than introduced by
temporal WAIT. Source and trace identities are in the linked finding.

The model timer update now mirrors the existing RTL's autonomous registered
timer behavior, including its start-before-clear priority. A simultaneous
registered end and fresh acquisition clears transaction state, while the
existing acquisition timer-start signal can restart the timer. An inactive
transaction does not by itself stop that timer. These behaviors are recorded
for correspondence; they are not a newly proposed timing mechanism.

The preregistration explicitly permits the first two corrections and matching
model/RTL implementation. Applying that correspondence requirement to the
third inherited discrepancy is an implementation interpretation, recorded here
without modifying the preregistration. The prohibition on shared timed-sampling
redesign remains in force: `src/motif_timed_sample.sv` and the standalone timed
sampling model retain their historical implementation.

Focused tests preserve each priority. The added 40-cycle timer-end/acquisition
fixture also has an independent wire expectation: no target marker. Final
qualification reports must identify the tested source hashes; earlier
implementation-run reports cannot substitute for source-matched receipts.
