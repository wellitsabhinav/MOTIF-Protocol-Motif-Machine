# Frozen-vocabulary qualification

The initial manifest inventories the model and qualified RTL subset at its source
commit. `BYTE_EXCHANGE` is model-only in that baseline. Firing aliases are
suboperations, not additional independently configurable motifs.

Gate 1 promotes the existing I2C model machinery. A separate promoted manifest
will freeze that implementation and its fixed integration for subsequent reuse
tests. Neither inventory is regenerated in place. An architectural source change
after a reuse experiment begins invalidates that experiment.

```sh
python -m tools.frozen_manifest --historical
```

Hashes normalize CRLF to LF, matching the repository text convention. The
boundary includes all model and RTL sources, configuration and physical flow
inputs. Routing counts denote named logical connections; they do not imply a
programmable routing table or physical wire count.
