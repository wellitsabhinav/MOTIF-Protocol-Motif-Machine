# Physical attempt 2: setup failure and final flow revision rationale

Attempt 2 completed with **failure**. It produced routed physical artifacts and
passed the recorded routing DRC, Magic DRC, LVS and antenna checks, but failed
setup timing. Official precheck and routed functional tests were skipped.
Physical qualification remains false. This record preserves the negative result;
it does not establish closure or replace the immutable logical and synthesis
qualification evidence.

## Identity and evidence boundary

The [official run 38429471310](https://github.com/wellitsabhinav/MOTIF-Protocol-Motif-Machine/actions/runs/38429471310)
used source `f55553a2b10b0880268663d8f06067c5ba1e14e0`. GDS job
`115407553588` ran from `2026-10-13T16:18:57Z` to
`2026-10-13T19:58:31Z`. The [dispatch receipt](../../../experiments/temporal_qualification/physical/attempt_2_dispatch.json)
binds this run to its [prepared intent](../../../experiments/temporal_qualification/physical/attempt_2_intent.json).
This was the first diagnosed setting revision: four configured OpenROAD threads
and placement target density 45 percent. The two changes cannot be assigned
separate causal effects from this run.

The actual `GDS_logs` artifact is `11843789314`, 265,262,975 archive bytes, with
raw ZIP SHA-256
`5cdff1a5201ebad89713da86188c8bd5b0b7d93afa1737752023c6b7d5e2a7d0`.
Extraction and source correspondence bind the reports below to this one archive
and source. The complete decoded job log has 5,027,070 bytes and 45,752 lines;
its raw SHA-256 is
`3e847bb1334a6f7b5a2bbd1486d72c87e15510983b58b8f421587edd40f4f4d2`.
Embedded BOM characters were removed only in memory for observation parsing;
the raw log remains unchanged. Full logs, netlists, timing reports and physical
artifacts remain in ignored build output.

Concise evidence links: [negative gate result](../../../experiments/temporal_qualification/physical/attempt_2_result.json),
[identified metrics](../../../experiments/temporal_qualification/physical/attempt_2_metrics.json),
[source and archive correspondence](../../../experiments/temporal_qualification/physical/attempt_2_source_correspondence.json),
[stage and log observations](../../../experiments/temporal_qualification/physical/attempt_2_observations.json),
[actual critical-path excerpts](../../../experiments/temporal_qualification/physical/attempt_2_critical_paths.txt),
and [final-revision machine rationale](../../../experiments/temporal_qualification/physical/attempt_3_diagnosis.json).

The semantic boundary remains freeze commit
`638c2ee4e7c9f53c64e6f660331747e5a79b570d`, manifest LF SHA-256
`71d5b07b5524fb6fa702357291eb35f52eccc5861111f7824b6fb9ead98a3047`.
Preregistration remains commit `637aeb947e7726ce0ef6347f0788c2803149f091`,
LF SHA-256 `2c294fc24c46c0a14bb16e24087ece1fbb60e347939536fedd9141ce1ed21522`.
Correspondence reports all protected source bytes equal. Allocation remains
**6 × 4** and the clock target remains **20 ns**.

## Observed terminal result and durations

Job-log lines 45523–45532 record a deferred setup violation at
`nom_typ_1p20V_25C`, LibreLane termination and process exit code 1. Fast and slow
setup violations were also reported as warnings. The resolved
`TIMING_VIOLATION_CORNERS` is `['*typ*']`; the pinned checker warns for violating
corners outside that selector and raises a deferred error for selected corners.
The distinction explains the terminal message and does not make the other
corners pass. [Pinned checker implementation](https://github.com/librelane/librelane/blob/ca6adb1e2982cd75445a68b632d461213d8ca421/librelane/steps/checker.py#L553-L630).

The following intervals are measured from a step's logged entry to the next
actual step's entry, including intervening flow overhead. They are not CPU times.
All timestamps are UTC on 2026-10-13.

| Step | Entry | Next step entry | Interval |
|---|---|---|---|
| Global placement | 16:28:04.9202747 | 16:28:30.9159435 | 25.995669 s |
| CTS | 16:29:06.7132860 | 16:29:23.5232782 | 16.809992 s |
| Post-CTS timing repair | 16:29:37.5551168 | 17:43:18.0704528 | 4,420.515336 s |
| Global routing | 17:43:33.1071059 | 17:57:55.7998581 | 862.692753 s |
| Detailed routing | 17:59:29.5433364 | 19:12:26.9295954 | 4,377.386259 s |
| RC extraction | 19:12:41.8020252 | 19:12:48.6489066 | 6.846881 s |
| Post-route STA | 19:12:48.6489066 | 19:13:31.5191051 | 42.870199 s |
| Magic DRC | 19:16:35.3510644 | 19:56:56.4690067 | 2,421.117942 s |
| Netgen LVS | 19:57:32.9781182 | 19:57:42.7532096 | 9.775091 s |

Post-CTS setup repair ended with estimated WNS −7.722 ns, TNS −1,451.0 ns and
198 violating endpoints at lines 39910–39911, followed by an unable-to-repair
warning. Hold repair ended at +0.101 ns worst slack and zero TNS, inserting
1,294 hold buffers, at lines 40180–40184. These are unlabelled resizer progress
rows after loading three timing corners. They cannot be assigned to one corner
or directly compared with final extracted STA or attempt 1's estimated rows as
a timing improvement.

## Final extracted timing

`54-openroad-rcx` completed before `55-openroad-stapostpnr`. The final metrics and
the individual `wns`, `tns` and `ws` reports agree on these values in nanoseconds.
Counts are reported violating setup endpoints. Each corner has zero reported
hold violations and zero hold WNS and TNS; positive hold worst slack is included
to distinguish worst slack from worst **negative** slack.

| Corner | Setup WNS | Setup TNS | Setup count | Hold worst slack | Hold WNS | Hold TNS |
|---|---:|---:|---:|---:|---:|---:|
| `nom_fast_1p32V_m40C` | −0.5328040381921172 | −53.6000201616507 | 188 | 0.10836781778663933 | 0 | 0 |
| `nom_typ_1p20V_25C` | −9.764564544427186 | −1859.0249581473663 | 198 | 0.2798822364200014 | 0 | 0 |
| `nom_slow_1p08V_125C` | −26.75138053461459 | −5172.522524704961 | 202 | 0.5924894076393782 | 0 | 0 |

The typical and slow worst paths launch from `_28309_/Q`, identified in the
actual final netlist as `core.exchange.program_i[928]`: entry 14, word bit 32,
VALUE bit 11. They end respectively at `_27024_/D` and `_27026_/D`, whose Q nets
are `core.rx_fifo.memory[3][1]` and `core.rx_fifo.memory[3][3]`. Typical arrival
and required times are 30.192322 and 20.427757 ns; slow values are 47.487091 and
20.735708 ns. The fast worst path starts at `rst_n` and ends at `_27024_/D`.

Summing reported increments on each worst data path from the launch-Q row to
the destination-D row gives typical **26.063588 ns cell arcs / 3.211693 ns
input and net arcs**, and slow **43.600155 ns / 2.518237 ns**. Typical has 95
output-cell arcs, including the launch flop, of which 64 are not buffers; slow
has 93 and 63 respectively. These are counts and sums of the identified report
rows, excluding clock paths. They are not estimates of delay removable by a
flow change. The observed mapped paths are deep table-data-to-FIFO control
cones. Gate names alone do not identify every executor stage, and this evidence
does not establish the temporal counter as the critical-path cause. Loading and
slew still affect the cell arc delays.

## Physical measurements and limits of the checks

The final metrics report **20,178 standard cells**, including **1,401 sequential
cells**, **263,349 µm² standard-cell area**, and utilization **0.291827** in a
**902,417 µm² core**. The detailed-routing cell inventory reports the more
precise area **263,349.27 µm²**. It contains 4,029 timing-repair buffers with
49,300.9 µm² reported area. The all-instance inventory instead includes 62,098
fill cells: 82,276 total instances and 902,417 µm² aggregate instance area.
Those totals must not be substituted for standard-cell area or the independent
paired synthesis cost qualification.

Global routing reported **7,782 total overflow**: Metal2 17, Metal3 7,655 and
Metal4 110 (lines 40475–40480), 3,651,991 µm wirelength and 230,501 vias. Final
detailed routing reported **2,448,577 µm wirelength and 206,169 vias**
(lines 42576–42582). Global overflow remains a negative campaign gate even
though detailed routing subsequently completed without reported routing DRC.

| Check | Observed result | Scope |
|---|---|---|
| Detailed-routing DRC | 0 | Final routing checker; line 42683 |
| Magic DRC | 0 | Magic report and checker; lines 43868 and 43885 |
| LVS | 0 errors | Netgen and LVS checker; line 45421 |
| Antenna | 0 violating nets/pins; 0 route violations | Final flow metrics after antenna repair |
| KLayout DRC | unavailable | Disabled/skipped; warning at lines 45457–45458 |
| Official precheck | skipped | Official workflow job, no pass |
| Official routed functional tests | skipped | Official workflow job, no pass |

Final slew violations are fast 2, typical 47 and slow 542; capacitance
violations are 51, 51 and 50 respectively. All corners also report 160 fanout
violations. The slew/cap checker corner overrides are `['']`, selecting no
corners for errors. Its subsequent “no violations” message concerns the
selected error set; it cannot override the reported warnings or measured
violations. Local manufacturability summaries, GDS generation and an available
render do not establish official precheck, functional correspondence or timing
closure.

The final GDS is 27,601,790 bytes, SHA-256
`a106d0f121719f3212acf4ab62bc46cbeb27663c2ad3dccdf02ec528726fb8ba`;
the final netlist is 4,640,858 bytes, SHA-256
`38ec2d55bf67dee92f00eefb59ce8119d02ad091b8324a846909afe2ff4a87d0`.
They belong to this failed attempt and may support identified views and future
bounded functional checks; they are not qualified physical delivery artifacts.

## Rationale for the final permitted setting revision

Attempt 2 actually used `SYNTH_STRATEGY = 'AREA 0'` and no synthesis corner
override, hence the default typical library. The proposed final revision uses
`SYNTH_STRATEGY = 'DELAY 0'` and
`SYNTH_CORNER = 'nom_slow_1p08V_125C'`. The pinned LibreLane source commit is
`ca6adb1e2982cd75445a68b632d461213d8ca421` (3.1.0.dev3). It explicitly supports
both settings and selects the requested timing library instead of the default.
[Synthesis settings](https://github.com/librelane/librelane/blob/ca6adb1e2982cd75445a68b632d461213d8ca421/librelane/steps/pyosys.py#L224-L228),
[strategy choices](https://github.com/librelane/librelane/blob/ca6adb1e2982cd75445a68b632d461213d8ca421/librelane/steps/pyosys.py#L415-L428),
[corner filtering](https://github.com/librelane/librelane/blob/ca6adb1e2982cd75445a68b632d461213d8ca421/librelane/common/toolbox.py#L79-L108).

The hypothesis is that timing-directed combinational restructuring and mapping
against the measured slow corner can improve the deep control cones. The
generated delay strategy uses different mapping operations from `AREA 0` and
retains the 20,000 ps target. `SYNTH_ABC_DFF` remains false: flip-flops are not
passed through ABC. Although the generated script contains retime commands,
this proposal does not perform sequential retiming or change declared
architectural state. [ABC strategy construction](https://github.com/librelane/librelane/blob/ca6adb1e2982cd75445a68b632d461213d8ca421/librelane/scripts/pyosys/construct_abc_script.py#L119-L171),
[conditional ABC flip-flop argument](https://github.com/librelane/librelane/blob/ca6adb1e2982cd75445a68b632d461213d8ca421/librelane/scripts/pyosys/synthesize.py#L465-L485).

An alternative is the currently disabled post-global-route timing repair. It
uses route-estimated parasitics, resizing and buffering after the first routing
pass. The pinned flow labels this option experimental and potentially slow;
it does not promise restructuring of the original deep mapped cone. Selecting
timing-directed synthesis is a justified final experiment given the measured
cell-arc burden, rather than a prediction that resizing or placement can close
the large slow-corner deficit. [Post-route repair script](https://github.com/librelane/librelane/blob/ca6adb1e2982cd75445a68b632d461213d8ca421/librelane/scripts/openroad/rsz_timing_postgrt.tcl),
[flow option and default](https://github.com/librelane/librelane/blob/ca6adb1e2982cd75445a68b632d461213d8ca421/librelane/flows/classic.py#L158-L166).

Mapping may increase area, congestion, runtime and hold-repair demand, and can
worsen other corners. Synthesis estimates do not include final routing, so the
new netlist still requires all existing source, functional and physical gates.
The two synthesis changes form one revision; their effects cannot be isolated
from a single resulting run. No closure or speedup is predicted.

The final revision must retain density 45 percent, configured threads 4,
all margins, tool/library/workflow pins, checker settings, **6 × 4 / 20 ns**,
and every frozen RTL/model/frontend/timer/vocabulary/state semantic. It must
not relax a clock, add timing exceptions, filter acceptance corners or weaken
an oracle. One setting revision remains, allowing **attempt 3 only**. No fourth
run or semantic repair is permitted in this campaign; a remaining failure
must be preserved and reported alongside the reached demonstrations.
