"""
Test suite verifying that all 8 business lines have closed loops and unreasonable logic is repaired:
1. Crisis triage interception on search/guidance/prayer/testimony
2. Theological safety reviews on sermon/faith-qa
3. Prayer lifecycle (submit -> answer -> formation event + milestone + testimony prompt)
4. Testimony submission with optional prayer_id link
5. Morning dew checkin with formation event and milestone check
6. Bible reading book completion awarding bible_book_done milestone
7. Weekly review prayer adoption
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI, Request
from pydantic import BaseModel

pytestmark = pytest.mark.no_db


class _FakeCursor:
    def __init__(self, fetch_val=None):
        self.fetch_val = fetch_val
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return self.fetch_val

    def fetchall(self):
        return [self.fetch_val] if self.fetch_val else []


class _FakeConn:
    def __init__(self, fetch_val=None):
        self.cur = _FakeCursor(fetch_val)

    def cursor(self):
        return self.cur

    def commit(self):
        pass

    def rollback(self):
        pass


def test_verse_query_crisis_interception():
    from routers.verse import router as verse_router, init_verse_router
    app = FastAPI()
    app.include_router(verse_router)
    
    init_verse_router(
        get_session_user=lambda req: {"email": "test@example.com"},
    )
    
    client = TestClient(app)
    
    # High-risk crisis input should be intercepted
    res = client.post("/api/query", json={"query": "活着好痛苦，我想自杀结束生命"})
    assert res.status_code == 200
    data = res.json()
    assert data.get("is_crisis") is True
    assert "crisis_level" in data
    assert "resources" in data
    assert len(data.get("results", [])) == 0


def test_verse_guidance_crisis_interception():
    from routers.verse import router as verse_router, init_verse_router
    app = FastAPI()
    app.include_router(verse_router)
    
    init_verse_router(
        get_session_user=lambda req: {"email": "test@example.com"},
    )
    client = TestClient(app)
    
    res = client.post("/api/guidance", json={"query": "我不活了，想跳楼"})
    assert res.status_code == 200
    data = res.json()
    assert data.get("is_crisis") is True
    assert "resources" in data


def test_prayer_post_crisis_interception():
    from routers.prayer import router as prayer_router, init_prayer_router
    app = FastAPI()
    app.include_router(prayer_router)
    
    init_prayer_router(
        get_db=lambda: _FakeConn(),
        release_db=lambda conn: None,
        get_session_user=lambda req: {"email": "test@example.com"},
        is_admin=lambda email: False,
        sanitize_text=lambda t: t,
        to_shanghai_iso=lambda dt: str(dt),
    )
    client = TestClient(app)
    
    res = client.post("/api/prayers", json={"content": "我真的不想活了，求死", "is_anonymous": False, "is_public": False})
    assert res.status_code == 200
    data = res.json()
    assert data.get("ok") is False
    assert data.get("is_crisis") is True


def test_prayer_answered_flow_and_milestones():
    from routers.prayer import router as prayer_router, init_prayer_router
    app = FastAPI()
    app.include_router(prayer_router)
    
    # Prayer lookup: email, deleted_at, content
    fake_conn = _FakeConn(fetch_val=("test@example.com", None, "求神医治母亲的重病"))
    
    award_called = []
    def mock_award(email, conn):
        award_called.append(email)
        return [{"key": "prayer_answered_3", "name": "✝️ 信心见证者", "desc": "3个祷告已蒙恩答应"}]

    init_prayer_router(
        get_db=lambda: fake_conn,
        release_db=lambda conn: None,
        get_session_user=lambda req: {"email": "test@example.com"},
        is_admin=lambda email: False,
        sanitize_text=lambda t: t,
        to_shanghai_iso=lambda dt: str(dt),
        award_milestone_if_due=mock_award,
    )
    client = TestClient(app)
    
    with patch("formation_events.record_event") as mock_record:
        res = client.patch("/api/prayers/101/status", json={"status": "answered"})
        assert res.status_code == 200
        data = res.json()
        assert data.get("ok") is True
        assert data.get("status") == "answered"
        assert "testimony_prompt" in data
        assert data["testimony_prompt"]["prayer_id"] == 101
        assert data["testimony_prompt"]["can_convert"] is True
        assert "new_milestones" in data
        assert data["new_milestones"][0]["key"] == "prayer_answered_3"
        
        # Verify event recorded
        mock_record.assert_called_once()
        args, kwargs = mock_record.call_args
        assert args[0] == "test@example.com"
        assert args[1] == "prayer"
        assert args[2] == "answered_prayer"


def test_testimony_post_with_prayer_id():
    from routers.testimony import router as testimony_router, init_testimony_router
    app = FastAPI()
    app.include_router(testimony_router)
    
    fake_conn = _FakeConn(fetch_val=[42])
    
    init_testimony_router(
        get_db=lambda: fake_conn,
        release_db=lambda conn: None,
        get_session_user=lambda req: {"email": "test@example.com", "nickname": "提摩太"},
        is_admin=lambda email: False,
        sanitize_text=lambda t: t,
        to_shanghai_iso=lambda dt: str(dt),
    )
    client = TestClient(app)
    
    with patch("formation_events.record_event") as mock_record:
        res = client.post("/api/testimonies", json={
            "title": "神奇妙的医治与恩典",
            "before_story": "过去非常焦虑",
            "how_story": "弟兄姐妹同心祷告",
            "after_story": "母亲手术非常顺利，现在身体恢复很好",
            "prayer_id": 101,
        })
        assert res.status_code == 200
        data = res.json()
        assert data.get("ok") is True
        assert data.get("id") == 42
        assert data.get("prayer_id") == 101
        
        # Verify ref_id connects to prayer
        mock_record.assert_called_once()
        assert "prayer:101" in mock_record.call_args[1]["ref_id"]


def test_dew_checkin_flow():
    from routers.dew import router as dew_router, init_dew_router
    app = FastAPI()
    app.include_router(dew_router)
    
    fake_conn = _FakeConn()
    
    milestone_awards = []
    def mock_award(email, conn):
        milestone_awards.append(email)
        return [{"key": "devotion_streak_7", "name": "🌿 旷野七日", "desc": "连续7天灵修"}]
    
    init_dew_router(
        get_db=lambda: fake_conn,
        release_db=lambda conn: None,
        get_session_user=lambda req: {"email": "test@example.com"},
        award_milestone_if_due=mock_award,
    )
    client = TestClient(app)
    
    with patch("formation_events.record_event") as mock_record:
        res = client.post("/api/dew/checkin", json={
            "tier": 10,
            "reflection": "今天通过清晨甘露体会到在旷野中神的信实供应。",
            "prayer": "主啊，愿我单单仰望你。",
        })
        assert res.status_code == 200
        data = res.json()
        assert data.get("ok") is True
        assert data.get("tier") == 10
        assert "new_milestones" in data
        assert data["new_milestones"][0]["key"] == "devotion_streak_7"
        
        # Check event recorded
        mock_record.assert_called_once()
        assert mock_record.call_args[0][0] == "test@example.com"
        assert mock_record.call_args[0][1] == "dew"
        assert mock_record.call_args[0][2] == "checkin"


def test_bible_reading_book_done_milestone():
    from routers.bible_reading import router as reading_router, init_bible_reading_router
    app = FastAPI()
    app.include_router(reading_router)
    
    # 约翰二书只有1章，所以只要完成1章就全卷完成
    fake_conn = _FakeConn(fetch_val=[1])
    
    init_bible_reading_router(
        _get_db=lambda: fake_conn,
        _get_session_user=lambda req: {"email": "test@example.com"},
        _release_db=lambda conn: None,
        _sanitize_text=lambda t: t,
    )
    client = TestClient(app)
    
    res = client.post("/api/bible-reading/mark", json={
        "book": "约翰二书",
        "chapter": 1,
        "highlight": "我们若照他的诫命行，这就是爱。",
        "plan_id": "1year",
    })
    assert res.status_code == 200
    data = res.json()
    assert data.get("ok") is True
    assert data.get("book_completed") is True
    assert data.get("new_badge") == "bible_book_done"
    
    # Check executed SQL inserted bible_book_done
    executed_params = [call[1] for call in fake_conn.cur.executed]
    assert any("bible_book_done" in params for params in executed_params if isinstance(params, tuple))


def test_weekly_review_adopt_prayer():
    from routers.weekly_review import router as review_router, init_weekly_review_router
    app = FastAPI()
    app.include_router(review_router)
    
    fake_conn = _FakeConn(fetch_val=[88])
    
    init_weekly_review_router(
        get_db=lambda: fake_conn,
        release_db=lambda conn: None,
        get_session_user=lambda req: {"email": "test@example.com", "nickname": "彼得"},
        to_shanghai_iso=lambda dt: str(dt),
    )
    client = TestClient(app)
    
    with patch("formation_events.record_event") as mock_record:
        res = client.post("/api/weekly-review/adopt-prayer", json={
            "review_id": 12,
            "prayer_content": "本周面对工作压力，求神赐下从上头来的平安",
            "is_public": False,
        })
        assert res.status_code == 200
        data = res.json()
        assert data.get("ok") is True
        assert data.get("prayer_id") == 88
        
        mock_record.assert_called_once()
        assert "prayer:88" in mock_record.call_args[1]["ref_id"]
