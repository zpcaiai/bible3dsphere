"""MissionBridge: voluntary mission care, formation programs and safeguarding."""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from mission_os.outbox import enqueue
from mission_feature_guard import require_mission_os

try:
    from backend.mission_bridge_auth import authorize, resolve_role, set_tenant_context
except Exception:
    from mission_bridge_auth import authorize, resolve_role, set_tenant_context
try:
    from backend.mission_bridge_program import validate_for_publish
except Exception:
    from mission_bridge_program import validate_for_publish

_state: Dict[str, Any] = {}

def _mission_gate(request:Request)->None:
    if any(part in request.url.path for part in ("/policy","/privacy/","/incidents")):return
    require_mission_os(request)

router = APIRouter(prefix="/api/mission-bridge", tags=["mission-bridge"],dependencies=[Depends(_mission_gate)])
v1_router = APIRouter(prefix="/api/v1", tags=["mission-bridge-safeguarding"],dependencies=[Depends(_mission_gate)])


def init_mission_bridge_router(*, get_db, release_db, get_session_user, is_admin=None) -> None:
    _state.update(locals())


def _user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(401, detail="请先登录")
    return user


def _tenant(request: Request) -> str:
    value = (request.headers.get("X-Tenant-Id") or "public").strip()
    return value[:80] if value else "public"


def _audit(cur, tenant: str, actor: str, action: str, target_type: str, target_id=None, metadata=None):
    cur.execute("INSERT INTO mission_bridge_audit_log(tenant_id,actor_user_id,action,target_type,target_id,metadata) VALUES(%s,%s,%s,%s,%s,%s::jsonb)",
                (tenant, actor, action, target_type, str(target_id) if target_id else None, json.dumps(metadata or {}, ensure_ascii=False)))


def _role(cur, tenant: str, email: str) -> str:
    if tenant == "public":
        return "participant"
    cur.execute("SELECT role_key FROM organization_memberships WHERE organization_id=%s AND email=%s AND status='active'", (tenant,email))
    row=cur.fetchone()
    if not row: raise HTTPException(403,detail="无权访问该租户")
    return str(row[0])


def _safeguarding_role(cur, tenant: str, user: dict) -> str:
    ctx=authorize(cur,user,"incident.manage",tenant,platform_admin=bool(_state.get("is_admin") and _state["is_admin"](user["email"])))
    return ctx.role


@router.get("/policy")
def policy(request: Request) -> dict:
    user,tenant=_user(request),_tenant(request); conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            authorize(cur,user,"program.read",tenant,platform_admin=bool(_state.get("is_admin") and _state["is_admin"](user["email"])))
            cur.execute("SELECT id,version,title,policy,published_at FROM safeguarding_policy_versions WHERE status='active' ORDER BY published_at DESC LIMIT 1"); row=cur.fetchone()
            cur.execute("SELECT 1 FROM safeguarding_acknowledgements WHERE tenant_id=%s AND user_id=%s AND policy_version_id=%s",(tenant,user["email"],row[0])); acknowledged=bool(cur.fetchone())
    finally:_state["release_db"](conn)
    return {"ok":True,"policy":{"id":str(row[0]),"version":row[1],"title":row[2],"rules":row[3],"publishedAt":row[4].isoformat()},"acknowledged":acknowledged}


@router.post("/policy/acknowledge")
def acknowledge_policy(request: Request) -> dict:
    user,tenant=_user(request),_tenant(request); conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            authorize(cur,user,"program.read",tenant,platform_admin=bool(_state.get("is_admin") and _state["is_admin"](user["email"])))
            cur.execute("SELECT id,version FROM safeguarding_policy_versions WHERE status='active' ORDER BY published_at DESC LIMIT 1"); row=cur.fetchone()
            cur.execute("INSERT INTO safeguarding_acknowledgements(tenant_id,user_id,policy_version_id) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",(tenant,user["email"],row[0])); _audit(cur,tenant,user["email"],"policy.acknowledge","policy",row[0],{"version":row[1]}); conn.commit()
    finally:_state["release_db"](conn)
    return {"ok":True,"policyVersion":row[1]}


@router.get("/dashboard")
def dashboard(request: Request) -> dict:
    user, tenant = _user(request), _tenant(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            authorize(cur,user,"program.read",tenant,platform_admin=bool(_state.get("is_admin") and _state["is_admin"](user["email"])))
            cur.execute("SELECT p.id,p.title,p.description,p.group_type,p.active_version,v.definition,v.safeguarding_profile FROM mission_bridge_program_definitions p JOIN mission_bridge_program_versions v ON v.program_id=p.id AND v.version=p.active_version WHERE p.status='published' ORDER BY p.created_at")
            programs = [{"id":r[0],"title":r[1],"description":r[2],"groupType":r[3],"version":r[4],"definition":r[5],"safeguarding":r[6]} for r in cur.fetchall()]
            cur.execute("SELECT id,program_id,program_version,status,current_step,participant_goal,enrolled_at FROM mission_bridge_enrollments WHERE tenant_id=%s AND user_id=%s ORDER BY enrolled_at DESC", (tenant,user["email"]))
            enrollments = [{"id":str(r[0]),"programId":r[1],"version":r[2],"status":r[3],"currentStep":r[4],"goal":r[5],"enrolledAt":r[6].isoformat()} for r in cur.fetchall()]
            cur.execute("SELECT consent_type,granted,policy_version,updated_at FROM mission_bridge_consents WHERE tenant_id=%s AND user_id=%s", (tenant,user["email"]))
            consents = {r[0]:{"granted":r[1],"policyVersion":r[2],"updatedAt":r[3].isoformat()} for r in cur.fetchall()}
            _audit(cur,tenant,user["email"],"dashboard.view","user",user["email"])
            conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok":True,"programs":programs,"enrollments":enrollments,"consents":consents,"principles":{"voluntary":True,"careNotConditional":True,"aiTrainingOptOut":True}}


class ConsentBody(BaseModel):
    consentType: Literal["program_participation","ai_content_adaptation","mentor_sharing"]
    granted: bool
    policyVersion: str = Field(default="1.0.0", max_length=30)


@router.put("/consents")
def set_consent(body: ConsentBody, request: Request) -> dict:
    user, tenant = _user(request), _tenant(request); conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            authorize(cur,user,"participant.self",tenant,platform_admin=bool(_state.get("is_admin") and _state["is_admin"](user["email"])))
            cur.execute("INSERT INTO mission_bridge_consents(tenant_id,user_id,consent_type,granted,policy_version,granted_at,withdrawn_at) VALUES(%s,%s,%s,%s,%s,CASE WHEN %s THEN now() END,CASE WHEN %s THEN NULL ELSE now() END) ON CONFLICT(tenant_id,user_id,consent_type) DO UPDATE SET granted=EXCLUDED.granted,policy_version=EXCLUDED.policy_version,granted_at=CASE WHEN EXCLUDED.granted THEN now() ELSE mission_bridge_consents.granted_at END,withdrawn_at=CASE WHEN EXCLUDED.granted THEN NULL ELSE now() END,updated_at=now()", (tenant,user["email"],body.consentType,body.granted,body.policyVersion,body.granted,body.granted))
            _audit(cur,tenant,user["email"],"consent.update","consent",body.consentType,{"granted":body.granted}); conn.commit()
    finally: _state["release_db"](conn)
    return {"ok":True,"consentType":body.consentType,"granted":body.granted}


CONSENT_TYPES={"service_participation","faith_exploration","discipleship_program","audio_recording","video_recording","ai_assistance","research_and_evaluation","guardian_consent","professional_referral","data_sharing"}
CONSENT_DEFAULTS={
    "service_participation":("提供一般关怀服务",["profile","care_plan"],730),
    "faith_exploration":("自愿参加信仰探索",["program_progress"],365),
    "discipleship_program":("自愿参加门徒训练",["program_progress","reflection"],730),
    "audio_recording":("保存课程录音",["audio"],90),"video_recording":("保存课程录像",["video"],90),
    "ai_assistance":("使用 AI 辅助整理内容",["minimized_prompt","model_output"],30),
    "research_and_evaluation":("脱敏项目评估",["anonymous_metrics"],730),
    "guardian_consent":("监护人授权",["guardian_relationship"],365),
    "professional_referral":("转介专业机构",["referral_summary"],365),
    "data_sharing":("向明确对象共享数据",["approved_fields"],90),
}


@router.get("/privacy/consents")
def privacy_consents(request: Request) -> dict:
    user,tenant=_user(request),_tenant(request); conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            authorize(cur,user,"participant.self",tenant,platform_admin=bool(_state.get("is_admin") and _state["is_admin"](user["email"])))
            cur.execute("SELECT consent_type,policy_version,language,purpose,data_categories,retention_days,granted,granted_at,revoked_at FROM mission_bridge_consent_records WHERE tenant_id=%s AND user_id=%s",(tenant,user["email"])); rows={r[0]:r for r in cur.fetchall()}
    finally:_state["release_db"](conn)
    items=[]
    for key in sorted(CONSENT_TYPES):
        row=rows.get(key); default=CONSENT_DEFAULTS[key]
        items.append({"consentType":key,"policyVersion":row[1] if row else "1.0.0","language":row[2] if row else "zh-CN","purpose":row[3] if row else default[0],"dataCategories":row[4] if row else default[1],"retentionDays":row[5] if row else default[2],"granted":bool(row[6]) if row else False,"grantedAt":row[7].isoformat() if row and row[7] else None,"revokedAt":row[8].isoformat() if row and row[8] else None})
    return {"ok":True,"items":items,"bundledConsentForbidden":True}


class DetailedConsentBody(BaseModel):
    granted: bool
    language: str = Field(default="zh-CN",max_length=20)


@router.put("/privacy/consents/{consent_type}")
def update_detailed_consent(consent_type: str, body: DetailedConsentBody, request: Request) -> dict:
    if consent_type not in CONSENT_TYPES: raise HTTPException(400,detail="不支持的同意类型")
    user,tenant=_user(request),_tenant(request); purpose,categories,days=CONSENT_DEFAULTS[consent_type]; conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            authorize(cur,user,"participant.self",tenant,platform_admin=bool(_state.get("is_admin") and _state["is_admin"](user["email"])))
            cur.execute("INSERT INTO mission_bridge_consent_records(tenant_id,user_id,consent_type,policy_version,language,purpose,data_categories,retention_days,granted,granted_at,revoked_at) VALUES(%s,%s,%s,'1.0.0',%s,%s,%s::jsonb,%s,%s,CASE WHEN %s THEN now() END,CASE WHEN %s THEN NULL ELSE now() END) ON CONFLICT(tenant_id,user_id,consent_type) DO UPDATE SET language=EXCLUDED.language,granted=EXCLUDED.granted,granted_at=CASE WHEN EXCLUDED.granted THEN now() ELSE mission_bridge_consent_records.granted_at END,revoked_at=CASE WHEN EXCLUDED.granted THEN NULL ELSE now() END,updated_at=now()",(tenant,user["email"],consent_type,body.language,purpose,json.dumps(categories,ensure_ascii=False),days,body.granted,body.granted,body.granted)); _audit(cur,tenant,user["email"],"detailed_consent.update","consent",consent_type,{"granted":body.granted}); conn.commit()
    finally:_state["release_db"](conn)
    return {"ok":True,"consentType":consent_type,"granted":body.granted,"effectiveImmediately":True}


@router.post("/privacy/export")
def request_export(request: Request) -> dict:
    return _create_data_request(request,"export")


@router.post("/privacy/delete")
def request_delete(request: Request) -> dict:
    return _create_data_request(request,"delete")


def _create_data_request(request: Request, request_type: str) -> dict:
    user,tenant=_user(request),_tenant(request); conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            authorize(cur,user,"participant.self",tenant,platform_admin=bool(_state.get("is_admin") and _state["is_admin"](user["email"])))
            cur.execute("INSERT INTO mission_bridge_data_requests(tenant_id,user_id,request_type,scope) VALUES(%s,%s,%s,'{\"mission_bridge\":true}'::jsonb) RETURNING id,requested_at",(tenant,user["email"],request_type)); row=cur.fetchone(); _audit(cur,tenant,user["email"],f"privacy.{request_type}","data_request",row[0],{"safetyRecordsRetained":True}); conn.commit()
    finally:_state["release_db"](conn)
    return {"ok":True,"requestId":str(row[0]),"status":"pending","requestedAt":row[1].isoformat(),"safetyRecordsRetained":True}


class ProposalBody(BaseModel):
    title: str = Field(min_length=3,max_length=160)
    groupDescription: str = Field(min_length=10,max_length=2000)
    needClaimedBy: str = Field(min_length=2,max_length=160)
    communitySelfDescription: str = Field(min_length=4,max_length=2000)
    existingResources: list[str] = Field(default_factory=list,max_length=30)
    entryChannels: list[str] = Field(default_factory=list,max_length=30)
    potentialRisks: list[str] = Field(default_factory=list,max_length=30)
    capabilityGaps: list[str] = Field(default_factory=list,max_length=30)


@router.get("/discovery/proposals")
def list_proposals(request: Request) -> dict:
    user,tenant=_user(request),_tenant(request); conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            authorize(cur,user,"program.manage",tenant,platform_admin=bool(_state.get("is_admin") and _state["is_admin"](user["email"])))
            cur.execute("SELECT id,title,group_description,status,created_at FROM mission_bridge_group_proposals WHERE tenant_id=%s ORDER BY created_at DESC",(tenant,)); items=[{"id":str(r[0]),"title":r[1],"groupDescription":r[2],"status":r[3],"createdAt":r[4].isoformat()} for r in cur.fetchall()]
    finally:_state["release_db"](conn)
    return {"ok":True,"items":items}


@router.post("/discovery/proposals")
def create_proposal(body: ProposalBody, request: Request) -> dict:
    if "未信" in body.communitySelfDescription and len(body.communitySelfDescription.strip()) <= 12: raise HTTPException(422,detail="不能把‘未信’本身定义为社会问题")
    user,tenant=_user(request),_tenant(request); conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            authorize(cur,user,"program.manage",tenant,platform_admin=bool(_state.get("is_admin") and _state["is_admin"](user["email"])))
            cur.execute("INSERT INTO mission_bridge_group_proposals(tenant_id,title,group_description,need_claimed_by,community_self_description,existing_resources,entry_channels,potential_risks,capability_gaps,created_by) VALUES(%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s) RETURNING id",(tenant,body.title,body.groupDescription,body.needClaimedBy,body.communitySelfDescription,json.dumps(body.existingResources,ensure_ascii=False),json.dumps(body.entryChannels,ensure_ascii=False),json.dumps(body.potentialRisks,ensure_ascii=False),json.dumps(body.capabilityGaps,ensure_ascii=False),user["email"])); pid=cur.fetchone()[0]; _audit(cur,tenant,user["email"],"discovery.proposal.create","proposal",pid); conn.commit()
    finally:_state["release_db"](conn)
    return {"ok":True,"proposalId":str(pid)}


class InterviewBody(BaseModel):
    participantKind: Literal["community_member","stakeholder","service_provider"]
    anonymous: bool = True
    consentConfirmed: bool
    responses: list[dict] = Field(min_length=1,max_length=30)


@router.post("/discovery/proposals/{proposal_id}/interviews")
def create_interview(proposal_id: uuid.UUID, body: InterviewBody, request: Request) -> dict:
    if not body.consentConfirmed: raise HTTPException(409,detail="访谈必须先获得明确同意")
    user,tenant=_user(request),_tenant(request); conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            authorize(cur,user,"program.manage",tenant,platform_admin=bool(_state.get("is_admin") and _state["is_admin"](user["email"])))
            cur.execute("INSERT INTO mission_bridge_discovery_interviews(tenant_id,proposal_id,participant_kind,anonymous,consent_confirmed,interviewer_user_id) SELECT %s,id,%s,%s,TRUE,%s FROM mission_bridge_group_proposals WHERE id=%s AND tenant_id=%s RETURNING id",(tenant,body.participantKind,body.anonymous,user["email"],str(proposal_id),tenant)); row=cur.fetchone()
            if not row: raise HTTPException(404,detail="群体提案不存在")
            for response in body.responses:
                question=str(response.get("question", ""))[:500].strip(); answer=str(response.get("response", ""))[:4000].strip()
                if question and answer: cur.execute("INSERT INTO mission_bridge_interview_responses(tenant_id,interview_id,question,response) VALUES(%s,%s,%s,%s)",(tenant,row[0],question,answer))
            _audit(cur,tenant,user["email"],"discovery.interview.create","interview",row[0],{"anonymous":body.anonymous}); conn.commit()
    finally:_state["release_db"](conn)
    return {"ok":True,"interviewId":str(row[0])}


class NeedBody(BaseModel):
    label: str = Field(min_length=2,max_length=160)
    category: str = Field(min_length=2,max_length=80)
    frequency: int = Field(default=1,ge=1,le=1000)
    severity: int = Field(default=1,ge=1,le=5)
    expressedByCommunity: bool = False
    serviceBoundary: Literal["church_can_support","professional_referral","existing_resource","out_of_scope"] = "church_can_support"
    source: Literal["researcher","ai_candidate"] = "researcher"
    confirmed: bool = False


@router.post("/discovery/proposals/{proposal_id}/needs")
def add_need(proposal_id: uuid.UUID, body: NeedBody, request: Request) -> dict:
    user,tenant=_user(request),_tenant(request); conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            authorize(cur,user,"program.manage",tenant,platform_admin=bool(_state.get("is_admin") and _state["is_admin"](user["email"])))
            cur.execute("INSERT INTO mission_bridge_observed_needs(tenant_id,proposal_id,label,category,frequency,severity,expressed_by_community,service_boundary,source,confirmed_by,confirmed_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,CASE WHEN %s THEN %s END,CASE WHEN %s THEN now() END) RETURNING id",(tenant,str(proposal_id),body.label,body.category,body.frequency,body.severity,body.expressedByCommunity,body.serviceBoundary,body.source,body.confirmed,user["email"],body.confirmed)); nid=cur.fetchone()[0]; conn.commit()
    finally:_state["release_db"](conn)
    return {"ok":True,"needId":str(nid),"requiresResearcherConfirmation":body.source=="ai_candidate" and not body.confirmed}


@router.get("/discovery/proposals/{proposal_id}/report")
def discovery_report(proposal_id: uuid.UUID, request: Request) -> dict:
    user,tenant=_user(request),_tenant(request); conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            authorize(cur,user,"program.manage",tenant,platform_admin=bool(_state.get("is_admin") and _state["is_admin"](user["email"])))
            cur.execute("SELECT title,group_description,community_self_description,status FROM mission_bridge_group_proposals WHERE id=%s AND tenant_id=%s",(str(proposal_id),tenant)); proposal=cur.fetchone()
            if not proposal: raise HTTPException(404,detail="群体提案不存在")
            cur.execute("SELECT COUNT(*),COUNT(*) FILTER(WHERE participant_kind='community_member') FROM mission_bridge_discovery_interviews WHERE proposal_id=%s AND tenant_id=%s",(str(proposal_id),tenant)); counts=cur.fetchone()
            cur.execute("SELECT label,category,frequency,severity,expressed_by_community,service_boundary FROM mission_bridge_observed_needs WHERE proposal_id=%s AND tenant_id=%s AND confirmed_at IS NOT NULL ORDER BY severity DESC,frequency DESC",(str(proposal_id),tenant)); needs=[{"label":r[0],"category":r[1],"frequency":r[2],"severity":r[3],"communityExpressed":r[4],"boundary":r[5]} for r in cur.fetchall()]
            _audit(cur,tenant,user["email"],"discovery.report.view","proposal",proposal_id); conn.commit()
    finally:_state["release_db"](conn)
    return {"ok":True,"proposal":{"id":str(proposal_id),"title":proposal[0],"description":proposal[1],"communityVoice":proposal[2],"status":proposal[3]},"interviews":{"total":counts[0],"communityMembers":counts[1],"communityMemberRatio":round(counts[1]/counts[0],2) if counts[0] else 0},"needs":needs,"readyForPilot":counts[0]>=10 and bool(needs),"note":"仅包含研究员确认的主题；AI候选主题不会自动进入报告。"}


class ProgramPublishBody(BaseModel):
    definition: dict


@router.post("/admin/programs/validate")
def validate_program(body: ProgramPublishBody, request: Request) -> dict:
    user,tenant=_user(request),_tenant(request); conn=_state["get_db"]()
    try:
        with conn.cursor() as cur: authorize(cur,user,"program.manage",tenant,platform_admin=bool(_state.get("is_admin") and _state["is_admin"](user["email"])))
    finally:_state["release_db"](conn)
    model=validate_for_publish(body.definition)
    return {"ok":True,"valid":True,"programId":model.id,"version":model.version,"steps":sum(len(p.steps) for p in model.pathways)}


@router.post("/admin/programs/publish")
def publish_program(body: ProgramPublishBody, request: Request) -> dict:
    model=validate_for_publish(body.definition); user,tenant=_user(request),_tenant(request); conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            authorize(cur,user,"program.manage",tenant,platform_admin=bool(_state.get("is_admin") and _state["is_admin"](user["email"])))
            cur.execute("SELECT 1 FROM mission_bridge_program_versions WHERE program_id=%s AND version=%s",(model.id,model.version))
            if cur.fetchone(): raise HTTPException(409,detail="已发布版本不可覆盖，请创建新版本")
            cur.execute("INSERT INTO mission_bridge_program_definitions(id,group_type,title,description,active_version,status) VALUES(%s,%s,%s,%s,%s,'published') ON CONFLICT(id) DO UPDATE SET group_type=EXCLUDED.group_type,title=EXCLUDED.title,description=EXCLUDED.description,active_version=EXCLUDED.active_version,status='published'",(model.id,model.groupType,model.title,model.description,model.version))
            cur.execute("INSERT INTO mission_bridge_program_versions(program_id,version,definition,safeguarding_profile) VALUES(%s,%s,%s::jsonb,%s::jsonb)",(model.id,model.version,json.dumps(model.model_dump(),ensure_ascii=False),json.dumps(model.safeguardingProfile,ensure_ascii=False)))
            for pathway in model.pathways:
                cur.execute("INSERT INTO mission_bridge_program_pathways(program_id,program_version,key,title,eligibility) VALUES(%s,%s,%s,%s,%s::jsonb)",(model.id,model.version,pathway.key,pathway.title,json.dumps(pathway.eligibility,ensure_ascii=False)))
                for order,step in enumerate(pathway.steps,1): cur.execute("INSERT INTO mission_bridge_program_steps(program_id,program_version,pathway_key,step_order,title,step_type,required,condition,content_refs) VALUES(%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)",(model.id,model.version,pathway.key,order,step.title,step.stepType,step.required,json.dumps(step.condition),json.dumps(step.contentRefs)))
            _audit(cur,tenant,user["email"],"program.publish","program",model.id,{"version":model.version}); conn.commit()
    finally:_state["release_db"](conn)
    return {"ok":True,"programId":model.id,"version":model.version,"immutable":True}


@router.post("/enrollments/{enrollment_id}/pause")
def pause_program(enrollment_id:uuid.UUID,request:Request)->dict:
    user,tenant=_user(request),_tenant(request);conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            authorize(cur,user,"participant.self",tenant);cur.execute("UPDATE mission_bridge_enrollments SET status='paused' WHERE id=%s AND tenant_id=%s AND user_id=%s AND status='active' RETURNING id",(str(enrollment_id),tenant,user["email"]));row=cur.fetchone()
            if not row:raise HTTPException(404,detail="活跃项目不存在")
            cur.execute("INSERT INTO mission_bridge_program_pauses(tenant_id,enrollment_id,paused_by) VALUES(%s,%s,%s)",(tenant,str(enrollment_id),user["email"]));conn.commit()
    finally:_state["release_db"](conn)
    return {"ok":True,"status":"paused"}


@router.post("/enrollments/{enrollment_id}/resume")
def resume_program(enrollment_id:uuid.UUID,request:Request)->dict:
    user,tenant=_user(request),_tenant(request);conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            authorize(cur,user,"participant.self",tenant);cur.execute("UPDATE mission_bridge_enrollments SET status='active' WHERE id=%s AND tenant_id=%s AND user_id=%s AND status='paused' RETURNING id",(str(enrollment_id),tenant,user["email"]));row=cur.fetchone()
            if not row:raise HTTPException(404,detail="暂停项目不存在")
            cur.execute("UPDATE mission_bridge_program_pauses SET resumed_at=now() WHERE enrollment_id=%s AND resumed_at IS NULL",(str(enrollment_id),));conn.commit()
    finally:_state["release_db"](conn)
    return {"ok":True,"status":"active"}


@router.get("/journey")
def participant_journey(request:Request)->dict:
    user,tenant=_user(request),_tenant(request);conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            authorize(cur,user,"participant.self",tenant)
            cur.execute("SELECT id,title,success_description,status,participant_confirmed_at FROM mission_bridge_participant_goals WHERE tenant_id=%s AND user_id=%s ORDER BY created_at DESC",(tenant,user["email"]));goals=[{"id":str(r[0]),"title":r[1],"successDescription":r[2],"status":r[3],"confirmed":bool(r[4])} for r in cur.fetchall()]
            cur.execute("SELECT p.id,p.title,p.status,p.rationale,p.participant_approved_at,a.id,a.title,a.action_type,a.due_date,a.status,a.suggestion_reason FROM mission_bridge_care_plans p LEFT JOIN mission_bridge_care_actions a ON a.care_plan_id=p.id WHERE p.tenant_id=%s AND p.user_id=%s ORDER BY p.created_at DESC,a.created_at",(tenant,user["email"]));plans={}
            for r in cur.fetchall():
                plan=plans.setdefault(str(r[0]),{"id":str(r[0]),"title":r[1],"status":r[2],"rationale":r[3],"approved":bool(r[4]),"actions":[]})
                if r[5]:plan["actions"].append({"id":str(r[5]),"title":r[6],"type":r[7],"dueDate":str(r[8]) if r[8] else None,"status":r[9],"suggestionReason":r[10]})
            cur.execute("SELECT label,evidence,confirmed_by_participant FROM mission_bridge_participant_strengths WHERE tenant_id=%s AND user_id=%s ORDER BY created_at DESC",(tenant,user["email"]));strengths=[{"label":r[0],"evidence":r[1],"confirmed":r[2]} for r in cur.fetchall()]
    finally:_state["release_db"](conn)
    return {"ok":True,"goals":goals,"carePlans":list(plans.values()),"strengths":strengths,"participantOwnsGoals":True}


class GoalBody(BaseModel):
    enrollmentId:Optional[uuid.UUID]=None;title:str=Field(min_length=3,max_length=240);successDescription:str=Field(min_length=5,max_length=1000)


@router.post("/journey/goals")
def create_goal(body:GoalBody,request:Request)->dict:
    if any(word in body.title.lower() for word in ("必须受洗","baptism required")):raise HTTPException(422,detail="一般关怀项目不能把受洗设为默认成功指标")
    user,tenant=_user(request),_tenant(request);conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            authorize(cur,user,"participant.self",tenant);cur.execute("INSERT INTO mission_bridge_participant_goals(tenant_id,user_id,enrollment_id,title,success_description) VALUES(%s,%s,%s,%s,%s) RETURNING id",(tenant,user["email"],str(body.enrollmentId) if body.enrollmentId else None,body.title,body.successDescription));gid=cur.fetchone()[0];conn.commit()
    finally:_state["release_db"](conn)
    return {"ok":True,"goalId":str(gid),"status":"proposed","requiresParticipantConfirmation":True}


@router.post("/journey/goals/{goal_id}/confirm")
def confirm_goal(goal_id:uuid.UUID,request:Request)->dict:
    user,tenant=_user(request),_tenant(request);conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            authorize(cur,user,"participant.self",tenant);cur.execute("UPDATE mission_bridge_participant_goals SET status='active',participant_confirmed_at=now() WHERE id=%s AND tenant_id=%s AND user_id=%s RETURNING id",(str(goal_id),tenant,user["email"]));row=cur.fetchone()
            if not row:raise HTTPException(404,detail="目标不存在")
            conn.commit()
    finally:_state["release_db"](conn)
    return {"ok":True,"status":"active","participantConfirmed":True}


class CarePlanBody(BaseModel):
    enrollmentId:Optional[uuid.UUID]=None;title:str=Field(min_length=3,max_length=240);rationale:str=Field(min_length=8,max_length=1500);actions:list[dict]=Field(min_length=1,max_length=20)


@router.post("/journey/care-plans")
def create_care_plan(body:CarePlanBody,request:Request)->dict:
    user,tenant=_user(request),_tenant(request);conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            authorize(cur,user,"participant.self",tenant);cur.execute("INSERT INTO mission_bridge_care_plans(tenant_id,user_id,enrollment_id,title,rationale) VALUES(%s,%s,%s,%s,%s) RETURNING id",(tenant,user["email"],str(body.enrollmentId) if body.enrollmentId else None,body.title,body.rationale));pid=cur.fetchone()[0]
            for action in body.actions:
                title=str(action.get('title','')).strip()[:240];reason=str(action.get('suggestionReason','')).strip()[:1000]
                if not title or not reason:raise HTTPException(422,detail="每个建议行动必须包含建议原因")
                cur.execute("INSERT INTO mission_bridge_care_actions(tenant_id,care_plan_id,title,action_type,suggestion_reason) VALUES(%s,%s,%s,%s,%s)",(tenant,pid,title,str(action.get('type','weekly_action'))[:80],reason))
            conn.commit()
    finally:_state["release_db"](conn)
    return {"ok":True,"carePlanId":str(pid),"status":"draft","requiresParticipantApproval":True}


@router.post("/journey/actions/{action_id}/complete")
def complete_action(action_id:uuid.UUID,request:Request)->dict:
    user,tenant=_user(request),_tenant(request);conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            authorize(cur,user,"participant.self",tenant);cur.execute("UPDATE mission_bridge_care_actions a SET status='completed',completed_at=now() FROM mission_bridge_care_plans p WHERE a.id=%s AND a.care_plan_id=p.id AND p.tenant_id=%s AND p.user_id=%s RETURNING a.id",(str(action_id),tenant,user["email"]));row=cur.fetchone()
            if not row:raise HTTPException(404,detail="行动不存在")
            conn.commit()
    finally:_state["release_db"](conn)
    return {"ok":True,"status":"completed"}


class EnrollBody(BaseModel):
    programId: str = Field(max_length=80)
    participantGoal: str = Field(min_length=2,max_length=500)


@router.post("/enrollments")
def enroll(body: EnrollBody, request: Request) -> dict:
    user, tenant = _user(request), _tenant(request); conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            authorize(cur,user,"program.read",tenant,platform_admin=bool(_state.get("is_admin") and _state["is_admin"](user["email"])))
            cur.execute("SELECT granted FROM mission_bridge_consents WHERE tenant_id=%s AND user_id=%s AND consent_type='program_participation'",(tenant,user["email"])); consent=cur.fetchone()
            if not consent or not consent[0]: raise HTTPException(409,detail="请先确认自愿参与与随时退出条款")
            cur.execute("SELECT active_version FROM mission_bridge_program_definitions WHERE id=%s AND status='published'",(body.programId,)); row=cur.fetchone()
            if not row: raise HTTPException(404,detail="项目不存在")
            cur.execute("INSERT INTO mission_bridge_enrollments(tenant_id,user_id,program_id,program_version,participant_goal) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(tenant_id,user_id,program_id) DO UPDATE SET status='active',participant_goal=EXCLUDED.participant_goal,exited_at=NULL RETURNING id",(tenant,user["email"],body.programId,row[0],body.participantGoal)); eid=cur.fetchone()[0]
            _audit(cur,tenant,user["email"],"enrollment.start","enrollment",eid,{"programId":body.programId})
            enqueue(cur,tenant_id=tenant,aggregate_type="MissionProgramEnrollment",aggregate_id=str(eid),event_type="MissionProgramEnrollmentStarted",event_version=1,actor_id=user["email"],correlation_id=request.headers.get("X-Request-Id") or str(uuid.uuid4()),data={"program_id":body.programId,"enrollment_id":str(eid)})
            conn.commit()
    finally: _state["release_db"](conn)
    return {"ok":True,"enrollmentId":str(eid)}


@router.post("/enrollments/{enrollment_id}/exit")
def exit_program(enrollment_id: uuid.UUID, request: Request) -> dict:
    user, tenant = _user(request), _tenant(request); conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            authorize(cur,user,"participant.self",tenant,platform_admin=bool(_state.get("is_admin") and _state["is_admin"](user["email"])))
            cur.execute("UPDATE mission_bridge_enrollments SET status='exited',exited_at=now() WHERE id=%s AND tenant_id=%s AND user_id=%s RETURNING id",(str(enrollment_id),tenant,user["email"])); row=cur.fetchone()
            if not row: raise HTTPException(404,detail="报名记录不存在")
            _audit(cur,tenant,user["email"],"enrollment.exit","enrollment",enrollment_id,{"careAccessPreserved":True}); conn.commit()
    finally:_state["release_db"](conn)
    return {"ok":True,"careAccessPreserved":True}


class CheckinBody(BaseModel):
    wellbeing: int = Field(ge=1,le=5)
    reflection: str = Field(default="",max_length=2000)
    needsSupport: bool = False


@router.post("/enrollments/{enrollment_id}/checkins")
def checkin(enrollment_id: uuid.UUID, body: CheckinBody, request: Request) -> dict:
    user,tenant=_user(request),_tenant(request); conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            authorize(cur,user,"participant.self",tenant,platform_admin=bool(_state.get("is_admin") and _state["is_admin"](user["email"])))
            cur.execute("SELECT id,current_step FROM mission_bridge_enrollments WHERE id=%s AND tenant_id=%s AND user_id=%s AND status='active'",(str(enrollment_id),tenant,user["email"])); row=cur.fetchone()
            if not row: raise HTTPException(404,detail="活跃项目不存在")
            cur.execute("INSERT INTO mission_bridge_checkins(enrollment_id,user_id,wellbeing,reflection,needs_support) VALUES(%s,%s,%s,%s,%s) RETURNING id",(str(enrollment_id),user["email"],body.wellbeing,body.reflection,body.needsSupport)); cid=cur.fetchone()[0]
            cur.execute("UPDATE mission_bridge_enrollments SET current_step=current_step+1 WHERE id=%s",(str(enrollment_id),)); _audit(cur,tenant,user["email"],"checkin.create","checkin",cid,{"needsSupport":body.needsSupport})
            enqueue(cur,tenant_id=tenant,aggregate_type="MissionProgramEnrollment",aggregate_id=str(enrollment_id),event_type="MissionTrainingMilestoneCompleted",event_version=1,actor_id=user["email"],correlation_id=request.headers.get("X-Request-Id") or str(uuid.uuid4()),data={"enrollment_id":str(enrollment_id),"checkin_id":str(cid),"support_requested":body.needsSupport})
            conn.commit()
    finally:_state["release_db"](conn)
    return {"ok":True,"checkinId":str(cid),"supportRequested":body.needsSupport}


class IncidentBody(BaseModel):
    riskLevel: Literal["L0","L1","L2","L3"]
    category: str = Field(min_length=2,max_length=80)
    summary: str = Field(min_length=4,max_length=2000)
    immediateDanger: bool = False
    locationScope: str = Field(default="undisclosed",max_length=80)


@router.post("/incidents")
@v1_router.post("/incidents")
def create_incident(body: IncidentBody, request: Request) -> dict:
    user,tenant=_user(request),_tenant(request); level="L3" if body.immediateDanger else body.riskLevel; conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            authorize(cur,user,"incident.report",tenant,platform_admin=bool(_state.get("is_admin") and _state["is_admin"](user["email"])))
            cur.execute("INSERT INTO incident_reports(tenant_id,participant_id,reporter_user_id,risk_level,category,summary,immediate_danger,location_scope) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id,created_at",(tenant,user["email"],user["email"],level,body.category,body.summary,body.immediateDanger,body.locationScope)); row=cur.fetchone()
            _audit(cur,tenant,user["email"],"incident.create","incident",row[0],{"riskLevel":level})
            enqueue(cur,tenant_id=tenant,aggregate_type="MissionIncident",aggregate_id=str(row[0]),event_type="MissionIncidentCreated",event_version=1,actor_id=user["email"],correlation_id=request.headers.get("X-Request-Id") or str(uuid.uuid4()),data={"incident_id":str(row[0]),"risk_level":level,"requires_human_review":level in ("L2","L3")})
            conn.commit()
    finally:_state["release_db"](conn)
    return {"ok":True,"incidentId":str(row[0]),"riskLevel":level,"requiresHumanEscalation":level in ("L2","L3"),"emergencyNotice":level=="L3"}


class EscalateBody(BaseModel):
    toLevel: Literal["L1","L2","L3"]
    reason: str = Field(min_length=4,max_length=1000)


@router.post("/incidents/{incident_id}/escalate")
@v1_router.post("/incidents/{incident_id}/escalate")
def escalate(incident_id: uuid.UUID, body: EscalateBody, request: Request) -> dict:
    user,tenant=_user(request),_tenant(request); conn=_state["get_db"]()
    order={"L0":0,"L1":1,"L2":2,"L3":3}
    try:
        with conn.cursor() as cur:
            authorize(cur,user,"incident.report",tenant,platform_admin=bool(_state.get("is_admin") and _state["is_admin"](user["email"])))
            cur.execute("SELECT risk_level,reporter_user_id FROM incident_reports WHERE id=%s AND tenant_id=%s",(str(incident_id),tenant)); row=cur.fetchone()
            if not row: raise HTTPException(404,detail="事件不存在")
            if row[1] != user["email"] and not (_state.get("is_admin") and _state["is_admin"](user["email"])):
                raise HTTPException(404,detail="事件不存在")
            if order[body.toLevel] <= order[row[0]]: raise HTTPException(409,detail="安全事件只能升级，不能由 AI 或普通流程降级")
            cur.execute("UPDATE incident_reports SET risk_level=%s WHERE id=%s",(body.toLevel,str(incident_id)))
            cur.execute("INSERT INTO escalation_events(incident_id,from_level,to_level,reason,triggered_by_type,triggered_by_id) VALUES(%s,%s,%s,%s,'user',%s)",(str(incident_id),row[0],body.toLevel,body.reason,user["email"])); _audit(cur,tenant,user["email"],"incident.escalate","incident",incident_id,{"from":row[0],"to":body.toLevel}); conn.commit()
    finally:_state["release_db"](conn)
    return {"ok":True,"riskLevel":body.toLevel}


@router.get("/incidents/{incident_id}/timeline")
@v1_router.get("/incidents/{incident_id}/timeline")
def timeline(incident_id: uuid.UUID, request: Request) -> dict:
    user,tenant=_user(request),_tenant(request); conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            set_tenant_context(cur,tenant)
            cur.execute("SELECT reporter_user_id,risk_level,category,summary,status,created_at FROM incident_reports WHERE id=%s AND tenant_id=%s",(str(incident_id),tenant)); incident=cur.fetchone()
            if not incident: raise HTTPException(404,detail="事件不存在")
            is_owner=incident[0]==user["email"]
            if not is_owner:
                role=_safeguarding_role(cur,tenant,user)
                if incident[2] in {"minor_safety","child_abuse","child_protection"} and role not in {"platform_admin","child_protection_officer"}: raise HTTPException(403,detail="未成年人事件需要儿童保护权限")
            cur.execute("SELECT from_level,to_level,reason,triggered_by_type,created_at FROM escalation_events WHERE incident_id=%s ORDER BY created_at",(str(incident_id),)); events=[{"from":r[0],"to":r[1],"reason":r[2],"byType":r[3],"createdAt":r[4].isoformat()} for r in cur.fetchall()]
            _audit(cur,tenant,user["email"],"incident.view","incident",incident_id); conn.commit()
    finally:_state["release_db"](conn)
    return {"ok":True,"incident":{"id":str(incident_id),"riskLevel":incident[1],"category":incident[2],"summary":incident[3],"status":incident[4],"createdAt":incident[5].isoformat()},"events":events}


@router.get("/admin/incidents")
def list_incidents(request: Request) -> dict:
    user,tenant=_user(request),_tenant(request); conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            role=_safeguarding_role(cur,tenant,user)
            cur.execute("SELECT id,risk_level,category,immediate_danger,status,assigned_to,created_at FROM incident_reports WHERE tenant_id=%s ORDER BY CASE risk_level WHEN 'L3' THEN 3 WHEN 'L2' THEN 2 WHEN 'L1' THEN 1 ELSE 0 END DESC,created_at DESC LIMIT 200",(tenant,))
            items=[]
            for r in cur.fetchall():
                if r[2] in {"minor_safety","child_abuse","child_protection"} and role not in {"platform_admin","child_protection_officer"}: continue
                items.append({"id":str(r[0]),"riskLevel":r[1],"category":r[2],"immediateDanger":r[3],"status":r[4],"assignedTo":r[5],"createdAt":r[6].isoformat()})
            _audit(cur,tenant,user["email"],"incident.list","incident",metadata={"count":len(items)}); conn.commit()
    finally:_state["release_db"](conn)
    return {"ok":True,"items":items}


class ResolveBody(BaseModel):
    resolutionNote: str = Field(min_length=8,max_length=2000)


@router.post("/admin/incidents/{incident_id}/resolve")
def resolve_incident(incident_id: uuid.UUID, body: ResolveBody, request: Request) -> dict:
    user,tenant=_user(request),_tenant(request); conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            role=_safeguarding_role(cur,tenant,user)
            cur.execute("SELECT risk_level,category,status FROM incident_reports WHERE id=%s AND tenant_id=%s FOR UPDATE",(str(incident_id),tenant)); row=cur.fetchone()
            if not row: raise HTTPException(404,detail="事件不存在")
            if row[0] in {"L2","L3"} and role not in {"platform_admin","safeguarding_officer","child_protection_officer"}: raise HTTPException(403,detail="L2/L3 只能由安全官解决")
            if row[1] in {"minor_safety","child_abuse","child_protection"} and role not in {"platform_admin","child_protection_officer"}: raise HTTPException(403,detail="未成年人事件需要儿童保护权限")
            cur.execute("UPDATE incident_reports SET status='resolved',assigned_to=%s,resolved_at=now() WHERE id=%s",(user["email"],str(incident_id)))
            _audit(cur,tenant,user["email"],"incident.resolve","incident",incident_id,{"riskLevel":row[0],"resolutionNote":body.resolutionNote}); conn.commit()
    finally:_state["release_db"](conn)
    return {"ok":True,"status":"resolved"}
