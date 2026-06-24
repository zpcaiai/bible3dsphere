"""
worldview_diagnoser_engine.py — Worldview Diagnoser Agent / 世界观诊断 Agent

目标
====
不只看用户「口头上信什么」，而是根据其语言、恐惧、价值排序、决策方式、焦虑来源，
推断其**真实运作**的世界观。覆盖 12 个领域，抽取底层信念，判断是否与圣经世界观一致，
按 0–100 打分，并产出一份 WorldviewProfile。

设计原则
========
- 纯函数 / 无状态：DB 落库由 router 负责。
- 确定性优先：用中文 + 英文关键词/短语模式做可解释的检测；LLM 仅作可选增益（hook）。
- 非定罪：信念以「检测到 / 可能 / 值得省察」呈现，不审判。
- 安全：本引擎假设上游 worldview_orchestrator.crisis_guard 已先行；若文本含明显高危词，
  也会把 suffering_theology 放进 recommendedNextAgents。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

try:  # 可选 LLM 增强层（无则纯确定性）
    from backend import worldview_llm as _llm
except Exception:  # pragma: no cover
    try:
        import worldview_llm as _llm  # type: ignore
    except Exception:
        _llm = None  # type: ignore

# ---------------------------------------------------------------------------
# 1. 12 个世界观领域
# ---------------------------------------------------------------------------
DOMAINS: List[Dict[str, Any]] = [
    {"domain": "god", "name": "神观", "keywords": ["神", "上帝", "耶和华", "主", "信仰", "祷告", "god", "lord", "faith"]},
    {"domain": "self", "name": "自我观", "keywords": ["我是谁", "我的价值", "自我", "身份", "没价值", "失败者", "配不上", "identity", "worth", "worthless"]},
    {"domain": "sin", "name": "罪观", "keywords": ["罪", "犯罪", "悔改", "羞耻", "内疚", "sin", "guilt", "shame", "repent"]},
    {"domain": "salvation", "name": "救恩观", "keywords": ["救恩", "得救", "称义", "恩典", "赦免", "salvation", "grace", "saved"]},
    {"domain": "suffering", "name": "苦难观", "keywords": ["痛苦", "苦难", "失去", "绝望", "灰心", "为什么是我", "suffering", "grief", "despair", "pain"]},
    {"domain": "money", "name": "金钱观", "keywords": ["钱", "赚", "财务", "收入", "资产", "财富", "安全感", "money", "rich", "wealth", "income"]},
    {"domain": "work", "name": "工作观", "keywords": ["工作", "事业", "创业", "职业", "成就", "升职", "内卷", "career", "job", "success", "startup"]},
    {"domain": "relationship", "name": "关系观", "keywords": ["关系", "恋爱", "婚姻", "孤独", "被爱", "认可", "朋友", "relationship", "lonely", "love", "approval"]},
    {"domain": "technology", "name": "技术观", "keywords": ["ai", "人工智能", "技术", "科技", "自动化", "淘汰", "取代", "失业", "technology", "robot", "automation"]},
    {"domain": "history", "name": "历史观", "keywords": ["历史", "时代", "文化", "潮流", "进步", "history", "culture", "progress"]},
    {"domain": "eternity", "name": "永恒观", "keywords": ["永恒", "死亡", "天堂", "地狱", "终末", "意义", "eternity", "death", "heaven", "meaning"]},
    {"domain": "mission", "name": "使命观", "keywords": ["使命", "呼召", "服事", "福音", "见证", "mission", "calling", "serve", "purpose"]},
]
DOMAIN_INDEX = {d["domain"]: d for d in DOMAINS}
DOMAIN_KEYS = [d["domain"] for d in DOMAINS]

# 偶像隐含的领域：某些偶像本质上横跨多个领域（如成就偶像同时触及自我与工作）。
IDOL_TO_DOMAINS: Dict[str, List[str]] = {
    "success": ["self", "work"],
    "money": ["money"],
    "security": ["money"],
    "technology": ["technology"],
    "control": ["self"],
    "relationship": ["relationship"],
    "victimhood": ["suffering"],
    "spiritual_performance": ["god", "salvation"],
}


# ---------------------------------------------------------------------------
# 2. 扭曲信念模式：谎言 → 状态/果子/偶像线索
# ---------------------------------------------------------------------------
# 每条：所有 any_of 命中即触发；severity 1–10；idol_hint 给下游 idol_detector。
DISTORTION_PATTERNS: List[Dict[str, Any]] = [
    {
        "domain": "self", "any_of": [["失败", "没价值"], ["失败", "完了"], ["失败者"], ["证明自己", "价值"], ["没用", "活着"], ["人生", "失败"], ["不能", "失败"]],
        "lie": "我的价值取决于我的表现与成就。",
        "severity": 8, "idol_hint": "success",
        "emotional_fruit": ["焦虑", "恐惧", "羞耻"],
        "behavioral_fruit": ["过度内卷", "无法安息", "害怕休息"],
    },
    {
        "domain": "money", "any_of": [["钱", "安全感"], ["没钱", "完了"], ["赚", "才安心"], ["财务自由", "安心"], ["资产", "底气"], ["赚很多钱"], ["赚", "钱", "失败"]],
        "lie": "金钱是我的安全感来源。",
        "severity": 7, "idol_hint": "money",
        "emotional_fruit": ["焦虑", "不安", "贪婪"],
        "behavioral_fruit": ["过度积累", "不敢奉献", "用收入定义自己"],
    },
    {
        "domain": "technology", "any_of": [["ai", "淘汰"], ["ai", "取代"], ["技术", "失业"], ["跟不上", "淘汰"], ["ai", "失业"]],
        "lie": "技术决定我的未来与价值（技术救世/技术恐惧）。",
        "severity": 6, "idol_hint": "technology",
        "emotional_fruit": ["焦虑", "恐惧", "被淘汰感"],
        "behavioral_fruit": ["强迫式学习", "无法停下", "用生产力定义价值"],
    },
    {
        "domain": "work", "any_of": [["超过别人"], ["不能输"], ["必须赢"], ["比别人强"], ["证明", "事业"]],
        "lie": "工作成就定义我是谁；我必须赢过别人。",
        "severity": 7, "idol_hint": "success",
        "emotional_fruit": ["比较", "嫉妒", "焦虑"],
        "behavioral_fruit": ["竞争性内卷", "工作成瘾", "无法庆祝他人"],
    },
    {
        "domain": "self", "any_of": [["必须掌控"], ["不能接受", "不确定"], ["控制", "崩溃"], ["计划", "崩溃"]],
        "lie": "我必须掌控一切才安全。",
        "severity": 6, "idol_hint": "control",
        "emotional_fruit": ["焦虑", "紧张"],
        "behavioral_fruit": ["过度计划", "无法交托", "对变化恐慌"],
    },
    {
        "domain": "relationship", "any_of": [["没有", "崩溃"], ["不爱我", "价值"], ["被认可", "价值"], ["孤独", "活不下去"]],
        "lie": "被人爱和认可决定我的价值。",
        "severity": 6, "idol_hint": "relationship",
        "emotional_fruit": ["被弃感", "焦虑", "讨好"],
        "behavioral_fruit": ["讨好他人", "无法设界限", "依附某个人"],
    },
    {
        "domain": "suffering", "any_of": [["神", "离弃"], ["神", "不要我"], ["没有意义"], ["人生", "无意义"], ["为什么是我"]],
        "lie": "苦难说明神离弃了我 / 人生没有意义。",
        "severity": 7, "idol_hint": "victimhood",
        "emotional_fruit": ["绝望", "被弃感", "愤怒"],
        "behavioral_fruit": ["退缩", "停止祷告", "自我封闭"],
    },
    {
        "domain": "god", "any_of": [["灵修", "不喜悦"], ["表现", "配得"], ["跌倒", "不要我"], ["做得好", "神才"]],
        "lie": "我必须表现属灵，神才会接纳我。",
        "severity": 6, "idol_hint": "spiritual_performance",
        "emotional_fruit": ["羞耻", "恐惧", "疲惫"],
        "behavioral_fruit": ["属灵表演", "隐藏挣扎", "用操练换取接纳"],
    },
]

# 与圣经世界观一致的标记（出现则提升该领域分数）
ALIGNED_MARKERS: Dict[str, List[List[str]]] = {
    "god": [["神是信实"], ["交托", "神"], ["神掌权"], ["信靠神"]],
    "self": [["在基督里", "身份"], ["神看我", "宝贵"], ["不靠成就"]],
    "money": [["奉献"], ["知足"], ["神供应"], ["管家"]],
    "work": [["忠心"], ["呼召", "工作"], ["荣耀神", "工作"]],
    "suffering": [["神同在"], ["盼望"], ["哀歌"], ["神没有离开"]],
    "relationship": [["先爱神"], ["在神里完整"], ["健康界限"]],
    "salvation": [["因信称义"], ["恩典", "得救"], ["不靠行为"]],
    "eternity": [["积财在天"], ["永恒", "盼望"], ["神国"]],
    "mission": [["服事人"], ["传福音"], ["国度"]],
}

# 高危词（兜底；正常应由 orchestrator.crisis_guard 先拦截）
_CRISIS_HINTS = ["不想活", "想死", "结束生命", "自杀", "伤害自己", "活不下去",
                 "kill myself", "want to die", "end my life", "hurt myself"]


# ---------------------------------------------------------------------------
# 3. 工具
# ---------------------------------------------------------------------------
def _norm(text: str) -> str:
    return (text or "").lower()


def _hit_any_of(any_of: List[List[str]], text: str) -> Optional[List[str]]:
    """any_of 中任一组（组内全部命中）即返回该组关键词。"""
    for group in any_of:
        if all(kw.lower() in text for kw in group):
            return group
    return None


def _detect_domains(text: str) -> List[str]:
    found: List[str] = []
    for d in DOMAINS:
        if any(kw.lower() in text for kw in d["keywords"]):
            found.append(d["domain"])
    return found


# ---------------------------------------------------------------------------
# 4. 主入口
# ---------------------------------------------------------------------------
def diagnose(
    *,
    user_id: Optional[str] = None,
    text: str = "",
    source_type: str = "journal",
    locale: Optional[str] = None,
    signals: Optional[Dict[str, Any]] = None,
    use_ai: bool = False,
) -> Dict[str, Any]:
    """
    诊断一段输入的底层世界观。返回结构见模块顶部 README / 路由层契约。
    """
    low = _norm(text)

    extracted: List[Dict[str, Any]] = []
    distorted_domains: Dict[str, int] = {}     # domain -> max severity
    idol_hints: List[str] = []

    for pat in DISTORTION_PATTERNS:
        grp = _hit_any_of(pat["any_of"], low)
        if not grp:
            continue
        dom = pat["domain"]
        sev = int(pat["severity"])
        distorted_domains[dom] = max(distorted_domains.get(dom, 0), sev)
        if pat["idol_hint"] not in idol_hints:
            idol_hints.append(pat["idol_hint"])
        extracted.append({
            "domain": dom,
            "beliefStatement": pat["lie"],
            "status": "distorted",
            "confidence": round(min(0.95, 0.55 + 0.04 * sev), 2),
            "evidence": "、".join(grp),
            "emotionalFruit": list(pat["emotional_fruit"]),
            "behavioralFruit": list(pat["behavioral_fruit"]),
            "idolHint": pat["idol_hint"],
        })

    detected = _detect_domains(low)
    # 确保所有有信念的领域也在 detected 中
    for dom in distorted_domains:
        if dom not in detected:
            detected.append(dom)
    # 偶像隐含的领域也并入（如 success → self/work）
    for h in idol_hints:
        for dom in IDOL_TO_DOMAINS.get(h, []):
            if dom not in detected:
                detected.append(dom)

    # 维度打分
    dimension_scores: List[Dict[str, Any]] = []
    for dom in detected:
        score, conf, expl = _score_domain(dom, low, distorted_domains.get(dom))
        dimension_scores.append({
            "domain": dom, "name": DOMAIN_INDEX[dom]["name"],
            "score": score, "confidence": conf, "explanation": expl,
            "evidence": [b["evidence"] for b in extracted if b["domain"] == dom],
        })

    # 画像汇总
    scored = [d for d in dimension_scores if d["score"] is not None]
    overall = round(sum(d["score"] for d in scored) / len(scored), 1) if scored else None
    ranked = sorted(scored, key=lambda d: d["score"])
    weakest = [d["domain"] for d in ranked[:3]]
    strongest = [d["domain"] for d in reversed(ranked[-3:])] if scored else []
    growth_focus = weakest[0] if weakest else None

    next_agents = _recommend_next_agents(low, idol_hints, distorted_domains)

    summary = _build_summary(detected, extracted, overall)

    result = {
        "userId": user_id,
        "detectedDomains": detected,
        "extractedBeliefs": extracted,
        "dimensionScores": dimension_scores,
        "overallScore": overall,
        "confidence": round(min(0.95, 0.4 + 0.1 * len(extracted)), 2) if extracted else 0.4,
        "profileSummary": summary,
        "dominantPatterns": idol_hints,
        "strongestDomains": strongest,
        "weakestDomains": weakest,
        "currentGrowthFocus": growth_focus,
        "recommendedNextAgents": next_agents,
    }
    return _ai_refine(result, text, use_ai)


_WV_STRUCTURED_SYSTEM = (
    "你是圣经世界观诊断 Agent。基于用户原文，识别其真实运作的底层世界观信念（不只看口头表述）。"
    "每条 finding 的 dimension_code 必须取自：god/self/sin/salvation/suffering/money/work/"
    "relationship/technology/history/eternity/mission。给出 expressed_belief、"
    "belief_type(explicit/implicit)、distortion_type（无则留空）、biblical_counter_truth、"
    "scripture_anchors（经文出处）、evidence（原文依据）、confidence、recommended_practices。"
    "summary 用温柔、非定罪、以恩典为中心的中文；dominant_distortions/renewal_focus 给关键扭曲与更新焦点。"
)


def _ai_refine(result: Dict[str, Any], text: str, use_ai: bool) -> Dict[str, Any]:
    """结构化 AI 优先（WorldviewAgentOutput）→ prose 润色兜底 → 确定性。
    评分、recommendedNextAgents（路由）恒为确定性；AI 仅补充信念/扭曲/summary。"""
    if not use_ai or _llm is None:
        return result
    # 1) 结构化输出（schema 校验）
    ai = None
    if hasattr(_llm, "generate_structured"):
        try:
            payload = {
                "text": text[:2000],
                "deterministic_domains": result.get("detectedDomains", []),
                "deterministic_beliefs": [b.get("beliefStatement") for b in result.get("extractedBeliefs", [])],
                "valid_dimension_codes": DOMAIN_KEYS,
            }
            ai = _llm.generate_structured(_WV_STRUCTURED_SYSTEM, payload, "WorldviewAgentOutput")
        except Exception:
            ai = None
    if ai:
        return _merge_worldview(result, ai)
    # 2) prose 润色兜底（仅改 profileSummary）
    return _polish_summary(result, text)


def _polish_summary(result: Dict[str, Any], text: str) -> Dict[str, Any]:
    system = ("你是圣经世界观辅导助手。基于给定的确定性诊断，用温柔、非定罪、以恩典为中心的"
              "中文，改写一段更贴近此人处境的 profileSummary（120-200字）。"
              "不要新增或更改任何经文引用、评分或领域判断。只输出 JSON：{\"profileSummary\":\"...\"}")
    user = (f"用户原文：{text[:1200]}\n\n"
            f"确定性识别的领域：{result.get('detectedDomains')}\n"
            f"识别到的信念：{[b.get('beliefStatement') for b in result.get('extractedBeliefs', [])]}\n"
            f"当前 profileSummary：{result.get('profileSummary')}")
    try:
        ai = _llm.enhance(system, user, temperature=0.5, max_tokens=500)
        return _llm.merge_fields(result, ai, ["profileSummary"])
    except Exception:
        return result


def _merge_worldview(result: Dict[str, Any], ai: Dict[str, Any]) -> Dict[str, Any]:
    """把 WorldviewAgentOutput 映射进确定性输出契约（保留评分/路由确定性）。"""
    out = dict(result)
    if ai.get("summary"):
        out["profileSummary"] = str(ai["summary"]).strip()
    dd = [str(x).strip() for x in (ai.get("dominant_distortions") or []) if str(x).strip()]
    if dd:
        merged = list(out.get("dominantPatterns", []))
        for x in dd:
            if x not in merged:
                merged.append(x)
        out["dominantPatterns"] = merged
    rf = [str(x).strip() for x in (ai.get("renewal_focus") or []) if str(x).strip()]
    if rf:
        out["renewalFocus"] = rf

    beliefs = list(out.get("extractedBeliefs", []))
    detected = list(out.get("detectedDomains", []))
    seen = {(b.get("domain"), b.get("beliefStatement")) for b in beliefs}
    for f in ai.get("findings", []) or []:
        stmt = (f.get("expressed_belief") or "").strip()
        if not stmt:
            continue
        dom = f.get("dimension_code") or "unknown"
        if (dom, stmt) in seen:
            continue
        seen.add((dom, stmt))
        beliefs.append({
            "domain": dom,
            "beliefStatement": stmt,
            "status": "distorted" if f.get("distortion_type") else "detected",
            "confidence": float(f.get("confidence", 0.6) or 0.6),
            "evidence": (f.get("evidence") or "")[:500],
            "emotionalFruit": [],
            "behavioralFruit": [],
            "idolHint": None,
            "biblicalCounterTruth": f.get("biblical_counter_truth"),
            "scriptureAnchors": list(f.get("scripture_anchors") or []),
            "recommendedPractices": list(f.get("recommended_practices") or []),
            "source": "ai",
        })
        if dom in DOMAIN_INDEX and dom not in detected:
            detected.append(dom)
    out["extractedBeliefs"] = beliefs
    out["detectedDomains"] = detected
    out["source"] = "ai"
    return out


def _score_domain(domain: str, low: str, distortion_sev: Optional[int]) -> Tuple[float, float, str]:
    """0–100：60 基线；扭曲下拉，圣经一致标记上提。"""
    score = 60.0
    notes: List[str] = []
    if distortion_sev:
        score = max(15.0, 60.0 - distortion_sev * 4.0)
        notes.append("检测到由恐惧/偶像驱动的扭曲信念")
    aligned = ALIGNED_MARKERS.get(domain, [])
    if aligned and _hit_any_of(aligned, low):
        score = min(95.0, score + 22.0)
        notes.append("出现与圣经世界观一致的标记")
    conf = 0.45 if not distortion_sev else round(min(0.9, 0.55 + 0.04 * distortion_sev), 2)
    expl = "；".join(notes) or "有基本认知，但证据有限，建议进一步省察"
    return round(score, 1), conf, expl


def _recommend_next_agents(low: str, idol_hints: List[str],
                           distorted_domains: Dict[str, int]) -> List[str]:
    out: List[str] = []
    if idol_hints:
        out.append("idol_detector")
        out.append("biblical_truth_mapper")
        out.append("narrative_rewriter")
    if any(d in distorted_domains for d in ("money", "work", "technology")):
        out.append("vocation_worldview")
    if "technology" in distorted_domains or "history" in distorted_domains:
        out.append("cultural_discernment")
    if "suffering" in distorted_domains or any(h in low for h in _CRISIS_HINTS):
        out.append("suffering_theology")
    # 去重保序
    seen, dedup = set(), []
    for a in out:
        if a not in seen:
            seen.add(a)
            dedup.append(a)
    return dedup


def _build_summary(detected: List[str], extracted: List[Dict[str, Any]],
                   overall: Optional[float]) -> str:
    if not detected:
        return "这次输入没有显出明显的世界观议题。愿你继续在神面前诚实地省察自己所信、所靠、所活的故事。"
    dom_names = "、".join(DOMAIN_INDEX[d]["name"] for d in detected[:4])
    if not extracted:
        return f"这次输入主要触及：{dom_names}。目前没有明显的扭曲信念，是温柔省察的好时机。"
    lies = "；".join(b["beliefStatement"] for b in extracted[:2])
    tail = f"（综合一致度约 {overall}/100）" if overall is not None else ""
    return (f"这次输入主要触及：{dom_names}。其中可能有值得在神面前省察的信念："
            f"{lies} 这不是定罪，而是邀请——看见它，再用圣经真理重新理解。{tail}")


# ---------------------------------------------------------------------------
# 5. 静态配置
# ---------------------------------------------------------------------------
def meta() -> Dict[str, Any]:
    return {
        "domains": [{"domain": d["domain"], "name": d["name"]} for d in DOMAINS],
        "distortionCount": len(DISTORTION_PATTERNS),
        "scoring": {"baseline": 60, "min": 15, "max": 95,
                    "note": "60=有基本认知；<40=由世俗化/偶像/恐惧驱动；>80=稳定地符合圣经世界观"},
    }
