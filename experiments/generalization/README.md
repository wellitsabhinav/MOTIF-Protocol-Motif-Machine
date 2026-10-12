# Frozen-vocabulary qualification

The initial manifest inventories the model and qualified RTL subset at its source
commit. `BYTE_EXCHANGE` is model-only in that baseline. Firing aliases are
suboperations, not additional independently configurable motifs.

Gate 1 promotes the existing I2C model machinery. A separate promoted manifest
will freeze that implementation and its fixed integration for subsequent reuse
tests. Neither inventory is regenerated in place. An architectural source change
after a reuse experiment begins invalidates that experiment.

```sh
python -m tools.frozen_manifest --historical
python -m tools.generalization --gate 1
```

Hashes normalize CRLF to LF, matching the repository text convention. The
boundary includes all model and RTL sources, configuration and physical flow
inputs. Routing counts denote named logical connections; they do not imply a
programmable routing table or physical wire count.

`gate1_logical.json` records 48 deterministic I2C cases and 88,287 normalized
model/RTL cycles at the recorded source SHA. The model is unchanged. Generated
input schedules, normalized traces and simulator output are under ignored
`build/generalization/gate1`; Linux CI retains trace artifacts for 14 days.
Use `--synthesize` for a separate synthesis sanity report. If the pinned typical
library is present under ignored build output, this also reports nominal cell
area; otherwise it reports generic cell counts. This command does not run P&R.

`gate1_synthesis.json` is a nominal typical-library mapping, not a routed-area
measurement or a matched-reference comparison. Historical subset reports remain
separate. `gate1_physical.json` records the fully passing pinned official flow
at its original source SHA, plus artifact digest and the declaration-only circuit
correspondence. `promoted_motif_vocabulary.json` freezes the resulting hardware
and integration without overwriting the initial inventory.

`python -m tools.generalization --gate 2` reproduces six configuration-only
Microwire attempts and their negative counterexamples. `gate2_result.json` records
model/RTL agreement and `MOTIF_BYTE_EXCHANGE_PROTOCOL_SPECIFIC`. The closest
configuration returns A5FF rather than A55A because per-byte controller ACK is
mandatory. `reuse.json` counts validated users only. Gate 3 is unattempted under
the stop condition. No source changes were made to rescue the failed workload.

The trace harness schedules host actions synchronously after the unchanged
model's actor tick. Full-at-decision RX NACK and delayed empty-TX readiness are
explicitly tested. START/STOP controller actions may complete an eighth data
clock before framing; accepted bytes survive release as the execution contract
requires. A STOP requested while stretched SCL resolves low is not a wire STOP.

`divergences.json` records the watchdog semantic correction and host scheduling
distinction. No model change was used to force correspondence.
