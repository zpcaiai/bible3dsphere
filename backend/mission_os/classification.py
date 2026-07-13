"""Skill 11: field-level sensitivity classification (P0-P4) and field authorization.

Pure-python invariants; no database or framework coupling. The registry keeps
public / research / sensitive views separated so P3/P4 data never leaks into a
public DTO or a general AI model.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone

# Ordered least -> most sensitive. Matches the geographic precision ladder in the
# Mission OS spec (P0 public country/region ... P4 exact address / sensitive contact).
LEVELS = ("P0", "P1", "P2", "P3", "P4")
_RANK = {lvl: i for i, lvl in enumerate(LEVELS)}

# DTO shapes and the maximum sensitivity each may ever contain.
DTO_MAX = {"public": "P1", "research": "P2", "internal": "P3", "sensitive": "P4"}

# Access scopes and the maximum sensitivity they may see without an explicit grant.
SCOPE_MAX = {
    "public": "P1",
    "researcher": "P2",
    "reviewer": "P3",
    "safeguarding": "P4",
    "ai_model": "P2",  # general AI models never receive P3/P4 without redaction+approval
}

# Redaction sentinel written in place of a field the viewer may not see.
REDACTED = "[REDACTED]"

# Default field classifications keyed by (resource_type, field_name). Callers may
# override per-tenant via the mission_field_classifications table.
DEFAULT_CLASSIFICATIONS = {
    ("mission_field", "sensitive_geometry_reference"): "P4",
    ("mission_field", "public_geometry"): "P1",
    ("local_partner", "encrypted_contact_reference"): "P4",
    ("local_church", "sensitive_location_reference"): "P4",
    ("worker_profile", "family_stage_summary"): "P3",
    ("worker_profile", "health_constraints"): "P3",
    ("calling_journey", "spouse_feedback"): "P4",
    ("incident", "narrative"): "P4",
}
# Field-name substrings that are inherently high sensitivity regardless of resource.
_HIGH_SENSITIVITY_HINTS = {
    "exact_location": "P4", "precise_location": "P4", "passport": "P4",
    "local_contact": "P4", "contact_reference": "P4", "spouse_feedback": "P4",
    "mental_health": "P4", "home_address": "P4",
    "family": "P3", "health": "P3", "financial_detail": "P3",
}


def normalize_level(level: str) -> str:
    if level not in _RANK:
        raise ValueError(f"invalid sensitivity level: {level!r}")
    return level


def at_most(level: str, ceiling: str) -> bool:
    """True when *level* is no more sensitive than *ceiling*."""
    return _RANK[normalize_level(level)] <= _RANK[normalize_level(ceiling)]


def classify_field(resource_type: str, field_name: str, *, overrides: dict | None = None) -> str:
    """Resolve the sensitivity level for a field. Fail closed to P3 when unknown."""
    if overrides:
        key = (resource_type, field_name)
        if key in overrides:
            return normalize_level(overrides[key])
    key = (resource_type, field_name)
    if key in DEFAULT_CLASSIFICATIONS:
        return DEFAULT_CLASSIFICATIONS[key]
    low = field_name.lower()
    for hint, lvl in _HIGH_SENSITIVITY_HINTS.items():
        if hint in low:
            return lvl
    # Unknown fields default to P2 (research) — never assumed public.
    return "P2"


def scope_ceiling(access_scope: str, *, grant_level: str | None = None) -> str:
    """Highest sensitivity an access scope may see, optionally raised by a grant."""
    base = SCOPE_MAX.get(access_scope, "P0")
    if grant_level and _RANK[normalize_level(grant_level)] > _RANK[base]:
        return normalize_level(grant_level)
    return base


def redact_record(record: dict, resource_type: str, *, ceiling: str,
                  overrides: dict | None = None) -> tuple[dict, list[str]]:
    """Return a copy of *record* with fields above *ceiling* redacted.

    Also returns the sorted list of redacted field names so the caller can audit
    what was withheld without recording the values themselves.
    """
    normalize_level(ceiling)
    out, redacted = {}, []
    for field_name, value in record.items():
        level = classify_field(resource_type, field_name, overrides=overrides)
        if at_most(level, ceiling):
            out[field_name] = value
        else:
            out[field_name] = REDACTED
            redacted.append(field_name)
    return out, sorted(redacted)


def assert_dto_safe(dto_kind: str, resource_type: str, field_names, *, overrides: dict | None = None) -> None:
    """Raise when a DTO would carry a field above its allowed sensitivity ceiling.

    Guards the hard rule: public/research DTOs never contain P3/P4 data.
    """
    if dto_kind not in DTO_MAX:
        raise ValueError(f"unknown dto kind: {dto_kind!r}")
    ceiling = DTO_MAX[dto_kind]
    for field_name in field_names:
        level = classify_field(resource_type, field_name, overrides=overrides)
        if not at_most(level, ceiling):
            raise ValueError(
                f"{dto_kind} DTO for {resource_type} cannot expose {field_name} ({level} > {ceiling})"
            )


def ai_input_allowed(resource_type: str, field_names, *, overrides: dict | None = None) -> None:
    """Raise when any field exceeds the AI model ceiling (P2). P3/P4 never enter models raw."""
    for field_name in field_names:
        level = classify_field(resource_type, field_name, overrides=overrides)
        if not at_most(level, SCOPE_MAX["ai_model"]):
            raise ValueError(f"field {field_name} ({level}) may not enter a general AI model")


@dataclass(frozen=True)
class FieldAccessGrant:
    """A time-boxed field-level authorization above a scope's default ceiling."""
    subject_type: str
    subject_id: str
    resource_type: str
    field_name: str
    max_sensitivity: str
    expires_at: datetime | None = None
    revoked_at: datetime | None = None

    def is_active(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        if self.revoked_at is not None:
            return False
        if self.expires_at is not None:
            if self.expires_at.tzinfo is None:
                return False
            return self.expires_at > now
        return True

    def effective_level(self, now: datetime | None = None) -> str | None:
        return normalize_level(self.max_sensitivity) if self.is_active(now) else None
