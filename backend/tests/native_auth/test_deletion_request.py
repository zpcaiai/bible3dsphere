"""Deletion initiation uses real production password/SQL/HTTP boundaries."""
from pathlib import Path

from test_mobile_contract import service, register, isolated_rate_limits


def install(database):
    sql = Path(__file__).resolve().parents[2] / 'migrations/0246_account_deletion_requests.sql'
    with database() as conn, conn.cursor() as cur:
        cur.execute(sql.read_text())


def expected_id(database, email):
    with database() as conn, conn.cursor() as cur:
        cur.execute('SELECT id FROM users WHERE email=%s', (email,))
        return str(cur.fetchone()[0])


def test_reauth_and_atomic_existing_session_revocation(service):
    client, database, namespace = service
    install(database)
    client.cookies.clear()
    response, account = register(client, 'bearer')
    token = response.json()['token']
    client.cookies.clear()
    second = client.post('/api/auth/email/login', json={
        'email': account['email'], 'password': account['password'], 'session_transport': 'bearer'}).json()['token']
    client.cookies.clear()
    payload = {'password': 'incorrect', 'confirmation': 'REQUEST_ACCOUNT_DELETION',
               'expected_user_id': expected_id(database, account['email'])}
    headers = {'Authorization': f'Bearer {token}'}
    assert client.post('/api/auth/account-deletion', json=payload, headers=headers).status_code == 401
    with database() as conn, conn.cursor() as cur:
        cur.execute('SELECT count(*) FROM account_deletion_requests'); assert cur.fetchone()[0] == 0
        cur.execute('SELECT count(*) FROM user_tokens WHERE email=%s', (account['email'],)); assert cur.fetchone()[0] == 2
    payload['password'] = account['password']
    result = client.post('/api/auth/account-deletion', json=payload, headers=headers)
    assert result.status_code == 202
    assert result.headers['cache-control'] == 'no-store'
    assert result.json()['status'] == 'pending_review'
    assert result.json()['deletion_completed'] is False
    with database() as conn, conn.cursor() as cur:
        cur.execute('SELECT count(*) FROM user_tokens WHERE email=%s', (account['email'],)); assert cur.fetchone()[0] == 0
        cur.execute('SELECT count(*) FROM users WHERE email=%s', (account['email'],)); assert cur.fetchone()[0] == 1
    assert token not in namespace['_SESSION_STORE'] and second not in namespace['_SESSION_STORE']
    assert client.post('/api/auth/account-deletion', json=payload, headers=headers).status_code == 401
    assert client.get('/api/auth/me', headers={'Authorization': f'Bearer {second}'}).status_code == 401


def test_transaction_failure_preserves_sessions_and_no_false_receipt(service):
    client, database, namespace = service
    install(database); client.cookies.clear()
    response, account = register(client, 'bearer'); token = response.json()['token']; client.cookies.clear()
    with database() as conn, conn.cursor() as cur:
        cur.execute("CREATE FUNCTION reject_deletion_tokens() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'task failure injection'; END $$")
        cur.execute('CREATE TRIGGER reject_deletion_tokens BEFORE DELETE ON user_tokens FOR EACH ROW EXECUTE FUNCTION reject_deletion_tokens()')
    result = client.post('/api/auth/account-deletion', json={
        'password': account['password'], 'confirmation': 'REQUEST_ACCOUNT_DELETION',
        'expected_user_id': expected_id(database, account['email'])},
        headers={'Authorization': f'Bearer {token}'})
    assert result.status_code == 500
    with database() as conn, conn.cursor() as cur:
        cur.execute('SELECT count(*) FROM account_deletion_requests WHERE user_id=(SELECT id FROM users WHERE email=%s)', (account['email'],)); assert cur.fetchone()[0] == 0
        cur.execute('SELECT count(*) FROM user_tokens WHERE token=%s', (token,)); assert cur.fetchone()[0] == 1
        cur.execute('DROP TRIGGER reject_deletion_tokens ON user_tokens'); cur.execute('DROP FUNCTION reject_deletion_tokens()')
    assert token in namespace['_SESSION_STORE']


def test_stale_cache_expiry_and_ban_cannot_request_deletion(service):
    client, database, namespace = service
    install(database)
    for mutation in ['expired', 'banned', 'revoked']:
        client.cookies.clear(); response, account = register(client, 'bearer')
        token = response.json()['token']; client.cookies.clear()
        with database() as conn, conn.cursor() as cur:
            if mutation == 'expired': cur.execute("UPDATE user_tokens SET expires_at=NOW()-INTERVAL '1 second' WHERE token=%s", (token,))
            elif mutation == 'banned': cur.execute('UPDATE users SET is_banned=TRUE WHERE email=%s', (account['email'],))
            else: cur.execute('DELETE FROM user_tokens WHERE token=%s', (token,))
        assert token in namespace['_SESSION_STORE']
        result = client.post('/api/auth/account-deletion', json={'password': account['password'],
            'confirmation': 'REQUEST_ACCOUNT_DELETION', 'expected_user_id': expected_id(database, account['email'])}, headers={'Authorization': f'Bearer {token}'})
        assert result.status_code == 401


def test_reauthenticated_repeat_keeps_one_durable_request(service):
    client, database, namespace = service
    install(database); client.cookies.clear()
    response, account = register(client, 'bearer'); token = response.json()['token']; client.cookies.clear()
    payload = {'password': account['password'], 'confirmation': 'REQUEST_ACCOUNT_DELETION',
               'expected_user_id': expected_id(database, account['email'])}
    first = client.post('/api/auth/account-deletion', json=payload, headers={'Authorization': f'Bearer {token}'})
    assert first.status_code == 202
    login = client.post('/api/auth/email/login', json={'email': account['email'],
        'password': account['password'], 'session_transport': 'bearer'})
    client.cookies.clear()
    second = client.post('/api/auth/account-deletion', json=payload,
        headers={'Authorization': f"Bearer {login.json()['token']}"})
    assert second.status_code == 202
    assert first.json()['request_id'] == second.json()['request_id']


def test_cookie_precedence_and_confirmation_are_enforced(service):
    client, database, namespace = service
    install(database); client.cookies.clear()
    a, account_a = register(client, 'bearer'); token_a = a.json()['token']; client.cookies.clear()
    b, account_b = register(client, 'bearer'); token_b = b.json()['token']
    # Cookie B wins over Bearer A; A's password cannot delete B's sessions.
    payload = {'password': account_a['password'], 'confirmation': 'wrong',
               'expected_user_id': expected_id(database, account_b['email'])}
    headers = {'Authorization': f'Bearer {token_a}'}
    assert client.post('/api/auth/account-deletion', json=payload, headers=headers).status_code == 422
    payload['confirmation'] = 'REQUEST_ACCOUNT_DELETION'
    payload['password'] = 'incorrect'
    assert client.post('/api/auth/account-deletion', json=payload, headers=headers).status_code == 401
    payload['password'] = account_b['password']
    assert client.post('/api/auth/account-deletion', json=payload, headers=headers).status_code == 202
    with database() as conn, conn.cursor() as cur:
        cur.execute('SELECT token FROM user_tokens WHERE token IN (%s,%s)', (token_a, token_b))
        assert cur.fetchall() == [(token_a,)]


def test_cross_tab_cookie_switch_rejects_original_account_intent(service):
    client, database, namespace = service
    install(database); client.cookies.clear()
    a, account_a = register(client, 'bearer'); token_a = a.json()['token']; client.cookies.clear()
    b, account_b = register(client, 'bearer'); token_b = b.json()['token']
    assert account_a['password'] == account_b['password']
    payload = {'password': account_a['password'], 'confirmation': 'REQUEST_ACCOUNT_DELETION',
               'expected_user_id': str(a.json()['user']['id'])}
    result = client.post('/api/auth/account-deletion', json=payload)
    assert result.status_code == 409
    with database() as conn, conn.cursor() as cur:
        cur.execute('SELECT count(*) FROM user_tokens WHERE token IN (%s,%s)', (token_a, token_b)); assert cur.fetchone()[0] == 2
        cur.execute('SELECT count(*) FROM account_deletion_requests WHERE user_id IN (%s,%s)',
                    (a.json()['user']['id'], b.json()['user']['id'])); assert cur.fetchone()[0] == 0
