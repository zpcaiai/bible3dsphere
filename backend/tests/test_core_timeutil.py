"""ISO 8601 parsing must not depend on which Python happens to be running.

The API emits `Z`-suffixed UTC timestamps (Pydantic v2 `model_dump(mode="json")`),
but `datetime.fromisoformat` only accepts `Z` from Python 3.11. CI runs 3.11, so a
service that cannot parse its own output would look perfectly healthy right up until
it ran on an older interpreter.
"""
from __future__ import annotations

import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from core.timeutil import ensure_aware, parse_iso8601, parse_iso8601_date, to_iso8601


pytestmark = pytest.mark.no_db
BACKEND = Path(__file__).resolve().parents[1]


# ── 核心：Z 后缀 ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("value", [
    "2026-07-28T08:32:29Z",
    "2026-07-28T08:32:29.304396Z",
    "2026-07-28T08:32:29z",
    "  2026-07-28T08:32:29Z  ",
])
def test_z_suffix_parses_on_every_python(value):
    parsed = parse_iso8601(value)
    assert parsed.utcoffset() == timezone.utc.utcoffset(None)
    assert parsed.year == 2026 and parsed.month == 7 and parsed.day == 28


def test_this_is_the_case_the_stdlib_used_to_reject():
    """Documents the defect: on <3.11 the stdlib raises on the app's own output."""
    if sys.version_info < (3, 11):
        with pytest.raises(ValueError):
            datetime.fromisoformat("2026-07-28T08:32:29Z")
    assert parse_iso8601("2026-07-28T08:32:29Z") is not None


def test_explicit_offsets_are_preserved():
    parsed = parse_iso8601("2026-07-28T09:00:00+08:00")
    assert parsed.utcoffset().total_seconds() == 8 * 3600


def test_naive_timestamps_are_treated_as_utc_not_local():
    parsed = parse_iso8601("2026-07-28T08:32:29")
    assert parsed.tzinfo is not None
    assert parsed.utcoffset().total_seconds() == 0


def test_a_datetime_passes_through_and_gains_a_timezone():
    naive = datetime(2026, 7, 28, 8, 32, 29)
    assert parse_iso8601(naive).tzinfo is not None
    aware = datetime(2026, 7, 28, 8, 32, 29, tzinfo=timezone.utc)
    assert parse_iso8601(aware) == aware


@pytest.mark.parametrize("value", ["", "   ", "not-a-date", "2026-13-45T99:99:99Z"])
def test_garbage_raises_value_error_so_callers_can_return_4xx(value):
    with pytest.raises(ValueError):
        parse_iso8601(value)


# ── 日期 ─────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("value,expected", [
    ("2026-07-28", date(2026, 7, 28)),
    ("2026-07-28T08:32:29Z", date(2026, 7, 28)),
    ("2026-07-28T08:32:29+08:00", date(2026, 7, 28)),
    (datetime(2026, 7, 28, 8, tzinfo=timezone.utc), date(2026, 7, 28)),
    (date(2026, 7, 28), date(2026, 7, 28)),
])
def test_dates_accept_both_bare_dates_and_full_timestamps(value, expected):
    assert parse_iso8601_date(value) == expected


def test_bad_dates_still_raise():
    with pytest.raises(ValueError):
        parse_iso8601_date("yesterday")


# ── 往返 ─────────────────────────────────────────────────────────────────────

def test_round_trip_is_stable():
    original = "2026-07-28T08:32:29.304396Z"
    once = parse_iso8601(original)
    assert parse_iso8601(to_iso8601(once)) == once


def test_serialisation_never_emits_a_naive_timestamp():
    assert re.search(r"(\+|-)\d{2}:\d{2}$", to_iso8601(datetime(2026, 7, 28, 8, 32, 29)))


def test_ensure_aware_leaves_an_aware_datetime_alone():
    aware = datetime(2026, 7, 28, tzinfo=timezone.utc)
    assert ensure_aware(aware) is aware


# ── 调用点确实收敛到了同一个实现 ─────────────────────────────────────────────

CALLERS = (
    "user_profile_tag_system.py",
    "routers/mission_deployment.py",
    "routers/mission_claims.py",
)


@pytest.mark.parametrize("relative", CALLERS)
def test_call_sites_no_longer_parse_iso_timestamps_by_hand(relative):
    text = (BACKEND / relative).read_text(encoding="utf-8")
    leftovers = [
        line.strip() for line in text.splitlines()
        if "datetime.fromisoformat(" in line
    ]
    assert leftovers == [], f"{relative} 仍在手工解析 ISO 时间戳: {leftovers}"


@pytest.mark.parametrize("relative", CALLERS)
def test_call_sites_import_the_shared_parser(relative):
    text = (BACKEND / relative).read_text(encoding="utf-8")
    assert "core.timeutil" in text


def test_no_new_hand_rolled_z_workarounds_creep_back_in():
    """`.replace("Z", "+00:00")` 是这个 bug 的老补丁，新代码不该再出现。"""
    offenders = []
    for path in sorted(BACKEND.glob("routers/*.py")):
        text = path.read_text(encoding="utf-8")
        if 'fromisoformat' in text and 'replace("Z"' not in text and "replace('Z'" not in text:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if "fromisoformat" in line and ("replace(\"Z\"" in line or "replace('Z'" in line):
                offenders.append(f"{path.name}:{number}")
    # 既有补丁允许保留，但数量不得增长——超过基线说明又有人手写了一遍
    assert len(offenders) <= 8, f"hand-rolled Z workarounds growing: {offenders}"


def test_requirements_declare_each_dependency_once():
    """A duplicated pin is a silent merge hazard: two lines, two chances to drift."""
    import re
    from collections import Counter

    text = (BACKEND / "requirements.txt").read_text(encoding="utf-8")
    names = [
        re.split(r"[<>=;\[]", line, 1)[0].strip().lower()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    duplicates = [name for name, count in Counter(names).items() if count > 1]
    assert duplicates == [], f"declared more than once: {duplicates}"
