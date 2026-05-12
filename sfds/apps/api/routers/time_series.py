"""
Time Series Router — TimescaleDB analytics API.
"""

from fastapi import APIRouter, Depends, HTTPException
from services.time_series_service.service import TimeSeriesService, get_time_series_service

router = APIRouter()


@router.get("/analysis/{user_id}")
async def get_time_analysis(
    user_id: str,
    days: int = 30,
    svc: TimeSeriesService = Depends(get_time_series_service),
):
    return await svc.analyze(user_id, days=days)


@router.get("/trends/{user_id}")
async def get_trends(user_id: str, svc: TimeSeriesService = Depends(get_time_series_service)):
    return await svc.get_trends(user_id)


@router.get("/cycles/{user_id}")
async def detect_cycles(user_id: str, svc: TimeSeriesService = Depends(get_time_series_service)):
    return await svc.detect_cycles(user_id)
