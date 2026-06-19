"""
Crisis Engine — 危机守护子系统的纯逻辑层（无 IO，路由层调用）。

定位：危机状态识别 + 心理急救 + 属灵陪伴 + 人工/专业资源转介。
绝不是 AI 心理治疗师。核心顺序：先保命 → 再稳定 → 再陪伴 → 再属灵重建
（Safety > Stabilization > Connection > Meaning > Formation）。

Agent 职责：
  TriageAgent          triage()                危机分级 green/yellow/orange/red + 风险类型
  SafetyCheckAgent     safety_check_step()     直接、温柔、简短的安全确认状态机
  PFAAgent             grounding_54321()/...   心理急救：grounding / 呼吸 / 稳定
  SafetyPlanAgent      build_safety_plan()      个人安全计划模板
  EscalationAgent      red_emergency_message()  红色紧急升级文本 + 守护人提醒文本
  SpiritualCareAgent   spiritual_comfort()      低压属灵安慰（区分责备与控告，不增加羞耻）
  AddictionAgent       ten_minute_delay()       成瘾复发：HALT + 10 分钟延迟
  TraumaAgent          trauma_grounding()       创伤触发 / 解离 / flashback 稳定
  PostCrisisAgent      post_crisis_tasks()      危机后 24h/72h/7d/30d 恢复路径

设计红线：
  * 不诊断、不预测、不保证、不替代咨询师/急救。
  * Red 规则优先于任何 LLM 判断；红色绝不进入普通灵修建议或反思题。
  * 任何模糊的自伤/自杀表达 ≥ orange；绝不输出“你没有风险/你没事”。
  * 危机热线随 locale 多地区可配置（已核验：TW/CN/HK/US，其他回退到通用提示）。

LLM 调用由路由层注入（与 routers/agent.py 同一 provider 链），
未配置 API Key 时全部走本模块的规则/模板逻辑，功能完整可用。
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

try:  # 复用既有的 SafetyGuard 作为底层兜底（绝不降级，只抬高风险）
    import guardian_engine as _guardian
except ImportError:  # pragma: no cover
    try:
        from backend import guardian_engine as _guardian  # type: ignore
    except Exception:  # pragma: no cover
        _guardian = None  # type: ignore

# ─────────────────────────────────────────────────────────────────────────────
# 常量
# ─────────────────────────────────────────────────────────────────────────────

RISK_LEVELS: Tuple[str, ...] = ("green", "yellow", "orange", "red")
_LEVEL_RANK: Dict[str, int] = {"green": 0, "yellow": 1, "orange": 2, "red": 3}

CRISIS_RISK_TYPES: Tuple[str, ...] = (
    "suicidal_ideation", "self_harm", "harm_to_others", "panic_attack",
    "trauma_trigger", "dissociation", "domestic_violence", "spiritual_despair",
    "toxic_shame", "addiction_relapse", "psychosis_like_symptom", "medical_emergency",
)

MODULE_DISCLAIMER = (
    "危机守护不是诊断工具，也不是心理治疗或急救的替代。它只做四件事："
    "尽快帮助你回到安全、连接真实的人、找到专业资源、并给你不带控告的属灵陪伴。"
    "如果你此刻有立即危险，请直接拨打当地紧急电话。"
)


# ─────────────────────────────────────────────────────────────────────────────
# 多地区危机资源（已通过公开来源核验，2025/2026 现行）
#   每条：name / contact / availability / type / note
#   type: suicide_prevention | emotional_support | emergency | text | mental_health
# ─────────────────────────────────────────────────────────────────────────────

CRISIS_RESOURCES: Dict[str, Dict[str, object]] = {
    "TW": {
        "region": "台湾",
        "emergencyNumber": "119",
        "resources": [
            {"name": "1925 安心專線（依舊愛我）", "contact": "1925", "availability": "24/7",
             "type": "suicide_prevention", "note": "卫生福利部免费专线，自杀危机即时介入、评估与转介"},
            {"name": "1995 生命線協談專線", "contact": "1995", "availability": "24/7",
             "type": "emotional_support", "note": "民间团体，各类心理困扰协助"},
            {"name": "1980 張老師專線", "contact": "1980", "availability": "一至六 09:00-21:00 / 日 09:00-17:00",
             "type": "emotional_support", "note": "情绪困扰、生活适应"},
            {"name": "紧急救护／消防", "contact": "119", "availability": "24/7", "type": "emergency", "note": "医疗急症"},
        ],
    },
    "CN": {
        "region": "中国大陆",
        "emergencyNumber": "120",
        "resources": [
            {"name": "12356 全国统一心理援助热线", "contact": "12356", "availability": "24/7",
             "type": "mental_health", "note": "国家卫健委统一心理援助热线，全国各省已开通"},
            {"name": "北京心理危机研究与干预中心", "contact": "010-82951332", "availability": "24/7",
             "type": "suicide_prevention", "note": "固话可拨 800-810-1117；全国可拨手机线"},
            {"name": "医疗急救", "contact": "120", "availability": "24/7", "type": "emergency", "note": "吞药/出血/昏迷等医疗急症"},
        ],
    },
    "HK": {
        "region": "香港",
        "emergencyNumber": "999",
        "resources": [
            {"name": "撒瑪利亞防止自殺會 24 小時熱線", "contact": "2389 2222", "availability": "24/7",
             "type": "suicide_prevention", "note": "粤语情绪支援与自杀防治"},
            {"name": "Samaritan Befrienders（English）", "contact": "2389 2223", "availability": "24/7",
             "type": "emotional_support", "note": "English emotional support"},
            {"name": "緊急服務", "contact": "999", "availability": "24/7", "type": "emergency", "note": "立即危险/医疗/警务"},
        ],
    },
    "US": {
        "region": "United States",
        "emergencyNumber": "911",
        "resources": [
            {"name": "988 Suicide & Crisis Lifeline", "contact": "988", "availability": "24/7",
             "type": "suicide_prevention", "note": "Call or text 988; chat at 988lifeline.org"},
            {"name": "Crisis Text Line", "contact": "Text HOME to 741741", "availability": "24/7",
             "type": "text", "note": "Free confidential text support"},
            {"name": "Emergency", "contact": "911", "availability": "24/7", "type": "emergency", "note": "Immediate danger"},
        ],
    },
    "INTL": {
        "region": "International",
        "emergencyNumber": None,
        "resources": [
            {"name": "当地紧急电话 / Local emergency number", "contact": "—", "availability": "24/7",
             "type": "emergency", "note": "请拨打你所在国家/地区的紧急电话"},
            {"name": "Find a Helpline", "contact": "findahelpline.com", "availability": "24/7",
             "type": "emotional_support", "note": "按所在地查询当地心理危机热线"},
        ],
    },
}

# locale 前缀 / 关键词 → region code
_LOCALE_MAP: List[Tuple[str, str]] = [
    (r"^zh[-_]?tw", "TW"), (r"^zh[-_]?hk", "HK"), (r"^zh[-_]?mo", "HK"),
    (r"^zh[-_]?cn", "CN"), (r"^zh[-_]?sg", "INTL"),
    (r"tw|taiwan|台湾|臺灣", "TW"),
    (r"hk|hong\s*kong|香港|macau|澳门|澳門", "HK"),
    (r"cn|china|大陆|大陸|中国|中國", "CN"),
    (r"^en[-_]?us|usa|united\s*states|america", "US"),
]


def resolve_region(locale: Optional[str]) -> str:
    """把 locale / 地区字符串解析为 region code，未知回退到 TW（产品默认，可在路由层覆盖）。"""
    if not locale:
        return "TW"
    low = str(locale).strip().lower()
    for pattern, code in _LOCALE_MAP:
        if re.search(pattern, low):
            return code
    if low.startswith("en"):
        return "US"
    if low.startswith("zh"):
        return "TW"
    return "TW"


def get_resources(locale: Optional[str]) -> Dict[str, object]:
    """返回某 locale 对应地区的危机资源块（含 region / emergencyNumber / resources）。"""
    code = resolve_region(locale)
    block = dict(CRISIS_RESOURCES.get(code, CRISIS_RESOURCES["TW"]))
    block["regionCode"] = code
    return block


# ─────────────────────────────────────────────────────────────────────────────
# TriageAgent — 危机分级（规则 guard + 可被 LLM 抬高，但 Red 规则永远优先）
# ─────────────────────────────────────────────────────────────────────────────

# Red 强标记：本身已足够严重（计划已就绪 / 工具已获取 / 正在行动），无条件 Red。
_RED_STRONG_MARKERS = [
    r"写好了?遗书", r"遗书(写好|已经|留好)", r"买好了?(药|绳|刀|炭)",
    r"囤(了|好)药", r"吃了一(整)?瓶", r"吞(了|下).{0,5}药", r"服(药)?过量", r"overdose",
    r"站在(天台|楼顶|窗台|桥上|楼边)", r"在天台.{0,4}(跳|结束|站)",
    r"绳子(已经|都)?(系|挂|准备)好", r"现在就(要|去)死", r"马上就(要|去)(死|结束|跳|上吊)",
    r"今(晚|天)(就)?(结束(这一切|生命|自己)?|了结(自己|这一切)|去死|跳楼|上吊|不在了)",
    r"(就在)?今晚.{0,6}(结束|了结|动手)", r"正在(割|流血|跳|上吊)",
    r"再见了?，?这个世界", r"这是我最后", r"安排好了?(后事|一切)",
]

# Red 情境标记：单独出现可能有歧义，需与自伤/自杀/伤人或医疗急症并存才升 Red。
_RED_CONTEXTUAL_MARKERS = [
    r"已经?(准备|安排|计划)好", r"都准备好了", r"计划好了?怎么",
    r"刀(就)?(在|放在)?(手边|手里|旁边)", r"工具(都)?(备|准备|买)好",
]

# 各风险类型的检测模式（type, level_if_alone, [patterns]）
_TYPE_RULES: List[Tuple[str, str, List[str]]] = [
    ("suicidal_ideation", "orange", [
        r"不想活", r"活不下去", r"想死", r"去死算了", r"结束(自己的?)?生命",
        r"了结(自己|这一切)", r"自杀", r"消失算了", r"不想再撑", r"撑不下去了?",
        r"活着没(有)?(意义|意思)", r"生不如死",
        # 死亡相邻表达：为安全起见一律按自杀意念处理（宁可往高判）
        r"不配活(着)?", r"不值得活", r"不该活(着)?", r"没资格活(着)?", r"没脸活",
        r"suicide", r"kill\s*myself", r"end\s*my\s*life",
    ]),
    ("self_harm", "orange", [
        r"自残", r"自伤", r"割腕", r"割(自己|手)", r"想(撞|捶)墙", r"想让自己(痛|流血)",
        r"伤害自己", r"烫自己", r"self[-\s]?harm", r"cut\s*myself", r"hurt\s*myself",
    ]),
    ("harm_to_others", "orange", [
        r"想杀(了)?(他|她|他们|你)", r"想(伤害|弄死|打死|捅)(他|她|别人|人)",
        r"让(他|她|他们)付出代价", r"控制不住想(打|伤害)人", r"想报复.{0,4}(伤|杀|打)",
        r"hurt\s*(him|her|them|someone)", r"kill\s*(him|her|them)",
    ]),
    ("domestic_violence", "orange", [
        r"(他|她|家人|老公|老婆|男友|女友|父母).{0,6}(打我|施暴|家暴|动手)",
        r"正在被(打|家暴|虐待|性侵|侵犯)", r"被性侵", r"被强暴", r"被.{0,4}(跟踪|控制|囚禁)",
        r"我被打了", r"domestic\s*violence", r"被霸凌",
    ]),
    ("panic_attack", "yellow", [
        r"喘不过气", r"呼吸困难", r"心跳(很|好)快", r"快(要)?疯了", r"惊恐", r"panic",
        r"手(发抖|麻)", r"胸口(发闷|很紧)", r"感觉要死掉", r"控制不住(发抖|颤抖)",
    ]),
    ("trauma_trigger", "yellow", [
        r"又回到(那件事|那个场景|那时候)", r"闪回", r"flashback", r"被(拉|带)回(过去|那时)",
        r"那个画面(又|一直)(出现|闪)", r"创伤(被触发|又来了)",
    ]),
    ("dissociation", "orange", [
        r"身体(僵|动不了|麻木|不是我的)", r"灵魂出窍", r"不真实(感)?", r"像在做梦.{0,4}醒不来",
        r"感觉自己不(在现实|存在)", r"解离", r"不知道自己是谁", r"看着自己.{0,4}(像别人|很陌生)",
    ]),
    ("psychosis_like_symptom", "orange", [
        r"有声音(叫|让|命令)我", r"听到(有人|声音).{0,6}(叫|让|命令)", r"有人要害我", r"被监控|被跟踪.{0,6}(声音|信号)",
        r"控制我的(大脑|思想)", r"看到别人看不到",
    ]),
    ("medical_emergency", "orange", [
        r"吞(了|下).{0,5}药", r"服(了|药)?过量", r"overdose", r"大量(出血|流血)",
        r"胸口剧痛", r"昏(过去|倒)", r"失去意识", r"割得很深.{0,4}血",
    ]),
    ("addiction_relapse", "yellow", [
        r"快(要)?(控制不住|忍不住)", r"复发", r"又想(看|喝|赌|嗑|吸)", r"想看(色情|黄|片)",
        r"忍不住想(喝酒|喝|赌|抽|吸|嗑药)", r"戒不掉", r"破戒", r"relapse",
        r"想(暴食|催吐|报复性消费)", r"冲动(又|快)来了",
    ]),
    ("spiritual_despair", "yellow", [
        r"神(一定)?(不要|抛弃|离弃|放弃)(我|了)", r"我不配(活|被爱|被赦免)", r"神(不|没)(听|管)",
        r"永远(不会|无法)被(赦免|原谅)", r"祷告(没用|无用)", r"神在(惩罚|报应)我",
        r"我太(污秽|肮脏|罪大恶极)", r"我罪太重.{0,6}(不配|没救)", r"神(沉默|很远|不在)",
    ]),
    ("toxic_shame", "yellow", [
        r"我(就是个?)(废物|垃圾|烂人|没用的人)", r"我(根本)?不该(存在|出生|活着)",
        r"我配不上", r"我太(恶心|糟糕|失败).{0,4}(没救|无可救药)", r"我永远(好不了|改不了)",
    ]),
]


def _scan_types(text: str) -> List[Dict[str, str]]:
    matches: List[Dict[str, str]] = []
    seen = set()
    for rtype, level, patterns in _TYPE_RULES:
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                if rtype not in seen:
                    matches.append({"type": rtype, "level": level, "evidence": m.group(0)})
                    seen.add(rtype)
                break
    return matches


def _match_any(patterns: List[str], text: str) -> Optional[str]:
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0)
    return None


# 触发“必须直接安全确认”的风险类型
_DIRECT_SAFETY_TYPES = {"suicidal_ideation", "self_harm", "harm_to_others",
                        "domestic_violence", "medical_emergency"}
# 默认需要人工升级的风险类型（当达 orange 及以上）
_HUMAN_ESCALATION_TYPES = {"suicidal_ideation", "self_harm", "harm_to_others",
                           "domestic_violence", "medical_emergency", "psychosis_like_symptom"}

_WORKFLOW_BY_LEVEL = {
    "green": "normal_care",
    "yellow": "yellow_support",
    "orange": "orange_safety_plan",
    "red": "red_emergency",
}


def triage(text: str, llm_level: Optional[str] = None,
           context_levels: Optional[List[str]] = None) -> Dict[str, object]:
    """
    危机分级。返回结构（供路由层/前端使用）：
      riskLevel / riskTypes / evidence / confidence /
      recommendedWorkflow / requiresDirectSafetyQuestion / requiresHumanEscalation

    参数
      text            用户消息
      llm_level       （可选）LLM 分类结果，只能“抬高”风险，不能降低
      context_levels  （可选）近期历史风险等级，用于趋势兜底
    """
    text = text or ""
    matches = _scan_types(text)
    risk_types = [m["type"] for m in matches]
    evidence = [f"{m['type']}: {m['evidence']}" for m in matches]

    level = "green"
    for m in matches:
        if _LEVEL_RANK[m["level"]] > _LEVEL_RANK[level]:
            level = m["level"]

    # Red 升级（两类标记）
    #   强标记：无条件 Red；情境标记：与自伤/自杀/伤人/医疗急症并存才 Red。
    life_risk = any(t in {"suicidal_ideation", "self_harm", "harm_to_others"} for t in risk_types)
    strong = _match_any(_RED_STRONG_MARKERS, text)
    contextual = _match_any(_RED_CONTEXTUAL_MARKERS, text)
    if strong:
        level = "red"
        if not any(t in {"suicidal_ideation", "self_harm"} for t in risk_types):
            risk_types.append("suicidal_ideation")
        evidence.append(f"red_strong: {strong}")
    elif contextual and (life_risk or "medical_emergency" in risk_types):
        level = "red"
        evidence.append(f"red_contextual: {contextual}")
    elif contextual and not matches:
        # 强烈计划性语言但没匹配到类型 → 仍当作自杀意念兜底
        level = "red"
        risk_types.append("suicidal_ideation")
        evidence.append(f"red_contextual: {contextual}")

    # 底层兜底：复用 guardian SafetyGuard，只能抬高
    if _guardian is not None:
        try:
            g = _guardian.check_safety(text)
            if g == "high" and _LEVEL_RANK[level] < _LEVEL_RANK["orange"]:
                level = "orange"
                if "suicidal_ideation" not in risk_types:
                    risk_types.append("suicidal_ideation")
                evidence.append("guardian_safetyguard: high")
            elif g == "medium" and _LEVEL_RANK[level] < _LEVEL_RANK["yellow"]:
                level = "yellow"
                evidence.append("guardian_safetyguard: medium")
        except Exception:
            pass

    # LLM 只能抬高
    if llm_level in _LEVEL_RANK and _LEVEL_RANK[llm_level] > _LEVEL_RANK[level]:
        level = llm_level
        evidence.append(f"llm: {llm_level}")

    # 历史趋势兜底：近期多次 orange/red → 至少 yellow
    if context_levels:
        recent_high = sum(1 for c in context_levels[:10] if _LEVEL_RANK.get(c, 0) >= 2)
        if recent_high >= 2 and _LEVEL_RANK[level] < _LEVEL_RANK["yellow"]:
            level = "yellow"
            evidence.append("history: repeated_high_risk")

    requires_direct = (level in ("orange", "red")) or any(t in _DIRECT_SAFETY_TYPES for t in risk_types)
    requires_human = (level == "red") or (
        level == "orange" and any(t in _HUMAN_ESCALATION_TYPES for t in risk_types))

    # 置信度（启发式，仅供参考，绝不用作“低风险=没事”的依据）
    confidence = 0.5
    if matches:
        confidence = min(0.95, 0.55 + 0.1 * len(matches))
    if strong or (contextual and life_risk):
        confidence = 0.97

    return {
        "riskLevel": level,
        "riskTypes": risk_types,
        "evidence": evidence,
        "confidence": round(confidence, 2),
        "recommendedWorkflow": _WORKFLOW_BY_LEVEL[level],
        "requiresDirectSafetyQuestion": requires_direct,
        "requiresHumanEscalation": requires_human,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SafetyCheckAgent — 直接、温柔、简短的安全确认状态机
#   每次只问一个问题；不解释、不讲道、不要求用户证明自己没事。
# ─────────────────────────────────────────────────────────────────────────────

SAFETY_CHECK_STATES: Tuple[str, ...] = (
    "ask_intent", "ask_plan", "ask_alone", "ask_contact",
    "escalate_red", "create_safety_plan", "stabilize",
)

_SAFETY_QUESTIONS = {
    "ask_intent": (
        "我听见你现在非常痛苦。为了先确保你安全，我需要很直接地问你一句：\n"
        "你现在是否有伤害自己、结束生命，或伤害他人的想法？"
    ),
    "ask_plan": "谢谢你愿意如实告诉我。你现在是否已经有具体的方法、工具、地点或时间？",
    "ask_alone": "现在你是一个人吗？身边有没有可以马上联系到的人？",
    "ask_contact": "我们可以现在一起联系一位你信任的人吗？家人、朋友、牧者或小组长都可以。",
}


def safety_check_step(state: str, answer_yes: Optional[bool] = None) -> Dict[str, object]:
    """
    推进安全确认状态机。answer_yes：用户对当前问题的回答（True=有/是，False=没有/否，None=进入首问）。
    返回 {state, message, done, escalate}。
    """
    if state == "ask_intent" and answer_yes is None:
        return {"state": "ask_intent", "message": _SAFETY_QUESTIONS["ask_intent"], "done": False, "escalate": False}

    if state == "ask_intent":
        if answer_yes:
            return {"state": "ask_plan", "message": _SAFETY_QUESTIONS["ask_plan"], "done": False, "escalate": False}
        return {"state": "stabilize",
                "message": "谢谢你告诉我。那我们先一起把接下来的几分钟稳稳地度过，好吗？我会陪着你。",
                "done": False, "escalate": False}

    if state == "ask_plan":
        if answer_yes:
            return {"state": "escalate_red", "message": "", "done": True, "escalate": True}
        return {"state": "create_safety_plan",
                "message": "我听到了。你现在还没有具体的计划，这很重要。我们一起做一个今晚的安全小计划，并联系一个真实的人，好吗？",
                "done": False, "escalate": False}

    if state == "ask_alone":
        if answer_yes:  # 有人在身边
            return {"state": "ask_contact", "message": _SAFETY_QUESTIONS["ask_contact"], "done": False, "escalate": False}
        return {"state": "ask_contact", "message": _SAFETY_QUESTIONS["ask_contact"], "done": False, "escalate": False}

    if state == "ask_contact":
        return {"state": "create_safety_plan",
                "message": "好。无论你现在能不能联系到人，我都会陪你；同时我们也准备好随时可以拨打的热线。",
                "done": False, "escalate": False}

    # 兜底
    return {"state": "stabilize",
            "message": "我在这里陪你。我们一步一步来，先做一个很小的稳定动作。",
            "done": False, "escalate": False}


def safety_check_refusal_reply() -> str:
    """用户拒绝回答安全确认时——仍然温柔地指向真人与热线，不逼问、不放弃。"""
    return (
        "你可以不回答，没关系。我不会逼你。\n"
        "但因为我很在乎你的安全，我还是想请你现在做一件小事：\n"
        "联系一个你信任的人，或拨打当地的危机热线。你不需要独自承受这一切。"
    )


# ─────────────────────────────────────────────────────────────────────────────
# PFAAgent — 心理急救（Psychological First Aid：Look / Listen / Link）
# ─────────────────────────────────────────────────────────────────────────────

def grounding_54321() -> str:
    return (
        "我们现在只做一个很小的动作，把自己带回此刻：\n"
        "看见你周围的 5 个东西。\n"
        "摸到 4 个东西。\n"
        "听见 3 个声音。\n"
        "闻到 2 个气味。\n"
        "感受 1 个身体的感觉。\n"
        "不用做得完美，只要慢慢来。"
    )


def breathing_guide(cycles: int = 5) -> str:
    cycles = max(1, min(int(cycles or 5), 10))
    return (
        f"我们一起做 {cycles} 次呼吸，让身体慢下来：\n"
        "吸气 4 秒。\n停 1 秒。\n呼气 6 秒。\n"
        f"重复 {cycles} 次。呼气比吸气长，是在告诉身体——现在是安全的。"
    )


def pfa_look_checklist() -> List[str]:
    return ["你现在安全吗？", "你是一个人吗？", "身边有没有可能伤害自己的东西？",
            "有没有身体上的危险或受伤？", "需不需要医疗、警务或家人介入？"]


def pfa_listen_line() -> str:
    return (
        "我愿意先陪你停在这里。你不用马上把所有事情解释清楚。\n"
        "现在我们只做一件事：让你安全地度过接下来的 10 分钟。"
    )


def pfa_stabilize(risk_type: Optional[str] = None) -> str:
    """按风险类型选择最合适的稳定脚本。"""
    if risk_type == "panic_attack":
        return ("惊恐很可怕，但它通常像浪一样——会升高、到顶点、再退下去。\n"
                "我们现在不分析原因，只帮身体降下来。\n\n" + breathing_guide(5))
    if risk_type in ("trauma_trigger", "dissociation"):
        return trauma_grounding()
    return grounding_54321()


# ─────────────────────────────────────────────────────────────────────────────
# SafetyPlanAgent — 个人安全计划（Stanley-Brown 结构 + 属灵锚点）
# ─────────────────────────────────────────────────────────────────────────────

def build_safety_plan(locale: Optional[str] = None) -> Dict[str, object]:
    """返回一份可编辑的安全计划模板（含建议项 + 当地资源 + 紧急复制文本）。"""
    res = get_resources(locale)
    return {
        "warningSigns": [
            "连续失眠", "想消失 / 想一个人关机", "不想祷告也不想说话",
            "强烈的羞耻感", "想删掉所有社交账号", "开始安排后事或托付东西",
        ],
        "internalCopingStrategies": [
            "离开可能伤害自己的物品或地点", "坐到有人的公共空间", "喝一杯水、打开灯",
            "跟随 60 秒呼吸引导", "听一首熟悉的诗歌", "给一个人发一句话",
        ],
        "safePeople": [],          # 由用户填写（姓名+联系方式）
        "safePlaces": ["客厅 / 有人的房间", "楼下便利店或 24h 场所", "教会 / 小组的人那里"],
        "professionalResources": res["resources"],
        "meansRestrictionSteps": [
            "把药物交给信任的人保管或放到拿不到的地方",
            "把刀具、绳索等危险物品移走或请人帮忙收起",
            "今晚不独处，必要时去有人的地方过夜",
        ],
        "spiritualAnchors": [
            {"type": "scripture", "ref": "诗篇 34:18", "text": "耶和华靠近伤心的人，拯救灵性痛悔的人。"},
            {"type": "truth", "text": "神没有要求你独自撑过去。此刻先活下来，比解释一切更重要。"},
            {"type": "prayer", "text": "主啊，我现在很痛，求你抓住我，差人来陪我。"},
        ],
        "emergencyMessageTemplate": emergency_copy_text(),
        "regionCode": res["regionCode"],
        "emergencyNumber": res.get("emergencyNumber"),
        "disclaimer": MODULE_DISCLAIMER,
    }


def emergency_copy_text() -> str:
    """给用户一键复制、转发给真人的求助文本。"""
    return (
        "我现在状态很危险，可能会伤害自己。我不想一个人待着。"
        "请你现在联系我，或者马上来陪我。如果我没有回复，请帮我联系紧急服务。"
    )


# ─────────────────────────────────────────────────────────────────────────────
# EscalationAgent — 红色紧急升级
# ─────────────────────────────────────────────────────────────────────────────

def red_emergency_message(locale: Optional[str] = None) -> Dict[str, object]:
    """Red Level 文本：停止普通对话，给出三步紧急行动 + 当地资源 + 复制文本。"""
    res = get_resources(locale)
    lines = [
        "现在最重要的是你的即时安全，你不需要独自扛这个。",
        "请立刻做这三件事：",
        "1. 把可能伤害自己的东西放远，或离开那个地方。",
        "2. 现在拨打当地紧急电话或危机热线。",
        "3. 把下面这句话发给一个可信的人：",
        f"「{emergency_copy_text()}」",
    ]
    return {
        "headline": "请先保护好此刻的你",
        "steps": lines,
        "copyText": emergency_copy_text(),
        "resources": res["resources"],
        "region": res["region"],
        "regionCode": res["regionCode"],
        "emergencyNumber": res.get("emergencyNumber"),
    }


def guardian_alert_text(level: str, user_label: str = "你关心的人") -> str:
    """生成提醒守护人的文本（路由层在用户预授权后才会发送）。"""
    if level == "red":
        return (f"【紧急】{user_label}正处于严重危机状态，可能有立即危险，且不适合独处。"
                "请立刻联系 TA，或前往 TA 身边。如果联系不上，请帮忙联系紧急服务。")
    if level == "orange":
        return (f"{user_label}最近处于较高的情绪危机中，提到过伤害自己的念头。"
                "如果方便，请主动联系 TA，陪伴 TA 一段时间，并留意 TA 的安全。")
    return f"{user_label}最近状态比较低落。一句简单的问候和陪伴，对 TA 现在可能很重要。"


def escalation_levels() -> Dict[str, str]:
    return {
        "yellow": "建议用户主动联系守护人",
        "orange": "强烈建议联系守护人，生成可复制文本",
        "red": "立即建议联系；若用户已预授权，触发守护人通知 + 展示当地热线",
    }


# ─────────────────────────────────────────────────────────────────────────────
# SpiritualCareAgent — 低压属灵安慰（区分责备与控告，绝不增加羞耻）
# ─────────────────────────────────────────────────────────────────────────────

SPIRITUAL_CRISIS_TYPES: Tuple[str, ...] = (
    "condemnation", "toxic_shame", "loss_of_assurance", "spiritual_abuse",
    "church_trauma", "post_sin_despair", "dark_night", "religious_ocd",
)

# 圣灵的责备 vs 撒但的控告（帮助用户分辨）
CONVICTION_VS_CONDEMNATION = [
    {"dimension": "指向", "conviction": "指向基督与恩典", "condemnation": "指向绝望与自毁"},
    {"dimension": "结果", "conviction": "带来回转与盼望", "condemnation": "带来羞耻与逃避"},
    {"dimension": "范围", "conviction": "具体的某件事", "condemnation": "模糊地全盘否定你这个人"},
    {"dimension": "方向", "conviction": "使你靠近神", "condemnation": "使你逃离神"},
]

# 低刺激、高安慰、低控告的经文池
COMFORT_SCRIPTURES = [
    {"ref": "诗篇 34:18", "text": "耶和华靠近伤心的人，拯救灵性痛悔的人。", "theme": "神亲近伤心人"},
    {"ref": "以赛亚书 42:3", "text": "压伤的芦苇，他不折断；将残的灯火，他不吹灭。", "theme": "神不压伤软弱者"},
    {"ref": "罗马书 8:34", "text": "有基督耶稣已经死了，而且从死里复活，现今在神的右边，也替我们祈求。", "theme": "基督为软弱者代求"},
    {"ref": "罗马书 8:26", "text": "我们本不晓得当怎样祷告，只是圣灵亲自用说不出来的叹息替我们祷告。", "theme": "无法祷告时圣灵帮助"},
    {"ref": "诗篇 130:1", "text": "耶和华啊，我从深处向你求告。", "theme": "黑暗中仍可呼求"},
    {"ref": "诗篇 103:13-14", "text": "父亲怎样怜恤他的儿女……因为他知道我们的本体，思念我们不过是尘土。", "theme": "神体恤我们的软弱"},
    {"ref": "马太福音 11:28", "text": "凡劳苦担重担的人，可以到我这里来，我就使你们得安息。", "theme": "不必独自承受重担"},
    {"ref": "约翰一书 1:9", "text": "我们若认自己的罪，神是信实的，是公义的，必要赦免我们的罪。", "theme": "赦免与回转"},
]

# 危机中禁止的话术（路由层/前端用于过滤 LLM 输出）
FORBIDDEN_PHRASES = [
    "你就是信心不够", "你悔改就好了", "真正的基督徒不会这样", "这是神在惩罚你",
    "不要想太多", "多读经就好了", "你想想家人", "自杀是罪", "你不够属灵", "你要顺服权柄",
]

_SPIRITUAL_COMFORT = {
    "condemnation": (
        "你现在听到的，可能不是从神来的责备，而是一种把你推向绝望的控告。\n"
        "从神来的责备会带人回到基督；控告却让人觉得没有出路。\n"
        "此刻我们先不审判你的一生，只做一件事：让你安全地度过今天。"),
    "post_sin_despair": (
        "犯错之后的绝望很真实，但绝望不是从神来的声音。\n"
        "我们先区分：是圣灵温柔地领你回家，还是控告让你想躲、想毁掉自己？\n"
        "你不需要在崩溃里给自己定罪。先安全，再慢慢回到恩典。"),
    "loss_of_assurance": (
        "在崩溃的状态里，不适合给自己的一生下结论。\n"
        "得救的确据不是靠此刻的感觉撑住的。\n"
        "我们先让情绪稳下来，再谈信仰，好吗？"),
    "toxic_shame": (
        "羞耻会告诉你“你这个人就是错的”，但那不是神看你的眼光。\n"
        "你做过的事和你是谁，可以分开来看。\n"
        "现在先不急着评判自己，先让自己安全。"),
    "spiritual_abuse": (
        "如果有人用属灵的话语伤害了你，那种痛需要被认真听见，而不是被要求“顺服”。\n"
        "被伤害不是你的错。我们先照顾此刻的你。"),
    "church_trauma": (
        "教会里受的伤是真实的伤，值得被温柔对待，而不是被压下去。\n"
        "你可以同时爱神，又承认那段经历伤到了你。"),
    "dark_night": (
        "很多走在前面的圣徒，也经历过神好像沉默的黑夜。\n"
        "那不等于神离弃了你。黑暗里你仍然可以呼求，哪怕只是一声叹息。"),
    "religious_ocd": (
        "反复认罪、怎么都不安心，有时不是因为罪更大，而是一种宗教性的强迫在折磨你。\n"
        "这可能需要专业的帮助来一起处理。神的赦免不取决于你认得够不够多。"),
}


def spiritual_comfort(crisis_type: Optional[str] = None) -> Dict[str, object]:
    """返回低压属灵安慰：一段话 + 一节经文（不堆砌、不控告）。"""
    body = _SPIRITUAL_COMFORT.get(crisis_type or "", _SPIRITUAL_COMFORT["condemnation"])
    # 经文按 type 大致匹配主题，否则给“神亲近伤心人”
    scripture = COMFORT_SCRIPTURES[0]
    if crisis_type == "post_sin_despair":
        scripture = COMFORT_SCRIPTURES[7]
    elif crisis_type == "toxic_shame":
        scripture = COMFORT_SCRIPTURES[1]
    elif crisis_type == "dark_night":
        scripture = COMFORT_SCRIPTURES[4]
    return {
        "body": body,
        "scripture": scripture,
        "note": "我不会用经文压你。这里只给你一句可以抓住的话。你现在不需要表现得刚强。",
    }


def detect_spiritual_crisis(text: str) -> Optional[str]:
    """从文本里识别属灵危机子类型（用于选择合适的安慰）。"""
    rules = [
        ("post_sin_despair", r"犯(了)?罪.{0,8}(不配|没救|完了|绝望)|破戒.{0,6}(绝望|没救)"),
        ("loss_of_assurance", r"我(可能|是不是)没(得救|重生)|得救.{0,4}(没把握|没有确据)|怀疑自己(信|得救)"),
        ("spiritual_abuse", r"属灵(虐待|操控|霸凌)|用圣经(压|绑架)我"),
        ("church_trauma", r"教会(伤害|伤了|让我受伤)|被.{0,4}(弟兄|姊妹|牧师|长老).{0,4}伤"),
        ("religious_ocd", r"反复(认罪|悔改)|怎么(认|悔)都不(安|够)|强迫.{0,4}认罪"),
        ("dark_night", r"神(沉默|很远|不说话|不回应)|感觉不到神"),
        ("toxic_shame", r"我(就是|是个)(废物|垃圾|烂人)|我不该(存在|活着|出生)"),
        ("condemnation", r"神(不要|抛弃|离弃)(我|了)|我永远(不会|无法)被(赦免|原谅)"),
    ]
    for ctype, pat in rules:
        if re.search(pat, text):
            return ctype
    return None


# ─────────────────────────────────────────────────────────────────────────────
# AddictionAgent — 成瘾复发冲动的即时干预
# ─────────────────────────────────────────────────────────────────────────────

ADDICTION_DOMAINS = ("pornography", "alcohol", "drugs", "gambling",
                     "binge_eating", "gaming", "short_video", "impulsive_spending", "rage")

HALT_PROMPT = (
    "在做任何事之前，先花 10 秒检查一下你现在是否处于这些状态：\n"
    "H — Hungry 饥饿\nA — Angry 愤怒\nL — Lonely 孤独\nT — Tired 疲惫\n"
    "很多复发冲动，其实是身体在喊这四件事之一。"
)


def ten_minute_delay(domain: Optional[str] = None) -> str:
    return (
        "你现在不用承诺永远不再犯，也不用靠意志战胜一生的问题。\n"
        "你只需要把这个行动延迟 10 分钟。\n\n"
        "请现在做三步：\n"
        "1. 离开当前的房间。\n"
        "2. 把触发的设备 / 物品放远。\n"
        "3. 给一位守护人发一句：「我现在有复发冲动，请陪我 10 分钟。」"
    )


def addiction_alternatives() -> List[str]:
    return ["站起来喝一杯水", "打开灯、拉开窗帘", "出门走 5 分钟",
            "给 accountability partner 发消息", "做 60 秒呼吸", "写下此刻的 HALT 触发点"]


# ─────────────────────────────────────────────────────────────────────────────
# TraumaAgent — 创伤触发 / 解离 / flashback（只做 grounding，不做暴露、不逼回忆）
# ─────────────────────────────────────────────────────────────────────────────

def trauma_grounding() -> str:
    return (
        "你现在可能被过去的痛苦拉回去了。但你此刻在这里，不在那里。\n"
        "我们一起把你带回现在：\n"
        "看一眼今天的日期。\n"
        "双脚用力踩一踩地面，感受它的支撑。\n"
        "摸一下身边一个真实的物体，说出它的颜色和触感。\n"
        "慢慢告诉自己：「这是现在，不是那时。我是安全的。」"
    )


def trauma_donts() -> List[str]:
    return ["不会要求你详细复述创伤", "不会做暴露疗法", "不会说“这是神的美意”",
            "不会说“你饶恕他就好了”", "只做稳定、环境确认和连接真人"]


# ─────────────────────────────────────────────────────────────────────────────
# PostCrisisAgent — 危机后恢复（24h / 72h / 7d / 30d，不急着“立志改变”）
# ─────────────────────────────────────────────────────────────────────────────

POST_CRISIS_PHASES: Tuple[str, ...] = ("24h", "72h", "7d", "30d")

_POST_CRISIS_TASKS: Dict[str, List[str]] = {
    "24h": ["确认安全、移走危险物品", "睡眠 / 喝水 / 吃东西", "尽量不独处",
            "联系一位守护人", "取消今天的高压任务"],
    "72h": ["完成一次真人谈话", "写下这次危机的触发点", "更新安全计划",
            "预约咨询 / 牧养约谈", "降低属灵任务强度"],
    "7d": ["识别情绪与触发的模式", "建立属于自己的预警信号", "做轻量的灵修（不强求）",
           "恢复身体节律：作息、饮食、运动", "联系小组 / 教会的支持"],
    "30d": ["开始处理更深的创伤 / 信念 / 习惯", "建立成瘾复发预防机制",
            "属灵身份的重建（你是谁，神怎么看你）", "进入长期的陪伴 / 门训路径"],
}


def post_crisis_tasks(phase: str) -> List[str]:
    return list(_POST_CRISIS_TASKS.get(phase, _POST_CRISIS_TASKS["24h"]))


def post_crisis_all() -> Dict[str, List[str]]:
    return {p: list(_POST_CRISIS_TASKS[p]) for p in POST_CRISIS_PHASES}


# ─────────────────────────────────────────────────────────────────────────────
# 模式库桥接 — 危机后温柔地导入 spiritual-formation（绝不暗示「危机 = 罪」）
# ─────────────────────────────────────────────────────────────────────────────

# 与 spiritual-formation 的 SIN_PATTERN_IDS 保持一致
FORMATION_SIN_PATTERNS: Tuple[str, ...] = (
    "self_centeredness", "idolatry", "greed_consumerism", "sexual_disorder", "pride",
    "lies_falsehood", "hatred_division", "injustice_oppression", "religious_hypocrisy",
    "coldness_lack_of_love", "entertainment_escapism", "babel_pride", "spiritual_numbness",
)

# 风险类型 → 一个「温柔的起点」（用户可改）。默认 spiritual_numbness：
# 它谈的是「危机后觉得离神很远」，是最不带控告意味的入口。
_RISK_TO_PATTERN = {
    "addiction_relapse": "entertainment_escapism",
    "harm_to_others": "hatred_division",
    "spiritual_despair": "spiritual_numbness",
    "toxic_shame": "spiritual_numbness",
}


def formation_seed(risk_types: Optional[List[str]] = None) -> Dict[str, object]:
    """从危机风险类型温柔地建议一个「模式库」起点。

    重要：这只是恢复期的一个可改起点，**绝不**断言用户的危机本身是某种罪。
    框架始终是「先安全、再陪伴，状态稳定后再慢慢看长期模式」。
    """
    primary = "spiritual_numbness"
    for t in (risk_types or []):
        if t in _RISK_TO_PATTERN:
            primary = _RISK_TO_PATTERN[t]
            break
    return {
        "primarySinPattern": primary,
        "secondarySinPattern": None,
        "duration": "30_days",
        "intensity": "light",
        "riskTypes": list(risk_types or []),
        "title": "危机后的恢复（30 天 · 轻强度）",
        "note": ("这只是一个温柔的起点，不是说你的危机就是某种罪。模式库帮助你在状态稳定之后，"
                 "慢慢看见更长期的内在模式。你可以随时换成更贴近你的主题，也可以先不开始。"),
        "disclaimer": MODULE_DISCLAIMER,
    }


# ─────────────────────────────────────────────────────────────────────────────
# LLM 系统提示词（路由层在配置了 API Key 时注入使用）
# ─────────────────────────────────────────────────────────────────────────────

TRIAGE_SYSTEM_PROMPT = (
    "你是危机分流分类器。只输出风险等级，不写安慰、不写建议。\n"
    "等级定义：green=普通低落/压力；yellow=明显焦虑/抑郁/羞耻/诱惑/孤独；"
    "orange=有自伤念头/强烈崩溃/成瘾复发/高强度绝望；red=有明确计划/工具/时间/地点或正在行动，或对他人有具体伤害，或有即时人身危险。\n"
    "规则：1.只能在 green/yellow/orange/red 中选一个。2.任何模糊的自伤/自杀表达至少 orange。"
    "3.不确定时往高判，不要往低判。4.绝不输出“无风险/没事”。\n"
    "只回一个词：green 或 yellow 或 orange 或 red。"
)

SAFETY_CHECK_SYSTEM_PROMPT = (
    "你是危机安全确认 Agent。你的任务不是治疗，也不是讲道，而是快速确认用户是否有立即危险。\n"
    "规则：1.每次只问一个问题。2.问题必须直接、温柔、简短。"
    "3.如果用户表示有具体计划、工具、时间、地点，立即进入紧急升级。"
    "4.不要说“你会没事的”这种保证性语言。5.不要使用羞辱、责备、神学审判。"
    "6.不要长篇解释，不要问太多历史。"
)

SPIRITUAL_CARE_SYSTEM_PROMPT = (
    "你是危机中的属灵安慰 Agent。原则：先安慰再劝勉，先安全再悔改，先连接基督再分析罪，先陪伴再训练。\n"
    "禁止：用经文压人、把痛苦归因为“不够属灵”、在 Red Level 替代安全行动、增加羞耻感、做归因式审判。\n"
    "当用户表达属灵控告/羞耻时，温柔地帮助分辨：圣灵的责备指向基督与盼望，撒但的控告指向绝望与自毁。\n"
    "保持简短，用简体中文，一般不超过 120 字。"
)


def build_triage_messages(text: str) -> List[Dict[str, str]]:
    return [{"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
            {"role": "user", "content": text or ""}]


def parse_llm_level(raw: str) -> Optional[str]:
    """从 LLM 输出里抽取风险等级词。"""
    if not raw:
        return None
    low = raw.strip().lower()
    for lv in ("red", "orange", "yellow", "green"):
        if lv in low:
            return lv
    return None
