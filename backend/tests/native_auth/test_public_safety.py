"""Actual public/tenant content visibility and block/report integration."""
import ast
from pathlib import Path
import uuid

import pytest

from backend.routers import community_feed, prayer, testimony
from test_social_safety import social_service, ws_service, service, isolated_rate_limits, native_session, headers


@pytest.fixture(scope='module')
def public_service(social_service):
    client, database, namespace = social_service
    root = Path(__file__).resolve().parents[2]
    tree = ast.parse((root / 'db_schema.py').read_text())
    statements = [n.args[0].value for n in ast.walk(tree) if isinstance(n, ast.Call)
                  and isinstance(n.func, ast.Attribute) and n.func.attr == 'execute' and n.args
                  and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str)]
    with database() as conn, conn.cursor() as cur:
        cur.execute(next(s for s in statements if 'CREATE TABLE IF NOT EXISTS prayers (' in s))
        cur.execute(next(s for s in statements if 'ADD COLUMN IF NOT EXISTS status VARCHAR' in s and 'ALTER TABLE prayers' in s))
        for name in ['0034_community_feed.sql', '0041_churches.sql', '0052_testimonies.sql']:
            cur.execute((root / 'migrations' / name).read_text())
    deps = dict(get_db=database, release_db=namespace['_release_db'],
                get_session_user=namespace['_get_session_user'], is_admin=namespace['_is_admin'],
                sanitize_text=lambda value: value, to_shanghai_iso=lambda value: value.isoformat() if value else None)
    # No generated content path is called: exact router visibility/SQL paths.
    community_feed.init_community_feed_router(**deps)
    prayer.init_prayer_router(**deps)
    testimony.init_testimony_router(**deps)
    for router in [community_feed.router, prayer.router, testimony.router]:
        namespace['app'].include_router(router)
    return client, database, namespace


def actors(public_service):
    client, database, _ = public_service
    token, viewer = native_session(client)
    _, author = native_session(client)
    _, other = native_session(client)
    with database() as conn, conn.cursor() as cur:
        churches = []
        for owner in [viewer, other]:
            cur.execute('INSERT INTO churches(name,owner_email,join_code) VALUES(%s,%s,%s) RETURNING id',
                        ('Safety test', owner, uuid.uuid4().hex[:12]))
            churches.append(cur.fetchone()[0])
        for email, cid in [(viewer, churches[0]), (author, churches[0]), (other, churches[1])]:
            cur.execute('INSERT INTO church_members(church_id,email) VALUES(%s,%s)', (cid, email))
    return token, viewer, author, other, churches


def post(database, author, cid, public, content):
    with database() as conn, conn.cursor() as cur:
        cur.execute('INSERT INTO community_posts(email,church_id,is_public,content) VALUES(%s,%s,%s,%s) RETURNING id',
                    (author, cid, public, content))
        return cur.fetchone()[0]


def test_reports_require_actual_public_or_same_church_content_and_comment_parent(public_service):
    client, database, _ = public_service
    token, viewer, author, other, churches = actors(public_service)
    visible = post(database, author, churches[0], False, 'same church')
    hidden = post(database, other, churches[1], False, 'other church secret')
    public = post(database, other, churches[1], True, 'public')
    for pid, status in [(visible, 200), (hidden, 404), (public, 200)]:
        response = client.post('/api/safety/reports', headers=headers(token), json={
            'resource_type': 'community_post', 'resource_id': pid, 'category': 'spam',
            'target_email': 'forged@example.test'})
        assert response.status_code == status
        assert 'other church secret' not in response.text
    with database() as conn, conn.cursor() as cur:
        cur.execute('INSERT INTO community_comments(post_id,email,content) VALUES(%s,%s,%s) RETURNING id', (hidden, other, 'private comment'))
        cid = cur.fetchone()[0]
    assert client.post('/api/safety/reports', headers=headers(token), json={
        'resource_type': 'community_comment', 'resource_id': cid, 'category': 'harassment'}).status_code == 404
    with database() as conn, conn.cursor() as cur:
        cur.execute('UPDATE community_posts SET is_public=TRUE WHERE id=%s', (hidden,))
    response = client.post('/api/safety/reports', headers=headers(token), json={
        'resource_type': 'community_comment', 'resource_id': cid, 'category': 'harassment'})
    assert response.status_code == 200
    with database() as conn, conn.cursor() as cur:
        cur.execute('SELECT target_email FROM social_reports WHERE id=%s', (response.json()['id'],))
        assert cur.fetchone()[0] == other
        cur.execute('UPDATE community_comments SET deleted_at=NOW() WHERE id=%s', (cid,))
    assert client.post('/api/safety/reports', headers=headers(token), json={
        'resource_type': 'community_comment', 'resource_id': cid, 'category': 'spam'}).status_code == 404


def test_block_filters_feed_before_pagination_counts_and_parent_actions(public_service):
    client, database, _ = public_service
    token, viewer, author, other, churches = actors(public_service)
    blocked = post(database, author, churches[0], True, 'blocked post')
    visible = post(database, other, churches[1], True, 'visible post')
    assert client.post('/api/safety/blocks', headers=headers(token), json={'email': author}).status_code == 200
    response = client.get('/api/community/feed', headers=headers(token), params={'limit': 1})
    assert response.status_code == 200 and response.json()['items'][0]['id'] == visible
    items = client.get('/api/community/feed', headers=headers(token)).json()
    assert blocked not in [p['id'] for p in items['items']]
    assert items['total'] == len(items['items'])
    assert client.get(f'/api/community/feed/{blocked}/comments', headers=headers(token)).status_code == 404
    assert client.post(f'/api/community/feed/{blocked}/comments', headers=headers(token), json={'content': 'blocked interaction'}).status_code == 404
    assert client.post(f'/api/community/feed/{blocked}/amen', headers=headers(token)).status_code == 404
    # Users can still report a previously encountered blocked public post.
    assert client.post('/api/safety/reports', headers=headers(token), json={
        'resource_type': 'community_post', 'resource_id': blocked, 'category': 'harassment'}).status_code == 200


def test_blocked_comment_author_is_filtered_on_other_visible_parent(public_service):
    client, database, _ = public_service
    token, viewer, author, other, churches = actors(public_service)
    parent = post(database, other, churches[1], True, 'public parent')
    with database() as conn, conn.cursor() as cur:
        for source in [author, other]:
            cur.execute('INSERT INTO community_comments(post_id,email,content) VALUES(%s,%s,%s)', (parent, source, source))
    assert client.post('/api/safety/blocks', headers=headers(token), json={'email': author}).status_code == 200
    comments = client.get(f'/api/community/feed/{parent}/comments', headers=headers(token))
    assert comments.status_code == 200 and [c['content'] for c in comments.json()['items']] == [other]


@pytest.mark.parametrize('kind', ['prayer', 'testimony'])
def test_reports_enforce_public_tenant_and_deleted_for_other_walls(public_service, kind):
    client, database, _ = public_service
    token, viewer, author, other, churches = actors(public_service)
    with database() as conn, conn.cursor() as cur:
        if kind == 'prayer':
            cur.execute('INSERT INTO prayers(email,content,church_id,is_public) VALUES(%s,%s,%s,FALSE) RETURNING id',
                        (other, 'private prayer', churches[1]))
        else:
            cur.execute('INSERT INTO testimonies(email,church_id,is_public) VALUES(%s,%s,FALSE) RETURNING id', (other, churches[1]))
        resource_id = cur.fetchone()[0]
    data = {'resource_type': kind, 'resource_id': resource_id, 'category': 'other'}
    assert client.post('/api/safety/reports', headers=headers(token), json=data).status_code == 404
    from psycopg2 import sql
    table = sql.Identifier('prayers' if kind == 'prayer' else 'testimonies')
    with database() as conn, conn.cursor() as cur:
        cur.execute(sql.SQL('UPDATE {} SET is_public=TRUE WHERE id=%s').format(table), (resource_id,))
    assert client.post('/api/safety/reports', headers=headers(token), json=data).status_code == 200
    with database() as conn, conn.cursor() as cur:
        cur.execute(sql.SQL('UPDATE {} SET deleted_at=NOW() WHERE id=%s').format(table), (resource_id,))
    assert client.post('/api/safety/reports', headers=headers(token), json=data).status_code == 404


@pytest.mark.parametrize('kind', ['prayer', 'testimony'])
def test_other_walls_filter_blocked_author_before_count_page_and_amen(public_service, kind):
    from psycopg2 import sql
    client, database, _ = public_service
    token, viewer, author, other, churches = actors(public_service)
    table = sql.Identifier('prayers' if kind == 'prayer' else 'testimonies')
    with database() as conn, conn.cursor() as cur:
        ids = []
        for source, church in [(author, churches[0]), (other, churches[1])]:
            if kind == 'prayer':
                cur.execute('INSERT INTO prayers(email,content,church_id,is_public,is_anonymous) VALUES(%s,%s,%s,TRUE,TRUE) RETURNING id',
                            (source, 'anonymous prayer', church))
            else:
                cur.execute('INSERT INTO testimonies(email,church_id,is_public,is_anonymous) VALUES(%s,%s,TRUE,TRUE) RETURNING id', (source, church))
            ids.append(cur.fetchone()[0])
    assert client.post('/api/safety/blocks', headers=headers(token), json={'email': author}).status_code == 200
    path = '/api/prayers' if kind == 'prayer' else '/api/testimonies'
    response = client.get(path, headers=headers(token))
    assert response.status_code == 200
    data = response.json()
    assert ids[0] not in [r['id'] for r in data['items']]
    assert ids[1] in [r['id'] for r in data['items']]
    assert data['total'] == len(data['items'])
    assert client.post(f'{path}/{ids[0]}/amen', headers=headers(token)).status_code == 404
    assert client.post(f'{path}/{ids[1]}/amen', headers=headers(token)).status_code == 200
    assert client.post('/api/safety/unblock', headers=headers(token), json={'email': author}).status_code == 200
    assert ids[0] in [r['id'] for r in client.get(path, headers=headers(token)).json()['items']]


def test_shared_anonymous_prayer_respects_authenticated_block_without_revealing_identity(public_service):
    client, database, _ = public_service
    token, viewer, author, other, churches = actors(public_service)
    share = uuid.uuid4().hex
    with database() as conn, conn.cursor() as cur:
        # Execute the exact existing production helper's idempotent DDL.
        prayer._ensure_share_column(cur)
        cur.execute('INSERT INTO prayers(email,content,church_id,is_public,is_anonymous,share_token) '
                    'VALUES(%s,%s,%s,TRUE,TRUE,%s) RETURNING id', (author, 'shared prayer', churches[0], share))
        pid = cur.fetchone()[0]
    assert client.post('/api/safety/blocks', headers=headers(token), json={'email': author}).status_code == 200
    assert client.get(f'/api/prayer-share/{share}', headers=headers(token)).status_code == 404
    assert client.post(f'/api/prayer-share/{share}/amen', headers=headers(token)).status_code == 404
    # An intentionally public capability remains available to a guest; identity
    # must remain absent even when the user is anonymous.
    client.cookies.clear()
    guest = client.get(f'/api/prayer-share/{share}')
    assert guest.status_code == 200 and 'email' not in guest.json() and author not in guest.text
    assert client.post('/api/safety/unblock', headers=headers(token), json={'email': author}).status_code == 200
    assert client.get(f'/api/prayer-share/{share}', headers=headers(token)).status_code == 200


@pytest.mark.parametrize('public', [False, True])
def test_anonymous_prayer_masks_identity_for_other_viewers_but_preserves_owner_controls(public_service, public):
    client, database, _ = public_service
    token, viewer, author, other, churches = actors(public_service)
    with database() as conn, conn.cursor() as cur:
        cur.execute('INSERT INTO prayers(email,nickname,content,church_id,is_public,is_anonymous) VALUES(%s,%s,%s,%s,%s,TRUE) RETURNING id',
                    (author, 'private-author-nickname', 'anonymous request', churches[0], public))
        pid = cur.fetchone()[0]
        cur.execute('SELECT token FROM user_tokens WHERE email=%s ORDER BY created_at DESC LIMIT 1', (author,))
        author_token = cur.fetchone()[0]
    same_church = client.get('/api/prayers', headers=headers(token))
    received = next(row for row in same_church.json()['items'] if row['id'] == pid)
    assert received['email'] == '' and received['nickname'] != 'private-author-nickname'
    assert received['is_anonymous'] is True and received['is_own'] is False
    own = client.get('/api/prayers', headers=headers(author_token))
    owned = next(row for row in own.json()['items'] if row['id'] == pid)
    assert owned['email'] == author and owned['nickname'] == 'private-author-nickname'
    assert owned['is_own'] is True and owned['is_anonymous'] is True
    if public:
        client.cookies.clear()
        guest = client.get('/api/prayers')
        row = next(item for item in guest.json()['items'] if item['id'] == pid)
        assert row['email'] == '' and row['nickname'] != 'private-author-nickname'
        assert row['is_anonymous'] is True
