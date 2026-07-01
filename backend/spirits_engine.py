"""
spirits_engine.py — 依纳爵·诸灵分辨（安慰 / 枯竭）/ Ignatian Discernment of Spirits
（Ignatius of Loyola,《神操》「分辨诸灵的规则」）

补足「情感层面的属灵分辨」——不是「该不该做这个决定」（那是 `discernment_engine` / decision
所做的**理性/意志层面**分辨），而是分辨心里那股**内在运动**：它是把我朝向神（安慰），
还是拉离神（枯竭）？

依纳爵的核心洞见：不要在枯竭中更改先前在安慰中所立的方向；在枯竭中要「逆势而行」（agere
contra）。并且要分辨：这份低落到底是「枯竭，要坚立」，还是「因具体的罪而来的、归回的呼召」。

纯函数；确定性优先；内置危机词检测；AI 仅作可选增强，失败回退确定性结果。
不定罪、不贴标签，只帮助人认出神在心里的运动，谦卑忍耐，转向信靠。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# ── 安慰的记号（灵里朝向神的运动） ──
CONSOLATION_MARKS: List[str] = [
    "信、望、爱在心里增长",
    "内在的平安与安稳",
    "被吸引亲近神、渴慕祷告",
    "眼泪使人更爱神、更多痛悔归向祂",
    "渴慕属天、永恒之事，看轻眼前的诱惑",
    "喜乐、感恩，心被神的美善点燃",
]

# ── 枯竭的记号（朝离神的运动） ──
DESOLATION_MARKS: List[str] = [
    "黑暗、纷扰、心神不宁",
    "懒惰、冷淡、提不起劲祷告",
    "被拉向低下、属世、诱惑之物",
    "与神隔绝、被神遗弃的感觉",
    "失去盼望、信心、爱，觉得神很远",
    "忧闷、自我封闭，想放弃属灵操练",
]

# ── 分辨诸灵的规则（编码约 5 条，依纳爵《神操》） ──
RULES: List[Dict[str, str]] = [
    {"key": "rule1_no_change",
     "name": "在枯竭中，绝不更改先前的方向",
     "desc": "在枯竭时，绝不更改先前在安慰中所立的方向或决定。因为那时引导我们的，不是良善之灵，"
             "而是恶者。要持守在光明中所领受的。"},
    {"key": "rule2_agere_contra",
     "name": "逆势而行（agere contra）",
     "desc": "枯竭中不要退缩，反要逆势而行——加倍祷告、默想、省察、并加上适度的克己。恰恰在最不想的时候，"
             "更要坚持属灵的操练。"},
    {"key": "rule3_it_returns",
     "name": "安慰必再来，枯竭是暂时的",
     "desc": "要记得：安慰必再来，枯竭是暂时的，神的恩典始终未曾离开。这份低落不会是你故事的结局。"},
    {"key": "rule4_store_up",
     "name": "在安慰中要谦卑，为枯竭之日积蓄力量",
     "desc": "在安慰中的人，要存谦卑，思想枯竭来临时自己何等软弱；趁着光明，为将来黑暗的日子积蓄力量与决心。"},
    {"key": "rule5_causes",
     "name": "枯竭的三种缘由——都要谦卑忍耐",
     "desc": "枯竭可能是操练、是试验，或因我们松懈懒散所致——无论哪一种，都要谦卑、忍耐、忠心，"
             "在其中不下任何属灵的判断或大决定。"},
]

KEY_QUESTION = "这份低落是『枯竭，要坚立（stay, resist）』，还是『归回的呼召（a call to return）』？"

# ── 关键词：判断描述偏向安慰或枯竭 ──
CONSOLATION_KW: List[str] = [
    "平安", "喜乐", "感恩", "被爱", "亲近神", "渴慕", "盼望", "信心增长", "热心", "感动",
    "光明", "自由", "释放", "温暖", "被吸引", "眼泪", "更爱神", "安稳", "满足", "被神",
]
DESOLATION_KW: List[str] = [
    "黑暗", "纷扰", "不安", "冷淡", "懒", "提不起", "隔绝", "遗弃", "遥远", "神很远",
    "绝望", "失去盼望", "失去信心", "枯干", "枯竭", "低落", "沉重", "空虚", "封闭", "退缩",
    "灰心", "忧闷", "无力", "想放弃", "不想祷告", "冷漠", "麻木",
]

# ── 具体的罪 / 过犯（用于区分「归回的呼召」而非无缘由的枯竭） ──
SIN_KW: List[str] = [
    "犯罪", "犯了罪", "得罪", "撒谎", "说谎", "欺骗", "偷", "贪", "情欲", "色情", "淫",
    "苦毒", "恨", "嫉妒", "骄傲", "自私", "发怒", "伤害了", "背叛", "出卖", "报复",
    "亏欠", "对不起", "做错", "做了错事", "认罪", "羞愧于我做的", "沉迷", "上瘾",
    "论断", "毁谤", "闲话", "懒惰放纵", "放纵",
]

CRISIS_WORDS = [
    "自杀", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死", "死了算了",
    "伤害自己", "撑不下去了", "没有意义活着", "想消失",
]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = (
    "我听见你正承受很重的痛。在我们一起向神倾诉之前，我想先温柔地说：如果你有伤害自己的念头，"
    "请现在就联系你信任的人，或当地的心理危机热线——你值得有人此刻真实地陪着你。神爱你，"
    "你不必独自扛。（本功能不替代专业帮助。）"
)


def _score(text: str, kws: List[str]) -> int:
    t = text or ""
    return sum(1 for k in kws if k in t)


def _names_specific_sin(text: str) -> bool:
    """确定性：文本是否点名了一项具体的罪 / 过犯（→ 归回的呼召）。"""
    return _score(text, SIN_KW) > 0


def meta() -> Dict[str, Any]:
    """安慰/枯竭的记号、分辨规则、关键提问（供前端展示）。"""
    return {
        "consolation_marks": list(CONSOLATION_MARKS),
        "desolation_marks": list(DESOLATION_MARKS),
        "rules": RULES,
        "key_question": KEY_QUESTION,
        "principle": "分辨诸灵，不是分辨『该做什么』，而是分辨心里那股运动把你朝向神，还是拉离神；"
                     "在枯竭中要坚立、逆势而行，绝不在黑暗里更改光明中所立的方向。",
    }


def discern(text: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    """分辨内在运动是安慰还是枯竭；若枯竭，应用规则并区分『坚立』与『归回』（确定性；可选 AI 增强）。"""
    text = (text or "").strip()
    crisis = _detect_crisis(text)

    cons = _score(text, CONSOLATION_KW)
    deso = _score(text, DESOLATION_KW)
    # 判定：并列或都为 0 时，默认按「枯竭」牧养（人多在低落时才来求分辨）
    state = "consolation" if cons > deso else "desolation"

    if state == "consolation":
        movement = "安慰（consolation）"
        reading = (
            "你所描述的，带着朝向神的记号——信、望、爱在增长，心被吸引亲近祂。这是安慰，"
            "是良善之灵的工作。领受它，也别忘了依纳爵的提醒：在安慰中要存谦卑，为将来枯竭的日子积蓄力量。"
        )
        applied_rules = [RULES[3]]  # rule4：在安慰中谦卑、积蓄力量
        counsel = "现在正是把心更深交托、把方向立定的时候——趁着光明，记下神的良善与祂给你的确据。"
        practice = (
            "1）安静领受这份安慰，向神说出你的感恩；"
            "2）写下此刻你对神、对你所走方向最清楚的一句确据，留作枯竭之日的锚；"
            "3）为一件具体的事，趁着心被点燃，向神立定一个小小的、忠心的决定。"
        )
        verse = {"ref": "诗16:11", "text": "你必将生命的道路指示我。在你面前有满足的喜乐；在你右手中有永远的福乐。"}
        resolution = "stay_and_receive"
    else:
        movement = "枯竭（desolation）"
        if _names_specific_sin(text):
            # 因具体的罪而来的责备感 → 温柔归回、认罪
            branch = "return"
            reading = (
                "你所描述的低落里，似乎连着一件具体的事——一处你知道自己偏离了神的地方。"
                "这未必只是『枯竭』，更像是神温柔的责备，是『归回的呼召』。这不是要压垮你，"
                "而是要领你回家。"
            )
            applied_rules = [RULES[4]]  # rule5：谦卑、忍耐、不下大决定；此处是认罪归回
            counsel = (
                "不需要更改先前的方向，只需要归回：在神面前诚实说出那件事，认罪，接受祂在基督里"
                "早已预备好的赦免，然后重新站起来往前走。这份责备的目的是恢复，不是定罪。"
            )
            practice = (
                "1）具体地、诚实地在神面前说出那件你知道偏离了的事，不遮掩；"
                "2）领受赦免——「我们若认自己的罪，神是信实的、公义的，必要赦免我们的罪」（约壹1:9）；"
                "3）走一小步实际的归回（一句道歉、一个转身、一个了结），把心重新对准神。"
            )
            verse = {"ref": "诗43:5", "text": "我的心哪，你为何忧闷？为何在我里面烦躁？应当仰望神，因我还要称赞祂。祂是我脸上的光荣，是我的神。"}
            resolution = "return_and_confess"
        else:
            # 无缘由的枯竭 → 坚立、忍耐、逆势而行
            branch = "stay"
            reading = (
                "你所描述的，是朝离神的运动——黑暗、纷扰、觉得神遥远。但请听依纳爵最重要的一句话："
                "这是枯竭，不是真相。它不是在告诉你神离开了，它是暂时的黑夜。"
            )
            applied_rules = [RULES[0], RULES[1], RULES[2]]  # rule1 不改决定 + rule2 逆势而行 + rule3 必再来
            counsel = (
                "此刻最重要的一件事：现在别改任何决定。绝不在枯竭中更改你先前在安慰、在光明里所立的方向。"
                "然后逆势而行——恰恰在最不想祷告的时候，多祷告一点；并要记得：安慰必再来，恩典仍在。"
            )
            practice = (
                "1）先决定：现在不更改任何先前立定的方向或决定（rule 1）；"
                "2）逆势而行——比平常多花一点时间祷告、默想、省察，加上一点小小的克己（rule 2）；"
                "3）对自己说出并写下：这是枯竭，是暂时的，安慰必再来，神此刻仍与我同在（rule 3）。"
            )
            verse = {"ref": "诗42:5-6", "text": "我的心哪，你为何忧闷？为何在我里面烦躁？应当仰望神，因祂笑脸帮助我；我还要称赞祂。我的神啊，我的心在我里面忧闷，所以我从约旦地……记念你。"}
            resolution = "stay_and_resist"

    if state == "consolation":
        summary_line = "在安慰中：谦卑领受，为枯竭之日积蓄力量。"
        branch_val = "consolation"
    elif branch == "return":
        summary_line = "这是归回的呼召：温柔地认罪、领受赦免、重新站起来。"
        branch_val = "return"
    else:
        summary_line = "这是枯竭，要坚立：现在别改决定，逆势而行，安慰必再来。"
        branch_val = "stay"

    result: Dict[str, Any] = {
        "crisis": crisis,
        "crisis_note": CRISIS_NOTE if crisis else "",
        "state": state,
        "movement": movement,
        "branch": branch_val,
        "reading": reading,
        "key_question": KEY_QUESTION,
        "applied_rules": applied_rules,
        "counsel": counsel,
        "practice": practice,
        "scripture": verse,
        "resolution": resolution,
        "summary": summary_line,
        "ai_used": False,
    }
    if crisis:
        result["reading"] = CRISIS_NOTE + "\n\n" + result["reading"]

    if use_ai:
        enhanced = _ai_enhance(text, result, settings)
        if enhanced:
            result.update(enhanced)
            result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return (
        "你是一位温柔、以福音为中心的属灵陪伴者，熟悉依纳爵《神操》中『分辨诸灵的规则』"
        "（安慰 consolation / 枯竭 desolation）。请帮助用户分辨他所描述的内在运动是把他朝向神（安慰）"
        "还是拉离神（枯竭），中文，温暖不说教，不定罪、不贴标签、不说『你信心不够』之类的话。\n"
        "关键分辨：若是枯竭，务必提醒『现在别更改先前在安慰中所立的方向』（规则一），并鼓励『逆势而行』"
        "（规则二，加倍祷告默想省察克己）；并区分——若低落连着一件具体的罪，是『归回的呼召』（温柔认罪归回）；"
        "若无具体缘由，则是『枯竭，要坚立忍耐』。\n"
        f"当前确定性判断：{base.get('movement')}，方向：{base.get('resolution')}。\n"
        f"用户倾诉：{text}\n"
        "请输出 JSON：{\"reading\":\"对这股运动的分辨（2-4句）\",\"counsel\":\"核心劝勉\","
        "\"practice\":\"1) 2) 3) 三个可操作的属灵练习\",\"summary\":\"一句收束\"}。"
    )


def _ai_enhance(text: str, base: Dict[str, Any], settings: Any) -> Optional[Dict[str, Any]]:
    """可选 AI 增强：任何失败都回退（返回 None）。"""
    prompt = build_prompt(text, base)
    raw = _call_ai(prompt, settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        out: Dict[str, Any] = {}
        for k in ("reading", "counsel", "practice", "summary"):
            if data.get(k):
                out[k] = str(data[k])
        return out or None
    except Exception:
        return None


def _call_ai(prompt: str, settings: Any) -> Optional[str]:
    """尽力调用既有 provider；不可用则返回 None（引擎保持零硬依赖）。"""
    for modname, fn in (("waiting_engine", "call_ai_provider"), ("llm_provider", "call_llm")):
        try:
            mod = __import__(modname)
            f = getattr(mod, fn, None)
            if f:
                out = f(prompt) if settings is None else f(prompt, settings=settings)
                if out:
                    return out if isinstance(out, str) else str(out)
        except Exception:
            continue
    return None


def formation_signal(result: Dict[str, Any]):
    """回流 formation：诸灵分辨属于「认出运动、坚立或归回」，标注情绪/成长维度。"""
    if result.get("crisis"):
        return (["fear", "growth"], False, True, 2.0)
    if result.get("state") == "consolation":
        return (["hope", "growth"], True, True, 4.0)
    # 枯竭：坚立/归回都是成长中的操练
    return (["fear", "growth"], True, True, 5.0)
