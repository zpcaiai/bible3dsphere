"""
theological_safety_engine.py — 神学安全审查引擎 (Skill 9)

对"将展示给用户的 AI 输出"做福音中心的安全审查。纯逻辑模块（不访问数据库），
规则优先、AI 可选增强（与 gospel_engine 同构）。

审查维度（dimension）：
  legalism              律法主义（靠表现换取神的接纳 / 责备信心不足 / 强制公开认罪）
  prosperity_gospel     成功神学（保证成功、富足、必蒙祝福）
  spiritual_shaming     属灵羞辱（贬低、定罪、制造羞耻）
  ai_replaces_pastor    AI 取代牧者（宣称 AI 是牧者 / 不必找真人）
  crisis_without_human  危机中只给经文而不建议真实的人介入
  scripture_misuse      经文误用（把经文当成功保证）
  spiritual_scoring     属灵评分 / 等级 / 排行榜定义人的价值
  over_psychologizing   过度心理化以替代福音
  mysticism_manipulation 神秘操控（靠"足够相信"操控结果）
  disrespects_church    不尊重 / 贬低教会群体

返回：{review_status, detected_issues, corrected_content, reviewer_notes, dimensions_checked}
  review_status ∈ approved | needs_revision | blocked
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

PROMPT_VERSION = "theo-safety-v1"

DIMENSIONS: List[Dict[str, str]] = [
    {"code": "legalism", "name": "律法主义"},
    {"code": "prosperity_gospel", "name": "成功神学"},
    {"code": "spiritual_shaming", "name": "属灵羞辱"},
    {"code": "ai_replaces_pastor", "name": "AI取代牧者"},
    {"code": "crisis_without_human", "name": "危机中缺真人介入"},
    {"code": "scripture_misuse", "name": "经文误用"},
    {"code": "over_psychologizing", "name": "过度心理化"},
    {"code": "spiritual_scoring", "name": "属灵评分"},
    {"code": "mysticism_manipulation", "name": "神秘操控"},
    {"code": "disrespects_church", "name": "不尊重教会"},
]

# ── 规则库：每条规则一组正则，命中即记一个 issue ──────────────────────────────
_RULES: List[Dict[str, Any]] = [
    {
        "dimension": "legalism", "severity": 4,
        "patterns": [r"信心(太差|不足|不够)", r"不够属灵", r"必须公开认罪",
                     r"靠.{0,6}操练.{0,6}换取", r"做到.{0,8}神才(会|能)?(接纳|悦纳|喜悦)",
                     r"(达标|完成).{0,6}才(配|能).{0,4}(被神)?接纳"],
        "note": "把神的接纳建立在表现/行为之上，属律法主义。",
        "reframe": "提醒：神的接纳是恩典，先于我们的表现。操练是回应恩典，不是换取接纳。",
    },
    {
        "dimension": "prosperity_gospel", "severity": 4,
        "patterns": [r"(神|主).{0,6}一定.{0,6}(让你|使你).{0,6}(成功|富足|发财|顺利)",
                     r"只要.{0,8}就(一定|必定|肯定).{0,4}(成功|蒙福|得医治)",
                     r"完成.{0,6}操练.{0,8}(成功|发财|升职)"],
        "note": "把跟随神等同于必然的世俗成功，属成功神学。",
        "reframe": "提醒：顺服神不保证世俗成功；神应许的是祂的同在与塑造，结果交托给祂。",
    },
    {
        "dimension": "spiritual_shaming", "severity": 4,
        "patterns": [r"你(的)?属灵(状态)?(很|太)?(差|糟|失败)", r"你太(软弱|失败|糟糕)",
                     r"(真|很)(丢脸|可耻|羞耻)", r"你这样.{0,8}神(会)?(失望|生气|厌弃)"],
        "note": "用贬低/定罪/羞耻的语言对待用户。",
        "reframe": "改为温柔诚实：指出可成长之处，同时把人带回基督里被接纳的身份。",
    },
    {
        "dimension": "ai_replaces_pastor", "severity": 5,
        "patterns": [r"我是你的牧者", r"不需要.{0,4}(找)?(牧者|牧师|教会)",
                     r"AI.{0,8}陪你(解决|搞定).{0,4}所有", r"不用.{0,4}(找|去).{0,4}(牧师|教会)"],
        "note": "暗示 AI 可取代牧者/教会，越界。",
        "reframe": "明确：AI 只是辅助工具，不能取代牧者、教会和真实属灵同伴。",
    },
    {
        "dimension": "spiritual_scoring", "severity": 4,
        "patterns": [r"属灵(分数|评分|等级|得分)", r"打\d+分", r"\d+\s*分(（满分|/100)?",
                     r"排行榜", r"低于平均", r"属灵(排名|排行)"],
        "note": "用分数/等级/排行定义人的属灵价值。",
        "reframe": "改为趋势性语言（improving / stable / needs_attention）描述方向，不给人定分。",
    },
    {
        "dimension": "mysticism_manipulation", "severity": 3,
        "patterns": [r"只要你足够相信就(能|会).{0,6}(实现|得到)", r"宇宙(能量|会回应)",
                     r"心想事成"],
        "note": "以「足够相信」操控结果，偏离对神主权的信靠。",
        "reframe": "改为：信靠不是操控神，而是把无法掌控的交托给信实的神。",
    },
    {
        "dimension": "disrespects_church", "severity": 3,
        "patterns": [r"不需要(去)?教会", r"教会(没用|无所谓|可有可无)"],
        "note": "贬低教会群体在门徒塑造中的位置。",
        "reframe": "改为：成长以教会群体为土壤，鼓励真实的群体连接。",
    },
    {
        "dimension": "scripture_misuse", "severity": 3,
        "patterns": [r"这(节|句)经文(保证|确保)你.{0,6}(成功|得到|实现)",
                     r"背了?这.{0,4}经文.{0,6}就(能|会).{0,4}(脱离|得医治)"],
        "note": "把经文当成达成结果的保证/咒语。",
        "reframe": "改为：经文邀请我们认识神、信靠神，而非保证特定结果。",
    },
]

# 危机标记：内容若含这些信号，必须建议真实的人介入，否则记 crisis_without_human
_CRISIS_MARKERS = [
    r"不想活", r"想死", r"自杀", r"伤害自己", r"自残", r"活不下去",
    r"没有希望", r"结束(这)?一切", r"家暴", r"被(威胁|虐待)",
]
_HUMAN_REFERRAL = [
    r"牧者", r"牧师", r"专业(帮助|人士|咨询)", r"紧急(服务|热线|求助)",
    r"可信(的)?(人|家人|朋友)", r"身边.{0,4}(人|亲友)", r"心理(医生|咨询师)",
    r"110|120|急救",
]


def _find(patterns: List[str], text: str) -> bool:
    return any(re.search(p, text) for p in patterns)


def review(content: str, content_type: str = "generic") -> Dict[str, Any]:
    """规则审查。返回审查结果（不访问数据库）。"""
    text = (content or "").strip()
    issues: List[Dict[str, Any]] = []

    for rule in _RULES:
        if _find(rule["patterns"], text):
            issues.append({
                "dimension": rule["dimension"],
                "severity": rule["severity"],
                "note": rule["note"],
                "reframe": rule.get("reframe", ""),
            })

    # 危机安全检查：有危机信号但缺真实人介入建议
    if _find(_CRISIS_MARKERS, text) and not _find(_HUMAN_REFERRAL, text):
        issues.append({
            "dimension": "crisis_without_human",
            "severity": 5,
            "note": "内容含危机信号，但未建议联系真实可信的人/牧者/专业或紧急帮助。",
            "reframe": "必须加入：建议立即联系可信的属灵同伴、牧者、家人或当地紧急服务。",
        })

    max_sev = max((i["severity"] for i in issues), default=0)
    if max_sev >= 5:
        status = "blocked"
    elif issues:
        status = "needs_revision"
    else:
        status = "approved"

    corrected = None
    notes_parts: List[str] = []
    if issues:
        notes_parts.append("检测到 %d 处需要修订：" % len(issues))
        for i in issues:
            notes_parts.append(f"· [{i['dimension']}] {i['note']}")
        reframes = [i["reframe"] for i in issues if i.get("reframe")]
        if status == "needs_revision" and reframes:
            corrected = "建议按以下方向改写（保持温柔、诚实、福音中心）：\n" + "\n".join(reframes)
        elif status == "blocked":
            notes_parts.append("【阻断】此内容涉及危机安全，不能仅以属灵操练回应，必须先连接真实的人。")

    return {
        "review_status": status,
        "detected_issues": issues,
        "corrected_content": corrected,
        "reviewer_notes": "\n".join(notes_parts) if notes_parts else "未发现明显神学/安全问题。",
        "dimensions_checked": [d["code"] for d in DIMENSIONS],
    }


# ── 可选 AI 增强（默认关闭；与 gospel_engine 同构，失败回退规则）─────────────
SYSTEM_PROMPT = (
    "你是新教改革宗背景的神学安全审查员。审查给定文本是否福音中心，是否存在："
    "律法主义、成功神学、属灵羞辱、AI取代牧者、危机中只给经文不建议真人介入、"
    "经文误用、过度心理化替代福音、属灵评分定义人、神秘操控、不尊重教会。"
    "只输出 JSON：{\"review_status\":\"approved|needs_revision|blocked\","
    "\"detected_issues\":[{\"dimension\":\"\",\"severity\":1,\"note\":\"\"}],"
    "\"corrected_content\":\"\",\"reviewer_notes\":\"\"}"
)


def build_prompt(content: str) -> List[Dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": (content or "")[:6000]},
    ]


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    import json
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def analyze(content: str, content_type: str = "generic",
            settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    """规则审查为底；use_ai 且配置可用时，叠加 AI 复核（更严，取并集）。"""
    base = review(content, content_type)
    if not use_ai:
        return base

    ai_raw = None
    try:  # 复用项目既有的 LLM 调用约定；任何失败都回退规则结果
        from llm_client import chat_json  # type: ignore
        ai_raw = chat_json(build_prompt(content), settings=settings)
    except Exception:
        try:
            from backend.llm_client import chat_json  # type: ignore
            ai_raw = chat_json(build_prompt(content), settings=settings)
        except Exception:
            ai_raw = None

    parsed = _extract_json(ai_raw) if isinstance(ai_raw, str) else (ai_raw or None)
    if not isinstance(parsed, dict):
        return base

    # 取并集 + 取最严状态
    merged_issues = list(base["detected_issues"]) + list(parsed.get("detected_issues") or [])
    order = {"approved": 0, "needs_revision": 1, "blocked": 2}
    status = max([base["review_status"], parsed.get("review_status", "approved")],
                 key=lambda s: order.get(s, 0))
    return {
        "review_status": status,
        "detected_issues": merged_issues,
        "corrected_content": parsed.get("corrected_content") or base["corrected_content"],
        "reviewer_notes": (base["reviewer_notes"] + "\n[AI] " + (parsed.get("reviewer_notes") or "")).strip(),
        "dimensions_checked": base["dimensions_checked"],
    }


def meta() -> Dict[str, Any]:
    return {"dimensions": DIMENSIONS, "prompt_version": PROMPT_VERSION,
            "statuses": ["approved", "needs_revision", "blocked"]}
