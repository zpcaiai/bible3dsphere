"""Real PostgreSQL proof that content blocking does not disclose hidden authors."""
import uuid

import pytest

from test_public_safety import public_service, social_service, ws_service, service, isolated_rate_limits, actors, post
from test_social_safety import native_session, headers


@pytest.mark.parametrize('kind', ['prayer', 'testimony', 'community_post'])
def test_content_block_uses_opaque_owner_record_and_filters_author_without_exposing_email(public_service, kind):
    client, database, _ = public_service
    token, viewer, author, other, churches = actors(public_service)
    with database() as conn, conn.cursor() as cur:
        if kind == 'prayer':
            cur.execute('INSERT INTO prayers(email,content,church_id,is_public,is_anonymous) VALUES(%s,%s,%s,TRUE,TRUE) RETURNING id',
                        (author, 'anonymous content', churches[0]))
        elif kind == 'testimony':
            cur.execute('INSERT INTO testimonies(email,church_id,is_public,is_anonymous) VALUES(%s,%s,TRUE,TRUE) RETURNING id', (author, churches[0]))
        else:
            cur.execute('INSERT INTO community_posts(email,church_id,is_public) VALUES(%s,%s,TRUE) RETURNING id', (author, churches[0]))
        rid = cur.fetchone()[0]
    payload = {'resource_type': kind, 'resource_id': rid}
    for _ in range(2):
        response = client.post('/api/safety/blocks/from-content', headers=headers(token), json=payload)
        assert response.status_code == 200 and response.json() == {'blocked': True}
        assert author not in response.text
    listed = client.get('/api/safety/blocks', headers=headers(token))
    assert author not in listed.text and listed.json()['blocked'] == []
    record = listed.json()['items'][0]
    uuid.UUID(record['id'])
    assert record['label'] == ''
    with database() as conn, conn.cursor() as cur:
        cur.execute('SELECT blocked_email,identity_known FROM user_blocks WHERE id=%s AND blocker_email=%s', (record['id'], viewer))
        assert cur.fetchone() == (author, False)
    path = {'prayer': '/api/prayers', 'testimony': '/api/testimonies', 'community_post': '/api/community/feed'}[kind]
    assert rid not in [item['id'] for item in client.get(path, headers=headers(token)).json()['items']]
    # Guessing an email cannot remove a hidden-identity block.
    assert client.post('/api/safety/unblock', headers=headers(token), json={'email': author}).status_code == 200
    assert len(client.get('/api/safety/blocks', headers=headers(token)).json()['items']) == 1
    stranger, _ = native_session(client)
    assert client.post('/api/safety/unblock-record', headers=headers(stranger), json={'id': record['id']}).status_code == 200
    assert len(client.get('/api/safety/blocks', headers=headers(token)).json()['items']) == 1
    assert client.post('/api/safety/unblock-record', headers=headers(token), json={'id': record['id']}).status_code == 200
    assert client.get('/api/safety/blocks', headers=headers(token)).json()['items'] == []
    assert rid in [item['id'] for item in client.get(path, headers=headers(token)).json()['items']]


def test_block_by_content_rejects_other_church_hidden_and_self(public_service):
    client, database, _ = public_service
    token, viewer, author, other, churches = actors(public_service)
    hidden = post(database, other, churches[1], False, 'hidden')
    own = post(database, viewer, churches[0], True, 'self')
    assert client.post('/api/safety/blocks/from-content', headers=headers(token), json={
        'resource_type': 'community_post', 'resource_id': hidden}).status_code == 404
    assert client.post('/api/safety/blocks/from-content', headers=headers(token), json={
        'resource_type': 'community_post', 'resource_id': own}).status_code == 400
    assert client.get('/api/safety/blocks', headers=headers(token)).json()['items'] == []


def test_explicit_known_email_blocks_keep_compatible_list_and_can_use_opaque_unblock(public_service):
    client, database, _ = public_service
    token, viewer, author, other, churches = actors(public_service)
    assert client.post('/api/safety/blocks', headers=headers(token), json={'email': author}).status_code == 200
    listed = client.get('/api/safety/blocks', headers=headers(token)).json()
    assert listed['blocked'] == [author] and listed['items'][0]['label'] == author
    assert client.post('/api/safety/unblock-record', headers=headers(token), json={'id': listed['items'][0]['id']}).status_code == 200
    assert client.get('/api/safety/blocks', headers=headers(token)).json()['blocked'] == []


@pytest.mark.parametrize('actual_candidate', [True, False])
def test_known_and_content_block_lists_do_not_expose_pair_conflict(public_service, actual_candidate):
    client, database, _ = public_service
    token, viewer, author, other, churches = actors(public_service)
    rid = post(database, author, churches[0], True, 'anonymous-context-reference')
    content = {'resource_type': 'community_post', 'resource_id': rid}
    assert client.post('/api/safety/blocks/from-content', headers=headers(token), json=content).status_code == 200
    original = client.get('/api/safety/blocks', headers=headers(token)).json()['items'].copy()
    candidate = author if actual_candidate else other
    for _ in range(2):
        assert client.post('/api/safety/blocks', headers=headers(token), json={'email': candidate}).status_code == 200
        data = client.get('/api/safety/blocks', headers=headers(token)).json()
        assert len(data['items']) == 2
        assert sorted(item['label'] for item in data['items']) == ['', candidate]
        assert data['blocked'] == [candidate]
        assert original[0] in data['items']
    assert client.post('/api/safety/unblock', headers=headers(token), json={'email': candidate}).status_code == 200
    assert client.get('/api/safety/blocks', headers=headers(token)).json()['items'] == original
    with database() as conn, conn.cursor() as cur:
        from backend.routers.realtime import users_blocked
        assert users_blocked(cur, viewer, author)


def test_reverse_order_and_distinct_content_sources_remain_independent(public_service):
    client, database, _ = public_service
    token, viewer, author, other, churches = actors(public_service)
    first = post(database, author, churches[0], True, 'source one')
    second = post(database, author, churches[0], True, 'source two')
    assert client.post('/api/safety/blocks', headers=headers(token), json={'email': author}).status_code == 200
    for rid in [first, second]:
        assert client.post('/api/safety/blocks/from-content', headers=headers(token), json={
            'resource_type': 'community_post', 'resource_id': rid}).status_code == 200
    records = client.get('/api/safety/blocks', headers=headers(token)).json()['items']
    assert len(records) == 3 and sum(item['label'] == '' for item in records) == 2
    hidden = next(item for item in records if item['label'] == '')
    assert client.post('/api/safety/unblock-record', headers=headers(token), json={'id': hidden['id']}).status_code == 200
    assert len(client.get('/api/safety/blocks', headers=headers(token)).json()['items']) == 2
    assert client.post('/api/safety/unblock', headers=headers(token), json={'email': author}).status_code == 200
    assert len(client.get('/api/safety/blocks', headers=headers(token)).json()['items']) == 1
    with database() as conn, conn.cursor() as cur:
        from backend.routers.realtime import users_blocked
        assert users_blocked(cur, viewer, author)
    assert client.post('/api/safety/blocks/from-content', headers=headers(token), json={
        'resource_type': 'community_post', 'resource_id': 2**80}).status_code == 422
