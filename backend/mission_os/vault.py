"""AES-256-GCM ciphertext envelope helpers for Mission OS P3/P4 data.

Keys never enter the database.  ``MISSION_VAULT_KEYS`` is a JSON keyring whose
values are URL-safe base64 encoded 32-byte keys; ``MISSION_VAULT_ACTIVE_KEY``
selects the write key. Production fails closed when no keyring is configured.
"""
from __future__ import annotations
import base64, hashlib, json, os
from dataclasses import dataclass
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAX_FILE_BYTES=10*1024*1024

@dataclass(frozen=True)
class Envelope:
    key_version:str
    nonce:bytes
    ciphertext:bytes
    sha256:str

def _decode_key(value:str)->bytes:
    try:key=base64.urlsafe_b64decode(value.encode())
    except Exception as exc:raise ValueError('invalid vault key encoding') from exc
    if len(key)!=32:raise ValueError('vault keys must be exactly 32 bytes')
    return key

def load_keyring(env:dict|None=None)->tuple[str,dict[str,bytes]]:
    env=env or os.environ;raw=env.get('MISSION_VAULT_KEYS','');active=env.get('MISSION_VAULT_ACTIVE_KEY','')
    if not raw or not active:raise RuntimeError('Mission Vault keyring is not configured')
    try:parsed=json.loads(raw)
    except json.JSONDecodeError as exc:raise RuntimeError('MISSION_VAULT_KEYS must be JSON') from exc
    keys={str(k):_decode_key(str(v)) for k,v in parsed.items()}
    if active not in keys:raise RuntimeError('active Mission Vault key is missing')
    return active,keys

def aad(*,tenant_id:str,resource_type:str,resource_id:str,field_name:str)->bytes:
    return f'{tenant_id}\x1f{resource_type}\x1f{resource_id}\x1f{field_name}'.encode()

def encrypt(plaintext:bytes,*,associated_data:bytes,env:dict|None=None)->Envelope:
    if not plaintext:raise ValueError('vault plaintext may not be empty')
    active,keys=load_keyring(env);nonce=os.urandom(12)
    return Envelope(active,nonce,AESGCM(keys[active]).encrypt(nonce,plaintext,associated_data),hashlib.sha256(plaintext).hexdigest())

def decrypt(envelope:Envelope,*,associated_data:bytes,env:dict|None=None)->bytes:
    _active,keys=load_keyring(env)
    if envelope.key_version not in keys:raise RuntimeError('vault decryption key version unavailable')
    value=AESGCM(keys[envelope.key_version]).decrypt(envelope.nonce,envelope.ciphertext,associated_data)
    if hashlib.sha256(value).hexdigest()!=envelope.sha256:raise ValueError('vault integrity digest mismatch')
    return value

def validate_file(content:bytes)->None:
    if not content:raise ValueError('empty secure file')
    if len(content)>MAX_FILE_BYTES:raise ValueError('secure file exceeds 10 MiB limit')

def secure_session_valid(*,user_id:str,session_user_id:str,purpose:str,expires_at,revoked_at,now)->bool:
    return user_id==session_user_id and purpose in {'credential_download','medical_record_access','break_glass'} and revoked_at is None and expires_at>now
