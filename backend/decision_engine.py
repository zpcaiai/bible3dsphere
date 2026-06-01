"""
decision_engine.py — 决策辨识（司布真版 / Spiritual Discernment Guide，Skill 6）

司布真：神的旨意不是算出来的，而是在与神同行中辨明的。
不像商业顾问分析收益，而是问：哪个选项需要更大信心？产生更大顺服？更反映基督？
被恐惧驱动？被爱驱动？输出：潜在偶像、盲点、信心建议、祷告方向。纯函数 + 可选 AI。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

DIMS = [
    {"key": "faith", "name": "需要的信心", "hint": "哪个选项更需要我信靠神、而非靠自己？"},
    {"key": "obedience", "name": "带来的顺服", "hint": "哪个选项更让我顺服神的心意？"},
    {"key": "love", "name": "出于爱", "hint": "哪个选项更多出于爱神爱人，而非自我？"},
    {"key": "fear", "name": "被恐惧驱动", "hint": "哪个选项更多是恐惧在替我做决定？"},
]


def _n(v):
    try:
        return max(0.0, min(10.0, float(v)))
    except Exception:
        return 0.0


def _score(o: Dict[str, Any]) -> float:
    # 信心导向分：信心+顺服+爱 越高越好，恐惧越高越扣分
    return round((_n(o.get("faith")) + _n(o.get("obedience")) + _n(o.get("love")) + (10 - _n(o.get("fear")))) / 40.0, 4)


def discern(payload: Dict[str, Any]) -> Dict[str, Any]:
    situation = (payload.get("situation") or "").strip()
    raw = payload.get("options") or []
    options = []
    for i, o in enumerate(raw[:2]):
        options.append({
            "label": (o.get("label") or f"选项{chr(65+i)}").strip()[:120],
            "faith": _n(o.get("faith")), "obedience": _n(o.get("obedience")),
            "love": _n(o.get("love")), "fear": _n(o.get("fear")),
            "score": _score(o),
        })
    while len(options) < 2:
        options.append({"label": f"选项{chr(65+len(options))}", "faith": 0, "obedience": 0, "love": 0, "fear": 0, "score": 0})

    a, b = options[0], options[1]
    def cmp(key, hi=True):
        if a[key] == b[key]:
            return None
        return 0 if (a[key] > b[key]) == hi else 1
    questions = {
        "greater_faith": cmp("faith"), "greater_obedience": cmp("obedience"),
        "reflects_christ": cmp("love"), "fear_driven": cmp("fear"),
    }
    recommended = 0 if a["score"] >= b["score"] else 1
    rec, other = options[recommended], options[1 - recommended]

    # 潜在偶像 / 盲点
    idols, blind = [], []
    if a["fear"] >= 6 and b["fear"] >= 6:
        idols.append("两个选项背后都有较强的恐惧——留意安全感 / 控制偶像可能正在替你掌舵。")
    if other["fear"] - rec["fear"] >= 3:
        blind.append(f"留意：「{other['label']}」可能更多是恐惧在替你做决定，而非信心。")
    if rec["faith"] - other["faith"] >= 3:
        blind.append(f"「{rec['label']}」更需要信心——这往往正是神在邀请你成长的方向。")
    if not blind:
        blind.append("两个选项各有信心与恐惧的成分；带到神面前，求祂照明你真实的动机。")

    recommendation = (
        f"从「信心 · 顺服 · 爱、且较少被恐惧驱动」的角度看，「{rec['label']}」更靠近一条"
        f"信心的路。但请记得：这不是计算神的旨意，而是辅助你辨明。最终的指引，在你与神"
        f"安静同行、顺服良心与圣经的过程中渐渐清晰。")
    prayer = (f"主啊，关于这个决定，我不要只问哪条路更安全、更有利，而要问哪条路更讨你喜悦、"
              f"更需要信靠你。求你光照我的动机，赐我顺服的心，在与你同行中让你的旨意向我显明。")

    summary = (f"这不是一道收益计算题，而是一次信心的辨明。" +
               (f"针对「{situation}」，" if situation else "") +
               f"两个选项里，「{rec['label']}」更带着信心与顺服的方向。")

    return {
        "situation": situation, "options": options,
        "questions": questions, "recommended": recommended,
        "idols": idols, "blind_spots": blind,
        "recommendation": recommendation, "prayer": prayer,
        "scripture": {"ref": "箴3:5-6", "text": "你要专心仰赖耶和华……他必指引你的路。"},
        "summary": summary, "source": "deterministic",
    }


def formation_signal(result: Dict[str, Any]):
    return (["growth"], True, True, 4.0)


# ── AI（司布真 Decision Discernment 技能）────────────────────────────────────
def build_prompt(payload: Dict[str, Any], det: Dict[str, Any]) -> List[Dict[str, str]]:
    opts = "\n".join(
        f"- {o['label']}：需要信心{int(o['faith'])}/顺服{int(o['obedience'])}/出于爱{int(o['love'])}/被恐惧驱动{int(o['fear'])}"
        for o in det["options"])
    system = (
        "你是一位属灵辨识向导，按司布真的传统帮助用户辨明决定。司布真强调：神的旨意不是"
        "算出来的，而是在与神同行中辨明的。不要像商业顾问分析收益，而要问：哪个选项需要更大"
        "信心？产生更大顺服？更反映基督？被恐惧驱动？被爱驱动？输出潜在偶像、盲点、信心建议、"
        "祷告方向。温柔、不替神做决定、不施压。只输出 JSON。"
    )
    user = (f"处境：{payload.get('situation','')}\n选项评分：\n{opts}\n\n严格按 JSON："
            '{"summary":"一句辨明","recommendation":"信心建议(不替神决定)","blind_spots":["盲点"],'
            '"idols":["潜在偶像"],"prayer":"祷告方向"}')
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


def analyze(payload: Dict[str, Any], settings: Any = None, use_ai: bool = True) -> Dict[str, Any]:
    det = discern(payload)
    if not use_ai:
        return det
    try:
        try:
            from backend.waiting_engine import call_ai_provider
        except Exception:
            from waiting_engine import call_ai_provider
        ai = call_ai_provider(build_prompt(payload, det), settings=settings)
    except Exception:
        ai = None
    if not ai:
        return det
    if ai.get("summary"): det["summary"] = str(ai["summary"])
    if ai.get("recommendation"): det["recommendation"] = str(ai["recommendation"])
    if ai.get("prayer"): det["prayer"] = str(ai["prayer"])
    if isinstance(ai.get("blind_spots"), list) and ai["blind_spots"]:
        det["blind_spots"] = [str(x) for x in ai["blind_spots"]][:4]
    if isinstance(ai.get("idols"), list):
        det["idols"] = [str(x) for x in ai["idols"]][:4]
    det["source"] = "ai"
    return det


def meta() -> Dict[str, Any]:
    return {"dims": DIMS}
