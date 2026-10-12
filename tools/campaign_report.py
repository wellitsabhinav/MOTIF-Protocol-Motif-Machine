"""Complete evidence accounting without changing the frozen implementation."""
import argparse
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from motif import Engine
from motif.protocols import spi, uart, timed_stream
from tests.drivers import Wires
from tools.accounting import normalize
from tools.v2_inventory import accounting, verify


def report():
    frozen = verify()
    result = accounting()
    result['declared_state_widths'] = frozen['state_widths_declared']
    result['declared_total_register_bits'] = sum(frozen['state_widths_declared'].values())
    result['all_modes_allocate_global_configuration_bits'] = 1096
    legacy = json.loads(Path('reports/motif_usage.json').read_text())
    for name, config in [('spi_target', spi.target()), ('uart_rx', uart.receiver(32)), ('timed_stream', timed_stream.receiver(16))]:
        engine, driver = Engine(config), None
        driver = Wires(engine)
        if name == 'spi_target':
            assert driver.spi(85, 170) == 170
        elif name == 'uart_rx':
            driver.uart(85)
        else:
            driver.hold(p0=1); driver.hold(4, p0=0)
            for bit in [0, 1]*4:
                driver.hold(16, p2=bit)
            driver.hold(p0=1)
        assert engine.pop_rx() == 85
        counts = Counter(f for row in driver.trace for f in {normalize(n) for n in row['fires']})
        old = legacy['configurations'][name]
        if dict(counts) != old['motif_firings']:
            raise AssertionError('Inherited recipe firing behavior changed: '+name)
        fields = ['frame', 'frame_pin', 'frame_active_high', 'rx_pin', 'sample', 'lsb_first', 'transmit', 'watchdog']
        if name == 'spi_target':
            fields += ['clock_pin', 'tx_pin', 'fill', 'open_drain']
            data = ['pin->RX', 'RX_terminal->RX_FIFO', 'TX_FIFO->TX', 'fill_constant->TX', 'TX_bit->data_request', 'requests/ownership->guardian']
        else:
            fields += ['period', 'validate_start', 'validate_stop']
            data = ['pin->timer', 'timer_bit->RX', 'requests/ownership->guardian']
            data += ['RX_terminal->validated_byte', 'validated_byte->RX_FIFO'] if name == 'uart_rx' else ['RX_terminal->RX_FIFO']
        result['protocols'][name] = {
            'configuration': asdict(config), 'primitive_firings_per_example_frame': dict(counts),
            'example_frame_count': 1, 'active_configuration_fields': sorted(fields),
            'event_route_groups': old['event_routes'], 'event_route_group_count': len(old['event_routes']),
            'data_route_groups': data, 'data_route_group_count': len(data),
            'maximum_primitive_types_per_cycle': old['maximum_observed_firings_per_cycle'],
            'active_transaction_state_fields': [], 'active_transaction_semantic_dependency_bits': 0,
            'receive_semantically_used_bits': 11, 'receive_globally_allocated_bits': 21,
            'state_groups_referenced': ['frontend', 'receive', 'watchdog', 'fifos', 'core_lifecycle_provenance_diagnostics']+(['transmit'] if name == 'spi_target' else ['timer']),
            'activity_scope': 'Referenced register groups are dependency groups, not switching/power. The watchdog is optional; allocated state and table configuration remain global even when unused. Example firing counts reproduce the historical recipe in the current model; existing RTL regressions independently retain these users.',
            'new_rtl_required_for_protocol': 0, 'host_route_groups': ['host->TX_FIFO', 'RX_FIFO->host']}
    for name in ('i2c_target', 'microwire_read'):
        p = result['protocols'][name]
        p['active_transaction_semantic_dependency_bits'] = 27 if name == 'i2c_target' else 25
        p['transaction_globally_allocated_bits'] = 28
        p['state_groups_referenced'] = ['frontend', 'receive', 'transmit', 'watchdog', 'fifos', 'transaction', 'core_lifecycle_provenance_diagnostics']+(['timer'] if name == 'i2c_target' else [])
        p['host_route_groups'] = ['host->TX_FIFO', 'RX_FIFO->host']
    result['failed_unseen_attempt'] = {'validated_user': False, 'new_rtl': 0, 'classification': 'MOTIF_V2_UNSEEN_PROTOCOL_GENERALIZATION_PARTIAL', 'evidence': 'third_result.json'}
    result['routing_count_scope'] = 'Named actor-level interface dependencies, not physical wires or a crossbar inventory. Framing, host routes and support machinery are listed separately from table-entry routes. Possible chained alternate dependencies are included for training table graphs.'
    result['protocol_specific_support'] = {'new_transaction_modules': 0, 'new_transaction_lines': 0, 'inherited_protocol_shaped_integration_modules': ['motif_core.sv'], 'integration_responsibilities': ['clock-level-qualified data framing', 'own-clock/data timing provenance', 'clock-edge progress policy'], 'diagnostic_reference_modules': ['motif_sequential_shift.sv', 'motif_reference_top.sv']}
    verify()
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('build/exchange_decomposition/final_accounting.json'))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report(), indent=2)+'\n')
    print(args.output)
