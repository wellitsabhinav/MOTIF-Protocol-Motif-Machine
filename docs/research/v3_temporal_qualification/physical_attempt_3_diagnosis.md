# Final physical attempt: execution limit and campaign stop

The campaign stops with logical generalization and matched-cost qualification
passing, and physical qualification **unestablished**. All three permitted
physical runs and both diagnosed revisions are exhausted. No further circuit,
frontend, vocabulary, oracle or flow-setting repair belongs to this campaign.

## Terminal identity and established cause

Official [run 38470361703](https://github.com/wellitsabhinav/MOTIF-Protocol-Motif-Machine/actions/runs/38470361703)
used source `5dbf3abf11f61a8e6bd26cc5f328999190f12859` and the previously
committed final intent. Its GDS job `115547538149` ran from
`2026-10-13T21:24:33Z` to `2026-10-14T03:25:18Z`: 6 h 45 s including cleanup.
The workflow conclusion is `cancelled`. The actual GitHub check annotation
records that the job exceeded the maximum execution time of 6 h 0 m 0 s.
This establishes the cancellation cause for attempt 3; attempt 1's recorded
unknown cause retains its original scope.

Only PDF artifact `11850698812` was published. Neither `GDS_logs` nor
`tt_submission` exists for this run. Official precheck and gate-level test jobs
were skipped. The terminal-failure command exits **1**, with final measurements,
corner timing and routed evidence represented as unavailable. There is no
attempt-3 physical archive or source/archive correspondence from which to render
layout views or establish physical closure.

[Terminal result](../../../experiments/temporal_qualification/physical/attempt_3_result.json),
[actual check annotations](../../../experiments/temporal_qualification/physical/attempt_3_check_annotations.json),
[annotation/source identity](../../../experiments/temporal_qualification/physical/attempt_3_terminal_evidence.json).

## Identified partial observations

The complete decoded terminal log is 4,519,308 UTF-8 bytes with SHA-256
`dbe476608eb97ffa67055cbff03ee8093f38a203cc3099dd154b12cdcff9f2e9`.
The reporting parser records 46 entered stages. Full logs stay outside Git;
the committed excerpt retains original one-based line numbers. These log
measurements have their own stage and timestamp; they are not final STA, DRC,
LVS, utilization or cost qualification.

Post-CTS timing repair entered the next stage after 6,337.473226 s.
Its estimated-parasitic setup row reports WNS −7.573 ns, TNS −1,430.5 ns and
198 violating endpoints. The hold row reports WNS +0.100 ns and TNS 0.
All three libraries are loaded and the rows do not label an individual corner;
no per-corner result is inferred from them.

Global routing entered the next stage after 1,391.497483 s. Its reported
overflow is 71,352 and wirelength 4,202,676 µm. Detailed routing entered at
`2026-10-13T23:42:01.2379669Z` and did not reach a following stage.
At `2026-10-14T02:21:28Z` it reported intermediate wirelength 3,345,181 µm
and 252,217 vias. Its last progress checkpoint at
`2026-10-14T03:21:18.3630718Z` reports 80% of an optimization iteration and
270,448 violations. These are unfinished routing observations, **not final DRC**.
Cancellation appears at `2026-10-14T03:25:15.2105738Z`.

The configured placement target starts at 0.45; the actual global-placement
log adjusts it up to 0.5013. This is observed flow behavior, not a third manual
setting revision. OpenROAD's argument is 4 threads; effective worker count
and speedup are not measured. The last logged post-diode inventory has
23,590 cells and 308,999.58 µm² cell area. That intermediate inventory cannot
replace the preregistered nominal matched mapping or a missing final inventory.

[Stage observations](../../../experiments/temporal_qualification/physical/attempt_3_observations.json),
[compact log excerpt](../../../experiments/temporal_qualification/physical/attempt_3_log_excerpt.txt).

## Interpretation and limits

The combined `DELAY 0` strategy and slow-library selection did not establish
physical closure within the pinned run. Global-routing overflow is larger than
attempt 2's measured 7,782 at that stage. The two settings changed together;
their individual effects are not identified. A deep table/control path remains
a timing hypothesis supported by attempt 2's actual path reports, not a proof
that the temporal counter caused the physical failures or that configuration
expressibility is impossible.

Final setup/hold WNS and TNS by corner, final standard-cell/sequential inventory,
final wirelength/vias, final DRC, LVS, antenna results and GDS views are
**unavailable for attempt 3**. Attempt 2's final measurements and visibly
UNQUALIFIED views retain their own source and archive identities.

The immutable semantic manifest and preregistration verify before and after
evidence collection. Allocation stays 6×4, clock target 20 ns, and the initial
physical-flow hashes remain separate from the two diagnosed setting revisions.
The nominal cost gate still measures 210,241.9746 µm², +8.1623% versus frozen v2,
18 added declared state bits and zero configuration growth. Neither that pass
nor the selected LIN logical pass establishes physical closure.

[Final intent](../../../experiments/temporal_qualification/physical/attempt_3_intent.json),
[fixed stop ledger](../../../experiments/temporal_qualification/campaign_result.json),
[immutable contract](preregistration.json), [freeze](../../../experiments/temporal_qualification/frozen_v3_manifest.json).
