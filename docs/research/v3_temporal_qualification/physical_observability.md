# Physical observability: initial job-log snapshot

The downloaded log establishes that the initial physical flow reached the
beginning of the CTS step. It does not establish the current live stage, a
stalled process, a failed attempt or physical closure. The repeated thread
warning has a source-backed explanation in the pinned flow software; its
performance impact has not been measured.

This note concerns [official run 38349981124](https://github.com/wellitsabhinav/MOTIF-Protocol-Motif-Machine/actions/runs/38349981124),
identified in the [initial dispatch receipt](../../../experiments/temporal_qualification/physical/attempt_1_dispatch.json).
It changes no flow settings, model, RTL or campaign contract.

## Observed facts

The inspected file is the ignored
`build/v3_physical/attempt_1/decoded_job_snapshot.log`, containing the actual
decoded GitHub job-log snapshot rather than a rendered tool-result excerpt.
Its local raw-byte identity, including the UTF-8 byte-order mark, is:

| Property | Observed value |
|---|---|
| Bytes | 4,232,980 |
| Lines | 38,593 |
| Raw SHA-256 | `022d34be9c54aafea99549103b4f77b8cc9bbaf59de06dc6022086237cbd14aa` |
| First log timestamp | `2026-10-13T05:09:43.6172965Z` |
| Last nonempty log timestamp | `2026-10-13T05:19:37.2641535Z` |
| `OpenROAD will use None threads` messages | 10 |
| `[ORD-0032]` warnings | 10 |
| Last visible step entry | `OpenROAD.CTS`, `runs/wokwi/35-openroad-cts` |

The local file's modification time is a filesystem observation. It is not the
runner's execution time, proof that all emitted lines were retrieved, or an
independent measurement of time spent in CTS.

The same thread warning appears at the start of floorplanning, RC dumping,
row cutting, tap/endcap insertion, PDN generation, global placement, mid-PnR
STA, post-placement design repair, detailed placement and CTS. Earlier steps
continue visibly after their warnings. The snapshot records detailed-placement
output writes before the CTS step starts. Its final visible lines are:

```text
05:19:37.0688081Z  Running 'OpenROAD.CTS'
05:19:37.0718977Z  OpenROAD will use None threads
05:19:37.2190001Z  [ORD-0032] Invalid thread number specification: None.
05:19:37.2221223Z  Reading timing models for corner nom_fast_1p32V_m40C
05:19:37.2641535Z  ...sg13cmos5l_io_fast_1p32V_3p6V_m40C.lib
```

The snapshot contains no `final/metrics.json` publication, CTS completion
record or completed hardening result. It also records a pre-CTS cell report:
17,928 cells and 223,376.23 square micrometres after detailed placement,
including 2,305 timing-repair buffers. These are intermediate physical-stage
observations, not final area or the separately qualified matched nominal
synthesis cost. They do not establish post-route timing, congestion, DRC, LVS,
antenna status or functional qualification.

The inspected [project configuration](../../../src/config.json) retains
`CLOCK_PERIOD = 20`, `RUN_CTS = 1` and target placement density 60. It does not
set `OPENROAD_THREADS`. The [workflow](../../../.github/workflows/gds.yml) and
[lock](../../../flow-lock.json) retain the official action at
`3412659307918422f3f0727917cf9b499aaca588`, support tools at
`d66cf179e7bc4d296362ab7e2e3b344dc3c4f665`, and LibreLane `3.1.0.dev3`.
The log records the container tag `ghcr.io/librelane/librelane:3.1.0.dev3`
with image digest
`sha256:d109140b8f17fc54f4fca998beb8124f4949404ec52e339eebd2250854a18b5a`.

## Source-backed interpretation

LibreLane's tagged `OpenROADStep` declares `OPENROAD_THREADS` as an optional
integer whose default is `None`. Its command construction converts that value
to a string before applying the fallback:

```python
threads = str(self.config["OPENROAD_THREADS"]) or str(_get_process_limit())
```

With the default, Python produces the nonempty string `"None"`. That string is
truthy, so the fallback is not evaluated. The resulting command passes
`-threads None` to each new OpenROAD process and logs the same value. This
explains the repeated startup diagnostic observed in the snapshot. It is a
flow command-construction issue, rather than an instruction, FIFO or RTL
failure. [LibreLane 3.1.0.dev3 OpenROAD step source](https://github.com/librelane/librelane/blob/3.1.0.dev3/librelane/steps/openroad.py#L518-L532).

The tagged Nix recipe selects OpenROAD source revision
`dcf36133a369abc8f3c5e5738cd4d82e4903c0e0`. Its thread parser initializes the
candidate count from the current count, catches an invalid integer conversion,
emits warning `ORD-0032` and keeps that count. The corresponding class member
initializes the count to one. Thus the reviewed source predicts retention of
the existing count after this invalid argument, without treating it as a fatal
parse error. This predicts initial single-thread behavior for that source,
before any subsequent changes; it is not a measurement of this worker's
effective thread count. [LibreLane OpenROAD package recipe](https://github.com/librelane/librelane/blob/3.1.0.dev3/nix/openroad.nix),
[pinned OpenROAD parser](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/OpenRoad.cc#L667-L683),
[pinned count initialization](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/include/ord/OpenRoad.hh).

The pinned Tiny Tapeout action invokes `tt_tool.py --harden`. The pinned
support tool launches LibreLane and checks its subprocess return code. A
later nonzero result would establish a hardening failure through that path;
the supplied snapshot does not contain that result. [Pinned GDS action](https://github.com/TinyTapeout/tt-gds-action/blob/3412659307918422f3f0727917cf9b499aaca588/action.yml#L90-L96),
[pinned hardening launcher](https://github.com/TinyTapeout/tt-support-tools/blob/d66cf179e7bc4d296362ab7e2e3b344dc3c4f665/project.py#L476-L500).

The CTS Tcl script first reads the current database and common timing inputs,
then sets RC/parasitic estimates and repairs clock inverters before invoking
clock-tree synthesis. A step-entry banner and initial timing-library reads
therefore do not by themselves show that the tree-building algorithm has
begun, completed or failed. [Pinned CTS script](https://github.com/librelane/librelane/blob/3.1.0.dev3/librelane/scripts/openroad/cts.tcl).

## Hypotheses and unknowns

Lower effective parallelism could affect elapsed time for work that uses
multiple threads. The snapshot provides no CPU sampling, effective-thread
query or comparison run that attributes elapsed time to this warning. It
cannot establish that the warning explains the current workflow duration.
An integer thread-setting change has not been tested or applied in this note.

The tail may reflect the latest retrieved portion of a running log, delayed
publication, or a process still doing work within the visible step. These are
possibilities, not diagnosed causes. There is no runner process inspection,
stack trace, resource measurement or later step artifact in this snapshot to
choose among them. Its last timestamp cannot be promoted to a current-stage
claim or a CTS timeout measurement.

GitHub documents the job-log endpoint as a redirect to a plain-text download;
workflow-job metadata supplies separate status, conclusion and completion
fields. The downloaded log is evidence of its contents. Fresh metadata and
identified stage artifacts are needed for a current or final execution claim.
[GitHub workflow-job and log API](https://docs.github.com/en/rest/actions/workflow-jobs?apiVersion=2022-11-28#download-job-logs-for-a-workflow-run-job).

Neither the startup warning nor the apparent quiet tail justifies declaring
the attempt failed, cancelling it, dispatching another run or changing flow
settings. A later diagnosed revision must use the recorded attempt policy,
retain the actual completed negative evidence, and keep frozen semantics and
the 6×4/20 ns contract unchanged. The three-attempt limit is not affected by
how often a log snapshot is read.

## Evidence needed to resolve the unknowns

Preserve each fetched log as a separately hashed snapshot. Record fresh run
and job metadata alongside it, including timestamps and whether the hardening
step is still in progress or has a conclusion. If the run publishes an
artifact, identify the archive and compare its exact extracted bytes before
reading the actual CTS log, step state and later stages. A valid step state
retains its stage identity; it does not replace the official job conclusion.
Effective thread count or a performance cause needs direct runtime evidence,
rather than the text of the invalid argument.

The [physical reproduction guide](../../v3_physical_reproduction.md) documents
archive/source correspondence, partial measurement extraction, missing-value
handling, routed tests and the final fail-closed gate. Complete official
precheck, routed functional tests, source correspondence and corner timing
remain separate acceptance requirements. Missing measurements remain
unavailable; this observability note qualifies none of those gates.
