"""
neighbor_love_engine.py — 爱邻舍·怜悯·公义·款待 / Love of Neighbor
（Tim Keller《慷慨的正义》Generous Justice；山上宝训的仇敌之爱；Rosaria Butterfield 款待）

系统最大的结构性盲点是「几乎全是向内的心镜诊断」。本引擎是**旗舰级的向外转**：
接住一句「我该如何爱出去 / 我在回避的一个人或需要」，把福音的重心从「我的内在」转向「我的邻舍」。

核心洞见：
  · **凯勒《慷慨的正义》**：真正经历恩典的心，必然变得慷慨。圣经的「公义(mishpat)+公义/慈惠(tzadeqah)」
    落在具体的人身上——寡妇、孤儿、寄居者、穷人。被神白白恩待的人，转过来白白善待软弱者。
  · **山上宝训**：爱不止于「爱可爱的人」——要爱仇敌、为逼迫你的祷告、走那第二里路、怜恤人。
  · **款待（Butterfield）**：最平凡的款待——开一次饭桌、接待一个陌生人——就是门徒操练。
  · 向内诊断的终点不该只是「我在基督里是谁」，还有「因此我如何转向邻舍」——爱神与爱人不可拆开。

温柔诊断「心向内蜷缩」的几种形态（自保、冷漠、比较、部落化/只爱同类），
再落成一个**具体的邻舍 + 一个具体的爱的行动**（怜悯/公义/款待/仇敌之爱）。
纯函数；确定性优先；内置危机词检测；AI 仅作可选增强。不制造愧疚驱动的行善，导向由恩典流出的爱。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# ── 心「向内蜷缩」的常见形态 → 诊断 + 向外的出路 + 经文 ──
INWARD_CURVES: List[Dict[str, Any]] = [
    {"key": "self_protect", "name": "自保 / 怕麻烦、怕被消耗，所以不伸手",
     "kw": ["怕麻烦", "自保", "多一事", "怕被消耗", "自扫门前", "不想惹", "保护自己", "算了", "太累了", "怕吃亏"],
     "diag": "你的心在自我保护里蜷缩起来——这可以理解，但福音把我们从「先顾自己」里释放出来去爱。",
     "way": "你不需要拯救世界，只需向**一个**具体的人迈**一小步**。恩典先临到你，如今可以从你流一点出去——"
            "小到一顿饭、一次探望、一句真心的问候，都是爱的操练。",
     "ref": "腓2:4", "text": "各人不要单顾自己的事，也要顾别人的事。"},
    {"key": "indifference", "name": "冷漠 / 对别人的需要无感、麻木",
     "kw": ["冷漠", "无感", "麻木", "事不关己", "无所谓", "看不见", "习惯了", "别人的事", "没感觉", "漠然"],
     "diag": "对邻舍的需要变得看不见了。好撒玛利亚人的对比是：有人「看见就动了慈心」，有人「看见就过去了」。",
     "way": "求神重开你的眼，让你「看见」身边一个真实的需要——那个总在角落的同事、那个独居的邻居、那个新来的人。"
            "看见，是爱的开始。",
     "ref": "路10:33", "text": "惟有一个撒玛利亚人……看见他就动了慈心。"},
    {"key": "compare", "name": "只顾自己的向上比较 / 忙着经营自己",
     "kw": ["比较", "忙自己", "经营", "往上爬", "只顾", "自我提升", "内卷", "顾不上别人", "拼", "焦虑前途"],
     "diag": "你的注意力被「经营自己」占满了，邻舍就被挤出了视野。向上比较让人越来越向内。",
     "way": "把一点点注意力从「向上看别人」转成「向下看需要」。这不减损你，反而把你从比较的牢笼里释放出来——"
            "服事软弱者的人，最先被医治的常是自己。",
     "ref": "太20:26-28", "text": "只是在你们中间，谁愿为大，就必作你们的用人……正如人子来，不是要受人的服事，乃是要服事人。"},
    {"key": "tribal", "name": "只爱同类 / 对「异己」冷淡甚至敌意",
     "kw": ["同类", "异己", "对立", "立场", "看不惯那种人", "仇", "敌意", "分党", "标签", "他们那种"],
     "diag": "你的爱有一条隐形的边界——只流向「我这类人」。但基督的爱恰恰越过了那条界：祂爱仇敌，为逼迫祂的祷告。",
     "way": "想一个你心里划到「界外」的人或群体，本周为他真诚祷告一次、或迈出一个善意的小动作。"
            "爱仇敌不是感觉先到，是选择先行——从为他祝福开始。",
     "ref": "太5:44", "text": "只是我告诉你们，要爱你们的仇敌，为那逼迫你们的祷告。"},
    {"key": "willing", "name": "我想爱出去 / 想服事，但不知从哪开始",
     "kw": ["想爱", "想服事", "想帮", "从哪开始", "想付出", "想款待", "想关怀", "怎么爱", "想给出去", "想祝福"],
     "diag": "这份想要爱出去的心，本身就是恩典在你里面动工——现在把它落成一个具体的人、一个具体的动作。",
     "way": "别等「有余力」才开始。选一个近处的邻舍（家人、同事、邻居、教会里边缘的人），本周做一件具体的爱的事。"
            "从最平凡的款待开始——开一次饭桌，就是门徒操练。",
     "ref": "来13:2", "text": "不可忘记用爱心接待客旅；因为曾有接待客旅的，不知不觉就接待了天使。"},
]

# ── 三种向外之爱的操练框 ──
LOVE_FORMS = [
    {"key": "mercy", "name": "怜悯", "how": "向一个正在难处中的人伸手：探望、聆听、实际的帮补。"},
    {"key": "justice", "name": "公义", "how": "为无声者发声、待人公道、关心被亏待的软弱者（寡妇、孤儿、寄居者、穷人）。"},
    {"key": "hospitality", "name": "款待", "how": "把人请到你的桌前、你的生活里——尤其是孤单的、被边缘的、陌生的人。"},
    {"key": "enemy", "name": "仇敌之爱", "how": "为一个伤过你或与你对立的人祝福、祷告，迈出一个善意的小动作。"},
]

CRISIS_WORDS = [
    "自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死", "死了算了",
    "伤害自己", "撑不下去了", "没有意义活着", "想消失",
]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = (
    "我听见你此刻自己就很不好受。爱邻舍很重要，但此刻请先让自己被爱、被照顾。如果你有伤害自己的念头，"
    "请现在就联系你信任的人或当地心理危机热线——先被接住，你不必急着去付出。（本功能不替代专业帮助。）"
)


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best: Optional[Dict[str, Any]] = None
    best_hits = 0
    for c in INWARD_CURVES:
        hits = sum(1 for k in c["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, c
    return best or INWARD_CURVES[4]  # 默认落到「想爱出去」


def _suggest_form(curve_key: str) -> Dict[str, str]:
    mapping = {
        "self_protect": "mercy", "indifference": "mercy",
        "compare": "justice", "tribal": "enemy", "willing": "hospitality",
    }
    key = mapping.get(curve_key, "mercy")
    return next(f for f in LOVE_FORMS if f["key"] == key)


def meta() -> Dict[str, Any]:
    return {
        "title": "爱邻舍 · 怜悯 · 公义 · 款待",
        "source": "Tim Keller《慷慨的正义》；山上宝训；Rosaria Butterfield 款待神学",
        "core": ("经历恩典的心必然变得慷慨；圣经的公义落在具体的软弱者身上（寡妇、孤儿、寄居者、穷人）；"
                 "爱要越过『只爱同类』的界，直到爱仇敌；最平凡的款待就是门徒操练。"),
        "love_forms": LOVE_FORMS,
        "verse": "弥6:8",
        "principle": "「世人哪，耶和华已指示你何为善。他向你所要的是什么呢？只要你行公义，好怜悯，存谦卑的心，与你的神同行。」",
        "note": "向内诊断的终点不只是『我在基督里是谁』，还有『因此我如何转向邻舍』——爱神与爱人不可拆开。",
    }


def analyze(text: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    text = (text or "").strip()
    crisis = _detect_crisis(text)
    picked = _pick(text)
    form = _suggest_form(picked["key"])

    result: Dict[str, Any] = {
        "crisis": crisis,
        "crisis_note": CRISIS_NOTE if crisis else "",
        "inward_curve": {"key": picked["key"], "name": picked["name"]},
        "diagnosis": picked["diag"],
        "way_outward": picked["way"],
        "suggested_form": form,
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "gospel_root": ("这不是愧疚驱动的行善——是恩典流出的爱。你先白白被神恩待，如今可以从这份满溢里，"
                        "白白地向软弱者、陌生人、甚至仇敌，流一点出去。"),
        "concrete_step": ("把它落到一个人、一个动作：想出**一个**具体的名字（近处的邻舍），"
                          "本周用「" + form["name"] + "」的方式，为他做**一件**具体的事——" + form["how"]),
        "prayer": ("父啊，谢谢你在我还作仇敌的时候就爱了我。饶恕我常常把心向内蜷缩，只顾自己。"
                   "求你重开我的眼，让我看见身边一个真实的邻舍；给我勇气迈出一小步去爱——"
                   "不是为了赚什么，而是因为你先如此慷慨地爱了我。愿我的爱像你的爱，越过我自设的边界。"),
        "practices": [
            "点名一个人：现在就写下一个具体的名字（那个孤单的、难处中的、或你划到界外的人）。",
            "定一个动作：本周用「" + form["name"] + "」为他做一件具体的小事（" + form["how"] + "）。",
        ],
        "summary": ("福音把心从向内蜷缩转向邻舍。不必拯救世界，只要向一个具体的人迈一小步——"
                    "行公义、好怜悯、开一次饭桌。爱神与爱人，本是一件事。"),
        "closing": "「你要尽心……爱主你的神……又要爱邻舍如同自己。」（路10:27）",
        "ai_used": False,
    }

    if use_ai:
        enhanced = _ai_enhance(text, result, settings)
        if enhanced:
            result.update(enhanced)
            result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return (
        "你是一位温柔、以福音为中心的属灵陪伴者，熟悉 Tim Keller《慷慨的正义》、山上宝训的仇敌之爱与"
        "Rosaria Butterfield 的款待神学。核心：经历恩典的心必变慷慨；公义落在具体软弱者身上；"
        "爱要越过『只爱同类』直到爱仇敌；平凡款待即门徒操练；向内诊断的终点是转向邻舍。"
        "请针对用户的处境，温柔诊断『心向内蜷缩』的形态，把它转向一个**具体的邻舍 + 一个具体的爱的行动**，"
        "给经文与祷告。中文，温暖不说教，绝不制造愧疚驱动的行善，导向由恩典流出的爱。\n"
        f"用户处境：{text}\n"
        "请输出 JSON：{\"diagnosis\":\"...\",\"concrete_step\":\"...\",\"prayer\":\"一段可照着祷告的话\","
        "\"summary\":\"...\",\"closing\":\"一句经文\"}。"
    )


def _ai_enhance(text: str, base: Dict[str, Any], settings: Any) -> Optional[Dict[str, Any]]:
    prompt = build_prompt(text, base)
    raw = _call_ai(prompt, settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        out: Dict[str, Any] = {}
        for k in ("diagnosis", "concrete_step", "prayer", "summary", "closing"):
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
    """爱邻舍属于「爱 + 顺服 + 群体」，是向外结的果子。"""
    if result.get("crisis"):
        return (["love", "obedience", "community"], False, True, 2.0)
    return (["love", "obedience", "community"], True, True, 4.5)
