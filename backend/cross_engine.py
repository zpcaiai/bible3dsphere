"""
cross_engine.py — 十字架默想 / The Cross of Christ（斯托得《当代基督十架》）

系统的 gospel 是「诊断」、cross_lament 是「哀歌」；本引擎补一件不同的事——**仰望**：
默想十字架**客观成就了什么**，把目光从「我的问题」抬到「基督的成就」。

十架的客观成就（斯托得）：
  · **代替（substitution）**：祂站在我的位置，担我的罪（赛53:6；彼前2:24）。
  · **挽回（propitiation）**：祂的血除去神对罪的忿怒，使神向我为可亲（罗3:25；约壹4:10）。
  · **救赎（redemption）**：祂的血把我从罪的奴役里买赎回来（弗1:7）。
  · **和好（reconciliation）**：本为仇敌的，因祂的死与神和好、得着平安（西1:20-22）。
  · **大交换（the great exchange）**：祂成为罪，使我在祂里面成为神的义（林后5:21）。
  · **得胜（triumph）**：祂在十架上胜过一切执政掌权的（西2:15）。

纯函数；确定性优先；内置危机词检测；AI 仅作可选增强。不做诊断、不加重担，
只把人领到十架下仰望那已经成了的救恩。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

ACHIEVEMENTS: List[Dict[str, Any]] = [
    {"key": "guilt", "name": "罪咎压着我 / 觉得自己该被罚",
     "kw": ["罪咎", "该罚", "内疚", "罪恶感", "亏欠", "良心不安", "背着罪", "自责", "犯了罪"],
     "achievement": "代替", "en": "Substitution",
     "truth": "十架上，祂站在你的位置，把你该受的都担了。你的罪不是没人管，而是已经被钉在祂身上——"
              "神不会向同一笔债追讨两次。你可以放下那压着你的罪咎，因它已经被祂担尽。",
     "ref": "赛53:6", "text": "耶和华使我们众人的罪孽都归在他身上。"},
    {"key": "wrath", "name": "觉得神在生我的气 / 怕神的忿怒",
     "kw": ["生气", "忿怒", "神在气", "怕神罚", "神不喜悦", "得罪神", "神的愤怒", "怕报应"],
     "achievement": "挽回", "en": "Propitiation",
     "truth": "十架上，基督的血已经除去神对你罪的忿怒——这叫「挽回祭」。如今神向你不再是审判的怒容，"
              "而是父的笑脸。不是你平息了神的怒，是神自己出于爱，差子作了挽回祭。",
     "ref": "约壹4:10", "text": "不是我们爱神，乃是神爱我们，差他的儿子为我们的罪作了挽回祭。"},
    {"key": "bondage", "name": "被罪捆住出不来 / 像奴隶",
     "kw": ["捆", "戒不掉", "奴隶", "上瘾", "辖制", "出不来", "被罪抓住", "重复犯", "自由不了"],
     "achievement": "救赎", "en": "Redemption",
     "truth": "十架是一笔赎价：祂用自己的血，把你从罪的奴役市场买赎回来。你已经换了主人——"
              "罪不再是你的主。争战仍在，但你是「已被赎的自由人在争战」，不是「奴隶在绝望」。",
     "ref": "弗1:7", "text": "我们藉这爱子的血得蒙救赎，过犯得以赦免。"},
    {"key": "estranged", "name": "觉得和神疏远 / 关系破裂",
     "kw": ["疏远", "破裂", "隔绝", "和神生分", "回不去", "断了", "远离神", "关系冷", "不配到神面前"],
     "achievement": "和好", "en": "Reconciliation",
     "truth": "你本与神为敌，但基督藉十架的死，叫你与神和好、得着平安。那道横在中间的墙，祂已经拆了。"
              "你不必想办法「修复」与神的关系——祂已经在十架上修复好了，你只管回来。",
     "ref": "西1:21-22", "text": "你们从前……如今他藉着基督的肉身受死，叫你们与自己和好。"},
    {"key": "unrighteous", "name": "觉得自己永远不够义 / 站不住",
     "kw": ["不够义", "不配", "站不住", "永远不够", "达不到", "不圣洁", "污秽", "配不上神"],
     "achievement": "大交换", "en": "The Great Exchange",
     "truth": "十架上有一场大交换：祂成为罪（担你的不义），使你在祂里面成为神的义。神看你，看的是基督的义，"
              "不是你的成绩单。你站在神面前的凭据，是祂的义，稳如磐石。",
     "ref": "林后5:21", "text": "神使那无罪的，替我们成为罪，好叫我们在他里面成为神的义。"},
    {"key": "marvel", "name": "想更深地仰望十架 / 被十架的爱触动",
     "kw": ["仰望", "十架", "默想", "被爱", "感恩", "敬拜", "看见基督", "更深", "触动", "宝血"],
     "achievement": "得胜与爱", "en": "Triumph & Love",
     "truth": "十架既是最惨痛的、也是最荣耀的：在那里，神的爱与公义相遇，基督胜过了一切黑暗的权势。"
              "当你无从下手，就来仰望——不是分析，是敬拜；让「祂为我舍己」重新点燃你的心。",
     "ref": "加2:20", "text": "他是爱我，为我舍己。"},
]

CRISIS_WORDS = ["自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死",
                "死了算了", "伤害自己", "撑不下去了", "没有意义活着", "想消失"]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = ("我听见你正承受很重的痛。如果你有伤害自己的念头，请现在就联系你信任的人或当地心理危机热线。"
               "十字架上那位爱你、为你舍己的主此刻与你同在——你不必独自扛。（本功能不替代专业帮助。）")


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best, best_hits = None, 0
    for d in ACHIEVEMENTS:
        hits = sum(1 for k in d["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, d
    return best or ACHIEVEMENTS[5]


def meta() -> Dict[str, Any]:
    return {
        "title": "十字架默想",
        "source": "斯托得《当代基督十架》(The Cross of Christ)",
        "core": "默想十架客观成就了什么——代替、挽回、救赎、和好、大交换、得胜，把目光从我的问题抬到基督的成就。",
        "achievements": [{"key": d["key"], "name": d["name"], "en": d["en"]} for d in ACHIEVEMENTS],
        "verse": "林前2:2",
        "principle": "「因为我曾定了主意，在你们中间不知道别的，只知道耶稣基督并他钉十字架。」",
    }


def analyze(text: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    text = (text or "").strip()
    crisis = _detect_crisis(text)
    picked = _pick(text)
    result: Dict[str, Any] = {
        "crisis": crisis, "crisis_note": CRISIS_NOTE if crisis else "",
        "focus": {"key": picked["key"], "name": picked["name"]},
        "achievement": {"name": picked["achievement"], "en": picked["en"]},
        "truth": picked["truth"],
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "prayer": ("主耶稣，我来到你的十架下。谢谢你——在那里你替我担罪、除去神的忿怒、把我从罪里赎回、"
                   "叫我与神和好，还把你的义赐给了我。当我盯着自己的问题看到发慌，求你让我抬起头，"
                   "仰望你已经成了的救恩。你是爱我、为我舍己——这一件，够我信靠一生。"),
        "practices": [
            "仰望而非分析：安静读一遍锚点经文（" + picked["ref"] + "），把它当作神此刻对你说的话，只是敬拜。",
            "把重担钉上十架：具体说出你正扛着的那件事，宣告「这已经成了——" + picked["achievement"] + "」，把它交在十架下。",
        ],
        "summary": ("十架不是让你更内疚，而是让你抬头仰望：基督已经代替、挽回、救赎、和好、成就大交换、得了胜。"
                    "把目光从你的问题，转到祂的成就。"),
        "closing": "「成了！」（约19:30）",
        "ai_used": False,
    }
    if use_ai:
        enh = _ai_enhance(text, result, settings)
        if enh:
            result.update(enh); result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return ("你是一位温柔、以福音为中心的属灵陪伴者，熟悉斯托得《当代基督十架》。核心：默想十架的客观成就——"
            "代替/挽回(propitiation)/救赎/和好/大交换(林后5:21)/得胜——把目光从『我的问题』抬到『基督的成就』；"
            "这是仰望与敬拜，不是诊断或加重担。请针对用户处境，对上一项十架成就，给经文、祷告与一个『仰望十架』的操练。中文，温暖不说教。\n"
            f"用户处境：{text}\n"
            "请输出 JSON：{\"truth\":\"...\",\"prayer\":\"一段可照着祷告的话\",\"summary\":\"...\",\"closing\":\"一句经文\"}。")


def _ai_enhance(text, base, settings):
    raw = _call_ai(build_prompt(text, base), settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        return {k: str(data[k]) for k in ("truth", "prayer", "summary", "closing") if data.get(k)} or None
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
        return (["gospel", "cross", "worship"], False, True, 2.0)
    return (["gospel", "cross", "worship"], True, True, 4.0)
