"""
Waiting router — 等候之路 / Waiting Transformation Module

Endpoints (prefix /api/waiting):
  GET  /meta                              静态配置 (维度 / 类型标签 / 7 天模板)
  GET  /cases                             列出我的等待案例
  POST /cases                             新建等待案例
  GET  /cases/{id}                        案例详情 (含分析 / 操练 / 复盘)
  POST /cases/{id}/analyze                运行分析 (确定性 + 可选 AI)
  POST /cases/{id}/practices/generate     生成 7 天操练计划
  POST /cases/{id}/reflect                提交一次复盘
  POST /practices/{id}/complete           完成某天操练 + 反思

不定罪、不贴标签，是反思 / 分辨 / 陪伴式功能。用户以 email 标识。
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

try:
    from backend import waiting_engine as engine
except Exception:  # pragma: no cover
    import waiting_engine as engine  # type: ignore

try:
    from backend.core.config import settings as _settings
except Exception:  # pragma: no cover
    try:
        from core.config import settings as _settings
    except Exception:
        _settings = None

router = APIRouter(prefix="/api/waiting", tags=["waiting"])

_state: Dict[str, Any] = {}


def init_waiting_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _Json(obj):
    try:
        from psycopg2.extras import Json
        return Json(obj)
    except Exception:
        import json as _json
        return _json.dumps(obj)


def _case_row_to_dict(row, to_iso) -> dict:
    return {
        "id": row[0], "email": row[1],
        "waiting_for": row[2], "waiting_description": row[3] or "",
        "waiting_type": row[4] or "unknown",
        "anxiety_level": row[5], "hope_level": row[6], "passivity_level": row[7],
        "fantasy_level": row[8], "trust_level": row[9], "obedience_readiness": row[10],
        "action_clarity": row[11],
        "idolatry_risk": row[12], "emotional_dependency": row[13],
        "responsibility_alignment": row[14],
        "analysis_json": row[15] or {},
        "guidance_text": row[16] or "",
        "created_at": to_iso(row[17]), "updated_at": to_iso(row[18]),
    }


_CASE_COLS = (
    "id, email, waiting_for, waiting_description, waiting_type, "
    "anxiety_level, hope_level, passivity_level, fantasy_level, trust_level, "
    "obedience_readiness, action_clarity, idolatry_risk, emotional_dependency, "
    "responsibility_alignment, analysis_json, guidance_text, created_at, updated_at"
)


def _fetch_case(cur, case_id: str, email: str):
    cur.execute(
        f"SELECT {_CASE_COLS} FROM waiting_cases WHERE id=%s AND email=%s",
        (case_id, email),
    )
    return cur.fetchone()


# ── Request models ────────────────────────────────────────────────────────────
class CreateCaseRequest(BaseModel):
    waiting_for: str = Field(min_length=1, max_length=500)
    waiting_description: str = Field(default="", max_length=4000)
    anxiety_level: float = Field(default=0, ge=0, le=10)
    hope_level: float = Field(default=0, ge=0, le=10)
    passivity_level: float = Field(default=0, ge=0, le=10)
    fantasy_level: float = Field(default=0, ge=0, le=10)
    trust_level: float = Field(default=0, ge=0, le=10)
    obedience_readiness: float = Field(default=0, ge=0, le=10)
    action_clarity: float = Field(default=0, ge=0, le=10)


class AnalyzeRequest(BaseModel):
    use_ai: bool = True


class ReflectRequest(BaseModel):
    reflection_text: str = Field(default="", max_length=4000)
    anxiety_level: float = Field(default=0, ge=0, le=10)
    hope_level: float = Field(default=0, ge=0, le=10)
    trust_level: float = Field(default=0, ge=0, le=10)
    leaning: str = Field(default="", max_length=20)
    action_taken: str = Field(default="", max_length=2000)


class CompletePracticeRequest(BaseModel):
    user_reflection: str = Field(default="", max_length=4000)
    completed: bool = True


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.get("/meta")
def get_meta() -> dict:
    return {"ok": True, **engine.meta()}


@router.get("/cases")
def list_cases(request: Request, limit: int = Query(default=30, ge=1, le=100)) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_CASE_COLS} FROM waiting_cases WHERE email=%s "
                "ORDER BY created_at DESC LIMIT %s",
                (user["email"], limit),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "count": len(rows),
            "cases": [_case_row_to_dict(r, to_iso) for r in rows]}


@router.post("/cases")
def create_case(request: Request, body: CreateCaseRequest) -> dict:
    user = _require_user(request)
    email = user["email"]
    case_id = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO waiting_cases "
                "(id, email, waiting_for, waiting_description, anxiety_level, hope_level, "
                " passivity_level, fantasy_level, trust_level, obedience_readiness, action_clarity) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (case_id, email, body.waiting_for.strip(), body.waiting_description.strip(),
                 body.anxiety_level, body.hope_level, body.passivity_level,
                 body.fantasy_level, body.trust_level, body.obedience_readiness,
                 body.action_clarity),
            )
            conn.commit()
            row = _fetch_case(cur, case_id, email)
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"create failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "case": _case_row_to_dict(row, _state["to_shanghai_iso"])}


@router.post("/cases/{case_id}/analyze")
def analyze_case(case_id: str, request: Request, body: AnalyzeRequest) -> dict:
    user = _require_user(request)
    email = user["email"]
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            row = _fetch_case(cur, case_id, email)
            if not row:
                raise HTTPException(status_code=404, detail="case not found")
            case = _case_row_to_dict(row, to_iso)
            result = engine.analyze(case, settings=_settings, use_ai=body.use_ai)
            cur.execute(
                "UPDATE waiting_cases SET waiting_type=%s, idolatry_risk=%s, "
                "emotional_dependency=%s, responsibility_alignment=%s, "
                "analysis_json=%s, guidance_text=%s, updated_at=NOW() "
                "WHERE id=%s AND email=%s",
                (result["waiting_type"], result["idolatry_risk"],
                 result["emotional_dependency"], result["responsibility_alignment"],
                 _Json(result), "\n".join(result.get("guidance", [])),
                 case_id, email),
            )
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"analyze failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "case_id": case_id, **result}


@router.post("/cases/{case_id}/practices/generate")
def generate_practices(case_id: str, request: Request) -> dict:
    user = _require_user(request)
    email = user["email"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            row = _fetch_case(cur, case_id, email)
            if not row:
                raise HTTPException(status_code=404, detail="case not found")
            cur.execute("SELECT COUNT(*) FROM waiting_practices WHERE waiting_case_id=%s",
                        (case_id,))
            if cur.fetchone()[0] == 0:
                for d in engine.default_7_day_plan():
                    cur.execute(
                        "INSERT INTO waiting_practices "
                        "(id, waiting_case_id, day_index, practice_title, practice_content, "
                        " reflection_prompt) VALUES (%s,%s,%s,%s,%s,%s)",
                        (uuid.uuid4().hex, case_id, d["day_index"], d["practice_title"],
                         d["practice_content"], d["reflection_prompt"]),
                    )
                conn.commit()
            practices = _load_practices(cur, case_id)
    except HTTPException:
        raise
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"generate failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "case_id": case_id, "practices": practices}


def _load_practices(cur, case_id: str) -> List[dict]:
    cur.execute(
        "SELECT id, day_index, practice_title, practice_content, reflection_prompt, "
        "completed, user_reflection FROM waiting_practices "
        "WHERE waiting_case_id=%s ORDER BY day_index",
        (case_id,),
    )
    return [{
        "id": r[0], "day_index": r[1], "practice_title": r[2],
        "practice_content": r[3], "reflection_prompt": r[4],
        "completed": r[5], "user_reflection": r[6] or "",
    } for r in cur.fetchall()]


def _load_reflections(cur, case_id: str, to_iso) -> List[dict]:
    cur.execute(
        "SELECT id, reflection_text, anxiety_level, hope_level, trust_level, leaning, "
        "action_taken, created_at FROM waiting_reflections "
        "WHERE waiting_case_id=%s ORDER BY created_at DESC",
        (case_id,),
    )
    return [{
        "id": r[0], "reflection_text": r[1] or "", "anxiety_level": r[2],
        "hope_level": r[3], "trust_level": r[4], "leaning": r[5] or "",
        "action_taken": r[6] or "", "created_at": to_iso(r[7]),
    } for r in cur.fetchall()]


@router.get("/cases/{case_id}")
def get_case(case_id: str, request: Request) -> dict:
    user = _require_user(request)
    email = user["email"]
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            row = _fetch_case(cur, case_id, email)
            if not row:
                raise HTTPException(status_code=404, detail="case not found")
            case = _case_row_to_dict(row, to_iso)
            practices = _load_practices(cur, case_id)
            reflections = _load_reflections(cur, case_id, to_iso)
    finally:
        _state["release_db"](conn)
    return {"ok": True, "case": case, "analysis": case.get("analysis_json") or {},
            "practices": practices, "reflections": reflections}


@router.post("/cases/{case_id}/reflect")
def reflect(case_id: str, request: Request, body: ReflectRequest) -> dict:
    user = _require_user(request)
    email = user["email"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            row = _fetch_case(cur, case_id, email)
            if not row:
                raise HTTPException(status_code=404, detail="case not found")
            rid = uuid.uuid4().hex
            cur.execute(
                "INSERT INTO waiting_reflections "
                "(id, waiting_case_id, email, reflection_text, anxiety_level, hope_level, "
                " trust_level, leaning, action_taken) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (rid, case_id, email, body.reflection_text.strip(), body.anxiety_level,
                 body.hope_level, body.trust_level, body.leaning, body.action_taken.strip()),
            )
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"reflect failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "reflection_id": rid}


@router.post("/practices/{practice_id}/complete")
def complete_practice(practice_id: str, request: Request, body: CompletePracticeRequest) -> dict:
    user = _require_user(request)
    email = user["email"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            # 校验归属：practice → case → email
            cur.execute(
                "SELECT p.id FROM waiting_practices p "
                "JOIN waiting_cases c ON c.id = p.waiting_case_id "
                "WHERE p.id=%s AND c.email=%s",
                (practice_id, email),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="practice not found")
            cur.execute(
                "UPDATE waiting_practices SET completed=%s, user_reflection=%s, updated_at=NOW() "
                "WHERE id=%s",
                (body.completed, body.user_reflection.strip(), practice_id),
            )
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"complete failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "practice_id": practice_id}
