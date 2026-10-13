# Post-freeze unseen temporal candidate research

Research only; no workload has been selected and no configuration has been
written. The parent reviewer must select exactly one candidate in a later commit
before configuration or implementation work. Scores below are explicit research
judgments, not measured implementation results.

## Frozen boundary and provenance

- Freeze commit: `638c2ee4e7c9f53c64e6f660331747e5a79b570d`.
- Manifest: `experiments/temporal_qualification/frozen_v3_manifest.json`.
- Manifest SHA-256 after CRLF-to-LF normalization:
  `71d5b07b5524fb6fa702357291eb35f52eccc5861111f7824b6fb9ead98a3047`.
- Research began after that freeze. Entry checks found that HEAD and a clean
  working tree. The first URL-discovery queries followed these entry checks;
  the complete `tools.v3_inventory.verify()` check and manifest digest were
  then run before detailed source extraction. They passed. This records the
  order accurately rather than claiming the full checker preceded URL discovery.
- Only this new document and `experiments/temporal_qualification/unseen/research.json`
  are authored by the researcher. Existing RTL, model, compiler, frontend,
  configuration, tests, oracles, reports and manifests are not edited.
- Public interface and preregistration documents were consulted only to assess
  pin observability and bounded execution. Protocol requirements and proposed
  oracle rules below come from the listed external primary sources.

## Eligibility, scoring and ordering

An eligible candidate needs observable electrical input or output behavior,
accessible numeric timing requirements, and an oracle that can be independently
bounded using resolved pins and public host observations. Eligibility does **not**
mean the frozen machine can implement it. In particular, an upper-bound
requirement is not discarded merely because the machine has no upper-bound
primitive.

The prescribed order is lexicographic: descending structural independence `I`,
then descending temporal falsification value `F`, then ascending bounded scope
`S`, then the exact ASCII workload name. There is no weighted sum.

The ordinal structural rubric compares the actual bounded electrical task with
I2C's clock/data and shared ACK ownership and Microwire's clock/CS/data exchange:

| I | Structural category |
|---|---|
| 4 | Asynchronous serial entry is entirely in-band; no external bit clock, CS, or shared response/ACK phase is needed. |
| 3 | Timing is independently driven, but initialization retains either shared open-drain request/response ownership or an external reference clock plus reset control. |
| 2 | Two bidirectional open-drain clock/data lines and externally observable clocked byte activity retain substantial clocked-bus structure. |
| 1 | Entry relies directly on address/ACK or CS/command sequencing already represented by the qualified buses. |

`F=4` means multiple independent temporal boundaries and a serial recognition,
recovery, or response-window consequence; `F=3` means one main continuity gate
plus a smaller follow-on boundary consequence; `F=2` means a timing gate with
little additional consequence; `F=1` means mostly ordinary bit shifting. This
is a falsification opportunity score, not a prediction of success. The LIN
delimiter's optional receiver check is not counted as a mandatory second
continuity requirement.

`S=1` is one interval and one decision; `S=2` is a few intervals and at most one
byte, or one response pulse; `S=3` adds two-line transfer/ownership and a complete
clocked byte; `S=4` adds reference-clock accounting, reset control and an ATR
character. Scope measures the smallest meaningful sourced task, not estimated
instruction count. No score rewards known machine expressibility.

## Candidate matrix

Primary-source keys link to full documents and exact sections below. The
timing facts are separated from oracle proposals and implementation inferences.

| Rank | Exact workload name | Primary source and bounded task | I / F / S | Ownership, topology and clock assumptions | Frontend observability, oracle and falsification value |
|---|---|---|---|---|---|
| 1 | `LIN_BREAK_SYNC_ENTRY` | [L], recognize the break/sync prefix at a declared fixed nominal rate. Add separated-field restart probes without claiming a complete LIN node. | 4 / 4 / 2 | Master supplies one asynchronous dominant/recessive receive signal. The bounded prefix is receive-only; the target never drives the LIN data signal. A transceiver-normalized logic input is assumed. | Long LOW continuity and UART-format sync are visible on one pin. Resolved input plus host-readable acceptance bytes give a finite oracle. Split LOW runs, ordinary zero bytes, false sync and recovery can expose acceptance based on accumulated rather than continuous duration. Full automatic baud measurement and PID/data/checksum handling are outside this prefix. |
| 2 | `UART_BREAK_GAP_ENTRY` | [U], a device-specific UART BREAK and return-to-mark entry followed by one fixed 8N1 character. This is not a universal UART-gap standard. | 4 / 3 / 2 | Independent receive line, receive-only target; local baud reference. [U]'s end-of-break rule uses the device's X1 reference, not baud bit periods. | Input LOW/mark and the following byte are visible. A direct serial decoder plus host FIFO reads can bound acceptance. A local reference must be declared for the two-X1-edge rule; mapping that rule to arbitrary core cycles without documenting the reference would change the workload. Less independent temporal content than LIN's specified frame-entry/recovery sequence. |
| 3 | `MICROCHIP_AT21CS01_RESET_DISCOVERY` | [S], inactive-device high-speed reset, recovery and discovery ACK only. No EEPROM command emulation. | 3 / 4 / 2 | One shared open-drain SI/O line; host begins both reset and request; device owns an overlapping LOW response. Internal timing and external pull-up rise time are separate assumptions. | Reset/recovery/request transitions and target drive/release are digital and observable. An oracle can measure response onset, duration, host sample-window LOW, and release against the request origin. Power harvesting, charge depletion and analog rise/hysteresis are excluded; below-minimum input behavior is not automatically specified as silence. Its shared response ownership resembles I2C and its reset/presence shape resembles the training 1-Wire task. |
| 4 | `ISO7816_WARM_RESET_ATR_PREFIX` | [I], stable-powered warm reset and the first ATR character, not cold power sequencing or a full ATR/parser. | 3 / 4 / 4 | Reader drives RST and reference CLK; card owns I/O for ATR. CLK is a time reference rather than a data strobe. Fixed legal frequency and digital voltage normalization must be declared. | RST, CLK and I/O can be sampled separately. An oracle counts actual reference-clock edges, then checks the ATR deadline and first character on I/O. It must not infer elapsed card clocks solely from the core clock. Longer duration, parity/convention and three signals make this larger. The source's cold-reset inequality is inconsistent with its warm-reset wording; use the explicit warm-reset contract rather than silently repairing the cold text. |
| 5 | `PS2_INHIBIT_RELEASE_ENTRY` | [P], inhibit, continuous idle-clock permission and one fixed device-to-host byte. [P2] supports a request-to-send variant, but does not supply the often-quoted numeric host-inhibit minimum. | 2 / 3 / 3 | Shared open-drain CLK/DATA; device supplies byte clocks, host can inhibit by holding CLK LOW. Device must release ownership when inhibited. | Both resolved lines and target OEs can be observed. An oracle can require continuous idle CLK before the first transmit transition and measure an eleven-bit byte. The two-line structure overlaps I2C strongly, though device clock ownership differs. The request variant must not import an unsupported 100-us bound from tutorials. |

No exact score tie reaches the workload-name fallback. LIN outranks UART on `F`;
SWI outranks ISO7816 on smaller `S`; structural category outranks all later
criteria. The matrix does not authorize replacing a selected candidate after an
implementation failure.

## Primary-source register and timing facts

All substantive requirements below are from protocol-owner or manufacturer
documents. Secondary tutorials and community/forum answers were not used as
requirements.

**[L] LIN Consortium, LIN Specification Package 2.2A, 31 December 2010.**
[Official LIN-CiA specification](https://www.lin-cia.org/fileadmin/microsites/lin-cia.org/resources/documents/LIN_2.2A.pdf),
printed pp. 29–31, sections 2.3.1, 2.3.1.1 and 2.3.1.2; clock assumptions in
section 6.3, printed p. 113; nominal rate range 1–20 kbit/s in section 9.2.1.3,
printed p. 177. The official indexed source was readable; direct
PDF opening returned an error in the browsing tool.

| Symbol | Source fact |
|---|---|
| `B` | Nominal bit time. Byte framing: LOW start, eight bits LSB first, HIGH stop. |
| `G` | Master-generated break LOW is at least `13 B`; generated delimiter HIGH at least `B`. |
| `D` | Normal slave detector uses `11` local bit times; a precise-clock slave may instead use `9.5` nominal bit times. |
| `Q` | Sync byte is `0x55`. |
| `R` | Separated break/sync must be recognized even when a byte is expected; a new sequence aborts the old transfer. Overlap with a data byte is optional. |

A receiver need not enforce the full delimiter duration. Consequently a strict
delimiter rejection policy is an explicit additional recognizer contract, not a
mandatory LIN test. The fixed-rate subset does not assert automatic baud recovery
over the source's unsynchronized clock tolerance.

**[U] Texas Instruments, TL28L92 data sheet SLLS890C, April 2024 revision.**
[Official data sheet](https://www.ti.com/lit/ds/symlink/tl28l92.pdf),
section 5.3.7.2, printed p. 27. A break is LOW throughout the character, including
stop, and produces a zero byte and break status in that device. Break ends after
HIGH is recognized on two X1 clock edges; a phase-independent host pulse may
need one X1 period or three edges. This source does not define a general
inter-message UART gap. A MOTIF oracle would test only the documented electrical
entry behavior and a declared acceptance interface, not require TL28L92-specific
register emulation.

**[S] Microchip, AT21CS01/AT21CS11 data sheet DS20005857I, May 2026 revision.**
[Official current PDF](https://ww1.microchip.com/downloads/aemDocuments/documents/MPD/ProductDocuments/DataSheets/AT21CS01-AT21CS11-1-Kbit-Serial-EEPROM-Data-Sheet-DS20005857.pdf),
section 3.5.1, printed p. 10; sections 4.1.1.1–4.1.1.2 and Figure 4-1,
printed pp. 12–13; SI/O ownership in section 1.1, printed p. 5.

| Parameter | High-speed bound |
|---|---|
| Reset LOW, inactive device | `tRESET >= 96 us` |
| Discharge LOW, busy write | `tDSCHG >= 150 us`; busy-write scope is excluded |
| Recovery HIGH | `tRRT >= 8 us` |
| Host discovery request | `1 us <= tDRR <= 2 us - tPUP` |
| Device LOW ACK, measured from request initiation | `8 us <= tDACK <= 24 us` |
| Host sampling instant | `2 us <= tMSDR <= 6 us` |
| HIGH before the subsequent Start | `tHTSS >= 150 us` |

After reset the device uses high speed. `tPUP` is application dependent. Revision
A instead lists a 48-us high-speed reset bound; it must not be mixed into the
revision-I workload. The current PDF table and corresponding official HTML
table agree on the revision-I bounds.

**[I] SEALSQ, AT90SCRXXX/AT90SCR400 technical data sheet TPR0630E, 18 January 2023.**
[Official manufacturer PDF](https://www.sealsq.com/hubfs/SCR%20400.pdf),
section 15.5.7 and Figure 15-12, printed p. 159: warm reset holds RST LOW for at
least 400 card clocks and returns RST HIGH; ATR must appear within 40,000 clocks.
Section 15.6.1, p. 160, gives the ISO reference range as 1–5 MHz. The ETU definition
and reset defaults are in pp. 150 and 172 (`F=372`, `D=1`). Section 15.5.7's
cold-reset text on p. 158 writes `tb < 400`, while its warm-reset text explicitly
requires at least 400. The bounded candidate uses the latter. It must record
whether endpoint equality and any minimum post-release ATR delay are guaranteed
by the adopted source; this excerpt alone does not justify an invented strict
early-ATR rejection rule.

**[P] Microchip, ECE1117 data sheet DS00001860E, 2020 revision.**
[Official data sheet](https://ww1.microchip.com/downloads/aemDocuments/documents/CPG/ProductDocuments/DataSheets/ECE1117-Data-Sheet-DS00001860E.pdf),
sections 10 and 10.1.1, printed p. 61, and Table 10-2, p. 62. CLK/DATA are
bidirectional open drain, device-clocked, with eleven serial bits. Bit cells are
60–100 us. Transmission requires CLK continuously HIGH for at least 50 us.

**[P2] Cypress/Infineon, PS2D User Module data sheet 001-13681 Rev. *E.**
[Official data sheet](https://www.infineon.com/assets/row/public/documents/30/396/infineon-ps2d-001-13681-software-module-datasheets-en.pdf),
printed p. 3, Figure 3: on inhibit, device transfer stops and both lines are
released; host DATA LOW followed by CLK release requests transmission to the
device. This document supplies transfer ownership, not a numeric 100-us
inhibit requirement.

## Top-ranked candidate: independent oracle contract proposals

These are reviewable research proposals for `LIN_BREAK_SYNC_ENTRY`. They do not
choose a configuration. The parent must commit the adopted profile, acceptance
interface and required case set before implementation.

### Electrical and scope contract

Use the receive-side dominant/recessive logic from a LIN transceiver: LOW is
dominant, HIGH recessive. The harness supplies that actual serial line directly;
it may not generate hidden frame strobes or bit clocks from protocol decoding.
Unused pads can have static levels. Host SPI reads are the public observation
channel for recognition, not protocol-generated stimuli.

The smallest result is one host-readable `0x55` acceptance token for each
recognized prefix, with zero target OE on the receive line throughout. An
acceptance token is an experiment interface choice, not a LIN-prescribed on-wire
response. The byte cannot be emitted merely because a long LOW occurred; it
requires the subsequent byte's sampled framing and value, including its stop
sample. The whole stop interval need not finish before acceptance. A pin-and-host oracle
can therefore falsify missing, early, duplicate or spurious acceptance without
consulting instruction PCs, temporal counters, internal completion flags or the
configuration graph. A pass qualifies this prefix recognizer, not a full LIN
publisher, physical transceiver, autobaud implementation or fabricated device.

Two possible source-consistent receiver threshold profiles need to remain
distinct: normal local-clock `D`, or the permitted precise-clock variant. The
normal profile is the straightforward basis for the deterministic examples
below; this statement does not select it for implementation. Do not classify a
LOW between the detector threshold and the master generation minimum as a
mandatory receiver rejection.

### Independent measurement rules

1. Build an oracle solely from externally supplied resolved-line samples, their
   timestamps, and externally observed FIFO tokens/host reads. Find maximal
   uninterrupted LOW runs directly; never add durations across an intervening
   sampled HIGH.
2. Freeze the source-derived bit period and detector profile before running the
   implementation. Locate the release and next start transition from the line,
   then decode the byte at independently computed centers. Check start, value
   and stop from those samples. Do not reuse the MOTIF decoder or timer helper.
3. For exact one-core-cycle threshold races, explicitly define the sampled
   contract: edge-aligned held levels, known two-stage frontend settling, and
   a comparison domain containing the actual consecutive observable samples.
   Also include margin-separated physical durations. A one-cycle endpoint test
   is a declared digital contract probe, not a claim about analog LIN timing.
4. Bound each case by the stimulus schedule plus a preregistered observation
   drain interval. Measure any implementation latency separately. The protocol
   does not prescribe a FIFO response deadline; a finite host drain deadline is
   an experiment criterion and must be fixed before observing results.
5. Check both acceptance data/count and receive-line OE. Internal traces may
   explain a failure afterward; they may not define expected acceptance.

### Deterministic stimulus families

For concreteness, an illustrative wire instance can use `B=50 us` and the normal
detector profile; `20 ns` is the supplied core period. These values describe
research vectors only. They are not host settings, program entries or a chosen
configuration. Each sync byte is exactly the sequence
`LOW start; HIGH, LOW, HIGH, LOW, HIGH, LOW, HIGH, LOW; HIGH stop`, each cell `B`.

| Family | Deterministic wire schedule | Required oracle disposition for the adopted normal detector profile |
|---|---|---|
| Legal minimum generation | LOW `650 us`, HIGH `60 us`, correctly framed sync | Exactly one acceptance after independent stop validation; no receive-line drive. |
| Longer legal break | LOW `800 us`, same suffix | Same acceptance, with no duplicate token during the extra LOW. |
| Detector boundary | LOW `550 us - 20 ns`, `550 us`, `550 us + 20 ns`, each followed by the same suffix | Below/at/above the declared sampled detector boundary; wire/sampling endpoint convention must be preregistered. Only the below case is a rejection probe. |
| Receiver tolerance | LOW `600 us`, same suffix | Detectable prefix in the adopted detector profile. Label the master waveform nonconforming; do not use it as a false-positive test. |
| Split false break | LOW `300 us`, HIGH `1 us`, LOW `300 us`, then delimiter and sync | No prefix acceptance: neither uninterrupted LOW reaches the detector threshold. |
| Several interruptions | LOW `200 us`, HIGH `1 us`, LOW `200 us`, HIGH `2 us`, LOW `200 us`, suffix | No acceptance even though total LOW exceeds the threshold. |
| Ordinary zero byte | An ordinary 8N1 zero byte, HIGH `60 us`, sync without a break | No acceptance. This directly distinguishes a serial byte from initialization. |
| Wrong sync / bad stop | Legal break and delimiter, then separately `0x54`, `0xAA`, or sync with LOW stop | No `0x55` acceptance for those bounded-prefix predicates. Rejecting a non-sync value follows the adopted recognizer's definition; no unspecified LIN error response is invented. |
| Startup LOW interruption | Enable after frontend settling; incomplete LOW, observable HIGH, fresh legal break and sync | Only the later complete prefix accepts; no stale startup history. |
| Fresh prefix after failure | Split false break and suffix; HIGH gap; fresh legal break and sync | No token from the first attempt, exactly one from the later complete attempt. |
| Pending-sync separated recovery | First legal break LOW `650 us`, HIGH `60 us`, with no first sync transmitted; second legal break LOW `650 us`, HIGH `60 us`, then framed sync | Exactly one token for the second prefix after independent stop validation. The old pending header is abandoned. This is the source-required byte-expected boundary case `R`; a receiver that only rescans after a successfully completed prefix has not satisfied it. |
| Pending-sync stale-header control | First legal break LOW `650 us`, HIGH `60 us`; ordinary framed `0x00`; HIGH gap; sync without a fresh break | No acceptance under the bounded prefix definition. This distinguishes recovery via a real second break from retaining the first break indefinitely after a wrong sync byte. |
| Back-to-back prefixes | Two complete legal prefixes separated by a declared HIGH gap | Exactly two acceptance tokens; no old completion leaks into the next prefix. |

The pending-sync recovery case instantiates the required clause in section
2.3.1.2, printed p. 30, for a receiver expecting a byte field. The HIGH delimiter
ends the first break, and no first sync/data byte starts before the fresh second
break. Therefore the second break is not physically superimposed with any
already transmitting byte. A UART decoder internally treating its first LOW
edge as a start bit does not change that electrical distinction. The optional
overlap qualification continued on printed p. 31 concerns a break imposed during
an actual data-byte transmission. This interpretation follows the source's
explicit byte-expected condition and does not add that optional mid-byte case.

Short delimiters are diagnostic unless the parent explicitly adopts a strict
extra delimiter-recognition contract. Likewise, an excessively long break or
header must not be rejected merely by inventing an upper bound for this receiver.
Upper bounds in other candidate oracles are retained where their sources require
them. The absence of machine upper-bound support is not used to redefine any
source requirement.

## Implementation feasibility limits, kept separate from ranking

The frozen temporal WAIT counts 1–65,535 core observations, with registered
completion consumed later, and exposes one configured RX level at a time.
At 50 MHz, a single maximum threshold spans about 1.31 ms. Longer real intervals,
external-clock counts, simultaneous multi-line conditions and continuous
background detection can require composition or can fail. A source interval
must not be shortened to fit, a reference CLK must not be replaced silently by
core elapsed time, and a response window must not be dropped.

For the illustrative LIN vectors the LOW and bit periods are within a single
count range. That is only a representability observation. In particular,
mandatory separated-field recovery can expose a real limitation in a machine
that observes only its active entry. The research has not established a
configuration, table-size fit, or logical pass.

## Exclusion discipline

All five ranked bounded tasks meet the three eligibility gates. Narrow variants
that would require analog supply charge depletion, automotive bus voltage
compliance, card-contact power sequencing, an inaccessible timing contract, or
invisible internal status alone are excluded from their eligible digital scopes.
The generic UART-gap variant and a numeric PS/2 100-us request variant are not
assigned invented requirements. A broad Modbus RTU frame-gap task was screened
as additional context, but is outside this serial-initialization candidate pool:
it adds whole-message CRC/address validation and character-completion silence
accounting ([Modbus Organization serial-line guide V1.02](https://www.modbus.org/docs/Modbus_over_serial_line_V1_02.pdf),
section 2.5.1.1, printed pp. 13–14). It is not excluded because upper-bound checks
would be difficult.

## Research-end boundary check

After writing these new research artifacts, `tools.v3_inventory.verify()` and
the LF-normalized manifest digest check passed again. JSON parsing and the
declared lexicographic ranking also passed. The machine-readable receipt in
`research.json` records the result. HEAD at the receipt is the parent's final-doc
commit `f435c820449979ab1831e70bed230b2139842bae`, with the frozen semantic
inventory unchanged. Other agents may change nonprotected
documentation concurrently; such work is not authored or certified by this
researcher. A passing semantic check, rather than a claim of an end-of-research
clean tree, is the preservation criterion.
