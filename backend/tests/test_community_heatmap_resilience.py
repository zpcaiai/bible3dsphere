"""Resilience tests for anonymous community heatmap endpoint."""
from fastapi import Response
import pytest

pytestmark = pytest.mark.no_db


@pytest.mark.asyncio
async def test_emotion_heatmap_degrades_when_pool_is_exhausted():
    from routers import community

    def raise_pool_error():
        raise Exception("connection pool exhausted")

    community.init_community_router(get_db=raise_pool_error, release_db=lambda conn: None)
    response = Response()

    data = await community.emotion_heatmap(
        request=None,
        response=response,
        window_hours=24,
        top_n=8,
    )

    assert response.status_code == 503
    assert data["scope"] == "unavailable"
    assert data["emotions"] == []
    assert data["total_checkins"] == 0
