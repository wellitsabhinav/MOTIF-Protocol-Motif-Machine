# Continuous temporal qualification options

This comparison precedes implementation. The known 1-Wire initialization case
is a repair workload. No future unseen workload has been researched or selected.
The architectural question is whether one generic temporal responsibility can
represent persistent predicates with explicit interruption handling while
preserving qualified profiles.

The
[`diagnosis`](diagnosis.md) distinguishes the historical sampled-field failure
from a configuration-only composition that passes its nine selected cases with
exact model/RTL agreement. Three additional matching probes expose early interruption blindness, missing
active-epoch restart and timer-phase dependent response delay. These findings
justify testing a stronger temporal capability; they do not prove impossibility
over all v2 tables.

## Candidate comparison

| Criterion | A: dedicated temporal instruction | B: tagged WAIT qualification | C: guarded shared timer |
|---|---|---|---|
| Responsibility | Explicit persistent predicate action | Persistent predicate is a new WAIT completion policy | Timer validity depends on continued predicate satisfaction |
| Encoding | All eight opcodes are used; widening would violate table/configuration budget, so a tagged form is still needed | Reuse WAIT flag bits, mask threshold and existing level operand; table remains 16 x64 | Needs guard mode, predicate, threshold override and ownership routing |
| State | Separate counter plus lifecycle | Separate 16-bit counter plus minimal lifecycle | May reuse timer counter, with guard/ownership lifecycle state |
| Orthogonality | Clear semantic family | Clear family without growing opcode width; existing WAIT modes retain meaning | Couples qualification to sample scheduling, timer validation and handoff |
| Composition | Stalls PC until success/interruption branch | Same bounded stall/branch conventions as WAIT | Must prevent timer events from reaching unrelated RX/WAIT consumers |
| Race risk | Acquisition seed, completion registration and chained entry changes | Same races; isolate from existing timer | Also timer start/clear priority, stale sample events, guard invalidation and timer release |
| Compatibility risk | New decoder/encoding responsibilities | Qualified old profiles have no temporal tag | Existing UART and I2C setup share the modified timer |
| Area hypothesis | Small counter logic, but wider opcode is unacceptable | Modest counter/comparator and decode; actual area must be measured | Fewer added flops possible, but extra mux/ownership logic may offset savings |
| Verification | Independent persistence oracle + lifecycle | Same; old modes remain directly regression-testable | Must verify old timer behavior plus ownership/phase interactions |
| Potential reuse | Minimum HIGH/LOW, delay, branch/restart | Same generic uses | Generic guards are useful but more globally coupled |

Potential applications are hypotheses only. The campaign must not count
debounce, BREAK, wake-up or any other untested use as a validated protocol.

## Selection

Choose **B: one TEMPORAL_QUALIFY responsibility encoded as a tagged WAIT family**.
The public helper/name can identify temporal qualification even though the
physical opcode remains WAIT. This avoids opcode/table growth and preserves
shared timer semantics. The full selected contract and fixed budgets are in
the immutable preregistration; this document does not replace it.

Use unused WAIT flags to opt in, `mask[15:0]` for a 1–65,535-cycle threshold,
and `value[0]` for the required synchronized RX level. A constant-true delay is
the same consecutive-predicate operation, with no input interruption. Restrict
temporal entries to ALWAYS trigger so they cannot accidentally subsample the
predicate. Reject illegal encodings in both model and host RTL before enable.
Do not allocate new configuration storage. Host interface version becomes 3;
table size, register addresses and byte order remain unchanged.

Allocate a separate 16-bit counter, started bit and registered-complete bit:
18 planned added state bits, below the 24-bit cap. The counter belongs to the
current temporal entry; lifecycle/entry changes must discard stale progress.
Success selects `next`; interruption of a started partial qualification either
restarts in place or selects `alternate`. Initially false level predicates wait
without taking the interruption branch. Cancel/reject behavior composes through
the alternate destination instead of adding protocol outcomes to the primitive.

The acquisition observation counts for temporal entry zero after clearing the
old epoch. The first matching observation counts as one, and the T-th matching
observation registers success. Success is consumed on the following executor
cycle; subsequent input changes do not revoke it. A false would-be T-th sample
prevents success. A chained temporal entry can count the current observation,
but a second temporal entry in the same cycle is deferred to avoid multiple
counter advances. Keep the existing four-entry execution bound.

Reset, disable, abort, release, watchdog and fatal conditions clear qualification
before normal actions. Preserve raw guardian output suppression and frontend
sampling/provenance behavior. This capability makes no analog or unsampled
subcycle pulse guarantee.

## Cost and qualification gates

The existing table costs 1,024 bits and total configuration costs 1,096 bits.
Frozen v2 mapped area is 194,376.3318 square micrometres with 12,546 cells and
1,385 mapped register cells. These are synthesis figures, not routed physical
qualification. The fixed area ceiling is 213,813.96498 square micrometres:
10% above frozen v2, using the same top, tools and CMOS5L typical library.

The additional counter cost and decode critical-path effect are unmeasured
hypotheses until model/RTL qualification and paired synthesis. Do not optimize
before the cost gate or claim physical success from synthesis. The existing
transaction module's 70,237.9944 square micrometres indicates that table decode
is already substantial, but does not by itself predict the new area delta.

Verify both predicate levels, constant-true delay, threshold one and 65,535,
below/exact/above durations, one-cycle and repeated interruptions, completion
boundaries, acquisition/chaining, reset/disable/watchdog/fatal clearing and
back-to-back qualification. Run the unchanged nine repair cases, added audit
probes and independent legal timing sweeps. Correct the two documented model
correspondence defects against existing RTL responsibility; preserve their
original counterexamples. Then require all previously qualified workloads,
lint/formal and host configuration checks to pass.

Only after these gates and the fixed state/configuration/area budgets pass may
v3 be frozen and a future unseen workload be researched. Freeze and selection
must be separate immutable commits. A post-freeze semantic gap ends this
campaign; it does not authorize another primitive or candidate substitution.
