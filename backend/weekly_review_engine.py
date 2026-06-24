"""
weekly_review_engine.py — 每周复盘聚合引擎 (Skill 5)

输入一周（及上周对照）的打卡 / 操练完成 / 省察(examen)，输出趋势 + 温柔的福音性摘要。
纯逻辑模块（不访问数据库）。原则：不产生"属灵分数"，只给趋势、证据与下一步小行动。

趋势取值：improving / stable / fluctuating / worsening / needs_attention
"""
from __future__ import annotations

import statistics
from typing import Any, Dict, List, Optional

GENERATED_BY = "WeeklyReviewAgent"

# 打卡 data(JSONB) 中可能出现的键（不同前端版本兼容）
_KEYS = {
    "anxiety": ["anxiety_level", "anxiety", "焦虑", "anxiety_intensity"],
    "prayer": ["prayer_engagement", "prayer", "祷告", "prayer_level"],
    "scripture": ["scripture_engagement", "scripture", "读经", "bible", "word_engagement"],
    "mood": ["mood_intensity", "mood", "情绪强度"],
}
_TEXT_KEYS = {
    "struggle": ["main_struggle", "struggle", "挣扎"],
    "gratitude": ["main_gratitude", "gratitude", "感恩"],
    "repentance": ["repentance_note", "repentance", "悔改"],
    "prayer_request": ["prayer_request", "代祷"],
    "obedience": ["obedience_step", "obedience", "顺服"],
}
_TREND_SCORE = {"improving": 2, "stable": 1, "fluctuating": 0, "worsening": -1, "needs_attention": -2}


def _as_float(v: Any) -> Optional[float]:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None


def _series(checkins: List[Dict[str, Any]], concept: str) -> List[float]:
    out: List[float] = []
    for c in checkins or []:
        data = c.get("data") or {}
        if not isinstance(data, dict):
            continue
        for k in _KEYS[concept]:
            if k in data:
                f = _as_float(data[k])
                if f is not None:
                    out.append(f)
                    break
    return out


def _texts(checkins: List[Dict[str, Any]], concept: str) -> List[str]:
    out: List[str] = []
    for c in checkins or []:
        data = c.get("data") or {}
        if not isinstance(data, dict):
            continue
        for k in _TEXT_KEYS[concept]:
            v = data.get(k)
            if isinstance(v, str) and v.strip():
                out.append(v.strip())
                break
    return out


def _mean(xs: List[float]) -> Optional[float]:
    return round(statistics.fmean(xs), 2) if xs else None


def _volatility(xs: List[float]) -> Optional[float]:
    if len(xs) < 2:
        return None
    m = statistics.fmean(xs)
    if m == 0:
        return None
    return statistics.pstdev(xs) / abs(m)


def _classify(cur: Optional[float], prior: Optional[float], *, higher_is_better: bool,
              concern: Optional[tuple] = None, vol: Optional[float] = None) -> str:
    if cur is None:
        return "stable"  # 数据不足
    in_concern = False
    if concern:
        lo, hi = concern
        if (lo is not None and cur <= lo) or (hi is not None and cur >= hi):
            in_concern = True
    if vol is not None and vol >= 0.5:
        return "needs_attention" if in_concern else "fluctuating"
    if prior is None:
        return "needs_attention" if in_concern else "stable"
    delta = cur - prior
    eps = 0.5
    better = delta > eps if higher_is_better else delta < -eps
    worse = delta < -eps if higher_is_better else delta > eps
    if better:
        return "improving"
    if worse:
        return "needs_attention" if in_concern else "worsening"
    return "needs_attention" if in_concern else "stable"


def _completion(task_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(task_logs or [])
    done = sum(1 for t in (task_logs or []) if t.get("completed"))
    help_vals = [_as_float(t.get("perceived_helpfulness")) for t in (task_logs or [])]
    help_vals = [v for v in help_vals if v is not None]
    return {
        "total_logs": total,
        "completed": done,
        "completion_rate": round(done / total, 2) if total else None,
        "avg_helpfulness": _mean(help_vals),
    }


def summarize(week_start: str, week_end: str, *,
              checkins: List[Dict[str, Any]],
              prior_checkins: Optional[List[Dict[str, Any]]] = None,
              task_logs: Optional[List[Dict[str, Any]]] = None,
              examens: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """聚合一周数据，返回与 weekly_reviews 列对齐的 dict。"""
    prior_checkins = prior_checkins or []
    task_logs = task_logs or []
    examens = examens or []

    # —— 数值趋势 ——
    anx, anx_p = _series(checkins, "anxiety"), _series(prior_checkins, "anxiety")
    pray, pray_p = _series(checkins, "prayer"), _series(prior_checkins, "prayer")
    scr, scr_p = _series(checkins, "scripture"), _series(prior_checkins, "scripture")

    trend_anxiety = _classify(_mean(anx), _mean(anx_p), higher_is_better=False,
                              concern=(None, 7), vol=_volatility(anx))
    trend_prayer = _classify(_mean(pray), _mean(pray_p), higher_is_better=True,
                             concern=(3, None), vol=_volatility(pray))
    trend_scripture = _classify(_mean(scr), _mean(scr_p), higher_is_better=True,
                                concern=(3, None), vol=_volatility(scr))

    # community：本周愿意群体代祷 / 写下代祷的次数 vs 上周
    def _community_count(rows):
        n = 0
        for c in rows or []:
            data = c.get("data") or {}
            if not isinstance(data, dict):
                continue
            if data.get("wants_community_prayer") or any(
                isinstance(data.get(k), str) and data.get(k).strip() for k in _TEXT_KEYS["prayer_request"]
            ):
                n += 1
        return n
    comm_cur, comm_prior = _community_count(checkins), _community_count(prior_checkins)
    trend_community = _classify(float(comm_cur), float(comm_prior) if prior_checkins else None,
                                higher_is_better=True)

    comp = _completion(task_logs)
    consolation = [_as_float(e.get("consolation_level")) for e in examens]
    consolation = [v for v in consolation if v is not None]

    # —— 文本证据 ——
    struggles = _texts(checkins, "struggle")
    gratitudes = _texts(checkins, "gratitude") + [e.get("gratitude", "").strip()
                                                  for e in examens if (e.get("gratitude") or "").strip()]
    repentances = _texts(checkins, "repentance") + [e.get("confession", "").strip()
                                                    for e in examens if (e.get("confession") or "").strip()]
    obediences = _texts(checkins, "obedience") + [e.get("tomorrow_step", "").strip()
                                                  for e in examens if (e.get("tomorrow_step") or "").strip()]
    prayer_reqs = _texts(checkins, "prayer_request")

    # —— overall ——
    trends = [trend_anxiety, trend_prayer, trend_scripture, trend_community]
    score = statistics.fmean([_TREND_SCORE[t] for t in trends]) if trends else 1.0
    if score <= -1.0:
        overall = "needs_attention"
    elif score < 0:
        overall = "worsening"
    elif score >= 1.5:
        overall = "improving"
    elif score >= 0.5:
        overall = "stable"
    else:
        overall = "fluctuating"

    # —— 主题 ——
    if trend_anxiety in ("needs_attention", "worsening"):
        main_theme = "在焦虑中学习把无法掌控的交托给神"
    elif trend_prayer == "improving" or trend_scripture == "improving":
        main_theme = "恢复与神的亲近"
    elif comp["completion_rate"] is not None and comp["completion_rate"] >= 0.7:
        main_theme = "在恩典中持续操练顺服"
    else:
        main_theme = "在恩典中重新起步"

    # —— 摘要（基于真实证据，温柔、福音中心）——
    n_checkin = len(checkins)
    prog_bits = [f"本周打卡 {n_checkin} 次"]
    if comp["completion_rate"] is not None:
        prog_bits.append(f"操练完成率 {int(comp['completion_rate'] * 100)}%")
    if trend_prayer == "improving":
        prog_bits.append("祷告参与有上升")
    if consolation:
        prog_bits.append(f"省察中与神的亲近感平均 {_mean(consolation)}/10")
    progress_summary = "；".join(prog_bits) + "。"

    struggle_summary = ("本周较多提到：" + "；".join(struggles[:3]) + "。") if struggles else \
        ("焦虑趋势需要留意。" if trend_anxiety in ("needs_attention", "worsening") else "本周未记录明显挣扎。")

    repentance_summary = ("愿意带到神面前交托/悔改的：" + "；".join(repentances[:3]) + "。") \
        if repentances else "本周未记录具体悔改事项。"

    encouragement_summary = "提醒：你的价值不取决于本周的表现，而是在基督里已经被神接纳。"
    if gratitudes:
        encouragement_summary += "感恩的记号：" + "；".join(gratitudes[:2]) + "。"
    if obediences:
        encouragement_summary += "你已迈出真实的小步：" + "；".join(obediences[:2]) + "。"

    # —— 下一步（1–3 条）——
    steps: List[str] = []
    if trend_anxiety in ("needs_attention", "worsening"):
        steps.append("每天用马太福音6:25-34 或彼得前书5:7 做一次交托祷告")
    if trend_prayer in ("needs_attention", "worsening", "stable") and (not pray or _mean(pray) is None):
        steps.append("固定一个每日祷告的小时段，哪怕只有 5 分钟")
    if comp["completion_rate"] is not None and comp["completion_rate"] < 0.5:
        steps.append("把操练拆小，先完成每天一个核心任务即可")
    if not steps:
        steps.append("保持当前节律，并向一位属灵同伴分享一次本周的真实经历")
    steps = steps[:3]

    suggested_prayer_requests = prayer_reqs[:3] or (
        ["求神帮助我把焦虑交托给祂，把价值建立在基督里"] if trend_anxiety in ("needs_attention", "worsening") else []
    )

    return {
        "week_start": week_start,
        "week_end": week_end,
        "main_theme": main_theme,
        "progress_summary": progress_summary,
        "struggle_summary": struggle_summary,
        "repentance_summary": repentance_summary,
        "encouragement_summary": encouragement_summary,
        "trend_anxiety": trend_anxiety,
        "trend_prayer": trend_prayer,
        "trend_scripture": trend_scripture,
        "trend_community": trend_community,
        "overall_trend": overall,
        "metrics": {
            "checkin_count": n_checkin,
            "anxiety_mean": _mean(anx), "anxiety_mean_prior": _mean(anx_p),
            "prayer_mean": _mean(pray), "prayer_mean_prior": _mean(pray_p),
            "scripture_mean": _mean(scr), "scripture_mean_prior": _mean(scr_p),
            "consolation_mean": _mean(consolation),
            "community_count": comm_cur, "community_count_prior": comm_prior,
            **comp,
        },
        "recommended_next_steps": steps,
        "suggested_prayer_requests": suggested_prayer_requests,
        "generated_by_agent": GENERATED_BY,
    }


def meta() -> Dict[str, Any]:
    return {"generated_by": GENERATED_BY,
            "trends": ["improving", "stable", "fluctuating", "worsening", "needs_attention"]}
