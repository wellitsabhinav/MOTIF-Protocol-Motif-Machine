# Post-freeze demonstration input

The frozen demonstration code can consume a subsequently qualified workload without a tool edit. This interface selects no workload and performs no candidate research.

Create `experiments/temporal_qualification/unseen/config.json` as an ordinary public `Config` mapping and `result.json` with the following fields after the campaign reaches unseen evaluation:

| Field | Required evidence |
| --- | --- |
| `passed` | Boolean true only after the independent unseen oracle passes |
| `frozen_before_after_identical` | Boolean true after the semantic boundary checks |
| `frozen_manifest_sha256_lf` | SHA-256 of the frozen v3 manifest with LF text normalization |
| `demonstrations` | Nonempty array of identified cases described below |

Each case supplies `name`, `trace_directory` relative to the repository under `build/`, `expected`, `observed`, `oracle` containing `passed: true`, and `evidence_sha256_lf` for `inputs.txt`, `model.jsonl`, `rtl.jsonl`, and `simulation.log`. Expected and observed summaries must agree; keep the full independent oracle measurements and constraints in `oracle`. The name is an ASCII letter/digit/underscore followed by at most 79 letters, digits, underscores or hyphens. Optional `configuration` overrides the common Config mapping. Optional `pins` is an array of `[label, pin_number]` pairs; pin numbers are 0–7.

The renderer verifies the frozen manifest before and after, checks every artifact identity, and compares every protected normalized model/RTL field across the complete trace. It uses the existing waveform and ordered-execution renderer. It records both late-input file hashes and the verified freeze identity in generated results.

`--protocol unseen` is exposed only when the late `result.json` exists. `--all` then includes it. Unreached or failed evaluation cannot produce a PASS; incomplete identities, a failed oracle, unequal traces or a changed freeze return a nonzero exit status. The full evidence remains in ignored build output; selected figures and short excerpts may be published through the existing `--publish-figures` option.
