#!/usr/bin/env python3
"""
Disciple Formation Engine — Spiritual Planet DFOS v1.0
=======================================================

门徒塑造引擎：把"门徒倍增"的属灵愿景落成一个可计算的闭环。

设计原则（与产品宪章一致）：
    生命中心 / 关系中心 / 顺服中心 / 倍增中心 —— 不是知识/课程/打卡中心。
    评估的不是"知道什么"，而是"信靠什么、顺服了什么、复制了谁"。

工程取向（适配本项目现有栈，而非 Next.js/Neo4j/LangGraph）：
    - 确定性核心：纯函数 + 关键词启发式，零依赖可跑，保证永远有结果。
    - AI 增强：复用 waiting_engine.call_ai_provider（OpenAI 兼容，Gemini/SiliconFlow）。
      一次结构化 JSON 调用同时产出所有维度/偶像/品格/11 引擎/导师七段；失败回退确定性。
    - 图谱层：用 Postgres JSONB(twin) + disciple_relationships 表近似 Neo4j 的关系/倍增链。
    - LangGraph 编排：在 assess() 内按 Faith→Hope→Love→Idol→Obedience→Character→
      Discernment→Calling→DiscipleMaking→Parenting→Multiplication→StateTransition 顺序聚合。

本模块不落库、不依赖 FastAPI，便于单测；落库与回流由 routers/disciple.py 负责。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# 1. 属灵状态机 (Spiritual State Machine) — 10 态
# ─────────────────────────────────────────────────────────────────────────────

STATES: List[Dict[str, Any]] = [
    {"key": "SEEKER",              "order": 0, "zh": "慕道友",   "en": "Seeker",
     "desc": "正在认识福音，尚未信靠基督。"},
    {"key": "NEW_BELIEVER",       "order": 1, "zh": "初信者",   "en": "New Believer",
     "desc": "已信靠基督，开始祷告读经，需要救恩确据。"},
    {"key": "FOUNDATION_DISCIPLE","order": 2, "zh": "根基门徒", "en": "Foundation Disciple",
     "desc": "建立救恩确据与稳定灵修，愿意加入团契。"},
    {"key": "ROOTED_DISCIPLE",    "order": 3, "zh": "扎根门徒", "en": "Rooted Disciple",
     "desc": "真理根基、祷告生活、基本顺服成形。"},
    {"key": "OBEDIENT_DISCIPLE",  "order": 4, "zh": "顺服门徒", "en": "Obedient Disciple",
     "desc": "顺服稳定提升，偶像风险下降，品格明显成长。"},
    {"key": "SERVING_WORKER",     "order": 5, "zh": "服事工人", "en": "Serving Worker",
     "desc": "开始服事，有使命意识，愿意传福音。"},
    {"key": "MINISTRY_LEADER",    "order": 6, "zh": "事工领袖", "en": "Ministry Leader",
     "desc": "持续服事，能带领小组/项目，忠心有品格。"},
    {"key": "SPIRITUAL_PARENT",   "order": 7, "zh": "属灵父母", "en": "Spiritual Parent",
     "desc": "稳定陪伴他人成长，生养属灵儿女。"},
    {"key": "DISCIPLE_MAKER",     "order": 8, "zh": "门徒训练者","en": "Disciple Maker",
     "desc": "所带的门徒也开始带门徒（第二代）。"},
    {"key": "MULTIPLIER",         "order": 9, "zh": "倍增者",   "en": "Multiplier",
     "desc": "至少三代复制链，形成稳定门徒倍增网络。"},
]
STATE_BY_KEY = {s["key"]: s for s in STATES}
STATE_ORDER = {s["key"]: s["order"] for s in STATES}


# ─────────────────────────────────────────────────────────────────────────────
# 2. 塑造维度 (Formation Dimensions) — 11 维 (0~100)
# ─────────────────────────────────────────────────────────────────────────────

DIMENSIONS: List[Dict[str, str]] = [
    {"key": "faith",          "zh": "信靠"},
    {"key": "hope",           "zh": "盼望"},
    {"key": "love",           "zh": "爱"},
    {"key": "truth",          "zh": "真理"},
    {"key": "prayer",         "zh": "祷告"},
    {"key": "obedience",      "zh": "顺服"},
    {"key": "character",      "zh": "品格"},
    {"key": "calling",        "zh": "呼召"},
    {"key": "service",        "zh": "服事"},
    {"key": "mission",        "zh": "使命"},
    {"key": "multiplication", "zh": "倍增"},
]
DIM_KEYS = [d["key"] for d in DIMENSIONS]
DIM_ZH = {d["key"]: d["zh"] for d in DIMENSIONS}

# Christlikeness Index 用的核心 9 维（与宪章 CI 公式一致）
CI_KEYS = ["faith", "hope", "love", "truth", "prayer",
           "obedience", "character", "mission", "multiplication"]


# ─────────────────────────────────────────────────────────────────────────────
# 3. 偶像谱 (Idol Detection) — 9 类
# ─────────────────────────────────────────────────────────────────────────────

IDOLS: Dict[str, Dict[str, Any]] = {
    "approval":     {"zh": "认可偶像", "remedy": "在基督里你已被父神完全悦纳，不需用表现赢取爱。",
                     "kw": ["在乎别人看法", "被认可", "讨好", "怕被否定", "评价", "面子", "点赞", "别人怎么想"]},
    "control":      {"zh": "掌控偶像", "remedy": "神坐着为王，把你抓住不放的主权交还给祂。",
                     "kw": ["掌控", "控制", "焦虑", "计划被打乱", "不确定", "放不下", "必须按我", "操心"]},
    "comfort":      {"zh": "安逸偶像", "remedy": "基督呼召你背起十字架，真安息在祂里面而非在舒适里。",
                     "kw": ["太累", "想逃避", "舒服", "拖延", "刷手机", "躺平", "不想动", "享受"]},
    "power":        {"zh": "权力偶像", "remedy": "基督倒空自己作仆人，真正的伟大在于服事。",
                     "kw": ["权力", "地位", "话语权", "被尊重", "输不起", "争", "压过", "影响力"]},
    "success":      {"zh": "成就偶像", "remedy": "你的价值不在成就，乃在天父称你为爱子。",
                     "kw": ["成功", "业绩", "成就", "证明自己", "落后", "赢", "kpi", "目标没达成", "升职"]},
    "relationship": {"zh": "关系偶像", "remedy": "唯有神能满足你心，人无法成为你的救主。",
                     "kw": ["离不开", "对方", "感情", "被爱", "孤单", "依赖", "他/她", "分手", "在一起"]},
    "ministry":     {"zh": "事工偶像", "remedy": "神要的是你这个人，不是你为祂做的工。",
                     "kw": ["事工", "服事果效", "教会", "团契带领", "果子", "讲道", "侍奉成绩"]},
    "technology":   {"zh": "科技偶像", "remedy": "回到神面前安静，让祂而非信息流牧养你的心。",
                     "kw": ["手机", "刷", "ai", "信息", "短视频", "屏幕", "停不下来", "上瘾"]},
    "investment":   {"zh": "财富偶像", "remedy": "不能又事奉神又事奉玛门；积财在天。",
                     "kw": ["投资", "钱", "亏", "赚", "理财", "股票", "收益", "财务", "房子"]},
}
IDOL_KEYS = list(IDOLS.keys())


# ─────────────────────────────────────────────────────────────────────────────
# 4. 品格谱 (Character Formation) — 圣灵果子 + 八福 + 教牧书信
# ─────────────────────────────────────────────────────────────────────────────

CHARACTER: List[Dict[str, str]] = [
    {"key": "humility",     "zh": "谦卑"},
    {"key": "patience",     "zh": "忍耐"},
    {"key": "gentleness",   "zh": "温柔"},
    {"key": "courage",      "zh": "勇气"},
    {"key": "faithfulness", "zh": "忠心"},
    {"key": "self_control",  "zh": "节制"},
    {"key": "holiness",     "zh": "圣洁"},
    {"key": "love",         "zh": "爱"},
]
CHAR_KEYS = [c["key"] for c in CHARACTER]


# ─────────────────────────────────────────────────────────────────────────────
# 5. 11 引擎清单（前端用于渲染卡片）
# ─────────────────────────────────────────────────────────────────────────────

ENGINES: List[Dict[str, str]] = [
    {"key": "faith",        "zh": "信靠引擎",   "emoji": "🛐", "desc": "发现你真正信靠什么"},
    {"key": "hope",         "zh": "盼望引擎",   "emoji": "⏳", "desc": "你在等候神，还是在焦虑掌控"},
    {"key": "love",         "zh": "爱引擎",     "emoji": "❤️", "desc": "关系、冲突、饶恕、服事"},
    {"key": "idol",         "zh": "偶像监测",   "emoji": "🗿", "desc": "心被什么抓住"},
    {"key": "obedience",    "zh": "顺服引擎",   "emoji": "🚶", "desc": "神已显明的，你顺服了吗"},
    {"key": "character",    "zh": "品格塑造",   "emoji": "🌱", "desc": "在压力与等候中成形的生命"},
    {"key": "discernment",  "zh": "属灵分辨",   "emoji": "🧭", "desc": "这决定出于信心还是惧怕"},
    {"key": "calling",      "zh": "呼召引擎",   "emoji": "🔥", "desc": "恩赐、负担、果效、方向"},
    {"key": "disciple",     "zh": "门徒培养",   "emoji": "🤝", "desc": "谁在带你，你在带谁"},
    {"key": "parenting",    "zh": "属灵生养",   "emoji": "👪", "desc": "属灵家庭树与生养预备"},
    {"key": "multiplication","zh": "倍增引擎",  "emoji": "🌳", "desc": "复制链、DMI、王国影响"},
]


# ─────────────────────────────────────────────────────────────────────────────
# 6. 启发式打分工具
# ─────────────────────────────────────────────────────────────────────────────

# 正向/负向维度信号关键词（粗粒度，AI 关闭时的兜底）
_DIM_SIGNALS: Dict[str, Dict[str, List[str]]] = {
    "faith":     {"pos": ["信靠神", "交托", "相信神", "神掌权", "凭信心"],
                  "neg": ["靠自己", "不信", "怀疑神", "没有神也", "担心钱", "焦虑"]},
    "hope":      {"pos": ["盼望", "等候神", "将来有指望", "复活", "永生"],
                  "neg": ["绝望", "没意义", "看不到希望", "撑不下去", "灰心"]},
    "love":      {"pos": ["饶恕", "关心", "服事人", "和好", "陪伴", "体谅"],
                  "neg": ["恨", "冲突", "记仇", "冷漠", "争吵", "嫉妒"]},
    "truth":     {"pos": ["圣经说", "经文", "真理", "读经", "神的话"],
                  "neg": ["不知道圣经", "随便", "凭感觉", "世界说"]},
    "prayer":    {"pos": ["祷告", "安静在神面前", "祈求", "默想", "亲近神"],
                  "neg": ["没时间祷告", "很难安静", "祷告不下去", "远离神"]},
    "obedience": {"pos": ["顺服", "照着去做", "悔改", "遵行", "立刻去"],
                  "neg": ["拖延", "不想做", "明知道却", "抗拒", "拒绝顺服"]},
    "character": {"pos": ["忍耐", "谦卑", "节制", "温柔", "饶恕"],
                  "neg": ["发火", "骄傲", "失控", "苦毒", "嫉妒", "论断"]},
    "calling":   {"pos": ["恩赐", "负担", "呼召", "为主做", "异象"],
                  "neg": ["不知道方向", "迷茫", "没价值", "找不到意义"]},
    "service":   {"pos": ["服事", "侍奉", "帮助", "委身教会", "摆上"],
                  "neg": ["不想服事", "只顾自己", "退出服事"]},
    "mission":   {"pos": ["传福音", "宣教", "带人信主", "大使命", "为福音"],
                  "neg": ["不敢传", "不在乎别人灵魂", "封闭"]},
    "multiplication": {"pos": ["带门徒", "门训", "陪伴弟兄", "复制", "生养"],
                       "neg": ["没有带过人", "只顾自己长进"]},
}


def _clip(x: float, lo: float = 1.0, hi: float = 99.0) -> float:
    return max(lo, min(hi, x))


def _combined_text(inputs: Dict[str, str]) -> str:
    parts = [inputs.get(k, "") or "" for k in
             ("journal", "scripture", "prayer", "event", "feeling", "want", "fear", "belief", "question")]
    return "\n".join(parts).lower()


def _score_dimension(key: str, text: str, base: float) -> float:
    sig = _DIM_SIGNALS.get(key, {"pos": [], "neg": []})
    score = base
    for w in sig["pos"]:
        if w in text:
            score += 9
    for w in sig["neg"]:
        if w in text:
            score -= 9
    # 文本长度本身代表参与度（轻微加成）
    if len(text) > 120:
        score += 3
    return _clip(score)


def _score_idols(text: str) -> Dict[str, float]:
    scores = {}
    for k, meta in IDOLS.items():
        hit = sum(1 for w in meta["kw"] if w in text)
        scores[k] = _clip(12 + hit * 22)  # 命中越多越高
    return scores


def _risk_level(top_score: float) -> str:
    if top_score >= 75:
        return "CRITICAL"
    if top_score >= 55:
        return "HIGH"
    if top_score >= 35:
        return "MEDIUM"
    return "LOW"


# ─────────────────────────────────────────────────────────────────────────────
# 7. Christlikeness Index & DMI
# ─────────────────────────────────────────────────────────────────────────────

def compute_ci(dims: Dict[str, float]) -> float:
    vals = [float(dims.get(k, 0)) for k in CI_KEYS]
    return round(sum(vals) / len(vals), 1) if vals else 0.0


def compute_dmi(network: Dict[str, Any]) -> Dict[str, Any]:
    """DMI = Depth × Breadth × ReproductionRate × Duration（归一化到 0~100 展示）。"""
    depth = float(network.get("depth", 0))          # 复制代数
    breadth = float(network.get("breadth", 0))      # 直接门徒数
    reproduction = float(network.get("reproduction_rate", 0))  # 0~1，二代/一代
    duration = float(network.get("duration_months", 0))
    raw = depth * breadth * max(reproduction, 0.05) * max(duration / 12.0, 0.1)
    # 平滑到 0~100
    dmi = round(min(100.0, raw * 8.0), 1)
    return {
        "depth": depth, "breadth": breadth,
        "reproduction_rate": round(reproduction, 2),
        "duration_months": duration,
        "dmi": dmi,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 8. 状态迁移 (State Transition)
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_state(dims: Dict[str, float], network: Dict[str, Any]) -> str:
    """根据维度分 + 门徒网络，自下而上推断当前可达的最高状态（保守，逐级判定）。"""
    f, h, lv = dims.get("faith", 0), dims.get("hope", 0), dims.get("love", 0)
    truth, prayer, obed = dims.get("truth", 0), dims.get("prayer", 0), dims.get("obedience", 0)
    char, mission = dims.get("character", 0), dims.get("mission", 0)
    active = int(network.get("breadth", 0))           # 正在带的门徒
    gen2 = int(network.get("second_generation", 0))   # 第二代
    depth = int(network.get("depth", 0))

    # 第一步：纯由属灵生命维度判定"塑造层级"（不含门徒网络）
    formation = "SEEKER"
    if f >= 35:                                            formation = "NEW_BELIEVER"
    if truth >= 45 and prayer >= 40:                       formation = "FOUNDATION_DISCIPLE"
    if truth >= 55 and prayer >= 50 and obed >= 45:        formation = "ROOTED_DISCIPLE"
    if obed >= 65 and char >= 60:                          formation = "OBEDIENT_DISCIPLE"
    if mission >= 55 and dims.get("service", 0) >= 50:     formation = "SERVING_WORKER"
    if dims.get("service", 0) >= 65 and char >= 65:        formation = "MINISTRY_LEADER"

    # 第二步：门徒网络只能在"已具塑造根基"的前提下，把人推向生养/复制层级。
    # 没有生命根基的"带人"不算属灵父母——避免凭关系数量虚高。
    order = STATE_ORDER[formation]
    candidates = [formation]
    if order >= STATE_ORDER["SERVING_WORKER"] and active >= 1:
        candidates.append("SPIRITUAL_PARENT")
    if order >= STATE_ORDER["SERVING_WORKER"] and gen2 >= 1:
        candidates.append("DISCIPLE_MAKER")
    if order >= STATE_ORDER["SERVING_WORKER"] and depth >= 3 and gen2 >= 1:
        candidates.append("MULTIPLIER")
    return max(candidates, key=lambda k: STATE_ORDER[k])


def next_state(current: str) -> Optional[str]:
    o = STATE_ORDER.get(current, 0)
    for s in STATES:
        if s["order"] == o + 1:
            return s["key"]
    return None


def _growth_edge(dims: Dict[str, float]) -> str:
    """成长边界 = 最弱维度。"""
    if not dims:
        return "faith"
    return min(DIM_KEYS, key=lambda k: dims.get(k, 0))


# ─────────────────────────────────────────────────────────────────────────────
# 9. 确定性核心：assess_fallback
# ─────────────────────────────────────────────────────────────────────────────

def _baseline_dims(twin: Optional[Dict[str, Any]]) -> Dict[str, float]:
    prior = (twin or {}).get("dims") or {}
    return {k: float(prior.get(k, 50.0)) for k in DIM_KEYS}


def assess_fallback(inputs: Dict[str, str], twin: Optional[Dict[str, Any]] = None,
                    network: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    text = _combined_text(inputs)
    network = network or {}
    base = _baseline_dims(twin)
    # EMA：新信号与历史分各占一半，平滑长期画像
    dims = {}
    for k in DIM_KEYS:
        new = _score_dimension(k, text, base[k])
        dims[k] = round(0.5 * base[k] + 0.5 * new, 1)

    idol_scores = _score_idols(text)
    top_idols = sorted(idol_scores, key=idol_scores.get, reverse=True)[:3]
    top_idol = top_idols[0] if idol_scores[top_idols[0]] > 25 else None
    risk = _risk_level(idol_scores[top_idols[0]]) if top_idols else "LOW"

    # 品格：从 character 维度派生 + 关键词微调
    char_scores = {c: round(_clip(dims["character"] + (5 if CHARACTER and False else 0)), 1)
                   for c in CHAR_KEYS}

    ci = compute_ci(dims)
    state = evaluate_state(dims, network)
    edge = _growth_edge(dims)
    nxt = next_state(state)
    dmi = compute_dmi(network)

    obed_step = _default_obedience_step(edge, top_idol)

    engines = _build_engines_fallback(dims, idol_scores, top_idols, risk, char_scores, network, dmi)
    mentor = {
        "state": state,
        "root_cause": (f"近期文字显示你在「{DIM_ZH.get(edge, edge)}」上较弱"
                       + (f"，并可能被「{IDOLS[top_idol]['zh']}」抓住。" if top_idol else "。")),
        "biblical_truth": IDOLS[top_idol]["remedy"] if top_idol else "你在基督里是新造的人，旧事已过。",
        "obedience_step": obed_step,
        "prayer": "主啊，求你光照我心，让我真实地信靠你、顺服你，并能领人作你的门徒。",
        "growth_opportunity": f"本周聚焦操练「{DIM_ZH.get(edge, edge)}」。",
        "next_transition": nxt,
    }

    return {
        "ok": True,
        "source": "heuristic",
        "spiritual_state": state,
        "next_state": nxt,
        "christlikeness_index": ci,
        "dimensions": dims,
        "idol_scores": idol_scores,
        "top_idols": top_idols,
        "top_idol": top_idol,
        "risk_level": risk,
        "character_scores": char_scores,
        "growth_edge": edge,
        "next_step": obed_step,
        "dmi": dmi,
        "engines": engines,
        "mentor": mentor,
    }


def _default_obedience_step(edge: str, top_idol: Optional[str]) -> str:
    table = {
        "faith": "今天把一件你最焦虑的事，具体地交托给神，并记下来。",
        "hope": "写下你正在等候的一件事，把它从'我要掌控'改写成'我要等候神'。",
        "love": "今天主动向一位关系紧张的人迈出和好的一小步。",
        "truth": "今天读一段经文，写下一句神要对你说的话。",
        "prayer": "今天安静 10 分钟，只为听神说话而祷告。",
        "obedience": "找出一件你一直拖延、神已提醒你的事，今天就去做。",
        "character": "在今天最容易失控的场景里，先停三秒，求圣灵掌权。",
        "calling": "写下神给你的一个负担，并问：这周我能为它做的一小步是什么。",
        "service": "本周在教会或身边找一个具体的服事机会摆上自己。",
        "mission": "为一位还未信主的人祷告，并主动关心他一次。",
        "multiplication": "约一位弟兄姊妹，开始固定的一对一陪伴。",
    }
    return table.get(edge, "今天向神迈出一步顺服。")


def _build_engines_fallback(dims, idol_scores, top_idols, risk, char_scores, network, dmi) -> Dict[str, Any]:
    return {
        "faith": {"score": dims["faith"],
                  "false_beliefs": [], "true_beliefs": [],
                  "summary": f"信靠分 {dims['faith']}。留意你在压力下第一个抓住的是神还是别的。"},
        "hope": {"score": dims["hope"],
                 "waiting_pattern": "—",
                 "summary": f"盼望分 {dims['hope']}。等候的方式，泄露了你真正的盼望放在哪里。"},
        "love": {"score": dims["love"],
                 "summary": f"爱分 {dims['love']}。爱在关系的张力与饶恕里被验证。"},
        "idol": {"scores": idol_scores, "top_idols": top_idols, "risk_level": risk,
                 "gospel_remedy": IDOLS[top_idols[0]]["remedy"] if top_idols else "",
                 "demolition_plan": "命名它 → 在神面前承认 → 用福音真理取代 → 在群体中被守望。"},
        "obedience": {"score": dims["obedience"], "status": "UNCLEAR",
                      "summary": f"顺服分 {dims['obedience']}。成长不在于知道更多，而在于顺服已知。"},
        "character": {"scores": char_scores,
                      "summary": "品格在成功、失败、等候、压力、冲突中被塑造。"},
        "discernment": {"summary": "重大决定时，先分辨它出于信心、惧怕、骄傲，还是讨好。",
                        "peace_level": None, "obedience_risk": None},
        "calling": {"confidence": round((dims["calling"] + dims["service"]) / 2, 1),
                    "summary": "呼召在恩赐、负担、经历、果效的交汇处逐渐清晰。"},
        "disciple": {"discipled_by": network.get("mentors", 0),
                     "discipling": network.get("breadth", 0),
                     "summary": "提后2:2 —— 你从谁领受？你又交托给谁？"},
        "parenting": {"readiness": round((dims["character"] + dims["love"]) / 2, 1),
                      "summary": "属灵生养的预备：生命的份量 + 稳定的陪伴。"},
        "multiplication": {**dmi,
                           "summary": "成熟的标志是复制：是否培养了能再带门徒的门徒。"},
    }


# ─────────────────────────────────────────────────────────────────────────────
# 10. AI 增强
# ─────────────────────────────────────────────────────────────────────────────

MENTOR_SYSTEM_PROMPT = (
    "你是一位门徒塑造导师（Disciple Formation Mentor）。"
    "你的目标不是提供信息，而是塑造像基督的生命。"
    "你扎根于耶稣的门训模式（拣选-同行-示范-差遣-监督-纠正-倍增）、保罗模式（提后2:2四代复制）、"
    "以及科尔曼《布道的钥匙》、特罗特曼/导航会、亨里克森《门徒乃造就而成》、甘陵敦《世界在等待的门徒》传统。"
    "分析时务必看：身份、信念、情绪、注意力、渴望、惧怕、偶像、习惯、关系、使命、顺服。"
    "给建议前先找出：根部信念、根部偶像、根部动机、当前属灵状态。"
    "语气温柔、以福音为中心、不论断、把人带到基督面前，不是给人加担子。用简体中文。"
)

_JSON_SHAPE = """{
  "spiritual_state": "SEEKER|NEW_BELIEVER|FOUNDATION_DISCIPLE|ROOTED_DISCIPLE|OBEDIENT_DISCIPLE|SERVING_WORKER|MINISTRY_LEADER|SPIRITUAL_PARENT|DISCIPLE_MAKER|MULTIPLIER",
  "dimensions": {"faith":0-100,"hope":0-100,"love":0-100,"truth":0-100,"prayer":0-100,"obedience":0-100,"character":0-100,"calling":0-100,"service":0-100,"mission":0-100,"multiplication":0-100},
  "idol_scores": {"approval":0-100,"control":0-100,"comfort":0-100,"power":0-100,"success":0-100,"relationship":0-100,"ministry":0-100,"technology":0-100,"investment":0-100},
  "top_idols": ["..."],
  "character_scores": {"humility":0-100,"patience":0-100,"gentleness":0-100,"courage":0-100,"faithfulness":0-100,"self_control":0-100,"holiness":0-100,"love":0-100},
  "growth_edge": "维度key",
  "engines": {
    "faith": {"false_beliefs":["..."],"true_beliefs":["..."],"summary":"..."},
    "hope": {"waiting_pattern":"...","summary":"..."},
    "love": {"summary":"..."},
    "idol": {"gospel_remedy":"...","demolition_plan":"..."},
    "obedience": {"status":"IMMEDIATE|PARTIAL|DELAYED|REFUSAL|UNCLEAR","summary":"..."},
    "character": {"summary":"..."},
    "discernment": {"summary":"..."},
    "calling": {"summary":"..."},
    "disciple": {"summary":"..."},
    "parenting": {"summary":"..."},
    "multiplication": {"summary":"..."}
  },
  "mentor": {
    "root_cause": "1 根因分析",
    "biblical_truth": "2 圣经真理",
    "obedience_step": "3 一个具体顺服行动",
    "prayer": "4 一段回应祷告",
    "growth_opportunity": "5 成长机会",
    "next_transition": "6 下一个状态建议(状态key或null)"
  }
}"""


def build_prompt(inputs: Dict[str, str], twin: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    prior = ""
    if twin and twin.get("dims"):
        prior = "（用户既有画像，供参考连续性）：" + json.dumps(twin["dims"], ensure_ascii=False)
    user = (
        "请基于以下用户的属灵反思，完成门徒塑造评估。\n"
        f"今日反思/日志：{inputs.get('journal','')}\n"
        f"今日经文：{inputs.get('scripture','')}\n"
        f"今日祷告：{inputs.get('prayer','')}\n"
        f"具体处境/决定（可空）：{inputs.get('event','')}\n"
        f"感受（可空）：{inputs.get('feeling','')}\n"
        f"渴望/害怕（可空）：{inputs.get('want','')} / {inputs.get('fear','')}\n"
        f"{prior}\n\n"
        "先挖到根部信念与偶像，再以福音把人带到基督面前。所有分数 0~100。"
        f"严格只输出如下 JSON，不要任何额外文字：\n{_JSON_SHAPE}"
    )
    return [{"role": "system", "content": MENTOR_SYSTEM_PROMPT},
            {"role": "user", "content": user}]


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


def _call_ai(messages, settings):
    """返回解析后的 JSON dict 或 None。复用 waiting_engine 的 OpenAI 兼容 Provider。"""
    try:
        try:
            from backend.waiting_engine import call_ai_provider
        except Exception:
            from waiting_engine import call_ai_provider
        return call_ai_provider(messages, settings=settings)
    except Exception:
        return None


def assess(inputs: Dict[str, str], twin: Optional[Dict[str, Any]] = None,
           network: Optional[Dict[str, Any]] = None,
           settings: Any = None, use_ai: bool = True) -> Dict[str, Any]:
    """主入口：确定性核心 + AI 增强合并。永远返回完整报告。"""
    fallback = assess_fallback(inputs, twin=twin, network=network)
    if not use_ai:
        return fallback

    ai = _call_ai(build_prompt(inputs, twin), settings)
    if not ai:
        return fallback

    out = dict(fallback)
    # 维度
    if isinstance(ai.get("dimensions"), dict):
        merged = dict(fallback["dimensions"])
        for k in DIM_KEYS:
            v = ai["dimensions"].get(k)
            if isinstance(v, (int, float)):
                merged[k] = round(float(v), 1)
        out["dimensions"] = merged
        out["christlikeness_index"] = compute_ci(merged)
        out["growth_edge"] = ai.get("growth_edge") if ai.get("growth_edge") in DIM_KEYS else _growth_edge(merged)
        out["spiritual_state"] = (ai.get("spiritual_state")
                                  if ai.get("spiritual_state") in STATE_BY_KEY
                                  else evaluate_state(merged, network or {}))
        out["next_state"] = next_state(out["spiritual_state"])
    # 偶像
    if isinstance(ai.get("idol_scores"), dict):
        sc = dict(fallback["idol_scores"])
        for k in IDOL_KEYS:
            v = ai["idol_scores"].get(k)
            if isinstance(v, (int, float)):
                sc[k] = round(float(v), 1)
        out["idol_scores"] = sc
        tops = sorted(sc, key=sc.get, reverse=True)[:3]
        out["top_idols"] = tops
        out["top_idol"] = tops[0] if sc[tops[0]] > 25 else None
        out["risk_level"] = _risk_level(sc[tops[0]]) if tops else "LOW"
    if isinstance(ai.get("top_idols"), list) and ai["top_idols"]:
        valid = [t for t in ai["top_idols"] if t in IDOL_KEYS]
        if valid:
            out["top_idols"] = valid[:3]
            out["top_idol"] = valid[0]
    # 品格
    if isinstance(ai.get("character_scores"), dict):
        cs = dict(fallback["character_scores"])
        for k in CHAR_KEYS:
            v = ai["character_scores"].get(k)
            if isinstance(v, (int, float)):
                cs[k] = round(float(v), 1)
        out["character_scores"] = cs
    # 引擎文字
    if isinstance(ai.get("engines"), dict):
        eng = json.loads(json.dumps(fallback["engines"]))  # deep copy
        for ek, ev in ai["engines"].items():
            if ek in eng and isinstance(ev, dict):
                eng[ek].update({k: v for k, v in ev.items() if v not in (None, "", [])})
        out["engines"] = eng
    # 导师七段
    if isinstance(ai.get("mentor"), dict):
        m = dict(fallback["mentor"])
        m["state"] = out["spiritual_state"]
        for k in ("root_cause", "biblical_truth", "obedience_step", "prayer",
                  "growth_opportunity", "next_transition"):
            if ai["mentor"].get(k):
                m[k] = ai["mentor"][k]
        out["mentor"] = m
        if m.get("obedience_step"):
            out["next_step"] = m["obedience_step"]

    out["source"] = "ai"
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 11. 轻量 AI 导师对话（单独问答，非整套评估）
# ─────────────────────────────────────────────────────────────────────────────

def mentor_reply(question: str, twin: Optional[Dict[str, Any]] = None,
                 settings: Any = None, use_ai: bool = True) -> Dict[str, Any]:
    fallback = {
        "ok": True, "source": "heuristic",
        "answer": "在基督里安息。把你的处境带到神面前，先求祂的国和祂的义，"
                  "其余的祂必加给你。今天迈出一步顺服，胜过明白十个道理。",
    }
    if not use_ai or not question.strip():
        return fallback
    prior = ""
    if twin and twin.get("dims"):
        prior = "（用户画像）：" + json.dumps(twin["dims"], ensure_ascii=False)
    messages = [
        {"role": "system", "content": MENTOR_SYSTEM_PROMPT +
         " 回答要简短（150字内），落在一个具体的顺服或祷告上，不要长篇说教。"},
        {"role": "user", "content": f"{prior}\n我的问题：{question.strip()}"},
    ]
    ai = _call_ai(messages, settings)
    if ai and ai.get("answer"):
        return {"ok": True, "source": "ai", "answer": str(ai["answer"])}
    # 有些 provider 直接返回文本而非 JSON：尝试原样
    if isinstance(ai, dict):
        for v in ai.values():
            if isinstance(v, str) and len(v) > 10:
                return {"ok": True, "source": "ai", "answer": v}
    return fallback


# ─────────────────────────────────────────────────────────────────────────────
# 12. meta —— 给前端渲染状态机/维度/偶像/引擎
# ─────────────────────────────────────────────────────────────────────────────

def meta() -> Dict[str, Any]:
    return {
        "states": STATES,
        "dimensions": DIMENSIONS,
        "ci_keys": CI_KEYS,
        "idols": [{"key": k, "zh": v["zh"]} for k, v in IDOLS.items()],
        "character": CHARACTER,
        "engines": ENGINES,
    }


def empty_profile() -> Dict[str, Any]:
    dims = {k: 50.0 for k in DIM_KEYS}
    return {
        "spiritual_state": "SEEKER",
        "next_state": next_state("SEEKER"),
        "christlikeness_index": compute_ci(dims),
        "dimensions": dims,
        "top_idol": None,
        "growth_edge": "faith",
        "updated_at": None,
        "twin": {"dims": dims},
    }
