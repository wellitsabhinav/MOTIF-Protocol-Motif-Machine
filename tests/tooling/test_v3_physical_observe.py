"""Offline evidence/credential guards; no authenticated network calls."""
import io
import json
from urllib.error import HTTPError
import pytest
import tools.v3_physical_observe as observe


def test_redirect_log_download_does_not_forward_authorization(monkeypatch):
    class Opener:
        def open(self, request, timeout):
            assert request.get_header('Authorization') == 'Bearer FIXTURE_ONLY'
            raise HTTPError(request.full_url, 302, 'Found', {'Location': 'https://fixture.invalid/log'}, None)
    monkeypatch.setattr(observe, 'build_opener', lambda handler: Opener())
    def plain_open(url, timeout):
        assert url == 'https://fixture.invalid/log' and isinstance(url, str)
        return io.BytesIO(b'fixture-only log')
    monkeypatch.setattr(observe, 'urlopen', plain_open)
    assert observe.download('actions/jobs/1/logs', 'FIXTURE_ONLY') == b'fixture-only log'


def test_changed_physical_source_blocks_log_collection(tmp_path, monkeypatch):
    monkeypatch.setattr(observe, 'preflight', lambda source: {})
    calls = []
    def get(suffix):
        calls.append(suffix)
        return json.dumps({'id': 1, 'head_sha': 'e' * 40,
                           'path': '.github/workflows/gds.yml', 'run_attempt': 1}).encode()
    with pytest.raises(ValueError, match='another run/source'):
        observe.collect({'run_id': 1, 'source_sha': 'f' * 40}, tmp_path / 'unused', get)
    assert calls == ['actions/runs/1'] and not (tmp_path / 'unused').exists()
