# Unseen result and stop decision

Result: `MOTIF_V2_UNSEEN_PROTOCOL_GENERALIZATION_PARTIAL`.
The selected workload and its malformed-input contract remain unchanged.
All 1,302,050 normalized cycles match the independent v2 model and RTL. Eight
of nine cases satisfy the independent timing/ownership oracle. The case
`interrupted_non_reset` fails both implementations in the same way.

The controller drives low for 200 µs, releases for 1 µs, then drives low for
300 µs. Neither continuous low reaches the selected 480 µs reset minimum.
The oracle requires no presence. The target nevertheless drives a presence
pulse starting at 1524.94 µs from the case origin, lasting 119.86 µs. Target
ownership and pulse timing are otherwise correct. The failed qualification
is preserved, including the input and full model/RTL trace hashes, in
`third_result.json`; `third_counterexample.json` retains the high interruption,
field decisions and false response as inspectable normalized trace windows.

The configuration uses 27 initial ALWAYS receive ticks to align the existing
handoff timer restart, two 16-bit timer-sampled fields, masked zero decisions,
a rising-edge wait for release, two timer waits, a constant-low response,
eight timer samples to measure its length, release and termination. Four FF
tokens are loaded before traffic; one is consumed per attempted frame so the
existing handoff can arm the timer while releasing open-drain DQ. No data
shifting, host command or external state machine supplies the presence response.
These tokens and alignment entries are visible support costs and a cumbersome
configuration, not new reusable operations.

The 1 µs high gap is observed by the synchronized frontend but falls between
14.98 µs field samples. FIELD_DECISION sees only the accumulated sampled field.
It cannot establish that the wire remained low between samples. While RX waits
for its selected timer event, the single PC cannot also consume the high edge
to restart or reject duration qualification. WAIT_POLICY tests readiness,
timer expiry or a current level; it has no independently persistent elapsed-low
predicate. Falling-edge framing acquires only when inactive; level framing
would release the frame at the controller release needed to trigger presence.
The watchdog can abort on inactivity but cannot turn expiry into acceptance.

The isolated missing responsibility is **continuous input-level duration
qualification with interruption restart/rejection**. It can be described
without a protocol name. The existing response, handoff, ownership, legal
timing boundaries, back-to-back, long idle, reset and timeout behavior work in
this bounded attempt, supporting PARTIAL rather than a claim that a dedicated
1-Wire controller is required. No new operation was added. This is a tested
configuration counterexample plus a source-level semantic diagnosis, not an
exhaustive proof over every possible sixteen-entry program.

The silence requirement for malformed short pulses was preregistered before
implementation. It is stronger than the source's description of legal
initialization; this result must not be represented as proof about unspecified
DS18B20 silicon behavior, or as failure of every possible 1-Wire subset.

The v2 manifest, RTL, model, host decoder, packing compiler, generic trace
compiler, routing and physical inputs are identical before and after the
attempt. No post-result freeze or second semantic repair occurs. The failed
workload is excluded from validated-user counts. Full CMOS5L qualification
is NOT_REACHED under the three-success gate; all v2 placement, STA, routing,
DRC, LVS, precheck and routed-netlist host results are unavailable.
