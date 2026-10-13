# Prepared physical attempt 2

This is the first diagnosed flow revision, following the retained unsuccessful
initial attempt. It is prepared and has not been dispatched by this receipt.

| Identity | Value |
|---|---|
| Source branch | `codex/v3-physical-attempt-2` |
| Exact source | `f55553a2b10b0880268663d8f06067c5ba1e14e0` |
| Intent LF SHA-256 | `9c5fcad8e67d97fd3322c9282841525f94873e8aec81151283ead027e7c3c101` |
| Density | 45%, previously 60% |
| OpenROAD threads | Integer 4, previously unset |
| Allocation and clock | 6×4, 20 ns |

The source branch is an immutable dispatch pointer. The delivery branch also
contains the intent committed after the source was identified. Dispatching
the delivery branch would select a different commit and fail intent matching.
No second attempt has been consumed until an actual official run is identified.
The cap remains three total runs, including the failed initial attempt.

Open the [pinned GDS workflow](https://github.com/wellitsabhinav/MOTIF-Protocol-Motif-Machine/actions/workflows/gds.yml),
choose **Run workflow**, select branch `codex/v3-physical-attempt-2`, and run it
once. A rerun of the initial workflow would use the old settings and is not this
revision. Record the resulting run URL before any further dispatch.

The initial terminal result, diagnosis and setting change were committed in
that order. All frozen RTL, model, compiler, harness and qualification bytes
match the semantic manifest. Only the two diagnosed flow settings change;
the pinned workflow, library/tool identities, clock, allocation, hold margins
and acceptance gates remain fixed. Changing both settings evaluates their
combined outcome; it cannot attribute improvement to either setting alone.

[Immutable attempt intent](../../../experiments/temporal_qualification/physical/attempt_2_intent.json),
[prerevision diagnosis](../../../experiments/temporal_qualification/physical/attempt_2_diagnosis.json),
[initial negative](../../../experiments/temporal_qualification/physical/attempt_1_result.json),
[rationale](physical_attempt_1_diagnosis.md),
[archive and gate reproduction](../../v3_physical_reproduction.md).
