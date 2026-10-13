# Physical attempt 2: verified active-log observations

[Official run 38429471310](https://github.com/wellitsabhinav/MOTIF-Protocol-Motif-Machine/actions/runs/38429471310)
was dispatched at source `f55553a2b10b0880268663d8f06067c5ba1e14e0`.
The [intent](../../../experiments/temporal_qualification/physical/attempt_2_intent.json)
and [dispatch receipt](../../../experiments/temporal_qualification/physical/attempt_2_dispatch.json)
identify the first diagnosed flow revision, retaining the frozen semantics,
6×4 allocation and 20 ns target. This note records a snapshot, not its outcome.

## Snapshot identity

The read-only collector was [workflow 38435430815](https://github.com/wellitsabhinav/MOTIF-Protocol-Motif-Machine/actions/runs/38435430815)
at source `d69f99d71f589dc51fcf109ee37ffdc4c9237624`. Its artifact
`11832269523` is an 823,998-byte ZIP with raw SHA-256
`e9436796571b642dd77317f7c3e2230f389a96f9d6103f187d833625a026430c`.
The archive digest, all eight extracted member hashes and both snapshots'
bound workflow/jobs/log hashes were checked. This is a job-log snapshot
archive; it is not a physical layout or routed-netlist archive.

The ignored extraction is `build/v3_physical/observer_38435430815/extracted/`.
The active run's `38429471310/snapshot.json` records:

| Observation | Recorded value |
|---|---|
| Capture time, UTC | `2026-10-13T17:02:42.875268+00:00` |
| GDS job | `115407553588`, `in_progress`, conclusion `null` |
| Downloaded active log bytes | 4,233,075 |
| Active log raw SHA-256 | `f4f6983f7140c8119820d3a8f6329d896a672421d7fa7b18aaaed65e66139482` |
| Last visible log timestamp | `2026-10-13T16:29:05.3912244Z` |
| Last visible item | Detailed Placement step banner |

The same collector re-fetched the completed initial log: 4,547,178 bytes,
raw SHA-256 `7e27c87dca1bbe559a3cfa6974aeb688cb33ee575717b0382afdefe8aaf3ece9`.
It matches the [preserved initial-attempt evidence](physical_attempt_1_diagnosis.md).

## Observed settings and limits

Representative messages from the active log are:

```text
16:28:14.6215204Z Placement target density: 0.4500
16:28:31.6348916Z OpenROAD will use 4 threads
16:29:05.3912244Z Detailed Placement [step banner]
```

These establish that the flow reports placement target density 0.4500 and
the configured OpenROAD thread argument 4. The [pinned command-construction
analysis](physical_observability.md) explains why that verbose message records
the requested argument. It does not measure effective thread count or speedup.

Capture time identifies when the collector recorded its snapshot. The last
visible log timestamp identifies the tail it retrieved. Their difference
cannot be treated as time spent in detailed placement or a latest-stage claim.
The recorded official GDS job remains `in_progress`; no terminal result,
final metric inventory, physical closure or revised-setting performance result
is established here. Missing evidence remains unavailable. The collector
performs no cancellation, flow revision or additional physical dispatch.
