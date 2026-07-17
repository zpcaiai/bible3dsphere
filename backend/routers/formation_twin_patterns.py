"""Formation Twin Batch 5 temporal-pattern API.

All reads are owner scoped through PostgreSQL RLS.  Pattern discovery consumes
only eligible, reviewed structure and stores metadata references rather than
sensitive source bodies.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator, model_validator
from psycopg2.extras import Json, RealDictCursor

from formation_twin.temporal_graph import erase_temporal_graph, sync_temporal_pattern
from formation_twin.temporal_patterns import (
    CONFIDENCE_ALGORITHM_VERSION,
    ENGINE_VERSION,
    LIFECYCLE_STATUSES,
    PATTERN_TYPES,
    PUBLISHED_EVENTS,
    RULE_VERSION,
    TimePrecision,
    build_formation_engine_context,
    build_long_term_snapshot,
    calculate_pattern_confidence,
    discover_rule_pattern_candidates,
    generate_pattern_review,
    resolve_temporal_windows,
    temporal_data_quality,
    temporal_weight,
    transition_pattern,
    validate_pattern_text,
)


router = APIRouter(prefix="/api/v1/formation-twin", tags=["formation-twin-patterns"])
_state: dict[str, Any] = {}

SCHEDULED_PATTERN_JOBS = (
    "daily_pattern_incremental_update", "weekly_pattern_candidate_refresh",
    "monthly_pattern_review_generation", "quarterly_trajectory_rebuild",
    "life_season_closure_review", "pattern_expiration_review",
    "evidence_integrity_scan", "graph_consistency_scan",
)


def init_formation_twin_patterns_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _user(request: Request) -> dict[str, Any]:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _identity(email: str) -> tuple[str, str]:
    normalized = email.lower()
    return f"personal:{normalized}", str(uuid.uuid5(uuid.NAMESPACE_URL, f"formation-twin:{normalized}"))


def _owner(cur, email: str) -> None:
    cur.execute("SELECT set_config('app.current_user_email',%s,true)", (email,))


def _invalidate_reflections(cur, email: str, pattern_id: str | None = None) -> None:
    """Fail closed when a Batch 6/7 source pattern is withdrawn or erased."""
    if pattern_id:
        cur.execute(
            "UPDATE formation_twin_reflection_contexts SET invalidated_at=now() WHERE email=%s "
            "AND invalidated_at IS NULL AND confirmed_patterns_json @> %s::jsonb",
            (email, Json([{"pattern_id": pattern_id}])),
        )
    else:
        cur.execute(
            "UPDATE formation_twin_reflection_contexts SET invalidated_at=now() "
            "WHERE email=%s AND invalidated_at IS NULL AND long_term_snapshot_id IS NOT NULL",
            (email,),
        )
    cur.execute(
        "UPDATE formation_twin_reflection_mirrors SET status='INVALIDATED',invalidated_at=now() "
        "WHERE email=%s AND status='ACTIVE' AND context_id IN "
        "(SELECT id FROM formation_twin_reflection_contexts WHERE email=%s AND invalidated_at IS NOT NULL)",
        (email, email),
    )
    cur.execute(
        "UPDATE formation_twin_intervention_proposals SET lifecycle_status='INVALIDATED',invalidated_at=now() "
        "WHERE email=%s AND lifecycle_status='PROPOSED' AND context_id IN "
        "(SELECT id FROM formation_twin_reflection_contexts WHERE email=%s AND invalidated_at IS NOT NULL)",
        (email, email),
    )
    if pattern_id:
        cur.execute(
            "UPDATE formation_twin_risk_conditions SET invalidated_at=now() WHERE email=%s "
            "AND invalidated_at IS NULL AND evidence_references_json @> %s::jsonb",
            (email, Json([{"reference_id": pattern_id}])),
        )
    else:
        cur.execute(
            "UPDATE formation_twin_risk_conditions SET invalidated_at=now() WHERE email=%s "
            "AND invalidated_at IS NULL AND source_kind='CONFIRMED_FORMATION_PATTERN'",
            (email,),
        )
    if cur.rowcount:
        cur.execute(
            "UPDATE formation_twin_risk_snapshots SET invalidated_at=now() "
            "WHERE email=%s AND invalidated_at IS NULL",
            (email,),
        )
        cur.execute(
            "UPDATE formation_twin_early_warnings SET delivery_status='INVALIDATED',deleted_at=now() "
            "WHERE email=%s AND deleted_at IS NULL AND risk_snapshot_id IN "
            "(SELECT id FROM formation_twin_risk_snapshots WHERE email=%s AND invalidated_at IS NOT NULL)",
            (email, email),
        )


def _publish(cur, email: str, event_type: str, payload: dict[str, Any]) -> None:
    if event_type not in PUBLISHED_EVENTS:
        raise ValueError("unregistered Formation Twin pattern event")
    safe = {
        key: value for key, value in payload.items()
        if key.endswith("_id") or key in {"status", "action", "source_kind", "lifecycle_status", "engine_version"}
    }
    cur.execute(
        "INSERT INTO domain_events (aggregate_type,aggregate_id,event_type,payload) VALUES (%s,%s,%s,%s)",
        ("formation_twin", email, event_type, Json(safe)),
    )


def _cursor(conn):
    return conn.cursor(cursor_factory=RealDictCursor)


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _aware(value: datetime | None) -> datetime | None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError("timezone-aware datetime required")
    return value


class TemporalSettingsBody(BaseModel):
    temporal_engine_enabled: bool = True
    pattern_discovery_enabled: bool = True
    model_inference_enabled: bool = False
    semantic_retrieval_enabled: bool = False
    life_season_enabled: bool = True
    trajectory_enabled: bool = True
    graph_evidence_enabled: bool = False
    review_cadence: Literal["WEEKLY", "MONTHLY", "QUARTERLY", "MANUAL"] = "MONTHLY"
    timezone: str = Field(default="Asia/Shanghai", max_length=80)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        resolve_temporal_windows(datetime.now(timezone.utc), value)
        return value

    @model_validator(mode="after")
    def model_requires_feature_flag(self):
        if self.model_inference_enabled and os.getenv("FORMATION_TWIN_PATTERN_MODEL_INFERENCE_ENABLED", "false").lower() != "true":
            raise ValueError("model pattern inference is not enabled by deployment policy")
        return self


class ClusterBody(BaseModel):
    title: str | None = Field(default=None, max_length=160)
    cluster_type: str = Field(default="USER_DEFINED", max_length=40)
    member_event_ids: list[str] = Field(default_factory=list, max_length=100)
    formation_chain_ids: list[str] = Field(default_factory=list, max_length=100)
    grouping_reasons: list[str] = Field(min_length=1, max_length=10)
    started_at: datetime
    ended_at: datetime

    @field_validator("started_at", "ended_at")
    @classmethod
    def aware_times(cls, value: datetime) -> datetime:
        return _aware(value)

    @model_validator(mode="after")
    def valid_cluster(self):
        if not self.member_event_ids and not self.formation_chain_ids:
            raise ValueError("at least one cluster member is required")
        if self.ended_at < self.started_at:
            raise ValueError("invalid cluster time range")
        return self


class ClusterPatch(BaseModel):
    title: str | None = Field(default=None, max_length=160)
    user_review_status: Literal["CONFIRMED", "REJECTED", "MARKED_UNRELATED", "SAME_TIME_ONLY"] | None = None


class ClusterMemberBody(BaseModel):
    member_type: Literal["LIFE_EVENT", "EMOTIONAL_EPISODE", "FORMATION_CHAIN", "FORMATION_NODE"]
    member_id: str
    reason_code: Literal["USER_LINKED", "SHARED_CONTEXT", "SAME_SEASON", "SOURCE_LINKED"]


class PatternPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, min_length=1, max_length=1200)
    scope: dict[str, Any] | None = None
    review_due_at: datetime | None = None

    @field_validator("title", "description")
    @classmethod
    def safe_text(cls, value: str | None) -> str | None:
        return validate_pattern_text(value) if value else value

    @field_validator("review_due_at")
    @classmethod
    def aware_review_time(cls, value: datetime | None) -> datetime | None:
        return _aware(value)


class PatternReviewBody(BaseModel):
    scope: dict[str, Any] | None = None
    title: str | None = Field(default=None, max_length=160)
    reason_code: str = Field(default="USER_REVIEW", max_length=60)
    user_defined_description: str | None = Field(default=None, max_length=500)

    @field_validator("title", "user_defined_description")
    @classmethod
    def safe_text(cls, value: str | None) -> str | None:
        return validate_pattern_text(value) if value else value


class CounterEvidenceBody(BaseModel):
    source_record_type: Literal["LIFE_EVENT", "FORMATION_CHAIN", "FORMATION_NODE", "USER_CORRECTION"]
    source_record_id: str
    occurred_at: datetime
    reason_code: Literal[
        "ALTERNATIVE_RESPONSE", "CONTEXT_DIFFERED", "PATTERN_DID_NOT_OCCUR", "NEW_SUPPORT_FACTOR", "USER_CORRECTION",
    ]
    relevance: float = Field(default=1.0, ge=0, le=1)

    @field_validator("occurred_at")
    @classmethod
    def aware_occurrence(cls, value: datetime) -> datetime:
        return _aware(value)


LIFE_SEASON_TYPES = {
    "WORK_TRANSITION", "PROJECT_DELIVERY", "STUDY_PERIOD", "MARRIAGE_TRANSITION", "PARENTING_TRANSITION",
    "CARE_GIVING", "GRIEF", "HEALTH_CHALLENGE", "CHURCH_TRANSITION", "MINISTRY_TRANSITION",
    "SPIRITUAL_DRYNESS_SELF_REPORTED", "RECOVERY_PERIOD", "RELOCATION", "FINANCIAL_PRESSURE",
    "CALLING_DISCERNMENT", "REST_AND_SABBATICAL", "USER_DEFINED", "OTHER",
}


class LifeSeasonBody(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    season_type: str
    started_at: datetime
    ended_at: datetime | None = None
    time_precision: TimePrecision = TimePrecision.DAY
    life_domains: list[str] = Field(default_factory=list, max_length=12)
    roles: list[str] = Field(default_factory=list, max_length=20)
    user_description: str | None = Field(default=None, max_length=1200)

    @field_validator("started_at", "ended_at")
    @classmethod
    def aware_times(cls, value: datetime | None) -> datetime | None:
        return _aware(value)

    @field_validator("season_type")
    @classmethod
    def known_type(cls, value: str) -> str:
        if value not in LIFE_SEASON_TYPES:
            raise ValueError("unknown life season type")
        return value

    @model_validator(mode="after")
    def valid_range(self):
        if self.ended_at and self.ended_at < self.started_at:
            raise ValueError("invalid life season range")
        return self


class LifeSeasonPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    ended_at: datetime | None = None
    life_domains: list[str] | None = Field(default=None, max_length=12)
    roles: list[str] | None = Field(default=None, max_length=20)
    user_description: str | None = Field(default=None, max_length=1200)

    @field_validator("ended_at")
    @classmethod
    def aware_end(cls, value: datetime | None) -> datetime | None:
        return _aware(value)


class TrajectoryCorrectionBody(BaseModel):
    current_direction: Literal[
        "EMERGING", "STRENGTHENING", "STABLE", "WEAKENING", "BEING_REPLACED", "DORMANT",
        "RESOLVED_BY_USER", "MIXED", "INSUFFICIENT_DATA",
    ]
    limitation: str = Field(min_length=1, max_length=300)


class ReviewCompleteBody(BaseModel):
    retained_pattern_ids: list[str] = Field(default_factory=list, max_length=20)
    note: str | None = Field(default=None, max_length=400)


class RebuildBody(BaseModel):
    reason: Literal["USER_REQUEST", "DATA_DELETION", "ALGORITHM_UPGRADE", "CONSENT_CHANGE", "GRAPH_REPAIR"] = "USER_REQUEST"


class LongTermEraseBody(BaseModel):
    confirmation: Literal["ERASE_LONG_TERM_FORMATION_MODEL"]


def _ensure_settings(cur, email: str) -> dict[str, Any]:
    tenant, profile = _identity(email)
    cur.execute(
        "INSERT INTO formation_twin_temporal_settings (id,tenant_id,profile_id,email) VALUES (%s,%s,%s,%s) "
        "ON CONFLICT (tenant_id,profile_id) DO NOTHING",
        (str(uuid.uuid4()), tenant, profile, email),
    )
    cur.execute(
        "SELECT temporal_engine_enabled,pattern_discovery_enabled,model_inference_enabled,semantic_retrieval_enabled,"
        "life_season_enabled,trajectory_enabled,graph_evidence_enabled,review_cadence,timezone,consent_version,updated_at "
        "FROM formation_twin_temporal_settings WHERE email=%s",
        (email,),
    )
    return dict(cur.fetchone() or {})


def _evidence(cur, email: str, pattern_id: str) -> list[dict[str, Any]]:
    cur.execute(
        "SELECT id,evidence_role,evidence_type,source_record_type,source_record_id,occurred_at,temporal_weight,"
        "decay_strategy,source_quality,independence_group,relevance,user_review_status,explanation,created_at,invalidated_at "
        "FROM formation_twin_pattern_evidence WHERE email=%s AND pattern_id=%s ORDER BY occurred_at,id",
        (email, pattern_id),
    )
    return [dict(item) for item in cur.fetchall()]


def _public_pattern(row: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any]:
    supporting = [item for item in evidence if item["evidence_role"] == "SUPPORTING" and not item.get("invalidated_at")]
    counter = [item for item in evidence if item["evidence_role"] in {"COUNTEREVIDENCE", "CONTEXT_LIMIT"} and not item.get("invalidated_at")]
    unresolved = [item for item in evidence if item["evidence_role"] == "UNRESOLVED" and not item.get("invalidated_at")]
    return {
        "id": str(row["id"]), "title": row["title"], "pattern_type": row["pattern_type"],
        "description": row["description"], "statement_type": row["statement_type"], "source_kind": row["source_kind"],
        "scope": row["scope_json"], "lifecycle_status": row["lifecycle_status"],
        "confidence": row["confidence_json"], "confidence_rationale": (row["confidence_json"] or {}).get("rationale", []),
        "supporting_evidence": supporting, "counterevidence": counter, "unresolved_evidence": unresolved,
        "alternative_explanations": row["alternative_explanations_json"], "limitations": row["limitations_json"],
        "first_observed_at": row["first_observed_at"], "last_observed_at": row["last_observed_at"],
        "last_confirmed_at": row["last_confirmed_at"], "review_due_at": row["review_due_at"],
        "user_review_status": row["user_review_status"], "is_alternative_response": row["is_alternative_response"],
        "version": row["version"], "engine_version": row["engine_version"], "created_at": row["created_at"],
    }


def _pattern(cur, email: str, pattern_id: str) -> dict[str, Any]:
    cur.execute("SELECT * FROM formation_twin_patterns WHERE email=%s AND id=%s AND deleted_at IS NULL", (email, pattern_id))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return dict(row)


def _list_patterns(cur, email: str, *, statuses: list[str] | None = None) -> list[dict[str, Any]]:
    if statuses:
        cur.execute(
            "SELECT * FROM formation_twin_patterns WHERE email=%s AND deleted_at IS NULL AND lifecycle_status IN %s "
            "ORDER BY review_due_at,last_observed_at DESC",
            (email, tuple(statuses)),
        )
    else:
        cur.execute(
            "SELECT * FROM formation_twin_patterns WHERE email=%s AND deleted_at IS NULL ORDER BY review_due_at,last_observed_at DESC",
            (email,),
        )
    rows = [dict(item) for item in cur.fetchall()]
    return [_public_pattern(item, _evidence(cur, email, str(item["id"]))) for item in rows]


def _life_seasons(cur, email: str, *, active_only: bool = False) -> list[dict[str, Any]]:
    suffix = " AND active=TRUE" if active_only else ""
    cur.execute(
        "SELECT id,title,season_type,started_at,ended_at,time_precision,life_domains,roles_json,user_description,"
        "source_kind,user_review_status,active,created_at,updated_at FROM formation_twin_life_seasons "
        f"WHERE email=%s AND deleted_at IS NULL{suffix} ORDER BY started_at DESC",
        (email,),
    )
    return [dict(item) for item in cur.fetchall()]


def _trajectories(cur, email: str) -> list[dict[str, Any]]:
    cur.execute(
        "SELECT id,title,trajectory_type,scope_json,started_at,ended_at,current_direction,evidence_quality,"
        "user_review_status,source_pattern_ids_json,limitations_json,version,created_at,updated_at "
        "FROM formation_twin_trajectories WHERE email=%s AND deleted_at IS NULL ORDER BY started_at DESC",
        (email,),
    )
    return [dict(item) for item in cur.fetchall()]


def _store_snapshot(cur, email: str) -> dict[str, Any]:
    tenant, profile = _identity(email)
    patterns = _list_patterns(cur, email)
    seasons = _life_seasons(cur, email)
    trajectories = _trajectories(cur, email)
    now = datetime.now(timezone.utc)
    window_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    snapshot = build_long_term_snapshot(
        patterns=patterns, life_seasons=seasons, trajectories=trajectories,
        window_start=window_end - timedelta(days=365), window_end=window_end,
    )
    quality = temporal_data_quality(patterns)
    if not quality["snapshot_publish_allowed"]:
        return {"stored": False, "reason": "DATA_QUALITY_BLOCK", "snapshot": snapshot, "quality": quality}
    snapshot = _json_safe(snapshot)
    cur.execute(
        "SELECT id,version FROM formation_twin_long_term_snapshots WHERE email=%s AND superseded_at IS NULL "
        "ORDER BY created_at DESC LIMIT 1",
        (email,),
    )
    previous = cur.fetchone()
    if previous and snapshot["input_hash"]:
        cur.execute(
            "SELECT id,version FROM formation_twin_long_term_snapshots WHERE email=%s AND input_hash=%s",
            (email, snapshot["input_hash"]),
        )
        existing = cur.fetchone()
        if existing:
            return {"stored": False, "reason": "UNCHANGED", "snapshot_id": str(existing["id"]), "snapshot": snapshot}
    snapshot_id = str(uuid.uuid4())
    version = int(previous["version"] if previous else 0) + 1
    if previous:
        cur.execute("UPDATE formation_twin_long_term_snapshots SET superseded_at=now() WHERE id=%s", (str(previous["id"]),))
    cur.execute(
        "INSERT INTO formation_twin_long_term_snapshots "
        "(id,tenant_id,profile_id,email,window_start,window_end,active_life_seasons_json,confirmed_active_patterns_json,"
        "confirmed_contextual_patterns_json,weakening_patterns_json,dormant_patterns_json,pending_candidates_json,"
        "alternative_responses_json,grace_patterns_json,recovery_patterns_json,trajectories_json,counterevidence_json,"
        "unresolved_questions_json,data_coverage_json,uncertainty_json,limitations_json,blocked_items_json,input_hash,"
        "engine_version,version,supersedes_snapshot_id) VALUES "
        "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            snapshot_id, tenant, profile, email, snapshot["window_start"], snapshot["window_end"],
            Json(snapshot["active_life_seasons"]), Json(snapshot["confirmed_active_patterns"]),
            Json(snapshot["confirmed_contextual_patterns"]), Json(snapshot["weakening_patterns"]),
            Json(snapshot["dormant_patterns"]), Json(snapshot["pending_pattern_candidates"]),
            Json(snapshot["emerging_alternative_responses"]), Json(snapshot["grace_and_protection_patterns"]),
            Json(snapshot["recovery_patterns"]), Json(snapshot["trajectories"]),
            Json(snapshot["counterevidence_highlights"]), Json(snapshot["unresolved_questions"]),
            Json(snapshot["data_coverage"]), Json(snapshot["uncertainty_notes"]), Json(snapshot["limitations"]),
            Json(snapshot["blocked_items"]), snapshot["input_hash"], ENGINE_VERSION, version,
            str(previous["id"]) if previous else None,
        ),
    )
    _publish(cur, email, "formation_twin.long_term_snapshot_created", {"snapshot_id": snapshot_id, "engine_version": ENGINE_VERSION})
    return {"stored": True, "snapshot_id": snapshot_id, "snapshot": snapshot, "quality": quality}


def _recalculate_confidence(cur, email: str, pattern: dict[str, Any], user_review_status: str | None = None) -> dict[str, Any]:
    evidence = _evidence(cur, email, str(pattern["id"]))
    confidence = calculate_pattern_confidence(
        evidence, user_review_status=user_review_status or pattern["user_review_status"],
        scope_consistency_factor=1.0,
    ).model_dump(mode="json")
    tenant, profile = _identity(email)
    cur.execute("UPDATE formation_twin_patterns SET confidence_json=%s,updated_at=now() WHERE id=%s", (Json(confidence), str(pattern["id"])))
    cur.execute(
        "INSERT INTO formation_twin_pattern_confidence_history "
        "(id,tenant_id,profile_id,email,pattern_id,confidence_level,numeric_value,support_score,counterevidence_score,"
        "recency_factor,diversity_factor,user_confirmation_factor,scope_consistency_factor,rationale_json,algorithm_version,calculated_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            str(uuid.uuid4()), tenant, profile, email, str(pattern["id"]), confidence["level"], confidence["numeric_value"],
            confidence["support_score"], confidence["counterevidence_score"], confidence["recency_factor"],
            confidence["diversity_factor"], confidence["user_confirmation_factor"],
            confidence["scope_consistency_factor"], Json(confidence["rationale"]),
            CONFIDENCE_ALGORITHM_VERSION, confidence["calculated_at"],
        ),
    )
    _publish(cur, email, "formation_twin.pattern_confidence_updated", {"pattern_id": str(pattern["id"]), "status": confidence["level"]})
    return confidence


def _refresh_trajectory(cur, email: str, pattern_id: str, direction: str) -> str:
    tenant, profile = _identity(email)
    cur.execute(
        "SELECT id FROM formation_twin_trajectories WHERE email=%s AND deleted_at IS NULL "
        "AND source_pattern_ids_json @> %s::jsonb ORDER BY version DESC LIMIT 1",
        (email, Json([pattern_id])),
    )
    existing = cur.fetchone()
    if existing:
        trajectory_id = str(existing["id"])
        cur.execute(
            "UPDATE formation_twin_trajectories SET current_direction=%s,updated_at=now() WHERE id=%s",
            (direction, trajectory_id),
        )
        event = "formation_twin.trajectory_updated"
    else:
        trajectory_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO formation_twin_trajectories "
            "(id,tenant_id,profile_id,email,title,trajectory_type,scope_json,started_at,current_direction,evidence_quality,"
            "user_review_status,source_pattern_ids_json,limitations_json) "
            "SELECT %s,%s,%s,%s,'形成回应路径的时间变化','RESPONSE_PATH_TRAJECTORY',scope_json,first_observed_at,%s,"
            "evidence_quality,'PENDING',%s,%s FROM formation_twin_patterns WHERE email=%s AND id=%s",
            (trajectory_id, tenant, profile, email, direction, Json([pattern_id]),
             Json(["轨迹描述方向而非成长分数。", "记录缺失不代表没有成长。"]), email, pattern_id),
        )
        event = "formation_twin.trajectory_created"
    point_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    cur.execute(
        "INSERT INTO formation_twin_trajectory_points "
        "(id,tenant_id,profile_id,email,trajectory_id,window_start,window_end,direction,supporting_pattern_ids,counterevidence_ids,summary_json) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'[]',%s)",
        (point_id, tenant, profile, email, trajectory_id, now - timedelta(days=30), now, direction,
         Json([pattern_id]), Json({"statement_type": "RULE_DERIVED_RELATION", "score_included": False})),
    )
    _publish(cur, email, event, {"trajectory_id": trajectory_id, "status": direction})
    return trajectory_id


@router.get("/pattern-settings")
def get_pattern_settings(request: Request) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); settings = _ensure_settings(cur, user["email"]); conn.commit()
        return {"ok": True, "settings": settings, "model_default": "DISABLED", "semantic_default": "DISABLED"}
    finally:
        _state["release_db"](conn)


@router.put("/pattern-settings")
def update_pattern_settings(request: Request, body: TemporalSettingsBody) -> dict[str, Any]:
    user = _user(request); tenant, profile = _identity(user["email"]); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); values = body.model_dump()
            cur.execute(
                "INSERT INTO formation_twin_temporal_settings "
                "(id,tenant_id,profile_id,email,temporal_engine_enabled,pattern_discovery_enabled,model_inference_enabled,"
                "semantic_retrieval_enabled,life_season_enabled,trajectory_enabled,graph_evidence_enabled,review_cadence,timezone) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (tenant_id,profile_id) DO UPDATE SET "
                "temporal_engine_enabled=EXCLUDED.temporal_engine_enabled,pattern_discovery_enabled=EXCLUDED.pattern_discovery_enabled,"
                "model_inference_enabled=EXCLUDED.model_inference_enabled,semantic_retrieval_enabled=EXCLUDED.semantic_retrieval_enabled,"
                "life_season_enabled=EXCLUDED.life_season_enabled,trajectory_enabled=EXCLUDED.trajectory_enabled,"
                "graph_evidence_enabled=EXCLUDED.graph_evidence_enabled,review_cadence=EXCLUDED.review_cadence,"
                "timezone=EXCLUDED.timezone,consent_version=formation_twin_temporal_settings.consent_version+1,updated_at=now()",
                (str(uuid.uuid4()), tenant, profile, user["email"], *values.values()),
            )
            settings = _ensure_settings(cur, user["email"]); conn.commit()
        return {"ok": True, "settings": settings}
    except Exception:
        conn.rollback(); raise
    finally:
        _state["release_db"](conn)


@router.get("/temporal-windows")
def get_temporal_windows(request: Request, occurred_at: datetime, timezone_name: str = Query(default="Asia/Shanghai", alias="timezone")) -> dict[str, Any]:
    _user(request)
    return {"ok": True, "windows": resolve_temporal_windows(occurred_at, timezone_name)}


@router.get("/event-clusters")
def list_event_clusters(request: Request) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute("SELECT * FROM formation_twin_event_clusters WHERE email=%s AND deleted_at IS NULL ORDER BY started_at DESC", (user["email"],))
            clusters = [dict(item) for item in cur.fetchall()]
        return {"ok": True, "clusters": clusters}
    finally:
        _state["release_db"](conn)


@router.post("/event-clusters")
def create_event_cluster(request: Request, body: ClusterBody) -> dict[str, Any]:
    user = _user(request); tenant, profile = _identity(user["email"]); cluster_id = str(uuid.uuid4()); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "INSERT INTO formation_twin_event_clusters "
                "(id,tenant_id,profile_id,email,title,cluster_type,creation_method,shared_context_json,grouping_reasons_json,"
                "user_review_status,started_at,ended_at,rule_version) VALUES (%s,%s,%s,%s,%s,%s,'USER_GROUPED','{}',%s,'CONFIRMED',%s,%s,%s)",
                (cluster_id, tenant, profile, user["email"], body.title, body.cluster_type, Json(body.grouping_reasons), body.started_at, body.ended_at, RULE_VERSION),
            )
            for member_type, ids in (("LIFE_EVENT", body.member_event_ids), ("FORMATION_CHAIN", body.formation_chain_ids)):
                for member_id in ids:
                    cur.execute(
                        "INSERT INTO formation_twin_event_cluster_members "
                        "(id,tenant_id,profile_id,email,cluster_id,member_type,member_id,membership_status,added_reason) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s,'ACTIVE','USER_GROUPED')",
                        (str(uuid.uuid4()), tenant, profile, user["email"], cluster_id, member_type, member_id),
                    )
            _publish(cur, user["email"], "formation_twin.event_cluster_created", {"cluster_id": cluster_id, "source_kind": "USER"})
            conn.commit()
        return {"ok": True, "cluster_id": cluster_id, "original_records_modified": False}
    except Exception:
        conn.rollback(); raise
    finally:
        _state["release_db"](conn)


@router.patch("/event-clusters/{cluster_id}")
def update_event_cluster(request: Request, cluster_id: str, body: ClusterPatch) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "UPDATE formation_twin_event_clusters SET title=COALESCE(%s,title),user_review_status=COALESCE(%s,user_review_status),"
                "rejection_cooldown_until=CASE WHEN %s IN ('REJECTED','MARKED_UNRELATED') THEN now()+interval '90 days' ELSE rejection_cooldown_until END,updated_at=now() "
                "WHERE email=%s AND id=%s AND deleted_at IS NULL RETURNING id",
                (body.title, body.user_review_status, body.user_review_status, user["email"], cluster_id),
            )
            if not cur.fetchone(): raise HTTPException(status_code=404, detail="Cluster not found")
            _publish(cur, user["email"], "formation_twin.event_cluster_updated", {"cluster_id": cluster_id, "status": body.user_review_status or "UPDATED"})
            conn.commit()
        return {"ok": True}
    except Exception:
        conn.rollback(); raise
    finally: _state["release_db"](conn)


@router.delete("/event-clusters/{cluster_id}")
def delete_event_cluster(request: Request, cluster_id: str) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute("UPDATE formation_twin_event_clusters SET deleted_at=now(),user_review_status='REJECTED',rejection_cooldown_until=now()+interval '90 days' WHERE email=%s AND id=%s AND deleted_at IS NULL RETURNING id", (user["email"], cluster_id))
            if not cur.fetchone(): raise HTTPException(status_code=404, detail="Cluster not found")
            _publish(cur, user["email"], "formation_twin.event_cluster_rejected", {"cluster_id": cluster_id, "status": "REJECTED"}); conn.commit()
        return {"ok": True, "original_records_modified": False}
    except Exception:
        conn.rollback(); raise
    finally: _state["release_db"](conn)


@router.post("/event-clusters/{cluster_id}/members")
def add_cluster_member(request: Request, cluster_id: str, body: ClusterMemberBody) -> dict[str, Any]:
    user = _user(request); tenant, profile = _identity(user["email"]); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); cur.execute("SELECT id FROM formation_twin_event_clusters WHERE email=%s AND id=%s AND deleted_at IS NULL", (user["email"], cluster_id))
            if not cur.fetchone(): raise HTTPException(status_code=404, detail="Cluster not found")
            cur.execute(
                "INSERT INTO formation_twin_event_cluster_members (id,tenant_id,profile_id,email,cluster_id,member_type,member_id,membership_status,added_reason) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,'ACTIVE',%s) ON CONFLICT (cluster_id,member_type,member_id) DO UPDATE SET membership_status='ACTIVE',removed_at=NULL,added_reason=EXCLUDED.added_reason",
                (str(uuid.uuid4()), tenant, profile, user["email"], cluster_id, body.member_type, body.member_id, body.reason_code),
            ); conn.commit()
        return {"ok": True}
    except Exception:
        conn.rollback(); raise
    finally: _state["release_db"](conn)


@router.delete("/event-clusters/{cluster_id}/members/{member_id}")
def remove_cluster_member(request: Request, cluster_id: str, member_id: str) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); cur.execute("UPDATE formation_twin_event_cluster_members SET membership_status='REMOVED_BY_USER',removed_at=now() WHERE email=%s AND cluster_id=%s AND member_id=%s AND membership_status='ACTIVE' RETURNING id", (user["email"], cluster_id, member_id))
            if not cur.fetchone(): raise HTTPException(status_code=404, detail="Cluster member not found")
            cur.execute("UPDATE formation_twin_event_clusters SET rejection_cooldown_until=now()+interval '90 days',updated_at=now() WHERE id=%s", (cluster_id,)); conn.commit()
        return {"ok": True, "regrouping_cooldown_days": 90}
    except Exception:
        conn.rollback(); raise
    finally: _state["release_db"](conn)


@router.get("/patterns")
def list_patterns(request: Request, lifecycle_status: str | None = None) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); statuses = [lifecycle_status] if lifecycle_status else None
            if lifecycle_status and lifecycle_status not in LIFECYCLE_STATUSES: raise HTTPException(status_code=422, detail="Unknown lifecycle status")
            patterns = _list_patterns(cur, user["email"], statuses=statuses)
        return {"ok": True, "patterns": patterns, "disclaimer": "长期模式是可修正假设，不定义你的本质。"}
    finally: _state["release_db"](conn)


@router.get("/patterns/current")
def current_patterns(request: Request) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); patterns = _list_patterns(cur, user["email"], statuses=["CONFIRMED_ACTIVE", "CONFIRMED_CONTEXTUAL", "WEAKENING", "DORMANT"])
        return {"ok": True, "patterns": patterns, "recording_bias_notice": "记录偏差可能存在：你可能更常在困难时期记录。"}
    finally: _state["release_db"](conn)


@router.get("/patterns/candidates")
def pattern_candidates(request: Request) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); patterns = _list_patterns(cur, user["email"], statuses=["CANDIDATE", "PENDING_USER_REVIEW"])
        return {"ok": True, "patterns": patterns}
    finally: _state["release_db"](conn)


@router.get("/patterns/data-quality")
def pattern_data_quality_static(request: Request) -> dict[str, Any]:
    """Registered before the dynamic pattern detail route."""
    return pattern_data_quality(request)


@router.get("/patterns/{pattern_id}")
def get_pattern(request: Request, pattern_id: str) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); row = _pattern(cur, user["email"], pattern_id); item = _public_pattern(row, _evidence(cur, user["email"], pattern_id))
        return {"ok": True, "pattern": item}
    finally: _state["release_db"](conn)


@router.patch("/patterns/{pattern_id}")
def update_pattern(request: Request, pattern_id: str, body: PatternPatch) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); row = _pattern(cur, user["email"], pattern_id); values = body.model_dump(exclude_none=True)
            cur.execute(
                "UPDATE formation_twin_patterns SET title=%s,description=%s,scope_json=%s,review_due_at=%s,updated_at=now() WHERE id=%s",
                (values.get("title", row["title"]), values.get("description", row["description"]), Json(values.get("scope", row["scope_json"])), values.get("review_due_at", row["review_due_at"]), pattern_id),
            ); _store_snapshot(cur, user["email"]); conn.commit()
        return {"ok": True}
    except Exception:
        conn.rollback(); raise
    finally: _state["release_db"](conn)


@router.delete("/patterns/{pattern_id}")
def delete_pattern(request: Request, pattern_id: str) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); _pattern(cur, user["email"], pattern_id)
            cur.execute("UPDATE formation_twin_pattern_evidence SET invalidated_at=now(),evidence_role='INVALIDATED' WHERE email=%s AND pattern_id=%s AND invalidated_at IS NULL", (user["email"], pattern_id))
            cur.execute("UPDATE formation_twin_patterns SET lifecycle_status='INVALIDATED',user_review_status='REJECTED',deleted_at=now(),updated_at=now() WHERE email=%s AND id=%s", (user["email"], pattern_id))
            _invalidate_reflections(cur, user["email"], pattern_id)
            _publish(cur, user["email"], "formation_twin.pattern_invalidated", {"pattern_id": pattern_id, "status": "INVALIDATED"}); _store_snapshot(cur, user["email"]); conn.commit()
        return {"ok": True, "history_retained_in_audit": True, "current_context_removed": True}
    except Exception:
        conn.rollback(); raise
    finally: _state["release_db"](conn)


ACTION_TRANSITIONS = {
    "confirm": ("CONFIRMED_CONTEXTUAL", "CONFIRMED", "formation_twin.pattern_confirmed"),
    "partially-confirm": ("CONFIRMED_CONTEXTUAL", "PARTIALLY_CONFIRMED", "formation_twin.pattern_partially_confirmed"),
    "reject": ("REJECTED", "REJECTED", "formation_twin.pattern_rejected"),
    "narrow-scope": ("CONFIRMED_CONTEXTUAL", "SCOPE_NARROWED", "formation_twin.pattern_scope_changed"),
    "expand-scope": ("CONFIRMED_ACTIVE", "SCOPE_EXPANDED", "formation_twin.pattern_scope_changed"),
    "mark-weakening": ("WEAKENING", "CONFIRMED", "formation_twin.pattern_weakened"),
    "mark-dormant": ("DORMANT", "CONFIRMED", "formation_twin.pattern_dormant"),
    "mark-resolved": ("RESOLVED", "MARKED_RESOLVED", "formation_twin.pattern_resolved"),
    "mark-outdated": ("OUTDATED", "MARKED_OUTDATED", "formation_twin.pattern_outdated"),
    "reopen": ("PENDING_USER_REVIEW", "PENDING", "formation_twin.pattern_reopened"),
}


def _pattern_action(request: Request, pattern_id: str, action: str, body: PatternReviewBody) -> dict[str, Any]:
    user = _user(request); tenant, profile = _identity(user["email"]); conn = _state["get_db"]()
    try:
        target, review_status, event_type = ACTION_TRANSITIONS[action]
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); pattern = _pattern(cur, user["email"], pattern_id)
            transition_pattern(pattern["lifecycle_status"], target, initiated_by="USER")
            scope = body.scope or pattern["scope_json"]
            if action == "confirm" and scope.get("scope_kind") == "GLOBAL_UNKNOWN":
                scope = {**scope, "scope_kind": "CURRENT_CONTEXT_ONLY"}
            cur.execute(
                "UPDATE formation_twin_patterns SET lifecycle_status=%s,user_review_status=%s,scope_json=%s,"
                "title=COALESCE(%s,title),last_confirmed_at=CASE WHEN %s LIKE 'CONFIRMED%%' THEN now() ELSE last_confirmed_at END,"
                "review_due_at=CASE WHEN %s IN ('RESOLVED','OUTDATED','REJECTED') THEN review_due_at ELSE now()+interval '90 days' END,updated_at=now() WHERE id=%s",
                (target, review_status, Json(scope), body.title, target, target, pattern_id),
            )
            cur.execute(
                "INSERT INTO formation_twin_pattern_lifecycle_events "
                "(id,tenant_id,profile_id,email,pattern_id,previous_status,new_status,reason_code,reason_description,initiated_by) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'USER')",
                (str(uuid.uuid4()), tenant, profile, user["email"], pattern_id, pattern["lifecycle_status"], target, body.reason_code, "USER_INITIATED_REVIEW"),
            )
            if action in {"reject", "narrow-scope", "expand-scope"}:
                preference_type = "DO_NOT_SUGGEST_PATTERN" if action == "reject" else "PATTERN_SCOPE_PREFERENCE"
                cur.execute(
                    "INSERT INTO formation_twin_interpretation_preferences "
                    "(id,tenant_id,profile_id,email,preference_type,preference_payload_json,scope,active) VALUES (%s,%s,%s,%s,%s,%s,'CURRENT_USER',TRUE)",
                    (str(uuid.uuid4()), tenant, profile, user["email"], preference_type, Json({"pattern_key": pattern["pattern_key"], "action": action, "scope": scope})),
                )
            pattern["user_review_status"] = review_status
            confidence = _recalculate_confidence(cur, user["email"], pattern, review_status)
            direction = {
                "WEAKENING": "WEAKENING", "DORMANT": "DORMANT", "RESOLVED": "RESOLVED_BY_USER",
                "CONFIRMED_ACTIVE": "STABLE", "CONFIRMED_CONTEXTUAL": "MIXED",
            }.get(target)
            if direction:
                _refresh_trajectory(cur, user["email"], pattern_id, direction)
            if target in {"REJECTED", "RESOLVED", "OUTDATED"}:
                _invalidate_reflections(cur, user["email"], pattern_id)
            _publish(cur, user["email"], event_type, {"pattern_id": pattern_id, "action": action, "lifecycle_status": target})
            snapshot = _store_snapshot(cur, user["email"]); conn.commit()
        return {"ok": True, "pattern_id": pattern_id, "lifecycle_status": target, "confidence": confidence, "snapshot": {"stored": snapshot["stored"], "reason": snapshot.get("reason")}}
    except Exception:
        conn.rollback(); raise
    finally: _state["release_db"](conn)


for _action in ACTION_TRANSITIONS:
    def _make_endpoint(action_name: str):
        def endpoint(request: Request, pattern_id: str, body: PatternReviewBody) -> dict[str, Any]:
            return _pattern_action(request, pattern_id, action_name, body)
        endpoint.__name__ = f"pattern_{action_name.replace('-', '_')}"
        return endpoint
    router.add_api_route(f"/patterns/{{pattern_id}}/{_action}", _make_endpoint(_action), methods=["POST"])


@router.get("/patterns/{pattern_id}/evidence")
def get_pattern_evidence(request: Request, pattern_id: str) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); _pattern(cur, user["email"], pattern_id); items = _evidence(cur, user["email"], pattern_id)
        return {"ok": True, "supporting": [i for i in items if i["evidence_role"] == "SUPPORTING"], "counterevidence": [i for i in items if i["evidence_role"] in {"COUNTEREVIDENCE", "CONTEXT_LIMIT"}], "unresolved": [i for i in items if i["evidence_role"] == "UNRESOLVED"]}
    finally: _state["release_db"](conn)


def _review_evidence(request: Request, pattern_id: str, evidence_id: str, action: str) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); pattern = _pattern(cur, user["email"], pattern_id)
            if action == "confirm":
                cur.execute("UPDATE formation_twin_pattern_evidence SET user_review_status='CONFIRMED' WHERE email=%s AND pattern_id=%s AND id=%s RETURNING id", (user["email"], pattern_id, evidence_id))
            else:
                cur.execute("UPDATE formation_twin_pattern_evidence SET user_review_status='REJECTED',evidence_role='INVALIDATED',invalidated_at=now() WHERE email=%s AND pattern_id=%s AND id=%s RETURNING id", (user["email"], pattern_id, evidence_id))
            if not cur.fetchone(): raise HTTPException(status_code=404, detail="Evidence not found")
            confidence = _recalculate_confidence(cur, user["email"], pattern); _store_snapshot(cur, user["email"]); conn.commit()
        return {"ok": True, "confidence": confidence}
    except Exception:
        conn.rollback(); raise
    finally: _state["release_db"](conn)


@router.post("/patterns/{pattern_id}/evidence/{evidence_id}/confirm")
def confirm_pattern_evidence(request: Request, pattern_id: str, evidence_id: str) -> dict[str, Any]:
    return _review_evidence(request, pattern_id, evidence_id, "confirm")


@router.post("/patterns/{pattern_id}/evidence/{evidence_id}/reject")
def reject_pattern_evidence(request: Request, pattern_id: str, evidence_id: str) -> dict[str, Any]:
    return _review_evidence(request, pattern_id, evidence_id, "reject")


@router.post("/patterns/{pattern_id}/counterevidence")
def add_counterevidence(request: Request, pattern_id: str, body: CounterEvidenceBody) -> dict[str, Any]:
    user = _user(request); tenant, profile = _identity(user["email"]); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); pattern = _pattern(cur, user["email"], pattern_id)
            weight, strategy = temporal_weight(body.occurred_at, "FORMATION_CHAIN")
            evidence_id = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO formation_twin_pattern_evidence "
                "(id,tenant_id,profile_id,email,pattern_id,evidence_role,evidence_type,source_record_type,source_record_id,"
                "occurred_at,temporal_weight,decay_strategy,source_quality,independence_group,relevance,user_review_status,explanation) "
                "VALUES (%s,%s,%s,%s,%s,'COUNTEREVIDENCE','USER_REPORTED_COUNTEREXAMPLE',%s,%s,%s,%s,%s,'USER_DIRECT_STATEMENT',%s,%s,'CONFIRMED',%s)",
                (evidence_id, tenant, profile, user["email"], pattern_id, body.source_record_type, body.source_record_id, body.occurred_at, weight, strategy, f"{body.source_record_type}:{body.source_record_id}", body.relevance, f"用户确认的反例：{body.reason_code}"),
            )
            confidence = _recalculate_confidence(cur, user["email"], pattern)
            _refresh_trajectory(cur, user["email"], pattern_id, "BEING_REPLACED" if body.reason_code == "ALTERNATIVE_RESPONSE" else "MIXED")
            _store_snapshot(cur, user["email"]); conn.commit()
        return {"ok": True, "evidence_id": evidence_id, "confidence": confidence}
    except Exception:
        conn.rollback(); raise
    finally: _state["release_db"](conn)


@router.get("/life-seasons")
def list_life_seasons(request: Request) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur: _owner(cur, user["email"]); items = _life_seasons(cur, user["email"])
        return {"ok": True, "life_seasons": items}
    finally: _state["release_db"](conn)


@router.post("/life-seasons")
def create_life_season(request: Request, body: LifeSeasonBody) -> dict[str, Any]:
    user = _user(request); tenant, profile = _identity(user["email"]); season_id = str(uuid.uuid4()); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "INSERT INTO formation_twin_life_seasons "
                "(id,tenant_id,profile_id,email,title,season_type,started_at,ended_at,time_precision,life_domains,roles_json,"
                "user_description,source_kind,user_review_status,active) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'USER_CREATED','CONFIRMED',%s)",
                (season_id, tenant, profile, user["email"], body.title, body.season_type, body.started_at, body.ended_at, body.time_precision.value, Json(body.life_domains), Json(body.roles), body.user_description, body.ended_at is None),
            )
            _publish(cur, user["email"], "formation_twin.life_season_created", {"life_season_id": season_id, "source_kind": "USER"}); _store_snapshot(cur, user["email"]); conn.commit()
        return {"ok": True, "life_season_id": season_id}
    except Exception:
        conn.rollback(); raise
    finally: _state["release_db"](conn)


@router.get("/life-seasons/{season_id}")
def get_life_season(request: Request, season_id: str) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); cur.execute("SELECT * FROM formation_twin_life_seasons WHERE email=%s AND id=%s AND deleted_at IS NULL", (user["email"], season_id)); item = cur.fetchone()
            if not item: raise HTTPException(status_code=404, detail="Life season not found")
        return {"ok": True, "life_season": dict(item)}
    finally: _state["release_db"](conn)


@router.patch("/life-seasons/{season_id}")
def update_life_season(request: Request, season_id: str, body: LifeSeasonPatch) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); values = body.model_dump(exclude_none=True)
            cur.execute("SELECT * FROM formation_twin_life_seasons WHERE email=%s AND id=%s AND deleted_at IS NULL", (user["email"], season_id)); row = cur.fetchone()
            if not row: raise HTTPException(status_code=404, detail="Life season not found")
            cur.execute(
                "UPDATE formation_twin_life_seasons SET title=%s,ended_at=%s,life_domains=%s,roles_json=%s,user_description=%s,active=%s,updated_at=now() WHERE id=%s",
                (values.get("title", row["title"]), values.get("ended_at", row["ended_at"]), Json(values.get("life_domains", row["life_domains"])), Json(values.get("roles", row["roles_json"])), values.get("user_description", row["user_description"]), values.get("ended_at", row["ended_at"]) is None, season_id),
            ); _publish(cur, user["email"], "formation_twin.life_season_updated", {"life_season_id": season_id}); _store_snapshot(cur, user["email"]); conn.commit()
        return {"ok": True}
    except Exception:
        conn.rollback(); raise
    finally: _state["release_db"](conn)


@router.delete("/life-seasons/{season_id}")
def delete_life_season(request: Request, season_id: str) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); cur.execute("UPDATE formation_twin_life_seasons SET deleted_at=now(),active=FALSE WHERE email=%s AND id=%s AND deleted_at IS NULL RETURNING id", (user["email"], season_id))
            if not cur.fetchone(): raise HTTPException(status_code=404, detail="Life season not found")
            cur.execute("UPDATE formation_twin_patterns SET lifecycle_status='OUTDATED',review_due_at=now(),updated_at=now() WHERE id IN (SELECT pattern_id FROM formation_twin_pattern_life_seasons WHERE email=%s AND life_season_id=%s) AND lifecycle_status IN ('CANDIDATE','PENDING_USER_REVIEW')", (user["email"], season_id)); _store_snapshot(cur, user["email"]); conn.commit()
        return {"ok": True}
    except Exception:
        conn.rollback(); raise
    finally: _state["release_db"](conn)


def _set_season_active(request: Request, season_id: str, active: bool) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute("UPDATE formation_twin_life_seasons SET active=%s,ended_at=CASE WHEN %s THEN NULL ELSE COALESCE(ended_at,now()) END,updated_at=now() WHERE email=%s AND id=%s AND deleted_at IS NULL RETURNING id", (active, active, user["email"], season_id))
            if not cur.fetchone(): raise HTTPException(status_code=404, detail="Life season not found")
            event = "formation_twin.life_season_reopened" if active else "formation_twin.life_season_closed"
            if not active:
                cur.execute("UPDATE formation_twin_patterns SET lifecycle_status='CONFIRMED_CONTEXTUAL',review_due_at=now(),updated_at=now() WHERE id IN (SELECT pattern_id FROM formation_twin_pattern_life_seasons WHERE email=%s AND life_season_id=%s) AND lifecycle_status='CONFIRMED_ACTIVE'", (user["email"], season_id))
            _publish(cur, user["email"], event, {"life_season_id": season_id, "status": "ACTIVE" if active else "CLOSED"}); _store_snapshot(cur, user["email"]); conn.commit()
        return {"ok": True, "active": active, "patterns_recheck_required": not active}
    except Exception:
        conn.rollback(); raise
    finally: _state["release_db"](conn)


@router.post("/life-seasons/{season_id}/close")
def close_life_season(request: Request, season_id: str) -> dict[str, Any]: return _set_season_active(request, season_id, False)


@router.post("/life-seasons/{season_id}/reopen")
def reopen_life_season(request: Request, season_id: str) -> dict[str, Any]: return _set_season_active(request, season_id, True)


@router.post("/life-seasons/{season_id}/review")
def review_life_season(request: Request, season_id: str) -> dict[str, Any]:
    user = _user(request); tenant, profile = _identity(user["email"]); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); cur.execute("SELECT started_at,COALESCE(ended_at,now()) AS ended_at FROM formation_twin_life_seasons WHERE email=%s AND id=%s AND deleted_at IS NULL", (user["email"], season_id)); season = cur.fetchone()
            if not season: raise HTTPException(status_code=404, detail="Life season not found")
            patterns = _list_patterns(cur, user["email"]); payload = generate_pattern_review("LIFE_SEASON_CLOSURE_REVIEW", patterns=patterns, window_start=season["started_at"], window_end=season["ended_at"]); review_id = str(uuid.uuid4())
            cur.execute("INSERT INTO formation_twin_pattern_reviews (id,tenant_id,profile_id,email,review_type,window_start,window_end,review_payload_json,status) VALUES (%s,%s,%s,%s,'LIFE_SEASON_CLOSURE_REVIEW',%s,%s,%s,'PENDING')", (review_id, tenant, profile, user["email"], season["started_at"], season["ended_at"], Json(payload))); _publish(cur, user["email"], "formation_twin.pattern_review_created", {"review_id": review_id, "life_season_id": season_id}); conn.commit()
        return {"ok": True, "review_id": review_id, "review": payload}
    except Exception:
        conn.rollback(); raise
    finally: _state["release_db"](conn)


@router.get("/trajectories")
def list_trajectories(request: Request) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur: _owner(cur, user["email"]); items = _trajectories(cur, user["email"])
        return {"ok": True, "trajectories": items, "scoring": False}
    finally: _state["release_db"](conn)


@router.get("/trajectories/{trajectory_id}")
def get_trajectory(request: Request, trajectory_id: str) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); cur.execute("SELECT * FROM formation_twin_trajectories WHERE email=%s AND id=%s AND deleted_at IS NULL", (user["email"], trajectory_id)); item = cur.fetchone()
            if not item: raise HTTPException(status_code=404, detail="Trajectory not found")
            cur.execute("SELECT * FROM formation_twin_trajectory_points WHERE email=%s AND trajectory_id=%s ORDER BY window_start", (user["email"], trajectory_id)); points = [dict(row) for row in cur.fetchall()]
        return {"ok": True, "trajectory": dict(item), "points": points}
    finally: _state["release_db"](conn)


@router.post("/trajectories/{trajectory_id}/confirm")
def confirm_trajectory(request: Request, trajectory_id: str) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); cur.execute("UPDATE formation_twin_trajectories SET user_review_status='CONFIRMED',updated_at=now() WHERE email=%s AND id=%s AND deleted_at IS NULL RETURNING id", (user["email"], trajectory_id))
            if not cur.fetchone(): raise HTTPException(status_code=404, detail="Trajectory not found")
            _publish(cur, user["email"], "formation_twin.trajectory_updated", {"trajectory_id": trajectory_id, "status": "CONFIRMED"}); _store_snapshot(cur, user["email"]); conn.commit()
        return {"ok": True}
    except Exception:
        conn.rollback(); raise
    finally: _state["release_db"](conn)


@router.post("/trajectories/{trajectory_id}/correct")
def correct_trajectory(request: Request, trajectory_id: str, body: TrajectoryCorrectionBody) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); cur.execute("UPDATE formation_twin_trajectories SET current_direction=%s,user_review_status='CORRECTED',limitations_json=limitations_json||%s::jsonb,updated_at=now() WHERE email=%s AND id=%s AND deleted_at IS NULL RETURNING id", (body.current_direction, Json([body.limitation]), user["email"], trajectory_id))
            if not cur.fetchone(): raise HTTPException(status_code=404, detail="Trajectory not found")
            _publish(cur, user["email"], "formation_twin.trajectory_updated", {"trajectory_id": trajectory_id, "status": "CORRECTED"}); _store_snapshot(cur, user["email"]); conn.commit()
        return {"ok": True}
    except Exception:
        conn.rollback(); raise
    finally: _state["release_db"](conn)


@router.get("/pattern-reviews")
def list_pattern_reviews(request: Request) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur: _owner(cur, user["email"]); cur.execute("SELECT * FROM formation_twin_pattern_reviews WHERE email=%s ORDER BY created_at DESC", (user["email"],)); items = [dict(row) for row in cur.fetchall()]
        return {"ok": True, "reviews": items}
    finally: _state["release_db"](conn)


@router.post("/pattern-reviews/generate")
def generate_review(request: Request, review_type: Literal["WEEKLY_PATTERN_REVIEW", "MONTHLY_FORMATION_REVIEW", "QUARTERLY_TRAJECTORY_REVIEW"] = "MONTHLY_FORMATION_REVIEW") -> dict[str, Any]:
    user = _user(request); tenant, profile = _identity(user["email"]); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); patterns = _list_patterns(cur, user["email"])
            days = 7 if review_type == "WEEKLY_PATTERN_REVIEW" else 90 if review_type == "QUARTERLY_TRAJECTORY_REVIEW" else 30
            end = datetime.now(timezone.utc); start = end - timedelta(days=days)
            payload = generate_pattern_review(review_type, patterns=patterns, window_start=start, window_end=end)
            review_id = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO formation_twin_pattern_reviews "
                "(id,tenant_id,profile_id,email,review_type,window_start,window_end,review_payload_json,status) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'PENDING')",
                (review_id, tenant, profile, user["email"], review_type, start, end, Json(payload)),
            )
            _publish(cur, user["email"], "formation_twin.pattern_review_created", {"review_id": review_id, "status": "PENDING"}); conn.commit()
        return {"ok": True, "review_id": review_id, "review": payload}
    except Exception:
        conn.rollback(); raise
    finally: _state["release_db"](conn)


@router.get("/pattern-reviews/{review_id}")
def get_pattern_review(request: Request, review_id: str) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur: _owner(cur, user["email"]); cur.execute("SELECT * FROM formation_twin_pattern_reviews WHERE email=%s AND id=%s", (user["email"], review_id)); item = cur.fetchone()
        if not item: raise HTTPException(status_code=404, detail="Review not found")
        return {"ok": True, "review": dict(item)}
    finally: _state["release_db"](conn)


@router.post("/pattern-reviews/{review_id}/complete")
def complete_pattern_review(request: Request, review_id: str, body: ReviewCompleteBody) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); cur.execute("UPDATE formation_twin_pattern_reviews SET status='COMPLETED',completed_at=now() WHERE email=%s AND id=%s AND status='PENDING' RETURNING id", (user["email"], review_id))
            if not cur.fetchone(): raise HTTPException(status_code=404, detail="Pending review not found")
            _publish(cur, user["email"], "formation_twin.pattern_review_completed", {"review_id": review_id, "status": "COMPLETED"}); conn.commit()
        return {"ok": True}
    except Exception:
        conn.rollback(); raise
    finally: _state["release_db"](conn)


@router.post("/pattern-reviews/{review_id}/skip")
def skip_pattern_review(request: Request, review_id: str) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); cur.execute("UPDATE formation_twin_pattern_reviews SET status='SKIPPED',skipped_at=now() WHERE email=%s AND id=%s AND status='PENDING' RETURNING id", (user["email"], review_id))
            if not cur.fetchone(): raise HTTPException(status_code=404, detail="Pending review not found")
            _publish(cur, user["email"], "formation_twin.pattern_review_skipped", {"review_id": review_id, "status": "SKIPPED"}); conn.commit()
        return {"ok": True, "patterns_implicitly_confirmed": False}
    except Exception:
        conn.rollback(); raise
    finally: _state["release_db"](conn)


def _run_rebuild(cur, email: str, job_id: str) -> dict[str, Any]:
    tenant, profile = _identity(email); now = datetime.now(timezone.utc)
    settings = _ensure_settings(cur, email)
    if not settings.get("temporal_engine_enabled") or not settings.get("pattern_discovery_enabled"):
        return {"status": "SKIPPED", "reason": "FEATURE_DISABLED", "created_patterns": 0}
    cur.execute("SELECT COALESCE(safety_json->>'safety_level','NONE') AS safety_level FROM formation_twin_life_events WHERE email=%s AND deleted_at IS NULL ORDER BY occurred_at DESC LIMIT 1", (email,))
    safety = cur.fetchone()
    if safety and safety["safety_level"] in {"ELEVATED", "IMMINENT"}:
        _publish(cur, email, "formation_twin.pattern_inference_blocked", {"status": "CRISIS_SAFETY_GATE"})
        return {"status": "BLOCKED", "reason": "CRISIS_SAFETY_GATE", "created_patterns": 0}
    cur.execute(
        "SELECT c.id AS source_record_id,c.life_event_id,c.user_review_status,c.scope,c.alternative_of_chain_id,"
        "COALESCE(le.occurred_at,c.created_at) AS occurred_at,le.processing_preference,"
        "COALESCE((SELECT json_agg(json_build_object('node_type',n.node_type) ORDER BY cn.sequence_order) "
        "FROM formation_twin_chain_nodes cn JOIN formation_twin_formation_nodes n ON n.id=cn.node_id "
        "WHERE cn.chain_id=c.id AND cn.email=c.email AND n.email=c.email AND n.deleted_at IS NULL),'[]'::json) AS nodes,"
        "COALESCE((SELECT json_agg(json_build_object('relation_type',e.relation_type) ORDER BY ce.sequence_order) "
        "FROM formation_twin_chain_edges ce JOIN formation_twin_formation_edges e ON e.id=ce.edge_id "
        "WHERE ce.chain_id=c.id AND ce.email=c.email AND e.email=c.email AND e.deleted_at IS NULL),'[]'::json) AS edges "
        "FROM formation_twin_formation_chains c "
        "LEFT JOIN formation_twin_life_events le ON le.id=c.life_event_id AND le.email=c.email AND le.deleted_at IS NULL "
        "WHERE c.email=%s AND c.deleted_at IS NULL AND c.processing_status='ACTIVE' AND c.excluded_from_context=FALSE "
        "AND c.user_review_status IN ('CONFIRMED','PARTIALLY_CONFIRMED') "
        "AND (le.id IS NULL OR (le.processing_preference='ALLOW_FUTURE_ANALYSIS' AND le.status='ACCEPTED' AND le.exclude_from_twin_processing=FALSE))",
        (email,),
    )
    chain_rows = cur.fetchall()
    cur.execute(
        "SELECT id,started_at,ended_at FROM formation_twin_life_seasons WHERE email=%s AND deleted_at IS NULL "
        "AND user_review_status IN('CONFIRMED','PARTIALLY_CONFIRMED') ORDER BY started_at DESC",
        (email,),
    )
    season_windows = [dict(item) for item in cur.fetchall()]
    chains = []
    for row in chain_rows:
        nodes = row["nodes"] or []
        edges = row["edges"] or []
        season = next((item for item in season_windows if item["started_at"] <= row["occurred_at"] and (item["ended_at"] is None or row["occurred_at"] <= item["ended_at"])), None)
        chains.append({
            "source_record_id": str(row["source_record_id"]), "life_event_id": str(row["life_event_id"] or row["source_record_id"]),
            "independence_group": f"life_event:{row['life_event_id'] or row['source_record_id']}", "confirmed": True,
            "occurred_at": row["occurred_at"], "processing_preference": row["processing_preference"] or "ALLOW_FUTURE_ANALYSIS",
            "signature": {"node_types": [item["node_type"] for item in nodes], "relation_types": [item["relation_type"] for item in edges]},
            "life_domain": None, "life_season_id": str(season["id"]) if season else None,
            "is_alternative_response": bool(row["alternative_of_chain_id"]),
        })
    candidates = discover_rule_pattern_candidates(chains)
    created = skipped_rejected = 0
    for candidate in candidates:
        cur.execute("SELECT id,lifecycle_status,user_review_status FROM formation_twin_patterns WHERE email=%s AND pattern_key=%s ORDER BY version DESC", (email, candidate["pattern_key"]))
        existing = [dict(item) for item in cur.fetchall()]
        if any(item["lifecycle_status"] == "REJECTED" or item["user_review_status"] == "DO_NOT_SUGGEST_AGAIN" for item in existing):
            skipped_rejected += 1; continue
        if any(item["lifecycle_status"] in {"CANDIDATE", "PENDING_USER_REVIEW", "CONFIRMED_ACTIVE", "CONFIRMED_CONTEXTUAL", "WEAKENING", "DORMANT"} for item in existing):
            continue
        pattern_id = str(uuid.uuid4()); review_due = max(now + timedelta(days=30), candidate["last_observed_at"] + timedelta(days=30))
        evidence_items = []
        for record_id in candidate["supporting_record_ids"]:
            chain = next(item for item in chains if item["source_record_id"] == record_id)
            weight, strategy = temporal_weight(chain["occurred_at"], "FORMATION_CHAIN", now=now)
            evidence_items.append({
                "id": str(uuid.uuid4()), "evidence_role": "SUPPORTING", "evidence_type": "CONFIRMED_FORMATION_CHAIN",
                "source_record_type": "FORMATION_CHAIN", "source_record_id": record_id, "occurred_at": chain["occurred_at"],
                "temporal_weight": weight, "decay_strategy": strategy, "source_quality": "USER_CONFIRMED_CHAIN",
                "independence_group": chain["independence_group"], "relevance": 1.0, "user_review_status": "CONFIRMED",
                "explanation": "用户确认的形成链提供了独立结构证据。",
            })
        confidence = calculate_pattern_confidence(evidence_items, now=now).model_dump(mode="json")
        description = "多条已确认记录出现了相似的形成链结构；请核对它是否只适用于当前阶段或特定领域。"
        cur.execute(
            "INSERT INTO formation_twin_patterns "
            "(id,tenant_id,profile_id,email,pattern_key,title,pattern_type,description,trigger_signature_json,scope_json,"
            "lifecycle_status,confidence_json,evidence_quality,source_kind,statement_type,user_review_status,"
            "alternative_explanations_json,limitations_json,first_observed_at,last_observed_at,review_due_at,rule_version,engine_version,is_alternative_response,version) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PENDING_USER_REVIEW',%s,'USER_CONFIRMED_CHAIN','RULE',"
            "'RULE_PATTERN_HYPOTHESIS','PENDING',%s,%s,%s,%s,%s,%s,%s,%s,1)",
            (
                pattern_id, tenant, profile, email, candidate["pattern_key"], "重复出现的形成链结构",
                candidate["pattern_type"], description, Json(candidate["signature"]), Json(candidate["scope"]),
                Json(confidence), Json(["这些记录也可能因现实任务或共同阶段而相似。"]),
                Json(candidate["limitations"]), candidate["first_observed_at"], candidate["last_observed_at"],
                review_due, RULE_VERSION, ENGINE_VERSION, candidate["is_alternative_response"],
            ),
        )
        for item in evidence_items:
            cur.execute(
                "INSERT INTO formation_twin_pattern_evidence "
                "(id,tenant_id,profile_id,email,pattern_id,evidence_role,evidence_type,source_record_type,source_record_id,"
                "occurred_at,temporal_weight,decay_strategy,source_quality,independence_group,relevance,user_review_status,explanation) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (item["id"], tenant, profile, email, pattern_id, item["evidence_role"], item["evidence_type"], item["source_record_type"], item["source_record_id"], item["occurred_at"], item["temporal_weight"], item["decay_strategy"], item["source_quality"], item["independence_group"], item["relevance"], item["user_review_status"], item["explanation"]),
            )
        for season_id in candidate["scope"].get("life_season_ids", []):
            cur.execute(
                "INSERT INTO formation_twin_pattern_life_seasons (id,tenant_id,profile_id,email,pattern_id,life_season_id,relation_type) "
                "VALUES (%s,%s,%s,%s,%s,%s,'OBSERVED_DURING') ON CONFLICT DO NOTHING",
                (str(uuid.uuid4()), tenant, profile, email, pattern_id, season_id),
            )
        _publish(cur, email, "formation_twin.pattern_candidate_created", {"pattern_id": pattern_id, "source_kind": "RULE"}); created += 1
        if settings.get("graph_evidence_enabled"):
            graph = sync_temporal_pattern(tenant_id=tenant, profile_id=profile, pattern={"id": pattern_id, "pattern_type": candidate["pattern_type"], "lifecycle_status": "PENDING_USER_REVIEW", "user_review_status": "PENDING", "version": 1, "first_observed_at": candidate["first_observed_at"], "review_due_at": review_due}, evidence=evidence_items)
            cur.execute("INSERT INTO formation_twin_temporal_graph_syncs (id,tenant_id,profile_id,email,pattern_id,sync_status,node_count,relationship_count) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", (str(uuid.uuid4()), tenant, profile, email, pattern_id, graph["status"], graph["nodes"], graph["relationships"]))
    snapshot = _store_snapshot(cur, email)
    return {"status": "COMPLETED", "eligible_chains": len(chains), "candidates": len(candidates), "created_patterns": created, "preserved_rejections": skipped_rejected, "snapshot_stored": snapshot["stored"]}


@router.post("/patterns/rebuild")
def rebuild_patterns(request: Request, body: RebuildBody) -> dict[str, Any]:
    user = _user(request); tenant, profile = _identity(user["email"]); job_id = str(uuid.uuid4()); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); cur.execute("INSERT INTO formation_twin_pattern_rebuild_jobs (id,tenant_id,profile_id,email,trigger_reason,status,engine_version,rule_version,started_at) VALUES (%s,%s,%s,%s,%s,'RUNNING',%s,%s,now())", (job_id, tenant, profile, user["email"], body.reason, ENGINE_VERSION, RULE_VERSION))
            report = _run_rebuild(cur, user["email"], job_id); final_status = report["status"]
            cur.execute("UPDATE formation_twin_pattern_rebuild_jobs SET status=%s,report_json=%s,completed_at=CASE WHEN %s IN ('COMPLETED','SKIPPED','BLOCKED') THEN now() END WHERE id=%s", (final_status, Json(report), final_status, job_id)); conn.commit()
        return {"ok": True, "job_id": job_id, "status": final_status, "report": report}
    except Exception:
        conn.rollback()
        try:
            with _cursor(conn) as cur:
                _owner(cur, user["email"]); cur.execute("UPDATE formation_twin_pattern_rebuild_jobs SET status='FAILED',failed_at=now(),error_code='REBUILD_FAILED' WHERE id=%s", (job_id,)); conn.commit()
        except Exception:
            conn.rollback()
        raise
    finally: _state["release_db"](conn)


@router.get("/patterns/rebuild/{job_id}")
def get_pattern_rebuild(request: Request, job_id: str) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur: _owner(cur, user["email"]); cur.execute("SELECT id,trigger_reason,status,checkpoint_json,report_json,engine_version,rule_version,created_at,started_at,completed_at,failed_at,error_code FROM formation_twin_pattern_rebuild_jobs WHERE email=%s AND id=%s", (user["email"], job_id)); item = cur.fetchone()
        if not item: raise HTTPException(status_code=404, detail="Rebuild job not found")
        return {"ok": True, "job": dict(item)}
    finally: _state["release_db"](conn)


@router.get("/long-term-state/current")
def current_long_term_state(request: Request) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); cur.execute("SELECT * FROM formation_twin_long_term_snapshots WHERE email=%s AND superseded_at IS NULL ORDER BY created_at DESC LIMIT 1", (user["email"],)); item = cur.fetchone()
        if not item: return {"ok": True, "data_status": "INSUFFICIENT_DATA", "snapshot": None, "limitations": ["至少需要三项独立事件或两条用户确认形成链。"]}
        return {"ok": True, "data_status": "AVAILABLE", "snapshot": dict(item)}
    finally: _state["release_db"](conn)


@router.delete("/long-term-state")
def erase_long_term_state(request: Request, body: LongTermEraseBody) -> dict[str, Any]:
    user = _user(request); tenant, profile = _identity(user["email"])
    try:
        graph = erase_temporal_graph(tenant_id=tenant, profile_id=profile)
    except Exception:
        graph = {"status": "UNAVAILABLE", "deleted": 0}
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            _invalidate_reflections(cur, user["email"])
            for statement in (
                "DELETE FROM formation_twin_temporal_graph_syncs WHERE email=%s",
                "DELETE FROM formation_twin_pattern_processing_checkpoints WHERE email=%s",
                "DELETE FROM formation_twin_pattern_rebuild_jobs WHERE email=%s",
                "DELETE FROM formation_twin_long_term_snapshots WHERE email=%s",
                "DELETE FROM formation_twin_interpretation_preferences WHERE email=%s",
                "DELETE FROM formation_twin_pattern_reviews WHERE email=%s",
                "DELETE FROM formation_twin_trajectory_points WHERE email=%s",
                "DELETE FROM formation_twin_trajectories WHERE email=%s",
                "DELETE FROM formation_twin_pattern_life_seasons WHERE email=%s",
                "DELETE FROM formation_twin_life_seasons WHERE email=%s",
                "DELETE FROM formation_twin_pattern_lifecycle_events WHERE email=%s",
                "DELETE FROM formation_twin_pattern_confidence_history WHERE email=%s",
                "DELETE FROM formation_twin_pattern_evidence WHERE email=%s",
                "DELETE FROM formation_twin_patterns WHERE email=%s",
                "DELETE FROM formation_twin_event_cluster_members WHERE email=%s",
                "DELETE FROM formation_twin_event_clusters WHERE email=%s",
                "DELETE FROM formation_twin_temporal_windows WHERE email=%s",
                "DELETE FROM formation_twin_temporal_settings WHERE email=%s",
            ):
                cur.execute(statement, (user["email"],))
            conn.commit()
        return {"ok": True, "erased": True, "source_events_preserved": True, "graph": graph}
    except Exception:
        conn.rollback(); raise
    finally: _state["release_db"](conn)


@router.get("/interpretation-preferences")
def list_interpretation_preferences(request: Request) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); cur.execute(
                "SELECT id,preference_type,preference_payload_json,scope,source_review_id,active,created_at,revoked_at "
                "FROM formation_twin_interpretation_preferences WHERE email=%s ORDER BY created_at DESC",
                (user["email"],),
            ); items = [dict(row) for row in cur.fetchall()]
        return {"ok": True, "preferences": items, "shared_model_training": False}
    finally: _state["release_db"](conn)


@router.delete("/interpretation-preferences/{preference_id}")
def revoke_interpretation_preference(request: Request, preference_id: str) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); cur.execute(
                "UPDATE formation_twin_interpretation_preferences SET active=FALSE,revoked_at=now() "
                "WHERE email=%s AND id=%s AND active=TRUE RETURNING id",
                (user["email"], preference_id),
            )
            if not cur.fetchone(): raise HTTPException(status_code=404, detail="Active preference not found")
            conn.commit()
        return {"ok": True, "revoked": True}
    except Exception:
        conn.rollback(); raise
    finally: _state["release_db"](conn)


@router.get("/long-term-context/formation-engine")
def long_term_formation_context(request: Request) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"]); cur.execute("SELECT formation_context_consent FROM formation_twin_formation_settings WHERE email=%s", (user["email"],)); consent_row = cur.fetchone()
            cur.execute("SELECT COALESCE(safety_json->>'safety_level','NONE') AS safety_level FROM formation_twin_life_events WHERE email=%s AND deleted_at IS NULL ORDER BY occurred_at DESC LIMIT 1", (user["email"],)); safety_row = cur.fetchone()
            patterns = _list_patterns(cur, user["email"]); snapshot = build_long_term_snapshot(patterns=patterns, life_seasons=_life_seasons(cur, user["email"]), trajectories=_trajectories(cur, user["email"]), window_start=datetime.now(timezone.utc)-timedelta(days=365), window_end=datetime.now(timezone.utc))
        context = build_formation_engine_context(snapshot, consent=bool(consent_row and consent_row["formation_context_consent"]), safety_level=(safety_row or {}).get("safety_level", "NONE"))
        return {"ok": True, **context}
    finally: _state["release_db"](conn)


@router.get("/long-term-state/data-quality")
def pattern_data_quality(request: Request) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur: _owner(cur, user["email"]); patterns = _list_patterns(cur, user["email"]); report = temporal_data_quality(patterns)
        return {"ok": True, "scope": "current_user", **report}
    finally: _state["release_db"](conn)


@router.get("/pattern-jobs")
def pattern_jobs(request: Request) -> dict[str, Any]:
    _user(request)
    return {"ok": True, "jobs": SCHEDULED_PATTERN_JOBS, "scheduler_adapter": "existing scheduler / manual rebuild", "sensitive_labels": False}
