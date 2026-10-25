"""Real PostgreSQL + TCP verification of the production disciple router.

The session identity boundary reads disposable SQL token records. This suite
qualifies relationship SQL/HTTP behavior, not the complete login/provider flow.
No shared database, production credential, cloud instance, or paid provider is used.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import uuid

import httpx
import psycopg2
from psycopg2.extras import Json
import pytest

PG_BIN = Path('/opt/homebrew/opt/postgresql@17/bin')
REPO = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.integration


def available_port() -> int:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def serve() -> None:
    from fastapi import FastAPI, Request
    from psycopg2.pool import ThreadedConnectionPool
    import uvicorn
    from backend.core import deps
    from backend.routers import disciple

    pool = ThreadedConnectionPool(1, 4, os.environ['BIBLE_NETWORK_NATIVE_DSN'])
    deps.init_deps(pool, None)

    def sql_session_identity(request: Request):
        """Controlled session boundary, backed by actual isolated PostgreSQL."""
        header = request.headers.get('Authorization', '')
        if not header.startswith('Bearer '):
            return None
        conn = deps.acquire_conn()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT data FROM user_tokens WHERE token=%s AND expires_at > NOW()', (header[7:],))
                row = cur.fetchone()
                return row[0] if row else None
        finally:
            deps.release_conn(conn)

    disciple.init_disciple_router(get_db=deps.acquire_conn, release_db=deps.release_conn,
                                 get_session_user=sql_session_identity,
                                 to_shanghai_iso=lambda value: value.isoformat())
    app = FastAPI()
    app.include_router(disciple.router)
    uvicorn.run(app, host='127.0.0.1', port=int(os.environ['BIBLE_NETWORK_NATIVE_HTTP_PORT']),
                log_level='warning')


@pytest.fixture(scope='session')
def native():
    root = Path(os.environ['BIBLE_NETWORK_NATIVE_RUN_ROOT']).resolve()
    assert root.name.startswith('network-native-') and 'app-parity/round4' in str(root)
    root.mkdir(parents=True, exist_ok=False)
    data = root / 'postgres-data'
    init_args = [str(PG_BIN / 'initdb'), '-D', str(data), '-U', 'bible_native',
                 '-A', 'trust', '--no-locale', '--encoding=UTF8']
    with (root / 'initdb.log').open('w') as output:
        subprocess.run(init_args, stdout=output, stderr=subprocess.STDOUT, check=True, timeout=30)
    pg_port, http_port = available_port(), available_port()
    assert pg_port != http_port
    dsn = f'host=127.0.0.1 port={pg_port} user=bible_native dbname=postgres connect_timeout=2'
    pg_log = (root / 'postgres.log').open('w')
    pg_args = [str(PG_BIN / 'postgres'), '-D', str(data), '-h', '127.0.0.1', '-p', str(pg_port),
               '-c', 'unix_socket_directories=', '-c', 'fsync=on']
    pg = subprocess.Popen(pg_args, stdout=pg_log, stderr=subprocess.STDOUT)
    http = None
    http_log = None
    try:
        for _ in range(100):
            assert pg.poll() is None, 'Owned PostgreSQL process exited; see postgres.log'
            try:
                conn = psycopg2.connect(dsn)
                conn.close()
                break
            except psycopg2.OperationalError:
                time.sleep(0.05)
        else:
            raise AssertionError('Owned PostgreSQL readiness timed out')
        with psycopg2.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute('''CREATE TABLE disciple_relationships (
                    id BIGSERIAL PRIMARY KEY, mentor_email VARCHAR(255) NOT NULL,
                    disciple_email VARCHAR(255) DEFAULT '', disciple_name VARCHAR(120) DEFAULT '',
                    relationship_type VARCHAR(20) DEFAULT 'DISCIPLER', status VARCHAR(20) DEFAULT 'ACTIVE',
                    growth_goals JSONB DEFAULT '[]'::jsonb, started_at DATE DEFAULT CURRENT_DATE,
                    ended_at DATE, notes TEXT DEFAULT '')''')
                cur.execute('CREATE TABLE user_tokens (token TEXT PRIMARY KEY, data JSONB NOT NULL, expires_at TIMESTAMPTZ NOT NULL)')
                cur.execute('SELECT version(), pg_backend_pid()')
                version, sql_pid = cur.fetchone()
        env = os.environ.copy()
        env.update(BIBLE_NETWORK_NATIVE_DSN=dsn, BIBLE_NETWORK_NATIVE_HTTP_PORT=str(http_port),
                   PYTHONPATH=str(REPO))
        http_log = (root / 'http.log').open('w')
        http_args = [sys.executable, str(Path(__file__).resolve()), '--serve']
        http = subprocess.Popen(http_args, cwd=REPO, env=env, stdout=http_log, stderr=subprocess.STDOUT)
        base = f'http://127.0.0.1:{http_port}'
        client = httpx.Client(base_url=base, timeout=5)
        for _ in range(150):
            assert http.poll() is None, 'Owned HTTP server exited; see http.log'
            try:
                response = client.get('/api/disciple/network')
                if response.status_code == 401:
                    break
            except httpx.TransportError:
                pass
            time.sleep(0.05)
        else:
            raise AssertionError('Owned native HTTP readiness timed out')
        (root / 'physical-proof.json').write_text(json.dumps({
            'postgres_command': pg_args, 'postgres_pid': pg.pid, 'http_command': http_args,
            'http_pid': http.pid, 'sql_pid': sql_pid, 'postgres_version': version,
            'boundary': 'Local SQL/router TCP only; auth identity adapter is an explicit test boundary.'}, indent=2))
        yield {'dsn': dsn, 'client': client, 'root': root}
        client.close()
    finally:
        if http is not None and http.poll() is None:
            http.terminate()
            http.wait(timeout=10)
        if pg.poll() is None:
            pg.send_signal(signal.SIGINT)
            pg.wait(timeout=10)
        if http_log is not None:
            http_log.close()
        pg_log.close()


@pytest.fixture
def session(native, request):
    tokens = {owner: uuid.uuid4().hex for owner in ('one', 'two')}
    with psycopg2.connect(native['dsn']) as conn:
        with conn.cursor() as cur:
            cur.execute('TRUNCATE disciple_relationships RESTART IDENTITY')
            cur.execute('TRUNCATE user_tokens')
            for owner, token in tokens.items():
                cur.execute("INSERT INTO user_tokens VALUES (%s,%s,NOW()+INTERVAL '1 hour')",
                            (token, Json({'id': owner, 'email': f'{owner}@native.test'})))
    yield native, tokens
    with psycopg2.connect(native['dsn']) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT id,mentor_email,disciple_email,disciple_name,status,ended_at FROM disciple_relationships ORDER BY id')
            rows = cur.fetchall()
    text = json.dumps(rows, default=str, sort_keys=True)
    safe_name = ''.join(c if c.isalnum() else '-' for c in request.node.name)
    (native['root'] / f'postimage-{safe_name}.json').write_text(json.dumps({
        'executed_sql': 'SELECT id,mentor_email,disciple_email,disciple_name,status,ended_at FROM disciple_relationships ORDER BY id',
        'rows': rows, 'rows_sha256': hashlib.sha256(text.encode()).hexdigest()}, default=str, indent=2))


def headers(tokens, owner='one'):
    return {'Authorization': f'Bearer {tokens[owner]}'}


def create(native, tokens, name='actual disciple', owner='one'):
    response = native['client'].post('/api/disciple/network', headers=headers(tokens, owner), json={
        'disciple_name': name, 'disciple_email': 'disciple@native.test',
        'relationship_type': 'DISCIPLER', 'growth_goals': ['actual growth goal']})
    assert response.status_code == 200, response.text
    return response.json()


def sql_row(native, rid):
    with psycopg2.connect(native['dsn']) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT mentor_email,status,ended_at FROM disciple_relationships WHERE id=%s', (rid,))
            return cur.fetchone()


def test_returned_relationship_id_is_real_sql_identity_after_reload(session):
    native, tokens = session
    created = create(native, tokens)
    rid = created['id']
    assert type(rid) is int and rid > 0
    assert created['network']['relationships'][0]['id'] == rid
    result = native['client'].get('/api/disciple/network', headers=headers(tokens)).json()
    assert result['network']['relationships'][0]['id'] == rid
    assert result['network']['breadth'] == 1
    assert sql_row(native, rid) == ('one@native.test', 'ACTIVE', None)


def test_owner_end_ack_commits_real_row_and_removes_active_relationship(session):
    native, tokens = session
    rid = create(native, tokens)['id']
    response = native['client'].post(f'/api/disciple/network/{rid}/end', headers=headers(tokens))
    assert response.status_code == 200 and response.json() == {'ok': True}
    row = sql_row(native, rid)
    assert row[0] == 'one@native.test' and row[1] == 'ENDED' and row[2] is not None
    result = native['client'].get('/api/disciple/network', headers=headers(tokens)).json()
    assert result['network']['relationships'] == [] and result['network']['breadth'] == 0


def test_other_owner_never_receives_success_ack_and_row_stays_active(session):
    native, tokens = session
    rid = create(native, tokens)['id']
    response = native['client'].post(f'/api/disciple/network/{rid}/end', headers=headers(tokens, 'two'))
    assert response.status_code == 404, response.text
    assert sql_row(native, rid) == ('one@native.test', 'ACTIVE', None)
    result = native['client'].get('/api/disciple/network', headers=headers(tokens, 'two')).json()
    assert result['network']['relationships'] == []


def test_nonexistent_identity_never_receives_success_ack(session):
    native, tokens = session
    response = native['client'].post('/api/disciple/network/999999/end', headers=headers(tokens))
    assert response.status_code == 404, response.text
    assert sql_row(native, 999999) is None


def test_repeated_end_is_not_a_second_successful_mutation(session):
    native, tokens = session
    rid = create(native, tokens)['id']
    assert native['client'].post(f'/api/disciple/network/{rid}/end', headers=headers(tokens)).status_code == 200
    before = sql_row(native, rid)
    response = native['client'].post(f'/api/disciple/network/{rid}/end', headers=headers(tokens))
    assert response.status_code == 404, response.text
    assert sql_row(native, rid) == before


def test_auth_missing_or_expired_never_mutates_sql(session):
    native, tokens = session
    rid = create(native, tokens)['id']
    with psycopg2.connect(native['dsn']) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE user_tokens SET expires_at=NOW()-INTERVAL '1 minute' WHERE token=%s", (tokens['one'],))
    for auth in ({}, headers(tokens)):
        assert native['client'].post(f'/api/disciple/network/{rid}/end', headers=auth).status_code == 401
    assert sql_row(native, rid) == ('one@native.test', 'ACTIVE', None)


def test_real_sql_failure_rolls_back_and_pool_remains_usable(session):
    native, tokens = session
    rid = create(native, tokens, name='force-end-failure')['id']
    with psycopg2.connect(native['dsn']) as conn:
        with conn.cursor() as cur:
            cur.execute('''CREATE OR REPLACE FUNCTION reject_owned_test_end() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN RAISE EXCEPTION 'actual isolated PostgreSQL failure'; END $$''')
            cur.execute("CREATE TRIGGER fail_owned_end BEFORE UPDATE ON disciple_relationships FOR EACH ROW WHEN (OLD.disciple_name='force-end-failure') EXECUTE FUNCTION reject_owned_test_end()")
    response = native['client'].post(f'/api/disciple/network/{rid}/end', headers=headers(tokens))
    assert response.status_code == 500
    assert sql_row(native, rid) == ('one@native.test', 'ACTIVE', None)
    result = native['client'].get('/api/disciple/network', headers=headers(tokens))
    assert result.status_code == 200 and result.json()['network']['breadth'] == 1


if __name__ == '__main__':
    assert sys.argv[1:] == ['--serve']
    serve()
