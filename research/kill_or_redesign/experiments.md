# Experiment ledger

The pre-probe budget is in README.md, committed at `2f02976`. Eight full-top
variants are permitted; no physical workflow dispatch is permitted without the
positive synthesis/semantic gate. Changes to analysis/report export syntax are
tool compatibility fixes, not optimization trials.

| ID | Intervention | Purpose | Semantic status before measurement |
|---|---|---|---|
| A v2 | Frozen `490a50c3...` | Control for the temporal extension | Official baseline |
| B v3 | Frozen RTL, current checkout | Primary baseline | Official baseline |
| C elided | Temporal execution and acquisition elided; host validation retained | Test H6 | Forensic only; temporal protocols absent |
| D state_clamp | Keep temporal decode/control; clamp count/started/done | Separate state from decode | Forensic only; cannot qualify temporal protocols |
| P1 | Register first table read; retain remaining three chain reads | Isolate initial table mux | Timing cut; lifecycle cache alignment needs repair |
| P2 | Registered 66-bit predecode; one operation per cycle | Lower bound for serial execution | Timing cut; atomic chain and event semantics need audit |
| P3 | Register RX FIFO push/data | Test one distant endpoint boundary | Timing cut; FIFO snapshot/reservation ordering needs audit |
| P4 | Move reset/run/clear masking after the four-action computation | Localize control distribution | Intended exact transition/port equivalence; verify independently |

P4 was selected before its implementation, after buffered v3 STA showed the
worst full-top path starts at `ena`, and the worst register-launched path starts
at a watchdog configuration bit. Both run through the interpreter to FIFO
capture. This directly tests H4 without introducing event buffering or changing
programmability. It occupies the eighth variant; cached-validation/P2
combinations are not run. No broad combination search is allowed.

## Tool and environment method

Native Yosys 0.30+48 and the repository's `.tools/abc.exe` reproduce the frozen
v2/v3 mapped area exactly. All variants use the same typical Liberty mapping.
Flattening is performed **after** mapping. A deterministic fanout-eight tree of
`sg13cmos5l_buf_4` is inserted into the flat netlist for a second, optimistic
timing measurement; raw mapping is retained separately. This changes no Boolean
function. It is neither placement-aware nor a production buffering recipe.

An OpenSTA 2.0.17 Ubuntu archive was unpacked under ignored build output and
executed in the existing `PACT-OpenSTA-Review420` WSL environment. Ubuntu-24.04's
registered disk is unavailable; no host/WSL configuration was changed. Older
OpenSTA requires space-free script/Liberty basenames, simple assignment LHS,
`-group_count`/`-endpoint_count` and older report field names. Earlier reports
with missing libraries or unsupported syntax were rejected, never measurements.
The library's default wire-load model is explicitly replaced by `Zero`.

Constraints match the archived SDC: 20 ns, 0.25 ns uncertainty, 0.15 ns clock
transition, 4 ns input/output budgets, buf_4 input driving, 0.006 pF output load,
late/early derates 1.05/0.95. Clock remains ideal and wires have zero RC. No
false paths, reset/enable exceptions, multicycle exceptions or relaxed period
are added. Typical and slow PVT are analyzed. Register-launched paths are also
reported separately; they do not replace full-top worst slack.

Commands:

```text
python research/kill_or_redesign/analyze.py
python research/kill_or_redesign/tournament.py synth v3 v2 elided state_clamp
python research/kill_or_redesign/tournament.py synth p1 p2 p3
python research/kill_or_redesign/tournament.py synth p4
python research/kill_or_redesign/tournament.py sta v3 v2 elided state_clamp p1 p2 p3 p4
```

Mapping limit: 180 seconds per variant. STA limit: 60 seconds per invocation.
Full scripts, generated diagnostic patches, netlists and logs remain ignored.
`evidence/*_mapping.json`, `*_timing.json`, `*_graph.json` and `*_paths.json`
record identities and selected measurements. Final results and gate decisions
are summarized in decision.md. `tool_identity.json` binds the executable/package
and Liberty hashes; `validation.json` records buffer-only connectivity and report
arithmetic checks. No tools or package archives are committed.

## Final execution and stop

Six mappings completed: v3 137.032 s, P1 140.750 s, P2 70.141 s; other exact
durations are in their mapping receipts. P3 and P4 each hit 180 seconds while
mapping tasks overlapped. Contention may contribute to those limits. Their
captured partial stdout was not persisted by the original timeout handler;
receipts explicitly record that missing log. The handler now preserves partial
output for reproduction. Neither timeout supplies area, timing or congestion
evidence. They were not retried. Eight distinct variants were attempted.

P4's independent arbitrary-state/table/control combinational transition miter
proved all observable combinational outputs and 46 next-state bits equivalent
in 9.172 seconds. `python research/kill_or_redesign/verify_probe.py` reproduces
that proof. Sequential clear/acquisition priorities are unchanged.

`python research/kill_or_redesign/semantic_sanity.py` reproduces P2's bounded
representability checks. Nominal I²C fixed resolved-wire replay has 8 differing
visible cycles; it is not a failed closed-loop protocol oracle. A separate live
wired-AND controller passes 4,154 cycles with correct ACK/data/release. Three
1-Wire cases use live target feedback and the unchanged wire oracle; nominal
LIN uses the unchanged independent prefix oracle. Microwire checks controller
sample indices against A55A. SPI/UART/timed stream use their unchanged fixed
actor paths. Generic atomic termination produces a permanent negative: a byte
leaks into RX FIFO in P2. No acceptance expectation was weakened.

Additional STA launch selections isolate operational/PC paths without changing
full-top constraints: continuing PC → RX FIFO still has −4.285170 ns slow slack.
Their twenty-path receipts include exact report hashes. Full-top results remain
the tournament acceptance numbers.

No placement, CTS, global-route or full-GDS job was launched. P2 lacks atomic
semantics, while P3/P4 lack completed mapping. The physical sanity gate therefore
does not authorize a new run. The classification is MOTIF_REDESIGN; this study
stops with a specified replacement and measured kernel, not a production change.
