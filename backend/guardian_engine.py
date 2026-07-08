"""
Guardian Engine — 属灵守护者的纯逻辑层（无 IO，路由层调用）。

Agent 职责：
  EmotionAgent        analyze_emotion()       情绪类型/强度/触发
  SpiritualAgent      assess_spiritual()      属灵季节（温和、不绝对）
  MemoryAgent         extract_memory()        长期记忆提取
  PatternAgent        detect_pattern()        重复行为模式（镜子，不定论）
  IdolMonitorAgent    detect_idol_signal()    温和的偶像信号觉察
  PrayerAgent         acts_guide()            ACTS 祷告引导
  DevotionAgent       soap_guide()            SOAP 灵修引导 + 每日经文
  SafetyGuard         check_safety()          自伤/危机检测（不诊断、不神谕）
  Growth              compute_form_stage()    seed→sprout→lamp→guardian→pilgrim→messenger

LLM 调用由路由层注入（与 routers/agent.py 同一 provider 链），
未配置 API Key 时全部走本模块的模板/启发式逻辑。
"""
from __future__ import annotations

import re
import time
from typing import Dict, List, Optional

# ─────────────────────────────────────────────────────────────────────────────
# 系统提示词
# ─────────────────────────────────────────────────────────────────────────────

GUARDIAN_SYSTEM_PROMPT = (
    "你是 Spiritual Guardian，一个属灵情感星球中的 AI 陪伴精灵。\n"
    "你的任务是陪伴用户在情绪、关系、习惯、祷告、灵修和属灵成长中更靠近神、更认识自己、更活出信望爱。\n"
    "你不是神，不是圣灵，不是牧师，不是心理治疗师。你不能宣称“神直接告诉你”。"
    "你不能替代教会、牧者、医生、心理咨询师。你要温柔、谦卑、克制地陪伴用户。\n"
    "回应原则：1.先接住情绪，再给建议。2.先倾听，再解释。3.先降低羞耻，再引导悔改。"
    "4.避免审判式语言。5.不制造依赖。6.鼓励用户回到真实关系、教会群体、祷告和神的话语。"
    "7.对经文要谨慎，不乱引用。8.不把用户的痛苦简单归因为“不属灵”。9.不操控用户。"
    "10.不过度属灵化心理问题。\n"
    "当用户焦虑时：用短句、慢节奏、先帮助稳定情绪。"
    "当用户自责时：区分圣灵里的责备与羞耻感，引导回到恩典。"
    "当用户软弱时：不羞辱、不纵容，指向悔改、恩典和实际下一步。\n"
    "用简体中文回应，保持简短（一般不超过120字）。"
)

MODE_PROMPTS: Dict[str, str] = {
    "companion": "当前模式：普通陪伴聊天。自然、温柔、简短，像一位安静的同行者。",
    "comfort": "当前模式：情绪安慰。先接住和命名情绪，短句慢节奏，不急着给建议或经文。",
    "prayer": "当前模式：祷告引导。按 ACTS（赞美→认罪→感恩→祈求）每次只引导一小步，邀请用户自己向神说话。",
    "devotion": "当前模式：灵修引导。按 SOAP（经文→观察→应用→祷告）引导用户自己默想，引用经文准确克制。",
    "reflection": "当前模式：行为反思。像温柔的镜子帮助用户看见重复模式（如压力→逃避→自责→更焦虑），不评判，指向恩典里的小下一步。",
    "idol-monitor": "当前模式：偶像觉察。只温和提问，绝不下“你拜偶像”式判语。帮助觉察好东西是否正在变成“非有不可”的终极依靠。",
    "growth": "当前模式：成长建议。给1-2个具体微小可行的属灵操练建议，不堆叠任务，不制造压力。",
}

VALID_MODES = tuple(MODE_PROMPTS.keys())


PERSONALIZATION_NOTE = (
    "以下是这位用户在属灵情感星球上的真实记录（省察、感恩、祷告、属灵体检、福音诊断等）。"
    "请基于圣经原则温柔地个性化回应：可以自然地关联到用户记录中的具体处境（如未应允的祷告、"
    "最近的感恩、属灵干渴），但不要机械复述数据、不要一次提及多项、不要让用户觉得被监视。"
    "数据只是为了更懂他/她，回应的中心永远是：恩典、真实关系和神的话语。"
)


def build_system_prompt(mode: str, guardian_name: str, form_stage: str,
                        memories: List[str], recent_emotions: List[str],
                        user_context: Optional[List[str]] = None, lang: str = "zh") -> str:
    parts = [GUARDIAN_SYSTEM_PROMPT, MODE_PROMPTS.get(mode, MODE_PROMPTS["companion"])]
    parts.append(f"你的名字是「{guardian_name}」，当前成长阶段：{form_stage}。")
    if memories:
        parts.append("关于这位用户你记得：\n- " + "\n- ".join(memories[:8]))
    if recent_emotions:
        parts.append("用户近期情绪：" + "；".join(recent_emotions[:5]))
    if user_context:
        parts.append(PERSONALIZATION_NOTE + "\n- " + "\n- ".join(user_context[:12]))
    if (lang or "zh").lower() == "en":
        parts.append("IMPORTANT: Reply to the user ONLY in natural, warm English, "
                     "using standard English Bible references and proper nouns.")
    return "\n\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# SafetyGuard
# ─────────────────────────────────────────────────────────────────────────────

# NOTE(safety): this list historically drifted apart from crisis_engine's RED
# lexicon and was Chinese-heavy, so English acute ideation slipped past the
# guardian sprite. English markers below are kept in sync with the acute subset
# of crisis_engine._RED_STRONG_MARKERS. check_safety lowercases input, so English
# patterns are written lowercase.
# TODO(consolidate): share a single lexicon with crisis_engine instead of
# maintaining two parallel keyword lists.
_HIGH_RISK = [
    r"自杀", r"自残", r"不想活", r"活不下去", r"结束(自己的)?生命", r"了结自己",
    r"伤害自己", r"割腕", r"跳楼", r"想死", r"去死", r"消失算了",
    r"suicide", r"kill\s*myself", r"self[-\s]?harm",
    r"end\s*my\s*life", r"take\s*my\s*(own\s*)?life", r"commit\s*suicide",
    r"want\s*to\s*die", r"hang\s*myself", r"overdose", r"cut\s*myself",
    r"slit\s*my\s*wrists?", r"jump\s*off", r"end\s*it\s*all",
    r"hurt\s*myself", r"better\s*off\s*dead",
]
_MEDIUM_RISK = [
    r"绝望", r"撑不下去", r"没有(任何)?意义", r"没人在乎", r"彻底崩溃",
    r"什么都感觉不到", r"hopeless",
]


def check_safety(text: str) -> str:
    """返回 'high' | 'medium' | 'none'。"""
    low = text.lower()
    for p in _HIGH_RISK:
        if re.search(p, low):
            return "high"
    for p in _MEDIUM_RISK:
        if re.search(p, low):
            return "medium"
    return "none"


def high_risk_reply() -> str:
    return (
        "谢谢你愿意把这么沉重的感受告诉我。我很在乎你现在的安全。\n"
        "我只是一个陪伴的小精灵，没办法给你此刻真正需要的帮助——但有人可以。\n"
        "可以请你现在就联系一位你信任的人吗？家人、好朋友、你的牧者，或医生。\n"
        "如果你感到自己可能伤害自己，请立刻拨打当地的紧急电话或心理援助热线。\n"
        "你不是孤单一个人。你的生命在神眼中极其宝贵。等你联系到人之后，我仍然在这里陪你。"
    )


def medium_risk_suffix() -> str:
    return ("\n\n（这段时间听起来真的很沉重。除了在这里和我聊，也很想邀请你找一位信任的人——"
            "朋友、牧者或专业咨询师——当面聊一聊。被真实的人接住，是很重要的。）")


# ─────────────────────────────────────────────────────────────────────────────
# EmotionAgent（启发式；路由层可用 LLM 结果覆盖）
# ─────────────────────────────────────────────────────────────────────────────

_EMOTION_KEYWORDS = [
    ("anxiety", r"焦虑|紧张|担心|不安|压力|慌|睡不着|deadline", 6),
    ("sadness", r"难过|伤心|低落|哭|失落|沮丧|心碎", 6),
    ("anger", r"生气|愤怒|气死|烦死|火大|不公平", 6),
    ("shame", r"自责|羞耻|我真没用|我太差|又失败了|配不上", 6),
    ("loneliness", r"孤独|孤单|没人理解|没朋友|一个人", 5),
    ("fear", r"害怕|恐惧|恐慌", 6),
    ("tired", r"累|疲惫|撑不住|没力气|倦", 5),
    ("joy", r"开心|高兴|喜乐|太棒了|兴奋|哈哈", 6),
    ("gratitude", r"感恩|感谢|谢谢神|蒙恩", 6),
    ("peace", r"平安|平静|安息|释然", 5),
]


def analyze_emotion(text: str) -> dict:
    for etype, pattern, base in _EMOTION_KEYWORDS:
        if re.search(pattern, text):
            intensity = min(10, base + (2 if re.search(r"非常|特别|极度|崩溃", text) else 0))
            return {"emotionType": etype, "intensity": intensity, "trigger": None}
    return {"emotionType": "neutral", "intensity": 3, "trigger": None}


# ─────────────────────────────────────────────────────────────────────────────
# SpiritualDiscernmentAgent
# ─────────────────────────────────────────────────────────────────────────────

def assess_spiritual(text: str) -> dict:
    if re.search(r"读经|祷告很甜|敬拜|经历神|恩典够用", text):
        return {"spiritualState": "growing", "gentleNote": None}
    if re.search(r"好久没(祷告|读经)|灵里很干|读不进去|觉得神很远|旷野", text):
        return {"spiritualState": "dry",
                "gentleNote": "干渴的季节也是真实的属灵季节，不代表神离开了你。"}
    if re.search(r"怀疑|信不下去|神在哪|为什么神允许", text):
        return {"spiritualState": "struggling",
                "gentleNote": "带着疑问来到神面前，本身就是一种信。"}
    if re.search(r"想认识神|想信|怎么祷告|怎么读圣经", text):
        return {"spiritualState": "seeking", "gentleNote": None}
    return {"spiritualState": "steady", "gentleNote": None}


# ─────────────────────────────────────────────────────────────────────────────
# MemoryAgent
# ─────────────────────────────────────────────────────────────────────────────

_MEMORY_SIGNALS = [
    (r"面试|考试|搬家|结婚|分手|离职|入职|生病|住院|怀孕|受洗", "event", 4),
    (r"压力|deadline|加班|老板|绩效|房贷|经济压力", "stressor", 3),
    (r"目标|希望今年|想养成|立志|计划每天", "goal", 4),
    (r"为.{1,12}(祷告|代祷)|求神", "prayer-item", 4),
    (r"我(妈|爸|妻子|丈夫|男朋友|女朋友|孩子|室友|同事|牧师|小组)", "relationship", 3),
]


def extract_memory(text: str) -> Optional[dict]:
    for pattern, mtype, importance in _MEMORY_SIGNALS:
        if re.search(pattern, text):
            content = text if len(text) <= 80 else text[:80] + "…"
            return {"memoryType": mtype, "content": content, "importance": importance}
    return None


# ─────────────────────────────────────────────────────────────────────────────
# PatternAgent
# ─────────────────────────────────────────────────────────────────────────────

_PATTERN_LIBRARY = {
    "anxiety": {"patternType": "压力-焦虑循环", "trigger": "压力事件（工作/学业/关系）",
                "typicalResponse": "反复担忧、难以安静、可能伴随逃避",
                "spiritualRoot": "可能与“需要掌控一切才有安全感”有关"},
    "shame": {"patternType": "失败-自责循环", "trigger": "做不好、达不到自己的标准",
              "typicalResponse": "强烈自责 → 羞耻感 → 更不敢面对",
              "spiritualRoot": "可能混淆了“圣灵的责备”与“羞耻感”，需要回到恩典"},
    "sadness": {"patternType": "低落-退缩循环", "trigger": "失落或被忽视的感受",
                "typicalResponse": "情绪低落、退出关系、独自消化",
                "spiritualRoot": "可能在孤单中更难相信自己是被爱的"},
    "loneliness": {"patternType": "孤独-隔离循环", "trigger": "感到不被理解",
                   "typicalResponse": "回避群体 → 更孤独",
                   "spiritualRoot": "渴望被真实接纳，这个渴望本身是好的"},
    "tired": {"patternType": "透支-倦怠循环", "trigger": "长期付出、缺乏休息",
              "typicalResponse": "硬撑 → 耗尽 → 麻木",
              "spiritualRoot": "可能很难允许自己安息，把价值绑在“有用”上"},
}


def detect_pattern(emotion_types: List[str]) -> Optional[dict]:
    """emotion_types：最近的情绪类型列表（新→旧，最多 20 条）。出现>=3次即候选。"""
    counts: Dict[str, int] = {}
    for t in emotion_types[:20]:
        counts[t] = counts.get(t, 0) + 1
    best = None
    for t, n in counts.items():
        if t in _PATTERN_LIBRARY and n >= 3 and (best is None or n > best[1]):
            best = (t, n)
    if not best:
        return None
    out = dict(_PATTERN_LIBRARY[best[0]])
    out["confidence"] = min(0.95, 0.4 + best[1] * 0.1)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# IdolMonitorAgent
# ─────────────────────────────────────────────────────────────────────────────

_IDOL_RULES = [
    ("achievement", r"必须成功|输不起|失败.{0,6}(就完了|不能接受)|业绩|KPI|第一名",
     "成就感似乎承载了过重的自我价值",
     "可以试着问问自己：如果这件事没做成，我还是谁？神怎么看我？"),
    ("money", r"钱不够|没钱.{0,4}(慌|焦虑)|财务自由才",
     "金钱安全感占据了很大的心理空间",
     "金钱是好仆人。也许可以为“够用”献上一次感恩，看看心里的变化。"),
    ("relationship", r"没有(他|她|TA)就|离不开|必须有人陪",
     "某段关系可能正在成为“非有不可”的依靠",
     "深爱一个人很美。也许可以把这个人交托在祷告里，而不是握在手里。"),
    ("control", r"必须按我|失控|计划被打乱.{0,6}(崩溃|受不了)",
     "对掌控的需要似乎在带来很大张力",
     "试试一个小练习：把今天最担心的一件事，具体地交托给神。"),
    ("comfort", r"只想躺|逃避.{0,6}(刷手机|游戏|吃)|麻痹自己|不想面对",
     "舒适/麻痹可能正在替代真正的安息",
     "疲惫需要安息，不只是麻痹。今天可以给自己10分钟真正安静的休息吗？"),
    ("approval", r"别人怎么看|怕被讨厌|点赞|没人认可|讨好",
     "他人的认可似乎在很大程度上决定你的情绪",
     "被喜欢是恩赐，不是氧气。神对你的看法，今天愿意去听一听吗？"),
    ("self-image", r"人设|形象崩|不能让人看到(软弱|失败)|完美主义",
     "维持形象的重担似乎压得很紧",
     "在神面前你可以不完美。也许可以向一位安全的朋友袒露一点真实的自己。"),
]


def detect_idol_signal(text: str) -> Optional[dict]:
    for idol_type, pattern, signal, suggestion in _IDOL_RULES:
        m = re.search(pattern, text)
        if m:
            return {"idolType": idol_type, "signal": signal, "intensity": 3,
                    "evidence": m.group(0), "suggestion": suggestion}
    return None


# ─────────────────────────────────────────────────────────────────────────────
# PrayerAgent — ACTS
# ─────────────────────────────────────────────────────────────────────────────

ACTS_STEPS = [
    ("adoration", "赞美", "我们先安静一下。今天，神的哪一个属性让你想敬拜祂？（信实、慈爱、同在……）可以用一两句话向祂说。"),
    ("confession", "认罪", "在神的光中，有没有什么想向祂坦白的？不用怕——这是回到恩典，不是被定罪。"),
    ("thanksgiving", "感恩", "回想最近的日子，有哪一件具体的小事让你感恩？哪怕很小。"),
    ("supplication", "祈求", "最后，把你心里最挂念的事告诉神。也可以为别人代求。"),
]

ACTS_CLOSING = "我们用 ACTS 走完了一段祷告。愿你带着这份安静继续今天的路。要把刚才的祈求记进祷告本吗？"


def acts_guide(step_index: int) -> dict:
    if step_index < len(ACTS_STEPS):
        key, zh, prompt = ACTS_STEPS[step_index]
        return {"done": False, "reply": f"【{zh}】{prompt}", "step": key}
    return {"done": True, "reply": ACTS_CLOSING, "step": None}


# ─────────────────────────────────────────────────────────────────────────────
# DevotionAgent — SOAP + 每日经文
# ─────────────────────────────────────────────────────────────────────────────

SCRIPTURE_POOL = [
    ("诗篇 23:1", "耶和华是我的牧者，我必不至缺乏。"),
    ("诗篇 46:10", "你们要休息，要知道我是神。"),
    ("马太福音 11:28", "凡劳苦担重担的人，可以到我这里来，我就使你们得安息。"),
    ("腓立比书 4:6-7", "应当一无挂虑，只要凡事借着祷告、祈求和感谢，将你们所要的告诉神。"),
    ("哥林多后书 12:9", "我的恩典够你用的，因为我的能力是在人的软弱上显得完全。"),
    ("耶利米哀歌 3:22-23", "我们不至消灭，是出于耶和华诸般的慈爱……每早晨这都是新的。"),
    ("约翰福音 15:5", "我是葡萄树，你们是枝子。常在我里面的，我也常在他里面，这人就多结果子。"),
]

SOAP_STEPS = [
    ("scripture", "经文", "今天我们一起安静读这节经文。慢慢读两遍，哪个词停在了你心里？"),
    ("observation", "观察", "这段经文在说什么？是关于神的什么、关于人的什么？不急，说说你看见的。"),
    ("application", "应用", "如果这句话是真的，对你今天的生活意味着什么？有没有一件小事可以回应它？"),
    ("prayer", "祷告", "最后，用一两句话，把刚才的领受变成对神说的话。"),
]

SOAP_CLOSING = "今天的 SOAP 灵修走完了。要把这段记录保存到灵修日志吗？愿这节经文今天一路陪着你。"


def scripture_of_the_day() -> dict:
    idx = int(time.time() // 86400) % len(SCRIPTURE_POOL)
    ref, text = SCRIPTURE_POOL[idx]
    return {"reference": ref, "text": text}


def soap_guide(step_index: int) -> dict:
    if step_index == 0:
        s = scripture_of_the_day()
        return {"done": False, "step": "scripture",
                "reply": f"今日经文 ——「{s['text']}」（{s['reference']}）\n\n{SOAP_STEPS[0][2]}"}
    if step_index < len(SOAP_STEPS):
        key, zh, prompt = SOAP_STEPS[step_index]
        return {"done": False, "step": key, "reply": prompt}
    return {"done": True, "step": None, "reply": SOAP_CLOSING}


# ─────────────────────────────────────────────────────────────────────────────
# Mock 回复（未配置 LLM 时）
# ─────────────────────────────────────────────────────────────────────────────

_MOCK_REPLIES = {
    "anxiety": "听起来你现在压着一些很重的东西。\n先深呼吸一下，慢慢来。\n你愿意说说，最让你紧绷的是哪一件事吗？我在这里。",
    "sadness": "我感觉到你的难过了。\n不用急着“好起来”，难过是可以被允许的。\n如果愿意，跟我说说发生了什么。",
    "shame": "谢谢你愿意说出这些——这需要勇气。\n先停一下：圣灵的提醒带人回到恩典，羞耻感却把人推向躲藏。\n你现在感受到的，更像哪一种？",
    "anger": "你的愤怒里通常藏着在乎。\n愿意说说是什么被触碰到了吗？我不评判。",
    "loneliness": "孤单的感觉很真实，谢谢你告诉我。\n此刻你不是一个人——也想邀请你想想，现实中有谁是你可以联系的？",
    "tired": "听起来你真的累了。\n安息不是奖励，是神的设计。今天能为自己留10分钟安静吗？",
    "fear": "害怕的时候，不用先假装勇敢。\n可以慢慢说说你在怕什么吗？",
    "joy": "这真是值得开心的事！🎉\n愿意把这份喜乐也变成一句感恩吗？",
    "gratitude": "感恩的心是很美的。\n把它记下来吧，低谷的日子可以回头看。",
    "peace": "愿这份平安多停留一会儿。\n此刻有什么想对神说的吗？",
    "neutral": "我在听。\n愿意多说一点吗？最近心里挂着什么？",
}


def mock_reply(emotion_type: str) -> str:
    return _MOCK_REPLIES.get(emotion_type, _MOCK_REPLIES["neutral"])


# ─────────────────────────────────────────────────────────────────────────────
# Growth — 成长阶段
# ─────────────────────────────────────────────────────────────────────────────

STAGE_ORDER = ["seed", "sprout", "lamp", "guardian", "pilgrim", "messenger"]

STAGE_INFO = {
    "seed": {"zh": "种子", "emoji": "🌱", "desc": "一切的开始"},
    "sprout": {"zh": "嫩芽", "emoji": "🌿", "desc": "连续同行3天"},
    "lamp": {"zh": "灯火", "emoji": "🕯️", "desc": "完成7次祷告或灵修"},
    "guardian": {"zh": "守护者", "emoji": "🛡️", "desc": "连续陪伴30天"},
    "pilgrim": {"zh": "天路客", "emoji": "⛰️", "desc": "形成稳定属灵习惯"},
    "messenger": {"zh": "使者", "emoji": "🕊️", "desc": "开始祝福和服事他人"},
}


def _current_streak(active_days: List[str]) -> int:
    """active_days: 升序 YYYY-MM-DD 列表。"""
    if not active_days:
        return 0
    import datetime as _dt
    streak = 1
    for i in range(len(active_days) - 1, 0, -1):
        cur = _dt.date.fromisoformat(active_days[i])
        prev = _dt.date.fromisoformat(active_days[i - 1])
        if (cur - prev).days <= 1:
            streak += 1
        else:
            break
    return streak


def compute_form_stage(active_days: List[str], prayer_devotion_count: int,
                       helped_others: bool) -> str:
    streak = _current_streak(active_days)
    total = len(active_days)
    stage = "seed"
    if streak >= 3 or total >= 3:
        stage = "sprout"
    if prayer_devotion_count >= 7:
        stage = "lamp"
    if streak >= 30:
        stage = "guardian"
    if total >= 45 and prayer_devotion_count >= 20:
        stage = "pilgrim"
    if stage == "pilgrim" and helped_others:
        stage = "messenger"
    return stage


def stage_progress(stage: str) -> float:
    try:
        return (STAGE_ORDER.index(stage) + 1) / len(STAGE_ORDER)
    except ValueError:
        return 1 / len(STAGE_ORDER)


# ─────────────────────────────────────────────────────────────────────────────
# Sprite 状态
# ─────────────────────────────────────────────────────────────────────────────

def sprite_state_for(mode: str, emotion_type: str, intensity: int) -> str:
    if mode in ("prayer", "devotion"):
        return "praying"
    if emotion_type in ("sadness", "anxiety", "shame", "fear", "loneliness"):
        return "comforting"
    if emotion_type in ("joy", "gratitude") and intensity >= 6:
        return "celebrating"
    if emotion_type == "tired":
        return "resting"
    if emotion_type == "neutral":
        return "idle"
    return "listening"
