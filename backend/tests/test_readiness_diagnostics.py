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
    import uvicorn
    from routers import main_extracted_health as health

    app = FastAPI()
    ready = threading.Event()
    ready.set()
    pool = _production_pool_type(real_postgres)(1, 4, real_postgres)
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


def _production_pool_type(dsn):
    """Execute the actual production initializer against the test-owned DB."""
    import ast
    from pathlib import Path
    source = Path(__file__).resolve().parents[1] / 'main.py'
    tree = ast.parse(source.read_text())
    nodes = [n for n in tree.body if isinstance(n, ast.ImportFrom) and n.module == 'db_pool']
    nodes += [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_init_database']
    namespace = {'DATABASE_URL': dsn}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), namespace)
    namespace['_init_database']()
    pool = namespace['_db_pool']
    pool_type = type(pool)
    pool.closeall()
    return pool_type


def test_pending_connect_does_not_block_return(real_postgres, monkeypatch):
    import concurrent.futures
    import threading
    import psycopg2
    pool = _production_pool_type(real_postgres)(1, 3, real_postgres)
    borrowed = pool.getconn()
    connect = psycopg2.connect
    entered, allow, returned = threading.Event(), threading.Event(), threading.Event()
    def delayed_connect(*args, **kwargs):
        entered.set()
        assert allow.wait(5)
        return connect(*args, **kwargs)
    monkeypatch.setattr(psycopg2, 'connect', delayed_connect)
    def put():
        pool.putconn(borrowed)
        returned.set()
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            pending = executor.submit(pool.getconn)
            try:
                assert entered.wait(5)
                returning = executor.submit(put)
                assert returned.wait(0.5), 'Returning a healthy connection blocked behind a new connection'
            finally:
                allow.set()
                fresh = pending.result(timeout=5)
                returning.result(timeout=5)
                pool.putconn(fresh)
    finally:
        pool.closeall()


def test_pending_capacity_and_same_key_share_one_real_connection(real_postgres, monkeypatch):
    import concurrent.futures
    import threading
    import psycopg2
    from psycopg2.pool import PoolError
    pool = _production_pool_type(real_postgres)(1, 2, real_postgres)
    borrowed = pool.getconn()
    connect = psycopg2.connect
    entered, allow = threading.Event(), threading.Event()
    calls = []
    def delayed(*args, **kwargs):
        calls.append(1)
        entered.set()
        assert allow.wait(5)
        return connect(*args, **kwargs)
    monkeypatch.setattr(psycopg2, 'connect', delayed)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(pool.getconn, 'shared')
            try:
                assert entered.wait(5)
                second = executor.submit(pool.getconn, 'shared')
                with pytest.raises(PoolError):
                    pool.getconn('excess')
            finally:
                allow.set()
            a, b = first.result(timeout=5), second.result(timeout=5)
            assert a is b and len(calls) == 1
            assert len(pool._used) == 2 and not pool._pending_connections
            with a.cursor() as cursor:
                cursor.execute('SELECT 1')
                assert cursor.fetchone() == (1,)
            pool.putconn(a, 'shared')
            pool.putconn(borrowed)
    finally:
        allow.set()
        pool.closeall()


def test_failed_real_connection_releases_reserved_capacity(real_postgres, monkeypatch):
    import psycopg2
    pool = _production_pool_type(real_postgres)(1, 2, real_postgres)
    borrowed = pool.getconn()
    connect = psycopg2.connect
    calls = []
    def first_fails(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            # Real libpq failure against a unique nonexistent local socket.
            return connect(host='/tmp/no-readiness-db-' + uuid.uuid4().hex,
                           dbname='postgres', user='readiness_test', connect_timeout=5)
        return connect(*args, **kwargs)
    monkeypatch.setattr(psycopg2, 'connect', first_fails)
    try:
        with pytest.raises(psycopg2.OperationalError):
            pool.getconn('new')
        assert not pool._pending_connections
        fresh = pool.getconn('new')
        with fresh.cursor() as cursor:
            cursor.execute('SELECT 1')
            assert cursor.fetchone() == (1,)
        assert len(calls) == 2
        pool.putconn(fresh, 'new')
        pool.putconn(borrowed)
    finally:
        pool.closeall()


def test_close_during_real_connection_creation_closes_late_connection(real_postgres, monkeypatch):
    import concurrent.futures
    import threading
    import psycopg2
    from psycopg2.pool import PoolError
    pool = _production_pool_type(real_postgres)(1, 2, real_postgres)
    pool.getconn()
    connect = psycopg2.connect
    entered, allow = threading.Event(), threading.Event()
    created = []
    def delayed(*args, **kwargs):
        entered.set()
        assert allow.wait(5)
        conn = connect(*args, **kwargs)
        created.append(conn)
        return conn
    monkeypatch.setattr(psycopg2, 'connect', delayed)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(pool.getconn)
            try:
                assert entered.wait(5)
                pool.closeall()
            finally:
                allow.set()
            with pytest.raises(PoolError):
                pending.result(timeout=5)
        assert len(created) == 1 and created[0].closed and not pool._pending_connections
        with pytest.raises(PoolError):
            pool.getconn()
    finally:
        allow.set()
        if not pool.closed:
            pool.closeall()


def test_two_real_connections_can_be_created_concurrently_with_capacity_bound(real_postgres, monkeypatch):
    import concurrent.futures
    import threading
    import psycopg2
    from psycopg2.pool import PoolError
    pool = _production_pool_type(real_postgres)(0, 2, real_postgres)
    connect = psycopg2.connect
    entered, allow = threading.Barrier(3), threading.Event()
    def delayed(*args, **kwargs):
        entered.wait(timeout=5)
        assert allow.wait(5)
        return connect(*args, **kwargs)
    monkeypatch.setattr(psycopg2, 'connect', delayed)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            a, b = executor.submit(pool.getconn), executor.submit(pool.getconn)
            try:
                entered.wait(timeout=5)
                assert len(pool._pending_connections) == 2
                with pytest.raises(PoolError):
                    pool.getconn()
            finally:
                allow.set()
            x, y = a.result(timeout=5), b.result(timeout=5)
        assert x is not y and x.get_backend_pid() != y.get_backend_pid()
        for conn in [x, y]:
            with conn.cursor() as cursor:
                cursor.execute('SELECT 1')
                assert cursor.fetchone() == (1,)
            pool.putconn(conn)
        assert not pool._pending_connections and not pool._used
    finally:
        allow.set()
        pool.closeall()


def test_explicit_key_reuse_and_discard_keep_original_api(real_postgres):
    pool = _production_pool_type(real_postgres)(1, 3, real_postgres)
    try:
        first = pool.getconn('key')
        assert pool.getconn('key') is first
        pool.putconn(first, 'key', close=True)
        assert first.closed
        second = pool.getconn('key')
        assert second is not first and not second.closed
        with second.cursor() as cursor:
            cursor.execute('SELECT 1')
            assert cursor.fetchone() == (1,)
        pool.putconn(second, 'key')
        assert not pool._used
    finally:
        pool.closeall()
