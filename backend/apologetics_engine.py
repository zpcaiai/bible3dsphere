"""
apologetics_engine.py — Apologetics Lens Agent / 护教学视角 Agent

处理哲学、科学、AI、政治、历史、技术、文化、宗教比较的问题，识别问题背后的世界观
**预设 (presupposition)**，对比常见世俗框定，再给出圣经世界观回应。

固定回答结构（规格）：
  1. 问题背后的世界观前提
  2. 常见世俗世界观如何回答
  3. 圣经世界观如何重新框定
  4. 容易走偏的地方
  5. 对信徒生活/职业/技术/使命的应用
  6. 可继续操练的问题

安全：涉及现实政治、医学、法律、金融时提示「非专业建议」；不制造阴谋论；允许复杂与张力。
"""
from __future__ import annotations

from typing import Any, Dict, List

try:
    from backend import worldview_llm as _llm
except Exception:  # pragma: no cover
    try:
        import worldview_llm as _llm  # type: ignore
    except Exception:
        _llm = None  # type: ignore

TOPICS: List[Dict[str, Any]] = [
    {
        "topic": "technology_ai",
        "keywords": ["ai", "人工智能", "技术", "科技", "机器", "自动化", "终局", "奇点"],
        "presuppositions": [
            "人的价值主要来自智能与生产力",
            "技术进步具有准救赎意义（技术救世主义）",
            "人类未来主要由技术决定",
            "创造主与受造界的边界被模糊",
        ],
        "secular_framings": [
            {"worldview": "技术乐观主义", "answerSummary": "AI 将解决人类大多数问题，带来繁荣与解放。",
             "limitation": "无法处理罪、死亡与意义问题；把工具当成了救主。"},
            {"worldview": "技术悲观/末世恐惧", "answerSummary": "AI 终将取代甚至毁灭人类。",
             "limitation": "以恐惧为终极框架，忽略神对历史的护理与人的受造尊严。"},
        ],
        "biblical_framing": (
            "人的价值来自神的形象，而非算力或产出（创1:26-27）。技术是受造界中『治理/耕耘』"
            "使命的延伸，是工具而非救主（创2:15）。罪的问题不能靠工具消除，只能靠基督的救赎。"
            "终极盼望不是技术乌托邦，而是神国的成全（西1:15-20）。"
        ),
        "scripture_refs": ["创1:26-27", "创11:1-9", "诗8:3-6", "西1:15-20"],
        "doctrine_tags": ["imago_dei", "创造使命", "human_finitude", "providence"],
        "pastoral_cautions": [
            "不要把技术当救主，也不要陷入技术恐惧；两者都是把终极性错置。",
            "不要把 AI 简单等同于启示录的兽——避免阴谋论，承认共同恩典。",
        ],
        "resources": ["《返璞归真》C.S.路易斯", "凯波尔《加尔文主义讲座》中的领域主权"],
        "next_agents": ["cultural_discernment", "vocation_worldview"],
    },
    {
        "topic": "science_faith",
        "keywords": ["科学", "证明神", "进化", "创造", "宇宙", "理性", "证据"],
        "presuppositions": [
            "只有可被自然科学验证的才算真实（科学主义）",
            "信仰与理性必然冲突",
            "物质世界是唯一实在",
        ],
        "secular_framings": [
            {"worldview": "科学主义/自然主义", "answerSummary": "科学终将解释一切，神是多余假设。",
             "limitation": "『只有科学才是真理』本身不是科学命题，自我反驳；无法奠定道德、意义与理性的可靠性。"},
        ],
        "biblical_framing": (
            "圣经与真科学不冲突：神是创造的主，也是理性秩序的根源（西2:3）。科学研究受造界的"
            "『如何』，圣经启示『为何』与『谁』。承认科学的能力，也承认它的边界。"
        ),
        "scripture_refs": ["诗19:1", "西2:2-3", "罗1:19-20"],
        "doctrine_tags": ["general_revelation", "creation", "wisdom"],
        "pastoral_cautions": ["不必在每个科学细节上『护教焦虑』；允许诚实的未知与张力。"],
        "resources": ["《现代科学的基督教根基》", "提姆·凯勒《我为什么相信》"],
        "next_agents": ["cultural_discernment"],
    },
    {
        "topic": "politics_power",
        "keywords": ["政治", "制度", "民主", "威权", "国家", "领袖", "革命", "权力"],
        "presuppositions": [
            "某种制度或领袖能带来终极拯救",
            "终极盼望应放在地上的权力结构",
            "道德高地由政治阵营决定",
        ],
        "secular_framings": [
            {"worldview": "政治弥赛亚主义", "answerSummary": "只要正确的人/制度掌权，就能实现救赎式的好世界。",
             "limitation": "把有限、堕落的人类权力终极化；历史一再证明它带来失望与压迫。"},
        ],
        "biblical_framing": (
            "神掌管历史，地上权柄是神所设立、却有限且要被审判的（罗13；启）。基督徒既参与公共"
            "善工，又不把终极盼望押在任何党派或领袖上（诗146:3）。"
        ),
        "scripture_refs": ["诗146:3", "罗13:1-7", "腓3:20"],
        "doctrine_tags": ["sovereignty", "common_grace", "已然未然"],
        "pastoral_cautions": ["这不是专业政治/法律建议。", "警惕用信仰为单一阵营背书，撕裂肢体。"],
        "resources": ["奥古斯丁《上帝之城》", "凯波尔领域主权"],
        "next_agents": ["cultural_discernment"],
    },
    {
        "topic": "religion_comparison",
        "keywords": ["佛教", "伊斯兰", "印度教", "无神论", "其他宗教", "都一样", "条条大路"],
        "presuppositions": [
            "所有宗教在本质上都一样（宗教多元主义）",
            "真理是主观的、因人而异",
        ],
        "secular_framings": [
            {"worldview": "宗教多元主义", "answerSummary": "所有宗教都是通往同一座山顶的不同道路。",
             "limitation": "各宗教对神、人、罪、救赎的核心主张彼此矛盾，不能同真；『都一样』本身是一种排他主张。"},
        ],
        "biblical_framing": (
            "基督信仰的独特在于：救恩是神主动的恩典，藉着道成肉身、受死复活的基督成就（约14:6；"
            "弗2:8-9），而非人靠功德攀登。以尊重与爱，诚实陈明这份不同。"
        ),
        "scripture_refs": ["约14:6", "徒4:12", "弗2:8-9"],
        "doctrine_tags": ["solus_christus", "grace", "revelation"],
        "pastoral_cautions": ["以温柔敬畏回应（彼前3:15-16），不贬低他人，不傲慢。"],
        "resources": ["提姆·凯勒《诸神的面具》", "鲁益师《返璞归真》"],
        "next_agents": [],
    },
    {
        "topic": "money_economy",
        "keywords": ["资本主义", "消费主义", "功利", "市场", "效率", "财富", "成功学"],
        "presuppositions": [
            "有用/能量化的才有价值（功利主义）",
            "拥有越多越完整（消费主义）",
            "人主要是经济动物",
        ],
        "secular_framings": [
            {"worldview": "消费/功利主义", "answerSummary": "幸福=效用最大化与不断升级的消费。",
             "limitation": "无法为不可量化之物（爱、敬拜、安息、人的尊严）定位；制造永不满足的循环。"},
        ],
        "biblical_framing": (
            "人是按神形象被造的敬拜者，不只是消费者或生产单位。财富是托管，工作是管家职分，"
            "安息与知足是对『更多即更好』的福音式抵抗（来13:5；传）。"
        ),
        "scripture_refs": ["提前6:6-10", "来13:5", "太6:24"],
        "doctrine_tags": ["stewardship", "contentment", "sabbath"],
        "pastoral_cautions": ["不必妖魔化市场或财富本身；问题是把它终极化。"],
        "resources": ["《诸神的面具》", "傅士德《属灵操练礼赞》"],
        "next_agents": ["cultural_discernment", "vocation_worldview"],
    },
]

_FALLBACK_TOPIC = {
    "topic": "general",
    "presuppositions": ["这个问题背后可能预设了某个不被检视的终极权威或价值标准。"],
    "secular_framings": [{"worldview": "世俗默认", "answerSummary": "以人自身为终极标准来回答。",
                          "limitation": "缺少超越的根基，难以稳固地奠定意义、道德与盼望。"}],
    "biblical_framing": "圣经世界观从『神是创造、救赎与终末的主』出发重新框定问题——先问『谁是终极权威』。",
    "scripture_refs": ["箴1:7", "西2:2-3"],
    "doctrine_tags": ["revelation", "wisdom"],
    "pastoral_cautions": ["允许复杂性与张力，不急于给出口号式答案。"],
    "resources": ["提姆·凯勒《我为什么相信》"],
    "next_agents": [],
}


def _detect_topic(question: str) -> Dict[str, Any]:
    low = (question or "").lower()
    best, best_hits = None, 0
    for t in TOPICS:
        hits = sum(1 for kw in t["keywords"] if kw.lower() in low)
        if hits > best_hits:
            best, best_hits = t, hits
    return best if best_hits >= 1 else _FALLBACK_TOPIC


def analyze(question: str, *, locale: str = "zh-CN", use_ai: bool = False) -> Dict[str, Any]:
    """对一个护教学问题做世界观分析，返回规格结构。"""
    t = _detect_topic(question)
    response = _compose_response(t, question)
    out = {
        "topic": t["topic"],
        "userQuestion": question,
        "detectedPresuppositions": list(t["presuppositions"]),
        "secularFramings": list(t["secular_framings"]),
        "biblicalFraming": t["biblical_framing"],
        "apologeticsResponse": response,
        "scriptureRefs": list(t["scripture_refs"]),
        "doctrineTags": list(t["doctrine_tags"]),
        "pastoralCautions": list(t["pastoral_cautions"]),
        "recommendedResources": list(t["resources"]),
        "recommendedNextAgents": list(t["next_agents"]),
        "confidence": 0.8 if t is not _FALLBACK_TOPIC else 0.4,
    }
    if not use_ai or _llm is None:
        return out
    system = ("你是基督教护教学助手。基于给定的世界观前提与圣经框定，用清晰、尊重、有张力意识的"
              "中文改写 biblicalFraming（2-4句）与 apologeticsResponse（按『前提→世俗回答→圣经框定→"
              "易走偏处→应用→可操练问题』结构，200-350字）。**不要**捏造或引用具体经文出处；"
              "不制造阴谋论。只输出 JSON：{\"biblicalFraming\":\"...\",\"apologeticsResponse\":\"...\"}")
    user = (f"问题：{question[:1000]}\n前提：{out['detectedPresuppositions']}\n"
            f"当前 biblicalFraming：{out['biblicalFraming']}\n当前回应：{out['apologeticsResponse']}")
    try:
        ai = _llm.enhance(system, user, temperature=0.5, max_tokens=700)
        return _llm.merge_fields(out, ai, ["biblicalFraming", "apologeticsResponse"])
    except Exception:
        return out


def _compose_response(t: Dict[str, Any], question: str) -> str:
    pres = "；".join(t["presuppositions"][:2])
    secular = t["secular_framings"][0]["answerSummary"] if t["secular_framings"] else ""
    return (
        f"1) 这个问题背后的世界观前提：{pres}。\n"
        f"2) 常见世俗回答：{secular}\n"
        f"3) 圣经世界观如何重新框定：{t['biblical_framing']}\n"
        f"4) 容易走偏处：{t['pastoral_cautions'][0] if t['pastoral_cautions'] else '把有限之物终极化。'}\n"
        f"5) 应用：让这份框定落到你的生活、职业、技术使用与使命选择中。\n"
        f"6) 可继续操练：在祷告中问『我此刻把终极权威放在了哪里？』"
    )


def meta() -> Dict[str, Any]:
    return {"topics": [{"topic": t["topic"], "keywords": t["keywords"]} for t in TOPICS]}
