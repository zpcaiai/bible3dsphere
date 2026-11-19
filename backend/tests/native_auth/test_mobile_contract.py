"""Actual PostgreSQL and loopback HTTP authentication contract.

Run with --confcutdir=backend/tests/native_auth and NATIVE_AUTH_TEST_DSN pointing
at a task-owned PostgreSQL cluster. Production auth helpers are compiled from
their original AST to avoid unrelated model downloads during whole-app startup.
No password, session, cookie or SQL persistence implementation is substituted.
"""
import ast
import ipaddress
import json
import os
from pathlib import Path
import random
import secrets
import socket
import threading
import time
import uuid

from fastapi import FastAPI, HTTPException, Request, Response
import httpx
import psycopg2
import pytest
import uvicorn

from backend.routers import main_extracted_auth_email as auth


@pytest.fixture(autouse=True)
def isolated_rate_limits():
    # Each case owns its HTTP workload. Keep the real limiter and its configured
    # ceilings, while preventing earlier unrelated cases from using its quota.
    auth.limiter._storage.reset()


@pytest.fixture(scope='module')
def service():
    root = Path(__file__).resolve().parents[2]
    dsn = os.environ['NATIVE_AUTH_TEST_DSN']
    schema = 'native_auth_' + uuid.uuid4().hex
    with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(f'CREATE SCHEMA {schema}')

    def database():
        return psycopg2.connect(dsn, options=f'-csearch_path={schema}')

    schema_tree = ast.parse((root / 'db_schema.py').read_text())
    statements = [node.args[0].value for node in ast.walk(schema_tree)
                  if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                  and node.func.attr == 'execute' and node.args
                  and isinstance(node.args[0], ast.Constant)
                  and isinstance(node.args[0].value, str)]
    with database() as conn, conn.cursor() as cur:
        for table in ['users', 'user_tokens', 'security_audit', 'user_roles']:
            cur.execute(next(sql for sql in statements
                             if f'CREATE TABLE IF NOT EXISTS {table} (' in sql))
        cur.execute('ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE')
        cur.execute('ALTER TABLE users ADD COLUMN is_banned BOOLEAN DEFAULT FALSE')

    names = {'_get_user', '_get_user_by_email', '_create_user', '_make_session',
             '_get_session_user', '_set_session_cookie', '_clear_session_cookie',
             '_request_is_https', '_security_audit', '_generate_code',
             '_is_admin', '_invalidate_admin_cache'}
    original = root / 'main.py'
    nodes = [node for node in ast.parse(original.read_text()).body
             if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in nodes} == names
    namespace = {
        'HTTPException': HTTPException,
        'Request': Request, 'Response': Response, 'json': json, 'secrets': secrets,
        'random': random, 'time': time, 'ipaddress': ipaddress,
        '_SESSION_LOCK': threading.Lock(), '_SESSION_STORE': {},
        '_AUDIT_LOCK': threading.Lock(), '_get_db': database,
        '_release_db': psycopg2.extensions.connection.close,
        'SESSION_COOKIE_NAME': 'biblesphere_session',
        'SESSION_COOKIE_MAX_AGE': 30 * 24 * 3600,
        '_ADMIN_CACHE': {}, '_ADMIN_CACHE_TTL': 300, 'ADMIN_EMAILS': set(),
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(original), 'exec'), namespace)
    from backend.routers import admin_common
    admin_common._state.update(get_session_user=namespace['_get_session_user'],
                               is_admin=namespace['_is_admin'])
    # The only unavailable integration is email delivery. Explicit dev mode
    # uses the production route's existing local verification-code path.
    auth.init_main_extracted_auth_email(
        get_db=database, release_db=namespace['_release_db'],
        get_session_user=namespace['_get_session_user'],
        get_user=namespace['_get_user'], get_user_by_email=namespace['_get_user_by_email'],
        create_user=namespace['_create_user'], make_session=namespace['_make_session'],
        set_session_cookie=namespace['_set_session_cookie'],
        clear_session_cookie=namespace['_clear_session_cookie'],
        send_email=None, generate_code=namespace['_generate_code'],
        security_audit=namespace['_security_audit'], code_store={},
        code_lock=threading.Lock(), session_store=namespace['_SESSION_STORE'],
        session_lock=namespace['_SESSION_LOCK'], session_cookie_name='biblesphere_session',
        smtp_host='', smtp_port=0, smtp_user='', smtp_pass='',
        sendgrid_api_key='', resend_api_key='', allow_dev_auth_code=True,
        code_ttl_seconds=600,
    )
    app = FastAPI()
    app.state.limiter = auth.limiter
    app.include_router(auth.router)
    namespace['app'] = app
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen()
    server = uvicorn.Server(uvicorn.Config(app, log_level='warning', lifespan='off'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [listener]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert server.started
    with httpx.Client(base_url=f'http://127.0.0.1:{listener.getsockname()[1]}', timeout=5) as client:
        yield client, database, namespace
    server.should_exit = True
    thread.join(timeout=10)
    listener.close()
    assert not thread.is_alive()


def register(client, transport=None, headers=None):
    email = uuid.uuid4().hex + '@example.test'
    code_response = client.post('/api/auth/email/send-code', json={'email': email})
    assert code_response.status_code == 200
    payload = {'email': email, 'password': 'test-only-password-238',
               'code': code_response.json()['dev_code'], 'nickname': 'Contract test'}
    if transport is not None:
        payload['session_transport'] = transport
    response = client.post('/api/auth/email/register', json=payload, headers=headers)
    return response, payload


def test_native_registration_login_and_logout_use_real_session_rows(service):
    client, database, namespace = service
    response, payload = register(client, 'bearer')
    assert response.status_code == 200
    token = response.json()['token']
    assert 'no-store' in response.headers['cache-control']
    with database() as conn, conn.cursor() as cur:
        cur.execute('SELECT email, expires_at > NOW() FROM user_tokens WHERE token=%s', (token,))
        assert cur.fetchone() == (payload['email'], True)
    client.cookies.clear()
    namespace['_SESSION_STORE'].clear()
    assert client.get('/api/auth/me', headers={'Authorization': f'Bearer {token}'}).status_code == 200
    login = client.post('/api/auth/email/login', json={
        'email': payload['email'], 'password': payload['password'], 'session_transport': 'bearer'})
    assert login.status_code == 200
    assert login.json()['token'] != token
    client.cookies.clear()
    assert client.post('/api/auth/logout', headers={'Authorization': f'Bearer {token}'}).status_code == 200
    assert client.get('/api/auth/me', headers={'Authorization': f'Bearer {token}'}).status_code == 401
    with database() as conn, conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM user_tokens WHERE token=%s', (token,))
        assert cur.fetchone()[0] == 0


def test_default_browser_session_keeps_httponly_cookie_without_body_token(service):
    client, _, _ = service
    response, payload = register(client)
    assert response.status_code == 200
    assert 'token' not in response.json()
    cookie = response.headers['set-cookie'].lower()
    assert 'httponly' in cookie and 'samesite=lax' in cookie
    login = client.post('/api/auth/email/login', json={
        'email': payload['email'], 'password': payload['password']})
    assert login.status_code == 200 and 'token' not in login.json()
    assert client.get('/api/auth/me').status_code == 200


@pytest.mark.parametrize('origin', ['https://example.test', 'null'])
def test_browser_bearer_override_rejected_before_registration_side_effects(service, origin):
    client, database, _ = service
    rejected, payload = register(client, 'bearer', {'Origin': origin})
    assert rejected.status_code == 400
    with database() as conn, conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM users WHERE email=%s', (payload['email'],))
        assert cur.fetchone()[0] == 0
    # Reusing the same still-valid code proves rejection did not consume it.
    accepted = client.post('/api/auth/email/register', json=payload)
    assert accepted.status_code == 200 and accepted.json()['token']


def test_invalid_transport_and_credentials_never_issue_native_session(service):
    client, database, _ = service
    response, payload = register(client, 'bearer')
    assert response.status_code == 200
    for transport, password, expected in [('invalid', payload['password'], 422),
                                          ('bearer', 'wrong-password', 401)]:
        result = client.post('/api/auth/email/login', json={
            'email': payload['email'], 'password': password, 'session_transport': transport})
        assert result.status_code == expected and 'token' not in result.json()
    with database() as conn, conn.cursor() as cur:
        cur.execute('UPDATE users SET is_banned=TRUE WHERE email=%s', (payload['email'],))
    result = client.post('/api/auth/email/login', json={
        'email': payload['email'], 'password': payload['password'], 'session_transport': 'bearer'})
    assert result.status_code == 403 and 'token' not in result.json()


def test_legacy_cross_origin_web_contract_is_preserved(service):
    client, _, _ = service
    response, _ = register(client, headers={'Origin': 'https://web.example.test'})
    assert response.status_code == 200
    assert response.json()['token']
    assert 'httponly' in response.headers['set-cookie'].lower()


def test_login_does_not_log_password_derived_material(service, capsys):
    client, database, _ = service
    response, payload = register(client, 'bearer')
    assert response.status_code == 200
    with database() as conn, conn.cursor() as cur:
        cur.execute('SELECT password_hash FROM users WHERE email=%s', (payload['email'],))
        stored_hash = cur.fetchone()[0]
    capsys.readouterr()
    login = client.post('/api/auth/email/login', json={
        'email': payload['email'], 'password': payload['password'], 'session_transport': 'bearer'})
    assert login.status_code == 200
    logs = capsys.readouterr().out
    assert stored_hash not in logs
    assert stored_hash[:30] not in logs
    assert payload['password'] not in logs
