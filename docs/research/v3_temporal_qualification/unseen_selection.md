# Selected unseen workload: LIN break/sync entry

The post-freeze [independent matrix](unseen_candidate_matrix.md) ranks
`LIN_BREAK_SYNC_ENTRY` first under the prescribed lexicographic rule. It has
in-band asynchronous framing, no external data clock or CS, continuous dominant
LOW and a fixed UART-format sync pattern. Required recovery while awaiting a
byte provides a temporal falsification case beyond the repaired reset/presence
workload. This is a research interpretation of the ranking, not a predicted
implementation pass.

The immutable [machine-readable selection](../../../experiments/temporal_qualification/unseen/selected_workload.json)
fixes all timing bounds, malformed-input rules, 25 named cases and nine phase
sweep cases before any configuration is written. The target recognizes only a
fixed-rate, digitally normalized prefix and exposes a public FIFO acceptance
token. It does not transmit a LIN response or implement autobaud, PID, payload
or checksum handling.

[LIN 2.2A](https://www.lin-cia.org/fileadmin/microsites/lin-cia.org/resources/documents/LIN_2.2A.pdf),
sections 2.3.1.1–2.3.1.2, printed pp. 30–31, separates the master's minimum
13-bit break from the normal receiver's 11-local-bit detector. The contract
adopts the normal 11-bit detector at a fixed 20-kbit/s local rate. A 12-bit LOW
therefore tests receiver tolerance and is not an expected rejection. Checking
a full one-bit delimiter is optional; all qualification suffixes use a legal
60-µs delimiter, and no strict delimiter-rejection rule is added.

The source requires a fresh break/sync sequence to replace an incomplete frame
when the receiver expects a byte at a separated boundary. The selected recovery
case sends a first break/delimiter but no first sync, followed by a second
break/delimiter and 0x55. A separate case sends a whole wrong sync byte before
the fresh prefix. Neither imposes the optional case of a break superimposed
with an already transmitting data byte.

The independent oracle uses only resolved input samples, fixed bit periods,
lifecycle inputs and public FIFO observations. It decodes 8N1 LSB-first at
nominal centers and rejects a wrong value or LOW stop. No token may appear
before the stop cell begins; the token must be available by stop end plus two
bit periods. This finite public-interface latency is an experimental criterion,
rather than a LIN response deadline. One-cycle glitches are held on the core
grid and are sampled-continuity probes, without analog claims.

The official specification PDF was retrieved after freeze and hashes to
`e5e1a4ad3615721c519582914518730e8c49a41b527e82db77e7c3f8b8a18b98`.
It remains an ignored research artifact. No configuration exists at the time
of this selection commit. The frozen manifest remains
`71d5b07b5524fb6fa702357291eb35f52eccc5861111f7824b6fb9ead98a3047`.

A configuration counterexample may motivate configuration changes while this
oracle remains fixed. Any necessary semantic repair instead ends the campaign,
preserving the negative result and reached demonstrations. No candidate switch
or physical run is permitted to bypass that decision.
