"""
virtues_engine.py — 第七大陆 · 信望爱星系 / Faith-Hope-Love Formation Engine（Skill 7）

把 formation 八维（state_vector）汇成「信靠 / 盼望 / 爱人 / 像基督」四大指数，
并评估 9 个属灵品格（信/望/爱/谦卑/顺服/圣洁/智慧/勇气/忍耐）：当前水平 + 经文 +
推荐操练 + 成长方向。纯函数；AI 走 Faith-Hope-Love 技能 Prompt，失败回退。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional


def _g(sv: Dict[str, Any], k: str, default: float = 0.5) -> float:
    try:
        return max(0.0, min(1.0, float(sv.get(k, default))))
    except Exception:
        return default


def _mean(*xs: float) -> float:
    return round(sum(xs) / len(xs), 4) if xs else 0.0


# 9 品格：从八维推导 + 经文 + 操练 + 成长方向
VIRTUES: List[Dict[str, Any]] = [
    {"key": "faith", "name": "信靠", "en": "Faith", "color": "#5ac8fa",
     "scripture": {"ref": "来11:1", "text": "信就是所望之事的实底，是未见之事的确据。"},
     "practice": "今天把一件最难交托的事，明确地交在神手中。",
     "grow": "信心在「不得不依靠神」的处境里长大——别躲开它。"},
    {"key": "hope", "name": "盼望", "en": "Hope", "color": "#51cf66",
     "scripture": {"ref": "罗15:13", "text": "但愿使人有盼望的神……叫你们大有盼望。"},
     "practice": "写下一件你正绝望的事，旁边写：「但神仍坐在宝座上。」",
     "grow": "盼望不是乐观，是确信神必不撇下你——常默想祂的应许。"},
    {"key": "love", "name": "爱", "en": "Love", "color": "#ff8787",
     "scripture": {"ref": "约一4:19", "text": "我们爱，因为神先爱我们。"},
     "practice": "今天主动去关心、服事或理解一个人。",
     "grow": "爱从被爱里流出——先饱享神的爱，再去爱人。"},
    {"key": "humility", "name": "谦卑", "en": "Humility", "color": "#a78bfa",
     "scripture": {"ref": "腓2:3", "text": "只要存心谦卑，各人看别人比自己强。"},
     "practice": "今天承认一次「我错了」或主动让一次。",
     "grow": "谦卑是看见恩典——你所有的都是领受的。"},
    {"key": "obedience", "name": "顺服", "en": "Obedience", "color": "#4ecdc4",
     "scripture": {"ref": "约14:15", "text": "你们若爱我，就必遵守我的命令。"},
     "practice": "在一件你一直拖延的顺服上，今天迈出第一步。",
     "grow": "顺服是爱的表达，不是规条的捆绑。"},
    {"key": "holiness", "name": "圣洁", "en": "Holiness", "color": "#ffd43b",
     "scripture": {"ref": "彼前1:16", "text": "你们要圣洁，因为我是圣洁的。"},
     "practice": "今天对一个试探说「不」，并转向基督。",
     "grow": "圣洁不是靠咬牙，是靠尝到基督比罪更甘甜。"},
    {"key": "wisdom", "name": "智慧", "en": "Wisdom", "color": "#fcbad3",
     "scripture": {"ref": "雅1:5", "text": "你们中间若有缺少智慧的，应当求那厚赐与众人的神。"},
     "practice": "今天一个决定前，先停下来祷告求智慧。",
     "grow": "智慧始于敬畏耶和华——把神放在每个判断的中心。"},
    {"key": "courage", "name": "勇气", "en": "Courage", "color": "#ffa94d",
     "scripture": {"ref": "书1:9", "text": "你当刚强壮胆……因为你无论往哪里去，耶和华你的神必与你同在。"},
     "practice": "今天做一件你因恐惧而一直回避的对的事。",
     "grow": "勇气不是不怕，是怕的时候仍然信靠那位与你同在的神。"},
    {"key": "perseverance", "name": "忍耐", "en": "Perseverance", "color": "#2dd4bf",
     "scripture": {"ref": "加6:9", "text": "我们行善，不可丧志；若不灰心，到了时候就要收成。"},
     "practice": "在一件你想放弃的事上，今天只忠心再走一小步。",
     "grow": "忍耐在等候里被炼成——把收成交给神的时间。"},
]
VIRTUE_INDEX = {v["key"]: v for v in VIRTUES}


def _derive(sv: Dict[str, Any]) -> Dict[str, float]:
    hum = _g(sv, "humility"); es = _g(sv, "emotional_stability"); ta = _g(sv, "truth_alignment")
    rh = _g(sv, "relational_health"); res = _g(sv, "resilience"); sc = _g(sv, "spiritual_clarity")
    fear = _g(sv, "fear_tendency"); pride = _g(sv, "pride_tendency")
    return {
        "faith": _mean(ta, sc, 1 - fear),
        "hope": _mean(res, sc, es),
        "love": _mean(rh, hum),
        "humility": _mean(hum, 1 - pride),
        "obedience": _mean(ta, hum),
        "holiness": _mean(ta, sc),
        "wisdom": _mean(ta, es),
        "courage": _mean(1 - fear, res),
        "perseverance": _mean(res, es),
    }


def _level(x: float) -> str:
    return "萌芽" if x < 0.4 else "成长中" if x < 0.6 else "渐丰盛" if x < 0.8 else "丰盛"


def evaluate(state_vector: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    sv = state_vector or {}
    has = bool(sv)
    scores = _derive(sv) if has else {v["key"]: 0.0 for v in VIRTUES}

    indices = {
        "faith": scores["faith"], "hope": scores["hope"], "love": scores["love"],
        "christlikeness": _mean(scores["faith"], scores["hope"], scores["love"], scores["humility"]),
    }
    virtues = []
    for v in VIRTUES:
        s = scores[v["key"]]
        virtues.append({"key": v["key"], "name": v["name"], "en": v["en"], "color": v["color"],
                        "score": s, "level": _level(s),
                        "scripture": v["scripture"], "practice": v["practice"], "grow": v["grow"]})
    # 成长亮点 / 待培育
    ranked = sorted(virtues, key=lambda x: x["score"], reverse=True)
    top = ranked[0]["name"] if has else ""
    low = ranked[-1]["name"] if has else ""
    summary = (f"你最明亮的品格是「{top}」，而「{low}」正等候被神培育——"
               f"成长不是补短板的焦虑，是让基督的生命在每一维里更丰满。" if has
               else "完成一些打卡与省察，星系就会被你真实的属灵动态点亮。")
    return {"has_data": has, "indices": indices, "virtues": virtues,
            "summary": summary, "source": "deterministic"}


# ── AI（Faith-Hope-Love 技能 Prompt）─────────────────────────────────────────
def build_prompt(evaluation: Dict[str, Any]) -> List[Dict[str, str]]:
    lines = "\n".join(f"- {v['name']}({v['en']}): {int(v['score']*100)} · {v['level']}"
                      for v in evaluation["virtues"])
    system = (
        "你按照属灵形成的 Faith-Hope-Love 引擎评估用户的品格成长。对每个维度温柔地给出："
        "当前水平、支持证据、成长机会、推荐操练、推荐经文、推荐属灵练习。"
        "不定罪、不制造焦虑，导向在基督里更丰盛的生命。只输出一个 JSON 对象。"
    )
    user = (f"用户当前 9 维属灵品格：\n{lines}\n\n请给一段温柔的总体评估与方向，"
            '严格按 JSON：{"summary":"总体评估与下一步方向(120-200字)"}')
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


def analyze(state_vector: Optional[Dict[str, Any]], settings: Any = None, use_ai: bool = True) -> Dict[str, Any]:
    out = evaluate(state_vector)
    if not use_ai or not out["has_data"]:
        return out
    try:
        try:
            from backend.waiting_engine import call_ai_provider
        except Exception:
            from waiting_engine import call_ai_provider
        ai = call_ai_provider(build_prompt(out), settings=settings)
    except Exception:
        ai = None
    if ai and ai.get("summary"):
        out["summary"] = str(ai["summary"])
        out["source"] = "ai"
    return out
