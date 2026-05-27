"""
Journal router — devotion journals & sermon journals.
Covers: /api/devotion/journals, /api/sermon/journals
"""
from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator

router = APIRouter(prefix="/api", tags=["journal"])

_state: dict[str, Any] = {}


def init_journal_router(
    *,
    get_db,
    release_db,
    get_session_user,
    sanitize_text,
    validate_date_str,
    to_shanghai_iso,
) -> None:
    _state.update(locals())


# ── Helpers ───────────────────────────────────────────────────────────────────

def _row_to_journal(row) -> dict:
    s = _state["to_shanghai_iso"]
    return {
        "id": row[0], "email": row[1],
        "date": str(row[2]) if row[2] else "",
        "title": row[3] or "", "scripture": row[4] or "",
        "observation": row[5] or "", "reflection": row[6] or "",
        "application": row[7] or "", "prayer": row[8] or "",
        "mood": row[9] or "",
        "created_at": s(row[10]), "updated_at": s(row[11]),
    }


def _row_to_sermon(row) -> dict:
    s = _state["to_shanghai_iso"]
    return {
        "id": row[0], "email": row[1],
        "sermon_date": str(row[2]) if row[2] else "",
        "preacher": row[3] or "", "sermon_title": row[4] or "",
        "scripture_refs": row[5] or "", "key_points": row[6] or "",
        "personal_application": row[7] or "", "prayer_response": row[8] or "",
        "questions": row[9] or "", "notes": row[10] or "",
        "created_at": s(row[11]), "updated_at": s(row[12]),
    }


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ── Request models ────────────────────────────────────────────────────────────

class DevotionJournalSaveRequest(BaseModel):
    date: str = Field(min_length=1, max_length=10)
    title: str = Field(default="", max_length=200)
    scripture: str = Field(default="", max_length=500)
    observation: str = Field(default="", max_length=2000)
    reflection: str = Field(default="", max_length=2000)
    application: str = Field(default="", max_length=2000)
    prayer: str = Field(default="", max_length=2000)
    mood: str = Field(default="", max_length=20)

    @field_validator("date")
    @classmethod
    def validate_date(cls, v):
        return _state["validate_date_str"](v)


class SermonJournalSaveRequest(BaseModel):
    sermon_date: str = Field(min_length=1, max_length=10)
    preacher: str = Field(default="", max_length=100)
    sermon_title: str = Field(default="", max_length=300)
    scripture_refs: str = Field(default="", max_length=500)
    key_points: str = Field(default="", max_length=3000)
    personal_application: str = Field(default="", max_length=2000)
    prayer_response: str = Field(default="", max_length=2000)
    questions: str = Field(default="", max_length=1000)
    notes: str = Field(default="", max_length=2000)

    @field_validator("sermon_date")
    @classmethod
    def validate_date(cls, v):
        return _state["validate_date_str"](v)


# ── Devotion journals ─────────────────────────────────────────────────────────

@router.get("/devotion/journals")
def get_journals(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    user = _require_user(request)
    email = user["email"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, journal_date, title, scripture_text, observation, reflection, "
                "application, prayer, mood, created_at, updated_at "
                "FROM devotion_journals WHERE email=%s AND deleted_at IS NULL "
                "ORDER BY updated_at DESC LIMIT %s OFFSET %s",
                (email, min(limit, 200), offset),
            )
            rows = cur.fetchall()
            cur.execute(
                "SELECT COUNT(*) FROM devotion_journals WHERE email=%s AND deleted_at IS NULL",
                (email,),
            )
            total = cur.fetchone()[0]
        return {"ok": True, "items": [_row_to_journal(r) for r in rows], "total": total}
    finally:
        _state["release_db"](conn)


@router.post("/devotion/journals")
def save_journal(payload: DevotionJournalSaveRequest, request: Request) -> dict:
    user = _require_user(request)
    email = user["email"]
    san = _state["sanitize_text"]
    s_title = san(payload.title); s_scripture = san(payload.scripture)
    s_obs = san(payload.observation); s_ref = san(payload.reflection)
    s_app = san(payload.application); s_prayer = san(payload.prayer)
    s_mood = san(payload.mood)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM devotion_journals WHERE email=%s AND journal_date=%s",
                (email, payload.date),
            )
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    "UPDATE devotion_journals SET title=%s, scripture_text=%s, observation=%s, "
                    "reflection=%s, application=%s, prayer=%s, mood=%s, updated_at=NOW() "
                    "WHERE email=%s AND journal_date=%s",
                    (s_title, s_scripture, s_obs, s_ref, s_app, s_prayer, s_mood, email, payload.date),
                )
                jid = existing[0]
            else:
                cur.execute(
                    "INSERT INTO devotion_journals "
                    "(email, journal_date, title, scripture_text, observation, reflection, application, prayer, mood) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                    (email, payload.date, s_title, s_scripture, s_obs, s_ref, s_app, s_prayer, s_mood),
                )
                jid = cur.fetchone()[0]
            conn.commit()
            cur.execute(
                "SELECT id, email, journal_date, title, scripture_text, observation, reflection, "
                "application, prayer, mood, created_at, updated_at FROM devotion_journals WHERE id=%s",
                (jid,),
            )
            row = cur.fetchone()
        return {"ok": True, "journal": _row_to_journal(row)}
    finally:
        _state["release_db"](conn)


@router.get("/devotion/journals/{journal_id}")
def get_journal(journal_id: int, request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, journal_date, title, scripture_text, observation, reflection, "
                "application, prayer, mood, created_at, updated_at "
                "FROM devotion_journals WHERE id=%s AND email=%s AND deleted_at IS NULL",
                (journal_id, user["email"]),
            )
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Journal not found")
        return {"ok": True, "journal": _row_to_journal(row)}
    finally:
        _state["release_db"](conn)


@router.delete("/devotion/journals/{journal_id}")
def delete_journal(journal_id: int, request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE devotion_journals SET deleted_at=NOW() "
                "WHERE id=%s AND email=%s AND deleted_at IS NULL RETURNING id",
                (journal_id, user["email"]),
            )
            row = cur.fetchone()
            conn.commit()
        if not row:
            raise HTTPException(status_code=404, detail="Journal not found")
        return {"ok": True}
    finally:
        _state["release_db"](conn)


# ── Sermon journals ───────────────────────────────────────────────────────────

@router.get("/sermon/journals")
def get_sermon_journals(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, sermon_date, preacher, sermon_title, scripture_refs, key_points, "
                "personal_application, prayer_response, questions, notes, created_at, updated_at "
                "FROM sermon_journals WHERE email=%s AND deleted_at IS NULL "
                "ORDER BY updated_at DESC LIMIT %s OFFSET %s",
                (user["email"], min(limit, 200), offset),
            )
            rows = cur.fetchall()
            cur.execute(
                "SELECT COUNT(*) FROM sermon_journals WHERE email=%s AND deleted_at IS NULL",
                (user["email"],),
            )
            total = cur.fetchone()[0]
        return {"ok": True, "items": [_row_to_sermon(r) for r in rows], "total": total}
    finally:
        _state["release_db"](conn)


@router.post("/sermon/journals")
def save_sermon_journal(payload: SermonJournalSaveRequest, request: Request) -> dict:
    user = _require_user(request)
    email = user["email"]
    san = _state["sanitize_text"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM sermon_journals WHERE email=%s AND sermon_date=%s",
                (email, payload.sermon_date),
            )
            existing = cur.fetchone()
            vals = (
                san(payload.preacher), san(payload.sermon_title), san(payload.scripture_refs),
                san(payload.key_points), san(payload.personal_application),
                san(payload.prayer_response), san(payload.questions), san(payload.notes),
            )
            if existing:
                cur.execute(
                    "UPDATE sermon_journals SET preacher=%s, sermon_title=%s, scripture_refs=%s, "
                    "key_points=%s, personal_application=%s, prayer_response=%s, questions=%s, "
                    "notes=%s, updated_at=NOW() WHERE email=%s AND sermon_date=%s",
                    (*vals, email, payload.sermon_date),
                )
                sid = existing[0]
            else:
                cur.execute(
                    "INSERT INTO sermon_journals "
                    "(email, sermon_date, preacher, sermon_title, scripture_refs, key_points, "
                    "personal_application, prayer_response, questions, notes) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                    (email, payload.sermon_date, *vals),
                )
                sid = cur.fetchone()[0]
            conn.commit()
            cur.execute(
                "SELECT id, email, sermon_date, preacher, sermon_title, scripture_refs, key_points, "
                "personal_application, prayer_response, questions, notes, created_at, updated_at "
                "FROM sermon_journals WHERE id=%s",
                (sid,),
            )
            row = cur.fetchone()
        return {"ok": True, "journal": _row_to_sermon(row)}
    finally:
        _state["release_db"](conn)


@router.get("/sermon/journals/{journal_id}")
def get_sermon_journal(journal_id: int, request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, sermon_date, preacher, sermon_title, scripture_refs, key_points, "
                "personal_application, prayer_response, questions, notes, created_at, updated_at "
                "FROM sermon_journals WHERE id=%s AND email=%s AND deleted_at IS NULL",
                (journal_id, user["email"]),
            )
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Sermon journal not found")
        return {"ok": True, "journal": _row_to_sermon(row)}
    finally:
        _state["release_db"](conn)


@router.delete("/sermon/journals/{journal_id}")
def delete_sermon_journal(journal_id: int, request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE sermon_journals SET deleted_at=NOW() "
                "WHERE id=%s AND email=%s AND deleted_at IS NULL RETURNING id",
                (journal_id, user["email"]),
            )
            row = cur.fetchone()
            conn.commit()
        if not row:
            raise HTTPException(status_code=404, detail="Sermon journal not found")
        return {"ok": True}
    finally:
        _state["release_db"](conn)
