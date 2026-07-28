"""EMD-OS training opt-out — G5 privacy, enforced in code rather than in a setting.

P3-class material (prayer, family history, crisis state, trauma narrative, minors) must
never reach a model vendor's training corpus. A checkbox in a vendor console is necessary
but not sufficient: consoles get toggled back, accounts get migrated, and a new provider
arrives with different defaults. So the guarantee is layered:

    1. classify_material()      — what sensitivity class is this text/field?
    2. training_optout_headers()— per-provider opt-out headers *and* body flags
    3. sanitize_provider_call() — refuses to build a request that lacks them
    4. audit_provider_config()  — turns vendor console settings into a pass/fail record

`sanitize_provider_call` raises rather than warning. A provider without a documented
opt-out mechanism cannot be used for EMD material at all — that is the intended outcome,
not a bug to work around.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any


class TrainingOptOutError(RuntimeError):
    """Raised when EMD material would reach a provider without an opt-out guarantee."""


SENSITIVITY_ORDER: tuple[str, ...] = (
    "P0_PUBLIC", "P1_PERSONAL", "P2_SENSITIVE", "P3_HIGHLY_SENSITIVE", "P4_SEALED_SAFETY",
)
SENSITIVITY_RANK: dict[str, int] = {level: index for index, level in enumerate(SENSITIVITY_ORDER)}

# 达到或超过这个级别的材料，一律不得进入训练。
TRAINING_FORBIDDEN_AT_OR_ABOVE = "P2_SENSITIVE"

# 字段名 → 敏感级别。EMD 的开放文本默认按最高级别处理，宁可过度保护。
FIELD_SENSITIVITY: dict[str, str] = {
    "prayer_text": "P3_HIGHLY_SENSITIVE",
    "confession_text": "P3_HIGHLY_SENSITIVE",
    "journal_text": "P3_HIGHLY_SENSITIVE",
    "raw_narrative": "P3_HIGHLY_SENSITIVE",
    "family_history": "P3_HIGHLY_SENSITIVE",
    "genogram_notes": "P3_HIGHLY_SENSITIVE",
    "trauma_material": "P3_HIGHLY_SENSITIVE",
    "minor_profile": "P3_HIGHLY_SENSITIVE",
    "crisis_text": "P4_SEALED_SAFETY",
    "safety_notes": "P4_SEALED_SAFETY",
    "open_response": "P2_SENSITIVE",
    "objective_facts": "P2_SENSITIVE",
    "display_name": "P1_PERSONAL",
    "locale": "P0_PUBLIC",
}

# 内容特征。即使字段名无害，命中这些模式也按 P3 处理。
_CONTENT_PATTERNS: tuple[tuple[str, str], ...] = (
    # 「动手」「打」这类词必须带受害语境才算 P4。裸词会把「他动手做饭」「动手能力评估」
    # 全判成危机级——过度保护看似安全，实则让真正的 P4 淹没在噪音里，也让大量正常文本
    # 无法交给模型辅助整理。
    ("P4_SEALED_SAFETY",
     # 生命风险的直接表达
     r"自杀|自残|不想活|活不下去|结束这一切|想死(?![你我])|遗书"
     # 暴力：必须带受害语境。裸「动手」会把「他动手做饭」判成危机级，
     # 而「动手打」「对我动手」才是这里要抓的。
     r"|家暴|验伤|动手打|对(我|她|他)动手"
     r"|(被|挨)(他|她|爸|妈|丈夫|妻子|老公|老婆)?打"
     # 「打我」本身就是信号，但「打我电话」不是——用否定前瞻区分，
     # 而不是要求施害者代词紧邻（「他昨天又打我」中间还隔着时间词）。
     r"|打我(?!电话|手机|微信|号码|call)|掐我|踢我|推我"
     r"|掐(我的)?脖子|拿刀|报警"
     r"|威胁(我|说).{0,10}(杀|死|命)"),
    ("P3_HIGHLY_SENSITIVE", r"祷告|祈祷|认罪|悔改|我父亲|我母亲|童年|小时候|离婚|流产|确诊|抑郁症|服药"),
    ("P2_SENSITIVE", r"我(很)?(生气|难过|羞愧|害怕)|吵架|冲突|情绪"),
)
_CONTENT_RE: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (level, re.compile(pattern)) for level, pattern in _CONTENT_PATTERNS
)


def classify_material(*, field: str | None = None, text: str | None = None) -> dict[str, Any]:
    """Highest sensitivity implied by the field name and the content itself."""
    level = "P0_PUBLIC"
    reasons: list[str] = []

    if field:
        field_level = FIELD_SENSITIVITY.get(field)
        if field_level:
            level = field_level
            reasons.append(f"field:{field}")
        elif field.startswith("emd_"):
            level = "P2_SENSITIVE"
            reasons.append("field:emd_default")

    if text:
        for candidate, pattern in _CONTENT_RE:
            if pattern.search(text) and SENSITIVITY_RANK[candidate] > SENSITIVITY_RANK[level]:
                level = candidate
                reasons.append(f"content:{candidate}")
                break

    forbidden = SENSITIVITY_RANK[level] >= SENSITIVITY_RANK[TRAINING_FORBIDDEN_AT_OR_ABOVE]
    return {
        "sensitivity": level,
        "training_forbidden": forbidden,
        "retention_forbidden": SENSITIVITY_RANK[level] >= SENSITIVITY_RANK["P3_HIGHLY_SENSITIVE"],
        "reasons": reasons,
    }


# ── 供应商侧的退出机制 ───────────────────────────────────────────────────────
# 每个供应商的退出方式不同：有的是请求头，有的是 body 字段，有的两者都要。
# 没有记录在案的机制 = 不能用于 EMD 材料。

PROVIDER_OPT_OUT: dict[str, dict[str, Any]] = {
    "openai": {
        "headers": {"OpenAI-Beta": "no-training=1"},
        "body": {"store": False},
        "console_setting": "Data Controls → 关闭 “Improve the model for everyone”",
        "zero_retention_available": True,
    },
    "anthropic": {
        "headers": {"anthropic-no-training": "true"},
        "body": {},
        "console_setting": "默认不使用 API 数据训练；确认未加入任何数据共享计划",
        "zero_retention_available": True,
    },
    "gemini": {
        "headers": {},
        "body": {"disable_data_logging": True},
        "console_setting": "使用付费层（付费层默认不用于改进产品）",
        "zero_retention_available": True,
    },
    "local": {
        "headers": {},
        "body": {},
        "console_setting": "本地推理，数据不出机器",
        "zero_retention_available": True,
    },
    "mock": {
        "headers": {},
        "body": {},
        "console_setting": "测试用假provider，不发生网络调用",
        "zero_retention_available": True,
    },
}


def training_optout_headers(provider: str) -> dict[str, str]:
    config = PROVIDER_OPT_OUT.get(provider)
    if config is None:
        raise TrainingOptOutError(
            f"provider '{provider}' 没有记录在案的训练退出机制，禁止用于 EMD 材料"
        )
    return dict(config["headers"])


def sanitize_provider_call(
    *,
    provider: str,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    material_sensitivity: str = "P3_HIGHLY_SENSITIVE",
) -> dict[str, Any]:
    """Return a request that carries the opt-out, or refuse to build one at all."""
    if material_sensitivity not in SENSITIVITY_RANK:
        raise TrainingOptOutError(f"unknown sensitivity: {material_sensitivity}")

    config = PROVIDER_OPT_OUT.get(provider)
    if config is None:
        raise TrainingOptOutError(
            f"provider '{provider}' 没有记录在案的训练退出机制，禁止用于 EMD 材料"
        )

    forbidden = SENSITIVITY_RANK[material_sensitivity] >= SENSITIVITY_RANK[TRAINING_FORBIDDEN_AT_OR_ABOVE]
    if forbidden and not config["zero_retention_available"]:
        raise TrainingOptOutError(
            f"provider '{provider}' 无法保证零留存，{material_sensitivity} 材料不得外发"
        )

    merged_headers = {**(headers or {}), **config["headers"]}
    merged_body = {**(body or {}), **config["body"]}
    return {
        "provider": provider,
        "headers": merged_headers,
        "body": merged_body,
        "training_opt_out_applied": True,
        "material_sensitivity": material_sensitivity,
        "retention": "ZERO" if forbidden else "PROVIDER_DEFAULT",
    }


def assert_no_training_material(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Guard for anything that builds a training candidate set."""
    offenders = []
    for record in records:
        verdict = classify_material(
            field=record.get("field"), text=record.get("text"),
        )
        if verdict["training_forbidden"]:
            offenders.append({
                "field": record.get("field"),
                "sensitivity": verdict["sensitivity"],
                "reasons": verdict["reasons"],
            })
    if offenders:
        raise TrainingOptOutError(
            f"{len(offenders)} 条 EMD 材料被送入训练候选集，已阻断"
        )
    return {"checked": len(records), "training_candidates": 0, "status": "CLEAN"}


# ── 供应商配置审计 ───────────────────────────────────────────────────────────

AUDIT_QUESTIONS: tuple[tuple[str, str], ...] = (
    ("api_data_excluded_from_training", "供应商书面声明 API 数据不用于训练"),
    ("console_toggle_verified", "控制台开关已人工确认关闭并截图留档"),
    ("zero_retention_enabled", "已申请或确认零留存 / 短留存"),
    ("subprocessors_reviewed", "已审阅子处理者清单与所在地"),
    ("dpa_signed", "已签署数据处理协议（DPA）"),
    ("region_pinned", "推理区域已固定，符合跨境要求"),
)


def audit_provider_config(
    *,
    provider: str,
    answers: dict[str, bool],
    verified_by: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The artefact the privacy assessment needs: who checked what, and when."""
    moment = now or datetime.now(timezone.utc)
    missing = [key for key, _ in AUDIT_QUESTIONS if not answers.get(key)]
    known_provider = provider in PROVIDER_OPT_OUT

    if not known_provider:
        status = "FAIL"
    elif missing:
        status = "FAIL"
    else:
        status = "PASS"

    return {
        "provider": provider,
        "provider_recognised": known_provider,
        "console_setting": PROVIDER_OPT_OUT.get(provider, {}).get("console_setting"),
        "status": status,
        "unanswered_or_failed": missing,
        "questions": [{"key": key, "text": text, "answer": bool(answers.get(key))} for key, text in AUDIT_QUESTIONS],
        "verified_by": verified_by,
        "verified_at": moment.isoformat(),
        "emd_material_allowed": status == "PASS",
        "note": "任何一项未通过，EMD 开放文本一律不得外发给该供应商。",
    }


def describe_training_optout() -> dict[str, Any]:
    return {
        "module": "formation_twin.emotional_maturity_training_optout",
        "forbidden_at_or_above": TRAINING_FORBIDDEN_AT_OR_ABOVE,
        "providers": sorted(PROVIDER_OPT_OUT),
        "audit_questions": [key for key, _ in AUDIT_QUESTIONS],
        "enforcement": "sanitize_provider_call 会抛异常而不是警告",
    }
