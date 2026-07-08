"""
fellowship_engine.py — 团契生活 / Life Together（潘霍华 Dietrich Bonhoeffer《团契生活》）

补足系统「有 community/accountability 功能，却无团契神学底座」的空白。
与 community（匿名情绪热力）、accountability-group（小组 CRUD）互补：本引擎只做**神学诊断**——
接住一句「我和弟兄姊妹之间的挣扎」，用潘霍华《团契生活》的洞见照一面镜子。

潘霍华的核心洞见：
  1. 基督徒的团契是**神所赐的实际**，不是我们要去实现的**人的理想**。
     「爱自己所梦想的团契的人，会毁掉团契；爱身边真实弟兄的人，会建立团契。」
     ——对「理想幻灭」是恩典：幻灭破除的是我的幻想，好让我爱真实的人、真实的基督的团契。
  2. 我们**唯独借着基督、也在基督里**才彼此相通——祂是我与弟兄之间的中保。
     所以团契不建立在情投意合上，而建立在「我们同属基督」上。
  3. **独处与共处**互为前提：「不能独处的人要提防团契；不在团契中的人要提防独处。」
  4. 服事的操练：**约束舌头、谦和、聆听、帮助、担当、传扬**。
  5. **认罪与相通**：向弟兄认罪，打破罪的孤立；在恩典中彼此担当。

纯函数；确定性优先；内置危机词检测；AI 仅作可选增强。
不定罪、不贴标签，只把人从「理想的团契」领回「基督里真实的团契」。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# ── 团契中的常见挣扎 → 潘霍华的诊断 + 出路 + 经文 ──
STRUGGLES: List[Dict[str, Any]] = [
    {"key": "disillusion", "name": "对团契/教会失望、幻灭",
     "kw": ["失望", "幻灭", "理想", "不像我以为", "达不到", "假", "表面", "让我心寒", "没有爱", "虚伪"],
     "diagnosis": "你爱的，可能是你梦想中的团契；当真实的人达不到那幅画，你就受伤了。",
     "way": "潘霍华说这份幻灭其实是恩典：它拆掉的是我对团契的幻想，好让我开始爱「基督里真实的、有瑕疵的人」。"
            "团契是神已赐下的实际，不是我要靠满意度去实现的理想。停止要求它满足我的画面，开始为「它本是基督的身体」感恩。",
     "ref": "罗15:7", "text": "你们要彼此接纳，如同基督接纳你们一样，使荣耀归与神。"},
    {"key": "isolation", "name": "退缩、孤立、不想进群体",
     "kw": ["孤立", "退缩", "不想去", "独来独往", "一个人", "封闭", "躲", "不想聚会", "疏离", "宅"],
     "diagnosis": "你在把自己关起来。潘霍华警告：一个人若总是独处、不进团契，罪与谎言会在孤立里发酵。",
     "way": "「不能独处的人要提防团契；不在团契中的人要提防独处。」你需要的不是勉强的热闹，而是在基督里"
            "与至少一两位真实的弟兄姊妹相通——让光照进你独自守着的地方。",
     "ref": "传4:9-10", "text": "两个人总比一个人好……若是跌倒，这人可以扶起他的同伴。"},
    {"key": "conflict", "name": "与弟兄姊妹起冲突 / 有嫌隙",
     "kw": ["冲突", "吵", "嫌隙", "得罪", "矛盾", "不和", "看不惯", "计较", "误会", "结怨"],
     "diagnosis": "你和某位弟兄之间竖起了一道墙。潘霍华提醒：我与弟兄之间原有一位中保——基督。",
     "way": "不要越过基督直接去论断对方，也不要绕过对方在心里定他的罪。借着基督去看他：他也是主用血买赎的。"
            "先约束舌头、先聆听，再在合宜时坦诚面对——目标是挽回，不是赢。",
     "ref": "太18:15", "text": "倘若你的弟兄得罪你，你就去，趁着只有他和你在一处的时候，指出他的错来。"},
    {"key": "compare", "name": "在群体里比较、嫉妒、争谁更属灵",
     "kw": ["比较", "嫉妒", "羡慕", "谁更", "被忽略", "没人看见", "争", "排挤", "地位", "不如"],
     "diagnosis": "群体成了你衡量自己的舞台。潘霍华说：真团契里没有属灵的排名，只有同蒙恩典的罪人。",
     "way": "把「我在群体里排第几」交出来。服事的操练正是解药——约束舌头、谦和、去聆听与担当那看似比你「小」的人。"
            "在基督里，你已被悦纳，不必靠在群体中胜出来证明自己。",
     "ref": "腓2:3", "text": "凡事不可结党，不可贪图虚浮的荣耀；只要存心谦卑，各人看别人比自己强。"},
    {"key": "burden", "name": "被人的需要压得喘不过气 / 想担当却枯竭",
     "kw": ["累", "被消耗", "压得", "担不动", "付出", "枯竭", "透支", "被依赖", "背负", "喘不过气"],
     "diagnosis": "你在担当别人，却快被压垮了。潘霍华把「彼此担当」列为团契的操练，但担当的力量之源是基督，不是你。",
     "way": "彼此担当是真的，但你不是那位救主。把担子先卸给基督，再从祂那里领受力量去担当；也要学会让别人担当你——"
            "团契是双向的，不是你一个人扛。",
     "ref": "加6:2", "text": "你们各人的重担要互相担当，如此，就完全了基督的律法。"},
    {"key": "hide", "name": "在群体里戴面具、不敢真实 / 有藏着的罪",
     "kw": ["面具", "假装", "不敢说", "藏", "隐瞒", "怕被看见", "秘密", "羞耻", "装", "表演"],
     "diagnosis": "你在弟兄面前活得很用力地「体面」。潘霍华说：罪最想要的就是让你**独自**待在暗处。",
     "way": "向一位可信的弟兄认罪，会打破罪的孤立——不是为了羞辱你，而是让恩典照进那个你一直独自守着的角落。"
            "在真实里，你会第一次经历「被完全看见、仍被完全接纳」。",
     "ref": "雅5:16", "text": "所以你们要彼此认罪，互相代求，使你们可以得医治。"},
    {"key": "general", "name": "说不清的团契困扰",
     "kw": [],
     "diagnosis": "团契里的事往往难以一句话说清。",
     "way": "先回到根基：这群人之所以能相通，不是因为合得来，而是因为同属基督。从这里重新出发。",
     "ref": "约壹1:7", "text": "我们若在光明中行，如同神在光明中，就彼此相交。"},
]

# ── 服事的操练（潘霍华列举）──
MINISTRIES = ["约束舌头", "谦和", "聆听", "帮助", "担当", "传扬"]

CRISIS_WORDS = [
    "自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死", "死了算了",
    "伤害自己", "撑不下去了", "没有意义活着", "想消失",
]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = (
    "我听见你正承受很重的痛。谈团契之前，我想先温柔地说：如果你有伤害自己的念头，"
    "请现在就联系你信任的人或当地心理危机热线，也让团契里一位可信的肢体此刻真实地陪着你——你不必独自扛。"
    "（本功能不替代专业帮助。）"
)


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best: Optional[Dict[str, Any]] = None
    best_hits = 0
    for s in STRUGGLES:
        if s["key"] == "general":
            continue
        hits = sum(1 for k in s["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, s
    return best or next(s for s in STRUGGLES if s["key"] == "general")


def meta() -> Dict[str, Any]:
    return {
        "title": "团契生活",
        "source": "Dietrich Bonhoeffer《团契生活》(Life Together)",
        "pillars": [
            "团契是神所赐的实际，不是人要实现的理想——爱真实的弟兄，别爱你梦想的团契。",
            "我们唯独借着基督、在基督里彼此相通——祂是弟兄之间的中保。",
            "独处与共处互为前提——不能独处的要提防团契，不在团契中的要提防独处。",
            "服事的操练：约束舌头、谦和、聆听、帮助、担当、传扬。",
            "认罪与相通打破罪的孤立——在恩典中彼此担当。",
        ],
        "ministries": MINISTRIES,
        "verse": "诗133:1",
        "principle": "「看哪，弟兄和睦同居，是何等地善，何等地美！」——团契的美不在合得来，在同属基督。",
    }


def analyze(struggle: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    struggle = (struggle or "").strip()
    crisis = _detect_crisis(struggle)
    picked = _pick(struggle)

    result: Dict[str, Any] = {
        "crisis": crisis,
        "crisis_note": CRISIS_NOTE if crisis else "",
        "struggle": {"key": picked["key"], "name": picked["name"]},
        "diagnosis": picked["diagnosis"],
        "way_forward": picked["way"],
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "mediator_reminder": ("回到根基：这群人能彼此相通，不是因为性情相投，而是因为同属基督——"
                              "祂是你与弟兄之间的中保。透过祂去看对方，也透过祂去被对方接纳。"),
        "ministries": MINISTRIES,
        "prayer": ("主啊，谢谢你把我放进你身体里，虽然它并不完美。饶恕我常常爱我梦想的团契，过于爱你放在我身边"
                   "真实的弟兄姊妹。求你叫我借着你去看他们、去爱他们；教我约束舌头、学习聆听与担当，"
                   "也给我勇气在可信的肢体面前活得真实。愿荣耀归你。"),
        "practices": [
            "选一样服事的操练（约束舌头 / 聆听 / 担当）本周实践一次：例如去真诚聆听一位你平时忽略的肢体。",
            "为你想起的那个人具体祷告一次——为他祝福，而不是在心里给他定罪；让基督站在你和他中间。",
        ],
        "summary": ("团契的美不在「合得来」，在「同属基督」。别爱你梦想的团契，去爱身边真实的弟兄；"
                    "独处与共处一起操练，认罪与担当打破孤立。"),
        "closing": "「弟兄和睦同居，是何等地善，何等地美！」（诗133:1）",
        "ai_used": False,
    }

    if use_ai:
        enhanced = _ai_enhance(struggle, result, settings)
        if enhanced:
            result.update(enhanced)
            result["ai_used"] = True
    return result


def build_prompt(struggle: str, base: Dict[str, Any]) -> str:
    return (
        "你是一位温柔、以福音为中心的属灵陪伴者，熟悉潘霍华《团契生活》(Life Together)。核心洞见："
        "团契是神所赐的实际而非人的理想（『爱梦想的团契会毁掉团契』）；我们唯独借着基督彼此相通（祂是中保）；"
        "独处与共处互为前提；服事的操练是约束舌头、谦和、聆听、帮助、担当、传扬；认罪打破罪的孤立。"
        "请针对用户在团契中的挣扎，温柔诊断，把他从『理想的团契』领回『基督里真实的团契』，"
        "给一处经文、一段祷告、一个可行的服事操练。中文，温暖不说教，绝不定罪、不贴『你不属灵』的标签。\n"
        f"用户处境：{struggle}\n"
        "请输出 JSON：{\"diagnosis\":\"...\",\"way_forward\":\"...\",\"prayer\":\"一段可照着祷告的话\","
        "\"summary\":\"...\",\"closing\":\"一句经文\"}。"
    )


def _ai_enhance(struggle: str, base: Dict[str, Any], settings: Any) -> Optional[Dict[str, Any]]:
    prompt = build_prompt(struggle, base)
    raw = _call_ai(prompt, settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        out: Dict[str, Any] = {}
        for k in ("diagnosis", "way_forward", "prayer", "summary", "closing"):
            if data.get(k):
                out[k] = str(data[k])
        return out or None
    except Exception:
        return None


def _call_ai(prompt: str, settings: Any) -> Optional[str]:
    for modname, fn in (("engine_ai", "call_ai"),):
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
    """团契属于「群体 + 谦卑 + 爱」。"""
    if result.get("crisis"):
        return (["community", "humility", "love"], False, True, 2.0)
    return (["community", "humility", "love"], True, True, 4.0)
