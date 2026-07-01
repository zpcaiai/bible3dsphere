"""
emotionally_healthy_engine.py — 情商与灵命 / Emotionally Healthy Spirituality
（Peter Scazzero《Emotionally Healthy Spirituality》）

补足 gap 分析所缺的「心理健康 ↔ 属灵成熟」桥梁——这正是本产品「属灵星球」的核心论题。
Scazzero 的命题：「一个人情感不成熟，却属灵成熟，是不可能的。」
冰山比喻：水面上是我们展示的自己，水面下是情绪、过去、伤口、动机。

本引擎只做「一个温柔的自我评估」这一件事：让用户为六个维度自评，找出最需要关注的
1–2 个维度，明说这不是评判你的属灵/情绪好坏，只是帮你看见成长的邀请，再给一个
具体的成长步伐 + 经文。

纯函数；确定性优先；内置危机词检测；AI 仅作可选增强，失败回退确定性结果。
不定罪、不贴标签，只帮助人诚实察看「冰山之下」，把心理健康与属灵成熟连起来。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

THESIS = "一个人情感不成熟，却属灵成熟，是不可能的。"
ICEBERG = "水面上是你展示的，水面下才是真正驱动你的。"

# ── 六个维度（0..1 自评）：key / name / hint / 成长步伐 / 锚点经文 ──
DIMENSIONS: List[Dict[str, Any]] = [
    {"key": "self_awareness", "name": "自我觉察",
     "hint": "我能觉察自己此刻真实的情绪（而不是压下去或说不清）。",
     "grow": "今天停三次，各花一分钟，只是诚实地问自己：『我现在的感觉是什么？』——不评判、不修正，只是命名它。认识自己，才能认识神。",
     "ref": "诗139:23-24", "text": "神啊，求你鉴察我，知道我的心思，试炼我，知道我的意念，看在我里面有什么恶行没有。"},
    {"key": "past", "name": "面对过去",
     "hint": "我愿意诚实面对原生家庭与过去，对今天的我的影响。",
     "grow": "写下一句你从原生家庭里带来的、至今仍在影响你的模式（比如『不能示弱』『必须被需要』）。回到过去，是为了能真正向前——把它带到神面前，而不是假装它不存在。",
     "ref": "诗139:1", "text": "耶和华啊，你已经鉴察我，认识我。"},
    {"key": "limits", "name": "接受限制",
     "hint": "我能接受自己的限制，能为了更重要的事、对好的事情说『不』。",
     "grow": "这一周，练习对一件『好、但不是你此刻该扛』的事说一次『不』。接受限制不是失败，是承认你是受造者、不是神——这本身就是一种谦卑的敬拜。",
     "ref": "诗103:14", "text": "因为他知道我们的本体，思念我们不过是尘土。"},
    {"key": "grief", "name": "容许哀伤",
     "hint": "我容许自己为失去与失望哀伤，而不总是假装坚强。",
     "grow": "允许自己为一件真实的失去哀伤一次——不急着『快点好起来』或『要感恩』。可以对神说出你的失望。拥抱哀伤，是走向成熟的必经之路，不是软弱。",
     "ref": "诗56:8", "text": "我几次流离，你都记数；求你把我眼泪装在你的皮袋里。"},
    {"key": "sabbath", "name": "安息节奏",
     "hint": "我的生活里有真正安息与停下来的节奏，而不是一直转。",
     "grow": "这一周划出一段（哪怕两小时）真正的安息：不为产出、不刷手机，只是停下、享受神与祂所造的。以安息为节奏，是情绪健康地活出成圣的方式。",
     "ref": "诗23:2", "text": "他使我躺卧在青草地上，领我在可安歇的水边。"},
    {"key": "beneath", "name": "冰山之下",
     "hint": "我愿意察看『冰山之下』——我行为底下的动机、伤口与恐惧。",
     "grow": "下一次你有强烈的情绪反应时，别停在表面，往下问一层：『这底下，我真正害怕或渴望的是什么？』水面下的，才是真正驱动你的。愿意察看它，神就能在那里医治你。",
     "ref": "诗51:6", "text": "你所喜爱的是内里诚实；你在我隐密处，必使我得智慧。"},
]
DIMENSION_INDEX = {d["key"]: d for d in DIMENSIONS}

CRISIS_WORDS = [
    "自杀", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死", "死了算了",
    "伤害自己", "撑不下去了", "没有意义活着", "想消失",
]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = (
    "我听见你正承受很重的痛。在我们一起看这份自我评估之前，我想先温柔地说：如果你有伤害自己的念头，"
    "请现在就联系你信任的人，或当地的心理危机热线——你值得有人此刻真实地陪着你。神爱你，"
    "你不必独自扛。（本功能不替代专业帮助。）"
)


def _clamp01(v: Any) -> float:
    try:
        f = float(v)
    except Exception:
        return 0.5
    if f < 0.0:
        return 0.0
    if f > 1.0:
        return 1.0
    return f


def _weakest(ratings: Dict[str, float], max_n: int = 2) -> List[Dict[str, Any]]:
    """找出自评最低的 1–2 个维度（只在已知维度里比较）。"""
    scored: List[tuple] = []
    for d in DIMENSIONS:
        if d["key"] in (ratings or {}):
            scored.append((_clamp01(ratings[d["key"]]), d))
    if not scored:
        return []
    scored.sort(key=lambda x: x[0])
    lowest = scored[0][0]
    picked = [scored[0][1]]
    # 若第二低与最低非常接近（差 <= 0.15），一并纳入，最多 max_n 个
    for val, d in scored[1:max_n]:
        if val - lowest <= 0.15:
            picked.append(d)
    return picked


def meta() -> Dict[str, Any]:
    """命题 + 冰山比喻 + 六个维度（供前端渲染自评表单）。"""
    return {
        "thesis": THESIS,
        "iceberg": ICEBERG,
        "dimensions": [
            {"key": d["key"], "name": d["name"], "hint": d["hint"]}
            for d in DIMENSIONS
        ],
        "principle": "情绪健康与属灵成熟无法分开：认识自己才能认识神，回到过去才能向前，"
                     "穿越『墙』走向成熟，拥抱限制与哀伤，以安息为节奏活出成圣。",
    }


def assess(ratings: Dict[str, float], text: Optional[str] = None,
           *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    """对六维自评做温柔反映，找出最需关注的维度并给成长步伐（确定性；可选 AI 增强）。"""
    ratings = ratings or {}
    text = (text or "").strip()
    crisis = _detect_crisis(text) if text else False
    weak = _weakest(ratings)

    invitations: List[Dict[str, Any]] = []
    for d in weak:
        invitations.append({
            "key": d["key"], "name": d["name"],
            "your_rating": _clamp01(ratings.get(d["key"], 0.5)),
            "growth_step": d["grow"],
            "scripture": {"ref": d["ref"], "text": d["text"]},
        })

    if weak:
        names = "、".join(d["name"] for d in weak)
        reflection = (
            "先温柔地说清楚：这不是在评判你属灵好不好、情绪健不健康——你不是一个分数。"
            "冰山之下才是真正驱动你的，而你愿意往下看，本身就是勇敢与成熟。"
            "从你的自评看，「" + names + "」也许是神此刻向你发出的成长邀请——不是要你更努力，"
            "是要你更诚实、更被爱。"
        )
    else:
        reflection = (
            "你还没有为这些维度自评，或没有可比较的项。没关系——"
            "情绪健康的第一步，本来就是慢下来、诚实地看自己一眼。"
            "冰山之下才是真正驱动你的，而你愿意往下看，就已经在成长的路上了。"
        )

    result: Dict[str, Any] = {
        "crisis": crisis,
        "crisis_note": CRISIS_NOTE if crisis else "",
        "thesis": THESIS,
        "iceberg": ICEBERG,
        "reflection": reflection,
        "invitations": invitations,
        "summary": (
            "情绪健康与属灵成熟是一起长大的。今天不用全部都做到——"
            "只从上面一个成长邀请开始，让神在你『冰山之下』的地方，温柔地遇见你。"
        ),
        "closing": "「神啊，求你鉴察我，知道我的心思……看在我里面有什么恶行没有，引导我走永生的道路。」（诗139:23-24）",
        "ai_used": False,
    }

    if use_ai:
        enhanced = _ai_enhance(ratings, text, result, settings)
        if enhanced:
            result.update(enhanced)
            result["ai_used"] = True
    return result


def build_prompt(ratings: Dict[str, float], text: Optional[str], base: Dict[str, Any]) -> str:
    weak_names = "、".join(inv["name"] for inv in base.get("invitations", [])) or "（暂无明显偏低项）"
    return (
        "你是一位温柔、以福音为中心的属灵陪伴者，深谙 Peter Scazzero《Emotionally Healthy Spirituality 情商与灵命》。"
        "核心命题：『一个人情感不成熟，却属灵成熟，是不可能的。』冰山比喻：水面上是展示的自己，"
        "水面下是情绪、过去、伤口、动机。请根据用户的六维自评，温柔地反映，绝不评判其属灵/情绪好坏，"
        "把它框成『成长的邀请』而非『你哪里不够』。中文，温暖不说教，不定罪、不贴标签。\n"
        f"用户自评（0–1，越低越需关注）：{json.dumps(ratings, ensure_ascii=False)}\n"
        f"确定性算出最需关注的维度：{weak_names}\n"
        f"用户补充文字：{text or '（无）'}\n"
        "请输出 JSON：{\"reflection\":\"温柔的整体反映，明说这不是评判\","
        "\"invitations\":[{\"key\":\"维度key\",\"growth_step\":\"一个具体可行的成长步伐\"}],"
        "\"summary\":\"...\",\"closing\":\"一句经文\"}。"
    )


def _ai_enhance(ratings: Dict[str, float], text: Optional[str], base: Dict[str, Any],
                settings: Any) -> Optional[Dict[str, Any]]:
    """可选 AI 增强：任何失败都回退（返回 None）。"""
    prompt = build_prompt(ratings, text, base)
    raw = _call_ai(prompt, settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        out: Dict[str, Any] = {}
        if data.get("reflection"):
            out["reflection"] = str(data["reflection"])
        steps = {inv.get("key"): inv.get("growth_step")
                 for inv in data.get("invitations", []) if isinstance(inv, dict)}
        if steps:
            invs = []
            for inv in base.get("invitations", []):
                ni = dict(inv)
                if steps.get(inv["key"]):
                    ni["growth_step"] = str(steps[inv["key"]])
                invs.append(ni)
            out["invitations"] = invs
        if data.get("summary"):
            out["summary"] = str(data["summary"])
        if data.get("closing"):
            out["closing"] = str(data["closing"])
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
    """回流 formation：情绪健康评估属于「成长」；有危机则并入『恐惧』维度并降情绪强度。"""
    if result.get("crisis"):
        return (["growth", "fear"], False, True, 2.0)
    return (["growth"], True, True, 5.0)
