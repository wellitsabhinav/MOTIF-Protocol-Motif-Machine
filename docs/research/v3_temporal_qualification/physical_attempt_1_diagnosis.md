# Initial physical attempt: terminal evidence and revision hypotheses

The first physical attempt is not qualified. Its official workflow completed
with conclusion `cancelled`; precheck and routed functional testing were
skipped, and no physical archive or final metric inventory was published.
The completed log establishes progress beyond CTS, remaining setup violations
after estimated timing repair, routing congestion and incomplete detailed
routing. The available evidence does not identify the actor or cause of
cancellation.

This diagnosis concerns [run 38349981124](https://github.com/wellitsabhinav/MOTIF-Protocol-Motif-Machine/actions/runs/38349981124)
and GDS job `115139931872`, at source
`5467fd4d15a18dda9bc58a93bb3182b03629aa4b`. The
[intent](../../../experiments/temporal_qualification/physical/attempt_1_intent.json),
[dispatch](../../../experiments/temporal_qualification/physical/attempt_1_dispatch.json)
and [terminal result](../../../experiments/temporal_qualification/physical/attempt_1_result.json)
retain the original 6×4 allocation, 20 ns clock target, pinned tool identity
and frozen semantic boundary. This note edits none of those inputs.

## Evidence identities and official outcome

The ignored completed decoded log is
`build/v3_physical/attempt_1/decoded_terminal_job.log`. Its local raw-byte
SHA-256, including the UTF-8 byte-order mark, is
`7e27c87dca1bbe559a3cfa6974aeb688cb33ee575717b0382afdefe8aaf3ece9`.
It contains 4,547,178 bytes and 41,420 lines, from
`2026-10-13T05:09:43.6172965Z` through
`2026-10-13T11:10:08.1800911Z`. These identities distinguish it from the earlier
[snapshot](physical_observability.md), whose tail showed only CTS startup.

The retained terminal metadata files and raw hashes are:

| Ignored metadata file under the attempt directory | Raw SHA-256 |
|---|---|
| `workflow_terminal.json` | `a324c0edcd4dbe79cca5214ed7b87603200e12fa563698b1810539c9316e6c3b` |
| `jobs_terminal.json` | `5e06a02097e9d1436c135407e0a479fd14a941e53fc2ffd1653044ee8838c5c2` |
| `artifacts_terminal.json` | `098b7d78affe727eadce0ebfc4f6a66f4f6932cfbee9a39cd54197ef707e0d1f` |

The workflow metadata reports `status: completed`, `conclusion: cancelled` and
`run_attempt: 1`. The GDS job ran from 05:09:42 to 11:10:09 UTC. Its build step
ended with cancellation at 11:10:07. The documentation job succeeded; the
official `precheck` and `gl_test` jobs were skipped. The sole published artifact
was the documentation `PDF`, ID `11790357102`, 34,393 bytes. That PDF is not a
physical archive, layout, netlist or timing result.

The terminal result records `physical_qualified: false`. Its measurement,
corner and routed-evidence inventories remain `null`, because the required
physical archives were never published. Selected values printed in the job
log are preserved below as stage observations; they are not substituted for a
verified final archive inventory.

The concise [observation receipt](../../../experiments/temporal_qualification/physical/attempt_1_log_observations.json)
records parsed stage entries and explicitly scoped partial observations. The
[selected excerpt](../../../experiments/temporal_qualification/physical/attempt_1_log_excerpt.txt)
preserves original numbered log lines. Both identify the completed log above.

## Actual stage sequence and time boundaries

All timestamps below are UTC on 2026-10-13. Durations are differences between
logged step entry and the next logged OpenROAD step entry, including output
and flow overhead. They are not CPU utilization measurements.

| Stage | Logged entry | Following evidence | Observed interval |
|---|---|---|---|
| CTS, `35-openroad-cts` | 05:19:37.0688081 | CTS output writes and legalization; `OpenROAD.STAMidPNR-1` enters at 05:19:56.0636026 | 18.995 s |
| Post-CTS resizer, `37-openroad-resizertimingpostcts` | 05:20:20.7782238 | Setup and hold repair tables, output writes; `OpenROAD.STAMidPNR-2` enters at 08:54:50.7075516 | 3 h 34 min 29.929 s |
| Global routing, `39-openroad-globalrouting` | 08:55:18.4663199 | Final global congestion table; `OpenROAD.CheckAntennas` enters at 09:11:23.8166289 | 16 min 5.350 s |
| Detailed routing, `44-openroad-detailedrouting` | 09:14:42.6660525 | Third optimization iteration still reports violations at 11:07:50.1692925; build cancellation at 11:10:07.4976074 | No completion observed |

The completed log shows that CTS finished and execution proceeded to later
steps. The earlier quiet snapshot therefore did not identify the long-running
stage. The major observed timing-repair interval belongs to the post-CTS
resizer. The log does not establish why that interval was long or how much
parallelism any specific operation used.

## Remaining estimated timing violation

The resizer setup table begins at 05:20:26 with 198 violating endpoints,
WNS −32.100 ns and TNS −6141.6 ns. Its final setup row at 08:41:08 still has
198 violating endpoints, WNS −6.745 ns and TNS −1247.8 ns. Warning `RSZ-0062`
explicitly reports that all setup violations could not be repaired. This is
a real negative timing observation; improvement from the initial row is not
setup closure.

The following hold repair is a separate table. It begins with 1,205 violating
endpoints, WNS −0.098 ns and TNS −12.208 ns. The final hold row at 08:54:47
reports WNS +0.100 ns and TNS 0.000 ns, with 1,246 hold buffers inserted.
Positive hold slack does not erase the remaining setup violation or establish
timing at every corner.

Compact excerpts from the completed log preserve both results. Line numbers
refer to its 1-based decoded line inventory; wrapped table rows have been
joined here with their same timestamp/value context:

```text
38853–38854 05:20:26.7128509Z setup iter 0: WNS -32.100; TNS -6141.6; violating endpoints 198
40043–40044 08:41:08.1770478Z setup final:  WNS  -6.745; TNS -1247.8; violating endpoints 198
40051–40052 08:41:08.1820642Z [RSZ-0062] Unable to repair all setup violations.
40305–40306 08:54:47.8373169Z hold final:  WNS   0.100; TNS     0.000; inserted buffers 1246
40309      08:54:47.8386125Z [RSZ-0032] Inserted 1246 hold buffers.
```

These values belong to estimated resizer progress. Startup lines 38806–38826
load fast, slow and typical libraries; the repair table itself does not label
an individual corner. A last-loaded library cannot establish that attribution.
The pinned step estimates placement parasitics and invokes setup/hold repair
without a per-corner table selector. Individual corner attribution therefore
remains unavailable. These rows are not final extracted-parasitic STA, and no
complete final setup/hold WNS/TNS by corner is available for qualification.
[Pinned post-CTS repair script](https://github.com/librelane/librelane/blob/3.1.0.dev3/librelane/scripts/openroad/rsz_timing_postcts.tcl).
The post-CTS stage also prints 20,013 cells and 264,931.43 square micrometres,
including timing-repair and clock cells. That is a physical-stage cell report,
not a new matched nominal synthesis-cost comparison.

## Routing evidence and cancellation boundary

The global router exhausts its 50 extra overflow-removal iterations and prints
the following final table at 09:11:21:

| Layer | Reported usage | Total overflow |
|---|---:|---:|
| Metal1 | 0.00% | 0 |
| Metal2 | 84.72% | 49 |
| Metal3 | 93.53% | 10,691 |
| Metal4 | 42.64% | 106 |
| Total | 75.16% | 10,846 |

Warning `GRT-0115` says global routing finished with congestion. This is a
nonzero global-route overflow observation, with most reported overflow on
Metal3. It cannot satisfy the campaign's zero-overflow gate. The recorded
global-route wirelength is 3,769,279 micrometres and the router reports 238,616
vias; neither is a final detailed-routing measurement.

Detailed routing proceeds into its third optimization iteration. Its last
visible progress row says `Completing 80% with 7628 violations` at
11:07:50.1692925. That percentage refers to that iteration's progress, not
overall workflow completion. The 7,628 count is a partial detailed-router
violation count, not a completed final DRC report.

```text
40609 09:11:21.7168689Z Total: usage 75.16%; total overflow 10846
40613 09:11:21.7665182Z [GRT-0115] Global routing finished with congestion.
41261 11:07:50.1692925Z Completing 80% with 7628 violations.
41263 11:10:07.4976074Z The operation was canceled.
```

The log and terminal metadata identify cancellation, not its cause. There is
no supplied actor/reason record that distinguishes a manual cancellation,
runner limit or service action. Elapsed time and nearby warning/violation rows
do not establish causation. No cancellation or new dispatch was performed as
part of this documentation task.

The archive upload/render steps were skipped. There is no identified final
GDS, DEF, routed netlist, final metric JSON or corner report to recover from
this attempt. Official precheck, LVS/final DRC/antenna qualification and routed
functional tests remain unavailable. Missing results are not zero violations
or functional passes, and no physical view is reconstructed from text logs.

## Assessment of the first planned flow revision

The planned revision changes only `OPENROAD_THREADS` to 4 and
`PL_TARGET_DENSITY_PCT` from 60 to 45. It retains 6×4 allocation, the 20 ns
target, frozen RTL/model semantics, pinned tools and acceptance criteria.
Both settings are assessed as hypotheses below; this note reports no revised
run outcome. The [machine-readable revision diagnosis](../../../experiments/temporal_qualification/physical/attempt_2_diagnosis.json)
records these settings and their rationale before the configuration change.

**Thread setting.** The initial log contains the repeated `None` thread
diagnostic explained in [physical_observability.md](physical_observability.md).
The pinned LibreLane command builder stringifies an unset optional value,
bypassing its intended fallback. Supplying integer 4 addresses that known
command-construction path. The pinned OpenROAD parser accepts an integer and
limits the count to hardware concurrency. Its invalid-string path retains
the existing count, whose class initializer is one. [Pinned LibreLane command builder](https://github.com/librelane/librelane/blob/3.1.0.dev3/librelane/steps/openroad.py#L518-L532),
[pinned OpenROAD parser](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/OpenRoad.cc#L643-L683),
[pinned initialization](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/include/ord/OpenRoad.hh).

The supported interpretation is that the explicit setting avoids passing
`None` and may permit more parallel work. Runtime improvement, effective
worker thread count and any factor of speedup remain unverified. It does not
repair a negative setup slack or remove routing violations by itself. In
particular, the long post-CTS repair interval is not proved to have been
caused entirely by the thread default.

**Placement density.** The floorplan reports a core area of 902,417.242 square
micrometres, and the initial GPL statistics report movable area 242,828.908
square micrometres and utilization 26.909%. The initial target density is
0.6000. A proposed target of 0.45 remains above that initial average
utilization. This supports exploring a less concentrated placement policy
within the same floorplan; it does not prove local routing capacity or that
all later buffering will fit that policy.

Target placement density and measured average utilization are different
quantities. OpenROAD's routability-driven placement estimates congestion and
inflates cells in congested tiles. The initial log itself later reports
adaptive target density increases, ending near 0.7397681. Lowering the
starting target therefore does not guarantee a final 45% local density or
zero overflow. [Pinned global-placement documentation](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/gpl/README.md),
[pinned LibreLane density variable](https://github.com/librelane/librelane/blob/3.1.0.dev3/librelane/steps/openroad.py).

Reduced concentration may improve local routability, while greater spreading
can increase wirelength and delay. Neither direction is measured for the
revised setting, and the remaining setup violation must still be tested at
the unchanged target. Changing both knobs in one revision can assess their
combined qualification outcome, but cannot independently attribute any
improvement to one knob.

The completed negative attempt is preserved. A revised run must demonstrate
its own exact source/settings identity, final corner STA, zero required
physical violations, official precheck and routed functional tests. It must
not reuse the positive hold-repair row as a setup pass, relabel partial routing
as final DRC, change frozen semantics, or relax the oracle/clock/allocation.
The [preregistered limit](preregistration.json) remains the initial attempt plus
at most two diagnosed flow-setting revisions. This diagnosis alone qualifies
none of the physical gates.
