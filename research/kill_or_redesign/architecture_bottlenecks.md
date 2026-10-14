# Architectural bottlenecks

Actual transaction execution is in `src/motif_transaction.sv:145–295`; integration
and FIFO capture are in `src/motif_core.sv:75–125`. Line references here are
source locations, not gate-stage attributions. [Figure 1](figures/01_current_path.svg)
shows the documented dependency.

`pc_o` selects a 64-bit word from 1,024 configuration bits. Opcode/event/operands
select predicates and mutate working `pending_next`, RX/count, role/acceptance,
drive/hold and successor PC. `pc_next` then selects another complete word in the
**same cycle**, up to four distinct entries. Lookahead additionally reads the
successor trigger and temporal tag/opcode. Completion/fault/termination gates
all accumulated actions before the FIFO and shared actors commit at the edge.

| Structure | Source evidence | Quantitative consequence |
|---|---|---|
| Dependent indirect reads | `program_i[pc_next*64 +: 64]` inside four-iteration loop | Four serial word/action dependencies; lookahead adds reads, not necessarily distinct physical ports after sharing |
| Repeated decode | opcode/event/field functions invoked each iteration | Transaction 5,517 cells; P2 one-operation version 1,271 |
| Priority/reconvergence | visited/conflict checks, advance/chain/temporal deferral, final fatal cancellation | PC path 64 non-buffer levels even after fixed buffering |
| Variable data selection | field-bit selector; RX mask, variable shift/length, role/data pin indices | Expensive mux/comparison cones; mapped mux graph maxima 21 in matched v3 |
| Global qualification | wrapper's full-table validation → enable; watchdog → inhibit → run/clear | Worst full and register paths cross global control into distant FIFO endpoints |
| Distant final side effects | executor actions feed both RX/TX FIFO and output/guardian logic | RX FIFO critical endpoints; TX FIFO cones also deep |
| Poor boundaries | No instruction register or atomic intent register between these responsibilities | P1 barely improves; P2 structurally cuts the dependency |

The graph is acyclic between registers. Working-variable dependencies are not
literal combinational feedback. Some decoding can be shared, but sharing a
predicate does not remove four dependent control decisions. The table is wide,
yet storage alone is not fatal: P2 retains it and substantially improves timing.
Temporal state adds 18 bits and worsens matched area, but its removal leaves the
same architectural problem. Generic programmability is not disproved.
