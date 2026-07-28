"""EMD-OS psychometric fieldwork — G1, the parts a machine can carry.

Two checklist items need humans in a room: cognitive interviews (does the respondent
understand the item the way we meant it?) and inter-rater agreement (do two scorers give
the same open response the same stage?). Nothing here replaces either. What it does is
remove every excuse *around* them: the protocol, the recording schema, the sampling, the
agreement maths, and the disagreement triage all exist, so the human work is exactly the
work that needs a human.

Design decisions worth stating:

* **Cohen's κ, not raw percent agreement.** With six ordered stages and a lumpy
  distribution, two raters who both default to E2 can hit 70% agreement by accident. κ
  corrects for that; `agreement_report()` reports both and flags when they diverge.
* **Adjacent disagreement is tracked separately.** E2-vs-E3 and E1-vs-E5 are not the same
  failure. A rubric with fuzzy neighbouring anchors is fixable; raters who disagree by
  three stages means the anchors are not describing observable behaviour at all.
* **Interviews sample the items nobody has probed yet**, not the convenient ones —
  `select_interview_items()` deliberately prefers untested dimensions and phrasing that
  earlier sessions flagged as confusing.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from itertools import combinations
from typing import Any

from .emotional_maturity import DIMENSION_BY_CODE, DIMENSION_CODES, STAGES, STAGE_RANK


PROTOCOL_VERSION = "emd-cognitive-interview-1.0"
AGREEMENT_VERSION = "emd-inter-rater-1.0"


# ═════════════════════════════════════════════════════════════════════════════
# 认知访谈
# ═════════════════════════════════════════════════════════════════════════════

# 「说出你的理解」四步法。顺序重要：先复述，再解释，最后才问选项，
# 否则受访者会先被选项框住，我们就再也看不到他原本的理解了。
INTERVIEW_STEPS: tuple[dict[str, str], ...] = (
    {
        "step": "PARAPHRASE",
        "prompt": "请用你自己的话，把这道题在问什么再说一遍。",
        "looking_for": "复述与题目原意是否一致；有没有多出或漏掉条件。",
    },
    {
        "step": "RECALL",
        "prompt": "你刚才回答的时候，脑子里想到的是哪一件具体的事？",
        "looking_for": "回忆的是真实事件还是泛泛印象；时间范围对不对。",
    },
    {
        "step": "DECISION",
        "prompt": "你是怎么在这几个选项之间做决定的？为什么不是旁边那个？",
        "looking_for": "选项之间的界线是否可分辨；有没有靠猜。",
    },
    {
        "step": "DIFFICULTY",
        "prompt": "这道题里有没有哪个词让你犹豫、或者觉得可以有两种理解？",
        "looking_for": "歧义词、文化预设、宗教术语、翻译腔。",
    },
)

# 已知的高危词。这些不是猜的：它们要么一词多义，要么在不同传统里含义相反。
KNOWN_AMBIGUOUS_TERMS: tuple[dict[str, str], ...] = (
    {"term": "真我", "risk": "在心理学与不同神学传统里指向相反的东西"},
    {"term": "顺服", "risk": "可能被读成健康的委身，也可能被读成对施害者的服从"},
    {"term": "放下", "risk": "与「宽恕」「压抑」「回避」难以区分"},
    {"term": "界线", "risk": "常被误解为疏远或不属灵"},
    {"term": "情绪化", "risk": "带贬义，会让人低报真实反应"},
    {"term": "属灵", "risk": "在自评里会触发社会赞许作答"},
    {"term": "最近", "risk": "时间范围因人而异，从一周到一年不等"},
    {"term": "经常", "risk": "频率词没有锚点，无法跨人比较"},
)

FINDING_TYPES: tuple[str, ...] = (
    "MISREAD",            # 复述与原意不符
    "AMBIGUOUS_TERM",     # 某个词有两种理解
    "OPTION_INDISTINCT",  # 相邻选项分不出来
    "RECALL_MISMATCH",    # 想到的事件与题目要问的不是一回事
    "SOCIAL_DESIRABILITY",  # 明显往「好」的方向答
    "EMOTIONAL_BURDEN",   # 题目本身造成不适
    "CULTURAL_MISMATCH",  # 前提在受访者的处境里不成立
    "OK",                 # 理解一致
)
BLOCKING_FINDINGS: frozenset[str] = frozenset({
    "MISREAD", "AMBIGUOUS_TERM", "OPTION_INDISTINCT", "EMOTIONAL_BURDEN",
})


def build_interview_protocol(
    *,
    item_id: str,
    item_text: str,
    dimension_code: str,
    locale: str = "zh-CN",
) -> dict[str, Any]:
    """Everything the interviewer reads aloud, plus what to write down."""
    if dimension_code not in DIMENSION_BY_CODE:
        raise ValueError(f"unknown dimension: {dimension_code}")

    flagged = [entry for entry in KNOWN_AMBIGUOUS_TERMS if entry["term"] in item_text]
    return {
        "protocol_version": PROTOCOL_VERSION,
        "item_id": item_id,
        "item_text": item_text,
        "dimension_code": dimension_code,
        "dimension_name": DIMENSION_BY_CODE[dimension_code]["name"],
        "locale": locale,
        "steps": list(INTERVIEW_STEPS),
        "terms_to_probe": flagged,
        "interviewer_rules": [
            "先让受访者作答，再开始追问；不要在作答前解释题意。",
            "不要说「对」「不对」，也不要点头纠正——你在测题目，不是在测人。",
            "受访者说不清楚时，重复他自己的话，不要替他补完。",
            "如果题目引起明显不适，立刻停下并说明可以跳过。",
        ],
        "record_verbatim": True,
        "expected_minutes": 3,
    }


def select_interview_items(
    *,
    available_items: list[dict[str, Any]],
    already_probed: list[str] | None = None,
    prior_findings: list[dict[str, Any]] | None = None,
    per_session: int = 8,
) -> dict[str, Any]:
    """Choose which items this session probes — coverage first, then known trouble."""
    probed = set(already_probed or [])
    troubled = {
        str(finding.get("item_id"))
        for finding in (prior_findings or [])
        if finding.get("finding_type") in BLOCKING_FINDINGS
    }
    covered_dimensions = {
        str(item.get("dimension_code"))
        for item in available_items if str(item.get("item_id")) in probed
    }

    def priority(item: dict[str, Any]) -> tuple[int, int, str]:
        item_id = str(item.get("item_id"))
        dimension = str(item.get("dimension_code"))
        return (
            0 if item_id in troubled else 1,          # 先回访出过问题的
            0 if dimension not in covered_dimensions else 1,  # 再补没覆盖的维度
            item_id,
        )

    ordered = sorted(available_items, key=priority)
    chosen = ordered[:per_session]
    return {
        "selected": chosen,
        "selected_ids": [str(item.get("item_id")) for item in chosen],
        "revisits": [str(item.get("item_id")) for item in chosen if str(item.get("item_id")) in troubled],
        "dimensions_still_unprobed": sorted(set(DIMENSION_CODES) - covered_dimensions - {
            str(item.get("dimension_code")) for item in chosen
        }),
        "rationale": "优先回访已知有问题的题目，其次补足未覆盖的维度。",
    }


def analyse_interviews(
    findings: list[dict[str, Any]],
    *,
    minimum_interviews: int = 5,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Turn a pile of session notes into a verdict per item."""
    moment = now or datetime.now(timezone.utc)
    participants = {str(finding.get("participant_id")) for finding in findings if finding.get("participant_id")}

    by_item: dict[str, list[dict[str, Any]]] = {}
    for finding in findings:
        kind = str(finding.get("finding_type", "OK"))
        if kind not in FINDING_TYPES:
            raise ValueError(f"unknown finding type: {kind}")
        by_item.setdefault(str(finding.get("item_id")), []).append(finding)

    items: list[dict[str, Any]] = []
    for item_id, entries in sorted(by_item.items()):
        kinds = Counter(str(entry.get("finding_type", "OK")) for entry in entries)
        blocking = sum(count for kind, count in kinds.items() if kind in BLOCKING_FINDINGS)
        understood = kinds.get("OK", 0)
        total = len(entries)
        items.append({
            "item_id": item_id,
            "interviews": total,
            "understood_as_intended": understood,
            "blocking_findings": blocking,
            "finding_breakdown": dict(kinds),
            "verdict": (
                "REWRITE" if blocking >= 2 else
                "REVIEW" if blocking == 1 else
                "KEEP" if understood == total else "WATCH"
            ),
            "verbatim_quotes": [
                str(entry.get("quote")) for entry in entries if entry.get("quote")
            ][:5],
        })

    needs_rewrite = [item["item_id"] for item in items if item["verdict"] == "REWRITE"]
    dimensions_touched = {
        str(finding.get("dimension_code")) for finding in findings if finding.get("dimension_code")
    }
    enough = len(participants) >= minimum_interviews

    return {
        "analysed_at": moment.isoformat(),
        "protocol_version": PROTOCOL_VERSION,
        "participants": len(participants),
        "minimum_interviews": minimum_interviews,
        "sample_sufficient": enough,
        "items": items,
        "items_needing_rewrite": needs_rewrite,
        "dimensions_covered": sorted(dimensions_touched),
        "dimensions_uncovered": sorted(set(DIMENSION_CODES) - dimensions_touched),
        "gate_status": (
            "PASS" if enough and not needs_rewrite
            else "BLOCKED" if needs_rewrite
            else "INSUFFICIENT_SAMPLE"
        ),
        "note": (
            "每个维度至少要有一条题目被逐字复述并确认理解一致；"
            "任何一道题出现两次以上阻断性发现，必须改写后重测。"
        ),
    }


# ═════════════════════════════════════════════════════════════════════════════
# 评分一致性
# ═════════════════════════════════════════════════════════════════════════════

def cohens_kappa(rater_a: list[str], rater_b: list[str]) -> float:
    """Chance-corrected agreement. Returns 0.0 when the raters never vary."""
    if len(rater_a) != len(rater_b):
        raise ValueError("raters must score the same responses")
    total = len(rater_a)
    if total == 0:
        raise ValueError("no responses to compare")

    observed = sum(1 for left, right in zip(rater_a, rater_b) if left == right) / total
    counts_a, counts_b = Counter(rater_a), Counter(rater_b)
    expected = sum(
        (counts_a[label] / total) * (counts_b[label] / total)
        for label in set(counts_a) | set(counts_b)
    )
    if expected >= 1.0:
        return 0.0
    return (observed - expected) / (1 - expected)


def interpret_kappa(kappa: float) -> str:
    if kappa < 0:
        # 负 κ 不是「一致性弱」，是两位评分者系统性地反着来。
        # 归进 SLIGHT 会让 -1.0 读成「有点一致」，那是完全相反的结论。
        return "SYSTEMATIC_DISAGREEMENT"
    if kappa < 0.20:
        return "SLIGHT"
    if kappa < 0.40:
        return "FAIR"
    if kappa < 0.60:
        return "MODERATE"
    if kappa < 0.80:
        return "SUBSTANTIAL"
    return "ALMOST_PERFECT"


def agreement_report(
    scorings: list[dict[str, Any]],
    *,
    threshold: float = 0.70,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Compare two or more raters over the same open responses.

    Each entry: {"response_id", "rater_id", "stage"}. Raters need not be the same people
    across responses, but every response must have at least two scores to count.
    """
    moment = now or datetime.now(timezone.utc)
    by_response: dict[str, dict[str, str]] = {}
    for entry in scorings:
        stage = str(entry.get("stage"))
        if stage not in STAGE_RANK:
            raise ValueError(f"unknown stage: {stage}")
        by_response.setdefault(str(entry["response_id"]), {})[str(entry["rater_id"])] = stage

    double_scored = {rid: scores for rid, scores in by_response.items() if len(scores) >= 2}
    if not double_scored:
        return {
            "computed_at": moment.isoformat(), "version": AGREEMENT_VERSION,
            "responses_double_scored": 0, "status": "INSUFFICIENT_DATA",
            "note": "没有任何一条回答被两位评分者独立评过。",
        }

    pairs: list[tuple[str, str]] = []
    disagreements: list[dict[str, Any]] = []
    for response_id, scores in sorted(double_scored.items()):
        raters = sorted(scores)
        for left, right in combinations(raters, 2):
            pairs.append((scores[left], scores[right]))
            distance = abs(STAGE_RANK[scores[left]] - STAGE_RANK[scores[right]])
            if distance:
                disagreements.append({
                    "response_id": response_id,
                    "raters": [left, right],
                    "stages": [scores[left], scores[right]],
                    "distance": distance,
                    "kind": "ADJACENT" if distance == 1 else "SERIOUS",
                })

    left_scores = [pair[0] for pair in pairs]
    right_scores = [pair[1] for pair in pairs]
    exact = sum(1 for a, b in pairs if a == b) / len(pairs)
    within_one = sum(
        1 for a, b in pairs if abs(STAGE_RANK[a] - STAGE_RANK[b]) <= 1
    ) / len(pairs)
    kappa = cohens_kappa(left_scores, right_scores)
    serious = [item for item in disagreements if item["kind"] == "SERIOUS"]

    # 百分比高而 κ 低 = 两位评分者都在猜同一个众数，不是真的一致。
    inflated = exact >= threshold and kappa < 0.40

    return {
        "computed_at": moment.isoformat(),
        "version": AGREEMENT_VERSION,
        "responses_double_scored": len(double_scored),
        "comparisons": len(pairs),
        "exact_agreement": round(exact, 3),
        "within_one_stage": round(within_one, 3),
        "cohens_kappa": round(kappa, 3),
        "kappa_interpretation": interpret_kappa(kappa),
        "threshold": threshold,
        "meets_threshold": exact >= threshold and kappa >= 0.40,
        "chance_inflated": inflated,
        "disagreements": disagreements,
        "serious_disagreements": serious,
        "stage_distribution": dict(Counter(left_scores + right_scores)),
        "status": (
            "BLOCKED" if serious or kappa < 0 else
            "REVIEW" if inflated or exact < threshold else "PASS"
        ),
        "next_action": (
            "κ 为负：两位评分者系统性相反，先确认是否看错了量表方向" if kappa < 0 else
            "裁决严重分歧并修订行为锚点" if serious else
            "一致率看似达标但 κ 偏低：两位评分者可能都在选众数，需检查锚点区分度"
            if inflated else
            "补足样本或修订锚点后重测" if exact < threshold else
            "记录结果并进入下一批"
        ),
    }


def triage_disagreements(report: dict[str, Any]) -> dict[str, Any]:
    """What to actually do about each disagreement, in priority order."""
    serious = report.get("serious_disagreements", [])
    adjacent = [
        item for item in report.get("disagreements", []) if item["kind"] == "ADJACENT"
    ]
    stages_in_conflict = Counter()
    for item in adjacent:
        stages_in_conflict[tuple(sorted(item["stages"], key=lambda s: STAGE_RANK[s]))] += 1

    return {
        "resolve_first": [
            {
                "response_id": item["response_id"],
                "stages": item["stages"],
                "action": "两位评分者一起看原文，写下各自依据的行为锚点；"
                          "若两人都能自圆其说，说明锚点没有描述可观察行为，必须改写。",
            }
            for item in serious
        ],
        "boundary_pairs_needing_sharper_anchors": [
            {"between": list(pair), "occurrences": count}
            for pair, count in stages_in_conflict.most_common(3)
        ],
        "adjacent_count": len(adjacent),
        "serious_count": len(serious),
        "guidance": (
            "相邻分歧（E2/E3）多半是锚点措辞问题，可以改；"
            "跨两级以上的分歧说明锚点没有落在可观察行为上，不能只靠培训解决。"
        ),
    }


def describe_psychometrics() -> dict[str, Any]:
    return {
        "module": "formation_twin.emotional_maturity_psychometrics",
        "protocol_version": PROTOCOL_VERSION,
        "agreement_version": AGREEMENT_VERSION,
        "interview_steps": [step["step"] for step in INTERVIEW_STEPS],
        "finding_types": list(FINDING_TYPES),
        "blocking_findings": sorted(BLOCKING_FINDINGS),
        "stages": list(STAGES),
        "what_still_needs_humans": [
            "跑访谈本身（5–10 人 × 30 分钟）",
            "第二位评分者独立评 30 条开放回答",
            "对严重分歧作出裁决并改写行为锚点",
        ],
    }
