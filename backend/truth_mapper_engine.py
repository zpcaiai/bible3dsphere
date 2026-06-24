"""
truth_mapper_engine.py — Biblical Truth Mapper Agent / 圣经真理映射 Agent

把扭曲信念 / 偶像模式映射到：圣经真理 + 福音重构 + 经文 + 教义标签 + 圣经人物 + 操练方向。
不是简单推荐经文，而是完成「谎言 → 圣经真理 → 福音重构 → 操练方向」的映射。

复用策略
========
- 内置确定性 TRUTH_MAPS（覆盖规格 6 大映射 + 属灵表现 + 通用兜底）。
- 可选增益：若 gospel_engine 可用，借其 IDOLS 的 unbelief/gospel 文案补强。
- 圣经人物：本引擎给出人物中文名；router 可按名查询 biblical_characters 表附上 lesson/经文/简介。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

try:  # 可选 LLM 增强（仅润色 prose；经文/教义/人物恒为确定性）
    from backend import worldview_llm as _llm
except Exception:  # pragma: no cover
    try:
        import worldview_llm as _llm  # type: ignore
    except Exception:
        _llm = None  # type: ignore

# 每条映射：按 idol_category 优先匹配，其次 domain，最后 fallback。
TRUTH_MAPS: List[Dict[str, Any]] = [
    {
        "idol_category": "success", "domains": ["self", "work"],
        "lie_keywords": ["成就", "成功", "价值", "失败", "证明自己", "赢"],
        "biblical_truth": "人按神的形象被造，并在基督里因恩典被完全接纳——价值不靠表现赚取。",
        "gospel_reframe": "你不是「先成功、才有价值」，而是「已被爱、所以自由地工作」。十字架已经一次性证明了你的价值。",
        "scripture_refs": ["创1:26-27", "弗1:4-7", "加2:20"],
        "doctrine_tags": ["imago_dei", "justification", "identity_in_christ"],
        "bible_persons": ["保罗", "彼得", "摩西"],
        "pastoral_cautions": ["不要把「放下成就」误解为「不再追求卓越」——是动机从称义转向感恩。"],
        "practice_suggestions": ["做一件隐藏的、无人看见的忠心善事", "把一项成就当作礼物献上，而非身份"],
    },
    {
        "idol_category": "money", "domains": ["money"],
        "lie_keywords": ["钱", "安全感", "财务", "资产", "贫穷", "供应"],
        "biblical_truth": "神是供应者，财富是受托管理的资源，而非安全感的根基。",
        "gospel_reframe": "安全感不在余额，而在那位「连自己的儿子都赐给我们」的天父——祂岂不也把万物白白赐给我们？",
        "scripture_refs": ["太6:19-34", "提前6:6-10", "腓4:11-13"],
        "doctrine_tags": ["providence", "stewardship", "contentment"],
        "bible_persons": ["亚伯拉罕", "约瑟", "保罗"],
        "pastoral_cautions": ["谨慎区分「智慧的预备」与「以掌控代替信靠」——节俭本身不是偶像。"],
        "practice_suggestions": ["本周做一次不计代价的奉献或施予", "为三件已有的供应具体感恩"],
    },
    {
        "idol_category": "control", "domains": ["self", "suffering"],
        "lie_keywords": ["掌控", "控制", "确定", "计划", "不确定"],
        "biblical_truth": "人是有限的，神掌权；信心是在有限中向那位掌权者交托。",
        "gospel_reframe": "你不需要做掌权的那一位——那个位置已经有人坐了，而且祂爱你。放手不是失控，是回到受造者的安息。",
        "scripture_refs": ["箴3:5-6", "太6:25-34", "罗8:28"],
        "doctrine_tags": ["sovereignty", "trust", "creatureliness"],
        "bible_persons": ["约瑟", "但以理", "大卫"],
        "pastoral_cautions": ["对经历过创伤的人，掌控常是自保机制——以温柔陪伴代替催促放手。"],
        "practice_suggestions": ["今天留一件事「不去安排」，交在神手中", "做一次安息式停顿，承认我不是掌权者"],
    },
    {
        "idol_category": "technology", "domains": ["technology"],
        "lie_keywords": ["技术", "ai", "效率", "淘汰", "未来", "进步"],
        "biblical_truth": "技术是治理受造界的工具，不是救主；人的罪与有限不能靠工具消除。",
        "gospel_reframe": "技术能放大能力，却不能赦免罪、不能赐永生。真盼望不是技术乌托邦，而是神国的成全。被时代淘汰，也淘汰不掉神对你的爱。",
        "scripture_refs": ["创11:1-9", "诗8:3-6", "西1:15-20"],
        "doctrine_tags": ["创造使命", "human_finitude", "providence"],
        "bible_persons": ["但以理", "所罗门", "约瑟"],
        "pastoral_cautions": ["不要把 AI / 技术简单等同于启示录的兽——避免阴谋论，承认共同恩典。"],
        "practice_suggestions": ["设定不学技术、不看收益的安息窗口", "写下一个用技术服事人的具体方式"],
    },
    {
        "idol_category": "relationship", "domains": ["relationship"],
        "lie_keywords": ["被爱", "认可", "关系", "孤独", "某个人", "离不开"],
        "biblical_truth": "人需要爱，但终极身份来自神的接纳，而非某段关系或某个人的认可。",
        "gospel_reframe": "你被一份永不离弃的爱所定义。当神是你的终极满足，你反而能更自由、更健康地爱人，而不是抓取。",
        "scripture_refs": ["约4:13-14", "路15:11-24", "弗1:4-6"],
        "doctrine_tags": ["adoption", "identity_in_christ", "satisfaction_in_god"],
        "bible_persons": ["撒玛利亚妇人", "彼得", "大卫"],
        "pastoral_cautions": ["不要把「健康的爱与需要」病理化——问题是把救主的位置给了人。"],
        "practice_suggestions": ["独处一段时间，练习在神面前一个人也完整", "为这段关系祷告：我爱他，但不靠他活着"],
    },
    {
        "idol_category": "victimhood", "domains": ["suffering"],
        "lie_keywords": ["苦难", "无意义", "离弃", "受害", "没人懂", "过去"],
        "biblical_truth": "苦难是真实的痛苦，但它不能取消神的同在、护理与终末的盼望。",
        "gospel_reframe": "圣经不要求你假装不痛——它给你哀歌的语言。十字架上的神懂你的痛，并已为你预备了终末的擦干眼泪。你的过去不是你的全部身份。",
        "scripture_refs": ["诗13", "罗8:18-39", "林后4:16-18", "彼前1:3-9"],
        "doctrine_tags": ["lament", "providence", "hope", "new_identity"],
        "bible_persons": ["约伯", "拿俄米", "约瑟", "保罗"],
        "pastoral_cautions": ["绝不可冷冰冰地解释苦难；先陪伴与哀哭，再谈盼望。高危时优先安全，转 suffering_theology。"],
        "practice_suggestions": ["用哀歌祷告向神诚实说出痛苦，同时抓住一个盼望应许", "做一件不属于受害者剧本的小选择"],
    },
    {
        "idol_category": "spiritual_performance", "domains": ["god", "salvation"],
        "lie_keywords": ["表现", "配得", "灵修", "不喜悦", "称义", "够好"],
        "biblical_truth": "人是因信称义、靠恩典被接纳，不是靠属灵表现赚取神的喜悦。",
        "gospel_reframe": "你在基督里的地位不随你今天灵修好坏浮动。神接纳你，是因为基督的义，不是你的表现。你可以停止表演，开始相交。",
        "scripture_refs": ["弗2:8-9", "加2:16", "罗8:1"],
        "doctrine_tags": ["justification", "grace", "adoption"],
        "bible_persons": ["彼得", "保罗", "撒该"],
        "pastoral_cautions": ["对羞耻倾向者，强调恩典而非更多操练；不要再加重「该做到」的负担。"],
        "practice_suggestions": ["做一个只在神与你之间、不告诉任何人的属灵操练", "向神诚实承认一处一直在「装」的地方，领受赦免"],
    },
]

_FALLBACK = {
    "biblical_truth": "在基督里，你的身份、价值与安全感都有了不可动摇的根基。",
    "gospel_reframe": "无论你正把什么放在神的位置上，福音邀请你把它交还，重新让神作神。",
    "scripture_refs": ["太6:33", "罗8:28", "腓4:6-7"],
    "doctrine_tags": ["gospel", "identity_in_christ"],
    "bible_persons": ["大卫", "保罗"],
    "pastoral_cautions": ["这是邀请，不是定罪。"],
    "practice_suggestions": ["把一件最放不下的事交托祷告", "做一个小的顺服行动，打破对结果的绝对依赖"],
}


def _score_match(entry: Dict[str, Any], domain: Optional[str],
                 idol_category: Optional[str], lie: str) -> float:
    score = 0.0
    if idol_category and entry.get("idol_category") == idol_category:
        score += 0.6
    if domain and domain in entry.get("domains", []):
        score += 0.3
    low = (lie or "").lower()
    if low:
        hits = sum(1 for kw in entry.get("lie_keywords", []) if kw.lower() in low)
        score += min(0.3, 0.1 * hits)
    return score


def map_one(*, domain: Optional[str] = None, idol_category: Optional[str] = None,
            lie: str = "", use_ai: bool = False) -> Dict[str, Any]:
    """对单条扭曲信念做映射，返回规格 mapping 结构。"""
    best, best_score = None, 0.0
    for e in TRUTH_MAPS:
        sc = _score_match(e, domain, idol_category, lie)
        if sc > best_score:
            best, best_score = e, sc
    src = best if best and best_score >= 0.3 else _FALLBACK
    confidence = round(min(0.95, 0.5 + best_score), 2) if best and best_score >= 0.3 else 0.4
    out = {
        "lieStatement": lie or "（未提供具体陈述）",
        "biblicalTruth": src["biblical_truth"],
        "gospelReframe": src["gospel_reframe"],
        "scriptureRefs": list(src["scripture_refs"]),
        "doctrineTags": list(src["doctrine_tags"]),
        "recommendedBiblePersons": list(src["bible_persons"]),
        "pastoralCautions": list(src["pastoral_cautions"]),
        "practiceSuggestions": list(src["practice_suggestions"]),
        "confidence": confidence,
    }
    return _ai_enhance_one(out, domain, idol_category, lie, use_ai)


_DIAG_STRUCTURED_SYSTEM = (
    "你是属灵诊断 / 真理映射 Agent。针对给定的扭曲信念，输出 findings：每条含 category（所属领域）、"
    "finding_type、title、description（福音重构，温暖、以基督为中心）、gospel_truth（圣经真理）、"
    "scripture_anchors（经文出处）、severity(1-5)、confidence、possible_root、"
    "recommended_practice_types、requires_pastor_attention。primary_theme 概括主题，summary 总结。"
    "findings 的顺序须与输入信念一一对应。"
)


def _merge_refs(canonical, ai_refs):
    """canonical 优先，去重并入 AI 经文（保住权威经文，结构化补充）。"""
    out = list(canonical or [])
    for r in (ai_refs or []):
        r = str(r).strip()
        if r and r not in out:
            out.append(r)
    return out


def _apply_finding(m: Dict[str, Any], f: Dict[str, Any]) -> Dict[str, Any]:
    """把一条 DiagnosisFinding 合并进一个确定性 mapping。经文 canonical-first；人物/教义不变。"""
    out = dict(m)
    if f.get("gospel_truth"):
        out["biblicalTruth"] = str(f["gospel_truth"]).strip()
    if f.get("description"):
        out["gospelReframe"] = str(f["description"]).strip()
    out["scriptureRefs"] = _merge_refs(out.get("scriptureRefs"), f.get("scripture_anchors"))
    practices = list(out.get("practiceSuggestions", []))
    for p in (f.get("recommended_practice_types") or []):
        p = str(p).strip()
        if p and p not in practices:
            practices.append(p)
    out["practiceSuggestions"] = practices
    if f.get("severity") is not None:
        out["severity"] = f["severity"]
    if f.get("possible_root"):
        out["possibleRoot"] = f["possible_root"]
    out["requiresPastorAttention"] = bool(f.get("requires_pastor_attention"))
    if f.get("confidence") is not None:
        out["confidence"] = float(f["confidence"])
    out["source"] = "ai"
    return out


def _ai_enhance_one(out: Dict[str, Any], domain, idol_category, lie: str, use_ai: bool) -> Dict[str, Any]:
    """单条：结构化 AI 优先（DiagnosisAgentOutput.findings[0]）→ prose 润色兜底。"""
    if not use_ai or _llm is None:
        return out
    if hasattr(_llm, "generate_structured"):
        try:
            payload = {"belief": lie, "domain": domain, "idol_category": idol_category}
            ai = _llm.generate_structured(_DIAG_STRUCTURED_SYSTEM, payload, "DiagnosisAgentOutput")
        except Exception:
            ai = None
        if ai and ai.get("findings"):
            return _apply_finding(out, ai["findings"][0])
    return _ai_refine_map(out, use_ai)


def _ai_refine_map(out: Dict[str, Any], use_ai: bool) -> Dict[str, Any]:
    """可选：润色 biblicalTruth / gospelReframe 文字；经文/人物/教义不变。"""
    if not use_ai or _llm is None:
        return out
    system = ("你是福音辅导助手。基于给定材料，用温暖、以基督为中心的中文改写 biblicalTruth"
              "（1-2句）与 gospelReframe（2-4句）。"
              "**严禁**新增、改写或引用任何经文出处——经文由系统另行提供。"
              "只输出 JSON：{\"biblicalTruth\":\"...\",\"gospelReframe\":\"...\"}")
    user = (f"针对谎言：{out['lieStatement']}\n"
            f"已选定经文（仅供你理解语境，勿改动/勿在输出中引用具体经节）：{out['scriptureRefs']}\n"
            f"当前 biblicalTruth：{out['biblicalTruth']}\n当前 gospelReframe：{out['gospelReframe']}")
    try:
        ai = _llm.enhance(system, user, temperature=0.5, max_tokens=400)
        return _llm.merge_fields(out, ai, ["biblicalTruth", "gospelReframe"])
    except Exception:
        return out


def map_beliefs(beliefs: List[Dict[str, Any]], use_ai: bool = False) -> Dict[str, Any]:
    """
    输入诊断器产出的 beliefs（含 domain / beliefStatement / idolHint），
    输出映射集合 + 摘要 + 下一步建议。use_ai 仅对前 3 条做 prose 润色（控延迟）。
    """
    # 1) 确定性映射（canonical 经文/人物/教义）
    mappings: List[Dict[str, Any]] = []
    for b in beliefs or []:
        mappings.append(map_one(
            domain=b.get("domain"),
            idol_category=b.get("idolHint") or b.get("idol_category"),
            lie=b.get("beliefStatement") or b.get("lie") or "",
            use_ai=False,
        ))
    result = {
        "mappings": mappings,
        "summary": _summary(mappings),
        "recommendedNextAgents": ["narrative_rewriter", "formation_practice"] if mappings else [],
    }
    if not use_ai or _llm is None or not mappings:
        return result

    # 2) 结构化 AI：一次 generate_json 覆盖全部信念，按序分配到 mappings
    ai = None
    if hasattr(_llm, "generate_structured"):
        try:
            payload = {"beliefs": [
                {"belief": b.get("beliefStatement") or b.get("lie") or "",
                 "domain": b.get("domain"),
                 "idol_category": b.get("idolHint") or b.get("idol_category")}
                for b in beliefs
            ]}
            ai = _llm.generate_structured(_DIAG_STRUCTURED_SYSTEM, payload, "DiagnosisAgentOutput")
        except Exception:
            ai = None
    if ai:
        findings = ai.get("findings") or []
        for i, m in enumerate(result["mappings"]):
            if i < len(findings):
                result["mappings"][i] = _apply_finding(m, findings[i])
        if ai.get("summary"):
            result["summary"] = str(ai["summary"]).strip()
        if ai.get("primary_theme"):
            result["primaryTheme"] = str(ai["primary_theme"]).strip()
        if ai.get("risk_level"):
            result["riskLevel"] = ai["risk_level"]
        result["source"] = "ai"
        return result

    # 3) 无结构化（未配置真实 provider）→ prose 润色兜底（<=3 条，控延迟）
    for i in range(min(3, len(result["mappings"]))):
        result["mappings"][i] = _ai_refine_map(result["mappings"][i], True)
    return result


def _summary(mappings: List[Dict[str, Any]]) -> str:
    if not mappings:
        return "暂无可映射的扭曲信念。愿真理继续更新你看神、看自己、看世界的眼光。"
    refs = []
    for m in mappings[:3]:
        refs.extend(m["scriptureRefs"][:1])
    return (f"已为 {len(mappings)} 条信念映射了圣经真理与福音重构。"
            f"可默想：{('、'.join(dict.fromkeys(refs)))}。"
            f"下一步：把它写进新的生命叙事，并落到具体操练。")


def meta() -> Dict[str, Any]:
    return {
        "mapCount": len(TRUTH_MAPS),
        "covers": [{"idol_category": e["idol_category"], "domains": e["domains"]} for e in TRUTH_MAPS],
    }
