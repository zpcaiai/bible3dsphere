"""Exercise the mission router through live HTTP and an isolated PostgreSQL schema."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import uuid

from fastapi import FastAPI
import httpx
import psycopg2
from psycopg2 import sql
import pytest

from mission_feature_guard import init_mission_feature_guard
from routers.mission_organizations import init_mission_organizations_router, router


BACKEND = Path(__file__).resolve().parents[1]
ORG = 'parity-profile'
OTHER_ORG = 'parity-other'
OWNER = 'profile-owner@example.test'
VIEWER = 'profile-viewer@example.test'


def build_profile_app(dsn, schema, auth_url):
    def database():
        return psycopg2.connect(dsn, options=f'-csearch_path={schema}')

    def session(request):
        response = httpx.get(
            f'{auth_url}/api/auth/me',
            headers={'Authorization': request.headers.get('Authorization', '')},
            timeout=5,
        )
        if response.is_success:
            return response.json().get('user')
        return None

    init_mission_feature_guard(
        get_db=database, release_db=psycopg2.extensions.connection.close,
        get_session_user=session,
    )
    init_mission_organizations_router(
        get_db=database, release_db=psycopg2.extensions.connection.close,
        get_session_user=session,
        is_admin=lambda email: False,  # Exercise the production organization RBAC path.
    )
    app = FastAPI()
    app.include_router(router)
    return app


def _account(auth_url, email):
    with httpx.Client(base_url=auth_url, timeout=10) as client:
        code = client.post('/api/auth/email/send-code', json={'email': email})
        code.raise_for_status()
        response = client.post('/api/auth/email/register', json={
            'email': email, 'code': code.json()['dev_code'],
            'nickname': email.split('@')[0], 'password': 'LocalFixture!184',
            'session_transport': 'bearer',
        })
        response.raise_for_status()
        return {'Authorization': f"Bearer {response.json()['token']}"}


@contextmanager
def profile_fixture(directory):
    dsn = os.environ['NATIVE_AUTH_TEST_DSN']
    auth_url = os.environ['NATIVE_AUTH_BASE_URL']
    schema = 'profile_' + uuid.uuid4().hex
    with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    try:
        with psycopg2.connect(dsn, options=f'-csearch_path={schema}') as conn, conn.cursor() as cur:
            for filename in (
                '0122_productization.sql', '0156_mission_os_feature_flags.sql',
                '0160_mission_os_audit_lineage.sql', '0169_mission_os_organizations.sql',
            ):
                cur.execute((BACKEND / 'migrations' / filename).read_text())
            cur.execute("UPDATE mission_feature_flags SET default_value=TRUE WHERE key='mission_os_enabled'")
            cur.executemany(
                'INSERT INTO organizations(id,name,owner_email) VALUES (%s,%s,%s)',
                [(ORG, 'Profile church', OWNER), (OTHER_ORG, 'Other church', VIEWER)],
            )
            cur.executemany(
                'INSERT INTO organization_memberships(id,organization_id,email,role_key) VALUES (%s,%s,%s,%s)',
                [('owner', ORG, OWNER, 'owner'), ('viewer', ORG, VIEWER, 'viewer')],
            )
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        base = f'http://127.0.0.1:{port}'
        directory = Path(directory)
        with (directory / 'mission-profile-http.log').open('wb') as log:
            process = subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), str(port), schema],
                stdout=log, stderr=subprocess.STDOUT,
                env={**os.environ, 'MISSION_OS_ENABLED': '1', 'MISSION_EMERGENCY_OFF': '0'},
            )
            try:
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    assert process.poll() is None, 'Profile HTTP server exited'
                    try:
                        if httpx.get(f'{base}/openapi.json', timeout=1).is_success:
                            break
                    except httpx.TransportError:
                        time.sleep(0.1)
                else:
                    raise AssertionError('Profile HTTP server did not start')
                yield base, schema, process.pid, _account(auth_url, OWNER), _account(auth_url, VIEWER)
            finally:
                process.terminate()
                process.wait(timeout=15)
    finally:
        with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
            cur.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


def test_profile_updates_preserve_omitted_fields_and_tenant_authority(tmp_path):
    with profile_fixture(tmp_path) as (base, schema, pid, owner, viewer):
        assert pid > 0
        org = f'{base}/api/v1/mission/organizations/{ORG}'
        endpoint = f'{org}/profile'
        with httpx.Client(timeout=10) as client:
            assert client.patch(endpoint, json={'legalName': 'denied'}).status_code == 401
            assert client.patch(endpoint, headers=viewer, json={'legalName': 'denied'}).status_code == 403
            assert client.patch(endpoint, headers=owner, json={'legalName': 'missing kind'}).status_code == 409
            created = client.put(endpoint, headers=owner, json={
                'organizationKind': 'church', 'legalName': 'Initial', 'countryCode': 'cn',
                'safeguardingContactUserId': 'contact-before', 'dataResidencyRegion': 'region-before',
            })
            created.raise_for_status()
            assert created.json() == {'ok': True, 'organizationId': ORG}
            client.put(endpoint, headers=owner, json={'organizationKind': 'church', 'legalName': 'Legacy caller'}).raise_for_status()

        with ThreadPoolExecutor(max_workers=2) as pool:
            def patch(payload):
                response = httpx.patch(endpoint, headers=owner, json=payload, timeout=10)
                response.raise_for_status()
            writes = [
                pool.submit(patch, {'legalName': 'Concurrent name'}),
                pool.submit(patch, {'dataResidencyRegion': 'region-new'}),
            ]
            for write in writes:
                write.result()
        assert httpx.patch(endpoint, headers=owner, json={'countryCode': None}).is_success
        assert httpx.patch(endpoint, headers=owner, json={'organizationKind': None}).status_code == 422
        assert httpx.patch(endpoint, headers=owner, json={'countryCode': '7X'}).status_code == 422
        assert httpx.patch(
            f'{base}/api/v1/mission/organizations/{OTHER_ORG}/profile', headers=owner,
            json={'organizationKind': 'church'},
        ).status_code == 403
        response = httpx.get(org, headers=owner)
        response.raise_for_status()
        assert response.json()['profilePatchSupported'] is True
        assert response.json()['organization']['legalName'] == 'Concurrent name'
        assert response.json()['organization']['countryCode'] is None
        with psycopg2.connect(
            os.environ['NATIVE_AUTH_TEST_DSN'], options=f'-csearch_path={schema}',
        ) as conn, conn.cursor() as cur:
            cur.execute(
                'SELECT organization_id, legal_name, country_code, safeguarding_contact_user_id, '
                'data_residency_region FROM mission_organization_profiles ORDER BY organization_id'
            )
            row = cur.fetchall()
            assert row == [(ORG, 'Concurrent name', None, 'contact-before', 'region-new')]
            cur.execute(
                'SELECT field_names_changed FROM mission_audit_logs WHERE resource_id=%s',
                (ORG,),
            )
            assert sorted(tuple(fields) for (fields,) in cur.fetchall()) == sorted([
                ('country_code', 'data_residency_region', 'legal_name', 'organization_kind', 'safeguarding_contact_user_id'),
                ('legal_name', 'organization_kind'), ('legal_name',),
                ('data_residency_region',), ('country_code',),
            ])
        print(json.dumps({'profile_http_pid': pid, 'row': row, 'concurrent_requests': len(writes)}))


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(
        build_profile_app(os.environ['NATIVE_AUTH_TEST_DSN'], sys.argv[2], os.environ['NATIVE_AUTH_BASE_URL']),
        host='127.0.0.1', port=int(sys.argv[1]),
    )
