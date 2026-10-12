# Controlled exchange decomposition

One architectural repair replaces the frozen protocol-specific BYTE_EXCHANGE
with FIELD_DECISION, DIRECTION_HANDOFF, BOUNDARY_RESPONSE and WAIT_POLICY.
Six existing motif types remain shared. The fixed instruction table has sixteen
64-bit entries, a four-bit PC, and a four-entry immediate execution bound.

`source_audit.md` precedes the immutable preregistration commit
`d3ca35e2221f8e7654f4c42fa79ab7992e8ee8d8`. `model_feasibility.json` records
independent model feasibility before RTL implementation. Every implementation
correction is recorded in `corrections.json`; the semantics document is unchanged.

The qualified v2 circuit retains all 48 I2C cases and 88,287 cycles, including
legacy externally visible equivalence. Eight synthetic field/direction probes
cover 1, 8, 9 and 16 bits in both orders; they are not protocol users. Microwire
returns the unchanged oracle word A55A with separate DI/DO, active-high framing,
dummy zero, continuous output and no target clock drive. Runtime host tests
exercise the generic table, I2C starvation/recovery and back-to-back Microwire.

```sh
python -m pytest -q
python -m tools.generalization --gate 2 --baseline legacy
python -m tools.generalization --gate 1 --baseline v2
python -m tools.generalization --gate 2 --baseline v2
python -m tools.exchange_decomposition --check-preregistration
python -m tools.exchange_decomposition --check-freeze
```

The legacy command uses an isolated fixture of
`7a74a1772dd178e498228667b54ec6a2fd39373a`. Its source SHA and hashes are
checked; its A5FF failure remains `MOTIF_BYTE_EXCHANGE_PROTOCOL_SPECIFIC`.
Historical manifests, results, oracle inputs and physical reports are unchanged.

Generated vectors, complete normalized traces and simulator logs live in ignored
build output and are reproducible. Checked-in results retain their hashes.
SHA-256 text hashes normalize CRLF to LF. On Windows the local Icarus runtime
can be selected through IVERILOG_BASE; this is environment setup, not protocol
configuration.

`frozen_v2_manifest.json` protects all model/RTL, host decoding, packing,
routing and physical inputs, plus the generic trace compiler. After freeze,
new workload configuration and independent oracle/stimulus may be added outside
that boundary. The third workload was selected and committed afterward in `4959350`.
No second semantic repair is allowed. Full CMOS5L is gated on three-protocol
logical success; current v2 synthesis is separate from historical routed evidence.

The selected 1-Wire reset/presence subset matches model/RTL across 1,302,050
cycles and passes eight of nine independent cases. Interrupted short lows
produce a false presence pulse: `MOTIF_V2_UNSEEN_PROTOCOL_GENERALIZATION_PARTIAL`.
No second repair or v2 physical run occurs. See [the report](report.md),
[selection](third_selection.md), [result](third_result.json) and
[counterexample](third_counterexample.json). Failed attempts are not validated users.

```sh
python -m tools.generalization --gate 3 --baseline v2
python -m tools.unseen_result
python -m tools.accounting
```
