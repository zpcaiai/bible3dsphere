"""Spiritual Formation persistence API.

Sin Pattern to New Creation Transformation Engine.

Endpoints persist Daily Examen, Thought Captive, Grace Recovery, and
Transformation Plan records, then expose non-shaming aggregate review views.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

try:  # absolute when run from backend/, package-style otherwise
    from spiritual_formation_engine import (
        DURATIONS,
        INTENSITIES,
        generate_transformation_plan,
        recommend_spiritual_response,
        discern_purpose,
        generate_rule_of_life,
        weakest_skill_from_entries,
        compute_streak,
        HORARIUM_HOURS,
        HORARIUM_HOUR_IDS,
    )
except ImportError:  # pragma: no cover
    from backend.spiritual_formation_engine import (
        DURATIONS,
        INTENSITIES,
        generate_transformation_plan,
        recommend_spiritual_response,
        discern_purpose,
        generate_rule_of_life,
        weakest_skill_from_entries,
        compute_streak,
        HORARIUM_HOURS,
        HORARIUM_HOUR_IDS,
    )

router = APIRouter(prefix="/api/spiritual-formation", tags=["spiritual-formation"])
_state: Dict[str, Any] = {}
_SHANGHAI_TZ = timezone(timedelta(hours=8))

HOLY_SPIRIT_FRUITS = [
    "love", "joy", "peace", "patience", "kindness", "goodness",
    "faithfulness", "gentleness", "self_control",
]
NEW_LIFE_VIRTUES = [
    "holiness", "righteousness", "mercy", "compassion", "obedience",
    "humility", "truthfulness", "generosity", "purity", "worship",
    "justice", "faith", "reverence", "contentment", "forgiveness",
]
SIN_PATTERN_IDS = [
    "self_centeredness", "idolatry", "greed_consumerism", "sexual_disorder",
    "pride", "lies_falsehood", "hatred_division", "injustice_oppression",
    "religious_hypocrisy", "coldness_lack_of_love", "entertainment_escapism",
    "babel_pride", "spiritual_numbness",
]

HOLY_LIFE_SKILL_IDS = [
    "morning_consecration",
    "purpose_reset",
    "presence_of_god",
    "thought_examination",
    "intention_inspector",
    "holy_speech",
    "ordinary_life_worship",
    "self_denial_trainer",
    "humility_detector",
    "charity_practice",
    "evening_examen",
    "eternal_perspective",
]

SIN_PATTERN_META = {
    "self_centeredness": {"name": "Self-Centeredness", "fruits": ["faithfulness", "gentleness", "self_control"]},
    "idolatry": {"name": "Idolatry", "fruits": ["love", "joy", "faithfulness"]},
    "greed_consumerism": {"name": "Greed and Consumerism", "fruits": ["self_control", "goodness", "joy"]},
    "sexual_disorder": {"name": "Sexual Disorder", "fruits": ["self_control", "faithfulness", "love"]},
    "pride": {"name": "Pride", "fruits": ["gentleness", "patience", "faithfulness"]},
    "lies_falsehood": {"name": "Lies and Falsehood", "fruits": ["faithfulness", "goodness", "peace"]},
    "hatred_division": {"name": "Violence, Hatred and Division", "fruits": ["peace", "patience", "gentleness", "love"]},
    "injustice_oppression": {"name": "Injustice and Oppression", "fruits": ["goodness", "kindness", "love", "faithfulness"]},
    "religious_hypocrisy": {"name": "Religious Hypocrisy", "fruits": ["faithfulness", "gentleness", "love"]},
    "coldness_lack_of_love": {"name": "Coldness and Lack of Love", "fruits": ["love", "kindness", "goodness", "patience"]},
    "entertainment_escapism": {"name": "Entertainment Escapism", "fruits": ["self_control", "peace", "joy"]},
    "babel_pride": {"name": "Babel-like Technological and Civilizational Pride", "fruits": ["faithfulness", "self_control", "gentleness"]},
    "spiritual_numbness": {"name": "Spiritual Numbness", "fruits": ["faithfulness", "self_control", "love"]},
}

MODULE_DISCLAIMER = (
    "This tool is a spiritual formation aid. It does not replace Scripture, "
    "prayer, the Holy Spirit, the local church, pastoral care, wise "
    "accountability, or professional help when needed."
)


def init_spiritual_formation_router(*, get_db, release_db, get_session_user, to_shanghai_iso, root_dir=None) -> None:
    _state.update(locals())
    if get_db and release_db:
        _init_tables(get_db, release_db, root_dir)


def _init_tables(get_db, release_db, root_dir=None) -> None:
    schema_path = Path(root_dir or Path(__file__).resolve().parents[2]) / "backend" / "spiritual_formation_schema.sql"
    sql = schema_path.read_text(encoding="utf-8")
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


def _db_user_id(user: dict) -> str:
    return str(user.get("email") or user.get("id") or "")


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _today_shanghai() -> date:
    return datetime.now(_SHANGHAI_TZ).date()


def _as_date(value: date | datetime | str | None) -> date:
    if value is None:
        return _today_shanghai()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


def _json(value, fallback):
    if value is None:
        return fallback
    return value


def _Json(obj):
    try:
        from psycopg2.extras import Json
        return Json(obj)
    except Exception:
        return obj


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class DailyExamenIn(CamelModel):
    id: Optional[str] = Field(default=None, max_length=120)
    date: Optional[datetime | date | str] = None
    strongest_emotion: str = Field(alias="strongestEmotion", min_length=1, max_length=64)
    triggers: List[str] = Field(default_factory=list, max_length=20)
    behavior_description: str = Field(default="", alias="behaviorDescription", max_length=5000)
    detected_sin_patterns: List[str] = Field(default_factory=list, alias="detectedSinPatterns", max_length=13)
    selected_primary_sin_pattern: Optional[str] = Field(default=None, alias="selectedPrimarySinPattern", max_length=80)
    core_lie: str = Field(default="", alias="coreLie", max_length=3000)
    gospel_truth: str = Field(default="", alias="gospelTruth", max_length=3000)
    confession: str = Field(default="", max_length=3000)
    repentance_action: str = Field(default="", alias="repentanceAction", max_length=3000)
    obedience_action: str = Field(default="", alias="obedienceAction", max_length=3000)
    fruit_practiced: List[str] = Field(default_factory=list, alias="fruitPracticed", max_length=9)
    virtues_practiced: List[str] = Field(default_factory=list, alias="virtuesPracticed", max_length=15)
    prayer: str = Field(default="", max_length=4000)
    grace_recovery_needed: bool = Field(default=False, alias="graceRecoveryNeeded")

    @field_validator("detected_sin_patterns", "fruit_practiced", "virtues_practiced", "triggers")
    @classmethod
    def clean_list(cls, values):
        return [str(v)[:100] for v in values]


class ThoughtCaptiveIn(CamelModel):
    id: Optional[str] = Field(default=None, max_length=120)
    date: Optional[datetime | date | str] = None
    catch_thought: str = Field(alias="catchThought", min_length=1, max_length=5000)
    named_sin_pattern: str = Field(alias="namedSinPattern", min_length=1, max_length=80)
    exposed_lie: str = Field(alias="exposedLie", min_length=1, max_length=3000)
    replacement_truth: str = Field(alias="replacementTruth", min_length=1, max_length=3000)
    obedience_action: str = Field(alias="obedienceAction", min_length=1, max_length=3000)
    scripture: Optional[dict] = None


class GraceRecoveryIn(CamelModel):
    id: Optional[str] = Field(default=None, max_length=120)
    date: Optional[datetime | date | str] = None
    sin_pattern: Optional[str] = Field(default=None, alias="sinPattern", max_length=80)
    what_happened: str = Field(alias="whatHappened", min_length=1, max_length=5000)
    confession: str = Field(min_length=1, max_length=3000)
    received_grace_statement: str = Field(alias="receivedGraceStatement", min_length=1, max_length=3000)
    repair_action: str = Field(default="", alias="repairAction", max_length=3000)
    boundary_action: str = Field(default="", alias="boundaryAction", max_length=3000)
    accountability_action: str = Field(default="", alias="accountabilityAction", max_length=3000)
    next_obedience_step: str = Field(alias="nextObedienceStep", min_length=1, max_length=3000)


class TransformationPlanIn(CamelModel):
    id: Optional[str] = Field(default=None, max_length=120)
    title: str = Field(min_length=1, max_length=500)
    duration: str = Field(min_length=1, max_length=40)
    intensity: str = Field(min_length=1, max_length=40)
    primary_sin_pattern: str = Field(alias="primarySinPattern", min_length=1, max_length=80)
    secondary_sin_pattern: Optional[str] = Field(default=None, alias="secondarySinPattern", max_length=80)
    target_fruits: List[str] = Field(default_factory=list, alias="targetFruits", max_length=9)
    target_virtues: List[str] = Field(default_factory=list, alias="targetVirtues", max_length=15)
    daily_practices: List[dict] = Field(default_factory=list, alias="dailyPractices", max_length=80)
    weekly_practices: List[dict] = Field(default_factory=list, alias="weeklyPractices", max_length=80)
    review_questions: List[str] = Field(default_factory=list, alias="reviewQuestions", max_length=40)
    progress_summary: str = Field(default="", alias="progressSummary", max_length=5000)
    recommended_next_step: str = Field(default="", alias="recommendedNextStep", max_length=3000)
    start_date: date | str = Field(alias="startDate")
    end_date: date | str = Field(alias="endDate")
    status: str = Field(default="active", max_length=40)
    completed_practice_ids: List[str] = Field(default_factory=list, alias="completedPracticeIds", max_length=200)


class PlanStatusUpdate(CamelModel):
    status: Optional[str] = Field(default=None, max_length=40)
    completed_practice_ids: Optional[List[str]] = Field(default=None, alias="completedPracticeIds", max_length=200)


class HolyLifeSkillEntryIn(CamelModel):
    skill_id: str = Field(alias="skillId", min_length=1, max_length=80)
    score: int = Field(default=50, ge=0, le=100)
    reflection: str = Field(default="", max_length=5000)
    completed: bool = False
    updated_at: Optional[str] = Field(default=None, alias="updatedAt", max_length=80)

    @field_validator("skill_id")
    @classmethod
    def validate_skill_id(cls, value):
        if value not in HOLY_LIFE_SKILL_IDS:
            raise ValueError("Unknown holy life skill")
        return value


class HolyLifePresenceLogIn(CamelModel):
    id: str = Field(min_length=1, max_length=120)
    created_at: str = Field(alias="createdAt", min_length=1, max_length=80)
    reflection: str = Field(default="", max_length=3000)


class HolyLifeDayLogIn(CamelModel):
    id: Optional[str] = Field(default=None, max_length=160)
    date: Optional[str] = Field(default=None, max_length=40)
    intention: str = Field(default="", max_length=5000)
    entries: List[HolyLifeSkillEntryIn] = Field(default_factory=list, max_length=12)
    presence_logs: List[HolyLifePresenceLogIn] = Field(default_factory=list, alias="presenceLogs", max_length=50)
    rule_of_life: Dict[str, Any] = Field(default_factory=dict, alias="ruleOfLife")
    purpose_review: Dict[str, Any] = Field(default_factory=dict, alias="purposeReview")
    decision_sanctification_logs: List[Dict[str, Any]] = Field(default_factory=list, alias="decisionSanctificationLogs", max_length=50)
    daily_report: str = Field(default="", alias="dailyReport", max_length=6000)
    tomorrow_formation: str = Field(default="", alias="tomorrowFormation", max_length=6000)


class RecommendIn(CamelModel):
    emotion: Optional[str] = Field(default=None, max_length=64)
    triggers: List[str] = Field(default_factory=list, max_length=20)
    behavior_text: str = Field(default="", alias="behaviorText", max_length=5000)
    selected_sin_pattern: Optional[str] = Field(default=None, alias="selectedSinPattern", max_length=80)

    @field_validator("triggers")
    @classmethod
    def clean_list(cls, values):
        return [str(v)[:100] for v in values]


class GeneratePlanIn(CamelModel):
    duration: str = Field(min_length=1, max_length=40)
    intensity: str = Field(default="normal", max_length=40)
    primary_sin_pattern: str = Field(alias="primarySinPattern", min_length=1, max_length=80)
    secondary_sin_pattern: Optional[str] = Field(default=None, alias="secondarySinPattern", max_length=80)
    start_date: Optional[str] = Field(default=None, alias="startDate", max_length=20)


def _daily_row(row, to_iso) -> dict:
    return {
        "id": row[0], "userId": row[1], "date": str(row[2]),
        "strongestEmotion": row[3],
        "triggers": _json(row[4], []),
        "behaviorDescription": row[5] or "",
        "detectedSinPatterns": _json(row[6], []),
        "selectedPrimarySinPattern": row[7],
        "coreLie": row[8] or "",
        "gospelTruth": row[9] or "",
        "confession": row[10] or "",
        "repentanceAction": row[11] or "",
        "obedienceAction": row[12] or "",
        "fruitPracticed": _json(row[13], []),
        "virtuesPracticed": _json(row[14], []),
        "prayer": row[15] or "",
        "graceRecoveryNeeded": bool(row[16]),
        "createdAt": to_iso(row[17]),
        "updatedAt": to_iso(row[18]),
    }


def _thought_row(row, to_iso) -> dict:
    return {
        "id": row[0], "userId": row[1], "date": str(row[2]),
        "catchThought": row[3], "namedSinPattern": row[4],
        "exposedLie": row[5], "replacementTruth": row[6],
        "obedienceAction": row[7], "scripture": row[8] or {},
        "createdAt": to_iso(row[9]),
    }


def _recovery_row(row, to_iso) -> dict:
    return {
        "id": row[0], "userId": row[1], "date": str(row[2]),
        "sinPattern": row[3], "whatHappened": row[4],
        "confession": row[5], "receivedGraceStatement": row[6],
        "repairAction": row[7] or "", "boundaryAction": row[8] or "",
        "accountabilityAction": row[9] or "",
        "nextObedienceStep": row[10], "createdAt": to_iso(row[11]),
    }


def _plan_row(row, to_iso) -> dict:
    return {
        "id": row[0], "userId": row[1], "title": row[2],
        "duration": row[3], "intensity": row[4],
        "primarySinPattern": row[5], "secondarySinPattern": row[6],
        "targetFruits": row[7] or [], "targetVirtues": row[8] or [],
        "dailyPractices": row[9] or [], "weeklyPractices": row[10] or [],
        "reviewQuestions": row[11] or [], "progressSummary": row[12] or "",
        "recommendedNextStep": row[13] or "",
        "startDate": str(row[14]), "endDate": str(row[15]), "status": row[16],
        "completedPracticeIds": row[17] or [],
        "createdAt": to_iso(row[18]), "updatedAt": to_iso(row[19]),
    }


def _holy_life_row(row, to_iso) -> dict:
    return {
        "id": row[0],
        "userId": row[1],
        "date": str(row[2]),
        "intention": row[3] or "",
        "entries": row[4] or [],
        "presenceLogs": row[5] or [],
        "ruleOfLife": row[6] or {},
        "purposeReview": row[7] or {},
        "decisionSanctificationLogs": row[8] or [],
        "dailyReport": row[9] or "",
        "tomorrowFormation": row[10] or "",
        "createdAt": to_iso(row[11]),
        "updatedAt": to_iso(row[12]),
    }


def _holy_life_score(entry: dict) -> int:
    try:
        score = int(entry.get("score", 0))
    except Exception:
        score = 0
    return max(0, min(100, score))


DAILY_COLS = (
    "id, user_id, date, strongest_emotion, triggers, behavior_description, "
    "detected_sin_patterns, selected_primary_sin_pattern, core_lie, gospel_truth, "
    "confession, repentance_action, obedience_action, fruit_practiced, virtues_practiced, "
    "prayer, grace_recovery_needed, created_at, updated_at"
)
THOUGHT_COLS = "id, user_id, date, catch_thought, named_sin_pattern, exposed_lie, replacement_truth, obedience_action, scripture, created_at"
RECOVERY_COLS = "id, user_id, date, sin_pattern, what_happened, confession, received_grace_statement, repair_action, boundary_action, accountability_action, next_obedience_step, created_at"
PLAN_COLS = (
    "id, user_id, title, duration, intensity, primary_sin_pattern, secondary_sin_pattern, "
    "target_fruits, target_virtues, daily_practices, weekly_practices, review_questions, "
    "progress_summary, recommended_next_step, start_date, end_date, status, "
    "completed_practice_ids, created_at, updated_at"
)
HOLY_LIFE_COLS = (
    "id, user_id, date, intention, entries, presence_logs, rule_of_life, "
    "purpose_review, decision_sanctification_logs, daily_report, "
    "tomorrow_formation, created_at, updated_at"
)


@router.get("/meta")
def meta() -> dict:
    return {
        "ok": True,
        "disclaimer": MODULE_DISCLAIMER,
        "holySpiritFruits": HOLY_SPIRIT_FRUITS,
        "newLifeVirtues": NEW_LIFE_VIRTUES,
        "sinPatterns": [{"id": k, **v} for k, v in SIN_PATTERN_META.items()],
    }


@router.post("/recommend")
def recommend(body: RecommendIn) -> dict:
    """Stateless: score likely sin patterns and return formation guidance."""
    if body.selected_sin_pattern and body.selected_sin_pattern not in SIN_PATTERN_IDS:
        raise HTTPException(status_code=422, detail="Unknown sin pattern")
    result = recommend_spiritual_response(
        emotion=body.emotion,
        triggers=body.triggers,
        behavior_text=body.behavior_text,
        selected_sin_pattern=body.selected_sin_pattern,
    )
    return {"ok": True, "recommendation": result, "disclaimer": MODULE_DISCLAIMER}


@router.post("/generate-plan")
def generate_plan(body: GeneratePlanIn) -> dict:
    """Stateless: build a transformation plan scaled by duration and intensity."""
    if body.duration not in DURATIONS:
        raise HTTPException(status_code=422, detail="Unknown duration")
    if body.intensity not in INTENSITIES:
        raise HTTPException(status_code=422, detail="Unknown intensity")
    try:
        plan = generate_transformation_plan(
            duration=body.duration,
            intensity=body.intensity,
            primary_sin_pattern=body.primary_sin_pattern,
            secondary_sin_pattern=body.secondary_sin_pattern,
            start_date=body.start_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "plan": plan, "disclaimer": MODULE_DISCLAIMER}


@router.post("/daily-examens")
def save_daily_examen(request: Request, body: DailyExamenIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    entry_id = body.id or _new_id("daily")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO spiritual_daily_examens
                (id, user_id, date, strongest_emotion, triggers, behavior_description,
                 detected_sin_patterns, selected_primary_sin_pattern, core_lie, gospel_truth,
                 confession, repentance_action, obedience_action, fruit_practiced,
                 virtues_practiced, prayer, grace_recovery_needed)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO UPDATE SET
                  date=EXCLUDED.date, strongest_emotion=EXCLUDED.strongest_emotion,
                  triggers=EXCLUDED.triggers, behavior_description=EXCLUDED.behavior_description,
                  detected_sin_patterns=EXCLUDED.detected_sin_patterns,
                  selected_primary_sin_pattern=EXCLUDED.selected_primary_sin_pattern,
                  core_lie=EXCLUDED.core_lie, gospel_truth=EXCLUDED.gospel_truth,
                  confession=EXCLUDED.confession, repentance_action=EXCLUDED.repentance_action,
                  obedience_action=EXCLUDED.obedience_action, fruit_practiced=EXCLUDED.fruit_practiced,
                  virtues_practiced=EXCLUDED.virtues_practiced, prayer=EXCLUDED.prayer,
                  grace_recovery_needed=EXCLUDED.grace_recovery_needed, updated_at=NOW()
                WHERE spiritual_daily_examens.user_id=EXCLUDED.user_id
                RETURNING """ + DAILY_COLS,
                (
                    entry_id, user_id, _as_date(body.date), body.strongest_emotion,
                    _Json(body.triggers), body.behavior_description.strip(),
                    _Json(body.detected_sin_patterns), body.selected_primary_sin_pattern,
                    body.core_lie.strip(), body.gospel_truth.strip(), body.confession.strip(),
                    body.repentance_action.strip(), body.obedience_action.strip(),
                    _Json(body.fruit_practiced), _Json(body.virtues_practiced),
                    body.prayer.strip(), body.grace_recovery_needed,
                ),
            )
            row = cur.fetchone()
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"save failed: {exc}")
    finally:
        _state["release_db"](conn)
    if not row:
        raise HTTPException(status_code=403, detail="Cannot update another user's entry")
    return {"ok": True, "entry": _daily_row(row, _state["to_shanghai_iso"])}


@router.get("/daily-examens")
def list_daily_examens(request: Request, limit: int = Query(default=60, ge=1, le=365)) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {DAILY_COLS} FROM spiritual_daily_examens WHERE user_id=%s ORDER BY date DESC, created_at DESC LIMIT %s", (user_id, limit))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "items": [_daily_row(r, _state["to_shanghai_iso"]) for r in rows]}


@router.get("/daily-examens/{entry_id}")
def get_daily_examen(entry_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {DAILY_COLS} FROM spiritual_daily_examens WHERE id=%s AND user_id=%s", (entry_id, user_id))
            row = cur.fetchone()
    finally:
        _state["release_db"](conn)
    if not row:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"ok": True, "entry": _daily_row(row, _state["to_shanghai_iso"])}


@router.delete("/daily-examens/{entry_id}")
def delete_daily_examen(entry_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM spiritual_daily_examens WHERE id=%s AND user_id=%s", (entry_id, user_id))
            conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True}


@router.post("/thought-captive")
def save_thought_captive(request: Request, body: ThoughtCaptiveIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    entry_id = body.id or _new_id("thought")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO spiritual_thought_captive_entries
                (id, user_id, date, catch_thought, named_sin_pattern, exposed_lie,
                 replacement_truth, obedience_action, scripture)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO UPDATE SET
                  date=EXCLUDED.date, catch_thought=EXCLUDED.catch_thought,
                  named_sin_pattern=EXCLUDED.named_sin_pattern, exposed_lie=EXCLUDED.exposed_lie,
                  replacement_truth=EXCLUDED.replacement_truth,
                  obedience_action=EXCLUDED.obedience_action, scripture=EXCLUDED.scripture
                WHERE spiritual_thought_captive_entries.user_id=EXCLUDED.user_id
                RETURNING """ + THOUGHT_COLS,
                (entry_id, user_id, _as_date(body.date), body.catch_thought.strip(),
                 body.named_sin_pattern, body.exposed_lie.strip(),
                 body.replacement_truth.strip(), body.obedience_action.strip(),
                 _Json(body.scripture or {})),
            )
            row = cur.fetchone()
            conn.commit()
    finally:
        _state["release_db"](conn)
    if not row:
        raise HTTPException(status_code=403, detail="Cannot update another user's entry")
    return {"ok": True, "entry": _thought_row(row, _state["to_shanghai_iso"])}


@router.get("/thought-captive")
def list_thought_captive(request: Request, limit: int = Query(default=60, ge=1, le=365)) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {THOUGHT_COLS} FROM spiritual_thought_captive_entries WHERE user_id=%s ORDER BY date DESC, created_at DESC LIMIT %s", (user_id, limit))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "items": [_thought_row(r, _state["to_shanghai_iso"]) for r in rows]}


@router.post("/grace-recovery")
def save_grace_recovery(request: Request, body: GraceRecoveryIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    entry_id = body.id or _new_id("recovery")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO spiritual_grace_recovery_entries
                (id, user_id, date, sin_pattern, what_happened, confession,
                 received_grace_statement, repair_action, boundary_action,
                 accountability_action, next_obedience_step)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO UPDATE SET
                  date=EXCLUDED.date, sin_pattern=EXCLUDED.sin_pattern,
                  what_happened=EXCLUDED.what_happened, confession=EXCLUDED.confession,
                  received_grace_statement=EXCLUDED.received_grace_statement,
                  repair_action=EXCLUDED.repair_action, boundary_action=EXCLUDED.boundary_action,
                  accountability_action=EXCLUDED.accountability_action,
                  next_obedience_step=EXCLUDED.next_obedience_step
                WHERE spiritual_grace_recovery_entries.user_id=EXCLUDED.user_id
                RETURNING """ + RECOVERY_COLS,
                (entry_id, user_id, _as_date(body.date), body.sin_pattern,
                 body.what_happened.strip(), body.confession.strip(),
                 body.received_grace_statement.strip(), body.repair_action.strip(),
                 body.boundary_action.strip(), body.accountability_action.strip(),
                 body.next_obedience_step.strip()),
            )
            row = cur.fetchone()
            conn.commit()
    finally:
        _state["release_db"](conn)
    if not row:
        raise HTTPException(status_code=403, detail="Cannot update another user's entry")
    return {"ok": True, "entry": _recovery_row(row, _state["to_shanghai_iso"])}


@router.get("/grace-recovery")
def list_grace_recovery(request: Request, limit: int = Query(default=60, ge=1, le=365)) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {RECOVERY_COLS} FROM spiritual_grace_recovery_entries WHERE user_id=%s ORDER BY date DESC, created_at DESC LIMIT %s", (user_id, limit))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "items": [_recovery_row(r, _state["to_shanghai_iso"]) for r in rows]}


@router.post("/plans")
def save_plan(request: Request, body: TransformationPlanIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    plan_id = body.id or _new_id("plan")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            if body.status == "active":
                cur.execute("UPDATE spiritual_transformation_plans SET status='paused', updated_at=NOW() WHERE user_id=%s AND status='active' AND id<>%s", (user_id, plan_id))
            cur.execute(
                """
                INSERT INTO spiritual_transformation_plans
                (id, user_id, title, duration, intensity, primary_sin_pattern,
                 secondary_sin_pattern, target_fruits, target_virtues,
                 daily_practices, weekly_practices, review_questions,
                 progress_summary, recommended_next_step, start_date, end_date,
                 status, completed_practice_ids)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO UPDATE SET
                  title=EXCLUDED.title, duration=EXCLUDED.duration, intensity=EXCLUDED.intensity,
                  primary_sin_pattern=EXCLUDED.primary_sin_pattern,
                  secondary_sin_pattern=EXCLUDED.secondary_sin_pattern,
                  target_fruits=EXCLUDED.target_fruits, target_virtues=EXCLUDED.target_virtues,
                  daily_practices=EXCLUDED.daily_practices, weekly_practices=EXCLUDED.weekly_practices,
                  review_questions=EXCLUDED.review_questions,
                  progress_summary=EXCLUDED.progress_summary,
                  recommended_next_step=EXCLUDED.recommended_next_step,
                  start_date=EXCLUDED.start_date, end_date=EXCLUDED.end_date,
                  status=EXCLUDED.status, completed_practice_ids=EXCLUDED.completed_practice_ids,
                  updated_at=NOW()
                WHERE spiritual_transformation_plans.user_id=EXCLUDED.user_id
                RETURNING """ + PLAN_COLS,
                (
                    plan_id, user_id, body.title.strip(), body.duration, body.intensity,
                    body.primary_sin_pattern, body.secondary_sin_pattern,
                    _Json(body.target_fruits), _Json(body.target_virtues),
                    _Json(body.daily_practices), _Json(body.weekly_practices),
                    _Json(body.review_questions), body.progress_summary.strip(),
                    body.recommended_next_step.strip(), _as_date(body.start_date),
                    _as_date(body.end_date), body.status, _Json(body.completed_practice_ids),
                ),
            )
            row = cur.fetchone()
            conn.commit()
    finally:
        _state["release_db"](conn)
    if not row:
        raise HTTPException(status_code=403, detail="Cannot update another user's plan")
    return {"ok": True, "plan": _plan_row(row, _state["to_shanghai_iso"])}


@router.get("/plans")
def list_plans(request: Request, limit: int = Query(default=50, ge=1, le=200)) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {PLAN_COLS} FROM spiritual_transformation_plans WHERE user_id=%s ORDER BY start_date DESC, created_at DESC LIMIT %s", (user_id, limit))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "items": [_plan_row(r, _state["to_shanghai_iso"]) for r in rows]}


@router.get("/plans/active")
def get_active_plan(request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {PLAN_COLS} FROM spiritual_transformation_plans WHERE user_id=%s AND status='active' ORDER BY start_date DESC LIMIT 1", (user_id,))
            row = cur.fetchone()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "plan": _plan_row(row, _state["to_shanghai_iso"]) if row else None}


@router.put("/plans/{plan_id}")
def update_plan(plan_id: str, request: Request, body: PlanStatusUpdate) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            if body.status == "active":
                cur.execute("UPDATE spiritual_transformation_plans SET status='paused', updated_at=NOW() WHERE user_id=%s AND status='active' AND id<>%s", (user_id, plan_id))
            cur.execute(
                """
                UPDATE spiritual_transformation_plans
                SET status=COALESCE(%s, status),
                    completed_practice_ids=COALESCE(%s, completed_practice_ids),
                    updated_at=NOW()
                WHERE id=%s AND user_id=%s
                RETURNING """ + PLAN_COLS,
                (body.status, _Json(body.completed_practice_ids) if body.completed_practice_ids is not None else None, plan_id, user_id),
            )
            row = cur.fetchone()
            conn.commit()
    finally:
        _state["release_db"](conn)
    if not row:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"ok": True, "plan": _plan_row(row, _state["to_shanghai_iso"])}


@router.post("/holy-life/day-logs")
def save_holy_life_day_log(request: Request, body: HolyLifeDayLogIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    log_date = _as_date(body.date)
    log_id = f"holy_life_{user_id}_{log_date}"
    entries = [entry.model_dump(by_alias=True, mode="json") for entry in body.entries]
    presence_logs = [entry.model_dump(by_alias=True, mode="json") for entry in body.presence_logs]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO spiritual_holy_life_day_logs
                (id, user_id, date, intention, entries, presence_logs,
                 rule_of_life, purpose_review, decision_sanctification_logs,
                 daily_report, tomorrow_formation)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (user_id, date) DO UPDATE SET
                  intention=EXCLUDED.intention,
                  entries=EXCLUDED.entries,
                  presence_logs=EXCLUDED.presence_logs,
                  rule_of_life=EXCLUDED.rule_of_life,
                  purpose_review=EXCLUDED.purpose_review,
                  decision_sanctification_logs=EXCLUDED.decision_sanctification_logs,
                  daily_report=EXCLUDED.daily_report,
                  tomorrow_formation=EXCLUDED.tomorrow_formation,
                  updated_at=NOW()
                RETURNING """ + HOLY_LIFE_COLS,
                (
                    log_id,
                    user_id,
                    log_date,
                    body.intention.strip(),
                    _Json(entries),
                    _Json(presence_logs),
                    _Json(body.rule_of_life),
                    _Json(body.purpose_review),
                    _Json(body.decision_sanctification_logs),
                    body.daily_report.strip(),
                    body.tomorrow_formation.strip(),
                ),
            )
            row = cur.fetchone()
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"save failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "dayLog": _holy_life_row(row, _state["to_shanghai_iso"])}


@router.get("/holy-life/day-logs")
def list_holy_life_day_logs(request: Request, limit: int = Query(default=60, ge=1, le=365)) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {HOLY_LIFE_COLS} FROM spiritual_holy_life_day_logs "
                "WHERE user_id=%s ORDER BY date DESC, created_at DESC LIMIT %s",
                (user_id, limit),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "items": [_holy_life_row(r, _state["to_shanghai_iso"]) for r in rows]}


@router.get("/holy-life/today")
def get_holy_life_today(request: Request, log_date: Optional[str] = Query(default=None, alias="date")) -> dict:
    user_id = _db_user_id(_require_user(request))
    target_date = _as_date(log_date)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {HOLY_LIFE_COLS} FROM spiritual_holy_life_day_logs WHERE user_id=%s AND date=%s",
                (user_id, target_date),
            )
            row = cur.fetchone()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "dayLog": _holy_life_row(row, _state["to_shanghai_iso"]) if row else None}


@router.get("/holy-life/day-logs/{log_id}")
def get_holy_life_day_log(log_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {HOLY_LIFE_COLS} FROM spiritual_holy_life_day_logs WHERE id=%s AND user_id=%s",
                (log_id, user_id),
            )
            row = cur.fetchone()
    finally:
        _state["release_db"](conn)
    if not row:
        raise HTTPException(status_code=404, detail="Holy life day log not found")
    return {"ok": True, "dayLog": _holy_life_row(row, _state["to_shanghai_iso"])}


@router.delete("/holy-life/day-logs/{log_id}")
def delete_holy_life_day_log(log_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM spiritual_holy_life_day_logs WHERE id=%s AND user_id=%s", (log_id, user_id))
            conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True}


@router.get("/holy-life/summary")
def holy_life_summary(request: Request, days: int = Query(default=30, ge=1, le=365)) -> dict:
    user_id = _db_user_id(_require_user(request))
    since = datetime.now(timezone.utc).date() - timedelta(days=days)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {HOLY_LIFE_COLS} FROM spiritual_holy_life_day_logs "
                "WHERE user_id=%s AND date >= %s ORDER BY date DESC",
                (user_id, since),
            )
            logs = [_holy_life_row(r, _state["to_shanghai_iso"]) for r in cur.fetchall()]
    finally:
        _state["release_db"](conn)

    skill_counts: Dict[str, dict] = {skill_id: {"skillId": skill_id, "completed": 0, "scoreTotal": 0, "scoreCount": 0} for skill_id in HOLY_LIFE_SKILL_IDS}
    total_completed = 0
    total_score = 0
    total_score_count = 0
    for log in logs:
        for entry in log.get("entries") or []:
            skill_id = entry.get("skillId")
            if skill_id not in skill_counts:
                continue
            score = _holy_life_score(entry)
            skill_counts[skill_id]["scoreTotal"] += score
            skill_counts[skill_id]["scoreCount"] += 1
            total_score += score
            total_score_count += 1
            if entry.get("completed"):
                skill_counts[skill_id]["completed"] += 1
                total_completed += 1

    skill_summary = []
    for item in skill_counts.values():
        count = item.pop("scoreCount")
        total = item.pop("scoreTotal")
        item["averageScore"] = round(total / count) if count else 0
        skill_summary.append(item)

    return {
        "ok": True,
        "days": days,
        "logCount": len(logs),
        "presencePauseCount": sum(len(log.get("presenceLogs") or []) for log in logs),
        "purposeReviewCount": sum(1 for log in logs if (log.get("purposeReview") or {}).get("callingStatement")),
        "decisionLogCount": sum(len(log.get("decisionSanctificationLogs") or []) for log in logs),
        "completedCount": total_completed,
        "averageScore": round(total_score / total_score_count) if total_score_count else 0,
        "skills": skill_summary,
    }


# ---------------------------------------------------------------------------
# Holy Life — Purpose Engine + dynamic Rule of Life (pure rule-based engines)
# ---------------------------------------------------------------------------


class PurposeDiscernIn(CamelModel):
    task: str = Field(default="", max_length=2000)
    stated_reason: str = Field(default="", alias="statedReason", max_length=3000)
    answers: List[str] = Field(default_factory=list, max_length=10)

    @field_validator("answers")
    @classmethod
    def clean_answers(cls, values):
        return [str(v)[:1000] for v in values][:10]


class RuleOfLifeGenerateIn(CamelModel):
    intention: str = Field(default="", max_length=5000)
    focus_skill_id: Optional[str] = Field(default=None, alias="focusSkillId", max_length=80)
    entries: List[HolyLifeSkillEntryIn] = Field(default_factory=list, max_length=12)


@router.post("/holy-life/purpose-review")
def holy_life_purpose_review(body: PurposeDiscernIn) -> dict:
    """Stateless five-question purpose discernment (why-ladder)."""
    result = discern_purpose(task=body.task, stated_reason=body.stated_reason, answers=body.answers)
    return {"ok": True, "purpose": result, "disclaimer": MODULE_DISCLAIMER}


@router.post("/holy-life/rule-of-life")
def holy_life_rule_of_life(body: RuleOfLifeGenerateIn) -> dict:
    """Stateless dynamic Rule of Life generation from intention + weakest skill."""
    focus = body.focus_skill_id
    if not focus and body.entries:
        focus = weakest_skill_from_entries([e.model_dump(by_alias=True) for e in body.entries])
    rule = generate_rule_of_life(intention=body.intention, focus_skill_id=focus)
    return {"ok": True, "ruleOfLife": rule}


# ---------------------------------------------------------------------------
# Horarium — William Law's fixed hours of prayer (integrated into spiritual-formation)
# ---------------------------------------------------------------------------

HORARIUM_COLS = "id, user_id, date, entries, note, created_at, updated_at"


def _horarium_row(row, to_iso) -> dict:
    return {
        "id": row[0],
        "userId": row[1],
        "date": str(row[2]),
        "entries": row[3] or [],
        "note": row[4] or "",
        "createdAt": to_iso(row[5]),
        "updatedAt": to_iso(row[6]),
    }


class HorariumPrayerEntryIn(CamelModel):
    hour_id: str = Field(alias="hourId", min_length=1, max_length=40)
    completed: bool = False
    reflection: str = Field(default="", max_length=3000)
    completed_at: Optional[str] = Field(default=None, alias="completedAt", max_length=80)

    @field_validator("hour_id")
    @classmethod
    def validate_hour(cls, value):
        if value not in HORARIUM_HOUR_IDS:
            raise ValueError("Unknown horarium hour")
        return value


class HorariumDayLogIn(CamelModel):
    id: Optional[str] = Field(default=None, max_length=160)
    date: Optional[str] = Field(default=None, max_length=40)
    entries: List[HorariumPrayerEntryIn] = Field(default_factory=list, max_length=12)
    note: str = Field(default="", max_length=4000)


@router.get("/holy-life/horarium/hours")
def horarium_hours() -> dict:
    return {"ok": True, "hours": HORARIUM_HOURS}


@router.post("/holy-life/horarium/day-logs")
def save_horarium_day_log(request: Request, body: HorariumDayLogIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    log_date = _as_date(body.date)
    log_id = body.id or f"horarium_{user_id}_{log_date}"
    entries = [entry.model_dump(by_alias=True, mode="json") for entry in body.entries]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO spiritual_horarium_day_logs
                (id, user_id, date, entries, note)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (user_id, date) DO UPDATE SET
                  entries=EXCLUDED.entries,
                  note=EXCLUDED.note,
                  updated_at=NOW()
                RETURNING """ + HORARIUM_COLS,
                (log_id, user_id, log_date, _Json(entries), body.note.strip()),
            )
            row = cur.fetchone()
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"save failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "dayLog": _horarium_row(row, _state["to_shanghai_iso"])}


@router.get("/holy-life/horarium/day-logs")
def list_horarium_day_logs(request: Request, limit: int = Query(default=60, ge=1, le=365)) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {HORARIUM_COLS} FROM spiritual_horarium_day_logs "
                "WHERE user_id=%s ORDER BY date DESC, created_at DESC LIMIT %s",
                (user_id, limit),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "items": [_horarium_row(r, _state["to_shanghai_iso"]) for r in rows]}


@router.get("/holy-life/horarium/today")
def get_horarium_today(request: Request, log_date: Optional[str] = Query(default=None, alias="date")) -> dict:
    user_id = _db_user_id(_require_user(request))
    target_date = _as_date(log_date)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {HORARIUM_COLS} FROM spiritual_horarium_day_logs WHERE user_id=%s AND date=%s",
                (user_id, target_date),
            )
            row = cur.fetchone()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "dayLog": _horarium_row(row, _state["to_shanghai_iso"]) if row else None}


@router.get("/holy-life/horarium/streak")
def horarium_streak(request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT date, entries FROM spiritual_horarium_day_logs WHERE user_id=%s ORDER BY date DESC LIMIT 365",
                (user_id,),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    active_dates = [r[0] for r in rows if any((e or {}).get("completed") for e in (r[1] or []))]
    return {"ok": True, "streak": compute_streak(active_dates), "hours": HORARIUM_HOURS}


def _count(items: list[str]) -> list[dict]:
    counts: Dict[str, int] = {}
    for item in items:
        if item:
            counts[item] = counts.get(item, 0) + 1
    return [{"id": k, "count": v} for k, v in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)]


def _week_bounds(week_start: Optional[str], week_end: Optional[str]) -> tuple[date, date]:
    today = datetime.now(timezone.utc).date()
    start = date.fromisoformat(week_start) if week_start else today - timedelta(days=today.weekday())
    end = date.fromisoformat(week_end) if week_end else start + timedelta(days=6)
    return start, end


@router.get("/weekly-review")
def weekly_review(request: Request, week_start: Optional[str] = None, week_end: Optional[str] = None) -> dict:
    user_id = _db_user_id(_require_user(request))
    start, end = _week_bounds(week_start, week_end)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {DAILY_COLS} FROM spiritual_daily_examens WHERE user_id=%s AND date BETWEEN %s AND %s", (user_id, start, end))
            daily = [_daily_row(r, _state["to_shanghai_iso"]) for r in cur.fetchall()]
            cur.execute(f"SELECT {RECOVERY_COLS} FROM spiritual_grace_recovery_entries WHERE user_id=%s AND date BETWEEN %s AND %s", (user_id, start, end))
            recovery = [_recovery_row(r, _state["to_shanghai_iso"]) for r in cur.fetchall()]
    finally:
        _state["release_db"](conn)

    patterns = _count([p for e in daily for p in (e.get("detectedSinPatterns") or [])])
    triggers = _count([t for e in daily for t in (e.get("triggers") or [])])
    fruits = _count([f for e in daily for f in (e.get("fruitPracticed") or [])])
    return {
        "ok": True,
        "weekStartDate": str(start),
        "weekEndDate": str(end),
        "mostFrequentSinPatterns": patterns,
        "topTriggers": triggers,
        "recurringCoreLies": list(dict.fromkeys([e["coreLie"] for e in daily if e.get("coreLie")]))[:5],
        "fruitsPracticed": fruits,
        "obedienceActionsCompleted": [e["obedienceAction"] for e in daily if e.get("obedienceAction")],
        "graceRecoveryCount": len(recovery) + sum(1 for e in daily if e.get("graceRecoveryNeeded")),
        "pastoralEncouragement": (
            "God is bringing this pattern into the light. Do not despise small beginnings. "
            "Awareness, confession, and one act of obedience are real signs of grace."
            if daily or recovery else
            "No entries yet. Begin with a simple daily scan. The goal is not perfection, but bringing life before God honestly."
        ),
    }


@router.get("/fruit-progress")
def fruit_progress(request: Request, days: int = Query(default=90, ge=1, le=365)) -> dict:
    user_id = _db_user_id(_require_user(request))
    since = datetime.now(timezone.utc).date() - timedelta(days=days)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT fruit_practiced FROM spiritual_daily_examens WHERE user_id=%s AND date >= %s", (user_id, since))
            fruit_lists = [r[0] or [] for r in cur.fetchall()]
            cur.execute("SELECT named_sin_pattern FROM spiritual_thought_captive_entries WHERE user_id=%s AND date >= %s", (user_id, since))
            thought_patterns = [r[0] for r in cur.fetchall()]
            cur.execute("SELECT sin_pattern FROM spiritual_grace_recovery_entries WHERE user_id=%s AND date >= %s AND sin_pattern IS NOT NULL", (user_id, since))
            recovery_patterns = [r[0] for r in cur.fetchall()]
    finally:
        _state["release_db"](conn)

    counts = {fruit: 0 for fruit in HOLY_SPIRIT_FRUITS}
    for fruit in [f for group in fruit_lists for f in group]:
        if fruit in counts:
            counts[fruit] += 1
    for pattern in thought_patterns + recovery_patterns:
        for fruit in SIN_PATTERN_META.get(pattern, {}).get("fruits", []):
            counts[fruit] += 1
    def label(count: int) -> str:
        if count >= 6:
            return "growing"
        if count >= 2:
            return "newly_practiced"
        if count == 1:
            return "ask_for_grace"
        return "needs_attention"
    return {"ok": True, "items": [{"fruit": f, "count": c, "label": label(c)} for f, c in counts.items()]}


@router.get("/new-creation-map")
def new_creation_map(request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    today = datetime.now(timezone.utc).date()
    windows = [("last_7_days", 7), ("last_30_days", 30), ("last_90_days", 90), ("year", 365)]
    conn = _state["get_db"]()
    try:
        results = []
        with conn.cursor() as cur:
            for key, days in windows:
                since = today - timedelta(days=days)
                cur.execute("SELECT detected_sin_patterns, fruit_practiced, obedience_action FROM spiritual_daily_examens WHERE user_id=%s AND date >= %s", (user_id, since))
                rows = cur.fetchall()
                results.append({
                    "window": key,
                    "dailyScanCount": len(rows),
                    "oldPatterns": _count([p for r in rows for p in (r[0] or [])])[:5],
                    "fruitsPracticed": _count([f for r in rows for f in (r[1] or [])])[:5],
                    "obedienceThemes": [r[2] for r in rows if r[2]][:10],
                })
    finally:
        _state["release_db"](conn)
    return {
        "ok": True,
        "worthStatement": "This map is not a record of your worth. Your worth is in Christ.",
        "windows": results,
    }
