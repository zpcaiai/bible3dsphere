"""Real HTTP/WebSocket tickets with real PostgreSQL-backed authentication."""
import json
import time

import pytest
from websockets.exceptions import InvalidStatus
from websockets.sync.client import connect

from backend.routers import realtime
from test_mobile_contract import service, register, isolated_rate_limits


@pytest.fixture(scope='module')
def ws_service(service):
    client, database, namespace = service
    assert not realtime.manager.connections
    realtime.manager = realtime.ConnectionManager()
    realtime.init_realtime_router(
        get_db=database, release_db=namespace['_release_db'],
        get_session_user=namespace['_get_session_user'])
    namespace['app'].include_router(realtime.router)
    return client, database, namespace


def native_session(client):
    client.cookies.clear()
    response, payload = register(client, 'bearer')
    assert response.status_code == 200
    client.cookies.clear()
    return response.json()['token'], payload['email']


def issue(client, token):
    response = client.post('/api/rtc/ws-ticket', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    assert token not in response.text
    data = response.json()
    assert data['expires_in'] == 30
    url = str(client.base_url).replace('http://', 'ws://').rstrip('/')
    return f"{url}/api/ws/rtc?ticket={data['ticket']}"


def test_ticket_issue_requires_real_authentication(ws_service):
    client, _, _ = ws_service
    client.cookies.clear()
    response = client.post('/api/rtc/ws-ticket')
    assert response.status_code == 401 and 'ticket' not in response.json()


def test_long_lived_session_token_url_is_rejected(ws_service):
    client, _, _ = ws_service
    token, _ = native_session(client)
    url = str(client.base_url).replace('http://', 'ws://').rstrip('/')
    with pytest.raises(InvalidStatus) as rejected:
        connect(f'{url}/api/ws/rtc?token={token}', open_timeout=5)
    assert rejected.value.response.status_code == 403


def test_ticket_connects_once_and_replay_is_rejected(ws_service):
    client, _, _ = ws_service
    token, email = native_session(client)
    uri = issue(client, token)
    with connect(uri, open_timeout=5) as ws:
        ready = json.loads(ws.recv(timeout=5))
        assert ready['type'] == 'ready' and ready['email'] == email
    with pytest.raises(InvalidStatus) as rejected:
        connect(uri, open_timeout=5)
    assert rejected.value.response.status_code == 403


def test_unused_ticket_cannot_outlive_issuing_session_revocation(ws_service):
    client, database, _ = ws_service
    token, _ = native_session(client)
    uri = issue(client, token)
    assert client.post('/api/auth/logout', headers={'Authorization': f'Bearer {token}'}).status_code == 200
    with database() as conn, conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM user_tokens WHERE token=%s', (token,))
        assert cur.fetchone()[0] == 0
    with pytest.raises(InvalidStatus) as rejected:
        connect(uri, open_timeout=5)
    assert rejected.value.response.status_code == 403


def test_ticket_expires_with_actual_wall_clock(ws_service):
    client, _, _ = ws_service
    token, _ = native_session(client)
    uri = issue(client, token)
    time.sleep(realtime.WS_TICKET_TTL_SECONDS + 0.1)
    with pytest.raises(InvalidStatus) as rejected:
        connect(uri, open_timeout=5)
    assert rejected.value.response.status_code == 403


def test_each_session_ticket_retains_its_original_owner(ws_service):
    client, _, _ = ws_service
    first, first_email = native_session(client)
    first_uri = issue(client, first)
    second, second_email = native_session(client)
    second_uri = issue(client, second)
    assert first_email != second_email
    with connect(first_uri, open_timeout=5) as ws:
        assert json.loads(ws.recv(timeout=5))['email'] == first_email
    with connect(second_uri, open_timeout=5) as ws:
        assert json.loads(ws.recv(timeout=5))['email'] == second_email


@pytest.mark.parametrize('invalidity', ['expired', 'banned'])
def test_warm_cache_cannot_issue_ticket_for_invalid_database_session(ws_service, invalidity):
    client, database, namespace = ws_service
    token, email = native_session(client)
    assert token in namespace['_SESSION_STORE']
    with database() as conn, conn.cursor() as cur:
        if invalidity == 'expired':
            cur.execute("UPDATE user_tokens SET expires_at=NOW()-INTERVAL '1 second' WHERE token=%s", (token,))
        else:
            cur.execute('UPDATE users SET is_banned=TRUE WHERE email=%s', (email,))
    response = client.post('/api/rtc/ws-ticket', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 401


def test_active_logout_closes_only_originating_session_without_client_cooperation(ws_service):
    from websockets.exceptions import ConnectionClosed
    client, _, _ = ws_service
    token, email = native_session(client)
    other = client.post('/api/auth/email/login', json={
        'email': email, 'password': 'test-only-password-238', 'session_transport': 'bearer'})
    assert other.status_code == 200
    second = other.json()['token']
    client.cookies.clear()
    with connect(issue(client, token), open_timeout=5) as ws, connect(issue(client, second), open_timeout=5) as same_account:
        assert json.loads(ws.recv(timeout=5))['type'] == 'ready'
        assert json.loads(same_account.recv(timeout=5))['type'] == 'ready'
        assert client.post('/api/auth/logout', headers={'Authorization': f'Bearer {token}'}).status_code == 200
        with pytest.raises(ConnectionClosed) as closed:
            ws.recv(timeout=5)
        assert closed.value.rcvd.code == 4401
        # A separate token of the same email remains usable, including new ticket.
        with connect(issue(client, second), open_timeout=5) as still_valid:
            assert json.loads(still_valid.recv(timeout=5))['email'] == email


def test_active_expired_session_cannot_dispatch_incoming_frame(ws_service):
    from websockets.exceptions import ConnectionClosed
    client, database, _ = ws_service
    token, _ = native_session(client)
    with connect(issue(client, token), open_timeout=5) as ws:
        assert json.loads(ws.recv(timeout=5))['type'] == 'ready'
        with database() as conn, conn.cursor() as cur:
            cur.execute("UPDATE user_tokens SET expires_at=NOW()-INTERVAL '1 second' WHERE token=%s", (token,))
        ws.send(json.dumps({'type': 'chat', 'to': 'not-a-friend@example.test', 'body': 'must not dispatch'}))
        with pytest.raises(ConnectionClosed) as closed:
            ws.recv(timeout=5)
        assert closed.value.rcvd.code == 4401


def test_active_revoked_session_does_not_receive_server_push(ws_service):
    import asyncio
    from websockets.exceptions import ConnectionClosed
    client, database, _ = ws_service
    token, email = native_session(client)
    with connect(issue(client, token), open_timeout=5) as ws:
        assert json.loads(ws.recv(timeout=5))['type'] == 'ready'
        with database() as conn, conn.cursor() as cur:
            cur.execute('DELETE FROM user_tokens WHERE token=%s', (token,))
        loop = realtime._state['loop']
        assert loop is not None and loop.is_running()
        future = asyncio.run_coroutine_threadsafe(
            realtime.manager.send_to_user(email, {'type': 'chat', 'body': 'must not receive'}), loop)
        future.result(timeout=5)
        with pytest.raises(ConnectionClosed) as closed:
            ws.recv(timeout=5)
        assert closed.value.rcvd.code == 4401


@pytest.mark.parametrize('invalidity', ['expired', 'banned'])
def test_issued_ticket_rechecks_database_before_consumption(ws_service, invalidity):
    client, database, _ = ws_service
    token, email = native_session(client)
    uri = issue(client, token)
    with database() as conn, conn.cursor() as cur:
        if invalidity == 'expired':
            cur.execute("UPDATE user_tokens SET expires_at=NOW()-INTERVAL '1 second' WHERE token=%s", (token,))
        else:
            cur.execute('UPDATE users SET is_banned=TRUE WHERE email=%s', (email,))
    with pytest.raises(InvalidStatus) as rejected:
        connect(uri, open_timeout=5)
    assert rejected.value.response.status_code == 403


def test_session_sql_lock_does_not_block_realtime_event_loop(ws_service):
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    client, database, _ = ws_service
    token, _ = native_session(client)
    with connect(issue(client, token), open_timeout=5) as anchor:
        assert json.loads(anchor.recv(timeout=5))['type'] == 'ready'
        uri = issue(client, token)
        blocker = database()
        executor = ThreadPoolExecutor(max_workers=1)
        pending = None
        try:
            with blocker.cursor() as cur:
                cur.execute('LOCK TABLE user_tokens IN ACCESS EXCLUSIVE MODE')
            pending = executor.submit(connect, uri, open_timeout=5)
            deadline = time.monotonic() + 2
            waiting = 0
            while waiting == 0 and time.monotonic() < deadline:
                with database() as probe, probe.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM pg_stat_activity WHERE wait_event_type='Lock' "
                                "AND query LIKE 'SELECT t.data FROM user_tokens%'")
                    waiting = cur.fetchone()[0]
                if waiting == 0:
                    time.sleep(0.01)
            assert waiting > 0, 'Real auth SQL must be waiting on our PostgreSQL lock'

            async def event_loop_tick():
                await asyncio.sleep(0.05)
                return asyncio.get_running_loop() is realtime._state['loop']

            tick = asyncio.run_coroutine_threadsafe(event_loop_tick(), realtime._state['loop'])
            assert tick.result(timeout=1) is True
            assert not pending.done(), 'Handshake cannot finish before auth lock releases'
        finally:
            blocker.rollback()
            blocker.close()
            if pending is not None:
                ws = pending.result(timeout=5)
                assert json.loads(ws.recv(timeout=5))['type'] == 'ready'
                ws.close()
            executor.shutdown(wait=True)


def test_mixed_cookie_and_bearer_logout_revokes_same_session_that_issued_ticket(ws_service):
    from websockets.exceptions import ConnectionClosed
    client, database, _ = ws_service
    first, email = native_session(client)
    login = client.post('/api/auth/email/login', json={
        'email': email, 'password': 'test-only-password-238', 'session_transport': 'bearer'})
    second = login.json()['token']
    client.cookies.set('biblesphere_session', first)
    try:
        with connect(issue(client, second), open_timeout=5) as ws:
            assert json.loads(ws.recv(timeout=5))['email'] == email
            assert client.post('/api/auth/logout', headers={'Authorization': f'Bearer {second}'}).status_code == 200
            with database() as conn, conn.cursor() as cur:
                cur.execute('SELECT token=%s FROM user_tokens WHERE token IN (%s,%s)', (second, first, second))
                assert cur.fetchall() == [(True,)]
            with pytest.raises(ConnectionClosed) as closed:
                ws.recv(timeout=5)
            assert closed.value.rcvd.code == 4401
    finally:
        client.cookies.clear()


def test_room_response_after_lock_wait_rechecks_revoked_session(ws_service):
    import asyncio
    from websockets.exceptions import ConnectionClosed
    client, database, _ = ws_service
    token, email = native_session(client)
    _, peer = native_session(client)
    low, high = sorted([email, peer])
    room = 'vd_revoked_lock_room'
    with database() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO friendships(requester,addressee,user_low,user_high,status) VALUES(%s,%s,%s,%s,'accepted')",
                    (email, peer, low, high))
        cur.execute("INSERT INTO direct_voice_rooms(id,user_low,user_high,expires_at) VALUES(%s,%s,%s,NOW()+INTERVAL '1 hour')",
                    (room, low, high))
    with connect(issue(client, token), open_timeout=5) as ws:
        assert json.loads(ws.recv(timeout=5))['type'] == 'ready'
        loop = realtime._state['loop']
        asyncio.run_coroutine_threadsafe(realtime.manager._lock.acquire(), loop).result(timeout=5)
        try:
            ws.send(json.dumps({'type': 'join_room', 'room': room}))

            async def wait_for_join_waiter():
                deadline = asyncio.get_running_loop().time() + 2
                while not realtime.manager._lock._waiters:
                    assert asyncio.get_running_loop().time() < deadline
                    await asyncio.sleep(0.01)

            asyncio.run_coroutine_threadsafe(wait_for_join_waiter(), loop).result(timeout=3)
            assert client.post('/api/auth/logout', headers={'Authorization': f'Bearer {token}'}).status_code == 200
        finally:
            loop.call_soon_threadsafe(realtime.manager._lock.release)
        with pytest.raises(ConnectionClosed) as closed:
            ws.recv(timeout=5)
        assert closed.value.rcvd.code == 4401


def test_concurrent_revocation_closes_always_clean_manager_state(ws_service):
    import asyncio
    from websockets.exceptions import ConnectionClosed
    client, database, _ = ws_service
    token, email = native_session(client)
    with connect(issue(client, token), open_timeout=5) as ws:
        assert json.loads(ws.recv(timeout=5))['type'] == 'ready'
        with database() as conn, conn.cursor() as cur:
            cur.execute('DELETE FROM user_tokens WHERE token=%s', (token,))

        async def simultaneous_closes():
            actual = next(iter(realtime.manager.connections[email]))
            await asyncio.gather(realtime.manager.close_socket(actual),
                                 realtime.manager.close_socket(actual),
                                 realtime.manager.send_to_socket(email, actual, {'type': 'private'}))
            deadline = asyncio.get_running_loop().time() + 2
            while actual in realtime.manager.sessions:
                assert asyncio.get_running_loop().time() < deadline
                await asyncio.sleep(0.01)
            assert actual not in realtime.manager.send_locks
            assert not realtime.manager.is_online(email)

        asyncio.run_coroutine_threadsafe(simultaneous_closes(), realtime._state['loop']).result(timeout=5)
        with pytest.raises(ConnectionClosed):
            ws.recv(timeout=5)


def test_pending_delivery_waits_for_ready_without_blocking_ready_send_lock(ws_service):
    import asyncio
    client, database, _ = ws_service
    first, a = native_session(client)
    second, b = native_session(client)
    with connect(issue(client, second), open_timeout=5) as anchor:
        assert json.loads(anchor.recv(timeout=5))['type'] == 'ready'
        blocker = database()
        pending = None
        waiting_socket = None
        try:
            with blocker.cursor() as cur:
                cur.execute('LOCK TABLE friendships IN ACCESS EXCLUSIVE MODE')
            waiting_socket = connect(issue(client, first), open_timeout=5)
            deadline = time.monotonic() + 2
            waiting = 0
            while waiting == 0 and time.monotonic() < deadline:
                with database() as probe, probe.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM pg_stat_activity WHERE wait_event_type='Lock' "
                                "AND query LIKE '%%FROM friendships WHERE%%'")
                    waiting = cur.fetchone()[0]
                if not waiting:
                    time.sleep(0.01)
            assert waiting > 0
            pending = asyncio.run_coroutine_threadsafe(realtime.manager.send_to_user(a,
                {'type': 'presence', 'email': b, 'online': True}), realtime._state['loop'])
            time.sleep(0.05)
            assert not pending.done(), 'Private delivery must wait outside ready send lock'
        finally:
            blocker.rollback()
            blocker.close()
        try:
            assert json.loads(waiting_socket.recv(timeout=5))['type'] == 'ready'
            assert json.loads(waiting_socket.recv(timeout=5))['type'] == 'presence'
            pending.result(timeout=5)
        finally:
            if waiting_socket is not None:
                waiting_socket.close()
