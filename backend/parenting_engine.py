"""
parenting_engine.py — 教养儿女 · 家庭门训（申6；Paul Tripp《为人父母》Parenting）

**完全缺失**的领域。核心不是育儿技巧，而是「在家中作门徒的父母」的属灵框架。
申6:6-7：把神的话「殷勤教训你的儿女……坐、行、躺、起，都要谈论」——门训在日常缝隙里发生。

Tripp 的两个转向：
  · 父母不是儿女的『主人/塑造者』，而是神所差、暂时受托的『大使』——目标不是让孩子听我，而是把他们指向神；
  · 教养不靠『控制』行为，而靠『福音』触及心——孩子的问题行为底下是心的问题，父母自己也是蒙恩的罪人，
    与孩子一同站在十字架前，而非高高在上。

要点：靠恩典而非控制；以身作则地悔改（让孩子看见你也认罪、也需要福音）；把握日常的门训缝隙；
为孩子的心（而非只为成绩/表现）祷告；把结果交托神（你负责忠心撒种，生长在乎神）。

纯函数；确定性；内置危机词检测（含父母的耗竭/自责）；AI 可选增强。不定罪父母、不给完美父母的重担。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

STATES: List[Dict[str, Any]] = [
    {"key": "control", "name": "总在管教却越管越僵 / 靠吼靠罚",
     "kw": ["管不住", "越管越", "吼", "罚", "对着干", "叛逆", "控制", "冲突", "管教", "发火"],
     "diag": "你在努力『控制行为』，却越控越僵。Tripp 会说：孩子的问题行为底下是心的问题，光管行为、够不到心。",
     "way": "从『控制』转向『触及心』：管教之外，多问『你心里在想什么/怕什么/要什么』，把福音带到那颗心。"
            "也别忘了你自己是蒙恩的罪人——放下『我说了算』的高姿态，与孩子一同站在十字架前。"
            "靠恩典教养，比靠权力压制，更能赢得一颗心。",
     "ref": "弗6:4", "text": "你们作父亲的，不要惹儿女的气，只要照着主的教训和警戒养育他们。"},
    {"key": "disciple", "name": "想在日常里带孩子认识神 / 家庭门训",
     "kw": ["带孩子信", "家庭门训", "家庭祭坛", "怎么教信仰", "灵修", "读经给孩子", "属灵教养", "信仰传承", "带孩子祷告"],
     "diag": "你想把信仰传给下一代——申6 说，这主要不在正式课堂，而在日常的缝隙：坐、行、躺、起，随时谈论神。",
     "way": "别等『完美的家庭祭坛』才开始。把神自然编进日常：睡前一句祷告、饭前谢恩、路上聊聊白天里神的恩典、"
            "一起看见受造之美就赞叹祂。门训是生活方式，不是又一门功课。你自己先真实地爱神，孩子会看见并被吸引。",
     "ref": "申6:6-7", "text": "我今日所吩咐你的话都要记在心上，也要殷勤教训你的儿女。无论你坐在家里，行在路上，躺下，起来，都要谈论。"},
    {"key": "example", "name": "怕自己做得不好、以身作则的压力",
     "kw": ["做不好", "以身作则", "怕影响", "自己都", "榜样", "怕带坏", "言行不一", "压力", "怕做错父母"],
     "diag": "你怕自己不够好会带坏孩子——这份看重是好的，但『完美父母』不是福音要你背的担子。",
     "way": "孩子需要的不是完美的父母，是一个『愿意在他面前认罪、也活出恩典』的父母。当你做错了，向孩子道歉、"
            "让他看见你也需要福音——这本身就是最有力的门训：他学到的不是『爸妈从不犯错』，而是『犯错了可以回到神面前』。"
            "以身作则，不是无瑕，而是真实地悔改与信靠。",
     "ref": "诗103:13", "text": "父亲怎样怜恤他的儿女，耶和华也怎样怜恤敬畏他的人。"},
    {"key": "worry_child", "name": "为孩子的偏差/未来揪心 / 怕教养失败",
     "kw": ["为孩子担心", "怕教养失败", "孩子走偏", "未来", "揪心", "怕孩子", "担心孩子", "教养失败", "怕没教好"],
     "diag": "你为孩子的路揪心——这是父母心。但要分清：你负责忠心撒种，生长却在乎神；孩子最终也在神面前为自己负责。",
     "way": "把『我必须把孩子塑造成功』的重担卸下，换成『我忠心撒种、把他交托给神』的姿态。"
            "为孩子的『心』祷告（比成绩/表现更要紧），也守住关系的门。若孩子已经偏离，可到『为浪子祷告』页——"
            "你不是独自扛起孩子得救的责任，那是神的工。",
     "ref": "箴22:6", "text": "教养孩童，使他走当行的道，就是到老他也不偏离。"},
    {"key": "exhausted", "name": "为人父母太累了 / 被消耗、快撑不住",
     "kw": ["太累", "撑不住", "被消耗", "崩溃", "喘不过气", "睡不够", "耐心耗尽", "情绪失控", "当父母好难"],
     "diag": "养育儿女是日复一日的倾倒——你会累、会烦、会内疚，这很正常，也被神看见。空了的杯子倒不出水。",
     "way": "先让自己被神喂养、被恩典托住（累到极处可到『耗竭』页）。你不必做全能父母；求神天天给你够用的耐心与恩典，"
            "也允许自己求助、休息。你对孩子最好的礼物之一，是一个『在神里被恢复』的父母，而非一个耗尽自己的父母。",
     "ref": "赛40:11", "text": "他必像牧人牧养自己的羊群……轻轻引导那乳养小羊的。"},
]

CRISIS_WORDS = ["自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死",
                "死了算了", "伤害自己", "撑不下去了", "没有意义活着", "想消失", "不想当妈", "不想当爸"]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = ("我听见你作父母已经累到很深了。如果你有伤害自己的念头，请现在就联系你信任的人或当地心理危机热线。"
               "你不必做完美的父母，也不该独自硬撑——你和孩子都值得你先被好好照顾。（本功能不替代专业帮助。）")


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best, best_hits = None, 0
    for d in STATES:
        hits = sum(1 for k in d["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, d
    return best or (STATES[1] if len(STATES) > 1 else STATES[0])


def meta() -> Dict[str, Any]:
    return {
        "title": "教养儿女 · 家庭门训",
        "source": "申6；Paul Tripp《为人父母》",
        "core": "父母是神所差、暂时受托的大使（把孩子指向神，非让孩子听我）；靠福音触及心，非靠控制管行为；门训在日常缝隙里发生。",
        "states": [{"key": d["key"], "name": d["name"]} for d in STATES],
        "verse": "申6:6-7",
        "principle": "你负责忠心撒种，生长在乎神；养育孩子最有力的门训，是让他看见你也是蒙恩、也悔改、也信靠的罪人。",
    }


def analyze(text: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    text = (text or "").strip()
    crisis = _detect_crisis(text)
    picked = _pick(text)
    result: Dict[str, Any] = {
        "crisis": crisis, "crisis_note": CRISIS_NOTE if crisis else "",
        "state": {"key": picked["key"], "name": picked["name"]},
        "diagnosis": picked["diag"],
        "way_forward": picked["way"],
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "prayer": ("父啊，谢谢你把孩子托付给我——提醒我：我不是他的主人，是你差来的大使，我的使命是把他指向你，而非让他听我。"
                   "帮我不只管行为，更触及他的心；帮我靠恩典而非控制去教养。当我做错，给我勇气向孩子认错，"
                   "让他看见福音在我身上。我忠心撒种，把生长交给你；也求你天天给我够用的耐心与恩典，我自己先被你喂养。"),
        "practices": [
            "把神编进日常：今天选一个缝隙（睡前/饭前/路上），自然地和孩子谈一句神的恩典或做一句祷告。",
            "以身作则地悔改：本周若对孩子发了火或做错了，主动向他道歉——让他看见你也需要福音。",
        ],
        "summary": ("教养的核心不是技巧，是『在家中作门徒的父母』：你是把孩子指向神的大使，靠福音触及心而非靠控制管行为，"
                    "门训在日常缝隙里发生。你忠心撒种，生长交给神；孩子最需要的，是一个真实悔改、信靠恩典的你。"),
        "closing": "「殷勤教训你的儿女……坐、行、躺、起，都要谈论。」（申6:7）",
        "ai_used": False,
    }
    if use_ai:
        enh = _ai_enhance(text, result, settings)
        if enh:
            result.update(enh); result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return ("你是一位温柔、以福音为中心的属灵陪伴者，熟悉申6 与 Paul Tripp《为人父母》。核心：父母是神所差、暂时受托的"
            "大使(把孩子指向神，非让孩子听我)；靠福音触及心、非靠控制管行为；门训在日常缝隙(申6:7)；以身作则地悔改"
            "(让孩子看见你也蒙恩)；你忠心撒种、生长在乎神。请针对用户处境温柔陪伴，给经文、祷告与操练；"
            "不定罪父母、不给『完美父母』的重担。中文。\n"
            f"用户处境：{text}\n"
            "请输出 JSON：{\"diagnosis\":\"...\",\"way_forward\":\"...\",\"prayer\":\"一段可照着祷告的话\",\"summary\":\"...\",\"closing\":\"一句经文\"}。")


def _ai_enhance(text, base, settings):
    raw = _call_ai(build_prompt(text, base), settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        return {k: str(data[k]) for k in ("diagnosis", "way_forward", "prayer", "summary", "closing") if data.get(k)} or None
    except Exception:
        return None


def _call_ai(prompt, settings):
    for modname, fn in (("engine_ai", "call_ai"),):
        try:
            mod = __import__(modname); f = getattr(mod, fn, None)
            if f:
                out = f(prompt) if settings is None else f(prompt, settings=settings)
                if out:
                    return out if isinstance(out, str) else str(out)
        except Exception:
            continue
    return None


def formation_signal(result):
    if result.get("crisis"):
        return (["discipleship", "grace", "family"], False, True, 2.0)
    return (["discipleship", "grace", "family"], True, True, 4.0)
