"""Skill 01 - case-intake-normalizer (deterministic + llm)."""

from __future__ import annotations

import re

from .models import (
    ConsentScope,
    DiscernmentCase,
    FailureCode,
    NormalizedCase,
    SkillFailure,
    SourceKind,
    TextSegment,
)

SKILL_ID = "case-intake-normalizer"
SKILL_VERSION = "0.1.0"

MIN_INPUT_LENGTH = 12

_SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?；;\n])")
_USER_VOICE = ("我觉得", "我认为", "我担心", "我常常", "我总是", "我每天", "我希望", "我很")
_QUOTE_MARKERS = ("宣称", "说：", "表示", "写道", "“", "\"")
_CONFLICT_PAIRS = (("从不", "有时"), ("总是", "偶尔"), ("绝对", "可能"))


def _clean(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    lines = [line.strip() for line in text.split("\n")]
    deduped: list[str] = []
    for line in lines:
        if line and (not deduped or deduped[-1] != line):
            deduped.append(line)
    return "\n".join(deduped).strip()


def _segments(text: str, self_reflection: bool) -> tuple[list[TextSegment], list[TextSegment]]:
    """Split source text into analysed-object vs user-reaction segments.

    Provenance is marked; nothing is rewritten and no motive is invented.
    """

    analysed: list[TextSegment] = []
    reaction: list[TextSegment] = []
    cursor = 0
    index = 0
    for raw in _SENTENCE_SPLIT.split(text):
        chunk = raw.strip()
        if not chunk:
            cursor += len(raw)
            continue
        start = text.find(chunk, cursor)
        end = start + len(chunk)
        cursor = end
        index += 1
        is_user_voice = any(marker in chunk for marker in _USER_VOICE)
        if self_reflection:
            kind = SourceKind.USER_COMMENT
        elif is_user_voice:
            kind = SourceKind.USER_COMMENT
        elif any(marker in chunk for marker in _QUOTE_MARKERS):
            kind = SourceKind.QUOTE
        else:
            kind = SourceKind.PARAPHRASE
        segment = TextSegment(
            segment_id=f"seg-{index:03d}",
            text=chunk,
            source_kind=kind,
            start=start,
            end=end,
        )
        if kind is SourceKind.USER_COMMENT:
            reaction.append(segment)
        else:
            analysed.append(segment)
    return analysed, reaction


def _missing_context(case: DiscernmentCase, text: str) -> list[str]:
    missing: list[str] = []
    if not case.source_metadata:
        missing.append("缺少来源元数据（出处、时间、平台）")
    if case.subject_type.value == "person" and "http" not in text:
        missing.append("缺少可核验的公开材料链接")
    if len(text) < 60:
        missing.append("材料篇幅很短，可能不足以支撑模式性判断")
    if "年" not in text and "月" not in text:
        missing.append("缺少明确时间范围")
    return missing


def _conflicts(text: str) -> list[str]:
    found: list[str] = []
    for a, b in _CONFLICT_PAIRS:
        if a in text and b in text:
            found.append(f"材料中同时出现“{a}”与“{b}”，存在张力，未自行裁决")
    return found


def _topic(text: str) -> str:
    first = _SENTENCE_SPLIT.split(text)[0].strip()
    return first[:40] if first else text[:40]


def normalize(case: DiscernmentCase) -> NormalizedCase:
    """Produce ``normalized_case``. Adds no facts and judges no motives."""

    cleaned = _clean(case.raw_input)
    if len(cleaned) < MIN_INPUT_LENGTH:
        raise SkillFailure(
            FailureCode.INSUFFICIENT_EVIDENCE,
            "输入过短，无法在不臆测的前提下规范化",
        )

    self_reflection = case.subject_type.value == "self_reflection"
    analysed, reaction = _segments(cleaned, self_reflection)

    known_facts = [
        seg.text for seg in analysed if seg.source_kind is SourceKind.QUOTE
    ]
    unknowns = [
        "当事人的内在动机（系统不可读心，只能作假设）",
        "材料之外的行为模式是否一致",
    ]

    consent: ConsentScope = case.consent_scope
    return NormalizedCase(
        case_id=case.case_id,
        subject_type=case.subject_type,
        topic=_topic(cleaned),
        subject_description=cleaned if self_reflection else " ".join(
            seg.text for seg in analysed
        )[:400],
        user_goal=case.user_goal,
        faith_context=case.faith_context,
        sensitivity=case.sensitivity,
        consent_scope=consent,
        analyzed_object_segments=analysed,
        user_reaction_segments=reaction,
        known_facts=known_facts,
        unknowns=unknowns,
        missing_context=_missing_context(case, cleaned),
        conflicts=_conflicts(cleaned),
        time_range=str(case.source_metadata.get("time_range", "unspecified")),
        source_metadata=case.source_metadata,
    )
