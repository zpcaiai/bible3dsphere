"""Unit tests for the stronghold aggregation (pure, no DB).

Mirrors the frontend lib/strongholdHistory.test.ts so cloud + local stay in parity.
"""
from datetime import datetime, timezone

from routers.strongholds import summarize_records, build_insight

NOW = int(datetime(2026, 6, 19, tzinfo=timezone.utc).timestamp() * 1000)
DAY = 24 * 60 * 60 * 1000


def days_ago(n: int) -> str:
    return datetime.fromtimestamp((NOW - n * DAY) / 1000, tz=timezone.utc).isoformat()


def rec(**kw) -> dict:
    base = {
        "date": days_ago(1),
        "primaryCode": "control_idolatry",
        "archetypeCode": "self_sovereignty",
        "blockedDoctrineCode": "god_sovereignty",
        "triggerType": None,
        "emotions": [],
        "detectedCodes": ["control_idolatry"],
    }
    base.update(kw)
    return base


RECORDS = [
    rec(primaryCode="control_idolatry", archetypeCode="self_sovereignty", triggerType="uncertainty", date=days_ago(20)),
    rec(primaryCode="control_idolatry", archetypeCode="self_sovereignty", triggerType="uncertainty", date=days_ago(5)),
    rec(primaryCode="control_idolatry", archetypeCode="self_sovereignty", triggerType="criticism", date=days_ago(3)),
    rec(primaryCode="achievement_idolatry", archetypeCode="performance_righteousness", triggerType="comparison", date=days_ago(22)),
    rec(primaryCode="achievement_idolatry", archetypeCode="performance_righteousness", triggerType="comparison", date=days_ago(21)),
    rec(primaryCode="nihilism", archetypeCode="wounded_unbelief", triggerType=None, date=days_ago(40)),  # outside 30d
]


def test_range_filtering():
    assert summarize_records(RECORDS, 30, NOW)["totalScans"] == 5
    assert summarize_records(RECORDS, 90, NOW)["totalScans"] == 6


def test_top_strongholds_and_trend():
    s = summarize_records(RECORDS, 30, NOW)
    assert s["topStrongholds"][0]["code"] == "control_idolatry"
    assert s["topStrongholds"][0]["count"] == 3
    assert s["topStrongholds"][0]["trend"] == "rising"
    ach = next(x for x in s["topStrongholds"] if x["code"] == "achievement_idolatry")
    assert ach["trend"] == "falling"


def test_triggers_linked():
    s = summarize_records(RECORDS, 30, NOW)
    unc = next(t for t in s["topTriggers"] if t["type"] == "uncertainty")
    assert unc["count"] == 2
    assert "control_idolatry" in unc["linkedStrongholds"]
    comp = next(t for t in s["topTriggers"] if t["type"] == "comparison")
    assert "achievement_idolatry" in comp["linkedStrongholds"]


def test_archetype_distribution():
    s = summarize_records(RECORDS, 30, NOW)
    sov = next(a for a in s["archetypeDistribution"] if a["code"] == "self_sovereignty")
    assert sov["count"] == 3


def test_build_insight():
    s = summarize_records(RECORDS, 30, NOW)
    insight = build_insight(s)
    assert insight["hasData"] is True
    assert insight["focus"]["strongholdCode"] == "control_idolatry"
    assert insight["focus"]["topTrigger"] == "uncertainty"
    assert any(g["strongholdCode"] == "achievement_idolatry" for g in insight["growthSignals"])


def test_insight_needs_two_scans():
    one = summarize_records([RECORDS[0]], 30, NOW)
    assert build_insight(one)["hasData"] is False


# ── Profile + progress (merge stronghold scans + daily examens) ──
from routers.strongholds import build_profile, build_progress  # noqa: E402


def _daily(n_days_ago, primary, emotion):
    return {"date": days_ago(n_days_ago)[:10], "emotion": emotion,
            "triggers": [], "sinPatterns": [primary], "primarySin": primary}


DAILY = [_daily(2, "pride", "焦虑"), _daily(10, "self_centeredness", "羞耻")]


def test_profile_merges_dimensions_and_rhythm():
    prof = build_profile(RECORDS[:5], DAILY, 90, NOW)
    assert prof["stronghold"]["dominant"][0]["code"] == "control_idolatry"
    assert any(b["code"] == "god_sovereignty" for b in prof["stronghold"]["blockedDoctrines"])
    assert any(d["code"] == "pride" for d in prof["sinPattern"]["dominant"])
    assert prof["rhythm"]["dailyExamens"] == 2
    assert prof["rhythm"]["strongholdScans"] == 5
    assert prof["rhythm"]["activeDays"] >= 6
    assert prof["encouragements"]


def test_progress_direction_and_signals():
    prog = build_progress(RECORDS[:5], DAILY, 30, NOW)
    assert prog["overallTrend"] in ("growing", "stable", "struggling")
    assert prog["awarenessScore"] >= 0
    assert any(g["strongholdCode"] == "achievement_idolatry" for g in prog["growthSignals"])
    assert any(s["strongholdCode"] == "control_idolatry" for s in prog["struggleSignals"])


def test_progress_insufficient_data():
    prog = build_progress(RECORDS[:1], [], 30, NOW)
    assert prog["overallTrend"] == "insufficient_data"
