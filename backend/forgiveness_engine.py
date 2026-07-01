"""
forgiveness_engine.py — 饶恕与和好 / Forgiveness & Reconciliation
（Miroslav Volf《白白的恩典》Free of Charge /《拥抱神学》Exclusion and Embrace；
 Everett Worthington「REACH」饶恕模型）

补足 crisis / suffering 之后一直缺的一味：**当我被人伤害，如何饶恕**。

核心分辨（安全关键）：
  · **饶恕 ≠ 淡化伤害**：饶恕先要「如实承认这是真的错、真的痛」，而不是假装没事。
  · **饶恕 ≠ 和好**：饶恕是**单方**的、我可以在神面前先做的（松开以牙还牙的权利）；
    和好是**双方**的，需要对方的悔改与改变，且**绝不以重回受害/危险的处境为代价**。
  · **饶恕 ≠ 忘记 / 纵容 / 立刻恢复信任**：界限、公义、保护自己与他人，与饶恕并行不悖。

福音根基：我们能白白饶恕，因为我们已白白被神饶恕（弗4:32；西3:13）。饶恕是「把加害者交给神」，
不是「假装伤害不存在」。Worthington 的 REACH 五步：回想伤害(Recall)→同理(Empathize)→
利他的礼物(Altruistic gift)→立志饶恕(Commit)→持守饶恕(Hold on)。

纯函数；确定性优先；内置危机词检测 + 施虐/危险处境检测（命中则不推动和好，转向保护与求助）；
AI 仅作可选增强。不定罪、不催逼、不把饶恕简化成「你必须马上放下」。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# ── REACH 五步（Worthington）──
REACH: List[Dict[str, str]] = [
    {"key": "recall", "name": "如实承认（Recall）",
     "desc": "不淡化、不夸大，在神面前如实说出发生了什么、伤在哪里。饶恕从「承认这是真的错」开始，而非否认。",
     "prompt": "具体写下：他做了什么，这让你失去了什么、痛在哪里。允许自己诚实。",
     "ref": "诗62:8", "text": "你们众民当时时倚靠他，在他面前倾心吐意。"},
    {"key": "empathize", "name": "尝试同理（Empathize）",
     "desc": "不是为对方开脱，而是试着理解他的处境与破碎——这松开的是「我要牢牢抓住这份恨」的手。做不到也没关系。",
     "prompt": "若做得到，试着想：是什么样的伤或惧，让一个人会这样待人？（若太难，可跳过，交给神。）",
     "ref": "路23:34", "text": "父啊，赦免他们！因为他们所做的，他们不晓得。"},
    {"key": "altruistic", "name": "白白的礼物（Altruistic gift）",
     "desc": "回想自己也曾被神白白赦免。饶恕是把「我本可紧抓的报复权」当作礼物松开——不是对方赚得的，是恩典。",
     "prompt": "回想一次你被神（或被人）白白赦免的经历，让那份被赦免的记忆软化你的心。",
     "ref": "弗4:32", "text": "并要以恩慈相待，存怜悯的心，彼此饶恕，正如神在基督里饶恕了你们一样。"},
    {"key": "commit", "name": "立志饶恕（Commit）",
     "desc": "饶恕是一个在神面前立下的**决定**，先于感觉。感觉会反复，但决定可以先立下、可以重申。",
     "prompt": "对神说出一句立志的话：「我选择松开向他讨债的权利，把他交在你手里。」",
     "ref": "罗12:19", "text": "不要自己伸冤……主说：伸冤在我，我必报应。"},
    {"key": "hold", "name": "持守饶恕（Hold on）",
     "desc": "记忆和怒气会回潮——那不代表饶恕失败。每次回潮，就重申一次那个决定，把它再交托一次。",
     "prompt": "为「怒气回潮时怎么办」定一句话：当我又想起，我就再说一次「我已经把他交给神了」。",
     "ref": "太18:21-22", "text": "不是到七次，乃是到七十个七次。"},
]

# ── 伤害类型 → 温柔的分辨提示 ──
HURT_TYPES: List[Dict[str, Any]] = [
    {"key": "betrayal", "name": "背叛 / 被出卖",
     "kw": ["背叛", "出卖", "欺骗", "劈腿", "谎", "捅刀", "利用", "被骗"],
     "note": "背叛之所以格外痛，是因为它伤在信任上。饶恕不等于立刻恢复信任——信任是需要时间与对方改变来重建的。"},
    {"key": "injustice", "name": "不公 / 被亏待",
     "kw": ["不公", "冤枉", "亏待", "占便宜", "剥削", "抢", "偷", "赖账", "陷害"],
     "note": "你对公义的渴望是对的，神比你更恨这不公。饶恕不是说「算了这没关系」，而是把伸冤的权柄交回给神。"},
    {"key": "words", "name": "言语 / 羞辱 / 论断",
     "kw": ["羞辱", "骂", "中伤", "造谣", "说闲话", "论断", "贬低", "嘲笑", "冷言"],
     "note": "话语的伤会在心里反复回放。饶恕的一部分，是不再让那句话当你的法官——神对你的评价，才是真的。"},
    {"key": "family", "name": "至亲 / 父母 / 家人的伤",
     "kw": ["父母", "家人", "爸", "妈", "原生家庭", "亲人", "手足", "兄弟", "姐妹"],
     "note": "至亲的伤最深，也最复杂。饶恕父母不等于假装童年没有伤，而是不再让那伤定义你的一生——可以饶恕，也可以设界限。"},
    {"key": "abandon", "name": "被离弃 / 被抛下",
     "kw": ["抛弃", "离弃", "抛下", "不要我", "丢下", "遗弃", "消失", "不管"],
     "note": "被离弃会让人以为「我不值得被留下」。那是谎言。神说祂总不撇下你——你的价值不由离开你的人决定。"},
    {"key": "general", "name": "说不清的伤",
     "kw": [],
     "note": "有些伤说不清、也未必有明确的加害者。你不必先把它讲清楚才能开始——可以先把它照实端到神面前。"},
]

# ── 施虐/持续危险处境：命中则**不推动和好**，转向保护与求助 ──
ABUSE_WORDS = [
    "家暴", "殴打", "打我", "施暴", "性侵", "猥亵", "虐待", "威胁", "跟踪", "控制我",
    "不让我", "恐吓", "动手", "被打", "拳", "掐", "强迫我", "危险",
]


def _detect_abuse(text: str) -> bool:
    t = (text or "")
    return any(w in t for w in ABUSE_WORDS)


ABUSE_NOTE = (
    "我听见你所描述的，可能是**持续的伤害或危险**。这里要非常清楚地说：**饶恕从来不等于回到会继续伤害你的处境里，"
    "也不等于你必须与加害者和好、或忍受下去。**你的安全是要紧的、也是神所看重的。请优先联系你信任的人、"
    "当地的保护/求助资源或专业人士。你可以在神面前慢慢走饶恕这条内在的路，同时坚定地设立界限、寻求保护——两者并不冲突。"
)

CRISIS_WORDS = [
    "自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死", "死了算了",
    "伤害自己", "撑不下去了", "没有意义活着", "想消失",
]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = (
    "我听见你正承受很重的痛。谈饶恕之前，我想先温柔地说：如果你有伤害自己的念头，"
    "请现在就联系你信任的人或当地心理危机热线——你不必独自扛这份痛。（本功能不替代专业帮助。）"
)


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best: Optional[Dict[str, Any]] = None
    best_hits = 0
    for h in HURT_TYPES:
        if h["key"] == "general":
            continue
        hits = sum(1 for k in h["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, h
    return best or next(h for h in HURT_TYPES if h["key"] == "general")


def meta() -> Dict[str, Any]:
    return {
        "title": "饶恕与和好",
        "source": "Miroslav Volf《白白的恩典》；Everett Worthington「REACH」模型",
        "distinctions": [
            "饶恕 ≠ 淡化伤害——先如实承认这是真的错、真的痛。",
            "饶恕 ≠ 和好——饶恕是单方的，和好需要双方与对方的改变。",
            "饶恕 ≠ 忘记 / 纵容 / 立刻恢复信任——界限与公义可以并行。",
            "饶恕 ≠ 回到会继续伤害你的处境——你的安全是神所看重的。",
        ],
        "reach": REACH,
        "gospel": "我们能白白饶恕，因为已白白被神饶恕（弗4:32）。",
        "verse": "西3:13",
        "principle": "「倘若这人与那人有嫌隙，总要彼此包容，彼此饶恕；主怎样饶恕了你们，你们也要怎样饶恕人。」",
    }


def analyze(hurt: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    hurt = (hurt or "").strip()
    crisis = _detect_crisis(hurt)
    abuse = _detect_abuse(hurt)
    picked = _pick(hurt)

    diagnosis = (
        "你所承受的，属于「" + picked["name"] + "」这一类的伤。" + picked["note"]
        + " 在开始饶恕之前，请先听清楚：饶恕不是说这伤「没关系」，而是选择不再自己讨债，"
        "把那份公义交回给比你更恨这不公的神。"
    )
    result: Dict[str, Any] = {
        "crisis": crisis,
        "crisis_note": CRISIS_NOTE if crisis else "",
        "abuse_flag": abuse,
        "abuse_note": ABUSE_NOTE if abuse else "",
        "hurt_type": {"key": picked["key"], "name": picked["name"], "note": picked["note"]},
        "diagnosis": diagnosis,
        "distinction": ("提醒你分清两件事：**饶恕**是你可以在神面前先走的单方之路（松开报复权）；"
                        "**和好**是另一回事，需要对方真实的悔改与改变——"
                        + ("在你所描述的处境里，请把安全放在第一位，先不谈和好。" if abuse
                           else "你可以先饶恕，同时把是否、何时和好交给时间与智慧。")),
        "reach_steps": REACH,
        "anchor": {"ref": "弗4:32", "text": "并要以恩慈相待，存怜悯的心，彼此饶恕，正如神在基督里饶恕了你们一样。"},
        "prayer": ("主啊，你知道我受的伤有多真、多痛。我承认我里面有想讨回公道的怒。今天我不假装没事，"
                   "但我愿意学着松开我紧抓的报复权，把这个人和这件事交在你手里——伸冤在你。"
                   "求你医治我，也照你的公义与怜悯处理这一切；在你认为合适之前，请保守我有智慧设立该有的界限。"),
        "practices": [
            "走一遍 REACH：照着上面五步，一步一步在神面前把这份伤谱成祷告，不必一次走完。",
            "把决定与感觉分开：今天先立下「我选择饶恕」这个决定；等怒气回潮时，再重申一次，而不推翻它。",
        ],
        "summary": ("饶恕不是一次性把伤抹掉，而是一个可以反复重申的决定：把讨债权交给神，让自己从苦毒里被释放。"
                    "它与设立界限、寻求公义并不冲突。"),
        "closing": "「主怎样饶恕了你们，你们也要怎样饶恕人。」（西3:13）",
        "ai_used": False,
    }
    if abuse:
        # 危险处境：把「持守饶恕/和好」的语气整体降到「安全优先」，practices 换成保护导向
        result["practices"] = [
            "把安全放第一：联系你信任的人、当地保护/求助资源或专业人士，先让自己处在安全里。",
            "分清两条路：你可以在神面前慢慢走内在饶恕的路，同时坚定设立界限、不回到受伤的处境——两者不冲突。",
        ]

    if use_ai:
        enhanced = _ai_enhance(hurt, result, settings)
        if enhanced:
            result.update(enhanced)
            result["ai_used"] = True
    return result


def build_prompt(hurt: str, base: Dict[str, Any]) -> str:
    return (
        "你是一位温柔、以福音为中心、且有创伤敏感度的属灵陪伴者，熟悉 Miroslav Volf 的饶恕神学与"
        "Worthington 的 REACH 模型。铁律：(1) 饶恕先要如实承认伤害，不淡化；(2) 饶恕是单方的，"
        "和好是双方的、需要对方改变；(3) 绝不催逼受害者回到会继续被伤害的处境，安全优先；"
        "(4) 界限、公义与饶恕并行不悖。请针对用户被伤害的处境，温柔分辨伤害类型，区分饶恕与和好，"
        "给一段可祷告的话与一个不催逼的下一步。中文，温暖不说教，绝不说『你必须马上放下』『你不饶恕就是你的问题』。\n"
        f"用户处境：{hurt}\n"
        "请输出 JSON：{\"diagnosis\":\"...\",\"distinction\":\"...\",\"prayer\":\"一段可照着祷告的话\","
        "\"summary\":\"...\",\"closing\":\"一句经文\"}。"
    )


def _ai_enhance(hurt: str, base: Dict[str, Any], settings: Any) -> Optional[Dict[str, Any]]:
    prompt = build_prompt(hurt, base)
    raw = _call_ai(prompt, settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        out: Dict[str, Any] = {}
        for k in ("diagnosis", "distinction", "prayer", "summary", "closing"):
            if data.get(k):
                out[k] = str(data[k])
        return out or None
    except Exception:
        return None


def _call_ai(prompt: str, settings: Any) -> Optional[str]:
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
    """饶恕属于「关系 + 恩典 + 释放」。危险/危机处境降权并标记需真人介入。"""
    if result.get("crisis") or result.get("abuse_flag"):
        return (["relationship", "grace", "release"], False, True, 2.0)
    return (["relationship", "grace", "release"], True, True, 4.5)
