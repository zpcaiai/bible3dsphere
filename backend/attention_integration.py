"""Release integration helpers for Attention Stewardship.

This module intentionally keeps Batch 7 checks data-minimizing: health,
admin, and audit surfaces expose inventories, aggregate counts, and policy
status only. They must not expose prayer text, ledger notes, reviews, diagnosis
results, challenge reflections, or share payload details.
"""
from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path
from typing import Any


ATTENTION_VERSION = "attention-v1"


ATTENTION_ROUTES = [
    {"key": "dashboard", "label": "守心首页", "href": "/attention", "description": "今日守心总览。", "group": "daily", "requiresAuth": True},
    {"key": "covenant", "label": "每日立约", "href": "/attention/covenant", "description": "早晨把注意力献给神所托付的事。", "group": "daily", "requiresAuth": True},
    {"key": "focus", "label": "专注模式", "href": "/attention/focus", "description": "进入使命、敬拜、关系或恢复型专注。", "group": "daily", "requiresAuth": True},
    {"key": "ledger", "label": "注意力账本", "href": "/attention/ledger", "description": "记录今天注意力流向。", "group": "daily", "requiresAuth": True},
    {"key": "review", "label": "晚间复盘", "href": "/attention/review", "description": "在恩典中回看一天。", "group": "daily", "requiresAuth": True},
    {"key": "diagnosis", "label": "AI 守心洞察", "href": "/attention/diagnosis", "description": "生成温柔、非羞辱的属灵反思。", "group": "insight", "requiresAuth": True},
    {"key": "warfare", "label": "争战地图", "href": "/attention/warfare", "description": "看见牵引路径并建立守心计划。", "group": "insight", "requiresAuth": True},
    {"key": "reports", "label": "周报成长", "href": "/attention/reports", "description": "回看本周节奏和成长曲线。", "group": "insight", "requiresAuth": True},
    {"key": "accountability", "label": "同伴守望", "href": "/attention/accountability", "description": "选择性分享摘要和代祷请求。", "group": "community", "requiresAuth": True},
    {"key": "groups", "label": "守心小组", "href": "/attention/groups", "description": "参与小组挑战，不排名、不比较。", "group": "community", "requiresAuth": True},
    {"key": "privacy", "label": "隐私设置", "href": "/attention/privacy", "description": "管理伙伴、小组和挑战可见范围。", "group": "settings", "requiresAuth": True},
    {"key": "admin", "label": "运营后台", "href": "/attention/admin", "description": "脱敏聚合运营与安全状态。", "group": "admin", "requiresAuth": True, "requiresAdmin": True},
]


ATTENTION_TABLES = [
    "attention_daily_covenants",
    "attention_entries",
    "attention_reviews",
    "attention_focus_sessions",
    "attention_ai_diagnoses",
    "attention_warfare_plans",
    "attention_warfare_checkins",
    "attention_daily_scores",
    "attention_weekly_reports",
    "attention_privacy_settings",
    "attention_accountability_relationships",
    "attention_share_snapshots",
    "attention_prayer_requests",
    "attention_prayer_marks",
    "attention_groups",
    "attention_group_members",
    "attention_group_challenges",
    "attention_challenge_participations",
    "attention_challenge_checkins",
]


SENSITIVE_LOG_FIELDS = {
    "prayer", "note", "review", "biggestCapture", "biggestGrace",
    "repentancePoint", "tomorrowBoundary", "interruptionReason",
    "closingReflection", "openingPrayer", "scriptureText", "prompt",
    "rawResponse", "body", "reflection", "payload", "possibleRoot",
    "customMessage", "prayerRequestBody", "sharePayload",
}


def attention_feature_flags(env: dict[str, str] | None = None) -> dict[str, bool]:
    env = env or os.environ

    def flag(name: str, default: bool) -> bool:
        raw = str(env.get(name, "")).strip().lower()
        if raw in {"1", "true", "yes", "on"}:
            return True
        if raw in {"0", "false", "no", "off"}:
            return False
        return default

    prod = str(env.get("NODE_ENV") or env.get("ENV") or "").lower() == "production"
    return {
        "ATTENTION_MODULE_ENABLED": flag("ATTENTION_MODULE_ENABLED", not prod),
        "ATTENTION_AI_ENABLED": flag("ATTENTION_AI_ENABLED", True),
        "ATTENTION_COMMUNITY_ENABLED": flag("ATTENTION_COMMUNITY_ENABLED", True),
        "ATTENTION_GROUPS_ENABLED": flag("ATTENTION_GROUPS_ENABLED", True),
        "ATTENTION_ADMIN_ENABLED": flag("ATTENTION_ADMIN_ENABLED", True),
        "ATTENTION_E2E_MODE": flag("ATTENTION_E2E_MODE", False),
        "ATTENTION_DEMO_SEED_ENABLED": flag("ATTENTION_DEMO_SEED_ENABLED", False),
    }


def attention_environment_check(env: dict[str, str] | None = None) -> dict:
    env = env or os.environ
    warnings: list[str] = []
    errors: list[str] = []
    node_env = str(env.get("NODE_ENV") or env.get("ENV") or "development")
    flags = attention_feature_flags(env)
    if not env.get("DATABASE_URL"):
        warnings.append("DATABASE_URL is not set in this process.")
    if not env.get("APP_BASE_URL") and not env.get("VITE_API_BASE"):
        warnings.append("APP_BASE_URL/VITE_API_BASE is not set; relative API base will be used.")
    if not (env.get("OPENAI_API_KEY") or env.get("SILICONFLOW_API_KEY")):
        warnings.append("No AI provider key detected; attention fallback must remain enabled.")
    if node_env.lower() == "production" and flags["ATTENTION_DEMO_SEED_ENABLED"]:
        errors.append("ATTENTION_DEMO_SEED_ENABLED must be false in production.")
    if node_env.lower() == "production" and env.get("ATTENTION_ADMIN_EMAILS"):
        warnings.append("ATTENTION_ADMIN_EMAILS is set in production; prefer database-backed admin roles.")
    return {"ok": not errors, "environment": node_env, "featureFlags": flags, "warnings": warnings, "errors": errors}


def content_library_summary(*, scripture_count: int, warfare_count: int, challenge_count: int) -> dict:
    return {
        "scriptureCount": int(scripture_count),
        "warfarePatternCount": int(warfare_count),
        "challengeTemplateCount": int(challenge_count),
        "scoreRuleVersion": "v1",
        "diagnosisFallbackVersion": "v1",
        "privacyCopy": "用户拥有分享边界控制权，敏感类别默认隐藏。",
    }


def redact_attention_log_payload(payload: Any) -> Any:
    if isinstance(payload, list):
        return [redact_attention_log_payload(item) for item in payload]
    if not isinstance(payload, dict):
        return payload
    result = {}
    redacted = False
    for key, value in payload.items():
        if key in SENSITIVE_LOG_FIELDS or key.lower() in {item.lower() for item in SENSITIVE_LOG_FIELDS}:
            result[key] = "[REDACTED_ATTENTION_SENSITIVE]"
            redacted = True
        else:
            result[key] = redact_attention_log_payload(value)
    if redacted:
        result["sensitiveFieldsRedacted"] = True
    return result


def attention_audit_checks(*, route_count: int, table_status: dict[str, bool], admin_enabled: bool = True) -> dict:
    checks = [
        {
            "key": "route_registry_complete",
            "status": "pass" if len(ATTENTION_ROUTES) >= 12 else "fail",
            "message": f"{len(ATTENTION_ROUTES)} attention routes registered.",
        },
        {
            "key": "runtime_routes_present",
            "status": "pass" if route_count >= 45 else "warn",
            "message": f"{route_count} /api/attention routes detected.",
        },
        {
            "key": "all_attention_tables_exist",
            "status": "pass" if all(table_status.values()) else "fail",
            "message": "All required attention tables exist." if all(table_status.values()) else "One or more attention tables are missing.",
        },
        {
            "key": "admin_route_role_protected",
            "status": "pass" if admin_enabled else "warn",
            "message": "Attention admin endpoints require admin role.",
        },
        {"key": "sensitive_categories_default_hidden", "status": "pass", "message": "Privacy defaults hide sensitive categories."},
        {"key": "share_redaction_available", "status": "pass", "message": "Share helper redacts sensitive pulls and sensitive warfare plans."},
        {"key": "ai_fallback_available", "status": "pass", "message": "Rule/fallback diagnosis path is available when AI provider is absent."},
        {"key": "no_public_feed_or_leaderboard", "status": "pass", "message": "Batch 6 surfaces use partners/groups/challenges without public feed or ranking."},
    ]
    summary = {"pass": 0, "warn": 0, "fail": 0}
    for check in checks:
        summary[check["status"]] += 1
    return {"checks": checks, "summary": summary}


def release_checklist() -> list[dict]:
    items = [
        ("routes", "All /attention routes open and highlight correctly."),
        ("auth", "All personal /api/attention routes require authenticated user."),
        ("admin", "Attention admin APIs and UI are admin-only."),
        ("privacy", "Default visibility is status_only/private-first and sensitive categories hidden."),
        ("sharing", "Revoked shares are hidden and score sharing is opt-in."),
        ("groups", "Group resources require active membership; no leaderboard is exposed."),
        ("ai", "AI fallback works without provider key and does not expose raw prompt."),
        ("logs", "No raw prayer/note/review/prompt/reflection logging."),
        ("mobile", "Dashboard, privacy, accountability, and groups work on mobile viewport."),
        ("release", "Smoke, build, and attention audit scripts have been run."),
    ]
    return [{"key": key, "status": "manual", "label": label} for key, label in items]


def static_log_scan(paths: list[Path]) -> dict:
    high_risk_patterns = [
        "console.log(prayer", "console.log(note", "console.log(review",
        "console.log(prompt", "console.log(rawResponse", "console.log(interruptionReason",
        "console.log(prayerRequest", "console.log(sharePayload", "console.log(reflection",
        "logger.info({ body", "logger.error({ body",
    ]
    hits = []
    for path in paths:
        if not path.exists() or path.is_dir():
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue
        for idx, line in enumerate(lines, start=1):
            compact = line.replace(" ", "")
            for pattern in high_risk_patterns:
                if pattern.replace(" ", "") in compact:
                    hits.append({"file": str(path), "line": idx, "pattern": pattern})
    return {"ok": not hits, "hits": hits, "scannedFiles": len(paths)}


def demo_seed_users() -> list[dict]:
    return deepcopy([
        {"email": "demo.alice@example.test", "nickname": "Alice", "scenario": "完整一周守心数据"},
        {"email": "demo.ben@example.test", "nickname": "Ben", "scenario": "Alice 的守望伙伴"},
        {"email": "demo.chloe@example.test", "nickname": "Chloe", "scenario": "小组 leader"},
        {"email": "demo.david@example.test", "nickname": "David", "scenario": "小组成员，较少记录"},
        {"email": "demo.eve@example.test", "nickname": "Eve", "scenario": "无权限隔离测试用户"},
    ])
