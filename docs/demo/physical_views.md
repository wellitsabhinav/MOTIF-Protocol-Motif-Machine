# Rendering identified v3 physical artifacts

`render_v3_physical.py` is ready for an identified physical attempt. No v3
physical attempt or result is established by adding or running this renderer.
It runs no synthesis, place-and-route, GDS conversion, precheck or functional
simulation, and makes no physical qualification decision.

Supply the immutable semantic manifest and its independently recorded SHA-256,
the exact physical workflow head commit, an extracted artifact directory, and
a source correspondence receipt. All consumed physical files must have raw
SHA-256 entries in that receipt. The renderer checks RTL against the exact LF
hashes in the frozen manifest; the historical declaration-insensitive
correspondence exception is not accepted for v3.

```powershell
python docs/demo/render_v3_physical.py `
  --artifact-directory build/v3_physical/attempt_1/artifacts `
  --source-sha <exact-workflow-head-commit> `
  --manifest experiments/temporal_qualification/frozen_v3_manifest.json `
  --manifest-sha256-lf 71d5b07b5524fb6fa702357291eb35f52eccc5861111f7824b6fb9ead98a3047 `
  --correspondence build/v3_physical/attempt_1/source_correspondence.json `
  --output build/demo/physical_v3/attempt_1
```

The output is a plain `index.html`, `physical_views.json`, and only the views
supported by identified artifacts. Missing metrics are JSON `null`. Missing
views have `status: "unavailable"` and `outputs: null`. Add one or more
`--require-view floorplan`, `--require-view placement`, `--require-view routing`
or `--require-view gds` options to make a missing required view exit nonzero.
Identity violations always exit nonzero. A successful rendering command says
only that source identity and its selected presentation inputs were checked.
Use a fresh output directory for each attempt or changed receipt. Reusing an
output directory requires the same identity and receipt; unexpected leftover
files or output from another attempt cause the command to refuse reuse.

The correspondence receipt has this structure. Angle-bracket values below
are explanatory placeholders, not an existing attempt or a runnable receipt.

```json
{
  "schema_version": 1,
  "source_sha": "<40-character exact workflow head commit>",
  "workflow_head_sha": "<same exact commit>",
  "frozen_manifest_sha256_lf": "<recorded frozen manifest SHA-256>",
  "rtl_source_hashes_lf": {
    "src/motif_core.sv": "<frozen LF hash>",
    "<every other frozen src/*.sv path>": "<its frozen LF hash>"
  },
  "source": {
    "role": "materialized_identified_workflow_commit",
    "derivation": "git show of each RTL path at the independently identified workflow_head_sha"
  },
  "artifact": {
    "id": 123456789,
    "name": "<official artifact name>",
    "archive_sha256_raw": "<downloaded archive SHA-256>",
    "workflow_run_url": "https://github.com/<owner>/<repo>/actions/runs/<run-id>"
  },
  "files_sha256_raw": {
    "runs/wokwi/final/metrics.json": "<raw hash>",
    "runs/wokwi/13-openroad-floorplan/<top>.def": "<raw hash>",
    "runs/wokwi/34-openroad-detailedplacement/<top>.def": "<raw hash>",
    "runs/wokwi/44-openroad-detailedrouting/<top>.def": "<raw hash>",
    "runs/wokwi/final/gds/<top>.gds": "<raw hash>",
    "runs/wokwi/final/render/<top>.png": "<raw hash>"
  },
  "expected_corners": [
    "nom_fast_1p32V_m40C", "nom_typ_1p20V_25C", "nom_slow_1p08V_125C"
  ],
  "checks": {
    "official_precheck": null,
    "routed_netlist_functional_tests": null
  }
}
```

`rtl_source_hashes_lf` must contain exactly all frozen `src/*.sv` entries,
including the reference top. Do not add keys for generated netlists or flow
JSON. Materialized sources are distinct from bundled sources: when `source`
has no `directory`, the renderer independently reads each RTL file with
`git show <workflow_head_sha>:<path>` from the local repository. That commit
must be locally available. If `directory` is supplied, it is relative to the
artifact directory, contains the files below `src/` (so `motif_core.sv` is
directly inside it), and the renderer also checks materialized bytes against
the named commit. Record the exact derivation in either materialized case.

Use `source.role: "bundled_workflow_sources"` only when the actual downloaded
workflow bundle includes those sources. Its `source.directory` is mandatory.
Do not relabel files recovered from Git as bundled build inputs. The parent
physical evidence process is responsible for identifying the workflow head
SHA and run/artifact IDs independently and retaining correspondence evidence;
the renderer verifies the bytes that receipt binds.

The default discovery chooses receipt-bound inputs in the
`*-openroad-floorplan`, `*-openroad-detailedplacement`, and
`*-openroad-detailedrouting` stage directories, plus `final/gds` and
`final/render`. Stage numbers may change. If more than one matching input
exists, the command refuses ambiguity. Use an explicit `views` map to select
the actual stage and image instead:

```json
{
  "metrics_path": "runs/wokwi/final/metrics.json",
  "views": {
    "floorplan": {"geometry": "runs/wokwi/13-openroad-floorplan/<top>.def"},
    "placement": {"geometry": "runs/wokwi/34-openroad-detailedplacement/<top>.def"},
    "routing": {"geometry": "runs/wokwi/44-openroad-detailedrouting/<top>.def"},
    "gds": {
      "geometry": "runs/wokwi/final/gds/<top>.gds",
      "image": "runs/wokwi/final/render/<top>.png"
    }
  }
}
```

Each map accepts an optional identified PNG/SVG `image` and `geometry`.
An existing image is copied byte for byte. Without an existing image,
floorplan, placement and routing can be rendered from the actual stage DEF.
The floorplan shows the declared die rectangle, spans between the first and
last row site origins, and placed pin origins. Placement shows actual component
origins as points, without inferring cell dimensions from unavailable LEF.
Routing shows all parsed routed `NETS` path centerlines, grouped by layer;
wire widths, via cuts, `RECT` patches and `SPECIALNETS` power geometry are
explicitly omitted. These DEF views are coordinate views, not fabricated
mask polygons or complete GDS views. The output includes the exact coordinate
inventory counts and input hashes. A GDS view requires both an identified
GDSII file and an existing official PNG/SVG render; the renderer installs no
layout tools and does not synthesize an image when the official render is
missing.

Useful physical inputs to retain from each attempt are:

- The workflow run ID, exact head SHA, downloaded artifact IDs/names/raw archive
  hashes, and official job/step status receipts.
- Each actual stage's `state_out.json`, the floorplan/placement/routing DEF files,
  and final GDS and render files. A state file records a published state and is
  not treated as proof that a job passed.
- `final/metrics.json`, global-routing log, all corner STA reports, antenna/DRC/LVS
  reports, official precheck output, routed-netlist tests and source correspondence.
- The separately recorded physical flow configuration, pinned tool/library
  identity, and each diagnosed flow-setting revision.

All physical input artifacts and full generated output remain in ignored
`build/` or identified CI/release artifacts. Commit only selected small figures
and concise receipts after their provenance is checked. Keep failed attempts
in separate directories; do not overwrite their inputs with a later attempt.

The independent metric extractor is `python -m tools.v3_physical_metrics`.
Supply its positional single flow-run directory (the directory that contains
numbered stages and `final/`), `--run-id`, `--source-sha`, `--artifacts` and
`--jobs` JSON receipts, and `--output`. Optional `--workflow` and
`--source-correspondence` receipts retain run status and correspondence;
`--scope` records an explicit extraction description. Artifact receipts use
the ID/name/`archive_sha256_raw` identity above and may be a list for multiple
downloaded archives. Jobs metadata may be an object containing `jobs` or the
job list itself. The CLI hashes the exact raw metadata files as well as each
flow input it reads.

This extractor prefers actual nonempty `final/metrics.json`, otherwise the
last numbered stage's available `state_out.json` metric dictionary. It labels
the latter `partial_unfinished_stage_metrics`. The three expected nominal
corners and any additional actual corners are retained; absent values have
individual reasons. Missing timing keys may use values from the last actual
STA stage's per-corner reports, retaining that stage identity. Nonfinite values
are not hidden by earlier reports. Separate tool-specific DRC and antenna
measurements are retained, and overflow may be taken from the actual final
global-routing congestion table. A final metrics file, published stage state,
or successful extraction never establishes physical closure: the separate
campaign attempt ledger owns that decision and checks all required gates.
