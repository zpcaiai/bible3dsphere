"""
fuel_engine.py — 养料库 / Spiritual Fuel（按「用户困扰」组织，而非按作者）

内容不是「司布真专区 / 钟马田专区」，而是按困扰组织：用户选一个困扰，自动组装
经文 + 多个属灵传统的洞见 + 操练 + 祷告。说明：以下「洞见」是对各传统神学强调的
意译概述（非逐字引语），用于把养料按需取用。纯函数，可选 AI 扩展。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# 困扰 → 养料包
PACKS: Dict[str, Dict[str, Any]] = {
    "anxiety": {
        "name": "焦虑", "icon": "😟", "color": "#ffa94d",
        "scriptures": [
            {"ref": "腓4:6-7", "text": "应当一无挂虑……神所赐出人意外的平安，必保守你们的心。"},
            {"ref": "太6:34", "text": "不要为明天忧虑，因为明天自有明天的忧虑。"},
            {"ref": "彼前5:7", "text": "你们要将一切的忧虑卸给神，因为他顾念你们。"},
        ],
        "voices": [
            {"tag": "钟马田的传统", "insight": "焦虑往往是想替神掌管未来。先停下来诊断：我真正害怕失去的是什么？那害怕，揭示了我把安全感放在了哪里。"},
            {"tag": "司布真的传统", "insight": "把眼目从风浪移到那位踏浪而来的主身上。忧虑改变不了明天，却会榨干今天的力量；天父连麻雀都看顾，何况是你。"},
            {"tag": "清教徒的传统", "insight": "焦虑常因把暂时的当作终极的。操练「默想神的护理」——祂昨日如何带领，今日仍照样信实。"},
        ],
        "practice": "把最挂虑的三件事写下，逐一祷告交托：「这件事我交给你。」",
        "prayer": "主啊，我把忧虑卸给你，因你顾念我。求你以出人意外的平安守护我的心。",
    },
    "depression": {
        "name": "属灵低潮", "icon": "🌫️", "color": "#748ffc",
        "scriptures": [
            {"ref": "诗42:11", "text": "我的心哪，你为何忧闷？……应当仰望神。"},
            {"ref": "诗40:2", "text": "他从淤泥中把我拉上来，使我的脚立在磐石上。"},
        ],
        "voices": [
            {"tag": "钟马田《属灵低潮》", "insight": "我们多半的不快乐，是因为听自己说话，而不是向自己传讲福音。要停止听那低落的声音，转而对自己宣讲真理。"},
            {"tag": "司布真的传统", "insight": "连最火热的讲道者也有灰暗的日子；那不是被弃，而是被炼。继续凭信心来到神面前，哪怕只凭一句应许的微光。"},
        ],
        "practice": "对自己宣告三件救恩中不变的事实：被赦免、被收纳、有永生。",
        "prayer": "主啊，我的心忧闷。求你把救恩的喜乐重新赐给我，叫我仰望你而非环境。",
    },
    "sin": {
        "name": "罪的捆绑", "icon": "⛓️", "color": "#ff8787",
        "scriptures": [
            {"ref": "罗7:24-25", "text": "我真是苦啊……感谢神，靠着我们的主耶稣基督就能脱离了。"},
            {"ref": "约一1:9", "text": "我们若认自己的罪，神是信实的……必要赦免我们的罪。"},
            {"ref": "罗6:14", "text": "罪必不能作你们的主，因你们不在律法之下，乃在恩典之下。"},
        ],
        "voices": [
            {"tag": "欧文的传统", "insight": "要治死罪，否则罪要治死你。但治死罪不靠咬牙苦修，乃靠仰望被钉的基督，让福音的大能临到那条罪根。"},
            {"tag": "钟马田的传统", "insight": "罪的捆绑背后常有一个谎言与偶像。问：这罪在替我满足什么需要？唯有基督能真正满足它。"},
            {"tag": "司布真的传统", "insight": "胜过罪不是靠盯着罪，而是靠尝到基督比罪更甘甜。当祂成为你心头所爱，旧的捆绑就松开了。"},
        ],
        "practice": "把那条反复的罪带到十字架前认罪，并求圣灵指出它底下的偶像与谎言。",
        "prayer": "主啊，我厌倦了被它辖制。求你用你的宝血洗净我，用你的甘甜胜过它的诱惑。",
    },
    "holiness": {
        "name": "追求圣洁", "icon": "✨", "color": "#ffd43b",
        "scriptures": [
            {"ref": "彼前1:16", "text": "你们要圣洁，因为我是圣洁的。"},
            {"ref": "来12:14", "text": "非圣洁没有人能见主。"},
        ],
        "voices": [
            {"tag": "莱尔《圣洁》的传统", "insight": "圣洁不是一时的激动，而是与罪日复一日的争战，是越来越恨恶罪、爱慕基督的实际改变。"},
            {"tag": "司布真的传统", "insight": "圣洁始于与基督亲密的相交；离了葡萄树，枝子结不出果子。先连于祂，圣洁是相交的果实。"},
        ],
        "practice": "今天对一个具体的试探说「不」，并立刻转向基督、求祂的同在充满那空处。",
        "prayer": "主啊，求你使我圣洁，不是靠我的努力，而是靠你住在我里面的生命。",
    },
    "waiting": {
        "name": "等候神", "icon": "🕯️", "color": "#5ac8fa",
        "scriptures": [
            {"ref": "赛40:31", "text": "等候耶和华的必从新得力……行走却不疲乏。"},
            {"ref": "诗27:14", "text": "要等候耶和华！当壮胆，坚固你的心。"},
        ],
        "voices": [
            {"tag": "亚伯拉罕 / 约瑟的见证", "insight": "应许与成就之间，常隔着漫长的等待；神在等待里塑造的，往往比祂赐下的更宝贵。"},
            {"tag": "司布真的传统", "insight": "等候不是停摆，而是积极的信靠。在等待中仍忠心、仍祷告、仍盼望，便是等候上帝而非枯等。"},
        ],
        "practice": "在等待中做一个不依赖最终结果的小行动，把结果交托给神的时间表。",
        "prayer": "主啊，我在等待中容易焦躁。求你叫我等候你时仍然忠心，并在等待里被你塑造。",
    },
    "suffering": {
        "name": "受苦", "icon": "🌧️", "color": "#9775fa",
        "scriptures": [
            {"ref": "罗8:28", "text": "万事都互相效力，叫爱神的人得益处。"},
            {"ref": "林后4:17", "text": "我们这至暂至轻的苦楚，要为我们成就极重无比、永远的荣耀。"},
        ],
        "voices": [
            {"tag": "司布真的传统", "insight": "我在苦难的熔炉里学到的，比在顺境中更多。神的杖与竿都安慰我——祂从不浪费你的眼泪。"},
            {"tag": "清教徒的传统", "insight": "苦难是神雕刻你的凿子。它削去的，是拦阻你亲近祂的东西；它留下的，是更深的信靠。"},
        ],
        "practice": "把这场苦难具体地交托，并求神让你看见祂在其中要成就的一件好事。",
        "prayer": "主啊，我不明白这苦难，但我相信你不会浪费它。求你在其中与我同在，塑造我更像你。",
    },
    "pride": {
        "name": "骄傲", "icon": "🦅", "color": "#fb923c",
        "scriptures": [
            {"ref": "雅4:6", "text": "神阻挡骄傲的人，赐恩给谦卑的人。"},
            {"ref": "腓2:5-8", "text": "你们当以基督耶稣的心为心……自己卑微，存心顺服，以至于死。"},
        ],
        "voices": [
            {"tag": "钟马田的传统", "insight": "骄傲常藏在「属灵」的外衣下——用属灵表现证明自己。要诚实诊断：我在用什么赢得价值？"},
            {"tag": "司布真的传统", "insight": "站在十字架下，无人能骄傲。看见基督为你所付的代价，自夸就化为敬拜。"},
        ],
        "practice": "今天主动承认一次「我错了」，或把一次本可邀功的善事隐藏起来，只让神看见。",
        "prayer": "主啊，求你折服我里面的骄傲，让我在十字架前看见恩典，以致只夸你的十架。",
    },
    "love": {
        "name": "爱人困难", "icon": "💔", "color": "#f472b6",
        "scriptures": [
            {"ref": "约一4:19", "text": "我们爱，因为神先爱我们。"},
            {"ref": "弗4:32", "text": "要以恩慈相待，存怜悯的心，彼此饶恕，正如神在基督里饶恕了你们。"},
        ],
        "voices": [
            {"tag": "司布真的传统", "insight": "爱不是先咬牙挤出，而是先饱享神的爱。被爱满溢的心，自然流向人;先回到那爱的源头。"},
            {"tag": "钟马田的传统", "insight": "爱不出来，常因受了伤、立了界、护着自己。诊断那伤口，把它带到福音前，宽恕从被宽恕里长出。"},
        ],
        "practice": "为那个你难以去爱的人祷告，并今天向他/她迈出一个微小的恩慈行动。",
        "prayer": "主啊，我爱不动了。求你先用你的爱充满我，让我从你的恩典里，重新去爱这个人。",
    },
}


def pack(key: str) -> Optional[Dict[str, Any]]:
    p = PACKS.get(key)
    if not p:
        return None
    return {"key": key, **p}


def meta() -> Dict[str, Any]:
    return {"struggles": [{"key": k, "name": v["name"], "icon": v["icon"], "color": v["color"]}
                          for k, v in PACKS.items()]}


# ── AI 扩展（可选）：为某困扰再生成一段牧养性补充 ─────────────────────────────
def build_prompt(key: str) -> List[Dict[str, str]]:
    p = PACKS.get(key, {})
    system = ("你按改革宗灵修传统（司布真的牧养 + 钟马田的诊断 + 清教徒/欧文/莱尔的深度）"
              "回应用户的属灵困扰。温柔、以基督为中心、实际。只输出 JSON。")
    user = (f"困扰：{p.get('name','')}。请补充一段 120-180 字的牧养性默想，"
            '严格按 JSON：{"extra":"补充默想"}')
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


def assemble(key: str, settings: Any = None, use_ai: bool = False) -> Optional[Dict[str, Any]]:
    p = pack(key)
    if not p:
        return None
    if use_ai:
        try:
            try:
                from backend.waiting_engine import call_ai_provider
            except Exception:
                from waiting_engine import call_ai_provider
            ai = call_ai_provider(build_prompt(key), settings=settings)
            if ai and ai.get("extra"):
                p["extra"] = str(ai["extra"])
        except Exception:
            pass
    return p
