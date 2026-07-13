"""Skill 16/24 API: mission fields (public/sensitive split) and field assessment."""
from __future__ import annotations
import json
import uuid
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from core.tenancy import require_org_permission
from mission_bridge_auth import set_tenant_context
from mission_feature_guard import require_mission_feature
from mission_os.audit import audit
from mission_os.outbox import enqueue
from mission_os.field import (
    MissionFieldProfile, FIELD_TYPES, public_field_dto, assert_public_dto_clean, assess_field,
)

router = APIRouter(prefix='/api/v1/mission/fields', tags=['mission-fields'], dependencies=[Depends(require_mission_feature('mission_field_intelligence_enabled'))])
_state = {}


def init_mission_fields_router(*, get_db, release_db, get_session_user, is_admin):
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


class FieldBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    fieldType: str = Field(min_length=2, max_length=48)
    canonicalName: str = Field(min_length=1, max_length=200)
    countryCode: str | None = Field(default=None, min_length=2, max_length=2)
    description: str | None = Field(default=None, max_length=2000)
    sensitivityLevel: Literal['P0', 'P1', 'P2', 'P3', 'P4'] = 'P1'

    def check(self):
        if self.fieldType not in FIELD_TYPES:
            raise ValueError('invalid field type')


@router.post('')
def create_field(body: FieldBody, request: Request):
    _user_obj, email = _user(request)
    try:
        body.check()
        MissionFieldProfile(str(uuid.uuid4()), body.organizationId, body.fieldType, body.canonicalName, body.countryCode).validate()
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc))
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute(
                "INSERT INTO mission_fields(tenant_id,field_type,canonical_name,description,country_code,sensitivity_level,created_by) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (body.organizationId, body.fieldType, body.canonicalName, body.description,
                 body.countryCode.upper() if body.countryCode else None, body.sensitivityLevel, email))
            fid = cur.fetchone()[0]
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='create',
                  resource_type='mission_field', resource_id=str(fid), result='success')
            enqueue(cur, tenant_id=body.organizationId, aggregate_type='MissionField', aggregate_id=str(fid),
                    event_type='MissionFieldCreated', event_version=1, actor_id=email,
                    correlation_id=request.headers.get('X-Request-Id') or str(uuid.uuid4()),
                    data={'field_id': str(fid), 'field_type': body.fieldType})
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'fieldId': str(fid), 'status': 'draft'}


@router.get('/{field_id}')
def get_field(field_id: str, organizationId: str, view: Literal['public', 'internal'] = 'internal', request: Request = None):
    _user_obj, email = _user(request)
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            _role(cur, email, organizationId)
            set_tenant_context(cur, organizationId)
            cur.execute(
                "SELECT id,field_type,canonical_name,display_name,description,country_code,public_visibility,sensitivity_level,lifecycle_status,research_status,data_confidence "
                "FROM mission_fields WHERE id=%s AND tenant_id=%s", (field_id, organizationId))
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, detail='禾场不存在')
            record = {
                'id': str(row[0]), 'fieldType': row[1], 'canonicalName': row[2], 'displayName': row[3],
                'description': row[4], 'countryCode': row[5], 'publicVisibility': row[6],
                'sensitivityLevel': row[7], 'lifecycleStatus': row[8], 'researchStatus': row[9], 'dataConfidence': row[10],
            }
    finally:
        _state['release_db'](conn)
    if view == 'public':
        record = public_field_dto(record)
        assert_public_dto_clean(record.keys())
    return {'ok': True, 'view': view, 'field': record}


class AssessBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    needScore: float = Field(ge=0, le=1)
    evidenceScore: float = Field(ge=0, le=1)
    readinessScore: float = Field(ge=0, le=1)
    riskLevel: Literal['low', 'medium', 'high', 'critical']
    hardBlocks: list[str] = Field(default_factory=list)


@router.post('/{field_id}/assess')
def assess(field_id: str, body: AssessBody, request: Request):
    _user_obj, email = _user(request)
    try:
        result = assess_field(need_score=body.needScore, evidence_score=body.evidenceScore,
                              readiness_score=body.readinessScore, risk_level=body.riskLevel,
                              hard_blocks=body.hardBlocks)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc))
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            status = 'blocked' if result.is_blocked() else 'calculated'
            cur.execute("SELECT id FROM mission_field_assessment_frameworks WHERE (tenant_id=%s OR tenant_id IS NULL) AND status='active' ORDER BY tenant_id NULLS LAST, version DESC LIMIT 1", (body.organizationId,))
            fw = cur.fetchone()
            framework_id = fw[0] if fw else None
            cur.execute(
                "INSERT INTO mission_field_assessments(tenant_id,field_id,framework_id,status,need_score,evidence_score,readiness_score,risk_level,hard_blocks,recommendation,generated_by_type,generated_by_id) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,'system',%s) RETURNING id",
                (body.organizationId, field_id, framework_id, status, result.need_score, result.evidence_score,
                 result.readiness_score, result.risk_level, json.dumps(list(result.hard_blocks)), result.recommendation, email))
            aid = cur.fetchone()[0]
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='create',
                  resource_type='mission_field_assessment', resource_id=str(aid), result='success')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'assessmentId': str(aid), 'status': status,
            'needScore': result.need_score, 'evidenceScore': result.evidence_score,
            'readinessScore': result.readiness_score, 'riskLevel': result.risk_level,
            'hardBlocks': list(result.hard_blocks), 'recommendation': result.recommendation}


@router.get('')
def list_fields(organizationId: str, request: Request):
    _user_obj, email = _user(request)
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            _role(cur, email, organizationId)
            set_tenant_context(cur, organizationId)
            cur.execute("SELECT id,field_type,canonical_name,lifecycle_status,research_status,data_confidence,sensitivity_level FROM mission_fields WHERE tenant_id=%s ORDER BY created_at DESC LIMIT 200", (organizationId,))
            rows = [{'id': str(r[0]), 'fieldType': r[1], 'canonicalName': r[2], 'lifecycleStatus': r[3],
                     'researchStatus': r[4], 'dataConfidence': r[5], 'sensitivityLevel': r[6]} for r in cur.fetchall()]
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'items': rows}
