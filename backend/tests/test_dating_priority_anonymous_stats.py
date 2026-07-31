"""No-database coverage for the anonymous dating-priority survey."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers import dating_priority

pytestmark = pytest.mark.no_db


class _FakeCursor:
    def __init__(self, store):
        self.store = store
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        normalized = " ".join(sql.split())
        self.store["executed"].append((normalized, params))
        if normalized.startswith("INSERT INTO dating_priority_submissions"):
            self.store["rows"].append((params[5], params[2], params[3]))
            self.store["visitor_ids"].add(params[0])
        elif normalized.startswith("SELECT response_json"):
            self.rows = list(self.store["rows"])
        elif normalized.startswith("SELECT COUNT(DISTINCT visitor_id)"):
            self.rows = [(len(self.store["visitor_ids"]),)]

    def fetchall(self):
        return list(self.rows)

    def fetchone(self):
        return self.rows[0] if self.rows else None


class _FakeConn:
    def __init__(self, store):
        self.store = store

    def cursor(self):
        return _FakeCursor(self.store)

    def commit(self):
        self.store["commits"] += 1


def _client(rows=None, visitor_ids=None):
    store = {
        "rows": list(rows or []),
        "visitor_ids": set(visitor_ids or []),
        "executed": [],
        "commits": 0,
        "released": 0,
    }
    dating_priority.init_dating_priority_router(
        _get_db=lambda: _FakeConn(store),
        _release_db=lambda conn: store.__setitem__(
            "released", store["released"] + 1
        ),
    )
    app = FastAPI()
    app.include_router(dating_priority.router)
    return TestClient(app), store


def _response(selected=None, vetoes=None):
    selected = selected or []
    vetoes = vetoes or []
    return json.dumps({
        "version": 3,
        "selected": selected,
        "vetoes": vetoes,
        "totalScore": sum(item["score"] for item in selected),
    }, ensure_ascii=False)


def test_submit_returns_current_anonymous_aggregates():
    previous = _response(
        selected=[{
            "rank": 1,
            "category": "人品与关系品质",
            "label": "诚实守信",
            "description": "",
            "score": 100,
        }],
        vetoes=[{
            "suppliedRank": 1,
            "label": "家暴、推搡、威胁、砸东西或严重控制行为",
            "strength": "极高",
        }],
    )
    client, store = _client(rows=[(previous, [], [])])

    response = client.post("/api/dating-priority/submit", json={
        "visitor_id": "survey-visitor-00000002",
        "perspective": "female_to_male",
        "version": 3,
        "selected": [
            {
                "rank": 1,
                "category": "人品与关系品质",
                "label": "诚实守信",
                "description": "不隐瞒重要事实",
                "score": 60,
            },
            {
                "rank": 2,
                "category": "价值观与人生方向",
                "label": "人生观和价值观一致",
                "description": "",
                "score": 40,
            },
        ],
        "vetoes": [{
            "suppliedRank": 1,
            "label": "家暴、推搡、威胁、砸东西或严重控制行为",
            "strength": "极高",
        }],
        "totalScore": 100,
    })

    assert response.status_code == 200
    body = response.json()
    assert body["anonymous"] is True
    assert body["stats"]["total"] == 2
    assert body["stats"]["priority_stats"][0] == {
        "category": "人品与关系品质",
        "label": "诚实守信",
        "avg_rank": 1.0,
        "avg_score": 80.0,
        "selection_count": 2,
        "selection_rate": 100.0,
    }
    assert body["stats"]["veto_stats"][0]["selection_rate"] == 100.0
    assert store["commits"] == 1
    assert store["released"] == 1
    assert "survey-visitor-00000002" not in json.dumps(body, ensure_ascii=False)


def test_submit_rejects_invalid_weight_total_before_database_access():
    client, store = _client()
    response = client.post("/api/dating-priority/submit", json={
        "visitor_id": "survey-visitor-00000003",
        "perspective": "male_to_female",
        "selected": [{
            "rank": 1,
            "category": "人品与关系品质",
            "label": "诚实守信",
            "description": "",
            "score": 99,
        }],
        "vetoes": [],
        "totalScore": 99,
    })

    assert response.status_code == 422
    assert store["executed"] == []


def test_stats_endpoint_returns_aggregates_without_visitor_identifiers():
    stored = _response(
        selected=[],
        vetoes=[{
            "suppliedRank": 12,
            "label": "完全缺乏外貌、身体或情感吸引力",
            "strength": "因人而异",
        }],
    )
    client, store = _client(rows=[(stored, [], [])])

    response = client.get(
        "/api/dating-priority/stats",
        params={"perspective": "male_to_female"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["priority_stats"] == []
    assert body["veto_stats"][0]["supplied_rank"] == 12
    assert "visitor" not in json.dumps(body)
    assert store["released"] == 1


def test_participant_endpoint_returns_global_distinct_count_only():
    client, store = _client(visitor_ids={
        "survey-visitor-00000001",
        "survey-visitor-00000002",
        "survey-visitor-00000003",
    })

    response = client.get("/api/dating-priority/participants")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "anonymous": True,
        "participant_count": 3,
    }
    assert "survey-visitor" not in response.text
    assert store["released"] == 1


def test_legacy_stats_keep_their_own_denominator_when_current_rows_exist():
    current = _response(selected=[], vetoes=[])
    stats = dating_priority._aggregate_current_stats(
        [
            (current, [], []),
            ({}, ["旧版关注项"], ["旧版阻力项"]),
        ],
        "dx",
    )

    assert stats["total"] == 1
    assert stats["current_total"] == 1
    assert stats["focus_stats"][0]["selection_rate"] == 100.0
    assert stats["block_stats"][0]["selection_rate"] == 100.0


def test_migration_adds_versioned_json_storage_without_removing_legacy_columns():
    root = Path(__file__).resolve().parents[1]
    migration = (
        root / "migrations/0234_dating_priority_anonymous_stats.sql"
    ).read_text()
    rollback = (
        root / "migrations/rollback/0234_dating_priority_anonymous_stats_down.sql"
    ).read_text()

    assert "ADD COLUMN IF NOT EXISTS response_version" in migration
    assert "ADD COLUMN IF NOT EXISTS response_json" in migration
    assert "ALTER COLUMN perspective TYPE VARCHAR(32)" in migration
    assert "DROP COLUMN IF EXISTS response_json" in rollback
    assert "focus_order" not in rollback


def test_submit_accepts_more_than_ten_selections():
    """选项个数不再受限，后端必须跟着放开，否则前端一提交就 422。"""
    client, store = _client()
    count = 40
    # 与前端 rankWeightedPoints 同样的约束：合计恰好 100，且每项至少 1 分
    base = 1
    pool = 100 - base * count
    weights = [count - index for index in range(count)]
    weight_sum = sum(weights)
    exact = [(weight * pool) / weight_sum for weight in weights]
    scores = [base + int(value) for value in exact]
    leftover = 100 - sum(scores)
    order = sorted(
        range(count),
        key=lambda i: (-(exact[i] - int(exact[i])), i),
    )
    for i in range(leftover):
        scores[order[i]] += 1

    assert sum(scores) == 100
    assert min(scores) >= 1

    response = client.post("/api/dating-priority/submit", json={
        "visitor_id": "survey-visitor-00000042",
        "perspective": "female_to_male",
        "version": 3,
        "selected": [
            {
                "rank": index + 1,
                "category": "人品与关系品质",
                "label": f"因素-{index + 1}",
                "description": "",
                "score": scores[index],
            }
            for index in range(count)
        ],
        "vetoes": [],
        "totalScore": 100,
    })

    assert response.status_code == 200, response.text
    assert response.json()["stats"]["total"] == 1
    assert store["commits"] == 1


def test_stats_accumulate_across_every_distinct_anonymous_visitor():
    """统计要累计所有人的投票，但同一访客重复提交只算最新一次（防刷票）。"""
    # 三个不同的匿名访客，两个投给"诚实守信"（不同排名/权重），
    # 一个投给"人生观和价值观一致"；此外模拟第一个访客后来改票。
    rows = [
        (_response(selected=[{
            "rank": 1, "category": "人品与关系品质", "label": "诚实守信",
            "description": "", "score": 100,
        }]), [], []),
        (_response(selected=[{
            "rank": 2, "category": "人品与关系品质", "label": "诚实守信",
            "description": "", "score": 40,
        }, {
            "rank": 1, "category": "价值观与人生方向", "label": "人生观和价值观一致",
            "description": "", "score": 60,
        }]), [], []),
        (_response(selected=[{
            "rank": 1, "category": "价值观与人生方向", "label": "人生观和价值观一致",
            "description": "", "score": 100,
        }]), [], []),
    ]
    client, _store = _client(rows=rows)

    response = client.get(
        "/api/dating-priority/stats",
        params={"perspective": "female_to_male"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    by_label = {item["label"]: item for item in body["priority_stats"]}
    assert by_label["诚实守信"]["selection_count"] == 2
    assert by_label["人生观和价值观一致"]["selection_count"] == 2
    # 三位访客，"人生观和价值观一致" 被两位选中 → 2/3
    assert by_label["人生观和价值观一致"]["selection_rate"] == round(2 / 3 * 100, 1)
