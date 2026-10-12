"""Unseen controller/oracle outside the immutable v2 implementation boundary."""
import hashlib
import json
import subprocess
from dataclasses import asdict, replace
from pathlib import Path

from motif.transaction import configuration
from tools.exchange_decomposition import Recorder, compare_rtl, digest, summary
from tools.v2_inventory import verify, sha

ROOT = Path('experiments/exchange_decomposition')
SELECTION_COMMIT = '4959350'


def pulse_intervals(levels):
    """Half-open intervals of asserted target-low ownership."""
    pulses, start = [], None
    for i, level in enumerate([*levels, False]):
        if level and start is None:
            start = i
        if not level and start is not None:
            pulses.append((start, i))
            start = None
    return pulses


def oracle(controller, target_low, data, oe, workload, case):
    """Measure continuous controller pulses and target ownership, never MOTIF PCs."""
    ns = workload['core_period_ns']
    timing = workload['timing_us']
    resets = pulse_intervals([not bit for bit in controller])
    releases = [end for start, end in resets
                if (end-start)*ns >= timing['reset_low_min']*1000]
    # System reset invalidates the in-progress initialization epoch. Watchdog is
    # an independently selected safety override, not part of 1-Wire timing.
    if 'reset_us_from_start' in case or 'watchdog_cycles' in case:
        releases = []
    observed = pulse_intervals(target_low)
    errors = []
    if len(releases) != case['expected_presence']:
        errors.append('Controller specification disagrees with expected pulse count')
    if len(observed) != len(releases):
        errors.append(f'Expected {len(releases)} presence pulse(s), observed {len(observed)}')
    for i, (start, end) in enumerate(observed):
        if i < len(releases):
            delay = (start-releases[i])*ns/1000
            width = (end-start)*ns/1000
            if not timing['presence_delay_min'] <= delay <= timing['presence_delay_max']:
                errors.append(f'Presence {i} delay {delay}us outside independent bounds')
            if not timing['presence_low_min'] <= width <= timing['presence_low_max']:
                errors.append(f'Presence {i} width {width}us outside independent bounds')
        if any(not bit for bit in controller[start:end]):
            errors.append(f'Target owns DQ during controller low, pulse {i}')
    if any(mask & ~4 for mask in oe):
        errors.append('Target drove a passive input or unowned pin')
    if any(mask & datum & 4 for mask, datum in zip(oe, data)):
        errors.append('Target drove DQ high')
    return {'passed': not errors, 'errors': errors,
            'qualified_controller_releases_cycles': releases,
            'observed_presence_cycles': observed,
            'timings_us': [{'start': start*ns/1000, 'low': (end-start)*ns/1000}
                           for start, end in observed]}


def controller_case(workload, case, config):
    if 'watchdog_cycles' in case:
        config = replace(config, watchdog=case['watchdog_cycles'])
    engine, controller = Recorder(config), []
    reset_cycle = case.get('reset_us_from_start', -1)*1000//workload['core_period_ns']
    for level, us in case['segments_us']:
        cycles = us*1000//workload['core_period_ns']
        if cycles*workload['core_period_ns'] != us*1000:
            raise ValueError('Nonintegral controller timing')
        for _ in range(cycles):
            cycle = len(controller)
            # Preload constants before the first external pulse. No host activity
            # supplies a frame decision, response or timer during traffic.
            engine.host_push, engine.host_data = 8 <= cycle < 12, 255
            previous = engine.rows[-1] if engine.rows else {'oe': 0}
            resolved = bool(level) and not bool(previous['oe'] & 4)
            pins = 248 | (7 if resolved else 0)
            engine.step(pins, reset=cycle == reset_cycle)
            controller.append(level)
    return engine, controller


def check_selection():
    path = ROOT/'third_workload.json'
    pinned = subprocess.check_output(['git', 'show', SELECTION_COMMIT+':'+path.as_posix()])
    if path.read_bytes().replace(b'\r\n', b'\n') != pinned:
        raise ValueError('Selected workload changed after commitment')
    workload = json.loads(path.read_text())
    if sha((ROOT/'frozen_v2_manifest.json').read_bytes()) != workload['frozen_manifest_sha256_lf']:
        raise ValueError('Selected workload refers to another freeze')
    inputs = {k: workload[k] for k in ('timing_us', 'cases', 'core_period_ns', 'pin_mapping', 'malformed_contract')}
    if digest(inputs) != workload['oracle_input_sha256']:
        raise ValueError('Oracle inputs changed')
    return workload


def run(output=None, model_only=False):
    before = verify()
    workload = check_selection()
    config = configuration(json.loads((ROOT/'configurations/one_wire_reset_presence.json').read_text()))
    reports, counterexample = [], None
    for case in workload['cases']:
        engine, controller = controller_case(workload, case, config)
        directory = Path('build/exchange_decomposition/gate3')/case['name']
        actual = engine.rows if model_only else compare_rtl(engine, directory)
        result = oracle(controller, [bool(r['oe'] & 4) for r in actual],
                        [r['data'] for r in actual], [r['oe'] for r in actual], workload, case)
        if case.get('require_timeout') and not any(r['status'] & 64 for r in actual):
            result['passed'] = False
            result['errors'].append('Watchdog timeout absent')
        report = {**summary(case['name'], engine), 'oracle': result,
                  'model_rtl_agreement': None if model_only else True,
                  'host_actions_during_traffic': 0, 'new_hardware_behavior': False}
        if not model_only:
            report['evidence_sha256_lf'] = {name: sha((directory/name).read_bytes())
                for name in ('inputs.txt', 'model.jsonl', 'rtl.jsonl', 'simulation.log')}
        reports.append(report)
        if not result['passed'] and counterexample is None:
            first = result['observed_presence_cycles'][0][0] if result['observed_presence_cycles'] else 0
            counterexample = {'case': case['name'], 'oracle': result,
                              'window': [{'cycle': i, 'controller_dq': controller[i], **actual[i]}
                                         for i in range(max(0, first-8), min(len(actual), first+9))]}
        print(('PASS' if result['passed'] else 'FAIL')+' unseen '+case['name']+' '+str(len(actual))+' cycles '+str(result['errors']), flush=True)
        del engine, actual, controller
    after = verify()
    if before != after:
        raise ValueError('Freeze changed during unseen attempt')
    passed = all(r['oracle']['passed'] for r in reports)
    result = {'schema_version': 2, 'gate': 3,
              'classification': 'MOTIF_V2_FROZEN_VOCABULARY_UNSEEN_PROTOCOL_GENERALIZATION_CONFIRMED' if passed else 'MOTIF_V2_UNSEEN_PROTOCOL_GENERALIZATION_PARTIAL',
              'workload': workload['workload'], 'selection_commit': SELECTION_COMMIT,
              'cases': reports, 'total_compared_cycles': sum(r['cycles'] for r in reports),
              'frozen_before_after_identical': True, 'freeze_sha256_lf': sha((ROOT/'frozen_v2_manifest.json').read_bytes()),
              'frozen_source_hashes': before['source_hashes'],
              'oracle_and_configuration_hashes': {p.as_posix(): sha(p.read_bytes()) for p in
                  (Path(__file__).relative_to(Path.cwd()), ROOT/'third_workload.json', ROOT/'configurations/one_wire_reset_presence.json')},
              'source_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
              'model_only': model_only, 'counterexample': counterexample,
              'physical': 'ELIGIBLE' if passed and not model_only else 'NOT_REACHED',
              'validated_user': passed and not model_only}
    destination = Path(output) if output else Path('build/exchange_decomposition/gate3/result.json')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    parser.add_argument('--model-only', action='store_true')
    args = parser.parse_args()
    run(args.output, args.model_only)
