"""
providence_engine.py — 神的护理 / 信靠主权的手（傅拉维《护理的奥秘》The Mystery of Providence；
Jerry Bridges《信靠神》Trusting God）

补「在琐碎与痛苦里读出慈父的手」这条线。与 suffering/waiting/contentment 互补：
它们处理受苦/等候/知足的心态，本引擎专讲**神的护理**——神在万事上智慧、良善、有主权地掌管，
甚至叫万事（包括难处）互相效力，叫爱神的人得益处（罗8:28）。

傅拉维/Bridges 的三根支柱（信靠神须同时相信）：
  · 神**全权**（sovereign）——祂掌管万事，没有一件事在祂掌管之外；
  · 神**全智**（wise）——祂的安排永远是最智慧的，即使我此刻看不懂；
  · 神**全善**（good/loving）——祂对祂儿女的心意永远是慈爱的，不会有闪失的错待。
危险是只抓其一（只信主权→宿命；只信慈爱→怀疑祂是否掌权）。三根一起，心才能安。

纯函数；确定性优先；内置危机词检测（痛苦主题，不轻看）；AI 仅作可选增强。
不轻率地说「一切都有神美意」，而是温柔地把三根支柱交给正在难处里的人。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

SITUATIONS: List[Dict[str, Any]] = [
    {"key": "chaos", "name": "觉得一切失控 / 乱成一团",
     "kw": ["失控", "乱", "一团糟", "没头绪", "崩", "抓不住", "混乱", "全乱了", "无能为力"],
     "pillar": "全权", "note": "没有一件事落在神掌管之外——连你觉得最失控的地方，祂的手仍在其上。",
     "truth": "你感到失控，但神从未失控。祂用祂全能的手托住万有，也托住你此刻的处境。"
              "你不必掌控全局才能安心——因为掌管的那位，是你的父。",
     "ref": "诗115:3", "text": "然而，我们的神在天上，都随自己的意旨行事。"},
    {"key": "senseless", "name": "想不通为什么会这样 / 觉得没意义",
     "kw": ["想不通", "为什么", "没意义", "不明白", "毫无道理", "凭什么", "看不懂", "白白", "无解"],
     "pillar": "全智", "note": "你此刻看不懂，不等于没有意义——神的智慧远高过你能看见的这一段。",
     "truth": "你站在织锦的背面，只看见乱线；神看见正面的图案。祂做的每一件事都是最智慧的，"
              "即使要等很久、甚至今生才明白一部分。看不懂时，可以信靠那位从不出错的智慧。",
     "ref": "罗11:33", "text": "深哉，神丰富的智慧和知识！他的判断何其难测，他的踪迹何其难寻！"},
    {"key": "unfair", "name": "觉得神待我不公 / 为何是我",
     "kw": ["不公", "为何是我", "不公平", "凭什么是我", "神狠心", "被亏待", "别人都好", "偏偏我", "冤"],
     "pillar": "全善", "note": "神对祂儿女的心意永远是慈爱的——祂不会错待你，哪怕这一刻感觉像被亏待。",
     "truth": "那位为你舍了独生子的神，绝不会在小事上吝待你、在大事上错待你。祂的良善不由你的处境证明，"
              "而由十字架证明了。难处不是祂爱的中断，反而常是祂爱的另一种作为。",
     "ref": "罗8:32", "text": "神既不爱惜自己的儿子，为我们众人舍了，岂不也把万物和他一同白白地赐给我们吗？"},
    {"key": "worry", "name": "担心未来 / 怕接下来会更糟",
     "kw": ["担心", "怕未来", "会更糟", "忧虑", "怕出事", "前路", "不确定", "焦虑未来", "怕失去"],
     "pillar": "全权全善", "note": "掌管明天的，是那位爱你的父；你不必独自替祂担忧明天。",
     "truth": "你走向的每一个明天，神都已经在那里等你。祂既是全权、又是全善，就没有一个「祂管不了」或"
              "「祂不在乎」的明天。把忧虑一件件卸给祂，因为祂顾念你。",
     "ref": "太6:34", "text": "所以，不要为明天忧虑，因为明天自有明天的忧虑。",
     },
    {"key": "small", "name": "琐碎的日常里想看见神的手",
     "kw": ["琐碎", "日常", "平淡", "小事", "看不见神", "普通", "无聊", "点点滴滴", "平常"],
     "pillar": "全权全智全善", "note": "护理不只在大事，也在最小的细节——一只麻雀落地祂都知道。",
     "truth": "神的护理细到你的头发都被数过。今天那些看似偶然的相遇、安排、拦阻，未必是偶然——"
              "学习在平凡里读出祂的手，日子就不再是随机，而是被慈父编织的。",
     "ref": "太10:29-30", "text": "两个麻雀……若是你们的父不许，一个也不能掉在地上……就是你们的头发也都被数过了。"},
    {"key": "trust", "name": "想学习在难处里信靠神的手",
     "kw": ["信靠", "护理", "神的手", "交托", "主权", "学习信靠", "安息", "顺服神的安排", "更信"],
     "pillar": "三根一起", "note": "信靠神，是同时相信祂全权、全智、全善——三根一起，心才能真安。",
     "truth": "信靠不是弄懂了才信，而是认定那位掌管的、是全智又全善的父，就把看不懂的这一段交在祂手里。"
              "你可以对祂说：我不明白，但我信你——你的主权、智慧、慈爱，够我倚靠。",
     "ref": "箴3:5-6", "text": "你要专心仰赖耶和华，不可倚靠自己的聪明……他必指引你的路。"},
]

CRISIS_WORDS = ["自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死",
                "死了算了", "伤害自己", "撑不下去了", "没有意义活着", "想消失"]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = ("我听见你正承受很重的痛。谈神的护理之前，我想先温柔地说：如果你有伤害自己的念头，"
               "请现在就联系你信任的人或当地心理危机热线。神的手此刻仍托住你——你不必独自扛。（本功能不替代专业帮助。）")


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best, best_hits = None, 0
    for d in SITUATIONS:
        hits = sum(1 for k in d["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, d
    return best or SITUATIONS[5]


def meta() -> Dict[str, Any]:
    return {
        "title": "神的护理 · 信靠主权的手",
        "source": "傅拉维《护理的奥秘》；Jerry Bridges《信靠神》",
        "core": "信靠神须同时相信三根支柱：神全权、全智、全善——万事都在祂掌管中，且叫爱神的人得益处。",
        "pillars": [
            {"name": "全权", "note": "没有一件事落在祂掌管之外。"},
            {"name": "全智", "note": "祂的安排永远最智慧，即使我看不懂。"},
            {"name": "全善", "note": "祂对儿女的心意永远慈爱，不会错待。"},
        ],
        "situations": [{"key": d["key"], "name": d["name"]} for d in SITUATIONS],
        "verse": "罗8:28",
        "principle": "「万事都互相效力，叫爱神的人得益处。」——不是万事都是好的，而是那位全权全智全善的父，叫万事效力于益处。",
    }


def analyze(text: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    text = (text or "").strip()
    crisis = _detect_crisis(text)
    picked = _pick(text)
    result: Dict[str, Any] = {
        "crisis": crisis, "crisis_note": CRISIS_NOTE if crisis else "",
        "situation": {"key": picked["key"], "name": picked["name"]},
        "pillar": picked["pillar"],
        "pillar_note": picked["note"],
        "truth": picked["truth"],
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "three_pillars": ("信靠神，是同时抓住三根支柱：祂**全权**（掌管万事）、**全智**（安排最智慧）、"
                          "**全善**（心意永慈爱）。只抓一根会失衡；三根一起，心才能安。"),
        "prayer": ("父啊，我此刻看不清、也想不通，心里发慌。求你帮助我信靠你——不是因为我弄懂了，"
                   "而是因为我认定你是全权的、全智的、又全善的父。你既没有爱惜自己的儿子，就绝不会错待我。"
                   "我把这看不懂的一段交在你手里；求你叫万事效力于益处，也叫我在其中更认识你、更信靠你。"),
        "practices": [
            "把处境放进三根支柱：就眼下这件事，分别对神说「你掌管这事、你比我有智慧、你爱我不会错待」。",
            "回望护理：写下过去一件当时想不通、后来看见神的手的事，用它来喂养今天的信靠。",
        ],
        "summary": ("神的护理是：全权、全智、全善的父掌管万事，叫万事效力于益处。看不懂时，不必先弄懂才信——"
                    "认定那掌管的是慈爱的父，就把这一段交在祂手里。"),
        "closing": "「万事都互相效力，叫爱神的人得益处。」（罗8:28）",
        "ai_used": False,
    }
    if use_ai:
        enh = _ai_enhance(text, result, settings)
        if enh:
            result.update(enh); result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return ("你是一位温柔、以福音为中心的属灵陪伴者，熟悉傅拉维《护理的奥秘》与 Bridges《信靠神》。"
            "核心：信靠神须同时相信三根支柱——神全权、全智、全善；万事互相效力叫爱神的人得益处(罗8:28，"
            "不是万事皆好，而是父叫万事效力于益处)。请针对用户处境，温柔地把对应的支柱交给他，"
            "绝不轻率地说『一切都有美意』，给经文、祷告与操练。中文，不轻看其痛。\n"
            f"用户处境：{text}\n"
            "请输出 JSON：{\"truth\":\"...\",\"three_pillars\":\"...\",\"prayer\":\"一段可照着祷告的话\",\"summary\":\"...\",\"closing\":\"一句经文\"}。")


def _ai_enhance(text, base, settings):
    raw = _call_ai(build_prompt(text, base), settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        return {k: str(data[k]) for k in ("truth", "three_pillars", "prayer", "summary", "closing") if data.get(k)} or None
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
        return (["trust", "providence", "hope"], False, True, 2.0)
    return (["trust", "providence", "hope"], True, True, 4.0)
