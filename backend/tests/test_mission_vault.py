from __future__ import annotations
import base64,json
from datetime import datetime,timedelta,timezone
import pytest
from mission_os import vault

def env():
    key=base64.urlsafe_b64encode(bytes(range(32))).decode()
    return {'MISSION_VAULT_KEYS':json.dumps({'v1':key}),'MISSION_VAULT_ACTIVE_KEY':'v1'}

def test_aes_gcm_round_trip_and_context_binding():
    ad=vault.aad(tenant_id='t1',resource_type='credential',resource_id='c1',field_name='identifier')
    item=vault.encrypt(b'P12345678',associated_data=ad,env=env())
    assert item.ciphertext!=b'P12345678'
    assert vault.decrypt(item,associated_data=ad,env=env())==b'P12345678'
    with pytest.raises(Exception):vault.decrypt(item,associated_data=ad+b'other',env=env())

def test_keyring_fails_closed_and_unknown_version_fails():
    with pytest.raises(RuntimeError):vault.load_keyring({})
    ad=b'a';item=vault.encrypt(b'secret',associated_data=ad,env=env())
    bad=vault.Envelope('retired',item.nonce,item.ciphertext,item.sha256)
    with pytest.raises(RuntimeError):vault.decrypt(bad,associated_data=ad,env=env())

def test_file_limits_and_secure_session():
    with pytest.raises(ValueError):vault.validate_file(b'')
    now=datetime.now(timezone.utc)
    assert vault.secure_session_valid(user_id='u',session_user_id='u',purpose='credential_download',expires_at=now+timedelta(minutes=1),revoked_at=None,now=now)
    assert not vault.secure_session_valid(user_id='u',session_user_id='x',purpose='credential_download',expires_at=now+timedelta(minutes=1),revoked_at=None,now=now)

def test_vault_migration_and_router_contracts():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    sql=(root/'migrations/0207_mission_os_encrypted_vault.sql').read_text()
    assert all(x in sql for x in ('mission_vault_secrets','mission_vault_files','mission_vault_access_grants','ENABLE ROW LEVEL SECURITY'))
    routes={(r.path,','.join(sorted(r.methods or []))) for r in __import__('routers.mission_deployment',fromlist=['credential_router']).credential_router.routes}
    assert ('/api/v1/mission/credentials/vault-session','POST') in routes
    assert ('/api/v1/mission/credentials/{credential_id}/secure-file','GET') in routes
