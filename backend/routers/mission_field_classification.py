"""Skill 11 API: field-level sensitivity classification and field authorization."""
from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from core.tenancy import require_org_permission
from mission_bridge_auth import set_tenant_context
from mission_feature_guard import require_mission_os
from mission_os.audit import audit
from mission_os.classification import normalize_level, scope_ceiling, LEVELS

router = APIRouter(prefix='/api/v1/mission/field-classifications', tags=['mission-field-classification'], dependencies=[Depends(require_mission_os)])
grants_router = APIRouter(prefix='/api/v1/mission/field-access-grants', tags=['mission-field-classification'], dependencies=[Depends(require_mission_os)])
_state = {}


def init_mission_field_classification_router(*, get_db, release_db, get_session_user, is_admin):
    _state.update(locals())


def _user(request):
    user = _state['get_session_user'](request)
    email = str((user or {}).get('email') or '')
    if not email:
        raise HTTPException(401, detail='请先登录')
    return user, email


def _admin(cur, email, org_id):
    if _state['is_admin'](email):
        return 'platform_admin'
    return require_org_permission(cur, email, org_id, 'manage_settings')['role']


class ClassificationBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    resourceType: str = Field(min_length=1, max_length=80)
    fieldName: str = Field(min_length=1, max_length=120)
    sensitivityLevel: Literal['P0', 'P1', 'P2', 'P3', 'P4']
    rationale: str | None = Field(default=None, max_length=500)


@router.get('')
def list_classifications(organizationId: str, request: Request):
    _user_obj, email = _user(request)
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            _admin(cur, email, organizationId)
            set_tenant_context(cur, organizationId)
            cur.execute(
                "SELECT resource_type,field_name,sensitivity_level,rationale,reviewed_by,updated_at "
                "FROM mission_field_classifications WHERE tenant_id=%s ORDER BY resource_type,field_name",
                (organizationId,))
            rows = [{'resourceType': r[0], 'fieldName': r[1], 'sensitivityLevel': r[2],
                     'rationale': r[3], 'reviewedBy': r[4],
                     'updatedAt': r[5].isoformat() if r[5] else None} for r in cur.fetchall()]
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'levels': list(LEVELS), 'classifications': rows}


@router.put('')
def upsert_classification(body: ClassificationBody, request: Request):
    _user_obj, email = _user(request)
    normalize_level(body.sensitivityLevel)
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _admin(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute(
                "INSERT INTO mission_field_classifications(tenant_id,resource_type,field_name,sensitivity_level,rationale,reviewed_by) "
                "VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(tenant_id,resource_type,field_name) DO UPDATE SET "
                "sensitivity_level=EXCLUDED.sensitivity_level,rationale=EXCLUDED.rationale,reviewed_by=EXCLUDED.reviewed_by,updated_at=now()",
                (body.organizationId, body.resourceType, body.fieldName, body.sensitivityLevel, body.rationale, email))
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='update',
                  resource_type='mission_field_classification', resource_id=f'{body.resourceType}.{body.fieldName}',
                  result='success', changed_fields=['sensitivity_level'])
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'resourceType': body.resourceType, 'fieldName': body.fieldName, 'sensitivityLevel': body.sensitivityLevel}


class GrantBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    subjectType: Literal['user', 'role', 'service']
    subjectId: str = Field(min_length=1, max_length=255)
    resourceType: str = Field(min_length=1, max_length=80)
    fieldName: str = Field(min_length=1, max_length=120)
    maxSensitivity: Literal['P0', 'P1', 'P2', 'P3', 'P4']
    reason: str = Field(min_length=3, max_length=500)
    expiresHours: int = Field(default=168, ge=1, le=8760)


@grants_router.post('')
def create_grant(body: GrantBody, request: Request):
    _user_obj, email = _user(request)
    normalize_level(body.maxSensitivity)
    # A service subject (general AI account) may never be granted P3/P4.
    if body.subjectType == 'service' and body.maxSensitivity in ('P3', 'P4'):
        raise HTTPException(403, detail='服务账号不得被授予 P3/P4 敏感字段')
    expires_at = datetime.now(timezone.utc) + timedelta(hours=body.expiresHours)
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _admin(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute(
                "INSERT INTO mission_field_access_grants(tenant_id,subject_type,subject_id,resource_type,field_name,max_sensitivity,reason,granted_by,expires_at) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (body.organizationId, body.subjectType, body.subjectId, body.resourceType, body.fieldName,
                 body.maxSensitivity, body.reason, email, expires_at))
            gid = cur.fetchone()[0]
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='approve',
                  resource_type='mission_field_access_grant', resource_id=str(gid), result='success',
                  reason='field_access_grant')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'grantId': str(gid), 'expiresAt': expires_at.isoformat(),
            'ceiling': scope_ceiling('reviewer', grant_level=body.maxSensitivity)}
