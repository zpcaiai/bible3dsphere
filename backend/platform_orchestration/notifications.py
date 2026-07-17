"""Privacy-safe notification coalescing."""
from __future__ import annotations

from datetime import datetime
from typing import Any


def coordinate_notifications(candidates: list[dict[str, Any]], *, quiet_hours: bool = False) -> dict[str, Any]:
    valid = [item for item in candidates if not item.get("disabled")]
    crisis = [item for item in valid if item.get("urgency") == "IMMEDIATE" and item.get("source_module") == "crisis"]
    if crisis:
        item = crisis[0]
        return {"deliver": True, "title": "请先关注当前安全", "body": "打开应用查看安全支持与真人连接选项。", "source_modules": ["crisis"], "reason_codes": ["CRISIS_PRIORITY", "SENSITIVE_CONTENT_REDACTED"]}
    if quiet_hours:
        return {"deliver": False, "title": None, "body": None, "source_modules": [], "reason_codes": ["QUIET_HOURS"]}
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in valid:
        groups.setdefault(item.get("grouping_key") or item.get("notification_type", "general"), []).append(item)
    sources = sorted({item.get("source_module", "unknown") for item in valid})
    if not valid:
        return {"deliver": False, "title": None, "body": None, "source_modules": [], "reason_codes": ["NO_CANDIDATES"]}
    if len(valid) > 1:
        return {"deliver": True, "title": "今晚有几项可选提醒", "body": f"应用内有 {len(valid)} 项可选内容，按你的容量选择一项即可。", "source_modules": sources, "reason_codes": ["ORDINARY_NOTIFICATIONS_BATCHED", "SENSITIVE_CONTENT_REDACTED"]}
    item = valid[0]
    sensitive = item.get("sensitivity") in {"SENSITIVE", "HIGHLY_SENSITIVE"}
    return {"deliver": True, "title": "有一项可选提醒" if sensitive else str(item.get("title", "可选提醒"))[:80], "body": "打开应用查看详情。" if sensitive else str(item.get("body", ""))[:160], "source_modules": sources, "reason_codes": ["SENSITIVE_CONTENT_REDACTED"] if sensitive else ["SINGLE_NOTIFICATION"]}
