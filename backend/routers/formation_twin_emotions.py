"""Formation Twin Batch 3 emotional-state APIs."""
from __future__ import annotations

import hashlib
import os
import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from psycopg2.extras import Json

from formation_twin.emotion_inference import infer_candidates
from formation_twin.emotion_ontology import EmotionLabel, normalize_emotion_label
from formation_twin.emotional_engine import ENGINE_VERSION, RULE_VERSION, build_snapshot, emotion_frequencies, extract_user_reported

router = APIRouter(prefix="/api/v1/formation-twin", tags=["formation-twin-emotions"])
_state: dict[str, Any] = {}
SOURCE_CONTRACT_DESCRIPTION = (
    "Sources remain separate: USER_REPORT/USER_REPORTED_FACT, "
    "RULE/RULE_DERIVED_METRIC, MODEL/MODEL_INFERENCE, and "
    "USER_CONFIRMED/USER_CONFIRMED_INFERENCE. Model candidates are not user facts."
)


def _flag(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).lower() == "true"


def init_formation_twin_emotions_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _identity(email: str) -> tuple[str, str]:
    return f"personal:{email.lower()}", str(uuid.uuid5(uuid.NAMESPACE_URL, f"formation-twin:{email.lower()}"))


def _owner(cur, email: str) -> None:
    cur.execute("SELECT set_config('app.current_user_email', %s, true)", (email,))


def _publish(cur, email: str, event_type: str, payload: dict) -> None:
    cur.execute(
        "INSERT INTO domain_events (aggregate_type,aggregate_id,event_type,payload) VALUES ('formation_twin',%s,%s,%s)",
        (email, event_type, Json(payload)),
    )


def _read_sensitive(cur, content_id: str, email: str) -> str:
    from formation_twin.crypto import EncryptedContent, decrypt_text
    cur.execute("SELECT encryption_key_version,nonce,encrypted_content,content_hash FROM formation_twin_sensitive_contents WHERE id=%s AND email=%s AND deleted_at IS NULL", (content_id, email))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Sensitive content not found")
    return decrypt_text(EncryptedContent(key_version=row[0], nonce=bytes(row[1]), ciphertext=bytes(row[2]), sha256=row[3]), associated_data=f"{email}:{content_id}".encode())


def _settings(cur, email: str) -> dict:
    tenant_id, profile_id = _identity(email)
    cur.execute(
        "INSERT INTO formation_twin_emotion_settings (id,tenant_id,profile_id,email) VALUES (%s,%s,%s,%s) ON CONFLICT (tenant_id,profile_id) DO NOTHING",
        (str(uuid.uuid4()), tenant_id, profile_id, email),
    )
    cur.execute("SELECT emotion_engine_enabled,trends_enabled,model_inference_enabled,provider_policy,consent_version FROM formation_twin_emotion_settings WHERE email=%s", (email,))
    row = cur.fetchone()
    return {"emotion_engine_enabled": row[0], "trends_enabled": row[1], "model_inference_enabled": row[2], "provider_policy": row[3], "consent_version": row[4]}


class EmotionSettingsBody(BaseModel):
    emotion_engine_enabled: bool = True
    trends_enabled: bool = True
    model_inference_enabled: bool = False
    provider_policy: Literal["CLOUD_PROVIDER", "PRIVATE_DEPLOYMENT", "LOCAL_MODEL", "DISABLED"] = "DISABLED"


class ObservationBody(BaseModel):
    emotion_label: str = Field(min_length=1, max_length=80)
    custom_label: str | None = Field(default=None, max_length=80)
    intensity: int | None = Field(default=None, ge=0, le=10)
    occurred_at: datetime
    source_event_id: str | None = None

    @field_validator("occurred_at")
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timezone-aware occurred_at required")
        return value


class ReviewBody(BaseModel):
    user_label: str | None = Field(default=None, max_length=80)
    user_comment: str | None = Field(default=None, max_length=1000)


class EpisodeBody(BaseModel):
    title: str = Field(default="", max_length=160)
    episode_type: Literal["SINGLE_EVENT", "ONGOING_SITUATION", "RELATIONSHIP_CONFLICT", "WORK_STRESS", "LOSS_AND_GRIEF", "LIFE_TRANSITION", "TEMPTATION_CONTEXT", "RECOVERY_PERIOD", "USER_DEFINED", "OTHER"] = "USER_DEFINED"
    started_at: datetime
    ended_at: datetime | None = None
    life_domains: list[str] = Field(default_factory=list, max_length=8)
    primary_emotions: list[str] = Field(default_factory=list, max_length=8)
    secondary_emotions: list[str] = Field(default_factory=list, max_length=8)
    life_event_ids: list[str] = Field(default_factory=list, max_length=50)


class MergeBody(BaseModel):
    episode_ids: list[str] = Field(min_length=1, max_length=9)
    title: str = Field(default="", max_length=160)


class SplitBody(BaseModel):
    life_event_ids: list[str] = Field(min_length=1, max_length=50)
    title: str = Field(default="", max_length=160)


@router.get("/emotion-settings")
def get_settings(request: Request) -> dict:
    user = _user(request); conn = _state["get_db"]()
    try:
        with conn.cursor() as cur: _owner(cur, user["email"]); value = _settings(cur, user["email"]); conn.commit()
        return {"ok": True, **value}
    finally: _state["release_db"](conn)


@router.put("/emotion-settings")
def update_settings(request: Request, body: EmotionSettingsBody) -> dict:
    user = _user(request); conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"]); _settings(cur, user["email"])
            if body.model_inference_enabled and body.provider_policy == "DISABLED":
                raise HTTPException(status_code=422, detail="Choose an allowed provider policy before enabling inference")
            cur.execute("UPDATE formation_twin_emotion_settings SET emotion_engine_enabled=%s,trends_enabled=%s,model_inference_enabled=%s,provider_policy=%s,updated_at=now() WHERE email=%s", (body.emotion_engine_enabled, body.trends_enabled, body.model_inference_enabled, body.provider_policy, user["email"]))
            _publish(cur, user["email"], "formation_twin.consent_updated", {"scope": "EMOTION_INFERENCE", "enabled": body.model_inference_enabled})
            conn.commit()
        return {"ok": True, **body.model_dump()}
    except Exception: conn.rollback(); raise
    finally: _state["release_db"](conn)


def _insert_observation(cur, email: str, value: dict, *, parent_id: str | None = None) -> str | None:
    tenant_id, profile_id = _identity(email); oid = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO formation_twin_emotion_observations (id,tenant_id,profile_id,email,life_event_id,parent_observation_id,emotion_label,custom_label,intensity,source_kind,statement_type,occurred_at,confidence,model_version,prompt_version,schema_version,rule_version,evidence_json,alternative_labels,user_review_status,processing_status) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING id",
        (oid, tenant_id, profile_id, email, value.get("life_event_id"), parent_id, value["emotion_label"], value.get("custom_label"), value.get("intensity"), value["source_kind"], value["statement_type"], value["occurred_at"], value.get("confidence"), value.get("model_version"), value.get("prompt_version"), value.get("schema_version"), value.get("rule_version"), Json(value.get("evidence_spans") or []), Json(value.get("alternative_labels") or []), value.get("user_review_status", "NOT_REQUIRED"), value.get("processing_status", "ACTIVE")),
    )
    row = cur.fetchone(); return str(row[0]) if row else None


def _load_observations(cur, email: str, *, days: int = 30) -> list[dict]:
    cur.execute("SELECT id,emotion_label,custom_label,intensity,source_kind,statement_type,occurred_at,confidence,model_version,prompt_version,rule_version,evidence_json,alternative_labels,user_review_status,processing_status,life_event_id FROM formation_twin_emotion_observations WHERE email=%s AND deleted_at IS NULL AND occurred_at>=now()-(%s || ' days')::interval ORDER BY occurred_at", (email, days))
    return [{"id":str(r[0]),"emotion_label":r[1],"custom_label":r[2],"intensity":r[3],"source_kind":r[4],"statement_type":r[5],"occurred_at":r[6],"confidence":float(r[7]) if r[7] is not None else None,"model_version":r[8],"prompt_version":r[9],"rule_version":r[10],"evidence":r[11] or [],"alternative_labels":r[12] or [],"user_review_status":r[13],"processing_status":r[14],"life_event_id":str(r[15]) if r[15] else None} for r in cur.fetchall()]


def _load_energy(cur, email: str, *, days: int = 30) -> list[dict]:
    cur.execute("SELECT id,energy_level,stress_level,sleep_quality,restfulness,mental_load,source_kind,statement_type,occurred_at,life_event_id FROM formation_twin_energy_stress_observations WHERE email=%s AND deleted_at IS NULL AND occurred_at>=now()-(%s || ' days')::interval ORDER BY occurred_at", (email, days))
    return [{"id":str(r[0]),"energy_level":r[1],"stress_level":r[2],"sleep_quality":r[3],"restfulness":r[4],"mental_load":r[5],"source_kind":r[6],"statement_type":r[7],"occurred_at":r[8],"life_event_id":str(r[9]) if r[9] else None} for r in cur.fetchall()]


def _load_body(cur, email: str, *, days: int = 30) -> list[dict]:
    cur.execute("SELECT id,body_label,custom_label,body_region,intensity,source_kind,statement_type,occurred_at,life_event_id FROM formation_twin_body_observations WHERE email=%s AND deleted_at IS NULL AND occurred_at>=now()-(%s || ' days')::interval ORDER BY occurred_at", (email, days))
    return [{"id":str(r[0]),"body_label":r[1],"custom_label":r[2],"body_region":r[3],"intensity":r[4],"source_kind":r[5],"statement_type":r[6],"occurred_at":r[7],"life_event_id":str(r[8]) if r[8] else None} for r in cur.fetchall()]


def _save_snapshot(cur, email: str, snapshot_type: str, payload: dict) -> str:
    tenant_id, profile_id = _identity(email)
    cur.execute("SELECT id,version FROM formation_twin_emotional_snapshots WHERE email=%s AND snapshot_type=%s AND superseded_at IS NULL ORDER BY created_at DESC LIMIT 1", (email, snapshot_type)); old = cur.fetchone()
    cur.execute("SELECT id FROM formation_twin_emotional_snapshots WHERE email=%s AND snapshot_type=%s AND input_hash=%s", (email, snapshot_type, payload["input_hash"])); existing = cur.fetchone()
    if existing: return str(existing[0])
    sid = str(uuid.uuid4()); version = (old[1] + 1) if old else 1
    cur.execute("INSERT INTO formation_twin_emotional_snapshots (id,tenant_id,profile_id,email,snapshot_type,window_start,window_end,data_status,data_coverage_json,user_reported_state_json,rule_derived_state_json,model_inferred_state_json,current_candidates_json,conflicts_json,uncertainty_json,limitations_json,user_review_status,version,engine_version,input_hash,supersedes_snapshot_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'[]'::jsonb,%s,%s,'NOT_REQUIRED',%s,%s,%s,%s)", (sid,tenant_id,profile_id,email,snapshot_type,payload["window_start"],payload["window_end"],payload["data_status"],Json(payload["data_coverage"]),Json(payload["user_reported"]),Json(payload["rule_derived"]),Json(payload["possible_model_candidates"]),Json(payload["possible_model_candidates"]),Json(payload["uncertainty"]),Json(payload["limitations"]),version,ENGINE_VERSION,payload["input_hash"],str(old[0]) if old else None))
    if old: cur.execute("UPDATE formation_twin_emotional_snapshots SET superseded_at=now() WHERE id=%s", (old[0],))
    return sid


@router.post("/emotional-state/rebuild")
def rebuild_state(request: Request) -> dict:
    user = _user(request); email = user["email"]; conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur,email); settings = _settings(cur,email)
            if not _flag("FORMATION_TWIN_EMOTION_ENGINE_ENABLED", True) or not settings["emotion_engine_enabled"]:
                raise HTTPException(status_code=409, detail="Emotional state engine is disabled")
            cur.execute("SELECT id,event_type,occurred_at,self_report_json,content_reference_id,safety_json,processing_preference FROM formation_twin_life_events WHERE email=%s AND deleted_at IS NULL AND status='ACCEPTED' AND exclude_from_twin_processing=FALSE AND processing_preference<>'STORE_ONLY' ORDER BY occurred_at", (email,))
            events = cur.fetchall(); created = 0; candidates_created = 0
            cur.execute("UPDATE formation_twin_emotion_observations observation SET processing_status='EXCLUDED' WHERE observation.email=%s AND observation.deleted_at IS NULL AND observation.life_event_id IS NOT NULL AND observation.processing_status='ACTIVE' AND NOT EXISTS (SELECT 1 FROM formation_twin_life_events event WHERE event.id=observation.life_event_id AND event.email=%s AND event.deleted_at IS NULL AND event.status='ACCEPTED' AND event.exclude_from_twin_processing=FALSE AND event.processing_preference<>'STORE_ONLY')",(email,email))
            cur.execute("UPDATE formation_twin_emotion_observations observation SET processing_status='ACTIVE' WHERE observation.email=%s AND observation.deleted_at IS NULL AND observation.life_event_id IS NOT NULL AND observation.processing_status='EXCLUDED' AND EXISTS (SELECT 1 FROM formation_twin_life_events event WHERE event.id=observation.life_event_id AND event.email=%s AND event.deleted_at IS NULL AND event.status='ACCEPTED' AND event.exclude_from_twin_processing=FALSE AND event.processing_preference<>'STORE_ONLY')",(email,email))
            cur.execute("UPDATE formation_twin_body_observations observation SET deleted_at=now() WHERE observation.email=%s AND observation.deleted_at IS NULL AND observation.life_event_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM formation_twin_life_events event WHERE event.id=observation.life_event_id AND event.email=%s AND event.deleted_at IS NULL AND event.status='ACCEPTED' AND event.exclude_from_twin_processing=FALSE AND event.processing_preference<>'STORE_ONLY')",(email,email))
            cur.execute("UPDATE formation_twin_energy_stress_observations observation SET deleted_at=now() WHERE observation.email=%s AND observation.deleted_at IS NULL AND observation.life_event_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM formation_twin_life_events event WHERE event.id=observation.life_event_id AND event.email=%s AND event.deleted_at IS NULL AND event.status='ACCEPTED' AND event.exclude_from_twin_processing=FALSE AND event.processing_preference<>'STORE_ONLY')",(email,email))
            for row in events:
                event = {"event_id":str(row[0]),"event_type":row[1],"occurred_at":row[2],"self_report":row[3] or {}}
                observations, energy, body_states = extract_user_reported(event)
                for observation in observations:
                    if _insert_observation(cur,email,observation): created += 1
                if energy:
                    tenant_id,profile_id=_identity(email)
                    cur.execute("INSERT INTO formation_twin_energy_stress_observations (id,tenant_id,profile_id,email,life_event_id,energy_level,stress_level,sleep_quality,restfulness,mental_load,source_kind,statement_type,occurred_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'USER_REPORT','USER_REPORTED_FACT',%s) ON CONFLICT DO NOTHING", (str(uuid.uuid4()),tenant_id,profile_id,email,row[0],energy.get('energy_level'),energy.get('stress_level'),energy.get('sleep_quality'),energy.get('restfulness'),energy.get('mental_load'),row[2]))
                for body_state in body_states:
                    tenant_id,profile_id=_identity(email)
                    cur.execute("INSERT INTO formation_twin_body_observations (id,tenant_id,profile_id,email,life_event_id,body_label,body_region,intensity,source_kind,statement_type,occurred_at,user_review_status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'USER_REPORT','USER_REPORTED_FACT',%s,'NOT_REQUIRED') ON CONFLICT DO NOTHING",(str(uuid.uuid4()),tenant_id,profile_id,email,row[0],body_state['body_label'],body_state.get('body_region'),body_state.get('intensity'),row[2]))
                safety_level=(row[5] or {}).get("safety_level","NONE")
                if settings["model_inference_enabled"] and row[4] and safety_level not in {"ELEVATED","IMMINENT"}:
                    text=_read_sensitive(cur,str(row[4]),email); inferred,meta=infer_candidates(text)
                    tenant_id,_=_identity(email)
                    cur.execute("INSERT INTO formation_twin_emotion_model_runs (id,tenant_id,email,request_id,provider,model_name,model_version,prompt_template_version,schema_version,result_status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(str(uuid.uuid4()),tenant_id,email,str(uuid.uuid4()),settings['provider_policy'],os.getenv('LLM_MODEL'),os.getenv('LLM_MODEL'),meta.get('prompt_version'),meta.get('schema_version'),meta.get('status','UNKNOWN')))
                    for candidate in inferred:
                        candidate.update({"occurred_at":row[2],"life_event_id":str(row[0]),"processing_status":"ACTIVE"})
                        oid=_insert_observation(cur,email,candidate)
                        if oid:
                            candidates_created += 1
                            for span in candidate["evidence_spans"]:
                                evhash=hashlib.sha256(f"{row[4]}:{span['start_offset']}:{span['end_offset']}".encode()).hexdigest()
                                cur.execute("INSERT INTO formation_twin_emotion_evidence (id,tenant_id,email,emotion_observation_id,life_event_id,content_reference_id,evidence_type,start_offset,end_offset,evidence_hash) VALUES (%s,%s,%s,%s,%s,%s,'TEXT_OFFSET',%s,%s,%s)", (str(uuid.uuid4()),_identity(email)[0],email,oid,row[0],row[4],span['start_offset'],span['end_offset'],evhash))
            observations=_load_observations(cur,email); energy_points=_load_energy(cur,email); body_points=_load_body(cur,email); now=datetime.now(timezone.utc)
            pending=[item for item in observations if item["source_kind"]=="MODEL" and item["user_review_status"]=="PENDING"]
            snapshots={}
            for kind,delta in (("CURRENT_EMOTIONAL_STATE",timedelta(hours=24)),("DAILY_EMOTIONAL_SUMMARY",timedelta(days=1)),("WEEKLY_EMOTIONAL_TREND",timedelta(days=7))):
                payload=build_snapshot(observations=observations,energy_points=energy_points,body_points=body_points,start=now-delta,end=now,model_candidates=pending)
                trends_enabled = _flag("FORMATION_TWIN_EMOTION_TRENDS_ENABLED", True) and settings["trends_enabled"]
                if not trends_enabled:
                    payload["rule_derived"] = {"source_kind":"RULE","statement_type":"RULE_DERIVED_METRIC","rule_version":RULE_VERSION,"status":"DISABLED"}
                    payload["limitations"].append("情感趋势计算已关闭。")
                    payload["input_hash"] = hashlib.sha256(str(payload).encode()).hexdigest()
                snapshots[kind]=_save_snapshot(cur,email,kind,payload)
                if kind == "WEEKLY_EMOTIONAL_TREND" and trends_enabled:
                    tenant_id,profile_id=_identity(email)
                    event_ids=list(dict.fromkeys(item["life_event_id"] for item in energy_points if item.get("life_event_id")))
                    coverage=payload["data_coverage"]["coverage"]
                    for metric_type,metric_value in ((key,value) for key,value in payload["rule_derived"].items() if key.endswith("_trend")):
                        cur.execute("INSERT INTO formation_twin_emotion_rule_results (id,tenant_id,profile_id,email,metric_type,metric_value,window_start,window_end,rule_version,data_point_count,coverage,evidence_event_ids) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(str(uuid.uuid4()),tenant_id,profile_id,email,metric_type,Json(metric_value),payload["window_start"],payload["window_end"],RULE_VERSION,metric_value["data_points"],coverage,Json(event_ids)))
            _publish(cur,email,"formation_twin.emotional_state_updated",{"snapshot_id":snapshots["CURRENT_EMOTIONAL_STATE"],"engine_version":ENGINE_VERSION})
            conn.commit()
        return {"ok":True,"events_considered":len(events),"observations_created":created,"candidates_created":candidates_created,"snapshots":snapshots}
    except Exception: conn.rollback(); raise
    finally: _state["release_db"](conn)


def _snapshot_response(request: Request, snapshot_type: str) -> dict:
    user=_user(request); conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur,user["email"]); cur.execute("SELECT id,window_start,window_end,data_status,data_coverage_json,user_reported_state_json,rule_derived_state_json,current_candidates_json,conflicts_json,uncertainty_json,limitations_json,version,engine_version,created_at FROM formation_twin_emotional_snapshots WHERE email=%s AND snapshot_type=%s AND superseded_at IS NULL ORDER BY created_at DESC LIMIT 1",(user["email"],snapshot_type)); row=cur.fetchone()
        if not row: return {"ok":True,"snapshot":{"snapshot_type":snapshot_type,"data_status":"INSUFFICIENT_DATA","limitations":["请先允许处理至少一条主动记录，然后重建情感状态。"]}}
        return {"ok":True,"snapshot":{"id":str(row[0]),"snapshot_type":snapshot_type,"window_start":row[1].isoformat(),"window_end":row[2].isoformat(),"data_status":row[3],"data_coverage":row[4],"user_reported":row[5],"rule_derived":row[6],"possible_model_candidates":row[7],"conflicts":row[8],"uncertainty":row[9],"limitations":row[10],"version":row[11],"engine_version":row[12],"created_at":row[13].isoformat()}}
    finally: _state["release_db"](conn)


@router.get("/emotional-state/current", description=SOURCE_CONTRACT_DESCRIPTION)
def current_state(request: Request) -> dict: return _snapshot_response(request,"CURRENT_EMOTIONAL_STATE")


@router.get("/emotional-state/daily")
def daily_state(request: Request, date: date | None = None) -> dict: return _snapshot_response(request,"DAILY_EMOTIONAL_SUMMARY")


@router.get("/emotional-state/weekly")
def weekly_state(request: Request) -> dict:
    response=_snapshot_response(request,"WEEKLY_EMOTIONAL_TREND"); user=_user(request); conn=_state["get_db"]()
    try:
        with conn.cursor() as cur: _owner(cur,user["email"]); observations=_load_observations(cur,user["email"],days=14)
        now=datetime.now(timezone.utc); response["frequencies"]=emotion_frequencies(observations,start=now-timedelta(days=7),end=now); return response
    finally: _state["release_db"](conn)


@router.get("/emotion-observations", description=SOURCE_CONTRACT_DESCRIPTION)
def list_observations(request: Request, source_kind: str | None=None, limit:int=Query(100,ge=1,le=200)) -> dict:
    user=_user(request); conn=_state["get_db"]()
    try:
        with conn.cursor() as cur: _owner(cur,user["email"]); items=_load_observations(cur,user["email"],days=365)
        if source_kind: items=[item for item in items if item["source_kind"]==source_kind]
        return {"ok":True,"items":list(reversed(items[-limit:]))}
    finally:_state["release_db"](conn)


@router.get("/emotion-observations/{observation_id}")
def get_observation(observation_id:str,request:Request)->dict:
    items=list_observations(request,limit=200)["items"]; item=next((x for x in items if x["id"]==observation_id),None)
    if not item: raise HTTPException(status_code=404,detail="Emotion observation not found")
    return {"ok":True,"observation":item}


@router.post("/emotion-observations")
def create_observation(request:Request,body:ObservationBody)->dict:
    user=_user(request); label,derived_custom=normalize_emotion_label(body.emotion_label); conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur,user["email"]); life_event_id=None
            if body.source_event_id:
                cur.execute("SELECT id FROM formation_twin_life_events WHERE id=%s AND email=%s AND deleted_at IS NULL",(body.source_event_id,user["email"])); row=cur.fetchone()
                if not row: raise HTTPException(status_code=404,detail="Source event not found")
                life_event_id=str(row[0])
            oid=_insert_observation(cur,user["email"],{"emotion_label":label,"custom_label":body.custom_label or derived_custom,"intensity":body.intensity,"source_kind":"USER_REPORT","statement_type":"USER_REPORTED_FACT","occurred_at":body.occurred_at,"life_event_id":life_event_id,"user_review_status":"NOT_REQUIRED","processing_status":"ACTIVE"})
            if not oid: raise HTTPException(status_code=409,detail="This observation already exists")
            cur.execute("UPDATE formation_twin_emotional_snapshots SET superseded_at=now() WHERE email=%s AND superseded_at IS NULL",(user["email"],))
            _publish(cur,user["email"],"formation_twin.emotion_observation_created",{"observation_id":oid,"source_kind":"USER_REPORT"}); conn.commit()
        return {"ok":True,"observation_id":oid}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.patch("/emotion-observations/{observation_id}")
def revise_observation(observation_id:str,request:Request,body:ObservationBody)->dict:
    user=_user(request); conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur,user["email"]); cur.execute("SELECT life_event_id,revision FROM formation_twin_emotion_observations WHERE id=%s AND email=%s AND deleted_at IS NULL",(observation_id,user["email"])); old=cur.fetchone()
            if not old:raise HTTPException(status_code=404,detail="Emotion observation not found")
            label,custom=normalize_emotion_label(body.emotion_label); tenant,profile=_identity(user["email"]); oid=str(uuid.uuid4())
            cur.execute("INSERT INTO formation_twin_emotion_observations (id,tenant_id,profile_id,email,life_event_id,emotion_label,custom_label,intensity,source_kind,statement_type,occurred_at,user_review_status,processing_status,revision,supersedes_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'USER_REPORT','USER_REPORTED_FACT',%s,'NOT_REQUIRED','ACTIVE',%s,%s)",(oid,tenant,profile,user["email"],old[0],label,body.custom_label or custom,body.intensity,body.occurred_at,old[1]+1,observation_id)); cur.execute("UPDATE formation_twin_emotion_observations SET processing_status='SUPERSEDED' WHERE id=%s",(observation_id,));cur.execute("UPDATE formation_twin_emotional_snapshots SET superseded_at=now() WHERE email=%s AND superseded_at IS NULL",(user["email"],));conn.commit()
        return {"ok":True,"observation_id":oid,"supersedes_id":observation_id}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.delete("/emotion-observations/{observation_id}")
def delete_observation(observation_id:str,request:Request)->dict:
    user=_user(request);conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur,user["email"])
            cur.execute("UPDATE formation_twin_emotion_observations SET deleted_at=now(),processing_status='DELETED' WHERE id=%s AND email=%s AND deleted_at IS NULL RETURNING id",(observation_id,user["email"]))
            found=cur.fetchone()
            if found:
                cur.execute("UPDATE formation_twin_emotional_snapshots SET superseded_at=now() WHERE email=%s AND superseded_at IS NULL",(user["email"],))
            conn.commit()
        if not found:raise HTTPException(status_code=404,detail="Emotion observation not found")
        return {"ok":True}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.get("/emotion-candidates")
def list_candidates(request:Request)->dict:return {"ok":True,"items":list_observations(request,source_kind="MODEL",limit=200)["items"]}


def _review(candidate_id:str,request:Request,body:ReviewBody,action:str)->dict:
    user=_user(request);conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur,user["email"]);cur.execute("SELECT emotion_label,custom_label,intensity,occurred_at,life_event_id,user_review_status FROM formation_twin_emotion_observations WHERE id=%s AND email=%s AND source_kind='MODEL' AND deleted_at IS NULL",(candidate_id,user["email"]));row=cur.fetchone()
            if not row:raise HTTPException(status_code=404,detail="Emotion candidate not found")
            if row[5] != "PENDING":raise HTTPException(status_code=409,detail="Emotion candidate was already reviewed")
            status={"CONFIRM":"CONFIRMED","PARTIAL":"PARTIALLY_CONFIRMED","REJECT":"REJECTED","RELABEL":"RELABELED","DISMISS":"DISMISSED"}[action]
            cur.execute("UPDATE formation_twin_emotion_observations SET user_review_status=%s WHERE id=%s",(status,candidate_id));tenant,profile=_identity(user["email"])
            label=row[0]
            if action in {"RELABEL","PARTIAL"}:
                if not body.user_label:raise HTTPException(status_code=422,detail="user_label is required")
                label,_=normalize_emotion_label(body.user_label)
            confirmed_id=None
            if action in {"CONFIRM","PARTIAL","RELABEL"}:
                confirmed_id=_insert_observation(cur,user["email"],{"emotion_label":label,"custom_label":body.user_label if label=="OTHER" else None,"intensity":row[2],"source_kind":"USER_CONFIRMED","statement_type":"USER_CONFIRMED_INFERENCE","occurred_at":row[3],"life_event_id":str(row[4]) if row[4] else None,"user_review_status":"NOT_REQUIRED","processing_status":"ACTIVE"},parent_id=candidate_id)
            cur.execute("INSERT INTO formation_twin_inference_reviews (id,tenant_id,profile_id,email,emotion_observation_id,review_action,original_label,user_label,user_comment,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(str(uuid.uuid4()),tenant,profile,user["email"],candidate_id,action,row[0],label if action in {'RELABEL','PARTIAL'} else None,body.user_comment,user["email"]))
            cur.execute("UPDATE formation_twin_emotional_snapshots SET superseded_at=now() WHERE email=%s AND superseded_at IS NULL",(user["email"],))
            _publish(cur,user["email"],f"formation_twin.emotion_candidate_{status.lower()}",{"candidate_id":candidate_id,"confirmed_observation_id":confirmed_id});conn.commit()
        return {"ok":True,"status":status,"confirmed_observation_id":confirmed_id}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.post("/emotion-candidates/{candidate_id}/confirm")
def confirm_candidate(candidate_id:str,request:Request,body:ReviewBody|None=None)->dict:return _review(candidate_id,request,body or ReviewBody(),"CONFIRM")
@router.post("/emotion-candidates/{candidate_id}/partially-confirm")
def partial_candidate(candidate_id:str,request:Request,body:ReviewBody)->dict:return _review(candidate_id,request,body,"PARTIAL")
@router.post("/emotion-candidates/{candidate_id}/reject")
def reject_candidate(candidate_id:str,request:Request,body:ReviewBody|None=None)->dict:return _review(candidate_id,request,body or ReviewBody(),"REJECT")
@router.post("/emotion-candidates/{candidate_id}/relabel")
def relabel_candidate(candidate_id:str,request:Request,body:ReviewBody)->dict:return _review(candidate_id,request,body,"RELABEL")
@router.post("/emotion-candidates/{candidate_id}/dismiss")
def dismiss_candidate(candidate_id:str,request:Request,body:ReviewBody|None=None)->dict:return _review(candidate_id,request,body or ReviewBody(),"DISMISS")


def _episode_rows(cur,email:str)->list[dict]:
    cur.execute("SELECT episode.id,episode.title,episode.episode_type,episode.creation_method,episode.started_at,episode.ended_at,episode.life_domains,episode.primary_emotions,episode.secondary_emotions,episode.status,episode.user_review_status,episode.created_at,episode.updated_at,ARRAY(SELECT link.life_event_id::text FROM formation_twin_episode_events link WHERE link.episode_id=episode.id AND link.email=%s ORDER BY link.created_at) FROM formation_twin_emotional_episodes episode WHERE episode.email=%s AND episode.deleted_at IS NULL ORDER BY episode.started_at DESC",(email,email))
    return [{"id":str(r[0]),"title":r[1] or "","episode_type":r[2],"creation_method":r[3],"started_at":r[4].isoformat(),"ended_at":r[5].isoformat() if r[5] else None,"life_domains":r[6] or [],"primary_emotions":r[7] or [],"secondary_emotions":r[8] or [],"status":r[9],"user_review_status":r[10],"created_at":r[11].isoformat(),"updated_at":r[12].isoformat(),"life_event_ids":r[13] or []} for r in cur.fetchall()]


@router.get("/emotional-episodes")
def list_episodes(request:Request)->dict:
    user=_user(request);conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:_owner(cur,user["email"]);items=_episode_rows(cur,user["email"])
        return {"ok":True,"items":items}
    finally:_state["release_db"](conn)


@router.post("/emotional-episodes")
def create_episode(request:Request,body:EpisodeBody)->dict:
    user=_user(request);tenant,profile=_identity(user["email"]);eid=str(uuid.uuid4());conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur,user["email"]);cur.execute("INSERT INTO formation_twin_emotional_episodes (id,tenant_id,profile_id,email,title,episode_type,creation_method,started_at,ended_at,life_domains,primary_emotions,secondary_emotions,status,user_review_status) VALUES (%s,%s,%s,%s,%s,%s,'USER_CREATED',%s,%s,%s,%s,%s,'ACTIVE','NOT_REQUIRED')",(eid,tenant,profile,user["email"],body.title,body.episode_type,body.started_at,body.ended_at,Json(body.life_domains),Json(body.primary_emotions),Json(body.secondary_emotions)))
            for event_id in body.life_event_ids:
                cur.execute("INSERT INTO formation_twin_episode_events (id,tenant_id,email,episode_id,life_event_id,relation_type) SELECT %s,%s,%s,%s,id,'USER_LINKED' FROM formation_twin_life_events WHERE id=%s AND email=%s AND deleted_at IS NULL ON CONFLICT DO NOTHING",(str(uuid.uuid4()),tenant,user["email"],eid,event_id,user["email"]))
            _publish(cur,user["email"],"formation_twin.emotional_episode_confirmed",{"episode_id":eid,"creation_method":"USER_CREATED"});conn.commit()
        return {"ok":True,"episode_id":eid}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.get("/emotional-episodes/{episode_id}")
def get_episode(episode_id:str,request:Request)->dict:
    item=next((x for x in list_episodes(request)["items"] if x["id"]==episode_id),None)
    if not item:raise HTTPException(status_code=404,detail="Episode not found")
    return {"ok":True,"episode":item}


@router.patch("/emotional-episodes/{episode_id}")
def update_episode(episode_id:str,request:Request,body:EpisodeBody)->dict:
    user=_user(request);conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:_owner(cur,user["email"]);cur.execute("UPDATE formation_twin_emotional_episodes SET title=%s,episode_type=%s,started_at=%s,ended_at=%s,life_domains=%s,primary_emotions=%s,secondary_emotions=%s,updated_at=now() WHERE id=%s AND email=%s AND deleted_at IS NULL RETURNING id",(body.title,body.episode_type,body.started_at,body.ended_at,Json(body.life_domains),Json(body.primary_emotions),Json(body.secondary_emotions),episode_id,user["email"]));found=cur.fetchone();conn.commit()
        if not found:raise HTTPException(status_code=404,detail="Episode not found")
        return {"ok":True}
    finally:_state["release_db"](conn)


@router.post("/emotional-episodes/{episode_id}/resolve")
def resolve_episode(episode_id:str,request:Request)->dict:
    user=_user(request);conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:_owner(cur,user["email"]);cur.execute("UPDATE formation_twin_emotional_episodes SET status='RESOLVED',ended_at=COALESCE(ended_at,now()),updated_at=now() WHERE id=%s AND email=%s AND deleted_at IS NULL RETURNING id",(episode_id,user["email"]));found=cur.fetchone();conn.commit()
        if not found:raise HTTPException(status_code=404,detail="Episode not found")
        return {"ok":True,"status":"RESOLVED"}
    finally:_state["release_db"](conn)


@router.post("/emotional-episodes/{episode_id}/merge")
def merge_episode(episode_id:str,request:Request,body:MergeBody)->dict:
    ids=list(dict.fromkeys([episode_id,*body.episode_ids]));user=_user(request);conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur,user["email"]);cur.execute("SELECT MIN(started_at),MAX(ended_at) FROM formation_twin_emotional_episodes WHERE email=%s AND id IN %s AND deleted_at IS NULL",(user["email"],tuple(ids)));bounds=cur.fetchone()
            if not bounds or bounds[0] is None:raise HTTPException(status_code=404,detail="Episodes not found")
            new_id=str(uuid.uuid4());tenant,profile=_identity(user["email"]);cur.execute("INSERT INTO formation_twin_emotional_episodes (id,tenant_id,profile_id,email,title,episode_type,creation_method,started_at,ended_at,status,user_review_status) VALUES (%s,%s,%s,%s,%s,'USER_DEFINED','USER_CREATED',%s,%s,'ACTIVE','NOT_REQUIRED')",(new_id,tenant,profile,user["email"],body.title,bounds[0],bounds[1]));cur.execute("INSERT INTO formation_twin_episode_events (id,tenant_id,email,episode_id,life_event_id,relation_type) SELECT gen_random_uuid(),tenant_id,email,%s,life_event_id,'USER_MERGED' FROM formation_twin_episode_events WHERE email=%s AND episode_id IN %s ON CONFLICT DO NOTHING",(new_id,user["email"],tuple(ids)));cur.execute("UPDATE formation_twin_emotional_episodes SET status='ARCHIVED',updated_at=now() WHERE email=%s AND id IN %s",(user["email"],tuple(ids)));conn.commit()
        return {"ok":True,"episode_id":new_id}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.post("/emotional-episodes/{episode_id}/split")
def split_episode(episode_id:str,request:Request,body:SplitBody)->dict:
    user=_user(request);conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur,user["email"]);cur.execute("SELECT started_at FROM formation_twin_emotional_episodes WHERE id=%s AND email=%s AND deleted_at IS NULL",(episode_id,user["email"]));row=cur.fetchone()
            if not row:raise HTTPException(status_code=404,detail="Episode not found")
            new_id=str(uuid.uuid4());tenant,profile=_identity(user["email"]);cur.execute("INSERT INTO formation_twin_emotional_episodes (id,tenant_id,profile_id,email,title,episode_type,creation_method,started_at,status,user_review_status) VALUES (%s,%s,%s,%s,%s,'USER_DEFINED','USER_CREATED',%s,'ACTIVE','NOT_REQUIRED')",(new_id,tenant,profile,user["email"],body.title,row[0]));cur.execute("UPDATE formation_twin_episode_events SET episode_id=%s,relation_type='USER_SPLIT' WHERE email=%s AND episode_id=%s AND life_event_id IN %s",(new_id,user["email"],episode_id,tuple(body.life_event_ids)));conn.commit()
        return {"ok":True,"episode_id":new_id}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.delete("/emotional-episodes/{episode_id}")
def delete_episode(episode_id:str,request:Request)->dict:
    user=_user(request);conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:_owner(cur,user["email"]);cur.execute("UPDATE formation_twin_emotional_episodes SET deleted_at=now(),status='ARCHIVED' WHERE id=%s AND email=%s AND deleted_at IS NULL RETURNING id",(episode_id,user["email"]));found=cur.fetchone();conn.commit()
        if not found:raise HTTPException(status_code=404,detail="Episode not found")
        return {"ok":True}
    finally:_state["release_db"](conn)


@router.get("/emotional-state/data-quality")
def emotional_quality(request:Request)->dict:
    user=_user(request);conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur,user["email"]);cur.execute("""SELECT
              COUNT(*) FILTER (WHERE source_kind='MODEL' AND (model_version IS NULL OR evidence_json='[]'::jsonb)),
              COUNT(*) FILTER (WHERE source_kind='RULE' AND rule_version IS NULL),
              COUNT(*) FILTER (WHERE statement_type='USER_REPORTED_FACT' AND confidence IS NOT NULL),
              COUNT(*) FILTER (WHERE confidence<0 OR confidence>1),
              COUNT(*) FILTER (WHERE life_event_id IS NOT NULL)-COUNT(DISTINCT (life_event_id,emotion_label,custom_label,source_kind)) FILTER (WHERE life_event_id IS NOT NULL)
              FROM formation_twin_emotion_observations WHERE email=%s AND deleted_at IS NULL""",(user["email"],));row=cur.fetchone()
        issues={"model_missing_provenance":row[0],"rule_missing_version":row[1],"user_report_with_confidence":row[2],"invalid_confidence":row[3],"duplicate_event_observations":max(0,row[4] or 0)};return {"ok":True,"quality_passed":sum(issues.values())==0,"issues":issues}
    finally:_state["release_db"](conn)
