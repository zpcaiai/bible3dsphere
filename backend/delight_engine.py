"""
delight_engine.py — 喜乐重构 / Christian Hedonism（John Piper《Desiring God 渴慕神》基督徒享乐主义）

补足 gap 分析所缺的「把责任重构为通往在神里喜乐之路」。派博的核心洞见：
神造我们是为了在祂里面享受祂——所以任何感觉像「苦差 / 义务」的操练，其实都是通往
最深喜乐的门，而不是我们付给神的费用。座右铭：
  「神在我们最以祂为乐时，最得着荣耀。」（God is most glorified in us when we are most satisfied in Him.）

与 affections_engine（情感辨识）互补而不重叠：本引擎只做「把一件 joyless 的操练，
用基督徒享乐主义重构成 means to joy」这一件事——温柔承认那份重担，再把逻辑、经文、
一个『为喜乐而争战』的具体操练交回给用户。

纯函数；确定性优先；内置危机词检测；AI 仅作可选增强，失败回退确定性结果。
不定罪、不贴标签、不说『你不够属灵』，只帮助人看见责任底下藏着的喜乐。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# ── 座右铭 + 五个信念（意译 Piper 的 Christian Hedonism） ──
MOTTO = "神在我们最以祂为乐时，最得着荣耀。(God is most glorified in us when we are most satisfied in Him.)"

FIVE_CONVICTIONS: List[str] = [
    "神造万有——包括你——都是为了祂自己的荣耀。",
    "每个人都在寻求幸福，这渴望不该被压制，而该被满足在神里面。",
    "最深、最持久的喜乐，唯独在神自己里面才找得到。",
    "这份在神里的喜乐，在患难中仍能持守，并会溢流成舍己的爱。",
    "「为喜乐而争战」是信心与顺服的一部分，不是自私。",
]

# ── 常见「感觉像苦差」的操练 → 重构逻辑 + 锚点经文 + 为喜乐而争战的具体操练 ──
DUTIES: List[Dict[str, Any]] = [
    {"key": "bible", "name": "读经", "kw": ["读经", "圣经", "灵修", "读神的话", "查经", "背经"],
     "burden": "翻开圣经却像在完成任务，读不进去、也感觉不到什么。",
     "reframe": "读经不是你交给神的作业，而是神主动向你说话、让你尝到祂的门。祂话语里的甘甜，是设计给你去享受的，不是要你去消化的义务。",
     "ref": "诗119:103", "text": "你的言语在我上膛何等甘美，在我口中比蜜更甜！",
     "fight": "读经前先安静祷告诗119:18『求你开我的眼，使我看出你律法中的奇妙』——把读经从『我要读完』改成『主，请你让我看见你』。"},
    {"key": "prayer", "name": "祷告", "kw": ["祷告", "祈祷", "祷", "亲近神", "灵修祷告"],
     "burden": "祷告像自言自语，或像一份必须打卡的功课，提不起劲。",
     "reframe": "祷告不是宗教义务，而是被邀请进入你所能拥有的最亲密的关系——与那位最满足你的神面对面。喜乐不在『祷告这个动作』，在祷告所通向的祂。",
     "ref": "诗16:11", "text": "在你面前有满足的喜乐，在你右手中有永远的福乐。",
     "fight": "把祷告从『我该说什么』改成『我要享受与谁在一起』：先花一分钟只是安静地对神说『我在这里，我要你』，不求什么，只求祂自己。"},
    {"key": "gather", "name": "聚会 / 团契", "kw": ["聚会", "团契", "教会", "崇拜", "小组", "主日"],
     "burden": "去聚会像例行公事，甚至有点累，只想待在家。",
     "reframe": "聚集敬拜不是要还的『出席义务』，而是神设计来放大喜乐的地方——喜乐在众人一同以祂为乐时被点燃、被加倍。你不是去付出，是去被神和肢体一同喂养。",
     "ref": "诗122:1", "text": "人对我说：我们往耶和华的殿去，我就欢喜。",
     "fight": "去之前先为一件事祷告：『主，让我在这次聚集里，因你而重新快乐一次。』把目光从『我要表现』转到『我要一同以祂为乐』。"},
    {"key": "obey", "name": "顺服", "kw": ["顺服", "听命", "遵守", "舍己", "背十字架", "命令", "诫命"],
     "burden": "顺服神感觉像放弃自己想要的，像一种损失和牺牲。",
     "reframe": "神的命令不是要夺走你的喜乐，而是护栏，把你引向祂里面更深、更真的喜乐。顺服不是『我失去』，是『我信祂的道路比我的更好、更快乐』。",
     "ref": "诗37:4", "text": "又要以耶和华为乐，祂就将你心里所求的赐给你。",
     "fight": "把每一个『我必须顺服』改写成『我相信在这件事上，祂的喜乐比我抓住的更大』——顺服前先默想诗37:4，让『以祂为乐』成为顺服的动机。"},
    {"key": "give", "name": "奉献", "kw": ["奉献", "十一", "捐", "给钱", "钱财", "financial"],
     "burden": "奉献时心里舍不得，像被拿走了本属于我的东西。",
     "reframe": "奉献不是给神交税，而是把财宝挪到那会带来永恒喜乐的地方——你是在投资，不是在损失。神爱那乐意给的人，因为给出去本身就通向更大的快乐。",
     "ref": "林后9:7", "text": "各人要随本心所酌定的，不要作难，不要勉强，因为捐得乐意的人是神所喜爱的。",
     "fight": "奉献前，把它想象成一笔『投资在永恒喜乐上』的存款，而不是一笔支出；为『能给』献上感恩，让『乐意』先于『金额』。"},
    {"key": "serve", "name": "服事", "kw": ["服事", "事奉", "服侍", "帮忙", "牺牲", "付出", "摆上"],
     "burden": "服事到心力交瘁，感觉是在被消耗、在硬撑。",
     "reframe": "健康的服事不是自我榨干，而是在神里的喜乐溢流出来、成为爱人的方式。当你先在祂里面被满足，服事就从『我要撑住』变成『我心中的喜乐装不下、要分给人』。",
     "ref": "诗100:2", "text": "你们当乐意事奉耶和华，当来向他歌唱！",
     "fight": "服事前先『装满』再『倒出』：花几分钟单单享受神的爱与同在，直到心里有一点点满溢，再从那份满溢出发去服事，而不是从空罐子里硬挤。"},
]

CRISIS_WORDS = [
    "自杀", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死", "死了算了",
    "伤害自己", "撑不下去了", "没有意义活着", "想消失",
]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = (
    "我听见你正承受很重的痛。在我们一起谈喜乐之前，我想先温柔地说：如果你有伤害自己的念头，"
    "请现在就联系你信任的人，或当地的心理危机热线——你值得有人此刻真实地陪着你。神爱你，"
    "你不必独自扛。（本功能不替代专业帮助。）"
)


def _pick_duty(text: str) -> Dict[str, Any]:
    t = text or ""
    scored: List[tuple] = []
    for d in DUTIES:
        hits = sum(1 for k in d["kw"] if k in t)
        if hits:
            scored.append((hits, d))
    scored.sort(key=lambda x: -x[0])
    if scored:
        return scored[0][1]
    # 找不到具体操练时，用一个通用的「以神为乐」重构
    return {
        "key": "general", "name": "这件操练",
        "burden": "它现在对你来说，更像一份必须完成的责任，而不是喜乐的来源。",
        "reframe": "无论是哪一样属灵操练，它都不是你交给神的费用，而是神设计来把你引向祂、让你在祂里面得满足的门。重点从来不是那个动作，而是动作所通向的神自己。",
        "ref": "诗16:11", "text": "在你面前有满足的喜乐，在你右手中有永远的福乐。",
        "fight": "开始之前，先把它交托：『主，我不只是要做完这件事，我要在这件事里遇见你、以你为乐。』让『享受祂』成为你去做的动机。",
    }


def meta() -> Dict[str, Any]:
    """座右铭 + 五个信念 + 锚点经文（供前端展示）。"""
    return {
        "motto": MOTTO,
        "five_convictions": FIVE_CONVICTIONS,
        "verses": [
            "诗16:11 在你面前有满足的喜乐",
            "诗37:4 你要以耶和华为乐，祂就将你心里所求的赐给你",
        ],
        "duties": [{"key": d["key"], "name": d["name"]} for d in DUTIES],
        "principle": "基督徒享乐主义 = 追求在神里最深的喜乐，正是神最得荣耀、也是你最蒙福的道路。责任不是喜乐的对立面，而是通往喜乐的门。",
    }


def reframe(duty: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    """把一件感觉像苦差的操练，用基督徒享乐主义重构成通往在神里喜乐之路（确定性；可选 AI 增强）。"""
    duty = (duty or "").strip()
    crisis = _detect_crisis(duty)
    d = _pick_duty(duty)

    acknowledge = (
        "我先停下来，温柔地承认：把「" + d["name"] + "」经历成一份重担，是真实的，也没有关系——"
        + d["burden"] + " 你愿意把这份感觉带出来，本身就是诚实的一步。"
    )
    logic = d["reframe"]
    scripture = {"ref": d["ref"], "text": d["text"]}
    fight_practice = d["fight"]

    result: Dict[str, Any] = {
        "crisis": crisis,
        "crisis_note": CRISIS_NOTE if crisis else "",
        "duty": d["name"],
        "motto": MOTTO,
        "acknowledge": acknowledge,
        "reframe": logic,
        "scripture": scripture,
        "fight_for_joy": fight_practice,
        "summary": (
            "「" + d["name"] + "」不是你付给神的费用，而是通往在神里喜乐的门。"
            "神在你最以祂为乐时最得荣耀——所以为这份喜乐去争战，正是信心与顺服。"
        ),
        "closing": "「在你面前有满足的喜乐，在你右手中有永远的福乐。」（诗16:11）",
        "ai_used": False,
    }

    if use_ai:
        enhanced = _ai_enhance(duty, result, settings)
        if enhanced:
            result.update(enhanced)
            result["ai_used"] = True
    return result


def build_prompt(duty: str, base: Dict[str, Any]) -> str:
    return (
        "你是一位温柔、以福音为中心的属灵陪伴者，深谙 John Piper《Desiring God 渴慕神》"
        "所讲的基督徒享乐主义（Christian Hedonism）：座右铭是『神在我们最以祂为乐时，最得着荣耀』。"
        "核心是——任何感觉像责任/苦差的属灵操练，其实是通往在神里喜乐的门，不是我们付给神的费用。"
        "请把用户觉得像苦差的操练，温柔重构成通往喜乐之路。中文，温暖不说教，"
        "先真诚承认那份felt burden，绝不定罪、不贴标签、不说『你不够属灵/信心不足』。\n"
        f"用户觉得像责任/苦差的操练：{duty}\n"
        "请输出 JSON：{\"acknowledge\":\"温柔承认那份重担\",\"reframe\":\"用基督徒享乐主义把它重构成 means to joy 的逻辑\","
        "\"fight_for_joy\":\"一个具体、可立刻实践的『为喜乐而争战』操练\",\"summary\":\"...\",\"closing\":\"一句经文\"}。"
    )


def _ai_enhance(duty: str, base: Dict[str, Any], settings: Any) -> Optional[Dict[str, Any]]:
    """可选 AI 增强：任何失败都回退（返回 None）。"""
    prompt = build_prompt(duty, base)
    raw = _call_ai(prompt, settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        out: Dict[str, Any] = {}
        for k in ("acknowledge", "reframe", "fight_for_joy", "summary", "closing"):
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
    """回流 formation：喜乐重构属于「渴望神+盼望+成长」，标注 desire/hope/growth 维度。"""
    if result.get("crisis"):
        return (["desire", "hope", "growth"], False, True, 2.0)
    return (["desire", "hope", "growth"], True, True, 5.0)
