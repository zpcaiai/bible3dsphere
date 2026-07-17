"""Fail-closed registry and contract quality scan."""
from __future__ import annotations

from typing import Any

from .contracts import FORBIDDEN_PLATFORM_FIELDS, FORBIDDEN_KEY_RE
from .registry import AGENT_CAPABILITIES, EVENT_SCHEMAS, PROJECTIONS, PURPOSE_POLICIES


def scan_platform_contracts() -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    for event_type, schema in EVENT_SCHEMAS.items():
        if not schema.get("version") or not schema.get("schema_uri"):
            issues.append({"severity": "HIGH", "code": "EVENT_VERSION_MISSING", "subject": event_type})
        for field in schema.get("allowed_payload_fields", []):
            if field.lower() in FORBIDDEN_PLATFORM_FIELDS or FORBIDDEN_KEY_RE.search(field):
                issues.append({"severity": "HIGH", "code": "EVENT_FIELD_FORBIDDEN", "subject": event_type})
    for name, projection in PROJECTIONS.items():
        if not projection.get("version"):
            issues.append({"severity": "HIGH", "code": "PROJECTION_VERSION_MISSING", "subject": name})
        if not 30 <= int(projection.get("ttl", 0)) <= 900:
            issues.append({"severity": "HIGH", "code": "PROJECTION_TTL_INVALID", "subject": name})
        if len(projection.get("fields", [])) > 8:
            issues.append({"severity": "MEDIUM", "code": "PROJECTION_TOO_BROAD", "subject": name})
    for purpose, policy in PURPOSE_POLICIES.items():
        if not policy["projections"].issubset(PROJECTIONS):
            issues.append({"severity": "HIGH", "code": "PURPOSE_PROJECTION_MISSING", "subject": purpose})
    ids = [agent.agent_id for agent in AGENT_CAPABILITIES]
    if len(ids) != len(set(ids)):
        issues.append({"severity": "HIGH", "code": "DUPLICATE_ACTIVE_AGENT", "subject": "agent_registry"})
    high = [issue for issue in issues if issue["severity"] == "HIGH"]
    return {"ok": not high, "high_severity_count": len(high), "issue_count": len(issues), "issues": issues}
