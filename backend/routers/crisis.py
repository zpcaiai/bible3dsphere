"""
Crisis router — 危机守护子系统 (/api/crisis)

  POST /api/crisis/triage              危机分级（记录 crisis_events，orange/red 附资源）
  POST /api/crisis/safety-check        安全确认状态机推进
  GET  /api/crisis/resources           按 locale 返回当地危机热线/紧急资源
  GET  /api/crisis/safety-plan         读取当前安全计划
  GET  /api/crisis/safety-plan/template 生成安全计划模板（按 locale）
  POST /api/crisis/safety-plan         创建/更新安全计划（单一 active）
  GET  /api/crisis/guardians           守护人列表
  POST /api/crisis/guardians           新增守护人
  PUT  /api/crisis/guardians/{id}      更新守护人
  DELETE /api/crisis/guardians/{id}    删除守护人
  POST /api/crisis/escalate            红色升级文本 + 守护人提醒（需预授权才通知）
  GET  /api/crisis/comfort             低压属灵安慰（区分责备/控告）
  GET  /api/crisis/pfa                 心理急救稳定脚本（grounding/呼吸）
  GET  /api/crisis/addiction           成瘾复发：HALT + 10 分钟延迟
  GET  /api/crisis/trauma              创伤 grounding
  GET  /api/crisis/post-crisis         危机后 24h/72h/7d/30d 任务
  POST /api/crisis/followups           生成一段恢复跟进
  GET  /api/crisis/followups           跟进列表
  PUT  /api/crisis/followups/{id}      更新跟进进度
  GET  /api/crisis/events              个人危机事件审计列表
  POST /api/crisis/events/{id}/ack     用户确认
  DELETE /api/crisis/events/{id}       删除单条危机记录
  GET  /api/crisis/meta                元数据（风险类型/分辨表/禁语/免责声明）

定位：先保命 → 再稳定 → 再陪伴 → 再属灵重建。不诊断、不预测、不替代急救/咨询。
LLM 未配置时全部走 crisis_engine 的规则/模板逻辑，功能完整可用。
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

try:  # absolute when run from backend/, package-style otherwise
    import crisis_engine as ce
except ImportError:  # pragma: no cover
    from backend import crisis_engine as ce  # type: ignore

try:
    import notify
except ImportError:  # pragma: no cover
    from backend import notify  # type: ignore

try:
    from core.config import get_settings
    _settings = get_settings()
except Exception:  # pragma: no cover
    _settings = None

router = APIRouter(prefix="/api/crisis", tags=["crisis"])

_state: Dict[str, Any] = {}

_PHASE_OFFSETS = {"24h": 1, "72h": 3, "7d": 7, "30d": 30}


def init_crisis_router(*, get_db, release_db, get_session_user, to_shanghai_iso, root_dir=None) -> None:
    _state.update(locals())
    if get_db and release_db:
        _init_tables(get_db, release_db, root_dir)


def _init_tables(get_db, release_db, root_dir=None) -> None:
    schema_path = Path(root_dir or Path(__file__).resolve().parents[2]) / "backend" / "crisis_schema.sql"
    try:
        sql = schema_path.read_text(encoding="utf-8")
    except Exception as exc:  # pragma: no cover
        print(f"[crisis] schema file unreadable: {exc}", flush=True)
        return
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        print("[crisis] tables ensured", flush=True)
    except Exception as exc:  # pragma: no cover
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"[crisis] WARNING: table init failed: {exc}", flush=True)
    finally:
        release_db(conn)


# ─────────────────────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────────────────────

def _uid() -> str:
    return uuid.uuid4().hex


def _db():
    return _state["get_db"]()


def _release(conn) -> None:
    _state["release_db"](conn)


def _to_iso(dt) -> str:
    return _state["to_shanghai_iso"](dt) if dt else ""


def _require_email(request: Request) -> str:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user["email"]


def _optional_email(request: Request) -> Optional[str]:
    try:
        user = _state["get_session_user"](request)
        if user and user.get("email"):
            return user["email"]
    except Exception:
        pass
    return None


def _jsonb(value) -> str:
    return json.dumps(value or [], ensure_ascii=False)


def _mask_email(e: Optional[str]) -> str:
    """脱敏：给牧者看的当事人邮箱只显示首字母，如 a***@x.com。"""
    e = e or ""
    if "@" not in e:
        return e
    local, dom = e.split("@", 1)
    masked = "*" if len(local) <= 1 else local[0] + "***"
    return f"{masked}@{dom}"


# ── optional LLM triage (only raises the level, never lowers) ────────────────

def _llm_configured() -> bool:
    if _settings is None:
        return False
    for key in ("gemini_api_key", "deepseek_api_key", "siliconflow_api_key"):
        v = getattr(_settings, key, "") or ""
        if v and not v.startswith("your_"):
            return True
    return False


def _llm_triage_level(text: str) -> Optional[str]:
    if not _llm_configured():
        return None
    try:
        import httpx
    except Exception:
        return None
    providers = []
    gem = getattr(_settings, "gemini_api_key", "") or ""
    ds = getattr(_settings, "deepseek_api_key", "") or ""
    sf = getattr(_settings, "siliconflow_api_key", "") or ""
    if gem and not gem.startswith("your_"):
        providers.append({"url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                          "model": "gemini-2.0-flash",
                          "headers": {"Authorization": f"Bearer {gem}", "Content-Type": "application/json"}})
    if ds and not ds.startswith("your_"):
        providers.append({"url": "https://api.deepseek.com/chat/completions", "model": "deepseek-chat",
                          "headers": {"Authorization": f"Bearer {ds}", "Content-Type": "application/json"}})
    if sf and not sf.startswith("your_"):
        providers.append({"url": "https://api.siliconflow.cn/v1/chat/completions", "model": "deepseek-ai/DeepSeek-V3",
                          "headers": {"Authorization": f"Bearer {sf}", "Content-Type": "application/json"}})
    messages = ce.build_triage_messages(text)
    for p in providers:
        try:
            with httpx.Client(timeout=20) as client:
                resp = client.post(p["url"], headers=p["headers"], json={
                    "model": p["model"], "messages": messages, "temperature": 0.0, "max_tokens": 8})
            if resp.status_code >= 400:
                continue
            raw = resp.json()["choices"][0]["message"]["content"]
            return ce.parse_llm_level(raw)
        except Exception:
            continue
    return None


# ─────────────────────────────────────────────────────────────────────────────
# request models (frontend sends camelCase)
# ─────────────────────────────────────────────────────────────────────────────

class TriageBody(BaseModel):
    message: str = ""
    locale: Optional[str] = None
    useLLM: bool = True


class SafetyCheckBody(BaseModel):
    state: str = "ask_intent"
    answerYes: Optional[bool] = None


class SafetyPlanBody(BaseModel):
    warningSigns: List[Any] = Field(default_factory=list)
    internalCopingStrategies: List[Any] = Field(default_factory=list)
    safePeople: List[Any] = Field(default_factory=list)
    safePlaces: List[Any] = Field(default_factory=list)
    professionalResources: List[Any] = Field(default_factory=list)
    meansRestrictionSteps: List[Any] = Field(default_factory=list)
    spiritualAnchors: List[Any] = Field(default_factory=list)
    emergencyMessageTemplate: str = ""
    regionCode: Optional[str] = None


class GuardianBody(BaseModel):
    name: str
    relationship: str = ""
    role: str = "friend"
    phone: str = ""
    email: str = ""
    notifyMethods: List[str] = Field(default_factory=list)
    permissionLevel: str = "orange"
    consentEnabled: bool = False


class EscalateBody(BaseModel):
    level: str = "red"
    locale: Optional[str] = None
    notifyGuardians: bool = False
    eventId: Optional[str] = None


class FollowupBody(BaseModel):
    phase: str = "24h"
    eventId: Optional[str] = None
    tasks: Optional[List[str]] = None


class FollowupUpdateBody(BaseModel):
    completedTaskIds: Optional[List[str]] = None
    status: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# triage
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/triage")
def triage(body: TriageBody, request: Request):
    text = (body.message or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="message is required")

    email = _optional_email(request)
    context_levels = _recent_levels(email) if email else None
    llm_level = _llm_triage_level(text) if body.useLLM else None

    result = ce.triage(text, llm_level=llm_level, context_levels=context_levels)
    level = result["riskLevel"]

    payload: Dict[str, Any] = dict(result)
    payload["disclaimer"] = ce.MODULE_DISCLAIMER

    if level in ("orange", "red"):
        payload["resources"] = ce.get_resources(body.locale)
    if level == "red":
        payload["emergency"] = ce.red_emergency_message(body.locale)
    if result["requiresDirectSafetyQuestion"]:
        payload["safetyCheck"] = ce.safety_check_step("ask_intent", None)

    # audit log (best-effort; never blocks the crisis response)
    if email:
        _log_event(email, text, result)

    return payload


def _recent_levels(email: str) -> List[str]:
    conn = _db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT risk_level FROM crisis_events WHERE user_id=%s "
                        "ORDER BY created_at DESC LIMIT 10", (email,))
            return [r[0] for r in cur.fetchall()]
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return []
    finally:
        _release(conn)


def _log_event(email: str, text: str, result: Dict[str, Any]) -> Optional[str]:
    eid = _uid()
    # red 事件保留触发文本以便人工跟进；其余等级默认不存原文，降低敏感数据留存
    stored_msg = text if result["riskLevel"] == "red" else None
    conn = _db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO crisis_events (id, user_id, risk_level, risk_types, evidence, "
                "triggering_message, workflow_started) "
                "VALUES (%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s)",
                (eid, email, result["riskLevel"], _jsonb(result["riskTypes"]),
                 _jsonb(result["evidence"]), stored_msg, result["recommendedWorkflow"]))
        conn.commit()
        try:
            import formation_events as _fe
            _sevmap = {"red": "red", "amber": "amber", "yellow": "amber"}
            _fe.record_event(email, "crisis", "crisis", title="危机分级",
                             severity=_sevmap.get(result.get("riskLevel"), "green"), ref_id=eid)
        except Exception:
            pass
        return eid
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return None
    finally:
        _release(conn)


# ─────────────────────────────────────────────────────────────────────────────
# safety-check / pfa / comfort / addiction / trauma / post-crisis (stateless)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/safety-check")
def safety_check(body: SafetyCheckBody):
    if body.state not in ce.SAFETY_CHECK_STATES:
        raise HTTPException(status_code=400, detail="invalid state")
    step = ce.safety_check_step(body.state, body.answerYes)
    return step


@router.get("/resources")
def resources(locale: Optional[str] = Query(None)):
    return ce.get_resources(locale)


@router.get("/pfa")
def pfa(type: Optional[str] = Query(None), cycles: int = Query(5)):
    return {
        "stabilize": ce.pfa_stabilize(type),
        "grounding": ce.grounding_54321(),
        "breathing": ce.breathing_guide(cycles),
        "lookChecklist": ce.pfa_look_checklist(),
        "listen": ce.pfa_listen_line(),
    }


@router.get("/comfort")
def comfort(type: Optional[str] = Query(None), message: Optional[str] = Query(None)):
    ctype = type or (ce.detect_spiritual_crisis(message) if message else None)
    out = ce.spiritual_comfort(ctype)
    out["detectedType"] = ctype
    out["convictionVsCondemnation"] = ce.CONVICTION_VS_CONDEMNATION
    return out


@router.get("/addiction")
def addiction(domain: Optional[str] = Query(None)):
    return {
        "halt": ce.HALT_PROMPT,
        "delayPlan": ce.ten_minute_delay(domain),
        "alternatives": ce.addiction_alternatives(),
        "domains": list(ce.ADDICTION_DOMAINS),
    }


@router.get("/trauma")
def trauma():
    return {"grounding": ce.trauma_grounding(), "donts": ce.trauma_donts()}


@router.get("/post-crisis")
def post_crisis(phase: Optional[str] = Query(None)):
    if phase:
        return {"phase": phase, "tasks": ce.post_crisis_tasks(phase)}
    return {"phases": ce.post_crisis_all()}


# ─────────────────────────────────────────────────────────────────────────────
# safety plan
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/safety-plan/template")
def safety_plan_template(locale: Optional[str] = Query(None)):
    return ce.build_safety_plan(locale)


def _row_to_plan(row) -> Dict[str, Any]:
    return {
        "id": row[0], "warningSigns": row[1], "internalCopingStrategies": row[2],
        "safePeople": row[3], "safePlaces": row[4], "professionalResources": row[5],
        "meansRestrictionSteps": row[6], "spiritualAnchors": row[7],
        "emergencyMessageTemplate": row[8], "regionCode": row[9], "status": row[10],
        "lastReviewedAt": _to_iso(row[11]), "updatedAt": _to_iso(row[12]),
    }


_PLAN_COLS = ("id, warning_signs, internal_coping_strategies, safe_people, safe_places, "
              "professional_resources, means_restriction_steps, spiritual_anchors, "
              "emergency_message_template, region_code, status, last_reviewed_at, updated_at")


@router.get("/safety-plan")
def get_safety_plan(request: Request):
    email = _require_email(request)
    conn = _db()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_PLAN_COLS} FROM crisis_safety_plans "
                        "WHERE user_id=%s AND status='active' ORDER BY updated_at DESC LIMIT 1", (email,))
            row = cur.fetchone()
        return {"plan": _row_to_plan(row) if row else None}
    finally:
        _release(conn)


@router.post("/safety-plan")
def save_safety_plan(body: SafetyPlanBody, request: Request):
    email = _require_email(request)
    conn = _db()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE crisis_safety_plans SET status='archived', updated_at=NOW() "
                        "WHERE user_id=%s AND status='active'", (email,))
            pid = _uid()
            cur.execute(
                "INSERT INTO crisis_safety_plans (id, user_id, warning_signs, "
                "internal_coping_strategies, safe_people, safe_places, professional_resources, "
                "means_restriction_steps, spiritual_anchors, emergency_message_template, "
                "region_code, last_reviewed_at) VALUES "
                "(%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s,NOW())",
                (pid, email, _jsonb(body.warningSigns), _jsonb(body.internalCopingStrategies),
                 _jsonb(body.safePeople), _jsonb(body.safePlaces), _jsonb(body.professionalResources),
                 _jsonb(body.meansRestrictionSteps), _jsonb(body.spiritualAnchors),
                 body.emergencyMessageTemplate, body.regionCode))
            cur.execute(f"SELECT {_PLAN_COLS} FROM crisis_safety_plans WHERE id=%s", (pid,))
            row = cur.fetchone()
        conn.commit()
        return {"plan": _row_to_plan(row)}
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail="save failed")
    finally:
        _release(conn)


# ─────────────────────────────────────────────────────────────────────────────
# guardian network
# ─────────────────────────────────────────────────────────────────────────────

def _row_to_guardian(row) -> Dict[str, Any]:
    return {
        "id": row[0], "name": row[1], "relationship": row[2], "role": row[3],
        "phone": row[4], "email": row[5], "notifyMethods": row[6],
        "permissionLevel": row[7], "consentEnabled": row[8], "createdAt": _to_iso(row[9]),
    }


_GUARD_COLS = ("id, name, relationship, role, phone, email, notify_methods, "
               "permission_level, consent_enabled, created_at")


@router.get("/guardians")
def list_guardians(request: Request):
    email = _require_email(request)
    conn = _db()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_GUARD_COLS} FROM crisis_guardian_contacts "
                        "WHERE user_id=%s ORDER BY created_at DESC", (email,))
            rows = cur.fetchall()
        return {"items": [_row_to_guardian(r) for r in rows]}
    finally:
        _release(conn)


@router.post("/guardians")
def add_guardian(body: GuardianBody, request: Request):
    email = _require_email(request)
    if body.role not in ("family", "friend", "pastor", "small_group_leader",
                          "counselor", "doctor", "peer_companion"):
        raise HTTPException(status_code=400, detail="invalid role")
    if body.permissionLevel not in ("yellow", "orange", "red"):
        raise HTTPException(status_code=400, detail="invalid permissionLevel")
    conn = _db()
    try:
        gid = _uid()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO crisis_guardian_contacts (id, user_id, name, relationship, role, "
                "phone, email, notify_methods, permission_level, consent_enabled) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)",
                (gid, email, body.name, body.relationship, body.role, body.phone, body.email,
                 _jsonb(body.notifyMethods), body.permissionLevel, body.consentEnabled))
            cur.execute(f"SELECT {_GUARD_COLS} FROM crisis_guardian_contacts WHERE id=%s", (gid,))
            row = cur.fetchone()
        conn.commit()
        return {"guardian": _row_to_guardian(row)}
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail="add failed")
    finally:
        _release(conn)


@router.put("/guardians/{gid}")
def update_guardian(gid: str, body: GuardianBody, request: Request):
    email = _require_email(request)
    conn = _db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE crisis_guardian_contacts SET name=%s, relationship=%s, role=%s, phone=%s, "
                "email=%s, notify_methods=%s::jsonb, permission_level=%s, consent_enabled=%s, "
                "updated_at=NOW() WHERE id=%s AND user_id=%s",
                (body.name, body.relationship, body.role, body.phone, body.email,
                 _jsonb(body.notifyMethods), body.permissionLevel, body.consentEnabled, gid, email))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="not found")
            cur.execute(f"SELECT {_GUARD_COLS} FROM crisis_guardian_contacts WHERE id=%s", (gid,))
            row = cur.fetchone()
        conn.commit()
        return {"guardian": _row_to_guardian(row)}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail="update failed")
    finally:
        _release(conn)


@router.delete("/guardians/{gid}")
def delete_guardian(gid: str, request: Request):
    email = _require_email(request)
    conn = _db()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM crisis_guardian_contacts WHERE id=%s AND user_id=%s", (gid, email))
        conn.commit()
        return {"ok": True}
    finally:
        _release(conn)


# ─────────────────────────────────────────────────────────────────────────────
# escalation
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/escalate")
def escalate(body: EscalateBody, request: Request):
    email = _optional_email(request)
    level = body.level if body.level in ("yellow", "orange", "red") else "red"
    out: Dict[str, Any] = {
        "emergency": ce.red_emergency_message(body.locale),
        "guardianAlertText": ce.guardian_alert_text(level),
        "copyText": ce.emergency_copy_text(),
    }

    out["channelConfigured"] = notify.sms_configured()

    notified: List[Dict[str, Any]] = []
    if email and body.notifyGuardians:
        # 仅对已预授权（consent_enabled）且权限覆盖该等级的守护人发送。
        # 未配置发送通道时 send_sms 返回 not_configured：只记录意图，绝不泄露隐私。
        rank = {"yellow": 1, "orange": 2, "red": 3}
        eligible: List[Dict[str, Any]] = []
        conn = _db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, name, permission_level, notify_methods, phone, email "
                            "FROM crisis_guardian_contacts WHERE user_id=%s AND consent_enabled=TRUE",
                            (email,))
                for r in cur.fetchall():
                    if rank.get(r[2], 2) <= rank.get(level, 3):
                        eligible.append({"id": r[0], "name": r[1], "methods": r[3] or [],
                                         "phone": r[4] or "", "email": r[5] or ""})
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            _release(conn)

        for g in eligible:
            alert = ce.guardian_alert_text(level, g["name"])
            delivery = notify.send_notification(
                body=alert, methods=g["methods"], phone=g["phone"],
                meta={"level": level, "kind": "crisis_guardian_alert"})
            notified.append({"guardianId": g["id"], "name": g["name"],
                             "alertText": alert, "delivery": delivery})

        if body.eventId:
            _record_escalation(email, body.eventId, level, notified)

    out["guardiansNotified"] = notified
    out["anyDelivered"] = any(n.get("delivery", {}).get("ok") for n in notified)
    out["consentRequired"] = (not notified) and bool(body.notifyGuardians)
    return out


def _record_escalation(email: str, event_id: str, level: str, notified: List[Dict[str, Any]]) -> None:
    conn = _db()
    try:
        any_ok = any(n.get("delivery", {}).get("ok") for n in notified)
        action = {"at": datetime.now(timezone.utc).isoformat(), "level": level,
                  "guardianIds": [n["guardianId"] for n in notified],
                  "delivery": [{"guardianId": n["guardianId"],
                                "status": n.get("delivery", {}).get("status")} for n in notified]}
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE crisis_events SET escalation_actions = escalation_actions || %s::jsonb, "
                "guardian_notified = CASE WHEN %s THEN TRUE ELSE guardian_notified END "
                "WHERE id=%s AND user_id=%s",
                (json.dumps([action], ensure_ascii=False), any_ok, event_id, email))
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        _release(conn)


# ─────────────────────────────────────────────────────────────────────────────
# post-crisis follow-ups
# ─────────────────────────────────────────────────────────────────────────────

def _row_to_followup(row) -> Dict[str, Any]:
    return {"id": row[0], "eventId": row[1], "phase": row[2], "tasks": row[3],
            "completedTaskIds": row[4], "dueAt": _to_iso(row[5]), "status": row[6],
            "createdAt": _to_iso(row[7])}


_FU_COLS = "id, event_id, phase, tasks, completed_task_ids, due_at, status, created_at"


@router.post("/followups")
def create_followup(body: FollowupBody, request: Request):
    email = _require_email(request)
    if body.phase not in ce.POST_CRISIS_PHASES:
        raise HTTPException(status_code=400, detail="invalid phase")
    tasks = body.tasks if body.tasks is not None else ce.post_crisis_tasks(body.phase)
    due = datetime.now(timezone.utc) + timedelta(days=_PHASE_OFFSETS.get(body.phase, 1))
    conn = _db()
    try:
        fid = _uid()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO crisis_followups (id, user_id, event_id, phase, tasks, due_at) "
                "VALUES (%s,%s,%s,%s,%s::jsonb,%s)",
                (fid, email, body.eventId, body.phase, _jsonb(tasks), due))
            cur.execute(f"SELECT {_FU_COLS} FROM crisis_followups WHERE id=%s", (fid,))
            row = cur.fetchone()
        conn.commit()
        return {"followup": _row_to_followup(row)}
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail="create failed")
    finally:
        _release(conn)


@router.get("/followups")
def list_followups(request: Request):
    email = _require_email(request)
    conn = _db()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_FU_COLS} FROM crisis_followups WHERE user_id=%s "
                        "ORDER BY due_at ASC", (email,))
            rows = cur.fetchall()
        return {"items": [_row_to_followup(r) for r in rows]}
    finally:
        _release(conn)


@router.put("/followups/{fid}")
def update_followup(fid: str, body: FollowupUpdateBody, request: Request):
    email = _require_email(request)
    conn = _db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE crisis_followups SET completed_task_ids = COALESCE(%s::jsonb, completed_task_ids), "
                "status = COALESCE(%s, status), updated_at=NOW() WHERE id=%s AND user_id=%s",
                (_jsonb(body.completedTaskIds) if body.completedTaskIds is not None else None,
                 body.status, fid, email))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="not found")
            cur.execute(f"SELECT {_FU_COLS} FROM crisis_followups WHERE id=%s", (fid,))
            row = cur.fetchone()
        conn.commit()
        return {"followup": _row_to_followup(row)}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail="update failed")
    finally:
        _release(conn)


# ─────────────────────────────────────────────────────────────────────────────
# events (personal audit) + meta
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/events")
def list_events(request: Request, limit: int = Query(50)):
    email = _require_email(request)
    conn = _db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, risk_level, risk_types, workflow_started, guardian_notified, "
                        "user_acknowledged, created_at FROM crisis_events WHERE user_id=%s "
                        "ORDER BY created_at DESC LIMIT %s", (email, max(1, min(limit, 200))))
            rows = cur.fetchall()
        return {"items": [{"id": r[0], "riskLevel": r[1], "riskTypes": r[2],
                           "workflow": r[3], "guardianNotified": r[4],
                           "acknowledged": r[5], "createdAt": _to_iso(r[6])} for r in rows]}
    finally:
        _release(conn)


@router.post("/events/{eid}/ack")
def ack_event(eid: str, request: Request):
    email = _require_email(request)
    conn = _db()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE crisis_events SET user_acknowledged=TRUE WHERE id=%s AND user_id=%s",
                        (eid, email))
        conn.commit()
        return {"ok": True}
    finally:
        _release(conn)


@router.delete("/events/{eid}")
def delete_event(eid: str, request: Request):
    email = _require_email(request)
    conn = _db()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM crisis_events WHERE id=%s AND user_id=%s", (eid, email))
        conn.commit()
        return {"ok": True}
    finally:
        _release(conn)


# ─────────────────────────────────────────────────────────────────────────────
# 牧者/咨询师协作后台 — 基于明确授权、可撤销、按 scope 只读
# ─────────────────────────────────────────────────────────────────────────────

_SCOPES = ("status", "safety_plan", "events")
_CAREGIVER_ROLES = tuple(
    r.strip() for r in (os.getenv("CRISIS_CAREGIVER_ROLES", "pastor,counselor,small_group_leader").split(","))
    if r.strip()
) or ("pastor", "counselor", "small_group_leader")


def _norm_email(e: Optional[str]) -> str:
    return (e or "").strip().lower()


def _require_verified_caregiver(request: Request) -> str:
    """协作只对「邮箱注册且已验证」的账号开放（防冒名）。
    邮箱注册强制验证码、email 列唯一且不可改；微信账号 email 为空（拿不到 email 不会到这里）。
    这里再加一道防御：要求账号 login_type 为 email。"""
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    if (user.get("login_type") or "email") != "email":
        raise HTTPException(status_code=403, detail="caregiver access requires a verified email account")
    return _norm_email(user["email"])


class ShareBody(BaseModel):
    caregiverEmail: str
    caregiverName: str = ""
    caregiverRole: str = "pastor"
    contactPhone: str = ""
    expiresInDays: Optional[int] = None
    scope: List[str] = Field(default_factory=lambda: ["status", "safety_plan", "events"])


def _row_to_share(row) -> Dict[str, Any]:
    return {"id": row[0], "caregiverEmail": row[1], "caregiverName": row[2],
            "caregiverRole": row[3], "scope": row[4], "status": row[5], "createdAt": _to_iso(row[6]),
            "contactPhone": (row[7] if len(row) > 7 else ""),
            "expiresAt": _to_iso(row[8]) if len(row) > 8 and row[8] else None}


_SHARE_COLS = "id, caregiver_email, caregiver_name, caregiver_role, scope, status, created_at, contact_phone, expires_at"


def _share_expiry(days: Optional[int]):
    if days and int(days) > 0:
        return datetime.now(timezone.utc) + timedelta(days=min(int(days), 3650))
    return None


@router.post("/shares")
def create_share(body: ShareBody, request: Request):
    email = _require_email(request)
    ce_email = _norm_email(body.caregiverEmail)
    if not ce_email or "@" not in ce_email:
        raise HTTPException(status_code=400, detail="invalid caregiverEmail")
    if body.caregiverRole not in _CAREGIVER_ROLES:
        raise HTTPException(status_code=400, detail="invalid caregiverRole")
    scope = [s for s in (body.scope or []) if s in _SCOPES] or ["status"]
    conn = _db()
    try:
        sid = _uid()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO crisis_care_shares (id, user_id, caregiver_email, caregiver_name, "
                "caregiver_role, contact_phone, expires_at, scope) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb)",
                (sid, email, ce_email, body.caregiverName, body.caregiverRole,
                 (body.contactPhone or "").strip(), _share_expiry(body.expiresInDays), _jsonb(scope)))
            cur.execute(f"SELECT {_SHARE_COLS} FROM crisis_care_shares WHERE id=%s", (sid,))
            row = cur.fetchone()
            cur.execute("SELECT 1 FROM users WHERE LOWER(email)=%s LIMIT 1", (ce_email,))
            registered = cur.fetchone() is not None
        conn.commit()
        out = _row_to_share(row)
        out["caregiverRegistered"] = registered
        return {"share": out}
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail="share failed")
    finally:
        _release(conn)


@router.get("/shares")
def list_shares(request: Request):
    email = _require_email(request)
    conn = _db()
    try:
        items = []
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_SHARE_COLS} FROM crisis_care_shares "
                        "WHERE user_id=%s AND status='active' ORDER BY created_at DESC", (email,))
            rows = cur.fetchall()
            items = [_row_to_share(r) for r in rows]
            for it in items:
                cur.execute("SELECT COUNT(*), MAX(viewed_at) FROM crisis_share_views WHERE share_id=%s", (it["id"],))
                vc = cur.fetchone()
                it["viewCount"] = int(vc[0] or 0)
                it["lastViewedAt"] = _to_iso(vc[1])
                cur.execute("SELECT 1 FROM users WHERE LOWER(email)=%s LIMIT 1", (it["caregiverEmail"],))
                it["caregiverRegistered"] = cur.fetchone() is not None
        return {"items": items}
    finally:
        _release(conn)


@router.delete("/shares/{sid}")
def revoke_share(sid: str, request: Request):
    email = _require_email(request)
    conn = _db()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE crisis_care_shares SET status='revoked', revoked_at=NOW() "
                        "WHERE id=%s AND user_id=%s", (sid, email))
        conn.commit()
        return {"ok": True}
    finally:
        _release(conn)


@router.get("/caregiver/shares")
def caregiver_incoming(request: Request):
    me = _require_verified_caregiver(request)
    conn = _db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, user_id, caregiver_role, scope, created_at, last_viewed_at, "
                        "contact_phone FROM crisis_care_shares WHERE caregiver_email=%s "
                        "AND status='active' AND (expires_at IS NULL OR expires_at > NOW()) "
                        "ORDER BY created_at DESC", (me,))
            rows = cur.fetchall()
        return {"items": [{"id": r[0], "sharerEmail": _mask_email(r[1]), "caregiverRole": r[2],
                           "scope": r[3], "createdAt": _to_iso(r[4]), "lastViewedAt": _to_iso(r[5]),
                           "contactPhone": (r[6] or "") if len(r) > 6 else ""}
                          for r in rows]}
    finally:
        _release(conn)


@router.get("/caregiver/shares/{sid}")
def caregiver_view(sid: str, request: Request):
    me = _require_verified_caregiver(request)
    conn = _db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, scope, status, contact_phone, expires_at "
                        "FROM crisis_care_shares WHERE id=%s AND caregiver_email=%s", (sid, me))
            share = cur.fetchone()
            expired = bool(share and share[4] is not None and share[4] <= datetime.now(timezone.utc))
            if not share or share[2] != "active" or expired:
                raise HTTPException(status_code=404, detail="share not found, revoked, or expired")
            sharer, scope = share[0], (share[1] or [])
            summary: Dict[str, Any] = {"sharerEmail": _mask_email(sharer), "scope": scope,
                                       "contactPhone": (share[3] or "")}

            if "status" in scope:
                cur.execute("SELECT risk_level, created_at FROM crisis_events WHERE user_id=%s "
                            "ORDER BY created_at DESC LIMIT 1", (sharer,))
                row = cur.fetchone()
                summary["latestStatus"] = ({"riskLevel": row[0], "at": _to_iso(row[1])} if row else None)

            if "safety_plan" in scope:
                cur.execute(f"SELECT {_PLAN_COLS} FROM crisis_safety_plans WHERE user_id=%s "
                            "AND status='active' ORDER BY updated_at DESC LIMIT 1", (sharer,))
                prow = cur.fetchone()
                summary["safetyPlan"] = (_row_to_plan(prow) if prow else None)

            if "events" in scope:
                cur.execute("SELECT id, risk_level, risk_types, created_at FROM crisis_events "
                            "WHERE user_id=%s ORDER BY created_at DESC LIMIT 10", (sharer,))
                summary["recentEvents"] = [{"id": e[0], "riskLevel": e[1], "riskTypes": e[2],
                                            "createdAt": _to_iso(e[3])} for e in cur.fetchall()]

            cur.execute("INSERT INTO crisis_share_views (id, share_id, user_id, caregiver_email) "
                        "VALUES (%s,%s,%s,%s)", (_uid(), sid, sharer, me))
            cur.execute("UPDATE crisis_care_shares SET last_viewed_at=NOW() WHERE id=%s", (sid,))
        conn.commit()
        summary["disclaimer"] = ce.MODULE_DISCLAIMER
        return summary
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _release(conn)


class FormationSeedBody(BaseModel):
    riskTypes: Optional[List[str]] = None


@router.post("/bridge/formation-seed")
def bridge_formation_seed(body: FormationSeedBody, request: Request):
    """危机后 → 模式库的温柔桥接：返回一个可改的转化计划「种子」。
    不写入 spiritual-formation 表（由前端用用户自己的 token 调 spiritual-formation
    接口创建，确保 user_id 正确）。"""
    types = body.riskTypes
    email = _optional_email(request)
    if not types and email:
        conn = _db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT risk_types FROM crisis_events WHERE user_id=%s "
                            "ORDER BY created_at DESC LIMIT 5", (email,))
                agg: List[str] = []
                for r in cur.fetchall():
                    if isinstance(r[0], list):
                        agg.extend(r[0])
                types = agg
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            _release(conn)
    return ce.formation_seed(types or [])


@router.get("/shares/{sid}/views")
def list_share_views(sid: str, request: Request):
    """当事人查看「谁、何时」查看过自己的某条分享（透明审计）。仅分享者本人可读。"""
    email = _require_email(request)
    conn = _db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM crisis_care_shares WHERE id=%s AND user_id=%s", (sid, email))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="not found")
            cur.execute("SELECT caregiver_email, viewed_at FROM crisis_share_views "
                        "WHERE share_id=%s ORDER BY viewed_at DESC LIMIT 50", (sid,))
            rows = cur.fetchall()
        return {"items": [{"caregiverEmail": r[0], "viewedAt": _to_iso(r[1])} for r in rows]}
    except HTTPException:
        raise
    finally:
        _release(conn)


@router.get("/meta")
def meta():
    return {
        "riskLevels": list(ce.RISK_LEVELS),
        "riskTypes": list(ce.CRISIS_RISK_TYPES),
        "spiritualCrisisTypes": list(ce.SPIRITUAL_CRISIS_TYPES),
        "convictionVsCondemnation": ce.CONVICTION_VS_CONDEMNATION,
        "forbiddenPhrases": ce.FORBIDDEN_PHRASES,
        "escalationLevels": ce.escalation_levels(),
        "postCrisisPhases": list(ce.POST_CRISIS_PHASES),
        "addictionDomains": list(ce.ADDICTION_DOMAINS),
        "disclaimer": ce.MODULE_DISCLAIMER,
    }
