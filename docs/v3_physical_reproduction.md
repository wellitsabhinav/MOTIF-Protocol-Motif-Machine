# Reproducing identified v3 physical evidence

This guide documents the physical evidence helpers and their current command
interfaces. It makes no physical qualification or timing-closure claim. The
[campaign report](research/v3_temporal_qualification/final_report.md) records
reached results; the commands below keep eligibility, measurement extraction,
functional testing, presentation and the final gate separate.

The initial attempt has [intent](../experiments/temporal_qualification/physical/attempt_1_intent.json)
and [dispatch](../experiments/temporal_qualification/physical/attempt_1_dispatch.json)
receipts for source `5467fd4d15a18dda9bc58a93bb3182b03629aa4b` and
[official workflow run 38349981124](https://github.com/wellitsabhinav/MOTIF-Protocol-Motif-Machine/actions/runs/38349981124).
Those receipts identify an attempt, rather than establish its outcome. Fetch
fresh completed-run metadata when recording a final result; a dispatch-time
snapshot does not establish job completion.

Run repository commands from its root. Local extraction and identity helpers
use Python, Git and the committed qualification receipts. The renderer also
needs the plotting dependencies described in the
[getting-started guide](getting_started.md). The actual physical flow runs on
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
TASK_SOURCE_SHA=5467fd4d15a18dda9bc58a93bb3182b03629aa4b
TASK_RUN_ID=38349981124
TASK_DIR=build/v3_physical/attempt_1
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

Before a new dispatch, `--intent` creates the next immutable numbered intent:

```bash
python -m tools.v3_physical --source-sha "$TASK_SOURCE_SHA" --intent
```

Do not run this again to reproduce the existing initial intent. It allocates a
new attempt number, rather than replaying an old one. The initial attempt must
use all original physical inputs. At most two further attempts are allowed,
each with a diagnosed flow-setting revision in `src/config.json`. Model/RTL
semantics, tool lock, official workflow and allocation remain fixed. A revision
requires retained negative qualification evidence for the previous attempt,
plus a diagnosis JSON with `previous_attempt`, a concrete `failure` and
`permitted_setting_changes`. It must implement a changed configuration hash.

```bash
python -m tools.v3_physical --source-sha "$TASK_SOURCE_SHA" --intent \
  --diagnosis experiments/temporal_qualification/physical/attempt_1_diagnosis.json
```

The diagnosis path above is the naming pattern for a future diagnosed revision;
it is not a claim that such a revision or diagnosis exists. An unfinished run
is not a diagnosed failed attempt. Preserve the completed failed run and its
actual cause before preparing a revision. Do not use GitHub's rerun button to
bypass the limit: dispatch recording requires `run_attempt == 1`. Separate
routed functional retests reuse a physical artifact and run no new physical
flow.

After dispatch, retain the GitHub workflow JSON and bind it to the intent:

```bash
python -m tools.v3_physical --source-sha "$TASK_SOURCE_SHA" \
  --record-dispatch 1 --workflow "$TASK_DIR/workflow_dispatch_snapshot.json"
```

This verifies the repository, official workflow path, dispatch event, exact
head SHA and first run attempt. It refuses a conflicting replacement dispatch.

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
gh api "repos/$TASK_REPO/actions/artifacts/${TASK_ARTIFACT_ID:?Set the identified artifact ID}" > "$TASK_DIR/artifact_api.json"
gh api "repos/$TASK_REPO/actions/artifacts/$TASK_ARTIFACT_ID/zip" > "$TASK_DIR/physical_artifact.zip"
```

The correspondence command needs the API metadata plus
`local_archive_path`. Its published `digest` must be a SHA-256 that matches the
downloaded ZIP; a missing digest is unavailable evidence. The following Python
example prepares the metadata and extractor input receipt, then extracts into
a fresh directory after rejecting unsafe archive members. Export `TASK_DIR`
first so Python receives the same explicit directory.

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
  --output experiments/temporal_qualification/physical/attempt_1_result.json
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
If no physical archive was published, record terminal official failure without
inventing an artifact identity:

```bash
python -m tools.v3_physical --source-sha "$TASK_SOURCE_SHA" --record-failure 1 \
  --workflow "$TASK_DIR/workflow.json" --jobs "$TASK_DIR/jobs.json" \
  --artifacts "$TASK_DIR/artifacts.json"
```

This writes the failed-attempt ledger and exits nonzero. It requires a completed
unsuccessful run, a failed required official job and the matching immutable
dispatch. If physical archives exist, use normal partial-metric extraction.
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
  --output build/demo/physical_v3/attempt_1
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

Keep each attempt in a separate ignored `build/` directory. Full archives,
traces, simulator output, netlists, stage databases and GDS remain outside Git
and belong in identified CI artifacts or releases. Commit concise receipts,
diagnoses and selected small figures only after provenance checks. The routed
workflow currently retains its evidence artifact for 14 days; preserve any
required long-lived release artifacts before that retention window expires.
