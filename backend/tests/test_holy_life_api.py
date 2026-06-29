"""HTTP-level tests for Holy Life Engine persistence endpoints."""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers import spiritual_formation as sf

pytestmark = pytest.mark.no_db


def _unwrap_json(value):
    return getattr(value, "adapted", value)


class FakeCursor:
    def __init__(self, store):
        self.store = store
        self._one = None
        self._many = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=None):
        params = params or ()
        if "INSERT INTO spiritual_holy_life_day_logs" in sql:
            (
                log_id,
                user_id,
                log_date,
                intention,
                entries,
                presence_logs,
                rule_of_life,
                purpose_review,
                decision_sanctification_logs,
                daily_report,
                tomorrow_formation,
            ) = params
            now = datetime(2026, 6, 29, 12, 0, tzinfo=timezone.utc)
            key = (user_id, str(log_date))
            created_at = self.store.get(key, {}).get("created_at", now)
            record = {
                "id": log_id,
                "user_id": user_id,
                "date": log_date,
                "intention": intention,
                "entries": _unwrap_json(entries),
                "presence_logs": _unwrap_json(presence_logs),
                "rule_of_life": _unwrap_json(rule_of_life),
                "purpose_review": _unwrap_json(purpose_review),
                "decision_sanctification_logs": _unwrap_json(decision_sanctification_logs),
                "daily_report": daily_report,
                "tomorrow_formation": tomorrow_formation,
                "created_at": created_at,
                "updated_at": now,
            }
            self.store[key] = record
            self._one = self._row(record)
            return

        if "FROM spiritual_holy_life_day_logs" not in sql:
            self._one = None
            self._many = []
            return

        if "WHERE user_id=%s ORDER BY" in sql:
            user_id, limit = params
            rows = [r for r in self.store.values() if r["user_id"] == user_id]
            rows.sort(key=lambda r: str(r["date"]), reverse=True)
            self._many = [self._row(r) for r in rows[:limit]]
            return

        if "WHERE user_id=%s AND date=%s" in sql:
            user_id, log_date = params
            self._one = self._row(self.store.get((user_id, str(log_date)))) if (user_id, str(log_date)) in self.store else None
            return

        if "WHERE id=%s AND user_id=%s" in sql:
            log_id, user_id = params
            match = next((r for r in self.store.values() if r["id"] == log_id and r["user_id"] == user_id), None)
            self._one = self._row(match) if match else None
            return

        if "WHERE user_id=%s AND date >= %s" in sql:
            user_id, since = params
            rows = [r for r in self.store.values() if r["user_id"] == user_id and r["date"] >= since]
            self._many = [self._row(r) for r in rows]
            return

        self._one = None
        self._many = []

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._many

    @staticmethod
    def _row(record):
        if not record:
            return None
        return (
            record["id"],
            record["user_id"],
            record["date"],
            record["intention"],
            record["entries"],
            record["presence_logs"],
            record.get("rule_of_life") or {},
            record.get("purpose_review") or {},
            record.get("decision_sanctification_logs") or [],
            record["daily_report"],
            record["tomorrow_formation"],
            record["created_at"],
            record["updated_at"],
        )


class FakeConn:
    def __init__(self, store):
        self.store = store

    def cursor(self):
        return FakeCursor(self.store)

    def commit(self):
        return None

    def rollback(self):
        return None


@pytest.fixture
def holy_life_client():
    previous_state = dict(sf._state)
    store = {}
    app = FastAPI()
    sf.init_spiritual_formation_router(
        get_db=lambda: FakeConn(store),
        release_db=lambda _conn: None,
        get_session_user=lambda _request: {"email": "user@example.com"},
        to_shanghai_iso=lambda dt: dt.isoformat() if dt else None,
    )
    app.include_router(sf.router)
    try:
        yield TestClient(app)
    finally:
        sf._state.clear()
        sf._state.update(previous_state)


def test_holy_life_day_log_roundtrip_and_summary(holy_life_client):
    log_date = date.today().isoformat()
    payload = {
        "id": "client_supplied_id_is_ignored",
        "date": log_date,
        "intention": "Offer the day to God",
        "entries": [
            {
                "skillId": "morning_consecration",
                "score": 80,
                "reflection": "I surrendered my work.",
                "completed": True,
                "updatedAt": "2026-06-29T08:00:00Z",
            }
        ],
        "presenceLogs": [
            {
                "id": "presence_1",
                "createdAt": "2026-06-29T09:00:00Z",
                "reflection": "Observe, repent, return.",
            }
        ],
        "ruleOfLife": {
            "theme": "Purpose Reset",
            "morningPrayer": "Offer the day",
            "dailyPractice": "Review ordinary duties",
            "decisionGuardrail": "Choose love and truth",
            "eveningExamen": "Review fidelity",
            "generatedAt": "2026-06-29T08:10:00Z",
        },
        "purposeReview": {
            "callingStatement": "Faithful stewardship today",
            "stewardshipFocus": "Work and speech",
            "misalignment": "Self-protection",
            "nextFaithfulAction": "Practice humility",
        },
        "decisionSanctificationLogs": [
            {
                "id": "decision_1",
                "createdAt": "2026-06-29T10:00:00Z",
                "decision": "Have a difficult conversation",
                "motive": "Truth in love",
                "desireToSurrender": "Approval",
                "scriptureAnchor": "Romans 12:1-2",
                "obedienceStep": "Speak gently",
            }
        ],
        "dailyReport": "Daily report",
        "tomorrowFormation": "Practice humility",
    }

    created = holy_life_client.post("/api/spiritual-formation/holy-life/day-logs", json=payload)
    assert created.status_code == 200
    day_log = created.json()["dayLog"]
    assert day_log["id"] == f"holy_life_user@example.com_{log_date}"
    assert day_log["entries"][0]["skillId"] == "morning_consecration"
    assert day_log["ruleOfLife"]["theme"] == "Purpose Reset"
    assert day_log["purposeReview"]["callingStatement"] == "Faithful stewardship today"
    assert day_log["decisionSanctificationLogs"][0]["decision"] == "Have a difficult conversation"

    listed = holy_life_client.get("/api/spiritual-formation/holy-life/day-logs")
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 1

    today = holy_life_client.get(f"/api/spiritual-formation/holy-life/today?date={log_date}")
    assert today.status_code == 200
    assert today.json()["dayLog"]["dailyReport"] == "Daily report"

    summary = holy_life_client.get("/api/spiritual-formation/holy-life/summary?days=365")
    assert summary.status_code == 200
    body = summary.json()
    assert body["logCount"] == 1
    assert body["presencePauseCount"] == 1
    assert body["purposeReviewCount"] == 1
    assert body["decisionLogCount"] == 1
    assert body["averageScore"] == 80
