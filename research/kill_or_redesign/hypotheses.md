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

Confidence and final dispositions are recorded below after measurements. No
survival presumption; sunk costs are excluded from the decision.

## Measured disposition

| ID | Supporting evidence | Contradicting evidence | Confidence / disposition | What could falsify this disposition |
|---|---|---|---|---|
| H1 | Common buffering converts typical v3 WNS from −31.62 to +2.06 ns; flow choices matter | Full slow WNS −5.72; continuing PC path −4.285 even at zero RC; two historical flow revisions did not qualify | High: flow amplifies; low confidence in flow-only rescue; KEEP unsupported | Correct unchanged architecture physically closes all gates under legitimate constraints |
| H2 | P2 slow WNS +9.825; transaction area falls 68.45%; global graph depth 81→41 | P1 leaves three later dependent reads and gains only 0.595 ns slow slack | High: an execution boundary is useful | Correct integrated registered sequencer loses timing/area margins |
| H3 | Four dependent table/action reads; v2 has the same slow failure; P2 reduces mux maximum 21→8 | P2 retains all table storage and host logic, so generic vocabulary itself is not fatal | High: repeated decode/read/control arrangement, not programmability alone | One-cycle four-action implementation closes without comparable structural work |
| H4 | Raw reset fanout 1,220, PC 274; 2,619 optimistic v3 buffers | PC path still fails with every live net <=8 fanout and zero RC | High as amplifier; fanout-only explanation rejected | Equivalent local-control implementation alone closes physical gates; P4 has no timing result |
| H5 | Attempt 3 total route overflow 71,352, Metal3 demand 128.46% | Attempt 2 completed route; raw pre-layout and zero-RC probes already fail | High as physical amplifier; routing-only origin rejected | Healthy synthesis with unchanged architecture followed by routing-only collapse that accounts for all loss |
| H6 | v3 mapped area +8.1623%, adds 18 state bits | v2 buffered slow −5.528, v3 −5.722; elision −6.857; state clamp −6.529 | High: dominant-temporal-cause rejected; marginal contribution remains mapping-dependent | Controlled robust matched mapping finds a temporal-dependent dominant penalty absent from v2 |
| H7 | Three unqualified physical attempts; atomic semantics make careless cuts invalid | P2 retains table/opcodes, is 25.957% smaller, has large slow margin and selected multi-protocol positive wire evidence | Medium: kill current execution architecture, retain concept for one exact bounded redesign | Integrated specified design breaches area/state/semantic/physical gates; then kill competition entry |

These are empirical dispositions, not universal impossibility proofs. No
condition here authorizes further optimization in this completed study.
