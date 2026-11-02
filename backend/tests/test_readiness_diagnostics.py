import json
import uuid
import asyncio

import pytest

from readiness_diagnostics import request_trace, stage


def records(caplog):
    return [json.loads(r.message) for r in caplog.records if r.name == 'readiness']


def test_stage_failure_is_correlated_and_private(caplog):
    caplog.set_level('INFO', logger='readiness')
    rid = str(uuid.uuid4())
    with pytest.raises(ValueError):
        with request_trace('/health/ready', rid, 'postgres://user:secret@db.example/db'):
            with stage('db.pre_ping'):
                raise ValueError('private SQL and password')
    rows = records(caplog)
    assert [r['event'] for r in rows] == ['start', 'start', 'error', 'error']
    assert all(r['request_id'] == rid and r['pid'] > 0 for r in rows)
    assert rows[-2]['phase'] == 'db.pre_ping'
    assert rows[-2]['error_type'] == 'ValueError'
    assert rows[-2]['elapsed_ms'] >= 0
    assert 'secret' not in caplog.text and 'private SQL' not in caplog.text
    with stage('db.query'):
        pass
    assert len(records(caplog)) == 4


def test_private_routes_are_unobserved_and_invalid_id_is_replaced(caplog):
    caplog.set_level('INFO', logger='readiness')
    with request_trace('/api/private', 'confession', '') as trace:
        assert trace is None
        with stage('db.query'):
            pass
    assert records(caplog) == []
    with request_trace('/health/ready', 'secret\nforged-log', '') as trace:
        assert str(uuid.UUID(trace.request_id)) == trace.request_id
        trace.status = 503
    assert 'secret' not in caplog.text
    assert records(caplog)[-1]['status'] == 503


def test_nested_context_restores_parent(caplog):
    caplog.set_level('INFO', logger='readiness')
    a, b = str(uuid.uuid4()), str(uuid.uuid4())
    with request_trace('/health/ready', a, ''):
        with request_trace('/health/live', b, ''):
            with stage('inner'):
                pass
        with stage('outer'):
            pass
    rows = records(caplog)
    assert next(r for r in rows if r['phase'] == 'inner')['request_id'] == b
    assert next(r for r in rows if r['phase'] == 'outer')['request_id'] == a


def test_concurrent_worker_contexts_do_not_mix(caplog):
    caplog.set_level('INFO', logger='readiness')
    ids = [str(uuid.uuid4()), str(uuid.uuid4())]

    def worker(label):
        with stage(label):
            return label

    async def request(rid, label):
        with request_trace('/health/ready', rid, ''):
            return await asyncio.to_thread(worker, label)

    async def run():
        return await asyncio.gather(*(request(rid, label) for rid, label in zip(ids, ['a', 'b'])))

    assert asyncio.run(run()) == ['a', 'b']
    rows = records(caplog)
    for rid, label in zip(ids, ['a', 'b']):
        assert {r['request_id'] for r in rows if r['phase'] == label} == {rid}
