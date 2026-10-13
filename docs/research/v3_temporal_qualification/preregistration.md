# Preregistered v3 temporal qualification

The [machine contract](preregistration.json) is the controlling preregistration.
It is committed after the architectural audit and before any model semantic
change. Later evidence records that commit and the LF-normalized SHA-256; neither
artifact may be edited to accommodate results.

The experiment adds one generic continuous-predicate responsibility through a
tagged WAIT operation. A separate sixteen-bit count and two lifecycle bits retain
the existing timer, frontend, ownership and bounded executor. Thresholds and
protocol timing belong to configuration. The experiment is falsifiable by exact
threshold/interruption races, lifecycle cancellation, regressions, a 10% mapped
area cap, and one independently selected post-freeze workload.

The original nine-case 1-Wire failure remains frozen evidence. An existing
response-capture composition can repair those cases but fails stronger startup,
restart and release-relative timing probes. It is a comparison baseline, not an
exhaustive proof that existing programs cannot express any temporal behavior.

Fresh review also found two existing model correspondence defects in synthetic
chains outside the qualified protocol profiles. The model will compare the
pre-edge TX bit in a validating WAIT and cancel same-cycle FIFO operations on
terminating HALT, preserving the original RTL behavior. These disclosed
corrections do not add another primitive family or change the historical frozen
sources; their counterexamples and regression tests are retained separately.

The cost limits are at most 24 added declared state bits, zero configuration
growth, and mapped area no greater than 213,813.96498 square micrometres under the
same pinned mapping as v2. A successful cost/logical gate permits a freeze, not a
claim of physical success. Future workload research starts only after that
freeze. Physical qualification retains 6x4/20ns and permits the initial run plus
two diagnosed flow-setting revisions without semantic edits.

A clean negative result ends architectural work. The final report and reached
demonstrations still explain exactly what was measured and where progress
stopped.
