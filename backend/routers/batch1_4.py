"""Completion API for Spiritual Formation Batches 1, 3, and 4."""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

try:
    from batch1_4_engine import MODULES, build_summary, normalize_payload, orchestrate_intent, validate_record_type
except ImportError:  # pragma: no cover
    from backend.batch1_4_engine import MODULES, build_summary, normalize_payload, orchestrate_intent, validate_record_type

router = APIRouter(prefix="/api/spiritual-formation/batch1-4", tags=["spiritual-formation-batch1-4"])
_state: Dict[str, Any] = {}


def init_batch1_4_router(*, get_db, release_db, get_session_user, to_shanghai_iso, root_dir=None) -> None:
    _state.update(locals())
    _init_tables(get_db, release_db, root_dir)


def _init_tables(get_db, release_db, root_dir=None) -> None:
    base = Path(root_dir or Path(__file__).resolve().parents[2])
    path = base / "backend" / "migrations" / "0112_batch1_4_formation_records.sql"
    sql = path.read_text(encoding="utf-8")
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        release_db(conn)


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _json(value):
    if value is None:
        return {}
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return {}


def _as_date(value: str | date | datetime | None):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()


def _row(row, to_iso) -> dict:
    return {
        "id": row[0],
        "batch": row[2],
        "domain": row[3],
        "record_type": row[4],
        "payload": _json(row[5]),
        "occurred_on": str(row[6]) if row[6] else "",
        "status": row[7] or "active",
        "created_at": to_iso(row[8]),
        "updated_at": to_iso(row[9]),
    }


_COLS = "id, email, batch, domain, record_type, payload, occurred_on, status, created_at, updated_at"


class RecordBody(BaseModel):
    id: Optional[str] = Field(default=None, max_length=160)
    payload: Dict[str, Any] = Field(default_factory=dict)
    occurred_on: Optional[str] = Field(default=None, max_length=40)
    status: str = Field(default="active", max_length=40)


class IntentBody(BaseModel):
    text: str = Field(default="", max_length=6000)
    domain: Optional[str] = Field(default=None, max_length=40)


@router.get("/meta")
def meta() -> dict:
    return {"ok": True, "modules": MODULES}


@router.post("/orchestrate")
def orchestrate(body: IntentBody) -> dict:
    return {"ok": True, **orchestrate_intent(body.text, domain=body.domain)}


@router.post("/records/{domain}/{record_type}")
def save_record(domain: str, record_type: str, request: Request, body: RecordBody) -> dict:
    user = _require_user(request)
    try:
        validate_record_type(domain, record_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    rid = body.id or str(body.payload.get("id") or f"{domain}_{record_type}_{uuid.uuid4().hex}")
    payload = normalize_payload(body.payload, fallback_id=rid, email=user["email"])
    status = body.status or str(payload.get("status") or "active")
    occurred_on = _as_date(body.occurred_on or payload.get("date") or payload.get("sessionDate") or payload.get("checkinDate"))
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO formation_batch1_4_records
                    (id, email, batch, domain, record_type, payload, occurred_on, status)
                VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s,%s)
                ON CONFLICT (email, id) DO UPDATE SET
                    batch=EXCLUDED.batch,
                    domain=EXCLUDED.domain,
                    record_type=EXCLUDED.record_type,
                    payload=EXCLUDED.payload,
                    occurred_on=EXCLUDED.occurred_on,
                    status=EXCLUDED.status,
                    updated_at=NOW()
                """,
                (
                    rid,
                    user["email"],
                    MODULES[domain]["batch"],
                    domain,
                    record_type,
                    json.dumps(payload, ensure_ascii=False),
                    occurred_on,
                    status,
                ),
            )
            conn.commit()
            cur.execute(f"SELECT {_COLS} FROM formation_batch1_4_records WHERE id=%s AND email=%s", (rid, user["email"]))
            row = cur.fetchone()
    except HTTPException:
        raise
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="save failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "record": _row(row, to_iso)}


@router.get("/records/{domain}/{record_type}")
def list_records(
    domain: str,
    record_type: str,
    request: Request,
    status: Optional[str] = Query(default=None, max_length=40),
    limit: int = Query(default=200, ge=1, le=500),
) -> dict:
    user = _require_user(request)
    try:
        validate_record_type(domain, record_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    params: list[Any] = [user["email"], domain, record_type]
    status_sql = ""
    if status:
        status_sql = " AND status=%s"
        params.append(status)
    params.append(limit)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_COLS} FROM formation_batch1_4_records "
                f"WHERE email=%s AND domain=%s AND record_type=%s{status_sql} "
                "ORDER BY updated_at DESC LIMIT %s",
                tuple(params),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "items": [_row(r, to_iso) for r in rows]}


@router.get("/records/{domain}/{record_type}/{record_id}")
def get_record(domain: str, record_type: str, record_id: str, request: Request) -> dict:
    user = _require_user(request)
    try:
        validate_record_type(domain, record_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_COLS} FROM formation_batch1_4_records "
                "WHERE id=%s AND email=%s AND domain=%s AND record_type=%s",
                (record_id, user["email"], domain, record_type),
            )
            row = cur.fetchone()
    finally:
        _state["release_db"](conn)
    if not row:
        raise HTTPException(status_code=404, detail="record not found")
    return {"ok": True, "record": _row(row, to_iso)}


@router.delete("/records/{domain}/{record_type}/{record_id}")
def delete_record(domain: str, record_type: str, record_id: str, request: Request) -> dict:
    user = _require_user(request)
    try:
        validate_record_type(domain, record_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM formation_batch1_4_records WHERE id=%s AND email=%s AND domain=%s AND record_type=%s",
                (record_id, user["email"], domain, record_type),
            )
            deleted = cur.rowcount
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="delete failed")
    finally:
        _state["release_db"](conn)
    if not deleted:
        raise HTTPException(status_code=404, detail="record not found")
    return {"ok": True}


@router.get("/summary")
def summary(request: Request, limit: int = Query(default=500, ge=1, le=1000)) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_COLS} FROM formation_batch1_4_records WHERE email=%s ORDER BY updated_at DESC LIMIT %s",
                (user["email"], limit),
            )
            rows = [_row(r, to_iso) for r in cur.fetchall()]
    finally:
        _state["release_db"](conn)
    return {"ok": True, "summary": build_summary(rows)}
