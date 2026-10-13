# MOTIF v3 controlled temporal qualification

## A. Executive classification

The logical and local matched-cost qualification gates pass. V3 maps to
210,241.9746 µm², 8.1623% above frozen v2, within the fixed 10% cap. The architecture
is frozen. The independently selected LIN break/sync prefix passes its 34-case
unseen logical gate without semantic changes. The initial physical attempt ended
cancelled without published physical archives. Physical qualification remains
incomplete while diagnosed flow revisions are prepared. Logical generalization and cost qualification
do not establish physical closure. [Gate receipts](../../../experiments/temporal_qualification/),
[cost receipt](../../../experiments/temporal_qualification/synthesis.json).

## B. Starting frozen state

Established fact: work started from clean `490a50c3e03f1be96784fd27f9d64b718c2aa5cc`
with 109 passing tests and both historical freeze checks. PR #10 was reviewed
against its green head, with two out-of-profile model discrepancies documented,
then merged as `5601be5c15a844e4a1ebdb13c15ea17034f38fa5`. The v3 branch starts
there. [Starting evidence](../../../experiments/temporal_qualification/starting_state.json).

The legacy BYTE_EXCHANGE result remains A5FF rather than A55A. Frozen v2 retains
`MOTIF_V2_UNSEEN_PROTOCOL_GENERALIZATION_PARTIAL`, including eight passing
1-Wire cases and one false-presence failure. No historical oracle, configuration,
result or manifest was rewritten. [Legacy boundary](../../../experiments/generalization/promoted_motif_vocabulary.json),
[v2 boundary](../../../experiments/exchange_decomposition/frozen_v2_manifest.json),
[v2 result](../../../experiments/exchange_decomposition/third_result.json).

## C. v2 temporal failure diagnosis

Measured result: after LOW 200 µs, the frontend observes HIGH at cycle 60002.
The active timer-triggered RX ignores that observable interruption; subsequent
sampled fields remain zero and permit false presence. This is a loss of
transaction history, rather than an unobserved input pulse.
[Cycle audit](diagnosis.md), [historical counterexample](../../../experiments/exchange_decomposition/third_counterexample.json).

A new configuration using existing dual-source response capture passes all
nine original cases in both model and RTL, over 1,302,050 cycles. It fails
startup interruption, restarted-valid-low and release-relative timing probes,
also with exact model/RTL agreement, over another 387,550 cycles. These are
comparison results, not a proof that every possible v2 configuration fails.
[Identified comparison](../../../experiments/temporal_qualification/v2_composition_baseline.json).

## D. Architectural alternatives considered

Separate temporal instructions offer a clear responsibility, but all eight
opcodes are occupied and widening conflicts with the configuration budget.
Guarding the shared timer reduces potential counter duplication but couples
qualification to validation, handoff, phase and registered expiry. Persistent
WAIT reuses operands and bounded sequencing while isolating continuity from
sampling. It was chosen before implementation.
[Comparison and rationale](architectural_options.md).

## E. Preregistered temporal abstraction

Established fact: immutable preregistration commit
`637aeb947e7726ce0ef6347f0788c2803149f091` precedes the model change. Its JSON
SHA-256 with CRLF normalized to LF is
`2c294fc24c46c0a14bb16e24087ece1fbb60e347939536fedd9141ce1ed21522`.
[Machine contract](preregistration.json), [readable rationale](preregistration.md).

Tagged WAIT qualifies T consecutive synchronized observations, counting the
first as one. RX-level mode and constant-true delay are the only predicates.
An interrupted partial interval restarts or branches; initially false waits.
Success is registered and consumed next executor cycle. Acquisition may count
its observation but suppresses ordinary actions. Chaining counts at most once
per cycle and defers a second temporal entry. Lifecycle/fatal clearing removes
stale progress and completion. Pulses unobservable to the frontend are outside
the claim.

## F. Implementation

The table remains sixteen 64-bit entries with eight opcodes. WAIT flag bit 2
selects temporal semantics; argument 3 selects RX persistence, argument 2 delay,
mask specifies 1–65,535 observations, and flag bit 3 selects alternate branching.
Temporal entries require ALWAYS and reject reserved operands. Public helpers
and host validation agree; register 21 reports version 3. Formerly ignored
tag bits acquire meaning, so arbitrary old ignored-bit binaries are not a
compatibility claim. [Encoding and helpers](../../../motif/transaction.py),
[transaction RTL](../../../src/motif_transaction.sv), [host interface](../../host-interface.md).

One 16-bit count and two lifecycle bits have one sequential writer. Generic RTL
contains no workload names, reset/presence timing constants or protocol-specific
FSM. The four-entry chain bound, guardian, configuration immutability and
pre-edge FIFO choices remain. Three inherited model correspondence corrections
are documented separately, with original negative traces. The third correction
is explicitly recorded as an interpretation of the preregistered matching
model/RTL requirement; the preregistration was not revised.
[Correspondence record](implementation_correspondence.md).

## G. Temporal edge-case verification

Measured result: 55 independent wire-marker fixtures pass exact augmented
model/RTL comparison over 395,249 cycles. They cover both levels; thresholds
1, 2, 4, 16 and 65,535 below/equal/above; interruption positions and policies;
long idle; delay; reset, abort, disable, watchdog and release; chained entries;
and registered timer-end/acquisition priority.
[Temporal receipt](../../../experiments/temporal_qualification/temporal.json),
[independent fixture expectations](../../../tools/temporal_vectors.py).

The model exhausts all 128 seven-observation bit sequences at thresholds 1–4
for both levels: 1,024 sequences checked by a run-length oracle. Bounded RTL
properties prove the stated safety properties at thresholds 1–4 over 12 steps.
They are bounded safety evidence, not an unbounded proof or a proof for every
table. Existing guardian and watchdog proofs also pass.
[Model tests](../../../tests/model/test_temporal.py), [properties](../../../formal/temporal.sv),
[regression receipt](../../../experiments/temporal_qualification/regression.json).

The first Linux CI attempt failed before SAT because its newer Yosys retained
clock-triggered assertion cells. Compatible lowering preserves the same clocked
checks and bounds; corrected CI passes them. No assertion or RTL was weakened.
[Failure record](../../../experiments/temporal_qualification/review/ci_formal_lowering.json),
[formal driver](../../../tools/formal_check.py).

## H. 1-Wire repair result

Measured result: all 18 repair cases pass, including the nine unchanged
historical stimuli/oracles, over 2,167,672 compared cycles. LOW 200 µs / HIGH
1 µs / LOW 300 µs emits no presence. Startup interruption, restarted valid reset,
590 µs reset and six deterministic legal-length/release-phase probes pass.
[Repair receipt](../../../experiments/temporal_qualification/repair.json).

Configuration composes LOW qualification for 24,000 observations, release
waiting, 1,500-observation delay, existing LOW response, 6,000-observation pulse
delay, release and termination. It contains no alignment or FIFO timer-start
tokens. At the bounded 50 MHz workload, nominal presence begins 30.04 µs after
release and lasts 120.02 µs, satisfying the unchanged wire oracle. These are
measured wire intervals, distinct from internal observation counts.
[Configuration](../../../experiments/temporal_qualification/configurations/one_wire_reset_presence.json).
This is training/repair evidence, not an unseen generalization result.

## I. I²C regression

Measured result: the original 48 cases retain identical stimulus and match
frozen v2 visible traces over 88,287 cycles, with full v3 model/RTL agreement.
The pinned reproduction also preserves the legacy external-equivalence gate.
Coverage retains repeated START, ACK/ninth clock, pressure, starvation,
malformed clocks, lifecycle, first-bit and concurrent host/FIFO behavior.
[Regression receipt](../../../experiments/temporal_qualification/regression.json),
[historical gate](../../../experiments/exchange_decomposition/i2c_logical.json).

## J. Microwire regression

Measured result: the independent bounded READ oracle observes exact A55A,
dummy zero, uninterrupted sixteen-bit output and correct rising-edge advance
over 1,970 compared cycles. DI/DO remain separate and the target never drives
CLK. Runtime tests retain back-to-back operations.
[Regression receipt](../../../experiments/temporal_qualification/regression.json),
[runtime receipt](../../../experiments/temporal_qualification/cocotb.json).

## K. SPI/UART/timed-stream regression

Measured result: existing RTL mode comparisons, FIFO/concurrency and protection
checks, lint, bounded checks and all five runtime host tests pass. Selected
demonstrations receive SPI 3C while returning A6, UART 55 A6 and timed stream
55 AA. These are bounded profiles, not complete protocol stacks.
[Regression receipt](../../../experiments/temporal_qualification/regression.json),
[demonstration expectations and observations](../../demo/demonstrations.json).

## L. v3 synthesis/accounting

Measured result: matched mapping passes. Declared accounting measures 18 added state bits
and zero added configuration bits. Configuration remains 1,096 bits, including
the 1,024-bit table; declared total state is 1,398 bits versus v2's 1,380.
Mapped cell counts are a separate measurement. The hard cap remains
213,813.96498 µm² and at most 1.10 times the matched v2 mapping.
[Accounting receipt](../../../experiments/temporal_qualification/accounting.json),
[synthesis receipt](../../../experiments/temporal_qualification/synthesis.json).

| Measurement | Frozen v2 | V3 | Delta |
|---|---:|---:|---:|
| Typical mapped area (µm²) | 194,376.3318 | 210,241.9746 | +15,865.6428 (+8.1623%) |
| Total mapped cells | 12,546 | 13,332 | +786 |
| Sequential cells | 1,385 | 1,403 | +18 |
| Combinational cells | 11,161 | 11,929 | +768 |
| Declared register bits | 1,380 | 1,398 | +18 |
| Configuration bits | 1,096 | 1,096 | 0 |
| Table bits | 1,024 | 1,024 | 0 |

The pair uses identical Yosys 0.30+48 `b5b0b7e83`, identical ABC executable,
top module and pinned typical CMOS5L Liberty SHA-256
`34163f3e7de9f854afac57332ba06f1739b78e7ac35660a8a5ddd39c570124ad`.
Executable, source and netlist hashes are recorded. Frozen v2's historical area
is reproduced exactly. No cost-evading optimization was performed.

Independent Linux CI at source `383e494` passes all required jobs, including
matched cost. Its separately pinned OSS suite maps v3/v2 to 198,921.933 /
187,638.4062 µm². This additional pair has different tool conditions from the
historical local baseline; it does not replace the local 8.1623% cap decision.
Full simulation/netlist artifacts are published by the identified run.
[CI receipt](../../../experiments/temporal_qualification/ci_qualification.json),
[green run](https://github.com/wellitsabhinav/MOTIF-Protocol-Motif-Machine/actions/runs/38293882738).

## M. v3 freeze identity

Established fact: separate immutable freeze commit
`638c2ee4e7c9f53c64e6f660331747e5a79b570d` records manifest LF SHA-256
`71d5b07b5524fb6fa702357291eb35f52eccc5861111f7824b6fb9ead98a3047`.
Creation followed a clean committed source tree, complete passing qualification
receipts and budgets satisfied. Original executed source identities, byte-equal
dependency checks and narrowly scoped evidence bindings remain in the receipts.
Validation rejects truncated/duplicate case
sets, model-only receipts and stale source hashes. Initial physical inputs are
identified separately from the semantic boundary.
[Immutable manifest](../../../experiments/temporal_qualification/frozen_v3_manifest.json),
[freeze machinery](../../../tools/v3_inventory.py), [preregistered freeze rule](preregistration.json).

## N. New unseen protocol selection

Established fact: independently delegated primary-source research began after
the freeze. The candidate matrix ranks LIN break/sync, UART BREAK/gap,
AT21CS01 reset/discovery, ISO 7816 warm reset/ATR prefix and PS/2 inhibit/release
by structural independence, temporal falsification and bounded scope. LIN was
selected once, at commit `5f67d888df07a7e76f814a8df9984394a951f7ac`, before its
configuration. Selection LF SHA-256 is
`f3e6d9b7661d61f07b390f0225deb43eeb03e5819dfd2d2191efc628d1a61663`.
The complete official LIN 2.2A PDF was retrieved and hashed. Ranking scores are
research judgments, rather than measured implementation properties.
[Candidate matrix](unseen_candidate_matrix.md), [selection rationale](unseen_selection.md),
[immutable electrical contract](../../../experiments/temporal_qualification/unseen/selected_workload.json).

## O. Unseen protocol result

Measured result: all 34 committed LIN cases pass the independent electrical
oracle and full augmented model/RTL comparison over 3,210,266 cycles. The
semantic manifest verifies identically before and after. Cases include
11-bit receiver threshold below/equal/above, the distinct 13-bit master minimum,
observable one-cycle HIGH splits, repeated interruptions, malformed sync/stop,
stale-header rejection, fresh-break recovery while awaiting sync, lifecycle
cuts, two prefixes and nine legal length/phase probes. Four runtime host cases
also pass actual table loading, receive-only pad checks and posttraffic FIFO
drain; that subset does not replace the dense timing gate. The local test set
passes: 204 model/tooling tests plus all 15 receipt guard checks, including
44 independent oracle tests in the first group.
[Logical receipt](../../../experiments/temporal_qualification/unseen/logical_result.json),
[runtime host receipt](../../../experiments/temporal_qualification/unseen/runtime_host_result.json),
[executed-source binding](../../../experiments/temporal_qualification/unseen/source_binding.json).

Independent pinned Linux CI repeats the 34-case gate, runtime checks and four
demonstrations at evaluated source `01fa51d`; all regression and cost jobs also
pass. The published full-evidence ZIP is 57,889,637 bytes and its download
matches the published SHA-256. Extracted CI and local receipts identify
identical executed evaluation source bytes.
[CI receipt](../../../experiments/temporal_qualification/unseen/ci_result.json),
[full CI artifact](https://github.com/wellitsabhinav/MOTIF-Protocol-Motif-Machine/actions/runs/38347135337/artifacts/11789508413).

Scope is fixed nominal 20 kbit/s transceiver-normalized digital prefix
recognition. FIFO `0x55` is an experiment acceptance token; all eight target
output enables remain zero. Nominal acceptance is observed at core cycle
79,256, inside the independent stop-cell window. Sixteen entries compose
continuous LOW qualification, guarded replacement-break classification and
existing timed sampling. No model, RTL, frontend, timer, vocabulary or state
change was needed. This establishes one bounded unseen logical pass, not
autobaud, full LIN frames, analog compliance or physical closure.
[Configuration and boundary argument](unseen_lin_configuration.md),
[independent oracle](../../../tools/lin_oracle.py), [stop rule](preregistration.json).

## P. Physical qualification

The initial v3 attempt ran on merged source
`5467fd4d15a18dda9bc58a93bb3182b03629aa4b`, after green reviewed PR #12. Its
immutable intent was committed before dispatch, with the original separately
identified physical inputs at 6×4 and 20 ns. Its GDS job ended cancelled after
6 h 27 s; the log does not establish the cancellation cause. Official precheck
and routed-netlist tests were skipped, and only a documentation PDF was
published. No final physical archive, corner STA, DRC, LVS or layout view is
available. The attempt is **not physically qualified**.

The completed log records CTS entering the next stage after 18.995 s,
post-CTS repair after 12,869.929 s, and global routing after 965.350 s.
Global overflow was 10,846. Detailed routing last reported 7,628 violations at
80% of an optimization iteration before cancellation; this is partial progress,
not final DRC. The actual log and intermediate observations retain their
source and raw-byte identity. At most two diagnosed setting revisions may
follow; frozen semantics, allocation and clock remain fixed.
[Terminal result](../../../experiments/temporal_qualification/physical/attempt_1_result.json),
[partial observations](../../../experiments/temporal_qualification/physical/attempt_1_log_observations.json),
[diagnosis](physical_attempt_1_diagnosis.md),
[Initial intent](../../../experiments/temporal_qualification/physical/attempt_1_intent.json),
[dispatch receipt](../../../experiments/temporal_qualification/physical/attempt_1_dispatch.json),
[completed physical workflow](https://github.com/wellitsabhinav/MOTIF-Protocol-Motif-Machine/actions/runs/38349981124),
[flow identity](../../../flow-lock.json),
[physical restriction](preregistration.json).

Attempt 2 is prepared at exact source
`f55553a2b10b0880268663d8f06067c5ba1e14e0`: density 45 and integer threads 4.
Its immutable intent precedes dispatch. The initial failed attempt remains
the only dispatched run in this ledger; no revised result is claimed.
[Prepared dispatch identities](physical_attempt_2_dispatch.md),
[attempt 2 intent](../../../experiments/temporal_qualification/physical/attempt_2_intent.json).

## Q. PPA comparison

Temporal qualification costs 18 declared bits and 15,865.6428 µm² in this
matched mapping, principally additional combinational logic: +768 combinational
cells versus +18 sequential cells. Initial physical logs report intermediate
20,115 cells and 265,486.64 µm² after antenna insertion. Unlabelled resizer
setup progress still had WNS −6.745 ns and TNS −1,247.8 ns with 198 violating
endpoints; its later hold table had WNS +0.100 ns and TNS 0.000 ns. These are
estimated intermediate observations with individual corner attribution
unavailable, not final extracted STA. No v3 power,
final routed area or maximum frequency is available. No matched v2 physical
baseline exists for these intermediate values; they cannot replace the
preregistered nominal mapping comparison. Earlier routed results retain their earlier source scope and cannot
qualify v3. [Historical physical scope](../../physical.md).

## R. Demonstration artifacts

Measured result: eleven demonstrations pass over 702,987 compared cycles,
including four selected LIN cases in addition to the seven qualified profiles.
`python -m tools.demo --all --schematics` produces plain HTML at
`build/demo/index.html`, real waveforms, ordered execution timelines,
configuration summaries, expected/observed results and concise trace excerpts.
Cache reuse requires matching source, stimulus and artifact identities; failed
validation exits nonzero. Selected editable and rendered artifacts are committed;
full traces, caches, simulator outputs and netlists remain ignored build outputs
and reproducible CI artifacts. [Demonstration inventory](../../demo/demonstrations.json),
[guide](../../GETTING_STARTED.md).

The downloaded [CI plain HTML package](https://github.com/wellitsabhinav/MOTIF-Protocol-Motif-Machine/actions/runs/38385913225/artifacts/11806692626)
was checked against its published ZIP digest and manifest: all 464 listed files
match, every local HTML link resolves, and all eleven demonstrations pass.
This package identifies source head `052beae`; it predates the terminal physical
diagnosis. [Delivery verification](../../../experiments/temporal_qualification/delivery.json).

## S. Architecture diagrams

Actual module/interface inventories generate the connected core, top-level and
legacy→v2→v3 views. JSON connectivity/inventory sources and SVG/PNG renders are
provided together. These are views of the identified circuit, not measured
layout. [Core](../../demo/figures/architecture/architecture.svg),
[top](../../demo/figures/architecture/top.svg), [evolution](../../demo/figures/architecture/evolution.svg),
[identities](../../demo/figures/architecture/identity.json).

## T. Protocol waveforms

Waveforms derive from RTL simulation and timelines from actual ordered executor
observations. Both valid 1-Wire presence and interrupted-low silence are shown.
A cycle-level zoom shows synchronized HIGH, cleared progress and fresh restart.
The historical false presence and new v2 composition negatives have separate
identities and labels. [Protocol figure index](../../demo/README.md),
[interruption zoom](../../demo/figures/one_wire/interrupted_non_reset/waveform_59990_60060.svg),
[historical failure](../../demo/figures/historical/v2_interrupted_low/waveform.svg).

The selected LIN figures show nominal recognition, interrupted false break,
pending-sync recovery and two prefixes. A focused view shows a raw HIGH at
35,000, synchronized HIGH at 35,002, immediate progress clearing, and no token.
[LIN interruption zoom](../../demo/figures/unseen/one_cycle_high_split/waveform_34995_35012.svg),
[LIN nominal timeline](../../demo/figures/unseen/nominal/timeline.svg),
[focused RTL excerpts](../../demo/figures/unseen/focused_views.json).

## U. Synthesized schematics

Yosys proc/opt-derived views show real elaborated top-level, PC and temporal
connectivity; they are explicitly labeled elaborated, rather than technology
mapped. Separate measured CMOS5L views show actual mapped hierarchy counts and
PC/counter bit-0 neighborhoods, with exact cell types, port directions, net-bit
links and explicit omitted logic. The renderer validates measured source,
netlist and library hashes and does not rerun synthesis.
[Transaction view](../../demo/figures/architecture/transaction.svg),
[temporal view](../../demo/figures/architecture/temporal.svg),
[mapped hierarchy](../../demo/figures/mapped/hierarchy.svg),
[mapped PC](../../demo/figures/mapped/transaction_bit0.svg),
[mapped counter](../../demo/figures/mapped/temporal_bit0.svg),
[mapped identities](../../demo/figures/mapped/identity.json),
[reproduction script](../../demo/render_mapped.py).

## V. GDS/floorplan/routing visuals

Unavailable because the initial identified v3 workflow published no physical archive. No
historical layout is presented as a v3 result and no physical view is fabricated.
[Physical scope record](../../physical.md), [campaign gate order](preregistration.json).

## W. Negative evidence

Permanent negatives include legacy A5FF and frozen v2 false presence. New
comparison negatives establish three failures of one configuration, without
claiming exhaustive impossibility. Three inherited model correspondence
counterexamples and the diagnosed CI lowering failure are also retained.
[Historical report](../../../experiments/exchange_decomposition/report.md),
[comparison evidence](../../../experiments/temporal_qualification/v2_composition_baseline.json),
[correspondence record](implementation_correspondence.md).

The initial physical attempt is retained as an unsuccessful cancelled run with
remaining setup violations, routing congestion and unavailable final gates.
[Physical negative](../../../experiments/temporal_qualification/physical/attempt_1_result.json),
[diagnosed partial evidence](physical_attempt_1_diagnosis.md).

## X. Evidence strength

Established facts are commit order, immutable bytes and actual interfaces.
Measured results are independent bounded wire-oracle outcomes, exact
model/RTL comparisons, bounded properties and source-identified accounting.
Interpretation: tagged WAIT cleanly separates sampled persistence from timer
sampling and repairs the known training failures. Measured result: the responsibility
composes with the one selected LIN prefix under its bounded electrical contract.
Broader composition remains a hypothesis. Unverified possibilities include
debounce, wake-up detection, unsampled analog behavior, complete protocol
support, autobaud and physical closure. None is claimed as validated here.
[Preregistration](preregistration.json), [qualification sources](../../../tools/temporal_campaign.py).

## Y. Competition relevance

Interpretation: the bounded result tests whether a small vocabulary can express
another responsibility while preserving different serial behaviors. It does
not prove an area advantage, universal protocol support or practical physical
closure. Fixed cost and attempt gates make an unfavorable result meaningful.
[Architectural rationale](architectural_options.md), [fixed budgets](preregistration.json).

## Z. Recommended next step

Evaluate a diagnosed revision of the completed initial CMOS5L attempt at 6×4
and 20 ns. Explicit OpenROAD threads address the invalid default argument;
lower placement density tests the observed congestion. Neither change is a
claim of closure. The qualified unseen PR has merged. At most two diagnosed
flow-setting revisions may follow. Preserve failed attempts, retain unavailable metrics as
unavailable, and complete physical classification and reached demonstrations
without changing frozen semantics or the selected oracle.
[Stop conditions](preregistration.json).
