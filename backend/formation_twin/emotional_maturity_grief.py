"""EMD-OS Batch 7: grief, limits, sabbath and spiritual-bypassing governance (EM-54 ~ EM-61).

    EM-54 丧失与影响地图 → EM-55 哀伤与哀歌陪伴 → EM-56 控制／影响／责任校准
    → EM-57 模糊丧失与未完成告别 → EM-58 属灵逃避检测 → EM-59 交托与纪念仪式
    → EM-60 每日暂停与安息节奏 → EM-61 14/30/90 整合评估

八个必须严格区分的概念（由代码强制）：

1. 接纳 ≠ 认同：承认已经发生，不代表认为它是对的。
2. 交托 ≠ 消极放弃：放下无法控制的结果，同时继续做自己仍有责任做的事。
3. 哀伤 ≠ 属灵失败：仍在流泪或困惑，不代表缺乏信心或不够成熟。
4. 安息 ≠ 逃避责任：安息之后能更自由地承担该承担的。
5. 停止工作 ≠ 恢复：行为停止、身体恢复、注意力脱离、情绪恢复、休息负罪感、重新承担能力要分别测量。
6. 宽恕 ≠ 结束哀伤：宽恕不要求你不再难过。
7. 意义 ≠ 过早意义化：意义只能由用户自己在时间中形成，系统不代神宣告理由。
8. 纪念 ≠ 迷信：仪式是可选的表达形式，不产生任何超自然效力或交换条件。
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from .emotional_maturity import UnsafeContentError, validate_safe_text


ENGINE_VERSION = "emd-grief-engine-1.0"
RULE_VERSION = "emd-grief-rules-1.0"

# ── 丧失与整合证据等级 ───────────────────────────────────────────────────────
GRIEF_INTEGRATION_LEVELS: dict[str, str] = {
    "GI0": "证据不足：只有抽象表达",
    "GI1": "命名丧失：说得出失去了谁、什么或哪一种未来",
    "GI2": "识别次生影响：看见角色、身份、日常、社区或梦想的连带丧失",
    "GI3": "责任与有限分离：能区分仍应承担的责任与无法控制的结果",
    "GI4": "容纳哀伤并采取现实行动：哀伤、求助、纪念、设立边界或完成必要收尾",
    "GI5": "建立恢复和安息节奏：不再只依靠崩溃后的被迫停止",
    "GI6": "纵向整合：能继续生活与承担责任，同时允许哀伤波动和纪念存在",
}
GI_ORDER: tuple[str, ...] = ("GI0", "GI1", "GI2", "GI3", "GI4", "GI5", "GI6")
GI_RANK: dict[str, int] = {level: index for index, level in enumerate(GI_ORDER)}

EIGHT_DISTINCTIONS: tuple[tuple[str, str], ...] = (
    ("ACCEPTANCE_IS_NOT_APPROVAL", "接纳是承认已经发生，不是认为这件事是好的或公义的"),
    ("SURRENDER_IS_NOT_PASSIVITY", "交托是放下无法控制的结果，不是停止做自己仍有责任做的事"),
    ("GRIEF_IS_NOT_SPIRITUAL_FAILURE", "仍在流泪或困惑，不代表缺乏信心或属灵不成熟"),
    ("REST_IS_NOT_IRRESPONSIBILITY", "安息之后能更自由地承担该承担的责任"),
    ("STOPPING_IS_NOT_RECOVERY", "停止工作与真正恢复是两件事，需要分别测量"),
    ("FORGIVENESS_DOES_NOT_END_GRIEF", "宽恕不要求你不再难过"),
    ("MEANING_IS_NOT_PREMATURE_MEANING", "意义由你自己在时间中形成，系统不代神宣告理由"),
    ("MEMORIAL_IS_NOT_SUPERSTITION", "仪式是可选的表达形式，不产生超自然效力或交换条件"),
)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _now(now: datetime | None = None) -> datetime:
    return now or datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────────────────────
# EM-54 loss_grief_event_mapper
# ─────────────────────────────────────────────────────────────────────────────

LOSS_TYPES: dict[str, str] = {
    "DEATH": "亲人或朋友离世",
    "RELATIONSHIP_END": "关系结束或断裂",
    "HEALTH": "健康、身体功能或精力的丧失",
    "ROLE_OR_WORK": "角色、职位或工作的丧失",
    "COMMUNITY": "群体、教会或归属的丧失",
    "FUTURE_HOPED_FOR": "曾经期待的未来落空",
    "TRUST_OR_SAFETY": "信任感或安全感的丧失",
    "FAITH_EXPECTATION": "对信仰经历或答案的期待落空",
    "OTHER": "其他",
}

SECONDARY_LOSS_DOMAINS: tuple[str, ...] = (
    "DAILY_ROUTINE", "IDENTITY", "ROLE", "COMMUNITY", "FINANCE", "PLANS_AND_DREAMS",
    "PHYSICAL_SPACE", "SHARED_LANGUAGE", "SPIRITUAL_PRACTICE",
)


def map_loss(
    *,
    loss_type: str,
    what_was_lost: str,
    secondary_losses: list[str] | None = None,
    concrete_impacts: list[str] | None = None,
    is_ambiguous: bool = False,
    occurred_at: datetime | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Name the primary loss, then the secondary losses that usually go unnamed."""
    if loss_type not in LOSS_TYPES:
        raise ValueError(f"unknown loss type: {loss_type}")
    validate_safe_text(what_was_lost)
    unknown = [item for item in (secondary_losses or []) if item not in SECONDARY_LOSS_DOMAINS]
    if unknown:
        raise ValueError(f"unknown secondary loss domain: {','.join(unknown)}")

    moment = _now(now)
    named = bool(what_was_lost.strip())
    secondary = list(secondary_losses or [])
    impacts = list(concrete_impacts or [])

    level = "GI0"
    if named:
        level = "GI1"
    if named and secondary:
        level = "GI2"

    return {
        "loss_id": _new_id("los"),
        "loss_type": loss_type,
        "loss_type_label": LOSS_TYPES[loss_type],
        "what_was_lost": what_was_lost,
        "secondary_losses": [{"domain": item} for item in secondary],
        "concrete_impacts": impacts,
        "is_ambiguous": is_ambiguous,
        "occurred_at": occurred_at,
        "days_since": (moment - occurred_at).days if occurred_at else None,
        "integration_level": level,
        "integration_level_label": GRIEF_INTEGRATION_LEVELS[level],
        "no_timeline_expected": "哀伤没有标准时长；系统不会要求你在某个时间点「走出来」。",
        "next_action": "AMBIGUOUS_LOSS_PROCESSOR" if is_ambiguous else "GRIEF_COMPANION",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-55 grief_lament_process_companion
# ─────────────────────────────────────────────────────────────────────────────

GRIEF_EMOTIONS: tuple[str, ...] = (
    "悲痛", "愤怒", "迷惘", "失望", "怀疑", "无力", "空洞", "怀念", "解脱", "内疚",
)
LAMENT_MOVEMENTS: tuple[tuple[str, str], ...] = (
    ("ADDRESS", "称呼：向谁说这番话"),
    ("COMPLAINT", "陈述：实际发生了什么，我现在怎么样"),
    ("ASK", "求问：我想问什么，包括没有答案的问题"),
    ("TRUST_OR_UNRESOLVED", "信靠或悬置：如果现在说不出信靠，可以停在这里"),
)


def accompany_grief(
    *,
    named_emotions: list[str],
    wants_lament: bool = False,
    spiritual_framework: str = "user_choice",
    days_since_loss: int | None = None,
) -> dict[str, Any]:
    """Grief is accompanied, not corrected. A lament may end unresolved."""
    for emotion in named_emotions:
        validate_safe_text(emotion)

    lament = []
    if wants_lament and spiritual_framework != "neutral":
        lament = [{"code": code, "prompt": text} for code, text in LAMENT_MOVEMENTS]

    return {
        "companion_id": _new_id("grf"),
        "named_emotions": named_emotions,
        "common_grief_emotions": list(GRIEF_EMOTIONS),
        "all_emotions_allowed": True,
        "lament_structure": lament,
        "lament_may_end_unresolved": True,
        "days_since_loss": days_since_loss,
        "never_says": [
            "不会说你应该已经好起来了。",
            "不会因为你仍在流泪或困惑，就说你缺乏信心、没有宽恕或属灵不成熟。",
            "不会要求你现在就找到这件事的意义。",
        ],
        "offers": [
            "把现在的感受原样说出来",
            "写一段没有结论的哀歌",
            "找一个安全的人陪你待一会儿",
            "如果需要，联系专业或牧养支持",
        ],
        "next_action": "CALIBRATE_CONTROL_AND_LIMITS",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-56 control_influence_limit_calibrator
# ─────────────────────────────────────────────────────────────────────────────

CONTROL_BUCKETS: tuple[tuple[str, str], ...] = (
    ("MY_RESPONSIBILITY", "我确实应当承担的"),
    ("MY_CHOICE", "我仍然可以选择的"),
    ("MY_INFLUENCE", "我可以影响但不能决定的"),
    ("SHARED", "需要双方或多方共同承担的"),
    ("NOT_CONTROLLABLE", "我无法控制的结果"),
)

_PASSIVE_SURRENDER = re.compile(
    r"(一切交给神就(不用|不需要)|反正都是神的旨意.{0,6}(不用|不必)(努力|治疗|沟通)|只要祷告就(不用|不需要))"
)


def calibrate_control(
    *,
    buckets: dict[str, list[str]],
    still_owed_actions: list[str] | None = None,
    surrender_statement: str | None = None,
) -> dict[str, Any]:
    """Sort reality into five buckets. Surrender never empties the responsibility bucket."""
    unknown = [key for key in buckets if key not in dict(CONTROL_BUCKETS)]
    if unknown:
        raise ValueError(f"unknown control bucket: {','.join(unknown)}")
    for entries in buckets.values():
        for entry in entries:
            validate_safe_text(entry)
    if surrender_statement:
        validate_safe_text(surrender_statement)
        if _PASSIVE_SURRENDER.search(surrender_statement):
            raise UnsafeContentError("this is avoidance framed as surrender")

    responsibilities = buckets.get("MY_RESPONSIBILITY", [])
    uncontrollable = buckets.get("NOT_CONTROLLABLE", [])
    outstanding = list(still_owed_actions or [])

    level = "GI2"
    if responsibilities and uncontrollable:
        level = "GI3"

    return {
        "calibration_id": _new_id("ctl"),
        "buckets": [
            {"code": code, "label": label, "entries": buckets.get(code, [])}
            for code, label in CONTROL_BUCKETS
        ],
        "integration_level": level,
        "surrender_is_not_passivity": (
            "交托是放下你无法控制的结果；它不取消你仍然可以做的治疗、沟通、求助或履责。"
        ),
        "outstanding_responsibilities": outstanding,
        "warning": (
            "这些仍然属于你可以做的事，交托不应该被用来跳过它们。" if outstanding else None
        ),
        "acceptance_is_not_approval": "你可以接受事情已经发生，同时仍然认为它是错的，并保留边界与现实追责。",
        "next_action": "DISCERN_SPIRITUAL_BYPASSING",
        "rule_version": RULE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-57 ambiguous_loss_unfinished_goodbye_processor
# ─────────────────────────────────────────────────────────────────────────────

AMBIGUOUS_LOSS_KINDS: dict[str, str] = {
    "PHYSICALLY_ABSENT_PSYCHOLOGICALLY_PRESENT": "人不在了，但仍持续占据心理空间",
    "PHYSICALLY_PRESENT_PSYCHOLOGICALLY_ABSENT": "人还在，但关系或认知已经改变",
    "NO_ANSWER_EVER": "永远得不到解释或答案",
    "NO_FORMAL_GOODBYE": "没有机会正式告别",
    "UNRESOLVED_ESTRANGEMENT": "关系断裂但没有结论",
    "UNCERTAIN_OUTCOME": "结果仍未确定，无法开始或结束哀伤",
}


def process_ambiguous_loss(
    *,
    kind: str,
    what_is_unresolved: str,
    wants_symbolic_goodbye: bool = False,
    contact_is_safe: bool = False,
) -> dict[str, Any]:
    """Ambiguous loss has no closure to manufacture; the goal is to live with the open ending."""
    if kind not in AMBIGUOUS_LOSS_KINDS:
        raise ValueError(f"unknown ambiguous loss kind: {kind}")
    validate_safe_text(what_is_unresolved)

    options = [
        "把没有答案的问题写下来，不强行回答",
        "为这段关系或这个未来写一封不寄出的信",
        "设定一个只属于自己的纪念时刻",
        "允许在纪念日出现波动，并提前安排支持",
    ]
    if wants_symbolic_goodbye:
        options.insert(0, "设计一个象征性的告别，不需要对方参与")
    if contact_is_safe:
        options.append("在你自己愿意的时候，考虑一次有边界的联系尝试")

    return {
        "process_id": _new_id("amb"),
        "kind": kind,
        "kind_label": AMBIGUOUS_LOSS_KINDS[kind],
        "what_is_unresolved": what_is_unresolved,
        "closure_not_required": "模糊丧失通常没有「结案」；目标是能与这个未完成共处，而不是逼自己了结。",
        "options": options,
        "not_required": [
            "不要求你原谅",
            "不要求你恢复联系",
            "不要求你为这件事找到理由",
        ],
        "anniversary_note": "纪念日、节日和相似场景出现悲伤反弹是常见的，不代表退步。",
        "next_action": "DESIGN_MEMORIAL_RITUAL" if wants_symbolic_goodbye else "DISCERN_SPIRITUAL_BYPASSING",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-58 spiritual_bypassing_discernment_guard
# ─────────────────────────────────────────────────────────────────────────────

BYPASSING_CODES: dict[str, str] = {
    "PREMATURE_MEANING": "过早意义化：还在痛里就被要求说出「这件事的功课」",
    "EMOTION_SUPPRESSION": "情绪压抑：用「要常常喜乐」压下合理的悲伤或愤怒",
    "RESPONSIBILITY_AVOIDANCE": "责任回避：以交托为名跳过治疗、沟通或赔偿",
    "FORCED_FORGIVENESS": "强迫宽恕：要求立刻原谅并恢复关系",
    "DIVINE_CERTAINTY_CLAIM": "宣称神意：断言神一定是为了什么才允许这件事",
    "SUFFERING_AS_PROOF": "以受苦为荣：把继续硬撑当作属灵成熟",
    "PRAYER_REPLACES_HELP": "以祷告替代帮助：用祷告取代医疗、安全或专业支持",
}
_BYPASS_PATTERNS: tuple[tuple[str, str], ...] = (
    ("PREMATURE_MEANING", r"(这件事一定有(神的)?美意|你要学的功课就是|凡事都有原因，所以你要)"),
    ("EMOTION_SUPPRESSION", r"(要常常喜乐.{0,8}(不要|别)(难过|生气)|基督徒不该(难过|生气|软弱)|靠着信心就不会难过)"),
    ("RESPONSIBILITY_AVOIDANCE", r"(交给神就(不用|不需要)(治疗|沟通|道歉|赔)|不用看医生.{0,6}祷告就)"),
    ("FORCED_FORGIVENESS", r"(必须(立刻|马上)原谅|不原谅就(不属灵|得不到)|你要(赶快)?原谅(他|她)才)"),
    ("DIVINE_CERTAINTY_CLAIM", r"(神(就是|一定)(为了|要)让你|这是神(给你的)?(管教|惩罚)|神告诉你)"),
    ("SUFFERING_AS_PROOF", r"(能撑住才是(真正)?(属灵|成熟)|越苦越属灵)"),
    ("PRAYER_REPLACES_HELP", r"(只要祷告就(够了|可以了).{0,8}(不用|不需要)(看医生|求助|报警))"),
)
_BYPASS_RE = tuple((code, re.compile(pattern)) for code, pattern in _BYPASS_PATTERNS)

HEALTHY_SPIRITUAL_OPTIONS: tuple[str, ...] = (
    "静默祷告",
    "诗篇默想（包括哀歌类诗篇）",
    "与可信赖的肢体一起祷告",
    "把情绪原样带到神面前",
)


def discern_spiritual_bypassing(text: str, *, spiritual_framework: str = "user_choice") -> dict[str, Any]:
    """Flag spiritualised suppression and offer the honest alternative — without banning faith."""
    detected = [
        {"code": code, "description": BYPASSING_CODES[code], "matched": match.group(0)}
        for code, pattern in _BYPASS_RE
        if (match := pattern.search(text or ""))
    ]

    reframes = {
        "PREMATURE_MEANING": "现在可以只说发生了什么和你的感受；意义可以以后再说，也可以一直不说。",
        "EMOTION_SUPPRESSION": "悲伤和愤怒本身不是不信；诗篇里有大量哀歌。",
        "RESPONSIBILITY_AVOIDANCE": "交托与行动可以同时存在：继续治疗、沟通或赔偿，同时放下结果。",
        "FORCED_FORGIVENESS": "宽恕是过程，不能被时间表逼迫，也不取消边界。",
        "DIVINE_CERTAINTY_CLAIM": "系统不会宣称神为什么允许这件事，也不会转述神对你说的话。",
        "SUFFERING_AS_PROOF": "硬撑不是成熟；承认有限并求助同样是成熟。",
        "PRAYER_REPLACES_HELP": "祷告是可选的支持，不替代医疗、安全或专业帮助。",
    }

    return {
        "discernment_id": _new_id("byp"),
        "flags": detected,
        "reframes": [{"code": item["code"], "reframe": reframes[item["code"]]} for item in detected],
        "healthy_spiritual_options": (
            list(HEALTHY_SPIRITUAL_OPTIONS) if spiritual_framework != "neutral" else []
        ),
        "faith_is_not_banned": "本检查不是禁止属灵操练，而是防止属灵语言被用来压抑现实。",
        "next_action": "DESIGN_MEMORIAL_RITUAL",
        "rule_version": RULE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-59 surrender_release_memorial_ritual_designer
# ─────────────────────────────────────────────────────────────────────────────

RITUAL_KINDS: dict[str, str] = {
    "RELEASE": "交托：把无法控制的结果说出来并放下",
    "MEMORIAL": "纪念：为失去的人或事保留一个位置",
    "FAREWELL": "告别：为没有正式结束的关系做一个象征性收尾",
    "GRATITUDE": "感念：说出仍然值得记得的部分",
    "BOUNDARY_MARKER": "界标：标记一个阶段结束和新的安排开始",
}
_RITUAL_MAGIC = re.compile(
    r"(这样做(就|一定)(会|能)(痊愈|复合|得到)|做完.{0,8}(神就|就一定|就会)|献上.{0,8}换取)"
)


def design_ritual(
    *,
    kind: str,
    what_it_marks: str,
    elements: list[str] | None = None,
    spiritual_framework: str = "user_choice",
    include_others: bool = False,
) -> dict[str, Any]:
    """Rituals are optional, user-authored and explicitly non-transactional."""
    if kind not in RITUAL_KINDS:
        raise ValueError(f"unknown ritual kind: {kind}")
    validate_safe_text(what_it_marks)
    for element in elements or []:
        validate_safe_text(element)
        if _RITUAL_MAGIC.search(element):
            raise UnsafeContentError("ritual must not promise supernatural results or trade with God")
    if _RITUAL_MAGIC.search(what_it_marks):
        raise UnsafeContentError("ritual must not promise supernatural results or trade with God")

    default_elements = {
        "RELEASE": ["写下我无法控制的部分", "读出来一次", "决定接下来我仍然会做的一件事"],
        "MEMORIAL": ["选一个具体物件或地点", "说出一段回忆", "决定以后什么时候再来"],
        "FAREWELL": ["写一封不寄出的信", "读一遍", "选择保留或封存"],
        "GRATITUDE": ["写下三件仍然值得记得的事", "说给一个安全的人听"],
        "BOUNDARY_MARKER": ["写下这个阶段结束了什么", "写下接下来的新安排"],
    }[kind]

    return {
        "ritual_id": _new_id("rit"),
        "kind": kind,
        "kind_label": RITUAL_KINDS[kind],
        "what_it_marks": what_it_marks,
        "elements": list(elements or default_elements),
        "optional": True,
        "user_authored": True,
        "with_others": include_others,
        "not_magic": [
            "仪式不产生超自然效力，也不是与神交换条件。",
            "做完仪式不代表哀伤结束；情绪仍然可以回来。",
            "你可以修改、推迟或完全不做。",
        ],
        "spiritual_framework": spiritual_framework,
        "next_action": "BUILD_REST_RHYTHM",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-60 daily_office_sabbath_rhythm_architect
# ─────────────────────────────────────────────────────────────────────────────

RHYTHM_SLOTS: tuple[tuple[str, str], ...] = (
    ("MORNING_PAUSE", "早晨的一个短暂停"),
    ("MIDDAY_PAUSE", "中午的一个短暂停"),
    ("EVENING_REVIEW", "晚间的简短回顾"),
    ("WEEKLY_SABBATH", "每周一段真正停下来的时间"),
    ("DELIGHT", "定期安排一件让你欢欣的小事"),
    ("CONTEMPLATION", "安静与沉思的时间"),
)
REST_MEASURES: tuple[tuple[str, str], ...] = (
    ("BEHAVIOR_STOPPED", "行为停止：确实不再工作"),
    ("BODY_RECOVERED", "身体恢复：睡眠、进食、体力"),
    ("ATTENTION_DETACHED", "注意力脱离：不再反复查看或在脑中处理"),
    ("EMOTION_RECOVERED", "情绪恢复：紧绷感下降"),
    ("REST_GUILT", "休息负罪感：停下来时的自责程度"),
    ("CAPACITY_RESTORED", "重新承担责任的能力"),
)


def build_rest_rhythm(
    *,
    available_slots: list[str],
    weekly_sabbath_hours: int = 4,
    current_measures: dict[str, Any] | None = None,
    spiritual_framework: str = "user_choice",
) -> dict[str, Any]:
    """Rest is measured on six axes — stopping work is only the first one."""
    unknown = [item for item in available_slots if item not in dict(RHYTHM_SLOTS)]
    if unknown:
        raise ValueError(f"unknown rhythm slot: {','.join(unknown)}")
    measures = current_measures or {}

    scored = []
    for code, label in REST_MEASURES:
        value = measures.get(code)
        scored.append({
            "code": code, "label": label, "value": value,
            "status": "UNKNOWN" if value is None else ("CONCERN" if code == "REST_GUILT" and value >= 6 else "RECORDED"),
        })
    stopping_only = (
        measures.get("BEHAVIOR_STOPPED") in {True, 1}
        and not any(measures.get(code) for code, _ in REST_MEASURES if code not in {"BEHAVIOR_STOPPED", "REST_GUILT"})
    )

    plan = [
        {"slot": code, "label": label, "planned": code in available_slots}
        for code, label in RHYTHM_SLOTS
    ]
    if spiritual_framework == "neutral":
        plan = [item for item in plan if item["slot"] != "CONTEMPLATION"] + [
            {"slot": "CONTEMPLATION", "label": "安静与反思的时间", "planned": "CONTEMPLATION" in available_slots}
        ]

    return {
        "rhythm_id": _new_id("rst"),
        "plan": plan,
        "weekly_sabbath_hours": weekly_sabbath_hours,
        "rest_measures": scored,
        "stopping_is_not_recovery": stopping_only,
        "stopping_note": (
            "你已经停下工作，但注意力和情绪还没有真正休息；这很常见，可以先只处理其中一项。"
            if stopping_only else None
        ),
        "rest_is_not_irresponsibility": "安息的目的不是逃避责任，而是让你之后能更自由地承担该承担的。",
        "start_small": "从一个可完成的槽位开始；节奏比强度更重要。",
        "next_action": "EVALUATE_REST_AND_GRIEF_INTEGRATION",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-61 rest_grief_limit_integration_evaluator
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_integration(
    *,
    day: int,
    loss_named: bool = False,
    secondary_losses_named: int = 0,
    responsibility_separated: bool = False,
    grief_expressed_events: int = 0,
    real_actions_taken: int = 0,
    rest_slots_kept: int = 0,
    rest_guilt_level: int | None = None,
    anniversary_reaction: bool = False,
    comparable_event_count: int = 0,
) -> dict[str, Any]:
    """Integration is about living with loss and limits — never about 'finishing' grief."""
    if day not in {14, 30, 90}:
        raise ValueError(f"unknown checkpoint day: {day}")

    level = "GI0"
    if loss_named:
        level = "GI1"
    if loss_named and secondary_losses_named >= 1:
        level = "GI2"
    if GI_RANK[level] >= GI_RANK["GI2"] and responsibility_separated:
        level = "GI3"
    if GI_RANK[level] >= GI_RANK["GI3"] and grief_expressed_events >= 1 and real_actions_taken >= 1:
        level = "GI4"
    if GI_RANK[level] >= GI_RANK["GI4"] and rest_slots_kept >= 2:
        level = "GI5"
    if day == 90 and GI_RANK[level] >= GI_RANK["GI5"] and comparable_event_count >= 2:
        level = "GI6"

    concerns: list[str] = []
    if rest_guilt_level is not None and rest_guilt_level >= 6:
        concerns.append("休息时的自责仍然很高，可以先只处理这一项。")
    if grief_expressed_events == 0 and real_actions_taken > 0:
        concerns.append("现实行动在进行，但哀伤几乎没有被表达过，注意不要用忙碌代替哀伤。")
    if rest_slots_kept == 0:
        concerns.append("暂停与安息还没有真正落地，节奏可能仍然依赖崩溃后的被迫停止。")

    return {
        "evaluation_id": _new_id("gie"),
        "day": day,
        "integration_level": level,
        "integration_level_label": GRIEF_INTEGRATION_LEVELS[level],
        "is_not_grief_completion": "这不是「哀伤完成度」，而是你与丧失、有限和现实生活相处的整合能力。",
        "concerns": concerns,
        "anniversary_note": (
            "纪念日出现悲伤反弹是常见的，不计为退步。" if anniversary_reaction else None
        ),
        "grief_may_fluctuate": True,
        "attribution_limits": [
            "这些变化与操练同时发生，但不能证明是操练造成的。",
            "环境、支持系统与身体状况的变化同样会影响结果。",
        ],
        "next_action": "UPDATE_FORMATION_TWIN",
        "rule_version": RULE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 状态机与自描述
# ─────────────────────────────────────────────────────────────────────────────

WORKFLOW_NODES: tuple[str, ...] = (
    "EM-54_loss_mapper", "EM-55_grief_companion", "EM-56_control_calibrator",
    "EM-57_ambiguous_loss", "EM-58_bypassing_guard", "EM-59_ritual_designer",
    "EM-60_rest_rhythm", "EM-61_integration_evaluator",
)

STATE_MACHINE: tuple[tuple[str, str], ...] = (
    ("LOSS_MAPPED", "GRIEF_ACCOMPANIED"),
    ("LOSS_MAPPED", "AMBIGUOUS_LOSS_PROCESSED"),
    ("GRIEF_ACCOMPANIED", "CONTROL_CALIBRATED"),
    ("AMBIGUOUS_LOSS_PROCESSED", "CONTROL_CALIBRATED"),
    ("CONTROL_CALIBRATED", "BYPASSING_CHECKED"),
    ("BYPASSING_CHECKED", "RITUAL_DESIGNED"),
    ("BYPASSING_CHECKED", "RITUAL_DECLINED"),
    ("RITUAL_DESIGNED", "REST_RHYTHM_BUILT"),
    ("RITUAL_DECLINED", "REST_RHYTHM_BUILT"),
    ("REST_RHYTHM_BUILT", "INTEGRATION_EVALUATED"),
    ("INTEGRATION_EVALUATED", "TWIN_UPDATED"),
)


def describe_grief_engine() -> dict[str, Any]:
    return {
        "module": "emotional_maturity_grief_and_rest",
        "short_name": "EMD-OS Batch 7",
        "batch": 7,
        "skills": list(WORKFLOW_NODES),
        "integration_levels": GRIEF_INTEGRATION_LEVELS,
        "eight_distinctions": [{"code": code, "meaning": text} for code, text in EIGHT_DISTINCTIONS],
        "loss_types": LOSS_TYPES,
        "secondary_loss_domains": list(SECONDARY_LOSS_DOMAINS),
        "grief_emotions": list(GRIEF_EMOTIONS),
        "lament_movements": [{"code": code, "prompt": text} for code, text in LAMENT_MOVEMENTS],
        "control_buckets": [{"code": code, "label": label} for code, label in CONTROL_BUCKETS],
        "ambiguous_loss_kinds": AMBIGUOUS_LOSS_KINDS,
        "bypassing_codes": BYPASSING_CODES,
        "ritual_kinds": RITUAL_KINDS,
        "rhythm_slots": [{"code": code, "label": label} for code, label in RHYTHM_SLOTS],
        "rest_measures": [{"code": code, "label": label} for code, label in REST_MEASURES],
        "does_not": [
            "不要求你在某个时间点走出哀伤",
            "不因为你仍在流泪或困惑就判定属灵失败",
            "不代神宣告这件事的理由",
            "不允许以交托为名跳过治疗、沟通或赔偿",
            "不把仪式说成有超自然效力或与神交换条件",
            "不把停止工作直接当作已经恢复",
        ],
        "engine_version": ENGINE_VERSION,
        "rule_version": RULE_VERSION,
        "state_machine": [{"from": source, "to": target} for source, target in STATE_MACHINE],
    }
