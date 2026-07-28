"""EMD-OS Batch 8: Formation Twin, identity, prayer, habit, pastoral and community integration.

    EM-62 Twin 快照桥 → EM-63 身份对齐 → EM-64 祷告状态路由 → EM-65 生活规则编译
    → EM-66 跨系统计划编排 → EM-67 牧养摘要脱敏 → EM-68 牧养与专业转介
    → EM-69 小组操练设计 → EM-70 群体反馈权力安全

九项不可突破的整合原则（由代码强制）：

1. 证据类型不得混写：可观察行为、用户解释、系统假设、经审核神学命题、牧者判断、用户确认整合。
2. 只有用户确认过的整合结论才能写入长期 Twin；撤回即失效并触发重算。
3. 用户拥有最终纠正权：撤回证据、删除共享、停止提醒、保留版本记录。
4. 属灵内容只能来自可版本化的神学内容包，不能由模型自由生成「神现在对你说……」。
5. 牧者、小组长、教会负责人默认没有任何访问权；角色不产生权限。
6. 群体反馈不能自动高于用户自己的证据。
7. 小组操练不得治疗化、不得监控化、不得强制披露。
8. 任何对外分享都是字段级、可预览、可删改、有期限、可撤回的。
9. 情感成熟度永远不能用于服事资格、按立、纪律或属灵排名。
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from .emotional_maturity import UnsafeContentError, validate_safe_text


ENGINE_VERSION = "emd-integration-engine-1.0"
RULE_VERSION = "emd-integration-rules-1.0"

# ── 统一证据契约 ─────────────────────────────────────────────────────────────
EVIDENCE_TYPES: dict[str, str] = {
    "OBSERVABLE_BEHAVIOR": "可观察行为",
    "USER_INTERPRETATION": "用户自己的解释",
    "SYSTEM_HYPOTHESIS": "系统暂定假设",
    "CURATED_THEOLOGICAL_PROPOSITION": "经审核神学内容库中的命题",
    "PASTORAL_DISCERNMENT": "牧者或人类关怀者的判断",
    "USER_CONFIRMED_INTEGRATION": "用户确认后形成的整合结论",
}
TWIN_WRITABLE_TYPES: frozenset[str] = frozenset({"OBSERVABLE_BEHAVIOR", "USER_CONFIRMED_INTEGRATION"})

# ── 牧养摘要中永远不能出现的字段 ─────────────────────────────────────────────
NEVER_SHAREABLE_FIELDS: frozenset[str] = frozenset({
    "journal_text", "prayer_text", "confession_text", "crisis_text", "childhood_material",
    "family_history_detail", "attachment_profile_raw", "unsent_drafts", "third_party_identity",
    "medical_detail", "sexual_detail", "financial_detail",
})

FORBIDDEN_USES: tuple[str, ...] = (
    "服事资格判断", "按立或职分决定", "小组长任命", "教会纪律决定",
    "属灵成熟排名", "雇佣、保险或信贷决定", "未经同意的第三方画像",
)

_DIVINE_VOICE = re.compile(
    r"(神(现在)?对你说|神告诉你|神给你的命定|神允许这次失败.{0,6}是为了|你(一定|正)受到.{0,6}(属灵)?(权势|捆绑)影响)"
)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _now(now: datetime | None = None) -> datetime:
    return now or datetime.now(timezone.utc)


def validate_theological_output(text: str) -> str:
    """Spiritual content must come from a versioned pack, never from free generation."""
    if _DIVINE_VOICE.search(text or ""):
        raise UnsafeContentError("system may not speak for God")
    return validate_safe_text(text)


# ─────────────────────────────────────────────────────────────────────────────
# EM-62 formation_twin_emotional_snapshot_bridge
# ─────────────────────────────────────────────────────────────────────────────

class TwinEvidence(BaseModel):
    evidence_id: str = Field(min_length=1, max_length=80)
    evidence_type: str
    dimension_code: str | None = None
    summary: str = Field(default="", max_length=240)
    user_confirmed: bool = False
    source_batch: int = Field(default=1, ge=1, le=10)

    @field_validator("evidence_type")
    @classmethod
    def known_type(cls, value: str) -> str:
        if value not in EVIDENCE_TYPES:
            raise ValueError(f"unknown evidence type: {value}")
        return value


def bridge_to_twin(
    evidence: list[TwinEvidence],
    *,
    consented_scopes: list[str],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Only user-confirmed, twin-writable evidence crosses into the long-term Twin."""
    moment = _now(now)
    if "EMD_LONGITUDINAL_TWIN" not in consented_scopes:
        return {
            "bridge_id": _new_id("brg"),
            "status": "BLOCKED_NO_CONSENT",
            "written": [],
            "next_action": "OFFER_LONGITUDINAL_CONSENT",
        }

    written: list[dict[str, Any]] = []
    held: list[dict[str, Any]] = []
    for item in evidence:
        writable = item.evidence_type in TWIN_WRITABLE_TYPES and item.user_confirmed
        record = {
            "evidence_id": item.evidence_id,
            "evidence_type": item.evidence_type,
            "evidence_type_label": EVIDENCE_TYPES[item.evidence_type],
            "dimension_code": item.dimension_code,
            "source_batch": item.source_batch,
            "user_confirmed": item.user_confirmed,
        }
        (written if writable else held).append(
            record if writable else {**record, "reason": (
                "TYPE_NOT_WRITABLE" if item.evidence_type not in TWIN_WRITABLE_TYPES else "USER_CONFIRMATION_MISSING"
            )}
        )

    return {
        "bridge_id": _new_id("brg"),
        "status": "WRITTEN" if written else "NOTHING_TO_WRITE",
        "written": written,
        "held_back": held,
        "evidence_types_never_merged": list(EVIDENCE_TYPES),
        "withdrawal_behaviour": [
            "撤回任一条证据会使其立即失效，并触发相关维度重算。",
            "旧版本以 superseded 形式保留，不静默改写历史。",
        ],
        "written_at": moment,
        "next_action": "MAP_IDENTITY_ALIGNMENT",
        "engine_version": ENGINE_VERSION,
    }


def withdraw_twin_evidence(evidence_id: str) -> dict[str, Any]:
    """A withdrawal always propagates: recompute, unshare, stop reminders, keep version history."""
    return {
        "withdrawal_id": _new_id("wdr"),
        "evidence_id": evidence_id,
        "effects": [
            "RECOMPUTE_DIMENSION_SNAPSHOT",
            "REVOKE_DERIVED_SHARES",
            "STOP_RELATED_REMINDERS",
            "KEEP_VERSION_HISTORY",
        ],
        "silent_retention": False,
        "next_action": "RECOMPUTE_AND_NOTIFY",
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-63 identity_spiritual_emotional_alignment_mapper
# ─────────────────────────────────────────────────────────────────────────────

ALIGNMENT_LAYERS: tuple[tuple[str, str], ...] = (
    ("IDENTITY_TRUTH", "我所相信的关于自己的核心真理（来自神学内容包或用户确认）"),
    ("ROLES", "我实际承担的角色"),
    ("VALUES", "我说我重视的"),
    ("EMOTIONAL_PATTERN", "在压力下实际出现的情绪与行为模式"),
    ("REAL_BEHAVIOR", "最近事件中真实发生的行为"),
)


def map_identity_alignment(
    *,
    layers: dict[str, list[str]],
    theology_pack_id: str | None = None,
) -> dict[str, Any]:
    """Alignment is a gap report, not a verdict on whether the user 'really believes' something."""
    unknown = [key for key in layers if key not in dict(ALIGNMENT_LAYERS)]
    if unknown:
        raise ValueError(f"unknown alignment layer: {','.join(unknown)}")
    for entries in layers.values():
        for entry in entries:
            validate_theological_output(entry)

    values = set(layers.get("VALUES", []))
    behaviors = set(layers.get("REAL_BEHAVIOR", []))
    missing_layers = [code for code, _ in ALIGNMENT_LAYERS if not layers.get(code)]

    gaps: list[dict[str, str]] = []
    if values and not behaviors:
        gaps.append({"code": "VALUE_WITHOUT_BEHAVIOR_EVIDENCE",
                     "note": "有清楚的价值陈述，但最近事件里还没有对应的行为证据。"})
    if layers.get("EMOTIONAL_PATTERN") and not layers.get("IDENTITY_TRUTH"):
        gaps.append({"code": "PATTERN_WITHOUT_IDENTITY_ANCHOR",
                     "note": "已描述压力下的模式，但还没有你自己确认的身份锚点。"})

    return {
        "alignment_id": _new_id("idn"),
        "layers": [
            {"code": code, "description": text, "entries": layers.get(code, [])}
            for code, text in ALIGNMENT_LAYERS
        ],
        "missing_layers": missing_layers,
        "gaps": gaps,
        "theology_pack_id": theology_pack_id,
        "not_a_verdict": "差距只是观察，不代表你不真诚，也不评估你的信心。",
        "next_action": "ROUTE_PRAYER_STATE",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-64 prayer_state_translation_and_liturgy_router
# ─────────────────────────────────────────────────────────────────────────────

PRAYER_FORMS: dict[str, str] = {
    "LAMENT": "哀歌：把痛苦、愤怒和疑问原样说出来",
    "CONFESSION": "认罪：为具体行为负责，不做自我羞辱",
    "PETITION": "祈求：说出具体的需要",
    "SURRENDER": "交托：放下无法控制的结果，同时保留仍要做的事",
    "THANKSGIVING": "感恩：说出仍然值得记得的",
    "EXAMEN": "省察：回顾一天里的安慰与枯干",
    "SILENCE": "静默：不说话地待一会儿",
    "INTERCESSION": "代祷：为别人祷告",
}
EMOTION_TO_PRAYER: dict[str, str] = {
    "GRIEF": "LAMENT", "ANGER": "LAMENT", "FEAR": "PETITION", "ANXIETY": "SILENCE",
    "GUILT": "CONFESSION", "SHAME": "LAMENT", "POWERLESSNESS": "SURRENDER",
    "GRATITUDE": "THANKSGIVING", "LONELINESS": "PETITION", "DISAPPOINTMENT": "LAMENT",
}


def route_prayer(
    *,
    confirmed_emotions: list[str],
    theology_pack_id: str | None = None,
    spiritual_framework: str = "user_choice",
    safety_level: str = "NONE",
) -> dict[str, Any]:
    """Route real emotion to a prayer form from a versioned pack. Prayer never replaces safety."""
    if spiritual_framework == "neutral":
        return {
            "routing_id": _new_id("pry"),
            "status": "NOT_APPLICABLE_NEUTRAL_FRAMEWORK",
            "forms": [],
            "alternatives": ["写下来", "与安全的人说", "安静休息十分钟"],
            "next_action": "COMPILE_RULE_OF_LIFE",
        }
    if safety_level in {"ELEVATED", "IMMINENT"}:
        return {
            "routing_id": _new_id("pry"),
            "status": "SAFETY_FIRST",
            "forms": [],
            "note": "先进入安全流程；祷告可以之后作为附加支持，但不替代紧急处理。",
            "next_action": "CRISIS_AND_SAFETY_SYSTEM",
        }

    forms: list[dict[str, str]] = []
    for emotion in confirmed_emotions:
        code = EMOTION_TO_PRAYER.get(emotion.upper())
        if code and not any(item["form"] == code for item in forms):
            forms.append({"emotion": emotion.upper(), "form": code, "description": PRAYER_FORMS[code]})
    if not forms:
        forms.append({"emotion": "UNSPECIFIED", "form": "SILENCE", "description": PRAYER_FORMS["SILENCE"]})

    return {
        "routing_id": _new_id("pry"),
        "status": "READY",
        "forms": forms,
        "available_forms": PRAYER_FORMS,
        "theology_pack_id": theology_pack_id,
        "content_source": "CURATED_THEOLOGICAL_PROPOSITION",
        "free_generation_allowed": False,
        "never_claims": [
            "不会说「神现在对你说……」",
            "不会宣告这次失败是神为了什么",
            "不会以祷告要求你停止悲伤或立刻原谅",
        ],
        "prayer_is_optional": True,
        "next_action": "COMPILE_RULE_OF_LIFE",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-65 rule_of_life_habit_compiler
# ─────────────────────────────────────────────────────────────────────────────

HABIT_CADENCES: tuple[str, ...] = ("DAILY", "WEEKLY", "RELATIONAL", "SEASONAL")
MAX_DAILY_HABITS = 3
MAX_WEEKLY_HABITS = 3
MAX_RELATIONAL_HABITS = 2


def compile_rule_of_life(
    *,
    goals: list[dict[str, Any]],
    current_load: int = 0,
    capacity: str = "NORMAL",
) -> dict[str, Any]:
    """Compile goals into a sustainable rule of life — capped, not maximised."""
    caps = {"DAILY": MAX_DAILY_HABITS, "WEEKLY": MAX_WEEKLY_HABITS, "RELATIONAL": MAX_RELATIONAL_HABITS,
            "SEASONAL": 2}
    if capacity == "LOW":
        caps = {key: max(1, value // 2) for key, value in caps.items()}

    compiled: dict[str, list[dict[str, Any]]] = {cadence: [] for cadence in HABIT_CADENCES}
    deferred: list[dict[str, Any]] = []
    for goal in goals:
        cadence = str(goal.get("cadence") or "DAILY").upper()
        if cadence not in HABIT_CADENCES:
            raise ValueError(f"unknown cadence: {cadence}")
        habit = validate_safe_text(str(goal.get("habit") or ""))
        record = {
            "habit": habit,
            "linked_dimension": goal.get("dimension_code"),
            "linked_module": goal.get("module"),
            "smallest_version": goal.get("smallest_version") or f"最小版本：{habit[:12]}…（两分钟内可完成）",
        }
        if len(compiled[cadence]) < caps[cadence]:
            compiled[cadence].append(record)
        else:
            deferred.append({**record, "cadence": cadence, "reason": "CADENCE_CAP_REACHED"})

    total = sum(len(items) for items in compiled.values())
    return {
        "rule_id": _new_id("rol"),
        "capacity": capacity,
        "caps": caps,
        "habits": {cadence: compiled[cadence] for cadence in HABIT_CADENCES},
        "total_habits": total,
        "deferred": deferred,
        "existing_load": current_load,
        "overload_warning": (
            "现有负担加上新习惯可能过多；建议先只保留每天一项。"
            if current_load + total > 6 else None
        ),
        "principles": [
            "习惯要小到即使在糟糕的一天也能完成。",
            "漏掉一天不算失败，也不影响任何评估。",
            "系统不用打卡数量代表成长。",
        ],
        "next_action": "ORCHESTRATE_CROSS_SYSTEM_PLAN",
        "rule_version": RULE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-66 cross_system_formation_plan_orchestrator
# ─────────────────────────────────────────────────────────────────────────────

PLAN_TRACKS: tuple[str, ...] = ("EMOTIONAL", "IDENTITY", "PRAYER", "HABIT", "COMMUNITY", "REASSESSMENT")
MAX_ACTIVE_TRACKS = 3


def orchestrate_plan(
    *,
    requested_tracks: list[str],
    priority_dimensions: list[str] | None = None,
    capacity: str = "NORMAL",
    safety_level: str = "NONE",
    consented_scopes: list[str] | None = None,
) -> dict[str, Any]:
    """One plan across systems, capped so that formation does not become another overload."""
    unknown = [item for item in requested_tracks if item not in PLAN_TRACKS]
    if unknown:
        raise ValueError(f"unknown plan track: {','.join(unknown)}")
    scopes = list(consented_scopes or [])

    if safety_level in {"ELEVATED", "IMMINENT"}:
        return {
            "plan_id": _new_id("pln"),
            "status": "SAFETY_FIRST",
            "active_tracks": [],
            "next_action": "CRISIS_AND_SAFETY_SYSTEM",
        }

    allowed = [track for track in requested_tracks if track != "COMMUNITY" or "EMD_PASTORAL_SHARE" in scopes]
    dropped = [track for track in requested_tracks if track not in allowed]
    limit = 2 if capacity == "LOW" else MAX_ACTIVE_TRACKS
    active = allowed[:limit]
    queued = allowed[limit:]

    return {
        "plan_id": _new_id("pln"),
        "status": "READY",
        "active_tracks": active,
        "queued_tracks": queued,
        "dropped_tracks": [{"track": item, "reason": "CONSENT_MISSING"} for item in dropped],
        "priority_dimensions": list(priority_dimensions or [])[:2],
        "max_active_tracks": limit,
        "checkpoints": [14, 30, 90],
        "single_plan_note": "所有系统共用一个计划，避免情感、祷告、习惯和小组各自安排任务。",
        "user_can_decline_any_track": True,
        "next_action": "OFFER_PASTORAL_SUMMARY" if "EMD_PASTORAL_SHARE" in scopes else "RUN_PLAN",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-67 pastoral_summary_consent_redactor
# ─────────────────────────────────────────────────────────────────────────────

SUMMARY_FIELDS: tuple[tuple[str, str], ...] = (
    ("CURRENT_FOCUS", "我现在正在练习的一两件事"),
    ("SUPPORT_NEEDED", "我希望得到的支持"),
    ("STAGE_SUMMARY", "维度阶段与置信度（不含分数）"),
    ("SAFETY_STATUS", "是否需要安全或专业支持"),
    ("BOUNDARY_NOTE", "我希望对方注意的边界"),
)
DEFAULT_SHARE_DAYS = 30


def build_pastoral_summary(
    *,
    selected_fields: list[str],
    field_values: dict[str, str],
    recipient_label: str,
    consented_scopes: list[str],
    expires_in_days: int = DEFAULT_SHARE_DAYS,
) -> dict[str, Any]:
    """Field-level consent, user preview, expiry and revocation — pastors have no default access."""
    if "EMD_PASTORAL_SHARE" not in consented_scopes:
        return {
            "summary_id": _new_id("sum"),
            "status": "BLOCKED_NO_CONSENT",
            "content": {},
            "next_action": "OFFER_PASTORAL_SHARE_CONSENT",
        }
    known = dict(SUMMARY_FIELDS)
    unknown = [item for item in selected_fields if item not in known]
    if unknown:
        raise ValueError(f"unknown summary field: {','.join(unknown)}")

    leaked = sorted(set(field_values) & NEVER_SHAREABLE_FIELDS)
    if leaked:
        raise UnsafeContentError(f"field is never shareable: {','.join(leaked)}")

    content = {}
    for field in selected_fields:
        value = validate_theological_output(str(field_values.get(field) or ""))
        content[field] = {"label": known[field], "value": value}

    return {
        "summary_id": _new_id("sum"),
        "status": "DRAFT_AWAITING_USER_PREVIEW",
        "recipient_label": recipient_label,
        "content": content,
        "excluded_fields": [code for code, _ in SUMMARY_FIELDS if code not in selected_fields],
        "never_shareable_fields": sorted(NEVER_SHAREABLE_FIELDS),
        "user_must_preview": True,
        "user_can_edit_each_field": True,
        "auto_sent": False,
        "expires_in_days": expires_in_days,
        "revocable_any_time": True,
        "forbidden_uses": list(FORBIDDEN_USES),
        "next_action": "USER_PREVIEW_AND_APPROVE",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-68 pastoral_care_handoff_coordinator
# ─────────────────────────────────────────────────────────────────────────────

HANDOFF_TARGETS: dict[str, str] = {
    "PASTORAL": "牧者或属灵关怀者",
    "COUNSELLING": "心理辅导或咨询师",
    "MEDICAL": "医疗或身体健康支持",
    "CRISIS": "危机与紧急安全支持",
    "LEGAL_OR_SAFETY": "法律、报警或保护流程",
    "PEER_SUPPORT": "同伴或小组守望",
}

HANDOFF_RULES: tuple[tuple[str, str], ...] = (
    ("SELF_HARM_OR_HARM_TO_OTHERS", "CRISIS"),
    ("MEDICAL_RED_FLAG", "MEDICAL"),
    ("VIOLENCE_OR_COERCIVE_CONTROL", "LEGAL_OR_SAFETY"),
    ("PERSISTENT_FUNCTIONAL_IMPAIRMENT", "COUNSELLING"),
    ("SPIRITUAL_AUTHORITY_HARM", "LEGAL_OR_SAFETY"),
    ("FAITH_QUESTION", "PASTORAL"),
    ("EVERYDAY_PRACTICE_SUPPORT", "PEER_SUPPORT"),
)


def coordinate_handoff(
    *,
    signals: list[str],
    church_involved_in_harm: bool = False,
    user_consented_to_contact: bool = False,
) -> dict[str, Any]:
    """Route to the right human support. The system never contacts anyone on its own."""
    codes = {str(item).upper() for item in signals}
    targets: list[dict[str, str]] = []
    for signal, target in HANDOFF_RULES:
        if signal in codes:
            targets.append({"signal": signal, "target": target, "label": HANDOFF_TARGETS[target]})

    if church_involved_in_harm:
        targets = [item for item in targets if item["target"] != "PASTORAL"]
        targets.append({
            "signal": "CHURCH_INVOLVED_IN_HARM", "target": "LEGAL_OR_SAFETY",
            "label": HANDOFF_TARGETS["LEGAL_OR_SAFETY"],
        })

    return {
        "handoff_id": _new_id("hnd"),
        "targets": targets or [{"signal": "NONE", "target": "PEER_SUPPORT", "label": HANDOFF_TARGETS["PEER_SUPPORT"]}],
        "auto_contact": False,
        "user_consent_required": True,
        "user_consented": user_consented_to_contact,
        "conflict_of_interest_rule": (
            "当伤害与教会权力相关时，不把用户转介回同一权力结构。"
        ),
        "draft_message": "我最近有一些情况想找人谈谈，你方便的时候我们约个时间。",
        "system_does_not": [
            "系统不会替你联系任何人。",
            "系统不会把你的记录发给牧者或机构。",
            "系统不做临床诊断，也不替代紧急服务。",
        ],
        "next_action": "USER_DECIDES_CONTACT",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-69 small_group_practice_accountability_designer
# ─────────────────────────────────────────────────────────────────────────────

GROUP_PRACTICE_KINDS: dict[str, str] = {
    "SHARED_PRACTICE": "共同操练同一个小习惯",
    "CHECK_IN_QUESTION": "一个每周的开放性问题",
    "SILENT_COMPANIONSHIP": "安静陪伴或一起祷告",
    "SKILL_REHEARSAL": "在小组中练习一次表达或暂停",
    "SERVICE_TOGETHER": "一起做一件小事",
}
FORBIDDEN_GROUP_PATTERNS: tuple[str, ...] = (
    "要求成员披露童年创伤或家庭细节",
    "把小组变成治疗小组或诊断场所",
    "公开比较成员的成熟度或进度",
    "把出勤或打卡作为属灵评价",
    "组长查看成员的私人记录",
    "以属灵理由施压要求原谅或恢复关系",
)


def design_group_practice(
    *,
    kind: str,
    group_size: int,
    disclosure_required: bool = False,
    leader_can_view_records: bool = False,
) -> dict[str, Any]:
    """Group practice is opt-in, non-therapeutic and never surveillance."""
    if kind not in GROUP_PRACTICE_KINDS:
        raise ValueError(f"unknown group practice kind: {kind}")
    blocks: list[str] = []
    if disclosure_required:
        blocks.append("DISCLOSURE_REQUIREMENT_NOT_ALLOWED")
    if leader_can_view_records:
        blocks.append("LEADER_RECORD_ACCESS_NOT_ALLOWED")
    if blocks:
        return {
            "practice_id": _new_id("grp"),
            "status": "REJECTED",
            "blocks": blocks,
            "forbidden_patterns": list(FORBIDDEN_GROUP_PATTERNS),
            "next_action": "REDESIGN_PRACTICE",
        }

    return {
        "practice_id": _new_id("grp"),
        "status": "READY",
        "kind": kind,
        "kind_label": GROUP_PRACTICE_KINDS[kind],
        "group_size": group_size,
        "opt_in": True,
        "pass_allowed": True,
        "pass_note": "任何人都可以说「这次我先听」，不需要解释。",
        "disclosure_required": False,
        "leader_record_access": False,
        "forbidden_patterns": list(FORBIDDEN_GROUP_PATTERNS),
        "confidentiality_agreement": "小组内的分享不带出小组；这一点需要每次明确说明。",
        "next_action": "RECONCILE_COMMUNITY_FEEDBACK",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-70 community_feedback_power_safety_reconciler
# ─────────────────────────────────────────────────────────────────────────────

FEEDBACK_WEIGHT_CAP = 0.3
POWER_LEVELS: tuple[str, ...] = ("PEER", "MODERATE_AUTHORITY", "HIGH_AUTHORITY")


def reconcile_community_feedback(
    *,
    feedback_items: list[dict[str, Any]],
    user_evidence_count: int,
    user_disputes: list[str] | None = None,
) -> dict[str, Any]:
    """Community feedback informs; it never outranks the user's own evidence or assigns eligibility."""
    disputed = set(user_disputes or [])
    accepted: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    for item in feedback_items:
        feedback_id = str(item.get("feedback_id") or _new_id("fbk"))
        power = str(item.get("power_level") or "PEER").upper()
        if power not in POWER_LEVELS:
            raise ValueError(f"unknown power level: {power}")
        text = validate_theological_output(str(item.get("observation") or ""))
        if any(keyword in text for keyword in ("资格", "按立", "不配", "不够属灵", "应该被撤下")):
            excluded.append({"feedback_id": feedback_id, "reason": "ELIGIBILITY_MISUSE"})
            continue
        if feedback_id in disputed:
            excluded.append({"feedback_id": feedback_id, "reason": "USER_DISPUTED"})
            continue
        weight = FEEDBACK_WEIGHT_CAP
        if power == "HIGH_AUTHORITY":
            weight = FEEDBACK_WEIGHT_CAP / 2
        accepted.append({
            "feedback_id": feedback_id,
            "power_level": power,
            "observation": text,
            "weight": round(weight, 2),
            "status": "OBSERVATION_ONLY",
        })

    return {
        "reconciliation_id": _new_id("rec"),
        "accepted": accepted,
        "excluded": excluded,
        "max_single_weight": FEEDBACK_WEIGHT_CAP,
        "user_evidence_count": user_evidence_count,
        "community_cannot_outrank_user": True,
        "high_authority_downweighted": True,
        "forbidden_uses": list(FORBIDDEN_USES),
        "user_may_dispute_any_item": True,
        "next_action": "UPDATE_FORMATION_TWIN",
        "rule_version": RULE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 状态机与自描述
# ─────────────────────────────────────────────────────────────────────────────

WORKFLOW_NODES: tuple[str, ...] = (
    "EM-62_twin_bridge", "EM-63_identity_alignment", "EM-64_prayer_router",
    "EM-65_rule_of_life", "EM-66_plan_orchestrator", "EM-67_pastoral_summary",
    "EM-68_handoff_coordinator", "EM-69_group_practice", "EM-70_community_feedback",
)

STATE_MACHINE: tuple[tuple[str, str], ...] = (
    ("EVIDENCE_CONFIRMED", "TWIN_UPDATED"),
    ("TWIN_UPDATED", "IDENTITY_ALIGNED"),
    ("IDENTITY_ALIGNED", "PRAYER_ROUTED"),
    ("PRAYER_ROUTED", "RULE_OF_LIFE_COMPILED"),
    ("RULE_OF_LIFE_COMPILED", "PLAN_ORCHESTRATED"),
    ("PLAN_ORCHESTRATED", "PASTORAL_SUMMARY_DRAFTED"),
    ("PLAN_ORCHESTRATED", "PLAN_RUNNING"),
    ("PASTORAL_SUMMARY_DRAFTED", "SUMMARY_SHARED"),
    ("PASTORAL_SUMMARY_DRAFTED", "SUMMARY_DISCARDED"),
    ("SUMMARY_SHARED", "SHARE_REVOKED"),
    ("PLAN_RUNNING", "GROUP_PRACTICE_ACTIVE"),
    ("GROUP_PRACTICE_ACTIVE", "COMMUNITY_FEEDBACK_RECONCILED"),
    ("COMMUNITY_FEEDBACK_RECONCILED", "TWIN_UPDATED"),
)


def describe_integration_engine() -> dict[str, Any]:
    return {
        "module": "emotional_maturity_integration",
        "short_name": "EMD-OS Batch 8",
        "batch": 8,
        "skills": list(WORKFLOW_NODES),
        "evidence_types": EVIDENCE_TYPES,
        "twin_writable_types": sorted(TWIN_WRITABLE_TYPES),
        "alignment_layers": [{"code": code, "description": text} for code, text in ALIGNMENT_LAYERS],
        "prayer_forms": PRAYER_FORMS,
        "habit_cadences": list(HABIT_CADENCES),
        "plan_tracks": list(PLAN_TRACKS),
        "summary_fields": [{"code": code, "label": label} for code, label in SUMMARY_FIELDS],
        "never_shareable_fields": sorted(NEVER_SHAREABLE_FIELDS),
        "handoff_targets": HANDOFF_TARGETS,
        "group_practice_kinds": GROUP_PRACTICE_KINDS,
        "forbidden_group_patterns": list(FORBIDDEN_GROUP_PATTERNS),
        "forbidden_uses": list(FORBIDDEN_USES),
        "max_community_feedback_weight": FEEDBACK_WEIGHT_CAP,
        "does_not": [
            "不混写不同类型的证据",
            "不把未经用户确认的结论写入 Formation Twin",
            "不让模型自由生成神对用户说的话",
            "不因为角色是牧者或小组长就给予访问权",
            "不让群体反馈高于用户自己的证据",
            "不把小组变成治疗或监控场所",
            "不把情感成熟度用于服事资格、按立或纪律",
            "不替用户联系任何人",
        ],
        "engine_version": ENGINE_VERSION,
        "rule_version": RULE_VERSION,
        "state_machine": [{"from": source, "to": target} for source, target in STATE_MACHINE],
    }
