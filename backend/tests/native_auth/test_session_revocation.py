"""Real SQL proves common auth cannot trust stale per-worker memory."""
import json
import threading

from starlette.requests import Request
from test_mobile_contract import service, register, isolated_rate_limits


def account(service):
    client, database, namespace = service
    client.cookies.clear(); response, payload = register(client, 'bearer'); client.cookies.clear()
    return response.json()['token'], payload


def test_revoked_warm_cache_denied(service):
    client, database, namespace = service
    token, payload = account(service)
    assert token in namespace['_SESSION_STORE']
    with database() as conn, conn.cursor() as cur:
        cur.execute('DELETE FROM user_tokens WHERE token=%s', (token,))
    assert client.get('/api/auth/me', headers={'Authorization': f'Bearer {token}'}).status_code == 401


def test_expired_warm_cache_denied(service):
    client, database, namespace = service
    token, payload = account(service)
    with database() as conn, conn.cursor() as cur:
        cur.execute("UPDATE user_tokens SET expires_at=NOW()-INTERVAL '1 second' WHERE token=%s", (token,))
    assert client.get('/api/auth/me', headers={'Authorization': f'Bearer {token}'}).status_code == 401


def test_banned_warm_cache_denied(service):
    client, database, namespace = service
    token, payload = account(service)
    with database() as conn, conn.cursor() as cur:
        cur.execute('UPDATE users SET is_banned=TRUE WHERE email=%s', (payload['email'],))
    assert client.get('/api/auth/me', headers={'Authorization': f'Bearer {token}'}).status_code == 401


def test_session_data_cannot_bind_recreated_identity(service):
    client, database, namespace = service
    token, payload = account(service)
    with database() as conn, conn.cursor() as cur:
        cur.execute('UPDATE user_tokens SET data=%s WHERE token=%s',
                    (json.dumps({'id': 'unrelated', 'email': payload['email']}), token))
    assert client.get('/api/auth/me', headers={'Authorization': f'Bearer {token}'}).status_code == 401


def test_inflight_sql_read_does_not_refill_revoked_authorization(service):
    client, database, namespace = service
    token, payload = account(service)
    read = threading.Event(); release = threading.Event(); results = []
    original = namespace['_get_db']
    # Interpose only on the completed real cursor read to control ordering.
    # Every query/row still comes from the actual isolated PostgreSQL cluster.
    class CursorBoundary:
        def __init__(self, cursor): self.cursor = cursor
        def __enter__(self): self.cursor.__enter__(); return self
        def __exit__(self, *args): return self.cursor.__exit__(*args)
        def execute(self, *args): return self.cursor.execute(*args)
        def fetchone(self):
            row = self.cursor.fetchone(); read.set(); assert release.wait(5); return row
    class ConnectionBoundary:
        def __init__(self, conn): self.conn = conn
        def cursor(self): return CursorBoundary(self.conn.cursor())
    original_release = namespace['_release_db']
    namespace['_get_db'] = lambda: ConnectionBoundary(database())
    namespace['_release_db'] = lambda conn: conn.conn.close()
    request = Request({'type': 'http', 'headers': [(b'authorization', f'Bearer {token}'.encode())]})
    thread = threading.Thread(target=lambda: results.append(namespace['_get_session_user'](request)))
    thread.start()
    try:
        assert read.wait(5)
        with database() as conn, conn.cursor() as cur:
            cur.execute('DELETE FROM user_tokens WHERE token=%s', (token,))
        namespace['_SESSION_STORE'].pop(token, None)
        release.set(); thread.join(5); assert not thread.is_alive()
        assert results[0]['email'] == payload['email']  # already in-flight read
    finally:
        release.set(); thread.join(5)
        namespace['_get_db'] = original; namespace['_release_db'] = original_release
    assert token not in namespace['_SESSION_STORE']
    assert client.get('/api/auth/me', headers={'Authorization': f'Bearer {token}'}).status_code == 401
