"""
wisdom_engine.py — 智慧 / Wisdom（箴言·传道书·雅各；敬畏耶和华是智慧的开端）

给以「诗篇-情绪」为主的现状，配一条「活得有智慧」的实践线。圣经的智慧(hokmah)不是高深知识，
而是**在神所造的秩序里活得纯熟**的技艺；其根基是「敬畏耶和华」（箴9:10）。

三个面向：
  · **箴言**：日常生活的纯熟——舌头、勤惰、金钱、朋友、谦卑、节制；智慧落在具体选择上。
  · **传道书**：诚实面对「日光之下」的虚空与有限，学会在神所赐的本分与当下里知足、敬畏神。
  · **雅各**：分辨「属地的聪明」与「从上头来的智慧」——后者「先是清洁，后是和平、温良、柔顺」（雅3:17）。

与 decision / discernment 引擎互补：那些做「属灵/意志层面的分辨」，本引擎做「箴言式的实践智慧」——
把一个具体处境，对上一条箴言原则 + 从上头来之智慧的检验。
纯函数；确定性优先；内置危机词检测；AI 仅作可选增强。不给标准答案，只给智慧的方向与敬畏的根。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

DOMAINS: List[Dict[str, Any]] = [
    {"key": "tongue", "name": "言语 / 说话惹的事",
     "kw": ["说错话", "口舌", "冲动说", "得罪", "八卦", "争辩", "回嘴", "乱说", "祸从口出", "抱怨"],
     "principle": "智慧管得住舌头：言语能医人也能伤人；快快地听，慢慢地说。",
     "ref": "箴17:27", "text": "寡少言语的，有知识；性情温良的，有聪明。",
     "step": "下次开口前先停三秒问：这话真实吗？必要吗？有益吗？——不满足就先不说。"},
    {"key": "diligence", "name": "拖延 / 勤惰 / 做事没恒心",
     "kw": ["拖延", "懒", "半途", "没恒心", "混", "不想动", "三分钟热度", "逃避事情", "堆积", "摆烂"],
     "principle": "智慧是殷勤而有节制的：懒惰使人受制，殷勤的手却使人富足；小步的忠心胜过空想。",
     "ref": "箴13:4", "text": "懒惰人羡慕，却无所得；殷勤人必得丰裕。",
     "step": "把那件拖着的事切成一个 10 分钟就能起步的小动作，今天先做这一步。"},
    {"key": "money", "name": "金钱 / 消费 / 债务的决定",
     "kw": ["钱", "消费", "债", "买", "投资", "省", "花钱", "财务", "借钱", "冲动购物"],
     "principle": "智慧待钱财：不倚靠无定的钱财，量入为出，慷慨而不贪；免债一身轻。",
     "ref": "箴21:5", "text": "殷勤筹划的，足致丰裕；行事急躁的，都必缺乏。",
     "step": "这笔花费先放 24 小时再决定；问：这是需要，还是想用它填补别的空？"},
    {"key": "friends", "name": "交友 / 受人影响 / 关系的选择",
     "kw": ["朋友", "交友", "圈子", "influence", "被带坏", "损友", "同伴", "择友", "关系", "谁来往"],
     "principle": "智慧择友：与智慧人同行必得智慧；铁磨铁，磨出刃来——你常在一起的人在塑造你。",
     "ref": "箴13:20", "text": "与智慧人同行的，必得智慧；和愚昧人作伴的，必受亏损。",
     "step": "看看你花最多时间的三个人，把你朝哪个方向带；本周多靠近一位使你更像基督的人。"},
    {"key": "pride", "name": "骄傲 / 自以为是 / 不听劝",
     "kw": ["自以为是", "不听劝", "骄傲", "固执", "我说了算", "听不进", "自负", "刚愎", "看不起人", "非要"],
     "principle": "智慧始于谦卑：敬畏耶和华是智慧的开端；智慧人肯受责备、肯听劝。",
     "ref": "箴9:10", "text": "敬畏耶和华是智慧的开端；认识至圣者便是聪明。",
     "step": "就眼下这件事，主动去问一位敬畏神、且敢对你说真话的人，认真听他怎么说。"},
    {"key": "meaning", "name": "觉得一切没意义 / 忙来忙去为什么（传道书）",
     "kw": ["没意义", "虚空", "为什么忙", "日光之下", "空", "白忙", "到底图啥", "厌倦", "循环", "无谓"],
     "principle": "传道书的智慧：日光之下尽是虚空，但敬畏神、守祂诫命、领受当下的本分与恩赐，就是人的本分与出路。",
     "ref": "传12:13", "text": "敬畏神，谨守他的诫命，这是人所当尽的本分。",
     "step": "今天不追问「全部的意义」，只忠心领受一件当下的小恩赐（一餐、一份工、一段关系），向神谢恩并尽本分。"},
    {"key": "general", "name": "一个需要智慧的处境 / 拿不定主意",
     "kw": [],
     "principle": "从上头来的智慧「先是清洁，后是和平、温良、柔顺，满有怜悯」——用这几样检验你倾向的选择。",
     "ref": "雅1:5", "text": "你们中间若有缺少智慧的，应当求那厚赐与众人、也不斥责人的神，主就必赐给他。",
     "step": "把你倾向的做法，对照雅3:17 逐条问：它清洁吗？带来和平吗？温良柔顺吗？有怜悯吗？"},
]

CRISIS_WORDS = [
    "自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死", "死了算了",
    "伤害自己", "撑不下去了", "没有意义活着", "想消失",
]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = (
    "我听见你正承受很重的痛。谈智慧之前，我想先温柔地说：如果你有伤害自己的念头，"
    "请现在就联系你信任的人或当地心理危机热线——你不必独自面对。（本功能不替代专业帮助。）"
)


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best, best_hits = None, 0
    for d in DOMAINS:
        if d["key"] == "general":
            continue
        hits = sum(1 for k in d["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, d
    return best or next(d for d in DOMAINS if d["key"] == "general")


def meta() -> Dict[str, Any]:
    return {
        "title": "智慧 · 敬畏神地活",
        "source": "箴言 · 传道书 · 雅各书",
        "core": "圣经的智慧是在神所造秩序里活得纯熟的技艺，根基是敬畏耶和华；分辨属地聪明与从上头来的智慧。",
        "domains": [{"key": d["key"], "name": d["name"]} for d in DOMAINS if d["key"] != "general"],
        "from_above": "从上头来的智慧：先是清洁，后是和平、温良、柔顺，满有怜悯，多结善果，没有偏见，没有假冒（雅3:17）。",
        "verse": "箴9:10",
        "principle": "「敬畏耶和华是智慧的开端。」——智慧不始于聪明，而始于在神面前的谦卑与敬畏。",
    }


def analyze(text: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    text = (text or "").strip()
    crisis = _detect_crisis(text)
    picked = _pick(text)
    result: Dict[str, Any] = {
        "crisis": crisis,
        "crisis_note": CRISIS_NOTE if crisis else "",
        "domain": {"key": picked["key"], "name": picked["name"]},
        "principle": picked["principle"],
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "from_above_test": "用「从上头来的智慧」检验你倾向的选择：它清洁吗？带来和平吗？温良柔顺吗？满有怜悯吗？（雅3:17）",
        "wise_step": picked["step"],
        "prayer": ("主啊，我承认智慧不在我，乃在你。求你厚赐智慧给我这缺少智慧的人——不斥责，白白地给。"
                   "叫我敬畏你，先在你面前谦卑下来，再在这具体的事上，拣选那清洁、和平、温良、有怜悯的路，"
                   "而不是那看似聪明却出于血气的路。愿我活得像认识你的人。"),
        "practices": [
            "走一小步智慧的路：" + picked["step"],
            "敬畏为根：做决定前先安静一句「主啊，在这事上我要敬畏你」，让敬畏而非利害来定方向。",
        ],
        "summary": ("圣经的智慧是「活得纯熟」的技艺，根在敬畏神。别只求聪明的算计，求那从上头来、"
                    "清洁又和平的智慧，并落到一个具体的小步上。"),
        "closing": "「敬畏耶和华是智慧的开端；认识至圣者便是聪明。」（箴9:10）",
        "ai_used": False,
    }
    if use_ai:
        enh = _ai_enhance(text, result, settings)
        if enh:
            result.update(enh); result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return (
        "你是一位温柔、以福音为中心的属灵陪伴者，熟悉箴言、传道书与雅各书的智慧文学。核心：圣经的智慧是"
        "在神所造秩序里活得纯熟的技艺，根基是敬畏耶和华(箴9:10)；要分辨属地的聪明与从上头来的智慧"
        "(雅3:17 先是清洁后是和平温良柔顺满有怜悯)。请针对用户的处境，对上一条箴言原则，给经文、"
        "一个可走的智慧小步与祷告；不要替他做决定，而是给智慧的方向与敬畏的根。中文，温暖不说教。\n"
        f"用户处境：{text}\n"
        "请输出 JSON：{\"principle\":\"...\",\"wise_step\":\"...\",\"prayer\":\"一段可照着祷告的话\","
        "\"summary\":\"...\",\"closing\":\"一句经文\"}。"
    )


def _ai_enhance(text: str, base: Dict[str, Any], settings: Any) -> Optional[Dict[str, Any]]:
    raw = _call_ai(build_prompt(text, base), settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        return {k: str(data[k]) for k in ("principle", "wise_step", "prayer", "summary", "closing") if data.get(k)} or None
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
    if result.get("crisis"):
        return (["wisdom", "discernment", "obedience"], False, True, 2.0)
    return (["wisdom", "discernment", "obedience"], True, True, 4.0)
