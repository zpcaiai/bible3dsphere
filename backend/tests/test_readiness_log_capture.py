import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    'capture_readiness_logs', Path(__file__).resolve().parents[1] / 'scripts/capture_readiness_logs.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
RID = 'e427d67d-3962-4811-8c33-ea08ac1e1a7f'


def row(**extra):
    return {'kind': 'readiness_stage', 'request_id': RID, 'phase': 'pool.acquire',
            'event': 'start', 'pid': 42, 'thread_id': 43, 'epoch_ns': 44,
            'monotonic_ns': 45, **extra}


def test_selects_exact_owned_raw_json_from_provider_envelope():
    raw = json.dumps(row())
    payload = 'data: ' + json.dumps({'data': '2026-11-02 INFO [readiness] ' + raw})
    selected = module.select_records(payload, {RID})
    assert selected == [{'record': row(), 'raw_record': raw}]


def test_excludes_unrelated_ids_and_private_fields():
    assert module.select_records(json.dumps(row()), set()) == []
    assert module.select_records(json.dumps(row(sql='private input')), {RID}) == []
    assert module.select_records(json.dumps(row(error='credential')), {RID}) == []


def test_excludes_private_paths_forged_timing_and_trailing_content():
    assert module.select_records(json.dumps(row(path='/api/private')), {RID}) == []
    assert module.select_records(json.dumps(row(pid=False)), {RID}) == []
    assert module.select_records(json.dumps(row()) + ' confidential', {RID}) == []


def test_handles_malformed_and_deep_unrelated_input_without_output():
    assert module.select_records('data: invalid private input', {RID}) == []
    payload = {'data': {'data': {'data': json.dumps(row())}}}
    assert len(module.select_records(payload, {RID})) == 1
    assert module.select_records(payload, {RID}, depth=9) == []


def test_transport_exception_does_not_print_credentials(monkeypatch, capsys):
    # Unit-only negative transport injection, not a provider acceptance result.
    monkeypatch.setenv('HF_TOKEN', 'neutral-fixture-token')
    def fail(_request, timeout):
        raise ValueError('invalid header neutral-fixture-token')
    monkeypatch.setattr(module.urllib.request, 'urlopen', fail)
    assert module.capture({RID}, RID) == 1
    raw = capsys.readouterr().out
    assert 'neutral-fixture-token' not in raw and 'invalid header' not in raw
    assert json.loads(raw)['error_type'] == 'ValueError'


def test_missing_existing_configuration_stays_not_run(monkeypatch, capsys):
    monkeypatch.delenv('HF_TOKEN', raising=False)
    assert module.capture({RID}, RID) == 1
    assert json.loads(capsys.readouterr().out)['status'] == 'NOT_RUN'


def test_accepts_only_the_new_technical_connect_phase():
    assert len(module.select_records(json.dumps(row(phase='db.connect')), {RID})) == 1
    assert module.select_records(json.dumps(row(phase='private.conversation')), {RID}) == []
