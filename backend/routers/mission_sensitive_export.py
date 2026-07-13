"""Skill 15 API: step-up, sensitive-export approval and secure download tokens."""
from __future__ import annotations
import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from core.tenancy import require_org_permission
from mission_bridge_auth import set_tenant_context
from mission_feature_guard import require_mission_os
from mission_os.audit import audit
from mission_os.outbox import enqueue
from mission_os import sensitive_export as se

router = APIRouter(prefix='/api/v1/mission/sensitive-exports', tags=['mission-sensitive-export'], dependencies=[Depends(require_mission_os)])
_state = {}


def init_mission_sensitive_export_router(*, get_db, release_db, get_session_user, is_admin):
    _state.update(locals())


def _user(request):
    user = _state['get_session_user'](request)
    email = str((user or {}).get('email') or '')
    if not email:
        raise HTTPException(401, detail='请先登录')
    return user, email


def _role(cur, email, org_id):
    if _state['is_admin'](email):
        return 'platform_admin'
    return require_org_permission(cur, email, org_id, 'manage_settings')['role']


def _corr(request):
    return request.headers.get('X-Request-Id') or str(uuid.uuid4())


class ExportBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    resourceType: str = Field(min_length=1, max_length=80)
    sensitivityLevel: Literal['P0', 'P1', 'P2', 'P3', 'P4']
    justification: str = Field(min_length=5, max_length=1000)
    scope: dict = Field(default_factory=dict)


@router.post('')
def create_request(body: ExportBody, request: Request):
    _user_obj, email = _user(request)
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute(
                "INSERT INTO mission_sensitive_export_requests(tenant_id,requester_id,resource_type,scope,sensitivity_level,justification) "
                "VALUES(%s,%s,%s,%s::jsonb,%s,%s) RETURNING id",
                (body.organizationId, email, body.resourceType, json.dumps(body.scope), body.sensitivityLevel, body.justification))
            rid = cur.fetchone()[0]
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='create',
                  resource_type='mission_sensitive_export_request', resource_id=str(rid), result='success')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'exportRequestId': str(rid), 'status': 'requested'}


class StepUpBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    method: Literal['totp', 'webauthn', 'email_code', 'sms_code']


@router.post('/{request_id}/step-up')
def verify_step_up(request_id: str, body: StepUpBody, request: Request):
    """Record a fresh step-up verification and open a short secure session."""
    _user_obj, email = _user(request)
    se.validate_step_up_method(body.method)
    now = datetime.now(timezone.utc)
    session_expiry = now + timedelta(seconds=se.MAX_STEP_UP_AGE_SECONDS)
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute("SELECT status FROM mission_sensitive_export_requests WHERE id=%s AND tenant_id=%s", (request_id, body.organizationId))
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, detail='导出申请不存在')
            se.assert_transition(row[0], 'step_up_pending')
            cur.execute(
                "INSERT INTO mission_secure_sessions(tenant_id,user_id,purpose,step_up_method,expires_at) "
                "VALUES(%s,%s,'sensitive_export',%s,%s) RETURNING id",
                (body.organizationId, email, body.method, session_expiry))
            sid = cur.fetchone()[0]
            cur.execute(
                "UPDATE mission_sensitive_export_requests SET status='step_up_pending',step_up_session_id=%s,step_up_verified_at=%s,updated_at=now() WHERE id=%s AND tenant_id=%s",
                (sid, now, request_id, body.organizationId))
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='approve',
                  resource_type='mission_secure_session', resource_id=str(sid), result='success', reason='step_up')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'secureSessionId': str(sid), 'status': 'step_up_pending', 'expiresAt': session_expiry.isoformat()}


class ApproveBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    watermarkLabel: str = Field(min_length=1, max_length=120)
    expiresMinutes: int = Field(default=60, ge=5, le=1440)
    maxDownloads: int = Field(default=1, ge=1, le=10)


@router.post('/{request_id}/approve')
def approve_request(request_id: str, body: ApproveBody, request: Request):
    """Independent approver with a fresh step-up issues a hashed, watermarked, expiring token."""
    _user_obj, approver = _user(request)
    watermark = se.require_watermark(body.watermarkLabel)
    now = datetime.now(timezone.utc)
    expires_at = se.validate_expiry(now + timedelta(minutes=body.expiresMinutes), now=now)
    raw = secrets.token_urlsafe(32)
    token_hash = se.hash_token(raw)
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, approver, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute(
                "SELECT status,requester_id,step_up_verified_at FROM mission_sensitive_export_requests WHERE id=%s AND tenant_id=%s",
                (request_id, body.organizationId))
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, detail='导出申请不存在')
            status, requester_id, step_up_at = row
            try:
                se.assert_transition(status, 'approved')
                se.can_approve(requester_id=requester_id, approver_id=approver, step_up_verified_at=step_up_at, now=now)
            except ValueError as exc:
                raise HTTPException(403, detail=str(exc))
            cur.execute(
                "UPDATE mission_sensitive_export_requests SET status='ready',approver_id=%s,approved_at=%s,token_hash=%s,watermark_label=%s,max_downloads=%s,expires_at=%s,updated_at=now() WHERE id=%s AND tenant_id=%s",
                (approver, now, token_hash, watermark, body.maxDownloads, expires_at, request_id, body.organizationId))
            audit(cur, tenant_id=body.organizationId, actor_id=approver, actor_role=role, action='approve',
                  resource_type='mission_sensitive_export_request', resource_id=str(request_id), result='success')
            enqueue(cur, tenant_id=body.organizationId, aggregate_type='MissionSensitiveExport', aggregate_id=str(request_id),
                    event_type='MissionSensitiveExportApproved', event_version=1, actor_id=approver, correlation_id=_corr(request),
                    data={'export_request_id': str(request_id), 'expires_at': expires_at.isoformat()})
            conn.commit()
    finally:
        _state['release_db'](conn)
    # The raw token is returned once to the approver and never stored or audited.
    return {'ok': True, 'status': 'ready', 'downloadToken': raw, 'watermarkLabel': watermark, 'expiresAt': expires_at.isoformat()}


class DenyBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=3, max_length=500)


@router.post('/{request_id}/deny')
def deny_request(request_id: str, body: DenyBody, request: Request):
    _user_obj, email = _user(request)
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute("SELECT status FROM mission_sensitive_export_requests WHERE id=%s AND tenant_id=%s", (request_id, body.organizationId))
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, detail='导出申请不存在')
            try:
                se.assert_transition(row[0], 'denied')
            except ValueError as exc:
                raise HTTPException(409, detail=str(exc))
            cur.execute("UPDATE mission_sensitive_export_requests SET status='denied',denied_reason=%s,updated_at=now() WHERE id=%s AND tenant_id=%s",
                        (body.reason, request_id, body.organizationId))
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='reject',
                  resource_type='mission_sensitive_export_request', resource_id=str(request_id), result='success')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'status': 'denied'}


@router.get('/{request_id}/download')
def download(request_id: str, organizationId: str, token: str, request: Request):
    _user_obj, email = _user(request)
    token_hash = se.hash_token(token)
    now = datetime.now(timezone.utc)
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, organizationId)
            set_tenant_context(cur, organizationId)
            cur.execute(
                "SELECT status,token_hash,expires_at,downloads,max_downloads,revoked_at,watermark_label FROM mission_sensitive_export_requests WHERE id=%s AND tenant_id=%s",
                (request_id, organizationId))
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, detail='导出申请不存在')
            status, stored_hash, expires_at, downloads, max_downloads, revoked_at, watermark = row
            if not stored_hash or not secrets.compare_digest(stored_hash, token_hash):
                audit(cur, tenant_id=organizationId, actor_id=email, actor_role=role, action='download',
                      resource_type='mission_sensitive_export_request', resource_id=str(request_id), result='denied')
                conn.commit()
                raise HTTPException(403, detail='下载令牌无效')
            if not se.download_available(status=status, expires_at=expires_at, downloads=downloads,
                                         max_downloads=max_downloads, revoked_at=revoked_at, now=now):
                raise HTTPException(410, detail='下载链接已失效')
            new_downloads = downloads + 1
            cur.execute("UPDATE mission_sensitive_export_requests SET downloads=%s,status='downloaded',updated_at=now() WHERE id=%s AND tenant_id=%s",
                        (new_downloads, request_id, organizationId))
            audit(cur, tenant_id=organizationId, actor_id=email, actor_role=role, action='export',
                  resource_type='mission_sensitive_export_request', resource_id=str(request_id), result='success')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'watermarkLabel': watermark, 'remainingDownloads': max_downloads - new_downloads}


class RevokeBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)


@router.post('/{request_id}/revoke')
def revoke_request(request_id: str, body: RevokeBody, request: Request):
    _user_obj, email = _user(request)
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute("UPDATE mission_sensitive_export_requests SET status='revoked',revoked_at=now(),token_hash=NULL,updated_at=now() WHERE id=%s AND tenant_id=%s AND status NOT IN('denied','expired')",
                        (request_id, body.organizationId))
            if cur.rowcount == 0:
                raise HTTPException(409, detail='申请无法撤销')
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='update',
                  resource_type='mission_sensitive_export_request', resource_id=str(request_id), result='success', reason='revoked')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'status': 'revoked'}
