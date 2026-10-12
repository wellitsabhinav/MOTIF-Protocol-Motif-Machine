"""Regression-check a reproduced negative without changing the protocol oracle."""
import argparse
import json
from pathlib import Path


def verify_result(path=Path('build/exchange_decomposition/gate3/result.json')):
    expected = json.loads(Path('experiments/exchange_decomposition/third_result.json').read_text())
    actual = json.loads(Path(path).read_text())
    for key in ('classification', 'workload', 'freeze_sha256_lf', 'total_compared_cycles', 'frozen_source_hashes'):
        if actual[key] != expected[key]:
            raise AssertionError('Unseen evidence changed: '+key)
    if not actual['frozen_before_after_identical'] or actual['model_only'] or actual['validated_user']:
        raise AssertionError('Expected complete, frozen negative qualification')
    if len(actual['cases']) != len(expected['cases']):
        raise AssertionError('Selected cases omitted')
    for old, new in zip(expected['cases'], actual['cases']):
        for key in ('name', 'cycles', 'configuration', 'oracle', 'model_rtl_agreement'):
            if old[key] != new[key]:
                raise AssertionError('Unseen case changed: '+old['name']+' '+key)
        for key in ('inputs.txt', 'model.jsonl', 'rtl.jsonl'):
            if old['evidence_sha256_lf'][key] != new['evidence_sha256_lf'][key]:
                raise AssertionError('Normalized trace changed: '+old['name']+' '+key)
    print('PASS reproduced unseen PARTIAL: eight passes and the preserved interrupted-pulse failure')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--result', type=Path, default=Path('build/exchange_decomposition/gate3/result.json'))
    verify_result(parser.parse_args().result)
