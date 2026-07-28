"""EMD-OS Batch 4: emotion awareness and regulation training (EM-28 ~ EM-35).

Batch 1–3 回答「评估什么、证据是否可信、现实中是否真的改变」；Batch 4 进入干预层，
目标不是让用户「没有情绪」，而是在这条链路上尽早恢复选择能力：

    触发事件 → 身体激活 → 情绪与意义 → 行动冲动 → 实际行为 → 后果 → 恢复与修复

运行链：

    EM-29 身体信号扫描 → EM-28 情绪精确命名 → EM-30 触发预警匹配
    → 激活分区路由：GREEN 觉察 / AMBER EM-31 暂停 / RED EM-32 冲动阻断 → EM-33 共同调节
    → CRISIS 交给现有 Crisis & Safety System
    → EM-34 四类恢复计划 → EM-35 旧模式复现演练 → 回到 Batch 3 的现实迁移验证

边界（由代码强制）：

* 情绪、行动冲动、实际行为三者分开：出现愤怒不被定罪，实际行为仍要负责。
* 愤怒不被自动解释为「次级情绪」；候选情绪永远是候选，需用户确认。
* 高激活时不做深度下潜：先停止危险行为、稳定身体、恢复选择能力。
* 身体信号不是心理诊断；胸痛、呼吸困难、眩晕、心悸、麻木退出情绪训练走医疗/安全提示。
* 属灵操练可以是选项，但不得用来压抑合理的悲伤或愤怒，也不得替代安全、医疗或专业支持。
"""
from __future__ import annotations

import hashlib
import json
import statistics
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .emotional_maturity import UnsafeContentError, validate_safe_text


ENGINE_VERSION = "emd-regulation-engine-1.0"
RULE_VERSION = "emd-regulation-rules-1.0"

SESSION_MODES: tuple[str, ...] = ("REAL_TIME", "RETROSPECTIVE", "REHEARSAL")
SAFETY_STATUSES: tuple[str, ...] = ("UNKNOWN", "SAFE", "NEEDS_CAUTION", "HIGH_RISK", "CRISIS_ROUTED")
ACTIVATION_BANDS: tuple[str, ...] = ("GREEN", "AMBER", "RED", "CRISIS", "UNKNOWN")
ACTIVATION_BAND_RANK: dict[str, int] = {"UNKNOWN": -1, "GREEN": 0, "AMBER": 1, "RED": 2, "CRISIS": 3}

# 工程默认值，不是临床阈值。
ACTIVATION_THRESHOLDS: tuple[tuple[str, int], ...] = (("GREEN", 3), ("AMBER", 6), ("RED", 8), ("CRISIS", 10))

CRISIS_SIGNALS: frozenset[str] = frozenset({
    "SELF_HARM_URGE", "SUICIDAL_IDEATION", "HARM_TO_OTHERS_URGE", "VIOLENCE_PRESENT",
    "DANGEROUS_DRIVING", "CANNOT_GUARANTEE_SAFETY",
})
HIGH_IMPULSE_SIGNALS: frozenset[str] = frozenset({
    "SEND_HOSTILE_MESSAGE", "PUBLIC_ATTACK", "QUIT_JOB_NOW", "BREAK_UP_NOW",
    "DELETE_IMPORTANT_DATA", "DESTROY_PROPERTY", "IMPULSE_SPENDING", "CUT_OFF_CONTACT_NOW",
})


# ─────────────────────────────────────────────────────────────────────────────
# EM-28 emotion_precise_labeling_trainer
# ─────────────────────────────────────────────────────────────────────────────

EMOTION_LEXICON: dict[str, dict[str, str]] = {
    "ANGER": {"label": "愤怒", "family": "anger", "valence": "unpleasant", "activation": "high"},
    "HURT": {"label": "受伤", "family": "sadness", "valence": "unpleasant", "activation": "medium"},
    "SHAME": {"label": "羞耻", "family": "shame", "valence": "unpleasant", "activation": "medium"},
    "GUILT": {"label": "内疚", "family": "shame", "valence": "unpleasant", "activation": "medium"},
    "FEAR": {"label": "害怕", "family": "fear", "valence": "unpleasant", "activation": "high"},
    "ANXIETY": {"label": "焦虑", "family": "fear", "valence": "unpleasant", "activation": "high"},
    "POWERLESSNESS": {"label": "无力", "family": "sadness", "valence": "unpleasant", "activation": "low"},
    "DISAPPOINTMENT": {"label": "失望", "family": "sadness", "valence": "unpleasant", "activation": "low"},
    "LONELINESS": {"label": "孤单", "family": "sadness", "valence": "unpleasant", "activation": "low"},
    "REJECTION": {"label": "被拒绝", "family": "sadness", "valence": "unpleasant", "activation": "medium"},
    "ENVY": {"label": "嫉妒", "family": "anger", "valence": "unpleasant", "activation": "medium"},
    "OVERLOOKED": {"label": "被忽视", "family": "sadness", "valence": "unpleasant", "activation": "medium"},
    "GRIEF": {"label": "哀伤", "family": "sadness", "valence": "unpleasant", "activation": "low"},
    "RELIEF": {"label": "松了一口气", "family": "joy", "valence": "pleasant", "activation": "low"},
    "GRATITUDE": {"label": "感恩", "family": "joy", "valence": "pleasant", "activation": "low"},
}

# 训练模式中的易混淆对
CONFUSION_PAIRS: tuple[tuple[str, str, str], ...] = (
    ("DISAPPOINTMENT", "SHAME", "失望指向事情没有达到期待；羞耻指向「我这个人有问题」。"),
    ("FEAR", "POWERLESSNESS", "害怕通常有具体威胁对象；无力更多是「我做什么都改变不了」。"),
    ("ENVY", "OVERLOOKED", "嫉妒关注对方拥有什么；被忽视关注我没有被看见。"),
    ("GUILT", "SHAME", "内疚是「我做错了一件事」；羞耻是「我这个人是错的」。"),
    ("LONELINESS", "REJECTION", "孤单是没有连接；被拒绝是有连接但被推开。"),
)

_EMOTION_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ANGER", ("气", "愤怒", "火大", "怒", "恼")),
    ("HURT", ("受伤", "难受", "心里疼", "被刺到")),
    ("SHAME", ("丢脸", "羞", "无地自容", "抬不起头")),
    ("GUILT", ("内疚", "对不起", "都怪我")),
    ("FEAR", ("害怕", "怕", "恐惧", "不安")),
    ("ANXIETY", ("焦虑", "紧张", "慌")),
    ("POWERLESSNESS", ("无力", "没办法", "做什么都没用")),
    ("DISAPPOINTMENT", ("失望", "落空", "白费")),
    ("LONELINESS", ("孤单", "没人", "一个人")),
    ("REJECTION", ("被拒绝", "被推开", "不要我")),
    ("ENVY", ("嫉妒", "羡慕又难受")),
    ("OVERLOOKED", ("被忽视", "没人看见", "当我不存在")),
    ("GRIEF", ("哀伤", "失去", "走了")),
)

_URGE_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("SEND_HOSTILE_MESSAGE", ("骂回去", "发消息骂", "怼回去", "群里说")),
    ("PUBLIC_ATTACK", ("公开", "发朋友圈", "让大家知道")),
    ("CUT_OFF_CONTACT_NOW", ("再也不联系", "拉黑", "断联")),
    ("QUIT_JOB_NOW", ("辞职", "不干了")),
    ("BREAK_UP_NOW", ("分手", "离婚")),
    ("WITHDRAW", ("不想说话", "关起来", "冷着")),
    ("DESTROY_PROPERTY", ("摔", "砸")),
)

_INTERPRETATION_HINTS: tuple[str, ...] = ("我觉得", "他就是", "她就是", "肯定是", "一定是", "分明是", "根本就")


class LabelingInput(BaseModel):
    mode: str = "REAL_TIME"
    raw_utterance: str = Field(default="", max_length=2000)
    context: str = "other"
    known_facts: list[str] = Field(default_factory=list, max_length=8)
    user_activation_level: int | None = Field(default=None, ge=0, le=10)
    safety_signals: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("mode")
    @classmethod
    def known_mode(cls, value: str) -> str:
        if value not in SESSION_MODES:
            raise ValueError(f"unknown session mode: {value}")
        return value


def activation_band(
    level: int | None,
    *,
    signals: list[str] | None = None,
    environment_safe: bool = True,
    can_stop_action: bool = True,
    irreversible_action_pending: bool = False,
) -> dict[str, Any]:
    """A single number never decides the route on its own."""
    codes = {str(item).upper() for item in (signals or [])}
    band = "UNKNOWN"
    if level is not None:
        for candidate, ceiling in ACTIVATION_THRESHOLDS:
            if level <= ceiling:
                band = candidate
                break
    if codes & HIGH_IMPULSE_SIGNALS and ACTIVATION_BAND_RANK[band] < ACTIVATION_BAND_RANK["RED"]:
        band = "RED"
    if not environment_safe or not can_stop_action:
        band = max(band, "RED", key=lambda value: ACTIVATION_BAND_RANK[value])
    if irreversible_action_pending:
        band = max(band, "RED", key=lambda value: ACTIVATION_BAND_RANK[value])
    if codes & CRISIS_SIGNALS:
        band = "CRISIS"
    return {
        "band": band,
        "level": level,
        "signals": sorted(codes),
        "environment_safe": environment_safe,
        "can_stop_action": can_stop_action,
        "irreversible_action_pending": irreversible_action_pending,
        "deep_dive_allowed": band in {"GREEN", "AMBER"},
        "route": {
            "GREEN": "AWARENESS_AND_REFLECTION",
            "AMBER": "SACRED_PAUSE_PROTOCOL",
            "RED": "IMPULSE_INTERRUPTER",
            "CRISIS": "CRISIS_AND_SAFETY_SYSTEM",
            "UNKNOWN": "ASK_ACTIVATION_LEVEL",
        }[band],
        "rule_version": RULE_VERSION,
    }


def label_emotions(payload: LabelingInput) -> dict[str, Any]:
    """Separate fact, interpretation, emotion candidates and action urges. Candidates stay candidates."""
    text = payload.raw_utterance or ""
    validate_safe_text(text)

    interpretations = [hint for hint in _INTERPRETATION_HINTS if hint in text]
    candidates: list[dict[str, Any]] = []
    for code, hints in _EMOTION_HINTS:
        span = next((hint for hint in hints if hint in text), None)
        if span:
            entry = dict(EMOTION_LEXICON[code])
            candidates.append({
                "emotion_code": code, "localized_label": entry["label"], "family": entry["family"],
                "valence": entry["valence"], "activation": entry["activation"],
                "supporting_span": span, "status": "CANDIDATE_AWAITING_USER_CONFIRMATION",
            })
    candidates = candidates[:3]

    urges = []
    for code, hints in _URGE_HINTS:
        span = next((hint for hint in hints if hint in text), None)
        if span:
            urges.append({"urge_code": code, "supporting_span": span, "executed": False})

    band = activation_band(payload.user_activation_level, signals=[item["urge_code"] for item in urges] + payload.safety_signals)
    short_path = payload.mode == "REAL_TIME" or band["band"] in {"RED", "CRISIS"}

    result = {
        "labeling_id": f"lbl_{uuid.uuid4().hex[:10]}",
        "mode": payload.mode,
        "objective_facts": list(payload.known_facts),
        "user_interpretations": interpretations,
        "emotion_candidates": candidates,
        "confirmed_emotions": [],
        "action_urges": urges,
        "activation": band,
        "path": "SHORT_PATH" if short_path else "FULL_PATH",
        "deep_dive_offered": band["deep_dive_allowed"] and payload.mode == "RETROSPECTIVE",
        "training_pairs": [
            {"a": first, "b": second, "distinction": note} for first, second, note in CONFUSION_PAIRS
        ] if payload.mode == "REHEARSAL" else [],
        "principles": [
            "情绪、行动冲动和实际行为是三件事：有情绪不等于做错事。",
            "愤怒可能是对不公、越界或伤害的合理反应，系统不会把它自动解释成别的情绪。",
            "候选情绪只是候选，需要你确认；你也可以给出系统没列出的词。",
        ],
        "next_action": band["route"],
        "engine_version": ENGINE_VERSION,
    }
    return result


def confirm_emotions(labeling: dict[str, Any], confirmed_codes: list[str], *, user_words: list[str] | None = None) -> dict[str, Any]:
    """Only the user turns a candidate into a confirmed emotion."""
    unknown = [code for code in confirmed_codes if code not in EMOTION_LEXICON]
    if unknown:
        raise ValueError(f"unknown emotion code: {','.join(unknown)}")
    confirmed = [
        {"emotion_code": code, "localized_label": EMOTION_LEXICON[code]["label"], "status": "USER_CONFIRMED"}
        for code in confirmed_codes
    ]
    for word in user_words or []:
        validate_safe_text(word)
        confirmed.append({"emotion_code": "USER_DEFINED", "localized_label": word, "status": "USER_CONFIRMED"})
    return {
        **labeling,
        "confirmed_emotions": confirmed,
        "emotion_candidates": [
            item for item in labeling["emotion_candidates"] if item["emotion_code"] not in confirmed_codes
        ],
        "next_action": labeling["next_action"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-29 interoceptive_body_signal_scanner
# ─────────────────────────────────────────────────────────────────────────────

EARLY_BODY_SIGNALS: dict[str, str] = {
    "JAW_CLENCH": "下颌咬紧",
    "SHOULDER_TENSION": "肩颈紧绷",
    "CHEST_TIGHT": "胸口发紧",
    "STOMACH_DROP": "胃部下沉",
    "HEAT_IN_FACE": "脸上发热",
    "SHALLOW_BREATH": "呼吸变浅",
    "HANDS_SHAKING": "手在抖",
    "RESTLESS_LEGS": "坐不住",
    "VOICE_TIGHT": "声音变紧",
    "GOING_NUMB": "整个人变木",
}
MEDICAL_RED_FLAGS: dict[str, str] = {
    "CHEST_PAIN": "胸痛",
    "BREATHING_DIFFICULTY": "呼吸困难",
    "DIZZINESS": "眩晕",
    "PALPITATIONS": "心悸",
    "LIMB_NUMBNESS": "手脚麻木",
    "FAINTING": "昏倒",
}


def scan_body_signals(
    reported_signals: list[str],
    *,
    activation_level: int | None = None,
) -> dict[str, Any]:
    """Record what the body reports. Never explain a red-flag symptom as anxiety."""
    codes = [str(item).upper() for item in reported_signals]
    red_flags = sorted({code for code in codes if code in MEDICAL_RED_FLAGS})
    early = sorted({code for code in codes if code in EARLY_BODY_SIGNALS})
    unknown = sorted({code for code in codes if code not in EARLY_BODY_SIGNALS and code not in MEDICAL_RED_FLAGS})

    if red_flags:
        return {
            "scan_id": f"bod_{uuid.uuid4().hex[:10]}",
            "status": "EXIT_TO_MEDICAL_SAFETY",
            "medical_red_flags": [{"code": code, "label": MEDICAL_RED_FLAGS[code]} for code in red_flags],
            "recorded_statement": "用户报告了身体不适；原因未知。",
            "forbidden_interpretations": ["不得把这些身体信号解释为焦虑或情绪问题。"],
            "emotion_training_paused": True,
            "next_action": "ROUTE_TO_MEDICAL_OR_EMERGENCY_GUIDANCE",
        }

    return {
        "scan_id": f"bod_{uuid.uuid4().hex[:10]}",
        "status": "RECORDED",
        "early_signals": [{"code": code, "label": EARLY_BODY_SIGNALS[code]} for code in early],
        "unrecognised_signals": unknown,
        "activation_level": activation_level,
        "note": "身体信号只是记录，不是心理或医学诊断。",
        "earliest_signal": early[0] if early else None,
        "next_action": "PRECISE_EMOTION_LABELING",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-30 trigger_early_warning_profiler
# ─────────────────────────────────────────────────────────────────────────────

MIN_EVENTS_FOR_TRIGGER_PROFILE = 2


def build_trigger_profile(
    events: list[dict[str, Any]],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build an individual early-warning profile from real events — user confirms before use."""
    moment = now or datetime.now(timezone.utc)
    if len(events) < MIN_EVENTS_FOR_TRIGGER_PROFILE:
        return {
            "profile_id": f"trg_{uuid.uuid4().hex[:10]}",
            "status": "INSUFFICIENT_EVENTS",
            "minimum_required": MIN_EVENTS_FOR_TRIGGER_PROFILE,
            "note": "还没有足够的现实事件来建立个体化预警；这不代表你没有模式。",
            "next_action": "COLLECT_MORE_EVENTS",
        }

    triggers = Counter()
    contexts = Counter()
    body = Counter()
    urges = Counter()
    escalation_minutes: list[float] = []
    for event in events:
        for item in event.get("trigger_codes") or []:
            triggers[str(item)] += 1
        contexts[str(event.get("context") or "other")] += 1
        for item in event.get("body_signals") or []:
            body[str(item).upper()] += 1
        for item in event.get("urges") or []:
            urges[str(item).upper()] += 1
        if event.get("escalation_minutes") is not None:
            escalation_minutes.append(float(event["escalation_minutes"]))

    signature = [code for code, count in triggers.most_common(3) if count >= 2] or [code for code, _ in triggers.most_common(2)]
    earliest_body = [code for code, count in body.most_common(3)]
    window = round(statistics.median(escalation_minutes), 1) if escalation_minutes else None

    return {
        "profile_id": f"trg_{uuid.uuid4().hex[:10]}",
        "status": "DRAFT_AWAITING_USER_CONFIRMATION",
        "event_count": len(events),
        "trigger_signature": signature,
        "contexts": [code for code, _ in contexts.most_common()],
        "earliest_body_signals": earliest_body,
        "typical_urges": [code for code, _ in urges.most_common(3)],
        "median_escalation_minutes": window,
        "early_warning_window": (
            f"从触发到冲动明显升高，中位数约 {window} 分钟" if window is not None else "升级时间尚未有足够记录"
        ),
        "user_review_status": "PENDING",
        "limitations": [
            "这是对已记录事件的描述，不是对你人格的判断。",
            "预警模型只在你确认后才会被用来提示。",
        ],
        "generated_at": moment,
        "next_action": "USER_CONFIRM_TRIGGER_PROFILE",
        "rule_version": RULE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-31 sacred_pause_protocol_coach
# ─────────────────────────────────────────────────────────────────────────────

PAUSE_STEPS: tuple[tuple[str, str], ...] = (
    ("STOP", "停：停止发送、争辩、操作或作出不可逆决定"),
    ("STEADY", "稳：确认环境安全，脚接触地面，放慢动作和呼吸"),
    ("DISTINGUISH", "辨：区分事实、解释、情绪、身体信号和行动冲动"),
    ("CHOOSE", "选：选择离开、延迟、求助、写草稿或简短回应"),
    ("TELL", "告：如关系安全，告知对方暂停时间和返回方式"),
    ("RETURN", "复：在约定时间内返回、更新或重新安排沟通"),
)
PAUSE_LEVELS: dict[str, dict[str, Any]] = {
    "P1": {"name": "微暂停", "min_seconds": 30, "max_seconds": 90,
           "fits": "情绪开始升高，仍能思考，尚未进入攻击或逃避"},
    "P2": {"name": "短暂停", "min_seconds": 600, "max_seconds": 1200,
           "fits": "身体激活明显，容易说出伤害性话语，需要先离开现场"},
    "P3": {"name": "延长暂停", "min_seconds": 7200, "max_seconds": 86400,
           "fits": "双方都高度激活，短暂停后仍无法安全沟通，需要睡眠或外部支持"},
}


def build_pause_protocol(
    *,
    band: str,
    relationship_safety: str = "STANDARD",
    both_parties_activated: bool = False,
    user_requested_level: str | None = None,
) -> dict[str, Any]:
    """Six-step pause. 告/复 exist so that a pause never degrades into cold shoulder."""
    if band not in ACTIVATION_BANDS:
        raise ValueError(f"unknown activation band: {band}")
    if band == "CRISIS":
        return {
            "protocol_id": f"pau_{uuid.uuid4().hex[:10]}",
            "status": "ROUTED_TO_CRISIS",
            "steps": [],
            "next_action": "CRISIS_AND_SAFETY_SYSTEM",
        }

    level = user_requested_level or {"GREEN": "P1", "AMBER": "P2", "RED": "P3", "UNKNOWN": "P1"}[band]
    if level not in PAUSE_LEVELS:
        raise ValueError(f"unknown pause level: {level}")
    if both_parties_activated:
        level = "P3"

    steps = [{"code": code, "instruction": text} for code, text in PAUSE_STEPS]
    tell_allowed = relationship_safety != "CAUTION"
    if not tell_allowed:
        steps = [step for step in steps if step["code"] != "TELL"]

    detail = PAUSE_LEVELS[level]
    return {
        "protocol_id": f"pau_{uuid.uuid4().hex[:10]}",
        "status": "READY",
        "pause_level": level,
        "pause_level_name": detail["name"],
        "fits": detail["fits"],
        "duration_seconds": [detail["min_seconds"], detail["max_seconds"]],
        "steps": steps,
        "return_commitment_required": level in {"P2", "P3"},
        "return_note": (
            "暂停时告诉对方你会在什么时候回来，避免暂停变成冷暴力。"
            if tell_allowed else
            "关系安全存疑时不要求你通知对方；先保护自己，返回方式由你决定。"
        ),
        "third_party_support_suggested": level == "P3",
        "next_action": "IMPULSE_INTERRUPTER" if band == "RED" else "POST_ACTIVATION_RECOVERY_PLANNER",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-32 impulse_action_interrupter
# ─────────────────────────────────────────────────────────────────────────────

REVERSIBILITY_CLASSES: tuple[str, ...] = (
    "REVERSIBLE_LOW_IMPACT", "REVERSIBLE_HIGH_IMPACT", "IRREVERSIBLE_HIGH_IMPACT", "SAFETY_CRITICAL",
)
INTERRUPT_STRATEGIES: tuple[str, ...] = (
    "DRAFT_ONLY", "DELAY_WINDOW", "FRICTION_LAYER", "SUBSTITUTE_ACTION", "ACCOUNTABILITY",
)
DELAY_WINDOWS: dict[str, int] = {
    "REVERSIBLE_LOW_IMPACT": 10 * 60,
    "REVERSIBLE_HIGH_IMPACT": 30 * 60,
    "IRREVERSIBLE_HIGH_IMPACT": 12 * 3600,
}
SUBSTITUTE_ACTIONS: dict[str, str] = {
    "SEND_HOSTILE_MESSAGE": "把想说的话写成一封不发送的信，保存为私人草稿。",
    "PUBLIC_ATTACK": "先记录事实和你想澄清的问题，不公开发布。",
    "QUIT_JOB_NOW": "生成一份离职原因与后果检查表，等睡一晚再决定。",
    "BREAK_UP_NOW": "写下你真正无法接受的具体行为，暂不作最终决定。",
    "CUT_OFF_CONTACT_NOW": "发送一句暂停声明，说明你需要多久，而不是直接断联。",
    "DELETE_IMPORTANT_DATA": "把内容移到归档文件夹，24 小时后再决定是否删除。",
    "DESTROY_PROPERTY": "先离开这个房间十分钟。",
    "IMPULSE_SPENDING": "把商品放进清单，明天同一时间再看一次。",
}


def interrupt_impulse(
    *,
    urge_type: str,
    urgency: int,
    reversibility: str,
    activation_level: int | None = None,
    safety_signals: list[str] | None = None,
    support_available: bool = False,
) -> dict[str, Any]:
    """Add a protective layer in front of irreversible actions; safety-critical goes to crisis."""
    if reversibility not in REVERSIBILITY_CLASSES:
        raise ValueError(f"unknown reversibility class: {reversibility}")
    codes = {str(item).upper() for item in (safety_signals or [])}
    if reversibility == "SAFETY_CRITICAL" or codes & CRISIS_SIGNALS:
        return {
            "guard_id": f"imp_{uuid.uuid4().hex[:10]}",
            "status": "ROUTED_TO_CRISIS",
            "strategies": [],
            "note": "涉及人身安全时不进入普通冲动阻断流程。",
            "next_action": "CRISIS_AND_SAFETY_SYSTEM",
        }

    strategies: list[str] = ["DRAFT_ONLY", "DELAY_WINDOW", "FRICTION_LAYER"]
    if urge_type.upper() in SUBSTITUTE_ACTIONS:
        strategies.append("SUBSTITUTE_ACTION")
    if support_available and urgency >= 7:
        strategies.append("ACCOUNTABILITY")

    delay = DELAY_WINDOWS[reversibility]
    if urgency >= 8 and reversibility == "IRREVERSIBLE_HIGH_IMPACT":
        delay = 24 * 3600

    return {
        "guard_id": f"imp_{uuid.uuid4().hex[:10]}",
        "status": "GUARDED",
        "urge_type": urge_type.upper(),
        "urgency": urgency,
        "reversibility": reversibility,
        "activation_level": activation_level,
        "strategies": strategies,
        "send_blocked": True,
        "draft_saved": True,
        "delay_seconds": delay,
        "delay_label": "睡一晚再决定" if delay >= 12 * 3600 else f"先延迟 {delay // 60} 分钟",
        "substitute_action": SUBSTITUTE_ACTIONS.get(urge_type.upper()),
        "friction_steps": [
            "退出当前聊天或发布界面",
            "取消快捷发送",
            "把内容复制到私人草稿",
            "把这个决定转成一个待复核任务",
        ],
        "recheck_prompt": "延迟结束后，如果冲动仍然高于 6/10，先联系支持者，今天不发送。",
        "user_can_override": True,
        "override_note": "你仍然可以选择发送；系统只增加一步，不替你做决定。",
        "next_action": "SAFE_COREGULATION_ROUTER" if urgency >= 7 else "POST_ACTIVATION_RECOVERY_PLANNER",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-33 safe_coregulation_router
# ─────────────────────────────────────────────────────────────────────────────

SUPPORT_TYPES: dict[str, str] = {
    "LISTEN": "只听十分钟，不分析、不说教",
    "PRESENCE": "陪你待在安全的空间里",
    "GROUNDING": "提醒你放慢动作、离开危险环境",
    "DELAY_SUPPORT": "帮你延迟发送或延迟重大决定",
    "PRAYER": "在你主动选择时一起祷告",
    "PRACTICAL_HELP": "协助交通、照看孩子或处理紧急现实事务",
    "PROFESSIONAL_SUPPORT": "转向牧者、辅导者、咨询师、医疗或危机资源",
}
DEFAULT_SHARING_SCOPE = "activation_level_and_support_request_only"


class SupportPerson(BaseModel):
    support_person_id: str
    relationship_role: str = Field(max_length=40)
    allowed_support_types: list[str] = Field(default_factory=list, max_length=7)
    available_now: bool = True
    content_sharing_scope: str = DEFAULT_SHARING_SCOPE
    person_has_consented: bool = False
    user_has_consented: bool = False
    is_conflict_party: bool = False

    @field_validator("allowed_support_types")
    @classmethod
    def known_types(cls, value: list[str]) -> list[str]:
        unknown = [item for item in value if item not in SUPPORT_TYPES]
        if unknown:
            raise ValueError(f"unknown support type: {','.join(unknown)}")
        return value


def route_coregulation(
    *,
    requested_support: list[str],
    contacts: list[SupportPerson],
    activation_level: int | None = None,
    spiritual_framework: str = "user_choice",
) -> dict[str, Any]:
    """Only dual-consented contacts, only the support types they agreed to, minimum content."""
    unknown = [item for item in requested_support if item not in SUPPORT_TYPES]
    if unknown:
        raise ValueError(f"unknown support type: {','.join(unknown)}")

    eligible: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []
    for contact in contacts:
        if not (contact.person_has_consented and contact.user_has_consented):
            excluded.append({"support_person_id": contact.support_person_id, "reason": "DUAL_CONSENT_MISSING"})
            continue
        if contact.is_conflict_party:
            excluded.append({"support_person_id": contact.support_person_id, "reason": "IS_CONFLICT_PARTY"})
            continue
        matched = [item for item in requested_support if item in contact.allowed_support_types]
        if not matched:
            excluded.append({"support_person_id": contact.support_person_id, "reason": "SUPPORT_TYPE_NOT_AGREED"})
            continue
        if not contact.available_now:
            excluded.append({"support_person_id": contact.support_person_id, "reason": "NOT_AVAILABLE_NOW"})
            continue
        eligible.append({
            "support_person_id": contact.support_person_id,
            "relationship_role": contact.relationship_role,
            "matched_support_types": matched,
            "content_sharing_scope": contact.content_sharing_scope or DEFAULT_SHARING_SCOPE,
        })

    if "PRAYER" in requested_support and spiritual_framework == "neutral":
        requested_support = [item for item in requested_support if item != "PRAYER"]

    return {
        "plan_id": f"cor_{uuid.uuid4().hex[:10]}",
        "status": "READY" if eligible else "NO_ELIGIBLE_CONTACT",
        "requested_support": requested_support,
        "eligible_contacts": eligible,
        "excluded_contacts": excluded,
        "message_draft": "我现在情绪比较高，想请你听我说十分钟，不需要建议。",
        "message_auto_sent": False,
        "shared_content": {
            "activation_level": activation_level,
            "support_request": requested_support,
            "event_details_shared": False,
        },
        "fallback": (
            ["写给自己的信", "延迟到明天", "使用专业或危机支持资源"] if not eligible else []
        ),
        "principles": [
            "求助不是不独立；在强烈激活时借助可信赖的人恢复选择能力是成熟行为。",
            "联系人不会被默认加入情绪急救名单，他们需要知道自己承担的角色和边界。",
            "系统不会替你发送消息，也不会把事件细节告诉对方。",
        ],
        "next_action": "POST_ACTIVATION_RECOVERY_PLANNER",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-34 post_activation_recovery_planner
# ─────────────────────────────────────────────────────────────────────────────

RECOVERY_HORIZONS: tuple[tuple[str, str], ...] = (
    ("NEXT_10_MIN", "接下来十分钟"),
    ("NEXT_2_HOURS", "接下来两小时"),
    ("NEXT_24_72_HOURS", "接下来二十四至七十二小时"),
)


def plan_recovery(
    *,
    activation_peak: int,
    activation_current: int,
    harmful_action_occurred: bool = False,
    pause_protocol_completed: bool = False,
    relationship_repair_needed: bool = False,
    relationship_safety: str = "STANDARD",
    sleep_deprived: bool = False,
    work_required_within_hours: int | None = None,
    spiritual_framework: str = "user_choice",
) -> dict[str, Any]:
    """Plan the four recoveries separately across three horizons (mirrors Batch 3 metrics)."""
    ten_minutes = ["确认现在的环境是安全的", "停止任何还在进行的伤害性行为", "喝水、坐下或站起来活动一下"]
    if not pause_protocol_completed:
        ten_minutes.append("先离开刺激源十分钟")
    ten_minutes.append("把已经写好的内容保存为草稿，不发送")

    two_hours = ["把事实和解释分开写下来", "决定是否需要找人陪一会儿", "先不进行高强度对话"]
    if sleep_deprived:
        two_hours.append("如果可以，先补一段睡眠再处理这件事")
    if work_required_within_hours is not None and work_required_within_hours <= 2:
        two_hours.append("只处理接下来两小时必须完成的事，其余往后放")

    long_horizon = ["处理还没消化的情绪", "复盘触发点与这次暂停是否有效", "更新旧模式预警"]
    if relationship_repair_needed and relationship_safety != "CAUTION":
        long_horizon.append("决定是否修复，以及你愿意承担哪一部分")
    if relationship_safety == "CAUTION":
        long_horizon.append("关系安全存疑时优先保护自己，不安排对质或修复")
    if harmful_action_occurred:
        long_horizon.append("对已经造成的影响做具体更正，而不是只说对不起")

    optional_spiritual = []
    if spiritual_framework != "neutral":
        optional_spiritual = [
            "如果你愿意，可以把这份情绪原样带到神面前，不必先把它变好听。",
            "祷告是可选的支持，不用来替代安全、医疗或专业帮助，也不要求你立刻停止难过。",
        ]

    return {
        "recovery_plan_id": f"rec_{uuid.uuid4().hex[:10]}",
        "activation_peak": activation_peak,
        "activation_current": activation_current,
        "horizons": [
            {"code": "NEXT_10_MIN", "label": "接下来十分钟", "actions": ten_minutes},
            {"code": "NEXT_2_HOURS", "label": "接下来两小时", "actions": two_hours},
            {"code": "NEXT_24_72_HOURS", "label": "接下来二十四至七十二小时", "actions": long_horizon},
        ],
        "recovery_kinds": {
            "behavioral": "停止伤害性行为，并保持停止",
            "functional": "恢复睡眠、进食、工作等基本功能",
            "emotional": "让情绪回到你自己定义的可承受范围，不要求归零",
            "relational": "在安全的前提下澄清、道歉、补救或重建边界",
        },
        "optional_spiritual_support": optional_spiritual,
        "not_required": [
            "不要求你立刻不难过。",
            "不要求你立刻原谅或立刻恢复联系。",
        ],
        "next_action": "RELAPSE_REHEARSAL",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-35 relapse_rehearsal_if_then_simulator
# ─────────────────────────────────────────────────────────────────────────────

REHEARSAL_LEVELS: dict[int, dict[str, Any]] = {
    1: {"name": "低压力近迁移", "description": "同一关系、相似触发、对方反应较温和"},
    2: {"name": "中压力变化", "description": "只改变一个变量：对方不接受边界、延迟回应、公开场合或你处于疲劳状态"},
    3: {"name": "高压力稳定性", "description": "权力差、重复越界、属灵化施压、公开羞辱"},
}
LEVEL_2_VARIABLES: tuple[str, ...] = (
    "对方不接受边界", "对方延迟回应", "事情发生在公开场合", "你处于疲劳状态",
)


def build_rehearsal(
    *,
    level: int,
    trigger_description: str,
    earliest_body_signal: str,
    planned_action: str,
    fallback_contact: str | None = None,
    changed_variable: str | None = None,
    violence_context: bool = False,
) -> dict[str, Any]:
    """Rehearse the old pattern reappearing — as an event to plan for, not as an identity."""
    if level not in REHEARSAL_LEVELS:
        raise ValueError(f"unknown rehearsal level: {level}")
    if violence_context:
        return {
            "rehearsal_id": f"reh_{uuid.uuid4().hex[:10]}",
            "status": "NOT_APPLICABLE_SAFETY",
            "cards": [],
            "note": "存在暴力风险的情境不进入普通演练，改由安全与保护流程处理。",
            "next_action": "ROUTE_TO_SAFETY_SUPPORT",
        }
    if level == 2 and changed_variable and changed_variable not in LEVEL_2_VARIABLES:
        raise ValueError("level 2 rehearsal changes exactly one listed variable")

    for text in (trigger_description, planned_action):
        validate_safe_text(text)

    cards = [
        {
            "if": f"如果我在{trigger_description}之后注意到{earliest_body_signal}，并且开始想立刻回应，",
            "then": f"那么我{planned_action}。",
            "kind": "PRIMARY",
        },
        {
            "if": "如果十分钟后冲动仍然高于 6/10，",
            "then": (
                f"那么我联系{fallback_contact}，今天不发送公开回应。"
                if fallback_contact else "那么我今天不发送公开回应，把内容留在草稿里。"
            ),
            "kind": "PAUSE_FAILED",
        },
        {
            "if": "如果我已经发送了伤害性内容，",
            "then": "那么我停止继续争辩，保留事实记录，等恢复后做具体更正和道歉。",
            "kind": "ALREADY_HAPPENED",
        },
    ]
    if level >= 2:
        cards.append({
            "if": f"如果{changed_variable or '对方不接受我的边界'}，",
            "then": "那么我重复一次我的界限，不升级冲突，也不立刻放弃这个界限。",
            "kind": "SINGLE_VARIABLE_CHANGE",
        })
    if level == 3:
        cards.append({
            "if": "如果对方用属灵理由施压，或在公开场合让我难堪，",
            "then": "那么我先保护自己，把话题延后，并在事后找一位安全的人一起复盘。",
            "kind": "HIGH_PRESSURE",
        })

    return {
        "rehearsal_id": f"reh_{uuid.uuid4().hex[:10]}",
        "status": "READY",
        "level": level,
        "level_name": REHEARSAL_LEVELS[level]["name"],
        "level_description": REHEARSAL_LEVELS[level]["description"],
        "changed_variable": changed_variable,
        "cards": cards,
        "language_rules": [
            "这是「旧模式复现演练」，不是把你标记为复发者。",
            "复现一次不取消你已经做到的改变。",
        ],
        "next_action": "TRACK_IN_REAL_LIFE_EVENTS",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 状态机与自描述
# ─────────────────────────────────────────────────────────────────────────────

WORKFLOW_NODES: tuple[str, ...] = (
    "EM-28_emotion_labeling", "EM-29_body_signal_scanner", "EM-30_trigger_early_warning",
    "EM-31_sacred_pause", "EM-32_impulse_interrupter", "EM-33_coregulation_router",
    "EM-34_recovery_planner", "EM-35_relapse_rehearsal",
)

STATE_MACHINE: tuple[tuple[str, str], ...] = (
    ("SESSION_STARTED", "BODY_SCANNED"),
    ("BODY_SCANNED", "EXIT_TO_MEDICAL_SAFETY"),
    ("BODY_SCANNED", "EMOTIONS_LABELLED"),
    ("EMOTIONS_LABELLED", "TRIGGER_MATCHED"),
    ("TRIGGER_MATCHED", "AWARENESS_ONLY"),
    ("TRIGGER_MATCHED", "PAUSE_PROTOCOL_ACTIVE"),
    ("TRIGGER_MATCHED", "IMPULSE_GUARDED"),
    ("TRIGGER_MATCHED", "CRISIS_ROUTED"),
    ("PAUSE_PROTOCOL_ACTIVE", "IMPULSE_GUARDED"),
    ("IMPULSE_GUARDED", "COREGULATION_REQUESTED"),
    ("COREGULATION_REQUESTED", "RECOVERY_PLANNED"),
    ("PAUSE_PROTOCOL_ACTIVE", "RECOVERY_PLANNED"),
    ("IMPULSE_GUARDED", "RECOVERY_PLANNED"),
    ("RECOVERY_PLANNED", "REHEARSAL_BUILT"),
    ("REHEARSAL_BUILT", "TRACKED_IN_REAL_LIFE"),
)


def describe_regulation_engine() -> dict[str, Any]:
    return {
        "module": "emotional_maturity_regulation",
        "short_name": "EMD-OS Batch 4",
        "batch": 4,
        "skills": list(WORKFLOW_NODES),
        "session_modes": list(SESSION_MODES),
        "activation_bands": {
            "GREEN": "0–3，能思考和选择，没有紧急行动冲动",
            "AMBER": "4–6，身体激活明显，仍能按短步骤行动",
            "RED": "7–8，或存在强烈的辱骂、断联、冲动发送、辞职、破坏物品等冲动",
            "CRISIS": "9–10 且无法保证安全，或存在自伤、伤人、暴力、危险驾驶风险",
        },
        "emotion_lexicon": {code: entry["label"] for code, entry in EMOTION_LEXICON.items()},
        "confusion_pairs": [{"a": a, "b": b, "distinction": note} for a, b, note in CONFUSION_PAIRS],
        "early_body_signals": EARLY_BODY_SIGNALS,
        "medical_red_flags": MEDICAL_RED_FLAGS,
        "pause_levels": PAUSE_LEVELS,
        "reversibility_classes": list(REVERSIBILITY_CLASSES),
        "support_types": SUPPORT_TYPES,
        "rehearsal_levels": {str(key): value for key, value in REHEARSAL_LEVELS.items()},
        "does_not": [
            "不把候选情绪写成事实",
            "不把愤怒自动解释为次级情绪",
            "不在高激活时做五层情绪深挖",
            "不把身体信号解释为焦虑或任何诊断",
            "不用经文或祷告要求用户停止悲伤、立刻原谅或恢复联系",
            "不替用户发送消息，也不默认把联系人加入急救名单",
        ],
        "engine_version": ENGINE_VERSION,
        "rule_version": RULE_VERSION,
        "state_machine": [{"from": source, "to": target} for source, target in STATE_MACHINE],
    }
