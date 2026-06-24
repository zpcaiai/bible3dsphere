"""
Theological Safety router — 神学安全审查 (/api/theological-safety)

  GET  /api/theological-safety/meta      审查维度 + 状态枚举
  POST /api/theological-safety/review    审查一段（将展示给用户的）AI 内容
  GET  /api/theological-safety/history   本人历史审查记录

把规格 Skill 9 落地：所有展示给用户的 AI 输出都可先经此审查，
结果写入 theological_review_logs，运行写入 agent_runs（含可观测性字段）。
用户以 email 标识。其它路由可 import safety_review_and_log() 复用。
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

try:
    from backend import theological_safety_engine as engine
except Exception:  # pragma: no cover
    import theological_safety_engine as engine  # type: ignore

router = APIRouter(prefix="/api/theological-safety", tags=["theological-safety"])
_state: Dict[str, Any] = {}


def init_theological_safety_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
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


def _as_uuid(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    try:
        return str(uuid.UUID(str(val)))
    except Exception:
        return None


def safety_review_and_log(email: Optional[str], content: str, content_type: str = "generic",
                          content_id: Optional[str] = None, use_ai: bool = False,
                          model_name: str = "") -> Dict[str, Any]:
    """运行审查 + 落库（theological_review_logs + agent_runs）。可被其它路由复用。

    依赖 init_theological_safety_router() 已注入 get_db/release_db。
    返回引擎结果，并附 review_id / agent_run_id。
    """
    get_db = _state.get("get_db")
    release_db = _state.get("release_db")

    t0 = time.perf_counter()
    error_message = ""
    try:
        result = engine.analyze(content, content_type=content_type, use_ai=use_ai)
        status = "DONE"
    except Exception as exc:  # 引擎不该抛，但保底
        result = {"review_status": "needs_revision", "detected_issues": [],
                  "corrected_content": None,
                  "reviewer_notes": f"审查引擎异常，已保守标记需复核：{exc}",
                  "dimensions_checked": []}
        status = "FAILED"
        error_message = str(exc)
    latency_ms = int((time.perf_counter() - t0) * 1000)

    review_id = uuid.uuid4().hex
    agent_run_id = None
    if get_db is None:  # 未注入 DB（如单测）→ 只返回结果
        result["review_id"] = review_id
        result["agent_run_id"] = None
        return result

    conn = get_db()
    try:
        with conn.cursor() as cur:
            # 1) 运行记录（演示 0074 可观测性字段）
            cur.execute(
                "INSERT INTO agent_runs "
                "(email, agent_name, skill_name, event_type, input_payload, output_payload, "
                " status, model_name, latency_ms, error_message) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (email or "", "TheologicalSafetyAgent", "theological_safety",
                 f"review:{content_type}",
                 _Json({"content_excerpt": (content or "")[:500], "content_type": content_type}),
                 _Json(result), status, model_name, latency_ms, error_message),
            )
            agent_run_id = cur.fetchone()[0]

            # 2) 审查日志
            cur.execute(
                "INSERT INTO theological_review_logs "
                "(id, email, agent_run_id, content_type, content_id, content_excerpt, "
                " review_status, detected_issues, corrected_content, reviewer_notes, reviewer) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (review_id, email, agent_run_id, content_type, _as_uuid(content_id),
                 (content or "")[:1000], result["review_status"],
                 _Json(result.get("detected_issues", [])), result.get("corrected_content"),
                 result.get("reviewer_notes", ""), "agent"),
            )
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        # 落库失败不应阻断审查本身——把结果返回，标注未落库
        result["persist_error"] = str(exc)
    finally:
        release_db(conn)

    result["review_id"] = review_id
    result["agent_run_id"] = agent_run_id
    return result


class ReviewBody(BaseModel):
    content: str = Field(..., min_length=1, max_length=12000)
    content_type: str = Field(default="generic", max_length=60)
    content_id: Optional[str] = Field(default=None, max_length=64)
    use_ai: bool = False


@router.get("/meta")
def get_meta() -> dict:
    return {"ok": True, **engine.meta()}


@router.post("/review")
def review(request: Request, body: ReviewBody) -> dict:
    user = _require_user(request)
    result = safety_review_and_log(
        email=user["email"], content=body.content, content_type=body.content_type,
        content_id=body.content_id, use_ai=body.use_ai,
    )
    return {"ok": True, **result}


@router.get("/history")
def history(request: Request, limit: int = Query(default=20, ge=1, le=100)) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, content_type, review_status, detected_issues, reviewer_notes, created_at "
                "FROM theological_review_logs WHERE email=%s ORDER BY created_at DESC LIMIT %s",
                (user["email"], limit),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    items = [{
        "id": r[0], "content_type": r[1], "review_status": r[2],
        "detected_issues": r[3], "reviewer_notes": r[4], "created_at": to_iso(r[5]),
    } for r in rows]
    return {"ok": True, "count": len(items), "items": items}
