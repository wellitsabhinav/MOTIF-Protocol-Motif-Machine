# Reproducing identified v3 physical evidence

This guide documents the physical evidence helpers and their current command
interfaces. It makes no physical qualification or timing-closure claim. The
[campaign report](research/v3_temporal_qualification/final_report.md) records
reached results; the commands below keep eligibility, measurement extraction,
functional testing, presentation and the final gate separate.

Attempt 1 was cancelled and published no physical archive; its
[terminal result](../experiments/temporal_qualification/physical/attempt_1_result.json)
preserves the incomplete outcome and unknown cancellation cause. Attempt 2,
[run 38429471310](https://github.com/wellitsabhinav/MOTIF-Protocol-Motif-Machine/actions/runs/38429471310)
at source `f55553a2b10b0880268663d8f06067c5ba1e14e0`, completed with setup
failure. Its identified `GDS_logs` archive contains final extracted metrics,
reports and layout artifacts, with
[negative qualification](../experiments/temporal_qualification/physical/attempt_2_result.json),
[measurements](../experiments/temporal_qualification/physical/attempt_2_metrics.json),
[source correspondence](../experiments/temporal_qualification/physical/attempt_2_source_correspondence.json)
and [diagnosis](research/v3_temporal_qualification/physical_attempt_2_diagnosis.md).
All three corners have negative setup WNS/TNS. Routing DRC, Magic DRC, LVS and
antenna metrics are zero, while KLayout DRC is unavailable and official precheck
and routed functional tests were skipped. Final metrics and GDS availability
do not establish physical qualification.

Attempt 3 ended **cancelled after the official six-hour execution limit** as
[official run 38470361703](https://github.com/wellitsabhinav/MOTIF-Protocol-Motif-Machine/actions/runs/38470361703).
The [final intent](../experiments/temporal_qualification/physical/attempt_3_intent.json)
binds source `5dbf3abf11f61a8e6bd26cc5f328999190f12859` and LF intent SHA-256
`0a47370b37cf44fcf5e71f356ae91f0c88e3121452a70e0f35c013dfa040c417`.
The [diagnosed final revision](../experiments/temporal_qualification/physical/attempt_3_diagnosis.json)
changes only synthesis strategy to `DELAY 0` and synthesis corner to
`nom_slow_1p08V_125C`. All frozen source bytes, 6 × 4 allocation, 20 ns target,
flow pins and acceptance gates remain unchanged. Three is the maximum number
of physical attempts, and all three are now used; no fourth run is permitted.
Exact source CI and the unseen gate passed before the approved helper launched
the run at `2026-10-13T21:24:29Z`. The
[actual dispatch](../experiments/temporal_qualification/physical/attempt_3_dispatch.json)
and [downloaded API receipt](../experiments/temporal_qualification/physical/attempt_3_dispatch_api_receipt.json)
bind that execution to the previously committed intent. No physical archive
was published; official precheck and routed tests were skipped. Its
[terminal result](../experiments/temporal_qualification/physical/attempt_3_result.json),
[explicit check annotation](../experiments/temporal_qualification/physical/attempt_3_check_annotations.json)
and [final diagnosis](research/v3_temporal_qualification/physical_attempt_3_diagnosis.md)
preserve the actual failure and unavailable final metrics. The campaign is
stopped with physical qualification unestablished; no further run or repair
is permitted within its fixed limit.

Run repository commands from its root. Local extraction and identity helpers
use Python, Git and the committed qualification receipts. The renderer also
needs the plotting dependencies described in the
[getting-started guide](GETTING_STARTED.md). The actual physical flow runs on
the pinned Linux workflow, rather than through these local Python helpers.
The Bash download examples additionally require an authenticated GitHub CLI
with permission to read this repository's Actions artifacts. A connected
GitHub artifact download is also usable when its exact metadata and ZIP bytes
are retained.

## Eligibility and the attempt ledger

[`tools.v3_physical`](../tools/v3_physical.py) verifies the frozen manifest,
the committed unseen logical receipt and every protected source byte at an
explicit 40-character workflow head SHA. It also compares the exact runtime
file inventory, allocation and physical inputs. The retained allocation is
`6x4` and `CLOCK_PERIOD` is 20 ns. The immutable semantic manifest is
[`frozen_v3_manifest.json`](../experiments/temporal_qualification/frozen_v3_manifest.json),
whose LF-normalized SHA-256 is
`71d5b07b5524fb6fa702357291eb35f52eccc5861111f7824b6fb9ead98a3047`.

```bash
TASK_SOURCE_SHA=f55553a2b10b0880268663d8f06067c5ba1e14e0
TASK_RUN_ID=38429471310
TASK_DIR=build/v3_physical/attempt_2_reproduction
python -m tools.v3_physical --source-sha "$TASK_SOURCE_SHA"
```

A `PASS` from this command means eligibility and source/settings checks passed.
It does not run synthesis or place and route. The actual
[`gds.yml`](../.github/workflows/gds.yml) workflow is manually dispatched at
the identified source. Its pinned action is
`3412659307918422f3f0727917cf9b499aaca588`, support tools are
`d66cf179e7bc4d296362ab7e2e3b344dc3c4f665`, and LibreLane is `3.1.0.dev3`.
The CMOS5L PDK and other recorded identities are in
[`flow-lock.json`](../flow-lock.json). The original physical-input hashes are
separate from the frozen semantic boundary.

Before a new dispatch, `--intent` creates the next immutable numbered intent.
All three campaign intents already exist. The examples below document that
interface; **do not replay them to recreate an existing intent or allocate a
fourth attempt**:

```bash
TASK_NEXT_SOURCE_SHA=5dbf3abf11f61a8e6bd26cc5f328999190f12859
python -m tools.v3_physical --source-sha "$TASK_NEXT_SOURCE_SHA" --intent
```

Do not run this again to reproduce an existing intent. It allocates a
new attempt number, rather than replaying an old one. The initial attempt must
use all original physical inputs. At most two further attempts are allowed,
each with a diagnosed flow-setting revision in `src/config.json`. Model/RTL
semantics, tool lock, official workflow and allocation remain fixed. A revision
requires retained negative qualification evidence for the previous attempt,
plus a diagnosis JSON with `previous_attempt`, a concrete `failure` and
`permitted_setting_changes`. It must implement a changed configuration hash.

```bash
python -m tools.v3_physical --source-sha "$TASK_NEXT_SOURCE_SHA" --intent \
  --diagnosis experiments/temporal_qualification/physical/attempt_3_diagnosis.json
```

For the prepared final intent, the source argument was the exact attempt-3
source shown as `TASK_NEXT_SOURCE_SHA`, rather than the attempt-2 replay source.
Only the example with `--diagnosis` represents that final revision. The committed
diagnosis preceded its two setting changes, and the intent preceded dispatch.
An unfinished run is not a diagnosed failed attempt. Preserve the completed
failed run and its actual cause before preparing a revision. Do not use
GitHub's rerun button to
bypass the limit: dispatch recording requires `run_attempt == 1`. Separate
routed functional retests reuse a physical artifact and run no new physical
flow.

After dispatch, retain the GitHub workflow JSON and bind it to the intent:

```bash
python -m tools.v3_physical --source-sha "$TASK_SOURCE_SHA" \
  --record-dispatch 2 --workflow "$TASK_DIR/workflow_dispatch_snapshot.json"
```

This verifies the repository, official workflow path, dispatch event, exact
head SHA and first run attempt. It refuses a conflicting replacement dispatch.
The existing attempt-2 dispatch is already recorded; this is an interface
example, not an instruction to overwrite its immutable receipt. Measurement
and rendering reproduction require no dispatch or ledger mutation.

## Download and verify one official archive

Record workflow/jobs metadata and the artifact list before choosing the exact
artifact ID. Do not select an archive merely because it has a familiar name.

```bash
mkdir -p "$TASK_DIR"
TASK_REPO=wellitsabhinav/MOTIF-Protocol-Motif-Machine
gh api "repos/$TASK_REPO/actions/runs/$TASK_RUN_ID" > "$TASK_DIR/workflow.json"
gh api "repos/$TASK_REPO/actions/runs/$TASK_RUN_ID/jobs?per_page=100" > "$TASK_DIR/jobs.json"
gh api "repos/$TASK_REPO/actions/runs/$TASK_RUN_ID/artifacts?per_page=100" > "$TASK_DIR/artifact_list.json"
```

Set `TASK_ARTIFACT_ID` to an independently checked ID from that run. The
following commands require that value and retain the published artifact
metadata and raw ZIP:

```bash
TASK_ARTIFACT_ID=11843789314  # Actual attempt-2 GDS_logs artifact
gh api "repos/$TASK_REPO/actions/artifacts/${TASK_ARTIFACT_ID:?Set the identified artifact ID}" > "$TASK_DIR/artifact_api.json"
gh api "repos/$TASK_REPO/actions/artifacts/$TASK_ARTIFACT_ID/zip" > "$TASK_DIR/physical_artifact.zip"
```

The correspondence command needs the API metadata plus
`local_archive_path`. Its published `digest` must be a SHA-256 that matches the
downloaded ZIP; a missing digest is unavailable evidence. The following Python
example prepares the metadata and extractor input receipt, then extracts into
a fresh directory after rejecting unsafe archive members. Export `TASK_DIR`
first so Python receives the same explicit directory.

For attempt 2, the raw ZIP is 265,262,975 bytes and SHA-256
`5cdff1a5201ebad89713da86188c8bd5b0b7d93afa1737752023c6b7d5e2a7d0`.
The recorded correspondence covers all 911 extracted files, including the
actual bundled RTL inventory. Retain the metadata and raw download even though
the associated workflow failed.

```bash
export TASK_DIR
python - <<'PY'
import hashlib, json, os, stat, zipfile
from pathlib import Path, PurePosixPath

root = Path(os.environ['TASK_DIR'])
archive = root / 'physical_artifact.zip'
metadata = json.loads((root / 'artifact_api.json').read_text())
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
if metadata.get('digest') != 'sha256:' + digest:
    raise ValueError('Downloaded ZIP does not match the published artifact digest')
metadata['local_archive_path'] = archive.as_posix()
(root / 'artifact_download.json').write_text(json.dumps(metadata, indent=2) + '\n')
(root / 'artifact_receipts.json').write_text(json.dumps([{
    'id': metadata['id'], 'name': metadata['name'], 'archive_sha256_raw': digest,
    'archive_bytes': archive.stat().st_size,
    'extraction_scope': 'One exact official archive; no mixed extraction root'
}], indent=2) + '\n')
destination = root / 'artifacts'
if destination.exists():
    raise ValueError('Choose a fresh extraction destination')
with zipfile.ZipFile(archive) as bundle:
    seen = set()
    for member in bundle.infolist():
        name, parts = member.filename, PurePosixPath(member.filename).parts
        if (not parts or name.startswith('/') or '\\' in name or ':' in name
                or '..' in parts or stat.S_ISLNK(member.external_attr >> 16)):
            raise ValueError('Unsafe ZIP member: ' + name)
        if not member.is_dir():
            if name in seen:
                raise ValueError('Duplicate ZIP member: ' + name)
            seen.add(name)
    destination.mkdir()
    bundle.extractall(destination)
PY
```

Now verify exact source and extracted-byte correspondence:

```bash
python -m tools.v3_physical --source-sha "$TASK_SOURCE_SHA" \
  --run-id "$TASK_RUN_ID" --artifact-metadata "$TASK_DIR/artifact_download.json" \
  --extracted "$TASK_DIR/artifacts" --output "$TASK_DIR/source_correspondence.json"
```

The helper checks the archive digest, artifact run/head identity, safe unique
ZIP members, and exact equality between every ZIP member's raw hash and the
extracted file inventory. Modified, missing, additional or mixed extracted
files fail. Each correspondence receipt covers one archive. Keep other
archives in their own roots and preserve their own download identities.

If the archive actually bundles `src/*.sv`, their complete LF hash inventory
must equal frozen v3. Otherwise source correspondence uses independent
`git show` reads at the exact workflow commit and labels them
`materialized_identified_workflow_commit`. Git-recovered sources are not
relabeled as bundled build inputs. No declaration-insensitive historical
correspondence exception qualifies v3.

## Extract measurements without deciding qualification

Find the single actual flow-run directory inside the verified archive. It
contains numbered stages and, if produced, `final/`. Set `TASK_FLOW_DIR` to that
explicit directory; do not mix stages from different runs or use an earlier
successful run as a substitute.

For the verified attempt-2 archive the explicit run root is
`$TASK_DIR/artifacts/runs/wokwi`; final timing comes from
`55-openroad-stapostpnr` after RC extraction. The final receipt reports 20,178
standard cells, 263,349 µm² standard-cell area and utilization 0.291827 in a
902,417 µm² core. All-instance/filler area and the independent nominal synthesis
cost are different inventories. Global routing overflow is 7,782 even though
final detailed routing DRC is zero.

```bash
python -m tools.v3_physical_metrics "${TASK_FLOW_DIR:?Set the exact extracted flow-run directory}" \
  --run-id "$TASK_RUN_ID" --source-sha "$TASK_SOURCE_SHA" \
  --artifacts "$TASK_DIR/artifact_receipts.json" --jobs "$TASK_DIR/jobs.json" \
  --workflow "$TASK_DIR/workflow.json" \
  --source-correspondence "$TASK_DIR/source_correspondence.json" \
  --output "$TASK_DIR/metrics.json"
```

[`tools.v3_physical_metrics`](../tools/v3_physical_metrics.py) prefers nonempty
`final/metrics.json`. If that file is unavailable or invalid, it retains the
last numbered stage with an available metric dictionary and labels the result
`partial_unfinished_stage_metrics`. A stage's `state_out.json` records published
state, not proof of job success. The report retains actual stage paths, job and
step status, input raw hashes, source metadata hashes and unavailable reasons.

Measurements include cell count/area, register count, core area/utilization,
detailed/global wirelength, vias, tool-specific DRC, LVS, antenna results,
hold buffers and routing overflow where published. The extractor preserves
the three expected corners and additional actual corners:

| Corner | Voltage | Temperature |
|---|---:|---:|
| `nom_fast_1p32V_m40C` | 1.32 V | −40 °C |
| `nom_typ_1p20V_25C` | 1.20 V | 25 °C |
| `nom_slow_1p08V_125C` | 1.08 V | 125 °C |

Each corner retains setup and hold worst slack, WNS and TNS. Missing timing
keys may use uniquely identified reports from the last actual STA stage;
earlier reports are not blended into a later stage. A present invalid value
does not get replaced by a convenient alias or earlier result. Missing,
nonfinite and unsupported measurements are JSON `null`, with reasons. `null`
never means zero violations or a pass. Overflow may come from the final
congestion table in the actual global-routing log. Mapped nominal cost and
post-layout cell area remain distinct measurements.

## Retest the identified routed netlist

The separate [`v3-routed-tests` workflow](../.github/workflows/v3-routed-tests.yml)
reads `experiments/temporal_qualification/physical/routed_retest.json` with an
explicit positive `build_run_id`. After a successful official physical build,
select that run in this small input file and run the workflow by push, pull
request or manual dispatch. With no selection the routed job is skipped; a
skipped job is not evidence of a functional pass.

The workflow checks source/settings correspondence to the selected physical
head, downloads its `tt_submission` artifact, requires exactly one routed
Verilog file and records its raw hash. The pinned official action runs the
five original runtime tests. The workflow then runs `runtime_lin_unseen` on
the same netlist, covering the four qualified LIN host cases. It hashes the
actual `test/gate_level_netlist.v`, preserves it as `compiled_netlist.v`, and
checks its identity against the downloaded file. XML rosters must contain all
required tests exactly once, without failures, errors or skips.

The published `identified-v3-routed-functional-evidence` artifact retains the
selected workflow metadata, netlist identity, compiled netlist and both XML
results. Download and retain its separate run/artifact/ZIP identity. At its
actual extracted `routed_retest` directory, replay the receipt:

```bash
python -m tools.v3_routed_receipt "${TASK_ROUTED_DIR:?Set the extracted routed_retest directory}"
```

[`tools.v3_routed_receipt`](../tools/v3_routed_receipt.py) additionally checks
the qualified runtime configuration, stimulus and oracle source hashes,
the semantic boundary, downloaded/compiled netlist equality and the six-test
roster. Its `result.json` is zero-delay routed functional evidence. It does
not establish setup/hold timing. The LIN runtime subset observes actual host
loading, receive-only traffic pads and posttraffic FIFO behavior; the complete
34-case core gate established dense temporal acceptance behavior separately.

## Replay the physical gate and preserve failures

[`tools.v3_physical_gate`](../tools/v3_physical_gate.py) re-extracts measurements
and recomputes archive/source correspondence from current identified inputs.
Stale reports, altered files or another frozen boundary fail. For complete
evidence, run:

```bash
python -m tools.v3_physical_gate "$TASK_FLOW_DIR" \
  --metrics "$TASK_DIR/metrics.json" --artifacts "$TASK_DIR/artifact_receipts.json" \
  --jobs "$TASK_DIR/jobs.json" --workflow "$TASK_DIR/workflow.json" \
  --source-correspondence "$TASK_DIR/source_correspondence.json" \
  --physical-artifact-metadata "$TASK_DIR/artifact_download.json" \
  --artifact-directory "$TASK_DIR/artifacts" \
  --routed-receipt "$TASK_ROUTED_DIR/result.json" --routed-directory "$TASK_ROUTED_DIR" \
  --output "$TASK_DIR/qualification_result.json"
```

Qualification requires successful completed official `gds`, `precheck` and
`gl_test` jobs, final metrics, nonnegative finite setup/hold worst slack and WNS,
zero TNS in all expected and actually reported corners, zero detailed-route
DRC/Magic DRC/LVS errors and routing overflow, and zero reported antenna
violations. Missing antenna metrics stay unavailable. The six-test routed
receipt must identify the same source/run and a netlist bound by the physical
archive. This is bounded digital/physical evidence; it adds no analog or silicon
claim.

If routed evidence was never produced, omit both `--routed-receipt` and
`--routed-directory`. With valid remaining archive/measurement inputs, the gate
writes an explicit negative result, marks routed evidence unavailable and exits
nonzero. A supplied invalid routed receipt cannot become a pass. Partial or
missing required timing/check results also fail. Keep the negative result,
job/stage state, logs, archive identity and diagnosis in the same numbered
attempt. Do not replace unavailable inputs with invented zeros or XML passes.
Attempt 2 follows this negative path. Reproduction outputs go under `build/`;
do not overwrite the committed attempt-1 or attempt-2 result receipts.
If no physical archive was published, record terminal official failure without
inventing an artifact identity:

```bash
python -m tools.v3_physical --source-sha "$TASK_SOURCE_SHA" --record-failure 1 \
  --workflow "$TASK_DIR/workflow.json" --jobs "$TASK_DIR/jobs.json" \
  --artifacts "$TASK_DIR/artifact_list.json"
```

This writes the failed-attempt ledger and exits nonzero. It requires a completed
unsuccessful run, a failed required official job and the matching immutable
dispatch. If physical archives exist, use normal partial-metric extraction.
The `--record-failure 1` example applies to the already recorded archive-less
attempt 1 and must use its own source/run metadata. It does not apply to the
attempt-2 archive replay variables, and must not rewrite historical evidence.
An unfinished run cannot unlock a flow revision; the prior failed result must
match its dispatch's source and run ID.

## Render only identified physical views

The presentation command reads the verified artifact and correspondence receipt:

```bash
python docs/demo/render_v3_physical.py \
  --artifact-directory "$TASK_DIR/artifacts" --source-sha "$TASK_SOURCE_SHA" \
  --manifest experiments/temporal_qualification/frozen_v3_manifest.json \
  --manifest-sha256-lf 71d5b07b5524fb6fa702357291eb35f52eccc5861111f7824b6fb9ead98a3047 \
  --correspondence "$TASK_DIR/source_correspondence.json" \
  --output "$TASK_DIR/full_views" \
  --require-view floorplan --require-view placement \
  --require-view routing --require-view gds
```

[`render_v3_physical.py`](demo/render_v3_physical.py) produces plain HTML,
`physical_views.json` and only supported identified views. Each consumed file
must match its receipt hash. Existing PNG/SVG images are copied unchanged.
Without images, floorplan, placement and routing views may be derived from
actual DEF coordinates: die/row/pin origins, cell origins and parsed signal
route centerlines. These are explicitly limited coordinate views; cell widths,
via cuts, route widths, patches and power geometry are not invented. A GDS view
requires the identified GDSII geometry and an existing official rendered image.

The renderer runs no physical flow and makes no qualification decision. Missing
views have unavailable status; missing direct final metrics are `null`.
Invalid nonfinite presentation metrics are rejected rather than displayed as
valid values. Use `--require-view floorplan`, `placement`, `routing` or `gds`
once per required view to fail on unavailable presentation inputs. Ambiguous
inputs require an explicit receipt `views` recipe. Reuse requires the same
identity and receipt, with no unexpected leftover output files. Detailed view
formats and omissions are documented in [physical_views.md](demo/physical_views.md).

Attempt 2 has four actual inputs, all belonging to archive `11843789314`:

| View | Identified geometry/image | Presentation scope |
|---|---|---|
| Floorplan | `runs/wokwi/13-openroad-floorplan/*.def` | Actual die bounds and spans between row site origins |
| Placement | `runs/wokwi/34-openroad-detailedplacement/*.def` | 17,947 actual component origins; points are not cell footprints |
| Routing | `runs/wokwi/44-openroad-detailedrouting/*.def` | Actual signal-route centerlines; via cuts, widths, patches and power geometry omitted |
| GDS | `runs/wokwi/final/gds/*.gds` and `final/render/*.png` | Existing identified official image with bound GDS bytes |

The stars in this table abbreviate the recorded top-module basename; they are
not permission to select arbitrary files. The renderer's receipt retains exact
paths and raw hashes. [Selected view identity](demo/figures/physical/attempt_2/identity.json)
links the public [floorplan](demo/figures/physical/attempt_2/floorplan.svg),
[placement](demo/figures/physical/attempt_2/placement.png),
[routing](demo/figures/physical/attempt_2/routing.png) and
[GDS preview](demo/figures/physical/attempt_2/gds.png) to those inputs. Every
selected view is visibly **UNQUALIFIED**.

## Select small unqualified previews and render metrics

[`select_physical_views.py`](demo/select_physical_views.py) accepts the actual
`--help` arguments `--view-report`, `--metrics`, `--source-sha`, `--run-id`,
optional `--manifest`, and `--output-dir`. It takes the renderer's report and
the same-run measurement receipt. For the recorded failed attempt:

```bash
TASK_PHYSICAL_METRICS=experiments/temporal_qualification/physical/attempt_2_metrics.json
TASK_MANIFEST=experiments/temporal_qualification/frozen_v3_manifest.json
python docs/demo/select_physical_views.py \
  --view-report "$TASK_DIR/full_views/physical_views.json" \
  --metrics "$TASK_PHYSICAL_METRICS" \
  --source-sha "$TASK_SOURCE_SHA" --run-id "$TASK_RUN_ID" \
  --manifest "$TASK_MANIFEST" --output-dir "$TASK_DIR/selected_views"
```

The full renderer received the explicit `--correspondence` receipt. The
selector then requires exact RTL correspondence, matching view/metric source
and workflow identities, and the same artifact ID and raw ZIP hash. It reads
the supplied immutable manifest, checks its LF hash against both source/view
boundaries and the fixed v3 manifest hash, and obtains preregistration from
that checked manifest. The measurement receipt's embedded source
correspondence must have the same source, manifest and preregistration
identities. The selector has no separate `--source-correspondence` argument;
that validation uses the supplied metric receipt. It also requires recorded
`gds=failure`, `precheck=skipped` and `gl_test=skipped` conclusions. This helper
is for the current attempt-2 negative presentation, not a later closure claim.

Selection writes `identity.json`, four PNG previews and a floorplan SVG. PNG
layout content is uniformly downscaled to at most 1,600 pixels without
upscaling, then wrapped with a status banner/footer. The floorplan keeps its
vector geometry inside a translated group and adds a status header. All input
and selected-output hashes and transformations are retained. Dense placement
and routing SVGs, raw GDS and netlists stay in ignored build/CI artifacts; they
are not copied into the selected public package or Git.

[`render_physical_metrics.py`](demo/render_physical_metrics.py) accepts
`--physical-receipt`, `--physical-receipt-sha256`, `--physical-source-sha`,
optional `--manifest`, and `--output-dir`. Supply the expected raw hash of the
identified receipt explicitly, independently of the file being rendered:

```bash
TASK_METRICS_SHA256=64fb505400247f6edfe05021923583140fe9404e7e46f656ec52044c5215c5f3
python docs/demo/render_physical_metrics.py \
  --physical-receipt "$TASK_PHYSICAL_METRICS" \
  --physical-receipt-sha256 "$TASK_METRICS_SHA256" \
  --physical-source-sha "$TASK_SOURCE_SHA" \
  --manifest "$TASK_MANIFEST" --output-dir "$TASK_DIR/metric_figures"
```

This checks the raw receipt bytes, exact source SHA and embedded source
correspondence, then binds the actual manifest LF hash and its preregistration
to that source correspondence. An altered receipt or different semantic
boundary fails. If checkout newline conversion changed the tracked JSON's raw
bytes, materialize its exact committed Git blob before using the recorded raw
hash; do not replace the expected hash with one computed from altered input.

The outputs are `physical_cost.{svg,png,json}` and
`physical_timing.{svg,png,json}`. Missing metrics remain unavailable; utilization
converts the recorded fraction to percent. Corner WNS/TNS retain their signs
and a visible zero reference. The figures keep physical stage measurements
separate from the nominal mapped-area cap and preserve source paths, input
identities, original values and renderer hashes in JSON. The corresponding
selected [measurement figure](demo/figures/physical/attempt_2/physical_cost.svg)
and [timing figure](demo/figures/physical/attempt_2/physical_timing.svg) remain
UNQUALIFIED. A renderer's `PASS` means its input identities and presentation
requirements passed; it is not the campaign's physical gate.

Both helpers require fresh empty output directories. Keep full views,
selected previews and metric figures in separate replay directories. After
review, only concise identities and the selected small floorplan/metric SVGs,
PNG previews and JSON receipts belong in the public package. Large full
vector views and raw physical geometry remain outside that package and Git.

Keep each attempt in a separate ignored `build/` directory. Full archives,
traces, simulator output, netlists, stage databases and GDS remain outside Git
and belong in identified CI artifacts or releases. Commit concise receipts,
diagnoses and selected small figures only after provenance checks. The routed
workflow currently retains its evidence artifact for 14 days; preserve any
required long-lived release artifacts before that retention window expires.
