# MOTIF — Protocol Motif Machine

MOTIF explores compound operations for programmable serial I/O. Bounded motifs
combine sampling, shifting, counting, framing, and event generation. An
independent pad guardian controls final output enables.

```mermaid
flowchart LR
  Pins --> Frontend[Event frontend]
  Config[Configuration] --> Executor[Compound motifs]
  Frontend --> Executor
  FIFO[Byte FIFOs] <--> Executor
  Executor --> Guardian[Pad guardian]
  Frontend --> Guardian
  Guardian --> Pads
```

Current status: SPI mode-0 target, UART 8N1 receive and seven-bit I²C target
behaviors are tested in the executable model. I²C covers repeated START,
ACK/NACK, turnaround, clock stretching and recovery. RTL and physical results
remain pending; model reuse does not establish implementation cost.

```sh
python -m pip install -e '.[test]'
python -m pytest -q
```

`motif/` contains the model and configuration helpers; `tests/` contains wire-level
and adversarial checks; `docs/` defines behavior and evidence. See
[architecture](docs/architecture.md), [execution semantics](docs/execution-model.md),
[protocol support](docs/protocol-support.md), and [verification](docs/verification.md).

License: Apache-2.0. See LICENSE.
