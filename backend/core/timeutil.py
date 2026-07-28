"""ISO 8601 parsing that behaves the same on every supported Python.

`datetime.fromisoformat` only learned to accept a trailing `Z` in Python 3.11.
That matters here because the API *emits* `Z`: Pydantic v2's `model_dump(mode="json")`
renders an aware UTC datetime as `2026-07-28T08:32:29.304396Z`. So a payload this
service produced can fail to parse in this same service — but only on Python 3.10,
which is exactly the kind of defect that survives CI (pinned to 3.11) and surfaces
on whichever box happens to run an older interpreter.

Most call sites had already worked around it with `.replace("Z", "+00:00")`; a handful
had not, and the two groups disagreed about whether `Z` was acceptable input. This
module makes that one decision in one place.

    parse_iso8601("2026-07-28T08:32:29Z")        -> aware datetime (UTC)
    parse_iso8601("2026-07-28T08:32:29+08:00")   -> aware datetime (+08:00)
    parse_iso8601("2026-07-28T08:32:29")         -> aware datetime, assumed UTC
    parse_iso8601_date("2026-07-28T08:32:29Z")   -> date
"""
from __future__ import annotations

from datetime import date, datetime, timezone


__all__ = ["parse_iso8601", "parse_iso8601_date", "to_iso8601", "ensure_aware"]


def _normalise(value: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError("empty timestamp")
    # 兼容 Z / z 后缀；Python 3.11 之前 fromisoformat 不接受。
    if text.endswith(("Z", "z")):
        text = f"{text[:-1]}+00:00"
    return text


def ensure_aware(moment: datetime, *, assume: timezone = timezone.utc) -> datetime:
    """A naive datetime is treated as UTC rather than silently compared as local time."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=assume)
    return moment


def parse_iso8601(value: str | datetime) -> datetime:
    """Parse an ISO 8601 timestamp into an aware datetime.

    Raises `ValueError` on anything unparseable — callers that face user input should
    catch it and return 4xx rather than letting it become a 500.
    """
    if isinstance(value, datetime):
        return ensure_aware(value)
    return ensure_aware(datetime.fromisoformat(_normalise(str(value))))


def parse_iso8601_date(value: str | datetime | date) -> date:
    """Parse a date, accepting either a bare date or a full timestamp."""
    if isinstance(value, datetime):
        return ensure_aware(value).date()
    if isinstance(value, date):
        return value
    text = _normalise(str(value))
    try:
        return date.fromisoformat(text)
    except ValueError:
        return ensure_aware(datetime.fromisoformat(text)).date()


def to_iso8601(moment: datetime) -> str:
    """Serialise with an explicit offset, never a bare naive timestamp."""
    return ensure_aware(moment).isoformat()
