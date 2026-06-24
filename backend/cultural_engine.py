"""
cultural_engine.py — Cultural Discernment Agent / 文化分辨 Agent

识别用户所处时代文化中的「假应许」「假救主」「日常礼仪 (liturgies)」，帮助分辨
消费主义、个人主义、成功主义、技术救世主义、娱乐成瘾、身份政治、民族主义、
相对主义、虚无主义、功利主义等时代精神。

原则：不做简单反文化姿态；承认共同恩典；分辨「可接受的工具」与「不可敬拜的救主」；
给出反文化操练（安息、奉献、节制、禁食、服事、真实群体连接）。
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

SPIRITS: List[Dict[str, Any]] = [
    {"key": "consumerism", "name": "消费主义",
     "keywords": ["买", "购物", "消费", "升级", "拥有", "名牌", "种草", "剁手"],
     "hidden_promise": "你买得越多，就越完整、越幸福。",
     "hidden_demand": "你必须不断升级生活、永不知足。",
     "liturgies": ["无尽刷购物 App", "把身份建立在拥有物上"],
     "counter_practices": ["节制消费一周", "为一个人奉献金钱或资源", "为已有的具体感恩"],
     "scripture_refs": ["来13:5", "传5:10"]},
    {"key": "individualism", "name": "个人主义",
     "keywords": ["只属于我自己", "我的人生我做主", "不被束缚", "独立", "自由就是"],
     "hidden_promise": "你只属于你自己，自由即无拘束。",
     "hidden_demand": "你不能让任何关系或委身限制你。",
     "liturgies": ["回避一切长期委身", "把群体当作消费选项"],
     "counter_practices": ["向一个群体做一次具体委身", "练习顺服与彼此担当"],
     "scripture_refs": ["林前12:12-27", "腓2:3-4"]},
    {"key": "success_ism", "name": "成功主义",
     "keywords": ["成功", "赢", "成就", "出人头地", "内卷", "比别人强", "证明自己"],
     "hidden_promise": "你成功了才有价值。",
     "hidden_demand": "你必须持续赢、永不停下。",
     "liturgies": ["把休息当罪恶感", "用 KPI 衡量自我价值"],
     "counter_practices": ["守一次安息日", "做一件隐藏的、无回报的善事"],
     "scripture_refs": ["腓3:7-9", "太11:28-30"]},
    {"key": "techno_salvationism", "name": "技术救世主义",
     "keywords": ["ai", "技术", "科技", "效率", "淘汰", "跟不上", "工具", "自动化"],
     "hidden_promise": "技术最终会解决人性与人生的问题；掌握技术就安全。",
     "hidden_demand": "你必须一直升级自己，否则被淘汰。",
     "liturgies": ["强迫式追逐每个新工具", "用生产力定义价值"],
     "counter_practices": ["设定不学技术、不看收益的安息窗口", "用使命过滤技术选择", "祷告交托对未来的恐惧"],
     "scripture_refs": ["诗20:7", "西1:17"]},
    {"key": "entertainment_addiction", "name": "娱乐成瘾",
     "keywords": ["刷视频", "停不下来", "上瘾", "逃避", "麻木", "刺激", "短视频"],
     "hidden_promise": "逃避痛苦就能获得自由。",
     "hidden_demand": "你必须持续被刺激，不能面对安静与空白。",
     "liturgies": ["用刷屏填满每段空白", "以娱乐麻醉情绪"],
     "counter_practices": ["设定媒体禁食时段", "用安静独处面对真实情绪并带到神面前"],
     "scripture_refs": ["诗46:10", "加5:1"]},
    {"key": "identity_politics", "name": "身份政治",
     "keywords": ["身份", "群体", "标签", "立场", "阵营", "道德高地"],
     "hidden_promise": "你的群体身份解释你的一切。",
     "hidden_demand": "你必须用身份争夺道德高地、敌视他者。",
     "liturgies": ["以阵营划分善恶", "把人简化为标签"],
     "counter_practices": ["与立场不同者真诚对话并为其祝福", "默想在基督里超越的合一"],
     "scripture_refs": ["加3:28", "弗2:14-16"]},
    {"key": "nationalism", "name": "民族 / 政治偶像",
     "keywords": ["国家", "民族", "制度", "领袖", "复兴", "爱国"],
     "hidden_promise": "某国家、制度或领袖能带来终极拯救。",
     "hidden_demand": "你必须把终极盼望放在地上权力。",
     "liturgies": ["把政治胜负当救赎大事", "为阵营牺牲真理与爱"],
     "counter_practices": ["为执政者与对立者同样祷告", "把盼望重新放回神的国"],
     "scripture_refs": ["诗146:3", "腓3:20"]},
    {"key": "relativism", "name": "相对主义",
     "keywords": ["没有绝对", "都是相对", "你的真理", "我的真理", "没有对错"],
     "hidden_promise": "没有绝对真理，你可以自由定义一切。",
     "hidden_demand": "你不能承认任何高于自我的权威。",
     "liturgies": ["把一切道德判断私人化", "以『不评判』回避真理"],
     "counter_practices": ["在一处具体伦理上顺服圣经而非感觉", "默想真理使人自由"],
     "scripture_refs": ["约8:31-32", "约17:17"]},
    {"key": "nihilism", "name": "虚无主义",
     "keywords": ["没有意义", "无所谓", "虚无", "活着干嘛", "都没用"],
     "hidden_promise": "既然无意义，就不用负责、不用承受。",
     "hidden_demand": "你只能靠短暂刺激活着。",
     "liturgies": ["以犬儒回避盼望", "用刺激填补空洞"],
     "counter_practices": ["每天记录一件指向意义的小事", "把空虚带到神面前的哀歌祷告"],
     "scripture_refs": ["传12:13", "约10:10"]},
    {"key": "utilitarianism", "name": "功利主义",
     "keywords": ["有用就是", "划算", "效率", "值不值", "回报", "量化"],
     "hidden_promise": "有用就是好；能量化的才重要。",
     "hidden_demand": "不能量化的东西都不重要。",
     "liturgies": ["用『有没有用』衡量一切关系与活动", "牺牲不可见之善"],
     "counter_practices": ["做一件『无用却美善』的事（敬拜、陪伴、欣赏受造）", "为不可量化之恩感恩"],
     "scripture_refs": ["可14:3-9", "诗27:4"]},
]
_SPIRIT_INDEX = {s["key"]: s for s in SPIRITS}


def discern(user_input: str, *, cultural_topic: str = "", use_ai: bool = False) -> Dict[str, Any]:
    """识别文化时代精神，返回规格结构。"""
    low = (user_input or "").lower()
    detected: List[Dict[str, Any]] = []
    for s in SPIRITS:
        hits = sum(1 for kw in s["keywords"] if kw.lower() in low)
        if hits >= 1:
            detected.append(s)
    # 按命中强度（粗略）排序：保留出现的
    spirits = [s["name"] for s in detected]
    promises = [s["hidden_promise"] for s in detected]
    demands = [s["hidden_demand"] for s in detected]
    liturgies = [lit for s in detected for lit in s["liturgies"]]
    counter = [cp for s in detected for cp in s["counter_practices"]]
    refs = [r for s in detected for r in s["scripture_refs"]]

    next_agents: List[str] = []
    keys = {s["key"] for s in detected}
    if keys & {"consumerism", "success_ism", "techno_salvationism"}:
        next_agents.append("idol_detector")
    if keys & {"techno_salvationism", "success_ism"}:
        next_agents.append("vocation_worldview")

    discernment = _build_discernment(detected)
    risks = _risks(detected)

    out = {
        "culturalTopic": cultural_topic or (detected[0]["name"] if detected else "未识别"),
        "userInput": user_input,
        "detectedSpirits": spirits,
        "culturalLiturgies": liturgies,
        "hiddenPromises": promises,
        "hiddenDemands": demands,
        "biblicalDiscernment": discernment,
        "risksForUser": risks,
        "counterPractices": list(dict.fromkeys(counter))[:6],
        "recommendedScriptureRefs": list(dict.fromkeys(refs)),
        "recommendedNextAgents": list(dict.fromkeys(next_agents)),
    }
    if not use_ai or _llm is None or not detected:
        return out
    system = ("你是文化神学分辨助手。基于识别到的时代精神及其假应许/假要求，用中文改写"
              "biblicalDiscernment（3-5句）：不做简单反文化姿态，承认共同恩典，分辨『可用的工具』"
              "与『不可敬拜的救主』。**不要**引用具体经文出处。只输出 JSON：{\"biblicalDiscernment\":\"...\"}")
    user = (f"输入：{user_input[:800]}\n识别到的时代精神：{spirits}\n"
            f"假应许：{promises}\n假要求：{demands}\n当前 biblicalDiscernment：{discernment}")
    try:
        ai = _llm.enhance(system, user, temperature=0.5, max_tokens=500)
        return _llm.merge_fields(out, ai, ["biblicalDiscernment"])
    except Exception:
        return out


def _build_discernment(detected: List[Dict[str, Any]]) -> str:
    if not detected:
        return ("这段表达里没有显出强烈的时代精神。文化中有共同恩典，也有假救主——"
                "继续操练分辨『可用的工具』与『不可敬拜的偶像』。")
    names = "、".join(s["name"] for s in detected[:3])
    return (f"这里可能有这些时代精神在运作：{names}。它们都给出一个假应许，并悄悄提出一个要求。"
            f"福音的分辨不是简单反对文化，而是认出它把哪一样『好东西』高举成了『救主』，"
            f"再用安息、知足、奉献、服事与真实群体把终极性交还给神。")


def _risks(detected: List[Dict[str, Any]]) -> List[str]:
    out = []
    for s in detected[:3]:
        out.append(f"在『{s['name']}』上，你可能正不知不觉地接受它的要求：{s['hidden_demand']}")
    return out


def meta() -> Dict[str, Any]:
    return {"spirits": [{"key": s["key"], "name": s["name"]} for s in SPIRITS]}
