"""
chinese_devotion_engine.py — 华人本土灵修 / Chinese Devotional Voices

补足「语料 100% 西方」的空白。收录倪柝声、王明道、唐崇荣、宋尚节四位华人属灵前辈的
**思想要义（中文摘述，非逐字引用，避免版权问题）**，按主题可检索，可按需要匹配默想。
每条都附教义分辨提示，导向「以圣经为最终准绳、阅读原著」。纯函数；确定性；内置危机检测。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

AUTHORS: List[Dict[str, str]] = [
    {"key": "nee", "name": "倪柝声", "en": "Watchman Nee",
     "brief": "强调与基督同死同活的经历、十字架对付己、凭信不凭感觉。",
     "caveat": "其「地方教会/召会」体系与灵魂-灵二分等部分教导在主流神学有争议；宜取其被广泛接纳的灵修洞见，凡事以圣经分辨。"},
    {"key": "wang", "name": "王明道", "en": "Wang Mingdao",
     "brief": "重生的真实、信仰不掺假、在患难逼迫中持守到底。",
     "caveat": "立场保守独立、无重大争议；其受苦中的忠贞见证尤可取法。"},
    {"key": "tong", "name": "唐崇荣", "en": "Stephen Tong",
     "brief": "归正神学、神的主权与荣耀、理性与信仰并重、良心与真理。",
     "caveat": "归正宗立场鲜明；取其对神主权与真理的强调。"},
    {"key": "sung", "name": "宋尚节", "en": "John Sung",
     "brief": "认罪悔改、复兴、火热布道、追求圣洁。",
     "caveat": "奋兴派风格强烈；取其认罪与复兴的真诚，避免情绪主义的偏颇。"},
]
AUTHOR_INDEX = {a["key"]: a for a in AUTHORS}

# insight 为「中文摘述」——用本引擎自己的话概述该作者思想，非原文引用。
CORPUS: List[Dict[str, Any]] = [
    {"author": "nee", "theme": "与基督联合", "tags": ["联合", "同死", "同活", "旧人", "身份"],
     "insight": "得胜的秘诀不在于你多努力，而在于看见一个已成的事实：你的旧人已经与基督同钉十字架，"
                "你现今是与祂一同复活的人。不是「治死」到死，而是「算」自己已经死了、向神活着。",
     "ref": "罗6:11", "text": "这样，你们向罪也当看自己是死的；向神，在基督耶稣里，却当看自己是活的。"},
    {"author": "nee", "theme": "凭信不凭感觉", "tags": ["感觉", "信心", "情绪", "确据"],
     "insight": "属灵生命不建立在起伏的感觉上，而建立在神所说的事实上。感觉像海面的浪，事实像海底的磐石；"
                "当感觉退去，神的话仍然站立。信，是抓住事实过于抓住感受。",
     "ref": "林后5:7", "text": "因我们行事为人是凭着信心，不是凭着眼见。"},
    {"author": "nee", "theme": "十字架对付己", "tags": ["舍己", "十字架", "己", "破碎"],
     "insight": "十字架的工作，是把「己」带到一个了结的地方——不是压抑，而是让那颗只为自己而活的心"
                "被主破碎，好让基督的生命从里面流出来。破碎的外壳，是为了释放里面的香气。",
     "ref": "约12:24", "text": "一粒麦子若不落在地里死了，仍旧是一粒；若是死了，就结出许多子粒来。"},
    {"author": "wang", "theme": "重生的真实", "tags": ["重生", "真实", "假冒", "新生命"],
     "insight": "许多人有宗教的外壳，却没有重生的实际。真信仰不是改良行为，而是从上头来的新生命；"
                "重生的人会有真实的改变——恨恶从前所爱的罪，爱慕从前所轻看的圣洁。",
     "ref": "约3:3", "text": "人若不重生，就不能见神的国。"},
    {"author": "wang", "theme": "受苦中的忠贞", "tags": ["受苦", "逼迫", "忠心", "站立", "患难"],
     "insight": "为真理受苦不是失败，而是与主同行的记号。风暴不能动摇一个把根扎在基督里的人；"
                "宁可站着死，绝不跪着生——因为那位为我们受死的主，值得我们至死忠心。",
     "ref": "启2:10", "text": "你务要至死忠心，我就赐给你那生命的冠冕。"},
    {"author": "tong", "theme": "神的主权与荣耀", "tags": ["主权", "荣耀", "神本", "敬拜"],
     "insight": "人生一切问题的根源，是把自己放在神的位置上；一切医治的起点，是让神回到宝座上。"
                "当我们看见神的主权与荣耀何等大，自我就缩小到它本该有的尺寸，敬拜便成了最自然的回应。",
     "ref": "罗11:36", "text": "因为万有都是本于祂，倚靠祂，归于祂。愿荣耀归给祂。"},
    {"author": "tong", "theme": "理性与信仰", "tags": ["理性", "真理", "思想", "良心"],
     "insight": "信仰不是反理性的跳跃，而是理性在真理面前的降服。神既是真理的源头，认真思想与真诚相信"
                "并不冲突；逃避思考的信仰是懒惰，拒绝降服的理性是骄傲——真门徒两样都不要。",
     "ref": "太22:37", "text": "你要尽心、尽性、尽意爱主你的神。"},
    {"author": "sung", "theme": "认罪与复兴", "tags": ["认罪", "复兴", "悔改", "洁净"],
     "insight": "复兴从来不是先有热闹，而是先有认罪。当人肯诚实地在神面前把罪一件件挖出来、对付干净，"
                "圣灵的火才落下来。别求感动，先求洁净；心一干净，喜乐与能力自然涌流。",
     "ref": "诗51:10", "text": "神啊，求你为我造清洁的心，使我里面重新有正直的灵。"},
]

CRISIS_WORDS = [
    "自杀", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死", "死了算了",
    "伤害自己", "撑不下去了", "没有意义活着", "想消失",
]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = (
    "我听见你心里很沉重。先温柔地说：如果你有伤害自己的念头，请现在就联系你信任的人或当地"
    "心理危机热线——你值得此刻有人真实地陪着你。（本功能不替代专业帮助。）"
)

DISCLAIMER = ("以下为各位前辈思想的中文摘述（非逐字引用，以避免版权问题）。"
              "请以圣经为最终准绳，并鼓励阅读原著；对有争议的体系，持守分辨。")


def meta() -> Dict[str, Any]:
    return {
        "authors": AUTHORS,
        "themes": sorted({c["theme"] for c in CORPUS}),
        "count": len(CORPUS),
        "principle": "华人属灵传统里也有深井。取其被圣经印证的洞见，配上分辨，滋养今天的你。",
        "disclaimer": DISCLAIMER,
    }


def _entry(c: Dict[str, Any]) -> Dict[str, Any]:
    a = AUTHOR_INDEX.get(c["author"], {})
    return {
        "author": a.get("name", c["author"]), "author_en": a.get("en", ""),
        "theme": c["theme"], "insight": c["insight"],
        "scripture": {"ref": c["ref"], "text": c["text"]},
        "caveat": a.get("caveat", ""),
    }


def search(query: str = "", author: Optional[str] = None, limit: int = 8) -> Dict[str, Any]:
    q = (query or "").strip()
    hits = []
    for c in CORPUS:
        if author and c["author"] != author:
            continue
        score = 0
        if q:
            if q in c["theme"]:
                score += 3
            score += sum(1 for tag in c["tags"] if tag in q or q in tag)
            if q in c["insight"]:
                score += 1
        else:
            score = 1
        if score > 0:
            hits.append((score, c))
    hits.sort(key=lambda x: -x[0])
    return {"disclaimer": DISCLAIMER, "results": [_entry(c) for _, c in hits[:limit]]}


def meditate(need: str = "", *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    crisis = _detect_crisis(need or "")
    found = search(need, limit=1)["results"]
    entry = found[0] if found else _entry(CORPUS[0])
    result = {
        "crisis": crisis,
        "crisis_note": CRISIS_NOTE if crisis else "",
        "entry": entry,
        "reflection": "把这段要义带到神面前，问：这在我身上具体意味着什么？我愿意回应哪一步？",
        "prayer": "主啊，谢谢你在华人教会中兴起忠心的仆人。求你借着这真理光照我，也叫我以你的话为准绳。",
        "disclaimer": DISCLAIMER,
        "ai_used": False,
    }
    return result


def formation_signal(result: Dict[str, Any]):
    if result.get("crisis"):
        return (["hope", "growth"], False, True, 2.0)
    return (["hope", "growth"], True, True, 4.0)
