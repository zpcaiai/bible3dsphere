"""
lament_engine.py — 哀歌 / Biblical Lament（Mark Vroegop《Dark Clouds, Deep Mercy》）

补足 gap 分析所缺的「结构化哀歌祷告模板」。哀歌不是抱怨，是**带着信心向神倾诉痛苦**，
是圣经里近三分之一诗篇的语言。Vroegop 归纳的四个动作：
  转向神(Turn) → 倾诉(Complain) → 祈求(Ask) → 信靠(Trust)。

与 `suffering_engine`（苦难诊断/牧养分类）互补而不重叠：本引擎只做「把痛苦谱成一篇哀歌祷告」
这一件事——给用户一个可以照着向神说话的脚手架。

纯函数；确定性优先；内置危机词检测；AI 仅作可选增强，失败回退确定性结果。
不定罪、不贴标签，只帮助人向神诚实倾诉并转向信靠。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# ── 四个动作（Vroegop 四步） ──
MOVEMENTS: List[Dict[str, str]] = [
    {"key": "turn",     "name": "转向神", "verb": "Turn",
     "desc": "把痛苦带到神面前，而不是远离祂。哀歌从「呼求」开始——即使只喊得出祂的名。",
     "prompt": "对神说出你现在的处境，哪怕只是一句「主啊，我在这里，我需要你」。",
     "ref": "诗13:1", "text": "耶和华啊，你忘记我要到几时呢？要到永远吗？"},
    {"key": "complain", "name": "倾诉", "verb": "Complain",
     "desc": "诚实地说出到底哪里痛。圣经允许你把控诉、不解、眼泪都摆在神面前。",
     "prompt": "具体说出你的痛、你的不解、你觉得不公平的地方——不必修饰。",
     "ref": "诗13:2", "text": "我心里筹算，终日愁苦，要到几时呢？"},
    {"key": "ask",      "name": "祈求", "verb": "Ask",
     "desc": "大胆求神介入。哀歌不停在抱怨，它向那位有能力的神伸手。",
     "prompt": "明确求神做一件事：光照、拯救、看顾、给力量、或只是与你同在。",
     "ref": "诗13:3", "text": "耶和华我的神啊，求你看顾我，应允我，使我眼目光明。"},
    {"key": "trust",    "name": "信靠", "verb": "Trust",
     "desc": "选择信靠——不是因为感觉好了，而是因为神的性情与应许不改变。哀歌以信心收尾。",
     "prompt": "写下一句你仍然相信的关于神的真理，把心交托给祂。",
     "ref": "诗13:5-6", "text": "但我倚靠你的慈爱，我的心因你的救恩快乐……因祂用厚恩待我。"},
]
MOVEMENT_INDEX = {m["key"]: m for m in MOVEMENTS}

# ── 哀歌主题 → 锚点经文 + 祈求措辞 ──
THEMES: List[Dict[str, Any]] = [
    {"key": "loss", "name": "失去 / 哀伤", "kw": ["失去", "死", "离世", "分手", "走了", "没有了", "丧"],
     "ref": "诗34:18", "text": "耶和华靠近伤心的人，拯救灵性痛悔的人。",
     "ask": "求你靠近我这颗破碎的心，在我说不出话的地方替我叹息。"},
    {"key": "injustice", "name": "不公 / 被伤害", "kw": ["不公", "冤", "背叛", "欺负", "委屈", "被害", "不公平"],
     "ref": "诗10:14", "text": "其实你已经观看，因为奸恶毒害,你都看见了……你是帮助孤儿的。",
     "ask": "求你看见这不公，作我的辩护者，我把伸冤的权交在你手中。"},
    {"key": "illness", "name": "疾病 / 软弱", "kw": ["病", "痛", "医", "身体", "撑不住", "累垮", "虚弱"],
     "ref": "诗41:3", "text": "他病重在榻，耶和华必扶持他。",
     "ask": "求你医治、扶持我，在我软弱到极处时成为我的力量。"},
    {"key": "waiting", "name": "漫长等待", "kw": ["等", "还没", "迟迟", "遥遥", "无期", "多久"],
     "ref": "诗27:14", "text": "要等候耶和华！当壮胆，坚固你的心。",
     "ask": "求你在这看不到尽头的等待里，坚固我的心，叫我不失去盼望。"},
    {"key": "guilt", "name": "罪疚 / 懊悔", "kw": ["罪", "错", "懊悔", "羞愧", "对不起", "内疚", "亏欠"],
     "ref": "诗51:17", "text": "神所要的祭就是忧伤的灵；忧伤痛悔的心，你必不轻看。",
     "ask": "求你按你的慈爱赦免我，重造一颗清洁的心，让我在恩典里重新站立。"},
    {"key": "loneliness", "name": "孤独 / 被弃", "kw": ["孤独", "没人", "孤单", "被弃", "抛弃", "无人", "孤立"],
     "ref": "诗27:10", "text": "我父母离弃我，耶和华必收留我。",
     "ask": "求你让我知道你从未离开，在无人的地方作我最深的同在。"},
    {"key": "fear", "name": "恐惧 / 焦虑", "kw": ["怕", "恐惧", "焦虑", "担心", "不安", "惊", "慌"],
     "ref": "诗56:3", "text": "我惧怕的时候要倚靠你。",
     "ask": "求你在我惧怕时接住我，用你的同在赶散我心里的黑。"},
    {"key": "darkness", "name": "看不到神 / 属灵黑夜", "kw": ["黑暗", "看不到", "沉默", "远离", "枯干", "绝望", "无意义"],
     "ref": "诗88:1", "text": "耶和华拯救我的神啊，我昼夜在你面前呼吁。",
     "ask": "求你在这片沉默的黑里，哪怕给我一点点你仍在的记号；我仍要向你呼求。"},
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


def _pick_themes(text: str, max_n: int = 2) -> List[Dict[str, Any]]:
    t = text or ""
    scored: List[tuple] = []
    for th in THEMES:
        hits = sum(1 for k in th["kw"] if k in t)
        if hits:
            scored.append((hits, th))
    scored.sort(key=lambda x: -x[0])
    picked = [th for _, th in scored[:max_n]]
    if not picked:
        picked = [THEMES[0]]  # 默认「失去/哀伤」的普遍安慰
    return picked


def meta() -> Dict[str, Any]:
    """哀歌四步 + 主题 + 示例哀歌诗篇（供前端展示）。"""
    return {
        "movements": MOVEMENTS,
        "themes": [{"key": t["key"], "name": t["name"]} for t in THEMES],
        "lament_psalms": [
            {"ref": "诗13", "note": "「要到几时呢」——个人哀歌的典范，四步俱全。"},
            {"ref": "诗22", "note": "「我的神，为什么离弃我」——主在十架上引用的哀歌。"},
            {"ref": "诗88", "note": "少数以黑暗收尾的哀歌——告诉我们：连绝望也可以向神说。"},
            {"ref": "耶利米哀歌3", "note": "「每早晨都是新的」——废墟中仍抓住慈爱。"},
        ],
        "principle": "哀歌 = 带着信心的哭泣。它不是不信，正相反——它是把痛苦带到唯一能承受它的神那里。",
    }


def compose(text: str, situation: Optional[str] = None,
            *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    """把用户的痛苦谱成一篇四步哀歌祷告（确定性；可选 AI 增强）。"""
    text = (text or "").strip()
    crisis = _detect_crisis(text)
    themes = _pick_themes(text)
    primary = themes[0]

    # 确定性地为四个动作各生成一段可照着祷告的草稿
    blocks: List[Dict[str, Any]] = []
    for m in MOVEMENTS:
        if m["key"] == "turn":
            draft = "主啊，我来到你面前。" + ("我几乎说不出话，但我把" + primary["name"] + "带到你这里。")
        elif m["key"] == "complain":
            body = text if text else "我心里的重担"
            draft = "我要诚实地告诉你：" + body + "。这让我" + primary["name"].split(" /")[0] + "，我不明白，也撑得很吃力。"
        elif m["key"] == "ask":
            draft = primary["ask"]
            if len(themes) > 1:
                draft += " 也" + themes[1]["ask"]
        else:  # trust
            draft = "但我仍要倚靠你的慈爱。" + primary["text"] + "（" + primary["ref"] + "）就算感觉没有变，你的性情没有变。我把心交在你手里。"
        blocks.append({
            "key": m["key"], "name": m["name"], "verb": m["verb"],
            "guidance": m["prompt"], "draft": draft,
            "scripture": {"ref": m["ref"], "text": m["text"]},
        })

    result: Dict[str, Any] = {
        "crisis": crisis,
        "crisis_note": CRISIS_NOTE if crisis else "",
        "themes": [{"key": t["key"], "name": t["name"],
                    "scripture": {"ref": t["ref"], "text": t["text"]}} for t in themes],
        "movements": blocks,
        "prayer": "\n".join(b["draft"] for b in blocks),
        "summary": "你可以照着上面四步向神祷告——从" + MOVEMENTS[0]["name"] + "开始，"
                   "以" + MOVEMENTS[-1]["name"] + "收尾。哀歌的方向永远是：把痛苦交出去，把信靠拿回来。",
        "closing": "「我倚靠你的慈爱，我的心因你的救恩快乐。」（诗13:5）",
        "ai_used": False,
    }

    if use_ai:
        enhanced = _ai_enhance(text, situation, result, settings)
        if enhanced:
            result.update(enhanced)
            result["ai_used"] = True
    return result


def build_prompt(text: str, situation: Optional[str], base: Dict[str, Any]) -> str:
    return (
        "你是一位温柔、以福音为中心的属灵陪伴者，熟悉 Mark Vroegop《Dark Clouds, Deep Mercy》"
        "所讲的圣经哀歌（转向神→倾诉→祈求→信靠）。请把用户的痛苦谱成一篇真诚的四步哀歌祷告，"
        "中文，温暖不说教，不定罪、不贴标签、不说『你信心不够』之类的话，多用诗篇的语气。\n"
        f"用户处境：{situation or '（未特别说明）'}\n用户倾诉：{text}\n"
        "请输出 JSON：{\"movements\":[{\"key\":\"turn|complain|ask|trust\",\"draft\":\"...\"}],"
        "\"summary\":\"...\",\"closing\":\"一句经文\"}。draft 是可以让用户直接照着祷告的话。"
    )


def _ai_enhance(text: str, situation: Optional[str], base: Dict[str, Any], settings: Any) -> Optional[Dict[str, Any]]:
    """可选 AI 增强：任何失败都回退（返回 None）。"""
    prompt = build_prompt(text, situation, base)
    raw = _call_ai(prompt, settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        drafts = {d.get("key"): d.get("draft") for d in data.get("movements", []) if isinstance(d, dict)}
        blocks = []
        for b in base["movements"]:
            nb = dict(b)
            if drafts.get(b["key"]):
                nb["draft"] = str(drafts[b["key"]])
            blocks.append(nb)
        out = {"movements": blocks, "prayer": "\n".join(b["draft"] for b in blocks)}
        if data.get("summary"):
            out["summary"] = str(data["summary"])
        if data.get("closing"):
            out["closing"] = str(data["closing"])
        return out
    except Exception:
        return None


def _call_ai(prompt: str, settings: Any) -> Optional[str]:
    """尽力调用既有 provider；不可用则返回 None（引擎保持零硬依赖）。"""
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
    """回流 formation：哀歌属于「向神诚实倾诉+转向信靠」，标注情绪/成长维度。"""
    if result.get("crisis"):
        return (["fear", "growth"], False, True, 2.0)
    return (["hope", "growth"], True, True, 5.0)
