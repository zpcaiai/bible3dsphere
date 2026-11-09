"""Actual habit router over TCP and isolated PostgreSQL production tables.

Authentication is an explicit fixture boundary, not production-auth acceptance.
HABITS_TEST_DATABASE_URL must refer to a task-owned disposable database.
"""
import ast
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import socket
import threading
import time
import uuid

from fastapi import FastAPI
import httpx
import psycopg2
from psycopg2.extensions import TRANSACTION_STATUS_IDLE
import pytest
import uvicorn

from backend.routers import main_extracted_habits as habits


@pytest.fixture()
def database():
    dsn = os.environ['HABITS_TEST_DATABASE_URL']
    schema = 'native_habits_' + uuid.uuid4().hex
    with psycopg2.connect(dsn) as admin, admin.cursor() as cur:
        cur.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
        cur.execute(f'CREATE SCHEMA {schema}')

    def connect():
        return psycopg2.connect(dsn, options=f'-csearch_path={schema},public')

    root = Path(habits.__file__).parents[1]
    tree = ast.parse((root / 'db_schema.py').read_text())
    users_ddl = next(node.value for node in ast.walk(tree)
                     if isinstance(node, ast.Constant)
                     and isinstance(node.value, str)
                     and 'CREATE TABLE IF NOT EXISTS users (' in node.value)
    # Extract one complete, unmodified CREATE TABLE from production SQL.
    source = (root / 'habit_behavior_schema.sql').read_text()
    start = source.index('CREATE TABLE IF NOT EXISTS habit_state_machines (')
    end = source.index('\n);', start) + len('\n);')
    with connect() as conn, conn.cursor() as cur:
        cur.execute(users_ddl)
        cur.execute(source[start:end])
        cur.execute((root / 'migrations/0046_habit_daily_notes.sql').read_text())
        cur.execute("INSERT INTO users (id,email) VALUES (1,'owner@example.test'),(2,'other@example.test')")
        cur.execute("INSERT INTO habit_state_machines (id,user_id,habit_name,total_executions) VALUES (%s,1,'Reading',7)", (str(uuid.UUID(int=1)),))
        cur.execute("INSERT INTO habit_state_machines (id,user_id,habit_name,total_executions) VALUES (%s,2,'Other',11)", (str(uuid.UUID(int=2)),))
        cur.execute('SELECT pg_backend_pid(),version()')
        pid, version = cur.fetchone()
        assert pid > 0 and 'PostgreSQL 17.' in version
    yield connect
    # Keep task-owned data for inspection; no user schema is touched.


@pytest.fixture()
def wire(database):
    released = []

    def release(conn):
        released.append(conn.get_transaction_status())
        conn.close()

    def identity(request):
        token = request.headers.get('authorization')
        if token == 'Bearer owner':
            return {'id': 1}
        if token == 'Bearer other':
            return {'id': 2}
        return None

    old = (habits._get_db, habits._release_db, habits._get_session_user, habits.settings)
    habits.init_main_extracted_habits(get_db=database, release_db=release,
                                     get_session_user=identity, settings_obj=None)
    app = FastAPI()
    app.include_router(habits.router)
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen()
    server = uvicorn.Server(uvicorn.Config(app, log_level='warning', lifespan='off'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [listener]})
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert server.started
    client = httpx.Client(base_url=f'http://127.0.0.1:{listener.getsockname()[1]}',
                          timeout=10, trust_env=False)
    try:
        yield client, released
    finally:
        client.close()
        server.should_exit = True
        thread.join(timeout=10)
        assert not thread.is_alive()
        listener.close()
        habits._get_db, habits._release_db, habits._get_session_user, habits.settings = old


def snapshot(database):
    with database() as conn, conn.cursor() as cur:
        cur.execute('SELECT user_id,habit_id,note_date::text,note FROM habit_daily_notes ORDER BY user_id,habit_id,note_date')
        notes = cur.fetchall()
        cur.execute('SELECT id::text,user_id,total_executions,current_streak_days FROM habit_state_machines ORDER BY id')
        counters = cur.fetchall()
        cur.execute('SELECT pg_backend_pid()')
        pid = cur.fetchone()[0]
    digest = hashlib.sha256(json.dumps([notes, counters], ensure_ascii=False).encode()).hexdigest()
    print(json.dumps({'row_post_image_sha256': digest, 'postgres_backend_pid': pid,
                      'router_pid': os.getpid(), 'notes': len(notes)}))
    return notes, counters


OWN = str(uuid.UUID(int=1))
FOREIGN = str(uuid.UUID(int=2))
MISSING = str(uuid.UUID(int=3))


def test_owner_upsert_clear_and_execution_counters(wire, database):
    client, released = wire
    _, before = snapshot(database)
    for value in ['first', 'second', '']:
        response = client.post(f'/api/habits/{OWN}/note',
                               headers={'Authorization': 'Bearer owner'}, json={'note': value})
        assert response.status_code == 200 and response.json() == {'ok': True}
        notes, after = snapshot(database)
        assert notes == [('1', OWN, date.today().isoformat(), value)]
        assert after == before
    assert released == [TRANSACTION_STATUS_IDLE] * 3


@pytest.mark.parametrize('habit_id', [FOREIGN, MISSING])
def test_foreign_or_missing_habit_cannot_create_note(wire, database, habit_id):
    client, released = wire
    before = snapshot(database)
    response = client.post(f'/api/habits/{habit_id}/note',
                           headers={'Authorization': 'Bearer owner'}, json={'note': 'private'})
    assert response.status_code == 404
    assert snapshot(database) == before
    assert released == [TRANSACTION_STATUS_IDLE]


def test_unauthenticated_and_invalid_payload_never_write(wire, database):
    client, released = wire
    before = snapshot(database)
    assert client.post(f'/api/habits/{OWN}/note', json={'note': 'private'}).status_code == 401
    response = client.post(f'/api/habits/{OWN}/note',
                           headers={'Authorization': 'Bearer owner'}, json={'note': '界' * 2001})
    assert response.status_code == 422
    assert snapshot(database) == before and released == []


def test_database_rejection_rolls_back_and_keeps_committed_note(wire, database):
    client, released = wire
    headers = {'Authorization': 'Bearer owner'}
    assert client.post(f'/api/habits/{OWN}/note', headers=headers, json={'note': 'retained'}).status_code == 200
    with database() as conn, conn.cursor() as cur:
        cur.execute("ALTER TABLE habit_daily_notes ADD CONSTRAINT reject_test_note CHECK (note <> 'database-rejection')")
    before = snapshot(database)
    response = client.post(f'/api/habits/{OWN}/note', headers=headers, json={'note': 'database-rejection'})
    assert response.status_code == 500
    assert snapshot(database) == before
    assert released[-1] == TRANSACTION_STATUS_IDLE
    assert client.post(f'/api/habits/{OWN}/note', headers=headers, json={'note': 'retry'}).status_code == 200
    assert snapshot(database)[0][0][-1] == 'retry'


def test_owner_is_rechecked_after_concurrent_transfer(wire, database):
    client, released = wire
    holder = database()
    try:
        with holder.cursor() as cur:
            cur.execute('UPDATE habit_state_machines SET user_id=2 WHERE id=%s', (OWN,))
        with ThreadPoolExecutor(1) as pool:
            pending = pool.submit(client.post, f'/api/habits/{OWN}/note',
                                  headers={'Authorization': 'Bearer owner'}, json={'note': 'old-owner'})
            deadline = time.monotonic() + 3
            waiting = False
            while time.monotonic() < deadline and not pending.done():
                with database() as probe, probe.cursor() as cur:
                    cur.execute("SELECT count(*) FROM pg_stat_activity WHERE wait_event_type='Lock' AND query LIKE 'SELECT id FROM habit_state_machines%'")
                    waiting = cur.fetchone()[0] > 0
                if waiting:
                    break
                time.sleep(0.01)
            holder.commit()
            response = pending.result(timeout=10)
        assert waiting, 'The actual router must lock/recheck the parent ownership row'
        assert response.status_code == 404
        assert snapshot(database)[0] == []
        assert released == [TRANSACTION_STATUS_IDLE]
    finally:
        holder.rollback()
        holder.close()
