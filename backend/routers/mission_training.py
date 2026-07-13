"""Skill 37/44 API: training plans (gap->module, hard-block guard) and language assessment."""
from __future__ import annotations
import json
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from core.tenancy import require_org_permission
from mission_bridge_auth import set_tenant_context
from mission_feature_guard import require_mission_feature
from mission_os.audit import audit
from mission_os.training import (
    MODULE_TYPES, validate_gap_has_module, assert_hard_block_not_course_only,
    can_certify_language_level, validate_language_level,
)

_training_gate = require_mission_feature('mission_training_enabled')
router = APIRouter(prefix='/api/v1/mission/training-plans', tags=['mission-training'], dependencies=[Depends(_training_gate)])
lang_router = APIRouter(prefix='/api/v1/mission/language-plans', tags=['mission-training'], dependencies=[Depends(_training_gate)])
_state = {}


def init_mission_training_router(*, get_db, release_db, get_session_user, is_admin):
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


class GapSpec(BaseModel):
    readinessDimension: str = Field(min_length=2, max_length=64)
    isHardBlock: bool = False
    moduleTypes: list[str] = Field(default_factory=list)


class PlanBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    workerProfileId: str = Field(min_length=1)
    planType: str = Field(default='foundational_formation', max_length=48)
    durationMonths: int = Field(default=12, ge=1, le=36)
    gaps: list[GapSpec] = Field(default_factory=list)


@router.post('')
def create_plan(body: PlanBody, request: Request):
    _user_obj, email = _user(request)
    # Validate: every gap maps to a module, and no hard block is course-only.
    for g in body.gaps:
        for mt in g.moduleTypes:
            if mt not in MODULE_TYPES:
                raise HTTPException(422, detail=f'invalid module type: {mt}')
        try:
            validate_gap_has_module(g.readinessDimension, g.moduleTypes)
            assert_hard_block_not_course_only(is_hard_block=g.isHardBlock, module_types=g.moduleTypes)
        except ValueError as exc:
            raise HTTPException(422, detail=str(exc))
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute(
                "INSERT INTO mission_training_plans(tenant_id,worker_profile_id,plan_type,duration_months,plan_status) "
                "VALUES(%s,%s,%s,%s,'awaiting_worker_review') RETURNING id",
                (body.organizationId, body.workerProfileId, body.planType, body.durationMonths))
            pid = cur.fetchone()[0]
            for g in body.gaps:
                cur.execute(
                    "INSERT INTO mission_training_plan_gaps(tenant_id,training_plan_id,readiness_dimension,blocking) VALUES(%s,%s,%s,%s)",
                    (body.organizationId, pid, g.readinessDimension, g.isHardBlock))
                for i, mt in enumerate(g.moduleTypes):
                    cur.execute(
                        "INSERT INTO mission_training_plan_modules(tenant_id,training_plan_id,module_type,title,sequence_order) VALUES(%s,%s,%s,%s,%s)",
                        (body.organizationId, pid, mt, f'{g.readinessDimension}:{mt}', i))
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='create',
                  resource_type='mission_training_plan', resource_id=str(pid), result='success')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'trainingPlanId': str(pid), 'status': 'awaiting_worker_review'}


@router.get('')
def list_plans(organizationId: str, request: Request):
    _user_obj, email = _user(request); conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            _role(cur, email, organizationId); set_tenant_context(cur, organizationId)
            cur.execute("SELECT id,worker_profile_id,plan_type,plan_status,duration_months,created_at FROM mission_training_plans WHERE tenant_id=%s ORDER BY created_at DESC LIMIT 200", (organizationId,))
            items=[{'id':str(r[0]),'workerProfileId':r[1],'planType':r[2],'planStatus':r[3],'durationMonths':r[4],'createdAt':r[5].isoformat()} for r in cur.fetchall()]
    finally: _state['release_db'](conn)
    return {'ok':True,'items':items}


class LangAssessBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    assessorType: Literal['self', 'ai', 'native_speaker', 'authorized_assessor']
    level: str = Field(min_length=2, max_length=4)
    verified: bool = False


@lang_router.post('/{plan_id}/assessments')
def add_language_assessment(plan_id: str, body: LangAssessBody, request: Request):
    _user_obj, email = _user(request)
    try:
        validate_language_level(body.level)
        if body.verified:
            can_certify_language_level(level=body.level, assessor_type=body.assessorType)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc))
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute("SELECT 1 FROM mission_language_plans WHERE id=%s AND tenant_id=%s", (plan_id, body.organizationId))
            if not cur.fetchone():
                raise HTTPException(404, detail='语言计划不存在')
            cur.execute(
                "INSERT INTO mission_language_assessments(tenant_id,plan_id,assessment_type,assessor_type,assessor_id,speaking_level,verified) "
                "VALUES(%s,%s,'checkpoint',%s,%s,%s,%s) RETURNING id",
                (body.organizationId, plan_id, body.assessorType, email, body.level, body.verified))
            aid = cur.fetchone()[0]
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='create',
                  resource_type='mission_language_assessment', resource_id=str(aid), result='success')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'assessmentId': str(aid), 'verified': body.verified}
