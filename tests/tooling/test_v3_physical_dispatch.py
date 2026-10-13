"""Offline dispatch guards; these fixtures never launch a workflow."""
import json
from pathlib import Path
import pytest
import tools.v3_physical_dispatch as dispatch


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    intent = {"attempt": 1, "source_sha": "f" * 40, "status": "prepared_before_dispatch",
              "frozen_manifest_sha256_lf": "c" * 64,
              "preregistration": {"commit": "d" * 40, "sha256_lf": "d" * 64}}
    path = tmp_path / 'attempt_1_intent.json'
    path.write_text(json.dumps(intent))
    monkeypatch.setattr(dispatch, 'DIRECTORY', tmp_path)
    monkeypatch.setattr(dispatch, 'preflight', lambda source: {key: intent[key] for key in
                        ("source_sha", "frozen_manifest_sha256_lf", "preregistration")})
    request = {"attempt": 1, "source_sha": "f" * 40, "branch": "fixture-only",
               "intent_sha256_lf": dispatch.sha(path.read_bytes())}
    calls = []
    def api(method, suffix, data=None):
        calls.append((method, suffix, data))
        if suffix.startswith('git/ref/'):
            return {"object": {"sha": request['source_sha']}}
        if method == 'GET':
            return {"total_count": 0, "workflow_runs": []}
        return {"workflow_run_id": 123, "html_url": "https://github.com/fixture/run/123"}
    return request, api, calls


def test_exact_prepared_source_dispatches_once_and_records_response(prepared):
    request, api, calls = prepared
    result = dispatch.launch(request, api)
    assert result['dispatched'] and result['workflow_run_id'] == 123
    assert [call for call in calls if call[0] == 'POST'] == [
        ('POST', 'actions/workflows/gds.yml/dispatches', {'ref': 'fixture-only', 'return_run_details': True})]


def test_existing_source_run_prevents_duplicate_post(prepared):
    request, api, calls = prepared
    def existing(method, suffix, data=None):
        if suffix.startswith('actions/runs'):
            return {'total_count': 1, 'workflow_runs': [{'path': '.github/workflows/gds.yml',
                    'id': 456, 'html_url': 'https://github.com/fixture/run/456', 'run_attempt': 1}]}
        return api(method, suffix, data)
    result = dispatch.launch(request, existing)
    assert result['dispatched'] is False and result['workflow_run_id'] == 456
    assert not any(call[0] == 'POST' for call in calls)


def test_moved_source_ref_prevents_dispatch(prepared):
    request, api, calls = prepared
    def moved(method, suffix, data=None):
        return {'object': {'sha': 'e' * 40}}
    with pytest.raises(ValueError, match='branch moved'):
        dispatch.launch(request, moved)
    assert calls == []


def test_changed_intent_prevents_even_api_reads(prepared):
    request, api, calls = prepared
    request['intent_sha256_lf'] = '0' * 64
    with pytest.raises(ValueError, match='immutable intent'):
        dispatch.launch(request, api)
    assert calls == []


def test_empty_success_does_not_retry_post(prepared):
    request, api, calls = prepared
    def empty(method, suffix, data=None):
        response = api(method, suffix, data)
        return {} if method == 'POST' else response
    result = dispatch.launch(request, empty)
    assert result['dispatched'] and result['workflow_run_id'] is None
    assert sum(call[0] == 'POST' for call in calls) == 1
