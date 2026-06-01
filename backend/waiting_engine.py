"""
waiting_engine.py — 等候之路 / Waiting Transformation Module

把「等待戈多」(被动、虚无、焦虑、幻想式等待) 温柔地分辨与转化为
「等候上帝」(在不确定中仍信靠、忠心行动、不把结果当偶像)。

本引擎：
  - 提供确定性 (deterministic) 评分，保证无外部 AI 也能运行；
  - 提供 build_prompt() 与可替换的 AIProvider，在配置了 LLM 时可增强分析；
  - 内置固定的「7 天等候操练」模板；
  - 内置危机词检测，对自伤 / 极端绝望提示寻求现实专业帮助。

语气铁律：不定罪、不贴标签、不说「神一定要你…」、不把等待等同于软弱、
保留心理复杂性、鼓励祷告与现实责任。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 自评维度 (前端 0–10 滑杆)
# ---------------------------------------------------------------------------
INPUT_DIMENSIONS: List[Dict[str, str]] = [
    {"key": "anxiety_level",      "name": "焦虑程度",   "hint": "想到这件事，我有多焦躁不安？"},
    {"key": "hope_level",         "name": "盼望程度",   "hint": "我对它仍存着多少有根的盼望？"},
    {"key": "passivity_level",    "name": "被动程度",   "hint": "我是否在『耗着』、什么也不做地等？"},
    {"key": "fantasy_level",      "name": "幻想程度",   "hint": "我多常用想象的剧情来填补等待？"},
    {"key": "trust_level",        "name": "信靠程度",   "hint": "在不确定中，我有多信靠神？"},
    {"key": "obedience_readiness","name": "顺服预备",   "hint": "无论结果如何，我多愿意继续顺服？"},
    {"key": "action_clarity",     "name": "行动清晰度", "hint": "我多清楚此刻能忠心做的小事？"},
]
INPUT_KEYS = [d["key"] for d in INPUT_DIMENSIONS]

WAITING_TYPE_LABELS = {
    "godot_waiting": {"label": "等待戈多", "color": "#ff8787",
                      "desc": "更接近被动、虚无、焦虑、幻想式的等待。"},
    "god_waiting":   {"label": "等候上帝", "color": "#34c759",
                      "desc": "更接近信靠、盼望、忠心行动的等候。"},
    "mixed":         {"label": "二者交织", "color": "#ffd43b",
                      "desc": "两种等待同时存在 —— 这很真实，也正是被塑造的地方。"},
    "unknown":       {"label": "尚不清晰", "color": "#868e96",
                      "desc": "信息还不够，先从命名你的等待开始。"},
}


def _n(v: Any) -> float:
    """把 0–10 输入归一到 0–1，并裁剪。"""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, v / 10.0))


def _mean(*xs: float) -> float:
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 4) if xs else 0.0


# ---------------------------------------------------------------------------
# 确定性评分
# ---------------------------------------------------------------------------
def score(inputs: Dict[str, Any]) -> Dict[str, Any]:
    anx = _n(inputs.get("anxiety_level"))
    hope = _n(inputs.get("hope_level"))
    passivity = _n(inputs.get("passivity_level"))
    fantasy = _n(inputs.get("fantasy_level"))
    trust = _n(inputs.get("trust_level"))
    obed = _n(inputs.get("obedience_readiness"))
    action = _n(inputs.get("action_clarity"))

    # 若几乎没有信息 → unknown
    provided = sum(1 for k in INPUT_KEYS if inputs.get(k) not in (None, "", 0, 0.0))
    if provided <= 1:
        return {
            "waiting_type": "unknown",
            "godot_waiting_score": 0.0, "god_waiting_score": 0.0,
            "idolatry_risk": 0.0, "passivity_risk": 0.0,
            "hope_stability": 0.0, "trust_level": trust, "action_clarity": action,
            "emotional_dependency": 0.0, "responsibility_alignment": 0.0,
        }

    godot = _mean(anx, passivity, fantasy, 1 - trust, 1 - action)
    god = _mean(trust, hope, action, obed, 1 - passivity, 1 - fantasy)
    idolatry_risk = _mean(fantasy, anx, 1 - trust)
    passivity_risk = _mean(passivity, 1 - action)
    hope_stability = _mean(hope, trust, 1 - fantasy)
    emotional_dependency = _mean(anx, fantasy, 1 - trust)
    responsibility_alignment = _mean(action, obed, 1 - passivity)

    diff = god - godot
    if abs(diff) < 0.12:
        wtype = "mixed"
    elif diff >= 0.12:
        wtype = "god_waiting"
    else:
        wtype = "godot_waiting"

    return {
        "waiting_type": wtype,
        "godot_waiting_score": godot,
        "god_waiting_score": god,
        "idolatry_risk": idolatry_risk,
        "passivity_risk": passivity_risk,
        "hope_stability": hope_stability,
        "trust_level": trust,
        "action_clarity": action,
        "emotional_dependency": emotional_dependency,
        "responsibility_alignment": responsibility_alignment,
    }


# ---------------------------------------------------------------------------
# 温柔的文字分析 + 建议 + 反思问题 (确定性)
# ---------------------------------------------------------------------------
def _waiting_object_text(waiting_for: str, s: Dict[str, Any]) -> str:
    obj = (waiting_for or "你所等待的").strip()
    if s["idolatry_risk"] >= 0.6:
        return (f"你正在等的，是「{obj}」。从你的描述看，它此刻承载的分量似乎很重 —— "
                f"重到有点像在替你回答『我是否安好、是否有价值』。这值得温柔地留意。")
    return (f"你正在等的，是「{obj}」。看见它、为它命名，本身就是从被动走向清醒的第一步。")


def _emotional_text(s: Dict[str, Any]) -> str:
    anx = s["emotional_dependency"]
    if anx >= 0.6:
        return ("等待里夹着不少焦虑与幻想 —— 心会反复预演各种剧情，也害怕失去。"
                "这是很人性的，不是软弱；只是它提醒你，内心需要一个比结果更稳的锚。")
    if anx >= 0.35:
        return "情绪大致平稳，但偶尔会被不确定牵动。允许自己有这些起伏，同时不被它们带走。"
    return "你的情绪在这件事上相对安稳，这是一份恩典 —— 也可能是信靠正在生长的迹象。"


def _idolatry_text(s: Dict[str, Any]) -> str:
    r = s["idolatry_risk"]
    if r >= 0.6:
        return ("这个等待对象，似乎正在悄悄决定你的平安、价值感与安全感。它本是好的，"
                "但当它坐上了只有神能坐的位置，等待就容易变成煎熬。这不是定罪，是一个邀请："
                "把它从『救主』的位置，温柔地放回『礼物』的位置。")
    if r >= 0.35:
        return "它对你很重要，但还没有完全取代神的位置。继续留心，别让盼望不知不觉变成依赖。"
    return "目前它还在一个健康的位置 —— 你在等它，但你不是靠它活着。"


def _passivity_text(s: Dict[str, Any]) -> str:
    r = s["passivity_risk"]
    if r >= 0.6:
        return ("等待此刻更像『耗着』—— 也许有些该承担的责任或可做的小事，被『等』暂时遮住了。"
                "等候上帝从不等于停摆；在等的同时，仍可以忠心地做今天能做的一件小事。")
    if r >= 0.35:
        return "你没有完全停摆，但行动的方向还可以更清晰一点。等候里仍有可作的工。"
    return "你在等待中仍保持着行动与责任，这正是『等候』与『枯等』的关键分别。"


def _fhl_text(s: Dict[str, Any]) -> str:
    if s["god_waiting_score"] >= s["godot_waiting_score"]:
        return ("整体方向上，这段等待正在塑造信靠、盼望与忍耐 —— 你在不确定中仍选择忠心。"
                "继续走，等候本身就是被神塑造的过程。")
    return ("此刻这段等待更容易催生焦虑、控制与幻想，而非信、望、爱。这不是终点 —— "
            "只要愿意把结果松手、恢复一点行动与爱，方向就能被重新校准。")


# 危机词：出现则附上现实求助提示 (不替代专业判断)
_CRISIS_PATTERNS = [
    "自杀", "想死", "不想活", "结束生命", "活不下去", "伤害自己", "自残", "自伤",
    "没有意义活着", "解脱算了", "撑不下去",
]


def detect_crisis(text: str) -> bool:
    if not text:
        return False
    t = str(text)
    return any(p in t for p in _CRISIS_PATTERNS)


CRISIS_NOTE = (
    "⚠️ 我读到一些很沉重的字句。你的痛苦是真实的，也值得被认真对待。"
    "这类感受往往超出一个反思工具能承载的范围 —— 请考虑尽快联系你信任的人，"
    "或寻求现实中的专业帮助 (如心理咨询师、医生，或当地的心理援助热线)。"
    "你并不孤单，也不需要独自扛。"
)


def deterministic_analysis(case: Dict[str, Any], s: Dict[str, Any]) -> Dict[str, Any]:
    waiting_for = case.get("waiting_for", "")
    desc = case.get("waiting_description", "")
    crisis = detect_crisis(waiting_for) or detect_crisis(desc)

    guidance: List[str] = []
    if s["passivity_risk"] >= 0.45:
        guidance.append("今天选一件不依赖最终结果的小事，忠心地完成它 —— 让等待重新有重量。")
    if s["idolatry_risk"] >= 0.45:
        guidance.append("用一句祷告把结果松手：『我仍盼望它，但我不靠它活着。』")
    if s["emotional_dependency"] >= 0.45:
        guidance.append("当幻想剧情升起时，温柔地把注意力拉回『此刻我能做的、能爱的』。")
    if not guidance:
        guidance = [
            "继续保持这份在不确定中的信靠 —— 它正在把你塑造得更像耶稣。",
            "为这段等待中已有的恩典具体感恩一件事。",
            "今天主动去爱或服事一个人，让等待不至于让你向内封闭。",
        ]
    guidance = guidance[:3]

    summary_label = WAITING_TYPE_LABELS[s["waiting_type"]]["label"]
    summary = (f"此刻你的等待，更接近「{summary_label}」。"
               + WAITING_TYPE_LABELS[s["waiting_type"]]["desc"])
    if crisis:
        summary = CRISIS_NOTE + "\n\n" + summary

    return {
        "waiting_type": s["waiting_type"],
        "godot_waiting_score": s["godot_waiting_score"],
        "god_waiting_score": s["god_waiting_score"],
        "idolatry_risk": s["idolatry_risk"],
        "passivity_risk": s["passivity_risk"],
        "hope_stability": s["hope_stability"],
        "trust_level": s["trust_level"],
        "action_clarity": s["action_clarity"],
        "emotional_dependency": s["emotional_dependency"],
        "responsibility_alignment": s["responsibility_alignment"],
        "summary": summary,
        "crisis_flag": crisis,
        "analysis": {
            "waiting_object": _waiting_object_text(waiting_for, s),
            "emotional_pattern": _emotional_text(s),
            "possible_idolatry_pattern": _idolatry_text(s),
            "passivity_pattern": _passivity_text(s),
            "faith_hope_love_direction": _fhl_text(s),
        },
        "guidance": guidance,
        "reflection_questions": [
            "我到底在等什么？在它背后，我真正渴望的是什么？",
            "如果它永远不来，我是否仍相信自己在神面前有价值、被爱？",
            "今天我可以忠心完成的一件小事是什么？",
        ],
        "source": "deterministic",
    }


# ---------------------------------------------------------------------------
# 固定的 7 天等候操练模板
# ---------------------------------------------------------------------------
SEVEN_DAY_PLAN: List[Dict[str, Any]] = [
    {"day_index": 1, "practice_title": "命名等待",
     "practice_content": "写下你正在等待的人、事或结果，以及你最害怕它不来的原因。",
     "reflection_prompt": "这个等待背后，我真正渴望的是什么？"},
    {"day_index": 2, "practice_title": "识别依附",
     "practice_content": "省察这个等待对象，是否正在决定你的平安、价值感与安全感。",
     "reflection_prompt": "如果它不来，我是否仍相信自己被神认识和爱？"},
    {"day_index": 3, "practice_title": "从幻想回到现实",
     "practice_content": "区分『我希望发生的事』和『我今天能忠心去做的事』。",
     "reflection_prompt": "我今天可以承担的一个小责任是什么？"},
    {"day_index": 4, "practice_title": "交托结果",
     "practice_content": "用祷告把结果交托给神，不把结果当作救主。",
     "reflection_prompt": "我最难交托的是什么？为什么？"},
    {"day_index": 5, "practice_title": "等候中的行动",
     "practice_content": "做一个不依赖最终结果的小行动。",
     "reflection_prompt": "这个行动是否让我更自由、更真实、更有爱？"},
    {"day_index": 6, "practice_title": "等候中的爱",
     "practice_content": "在尚未得着结果之前，仍主动去关心、服事或理解一个人。",
     "reflection_prompt": "我是否因等待而变得更封闭？今天我如何重新去爱？"},
    {"day_index": 7, "practice_title": "复盘转化",
     "practice_content": "回顾这一周，你的等待是否从焦虑被动，转向信靠、盼望与行动。",
     "reflection_prompt": "我里面有什么被重新校准了？"},
]


def default_7_day_plan() -> List[Dict[str, Any]]:
    # 返回副本，避免调用方意外修改模板
    return [dict(d) for d in SEVEN_DAY_PLAN]


# ---------------------------------------------------------------------------
# AI 分析：Prompt 构建 + 可替换 Provider (失败回退确定性结果)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "你是一个温柔、成熟、非控制型的属灵反思助手。你的任务不是替用户判断神的旨意，"
    "也不是定罪用户，而是帮助用户看见自己的等待状态：它更接近被动、虚无、焦虑的"
    "『等待戈多』，还是更接近信靠、盼望、忠心行动的『等候上帝』。\n"
    "禁止：不要说『神告诉你』；不要说『你一定应该』；不要贴标签；不要制造羞耻感；"
    "不要把复杂心理问题简单属灵化；不要用强制命令口吻。\n"
    "必须：使用温柔、反思式语言；保留不确定性；给出多种可能解释；鼓励用户恢复责任、"
    "祷告、省察、行动；强调等候不是逃避，盼望不是幻想，信靠不是被动。\n"
    "若用户文字流露自伤、极端绝望，请在 summary 开头温柔地建议寻求现实中的专业帮助"
    "与可信赖的人。\n"
    "只输出一个 JSON 对象，不要任何额外文字。"
)

_JSON_SHAPE = (
    '{\n'
    '  "waiting_type": "godot_waiting | god_waiting | mixed | unknown",\n'
    '  "godot_waiting_score": 0.0, "god_waiting_score": 0.0,\n'
    '  "idolatry_risk": 0.0, "passivity_risk": 0.0,\n'
    '  "hope_stability": 0.0, "trust_level": 0.0, "action_clarity": 0.0,\n'
    '  "summary": "简短总结",\n'
    '  "analysis": {"waiting_object": "...", "emotional_pattern": "...",\n'
    '    "possible_idolatry_pattern": "...", "passivity_pattern": "...",\n'
    '    "faith_hope_love_direction": "..."},\n'
    '  "guidance": ["...", "...", "..."],\n'
    '  "reflection_questions": ["...", "...", "..."]\n'
    '}'
)


def build_prompt(case: Dict[str, Any]) -> List[Dict[str, str]]:
    ratings = {d["name"]: case.get(d["key"], 0) for d in INPUT_DIMENSIONS}
    rating_lines = "\n".join(f"- {k} (0-10): {v}" for k, v in ratings.items())
    user = (
        f"用户正在等待：{case.get('waiting_for','')}\n"
        f"具体描述：{case.get('waiting_description','') or '（未填写）'}\n\n"
        f"用户自评：\n{rating_lines}\n\n"
        "请从以下维度温柔地分辨：(1) 等待对象到底是什么；(2) 情绪状态；"
        "(3) 偶像风险 —— 它是否在决定其价值感/平安/安全感/意义；(4) 被动风险 —— "
        "是否在用等待逃避该承担的责任；(5) 信望爱方向；(6) 3 条以内温和、可执行的小步骤。\n"
        f"严格按此 JSON 结构输出（数值 0.0–1.0）：\n{_JSON_SHAPE}"
    )
    return [{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user}]


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    # 去掉 ```json 围栏
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


def call_ai_provider(messages: List[Dict[str, str]],
                     settings: Any = None,
                     timeout: float = 40.0) -> Optional[Dict[str, Any]]:
    """
    用项目既有的 OpenAI 兼容 Provider (Gemini / SiliconFlow) 做一次非流式 JSON 补全。
    任何失败都返回 None，由调用方回退到确定性分析。
    """
    if settings is None:
        try:
            from backend.core.config import settings as settings  # type: ignore
        except Exception:
            try:
                from core.config import settings as settings  # type: ignore
            except Exception:
                return None
    try:
        import httpx
    except Exception:
        return None

    providers = []
    gem = getattr(settings, "gemini_api_key", "") or ""
    sf = getattr(settings, "siliconflow_api_key", "") or ""
    if gem and not gem.startswith("your_"):
        providers.append({
            "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
            "model": "gemini-2.0-flash",
            "headers": {"Authorization": f"Bearer {gem}", "Content-Type": "application/json"},
        })
    if sf and not sf.startswith("your_"):
        providers.append({
            "url": "https://api.siliconflow.cn/v1/chat/completions",
            "model": "deepseek-ai/DeepSeek-V3",
            "headers": {"Authorization": f"Bearer {sf}", "Content-Type": "application/json"},
        })
    if not providers:
        return None

    for p in providers:
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(p["url"], headers=p["headers"], json={
                    "model": p["model"],
                    "messages": messages,
                    "temperature": 0.6,
                    "max_tokens": 900,
                })
            if resp.status_code >= 400:
                continue
            content = resp.json()["choices"][0]["message"]["content"]
            parsed = _extract_json(content)
            if parsed:
                return parsed
        except Exception:
            continue
    return None


def _coerce_ai_result(ai: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
    """把 AI 返回的 JSON 规整到统一结构，缺字段用确定性结果兜底。"""
    def f(key, default=0.0):
        try:
            return max(0.0, min(1.0, float(ai.get(key, fallback.get(key, default)))))
        except Exception:
            return fallback.get(key, default)

    wtype = ai.get("waiting_type")
    if wtype not in WAITING_TYPE_LABELS:
        wtype = fallback["waiting_type"]

    analysis = ai.get("analysis") if isinstance(ai.get("analysis"), dict) else {}
    out = dict(fallback)
    out.update({
        "waiting_type": wtype,
        "godot_waiting_score": f("godot_waiting_score"),
        "god_waiting_score": f("god_waiting_score"),
        "idolatry_risk": f("idolatry_risk"),
        "passivity_risk": f("passivity_risk"),
        "hope_stability": f("hope_stability"),
        "trust_level": f("trust_level"),
        "action_clarity": f("action_clarity"),
        "summary": str(ai.get("summary") or fallback["summary"]),
        "analysis": {**fallback["analysis"], **{k: str(v) for k, v in analysis.items()}},
        "guidance": [str(x) for x in (ai.get("guidance") or fallback["guidance"])][:3],
        "reflection_questions": [str(x) for x in
                                 (ai.get("reflection_questions") or fallback["reflection_questions"])][:5],
        "source": "ai",
    })
    # 危机提示永远保留
    if fallback.get("crisis_flag") and not out["summary"].startswith("⚠️"):
        out["summary"] = CRISIS_NOTE + "\n\n" + out["summary"]
    return out


def analyze(case: Dict[str, Any], settings: Any = None, use_ai: bool = True) -> Dict[str, Any]:
    """
    主入口：先算确定性结果，若配置了 AI Provider 则尝试增强；任何失败都回退确定性。
    """
    s = score(case)
    fallback = deterministic_analysis(case, s)
    if not use_ai or s["waiting_type"] == "unknown":
        return fallback
    try:
        ai = call_ai_provider(build_prompt(case), settings=settings)
    except Exception:
        ai = None
    if not ai:
        return fallback
    return _coerce_ai_result(ai, fallback)


def meta() -> Dict[str, Any]:
    return {
        "input_dimensions": INPUT_DIMENSIONS,
        "waiting_type_labels": WAITING_TYPE_LABELS,
        "seven_day_plan": SEVEN_DAY_PLAN,
    }


# ---------------------------------------------------------------------------
# 回流 Formation（闭环）：把一次等候分析折算成「形成事件」信号
# ---------------------------------------------------------------------------
def formation_signal(result: Dict[str, Any]):
    """返回 (pattern_categories, loop_broken, reflection_active, emotional_intensity)；None=跳过。"""
    wt = result.get("waiting_type")
    if wt == "god_waiting":
        return (["growth", "spiritual"], True, True, 4.0)
    if wt == "godot_waiting":
        emo = round(3.0 + float(result.get("idolatry_risk", 0.5)) * 6.0, 1)
        return (["fear", "desire"], False, True, emo)
    if wt == "mixed":
        return (["fear"], False, True, 5.0)
    return None  # unknown -> 不记录
