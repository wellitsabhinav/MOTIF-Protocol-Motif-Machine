# Competing hypotheses (registered before probes)

| ID | Claim | Initial support | Initial contradiction | Falsifying experiment |
|---|---|---|---|---|
| H1 | Flow dominates; architecture can remain | Large post-CTS repair activity | Typical pre-PNR arrival 48.40 ns with ideal wires | Compare ideal-wire STA and architectural cuts |
| H2 | Cycle boundary dominates | Four dependent table/actions in one cycle | A cut can violate atomic event semantics | Registered fetch/execute/action tournament plus semantic audit |
| H3 | Decode/table structure dominates | 16x64 indirect reads repeated in chain | Storage cost alone does not imply slow execution | v2/v3 depth and predecode probes |
| H4 | Control distribution dominates | PC/control and reset feed many loads | Post-route paths contain many non-buffer gates | Fanout ranking and cell/net breakdown |
| H5 | Congestion dominates | Attempt 3 Metal3 demand exceeds capacity | Attempt 2 routes; pre-PNR already fails | Archived stage timing and congestion comparison |
| H6 | Temporal extension dominates | v3 adds 18 state bits and mapped area | v2 already has the four-action interpreter | Matched v2, v3, temporal elision/state removal |
| H7 | Competition architecture mismatch | No qualified routed v2/v3 result | Generic vocabulary has bounded logical demonstrations | Budgeted rescue and competition comparison |

Confidence and final dispositions will be recorded after measurements. No
survival presumption; sunk costs are excluded from the decision.
