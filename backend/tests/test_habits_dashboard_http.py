"""Exercise the habits dashboard against the real PostgreSQL execution ledger."""
import os

import httpx


def test_today_counts_are_scoped_and_independent_of_dashboard_view():
    base = os.environ["NATIVE_MISSION_LIFE_BASE_URL"]
    owner = {"Authorization": "Bearer " + os.environ["NATIVE_MISSION_LIFE_TOKEN"]}
    outsider = {"Authorization": "Bearer " + os.environ["NATIVE_MISSION_LIFE_OUTSIDER_TOKEN"]}
    with httpx.Client(base_url=base, timeout=10) as client:
        assert client.get("/api/habits/dashboard").status_code == 401
        dashboard = client.get("/api/habits/dashboard", headers=owner)
        dashboard.raise_for_status()
        assert dashboard.json() == {
            "active_habits": 2,
            "today_executions": 3,
            "today_completed_executions": 2,
            "circuit_breaker_count": 1,
            "current_streak": 4,
            "token_balance": 0,
            "last_habit_name": "Morning reading",
        }
        other = client.get("/api/habits/dashboard", headers=outsider)
        other.raise_for_status()
        assert other.json()["today_completed_executions"] == 1
        assert other.json()["today_executions"] == 1
        assert other.json()["active_habits"] == 1
        habits = client.get("/api/habits", headers=owner)
        habits.raise_for_status()
        assert len(habits.json()["items"]) == 2
        habit_id = habits.json()["items"][0]["id"]
        path = f"/api/habits/{habit_id}/log"
        body = {"habit_id": str(habit_id), "was_completed": True,
                "tier_executed": "Green", "completion_percentage": 100}
        assert client.post(path, headers=outsider, json=body).status_code == 404
        written = client.post(path, headers=owner, json=body)
        written.raise_for_status()
        assert written.json()["ok"] is True
        latest = client.get("/api/habits/dashboard", headers=owner)
        latest.raise_for_status()
        assert latest.json()["today_completed_executions"] == 3
        assert latest.json()["today_executions"] == 4
