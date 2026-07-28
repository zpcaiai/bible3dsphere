"""EMD-OS presentation contract — G0 用途标注，由后端强制而非由前端自觉。

后端已经拦掉分数（`total_score` 恒为 NULL），但一个诚实的后端配一个造分数感的前端，
用户看到的仍然是「我拿了几分」。所以展示规则也写成代码：

    build_stage_display()   阶段 + 情境 + 时间范围 + 置信度，四者缺一不可
    validate_ui_payload()   拒绝任何含分数、百分比、排名或诊断措辞的载荷
    required_labels()       exploratory / 非临床 / 个人反思用途，按配置档给出

前端只要调用 `/emotional-maturity/display-contract` 就能拿到必须渲染的字段与禁用词，
契约测试会在后端侧失败，而不是等到用户看见「你的情感成熟度：72 分」。
"""
from __future__ import annotations

import re
from typing import Any

from .emotional_maturity import STAGE_IS_NOT, STAGE_LABELS, STAGE_RANK


class PresentationContractError(ValueError):
    """Raised when a payload would render as a score, ranking or diagnosis."""


# 阶段展示必须同时出现的四个字段。少一个就会变成「分数」。
REQUIRED_DISPLAY_FIELDS: tuple[str, ...] = ("stage", "context", "timeframe", "confidence")

# 载荷里绝不允许出现的键（后端已过滤，这里是第二道）。
FORBIDDEN_KEYS: frozenset[str] = frozenset({
    "score", "total_score", "emotional_maturity_total_score", "maturity_total",
    "percentile", "maturity_percentile", "rank", "ranking", "peer_ranking",
    "percentage", "progress_percent", "level_number", "grade", "stars",
    "personality_type", "attachment_diagnosis", "clinical_diagnosis",
    "spiritual_maturity_score", "spiritual_rank",
})

# 文案里绝不允许出现的措辞。
FORBIDDEN_TEXT_PATTERNS: tuple[tuple[str, str], ...] = (
    ("SCORE_LANGUAGE", r"\d+\s*分|得分|总分|评分为|打分"),
    ("PERCENT_LANGUAGE", r"\d+\s*%|百分位|超过了?\s*\d+\s*%的"),
    ("RANKING_LANGUAGE", r"排名|第\s*\d+\s*名|比其他(用户|弟兄|姊妹)"),
    ("DIAGNOSIS_LANGUAGE", r"你患有|你被诊断|你就是.{0,4}型人格|确诊为"),
    ("PERMANENCE_LANGUAGE", r"你(这个人)?就是|你永远|你一辈子"),
    ("SPIRITUAL_VERDICT", r"神(告诉|对你说|喜悦|不喜悦)|圣灵(已经)?离开|你不够属灵"),
)
_FORBIDDEN_TEXT_RE: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (code, re.compile(pattern)) for code, pattern in FORBIDDEN_TEXT_PATTERNS
)

CONFIDENCE_DISPLAY: dict[str, str] = {
    "INSUFFICIENT": "证据不足，只作参考",
    "PROVISIONAL": "初步印象，可能会变",
    "MODERATE": "有一定证据支持",
    "HIGHER": "多次、多情境证据一致",
}

PROFILE_LABELS: dict[str, tuple[str, ...]] = {
    "PILOT": ("exploratory", "非临床", "个人反思用途", "试点版本"),
    "PRODUCTION": ("exploratory", "非临床"),
}


def required_labels(profile: str = "PILOT") -> tuple[str, ...]:
    if profile not in PROFILE_LABELS:
        raise PresentationContractError(f"unknown profile: {profile}")
    return PROFILE_LABELS[profile]


def build_stage_display(
    *,
    dimension_code: str,
    dimension_name: str,
    stage: str,
    context: str,
    timeframe: str,
    confidence: str,
    evidence_count: int = 0,
    profile: str = "PILOT",
) -> dict[str, Any]:
    """The only sanctioned way to render a stage."""
    if stage not in STAGE_RANK:
        raise PresentationContractError(f"unknown stage: {stage}")
    if confidence not in CONFIDENCE_DISPLAY:
        raise PresentationContractError(f"unknown confidence: {confidence}")
    if not context or not timeframe:
        raise PresentationContractError("阶段展示必须带情境与时间范围")

    return {
        "dimension_code": dimension_code,
        "dimension_name": dimension_name,
        "stage": stage,
        "stage_label": STAGE_LABELS[stage],
        "context": context,
        "timeframe": timeframe,
        "confidence": confidence,
        "confidence_label": CONFIDENCE_DISPLAY[confidence],
        "evidence_count": evidence_count,
        "labels": list(required_labels(profile)),
        "disclaimers": list(STAGE_IS_NOT),
        "score": None,
        "comparable_across_users": False,
        "render_as": "TEXT_WITH_CONTEXT",
        "render_as_forbidden": ["PROGRESS_BAR", "GAUGE", "RADAR_SCORE", "LEADERBOARD"],
    }


# 用户自己写的文字会被原样回显（意图确认、日记摘录）。那些字段里出现「总分」
# 只说明用户打了这两个字，不代表系统在给分——红队用例发现，不区分这两者会让
# 任何输入了「总分」的用户把自己的页面搞成 invalid，反而逼着前端绕过契约。
USER_AUTHORED_KEYS: frozenset[str] = frozenset({
    "life_season", "open_response", "objective_facts", "user_interpretations",
    "behavior_summary", "note", "notes", "target_issue", "free_text", "verbatim",
    "user_correction", "accepted", "submitted", "echo",
})


def _path_segments(path: str) -> list[str]:
    """`$.a.b[0].c` -> ['a', 'b', 'c'] — indices are not field names."""
    return [
        segment.split("[", 1)[0]
        for segment in path.split(".")[1:]
        if segment.split("[", 1)[0]
    ]


def _is_user_authored(path: str) -> bool:
    """Match whole path segments, never substrings.

    The first version used `f".{key}" in path`, so any system field whose name merely
    *started with* a user key slipped through: `accepted_stage`, `notes_from_system` and
    `echo_verdict` all matched and were skipped by the forbidden-language check. A
    validator that can be bypassed by choosing a field name is not a validator.
    """
    return any(segment in USER_AUTHORED_KEYS for segment in _path_segments(path))


def validate_ui_payload(
    payload: Any, *, path: str = "$", strict_user_content: bool = False,
) -> dict[str, Any]:
    """Walk an outbound payload and reject anything that reads as a score.

    Text the user wrote is skipped unless `strict_user_content=True`: echoing it back is
    not the system making a claim. Forbidden **keys** are still rejected everywhere — a
    `total_score` field is the system's, whatever it sits next to.
    """
    violations: list[dict[str, str]] = []
    skipped_user_content: list[str] = []

    def walk(node: Any, current: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                lowered = str(key).lower()
                if lowered in FORBIDDEN_KEYS and value is not None:
                    violations.append({
                        "code": "FORBIDDEN_KEY", "path": f"{current}.{key}",
                        "detail": f"'{key}' 不得出现在展示载荷中",
                    })
                walk(value, f"{current}.{key}")
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{current}[{index}]")
        elif isinstance(node, str):
            if not strict_user_content and _is_user_authored(current):
                skipped_user_content.append(current)
                return
            for code, pattern in _FORBIDDEN_TEXT_RE:
                match = pattern.search(node)
                if match:
                    violations.append({
                        "code": code, "path": current,
                        "detail": f"禁用措辞：{match.group(0)}",
                    })
                    break

    walk(payload, path)
    return {
        "valid": not violations,
        "violations": violations,
        "skipped_user_content": skipped_user_content,
        "checked_keys": len(FORBIDDEN_KEYS),
        "checked_patterns": len(FORBIDDEN_TEXT_PATTERNS),
    }


def display_contract(profile: str = "PILOT") -> dict[str, Any]:
    """What the frontend must render — served to the client so there is one source of truth."""
    return {
        "contract_version": "emd-display-contract-1.0",
        "profile": profile,
        "required_fields_per_stage": list(REQUIRED_DISPLAY_FIELDS),
        "required_labels": list(required_labels(profile)),
        "disclaimers": list(STAGE_IS_NOT),
        "forbidden_keys": sorted(FORBIDDEN_KEYS),
        "forbidden_language": [{"code": code, "example": pattern} for code, pattern in FORBIDDEN_TEXT_PATTERNS],
        "allowed_visualisations": ["TEXT_WITH_CONTEXT", "TIMELINE_OF_EVENTS", "STAGE_DESCRIPTION_CARD"],
        "forbidden_visualisations": ["PROGRESS_BAR", "GAUGE", "RADAR_SCORE", "LEADERBOARD", "PERCENTILE_BADGE"],
        "confidence_vocabulary": CONFIDENCE_DISPLAY,
        "stage_vocabulary": STAGE_LABELS,
        "rationale": (
            "阶段不是分数。任何进度条、仪表盘或雷达图都会把「当前一段时间的表现」"
            "读成「我这个人的等级」，这正是本系统要避免的伤害。"
        ),
    }
