"""
idolatry_engine.py — 偶像监测系统 / 依附强度指数 (Attachment Intensity Index)

设计原则
========
这个引擎的目标 **不是** 判断「你在拜偶像」、更不是定罪，而是温柔地观测：
    有什么东西正在取代神，成为你安全感、价值感、盼望、身份与顺服的中心。

它把「依附」量化为 **依附强度指数 (Attachment Intensity Index)**，而非「偶像分」，
以避免羞耻与定罪。输出语言始终是邀请性的：把一个「好目标」是否正悄悄变成
「内在依附中心」呈现出来，并导向「识别依附 → 松开控制 → 恢复信靠 → 重新把神放在
中心 → 更自由地爱人和顺服」。

该模块为纯函数 / 无状态，便于被 router 与测试复用。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 1. 七类「功能性偶像」
# ---------------------------------------------------------------------------
# 每类带：温柔的中文名、表现、emoji、相关经文、福音「破除节点」、以及三条建议。
IDOL_TYPES: List[Dict[str, Any]] = [
    {
        "type": "success",
        "name": "成就 / 表现",
        "emoji": "🏆",
        "manifestation": "不成功就觉得自己没价值；用成果证明自己配得被爱。",
        "scripture": {"ref": "腓3:8", "text": "我也将万事当作有损的，因我以认识我主基督耶稣为至宝。"},
        "break_principle": "在基督里的身份 (Identity in Christ) 破除「表现→价值」的捆绑。",
        "suggestions": [
            "暂停一个「为了证明自己」而做的决定，问：若没有成果，我是否仍被神所爱？",
            "今天刻意做一件「无人看见、无回报」的善事，练习在隐密中被神看见。",
            "把一项成就交托祷告：「这是礼物，不是我的身份。」",
        ],
    },
    {
        "type": "money",
        "name": "金钱 / 保障",
        "emoji": "💰",
        "manifestation": "安全感完全依赖资产增长；钱一波动，平安就跟着波动。",
        "scripture": {"ref": "太6:24", "text": "一个人不能事奉两个主……你们不能又事奉神，又事奉玛门。"},
        "break_principle": "天父的供应 (Providence) 破除「资产→安全感」的依附。",
        "suggestions": [
            "本周做一次「不计代价」的奉献或施予，小小地松开对掌控的手。",
            "省察：若收入减少一半，我最怕失去的究竟是物质，还是「我能掌控」的感觉？",
            "为「日用的饮食今日赐给我们」具体感恩三件已有的供应。",
        ],
    },
    {
        "type": "approval",
        "name": "认可 / 被看见",
        "emoji": "👍",
        "manifestation": "极度在意别人的评价；一句否定就能毁掉一整天。",
        "scripture": {"ref": "加1:10", "text": "我现在是要得人的心呢？还是要得神的心呢？……我就不是基督的仆人了。"},
        "break_principle": "神的悦纳 (Adoption) 破除「他人评价→自我价值」的循环。",
        "suggestions": [
            "今天有一个时刻，刻意不去解释、不去争取认可，让它过去。",
            "写下一句神看你的话 (如「你是我的爱子，我喜悦你」)，在被否定时默想。",
            "区分：这件事我是为爱神爱人而做，还是为了被赞许而做？",
        ],
    },
    {
        "type": "control",
        "name": "掌控 / 确定性",
        "emoji": "🎛️",
        "manifestation": "不能接受不确定；用过度计划与管控来抵御焦虑。",
        "scripture": {"ref": "箴3:5-6", "text": "你要专心仰赖耶和华，不可倚靠自己的聪明……他必指引你的路。"},
        "break_principle": "信靠神的主权 (Trust in God's Sovereignty) 破除「恐惧→控制」的链条。",
        "suggestions": [
            "今天留一件事「不去安排」，把它交在神手中，观察自己的不安。",
            "做一次安息式的停顿：什么都不解决，只承认「我不是掌权的那一位」。",
            "省察：我想掌控，是为了保护所爱的，还是因为我不敢信任神？",
        ],
    },
    {
        "type": "relationship",
        "name": "关系 / 某个人",
        "emoji": "💞",
        "manifestation": "没有某个人就崩溃；把对方放在只有神能坐的位置。",
        "scripture": {"ref": "诗73:25", "text": "除你以外，在天上我有谁呢？除你以外，在地上我也没有所爱慕的。"},
        "break_principle": "神是终极的满足 (God as Ultimate Satisfaction) 破除「关系→身份」的依附。",
        "suggestions": [
            "为这段关系祷告：「我爱他/她，但我不靠他/她活着。」",
            "今天独处一小段时间，练习在神面前一个人也是完整的。",
            "省察：我对这个人的需要，是健康的爱，还是把救主的位置给了他/她？",
        ],
    },
    {
        "type": "comfort",
        "name": "舒适 / 安逸",
        "emoji": "🛋️",
        "manifestation": "一切决定都在避免代价；用舒适回避被神呼召的冒险。",
        "scripture": {"ref": "太16:24", "text": "若有人要跟从我，就当舍己，背起他的十字架来跟从我。"},
        "break_principle": "舍己跟随 (Self-denial) 破除「避免代价→属灵停滞」。",
        "suggestions": [
            "今天选一件你一直在回避、却该做的难事，迈出第一步。",
            "省察：我最近的决定，有多少是出于爱与呼召，多少只是为了不付代价？",
            "为一个需要你付出的人或事，主动承担一点不便。",
        ],
    },
    {
        "type": "spiritual_image",
        "name": "属灵形象",
        "emoji": "😇",
        "manifestation": "用属灵表现证明自己；敬虔成了表演，而非与神相交。",
        "scripture": {"ref": "太6:1", "text": "你们要小心，不可将善事行在人的面前，故意叫他们看见。"},
        "break_principle": "因信称义 (Justification by Faith) 破除「属灵表现→自我义」。",
        "suggestions": [
            "今天有一个属灵操练，只在神与你之间进行，不告诉任何人。",
            "向神诚实承认一处你一直在「装」的地方，领受赦免而非表演完美。",
            "省察：我的敬虔是为了亲近神，还是为了维持一个「属灵的人设」？",
        ],
    },
]

# 扩展：规格要求的另外 6 类偶像（Worldview Formation OS）
IDOL_TYPES += [
    {
        "type": "knowledge",
        "name": "知识 / 看透",
        "emoji": "📚",
        "manifestation": "用「我懂、我看透了」来掌控不确定；以理解代替信靠与顺服。",
        "scripture": {"ref": "林前8:1", "text": "知识是叫人自高自大，惟有爱心能造就人。"},
        "break_principle": "敬畏神是知识的开端 (Fear of the Lord) 破除「看透→掌控」。",
        "suggestions": [
            "承认一件你「想通了也仍不能掌控」的事，把它交托给神。",
            "今天选择顺服一件你还没完全理解的真理，而不是先要求全懂。",
            "省察：我追求理解，是为了爱神爱人，还是为了不必信靠？",
        ],
    },
    {
        "type": "technology",
        "name": "技术 / 效率",
        "emoji": "🤖",
        "manifestation": "把盼望放在技术与效率上；相信「跟上技术」就能掌握命运、消除恐惧。",
        "scripture": {"ref": "诗20:7", "text": "有人靠车，有人靠马，但我们要提到耶和华我们神的名。"},
        "break_principle": "人的有限与神的护理破除「技术救世 / 效率至上」。",
        "suggestions": [
            "设定一段「不追技术、不看收益」的安息时间，练习神仍掌权。",
            "省察：我学习/使用技术，是受呼召的治理，还是被恐惧驱赶？",
            "为「即使被时代淘汰，我在神面前的价值不变」具体感恩。",
        ],
    },
    {
        "type": "self_realization",
        "name": "自我实现",
        "emoji": "🌟",
        "manifestation": "把「成为最好的自己 / 忠于自我」当作终极意义，自我成了不可挑战的权威。",
        "scripture": {"ref": "太16:25", "text": "凡要救自己生命的，必丧掉生命；凡为我丧掉生命的，必得着生命。"},
        "break_principle": "在基督里舍己得生破除「自我实现→自我中心」。",
        "suggestions": [
            "今天为一个不会带给你「成长感」的人或事，单纯地舍己服事。",
            "省察：我的「做自己」，是否其实拒绝了任何高于自我的权威？",
            "把一个梦想交托：「若神不让它实现，我是否仍信祂是好的？」",
        ],
    },
    {
        "type": "national_political",
        "name": "民族 / 政治",
        "emoji": "🏛️",
        "manifestation": "把终极盼望放在某国家、制度或领袖上；用政治认同争夺道德高地。",
        "scripture": {"ref": "诗146:3", "text": "你们不要倚靠君王，不要倚靠世人，他一点不能帮助。"},
        "break_principle": "神的国度高于地上权力破除「政治→终极拯救」。",
        "suggestions": [
            "为「立场与你相反」的人祷告祝福，练习国度先于阵营。",
            "省察：我的愤怒/盼望，有多少其实押在了地上的权力上？",
            "把一个时局忧虑交托给那位真正掌管历史的神。",
        ],
    },
    {
        "type": "victimhood",
        "name": "受害 / 苦难叙事",
        "emoji": "🩹",
        "manifestation": "用「我永远是受害者、没人懂我」定义自己；过去成了不可改写的全部身份。",
        "scripture": {"ref": "罗8:37", "text": "然而靠着爱我们的主，在这一切的事上已经得胜有余了。"},
        "break_principle": "在基督里的新身份破除「过去→全部身份」。",
        "suggestions": [
            "诚实承认真实的伤害（不否认），同时把「定义你的权利」交还给神。",
            "今天主动做一件「不属于受害者剧本」的小小选择。",
            "省察：受害叙事给了我什么「好处」，让我不愿离开它？",
        ],
    },
    {
        "type": "power",
        "name": "权力 / 影响力",
        "emoji": "👑",
        "manifestation": "用掌控他人、扩张影响力来获得安全与价值；难以服在权柄与软弱之下。",
        "scripture": {"ref": "可10:43", "text": "只是在你们中间，不是这样。你们中间，谁愿为大，就必作你们的用人。"},
        "break_principle": "舍己的仆人式领导破除「权力→价值」。",
        "suggestions": [
            "今天主动放下一次「本可掌控」的局面，让别人带领。",
            "为一个比你弱小、无法回报你的人服事。",
            "省察：我渴望影响力，是为了服事人，还是为了被需要、被仰望？",
        ],
    },
]

IDOL_INDEX: Dict[str, Dict[str, Any]] = {d["type"]: d for d in IDOL_TYPES}


# ---------------------------------------------------------------------------
# 2. 六个核心省察问题
# ---------------------------------------------------------------------------
CORE_QUESTIONS: List[str] = [
    "我最近最害怕失去什么？",
    "什么东西一旦得不到，我就失去平安？",
    "我最常用什么来证明自己有价值？",
    "什么东西会让我愿意违背良心？",
    "我最近最常思想、最常比较、最常焦虑的是什么？",
    "如果神让我放下它，我最抗拒的是什么？",
]


# ---------------------------------------------------------------------------
# 3. 五个子维度与权重
# ---------------------------------------------------------------------------
DIMENSIONS: List[Dict[str, Any]] = [
    {"key": "identity_dependency", "name": "身份依赖", "weight": 0.24,
     "hint": "我用它来定义「我是谁」、证明我有价值。"},
    {"key": "peace_disruption", "name": "平安扰动", "weight": 0.22,
     "hint": "它一旦不顺，我的平安就被打乱。"},
    {"key": "fear_of_loss", "name": "害怕失去", "weight": 0.20,
     "hint": "想到失去它，我会强烈不安、恐惧。"},
    {"key": "obedience_conflict", "name": "顺服冲突", "weight": 0.18,
     "hint": "为了它，我愿意妥协良心或违背神的引导。"},
    {"key": "attention_capture", "name": "注意捕获", "weight": 0.16,
     "hint": "它占据我最多的思想、比较与焦虑。"},
]
DIM_KEYS = [d["key"] for d in DIMENSIONS]


def _clamp(x: float) -> float:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, x))


def compute_intensity(dims: Dict[str, float]) -> float:
    """加权平均得到依附强度指数 (0–1)。"""
    total = 0.0
    for d in DIMENSIONS:
        total += _clamp(dims.get(d["key"], 0.0)) * d["weight"]
    return round(total, 4)


def risk_from_intensity(x: float) -> str:
    if x < 0.35:
        return "low"
    if x < 0.55:
        return "moderate"
    if x < 0.72:
        return "elevated"
    return "high"


RISK_LABELS = {
    "low": {"label": "自由", "color": "#34c759",
            "note": "目前它还在一个健康的位置 —— 是好目标，而非内心中心。"},
    "moderate": {"label": "留意", "color": "#a8e6cf",
                 "note": "出现了一些依附的迹象，值得温柔地观察。"},
    "elevated": {"label": "升高", "color": "#ffd43b",
                 "note": "它正从一个好目标，开始往内在依附中心移动。"},
    "high": {"label": "高度依附", "color": "#ff8787",
             "note": "数据显示它正高度影响你的平安、价值感与决策自由。"},
}


# ---------------------------------------------------------------------------
# 4. 非定罪式说明 + 建议 + Graph 模型
# ---------------------------------------------------------------------------
def build_explanation(idol: Dict[str, Any], dims: Dict[str, float], intensity: float) -> str:
    """生成一段邀请性的、非定罪的说明文字。"""
    name = idol["name"]
    risk = risk_from_intensity(intensity)
    # 找出最突出的两个维度
    ranked = sorted(DIMENSIONS, key=lambda d: _clamp(dims.get(d["key"], 0.0)), reverse=True)
    top = [d for d in ranked if _clamp(dims.get(d["key"], 0.0)) >= 0.5][:2]
    top_names = "、".join(d["name"] for d in top) if top else None

    if risk == "low":
        body = (f"当前数据显示，「{name}」还在一个相对自由的位置。"
                f"它是一个好目标，目前并没有取代神成为你内心的中心。")
    else:
        lead = RISK_LABELS[risk]["note"]
        body = (f"当前数据显示，「{name}」{lead}"
                f"它可能正在从一个好目标，慢慢变成内在的依附中心。")
        if top_names:
            body += f"最明显的迹象出现在「{top_names}」上。"
    body += "这不是定罪 —— 而是一个邀请：看见它，然后把它重新交还到它该在的位置。"
    return body


def graph_model(idol_type: str) -> Dict[str, Any]:
    """
    返回该偶像的依附回路 Graph，并叠加福音「破除节点」。

    通用回路（来自规格）：
        fear_of_loss → control_behavior → anxiety → over_focus
        → identity_dependency → deeper_attachment
    """
    idol = IDOL_INDEX.get(idol_type, {})
    chain = [
        {"id": "fear_of_loss", "label": "害怕失去"},
        {"id": "control_behavior", "label": "控制 / 抓取"},
        {"id": "anxiety", "label": "焦虑不安"},
        {"id": "over_focus", "label": "过度专注 / 比较"},
        {"id": "identity_dependency", "label": "身份依附"},
        {"id": "deeper_attachment", "label": "更深的依附"},
    ]
    # 福音原则破除节点（哪条边被斩断）
    breaks = [
        {"principle": "信靠神 (Trust in God)", "breaks": ["fear_of_loss", "control_behavior"],
         "note": "信靠斩断「害怕失去 → 控制行为」。"},
        {"principle": "安息 (Sabbath)", "breaks": ["over_focus", "identity_dependency"],
         "note": "安息斩断「过度投入 → 身份依附」。"},
        {"principle": "谦卑 (Humility)", "breaks": ["over_focus", "anxiety"],
         "note": "谦卑斩断「比较 → 焦虑」。"},
    ]
    if idol:
        breaks.insert(0, {
            "principle": idol.get("break_principle", ""),
            "breaks": ["identity_dependency", "deeper_attachment"],
            "note": idol.get("break_principle", ""),
        })
    return {"chain": chain, "breaks": breaks}


def suggestions_for(idol_type: str) -> List[str]:
    idol = IDOL_INDEX.get(idol_type)
    base = [
        "暂停基于恐惧的决定 —— 不在不安里做选择。",
        "省察：如果这件事失败了，我是否仍相信自己在神面前有价值？",
        "做一个小的顺服行动，打破对结果的绝对依赖。",
    ]
    if not idol:
        return base
    # 偶像专属建议优先，通用建议兜底
    return list(idol.get("suggestions", []))[:3] or base


# ---------------------------------------------------------------------------
# 5. 来自其它子系统的信号增益 (enrichment)
# ---------------------------------------------------------------------------
# signals 形如：
#   {
#     "emotion": {"anxiety": 0.7, "fear": 0.6, "envy": 0.3},   # 情绪系统
#     "fear_tendency": 0.65, "pride_tendency": 0.4,             # Formation 系统
#     "decision_fear": 0.7,                                     # 决策系统驱动力
#     "loop_detected": "恐惧-控制回路",                          # Graph 系统
#     "top_focus": "work",                                      # 注意力系统
#   }
# 这些是「客观痕迹」，用来：(a) 给已选偶像的子维度做温和加权；(b) 自动提示可能的偶像。
_FOCUS_TO_IDOL = {
    "work": "success", "career": "success",
    "money": "money", "finance": "money",
    "relationship": "relationship", "family": "relationship",
    "future": "control", "self": "approval",
    "spirituality": "spiritual_image",
}


def enrich_dims(dims: Dict[str, float], signals: Optional[Dict[str, Any]]) -> Dict[str, float]:
    """用客观信号对子维度做温和（最多 +0.15）加权，并返回 detected_from 列表。"""
    out = {k: _clamp(dims.get(k, 0.0)) for k in DIM_KEYS}
    sources = set(["self_reflection"])
    if not signals:
        return out, sources  # type: ignore

    emo = signals.get("emotion") or {}
    anx = _clamp(emo.get("anxiety", 0.0))
    fear = _clamp(emo.get("fear", 0.0))
    envy = _clamp(emo.get("envy", 0.0))
    if anx or fear:
        out["peace_disruption"] = min(1.0, out["peace_disruption"] + 0.15 * max(anx, fear))
        out["fear_of_loss"] = min(1.0, out["fear_of_loss"] + 0.12 * max(anx, fear))
        sources.add("emotion")
    if envy:
        out["attention_capture"] = min(1.0, out["attention_capture"] + 0.12 * envy)
        sources.add("emotion")

    ft = _clamp(signals.get("fear_tendency", 0.0))
    if ft >= 0.5:
        out["fear_of_loss"] = min(1.0, out["fear_of_loss"] + 0.10 * ft)
        sources.add("formation")

    dfear = _clamp(signals.get("decision_fear", 0.0))
    if dfear >= 0.5:
        out["obedience_conflict"] = min(1.0, out["obedience_conflict"] + 0.10 * dfear)
        sources.add("decision")

    if signals.get("loop_detected"):
        out["attention_capture"] = min(1.0, out["attention_capture"] + 0.08)
        sources.add("graph")

    return out, sources  # type: ignore


def suggested_targets(signals: Optional[Dict[str, Any]]) -> List[str]:
    """根据注意力 / 情绪信号，提示用户可能值得省察的偶像类型。"""
    if not signals:
        return []
    out: List[str] = []
    focus = signals.get("top_focus")
    if focus and focus in _FOCUS_TO_IDOL:
        out.append(_FOCUS_TO_IDOL[focus])
    emo = signals.get("emotion") or {}
    if _clamp(emo.get("envy", 0.0)) >= 0.4:
        out.append("approval")
    if _clamp(signals.get("fear_tendency", 0.0)) >= 0.6:
        out.append("control")
    # 去重保序
    seen, dedup = set(), []
    for t in out:
        if t not in seen and t in IDOL_INDEX:
            seen.add(t)
            dedup.append(t)
    return dedup


# ---------------------------------------------------------------------------
# 6. 主入口：对一次省察打分
# ---------------------------------------------------------------------------
def assess(ratings: List[Dict[str, Any]],
           signals: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    输入若干条对某偶像类型的子维度评分，输出完整分析。

    ratings 每项: {target_type, target_name?, <五个子维度 0–1>}
    返回:
      {
        patterns: [ {target_type, target_name, dims, intensity, risk_level,
                     detected_from, explanation, graph, suggestions, scripture, meta} ],
        top: {target_type, intensity, risk_level} | None,
        summary: str,
      }
    """
    patterns: List[Dict[str, Any]] = []
    for r in ratings or []:
        ttype = r.get("target_type")
        idol = IDOL_INDEX.get(ttype)
        if not idol:
            continue
        raw = {k: _clamp(r.get(k, 0.0)) for k in DIM_KEYS}
        dims, sources = enrich_dims(raw, signals)
        intensity = compute_intensity(dims)
        risk = risk_from_intensity(intensity)
        patterns.append({
            "target_type": ttype,
            "target_name": (r.get("target_name") or "").strip()[:200],
            "dims": dims,
            "intensity": intensity,
            "risk_level": risk,
            "detected_from": ",".join(sorted(sources)),
            "explanation": build_explanation(idol, dims, intensity),
            "graph": graph_model(ttype),
            "suggestions": suggestions_for(ttype),
            "scripture": idol["scripture"],
            "meta": {"name": idol["name"], "emoji": idol["emoji"]},
        })

    patterns.sort(key=lambda p: p["intensity"], reverse=True)
    top = None
    if patterns:
        t = patterns[0]
        top = {"target_type": t["target_type"], "intensity": t["intensity"],
               "risk_level": t["risk_level"], "name": t["meta"]["name"]}

    summary = _overall_summary(patterns)
    return {"patterns": patterns, "top": top, "summary": summary}


def _overall_summary(patterns: List[Dict[str, Any]]) -> str:
    if not patterns:
        return "这次省察没有发现明显的依附迹象。愿你在神面前继续自由地爱人与顺服。"
    high = [p for p in patterns if p["risk_level"] in ("elevated", "high")]
    if not high:
        return ("整体看，目前没有任何东西高度取代神的位置。继续保持这份对内心的诚实 —— "
                "识别、松手、信靠，是一生的操练。")
    names = "、".join(p["meta"]["name"] for p in high[:2])
    return (f"整体看，「{names}」目前最值得你温柔留意 —— 它或许正在靠近你内心的中心。"
            f"路径很清楚：识别依附 → 松开控制 → 恢复信靠 → 重新把神放在中心 → "
            f"更自由地爱人和顺服。你不需要靠自己撬动它，只需要先看见，然后交还。")


# 便于 router / 前端获取静态配置
def meta() -> Dict[str, Any]:
    return {
        "idol_types": [
            {k: v for k, v in d.items() if k != "suggestions"} for d in IDOL_TYPES
        ],
        "core_questions": CORE_QUESTIONS,
        "dimensions": DIMENSIONS,
        "risk_labels": RISK_LABELS,
    }


# ---------------------------------------------------------------------------
# 7. 回流 Formation（闭环）：把一次省察折算成「形成事件」信号
# ---------------------------------------------------------------------------
# 偶像类型 → formation pattern category（fear/pride/relational/desire/growth…）
IDOL_TO_PATTERN = {
    "success": "pride", "approval": "pride", "spiritual_image": "pride",
    "control": "fear", "money": "fear", "comfort": "fear",
    "relationship": "relational",
    # 扩展 6 类
    "knowledge": "pride", "self_realization": "pride", "power": "pride",
    "national_political": "pride", "technology": "fear", "victimhood": "fear",
}


def formation_signal(result: Dict[str, Any]):
    """
    返回 (pattern_categories, loop_broken, reflection_active, emotional_intensity)。
    诚实但温柔：诚实的自我省察本身是 reflection（成长），高依附则如实地轻推相应倾向；
    若没有明显依附，则记为 growth。返回 None 表示无需记录。
    """
    top = result.get("top")
    if not top:
        return (["growth"], True, True, 4.0)
    cat = IDOL_TO_PATTERN.get(top.get("target_type"), "desire")
    intensity = float(top.get("intensity", 0.0))
    pats = [cat]
    if intensity >= 0.55 and cat != "desire":
        pats.append("desire")
    loop_broken = intensity < 0.35           # 低依附 = 自由
    emo = round(3.0 + intensity * 6.0, 1)
    return (pats, loop_broken, True, emo)
