"""EMD-OS Batch 6: empathy, boundaries, clean conflict, apology, forgiveness and repair.

    EM-44 同理心 → EM-45 心智化 → EM-46 边界权责 → EM-47 边界执行阶梯
    → EM-48 清洁冲突议题 → EM-49 冲突对话 → EM-50 负责任的道歉
    → EM-51 宽恕／信任／和好辨析 → EM-52 修复与补偿计划 → EM-53 修复成效与信任决策路由

七个必须严格区分的概念（全部由代码强制）：

1. 同理心 ≠ 同意：理解对方的感受，不代表认可对方的控制、威胁或越界行为。
2. 心智化 ≠ 读心：动机结论必须降级为假设 + 澄清问题。
3. 边界 ≠ 控制：边界说的是「我会怎么做」，控制说的是「你必须怎么做，否则我惩罚你」。
4. 清洁冲突 ≠ 没有情绪：允许愤怒、失望、哭泣与明确说不；不允许人身攻击、威胁、羞辱、翻旧账、沉默惩罚。
5. 道歉 ≠ 自我羞辱：承担具体行为，而不是把注意力转移到安慰道歉者。
6. 宽恕 ≠ 信任 ≠ 和好 ≠ 恢复接触 ≠ 恢复角色。
7. 修复行为 ≠ 关系必然恢复：对方永远有权不回应、不原谅、不恢复信任。
"""
from __future__ import annotations

import re
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from .emotional_maturity import UnsafeContentError, validate_safe_text
from .emotional_maturity_family import validate_third_party_language


ENGINE_VERSION = "emd-conflict-engine-1.0"
RULE_VERSION = "emd-conflict-rules-1.0"

# ── 关系证据等级 ─────────────────────────────────────────────────────────────
RELATIONSHIP_EVIDENCE_LEVELS: dict[str, str] = {
    "RE0": "抽象原则：知道「应该怎样沟通」",
    "RE1": "模拟表达：在系统情境题中完成话术",
    "RE2": "现实尝试：实际表达了边界、道歉或修复请求",
    "RE3": "行动后验证：48–72 小时后确认实际采取了什么行动",
    "RE4": "行为持续：数周内在相似情境中重复表现",
    "RE5": "双方秩序改善：在安全且双方自愿前提下，重复冲突减少、承诺被持续履行",
    "RE6": "跨场景整合：在家庭、职场、教会或亲密关系中形成较稳定迁移",
}
RE_ORDER: tuple[str, ...] = ("RE0", "RE1", "RE2", "RE3", "RE4", "RE5", "RE6")
RE_RANK: dict[str, int] = {level: index for index, level in enumerate(RE_ORDER)}

RELATIONSHIP_SAFETY_STATES: tuple[str, ...] = ("SAFE", "CAUTION", "UNSAFE", "UNKNOWN")
MAX_ACTIVATION_FOR_CONFLICT = 5


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


# ─────────────────────────────────────────────────────────────────────────────
# EM-44 empathic_perspective_taking_trainer
# ─────────────────────────────────────────────────────────────────────────────

_AGREEMENT_LEAK = re.compile(r"(所以(他|她)(这样做|的要求)是(合理|对)的|因此你应该接受|你也有错，所以)")


def train_perspective_taking(
    *,
    situation: str,
    user_experience: str,
    possible_other_experience: str,
    harmful_behaviors: list[str] | None = None,
    relationship_safety: str = "UNKNOWN",
) -> dict[str, Any]:
    """Understanding why someone may feel that way never makes harmful behaviour reasonable."""
    for text in (situation, user_experience, possible_other_experience):
        validate_third_party_language(text)
    if _AGREEMENT_LEAK.search(possible_other_experience):
        raise UnsafeContentError("empathy output must not endorse harmful behaviour")

    harms = list(harmful_behaviors or [])
    return {
        "training_id": _new_id("emp"),
        "situation": situation,
        "your_experience": user_experience,
        "possible_other_experience": possible_other_experience,
        "hypothesis_status": "UNVERIFIED_HYPOTHESIS",
        "empathy_is_not_agreement": (
            "理解对方可能的感受，不代表认可对方的行为；两者可以同时成立。"
        ),
        "still_true_regardless": [
            *( [f"以下行为仍然不因理解而变得合理：{item}" for item in harms] ),
            "你的事实记录、边界与责任划分不会因为同理心而取消。",
        ],
        "relationship_safety": relationship_safety,
        "safety_note": (
            "关系安全存疑时，先保护自己，再谈理解对方。"
            if relationship_safety in {"CAUTION", "UNSAFE"} else None
        ),
        "next_action": "CALIBRATE_MOTIVE_UNCERTAINTY",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-45 mentalization_motive_uncertainty_calibrator
# ─────────────────────────────────────────────────────────────────────────────

_MIND_READING_PATTERNS: tuple[str, ...] = (
    r"(他|她)就是(故意|想|要)", r"(他|她)(肯定|一定|根本)(是|就)", r"我知道(他|她)在想",
    r"(他|她)从来(没有|不)", r"(他|她)每次都",
)
_MIND_READING_RE = tuple(re.compile(pattern) for pattern in _MIND_READING_PATTERNS)


def calibrate_motive_uncertainty(statement: str) -> dict[str, Any]:
    """Turn a motive verdict into a testable hypothesis plus a clarification question."""
    validate_third_party_language(statement)
    detected = [pattern.pattern for pattern in _MIND_READING_RE if pattern.search(statement)]

    hypothesis = statement
    for pattern in _MIND_READING_RE:
        hypothesis = pattern.sub("我猜对方可能", hypothesis)
    if detected:
        hypothesis = f"我担心{hypothesis.strip()}，但我还不知道这是不是他的真实意思。"

    return {
        "calibration_id": _new_id("mtz"),
        "original_statement": statement,
        "mind_reading_detected": bool(detected),
        "matched_patterns": detected,
        "hypothesis": hypothesis if detected else f"我目前的理解是：{statement}",
        "hypothesis_status": "UNVERIFIED_HYPOTHESIS",
        "clarification_questions": [
            "你刚才说那句话时，想表达的是什么？",
            "我理解成……，这是你的意思吗？",
            "有没有我没看到的情况？",
        ],
        "alternative_explanations": [
            "对方可能有你不知道的压力或信息",
            "对方可能表达方式与你不同",
            "对方可能确实如你所想——但这需要澄清后才知道",
        ],
        "rule": "心智化不是替对方回答，而是把结论变回问题。",
        "next_action": "MAP_BOUNDARY_RIGHTS",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-46 boundary_rights_responsibility_guard
# ─────────────────────────────────────────────────────────────────────────────

BOUNDARY_OBJECTS: tuple[str, ...] = (
    "BODY", "PRIVACY", "TIME", "FINANCE", "WORKLOAD", "EMOTIONAL_LABOUR", "DIGITAL_DEVICES",
    "FAITH_AND_CONSCIENCE", "CAREER_DECISION", "FAMILY_DECISION", "COMMUNICATION_STYLE",
    "CONTACT_FREQUENCY", "INFORMATION_DISCLOSURE",
)
BOUNDARY_KINDS: tuple[str, ...] = ("REQUEST", "LIMIT")

_CONTROL_PATTERNS = re.compile(
    r"(你必须(承认|同意|道歉|改变)|否则我就(让|告诉|公开)|我会让(所有人|大家)(都)?不理你|不然你就别想)"
)


def map_boundary(
    *,
    boundary_object: str,
    scenario: str,
    boundary_kind: str,
    boundary_statement: str,
    my_responsibilities: list[str],
    their_responsibilities: list[str],
    shared_responsibilities: list[str] | None = None,
    uncontrollable: list[str] | None = None,
    action_if_violated: str,
    relationship_safety: str = "UNKNOWN",
    power_asymmetry: str = "LOW",
    guilt_level: int | None = None,
) -> dict[str, Any]:
    """A boundary says what I will do — never what the other person must do or else."""
    if boundary_object not in BOUNDARY_OBJECTS:
        raise ValueError(f"unknown boundary object: {boundary_object}")
    if boundary_kind not in BOUNDARY_KINDS:
        raise ValueError(f"unknown boundary kind: {boundary_kind}")
    for text in (scenario, boundary_statement, action_if_violated):
        validate_third_party_language(text)
    if _CONTROL_PATTERNS.search(boundary_statement) or _CONTROL_PATTERNS.search(action_if_violated):
        raise UnsafeContentError("this is control, not a boundary")

    return {
        "boundary_id": _new_id("bnd"),
        "boundary_object": boundary_object,
        "boundary_kind": boundary_kind,
        "boundary_statement": boundary_statement,
        "responsibility_map": {
            "mine": my_responsibilities,
            "theirs": their_responsibilities,
            "shared": list(shared_responsibilities or []),
            "not_controllable": list(uncontrollable or ["对方是否接受", "对方的情绪反应", "关系最终走向"]),
        },
        "action_if_violated": action_if_violated,
        "boundary_is_not_control": (
            "边界描述我会怎么做；控制是要求对方必须怎么做，否则惩罚、威胁或操纵。"
        ),
        "relationship_safety": relationship_safety,
        "power_asymmetry": power_asymmetry,
        "guilt_note": (
            "内疚感高不代表边界错了；内疚通常是旧脚本的声音，不是判断标准。"
            if guilt_level is not None and guilt_level >= 6 else None
        ),
        "next_action": "PLAN_BOUNDARY_ENFORCEMENT",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-47 boundary_enforcement_escalation_planner
# ─────────────────────────────────────────────────────────────────────────────

ENFORCEMENT_LADDER: dict[str, str] = {
    "L0": "明确一次：清楚说明事实、限制和请求",
    "L1": "简短重复：不进入无限辩论，不增加新理由",
    "L2": "减少暴露：减少接触、缩短通话、改用书面渠道",
    "L3": "结构性保护：锁门、权限管理、排班规则、财务隔离、信息最小化",
    "L4": "第三方支持：主管、人力资源、牧养监督机制、调解者、可信见证人",
    "L5": "安全退出：结束互动、暂停关系、离开危险环境或进入正式保护流程",
}
LADDER_ORDER: tuple[str, ...] = ("L0", "L1", "L2", "L3", "L4", "L5")
LADDER_RANK: dict[str, int] = {level: index for index, level in enumerate(LADDER_ORDER)}


def plan_boundary_enforcement(
    *,
    violation_count: int,
    previous_actions: list[str] | None = None,
    power_asymmetry: str = "LOW",
    retaliation_risk: str = "LOW",
    safety_risk: bool = False,
    available_support: list[str] | None = None,
) -> dict[str, Any]:
    """Turn a spoken boundary into graded, non-retaliatory protective action."""
    if safety_risk:
        level = "L5"
    else:
        level = {0: "L0", 1: "L1", 2: "L2"}.get(violation_count, "L3")
        if violation_count >= 4 and available_support:
            level = "L4"
        if power_asymmetry == "HIGH" and LADDER_RANK[level] >= LADDER_RANK["L2"] and available_support:
            level = max(level, "L4", key=lambda value: LADDER_RANK[value])

    return {
        "plan_id": _new_id("enf"),
        "recommended_level": level,
        "level_description": ENFORCEMENT_LADDER[level],
        "ladder": [{"level": code, "description": text} for code, text in ENFORCEMENT_LADDER.items()],
        "may_skip_levels": True,
        "skip_note": "出现安全风险时可以直接进入 L5，不必逐级走完。",
        "previous_actions": list(previous_actions or []),
        "violation_count": violation_count,
        "retaliation_risk": retaliation_risk,
        "retaliation_note": (
            "报复风险较高时，优先书面记录与第三方在场，不做公开对质。"
            if retaliation_risk in {"MEDIUM", "HIGH"} else None
        ),
        "non_retaliation_rule": "边界执行的目的是保护自己，不是让对方难堪或受罚。",
        "available_support": list(available_support or []),
        "next_action": "FRAME_CLEAN_CONFLICT_ISSUE",
        "rule_version": RULE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-48 clean_conflict_issue_framer
# ─────────────────────────────────────────────────────────────────────────────

DIRTY_CONFLICT_CODES: dict[str, str] = {
    "MIND_READING": "未经核实判断动机",
    "GLOBAL_LABEL": "整体人格标签：自私、恶毒、废物、没救",
    "ABSOLUTE_LANGUAGE": "总是、从来不、每次都",
    "HISTORY_FLOODING": "一次引入大量旧账",
    "THREAT": "分手、离职、公开羞辱等作为操纵",
    "MORAL_OR_SPIRITUAL_COERCION": "用孝顺、忠心、属灵状态压制讨论",
    "PUNITIVE_SILENCE": "通过沉默惩罚",
    "COUNTER_COMPLAINT": "一听到反馈就立刻反控诉",
}
_DIRTY_PATTERNS: tuple[tuple[str, str], ...] = (
    ("MIND_READING", r"(他|她)就是(故意|想)|(他|她)(肯定|一定)是"),
    ("GLOBAL_LABEL", r"(自私|恶毒|废物|没救|烂人|无可救药)"),
    ("ABSOLUTE_LANGUAGE", r"(总是|从来不|从来没有|每次都|永远)"),
    ("HISTORY_FLOODING", r"(从(结婚|认识|一开始|小时候)(开始)?就|上次|以前也|哪一次不是)"),
    ("THREAT", r"(那就分手|我就离职|我让所有人知道|信不信我)"),
    ("MORAL_OR_SPIRITUAL_COERCION", r"(不孝|不忠心|不够属灵|真正的基督徒不会|你这样对得起)"),
    ("PUNITIVE_SILENCE", r"(不理(他|她|你)|冷战|懒得说话)"),
    ("COUNTER_COMPLAINT", r"(你还不是|你自己呢|你也一样)"),
)
_DIRTY_RE = tuple((code, re.compile(pattern)) for code, pattern in _DIRTY_PATTERNS)

CLEAN_CONFLICT_ALLOWS: tuple[str, ...] = ("愤怒", "失望", "哭泣", "意见激烈不同", "明确说不")


def frame_conflict_issue(
    *,
    raw_complaint: str,
    activation_level: int,
    violence_risk: bool = False,
    single_issue: str | None = None,
    willing_to_hear_other: bool = True,
) -> dict[str, Any]:
    """Strip the dirty components and reduce the complaint to one solvable issue."""
    validate_third_party_language(raw_complaint)
    detected = [
        {"code": code, "description": DIRTY_CONFLICT_CODES[code], "matched": match.group(0)}
        for code, pattern in _DIRTY_RE
        if (match := pattern.search(raw_complaint))
    ]

    blocks: list[str] = []
    if activation_level > MAX_ACTIVATION_FOR_CONFLICT:
        blocks.append("ACTIVATION_TOO_HIGH")
    if violence_risk:
        blocks.append("VIOLENCE_RISK")
    if not single_issue:
        blocks.append("NO_SINGLE_ISSUE_STATED")
    if not willing_to_hear_other:
        blocks.append("NOT_READY_TO_HEAR_OTHER")

    if blocks:
        return {
            "issue_id": _new_id("iss"),
            "status": "NOT_READY",
            "blocks": blocks,
            "dirty_components": detected,
            "next_action": "SACRED_PAUSE_PROTOCOL" if "ACTIVATION_TOO_HIGH" in blocks else "PREPARE_LATER",
        }

    return {
        "issue_id": _new_id("iss"),
        "status": "READY",
        "single_issue": single_issue,
        "dirty_components": detected,
        "cleaned_structure": {
            "current_event": "这次具体发生了什么",
            "historical_pattern": "以往的模式（本次不处理，另行安排）",
            "motive_hypothesis": "我的猜测，需要澄清",
            "emotion": "我实际的感受",
            "concrete_impact": "对我造成的具体影响",
            "single_request": single_issue,
            "out_of_scope": "本次不处理的内容",
        },
        "clean_conflict_allows": list(CLEAN_CONFLICT_ALLOWS),
        "clean_conflict_forbids": list(DIRTY_CONFLICT_CODES.values()),
        "note": "清洁冲突不是没有情绪的冲突；愤怒和眼泪都可以出现。",
        "next_action": "FACILITATE_DIALOGUE",
        "rule_version": RULE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-49 clean_conflict_dialogue_facilitator
# ─────────────────────────────────────────────────────────────────────────────

DIALOGUE_PROTOCOL: tuple[str, ...] = (
    "确认单一议题和时间",
    "A 用事实-感受-需要-请求表达",
    "B 只复述，不反驳",
    "A 确认复述是否准确",
    "B 表达自己的视角",
    "A 复述",
    "区分共同事实、不同解释和不同需要",
    "生成两个以上可行方案",
    "明确承诺、边界和检查时间",
    "无法继续时执行暂停契约",
)
DIALOGUE_MODES: tuple[str, ...] = ("SOLO_REHEARSAL", "MUTUAL_WORKSPACE")


def facilitate_dialogue(
    *,
    mode: str,
    single_issue: str,
    both_parties_consented: bool = False,
    relationship_safety: str = "UNKNOWN",
) -> dict[str, Any]:
    """Ten-step turn-taking protocol. Simulated replies are always labelled as simulated."""
    if mode not in DIALOGUE_MODES:
        raise ValueError(f"unknown dialogue mode: {mode}")
    if relationship_safety == "UNSAFE":
        return {
            "dialogue_id": _new_id("dlg"),
            "status": "NOT_GENERATED_UNSAFE",
            "note": "不安全关系不进入面对面冲突对话流程。",
            "next_action": "ROUTE_TO_SAFETY_SUPPORT",
        }
    if mode == "MUTUAL_WORKSPACE" and not both_parties_consented:
        return {
            "dialogue_id": _new_id("dlg"),
            "status": "BLOCKED_CONSENT",
            "note": "共享修复工作区需要双方分别明确授权。",
            "next_action": "REQUEST_MUTUAL_CONSENT",
        }

    return {
        "dialogue_id": _new_id("dlg"),
        "status": "READY",
        "mode": mode,
        "single_issue": single_issue,
        "protocol": [{"step": index + 1, "instruction": text} for index, text in enumerate(DIALOGUE_PROTOCOL)],
        "simulated_reply_label": (
            "这是模拟回应，不代表对方实际想法。" if mode == "SOLO_REHEARSAL" else None
        ),
        "private_draft_separated": True,
        "shared_content_requires_consent": mode == "MUTUAL_WORKSPACE",
        "pause_contract": {
            "trigger": "任一方激活过高、出现人身攻击或无法复述时",
            "action": "暂停并约定返回时间，暂停不等于结束对话",
        },
        "system_does_not": [
            "系统不替任何一方判断对方真实想法。",
            "系统不裁决谁对谁错。",
        ],
        "next_action": "BUILD_ACCOUNTABLE_APOLOGY",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-50 accountable_apology_and_amends_builder
# ─────────────────────────────────────────────────────────────────────────────

APOLOGY_PARTS: tuple[tuple[str, str], ...] = (
    ("SPECIFIC_BEHAVIOR", "具体行为：我做了什么"),
    ("OWNERSHIP", "明确承担：这是我的选择和责任"),
    ("IMPACT", "承认影响：它可能怎样影响了你"),
    ("GENUINE_REGRET", "表达真实歉意：不要求对方安慰自己"),
    ("AMENDS", "更正或补偿：能恢复什么现实损失"),
    ("CHANGE_PLAN", "改变计划：以后怎样减少重演"),
    ("RESPECT_CHOICE", "尊重对方选择：不要求立即原谅、回应或恢复关系"),
)
INVALID_APOLOGY_CODES: dict[str, str] = {
    "IF_APOLOGY": "「如果你觉得受伤，我道歉。」",
    "BUT_APOLOGY": "「对不起，但你也有问题。」",
    "SELF_CONDEMNATION": "「我就是垃圾，你别生气了。」",
    "FORGIVENESS_PRESSURE": "「我已经道歉了，你必须翻篇。」",
    "ABSTRACT_APOLOGY": "「反正都是我不好。」",
    "IMAGE_REPAIR_ONLY": "只担心自己被怎么看，没有处理实际损害",
}
_INVALID_APOLOGY_PATTERNS: tuple[tuple[str, str], ...] = (
    ("IF_APOLOGY", r"如果你(觉得|感到).{0,6}(受伤|不舒服|被冒犯)"),
    ("BUT_APOLOGY", r"(对不起|抱歉|我道歉).{0,12}(但是|但你|不过你|你也有)"),
    ("SELF_CONDEMNATION", r"(我就是(个)?(垃圾|烂人|废物)|我什么都做不好|我根本不配)"),
    ("FORGIVENESS_PRESSURE", r"(我都道歉了|你必须(原谅|翻篇)|应该可以过去了吧)"),
    ("ABSTRACT_APOLOGY", r"(反正都是我不好|都怪我行了吧)"),
)
_INVALID_APOLOGY_RE = tuple((code, re.compile(pattern)) for code, pattern in _INVALID_APOLOGY_PATTERNS)


def build_apology(
    *,
    specific_behavior: str,
    impact: str,
    amends: str | None = None,
    change_plan: str | None = None,
    draft_text: str | None = None,
) -> dict[str, Any]:
    """A healthy apology owns behaviour; it never asks the injured party to comfort the apologiser."""
    for text in (specific_behavior, impact, amends or "", change_plan or "", draft_text or ""):
        if text:
            validate_safe_text(text)

    invalid = [
        {"code": code, "example": INVALID_APOLOGY_CODES[code], "matched": match.group(0)}
        for code, pattern in _INVALID_APOLOGY_RE
        if draft_text and (match := pattern.search(draft_text))
    ]
    if draft_text and "我" not in draft_text:
        invalid.append({"code": "ABSTRACT_APOLOGY", "example": INVALID_APOLOGY_CODES["ABSTRACT_APOLOGY"], "matched": ""})

    missing = []
    if not amends:
        missing.append("AMENDS")
    if not change_plan:
        missing.append("CHANGE_PLAN")

    composed = (
        f"我{specific_behavior}，这是我的选择和责任。它{impact}。"
        + (f"我会{amends}。" if amends else "")
        + (f"以后我会{change_plan}。" if change_plan else "")
        + "你可以决定要不要回应、什么时候回应，我不会催你原谅。"
    )
    validate_safe_text(composed)

    return {
        "apology_id": _new_id("apo"),
        "status": "NEEDS_REVISION" if invalid else "READY",
        "parts": [{"code": code, "description": text} for code, text in APOLOGY_PARTS],
        "missing_parts": missing,
        "invalid_patterns": invalid,
        "composed_draft": composed,
        "auto_sent": False,
        "rules": [
            "道歉不是自我羞辱；承担行为，不是把注意力转到安慰你自己。",
            "道歉不能附带条件、反控诉或催促原谅。",
            "对方仍然可以不回应、不原谅、不恢复关系。",
        ],
        "next_action": "DIFFERENTIATE_FORGIVENESS",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-51 forgiveness_trust_reconciliation_differentiator
# ─────────────────────────────────────────────────────────────────────────────

SEPARATION_MODEL: tuple[tuple[str, str, bool], ...] = (
    ("NAME_THE_HARM", "命名伤害：承认发生了什么", False),
    ("GRIEF_AND_ANGER", "哀伤与愤怒：允许真实情绪", False),
    ("STOP_RETALIATION", "停止报复：不以毁灭对方为目标", False),
    ("FORGIVENESS_PROCESS", "宽恕过程：按你的信仰框架逐步释放报复与终极审判的执念", False),
    ("REAL_WORLD_JUSTICE", "现实公义：报告、申诉、法律后果、保护他人", False),
    ("TRUST", "信任：根据可靠证据开放风险", True),
    ("RECONCILIATION", "和好：双方承认、承担并重建关系", True),
    ("ROLE_RESTORATION", "恢复角色：恢复原有权限、职位或亲密程度", True),
)
FORGIVENESS_PRINCIPLES: tuple[str, ...] = (
    "宽恕不要求否认伤害",
    "宽恕不要求停止哀伤",
    "宽恕不取消边界",
    "宽恕不取消现实后果",
    "宽恕不等于忘记",
    "宽恕不自动恢复信任",
    "宽恕不强迫重新接触",
    "宽恕速度不能作为属灵成熟评分",
)
FRAMEWORK_SOURCES: tuple[str, ...] = ("USER_SELECTED_THEOLOGY", "CHURCH_CONFIGURED_PRINCIPLES", "GENERAL_RELATIONAL_PRINCIPLES")


def differentiate_forgiveness(
    *,
    harm_type: str,
    still_feels_anger: bool = False,
    pursuing_destruction: bool = False,
    can_separate_justice_from_revenge: bool = True,
    relationship_safety: str = "UNKNOWN",
    framework_source: str = "GENERAL_RELATIONAL_PRINCIPLES",
) -> dict[str, Any]:
    """Eight separate things. Anger alone never means the user has not forgiven."""
    if framework_source not in FRAMEWORK_SOURCES:
        raise ValueError(f"unknown framework source: {framework_source}")
    validate_safe_text(harm_type)

    return {
        "differentiation_id": _new_id("fgv"),
        "harm_type": harm_type,
        "framework_source": framework_source,
        "separation_model": [
            {"code": code, "meaning": meaning, "depends_on_other_party": depends}
            for code, meaning, depends in SEPARATION_MODEL
        ],
        "independent_of_other_party": [code for code, _, depends in SEPARATION_MODEL if not depends],
        "requires_other_party": [code for code, _, depends in SEPARATION_MODEL if depends],
        "principles": list(FORGIVENESS_PRINCIPLES),
        "anger_does_not_disprove_forgiveness": True,
        "assessment_questions": [
            "你是否仍以毁灭、报复或控制对方为主要目标？",
            "你能否把追求公义与报复区分开？",
            "你能否在保持边界的同时，逐渐不被这件事完全支配？",
        ],
        "observed": {
            "still_feels_anger": still_feels_anger,
            "pursuing_destruction": pursuing_destruction,
            "can_separate_justice_from_revenge": can_separate_justice_from_revenge,
        },
        "system_conclusion": None,
        "conclusion_note": "系统不判定你是否已经宽恕；这由你自己（以及你的信仰框架）来判断。",
        "contact_note": (
            "在持续伤害或不安全关系中，保持距离可能正是成熟的边界。"
            if relationship_safety in {"CAUTION", "UNSAFE"} else None
        ),
        "next_action": "PLAN_REPAIR_AND_RESTITUTION",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-52 relationship_repair_restitution_planner
# ─────────────────────────────────────────────────────────────────────────────

REPAIR_MODES: tuple[str, ...] = ("UNILATERAL", "MUTUAL")
RESTITUTION_KINDS: tuple[str, ...] = (
    "RETURN_PROPERTY", "CORRECT_MISINFORMATION", "PUBLIC_CORRECTION", "FINANCIAL_REPAYMENT",
    "STOP_BEHAVIOR", "RESTATE_BOUNDARY", "THIRD_PARTY_NOTIFICATION", "TIME_AND_PRESENCE",
)


def plan_restitution(
    *,
    mode: str,
    items: list[dict[str, Any]],
    other_party_consented: bool = False,
    relationship_safety: str = "UNKNOWN",
) -> dict[str, Any]:
    """Only the user's own commitments are planned; the other party's response is never scheduled."""
    if mode not in REPAIR_MODES:
        raise ValueError(f"unknown repair mode: {mode}")
    if mode == "MUTUAL" and not other_party_consented:
        return {
            "plan_id": _new_id("rst"),
            "status": "DOWNGRADED_TO_UNILATERAL",
            "reason": "OTHER_PARTY_CONSENT_MISSING",
            "note": "对方没有参与时，仍然可以完成你自己那一部分的修复。",
            "next_action": "EXECUTE_UNILATERAL_ITEMS",
        }
    if relationship_safety == "UNSAFE":
        return {
            "plan_id": _new_id("rst"),
            "status": "NOT_GENERATED_UNSAFE",
            "note": "不安全关系不进入普通修复与补偿流程。",
            "next_action": "ROUTE_TO_SAFETY_SUPPORT",
        }

    records = []
    for item in items:
        kind = str(item.get("kind") or "")
        if kind not in RESTITUTION_KINDS:
            raise ValueError(f"unknown restitution kind: {kind}")
        description = validate_safe_text(str(item.get("description") or ""))
        records.append({
            "kind": kind,
            "description": description,
            "due_in_days": int(item.get("due_in_days", 7) or 7),
            "verifiable_by": item.get("verifiable_by") or "用户自述 + 48–72 小时后复核",
            "status": "PLANNED",
        })

    return {
        "plan_id": _new_id("rst"),
        "status": "READY",
        "mode": mode,
        "items": records,
        "verification_window_days": 3,
        "outcome_not_guaranteed": "完成这些行动不保证关系恢复；对方仍然可以不回应、不原谅、不恢复关系。",
        "user_responsible_for": ["按时执行", "如实记录", "不催促对方"],
        "next_action": "ROUTE_REPAIR_OUTCOME",
        "rule_version": RULE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-53 repair_outcome_trust_rebuild_decision_router
# ─────────────────────────────────────────────────────────────────────────────

TRUST_LADDER: dict[str, str] = {
    "TR0": "证据不足或仍不安全",
    "TR1": "只有承诺或道歉，尚无行为证据",
    "TR2": "完成低风险、短周期承诺",
    "TR3": "多次稳定履行，旧行为明显减少",
    "TR4": "可以逐步开放更高风险权限",
    "TR5": "信任大体恢复，但保留成熟边界与复现协议",
}
TRUST_ORDER: tuple[str, ...] = ("TR0", "TR1", "TR2", "TR3", "TR4", "TR5")
TRUST_RANK: dict[str, int] = {level: index for index, level in enumerate(TRUST_ORDER)}
TRUST_DOMAINS: tuple[str, ...] = (
    "EMOTIONAL_CONFIDENTIALITY", "TIME_RELIABILITY", "FINANCE", "CHILD_CARE",
    "WORK_AUTHORITY", "SPIRITUAL_LEADERSHIP", "PHYSICAL_SAFETY",
)
DECISION_OPTIONS: tuple[str, ...] = (
    "CONTINUE_REBUILDING", "LIMIT_CONTACT", "REQUEST_MEDIATION", "PAUSE_RELATIONSHIP", "EXIT_RELATIONSHIP",
)


def route_repair_outcome(
    *,
    domain: str,
    apology_delivered: bool,
    restitution_completed: bool,
    old_behavior_stopped_weeks: int = 0,
    boundary_respected: bool = False,
    safety_concern: bool = False,
    repeated_violation: bool = False,
) -> dict[str, Any]:
    """Trust is per-domain and evidence-based — the system offers options, never the decision."""
    if domain not in TRUST_DOMAINS:
        raise ValueError(f"unknown trust domain: {domain}")

    if safety_concern:
        level = "TR0"
    elif not apology_delivered and not restitution_completed:
        level = "TR0"
    elif apology_delivered and not restitution_completed:
        level = "TR1"
    elif restitution_completed and old_behavior_stopped_weeks < 4:
        level = "TR2"
    elif old_behavior_stopped_weeks >= 4 and boundary_respected and not repeated_violation:
        level = "TR3"
    else:
        level = "TR2"
    if level == "TR3" and old_behavior_stopped_weeks >= 12:
        level = "TR4"
    if level == "TR4" and old_behavior_stopped_weeks >= 26 and boundary_respected:
        level = "TR5"

    options: list[dict[str, str]] = []
    if safety_concern:
        options = [
            {"option": "EXIT_RELATIONSHIP", "because": "存在安全顾虑时，退出或暂停是被支持的选择"},
            {"option": "LIMIT_CONTACT", "because": "先把接触降到最低，并保留记录"},
        ]
    elif repeated_violation:
        options = [
            {"option": "LIMIT_CONTACT", "because": "同类越界重复发生"},
            {"option": "REQUEST_MEDIATION", "because": "需要第三方在场才能继续沟通"},
            {"option": "PAUSE_RELATIONSHIP", "because": "暂停并观察是否有实际改变"},
        ]
    else:
        options = [
            {"option": "CONTINUE_REBUILDING", "because": f"当前信任证据为 {level}"},
            {"option": "LIMIT_CONTACT", "because": "你可以在任何阶段选择缩小范围"},
        ]

    return {
        "routing_id": _new_id("trr"),
        "domain": domain,
        "trust_level": level,
        "trust_level_label": TRUST_LADDER[level],
        "trust_is_not": ["0 或 100", "原谅或不原谅", "完全开放或彻底断联"],
        "evidence": {
            "apology_delivered": apology_delivered,
            "restitution_completed": restitution_completed,
            "old_behavior_stopped_weeks": old_behavior_stopped_weeks,
            "boundary_respected": boundary_respected,
            "repeated_violation": repeated_violation,
        },
        "options": options,
        "system_decides": False,
        "decision_note": "系统只给出有证据支撑的选项；是否维持关系由你决定。",
        "relationship_evidence_levels": RELATIONSHIP_EVIDENCE_LEVELS,
        "next_action": "TRACK_AS_REAL_LIFE_EVENT",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 状态机与自描述
# ─────────────────────────────────────────────────────────────────────────────

WORKFLOW_NODES: tuple[str, ...] = (
    "EM-44_perspective_taking", "EM-45_motive_calibrator", "EM-46_boundary_guard",
    "EM-47_enforcement_planner", "EM-48_issue_framer", "EM-49_dialogue_facilitator",
    "EM-50_apology_builder", "EM-51_forgiveness_differentiator", "EM-52_restitution_planner",
    "EM-53_outcome_router",
)

STATE_MACHINE: tuple[tuple[str, str], ...] = (
    ("PERSPECTIVE_TAKEN", "MOTIVE_CALIBRATED"),
    ("MOTIVE_CALIBRATED", "BOUNDARY_MAPPED"),
    ("BOUNDARY_MAPPED", "ENFORCEMENT_PLANNED"),
    ("ENFORCEMENT_PLANNED", "ISSUE_FRAMED"),
    ("ISSUE_FRAMED", "DIALOGUE_READY"),
    ("ISSUE_FRAMED", "NOT_READY_PAUSE_FIRST"),
    ("DIALOGUE_READY", "APOLOGY_BUILT"),
    ("APOLOGY_BUILT", "FORGIVENESS_DIFFERENTIATED"),
    ("FORGIVENESS_DIFFERENTIATED", "RESTITUTION_PLANNED"),
    ("RESTITUTION_PLANNED", "OUTCOME_ROUTED"),
    ("OUTCOME_ROUTED", "TRACKED_IN_REAL_LIFE"),
)


def describe_conflict_engine() -> dict[str, Any]:
    return {
        "module": "emotional_maturity_conflict_and_repair",
        "short_name": "EMD-OS Batch 6",
        "batch": 6,
        "skills": list(WORKFLOW_NODES),
        "relationship_evidence_levels": RELATIONSHIP_EVIDENCE_LEVELS,
        "boundary_objects": list(BOUNDARY_OBJECTS),
        "enforcement_ladder": ENFORCEMENT_LADDER,
        "dirty_conflict_codes": DIRTY_CONFLICT_CODES,
        "clean_conflict_allows": list(CLEAN_CONFLICT_ALLOWS),
        "dialogue_protocol": list(DIALOGUE_PROTOCOL),
        "apology_parts": [{"code": code, "description": text} for code, text in APOLOGY_PARTS],
        "invalid_apology_patterns": INVALID_APOLOGY_CODES,
        "separation_model": [
            {"code": code, "meaning": meaning, "depends_on_other_party": depends}
            for code, meaning, depends in SEPARATION_MODEL
        ],
        "forgiveness_principles": list(FORGIVENESS_PRINCIPLES),
        "trust_ladder": TRUST_LADDER,
        "trust_domains": list(TRUST_DOMAINS),
        "decision_options": list(DECISION_OPTIONS),
        "does_not": [
            "不把同理心当作认可对方的行为",
            "不替对方回答动机",
            "不把控制包装成边界",
            "不要求冲突里没有情绪",
            "不接受自我羞辱式或附带条件的道歉",
            "不把宽恕等同于信任、和好或恢复角色",
            "不因为用户仍然愤怒就断言用户没有宽恕",
            "不用宽恕速度作为属灵成熟评分",
            "不替用户决定是否维持关系",
        ],
        "engine_version": ENGINE_VERSION,
        "rule_version": RULE_VERSION,
        "state_machine": [{"from": source, "to": target} for source, target in STATE_MACHINE],
    }
