"""
formation_practice_engine.py — Formation Practice Agent / 世界观操练 Agent

把诊断/偶像/真理/叙事/苦难/决策的结果，转化为 1/3/7/30/90 天可执行操练计划。
目标不是「知道更多」，而是通过重复操练，让圣经世界观进入情绪、欲望、行为、关系与决策。

安全规则
========
- 危机(high/imminent)用户：只生成安全支持与温和陪伴，不生成高强度计划。
- 羞耻状态：不生成过重任务。
- 枯竭(burnout)：优先安息、睡眠、饮食、陪伴、简短祷告。
- 成就偶像：减少绩效化打卡，强调恩典与隐藏忠心。

复用：与既有 spiritual_formation_engine 的 transformation plan 互补；本引擎聚焦
世界观 OS 的 task/library/snapshot 闭环。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# 10 类操练（规格）
PRACTICE_LIBRARY: List[Dict[str, Any]] = [
    {"key": "daily_meditation", "title": "每日默想", "minutes": 10,
     "target_idols": [], "instruction": "默想今日经文，写下神向你说的一句话，以及今天最想交托的一件事。",
     "scripture_refs": ["诗1:2-3"], "reflection": "今天我把什么放在了神的位置上？"},
    {"key": "anti_idol", "title": "反偶像操练", "minutes": 10,
     "target_idols": ["success", "control", "approval", "power"],
     "instruction": "今天有意识地不通过成就/掌控证明自己，做一个隐藏的、无人看见的忠心行动。",
     "scripture_refs": ["太6:3-4"], "reflection": "不靠它，我是否仍相信自己在神面前有价值？"},
    {"key": "repentance_prayer", "title": "悔改祷告", "minutes": 5,
     "target_idols": ["spiritual_performance"],
     "instruction": "向神诚实承认一处把受造之物当作救主的地方：『主啊，我承认我把 ___ 当作安全感。』",
     "scripture_refs": ["罗8:1"], "reflection": "我从哪个谎言转向了哪个真理？"},
    {"key": "gratitude", "title": "感恩记录", "minutes": 5,
     "target_idols": ["money", "victimhood"],
     "instruction": "写下 3 件不是靠你表现换来的恩典。",
     "scripture_refs": ["帖前5:18"], "reflection": "感恩如何松动了我的比较与匮乏感？"},
    {"key": "sabbath_rest", "title": "安息操练", "minutes": 120,
     "target_idols": ["control", "success", "technology"],
     "instruction": "设定 2 小时不工作、不学习、不查看收益、不比较别人，单纯安息。",
     "scripture_refs": ["太11:28-30"], "reflection": "停下来时，我的不安暴露了我在靠什么活着？"},
    {"key": "giving", "title": "奉献操练", "minutes": 30,
     "target_idols": ["money", "security"],
     "instruction": "为一个具体的人或事奉献时间、金钱或资源，松开对掌控的手。",
     "scripture_refs": ["林后9:7"], "reflection": "奉献时我最舍不得的是什么？"},
    {"key": "service", "title": "服事行动", "minutes": 30,
     "target_idols": ["success", "self_realization", "power"],
     "instruction": "今天主动鼓励或服事一个人，不求回报、不让对方知道是你。",
     "scripture_refs": ["可10:43-45"], "reflection": "从自我中心转向爱人，我感受到什么？"},
    {"key": "relational_repair", "title": "关系修复", "minutes": 20,
     "target_idols": ["relationship", "approval"],
     "instruction": "向一个人表达歉意或感谢，主动跨出修复的一步。",
     "scripture_refs": ["弗4:32"], "reflection": "骄傲/防御/苦毒在哪里拦阻了我？"},
    {"key": "tech_temperance", "title": "技术节制", "minutes": 15,
     "target_idols": ["technology", "knowledge"],
     "instruction": "设定 AI / 信息工具的使用边界，并写下你使用它们的目的（治理而非依赖）。",
     "scripture_refs": ["林前6:12"], "reflection": "我是在使用工具，还是被工具使用？"},
    {"key": "lament_prayer", "title": "哀歌祷告", "minutes": 15,
     "target_idols": ["victimhood"],
     "instruction": "向神诚实说出痛苦（呼求→倾诉→肯定），同时抓住一个盼望应许。",
     "scripture_refs": ["诗13"], "reflection": "在痛苦中，我抓住了神怎样的应许？"},
]
_LIB = {p["key"]: p for p in PRACTICE_LIBRARY}

_IDOL_TO_PRACTICES = {
    "success": ["anti_idol", "sabbath_rest", "service", "gratitude"],
    "control": ["sabbath_rest", "anti_idol", "daily_meditation"],
    "money": ["giving", "gratitude"],
    "security": ["giving", "gratitude"],
    "technology": ["tech_temperance", "sabbath_rest"],
    "knowledge": ["tech_temperance", "daily_meditation"],
    "approval": ["relational_repair", "anti_idol"],
    "relationship": ["relational_repair", "daily_meditation"],
    "self_realization": ["service", "repentance_prayer"],
    "power": ["service", "anti_idol"],
    "spiritual_performance": ["repentance_prayer", "daily_meditation"],
    "victimhood": ["lament_prayer", "gratitude"],
    "comfort": ["service", "sabbath_rest"],
    "pleasure": ["sabbath_rest", "gratitude"],
}

_IDOL_ZH = {"success": "成就", "control": "控制", "money": "金钱", "technology": "技术",
            "relationship": "关系", "approval": "认可", "victimhood": "受害叙事",
            "spiritual_performance": "属灵表现", "power": "权力", "knowledge": "知识"}


def generate_plan(*, focus_idols: Optional[List[str]] = None,
                  focus_domains: Optional[List[str]] = None,
                  duration_days: int = 7, intensity: str = "normal",
                  safety: Optional[Dict[str, bool]] = None) -> Dict[str, Any]:
    """生成操练计划。safety = {crisis, shame, burnout}。"""
    focus_idols = focus_idols or []
    safety = safety or {}

    if safety.get("crisis"):
        return _gentle_support_plan(duration_days)
    if safety.get("burnout"):
        return _burnout_plan(duration_days)

    # 选择操练（默想 + 悔改/反谎言祷告 为基底）
    keys: List[str] = ["daily_meditation", "repentance_prayer"]
    for idol in focus_idols:
        for k in _IDOL_TO_PRACTICES.get(idol, []):
            if k not in keys:
                keys.append(k)
    if not focus_idols:
        keys += ["gratitude", "sabbath_rest", "service"]
    # 羞耻：去掉绩效化打卡，强调恩典
    if safety.get("shame"):
        keys = [k for k in keys if k not in ("anti_idol",)]
        if "repentance_prayer" not in keys:
            keys.insert(1, "repentance_prayer")

    # 强度 → 每日任务数
    per_day = {"gentle": 2, "normal": 3, "deep": 4}.get(intensity, 3)
    days = max(1, min(int(duration_days or 7), 90))

    tasks = _build_tasks(keys, days, per_day)
    title = _title(focus_idols, days)

    return {
        "planTitle": title,
        "durationDays": days,
        "intensity": intensity,
        "focusSummary": _focus_summary(focus_idols),
        "selectedPractices": keys,
        "tasks": tasks,
        "reviewQuestions": [
            "这段操练里，我看见自己最常依靠什么来代替神？",
            "哪一天我真正经历了把它交还给神的自由？",
            "我的情绪/行为/关系有什么细微的变化？",
        ],
        "successMarkers": ["焦虑降低、更能安息", "能接受自己的有限而不恐慌",
                           "能做隐藏的忠心行动，不需被看见", "比较与抓取减少"],
        "warningSigns": ["把操练本身变成新的表现主义（用打卡证明属灵）",
                         "因做不到而陷入羞耻——记得这是恩典里的成长，不是考核"],
    }


def _build_tasks(keys: List[str], days: int, per_day: int) -> List[Dict[str, Any]]:
    tasks: List[Dict[str, Any]] = []
    n = len(keys)
    for day in range(1, days + 1):
        day_keys = []
        # 默想每天都有；其余轮转
        day_keys.append("daily_meditation")
        i = 0
        while len(day_keys) < per_day and i < n:
            k = keys[(day - 1 + i) % n]
            if k not in day_keys:
                day_keys.append(k)
            i += 1
        for k in day_keys:
            p = _LIB[k]
            tasks.append({
                "day": day, "practiceKey": k, "title": p["title"],
                "instructions": p["instruction"], "scriptureRefs": p["scripture_refs"],
                "reflectionPrompt": p["reflection"], "expectedMinutes": p["minutes"],
            })
        # 30/90 天计划：每 7 天插入一次安息日复盘，避免过载
        if days >= 30 and day % 7 == 0:
            tasks.append({"day": day, "practiceKey": "sabbath_rest", "title": "周安息复盘",
                          "instructions": "回顾这一周，向神感恩与交托，不安排生产性任务。",
                          "scriptureRefs": ["太11:28-30"], "reflectionPrompt": "这周神在我里面动了什么工？",
                          "expectedMinutes": 60})
    return tasks


def _title(focus_idols: List[str], days: int) -> str:
    if not focus_idols:
        return f"{days} 天：在恩典中操练信靠与忠心"
    zh = "、".join(_IDOL_ZH.get(i, i) for i in focus_idols[:2])
    return f"{days} 天：从{zh}，转向交托与隐藏的忠心"


def _focus_summary(focus_idols: List[str]) -> str:
    if not focus_idols:
        return "在日常重复中，让福音真理进入情绪、欲望与行为。"
    zh = "、".join(_IDOL_ZH.get(i, i) for i in focus_idols)
    return f"本期聚焦松开对「{zh}」的依附，重新把神放在中心，更自由地爱人与顺服。"


def _gentle_support_plan(days: int) -> Dict[str, Any]:
    return {
        "planTitle": "温和陪伴：先安全、先安息",
        "durationDays": min(days, 7), "intensity": "gentle", "focusSummary": "现在不是操练强度的时候，而是被陪伴、被照顾。",
        "selectedPractices": ["lament_prayer", "daily_meditation"],
        "tasks": [
            {"day": 1, "practiceKey": "safety", "title": "安全第一",
             "instructions": "今天最重要的是安全：联系一位可信任的人，让他陪着你。",
             "scriptureRefs": ["诗34:18"], "reflectionPrompt": "我现在可以联系谁？", "expectedMinutes": 10},
            {"day": 1, "practiceKey": "lament_prayer", "title": "一句简短的祷告",
             "instructions": "只需向神说一句真实的话，哪怕只是『主啊，我撑不住了』。",
             "scriptureRefs": ["诗130:1"], "reflectionPrompt": "", "expectedMinutes": 3},
        ],
        "reviewQuestions": ["今天我有没有让一个人知道我的处境？"],
        "successMarkers": ["没有独自一人", "联系到了可信任的人"],
        "warningSigns": ["独自硬撑", "把痛苦合理化为『不值得麻烦别人』"],
    }


def _burnout_plan(days: int) -> Dict[str, Any]:
    return {
        "planTitle": f"{min(days,7)} 天：先休息，像以利亚那样被神照顾",
        "durationDays": min(days, 7), "intensity": "gentle",
        "focusSummary": "枯竭时，神先让你睡、让你吃，再轻声说话。优先身体与陪伴，而非更多任务。",
        "selectedPractices": ["sabbath_rest", "gratitude", "daily_meditation"],
        "tasks": [
            {"day": 1, "practiceKey": "sabbath_rest", "title": "睡眠与饮食",
             "instructions": "今天好好睡、好好吃，安排一段什么都不做的休息。",
             "scriptureRefs": ["王上19:5-8"], "reflectionPrompt": "我允许自己休息吗？", "expectedMinutes": 60},
            {"day": 1, "practiceKey": "gratitude", "title": "一件小恩典",
             "instructions": "只记下一件今天的小恩典，不必做更多。",
             "scriptureRefs": ["哀3:22-23"], "reflectionPrompt": "", "expectedMinutes": 3},
        ],
        "reviewQuestions": ["这几天我的身体被善待了吗？", "我有没有让人陪我？"],
        "successMarkers": ["睡眠/饮食改善", "不再用任务证明自己", "接受被照顾"],
        "warningSigns": ["把休息也变成另一项要完成的 KPI"],
    }


def meta() -> Dict[str, Any]:
    return {"practices": [{"key": p["key"], "title": p["title"]} for p in PRACTICE_LIBRARY],
            "durations": [1, 3, 7, 30, 90], "intensities": ["gentle", "normal", "deep"]}
