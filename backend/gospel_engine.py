"""
gospel_engine.py — 福音诊断室 / Gospel Diagnostic Lab（双引擎核心）

把「司布真 Heart Engine（看见基督）」与「钟马田 Mind Engine（福音诊断）」合成一个
完整循环：经历 → 情绪 → 欲望 → 恐惧 → 偶像 → 不信 → 福音真理 → 基督 → 祷告 → 行动。

  钟马田引擎：症状不是问题；情绪揭示信念，信念揭示偶像，偶像揭示不信，福音对付不信。
  司布真引擎：从处境到基督、从自我到基督、从焦虑到信靠、从亏欠到十架。

纯函数 + 确定性，保证零依赖可跑；配置 LLM 时用两位的「技能 Prompt」增强，失败回退。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# 功能性偶像（与 idolatry_engine 对齐，便于回流）
IDOLS: Dict[str, Dict[str, str]] = {
    "control":      {"name": "控制 / 掌控", "pattern": "fear"},
    "approval":     {"name": "认可 / 被看见", "pattern": "pride"},
    "comfort":      {"name": "舒适 / 安逸", "pattern": "fear"},
    "security":     {"name": "安全感 / 保障", "pattern": "fear"},
    "success":      {"name": "成就 / 表现", "pattern": "pride"},
    "relationship": {"name": "关系 / 某个人", "pattern": "relational"},
}

# 关键词 → 偶像（在「想要」「害怕」文本里匹配）
_IDOL_KEYWORDS = {
    "control": ["控制", "掌控", "确定", "不确定", "失控", "计划", "安排", "未知"],
    "approval": ["认可", "评价", "看法", "否定", "拒绝", "面子", "被看见", "称赞", "批评"],
    "comfort": ["舒适", "轻松", "麻烦", "代价", "逃避", "安逸", "懒", "回避"],
    "security": ["安全", "保障", "钱", "财务", "失业", "贫穷", "生病", "未来", "失去", "稳定"],
    "success": ["成功", "成就", "表现", "失败", "落后", "比较", "输", "优秀", "证明"],
    "relationship": ["关系", "分手", "孤独", "抛弃", "离开", "婚姻", "恋", "被爱", "陪伴"],
}

# 情绪关键词
_EMO_KEYWORDS = {
    "焦虑": ["焦虑", "紧张", "不安", "担心", "慌"],
    "恐惧": ["恐惧", "害怕", "怕", "惧"],
    "愤怒": ["愤怒", "生气", "恼", "气", "委屈"],
    "羞耻": ["羞耻", "丢脸", "自卑", "没用", "没价值"],
    "悲伤": ["悲伤", "难过", "失落", "沮丧", "哭"],
    "嫉妒": ["嫉妒", "羡慕", "不甘", "比"],
    "空虚": ["空虚", "麻木", "无意义", "迷茫"],
}

# 每个偶像：不信的谎言 + 福音真理 + 经文 + 默想 + 祷告 + 行动
_REMEDY: Dict[str, Dict[str, Any]] = {
    "control": {
        "unbelief": "我不相信神在掌权，所以必须自己抓住一切。",
        "gospel": "神坐在宝座上掌管万有，连你的头发都数过。你可以松手，因为祂从不松手。",
        "scripture": {"ref": "箴3:5-6", "text": "你要专心仰赖耶和华，不可倚靠自己的聪明……他必指引你的路。"},
        "meditation": "亲爱的，你不是宇宙的支撑者——那位托住万有的，是被钉痕的手。今夜可以安睡，因为掌权的不是你的焦虑，而是你的天父。",
        "prayer": "主啊，我一直想替你掌管未来。求你帮助我把紧握的手张开，把结果交还给你。",
        "action": "写下你最想控制的三件事，逐一在祷告中交给神：「这件事我交给你。」",
    },
    "approval": {
        "unbelief": "我不相信神已完全接纳我，所以必须靠别人的认可证明自己。",
        "gospel": "在基督里，你已被天父称义、全然接纳。你不是为被爱而表现，而是因被爱而活。",
        "scripture": {"ref": "加1:10", "text": "我现在是要得人的心呢？还是要得神的心呢？"},
        "meditation": "你苦苦寻求的那一句「你够好了」，十字架已经说出。父神看你如同看祂的爱子——不是因你的表现，而是因基督的功劳。",
        "prayer": "主啊，我太在意别人的眼光。求你让我安息在你对我的悦纳里，胜过一切人的称赞或否定。",
        "action": "今天有一个时刻，刻意不去解释、不去争取认可，让它安然过去。",
    },
    "comfort": {
        "unbelief": "我不相信神够好、够满足，所以用舒适来麻醉自己。",
        "gospel": "基督是活水的泉源，唯有祂能真正解你心里的渴，胜过一切短暂的安逸。",
        "scripture": {"ref": "约4:14", "text": "人若喝我所赐的水，就永远不渴。"},
        "meditation": "舒适像盐水，越喝越渴。但有一位站着高声说：到我这里来喝。祂要给的不是麻醉，是真正的安息。",
        "prayer": "主啊，我常用舒适逃避你的呼召。求你让我尝到你的甘甜，胜过一切廉价的安慰。",
        "action": "今天选一件你一直在回避、却该做的难事，迈出第一步。",
    },
    "security": {
        "unbelief": "我不相信天父会供应，所以把安全感建立在拥有上。",
        "gospel": "你的天父知道你一切所需；祂连麻雀都看顾，何况是你。你的产业存在天上，不会朽坏。",
        "scripture": {"ref": "太6:31-33", "text": "你们要先求他的国和他的义，这些东西都要加给你们了。"},
        "meditation": "数算天上的飞鸟，它们不种不收，天父尚且养活。你比飞鸟贵重得多。真正的保障不在银行的数字，而在那位永不改变的供应者。",
        "prayer": "主啊，我把安全感放在了拥有上。求你成为我真正的保障，叫我在不确定中仍然安稳。",
        "action": "本周做一次「不计代价」的奉献或施予，小小地松开对掌控的手。",
    },
    "success": {
        "unbelief": "我不相信我在基督里已被爱，所以必须用成就赢得价值。",
        "gospel": "你的价值不在成就，而在十字架——基督为你舍命，已宣告你是无价的。",
        "scripture": {"ref": "腓3:8", "text": "我也将万事当作有损的，因我以认识我主基督耶稣为至宝。"},
        "meditation": "若你的名字写在生命册上，便不必把它刻在世界的奖杯上。成就会褪色，但「这是我的爱子，我所喜悦的」永不改变。",
        "prayer": "主啊，我用成就证明自己，活得好累。求你让我安息在你已成就的恩典里。",
        "action": "今天做一件「无人看见、无回报」的善事，练习在隐密中被神看见。",
    },
    "relationship": {
        "unbelief": "我不相信神是我终极的满足，所以把某人放在只有神能坐的位置。",
        "gospel": "除神以外，在地上你别无所慕。祂的爱永不离弃，是一切人间之爱的源头与归宿。",
        "scripture": {"ref": "诗73:25-26", "text": "除你以外，在天上我有谁呢？……但神是我心里的力量，又是我的福分，直到永远。"},
        "meditation": "人的爱会枯竭，会离开，会让你失望——不是因为爱错了人，而是因为没有人能背负神的位置。把救主的座位还给救主，你才能真正自由地去爱人。",
        "prayer": "主啊，我把一个人放在了你的位置上。求你先得着我的心，让我从你的爱里去爱他/她。",
        "action": "为这段关系祷告：「我爱他/她，但我不靠他/她活着。」",
    },
}

CORE_QUESTIONS = [
    {"key": "event",   "q": "发生了什么事？", "ph": "客观地描述这件事，像在跟朋友讲…"},
    {"key": "feeling", "q": "你感受到什么？", "ph": "焦虑、愤怒、羞耻、悲伤、空虚…"},
    {"key": "want",    "q": "你真正想要的是什么？", "ph": "在这感受底下，你渴望得到 / 留住什么？"},
    {"key": "fear",    "q": "你最害怕失去什么？", "ph": "如果它没了，你会崩溃的是什么？"},
    {"key": "belief",  "q": "这让你相信了关于神 / 自己的什么？", "ph": "诚实地写，哪怕是「神不管我」…"},
]


def _match(text: str, kw_map: Dict[str, List[str]]) -> Optional[str]:
    t = text or ""
    best, score = None, 0
    for key, kws in kw_map.items():
        c = sum(1 for k in kws if k in t)
        if c > score:
            best, score = key, c
    return best


def diagnose(inputs: Dict[str, str]) -> Dict[str, Any]:
    """确定性双引擎诊断 → 属灵病历。"""
    event = (inputs.get("event") or "").strip()
    feeling = (inputs.get("feeling") or "").strip()
    want = (inputs.get("want") or "").strip()
    fear = (inputs.get("fear") or "").strip()
    belief = (inputs.get("belief") or "").strip()

    emotion = _match(feeling, _EMO_KEYWORDS) or "说不清的重担"
    idol = _match(want + " " + fear + " " + feeling + " " + event, _IDOL_KEYWORDS) or "security"
    rem = _REMEDY[idol]
    idol_name = IDOLS[idol]["name"]

    summary = (f"你以为问题是「{emotion}」，但钟马田会说：往下看。"
               f"在它底下，是把「{idol_name}」放到了只有神能坐的位置；"
               f"再往深处，是一个不信——{rem['unbelief']} "
               f"而福音正是对付这不信的：{rem['gospel']}")

    return {
        "emotion": emotion,
        "desire": want or "（未写）",
        "fear_named": fear or "（未写）",
        "idol_type": idol,
        "idol_name": idol_name,
        "unbelief": rem["unbelief"],
        "gospel_truth": rem["gospel"],
        "scripture": rem["scripture"],
        "meditation": rem["meditation"],
        "prayer": rem["prayer"],
        "action": rem["action"],
        "summary": summary,
        "source": "deterministic",
    }


# ── AI 增强：用司布真 + 钟马田技能 Prompt ──────────────────────────────────────
SYSTEM_PROMPT = (
    "你按照马丁·钟马田(Martyn Lloyd-Jones)的福音诊断法 + 司布真(C.H. Spurgeon)的牧养传统运作。\n"
    "钟马田原则：症状不是问题；情绪揭示信念，信念揭示偶像，偶像揭示不信，福音对付不信。"
    "诊断链：行为→情绪→欲望→恐惧→偶像→不信→福音真理。绝不停在情绪或处境，绝不肤浅安慰，要挖到根。\n"
    "司布真原则：永远从处境引向基督、从自我引向基督、从焦虑引向信靠、从亏欠引向十架、从软弱引向恩典。"
    "温柔、敬虔、以基督为中心；绝不只给心理建议，绝不让人停留在自己身上，绝不在没有指向基督前结束。\n"
    "语气温柔、不定罪、不制造羞耻。只输出一个 JSON 对象，不要任何额外文字。"
)
_JSON_SHAPE = (
    '{"emotion":"主要情绪","idol_type":"control|approval|comfort|security|success|relationship",'
    '"idol_name":"中文偶像名","unbelief":"底层的不信谎言","gospel_truth":"福音如何对付这不信",'
    '"scripture":{"ref":"出处","text":"经文"},"meditation":"司布真式默想(120-200字,温暖,以基督为中心)",'
    '"prayer":"一段简短祷告","action":"今天一个具体的信心行动","summary":"一句话点出根源并给出福音盼望"}'
)


def build_prompt(inputs: Dict[str, str]) -> List[Dict[str, str]]:
    user = (
        f"发生的事：{inputs.get('event','')}\n"
        f"感受：{inputs.get('feeling','')}\n"
        f"想要：{inputs.get('want','')}\n"
        f"害怕失去：{inputs.get('fear','')}\n"
        f"由此相信（关于神/自己）：{inputs.get('belief','')}\n\n"
        "先用钟马田的方式挖到偶像与不信，再用司布真的方式把我带到基督面前。"
        f"严格按此 JSON 输出：\n{_JSON_SHAPE}"
    )
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


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


def analyze(inputs: Dict[str, str], settings: Any = None, use_ai: bool = True) -> Dict[str, Any]:
    fallback = diagnose(inputs)
    if not use_ai:
        return fallback
    try:
        # 复用 waiting_engine 已实现的 OpenAI 兼容 Provider
        try:
            from backend.waiting_engine import call_ai_provider
        except Exception:
            from waiting_engine import call_ai_provider
        ai = call_ai_provider(build_prompt(inputs), settings=settings)
    except Exception:
        ai = None
    if not ai:
        return fallback
    out = dict(fallback)
    for k in ("emotion", "unbelief", "gospel_truth", "meditation", "prayer", "action", "summary"):
        if ai.get(k):
            out[k] = str(ai[k])
    it = ai.get("idol_type")
    if it in IDOLS:
        out["idol_type"] = it
        out["idol_name"] = IDOLS[it]["name"]
    if ai.get("idol_name"):
        out["idol_name"] = str(ai["idol_name"])
    sc = ai.get("scripture")
    if isinstance(sc, dict) and sc.get("text"):
        out["scripture"] = {"ref": str(sc.get("ref", "")), "text": str(sc["text"])}
    out["source"] = "ai"
    return out


def formation_signal(result: Dict[str, Any]):
    """福音诊断 = 看见偶像 + 应用福音 → 轻推相应倾向但 loop_broken（福音对付）。"""
    idol = result.get("idol_type")
    pat = IDOLS.get(idol, {}).get("pattern", "fear")
    return ([pat, "growth"], True, True, 5.0)


def meta() -> Dict[str, Any]:
    return {"core_questions": CORE_QUESTIONS,
            "idols": [{"type": k, **v} for k, v in IDOLS.items()]}
