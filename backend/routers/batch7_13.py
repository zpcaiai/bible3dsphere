"""Backend API for Spiritual Planet Batches 7-13.

Prefix: /api/formation-os

This router provides a production-shaped backend boundary for the modules that
were prototyped in the frontend:
- Batch 7 Community / Accountability / Discipleship
- Batch 8 Gift / Calling / Mission
- Batch 9 Bible Doctrine
- Batch 10 AI Formation Agent
- Batch 11 Analytics
- Batch 12 Productization
- Batch 13 Master Build
"""
from __future__ import annotations

from typing import Annotated, Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field

try:
    from backend import batch7_13_engine as engine
except Exception:  # pragma: no cover
    import batch7_13_engine as engine


router = APIRouter(prefix="/api/formation-os", tags=["formation-os"])
_state: Dict[str, Any] = {}
_memory_records: list[dict[str, Any]] = []
BatchParam = Annotated[int, Path(ge=7, le=13)]
BatchQuery = Annotated[Optional[int], Query(ge=7, le=13)]
RecordTypeQuery = Annotated[Optional[str], Query(min_length=1, max_length=80)]


def init_batch7_13_router(*, get_db=None, release_db=None, get_session_user=None, to_shanghai_iso=None) -> None:
    _state.update({
        "get_db": get_db,
        "release_db": release_db,
        "get_session_user": get_session_user,
        "to_shanghai_iso": to_shanghai_iso,
    })


def _require_user(request: Request) -> dict:
    getter = _state.get("get_session_user")
    if not getter:
        return {"email": "local-dev@example.com"}
    user = getter(request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _db_available() -> bool:
    return bool(_state.get("get_db") and _state.get("release_db"))


def _save_records(records: list[dict[str, Any]]) -> None:
    if not _db_available():
        _memory_records[:0] = records
        return
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            for record in records:
                cur.execute(
                    """
                    INSERT INTO formation_os_records
                    (id, email, batch, module_key, record_type, payload)
                    VALUES (%s,%s,%s,%s,%s,%s::jsonb)
                    ON CONFLICT (id) DO UPDATE SET
                      payload=EXCLUDED.payload,
                      updated_at=now()
                    """,
                    (
                        record["id"],
                        record["email"],
                        record["batch"],
                        record["module_key"],
                        record["record_type"],
                        _json_dumps(record["payload"]),
                    ),
                )
                cur.execute(
                    """
                    INSERT INTO formation_os_events
                    (email, batch, module_key, event_type, source_record_id, payload)
                    VALUES (%s,%s,%s,%s,%s,%s::jsonb)
                    """,
                    (
                        record["email"],
                        record["batch"],
                        record["module_key"],
                        f"{record['record_type']}_created",
                        record["id"],
                        _json_dumps({"record_type": record["record_type"]}),
                    ),
                )
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        _state["release_db"](conn)


def _json_dumps(value: Any) -> str:
    import json
    return json.dumps(value, ensure_ascii=False)


def _list_records(email: str, batch: Optional[int] = None, record_type: Optional[str] = None) -> list[dict[str, Any]]:
    if not _db_available():
        rows = [r for r in _memory_records if r.get("email") == email]
        if batch is not None:
            rows = [r for r in rows if r.get("batch") == batch]
        if record_type:
            rows = [r for r in rows if r.get("record_type") == record_type]
        return rows
    conn = _state["get_db"]()
    try:
        clauses = ["email=%s"]
        params: list[Any] = [email]
        if batch is not None:
            clauses.append("batch=%s")
            params.append(batch)
        if record_type:
            clauses.append("record_type=%s")
            params.append(record_type)
        where = " AND ".join(clauses)
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, email, batch, module_key, record_type, payload, created_at, updated_at
                FROM formation_os_records
                WHERE {where}
                ORDER BY created_at DESC
                LIMIT 500
                """,
                tuple(params),
            )
            return [
                {
                    "id": row[0],
                    "email": row[1],
                    "batch": row[2],
                    "module_key": row[3],
                    "record_type": row[4],
                    "payload": row[5] or {},
                    "created_at": _to_iso(row[6]),
                    "updated_at": _to_iso(row[7]),
                }
                for row in cur.fetchall()
            ]
    finally:
        _state["release_db"](conn)


def _to_iso(value: Any) -> str:
    if value is None:
        return ""
    converter = _state.get("to_shanghai_iso")
    if converter:
        return converter(value)
    return str(value)


class IntentBody(BaseModel):
    intent_text: str = Field(default="", max_length=8000)
    context: Dict[str, Any] = Field(default_factory=dict)


class ArtifactBody(BaseModel):
    context: Dict[str, Any] = Field(default_factory=dict)


@router.get("/registry")
def registry(request: Request) -> dict:
    _require_user(request)
    return {"ok": True, **engine.module_registry()}


@router.get("/roadmap")
def roadmap(request: Request) -> dict:
    _require_user(request)
    return {"ok": True, "roadmap": engine.roadmap()}


@router.get("/batches/{batch}/dashboard")
def batch_dashboard(batch: BatchParam, request: Request) -> dict:
    user = _require_user(request)
    if batch not in engine.BATCHES:
        raise HTTPException(status_code=404, detail="unsupported batch")
    records = _list_records(user["email"], batch=batch)
    return {"ok": True, "dashboard": engine.dashboard(batch, records), "records": records}


@router.post("/batches/{batch}/orchestrate")
def batch_orchestrate(batch: BatchParam, body: IntentBody, request: Request) -> dict:
    _require_user(request)
    try:
        route = engine.orchestrate(batch, body.intent_text, body.context)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"ok": True, "route": route}


@router.post("/batches/{batch}/artifacts")
def create_batch_artifacts(batch: BatchParam, body: ArtifactBody, request: Request) -> dict:
    user = _require_user(request)
    try:
        records = engine.create_artifacts(batch, user["email"], body.context)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    try:
        _save_records(records)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"persist failed: {exc}")
    return {"ok": True, "records": records, "dashboard": engine.dashboard(batch, _list_records(user["email"], batch=batch))}


@router.get("/records")
def list_records(request: Request, batch: BatchQuery = None, record_type: RecordTypeQuery = None) -> dict:
    user = _require_user(request)
    return {"ok": True, "records": _list_records(user["email"], batch=batch, record_type=record_type)}


@router.get("/bible/graph-search")
def bible_graph_search(request: Request, query: str = Query(default="", max_length=200)) -> dict:
    _require_user(request)
    return {"ok": True, "result": engine.bible_graph_search(query)}


@router.post("/safety/route")
def safety_route(body: IntentBody, request: Request) -> dict:
    _require_user(request)
    return {"ok": True, "safety": engine.safety_scan(body.intent_text, body.context.get("source", "formation_os"))}
