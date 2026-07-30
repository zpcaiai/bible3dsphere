"""Real-database coverage for anonymous dating-priority stat accumulation.

test_dating_priority_anonymous_stats.py exercises the router logic with a
fake cursor (fast, no DB), but that fake doesn't implement real SQL
semantics. The one thing genuinely worth double-checking against a real
PostgreSQL instance is `_load_stats`'s `DISTINCT ON (visitor_id) ... ORDER
BY created_at DESC, id DESC` clause: does it actually (a) accumulate votes
across every distinct anonymous visitor, and (b) collapse a resubmission
from the same visitor down to their latest answer instead of stacking it?
That's exactly the "累计所有人的匿名选项投票次数和结果" requirement, so it's
worth a real integration test rather than trusting the fake-cursor suite.
"""
from __future__ import annotations

import uuid

import pytest

pytestmark = pytest.mark.integration


def _visitor_id() -> str:
    return f"survey-visitor-{uuid.uuid4().hex}"


def _submit(client, visitor_id, perspective, label, category="人品与关系品质"):
    return client.post("/api/dating-priority/submit", json={
        "visitor_id": visitor_id,
        "perspective": perspective,
        "version": 3,
        "selected": [{
            "rank": 1,
            "category": category,
            "label": label,
            "description": "",
            "score": 100,
        }],
        "vetoes": [],
        "totalScore": 100,
    })


def test_stats_accumulate_votes_from_every_distinct_visitor_in_real_postgres(client):
    # 用一个仅本测试可能用到的独特标签，避免和其它测试/历史数据的行掺在一起，
    # 导致 selection_count 断言变得不确定。
    label = f"真实数据库累计测试-{uuid.uuid4().hex[:8]}"
    perspective = "female_to_male"

    voters = [_visitor_id() for _ in range(3)]
    for visitor_id in voters:
        response = _submit(client, visitor_id, perspective, label)
        assert response.status_code == 200

    stats = client.get(
        "/api/dating-priority/stats",
        params={"perspective": perspective},
    ).json()

    matches = [item for item in stats["priority_stats"] if item["label"] == label]
    assert len(matches) == 1
    # 三个不同的匿名访客都投给了同一个因素，票数必须是 3，不能因为
    # 分批提交或聚合逻辑漏掉任何一位而变少。
    assert matches[0]["selection_count"] == 3


def test_resubmission_from_the_same_visitor_replaces_their_earlier_vote(client):
    """同一访客改答案，DISTINCT ON (visitor_id) 必须只保留最新一票。"""
    visitor_id = _visitor_id()
    perspective = "male_to_female"
    first_label = f"改票前-{uuid.uuid4().hex[:8]}"
    second_label = f"改票后-{uuid.uuid4().hex[:8]}"

    first = _submit(client, visitor_id, perspective, first_label)
    assert first.status_code == 200
    assert any(
        item["label"] == first_label
        for item in first.json()["stats"]["priority_stats"]
    )

    second = _submit(client, visitor_id, perspective, second_label)
    assert second.status_code == 200
    stats = second.json()["stats"]

    labels = {item["label"] for item in stats["priority_stats"]}
    assert second_label in labels
    # 旧答案不能继续占一票——否则一个人反复改主意会让统计虚高。
    assert first_label not in labels
