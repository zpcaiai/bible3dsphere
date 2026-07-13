"""Skill 46/49 API: practicum start gate, stage certification and safeguarding contact."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from core.tenancy import require_org_permission
from mission_bridge_auth import set_tenant_context
from mission_feature_guard import require_mission_feature
from mission_os.audit import audit
from mission_os.practicum import assert_can_start_practicum, validate_activities
from mission_os.certification import (
    certification_type_allowed, can_certify, safeguarding_contact_allowed,
)

_training_gate = require_mission_feature('mission_training_enabled')
router = APIRouter(prefix='/api/v1/mission/certifications', tags=['mission-certification'], dependencies=[Depends(_training_gate)])
practicum_router = APIRouter(prefix='/api/v1/mission/practicum-placements', tags=['mission-certification'], dependencies=[Depends(_training_gate)])
_state = {}


def init_mission_certification_router(*, get_db, release_db, get_session_user, is_admin):
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
    return require_org_permission(cur, email, org_id, 'view_dashboard')['role']


class StartPlacementBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    hasHost: bool
    hasSupervisor: bool
    safeguardingCurrent: bool
    requiredTrainingDone: bool
    allowedActivities: list[str] = Field(default_factory=list)
    prohibitedActivities: list[str] = Field(default_factory=list)


@practicum_router.post('/{placement_id}/start')
def start_placement(placement_id: str, body: StartPlacementBody, request: Request):
    _user_obj, email = _user(request)
    try:
        assert_can_start_practicum(has_host=body.hasHost, has_supervisor=body.hasSupervisor,
                                   safeguarding_current=body.safeguardingCurrent,
                                   required_training_done=body.requiredTrainingDone)
        validate_activities(allowed=body.allowedActivities, prohibited=body.prohibitedActivities)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc))
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute("UPDATE mission_practicum_placements SET placement_status='active',safeguarding_current=TRUE,allowed_activities=%s::jsonb,updated_at=now() WHERE id=%s AND tenant_id=%s",
                        (json.dumps(body.allowedActivities), placement_id, body.organizationId))
            if cur.rowcount == 0:
                raise HTTPException(404, detail='实习安排不存在')
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='update',
                  resource_type='mission_practicum_placement', resource_id=str(placement_id), result='success', reason='started')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'status': 'active'}


class StageCertBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    workerProfileId: str = Field(min_length=1)
    workerUserId: str = Field(min_length=1)
    certificationType: str = Field(min_length=3, max_length=64)
    highRisk: bool = False
    evidenceClasses: list[str] = Field(default_factory=list)
    reviewerIds: list[str] = Field(default_factory=list)


@router.post('/stage')
def issue_stage_certification(body: StageCertBody, request: Request):
    _user_obj, email = _user(request)
    try:
        certification_type_allowed(body.certificationType)   # blocks deployment_approved
        can_certify(evidence_classes=body.evidenceClasses, high_risk=body.highRisk,
                    reviewer_ids=body.reviewerIds or [email], observer_id=email, observed_id=body.workerUserId)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc))
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            second = next((r for r in body.reviewerIds if r != email), None)
            cur.execute(
                "INSERT INTO mission_stage_certifications(tenant_id,worker_profile_id,certification_type,certification_status,high_risk,decided_by,second_reviewer_id,issued_at) "
                "VALUES(%s,%s,%s,'issued',%s,%s,%s,now()) RETURNING id",
                (body.organizationId, body.workerProfileId, body.certificationType, body.highRisk, email, second))
            cid = cur.fetchone()[0]
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='approve',
                  resource_type='mission_stage_certification', resource_id=str(cid), result='success', reason=body.certificationType)
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'certificationId': str(cid), 'certificationType': body.certificationType}


@router.get('/safeguarding/contact-allowed')
def safeguarding_contact(organizationId: str, workerProfileId: str, request: Request):
    _user_obj, email = _user(request)
    now = datetime.now(timezone.utc)
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            _role(cur, email, organizationId)
            set_tenant_context(cur, organizationId)
            cur.execute("SELECT certification_level,expires_at FROM mission_safeguarding_training_records WHERE tenant_id=%s AND worker_profile_id=%s ORDER BY certified_at DESC NULLS LAST LIMIT 1",
                        (organizationId, workerProfileId))
            row = cur.fetchone()
            level = row[0] if row else None
            expires_at = row[1] if row else None
    finally:
        _state['release_db'](conn)
    allowed = safeguarding_contact_allowed(level=level, expires_at=expires_at, now=now)
    return {'ok': True, 'contactAllowed': allowed, 'level': level}
