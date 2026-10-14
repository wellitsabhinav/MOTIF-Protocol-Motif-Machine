# Bounded architecture falsification study

Question: is frozen MOTIF physically recoverable through flow repairs, or must
its execution architecture change or be abandoned for the competition?

This is a separate study authorized on 2026-10-14. The temporal qualification
campaign and its exhausted three-attempt budget remain historical evidence.
Production RTL, frozen manifests, configurations and acceptance gates are not
edited. Diagnostic variants are generated under ignored `build/kill_or_redesign/`.

The study starts at `9e4c500d1cc38c5b008babd245580d1b7d7e542d`, on
`development/kill-or-redesign-study`. No AGENTS.md was found in the checkout or
its ancestors. Baseline working tree was clean. No new GitHub workflow is
dispatched and no merge is authorized by this study.

## Fixed method and stopping rule

1. Authenticate local raw attempt-2 archive/reports; inspect at least twenty
   setup paths per corner and pre/post-layout stage, high-fanout nets and cones.
2. Reuse frozen v2/v3 mapped evidence and run matched diagnostic synthesis.
3. At most eight full-top forensic variants, each with a 180-second synthesis
   limit and 60-second STA limit. No repeated flow-knob searches.
4. Candidates: temporal elision; temporal state clamp; registered table output;
   registered predecode with one operation per cycle; action/FIFO register;
   and one combination only if isolated results justify it. Configuration
   validation caching may be tested if it limits the candidates.
5. A timing-only cut is not a semantic implementation. Explicitly audit lost
   events, temporal observations, atomic chain faults, host/FIFO ordering and
   pad release before calling a probe a rescue.
6. No new placement/routing unless a candidate has credible 20 ns synthesis
   timing at slow PVT, <=15% mapped area growth, and a concrete semantic route.
   Any physical sanity check would stop by global routing and be time-bounded.
7. End with exactly one decision. Missing physical proof cannot justify KEEP.
   A cheap cut that fails semantic feasibility cannot justify REDESIGN.

Measurements distinguish archived OpenROAD/OpenSTA results, new ideal-wire
OpenSTA analysis, graph depth, source inspection and engineering inference.
Large files stay ignored. Compact evidence includes hashes and reproduction
commands. Consult `decision.md` for the final classification.

## Reproduction

Run `python research/kill_or_redesign/analyze.py` for archived path/graph analysis.
Further synthesis commands and tool identities are recorded in `experiments.md`.

Final classification: **MOTIF_REDESIGN**. Read [decision.md](decision.md) for the
measured result and exact replacement; this does not qualify new RTL or GDS.
All eleven requested reports, compact evidence and four figures are present.
Run `python research/kill_or_redesign/report.py` to recreate the figures/tables
and `python research/kill_or_redesign/validate.py` to audit retained evidence.
