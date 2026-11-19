"""Unfrozen social controls: actual HTTP requests and PostgreSQL row images."""
import ast
import json
from pathlib import Path

import pytest

from test_ws_ticket_contract import ws_service, native_session
from test_mobile_contract import service, isolated_rate_limits
from backend.routers import realtime, voice
from websockets.sync.client import connect
from test_ws_ticket_contract import issue


@pytest.fixture(scope='module')
def social_service(ws_service):
    client, database, namespace = ws_service
    # Execute the actual existing voice membership DDL without SDK startup.
    tree = ast.parse((Path(__file__).resolve().parents[2] / 'routers/voice.py').read_text())
    ddl = next(n.value.value for n in tree.body if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == '_TABLES_SQL' for t in n.targets))
    with database() as conn, conn.cursor() as cur:
        cur.execute(ddl)
    voice.init_voice_router(get_db=database, release_db=namespace['_release_db'],
                            get_session_user=namespace['_get_session_user'])
    namespace['app'].include_router(voice.router)
    return client, database, namespace


def headers(token):
    return {'Authorization': f'Bearer {token}'}


def make_friends(database, a, b):
    lo, hi = sorted([a, b])
    with database() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO friendships(requester,addressee,user_low,user_high,status) "
                    "VALUES(%s,%s,%s,%s,'accepted')", (a, b, lo, hi))


def ready_frame(socket):
    # The current server can deliver an authorized friend's presence while the
    # initial friend SQL is still loading. The native transport waits for ready.
    for _ in range(10):
        frame = json.loads(socket.recv(timeout=5))
        if frame['type'] == 'presence':
            continue
        assert frame['type'] == 'ready'
        return frame
    raise AssertionError('Server readiness never arrived')


def test_safety_requires_session_and_valid_schema(social_service):
    client, _, _ = social_service
    client.cookies.clear()
    for path, payload in [('/api/safety/blocks', {'email': 'nobody@example.test'}),
                          ('/api/safety/reports', {'resource_type': 'user', 'target_email': 'nobody@example.test', 'category': 'spam'})]:
        assert client.post(path, json=payload).status_code == 401
    token, _ = native_session(client)
    assert client.post('/api/safety/reports', headers=headers(token), json={
        'resource_type': 'user', 'category': 'not-a-category'}).status_code == 422


def test_blocks_persist_idempotently_and_unblock_is_owner_scoped(social_service):
    client, database, namespace = social_service
    first, a = native_session(client)
    second, b = native_session(client)
    for _ in range(2):
        assert client.post('/api/safety/blocks', headers=headers(first), json={'email': b}).json() == {'blocked': True}
    assert client.get('/api/safety/blocks', headers=headers(first)).json()['blocked'] == [b]
    assert client.get('/api/safety/blocks', headers=headers(second)).json()['blocked'] == []
    assert client.post('/api/safety/unblock', headers=headers(second), json={'email': a}).status_code == 200
    with database() as conn, conn.cursor() as cur:
        cur.execute('SELECT blocker_email,blocked_email FROM user_blocks WHERE blocker_email=%s', (a,))
        assert cur.fetchall() == [(a, b)]
    assert client.post('/api/safety/blocks', headers=headers(first), json={'email': a}).status_code == 400
    assert client.post('/api/safety/unblock', headers=headers(first), json={'email': b}).json() == {'blocked': False}
    assert client.get('/api/safety/blocks', headers=headers(first)).json()['blocked'] == []


def test_received_message_report_resolves_actual_sender_not_supplied_target(social_service):
    client, database, _ = social_service
    sender, a = native_session(client)
    recipient, b = native_session(client)
    with database() as conn, conn.cursor() as cur:
        cur.execute('INSERT INTO chat_messages(sender,recipient,body) VALUES(%s,%s,%s) RETURNING id',
                    (a, b, 'private body must not be copied into report'))
        mid = cur.fetchone()[0]
    payload = {'resource_type': 'direct_message', 'resource_id': mid, 'target_email': 'forged@example.test', 'category': 'harassment'}
    first = client.post('/api/safety/reports', headers=headers(recipient), json=payload)
    assert first.status_code == 200 and first.json()['status'] == 'review_pending'
    second = client.post('/api/safety/reports', headers=headers(recipient), json=payload)
    assert first.json() == second.json()
    with database() as conn, conn.cursor() as cur:
        cur.execute('SELECT reporter_email,target_email,resource_type,resource_key,category,status FROM social_reports WHERE id=%s',
                    (first.json()['id'],))
        assert cur.fetchone() == (b, a, 'direct_message', str(mid), 'harassment', 'review_pending')
    assert 'private body' not in first.text
    # Sender cannot spoof recipient access to report the same private message.
    assert client.post('/api/safety/reports', headers=headers(sender), json=payload).status_code == 404


def test_reports_reject_cross_account_private_message_idor(social_service):
    client, database, _ = social_service
    first, a = native_session(client)
    _, b = native_session(client)
    stranger, c = native_session(client)
    with database() as conn, conn.cursor() as cur:
        cur.execute('INSERT INTO chat_messages(sender,recipient,body) VALUES(%s,%s,%s) RETURNING id', (a, b, 'private'))
        mid = cur.fetchone()[0]
    assert client.post('/api/safety/reports', headers=headers(stranger), json={
        'resource_type': 'direct_message', 'resource_id': mid, 'category': 'spam'}).status_code == 404
    assert client.post('/api/safety/reports', headers=headers(first), json={
        'resource_type': 'user', 'target_email': a, 'category': 'spam'}).status_code == 400
    assert client.post('/api/safety/reports', headers=headers(stranger), json={
        'resource_type': 'user', 'target_email': b, 'category': 'spam'}).status_code == 200


def test_moderation_requires_current_database_admin_and_persists_human_disposition(social_service):
    client, database, namespace = social_service
    first, a = native_session(client)
    _, b = native_session(client)
    response = client.post('/api/safety/reports', headers=headers(first), json={
        'resource_type': 'user', 'target_email': b, 'category': 'child_safety'})
    rid = response.json()['id']
    assert client.get('/api/safety/moderation/reports', headers=headers(first)).status_code == 403
    assert client.post(f'/api/safety/moderation/reports/{rid}/review', headers=headers(first),
                       json={'disposition': 'dismissed'}).status_code == 403
    with database() as conn, conn.cursor() as cur:
        cur.execute('UPDATE users SET is_admin=TRUE WHERE email=%s', (a,))
    namespace['_invalidate_admin_cache'](a)
    queue = client.get('/api/safety/moderation/reports', headers=headers(first))
    assert queue.status_code == 200 and rid in [r['id'] for r in queue.json()['reports']]
    review = client.post(f'/api/safety/moderation/reports/{rid}/review', headers=headers(first),
                         json={'disposition': 'escalated'})
    assert review.json()['status'] == 'under_review'
    with database() as conn, conn.cursor() as cur:
        cur.execute('SELECT status,reviewer_email,disposition,reviewed_at IS NOT NULL FROM social_reports WHERE id=%s', (rid,))
        assert cur.fetchone() == ('under_review', a, 'escalated', True)
        cur.execute('UPDATE users SET is_admin=FALSE WHERE email=%s', (a,))
    namespace['_invalidate_admin_cache'](a)
    assert client.get('/api/safety/moderation/reports', headers=headers(first)).status_code == 403
    with database() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO user_roles(email,role) VALUES(%s,'admin') ON CONFLICT(email) DO UPDATE SET role='admin'", (a,))
    namespace['_invalidate_admin_cache'](a)
    assert client.get('/api/safety/moderation/reports', headers=headers(first)).status_code == 200


def test_block_prevents_real_chat_signal_history_and_voice_without_dropping_recipient(social_service):
    client, database, _ = social_service
    first, a = native_session(client)
    second, b = native_session(client)
    make_friends(database, a, b)
    with connect(issue(client, first), open_timeout=5) as sender, connect(issue(client, second), open_timeout=5) as recipient:
        assert ready_frame(sender)['email'] == a
        assert ready_frame(recipient)['email'] == b
        # Initial presence may be queued; drain it through the actual protocol.
        def chat_frame(socket):
            for _ in range(10):
                frame = json.loads(socket.recv(timeout=5))
                if frame['type'] == 'chat':
                    return frame
            raise AssertionError('No actual chat frame')
        sender.send(json.dumps({'type': 'chat', 'to': b, 'body': 'allowed-before-block', 'client_id': 'before'}))
        assert chat_frame(recipient)['body'] == 'allowed-before-block'
        assert chat_frame(sender)['self'] is True
        assert client.post('/api/safety/blocks', headers=headers(second), json={'email': a}).status_code == 200
        for token, peer in [(first, b), (second, a)]:
            assert client.get('/api/chat/history', headers=headers(token), params={'peer': peer}).status_code == 403
            assert client.get('/api/friends', headers=headers(token)).json()['friends'] == []
            assert client.post('/api/voice/direct/token', headers=headers(token), json={'peer': peer}).status_code == 403
        assert client.post('/api/friends/request', headers=headers(first), json={'email': b}).status_code == 404
        sender.send(json.dumps({'type': 'chat', 'to': b, 'body': 'forbidden-after-block', 'client_id': 'after'}))
        assert json.loads(sender.recv(timeout=5))['type'] == 'error'
        for frame in [{'type': 'typing', 'to': b}, {'type': 'call_decline', 'to': b, 'room': 'private-room'},
                      {'type': 'call_invite', 'to': b, 'room': 'private-room'}]:
            sender.send(json.dumps(frame))
        with pytest.raises(TimeoutError):
            recipient.recv(timeout=0.2)
        assert recipient.ping().wait(timeout=2), 'Filtered content must not close healthy recipient'
        with database() as conn, conn.cursor() as cur:
            cur.execute('SELECT body FROM chat_messages WHERE sender=%s AND recipient=%s ORDER BY id', (a, b))
            assert cur.fetchall() == [('allowed-before-block',)]
        assert client.post('/api/safety/unblock', headers=headers(second), json={'email': a}).status_code == 200
        history = client.get('/api/chat/history', headers=headers(first), params={'peer': b})
        assert history.status_code == 200 and history.json()['messages'][0]['body'] == 'allowed-before-block'


def test_group_history_and_live_delivery_filter_only_blocked_author_and_allow_report(social_service):
    client, database, _ = social_service
    first, a = native_session(client)
    second, b = native_session(client)
    third, c = native_session(client)
    gid = 'safety-' + a.split('@')[0]
    with database() as conn, conn.cursor() as cur:
        cur.execute('INSERT INTO voice_groups(id,owner,join_code) VALUES(%s,%s,%s)', (gid, a, a[:12]))
        for email in [a, b, c]:
            cur.execute('INSERT INTO voice_group_members(group_id,email) VALUES(%s,%s)', (gid, email))
        cur.execute('INSERT INTO group_messages(group_id,sender,body) VALUES(%s,%s,%s) RETURNING id', (gid, a, 'blocked-author'))
        mid = cur.fetchone()[0]
        cur.execute('INSERT INTO group_messages(group_id,sender,body) VALUES(%s,%s,%s)', (gid, c, 'visible-author'))
    assert client.post('/api/safety/blocks', headers=headers(second), json={'email': a}).status_code == 200
    history = client.get(f'/api/groups/{gid}/chat', headers=headers(second))
    assert [m['body'] for m in history.json()['messages']] == ['visible-author']
    assert client.post('/api/safety/reports', headers=headers(second), json={
        'resource_type': 'group_message', 'resource_id': mid, 'category': 'harassment'}).json()['status'] == 'review_pending'
    stranger, _ = native_session(client)
    assert client.post('/api/safety/reports', headers=headers(stranger), json={
        'resource_type': 'group_message', 'resource_id': mid, 'category': 'harassment'}).status_code == 404
    with connect(issue(client, second), open_timeout=5) as ws:
        assert json.loads(ws.recv(timeout=5))['type'] == 'ready'
        assert client.post(f'/api/groups/{gid}/chat', headers=headers(first), json={'body': 'must-filter'}).status_code == 200
        assert client.post(f'/api/groups/{gid}/chat', headers=headers(third), json={'body': 'must-deliver'}).status_code == 200
        frame = json.loads(ws.recv(timeout=5))
        assert frame['type'] == 'group_chat' and frame['message']['body'] == 'must-deliver'
        assert ws.ping().wait(timeout=2)


def test_blocked_pair_cannot_persist_chat_even_if_earlier_friend_check_was_valid(social_service):
    client, database, _ = social_service
    first, a = native_session(client)
    second, b = native_session(client)
    make_friends(database, a, b)
    with database() as conn, conn.cursor() as cur:
        assert realtime._are_friends(cur, a, b)
    assert client.post('/api/safety/blocks', headers=headers(second), json={'email': a}).status_code == 200
    # Real persistence independently rechecks under the same pair transaction
    # lock as block insertion, closing the earlier-check/later-write race.
    assert realtime._persist_message(a, b, 'must-not-persist', 'text', 'late', False) is None
    with database() as conn, conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM chat_messages WHERE sender=%s AND recipient=%s', (a, b))
        assert cur.fetchone()[0] == 0


@pytest.fixture
def local_jwt_configuration(monkeypatch):
    import uuid
    # Isolated cryptographic integration only. No provider/network request and
    # no existing account credentials are read or used.
    secret = uuid.uuid4().hex + uuid.uuid4().hex
    monkeypatch.setenv('LIVEKIT_URL', 'wss://local-jwt-test.invalid')
    monkeypatch.setenv('LIVEKIT_API_KEY', 'local-test-issuer')
    monkeypatch.setenv('LIVEKIT_API_SECRET', secret)
    monkeypatch.setenv('LIVEKIT_TOKEN_TTL', '60')
    monkeypatch.setenv('LIVEKIT_E2EE', 'true')
    return secret


def test_direct_room_jwt_and_e2ee_are_bound_to_actual_participant_pair(social_service, local_jwt_configuration):
    import jwt
    client, database, _ = social_service
    first, a = native_session(client)
    second, b = native_session(client)
    _, c = native_session(client)
    make_friends(database, a, b)
    make_friends(database, a, c)
    created = client.post('/api/voice/direct/token', headers=headers(first), json={'peer': b})
    assert created.status_code == 200
    room = created.json()['room']
    claims = jwt.decode(created.json()['token'], local_jwt_configuration,
                        algorithms=['HS256'], issuer='local-test-issuer')
    assert claims['sub'] == a and claims['video']['room'] == room
    assert 0 < claims['exp'] - claims['iat'] <= 60
    with database() as conn, conn.cursor() as cur:
        cur.execute('SELECT user_low,user_high,expires_at>NOW() FROM direct_voice_rooms WHERE id=%s', (room,))
        assert cur.fetchone() == (*sorted([a, b]), True)
    accepted = client.post('/api/voice/direct/token', headers=headers(second), json={'peer': a, 'room': room})
    assert accepted.status_code == 200 and accepted.json()['e2ee_key'] == created.json()['e2ee_key']
    assert client.post('/api/safety/blocks', headers=headers(second), json={'email': a}).status_code == 200
    # Supplying another valid friend must not authorize the previously known AB room.
    spoof = client.post('/api/voice/direct/token', headers=headers(first), json={'peer': c, 'room': room})
    assert spoof.status_code == 403 and 'token' not in spoof.json() and 'e2ee_key' not in spoof.json()
    assert client.post('/api/voice/direct/token', headers=headers(first), json={'peer': b, 'room': room}).status_code == 403


def test_unregistered_or_expired_room_never_grants_credentials(social_service, local_jwt_configuration):
    client, database, _ = social_service
    first, a = native_session(client)
    _, b = native_session(client)
    make_friends(database, a, b)
    assert client.post('/api/voice/direct/token', headers=headers(first), json={'peer': b, 'room': 'vd_unregistered'}).status_code == 403
    created = client.post('/api/voice/direct/token', headers=headers(first), json={'peer': b})
    room = created.json()['room']
    with database() as conn, conn.cursor() as cur:
        cur.execute("UPDATE direct_voice_rooms SET expires_at=NOW()-INTERVAL '1 second' WHERE id=%s", (room,))
    assert client.post('/api/voice/direct/token', headers=headers(first), json={'peer': b, 'room': room}).status_code == 403


@pytest.mark.parametrize('invalidity', ['expired', 'revoked', 'banned'])
def test_voice_rejects_invalid_warm_cached_session(social_service, local_jwt_configuration, invalidity):
    client, database, namespace = social_service
    first, a = native_session(client)
    _, b = native_session(client)
    make_friends(database, a, b)
    assert first in namespace['_SESSION_STORE']
    with database() as conn, conn.cursor() as cur:
        if invalidity == 'expired':
            cur.execute("UPDATE user_tokens SET expires_at=NOW()-INTERVAL '1 second' WHERE token=%s", (first,))
        elif invalidity == 'revoked':
            cur.execute('DELETE FROM user_tokens WHERE token=%s', (first,))
        else:
            cur.execute('UPDATE users SET is_banned=TRUE WHERE email=%s', (a,))
    response = client.post('/api/voice/direct/token', headers=headers(first), json={'peer': b})
    assert response.status_code == 401 and 'token' not in response.json()


def test_signaling_room_join_rejects_guessed_room_and_filters_blocked_peers(social_service):
    client, database, _ = social_service
    first, a = native_session(client)
    second, b = native_session(client)
    third, c = native_session(client)
    outsider, _ = native_session(client)
    gid = 'room-' + a[:16]
    with database() as conn, conn.cursor() as cur:
        cur.execute('INSERT INTO voice_groups(id,owner,join_code) VALUES(%s,%s,%s)', (gid, a, a[:12]))
        for email in [a, b, c]:
            cur.execute('INSERT INTO voice_group_members(group_id,email) VALUES(%s,%s)', (gid, email))
    room = 'vg_' + gid
    with connect(issue(client, first), open_timeout=5) as wa, connect(issue(client, second), open_timeout=5) as wb, \
            connect(issue(client, third), open_timeout=5) as wc, connect(issue(client, outsider), open_timeout=5) as wo:
        for ws in [wa, wb, wc, wo]:
            ready_frame(ws)
        wa.send(json.dumps({'type': 'join_room', 'room': room}))
        assert json.loads(wa.recv(timeout=5))['peers'] == []
        wc.send(json.dumps({'type': 'join_room', 'room': room}))
        assert json.loads(wc.recv(timeout=5))['peers'] == [a]
        assert json.loads(wa.recv(timeout=5))['type'] == 'peer_joined'
        assert client.post('/api/safety/blocks', headers=headers(second), json={'email': a}).status_code == 200
        wb.send(json.dumps({'type': 'join_room', 'room': room}))
        peers = json.loads(wb.recv(timeout=5))
        assert peers['type'] == 'room_peers' and peers['peers'] == [c]
        wo.send(json.dumps({'type': 'join_room', 'room': room}))
        assert json.loads(wo.recv(timeout=5))['code'] == 'room_unavailable'
        # B must not receive signaling from blocked A even inside a shared group.
        wa.send(json.dumps({'type': 'offer', 'to': b, 'room': room, 'sdp': 'must-not-deliver'}))
        with pytest.raises(TimeoutError):
            wb.recv(timeout=0.2)
        assert wb.ping().wait(timeout=2)
