"""OpenTelemetry-compatible, privacy-safe attribute helper."""
from __future__ import annotations

from typing import Any


ALLOWED_TRACE_ATTRIBUTES = {
    "correlation_id", "causation_id", "trace_id", "module", "workflow", "result", "redacted_reason_code",
}
FORBIDDEN_LABELS = {
    "user_id", "email", "emotion", "temptation_type", "crisis_type", "journal_title",
    "church_name", "sensitive_pattern", "search_query",
}


def safe_trace_attributes(attributes: dict[str, Any]) -> dict[str, str]:
    if set(attributes) & FORBIDDEN_LABELS:
        raise ValueError("sensitive observability labels are forbidden")
    return {key: str(value)[:160] for key, value in attributes.items() if key in ALLOWED_TRACE_ATTRIBUTES and value is not None}
