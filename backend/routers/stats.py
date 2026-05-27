"""
Stats & observability router.
Covers: /api/stats, /api/stats/track, /api/layout, /api/history,
        /api/feature, /api/retrieval/evaluation
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["stats"])

# ── These module-level references are populated by main.py after import ───────
# main.py calls:  from routers.stats import init_stats_router; init_stats_router(...)
_state: dict[str, Any] = {}


def init_stats_router(
    *,
    stats_lock: threading.Lock,
    load_visit_stats,
    public_visit_stats,
    track_visit,
    load_json_file,
    build_feature_match_map,
    load_history,
    load_retrieval_observability_from_db,
    load_json_file_raw,
    layout_file: Path,
    evaluation_cases_file: Path,
    evaluation_report_file: Path,
    artifact_manifest_file: Path,
    root_dir: Path,
) -> None:
    _state.update(
        stats_lock=stats_lock,
        load_visit_stats=load_visit_stats,
        public_visit_stats=public_visit_stats,
        track_visit=track_visit,
        load_json_file=load_json_file,
        build_feature_match_map=build_feature_match_map,
        load_history=load_history,
        load_retrieval_observability_from_db=load_retrieval_observability_from_db,
        load_json_file_raw=load_json_file_raw,
        layout_file=layout_file,
        evaluation_cases_file=evaluation_cases_file,
        evaluation_report_file=evaluation_report_file,
        artifact_manifest_file=artifact_manifest_file,
        root_dir=root_dir,
    )


class VisitTrackRequest(BaseModel):
    visitorId: str


@router.get("/stats")
def get_stats() -> dict:
    with _state["stats_lock"]:
        return _state["public_visit_stats"](_state["load_visit_stats"]())


@router.post("/stats/track")
def post_track_stats(payload: VisitTrackRequest) -> dict:
    return _state["track_visit"](payload.visitorId)


@router.get("/layout")
def get_layout() -> dict:
    layout = _state["load_json_file"](_state["layout_file"])
    return {"items": layout, "count": len(layout)}


@router.get("/history")
def get_history() -> dict:
    return {"items": _state["load_history"]()}


@router.get("/feature")
def get_feature(key: str = Query(min_length=1)) -> dict:
    item = _state["build_feature_match_map"]().get(key)
    if item is None:
        raise HTTPException(status_code=404, detail="Feature not found")
    return item


@router.get("/retrieval/evaluation")
def get_retrieval_evaluation() -> dict:
    _load = _state["load_json_file_raw"]
    root  = _state["root_dir"]
    cases    = _load(_state["evaluation_cases_file"], [])
    db_report, db_manifest = _state["load_retrieval_observability_from_db"]()
    report   = db_report  or _load(_state["evaluation_report_file"], None)
    manifest = db_manifest or _load(_state["artifact_manifest_file"], None)

    themes: dict[str, int] = {}
    labels: dict[str, int] = {}
    for case in (cases if isinstance(cases, list) else []):
        theme = str(case.get("theme") or "unknown")
        themes[theme] = themes.get(theme, 0) + 1
        for lbl in case.get("emotion_labels") or []:
            lk = str(lbl)
            labels[lk] = labels.get(lk, 0) + 1

    artifact_items = manifest.get("artifacts") or [] if isinstance(manifest, dict) else []

    return {
        "ok": True,
        "gold_set": {
            "case_count": len(cases) if isinstance(cases, list) else 0,
            "themes": themes,
            "top_emotion_labels": sorted(labels.items(), key=lambda x: x[1], reverse=True)[:12],
        },
        "latest_report": report,
        "manifest": {
            "available": isinstance(manifest, dict),
            "generated_at": manifest.get("generated_at") if isinstance(manifest, dict) else None,
            "artifact_count": manifest.get("artifact_count") if isinstance(manifest, dict) else 0,
            "missing": manifest.get("missing") if isinstance(manifest, dict) else [],
            "artifacts": artifact_items[:12],
        },
        "paths": {
            "cases": str(_state["evaluation_cases_file"].relative_to(root)),
            "report": str(_state["evaluation_report_file"].relative_to(root)),
            "manifest": str(_state["artifact_manifest_file"].relative_to(root)),
        },
    }
