# Physical attempt 2: preparation and identified dispatch

This is the first diagnosed flow revision, following the retained unsuccessful
initial attempt. Its immutable intent was committed before dispatch. The
approved CI helper subsequently launched
[official run 38429471310](https://github.com/wellitsabhinav/MOTIF-Protocol-Motif-Machine/actions/runs/38429471310)
at `2026-10-13T16:18:53Z` (21:48:53 IST), using the exact source below.

| Identity | Value |
|---|---|
| Source branch | `codex/v3-physical-attempt-2` |
| Exact source | `f55553a2b10b0880268663d8f06067c5ba1e14e0` |
| Intent LF SHA-256 | `9c5fcad8e67d97fd3322c9282841525f94873e8aec81151283ead027e7c3c101` |
| Density | 45%, previously 60% |
| OpenROAD threads | Integer 4, previously unset |
| Allocation and clock | 6×4, 20 ns |
| Official workflow run | `38429471310`, first run attempt |
| Helper run and source | `38429454463`, `ead060d37d8729f7b7cac9c9ddcc89aabdeef8a6` |

The source branch is an immutable dispatch pointer. The delivery branch also
contains the intent committed after the source was identified. Dispatching
the delivery branch would select a different commit and fail intent matching.
Two physical attempts have now been dispatched, including the failed initial
attempt. The cap remains three total runs; one diagnosed revision remains
available only after a retained unsuccessful result.

The launch selected branch `codex/v3-physical-attempt-2` in the unchanged
[pinned GDS workflow](https://github.com/wellitsabhinav/MOTIF-Protocol-Motif-Machine/actions/workflows/gds.yml).
An existing source run prevents another helper dispatch. The intent and
actual workflow metadata must be compared before collecting physical evidence;
this launch establishes no physical acceptance gate.

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
[actual dispatch receipt](../../../experiments/temporal_qualification/physical/attempt_2_dispatch.json),
[verified API response](../../../experiments/temporal_qualification/physical/attempt_2_dispatch_api_receipt.json),
[archive and gate reproduction](../../v3_physical_reproduction.md).

## CI launch helper

The optional `v3-physical-dispatch` helper runs when the explicit tracked
dispatch request changes on the delivery branch. It checks the immutable
intent, frozen source/settings, prior completed failure and exact branch ref.
An existing GDS run for that source prevents another launch. It sends one
normal authenticated API request and never retries the POST; an empty accepted
response must be resolved by reading actual run metadata. It does not execute
P&R or change the pinned GDS workflow.

Only this helper job receives `actions: write`, using the normal ephemeral
GitHub job token. No repository protection, account permission or persistent
credential changes are needed. GitHub documents workflow dispatch as a token
event that can start a new workflow and requires Actions write permission.
[GitHub token behavior](https://docs.github.com/en/actions/concepts/security/github_token),
[workflow-dispatch API](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event),
[returned run identities](https://github.blog/changelog/2026-02-19-workflow-dispatch-api-now-returns-run-ids/).

The API response is published as a separate small CI artifact. It is evidence
of dispatch acceptance only; the campaign ledger binds the actual workflow
run, exact source and subsequent physical gates separately.
