# Unseen workload selection — committed after v2 freeze

Selection time: 2026-10-12 15:46:47 UTC. Frozen commit:
`b5675757c7a8405fd8dd40168a2370b3edd69a65`. No candidate was used to derive
the four operations or qualify the two training workloads.

| Candidate and primary source | Distinct from I²C | Distinct from Microwire | Direction changes | Timing complexity | Current I/O suitability | Triviality |
|---|---|---|---|---|---|---|
| [DS18B20 1-Wire initialization, Rev 6](https://www.analog.com/media/en/technical-documentation/data-sheets/ds18b20.pdf), pp. 3, 10, 15 | One wire; pulse duration establishes reset | No controller clock; delayed target pulse | Controller low → release → target low → release | Continuous reset qualification, release-relative delay, pulse width | Open-drain output plus passive copies of the same input wire | Narrow handshake, but tests a new temporal predicate |
| [PS/2, AVR313 Rev 1235B](https://www.microchip.com/content/dam/mchp/documents/OTH/ApplicationNotes/ApplicationNotes/doc1235.pdf), pp. 1–3 | Keyboard-generated clock and odd parity | Host inhibit and request-to-send | Host request followed by keyboard clock/ack | Clock generation, inhibition, 11-bit framing | Two open-drain wires fit; autonomous periodic clock ownership is a substantial demand | Not trivial; larger clock-generation question dominates transaction reuse |
| [ISO7816 T=0, AN4453 Rev 0](https://www.nxp.com/assets/documents/data/en/application-notes/AN4453.pdf), pp. 2–7 | Half-duplex asynchronous character exchange | Five-byte headers and procedure bytes | Procedure bytes select TX/RX continuation | ETU timing, parity error response, ATR and guard intervals | Clock/reset/data fit logically; voltage classes are outside the digital prototype | Substantive but conflates several missing/untested character-layer operations |
| [Microchip SWI description](https://developerhelp.microchip.com/xwiki/bin/view/applications/swi/) | Duration-coded single wire | Discovery, data and ninth-bit response | Byte-boundary handoffs | Pulse slots and reset/discovery timing | One open-drain wire fits | Ninth-bit ACK structure is close to the training I²C composition |

Select **bounded 1-Wire reset/presence target initialization**. This challenges
duration-qualified framing and release-relative waiting without adding a parity,
application-command or autonomous clock-generator requirement. Selection favors
a distinct semantic responsibility, not an expected pass. It is only an
initialization subset: no ROM command, search, temperature, parasite power,
analog thresholds, pullup RC model or data-slot support is claimed.

The independent oracle contract is committed in `third_workload.json` before any
configuration, oracle code or attempt. A valid reset is a **continuous** controller
low of at least 480 µs, followed by release. Presence must start 15–60 µs after
release, last 60–240 µs, and use only open-drain DQ ownership. The upper test bound
of 960 µs is an experimental bound, not a datasheet maximum. The source specifies
the legal timing; the campaign additionally requires silence for shorter and
interrupted non-reset pulses. This malformed-input robustness requirement is an
explicit independent test contract, not a claim about unspecified DS18B20 silicon
behavior. A one-microsecond high interruption must not be summed into a reset.

Use a 50 MHz digital core, one wired-AND DQ net observed by three passive input
routes, and one target output. Configuration and four constant FIFO tokens may
be preloaded before each bounded case. No host actions during an active frame,
external frame-reset sequencer, synthetic clock, or pulse-qualification wrapper
are permitted. Run the same configuration for all cases; system reset may clear
the fixture at the specified test point. Watchdog variants are separately labeled
safety tests. Verify all frozen hashes before and after the attempt. Do not change
candidate or relax the oracle after observing results.

If one isolated generic duration-qualification operation is missing, classify
PARTIAL and stop. If protocol-specific hardware is necessary, classify REJECTED
and stop. Only all-case logical success permits the physical flow.

Source PDFs were read through the browser. AN4453 downloaded byte hash is pinned;
the other two servers refused direct byte retrieval, so their byte hashes are
unavailable. The workload pins URLs, revisions/pages, derived timing inputs and
their canonical JSON hash. This distinction prevents claiming an unmeasured
document hash.
