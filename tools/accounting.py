import json
from collections import Counter
from pathlib import Path

from motif import Engine
from motif.protocols import i2c, spi, timed_stream, uart
from reference.sequential_spi import SequentialSPI
from tests.drivers import Wires
from tests.i2c_driver import Bus

# Explicit bounded encodings, not Python object sizes. These are model estimates;
# allocated RTL storage is measured separately after synthesis.
CONFIG_WIDTHS = {"frame": 2, "frame_pin": 3, "clock_pin": 3, "rx_pin": 3,
                 "tx_pin": 3, "sample": 1, "transmit": 1, "lsb_first": 1,
                 "period": 16, "validate_start": 1, "validate_stop": 1,
                 "open_drain": 8, "watchdog": 16, "fill": 8, "exchange": 1,
                 "address": 7, "ack_address": 1, "ack_data": 1}
STATE_WIDTHS = {"frontend": 26, "rx": 11, "tx": 12, "timer": 22,
                "pending_sample": 4, "validated_byte": 8, "active": 1,
                "guardian_age_trip": 17, "diagnostics": 9, "fifos": 78,
                "byte_exchange": 17}


def normalize(name):
    if name == "SHIFT_TX_LOAD":
        return "SHIFT_TX"
    if name in ("MATCH_FIRST_WORD", "OPEN_DRAIN_ACK", "OPEN_DRAIN_ACK_SAMPLE", "TURNAROUND", "STRETCH_UNTIL_READY"):
        return "BYTE_EXCHANGE"
    return name


def report():
    result = {"schema_version": 1, "kind": "bounded_model_encoding_estimate",
              "configuration_widths": CONFIG_WIDTHS, "state_widths": STATE_WIDTHS,
              "allocated_config_bits": sum(CONFIG_WIDTHS.values()),
              "allocated_state_bits": sum(STATE_WIDTHS.values()), "configurations": {}}
    recipes = {
        "spi_target": [("frame", "acquire/release"), ("rise", "rx"), ("fall", "tx"), ("rx_complete", "rx_fifo"), ("tx_complete", "tx_load"), ("acquire", "tx_load"), ("release", "guardian")],
        "uart_rx": [("fall", "acquire"), ("acquire", "timer"), ("timer_sample", "rx"), ("timer_stop", "rx_fifo/release"), ("release", "guardian")],
        "timed_stream": [("frame", "acquire/release"), ("acquire", "timer"), ("timer_sample", "rx"), ("rx_complete", "rx_fifo"), ("release", "guardian")],
        "i2c_target": [("sda_edge/scl_level", "acquire/release"), ("rise", "rx/exchange"), ("fall", "tx/exchange"), ("rx_complete", "exchange_decision"), ("fifo_ready", "stretch_release"), ("release", "guardian")],
    }
    for name, config in [("spi_target", spi.target()), ("uart_rx", uart.receiver(32)), ("timed_stream", timed_stream.receiver(16)), ("i2c_target", i2c.target())]:
        engine = Engine(config)
        if name == "i2c_target":
            wire = Bus(engine)
            wire.start()
            wire.write(0xA4)
            wire.write(85)
            engine.pop_rx()
            engine.push_tx(170)
            wire.start()
            wire.write(0xA5)
            assert wire.read() == 170
            wire.stop()
        else:
            wire = Wires(engine)
            if name == "spi_target":
                wire.spi(85, 170)
            elif name == "uart_rx":
                wire.uart(85)
            else:
                wire.hold(p0=1)
                wire.hold(4, p0=0)
                for bit in [0, 1] * 4:
                    wire.hold(16, p2=bit)
                wire.hold(p0=1)
        counts = Counter(normalize(firing) for row in wire.trace for firing in row["fires"])
        result["configurations"][name] = {
            "motif_firings": dict(sorted(counts.items())), "unique_motif_types": len(counts),
            "event_routes": recipes[name], "event_route_count": len(recipes[name]),
            "data_routes": ["rx->rx_fifo", "tx_fifo->tx", "constant->tx"] if name == "spi_target" else (["rx->first_word_match", "rx->rx_fifo", "tx_fifo->tx"] if name == "i2c_target" else ["rx->rx_fifo"]),
            "maximum_observed_firings_per_cycle": max(len(row["fires"]) for row in wire.trace),
            "qualified_event_to_rx_action_cycles": 0 if config.sample == "rising" else 1,
            "pin_to_action_cycles": "2..3 with input phase; timer adds one registered event cycle",
            "protocol_specific_hardware": ["bounded ninth-clock byte exchange"] if config.exchange else [],
        }
    reference = SequentialSPI(spi.target())
    Wires(reference).spi(85, 170)
    result["sequential_reference"] = {"coverage": "SPI target mode 0 only", "issued_operations_per_byte_frame": reference.issued,
                                      "maximum_operation_backlog": reference.max_backlog,
                                      "rx_enqueue_latency_after_terminal_shift_cycles": 1,
                                      "motif_rx_enqueue_latency_after_terminal_shift_cycles": 0,
                                      "throughput_at_test_spacing": "both complete identical frames",
                                      "program_storage_bits": 0,
                                      "limitation": "Fixed SPI reference; not equivalent multi-protocol programmability or RTL area evidence"}
    result["reuse"] = {motif: [name for name, cfg in result["configurations"].items() if motif in cfg["motif_firings"]]
                       for motif in sorted({key for cfg in result["configurations"].values() for key in cfg["motif_firings"]})}
    return result


if __name__ == "__main__":
    destination = Path("reports/motif_usage.json")
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(report(), indent=2) + "\n", encoding="utf-8")
    print(destination)
