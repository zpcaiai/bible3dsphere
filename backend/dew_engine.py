"""
dew_engine.py — 清晨甘露 / Morning Dew（司布真式每日默想）

每日生成一篇以基督为中心、温暖、敬虔、牧养的默想：
  经文 → 默想 → 基督连结 → 反思问题 → 祷告 → 今日信心行动。
tier=5/10/15 控制篇幅。确定性版（经文池 + 主题模板）零依赖可跑；配 LLM 时用司布真
默想技能 Prompt 生成全文，失败回退。
"""
from __future__ import annotations

import json
import re
from datetime import date
from typing import Any, Dict, List, Optional

# 经文池（出处 / 经文 / 主题）
VERSES: List[Dict[str, str]] = [
    {"ref": "诗46:10", "text": "你们要休息，要知道我是神。", "theme": "trust"},
    {"ref": "太11:28", "text": "凡劳苦担重担的人，可以到我这里来，我就使你们得安息。", "theme": "communion"},
    {"ref": "哀3:22-23", "text": "我们不致消灭，是出于耶和华诸般的慈爱……每早晨这都是新的。", "theme": "grace"},
    {"ref": "赛41:10", "text": "你不要害怕，因为我与你同在……我必坚固你，我必帮助你。", "theme": "trust"},
    {"ref": "约15:5", "text": "我是葡萄树，你们是枝子……离了我，你们就不能做什么。", "theme": "communion"},
    {"ref": "罗8:1", "text": "如今，那些在基督耶稣里的就不定罪了。", "theme": "cross"},
    {"ref": "诗23:1", "text": "耶和华是我的牧者，我必不致缺乏。", "theme": "trust"},
    {"ref": "林后12:9", "text": "我的恩典够你用的，因为我的能力是在人的软弱上显得完全。", "theme": "grace"},
    {"ref": "腓4:6-7", "text": "应当一无挂虑……神所赐出人意外的平安，必在基督耶稣里保守你们的心。", "theme": "trust"},
    {"ref": "约一3:1", "text": "你看父赐给我们是何等的慈爱，使我们得称为神的儿女。", "theme": "grace"},
    {"ref": "来12:2", "text": "仰望为我们信心创始成终的耶稣。", "theme": "cross"},
    {"ref": "诗27:4", "text": "有一件事，我曾求耶和华，我仍要寻求：就是一生……瞻仰他的荣美。", "theme": "communion"},
    {"ref": "赛40:31", "text": "但那等候耶和华的必从新得力……奔跑却不困倦，行走却不疲乏。", "theme": "perseverance"},
    {"ref": "诗103:12", "text": "东离西有多远，他叫我们的过犯离我们也有多远。", "theme": "cross"},
    {"ref": "番3:17", "text": "耶和华你的神……必因你欢欣喜乐……且因你喜乐而欢呼。", "theme": "grace"},
    {"ref": "约16:33", "text": "在世上你们有苦难，但你们可以放心，我已经胜了世界。", "theme": "perseverance"},
    {"ref": "诗63:1", "text": "神啊，你是我的神，我要切切地寻求你……我的心渴想你。", "theme": "communion"},
    {"ref": "弗2:8", "text": "你们得救是本乎恩，也因着信，这并不是出于自己，乃是神所赐的。", "theme": "cross"},
    {"ref": "诗30:5", "text": "一宿虽然有哭泣，早晨便必欢呼。", "theme": "grace"},
    {"ref": "箴3:5-6", "text": "你要专心仰赖耶和华……他必指引你的路。", "theme": "trust"},
    {"ref": "彼前5:7", "text": "你们要将一切的忧虑卸给神，因为他顾念你们。", "theme": "trust"},
    {"ref": "加2:20", "text": "现在活着的不再是我，乃是基督在我里面活着。", "theme": "cross"},
    {"ref": "诗34:8", "text": "你们要尝尝主恩的滋味，便知道他是美善。", "theme": "communion"},
    {"ref": "罗5:8", "text": "惟有基督在我们还作罪人的时候为我们死，神的爱就在此向我们显明了。", "theme": "cross"},
]

THEMES: Dict[str, Dict[str, str]] = {
    "trust": {
        "meditation": "亲爱的心哪，今晨不要先去丈量你的难处，先来仰望你的神。海浪再大，也漫不过那位踏浪而行的主。祂从不曾打盹，也从不曾失算。你所惧怕的明天，早已在祂手中。把重担放下吧——不是因为它轻，而是因为托住它的肩膀够宽。",
        "christ": "在客西马尼，主自己也尝过忧惧的滋味；祂懂你的颤抖。如今祂坐在父的右边，正为你代求。你信靠的不是一个抽象的旨意，而是一位带着钉痕、爱你到底的救主。",
        "reflection": "今天我最想自己掌控、最难交托的，是哪一件事？",
        "prayer": "主啊，我承认我常想替你掌权。今天，我把这件事交在你手中——你的意念高过我的意念，你的爱也深过我的惧怕。",
        "action": "写下你最挂虑的一件事，在它旁边写：「这件事我交给你。」",
    },
    "grace": {
        "meditation": "每一个早晨，神的怜悯都是新造的，像草上的甘露，未曾因昨日的失败而减少一分。你不必带着旧账来到祂面前；祂的恩典不是给配得的人，而是给来到的人。今天，你被爱，不是因为你做得够好，而是因为祂本为良善。",
        "christ": "这恩典有一个名字，叫耶稣。祂为你倾尽所有，使你这本是客旅的，得以称为神的儿女。十字架是恩典最大的证据：祂宁可舍命，也不愿失去你。",
        "reflection": "我是否还在用「表现」赚取神的爱，而不是安息在祂白白的恩典里？",
        "prayer": "主啊，谢谢你的怜悯每早晨都是新的。求你让我今天活在恩典里，不靠自己挣来，只靠你白白赐下。",
        "action": "今天对自己说三次：「我被爱，不是因为我够好，而是因为神是爱。」",
    },
    "cross": {
        "meditation": "来到十字架下，所有的控告都安静了。那挂在木头上的，担当了你一切的羞愧与亏欠。你的罪虽多，主的血更深;你的过犯虽真，赦免更真。不要再做自己的审判官——审判已经在各各他落槌，宣判是：赦了。",
        "christ": "基督替你受了该受的，又把祂配得的赐给你。如今在祂里面就不定罪了——这不是感觉，是事实，是用血写成的契约。你可以坦然无惧地来到施恩宝座前。",
        "reflection": "有什么旧的亏欠或羞愧，我还没有交在十字架前、领受赦免？",
        "prayer": "主耶稣，谢谢你为我受死。我领受你的赦免，不再活在控告里，而是活在你成就的恩典中。",
        "action": "把一件压在心里的亏欠，明确地交在十字架前，并领受「赦了」。",
    },
    "communion": {
        "meditation": "你的心是为神造的，离了祂便永不安歇。今晨不要急着做工，先来与主相交片刻。如鹿切慕溪水，让你的渴慕被祂自己满足。亲近祂不是又一项任务，而是回家。坐下来，安静地，被爱。",
        "christ": "主说，祂是葡萄树，你是枝子——你的生命之汁从祂而来。离了祂你什么都不能做，连在祂里面你便多结果子。今天，先连于祂，再去生活。",
        "reflection": "今天我能留出哪一小段时间，只是与神同在，不求什么？",
        "prayer": "主啊，我的心渴想你。求你成为我心里的满足，胜过一切我用来填补空虚的东西。",
        "action": "安静三分钟，什么都不求，只在神面前安息。",
    },
    "perseverance": {
        "meditation": "等候不是停滞，奔跑不是靠自己的力气。那等候耶和华的，必如鹰展翅上腾。你今日的疲乏，神都看见;祂不轻看将残的灯火、压伤的芦苇。再走一步，因为搀扶你的手从不松开。",
        "christ": "主自己曾因那摆在前面的喜乐，忍受了十字架。祂是信心创始成终的那一位——开始这工的，必亲自完成。你不是独自奔跑，祂在前头，也在你旁边。",
        "reflection": "在我快要放弃的地方，神可能正在塑造我什么？",
        "prayer": "主啊，我有些累了。求你叫我从新得力，在等候中仍然忠心，因为你必不撇下我。",
        "action": "在一件你想放弃的事上，今天只忠心地再走一小步。",
    },
}


def _pick(d: date) -> Dict[str, str]:
    doy = d.timetuple().tm_yday
    return VERSES[doy % len(VERSES)]


def deterministic(d: date, tier: int) -> Dict[str, Any]:
    v = _pick(d)
    th = THEMES[v["theme"]]
    out = {
        "date": d.isoformat(), "tier": tier,
        "scripture": {"ref": v["ref"], "text": v["text"]},
        "meditation": th["meditation"],
        "prayer": th["prayer"],
        "christ": th["christ"] if tier >= 10 else "",
        "reflection": th["reflection"] if tier >= 10 else "",
        "action": th["action"] if tier >= 15 else "",
        "source": "deterministic",
    }
    return out


# ── AI（司布真默想技能 Prompt）──────────────────────────────────────────────
def build_prompt(verse: Dict[str, str], tier: int) -> List[Dict[str, str]]:
    words = {5: "150-220", 10: "280-380", 15: "450-600"}.get(tier, "280-380")
    system = (
        "你按照司布真(C.H. Spurgeon)《清晨甘露》的传统写每日默想：以基督为中心、温暖、"
        "敬虔、牧养、实际。永远从处境引向基督，从自我引向基督，从焦虑引向信靠，从软弱引向恩典。"
        "用第二人称温柔地对读者说话。只输出一个 JSON 对象。"
    )
    user = (
        f"今日经文：{verse['ref']}「{verse['text']}」\n"
        f"请写一篇约 {words} 字的默想，严格按 JSON：\n"
        '{"meditation":"司布真式默想","christ":"基督连结(这经文如何指向基督)",'
        '"reflection":"一个反思问题","prayer":"一段简短祷告","action":"今日一个信心行动"}'
    )
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


def generate(d: date, tier: int, settings: Any = None, use_ai: bool = True) -> Dict[str, Any]:
    fallback = deterministic(d, tier)
    if not use_ai:
        return fallback
    try:
        try:
            from backend.waiting_engine import call_ai_provider
        except Exception:
            from waiting_engine import call_ai_provider
        ai = call_ai_provider(build_prompt(_pick(d), tier), settings=settings)
    except Exception:
        ai = None
    if not ai:
        return fallback
    out = dict(fallback)
    for k in ("meditation", "christ", "reflection", "prayer", "action"):
        if ai.get(k):
            out[k] = str(ai[k])
    # tier 篇幅控制：低 tier 不强行塞满
    if tier < 10:
        out["christ"] = out.get("christ", "") if tier >= 10 else ""
        out["reflection"] = ""
    if tier < 15:
        out["action"] = ""
    out["source"] = "ai"
    return out
