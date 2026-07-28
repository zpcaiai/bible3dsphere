"""EMD-OS Batch 5: family scripts, attachment and true-self integration (EM-36 ~ EM-43).

    EM-36 三代家庭图 → EM-37 家庭脚本／角色／三角关系 → EM-38 依恋激活循环
    → EM-39 自我分化训练 → EM-40 早年生存誓言重构 → EM-41 虚假自我面具
    → EM-42 真我罗盘 → EM-43 安全脆弱表达实验 → 回到 Batch 3 的现实验证

伦理边界（由代码强制）：

* 历史解释行为，但不替代责任：过去说明旧模式从何而来，成年后的行为仍由自己负责。
* 家庭成员不被远程诊断：只描述用户报告的可观察行为，不给父母、伴侣或教会领袖贴人格或疾病标签。
* 不诱导或制造童年记忆：材料必须标来源，`system_hypothesis` 永远不能写进家庭历史。
* 依恋模式不是永久人格类型：任何激活循环都必须绑定关系对象、触发条件、压力水平、时间范围与置信度。
* 「内在孩童」只是可选比喻，可换成「过去的自己」；拒绝这个练习不算抗拒成长。
* 饶恕、重新信任、恢复接触、关系和好是四件事；持续伤害中保持距离可能正是成熟边界。
"""
from __future__ import annotations

import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .emotional_maturity import UnsafeContentError, validate_safe_text


ENGINE_VERSION = "emd-family-engine-1.0"
RULE_VERSION = "emd-family-rules-1.0"

# ── 模式证据等级 ─────────────────────────────────────────────────────────────
FAMILY_PATTERN_LEVELS: dict[str, str] = {
    "FP0": "证据不足：只有抽象评价",
    "FP1": "单一事件线索",
    "FP2": "重复事件：至少两次不同时期的相似事件",
    "FP3": "多关系重复：同一脚本出现在多个成员或关系中",
    "FP4": "当下行为关联：家庭脚本与现实事件形成明确连接",
    "FP5": "纵向验证：在 30/90 天事件中持续验证并获用户确认",
}
FP_ORDER: tuple[str, ...] = ("FP0", "FP1", "FP2", "FP3", "FP4", "FP5")
FP_RANK: dict[str, int] = {level: index for index, level in enumerate(FP_ORDER)}
TWIN_WRITE_MINIMUM = "FP4"

# ── 记忆材料来源 ─────────────────────────────────────────────────────────────
MEMORY_SOURCES: dict[str, str] = {
    "direct_memory": "用户直接记忆",
    "family_account": "家人转述",
    "record_or_photo": "照片或记录",
    "vague_impression": "模糊印象",
    "system_hypothesis": "系统假设",
}
FACTUAL_MEMORY_SOURCES: frozenset[str] = frozenset({"direct_memory", "family_account", "record_or_photo"})

# ── 第三方诊断词拦截 ─────────────────────────────────────────────────────────
_THIRD_PARTY_DIAGNOSIS = re.compile(
    r"(自恋型人格|边缘型人格|反社会|人格障碍|精神病|抑郁症|双相|焦虑型依恋者|回避型依恋者|恶性控制者|NPD|BPD)"
)

# 饶恕四分法（Batch 6 会继续使用）
FORGIVENESS_DISTINCTIONS: tuple[tuple[str, str], ...] = (
    ("STOP_RETALIATION", "停止报复"),
    ("RELEASE_CONTROL", "释放自己对结果的执着"),
    ("FORGIVENESS", "饶恕"),
    ("REBUILD_TRUST", "重新信任"),
    ("RESUME_CONTACT", "恢复接触"),
    ("RECONCILIATION", "关系和好"),
)


def _now(now: datetime | None = None) -> datetime:
    return now or datetime.now(timezone.utc)


def validate_third_party_language(text: str) -> str:
    """A family member is described by observable behaviour, never diagnosed."""
    if _THIRD_PARTY_DIAGNOSIS.search(text or ""):
        raise UnsafeContentError("third-party diagnosis is not allowed")
    return validate_safe_text(text)


def evidence_level(
    *,
    concrete_events: int,
    distinct_periods: int,
    relationships_involved: int,
    linked_to_current_behavior: bool = False,
    longitudinally_confirmed: bool = False,
    user_confirmed: bool = False,
) -> str:
    """Deterministic FP level. Abstract statements never rise above FP0."""
    if concrete_events <= 0:
        return "FP0"
    level = "FP1"
    if concrete_events >= 2 and distinct_periods >= 2:
        level = "FP2"
    if relationships_involved >= 2 and FP_RANK[level] >= FP_RANK["FP2"]:
        level = "FP3"
    if linked_to_current_behavior and FP_RANK[level] >= FP_RANK["FP2"]:
        level = "FP4"
    if longitudinally_confirmed and user_confirmed and FP_RANK[level] >= FP_RANK["FP4"]:
        level = "FP5"
    return level


def may_write_to_twin(level: str) -> bool:
    if level not in FP_RANK:
        raise ValueError(f"unknown family pattern level: {level}")
    return FP_RANK[level] >= FP_RANK[TWIN_WRITE_MINIMUM]


# ─────────────────────────────────────────────────────────────────────────────
# EM-36 three_generation_genogram_mapper
# ─────────────────────────────────────────────────────────────────────────────

GENERATIONS: tuple[str, ...] = ("G1_GRANDPARENTS", "G2_PARENTS", "G3_SELF")
RELATIONSHIP_QUALITIES: tuple[str, ...] = (
    "CLOSE", "DISTANT", "CONFLICTUAL", "CUTOFF", "OVERINVOLVED", "SUPPORTIVE", "UNKNOWN",
)


class GenogramMember(BaseModel):
    member_id: str = Field(min_length=1, max_length=60)
    generation: str
    role_label: str = Field(min_length=1, max_length=40)
    observed_behaviors: list[str] = Field(default_factory=list, max_length=10)
    is_deceased: bool = False
    memory_source: str = "direct_memory"

    @field_validator("generation")
    @classmethod
    def known_generation(cls, value: str) -> str:
        if value not in GENERATIONS:
            raise ValueError(f"unknown generation: {value}")
        return value

    @field_validator("memory_source")
    @classmethod
    def known_source(cls, value: str) -> str:
        if value not in MEMORY_SOURCES:
            raise ValueError(f"unknown memory source: {value}")
        return value

    @model_validator(mode="after")
    def no_diagnosis(self):
        # 只保留可观察行为；姓名不入库，角色标签即身份
        validate_third_party_language(self.role_label)
        for behaviour in self.observed_behaviors:
            validate_third_party_language(behaviour)
        return self


class GenogramRelationship(BaseModel):
    from_member_id: str
    to_member_id: str
    quality: str = "UNKNOWN"
    evidence_events: int = Field(default=0, ge=0)

    @field_validator("quality")
    @classmethod
    def known_quality(cls, value: str) -> str:
        if value not in RELATIONSHIP_QUALITIES:
            raise ValueError(f"unknown relationship quality: {value}")
        return value


def build_genogram(
    members: list[GenogramMember],
    relationships: list[GenogramRelationship],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """A user-controlled three-generation map of observable behaviour — not a diagnosis chart."""
    moment = _now(now)
    known_ids = {member.member_id for member in members}
    dangling = [
        item for item in relationships
        if item.from_member_id not in known_ids or item.to_member_id not in known_ids
    ]
    if dangling:
        raise ValueError("relationship references an unknown member")

    hypothesis_only = [member.member_id for member in members if member.memory_source == "system_hypothesis"]
    factual = [member for member in members if member.memory_source in FACTUAL_MEMORY_SOURCES]
    by_generation = Counter(member.generation for member in factual)

    return {
        "genogram_id": f"geno_{uuid.uuid4().hex[:10]}",
        "status": "DRAFT_USER_CONTROLLED",
        "member_count": len(factual),
        "generations_covered": [item for item in GENERATIONS if by_generation.get(item)],
        "members": [member.model_dump(mode="json") for member in factual],
        "relationships": [item.model_dump(mode="json") for item in relationships],
        "excluded_hypothesis_members": hypothesis_only,
        "memory_sources_used": sorted({member.memory_source for member in factual}),
        "third_party_diagnosis_blocked": True,
        "editable_by_user": True,
        "limitations": [
            "家庭图只记录你报告的可观察行为，不评估任何家人的人格或健康状况。",
            "系统假设不会写进家庭历史；只有直接记忆、家人转述和照片记录算作事实性材料。",
            "你可以随时修改或删除其中任何一条。",
        ],
        "created_at": moment,
        "next_action": "ANALYSE_FAMILY_SCRIPTS",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-37 family_script_role_triangle_analyzer
# ─────────────────────────────────────────────────────────────────────────────

FAMILY_SCRIPTS: dict[str, str] = {
    "NO_NEGATIVE_EMOTION": "不要表达负面情绪",
    "NEVER_CHALLENGE_ELDERS": "不要挑战长辈",
    "KEEP_PROBLEMS_INSIDE": "家庭问题不能对外说",
    "ACHIEVEMENT_EQUALS_WORTH": "成绩决定价值",
    "SURFACE_PEACE_FIRST": "维持表面和平比解决问题重要",
    "NEEDS_ARE_BURDENS": "有需要就是给别人添麻烦",
    "LOVE_EQUALS_SELF_SACRIFICE": "爱等于牺牲自己",
    "SPIRITUAL_PEOPLE_DONT_GET_ANGRY": "真正属灵的人不应愤怒",
}
FAMILY_ROLES: dict[str, str] = {
    "HERO_CHILD": "英雄或完美孩子",
    "CARETAKER": "照顾者",
    "MEDIATOR": "调停者",
    "SCAPEGOAT": "替罪羊",
    "INVISIBLE_CHILD": "隐形孩子",
    "EMOTION_CONTAINER": "情绪容器",
    "MESSENGER": "传话者",
    "RESCUER": "拯救者",
}


def analyze_family_scripts(
    *,
    script_candidates: list[dict[str, Any]],
    roles_reported: list[str] | None = None,
    triangles: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Scripts, roles and triangles — each carrying its own FP evidence level."""
    scripts: list[dict[str, Any]] = []
    for candidate in script_candidates:
        code = str(candidate.get("script_code") or "")
        if code and code not in FAMILY_SCRIPTS:
            raise ValueError(f"unknown family script: {code}")
        level = evidence_level(
            concrete_events=int(candidate.get("concrete_events", 0) or 0),
            distinct_periods=int(candidate.get("distinct_periods", 0) or 0),
            relationships_involved=int(candidate.get("relationships_involved", 0) or 0),
            linked_to_current_behavior=bool(candidate.get("linked_to_current_behavior")),
            longitudinally_confirmed=bool(candidate.get("longitudinally_confirmed")),
            user_confirmed=bool(candidate.get("user_confirmed")),
        )
        scripts.append({
            "script_code": code or "USER_DEFINED",
            "script_text": FAMILY_SCRIPTS.get(code, str(candidate.get("script_text") or "")),
            "evidence_level": level,
            "evidence_label": FAMILY_PATTERN_LEVELS[level],
            "may_write_to_twin": may_write_to_twin(level),
            "user_review_status": "PENDING",
        })

    unknown_roles = [item for item in (roles_reported or []) if item not in FAMILY_ROLES]
    if unknown_roles:
        raise ValueError(f"unknown family role: {','.join(unknown_roles)}")

    triangle_records = []
    for triangle in triangles or []:
        triangle_records.append({
            "tension_between": [str(triangle.get("member_a")), str(triangle.get("member_b"))],
            "third_party_pulled_in": str(triangle.get("third_party")),
            "user_function": str(triangle.get("user_function") or "MEDIATOR"),
            "observable_pattern": validate_third_party_language(str(triangle.get("observable_pattern") or "")),
            "evidence_events": int(triangle.get("evidence_events", 0) or 0),
        })

    return {
        "analysis_id": f"fsa_{uuid.uuid4().hex[:10]}",
        "scripts": scripts,
        "roles": [{"code": code, "label": FAMILY_ROLES[code]} for code in (roles_reported or [])],
        "triangles": triangle_records,
        "twin_writable_scripts": [item["script_code"] for item in scripts if item["may_write_to_twin"]],
        "notes": [
            "家庭脚本描述的是当时家庭里学到的规则，不是你今天必须遵守的规则。",
            "只有证据达到 FP4 以上，才会写入长期档案。",
        ],
        "next_action": "PROFILE_ATTACHMENT_CYCLE",
        "rule_version": RULE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-38 attachment_activation_cycle_profiler
# ─────────────────────────────────────────────────────────────────────────────

PROTECTIVE_ACTIONS: dict[str, tuple[str, ...]] = {
    "PURSUE": ("连续发送消息", "反复要求确认", "测试对方是否在意", "不断解释", "查看对方行踪"),
    "WITHDRAW": ("突然沉默", "转移话题", "情感断开", "以工作或游戏隔离", "拒绝讨论", "先结束关系"),
    "CONTROL": ("规定对方必须如何回应", "用道德或属灵评价施压", "要求对方立刻解决自己的情绪"),
    "MIXED": ("先强烈追逐，被拒绝后突然断联",),
}
CYCLE_STEPS: tuple[str, ...] = (
    "TRIGGER", "AUTOMATIC_MEANING", "BODY_AND_EMOTION", "PROTECTIVE_ACTION",
    "OTHER_RESPONSE", "USER_SECOND_RESPONSE", "ESCALATION_OR_REPAIR",
)
MIN_EVENTS_FOR_CYCLE = 2


def profile_attachment_cycle(
    *,
    relationship_context: str,
    events: list[dict[str, Any]],
    trigger_condition: str,
    pressure_level: str = "medium",
    timeframe_days: int = 90,
    relationship_safety: str = "SAFE",
) -> dict[str, Any]:
    """A cycle is always bound to relationship, trigger, pressure, timeframe and confidence."""
    if len(events) < MIN_EVENTS_FOR_CYCLE:
        return {
            "cycle_id": f"att_{uuid.uuid4().hex[:10]}",
            "status": "INSUFFICIENT_EVENTS",
            "minimum_required": MIN_EVENTS_FOR_CYCLE,
            "note": "还没有足够事件来描述这个循环；这不代表你有依恋问题。",
            "next_action": "COLLECT_MORE_EVENTS",
        }

    action_counts = Counter(str(event.get("protective_action") or "").upper() for event in events)
    unknown = [code for code in action_counts if code and code not in PROTECTIVE_ACTIONS]
    if unknown:
        raise ValueError(f"unknown protective action family: {','.join(unknown)}")
    dominant = action_counts.most_common(1)[0][0] if action_counts else "UNKNOWN"
    repaired = sum(1 for event in events if event.get("repaired"))

    contexts_other = sorted({
        str(event.get("relationship_context")) for event in events
        if event.get("relationship_context") and str(event.get("relationship_context")) != relationship_context
    })

    level = evidence_level(
        concrete_events=len(events),
        distinct_periods=len({str(event.get("period") or index) for index, event in enumerate(events)}),
        relationships_involved=1 + len(contexts_other),
        linked_to_current_behavior=True,
        longitudinally_confirmed=timeframe_days >= 90 and len(events) >= 3,
        user_confirmed=all(event.get("user_confirmed") for event in events),
    )

    return {
        "cycle_id": f"att_{uuid.uuid4().hex[:10]}",
        "status": "DRAFT_AWAITING_USER_CONFIRMATION",
        "relationship_context": relationship_context,
        "trigger_condition": trigger_condition,
        "pressure_level": pressure_level,
        "timeframe_days": timeframe_days,
        "steps": list(CYCLE_STEPS),
        "dominant_protective_action": dominant,
        "action_examples": list(PROTECTIVE_ACTIONS.get(dominant, ())),
        "event_count": len(events),
        "repair_count": repaired,
        "other_contexts_observed": contexts_other,
        "context_specific": not contexts_other,
        "evidence_level": level,
        "may_write_to_twin": may_write_to_twin(level),
        "attachment_type_assigned": None,
        "user_facing_statement": (
            f"当前证据显示：在{relationship_context}关系中、遇到「{trigger_condition}」时，"
            f"你比较容易进入{dominant.lower()}型的保护动作。"
            + ("在其他关系情境中没有观察到同样模式。" if not contexts_other else "")
        ),
        "limitations": [
            "这是对一段时间内事件的描述，不是永久的依恋类型。",
            "系统不会给你贴「焦虑型」或「回避型」标签。",
            "对方的行为只按你报告的可观察内容记录，不作任何诊断。",
        ],
        "relationship_safety": relationship_safety,
        "next_action": "SELF_DIFFERENTIATION_COACH",
        "rule_version": RULE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-39 self_differentiation_capacity_coach
# ─────────────────────────────────────────────────────────────────────────────

DIFFERENTIATION_STAGES: dict[str, str] = {
    "SD0": "证据不足",
    "SD1": "融合或切断：要么完全顺从，要么彻底断联",
    "SD2": "开始识别：意识到立场不同，但很难承受不赞同",
    "SD3": "低压力实践：能在安全和低风险情境表达立场",
    "SD4": "多数情境稳定：对方失望、批评或施压时仍能保持立场和连接",
    "SD5": "整合：承担自己的责任，释放他人的反应，并在关系变化后主动修复",
}
SD_ORDER: tuple[str, ...] = ("SD0", "SD1", "SD2", "SD3", "SD4", "SD5")
SD_RANK: dict[str, int] = {stage: index for index, stage in enumerate(SD_ORDER)}

DIFFERENTIATION_PROTOCOL: tuple[tuple[str, str], ...] = (
    ("STEADY_SELF", "稳定自己：先调节，不在高度激活时作重大关系决定"),
    ("STATE_POSITION", "说出我的位置：我看到什么、我感受什么、我的决定是什么"),
    ("ACKNOWLEDGE_RELATIONSHIP", "承认关系：我重视你，也听见你不赞同"),
    ("RETURN_RESPONSIBILITY", "归还责任：我负责清楚而尊重地表达；你如何感受和选择是你的责任"),
    ("STAY_CONNECTED_OR_SAFE_DISTANCE", "保持连接或安全距离：不讨好、不攻击，也不以冷暴力惩罚"),
)


def assess_differentiation(
    *,
    events: list[dict[str, Any]],
    activation_level: int | None = None,
) -> dict[str, Any]:
    """Stage from observed behaviour; the five-step protocol is the practice, not a script to obey."""
    if not events:
        stage = "SD0"
    else:
        stated = [event for event in events if event.get("stated_position")]
        under_pressure = [event for event in stated if event.get("under_pressure")]
        cutoff_or_comply = [
            event for event in events
            if event.get("complied_completely") or event.get("cut_off_contact")
        ]
        repaired = [event for event in events if event.get("repaired_after")]
        returned_responsibility = [event for event in stated if event.get("returned_responsibility")]

        if not stated and cutoff_or_comply:
            stage = "SD1"
        elif stated and not under_pressure:
            stage = "SD3" if len(stated) >= 2 else "SD2"
        elif under_pressure and returned_responsibility and repaired:
            stage = "SD5"
        elif under_pressure:
            stage = "SD4"
        else:
            stage = "SD2"

    high_activation = activation_level is not None and activation_level >= 7
    return {
        "assessment_id": f"sdf_{uuid.uuid4().hex[:10]}",
        "stage": stage,
        "stage_label": DIFFERENTIATION_STAGES[stage],
        "protocol": [{"code": code, "instruction": text} for code, text in DIFFERENTIATION_PROTOCOL],
        "practice_blocked_while_activated": high_activation,
        "practice_note": (
            "现在激活程度较高，先用 Batch 4 的暂停协议稳定下来，再练习表达立场。"
            if high_activation else
            "从低风险的一次表达开始；不需要一次就处理最难的关系。"
        ),
        "not_required": [
            "分化不是断联，也不是必须说服对方。",
            "对方失望不等于你的边界错了。",
        ],
        "next_action": "REFRAME_CHILDHOOD_OATH",
        "rule_version": RULE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-40 childhood_oath_reframe_and_reparenting_facilitator
# ─────────────────────────────────────────────────────────────────────────────

COMMON_SURVIVAL_OATHS: dict[str, str] = {
    "NO_BURDEN": "我不能给别人添麻烦",
    "ALWAYS_USEFUL": "我必须永远有用",
    "NO_MISTAKES": "我不能犯错",
    "TRUST_NOBODY": "我不能相信任何人",
    "CARE_FOR_EVERYONE": "我必须照顾所有人",
    "NEEDS_GET_REJECTED": "我一表达需要就会被拒绝",
    "ONLY_COMPLIANCE_KEEPS_LOVE": "只有顺从才能维持关系",
    "NEVER_WEAK": "我不能表现软弱",
    "MORE_SPIRITUAL_TO_BE_ACCEPTED": "我必须比别人更属灵，才值得被接纳",
}
OATH_LANGUAGE_OPTIONS: tuple[str, ...] = ("PAST_SELF", "INNER_CHILD", "EARLY_SURVIVAL_RESPONSE", "OLD_CORE_BELIEF")
MAX_ACTIVATION_FOR_OATH_WORK = 5

_MEMORY_INDUCTION = re.compile(r"(你小时候一定|你一定曾经被|想象一下你被|回到那个画面.{0,6}告诉我你看到)")


def reframe_survival_oath(
    *,
    oath_text: str,
    memory_source: str,
    current_repetition: str,
    user_consent: bool,
    activation_level: int,
    in_crisis: bool = False,
    preferred_language: str = "PAST_SELF",
    spiritual_integration_enabled: bool = False,
    adult_commitment: str | None = None,
) -> dict[str, Any]:
    """Reframe an early survival rule into an adult commitment — never induce a memory."""
    if preferred_language not in OATH_LANGUAGE_OPTIONS:
        raise ValueError(f"unknown language option: {preferred_language}")
    if memory_source not in MEMORY_SOURCES:
        raise ValueError(f"unknown memory source: {memory_source}")

    blocks: list[str] = []
    if not user_consent:
        blocks.append("USER_CONSENT_MISSING")
    if activation_level > MAX_ACTIVATION_FOR_OATH_WORK:
        blocks.append("ACTIVATION_TOO_HIGH")
    if in_crisis:
        blocks.append("CRISIS_ACTIVE")
    if memory_source not in FACTUAL_MEMORY_SOURCES:
        blocks.append("MATERIAL_NOT_FACTUAL")
    if blocks:
        return {
            "oath_id": f"oat_{uuid.uuid4().hex[:10]}",
            "status": "NOT_STARTED",
            "blocks": blocks,
            "note": "现在不适合做这项练习；这不是抗拒，也不影响你的任何评估结果。",
            "next_action": "STABILISE_FIRST" if "ACTIVATION_TOO_HIGH" in blocks else "OFFER_LATER",
        }

    for text in (oath_text, current_repetition, adult_commitment or ""):
        if text:
            validate_safe_text(text)
            if _MEMORY_INDUCTION.search(text):
                raise UnsafeContentError("memory induction phrasing is not allowed")

    commitment = adult_commitment or "我可以关心他们，但我不负责让所有人都满意。"
    validate_safe_text(commitment)

    spiritual = []
    if spiritual_integration_enabled:
        spiritual = [
            "如果你愿意，可以把这句旧誓言原样带到神面前，不用先把它修得好听。",
            "属灵整合是可选的，它不用来证明你更属灵，也不替代现实中的界限与行动。",
        ]

    return {
        "oath_id": f"oat_{uuid.uuid4().hex[:10]}",
        "status": "REFRAMED_DRAFT",
        "oath_text": oath_text,
        "memory_source": memory_source,
        "memory_source_label": MEMORY_SOURCES[memory_source],
        "language_used": preferred_language,
        "protective_function": "这条规则当年很可能帮助你在那个环境里保持安全或被接纳。",
        "current_cost": current_repetition,
        "adult_commitment": commitment,
        "responsibility_note": "过去帮助我们理解旧模式从何而来；成年后的行为仍然需要由我们自己负责。",
        "optional_spiritual_integration": spiritual,
        "user_can_decline": True,
        "decline_note": "你可以拒绝这个练习，也可以换成「过去的自己」或「早年生存反应」的说法。",
        "not_a_diagnosis": "这不是诊断，也不表示你必然经历过某种创伤。",
        "next_action": "PROFILE_FALSE_SELF_MASKS",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-41 false_self_mask_and_defense_profiler
# ─────────────────────────────────────────────────────────────────────────────

MASKS: dict[str, dict[str, str]] = {
    "PERFECT_PERFORMER": {"label": "完美表现者", "belief": "我不能出错，否则没有价值",
                          "protected": "被否定和被看轻的恐惧", "cost": "无法承认失误，难以被真正认识"},
    "RESCUER": {"label": "全能拯救者", "belief": "如果我不解决，别人就会崩溃",
                "protected": "对失控和被抛弃的恐惧", "cost": "长期过载，替别人承担了他们的责任"},
    "PLEASER": {"label": "讨好与伪和平维护者", "belief": "只有别人满意，我才是安全的",
                "protected": "冲突和被拒绝的恐惧", "cost": "边界模糊，积累怨恨"},
    "CONTROLLER": {"label": "控制者", "belief": "只有掌控全部细节，才不会出事",
                   "protected": "不确定与无助感", "cost": "关系紧绷，别人失去空间"},
    "INVULNERABLE_EXPERT": {"label": "不可脆弱的专家", "belief": "我不能承认不知道或需要帮助",
                            "protected": "羞耻与被小看的恐惧", "cost": "孤立，得不到实际支持"},
    "DETACHED_OBSERVER": {"label": "情感绝缘者", "belief": "只要我不需要任何人，就不会受伤",
                          "protected": "亲密带来的风险", "cost": "关系变浅，情绪迟钝"},
    "SPIRITUAL_PERFORMER": {"label": "属灵表演者", "belief": "我必须始终正确、喜乐、刚强和有信心",
                            "protected": "被评判为不属灵的恐惧", "cost": "无法诚实哀伤、发怒或说不知道"},
    "MORAL_SUPERIORITY_DEFENSE": {"label": "道德优越防御", "belief": "只要我在道理上占上风，就不会受伤",
                                  "protected": "被指责和被误解的痛", "cost": "冲突升级，关系里没有柔软"},
}


def profile_masks(
    mask_observations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Masks once protected something; they are patterns with a cost, not a personality verdict."""
    records: list[dict[str, Any]] = []
    for observation in mask_observations:
        code = str(observation.get("mask_code") or "")
        if code not in MASKS:
            raise ValueError(f"unknown mask: {code}")
        level = evidence_level(
            concrete_events=int(observation.get("concrete_events", 0) or 0),
            distinct_periods=int(observation.get("distinct_periods", 0) or 0),
            relationships_involved=int(observation.get("contexts", 0) or 0),
            linked_to_current_behavior=bool(observation.get("linked_to_current_behavior")),
            user_confirmed=bool(observation.get("user_confirmed")),
        )
        detail = MASKS[code]
        records.append({
            "mask_code": code,
            "label": detail["label"],
            "belief": detail["belief"],
            "what_it_protected": detail["protected"],
            "current_cost": detail["cost"],
            "contexts": observation.get("context_labels") or [],
            "evidence_level": level,
            "may_write_to_twin": may_write_to_twin(level),
            "user_review_status": "PENDING",
        })

    return {
        "mask_profile_id": f"msk_{uuid.uuid4().hex[:10]}",
        "masks": records,
        "framing": [
            "面具不是虚伪，它当年通常真的保护过你。",
            "这里描述的是在压力下容易出现的模式，不是你这个人的定义。",
        ],
        "next_action": "INTEGRATE_TRUE_SELF",
        "rule_version": RULE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-42 true_self_value_identity_integrator
# ─────────────────────────────────────────────────────────────────────────────

COMPASS_PARTS: tuple[tuple[str, str], ...] = (
    ("IDENTITY", "我是谁，不只由表现、角色和他人评价定义"),
    ("VALUES", "我真正重视什么"),
    ("LIMITS", "我不能做什么、无法控制什么"),
    ("GIFTS", "我能够贡献什么"),
    ("RESPONSIBILITIES", "我确实应当承担什么"),
    ("RELATIONAL_COMMITMENTS", "我希望如何爱人、沟通和修复"),
)
TRUE_SELF_IS_NOT: tuple[str, ...] = (
    "我想做什么就做什么",
    "我的感受永远正确",
    "拒绝一切责任",
    "追求绝对自我实现",
)


def build_true_self_compass(
    *,
    parts: dict[str, list[str]],
    adult_commitment: str,
    mask_codes: list[str] | None = None,
    spiritual_framework: str = "user_choice",
) -> dict[str, Any]:
    """Turn 'true self' from a slogan into a checkable compass with limits and responsibilities."""
    unknown = [key for key in parts if key not in dict(COMPASS_PARTS)]
    if unknown:
        raise ValueError(f"unknown compass part: {','.join(unknown)}")
    validate_safe_text(adult_commitment)
    for entries in parts.values():
        for entry in entries:
            validate_safe_text(entry)

    missing = [code for code, _ in COMPASS_PARTS if not parts.get(code)]
    contradicting_masks = [code for code in (mask_codes or []) if code in MASKS]

    completeness = round((len(COMPASS_PARTS) - len(missing)) / len(COMPASS_PARTS), 2)
    return {
        "compass_id": f"tsc_{uuid.uuid4().hex[:10]}",
        "parts": [
            {"code": code, "description": description, "entries": parts.get(code, [])}
            for code, description in COMPASS_PARTS
        ],
        "missing_parts": missing,
        "completeness": completeness,
        "adult_commitment": adult_commitment,
        "true_self_is_not": list(TRUE_SELF_IS_NOT),
        "masks_this_replaces": [
            {"mask_code": code, "label": MASKS[code]["label"], "cost": MASKS[code]["cost"]}
            for code in contradicting_masks
        ],
        "consistency_check": [
            "限度和责任必须同时存在：只有权利没有责任不是真我。",
            "罗盘只有在现实行为里被验证，才算整合。",
        ],
        "spiritual_framework": spiritual_framework,
        "next_action": "DESIGN_VULNERABILITY_EXPERIMENT",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-43 safe_constructive_vulnerability_experiment_designer
# ─────────────────────────────────────────────────────────────────────────────

DISCLOSURE_DEPTHS: dict[str, str] = {
    "V1": "偏好与轻微需要",
    "V2": "当前感受",
    "V3": "关系影响",
    "V4": "深层恐惧或旧模式",
    "V5": "高敏感经历或创伤材料（仅限高度安全关系且用户主动选择）",
}
DEPTH_ORDER: tuple[str, ...] = ("V1", "V2", "V3", "V4", "V5")
DEPTH_RANK: dict[str, int] = {depth: index for index, depth in enumerate(DEPTH_ORDER)}
RELATIONSHIP_SAFETY_STATES: tuple[str, ...] = ("SAFE", "CAUTION", "UNSAFE", "UNKNOWN")
EXPRESSION_STRUCTURE: tuple[tuple[str, str], ...] = (
    ("FACT", "发生了什么"),
    ("FEELING", "我实际感到什么"),
    ("MEANING", "我当时如何理解，但这可能只是我的解释"),
    ("NEED_OR_VALUE", "我重视什么、需要什么"),
    ("REQUEST", "具体、可选择、可执行的请求"),
    ("BOUNDARY", "如果请求不被接受，我将如何保护自己"),
)
DEFAULT_MAX_DEPTH = "V2"
CAUTION_MAX_DEPTH = "V2"


def design_vulnerability_experiment(
    *,
    target_relationship_type: str,
    safety_status: str,
    target_issue: str,
    preferred_depth: str = DEFAULT_MAX_DEPTH,
    power_asymmetry: str = "LOW",
    activation_level: int = 3,
    prior_experiment_count: int = 0,
) -> dict[str, Any]:
    """Graded, verifiable reality experiment. UNSAFE relationships get no experiment at all."""
    if safety_status not in RELATIONSHIP_SAFETY_STATES:
        raise ValueError(f"unknown relationship safety: {safety_status}")
    if preferred_depth not in DEPTH_RANK:
        raise ValueError(f"unknown disclosure depth: {preferred_depth}")
    validate_safe_text(target_issue)

    if safety_status == "UNSAFE":
        return {
            "experiment_id": f"vex_{uuid.uuid4().hex[:10]}",
            "status": "NOT_GENERATED_UNSAFE",
            "depth": None,
            "note": "在存在暴力、威胁、操控、公开羞辱或职权报复的关系中，不生成脆弱表达实验。",
            "alternatives": ["记录事实与证据", "与关系之外的安全对象讨论", "准备保护与退出选项"],
            "next_action": "ROUTE_TO_SAFETY_SUPPORT",
        }

    depth = preferred_depth
    caps: list[str] = []
    if safety_status in {"CAUTION", "UNKNOWN"} and DEPTH_RANK[depth] > DEPTH_RANK[CAUTION_MAX_DEPTH]:
        depth = CAUTION_MAX_DEPTH
        caps.append("RELATIONSHIP_SAFETY_CAUTION")
    if power_asymmetry == "HIGH" and DEPTH_RANK[depth] > DEPTH_RANK["V2"]:
        depth = "V2"
        caps.append("POWER_ASYMMETRY")
    if prior_experiment_count == 0 and DEPTH_RANK[depth] > DEPTH_RANK[DEFAULT_MAX_DEPTH]:
        depth = DEFAULT_MAX_DEPTH
        caps.append("FIRST_EXPERIMENT_STARTS_LOW")
    if activation_level >= 7:
        return {
            "experiment_id": f"vex_{uuid.uuid4().hex[:10]}",
            "status": "DEFERRED_HIGH_ACTIVATION",
            "depth": None,
            "note": "现在激活程度较高，先稳定下来再安排这次对话。",
            "next_action": "SACRED_PAUSE_PROTOCOL",
        }

    structure = [{"code": code, "description": text} for code, text in EXPRESSION_STRUCTURE]
    if safety_status in {"CAUTION", "UNKNOWN"}:
        structure = [item for item in structure if item["code"] in {"FACT", "REQUEST", "BOUNDARY"}]

    return {
        "experiment_id": f"vex_{uuid.uuid4().hex[:10]}",
        "status": "READY",
        "target_relationship_type": target_relationship_type,
        "safety_status": safety_status,
        "depth": depth,
        "depth_label": DISCLOSURE_DEPTHS[depth],
        "depth_caps_applied": caps,
        "target_issue": target_issue,
        "expression_structure": structure,
        "success_criteria": [
            "你按计划表达了事实、感受与请求",
            "你保留了自己的边界",
            "你记录了实际发生了什么",
        ],
        "not_success_criteria": [
            "对方是否同意",
            "对方是否道歉",
            "关系是否立刻变好",
        ],
        "possible_responses": ["接受并调整", "解释或防御", "沉默或回避", "反过来指责"],
        "boundary_plan": "如果请求不被接受，我会说明我将如何安排自己，而不是威胁或冷处理。",
        "record_prompt": "对话后记录：我做了什么、对方如何反应、我的边界是否保住。",
        "next_action": "TRACK_AS_REAL_LIFE_EVENT",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 状态机与自描述
# ─────────────────────────────────────────────────────────────────────────────

WORKFLOW_NODES: tuple[str, ...] = (
    "EM-36_genogram_mapper", "EM-37_family_script_analyzer", "EM-38_attachment_cycle_profiler",
    "EM-39_differentiation_coach", "EM-40_survival_oath_reframe", "EM-41_mask_profiler",
    "EM-42_true_self_compass", "EM-43_vulnerability_experiment",
)

STATE_MACHINE: tuple[tuple[str, str], ...] = (
    ("GENOGRAM_DRAFTED", "SCRIPTS_ANALYSED"),
    ("SCRIPTS_ANALYSED", "ATTACHMENT_CYCLE_PROFILED"),
    ("ATTACHMENT_CYCLE_PROFILED", "DIFFERENTIATION_ASSESSED"),
    ("DIFFERENTIATION_ASSESSED", "OATH_REFRAMED"),
    ("DIFFERENTIATION_ASSESSED", "OATH_DECLINED"),
    ("OATH_REFRAMED", "MASKS_PROFILED"),
    ("OATH_DECLINED", "MASKS_PROFILED"),
    ("MASKS_PROFILED", "TRUE_SELF_COMPASS_BUILT"),
    ("TRUE_SELF_COMPASS_BUILT", "VULNERABILITY_EXPERIMENT_READY"),
    ("TRUE_SELF_COMPASS_BUILT", "EXPERIMENT_BLOCKED_UNSAFE"),
    ("VULNERABILITY_EXPERIMENT_READY", "TRACKED_IN_REAL_LIFE"),
)


def describe_family_engine() -> dict[str, Any]:
    return {
        "module": "emotional_maturity_family_and_self",
        "short_name": "EMD-OS Batch 5",
        "batch": 5,
        "skills": list(WORKFLOW_NODES),
        "pattern_evidence_levels": FAMILY_PATTERN_LEVELS,
        "twin_write_minimum": TWIN_WRITE_MINIMUM,
        "memory_sources": MEMORY_SOURCES,
        "factual_memory_sources": sorted(FACTUAL_MEMORY_SOURCES),
        "family_scripts": FAMILY_SCRIPTS,
        "family_roles": FAMILY_ROLES,
        "protective_actions": {code: list(values) for code, values in PROTECTIVE_ACTIONS.items()},
        "differentiation_stages": DIFFERENTIATION_STAGES,
        "survival_oaths": COMMON_SURVIVAL_OATHS,
        "oath_language_options": list(OATH_LANGUAGE_OPTIONS),
        "masks": {code: detail["label"] for code, detail in MASKS.items()},
        "compass_parts": [{"code": code, "description": text} for code, text in COMPASS_PARTS],
        "disclosure_depths": DISCLOSURE_DEPTHS,
        "forgiveness_distinctions": [{"code": code, "label": label} for code, label in FORGIVENESS_DISTINCTIONS],
        "does_not": [
            "不用童年经历免除成年后的责任",
            "不远程诊断父母、伴侣或教会领袖",
            "不诱导或补全童年记忆",
            "不给用户指派永久依恋类型",
            "不把拒绝内在孩童练习当作抗拒成长",
            "不把饶恕等同于重新信任或恢复接触",
            "不在不安全关系中生成脆弱表达实验",
        ],
        "engine_version": ENGINE_VERSION,
        "rule_version": RULE_VERSION,
        "state_machine": [{"from": source, "to": target} for source, target in STATE_MACHINE],
    }
