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


@pytest.fixture(scope='module')
def real_postgres():
    """A task-owned real cluster; never connect to an existing user database."""
    import os
    from pathlib import Path
    import subprocess
    import tempfile
    import psycopg2

    root = Path(tempfile.mkdtemp(prefix='readiness-pg-', dir='/tmp'))
    bindir = Path(subprocess.check_output(['pg_config', '--bindir'], text=True).strip())
    data = root / 'data'
    subprocess.run([str(bindir / 'initdb'), '-D', str(data), '-A', 'trust',
                    '-U', 'readiness_test', '--no-locale', '--encoding=UTF8'],
                   check=True, capture_output=True, timeout=5)
    control = [str(bindir / 'pg_ctl'), '-D', str(data)]
    subprocess.run([*control, '-l', str(root / 'postgres.log'), '-o',
                    f"-k {root} -h ''", '-w', '-t', '5', 'start'],
                   check=True, capture_output=True, timeout=5)
    pg_pid = int((data / 'postmaster.pid').read_text().splitlines()[0])
    dsn = f'host={root} dbname=postgres user=readiness_test connect_timeout=5'
    try:
        with psycopg2.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT pg_backend_pid(), version()')
                backend_pid, version = cur.fetchone()
        print(json.dumps({'postgres_pid': pg_pid, 'backend_pid': backend_pid,
                          'test_pid': os.getpid(), 'version': version}), flush=True)
        assert pg_pid > 0 and pg_pid != os.getpid()
        yield dsn
    finally:
        subprocess.run([*control, '-m', 'fast', '-w', '-t', '5', 'stop'],
                       check=True, capture_output=True, timeout=5)
        print(json.dumps({'owned_postgres_stopped': pg_pid,
                          'raw_log': str(root / 'postgres.log')}), flush=True)


@pytest.fixture
def real_http(real_postgres):
    """Real router/middleware and unchanged DB helper AST, under real Uvicorn."""
    import ast
    from pathlib import Path
    import socket
    import threading
    import time
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    from psycopg2.pool import ThreadedConnectionPool
    import uvicorn
    from routers import main_extracted_health as health

    app = FastAPI()
    ready = threading.Event()
    ready.set()
    pool = ThreadedConnectionPool(1, 4, real_postgres)
    namespace = {'app': app, 'Request': Request, 'JSONResponse': JSONResponse,
                 '_db_pool': pool, '_runtime_ready': ready, '_runtime_init_error': None,
                 'DATABASE_URL': 'postgres://readiness_test@localhost/postgres',
                 '_readiness_request': request_trace, '_db_stage': stage}
    source = Path(__file__).resolve().parents[1] / 'main.py'
    names = {'_is_stale_conn_error', '_get_db', '_release_db', 'runtime_readiness_guard'}
    nodes = [n for n in ast.parse(source.read_text()).body
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]
    assert len(nodes) == 4
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), namespace)
    health.init_main_extracted_health(get_db=namespace['_get_db'],
        release_db=namespace['_release_db'], get_db_pool=lambda: pool,
        runtime_ready=ready.is_set, ai_status_payload=None,
        database_url=namespace['DATABASE_URL'])
    app.include_router(health.router)
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    sock.listen()
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level='warning', lifespan='off'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]})
    thread.start()
    limit = time.monotonic() + 5
    try:
        while not server.started and thread.is_alive() and time.monotonic() < limit:
            time.sleep(0.01)
        assert server.started and time.monotonic() < limit
        yield f'http://127.0.0.1:{port}', pool, ready
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        assert not thread.is_alive()
        sock.close()
        pool.closeall()


def test_real_http_postgres_stale_connection_recovery(real_http, real_postgres, caplog):
    import urllib.request
    import psycopg2
    caplog.set_level('INFO', logger='readiness')
    url, pool, _ready = real_http
    victim = pool._pool[0].get_backend_pid()
    with psycopg2.connect(real_postgres) as admin:
        with admin.cursor() as cursor:
            cursor.execute('SELECT pg_terminate_backend(%s)', (victim,))
            assert cursor.fetchone()[0] is True
    rid = str(uuid.uuid4())
    request = urllib.request.Request(url + '/health/ready', headers={'X-Request-ID': rid})
    with urllib.request.urlopen(request, timeout=5) as response:
        assert response.status == 200 and response.headers['X-Request-ID'] == rid
        assert json.load(response) == {'status': 'ready', 'database': 'connected'}
    rows = [r for r in records(caplog) if r['request_id'] == rid]
    assert any(r['phase'] == 'db.pre_ping' and r['event'] == 'error' for r in rows)
    assert any(r['phase'] == 'pool.discard' and r['event'] == 'end' for r in rows)
    for phase in ['pool.acquire', 'db.pre_ping', 'db.query', 'db.rollback', 'pool.release']:
        assert any(r['phase'] == phase and r['event'] == 'end' for r in rows)
    assert rows[-1]['phase'] == 'request' and rows[-1]['status'] == 200
    print(json.dumps({'real_http_stale_recovery': rows}), flush=True)


def test_real_five_second_timeout_retains_open_acquire_stage(real_http, caplog):
    import socket
    import time
    import urllib.request
    caplog.set_level('INFO', logger='readiness')
    url, pool, _ready = real_http
    rid = str(uuid.uuid4())
    request = urllib.request.Request(url + '/health/ready', headers={'X-Request-ID': rid})
    # Fault injection holds the actual pool mutex; no substituted DB/HTTP core.
    pool._lock.acquire()
    started = time.monotonic()
    try:
        with pytest.raises((TimeoutError, socket.timeout)):
            urllib.request.urlopen(request, timeout=5)
        assert time.monotonic() - started >= 5
        rows = [r for r in records(caplog) if r['request_id'] == rid]
        assert [r['phase'] for r in rows] == ['request', 'pool.acquire']
        assert all(r['event'] == 'start' for r in rows)
        print(json.dumps({'injected_real_http_5s_timeout': rows}), flush=True)
    finally:
        pool._lock.release()


def test_real_startup_guard_and_liveness_preserve_statuses(real_http, caplog):
    import urllib.error
    import urllib.request
    caplog.set_level('INFO', logger='readiness')
    url, _pool, ready = real_http
    ready.clear()
    rid = str(uuid.uuid4())
    request = urllib.request.Request(url + '/health/ready', headers={'X-Request-ID': rid})
    with pytest.raises(urllib.error.HTTPError) as caught:
        urllib.request.urlopen(request, timeout=5)
    assert caught.value.code == 503
    assert caught.value.headers['X-Request-ID'] == rid
    assert json.load(caught.value)['status'] == 'starting'
    with urllib.request.urlopen(url + '/health/live', timeout=5) as response:
        assert response.status == 200
        assert json.load(response)['status'] == 'live'
    rows = [r for r in records(caplog) if r['request_id'] == rid]
    assert [r['phase'] for r in rows] == ['request', 'request']
    assert rows[-1]['status'] == 503
