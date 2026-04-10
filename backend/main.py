import json
import os
import sys
import time
import traceback
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from query_emotion_verses import (
    DEFAULT_RERANK_CANDIDATES,
    DEFAULT_RERANK_WEIGHT,
    assess_psychological_state,
    query_emotion_verses,
)
from web_emotion_query import HISTORY_FILE, load_history, save_history_entry

LAYOUT_FILE = ROOT_DIR / 'emotion_sphere_layout.json'
MATCHES_FILE = ROOT_DIR / 'emotion_exemplar_verse_matches.json'
FRONTEND_DIST = ROOT_DIR / 'emotion-sphere-ui' / 'dist'


class QueryRequest(BaseModel):
    query: str = Field(min_length=1)
    topFeatures: int = Field(default=5, ge=1, le=20)
    topVerses: int = Field(default=5, ge=1, le=20)
    languageFilter: str = Field(default='both')
    includeGuidance: bool = False
    enableRerank: bool = False
    rerankCandidates: int = Field(default=DEFAULT_RERANK_CANDIDATES, ge=1, le=100)
    rerankWeight: float = Field(default=DEFAULT_RERANK_WEIGHT, ge=0.0, le=1.0)


class GuidanceRequest(BaseModel):
    query: str = Field(min_length=1)


app = FastAPI(title='Bible Emotion Sphere API')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


def load_json_file(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, 'r', encoding='utf-8') as file:
        return json.load(file)


def build_feature_match_map() -> dict[str, dict]:
    match_map = {}
    for item in load_json_file(MATCHES_FILE):
        key = f"{item.get('layer')}:{item.get('feature_id')}"
        match_map[key] = item
    return match_map


@app.get('/api/health')
def health() -> dict:
    return {'ok': True}


@app.get('/api/layout')
def get_layout() -> dict:
    layout = load_json_file(LAYOUT_FILE)
    return {'items': layout, 'count': len(layout)}


@app.get('/api/history')
def get_history() -> dict:
    return {'items': load_history()}


@app.get('/api/feature')
def get_feature(key: str = Query(min_length=1)) -> dict:
    item = build_feature_match_map().get(key)
    if item is None:
        raise HTTPException(status_code=404, detail='Feature not found')
    return item


# ── debug flag: set DEBUG_API=1 in HF Space secrets to expose tracebacks ──
_DEBUG = os.getenv('DEBUG_API', '0') == '1'


def _handle_exc(exc: Exception) -> None:
    """Always print full traceback to stdout (visible in HF Logs)."""
    print('=' * 72, flush=True)
    print('API ERROR:', type(exc).__name__, str(exc), flush=True)
    traceback.print_exc()
    print('=' * 72, flush=True)


@app.post('/api/guidance')
def get_guidance(payload: GuidanceRequest) -> dict:
    try:
        return assess_psychological_state(payload.query.strip())
    except Exception as exc:
        _handle_exc(exc)
        detail = {'error': str(exc), 'traceback': traceback.format_exc()} if _DEBUG else str(exc)
        raise HTTPException(status_code=500, detail=detail) from exc


@app.post('/api/query')
def post_query(payload: QueryRequest) -> dict:
    query_text = payload.query.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail='Missing query')

    # Startup diagnostics printed once on first request
    _startup_check()

    try:
        started_at = time.perf_counter()
        result = query_emotion_verses(
            query_text=query_text,
            top_features=payload.topFeatures,
            top_verses_per_language=payload.topVerses,
            include_guidance=payload.includeGuidance,
            enable_rerank=payload.enableRerank,
            rerank_candidates=payload.rerankCandidates,
            rerank_weight=payload.rerankWeight,
        )
        result['query_latency_ms'] = round((time.perf_counter() - started_at) * 1000, 2)
        save_history_entry(query_text, payload.topFeatures, payload.topVerses, payload.languageFilter, result)
        return result
    except Exception as exc:
        _handle_exc(exc)
        detail = {'error': str(exc), 'traceback': traceback.format_exc()} if _DEBUG else str(exc)
        raise HTTPException(status_code=500, detail=detail) from exc


_startup_checked = False


def _startup_check() -> None:
    """Print key file sizes and paths to HF Logs on first query."""
    global _startup_checked
    if _startup_checked:
        return
    _startup_checked = True
    print('── Startup check ──', flush=True)
    print(f'ROOT_DIR : {ROOT_DIR}', flush=True)
    for name, path in [
        ('layout', LAYOUT_FILE),
        ('matches', MATCHES_FILE),
    ]:
        exists = path.exists()
        size = path.stat().st_size if exists else -1
        print(f'  {name}: {path}  exists={exists}  size={size}', flush=True)
    # Check for common large files that might be LFS pointers
    for pattern in ('*.npy', '*.pkl', '*.bin'):
        for p in sorted(ROOT_DIR.glob(pattern)):
            print(f'  {p.name}: {p.stat().st_size} bytes', flush=True)
    print('──────────────────', flush=True)


if FRONTEND_DIST.exists():
    app.mount('/assets', StaticFiles(directory=FRONTEND_DIST / 'assets'), name='assets')


@app.get('/{full_path:path}')
def serve_frontend(full_path: str, request: Request):
    if full_path.startswith('api/'):
        raise HTTPException(status_code=404, detail='Not found')

    if FRONTEND_DIST.exists():
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / 'index.html')

    raise HTTPException(status_code=404, detail='Frontend build output not found. Run npm run build in emotion-sphere-ui first.')
