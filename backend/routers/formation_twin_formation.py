"""Formation Twin Batch 4 API: reviewable spiritual-formation chains.

The router keeps user reports, observations, rules, model hypotheses, and
user-confirmed patterns as different records.  Crisis routing always runs
before formation processing, and full sensitive text never enters events,
logs, snapshots, or the optional graph.
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator, model_validator
from psycopg2.extras import Json

from formation_twin.crypto import EncryptedContent, decrypt_text
from formation_twin.formation_graph import graph_status, sync_reviewed_chain
from formation_twin.formation_inference import infer_formation_candidates
from formation_twin.formation_ontology import (
    DEEP_FORMATION_TYPES,
    NODE_TYPES,
    RELATIONS,
    SCOPES,
)
from formation_twin.formation_safety import crisis_blocks_formation
from formation_twin.spiritual_engine import ENGINE_VERSION, build_formation_snapshot, context_envelope


router = APIRouter(prefix="/api/v1/formation-twin", tags=["formation-twin-formation"])
_state: dict[str, Any] = {}

SPECIAL_TABLES = {
    "IDENTITY_STATEMENT": "formation_twin_identity_statements",
    "INTERPRETATION": "formation_twin_interpretations",
    "BELIEF_STATEMENT": "formation_twin_belief_statements",
    "DESIRE": "formation_twin_desire_observations",
    "FEAR": "formation_twin_fear_observations",
    "TEMPTATION": "formation_twin_temptation_observations",
    "BEHAVIOR": "formation_twin_behavior_observations",
    "SPIRITUAL_PRACTICE": "formation_twin_behavior_observations",
    "OUTCOME": "formation_twin_outcome_observations",
}
SNAPSHOT_KINDS = {
    "current": ("CURRENT_FORMATION_STATE", timedelta(days=30)),
    "daily": ("DAILY_FORMATION_SUMMARY", timedelta(days=1)),
    "weekly": ("WEEKLY_FORMATION_SUMMARY", timedelta(days=7)),
}
EVENT_LABELS = {
    "DAILY_CHECKIN": "记录到一次主动状态签到",
    "JOURNAL_ENTRY": "记录到一次经授权的生命反思",
    "VOICE_JOURNAL": "记录到一次用户确认的语音反思",
    "PRAYER_ACTIVITY": "记录到一次经授权的祷告活动",
    "DEVOTION_ACTIVITY": "记录到一次经授权的灵修活动",
    "HABIT_ACTIVITY": "记录到一次经授权的习惯活动",
    "ATTENTION_ACTIVITY": "记录到一次经授权的注意力活动",
    "CHURCH_ACTIVITY": "记录到一次经授权的教会活动",
    "FORMATION_ACTIVITY": "记录到一次经授权的形成活动",
}


def init_formation_twin_formation_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _identity(email: str) -> tuple[str, str]:
    return f"personal:{email.lower()}", str(uuid.uuid5(uuid.NAMESPACE_URL, f"formation-twin:{email.lower()}"))


def _owner(cur, email: str) -> None:
    cur.execute("SELECT set_config('app.current_user_email',%s,true)", (email,))


def _publish(cur, email: str, event_type: str, payload: dict) -> None:
    safe = {key: value for key, value in payload.items() if key.endswith("_id") or key in {"action", "source_kind", "status", "snapshot_type", "engine_version"}}
    cur.execute(
        "INSERT INTO domain_events (aggregate_type,aggregate_id,event_type,payload) VALUES (%s,%s,%s,%s)",
        ("formation_twin", email, event_type, Json(safe)),
    )


class SettingsBody(BaseModel):
    spiritual_engine_enabled: bool = True
    formation_chain_enabled: bool = True
    belief_hypothesis_enabled: bool = False
    graph_enabled: bool = False
    theological_validator_enabled: bool = True
    prayer_context_consent: bool = False
    habit_context_consent: bool = False
    attention_context_consent: bool = False
    formation_context_consent: bool = False
    provider_policy: Literal["DISABLED", "CONFIGURED_PROVIDER"] = "DISABLED"

    @model_validator(mode="after")
    def provider_requires_explicit_opt_in(self):
        if not self.theological_validator_enabled:
            raise ValueError("theological validator cannot be disabled")
        if self.belief_hypothesis_enabled and self.provider_policy != "CONFIGURED_PROVIDER":
            raise ValueError("model hypotheses require CONFIGURED_PROVIDER")
        return self


class NodeBody(BaseModel):
    node_type: str
    content: str = Field(min_length=1, max_length=2000)
    life_event_id: str | None = None
    scope: str = "THIS_EVENT_ONLY"

    @field_validator("node_type")
    @classmethod
    def known_node_type(cls, value: str) -> str:
        if value not in NODE_TYPES:
            raise ValueError("unknown node_type")
        return value

    @field_validator("scope")
    @classmethod
    def known_scope(cls, value: str) -> str:
        if value not in SCOPES:
            raise ValueError("unknown scope")
        return value


class NodePatch(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=2000)
    scope: str | None = None
    node_type: str | None = None

    @model_validator(mode="after")
    def validate_values(self):
        if self.node_type is not None and self.node_type not in NODE_TYPES:
            raise ValueError("unknown node_type")
        if self.scope is not None and self.scope not in SCOPES:
            raise ValueError("unknown scope")
        return self


class ReviewBody(BaseModel):
    content: str | None = Field(default=None, max_length=2000)
    scope: str = "THIS_EVENT_ONLY"
    node_type: str | None = None
    user_comment: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_values(self):
        if self.scope not in SCOPES:
            raise ValueError("unknown scope")
        if self.node_type is not None and self.node_type not in NODE_TYPES:
            raise ValueError("unknown node_type")
        return self


class BulkReviewBody(BaseModel):
    node_ids: list[str] = Field(min_length=1, max_length=100)


class ChainBody(BaseModel):
    title: str = Field(default="", max_length=160)
    life_event_id: str | None = None
    scope: str = "THIS_EVENT_ONLY"
    node_ids: list[str] = Field(default_factory=list, max_length=30)

    @field_validator("scope")
    @classmethod
    def known_scope(cls, value: str) -> str:
        if value not in SCOPES:
            raise ValueError("unknown scope")
        return value


class AddNodeBody(BaseModel):
    node_id: str
    sequence_order: int = Field(ge=0, le=1000)


class EdgeBody(BaseModel):
    source_node_id: str
    target_node_id: str
    relation_type: str = "USER_ASSOCIATED_WITH"
    sequence_order: int = Field(default=0, ge=0, le=1000)

    @field_validator("relation_type")
    @classmethod
    def known_relation(cls, value: str) -> str:
        if value not in RELATIONS:
            raise ValueError("unknown relation_type")
        return value


def _settings(cur, email: str, *, create: bool = True) -> dict:
    tenant, profile = _identity(email)
    if create:
        cur.execute(
            "INSERT INTO formation_twin_formation_settings (id,tenant_id,profile_id,email) VALUES (%s,%s,%s,%s) ON CONFLICT (tenant_id,profile_id) DO NOTHING",
            (str(uuid.uuid4()), tenant, profile, email),
        )
    cur.execute(
        "SELECT spiritual_engine_enabled,formation_chain_enabled,belief_hypothesis_enabled,graph_enabled,theological_validator_enabled,"
        "prayer_context_consent,habit_context_consent,attention_context_consent,formation_context_consent,provider_policy,consent_version,updated_at "
        "FROM formation_twin_formation_settings WHERE email=%s",
        (email,),
    )
    row = cur.fetchone()
    if not row:
        return {}
    keys = ["spiritual_engine_enabled", "formation_chain_enabled", "belief_hypothesis_enabled", "graph_enabled", "theological_validator_enabled", "prayer_context_consent", "habit_context_consent", "attention_context_consent", "formation_context_consent", "provider_policy", "consent_version", "updated_at"]
    result = dict(zip(keys, row))
    result["updated_at"] = result["updated_at"].isoformat()
    return result


@router.get("/formation-settings")
def get_settings(request: Request) -> dict:
    user = _user(request); conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"]); settings = _settings(cur, user["email"]); conn.commit()
        return {"ok": True, "settings": settings, "defaults": {"model_hypotheses": False, "graph": False, "context_integrations": False}}
    finally:
        _state["release_db"](conn)


@router.put("/formation-settings")
def update_settings(request: Request, body: SettingsBody) -> dict:
    user = _user(request); tenant, profile = _identity(user["email"]); conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"])
            values = body.model_dump()
            cur.execute(
                "INSERT INTO formation_twin_formation_settings (id,tenant_id,profile_id,email,spiritual_engine_enabled,formation_chain_enabled,belief_hypothesis_enabled,graph_enabled,theological_validator_enabled,prayer_context_consent,habit_context_consent,attention_context_consent,formation_context_consent,provider_policy) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (tenant_id,profile_id) DO UPDATE SET spiritual_engine_enabled=EXCLUDED.spiritual_engine_enabled,formation_chain_enabled=EXCLUDED.formation_chain_enabled,belief_hypothesis_enabled=EXCLUDED.belief_hypothesis_enabled,graph_enabled=EXCLUDED.graph_enabled,theological_validator_enabled=EXCLUDED.theological_validator_enabled,prayer_context_consent=EXCLUDED.prayer_context_consent,habit_context_consent=EXCLUDED.habit_context_consent,attention_context_consent=EXCLUDED.attention_context_consent,formation_context_consent=EXCLUDED.formation_context_consent,provider_policy=EXCLUDED.provider_policy,updated_at=now()",
                (str(uuid.uuid4()), tenant, profile, user["email"], *values.values()),
            )
            settings = _settings(cur, user["email"], create=False); conn.commit()
        return {"ok": True, "settings": settings}
    except Exception:
        conn.rollback(); raise
    finally:
        _state["release_db"](conn)


def _mirror_special(cur, *, email: str, node_id: str, body: dict, source_kind: str,
                    statement_type: str, review_status: str) -> tuple[str | None, str | None]:
    table = SPECIAL_TABLES.get(body["node_type"])
    if not table:
        return None, None
    tenant, profile = _identity(email); record_id = str(uuid.uuid4())
    extra_columns = ",behavior_kind" if table == "formation_twin_behavior_observations" else ""
    extra_values = ",%s" if extra_columns else ""
    params: list[Any] = [record_id, tenant, profile, email, body["content"], source_kind, statement_type, body.get("scope", "THIS_EVENT_ONLY"), review_status, body.get("life_event_id")]
    if extra_columns:
        params.append("SPIRITUAL_PRACTICE" if body["node_type"] == "SPIRITUAL_PRACTICE" else "BEHAVIOR")
    cur.execute(
        f"INSERT INTO {table} (id,tenant_id,profile_id,email,content,source_kind,statement_type,scope,user_review_status,life_event_id{extra_columns}) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s{extra_values})",
        tuple(params),
    )
    return table, record_id


def _insert_node(cur, *, email: str, body: dict, source_kind: str, statement_type: str,
                 review_status: str, confidence: float | None = None, evidence: list | None = None,
                 alternatives: list | None = None, emotion_observation_id: str | None = None,
                 model_meta: dict | None = None, expires_at: str | None = None,
                 supersedes_id: str | None = None) -> str:
    tenant, profile = _identity(email); node_id = str(uuid.uuid4())
    canonical_type, canonical_id = _mirror_special(
        cur, email=email, node_id=node_id, body=body, source_kind=source_kind,
        statement_type=statement_type, review_status=review_status,
    )
    meta = model_meta or {}
    cur.execute(
        "INSERT INTO formation_twin_formation_nodes (id,tenant_id,profile_id,email,node_type,content,canonical_record_type,canonical_record_id,life_event_id,emotion_observation_id,source_kind,statement_type,scope,confidence,alternatives_json,evidence_json,user_review_status,processing_status,model_version,prompt_version,schema_version,rule_version,supersedes_id,expires_at,occurred_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'ACTIVE',%s,%s,%s,%s,%s,%s,%s)",
        (node_id, tenant, profile, email, body["node_type"], body["content"], canonical_type, canonical_id,
         body.get("life_event_id"), emotion_observation_id, source_kind, statement_type, body.get("scope", "THIS_EVENT_ONLY"),
         confidence, Json(alternatives or []), Json(evidence or []), review_status, meta.get("model_version"),
         meta.get("prompt_version"), meta.get("schema_version"), meta.get("rule_version"), supersedes_id, expires_at, body.get("occurred_at") or datetime.now(timezone.utc)),
    )
    for item in evidence or []:
        start = item.get("start_offset")
        end = item.get("end_offset")
        digest = hashlib.sha256(json.dumps(item, sort_keys=True).encode()).hexdigest()
        cur.execute(
            "INSERT INTO formation_twin_formation_evidence (id,tenant_id,profile_id,email,node_id,life_event_id,evidence_type,start_offset,end_offset,evidence_hash) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (str(uuid.uuid4()), tenant, profile, email, node_id, body.get("life_event_id"), "TEXT_SPAN", start, end, digest),
        )
    return node_id


def _update_special_for_node(cur, *, email: str, node_id: str, deleted: bool = False,
                             review_status: str | None = None) -> None:
    cur.execute("SELECT canonical_record_type,canonical_record_id FROM formation_twin_formation_nodes WHERE id=%s AND email=%s", (node_id, email)); row = cur.fetchone()
    if not row or row[0] not in set(SPECIAL_TABLES.values()) or not row[1]:
        return
    if deleted:
        cur.execute(f"UPDATE {row[0]} SET deleted_at=now() WHERE id=%s AND email=%s", (row[1], email))
    if review_status:
        cur.execute(f"UPDATE {row[0]} SET user_review_status=%s WHERE id=%s AND email=%s", (review_status, row[1], email))


def _delete_generated_special_records(cur, *, email: str) -> None:
    for table in set(SPECIAL_TABLES.values()):
        cur.execute(
            f"UPDATE {table} SET deleted_at=now() WHERE email=%s AND deleted_at IS NULL AND id IN (SELECT canonical_record_id FROM formation_twin_formation_nodes WHERE email=%s AND source_kind IN ('OBSERVATION','RULE','MODEL') AND deleted_at IS NULL AND canonical_record_type=%s)",
            (email, email, table),
        )


def _node_rows(cur, email: str, *, where: str = "", params: tuple = ()) -> list[dict]:
    cur.execute(
        "SELECT id,node_type,content,life_event_id,emotion_observation_id,source_kind,statement_type,scope,confidence,alternatives_json,evidence_json,user_review_status,processing_status,model_version,prompt_version,schema_version,rule_version,revision,supersedes_id,expires_at,occurred_at,created_at "
        "FROM formation_twin_formation_nodes WHERE email=%s AND deleted_at IS NULL " + where + " ORDER BY created_at DESC",
        (email, *params),
    )
    keys = ["id", "node_type", "content", "life_event_id", "emotion_observation_id", "source_kind", "statement_type", "scope", "confidence", "alternatives", "evidence", "user_review_status", "processing_status", "model_version", "prompt_version", "schema_version", "rule_version", "revision", "supersedes_id", "expires_at", "occurred_at", "created_at"]
    items = []
    for row in cur.fetchall():
        item = dict(zip(keys, row))
        for key in ("id", "life_event_id", "emotion_observation_id", "supersedes_id"):
            item[key] = str(item[key]) if item[key] else None
        item["confidence"] = float(item["confidence"]) if item["confidence"] is not None else None
        for key in ("expires_at", "occurred_at", "created_at"):
            item[key] = item[key].isoformat() if item[key] else None
        items.append(item)
    return items


@router.post("/formation-nodes")
def create_node(request: Request, body: NodeBody) -> dict:
    user = _user(request); conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"])
            if body.life_event_id:
                cur.execute("SELECT 1 FROM formation_twin_life_events WHERE id=%s AND email=%s AND deleted_at IS NULL", (body.life_event_id, user["email"]))
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="Life event not found")
            node_id = _insert_node(cur, email=user["email"], body=body.model_dump(), source_kind="USER_REPORT", statement_type="USER_REPORTED_FACT", review_status="NOT_REQUIRED")
            _invalidate_snapshots(cur, user["email"]); _publish(cur, user["email"], "formation_twin.formation_node_created", {"node_id": node_id, "source_kind": "USER_REPORT"}); conn.commit()
        return {"ok": True, "node_id": node_id}
    except Exception:
        conn.rollback(); raise
    finally:
        _state["release_db"](conn)


@router.get("/formation-nodes")
def list_nodes(request: Request, node_type: str | None = None, source_kind: str | None = None,
               review_status: str | None = None, include_inactive: bool = False,
               limit: int = Query(200, ge=1, le=500)) -> dict:
    user = _user(request); conn = _state["get_db"]()
    try:
        clauses = []; params: list[Any] = []
        for column, value in (("node_type", node_type), ("source_kind", source_kind), ("user_review_status", review_status)):
            if value:
                clauses.append(f"{column}=%s"); params.append(value)
        if not include_inactive:
            clauses.append("processing_status='ACTIVE'")
        where = ("AND " + " AND ".join(clauses)) if clauses else ""
        with conn.cursor() as cur:
            _owner(cur, user["email"]); items = _node_rows(cur, user["email"], where=where, params=tuple(params))[:limit]
        return {"ok": True, "items": items}
    finally:
        _state["release_db"](conn)


@router.get("/formation-nodes/{node_id}")
def get_node(node_id: str, request: Request) -> dict:
    user = _user(request); conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"]); items = _node_rows(cur, user["email"], where="AND id=%s", params=(node_id,))
        if not items:
            raise HTTPException(status_code=404, detail="Formation node not found")
        return {"ok": True, "node": items[0]}
    finally:
        _state["release_db"](conn)


@router.patch("/formation-nodes/{node_id}")
def revise_node(node_id: str, request: Request, body: NodePatch) -> dict:
    current = get_node(node_id, request)["node"]
    if current["source_kind"] != "USER_REPORT":
        raise HTTPException(status_code=409, detail="Use review actions for non-user records")
    user = _user(request); conn = _state["get_db"]()
    try:
        new_body = {"node_type": body.node_type or current["node_type"], "content": body.content or current["content"], "scope": body.scope or current["scope"], "life_event_id": current["life_event_id"]}
        with conn.cursor() as cur:
            _owner(cur, user["email"]); new_id = _insert_node(cur, email=user["email"], body=new_body, source_kind="USER_REPORT", statement_type="USER_REPORTED_FACT", review_status="NOT_REQUIRED", supersedes_id=node_id)
            _update_special_for_node(cur, email=user["email"], node_id=node_id, deleted=True)
            cur.execute("UPDATE formation_twin_formation_nodes SET processing_status='SUPERSEDED' WHERE id=%s AND email=%s", (node_id, user["email"]))
            _invalidate_snapshots(cur, user["email"]); conn.commit()
        return {"ok": True, "node_id": new_id, "supersedes_id": node_id}
    except Exception:
        conn.rollback(); raise
    finally:
        _state["release_db"](conn)


@router.delete("/formation-nodes/{node_id}")
def delete_node(node_id: str, request: Request) -> dict:
    user = _user(request); conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"])
            _update_special_for_node(cur, email=user["email"], node_id=node_id, deleted=True)
            cur.execute("UPDATE formation_twin_formation_nodes SET deleted_at=now(),processing_status='DELETED' WHERE id=%s AND email=%s AND deleted_at IS NULL RETURNING id", (node_id, user["email"])); found = cur.fetchone()
            if found:
                cur.execute("UPDATE formation_twin_formation_edges SET deleted_at=now(),processing_status='DELETED' WHERE email=%s AND (source_node_id=%s OR target_node_id=%s)", (user["email"], node_id, node_id)); _invalidate_snapshots(cur, user["email"])
            conn.commit()
        if not found:
            raise HTTPException(status_code=404, detail="Formation node not found")
        return {"ok": True}
    finally:
        _state["release_db"](conn)


def _review_node(node_id: str, request: Request, body: ReviewBody, action: str) -> dict:
    user = _user(request); conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"]); items = _node_rows(cur, user["email"], where="AND id=%s", params=(node_id,))
            if not items:
                raise HTTPException(status_code=404, detail="Formation node not found")
            node = items[0]
            if node["source_kind"] != "MODEL" or node["user_review_status"] != "PENDING":
                raise HTTPException(status_code=409, detail="Only pending model hypotheses can be reviewed")
            status = {"confirm": "CONFIRMED", "partially-confirm": "PARTIALLY_CONFIRMED", "reject": "REJECTED", "relabel": "RELABELED", "change-scope": "SCOPE_CHANGED", "dismiss": "DISMISSED"}[action]
            cur.execute("UPDATE formation_twin_formation_nodes SET user_review_status=%s,processing_status='REVIEWED' WHERE id=%s", (status, node_id))
            _update_special_for_node(cur, email=user["email"], node_id=node_id, review_status=status)
            confirmed_id = None
            if action in {"confirm", "partially-confirm", "relabel", "change-scope"}:
                content = body.content or node["content"]
                node_type = body.node_type or node["node_type"]
                if action in {"partially-confirm", "relabel"} and not body.content:
                    raise HTTPException(status_code=422, detail="content is required")
                confirmed_id = _insert_node(
                    cur, email=user["email"], body={"node_type": node_type, "content": content, "scope": body.scope, "life_event_id": node["life_event_id"]},
                    source_kind="USER_CONFIRMED", statement_type="USER_CONFIRMED_FORMATION_PATTERN", review_status="NOT_REQUIRED", supersedes_id=node_id,
                )
            tenant, profile = _identity(user["email"]); review_id = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO formation_twin_formation_reviews (id,tenant_id,profile_id,email,node_id,review_action,scope,replacement_content,user_comment,created_by,confirmed_record_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (review_id, tenant, profile, user["email"], node_id, action.upper().replace("-", "_"), body.scope, body.content, body.user_comment, user["email"], confirmed_id),
            )
            _invalidate_snapshots(cur, user["email"]); _publish(cur, user["email"], "formation_twin.formation_hypothesis_reviewed", {"node_id": node_id, "review_id": review_id, "action": action}); conn.commit()
        return {"ok": True, "status": status, "review_id": review_id, "confirmed_node_id": confirmed_id}
    except Exception:
        conn.rollback(); raise
    finally:
        _state["release_db"](conn)


for _action in ("confirm", "partially-confirm", "reject", "relabel", "change-scope", "dismiss"):
    def _factory(action_name: str):
        async def endpoint(node_id: str, request: Request, body: ReviewBody | None = None):
            return _review_node(node_id, request, body or ReviewBody(), action_name)
        endpoint.__name__ = f"review_formation_node_{action_name.replace('-', '_')}"
        return endpoint
    router.post(f"/formation-nodes/{{node_id}}/{_action}")(_factory(_action))


@router.post("/formation-reviews/{review_id}/revoke")
def revoke_review(review_id: str, request: Request) -> dict:
    user = _user(request); conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"])
            cur.execute("UPDATE formation_twin_formation_reviews SET revoked_at=now() WHERE id=%s AND email=%s AND revoked_at IS NULL RETURNING node_id,confirmed_record_id", (review_id, user["email"])); row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Active review not found")
            if row[1]:
                _update_special_for_node(cur, email=user["email"], node_id=str(row[1]), deleted=True)
                cur.execute("UPDATE formation_twin_formation_nodes SET deleted_at=now(),processing_status='REVOKED' WHERE id=%s AND email=%s", (row[1], user["email"]))
            cur.execute("UPDATE formation_twin_formation_nodes SET user_review_status='PENDING',processing_status='ACTIVE' WHERE id=%s AND email=%s", (row[0], user["email"]))
            _update_special_for_node(cur, email=user["email"], node_id=str(row[0]), review_status="PENDING")
            _invalidate_snapshots(cur, user["email"]); conn.commit()
        return {"ok": True, "status": "REVOKED"}
    except Exception:
        conn.rollback(); raise
    finally:
        _state["release_db"](conn)


@router.post("/formation-nodes/{node_id}/revoke")
def revoke_node_confirmation(node_id: str, request: Request) -> dict:
    """Convenience endpoint: revoke the latest active review for a candidate node."""
    user = _user(request); conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"]); cur.execute("SELECT id FROM formation_twin_formation_reviews WHERE node_id=%s AND email=%s AND revoked_at IS NULL ORDER BY created_at DESC LIMIT 1", (node_id, user["email"])); row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Active confirmation not found")
        return revoke_review(str(row[0]), request)
    finally:
        _state["release_db"](conn)


@router.get("/formation-review-queue")
def review_queue(request: Request) -> dict:
    return list_nodes(request, source_kind="MODEL", review_status="PENDING", limit=200)


@router.post("/formation-review-queue/bulk-dismiss")
def bulk_dismiss(request: Request, body: BulkReviewBody) -> dict:
    results = []
    for node_id in dict.fromkeys(body.node_ids):
        try:
            results.append({"node_id": node_id, **_review_node(node_id, request, ReviewBody(), "dismiss")})
        except HTTPException as exc:
            results.append({"node_id": node_id, "ok": False, "detail": exc.detail})
    return {"ok": all(item.get("ok") for item in results), "results": results}


def _chain_rows(cur, email: str, chain_id: str | None = None) -> list[dict]:
    condition = "AND chain.id=%s" if chain_id else ""
    cur.execute(
        "SELECT chain.id,chain.title,chain.life_event_id,chain.creation_method,chain.scope,chain.completeness,chain.user_review_status,chain.processing_status,chain.limitations_json,chain.alternative_of_chain_id,chain.excluded_from_context,chain.version,chain.created_at,chain.updated_at "
        "FROM formation_twin_formation_chains chain WHERE chain.email=%s AND chain.deleted_at IS NULL " + condition + " ORDER BY chain.created_at DESC",
        (email, chain_id) if chain_id else (email,),
    )
    items = []
    for row in cur.fetchall():
        item = {"id": str(row[0]), "title": row[1], "life_event_id": str(row[2]) if row[2] else None, "creation_method": row[3], "scope": row[4], "completeness": float(row[5]), "user_review_status": row[6], "processing_status": row[7], "limitations": row[8], "alternative_of_chain_id": str(row[9]) if row[9] else None, "excluded_from_context": row[10], "version": row[11], "created_at": row[12].isoformat(), "updated_at": row[13].isoformat()}
        cur.execute("SELECT node_id,sequence_order FROM formation_twin_chain_nodes WHERE chain_id=%s AND email=%s ORDER BY sequence_order", (item["id"], email)); links = cur.fetchall(); ids = [str(link[0]) for link in links]
        nodes = []
        if ids:
            nodes = _node_rows(cur, email, where="AND id IN %s", params=(tuple(ids),)); by_id = {node["id"]: node for node in nodes}; nodes = [{**by_id[node_id], "sequence_order": order} for node_id, order in ((str(link[0]), link[1]) for link in links) if node_id in by_id]
        cur.execute("SELECT edge.id,edge.source_node_id,edge.target_node_id,edge.relation_type,edge.source_kind,edge.statement_type,edge.user_review_status,link.sequence_order FROM formation_twin_chain_edges link JOIN formation_twin_formation_edges edge ON edge.id=link.edge_id WHERE link.chain_id=%s AND link.email=%s AND edge.deleted_at IS NULL ORDER BY link.sequence_order", (item["id"], email));
        item["nodes"] = nodes
        item["edges"] = [{"id": str(edge[0]), "source_node_id": str(edge[1]), "target_node_id": str(edge[2]), "relation_type": edge[3], "source_kind": edge[4], "statement_type": edge[5], "user_review_status": edge[6], "sequence_order": edge[7]} for edge in cur.fetchall()]
        items.append(item)
    return items


@router.get("/formation-chains")
def list_chains(request: Request) -> dict:
    user = _user(request); conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"]); items = _chain_rows(cur, user["email"])
        return {"ok": True, "items": items}
    finally:
        _state["release_db"](conn)


@router.get("/formation-chains/{chain_id}")
def get_chain(chain_id: str, request: Request) -> dict:
    user = _user(request); conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"]); items = _chain_rows(cur, user["email"], chain_id)
        if not items:
            raise HTTPException(status_code=404, detail="Formation chain not found")
        return {"ok": True, "chain": items[0]}
    finally:
        _state["release_db"](conn)


def _insert_chain(cur, *, email: str, body: ChainBody, creation_method: str, alternative_of: str | None = None) -> str:
    tenant, profile = _identity(email); chain_id = str(uuid.uuid4())
    unique_ids = list(dict.fromkeys(body.node_ids))
    if unique_ids:
        cur.execute("SELECT id FROM formation_twin_formation_nodes WHERE email=%s AND id IN %s AND deleted_at IS NULL", (email, tuple(unique_ids)))
        found = {str(row[0]) for row in cur.fetchall()}
        if found != set(unique_ids):
            raise HTTPException(status_code=404, detail="One or more nodes were not found")
    completeness = min(1.0, len(unique_ids) / 8)
    cur.execute(
        "INSERT INTO formation_twin_formation_chains (id,tenant_id,profile_id,email,title,life_event_id,creation_method,scope,completeness,user_review_status,limitations_json,alternative_of_chain_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (chain_id, tenant, profile, email, body.title, body.life_event_id, creation_method, body.scope, completeness, "NOT_REQUIRED" if creation_method == "USER_CREATED" else "PENDING", Json(["缺失环节会保持为空，不会由系统补全。"]), alternative_of),
    )
    for order, node_id in enumerate(unique_ids):
        cur.execute("INSERT INTO formation_twin_chain_nodes (id,tenant_id,profile_id,email,chain_id,node_id,sequence_order) VALUES (%s,%s,%s,%s,%s,%s,%s)", (str(uuid.uuid4()), tenant, profile, email, chain_id, node_id, order))
    return chain_id


@router.post("/formation-chains")
def create_chain(request: Request, body: ChainBody) -> dict:
    user = _user(request); conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"]); chain_id = _insert_chain(cur, email=user["email"], body=body, creation_method="USER_CREATED"); _invalidate_snapshots(cur, user["email"]); conn.commit()
        return {"ok": True, "chain_id": chain_id}
    except Exception:
        conn.rollback(); raise
    finally:
        _state["release_db"](conn)


@router.patch("/formation-chains/{chain_id}")
def update_chain(chain_id: str, request: Request, body: ChainBody) -> dict:
    user = _user(request); conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"]); cur.execute("UPDATE formation_twin_formation_chains SET title=%s,scope=%s,updated_at=now(),version=version+1 WHERE id=%s AND email=%s AND deleted_at IS NULL RETURNING id", (body.title, body.scope, chain_id, user["email"])); found = cur.fetchone()
            if found and body.node_ids:
                unique_ids = list(dict.fromkeys(body.node_ids))
                cur.execute("SELECT id::text FROM formation_twin_formation_nodes WHERE email=%s AND id IN %s AND deleted_at IS NULL", (user["email"], tuple(unique_ids)))
                if {row[0] for row in cur.fetchall()} != set(unique_ids):
                    raise HTTPException(status_code=404, detail="One or more nodes were not found")
                tenant, profile = _identity(user["email"])
                cur.execute("UPDATE formation_twin_formation_edges edge SET deleted_at=now(),processing_status='DELETED' FROM formation_twin_chain_edges link WHERE link.edge_id=edge.id AND link.chain_id=%s AND link.email=%s AND (edge.source_node_id NOT IN %s OR edge.target_node_id NOT IN %s)", (chain_id, user["email"], tuple(unique_ids), tuple(unique_ids)))
                cur.execute("DELETE FROM formation_twin_chain_edges link USING formation_twin_formation_edges edge WHERE link.edge_id=edge.id AND link.chain_id=%s AND link.email=%s AND edge.deleted_at IS NOT NULL", (chain_id, user["email"]))
                cur.execute("DELETE FROM formation_twin_chain_nodes WHERE chain_id=%s AND email=%s", (chain_id, user["email"]))
                for order, node_id in enumerate(unique_ids):
                    cur.execute("INSERT INTO formation_twin_chain_nodes (id,tenant_id,profile_id,email,chain_id,node_id,sequence_order) VALUES (%s,%s,%s,%s,%s,%s,%s)", (str(uuid.uuid4()), tenant, profile, user["email"], chain_id, node_id, order))
            conn.commit()
        if not found:
            raise HTTPException(status_code=404, detail="Formation chain not found")
        return {"ok": True}
    finally:
        _state["release_db"](conn)


@router.delete("/formation-chains/{chain_id}")
def delete_chain(chain_id: str, request: Request) -> dict:
    return _chain_status(chain_id, request, "DELETED", deleted=True)


@router.post("/formation-chains/{chain_id}/nodes")
def add_chain_node(chain_id: str, request: Request, body: AddNodeBody) -> dict:
    user = _user(request); tenant, profile = _identity(user["email"]); conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"]); cur.execute("SELECT 1 FROM formation_twin_formation_chains WHERE id=%s AND email=%s AND deleted_at IS NULL", (chain_id, user["email"]));
            if not cur.fetchone(): raise HTTPException(status_code=404, detail="Formation chain not found")
            cur.execute("SELECT 1 FROM formation_twin_formation_nodes WHERE id=%s AND email=%s AND deleted_at IS NULL", (body.node_id, user["email"]));
            if not cur.fetchone(): raise HTTPException(status_code=404, detail="Formation node not found")
            cur.execute("UPDATE formation_twin_chain_nodes SET sequence_order=sequence_order+1 WHERE chain_id=%s AND email=%s AND sequence_order>=%s", (chain_id, user["email"], body.sequence_order))
            cur.execute("INSERT INTO formation_twin_chain_nodes (id,tenant_id,profile_id,email,chain_id,node_id,sequence_order) VALUES (%s,%s,%s,%s,%s,%s,%s)", (str(uuid.uuid4()), tenant, profile, user["email"], chain_id, body.node_id, body.sequence_order)); conn.commit()
        return {"ok": True}
    except Exception:
        conn.rollback(); raise
    finally: _state["release_db"](conn)


@router.delete("/formation-chains/{chain_id}/nodes/{node_id}")
def remove_chain_node(chain_id: str, node_id: str, request: Request) -> dict:
    user = _user(request); conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"]); cur.execute("DELETE FROM formation_twin_chain_nodes WHERE chain_id=%s AND node_id=%s AND email=%s RETURNING id", (chain_id, node_id, user["email"])); found = cur.fetchone(); cur.execute("UPDATE formation_twin_formation_edges edge SET deleted_at=now(),processing_status='DELETED' FROM formation_twin_chain_edges link WHERE link.edge_id=edge.id AND link.chain_id=%s AND link.email=%s AND (edge.source_node_id=%s OR edge.target_node_id=%s)", (chain_id, user["email"], node_id, node_id)); cur.execute("DELETE FROM formation_twin_chain_edges link USING formation_twin_formation_edges edge WHERE link.edge_id=edge.id AND link.chain_id=%s AND link.email=%s AND edge.deleted_at IS NOT NULL", (chain_id, user["email"])); conn.commit()
        if not found: raise HTTPException(status_code=404, detail="Chain node not found")
        return {"ok": True}
    finally: _state["release_db"](conn)


@router.post("/formation-chains/{chain_id}/edges")
def add_chain_edge(chain_id: str, request: Request, body: EdgeBody) -> dict:
    user = _user(request); tenant, profile = _identity(user["email"]); conn = _state["get_db"](); edge_id = str(uuid.uuid4())
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"]); cur.execute("SELECT node_id::text FROM formation_twin_chain_nodes WHERE chain_id=%s AND email=%s", (chain_id, user["email"])); ids = {row[0] for row in cur.fetchall()}
            if body.source_node_id not in ids or body.target_node_id not in ids: raise HTTPException(status_code=422, detail="Both nodes must belong to this chain")
            cur.execute("INSERT INTO formation_twin_formation_edges (id,tenant_id,profile_id,email,source_node_id,target_node_id,relation_type,source_kind,statement_type,user_review_status) VALUES (%s,%s,%s,%s,%s,%s,%s,'USER_REPORT','USER_REPORTED_FACT','NOT_REQUIRED')", (edge_id, tenant, profile, user["email"], body.source_node_id, body.target_node_id, body.relation_type))
            cur.execute("INSERT INTO formation_twin_chain_edges (id,tenant_id,profile_id,email,chain_id,edge_id,sequence_order) VALUES (%s,%s,%s,%s,%s,%s,%s)", (str(uuid.uuid4()), tenant, profile, user["email"], chain_id, edge_id, body.sequence_order)); conn.commit()
        return {"ok": True, "edge_id": edge_id}
    except Exception:
        conn.rollback(); raise
    finally: _state["release_db"](conn)


@router.delete("/formation-chains/{chain_id}/edges/{edge_id}")
def remove_chain_edge(chain_id: str, edge_id: str, request: Request) -> dict:
    user = _user(request); conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"]); cur.execute("DELETE FROM formation_twin_chain_edges WHERE chain_id=%s AND edge_id=%s AND email=%s RETURNING id", (chain_id, edge_id, user["email"])); found = cur.fetchone(); cur.execute("UPDATE formation_twin_formation_edges SET deleted_at=now(),processing_status='DELETED' WHERE id=%s AND email=%s", (edge_id, user["email"])); conn.commit()
        if not found: raise HTTPException(status_code=404, detail="Chain edge not found")
        return {"ok": True}
    finally: _state["release_db"](conn)


@router.post("/formation-chains/{chain_id}/duplicate-alternative")
def duplicate_alternative(chain_id: str, request: Request) -> dict:
    chain = get_chain(chain_id, request)["chain"]
    body = ChainBody(title=f"{chain['title']}（另一种可能）", life_event_id=chain["life_event_id"], scope=chain["scope"], node_ids=[item["id"] for item in chain["nodes"]])
    user = _user(request); conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"]); new_id = _insert_chain(cur, email=user["email"], body=body, creation_method="USER_CREATED", alternative_of=chain_id); conn.commit()
        return {"ok": True, "chain_id": new_id, "alternative_of_chain_id": chain_id}
    finally: _state["release_db"](conn)


def _chain_status(chain_id: str, request: Request, status: str, *, deleted: bool = False, excluded: bool | None = None) -> dict:
    user = _user(request); conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"]); cur.execute("UPDATE formation_twin_formation_chains SET user_review_status=%s,processing_status=%s,deleted_at=CASE WHEN %s THEN now() ELSE deleted_at END,excluded_from_context=COALESCE(%s,excluded_from_context),updated_at=now() WHERE id=%s AND email=%s AND deleted_at IS NULL RETURNING id", (status, status, deleted, excluded, chain_id, user["email"])); found = cur.fetchone()
            if found and deleted:
                cur.execute("UPDATE formation_twin_formation_edges edge SET deleted_at=now(),processing_status='DELETED' FROM formation_twin_chain_edges link WHERE link.edge_id=edge.id AND link.chain_id=%s AND link.email=%s", (chain_id, user["email"]))
            _invalidate_snapshots(cur, user["email"]); conn.commit()
        if not found: raise HTTPException(status_code=404, detail="Formation chain not found")
        return {"ok": True, "status": status}
    finally: _state["release_db"](conn)


@router.post("/formation-chains/{chain_id}/confirm")
def confirm_chain(chain_id: str, request: Request) -> dict: return _chain_status(chain_id, request, "CONFIRMED")
@router.post("/formation-chains/{chain_id}/reject")
def reject_chain(chain_id: str, request: Request) -> dict: return _chain_status(chain_id, request, "REJECTED", excluded=True)
@router.post("/formation-chains/{chain_id}/exclude")
def exclude_chain(chain_id: str, request: Request) -> dict: return _chain_status(chain_id, request, "EXCLUDED", excluded=True)


def _invalidate_snapshots(cur, email: str) -> None:
    cur.execute("UPDATE formation_twin_formation_snapshots SET superseded_at=now() WHERE email=%s AND superseded_at IS NULL", (email,))


def _read_sensitive_for_model(cur, email: str, content_id: str) -> str:
    cur.execute("SELECT encryption_key_version,nonce,encrypted_content,content_hash FROM formation_twin_sensitive_contents WHERE id=%s AND email=%s AND deleted_at IS NULL AND processing_preference='ALLOW_FUTURE_ANALYSIS'", (content_id, email)); row = cur.fetchone()
    if not row: return ""
    envelope = EncryptedContent(key_version=row[0], nonce=bytes(row[1]), ciphertext=bytes(row[2]), sha256=row[3])
    return decrypt_text(envelope, associated_data=f"{email}:{content_id}".encode())


def _save_snapshot(cur, email: str, snapshot_type: str, payload: dict) -> str:
    tenant, profile = _identity(email)
    cur.execute("SELECT COALESCE(MAX(version),0)+1 FROM formation_twin_formation_snapshots WHERE email=%s AND snapshot_type=%s", (email, snapshot_type)); version = cur.fetchone()[0]
    _invalidate_snapshots_for_type(cur, email, snapshot_type); snapshot_id = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO formation_twin_formation_snapshots (id,tenant_id,profile_id,email,snapshot_type,window_start,window_end,data_status,user_reported_json,observed_relations_json,confirmed_patterns_json,pending_hypotheses_json,grace_recovery_json,directions_json,tensions_json,reflective_questions_json,limitations_json,coverage_json,version,engine_version,input_hash) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (email,snapshot_type,input_hash) DO UPDATE SET superseded_at=NULL RETURNING id",
        (snapshot_id, tenant, profile, email, snapshot_type, payload["window_start"], payload["window_end"], payload["data_status"], Json(payload["user_reported_items"]), Json(payload["observed_relations"]), Json(payload["confirmed_patterns"]), Json(payload["pending_hypotheses"]), Json(payload["grace_and_recovery"]), Json(payload["formation_directions"]), Json(payload["tensions"]), Json(payload["reflective_questions"]), Json(payload["limitations"]), Json(payload["record_coverage"]), version, ENGINE_VERSION, payload["input_hash"]),
    )
    return str(cur.fetchone()[0])


def _invalidate_snapshots_for_type(cur, email: str, snapshot_type: str) -> None:
    cur.execute("UPDATE formation_twin_formation_snapshots SET superseded_at=now() WHERE email=%s AND snapshot_type=%s AND superseded_at IS NULL", (email, snapshot_type))


@router.post("/formation-state/rebuild")
def rebuild_formation_state(request: Request) -> dict:
    user = _user(request); email = user["email"]; conn = _state["get_db"](); now = datetime.now(timezone.utc)
    try:
        with conn.cursor() as cur:
            _owner(cur, email); settings = _settings(cur, email)
            if not settings.get("spiritual_engine_enabled"):
                conn.commit(); return {"ok": True, "status": "DISABLED", "events_considered": 0}
            _delete_generated_special_records(cur, email=email)
            cur.execute("UPDATE formation_twin_formation_nodes SET deleted_at=now(),processing_status='SUPERSEDED' WHERE email=%s AND source_kind IN ('OBSERVATION','RULE','MODEL') AND deleted_at IS NULL", (email,))
            cur.execute("UPDATE formation_twin_formation_chains SET deleted_at=now(),processing_status='SUPERSEDED' WHERE email=%s AND creation_method='RULE_ASSEMBLED' AND deleted_at IS NULL", (email,))
            cur.execute(
                "SELECT id,event_type,event_subtype,occurred_at,self_report_json,behavioral_facts_json,spiritual_practice_facts_json,content_reference_id,safety_json,status "
                "FROM formation_twin_life_events WHERE email=%s AND deleted_at IS NULL AND exclude_from_twin_processing=FALSE AND status='ACCEPTED' AND processing_preference='ALLOW_FUTURE_ANALYSIS' ORDER BY occurred_at",
                (email,),
            ); events = cur.fetchall(); nodes_created = 0; chains_created = 0; candidates_created = 0; blocked_crisis = 0
            for event in events:
                event_id = str(event[0])
                if crisis_blocks_formation(event[8] or {}, event[9]):
                    blocked_crisis += 1; continue
                event_node_id = _insert_node(cur, email=email, body={"node_type": "LIFE_EVENT", "content": EVENT_LABELS.get(event[1], "记录到一次经授权的生命事件"), "scope": "THIS_EVENT_ONLY", "life_event_id": event_id, "occurred_at": event[3]}, source_kind="OBSERVATION", statement_type="OBSERVED_EVENT", review_status="NOT_REQUIRED")
                nodes_created += 1; related_ids: list[str] = []
                cur.execute("SELECT id,emotion_label,custom_label,intensity,source_kind,statement_type,user_review_status FROM formation_twin_emotion_observations WHERE email=%s AND life_event_id=%s AND deleted_at IS NULL AND processing_status='ACTIVE' AND source_kind IN ('USER_REPORT','USER_CONFIRMED')", (email, event_id))
                for emotion in cur.fetchall():
                    label = emotion[2] or emotion[1]; content = f"用户记录的情绪：{label}" + (f"（强度 {emotion[3]}/10）" if emotion[3] is not None else "")
                    source_kind = "USER_CONFIRMED" if emotion[4] == "USER_CONFIRMED" else "USER_REPORT"
                    statement_type = "USER_CONFIRMED_FORMATION_PATTERN" if source_kind == "USER_CONFIRMED" else "USER_REPORTED_FACT"
                    node_id = _insert_node(cur, email=email, body={"node_type": "EMOTION", "content": content, "scope": "THIS_EVENT_ONLY", "life_event_id": event_id, "occurred_at": event[3]}, source_kind=source_kind, statement_type=statement_type, review_status="NOT_REQUIRED", emotion_observation_id=str(emotion[0]))
                    related_ids.append(node_id); nodes_created += 1
                if event[5]:
                    related_ids.append(_insert_node(cur, email=email, body={"node_type": "BEHAVIOR", "content": "记录到经授权的行为事实", "scope": "THIS_EVENT_ONLY", "life_event_id": event_id, "occurred_at": event[3]}, source_kind="OBSERVATION", statement_type="OBSERVED_EVENT", review_status="NOT_REQUIRED")); nodes_created += 1
                if event[6]:
                    related_ids.append(_insert_node(cur, email=email, body={"node_type": "SPIRITUAL_PRACTICE", "content": "记录到经授权的属灵操练事实", "scope": "THIS_EVENT_ONLY", "life_event_id": event_id, "occurred_at": event[3]}, source_kind="OBSERVATION", statement_type="OBSERVED_EVENT", review_status="NOT_REQUIRED")); nodes_created += 1
                model_allowed = settings.get("belief_hypothesis_enabled") and settings.get("provider_policy") == "CONFIGURED_PROVIDER" and os.getenv("FORMATION_TWIN_BELIEF_HYPOTHESIS_ENABLED", "false").lower() == "true"
                if model_allowed and event[7]:
                    text = _read_sensitive_for_model(cur, email, str(event[7]))
                    if text:
                        try:
                            from theological_safety import detect_crisis
                            risk = detect_crisis(text).get("risk_level", "low")
                        except Exception:
                            risk = "low"
                        if risk in {"high", "critical"}:
                            blocked_crisis += 1
                        else:
                            candidates, run = infer_formation_candidates(text)
                            tenant, profile = _identity(email); request_id = str(uuid.uuid4())
                            cur.execute("INSERT INTO formation_twin_formation_model_runs (id,tenant_id,profile_id,email,request_id,provider,model_name,prompt_version,schema_version,result_status,candidate_count) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (str(uuid.uuid4()), tenant, profile, email, request_id, "configured", os.getenv("LLM_MODEL"), run.get("prompt_version"), run.get("schema_version"), run["status"], len(candidates)))
                            for candidate in candidates:
                                node_id = _insert_node(cur, email=email, body={"node_type": candidate["node_type"], "content": candidate["content"], "scope": candidate["scope"], "life_event_id": event_id, "occurred_at": event[3]}, source_kind="MODEL", statement_type=candidate["statement_type"], review_status="PENDING", confidence=candidate["confidence"], evidence=candidate["evidence"], alternatives=candidate["alternatives"], model_meta={"model_version": os.getenv("LLM_MODEL", "configured-provider"), "prompt_version": run.get("prompt_version"), "schema_version": run.get("schema_version")}, expires_at=candidate["expires_at"])
                                related_ids.append(node_id); candidates_created += 1; nodes_created += 1
                if settings.get("formation_chain_enabled") and related_ids:
                    chain_body = ChainBody(title=EVENT_LABELS.get(event[1], "生命事件形成链"), life_event_id=event_id, node_ids=[event_node_id, *related_ids])
                    chain_id = _insert_chain(cur, email=email, body=chain_body, creation_method="RULE_ASSEMBLED")
                    tenant, profile = _identity(email)
                    for order, (left, right) in enumerate(zip([event_node_id, *related_ids], related_ids)):
                        edge_id = str(uuid.uuid4()); cur.execute("INSERT INTO formation_twin_formation_edges (id,tenant_id,profile_id,email,source_node_id,target_node_id,relation_type,source_kind,statement_type,user_review_status,rule_version) VALUES (%s,%s,%s,%s,%s,%s,'OBSERVED_IN_SAME_EVENT','RULE','RULE_DERIVED_RELATION','NOT_REQUIRED','formation-chain-rules-1.0')", (edge_id, tenant, profile, email, left, right)); cur.execute("INSERT INTO formation_twin_chain_edges (id,tenant_id,profile_id,email,chain_id,edge_id,sequence_order) VALUES (%s,%s,%s,%s,%s,%s,%s)", (str(uuid.uuid4()), tenant, profile, email, chain_id, edge_id, order))
                    chains_created += 1
            all_nodes = _node_rows(cur, email, where="AND processing_status='ACTIVE'")
            all_chains = _chain_rows(cur, email)
            snapshots = {}
            for _, (snapshot_type, delta) in SNAPSHOT_KINDS.items():
                payload = build_formation_snapshot(nodes=all_nodes, chains=all_chains, window_start=now-delta, window_end=now)
                snapshots[snapshot_type] = _save_snapshot(cur, email, snapshot_type, payload)
            _publish(cur, email, "formation_twin.formation_state_updated", {"snapshot_id": snapshots["CURRENT_FORMATION_STATE"], "engine_version": ENGINE_VERSION}); conn.commit()
        return {"ok": True, "status": "REBUILT", "events_considered": len(events), "crisis_records_blocked": blocked_crisis, "nodes_created": nodes_created, "chains_created": chains_created, "candidates_created": candidates_created, "snapshots": snapshots}
    except Exception:
        conn.rollback(); raise
    finally: _state["release_db"](conn)


def _snapshot_response(request: Request, kind: str) -> dict:
    snapshot_type, _ = SNAPSHOT_KINDS[kind]; user = _user(request); conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"]); cur.execute("SELECT id,window_start,window_end,data_status,user_reported_json,observed_relations_json,confirmed_patterns_json,pending_hypotheses_json,grace_recovery_json,directions_json,tensions_json,reflective_questions_json,limitations_json,coverage_json,version,engine_version,created_at FROM formation_twin_formation_snapshots WHERE email=%s AND snapshot_type=%s AND superseded_at IS NULL ORDER BY created_at DESC LIMIT 1", (user["email"], snapshot_type)); row = cur.fetchone()
        if not row: return {"ok": True, "snapshot": {"snapshot_type": snapshot_type, "data_status": "INSUFFICIENT_DATA", "limitations": ["请先授权至少一条生命事件参与处理，然后重建形成状态。"]}}
        keys = ["id", "window_start", "window_end", "data_status", "user_reported_items", "observed_relations", "confirmed_patterns", "pending_hypotheses", "grace_and_recovery", "formation_directions", "tensions", "reflective_questions", "limitations", "record_coverage", "version", "engine_version", "created_at"]
        payload = dict(zip(keys, row)); payload["snapshot_type"] = snapshot_type
        for key in ("id",): payload[key] = str(payload[key])
        for key in ("window_start", "window_end", "created_at"): payload[key] = payload[key].isoformat()
        return {"ok": True, "snapshot": payload}
    finally: _state["release_db"](conn)


@router.get("/formation-state/current")
def current_formation_state(request: Request) -> dict: return _snapshot_response(request, "current")
@router.get("/formation-state/daily")
def daily_formation_state(request: Request) -> dict: return _snapshot_response(request, "daily")
@router.get("/formation-state/weekly")
def weekly_formation_state(request: Request) -> dict: return _snapshot_response(request, "weekly")


@router.get("/formation-context/{target}")
def get_formation_context(target: Literal["formation", "prayer", "habit", "attention"], request: Request) -> dict:
    user = _user(request); response = _snapshot_response(request, "current"); snapshot = response["snapshot"]
    if snapshot.get("data_status") == "INSUFFICIENT_DATA": return {"ok": True, "available": False, "reason": "INSUFFICIENT_DATA", "target": target}
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"]); settings = _settings(cur, user["email"]); conn.commit()
        consent = bool(settings.get(f"{target}_context_consent"))
        return {"ok": True, **context_envelope(snapshot, target, consent=consent)}
    finally: _state["release_db"](conn)


@router.get("/formation-graph/status")
def get_graph_status(request: Request) -> dict:
    user = _user(request); conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"]); settings = _settings(cur, user["email"]); conn.commit()
        environment = graph_status()
        return {"ok": True, **environment, "profile_enabled": bool(settings.get("graph_enabled")), "effective_status": environment["status"] if settings.get("graph_enabled") else "DISABLED_BY_PROFILE", "privacy": "IDs, types, review state, and content hashes only"}
    finally:
        _state["release_db"](conn)


@router.post("/formation-chains/{chain_id}/sync-graph")
def sync_chain_graph(chain_id: str, request: Request) -> dict:
    chain = get_chain(chain_id, request)["chain"]
    if chain["user_review_status"] != "CONFIRMED": raise HTTPException(status_code=409, detail="Only user-confirmed chains can be synced")
    user = _user(request); tenant, profile = _identity(user["email"]); conn = _state["get_db"]()
    with conn.cursor() as cur:
        _owner(cur, user["email"]); settings = _settings(cur, user["email"]); conn.commit()
    if not settings.get("graph_enabled"):
        _state["release_db"](conn)
        return {"ok": True, "status": "DISABLED", "nodes": 0, "edges": 0}
    result = sync_reviewed_chain(tenant_id=tenant, profile_id=profile, chain_id=chain_id, nodes=chain["nodes"], edges=chain["edges"])
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"]); cur.execute("INSERT INTO formation_twin_graph_syncs (id,tenant_id,profile_id,email,chain_id,sync_status,node_count,edge_count,error_code) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", (str(uuid.uuid4()), tenant, profile, user["email"], chain_id, result["status"], result.get("nodes", 0), result.get("edges", 0), None if result["status"] in {"SYNCED", "DISABLED"} else result["status"])); conn.commit()
        return {"ok": result["status"] in {"SYNCED", "DISABLED"}, **result}
    finally: _state["release_db"](conn)


@router.get("/formation-state/data-quality")
def formation_data_quality(request: Request) -> dict:
    user = _user(request); conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"]); cur.execute("SELECT COUNT(*) FILTER (WHERE source_kind='MODEL' AND (confidence IS NULL OR evidence_json='[]'::jsonb OR user_review_status NOT IN ('PENDING','CONFIRMED','PARTIALLY_CONFIRMED','REJECTED','RELABELED','SCOPE_CHANGED','DISMISSED'))),COUNT(*) FILTER (WHERE source_kind='MODEL' AND statement_type='MODEL_FORMATION_HYPOTHESIS' AND node_type IN %s AND alternatives_json='[]'::jsonb),COUNT(*) FILTER (WHERE source_kind='USER_REPORT' AND confidence IS NOT NULL),COUNT(*) FILTER (WHERE statement_type='USER_CONFIRMED_FORMATION_PATTERN' AND source_kind<>'USER_CONFIRMED') FROM formation_twin_formation_nodes WHERE email=%s AND deleted_at IS NULL", (tuple(DEEP_FORMATION_TYPES), user["email"])); row = cur.fetchone(); cur.execute("SELECT COUNT(*) FROM formation_twin_formation_edges WHERE email=%s AND relation_type IN ('CAUSED','PROVED','DETERMINED') AND deleted_at IS NULL", (user["email"],)); unsafe_edges = cur.fetchone()[0]
        issues = {"model_missing_provenance": row[0], "deep_hypothesis_missing_alternatives": row[1], "user_report_with_confidence": row[2], "confirmed_source_mismatch": row[3], "forbidden_causal_edges": unsafe_edges}
        return {"ok": True, "quality_passed": sum(issues.values()) == 0, "issues": issues}
    finally: _state["release_db"](conn)


def _category_endpoint(node_type: str):
    def endpoint(request: Request):
        return list_nodes(request, node_type=node_type, limit=200)
    return endpoint


for _path, _node_type in {
    "identity-statements": "IDENTITY_STATEMENT", "belief-statements": "BELIEF_STATEMENT",
    "desires": "DESIRE", "fears": "FEAR", "temptations": "TEMPTATION",
    "grace-evidence": "GRACE_EVIDENCE",
}.items():
    _endpoint = _category_endpoint(_node_type); _endpoint.__name__ = f"list_{_path.replace('-', '_')}"; router.get(f"/{_path}")(_endpoint)

_grace_factors_endpoint = _category_endpoint("GRACE_EVIDENCE")
_grace_factors_endpoint.__name__ = "list_grace_factors"
router.get("/grace-factors")(_grace_factors_endpoint)
